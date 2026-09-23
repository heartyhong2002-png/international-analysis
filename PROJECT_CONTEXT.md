# Project Context for AI Assistants

이 파일은 새 AI 세션이나 다른 도구가 이 저장소를 읽을 때 가장 먼저 봐야 하는 진입점이다. 자세한 개발 로그보다 현재 방향을 우선한다.

## Current Identity

이 저장소의 현재 목표는 국제정세 사건을 단정적으로 예측하는 것이 아니다. 현재 목표는 뉴스, 정부 공식 발표, 현지 독립 언론, Reddit 여론, 여론조사, 금융·무역 지표를 종합해 공급망 및 지정학 리스크의 조기경보를 제공하는 것이다.

핵심 산출물은 `output/dashboard/index.html` 대시보드다. Markdown, PDF, Word 보고서와 MySQL 뷰는 대시보드를 뒷받침하는 증거 자료로 본다.

## Important Direction Change

초기에는 "AI가 앞으로 어떤 국제정세 이슈가 발생할지 예측하는 시스템"을 목표로 했다. 그러나 미래 사건의 정답 정의, 장기 검증 필요성, 오탐·미탐 해석 문제 때문에 졸업작품 범위에서 방어하기 어렵다고 판단했다.

따라서 현재 방향은 다음과 같이 바뀌었다.

- 폐기한 목표: 미래 국제정세 사건을 맞히는 예측 시스템
- 현재 목표: 관측 가능한 데이터 신호를 기반으로 위험 증가를 탐지하는 조기경보 시스템
- 검증 질문: "사건을 맞혔는가"가 아니라 "위험 신호를 근거 기반으로 일관되게 포착했는가"

대외 문서에서는 이 전환을 기능 축소나 실패로 설명하지 않는다. 핵심 메시지는 “예측의 검증 한계를 발견했고, 이미 구축한 수집·분석 자산을 감사 가능한 조기경보 문제로 재설계했다”이다. 발표 구조와 질문 대응은 `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md`를 기준으로 한다.

예전 문서에 "예측", "챗봇 전환", "자동 게시" 같은 표현이 남아 있어도 현재 방향으로 해석하면 안 된다. 그런 문서는 이력 또는 보류 문서다.

## Recommended Reading Order

1. `README.md`
2. `PROJECT_CONTEXT.md`
3. `docs/current/PROJECT_PLAN.md`
4. `docs/current/VALIDATION_PLAN.md`
5. `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md` when explaining the project externally
6. `docs/current/DATA_COLLECTION_GUIDE.md`
7. `docs/current/LLM_SYSTEM_SUMMARY.md`
8. `docs/current/DATABASE_SETUP.md` when database context is needed
9. `docs/SESSION_PROMPTS.md` when starting role-specific AI sessions
10. `docs/REPOSITORY_STRUCTURE.md` when moving or classifying files
11. `project-handoff.md` only when detailed history or coordination context is needed
12. `docs/history/PROJECT_EVOLUTION_TIMELINE.md` when the pivot story is needed

## Current Planning Documents

- `docs/current/PROJECT_PLAN.md`: current early-warning project plan
- `docs/current/DATA_COLLECTION_GUIDE.md`: data collection strategy for warning signals
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

- News, RSS, and review logs become warning-signal inputs.
- Government announcements become official-position signals.
- Independent/local media and Reddit become non-official or public-sentiment signals.
- Financial and trade data become supply-chain proxy signals.
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

Avoid these terms unless discussing retired history.

- prediction accuracy
- future event prediction
- guaranteed forecast
- fully automated geopolitical prediction

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
