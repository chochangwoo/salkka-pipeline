"""
collector/molit.py
국토부 실거래가 API로 아파트 매매 데이터 수집
사용 API: 15126468 — 아파트 매매 실거래가 상세 자료
https://www.data.go.kr/data/15126468/openapi.do
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
import config


@dataclass
class TradeRecord:
    """실거래 단건 데이터"""
    complex_name: str           # 단지명
    district: str               # 법정동
    area: float                 # 전용면적 (㎡)
    floor: int                  # 층
    price: int                  # 거래금액 (만원)
    trade_date: str             # 거래일 (YYYY-MM-DD)
    build_year: int             # 건축연도
    road_name: str              # 도로명
    lat: Optional[float] = None # 위도 (카카오 API로 추가)
    lng: Optional[float] = None # 경도 (카카오 API로 추가)


def fetch_trades(
    region: str = config.TARGET_REGION,
    months: int = 2
) -> list[TradeRecord]:
    """
    최근 N개월 실거래 데이터 수집
    
    Args:
        region: 조회 지역구 (예: "마포구")
        months: 조회 개월 수
    Returns:
        TradeRecord 리스트
    """
    records = []
    today = datetime.today()
    lawd_codes = _get_lawd_cd(region)

    url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"

    for i in range(months):
        target = today - timedelta(days=30 * i)
        ym = target.strftime("%Y%m")

        for code in lawd_codes:
            params = {
                "serviceKey":   config.MOLIT_API_KEY,
                "pageNo":       "1",
                "numOfRows":    "100",
                "LAWD_CD":      code,
                "DEAL_YMD":     ym,
            }

            try:
                resp = requests.get(url, params=params, timeout=10)
                resp.raise_for_status()
                records.extend(_parse_xml(resp.text, region))
            except requests.RequestException as e:
                print(f"[오류] 국토부 API 요청 실패 ({code}): {e}")

        print(f"[수집] {ym} {region}: {len(records)}건")

    return records


def _parse_xml(xml_text: str, region: str) -> list[TradeRecord]:
    """XML 응답 파싱"""
    records = []
    try:
        root = ET.fromstring(xml_text)
        items = root.findall(".//item")
        
        for item in items:
            def get(tag):
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else ""

            try:
                price_str = get("dealAmount").replace(",", "")
                records.append(TradeRecord(
                    complex_name = get("aptNm"),
                    district     = get("umdNm"),
                    area         = float(get("excluUseAr") or 0),
                    floor        = int(get("floor") or 0),
                    price        = int(price_str) if price_str else 0,
                    trade_date   = f"{get('dealYear')}-{get('dealMonth').zfill(2)}-{get('dealDay').zfill(2)}",
                    build_year   = int(get("buildYear") or 0),
                    road_name    = get("roadNm"),
                ))
            except (ValueError, TypeError) as e:
                print(f"[경고] 파싱 실패 항목 스킵: {e}")
                continue

    except ET.ParseError as e:
        print(f"[오류] XML 파싱 실패: {e}")
    
    return records


def get_weekly_summary(records: list[TradeRecord]) -> dict:
    """
    주간 통계 요약 계산
    - 거래량, 평균가, 평형대별 통계
    """
    if not records:
        return {}

    # 최근 7일 필터
    cutoff = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    weekly = [r for r in records if r.trade_date >= cutoff]

    if not weekly:
        weekly = records  # 데이터 없으면 전체 사용

    # 84㎡ 전후 필터 (실수요자 관심 평형)
    apt84 = [r for r in weekly if 80 <= r.area <= 90]
    apt59 = [r for r in weekly if 55 <= r.area <= 65]

    def avg_price(lst):
        return int(sum(r.price for r in lst) / len(lst)) if lst else 0

    return {
        "total_count":      len(weekly),
        "avg_price_84":     avg_price(apt84),
        "avg_price_59":     avg_price(apt59),
        "max_price":        max((r.price for r in weekly), default=0),
        "min_price":        min((r.price for r in weekly), default=0),
        "trade_dates":      sorted(set(r.trade_date for r in weekly)),
        "complexes":        list(set(r.complex_name for r in weekly)),
    }


def get_notable_trades(records: list[TradeRecord], top_n: int = 2) -> list[TradeRecord]:
    """
    주목할 거래 선정
    - 거래량 많은 단지 우선
    - 84㎡ 기준
    """
    apt84 = [r for r in records if 80 <= r.area <= 90]
    
    # 단지별 거래 빈도 계산
    from collections import Counter
    complex_counts = Counter(r.complex_name for r in apt84)
    top_complexes = [name for name, _ in complex_counts.most_common(top_n)]
    
    result = []
    for name in top_complexes:
        # 해당 단지 최신 거래 1건
        trades = sorted(
            [r for r in apt84 if r.complex_name == name],
            key=lambda x: x.trade_date,
            reverse=True
        )
        if trades:
            result.append(trades[0])
    
    return result


def _get_lawd_cd(region: str) -> list[str]:
    """
    지역명 → 법정동 코드 리스트 변환
    경기도 시 중 구가 있는 경우 모든 구 코드를 반환
    """
    CODE_MAP = {
        # ── 서울특별시 (25구) ──
        "강남구":   ["11680"],
        "강동구":   ["11740"],
        "강북구":   ["11305"],
        "강서구":   ["11500"],
        "관악구":   ["11620"],
        "광진구":   ["11215"],
        "구로구":   ["11530"],
        "금천구":   ["11545"],
        "노원구":   ["11350"],
        "도봉구":   ["11320"],
        "동대문구": ["11230"],
        "동작구":   ["11590"],
        "마포구":   ["11440"],
        "서대문구": ["11410"],
        "서초구":   ["11650"],
        "성동구":   ["11200"],
        "성북구":   ["11290"],
        "송파구":   ["11710"],
        "양천구":   ["11470"],
        "영등포구": ["11560"],
        "용산구":   ["11170"],
        "은평구":   ["11380"],
        "종로구":   ["11110"],
        "중구":     ["11140"],
        "중랑구":   ["11260"],
        # ── 경기도 (28시) ──
        "고양시":   ["41281", "41285", "41287"],  # 덕양·일산동·일산서
        "과천시":   ["41290"],
        "광명시":   ["41210"],
        "광주시":   ["41610"],
        "구리시":   ["41310"],
        "군포시":   ["41410"],
        "김포시":   ["41570"],
        "남양주시": ["41360"],
        "동두천시": ["41250"],
        "부천시":   ["41190"],
        "성남시":   ["41131", "41133", "41135"],  # 수정·중원·분당
        "수원시":   ["41111", "41113", "41115", "41117"],  # 장안·권선·팔달·영통
        "시흥시":   ["41390"],
        "안산시":   ["41271", "41273"],  # 상록·단원
        "안성시":   ["41550"],
        "안양시":   ["41171", "41173"],  # 만안·동안
        "양주시":   ["41630"],
        "여주시":   ["41670"],
        "오산시":   ["41370"],
        "용인시":   ["41461", "41463", "41465"],  # 처인·기흥·수지
        "의왕시":   ["41430"],
        "의정부시": ["41150"],
        "이천시":   ["41500"],
        "파주시":   ["41480"],
        "평택시":   ["41220"],
        "포천시":   ["41650"],
        "하남시":   ["41450"],
        "화성시":   ["41590"],
    }
    return CODE_MAP.get(region, ["11440"])
