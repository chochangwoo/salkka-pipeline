"""
collector/kakao.py
임장 요소 수집 — 도로명주소 API + Haversine 기반

MVP 전략:
- 지오코딩: 도로명주소 API (행안부, 무료, 사업자 불필요)
- 거리 계산: Haversine 직선거리 공식
- 지하철역: 서울 주요역 좌표 DB 자체 보유
- 초등학교: 서울 주요 학교 좌표 DB 자체 보유
- 대형마트/학원: v2.2에서 네이버 장소 검색으로 추가 예정

※ 카카오맵 API: 2024.12.1부터 신규 앱 비즈니스 인증 필요 → MVP 제외
"""

import math
import requests
from dataclasses import dataclass
from typing import Optional
import config


# 강남역 좌표 (대중교통 시간 기준점)
GANGNAM_LAT = 37.4979502
GANGNAM_LNG = 127.0276368


# ── 서울 주요 지하철역 좌표 DB ─────────────────────────────────
# 마포구·서대문구·용산구·강남구 등 주요 지역 역
SUBWAY_STATIONS = {
    # 마포구
    "마포": {"lat": 37.5393, "lng": 126.9459, "line": "5호선"},
    "마포구청": {"lat": 37.5633, "lng": 126.9017, "line": "6호선"},
    "공덕": {"lat": 37.5440, "lng": 126.9518, "line": "5·6·경의선"},
    "홍대입구": {"lat": 37.5571, "lng": 126.9246, "line": "2호선"},
    "합정": {"lat": 37.5497, "lng": 126.9139, "line": "2·6호선"},
    "망원": {"lat": 37.5559, "lng": 126.9106, "line": "6호선"},
    "상수": {"lat": 37.5478, "lng": 126.9226, "line": "6호선"},
    "광흥창": {"lat": 37.5479, "lng": 126.9322, "line": "6호선"},
    "대흥": {"lat": 37.5477, "lng": 126.9429, "line": "6호선"},
    "애오개": {"lat": 37.5354, "lng": 126.9563, "line": "5호선"},
    "신촌": {"lat": 37.5554, "lng": 126.9369, "line": "2호선"},
    "이대": {"lat": 37.5568, "lng": 126.9459, "line": "2호선"},
    "디지털미디어시티": {"lat": 37.5760, "lng": 126.8997, "line": "6·경의선"},
    "월드컵경기장": {"lat": 37.5682, "lng": 126.8972, "line": "6호선"},
    # 용산구
    "용산": {"lat": 37.5299, "lng": 126.9648, "line": "1호선"},
    "삼각지": {"lat": 37.5345, "lng": 126.9728, "line": "4·6호선"},
    "녹사평": {"lat": 37.5344, "lng": 126.9874, "line": "6호선"},
    "이태원": {"lat": 37.5345, "lng": 126.9944, "line": "6호선"},
    "한강진": {"lat": 37.5397, "lng": 127.0018, "line": "6호선"},
    "효창공원앞": {"lat": 37.5389, "lng": 126.9611, "line": "6·경의선"},
    # 강남구
    "강남": {"lat": 37.4980, "lng": 127.0276, "line": "2호선"},
    "역삼": {"lat": 37.5007, "lng": 127.0365, "line": "2호선"},
    "선릉": {"lat": 37.5045, "lng": 127.0489, "line": "2호선"},
    "삼성": {"lat": 37.5088, "lng": 127.0631, "line": "2호선"},
    "압구정": {"lat": 37.5270, "lng": 127.0283, "line": "3호선"},
    "신사": {"lat": 37.5161, "lng": 127.0200, "line": "3호선"},
    "잠실": {"lat": 37.5133, "lng": 127.1002, "line": "2·8호선"},
    # 서초구
    "서초": {"lat": 37.4918, "lng": 127.0078, "line": "2호선"},
    "교대": {"lat": 37.4936, "lng": 127.0145, "line": "2·3호선"},
    "방배": {"lat": 37.4816, "lng": 126.9977, "line": "2호선"},
    # 성동구
    "왕십리": {"lat": 37.5612, "lng": 127.0379, "line": "2·5호선"},
    "한양대": {"lat": 37.5573, "lng": 127.0443, "line": "2호선"},
    "뚝섬": {"lat": 37.5474, "lng": 127.0472, "line": "2호선"},
    "성수": {"lat": 37.5446, "lng": 127.0557, "line": "2호선"},
    # 광진구
    "건대입구": {"lat": 37.5404, "lng": 127.0695, "line": "2·7호선"},
    "구의": {"lat": 37.5384, "lng": 127.0843, "line": "2호선"},
    "강변": {"lat": 37.5350, "lng": 127.0938, "line": "2호선"},
    # 송파구
    "잠실새내": {"lat": 37.5115, "lng": 127.0860, "line": "2호선"},
    "종합운동장": {"lat": 37.5106, "lng": 127.0735, "line": "2호선"},
    "석촌": {"lat": 37.5057, "lng": 127.1067, "line": "8·9호선"},
    "송파": {"lat": 37.5050, "lng": 127.1117, "line": "8호선"},
    "가락시장": {"lat": 37.4926, "lng": 127.1183, "line": "3·8호선"},
    # 노원구
    "노원": {"lat": 37.6562, "lng": 127.0617, "line": "4·7호선"},
    "상계": {"lat": 37.6611, "lng": 127.0731, "line": "4호선"},
    "중계": {"lat": 37.6447, "lng": 127.0639, "line": "7호선"},
    "하계": {"lat": 37.6389, "lng": 127.0583, "line": "7호선"},
    "마들": {"lat": 37.6496, "lng": 127.0507, "line": "7호선"},
    # 은평구
    "연신내": {"lat": 37.6190, "lng": 126.9212, "line": "3·6호선"},
    "불광": {"lat": 37.6108, "lng": 126.9296, "line": "3·6호선"},
    "역촌": {"lat": 37.6061, "lng": 126.9221, "line": "6호선"},
    "응암": {"lat": 37.5986, "lng": 126.9193, "line": "6호선"},
    "구산": {"lat": 37.5941, "lng": 126.9123, "line": "6호선"},
    # 서대문구
    "충정로": {"lat": 37.5599, "lng": 126.9634, "line": "2·5호선"},
    "서대문": {"lat": 37.5657, "lng": 126.9666, "line": "5호선"},
    "독립문": {"lat": 37.5729, "lng": 126.9601, "line": "3호선"},
    "홍제": {"lat": 37.5894, "lng": 126.9440, "line": "3호선"},
}

# ── 서울 주요 초등학교 좌표 DB ────────────────────────────────
# 주요 지역구 대표 초등학교
ELEMENTARY_SCHOOLS = {
    # 마포구
    "마포초등학교": {"lat": 37.5447, "lng": 126.9530},
    "용강초등학교": {"lat": 37.5410, "lng": 126.9435},
    "도화초등학교": {"lat": 37.5395, "lng": 126.9519},
    "염리초등학교": {"lat": 37.5428, "lng": 126.9440},
    "공덕초등학교": {"lat": 37.5459, "lng": 126.9536},
    "서강초등학교": {"lat": 37.5519, "lng": 126.9339},
    "성원초등학교": {"lat": 37.5557, "lng": 126.9168},
    "합정초등학교": {"lat": 37.5500, "lng": 126.9120},
    "망원초등학교": {"lat": 37.5550, "lng": 126.9047},
    "신석초등학교": {"lat": 37.5678, "lng": 126.9103},
    "성산초등학교": {"lat": 37.5660, "lng": 126.9145},
    # 강남구
    "개포초등학교": {"lat": 37.4826, "lng": 127.0453},
    "대치초등학교": {"lat": 37.4946, "lng": 127.0573},
    "역삼초등학교": {"lat": 37.5020, "lng": 127.0405},
    # 서초구
    "서초초등학교": {"lat": 37.4910, "lng": 127.0122},
    "반포초등학교": {"lat": 37.5060, "lng": 127.0063},
    # 송파구
    "잠실초등학교": {"lat": 37.5107, "lng": 127.0826},
    "풍납초등학교": {"lat": 37.5277, "lng": 127.1113},
    # 용산구
    "용산초등학교": {"lat": 37.5305, "lng": 126.9671},
    "보광초등학교": {"lat": 37.5320, "lng": 127.0003},
    # 성동구
    "금호초등학교": {"lat": 37.5564, "lng": 127.0207},
    "행당초등학교": {"lat": 37.5572, "lng": 127.0312},
    # 노원구
    "노원초등학교": {"lat": 37.6540, "lng": 127.0660},
    "상계초등학교": {"lat": 37.6580, "lng": 127.0680},
    # 은평구
    "은평초등학교": {"lat": 37.6120, "lng": 126.9280},
    "불광초등학교": {"lat": 37.6130, "lng": 126.9340},
    # 서대문구
    "서대문초등학교": {"lat": 37.5720, "lng": 126.9580},
    "북성초등학교": {"lat": 37.5766, "lng": 126.9624},
    # 광진구
    "광장초등학교": {"lat": 37.5390, "lng": 127.0920},
    "구의초등학교": {"lat": 37.5420, "lng": 127.0830},
}


@dataclass
class LocationFactors:
    """단지 임장 요소 데이터"""
    complex_name: str
    lat: float
    lng: float

    # 교통
    nearest_subway: str = ""            # 가장 가까운 지하철역명
    subway_line: str = ""               # 호선
    subway_walk_min: int = 0            # 도보 분

    # 강남 출근
    gangnam_transit_min: int = 0        # 강남역까지 대중교통 분

    # 학군
    nearest_elementary: str = ""        # 가장 가까운 초등학교
    elementary_walk_min: int = 0        # 도보 분
    academy_count: int = 0             # 반경 500m 학원 수 (v2.2 예정)

    # 인프라
    has_large_mart: bool = False        # 대형마트 반경 1.5km (v2.2 예정)
    nearest_mart: str = ""             # 마트명
    mart_walk_min: int = 0             # 도보 분
    hospital_count: int = 0            # 반경 1km 병원 수


# ── Haversine 거리 계산 ──────────────────────────────────────

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 직선거리 (미터)"""
    R = 6371000
    rlat1, rlng1 = math.radians(lat1), math.radians(lng1)
    rlat2, rlng2 = math.radians(lat2), math.radians(lng2)
    dlat = rlat2 - rlat1
    dlng = rlng2 - rlng1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _walk_minutes(distance_m: float) -> int:
    """거리(m) → 도보 분 (성인 평균 80m/분)"""
    return max(1, round(distance_m / 80))


# ── 도로명주소 API 지오코딩 ──────────────────────────────────

def _geocode(query: str) -> Optional[tuple[float, float]]:
    """
    도로명주소 API로 주소 → (위도, 경도) 변환
    https://business.juso.go.kr/addrlink/openApi/apiExprn.do

    API 키가 없으면 단지명 기반 좌표 DB 매칭으로 폴백
    """
    if not config.JUSO_API_KEY:
        print("[경고] JUSO_API_KEY 미설정 — 좌표 DB 폴백 사용")
        return _geocode_fallback(query)

    url = "https://business.juso.go.kr/addrlink/addrCoordApi.do"
    params = {
        "confmKey":   config.JUSO_API_KEY,
        "resultType": "json",
        "admCd":      "",
        "keyword":    query,
        "currentPage": "1",
        "countPerPage": "1",
    }

    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", {}).get("juso", [])
            if results:
                addr = results[0]
                # 도로명주소 API 좌표계 변환 (entX, entY → WGS84)
                if addr.get("entX") and addr.get("entY"):
                    return float(addr["entY"]), float(addr["entX"])

        # 주소 검색 실패 시 좌표 DB 폴백
        return _geocode_fallback(query)

    except requests.RequestException as e:
        print(f"[경고] 도로명주소 API 실패: {e}")
        return _geocode_fallback(query)


def _geocode_fallback(query: str) -> Optional[tuple[float, float]]:
    """
    API 실패 시 지역구 중심 좌표로 폴백
    정밀도는 떨어지지만 Haversine 추정값은 생성 가능
    """
    DISTRICT_CENTERS = {
        "마포구":   (37.5633, 126.9082),
        "강남구":   (37.5172, 127.0473),
        "서초구":   (37.4837, 127.0324),
        "송파구":   (37.5145, 127.1060),
        "용산구":   (37.5324, 126.9907),
        "성동구":   (37.5634, 127.0369),
        "광진구":   (37.5384, 127.0822),
        "노원구":   (37.6542, 127.0568),
        "은평구":   (37.6027, 126.9291),
        "서대문구": (37.5791, 126.9368),
    }
    for district, coords in DISTRICT_CENTERS.items():
        if district in query:
            print(f"[폴백] {district} 중심 좌표 사용")
            return coords
    return None


# ── 임장 요소 수집 ───────────────────────────────────────────

def get_location_factors(
    complex_name: str,
    address: str
) -> Optional[LocationFactors]:
    """
    단지명 + 주소로 임장 요소 전체 수집

    Args:
        complex_name: 단지명
        address: 도로명 주소
    Returns:
        LocationFactors 또는 None
    """
    print(f"[임장] {complex_name} 위치 정보 수집 중...")

    # 1. 주소 → 좌표 변환 (도로명주소 API)
    coords = _geocode(address or complex_name)
    if not coords:
        print(f"[경고] 좌표 변환 실패: {complex_name}")
        return None

    lat, lng = coords
    factors = LocationFactors(complex_name=complex_name, lat=lat, lng=lng)

    # 2. 좌표 DB 기반 임장 요소 수집 (API 호출 불필요)
    _fetch_subway(factors)
    _fetch_elementary(factors)
    _fetch_gangnam_transit(factors)

    # 3. 학원·마트는 v2.2에서 네이버 장소 검색으로 추가 예정
    # factors.academy_count, factors.has_large_mart 등은 기본값 유지

    return factors


def _fetch_subway(factors: LocationFactors):
    """자체 좌표 DB에서 가장 가까운 지하철역 찾기"""
    min_dist = float("inf")
    nearest_name = ""
    nearest_line = ""

    for name, info in SUBWAY_STATIONS.items():
        dist = _haversine(factors.lat, factors.lng, info["lat"], info["lng"])
        if dist < min_dist:
            min_dist = dist
            nearest_name = name
            nearest_line = info["line"]

    if nearest_name and min_dist <= config.RADIUS_SUBWAY:
        factors.nearest_subway = nearest_name
        factors.subway_line = nearest_line
        factors.subway_walk_min = _walk_minutes(min_dist)
    elif nearest_name:
        # 반경 밖이라도 가장 가까운 역 정보 제공
        factors.nearest_subway = nearest_name
        factors.subway_line = nearest_line
        factors.subway_walk_min = _walk_minutes(min_dist)


def _fetch_elementary(factors: LocationFactors):
    """자체 좌표 DB에서 가장 가까운 초등학교 찾기"""
    min_dist = float("inf")
    nearest_name = ""

    for name, info in ELEMENTARY_SCHOOLS.items():
        dist = _haversine(factors.lat, factors.lng, info["lat"], info["lng"])
        if dist < min_dist:
            min_dist = dist
            nearest_name = name

    if nearest_name and min_dist <= config.RADIUS_SCHOOL:
        factors.nearest_elementary = nearest_name
        factors.elementary_walk_min = _walk_minutes(min_dist)
    elif nearest_name:
        factors.nearest_elementary = nearest_name
        factors.elementary_walk_min = _walk_minutes(min_dist)


def _fetch_gangnam_transit(factors: LocationFactors):
    """강남역까지 대중교통 소요 시간 추정 (Haversine 기반)"""
    dist_m = _haversine(factors.lat, factors.lng, GANGNAM_LAT, GANGNAM_LNG)

    # 대중교통 추정: 직선거리 × 1.4(우회계수) / 400m/분(평균속도) + 환승 10분
    estimated_min = int(dist_m * 1.4 / 400) + 10
    factors.gangnam_transit_min = min(estimated_min, 90)  # 최대 90분 캡


def factors_to_dict(f: LocationFactors) -> dict:
    """프롬프트용 딕셔너리 변환"""
    return {
        "지하철역":      f"{f.nearest_subway}역 {f.subway_line}" if f.nearest_subway else "정보 없음",
        "지하철_도보":   f"{f.subway_walk_min}분" if f.nearest_subway else "-",
        "강남_대중교통": f"약 {f.gangnam_transit_min}분",
        "초등학교":      f.nearest_elementary or "정보 없음",
        "초등학교_도보": f"{f.elementary_walk_min}분" if f.nearest_elementary else "-",
        "학원_수":       f"{f.academy_count}개" if f.academy_count else "조사 중 (v2.2)",
        "대형마트":      f.nearest_mart if f.has_large_mart else "조사 중 (v2.2)",
        "마트_도보":     f"{f.mart_walk_min}분" if f.has_large_mart else "-",
    }
