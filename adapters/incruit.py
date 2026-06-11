"""인크루트 정적 HTML 스크래퍼 어댑터.

인크루트 채용 검색 결과 페이지(정적 HTML)를 GET → BeautifulSoup 로 파싱해
신입·인턴 개발 공고를 JobPosting 리스트로 반환한다.

────────────────────────────────────────────────────────────────────────
TODO(검색 URL 미확정): 아래 SEARCH_URL_TMPL 은 추정값이다. 실제 인크루트
  검색 엔드포인트·파라미터·페이지네이션 방식은 사이트를 직접 확인해 검증해야 한다.
  후보 패턴:
    https://search.incruit.com/list/search.asp?col=job&kw=<urlencode(keyword)>&page=<n>
  - 신입 필터 파라미터(예: 경력 구분 ?cl= 등)도 확인 후 URL 에 반영하면
    is_dev_role/is_entry 후필터 부하를 줄일 수 있다. (TODO: 신입 필터 파라미터 확정)
TODO(셀렉터 미검증): _CARD_SELECTOR 등 모든 CSS 셀렉터는 추정값이다.
  실제 DOM 을 확인해 셀렉터를 검증/수정해야 한다. 셀렉터가 안 맞으면
  카드를 못 찾고 빈 리스트를 반환할 뿐 크래시하지는 않는다.
────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import logging
import time
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

import config
from adapters.base import BaseAdapter, today_kst
from core.schema import JobPosting, is_dev_role

logger = logging.getLogger(__name__)

# TODO(검증 필요): 실제 검색 엔드포인트/파라미터 확인 후 수정.
# kw=<urlencode(keyword)>, page=<n> 는 자리표시자 기준 추정.
_SEARCH_BASE = "https://search.incruit.com/list/search.asp"
_SITE_BASE = "https://www.incruit.com/"

# TODO(셀렉터 검증 필요): 아래 셀렉터 전부 추정 — 실제 DOM 으로 검증/수정.
# 공고 카드 컨테이너 후보 셀렉터들 (위에서부터 시도, 먼저 걸리는 것 채택).
_CARD_SELECTORS = [
    "div.c_col",          # 추정: 검색결과 리스트 아이템
    "li.c_row",           # 추정
    "div.jobcard",        # 추정
]
# 카드 내부 필드 셀렉터 후보 (각각 위에서부터 먼저 잡히는 것 사용).
_COMPANY_SELECTORS = ["a.cpname", "span.cpname", ".company a", ".company"]
_TITLE_SELECTORS = ["a.cl_top", "a.jobtit", ".cell_mid .job a", ".title a", "h2 a"]
_LOCATION_SELECTORS = ["span.cl_md", ".area", ".region", ".cell_md .work_place"]
_DEADLINE_SELECTORS = ["span.cl_btn", ".date", ".deadline", ".cell_last .date"]


def _first_text(node, selectors: list[str]) -> str:
    """node 안에서 selectors 를 순서대로 시도해 첫 텍스트를 반환 (없으면 '')."""
    for sel in selectors:
        try:
            el = node.select_one(sel)
        except Exception:
            el = None
        if el is not None:
            txt = el.get_text(strip=True)
            if txt:
                return txt
    return ""


def _first_link(node, selectors: list[str]) -> str:
    """node 안에서 selectors 를 순서대로 시도해 첫 href 를 반환 (없으면 '')."""
    for sel in selectors:
        try:
            el = node.select_one(sel)
        except Exception:
            el = None
        if el is not None and el.has_attr("href"):
            href = (el.get("href") or "").strip()
            if href:
                return href
    return ""


class IncruitAdapter(BaseAdapter):
    name = "인크루트"

    def _search_url(self, keyword: str, page: int) -> str:
        # TODO(검증 필요): 파라미터 이름/페이지네이션 방식 실제 확인 후 수정.
        qs = urlencode({"col": "job", "kw": keyword, "page": page})
        return f"{_SEARCH_BASE}?{qs}"

    def _parse_cards(self, soup: BeautifulSoup) -> list:
        """가장 먼저 매칭되는 카드 셀렉터로 카드 노드 리스트 반환 (없으면 [])."""
        for sel in _CARD_SELECTORS:
            try:
                cards = soup.select(sel)
            except Exception:
                cards = []
            if cards:
                return cards
        return []

    def _parse_card(self, card, keyword: str, collected: str) -> JobPosting | None:
        """카드 1개 → JobPosting. 추출 실패/필터 탈락 시 None."""
        title = _first_text(card, _TITLE_SELECTORS)
        if not title or not is_dev_role(title):
            return None

        company = _first_text(card, _COMPANY_SELECTORS)
        location = _first_text(card, _LOCATION_SELECTORS)
        deadline_raw = _first_text(card, _DEADLINE_SELECTORS)
        deadline = deadline_raw or None  # TODO(정규화): 'YYYY-MM-DD' 변환 — DOM 확인 후

        href = _first_link(card, _TITLE_SELECTORS)
        url = urljoin(_SITE_BASE, href) if href else ""

        return JobPosting(
            source=self.name,
            company=company,
            title=title,
            url=url,
            employment_type="신입",  # TODO: 검색 시 신입 필터 반영되면 그대로 신뢰
            location=location,
            deadline=deadline,
            keyword=keyword,
            collected_date=collected,
        )

    def _fetch_page(self, client, keyword: str, page: int, collected: str) -> list:
        """검색 1페이지 수집. 요청/파싱 실패는 로그만 남기고 [] 반환 (죽지 않음)."""
        url = self._search_url(keyword, page)
        try:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:  # 네트워크/HTTP 오류
            logger.warning("[인크루트] GET 실패 kw=%r page=%d: %s", keyword, page, e)
            return []

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception as e:  # 파서 오류
            logger.warning("[인크루트] 파싱 실패 kw=%r page=%d: %s", keyword, page, e)
            return []

        cards = self._parse_cards(soup)
        if not cards:
            # TODO(셀렉터 검증): 카드를 못 찾으면 셀렉터 불일치 가능성 — 빈 리스트 반환.
            logger.info("[인크루트] 카드 없음 kw=%r page=%d (셀렉터 검증 필요)", keyword, page)
            return []

        results: list = []
        for card in cards:
            try:
                job = self._parse_card(card, keyword, collected)
            except Exception as e:  # 카드 단위 추출 오류는 건너뜀
                logger.debug("[인크루트] 카드 파싱 건너뜀 kw=%r: %s", keyword, e)
                continue
            if job is not None:
                results.append(job)
        return results

    def fetch(self) -> list:
        collected = today_kst()
        results: list = []
        try:
            with self.client() as client:
                for keyword in config.SEARCH_KEYWORDS:
                    for page in range(1, config.MAX_PAGES_PER_KEYWORD + 1):
                        page_jobs = self._fetch_page(client, keyword, page, collected)
                        results.extend(page_jobs)
                        # 매너: 키워드/페이지 사이 레이트리밋 존중.
                        time.sleep(1.0)
        except Exception as e:  # 클라이언트 생성 등 치명 오류도 어댑터는 죽지 않게
            logger.error("[인크루트] fetch 중단: %s", e)

        logger.info("[인크루트] 수집 완료: %d건", len(results))
        return results
