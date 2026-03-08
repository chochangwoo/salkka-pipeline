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

#### [6] 전세가율 자동 추정 (2026-03-07)
- **문제**: `jeonse_rate=62.0` 하드코딩
- **해결**: `collector/naver_land.py`에 `estimate_jeonse_rate()` 함수 추가
  - 세대수 상위 N개 단지의 매매/전세 호가 중위값으로 전세가율 계산
  - 7일 캐시 적용, 이상치(30~95% 범위 외) 자동 제거
- **결과**: `main.py` STEP 1.5에서 자동 추정 후 파이프라인 전체에 반영
- **파일**: `collector/naver_land.py`, `main.py`

#### [7] 뉴스 자동 수집 + GPT 요약 (2026-03-07)
- **문제**: `THIS_WEEK_NEWS`가 수동 입력
- **해결**: `collector/news.py` 신규 생성
  - Google News RSS로 부동산 뉴스 자동 수집
  - 키워드 필터링 + 지역 우선 선정
  - GPT로 뉴스레터용 요약 (category/title/body/impact)
- **결과**: `main.py` STEP 2.5에서 자동 수집, 실패 시 수동 데이터 폴백
- **파일**: `collector/news.py`, `main.py`

#### [8] 공급 데이터 13개 지역 확장 (2026-03-07)
- **문제**: `CURATED_SUPPLY`에 3개 지역만 존재
- **해결**: 13개 지역으로 확장 (경기 남부 4개, 서울 6개, 경기 3개)
- **파일**: `collector/supply.py`

#### [9] 투표/관심단지 백엔드 (2026-03-07)
- **문제**: 투표/관심단지 기능에 DB 함수 없음
- **해결**: `utils/db.py`에 CRUD 함수 추가
  - `submit_vote()`, `has_voted()`, `get_vote_results()` — 투표
  - `add_to_watchlist()`, `get_watchlist()`, `remove_from_watchlist()` — 관심 단지
  - SQL 스키마 (votes, watchlist 테이블) 참고용 추가
- **파일**: `utils/db.py`

#### [10] 1호 실발행 완료 (2026-03-07)
- Vol.001 마포구 뉴스레터 발송 성공
- Supabase 테이블 4개 생성 (subscribers, newsletter_logs, votes, watchlist)
- 구독자 등록 + 이메일 수신 확인 완료
- **파일**: `main.py` (파이프라인 end-to-end 검증)

#### [11] 마케팅 자동화 파이프라인 통합 (2026-03-07)
- **문제**: 마케팅 모듈이 독립 CLI, 데이터 포맷 불일치, `timing_result.json` 미저장
- **해결**:
  - `main.py` STEP 4.5에 마케팅 생성 통합 (카드뉴스 + 블로그/카페/블라인드 + SEO 아카이브)
  - `timing_result.json`, `marketing_summary.json` 체크포인트 자동 저장
  - `marketing.yml` 간소화 (생성은 main.py, 워크플로우는 배포+보존만)
  - `weekly.yml`에 JUSO_API_KEY 추가, 아티팩트명 통일
- **생성물**: 파이프라인 1회 실행 시 자동 생성
  - `data/cards/card_vol{NNN}.html` — 인스타 카드뉴스 (3장)
  - `data/posts/naver_blog_vol{NNN}.md` — 네이버 블로그 포스팅
  - `data/posts/cafe_post_vol{NNN}.txt` — 부동산 카페 게시글
  - `data/posts/blind_post_vol{NNN}.txt` — 블라인드 게시글
  - `data/archive/vol{NNN}.html` — SEO 아카이브 웹페이지
- **파일**: `main.py`, `.github/workflows/marketing.yml`, `.github/workflows/weekly.yml`

---

### 남은 작업 (우선순위순)

| # | 작업 | 난이도 | 비고 |
|---|------|--------|------|
| 1 | 결제 시스템 연동 | 상 | 토스페이먼츠/포트원 |
| 2 | 인스타 카드 PNG 자동 변환 | 하 | Playwright 스크린샷 |
| 3 | 비교 지역 자동 매칭 | 중 | 투표 결과 기반 또는 예산대 자동 매칭 |
| 4 | 네이버 429 근본 해결 | 중 | 쿠키/세션 관리 또는 프록시 |
