"""원티드 OpenAPI 어댑터 — 신입·인턴 개발 공고 수집.

# TODO(원티드 OpenAPI 스키마 확정 후 fetch() 본체 구현)
# 원티드 공식 OpenAPI(https://openapi.wanted.jobs/)의 정확한 엔드포인트/응답
# 스키마가 아직 미확정이다. 가짜 스키마를 지어내지 말 것.
# 키 발급(WANTED_API_KEY) 후 실제 응답을 직접 보고 아래 _parse()/fetch() 를 채운다.
#   - API 문서: https://openapi.wanted.jobs/api-docs
#   - 확정해야 할 것: 검색 엔드포인트 URL, 쿼리 파라미터(키워드/페이지/경력),
#     인증 방식(Authorization 헤더 형식), 응답 JSON 의 공고 리스트 경로/필드명
#   - 그 전까지 fetch() 는 어떤 경우에도 [] 를 반환하며 파이프라인을 중단하지 않는다.
"""
from __future__ import annotations

import config
from adapters.base import BaseAdapter, today_kst
from core.schema import JobPosting, is_dev_role

# 스키마 확정 후 실제 값으로 교체할 것 (현재는 추정 placeholder).
_WANTED_API_BASE = "https://openapi.wanted.jobs"


class WantedAdapter(BaseAdapter):
    name = "원티드"

    def fetch(self) -> list:
        """신입·인턴 개발 공고를 수집해 JobPosting 리스트로 반환.

        스키마 확정 전 안전 스캐폴드: 키가 없으면 [], 키가 있어도 엔드포인트/파싱이
        미확정이라 어떤 오류든 [] 로 흡수하고 파이프라인을 절대 중단하지 않는다.
        """
        if not config.WANTED_API_KEY:
            return []

        results: list[JobPosting] = []
        try:
            # ── 호출 골격(추정) — 스키마 확정 후 실제 엔드포인트/파라미터로 교체 ──
            # 인증 헤더 형식(Bearer 여부 등)은 미확정이므로 키 발급 후 확인할 것.
            headers = {"Authorization": f"Bearer {config.WANTED_API_KEY}"}
            with self.client() as client:
                for keyword in config.SEARCH_KEYWORDS:
                    # TODO: 실제 검색 엔드포인트/파라미터 확정 후 구현.
                    #   resp = client.get(
                    #       f"{_WANTED_API_BASE}/<검색경로>",
                    #       headers=headers,
                    #       params={"query": keyword, "limit": config.PAGE_SIZE},
                    #   )
                    #   resp.raise_for_status()
                    #   results.extend(self._parse(resp.json(), keyword))
                    _ = (client, headers, keyword)  # 미사용 경고 억제 (placeholder)
        except Exception as exc:  # noqa: BLE001 — 어떤 오류든 흡수, 파이프라인 보호
            print(f"[원티드] 수집 실패(스키마 미확정/네트워크) — 빈 결과 반환: {exc}")
            return []

        return results

    def _parse(self, payload: dict, keyword: str) -> list:
        """원티드 응답 JSON → JobPosting 리스트.

        # TODO: 스키마 확정 후 payload 의 실제 필드 경로로 매핑할 것.
        아래는 채워 넣기 쉽도록 남긴 생성 예시 형태(실값 아님).
        """
        items = payload.get("data", [])  # TODO: 실제 공고 리스트 경로로 교체
        out: list[JobPosting] = []
        for item in items:
            title = item.get("title", "")
            company = item.get("company", "")
            # 개발 직군만 통과 (제목/회사 기준 1차 필터)
            if not is_dev_role(f"{title} {company}"):
                continue
            out.append(
                JobPosting(
                    source="원티드",
                    company=company,
                    title=title,
                    url=item.get("url", ""),
                    employment_type="신입",        # 기본값 (수집 대상이 신입·인턴)
                    location=item.get("location", ""),
                    deadline=item.get("deadline"),  # 'YYYY-MM-DD' or None
                    keyword=keyword,
                    collected_date=today_kst(),
                )
            )
        return out
