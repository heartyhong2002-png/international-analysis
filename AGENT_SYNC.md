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
| done | ANTIGRAVITY | db / pipeline / cross-verification | `scripts/run_pipeline.py`, `scripts/load_cross_verification_to_db.py`, `scripts/create_views.sql` | 해협 센서·공급망 사건 교차검증의 DB 적재와 대시보드 뷰 연동 | 2026-10-02 |
| done | ANTIGRAVITY | data-collection / supply-chain-sensors | `scripts/fetch_maritime_chokepoints.py`, `scripts/cross_verify_events.py`, `data/maritime_chokepoints/`, `data/event_cross_verification/` | 해협·시장 센서 수집 및 복수 계통 교차검증 | 2026-10-02 |
| done | ANTIGRAVITY | data-collection / public-opinion | `scripts/fetch_local_opinions.py`, `scripts/fetch_google_trends.py`, `data/local_opinions/`, `data/google_trends/` | 대안 로컬 여론·검색 트렌드 센서 구축 | 2026-09-29 |
| in-progress | ANTIGRAVITY | dashboard / ui | `scripts/streamlit_dashboard.py` | Streamlit 대시보드 유지보수 및 고도화 | 2026-09-28 |
| in-progress | ANTIGRAVITY | llm-analysis / alert-scoring | `prototype_all_in_one.py`, `scripts/analyze_signal_gap.py`, `scripts/analyze_signals.py`, `data/review_log.csv` | LLM 분석·Risk Signal Score·검수 체계 연동 | 2026-09-28 |
| done | Codex | docs / session-sync | `PROJECT_CONTEXT.md`, `AGENT_SYNC.md`, `docs/current/DATA_COLLECTION_GUIDE.md`, `project-handoff.md` | 현재 방향, 센서 분류, 교차검증 규칙, 세션 상태 문서 정리 | 2026-10-02 |

Status 값은 `open`, `in-progress`, `review-needed`, `done`, `blocked` 중 하나를 쓴다.

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
