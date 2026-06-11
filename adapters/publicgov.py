"""공공기관 채용정보 (인사혁신처/잡알리오, apis.data.go.kr/1051000/recruitment).

확정 스펙:
  End Point : https://apis.data.go.kr/1051000/recruitment/list  (GET)
  인증       : serviceKey = config.DATA_GO_KR_KEY (data.go.kr 일반 인증키 Decoding)
  응답       : {"result":[{"item":{...}}], "resultCode":0, "totalCount":N}
  핵심필드   : recrutPbancTtl(공고명) instNm(기관) pbancEndYmd(마감) srcUrl(링크)
              recrutSeNm(채용구분) hireTypeNmLst(고용유형) ncsCdNmLst(직무) recrutPblntSn(일련번호)
"""
from __future__ import annotations

import time

import config
from adapters.base import BaseAdapter, today_kst
from core.schema import JobPosting

BASE = "https://apis.data.go.kr/1051000/recruitment/list"


def _ymd(s) -> str | None:
    """'YYYY-MM-DD' 또는 'YYYYMMDD' → 'YYYY-MM-DD', 없으면 None."""
    if not s:
        return None
    s = str(s).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s[:10] if len(s) >= 10 else None


def _is_entry(se_hire: str) -> bool:
    """채용구분/고용유형 문자열이 신입·인턴 계열이면 True."""
    t = se_hire.lower()
    return any(tok in t for tok in ("신입", "인턴", "체험형", "무관"))


# 정보통신 NCS 로 잡히지만 소프트웨어 개발과 무관한 현장직 — 제목에 있으면 제외
_NEG = ("작업원", "일용", "미화", "운전", "경비", "청소", "조리", "주차",
        "안내원", "검침", "환경관리", "설비 유지보수", "배전", "수금",
        "ami", "전력통신", "통신분야", "통신설비", "선로", "비정규 근로자")


class PublicGovAdapter(BaseAdapter):
    name = "공공기관"

    def fetch(self) -> list:
        key = config.DATA_GO_KR_KEY.strip()
        if not key:
            print("[공공기관] DATA_GO_KR_KEY 미설정 — 건너뜀")
            return []

        jobs: list[JobPosting] = []
        seen: set = set()
        with self.client() as cli:
            for page in range(1, config.MAX_PAGES_PER_KEYWORD * 3 + 1):
                params = {
                    "serviceKey": key,
                    "pageNo": page,
                    "numOfRows": config.PAGE_SIZE,
                    "resultType": "json",
                    "ongoingYn": "Y",        # 진행 중 공고만
                    "ncsCdLst": "R600020",   # NCS 대분류 20=정보통신(IT)만 — API단 필터
                }
                try:
                    r = cli.get(BASE, params=params)
                    r.raise_for_status()
                    data = r.json()
                except Exception as e:
                    print(f"[공공기관] p{page} 호출/파싱 실패: {e}")
                    break

                items = data.get("result") or []
                if not items:
                    break

                for entry in items:
                    item = entry.get("item", entry) if isinstance(entry, dict) else {}
                    try:
                        sn = item.get("recrutPblntSn")
                        if sn in seen:
                            continue
                        seen.add(sn)

                        title = (item.get("recrutPbancTtl") or "").strip()
                        hire = (item.get("hireTypeNmLst") or "").strip()
                        se = (item.get("recrutSeNm") or "").strip()

                        # NCS=정보통신으로 이미 IT 필터됨 → 신입·인턴 + 비SW 현장직 제외
                        if not _is_entry(f"{se} {hire}"):
                            continue
                        if any(w in title.lower() for w in _NEG):
                            continue

                        url = (item.get("srcUrl") or "").strip()
                        if not url and sn:
                            url = f"https://job.alio.go.kr/recruitview.do?recrutPblntSn={sn}"

                        jobs.append(JobPosting(
                            source="공공기관",
                            company=(item.get("instNm") or "").strip(),
                            title=title,
                            url=url,
                            employment_type=hire or se or "신입",
                            location=(item.get("workRgnNmLst") or "").strip(),
                            deadline=_ymd(item.get("pbancEndYmd")),
                            keyword="공공기관",
                            collected_date=today_kst(),
                        ))
                    except Exception as e:
                        print(f"[공공기관] 항목 파싱 실패: {e}")
                        continue

                total = data.get("totalCount", 0)
                if total and page * config.PAGE_SIZE >= total:
                    break
                time.sleep(0.4)

        print(f"[공공기관] 수집 {len(jobs)}건")
        return jobs
