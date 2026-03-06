"""
collector/molit.py
국토부 실거래가 API로 아파트 매매 데이터 수집
공식 API: https://api.data.go.kr/openapi/tn_pubr_public_aptTrade_info_api
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
    months: int = 1
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

    for i in range(months):
        target = today - timedelta(days=30 * i)
        ym = target.strftime("%Y%m")  # 예: "202503"
        
        params = {
            "serviceKey":   config.MOLIT_API_KEY,
            "pageNo":       "1",
            "numOfRows":    "100",
            "LAWD_CD":      _get_lawd_cd(region),   # 법정동 코드
            "DEAL_YMD":     ym,
        }

        url = "http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTrade"
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            records.extend(_parse_xml(resp.text, region))
            print(f"[수집] {ym} {region}: {len(records)}건")
        except requests.RequestException as e:
            print(f"[오류] 국토부 API 요청 실패: {e}")

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


def _get_lawd_cd(region: str) -> str:
    """
    지역구 → 법정동 코드 변환
    실제 운영 시 전체 코드 테이블로 확장 필요
    """
    CODE_MAP = {
        "마포구":   "11440",
        "강남구":   "11680",
        "서초구":   "11650",
        "송파구":   "11710",
        "용산구":   "11170",
        "성동구":   "11200",
        "광진구":   "11215",
        "노원구":   "11350",
        "은평구":   "11380",
        "서대문구": "11410",
    }
    return CODE_MAP.get(region, "11440")  # 기본값: 마포구
