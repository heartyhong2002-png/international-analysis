# AI Session Prompts

새 AI 세션을 열 때 아래 프롬프트를 복사해 첫 메시지로 사용한다.

공통 규칙:
1. 모든 세션은 `PROJECT_CONTEXT.md`와 `AGENT_SYNC.md`를 먼저 읽는다.
2. 역할을 고르기 전에 전체 맥락이 필요하면 `docs/current/AI_SESSION_HANDOFF_PROMPT.md`를 먼저 사용한다.
3. `docs/history/`, `docs/archive/`의 예측·챗봇 자료는 이력일 뿐 현재 계획이 아니다.
4. 작업 시작 전 `git status --short`를 확인하고, Active Work Board에 담당 영역·파일을 등록한다.
5. 다른 세션이 `in-progress`인 파일은 조율 없이 수정하지 않는다.
6. 작업이 끝나면 `AGENT_SYNC.md`에 한 일·바꾼 파일·확인한 것·다음 작업·주의할 점을 짧게 남긴다.
7. 표준 런타임은 **Python 3.13** (프로젝트 `.venv`). PATH의 구형 Python을 쓰지 않는다.

기준일: 2026-10-30. 공식 경보 행은 운영상 0건일 수 있으며, `TEST-FIXTURE-*`는 합성 회귀 테스트일 뿐 운영 성과가 아니다.

---

## 0. 전체 프로젝트 공통 시작 (역할 선택 전)

역할별 프롬프트 대신, 새 AI에게 전체 상태를 먼저 받게 하려면 `docs/current/AI_SESSION_HANDOFF_PROMPT.md`를 그대로 복사한다.

그다음 아래 한 줄을 덧붙인다.

```text
위 인수인계를 읽고, 구현됨 / 부분 구현 / 향후 계획을 구분해 요약해줘. 그 다음 docs/SESSION_PROMPTS.md의 역할 중 하나를 고를 수 있게, 지금 병렬로 열 수 있는 세션과 의존 순서를 제안해줘. 코드는 아직 수정하지 마.
```

---

## 1. Control Tower

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, README.md, docs/current/PROJECT_PLAN.md, docs/current/VALIDATION_PLAN.md, docs/SESSION_PROMPTS.md를 읽어줘.

이 프로젝트는 국제정세 사건 예측 시스템이 아니라, 공급망·지정학 리스크 조기경보 시스템이다. 예전 예측/챗봇 문서는 docs/history 또는 docs/archive의 이력으로만 봐. 교수님 연구실 참여는 미확정이며, 개인 프로젝트와 연구실 프로젝트를 합치지 마.

너는 컨트롤타워 담당이다. 전체 방향, 작업 우선순위, 문서 정합성, 세션 간 역할 충돌 방지, Git 커밋 단위 정리를 맡는다. 수집기·LLM 산식·DB 스키마·대시보드 구현은 직접 하지 말고, 어느 세션이 맡아야 하는지만 제안해.

우선순위(조율용):
1. DB writer가 점수·경보·근거·판정을 한 트랜잭션으로 저장
2. LLM이 그 계약으로 결과 전달 + 10건 이상 동결 백테스트 준비
3. 수집은 패킷 A(미 국내 공식)+B(동맹 registry) 동시, 이후 C(경쟁·대립축 role)
4. 공식 뷰에 실제 행이 생긴 뒤 대시보드 HTML 재생성
5. QA가 과장 표현·오탐/미탐 기록 점검
6. 발표 문서는 현재 구현 상태에 맞추기

담당 범위 밖 코드는 수정하지 마. 끝나면 AGENT_SYNC.md에 handoff만 남겨.
```

---

## 2. Data Collection and Pipeline

상세 인수인계가 필요하면 `docs/current/DATA_COLLECTION_PIPELINE_HANDOFF_PROMPT.md`를 이 프롬프트 앞에 붙인다. 패킷 A+B는 `docs/current/DATA_COLLECTION_GUIDE.md` §6과 `DATA_COLLECTION_SESSION_PROMPT.md`의 2026-10-29 착수 절을 따른다.

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, docs/current/DATA_COLLECTION_GUIDE.md, docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md, docs/current/PYTHON_SCRIPT_INVENTORY.md를 읽어줘.

이 프로젝트는 예측 시스템이 아니다. 데이터는 정답지가 아니라 위험 신호를 관측하는 센서다. 단일 출처로 Alert Level을 올리지 않는다.

너는 데이터 수집·파이프라인 담당이다. 책임은 공개 원시 데이터, raw_ref/content_hash, 수집 영수증(receipt), 접근·라이선스·오류 상태를 보존하는 것이다.

담당: scripts/collection/*, scripts/run_pipeline.py 수집 단계, data/ 수집 산출물, config/source_registry/, DATA_COLLECTION_GUIDE.md

절대 금지: verification_state 최종 판정, Alert Level 산정, LLM 해석, DB 스키마, 대시보드 UI, 비공개/우회/표적 정보 수집.

우선순위: 패킷 A(Federal Register·Congress·USTR 등)+패킷 B(동맹 registry) 동시. 패킷 C는 role/OFAC·BIS registry를 A/B 다음에.

검증: .venv의 Python 3.13으로 py_compile / --collect-only. API 키를 로그·커밋에 남기지 마.
끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 3. LLM Analysis and Alert Formula

상세 인수인계가 필요하면 `docs/current/LLM_HANDOFF_PROMPT.md`를 앞에 붙인다.

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, docs/current/LLM_SYSTEM_SUMMARY.md, docs/current/VALIDATION_PLAN.md, docs/current/LLM_HANDOFF_PROMPT.md를 읽어줘.

너는 LLM 분석·경보 산식 담당이다. “예측/발생 확정” 대신 “위험 신호/경보/근거/확인 필요”를 써.

담당: prototype_all_in_one.py, scripts/analysis/*, scripts/validation/verify_model_consensus.py, sample_for_review.py, backtest_tev1.py, review_log 모델 출력 열.

금지: 수집기·DB DDL·대시보드 직접 수정, 유료 API 무단 호출, tev1 단독 공식 Alert, 사람 검수 라벨 덮어쓰기.

우선: 동결 원문·사람 라벨 포함 10건+ 백테스트 준비, DB writer 입력 계약 정리.
끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 4. Database and Evidence Store

상세 인수인계: `docs/current/DATABASE_VALIDATION_SESSION_PROMPT.md`.

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, docs/current/DATABASE_SETUP.md, docs/current/VALIDATION_PLAN.md, docs/current/DATABASE_VALIDATION_SESSION_PROMPT.md를 읽어줘.

너는 DB·검증 저장소 담당이다. MySQL은 경보 근거·규칙 버전·검증 이력의 증거 계층이다.

담당: scripts/db/*, docs/current/DATABASE_SETUP.md
금지: LLM/분석/대시보드/수집기 본문, REPLACE INTO로 이력 삭제, TEST fixture를 성과로 보고.

우선: 점수·경보·근거·판정 트랜잭션 writer, validation audit 연결, TEST fixture 생성/정리 자동화.
끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 5. Dashboard and Reports

상세 인수인계: `docs/current/DASHBOARD_SESSION_PROMPT.md`.

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, README.md, docs/current/PROJECT_PLAN.md, docs/current/DASHBOARD_SESSION_PROMPT.md, reports/EARLY_WARNING_DELIVERABLES.md를 읽어줘.

너는 대시보드·보고서 담당이다. 최종 산출물은 output/dashboard/index.html.

Alert Level은 v_dashboard_current_alerts만 읽는다. 없으면 확인 필요. 기사 수로 Critical을 만들지 마.
이슈 감시축은 6대(미 국내·동맹·경쟁/대립축 포함). 센서 UI 5축(Maritime 등)과 혼동하지 마.
끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 6. Validation and QA

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, docs/current/VALIDATION_PLAN.md, docs/history/PREDICTION_APPROACH_RETIRED.md를 읽어줘.

너는 검증·QA 담당이다. 검증 질문은 예측 적중률이 아니라 근거 기반 경보 품질이다.
과장 표현(“100%”, “환각 0%”)을 제거하고, 사람 판정·오탐/미탐을 append-only로 남긴다.
끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 7. Presentation and Portfolio

```text
먼저 PROJECT_CONTEXT.md, README.md, docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md, docs/current/PORTFOLIO_AND_REPORT_GUIDE.md를 읽어줘.

너는 발표·포트폴리오 문서화 담당이다. 코드 구현 금지.
예측→조기경보 피벗을 스토리로 쓰고, 미구현을 완성된 것처럼 쓰지 마. 연구실 참여는 미확정.
끝나면 AGENT_SYNC.md에 handoff를 남겨.
```

---

## 8. (선택) Weekly Research Brief

`docs/history/WEEKLY_RESEARCH_BRIEF_HANDOFF.md` 참고. 코드 수정 금지. OSINT·NLP·RAG 논문 2~3개 한국어 브리핑.

---

## 세션 간 파일 소유 요약

| 자원 | 소유 |
|---|---|
| 수집기·영수증 | 세션 2 |
| 모델 출력·점수 후보 | 세션 3 |
| 사람 판정·오탐/미탐 | 세션 6 |
| DB writer·공식 뷰 | 세션 4 |
| HTML/보고서 화면 | 세션 5 |
| 우선순위·문서 정합 | 세션 1 |
| 발표 스토리 | 세션 7 |

권장 병렬: **1+2+4+7** → **3(DB 계약 후)** → **5+6(공식 행 후)**.
