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
"""
