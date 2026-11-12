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
