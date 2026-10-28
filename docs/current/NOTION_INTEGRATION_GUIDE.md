# Notion(노션) 연동 및 자동화 가이드

**문서 식별자:** `docs/current/NOTION_INTEGRATION_GUIDE.md`  
**기준 일자:** 2026-10-28  
**상태:** 구현 완료 (사용자 API 키 입력 대기 중)  

---

## 📌 1. 연동 기능 개요

본 프로젝트에는 사용자가 요청한 **모든 용도(3가지 축)**의 노션 연동 모듈이 구축되어 있습니다.

| 연동 영역 | 파일 / 모듈 | 주요 역할 및 특징 |
| :--- | :--- | :--- |
| **① 작업 보드 동기화** | `scripts/notion/sync_notion_board.py` | `AGENT_SYNC.md`의 Active Work Board를 Notion 칸반 데이터베이스로 양방향 동기화. **(DB가 없으면 노션 허브 하위에 자동 생성)** |
| **② 조기경보 보고서 발행** | `scripts/notion/publish_notion_report.py` | `reports/`의 최신 조기경보 브리프(마크다운)를 파싱하여 Notion 블록으로 변환, 허브 페이지 하위에 자동 업로드 |
| **③ Antigravity Notion MCP** | `~/.gemini/config/mcp_config.json` | AI 어시스턴트(Antigravity)가 대화창에서 노션 문서를 직접 읽고 쓸 수 있는 Model Context Protocol 서버 연동 |

---

## 🔑 2. 사용자가 키를 입력해야 하는 위치 (2곳)

사용자께서 발급받으신 Notion 내부 통합 시크릿 토큰(`secret_...` 또는 `ntn_...`)을 아래 두 곳에 붙여넣어 주세요.

### 1) `.env` 파일 (파이썬 자동화 스크립트용)
저장소 루트의 `.env` 파일을 열고 `NOTION_API_KEY` 값을 입력합니다:
```bash
# ==============================================================================
# Notion Integration Configuration
# ==============================================================================
NOTION_API_KEY=여기에_발급받으신_시크릿_토큰_입력
NOTION_HUB_PAGE_ID=3eede224b44181f0bd20ea55620bf5c4
NOTION_BOARD_DATABASE_ID=
NOTION_REPORT_PAGE_ID=
```
*(참고: `NOTION_BOARD_DATABASE_ID`는 비워두셔도 최초 실행 시 스크립트가 노션 허브 아래에 자동으로 DB를 생성하고 ID를 알아서 기록합니다!)*

### 2) `C:\Users\홍준기\.gemini\config\mcp_config.json` (Antigravity AI 세션용)
Antigravity가 노션 툴을 사용할 수 있도록 토큰을 입력합니다:
```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": [
        "-y",
        "notion-mcp-server"
      ],
      "env": {
        "NOTION_TOKEN": "여기에_발급받으신_시크릿_토큰_입력"
      }
    }
  }
}
```

> **⚠️ 필수 확인 (노션 페이지 권한 연결):**  
> 노션 허브 페이지(`https://app.notion.com/p/3eede224b44181f0bd20ea55620bf5c4?pvs=204`)에 접속하여 우측 상단 `···` ➔ `연결(Connect to)` ➔ 방금 만드신 통합을 반드시 추가해 주세요. (권한이 연결되어야 읽기/쓰기가 가능합니다)

---

## 🚀 3. 실행 명령어 모음 (CLI 사용법)

터미널에서 아래 명령어로 간편하게 실행할 수 있습니다.

### 1. 연결 및 권한 테스트
```powershell
python scripts/notion/notion_manager.py --check
```
*토큰 유효성, 봇 이름, 허브 페이지 접근 권한을 즉시 확인합니다.*

### 2. 작업 보드 동기화 (`AGENT_SYNC.md` ➔ Notion Board)
```powershell
python scripts/notion/notion_manager.py --sync-board
```
*`AGENT_SYNC.md`의 최신 표를 노션의 Task 보드로 전송합니다. (진행 상태: done, in-progress, review-needed 등 자동 매핑)*

### 3. 조기경보 보고서 노션에 자동 발행
```powershell
python scripts/notion/notion_manager.py --publish-report
```
*최신 리스크 브리프 마크다운을 노션 페이지로 예쁘게 서식화하여 업로드하고, 생성된 노션 웹페이지 URL을 터미널에 반환합니다.*

### 4. 전체 한 번에 실행 (보드 동기화 + 보고서 발행)
```powershell
python scripts/notion/notion_manager.py --all
```
