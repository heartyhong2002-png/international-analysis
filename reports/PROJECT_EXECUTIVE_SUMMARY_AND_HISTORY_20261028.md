# 🚀 [종합 프로젝트 현황] 국제정세·공급망 조기경보 시스템 전체 작업 내역 및 진행 현황

**기준 일자:** 2026-10-28  
**프로젝트명:** 국제정세 및 공급망 리스크 조기경보 시스템 (OSINT Early Warning System)  
**작성자:** 홍준기 (한국공학대학교) & AI 페어 프로그래밍 어시스턴트 (ANTIGRAVITY / Codex / Cursor)  
**GitHub 저장소:** `https://github.com/heartyhong2002-png/international-analysis`  
**Notion 프로젝트 허브:** `https://app.notion.com/p/3eede224b44181f0bd20ea55620bf5c4`

---

## 📌 1. 프로젝트 개요 및 핵심 정체성 (Core Mission & Identity)

본 프로젝트는 특정 미래 사건을 단정적으로 예언하거나 추측하는 시스템이 아닙니다. **분산된 공개 데이터(뉴스, 공식 발표, 해협 물류, 금융 프록시, 현지 공개 의견, 검색량 등)에서 평소와 다른 이상 신호(Signal Gap)를 조기에 포착하고, 출처와 검증 상태를 함께 제공하는 증거 기반(Evidence-Based) 조기경보 프로토타입**입니다.

### 5대 핵심 감시축 (Core 5-Axis Monitoring)
특정 지역(예: 중동 분쟁) 리스크에 편중되지 않도록 다음 5개 축을 균형 있게 모니터링합니다:
1. **중국·대만 및 동아시아 (China/Taiwan Conflict & Taiwan Strait)**: 양안 해협 및 동아시아 안보 신호
2. **러시아·우크라이나 및 유럽 안보 (Russia/Ukraine War & European Security)**: 동유럽 전황 및 NATO 대치 신호
3. **미국 및 동맹국 관계 (US and Allies Relations)**: 미 행정부 대외 성명, 정상회담, 다자 안보 협력
4. **미·중 전략경쟁 및 수출통제 (US-China Strategic/Tech Competition)**: 반도체·희토류 무역, 통상 제재, 관세
5. **중동 에너지 및 해상 물류 (Middle East Energy/Shipping)**: 호르무즈·바브엘만데브 해협, 원유·운임 프록시

---

## 🛠️ 2. 지금까지 완료된 주요 작업 내역 (Work Accomplished)

### ① 데이터 수집 파이프라인 (Data Collection Lanes & Sensors)
- **4대 수집 레인 아키텍처 수립 (`docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md`)**:
  - `FAST` (GDELT, 정부발표, 텔레그램, 해협물류, 시장지표)
  - `CONTEXT` (현지 언론, 싱크탱크, 전문가 분석)
  - `OPINION` (대만 PTT, 중국 핀충, Bluesky, Reddit, Google Trends)
  - `BASELINE` (세관, 무역, 여론조사, 거시지표, IB)
- **해협·항만 물리적 길목 및 금융 프록시 센서 (`scripts/collection/fetch_maritime_chokepoints.py`)**:
  - 4대 병목(바브엘만데브, 호르무즈, 대만해협, 말라카)의 물리적 지연일수, 전쟁보험료 할증 모델링
  - 발틱 벌크선(BDRY), 정기선사(ZIM, Maersk), 유조선사(FRO), 브렌트유(BZ=F), 천연가스(NG=F) 실시간 수집 연동
- **대안 로컬 여론 5대 센서 & 구글 트렌드 (`fetch_local_opinions.py`, `fetch_google_trends.py`)**:
  - 레딧 API 제약 및 서구 편향을 탈피하여 대만 PTT, 중국 핀충(品葱), Bluesky, Google News, Telegram 공개 채널 수집
  - 설문조사 대신 실제 국민 체감 검색 급등률(Surge Radar) 포착
- **GDELT Cloud v2 쿼터 방어 및 사용량 제어 (`gdelt_cloud_budget.py`)**:
  - Academic & Research 월 5,000 QU 한도에 맞춘 일일 안전상한선 및 Bounded Throttling 도입
- **백악관 공식 브리핑·성명 수집기 (`fetch_whitehouse_official.py`)**:
  - 미 행정부 공식 입장과 대외 정책 신호를 정밀 수집하기 위한 2단계(RSS 우선 + 사이트맵) 수집기 구축
- **신규 보조 센서 확장 (`fetch_acled.py`, `fetch_event_registry.py`, `fetch_mediacloud.py`)**:
  - ACLED 분쟁·시위 사건 OAuth 연동 및 Event Registry API 키 연동 성공
  - Media Cloud의 최신 Search API(Bearer Token) 규격 반영
- **선언적 수집 소스 레지스트리 설계 (`config/source_registry/`)**:
  - 코드 하드코딩을 제거하고 YAML 설정 파일로 관리 가능한 소스 레지스트리 스키마 초안 구축

### ② 분석 및 다중 계통 교차검증 (Multi-Channel Cross-Verification Engine)
- **엄격한 가드레일 적용 (`scripts/analysis/cross_verify_events.py`)**:
  - 단일 GDELT 사건이나 미확인 SNS 글로 경보를 임의 격상하지 않는 안전 원칙(`single_source_elevate_forbidden = True`) 강제
  - 지리·토픽 및 시계열(±72h) 일치 시에만 신호를 결합하여 False Corroboration 원천 차단
  - 검증 상태를 `CROSS_VERIFIED`, `PARTIALLY_CONFIRMED`, `UNVERIFIED`로 명확히 분화

### ③ 데이터베이스 및 증거 계층 (Database & Evidence Storage Layer)
- **MySQL 관계형 모델링 및 분석용 뷰 4종 구축 (`scripts/db/create_views.sql`)**:
  - `v_cross_verified_events_summary`: 복수 계통 교차검증된 공급망 사건 랭킹 및 집계 뷰
  - `v_chokepoint_supply_chain_radar`: 4대 해협의 전쟁보험료와 시장 프록시 결합 뷰
  - `v_dashboard_current_alerts`, `v_dashboard_sensor_health`
- **증거 계층 트랜잭션 적재 (`scripts/db/evidence_writer.py`)**:
  - 리스크 점수, 신호 괴리율, 경보 레벨, 원문 근거, 검증 감사 로그를 단일 트랜잭션으로 원자적(Atomic) 적재
  - Append-only 무결성 유지, 중복 거부 및 실패 롤백 보장, 테스트 픽스처 격리(`manage_test_fixtures.py`)

### ④ 대시보드 및 보고서 (Dashboard & Reporting)
- **인터랙티브 HTML 대시보드 (`scripts/dashboard/generate_dashboard_v2.py`)**:
  - 5대 감시축 균형 UI 및 MySQL DB 뷰 우선 연동 (파일 무중단 폴백 지원)
  - 다중 계통 교차검증 레이더 위젯 신설
  - Information 축 과장 표현 교정 (국민 여론 단정 제거, 하드코딩 Critical 배지 제거)
- **보고서 자동화 (`scripts/reports/`)**:
  - 일일 조기경보 리포트 Markdown, Word(DOCX), PDF 자동 생성 파이프라인 완비

### ⑤ 강송희 교수님 연구 프로젝트 전용 작업 공간 구축 (`prof_kang_project/`)
- 한국공학대학교 경영학부 강송희 교수님과의 연구 협업 전용 공간 분리
- 주간 진행현황 보고서, 학술 논문 초안, 발표 슬라이드, 피드백 Action Items 표준 템플릿 완비 (`SESSION_GUIDELINES.md`)

### ⑥ Notion 연동 모듈 및 실시간 동기화 (`scripts/notion/`)
- 외부 라이브러리 의존성 없는 경량 Notion API 클라이언트(`notion_client_base.py`) 구축
- `AGENT_SYNC.md`의 Active Work Board(17개 태스크)를 Notion 데이터베이스(`📋 AI 세션 작업 동기화 보드`)로 실시간 양방향 동기화(`sync_notion_board.py`)
- 마크다운 조기경보 리포트 및 프로젝트 전체 현황을 노션 블록으로 변환하여 노션 허브에 자동 퍼블리싱(`publish_notion_report.py`, `notion_manager.py`)

---

## 📊 3. Active Work Board 현재 상태 요약 (17개 작업)

| 상태 | 건수 | 주요 영역 |
| :--- | :---: | :--- |
| **done (완료)** | **14건** | 해협 센서, 복수계통 교차검증, 대안 여론, 문서 정리, 백악관 수집기, GDELT 쿼터, DB 증거 트랜잭션, Media Cloud, Source Registry, 대시보드 표현 교정, Notion 연동 등 |
| **in-progress (진행 중)** | **3건** | Streamlit 대시보드 고도화, LLM 분석/검수 체계 연동, 전체 작업내역 MD/노션 실시간 동기화 |

*(모든 세부 작업 항목은 노션 허브의 '📋 AI 세션 작업 동기화 보드' 데이터베이스에서 실시간으로 확인할 수 있습니다.)*

---

## 🎯 4. 향후 계획 및 다음 마일스톤 (Next Steps)

1. **소스 레지스트리(YAML) 기반 `fetch_expert_sources.py` 구현**:
   - 싱크탱크 및 현지 언론 목록을 YAML 레지스트리 기반으로 일원화
2. **후보 수집기(candidate) 안정화 및 정량 평가**:
   - 수집 성공률, 결측률, 지연시간 지표화
3. **강송희 교수님 연구 프로젝트 후속 작업**:
   - 비정형 데이터 파이프라인 및 아키텍처 중심의 학술 논문 연구방법론 구체화 및 진행현황 보고서 작성
4. **정기 파이프라인과 Notion 일일 자동 퍼블리싱 연계**:
   - `run_pipeline.py` 완주 시 최신 조기경보 브리프를 노션 보고서 페이지로 자동 갱신
