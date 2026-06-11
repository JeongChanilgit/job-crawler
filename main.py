"""채용공고 크롤러 엔트리포인트.

각 어댑터에서 신입·인턴 개발 공고 수집 → 중복 제거 → 노션 적재.
실행: `python main.py` (로컬은 .env, GitHub Actions 는 Secrets 사용)
"""
from __future__ import annotations

import sys
import traceback

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")  # 스크립트 옆 .env (cwd 무관). Actions 에선 파일 없어 Secrets 사용

import config
from core.notion_writer import NotionWriter
from core.schema import JobPosting


def build_adapters() -> list:
    adapters = []
    if config.ENABLED_SITES.get("worknet"):
        from adapters.worknet import WorknetAdapter
        adapters.append(WorknetAdapter())
    if config.ENABLED_SITES.get("saramin"):
        from adapters.saramin import SaraminAdapter
        adapters.append(SaraminAdapter())
    if config.ENABLED_SITES.get("wanted"):
        from adapters.wanted import WantedAdapter
        adapters.append(WantedAdapter())
    if config.ENABLED_SITES.get("publicgov"):
        from adapters.publicgov import PublicGovAdapter
        adapters.append(PublicGovAdapter())
    if config.ENABLED_SITES.get("incruit"):
        from adapters.incruit import IncruitAdapter
        adapters.append(IncruitAdapter())
    if config.ENABLED_SITES.get("jobkorea"):
        from adapters.jobkorea import JobkoreaAdapter
        adapters.append(JobkoreaAdapter())
    if config.ENABLED_SITES.get("catch"):
        from adapters.catch import CatchAdapter
        adapters.append(CatchAdapter())
    return adapters


def main() -> int:
    if not config.NOTION_TOKEN or not config.NOTION_DATABASE_ID:
        print("[FATAL] NOTION_TOKEN / NOTION_DATABASE_ID 환경변수가 없습니다.", file=sys.stderr)
        return 1

    all_jobs: list[JobPosting] = []
    for adapter in build_adapters():
        try:
            jobs = adapter.fetch()
            print(f"[{adapter.name}] 수집 {len(jobs)}건")
            all_jobs.extend(jobs)
        except Exception as e:  # 한 사이트 실패가 전체를 막지 않게
            print(f"[{adapter.name}] 수집 실패: {e}", file=sys.stderr)
            traceback.print_exc()

    # 실행 내 중복 제거
    seen: set[str] = set()
    unique: list[JobPosting] = []
    for j in all_jobs:
        if j.dedup_key in seen:
            continue
        seen.add(j.dedup_key)
        unique.append(j)
    print(f"[합계] 수집 {len(all_jobs)}건 → 중복 제거 {len(unique)}건")

    writer = NotionWriter(config.NOTION_TOKEN, config.NOTION_DATABASE_ID)
    added = writer.upsert_many(unique)
    print(f"[노션] 신규 적재 {added}건 (기존 중복 제외)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
