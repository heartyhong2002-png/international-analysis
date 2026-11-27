# AGENTS.md - Multi-Agent Operating Protocol (Hermes / Antigravity / Cursor)

## 1. Paths & Environment
- **Workspace**: `C:\dev\international-analysis` (Desktop Junction: `C:\Users\홍준기\Desktop\international-analysis`)
- **Python**: `C:\dev\international-analysis\.venv\Scripts\python.exe`
- **State Docs**: `PROJECT_CONTEXT.md`, `AGENT_SYNC.md`

## 2. Key CLI Commands
- 전체 수집기 1회 실행: `c:\dev\international-analysis\.venv\Scripts\python.exe scripts/collection/run_phone_collector.py --once`
- 반도체 시장/장비주/DRAM: `c:\dev\international-analysis\.venv\Scripts\python.exe scripts/collection/fetch_semiconductor_market.py`
- 블루스카이 테크/규제 속보: `c:\dev\international-analysis\.venv\Scripts\python.exe scripts/collection/fetch_bluesky_public.py`
- 조기경보 신호 전처리: `c:\dev\international-analysis\.venv\Scripts\python.exe scripts/automation/preprocess_signals.py`
- 노션 전체 동기화: `c:\dev\international-analysis\.venv\Scripts\python.exe scripts/notion/notion_manager.py --all`

## 3. MySQL MCP (`international_analysis` DB)
- **Tools**: `mcp_mysql_execute_sql`, `mcp_mysql_get_schema_info`, `mcp_mysql_get_table_sample`
- **Key Tables**: `alert_events`, `rss_signal_gap`, `maritime_chokepoint_signals`, `cross_verified_events`, `financial_proxy`

## 4. Antigravity ↔ Qwen Code 병행 연동 규칙 (충돌 방지)
1. **Worktree / 브랜치 격리**:
   - Qwen Code는 `.qwen/worktrees/*` (`qwen/*` 브랜치)에서 작업하고, Antigravity는 메인 워킹트리(`cursor/actions-light-collection` 또는 전용 `antigravity/*` 브랜치)에서 작업한다. (`.qwen/`은 `.gitignore`로 커밋 제외)
2. **파일 소유권 분리 (동시 수정 금지)**:
   - 작업 시작 전 `git status -sb`와 `AGENT_SYNC.md` 상단을 확인해 상대가 수정 중인 파일을 동시에 건드리지 않는다.
   - `AGENT_SYNC.md` 보드 갱신과 최종 `origin/cursor/actions-light-collection` 푸시는 통합 시점에 한 번에 반영한다.
3. **작업 연동 절차**:
   - Qwen Code 작업 완료 후 전용 브랜치(`qwen/*`)에 커밋 → 메인 브랜치에서 `git merge --no-ff qwen/<branch>` (또는 `cherry-pick`)로 병합 → `py_compile` 검증 후 `origin` 푸시.
