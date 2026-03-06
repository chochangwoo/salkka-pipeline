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
    generate_editor_summary, generate_market_summary
)
from reporter.builder import build_newsletter, save_html
from premium.detector import detect_urgent_sales, detect_jeonse_risk, compare_complexes
from premium.analyzer import (
    analyze_urgent_sale, analyze_jeonse_risk,
    analyze_comparison, answer_subscriber_question
)
from premium.builder  import build_premium_newsletter
from sender.resend    import send_by_plan
from utils.db         import (
    get_active_subscribers, get_latest_issue_num, log_newsletter
)


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

    # ── STEP 2: 공통 AI 분석 ────────────────────────────────
    if step in ("analyze", "all"):
        print("\n[STEP 2] 공통 AI 분석 중...")

        # 2-1. 시장 온도계 요약
        market_text = generate_market_summary(
            summary=summary,
            region=region,
            jeonse_rate=62.0,  # TODO: 실제 API 연동
        )
        print(f"  → 시장 요약 생성 완료")

        # 2-2. 단지별 임장 서술
        complex_results = []
        tags = ["📌 이번 주 포커스", "💡 주목 단지"]

        for i, trade in enumerate(notable):
            print(f"  → [{i+1}/{len(notable)}] {trade.complex_name} 임장 요소 수집 중...")

            # 도로명주소 API + Haversine으로 임장 요소 수집
            city = "경기도" if "시" in region else "서울특별시"
            factors = get_location_factors(
                complex_name=trade.complex_name,
                address=f"{city} {region} {trade.road_name}"
            )

            # GPT 임장 서술 생성
            if factors:
                description = analyze_complex(
                    trade=trade,
                    factors=factors,
                    special_notes="없음"
                )
            else:
                description = f"{trade.complex_name}에 대한 위치 정보를 수집하지 못했습니다."

            complex_results.append({
                "trade":       trade,
                "description": description,
                "tag":         tags[i] if i < len(tags) else "📍 단지 분석",
            })

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
        market_text    = "이번 주 시장 분석 데이터를 불러오는 중입니다."
        complex_results = []
        timing         = {"signal": "조심스런 매수 고려", "reason": "", "hint": ""}
        editor_summary = "이번 주 브리핑을 준비 중입니다."

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

    # ── STEP 4: 리포트 생성 ─────────────────────────────────
    print("\n[STEP 4] HTML 리포트 생성 중...")
    issue_num = get_latest_issue_num() + 1

    # 4-1. 무료 HTML
    common_kwargs = dict(
        region             = region,
        issue_num          = issue_num,
        summary            = summary,
        market_summary_text= market_text,
        complexes          = complex_results,
        timing             = timing,
        indicators         = THIS_WEEK_INDICATORS,
        news_item          = THIS_WEEK_NEWS,
        editor_summary     = editor_summary,
    )
    free_html = build_newsletter(**common_kwargs)

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
        subject_free    = f"[살까말까 Vol.{issue_num:03d}] 이번 주 {region} 실거래 브리핑"
        subject_premium = f"[살까말까 Premium Vol.{issue_num:03d}] 이번 주 {region} 실거래 브리핑"

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
