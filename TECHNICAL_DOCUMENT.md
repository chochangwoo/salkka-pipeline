# 살까말까 (SalkkamalKka) — 기술 문서

> **프로젝트 정식 명칭:** 살까말까 (SalkkamalKka)
> **부제:** AI 기반 부동산 실거래 주간 뉴스레터 자동화 파이프라인
> **영문:** SalkkamalKka — Weekly Real Estate Brief for Home Buyers
> **버전:** 1.0 (MVP)
> **최종 수정일:** 2026-03-06

---

## 1. 프로젝트 개요

### 1.1 목적

**살까말까**는 내집마련을 준비하는 30~40대 실수요자를 위한 **부동산 주간 뉴스레터 자동화 시스템**입니다. 국토부 실거래가 데이터를 수집하고, AI가 임장(현장 방문) 수준의 분석을 수행하여, 매주 월요일 아침 구독자에게 HTML 이메일 뉴스레터를 자동 발송합니다.

### 1.2 핵심 가치

| 가치 | 설명 |
|------|------|
| **데이터 기반** | 국토부 공식 실거래가 API를 통한 정확한 거래 데이터 활용 |
| **AI 분석** | GPT-4o 기반 임장 서술, 타이밍 신호, 시장 요약 자동 생성 |
| **완전 자동화** | GitHub Actions로 매주 자동 실행 — 수집 → 분석 → 리포트 → 발송 |
| **실수요자 친화** | 전문 용어 대신 쉬운 말, 데이터 나열 대신 의미 해석 중심 |

### 1.3 대상 사용자

- **1차:** 내집마련을 준비 중인 30~40대 실수요자 (서울 아파트 중심)
- **2차:** 부동산 시장 동향에 관심 있는 일반 구독자

---

## 2. 시스템 아키텍처

### 2.1 전체 흐름도

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions (매주 월요일 05:00 KST)         │
│                     workflow_dispatch (수동 트리거 지원)           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      main.py (파이프라인 오케스트레이터)            │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │ STEP 1   │──▶│ STEP 2   │──▶│ STEP 3   │──▶│ STEP 4   │    │
│  │ 데이터   │   │ AI 분석  │   │ 리포트   │   │ 이메일   │    │
│  │ 수집     │   │          │   │ 생성     │   │ 발송     │    │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘    │
│       │              │              │              │           │
└───────┼──────────────┼──────────────┼──────────────┼───────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐
   │ 국토부  │   │ OpenAI   │   │  HTML   │   │ Resend   │
   │ API     │   │ GPT API  │   │ Builder │   │ API      │
   ├─────────┤   └──────────┘   └─────────┘   └──────────┘
   │ 카카오  │                                      │
   │ Maps API│                                      ▼
   └─────────┘                                 ┌──────────┐
                                               │ Supabase │
                                               │ (구독자DB)│
                                               └──────────┘
```

### 2.2 디렉토리 구조

```
salkka-pipeline/
├── main.py                  # 파이프라인 오케스트레이터 (진입점)
├── config.py                # 환경변수 관리 및 서비스 설정
├── requirements.txt         # Python 의존성 (3개)
├── .env.example             # 환경변수 템플릿
│
├── collector/               # [STEP 1] 데이터 수집 레이어
│   ├── molit.py             #   국토부 실거래가 API 연동
│   └── kakao.py             #   카카오맵 위치/인프라 데이터 수집
│
├── analyzer/                # [STEP 2] AI 분석 레이어
│   └── gpt.py               #   OpenAI GPT API 호출 및 분석
│
├── prompts/                 # GPT 프롬프트 관리
│   └── templates.py         #   시스템/유저 프롬프트 템플릿
│
├── reporter/                # [STEP 3] 리포트 생성 레이어
│   └── builder.py           #   HTML 이메일 뉴스레터 조립
│
├── sender/                  # [STEP 4] 발송 레이어
│   └── resend.py            #   Resend API 이메일 발송
│
├── utils/                   # 공통 유틸리티
│   └── db.py                #   Supabase REST API 연동
│
├── data/                    # 런타임 데이터 (gitignore 대상)
│   ├── trades_summary.json  #   주간 거래 통계 체크포인트
│   ├── notable_trades.json  #   주목 단지 데이터 체크포인트
│   └── newsletter_vol*.html #   생성된 뉴스레터 HTML
│
└── .github/
    └── workflows/
        └── weekly.yml       # GitHub Actions 주간 자동화 워크플로우
```

---

## 3. 파이프라인 상세

### 3.1 STEP 1 — 데이터 수집 (collector/)

#### 3.1.1 국토부 실거래가 수집 (`collector/molit.py`)

**데이터 소스:** 국토교통부 아파트매매 실거래 상세 자료 API (`data.go.kr`)

```
API Endpoint: http://openapi.molit.go.kr/.../getRTMSDataSvcAptTrade
요청 방식:    GET (XML 응답)
인증:        공공데이터포털 서비스 키 (MOLIT_API_KEY)
```

**주요 로직:**

| 함수 | 역할 |
|------|------|
| `fetch_trades(region, months)` | 최근 N개월 실거래 데이터 수집, XML 파싱 → `TradeRecord` 리스트 |
| `get_weekly_summary(records)` | 최근 7일 필터링 후 주간 통계 계산 (거래량, 평균가, 최고/최저가) |
| `get_notable_trades(records, top_n)` | 84㎡ 기준 거래 빈도 상위 단지 선정 (기본 2개) |

**TradeRecord 데이터 구조:**

```python
@dataclass
class TradeRecord:
    complex_name: str    # 단지명
    district: str        # 법정동
    area: float          # 전용면적 (㎡)
    floor: int           # 층
    price: int           # 거래금액 (만원)
    trade_date: str      # 거래일 (YYYY-MM-DD)
    build_year: int      # 건축연도
    road_name: str       # 도로명
```

**지원 지역 (법정동 코드 매핑):**

| 지역 | 코드 | 지역 | 코드 |
|------|------|------|------|
| 마포구 | 11440 | 강남구 | 11680 |
| 서초구 | 11650 | 송파구 | 11710 |
| 용산구 | 11170 | 성동구 | 11200 |
| 광진구 | 11215 | 노원구 | 11350 |
| 은평구 | 11380 | 서대문구 | 11410 |

#### 3.1.2 카카오맵 임장 요소 수집 (`collector/kakao.py`)

**데이터 소스:** 카카오 Maps REST API (`dapi.kakao.com`)

주목 단지별로 다음 임장 요소를 자동 수집합니다:

| 요소 | 검색 키워드 | 반경 | 출력 |
|------|------------|------|------|
| 지하철 | "지하철역" | 1,500m | 역명, 호선, 도보 시간 |
| 초등학교 | "초등학교" | 1,000m | 학교명, 도보 시간 |
| 학원 | "학원" | 500m | 반경 내 학원 수 |
| 대형마트 | "이마트/홈플러스/롯데마트/코스트코" | 1,500m | 마트명, 도보 시간 |
| 강남역 통근 | Haversine 직선거리 추정 | - | 대중교통 소요 분 (추정) |

**도보 시간 계산:** `거리(m) ÷ 80m/분` (성인 평균 보행 속도 기준)

**강남역 통근 시간 추정 공식:**
```
추정 시간 = (직선거리 × 1.4) ÷ 400m/분 + 환승 여유 10분
최대값 캡: 90분
```
> MVP 제약: 카카오 길찾기 API는 유료 플랜 필요 → 직선거리 기반 추정치 사용

**API 호출 간 딜레이:** 300ms (Rate Limit 방지)

---

### 3.2 STEP 2 — AI 분석 (analyzer/)

#### 3.2.1 GPT 모델 전략

비용 효율을 위한 **2-Tier 모델 전략**을 사용합니다:

| Tier | 모델 | 용도 | 선택 근거 |
|------|------|------|----------|
| **Economy** | `gpt-4o-mini` | 시장 요약, 타이밍 신호 | 구조화된 단순 정리 작업 |
| **Quality** | `gpt-4o` | 임장 서술, 편집장 총평 | 자연스러운 문체와 톤 품질 중요 |

**공통 설정:** `max_tokens=1000`, `temperature=0.7`

#### 3.2.2 4개 분석 함수

**1) `generate_market_summary()` — 시장 온도계 요약**
- 모델: `gpt-4o-mini`
- 입력: 주간 거래 통계 (거래량, 평균가, 최고가, 전세가율)
- 출력: 2~3문장 평문 시장 요약 (100자 내외)

**2) `analyze_complex()` — 단지 임장 서술**
- 모델: `gpt-4o`
- 입력: 실거래 데이터 + 카카오맵 임장 요소
- 출력: 생활 동선, 학군, 가격 평가 + 단점까지 포함한 임장 서술 (200자 내외)
- 페르소나: "10년 경력 부동산 전문가이자 친절한 친구"

**3) `analyze_timing()` — 타이밍 신호 판단**
- 모델: `gpt-4o-mini`
- 입력: 시장 데이터 (거래량, 평균가, 전세가율, 미분양, 금리)
- 출력: 구조화 응답
  - `신호`: "관망 유지" / "조심스런 매수 고려" / "적극 매수 고려" 중 택 1
  - `근거`: 데이터 기반 2~3문장
  - `힌트`: 실수요자 행동 힌트 1문장
- 페르소나: "감정 없이 데이터만 보는 냉철한 분석가"

**4) `generate_editor_summary()` — 편집장 총평**
- 모델: `gpt-4o`
- 입력: 시장 분위기, 타이밍 신호, 주목 단지명
- 출력: 따뜻하지만 솔직한 편집장의 한 마디 (150자 내외)
- 페르소나: "부동산 잘 아는 친구가 카톡으로 보내준 메시지" 톤

#### 3.2.3 프롬프트 관리 (`prompts/templates.py`)

모든 프롬프트는 `templates.py`에서 중앙 관리됩니다:
- **System Prompt:** 페르소나, 작성 원칙, 제약사항 정의
- **User Prompt:** `{변수명}` 형식의 포맷 문자열로 런타임 데이터 주입
- 버전 관리를 통한 A/B 테스트 가능 구조

---

### 3.3 STEP 3 — 리포트 생성 (reporter/)

#### 3.3.1 뉴스레터 구조 (`reporter/builder.py`)

인라인 CSS 기반 HTML 이메일 (640px 고정 폭, 신문 스타일 디자인):

| 섹션 | 내용 |
|------|------|
| **헤더** | 날짜, 타이틀 "살까말까", 호수(Vol.), 지역명 |
| **01. 시장 온도계** | 주간 거래량 / 84㎡ 평균가 / 분석 단지 수 (3-column 그리드) |
| **02. 주목할 단지** | 단지별 카드 (실거래가, 층수, 거래일 태그 + GPT 임장 서술) |
| **03. 타이밍 신호** | 다크 패널에 타이밍 신호 + 근거 + 인디케이터 테이블 |
| **04. 이번 주 뉴스** | 편집자가 직접 선정한 정책/시장 뉴스 1건 |
| **편집장 총평** | AI 편집장의 주간 총평 (다크 배경) |
| **푸터** | 구독 관리, 수신 거부, 투자 비권유 안내 |

**디자인 시스템:**
- 서체: Noto Serif KR (제목), Noto Sans KR (본문)
- 색상: `#1a1208` (다크), `#faf7f2` (배경), `#e8a020` (골드 액센트), `#c8401a` (레드 액센트)
- 인디케이터 배지: 긍정(초록), 주의(노란), 부정(빨강), 중립(회색)

---

### 3.4 STEP 4 — 이메일 발송 (sender/)

#### 3.4.1 Resend API 연동 (`sender/resend.py`)

```
Endpoint:  POST https://api.resend.com/emails
인증:      Bearer Token (RESEND_API_KEY)
무료 플랜: 월 3,000건
```

- 구독자 목록을 Supabase에서 조회 후, 개별 API 호출로 1건씩 발송
- 발송 완료 후 성공/실패 카운트를 Supabase `newsletter_logs` 테이블에 기록
- 테스트 모드 지원 (`send_test()`)

---

## 4. 데이터 저장소

### 4.1 Supabase (PostgreSQL)

Supabase Python SDK 없이 **PostgREST REST API를 직접 호출**하는 경량 구현입니다.

#### subscribers 테이블

```sql
CREATE TABLE subscribers (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    plan        TEXT DEFAULT 'free',       -- free / standard / premium
    region      TEXT DEFAULT '마포구',
    status      TEXT DEFAULT 'active',     -- active / unsubscribed
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ
);
```

#### newsletter_logs 테이블

```sql
CREATE TABLE newsletter_logs (
    id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    issue_num        INTEGER NOT NULL,
    region           TEXT,
    recipient_count  INTEGER,
    success_count    INTEGER,
    sent_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.2 로컬 파일 (체크포인트)

파이프라인 단계 간 데이터 전달을 위한 JSON 체크포인트:

| 파일 | 용도 |
|------|------|
| `data/trades_summary.json` | 주간 거래 통계 |
| `data/notable_trades.json` | 주목 단지 데이터 |
| `data/newsletter_vol{NNN}.html` | 완성된 뉴스레터 HTML |

---

## 5. 외부 서비스 의존성

| 서비스 | 용도 | 비용 | 환경변수 |
|--------|------|------|----------|
| **국토부 실거래가 API** | 아파트 매매 실거래 데이터 | 무료 (공공데이터포털) | `MOLIT_API_KEY` |
| **카카오맵 REST API** | 지오코딩, 주변 POI 검색 | 무료 (기본 쿼터) | `KAKAO_API_KEY` |
| **OpenAI API** | GPT-4o / GPT-4o-mini 텍스트 생성 | 종량제 | `OPENAI_API_KEY` |
| **Supabase** | 구독자 DB, 발송 이력 저장 | 무료 (Free Tier) | `SUPABASE_URL`, `SUPABASE_KEY` |
| **Resend** | 이메일 발송 | 무료 (월 3,000건) | `RESEND_API_KEY` |

---

## 6. 배포 및 자동화

### 6.1 GitHub Actions 워크플로우

**파일:** `.github/workflows/weekly.yml`

```
스케줄:     매주 일요일 20:00 UTC (= 월요일 05:00 KST)
런타임:     ubuntu-latest, Python 3.11
트리거:     cron + workflow_dispatch (수동)
아티팩트:   data/ 디렉토리 (30일 보존)
```

**수동 트리거 입력:**
- `region`: 분석 지역 (기본값: "마포구")
- `test_mode`: 테스트 모드 on/off (발송 생략)

### 6.2 필요 GitHub Secrets

```
MOLIT_API_KEY
KAKAO_API_KEY
OPENAI_API_KEY
SUPABASE_URL
SUPABASE_KEY
RESEND_API_KEY
FROM_EMAIL
```

---

## 7. 실행 방법

### 7.1 로컬 개발 환경 설정

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env 파일 편집 → 각 API 키 입력

# 3. Supabase 테이블 생성
# utils/db.py 하단의 SQL 스키마 참고하여 Supabase Dashboard에서 실행
```

### 7.2 실행 명령어

```bash
# 전체 파이프라인 실행
python main.py --region 마포구

# 단계별 실행
python main.py --step collect     # 데이터 수집만
python main.py --step analyze     # AI 분석만
python main.py --step send        # 발송만

# 테스트 모드 (발송 생략, HTML만 생성)
python main.py --region 강남구 --test
```

### 7.3 의존성

```
openai>=1.0.0          # OpenAI Python SDK
requests>=2.31.0       # HTTP 클라이언트 (모든 REST API 호출)
python-dotenv>=1.0.0   # .env 파일 로딩
```

Python 3.11 이상 필요.

---

## 8. 비용 구조 (1회 실행 기준 추정)

| 항목 | 단가 | 1회 사용량 | 추정 비용 |
|------|------|-----------|----------|
| GPT-4o (임장 서술 × 2, 편집장 총평 × 1) | ~$5/1M 입력 토큰 | ~3,000 토큰 | ~$0.02 |
| GPT-4o-mini (시장 요약 × 1, 타이밍 × 1) | ~$0.15/1M 입력 토큰 | ~2,000 토큰 | <$0.01 |
| 국토부 API | 무료 | - | $0 |
| 카카오맵 API | 무료 | ~10 호출 | $0 |
| Supabase | 무료 (Free Tier) | - | $0 |
| Resend | 무료 (월 3,000건) | 구독자 수 | $0 |
| **총 예상 비용** | | | **~$0.03/주** |

---

## 9. 현재 제약사항 및 향후 개선 방향

### 9.1 현재 제약사항 (MVP)

| 항목 | 현재 상태 | 비고 |
|------|----------|------|
| 뉴스 아이템 | 편집자가 `main.py`에서 수동 입력 | TODO: 뉴스 크롤링 자동화 |
| 타이밍 인디케이터 | 편집자가 `main.py`에서 수동 입력 | 매주 업데이트 필요 |
| 전세가율 | `62.0`으로 하드코딩 | TODO: 실시간 API 연동 |
| 전주 대비 거래량 변화 | "데이터 준비 중" 표시 | TODO: 주간 비교 로직 구현 |
| 고점 대비 가격 | "집계 중" 표시 | TODO: 역사 데이터 축적 필요 |
| 강남역 통근 시간 | Haversine 직선거리 추정 | 카카오 길찾기 API는 유료 |
| 지원 지역 | 서울 10개 구 | 법정동 코드 추가로 확장 가능 |
| 이메일 발송 | 구독자별 개별 API 호출 | 대량 발송 시 배치 처리 필요 |

### 9.2 향후 개선 방향

1. **뉴스 자동화:** 부동산 뉴스 크롤러 도입 → 자동 뉴스 요약/선별
2. **시계열 데이터:** 주간 데이터 축적 → 전주 대비, 고점 대비 자동 계산
3. **전세가율 API 연동:** 한국감정원 또는 KB부동산 데이터 연동
4. **지역 확장:** 서울 전 25개 구 + 수도권 주요 도시 지원
5. **구독자 세분화:** plan(free/standard/premium)별 차별화된 콘텐츠
6. **웹 아카이브:** 발송된 뉴스레터를 웹에서도 열람 가능하도록 구현
7. **성능 개선:** 비동기(async) 처리 도입, 대량 발송 시 배치 처리
8. **A/B 테스트:** 프롬프트 버전별 성과 추적 및 최적화

---

## 10. 명칭 제안

### 채택 명칭: **살까말까 (SalkkamalKka)**

현재 사용 중인 "살까말까"를 정식 브랜드명으로 확정합니다.

| 항목 | 내용 |
|------|------|
| **한국어 명칭** | 살까말까 |
| **영문 표기** | SalkkamalKka |
| **도메인** | salkkamalka.com |
| **발신 이메일** | letter@salkkamalka.com |
| **슬로건** | "내집마련을 준비하는 당신을 위한 주간 브리핑" |
| **영문 부제** | Weekly Real Estate Brief for Home Buyers |

### 대안 명칭 후보

| 명칭 | 의미 | 적합도 |
|------|------|--------|
| **집브리프 (JipBrief)** | 집 + Brief. 짧고 직관적 | 실용적이나 브랜딩 약함 |
| **내집레터 (NaejipLetter)** | 내집 + Newsletter. 목적이 명확 | 친근하나 차별화 부족 |
| **집센서 (JipSensor)** | 집 + Sensor. 시장을 감지하는 느낌 | 기술적 느낌, 뉴스레터 성격과 거리감 |
| **살까말까** (현행) | "살까 말까" 고민을 대변. 타겟 공감 극대화 | **최적** — 재미, 공감, 기억성 모두 충족 |

**"살까말까"를 유지하는 이유:**
- 30~40대 실수요자의 가장 핵심적인 고민("이 집 살까? 말까?")을 정확히 반영
- 한 번 들으면 잊기 어려운 높은 기억성
- 친근하고 재미있는 톤이 뉴스레터 브랜드에 적합
- 이미 코드베이스, 도메인, 이메일 주소에 일관되게 사용 중

---

## 부록 A. 환경변수 전체 목록

| 변수명 | 필수 | 설명 | 기본값 |
|--------|------|------|--------|
| `MOLIT_API_KEY` | O | 국토부 실거래가 API 키 | - |
| `KAKAO_API_KEY` | O | 카카오맵 REST API 키 | - |
| `OPENAI_API_KEY` | O | OpenAI API 키 | - |
| `SUPABASE_URL` | O | Supabase 프로젝트 URL | - |
| `SUPABASE_KEY` | O | Supabase anon/public 키 | - |
| `RESEND_API_KEY` | O | Resend API 키 | - |
| `FROM_EMAIL` | - | 발신 이메일 주소 | `letter@salkkamalka.com` |

## 부록 B. config.py 설정값

| 설정 | 값 | 설명 |
|------|-----|------|
| `GPT_MODEL_MAIN` | `gpt-4o-mini` | 단순 정리 작업용 모델 |
| `GPT_MODEL_WRITER` | `gpt-4o` | 품질 중요 서술용 모델 |
| `GPT_MAX_TOKENS` | `1000` | GPT 응답 최대 토큰 |
| `GPT_TEMPERATURE` | `0.7` | 창의성 수준 |
| `TARGET_REGION` | `마포구` | 기본 분석 지역 |
| `TARGET_CITY` | `서울특별시` | 기본 분석 도시 |
| `MAX_COMPLEXES` | `2` | 분석 대상 주목 단지 수 |
| `RADIUS_SCHOOL` | `1000`m | 학교 검색 반경 |
| `RADIUS_SUBWAY` | `1500`m | 지하철 검색 반경 |
| `RADIUS_MART` | `1500`m | 마트 검색 반경 |
| `RADIUS_ACADEMY` | `500`m | 학원 검색 반경 |
