"""
collector/supply.py
공급/정비사업 데이터 수집

데이터 소스:
1. 국토부 주택인허가 API (공공데이터포털)
2. 수동 입력 데이터 (editor가 매월 업데이트)
"""

import requests
from dataclasses import dataclass, field
from datetime import datetime
import config


@dataclass
class SupplyItem:
    """분양/입주 예정 단지"""
    name: str                   # 단지명
    region: str                 # 지역 (구 단위)
    households: int             # 세대수
    expected_date: str          # 예정 시기 (YYYY-MM 또는 YYYY)
    supply_type: str            # "분양예정" / "입주예정" / "정비사업"
    status: str = ""            # 상태 (인허가/착공/분양승인 등)
    developer: str = ""         # 시행사/건설사
    note: str = ""              # 비고


@dataclass
class SupplyForecast:
    """지역 공급 전망"""
    region: str
    total_supply_3y: int = 0            # 향후 3년 총 공급
    items: list = field(default_factory=list)  # SupplyItem 리스트
    yearly_breakdown: dict = field(default_factory=dict)  # {2026: 1200, 2027: 3500, ...}
    risk_level: str = "보통"             # "낮음" / "보통" / "높음" / "매우높음"
    summary: str = ""                    # 요약 텍스트


# ── 국토부 인허가 API ──────────────────────────────────────────

def fetch_housing_permits(region: str, year: int = None) -> list[dict]:
    """
    국토부 주택인허가 데이터 조회
    API: 건축인허가정보 (공공데이터포털)
    """
    from collector.molit import _get_lawd_cd
    codes = _get_lawd_cd(region)
    year = year or datetime.today().year

    url = "http://apis.data.go.kr/1613000/ArchPmsService_v2/getApHusBassInfo"
    results = []

    for code in codes:
        params = {
            "serviceKey": config.MOLIT_API_KEY,
            "sigunguCd": code,
            "numOfRows": "100",
            "pageNo": "1",
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                # XML 파싱
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                items = root.findall(".//item")
                for item in items:
                    def get(tag):
                        el = item.find(tag)
                        return el.text.strip() if el is not None and el.text else ""

                    results.append({
                        "name": get("bldNm"),
                        "households": _safe_int(get("hhldCnt")),
                        "permit_date": get("archPmsDay"),
                        "dong_count": _safe_int(get("dongCnt")),
                        "use_type": get("mainPurpsCdNm"),
                    })
                print(f"[공급] 인허가 데이터: {len(items)}건 ({region})")
        except Exception as e:
            print(f"[공급] 인허가 API 오류 ({region}): {e}")

    # 아파트만 필터
    apt_results = [r for r in results if "아파트" in r.get("use_type", "") or "공동주택" in r.get("use_type", "")]
    return apt_results


# ── 수동 데이터 (매월 편집자 업데이트) ─────────────────────────

# 주요 지역 공급 예정 데이터 (editor가 매월 업데이트)
CURATED_SUPPLY = {
    "안양시 동안구": [
        SupplyItem("평촌 더샵 퍼스트파크", "안양시 동안구", 2998, "2027-06", "분양예정", "착공", "포스코이앤씨"),
        SupplyItem("평촌 자이 아이파크", "안양시 동안구", 1536, "2027-09", "분양예정", "인허가", "GS건설/HDC현대산업개발"),
        SupplyItem("비산 재건축", "안양시 동안구", 1200, "2028", "정비사업", "사업시행인가", ""),
        SupplyItem("평촌 래미안", "안양시 동안구", 892, "2028-03", "입주예정", "시공중", "삼성물산"),
    ],
    "마포구": [
        SupplyItem("마포프레스티지자이", "마포구", 3885, "2027-12", "입주예정", "시공중", "GS건설"),
        SupplyItem("신촌그랑자이", "마포구", 498, "2027-06", "분양예정", "착공", "GS건설"),
    ],
    "강남구": [
        SupplyItem("개포주공1단지 재건축", "강남구", 6702, "2028", "정비사업", "관리처분인가", ""),
        SupplyItem("은마아파트 재건축", "강남구", 5300, "2029", "정비사업", "정비구역지정", ""),
    ],
}


# ── 공급 전망 조합 ─────────────────────────────────────────────

def get_supply_forecast(region: str) -> SupplyForecast:
    """
    지역 공급 전망 생성
    수동 데이터 + API 데이터 결합
    """
    forecast = SupplyForecast(region=region)

    # 1. 수동 데이터 로드
    curated = CURATED_SUPPLY.get(region, [])
    forecast.items = list(curated)

    # 2. API 데이터 보강 시도
    try:
        permits = fetch_housing_permits(region)
        for p in permits:
            if p["households"] > 100:  # 소규모 제외
                forecast.items.append(SupplyItem(
                    name=p.get("name", "인허가 단지"),
                    region=region,
                    households=p["households"],
                    expected_date=p.get("permit_date", "")[:4] if p.get("permit_date") else "",
                    supply_type="인허가",
                    status="인허가 완료",
                ))
    except Exception as e:
        print(f"[공급] API 데이터 보강 실패: {e}")

    # 3. 연도별 집계
    current_year = datetime.today().year
    for item in forecast.items:
        try:
            year = int(item.expected_date[:4]) if item.expected_date else 0
            if current_year <= year <= current_year + 3:
                forecast.yearly_breakdown[year] = forecast.yearly_breakdown.get(year, 0) + item.households
        except (ValueError, IndexError):
            pass

    # 4. 총 공급량 계산
    forecast.total_supply_3y = sum(forecast.yearly_breakdown.values())

    # 5. 리스크 수준 판단
    if forecast.total_supply_3y >= 5000:
        forecast.risk_level = "매우높음"
    elif forecast.total_supply_3y >= 3000:
        forecast.risk_level = "높음"
    elif forecast.total_supply_3y >= 1000:
        forecast.risk_level = "보통"
    else:
        forecast.risk_level = "낮음"

    # 6. 요약 텍스트
    forecast.summary = _build_summary(forecast)

    return forecast


def supply_to_newsletter_text(forecast: SupplyForecast) -> str:
    """뉴스레터용 공급 텍스트"""
    if not forecast.items:
        return ""

    lines = [f"향후 3년 예정 공급: 약 {forecast.total_supply_3y:,}세대 (리스크: {forecast.risk_level})"]
    for year, count in sorted(forecast.yearly_breakdown.items()):
        lines.append(f"  {year}년: {count:,}세대")
    for item in forecast.items[:3]:
        lines.append(f"  - {item.name} ({item.households:,}세대, {item.expected_date}, {item.supply_type})")
    return "\n".join(lines)


# ── 내부 유틸 ──────────────────────────────────────────────────

def _build_summary(forecast: SupplyForecast) -> str:
    if not forecast.items:
        return ""

    parts = []
    parts.append(f"향후 3년 약 {forecast.total_supply_3y:,}세대 공급 예정")

    if forecast.risk_level in ("높음", "매우높음"):
        parts.append("공급 과잉으로 가격 하방 압력 가능")
    elif forecast.risk_level == "낮음":
        parts.append("공급 부족으로 가격 지지력 있음")

    major = [i for i in forecast.items if i.households >= 1000]
    if major:
        names = ", ".join(i.name for i in major[:2])
        parts.append(f"대규모: {names}")

    return ". ".join(parts)


def _safe_int(val) -> int:
    try:
        return int(val) if val else 0
    except (ValueError, TypeError):
        return 0
