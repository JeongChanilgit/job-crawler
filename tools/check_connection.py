"""노션 연결 + 환경변수 진단 (표준 라이브러리만 사용, deps 불필요).

실행: python tools/check_connection.py
- .env 파일이 있으면 읽고, 시스템 환경변수가 있으면 그게 우선.
- 토큰 값은 마스킹해서 출력 (노출 안 함).
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔에서 한글/이모지 깨짐 방지
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent  # job-crawler/


def load_env():
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def mask(v: str) -> str:
    if not v:
        return "(없음)"
    return "****" if len(v) <= 8 else f"{v[:4]}…{v[-4:]}"


def main() -> int:
    load_env()
    keys = ["NOTION_TOKEN", "NOTION_DATABASE_ID", "DATA_GO_KR_KEY",
            "SARAMIN_ACCESS_KEY", "WANTED_API_KEY"]
    print("== 환경변수 감지 ==")
    for k in keys:
        print(f"  {k}: {mask(os.environ.get(k, '').strip())}")

    tok = os.environ.get("NOTION_TOKEN", "").strip()
    db = os.environ.get("NOTION_DATABASE_ID", "").strip().replace("-", "")

    print("\n== 노션 연결 테스트 ==")
    if not tok or not db:
        print("  ⚠️  NOTION_TOKEN / NOTION_DATABASE_ID 가 안 잡힘.")
        print("     → .env 파일에 넣었는지, 또는 시스템 환경변수로 등록했는지 확인.")
        print("     (현재 터미널에서 $env:로만 설정했다면 다른 프로세스엔 안 보임 → .env 권장)")
        return 1

    req = urllib.request.Request(
        f"https://api.notion.com/v1/databases/{db}",
        headers={"Authorization": f"Bearer {tok}", "Notion-Version": "2022-06-28"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        title = "".join(t.get("plain_text", "") for t in data.get("title", []))
        print(f"  ✅ 연결 성공! DB 제목: {title!r}")
        print(f"     속성 {len(data.get('properties', {}))}개 인식 — 적재 준비 완료.")
        return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"  ❌ 실패 (HTTP {e.code})")
        if e.code == 401:
            print("     → 토큰이 틀렸습니다. NOTION_TOKEN 값에 공백/줄바꿈이 섞였는지 확인.")
        elif e.code == 404:
            print("     → DB를 못 찾음. 거의 항상 'integration을 DB에 연결(•••→Connections)' 단계 누락,")
            print("        또는 NOTION_DATABASE_ID가 틀림.")
        else:
            print("     →", body[:300])
        return 1
    except Exception as e:
        print(f"  ❌ 네트워크/기타 오류: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
