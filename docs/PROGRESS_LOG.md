# 살까말까 진행 로그

## 2026-03-07 — v3.0 개편 + 운영 준비

### 완료된 작업

#### [1] 비교 지역 실거래 데이터 수집 로직 (우선순위 1)
- **문제**: 비교 테이블에 메인 지역만 데이터가 들어가고, 비교 대상 지역은 빈 값
- **해결**: `main.py` STEP 2-2.5에서 비교 지역별 `fetch_trades()` + `get_weekly_summary()` 호출
- **결과**: 비교 테이블에 실제 84㎡ 평균가, 거래량이 채워짐
- **파일**: `main.py`

#### [2] CTA 링크 config 관리 (우선순위 2)
- **문제**: 급매 CTA, 맞춤 분석, 관심 단지, 투표 버튼이 모두 `href="#"` 더미
- **해결**: `config.py`에 `CTA_PREMIUM_URL`, `CTA_CUSTOM_ANALYSIS`, `CTA_WATCHLIST_URL`, `CTA_VOTE_URL` 추가
- **결과**: `.env` 또는 환경변수로 URL 설정 가능, 기본값은 랜딩페이지 #pricing
- **파일**: `config.py`, `reporter/builder.py`

#### [3] 네이버 API 429 대응 — JSON 캐싱 (우선순위 3)
- **문제**: 네이버 부동산 API가 DELAY 1.5초에도 429 반환
- **해결**:
  - DELAY를 1.5초 → 3초로 상향
  - `data/cache/naver/` 디렉토리에 JSON 파일 캐싱 추가
  - 캐시 TTL: 7일 (주 1회 발행 주기에 맞춤)
  - `search_complexes()`와 `enrich_complex()` 모두 캐시 적용
  - 첫 수집 이후에는 API 호출 없이 캐시에서 로드
- **파일**: `collector/naver_land.py`

#### [4] v3.0 뉴스레터 구조 개편 (이전 세션)
- 예산대×권역 비교 형식 전환
- "데이터 부족" 표현 전면 제거
- AI 느낌 제거 (산문 서술)
- 투표 섹션 추가
- 프리미엄 유도 장치 (블러, CTA)

#### [5] 마케팅 자동화 모듈 추가 (이전 세션)
- `marketing/card_generator.py` — 인스타 카드뉴스
- `marketing/archive_generator.py` — SEO 아카이브
- `marketing/blog_post_generator.py` — 블로그/카페/블라인드
- `.github/workflows/marketing.yml` — GitHub Actions 워크플로우

---

### 남은 작업 (우선순위순)

| # | 작업 | 난이도 | 비고 |
|---|------|--------|------|
| 1 | 전세가율 데이터 자동화 | 중 | 현재 62.0 하드코딩, 한국부동산원 API 또는 네이버 전세 데이터 활용 |
| 2 | 뉴스 자동 수집 | 중 | THIS_WEEK_NEWS가 수동, 부동산 뉴스 크롤링+GPT 요약 |
| 3 | 공급 데이터 지역 확장 | 하 | CURATED_SUPPLY에 3개 지역만, 더 많은 지역 추가 |
| 4 | 투표 백엔드 구현 | 중 | Supabase에 votes 테이블 + API 엔드포인트 |
| 5 | 결제 시스템 연동 | 상 | 토스페이먼츠/포트원 |
| 6 | 인스타 카드 PNG 자동 변환 | 하 | Playwright 스크린샷 |
| 7 | 비교 지역 자동 매칭 | 중 | 투표 결과 기반 또는 예산대 자동 매칭 |
