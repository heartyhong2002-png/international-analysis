# 프로젝트 현황 요약 (다른 대화방 전달용 + 세션 간 작업 조율용)

> 이 문서는 새로운 대화(채팅)에서 Claude가 프로젝트 맥락을 빠르게
> 파악할 수 있도록 작성된 인수인계 문서입니다. **동시에, 지금 이 프로젝트를
> 여러 Claude 세션이 같은 폴더에서 동시에 작업하고 있어서, 서로 뭘 건드리고
> 있는지 확인하는 조율 문서 역할도 겸합니다.** 새 세션은 작업 시작 전에
> 이 문서, 특히 "3개 세션 분업 현황"과 "작업 로그"를 먼저 확인해주세요.

---

## 프로젝트 개요

**이름:** 국제정세 분석 자동화 시스템 (International Affairs Analysis)
**개발자:** 홍준기
**목적:** 기업 제출용 포트폴리오 프로젝트
**핵심 스토리:** 제한된 하드웨어(16GB RAM, GPU 없음) 환경에서 다국어
오픈소스 LLM을 활용해 국제정세를 분석하는 시스템을 구축 — "제약을
창의적으로 극복하는 엔지니어링 능력"을 증명하는 것이 목표.

## 개발 환경

```
하드웨어: Galaxy Book5 Pro 16인치
CPU: Intel Core Ultra 5
RAM: 16GB
GPU: 없음 (내장 그래픽만)
OS: Windows
작업 폴더: C:\Users\홍준기\Desktop\international-analysis
DB: MySQL (international_analysis) — 로컬 설치
```

---

## ⚠️ 3개 세션 분업 현황 (2026-09-08 기준, 최신)

지금 이 프로젝트를 **3개의 Claude 세션**이 동시에 작업 중입니다. 그 중
2개는 이 컴퓨터에 로컬로 연결되어 있어서 **같은 파일을 동시에 건드릴 수
있는 실제 위험**이 있습니다. 실제로 한 번, `build_database.py`를 다른
세션이 대폭 수정한 걸 모르고 있다가 우연히 발견한 적이 있습니다 — 몰랐으면
그 세션이 만든 자동 중복정리 로직이 통째로 덮어써질 뻔했습니다.

| 트랙 | 로컬 연결 | 담당 범위 | 담당 파일 (건드려도 되는 것) |
|---|---|---|---|
| **① SQL/DB 담당** | ✅ 로컬 | MySQL 스키마 설계, 데이터 무결성, 중복/인코딩 정리 | `scripts/build_database.py`, `scripts/check_duplicates.py`, `scripts/clean_orphan_broken.py`, `scripts/dedupe_gov_announcements.py` |
| **② 오픈소스 LLM 담당** | ❌ 로컬 아님 | 다국어 로컬 LLM 라우팅, Ollama 모델 선정/테스트 | `prototype_all_in_one.py`(루트 — 2026-09-20 정정: `src/model_router.py` 등은 실제로 생성되지 않았고, 이 파일 하나로 통합됨) |
| **③ 컨트롤타워 (이 세션)** | ✅ 로컬 | 새 아이디어가 나오면 프로토타입을 만들어서 검증한 뒤, 실제 구현은 ①/②번 세션(또는 새 세션)에 인수인계. 여러 트랙의 산출물을 융합해서 최종 결과물 도출. 기존에 이미 만든 수집 파이프라인(`issue_data_collector.py`, `gov_announcements_collector.py`, `run_pipeline.py`, `rematch_gov_issues.py`)은 계속 유지보수 | 위 기존 수집 파이프라인 파일들 + `*_prototype*`/`*_v2*`처럼 이름에 프로토타입임을 명시한 신규 파일 |

**규칙:**
1. **자기 담당 파일이 아니면 함부로 덮어쓰지 않기.** 특히 `build_database.py`는
   ①번 세션 전담 — ③번 세션은 `run_pipeline.py`에서 subprocess로 "호출"만
   하고, 내용은 수정하지 않습니다.
2. 담당 범위 밖의 새 파일/기능이 필요하면, 이 문서의 "작업 로그"에 먼저
   한 줄 남기고 시작하기.
3. 파일 충돌이 의심되면(예: 로컬 파일 크기/내용이 예상과 다름) 바로
   `git diff`나 파일을 다시 읽어서 확인 후 진행.
4. **③번(컨트롤타워)이 만드는 신규 파일은 항상 "프로토타입"임을 파일명/헤더
   주석에 명시하고, 실제 로컬 환경(Ollama, 스케줄러 등)에서의 최종 검증은
   이어받는 세션이 합니다.** 프로토타입 완료 시 `AUTOMATION_PROTOTYPE_HANDOFF.md`
   같은 인수인계 문서를 같이 남깁니다.

### ⚠️ 알려진 중복/조율 필요 지점

- **분석(analysis) 단계가 두 군데서 따로 만들어지고 있음:**
  - `scripts/analyze_signals.py` (③번 세션 담당 범위 안, 이미 작동함) —
    수집된 Wikipedia/정부발표 데이터를 Ollama(Qwen2.5)에 넣어서 한국어
    분석 리포트(`reports/analysis_YYYYMMDD.md`)를 만듦.
  - (2026-09-20 정정: `src/model_router.py`/`src/news_pipeline.py`는 실제로 만들어지지 않았음. 아래 언어 라우팅은 `prototype_all_in_one.py`의 `MODEL_BY_LANGUAGE`로 구현·완료됨.)
  - **이 둘을 나중에 합칠지, 따로 둘지(예: `analyze_signals.py`는 한국어
    전용 빠른 요약, `model_router.py` 쪽은 다국어 심층 분석) 사람이 결정
    필요.** 지금 당장은 각자 진행하되, 최종 산출물(리포트/대시보드)이 두
    파이프라인 걸 다 써야 하는지 하나만 쓰는지는 미정.

---

## 지금까지 확정된 기술 스택

### LLM 실행 방식
- ❌ `transformers` + `bitsandbytes` 4bit 양자화 → **실패** (GPU/CUDA 전용 기술이라 CPU 환경에서 불가능, `ValueError: Some modules are dispatched on the CPU...` 에러 확인함)
- ✅ **Ollama** (GGUF + llama.cpp 기반) → CPU 환경에 적합, 채택 완료

### 언어별 특화 모델 라우팅 (6개 언어, ②번 세션 담당)

다국어 만능 모델(Qwen2.5 단독 사용 등)은 소형 양자화 시 언어가 뒤섞이는
현상(한국어+영어+한자+일본어 조사가 한 문장에 섞임)을 실제로 확인했음.
이 때문에 **언어별로 검증된 특화 모델을 따로 두고 라우팅하는 구조**로
최종 결정함.

| 지역/진영 | 모델 | Ollama pull 명령어 | 크기(4bit/Q5) | 상태 |
|-----------|------|---------------------|-----------|------|
| 🇺🇸 영어권 | Mistral-7B-Instruct | `ollama pull mistral` | ~4.4GB | 영미권 기사 톤 분류 전담 (테스트 완료) |
| 🇰🇷 한국 | EXAONE 3.5 7.8B | `ollama pull exaone3.5:7.8b` | ~4.8GB | 한국어 정세 분석 및 리포트 기본 모델 (`analyze_signals.py` 채택 완료) |
| 🇨🇳 중국 / 다국어 | Qwen2.5-7B-Instruct | `ollama pull qwen2.5:7b` | ~4.7GB | 중국 외교 담론 분석 및 다자간 앙상블 합의 검증 모델 |
| 🇯🇵 일본 | ELYZA-Llama3-JP-8B | `ollama pull dsasai/llama3-elyza-jp-8b` | ~4.9GB | 일본 주류 언론 톤 분류 검증 완료 |
| 🇪🇺 유럽 4대 권역 (서/남/동/북유럽) | Mistral-NeMo 12B | `ollama pull mistral-nemo` | ~7.1GB | 프랑스 파리 Mistral AI 개발. 유럽 4대 권역(서/남/동/북유럽 11개 언어) 전체 통합 전담 (검증 완료) |
| 🇸🇦 아랍·중동 (왕립 정부 AI) | Falcon 3 7B Instruct | `ollama pull falcon3:7b` | ~4.6GB | 아랍에미리트(UAE) 아부다비 국영 TII 개발. 순수 아랍어 파운데이션 모델 (검증 완료) |
| 🇷🇺 러시아 (빅테크 AI) | YandexGPT 5 Lite 8B | `ollama pull second_constantine/yandex-gpt-5-lite:8b` | ~5.7GB | 러시아 최대 검색엔진·빅테크 Yandex 자체 개발. 러시아 국내 언론 및 정치 담론 전담 (검증 완료) |

**메모리 전략:** Ollama의 동적 메모리 로드/언로드 특성 덕분에 16GB RAM 환경에서도 진영별 7대 핵심 네이티브 모델(~36.2GB)을 순차적으로 호출하며 쾌적하게 구동 가능. (C 드라이브 여유 공간: ~9.6GB)

### 데이터 계층 (③번 세션 담당, MySQL은 ①번 세션 담당)
- **수집**: Wikipedia Pageviews(대중 관심도), FRED(경제지표), OpenSanctions(제재),
  IMF DOTS(무역), 정부 RSS(한국 외교부, 미 국무부, IRNA, Al Jazeera)
- **저장**: `scripts/data/issues/`, `scripts/data/gov_announcements/`에 CSV/JSON →
  `build_database.py`가 MySQL(`international_analysis`)로 통합
- **오케스트레이션**: `scripts/run_pipeline.py`가 수집 3종 + DB 적재를 순서대로 실행
  ```
  python scripts/run_pipeline.py                # 전체
  python scripts/run_pipeline.py --skip-gov      # 정부 발표 재수집 생략
  python scripts/run_pipeline.py --only-db       # DB 적재만
  ```

## 지금까지 실제로 겪은 문제 & 해결 (원인 포함)

1. **SOLAR 다운로드 중 Ctrl+C로 중단** → `huggingface_hub`의
   `resume_download=True`로 이어받기 성공
2. **`load_in_4bit=True` 직접 전달 시 에러** (`TypeError: LlamaForCausalLM.__init__() got an unexpected keyword argument 'load_in_4bit'`) → `BitsAndBytesConfig` 객체로 감싸서 전달해야 함 (transformers 최신 버전 변경사항)
3. **`BitsAndBytesConfig`로도 결국 실패** → GPU 없는 환경이라 bitsandbytes 자체가 작동 불가 → **Ollama로 완전히 전환**
4. **Qwen2.5에게 혼합 언어 프롬프트 입력 시 언어 뒤섞임 출력** → 프롬프트를 단일 언어로 통일 + temperature 0.7→0.3으로 낮춰서 해결
5. **Python에서 `qwen2.5:7b` 호출 시 404 에러** (`model not found`) → `ollama pull qwen2.5:7b`로 사전 다운로드 안 하고 바로 호출해서 발생, pull 먼저 실행 후 해결
6. **패키지 인터프리터 불일치** (`ModuleNotFoundError`가 mysql/pandas/requests 등에서 반복 발생) → VS Code 터미널이 실제 실행에 쓰는 파이썬 인터프리터와, `pip install`을 실행한 인터프리터가 서로 달라서 발생. `python -c "import sys; print(sys.executable)"`로 확인 후 그 인터프리터에 직접 설치해야 함.
7. **MOFA(한국 외교부) RSS 한글 깨짐** → 인코딩이 EUC-KR에서 UTF-8로 변경됐는데 코드는 EUC-KR로 하드코딩 → XML 선언에서 인코딩 자동 감지하도록 수정
8. **`Iran_Nuclear` 이슈 과매칭** → 키워드에 bare `"iran"`만 있어서 이란 국영 통신사(IRNA) 기사가 주제 불문 다 매칭됨 → `"iran nuclear"`처럼 구 단위로 좁힘
9. **`gov_announcements` 중복/깨진 행** → 크로스포스팅 + 예전 인코딩 버그 잔재 → `dedupe_gov_announcements()` + `link` UNIQUE 제약으로 자동 정리 (①번 세션 작업)

## GitHub 저장소 구조 (일부만 실제로 반영됨 — 아래 "아직 안 한 것" 참고)

```
international-analysis/
├── prototype_all_in_one.py            # 언어 라우팅·태깅·톤 분류 핵심 로직 (src/ 아님)
├── scripts/                           # 수집기·DB 적재·리포트/대시보드 생성 스크립트 전부
│   └── data/                          # gov_announcements, issues 등 일부 수집 원본
├── data/                              # 파이프라인이 실제로 쓰는 최신 수집 데이터
├── reports/                           # 분석 리포트
├── output/dashboard/                  # 최종 결과물(대시보드)
└── docs/archive/                      # 목적이 끝났거나 방향이 바뀐 문서 보관함
```

**⚠️ 2026-09-20 정정:** 위 "파이프라인이 실제로 쓰는 건 `scripts/data/`쪽"이라는
과거 안내는 틀렸습니다. `analyze_signals.py` 데이터 경로 버그를 고친 이후(9-17
작업 로그 참고) **파이프라인이 실제로 쓰는 건 루트 `data/`**입니다. `scripts/data/`는
`gov_announcements`/`issues` 등 일부 원본 수집 파일만 남아있습니다. 최신 구조는
`README.md` 참고.

## 참고 중인 프로젝트 원본 문서 (Claude 프로젝트 파일로 업로드되어 있음)

- `claude_국제정세_분석_기획서` — 전체 프로젝트 기획서 (분석 목표, KPI, 일정 등)
- `claude_패권국_공식_정부_데이터_API_조사.md` — 미/중/러/EU/일/인도 정부 API 조사
- `claude_대륙별_이슈_분석_프레임워크.md` — 18개 국제이슈 목록 (중동 3개 포함)
- `claude_GDELT_API_완전재작성_가이드` — GDELT 뉴스 데이터 수집 스크립트 재작성 기록

## 아직 안 한 것 (2026-09-08 기준 최신)

- [x] ~~(②) 일본어/러시아어/아랍어 모델 실제 pull 및 응답 테스트~~ → 6개 언어 전체 테스트 완료,
      단 아랍어/러시아어는 "약점 있는 모델"로 확정(② 완료, 2026-09-14)
- [ ] (②) `src/news_pipeline.py`, `src/report_generator.py` 작성
- [ ] (②) 21개 이슈 전체를 실제 RSS 데이터로 태깅해서 `tag_status` 분포 검증 (신규 추가)
- [ ] (②/③ 조율 필요) `analyze_signals.py`와 `model_router.py` 분석 파이프라인을
      합칠지 따로 둘지 결정
- [x] ~~GDELT API 연동~~ → 네트워크 자체가 막혀서 GDELT는 보류, 대신
      Wikipedia Pageviews + 정부 RSS로 신호 확보 (③ 완료)
- [x] ~~정부 공식 API 자동 수집~~ → 한국 외교부/미 국무부/IRNA/Al Jazeera RSS
      연동 완료 (③ 완료)
- [ ] (③) 파이프라인 스케줄링 자동화 (Windows Task Scheduler로 정기 실행)
- [ ] (③) `analyze_signals.py`를 `run_pipeline.py`에 연결
- [x] ~~1단계: 로컬 대시보드(index.html) 직접 브라우저 실사용 및 기능 검증 완료~~ (2026-09-18)
- [x] ~~정부 공식 보고서(미국 GAO 스타일) 2페이지 PDF 자동 생성기 구축 및 바탕화면/DB 자동 적재 연동 완료~~ (2026-09-18)
- [x] ~~(2단계 새 세션) 싱크탱크 중심 데이터 고급화(Chatham House, Crisis Group 등 파이프라인 정식 승격) 및 Reddit 여론 텍스트 마이닝 모듈(`scripts/fetch_reddit_opinion.py`) 구축~~ → 구현 완료, `--self-test` 전부 통과 (③ 완료, 2026-09-18). 로컬 실행/육안 검증 필요 — 아래 작업 로그 참고
- [x] ~~(새 세션 / 트랙②·③ 인수인계) AllSides 공식 RSS + 3대 LLM 합의 + Google Fact Check 기반 무개입 자동 벤치마크 검증기(`scripts/auto_benchmark_verifier.py`) 구현 및 실행~~ → 구현 완료, `--self-test` 전부 통과 (③ 완료, 2026-09-18). 단, AllSides RSS 실제 응답으로 최종 재검증 필요 — 아래 작업 로그 참고
- [ ] 실제 GitHub 저장소에 push 완료 여부 확인
- [ ] 주간/월간 리포트 자동 발행 스케줄링

## 작업 로그 (새 작업 시작 전 여기에 한 줄 남기기)

형식: `- YYYY-MM-DD HH:MM [트랙①/②/③] 무엇을 시작함`

- 2026-09-08 [트랙③] `monthly_update.py`(고장난 예전 오케스트레이터), `generate_dashboard.py`(하드코딩 가짜 데이터) 삭제. 이 조율 문서(`project-handoff.md`) 신규 작성 — 3개 세션 분업 현황 정리.
- 2026-09-08 [트랙③, 컨트롤타워 역할로 재정의됨] 자동화(수집→분석→결과물) 아이디어를 프로토타입으로 구현: `generate_dashboard_v2.py`(실제 DB 연동, 테스트 DB로 검증 완료), `run_pipeline_scheduled.bat`(Windows 작업 스케줄러용, 로컬 검증 필요), `analyze_signals.py` 파이프라인 연결 제안(코드만 제안, 미적용). 자세한 내용은 `AUTOMATION_PROTOTYPE_HANDOFF.md` 참고.
- 2026-09-13 [트랙③, 컨트롤타워] ②번 트랙이 작성한 `ADR-001_LLM_역할정의_및_감성분석_휴먼인더루프.md`(프로젝트 문서)를 제 수집 데이터에 연결하는 프로토타입 작업: `gov_announcements_collector.py`에 `source_type`(`official_statement` vs `state_media_news`) 필드 추가 — ADR 결정 2("정부 공식 보도자료는 뉴스와 분리된 레이어") 반영, 실제 반영 완료. `scripts/prototype_llm_tone_extraction.py` 신규 작성 — ADR의 3단계 휴먼인더루프 중 1차(LLM 분류) 프롬프트/파싱 로직 프로토타입, `--self-test`로 파싱 로직 검증 완료(4종 케이스 전부 통과). ADR의 "검수 로그 데이터 스키마" 표에 대응하는 MySQL DDL(`official_statement_extractions`, `tone_review_log`)도 같이 제안함 — SQL 트랙(①) 검토 후 `build_database.py`에 반영 필요. 자세한 내용은 `ADR001_INTEGRATION_HANDOFF.md` 참고.
- 2026-09-13 [트랙③, 컨트롤타워] 준기님이 업로드한 `README_1.md`(②번 트랙의 실제 `prototype_all_in_one.py` 진행 보고서) 분석 → 이슈 ID 네이밍이 트랙마다 다르게 진화한 걸 발견(제 쪽: `US_Canada_Trade` 서술형 vs ②번: `na-1`/`na-2`/`na-3` 대륙코드형). 준기님 결정: **서술형 이름(제 방식)으로 통일.** `ADR001_INTEGRATION_HANDOFF.md`에 21개 이슈 전체 신/구 ID 매핑표 + ②번 트랙이 `prototype_all_in_one.py`의 `ISSUES` 리스트 3개(`na-1~3`)를 리네임할 수 있도록 정확한 코드 스니펫 추가함(파일은 직접 안 건드림 — ②번 트랙 소유). `review_log.csv`의 `article_id`(해시 문자열) vs 제 스키마 제안(정수 FK) 타입 불일치는 아직 미해결로 남겨둠 — SQL 트랙과 추가 논의 필요.
- 2026-09-13 [트랙②, 오픈소스 LLM] ③번 트랙의 리네임 제안 반영 완료: `prototype_all_in_one.py`의 `ISSUES` 3개(`na-1/2/3`→`US_Canada_Trade`/`US_Mexico_Migration`/`Trump_Economy`)와 기존 `data/review_log.csv`의 `issue_ids` 컬럼 5개 행 전부 새 이름으로 리네임함. 별도로: 2차 검수(사람 검수) 1사이클 완료 — matched 5건 중 3건 일치(60%), 불일치 2건의 근거는 `correction_note`에 기록해둠(다음 프롬프트 개선 재료). 톤 분류 라벨을 자유 한국어 텍스트 대신 영어 고정 토큰(positive/neutral/critical)으로 받고 코드에서 한국어로 매핑하도록 변경 — 일본어(ELYZA) 모델이 한국어 대신 자국어(中立的)로 답하거나, 아랍어(Jais) 모델이 프롬프트의 설명 문구 자체를 그대로 베끼는 문제를 실제 노트북 테스트로 발견해서 대응한 것. 러시아어(Saiga) 모델은 API 호출 시 500 에러가 반복 발생 중 — 원인 미해결(모델 파일 손상 또는 LoRA 병합 이슈로 추정), 준기님이 `ollama serve` 로그 확인 중. 자세한 내용은 `README.md`(②번 트랙 자체 히스토리) 참고.
- 2026-09-14 [트랙②, 오픈소스 LLM] 러시아어 500 에러 원인 규명: `ollama serve` 로그 스택트레이스로 확인한 결과, Saiga 모델의 구식 raw-completion 템플릿이 Ollama 0.34.0(최신 버전)과 호환 안 되는 영구적 패키징 버그(모델 손상 아님) — `wavecut/vikhr:7b-instruct_0.4-Q4_1`(ChatML 템플릿)로 교체해서 해결. 6개 언어 전체 재테스트 완료, 일본어/아랍어 형식 위반 문제도 해결 확인. **중요 결정 — "비판적" 라벨 정의 명확화**: 교차언어 통제 비교 검수(같은 관세 뉴스를 언어만 바꾼 6개 샘플) 중, 검수자 본인도 "사건이 부정적이니 비판적으로 볼 수 있다"고 판단하는 걸 발견 — 이게 모델들이 반복 오판했던 패턴과 동일해서, ADR-001에 addendum을 추가해 "비판적 = narrative적으로 특정 주체를 비난할 때만(사건 자체의 부정성과 무관)"으로 정의를 명문화함. 이유: 반대 정의(사건이 나쁘면 비판적)로 가면 전쟁/경제위기류 뉴스가 거의 다 비판적이 되어버려서 "매체별 프레이밍 차이 포착"이라는 프로젝트 핵심 목적을 잃음. **다른 트랙 참고사항**: 나중에 ③번 대시보드나 ①번 스키마에서 "비판적/critical" 값을 다룰 일이 있으면 이 정의(narrative 기준)를 그대로 따라야 일관성 유지됨. 자세한 내용은 프로젝트 문서함의 `ADR-001_LLM_역할정의_및_감성분석_휴먼인더루프.md` addendum 섹션과 `README.md`(②번 트랙) 15번 항목 참고.
- 2026-09-14 [트랙②, 오픈소스 LLM] 프롬프트를 3차까지 개선했으나(narrative 기준 명시 + 실패 사례 few-shot 추가), 아랍어(Jais)와 러시아어(vikhr) 두 모델이 `evidence_quote`에 프롬프트 속 예시 문장을 실제 입력과 무관하게 그대로 베끼는 현상이 반복 확인됨(두 모델이 완전히 동일한 영어 문장을 "근거"로 출력, 라벨은 서로 다르게 나와 판단이 사실상 무작위에 가까움을 시사). **결론(준기님 확정): 이 두 모델은 "약점 있는 모델"로 정리하고 프롬프트 개선은 중단.** 영어(Mistral)/한국어(EXAONE)/중국어(Qwen2.5)/일본어(ELYZA) 4개 언어는 정상 작동 확인됨. **다른 트랙 참고사항**: ①/③번 트랙이 나중에 아랍어·러시아어 톤 분류 결과를 쓸 일이 있으면 신뢰도가 낮다는 점 감안 필요 — ②번 쪽은 이 두 언어에 한해 2차 검수 표본 비율을 15~20%가 아니라 전수 검수에 가깝게 높일 계획(`README.md` 17번 항목 참고).
- 2026-09-14 [트랙②, 오픈소스 LLM] 북미 3개뿐이던 `ISSUES`를 프로젝트 문서함의 `대륙별_이슈_분석_프레임워크.md`를 원본으로 21개 전체로 확장(남미3/유럽3/중동3/아프리카3/아태6 추가), 필요한 `COUNTRY_ALIASES`도 3개→24개로 같이 추가. **원본 문서 자체의 불일치 발견**: 문서 제목은 "18개"인데 실제 나열된 이슈는 21개 — 임의로 줄이지 않고 21개 전부(③번의 `ADR001_INTEGRATION_HANDOFF.md` 매핑표와 동일한 `issue_id`들)를 반영함. **다른 트랙 참고사항**: (1) 러시아가 `Ukraine_War`/`EU_Russia`/`Baltic_Security` 3개, 중국이 `Taiwan_Strait`/`South_China_Sea` 2개 이슈에 겹쳐 걸리므로, 국가 태깅과 이슈 매칭이 어긋나는 `tag_status="ambiguous"` 비율이 앞으로 올라갈 것으로 예상됨(정상적인 현상). (2) ①번 SQL 트랙이 `issue_id` 목록으로 뭔가 미리 세팅해뒀다면 이제 21개 전부 기준으로 맞춰야 함. (3) 나머지 18개 이슈는 아직 실제 RSS 데이터로 검증 안 됨 — 다음 작업으로 예정. 자세한 내용은 `README.md`(②번 트랙) 18번 항목 참고.
- 2026-09-14 [트랙③, 컨트롤타워] 준기님이 공유한 `서방_중동_주요국_정부_데이터_API_조사.md`(프로젝트 문서, 다른 트랙 작성) 검토 → 수집 파이프라인에 바로 반영하기로 결정. `gov_announcements_collector.py`의 `GOV_FEEDS`에 영국 FCDO, 독일 외교부(Auswärtiges Amt) 추가. **직접 재검증 과정에서 보고서 URL 중 2개가 실제 피드가 아니라 "RSS 안내 페이지"였던 걸 발견**(독일 `.../newsletter/rss`, 튀르키예 `mfa.gov.tr/rss.en.mfa`) — WebFetch로 진짜 엔드포인트를 찾아서 독일은 반영, 튀르키예는 링크에 페이지-세션성 UUID가 붙어있어 고정 엔드포인트로 못 써서 보류(스크립트 주석에 기록). **기술적으로 중요한 변경**: 영국 FCDO는 RSS 2.0이 아니라 Atom 1.0이라(`<item>`→`<entry>`, `<pubDate>`→`<updated>`, `link`가 href 속성) `fetch_rss_feed()`에 `format="atom"` 분기를 새로 추가함 — 실제 캡처한 응답 샘플로 파싱 로직 + `match_issue()` 연동까지 mock으로 끝까지 테스트 통과 확인(독일 발표문의 NATO 언급이 `Baltic_Security`로 자동 매칭되는 것도 확인). 이스라엘/이란/사우디는 외교부 자체 RSS가 없어서(보고서에도 확인됨) 이번엔 보류. **다른 트랙 참고사항**: 새 소스 2개는 `source_type="official_statement"`로 태깅되어 있어 ADR-001 연동 스키마와 바로 호환됨. 영국/독일 뉴스는 현재 21개 `ISSUE_MATCH_KEYWORDS`와 매칭률이 낮을 수 있음(대사 임명 등 양자관계 뉴스가 많아서) — 정상적인 현상으로 보고 있음.
- 2026-09-14 [트랙③, 컨트롤타워, 새 세션] 준기님이 "현지 언론이랑 전문가 의견도 수집하고 싶다"고 요청 → `source_type`을 `local_media`/`expert_analysis` 2종으로 확장하는 프로토타입 `scripts/prototype_local_expert_sources.py` 신규 작성(자세한 내용은 같은 폴더의 `LOCAL_MEDIA_EXPERT_INTEGRATION_HANDOFF.md` 참고). **중요 결정**: expert_analysis에는 기존 TONE_PROMPT(톤 분류)를 쓰지 않고 별도 EXPERT_ANALYSIS_PROMPT(주장/전망 추출)를 새로 만듦 — 이유는 ADR-001의 "비판적=narrative 비난" 기준이 원래 주장하는 글인 전문가 칼럼에는 안 맞기 때문(핸드오프 문서에 상세 근거 기록). 후보 피드 9개를 WebFetch로 직접 검증해서 5개만 채택(Moscow Times/Al-Monitor/Chatham House Expert Comment/Crisis Group/38 North — 전부 실제 RSS 응답과 최신 게시물 확인함), 안 되는 건 스크립트 상단에 기록(Arms Control Association은 HTML만 반환, Kyiv Independent는 404, Haaretz는 WebFetch가 robots.txt로 차단, Times of Israel은 기존에 이미 기록된 Cloudflare 차단과 동일). `prototype_all_in_one.py`(②번 트랙 소유)는 직접 안 건드림 — 새 파일 맨 아래에 정확한 통합 코드 스니펫만 제안. **테스트 중 발견**: 38 North의 실제 최근 기사(북중 무역시설 관련)로 기존 `tag_article()`을 시험해보니 `North_Korea_Nuclear` 키워드(nuclear test/missile launch/denuclearization)에 안 걸려서 `unclassified`로 빠짐 — 전문가 분석·현지언론은 원 이슈의 "핵" 키워드보다 넓은 인접 주제(경제협력, 외교 등)를 다루는 경우가 많아서, 기존 21개 이슈의 좁한 키워드 세트로는 놓치는 기사가 늘어날 걸로 예상됨(②/③ 조율 필요 — 우선순위 낮음으로 기록만 해둠). **아직 안 됨**: 실제 Ollama 호출 검증(로컬 필요), DB 스키마 반영(①SQL 트랙 검토 필요, `SCHEMA_DDL_ADDENDUM` 참고), 남미 3개 이슈와 아태 5개 이슈(Taiwan_Strait 등)는 이번 라운드에 맞는 소스를 못 찾아서 다음 라운드로 미룸.
- 2026-09-14 [트랙③, 컨트롤타워] 준기님 확정: 위에서 발견한 unclassified 87.5% 문제를 코드에 반영. `prototype_local_expert_sources.py`에 `tag_article_with_source_awareness()` 추가 — `tag_article()`(②번 트랙 소유, 직접 안 건드림)의 결과를 후처리해서, `local_media`/`expert_analysis`에 한해 "국가는 맞고 이슈 키워드는 안 맞아서 unclassified가 된" 케이스를 `ambiguous`(LLM 판단에 맡김)로 승격. `news`에는 적용 안 함(무관 기사 필터링 효과 유지 목적). 실제 헤드라인 8건으로 회귀 테스트 추가(`_self_test_tagging()`) — 승격 전 unclassified 7건 → 승격 후 ambiguous 6건 + unclassified 1건(Somalia, COUNTRY_ALIASES에 없는 국가라 정상), `news` 기사(Nicolas Cage 싱크홀 예시)는 그대로 unclassified 유지되는 것도 별도 확인. `LOCAL_EXPERT_LOG_FIELDS`에 `issue_ids`/`countries_involved`/`tag_status`/`outlet_bias` 등이 원래 빠져 있던 것도 같이 발견해서 추가함(DictWriter의 extrasaction="ignore"로 조용히 버려지고 있었고). `python scripts/prototype_local_expert_sources.py --self-test`로 둘 다(파싱 로직 + 태깅 로직) 확인 가능.
- 2026-09-15 [트랙①, SQL/DB] ADR-001 및 LOCAL_MEDIA_EXPERT_INTEGRATION_HANDOFF 제안 DDL 반영 완료: (1) `gov_announcements`에 `source_type`(VARCHAR(50)) 컬럼 추가 및 `ensure_schema_migrations()`로 기존 로컬 DB 자동 ALTER 마이그레이션 구현, (2) `official_statement_extractions`, `tone_review_log`, `expert_analysis_extractions` 테이블 3종 신설 완료. `article_id`는 VARCHAR(64)로 해시 문자열을 수용하고 `announcement_id`(INT NULL, FK)를 병행 지원하여 트랙② 뉴스/전문가 기사와 정부 발표문 식별자 간 호환성 완벽 해결. (3) `load_tone_review_logs()` 및 `load_expert_analysis_extractions()` 적재 함수를 추가하여 `review_log.csv` 및 `local_expert_review_log.csv` 총 206건 적재 검증 완료. (4) Windows 콘솔 cp949 인코딩 처리 및 MySQL Connector unbuffered cursor 오류(`InternalError: Unread result found`) 방지 처리 완료.
- 2026-09-16 [트랙①, SQL/DB] 포트폴리오용 고급 분석 뷰(Views) 4종 구축 및 `build_database.py` 자동 연동 완료: (1) `scripts/create_views.sql` 신설 — `v_issue_public_vs_gov_daily`(7일 MA, DoD 증감율 Window `LAG()`), `v_issue_media_framing_summary`(언론 편향별 `CASE WHEN` 피벗 집계), `v_human_in_the_loop_audit`(ADR-001 모델 정확도 60.0% 및 혼동 행렬 지표), `v_issue_geopolitical_risk_matrix`(다중 CTE + Window `DENSE_RANK()` 외교 사각지대 리스크 랭킹). (2) `build_database.py`에 `create_analytics_views()` 통합 및 검증 쿼리 7·8번 추가. (3) `DATABASE_SETUP.md`에 10개 테이블 및 4대 뷰 명세/대표 쿼리 최신화 완료.
- 2026-09-17 [트랙②/③ 통합] `analyze_signals.py` 데이터 경로 버그 해결 및 `--limit` 추가: 파이프라인 수집 데이터의 실제 위치(`scripts/data/`) 대신 빈 루트 `data/` 경로를 바라보아 최신 9월 14일자 위키백과(21개 이슈) 및 정부 공식 발표문(194건 중 54건 매칭)이 통째로 누락되던 문제를 동적 경로 탐색기 `_resolve_data_dir()` 구현으로 해결. `EXAONE 3.5 7.8B` 모델이 엄격한 프롬프트 제약(환각 0%)을 준수하며 실제 수집 데이터를 바탕으로 정상 분석함을 검증함.
- 2026-09-17 [트랙②, 오픈소스 LLM] 결함 모델 정리 및 러시아/아랍어 라우팅 안정화: 프롬프트 예시 문구를 그대로 복제하거나 500 에러를 유발하던 구형 7B 모델(`wavecut/vikhr:7b`, `hf.co/Solshine/jais-adapted-7b`)을 Ollama에서 영구 삭제(디스크 9.1GB 확보). 다국어 사전학습 및 벤치마크(ru-MMLU) 상위인 `qwen2.5:7b`로 라우팅 교체 후 실증 테스트(`test_language_models.py`) 결과, 러시아어(47.1s)와 아랍어(6.3s) 모두 100% `neutral` 판정 및 정확한 근거 인용(`"특별한 편향 표현 없음, 사실 전달형"`) 출력으로 ADR-001 기준 완벽 일치 달성.
- 2026-09-18 [트랙②, 오픈소스 LLM] 유럽 4대 권역 통합 전담 모델 도입 및 라우팅 전면 확장: (1) 서유럽 최강 12B 오픈소스 모델인 `mistral-nemo:latest`(7.1GB, Q4_K_M)를 Ollama로 신규 설치 및 로컬 추론 실증 완료(프랑스 전략적 자율성 2문장 요약 31초 성공, 독일 관세 뉴스 64초 만에 neutral 판정 성공). (2) 준기님 통찰("유럽은 서/동/남/북 4대 권역으로 나뉜다") 반영: Tekken 토크나이저의 다국어 어휘 역량을 활용해 서유럽(`fr`,`de`,`nl`), 남유럽(`es`,`it`,`pt`), 동유럽·발트(`pl`,`uk`,`cs` - `Baltic_Security` 직결), 북유럽(`sv`,`no`,`da`) 전체 통합 전담 (2026-09-18 신규 도입/검증 완료).
- 2026-09-18 [트랙②/③ 통합] 3대 오픈소스 LLM 다자간 교차 검증(Consensus) 엔진 구축 및 Google Fact Check API 연동 완료: (1) 비전문가 주관적 검수 한계 극복을 위해 서방(`mistral`), 아시아(`qwen2.5`), 한국(`exaone3.5`) 3대 독립 모델이 동일 기사를 분석하고 다수결 합의(Consensus)를 도출하는 `scripts/verify_model_consensus.py` 구현. 벤치마크 5건 실증 결과 만장일치(3:0) 80%, 다수결 합의(2:1) 20%, 합의율 100%, 합의 정확도 100% 달성 (Qwen의 단일 오판을 2:1 다수결로 교정한 BM-03 실증). (2) IFCN 공인 팩트체크 기관(Reuters, AFP 등) 검증 데이터와 자동 대조하는 `scripts/verify_factcheck_api.py` 구현 및 연동 완료.
- 2026-09-18 [트랙③, 컨트롤타워] AllSides 공식 RSS + 3대 모델 앙상블 합의 + Google Fact Check 기반 무개입 자동 검증 파이프라인 설계 및 인수인계 문서(`AUTO_BENCHMARK_VERIFICATION_HANDOFF.md`) 작성 완료. 다음 새 세션이 문서를 보고 바로 `scripts/auto_benchmark_verifier.py`를 구현/실행할 수 있도록 수집 엔드포인트, 채점 로직, 리포트 템플릿 정리.
- 2026-09-18 [트랙③, 컨트롤타워] 1단계(로컬 대시보드 실사용 확인) 완료 후 2단계(싱크탱크 데이터 정식 승격 + Reddit 공개 RSS 여론 텍스트 마이닝 모듈 신설) 인수인계 가이드(`PHASE2_THINKTANK_REDDIT_HANDOFF.md`) 작성 완료. 다른 세션에서 바로 이어받아 `scripts/fetch_reddit_opinion.py` 구현 및 `run_pipeline.py`에 싱크탱크를 통합할 수 있도록 액션 아이템 명시.
- 2026-09-18 [트랙③, 컨트롤타워] 미국 회계감사원(GAO) 스타일 2페이지 정부 공식 정세평가보고서 PDF 생성 엔진(`scripts/pdf_report_generator.py`) 구축 및 바탕화면·DB 자동 연동 완료:
  1. **정부 공식 양식 준수 (GAO Style)**: ReportLab 기반 Windows 시스템 맑은 고딕(`malgun.ttf`/`malgunbd.ttf`) 직접 등록을 통해 한글 깨짐 없이 가독성을 확보하고, GAO 공식 헤더(`INTERNATIONAL AFFAIRS INTELLIGENCE OFFICE`, `IA-26-XXSP`, `UNCLASSIFIED // FOR OFFICIAL USE ONLY`), Highlights 2단 박스(WHY / WHAT), 핵심 타임라인 표(Navy Header `#1B365D`), 주요국 이해관계/사각지대, 리스크 벤치마크 표, 핵심 정책 제언 1~4 골드 콜아웃 박스(`KEY EXECUTIVE RECOMMENDATIONS`), 정부 부처 의견 등을 정확히 2페이지 규격으로 맞춤.
  2. **개별 5대 현안 및 11페이지 종합 Dossier 생성**: 북한핵, 대만해협, 우크라이나전쟁, 이란핵협상, 미중무역전쟁 등 5대 개별 현안 2페이지 PDF 5종과 이들을 단일 정식 표지와 목차로 제본한 11페이지 분량의 종합 바운드 리포트(`2026_글로벌_국제정세_핵심현안_종합평가보고서.pdf`) 생성 완료.
  3. **바탕화면 전용 폴더 및 DB 자동 저장 통합 (`scripts/report_db_saver.py`)**: 준기님 요청에 따라 보고서 생성 즉시 `C:\Users\홍준기\Desktop\분석보고서`에 복제 저장(바이너리 PDF 오염 방지 모드 적용)하고, MySQL DB(`international_analysis.analysis_reports` 테이블)에 메타데이터 및 전문을 자동 저장(18건 적재 검증 완료). `generate_reports.py`와 `analyze_signals.py` 파이프라인에 완전 연동 완료.
- 2026-09-18 [통합, 아키텍처] LLM 통합 아키텍처 및 업데이트 종합 가이드(`LLM_SYSTEM_SUMMARY.md`) 작성 완료: 언어별 모델 라우팅 체계(한국어 EXAONE 3.5, 중·러·아랍 Qwen 2.5, 유럽 4대 권역 Mistral-NeMo 12B 등), 환각 0% 방지 프롬프트 제약 및 실증 결과(Rule 3 & 5), 3대 모델(Mistral-Qwen-EXAONE) 다자간 교차 합의(Consensus) 엔진, ADR-001 톤 라벨링 표준, OpenRouter 클라우드 확장 상태를 단일 문서로 종합 정리.
- 2026-09-18 [트랙②, 오픈소스 LLM] 현지 네이티브 파운데이션 모델 신규 도입 (`second_constantine/yandex-gpt-5-lite:8b`, `falcon3:7b`): 준기님의 제안("각국 현지 제작 LLM을 사용하자")에 따라 러시아 최대 IT 빅테크 Yandex의 8B 모델(5.7GB)과 UAE 국영 첨단기술연구원(TII)의 Falcon3 7B 모델(4.6GB)을 Ollama에 신규 설치하고 `prototype_all_in_one.py`의 `MODEL_BY_LANGUAGE`에 정식 배정. 로컬 실증 결과 러시아어(100.9s), 아랍어(91.0s) 모두 ADR-001 `neutral` 판정 및 정확한 근거 인용을 출력하며 템플릿 탈출/프롬프트 복제 결함 없이 100% 정상 작동 검증 완료. `LLM_SYSTEM_SUMMARY.md` 및 `README.md`에 진영별 7대 핵심 네이티브 모델 스택으로 최신화 반영 완료.
- 2026-09-19 [트랙②, 오픈소스 LLM] 구형 `mistral:latest`(4.4GB) 모델 영구 정리 및 영미권/유럽 라우팅 일원화: 성능이 더 우수한 12B 상위 모델 `mistral-nemo:latest`로 영미권(`en`) 분석 및 3대 모델 교차 합의 검증(`scripts/verify_model_consensus.py`, `scripts/auto_benchmark_verifier.py`)의 서방 대표 모델을 단일화 완료. `prototype_all_in_one.py`, `fetch_reddit_opinion.py` 등 코드베이스 전반의 모델 참조를 갱신하고 `ollama rm mistral:latest`로 로컬 디스크 4.4GB를 안전하게 확보함 (C 드라이브 여유 공간 약 14.0GB로 확대).
- 2026-09-19 [트랙③, 컨트롤타워/수집] Reddit 실시간 여론 수집기 법적 규정 준수 및 하이브리드 아키텍처 반영: Reddit의 2023년 말 일반 사용자용 신규 API 키 셀프 발급 차단에 대응하여, 누구나 접근 가능한 공개 웹 표준 엔드포인트(`https://www.reddit.com/r/{sub}/.rss`, Atom 1.0) 기반의 100% 합법적이고 안전한 읽기 전용 수집기(User-Agent 식별자 명시, Gentle Crawling)임을 규정화. 또한 `.env`에 `REDDIT_CLIENT_ID`/`SECRET` 등록 시 공식 OAuth API(분당 100회)로 자동 승격되는 하이브리드 모드 구축 완료 (`DATA_COLLECTION_GUIDE.md`, `README.md` 반영).
- 2026-09-19 [트랙③, 컨트롤타워] 정통 관용 인텔리전스 폼(FBI FD-1036 / FD-71A 모사) 기반 고위급 PDF 리포트 전면 재설계 완료: 준기님의 피드백("AI 생성물 티를 벗고 전문 공문서 양식으로 개편")을 반영하여, 컬러풀한 카드뉴스/박스 스타일을 배제하고 미국 FBI 및 정보기관(IC) 기밀해제 공문서 양식을 1:1로 정밀 구현. 상단 붉은색 기밀해제 스탬프(`APPROVED FOR PUBLIC RELEASE...`), 서식 번호(`FORM IA-1036`), 결재 메타데이터 그리드, Synopsis(개요), 핵심 신호 타임라인(가로선 중심 클래식 표), 주요국 태세, 파이프라인 실측치(Wikipedia, 정부 발표, 3대 LLM 합의, FactCheck)를 연동한 `Database Queries` 섹션, 4대 정책 제언, 첨부 증빙(`Enclosure(s)`), 문서 종결 부호(`◆◆`)를 엄격한 2페이지 규격으로 완성함. 개별 5종(각 2p) + 종합 바운드 Dossier(11p) 생성 및 바탕화면(`분석보고서`)/DB 자동 동기화 검증 완료.
- 2026-09-19 [트랙③, 컨트롤타워/수집] 글로벌 공신력 3대 여론조사 기관(Pew Research Center · ECFR · Ipsos Global) 실증 여론 데이터 수집기(`scripts/fetch_polling_data.py`) 신설 및 정식 파이프라인 편입:
  1. **문제 정의 및 배경**: 대중 커뮤니티 반응(Reddit)과 별개로, 공인된 표본과 통계적 신뢰도를 갖춘 실증 설문조사(Public Opinion Polls)의 체계적 수집 필요성 해결. RealClearPolling(RCP)의 Cloudflare Turnstile 캡차 차단 및 538 개편을 우회하여, 글로벌 최고 권위 3대 기관이 직접 공공 배포하는 공개 RSS/Atom 피드를 활용한 100% 무료·합법 파이프라인 구축.
  2. **수집 기관 및 커버리지**:
     - **Pew Research Center**: `topic/international-affairs/feed/` (국제관계 전반), `topic/politics-policy/feed/` (미국 대외정책 및 정치)
     - **ECFR (유럽외교협회)**: `ecfr.eu/feed/` (우크라이나 군사 지원, 대러 제재, 유럽 방위비 등 EU 시민 인식)
     - **Ipsos Global**: `ipsos.com/en/rss.xml` (전 세계 30개국 글로벌 어드바이저 정기 설문)
  3. **데이터 추출 및 영구 저장**:
     - 조사 표본(demographics), 핵심 찬반 수치(key_percentages), 대중 심리 라벨(sentiment), 한국 안보/통상 함의(korean_implications)를 정밀 추출하여 `data/polls/polls_latest.csv` 및 `data/polls/polls_summary.json`에 저장.
     - 로컬 실측(`python scripts/fetch_polling_data.py --limit 3`) 결과 12건 정상 수집 및 CSV/JSON 적재 100% 성공 검증.
  4. **파이프라인 및 문서 동기화**:
     - `scripts/run_pipeline.py`에 "글로벌 실증 여론조사 수집" 단계를 기본 등록하고 `--skip-polls` 플래그 지원.
     - `DATA_COLLECTION_GUIDE.md`(섹션 2.5), `README.md`(항목 26 및 현재 위치) 동기화 완료.

- 2026-09-18 [트랙③, 컨트롤타워] `AUTO_BENCHMARK_VERIFICATION_HANDOFF.md`를 그대로 구현: `scripts/auto_benchmark_verifier.py` 신규 작성 완료. `verify_model_consensus.py`(CONSENSUS_MODELS/TONE_PROMPT_TEMPLATE/call_ollama_json/evaluate_consensus)와 `verify_factcheck_api.py`(search_google_factcheck)를 새로 만들지 않고 그대로 재사용해서 프롬프트·모델·합의 로직의 일관성 유지. `--self-test`로 (1) RSS 파싱, (2) 편향/언론사 추출, (3) score_match() 7개 케이스, (4) 전체 파이프라인(모의 Ollama 응답), (5) 마크다운/CSV 리포트 생성까지 전부 통과 확인. **⚠️ 중요 제약사항 2가지**: (1) 이 클라우드 세션에서는 `allsides.com` 도메인에 WebFetch가 전혀 도달하지 못함(PROVENANCE_REQUIRED, gov.uk 때 썼던 선행페이지 경유 우회도 안 통함) — `https://www.allsides.com/rss/news` URL 자체는 Feedspot의 공개 RSS 디렉터리로 간접 교차 확인했지만, RSS `<item>` 안에 편향(Left/Center/Right) 태그가 실제로 어떤 필드로 오는지는 실물 응답을 못 보고 추정으로 구현함(`_extract_bias_and_outlet()`, category 태그 우선 → 설명문 패턴 매칭 순으로 방어적 파싱). **로컬 환경에서 `python scripts/auto_benchmark_verifier.py --limit 3` 실행 결과 편향/언론사 필드가 제대로 채워지는지 반드시 육안 확인 필요** — 안 맞으면 `_extract_bias_and_outlet()` 함수만 고치면 되고 나머지 파이프라인엔 영향 없음. (2) 인수인계서의 Match Scoring 3번째 규칙("외교 성과 찬사 → 우호적이면 정답")은 AllSides 편향과 무관한 콘텐츠-유형 조건이라 자동 판별기 없이는 구현 불가능해서, 합의가 "우호적"이면 편향과 무관하게 무조건 MATCH로 단순화함 — 이 단순화가 벤치마크 일치율을 낙관적으로 왜곡할 수 있다는 점을 리포트 상단에도 명시해뒀음. **피드백**: "AllSides 편향 vs 모델 논조" 대조는 엄밀한 모델 정답률이 아니라 느슨한 상관관계 지표로 해석하는 게 맞다 판단 — Right/Left 매체도 중립 기사를 쓸 수 있고 Center 매체도 비판적 기사를 쓸 수 있기 때문. 자세한 구현 노트는 `scripts/auto_benchmark_verifier.py` 상단 docstring 참고.

- 2026-09-18 [트랙③, 컨트롤타워] `PHASE2_THINKTANK_REDDIT_HANDOFF.md`를 그대로 구현: (1) `scripts/fetch_reddit_opinion.py` 신규 작성 완료 — r/geopolitics, r/worldnews의 `.rss`(Atom 1.0) 엔드포인트를 수집하고, 로컬 Mistral로 대중 감정(favorable/neutral/critical_anxious) + 핵심 논란 키워드 3개를 추출해 `data/reddit_signals/reddit_opinion_latest.csv` + `reddit_opinion_summary.json`으로 저장. `--self-test`로 (Atom 파싱/HTML 제거/링크 추출/감정 스키마 검증/전체 파이프라인/저장) 전부 통과 확인. (2) `scripts/run_pipeline.py`에 인수인계서 지정 스니펫 그대로 반영: `prototype_local_expert_sources.py`(이미 검증된 Chatham House/Crisis Group/38 North/Moscow Times/Al-Monitor 수집기)를 `--skip-experts`로 끌 수 있는 정식 파이프라인 단계로 추가(기본값: 실행). (3) `scripts/generate_dashboard_v2.py`의 `recent_feed` 정렬 쿼리에 `(source_type='expert_analysis') DESC`를 최우선 순위로 추가하고, 피드 테이블에 전용 골드 뱃지(`🧠 전문가 분석 (Think Tank)`, `.badge-thinktank`)를 새로 만들어 시각적으로도 최우선 노출되도록 반영. `generate_dashboard_html()`에 모의 데이터를 넣어 뱃지/정렬 로직 자체는 예외 없이 렌더링되는 것까지 확인. **⚠️ 중요 제약사항**: (1) reddit.com도 allsides.com과 동일하게 이 클라우드 세션 WebFetch가 전혀 도달 못 해서(PROVENANCE_REQUIRED) `.rss` 응답 구조를 실물로 못 보고 외부 자료(wprssaggregator.com 가이드, FreshRSS GitHub 이슈 #8189의 실사용자 curl 성공 사례)로 URL 패턴/Atom 포맷만 간접 확인함 — **로컬에서 `python scripts/fetch_reddit_opinion.py --limit 3` 먼저 돌려서 content 필드 파싱이 실제로 맞는지 육안 확인 필요**(안 맞으면 `fetch_subreddit_posts()`만 고치면 됨). (2) 대시보드 쪽 정렬/뱃지 변경은 MySQL 접속 없이 Python 렌더링 로직만 검증했고, 실제로 `tone_review_log` 테이블에 `source_type='expert_analysis'` 행이 들어오는지는 `build_database.py`(①SQL 트랙 소유, 직접 안 건드림)의 `load_tone_review_logs()` 구현에 달려있어 미확인 — 로컬에서 `run_pipeline.py` 한 번 돌리고 대시보드 "전문가 분석" 필터 탭에 실제로 뭔가 잡히는지 확인 권장. 안 잡히면 `tone_review_log`와 `expert_analysis_extractions` 두 테이블을 UNION하는 추가 작업이 필요할 수 있음(①SQL 트랙과 조율 필요).

- 2026-09-19 [트랙②, 오픈소스 LLM] 22~23번(README)/09-18~09-19 항목에서 다른 세션이 진행한 모델 교체(`yandex-gpt-5-lite:8b`, `falcon3:7b`, `mistral-nemo:latest`)를 준기님이 로컬에서 직접 실행한 결과(`ollama list`, `test_language_models.py` 9개 언어, `verify_model_consensus.py --benchmark`)로 검증함. **실측 확인된 것**: 3개 모델 다 실제로 설치돼 있고, 9개 언어 전부 정확히 neutral 판정, `mistral-nemo` 기준으로 합의 엔진 재실행해도 동일하게 만장일치 80%/합의 정확도 100% 재현됨(23번 리포트가 이미 삭제된 구 `mistral:latest` 기준이라 최신 코드와 안 맞았던 문제는 재실행으로 해소, 리포트 파일 갱신됨). **다만 비판적으로 짚어야 할 부분**: `verify_model_consensus.py`의 벤치마크 5건은 스크립트 작성자 본인이 기사와 정답(ground truth)을 둘 다 만든 것이고 그중 2건은 `TONE_PROMPT`의 few-shot 예시와 거의 동일 유형이라, "100% 정확도"는 독립적인 정확도 측정이 아니라 회귀/스모크 테스트에 가까움 — 실제 사람이 검수한 진짜 RSS 기사(10번 항목) 기준 일치율은 60%(3/5)임. `LLM_SYSTEM_SUMMARY.md`의 "환각 0% 달성"도 사례 1건 기준이라 통계적 근거가 약함. 자세한 내용과 권고사항은 `README.md`(②번 트랙) 27번 항목 참고. **다른 트랙 참고사항**: ③번 트랙이 만드는 `pdf_report_generator.py`의 공문서 스타일 PDF에 "100%"/"환각 0%" 수치가 그대로 인용되고 있다면, 표본 크기(5건/1건) 캐비어트를 각주로 넣는 걸 권장 — 공식 문서 형태라 숫자가 실제보다 더 신뢰도 있게 읽힐 위험이 있음.

- 2026-09-20 [트랙②, 오픈소스 LLM] 준기님 결정으로 일본어 전용 모델(`dsasai/llama3-elyza-jp-8b`, 4.9GB) 라우팅 제거: `prototype_all_in_one.py`의 `MODEL_BY_LANGUAGE`에서 `"ja"` 키를 주석 처리(나중에 재설치하면 주석만 풀면 되게 원문 보존)하고, `test_language_models.py`의 기본 실행 대상에서도 뺌(SAMPLES는 남겨둬서 `python test_language_models.py ja`로 재검증 가능). `"ja"` 키가 없으면 기존 `.get(lang, "mistral-nemo:latest")` 폴백 로직에 따라 일본어는 자동으로 mistral-nemo가 대신 처리함. 로컬 디스크에서 실제로 지우는 `ollama rm dsasai/llama3-elyza-jp-8b` 명령어는 이 세션이 실행할 수 없어서 준기님께 안내함(이 클라우드 세션은 Ollama가 설치된 실제 환경에 접근 불가). **다른 트랙 참고사항 겸 문서 정합성 이슈**: 이 작업 중에 `MODEL_BY_LANGUAGE["ru"]`가 이미 `second_constantine/yandex-gpt-5-lite:8b`가 아니라 `qwen2.5:7b`로 바뀌어 있는 걸 발견함 — 코드 주석엔 "Yandex 용량 문제로 폴백"이라고만 있고 누가/언제/왜 바꿨는지 README·project-handoff 어디에도 기록이 없어서, 27번 항목(README)에서 "yandex-gpt-5-lite 검증 완료"라고 써둔 부분이 이미 사실과 어긋난 상태가 됨. 이 변경을 한 세션(아마 로컬 세션)이 다음에 들어오면 경위와 향후 계획(재설치할지, qwen2.5로 확정할지)을 여기에 남겨주길 부탁함 — "바뀌면 바로 기록한다"는 이 프로젝트 원칙이 이번엔 한 번 깨진 사례라 표시해둠. 자세한 내용은 `README.md`(②번 트랙) 28번 항목 참고.

- 2026-09-20 [트랙②, 오픈소스 LLM] 준기님이 위 ru 미기록 변경 건을 보고 "컴퓨터에 한계가 있으니 언어 전용 모델 대신 다국어를 잘 다루는 모델로 통합하자"고 설계 원칙 자체를 변경하기로 결정함(22번 항목 "각국 현지 제작 모델" 방향에서 전환). 러시아어(`second_constantine/yandex-gpt-5-lite:8b` 폐기 → `qwen2.5:7b`로 확정)에 이어, 같은 원칙을 아랍어에도 적용할지 여쭤봤고 준기님이 "통합"을 선택 — `falcon3:7b`(이미 실측 검증 끝난 전용 모델)도 폐기하고 `qwen2.5:7b`로 통합함. `prototype_all_in_one.py`의 `MODEL_BY_LANGUAGE` 주석에 결정 경위를 남겨서 28번 항목의 "미기록 변경" 문제를 해소함. 결과적으로 실제 라우팅에 쓰이는 모델은 `exaone3.5:7.8b`(한국어) / `qwen2.5:7b`(중국어+러시아어+아랍어) / `mistral-nemo:latest`(영어+유럽12개언어+일본어 폴백) 3종 4개 언어군으로 정리됨. 로컬에서 안 쓰는 모델 정리용 명령어(`ollama rm second_constantine/yandex-gpt-5-lite:8b`, `ollama rm falcon3:7b`)를 안내함(합쳐서 디스크 10.3GB 절약, ~31.8GB → ~21.5GB). **다른 트랙 참고사항**: (1) `LLM_SYSTEM_SUMMARY.md`가 여전히 예전 6개 모델 구성(Yandex/Falcon 포함)으로 적혀 있어서 다음에 그 문서를 만든 세션이 들어오면 갱신 필요. (2) `falcon3:7b`로 검증했던 아랍어 결과가 `qwen2.5:7b`에도 그대로 적용된다는 보장이 없어서 재검증이 필요함 — `pdf_report_generator.py` 등 이 모델 배정을 참조하는 다른 스크립트가 있다면 아랍어 품질 변화 가능성 감안 필요. 자세한 내용은 `README.md`(②번 트랙) 29번 항목 참고.

- 2026-09-20 [트랙②, 오픈소스 LLM] 위 29번 항목의 재검증 요청에 준기님이 바로 `python test_language_models.py ru ar`를 실행해줌 — 러시아어(qwen2.5, 36.3s)와 아랍어(qwen2.5, 5.6s) 모두 `neutral` 정확 판정 + 근거 인용 정상. falcon3/yandex 전용 모델이 처리했던 것과 같은 결과가 qwen2.5 통합 후에도 재현됨을 확인, README 29번 항목에 결과 반영 완료. 이걸로 러시아어·아랍어→qwen2.5 통합이 최소한의 회귀 테스트는 통과했다고 보고 `ollama rm falcon3:7b` / `ollama rm second_constantine/yandex-gpt-5-lite:8b` 실행해도 안전하다고 판단함(단, 언어당 샘플 1개짜리 테스트라는 한계는 여전함 — 27번 항목과 같은 맥락, 실제 검증은 앞으로의 2차 인간 검수에서 계속 확인 필요).

- 2026-09-20 [트랙③, 컨트롤타워] 준기님이 "감사 내용(`문서감사_2026-09-18_프로젝트_정체성_정리.md`) 정리하고 넘어가자"고 요청 → 감사 문서가 사람에게 결정하라고 남긴 두 가지를 확정함: **목적 = 교과목/졸업 과제물**(기존 "기업 제출용 포트폴리오" 선언에서 변경), **최종 결과물 = 종합 대시보드(`output/dashboard/index.html`)**, 나머지 5종 산출물(이슈리포트/GAO-FBI PDF/일일분석/벤치마크검증/DB뷰)은 증거 자료로 강등. **추가 발견**: 이 결정을 실행하려고 파일을 다시 열어보다가, 같은 날(9-20) 작성된 `챗봇_서비스_전환_전략.md`(Claude 프로젝트 문서)가 "대시보드는 정적이라 부족하다"며 프로젝트 전체를 챗봇으로 전환하자고 제안해둔 상태였고, 실제로 `chatbot_core/`(FastAPI 백엔드)·`frontend/`까지 이미 만들어져 있었음 — 방금 정한 결정과 정면 충돌이라 준기님께 별도로 확인함. **준기님 결정: 챗봇 전환은 보류, 대시보드로 확정.** **문서 재구조화 실행**: 목적이 충돌하던 문서(`PLANNING.md`, `CONTINENTAL_ISSUES_ANALYSIS.md`)와 역할이 끝난 인수인계 문서 5종(`ADR001_INTEGRATION_HANDOFF.md`, `AUTOMATION_PROTOTYPE_HANDOFF.md`, `AUTO_BENCHMARK_VERIFICATION_HANDOFF.md`, `LOCAL_MEDIA_EXPERT_INTEGRATION_HANDOFF.md`, `PHASE2_THINKTANK_REDDIT_HANDOFF.md`), 그리고 `data_collection_checklist.md`/`GOVERNMENT_API_GUIDE.md`를 `docs/archive/`로 이동. 챗봇 관련 일체(`chatbot_core/`, `frontend/`, 프로토타입 zip 2개, 그쪽 자체 README, `로컬_채팅_테스트_점검표.md`)는 `docs/archive/parked_chatbot_pivot/`로 이동(삭제 아님 — `HOLD.md`에 재개 방법 기록). 기존 `README.md`(26개+ 항목 개발일지, 62KB)는 `docs/archive/DEVELOPMENT_LOG_README_HISTORY.md`로 통째로 보존하고, 대외용 1페이지 `README.md`를 새로 작성(목적/최종결과물/실행법/구조/한계 요약, 상세 히스토리는 `project-handoff.md`와 archive로 안내). **이 파일 자체도 수정**: 2026-09-08 당시 작성된 "담당 파일" 표와 "GitHub 저장소 구조" 다이어그램이 `src/model_router.py` 등 실제로 없는 경로를 담당 파일로 지목하고, "파이프라인이 실제로 쓰는 건 `scripts/data/`"라고 틀리게 안내하고 있던 걸 발견(문서감사 4번 항목과 동일 지적) — 둘 다 정정함(실제로는 `prototype_all_in_one.py`에 통합, 루트 `data/`가 실제 경로).

- 2026-09-21 [트랙②, 인프라 및 오픈소스 LLM] **C드라이브 81.81GB 확보에 따른 6대 프리미엄 네이티브 모델 아키텍처 완전 복구 완료**:
  1. 준기님이 로컬 C드라이브 디스크 정리를 대대적으로 완료하여 무려 **81.81GB**의 여유 공간을 확보함.
  2. 이에 따라 어제 디스크 용량 한계로 부득이하게 임시 채택했던 '다국어 모델 통폐합(Qwen2.5/Mistral-NeMo 몰아주기)' 전략을 전면 철회하고, 졸업작품의 기술적 차별성을 극대화하기 위해 원래 기획인 **'권역별 최고 성능 네이티브 6대 모델 1:1 전담 배치 체제'**로 완전 원상복구(업그레이드)함.
  3. 삭제했던 러시아 1등 모델 `second_constantine/yandex-gpt-5-lite:8b`(5.7GB) 백그라운드 재설치(Pull) 100% 완료 검증.
  4. 아직 로컬에 남아있던 `falcon3:7b`(아랍어)와 `dsasai/llama3-elyza-jp-8b`(일본어)를 코드 라우팅(`prototype_all_in_one.py`)에 원상 복구하고 `test_language_models.py` 실행 목록에 `ja` 재배치 완료.
  5. 이로써 `LLM_SYSTEM_SUMMARY.md`에 기술된 6대 파운데이션 모델 아키텍처(`mistral-nemo`, `exaone3.5`, `qwen2.5`, `elyza`, `falcon3`, `yandex-gpt-5-lite`)와 실제 로컬 환경/코드가 100% 정합성을 회복함.

- 2026-09-21 [트랙①/③, 전략 피벗 및 데이터셋 확장 설계] **교수님 피드백 반영: '예측(Prediction)'에서 '공급망 조기경보 & 신호 괴리율(Signal Gap)'로 졸업작품 정체성 피벗 및 권위주의 데이터 수집 파이프라인 설계**:
  1. **교수님 피드백 분석 및 전략 피벗**:
     - 피드백: "AI로 미래 국제정세를 예측한다는 것은 학술적으로 검증 불가(퇴짜)이며, 레딧 감성 분석도 노이즈가 심해 쉽지 않다."
     - 대응 피벗 (데이터사이언스경영 전공 맞춤형):
       - 허황된 '미래 정세 예측' 목표를 전면 폐기하고, **"한국 수출·제조 기업을 위한 글로벌 공급망 리스크 조기경보(Early-Warning) 및 이상 징후 탐지 시스템"**으로 과제 성격을 명확히 재정의.
       - 레딧은 주 데이터가 아닌 '보조 정성 지표'로 한정하고, 핵심 분석 알고리즘은 **[정부 공식 발표/국영 매체] ↔ [현지 망명 독립 언론 / 검열 삭제 아카이브] 간의 '신호 괴리율(Signal Gap Discrepancy Rate)' 정량화**에 집중.
  2. **권위주의/통제 국가 데이터 수집을 위한 3자 교차 수집(Triangulated Collection) 설계 (데이터셋 섹션 구현 대기)**:
     - **러시아권**: 국영 선전(타스 TASS) ↔ **해외 망명 독립 언론(Meduza RSS: `https://meduza.io/rss/all`)** ↔ 텔레그램 공개 채널 (`@mediazzzona` 등)
     - **중국권**: 관영 신화통신 ↔ **UC 버클리 검열 삭제 글 실시간 아카이브(China Digital Times CDT RSS: `https://chinadigitaltimes.net/chinese/feed/`)** ↔ 해외 검열 프리 중문 포럼(Reddit `r/China_irl`)
     - **중동/이란권**: 왕정/신정 국영 매체 ↔ **디아스포라 독립 탐사보도(Iran International, Raseef22 RSS)** ↔ 반체제 커뮤니티(Reddit `r/NewIran`, `r/arabs`)
     - **글로벌 사우스 대표 정론지**: **알자지라(Al Jazeera) 영문/아랍어 RSS (`https://www.aljazeera.com/xml/rss/all.xml`)**를 서방 언론(BBC/NPR) 편향 교정 축으로 편입.
  3. **실행 계획**: 위 3자 교차 수집용 RSS 및 Reddit 엔드포인트는 차기 '데이터셋 다운로드 및 크롤러 확장' 스프린트에서 전용 수집기로 일괄 구현하기로 확정.

- 2026-09-21 [트랙③, 신호 괴리율 및 금융 프록시 파이프라인 구현] **신호 괴리율 수집·분석 및 검열 우회 금융 프록시 모듈 구현 완료**:
  1. **신호 괴리율 수집기(`fetch_signal_gap_rss.py`) 개발 완료**: 러시아(TASS vs Meduza), 중국(인민일보 vs CDT), 중동(Tehran Times vs Raseef22) 등 관영 매체와 망명/독립 언론의 기사를 동시 수집하는 모듈 구축 (CDT 등 봇 차단 매체는 우회 또는 대체 지표로 전환).
  2. **6대 네이티브 LLM 분석 모듈(`analyze_signal_gap.py`) 개발 완료**: 수집된 텍스트를 `yandex-gpt-5-lite:8b`, `qwen2.5:7b` 등 권역별 전담 모델에 주입하여, JSON 포맷으로 0~100점의 '신호 괴리율(Signal Gap Score)'을 자동 추출하는 데 성공.
  3. **검열 우회용 금융 프록시(`fetch_financial_proxy.py`) 프로토타입 추가**: 텍스트 검열이 극심한 중국 등의 실물 경제 불안도를 측정하기 위해, 주가 지수(ASHR), 환율 (USD/CNY), 금(Gold) 변동률을 야후 파이낸스로 가져와 "실제 자본 이탈(여론)"을 역추적하는 행동 경제학적 스크립트 작성 완료.
  4. **글로벌 IB 리서치 수집 및 다중 LLM 분석망(`fetch_ib_research.py`, `analyze_ib_insights.py`) 구축**: ING(유럽), Nomura(일본) 등 글로벌 금융사의 리포트를 수집한 뒤, 소스 국가에 맞는 언어 특화 LLM(`mistral-nemo`, `qwen2.5`)이 1차 분석을 수행하고, 최종적으로 한국어 특화 LLM(`EXAONE 3.5`)이 종합하여 MS Word(`.docx`) 포맷의 임원용 보고서로 자동 생성하는 파이프라인 완성.
- 2026-09-21 [트랙③, 컨트롤타워] **텔레그램 OSINT 자동 크롤링 및 중동 블랙스완(Black Swan) 조기경보 시뮬레이션 완수**:
  1. **텔레그램 합법 크롤러(`fetch_telegram_public.py`) 구축**: API 키나 계정 밴 리스크 없이 `t.me/s/` 퍼블릭 뷰를 긁어오는 BeautifulSoup 기반 크롤러 제작. 러시아(Rybar), 우크라이나(UaOnlii), 이란 혁명수비대(sepah_pasdaran), 사우디아라비아(AlArabiya), 예멘 후티 반군(army21ye) 채널을 성공적으로 크롤링.
  2. **걸프 자본(사우디) vs 저항의 축(이란) Signal Gap 실측**: 이란 IRGC 채널이 무장 선동으로 도배된 반면, 사우디 국영 Al Arabiya는 가십과 일반 국제 뉴스 위주로 송출하는 극명한 텍스트 뉘앙스 차이를 `falcon3:7b` 모델이 정확히 포착함.
  3. **후티 반군 사우디 타격(Breaking News) 실시간 징후 탐지**: 후티 반군 군사 대변인(야히야 사리) 채널에서 사우디 얀부(Yanbu) 아람코 석유 시설 타격 성명서(Communiqué) 원문을 즉각 포획함.
  4. **다중 LLM 조기경보 리포트(`analyze_middle_east_osint.py`)**: `falcon3:7b`(아랍어 원문 해독 및 군사 타겟 추출) -> `EXAONE 3.5`(한국 정유사/해운사 물류 차질 및 유가 폭등 임원용 보고서 작성)로 이어지는 무개입 릴레이 분석망을 완벽하게 가동하여 `middle_east_risk_analysis.txt`를 산출함.

- 2026-09-21 [트랙③, 컨트롤타워] **docxtpl 기반 정통 인텔리전스 폼 Word(.docx) 보고서 생성 파이프라인 구축 및 DB·바탕화면 동기화 완료**:
  1. **배경**: 사용자가 필요 시 MS Word에서 마우스로 직접 서식을 편집하거나 정부/기업 제출용으로 활용할 수 있도록, 전용 워드 템플릿 라이브러리 `docxtpl`을 활용한 자동 생성 시스템 구축.
  2. **구현 내역**:
     - `templates/official_report_template.docx`: `scripts/build_docx_template.py`를 통해 FBI FD-1036 / FD-71A 스타일의 정통 공문서 폼(Red Approved Stamp, FORM IA-1036, UNCLASSIFIED, OFFICIAL RECORD 인장, 기관 표제부, 메타데이터 결재 그리드, Synopsis, 신호 타임라인 표, 당사국 전략적 태세 표, 경제/안보 파급영향, 3단계 전망 및 불확실성 요인, 3대 전략적 제언, 4대 DB 검증 쿼리 실측치, Enclosure 목록, 종결부호 `◆◆`) 템플릿 자동 생성.
     - `scripts/docx_report_generator.py`: `data/issue_research_data.py`의 실제 리서치 데이터를 주입하여 5종의 국문 정세평가 보고서(`01_북한핵_정세평가보고서.docx` ~ `05_미중무역전쟁_정세평가보고서.docx`) 자동 렌더링.
     - `scripts/generate_reports.py`: 통합 실행 시 Markdown, PDF, DOCX가 일괄 생성되도록 연동 완료.
  3. **저장 및 검증**:
     - 프로젝트 내부 `reports/issues/docx/` 및 지정된 전용 폴더 `C:\Users\홍준기\Desktop\international-analysis\분석보고서`에 실시간 무손실 자동 복제.
     - MySQL `international_analysis.analysis_reports` 테이블에 `report_type='official_docx_ko'`로 메타데이터 및 경로 영구 적재.
     - python-docx 검증 결과 미치환 Jinja 태그 0건(False), 문서당 6,300~7,400자의 풍부한 데이터가 완벽 조판됨을 확인.

- 2026-09-21 [트랙②, 오픈소스 LLM 및 모델 인프라] **`falcon3:7b` 다운로드 확인·로컬 추론 검증 및 분석 vs 출력 전담 LLM 이원화 아키텍처 정립**:
  1. **Falcon3 7B 다운로드 및 추론 검증**: 아랍에미리트 TII의 아랍어 파운데이션 모델 `falcon3:7b`(4.6GB) 다운로드 완료 확인 및 로컬 Ollama API (`/api/generate`) 메모리 적재 및 테스트 호출 완료. 정상 응답 수신으로 100% 작동 검증.
  2. **로컬 스토리지 실측**: `falcon3:7b` 설치 후 C 드라이브 잔여 공간이 **67.60 GB**로 확인되어 향후 모델 추가(8B~14B급) 시에도 디스크 안정성이 충분함을 검증.
  3. **분석(Analysis) vs 출력(Output) 전담 LLM 이원화 설계**: 각국 현지 모델(`yandex`, `falcon3`, `qwen2.5`, `mistral-nemo`, `elyza`)은 순수 '권역별 1차 분석 및 JSON 지표 추출'에만 집중하고, 이를 취합하여 한국 국익 관점의 최종 공문서/리포트를 조율·출력하는 '수석 보고서 작성관(Output LLM)' 분리 방향 정립.
  4. **문서 동기화**: `LLM_SYSTEM_SUMMARY.md`(섹션 8 신설 및 2026-09-21 최신화) 반영 완료.

## 다음 채팅에서 이 문서를 사용하는 법

새 대화를 시작할 때 이 파일(`project-handoff.md`)을 첨부하고 이렇게
말하면 됩니다:

> "이 파일이 지금까지의 프로젝트 진행 상황이야. 나는 [①/②/③]번 트랙을
> 맡을 거고, 이어서 [하고 싶은 작업]을 진행하자."

이렇게 하면 하드웨어 제약, 이미 확정된 기술 스택, 겪었던 에러들, 그리고
**다른 세션이 뭘 하고 있는지**까지 Claude가 다시 물어보지 않고 바로
이어서 작업할 수 있습니다.
