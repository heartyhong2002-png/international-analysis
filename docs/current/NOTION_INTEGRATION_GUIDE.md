# Notion(노션) 연동 및 자동화 가이드

**문서 식별자:** `docs/current/NOTION_INTEGRATION_GUIDE.md`  
**기준 일자:** 2026-10-28  
**상태:** 연동 및 실시간 동기화 완료 (Active Work Board · MD 문서 보관소 · 전체 작업 이력 · 조기경보 리포트 발행 확인)  

---

## 📌 1. 연동 기능 개요

본 프로젝트에는 노션 허브(`https://app.notion.com/p/3eede224b44181f0bd20ea55620bf5c4?pvs=204`)와 로컬 GitHub 저장소를 동기화하는 **4대 노션 자동화 모듈**이 구축되어 있습니다.

| 연동 영역 | 파일 / 모듈 | 주요 역할 및 특징 |
| :--- | :--- | :--- |
| **① 작업 보드 동기화** | `scripts/notion/sync_notion_board.py` | `AGENT_SYNC.md`의 Active Work Board를 Notion 칸반 데이터베이스(`📋 AI 세션 작업 동기화 보드`)로 동기화. **(DB가 없으면 노션 허브 하위에 자동 생성)** |
| **② 문서 보관소 & 작업 이력 동기화** | `scripts/notion/sync_notion_docs.py` | 노션의 `MD 문서 보관소`에 최신 마크다운 인벤토리를 보강하고, 허브 하위에 `📚 전체 프로젝트 작업 이력 및 아키텍처 현황` 종합 페이지를 자동 생성·업데이트 |
| **③ 조기경보 보고서 발행** | `scripts/notion/publish_notion_report.py` | `reports/`의 최신 조기경보 브리프(마크다운)를 파싱하여 Notion 블록으로 변환, `보고서` 페이지 하위에 업로드 (중복 페이지 자동 정리 포함) |
| **④ Antigravity Notion MCP** | `~/.gemini/config/mcp_config.json` | AI 어시스턴트(Antigravity)가 대화창에서 노션 문서를 직접 읽고 쓸 수 있는 Model Context Protocol 서버 연동 |

---

## 🔑 2. 환경변수 및 설정 파일 위치

발급받은 Notion 내부 통합 시크릿 토큰(`secret_...` 또는 `ntn_...`)과 페이지 ID는 아래 두 곳에 설정됩니다.

### 1) `.env` 파일 (파이썬 자동화 스크립트용, `.gitignore`로 원격 노출 차단)
저장소 루트의 `.env` 파일:
```bash
# ==============================================================================
# Notion Integration Configuration
# ==============================================================================
NOTION_API_KEY=여기에_발급받으신_시크릿_토큰_입력
NOTION_HUB_PAGE_ID=3eede224b44181f0bd20ea55620bf5c4
NOTION_BOARD_DATABASE_ID=407de224-b441-818c-b033-cb6cf4ad5352
NOTION_REPORT_PAGE_ID=407de224-b441-80b7-a2e0-e0a1f852d542
NOTION_HISTORY_PAGE_ID=
```
*(참고: `NOTION_BOARD_DATABASE_ID`와 `NOTION_HISTORY_PAGE_ID`는 비워두어도 스크립트 실행 시 자동으로 생성·탐색하여 `.env`에 기록합니다.)*

### 2) `C:\Users\홍준기\.gemini\config\mcp_config.json` (Antigravity AI 세션용)
```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": [
        "-y",
        "@notionhq/notion-mcp-server"
      ],
      "env": {
        "NOTION_TOKEN": "여기에_발급받으신_시크릿_토큰_입력"
      }
    }
  }
}
```

> **⚠️ 필수 확인 (노션 페이지 권한 연결):**  
> 노션 허브 페이지(`https://app.notion.com/p/3eede224b44181f0bd20ea55620bf5c4?pvs=204`) 우측 상단 `···` ➔ `연결(Connect to)` ➔ `international analysis` 통합이 연결되어 있어야 읽기/쓰기가 가능합니다.

---

## 🚀 3. 실행 명령어 모음 (CLI 사용법)

터미널에서 아래 명령어로 간편하게 실행할 수 있습니다.

### 1. 연결 및 권한 테스트
```powershell
python scripts/notion/notion_manager.py --check
```
*토큰 유효성, 봇 이름(`international analysis`), 허브 페이지 접근 권한을 즉시 확인합니다.*

### 2. 작업 보드 동기화 (`AGENT_SYNC.md` ➔ Notion Board)
```powershell
python scripts/notion/notion_manager.py --sync-board
```
*`AGENT_SYNC.md`의 최신 표를 노션의 Task 보드로 전송합니다. (진행 상태: `done`, `in-progress`, `review-needed` 등 자동 매핑)*

### 3. MD 문서 보관소 및 전체 프로젝트 작업 이력 동기화
```powershell
python scripts/notion/notion_manager.py --sync-docs
```
*로컬의 최신 Markdown 문서 인벤토리와 Phase 1~4 전체 프로젝트 작업 이력을 노션 페이지로 동기화합니다.*

### 4. 조기경보 보고서 노션에 자동 발행
```powershell
python scripts/notion/notion_manager.py --publish-report
```
*최신 리스크 브리프 마크다운을 노션 페이지로 서식화하여 업로드하고, 생성된 노션 웹페이지 URL을 반환합니다.*

### 5. 전체 한 번에 실행 (보드 + 문서/작업이력 + 보고서 발행)
```powershell
python scripts/notion/notion_manager.py --all
```
