# Agent Sync Board

이 파일은 Codex와 ANTIGRAVITY처럼 여러 AI 도구가 같은 저장소에서 병행 작업할 때 충돌을 줄이기 위한 공유 작업판이다.

새 AI 세션은 `PROJECT_CONTEXT.md`를 먼저 읽고, 그 다음 이 파일을 읽는다. 긴 개발 이력은 필요할 때만 `project-handoff.md`에서 확인한다.

## Current Project Direction

- 현재 프로젝트는 국제정세 사건을 단정적으로 예측하는 시스템이 아니다.
- 현재 목표는 뉴스, 정부 발표, 독립 언론, Reddit 여론, 여론조사, 금융·무역 지표를 종합하는 공급망·지정학 리스크 조기경보 시스템이다.
- 새 작업에서는 “예측 성공/실패”보다 “위험 신호”, “근거”, “경보 단계”, “검증 가능성”을 우선한다.

## Tool Roles

### Codex

Codex는 주로 다음 작업을 맡는다.

- 저장소 구조 정리
- 문서 정합성 점검
- 코드·스크립트 수정
- GitHub에 올릴 변경 단위 정리
- 다른 AI 세션이 만든 결과의 충돌 검토

### ANTIGRAVITY

ANTIGRAVITY는 주로 다음 작업을 맡긴다.

- 특정 기능 구현
- 코드 자동 수정
- UI/대시보드 개선
- 수집기·파이프라인 실행 점검
- Codex가 정리한 요구사항을 코드로 반영

두 도구가 같은 파일을 동시에 고치지 않는 것이 원칙이다.

## Active Work Board

작업을 시작하기 전에 아래 표에 한 줄을 추가하거나 기존 줄을 갱신한다.

| Status | Owner | Area | Files | Task | Last Updated |
| --- | --- | --- | --- | --- | --- |
| done | ANTIGRAVITY | db / pipeline / cross-verification | `scripts/run_pipeline.py`, `scripts/db/load_cross_verification_to_db.py`, `scripts/db/create_views.sql` | 해협 센서·공급망 사건 교차검증의 DB 적재와 대시보드 뷰 연동 | 2026-10-02 |
| done | ANTIGRAVITY | data-collection / supply-chain-sensors | `scripts/collection/fetch_maritime_chokepoints.py`, `scripts/analysis/cross_verify_events.py`, `data/maritime_chokepoints/`, `data/event_cross_verification/` | 해협·시장 센서 수집 및 복수 계통 교차검증 | 2026-10-02 |
| done | ANTIGRAVITY | data-collection / public-opinion | `scripts/collection/fetch_local_opinions.py`, `scripts/collection/fetch_google_trends.py`, `data/local_opinions/`, `data/google_trends/` | 대안 로컬 여론·검색 트렌드 센서 구축 | 2026-09-29 |
| in-progress | ANTIGRAVITY | dashboard / ui | `scripts/dashboard/streamlit_dashboard.py` | Streamlit 대시보드 유지보수 및 고도화 | 2026-09-28 |
| done | Cursor / dashboard-report | dashboard / html-ui | `scripts/dashboard/generate_dashboard_v2.py`, `output/dashboard/` | Information 축 과장 표현 교정(국민 여론·하드코딩 Critical·WATCH 후보 제거) 후 HTML 재생성 | 2026-10-28 |
| in-progress | ANTIGRAVITY | llm-analysis / alert-scoring | `prototype_all_in_one.py`, `scripts/analysis/analyze_signal_gap.py`, `scripts/analysis/analyze_signals.py`, `data/review_log.csv` | LLM 분석·Risk Signal Score·검수 체계 연동 | 2026-09-28 |
| done | Codex | docs / session-sync | `PROJECT_CONTEXT.md`, `AGENT_SYNC.md`, `docs/current/DATA_COLLECTION_GUIDE.md`, `project-handoff.md` | 현재 방향, 센서 분류, 교차검증 규칙, 세션 상태 문서 정리 | 2026-10-02 |
| done | Codex | dashboard / Figma handoff | `docs/current/DASHBOARD_SESSION_PROMPT.md`, `PROJECT_CONTEXT.md`, `AGENT_SYNC.md` | Figma의 5대 감시축 균형 UI와 비상 관제 화면을 대시보드 세션에 인수인계 | 2026-10-04 |
| done | ANTIGRAVITY | dashboard / report / docs-sync | docs/, scripts/dashboard/generate_dashboard_v2.py | 최신 MD(수집 레인 아키텍처, 스크립트 인벤토리, 지도교수 면담자료) 확인 및 대시보드 뷰/표현 정합성 검증 | 2026-10-11 |
| done | Codex | data-collection / GDELT quota safety | `scripts/collection/gdelt_cloud_budget.py`, `scripts/collection/fetch_gdelt_cloud_events.py`, `scripts/run_pipeline.py`, `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md` | Academic & Research 월 5,000 QU에 맞춘 기본 비활성·로컬 월/일 안전상한·요청 간격·사용량 영수증 적용 | 2026-10-13 |
| done | Codex | data-collection / White House official | `scripts/collection/fetch_whitehouse_official.py`, `scripts/run_pipeline.py`, `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/current/PYTHON_SCRIPT_INVENTORY.md` | 백악관 공식 RSS 우선 수집기 초안과 제한적 사이트맵 보완을 선택 플래그로 연결 | 2026-10-15 |
| done | Codex | handoff / White House collector | `docs/current/ANTIGRAVITY_WHITEHOUSE_HANDOFF_PROMPT.md`, `docs/current/DATA_COLLECTION_SESSION_PROMPT.md` | 백악관 수집기 범위·검증 경계·드라이런 절차를 ANTIGRAVITY 인수인계 프롬프트로 정리 | 2026-10-15 |
| done | Cursor / DB-evidence | db / validation-store | `scripts/db/evidence_writer.py`, `scripts/db/load_validation_audit.py`, `scripts/db/manage_test_fixtures.py`, `scripts/db/create_views.sql`, `docs/current/DATABASE_SETUP.md` | 증거 계층 트랜잭션 writer·검증 감사 적재·TEST fixture 관리 | 2026-10-28 |
| done | Cursor Agent | data-collection / Media Cloud Search API | `scripts/collection/fetch_mediacloud.py`, `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`, `docs/current/PYTHON_SCRIPT_INVENTORY.md` | 구호스트 DNS 실패 확인 후 공식 `search.mediacloud.org` + Token 인증으로 후보 수집기 갱신(기본 파이프라인 미연결) | 2026-10-28 |
| done | Cursor Agent | data-collection / source-registry | `config/source_registry/*`, `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`, `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/current/PYTHON_SCRIPT_INVENTORY.md` | source_registry 초안(source_role/required/fallback/license_access_note) + 백악관·정부 RSS 공통 스키마·dedupe 규칙 | 2026-10-28 |
| done | ANTIGRAVITY | integration / notion & docs-sync | `scripts/notion/*`, `project-handoff.md`, `docs/current/NOTION_INTEGRATION_GUIDE.md`, `docs/REPOSITORY_STRUCTURE.md`, `scripts/README.md` | 로컬 MD 전체 작업 이력 반영 및 Notion 4대 연동(작업 보드·문서 보관소·작업 이력·리포트) 동기화 완결 | 2026-10-28 |
| done | ANTIGRAVITY | docs / notion-sync | AGENT_SYNC.md, project-handoff.md, scripts/notion/* | 전체 작업 내역 MD 문서 최신화 및 노션 허브·종합 현황 실시간 동기화 | 2026-10-28 |
| done | ANTIGRAVITY | automation / anomaly-scanner | scripts/automation/*, docs/current/DATA_COLLECTION_ROADMAP.md, docs/current/PYTHON_SCRIPT_INVENTORY.md | 글로벌 이상 징후 무인 스캐너 & 지능형 전처리 파이프라인 구축 및 노션 퍼블리싱 연동 완결 | 2026-10-29 |
| done | Cursor Agent | automation / anomaly-scanner-review | `scripts/automation/auto_anomaly_scanner.py`, `scripts/automation/preprocess_signals.py`, `scripts/notion/publish_notion_report.py`, `docs/current/DATA_COLLECTION_ROADMAP.md`, `docs/current/PYTHON_SCRIPT_INVENTORY.md` | ANTIGRAVITY 초안 검증·문서 깨짐 수정·Alert Level 오인 표현 제거·`--dry-run` 확인 | 2026-10-29 |

Status 값은 `open`, `in-progress`, `review-needed`, `done`, `blocked` 중 하나를 쓴다.

2026-10-28 [Cursor / DB-evidence 세션 시작]
- 한 일: `PROJECT_CONTEXT.md`, `AGENT_SYNC.md`, `DATABASE_SETUP.md`, `VALIDATION_PLAN.md` 정독. `docs/current/DATABASE_VALIDATION_SESSION_PROMPT.md`는 저장소에 없음(`SESSION_PROMPTS.md` §4 + 세션 지시문으로 대체).
- 확인한 것: fixture `TEST-FIXTURE-20261010-00000001` 존재. 운영 행도 있음(`RS-20261027143228-3f787bb6` / `RSS_RUSSIA` CRITICAL held_for_review). 코드 충돌 없음(ANTIGRAVITY 소유 LLM/Streamlit 파일은 비접촉).
- 다음 작업: 트랜잭션 evidence writer, validation audit 적재, fixture 관리, 공식 뷰 4개 검증.
- 주의할 점: `REPLACE INTO` 금지, append-only 유지, TEST fixture를 운영 성과로 보고하지 않음, `.env` 비밀값 비출력.

2026-10-28 [Cursor / DB-evidence handoff]
- 한 일:
  1. `scripts/db/evidence_writer.py` — 점수/갭/경보/근거/검증을 한 트랜잭션으로 저장. `run_key` 중복 거부, 실패 롤백, 입력 어휘 검증, 완료 후 공식 뷰 조회.
  2. `scripts/db/load_validation_audit.py` — `validation_backtest_log.csv`·`review_log.csv`·오류 로그를 `alert_validation_audit`에 append. 원본 CSV 비수정.
  3. `scripts/db/manage_test_fixtures.py` — fixture ensure/verify/cleanup(views). cleanup은 dry-run 기본, `--execute` + `data_quality_audit` 후 삭제.
  4. 공식 뷰 4개에서 `TEST_*` / `test-fixture-v1` / `TEST-FIXTURE%` / `fixture_review` 운영 집계 제외.
- 바꾼 파일: `scripts/db/evidence_writer.py`, `scripts/db/load_validation_audit.py`, `scripts/db/manage_test_fixtures.py`, `scripts/db/create_views.sql`, `docs/current/DATABASE_SETUP.md`, `AGENT_SYNC.md`.
- 확인한 것: writer 스모크(삽입·중복거부·뷰 제외·정리) 통과. `manage_test_fixtures.py verify` OK. 공식 뷰 counts — current_alerts=1, evidence_trace=6, gap_trend=1, validation_summary=5. 대시보드 운영 행=`RSS_RUSSIA` CRITICAL. fixture는 베이스 테이블에만 잔존, 성과 뷰 0건. review 1건 audit 적재. `.env` 비밀값 비출력/비커밋.
- 다음 작업: LLM/scoring 세션이 `evidence_writer.save_scoring_run`을 호출하도록 연결. `validation_backtest_log.csv` 사례 행 채운 뒤 `--sources backtest` 재적재. 품질 정리 스크립트는 dry-run·`data_quality_audit` 뒤에만 실삭제.
- 주의할 점: `prototype_all_in_one.py`·대시보드·`review_log.csv` 덮어쓰기·수집기·`REPLACE INTO` 금지. TEST fixture를 운영 precision으로 보고하지 말 것. mediacloud 등 타 세션 변경 파일은 이번 커밋에 섞지 말 것.

2026-10-04 [Codex / 데이터 수집 범위 확장 결정]
- 한 일: 대시보드·교차검증 업무와 분리하여 데이터 수집·파이프라인 세션의 다음 확장 범위를 정리함.
- 바꾼 파일: `AGENT_SYNC.md`, `project-handoff.md`, `docs/current/DATA_COLLECTION_GUIDE.md`.
- 결정 사항: 항공 물류·ADS-B/공항 운항 센서, 파나마 운하 병목 센서, 다국가 세관 데이터, X 공개 정보환경 신호, 정부 홈페이지의 API/RSS/Sitemap/HTML/PDF 단계형 수집을 우선 검토함.
- 다음 작업: 신규 수집기를 만들기 전에 국가·서비스별 접근 방식과 라이선스·robots·요청 제한을 source registry로 정의하고, 원시 데이터·수집 영수증만 구현할 것.
- 주의할 점: 파나마 운하는 남미 인접 미주 병목으로 기록하며 수에즈 운하와 혼동하지 않는다. X·정부 웹 데이터는 국민 여론이나 확정 사실로 해석하지 않는다.

2026-10-10 [Codex / GDELT 대체·보조 수집기 프로토타입]
- 한 일: 원본 GDELT 2.0 DOC, Media Cloud, ACLED, Event Registry용 제한 수집기를 추가함.
- 바꾼 파일: 당시 루트에 추가한 GDELT/MediaCloud/ACLED/Event Registry 수집기 4개(현재 `scripts/collection/`으로 이동), `docs/current/DATA_COLLECTION_GUIDE.md`, `AGENT_SYNC.md`.
- 확인한 것: Python 컴파일을 통과시켰고, 인증·429·요금 제한 시 파이프라인을 중단하지 않는 `receipt` 구조를 적용함. 현재 환경의 GDELT DOC 직접 호출은 429로 제한됨.
- 다음 작업: GDELT 호출 간격·캐시 정책을 조정하고, Media Cloud·ACLED 계정 승인 후 실제 응답 스키마를 고정해 `run_pipeline.py`에 선택 플래그로 연결할 것.
- 주의할 점: Event Registry는 보조 수단으로만 사용하며 학술 접근 승인 전에는 `AUTH_REQUIRED` 상태를 유지한다. 새 서비스 결과는 검증 세션에서 교차검증하기 전 사실이나 경보로 해석하지 않는다.

2026-10-10 [Codex / 외부 수집기 인증 재시험]
- 한 일: `.env` 인증정보를 사용해 ACLED와 Event Registry 소량 수집을 재시험함.
- 확인한 것: ACLED 예멘 3건 `HTTP 200`, Event Registry Red Sea shipping 3건 `HTTP 200`, 두 결과 모두 `complete=true`로 저장됨. Media Cloud는 기본 호스트 DNS 오류, GDELT 2.0 DOC는 `HTTP 429`로 남아 있음.
- 바꾼 파일: `docs/current/DATA_COLLECTION_GUIDE.md`, `AGENT_SYNC.md`; ACLED `.env` 덮어읽기와 Media Cloud 오류 키 마스킹을 보완함.
- 다음 작업: Media Cloud 공식 최신 API 호스트를 확인하고, GDELT 호출 간격·캐시 정책을 조정한 뒤 선택적 파이프라인 단계로 연결한다.
- 주의할 점: ACLED·Event Registry 결과는 원시 수집 데이터이며 검증 세션에서 교차검증하기 전 경보나 확정 사실로 사용하지 않는다.

2026-10-10 [Codex / Python 스크립트 인벤토리]
- 한 일: `scripts/` 하위 Python 57개를 역할별로 분류하고 `run_pipeline.py` 호출 경로를 확인함.
- 바꾼 파일: `docs/current/PYTHON_SCRIPT_INVENTORY.md`, `PROJECT_CONTEXT.md`, `AGENT_SYNC.md`.
- 확인한 것: 전체 57개 Python 파일 컴파일 통과. 활성 수집기는 `scripts/collection/`, 분석·검증·DB·대시보드는 이미 하위 폴더에 분리되어 있고 신규 외부 API 4개만 루트에 남아 있음.
- 다음 작업: 파일 이동 전에 신규 외부 API 수집기와 manual/prototype 파일의 상태를 확정하고, 영역별로 작은 이동 단위를 만든다.
- 주의할 점: `run_pipeline.py`의 경로를 먼저 갱신하지 않고 파일을 이동하지 않는다. 대시보드·교차검증 담당 세션 파일은 임의로 이동하거나 수정하지 않는다.

2026-10-04 [Codex / dashboard 세션 인수인계]
- 한 일: Figma에서 5대 감시축 중심의 `Balanced Watchboard` 시안을 만들고, 비상상황의 긴장감을 높이는 상단 위험 배너와 경보 상태 표시를 추가함.
- 바꾼 파일: `docs/current/DASHBOARD_SESSION_PROMPT.md`, `PROJECT_CONTEXT.md`, `AGENT_SYNC.md`.
- 확인한 것: Figma 파일 `https://www.figma.com/design/pTJxYxSF0Fv6PuEicHVAhI`, 주요 프레임 `1:2`; `scripts/dashboard/generate_dashboard_v2.py`와 `scripts/dashboard/streamlit_dashboard.py`는 기존 대시보드 담당 세션 소유 파일이므로 직접 수정하지 않음.
- 다음 작업: 대시보드 세션에서 Figma 시안의 5대 축 균형, 비상 배너, 검증 상태·데이터 공백 표시를 실제 HTML/Streamlit 화면에 반영할 것.
- 주의할 점: 비상 색상은 시각적 우선순위 표현일 뿐 확정 사실을 의미하지 않는다. 단일 출처로 Alert Level을 상향하지 말고 `verification_state`와 `complete=false`를 유지한다.

2026-10-02 [Codex / session-sync 및 교차검증 상태 점검]
- 한 일: `PROJECT_CONTEXT.md`와 `AGENT_SYNC.md`를 읽고, 최신 조기경보 방향과 4대 해협 센서·GDELT 사건·복수 계통 교차검증 상태를 확인함.
- 바꾼 파일: `AGENT_SYNC.md`에 조율 전용 작업 행과 본 메모를 추가함.
- 확인한 것: `git status --short`에서 해협 수집기·교차검증기·GDELT·로컬 여론·대시보드·보고서 관련 변경이 다른 세션 작업으로 존재함. 해당 파일들은 수정하지 않음.
- 다음 작업: 교차검증 산출물의 대시보드 연결이나 추가 센서 작업은 기존 담당 세션의 변경이 커밋·정리된 뒤 파일 소유권을 다시 확인하고 진행할 것.
- 주의할 점: 단일 GDELT·Telegram·AIS·시장 신호로 Alert Level을 올리지 않는다. `verification_state`와 `complete=false` 부분 수집 상태를 유지한다.

2026-10-02 [Codex / GDELT Cloud Events 프로브]
- 한 일: GDELT Cloud v2 Events API의 인증·응답 계약을 확인하고, 페이지 수·커서·완료 여부를 기록하는 제한 수집기를 추가함.
- 바꾼 파일: `scripts/fetch_gdelt_cloud_events.py`, `data/gdelt_cloud/*`, `AGENT_SYNC.md`.
- 확인한 것: `GDELT_CLOUD_API_KEY`가 `gdelt_sk_` 형식으로 설정됨. 1행·1페이지 요청이 HTTP 200으로 성공했고, `success=true`, `data[]`, `pagination`, `meta`를 확인함. 첫 실행의 Windows cp949 출력 문제를 수정하고 재실행함.
- 다음 작업: 이벤트 응답을 AIS·항만·운임 신호와 결합하기 전, 국가·해협·공급망 이슈별 쿼리와 `verification_state` 파생 규칙을 별도로 정의할 것.
- 주의할 점: `complete=false`는 1페이지 예산에서 다음 커서가 남았다는 뜻이다. 전체 데이터로 해석하지 말고, API 쿼리 비용과 부분 커버리지를 영수증과 함께 보존한다. 기존 세션이 수정 중인 `scripts/run_pipeline.py`에는 아직 연결하지 않음.

2026-10-02 [Codex / GDELT Cloud 문서·세션 프롬프트]
- 한 일: GDELT Cloud Events를 조기경보의 보조 사건 탐지 센서로 정의하고, 부분 수집·원시/영수증 보존·교차검증·API 키 비노출 원칙을 문서화함.
- 바꾼 파일: `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/current/DATA_COLLECTION_SESSION_PROMPT.md`, `AGENT_SYNC.md`.
- 확인한 것: 기존 GDELT 수집기와 파이프라인은 수정하지 않았고, 기존 `scripts/run_pipeline.py` 변경과 분리된 문서 작업임.
- 다음 작업: 국가·해협·공급망 이슈별 GDELT 쿼리 템플릿과 `verification_state` 파생 규칙을 설계한 뒤 파이프라인 연결 여부를 검토할 것.
- 주의할 점: `data/gdelt_cloud/`의 `complete=false` 결과는 전체 데이터가 아니다. GDELT 사건 하나만으로 경보 단계를 올리지 않는다.

2026-10-02 [Codex / GDELT Cloud 공급망 프로토타입]
- 한 일: 홍해·후티·해상운송 검색을 대상으로 GDELT Cloud Events를 7일·10행·1페이지 범위에서 수집하고, 사건·행위자·장소·출처·검증 대기 상태를 정규화함.
- 바꾼 파일: `scripts/prototype_gdelt_supply_chain_watch.py`, `data/gdelt_cloud/supply_chain_watch_latest.json`, `AGENT_SYNC.md`.
- 확인한 것: Python 컴파일 및 API 실행 성공. 10개 후보가 저장됐고 `complete=false`로 부분 커버리지가 명시됨. Alert Level은 계산하지 않음.
- 다음 작업: AIS·항만 공지·선사 발표·운임/보험료 데이터와 시간창을 맞춰 후보 사건의 교차검증 상태를 산출할 것.
- 주의할 점: 현재 결과는 GDELT 사건 후보일 뿐 실제 공격·운항 중단·피해를 확인한 결과가 아니다. 기존 `scripts/run_pipeline.py`에는 연결하지 않음.

## Recent Handoff

2026-10-29 [Cursor Agent / automation-anomaly-scanner-review]
- 한 일: ANTIGRAVITY가 이미 `done`으로 표시한 `scripts/automation/` 초안을 검증·보강함. 문서 경로 깨짐(`\x07uto_...`) 수정, 보스포루스 threat 강제 High 제거, CRITICAL SPIKE 등 Alert Level 오인 배지를 `ANOMALY_*`로 교체, Notion 제목을 `🚨 [무인자동탐지] YYYY-MM-DD 신규 리스크 징후 브리프`로 고정(`title_override`), 영수증에 `alert_level_set=false` 명시.
- 바꾼 파일: `scripts/automation/auto_anomaly_scanner.py`, `scripts/automation/preprocess_signals.py`, `scripts/notion/publish_notion_report.py`, `docs/current/DATA_COLLECTION_ROADMAP.md`, `docs/current/PYTHON_SCRIPT_INVENTORY.md`, `AGENT_SYNC.md`.
- 확인한 것: `py_compile` 통과. `python scripts/automation/auto_anomaly_scanner.py --dry-run` — 노이즈 2건 배제, 10→6 클러스터, 핫스팟 3건, `data/automation/anomalies_latest.json`·`reports/anomaly_detection/anomaly_brief_*.md` 생성. 기본 `run_pipeline.py` 미연결·GDELT Cloud 미호출. `git pull`은 현재 브랜치(`cursor/local-sync-20261028`)에 upstream 없어 `git fetch origin main`만 수행.
- 다음 작업: (선택) `--with-anomaly-scan` 플래그로 파이프라인 연결, 실제 GDELT DOC 429 대비 캐시 정책, Notion `--publish-notion` 실발행은 토큰 있을 때만.
- 주의할 점: Anomaly Score ≠ Alert Level. Streamlit·LLM 경보 산식·DB 스키마는 미수정. 단일 출처로 경보 격상 금지.

2026-10-29 [ANTIGRAVITY / automation-anomaly-scanner]
- 한 일: 무인 글로벌 이상 징후 스캐너 및 지능형 4단계 전처리 파이프라인 초안 구축.
  1. `scripts/automation/auto_anomaly_scanner.py`: GDELT 2.0 DOC·Google Trends·4대 해협 스캔, Z-Score/Anomaly Score.
  2. `scripts/automation/preprocess_signals.py`: 노이즈 필터·시맨틱 중복 제거·해협/공급망 엔티티 정규화.
  3. Notion `--publish-notion` 연동 및 문서화.
- 바꾼 파일: `scripts/automation/*`, `docs/current/PYTHON_SCRIPT_INVENTORY.md`, `docs/current/DATA_COLLECTION_ROADMAP.md`, `AGENT_SYNC.md`.
- 확인한 것: dry-run 및 Notion 퍼블리싱 시도.
- 다음 작업: 정기 스케줄러 또는 `run_pipeline.py` 선택 플래그 연동.
- 주의할 점: 무인 탐지 결과는 `UNVERIFIED` 유지, 단일 출처만으로 경보 격상 금지.


2026-10-28 [ANTIGRAVITY / notion-integration]
- 한 일: Notion 3대 연동 체계 구축 및 시운전 완료. 1) .env 및 NotionClient 기반 표준 API 래퍼, 2) AGENT_SYNC.md 작업 보드 동기화 모듈(DB 자동 생성 기능 포함), 3) 최신 조기경보 리포트 퍼블리싱 모듈, 4) Antigravity 전용 Notion MCP 설정 파일(~/.gemini/config/mcp_config.json) 생성, 5) notion_manager.py CLI 점검 도구 작성.
- 바꾼 파일: `scripts/notion/notion_client_base.py`, `scripts/notion/sync_notion_board.py`, `scripts/notion/publish_notion_report.py`, `scripts/notion/notion_manager.py`, `docs/current/NOTION_INTEGRATION_GUIDE.md`, `~/.gemini/config/mcp_config.json`, `AGENT_SYNC.md`, `PROJECT_CONTEXT.md`, `README.md`.
- 확인한 것: `notion_manager.py --check` 봇 인증(international analysis) 성공. `notion_manager.py --sync-board`로 허브 하위에 작업 보드 DB(407de224-b441-818c-b033-cb6cf4ad5352) 자동 생성 및 16건 등록 완료. `notion_manager.py --publish-report`로 최신 리스크 브리프 블록 변환 발행 완료.
- 다음 작업: scripts/run_pipeline.py에 --sync-notion 플래그 정식 편입 완료. 파이프라인(--only-db --sync-notion) 실행 시 DB 적재·대시보드 생성 후 Notion 보드(16건) 및 최신 브리프 자동 퍼블리싱 검증 완료. 지도교수 면담자료(PROJECT_ADVISOR_MEETING_BRIEF.md)도 Notion 하위 페이지로 발행 완결.
- 주의할 점: 토큰 및 비밀번호는 .env에 유지하며 .gitignore로 GitHub 커밋에서 엄격히 차단됨.

2026-10-28 [Cursor / dashboard-report]
- 한 일: 지정 문서 8종 정독. HTML 대시보드 Information 축 과장 표현을 교정하고 `generate_dashboard_v2.py`로 재생성.
- 바꾼 파일: `scripts/dashboard/generate_dashboard_v2.py`, `output/dashboard/index.html`, `output/dashboard/dashboard_latest.html`, `AGENT_SYNC.md`.
- 확인한 것:
  1. Streamlit(`scripts/dashboard/streamlit_dashboard.py`)은 Active Work Board상 ANTIGRAVITY `in-progress` → 이번 세션 비접촉.
  2. 공식 뷰에 운영 행 1건 표시: `RSS_RUSSIA` Critical / `human_review_required` / `PARTIALLY_CONFIRMED` (임의 경보 생성 아님).
  3. Telegram 하드코딩 Critical 뱃지·“국민 체감 불안도”·ENERGY `WATCH 후보` 제거. SNS/Trends는 온라인 정보환경 신호로 표기.
  4. `python scripts/dashboard/generate_dashboard_v2.py` 성공. index/latest 갱신(2026-10-28 17:07).
- 다음 작업: `v_alert_evidence_trace`를 `alert_event_id`로 경보 카드에 연결. 보고서 제목/요약을 “조기경보 근거”로 유지 점검. Streamlit 5축은 ANTIGRAVITY 소유권 해제 후.
- 주의할 점: Alert Level 임계값·DB 스키마·수집기·`SESSION_PROMPTS.md`·Streamlit 비접촉. `git add .` 금지(mediacloud·source_registry·DB-evidence 변경과 분리).

2026-10-28 [Cursor / DB-evidence · 재검증]
- 한 일: 세션 프롬프트 문서 정독 후 기존 writer·fixture·공식 뷰를 재검증. 신규 코드 변경 없음.
- 읽은 파일: `PROJECT_CONTEXT.md`, `AGENT_SYNC.md`, `docs/current/DATABASE_SETUP.md`, `docs/current/VALIDATION_PLAN.md`. `docs/current/DATABASE_VALIDATION_SESSION_PROMPT.md`는 없음(`SESSION_PROMPTS.md` §4 + 지시문 대체).
- 확인한 것: fixture `TEST-FIXTURE-20261010-00000001` verify OK·성과 뷰 0건. 운영 run=`RS-20261027143228-3f787bb6` / 대시보드=`RSS_RUSSIA` CRITICAL held_for_review. 뷰 counts current=1 evidence=6 gap=1 validation=5. `load_validation_audit --dry-run`은 중복 1건 skip. 품질 정리 스크립트는 dry-run·`data_quality_audit` 경로 유지.
- 다음 작업: LLM/scoring이 `evidence_writer.save_scoring_run` 호출. 미커밋 DB 파일(`evidence_writer.py` 등)은 mediacloud·source_registry와 분리 커밋.
- 주의할 점: ANTIGRAVITY 소유 Streamlit/LLM 파일·수집기·`review_log.csv`·`REPLACE INTO`·`SESSION_PROMPTS.md` 비접촉. TEST fixture를 precision으로 보고하지 말 것.

2026-10-28 [Cursor Agent / data-collection · source-registry]
- 한 일: `config/source_registry/` 초안 작성(SCHEMA + government/expert/local_media/opinion/customs YAML). 백악관 RSS vs `gov_announcements_collector` 공통 원시 필드·URL dedupe 규칙을 아키텍처 문서에 명시. Media Cloud는 기존 갱신 상태를 유지·문서 교차참조만.
- 바꾼 파일: `config/source_registry/*`, `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`, `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/current/PYTHON_SCRIPT_INVENTORY.md`, `AGENT_SYNC.md`.
- 확인한 것: YAML/스키마 초안 존재; 유료·쿼터·PENDING 센서는 `pipeline_default:false` 또는 `enabled:false`; DB/Streamlit/LLM 파일 비접촉; `docs/SESSION_PROMPTS.md` 미수정.
- 다음 작업: (1) expert/gov 수집기가 registry YAML을 읽도록 이관, (2) `MEDIACLOUD_API_KEY` 소량 프로브(선택), (3) 항공/파나마/세관/X는 라이선스 확인 후 개별 구현.
- 주의할 점: 기본 `--collect-only`에서 GDELT Cloud·Media Cloud·ACLED·Event Registry·White House를 자동 호출하지 않음. DB-evidence 미커밋 파일과 커밋을 섞지 말 것.

2026-10-28 [Cursor Agent / data-collection · Media Cloud]
- 한 일: Media Cloud 공식 Search API 호스트·인증을 재확인하고 `fetch_mediacloud.py`를 `https://search.mediacloud.org/api/` + `Authorization: Token` + `cs`/`ss` 필수로 갱신함. 기본 파이프라인에는 연결하지 않음.
- 바꾼 파일: `scripts/collection/fetch_mediacloud.py`, `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`, `docs/current/PYTHON_SCRIPT_INVENTORY.md`, `AGENT_SYNC.md`.
- 확인한 것: `py_compile` 통과; 키 부재 시 `AUTH_REQUIRED` 영수증; `GET /api/version` HTTP 200; `api.mediacloud.org` DNS 실패; `git diff --check` 통과; 영수증에 키/헤더 값 없음. 원격 브랜치 `cursor/mediacloud-api-notes-8f9f`의 문서 메모와 일치.
- 다음 작업: (1) `MEDIACLOUD_API_KEY` 설정 후 `--limit 3` 소량 프로브, (2) `config/source_registry/` 초안(`source_role`/`required`/`fallback`/`license_access_note`), (3) 백악관 RSS vs `gov_announcements_collector` 공통 원시 스키마·URL 중복 제거 규칙 문서화. 항공/파나마/세관/X는 접근·라이선스 확인 전 미구현.
- 주의할 점: Media Cloud·ACLED·Event Registry·GDELT Cloud는 기본 `--collect-only`에서 호출하지 않는다. 단일 출처로 Alert Level을 올리지 않는다. `docs/SESSION_PROMPTS.md`는 덮어쓰지 않음. Streamlit·LLM·DB 스키마 파일은 타 세션 소유.

2026-10-02 [Codex / Markdown 정합성 정리]
- 한 일: 제어문자 제거, Active Work Board 중복 행 정리, 센서 분류·감사 템플릿 정합성 보정.
- 바꾼 파일: `AGENT_SYNC.md`, `docs/current/DATA_COLLECTION_GUIDE.md`, `project-handoff.md`.
- 확인한 것: 예시 감사 케이스가 시뮬레이션 템플릿임을 표시했고, 시장 지표를 직접 센서가 아닌 영향 프록시로 분류함.
- 다음 작업: 센서별 실제 수집 결과와 감사 케이스를 채운 뒤 `pending_review`를 사람 검수 결과로 교체.
- 주의할 점: 과거 handoff는 역사 기록으로 보존했으며, 현재 작업 보드만 활성 상태로 정리함.

2026-10-02 [ANTIGRAVITY / db-views & pipeline 연동 완결]
- 한 일:
  1. **해협 센서 및 공급망 교차검증 MySQL 테이블(4개) 및 전용 적재기(`scripts/load_cross_verification_to_db.py`) 구현**:
     - `maritime_chokepoint_signals`: 4대 해협(홍해, 호르무즈, 대만, 말라카) 우회지연·전쟁보험료 적재 (4건).
     - `maritime_market_proxies`: BDRY, ZIM, FRO, 브렌트유 등 7개 시장 지표 적재 (7건).
     - `cross_verified_events`: 11개 GDELT 공급망 사건 및 교차검증 상태 적재 (11건).
     - `cross_verified_evidence`: 각 사건별 4대 독립 계통 근거 상세 적재 (33건).
  2. **조기경보 공급망 MySQL 분석 뷰(2개) 구축 (`scripts/create_views.sql`)**:
     - `v_cross_verified_events_summary`: 복수 계통 교차검증된 공급망 사건의 우선순위 랭킹 및 집계 뷰.
     - `v_chokepoint_supply_chain_radar`: 4대 해협의 전쟁보험료 할증과 유조선사(FRO +21.12% 급등) 등 시장 프록시를 결합한 공급망 레이더 뷰.
  3. **대시보드(`scripts/generate_dashboard_v2.py`) DB 뷰 우선 연동**:
     - 대시보드 생성 시 MySQL DB 연결이 존재할 경우 `v_cross_verified_events_summary` 뷰에서 최신 검증 사건을 쿼리하여 렌더링하고, DB 부재 시 파일로 무중단 폴백하는 이중 안정성 구조 구현.
  4. **전체 오케스트레이터 파이프라인(`scripts/run_pipeline.py`) 정식 편입**:
     - `--skip-chokepoints`, `--skip-cross-verification` 플래그 추가.
     - `run_pipeline.py --only-db` 실행 시 DB 집계(`build_database.py`), 해협/교차검증 DB 동기화(`load_cross_verification_to_db.py`), 대시보드 생성(`generate_dashboard_v2.py`)이 0.1분 내 일괄 완주됨을 실증 검증 완료.
- 바꾼 파일: `scripts/load_cross_verification_to_db.py`, `scripts/create_views.sql`, `scripts/run_pipeline.py`, `scripts/generate_dashboard_v2.py`, `docs/current/DATABASE_SETUP.md`, `AGENT_SYNC.md`, `project-handoff.md`
- 확인한 것:
  - `python scripts/run_pipeline.py --only-db`: 3단계 전체 0건 에러 정상 완주 확인.
  - `SHOW TABLES` 및 뷰 쿼리 결과 MySQL 내 4대 테이블 및 12개 뷰 정상 작동 확인.
- 다음 작업 (다른 세션/Codex 인수인계):
  1. [DB/저장소 담당 세션(Codex)]: 기존 원본 테이블(analysis_runs 등)과 build_database.py는 보존되었으므로, 신규 생성된 4대 테이블/2대 뷰의 DDL 및 데이터 정합성을 검토하고, git status의 untracked/modified 파일들을 논리적 커밋 단위로 정리/분리.
  2. [오픈소스 LLM 담당 세션]: data/local_opinions/에 수집된 비영어 로컬 텍스트(대만 PTT, 중국 핀충)를 다국어 LLM 분석 프롬프트에 연결하여 감성/정부발표 괴리 점수 산출 파이프라인 연계.
- 주의할 점: MySQL의 `v_cross_verified_events_summary` 뷰는 단일 출처 사건의 경보 상승을 차단하는 가드레일(single_source_elevate_forbidden)을 내장하고 있으므로, 임의로 임계값을 완화하지 말 것. run_pipeline.py는 기존 파이프라인 단계를 온전히 보존한 채 추가 단계만 배치하였음.

2026-10-02 [ANTIGRAVITY / audit & cross-verification-dashboard-sync 완결]
- 한 일:
  1. **교차검증 데이터 정량 감사 및 결함 수정 (`scripts/cross_verify_events.py`)**:
     - 기존의 무차별 일괄 매칭 결함(11건 전체에 4개 채널이 매칭되어 100% WARNING으로 치솟던 False Corroboration 문제)을 수정하여, 지리·토픽 및 시간창(±72h) 일치 시에만 결합하도록 정밀화함.
     - 결과: `CROSS_VERIFIED` 9건, `PARTIALLY_CONFIRMED` 1건, `UNVERIFIED` 1건으로 정상 분화.
     - 단순 치안/마약 사건(`Hadramout Coast Guard`)은 독립 채널 미결합 시 `UNVERIFIED` / `NORMAL`로 유지되어 `single_source_elevate_forbidden = True` 가드레일 정상 작동 입증.
     - 누락되었던 `source_url`, `observed_at`, `published_at`, `license_note`, `is_partial_probe` 메타데이터 100% 보존.
  2. **조기경보 센서 3계층(직접/교차검증/보조) 및 메타데이터 평가 매트릭스 문서화**:
     - `docs/current/DATA_COLLECTION_GUIDE.md`에 지연시간, 커버리지, 편향, 검열, 봇, 조작, 재현성, 라이선스/접근제한 표 구축.
  3. **폐쇄적 정보환경(중국/이란/러시아/북한) 6대 신호 분리 원칙 및 OSINT 윤리/한계 가이드라인 명문화**:
     - 정부 발표 사실 확정 배제(신호 괴리율 도출), SNS를 온라인 환경 신호로 한정, 비공개 그룹 침투/해킹/표적 정보 수집 절대 금지.
  4. **시계열 유효 시간창(GDELT 7일, 해협 24~72h, SNS 48h, 결합 ±72h) 및 중복 제거 규칙 명문화**.
  5. **대시보드(`scripts/generate_dashboard_v2.py`) 연동**:
     - `verification_state`, 경보 후보 단계, 결합 센서 태그, 관측 시각, 1페이지 예산 부분 수집 경고(`complete=false`), 단일 출처 격상 금지 배지를 포함한 `Multi-Channel Cross-Verification Engine` 위젯 신설. `index.html` 0건 에러 정상 렌더링 확인.
  6. **과거 사건 기반 FP/FN 감사 로깅 스키마 제안**:
     - `docs/current/DATA_COLLECTION_GUIDE.md` 및 `data/audit_cases_template.json`에 스키마와 감사 템플릿 2건(검수 대기 사례, 정상 음성 예시) 작성 완료.
- 바꾼 파일: `scripts/cross_verify_events.py`, `data/event_cross_verification/*`, `docs/current/DATA_COLLECTION_GUIDE.md`, `scripts/generate_dashboard_v2.py`, `output/dashboard/index.html`, `data/audit_cases_template.json`, `AGENT_SYNC.md`
- 확인한 것:
  - `python scripts/cross_verify_events.py`: 11건 중 교차검증 9건, 부분확인 1건, 미확인 1건 정상 산출 및 메타데이터 보존 확인.
  - `python scripts/generate_dashboard_v2.py`: 0건 에러로 `index.html` 렌더링 성공.
- 다음 작업: DB 및 LLM 분석 트랙에서 도출된 이슈별 리스크 스코어와 교차검증된 공급망 사건 후보를 정식 결합하는 뷰 생성.
- 주의할 점: 다른 AI 도구(Codex 등)는 GDELT Cloud 쿼리 시 1페이지 예산(`complete=false`) 상태를 전체 데이터로 해석하지 말고, 단일 사건으로 Alert Level을 임의 상향하지 말 것.

2026-10-02 [ANTIGRAVITY / maritime-chokepoints & cross-verification 구현 완결]
- 한 일: `DATA_COLLECTION_SESSION_PROMPT.md`의 우선순위 1번과 2번을 순차적으로 완결함.
  1. **해협·항만 및 해상 운임·에너지 센서 수집기(`scripts/fetch_maritime_chokepoints.py`) 구현**:
     - 4대 핵심 길목(바브엘만데브 홍해, 호르무즈 해협, 대만 해협, 말라카 해협)의 물리적 프로필, 희망봉 우회 지연일수, 전쟁보험료 할증, AIS 공백/스푸핑 불확실성을 모델링.
     - 발틱 벌크선(BDRY), 컨테이너 정기선사(ZIM, AMKBY/Maersk), 원유 유조선사(FRO/Frontline), 브렌트유(BZ=F), WTI(CL=F), 천연가스(NG=F) 실시간 프록시 수집 완료.
     - 원유 유조선사(FRO) 월간 +21.12% 급등(CRITICAL_SPIKE) 포착.
     - `data/maritime_chokepoints/maritime_latest.csv` 및 `maritime_summary.json` 저장.
  2. **GDELT Cloud 사건 및 복수 계통 신호 시계열 교차검증기(`scripts/cross_verify_events.py`) 구현**:
     - GDELT Cloud v2 사건(일반 사건 + `supply_chain_watch_latest.json` 공급망 후보 10건) 총 11건을 로드.
     - 해협 리스크 + 해상 운임/유조선 시장 + 로컬 여론 + 무장단체(후티/IRGC) 텔레그램 주장과 교차검증 수행.
     - 단일 GDELT 사건으로 Alert Level을 격상하지 않는 안전 원칙(`single_source_elevate_forbidden = True`) 강제.
     - 독립 채널 4개(해협 인프라, 운임 시장, 로컬 여론, 텔레그램 성명)가 일치한 홍해/호르무즈 사건들에 대해 `verification_state: CROSS_VERIFIED`, `alert_candidate_level: WARNING`을 산출하고 `data/event_cross_verification/`에 적재.
- 바꾼 파일: `scripts/fetch_maritime_chokepoints.py`, `scripts/cross_verify_events.py`, `data/maritime_chokepoints/*`, `data/event_cross_verification/*`, `AGENT_SYNC.md`, `project-handoff.md`
- 확인한 것:
  - `python scripts/fetch_maritime_chokepoints.py`: 7개 시장 지표 및 4개 해협 종합 평가 0건 에러 정상 저장.
  - `python scripts/cross_verify_events.py`: 11개 GDELT 사건 교차검증 0건 에러 정상 완료.
- 다음 작업: 교차검증 산출물(`verification_latest.json`)을 대시보드(`scripts/generate_dashboard_v2.py`)의 근거 추적 및 Alert Level 렌더링 카드에 결합.

2026-09-29 [ANTIGRAVITY / data-collection & dashboard 해외 여론 대안 센서 구축 및 대시보드 연동 완결]
- 한 일:
  1. 레딧의 HTTP 429 차단 한계를 극복하기 위해 검열 우회 및 차단 없는 5대 대안 센서 통합 수집기(`scripts/fetch_local_opinions.py`) 개발 완료 (대만 PTT, 중국 핀충, 블루스카이 API, 구글 뉴스 로컬 RSS, 텔레그램 OSINT). 44건 실시간 정상 적재.
  2. 구글 트렌드 위험 키워드 지표 수집기(`scripts/fetch_google_trends.py`) 실증 가동 (러시아 평화협상 x7.66 급등, 군 피해 x7.31 급등, 사우디 후티 x2.21 급등 포착).
  3. 전체 파이프라인(`scripts/run_pipeline.py`)에 구글 트렌드 및 5대 로컬 센서 수집 단계 정식 편입 (`--skip-trends`, `--skip-local-opinions` 플래그 지원).
  4. 단일 웹 대시보드(`scripts/generate_dashboard_v2.py` → `output/dashboard/index.html`)에 [구글 트렌드 위험 행동 지표] 및 [레딧 대체 5대 로컬 여론 스트림] 전용 위젯 섹션 신설 및 시각화 연동 완료.
- 바꾼 파일: `scripts/fetch_local_opinions.py`, `scripts/fetch_google_trends.py`, `scripts/generate_dashboard_v2.py`, `scripts/run_pipeline.py`, `output/dashboard/index.html`, `data/local_opinions/*`, `data/google_trends/*`, `AGENT_SYNC.md`, `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/SESSION_PROMPTS.md`, `project-handoff.md`
- 확인한 것:
  - `python scripts/fetch_local_opinions.py` 실행 시 5개 플랫폼 44건 오류 없이 `data/local_opinions/`에 저장됨.
  - `python scripts/generate_dashboard_v2.py` 실행 시 PTT, 핀충, 블루스카이, 구글뉴스, 텔레그램, 구글트렌드 카드가 균형 배치되어 `index.html`에 완전 렌더링됨.
  - `python scripts/run_pipeline.py --only-db` 실행 시 DB 집계부터 대시보드 생성까지 0.1분 내 무장애 정상 완주 확인.
- 다음 작업: 새로 유입된 로컬 여론 텍스트(대만 PTT 양안 이슈, 중국 핀충 경제 불만)를 다국어 LLM(Qwen2.5/Falcon3) 분석 프롬프트와 연결하여 이슈별 경보 등급 산출 파이프라인에 가중치로 반영.
- 주의할 점: 레딧 Atom 피드는 반복 요청 시 429 차단 위험이 크므로 대안 센서(`fetch_local_opinions.py`)를 기본값으로 유지할 것.

2026-09-28 [ANTIGRAVITY / dashboard·reports 조기경보 산출물 정리]
- 한 일: PROJECT_CONTEXT.md와 AGENT_SYNC.md를 검토하여 현재 조기경보 방향(Alert Level, 위험 징후, 근거, 검증 상태)과 세션 분업 규칙을 파악함. scripts/generate_dashboard_v2.py의 금융 프록시 부동소수점 예외(safe_float 미처리로 인한 crash) 및 fetch_signal_gap_data 예외 처리 결함을 수정하고 대시보드(output/dashboard/index.html)와 공식 보고서(Word/PDF) 생성 파이프라인 정상 가동을 확인 및 검증함.
- 바꾼 파일: AGENT_SYNC.md, scripts/generate_dashboard_v2.py, reports/issues/docx/* (5종), reports/issues/pdf/* (6종)
- 확인한 것: git pull 결과 원격 최신 상태(Already up to date). scripts/generate_dashboard_v2.py 실행 결과 21개 이슈, 정부 발표 462건, 기사 로그 518건을 집계하여 index.html이 정상 렌더링됨. docx_report_generator.py 및 pdf_report_generator.py도 0건 에러로 완전 렌더링되어 DB(analysis_reports) 및 지정 폴더(분석보고서/)에 동기화됨.
- 다음 작업: DB/LLM 트랙에서 v_early_warning_dashboard 또는 risk_alert_status 뷰·테이블이 구현되면, EARLY_WARNING_SNAPSHOT_QUERY 환경변수 또는 스키마 조인을 통해 대시보드 상단의 '확인 필요' 상태를 승인된 Alert Level(Normal, Watch, Warning, Critical) 데이터로 정식 결합.
- 주의할 점: 대시보드 생성기에서 Alert Level을 기사 수나 관심도로 임의 추론(Inference)하지 않고, DB/분석 트랙의 승인된 스냅샷 부재 시 '확인 필요' 상태를 유지해야 함.

2026-09-28 [Codex / session sync 및 충돌 점검]
- 한 일: `git pull`로 원격 최신 상태를 확인하고 `git status --short`, `PROJECT_CONTEXT.md`, `AGENT_SYNC.md`를 검토함.
- 바꾼 파일: `AGENT_SYNC.md`에 본 세션 작업 행을 추가함.
- 확인한 것: 원격은 `Already up to date`; 시작 시 수정 파일은 `AGENT_SYNC.md` 하나였음. ANTIGRAVITY가 같은 파일을 `in-progress`로 보유 중이어서 문서 공동 수정 충돌 가능성이 있음.
- 다음 작업: 별도 기능 작업 전 ANTIGRAVITY의 `AGENT_SYNC.md` 변경 완료 여부를 재확인하고, 코드 파일은 소유권이 명확한 경우에만 수정함.
- 주의할 점: 예측·챗봇 문서는 이력으로만 취급하며, 현재 산출물은 공급망·지정학 리스크 조기경보 시스템임.

2026-09-28 [Codex / information-environment 및 데이터 수집 문서]
- 한 일: PROJECT_CONTEXT.md와 AGENT_SYNC.md를 읽고, 원격 최신 상태를 동기화한 뒤 현재 조기경보 방향과 정보환경 프로토타입 작업 상태를 확인함.
- 바꾼 파일: 이 세션에서는 AGENT_SYNC.md만 갱신함. 정보환경·수집 기준의 본문과 프로필 파일은 기존 작업 결과를 확인함.
- 확인한 것: `git pull` 결과 `Already up to date`; 시작 시 `git status --short`는 깨끗함. Active Work Board에서 ANTIGRAVITY는 AGENT_SYNC.md만 담당 중이며, 본 영역과 직접 겹치는 코드 작업자는 확인되지 않음.
- 다음 작업: 정보환경 프로필을 실제 수집기 선택·경보 메타데이터에 연결하기 전, 국가별 출처 레지스트리와 검증 상태 필드를 확정해야 함.
- 주의할 점: 예측·챗봇 문서는 이력으로만 취급한다. 정보환경 등급은 국가의 진실성 평가가 아니며, 공급망 영향도와 정보 관측 가능성을 한 점수로 합치지 않는다.

## File Ownership Rule

작업을 시작하기 전에 아래를 확인한다.

1. `git status --short`로 이미 바뀐 파일을 확인한다.
2. 이 파일의 Active Work Board에서 다른 도구가 같은 파일을 맡고 있는지 확인한다.
3. 같은 파일을 수정해야 하면 먼저 현재 작업자의 결과를 읽고 이어서 수정한다.
4. 단순 문서 작업과 코드 작업을 한 커밋에 섞지 않는다.

## Handoff Rule

작업이 끝나면 아래 형식으로 이 파일 또는 `project-handoff.md`에 짧게 남긴다.

```text
YYYY-MM-DD [도구명 / 담당영역]
- 한 일:
- 바꾼 파일:
- 확인한 것:
- 다음 작업:
- 주의할 점:
```

짧은 작업은 이 파일에 남기고, 중요한 방향 전환이나 긴 작업 이력은 `project-handoff.md`에 남긴다.

## Historical Handoff Notes

2026-09-28 [Codex / project-context·session-audit]
- 한 일: `git pull`과 `git status --short`를 실행하고 `PROJECT_CONTEXT.md`, `AGENT_SYNC.md`를 읽어 현재 방향과 병행 세션 상태를 확인함.
- 바꾼 파일: `AGENT_SYNC.md`에 본 작업의 조율 전용 담당 행을 추가함.
- 확인한 것: 원격은 최신 상태였고, 작업 트리에는 `AGENT_SYNC.md` 변경이 이미 있었음. ANTIGRAVITY와 다른 Codex 작업이 `AGENT_SYNC.md`를 공유하므로 충돌 가능성이 있음. 현재 프로젝트의 기준은 공급망·지정학 리스크 조기경보이며 예측/챗봇 문서는 이력임.
- 다음 작업: 정보환경·데이터 수집 문서 작업은 기존 담당 세션의 변경을 먼저 확인한 뒤 진행할 것.
- 주의할 점: `AGENT_SYNC.md`를 추가 수정할 때는 기존 Active Work Board 행과 Recent Handoff Notes를 덮어쓰지 말고 최소 패치만 적용할 것.

## Prompt for ANTIGRAVITY

ANTIGRAVITY에 새 작업을 맡길 때는 아래 문장을 먼저 붙인다.

```text
먼저 PROJECT_CONTEXT.md와 AGENT_SYNC.md를 읽고 현재 프로젝트 방향과 다른 AI 세션의 작업 상태를 파악해줘.

이 프로젝트는 국제정세 예측 시스템이 아니라 공급망·지정학 리스크 조기경보 시스템이다. 예전 예측/챗봇 문서는 docs/history 또는 docs/archive의 이력으로만 봐.

작업 시작 전 git status --short를 확인하고, AGENT_SYNC.md의 Active Work Board에 네가 맡을 영역과 파일을 기록해줘. 이미 다른 도구가 수정 중인 파일은 충돌 가능성을 먼저 보고해줘.
```

## Historical Handoffs

2026-10-04 [Codex / dashboard balanced-watchboard implementation]
- 한 일: Figma `Balanced Watchboard` 시안의 5대 감시축 균형 카드와 비상 배너 구조를 HTML 대시보드에 반영함. Alert Level은 공식 DB 뷰 데이터만 사용하도록 유지함.
- 바꾼 파일: `scripts/dashboard/generate_dashboard_v2.py`, 생성 산출물 `output/dashboard/index.html` 및 최신본.
- 확인한 것: Python 컴파일 및 `python scripts/dashboard/generate_dashboard_v2.py` 실행 성공. HTML에서 `MARITIME`, `ENERGY`, `INFORMATION`, `FINANCE / TRADE`, `STATE / ACTOR` 5개 카드와 `NO SINGLE-SOURCE ESCALATION` 문구 확인.
- 다음 작업: `scripts/dashboard/streamlit_dashboard.py`는 ANTIGRAVITY가 in-progress 소유 중이므로 별도 세션에서 동일한 5축 구조를 반영할 것.
- 주의할 점: `UNVERIFIED`·`PARTIALLY_CONFIRMED`·`CROSS_VERIFIED`를 구분하고, `complete=false` 부분 수집과 공개 주장 데이터를 확정 사실로 표시하지 않는다.

2026-10-10 [Codex / official dashboard alert-view connection check]
- 한 일: `scripts/dashboard/generate_dashboard_v2.py`가 공식 뷰 `v_dashboard_current_alerts`의 연결 실패와 빈 스냅샷을 구분하도록 보완함.
- 확인한 것: MySQL 연결 성공, 공식 뷰 존재 확인. 현재 `scoring_runs`, `risk_signal_scores`, `signal_gap_snapshots`, `alert_events`가 모두 0건이라 공식 경보 행은 아직 없음. 대시보드는 임의 경보를 만들지 않고 `공식 경보 뷰 연결됨 · 최신 산출 스냅샷 없음`으로 표시함.
- 다음 작업: DB/LLM 담당 세션에서 완료된 scoring run과 alert event를 공식 뷰에 적재한 뒤 대시보드를 재생성하고, `v_alert_evidence_trace` 근거 연결을 검증할 것.
- 주의할 점: 현재 화면의 `확인 필요`는 데이터 부족 상태이며 Alert Level이 아니다. `scripts/dashboard/streamlit_dashboard.py`는 ANTIGRAVITY 소유 파일이므로 별도 조율 없이 수정하지 않음.

2026-09-28 [Codex / coordination · video-prototype handoff]
- 한 일: 최신 원격 상태, 현재 조기경보 방향, 작업판과 영상 분석 프로토타입의 추적 상태를 확인했다.
- 바꾼 파일: `AGENT_SYNC.md`.
- 확인한 것: `git pull --ff-only`은 최신 상태였고 작업 트리는 깨끗했다. `scripts/analyze_video_prototype.py`는 Git 추적 상태다.
- 다음 작업: 영상 분석은 감정·의도 판정이 아닌, 위험 신호 검토를 위한 시간 코드 근거 탐색 기능으로만 확장한다.
- 주의할 점: ANTIGRAVITY가 `AGENT_SYNC.md`를 `in-progress`로 보유 중이므로, 다음 작업 전 해당 행의 상태를 다시 확인한다.

2026-09-28 [Codex / sync · repository-state audit]
- 한 일: `PROJECT_CONTEXT.md`와 `AGENT_SYNC.md`를 읽고 `git pull --ff-only` 및 `git status --short`를 실행함.
- 바꾼 파일: `AGENT_SYNC.md`에 작업 행과 충돌 주의 기록을 최소 추가함.
- 확인한 것: 원격은 `Already up to date`; 시작 시 작업 트리에는 `AGENT_SYNC.md`만 수정 상태였고, 기존 수정은 다른 세션의 작업 보드·인수인계 내용으로 확인함.
- 다음 작업: 실제 구현을 시작할 경우 먼저 파일별 Active Work Board 소유권을 다시 확인하고, ANTIGRAVITY의 `AGENT_SYNC.md` 작업이 끝난 뒤 보드 중복 행을 정리함.
- 주의할 점: `AGENT_SYNC.md`는 현재 다른 세션과 공유 수정 중인 파일이므로, 이후 변경은 최소 범위로 유지하고 별도 커밋에서 충돌을 확인해야 함.

2026-09-28 [ANTIGRAVITY / sync · conflict-audit]
- 한 일: `PROJECT_CONTEXT.md`와 `AGENT_SYNC.md` 정독, `git pull` 실행, `git status --short` 확인, Active Work Board 갱신 및 세션 간 충돌 가능성 점검.
- 바꾼 파일: `AGENT_SYNC.md`.
- 확인한 것: `git pull` 최신 상태(`Already up to date`). 작업 트리에서 유일하게 변경 중인 파일은 세션 공유 파일인 `AGENT_SYNC.md`뿐이며, 다른 코드 및 데이터 파일은 커밋 완료되어 현재 코드 레벨의 직접적 충돌은 없음.
- 다음 작업: 구체적인 구현 과업(대시보드 UI/차트 고도화, 수집 파이프라인 확장 등) 지정 시 해당 파일 소유권을 Active Work Board에 등록 후 구현 착수.
- 주의할 점: 조기경보 시스템(Early-Warning System) 정체성을 유지하며, 과거 예측/챗봇 문서는 이력으로만 참조할 것.


2026-09-28 [ANTIGRAVITY / session-sync 및 충돌 점검]
- 한 일: `PROJECT_CONTEXT.md`와 `AGENT_SYNC.md`를 읽어 현재 방향(공급망·지정학 리스크 조기경보)과 세션 분업 상태를 확인함. `git pull` 및 `git status --short`를 수행함.
- 바꾼 파일: `AGENT_SYNC.md`.
- 확인한 것: `git pull` 결과 최신(`Already up to date`), `git status --short` 상 `AGENT_SYNC.md`만 수정 상태임. 다른 세션(Codex)이 `AGENT_SYNC.md`에 작업 로그를 기록 중이었으며, 현재 코드나 스크립트 파일 충돌은 없음.
- 다음 작업: 사용자로부터 구체적인 구현/개선 작업(UI/대시보드 개선, 수집기/파이프라인 실행 점검 등) 지시 대기.
- 주의할 점: 이전 예측·챗봇 문서는 단순 이력(docs/history, docs/archive)으로 취급함. Codex가 담당하는 영역(저장소 구조 정리, DB/스크립트 리팩토링 등)과 파일 소유권이 겹치지 않도록 주의.

2026-10-13 [Codex / GDELT Cloud QU 안전장치]
- 한 일: 학술 계정 월 5,000 QU를 기준으로 GDELT Cloud 호출을 기본 비활성화하고, 명시적 선택 실행에만 로컬 월·일 안전상한과 요청 간격을 적용했다.
- 바꾼 파일: `scripts/collection/gdelt_cloud_budget.py`, `scripts/collection/fetch_gdelt_cloud_events.py`, `scripts/run_pipeline.py`, `.gitignore`, `PROJECT_CONTEXT.md`, `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`, `docs/current/DATA_COLLECTION_SESSION_PROMPT.md`.
- 확인한 것: Python 컴파일, 파이프라인·수집기 도움말, 1 QU 초과 시 로컬 차단 동작, `git diff --check` 통과. 실제 API 호출은 비용 안전을 위해 실행하지 않았다.
- 다음 작업: GDELT Cloud Usage 화면과 `quota_state.json`을 주기적으로 대조하고, 필요 시 월·일 안전상한을 더 낮춘다.
- 주의할 점: 로컬 미터는 청구 시스템이 아니며 실제 사용량은 GDELT Cloud Usage 화면이 기준이다. API 키·Authorization 헤더는 로그·커밋에 남기지 않는다.

2026-10-15 [Codex / White House official RSS collector]
- 한 일: 백악관 공식 Releases RSS를 기본 경로로 수집하고, 선택적으로 사이트맵에서 누락 URL을 제한 발견하는 초안 수집기를 추가했다.
- 바꾼 파일: `scripts/collection/fetch_whitehouse_official.py`, `scripts/run_pipeline.py`, `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/current/PYTHON_SCRIPT_INVENTORY.md`, `docs/current/DATA_COLLECTION_SESSION_PROMPT.md`, `docs/current/ANTIGRAVITY_WHITEHOUSE_HANDOFF_PROMPT.md`.
- 확인한 것: 최근 1일·최대 3건 RSS 실행 성공, `data/whitehouse_official/whitehouse_latest.json`과 `rss_latest.xml` 저장, Python 컴파일 및 `--with-whitehouse` 도움말 확인.
- 다음 작업: 문서 유형별 RSS/HTML 본문 필드와 중복 제거 규칙을 검토한 뒤 공식 발표 공통 스키마에 연결한다.
- 주의할 점: 백악관 발표는 공식 입장 신호이지 사실 확정이 아니다. `--with-whitehouse`는 선택 실행이며 robots.txt와 요청 제한을 준수한다.


2026-09-28 [ANTIGRAVITY / llm-analysis · early-warning-alert sync]
- 한 일: `PROJECT_CONTEXT.md`와 `AGENT_SYNC.md` 검토 완료. `git pull` 최신 확인 및 `git status --short` 확인. Active Work Board에 LLM 분석·경보 산식 담당 영역 등록 완료.
- 바꾼 파일: `AGENT_SYNC.md`
- 확인한 것: 원격 최신 상태(`Already up to date`), 작업 트리는 `AGENT_SYNC.md`만 수정 상태이며 코드 파일 충돌 없음.
- 다음 작업: 사용자 요청에 따른 LLM 분석 프롬프트 고도화, 신호 괴리 산식 조정 또는 검수 표본 연동 작업 수행.
- 주의할 점: 미래 사건 예측/발생 확정 표현 배제, 관측 가능한 위험 신호·근거·경보 단계 중심 서술 유지.


2026-09-28 [ANTIGRAVITY / dashboard / ui]
- 한 일: PROJECT_CONTEXT.md 및 AGENT_SYNC.md 정독 완료. 예측 시스템이 아닌 '공급망·지정학 리스크 조기경보 시스템'임을 재숙지함. git pull 및 git status --short 확인 후 작업판에 Dashboard 소유권을 등록함.
- 바꾼 파일: AGENT_SYNC.md
- 확인한 것: git pull은 최신 상태였으며, 다른 세션(Codex)이 AGENT_SYNC.md를 활발히 점검 및 수정 중임을 인지함. 내가 이전에 작성했던 scripts/streamlit_dashboard.py 파일 등은 이미 안전하게 Commit 된 상태임을 확인.
- 다음 작업: 사용자의 추가 지시에 따라 조기경보 대시보드(Streamlit)의 UI 기능 확장 또는 신규 리스크 모니터링 모듈을 개발할 준비 완료.
- 주의할 점: 다른 Codex 세션과 AGENT_SYNC.md 수정 충돌을 피하기 위해 문서 작업은 최소화하고 코드(Dashboard) 고도화에 집중할 것.

2026-10-02 [ANTIGRAVITY(Codex-role) / code-audit & git-commit-grouping]
- 한 일:
  1. git status --short를 통해 작업 트리 분석
  2. 직전 ANTIGRAVITY 세션에서 추가한 해협 수집기, 교차검증기, DB DDL(scripts/create_views.sql), 통합 파이프라인(scripts/run_pipeline.py), 대시보드 등의 소스코드 정합성 검토 (기존 로직 파괴/수정 없이 잘 확장되었음을 확인)
  3. 현재 작업 트리의 변경 사항들을 4개의 논리적 커밋 단위(센서 수집기, 교차검증 엔진, DB/파이프라인, 대시보드/문서)로 분리/설계
- 바꾼 파일: AGENT_SYNC.md
- 확인한 것:
  - 신규 뷰(`v_cross_verified_events_summary`, `v_chokepoint_supply_chain_radar`) 생성 코드가 기존 scripts/create_views.sql에 충돌 없이 안전하게 추가됨.
  -
un_pipeline.py에 --skip-chokepoints, --skip-cross-verification 등 플래그 및 신규 수집/검증/DB 적재 프로세스가 순차적으로 잘 병합됨.
  - 기존 로직이나 사용자 커스텀 코드가 훼손된 정황은 발견되지 않음.
- 다음 작업: 설계한 Git 커밋 가이드라인을 사용자(또는 다른 세션)에게 전달하여 안전하게 버전을 기록(Commit)할 수 있도록 권고.
- 주의할 점: 현재 미추적(untracked)된 디렉토리와 파일들이 매우 많으므로, 한 번에 git add .를 수행하지 말고 제안한 4개의 논리적 그룹에 맞추어 커밋을 분할하는 것이 이력을 깔끔하게 관리하는 방법임.

2026-10-10 [Codex / Python 파이프라인 정리]
- 한 일: 신규 외부 API 수집기 4개를 `scripts/collection/`으로 이동하고 문서 경로를 갱신했다. 57개 Python 파일 인벤토리에서 실제 `run_pipeline.py` 호출 여부를 분류했다.
- 바꾼 파일: `scripts/collection/fetch_{acled,event_registry,gdelt_v2_public,mediacloud}.py`, `scripts/run_pipeline.py`, `docs/current/PYTHON_SCRIPT_INVENTORY.md`, `docs/current/DATA_COLLECTION_GUIDE.md`.
- 확인한 것: `--collect-only`, `--skip-db`, `--skip-dashboard` 실행 그룹 플래그를 추가했다. 대시보드·교차검증 구현 파일은 수정하지 않았다.
- 다음 작업: ACLED/Event Registry 선택 연결 여부 결정 후 항공·파나마·다국가 세관·X·정부 웹 수집기를 `scripts/collection/`에 개별 구현한다.
- 주의할 점: `prototype_local_expert_sources.py`는 이름과 달리 현재 기본 파이프라인에서 호출된다. `prototype_*` 파일을 이동·삭제할 때는 호출 관계와 다른 세션 소유권을 먼저 재확인한다.

2026-10-10 [Codex / 수집 레인 아키텍처 문서화]
- 한 일: GDELT Cloud·AIS·정부 발표를 FAST, 싱크탱크·현지 언론을 CONTEXT, 공개 여론을 OPINION, 세관·무역·금융·여론조사를 BASELINE으로 분리하는 수집 아키텍처를 문서화했다.
- 바꾼 파일: `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`, `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/current/PYTHON_SCRIPT_INVENTORY.md`, `PROJECT_CONTEXT.md`, `AGENT_SYNC.md`.
- 확인한 것: 싱크탱크는 registry 기반 단일 수집기로 확장하고, 수집 세션은 원시 데이터·영수증만 전달하며 `verification_state`·Alert Level·LLM 결과는 생성하지 않는 경계를 확정했다.
- 다음 작업: `config/source_registry/` 스키마 작성, 전문가 피드 registry 이관, `fetch_expert_sources.py` 구현, 이후 `run_pipeline.py --group` 지원 추가.
- 주의할 점: LLM 분석·경보 산식 세션은 `claim_type`, orientation, issue_tags를 해석하되 수집 원문과 접근 메모를 덮어쓰지 않는다.
- 2026-10-11 [Codex / tev1 보조 판정 백테스트]
- 한 일: `tev1`을 `/v1/systemone`으로 호출하는 소규모 4건 백테스트를 실행했다.
- 바꾼 파일: `scripts/validation/backtest_tev1.py`, `data/tev1_backtest_results.json`.
- 확인한 것: 4건 모두 호출 성공. 우크라이나·미중 무역은 `CRITICAL`, 대만해협은 `WARNING`, 홍해는 `WATCH`로 판정됐다. 홍해 사례는 `WATCH` 46.3%와 `INSUFFICIENT_EVIDENCE` 37.9%로 불확실성이 높았다.
- 다음 작업: 실제 동결 입력과 사람 검수 라벨을 추가해 10건 이상으로 확대하고, 기존 Risk Signal Score와 불일치 사례를 검수한다.
- 주의할 점: 이번 결과는 시뮬레이션된 구조화 특징에 대한 보조 비교이며 공식 Alert Level이나 정확도 증명이 아니다. `confidence`는 정답 확률이 아니다.

## 2026-10-12 [Codex / 교수님 연구실 면담 및 참여 검토]

- 한 일: 개인 프로젝트를 지도교수님께 설명한 뒤 제안받은 학부연구생·연구실 참여 가능성을 면담 기록으로 정리했다.
- 확인한 것: 후속 미팅은 석사생들의 주제 설정·교수님 컨펌 과정을 관찰하는 자리였으며, 데이터 플랫폼·비정형 데이터 처리·분석 인프라·시스템/아키텍처·파이프라인 설계 역량이 중요하게 언급되었다.
- 현재 상태: 연구실 참여는 확정이 아니라 검토 중이다. 개인 국제정세 조기경보 프로젝트와 연구실 프로젝트는 별개의 활동으로 유지한다.
- 다음 작업: 주당 시간, 역할, 활동 기간, 지도 방식, 성과 인정, 데이터·코드·AI 사용 규정을 확인한 뒤 참여 여부를 결정한다.
- 상세 기록: `docs/history/PROFESSOR_LAB_MEETING_20261012.md`.
- 주의할 점: 연구실 제안을 개인 프로젝트의 주제 변경이나 참여 확정으로 표현하지 않는다.


## 2026-10-28 [ANTIGRAVITY / notion 연동 및 동기화 실행]

- 한 일: Notion API 토큰 인증 및 허브 페이지 권한 점검 완료, `AGENT_SYNC.md` Active Work Board 16개 항목 노션 칸반 데이터베이스 동기화 완료, 최신 조기경보 마크다운 리포트 노션 페이지 자동 퍼블리싱 완료.
- 바꾼 파일: `AGENT_SYNC.md`, `project-handoff.md`, `docs/current/NOTION_INTEGRATION_GUIDE.md`, `docs/REPOSITORY_STRUCTURE.md`, `scripts/README.md`, `docs/current/PYTHON_SCRIPT_INVENTORY.md`, `scripts/notion/sync_notion_docs.py`, `scripts/notion/publish_notion_report.py`, `scripts/notion/notion_manager.py`
- 확인한 것:
  - 로컬 마크다운 문서(`project-handoff.md` 등)에 2026-10-13 ~ 2026-10-28 전체 작업 내역 최신화 반영
  - Notion API 봇 토큰 정상 인증 (`international analysis`, ID: `407de224-b441-81fb-9d81-0027f38ff54c`)
  - 허브 페이지(`international-analysis 프로젝트`) 접근 정상
  - 작업 보드(`📋 AI 세션 작업 동기화 보드`) 16개 태스크 동기화 완료 (done, in-progress 등 상태 매핑)
  - 조기경보 리포트 노션 페이지 퍼블리싱 완료
- 다음 작업: 향후 파이프라인 완료 시 노션 리포트 자동 전송 연계 또는 필요 시 `python scripts/notion/notion_manager.py --all` 활용.
- 주의할 점: 노션은 인간 대상의 협업 및 결과 열람 허브이며, 공식 코드·데이터 정체성의 Source of Truth는 계속 GitHub 저장소 마크다운 문서임.


## 2026-10-29 [ANTIGRAVITY / llm-analysis · alert-scoring & tev1 10건 불일치 감사]

- 한 일:
  1. `scripts/analysis/analyze_signal_gap.py`의 근거 문장 리스트 정규화(`_normalize_evidence_phrases`) 및 비정치·문화·스포츠 기사 오탐 차단 프롬프트(`_build_news_digest`) 고도화
  2. `scripts/validation/backtest_tev1.py`를 5대 핵심 감시축 10건 동결 사례로 확장하고, 결정론적 `calculate_alert_assessment()` 산식과 `tev1` 판정 간의 불일치(Discrepancy) 자동 감사 실행 (`data/tev1_backtest_results.json`)
  3. `docs/current/LLM_SYSTEM_SUMMARY.md` (§13) 및 `docs/current/VALIDATION_PLAN.md` (§12)에 10건 대조 결과표 및 3대 불일치 패턴 실증 기록 반영
- 바꾼 파일: `scripts/analysis/analyze_signal_gap.py`, `data/signal_gap/signal_gap_analysis.json`, `scripts/validation/backtest_tev1.py`, `data/tev1_backtest_results.json`, `docs/current/LLM_SYSTEM_SUMMARY.md`, `docs/current/VALIDATION_PLAN.md`, `AGENT_SYNC.md`, `project-handoff.md`
- 확인한 것:
  - 러시아(`yandex-gpt-5-lite:8b`) 인용문 병합 오류 해결로 정상 `'경보'`(괴리도 85.0, 위험 점수 69.7) 산출 확인
  - 10건 백테스트 전체 호출 성공(일치 5건, 불일치 5건): 단일 출처 미검증(`UNVERIFIED`) 사례 2건은 산식이 `'확인 필요'`로 방어하고, 일상적 동맹 군수 발표(`BT-2026-ALLY-02`)에서 `tev1`이 `CROSS_VERIFIED` 문자열에 과민 반응해 `WARNING` 오탐을 낸 것을 산식이 `'관찰(NORMAL)'`로 방어함을 실증함
- 다음 작업: 불일치 발생 사례(`formula_vs_tev1_discrepancy = true`)를 `pending_human_review.csv` 우선 검수 대기열과 자동 연동.
- 주의할 점: `tev1`은 공식 Alert Level 공급원이 아닌 보조 비교 판정기이며, 산식과 불일치 시 반드시 사람 검수(`human_review_required = true`)를 거침.
