"""
premium/detector.py
유료 구독자 전용 — 급매 감지 / 전세가율 위험 / 단지 비교

모든 감지 로직은 API 호출 없이 수집된 데이터 기반으로 동작.
GPT 해설은 premium/analyzer.py에서 별도 처리.
"""

from datetime import datetime
from collections import defaultdict
from collector.molit import TradeRecord


# ── 급매 감지 ────────────────────────────────────────────────

def detect_urgent_sales(
    trades: list[TradeRecord],
    drop_threshold: float = 0.05,
) -> list[dict]:
    """
    직전 거래 대비 N% 이상 하락한 거래를 감지

    Args:
        trades: 전체 실거래 데이터
        drop_threshold: 급매 판정 기준 (기본 5%)
    Returns:
        [{"trade": TradeRecord, "prev_price": int, "drop_rate": float, "urgency": str}]
    """
    # 단지별 + 면적대별로 거래 그룹핑
    groups = defaultdict(list)
    for t in trades:
        area_key = _area_bracket(t.area)
        groups[(t.complex_name, area_key)].append(t)

    urgent_sales = []

    for key, group in groups.items():
        # 날짜순 정렬
        sorted_trades = sorted(group, key=lambda x: x.trade_date)
        if len(sorted_trades) < 2:
            continue

        latest = sorted_trades[-1]
        prev = sorted_trades[-2]

        if prev.price <= 0:
            continue

        drop_rate = (prev.price - latest.price) / prev.price

        if drop_rate >= drop_threshold:
            urgency = "HIGH" if drop_rate >= 0.08 else "MEDIUM"
            urgent_sales.append({
                "trade":      latest,
                "prev_price": prev.price,
                "drop_rate":  round(drop_rate, 4),
                "urgency":    urgency,
            })

    # 긴급도 → 하락률 순 정렬
    urgent_sales.sort(key=lambda x: x["drop_rate"], reverse=True)
    return urgent_sales[:3]  # 최대 3건


# ── 전세가율 위험 경보 ───────────────────────────────────────

def detect_jeonse_risk(
    jeonse_data: list[dict],
    danger_threshold: float = 0.80,
    caution_threshold: float = 0.70,
) -> list[dict]:
    """
    전세가율이 위험 수준인 단지 감지

    Args:
        jeonse_data: [{"complex_name": str, "jeonse_rate": float, "매매가": int, "전세가": int}]
        danger_threshold: DANGER 기준 (기본 80%)
        caution_threshold: CAUTION 기준 (기본 70%)
    Returns:
        [{"complex_name": str, "jeonse_rate": float, "level": str}]
    """
    risks = []

    for item in jeonse_data:
        rate = item.get("jeonse_rate", 0)
        if rate >= danger_threshold:
            level = "DANGER"
        elif rate >= caution_threshold:
            level = "CAUTION"
        else:
            continue

        risks.append({
            "complex_name": item["complex_name"],
            "jeonse_rate":  round(rate, 4),
            "sale_price":   item.get("매매가", 0),
            "jeonse_price": item.get("전세가", 0),
            "level":        level,
        })

    # DANGER 우선 정렬
    risks.sort(key=lambda x: (0 if x["level"] == "DANGER" else 1, -x["jeonse_rate"]))
    return risks[:2]  # 최대 2건


# ── 단지 비교 리포트 ─────────────────────────────────────────

def compare_complexes(
    trades: list[TradeRecord],
    target_complexes: list[str],
) -> list[dict]:
    """
    지정된 단지들의 가격 이력 비교 (매월 첫째 주 실행)

    Args:
        trades: 전체 실거래 데이터
        target_complexes: 비교 대상 단지명 리스트
    Returns:
        [{"complex_name": str, "current_price": int, "peak_price": int,
          "drop_from_peak": float, "trend": str, "trade_count": int}]
    """
    results = []

    for name in target_complexes:
        # 해당 단지 84㎡ 거래만 필터
        complex_trades = sorted(
            [t for t in trades if t.complex_name == name and 80 <= t.area <= 90],
            key=lambda x: x.trade_date
        )

        if not complex_trades:
            continue

        current = complex_trades[-1]
        peak_price = max(t.price for t in complex_trades)
        drop_from_peak = (peak_price - current.price) / peak_price if peak_price > 0 else 0

        # 최근 3건 기준 추세 판단
        recent_3 = complex_trades[-3:] if len(complex_trades) >= 3 else complex_trades
        if len(recent_3) >= 2:
            if recent_3[-1].price > recent_3[0].price:
                trend = "상승"
            elif recent_3[-1].price < recent_3[0].price:
                trend = "하락"
            else:
                trend = "보합"
        else:
            trend = "데이터 부족"

        results.append({
            "complex_name":  name,
            "current_price": current.price,
            "current_trade": current,
            "peak_price":    peak_price,
            "drop_from_peak": round(drop_from_peak, 4),
            "trend":         trend,
            "trade_count":   len(complex_trades),
        })

    return results


# ── 유틸리티 ─────────────────────────────────────────────────

def _area_bracket(area: float) -> str:
    """면적 → 평형대 분류"""
    if 80 <= area <= 90:
        return "84"
    elif 55 <= area <= 65:
        return "59"
    elif 40 <= area <= 50:
        return "44"
    else:
        return str(int(area))
