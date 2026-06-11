# 채용공고 자동수집 (Job Crawler)

매일 아침 **09:00 KST**에 한국 채용 사이트들에서 **개발 직군 × 신입·인턴** 공고를 수집해
노션 DB에 자동 적재한다. GitHub Actions cron으로 무인 운영.

- **노션 DB**: `채용공고 자동수집 (Job Crawler)` (ID `76922a22ee364f6cac1879575284dae5`)
- **수집 필터**: 개발 직군 전체(백/프론트/모바일/데이터/DevOps/AI) × 신입·인턴
- **실행**: 매일 00:00 UTC = 09:00 KST (`.github/workflows/crawl.yml`)

---

## 사이트 등급 (왜 다 똑같이 안 되나)

| 등급 | 사이트 | 방식 | 상태 |
|---|---|---|---|
| 🟢 공식 API | 워크넷(고용24) | data.go.kr | 구현 완료, 키 발급 후 실검증 |
| 🟢 공식 API | 사람인 | oapi.saramin (JSON) | 구현 완료, 키 발급 후 실검증 |
| 🟢 공식 API | 공공기관(나라일터) | data.go.kr | 구현(엔드포인트 추정), 키 후 검증 |
| 🟢 공식 API | 원티드 | openapi.wanted.jobs | **스캐폴드** — 스키마 확정 후 본체 구현 |
| 🟡 정적 스크래핑 | 인크루트 | httpx+bs4 | 스캐폴드(셀렉터 추정), 실 DOM 검증 필요 |
| 🟡 정적 스크래핑 | 잡코리아 | httpx+bs4 | 스캐폴드, 기본 비활성 |
| 🔴 JS 렌더 | 캐치 | Playwright/내부 API | 스캐폴드, 기본 비활성 |
| ⛔ 제외 | 링크드인 | — | ToS 금지·차단으로 제외 |

> 링크드인은 스크래핑 금지(ToS)·차단이 강해 제외했다. 로켓펀치·피플앤잡·자소설닷컴·링커리어는
> 차단/JS렌더로 Phase 3(로컬 Playwright)로 미뤘다. **개인 구직용** 수집이며 robots·레이트리밋을 존중한다.

---

## 구조

```
job-crawler/
├─ main.py                 # 엔트리포인트: 수집 → 중복제거 → 노션 적재
├─ config.py               # 사이트 토글 · 검색 키워드 · 한도 · 시크릿
├─ requirements.txt
├─ .env.example            # → .env 로 복사해 키 채움 (로컬 전용)
├─ core/
│  ├─ schema.py            # JobPosting + 직군분류/신입필터 헬퍼
│  └─ notion_writer.py     # 노션 적재 + 링크 기준 중복 제거
├─ adapters/
│  ├─ base.py              # BaseAdapter, today_kst()
│  ├─ worknet.py  saramin.py  wanted.py  publicgov.py
│  └─ incruit.py  jobkorea.py  catch.py
└─ .github/workflows/crawl.yml   # 매일 09:00 KST cron
```

---

## 1. API 키 발급 (이게 임계경로 — 승인에 시간 걸림)

| 키 | 발급처 | 비고 |
|---|---|---|
| `DATA_GO_KR_KEY` | https://www.data.go.kr/data/3038225/openapi.do | 워크넷 + 공공기관 채용 공용. **일반 인증키(Decoding)** 사용 |
| `SARAMIN_ACCESS_KEY` | https://oapi.saramin.co.kr/join | 승인제. 일일 500회 |
| `WANTED_API_KEY` | https://openapi.wanted.jobs/ | 원티드 OpenAPI |
| `NOTION_TOKEN` | https://www.notion.so/my-integrations | 아래 2번 참조 (즉시 발급) |

## 2. 노션 연결 (중요)

1. https://www.notion.so/my-integrations → **New integration**(Internal) 생성 → **Internal Integration Secret** 복사 → `NOTION_TOKEN`.
2. 노션에서 `채용공고 자동수집` DB 페이지 열기 → 우상단 `•••` → **Connections** → 방금 만든 integration 연결.
   (이걸 안 하면 토큰이 있어도 쓰기가 거부됨.)
3. `NOTION_DATABASE_ID` 는 이미 `76922a22ee364f6cac1879575284dae5` (`.env.example`에 채워둠).

## 3. 로컬 실행 (스모크 테스트)

```powershell
cd C:\claude-develop\취업준비\job-crawler
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # .env 열어 키 채우기
python main.py
```

> 키가 없는 사이트는 자동으로 0건 반환(크래시 없음). **노션 토큰만 있어도** 파이프라인 배선은 검증된다
> (적재 0건이라도 정상). 각 API 키가 생기면 해당 사이트가 켜진다.

## 4. GitHub Actions 무인 배포

1. 이 폴더를 **비공개** GitHub 저장소로 푸시 (도와줄 수 있음).
2. 저장소 **Settings → Secrets and variables → Actions** 에 등록:
   `NOTION_TOKEN`, `NOTION_DATABASE_ID`, `DATA_GO_KR_KEY`, `SARAMIN_ACCESS_KEY`, `WANTED_API_KEY`
3. **Actions 탭**에서 `채용공고 수집` → **Run workflow** 로 수동 1회 실행해 확인.
4. 이후 매일 09:00 KST 자동 실행.

---

## 설정 바꾸기 (`config.py`)

- `SEARCH_KEYWORDS` — 검색 키워드 (개발 직군 폭 조절)
- `ENABLED_SITES` — 사이트별 on/off (스크래퍼는 셀렉터 검증 후 `True` 로)
- `MAX_PAGES_PER_KEYWORD`, `PAGE_SIZE` — 수집량/호출량

## 현재 상태 · 다음 단계

- ✅ 노션 DB, 프레임워크, 7개 어댑터, cron 워크플로우 완성 (전부 클린 컴파일).
- ⏳ **키 발급 후** 실호출 1회로 워크넷·사람인·공공기관 응답 필드 미세조정.
- ⏳ **원티드** OpenAPI 스키마 확정 후 `wanted.py` 본체 구현.
- ⏳ **인크루트·잡코리아·캐치** 실제 DOM 보고 셀렉터 확정 → 활성화.
