"""
reporter/builder.py
분석 결과를 HTML 이메일로 조립
"""

from datetime import datetime
import config


def build_newsletter(
    region: str,
    issue_num: int,
    summary: dict,
    market_summary_text: str,
    complexes: list[dict],          # [{"trade": TradeRecord, "description": str, "tag": str}]
    timing: dict,                   # {"signal": str, "reason": str, "hint": str}
    indicators: list[dict],         # [{"name": str, "status": str, "badge": str}]
    news_item: dict,                # {"title": str, "body": str, "impact": str}
    editor_summary: str,
) -> str:
    """
    HTML 뉴스레터 조립
    
    Returns:
        완성된 HTML 문자열
    """
    today = datetime.today()
    date_str = today.strftime("%Y년 %m월 %d일 %A").replace(
        "Monday","월요일").replace("Tuesday","화요일").replace(
        "Wednesday","수요일").replace("Thursday","목요일").replace(
        "Friday","금요일").replace("Saturday","토요일").replace(
        "Sunday","일요일")

    # 단지 카드 HTML 조립
    complex_cards_html = ""
    for c in complexes:
        trade = c["trade"]
        desc  = c.get("description", "")
        tag   = c.get("tag", "📌 이번 주 포커스")
        price_str = f"{trade.price / 10000:.1f}억원"
        
        complex_cards_html += f"""
        <div style="border:1px solid #e0d8cc; margin-bottom:16px;">
          <div style="padding:14px 18px; background:#1a1208; color:white; display:flex; justify-content:space-between; align-items:center;">
            <span style="font-family:'Noto Serif KR',serif; font-size:16px; font-weight:700;">{trade.complex_name} ({trade.area:.0f}㎡)</span>
            <span style="font-size:10px; font-weight:700; color:#e8a020; letter-spacing:0.1em;">{tag}</span>
          </div>
          <div style="padding:18px;">
            <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px;">
              <span style="font-size:11px; color:#8a7e6e; background:#f2ede4; padding:3px 10px; border:1px solid #e0d8cc;">실거래가 <strong style="color:#1a1208;">{price_str}</strong></span>
              <span style="font-size:11px; color:#8a7e6e; background:#f2ede4; padding:3px 10px; border:1px solid #e0d8cc;">층수 <strong style="color:#1a1208;">{trade.floor}층</strong></span>
              <span style="font-size:11px; color:#8a7e6e; background:#f2ede4; padding:3px 10px; border:1px solid #e0d8cc;">거래일 <strong style="color:#1a1208;">{trade.trade_date}</strong></span>
            </div>
            <div style="font-size:13px; line-height:1.85; color:#3d3428; white-space:pre-wrap;">{desc}</div>
          </div>
        </div>"""

    # 타이밍 인디케이터 HTML
    indicators_html = ""
    BADGE_STYLES = {
        "긍정":  "background:#d4edda; color:#155724;",
        "주의":  "background:#fff3cd; color:#856404;",
        "부정":  "background:#f8d7da; color:#721c24;",
        "중립":  "background:#e2e3e5; color:#383d41;",
    }
    for ind in indicators:
        badge_style = BADGE_STYLES.get(ind.get("badge", "중립"), BADGE_STYLES["중립"])
        indicators_html += f"""
        <div style="display:grid; grid-template-columns:120px 1fr 70px; gap:16px; align-items:center; padding:12px 16px; border-bottom:1px solid #e0d8cc; font-size:13px;">
          <div style="color:#8a7e6e; font-size:12px;">{ind['name']}</div>
          <div style="font-weight:500;">{ind['status']}</div>
          <div style="text-align:right;">
            <span style="font-size:10px; font-weight:700; letter-spacing:0.1em; padding:2px 8px; {badge_style}">{ind['badge']}</span>
          </div>
        </div>"""

    # 전체 HTML
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>살까말까 Vol.{issue_num:03d} — {region} 주간 브리핑</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700;900&family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0; padding:40px 20px; background:#e8e0d4; font-family:'Noto Sans KR',sans-serif; color:#1a1208;">
<div style="max-width:640px; margin:0 auto; background:#faf7f2; box-shadow:0 4px 40px rgba(0,0,0,0.15);">

  <!-- 헤더 -->
  <div style="border-bottom:3px double #1a1208;">
    <div style="display:flex; justify-content:space-between; padding:10px 32px; font-size:10px; color:#8a7e6e; border-bottom:1px solid #e0d8cc; letter-spacing:0.08em;">
      <span>{date_str}</span>
      <span>살까말까 · 내집마련 주간 브리핑</span>
      <span>{region} 특집</span>
    </div>
    <div style="text-align:center; padding:20px 32px 16px;">
      <div style="font-family:'Noto Serif KR',serif; font-size:48px; font-weight:900; letter-spacing:-0.02em; line-height:1;">
        살까<span style="color:#c8401a;">말까</span>
      </div>
      <div style="font-size:11px; color:#8a7e6e; letter-spacing:0.15em; margin-top:6px;">Weekly Real Estate Brief for Home Buyers</div>
    </div>
    <div style="display:flex; justify-content:space-between; padding:10px 32px; background:#1a1208; color:white; font-size:11px; letter-spacing:0.08em;">
      <span style="color:#e8a020; font-weight:700;">Vol. {issue_num:03d}</span>
      <span>내집마련을 준비하는 당신을 위한 주간 브리핑</span>
      <span>{region}</span>
    </div>
  </div>

  <div style="padding:0 32px;">

    <!-- 오프닝 -->
    <div style="padding:28px 0; border-bottom:1px solid #e0d8cc;">
      <div style="font-size:13px; color:#8a7e6e; margin-bottom:14px; letter-spacing:0.05em;">안녕하세요, 이번 주 살까말까입니다.</div>
      <div style="font-family:'Noto Serif KR',serif; font-size:16px; font-weight:700; line-height:1.7; margin-bottom:14px; color:#1a1208;">
        {market_summary_text}
      </div>
    </div>

    <!-- 섹션 1: 시장 온도계 -->
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#8a7e6e; white-space:nowrap;">01 · 이번 주 시장 온도계</span>
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
    </div>

    <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
      <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:20px;">
        <div style="font-family:'Noto Serif KR',serif; font-size:20px; font-weight:700;">{region} 주간 실거래 현황</div>
        <div style="font-size:11px; color:#8a7e6e; background:#f2ede4; padding:3px 10px; border:1px solid #e0d8cc;">
          {today.strftime("%Y. %m. %d")} 기준
        </div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr 1fr; border:1px solid #e0d8cc; margin-bottom:20px;">
        <div style="padding:18px 16px; border-right:1px solid #e0d8cc;">
          <div style="font-size:9px; letter-spacing:0.15em; text-transform:uppercase; color:#8a7e6e; margin-bottom:8px;">주간 거래량</div>
          <div style="font-family:'Noto Serif KR',serif; font-size:24px; font-weight:700;">{summary.get('total_count', 0)}건</div>
        </div>
        <div style="padding:18px 16px; border-right:1px solid #e0d8cc;">
          <div style="font-size:9px; letter-spacing:0.15em; text-transform:uppercase; color:#8a7e6e; margin-bottom:8px;">84㎡ 평균 실거래가</div>
          <div style="font-family:'Noto Serif KR',serif; font-size:24px; font-weight:700;">{summary.get('avg_price_84', 0) / 10000:.1f}억</div>
        </div>
        <div style="padding:18px 16px;">
          <div style="font-size:9px; letter-spacing:0.15em; text-transform:uppercase; color:#8a7e6e; margin-bottom:8px;">분석 단지 수</div>
          <div style="font-family:'Noto Serif KR',serif; font-size:24px; font-weight:700;">{len(complexes)}개</div>
        </div>
      </div>
    </div>

    <!-- 섹션 2: 주목할 단지 -->
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#8a7e6e; white-space:nowrap;">02 · 이번 주 주목할 단지</span>
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
    </div>
    <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
      {complex_cards_html}
    </div>

    <!-- 섹션 3: 타이밍 신호 -->
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#8a7e6e; white-space:nowrap;">03 · 실수요자 타이밍 신호</span>
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
    </div>
    <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
      <div style="font-family:'Noto Serif KR',serif; font-size:20px; font-weight:700; margin-bottom:20px;">지금 사야 할까요, 더 기다려야 할까요?</div>
      <div style="background:#1a1208; color:white; padding:24px; margin-bottom:20px;">
        <div style="font-size:9px; letter-spacing:0.25em; text-transform:uppercase; color:#e8a020; margin-bottom:10px;">이번 주 살까말까 판단</div>
        <div style="font-family:'Noto Serif KR',serif; font-size:24px; font-weight:900; margin-bottom:12px; line-height:1.2; color:#e8a020;">{timing.get('signal', '')}</div>
        <div style="font-size:13px; line-height:1.85; color:#c0b0a0;">{timing.get('reason', '')}</div>
        <div style="font-size:12px; margin-top:12px; padding-top:12px; border-top:1px solid #3a3020; color:#a09080;">{timing.get('hint', '')}</div>
      </div>
      <div style="border:1px solid #e0d8cc;">
        {indicators_html}
      </div>
    </div>

    <!-- 섹션 4: 이번 주 뉴스 -->
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#8a7e6e; white-space:nowrap;">04 · 이번 주 꼭 알아야 할 1건</span>
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
    </div>
    <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
      <div style="border:1px solid #e0d8cc; padding:20px;">
        <div style="font-size:9px; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:#c8401a; margin-bottom:10px;">📋 {news_item.get('category', '정책 변화')}</div>
        <div style="font-family:'Noto Serif KR',serif; font-size:18px; font-weight:700; margin-bottom:12px; line-height:1.4;">{news_item.get('title', '')}</div>
        <div style="font-size:13px; line-height:1.85; color:#3d3428; margin-bottom:14px;">{news_item.get('body', '')}</div>
        <div style="padding:12px 16px; background:#f2ede4; border-left:3px solid #c8401a; font-size:13px; line-height:1.7;">
          <strong style="color:#c8401a;">내집마련 실수요자라면:</strong> {news_item.get('impact', '')}
        </div>
      </div>
    </div>

    <!-- 편집장 총평 -->
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#8a7e6e; white-space:nowrap;">편집장의 한 마디</span>
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
    </div>
    <div style="padding:28px 0; border-bottom:1px solid #e0d8cc;">
      <div style="background:#1a1208; color:white; padding:24px;">
        <div style="font-size:9px; letter-spacing:0.25em; text-transform:uppercase; color:#e8a020; margin-bottom:12px;">AI 편집장의 주간 총평</div>
        <div style="font-family:'Noto Serif KR',serif; font-size:16px; line-height:1.8; margin-bottom:16px;">{editor_summary}</div>
        <div style="font-size:12px; color:#8a7e6e;">— 살까말까 AI 편집장, 매주 월요일 아침 7시</div>
      </div>
    </div>

  </div><!-- end body -->

  <!-- 푸터 -->
  <div style="padding:20px 32px; border-top:3px double #1a1208; text-align:center;">
    <div style="font-family:'Noto Serif KR',serif; font-size:20px; font-weight:900; margin-bottom:8px;">
      살까<span style="color:#c8401a;">말까</span>
    </div>
    <div style="font-size:11px; color:#8a7e6e; margin-bottom:6px;">
      <a href="#" style="color:#8a7e6e;">구독 관리</a> &nbsp;·&nbsp;
      <a href="#" style="color:#8a7e6e;">수신 거부</a> &nbsp;·&nbsp;
      <a href="#" style="color:#8a7e6e;">웹에서 보기</a>
    </div>
    <div style="font-size:10px; color:#b0a090;">
      본 브리핑은 정보 제공 목적이며 투자 권유가 아닙니다. 매수/매도 결정은 본인의 판단으로 하시기 바랍니다.
    </div>
  </div>

</div>
</body>
</html>"""

    return html


def save_html(html: str, filepath: str):
    """HTML 파일 저장"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[리포트] 저장 완료: {filepath}")
