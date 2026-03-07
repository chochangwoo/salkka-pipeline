"""
premium/builder.py
유료 구독자 전용 HTML 섹션 조립

무료 HTML 기반 위에 프리미엄 섹션을 삽입하는 방식.
"""

from datetime import datetime


def build_premium_newsletter(
    free_html: str,
    urgent_sales: list[dict] = None,
    jeonse_risks: list[dict] = None,
    comparison: dict = None,
    qna_items: list[dict] = None,
) -> str:
    """
    무료 HTML에 유료 전용 섹션을 추가

    Args:
        free_html: 무료 뉴스레터 HTML
        urgent_sales: 급매 알림 데이터 [{"trade": ..., "analysis": str, "urgency": str}]
        jeonse_risks: 전세 위험 데이터 [{"complex_name": str, "analysis": str, "level": str}]
        comparison: 단지 비교 {"histories": [...], "analysis": str} (월 1회)
        qna_items: Q&A [{"question": str, "answer": str}]
    Returns:
        프리미엄 HTML 문자열
    """
    premium_sections = ""

    # ── 급매 알림 섹션 ───────────────────────────────────────
    if urgent_sales:
        cards_html = ""
        for sale in urgent_sales:
            trade = sale["trade"]
            urgency = sale.get("urgency", "MEDIUM")
            urgency_color = "#dc3545" if urgency == "HIGH" else "#ffc107"
            urgency_text = "고긴급" if urgency == "HIGH" else "주의"
            drop_pct = sale.get("drop_rate", 0) * 100

            avg_recent = sale.get("avg_recent_price", sale.get("prev_price", 0))
            avg_drop_pct = max(0, (avg_recent - trade.price) / avg_recent * 100) if avg_recent > 0 else 0
            recent_count = sale.get("recent_trade_count", 2)

            cards_html += f"""
            <div style="border:1px solid #e0d8cc; margin-bottom:12px; padding:16px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="font-family:'Noto Serif KR',serif; font-size:15px; font-weight:700;">{trade.complex_name} ({trade.area:.0f}㎡)</span>
                <span style="font-size:10px; font-weight:700; color:white; background:{urgency_color}; padding:2px 8px; letter-spacing:0.1em;">{urgency_text} -{drop_pct:.1f}%</span>
              </div>
              <div style="padding:12px; background:#f9f6f0; border:1px solid #e0d8cc; margin-bottom:12px;">
                <div style="font-size:10px; color:#8a7e6e; letter-spacing:0.1em; margin-bottom:8px;">가격 구조 분석</div>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                  <span style="font-size:11px; background:white; padding:3px 8px; border:1px solid #e0d8cc;">최근 {recent_count}건 평균 <strong>{avg_recent / 10000:.1f}억</strong></span>
                  <span style="font-size:11px; background:white; padding:3px 8px; border:1px solid #e0d8cc;">직전 거래 <strong>{sale.get('prev_price', 0) / 10000:.1f}억</strong></span>
                  <span style="font-size:11px; background:white; padding:3px 8px; border:1px solid #e0d8cc;">이번 거래 <strong style="color:#c8401a;">{trade.price / 10000:.1f}억</strong></span>
                  <span style="font-size:11px; background:white; padding:3px 8px; border:1px solid #e0d8cc;">평균 대비 <strong style="color:#c8401a;">-{avg_drop_pct:.1f}%</strong></span>
                </div>
              </div>
              <div style="font-size:13px; line-height:1.85; color:#3d3428;">{sale.get('analysis', '')}</div>
            </div>"""

        premium_sections += f"""
        <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
          <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#c8401a; white-space:nowrap;">PREMIUM · 급매 알림</span>
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
        </div>
        <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
          <div style="font-family:'Noto Serif KR',serif; font-size:18px; font-weight:700; margin-bottom:16px;">이번 주 급매 감지 ({len(urgent_sales)}건)</div>
          {cards_html}
        </div>"""

    # ── 전세가율 위험 경보 ───────────────────────────────────
    if jeonse_risks:
        risk_cards = ""
        for risk in jeonse_risks:
            level = risk.get("level", "CAUTION")
            level_color = "#dc3545" if level == "DANGER" else "#ffc107"
            level_text = "위험" if level == "DANGER" else "주의"

            risk_cards += f"""
            <div style="border:1px solid #e0d8cc; margin-bottom:12px; padding:16px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="font-family:'Noto Serif KR',serif; font-size:15px; font-weight:700;">{risk['complex_name']}</span>
                <span style="font-size:10px; font-weight:700; color:white; background:{level_color}; padding:2px 8px;">전세가율 {risk['jeonse_rate'] * 100:.0f}% · {level_text}</span>
              </div>
              <div style="font-size:13px; line-height:1.85; color:#3d3428;">{risk.get('analysis', '')}</div>
            </div>"""

        premium_sections += f"""
        <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
          <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#c8401a; white-space:nowrap;">PREMIUM · 전세가율 위험 경보</span>
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
        </div>
        <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
          {risk_cards}
        </div>"""

    # ── 단지 비교 리포트 (월 1회) ────────────────────────────
    if comparison and comparison.get("histories"):
        rows_html = ""
        for h in comparison["histories"]:
            trend_color = "#155724" if h["trend"] == "상승" else "#721c24" if h["trend"] == "하락" else "#856404"
            rows_html += f"""
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:8px; padding:10px 12px; border-bottom:1px solid #e0d8cc; font-size:12px;">
              <div style="font-weight:600;">{h['complex_name']}</div>
              <div>{h['current_price'] / 10000:.1f}억</div>
              <div>고점 대비 -{h['drop_from_peak'] * 100:.1f}%</div>
              <div style="color:{trend_color}; font-weight:600;">{h['trend']}</div>
            </div>"""

        premium_sections += f"""
        <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
          <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#c8401a; white-space:nowrap;">PREMIUM · 단지 비교 리포트</span>
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
        </div>
        <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
          <div style="font-family:'Noto Serif KR',serif; font-size:18px; font-weight:700; margin-bottom:16px;">이번 달 단지 비교</div>
          <div style="border:1px solid #e0d8cc; margin-bottom:16px;">
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:8px; padding:10px 12px; background:#f2ede4; font-size:11px; font-weight:600; color:#8a7e6e;">
              <div>단지명</div><div>현재가</div><div>고점 대비</div><div>추세</div>
            </div>
            {rows_html}
          </div>
          <div style="font-size:13px; line-height:1.85; color:#3d3428;">{comparison.get('analysis', '')}</div>
        </div>"""

    # ── 구독자 Q&A ───────────────────────────────────────────
    if qna_items:
        qna_html = ""
        for i, item in enumerate(qna_items):
            if not item.get("answer"):
                continue
            qna_html += f"""
            <div style="margin-bottom:16px; padding:16px; border:1px solid #e0d8cc;">
              <div style="font-size:12px; color:#c8401a; font-weight:700; margin-bottom:8px;">Q{i+1}.</div>
              <div style="font-family:'Noto Serif KR',serif; font-size:15px; font-weight:700; margin-bottom:12px; line-height:1.5;">{item['question']}</div>
              <div style="font-size:13px; line-height:1.85; color:#3d3428; padding-top:12px; border-top:1px solid #e0d8cc;">{item['answer']}</div>
            </div>"""

        if qna_html:
            premium_sections += f"""
            <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
              <div style="flex:1; height:1px; background:#e0d8cc;"></div>
              <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#c8401a; white-space:nowrap;">PREMIUM · 구독자 Q&A</span>
              <div style="flex:1; height:1px; background:#e0d8cc;"></div>
            </div>
            <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
              <div style="font-family:'Noto Serif KR',serif; font-size:18px; font-weight:700; margin-bottom:16px;">이번 주 구독자 질문</div>
              {qna_html}
            </div>"""

    if not premium_sections:
        return free_html

    # 무료 HTML의 푸터 직전에 프리미엄 섹션 삽입
    # 푸터 시작점: "</div><!-- end body -->" 찾기
    insertion_point = free_html.find("</div><!-- end body -->")
    if insertion_point == -1:
        # 폴백: 마지막 </div> 직전
        insertion_point = free_html.rfind("</div>")

    premium_html = (
        free_html[:insertion_point]
        + premium_sections
        + free_html[insertion_point:]
    )

    return premium_html
