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
| open | Codex | repo / docs / db | Multiple (`scripts/`, `docs/`, `data/`) | 저장소 구조 정리 및 DB/스크립트 리팩토링 진행 중 (작업 트리 수정분 보유) | 2026-09-28 |
| in-progress | ANTIGRAVITY | sync / conflict-review | `AGENT_SYNC.md` | 초기 동기화 및 세션 간 파일 충돌 가능성 점검 완료 후 대기 | 2026-09-28 |

Status 값은 `open`, `in-progress`, `review-needed`, `done`, `blocked` 중 하나를 쓴다.

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

## Prompt for ANTIGRAVITY

ANTIGRAVITY에 새 작업을 맡길 때는 아래 문장을 먼저 붙인다.

```text
먼저 PROJECT_CONTEXT.md와 AGENT_SYNC.md를 읽고 현재 프로젝트 방향과 다른 AI 세션의 작업 상태를 파악해줘.

이 프로젝트는 국제정세 예측 시스템이 아니라 공급망·지정학 리스크 조기경보 시스템이다. 예전 예측/챗봇 문서는 docs/history 또는 docs/archive의 이력으로만 봐.

작업 시작 전 git status --short를 확인하고, AGENT_SYNC.md의 Active Work Board에 네가 맡을 영역과 파일을 기록해줘. 이미 다른 도구가 수정 중인 파일은 충돌 가능성을 먼저 보고해줘.
```

