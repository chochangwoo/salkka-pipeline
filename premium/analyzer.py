"""
premium/analyzer.py
유료 구독자 전용 GPT 분석

모든 유료 분석은 gpt-4o 사용 (품질 우선, 유료 가치 증명)
"""

from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)


def _call_gpt_premium(system: str, user: str) -> str:
    """유료 전용 GPT 호출 — 항상 gpt-4o 사용"""
    try:
        response = client.chat.completions.create(
            model=config.GPT_MODEL_WRITER,  # gpt-4o (품질 우선)
            messages=[
                {"role": "system",  "content": system},
                {"role": "user",    "content": user},
            ],
            max_tokens=config.GPT_MAX_TOKENS,
            temperature=config.GPT_TEMPERATURE,
        )
        text = response.choices[0].message.content.strip()
        usage = response.usage
        print(f"[GPT/premium/{config.GPT_MODEL_WRITER}] 입력:{usage.prompt_tokens} / 출력:{usage.completion_tokens} 토큰")
        return text
    except Exception as e:
        print(f"[오류] 유료 GPT 호출 실패: {e}")
        return ""


# ── 급매 해설 ────────────────────────────────────────────────

URGENT_SALE_SYSTEM = """
당신은 부동산 실거래가 분석 전문가입니다.
급매로 판단되는 거래에 대해 실수요자에게 유용한 해설을 작성합니다.

원칙:
- 급락 이유 가능성을 객관적으로 분석 (시장 상황 / 개인 사정 / 하자 우려)
- 실수요자 관심 여부를 냉정하게 판단
- 확인해야 할 사항 2~3가지 제시
- 과도한 추천이나 공포 유발 금지
- 200자 내외
""".strip()


def analyze_urgent_sale(sale: dict) -> str:
    """급매 거래 GPT 해설"""
    trade = sale["trade"]
    user_prompt = f"""
다음 급매 거래를 분석해줘.

단지명: {trade.complex_name}
거래가: {trade.price / 10000:.1f}억원 (전용 {trade.area}㎡, {trade.floor}층)
거래일: {trade.trade_date}
직전 거래가: {sale['prev_price'] / 10000:.1f}억원
하락률: {sale['drop_rate'] * 100:.1f}%
긴급도: {sale['urgency']}

출력: 급락 가능성 분석 + 실수요자 관점 판단 + 확인 사항 2~3개
""".strip()

    return _call_gpt_premium(URGENT_SALE_SYSTEM, user_prompt)


# ── 전세가율 위험 해설 ───────────────────────────────────────

JEONSE_RISK_SYSTEM = """
당신은 전세 시장 분석 전문가입니다.
전세가율이 위험 수준인 단지에 대해 세입자 관점과 매수 희망자 관점 모두를 설명합니다.

원칙:
- 역전세 위험의 실질적 의미를 쉽게 설명
- 세입자 관점: 전세금 반환 리스크
- 매수 희망자 관점: 갭투자 위험 vs 실수요자 기회
- 공포 유발 금지, 객관적 분석
- 200자 내외
""".strip()


def analyze_jeonse_risk(risk: dict) -> str:
    """전세가율 위험 GPT 해설"""
    user_prompt = f"""
다음 전세가율 위험 단지를 분석해줘.

단지명: {risk['complex_name']}
전세가율: {risk['jeonse_rate'] * 100:.1f}%
매매가: {risk.get('sale_price', 0) / 10000:.1f}억원
전세가: {risk.get('jeonse_price', 0) / 10000:.1f}억원
위험 등급: {risk['level']}

세입자 관점과 매수 희망자 관점 각각 설명해줘.
""".strip()

    return _call_gpt_premium(JEONSE_RISK_SYSTEM, user_prompt)


# ── 단지 비교 해설 ───────────────────────────────────────────

COMPARISON_SYSTEM = """
당신은 부동산 단지 비교 전문가입니다.
여러 단지의 가격 이력을 비교해 실수요자에게 맞는 선택지를 제안합니다.

원칙:
- 각 단지의 장단점을 객관적으로 비교
- "A단지는 ~한 분께, B단지는 ~한 분께 더 맞습니다" 형태로 마무리
- 투자 권유 금지, 실거주 관점에서 분석
- 300자 내외
""".strip()


def analyze_comparison(histories: list[dict]) -> str:
    """단지 비교 GPT 해설"""
    comparison_text = ""
    for h in histories:
        comparison_text += f"""
- {h['complex_name']}: 현재 {h['current_price'] / 10000:.1f}억원, 고점 대비 -{h['drop_from_peak'] * 100:.1f}%, 추세 {h['trend']}, 거래 {h['trade_count']}건
"""

    user_prompt = f"""
다음 단지들을 비교 분석해줘.

{comparison_text}

각 단지의 특징을 비교하고, 어떤 실수요자에게 맞는지 제안해줘.
""".strip()

    return _call_gpt_premium(COMPARISON_SYSTEM, user_prompt)


# ── Q&A 답변 ────────────────────────────────────────────────

QNA_SYSTEM = """
당신은 부동산 뉴스레터 "살까말까"의 전문 상담사입니다.
유료 구독자의 질문에 정확하고 유용한 답변을 제공합니다.

원칙:
- 데이터 기반 답변 (가능한 경우 실거래가 언급)
- 직접적 매수/매도 권유 금지
- "~한 상황이라면 ~를 고려해볼 수 있습니다" 형태
- 확인해야 할 사항 1~2가지 추가
- 200자 내외
""".strip()


def answer_subscriber_question(question: str, context: str = "") -> str:
    """구독자 Q&A 답변 생성"""
    user_prompt = f"""
구독자 질문: {question}

{f'참고 데이터: {context}' if context else ''}

실수요자 관점에서 도움이 되는 답변을 작성해줘.
""".strip()

    return _call_gpt_premium(QNA_SYSTEM, user_prompt)
