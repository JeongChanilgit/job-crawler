"""data.go.kr API 실응답 덤프 (워크넷 + 공공기관 후보 엔드포인트). 디버그용."""
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

key = os.environ.get("DATA_GO_KR_KEY", "")
print(f"DATA_GO_KR_KEY 길이: {len(key)}  앞4: {key[:4]}")

print("\n========== [1] 워크넷 openapi.work.go.kr ==========")
try:
    r = httpx.get(
        "http://openapi.work.go.kr/opi/opi/opia/wantedApi.do",
        params={"authKey": key, "callTp": "L", "returnType": "XML",
                "startPage": 1, "display": 5, "keyword": "개발"},
        timeout=20,
    )
    print("HTTP", r.status_code)
    print(r.text[:1500])
except Exception as e:
    print("ERR", e)

print("\n========== [2] 공공기관 후보 엔드포인트들 ==========")
candidates = [
    ("1051000/recruitment/list (인사혁신처)",
     "https://apis.data.go.kr/1051000/recruitment/list",
     {"serviceKey": key, "pageNo": 1, "numOfRows": 5, "resultType": "json"}),
    ("1051000/recruitment/list (XML)",
     "https://apis.data.go.kr/1051000/recruitment/list",
     {"serviceKey": key, "pageNo": 1, "numOfRows": 5}),
]
for name, url, params in candidates:
    print(f"\n--- {name} ---")
    try:
        r = httpx.get(url, params=params, timeout=20)
        print("HTTP", r.status_code)
        print(r.text[:700])
    except Exception as e:
        print("ERR", e)
