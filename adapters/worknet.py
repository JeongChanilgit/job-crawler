"""고용24/워크넷 채용정보 어댑터 (공공데이터포털 Open API).

신입(career='N') × 개발 직군 공고를 검색해 JobPosting 리스트로 반환한다.

TODO: 파라미터/응답 태그명은 공식 가이드 기준으로 미세조정이 필요할 수 있다.
      (https://www.data.go.kr/data/3038225/openapi.do — wantedApi.do)
      현재 추정: 항목 태그 <wanted>, 필드 <company>/<title>/<region>/<closeDt>/<wantedInfoUrl>.
"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET

import config
from adapters.base import BaseAdapter, today_kst
from core.schema import JobPosting, is_dev_role

BASE_URL = "http://openapi.work.go.kr/opi/opi/opia/wantedApi.do"


def _text(node, tag: str) -> str:
    """자식 태그 텍스트를 방어적으로 추출. 없으면 빈 문자열."""
    if node is None:
        return ""
    child = node.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _parse_deadline(raw: str) -> str | None:
    """'YYYYMMDD' -> 'YYYY-MM-DD'. '채용시까지'/공란이면 None."""
    s = (raw or "").strip()
    if not s or "채용시까지" in s:
        return None
    digits = s.replace("-", "").replace(".", "")
    if len(digits) == 8 and digits.isdigit():
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return None


class WorknetAdapter(BaseAdapter):
    name = "워크넷"

    def fetch(self) -> list:
        if not config.DATA_GO_KR_KEY:
            print("[워크넷] DATA_GO_KR_KEY 미설정 — 건너뜀")
            return []

        results: list[JobPosting] = []
        display = min(config.PAGE_SIZE, 100)

        with self.client() as client:
            for keyword in config.SEARCH_KEYWORDS:
                for page in range(1, config.MAX_PAGES_PER_KEYWORD + 1):
                    params = {
                        "authKey": config.DATA_GO_KR_KEY,
                        "callTp": "L",
                        "returnType": "XML",
                        "startPage": page,
                        "display": display,
                        "keyword": keyword,
                        "career": "N",  # 신입
                    }
                    try:
                        resp = client.get(BASE_URL, params=params)
                        resp.raise_for_status()
                        root = ET.fromstring(resp.text)
                    except Exception as e:  # noqa: BLE001
                        print(f"[워크넷] '{keyword}' p{page} 호출/파싱 실패: {e}")
                        continue

                    items = root.findall(".//wanted")
                    for item in items:
                        try:
                            title = _text(item, "title")
                            if not is_dev_role(title):
                                continue
                            company = _text(item, "company")
                            location = _text(item, "region")
                            deadline = _parse_deadline(_text(item, "closeDt"))
                            url = _text(item, "wantedInfoUrl")
                            results.append(
                                JobPosting(
                                    source="워크넷",
                                    company=company,
                                    title=title,
                                    url=url,
                                    employment_type="신입",
                                    location=location,
                                    deadline=deadline,
                                    keyword=keyword,
                                    collected_date=today_kst(),
                                )
                            )
                        except Exception as e:  # noqa: BLE001
                            print(f"[워크넷] 항목 파싱 건너뜀: {e}")
                            continue

                time.sleep(0.5)  # 키워드 호출 사이 예의상 간격

        print(f"[워크넷] 수집 {len(results)}건")
        return results
