import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────
MOLIT_API_KEY    = os.getenv("MOLIT_API_KEY")       # 국토부 실거래가 (15126468)
JUSO_API_KEY     = os.getenv("JUSO_API_KEY")        # 도로명주소 API (행안부)
KAKAO_API_KEY    = os.getenv("KAKAO_API_KEY")       # 카카오맵 (현재 미사용, v3 전환용)
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")      # OpenAI GPT
SUPABASE_URL     = os.getenv("SUPABASE_URL")        # Supabase
SUPABASE_KEY     = os.getenv("SUPABASE_KEY")        # Supabase
RESEND_API_KEY   = os.getenv("RESEND_API_KEY")      # Resend 이메일
FROM_EMAIL       = os.getenv("FROM_EMAIL", "letter@salkkamalka.com")

# ── GPT 설정 ──────────────────────────────────────
# 비용 전략: 단순 정리는 mini, 핵심 서술은 4o
GPT_MODEL_MAIN   = "gpt-4o-mini"    # 데이터 정리, 타이밍 신호
GPT_MODEL_WRITER = "gpt-4o"         # 임장 서술, 편집장 총평, 유료 분석 (품질 중요)
GPT_MAX_TOKENS   = 1500             # v2.3: 분석 깊이 강화로 토큰 확대
GPT_TEMPERATURE  = 0.7              # 약간의 창의성 허용

# ── 서비스 설정 ───────────────────────────────────
TARGET_REGION    = "마포구"
TARGET_CITY      = "서울특별시"
NEWSLETTER_TITLE = "살까말까"

# 분석할 단지 수 (비용 조절 가능)
MAX_COMPLEXES    = 2                # 주목 단지 최대 2개

# 임장 요소 검색 반경 (미터)
RADIUS_SCHOOL    = 1000             # 학교 검색 반경
RADIUS_SUBWAY    = 1500             # 지하철 검색 반경
RADIUS_MART      = 1500             # 마트 검색 반경 (v2.2)
RADIUS_ACADEMY   = 500              # 학원 검색 반경 (v2.2)

# ── CTA 링크 (v3.0) ────────────────────────────────
# 구글 폼 또는 자체 페이지 URL (생성 후 여기에 입력)
CTA_PREMIUM_URL     = os.getenv("CTA_PREMIUM_URL", "https://salkkamalka.com/#pricing")
CTA_CUSTOM_ANALYSIS = os.getenv("CTA_CUSTOM_ANALYSIS", "https://salkkamalka.com/#pricing")
CTA_WATCHLIST_URL   = os.getenv("CTA_WATCHLIST_URL", "https://salkkamalka.com/#pricing")
CTA_VOTE_URL        = os.getenv("CTA_VOTE_URL", "https://salkkamalka.com/#pricing")
