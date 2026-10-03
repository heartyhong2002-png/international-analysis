# Notion 프로젝트 운영보드 템플릿

이 문서는 Notion에 붙여넣어 사용할 프로젝트 관리 보드 템플릿이다.

GitHub의 `AGENT_SYNC.md`는 AI 세션들이 읽는 작업 동기화 파일이고, Notion은 사람이 전체 진행 상황을 보기 위한 운영 화면으로 사용한다.

현재 생성된 Notion 프로젝트 허브:

https://app.notion.com/p/3eede224b44181f0bd20ea55620bf5c4?pvs=204

---

# 국제정세 조기경보 프로젝트 운영보드

## 1. 프로젝트 한 줄 정의

국제정세 사건을 단정적으로 예측하는 AI가 아니라, 뉴스·정부 발표·독립 언론·GDELT Cloud 사건·해협/항만·Google Trends·현지 공개 여론·금융/무역 지표를 교차검증해 공급망 및 지정학 리스크의 조기경보 신호를 제시하는 시스템.

## 2. 현재 방향

- 현재 목표: 공급망·지정학 리스크 조기경보 시스템
- 폐기한 목표: 미래 국제정세 사건 예측 시스템
- 핵심 산출물: `output/dashboard/index.html`
- 핵심 검증 기준: 예측 적중률이 아니라 경보 근거, 출처 다양성, 사람 검수, 백테스트, 오탐·미탐 기록

## 3. 운영 원칙

- 새 AI 세션은 먼저 `PROJECT_CONTEXT.md`와 `AGENT_SYNC.md`를 읽는다.
- 작업 전 `git pull`과 `git status --short`를 확인한다.
- 같은 파일을 여러 세션이 동시에 수정하지 않는다.
- 문서, 코드, 데이터 커밋은 가능하면 분리한다.
- “예측”, “발생 확정”, “100% 정확도”, “환각 0%” 같은 표현은 현재 산출물에서 피한다.

---

# 작업 보드

Notion에서는 아래 표를 데이터베이스로 만들고, 보기(View)를 `Board by Status`, `Table by Area`, `Calendar by Due Date`로 나누면 좋다.

| Status | Priority | Owner | Area | Task | Files / Links | Due Date | Notes |
|---|---|---|---|---|---|---|---|
| Not started | High | Codex | Coordination | AGENT_SYNC 기준으로 작업 충돌 관리 | `AGENT_SYNC.md` |  | 새 세션 시작 전 확인 |
| Not started | High | ANTIGRAVITY | Dashboard | 조기경보 대시보드 화면 개선 | `output/dashboard/`, `scripts/streamlit_dashboard.py` |  | 예측 표현 금지 |
| Not started | High | Codex | Validation | 검증 계획과 실제 로그 파일 정합성 점검 | `docs/current/VALIDATION_PLAN.md`, `data/validation_backtest_log.csv` |  | 백테스트 템플릿 확인 |
| Not started | Medium | ANTIGRAVITY | Pipeline | 수집기 실행 오류 확인 | `scripts/`, `data/` |  | 실행 결과는 별도 커밋 |
| Not started | Medium | Codex | Portfolio | 발표/포트폴리오 서사 정리 | `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md` |  | 교수/면접관 관점 |

## Status 값

- Not started
- In progress
- Review needed
- Blocked
- Done

## Priority 값

- High
- Medium
- Low

## Area 값

- Coordination
- Documentation
- Data Collection
- LLM / Alert Formula
- Database
- Dashboard
- Validation / QA
- Portfolio
- GitHub / Release

---

# 세션별 역할

## Codex

주 역할:

- 전체 방향 정리
- 문서 정합성 점검
- GitHub 커밋 단위 정리
- ANTIGRAVITY 작업 결과 리뷰
- 충돌 해결

맡기기 좋은 작업:

- “현재 변경 파일을 커밋 단위로 나눠줘”
- “문서끼리 모순되는 내용 찾아줘”
- “AGENT_SYNC.md 기준으로 다음 작업을 정리해줘”
- “발표용으로 설명이 과장되지 않았는지 봐줘”

## ANTIGRAVITY

주 역할:

- 기능 구현
- UI/대시보드 수정
- 수집기/파이프라인 실행 점검
- 코드 자동 수정

맡기기 좋은 작업:

- “대시보드에 Alert Level 카드 추가해줘”
- “수집기 실행 오류 고쳐줘”
- “DB 뷰를 대시보드가 읽기 좋게 바꿔줘”
- “보고서 생성 스크립트 출력 형식을 수정해줘”

---

# 현재 산출물 체크리스트

## 문서

- [ ] `README.md`가 현재 방향을 정확히 설명한다.
- [ ] `PROJECT_CONTEXT.md`가 새 세션 진입점 역할을 한다.
- [ ] `AGENT_SYNC.md`가 최신 작업 상태를 반영한다.
- [ ] `docs/current/PROJECT_PLAN.md`가 조기경보 기준으로 되어 있다.
- [ ] `docs/current/VALIDATION_PLAN.md`가 예측 정확도 대신 경보 품질 검증을 설명한다.
- [ ] `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md`가 발표 흐름으로 바로 쓸 수 있다.

## 코드

- [ ] 수집 파이프라인이 실행된다.
- [ ] Risk Signal Score와 Alert Level 산식이 문서와 일치한다.
- [ ] DB 스키마가 경보 근거와 검증 로그를 저장한다.
- [ ] 대시보드가 예측 표현 없이 조기경보 화면을 보여준다.
- [ ] 보고서 생성 스크립트가 근거·검증 상태를 포함한다.

## 데이터 / 검증

- [ ] `data/validation_backtest_log.csv`에 백테스트 기록이 쌓인다.
- [ ] `data/false_alarm_missed_signal_log.csv`에 오탐·미탐 후보가 기록된다.
- [ ] `data/review_log.csv`에 사람 검수 결과가 남는다.
- [ ] 수집 데이터와 실행 결과 커밋이 코드 커밋과 분리된다.

---

# 주간 점검 템플릿

## 이번 주 완료

- 

## 진행 중

- 

## 막힌 것

- 

## 다음 우선순위

1. 
2. 
3. 

## GitHub 상태

- 마지막 push:
- 미커밋 변경:
- 충돌 가능 파일:

---

# 다른 AI 세션 시작 프롬프트

아래 문장을 Codex, ANTIGRAVITY, 다른 AI 세션에 붙여넣는다.

```text
먼저 PROJECT_CONTEXT.md와 AGENT_SYNC.md를 읽고 현재 프로젝트 방향과 다른 AI 세션의 작업 상태를 파악해줘.

이 프로젝트는 국제정세 예측 시스템이 아니라 공급망·지정학 리스크 조기경보 시스템이다. 예전 예측/챗봇 문서는 docs/history 또는 docs/archive의 이력으로만 봐.

작업 시작 전 git pull을 해서 최신 GitHub 상태를 받고, git status --short를 확인해줘. 그 다음 AGENT_SYNC.md의 Active Work Board에 네가 맡을 영역과 파일을 기록해줘. 이미 다른 도구가 수정 중인 파일은 충돌 가능성을 먼저 보고해줘.

작업이 끝나면 바꾼 파일, 확인한 것, 다음 작업, 주의할 점을 AGENT_SYNC.md 또는 project-handoff.md에 짧게 남겨줘.
```

---

# Notion과 GitHub 역할 분리

| 위치 | 역할 |
|---|---|
| Notion | 사람이 보는 프로젝트 관리 화면 |
| `AGENT_SYNC.md` | AI 세션이 읽는 작업 동기화판 |
| `PROJECT_CONTEXT.md` | 프로젝트 방향의 기준 문서 |
| `project-handoff.md` | 긴 개발 이력과 의사결정 로그 |
| GitHub commit | 실제 변경 이력 |

Notion에 적힌 내용이 GitHub 문서와 다르면 GitHub 문서를 우선한다.

