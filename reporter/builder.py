"""
reporter/builder.py
분석 결과를 HTML 이메일로 조립

v3: 예산대 × 권역 비교 형식, 투표 섹션, 프리미엄 유도 장치 포함
"""

from datetime import datetime
import config


# ── 예산대 설정 ─────────────────────────────────────────────────
BUDGET_TIERS = [
    {"label": "3~4억", "min": 30000, "max": 40000},
    {"label": "5~6억", "min": 50000, "max": 60000},
    {"label": "7억 이상", "min": 70000, "max": 999999},
]


def build_newsletter(
    region: str,
    issue_num: int,
    summary: dict,
    market_summary_text: str,
    complexes: list[dict],
    timing: dict,
    indicators: list[dict],
    news_item: dict,
    editor_summary: str,
    budget_label: str = "",
    comparison_regions: list[dict] = None,
    comparison_analysis: dict = None,
    urgent_sales_preview: list[dict] = None,
) -> str:
    """
    HTML 뉴스레터 조립 (v3 — 예산대×권역 비교)

    Args:
        budget_label: 이번 주 예산대 (예: "5~6억")
        comparison_regions: 비교 지역 데이터 리스트
        comparison_analysis: GPT 비교 분석 결과 {"recommended": str, "analysis": str}
        urgent_sales_preview: 급매 미리보기 (무료 1건 + 블러)
    """
    today = datetime.today()
    date_str = today.strftime("%Y년 %m월 %d일 %A").replace(
        "Monday","월요일").replace("Tuesday","화요일").replace(
        "Wednesday","수요일").replace("Thursday","목요일").replace(
        "Friday","금요일").replace("Saturday","토요일").replace(
        "Sunday","일요일")

    # 헤더 테마 타이틀
    if budget_label and comparison_regions:
        region_names = ", ".join(r.get("region", "") for r in comparison_regions)
        theme_title = f"이번 주 테마: {budget_label}으로 {region_names} 어디가 나을까?"
    else:
        theme_title = f"{region} 주간 실거래 브리핑"

    # 단지 카드 HTML 조립
    complex_cards_html = ""
    for c in complexes:
        trade = c["trade"]
        desc  = c.get("description", "")
        if not desc:
            continue
        tag   = c.get("tag", "이번 주 포커스")
        price_str = f"{trade.price / 10000:.1f}억원"
        peak_info = c.get("price_from_peak", "")
        jeonse_info = c.get("jeonse_rate_complex", "")

        price_structure_html = ""
        if peak_info:
            price_structure_html += f'<span style="font-size:11px; color:#8a7e6e; background:#f2ede4; padding:3px 10px; border:1px solid #e0d8cc;">고점 대비 <strong style="color:#c8401a;">{peak_info}</strong></span>'
        if jeonse_info:
            price_structure_html += f'<span style="font-size:11px; color:#8a7e6e; background:#f2ede4; padding:3px 10px; border:1px solid #e0d8cc;">전세가율 <strong style="color:#1a1208;">{jeonse_info}</strong></span>'

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
              {price_structure_html}
            </div>
            {c.get("naver_html", "")}
            <div style="font-size:13px; line-height:1.85; color:#3d3428; white-space:pre-wrap;">{desc}</div>
          </div>
        </div>"""

    # 지역 비교 테이블 HTML
    comparison_html = ""
    if comparison_regions and len(comparison_regions) >= 2:
        recommended = comparison_analysis.get("recommended", "") if comparison_analysis else ""
        analysis_text = comparison_analysis.get("analysis", "") if comparison_analysis else ""

        header_cols = ""
        for r in comparison_regions:
            is_rec = recommended and recommended in r.get("region", "")
            bg = "background:#c8401a; color:white;" if is_rec else "background:#f2ede4; color:#3d3428;"
            badge = ' <span style="font-size:8px; background:#e8a020; color:#1a1208; padding:1px 6px; font-weight:900;">추천</span>' if is_rec else ""
            header_cols += f'<div style="padding:12px 8px; text-align:center; font-weight:700; {bg}">{r["region"]}{badge}</div>'

        def _make_row(label, key, fmt=""):
            cols = ""
            for r in comparison_regions:
                val = r.get(key, "")
                if not val and val != 0:
                    val = "-"
                elif fmt == "억" and isinstance(val, (int, float)) and val > 0:
                    val = f"{val / 10000:.1f}억"
                elif fmt == "%" and isinstance(val, (int, float)):
                    val = f"{val:.0f}%"
                elif fmt == "건" and isinstance(val, (int, float)):
                    val = f"{val}건"
                is_rec = recommended and recommended in r.get("region", "")
                bg = "background:#fff8f5;" if is_rec else ""
                cols += f'<div style="padding:10px 8px; text-align:center; border-top:1px solid #e0d8cc; font-size:12px; {bg}">{val}</div>'
            return f"""
            <div style="display:grid; grid-template-columns:100px {'1fr ' * len(comparison_regions)}; border-bottom:1px solid #e0d8cc;">
              <div style="padding:10px 8px; font-size:11px; color:#8a7e6e; border-top:1px solid #e0d8cc;">{label}</div>
              {cols}
            </div>"""

        rows = ""
        rows += _make_row("84㎡ 평균가", "avg_84", "억")
        rows += _make_row("전세가율", "jeonse_rate", "%")
        rows += _make_row("최근 거래량", "trade_count", "건")
        rows += _make_row("강남 접근성", "gangnam_access")
        rows += _make_row("학군", "school_score")
        if any(r.get("editor_score") for r in comparison_regions):
            rows += _make_row("편집장 추천", "editor_score")

        analysis_block = ""
        if analysis_text:
            analysis_block = f"""
            <div style="padding:14px; background:#f9f6f0; border-left:3px solid #c8401a; margin-top:16px; font-size:13px; line-height:1.8; color:#3d3428;">
              {analysis_text}
            </div>"""

        comparison_html = f"""
        <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
          <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; color:#c8401a; white-space:nowrap;">01 · 지역 비교 분석</span>
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
        </div>
        <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
          <div style="font-family:'Noto Serif KR',serif; font-size:20px; font-weight:700; margin-bottom:16px;">{budget_label}으로 어디가 나을까?</div>
          <div style="border:1px solid #e0d8cc; margin-bottom:16px;">
            <div style="display:grid; grid-template-columns:100px {'1fr ' * len(comparison_regions)};">
              <div style="padding:12px 8px; font-size:11px; font-weight:600; color:#8a7e6e;">비교 항목</div>
              {header_cols}
            </div>
            {rows}
          </div>
          {analysis_block}
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
        indicators_html += f"""
        <div style="display:grid; grid-template-columns:120px 1fr 70px; gap:16px; align-items:center; padding:12px 16px; border-bottom:1px solid #e0d8cc; font-size:13px;">
          <div style="color:#8a7e6e; font-size:12px;">{ind['name']}</div>
          <div style="font-weight:500;">{ind['status']}</div>
          <div style="text-align:right;">
            <span style="font-size:10px; font-weight:700; letter-spacing:0.1em; padding:2px 8px; {BADGE_STYLES.get(ind.get('badge', '중립'), BADGE_STYLES['중립'])}">{ind['badge']}</span>
          </div>
        </div>"""

    # 급매 프리미엄 유도 HTML (무료 1건 + 블러)
    urgent_preview_html = ""
    if urgent_sales_preview:
        total = len(urgent_sales_preview)
        first = urgent_sales_preview[0] if urgent_sales_preview else None
        if first:
            trade = first["trade"]
            drop_pct = first.get("drop_rate", 0) * 100
            urgent_preview_html = f"""
        <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
          <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; color:#c8401a; white-space:nowrap;">급매 속보</span>
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
        </div>
        <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
          <div style="border:1px solid #e0d8cc; padding:16px; margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <span style="font-weight:700;">{trade.complex_name} ({trade.area:.0f}㎡)</span>
              <span style="font-size:10px; font-weight:700; color:white; background:#c8401a; padding:2px 8px;">-{drop_pct:.1f}%</span>
            </div>
            <div style="font-size:13px; color:#3d3428;">{trade.price / 10000:.1f}억 (직전 대비 {drop_pct:.1f}% 하락)</div>
          </div>"""

            if total > 1:
                urgent_preview_html += f"""
          <div style="position:relative; border:1px solid #e0d8cc; padding:16px; margin-bottom:16px;">
            <div style="filter:blur(5px); -webkit-filter:blur(5px); pointer-events:none;">
              <div style="font-weight:700; margin-bottom:8px;">급매 단지 {total - 1}건 추가</div>
              <div style="font-size:13px; color:#8a7e6e;">자세한 분석과 가격 구조를 확인하세요.</div>
            </div>
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); z-index:1;">
              <a href="#" style="display:inline-block; padding:10px 24px; background:#c8401a; color:white; text-decoration:none; font-size:13px; font-weight:700;">
                이번 주 급매 {total}건 전체 보기 &rarr;
              </a>
            </div>
          </div>"""

            urgent_preview_html += "</div>"

    # 맞춤 분석 유도 + 관심 단지 알림 CTA
    freemium_cta_html = f"""
    <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
      <div style="background:#f9f6f0; border:1px solid #e0d8cc; padding:20px; margin-bottom:12px; text-align:center;">
        <div style="font-size:13px; color:#3d3428; margin-bottom:12px; line-height:1.7;">
          내 상황(예산, 직장, 가족)을 알려주시면<br>맞춤 분석을 보내드립니다.
        </div>
        <a href="#" style="display:inline-block; padding:10px 28px; background:#1a1208; color:#e8a020; text-decoration:none; font-size:12px; font-weight:700; letter-spacing:0.05em;">
          맞춤 분석 요청하기 &rarr;
        </a>
      </div>
      <div style="background:#f9f6f0; border:1px solid #e0d8cc; padding:20px; text-align:center;">
        <div style="font-size:13px; color:#3d3428; margin-bottom:12px; line-height:1.7;">
          관심 단지를 등록하면 급매, 가격 변동 시<br>알림을 보내드립니다.
        </div>
        <a href="#" style="display:inline-block; padding:10px 28px; background:#1a1208; color:#e8a020; text-decoration:none; font-size:12px; font-weight:700; letter-spacing:0.05em;">
          관심 단지 등록하기 &rarr;
        </a>
      </div>
    </div>"""

    # 투표 섹션 HTML
    vote_regions = ["안양시 동안구", "마포구", "성남시 분당구"]
    vote_budgets = ["3~4억", "5~6억", "7억 이상"]

    vote_region_btns = ""
    for vr in vote_regions:
        vote_region_btns += f"""
          <a href="#" style="display:inline-block; padding:8px 16px; margin:4px; border:1px solid #e0d8cc; background:#faf7f2; color:#3d3428; text-decoration:none; font-size:12px; font-weight:500;">{vr}</a>"""

    vote_budget_btns = ""
    for vb in vote_budgets:
        vote_budget_btns += f"""
          <a href="#" style="display:inline-block; padding:8px 16px; margin:4px; border:1px solid #e0d8cc; background:#faf7f2; color:#3d3428; text-decoration:none; font-size:12px; font-weight:500;">{vb}</a>"""

    voting_html = f"""
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; color:#8a7e6e; white-space:nowrap;">다음 주 주제 투표</span>
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
    </div>
    <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
      <div style="font-family:'Noto Serif KR',serif; font-size:18px; font-weight:700; margin-bottom:16px; text-align:center;">
        다음 주에 분석했으면 하는 조합을 골라주세요
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:11px; color:#8a7e6e; margin-bottom:8px; font-weight:600;">어떤 지역이 궁금하세요?</div>
        <div style="display:flex; flex-wrap:wrap; gap:0;">
          {vote_region_btns}
        </div>
      </div>
      <div>
        <div style="font-size:11px; color:#8a7e6e; margin-bottom:8px; font-weight:600;">예산대는?</div>
        <div style="display:flex; flex-wrap:wrap; gap:0;">
          {vote_budget_btns}
        </div>
      </div>
      <div style="font-size:10px; color:#b0a090; margin-top:12px; text-align:center;">
        가장 많이 선택된 조합이 다음 주 뉴스레터 주제로 반영됩니다.
      </div>
    </div>"""

    # 섹션 번호 관리 (비교 테이블이 있으면 01번으로 사용)
    section_num = 1
    if comparison_html:
        section_num = 2  # 비교가 01이므로 시장 온도계는 02부터

    # 시장 온도계 (데이터가 있을 때만)
    market_section = ""
    if summary.get("total_count", 0) > 0:
        market_section = f"""
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#8a7e6e; white-space:nowrap;">{section_num:02d} · 이번 주 시장 온도계</span>
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
    </div>"""
        section_num += 1

    # 단지 섹션 (데이터가 있을 때만)
    complex_section = ""
    if complex_cards_html:
        complex_section = f"""
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#8a7e6e; white-space:nowrap;">{section_num:02d} · 이번 주 주목할 단지</span>
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
    </div>
    <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
      {complex_cards_html}
    </div>"""
        section_num += 1

    # 타이밍 섹션 (데이터가 있을 때만)
    timing_section = ""
    if timing.get("signal"):
        timing_section = f"""
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#8a7e6e; white-space:nowrap;">{section_num:02d} · 실수요자 타이밍 신호</span>
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
    </div>"""
        section_num += 1

    # 뉴스 섹션 (데이터가 있을 때만)
    news_section = ""
    if news_item.get("title"):
        news_section = f"""
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#8a7e6e; white-space:nowrap;">{section_num:02d} · 이번 주 꼭 알아야 할 1건</span>
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
    </div>
    <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
      <div style="border:1px solid #e0d8cc; padding:20px;">
        <div style="font-size:9px; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:#c8401a; margin-bottom:10px;">{news_item.get('category', '')}</div>
        <div style="font-family:'Noto Serif KR',serif; font-size:18px; font-weight:700; margin-bottom:12px; line-height:1.4;">{news_item.get('title', '')}</div>
        <div style="font-size:13px; line-height:1.85; color:#3d3428; margin-bottom:14px;">{news_item.get('body', '')}</div>
        <div style="padding:12px 16px; background:#f2ede4; border-left:3px solid #c8401a; font-size:13px; line-height:1.7;">
          <strong style="color:#c8401a;">내집마련 실수요자라면:</strong> {news_item.get('impact', '')}
        </div>
      </div>
    </div>"""

    # 편집장 총평 (있을 때만)
    editor_section = ""
    if editor_summary:
        editor_section = f"""
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#8a7e6e; white-space:nowrap;">편집장의 한 마디</span>
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
    </div>
    <div style="padding:28px 0; border-bottom:1px solid #e0d8cc;">
      <div style="background:#1a1208; color:white; padding:24px;">
        <div style="font-family:'Noto Serif KR',serif; font-size:16px; line-height:1.8; margin-bottom:16px;">{editor_summary}</div>
        <div style="font-size:12px; color:#8a7e6e;">-- 살까말까 편집장, 매주 월요일 아침 7시</div>
      </div>
    </div>"""

    # 전체 HTML 조립
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>살까말까 Vol.{issue_num:03d} -- {theme_title}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700;900&family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0; padding:40px 20px; background:#e8e0d4; font-family:'Noto Sans KR',sans-serif; color:#1a1208;">
<div style="max-width:640px; margin:0 auto; background:#faf7f2; box-shadow:0 4px 40px rgba(0,0,0,0.15);">

  <!-- 헤더 -->
  <div style="border-bottom:3px double #1a1208;">
    <div style="display:flex; justify-content:space-between; padding:10px 32px; font-size:10px; color:#8a7e6e; border-bottom:1px solid #e0d8cc; letter-spacing:0.08em;">
      <span>{date_str}</span>
      <span>살까말까 · 내집마련 주간 브리핑</span>
      <span>Vol. {issue_num:03d}</span>
    </div>
    <div style="text-align:center; padding:20px 32px 16px;">
      <div style="font-family:'Noto Serif KR',serif; font-size:48px; font-weight:900; letter-spacing:-0.02em; line-height:1;">
        살까<span style="color:#c8401a;">말까</span>
      </div>
      <div style="font-size:11px; color:#8a7e6e; letter-spacing:0.15em; margin-top:6px;">Weekly Real Estate Brief for Home Buyers</div>
    </div>
    <div style="padding:12px 32px; background:#1a1208; color:white; text-align:center;">
      <div style="font-family:'Noto Serif KR',serif; font-size:16px; font-weight:700; color:#e8a020; line-height:1.4;">
        {theme_title}
      </div>
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

    {comparison_html}
    {market_section}
    {complex_section}
    {urgent_preview_html}
    {timing_section}
    {news_section}
    {editor_section}
    {freemium_cta_html}

  </div><!-- end body -->

    {voting_html}

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
