"""노션 DB 의 모든 행을 보관(archive)해 비운다. (필터 개선 후 깨끗한 재적재용)"""
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

n = 0
while True:
    r = httpx.post(f"https://api.notion.com/v1/databases/{db}/query",
                   headers=h, json={"page_size": 100}, timeout=30)
    r.raise_for_status()
    rows = r.json()["results"]
    if not rows:
        break
    for p in rows:
        httpx.patch(f"https://api.notion.com/v1/pages/{p['id']}",
                    headers=h, json={"archived": True}, timeout=30)
        n += 1

print(f"보관 처리: {n}건 — DB 비움")
