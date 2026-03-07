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
- 반드시 가격 구조를 먼저 분석 (최근 N건 평균 대비 하락폭, 하락률)
- 급락 원인을 구체적으로 추론 (저층/향/수리/시장상황 등 물건 자체 요인 포함)
- "시장 상황 변화 가능성", "매도자 사정 가능성" 같은 일반적 추측 금지
- 해당 단지의 동일 면적대 최근 거래 흐름과 비교
- 실수요자가 실제로 확인해야 할 구체적 사항 3가지 제시
- 과도한 추천이나 공포 유발 금지
- 250자 내외
""".strip()


def analyze_urgent_sale(sale: dict) -> str:
    """급매 거래 GPT 해설"""
    trade = sale["trade"]
    avg_recent = sale.get("avg_recent_price", sale["prev_price"])
    recent_count = sale.get("recent_trade_count", 2)

    user_prompt = f"""
다음 급매 거래를 분석해줘.

[가격 구조]
단지명: {trade.complex_name}
이번 거래: {trade.price / 10000:.1f}억원 (전용 {trade.area:.0f}㎡, {trade.floor}층)
거래일: {trade.trade_date}
직전 거래가: {sale['prev_price'] / 10000:.1f}억원
최근 {recent_count}건 평균: {avg_recent / 10000:.1f}억원
하락률 (직전 대비): -{sale['drop_rate'] * 100:.1f}%
하락률 (평균 대비): -{max(0, (avg_recent - trade.price) / avg_recent * 100):.1f}%

[물건 특성]
층수: {trade.floor}층 {'(저층)' if trade.floor <= 3 else ''}
건축연도: {trade.build_year}년 (준공 {2026 - trade.build_year}년차)

출력 형식:
1) 가격 구조 요약 (평균 대비 얼마나 싼지 한 줄)
2) 급락 원인 추론 (물건 자체 요인 + 시장 요인 구분)
3) 실수요자 관점 판단
4) 반드시 확인할 사항 3가지
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
- 반드시 구체적 수치 기반 답변 (실거래가, 전세가율, 공급량 등 인용)
- "살만할 수 있습니다", "시장 상황을 고려해야 합니다" 같은 일반론 금지
- 해당 단지/지역의 실제 데이터를 근거로 판단 근거 제시
- 직접적 매수/매도 권유 금지, 그러나 판단에 필요한 체크리스트 제공
- "이 조건이라면 ~를 먼저 확인하세요" 형태의 구체적 행동 제안
- 확인해야 할 사항 2~3가지 추가
- 300자 내외
""".strip()


def answer_subscriber_question(question: str, context: str = "") -> str:
    """구독자 Q&A 답변 생성"""
    user_prompt = f"""
구독자 질문: {question}

{f'[참고 데이터]{chr(10)}{context}' if context else ''}

답변 형식:
1) 질문 핵심 요약 (한 줄)
2) 데이터 기반 분석 (실거래가, 전세가율, 공급량 등 구체적 수치 인용)
3) 실수요자 관점 판단 근거
4) 구체적으로 확인해야 할 사항 2~3가지
""".strip()

    return _call_gpt_premium(QNA_SYSTEM, user_prompt)
