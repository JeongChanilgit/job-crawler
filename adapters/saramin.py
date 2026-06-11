"""사람인 오픈 API 어댑터.

사람인 채용정보 검색 API(https://oapi.saramin.co.kr/job-search)로
신입 개발 공고를 수집해 JobPosting 리스트로 반환한다.
"""
from __future__ import annotations

import time
from datetime import datetime

import config
from adapters.base import BaseAdapter, today_kst
from core.schema import JobPosting, is_dev_role, normalize_employment

BASE_URL = "https://oapi.saramin.co.kr/job-search"


def _get(d, *keys, default=None):
    """중첩 dict 를 .get 체이닝으로 안전 추출. 중간이 dict 가 아니면 default."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _to_date(raw) -> str | None:
    """'YYYY-MM-DD' 문자열은 앞 10자만, epoch 초(int/숫자문자열)는 날짜로 변환."""
    if raw is None or raw == "":
        return None
    # epoch 초로 들어오는 경우
    try:
        ts = int(raw)
        # 마감일이 epoch 초로 오면 KST 날짜로 변환
        return datetime.utcfromtimestamp(ts + 9 * 3600).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    s = str(raw)
    return s[:10] if len(s) >= 10 else s


class SaraminAdapter(BaseAdapter):
    name = "사람인"

    def fetch(self) -> list:
        if not config.SARAMIN_ACCESS_KEY:
            print("[사람인] SARAMIN_ACCESS_KEY 미설정 — 건너뜀")
            return []

        results: list[JobPosting] = []
        with self.client() as client:
            for keyword in config.SEARCH_KEYWORDS:
                for start in range(config.MAX_PAGES_PER_KEYWORD):
                    try:
                        resp = client.get(
                            BASE_URL,
                            params={
                                "access-key": config.SARAMIN_ACCESS_KEY,
                                "keywords": keyword,
                                "experience-level": 1,  # 신입
                                "start": start,
                                "count": min(config.PAGE_SIZE, 110),
                                "fields": "expiration-date,posting-date",
                            },
                            headers={"Accept": "application/json"},
                        )
                        resp.raise_for_status()
                        data = resp.json()
                    except Exception as e:
                        print(f"[사람인] 호출 실패 keyword={keyword} start={start}: {e}")
                        continue

                    jobs = _get(data, "jobs", "job", default=[])
                    if not isinstance(jobs, list):
                        jobs = [jobs] if jobs else []
                    if not jobs:
                        break  # 더 이상 결과 없음 → 다음 키워드

                    for job in jobs:
                        try:
                            if not isinstance(job, dict):
                                continue
                            if str(job.get("active", "1")) != "1":
                                continue

                            title = _get(job, "position", "title", default="") or ""
                            if not is_dev_role(title):
                                continue

                            company = _get(job, "company", "detail", "name", default="") or ""
                            location = _get(job, "position", "location", "name", default="") or ""
                            exp_name = _get(job, "position", "experience-level", "name", default="") or ""
                            url = job.get("url", "") or ""
                            deadline = _to_date(
                                job.get("expiration-date") or job.get("expiration-timestamp")
                            )

                            results.append(
                                JobPosting(
                                    source=self.name,
                                    company=company,
                                    title=title,
                                    url=url,
                                    employment_type=normalize_employment(exp_name) or "신입",
                                    location=location,
                                    deadline=deadline,
                                    keyword=keyword,
                                    collected_date=today_kst(),
                                )
                            )
                        except Exception as e:
                            print(f"[사람인] 항목 파싱 실패: {e}")
                            continue

                time.sleep(0.5)

        print(f"[사람인] 수집 {len(results)}건")
        return results
