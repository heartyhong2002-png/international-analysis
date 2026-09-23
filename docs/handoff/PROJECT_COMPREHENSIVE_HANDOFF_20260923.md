# 🌐 국제정세 분석 자동화 시스템 — 전 과정 종합 인수인계 보고서 (Full Project Handoff)

**문서 식별자:** `PROJECT_COMPREHENSIVE_HANDOFF_20260923.md`  
**작성 일시:** 2026-09-23 23:29:05 KST  
**개발자:** 홍준기 (한국공학대학교 데이터사이언스경영 전공)  
**수신:** 다음 작업을 이어받을 AI 세션 (Claude / Antigravity)  
**저장소 위치:** `C:\Users\홍준기\Desktop\international-analysis`  
**현재 Git HEAD:** `e86edd5` (clean)

---

## 📌 1. 프로젝트 개요 및 핵심 정체성 (Executive Summary)

### 1.1 프로젝트 정의 및 목적
- **과제 성격:** 학부 교과목/졸업 과제물 및 데이터사이언스·경영 융합 포트폴리오.
- **핵심 스토리:** 
  > **"제한된 로컬 하드웨어(16GB RAM, No GPU) 환경에서 다국어 오픈소스 로컬 LLM을 활용해 관측 가능한 국제정세 신호와 공급망 리스크를 탐지하는 조기경보 시스템(Early-Warning System) 구축"**
- **문제 해결 스토리의 핵심:**
  1. **학술적 한계의 인식과 현명한 피벗:** 미래 사건 단정적 예측(Prediction)의 비과학성을 인정하고, 검증 가능한 **조기경보 및 신호 괴리율(Signal Gap)** 체계로 전환.
  2. **하드웨어 제약의 엔지니어링 극복:** 외산 GPU 클라우드 비용 없이, 순수 로컬 Ollama 메모리 스왑을 통해 6대 권역별 네이티브 파운데이션 모델(총 31.8GB)을 16GB RAM에서 100% 무결 구동.
  3. **데이터 편향 극복:** 소셜미디어(Reddit) 단독 노이즈를 배제하고, 공식 정부 발표 ↔ 해외 망명 독립 언론 ↔ 실증 여론조사 ↔ 금융 대체 지표 ↔ 텔레그램 OSINT의 5계층 복합 센서망 구축.

### 1.2 핵심 개발 환경
```yaml
Hardware: Samsung Galaxy Book5 Pro 16"
CPU: Intel Core Ultra 5
RAM: 16GB LPDDR5
GPU: None (Intel Arc 내장 그래픽 전용)
OS: Windows 11 Home (PowerShell 환경)
Local Database: MySQL 8.0+ (Database name: international_analysis)
LLM Engine: Ollama v0.34.0+ (Local API: http://localhost:11434)
Available Storage: C Drive ~81.8GB Free
```

### 1.3 최종 핵심 산출물 (Single Source of Truth)
- **최종 평가 대상:** **`output/dashboard/index.html`** (단일 인터랙티브 HTML 조기경보 대시보드)
- **증거 자료 (Supporting Evidence Assets):**
  - 미국 GAO/FBI 스타일 2페이지 공문서 PDF (`scripts/pdf_report_generator.py`)
  - MS Word (.docx) 정세평가 보고서 (`scripts/docx_report_generator.py`)
  - 일일 정세 분석 Markdown (`reports/issues/`)
  - MySQL 분석 뷰 4종 (`scripts/create_views.sql`)
  - 3대 모델 합의 검증 보고서 및 NIST AI RMF 매핑 문서

---

## 📜 2. 프로젝트 전략 변천사 (Evolution & Strategic Pivots)

본 프로젝트는 총 5단계를 거치며 현실적이고 학술적으로 방어 가능한 형태로 진화했습니다 (`docs/history/PROJECT_EVOLUTION_TIMELINE.md` 참고).

```mermaid
flowchart LR
    P1["1단계: 미래 사건 예측<br/>(Prediction)"] -->|검증 불가 폐기| P2["2단계: 대시보드 중심<br/>분석 시스템"]
    P2 -->|데이터 엔지니어링 집중| P3["3단계: 챗봇 서비스 검토<br/>(Parked in Archive)"]
    P3 -->|교수님 피드백 반영| P4["4단계: 공급망 조기경보 &<br/>신호 괴리율(Signal Gap)"]
    P4 -->|체계적 문서 분리| P5["5단계: 5계층 복합 센서 &<br/>NIST AI RMF 체계"]
```

1. **1단계 (미래 정세 예측 구상 → 폐기, `docs/history/PREDICTION_APPROACH_RETIRED.md`):**
   - AI로 미래 국제 분쟁 발생 여부를 맞히는 시스템을 기획했으나, 미래 사건은 정답(Ground Truth) 정의가 모호하고, 장기 검증이 필요하며, 외생 변수가 무한하여 **졸업 심사에서 학술적으로 방어 불가능**함을 확인하고 공식 폐기.
2. **2단계 (대시보드 중심 정리):**
   - "미래를 맞히는 AI"에서 "수집된 신호와 LLM 판단을 투명한 근거와 함께 제공하는 정보시스템"으로 재정의. 모든 리포트를 대시보드의 증거 자료로 위상 정리.
3. **3단계 (챗봇 서비스 피벗 검토 및 보류, `docs/history/CHATBOT_PIVOT_RETIRED.md`):**
   - FastAPI 기반 대화형 챗봇을 시험했으나, 데이터 파이프라인 및 신뢰성 검증이라는 본질을 흐릴 우려가 있어 코드를 `docs/archive/parked_chatbot_pivot/`로 안전하게 격리 보존(Hold).
4. **4단계 (공급망 리스크 조기경보 & 신호 괴리율 피벗):**
   - **교수님 피드백 반영:** 단정적 예측 대신 **"관측 가능한 데이터 신호의 이상 징후 조기경보"**로 전환.
   - **신호 괴리율 (Signal Gap Discrepancy Rate):** 권위주의 통제 국가의 [정부 선전/관영 매체] ↔ [해외 망명 독립 언론 / 검열 삭제 아카이브] 간의 논조 괴리를 0~100점으로 정량화.
5. **5단계 (문서 체계 분할 및 최신화 완료):**
   - `docs/current/`: 현재 활성 계획 (`PROJECT_PLAN.md`, `DATA_COLLECTION_GUIDE.md`, `VALIDATION_PLAN.md`)
   - `docs/history/`: 피벗 이력 보존 (`PROJECT_EVOLUTION_TIMELINE.md`, `PREDICTION_APPROACH_RETIRED.md`, `CHATBOT_PIVOT_RETIRED.md`)
   - `docs/archive/`: 이전 인수인계서 및 구형 결과물 보관
   - `docs/evidence/`: 레딧 IR 피어 리뷰 등 외부 실증 증빙 자료
   - `PROJECT_CONTEXT.md`: 신규 AI 세션을 위한 핵심 가이드라인

---

## 🤖 3. 로컬 6대 네이티브 LLM 아키텍처 (`docs/current/LLM_SYSTEM_SUMMARY.md`)

C드라이브 81.8GB 공간 확보 후, 권역별 최고 성능을 자랑하는 6대 네이티브 파운데이션 모델을 1:1 전담 배치하였습니다.

| 권역 / 언어 | 모델명 (Ollama) | 용량 | 역할 및 기술적 의의 |
| :--- | :--- | :--- | :--- |
| 🇰🇷 **한국** | `exaone3.5:7.8b` | 4.8GB | LG AI Research 개발. 한국어 정세 평가 및 최종 공문서/리포트 총괄 작성 |
| 🇺🇸🇪🇺 **영미·유럽** | `mistral-nemo:latest` | 7.1GB | Mistral AI-NVIDIA 12B 모델. 영미권 뉴스 분석 및 서·남·동·북유럽 11개 언어 통합 전담 |
| 🇨🇳 **중국** | `qwen2.5:7b` | 4.7GB | 알리바바 개발. 중국 관영 매체 프레이밍 분석 및 3자 합의 검증 |
| 🇷🇺 **러시아** | `second_constantine/yandex-gpt-5-lite:8b` | 5.7GB | 러시아 빅테크 얀덱스(Yandex) 자체 8B 모델. 러시아 국내 언론 및 안보 담론 해석 |
| 🇦🇪 **중동·아랍** | `falcon3:7b` | 4.6GB | UAE 아부다비 국영 TII 개발. 순수 아랍어 파운데이션 모델, 중동 정세 및 원문 해독 |
| 🇯🇵 **일본** | `dsasai/llama3-elyza-jp-8b` | 4.9GB | 도쿄대 마츠오 랩 ELYZA 모델. 일본 주류 언론 뉘앙스 정밀 분석 |

### 주요 LLM 안전 및 검증 장치
1. **환각 0% 하드 제약 프롬프트 (`scripts/analyze_signals.py`):**
   - 정부 발표 데이터가 없을 경우 추측하지 않고 반드시 `"수집된 정부 발표 없음 — 판단 불가"`로 출력하도록 강제.
2. **3대 모델 다자간 교차 합의 (Consensus Engine, `scripts/verify_model_consensus.py`):**
   - 서방(`mistral-nemo`), 아시아(`qwen2.5`), 한국(`exaone3.5`) 3대 모델이 동일 기사를 교차 분석하여 2:1 이상의 다수결 합의만 팩트로 채택.
3. **NIST AI RMF 1.0 체계 공식 매핑:**
   - Govern, Map, Measure, Manage 4대 기능에 기반한 'LLM-as-a-judge' 무개입 평가 체계 확립.

---

## 📡 4. 5계층 데이터 수집 및 분석 센서망 현황

| 계층 (Tier) | 데이터 소스 | 수집 스크립트 | 산출 파일 | 현재 상태 |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: 공식 정부 발표** | 한국 외교부, 미 국무부, 영국 FCDO, 독일 외교부, IRNA, 신화통신 등 | `scripts/gov_announcements_collector.py` | MySQL `gov_announcements` | 정상 가동 (21개 이슈 매칭) |
| **Tier 2: 신호 괴리율 (Signal Gap)** | 타스 vs 메두사, 인민일보 vs CDT, 테헤란타임스 vs 라시프22, 알자지라 | `scripts/fetch_signal_gap_rss.py`<br>`scripts/analyze_signal_gap.py` | `data/signal_gap/rss_signal_gap_latest.csv`<br>`data/signal_gap/signal_gap_analysis.json` | 러시아(85점), 중동(85점) 점수 도출 완료 |
| **Tier 3: 실증 여론 & 싱크탱크** | Pew Research, ECFR, Ipsos Global, Chatham House, Crisis Group | `scripts/fetch_polling_data.py`<br>`scripts/prototype_local_expert_sources.py` | `data/polls/polls_latest.csv`<br>`data/polls/polls_summary.json` | 12건 정규 수집 및 JSON 적재 완료 |
| **Tier 4: 금융 & 무역 대체 지표** | 중국 CSI300 ETF(ASHR), 위안화 환율(USD/CNY), 국제 금(Gold), UN Comtrade | `scripts/fetch_financial_proxy.py`<br>`scripts/fetch_us_macro_signals.py` | `data/signal_gap/financial_proxy_latest.csv` | 자본이탈 및 환율 변동 모니터링 가동 완료 |
| **Tier 5: 긴급 텔레그램 OSINT** | Rybar (러시아군), UaOnlii (우크라이나), sepah_pasdaran (IRGC), army21ye (후티) | `scripts/fetch_telegram_public.py`<br>`scripts/analyze_middle_east_osint.py` | `data/signal_gap/telegram_osint_latest.csv`<br>`data/signal_gap/middle_east_risk_analysis.txt` | 후티 반군 아람코 타격 성명 실시간 포착 실증 |

---

## 🗄️ 5. 저장소 디렉터리 구조 및 파일 맵

```text
international-analysis/
├── README.md                                  # 프로젝트 공식 진입점 (1페이지 요약)
├── PROJECT_CONTEXT.md                         # 새 AI 세션용 핵심 가이드라인
├── project-handoff.md                         # 세션 간 조율 및 상세 작업 로그
├── prototype_all_in_one.py                    # 6대 모델 언어 라우팅 및 톤 분류 핵심 엔진
├── docs/
│   ├── current/                               # [현재 활성] 조기경보 시스템 기준 계획
│   │   ├── PROJECT_PLAN.md                    # 조기경보 프로젝트 기획서
│   │   ├── DATA_COLLECTION_GUIDE.md           # 5계층 데이터 수집 기준
│   │   ├── VALIDATION_PLAN.md                 # 조기경보 품질 검증 계획서
│   │   ├── LLM_SYSTEM_SUMMARY.md              # LLM 아키텍처 상세 기술 문서
│   │   ├── DATABASE_SETUP.md                  # MySQL 증거 계층 및 조기경보 뷰
│   │   └── PRESENTATION_PORTFOLIO_NARRATIVE.md# [필독] 30초 피칭, 문제정의, 심사 Q&A 방어 논리
│   ├── handoff/                               # 트랙별 세션 인수인계 문서
│   │   ├── PROJECT_COMPREHENSIVE_HANDOFF_20260923.md
│   │   ├── DB_TRACK_HANDOFF_20260923.md
│   │   └── LLM_AND_DASHBOARD_TRACK_HANDOFF.md
│   ├── history/                               # [이력 보존] 기획 피벗 변천사
│   │   ├── PROJECT_EVOLUTION_TIMELINE.md      # 5단계 변천 타임라인
│   │   ├── PREDICTION_APPROACH_RETIRED.md     # 예측 접근 폐기 사유
│   │   └── CHATBOT_PIVOT_RETIRED.md           # 챗봇 피벗 보류 사유
│   ├── archive/                               # 이전 완료 인수인계서 및 레거시 산출물
│   │   ├── pre_pivot_validation_outputs/      # 피벗 전 구형 검증 리포트 보관함
│   │   └── parked_chatbot_pivot/              # 보류된 FastAPI 챗봇 소스 일체
│   └── evidence/                              # 학술적 피어 리뷰 등 외부 실증 증빙
│       └── reddit_feedback_20260923/          # r/IRstudies 전문가 피드백 데이터
├── reports/
│   └── EARLY_WARNING_DELIVERABLES.md          # 조기경보 대시보드·제출 산출물 화면/필드 계약 명세
├── scripts/                                   # 데이터 수집, 분석, 리포트 생성 스크립트
│   ├── run_pipeline.py                        # 전체 수집+적재+대시보드 통합 오케스트레이터
│   ├── generate_dashboard_v2.py               # [핵심] 조기경보 대시보드 생성기
│   ├── fetch_signal_gap_rss.py                # 신호 괴리율 RSS 수집기
│   ├── analyze_signal_gap.py                  # 신호 괴리율 6대 LLM 분석 엔진
│   ├── fetch_financial_proxy.py               # 검열 우회 금융 대체 지표 수집기
│   ├── fetch_polling_data.py                  # 글로벌 공신력 3대 여론조사 수집기
│   ├── fetch_telegram_public.py               # 텔레그램 공개 OSINT 크롤러
│   ├── build_database.py                      # MySQL 스키마 생성 및 통합 적재 (트랙① 전담)
│   ├── pdf_report_generator.py                # 미국 GAO/FBI 스타일 2페이지 공문서 PDF 생성기
│   ├── docx_report_generator.py               # MS Word (.docx) 정세평가 보고서 생성기
│   └── archive/legacy_utilities/              # 사용 중단된 구형 유틸리티 스크립트
├── data/                                      # 파이프라인이 사용하는 실 데이터 저장소
│   ├── signal_gap/                            # 신호 괴리율, 금융 프록시, 텔레그램 데이터
│   ├── polls/                                 # 글로벌 실증 여론조사 CSV/JSON
│   └── issues/                                # 21개 이슈별 원본 데이터
├── output/
│   └── dashboard/
│       └── index.html                         # [최종 산출물] 단일 HTML 대시보드
└── .gitignore                                 # .venv, scripts/data/ 등 관리
```

---

## 🎯 6. 다음 세션(새 AI 세션)이 즉시 수행해야 할 작업 (Action Items)

현재 **기획 문서(`docs/current/`)와 수집 모듈은 완성**되었으나, **최종 산출물인 대시보드와 검증 스크립트 구현이 대기 중**입니다. 다음 세션은 아래 4개 작업을 순서대로 진행하면 됩니다:

### [Action 1] 조기경보 대시보드 v2.5 전면 개편 (`scripts/generate_dashboard_v2.py`)
- **목표:** 9월 17일 구형 상태에 머물러 있는 대시보드를 최신 조기경보 아키텍처로 갱신하여 `output/dashboard/index.html`을 생성.
- **반영 필수 요소:**
  1. **4단계 조기경보 배지 (4-Tier Alert Badges):** 21개 이슈별 Risk Signal Score 기반 `Normal` (<40), `Watch` (40~65), `Warning` (65~80), `Critical` (>80) 배지 및 탭 필터링.
  2. **신호 괴리율 레이더 (Signal Gap Radar):** `data/signal_gap/signal_gap_analysis.json`의 러시아(85점), 중동(85점) 등 관영 vs 망명 언론 괴리율 시각화 및 LLM 차이점 요약 표시.
  3. **금융 대체 지표 모니터 (Market Proxies):** `data/signal_gap/financial_proxy_latest.csv`의 중국 ETF(ASHR), 위안화 환율, 금 시세 변동률 및 자본이탈 리스크 카드.
  4. **텔레그램 긴급 OSINT 피드:** `data/signal_gap/telegram_osint_latest.csv`의 현장 속보 탭.
  5. **근거 투명성 박스 (Evidence Coverage Inspector):** "경보가 상향된 이유"를 증빙하는 원문 인용 및 출처 링크 즉시 확인.

### [Action 2] 조기경보 정량 백테스트 검증 모듈 구축 (`scripts/backtest_early_warning.py`)
- **목표:** `docs/current/VALIDATION_PLAN.md`에 정의된 6대 핵심 검증 지표를 자동 산출하는 스크립트 신설.
- **검증 대상 시뮬레이션 케이스:**
  - 2022 우크라이나 침공 직전 신호 괴리
  - 2024 대만 해협 포위 훈련
  - 2024 홍해 후티 반군 물류 타격
  - 미중 상호 관세 인상 긴장
- **산출 지표:** `Alert Precision`, `Missed Signal Count`, `Evidence Coverage`, `Human Agreement Rate`.
- **결과물:** `docs/evidence/early_warning_backtest_report.md` 자동 생성 (교수님 제출용 벤치마크 증빙).

### [Action 3] 통합 파이프라인(`scripts/run_pipeline.py`) 연결
- `fetch_signal_gap_rss.py`와 `fetch_financial_proxy.py`를 파이프라인 실행 체인에 정식 등록.
- `python scripts/run_pipeline.py` 실행 시 수집 → DB 적재 → 최신 대시보드 갱신까지 원클릭으로 완결되도록 연결.

### [Action 4] Git 동기화 및 Vercel / GitHub Pages 배포 준비
- 수정된 대시보드와 백테스트 스크립트를 Git 커밋하고, 최종적으로 `output/dashboard/index.html`을 웹에 배포하여 모바일/태블릿에서도 시연 가능하도록 준비.

---

## 💡 7. 새 세션 시작 시 프롬프트 가이드

새로운 세션을 열고 아래와 같이 입력하시면 새 세션이 혼선 없이 즉시 본 문서를 읽고 작업을 이어갈 수 있습니다:

> **새 세션 입력 프롬프트:**
> ```text
> 루트에 있는 PROJECT_COMPREHENSIVE_HANDOFF_20260923.md 와 docs/current/ 문서를 확인했어.
> 우리는 'AI 기반 공급망 리스크 조기경보 시스템'을 구축 중이고, 최종 산출물은 output/dashboard/index.html 이야.
> 
> [Action 1] scripts/generate_dashboard_v2.py 를 개편해서 4단계 경보 배지, 신호 괴리율 레이더(85점 등), 금융 대체 지표(ASHR/위안화), 텔레그램 OSINT, 근거 추적 박스를 대시보드에 완벽하게 시각화하고 최신 index.html 을 생성해줘.
> 확인 요청 없이 자동으로 즉시 실행해줘.
> ```

---
*본 종합 인수인계 보고서는 개발자 홍준기 님의 성공적인 졸업 심사 및 포트폴리오 완성을 지원하기 위해 최신 저장소 상태를 완벽하게 반영하여 작성되었습니다.*
