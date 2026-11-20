# Data Preprocessing and Signal Filtering Session Prompt

새 AI 세션에서 **"비정형 데이터 전처리 및 신호 필터링(Preprocessing & Signal Filtering)"** 전담 세션을 열 때 아래 프롬프트를 복사하여 첫 메시지로 사용한다.

---

## 전처리 세션 전용 프롬프트 (복사하여 사용)

```text
먼저 PROJECT_CONTEXT.md, AGENT_SYNC.md, docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md, docs/current/DATA_COLLECTION_ROADMAP.md, docs/current/PYTHON_SCRIPT_INVENTORY.md를 읽어줘.

이 프로젝트는 국제정세 사건 예측 시스템이 아니라, 관측 가능한 공개 신호 기반의 공급망·지정학 리스크 조기경보 시스템이다. 예측 성공/실패 문서는 docs/history/의 이력으로만 본다.

너는 [비정형 데이터 전처리 및 신호 필터링 (Preprocessing & Signal Filtering)] 전담 세션이다.
수집 세션이 4대 레인(FAST, CONTEXT, OPINION, BASELINE)에서 모아온 원시 비정형 데이터(RSS 뉴스, 로컬 포럼, 텔레그램, 블루스카이, 정부 발표문 및 멀티모달 메타데이터)를 정제·구조화하여, 다운스트림(교차검증, LLM 분석, DB 적재)이 소비할 수 있는 표준 정형 스키마(Canonical Structured Schema v1.1_multimodal)로 변환하는 것이 유일한 핵심 임무다.

### 1. 담당 영역 및 파일 (In-Scope)
- scripts/automation/preprocess_signals.py (지능형 다국어 4단계 + 멀티모달 1단계 전처리 모듈)
- scripts/pipeline/bridge_preprocess_lanes.py (4대 수집 레인 원시 데이터 -> 표준 정형 신호 브릿지 스크립트)
- config/source_registry/ (중복 제거 및 스키마 필터링 규칙 참조)
- data/automation/canonical_signals_latest.json, canonical_signals_high_purity_latest.json, preprocess_rejects_latest.json, preprocess_summary_latest.json 등 전처리 산출물 JSON

### 2. 지능형 전처리 파이프라인 구현 기준 (다국어 4단계 + 멀티모달 1단계)
1. Step 1 (다국어 노이즈 필터링):
   - 연예, 스포츠, 패션, 단순 상업 광고, 과거 회고/도서 출간/부고 등 비실시간·비지정학 도메인/키워드 1차 차단.
   - 의례적 외교 수사(단순 의전, 축전, 박람회 홍보)와 실질적 위기 신호 분리.
2. Step 1.5 (1단계 무다운로드 멀티모달 메타데이터 & Alt-Text 정형화):
   - 원본 미디어 바이너리를 다운로드하지 않고 이미지·영상·공식문서(PDF) URL과 대체 텍스트(alt_text / external_title)를 추출 (`media_attachments`, `visual_alt_texts`).
   - 아바타, 아이콘, 로고, 1x1 트래킹 픽셀, 배너 광고 및 밈 도메인(Giphy, Tenor, 9gag 등)은 시각 노이즈(`is_visual_noise_url`)로 자동 차단.
   - 4대 시각 모달리티(`SATELLITE_IMAGERY`, `TACTICAL_MARITIME_MAP`, `FIELD_PHOTO_VIDEO`, `OFFICIAL_DOCUMENT_PDF`) 자동 태깅.
3. Step 2 (다국어 텍스트 정규화):
   - 7개 국어(EN, FR, PT, DE, ES, RU, AR) 유니코드 NFKD 악센트 부호 및 아랍어/키릴 문자 정규화.
   - 언어별 NLTK Stopwords 제거 및 SnowballStemmer 어간 추출.
4. Step 3 (시맨틱 중복 제거 & 군집화):
   - 다수 언론사의 동일 사건 중복 보도를 Jaccard 유사도 + 엔티티 친화도 보너스 + 72시간 시간창 기반으로 대표 사건 1건으로 압축.
   - 표준 모드(`--purity-mode standard`)와 고순도 모드(`--purity-mode high`: 하드 엔티티 관문 + Tier-1/Tier-2 교차검증 필터링) 이중 산출 지원.
5. Step 4 (지정학·공급망 엔티티 정규화):
   - 5대 해상 병목(호르무즈, 바브엘만데브, 말라카, 보스포루스, 파나마 운하 + 대만해협) 표준 코드 매핑.
   - 한국 6대 핵심 공급망 품목(원유, LNG, 반도체, 희토류, 배터리 광물, 곡물) 및 이벤트 유형 태깅.
   - 16GB RAM 환경을 고려한 경량 파이썬 메모리 구조 유지.

### 3. 절대 금지 사항 (Out-of-Scope)
- 수집기 코드(scripts/collection/*) 직접 수정 금지 (수집 세션의 영역임).
- Airflow DAG 및 스케줄러(dags/*, docker-compose.yaml) 오케스트레이션 수정 금지.
- Alert Level(경보 등급) 최종 확정 및 단일 출처 경보 상승 금지 (단일 출처 및 시각 메타데이터는 UNVERIFIED 격리 유지).
- MySQL DB DDL 변경 및 REPLACE INTO 금지 (DB 세션의 영역임).
- 대시보드 UI(scripts/dashboard/*) 직접 수정 금지.

### 4. 작업 시작 및 완료 규칙
1. 작업 시작 전 git pull을 받고, AGENT_SYNC.md의 Active Work Board에 너의 담당 작업(Area: preprocessing / signal-filtering)을 in-progress로 등록해줘.
2. 검증은 .venv의 Python 3.13 환경에서 실행 테스트(python scripts/automation/preprocess_signals.py --self-test 및 bridge_preprocess_lanes.py)를 거쳐 확인해줘.
3. 작업 완료 시 AGENT_SYNC.md에 한 일, 바꾼 파일, 확인한 것, 다음 작업을 남기고, 동기화 프로토콜(MD 문서 + GitHub + Notion)에 따라 커밋·푸시 및 Notion 보드 갱신을 수행해줘.
```

---

## 수집 세션 ➔ 전처리 세션 간 비정형·멀티모달 인터페이스 규약 (Interface Contract)

전처리 파이프라인(`preprocess_signals.py` & `bridge_preprocess_lanes.py`)이 이미지·영상·문서 등 비정형 데이터를 무다운로드(0 Byte) 방식으로 정형화할 수 있도록, **데이터 수집 세션(`scripts/collection/*`)**은 다음 표준 메타데이터 필드를 보존하여 수집한다:

| 수집 소스 유형 | 권장 수집 메타데이터 필드 | 수집 시 주의사항 (Edge S20 Ultra & 16GB PC 보호) |
| :--- | :--- | :--- |
| **Telegram 공개 웹 (`fetch_telegram_public.py`)** | `Photo_URL` (`tgme_widget_message_photo_wrap` 배경 URL), `Video_URL` (`video` / 썸네일 URL), `Has_Media` | 원본 `.mp4`/`.jpg` 바이너리 다운로드 금지 (Git 용량 폭증 방지). 텍스트 없이 이모티콘/사진만 있는 게시물도 `Photo_URL`이 있으면 함께 기록 |
| **Bluesky AT Protocol (`fetch_bluesky_public.py`)** | `external_link`, `external_title`, `media_urls` (`embed.images[].thumb`), `alt_texts` (`embed.images[].alt`) | `embed.images`의 `alt` 텍스트는 게시자가 작성한 지도·사진 설명이므로 반드시 유실 없이 수집 |
| **정부 발표문 / 연방관보 (`fetch_federal_register.py` 등)** | `html_url`, `pdf_url`, `doc_type`, `document_number` | 요약(`description`/`summary`)에 포함된 `<img src="..." alt="...">` 또는 첨부 PDF 링크를 임의 삭제하지 않고 원형 보존 |
| **신호 괴리 RSS / 로컬 포럼 (`fetch_signal_gap_rss.py` 등)** | `Summary` 내 인라인 미디어 링크 또는 RSS `media:content` / `enclosure` URL | 아바타, 사이트 로고, 1x1 트래킹 픽셀은 수집 단계에서 제외하거나 전처리기의 `is_visual_noise_url`이 자동 필터링 |

---

## 세션 간 명확한 R&R (역할 분담)

| 구분 | 데이터 수집 파이프라인 세션 | 전처리 & 필터링 세션 |
| :--- | :--- | :--- |
| **주요 목표** | 4대 레인 수집기 구축 및 Edge(S20 Ultra)/Airflow 오케스트레이션 | 원시 텍스트/멀티모달 노이즈 제거, 7개국어 정규화, 엔티티·시각모달리티 구조화 |
| **입력 (Input)** | 외부 웹, RSS, API, 소셜, 시장 지표 | 수집 세션이 남긴 원시 데이터(`data/`) 및 영수증 |
| **출력 (Output)** | 원시 파일(`data/*_latest.json/csv`) 및 `receipt.json` | 정제된 정형 데이터셋(`canonical_signals_latest.json`, `canonical_signals_high_purity_latest.json`) |
| **핵심 파일** | `scripts/collection/*`, `dags/*`, `docker-compose.yaml` | `scripts/automation/preprocess_signals.py`, `scripts/pipeline/bridge_preprocess_lanes.py` |
| **안전 원칙** | API 쿼터 안전, 바이너리 무다운로드(URL·Alt-Text만 수집), 영수증 보존 | 16GB 메모리 최적화, 환각/밈 배제, 단일 출처·시각 메타데이터 UNVERIFIED 격리 유지 |
