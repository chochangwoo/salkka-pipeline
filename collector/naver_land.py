"""
collector/naver_land.py
네이버 부동산 데이터 수집
- 단지 검색 / 상세 정보 / 매물 현황 / 시세
- JSON 파일 캐싱으로 429 Rate Limit 대응
"""

import requests
import time
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://new.land.naver.com/",
}

BASE = "https://new.land.naver.com/api"
DELAY = 3.0  # Rate limit 방지 (네이버 429 대응, 1.5→3초로 상향)
CACHE_DIR = Path("data/cache/naver")
CACHE_TTL_DAYS = 7  # 캐시 유효 기간 (일)


def _cache_path(key: str) -> Path:
    """캐시 파일 경로"""
    safe_key = key.replace(" ", "_").replace("/", "_")
    return CACHE_DIR / f"{safe_key}.json"


def _load_cache(key: str) -> dict | None:
    """캐시 로드 (TTL 만료 시 None)"""
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(data.get("_cached_at", "2000-01-01"))
        if (datetime.now() - cached_at).days > CACHE_TTL_DAYS:
            return None
        return data
    except (json.JSONDecodeError, ValueError):
        return None


def _save_cache(key: str, data: dict):
    """캐시 저장"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data["_cached_at"] = datetime.now().isoformat()
    _cache_path(key).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@dataclass
class ComplexInfo:
    """네이버 부동산 단지 상세"""
    complex_no: str = ""
    complex_name: str = ""
    total_households: int = 0        # 총 세대수
    total_dong: int = 0              # 총 동수
    max_floor: int = 0               # 최고 층수
    build_year: int = 0              # 준공연도
    construction_company: str = ""   # 건설사
    parking_per_household: float = 0 # 세대당 주차
    heating: str = ""                # 난방 방식
    floor_area_ratio: float = 0      # 용적률
    building_coverage: float = 0     # 건폐율
    # 매물 현황
    sale_count: int = 0              # 매매 매물 수
    jeonse_count: int = 0            # 전세 매물 수
    min_sale_price: int = 0          # 최저 호가 (만원)
    max_sale_price: int = 0          # 최고 호가 (만원)
    min_jeonse_price: int = 0        # 전세 최저 (만원)
    max_jeonse_price: int = 0        # 전세 최고 (만원)


# ── 법정동 코드 → 네이버 cortarNo ─────────────────────────────

def _to_cortar(lawd_5: str) -> str:
    """5자리 법정동 코드를 10자리 네이버 cortarNo로 변환"""
    return lawd_5 + "00000"


# ── 단지 검색 ──────────────────────────────────────────────────

def search_complexes(region: str, top_n: int = 30) -> list[dict]:
    """
    지역 내 아파트 단지 목록 검색 (캐시 지원)

    Returns:
        [{"complexNo": str, "complexName": str, "totalHouseholdCount": int, ...}]
    """
    # 캐시 확인
    cache_key = f"complexes_{region}"
    cached = _load_cache(cache_key)
    if cached and cached.get("items"):
        items = cached["items"]
        print(f"[네이버] {region} 단지 목록 캐시 히트: {len(items)}개")
        return items[:top_n]

    from collector.molit import _get_lawd_cd
    codes = _get_lawd_cd(region)

    results = []
    for code in codes:
        cortar = _to_cortar(code)
        try:
            resp = requests.get(
                f"{BASE}/regions/complexes",
                params={
                    "cortarNo": cortar,
                    "realEstateType": "APT",
                    "order": "",
                },
                headers=HEADERS,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("complexList", [])
                results.extend(items)
                print(f"[네이버] {region} 단지 검색: {len(items)}개")
            else:
                print(f"[네이버] 단지 검색 실패: HTTP {resp.status_code}")
            time.sleep(DELAY)
        except Exception as e:
            print(f"[네이버] 단지 검색 오류 ({region}): {e}")

    # 캐시 저장
    if results:
        _save_cache(cache_key, {"items": results})

    return results[:top_n]


# ── 단지 상세 ──────────────────────────────────────────────────

def get_complex_detail(complex_no: str) -> dict:
    """네이버 단지 상세 정보 조회"""
    try:
        resp = requests.get(
            f"{BASE}/complexes/{complex_no}",
            params={"sameAddressGroup": "false"},
            headers=HEADERS,
            timeout=10,
        )
        time.sleep(DELAY)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"[네이버] 상세 조회 실패 ({complex_no}): {e}")
    return {}


def get_complex_articles(complex_no: str, trade_type: str = "A1") -> list[dict]:
    """
    단지 매물 목록 조회
    trade_type: A1=매매, B1=전세, B2=월세
    """
    try:
        resp = requests.get(
            f"{BASE}/articles/complex/{complex_no}",
            params={
                "realEstateType": "APT",
                "tradeType": trade_type,
                "page": "1",
                "sameAddressGroup": "true",
            },
            headers=HEADERS,
            timeout=10,
        )
        time.sleep(DELAY)
        if resp.status_code == 200:
            return resp.json().get("articleList", [])
    except Exception as e:
        print(f"[네이버] 매물 조회 실패 ({complex_no}): {e}")
    return []


# ── 단지명 → 네이버 단지번호 ──────────────────────────────────

def find_complex_no(complex_name: str, region: str) -> str:
    """단지명으로 네이버 단지번호 검색 (부분 일치)"""
    complexes = search_complexes(region)
    for c in complexes:
        naver_name = c.get("complexName", "")
        if complex_name in naver_name or naver_name in complex_name:
            return c.get("complexNo", "")
    return ""


# ── 통합 조회: 단지 상세 + 매물 현황 ──────────────────────────

def enrich_complex(complex_name: str, region: str) -> ComplexInfo:
    """
    단지명으로 네이버 부동산 데이터 통합 조회 (캐시 지원).
    단지 상세 + 매매 매물 + 전세 매물을 하나의 ComplexInfo로 반환.
    """
    # 캐시 확인
    cache_key = f"enrich_{region}_{complex_name}"
    cached = _load_cache(cache_key)
    if cached and cached.get("complex_no"):
        info = ComplexInfo(**{k: v for k, v in cached.items() if k != "_cached_at"})
        print(f"[네이버] {complex_name}: 캐시 히트")
        return info

    info = ComplexInfo(complex_name=complex_name)

    complex_no = find_complex_no(complex_name, region)
    if not complex_no:
        print(f"[네이버] '{complex_name}' 단지번호 검색 실패")
        return info

    info.complex_no = complex_no

    # 상세 정보
    detail = get_complex_detail(complex_no)
    if detail:
        info.total_households = _int(detail.get("totalHouseholdCount"))
        info.total_dong = _int(detail.get("totalDongCount"))
        info.max_floor = _int(detail.get("highFloor"))
        info.build_year = _int(detail.get("useApproveYmd", "0")[:4])
        info.construction_company = detail.get("constructionCompanyName", "")
        info.parking_per_household = _float(detail.get("parkingCountByHousehold"))
        info.heating = detail.get("heatingMethodTypeCode", "")
        info.floor_area_ratio = _float(detail.get("floorAreaRatio"))
        info.building_coverage = _float(detail.get("buildingCoverageRatio"))
        print(f"[네이버] {complex_name}: {info.total_households}세대, {info.construction_company}")

    # 매매 매물
    sale_articles = get_complex_articles(complex_no, "A1")
    if sale_articles:
        info.sale_count = len(sale_articles)
        prices = _parse_prices(sale_articles)
        if prices:
            info.min_sale_price = min(prices)
            info.max_sale_price = max(prices)
        print(f"[네이버] {complex_name}: 매매 매물 {info.sale_count}건")

    # 전세 매물
    jeonse_articles = get_complex_articles(complex_no, "B1")
    if jeonse_articles:
        info.jeonse_count = len(jeonse_articles)
        prices = _parse_prices(jeonse_articles)
        if prices:
            info.min_jeonse_price = min(prices)
            info.max_jeonse_price = max(prices)

    # 캐시 저장
    _save_cache(cache_key, asdict(info))

    return info


def enrich_multiple(complex_names: list[str], region: str) -> dict[str, ComplexInfo]:
    """여러 단지를 한 번에 조회 (단지 목록 캐싱)"""
    results = {}
    for name in complex_names:
        results[name] = enrich_complex(name, region)
    return results


# ── 유틸리티 ───────────────────────────────────────────────────

def _int(val) -> int:
    try:
        return int(val) if val else 0
    except (ValueError, TypeError):
        return 0


def _float(val) -> float:
    try:
        return float(val) if val else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_prices(articles: list[dict]) -> list[int]:
    """매물 목록에서 가격 추출 (만원 단위)"""
    prices = []
    for a in articles:
        raw = a.get("dealOrWarrantPrc", "")
        if raw:
            try:
                cleaned = raw.replace(",", "").replace(" ", "")
                # "6억 5,000" 같은 형태 처리
                if "억" in cleaned:
                    parts = cleaned.split("억")
                    eok = int(parts[0]) * 10000
                    rest = int(parts[1]) if parts[1] else 0
                    prices.append(eok + rest)
                else:
                    prices.append(int(cleaned))
            except (ValueError, IndexError):
                continue
    return prices


def estimate_jeonse_rate(region: str, sample_n: int = 5) -> float:
    """
    지역 전세가율 추정.
    주요 단지 N개의 매매 호가 중위값 / 전세 호가 중위값으로 계산.
    캐시 지원 (7일 TTL).

    Returns:
        전세가율 (0~100 사이 %, 실패 시 0.0)
    """
    cache_key = f"jeonse_rate_{region}"
    cached = _load_cache(cache_key)
    if cached and cached.get("rate", 0) > 0:
        print(f"[전세가율] {region}: 캐시 히트 {cached['rate']:.1f}%")
        return cached["rate"]

    complexes = search_complexes(region, top_n=sample_n * 2)
    if not complexes:
        return 0.0

    # 세대수 큰 순으로 샘플링 (대표성)
    sorted_complexes = sorted(
        complexes,
        key=lambda c: int(c.get("totalHouseholdCount", 0) or 0),
        reverse=True,
    )

    rates = []
    for c in sorted_complexes[:sample_n]:
        cno = c.get("complexNo", "")
        if not cno:
            continue

        sale_articles = get_complex_articles(cno, "A1")
        jeonse_articles = get_complex_articles(cno, "B1")

        sale_prices = _parse_prices(sale_articles)
        jeonse_prices = _parse_prices(jeonse_articles)

        if sale_prices and jeonse_prices:
            sale_median = sorted(sale_prices)[len(sale_prices) // 2]
            jeonse_median = sorted(jeonse_prices)[len(jeonse_prices) // 2]
            if sale_median > 0:
                rate = (jeonse_median / sale_median) * 100
                if 30 <= rate <= 95:  # 이상치 제거
                    rates.append(rate)
                    print(f"  → {c.get('complexName', '')}: 전세가율 {rate:.1f}%")

    if not rates:
        return 0.0

    avg_rate = sum(rates) / len(rates)
    _save_cache(cache_key, {"rate": round(avg_rate, 1), "sample_count": len(rates)})
    print(f"[전세가율] {region}: {avg_rate:.1f}% (샘플 {len(rates)}개)")
    return round(avg_rate, 1)


def complex_info_to_text(info: ComplexInfo) -> str:
    """ComplexInfo → 뉴스레터용 텍스트 요약"""
    lines = []
    if info.total_households:
        lines.append(f"총 {info.total_households}세대 ({info.total_dong}개 동)")
    if info.construction_company:
        lines.append(f"건설사: {info.construction_company}")
    if info.max_floor:
        lines.append(f"최고 {info.max_floor}층")
    if info.parking_per_household:
        lines.append(f"주차 세대당 {info.parking_per_household:.1f}대")
    if info.sale_count:
        price_range = ""
        if info.min_sale_price and info.max_sale_price:
            price_range = f" ({info.min_sale_price/10000:.1f}~{info.max_sale_price/10000:.1f}억)"
        lines.append(f"매매 매물 {info.sale_count}건{price_range}")
    if info.jeonse_count:
        lines.append(f"전세 매물 {info.jeonse_count}건")
    return " | ".join(lines) if lines else ""
