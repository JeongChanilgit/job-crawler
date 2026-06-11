"""노션 적재 + 중복 제거.

notion-client SDK 버전에 따라 databases.query 가 사라지는 문제를 피하려고
raw REST API(httpx, Notion-Version 2022-06-28)를 직접 호출한다 — 검증된 안정 경로.
DB 에 이미 있는 '링크' 값을 한 번 읽어와서 같은 링크는 다시 넣지 않는다(증분 적재).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from core.schema import JobPosting

KST = timezone(timedelta(hours=9))
NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"


class NotionWriter:
    def __init__(self, token: str, database_id: str):
        self.database_id = database_id
        self.http = httpx.Client(
            base_url=API,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self._existing_urls: set[str] | None = None

    def _load_existing_urls(self) -> set[str]:
        urls: set[str] = set()
        cursor = None
        while True:
            payload: dict = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor
            r = self.http.post(f"/databases/{self.database_id}/query", json=payload)
            r.raise_for_status()
            data = r.json()
            for page in data.get("results", []):
                u = page.get("properties", {}).get("링크", {}).get("url")
                if u:
                    urls.add(u.strip().lower())
            if data.get("has_more"):
                cursor = data.get("next_cursor")
            else:
                break
        return urls

    def _to_properties(self, job: JobPosting) -> dict:
        today = datetime.now(KST).strftime("%Y-%m-%d")
        props: dict = {
            "포지션": {"title": [{"text": {"content": (job.title or "(제목 없음)")[:200]}}]},
            "회사": {"rich_text": [{"text": {"content": (job.company or "")[:200]}}]},
            "출처": {"select": {"name": job.source}},
            "고용형태": {"select": {"name": job.employment_type}},
            "직군": {"select": {"name": job.job_category}},
            "수집일": {"date": {"start": job.collected_date or today}},
        }
        if job.location:
            props["지역"] = {"rich_text": [{"text": {"content": job.location[:200]}}]}
        if job.url:
            props["링크"] = {"url": job.url}
        if job.deadline:
            props["마감일"] = {"date": {"start": job.deadline}}
        if job.keyword:
            props["키워드"] = {"rich_text": [{"text": {"content": job.keyword[:100]}}]}
        return props

    def upsert_many(self, jobs: list[JobPosting]) -> int:
        if self._existing_urls is None:
            self._existing_urls = self._load_existing_urls()
        added = 0
        for job in jobs:
            key = (job.url or "").strip().lower()
            if key and key in self._existing_urls:
                continue
            try:
                r = self.http.post("/pages", json={
                    "parent": {"database_id": self.database_id},
                    "properties": self._to_properties(job),
                })
                r.raise_for_status()
                if key:
                    self._existing_urls.add(key)
                added += 1
            except Exception as e:
                print(f"[노션] 적재 실패 ({job.company} / {job.title}): {e}")
        return added
