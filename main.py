"""
main.py
전체 파이프라인 오케스트레이터
실행: python main.py [--region 마포구] [--step collect|analyze|send] [--test]
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
from sender.resend    import send_newsletter, send_test
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


def run_pipeline(region: str, test_mode: bool = False, step: str = "all"):
    """
    전체 파이프라인 실행
    
    Args:
        region:    분석 지역 (예: "마포구")
        test_mode: True면 실제 발송 대신 콘솔 출력
        step:      "collect" | "analyze" | "send" | "all"
    """
    print(f"\n{'='*50}")
    print(f"살까말까 파이프라인 시작 — {region}")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # ── STEP 1: 데이터 수집 ──────────────────────────────────
    if step in ("collect", "all"):
        print("[1단계] 실거래 데이터 수집 중...")
        trades = fetch_trades(region=region, months=1)

        if not trades:
            print("[오류] 거래 데이터 없음. 파이프라인 중단.")
            return

        summary  = get_weekly_summary(trades)
        notable  = get_notable_trades(trades, top_n=config.MAX_COMPLEXES)

        print(f"  → 총 {len(trades)}건 수집, 주목 단지 {len(notable)}개 선정")

        # 중간 저장 (analyze 단계에서 재사용)
        _save_checkpoint("trades_summary", summary)
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
        from collector.molit import TradeRecord
        notable = [TradeRecord(**d) for d in notable_dicts]

    # ── STEP 2: AI 분석 ──────────────────────────────────────
    if step in ("analyze", "all"):
        print("\n[2단계] AI 분석 중...")

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

            # 카카오맵으로 임장 요소 수집
            factors = get_location_factors(
                complex_name=trade.complex_name,
                address=f"{config.TARGET_CITY} {region} {trade.road_name}"
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

    # ── STEP 3: 리포트 생성 ───────────────────────────────────
    print("\n[3단계] HTML 리포트 생성 중...")
    issue_num = get_latest_issue_num() + 1

    html = build_newsletter(
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

    # HTML 파일 저장 (발송 전 육안 확인용)
    output_path = f"data/newsletter_vol{issue_num:03d}.html"
    save_html(html, output_path)
    print(f"  → 리포트 저장: {output_path}")

    # ── STEP 4: 발송 ─────────────────────────────────────────
    if step in ("send", "all"):
        subject = f"[살까말까 Vol.{issue_num:03d}] 이번 주 {region} 실거래 브리핑"

        if test_mode:
            print(f"\n[테스트 모드] 실제 발송 생략. HTML 파일 확인: {output_path}")
            return

        print(f"\n[4단계] 이메일 발송 중...")
        subscribers = get_active_subscribers()
        emails = [s["email"] for s in subscribers]

        if not emails:
            print("[경고] 구독자가 없습니다.")
            return

        print(f"  → 발송 대상: {len(emails)}명")
        results = send_newsletter(html=html, subject=subject, recipients=emails)

        # 발송 이력 저장
        log_newsletter(
            issue_num=issue_num,
            region=region,
            recipient_count=len(emails),
            success_count=results["success"],
        )

        print(f"\n✅ 파이프라인 완료!")
        print(f"   발행 번호: Vol.{issue_num:03d}")
        print(f"   발송 성공: {results['success']}건")
        print(f"   발송 실패: {results['failed']}건")


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
    parser = argparse.ArgumentParser(description="살까말까 파이프라인")
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
