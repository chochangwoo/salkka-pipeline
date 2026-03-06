"""
sender/resend.py
Resend API로 뉴스레터 이메일 발송
무료 플랜: 월 3,000건
"""

import requests
import config


def send_newsletter(
    html: str,
    subject: str,
    recipients: list[str],
) -> dict:
    """
    구독자 전체 발송
    
    Args:
        html:       완성된 HTML 이메일
        subject:    이메일 제목
        recipients: 수신자 이메일 리스트
    Returns:
        {"success": int, "failed": int, "errors": list}
    """
    results = {"success": 0, "failed": 0, "errors": []}

    for email in recipients:
        result = send_single(html=html, subject=subject, to_email=email)
        if result.get("ok"):
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({"email": email, "error": result.get("error")})

    print(f"[발송 완료] 성공:{results['success']} / 실패:{results['failed']}")
    return results


def send_single(
    html: str,
    subject: str,
    to_email: str,
) -> dict:
    """
    단일 이메일 발송
    
    Returns:
        {"ok": bool, "id": str, "error": str}
    """
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {config.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "from":    config.FROM_EMAIL,
        "to":      [to_email],
        "subject": subject,
        "html":    html,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()

        if resp.status_code in (200, 201):
            print(f"[발송] ✓ {to_email}")
            return {"ok": True, "id": data.get("id", "")}
        else:
            error_msg = data.get("message", str(resp.status_code))
            print(f"[발송] ✗ {to_email}: {error_msg}")
            return {"ok": False, "error": error_msg}

    except requests.RequestException as e:
        print(f"[발송] ✗ {to_email}: 네트워크 오류 - {e}")
        return {"ok": False, "error": str(e)}


def send_test(html: str, subject: str, test_email: str) -> bool:
    """테스트 발송 (단일 이메일로 확인용)"""
    print(f"[테스트 발송] → {test_email}")
    result = send_single(html=html, subject=f"[테스트] {subject}", to_email=test_email)
    return result.get("ok", False)
