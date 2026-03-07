"""
main.py
전체 파이프라인 오케스트레이터 (v2)
실행: python main.py [--region 마포구] [--step collect|analyze|send] [--test]

파이프라인 흐름:
  STEP 1: 데이터 수집 (국토부 + 도로명주소 API)
  STEP 2: 공통 AI 분석 (시장 요약, 임장 서술, 타이밍, 총평)
  STEP 3: 유료 전용 분석 (급매 감지, 전세 위험, 단지 비교, Q&A)
  STEP 4: 리포트 생성 (무료 HTML + 유료 HTML)
  STEP 5: 플랜별 분리 발송
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import config
from collector.molit  import fetch_trades, get_weekly_summary, get_notable_trades
from collector.kakao  import get_location_factors
from analyzer.gpt     import (
    analyze_complex, analyze_timing,
    generate_editor_summary, generate_market_summary,
    generate_region_comparison,
)
from reporter.builder import build_newsletter, save_html
from premium.detector import detect_urgent_sales, detect_jeonse_risk, compare_complexes
from premium.analyzer import (
    analyze_urgent_sale, analyze_jeonse_risk,
    analyze_comparison, answer_subscriber_question
)
from premium.builder  import build_premium_newsletter
from collector.naver_land import enrich_complex, complex_info_to_text
from collector.supply     import get_supply_forecast, supply_to_newsletter_text
from content.generator    import (
    generate_drop_ranking, generate_rise_ranking,
    generate_urgent_sale_ranking, generate_supply_risk_ranking,
)
from content.builder      import (
    build_content_sections_html, build_complex_info_html, build_supply_section_html,
)
from sender.resend    import send_by_plan
from utils.db         import (
    get_active_subscribers, get_latest_issue_num, log_newsletter
)


# ── 예산대 × 권역 비교 설정 ────────────────────────────────────
# 3구간 시리즈: 매주 순환 발행
BUDGET_TIERS = [
    {"label": "3~4억", "min": 30000, "max": 40000},
    {"label": "5~6억", "min": 50000, "max": 60000},
    {"label": "7억 이상", "min": 70000, "max": 999999},
]

# 비교 대상 권역 (2~3개씩)
COMPARISON_REGIONS = {
    "경기 남부": [
        {"region": "안양시 동안구", "gangnam_access": "지하철 40분", "school_score": "상위권"},
        {"region": "군포시", "gangnam_access": "지하철 50분", "school_score": "중상위"},
        {"region": "의왕시", "gangnam_access": "지하철 45분", "school_score": "중상위"},
    ],
    "서울 서부": [
        {"region": "마포구", "gangnam_access": "지하철 25분", "school_score": "상위권"},
        {"region": "은평구", "gangnam_access": "지하철 40분", "school_score": "중상위"},
        {"region": "서대문구", "gangnam_access": "지하철 30분", "school_score": "상위권"},
    ],
}

# ── 수동으로 넣는 뉴스 아이템 (매주 편집자가 업데이트) ────────
# TODO: 나중에 뉴스 크롤링으로 자동화 가능
THIS_WEEK_NEWS = {
    "category": "정책 변화",
    "title":    "DSR 3단계 적용 범위 확대 — 내집마련에 미치는 영향",
    "body":     (
        "금융당국이 DSR(총부채원리금상환비율) 3단계 적용을 기존보다 넓히는 방안을 검토 중이에요. "
        "현재 1억 초과 대출에 적용되던 기준이 <strong>6천만원 초과로 낮아질 수 있습니다.</strong><br><br>"
        "쉽게 말하면, 같은 소득으로 빌릴 수 있는 돈이 줄어들 수 있어요. "
        "아직 확정은 아니지만, 하반기 중 시행 가능성이 있어요."
    ),
    "impact": (
        "대출 한도 계획을 지금 기준보다 10~15% 보수적으로 잡아두세요. "
        "확정되기 전에 사전 대출 승인을 받아두면 유리합니다."
    ),
}

# 타이밍 인디케이터 (매주 편집자가 업데이트)
THIS_WEEK_INDICATORS = [
    {"name": "거래량 추이",    "status": "3주 연속 증가 중",          "badge": "긍정"},
    {"name": "전세가율",       "status": "62%, 전월 대비 2%p 상승",   "badge": "긍정"},
    {"name": "금리 방향",      "status": "3월 동결 유력, 하반기 인하 기대", "badge": "중립"},
    {"name": "미분양 현황",    "status": "22가구, 전월 대비 감소",     "badge": "긍정"},
    {"name": "급매물 소화",    "status": "저층·소형 급매 대부분 소진", "badge": "주의"},
]

# 유료 구독자 Q&A (매주 편집자가 업데이트)
THIS_WEEK_QNA = [
    {"question": "마래푸 84㎡ 지금 9억 초반이면 살만한가요?", "answer": ""},
    {"question": "전세 만기 6개월 남았는데 매수하는 게 나을까요?", "answer": ""},
]

# 단지 비교 대상 (매월 업데이트)
MONTHLY_COMPARE_COMPLEXES = [
    "마포래미안푸르지오", "공덕자이", "신공덕삼성래미안",
]

# 전세가 데이터 (매주 편집자가 업데이트, 향후 API 자동화 예정)
THIS_WEEK_JEONSE = [
    # {"complex_name": "단지명", "jeonse_rate": 0.75, "매매가": 90000, "전세가": 67500},
]


def run_pipeline(region: str, test_mode: bool = False, step: str = "all"):
    """
    전체 파이프라인 실행 (v2 — 5단계)

    Args:
        region:    분석 지역 (예: "마포구")
        test_mode: True면 실제 발송 대신 콘솔 출력
        step:      "collect" | "analyze" | "send" | "all"
    """
    print(f"\n{'='*50}")
    print(f"살까말까 파이프라인 v2 시작 — {region}")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # ── STEP 1: 데이터 수집 ──────────────────────────────────
    if step in ("collect", "all"):
        print("[STEP 1] 실거래 데이터 수집 중...")
        trades = fetch_trades(region=region, months=2)

        if not trades:
            print("[오류] 거래 데이터 없음. 파이프라인 중단.")
            return

        summary  = get_weekly_summary(trades)
        notable  = get_notable_trades(trades, top_n=config.MAX_COMPLEXES)

        print(f"  → 총 {len(trades)}건 수집, 주목 단지 {len(notable)}개 선정")

        # 중간 저장 (analyze 단계에서 재사용)
        _save_checkpoint("trades_summary", summary)
        _save_checkpoint("trades_all", [
            {"complex_name": t.complex_name, "price": t.price,
             "area": t.area, "floor": t.floor, "trade_date": t.trade_date,
             "build_year": t.build_year, "road_name": t.road_name,
             "district": t.district}
            for t in trades
        ])
        _save_checkpoint("notable_trades", [
            {"complex_name": t.complex_name, "price": t.price,
             "area": t.area, "floor": t.floor, "trade_date": t.trade_date,
             "road_name": t.road_name}
            for t in notable
        ])

        if step == "collect":
            print("[수집 완료] 다음: python main.py --step analyze")
            return
    else:
        # 저장된 체크포인트 로드
        summary = _load_checkpoint("trades_summary") or {}
        notable_dicts = _load_checkpoint("notable_trades") or []
        trades_dicts = _load_checkpoint("trades_all") or []
        from collector.molit import TradeRecord
        notable = [TradeRecord(**d) for d in notable_dicts]
        trades = [TradeRecord(**d) for d in trades_dicts]

    # ── 예산대 결정 (주차에 따라 순환) ──────────────────────────
    import math
    week_num = datetime.now().isocalendar()[1]
    budget_tier = BUDGET_TIERS[week_num % len(BUDGET_TIERS)]
    budget_label = budget_tier["label"]
    print(f"  → 이번 주 예산대: {budget_label}")

    # 비교 대상 권역 결정
    comparison_group = None
    for group_name, regions in COMPARISON_REGIONS.items():
        if any(r["region"] == region for r in regions):
            comparison_group = regions
            break
    if not comparison_group:
        comparison_group = [{"region": region, "gangnam_access": "", "school_score": ""}]

    # ── STEP 1.5: 네이버 + 공급 데이터 수집 ───────────────────
    naver_infos = {}
    supply_forecast = None

    if step in ("collect", "analyze", "all"):
        print("\n[STEP 1.5] 네이버 부동산 + 공급 데이터 수집 중...")

        # 네이버 단지 상세 (주목 단지)
        for trade in notable:
            print(f"  → [네이버] {trade.complex_name} 상세 조회...")
            naver_info = enrich_complex(trade.complex_name, region)
            naver_infos[trade.complex_name] = naver_info

        # 공급 전망
        print(f"  → [공급] {region} 공급 전망 수집...")
        supply_forecast = get_supply_forecast(region)
        print(f"  → 공급 전망: {supply_forecast.total_supply_3y:,}세대 (리스크: {supply_forecast.risk_level})")

    # ── STEP 2: 공통 AI 분석 ────────────────────────────────
    if step in ("analyze", "all"):
        print("\n[STEP 2] 공통 AI 분석 중...")

        # 공급 데이터를 summary에 반영
        if supply_forecast:
            summary["supply_forecast"] = supply_to_newsletter_text(supply_forecast)

        # 2-1. 시장 온도계 요약
        market_text = generate_market_summary(
            summary=summary,
            region=region,
            jeonse_rate=62.0,  # TODO: 실제 API 연동
        )
        print(f"  → 시장 요약 생성 완료")

        # 2-2. 단지별 임장 서술
        complex_results = []
        tags = ["이번 주 포커스", "주목 단지"]

        for i, trade in enumerate(notable):
            print(f"  → [{i+1}/{len(notable)}] {trade.complex_name} 임장 요소 수집 중...")

            # 도로명주소 API + Haversine으로 임장 요소 수집
            city = "경기도" if "시" in region else "서울특별시"
            factors = get_location_factors(
                complex_name=trade.complex_name,
                address=f"{city} {region} {trade.road_name}"
            )

            # 네이버 데이터로 공급 리스크 텍스트 생성
            supply_text = supply_to_newsletter_text(supply_forecast) if supply_forecast else ""

            # GPT 임장 서술 생성 (네이버 + 공급 데이터 반영)
            if factors:
                description = analyze_complex(
                    trade=trade,
                    factors=factors,
                    special_notes="없음",
                    supply_risk=supply_text,
                )
            else:
                description = ""

            # 네이버 단지 정보 추가
            naver_info = naver_infos.get(trade.complex_name)
            naver_text = complex_info_to_text(naver_info) if naver_info else ""

            complex_results.append({
                "trade":       trade,
                "description": description,
                "tag":         tags[i] if i < len(tags) else "단지 분석",
                "naver_info":  naver_info,
                "naver_text":  naver_text,
            })

        # 2-2.5. 지역 비교 데이터 수집 + GPT 분석
        comparison_regions = []
        for cr in comparison_group:
            r_data = dict(cr)
            # 해당 지역 거래 데이터에서 84㎡ 평균가, 거래량 추출
            if cr["region"] == region:
                r_data["avg_84"] = summary.get("avg_price_84", 0)
                r_data["trade_count"] = summary.get("total_count", 0)
                r_data["jeonse_rate"] = 62.0  # TODO: 실제 전세가율 API 연동
            else:
                # 비교 지역의 데이터는 별도 수집 필요 (현재는 수동 데이터)
                r_data.setdefault("avg_84", 0)
                r_data.setdefault("trade_count", 0)
                r_data.setdefault("jeonse_rate", 0)
            comparison_regions.append(r_data)

        comparison_analysis = None
        valid_regions = [r for r in comparison_regions if r.get("avg_84", 0) > 0]
        if len(valid_regions) >= 2:
            print(f"  → 지역 비교 분석 중: {', '.join(r['region'] for r in valid_regions)}")
            comparison_analysis = generate_region_comparison(
                budget_label=budget_label,
                regions_data=valid_regions,
            )
            print(f"  → 추천 지역: {comparison_analysis.get('recommended', '미정')}")
        else:
            comparison_regions = []

        # 2-3. 타이밍 신호
        timing = analyze_timing(
            summary=summary,
            region=region,
            jeonse_rate=62.0,
        )
        print(f"  → 타이밍 신호: {timing.get('signal', '')}")

        # 2-4. 편집장 총평
        notable_names = ", ".join(c["trade"].complex_name for c in complex_results)
        editor_summary = generate_editor_summary(
            region=region,
            market_mood=market_text[:50] + "...",
            timing_signal=timing.get("signal", ""),
            notable_complex=notable_names,
        )

        if step == "analyze":
            print("\n[분석 완료] 결과:")
            print(f"  시장 요약: {market_text[:80]}...")
            print(f"  타이밍:   {timing.get('signal')}")
            print(f"  총평:     {editor_summary[:80]}...")
            return
    else:
        # 분석 단계 스킵 시 더미 데이터
        market_text    = ""
        complex_results = []
        timing         = {"signal": "조심스런 매수 고려", "reason": "", "hint": ""}
        editor_summary = ""
        comparison_regions = []
        comparison_analysis = None

    # ── STEP 3: 유료 전용 분석 ──────────────────────────────
    print("\n[STEP 3] 유료 전용 분석 중...")

    # 3-1. 급매 감지
    urgent_sales = detect_urgent_sales(trades)
    for sale in urgent_sales:
        sale["analysis"] = analyze_urgent_sale(sale)
    print(f"  → 급매 감지: {len(urgent_sales)}건")

    # 3-2. 전세가율 위험 경보
    jeonse_risks = detect_jeonse_risk(THIS_WEEK_JEONSE)
    for risk in jeonse_risks:
        risk["analysis"] = analyze_jeonse_risk(risk)
    print(f"  → 전세 위험: {len(jeonse_risks)}건")

    # 3-3. 단지 비교 (매월 첫째 주만)
    comparison = None
    if datetime.today().day <= 7:
        histories = compare_complexes(trades, MONTHLY_COMPARE_COMPLEXES)
        if histories:
            comparison = {
                "histories": histories,
                "analysis":  analyze_comparison(histories),
            }
            print(f"  → 단지 비교: {len(histories)}개 단지")
    else:
        print(f"  → 단지 비교: 이번 주 생략 (매월 첫째 주만)")

    # 3-4. 구독자 Q&A
    qna_items = []
    for item in THIS_WEEK_QNA:
        if item["question"]:
            answer = answer_subscriber_question(item["question"])
            qna_items.append({"question": item["question"], "answer": answer})
    print(f"  → Q&A: {len(qna_items)}건 답변 생성")

    # ── STEP 3.5: 바이럴 콘텐츠 생성 ──────────────────────────
    print("\n[STEP 3.5] 바이럴 콘텐츠 생성 중...")
    content_blocks = []

    # 급매 TOP
    urgent_ranking = generate_urgent_sale_ranking(trades, top_n=5)
    if urgent_ranking.items:
        content_blocks.append(urgent_ranking)
        print(f"  → 급매 랭킹: {len(urgent_ranking.items)}건")

    # 하락 TOP
    drop_ranking = generate_drop_ranking(trades, top_n=5)
    if drop_ranking.items:
        content_blocks.append(drop_ranking)
        print(f"  → 하락 랭킹: {len(drop_ranking.items)}건")

    # 상승 TOP
    rise_ranking = generate_rise_ranking(trades, top_n=5)
    if rise_ranking.items:
        content_blocks.append(rise_ranking)
        print(f"  → 상승 랭킹: {len(rise_ranking.items)}건")

    # 공급 리스크 TOP
    if supply_forecast and supply_forecast.items:
        supply_ranking = generate_supply_risk_ranking(supply_forecast.items, top_n=5)
        if supply_ranking.items:
            content_blocks.append(supply_ranking)
            print(f"  → 공급 랭킹: {len(supply_ranking.items)}건")

    # 콘텐츠 섹션 HTML 생성
    content_html = build_content_sections_html(
        content_blocks=content_blocks,
        supply_forecast=supply_forecast,
        complex_infos=naver_infos,
    )

    # 단지 카드에 네이버 정보 HTML 추가
    for c in complex_results:
        naver_info = c.get("naver_info")
        if naver_info:
            c["naver_html"] = build_complex_info_html(naver_info)

    # ── STEP 4: 리포트 생성 ─────────────────────────────────
    print("\n[STEP 4] HTML 리포트 생성 중...")
    issue_num = get_latest_issue_num() + 1

    # 4-1. 무료 HTML
    common_kwargs = dict(
        region              = region,
        issue_num           = issue_num,
        summary             = summary,
        market_summary_text = market_text,
        complexes           = complex_results,
        timing              = timing,
        indicators          = THIS_WEEK_INDICATORS,
        news_item           = THIS_WEEK_NEWS,
        editor_summary      = editor_summary,
        budget_label        = budget_label,
        comparison_regions  = comparison_regions if comparison_regions else None,
        comparison_analysis = comparison_analysis,
        urgent_sales_preview= urgent_sales if urgent_sales else None,
    )
    free_html = build_newsletter(**common_kwargs)

    # 콘텐츠 섹션을 무료 HTML에 삽입 (편집장 총평 직전)
    if content_html:
        insert_point = free_html.find("</div><!-- end body -->")
        if insert_point != -1:
            free_html = free_html[:insert_point] + content_html + free_html[insert_point:]

    # 4-2. 유료 HTML (무료 기반 + 프리미엄 섹션)
    premium_html = build_premium_newsletter(
        free_html=free_html,
        urgent_sales=urgent_sales,
        jeonse_risks=jeonse_risks,
        comparison=comparison,
        qna_items=qna_items,
    )

    # HTML 파일 저장 (발송 전 육안 확인용)
    free_path    = f"data/free_vol{issue_num:03d}.html"
    premium_path = f"data/premium_vol{issue_num:03d}.html"
    save_html(free_html, free_path)
    save_html(premium_html, premium_path)
    print(f"  → 무료 리포트: {free_path}")
    print(f"  → 유료 리포트: {premium_path}")

    # ── STEP 5: 플랜별 분리 발송 ────────────────────────────
    if step in ("send", "all"):
        if budget_label and comparison_regions:
            subject_free = f"[살까말까 Vol.{issue_num:03d}] {budget_label}으로 어디가 나을까?"
        else:
            subject_free = f"[살까말까 Vol.{issue_num:03d}] 이번 주 {region} 실거래 브리핑"
        subject_premium = f"[살까말까 Premium Vol.{issue_num:03d}] {region} 급매 {len(urgent_sales)}건 + 맞춤 분석"

        if test_mode:
            print(f"\n[테스트 모드] 실제 발송 생략.")
            print(f"  무료 HTML: {free_path}")
            print(f"  유료 HTML: {premium_path}")
            return

        print(f"\n[STEP 5] 플랜별 이메일 발송 중...")
        subscribers = get_active_subscribers()

        if not subscribers:
            print("[경고] 구독자가 없습니다.")
            return

        results = send_by_plan(
            free_html=free_html,
            premium_html=premium_html,
            subject_free=subject_free,
            subject_premium=subject_premium,
            subscribers=subscribers,
        )

        # 발송 이력 저장
        log_newsletter(
            issue_num=issue_num,
            region=region,
            recipient_count=results["total_success"] + results["total_failed"],
            success_count=results["total_success"],
        )

        print(f"\n✅ 파이프라인 v2 완료!")
        print(f"   발행 번호: Vol.{issue_num:03d}")
        print(f"   발송 성공: {results['total_success']}건")
        print(f"   발송 실패: {results['total_failed']}건")


# ── 체크포인트 저장/로드 ──────────────────────────────────────

def _save_checkpoint(name: str, data):
    Path("data").mkdir(exist_ok=True)
    with open(f"data/{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def _load_checkpoint(name: str):
    try:
        with open(f"data/{name}.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="살까말까 파이프라인 v2")
    parser.add_argument("--region", default=config.TARGET_REGION, help="분석 지역")
    parser.add_argument("--step",   default="all",
                        choices=["collect", "analyze", "send", "all"],
                        help="실행 단계")
    parser.add_argument("--test",   action="store_true", help="테스트 모드 (발송 생략)")
    args = parser.parse_args()

    run_pipeline(
        region    = args.region,
        test_mode = args.test,
        step      = args.step,
    )
