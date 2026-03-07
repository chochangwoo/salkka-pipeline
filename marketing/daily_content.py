"""
marketing/daily_content.py
──────────────────────────
매일 자동 생성되는 마케팅 콘텐츠 (블로그/카페/블라인드/인스타)

요일별 콘텐츠 전략:
  월: 주간 브리핑 요약 (뉴스레터 핵심)
  화: 단지 심층 분석 (1개 단지 포커스)
  수: 예산별 지역 비교
  목: 부동산 뉴스 해석
  금: 주말 임장 추천 + 체크리스트
  토: 인스타 카드뉴스 (시장 온도 시각화)
  일: 다음 주 전망 + 구독 유도

사용법:
    python marketing/daily_content.py [--region 마포구] [--day 0~6]

출력:
    data/daily/{날짜}/
        blog.md          네이버 블로그
        cafe.txt         부동산 카페
        blind.txt        블라인드
        instagram.txt    인스타 캡션
"""

import json
import argparse
from datetime import datetime
from pathlib import Path

from openai import OpenAI
import config


# ── 요일별 콘텐츠 타입 ────────────────────────────────────────

DAY_THEMES = {
    0: {"type": "weekly_summary",   "label": "주간 브리핑 요약"},
    1: {"type": "complex_deep",     "label": "단지 심층 분석"},
    2: {"type": "budget_compare",   "label": "예산별 지역 비교"},
    3: {"type": "news_insight",     "label": "부동산 뉴스 해석"},
    4: {"type": "weekend_guide",    "label": "주말 임장 가이드"},
    5: {"type": "card_visual",      "label": "시장 온도 카드뉴스"},
    6: {"type": "next_week",        "label": "다음 주 전망"},
}


# ── 데이터 로드 ───────────────────────────────────────────────

def _load(name: str):
    path = Path(f"data/{name}.json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _load_all():
    return {
        "summary": _load("marketing_summary") or _load("trades_summary"),
        "timing": _load("timing_result"),
        "trades": _load("notable_trades"),
        "all_trades": _load("trades_all"),
    }


def fmt_price(price_man: int) -> str:
    if not price_man:
        return "0원"
    if price_man >= 10000:
        uk = price_man // 10000
        chun = (price_man % 10000) // 1000
        return f"{uk}억 {chun}천" if chun else f"{uk}억"
    return f"{price_man:,}만"


# ── GPT 콘텐츠 생성 ──────────────────────────────────────────

def _gpt(system: str, user: str) -> str:
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=config.GPT_MODEL_MAIN,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=1200,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


SYSTEM_BLOG = """당신은 부동산 전문 블로거입니다.
내집마련 실수요자를 위해 친근하고 실용적인 글을 씁니다.
규칙:
- 구어체, 자연스러운 문장
- 숫자와 데이터로 신뢰감 확보
- "데이터 부족", "확인되지 않았습니다" 같은 표현 금지
- 확실하지 않으면 해당 내용은 아예 쓰지 않을 것
- "화이팅" 류 마무리 금지
- 마지막에 자연스럽게 '살까말까' 뉴스레터 구독 유도 (salkkamalka.com)
"""

SYSTEM_CAFE = """당신은 부동산 카페 활동을 하는 30대 직장인입니다.
내집마련 준비하면서 알게 된 정보를 공유하는 톤으로 글을 씁니다.
규칙:
- 반말이 아닌 존댓말, 하지만 딱딱하지 않게
- 이모지 적당히 사용
- 댓글 유도 질문으로 마무리
- 마지막에 자연스럽게 뉴스레터 언급 (salkkamalka.com)
"""

SYSTEM_BLIND = """당신은 블라인드에서 부동산 이야기를 공유하는 직장인입니다.
규칙:
- 간결하고 핵심만
- 직장인 톤 (ㅎㅎ, ㅋㅋ 약간 사용 가능)
- 반응 유도 질문으로 마무리
- 뉴스레터 언급은 자연스럽게 한 줄로
"""

SYSTEM_INSTA = """당신은 인스타그램 부동산 계정 운영자입니다.
규칙:
- 캡션은 3~5줄, 핵심만 간결하게
- 해시태그 10~15개 (부동산/내집마련/지역명 관련)
- CTA: 프로필 링크에서 무료 구독
"""


# ── 월: 주간 브리핑 요약 ─────────────────────────────────────

def gen_weekly_summary(data: dict, region: str) -> dict:
    summary = data["summary"]
    timing = data["timing"]
    trades = data["trades"] if isinstance(data["trades"], list) else []

    trade_count = summary.get("trade_count", 0)
    avg_price = fmt_price(summary.get("avg_price", 0))
    signal = timing.get("신호", "")
    reason = timing.get("근거", "")
    hint = timing.get("힌트", "")

    complex_info = ""
    for t in trades[:2]:
        name = t.get("complex_name", "")
        price = fmt_price(t.get("price", 0))
        complex_info += f"- {name}: {t.get('area', 84)}㎡ {t.get('floor', '')}층, {price}\n"

    prompt = f"""이번 주 {region} 부동산 실거래 데이터 요약을 가지고
블로그/카페/블라인드/인스타 각 채널용 게시글을 작성해줘.

데이터:
- 이번 주 거래량: {trade_count}건
- 84㎡ 평균가: {avg_price}
- 타이밍 신호: {signal}
- 근거: {reason}
- 힌트: {hint}
- 주목 단지:
{complex_info}
"""
    return _generate_all_channels("주간 브리핑 요약", prompt, region)


# ── 화: 단지 심층 분석 ───────────────────────────────────────

def gen_complex_deep(data: dict, region: str) -> dict:
    trades = data["trades"] if isinstance(data["trades"], list) else []
    if not trades:
        return _empty_result()

    # 첫 번째 주목 단지로 심층 분석
    t = trades[0]
    name = t.get("complex_name", "")
    price = fmt_price(t.get("price", 0))

    # 같은 단지 전체 거래 찾기
    all_trades = data.get("all_trades", [])
    same_complex = [x for x in all_trades if x.get("complex_name") == name] if isinstance(all_trades, list) else []

    history = ""
    for tx in same_complex[:5]:
        history += f"- {tx.get('trade_date', '')}: {tx.get('area', '')}㎡ {tx.get('floor', '')}층 {fmt_price(tx.get('price', 0))}\n"

    prompt = f"""{region} '{name}' 단지를 심층 분석하는 콘텐츠를 만들어줘.

기본 정보:
- 단지명: {name}
- 최근 거래가: {price} ({t.get('area', 84)}㎡, {t.get('floor', '')}층)
- 소재지: {region} {t.get('road_name', '')}

최근 거래 이력:
{history if history else '최근 거래 1건'}

분석 포인트:
1. 이 가격대가 적정한지 (전고점 대비)
2. 입지 장단점 (교통, 학군, 생활인프라)
3. 실수요자 관점에서의 매수 포인트
"""
    return _generate_all_channels(f"단지 분석: {name}", prompt, region)


# ── 수: 예산별 지역 비교 ─────────────────────────────────────

def gen_budget_compare(data: dict, region: str) -> dict:
    summary = data["summary"]
    avg_price = summary.get("avg_price", 0)

    prompt = f"""{region} 기준 예산별(3~4억 / 5~6억 / 7억 이상)
어떤 지역이 내집마련에 유리한지 비교하는 콘텐츠를 만들어줘.

현재 {region} 84㎡ 평균가: {fmt_price(avg_price)}

비교 포인트:
1. 각 예산대에서 살 수 있는 지역과 평형
2. 교통 접근성 (강남/여의도 출퇴근)
3. 학군과 생활 인프라
4. 향후 공급 리스크
5. 실수요자에게 어떤 예산대가 현실적인지
"""
    return _generate_all_channels("예산별 지역 비교", prompt, region)


# ── 목: 부동산 뉴스 해석 ─────────────────────────────────────

def gen_news_insight(data: dict, region: str) -> dict:
    # 실시간 뉴스 수집
    from collector.news import fetch_news_rss, select_top_news

    items = fetch_news_rss(max_items=20)
    top = select_top_news(items, region=region)

    if not top:
        # 뉴스 없으면 일반 시장 동향으로 대체
        prompt = f"""오늘 {region} 부동산 시장에서 주목할 만한 동향을
내집마련 실수요자 관점에서 해석하는 콘텐츠를 만들어줘.

포인트:
1. 최근 금리/대출 정책 변화
2. 공급 이슈
3. 실수요자가 지금 해야 할 것
"""
    else:
        prompt = f"""다음 부동산 뉴스를 내집마련 실수요자 관점에서
쉽게 해석하는 콘텐츠를 만들어줘.

뉴스 제목: {top['title']}
출처: {top.get('source', '')}
관련 지역: {region}

포인트:
1. 이 뉴스가 왜 중요한지
2. 실수요자에게 어떤 영향이 있는지
3. 구체적으로 어떤 행동을 해야 하는지
"""
    return _generate_all_channels("뉴스 해석", prompt, region)


# ── 금: 주말 임장 가이드 ─────────────────────────────────────

def gen_weekend_guide(data: dict, region: str) -> dict:
    trades = data["trades"] if isinstance(data["trades"], list) else []

    complex_names = ", ".join(t.get("complex_name", "") for t in trades[:3]) if trades else region

    prompt = f"""이번 주말 {region} 임장을 계획하는 실수요자를 위한
실전 가이드 콘텐츠를 만들어줘.

추천 임장 단지: {complex_names}

포함할 내용:
1. 임장 전 준비사항 (서류, 앱, 체크리스트)
2. 현장에서 반드시 확인할 것 5가지
3. 중개사에게 꼭 물어볼 질문 3가지
4. 임장 후 정리 방법
5. 주변 맛집/카페 한 줄 팁 (현실적으로)
"""
    return _generate_all_channels("주말 임장 가이드", prompt, region)


# ── 토: 인스타 카드뉴스 ──────────────────────────────────────

def gen_card_visual(data: dict, region: str) -> dict:
    summary = data["summary"]
    timing = data["timing"]

    trade_count = summary.get("trade_count", 0)
    avg_price = fmt_price(summary.get("avg_price", 0))
    signal = timing.get("신호", "")

    prompt = f"""인스타그램 카드뉴스(캐러셀) 3장 분량의 텍스트 콘텐츠를 만들어줘.

주제: 이번 주 {region} 부동산 시장 온도
데이터: 거래량 {trade_count}건, 84㎡ 평균 {avg_price}, 신호 {signal}

각 카드 구성:
카드1: 시장 온도 한 줄 요약 + 핵심 숫자 3개
카드2: 이번 주 주목 포인트 (왜 이런 흐름인지)
카드3: 실수요자 행동 가이드 + 구독 유도

인스타 캡션도 별도로 작성해줘.
"""
    return _generate_all_channels("카드뉴스", prompt, region)


# ── 일: 다음 주 전망 ─────────────────────────────────────────

def gen_next_week(data: dict, region: str) -> dict:
    summary = data["summary"]
    timing = data["timing"]

    signal = timing.get("신호", "")
    hint = timing.get("힌트", "")

    prompt = f"""다음 주 {region} 부동산 시장 전망 콘텐츠를 만들어줘.

이번 주 신호: {signal}
힌트: {hint}

포함할 내용:
1. 다음 주 주목할 이벤트 (금통위, 정책 발표 등)
2. 거래량/가격 방향성 예측
3. 실수요자가 다음 주에 할 일 (구체적으로)
4. 월요일 뉴스레터에서 다룰 예정 내용 예고
"""
    return _generate_all_channels("다음 주 전망", prompt, region)


# ── 채널별 콘텐츠 일괄 생성 ──────────────────────────────────

def _generate_all_channels(theme: str, data_prompt: str, region: str) -> dict:
    """4개 채널 콘텐츠를 한 번의 GPT 호출로 생성"""
    system = f"""당신은 부동산 마케팅 콘텐츠 전문가입니다.
하나의 주제로 4개 채널(네이버 블로그, 부동산 카페, 블라인드, 인스타그램)에
각각 최적화된 게시글을 작성합니다.

지역: {region}
오늘의 주제: {theme}

규칙:
- "데이터 부족", "확인되지 않았습니다" 같은 표현 절대 금지
- 확실하지 않은 내용은 아예 쓰지 말 것
- 각 채널의 톤과 길이를 맞출 것
- 모든 채널에 salkkamalka.com 구독 유도를 자연스럽게 포함

출력 형식:
반드시 아래 4개 구분자를 정확히 사용하여 채널별로 분리하세요.
구분자는 줄의 맨 앞에, 해당 줄에 구분자만 적어야 합니다.

===BLOG===
네이버 블로그 마크다운 형식. 800~1200자. SEO를 위해 제목(#)과 소제목(##) 포함.

===CAFE===
부동산 카페 텍스트. 500~800자. 존댓말, 댓글 유도 질문으로 마무리.

===BLIND===
블라인드 텍스트. 300~500자. 간결, 직장인 톤.

===INSTA===
인스타 캡션 200~300자 + 해시태그 10~15개.
"""

    result = _gpt(system, data_prompt)
    return _parse_channels(result)


def _parse_channels(text: str) -> dict:
    """GPT 출력에서 채널별 콘텐츠 분리"""
    channels = {"blog": "", "cafe": "", "blind": "", "instagram": ""}

    markers = {
        "===BLOG===": "blog",
        "===CAFE===": "cafe",
        "===BLIND===": "blind",
        "===INSTA===": "instagram",
    }

    current = None
    lines = []

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped in markers:
            if current and lines:
                channels[current] = "\n".join(lines).strip()
            current = markers[stripped]
            lines = []
        elif current is not None:
            lines.append(line)

    # 마지막 채널
    if current and lines:
        channels[current] = "\n".join(lines).strip()

    # 구분자가 하나도 없으면 전체를 모든 채널에 할당
    if not any(channels.values()):
        channels = {
            "blog": text,
            "cafe": text,
            "blind": text,
            "instagram": text,
        }

    return channels


def _empty_result() -> dict:
    return {"blog": "", "cafe": "", "blind": "", "instagram": ""}


# ── 메인 실행 ─────────────────────────────────────────────────

GENERATORS = {
    0: gen_weekly_summary,
    1: gen_complex_deep,
    2: gen_budget_compare,
    3: gen_news_insight,
    4: gen_weekend_guide,
    5: gen_card_visual,
    6: gen_next_week,
}

DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]


def generate_daily(region: str, day: int = None) -> dict:
    """
    오늘의 마케팅 콘텐츠 생성.

    Args:
        region: 지역
        day: 요일 (0=월~6=일), None이면 오늘

    Returns:
        {"blog": str, "cafe": str, "blind": str, "instagram": str}
    """
    if day is None:
        day = datetime.now().weekday()

    theme = DAY_THEMES[day]
    print(f"[마케팅] {DAY_NAMES[day]}요일 콘텐츠: {theme['label']}")

    data = _load_all()
    generator = GENERATORS[day]
    result = generator(data, region)

    # 파일 저장
    today = datetime.now().strftime("%Y%m%d")
    out_dir = Path(f"data/daily/{today}")
    out_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "blog": (out_dir / "blog.md", result.get("blog", "")),
        "cafe": (out_dir / "cafe.txt", result.get("cafe", "")),
        "blind": (out_dir / "blind.txt", result.get("blind", "")),
        "instagram": (out_dir / "instagram.txt", result.get("instagram", "")),
    }

    for name, (path, content) in files.items():
        if content:
            path.write_text(content, encoding="utf-8")
            print(f"  -> {name}: {path}")

    return result


def main():
    parser = argparse.ArgumentParser(description="살까말까 일일 마케팅 콘텐츠 생성")
    parser.add_argument("--region", default=config.TARGET_REGION)
    parser.add_argument("--day", type=int, default=None,
                        help="요일 강제 지정 (0=월~6=일)")
    args = parser.parse_args()

    generate_daily(region=args.region, day=args.day)
    print("\n[완료] 각 파일을 확인 후 해당 플랫폼에 복붙하세요.")


if __name__ == "__main__":
    main()
