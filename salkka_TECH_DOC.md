# 살까말까 — 기술 문서 v2.0

> 내집마련 실수요자를 위한 부동산 주간 브리핑 자동화 시스템  
> 작성 기준: 2025년 3월 / 파이프라인 v2 / Claude Code 환경

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [기술 스택 및 비용](#3-기술-스택-및-비용)
4. [데이터 수집](#4-데이터-수집)
5. [AI 분석 설계](#5-ai-분석-설계)
6. [유료 전용 기능](#6-유료-전용-기능-premium)
7. [HTML 리포트 생성](#7-html-리포트-생성)
8. [이메일 발송 구조](#8-이메일-발송-구조)
9. [자동화 (GitHub Actions)](#9-자동화-github-actions)
10. [환경변수 및 실행 가이드](#10-환경변수-및-실행-가이드)
11. [API 현황 및 제약사항](#11-api-현황-및-제약사항)
12. [무료 vs 유료 콘텐츠 설계](#12-무료-vs-유료-콘텐츠-설계)
13. [수익화 및 사업 현황](#13-수익화-및-사업-현황)
14. [향후 개발 계획](#14-향후-개발-계획)

---

## 1. 프로젝트 개요

### 서비스 정의

**"부동산 잘 아는 친구가 매주 보내주는 내집마련 브리핑"**

국토교통부 실거래 데이터를 GPT로 분석해, 내집마련 실수요자에게 매주 월요일 아침 자동으로 이메일 브리핑을 발송하는 뉴스레터 서비스.

### 핵심 차별화

| 구분 | 기존 서비스 (호갱노노 등) | 살까말까 |
|------|--------------------------|---------|
| 정보 접근 | 사용자가 직접 검색 (Pull) | 매주 이메일로 자동 수신 (Push) |
| 데이터 해석 | 수치·그래프만 제공 | GPT가 맥락과 의미 해석 |
| 타이밍 판단 | 없음 | "살까 / 기다릴까" 신호 직접 제공 |
| 임장 정보 | 없음 | 교통·학군·인프라 자동 수집 |
| 타겟 | 모든 부동산 관심자 | 내집마련 실수요자 전용 |

### 콘텐츠 구조 (뉴스레터 섹션)

```
01 · 이번 주 시장 온도계     — 거래량, 평균가, 전세가율
02 · 주목할 단지              — AI 임장 서술 (최대 2개)
03 · 실수요자 타이밍 신호     — 관망 / 조심스런 매수 / 적극 매수
04 · 꼭 알아야 할 뉴스 1건   — 정책·금리 변화 해설
    편집장 총평               — AI 편집장의 한 마디
```

---

## 2. 시스템 아키텍처

### 전체 파이프라인 흐름

```
[STEP 1] 데이터 수집
  collector/molit.py   → 국토부 실거래가 API (2개월치)
  collector/kakao.py   → 임장 요소 (MVP: 주소→좌표, Haversine)
        ↓
[STEP 2] 공통 AI 분석
  analyzer/gpt.py      → 시장 요약, 단지 임장 서술, 타이밍 신호, 편집장 총평
        ↓
[STEP 3] 유료 전용 분석
  premium/detector.py  → 급매 감지, 전세가율 위험, 단지 비교
  premium/analyzer.py  → GPT 해설 생성 (전부 gpt-4o)
        ↓
[STEP 4] 리포트 생성
  reporter/builder.py  → 무료 HTML 조립
  premium/builder.py   → 유료 섹션 추가 (무료 HTML 기반)
        ↓
[STEP 5] 플랜별 분리 발송
  utils/db.py          → Supabase에서 구독자 플랜 조회
  sender/resend.py     → free / standard / premium 분기 발송
```

### 디렉토리 구조

```
salkka-pipeline/
├── main.py                    # 전체 파이프라인 실행 진입점
├── config.py                  # 환경변수 + 서비스 설정
├── requirements.txt           # Python 의존성 (3개)
├── .env.example               # 환경변수 템플릿
│
├── collector/
│   ├── molit.py               # 국토부 실거래가 API 수집 + 파싱
│   └── kakao.py               # 임장 요소 수집 (주소→좌표, 거리 계산)
│
├── analyzer/
│   └── gpt.py                 # GPT 분석 함수 4종 (4o + 4o-mini 혼합)
│
├── prompts/
│   └── templates.py           # 프롬프트 템플릿 4종 (버전 관리용)
│
├── premium/                   # 유료 구독자 전용 기능
│   ├── detector.py            # 급매 감지 / 전세 위험 / 단지 비교 로직
│   ├── analyzer.py            # 유료 GPT 분석 (전부 gpt-4o)
│   └── builder.py             # 유료 HTML 섹션 조립
│
├── reporter/
│   └── builder.py             # 무료 HTML 이메일 조립
│
├── sender/
│   └── resend.py              # Resend API 이메일 발송
│
├── utils/
│   └── db.py                  # Supabase 구독자 관리 + 발송 이력
│
└── .github/workflows/
    └── weekly.yml             # 매주 월요일 자동 실행 (GitHub Actions)
```

### 데이터 흐름 및 체크포인트

파이프라인 각 단계는 `data/` 폴더에 JSON으로 중간 저장.  
단계별 독립 실행(`--step`)이 가능해 디버깅과 비용 절감에 유리.

```
data/
├── trades_summary.json    # STEP 1 산출물 — 주간 통계
├── trades_all.json        # STEP 1 산출물 — 전체 실거래 목록
├── notable_trades.json    # STEP 1 산출물 — 주목 단지 목록
├── analysis.json          # STEP 2 산출물 — GPT 분석 결과
├── free_vol001.html       # STEP 4 산출물 — 무료 뉴스레터
└── premium_vol001.html    # STEP 4 산출물 — 유료 뉴스레터
```

---

## 3. 기술 스택 및 비용

### 스택 선택 이유

| 역할 | 기술/서비스 | 선택 이유 | 월 비용 |
|------|------------|---------|--------|
| 실거래 수집 | 국토부 실거래가 API (15126468) | 공식 공공 API, 완전 무료 | 무료 |
| 임장 요소 (MVP) | 도로명주소 API + Haversine | 사업자 없이 개인 계정으로 사용 가능 | 무료 |
| 임장 요소 (v2) | 네이버 지도 API | 개인사업자 등록 후 전환 예정, 월 300만 건 무료 | 무료 |
| AI 분석 | GPT-4o / GPT-4o-mini | 품질·비용 혼합 전략 | ~5,000원 |
| DB | Supabase (PostgreSQL) | 무료 tier로 구독자 관리 충분 | 무료 |
| 이메일 발송 | Resend | 3,000건/월 무료, API 단순 | 무료 |
| 자동화 | GitHub Actions | Cron 스케줄, 무료 | 무료 |
| 도메인 | 개인 도메인 | 발신 신뢰도 필수 | ~1,200원 |

### 월 비용 추정

```
MVP 단계 (구독자 ~100명, 주 1회 발송 기준)

AI API (gpt-4o-mini 위주)   약 500원
도메인                       약 1,200원
Supabase                    0원 (무료 tier)
Resend                      0원 (3,000건 이내)
공공 API 전부               0원
─────────────────────────────────────
합계                         약 1,700원/월
```

> 구독자 3,000명까지 이메일 발송 비용 추가 없음.  
> GPT 호출 횟수는 구독자 수와 무관 (주 1회 리포트 생성이므로).

### Python 의존성 (`requirements.txt`)

```
openai>=1.0.0
requests>=2.31.0
python-dotenv>=1.0.0
```

---

## 4. 데이터 수집

### 4-1. 국토부 실거래가 API (`collector/molit.py`)

#### 확정 API

| 항목 | 내용 |
|------|------|
| **사용 API** | **15126468 — 아파트 매매 실거래가 상세 자료** ✅ |
| 미사용 API | 15126469 — 일반 자료 (필드 수 적어 제외) |
| 엔드포인트 | `http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev` |
| 응답 형식 | XML |
| 활용 신청 | 공공데이터포털 회원가입 후 자동승인 (1~2시간) |
| 개발 트래픽 | 10,000건/일 |

#### 주요 파라미터

```python
params = {
    "serviceKey": MOLIT_API_KEY,   # 공공데이터포털 발급 키
    "LAWD_CD":    "11440",         # 법정동 코드 앞 5자리
    "DEAL_YMD":   "202503",        # 계약년월 6자리
    "pageNo":     "1",
    "numOfRows":  "100",
}
```

#### 법정동 코드 주요 목록

```python
CODE_MAP = {
    "마포구":   "11440",   "강남구":   "11680",
    "서초구":   "11650",   "송파구":   "11710",
    "용산구":   "11170",   "성동구":   "11200",
    "광진구":   "11215",   "노원구":   "11350",
    "은평구":   "11380",   "서대문구": "11410",
}
```

#### 주요 응답 필드

```
aptNm        → 아파트명
dealAmount   → 거래금액 (만원, 쉼표 포함 문자열)
excluUseAr   → 전용면적 (㎡)
floor        → 층
dealYear / dealMonth / dealDay  → 계약일
buildYear    → 건축연도
roadNm       → 도로명
umdNm        → 법정동명
```

#### 주요 함수

```python
fetch_trades(region, months=2)
# → 최근 N개월 실거래 데이터 수집, TradeRecord 리스트 반환

get_weekly_summary(records)
# → {total_count, avg_price_84, avg_price_59, max_price, min_price}

get_notable_trades(records, top_n=2)
# → 거래량 많은 단지 상위 N개의 최신 거래 1건씩 반환
```

---

### 4-2. 임장 요소 수집 (`collector/kakao.py`)

#### MVP vs 정식 전략

| 단계 | 사용 방법 | 조건 | 시점 |
|------|----------|------|------|
| MVP (현재) | 도로명주소 API + Haversine 공식 | 개인 계정 가능, 사업자 불필요 | 지금 바로 |
| 정식 v2 | 네이버 지도 API | 네이버 클라우드 계정 (개인 가능, 월 300만 건 무료) | 개인사업자 등록 후 |
| 고도화 | 카카오 로컬 API | 비즈니스 인증 필요 (2024.12~ 정책 변경) | 필요 시 |

> **카카오맵 현황**: 2024년 12월 1일부터 신규 앱의 카카오맵 API 사용에  
> 활성화 설정 및 앱 권한 신청(비즈니스 인증) 필요. MVP 단계에서 제외.

#### 거리 계산 로직 (Haversine)

```python
# 두 좌표 간 직선거리 계산
def haversine(lat1, lng1, lat2, lng2) -> float:  # 반환: 미터

# 직선거리 → 도보 분 변환 (평균 80m/분)
walk_min = max(1, round(distance_m / 80))

# 강남역 대중교통 추정 (MVP 근사값)
# 직선거리 × 1.4(우회계수) / 400m/분(대중교통속도) + 10분(환승)
transit_min = min(int(dist_m * 1.4 / 400) + 10, 90)
```

#### 수집 항목 및 공공 데이터 소스

| 임장 요소 | MVP 데이터 소스 | 비고 |
|----------|---------------|------|
| 주소 → 좌표 | 도로명주소 API (행안부) | 무료, 사업자 불필요 |
| 지하철역 거리 | Haversine 직선거리 | 지하철역 좌표 DB 자체 보유 |
| 초등학교 거리 | 학교알리미 공공 API | 무료 |
| 강남역 출근 시간 | 직선거리 기반 추정값 | 정식 전환 시 네이버 API 사용 |
| 대형마트 | (v2.2에서 추가) | 네이버 장소 검색 |
| 학원 수 | (v2.2에서 추가) | 네이버 장소 검색 |

#### LocationFactors 데이터 클래스

```python
@dataclass
class LocationFactors:
    complex_name: str
    lat: float
    lng: float
    nearest_subway: str       # 가장 가까운 지하철역명
    subway_line: str          # 호선
    subway_walk_min: int      # 도보 분
    gangnam_transit_min: int  # 강남역까지 대중교통 분 (추정)
    nearest_elementary: str   # 가장 가까운 초등학교
    elementary_walk_min: int  # 도보 분
    academy_count: int        # 반경 500m 학원 수
    has_large_mart: bool      # 대형마트 반경 1.5km
    nearest_mart: str
    mart_walk_min: int
```

---

## 5. AI 분석 설계

### GPT 모델 혼합 전략 (`config.py`)

```python
GPT_MODEL_MAIN   = "gpt-4o-mini"  # 단순 정리, 구조적 출력
GPT_MODEL_WRITER = "gpt-4o"       # 핵심 서술, 브랜드 톤
GPT_MAX_TOKENS   = 1000
GPT_TEMPERATURE  = 0.7
```

| 함수 | 모델 | 이유 |
|------|------|------|
| `generate_market_summary` | gpt-4o-mini | 수치 요약, 품질보다 형식 중요 |
| `analyze_timing` | gpt-4o-mini | 구조화된 출력 (신호/근거/힌트) |
| `analyze_complex` | gpt-4o | 임장 서술 품질이 핵심 가치 |
| `generate_editor_summary` | gpt-4o | 브랜드 톤, 독자 신뢰 형성 |
| 유료 `analyze_*` 전체 | gpt-4o | 유료 가치 증명, 품질 우선 |

### 프롬프트 구조 (`prompts/templates.py`)

#### ① 단지 임장 서술 (`COMPLEX_DESCRIPTION_*`)

```
[시스템]
- 역할: 10년 경력 부동산 전문가 + 친한 친구
- 타겟: 30~40대 내집마련 실수요자
- 원칙: 전문용어 지양, 데이터 나열 금지, 장단점 솔직하게

[입력]
- 단지명, 실거래가, 면적/층/거래일, 직전 거래 대비 변동
- 임장 요소 7종: 초등학교, 지하철, 강남 출근, 학원 수, 마트, 특이사항

[출력 형식]
1단락: 생활 동선 (교통·인프라)
2단락: 학군·교육 환경
3단락: 가격 평가 + 솔직한 단점
마지막: ✅ 한 줄 요약

[분량] 200자 내외
```

#### ② 타이밍 신호 (`TIMING_SIGNAL_*`)

```
[시스템]
- 역할: 냉철한 데이터 분석가
- 제약: 매수/매도 직접 권유 금지, 불확실한 것은 솔직하게

[입력]
- 주간 거래량, 평균가, 전세가율, 미분양, 금리 동향, 급매물 현황

[출력 형식]
신호: "관망 유지" / "조심스런 매수 고려" / "적극 매수 고려" 중 1개
근거: 데이터 기반 2~3문장
힌트: 실수요자 행동 힌트 1문장

[분량] 150자 내외
```

#### ③ 편집장 총평 (`EDITOR_SUMMARY_*`)

```
[시스템]
- 역할: 살까말까 AI 편집장
- 톤: 부동산 잘 아는 친구의 카톡 메시지
- 원칙: 과장 금지, 겁주지 않기, 현실적이되 희망적으로

[입력]
- 시장 분위기, 타이밍 신호, 주목 단지명, 특이 이슈

[출력] 큰따옴표로 감싼 한 문단 / 150자 내외
```

#### ④ 시장 온도계 요약 (`MARKET_SUMMARY_*`)

```
[시스템]
- 역할: 데이터 분석 전문가
- 원칙: 숫자 나열 금지, 의미 중심 해석

[입력] 거래량, 84㎡·59㎡ 평균가, 최고가, 전세가율

[출력] 2~3문장 / 100자 내외
```

---

## 6. 유료 전용 기능 (`premium/`)

### 6-1. 급매 감지 (`detector.py` → `detect_urgent_sales`)

직전 거래 대비 N% 이상 하락한 거래를 자동 감지.

```python
detect_urgent_sales(trades, drop_threshold=0.05)  # 기본 5% 이상 하락
```

**긴급도 분류**

| 등급 | 기준 | 표시 |
|------|------|------|
| HIGH | 직전 거래 대비 -8% 이상 | 🔴 고긴급 |
| MEDIUM | -5% ~ -8% | 🟡 주의 |

**GPT 해설 내용 (`analyzer.py` → `analyze_urgent_sale`)**
- 급락 이유 가능성 분석 (시장 상황 / 개인 사정 / 하자 우려)
- 실수요자 관심 여부 판단
- 확인해야 할 사항 2~3가지

---

### 6-2. 전세가율 위험 경보 (`detect_jeonse_risk`)

```python
detect_jeonse_risk(
    jeonse_data,
    danger_threshold=0.80,   # 80% 이상 → DANGER
    caution_threshold=0.70   # 70% 이상 → CAUTION
)
```

| 등급 | 전세가율 | 색상 | 설명 |
|------|---------|------|------|
| DANGER | 80% 이상 | 🔴 빨강 | 역전세 위험, 전세금 반환 리스크 |
| CAUTION | 70~80% | 🟡 노랑 | 주의 구간, 추가 하락 시 역전세 가능 |

**GPT 해설**: 세입자 관점 + 매수 희망자 관점 각각 설명

---

### 6-3. 단지 비교 리포트 (`compare_complexes`)

```python
# 매월 첫째 주만 실행 (비용 절감)
if datetime.today().day <= 7:
    histories = compare_complexes(trades, MONTHLY_COMPARE_COMPLEXES)
```

**비교 항목**

| 항목 | 설명 |
|------|------|
| 현재 실거래가 | 가장 최근 거래 기준 |
| 역대 고점 대비 낙폭 | `(peak - current) / peak * 100` |
| 최근 추세 | 최근 3건 기준 상승/하락/보합 |
| 거래 활성도 | 기간 내 거래 건수 |

**GPT 해설 마무리**: "A단지는 ~한 분께, B단지는 ~한 분께 더 맞습니다"

---

### 6-4. 독자 Q&A (`answer_subscriber_question`)

유료 구독자가 이메일 회신으로 보낸 질문을 매주 2건 선정해 GPT가 답변.

```python
# main.py 상단에서 매주 편집자가 업데이트
THIS_WEEK_QNA = [
    {"question": "마래푸 84㎡ 지금 9억 초반이면 살만한가요?", "answer": ""},
    {"question": "전세 만기 6개월 남았는데 매수하는 게 나을까요?",  "answer": ""},
]
```

---

### 6-5. 유료 HTML 조립 (`premium/builder.py`)

무료 HTML 기반 위에 프리미엄 섹션을 삽입하는 방식.

```python
# 무료 HTML 생성
free_html = build_newsletter(**common_kwargs)

# 유료 = 무료 기반 + 프리미엄 섹션 추가
premium_html = build_premium_newsletter(
    **common_kwargs,
    urgent_sales=urgent_sales,    # 급매 알림
    jeonse_risks=jeonse_risks,    # 전세 위험
    comparison=comparison,        # 단지 비교 (월 1회)
    qna_items=qna_items,          # Q&A
)
```

---

## 7. HTML 리포트 생성

### 디자인 시스템 (`reporter/builder.py`)

```
폰트:  Noto Serif KR (제목) + Noto Sans KR (본문)
색상:  #1a1208 (기본), #c8401a (강조), #e8a020 (골드), #faf7f2 (배경)
스타일: 신문 editorial 디자인, 인쇄 친화적
```

### 뉴스레터 HTML 섹션 구조

```
[헤더]
  - 날짜, 볼륨 번호, 지역명
  - 살까말까 로고 타이포그래피

[본문]
  01 · 시장 온도계     (3열 그리드: 거래량 / 평균가 / 단지 수)
  02 · 주목 단지       (단지 카드 × N개)
  03 · 타이밍 신호     (신호 배너 + 인디케이터 테이블)
  04 · 이번 주 뉴스    (카테고리 + 내집마련 임팩트)
  편집장 총평          (다크 배경 박스)

[유료 추가 섹션]        ← premium/builder.py 삽입
  ⚡ 급매 알림
  ⚠️ 전세가율 위험 경보
  📊 단지 비교 리포트   (월 1회)
  💬 구독자 Q&A

[푸터]
  - 구독 관리 / 수신 거부 링크
  - 면책 문구
```

---

## 8. 이메일 발송 구조

### 플랜별 분리 발송 (`sender/resend.py`)

```python
# STEP 5: Supabase에서 플랜별 구독자 분리
subscribers     = get_active_subscribers()
free_emails     = [s["email"] for s in subscribers if s["plan"] == "free"]
standard_emails = [s["email"] for s in subscribers if s["plan"] == "standard"]
premium_emails  = [s["email"] for s in subscribers if s["plan"] == "premium"]

# 무료 → 기본 HTML
send_newsletter(free_html,    subject_free,    free_emails)

# 스탠다드/프리미엄 → 유료 HTML
send_newsletter(premium_html, subject_premium, standard_emails)
send_newsletter(premium_html, subject_premium, premium_emails)
```

### Resend API 호출 구조

```python
POST https://api.resend.com/emails
Authorization: Bearer {RESEND_API_KEY}

{
  "from":    "letter@salkkamalka.com",
  "to":      ["user@email.com"],
  "subject": "[살까말까 Vol.001] 이번 주 마포구 실거래 브리핑",
  "html":    "<html>...</html>"
}
```

### Supabase 테이블 스키마 (`utils/db.py`)

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

---

## 9. 자동화 (GitHub Actions)

### 실행 스케줄 (`.github/workflows/weekly.yml`)

```yaml
on:
  schedule:
    - cron: "0 20 * * 0"   # 매주 일요일 20:00 UTC = 월요일 05:00 KST
  workflow_dispatch:        # 수동 실행 가능
    inputs:
      region:
        default: "마포구"
      test_mode:
        type: boolean
        default: false
```

| 항목 | 내용 |
|------|------|
| 자동 실행 | 매주 월요일 05:00 KST |
| 발송 목표 | 오전 07:00 KST (파이프라인 약 1~2시간) |
| 수동 실행 | GitHub Actions 탭 → workflow_dispatch |
| 테스트 모드 | `--test` 플래그 → 발송 없이 HTML 파일만 생성 |
| 결과 아티팩트 | 생성된 HTML 리포트 30일 보관 |

### GitHub Secrets 목록

| Secret 이름 | 설명 | 발급처 |
|------------|------|-------|
| `MOLIT_API_KEY` | 국토부 실거래가 API 키 | data.go.kr |
| `OPENAI_API_KEY` | OpenAI API 키 | platform.openai.com |
| `SUPABASE_URL` | Supabase 프로젝트 URL | supabase.com |
| `SUPABASE_KEY` | Supabase anon public 키 | supabase.com |
| `RESEND_API_KEY` | Resend API 키 | resend.com |
| `FROM_EMAIL` | 발신 이메일 주소 | 도메인 이메일 |
| `KAKAO_API_KEY` | 카카오맵 키 (현재 미사용) | developers.kakao.com |

---

## 10. 환경변수 및 실행 가이드

### `.env` 설정

```bash
# .env.example → .env 복사 후 실제 값 입력

# 국토부 실거래가 API (공공데이터포털 → 15126468 신청)
MOLIT_API_KEY=여기에_입력

# 카카오맵 (MVP에서는 미사용, 추후 전환 시 입력)
KAKAO_API_KEY=여기에_입력

# OpenAI
OPENAI_API_KEY=sk-여기에_입력

# Supabase
SUPABASE_URL=https://프로젝트ID.supabase.co
SUPABASE_KEY=anon_public_키

# Resend
RESEND_API_KEY=re_여기에_입력
FROM_EMAIL=letter@도메인.com
```

### 초기 세팅 순서

```bash
# 1. 저장소 클론
git clone <repo-url> && cd salkka-pipeline

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# → .env 파일 열어 API 키 입력

# 4. Supabase 테이블 생성
# Supabase 대시보드 → SQL Editor → utils/db.py 하단 스키마 실행

# 5. 테스트 실행 (발송 없이 HTML만 생성)
python main.py --region 마포구 --test
```

### 단계별 실행 명령

```bash
# 전체 파이프라인 (발송 포함)
python main.py --region 마포구

# 테스트 모드 (발송 생략)
python main.py --region 마포구 --test

# 단계별 독립 실행
python main.py --step collect   # 수집만
python main.py --step analyze   # 분석만 (수집 캐시 재사용)
python main.py --step send      # 발송만 (리포트 캐시 재사용)

# 다른 지역 실행
python main.py --region 강남구
```

### 매주 편집자가 업데이트할 항목 (`main.py` 상단)

```python
THIS_WEEK_NEWS = {
    "category": "정책 변화",          # 매주 변경
    "title":    "...",                # 이번 주 주요 뉴스 1건
    "body":     "...",
    "impact":   "...",                # 실수요자 임팩트
}

THIS_WEEK_INDICATORS = [              # 타이밍 인디케이터 5개
    {"name": "거래량 추이", "status": "...", "badge": "긍정/주의/부정/중립"},
    ...
]

THIS_WEEK_QNA = [                     # 유료 구독자 질문 2건
    {"question": "...", "answer": ""},
    ...
]

MONTHLY_COMPARE_COMPLEXES = [         # 매월 업데이트
    "마포래미안푸르지오", "공덕자이", "신공덕삼성래미안",
]
```

---

## 11. API 현황 및 제약사항

### 국토부 실거래가 API 확정

```
✅ 사용: 15126468 — 아파트 매매 실거래가 상세 자료
   URL:  https://www.data.go.kr/data/15126468/openapi.do
   특징: 더 많은 응답 필드, 상세 정보 포함

❌ 미사용: 15126469 — 아파트 매매 실거래가 자료 (일반)
   URL:  https://www.data.go.kr/data/15126469/openapi.do
   이유: 상세 자료 대비 제공 필드 적음
```

### 카카오맵 API 사용 불가 (MVP 제외 결정)

```
변경 시점: 2024년 12월 1일
변경 내용: 신규 앱의 카카오맵 API 사용 시 활성화 설정 필수
           → 이미 활성화된 앱 외 추가 앱은 앱 권한 신청 필요
           → 앱 권한 신청 = 비즈니스 인증 (사업자 등록 필요)

MVP 결정: 도로명주소 API + Haversine으로 대체
정식 전환: 개인사업자 등록 후 네이버 지도 API 사용
```

### MVP 임장 요소 대체 방안

```python
# 1단계: 주소 → 좌표 (도로명주소 API, 완전 무료)
# https://business.juso.go.kr/addrlink/openApi/apiExprn.do
GET https://business.juso.go.kr/addrlink/addrCoordApi.do
    ?confmKey={KEY}&resultType=json&keyword={주소}

# 2단계: 좌표 간 직선거리 (Haversine, API 불필요)
distance_m = haversine(lat1, lng1, lat2, lng2)

# 3단계: 도보/교통 시간 추정
walk_min    = max(1, round(distance_m / 80))
transit_min = min(int(distance_m * 1.4 / 400) + 10, 90)
```

---

## 12. 무료 vs 유료 콘텐츠 설계

| 콘텐츠 | 무료 | 스탠다드 | 프리미엄 |
|--------|------|---------|---------|
| 시장 온도계 | ✅ 기본 요약 | ✅ 동일 | ✅ 동일 |
| 주목 단지 임장 서술 | ✅ 2개 | ✅ 동일 | ✅ 관심 단지 직접 설정 |
| 타이밍 신호 | ✅ 결론만 | ✅ 동일 | ✅ 동일 |
| 이번 주 뉴스 | ✅ 1건 | ✅ 동일 | ✅ 동일 |
| 편집장 총평 | ✅ | ✅ | ✅ |
| **급매 알림** | ❌ | ✅ 최대 3건 + GPT 해설 | ✅ |
| **전세가율 위험 경보** | ❌ | ✅ 최대 2건 | ✅ |
| **단지 비교 리포트** | ❌ | ✅ 월 1회 | ✅ |
| **구독자 Q&A** | ❌ | ✅ 매주 2건 | ✅ |
| **즉시 알림** | ❌ | ❌ | ✅ 급매 발생 시 즉시 |

> **핵심 원칙**: 무료는 "알게 해주는 것", 유료는 "결정하게 해주는 것"

---

## 13. 수익화 및 사업 현황

### 플랜 구성

| 플랜 | 가격 | 발송 주기 | 핵심 제공 |
|------|------|---------|---------|
| Free | 무료 (4주) | 주 1회 | 시장 온도계, 단지 2개, 타이밍 신호, 뉴스 1건 |
| Standard | 월 9,900원 | 주 2회 | Free 전체 + 급매·전세위험·비교·Q&A |
| Premium | 월 29,000원 | 주 2회 + 즉시 알림 | Standard 전체 + 관심 단지 설정, AI Q&A 5회 |

### 유료 전환 체크리스트

아래 **4개 이상** 충족 시 유료화 시작:

- [ ] 무료 구독자 50명 이상
- [ ] 오픈율 35% 이상 (3회 평균)
- [ ] 4주 구독 유지율 80% 이상
- [ ] 자발적 답장/공유 1건 이상 발생
- [ ] 구독자가 먼저 "더 자세히 볼 수 있나요?" 질문
- [ ] 콘텐츠 품질에 스스로 만족

### 지역 확장 로드맵

| 시기 | 지역 | 조건 |
|------|------|------|
| 0~6개월 | 마포구 집중 | 파이프라인 완전 자동화 + 유료 구독자 50명 |
| 6~9개월 | 인접 지역 1개 추가 (서대문/용산) | `--region` 파라미터만 변경, 코드 재사용 |
| 9~12개월 | 서울 서북권 패키지 (3개 구) | 지역 묶음 구독 상품 출시 |
| 12개월+ | 강남권 or 수도권 확장 | B2B (부동산 중개사무소) 전환 검토 |

### 법적 준비 사항

| 항목 | 내용 | 시점 |
|------|------|------|
| 개인사업자 등록 | 홈택스, 업종코드 739909, 무료 | 유료 서비스 전 |
| 통신판매업 신고 | 정부24, 약 6,000~10,000원 | 유료 서비스 전 |
| 개인정보처리방침 | 랜딩페이지 하단 링크 | 구독 폼 오픈 전 |
| 마케팅 수신 동의 | 구독 폼에 체크박스 | 구독 폼 오픈 전 |
| 면책 문구 | 이메일 하단 필수 삽입 | 첫 발송 전 |

```
[이메일 하단 필수 문구]
본 브리핑은 정보 제공 목적이며 투자 권유가 아닙니다.
매수/매도 결정은 본인의 판단으로 하시기 바랍니다.
```

---

## 14. 향후 개발 계획

### 우선순위별 태스크

| 우선순위 | 항목 | 버전 |
|---------|------|------|
| **P0** | 도로명주소 API로 `kakao.py` 교체 | v2.1 |
| **P0** | 국토부 API 15126468 실제 연동 테스트 | v2.1 |
| **P1** | 전세가격 API 연동 (전세가율 자동 계산) | v2.2 |
| **P1** | Supabase 구독자 DB 세팅 + Resend 테스트 발송 | v2.2 |
| **P1** | 개인사업자 등록 + 랜딩페이지 오픈 | v2.3 |
| **P2** | 네이버 지도 API 전환 (실제 도보 경로) | v3.0 |
| **P2** | 구독자 Q&A 이메일 자동 수집 | v3.0 |
| **P2** | 토스페이먼츠 유료 결제 연동 | v3.1 |
| **P3** | 2번째 지역 추가 + 지역 묶음 구독 | v4.0 |
| **P3** | B2B 중개사무소 대상 상품 출시 | v4.0 |

### 즉시 실행 가능한 다음 스텝 (P0)

```bash
# 1. 도로명주소 API 키 발급
#    https://business.juso.go.kr/addrlink/openApi/apiExprn.do

# 2. kakao.py → juso.py로 교체
#    _geocode() 함수를 도로명주소 API로 재구현

# 3. 국토부 API 키 발급
#    https://www.data.go.kr/data/15126468/openapi.do
#    → "활용신청" 버튼 클릭 → 자동승인 (1~2시간)

# 4. 테스트 실행
python main.py --step collect --region 마포구 --test
```

---

*문서 버전: v2.0 | 최종 수정: 2025년 3월 | 작성 환경: Claude Code*
