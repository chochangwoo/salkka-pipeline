"""
content/builder.py
바이럴 콘텐츠용 HTML 빌더

랭킹, 비교, 공급 리스크 등 콘텐츠 블록 → HTML 변환
뉴스레터 삽입 + SNS 카드용 독립 HTML 모두 지원
"""

from content.generator import ContentBlock, RankingItem
from collector.naver_land import ComplexInfo
from collector.supply import SupplyForecast


# ── 단지 상세 정보 카드 (네이버 데이터) ────────────────────────

def build_complex_info_html(info: ComplexInfo) -> str:
    """단지 상세 정보 → 인라인 HTML 카드"""
    if not info.total_households:
        return ""

    tags = []
    tags.append(f"총 {info.total_households:,}세대")
    if info.total_dong:
        tags.append(f"{info.total_dong}개 동")
    if info.max_floor:
        tags.append(f"최고 {info.max_floor}층")
    if info.construction_company:
        tags.append(info.construction_company)
    if info.parking_per_household:
        tags.append(f"주차 {info.parking_per_household:.1f}대/세대")

    tags_html = "".join(
        f'<span style="font-size:11px; background:#f2ede4; padding:2px 8px; '
        f'border:1px solid #e0d8cc; color:#3d3428;">{t}</span>'
        for t in tags
    )

    market_html = ""
    if info.sale_count:
        price_str = ""
        if info.min_sale_price and info.max_sale_price:
            price_str = f" ({info.min_sale_price/10000:.1f}~{info.max_sale_price/10000:.1f}억)"
        market_html += (
            f'<div style="font-size:12px; color:#3d3428;">'
            f'매매 매물 <strong style="color:#c8401a;">{info.sale_count}건</strong>{price_str}'
        )
        if info.jeonse_count:
            market_html += f' | 전세 매물 <strong>{info.jeonse_count}건</strong>'
        market_html += '</div>'

    return f"""
    <div style="padding:10px 16px; background:#f9f6f0; border:1px solid #e0d8cc; margin-bottom:12px;">
      <div style="font-size:10px; color:#8a7e6e; letter-spacing:0.1em; margin-bottom:6px;">단지 정보 (네이버 부동산)</div>
      <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:6px;">{tags_html}</div>
      {market_html}
    </div>"""


# ── 공급 리스크 섹션 ───────────────────────────────────────────

def build_supply_section_html(forecast: SupplyForecast) -> str:
    """공급 전망 → 뉴스레터 섹션 HTML"""
    if not forecast.items:
        return ""

    risk_colors = {
        "낮음": "#155724", "보통": "#856404",
        "높음": "#c8401a", "매우높음": "#dc3545",
    }
    risk_bg = {
        "낮음": "#d4edda", "보통": "#fff3cd",
        "높음": "#f8d7da", "매우높음": "#f8d7da",
    }
    color = risk_colors.get(forecast.risk_level, "#856404")
    bg = risk_bg.get(forecast.risk_level, "#fff3cd")

    # 연도별 바
    yearly_html = ""
    max_count = max(forecast.yearly_breakdown.values()) if forecast.yearly_breakdown else 1
    for year, count in sorted(forecast.yearly_breakdown.items()):
        bar_width = min(100, int(count / max_count * 100))
        yearly_html += f"""
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
          <span style="font-size:11px; color:#8a7e6e; width:50px;">{year}년</span>
          <div style="flex:1; background:#f2ede4; height:18px; position:relative;">
            <div style="width:{bar_width}%; background:{color}; height:100%; opacity:0.7;"></div>
          </div>
          <span style="font-size:11px; font-weight:600; width:70px; text-align:right;">{count:,}세대</span>
        </div>"""

    # 주요 단지 리스트
    items_html = ""
    for item in forecast.items[:5]:
        items_html += f"""
        <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #f2ede4; font-size:12px;">
          <div>
            <span style="font-weight:600;">{item.name}</span>
            <span style="color:#8a7e6e; margin-left:8px;">{item.supply_type}</span>
          </div>
          <div style="text-align:right;">
            <strong>{item.households:,}세대</strong>
            <span style="color:#8a7e6e; margin-left:8px;">{item.expected_date}</span>
          </div>
        </div>"""

    return f"""
    <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
      <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; color:#8a7e6e; white-space:nowrap;">05 &middot; 공급 리스크 분석</span>
      <div style="flex:1; height:1px; background:#e0d8cc;"></div>
    </div>
    <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <div style="font-family:'Noto Serif KR',serif; font-size:20px; font-weight:700;">향후 3년 공급 전망</div>
        <span style="font-size:11px; font-weight:700; padding:3px 10px; background:{bg}; color:{color};">
          공급 리스크: {forecast.risk_level}
        </span>
      </div>
      <div style="background:#1a1208; color:white; padding:20px; margin-bottom:16px;">
        <div style="font-family:'Noto Serif KR',serif; font-size:28px; font-weight:900; color:#e8a020; margin-bottom:4px;">
          {forecast.total_supply_3y:,}세대
        </div>
        <div style="font-size:12px; color:#a09080;">향후 3년 예정 공급량</div>
      </div>
      <div style="margin-bottom:16px;">{yearly_html}</div>
      <div style="border:1px solid #e0d8cc; padding:12px;">{items_html}</div>
    </div>"""


# ── 랭킹 콘텐츠 섹션 ──────────────────────────────────────────

def build_ranking_section_html(block: ContentBlock) -> str:
    """랭킹 ContentBlock → 뉴스레터 HTML"""
    if not block.items:
        return ""

    items_html = ""
    for item in block.items:
        # 1위는 강조
        is_top = item.rank == 1
        rank_style = (
            "background:#c8401a; color:white; font-weight:900;"
            if is_top else
            "background:#f2ede4; color:#3d3428; font-weight:700;"
        )
        value_color = "#c8401a" if item.value_label.startswith("-") else "#155724"

        items_html += f"""
        <div style="display:flex; align-items:center; gap:12px; padding:10px 14px; border-bottom:1px solid #f2ede4;">
          <span style="width:28px; height:28px; display:flex; align-items:center; justify-content:center; font-size:12px; {rank_style}">{item.rank}</span>
          <div style="flex:1;">
            <div style="font-size:13px; font-weight:600;">{item.complex_name}</div>
            <div style="font-size:11px; color:#8a7e6e;">{item.sub_info}</div>
          </div>
          <span style="font-size:16px; font-weight:900; color:{value_color};">{item.value_label}</span>
        </div>"""

    story_html = ""
    if block.story:
        story_html = f"""
        <div style="padding:14px; background:#f9f6f0; border-left:3px solid #c8401a; margin-top:16px; font-size:13px; line-height:1.8; color:#3d3428;">
          {block.story}
        </div>"""

    cta_html = ""
    if block.cta:
        cta_html = f"""
        <div style="text-align:center; margin-top:16px;">
          <span style="font-size:12px; color:#c8401a; font-weight:600;">{block.cta}</span>
        </div>"""

    return f"""
    <div style="padding:24px 0; border-bottom:1px solid #e0d8cc;">
      <div style="font-family:'Noto Serif KR',serif; font-size:20px; font-weight:700; margin-bottom:4px;">{block.title}</div>
      <div style="font-size:11px; color:#8a7e6e; margin-bottom:16px;">{block.subtitle}</div>
      <div style="border:1px solid #e0d8cc;">
        {items_html}
      </div>
      {story_html}
      {cta_html}
    </div>"""


# ── 전체 콘텐츠 섹션 조립 ─────────────────────────────────────

def build_content_sections_html(
    content_blocks: list[ContentBlock],
    supply_forecast: SupplyForecast = None,
    complex_infos: dict = None,
) -> str:
    """모든 콘텐츠 블록 → 뉴스레터 삽입용 HTML"""
    html = ""

    # 콘텐츠 블록 (랭킹, 비교 등)
    if content_blocks:
        html += """
        <div style="display:flex; align-items:center; gap:12px; margin:32px 0 20px;">
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
          <span style="font-size:9px; font-weight:700; letter-spacing:0.25em; color:#c8401a; white-space:nowrap;">SALKKAMALKKA DATA</span>
          <div style="flex:1; height:1px; background:#e0d8cc;"></div>
        </div>"""

        for block in content_blocks:
            html += build_ranking_section_html(block)

    # 공급 리스크
    if supply_forecast and supply_forecast.items:
        html += build_supply_section_html(supply_forecast)

    return html
