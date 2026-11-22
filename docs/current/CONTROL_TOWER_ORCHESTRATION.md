# 컨트롤타워 + 서브세션 오케스트레이션 모델

기준일: 2026-11-22. 이 문서는 다중 AI 세션 분업 운영 방식을 대체하는 **실행 프로토콜**이다.
기존 `docs/SESSION_PROMPTS.md`의 역할 정의(1~10)는 폐기하지 않고, 그 내용을 서브세션
파견 프롬프트의 원본 재료로 재사용한다.

## 1. 왜 전환하나

기존 모델: 사람이 독립 챗세션(Codex/ANTIGRAVITY/Cursor/Qwen)을 각각 기동 → `AGENT_SYNC.md`
MD 보드와 handoff 문서로 조율 → "자기 담당 파일 건드리지 말기"는 규약.

실제로 관측된 비용:
- 보드가 1,000줄대로 썩어 매 세션이 시작마다 재독 (토큰·컨텍스트 오염)
- 파일 충돌이 사후 발견 (`build_database.py` 덮어쓰기 사고) — 규칙이지 장치가 아님
- handoff가 문서 전파 방식이라 조율 지연, 컨트롤타워가 다른 세션의 작업 중간 상태를 못 봄
- Trio-Sync·작업 로그 등 메타업무가 실작업과 경쟁

새 모델: **대화형 세션은 컨트롤타워 하나만** 남긴다. 트랙 작업은 컨트롤타워가
서브세션(fresh context, 자체 transcript)으로 파견하고, 결과가 자동으로 복귀한다.
조율 채널은 대화가 아니라 **파일 스코프 + 파견 기록**이고, `AGENT_SYNC.md`는
"조업 보드"에서 **"컨트롤타워가 발행하는 결과 기록"**으로 격하된다.

## 2. 3대 원칙

1. **판단은 컨트롤타워, 실행은 서브세션.** 우선순위·범위 결정·diff 리뷰·commit·push·
   보드/Notion 반영·사용자 보고는 항상 컨트롤타워가 직접 한다. 서브세션에는
   "뭘 만들지"가 아니라 "어디까지, 뭐로 검증하고, 뭘 보고할지"가 확정된 과제를 던진다.
2. **파견 프롬프트는 자기완결(self-contained).** 서브세션은 이 대화를 보지 못한다.
   목적·배경·必读 파일·파일 스코프·금지사항·검증 명령·출력 형식을 모두 프롬프트에 담는다.
   "알아서 조사해서 고쳐와" 식의 이해 위임(no delegation of understanding)은 금지.
3. **서브세션은 커밋·보드 수정 금지.** git과 `AGENT_SYNC.md`/Notion 쓰는 권한은
   컨트롤타워에 단일화한다. 충돌 가능성이 구조적으로 사라진다.

## 3. 파견 단위 선택

| 도구 | 언제 | 특징 |
|---|---|---|
| `create_sub_session` (completion=`sent`) | 병렬로 돌리는 실작업(구현·수집·검증 실행) | 즉시 반환, 완료 시 알림으로 결과 수신. `sessionId`로 후속 지시 가능(컨텍스트 유지) |
| `create_sub_session` (completion=`first-turn`) | 결과가 직하단의 결정에 필요한 단발 작업 | 그 자리에서 결과 대기 |
| `agent` (하위 에이전트) | 읽기 전용 조사·파일 탐색, 결과만 텍스트로 필요한 경우 | 도구 실행 범위가 좁은 보조 조사원 |
| `send_message` / fork | 컨트롤타워 자기 대화의 최근 맥락을 상속받아 분기 실행할 때만 | 예: 대시보드 재생성처럼 "방금 논의한 내용"을 그대로 수행시킬 때 |
| 기존 독립 챗세션(Cursor 등) | 사용자가 명시적으로 별도 창에서 작업할 때 | §A 상태 확인 프로토콜로만 조율. 이 모델의 파견 대상이 아님 |

## 4. 파견 프롬프트 계약 (필수 7블록)

`docs/SESSION_PROMPTS.md`의 해당 역할 텍스트를 아래 골격에 끼워 넣는다.

```text
[목적] 한 문장 산출물 정의. 예: "preprocess_signals.py에 페르시아어 분리 규칙을 추가하고 --self-test 통과"
[배경] 프로젝트 정체성 1줄(예측 아님, 조기경보) + 현재 상태 + 이미 배제한 것. 서브세션은 다른 세션 진행 상황을 모르므로 겹치는 작업이 있으면 "누가 어떤 파일 중이니 건드리지 마"를 명시.
[필독] PROJECT_CONTEXT.md, AGENT_SYNC.md §해당 handoff, 역할별 docs/current/* (SESSION_PROMPTS.md의 역할 헤더 목록 재사용)
[파일 스코프] 수정 가능: glob 목록 / 읽기 전용: 목록 / 절대 금지: 목록 (SESSION_PROMPTS.md 파일 소유표의 '담당/금지'를 그대로 이식)
[실행 제약] 표준 인터프리터 .venv Python 3.13. 커밋·push 금지. AGENT_SYNC.md·보드 수정 금지. 유료 API·GDELT Cloud 플래그 외 기본 파이프라인 변경 금지.
[검증] 반드시 실행할 명령과 통과 기준. 예: py_compile, --self-test, --collect-only, --limit 3 로컬 실행 후 산출물 육안 확인.
[출력 형식] 10줄 이내로: 한 일 / 바꾼 파일 / 확인한 것(명령+결과 요약) / 미해결·리스크 / 다음 제안.
```

## 5. worked example — 역할 2-1(전처리) 파견

```text
[목적] scripts/automation/preprocess_signals.py에 페르시아어(fa) 언어 분리 규칙을
추가하고 High-Purity 클러스터의 행위자(who) 미상률을 낮춘다.

[배경] 이 프로젝트는 국제정세 예측이 아니라 OSINT 기반 공급망·지정학 리스크 조기경보
시스템이다. 전처리는 LLM/검증 전 필수 관문이다. 2026-11-20 보드 handoff에 따르면
미상률이 22.7%→6.3%로 개선된 상태이며, 이번엔 그 후속으로 fa 분리 엣지케이스를
점검한다. 같은 시각 다른 파견이 scripts/collection/*를 수정 중이니 건드리지 마.

[필독] PROJECT_CONTEXT.md, AGENT_SYNC.md 최신 handoff 블록(2026-11-20),
docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md, docs/current/PREPROCESSING_SESSION_PROMPT.md

[파일 스코프] 수정: scripts/automation/preprocess_signals.py, data/automation/* 재생산 산출물
읽기 전용: scripts/pipeline/bridge_preprocess_lanes.py, config/source_registry/*
금지: scripts/collection/*(다른 파견 소유), dags/*, MySQL DDL, 대시보드 UI

[실행 제약] .venv Python 3.13만 사용. 커밋·push 금지. AGENT_SYNC.md 수정 금지.

[검증] preprocess_signals.py --self-test 통과 + 최신 입력 재실행 후
canonical_signals_high_purity_latest.json의 who 미상률 수치 변화 확인(개선 보고).

[출력 형식] 한 일 / 바꾼 파일 / 확인한 것 / 미해결·리스크 / 다음 제안 (10줄 이내)
```

## 6. 동시 파견 규칙

- **스코프 비교집합이면 병렬.** `sent`로 여러 개 던지고 결과 알림을 받는다.
  권장 병렬은 SESSION_PROMPTS.md의 기존 추천과 동일(2+4, 7/8 등).
- **의존이면 직렬 or 후속 파견.** 예: DB 세션 결과 확인 후 대시보드 파견. 같은
  `sessionId`에 `--reveal`/후속 지시를 보내 컨텍스트를 재사용한다.
- **스코프가 겹치면** (a) 직렬화하거나, (b) 트랙별 git worktree + 브랜치에서
  작업시키고 merge는 컨트롤타워만 (diff 리뷰가 곧 QA가 된다). 현재 Qwen Code
  세션 자체가 이미 worktree에서 도는 형태를 지원하고 있다.
- **중복 실행 금지.** 파견한 과제를 같은 내용으로 다시 조사/실행하지 말 것.

## 7. 컨트롤타워 소비 루프

1. 과제 분해: 파일 스코프가 겹치지 않게 쪼갠다.
2. 파견: §4 골격 프롬프트, 병렬이면 `sent`.
3. 수신: 결과 블록 5종을 읽는다. 불충분하면 같은 `sessionId`로 후속 1회만 더 지시(재파견은 스코프 변경 시에만).
4. diff 리뷰: `git diff`로 실제 변경을 확인 — 서브세션의 자기보고를 그대로 신뢰하지 않는다.
5. 검증 재실행: 컨트롤타워가 자체 명령으로 최종 확인(테스트·생성물).
6. 커밋: 작은 focused commit. 커밋 메시지는 출력 형식의 '한 일/확인한 것'에서 생성.
7. 보드 반영: `AGENT_SYNC.md`에 handoff 블록 1개 + Active Work Board 줄 1개를 **컨트롤타워가** 작성.
8. (명시 요청 시) Trio-Sync §B: MD → Notion → GitHub. 파견 기록이 곧 생성 소스.

## 8. 보드·문서 역할 변화

| 문서 | 이전 | 이후 |
|---|---|---|
| `AGENT_SYNC.md` | 세션 간 실시간 조율 보드 | 컨트롤타워만 쓰는 발행 기록 + 상태 확인(§A) 기준 |
| `docs/SESSION_PROMPTS.md` | 사람이 복사해 새 챗세션에 붙여넣는 시작 프롬프트 | 파견 프롬프트의 역할 원본(1~10) + 파일 소유표 |
| `project-handoff.md` | 세션 간 조율·작업 로그 | 의사결정 히스토리 전용(실시간 조율 기능 종료) |
| Notion 보드 | 수동 동기화 | 파견 기록에서 생성(§B 실행 시) |

외부 도구(Cursor/ANTIGRAVITY)가 아직 독립 세션으로 참여하는 기간 동안은 기존
§A 상태 확인 규약이 유효하다. 이 모델은 그들을 대체하도록 권장하되, 강요하지 않는다.

## 9. 마이그레이션 순서

1. (완료) 이 문서 작성 + 보드/문서에 포인터 등록.
2. 다음 실작업부터 컨트롤타워 1세션 체제로 파견 실행 — 스크립트 변경 없음.
3. 잘 작동하면 `SESSION_PROMPTS.md` 기준일·common 규칙에 파견 모드 기본화 반영.
4. 원하면 §3의 `agent_tasks` MySQL 큐로 보드를 기계화(별도 후속 과제).
