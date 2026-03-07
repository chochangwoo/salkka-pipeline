"""
collector/news.py
부동산 뉴스 자동 수집 + GPT 요약

소스:
  - 네이버 뉴스 RSS (부동산 섹션)
  - 구글 뉴스 RSS

출력:
  {"category": str, "title": str, "body": str, "impact": str, "source": str, "url": str}
"""

import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timedelta

import config
from openai import OpenAI


# ── RSS 피드 소스 ────────────────────────────────────────────────

NAVER_RSS = "https://news.google.com/rss/search?q=%EB%B6%80%EB%8F%99%EC%82%B0+%EC%95%84%ED%8C%8C%ED%8A%B8&hl=ko&gl=KR&ceid=KR:ko"

KEYWORDS = ["아파트", "부동산", "실거래", "전세", "금리", "DSR", "분양", "재건축", "규제"]

EXCLUDE = ["광고", "분양 홍보", "모집"]


def fetch_news_rss(max_items: int = 20) -> list[dict]:
    """Google News RSS에서 부동산 관련 뉴스 수집"""
    try:
        resp = requests.get(NAVER_RSS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[뉴스] RSS 수집 실패: {e}")
        return []

    items = []
    try:
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item")[:max_items]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            source = item.findtext("source", "")

            # 제외 키워드 필터
            if any(ex in title for ex in EXCLUDE):
                continue

            # 관련 키워드 확인
            if not any(kw in title for kw in KEYWORDS):
                continue

            items.append({
                "title": _clean_html(title),
                "url": link,
                "source": source,
                "pub_date": pub_date,
            })
    except ET.ParseError as e:
        print(f"[뉴스] RSS 파싱 실패: {e}")

    print(f"[뉴스] {len(items)}건 수집")
    return items


def select_top_news(items: list[dict], region: str = "") -> dict | None:
    """
    수집된 뉴스 중 가장 중요한 1건 선정.
    지역 관련 뉴스 우선, 없으면 정책/금리 뉴스.
    """
    if not items:
        return None

    # 지역 관련 뉴스 우선
    if region:
        for item in items:
            if region in item["title"]:
                return item

    # 정책/금리 키워드 우선
    policy_kw = ["DSR", "금리", "규제", "대출", "정책", "재건축", "분양"]
    for item in items:
        if any(kw in item["title"] for kw in policy_kw):
            return item

    return items[0] if items else None


def summarize_news(news_item: dict, region: str = "") -> dict:
    """
    GPT로 뉴스를 뉴스레터 형식으로 요약.

    Returns:
        {"category": str, "title": str, "body": str, "impact": str}
    """
    if not news_item:
        return {}

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    system = """당신은 부동산 뉴스레터 편집자입니다.
뉴스 제목을 바탕으로 내집마련 실수요자를 위한 간결한 요약을 작성합니다.

규칙:
- "데이터 부족", "확인되지 않았습니다" 같은 표현 금지
- 확실하지 않은 내용은 아예 쓰지 않을 것
- 산문 형태로 자연스럽게
- "화이팅" 류 마무리 금지"""

    user = f"""다음 부동산 뉴스를 내집마련 실수요자 관점에서 요약해줘.

뉴스 제목: {news_item['title']}
출처: {news_item.get('source', '')}
관련 지역: {region if region else '전국'}

출력 형식 (JSON):
{{"category": "정책 변화 / 시장 동향 / 금리·대출 / 공급 이슈 중 하나",
  "title": "뉴스레터용 재가공 제목 (40자 이내)",
  "body": "쉬운 말로 요약 (3~4문장, 150자 내외)",
  "impact": "실수요자 행동 힌트 (1~2문장)"}}"""

    try:
        response = client.chat.completions.create(
            model=config.GPT_MODEL_MAIN,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=500,
            temperature=0.5,
        )
        raw = response.choices[0].message.content.strip()

        # JSON 파싱
        import json
        # ```json ... ``` 패턴 제거
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)
        result = json.loads(raw)
        print(f"[뉴스] GPT 요약 완료: {result.get('title', '')[:30]}...")
        return result

    except Exception as e:
        print(f"[뉴스] GPT 요약 실패: {e}")
        return {
            "category": "시장 동향",
            "title": news_item["title"][:40],
            "body": "",
            "impact": "",
        }


def get_weekly_news(region: str = "") -> dict:
    """
    주간 뉴스 1건 자동 수집 + 요약.
    파이프라인에서 THIS_WEEK_NEWS 대신 사용.

    Returns:
        {"category": str, "title": str, "body": str, "impact": str}
        비어있으면 빈 dict 반환.
    """
    items = fetch_news_rss(max_items=20)
    top = select_top_news(items, region=region)
    if not top:
        print("[뉴스] 이번 주 관련 뉴스 없음")
        return {}

    result = summarize_news(top, region=region)
    if result.get("body"):
        result["source"] = top.get("source", "")
        result["url"] = top.get("url", "")
    return result


def _clean_html(text: str) -> str:
    """HTML 태그 제거"""
    return re.sub(r"<[^>]+>", "", text).strip()
