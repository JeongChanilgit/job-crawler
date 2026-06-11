"""노션 쓰기 경로 검증 (표준 라이브러리만). 테스트 행 1개 생성 → 즉시 보관(삭제).

실행: python tools/test_write.py
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))


def load_env():
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def api(method, url, tok, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {tok}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def main() -> int:
    load_env()
    tok = os.environ.get("NOTION_TOKEN", "").strip()
    db = os.environ.get("NOTION_DATABASE_ID", "").strip().replace("-", "")
    if not tok or not db:
        print("토큰/DB 없음 — check_connection.py 먼저 확인.")
        return 1

    today = datetime.now(KST).strftime("%Y-%m-%d")
    body = {
        "parent": {"database_id": db},
        "properties": {
            "포지션": {"title": [{"text": {"content": "[연결테스트] 자동 생성 — 곧 삭제됨"}}]},
            "회사": {"rich_text": [{"text": {"content": "테스트"}}]},
            "출처": {"select": {"name": "워크넷"}},
            "고용형태": {"select": {"name": "신입"}},
            "직군": {"select": {"name": "기타"}},
            "수집일": {"date": {"start": today}},
        },
    }
    try:
        page = api("POST", "https://api.notion.com/v1/pages", tok, body)
        pid = page.get("id", "")
        print(f"  ✅ 쓰기 성공! 테스트 행 생성됨 (id …{pid[-6:]})")
    except urllib.error.HTTPError as e:
        print(f"  ❌ 쓰기 실패 (HTTP {e.code})")
        print("     →", e.read().decode("utf-8", "replace")[:300])
        return 1

    try:
        api("PATCH", f"https://api.notion.com/v1/pages/{pid}", tok, {"archived": True})
        print("  🧹 테스트 행 보관(삭제) 완료 — DB 깨끗합니다.")
    except Exception as e:
        print(f"  ⚠️ 생성은 됐는데 자동삭제 실패: {e}")
        print("     → 노션에서 '[연결테스트]' 행을 수동으로 지우세요.")
    print("\n  ▶ 결론: 노션 읽기+쓰기 모두 정상. 파이프라인 적재 준비 완료.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
