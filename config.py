"""채용공고 크롤러 전역 설정.

수집 대상: 개발 직군 전체 × 신입·인턴.
사이트 토글/키워드/한도를 여기서 조정한다.
"""
from __future__ import annotations

import os

# --- 수집 필터 ---
# 개발 직군 전반을 폭넓게 잡기 위한 검색 키워드.
# 각 어댑터는 이 키워드로 검색한 뒤, 결과를 신입·인턴 + 개발직군으로 후필터링한다.
SEARCH_KEYWORDS = [
    "개발자",
    "백엔드",
    "프론트엔드",
    "서버 개발",
    "안드로이드",
    "iOS",
    "데이터 엔지니어",
]

# 사이트별 활성화 토글 (Phase 단계적 적용)
ENABLED_SITES = {
    # Phase 1 — 공식 API (합법·안정)
    "worknet": True,     # 고용24/워크넷 (data.go.kr)
    "saramin": True,     # 사람인 오픈 API
    "wanted": True,      # 원티드 OpenAPI
    "publicgov": True,   # 공공기관 채용 (data.go.kr) — 나라일터/alio 계열
    # Phase 2 — 정적 스크래핑 (GitHub Actions 에서 동작 가능성 높음)
    "incruit": False,    # 인크루트 (정적 HTML) — 셀렉터 검증 후 활성화 (API 사이트 먼저 테스트)
    "jobkorea": False,   # 잡코리아 (정적, 레이트리밋 주의) — 안정화 후 활성화
    # Phase 3 — JS 렌더 (Playwright, 로컬 전용 권장)
    "jasoseol": False,   # 자소설닷컴
    "linkareer": False,  # 링커리어
    "catch": False,      # 캐치 (catch.co.kr, 대기업·공기업·인턴) — 구조 검증 후 활성화
}

# 사이트당 호출 상한 (과도한 요청 방지)
MAX_PAGES_PER_KEYWORD = 3
PAGE_SIZE = 50

# --- 시크릿 (환경변수 / GitHub Secrets) ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
DATA_GO_KR_KEY = os.getenv("DATA_GO_KR_KEY", "")
SARAMIN_ACCESS_KEY = os.getenv("SARAMIN_ACCESS_KEY", "")
WANTED_API_KEY = os.getenv("WANTED_API_KEY", "")

# --- 요청 공통 ---
HTTP_TIMEOUT = 20.0
USER_AGENT = "Mozilla/5.0 (compatible; JobCrawler/1.0; personal-use)"
