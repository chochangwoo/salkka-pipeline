"""
marketing/card_generator.py
─────────────────────────────
뉴스레터 데이터 → 인스타그램 카드뉴스 HTML 자동 생성

사용법:
    python marketing/card_generator.py \
        --summary data/trades_summary.json \
        --timing data/timing_result.json \
        --vol 5 --region 마포구

출력:
    data/cards/card_vol{NNN}.html  (브라우저 스크린샷 → 인스타그램 업로드)
"""

import json
import argparse
import os
from datetime import datetime
from pathlib import Path


# ──────────────────────────────────────────────
# 시장 온도 → 이모지 + 색상 매핑
# ──────────────────────────────────────────────
TIMING_COLOR = {
    "관망 유지":       {"bg": "#2d2d2d", "badge": "#888888", "emoji": "⏸"},
    "조심스런 매수 고려": {"bg": "#1a3a2a", "badge": "#4caf50", "emoji": "📈"},
    "적극 매수 고려":   {"bg": "#1a2a3a", "badge": "#2196f3", "emoji": "🚀"},
}


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fmt_price(price_man: int) -> str:
    """만원 단위 → 'N억 M천' 형식"""
    if price_man >= 10000:
        uk = price_man // 10000
        chun = (price_man % 10000) // 1000
        return f"{uk}억 {chun}천" if chun else f"{uk}억"
    return f"{price_man:,}만"


def generate_card_html(
    summary: dict,
    timing: dict,
    notable_trades: list,
    vol: int,
    region: str,
    issue_date: str,
) -> str:
    """
    3장 카드뉴스 HTML 생성
    - Card 1: 이번 주 시장 온도계
    - Card 2: 주목 단지 핵심 요약
    - Card 3: 타이밍 신호 + CTA
    """

    signal = timing.get("신호", "관망 유지")
    theme = TIMING_COLOR.get(signal, TIMING_COLOR["관망 유지"])
    avg_price = fmt_price(summary.get("avg_price", 0))
    trade_count = summary.get("trade_count", 0)

    # 주목 단지 최대 2개
    complexes = notable_trades[:2] if notable_trades else []
    complex_cards = ""
    for t in complexes:
        name = t.get("complex_name", "")
        price = fmt_price(t.get("price", 0))
        area = t.get("area", 84)
        floor = t.get("floor", 0)
        complex_cards += f"""
        <div class="complex-row">
          <span class="complex-name">{name}</span>
          <span class="complex-detail">{area}㎡ · {floor}층</span>
          <span class="complex-price">{price}</span>
        </div>
        """

    timing_hint = timing.get("힌트", "시장 상황을 지속적으로 모니터링하세요.")
    timing_reason = timing.get("근거", "")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>살까말까 Vol.{vol:03d} 카드뉴스</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Noto Sans KR', sans-serif;
    background: #111;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
    padding: 24px;
  }}

  /* ── 공통 카드 ── */
  .card {{
    width: 1080px;
    height: 1080px;
    position: relative;
    overflow: hidden;
    border-radius: 0;
    display: flex;
    flex-direction: column;
  }}

  /* ── 공통 헤더 ── */
  .card-header {{
    background: #1a1208;
    padding: 40px 60px 32px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 3px solid #e8a020;
  }}
  .brand {{ color: #e8a020; font-size: 28px; font-weight: 900; letter-spacing: 2px; }}
  .vol-badge {{
    background: #e8a020;
    color: #1a1208;
    font-size: 14px;
    font-weight: 700;
    padding: 6px 16px;
    border-radius: 20px;
  }}
  .region-tag {{
    color: #faf7f2;
    font-size: 16px;
    font-weight: 500;
    opacity: 0.7;
  }}

  /* ── 공통 푸터 ── */
  .card-footer {{
    background: #1a1208;
    padding: 20px 60px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid rgba(232,160,32,0.3);
    margin-top: auto;
  }}
  .footer-url {{ color: #e8a020; font-size: 18px; font-weight: 700; }}
  .footer-date {{ color: #faf7f2; font-size: 14px; opacity: 0.5; }}

  /* ══════════════════════════════
     CARD 1 — 시장 온도계
  ══════════════════════════════ */
  .card1-body {{
    flex: 1;
    background: #faf7f2;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 50px 60px;
    gap: 40px;
  }}
  .card1-title {{
    font-size: 36px;
    font-weight: 900;
    color: #1a1208;
    line-height: 1.3;
  }}
  .card1-title .highlight {{ color: #e8a020; }}
  .stat-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
  }}
  .stat-box {{
    background: #1a1208;
    border-radius: 16px;
    padding: 32px 24px;
    text-align: center;
  }}
  .stat-label {{ color: #e8a020; font-size: 14px; font-weight: 700; letter-spacing: 1px; margin-bottom: 12px; }}
  .stat-value {{ color: #faf7f2; font-size: 34px; font-weight: 900; line-height: 1; }}
  .stat-unit {{ color: rgba(250,247,242,0.5); font-size: 14px; margin-top: 6px; }}
  .market-summary {{
    background: rgba(26,18,8,0.07);
    border-left: 4px solid #e8a020;
    padding: 20px 24px;
    border-radius: 0 8px 8px 0;
    color: #1a1208;
    font-size: 18px;
    line-height: 1.7;
    font-weight: 500;
  }}

  /* ══════════════════════════════
     CARD 2 — 주목 단지
  ══════════════════════════════ */
  .card2-body {{
    flex: 1;
    background: #1a1208;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 50px 60px;
    gap: 36px;
  }}
  .card2-label {{
    color: #e8a020;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 3px;
  }}
  .card2-title {{
    color: #faf7f2;
    font-size: 40px;
    font-weight: 900;
    line-height: 1.2;
  }}
  .complex-list {{
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}
  .complex-row {{
    display: flex;
    align-items: center;
    background: rgba(250,247,242,0.06);
    border-radius: 12px;
    padding: 24px 28px;
    border: 1px solid rgba(232,160,32,0.2);
  }}
  .complex-name {{
    color: #faf7f2;
    font-size: 24px;
    font-weight: 700;
    flex: 1;
  }}
  .complex-detail {{
    color: rgba(250,247,242,0.5);
    font-size: 16px;
    margin-right: 24px;
  }}
  .complex-price {{
    color: #e8a020;
    font-size: 26px;
    font-weight: 900;
  }}
  .card2-note {{
    color: rgba(250,247,242,0.4);
    font-size: 15px;
    line-height: 1.6;
  }}

  /* ══════════════════════════════
     CARD 3 — 타이밍 신호
  ══════════════════════════════ */
  .card3-body {{
    flex: 1;
    background: {theme['bg']};
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 50px 60px;
    gap: 36px;
  }}
  .signal-badge {{
    display: inline-flex;
    align-items: center;
    gap: 12px;
    background: {theme['badge']};
    color: #fff;
    font-size: 22px;
    font-weight: 900;
    padding: 14px 32px;
    border-radius: 50px;
    width: fit-content;
  }}
  .signal-emoji {{ font-size: 28px; }}
  .signal-title {{
    color: #faf7f2;
    font-size: 52px;
    font-weight: 900;
    line-height: 1.15;
  }}
  .signal-reason {{
    color: rgba(250,247,242,0.7);
    font-size: 20px;
    line-height: 1.7;
    border-left: 3px solid {theme['badge']};
    padding-left: 20px;
  }}
  .signal-hint {{
    background: rgba(250,247,242,0.08);
    border-radius: 12px;
    padding: 24px 28px;
    color: #faf7f2;
    font-size: 18px;
    font-weight: 500;
    line-height: 1.6;
  }}
  .cta-box {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #e8a020;
    border-radius: 16px;
    padding: 24px 36px;
  }}
  .cta-text {{
    color: #1a1208;
    font-size: 20px;
    font-weight: 700;
    line-height: 1.4;
  }}
  .cta-arrow {{ color: #1a1208; font-size: 32px; font-weight: 900; }}

  /* ── 인쇄/스크린샷 안내 ── */
  .print-guide {{
    color: #666;
    font-size: 13px;
    text-align: center;
    padding: 8px;
  }}
</style>
</head>
<body>

<p class="print-guide">📸 각 카드를 1080×1080px 스크린샷 → 인스타그램 업로드 | 총 3장</p>

<!-- ════════════════════════════════
     CARD 1: 시장 온도계
════════════════════════════════ -->
<div class="card" id="card1">
  <div class="card-header">
    <div>
      <div class="brand">살까말까</div>
      <div class="region-tag">📍 {region} 부동산 브리핑</div>
    </div>
    <div class="vol-badge">Vol.{vol:03d} · {issue_date}</div>
  </div>

  <div class="card1-body">
    <div class="card1-title">
      이번 주 <span class="highlight">{region}</span><br>시장 온도는?
    </div>
    <div class="stat-grid">
      <div class="stat-box">
        <div class="stat-label">주간 거래량</div>
        <div class="stat-value">{trade_count}</div>
        <div class="stat-unit">건</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">84㎡ 평균가</div>
        <div class="stat-value">{avg_price}</div>
        <div class="stat-unit">기준</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">타이밍 신호</div>
        <div class="stat-value" style="font-size:22px; padding-top:6px;">{theme['emoji']}</div>
        <div class="stat-unit" style="font-size:12px;">{signal}</div>
      </div>
    </div>
    <div class="market-summary">
      {summary.get('summary_text', '이번 주 시장 동향을 분석했습니다.')}
    </div>
  </div>

  <div class="card-footer">
    <div class="footer-url">salkkamalka.com</div>
    <div class="footer-date">매주 월요일 아침 7시 발송</div>
  </div>
</div>


<!-- ════════════════════════════════
     CARD 2: 주목 단지
════════════════════════════════ -->
<div class="card" id="card2">
  <div class="card-header">
    <div>
      <div class="brand">살까말까</div>
      <div class="region-tag">이번 주 주목 단지</div>
    </div>
    <div class="vol-badge">Vol.{vol:03d}</div>
  </div>

  <div class="card2-body">
    <div class="card2-label">THIS WEEK'S PICKS</div>
    <div class="card2-title">AI가 고른<br>주목 단지 {len(complexes)}곳</div>
    <div class="complex-list">
      {complex_cards if complex_cards else '<div class="complex-row"><span class="complex-name" style="color:rgba(250,247,242,0.4)">이번 주 주목 단지 없음</span></div>'}
    </div>
    <div class="card2-note">
      📊 국토부 실거래 데이터 기반 · 거래 빈도 + 가격 구조 분석<br>
      단지별 상세 임장 서술은 뉴스레터 구독 후 확인하세요
    </div>
  </div>

  <div class="card-footer">
    <div class="footer-url">salkkamalka.com</div>
    <div class="footer-date">AI 임장 서술 · 무료 구독</div>
  </div>
</div>


<!-- ════════════════════════════════
     CARD 3: 타이밍 신호 + CTA
════════════════════════════════ -->
<div class="card" id="card3">
  <div class="card-header" style="background: rgba(255,255,255,0.05); border-bottom-color: {theme['badge']};">
    <div>
      <div class="brand" style="color: {theme['badge']};">살까말까</div>
      <div class="region-tag">이번 주 타이밍 신호</div>
    </div>
    <div class="vol-badge" style="background:{theme['badge']};">Vol.{vol:03d}</div>
  </div>

  <div class="card3-body">
    <div class="signal-badge">
      <span class="signal-emoji">{theme['emoji']}</span>
      데이터 기반 신호
    </div>
    <div class="signal-title">{signal}</div>
    <div class="signal-reason">{timing_reason[:120] + '...' if len(timing_reason) > 120 else timing_reason}</div>
    <div class="signal-hint">💡 {timing_hint}</div>
    <div class="cta-box">
      <div class="cta-text">
        매주 월요일 아침 7시<br>
        <strong>무료로 받아보기</strong>
      </div>
      <div class="cta-arrow">salkkamalka.com →</div>
    </div>
  </div>

  <div class="card-footer" style="background: rgba(255,255,255,0.04); border-top-color: rgba(255,255,255,0.1);">
    <div class="footer-url" style="color:{theme['badge']};">salkkamalka.com</div>
    <div class="footer-date">본 정보는 투자 권유가 아닙니다</div>
  </div>
</div>

</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="살까말까 인스타그램 카드뉴스 생성기")
    parser.add_argument("--summary",  default="data/trades_summary.json")
    parser.add_argument("--timing",   default="data/timing_result.json")
    parser.add_argument("--trades",   default="data/notable_trades.json")
    parser.add_argument("--vol",      type=int, default=1)
    parser.add_argument("--region",   default="마포구")
    parser.add_argument("--date",     default=datetime.now().strftime("%Y.%m.%d"))
    args = parser.parse_args()

    summary = load_json(args.summary) if os.path.exists(args.summary) else {}
    timing  = load_json(args.timing)  if os.path.exists(args.timing)  else {}
    trades  = load_json(args.trades)  if os.path.exists(args.trades)  else []

    html = generate_card_html(
        summary=summary,
        timing=timing,
        notable_trades=trades,
        vol=args.vol,
        region=args.region,
        issue_date=args.date,
    )

    out_dir = Path("data/cards")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"card_vol{args.vol:03d}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ 카드뉴스 생성 완료: {out_path}")
    print("📸 브라우저에서 열어 각 카드를 1080×1080px로 스크린샷 후 인스타그램에 업로드하세요.")


if __name__ == "__main__":
    main()
