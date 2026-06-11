"""노션 DB 에 적재된 공고 목록 출력 (확인용)."""
import os
import sys
from pathlib import Path

import httpx

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

tok = os.environ["NOTION_TOKEN"]
db = os.environ["NOTION_DATABASE_ID"].replace("-", "")
h = {"Authorization": f"Bearer {tok}", "Notion-Version": "2022-06-28",
     "Content-Type": "application/json"}
r = httpx.post(f"https://api.notion.com/v1/databases/{db}/query",
               headers=h, json={"page_size": 50}, timeout=30)
r.raise_for_status()
rows = r.json()["results"]


def title(p):
    return "".join(x.get("plain_text", "") for x in p["properties"].get("포지션", {}).get("title", []))


def rich(p, key):
    return "".join(x.get("plain_text", "") for x in p["properties"].get(key, {}).get("rich_text", []))


def sel(p, key):
    s = p["properties"].get(key, {}).get("select")
    return s["name"] if s else "-"


def date(p, key):
    d = p["properties"].get(key, {}).get("date")
    return d["start"] if d else "-"


print(f"노션 DB 총 {len(rows)}건\n" + "=" * 70)
for p in rows:
    print(f"[{sel(p,'출처')}·{sel(p,'직군')}·{sel(p,'고용형태')}] 마감 {date(p,'마감일')}")
    print(f"   {title(p)[:55]}")
    print(f"   @ {rich(p,'회사')}")
