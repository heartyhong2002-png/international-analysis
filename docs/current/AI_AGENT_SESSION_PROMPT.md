# AI Agent Operations & Infrastructure Session Prompt

이 문서는 **Hermes Agent, Discord 게이트웨이, MySQL MCP, 멀티 에이전트 오케스트레이션(Hermes ↔ Antigravity ↔ Cursor)** 등 **AI 에이전트 인프라 및 운영 업무**를 전담하는 새 세션을 시작할 때 첫 메시지로 사용하는 인수인계 프롬프트이다.

---

## 복사하여 새 세션 첫 메시지로 사용할 프롬프트

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, AGENTS.md, docs/current/AI_AGENT_SESSION_PROMPT.md를 읽어줘.

너는 [AI 에이전트 인프라 및 운영(Agent Operations)] 전담 세션이다.
본 프로젝트(international-analysis)의 조기경보 수집·분석 자산을 외부(아이패드 디스코드, 로컬 터미널, GUI 데스크톱)에서 제어하는 Hermes Agent 및 멀티 에이전트 협업 생태계의 설정, 유지보수, 모델 최적화를 전담한다.

[핵심 3대 원칙]
1. 비용 제로(Zero-Cost): 어떠한 경우에도 유료 과금이 발생하지 않는 무료 API 티어(Google Gemini, Groq) 및 로컬 Ollama만 사용한다.
2. 한국어 지원 및 도구 실행: 한국어 대화가 자연스럽고 MySQL MCP, 파일, 터미널 도구를 오류 없이 호출해야 한다.
3. 컨텍스트 및 토큰 한도 방어: 불필요한 내장 도구와 장황한 프롬프트 주입을 억제하여 TPM(Tokens Per Minute) 에러("This conversation has grown too large...")가 재발하지 않도록 유지한다.

[주요 담당 영역]
- Hermes Agent 설정: C:\Users\홍준기\AppData\Local\hermes\config.yaml, .env, SOUL.md
- 멀티 에이전트 프로토콜: AGENTS.md, .cursor/rules/
- Discord 모바일 게이트웨이 및 원격 제어 연동 상태 점검
- MySQL MCP (international_analysis DB) 연동 도구 상태 점검
- LLM 모델 라우팅 최적화 (Groq vs Gemini Flash vs Ollama)

현재 프로젝트의 에이전트 설정 상태와 모델별 제약사항을 점검하고, 내가 지시하는 에이전트 튜닝 및 운영 작업을 진행해줘.
```

---

## 1. 시스템 아키텍처 및 연결 현황

```mermaid
flowchart TD
    subgraph Mobile ["📱 Mobile & Edge Node"]
        IPad["iPad Air M2 13인치 (Discord 원격 관제)"]
        S20["Galaxy S20 Ultra (Termux 24/7 데이터 수집)"]
    end

    subgraph PC ["💻 Host PC (Windows 11)"]
        subgraph Hermes ["Hermes Agent Ecosystem"]
            H_GUI["Hermes Desktop GUI (Microsoft Store)"]
            H_GW["Hermes Gateway (Discord & Local WS)"]
            H_CFG["config.yaml & .env (C:\\Users\\홍준기\\AppData\\Local\\hermes)"]
        end

        subgraph IDE ["Multi-Agent IDE Layer"]
            AGY["Antigravity (Pair Programming / Architect)"]
            CUR["Cursor (IDE Specialist)"]
        end

        subgraph LocalData ["Local Workspace & DB"]
            WS["C:\\dev\\international-analysis (Desktop Junction)"]
            MySQL["MySQL 8.0 (localhost:3306, international_analysis)"]
            Ollama["Ollama (localhost:11434, qwen2.5/exaone3.5)"]
        end
    end

    IPad <-->|Discord Bot: 헤르메스#3484| H_GW
    S20 -->|Git Push data/| WS
    H_GW <--> H_GUI
    H_GW <-->|MySQL MCP (uvx)| MySQL
    H_GW <-->|CLI Execution| WS
    AGY <--> WS
    CUR <--> WS
```

### 1-1. 주요 경로 및 환경
- **작업 디렉토리**: `C:\dev\international-analysis` (바탕화면 Junction: `C:\Users\홍준기\Desktop\international-analysis`)
- **표준 파이썬**: `C:\dev\international-analysis\.venv\Scripts\python.exe` (Python 3.13)
- **Hermes 설정 홈**: `C:\Users\홍준기\AppData\Local\hermes`
  - 설정 파일: `config.yaml`
  - 환경 변수: `.env` (`DISCORD_BOT_TOKEN`, `GEMINI_API_KEY`, `GROQ_API_KEY`)
  - 시스템 페르소나: `SOUL.md`
  - 세션 데이터베이스: `state.db`
  - 로그: `logs\agent.log`, `logs\gateway.log`
- **로컬 MySQL DB**: `localhost:3306` (계정: `root`, DB: `international_analysis`, 테이블: 45개)

---

## 2. LLM 모델 제공자별 특성 및 무료 티어 제약

| 제공자 / 모델 | 무료 티어 한도 (TPM / RPM) | 컨텍스트 창 | 장점 및 주의사항 |
| :--- | :--- | :--- | :--- |
| **Google Gemini Flash** (`gemini-3-flash-preview`, `gemini-3.1-flash-lite`) | **1,000,000 TPM** / 15 RPM | **1,000,000 토큰** | **컨텍스트가 100만 토큰으로 사실상 무제한.** 멀티턴 대화나 긴 도구 결과에도 "대화 용량 초과" 에러가 절대 발생하지 않음. 한국어 유창. |
| **Groq Qwen** (`qwen/qwen3.8-27b`) | **7,000 ITPM** / 1,000 RPM | 131,072 토큰 | 속도는 0.5초로 극도로 빠르나, **분당 7,000 토큰 제한** 때문에 이전 대화가 2턴만 쌓여도 즉시 429 에러(대화 용량 초과) 발생. |
| **Groq Llama/GPT-OSS** (`openai/gpt-oss-120b`, `20b`) | **8,000 TPM** / 1,000 RPM | 131,072 토큰 | 120B 거대 파라미터로 추론 능력이 뛰어나나 분당 8,000 토큰 제한이 있어 연속 대화 시 쿨다운 필요. |
| **로컬 Ollama** (`qwen2.5:7b`, `exaone3.5:7.8b`) | **무제한 (오프라인)** | 8,192~32,768 토큰 | 외부 API 장애 시 완전 무과금 오프라인 백업. (thinking 파라미터 제외 필요) |

> [!IMPORTANT]
> **"This conversation has grown too large..." 에러 방지 규칙**
> 1. Hermes의 기본 설정은 43개 도구 + Computer Use 가이드로 인해 첫 턴만으로 **16,130 토큰**을 소모합니다.
> 2. Groq 무료 티어를 사용할 때는 반드시 `config.yaml`의 `disabled_toolsets`에서 불필요한 도구를 모두 비활성화하여 4,500 토큰 이하로 경량화해야 합니다.
> 3. 대용량 멀티턴 대화를 안정적으로 하려면 컨텍스트와 TPM이 100만 토큰에 달하는 **Google Gemini Flash** 모델을 적극 권장합니다.

---

## 3. 핵심 도구 및 명령어 레퍼런스

### 3-1. 수집 및 전처리 CLI
```bash
# 8대 수집기 전체 1회 일괄 실행 (S20 연동 수집기 포함)
C:\dev\international-analysis\.venv\Scripts\python.exe scripts/collection/run_phone_collector.py --once

# 반도체 시장·장비주·DRAM 현물가 수집
C:\dev\international-analysis\.venv\Scripts\python.exe scripts/collection/fetch_semiconductor_market.py

# 블루스카이 테크·규제 속보 수집
C:\dev\international-analysis\.venv\Scripts\python.exe scripts/collection/fetch_bluesky_public.py

# 조기경보 신호 4단계 다국어 전처리 및 클러스터링
C:\dev\international-analysis\.venv\Scripts\python.exe scripts/automation/preprocess_signals.py

# 노션 허브 전체 동기화 (작업보드, 문서보관소, 리포트)
C:\dev\international-analysis\.venv\Scripts\python.exe scripts/notion/notion_manager.py --all
```

### 3-2. MySQL MCP 도구 (Hermes 및 AI Agent 공통)
- `mcp__mysql__execute_sql`: MySQL 쿼리 직접 실행 (`SELECT * FROM alert_events LIMIT 5;` 등)
- `mcp__mysql__get_schema_info`: 테이블 및 컬럼 스키마 조회
- `mcp__mysql__get_table_sample`: 특정 테이블의 최근 샘플 레코드 조회

### 3-3. 게이트웨이 및 프로세스 관리 주의사항
- **Hermes Desktop GUI 앱**이 실행 중일 때는 GUI 내부에서 게이트웨이를 자체 구동하므로, 터미널에서 백그라운드 게이트웨이(`hermes gateway run`)를 중복 실행하면 `Gateway starting (deadline)` 포트 충돌이 발생합니다.
- 시작프로그램(`Startup\StartHermesGateway.lnk`)은 충돌 방지를 위해 제거되어 있습니다.

---

## 4. 세션 전환 시 점검 체크리스트
1. `C:\Users\홍준기\AppData\Local\hermes\config.yaml`의 문법 및 도구 설정 상태 확인
2. Discord 봇(`헤르메스#3484`) 연결 상태 (`logs\gateway.log` 확인)
3. MySQL 서버(`localhost:3306`) 가동 및 MCP 정상 응답 여부 확인
4. 작업 완료 후 `AGENT_SYNC.md`에 Handoff 기록 남기기
