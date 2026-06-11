"""잡코리아 정적 HTML 스크래퍼 어댑터.

채용 검색 결과 페이지(정적 HTML)를 GET → BeautifulSoup(lxml)로 파싱해
신입·인턴 개발 공고를 JobPosting 리스트로 반환한다.

config 에서 기본 비활성(ENABLED_SITES["jobkorea"] = False). 안정화 후 활성화.

------------------------------------------------------------------------------
TODO(검색 URL/페이지네이션 검증 필요):
  잡코리아 검색 URL 패턴이 미확정이다. 아래는 후보이며 실제 파라미터·
  페이지네이션 동작을 브라우저/네트워크 탭으로 확인해야 한다.
    https://www.jobkorea.co.kr/Search/?stext=<urlencode(keyword)>&tabType=recruit&Page_No=<n>
  - stext: 검색어 (urlencode)
  - tabType=recruit: 채용 탭
  - Page_No: 1-base 페이지 번호 (실제 파라미터명 확인 필요)
  일부 결과가 JS 렌더/AJAX 로 채워질 수 있어, 정적 HTML 만으로는 카드가
  비어 나올 수 있다. 그 경우 Phase 3(Playwright) 전환을 고려.

TODO(셀렉터 추정 — 실 DOM 검증 필요):
  아래 카드/필드 셀렉터는 모두 추정값이다. 실제 DOM 구조를 확인하고
  CARD_SELECTORS / 각 추출 함수의 셀렉터를 보정해야 한다.
------------------------------------------------------------------------------
"""
from __future__ import annotations

import logging
import time
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

import config
from adapters.base import BaseAdapter, today_kst
from core.schema import JobPosting, is_dev_role

log = logging.getLogger(__name__)

# 절대 URL 보정용 베이스
_BASE_URL = "https://www.jobkorea.co.kr"

# TODO(실 DOM 검증 필요): 공고 카드 컨테이너 후보 셀렉터. 위에서부터 먼저 잡히는 것 사용.
_CARD_SELECTORS = [
    "div.list-post",          # 추정: 검색 결과 리스트 아이템
    "li.list-post",
    "div.recruit-info li",
    "tr.devloopArea",
]


def _search_url(keyword: str, page: int) -> str:
    # TODO(검증 필요): 파라미터명/페이지네이션 실제 동작 확인.
    return (
        f"{_BASE_URL}/Search/"
        f"?stext={quote(keyword)}&tabType=recruit&Page_No={page}"
    )


def _text(node) -> str:
    return node.get_text(strip=True) if node else ""


def _select_first(card, selectors: list[str]):
    """추정 셀렉터를 순서대로 시도해 첫 매칭 노드 반환 (없으면 None)."""
    for sel in selectors:
        try:
            found = card.select_one(sel)
        except Exception:
            found = None
        if found:
            return found
    return None


class JobkoreaAdapter(BaseAdapter):
    name = "잡코리아"

    def fetch(self) -> list:
        results: list[JobPosting] = []
        try:
            with self.client() as client:
                for keyword in config.SEARCH_KEYWORDS:
                    for page in range(1, config.MAX_PAGES_PER_KEYWORD + 1):
                        results.extend(self._fetch_page(client, keyword, page))
                        # 매너: 보수적 레이트리밋 (봇 차단 중간 수준)
                        time.sleep(2.0)
        except Exception as e:  # 어떤 경우에도 죽지 않는다
            log.warning("[%s] fetch 중단: %s", self.name, e)
        return results

    def _fetch_page(self, client, keyword: str, page: int) -> list:
        url = _search_url(keyword, page)
        try:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            log.warning("[%s] 요청 실패 (kw=%s p=%s): %s", self.name, keyword, page, e)
            return []

        try:
            soup = BeautifulSoup(html, "lxml")
            cards = self._find_cards(soup)
        except Exception as e:
            log.warning("[%s] 파싱 실패 (kw=%s p=%s): %s", self.name, keyword, page, e)
            return []

        items: list[JobPosting] = []
        for card in cards:
            try:
                posting = self._parse_card(card, keyword)
            except Exception as e:
                log.debug("[%s] 카드 파싱 스킵: %s", self.name, e)
                continue
            if posting is not None:
                items.append(posting)
        return items

    def _find_cards(self, soup) -> list:
        for sel in _CARD_SELECTORS:
            try:
                found = soup.select(sel)
            except Exception:
                found = []
            if found:
                return found
        return []  # 못 찾으면 빈 리스트 (크래시 금지)

    def _parse_card(self, card, keyword: str):
        # --- 포지션/링크 ---
        # TODO(실 DOM 검증 필요): 제목 링크 셀렉터 추정.
        title_node = _select_first(card, [
            "a.title",
            "a.link-normal",
            "div.post-list-info a.title",
            "a[href*='/Recruit/']",
        ])
        title = _text(title_node)
        if not title:
            return None

        # 필터: 개발 직군만
        if not is_dev_role(title):
            return None

        href = title_node.get("href", "") if title_node else ""
        url = urljoin(_BASE_URL, href) if href else ""

        # --- 회사 ---
        # TODO(실 DOM 검증 필요): 회사명 셀렉터 추정.
        company_node = _select_first(card, [
            "a.name",
            "a.coName",
            "div.post-list-corp a",
            "span.corp",
        ])
        company = _text(company_node)

        # --- 지역 ---
        # TODO(실 DOM 검증 필요): 지역 셀렉터 추정.
        location_node = _select_first(card, [
            "span.loc",
            "p.option span.loc",
            "div.post-list-info span.loc",
        ])
        location = _text(location_node)

        # --- 마감 ---
        # TODO(실 DOM 검증 필요): 마감일 셀렉터 추정. 'YYYY-MM-DD' 정규화는 후속.
        deadline_node = _select_first(card, [
            "span.date",
            "span.day",
            "p.date span",
        ])
        deadline = _text(deadline_node) or None

        return JobPosting(
            source=self.name,
            company=company,
            title=title,
            url=url,
            employment_type="신입",
            location=location,
            deadline=deadline,
            keyword=keyword,
            collected_date=today_kst(),
        )
