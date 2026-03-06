# 살까말까 (SalkkamalKka)

> AI 기반 부동산 실거래 주간 뉴스레터 자동화 파이프라인

내집마련을 준비하는 30~40대 실수요자를 위한 **부동산 주간 브리핑**을 자동으로 생성하고 발송하는 시스템입니다.

## 주요 기능

- **실거래 데이터 수집** — 국토부 공식 API에서 아파트 매매 실거래가 자동 수집
- **AI 임장 분석** — GPT-4o가 교통, 학군, 인프라를 종합한 임장 수준 서술 생성
- **타이밍 신호** — 시장 데이터 기반 "관망 / 조심스런 매수 / 적극 매수" 판단
- **뉴스레터 자동 발송** — 매주 월요일 아침, 구독자에게 HTML 이메일 자동 발송

## 아키텍처

```
수집 (국토부 + 카카오맵)  →  AI 분석 (GPT-4o)  →  HTML 리포트 생성  →  이메일 발송 (Resend)
         │                        │                      │                     │
    collector/               analyzer/              reporter/              sender/
    molit.py                 gpt.py                 builder.py             resend.py
    kakao.py                 prompts/templates.py
```

## 프로젝트 구조

```
salkka-pipeline/
├── main.py                  # 파이프라인 진입점
├── config.py                # 환경변수 및 설정 관리
├── collector/               # 데이터 수집
│   ├── molit.py             #   국토부 실거래가 API
│   └── kakao.py             #   카카오맵 임장 요소 (지하철, 학교, 마트 등)
├── analyzer/                # AI 분석
│   └── gpt.py               #   GPT 호출 (임장 서술, 타이밍, 시장 요약, 총평)
├── prompts/                 # 프롬프트 관리
│   └── templates.py         #   시스템/유저 프롬프트 템플릿
├── reporter/                # 리포트 생성
│   └── builder.py           #   HTML 이메일 뉴스레터 조립
├── sender/                  # 발송
│   └── resend.py            #   Resend API 이메일 발송
├── utils/                   # 공통 유틸리티
│   └── db.py                #   Supabase 구독자 DB 연동
├── .github/workflows/
│   └── weekly.yml           #   GitHub Actions 주간 자동화
├── requirements.txt
├── .env.example
└── TECHNICAL_DOCUMENT.md    # 상세 기술 문서
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

| 환경변수 | 발급처 |
|----------|--------|
| `MOLIT_API_KEY` | [공공데이터포털](https://www.data.go.kr) — "아파트매매 실거래 상세 자료" |
| `KAKAO_API_KEY` | [카카오 개발자센터](https://developers.kakao.com) — REST API 키 |
| `OPENAI_API_KEY` | [OpenAI Platform](https://platform.openai.com) |
| `SUPABASE_URL` | [Supabase](https://supabase.com) — 프로젝트 URL |
| `SUPABASE_KEY` | [Supabase](https://supabase.com) — anon/public 키 |
| `RESEND_API_KEY` | [Resend](https://resend.com) |
| `FROM_EMAIL` | 발신 이메일 주소 (Resend에서 인증된 도메인) |

### 3. Supabase 테이블 생성

```sql
-- 구독자 테이블
CREATE TABLE subscribers (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    plan        TEXT DEFAULT 'free',
    region      TEXT DEFAULT '마포구',
    status      TEXT DEFAULT 'active',
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
# 전체 파이프라인
python main.py --region 마포구

# 단계별 실행
python main.py --step collect     # 데이터 수집만
python main.py --step analyze     # AI 분석만
python main.py --step send        # 발송만

# 테스트 모드 (발송 생략, HTML만 생성)
python main.py --region 강남구 --test
```

## 자동화 (GitHub Actions)

매주 **월요일 오전 5시 (KST)** 자동 실행됩니다.

- 스케줄: `cron: "0 20 * * 0"` (UTC 일요일 20:00)
- 수동 트리거: GitHub Actions 탭 → "Run workflow" → 지역/테스트 모드 선택
- 결과물: `data/` 디렉토리가 아티팩트로 30일간 보존

### 필요한 GitHub Secrets

```
MOLIT_API_KEY, KAKAO_API_KEY, OPENAI_API_KEY
SUPABASE_URL, SUPABASE_KEY
RESEND_API_KEY, FROM_EMAIL
```

## 지원 지역

현재 서울 10개 구를 지원합니다:

> 마포구, 강남구, 서초구, 송파구, 용산구, 성동구, 광진구, 노원구, 은평구, 서대문구

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.11 |
| AI | OpenAI GPT-4o / GPT-4o-mini |
| 데이터 | 국토부 실거래가 API, 카카오맵 REST API |
| DB | Supabase (PostgreSQL) |
| 이메일 | Resend API |
| CI/CD | GitHub Actions |

## 비용

1회 실행당 약 **$0.03** (GPT API 비용). 나머지 서비스는 무료 티어 사용.

## 문서

상세 기술 문서는 [`TECHNICAL_DOCUMENT.md`](./TECHNICAL_DOCUMENT.md)를 참고하세요.

## 라이선스

Private Project
