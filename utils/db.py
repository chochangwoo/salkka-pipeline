"""
utils/db.py
Supabase 연동 — 구독자 관리 + 발송 이력
"""

import requests
from datetime import datetime
import config


HEADERS = {
    "apikey":        config.SUPABASE_KEY,
    "Authorization": f"Bearer {config.SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=representation",
}


def _url(table: str) -> str:
    return f"{config.SUPABASE_URL}/rest/v1/{table}"


# ── 구독자 관리 ───────────────────────────────────────────────

def get_active_subscribers() -> list[dict]:
    """
    활성 구독자 이메일 목록 조회
    
    Returns:
        [{"id": str, "email": str, "plan": str, "region": str}]
    """
    resp = requests.get(
        _url("subscribers"),
        headers=HEADERS,
        params={
            "select": "id,email,plan,region",
            "status": "eq.active",          # 활성 구독자만
        },
        timeout=10
    )
    if resp.status_code == 200:
        return resp.json()
    print(f"[DB] 구독자 조회 실패: {resp.status_code}")
    return []


def add_subscriber(email: str, plan: str = "free", region: str = config.TARGET_REGION) -> bool:
    """구독자 추가"""
    resp = requests.post(
        _url("subscribers"),
        headers=HEADERS,
        json={
            "email":      email,
            "plan":       plan,
            "region":     region,
            "status":     "active",
            "created_at": datetime.utcnow().isoformat(),
        },
        timeout=10
    )
    return resp.status_code in (200, 201)


def unsubscribe(email: str) -> bool:
    """구독 해지"""
    resp = requests.patch(
        _url("subscribers"),
        headers=HEADERS,
        params={"email": f"eq.{email}"},
        json={"status": "unsubscribed", "updated_at": datetime.utcnow().isoformat()},
        timeout=10
    )
    return resp.status_code == 200


# ── 발송 이력 ─────────────────────────────────────────────────

def log_newsletter(
    issue_num: int,
    region: str,
    recipient_count: int,
    success_count: int,
) -> bool:
    """발송 이력 저장"""
    resp = requests.post(
        _url("newsletter_logs"),
        headers=HEADERS,
        json={
            "issue_num":       issue_num,
            "region":          region,
            "recipient_count": recipient_count,
            "success_count":   success_count,
            "sent_at":         datetime.utcnow().isoformat(),
        },
        timeout=10
    )
    return resp.status_code in (200, 201)


# ── 투표 ───────────────────────────────────────────────────────

def submit_vote(email: str, region: str, budget: str, issue_num: int) -> bool:
    """투표 제출 (중복 투표 방지는 호출측에서 has_voted 확인)"""
    resp = requests.post(
        _url("votes"),
        headers=HEADERS,
        json={
            "email":     email,
            "region":    region,
            "budget":    budget,
            "issue_num": issue_num,
            "voted_at":  datetime.utcnow().isoformat(),
        },
        timeout=10,
    )
    return resp.status_code in (200, 201)


def has_voted(email: str, issue_num: int) -> bool:
    """해당 호에 이미 투표했는지 확인"""
    resp = requests.get(
        _url("votes"),
        headers=HEADERS,
        params={
            "select":    "id",
            "email":     f"eq.{email}",
            "issue_num": f"eq.{issue_num}",
            "limit":     "1",
        },
        timeout=10,
    )
    if resp.status_code == 200:
        return len(resp.json()) > 0
    return False


def get_vote_results(issue_num: int) -> list[dict]:
    """
    해당 호의 투표 결과 집계 (region+budget 조합별 카운트).
    Supabase REST API는 GROUP BY를 지원하지 않으므로
    전체 투표를 가져와 Python에서 집계.

    Returns:
        [{"region": str, "budget": str, "count": int}]  (count 내림차순)
    """
    resp = requests.get(
        _url("votes"),
        headers=HEADERS,
        params={
            "select":    "region,budget",
            "issue_num": f"eq.{issue_num}",
        },
        timeout=10,
    )
    if resp.status_code != 200:
        return []

    votes = resp.json()
    counts: dict[tuple, int] = {}
    for v in votes:
        key = (v["region"], v["budget"])
        counts[key] = counts.get(key, 0) + 1

    results = [
        {"region": k[0], "budget": k[1], "count": c}
        for k, c in counts.items()
    ]
    results.sort(key=lambda x: x["count"], reverse=True)
    return results


# ── 관심 단지 (watchlist) ─────────────────────────────────────

def add_to_watchlist(email: str, complex_name: str, region: str = "") -> bool:
    """관심 단지 등록"""
    resp = requests.post(
        _url("watchlist"),
        headers=HEADERS,
        json={
            "email":        email,
            "complex_name": complex_name,
            "region":       region,
            "created_at":   datetime.utcnow().isoformat(),
        },
        timeout=10,
    )
    return resp.status_code in (200, 201)


def get_watchlist(email: str) -> list[dict]:
    """사용자의 관심 단지 목록 조회"""
    resp = requests.get(
        _url("watchlist"),
        headers=HEADERS,
        params={
            "select": "complex_name,region,created_at",
            "email":  f"eq.{email}",
            "order":  "created_at.desc",
        },
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()
    return []


def remove_from_watchlist(email: str, complex_name: str) -> bool:
    """관심 단지 삭제"""
    resp = requests.delete(
        _url("watchlist"),
        headers=HEADERS,
        params={
            "email":        f"eq.{email}",
            "complex_name": f"eq.{complex_name}",
        },
        timeout=10,
    )
    return resp.status_code in (200, 204)


# ── 발송 이력 (newsletter_logs) ───────────────────────────────

def get_latest_issue_num() -> int:
    """가장 최근 발행 번호 조회"""
    resp = requests.get(
        _url("newsletter_logs"),
        headers=HEADERS,
        params={
            "select":   "issue_num",
            "order":    "issue_num.desc",
            "limit":    "1",
        },
        timeout=10
    )
    if resp.status_code == 200:
        data = resp.json()
        if data:
            return data[0]["issue_num"]
    return 0


# ── Supabase 테이블 스키마 (참고용) ──────────────────────────
"""
-- 구독자 테이블
CREATE TABLE subscribers (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    plan        TEXT DEFAULT 'free',    -- free / standard / premium
    region      TEXT DEFAULT '마포구',
    status      TEXT DEFAULT 'active',  -- active / unsubscribed
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ
);

-- 발송 이력 테이블
CREATE TABLE newsletter_logs (
    id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    issue_num        INTEGER NOT NULL,
    region           TEXT,
    recipient_count  INTEGER,
    success_count    INTEGER,
    sent_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 투표 테이블 (v3.0)
CREATE TABLE votes (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email       TEXT,
    region      TEXT NOT NULL,
    budget      TEXT NOT NULL,
    voted_at    TIMESTAMPTZ DEFAULT NOW(),
    issue_num   INTEGER
);
CREATE INDEX idx_votes_issue ON votes(issue_num);

-- 관심 단지 테이블 (v3.0)
CREATE TABLE watchlist (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email         TEXT NOT NULL,
    complex_name  TEXT NOT NULL,
    region        TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
"""
