"""
content/generator.py
바이럴 콘텐츠 생성기

데이터를 "공유하고 싶은 스토리"로 변환.
충격 데이터 / 급매 탐지 / 랭킹 / 비교 콘텐츠 생성.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)


@dataclass
class RankingItem:
    """랭킹 한 건"""
    rank: int
    complex_name: str
    region: str = ""
    value: float = 0           # 핵심 수치 (%, 만원 등)
    value_label: str = ""      # 수치 설명 (예: "-21%", "8.5억")
    sub_info: str = ""         # 부가 정보


@dataclass
class ContentBlock:
    """생성된 콘텐츠 블록"""
    content_type: str          # "ranking" / "comparison" / "shock" / "supply_risk"
    title: str                 # 콘텐츠 제목
    subtitle: str = ""         # 부제
    items: list = field(default_factory=list)   # RankingItem 리스트
    story: str = ""            # AI 생성 스토리
    cta: str = ""              # Call to Action


# ── 랭킹 생성기 ───────────────────────────────────────────────

def generate_drop_ranking(trades: list, top_n: int = 10) -> ContentBlock:
    """
    가장 많이 떨어진 아파트 TOP N
    동일 단지 내 최고가 대비 최신 거래 하락률 기준
    """
    complex_data = _group_by_complex(trades)
    drops = []

    for key, group in complex_data.items():
        if len(group) < 2:
            continue
        sorted_g = sorted(group, key=lambda x: x.trade_date)
        peak_price = max(t.price for t in sorted_g)
        latest = sorted_g[-1]
        if peak_price <= 0:
            continue
        drop_rate = (peak_price - latest.price) / peak_price
        if drop_rate > 0.03:  # 3% 이상 하락만
            drops.append({
                "complex_name": key[0],
                "area": key[1],
                "drop_rate": drop_rate,
                "peak_price": peak_price,
                "current_price": latest.price,
                "region": latest.district,
            })

    drops.sort(key=lambda x: x["drop_rate"], reverse=True)

    items = []
    for i, d in enumerate(drops[:top_n]):
        items.append(RankingItem(
            rank=i + 1,
            complex_name=f"{d['complex_name']} ({d['area']}㎡)",
            region=d["region"],
            value=d["drop_rate"] * 100,
            value_label=f"-{d['drop_rate']*100:.1f}%",
            sub_info=f"고점 {d['peak_price']/10000:.1f}억 → 현재 {d['current_price']/10000:.1f}억",
        ))

    block = ContentBlock(
        content_type="ranking",
        title=f"가장 많이 떨어진 아파트 TOP{min(top_n, len(items))}",
        subtitle="고점 대비 하락률 기준",
        items=items,
    )
    if items:
        block.story = _generate_story(block)
    return block


def generate_rise_ranking(trades: list, top_n: int = 10) -> ContentBlock:
    """
    가장 많이 오른 아파트 TOP N
    직전 거래 대비 상승률 기준
    """
    complex_data = _group_by_complex(trades)
    rises = []

    for key, group in complex_data.items():
        if len(group) < 2:
            continue
        sorted_g = sorted(group, key=lambda x: x.trade_date)
        first = sorted_g[0]
        latest = sorted_g[-1]
        if first.price <= 0:
            continue
        rise_rate = (latest.price - first.price) / first.price
        if rise_rate > 0.02:
            rises.append({
                "complex_name": key[0],
                "area": key[1],
                "rise_rate": rise_rate,
                "first_price": first.price,
                "current_price": latest.price,
                "region": latest.district,
            })

    rises.sort(key=lambda x: x["rise_rate"], reverse=True)

    items = []
    for i, r in enumerate(rises[:top_n]):
        items.append(RankingItem(
            rank=i + 1,
            complex_name=f"{r['complex_name']} ({r['area']}㎡)",
            region=r["region"],
            value=r["rise_rate"] * 100,
            value_label=f"+{r['rise_rate']*100:.1f}%",
            sub_info=f"{r['first_price']/10000:.1f}억 → {r['current_price']/10000:.1f}억",
        ))

    block = ContentBlock(
        content_type="ranking",
        title=f"가장 많이 오른 아파트 TOP{min(top_n, len(items))}",
        subtitle="기간 내 상승률 기준",
        items=items,
    )
    if items:
        block.story = _generate_story(block)
    return block


def generate_urgent_sale_ranking(trades: list, top_n: int = 10) -> ContentBlock:
    """
    이번 주 급매 TOP N
    최근 평균 대비 하락률 기준
    """
    complex_data = _group_by_complex(trades)
    urgents = []

    for key, group in complex_data.items():
        if len(group) < 2:
            continue
        sorted_g = sorted(group, key=lambda x: x.trade_date)
        recent_prices = [t.price for t in sorted_g[-5:]]
        avg_price = sum(recent_prices) // len(recent_prices)
        latest = sorted_g[-1]
        if avg_price <= 0:
            continue
        drop = (avg_price - latest.price) / avg_price
        if drop > 0.03:
            urgents.append({
                "complex_name": key[0],
                "area": key[1],
                "drop_rate": drop,
                "avg_price": avg_price,
                "current_price": latest.price,
                "region": latest.district,
                "floor": latest.floor,
            })

    urgents.sort(key=lambda x: x["drop_rate"], reverse=True)

    items = []
    for i, u in enumerate(urgents[:top_n]):
        items.append(RankingItem(
            rank=i + 1,
            complex_name=f"{u['complex_name']} ({u['area']}㎡)",
            region=u["region"],
            value=u["drop_rate"] * 100,
            value_label=f"-{u['drop_rate']*100:.1f}%",
            sub_info=f"평균 {u['avg_price']/10000:.1f}억 → 매물 {u['current_price']/10000:.1f}억 ({u['floor']}층)",
        ))

    block = ContentBlock(
        content_type="ranking",
        title=f"이번 주 급매 TOP{min(top_n, len(items))}",
        subtitle="최근 평균 대비 할인율 기준",
        items=items,
        cta="전체 급매 리스트는 살까말까 프리미엄에서 확인하세요",
    )
    if items:
        block.story = _generate_story(block)
    return block


def generate_supply_risk_ranking(supply_items: list, top_n: int = 10) -> ContentBlock:
    """
    공급 폭탄 지역 TOP N
    """
    items = []
    sorted_supply = sorted(supply_items, key=lambda x: x.households, reverse=True)

    for i, s in enumerate(sorted_supply[:top_n]):
        items.append(RankingItem(
            rank=i + 1,
            complex_name=s.name,
            region=s.region,
            value=s.households,
            value_label=f"{s.households:,}세대",
            sub_info=f"{s.expected_date} {s.supply_type} | {s.status}",
        ))

    block = ContentBlock(
        content_type="supply_risk",
        title=f"공급 예정 TOP{min(top_n, len(items))}",
        subtitle="향후 3년 내 대규모 공급 단지",
        items=items,
    )
    if items:
        block.story = _generate_story(block)
    return block


def generate_jeonse_rate_ranking(trades: list, top_n: int = 10) -> ContentBlock:
    """
    전세가율 높은 단지 TOP N (위험 신호)
    Note: 전세 데이터가 별도로 필요. 여기선 구조만 제공.
    """
    items = []
    # 실제 전세 데이터가 연동되면 여기에 로직 추가
    return ContentBlock(
        content_type="ranking",
        title=f"전세가율 위험 단지 TOP{top_n}",
        subtitle="전세가율 70% 이상 단지",
        items=items,
    )


# ── 비교 콘텐츠 ───────────────────────────────────────────────

def generate_comparison(
    trades_a: list, region_a: str,
    trades_b: list, region_b: str,
) -> ContentBlock:
    """
    지역 vs 지역 비교 콘텐츠
    """
    stats_a = _region_stats(trades_a)
    stats_b = _region_stats(trades_b)

    items = [
        RankingItem(1, region_a, value_label=f"평균 {stats_a['avg_84']/10000:.1f}억",
                    sub_info=f"거래 {stats_a['count']}건"),
        RankingItem(2, region_b, value_label=f"평균 {stats_b['avg_84']/10000:.1f}억",
                    sub_info=f"거래 {stats_b['count']}건"),
    ]

    block = ContentBlock(
        content_type="comparison",
        title=f"{region_a} vs {region_b}",
        subtitle="84㎡ 기준 실거래 비교",
        items=items,
    )
    block.story = _generate_comparison_story(region_a, stats_a, region_b, stats_b)
    return block


# ── AI 스토리 생성 ─────────────────────────────────────────────

STORY_SYSTEM = """
당신은 부동산 데이터 저널리스트입니다.
데이터를 사람들이 공유하고 싶어하는 짧은 스토리로 바꿉니다.

원칙:
- 놀라움, 비교, 돈 이야기로 시작
- 첫 문장에 가장 충격적인 수치 배치
- SNS에서 공유되는 톤 (짧고 임팩트 있게)
- 3~4문장 이내
- 감탄사나 이모지 사용 금지
""".strip()


def _generate_story(block: ContentBlock) -> str:
    """랭킹 데이터로 바이럴 스토리 생성"""
    if not block.items:
        return ""

    data_text = f"제목: {block.title}\n"
    for item in block.items[:5]:
        data_text += f"{item.rank}위: {item.complex_name} {item.value_label} ({item.sub_info})\n"

    try:
        resp = client.chat.completions.create(
            model=config.GPT_MODEL_MAIN,
            messages=[
                {"role": "system", "content": STORY_SYSTEM},
                {"role": "user", "content": f"다음 데이터를 공유하고 싶은 한 문단 스토리로 만들어줘.\n\n{data_text}"},
            ],
            max_tokens=300,
            temperature=0.8,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[콘텐츠] 스토리 생성 실패: {e}")
        return ""


def _generate_comparison_story(region_a, stats_a, region_b, stats_b) -> str:
    """비교 스토리 생성"""
    data_text = (
        f"{region_a}: 84㎡ 평균 {stats_a['avg_84']/10000:.1f}억, "
        f"거래 {stats_a['count']}건, 최고가 {stats_a['max']/10000:.1f}억\n"
        f"{region_b}: 84㎡ 평균 {stats_b['avg_84']/10000:.1f}억, "
        f"거래 {stats_b['count']}건, 최고가 {stats_b['max']/10000:.1f}억"
    )
    try:
        resp = client.chat.completions.create(
            model=config.GPT_MODEL_MAIN,
            messages=[
                {"role": "system", "content": STORY_SYSTEM},
                {"role": "user", "content": f"다음 두 지역을 비교하는 스토리를 만들어줘.\n\n{data_text}"},
            ],
            max_tokens=300,
            temperature=0.8,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[콘텐츠] 비교 스토리 생성 실패: {e}")
        return ""


# ── 유틸리티 ───────────────────────────────────────────────────

def _group_by_complex(trades) -> dict:
    """단지명 + 면적대별 그룹핑"""
    groups = defaultdict(list)
    for t in trades:
        area_key = _area_bracket(t.area)
        groups[(t.complex_name, area_key)].append(t)
    return groups


def _area_bracket(area: float) -> str:
    if 80 <= area <= 90:
        return "84"
    elif 55 <= area <= 65:
        return "59"
    elif 40 <= area <= 50:
        return "44"
    else:
        return str(int(area))


def _region_stats(trades) -> dict:
    apt84 = [t for t in trades if 80 <= t.area <= 90]
    all_prices = [t.price for t in trades if t.price > 0]
    avg_84 = sum(t.price for t in apt84) // len(apt84) if apt84 else 0
    return {
        "count": len(trades),
        "avg_84": avg_84,
        "max": max(all_prices) if all_prices else 0,
        "min": min(all_prices) if all_prices else 0,
    }
