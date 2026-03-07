"""
marketing/archive_generator.py
───────────────────────────────
뉴스레터 데이터 → SEO 최적화 웹 아카이브 페이지 자동 생성

사용법:
    python marketing/archive_generator.py \
        --summary data/trades_summary.json \
        --timing data/timing_result.json \
        --trades data/notable_trades.json \
        --vol 5 --region 마포구

출력:
    data/archive/vol{NNN}.html   (GitHub Pages 또는 정적 호스팅에 자동 배포)

SEO 포인트:
    - <title>: "마포구 아파트 실거래 {날짜} 주간 브리핑 | 살까말까"
    - <meta description>: 주간 핵심 요약 자동 삽입
    - <h1>, <h2> 구조: 검색 크롤러 최적화
    - Open Graph: 카카오톡/SNS 공유 시 미리보기 자동 생성
"""

import json
import argparse
import os
from datetime import datetime
from pathlib import Path


def load_json(path: str) -> dict | list:
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


def generate_archive_html(
    summary: dict,
    timing: dict,
    notable_trades: list,
    vol: int,
    region: str,
    issue_date: str,
    news_title: str = "",
    news_summary: str = "",
    editor_comment: str = "",
) -> str:

    signal     = timing.get("신호", "관망 유지")
    reason     = timing.get("근거", "")
    hint       = timing.get("힌트", "")
    avg_price  = fmt_price(summary.get("avg_price", 0))
    trade_cnt  = summary.get("trade_count", 0)
    mkt_text   = summary.get("summary_text", "")

    meta_desc = f"{issue_date} {region} 아파트 실거래 주간 브리핑. 이번 주 거래량 {trade_cnt}건, 84㎡ 평균가 {avg_price}. 타이밍 신호: {signal}. AI 분석 기반 내집마련 정보."

    complex_sections = ""
    for t in notable_trades[:2]:
        name       = t.get("complex_name", "")
        price      = fmt_price(t.get("price", 0))
        area       = t.get("area", 84)
        floor      = t.get("floor", 0)
        build_year = t.get("build_year", "")
        analysis   = t.get("ai_analysis", "")
        complex_sections += f"""
      <article class="complex-card">
        <div class="complex-header">
          <h2 class="complex-name">{name}</h2>
          <div class="complex-tags">
            <span class="tag">전용 {area}㎡</span>
            <span class="tag">{floor}층</span>
            {f'<span class="tag">{build_year}년 준공</span>' if build_year else ''}
          </div>
        </div>
        <div class="complex-price">거래가 <strong>{price}</strong></div>
        {f'<div class="complex-analysis">{analysis}</div>' if analysis else ''}
      </article>
        """

    news_section = ""
    if news_title:
        news_section = f"""
    <section class="section">
      <div class="section-label">이번 주 뉴스</div>
      <h2 class="section-title">{news_title}</h2>
      {f'<p class="news-body">{news_summary}</p>' if news_summary else ''}
    </section>
        """

    editor_section = ""
    if editor_comment:
        editor_section = f"""
    <section class="editor-box">
      <div class="editor-label">편집장 총평</div>
      <blockquote class="editor-quote">{editor_comment}</blockquote>
    </section>
        """

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{region} 아파트 실거래 {issue_date} 주간 브리핑 | 살까말까 Vol.{vol:03d}</title>
<meta name="description" content="{meta_desc}">
<meta name="keywords" content="{region} 아파트, 실거래가, 내집마련, 부동산 뉴스레터, 주간 브리핑, 살까말까">
<meta name="robots" content="index, follow">

<!-- Open Graph (카카오톡, SNS 공유) -->
<meta property="og:title"       content="{region} 이번 주 부동산 브리핑 | 살까말까 Vol.{vol:03d}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:type"        content="article">
<meta property="og:url"         content="https://salkkamalka.com/archive/vol{vol:03d}">
<meta property="og:site_name"   content="살까말까">

<!-- Canonical -->
<link rel="canonical" href="https://salkkamalka.com/archive/vol{vol:03d}">

<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --dark:   #1a1208;
    --cream:  #faf7f2;
    --gold:   #e8a020;
    --red:    #c8401a;
    --text:   #2c2416;
    --muted:  #7a6e5e;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Noto Sans KR', sans-serif;
    background: var(--cream);
    color: var(--text);
    line-height: 1.7;
  }}

  /* ── 최상단 구독 배너 ── */
  .sub-banner {{
    background: var(--gold);
    text-align: center;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 700;
    color: var(--dark);
  }}
  .sub-banner a {{ color: var(--dark); text-decoration: underline; }}

  /* ── 헤더 ── */
  header {{
    background: var(--dark);
    padding: 40px 20px;
    text-align: center;
    border-bottom: 4px solid var(--gold);
  }}
  .brand {{ color: var(--gold); font-family: 'Noto Serif KR'; font-size: 36px; font-weight: 700; }}
  .vol-info {{ color: rgba(250,247,242,.6); font-size: 14px; margin-top: 8px; }}
  h1 {{
    color: var(--cream);
    font-family: 'Noto Serif KR';
    font-size: clamp(20px, 4vw, 30px);
    font-weight: 700;
    margin-top: 16px;
    line-height: 1.4;
  }}

  /* ── 본문 컨테이너 ── */
  .container {{
    max-width: 720px;
    margin: 0 auto;
    padding: 48px 20px 80px;
  }}
  .section {{ margin-bottom: 56px; }}
  .section-label {{
    color: var(--gold);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 12px;
  }}
  .section-title {{
    font-family: 'Noto Serif KR';
    font-size: 22px;
    font-weight: 700;
    color: var(--dark);
    margin-bottom: 20px;
    line-height: 1.4;
  }}

  /* ── 시장 통계 그리드 ── */
  .stat-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 20px;
  }}
  @media (max-width: 480px) {{ .stat-grid {{ grid-template-columns: 1fr 1fr; }} }}
  .stat-item {{
    background: var(--dark);
    border-radius: 10px;
    padding: 20px 16px;
    text-align: center;
  }}
  .stat-item .label {{ color: var(--gold); font-size: 11px; letter-spacing: 1px; margin-bottom: 8px; }}
  .stat-item .value {{ color: var(--cream); font-size: 22px; font-weight: 700; }}
  .market-text {{
    background: #f0ebe2;
    border-left: 4px solid var(--gold);
    padding: 16px 20px;
    border-radius: 0 8px 8px 0;
    font-size: 15px;
    line-height: 1.75;
  }}

  /* ── 단지 카드 ── */
  .complex-card {{
    border: 1px solid #e0d8cc;
    border-radius: 12px;
    padding: 28px;
    margin-bottom: 16px;
    background: white;
  }}
  .complex-header {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }}
  .complex-name {{ font-family: 'Noto Serif KR'; font-size: 20px; font-weight: 700; color: var(--dark); }}
  .complex-tags {{ display: flex; gap: 6px; flex-wrap: wrap; }}
  .tag {{
    background: #f0ebe2;
    color: var(--muted);
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 20px;
  }}
  .complex-price {{ font-size: 14px; color: var(--muted); margin-bottom: 14px; }}
  .complex-price strong {{ color: var(--red); font-size: 20px; font-weight: 700; }}
  .complex-analysis {{ font-size: 14px; line-height: 1.8; color: var(--text); border-top: 1px solid #e8e2d8; padding-top: 14px; }}

  /* ── 타이밍 신호 ── */
  .timing-box {{
    background: var(--dark);
    border-radius: 16px;
    padding: 32px 28px;
    margin-bottom: 16px;
  }}
  .timing-signal {{
    color: var(--gold);
    font-size: 28px;
    font-weight: 900;
    margin-bottom: 12px;
  }}
  .timing-reason {{ color: rgba(250,247,242,.75); font-size: 15px; line-height: 1.75; margin-bottom: 16px; }}
  .timing-hint {{
    background: rgba(232,160,32,.15);
    border-radius: 8px;
    padding: 14px 18px;
    color: var(--gold);
    font-size: 14px;
    font-weight: 500;
  }}

  /* ── 뉴스 ── */
  .news-body {{ font-size: 15px; line-height: 1.8; }}

  /* ── 편집장 총평 ── */
  .editor-box {{
    background: #f5f0e8;
    border-radius: 12px;
    padding: 28px;
    margin-bottom: 56px;
  }}
  .editor-label {{ color: var(--muted); font-size: 12px; letter-spacing: 2px; margin-bottom: 12px; }}
  .editor-quote {{ font-family: 'Noto Serif KR'; font-size: 17px; line-height: 1.8; color: var(--dark); font-style: italic; border: none; }}

  /* ── CTA ── */
  .cta-section {{
    background: var(--dark);
    border-radius: 16px;
    padding: 40px 32px;
    text-align: center;
  }}
  .cta-title {{ color: var(--cream); font-size: 20px; font-weight: 700; margin-bottom: 8px; }}
  .cta-sub {{ color: rgba(250,247,242,.6); font-size: 14px; margin-bottom: 24px; }}
  .cta-btn {{
    display: inline-block;
    background: var(--gold);
    color: var(--dark);
    font-weight: 700;
    font-size: 16px;
    padding: 14px 36px;
    border-radius: 50px;
    text-decoration: none;
  }}
  .cta-btn:hover {{ opacity: 0.9; }}

  /* ── 푸터 ── */
  footer {{
    background: var(--dark);
    color: rgba(250,247,242,.4);
    text-align: center;
    padding: 32px 20px;
    font-size: 12px;
    line-height: 1.8;
  }}
  footer a {{ color: var(--gold); }}
</style>
</head>
<body>

<div class="sub-banner">
  📬 매주 월요일 아침 7시, 무료로 받아보세요 →
  <a href="https://salkkamalka.com">salkkamalka.com 구독하기</a>
</div>

<header>
  <div class="brand">살까말까</div>
  <div class="vol-info">Vol.{vol:03d} · {issue_date} · 📍 {region}</div>
  <h1>{region} 이번 주 아파트 실거래 브리핑<br>거래량 {trade_cnt}건 · 84㎡ 평균 {avg_price}</h1>
</header>

<div class="container">

  <!-- 시장 온도계 -->
  <section class="section">
    <div class="section-label">01 · Market Overview</div>
    <h2 class="section-title">이번 주 {region} 시장 온도계</h2>
    <div class="stat-grid">
      <div class="stat-item">
        <div class="label">주간 거래량</div>
        <div class="value">{trade_cnt}건</div>
      </div>
      <div class="stat-item">
        <div class="label">84㎡ 평균가</div>
        <div class="value">{avg_price}</div>
      </div>
      <div class="stat-item">
        <div class="label">타이밍 신호</div>
        <div class="value" style="font-size:14px; padding-top:4px;">{signal}</div>
      </div>
    </div>
    {f'<div class="market-text">{mkt_text}</div>' if mkt_text else ''}
  </section>

  <!-- 주목 단지 -->
  {f'''<section class="section">
    <div class="section-label">02 · Notable Complexes</div>
    <h2 class="section-title">이번 주 주목할 단지</h2>
    {complex_sections}
  </section>''' if complex_sections else ''}

  <!-- 타이밍 신호 -->
  <section class="section">
    <div class="section-label">03 · Timing Signal</div>
    <h2 class="section-title">지금 사야 할까요?</h2>
    <div class="timing-box">
      <div class="timing-signal">{signal}</div>
      {f'<div class="timing-reason">{reason}</div>' if reason else ''}
      {f'<div class="timing-hint">💡 {hint}</div>' if hint else ''}
    </div>
  </section>

  {news_section}

  {editor_section}

  <!-- CTA -->
  <div class="cta-section">
    <div class="cta-title">매주 더 자세한 분석이 필요하신가요?</div>
    <div class="cta-sub">구독자에게는 급매 알림 · 단지 비교 · AI Q&A가 제공됩니다</div>
    <a href="https://salkkamalka.com" class="cta-btn">무료 구독 시작하기 →</a>
  </div>

</div>

<footer>
  <strong style="color:rgba(250,247,242,.7);">살까말까</strong> · 내집마련을 준비하는 당신을 위한 주간 브리핑<br>
  <a href="https://salkkamalka.com">salkkamalka.com</a> ·
  <a href="https://salkkamalka.com/unsubscribe">수신 거부</a><br><br>
  본 브리핑은 정보 제공 목적이며 투자 권유가 아닙니다. 매수/매도 결정은 본인의 판단으로 하시기 바랍니다.
</footer>

</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="살까말까 웹 아카이브 페이지 생성기")
    parser.add_argument("--summary",  default="data/trades_summary.json")
    parser.add_argument("--timing",   default="data/timing_result.json")
    parser.add_argument("--trades",   default="data/notable_trades.json")
    parser.add_argument("--vol",      type=int, default=1)
    parser.add_argument("--region",   default="마포구")
    parser.add_argument("--date",     default=datetime.now().strftime("%Y년 %m월 %d일"))
    parser.add_argument("--news-title",   default="")
    parser.add_argument("--news-summary", default="")
    parser.add_argument("--editor",       default="")
    args = parser.parse_args()

    summary = load_json(args.summary)
    timing  = load_json(args.timing)
    trades  = load_json(args.trades)
    if isinstance(trades, dict):
        trades = trades.get("trades", [])

    html = generate_archive_html(
        summary=summary,
        timing=timing,
        notable_trades=trades,
        vol=args.vol,
        region=args.region,
        issue_date=args.date,
        news_title=args.news_title,
        news_summary=args.news_summary,
        editor_comment=args.editor,
    )

    out_dir = Path("data/archive")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"vol{args.vol:03d}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ 아카이브 페이지 생성 완료: {out_path}")
    print("🌐 GitHub Pages 또는 Netlify에 배포하면 SEO 자동 인덱싱됩니다.")


if __name__ == "__main__":
    main()
