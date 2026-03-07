# CHANGELOG v3.0 — 예산대×권역 비교 + 프리미엄 유도 개편

## 변경 일자: 2026-03-07
## 근거: docs/feedback2_20260307.txt

---

## 1. 뉴스레터 구조 개편: 단일 지역 → 예산대×권역 비교

### 변경 파일
- `reporter/builder.py` — 전면 리빌드
- `main.py` — BUDGET_TIERS, COMPARISON_REGIONS 추가
- `analyzer/gpt.py` — `generate_region_comparison()` 추가
- `prompts/templates.py` — REGION_COMPARISON_SYSTEM/USER 추가

### 변경 내용
- 헤더 타이틀: "이번 주 테마: {예산}으로 {권역} 어디가 나을까?"
- 2~3개 지역 비교 테이블 (84㎡ 평균가, 전세가율, 거래량, 강남 접근성, 학군, 추천 점수)
- 추천 지역 1곳 강조 (배경색 + 추천 배지)
- 예산대 3구간 (3~4억 / 5~6억 / 7억 이상) 주차별 순환 발행
- 이메일 제목도 비교 형식으로 변경

---

## 2. "데이터 부족" 표현 전면 제거

### 변경 파일
- `prompts/templates.py` — 프롬프트에 금지 규칙 추가
- `analyzer/gpt.py` — 기본값을 빈 문자열로 변경
- `collector/naver_land.py` — "수집 실패" → 빈 문자열
- `collector/supply.py` — "수집 중", "데이터 부족" → 빈 문자열
- `premium/detector.py` — "데이터 부족" → 빈 문자열
- `main.py` — 위치 정보 실패 시 빈 문자열
- `reporter/builder.py` — 빈 섹션은 통째로 생략

### 규칙
- 확보된 데이터가 없는 항목은 본문에서 아예 제거
- "정보 없음"을 드러내는 모든 문장 삭제
- 데이터가 부족한 섹션 전체를 생략하고 확보된 내용만 발행

---

## 3. AI 느낌 제거 → 자연스러운 산문

### 변경 파일
- `prompts/templates.py`

### 변경 내용
- COMPLEX_DESCRIPTION_SYSTEM: 번호 나열(1)~4)) 금지, 산문 형태 필수
- EDITOR_SUMMARY_SYSTEM: 1~2문장 압축, "화이팅!" 류 마무리 금지
- 각 단지 서술 시 강조점과 순서를 달리하여 반복감 제거
- 출력 형식도 순서 고정이 아닌 "이 단지만의 특징부터 시작" 지시

---

## 4. 다음 주 주제 투표 섹션 추가

### 변경 파일
- `reporter/builder.py`

### 변경 내용
- 뉴스레터 하단(푸터 직전)에 투표 섹션 삽입
- 권역 선택지 3개 + 예산대 선택지 3개 버튼
- 투표 결과 중 가장 많이 선택된 조합이 다음 주 주제로 반영
- TODO: /api/vote POST 엔드포인트 구현, 중복 투표 방지, 현황 표시

---

## 5. 프리미엄 유도 장치 추가

### 변경 파일
- `reporter/builder.py`
- `main.py`

### 변경 내용
- **급매 미리보기**: 무료 1건만 공개, 나머지 블러 처리 + CTA 버튼
- **맞춤 분석 유도**: "내 상황을 알려주시면 맞춤 분석을 보내드립니다" CTA
- **관심 단지 알림**: "관심 단지 등록 시 급매·가격 변동 알림" CTA
