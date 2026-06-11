"""정규화된 채용공고 스키마 + 직군 분류 / 신입·인턴 필터 헬퍼.

노션 '직군'·'고용형태' SELECT 옵션과 1:1 대응되도록 매핑한다.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

# 노션 '직군' SELECT 옵션
CATEGORIES = ["백엔드", "프론트엔드", "풀스택", "모바일", "데이터", "DevOps/인프라", "AI/ML", "기타"]

# (직군, 매칭 토큰) — 위에서부터 먼저 매칭되는 것을 채택
_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("풀스택", ("풀스택", "full-stack", "fullstack")),
    ("DevOps/인프라", ("devops", "sre", "인프라", "쿠버네티스", "kubernetes",
                       "클라우드 엔지니어", "platform engineer", "시스템 엔지니어")),
    ("데이터", ("데이터 엔지니어", "data engineer", "빅데이터", "data scientist",
              "데이터 분석", "analytics")),
    ("AI/ML", ("머신러닝", "machine learning", "딥러닝", "ml engineer",
              "ai 엔지니어", "ai engineer", "인공지능")),
    ("모바일", ("안드로이드", "android", "ios", "flutter", "react native", "모바일")),
    ("프론트엔드", ("프론트엔드", "프론트 엔드", "front-end", "frontend",
                 "react", "vue", "웹 퍼블", "웹퍼블")),
    ("백엔드", ("백엔드", "백 엔드", "back-end", "backend", "서버 개발", "서버개발",
              "java", "spring", "kotlin", "node", "django", "golang", "go 개발")),
]

# 신입/인턴 판별 토큰
_ENTRY_TOKENS = ("신입", "인턴", "수습", "체험형", "경력무관", "경력 무관", "무관")
# 명백한 경력직 신호 (신입 신호가 없을 때만 제외 근거로 사용)
_SENIOR_TOKENS = ("년차", "년 이상", "시니어", "senior", " lead", "팀장", "수석", "책임")

# 개발 직군 판별 (하나라도 걸려야 개발 공고로 간주)
_DEV_HINTS = ("개발", "developer", "engineer", "엔지니어", "프로그래머", "백엔드", "프론트",
              "서버", "ios", "android", "데이터", "devops", "sre", "ml", " ai ",
              "소프트웨어", "software", "웹개발", "앱개발", "spring", "react")


def classify_category(text: str) -> str:
    t = (text or "").lower()
    for cat, tokens in _CATEGORY_RULES:
        if any(tok in t for tok in tokens):
            return cat
    return "기타"


def is_dev_role(text: str) -> bool:
    t = f" {(text or '').lower()} "
    return any(h in t for h in _DEV_HINTS)


def is_entry_level(text: str) -> bool:
    """신입/인턴으로 볼 수 있으면 True.

    API 의 경력 필드로 이미 신입을 걸렀다면 빈 문자열을 넘겨 통과시켜도 된다.
    """
    t = (text or "").lower()
    if any(tok in t for tok in _ENTRY_TOKENS):
        return True
    if any(tok in t for tok in _SENIOR_TOKENS):
        return False
    return True  # 신호가 전혀 없으면 보수적으로 통과 (API 단 필터 신뢰)


def normalize_employment(raw: str) -> str:
    """노션 '고용형태' SELECT 옵션으로 매핑."""
    t = (raw or "").lower()
    if "인턴" in t or "체험형" in t or "intern" in t:
        return "인턴"
    if "신입" in t and "경력" in t:
        return "신입/경력"
    if "신입" in t:
        return "신입"
    if "무관" in t:
        return "경력무관"
    return "신입"  # 기본값 (수집 대상이 신입·인턴)


@dataclass
class JobPosting:
    source: str                   # 출처 (워크넷/사람인/원티드/공공기관/인크루트/잡코리아 ...)
    company: str
    title: str                    # 포지션
    url: str
    employment_type: str = "신입"  # 인턴/신입/신입/경력/경력무관
    job_category: str = "기타"     # 직군
    location: str = ""
    deadline: str | None = None   # 'YYYY-MM-DD' or None
    keyword: str = ""             # 매칭된 검색 키워드
    collected_date: str = ""      # 'YYYY-MM-DD'

    def __post_init__(self):
        if not self.job_category or self.job_category == "기타":
            self.job_category = classify_category(f"{self.title} {self.keyword}")
        self.employment_type = normalize_employment(self.employment_type)

    @property
    def dedup_key(self) -> str:
        basis = (self.url or f"{self.company}|{self.title}").strip().lower()
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()
