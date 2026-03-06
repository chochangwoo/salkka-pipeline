"""
analyzer/gpt.py
OpenAI GPT API로 AI 분석 실행
- 비용 전략: 단순 정리는 gpt-4o-mini, 핵심 서술은 gpt-4o
"""

from openai import OpenAI
from prompts.templates import (
    COMPLEX_DESCRIPTION_SYSTEM, COMPLEX_DESCRIPTION_USER,
    TIMING_SIGNAL_SYSTEM,       TIMING_SIGNAL_USER,
    EDITOR_SUMMARY_SYSTEM,      EDITOR_SUMMARY_USER,
    MARKET_SUMMARY_SYSTEM,      MARKET_SUMMARY_USER,
)
from collector.molit import TradeRecord, get_weekly_summary
from collector.kakao import LocationFactors, factors_to_dict
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)


# ── 공통 GPT 호출 ─────────────────────────────────────────────

def _call_gpt(system: str, user: str, model: str = None) -> str:
    """
    GPT API 단일 호출
    
    Args:
        system: 시스템 프롬프트
        user:   유저 프롬프트
        model:  사용 모델 (None이면 config 기본값)
    Returns:
        생성된 텍스트
    """
    model = model or config.GPT_MODEL_MAIN
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system",  "content": system},
                {"role": "user",    "content": user},
            ],
            max_tokens=config.GPT_MAX_TOKENS,
            temperature=config.GPT_TEMPERATURE,
        )
        text = response.choices[0].message.content.strip()
        
        # 사용량 로깅 (비용 추적)
        usage = response.usage
        print(f"[GPT/{model}] 입력:{usage.prompt_tokens} / 출력:{usage.completion_tokens} 토큰")
        
        return text

    except Exception as e:
        print(f"[오류] GPT 호출 실패 ({model}): {e}")
        return ""


# ── 분석 함수들 ───────────────────────────────────────────────

def analyze_complex(
    trade: TradeRecord,
    factors: LocationFactors,
    prev_price: int = 0,
    special_notes: str = "없음"
) -> str:
    """
    단지 임장 서술 생성 (gpt-4o 사용 — 품질 중요)
    
    Args:
        trade:         실거래 데이터
        factors:       임장 요소 데이터
        prev_price:    직전 거래가 (만원)
        special_notes: 개발호재/리스크 등 특이사항
    Returns:
        임장 서술 텍스트
    """
    # 가격 변동 계산
    if prev_price and prev_price > 0:
        diff = trade.price - prev_price
        sign = "+" if diff > 0 else ""
        price_change = f"{sign}{diff//10000}천만원 ({sign}{diff/prev_price*100:.1f}%)"
    else:
        price_change = "직전 거래 데이터 없음"

    # 임장 요소 딕셔너리
    f_dict = factors_to_dict(factors)

    user_prompt = COMPLEX_DESCRIPTION_USER.format(
        complex_name  = trade.complex_name,
        price         = f"{trade.price / 10000:.1f}",
        area          = trade.area,
        floor         = trade.floor,
        trade_date    = trade.trade_date,
        price_change  = price_change,
        special_notes = special_notes,
        **f_dict
    )

    # 임장 서술은 gpt-4o (품질 우선)
    return _call_gpt(
        system = COMPLEX_DESCRIPTION_SYSTEM,
        user   = user_prompt,
        model  = config.GPT_MODEL_WRITER
    )


def analyze_timing(
    summary: dict,
    region: str = config.TARGET_REGION,
    jeonse_rate: float = 0.0,
    interest_rate: str = "동결",
    unsold: int = 0,
) -> dict:
    """
    타이밍 신호 판단 생성 (gpt-4o-mini — 구조화 출력)
    
    Returns:
        {"signal": str, "reason": str, "hint": str}
    """
    user_prompt = TIMING_SIGNAL_USER.format(
        region          = region,
        total_count     = summary.get("total_count", 0),
        count_change    = "데이터 준비 중",       # TODO: 전주 대비 계산
        avg_price_84    = f"{summary.get('avg_price_84', 0) / 10000:.1f}",
        price_from_peak = "집계 중",              # TODO: 고점 대비 계산
        jeonse_rate     = jeonse_rate,
        jeonse_change   = "집계 중",              # TODO: 전월 대비
        unsold          = unsold,
        unsold_change   = "집계 중",
        interest_rate   = interest_rate,
        urgent_sale     = "확인 중",
    )

    raw = _call_gpt(
        system = TIMING_SIGNAL_SYSTEM,
        user   = user_prompt,
        model  = config.GPT_MODEL_MAIN  # mini로 충분
    )

    # 간단한 파싱 (신호 / 근거 / 힌트 분리)
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    result = {"signal": "", "reason": "", "hint": "", "raw": raw}

    for line in lines:
        if line.startswith("신호"):
            result["signal"] = line.split(":", 1)[-1].strip()
        elif line.startswith("근거"):
            result["reason"] = line.split(":", 1)[-1].strip()
        elif line.startswith("힌트"):
            result["hint"] = line.split(":", 1)[-1].strip()

    # 파싱 실패 시 raw 텍스트 그대로 사용
    if not result["signal"]:
        result["signal"] = "조심스런 매수 고려"
        result["reason"] = raw

    return result


def generate_editor_summary(
    region: str,
    market_mood: str,
    timing_signal: str,
    notable_complex: str,
    special_issue: str = "없음"
) -> str:
    """
    편집장 총평 생성 (gpt-4o — 브랜드 톤 중요)
    """
    user_prompt = EDITOR_SUMMARY_USER.format(
        region          = region,
        market_mood     = market_mood,
        timing_signal   = timing_signal,
        notable_complex = notable_complex,
        special_issue   = special_issue,
    )

    return _call_gpt(
        system = EDITOR_SUMMARY_SYSTEM,
        user   = user_prompt,
        model  = config.GPT_MODEL_WRITER  # 4o (톤 품질 중요)
    )


def generate_market_summary(
    summary: dict,
    region: str = config.TARGET_REGION,
    jeonse_rate: float = 0.0,
) -> str:
    """
    시장 온도계 한 줄 요약 (gpt-4o-mini — 단순 요약)
    """
    user_prompt = MARKET_SUMMARY_USER.format(
        region       = region,
        total_count  = summary.get("total_count", 0),
        avg_price_84 = f"{summary.get('avg_price_84', 0) / 10000:.1f}",
        avg_price_59 = f"{summary.get('avg_price_59', 0) / 10000:.1f}",
        max_price    = f"{summary.get('max_price', 0) / 10000:.1f}",
        jeonse_rate  = jeonse_rate,
    )

    return _call_gpt(
        system = MARKET_SUMMARY_SYSTEM,
        user   = user_prompt,
        model  = config.GPT_MODEL_MAIN  # mini로 충분
    )
