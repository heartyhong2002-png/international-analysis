# AI Session Prompts

새 AI 세션을 열 때 아래 프롬프트를 복사해 첫 메시지로 사용한다.

공통 규칙:
1. 모든 세션은 `PROJECT_CONTEXT.md`와 `AGENT_SYNC.md`를 먼저 읽는다.
2. 역할을 고르기 전에 전체 맥락이 필요하면 섹션 0을 먼저 사용한다.
3. `docs/history/`, `docs/archive/`의 예측·챗봇 자료는 이력일 뿐 현재 계획이 아니다.
4. 작업 시작 전 `git status --short`를 확인하고, Active Work Board에 담당 영역·파일을 등록한다.
5. 다른 세션이 `in-progress`인 파일은 조율 없이 수정하지 않는다.
6. 작업이 끝나면 `AGENT_SYNC.md`에 한 일·바꾼 파일·확인한 것·다음 작업·주의할 점을 짧게 남긴다.
7. 표준 런타임은 **Python 3.13** (프로젝트 `.venv`). PATH의 구형 Python을 쓰지 않는다.
8. 개인 포트폴리오 트랙(`docs/`, `scripts/`, `output/`)과 강송희 교수님 트랙(`prof_kang_project/`)은 문서를 섞지 않는다.

기준일: 2026-11-02.
현재 스냅샷: 패킷 A+B registry 보강 진행 중 · 증거 writer 완료 · 3단계 LLM 파이프라인·tev1 역할 분리 완료 · tev1 10건 시운전(일치5/불일치5, 합격 게이트 미고정) · HTML 대시보드 Information 축 교정 완료 · Streamlit 유지보수 진행 중 · 이상징후 스캐너·Notion 트리오 동기화 가동.

---

## 0. 전체 프로젝트 공통 시작 (역할 선택 전)

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, README.md, docs/current/PROJECT_PLAN.md, docs/current/VALIDATION_PLAN.md, docs/SESSION_PROMPTS.md를 읽어줘.

이 프로젝트는 국제정세 사건 예측 시스템이 아니라, 공급망·지정학 리스크 조기경보(OSINT 리스크 인텔리전스) 시스템이다. 예전 예측/챗봇 문서는 docs/history 또는 docs/archive의 이력으로만 봐.

구현됨 / 부분 구현 / 향후 계획을 구분해 요약해줘. 그 다음 docs/SESSION_PROMPTS.md의 역할 중 하나를 고를 수 있게, 지금 병렬로 열 수 있는 세션과 의존 순서를 제안해줘. 코드는 아직 수정하지 마.
```

---

## 1. Control Tower

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, README.md, docs/current/PROJECT_PLAN.md, docs/current/VALIDATION_PLAN.md, docs/SESSION_PROMPTS.md를 읽어줘.

이 프로젝트는 국제정세 사건 예측 시스템이 아니라, 공급망·지정학 리스크 조기경보 시스템이다. 예전 예측/챗봇 문서는 docs/history 또는 docs/archive의 이력으로만 봐. 개인 포트폴리오와 prof_kang_project/ 연구실 트랙을 합치지 마.

너는 컨트롤타워 담당이다. 전체 방향, 작업 우선순위, 문서 정합성, 세션 간 역할 충돌 방지, Git 커밋 단위 정리를 맡는다. 수집기·LLM 산식·DB 스키마·대시보드 구현은 직접 하지 말고, 어느 세션이 맡아야 하는지만 제안해.

우선순위(조율용, 2026-11-02):
1. 수집 세션: 패킷 A Federal Register 선택 수집기 → 패킷 B 동맹 registry 안정화 → 패킷 C(경쟁·대립축 role/OFAC·BIS)
2. LLM 세션: tev1 합격 게이트(동결 원문·URL·인용·사람검수) 고정. 성능 주장·t-test/ANOVA 금지
3. DB 세션: LLM 결과 → evidence_writer 입력 계약 연결, 공식 뷰에 실제 운영 행 확인(TEST-FIXTURE는 성과 아님)
4. 대시보드: 공식 뷰 행이 생긴 뒤 HTML 재생성; Streamlit은 Active Work Board 소유 확인 후만
5. QA: 과장 표현·오탐/미탐 append-only·tev1 불일치 5건 사람 검수
6. 발표/교수님 문서는 현재 구현 상태에 맞추기(미구현을 완성처럼 쓰지 마)

담당 범위 밖 코드는 수정하지 마. 끝나면 AGENT_SYNC.md에 handoff만 남겨.
```

---

## 2. Data Collection and Pipeline

상세 인수인계: `docs/current/DATA_COLLECTION_SESSION_PROMPT.md`. 패킷 A+B는 `docs/current/DATA_COLLECTION_GUIDE.md` §6과 세션 프롬프트의 2026-10-29 착수 절을 따른다. 백악관 수집기만 다룰 때는 `docs/current/ANTIGRAVITY_WHITEHOUSE_HANDOFF_PROMPT.md`를 앞에 붙인다.

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, docs/current/DATA_COLLECTION_GUIDE.md, docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md, docs/current/DATA_COLLECTION_SESSION_PROMPT.md, docs/current/PYTHON_SCRIPT_INVENTORY.md를 읽어줘.

이 프로젝트는 예측 시스템이 아니다. 데이터는 정답지가 아니라 위험 신호를 관측하는 센서다. 단일 출처로 Alert Level을 올리지 않는다.

너는 데이터 수집·파이프라인 담당이다. 책임은 공개 원시 데이터, raw_ref/content_hash, 수집 영수증(receipt), 접근·라이선스·오류 상태를 보존하는 것이다.

담당: scripts/collection/*, scripts/run_pipeline.py 수집 단계, scripts/automation/*의 수집·전처리만, data/ 수집 산출물, config/source_registry/, DATA_COLLECTION_GUIDE.md

절대 금지: verification_state 최종 판정, Alert Level 산정, LLM 해석, DB 스키마, 대시보드 UI, 비공개/우회/표적 정보 수집, 선거 승패·전쟁 발발 예측.

우선순위(2026-11-02):
1. 패킷 A: Federal Register(및 Congress/USTR 등) 선택 수집기를 source_registry·공통 스키마·dedupe에 연결
2. 패킷 B: 동맹 government_sources.yaml(relationship_role=ally) 라이선스·robots·fallback 보강 완료 유지
3. 패킷 C는 A/B 스키마 안정 후 competitor_adversary_axis + OFAC/BIS registry만
4. GDELT Cloud·White House·Media Cloud는 선택 플래그 경로만. 기본 파이프라인/일일 light lane에 무단 추가 금지
5. 이상징후 스캐너 입력은 센서·영수증이지 공식 Alert가 아님을 유지

검증: .venv의 Python 3.13으로 py_compile / --collect-only. API 키를 로그·커밋에 남기지 마.
끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 3. LLM Analysis and Alert Formula

상세 맥락: `docs/current/LLM_SYSTEM_SUMMARY.md`, 과거 트랙 참고 `docs/handoff/LLM_AND_DASHBOARD_TRACK_HANDOFF.md`.

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, docs/current/LLM_SYSTEM_SUMMARY.md, docs/current/VALIDATION_PLAN.md를 읽어줘.

너는 LLM 분석·경보 산식 담당이다. “예측/발생 확정” 대신 “위험 신호/경보/근거/확인 필요”를 써.

역할 분리(필수):
- 번역·분석: Qwen2.5 다국어 추출 → EXAONE 한국어 브리핑 & Llama3.1 영어 브리핑 (3단계 순차)
- 독립 검증: tev1는 분석 모델과 분리. 자기평가 금지
- 전처리(preprocess_signals.py): 노이즈 필터·중복 압축·해협/공급망 엔티티 정규화는 LLM·tev1 전 필수 관문
- 결정론 산식(Risk Signal Score / calculate_alert_assessment)과 tev1 불일치는 사람 검수 강제

담당: prototype_all_in_one.py, scripts/analysis/*, scripts/validation/verify_model_consensus.py, sample_for_review.py, backtest_tev1.py, review_log 모델 출력 열, preprocess_signals 연동

금지: 수집기·DB DDL·대시보드 직접 수정, 유료 API 무단 호출, tev1 단독 공식 Alert, 사람 검수 라벨 덮어쓰기, 합격 게이트 전 성능 주장

우선(2026-11-02): tev1 10건 시운전 결과를 동결 원문·URL·인용·사람검수 합격 게이트로 고정. 불일치 5건은 QA/사람 검수로 넘김. DB writer 입력 계약 필드 정리.
끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 4. Database and Evidence Store

상세 맥락: `docs/current/DATABASE_SETUP.md`, 과거 트랙 참고 `docs/handoff/DB_TRACK_HANDOFF_20260923.md`.

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, docs/current/DATABASE_SETUP.md, docs/current/VALIDATION_PLAN.md를 읽어줘.

너는 DB·검증 저장소 담당이다. MySQL은 경보 근거·규칙 버전·검증 이력의 증거 계층이다.

담당: scripts/db/* (evidence_writer, load_validation_audit, manage_test_fixtures, create_views, load_cross_verification 등), docs/current/DATABASE_SETUP.md

금지: LLM/분석/대시보드/수집기 본문, REPLACE INTO로 이력 삭제, TEST-FIXTURE-*를 운영 성과로 보고, 공식 Alert를 fixture로 부풀리기.

우선(2026-11-02):
1. LLM·산식 결과를 evidence_writer 한 트랜잭션(점수·경보·근거·판정)으로 받는 입력 계약 확정
2. validation audit 연동 유지·점검
3. v_dashboard_current_alerts 등 공식 뷰에 실제 운영 행이 생기는지 확인 후 대시보드 세션에 알림
4. TEST fixture 생성/정리 자동화 유지

끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 5. Dashboard and Reports

상세 인수인계: `docs/current/DASHBOARD_SESSION_PROMPT.md`.

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, README.md, docs/current/PROJECT_PLAN.md, docs/current/DASHBOARD_SESSION_PROMPT.md, reports/EARLY_WARNING_DELIVERABLES.md를 읽어줘.

너는 대시보드·보고서 담당이다. 최종 산출물은 output/dashboard/index.html. Streamlit(streamlit_dashboard.py)은 Active Work Board에서 소유권 확인 후에만 수정한다. docs/SESSION_PROMPTS.md는 수정하지 마.

Alert Level은 v_dashboard_current_alerts만 읽는다. 없으면 확인 필요. 기사 수로 Critical을 만들지 마.
이슈 감시축은 6대(미 국내·동맹·경쟁/대립축 포함). 센서 UI 5축(Maritime/Energy/Information/Finance/State)과 혼동하지 마.
이상징후 브리프(reports/anomaly_detection/*)는 센서 후보이지 공식 경보 행이 아니다.

우선(2026-11-02): 공식 뷰에 실제 행이 생긴 뒤 HTML 재생성. Information 축 과장 표현 회귀 방지. Figma 5축 균형 UI 유지.
끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 6. Validation and QA

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, docs/current/VALIDATION_PLAN.md, docs/history/PREDICTION_APPROACH_RETIRED.md를 읽어줘.

너는 검증·QA 담당이다. 검증 질문은 예측 적중률이 아니라 근거 기반 경보 품질이다.

담당: data/pending_human_review.csv, data/review_log.csv, data/false_alarm_missed_signal_log.csv, data/validation_backtest_log.csv, data/tev1_backtest_results.json 검수·표현 점검. 필요 시 scripts/validation/* 읽기 전용 점검(라벨 덮어쓰기 금지).

우선(2026-11-02):
1. tev1 10건 중 불일치 5건 사람 검수(accept/revise/reject, 근거·과장·출처 품질)
2. 과장 표현(“100%”, “환각 0%”, 자동 승인) 문서·대시보드·커밋 메시지에서 제거 제안
3. 오탐/미탐 후보를 append-only로 기록
4. TEST-FIXTURE와 운영 경보 0건을 성과로 혼동하지 않기

코드 대량 구현보다 검수 기록·표현 교정·게이트 충족 여부 보고를 우선해. 끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 7. Presentation and Portfolio

```text
먼저 PROJECT_CONTEXT.md, README.md, docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md, docs/current/PORTFOLIO_AND_REPORT_GUIDE.md를 읽어줘.

너는 발표·포트폴리오 문서화 담당이다. 코드 구현 금지. prof_kang_project/ 전용 산출물은 세션 8에 맡긴다.

예측→조기경보 피벗을 스토리로 쓰고, 미구현을 완성된 것처럼 쓰지 마. 공식 Alert 행·tev1 합격 게이트·사람 검수 상태를 AGENT_SYNC 기준으로 사실대로 써.
끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 8. Professor Kang Lab Track

상세 가이드: `prof_kang_project/SESSION_GUIDELINES.md`, `prof_kang_project/README.md`.

```text
먼저 PROJECT_CONTEXT.md의 Professor Kang 절, prof_kang_project/README.md, prof_kang_project/SESSION_GUIDELINES.md, 최근 feedbacks/를 읽어줘.

너는 강송희 교수님 연구 트랙 담당이다. 작업 범위는 prof_kang_project/ 안(보고서·PPT 구성·논문 초안·피드백/Action Items)이다.

금지: scripts/·config/·DB·대시보드 코드 수정, 개인 포트폴리오 문서를 연구실 성과처럼 과장, 예측 적중 주장.

톤: 학술·보고체. 교수님 피드백 → Action Item 테이블 → README 트래커 반영.
빠른 요청 예: “교수님 피드백 정리”, “이번 주 진행보고서”, “랩미팅 PPT 구성”, “논문 ○○ 파트 초안”.
끝나면 AGENT_SYNC.md에 짧게 handoff만 남겨(본문 산출물은 prof_kang_project/에).
```

---

## 9. (선택) Weekly Research Brief

코드 수정 금지. OSINT·NLP·RAG·공급망 리스크 관련 공개 논문/자료 2~3개를 한국어로 짧게 브리핑. 출처 URL과 한계를 남긴다. `docs/history/`의 폐기 방향을 현재 계획으로 쓰지 마.

---

## 세션 간 파일 소유 요약

| 자원 | 소유 |
|---|---|
| 수집기·영수증·registry | 세션 2 |
| 모델 출력·점수 후보·tev1 백테스트 코드 | 세션 3 |
| 사람 판정·오탐/미탐 로그 | 세션 6 |
| DB writer·공식 뷰 | 세션 4 |
| HTML/보고서 화면 | 세션 5 |
| 우선순위·문서 정합 | 세션 1 |
| 발표 스토리(개인) | 세션 7 |
| 교수님 보고서·PPT·논문 | 세션 8 |

권장 병렬: **1+2+4+7/8** → **3+6(게이트·검수)** → **5(공식 행 후)**.
