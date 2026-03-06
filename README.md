# 살까말까 (SalkkamalKka) v2

> AI 기반 부동산 실거래 주간 뉴스레터 자동화 파이프라인

내집마련을 준비하는 30~40대 실수요자를 위한 **부동산 주간 브리핑**을 자동으로 생성하고 발송하는 시스템입니다.

## 핵심 차별화

| 구분 | 기존 서비스 (호갱노노 등) | 살까말까 |
|------|--------------------------|---------|
| 정보 접근 | 사용자가 직접 검색 (Pull) | 매주 이메일로 자동 수신 (Push) |
| 데이터 해석 | 수치·그래프만 제공 | GPT가 맥락과 의미 해석 |
| 타이밍 판단 | 없음 | "살까 / 기다릴까" 신호 직접 제공 |
| 임장 정보 | 없음 | 교통·학군·인프라 자동 수집 |

## 주요 기능

### 무료 (Free)
- **실거래 데이터 수집** — 국토부 공식 API(15126468)에서 아파트 매매 실거래가 자동 수집
- **AI 임장 분석** — GPT-4o가 교통, 학군, 인프라를 종합한 임장 수준 서술 생성 (2개 단지)
- **타이밍 신호** — 시장 데이터 기반 "관망 / 조심스런 매수 / 적극 매수" 판단
- **주간 뉴스** — 정책·금리 변화 해설 1건
- **뉴스레터 자동 발송** — 매주 월요일 아침, 구독자에게 HTML 이메일 자동 발송

### 유료 (Standard / Premium)
- **급매 알림** — 직전 거래 대비 5%+ 하락 자동 감지 + GPT 해설 (최대 3건)
- **전세가율 위험 경보** — 70%/80% 기준 CAUTION/DANGER 경보 (최대 2건)
- **단지 비교 리포트** — 지정 단지 가격 이력 비교 (월 1회)
- **구독자 Q&A** — 유료 구독자 질문 2건 GPT 답변

## 아키텍처

```
[STEP 1] 데이터 수집
  collector/molit.py   → 국토부 실거래가 API (2개월치)
  collector/kakao.py   → 도로명주소 API + Haversine 거리 계산
        ↓
[STEP 2] 공통 AI 분석
  analyzer/gpt.py      → 시장 요약, 단지 임장 서술, 타이밍 신호, 편집장 총평
        ↓
[STEP 3] 유료 전용 분석
  premium/detector.py  → 급매 감지, 전세가율 위험, 단지 비교
  premium/analyzer.py  → GPT-4o 해설 생성
        ↓
[STEP 4] 리포트 생성
  reporter/builder.py  → 무료 HTML 조립
  premium/builder.py   → 유료 섹션 추가 (무료 HTML 기반)
        ↓
[STEP 5] 플랜별 분리 발송
  sender/resend.py     → free / standard / premium 분기 발송
```

## 프로젝트 구조

```
salkka-pipeline/
├── main.py                    # 파이프라인 진입점 (5단계 오케스트레이터)
├── config.py                  # 환경변수 및 설정 관리
├── requirements.txt           # Python 의존성
├── .env.example               # 환경변수 템플릿
│
├── collector/                 # [STEP 1] 데이터 수집
│   ├── molit.py               #   국토부 실거래가 API (15126468 상세 자료)
│   └── kakao.py               #   도로명주소 API + Haversine + 자체 좌표 DB
│
├── analyzer/                  # [STEP 2] 공통 AI 분석
│   └── gpt.py                 #   GPT 분석 4종 (4o + 4o-mini 혼합)
│
├── prompts/                   # 프롬프트 관리
│   └── templates.py           #   시스템/유저 프롬프트 템플릿 4종
│
├── premium/                   # [STEP 3] 유료 구독자 전용
│   ├── detector.py            #   급매 감지 / 전세 위험 / 단지 비교 로직
│   ├── analyzer.py            #   유료 GPT 분석 (전부 gpt-4o)
│   └── builder.py             #   유료 HTML 섹션 조립
│
├── reporter/                  # [STEP 4] 리포트 생성
│   └── builder.py             #   무료 HTML 이메일 조립
│
├── sender/                    # [STEP 5] 발송
│   └── resend.py              #   Resend API 플랜별 분리 발송
│
├── utils/                     # 공통 유틸리티
│   └── db.py                  #   Supabase 구독자 관리 + 발송 이력
│
├── data/                      # 런타임 데이터 (gitignore)
│   ├── trades_summary.json    #   주간 통계 체크포인트
│   ├── trades_all.json        #   전체 실거래 목록
│   ├── notable_trades.json    #   주목 단지 목록
│   ├── free_vol*.html         #   무료 뉴스레터 HTML
│   └── premium_vol*.html      #   유료 뉴스레터 HTML
│
└── .github/workflows/
    └── weekly.yml             #   매주 월요일 자동 실행
```

## 빠른 시작

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열고 각 API 키를 입력합니다:

| 환경변수 | 필수 | 발급처 |
|----------|------|--------|
| `MOLIT_API_KEY` | O | [공공데이터포털](https://www.data.go.kr/data/15126468/openapi.do) — 아파트매매 실거래 상세 자료 |
| `JUSO_API_KEY` | O | [도로명주소 API](https://business.juso.go.kr/addrlink/openApi/apiExprn.do) — 무료, 사업자 불필요 |
| `OPENAI_API_KEY` | O | [OpenAI Platform](https://platform.openai.com) |
| `SUPABASE_URL` | O | [Supabase](https://supabase.com) — 프로젝트 URL |
| `SUPABASE_KEY` | O | [Supabase](https://supabase.com) — anon/public 키 |
| `RESEND_API_KEY` | O | [Resend](https://resend.com) |
| `FROM_EMAIL` | - | 발신 이메일 주소 (기본: letter@salkkamalka.com) |
| `KAKAO_API_KEY` | - | 현재 미사용 (v3 전환 시 필요) |

### 3. Supabase 테이블 생성

```sql
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
```

### 4. 실행

```bash
# 전체 파이프라인 (5단계 자동 실행)
python main.py --region 마포구

# 단계별 실행
python main.py --step collect     # 데이터 수집만
python main.py --step analyze     # AI 분석만
python main.py --step send        # 발송만

# 테스트 모드 (발송 생략, HTML만 생성)
python main.py --region 강남구 --test
```

## 무료 vs 유료 콘텐츠

| 콘텐츠 | Free | Standard | Premium |
|--------|------|----------|---------|
| 시장 온도계 | O | O | O |
| 주목 단지 임장 서술 (2개) | O | O | O |
| 타이밍 신호 | O | O | O |
| 이번 주 뉴스 1건 | O | O | O |
| 편집장 총평 | O | O | O |
| **급매 알림** (최대 3건) | - | O | O |
| **전세가율 위험 경보** (최대 2건) | - | O | O |
| **단지 비교 리포트** (월 1회) | - | O | O |
| **구독자 Q&A** (매주 2건) | - | O | O |

> 무료는 "알게 해주는 것", 유료는 "결정하게 해주는 것"

## GPT 모델 전략

| 함수 | 모델 | 이유 |
|------|------|------|
| 시장 요약 | gpt-4o-mini | 수치 요약, 형식 중요 |
| 타이밍 신호 | gpt-4o-mini | 구조화 출력 |
| 임장 서술 | gpt-4o | 임장 서술 품질이 핵심 |
| 편집장 총평 | gpt-4o | 브랜드 톤, 독자 신뢰 |
| 유료 분석 전체 | gpt-4o | 유료 가치 증명 |

## 자동화 (GitHub Actions)

매주 **월요일 오전 5시 (KST)** 자동 실행됩니다.

- 스케줄: `cron: "0 20 * * 0"` (UTC 일요일 20:00)
- 수동 트리거: GitHub Actions 탭 → "Run workflow" → 지역/테스트 모드 선택
- 결과물: `data/` 디렉토리가 아티팩트로 30일간 보존

### 필요한 GitHub Secrets

```
MOLIT_API_KEY, JUSO_API_KEY, OPENAI_API_KEY
SUPABASE_URL, SUPABASE_KEY
RESEND_API_KEY, FROM_EMAIL
```

## 매주 편집자 업데이트 항목

`main.py` 상단에서 매주 수동 업데이트가 필요한 항목:

```python
THIS_WEEK_NEWS          # 이번 주 뉴스 1건 (카테고리, 제목, 본문, 임팩트)
THIS_WEEK_INDICATORS    # 타이밍 인디케이터 5개 (이름, 상태, 배지)
THIS_WEEK_QNA           # 유료 구독자 질문 2건
THIS_WEEK_JEONSE        # 전세가 데이터 (향후 API 자동화 예정)
MONTHLY_COMPARE_COMPLEXES  # 단지 비교 대상 (매월 업데이트)
```

## 지원 지역

현재 서울 10개 구를 지원합니다:

> 마포구, 강남구, 서초구, 송파구, 용산구, 성동구, 광진구, 노원구, 은평구, 서대문구

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.11 |
| AI | OpenAI GPT-4o / GPT-4o-mini |
| 실거래 데이터 | 국토부 실거래가 API (15126468 상세 자료) |
| 지오코딩 | 도로명주소 API (행안부) + Haversine |
| DB | Supabase (PostgreSQL) |
| 이메일 | Resend API |
| CI/CD | GitHub Actions |

## 월 비용 추정

```
MVP 단계 (구독자 ~100명, 주 1회 발송 기준)

AI API (gpt-4o + gpt-4o-mini)   약 500원
도메인                           약 1,200원
Supabase / Resend / 공공 API     0원 (무료 tier)
──────────────────────────────────────
합계                             약 1,700원/월
```

## 문서

상세 기술 문서는 [`salkka_TECH_DOC.md`](./salkka_TECH_DOC.md)를 참고하세요.

## 라이선스

Private Project
