"""
collector/kakao.py
카카오맵 API로 임장 요소 수집
- 지하철 도보 거리
- 초등학교 배정/거리
- 주변 인프라 (마트, 학원 등)
- 강남역까지 대중교통 시간
"""

import requests
import time
from dataclasses import dataclass
from typing import Optional
import config


KAKAO_HEADERS = {"Authorization": f"KakaoAK {config.KAKAO_API_KEY}"}

# 강남역 좌표 (대중교통 시간 기준점)
GANGNAM_LAT = 37.4979502
GANGNAM_LNG = 127.0276368


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
    academy_count: int = 0             # 반경 500m 학원 수

    # 인프라
    has_large_mart: bool = False        # 대형마트 반경 1.5km
    nearest_mart: str = ""             # 마트명
    mart_walk_min: int = 0             # 도보 분
    hospital_count: int = 0            # 반경 1km 병원 수


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
    
    # 1. 주소 → 좌표 변환
    coords = _geocode(address or complex_name)
    if not coords:
        print(f"[경고] 좌표 변환 실패: {complex_name}")
        return None

    lat, lng = coords
    factors = LocationFactors(complex_name=complex_name, lat=lat, lng=lng)

    # 2. 각 요소 수집 (API 요청 간 딜레이)
    _fetch_subway(factors)
    time.sleep(0.3)

    _fetch_elementary(factors)
    time.sleep(0.3)

    _fetch_academy(factors)
    time.sleep(0.3)

    _fetch_mart(factors)
    time.sleep(0.3)

    _fetch_gangnam_transit(factors)

    return factors


def _geocode(query: str) -> Optional[tuple[float, float]]:
    """주소/단지명 → (위도, 경도)"""
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    resp = requests.get(url, headers=KAKAO_HEADERS, params={"query": query}, timeout=5)
    
    if resp.status_code != 200:
        return None
    
    docs = resp.json().get("documents", [])
    if docs:
        return float(docs[0]["y"]), float(docs[0]["x"])
    
    # 주소 검색 실패 시 키워드 검색으로 재시도
    url2 = "https://dapi.kakao.com/v2/local/search/keyword.json"
    resp2 = requests.get(url2, headers=KAKAO_HEADERS, params={"query": query}, timeout=5)
    docs2 = resp2.json().get("documents", [])
    if docs2:
        return float(docs2[0]["y"]), float(docs2[0]["x"])
    
    return None


def _search_nearby(lat: float, lng: float, keyword: str, radius: int) -> list[dict]:
    """반경 내 카카오맵 키워드 검색"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    params = {
        "query": keyword,
        "x": lng,
        "y": lat,
        "radius": radius,
        "sort": "distance",
    }
    resp = requests.get(url, headers=KAKAO_HEADERS, params=params, timeout=5)
    if resp.status_code == 200:
        return resp.json().get("documents", [])
    return []


def _walk_minutes(distance_m: float) -> int:
    """거리(m) → 도보 분 (성인 평균 80m/분)"""
    return max(1, round(distance_m / 80))


def _fetch_subway(factors: LocationFactors):
    """가장 가까운 지하철역 + 도보 시간"""
    places = _search_nearby(
        factors.lat, factors.lng,
        keyword="지하철역",
        radius=config.RADIUS_SUBWAY
    )
    if places:
        nearest = places[0]
        dist = float(nearest.get("distance", 0))
        # 역명에서 "(n호선)" 파싱 시도
        place_name = nearest.get("place_name", "")
        factors.nearest_subway = place_name.replace("역", "").strip()
        factors.subway_walk_min = _walk_minutes(dist)

        # 호선 정보 추출 (road_address_name에서 간단히)
        category = nearest.get("category_name", "")
        if "2호선" in category: factors.subway_line = "2호선"
        elif "5호선" in category: factors.subway_line = "5호선"
        elif "6호선" in category: factors.subway_line = "6호선"
        else: factors.subway_line = "지하철"


def _fetch_elementary(factors: LocationFactors):
    """가장 가까운 초등학교 + 도보 시간"""
    places = _search_nearby(
        factors.lat, factors.lng,
        keyword="초등학교",
        radius=config.RADIUS_SCHOOL
    )
    if places:
        nearest = places[0]
        dist = float(nearest.get("distance", 0))
        factors.nearest_elementary = nearest.get("place_name", "")
        factors.elementary_walk_min = _walk_minutes(dist)


def _fetch_academy(factors: LocationFactors):
    """반경 500m 내 학원 수"""
    places = _search_nearby(
        factors.lat, factors.lng,
        keyword="학원",
        radius=config.RADIUS_ACADEMY
    )
    factors.academy_count = len(places)


def _fetch_mart(factors: LocationFactors):
    """반경 1.5km 대형마트"""
    for keyword in ["이마트", "홈플러스", "롯데마트", "코스트코"]:
        places = _search_nearby(
            factors.lat, factors.lng,
            keyword=keyword,
            radius=config.RADIUS_MART
        )
        if places:
            nearest = places[0]
            dist = float(nearest.get("distance", 0))
            factors.has_large_mart = True
            factors.nearest_mart = nearest.get("place_name", keyword)
            factors.mart_walk_min = _walk_minutes(dist)
            break


def _fetch_gangnam_transit(factors: LocationFactors):
    """
    강남역까지 대중교통 소요 시간 (카카오 길찾기 API)
    ※ 카카오 길찾기 API는 유료 플랜 필요
    → MVP에서는 직선거리 기반 추정치 사용
    """
    import math

    # 직선거리 계산 (Haversine)
    R = 6371000  # 지구 반경 (m)
    lat1, lng1 = math.radians(factors.lat), math.radians(factors.lng)
    lat2, lng2 = math.radians(GANGNAM_LAT), math.radians(GANGNAM_LNG)
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlng/2)**2
    dist_m = R * 2 * math.asin(math.sqrt(a))

    # 대중교통 추정: 직선거리 × 1.4 / 평균 속도(400m/분) + 환승 여유 10분
    estimated_min = int(dist_m * 1.4 / 400) + 10
    factors.gangnam_transit_min = min(estimated_min, 90)  # 최대 90분 캡


def factors_to_dict(f: LocationFactors) -> dict:
    """프롬프트용 딕셔너리 변환"""
    return {
        "지하철역":      f"{f.nearest_subway}역 {f.subway_line}",
        "지하철_도보":   f"{f.subway_walk_min}분",
        "강남_대중교통": f"약 {f.gangnam_transit_min}분",
        "초등학교":      f.nearest_elementary,
        "초등학교_도보": f"{f.elementary_walk_min}분",
        "학원_수":       f"{f.academy_count}개",
        "대형마트":      f.nearest_mart if f.has_large_mart else "반경 1.5km 내 없음",
        "마트_도보":     f"{f.mart_walk_min}분" if f.has_large_mart else "-",
    }
