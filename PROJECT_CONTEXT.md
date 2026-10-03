# Project Context for AI Assistants

이 파일은 새 AI 세션이나 다른 도구가 이 저장소를 읽을 때 가장 먼저 봐야 하는 진입점이다. 자세한 개발 로그보다 현재 방향을 우선한다.

## Current Identity

이 저장소의 현재 목표는 국제정세 사건을 단정적으로 예측하는 것이 아니다. 현재 목표는 뉴스, 정부 공식 발표, 현지 독립 언론, GDELT Cloud 사건, 해협·항만 및 운임/보험료 센서, Google Trends, 현지 공개 여론, 여론조사, 금융·무역 지표를 종합해 공급망 및 지정학 리스크의 조기경보를 제공하는 것이다.

이 프로젝트는 언론사를 대체하거나 기사처럼 사실을 발행하는 서비스가 아니다. 공식 발표와 언론 보도는 기본 배경과 검증 기준으로 사용하되, 차별점은 언론이 아직 기사화하지 않았거나 단일 사건으로 정리하지 않은 공개 신호를 구조화하는 데 있다. 검색량 급등, 해협·항만 병목, 운임·보험료 변화, GDELT 사건 확산, 현지 공개 포럼·Telegram·Bluesky 표현 변화, 공식 발표와 독립 보도 간 괴리를 모아 “확정 사실”이 아니라 “추가 확인할 위험 징후”로 제시한다.

따라서 현재 정체성은 뉴스 자동화가 아니라 **OSINT 기반 리스크 인텔리전스 프로토타입**이다. 비전통 신호는 항상 출처, 수집 시각, 검증 상태, 한계와 함께 표시해야 하며, 단일 출처만으로 Alert Level을 확정하지 않는다.

핵심 산출물은 `output/dashboard/index.html` 대시보드다. Markdown, PDF, Word 보고서와 MySQL 뷰는 대시보드를 뒷받침하는 증거 자료로 본다.

## Important Direction Change

초기에는 "AI가 앞으로 어떤 국제정세 이슈가 발생할지 예측하는 시스템"을 목표로 했다. 그러나 미래 사건의 정답 정의, 장기 검증 필요성, 오탐·미탐 해석 문제 때문에 취업용 개인 포트폴리오에서 신뢰성 있게 방어하기 어렵다고 판단했다.

따라서 현재 방향은 다음과 같이 바뀌었다.

- 폐기한 목표: 미래 국제정세 사건을 맞히는 예측 시스템
- 현재 목표: 관측 가능한 데이터 신호를 기반으로 위험 증가를 탐지하는 조기경보 시스템
- 검증 질문: "사건을 맞혔는가"가 아니라 "위험 신호를 근거 기반으로 일관되게 포착했는가"

대외 문서에서는 이 전환을 기능 축소나 실패로 설명하지 않는다. 핵심 메시지는 “예측의 검증 한계를 발견했고, 이미 구축한 수집·분석 자산을 감사 가능한 조기경보 문제로 재설계했다”이다. 발표 구조와 질문 대응은 `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md`를 기준으로 한다.

이 프로젝트는 졸업작품이 아니라 개인 포트폴리오 프로젝트다. 졸업작품 또는 팀 프로젝트와 혼동하지 말고, 채용 담당자·면접관에게 보여줄 개인 프로젝트 기준으로 설명한다.

예전 문서에 "예측", "챗봇 전환", "자동 게시" 같은 표현이 남아 있어도 현재 방향으로 해석하면 안 된다. 그런 문서는 이력 또는 보류 문서다.

## Recommended Reading Order

1. `README.md`
2. `PROJECT_CONTEXT.md`
3. `AGENT_SYNC.md` when multiple AI tools such as Codex and ANTIGRAVITY are working in parallel
4. `docs/current/PROJECT_PLAN.md`
5. `docs/current/VALIDATION_PLAN.md`
6. `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md` when explaining the project externally
7. `docs/current/DATA_COLLECTION_GUIDE.md`
8. `docs/current/DATA_COLLECTION_ROADMAP.md` when planning sensor expansion
9. `docs/current/DATA_COLLECTION_SESSION_PROMPT.md` when starting a data-collection session
10. `docs/current/DASHBOARD_SESSION_PROMPT.md` when starting a dashboard/UI session
11. `docs/current/LLM_SYSTEM_SUMMARY.md`
12. `docs/current/DATABASE_SETUP.md` when database context is needed
13. `docs/SESSION_PROMPTS.md` when starting role-specific AI sessions
14. `docs/REPOSITORY_STRUCTURE.md` when moving or classifying files
15. `project-handoff.md` only when detailed history or coordination context is needed
16. `docs/history/PROJECT_EVOLUTION_TIMELINE.md` when the pivot story is needed

## Notion Hub

Notion hub page: https://app.notion.com/p/3eede224b44181f0bd20ea55620bf5c4?pvs=204

Use Notion for human-facing project management, learning notes, weekly plans, and decision summaries. Do not treat Notion as the source of truth for code, data, or formal project direction. If Notion and GitHub differ, GitHub Markdown files in this repository take precedence.

## Current Planning Documents

- `docs/current/PROJECT_PLAN.md`: current early-warning project plan
- `docs/current/DATA_COLLECTION_GUIDE.md`: data collection strategy for warning signals
- `docs/current/DATA_COLLECTION_ROADMAP.md`: staged data-source expansion and source-registry plan
- `docs/current/DATA_COLLECTION_SESSION_PROMPT.md`: handoff prompt for data-collection sessions
- `docs/current/VALIDATION_PLAN.md`: validation plan for warning quality, not prediction accuracy
- `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md`: presentation and portfolio narrative for external readers
- `docs/current/LLM_SYSTEM_SUMMARY.md`: LLM routing and analysis architecture
- `docs/current/DATABASE_SETUP.md`: MySQL schema and evidence storage layer

## History Documents

- `docs/history/PROJECT_EVOLUTION_TIMELINE.md`: full timeline from prediction concept to early-warning pivot
- `docs/history/PREDICTION_APPROACH_RETIRED.md`: why the prediction approach was retired
- `docs/history/CHATBOT_PIVOT_RETIRED.md`: why the chatbot pivot was parked
- `docs/handoff/`: handoff reports from role-specific AI sessions
- `docs/evidence/`: backtests, peer review artifacts, and validation evidence
- `docs/archive/`: old planning and handoff documents retained for traceability

## Reuse Policy

Most existing code and data should not be discarded. They are reused with a different interpretation.

- News, RSS, GDELT Cloud events, and review logs become warning-signal inputs.
- Government announcements become official-position signals.
- Independent/local media, public Telegram, Bluesky, local forums, Google Trends, and Reddit become non-official public information-environment signals.
- Maritime chokepoint, port, freight/insurance, financial, and trade data become supply-chain proxy signals.
- LLM tone classification becomes framing and risk-signal extraction.
- Model consensus and human review become trust and validation layers.

## Terms to Prefer

Use these terms in new docs and reports.

- early warning
- risk signal
- signal gap
- alert level
- evidence coverage
- human review
- validation by backtest and review
- OSINT-based risk intelligence
- non-traditional public signals
- verification state
- information gap
- corroborated signal

Avoid these terms unless discussing retired history.

- prediction accuracy
- future event prediction
- guaranteed forecast
- fully automated geopolitical prediction
- AI news outlet
- breaking-news automation
- confirmed fact from unverified data

## Git and Documentation Notes

When updating documentation, keep current plans and retired history separate. Do not merge everything into one huge Markdown file. Add concise links from `README.md` and this file instead.

For GitHub commits, prefer small focused commits. A good documentation-only commit is:

```bash
git add README.md PROJECT_CONTEXT.md docs/current docs/history docs/handoff docs/evidence docs/SESSION_PROMPTS.md docs/REPOSITORY_STRUCTURE.md project-handoff.md
git commit -m "docs: clarify early warning project context"
git push origin main
```

## File Organization Rule

Keep the repository root small. Root-level files should be entrypoints or active project-wide coordination files only. Detailed current docs go under `docs/current/`, retired plans under `docs/history/` or `docs/archive/`, role handoffs under `docs/handoff/`, validation evidence under `docs/evidence/`, and temporary scripts or scratch outputs under `scratch/`.

Do not move executable scripts from `scripts/` unless you also update every caller and verify the pipeline, because many scripts assume repository-relative paths.

When Codex and ANTIGRAVITY or another AI tool work in parallel, use `AGENT_SYNC.md` as the shared task board before editing files.
