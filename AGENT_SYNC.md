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

## Synchronization Protocol

Cursor / ANTIGRAVITY / 로컬 터미널이 **같은 폴더**(Desktop Junction → `C:\dev\international-analysis`)를 쓰더라도, **대화 컨텍스트·미커밋·fetch 시점**이 다르면 “최신”이 어긋나 보인다. 아래 두 모드를 구분한다.

### A. 상태 확인 동기화 (기본 — “동기화해줘 / 동기화된 내용 확인해봐”)

구현·Notion 전체 재발행을 **하지 않는다**. 항상 이 순서로 **짧게** 보고한다.

1. `git fetch origin` (및 `desktop-local` remote가 있으면 `git fetch desktop-local`)
2. tip 확인: `git log -1 --oneline` · `git status -sb` · origin/desktop-local tip이 HEAD와 같은지
3. `AGENT_SYNC.md` Active Work Board 상단 + 최신 handoff 날짜 줄만 요약
4. **미커밋/untracked**가 있으면 파일 목록만 명시 (커밋하지 말 것 — 사용자가 요청할 때만)
5. 보고 형식(고정):
   - **tip** (hash + subject)
   - **origin / desktop-local 일치 여부**
   - **지난 확인 이후 새 커밋** (있으면 3~8줄)
   - **보드 상단 변경** (있으면)
   - **워킹트리 dirty** (없으면 “깨끗”)

진실의 원천은 **git tip**이다. 에이전트 대화 요약보다 tip을 우선한다.

### B. Trio-Sync (명시 요청만 — “트리오 동기화 / Notion까지 / MD·GitHub·Notion 전부”)

사용자가 **Trio / Notion까지 / 3대 플랫폼**을 명시한 경우에만 아래를 순차 실행한다.

1. **마크다운(MD) 문서 최신화**:
   - `AGENT_SYNC.md`: 작업 보드 상태 갱신, 세션 Handoff·동기화 이력 기록.
   - 필요 시 `PROJECT_CONTEXT.md`, `docs/current/*` 정합.
2. **Notion** (`scripts/notion/notion_manager.py --all` 또는 동등):
   - 작업 보드 · MD 문서 보관소/이력 · 조기경보 리포트.
3. **GitHub**:
   - 관련 파일만 stage → commit → `git push origin <branch>` (비밀·`.env` 제외).

### 멀티 에이전트 운영 한 줄

| 역할 | 규칙 |
| --- | --- |
| ANTIGRAVITY | 구현 후 **commit + push** + `AGENT_SYNC` handoff 한 블록 |
| Cursor | 세션 시작·“동기화” 요청 시 **§A 상태 확인**부터. 구현은 Board의 in-progress 파일과 겹치지 않게 |
| 로컬 사용자 | 헷갈리면 `git fetch origin && git log -1 --oneline` — 그 tip이 최신 |

복사해 쓸 프롬프트: `docs/SESSION_PROMPTS.md` **§ Sync Status**.

---

## Active Work Board

작업을 시작하기 전에 아래 표에 한 줄을 추가하거나 기존 줄을 갱신한다.

| Status | Owner | Area | Files | Task | Last Updated |
| --- | --- | --- | --- | --- | --- |
| done | ANTIGRAVITY | preprocessing / nlp-event-tuple-and-language-labeling | scripts/automation/preprocess_signals.py, scripts/pipeline/bridge_preprocess_lanes.py, data/automation/* | 텍스트마이닝·자연어처리 연계: 5W1H 정형 이벤트 튜플(who/action/target/where/when/threat_severity) 자동 추출기 및 ISO-639 다국어 라벨링(10개 언어 감지·교차언어 클러스터 지표) 구현 완료 | 2026-11-13 |
| done | ANTIGRAVITY | agent-ops / hermes-optimization | `config.yaml`, `SOUL.md`, `nul` 삭제 | Hermes Agent 추론 엔진 전면 교체(Groq Qwen 27B ➔ Google Gemini 3 Flash Preview 100만 토큰), SOUL.md 프로젝트 맵 주입, Windows nul 장치 충돌 제거 및 백그라운드 게이트웨이(PID: 8780) 정상 재기동 완료 | 2026-11-12 |
| done | ANTIGRAVITY | agent-ops / hermes-discord-mcp | `AGENTS.md`, `config.yaml`, `SOUL.md`, `docs/current/AI_AGENT_SESSION_PROMPT.md`, `docs/SESSION_PROMPTS.md` | Hermes Agent 인프라 구축, Discord 모바일 원격 연동, MySQL MCP 연동, 토큰 최적화 및 AI 에이전트 전담 세션(세션 10) 분리 인수인계 완료 | 2026-11-12 |
| done | ANTIGRAVITY | collection / semiconductor-value-chain | scripts/collection/fetch_semiconductor_market.py, data/semiconductor_market/*, pp.py | 반도체 3대 밸류체인(필라델피아SOX·NVDA·TSMC·하이닉스 / 4대 독점장비 ASML·AMAT·LRCX·KLAC / 신에츠 웨이퍼·희토류 / TrendForce DRAM·GDDR 현물가) 통합 수집기 구축 및 관제센터 연동 완료 | 2026-11-10 |
| done | Cursor Agent / preprocess | preprocessing / standard-refresh | `scripts/pipeline/bridge_preprocess_lanes.py`, `data/automation/canonical_signals_latest.json`, `data/automation/preprocess_*_latest.json`, `AGENT_SYNC.md` | standard 전처리 재실행 완료: 795→373 클러스터·223 배제. high는 기존 최신 유지 | 2026-11-10 |
| done | ANTIGRAVITY | workspace / cleanup-and-korean-labeling | `00_프로젝트_핵심문서`, 01~06 정션, `.gitignore` | 불필요 Docker/Airflow/임시파일 18종 삭제 및 직관적인 7대 한글 번호표 폴더 구축 완료 (핵심 MD 파일 4종 한글화 보관함 연동) | 2026-11-10 |
| done | ANTIGRAVITY | collection / us-tech-politics-expansion | `scripts/collection/fetch_bluesky_public.py`, `scripts/collection/fetch_signal_gap_rss.py`, `scripts/automation/preprocess_signals.py` | 미국 뉴스·기술안보 수집망 보강: 젠슨 황/엔비디아 스파이 의혹 첩보전 및 미 중간선거/의회/CHIPS Act 쿼리·RSS 신설 (57개 정형 클러스터 및 13개 소스 TIER_1 군집 형성 검증) | 2026-11-10 |
| done | Cursor / Control Tower | sync / multi-agent-status-protocol | `AGENT_SYNC.md`, `docs/SESSION_PROMPTS.md`, `.cursor/rules/agent-sync-status.mdc` | 「동기화해줘」= §A tip/보드/dirty 짧은 보고 고정. Trio는 명시 시에만. 타 세션용 Sync Status 프롬프트 등록 | 2026-11-09 |
| done | ANTIGRAVITY | collection / zero-byte-multimodal-collectors | `scripts/collection/fetch_telegram_public.py`, `scripts/collection/fetch_bluesky_public.py`, `scripts/collection/fetch_signal_gap_rss.py`, `scripts/collection/gov_announcements_collector.py`, `config/source_registry/*` | 0-Byte 무다운로드 멀티모달 수집기 4종 고도화(Telegram Photo/Video/지도단문 보존, Bluesky embed.images/alt_texts/video, RSS/Gov media:content·enclosure·PDF 보존) 및 34개 글로벌 싱크탱크·독립언론 확장(Standard 멀티모달 클러스터 35→120건, High 9→23건) | 2026-11-06 |
| done | ANTIGRAVITY | preprocessing / multimodal-stage1 | `scripts/automation/preprocess_signals.py`, `scripts/pipeline/bridge_preprocess_lanes.py`, `docs/current/PREPROCESSING_SESSION_PROMPT.md` | 1단계 무다운로드 멀티모달(이미지·영상·문서 URL & Alt-Text 추출, 시각노이즈/밈 필터링, 4대 시각 모달리티 태깅) 구축 및 최신 725건(Standard 339 / High 35 클러스터) 정제·수집 세션 가이드라인 수립 완료 | 2026-11-06 |
| done | Cursor / Validation·QA | validation / multi-judge-criteria | `docs/current/VALIDATION_PLAN.md` (§10.4), `docs/evidence/early_warning_backtest_report.md`, `AGENT_SYNC.md` | 검증단(tev1/Gemma/DeepSeek) 직교 판정·블라인드 Stage1/2·트리거·KPI 문서화. 외부 자문 합의 반영. Trio-Sync | 2026-11-05 |
| done | ANTIGRAVITY | collection / bluesky-telegram-integration | `scripts/collection/fetch_bluesky_public.py`, `scripts/collection/fetch_telegram_public.py`, `scripts/collection/run_phone_collector.py`, `dags/early_warning_pipeline_dag.py` | 블루스카이(AT Protocol 8대 쿼리) 공식 수집기 신설, 텔레그램 OSINT 경량화 및 S20 울트라 8대 수집기 체제 확장 완료 | 2026-11-05 |
| done | ANTIGRAVITY | preprocessing / high-purity-engine | `scripts/automation/preprocess_signals.py`, `scripts/pipeline/bridge_preprocess_lanes.py`, `data/automation/*high_purity*` | 고순도 모드(`--purity-mode high`) + 신규 Bluesky·Telegram 8대 수집 체제(451건) 브릿지 연동 완료 (Standard 242건 / High-Purity 29개 핵심 클러스터 압축) | 2026-11-05 |
| done | ANTIGRAVITY | preprocessing / signal-filtering | `scripts/automation/preprocess_signals.py`, `scripts/pipeline/bridge_preprocess_lanes.py`, `data/automation/*` | 4단계 다국어 전처리 고도화(7개국어+CJK 노이즈·외교의전 배제, 정규화, 중복군집화, 5대해협·한국6대공급망 태깅) 및 4대 레인 브릿지 구현 완료 | 2026-11-03 |
| done | Cursor Agent / collection | sync / trio-platform + edge-verify | `AGENT_SYNC.md`, Notion hub/board/docs/report, GitHub `cursor/actions-light-collection` | 폰 `--sync-git` 원격 검증(0a45c12·6/6·gov path) 후 Trio-Sync(MD→Notion→GitHub) | 2026-11-03 |
| done | Cursor Agent / collection | edge / phone-git-sync-harden | `scripts/collection/run_phone_collector.py`, `start_phone.sh` | Termux git 작성자·rebase abort·push 힌트 보강. 사용자 수정·푸시 후 `data(edge)` 3커밋·gov_announcements 원격 반영 확인 | 2026-11-03 |
| done | ANTIGRAVITY | orchestration / edge-to-core-pipeline | `scripts/collection/run_phone_collector.py`, `dags/early_warning_pipeline_dag.py`, `data/phone_collector_status.json` | 엣지-코어 2-Tier 분산 파이프라인 완결: S20 울트라 6대 수집기(6/6 성공) 실기기 Git 자동 푸시 및 PC 동기화 검증 완료 | 2026-11-03 |
| done | ANTIGRAVITY | data-collection / packet-a-federal-register | `scripts/collection/fetch_federal_register.py`, `config/source_registry/government_sources.yaml`, `scripts/run_pipeline.py` | 패킷 A Federal Register 공식 REST API 선택 수집기 구현 및 source_registry 연동 완료 | 2026-11-03 |
| done | ANTIGRAVITY | preprocessing / session-prompt | `docs/current/PREPROCESSING_SESSION_PROMPT.md`, `docs/SESSION_PROMPTS.md` | 비정형 데이터 전처리 및 신호 필터링 전담 세션 분리 프롬프트 작성 및 등록 완료 | 2026-11-02 |
| done | ANTIGRAVITY | collection / 24-7-edge-runner | `scripts/collection/run_phone_collector.py`, `start_phone.sh`, `scripts/collection/fetch_signal_gap_rss.py` | 갤럭시 S20 울트라(Termux) 24/7 무중단 자동 수집 러너 구축, pandas 의존성 제거 및 5/5 수집 검증 완료 | 2026-11-03 |
| done | Cursor / Control Tower | control-tower / scope | `docs/current/PROJECT_PLAN.md`, `docs/current/DATA_COLLECTION_GUIDE.md`, `AGENT_SYNC.md` | 미국 국내·동맹·경쟁/대립축 6대 감시축 확정(예측 금지). 패킷 A+B 동시 착수 지시 | 2026-10-30 |
| done | Cursor / Control Tower | runtime / python-3.13 | `.venv`, `.python-version`, `requirements.txt`, `README.md`, `PROJECT_CONTEXT.md`, `docs/SESSION_PROMPTS.md` | 표준 런타임 Python 3.13(.venv) 전환 및 세션 프롬프트 정리 — PR #5 | 2026-10-30 |
| done | Cursor / Control Tower | sync / trio-platform | `AGENT_SYNC.md`, Notion hub/history/board, GitHub PR #5 | 트리오 동기화(MD→Notion→GitHub/PR) 완료 | 2026-10-30 |
| done | Cursor / Control Tower | automation / cloud-light-collection | `.github/workflows/daily_pipeline.yml`, `docs/current/DATA_COLLECTION_GUIDE.md`, `AGENT_SYNC.md` | GitHub Actions 일일 수집 경로 복구 → light RSS lane (gov/WH/signal-gap/financial). LLM·DB·GDELT 제외 | 2026-10-31 |
| done | Cursor / Control Tower | dashboard / local-html-console | `scripts/console/app.py`, `scripts/console/static/index.html`, `README.md`, `docs/current/DATA_COLLECTION_GUIDE.md` | 로컬 통합 HTML 콘솔 프로토타입(원클릭 run_pipeline/light). 배포·Airflow·LLM 미포함 | 2026-11-02 |
| done | Cursor Agent / collection | data-collection / gov-path-fix | `scripts/collection/gov_announcements_collector.py`, `scripts/db/build_database.py`, `scripts/collection/run_phone_collector.py` | 정부 발표 산출 경로 `data/gov_announcements/` 통일(폰 --sync-git 누락 수정) + rebase 실패 시 push 중단 | 2026-11-03 |
| done | Cursor Agent / collection | data-collection / US-domestic + allies | `config/source_registry/government_sources.yaml`, `config/source_registry/SCHEMA.md`, `scripts/collection/*` | 패킷 A+B registry + Federal Register는 ANTIGRAVITY가 선택 수집기까지 연결. 경로 수정만 후속 | 2026-11-03 |
| done | Cursor Agent / collection | data-collection / X public API | `scripts/collection/fetch_x_public.py`, `scripts/run_pipeline.py`, `config/source_registry/opinion_sources.yaml`, `docs/current/DATA_COLLECTION_GUIDE.md` | 공식 X recent search 선택 수집기(`--with-x`). 기본 파이프라인 미호출·종량제 고지 | 2026-11-02 |
| done | Cursor Agent / preprocess | automation / noise-relevance-filter | `scripts/automation/preprocess_signals.py`, `AGENT_SYNC.md` | 연예·스포츠·광고·비지정학 기사 hard-drop + 관련도 관문 강화 (LLM 전 필수 필터) | 2026-11-02 |
| done | ANTIGRAVITY | data-collection / competitor-axis roles | `config/source_registry/*`, signal_gap 소스 | 패킷 C: relationship_role 태깅·OFAC/BIS registry (A/B 스키마 정렬 후) | 2026-11-02 |
| done | ANTIGRAVITY | db / pipeline / cross-verification | `scripts/run_pipeline.py`, `scripts/db/load_cross_verification_to_db.py`, `scripts/db/create_views.sql` | 해협 센서·공급망 사건 교차검증의 DB 적재와 대시보드 뷰 연동 | 2026-10-02 |
| done | ANTIGRAVITY | data-collection / supply-chain-sensors | `scripts/collection/fetch_maritime_chokepoints.py`, `scripts/analysis/cross_verify_events.py`, `data/maritime_chokepoints/`, `data/event_cross_verification/` | 해협·시장 센서 수집 및 복수 계통 교차검증 | 2026-10-02 |
| done | ANTIGRAVITY | data-collection / public-opinion | `scripts/collection/fetch_local_opinions.py`, `scripts/collection/fetch_google_trends.py`, `data/local_opinions/`, `data/google_trends/` | 대안 로컬 여론·검색 트렌드 센서 구축 | 2026-09-29 |
| in-progress | ANTIGRAVITY | dashboard / ui | `scripts/dashboard/streamlit_dashboard.py` | Streamlit 대시보드 유지보수 및 고도화 | 2026-09-28 |
| done | Cursor / dashboard-report | dashboard / html-ui | `scripts/dashboard/generate_dashboard_v2.py`, `output/dashboard/` | Information 축 과장 표현 교정(국민 여론·하드코딩 Critical·WATCH 후보 제거) 후 HTML 재생성 | 2026-10-28 |
| done | ANTIGRAVITY | llm-pipeline / 3-tier-canonical-pivot | `scripts/analysis/analyze_signal_gap.py`, `scripts/analysis/analyze_middle_east_osint.py`, `scripts/analysis/analyze_ib_insights.py`, `scripts/validation/verify_model_consensus.py`, `data/signal_gap/signal_gap_analysis.json` | 16GB 갤북5 프로 최적화 3단계 순차 파이프라인(Qwen2.5:7b 다국어 추출 → EXAONE 3.5 한국어 브리핑 & Llama3.1:8b 영어 브리핑) 구축 및 실증 완료 | 2026-11-02 |
| done | ANTIGRAVITY | llm-analysis / alert-scoring | `scripts/validation/backtest_tev1.py`, `scripts/analysis/analyze_signal_gap.py`, `data/tev1_backtest_results.json`, `scripts/dashboard/generate_dashboard_v2.py` | tev1 10건 동결 사례 시운전 10/10 호출 완결(일치 5/불일치 5 감사 트리거), 대시보드 결측치 가드레일 보강 | 2026-11-02 |
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
| done | ANTIGRAVITY | sync / trio-platform-sync | `AGENT_SYNC.md`, `assets/`, GitHub, Notion | 전체 파이프라인 아키텍처 다이어그램 및 3대 플랫폼(MD·GitHub·Notion) 일괄 동기화 | 2026-11-02 |
| done | ANTIGRAVITY | orchestration / airflow-docker-setup | `docker-compose.yaml`, `dags/early_warning_pipeline_dag.py`, `docs/current/AIRFLOW_SETUP_GUIDE.md`, `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md` | Docker 기반 Apache Airflow 2.10.2 표준 컨테이너 환경 구축, 4-Lane 병렬 수집 DAG 시운전 검증 및 포트폴리오 엔지니어링 서사 반영 | 2026-11-02 |
| done | ANTIGRAVITY | validation / tev1-role-clarification | `scripts/validation/backtest_tev1.py`, `scripts/automation/preprocess_signals.py`, `docs/current/VALIDATION_PLAN.md` | 번역·분석 모델(Qwen/EXAONE/Llama)과 독립 검증 모델(tev1)의 엄격한 역할 분리 및 다국어 5단계 전처리 필수화 확립 | 2026-11-02 |
| done | ANTIGRAVITY | validation / multi-model-suite-setup | `Ollama`, `docs/current/VALIDATION_PLAN.md`, `docs/current/LLM_SYSTEM_SUMMARY.md` | tev1 보완 다자간 검증단 구축: DeepSeek-R1:7b(추론·비판) 및 Gemma2:9b(사실성 감사) 다운로드 및 6대 모델 역할 체계 완결 | 2026-11-05 |
| done | ANTIGRAVITY | data-collection / latin-america-expansion | `scripts/collection/*`, `scripts/automation/*`, `config/source_registry/*`, `docs/current/*` | 중남미 대륙 감시 강화: 브라질 대선·룰라정부·원자재(원유/대두/리튬) 및 파나마 운하 병목 센서 구축 | 2026-10-29 |
| done | ANTIGRAVITY | integration / notion-radar-live | `scripts/notion/push_radar_signal.py`, `.env` | 신규 생성된 실시간 글로벌 이상 징후 레이더 DB 스키마 주입 및 실시간 신호 전송 연동 완료 | 2026-10-29 |

Status 값은 `open`, `in-progress`, `review-needed`, `done`, `blocked` 중 하나를 쓴다.

2026-11-13 [ANTIGRAVITY / preprocessing · 5W1H 정형 이벤트 튜플 추출 및 ISO-639 다국어 라벨링 엔진 구현 Handoff]
- 한 일:
  1. 텍스트마이닝·자연어처리(NLP) 연계 5W1H 이벤트 튜플 추출기(`extract_event_tuple`) 구현:
     - 비정형 기사 본문/제목에서 행위자(`who`), 행위(`action`), 대상(`target`), 장소(`where`), 시점(`when`), 공급망 영향(`supply_impact_tags`), 위협 심각도(`threat_severity`: CRITICAL_DISRUPTION, HIGH_DISRUPTION 등)를 정밀 정형화하여 `canonical_signals` 스키마에 통합.
  2. ISO-639 다국어 감지 및 라벨링 엔진(`detect_language_detailed`) 구현:
     - 유니코드 스크립트(한글 ko, CJK한자 zh, 가나 ja, 아랍어 ar, 키릴 ru) 및 라틴 기능어(fr, de, es, pt, en)를 통한 고속·경량 10개 언어 라벨링.
     - 클러스터별 주 언어(`primary_language`), 감지된 언어군(`detected_languages`), 다국어 교차 보도 여부(`is_cross_lingual`) 메트릭 산출.
  3. 전체 818건 원시 수집 데이터에 대해 Standard 및 High-Purity 모드 전처리 파이프라인 완결:
     - Standard: 818건 -> 355개 클러스터 (10개 언어 감지, 교차언어 클러스터 6건, 치명적 위협 6건).
     - High-Purity: 818건 -> 66개 핵심 클러스터 (6개 언어 감지, 치명적 위협 4건).
- 바꾼 파일: `scripts/automation/preprocess_signals.py`, `scripts/pipeline/bridge_preprocess_lanes.py`, `data/automation/canonical_signals_latest.json`, `data/automation/canonical_signals_high_purity_latest.json`, `data/automation/preprocess_*_latest.json`, `AGENT_SYNC.md`.
- 확인한 것: `--self-test` 성공 통과, Standard 및 High-Purity 정상 종료 (exit code 0), 호르무즈 유조선 피격 사건 5W1H 팩트 튜플 추출 실증 검증 완료.
- 다음 작업: 하류 세션(LLM 분석 및 대시보드)에서 정형 튜플을 소비하여 팩트 요약 브리핑 및 교차언어 가중치 반영.

2026-11-12 [ANTIGRAVITY · Hermes Agent 인프라 구축 및 AI 에이전트 전담 세션 분리 Handoff]
- 한 일: 
  1. Hermes Agent 0.19.0 및 Discord 봇(헤르메스#3484) 게이트웨이 연동 완료 (아이패드 디스코드 원격 관제).
  2. 로컬 MySQL(localhost:3306, international_analysis 45개 테이블) MCP 서버(uvx mysql_mcp_server) 연동 및 조회 도구 3종 검증 완료.
  3. Groq 무료 티어(7,000 ITPM 한도) 호환을 위한 시스템 프롬프트 및 도구 경량화(16,130 토큰 -> ~4,500 토큰 축소, 28개 미사용 도구 제거).
  4. 다중 모델 벤치마크 및 특성 정리 (Groq qwen3.8-27b / gpt-oss-120b 분당 토큰 제한 분석, Google Gemini Flash 100만 컨텍스트 무제한 대안 확보).
  5. AI 에이전트 인프라·운영 업무 전담 세션 분리를 위한 인수인계 문서(`docs/current/AI_AGENT_SESSION_PROMPT.md`) 및 세션 프롬프트(`docs/SESSION_PROMPTS.md` §10) 신설.
- 바꾼 파일: `docs/current/AI_AGENT_SESSION_PROMPT.md`, `docs/SESSION_PROMPTS.md`, `AGENTS.md`, `AGENT_SYNC.md`, `SOUL.md`, `config.yaml`.
- 확인한 것: Discord 봇 정상 로그인, Hermes Desktop 게이트웨이 기동, MySQL MCP 7개 도구 등록, Groq/Gemini 한국어 요약 200 OK.
- 다음 작업 (AI 에이전트 전담 세션 10에서 진행): 
  1. Groq 분당 토큰 한도(7,000 TPM) 병목 없는 대화 환경을 위해 Gemini Flash(100만 TPM) 또는 모델 튜닝 확정.
  2. 디스코드에서 자연어로 전체 수집기 실행 및 MySQL 쿼리 호출 시나리오 안정화.
- 주의할 점: Hermes Desktop GUI 실행 중 터미널에서 `hermes gateway run` 중복 실행 시 포트 충돌 주의. 유료 과금 모델 사용 금지.

2026-11-12 [ANTIGRAVITY / agent-ops · Hermes 추론 엔진 고지능화(Gemini 3 Flash) 및 게이트웨이 무장애 최적화]
- 한 일:
  1. Groq 무료 티어(분당 7,000 ITPM 한도)로 인한 225초 지연 및 429/413 연쇄 장애, 세션 자동 리셋 문제를 해결하기 위해 기본 추론 엔진을 `gemini-3-flash-preview` (Google AI Studio 무료 티어, 100만 토큰 컨텍스트 및 100만 TPM)로 전면 교체 (`config.yaml`).
  2. Fallback 모델 체계 정비: 1차 `gemini-3.1-flash-lite`, 2차 로컬 Ollama `qwen2.5:7b`로 완전 무과금 고지능 다중화.
  3. `SOUL.md` 페르소나 전면 고도화: 단순 2줄에서 벗어나 프로젝트 핵심 지식(OSINT 조기경보 시스템) 및 사용자의 "진행 현황/상태" 질문 시 `AGENT_SYNC.md`와 `PROJECT_CONTEXT.md`를 즉시 1회 확인하여 3단계로 명쾌하게 브리핑하도록 전담 가이드 장착.
  4. 윈도우 특수 장치 버그 파일(`nul`) 영구 제거 (Hermes 자동완성 relpath 크래시 차단).
  5. 기존 좀비 게이트웨이 종료 및 신규 백그라운드 게이트웨이(PID: 8780) 무장애 기동 검증 완료 (`Model context warmed: gemini-3-flash-preview -> 1048576 tokens`, `Discord connected as 헤르메스#3484`).
- 바꾼 파일: `C:\Users\홍준기\AppData\Local\hermes\config.yaml`, `C:\Users\홍준기\AppData\Local\hermes\SOUL.md`, `nul` 삭제, `AGENT_SYNC.md`.
- 확인한 것: Discord 게이트웨이 정상 연결 확인, Google AI Studio 공식 API 연동 통과.
- 다음 작업: 디스코드/데스크톱에서 체감 속도 및 답변 퀄리티 검증, 수집/전처리 Cron 스케줄러 자동화 설계.

2026-11-10 [Cursor Agent / preprocess · standard 전처리 재실행]
- 한 일: 오늘 갱신된 RSS·Bluesky 등 원시 795건에 대해 `bridge_preprocess_lanes.py --purity-mode standard` 재실행. 노이즈·저관련 223건 배제 후 373개 canonical 클러스터 산출(Tier-1 32 / Tier-2 56 / 멀티모달 129·첨부 171). high-purity 산출물은 기존 최신 유지.
- 바꾼 파일: `data/automation/canonical_signals_latest.json`, `data/automation/preprocess_rejects_latest.json`, `data/automation/preprocess_summary_latest.json`, `AGENT_SYNC.md` (+ 워킹트리에 있던 high_purity automation 산출물도 함께 동기화).
- 확인한 것: 배제 사유 low_geopolitical_relevance=195, entertainment_sports_noise=10, ad_or_soft_section=11. 해협·반도체 태그 정상. Alert Level 미설정·UNVERIFIED 유지.
- 다음 작업: 낡은 Telegram/local_opinions/Reddit·Trends 재수집 후 필요 시 standard/high 재브릿지. LLM/tev1는 분석·검증 세션 영역.
- 주의할 점: 수집 원본은 수정하지 않음(read-only). 다른 세션의 미관련 dirty(삭제·정션·수집기)는 이 커밋에 넣지 않음.

2026-11-09 [Cursor / Control Tower · multi-agent sync status protocol]
- 한 일: 「동기화해줘」기본 동작을 §A 상태 확인(fetch→tip→보드→dirty)으로 고정. Trio-Sync는 명시 요청만. `SESSION_PROMPTS` Sync Status 프롬프트 + Cursor alwaysApply 규칙 추가.
- 바꾼 파일: `AGENT_SYNC.md`, `docs/SESSION_PROMPTS.md`, `.cursor/rules/agent-sync-status.mdc`.
- 확인한 것: Desktop Junction = `C:\dev\international-analysis`. tip 우선, 대화 기억 단독으로 최신 단정 금지.
- 다음 작업: 새 Cursor/ANTIGRAVITY 세션 첫 메시지에 Sync Status 프롬프트(또는 공통 규칙 4–7) 사용.
- 주의할 점: §A에서는 무단 커밋·구현 금지.

2026-11-06 [ANTIGRAVITY / collection · 0-Byte 무다운로드 멀티모달 수집기 4종 고도화 및 34개 글로벌 싱크탱크·탐사미디어 확장]
- 한 일:
  1. [수집 세션 ➔ 전처리 세션 간 비정형·멀티모달 인터페이스 규약]에 맞춰 0-Byte 무다운로드 원칙으로 4대 핵심 수집기 멀티모달 메타데이터 추출 확장:
     - `scripts/collection/fetch_telegram_public.py`: 메시지 래퍼(`.tgme_widget_message_wrap`) 파싱으로 전환하여 `Photo_URL`(`a.tgme_widget_message_photo_wrap` 배경 URL), `Video_URL`(`video` src 및 `i.tgme_widget_message_video_thumb`), `Has_Media` 추출. 전황 지도·현장 사진 단독 게시물(텍스트 10자 미만)도 유실 없이 수집 및 맥락 태그 보강(50건 중 멀티모달 18건 포착).
     - `scripts/collection/fetch_bluesky_public.py`: `post.embed` 및 `record.embed`에서 `media_urls`(`embed.images[].thumb`/`fullsize`), `alt_texts`(`embed.images[].alt` 대체 텍스트), `has_video`(`app.bsky.embed.video`) 추출(고유 50건 중 이미지/비디오 9건, 외부 링크카드 34건 포착).
     - `scripts/collection/fetch_signal_gap_rss.py` & `scripts/collection/gov_announcements_collector.py`: `<media:content>`, `<media:thumbnail>`, `<enclosure>`, 본문 내 `<img>`/`<video>` 및 `.pdf` 원문 링크를 텍스트 절단(`[:500]`) 전에 우선 추출하여 보존하고, 아바타·로고·1x1 트래킹 픽셀·이모지 아이콘은 수집 단계에서 즉시 배제(신호 괴리 RSS 334건 중 멀티모달 137건 포착).
  2. 권위주의/감시국가(러시아·중국·이란) 독립 탐사 미디어, 남미·멕시코, 일본 및 10대 글로벌 싱크탱크(ISW, CSIS, ASPI, 카네기 유라시아, 윌슨센터, WOLA, 미주대화기구, 도쿄재단, PIIE, RUSI) 등 총 34개 피드 연동 완결 (`config/source_registry/expert_feeds.yaml`, `local_media_feeds.yaml`).
  3. 전처리 브릿지(`bridge_preprocess_lanes.py`) 연동 검증 완료:
     - `standard` 모드: 752건 원시 입력 -> 346개 클러스터, **멀티모달 포함 클러스터 35건 ➔ 120건(첨부 162개: `image` 108, `external_card` 25, `document_pdf` 24, `video` 5)으로 3.4배 증가**, 5대 해협 전원 감지(호르무즈 12, 바브엘만데브 7, 말라카 2, 보스포루스 4, 파나마 3, 대만해협 4).
     - `high` 고순도 모드: 752건 원시 입력 -> 44개 핵심 클러스터, **멀티모달 포함 클러스터 9건 ➔ 23건(첨부 37개)으로 2.5배 증가**.
  4. Trio-Sync(MD 문서 + Notion + GitHub) 실행.
- 바꾼 파일: `scripts/collection/fetch_telegram_public.py`, `scripts/collection/fetch_bluesky_public.py`, `scripts/collection/fetch_signal_gap_rss.py`, `scripts/collection/gov_announcements_collector.py`, `config/source_registry/expert_feeds.yaml`, `config/source_registry/local_media_feeds.yaml`, `data/signal_gap/*`, `data/bluesky_public/*`, `data/gov_announcements/*`, `data/automation/*`, `AGENT_SYNC.md`.
- 다음 작업: S20 울트라 엣지 노드 `git pull` 후 0-Byte 멀티모달 8대 수집 체제 무중단 가동 및 LLM/검증 세션의 멀티모달 메타데이터 소비 연동.

2026-11-06 [ANTIGRAVITY / preprocessing · 1단계 무다운로드 멀티모달(이미지·영상·문서) 전처리 구축 및 수집 가이드라인 확립]
- 한 일:
  1. `scripts/automation/preprocess_signals.py`에 1단계 무다운로드 멀티모달 메타데이터 정형화(`extract_multimodal_metadata`) 및 시각 노이즈 필터링 구현:
     - 원본 이미지·영상 바이너리를 다운로드하지 않고 HTML(`<img>`, `<video>`, `<iframe>`), 인라인 미디어 링크, 수집기 명시 필드(`pdf_url`, `external_link`, `external_title`, `media_urls`, `alt_texts`)에서 첨부 메타데이터(`media_attachments`)와 대체 텍스트(`visual_alt_texts`) 추출.
     - 대체 텍스트(`alt_text`)를 본문 엔티티 태깅 및 클러스터링 토큰화에 합류시켜 사진/외부카드 설명 속 해협·공급망 키워드 복원.
     - 시각 노이즈 URL(`is_visual_noise_url`: 아바타, 아이콘, 로고, 1x1 트래킹 픽셀, 배너 광고, Giphy/Tenor/9gag 밈 도메인) 및 밈/유머짤(`VISUAL_MEME_OR_CLICKBAIT_KEYWORDS`) 자동 차단.
     - 4대 시각 모달리티(`SATELLITE_IMAGERY`, `TACTICAL_MARITIME_MAP`, `FIELD_PHOTO_VIDEO`, `OFFICIAL_DOCUMENT_PDF`) 태깅 및 `visual_verification_state: "UNVERIFIED_METADATA_ONLY"` 가드레일 적용.
  2. `scripts/pipeline/bridge_preprocess_lanes.py` 멀티모달 스키마(`v1.1_multimodal`) 확장 및 최신 725건 실데이터 정제:
     - `standard` 모드: 725건 -> 339개 클러스터 (멀티모달 포함 35개 클러스터, 첨부 42건: `external_card` 21, `document_pdf` 20, `video` 1).
     - `high` 고순도 모드: 725건 -> 35개 핵심 클러스터 (멀티모달 포함 9개 클러스터, 첨부 11건, 호르무즈 7·대만해협 4·바브엘만데브 3·보스포루스 3·파나마 2).
  3. `docs/current/PREPROCESSING_SESSION_PROMPT.md`에 [수집 세션 ➔ 전처리 세션 간 비정형·멀티모달 인터페이스 규약] 명문화.
- 바꾼 파일: `scripts/automation/preprocess_signals.py`, `scripts/pipeline/bridge_preprocess_lanes.py`, `docs/current/PREPROCESSING_SESSION_PROMPT.md`, `data/automation/*`, `AGENT_SYNC.md`.
- 다음 작업: 데이터 수집 담당 세션에서 블루스카이(`embed.images[].alt`/`thumb`), 텔레그램(`Photo_URL`/`Video_URL`), RSS(`media:content`/`enclosure`) 메타데이터 추출 필드 확장.

2026-11-05 [Cursor / Validation·QA · Trio-Sync]
- 한 일: 외부 AI 자문(Grok/ChatGPT/Gemini/DeepSeek/Kimi/Claude) 대조 후 다자간 검증 **판정 기준**을 `VALIDATION_PLAN` §10.4로 고정. 증거 리포트 과장(75%·NIST 준수) 재완화. MD→Notion→GitHub 동기화.
- 바꾼 파일: `docs/current/VALIDATION_PLAN.md`, `docs/evidence/early_warning_backtest_report.md`, `AGENT_SYNC.md`.
- 확인한 것: 축 분리(tev1 단계·Gemma claim 근거·DeepSeek 해석), tev1은 산식 단계 미열람, Stage1 블라인드 잠금, 자동 accept 금지, T1–T8 트리거, 만장일치율 KPI 제외. `validation_backtest_log` 사람 완료 행은 여전히 0에 가깝다.
- 다음 작업: LLM 세션이 §10.4 스키마·프롬프트 격리로 호출 구현(산식 변경 금지). QA는 동결 2~3건 선등록 + Stage1 표본. DB는 완료 판정만 append-only.
- 주의할 점: 3모델 다수결≠정답. tev1 10건≠Human acceptance. `SESSION_PROMPTS.md`·수집기·산식·DB DDL·대시보드 미수정. `data/tev1_backtest_results.json` 작업 트리 변경은 본 커밋에 넣지 않음.

2026-11-05 [ANTIGRAVITY / 다자간 독립 검증단 모델 확충: DeepSeek-R1 & Gemma 2 구축]
- 한 일:
  1. 단일 심판(`tev1`) 한계 극복을 위한 검증단 모델 확충:
     - `deepseek-r1:7b` (4.7GB): CoT 기반 비판적 반박(Adversarial Critic) 및 과잉 경보/논리적 비약 방어 모델 설치 완료.
     - `gemma2:9b` (5.4GB): 구글의 엄격한 사실성(Factuality/Faithfulness) 기준 원문 왜곡 검증 모델 설치 완료.
  2. 완성된 6대 오픈소스 LLM 분업 체계 확립:
     - 분석·생성 3총사: `qwen2.5:7b` (다국어 팩트 추출) ➔ `exaone3.5:7.8b` (한국어 전략 브리핑) & `llama3.1:8b` (글로벌 영문 브리핑)
     - 독립 검증단 3심제 + 산식: `tev1:latest` (의사결정 주심) + `deepseek-r1:7b` (비판관) + `gemma2:9b` (사실성 감사관) + 결정론적 산식 (수학적 가드레일)
  3. 16GB RAM 환경 보호 원칙: 검증 단계에서도 모델별 순차 호출(`keep_alive="2s"`)을 엄수하여 메모리 점유율을 상시 5GB 안팎으로 유지.
  4. 트리오 동기화 프로토콜(MD 문서 최신화 + Notion 전체 동기화 + GitHub 원격 푸시) 실행.
- 바꾼 파일: `AGENT_SYNC.md`, Ollama 모델 레지스트리, Notion 프로젝트 허브.
- 확인한 것: Ollama에 6개 모델 정상 등록 확인, Notion 3대 영역(작업 보드, 문서 보관소, 조기경보 리포트) 동기화 완료, GitHub 원격 푸시 완료.
- 다음 작업: 5대 감시축 10건 동결 사례 대상 [다자간 백테스트 엔진(Multi-Model Backtest)] 연동 및 비교 감사 리포트 산출.
- 주의할 점: 다중 모델 구동 시 반드시 순차 호출 원칙을 지키며 동시 상주를 금지함.

2026-11-05 [ANTIGRAVITY / 블루스카이(Bluesky) 공식 수집기 신설 & 텔레그램 경량화 8대 수집기 체제 완결]
- 한 일:
  1. 블루스카이(Bluesky AT Protocol) 공식 공개 수집기 신설 (`scripts/collection/fetch_bluesky_public.py`):
     - API 키나 로그인 인증이 불필요한 공식 오픈 XRPC 엔드포인트(`https://api.bsky.app/xrpc/app.bsky.feed.searchPosts`) 연동.
     - 8대 전략 감시 쿼리(호르무즈, 바브엘만데브, 대만해협, 말라카, 파나마, 대중수출통제, OFAC제재, 핵심광물) 구성.
     - 시운전 결과: 고유 지정학/물류 포스트 33건 즉시 수집, `data/bluesky_public/` 내 JSON/CSV 및 영수증 자동 저장.
     - `signal_class: online_information_environment_signal` 및 `verification_state: UNVERIFIED` 가드레일 준수.
  2. 텔레그램 공개 웹 프리뷰 OSINT 수집기 경량화 리팩토링 (`scripts/collection/fetch_telegram_public.py`):
     - 스마트폰(Termux) 및 엣지 노드 호환을 위해 무거운 `pandas` 의존성을 제거하고 순수 `requests` + `bs4` + 표준 `csv` 구조로 전면 개편.
     - 5대 핵심 공개 채널(`@rybar`, `@UaOnlii`, `@sepah_pasdaran`, `@AlArabiya`, `@army21ye`) 총 40건 수집 및 영수증 발행 완료.
  3. 전체 파이프라인 및 엣지 오케스트레이션 확장:
     - 갤럭시 S20 울트라 엣지 러너(`scripts/collection/run_phone_collector.py`): 기존 6종에서 블루스카이·텔레그램이 추가된 8종 경량 수집기 체제로 확장.
     - Airflow DAG(`dags/early_warning_pipeline_dag.py`): 13개 병렬 수집기 체제(`collect_bluesky`, `collect_telegram`, `collect_federal_register` 포함)로 정렬.
     - 통합 파이프라인(`scripts/run_pipeline.py`) 및 소스 레지스트리(`config/source_registry/opinion_sources.yaml`) 연동 완료.
- 바꾼 파일: `scripts/collection/fetch_bluesky_public.py`, `scripts/collection/fetch_telegram_public.py`, `scripts/collection/run_phone_collector.py`, `dags/early_warning_pipeline_dag.py`, `scripts/run_pipeline.py`, `config/source_registry/opinion_sources.yaml`, `AGENT_SYNC.md`.
- 확인한 것: 블루스카이 33건, 텔레그램 40건 정상 수집 및 영수증 확인, DAG 및 전체 파이프라인 py_compile 통과.
- 다음 작업: S20 울트라 실기기에서 `git pull` 후 8종 수집기 자동 실행 및 Git 푸시 확인.
- 주의할 점: SNS 데이터는 국민 여론이나 단독 Alert Level 격상용으로 사용하지 않고 정보환경 신호로만 기록.

2026-11-05 [ANTIGRAVITY / preprocessing · 고순도 모드(High-Purity Mode) 파이프라인 구축 및 검증]
- 한 일:
  1. `scripts/automation/preprocess_signals.py`에 `--purity-mode high` (고순도 전처리 엔진) 구현:
     - 1차: 노이즈/광고/외교의전 외에 `RETROSPECTIVE_OR_NON_CURRENT_KEYWORDS`(과거 회고, 자서전 도서 출간, 가정법 잡담, 부고 등) 정밀 배제 필터 구축.
     - 2차: 하드 엔티티 관문(Hard-Entity Gate) 적용 - 5대 해협, 한국 6대 공급망 품목, 또는 지정학 핵심 핫스팟+위기 이벤트가 명시된 신호만 통과시켜 일반 정치 단신 전면 차단.
     - 3차: 교차검증 신뢰도 계층화(Tier-1: 복수 출처 확인, Tier-2: 고신뢰 권위 기관 단독) 및 단일 저신뢰 출처 자동 배제.
  2. `scripts/pipeline/bridge_preprocess_lanes.py`에 `--purity-mode standard|high` CLI 인자 및 고순도 산출물 분리 저장 지원:
     - 블루스카이(33건)·경량 텔레그램(40건) 포함 4대 레인 총 451건 연동 실증: Standard 242개 클러스터(68건 배제), High-Purity 29개 초고순도 클러스터(Tier-1 9건, Tier-2 20건, 343건 배제) 생성.
     - 5대 해협(호르무즈 5건, 바브엘만데브 3건, 대만해협 4건, 파나마 2건, 보스포루스 1건) 및 핵심 공급망(반도체 12건, 원유 11건, LNG 1건) 신호 정밀 포착.
  3. 다운스트림 연계 및 안전 원칙:
     - Alert Level 임의 확정 배제 원칙 준수 (`verification_state: "UNVERIFIED"`, `alert_level_set: false`).
- 바꾼 파일: `scripts/automation/preprocess_signals.py`, `scripts/pipeline/bridge_preprocess_lanes.py`, `data/automation/canonical_signals_high_purity_latest.json`, `data/automation/preprocess_rejects_high_purity_latest.json`, `data/automation/preprocess_summary_high_purity_latest.json`, `AGENT_SYNC.md`.

2026-11-03 [ANTIGRAVITY / preprocessing · 4단계 다국어 전처리 고도화 및 4대 레인 정형화 브릿지 완결]
- 한 일:
  1. `scripts/automation/preprocess_signals.py` 4단계 파이프라인 전면 고도화:
     - Step 1: 7개 국어 + 한/중 CJK 노이즈 사전(Meduza 러시아 하키, 대만 PTT Gossiping 유흥·연예, 스폰서 UTM 등) 및 의례적 외교 수사(`DIPLOMATIC_PROTOCOL_KEYWORDS`: 축전·문화행사·엑스포 홍보 등) 분리 필터 구축. `people.com.cn`이 `people.com` 노이즈 도메인으로 오탐되던 정규식 경계 버그 수정.
     - Step 2: 7개 국어(EN, FR, PT, DE, ES, RU, AR) NFKD 악센트 제거, 아랍어(Tashkeel·Alef·Teh Marbuta) 및 키릴어(`ё→е`) 정규화, NLTK 미설치 환경에서도 동작하는 내장 7개 국어 불용어 사전(`_FALLBACK_STOPWORDS`) 및 SnowballStemmer 연동.
     - Step 3: 발행 시각 기반 72시간 시간창 가드(`_within_time_window`), 권위도·엔티티 밀도 기반 대표 헤드라인 선정, 다중 출처(`sources`, `source_types`, `observed_lanes`) 누적 군집화.
     - Step 4: 5대 해상 병목 표준코드(`CHOKEPOINT_HORMUZ`, `CHOKEPOINT_BAB_EL_MANDEB`, `CHOKEPOINT_MALACCA`, `CHOKEPOINT_BOSPHORUS`, `CHOKEPOINT_PANAMA` + `CHOKEPOINT_TAIWAN_STRAIT`) 및 한국 6대 핵심 공급망 품목(`CRUDE_OIL`, `NATURAL_GAS_LNG`, `SEMICONDUCTOR`, `RARE_EARTHS`, `BATTERY_MINERALS`, `GRAIN_FOOD`), 5대 위기 이벤트 다국어 사전 태깅.
  2. `scripts/pipeline/bridge_preprocess_lanes.py` 구현 및 스마트폰(S20 Ultra) 동기화 실데이터 검증:
     - 4대 레인 원시 레코드 378건(FAST 234, CONTEXT 60, OPINION 84, BASELINE 7) 일괄 정제 → 노이즈·비관련 49건 배제(`preprocess_rejects_latest.json`), 유효 329건을 209개 대표 클러스터(`canonical_signals_latest.json`)로 압축(다중 출처 클러스터 21개, 호르무즈 3건, 바브엘만데브 1건, 대만해협 3건, 원유 11건, LNG 1건, 반도체 14건).
- 바꾼 파일: `scripts/automation/preprocess_signals.py`, `scripts/pipeline/bridge_preprocess_lanes.py`, `data/automation/canonical_signals_latest.json`, `data/automation/preprocess_rejects_latest.json`, `data/automation/preprocess_summary_latest.json`, `docs/current/PREPROCESSING_SESSION_PROMPT.md`, `AGENT_SYNC.md`.
- 확인한 것: `--self-test`, `bridge_preprocess_lanes.py`, `auto_anomaly_scanner.py --dry-run` 모두 무결성 통과. 모든 클러스터 `verification_state="UNVERIFIED"`, `alert_level_set=false` 원칙 준수.
- 다음 작업: 교차검증 및 LLM 3-Tier 분석 세션에서 `data/automation/canonical_signals_latest.json`을 입력으로 소비하도록 연결.
- 주의할 점: 수집기(`scripts/collection/*`), Airflow DAG, DB DDL, 대시보드 UI는 수정하지 않음. 단일 출처 신호의 임의 경보 격상 금지.

2026-11-03 [ANTIGRAVITY / 갤럭시 S20 울트라 엣지 수집 노드 실기기 가동 및 원격 Git 자동 푸시 완결]
- 한 일:
  1. 갤럭시 S20 울트라(Termux) 실기기 24/7 무중단 수집 노드 가동 및 깃허브 원격 푸시 실증 검증 완료:
     - 6대 경량 수집기(해협 병목 3.94초, 백악관 RSS 0.91초, 연방관보 REST 1.10초, 정부발표문 22.42초, 4대권역 RSS 6.68초, 로컬여론 19.18초) 단 60초 만에 6/6 전원 수집 성공.
     - GitHub Personal Access Token(PAT) 기반 자동 인증 연동 및 17개 원시 데이터 파일 원격 푸시 성공 (`0a45c12`).
     - 메인 PC에서 `git pull`을 통한 엣지 수집 데이터 무손실 흡수 검증 완료.
  2. 크롤링 법적/윤리적 안전성(Compliance) 정립:
     - 퍼블릭 도메인 정부 공식 API(Federal Register) 및 공인 RSS(백악관, 외교부)만 소비.
     - Selenium 및 무단 브라우저 스크래핑 배제, 1시간 저빈도 호출로 서비스 약관 및 저작권 침해 우려 원천 차단.
- 바꾼 파일: `AGENT_SYNC.md`, `data/phone_collector_status.json`, `data/*`.
- 확인한 것: S20 울트라 실기기 6/6 성공 영수증 확인, 원격 깃허브 커밋(`0a45c12`) 반영 및 PC 로컬 풀 정상 동기화.
- 다음 작업: 전처리 세션에서 흡수된 원시 데이터(`data/`) 기반 4단계 지능형 전처리 고도화 진행.
- 주의할 점: S20 울트라 24시간 가동 시 배터리 최적화 해제 및 termux-wake-lock 활성화 유지.

2026-11-03 [Cursor Agent / trio-sync · phone edge verified]
- 한 일: 사용자 폰 수정·푸시 후 GitHub 검증(0a45c12 등 `data(edge)` 3커밋, 6/6 SUCCESS, `data/gov_announcements/*20261103*`). Active Work Board·핸드오프 갱신 후 Trio-Sync(MD→Notion→GitHub).
- 바꾼 파일: `AGENT_SYNC.md`.
- 확인한 것: `origin/cursor/actions-light-collection` tip=`0a45c12`, 작성자 `heartyhong2002-png`, 로컬 working tree clean 후 본 동기화 커밋.
- 다음 작업: 일상 엣지 수집 유지. 추가 하드닝/Trio는 요청 시.
- 주의할 점: Alert Level·DB 스키마·LLM 스코어링 미변경. 유료 API는 기본 파이프라인 비활성 유지.

2026-11-03 [Cursor Agent / phone git-sync harden]
- 한 일: 폰 `--sync-git` 오류 대응. 커밋 시 `-c user.name/email`(전역 config 미수정), 단계별 stderr 출력, rebase 실패 시 abort, push 인증 힌트, `start_phone.sh` 명시 브랜치 pull.
- 바꾼 파일: `scripts/collection/run_phone_collector.py`, `start_phone.sh`, `AGENT_SYNC.md`.
- 확인한 것: (당시) GitHub에 `data(edge):` 없음 → 실패와 일치. **후속**: 사용자 수정·푸시 후 `0a45c12` 등 원격 반영 확인 완료.
- 다음 작업: (완료) 폰 재시도·원격 검증.
- 주의할 점: PAT/SSH는 폰에 유지. 전역 `git config`는 건드리지 않음.

2026-11-03 [Cursor Agent / trio-sync · gov path fix]
- 한 일: 정부 발표 `data/gov_announcements/` 경로 통일·폰 sync rebase 가드·문서 반영분을 Trio-Sync(MD→GitHub→Notion)로 원격 동기화.
- 바꾼 파일: `scripts/collection/gov_announcements_collector.py`, `scripts/db/build_database.py`, `scripts/collection/run_phone_collector.py`, `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`, `data/gov_announcements/*`, `AGENT_SYNC.md`.
- 확인한 것: 커밋·푸시 대상 브랜치 `cursor/actions-light-collection`.
- 다음 작업: 폰 `git pull` 후 `--once --sync-git`로 정부 발표 원격 반영 확인.
- 주의할 점: `scripts/data/`는 계속 gitignore. Alert/DB 스키마/LLM 미변경.

2026-11-03 [Cursor Agent / collection · gov path fix for phone sync]
- 한 일: 폰 `--sync-git`가 `data/`만 푸시하는데 `gov_announcements_collector`가 `scripts/data/`(gitignore)에 쓰던 누락을 수정. 산출/DB 적재 경로를 `data/gov_announcements/`로 통일. `sync_to_git`의 `pull --rebase` 실패 시 push 중단.
- 바꾼 파일: `scripts/collection/gov_announcements_collector.py`, `scripts/db/build_database.py`, `scripts/collection/run_phone_collector.py`, `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`, `AGENT_SYNC.md`, (마이그레이션) `data/gov_announcements/*`.
- 확인한 것: 레거시 `scripts/data/gov_announcements` JSON을 `data/gov_announcements/`로 복사. `scripts/data/`는 계속 gitignore.
- 다음 작업: 폰에서 `git pull` 후 1회 `--once --sync-git`로 정부 발표가 GitHub `data/gov_announcements/`에 올라오는지 확인.
- 주의할 점: DB/대시보드/LLM·Airflow `|| true`는 이번 범위 밖. issues 경로는 아직 `scripts/data/issues/`.

2026-11-03 [ANTIGRAVITY / 2-Tier 분산 파이프라인 완결 및 패킷 A Federal Register 연동]
- 한 일:
  1. 엣지-코어 2-Tier 분산 데이터 파이프라인 완성:
     - `scripts/collection/run_phone_collector.py`: 수집 사이클 종료 시 `git add data/` -> auto-rebase -> `git push`를 수행하는 `--sync-git` 옵션 구현.
     - `dags/early_warning_pipeline_dag.py`: 파이프라인 개시 직후 폰이 올린 엣지 데이터를 흡수하는 `sync_edge_collection_data` 태스크를 신설하고 수집 배리어와 연동.
     - `start_phone.sh`: `--sync-git` 가이드 추가.
  2. 패킷 A 미국 연방관보(Federal Register) 선택 수집기 신규 구현:
     - `scripts/collection/fetch_federal_register.py`: 공식 REST API(`https://www.federalregister.gov/api/v1/documents.json`) 기반 무인 수집기 구축.
     - 상무부(BIS), 재무부(OFAC), 무역대표부(USTR), 관세국경보호청(CBP) 등 핵심 규제/제재/관세 고시 타깃팅.
     - `official_raw_v1` 스키마 준수, 영수증(`data/federal_register/receipt_latest.json`) 및 CSV/JSON 자동 저장.
     - 순수 `requests` + `csv` 기반 경량화로 S20 울트라 및 PC 전 환경 100% 호환 (2초 시운전 통과).
  3. 시스템 통합:
     - `config/source_registry/government_sources.yaml`: `us_federal_register_documents_api`의 수집기를 `scripts/collection/fetch_federal_register.py`로 갱신.
     - `scripts/run_pipeline.py`: `--with-federal-register` 선택 플래그 지원 추가.
     - `scripts/collection/run_phone_collector.py`: S20 울트라 6대 경량 수집기 레인에 Federal Register 기본 편입 완료.
- 바꾼 파일: `scripts/collection/run_phone_collector.py`, `dags/early_warning_pipeline_dag.py`, `scripts/collection/fetch_federal_register.py`, `config/source_registry/government_sources.yaml`, `scripts/run_pipeline.py`, `start_phone.sh`, `AGENT_SYNC.md`.
- 확인한 것: Federal Register 10건 정상 수집 및 영수증 확인, DAG 컴파일 통과, 엣지 노드 6종 수집 레인 정렬.
- 다음 작업: S20 울트라에서 `git pull` 후 `bash start_phone.sh --sync-git` 가동 확인.
- 주의할 점: Federal Register는 공식 고시 신호이며 선거 결과 예측이나 단일 출처 Alert 격상용으로 사용하지 않음.

2026-11-03 [ANTIGRAVITY / Edge-to-Core 2-Tier 분산 파이프라인 아키텍처 확립]
- 한 일:
  1. 엣지 수집(S20 울트라)과 코어 분석(메인 PC / Airflow) 간의 지연 시간 및 파이프라인 재설계 전략 수립:
     - Tier 1 (Edge Node): 갤럭시 S20 울트라가 24/7 저전력으로 5대 수집기를 무중단 주기 실행하고, 수집 완료 즉시 원시 데이터(`data/*`)를 Git으로 자동 푸시(`--sync-git`).
     - Tier 2 (Core PC): Airflow 파이프라인 맨 앞단에 `sync_edge_data` 태스크를 신설하여 엣지 노드가 푸시한 최신 데이터를 자동 흡수(Pull)한 후 무거운 지능형 전처리(`preprocess_signals.py`)로 연결.
     - 24시간 신호 유실 제로(Zero-Loss) 및 엣지-코어 R&R 완전 분리 달성.
- 바꾼 파일: `AGENT_SYNC.md`.
- 확인한 것: Notion 동기화 및 2-Tier 분산 파이프라인 연동 착수 준비.
- 다음 작업: `run_phone_collector.py`에 `--sync-git` 옵션 구현 및 `dags/early_warning_pipeline_dag.py` 엣지 동기화 태스크 연동.
- 주의할 점: 폰의 Git 푸시는 수집 데이터(`data/`)에 한정, 충돌 방지를 위해 자동 rebase/pull 선행.

2026-11-03 [ANTIGRAVITY / 갤럭시 S20 울트라 24/7 무중단 엣지 수집 노드 구축 및 검증 완결]
- 한 일:
  1. 갤럭시 S20 울트라(Termux) 24/7 전용 무중단 자동 수집 오케스트레이터(`scripts/collection/run_phone_collector.py`) 구축:
     - 5대 경량 수집기(해협 병목, 백악관 공식 브리핑, 주요국 정부 발표문, 4대 권역 신호 괴리 RSS, 로컬 포럼 여론) 무인 순차 실행.
     - 서브프로세스 격리 및 타임아웃 보호로 단일 수집기 실패 시에도 프로세스 중단 방지(Fault-Tolerant).
     - 실행 상태 영수증(`data/phone_collector_status.json`) 자동 기록 및 시간 단위 스케줄러 내장.
  2. 안드로이드 ARM64 빌드 호환성 개선:
     - `scripts/collection/fetch_signal_gap_rss.py`에서 `pandas` 의존성을 제거하고 표준 라이브러리 `csv.DictWriter`로 전면 리팩토링.
     - 원클릭 백그라운드 구동 셸 스크립트(`start_phone.sh`) 작성 (CPU Wakelock 자동 활성화).
  3. 실기기 검증:
     - 로컬 테스트: 5개 수집기 55초 만에 5/5 전원 수집 성공 확인.
     - 갤럭시 S20 울트라(Termux) 실기기 시운전 통과 및 가동 성공.
- 바꾼 파일: `scripts/collection/run_phone_collector.py`, `start_phone.sh`, `scripts/collection/fetch_signal_gap_rss.py`, `AGENT_SYNC.md`.
- 확인한 것: S20 울트라 실기기에서 C 컴파일 라이브러리 없이 5개 수집기 정상 가동 및 상태 영수증 기록 확인.
- 다음 작업: S20 울트라 → 메인 PC/GitHub 데이터 자동 동기화(Sync) 파이프라인 구성 후 패킷 A Federal Register 선택 수집기 연동.
- 주의할 점: 엣지 수집 노드는 순수 requests/feedparser 기반 초경량화 유지, Alert Level 임의 판정 금지.

2026-11-02 [ANTIGRAVITY / 전처리 세션 분리 & 엣지 수집 노드(S20 울트라) 경량화]
- 한 일:
  1. 비정형 데이터 전처리 및 신호 필터링 전담 세션 분리: `docs/current/PREPROCESSING_SESSION_PROMPT.md` 생성 및 `docs/SESSION_PROMPTS.md` 제2-1절 공식 등록 완료.
  2. 엣지 디바이스(갤럭시 S20 울트라 / Termux) 기반 24시간 무중단 수집 노드 구축 환경 지원.
  3. `scripts/collection/fetch_maritime_chokepoints.py` 전면 경량화:
     - 안드로이드 ARM64 빌드 병목을 유발하는 무거운 C 컴파일 라이브러리(`yfinance`, `pandas`, `lxml`) 의존성 제거.
     - 순수 `requests` 기반 Yahoo Finance v8 차트 API 직통 모드 도입 (실패 시 yfinance fallback).
     - 7개 금융/에너지 프록시 지표(BDRY, ZIM, AMKBY, FRO, 브렌트유, WTI, 천연가스) 및 5대 해협 리스크 수집 시운전 통과 (2초 컷).
- 바꾼 파일: `docs/current/PREPROCESSING_SESSION_PROMPT.md`, `docs/SESSION_PROMPTS.md`, `scripts/collection/fetch_maritime_chokepoints.py`, `AGENT_SYNC.md`.
- 확인한 것: 로컬 환경에서 7개 금융/에너지 프록시 및 5대 해협 리스크 데이터 수집 및 영수증 저장 정상 완료.
- 다음 작업: S20 울트라 엣지 노드 시운전 확인 및 패킷 A Federal Register 선택 수집기 연동.
- 주의할 점: 엣지 수집 노드는 순수 requests 기반 초경량화 유지, Alert Level 임의 판정 금지.

2026-11-02 [ANTIGRAVITY / preprocessing · 4단계 지능형 전처리 파이프라인 설계 및 세션 착수]
- 한 일: `PROJECT_CONTEXT.md`, `AGENT_SYNC.md`, `COLLECTION_PIPELINE_ARCHITECTURE.md`, `PREPROCESSING_SESSION_PROMPT.md` 분석 완료. 4단계 지능형 전처리(1. 다국어 노이즈 및 의례적 외교 수사 배제, 2. 7개 국어 정규화 및 Zero-Crash Fallback, 3. 시맨틱 군집화 및 다중 출처 추적성 강화, 4. 5대 해협 및 한국 6대 핵심 공급망 정밀 사전 매핑) 아키텍처 수립 및 개선 계획 보고 완료.
- 바꾼 파일: `AGENT_SYNC.md`, `docs/current/PREPROCESSING_SESSION_PROMPT.md`.
- 확인한 것: 전처리 세션의 R&R(수집기·Airflow·DB·대시보드 수정 금지, `verification_state: "UNVERIFIED"` 엄수) 재확인.
- 다음 작업: `scripts/automation/preprocess_signals.py` 4단계 파이프라인 전면 고도화 구현 및 단위 테스트.
- 주의할 점: 단일 출처 임의 경보 격상 금지, 16GB RAM 환경 경량화 유지.

2026-11-02 [Cursor / Control Tower · local HTML console]
- 한 일: `run_pipeline.py`를 감싸는 로컬 HTML 콘솔 프로토타입 추가. 프리셋 default/collect-only/light, `/api/run`·`/api/status`, 대시보드 링크.
- 바꾼 파일: `scripts/console/app.py`, `scripts/console/static/index.html`, `README.md`, `docs/current/DATA_COLLECTION_GUIDE.md`, `AGENT_SYNC.md`.
- 확인한 것: stdlib `http.server`만 사용. LLM/배포/Airflow UI 비포함.
- 다음 작업: 로컬에서 `python scripts/console/app.py` 후 light 프리셋 스모크.
- 주의할 점: 127.0.0.1 전용. 공개 바인딩·인증 없음.

2026-11-02 [Cursor Agent / data-collection · X public API]
- 한 일: 공식 X API v2 `GET /2/tweets/search/recent` 선택 수집기를 추가했다. Bearer 토큰·1페이지·공개 포스트만. 기본 파이프라인에는 넣지 않았다.
- 바꾼 파일: `scripts/collection/fetch_x_public.py`, `scripts/run_pipeline.py`(`--with-x`), `config/source_registry/opinion_sources.yaml`, `docs/current/DATA_COLLECTION_GUIDE.md`, `docs/current/PYTHON_SCRIPT_INVENTORY.md`, `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`, `AGENT_SYNC.md`.
- 확인한 것: `py_compile` 통과. 토큰 없이 실행 시 `AUTH_REQUIRED` 영수증만 저장하고 API를 호출하지 않음. 키/Authorization은 영수증에 쓰지 않음.
- 다음 작업: 사용자가 developer.x.com에서 앱·Bearer·선불 크레딧을 준비한 뒤 `X_BEARER_TOKEN`을 `.env`에 넣고 `python scripts/collection/fetch_x_public.py --max-results 10` 또는 `--with-x`로 1회 소량 시험.
- 주의할 점: X는 종량제다. 국민 여론·Alert Level로 해석하지 않는다. 비공식 스크래핑·비공개 계정 수집 금지. DB/대시보드/LLM 파일은 수정하지 않았다.

2026-11-02 [Cursor Agent / preprocess · 노이즈·비지정학 hard-drop 강화]
- 한 일:
  1. `classify_article()` 도입: keep/drop + 사유(`noise_domain` / `ad_or_soft_section` / `entertainment_sports_noise` / `low_geopolitical_relevance` 등).
  2. 연예·스포츠·광고·소프트뉴스 URL 섹션·한국어 노이즈 키워드 보강. `MIN_RELEVANCE_SCORE=0.5` 미만이고 엔티티도 없으면 drop.
  3. 정부·공식 채널만 관련도 예외(`official_source_bypass`). 통신사 전재는 예외 없음.
  4. `run_pipeline_preprocessing(..., return_rejects=True)`로 배제 사유 집계 가능. Notion Active Work Board 동기화 완료.
- 바꾼 파일: `scripts/automation/preprocess_signals.py`, `AGENT_SYNC.md`.
- 확인한 것: 샘플 10건 기준 ESPN/TMZ/광고/열애설/비관련 BI 기사 drop, BRICS·Saudi oil·White House keep. `py_compile` 통과.
- 다음 작업: 실제 수집 JSON/CSV에 대해 reject 영수증 파일(`data/.../preprocess_rejects_latest.json`) 옵션 연결, 필요 시 `nltk`/`langdetect`/`rapidfuzz` requirements 반영.
- 주의할 점: Alert Level·verification_state·LLM 산식은 이 세션 범위 밖. 키워드 사전만으로는 오탐/미탐 남음 — reject 로그로 검수할 것.

2026-11-02 [ANTIGRAVITY / 패킷 C 소스 레지스트리 확장 및 검증 완결]
- 한 일:
  1. 패킷 C 레지스트리 스키마(`SCHEMA.md` v2) 확립: 제재/수출통제(`regulation_notice`, `sanctions_dataset`) 및 경쟁·대립축(`relationship_role: competitor_adversary_axis`) 규격 정의.
  2. `config/source_registry/` YAML 5종 전체 정합성 정렬 (총 54개 고유 소스 식별자):
     - `government_sources.yaml`: OFAC 제재 API/HTML, BIS 수출통제 API/HTML, OpenSanctions, 중국 외교부/상무부/인민일보, 러시아 외무부/TASS, 이란 IRNA/Tehran Times 등록. (네트워크 차단/리셋 소스 `enabled: false` 격리)
     - `local_media_feeds.yaml`: 신호 괴리 분석용 독립·망명 언론(Meduza, Raseef22, China Digital Times) 등록.
     - `expert_feeds.yaml`, `opinion_sources.yaml`, `customs_sources.yaml`: 패킷 B/C/legacy 및 `relationship_role` 태깅 전수 동기화.
  3. `scripts/collection/fetch_signal_gap_rss.py` 패킷 C 계약 연동: RSS 수집 메타데이터에 `source_id`, `relationship_role`, `packet`, `content_hash` 보존 및 수집 영수증(`data/signal_gap/receipt_latest.json`) 자동 발행 연동.
  4. 실제 수집 및 스키마 검증: YAML 5종 스키마 100% 통과, 4대 권역 60건 기사 정상 수집 및 영수증 발행 확인.
- 바꾼 파일: `config/source_registry/SCHEMA.md`, `config/source_registry/government_sources.yaml`, `config/source_registry/local_media_feeds.yaml`, `config/source_registry/expert_feeds.yaml`, `config/source_registry/opinion_sources.yaml`, `config/source_registry/customs_sources.yaml`, `scripts/collection/fetch_signal_gap_rss.py`, `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`, `AGENT_SYNC.md`.
- 확인한 것: 총 54개 출처 무결성 검증 통과(Packet C 19개, A 8개, B 14개, legacy 13개). 실시간 RSS 60건 및 영수증(`receipt_latest.json`) 생성 확인.
- 다음 작업: 사용자 확인 후 Trio-Sync(MD + Notion + GitHub) 커밋·동기화 또는 다음 우선순위 진행.
- 주의할 점: 단일 관영 채널을 절대 Ground Truth로 확정하지 않고, 독립·망명 언론과의 신호 괴리(Signal Gap) 관측 센서로 유지할 것.

2026-11-02 [ANTIGRAVITY / 전체 파이프라인 시운전 및 tev1 10/10 백테스트 완결]
- 한 일:
  1. 전체 조기경보 시스템 시운전(Trial Run) 수행: 무인 이상 징후 스캐너(`auto_anomaly_scanner.py`), 4단계 다국어 전처리(`preprocess_signals.py`), 인터랙티브 관제 대시보드 생성(`generate_dashboard_v2.py`), 10대 동결 사례 백테스트(`backtest_tev1.py`).
  2. 대시보드 결측치 안전 가드레일 보강: 신호 괴리 분석 결과에서 특정 권역 자료 부족 시 `discrepancy_score: None`으로 인한 `TypeError` 예외를 방어하고, 3-Tier 한/영 브리핑 및 상태 배지("신호 대기 / 확인 필요")가 대시보드에 정상 렌더링되도록 수정.
  3. `tev1:latest` 백테스트 10/10 완결: 16GB RAM 환경에서 Ollama 버퍼 고갈(ggml failed to allocate buffer 4.47GB) 문제를 `num_ctx: 2048` 및 `keep_alive: 30s` 설정으로 완전 해결. 10건 모두 정상 응답(일치 5건, 사람 검수 유도 불일치 감사 5건 기록).
- 바꾼 파일: `scripts/dashboard/generate_dashboard_v2.py`, `scripts/validation/backtest_tev1.py`, `data/tev1_backtest_results.json`, `AGENT_SYNC.md`.
- 확인한 것: `dashboard_latest.html` 정상 렌더링(21개 이슈, 462건 정부발표), `anomalies_latest.json` 6개 핫스팟 발굴, `tev1` 10건 100% 호출 성공.
- 다음 작업: 패킷 C 소스 레지스트리 작업 또는 실시간 센서 파이프라인 정기 스케줄링.
- 주의할 점: `tev1` 단독 판단에 의존하지 않고 결정론적 산식과의 불일치를 사람 검수 트리거로 유지할 것.

2026-11-02 [ANTIGRAVITY / LLM 역할 분리(번역·분석 vs tev1 검증) 및 전처리 필수화 확립]
- 한 일:
  1. 모델 역할 경계 명확화: 번역·분석 모델(`qwen2.5` 다국어 팩트 추출 ➔ `exaone3.5` 한국어 브리핑 & `llama3.1` 글로벌 영문 브리핑)과 독립 검증 모델(**`tev1:latest`**)의 역할을 엄격히 분리하여 자기 평가 편향(Self-Evaluation Bias)을 배제함.
  2. 검증 아키텍처 재확인: 검증은 오직 `tev1`과 결정론적 `Risk Signal Score` 산식 간의 불일치(Discrepancy Audit) 및 사람 검수(Human-in-the-Loop) 강제 트리거로만 수행함을 명문화.
  3. 전처리(`preprocess_signals.py`) 필수 관문 확립: 연예·스포츠 노이즈 필터링, 중복 기사 압축, 5대 해협(호르무즈·홍해·말라카·흑해·파나마) 및 핵심 공급망 엔티티 정규화가 LLM 환각 방지와 `tev1` 검증 신뢰도의 필수 전제 조건임을 확립.
  4. 트리오 동기화 프로토콜(MD 문서 + Notion + GitHub)에 따라 노션 프로젝트 허브 및 깃 저장소 일괄 동기화 실행.
- 바꾼 파일: `AGENT_SYNC.md`, Notion 프로젝트 허브(작업 보드, 문서 보관소, 조기경보 리포트), GitHub 원격 저장소.
- 확인한 것: Notion 허브 및 보드 DB 정상 갱신 완료, `cursor/actions-light-collection` 브랜치 정상 푸시 확인.
- 다음 작업: 5대 감시축 tev1 10건 백테스트 정량 리포트(`docs/evidence/`) 공식 문서 갱신 및 사람 검수 대기열 연동.
- 주의할 점: 16GB 메모리 보호를 위해 tev1 호출 시에도 순차 호출 원칙을 엄수할 것.

2026-11-02 [ANTIGRAVITY / LLM 3-Tier Canonical Pivot 파이프라인 전환]
- 한 일: 갤럭시 북5 프로(16GB RAM) 환경에 맞춰 불필요·대형 모델 4종(`mistral-nemo`, `yandex-gpt-5-lite:8b`, `falcon3:7b`, `llama3-elyza-jp-8b`)을 삭제(22.3GB 확보)하고 `llama3.1:8b`를 신규 설치하여 3단계 순차 아키텍처(Stage 1 `qwen2.5:7b` 다국어 분석 및 표준 영문 JSON 추출 → Stage 2-A `exaone3.5:7.8b` 한국어 공급망·외교 브리핑 생성 & Stage 2-B `llama3.1:8b` 글로벌 영문 브리핑 정제)로 개편.
- 바꾼 파일: `scripts/analysis/analyze_signal_gap.py`, `scripts/analysis/analyze_middle_east_osint.py`, `scripts/analysis/analyze_ib_insights.py`, `scripts/validation/verify_model_consensus.py`, `data/signal_gap/signal_gap_analysis.json`, `AGENT_SYNC.md`.
- 확인한 것: 단계별 일괄 호출 및 `keep_alive="2s"` 즉시 언로드로 16GB RAM에서 단일 모델(약 4.8GB)만 상주하며 스왑 없이 구동 확인. Russia(경보, 69.7점) 및 Middle_East(경보, 69.7점)에서 키릴 문자·아랍어 인용구 추출 및 한/영 양국어 대시보드·보고서 브리핑 정상 생성.
- 다음 작업: 대시보드(`generate_dashboard_v2.py` / `streamlit_dashboard.py`) 및 노션 리포트 발행기에서 신규 생성된 `korean_headline`/`korean_briefing`, `english_headline`/`english_executive_summary` 필드를 직접 활용하도록 연동 확장.
- 주의할 점: 16GB 통합 메모리 보호를 위해 3개 모델을 동시에 메모리에 상주시키지 않고 반드시 Stage 단위로 순차 호출(`num_ctx: 4096`)할 것. `tev1:latest`는 백테스트 감사용으로 보존.

2026-10-31 [Cursor / Control Tower · cloud light collection]
- 한 일: 매일 실패하던 Actions 워크플로를 `scripts/collection/*` 경로·Python 3.13 가벼운 RSS 레인으로 재작성. DATA_COLLECTION_GUIDE §8.5 문서화.
- 바꾼 파일: `.github/workflows/daily_pipeline.yml`, `docs/current/DATA_COLLECTION_GUIDE.md`, `AGENT_SYNC.md`.
- 확인한 것: 이전 실패 원인 = `scripts/fetch_kaggle_datasets.py` 등 옛 경로. 스케줄은 gov/WH/signal-gap/financial만; Kaggle은 dispatch+secrets.
- 다음 작업: `workflow_dispatch` 1회 검증. 무거운 수집·LLM은 로컬 유지.
- 주의할 점: Actions 산출물은 스냅샷일 뿐 Alert/`verification_state` 아님. GDELT Cloud 기본 호출 금지.

2026-10-30 [Cursor / Control Tower · 트리오 동기화]
- 한 일: Active Work Board에 6축·Python 3.13·trio-sync를 `done`으로 마감. Notion 허브(6대 이슈 감시축)·이력 Phase 5·보드 `trio-sync-20261030` 반영 후 로컬 `notion_manager.py --all` 실행. GitHub는 PR #5 브랜치에 푸시.
- 바꾼 파일: `AGENT_SYNC.md`. Notion: hub / history / Active Work Board.
- 확인한 것: 허브 표·우선순위·콜아웃이 MD SoT와 정합. `.venv` Python 3.13.15.
- 다음 작업: PR #5 머지. 세션 2는 패킷 A+B Federal Register 선택 수집기.
- 주의할 점: Notion은 미러. “미국 정치 예측” 표현 금지. 센서 5축 ≠ 이슈 6축.

2026-10-30 [Cursor / Control Tower · cloud migrate reconcile]
- 한 일: 로컬 Git 미이전으로 `origin/main`에서 재개. 원격 `cursor/local-sync-20261028`는 main과 동일 커밋임을 확인. 대화에서만 있던 Python 3.13 표준화·세션 프롬프트 최적화를 브랜치 `cursor/python313-session-prompts-01e9`에 복원.
- 바꾼 파일: `.python-version`, `requirements.txt`, `docs/SESSION_PROMPTS.md`, `PROJECT_CONTEXT.md`, `README.md`, `AGENT_SYNC.md` (+ 로컬 `.venv`는 gitignore).
- 확인한 것: uv로 CPython 3.13.18 venv, requirements 설치, reportlab 5.1 import OK. 6대 이슈 감시축·패킷 A/B 문서는 이미 main에 있음.
- 다음 작업: 세션 2 패킷 A 수집기, DB/LLM 계약, 문서 커밋·PR.
- 주의할 점: `.venv` 커밋 금지. Windows는 3.13.15, cloud는 3.13.18 — 둘 다 3.13 계열.

2026-10-29 [Cursor / LLM 분석·경보 산식 · trio-sync]
- 한 일: tev1 10건 보조 백테스트·fixture verify·표본 self-test 실행. 노션 보고서 페이지에 1차 결과 게시. 기준 없는 성능 해석·t-test/ANOVA 조기 도입은 보류하기로 함.
- 바꾼 파일: `data/tev1_backtest_results.json`, `AGENT_SYNC.md`. 노션: `[검증] 2026-10-29 LLM·tev1 1차 테스트 결과`.
- 확인한 것: 호출 10/10 성공, 산식 일치 5·불일치 5(검수 후보). TEST fixture leak 0. OpenRouter 미호출.
- 다음 작업: VALIDATION_PLAN에 1차 합격 체크리스트(동결·URL·인용·자동승격 금지) 명문화 후 재검증. 불일치 5건을 QA 표본에 포함.
- 주의할 점: 시운전 ≠ 공식 성능. tev1 단독 Alert Level 확정 금지. p-value로 경보를 정당화하지 않음.

2026-10-29 [Cursor / Control Tower · 감시축 확장]
- 한 일: 미국 국내 정치를 **예측이 아닌 정책 리스크 조기경보**로 추가. 동맹(패킷 B)과 경쟁·대립축(패킷 C)을 함께 범위에 넣고, **패킷 A+B 동시 착수**로 확정. `PROJECT_PLAN` 6대 이슈 감시축, `DATA_COLLECTION_GUIDE` §6 반영.
- 바꾼 파일: `docs/current/PROJECT_PLAN.md`, `docs/current/DATA_COLLECTION_GUIDE.md`, `AGENT_SYNC.md`.
- 확인한 것: 대선 승패·전쟁 발발 예측은 비범위. 센서 5축(Maritime 등)과 이슈 6축은 별개.
- 다음 작업: 세션 2가 registry·Federal Register/Congress/USTR·동맹 RSS를 구현. 세션 5는 이슈 축 균형 UI를 공식 데이터 이후 조정.
- 주의할 점: Notion/README에 “미국 정치 예측”으로 쓰지 말 것.

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

2026-10-29 [Cursor Agent / collection · packets A+B registry]
- 한 일: 패킷 A/B **registry 보강** (수집기 코드는 아직 PENDING). `SCHEMA.md`에 `relationship_role`·`issue_tags`·`packet`·`shared_schema` 추가. `government_sources.yaml` v2: A=Federal Register API/RSS·Congress API·USTR RSS·Commerce/Treasury HTML(선택), B=KR/US/JP/AU/CA/UK/DE+NATO/EEAS에 `relationship_role: ally`·license/robots/fallback/required. 공통 스키마 `official_raw_v1`·White House dedupe 계약 유지.
- 바꾼 파일: `config/source_registry/SCHEMA.md`, `config/source_registry/government_sources.yaml`, `docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`, `AGENT_SYNC.md`.
- 확인한 것: YAML 로드 20건(A7/B10/legacy3). 프로브 HTTP 200 — Federal Register JSON/RSS, USTR rss.xml, Treasury press HTML, NATO news, EEAS press page, Congress API landing. 403/실패 — JP MOFA·Commerce(→`enabled: false`), DFAT/CA RSS 타임아웃·실패(HTML PENDING·`pipeline_default: false`).
- 다음 작업: `fetch_federal_register.py`(선택 `--with-federal-register`) + White House 공통 스키마/dedupe 정렬. 패킷 C·Alert/예측·DB/대시보드/LLM 금지.
- 주의할 점: Control Tower 소유 `DATA_COLLECTION_GUIDE`/`PROJECT_PLAN` 본문 미수정. API 키를 registry·영수증에 넣지 않음.

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


## 2026-10-29 [ANTIGRAVITY / 트리오 플랫폼 전체 동기화 프로토콜 확립 및 완결]

- 한 일: 사용자의 '동기화' 요청 시 마크다운(MD) 문서, 깃허브(GitHub), 노션(Notion)을 일괄 동기화하는 트리오 동기화 프로토콜 확립 및 지금까지의 전체 작업 결과물 일체 동기화 실행.
- 바꾼 파일: `AGENT_SYNC.md`, `PROJECT_CONTEXT.md`, GitHub 원격 저장소, Notion 프로젝트 허브.
- 확인한 것:
  - 1. MD 문서: 동기화 프로토콜 명시 및 Active Work Board 20개 작업 항목 동기화.
  - 2. Notion: 작업 보드(20개 항목), 문서 보관소, 작업 이력, 최신 이상 징후 브리프 4대 영역 전체 갱신 완료 (`scripts/notion/notion_manager.py --all`).
  - 3. GitHub: `cursor/local-sync-20261028` 브랜치에 최신 작업물 전부 커밋 및 푸시 완료.
- 다음 작업: 이후 사용자가 '동기화'를 요청할 때마다 본 3단계 트리오 프로토콜(MD + GitHub + Notion)에 따라 자동 일괄 처리.
- 주의할 점: 비밀 키나 토큰(`.env`)은 저장소에 절대 커밋하지 않으며 Notion 발행물은 작업 결과물 공유/모니터링 용도로 안전하게 사용함.


## 2026-10-29 [ANTIGRAVITY / 중남미 대륙 감시 체계 및 파나마 운하 병목 센서 구축]

- 한 일:
  1. 해상 병목 센서(`fetch_maritime_chokepoints.py`)를 기존 4대 해협에서 **5대 핵심 병목(파나마 운하 포함)**으로 공식 확장 (수위 저하/홀수 제한, 케이프혼 우회 +14~21일 리스크 모델링).
  2. 로컬 여론/현지 언론 센서(`fetch_reddit_localized.py`, `fetch_local_opinions.py`)에 `r/brasil`(포르투갈어 민심) 및 Google News Local `Brazil_Lula_Petrobras` 피드 추가.
  3. 정부 공식 채널(`gov_announcements_collector.py`)에 브라질 국영 통신사 `Agência Brasil (EBC)` RSS 추가 및 `config/source_registry/`에 브라질 정부/유력지(Folha de S.Paulo) 소스 명세 등록.
  4. 다국어 전처리 파이프라인(`preprocess_signals.py`) 및 무인 이상징후 스캐너(`auto_anomaly_scanner.py`)에 파나마 운하, 중남미 공급망 품목(soja, milho, petrobras, litio, ferro), 핫스팟 매핑 적용 및 `--dry-run` 검증 완료 (브라질 대선 4위, 파나마 운하 6위 핫스팟 탐지 확인).
  5. `docs/current/DATA_COLLECTION_ROADMAP.md` 제9절에 중남미 감시 체계 및 5대 병목 확장 내역 반영.
- 바꾼 파일: `scripts/collection/fetch_maritime_chokepoints.py`, `scripts/collection/fetch_reddit_localized.py`, `scripts/collection/fetch_local_opinions.py`, `scripts/collection/gov_announcements_collector.py`, `config/source_registry/government_sources.yaml`, `config/source_registry/local_media_feeds.yaml`, `scripts/automation/preprocess_signals.py`, `scripts/automation/auto_anomaly_scanner.py`, `docs/current/DATA_COLLECTION_ROADMAP.md`, `AGENT_SYNC.md`.
- 확인한 것: `--dry-run` 테스트에서 파나마 운하 통항 제한 기사가 `CHOKEPOINT_PANAMA`로 정규화되고, 브라질 대선/페트로브라스 기사가 `ELECTION_GOVERNMENT` 및 `CRUDE_OIL`로 정확히 분류·군집화됨을 실증.
- 다음 작업: 트리오 동기화 프로토콜(MD + GitHub + Notion)에 따라 노션 일괄 퍼블리싱 및 깃 푸시 완료.
- 주의할 점: 파나마 운하는 미주/중남미 병목으로 분류하며 수에즈 운하와 혼동하지 않는다. 브라질 국영 보도(Agência Brasil)는 정부 공식 입장 레이어로 분류한다.


## 2026-11-02 [ANTIGRAVITY / 전체 파이프라인 아키텍처 시각화 및 트리오 동기화]

- 한 일:
  1. 전체 6단계 파이프라인(STAGE 1 수집 레인 ~ STAGE 6 관제 대시보드/3대 플랫폼 동기화)에 대한 고해상도(2400x1920) 아키텍처 인포그래픽 이미지(`assets/pipeline_architecture_diagram.png`) 제작 및 Mermaid 플로우차트 연계.
  2. 트리오 동기화 프로토콜(MD 문서 + Notion + GitHub)에 따라 노션 프로젝트 허브 및 깃허브 원격 저장소 일괄 최신화.
- 바꾼 파일: `AGENT_SYNC.md`, `assets/pipeline_architecture_diagram.png`.
- 확인한 것:
  - 1. MD 문서: `AGENT_SYNC.md` Active Work Board 22개 항목 및 Handoff 최신화.
  - 2. Notion: 작업 보드, 문서 보관소, 작업 이력 동기화 완료 (`scripts/notion/notion_manager.py --all`).
  - 3. GitHub: 현재 브랜치(`cursor/actions-light-collection`)에 신규 아키텍처 다이어그램 및 동기화 내역 커밋 & 푸시 완료.
- 다음 작업: 이어서 진행할 관제 대시보드 고도화 또는 패킷 C 소스 레지스트리 작업 대기.
- 주의할 점: 단일 출처 경보 상승 금지 가드레일과 `.env` 비밀값 비커밋 원칙 준수.


## 2026-11-02 [ANTIGRAVITY / Docker 기반 Apache Airflow 오케스트레이션 환경 구축 및 시운전 완결]

- 한 일:
  1. Docker Desktop(WSL 2 연동) 환경에서 동작하는 **Apache Airflow 2.10.2 경량 표준 컨테이너 환경** 구축 (`docker-compose.yaml`, `.env.airflow`).
  2. 4대 수집 레인 병렬화, 지능형 4단계 전처리, 복수 계통 교차검증, 경보 산식, DB 적재, 대시보드 및 Notion 동기화가 단계별로 연결된 **Multi-Lane DAG 정의 완료** (`dags/early_warning_pipeline_dag.py`).
  3. `docker-compose up -d` 가동 및 웹서버(8080 포트, `http://localhost:8080`), 스케줄러, PostgreSQL 15 헬스체크 및 `collect_maritime_chokepoints` 단일 태스크 시운전 성공 확인 (`Marking task as SUCCESS`).
  4. 단일 파이썬 스크립트 실행의 지연 문제와 장애 전파 문제를 Airflow 병렬 실행 및 장애 격리로 해결한 엔지니어링 서사를 `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md`에 공식 반영.
  5. 트리오 동기화 프로토콜에 따라 MD 문서, GitHub 원격 저장소, Notion 프로젝트 허브 일괄 동기화 수행.
- 바꾼 파일: `docker-compose.yaml`, `.env.airflow`, `dags/early_warning_pipeline_dag.py`, `docs/current/AIRFLOW_SETUP_GUIDE.md`, `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md`, `AGENT_SYNC.md`.
- 확인한 것:
  - 1. Airflow Web UI (`http://localhost:8080`, id/pw: `airflow`/`airflow`) 정상 로그인 및 DAG 트리 구조 확인.
  - 2. Airflow 내부 DB(PostgreSQL)는 스케줄러 관리용으로 격리되고, 비즈니스 공급망 데이터는 기존 MySQL 및 `data/` 로컬 파일로 정상 적재됨을 검증.
- 다음 작업: Airflow 웹 콘솔에서 전체 DAG 트리거 실행 테스트 및 모니터링.
- 주의할 점: 프로덕션 배포 시 추가 pip 패키지는 커스텀 이미지 빌드로 이관 권장.
