"""사이트 어댑터 베이스 클래스.

각 어댑터는 fetch() 를 구현해 신입·인턴 개발 공고를 JobPosting 리스트로 반환한다.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

import httpx

import config

KST = timezone(timedelta(hours=9))


def today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


class BaseAdapter(ABC):
    name: str = "base"   # 노션 '출처' SELECT 값과 일치해야 함

    def client(self) -> httpx.Client:
        return httpx.Client(
            timeout=config.HTTP_TIMEOUT,
            headers={"User-Agent": config.USER_AGENT},
            follow_redirects=True,
        )

    @abstractmethod
    def fetch(self) -> list:
        """신입·인턴 개발 공고를 수집해 정규화된 JobPosting 리스트로 반환."""
        raise NotImplementedError
