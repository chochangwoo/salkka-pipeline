"""
marketing/blog_post_generator.py
──────────────────────────────────
뉴스레터 데이터 → 네이버 블로그 / 부동산 카페 게시글 자동 초안 생성

사용법:
    python marketing/blog_post_generator.py \
        --summary data/trades_summary.json \
        --timing data/timing_result.json \
        --trades data/notable_trades.json \
        --vol 5 --region 마포구

출력:
    data/posts/
        naver_blog_vol{NNN}.md       네이버 블로그 포스팅 (마크다운)
        cafe_post_vol{NNN}.txt       부동산 카페 게시글 (텍스트)
        blind_post_vol{NNN}.txt      블라인드 게시글 (텍스트)

자동화 포인트:
    - 매주 뉴스레터 발송 직후 GitHub Actions에서 자동 생성
    - 생성된 파일을 확인 후 수동으로 복붙 (플랫폼 자동 포스팅은 약관상 금지)
    - 수동 작업: 확인(1분) + 붙여넣기(2분) = 주 3분 투자
"""

import json
import argparse
import os
from datetime import datetime
from pathlib import Path


def load_json(path: str):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fmt_price(price_man: int) -> str:
    if price_man >= 10000:
        uk = price_man // 10000
        chun = (price_man % 10000) // 1000
        return f"{uk}억 {chun}천만원" if chun else f"{uk}억원"
    return f"{price_man:,}만원"


def generate_naver_blog(summary, timing, trades, vol, region, date) -> str:
    """네이버 블로그 포스팅 — SEO 최적화 마크다운"""
    signal    = timing.get("신호", "관망 유지")
    reason    = timing.get("근거", "")
    hint      = timing.get("힌트", "")
    avg_price = fmt_price(summary.get("avg_price", 0))
    cnt       = summary.get("trade_count", 0)
    mkt_text  = summary.get("summary_text", "")

    complex_lines = ""
    for t in trades[:2]:
        name  = t.get("complex_name", "")
        price = fmt_price(t.get("price", 0))
        area  = t.get("area", 84)
        floor = t.get("floor", 0)
        complex_lines += f"\n**{name}** — {area}㎡ {floor}층 · {price}\n"
        analysis = t.get("ai_analysis", "")
        if analysis:
            complex_lines += f"> {analysis[:200]}...\n"

    return f"""# {region} 아파트 실거래가 {date} 주간 브리핑

> 매주 월요일, AI가 분석한 {region} 부동산 시장 동향을 정리합니다.
> 더 자세한 분석은 **[살까말까](https://salkkamalka.com)** 뉴스레터에서 확인하세요.

---

## 이번 주 {region} 시장 요약

- 📊 **주간 거래량**: {cnt}건
- 💰 **84㎡ 평균 거래가**: {avg_price}
- 📡 **타이밍 신호**: {signal}

{mkt_text}

---

## 이번 주 주목할 단지
{complex_lines}
---

## 지금 사야 할까요? — 타이밍 분석

**이번 주 신호: {signal}**

{reason}

> 💡 {hint}

---

## 마무리

{region} 내집마련을 준비하고 있다면, 매주 월요일 아침 AI가 분석한 실거래 데이터를 이메일로 받아볼 수 있어요.

👉 **[살까말까 무료 구독하기](https://salkkamalka.com)** — 커피 한 잔 마시는 시간에 이번 주 시장 파악 끝!

---
*본 정보는 국토부 실거래 공공데이터 기반이며, 투자 권유가 아닙니다.*
*살까말까 Vol.{vol:03d} | {date}*
"""


def generate_cafe_post(summary, timing, trades, vol, region, date) -> str:
    """부동산 카페 게시글 — 친근한 구어체"""
    signal    = timing.get("신호", "관망 유지")
    reason    = timing.get("근거", "")
    hint      = timing.get("힌트", "")
    avg_price = fmt_price(summary.get("avg_price", 0))
    cnt       = summary.get("trade_count", 0)

    complex_summary = ""
    for t in trades[:2]:
        name  = t.get("complex_name", "")
        price = fmt_price(t.get("price", 0))
        area  = t.get("area", 84)
        floor = t.get("floor", 0)
        complex_summary += f"• {name} | {area}㎡ {floor}층 | {price}\n"

    return f"""안녕하세요! {region} 내집마련 준비하면서 매주 실거래 데이터 정리하고 있는데, 이번 주 내용 공유드려요 😊

━━━━━━━━━━━━━━━━━━━
📊 {date} {region} 주간 실거래 요약
━━━━━━━━━━━━━━━━━━━

✅ 이번 주 거래량: {cnt}건
✅ 84㎡ 평균가: {avg_price}
✅ 이번 주 신호: {signal}

{reason}

💡 {hint}

━━━━━━━━━━━━━━━━━━━
🏠 주목 단지
━━━━━━━━━━━━━━━━━━━
{complex_summary}
더 자세한 임장 서술 / 급매 분석 / 공급 리스크는
매주 월요일 이메일 뉴스레터로 정리해서 보내드리고 있어요.

무료로 구독 가능합니다 → https://salkkamalka.com

혹시 {region} 다른 단지 궁금하신 분 있으시면 댓글 달아주세요!
다음 주에 반영해볼게요 🙌

──
*국토부 실거래 공공데이터 기반 / 투자 권유 아님*
"""


def generate_blind_post(summary, timing, trades, vol, region, date) -> str:
    """블라인드 게시글 — 직장인 톤, 간결하게"""
    signal    = timing.get("신호", "관망 유지")
    avg_price = fmt_price(summary.get("avg_price", 0))
    cnt       = summary.get("trade_count", 0)
    hint      = timing.get("힌트", "")

    complex_names = " / ".join([t.get("complex_name", "") for t in trades[:2] if t.get("complex_name")])

    return f"""[{region} 내집마련 준비 중] 이번 주 실거래 요약 공유

저도 {region} 전세 살면서 내집마련 고민하다가, 매주 국토부 실거래 데이터 AI로 분석해서 뉴스레터 만들고 있어요.

이번 주 ({date}) 요약:
- 거래량: {cnt}건
- 84㎡ 평균: {avg_price}
- 주목 단지: {complex_names}
- 이번 주 판단: {signal}

{hint}

혹시 관심 있으신 분들 무료로 구독 가능합니다 (광고 아니고 진짜 제가 만든 거예요 ㅎㅎ)
→ salkkamalka.com

{region} 어떻게 보세요? 다들 지금 관망인가요?
"""


def main():
    parser = argparse.ArgumentParser(description="살까말까 블로그/카페 게시글 자동 생성기")
    parser.add_argument("--summary", default="data/trades_summary.json")
    parser.add_argument("--timing",  default="data/timing_result.json")
    parser.add_argument("--trades",  default="data/notable_trades.json")
    parser.add_argument("--vol",     type=int, default=1)
    parser.add_argument("--region",  default="마포구")
    parser.add_argument("--date",    default=datetime.now().strftime("%Y년 %m월 %d일"))
    args = parser.parse_args()

    summary = load_json(args.summary)
    timing  = load_json(args.timing)
    trades  = load_json(args.trades)
    if isinstance(trades, dict):
        trades = trades.get("trades", [])

    out_dir = Path("data/posts")
    out_dir.mkdir(parents=True, exist_ok=True)
    v = args.vol

    # 네이버 블로그
    blog = generate_naver_blog(summary, timing, trades, v, args.region, args.date)
    p1 = out_dir / f"naver_blog_vol{v:03d}.md"
    p1.write_text(blog, encoding="utf-8")

    # 부동산 카페
    cafe = generate_cafe_post(summary, timing, trades, v, args.region, args.date)
    p2 = out_dir / f"cafe_post_vol{v:03d}.txt"
    p2.write_text(cafe, encoding="utf-8")

    # 블라인드
    blind = generate_blind_post(summary, timing, trades, v, args.region, args.date)
    p3 = out_dir / f"blind_post_vol{v:03d}.txt"
    p3.write_text(blind, encoding="utf-8")

    print(f"✅ 게시글 초안 생성 완료 (Vol.{v:03d})")
    print(f"  📝 네이버 블로그: {p1}")
    print(f"  🏠 부동산 카페:   {p2}")
    print(f"  👔 블라인드:       {p3}")
    print()
    print("📋 다음 단계: 각 파일 열어서 확인 후 해당 플랫폼에 복붙 (약 3분)")


if __name__ == "__main__":
    main()
