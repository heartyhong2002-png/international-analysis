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
| **② 오픈소스 LLM 담당** | ❌ 로컬 아님 | 다국어(6개 언어) 로컬 LLM 라우팅, Ollama 모델 선정/테스트 | `src/model_router.py`, `src/news_pipeline.py`(예정), `src/report_generator.py`(예정), 언어별 Modelfile |
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
  - `src/model_router.py` + `src/news_pipeline.py` (②번 세션 담당, 아직
    미완성) — 6개 언어별로 다른 로컬 LLM을 라우팅해서 다국어 분석/요약을
    하려는 목적.
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

| 지역/언어 | 모델 | Ollama pull 명령어 | 크기(4bit) | 상태 |
|-----------|------|---------------------|-----------|------|
| 🇺🇸 영어 | Mistral-7B-Instruct | `ollama pull mistral` | ~4GB | 테스트 완료 |
| 🇰🇷 한국어 | SOLAR-10.7B-Instruct | Modelfile로 직접 등록 (`solar-korean`) | ~6GB | 등록/테스트 완료 (단, uncensored 버전은 한국어 질문에도 영어로만 답하는 문제 확인 — SOLAR 자체가 language:en 명시된 영어 전용 모델이었음) |
| 🇨🇳 중국어 | Qwen2.5-7B-Instruct | `ollama pull qwen2.5:7b` | ~4.5GB | 테스트 완료 (한국어 응답도 자연스럽게 나와서 `analyze_signals.py`의 기본 모델로도 채택됨) |
| 🇯🇵 일본어 | ELYZA-Llama3-JP-8B | `ollama pull dsasai/llama3-elyza-jp-8b` | ~4.9GB | 모델 확인만, 실행 테스트 예정 |
| 🇷🇺 러시아어 | Saiga-Mistral-7B | `ollama pull cyberlis/saiga-mistral:7b-lora-q4_K` | ~4.4GB | 모델 확인만, 실행 테스트 예정 |
| 🇸🇦 아랍어 | Jais-Adaptive-7B (Core42/G42) | `ollama pull jwnder/jais-adaptive:7b` | ~4.5GB | 모델 확인만, 실행 테스트 예정 |

**메모리 전략:** 6개 모델을 모두 디스크에 받아두되(총 ~28GB), Ollama가
요청 시점에만 순차적으로 메모리에 로드하고 유휴 시 자동 언로드하는
특성을 활용 → 16GB RAM으로도 6개 언어 지원 가능.

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
├── README.md                          # 프로젝트 개요/아키텍처/실행법
├── scripts/                           # 실제 작동하는 수집/DB 파이프라인 (③, ① 세션)
├── src/                                # 다국어 LLM 라우팅 (②번 세션, 아직 진행 중)
│   └── model_router.py
├── data/                               # 수집 데이터 (scripts/data/ 가 실제 경로 — 혼동 주의)
├── reports/                             # 분석 리포트
├── output/                              # 대시보드 등 산출물
└── requirements.txt
```

**⚠️ 참고:** `data/`가 프로젝트 루트와 `scripts/data/` 두 군데 있을 수
있는데, **파이프라인이 실제로 쓰는 건 `scripts/data/`쪽**입니다(스크립트
파일 위치 기준으로 고정되어 있음). 루트의 `data/`는 예전 흔적일 수 있으니
헷갈리면 `scripts/data/`를 기준으로 보세요.

## 참고 중인 프로젝트 원본 문서 (Claude 프로젝트 파일로 업로드되어 있음)

- `claude_국제정세_분석_기획서` — 전체 프로젝트 기획서 (분석 목표, KPI, 일정 등)
- `claude_패권국_공식_정부_데이터_API_조사.md` — 미/중/러/EU/일/인도 정부 API 조사
- `claude_대륙별_이슈_분석_프레임워크.md` — 18개 국제이슈 목록 (중동 3개 포함)
- `claude_GDELT_API_완전재작성_가이드` — GDELT 뉴스 데이터 수집 스크립트 재작성 기록

## 아직 안 한 것 (2026-09-08 기준 최신)

- [ ] (②) 일본어/러시아어/아랍어 모델 실제 pull 및 응답 테스트
- [ ] (②) `src/news_pipeline.py`, `src/report_generator.py` 작성
- [ ] (②/③ 조율 필요) `analyze_signals.py`와 `model_router.py` 분석 파이프라인을
      합칠지 따로 둘지 결정
- [x] ~~GDELT API 연동~~ → 네트워크 자체가 막혀서 GDELT는 보류, 대신
      Wikipedia Pageviews + 정부 RSS로 신호 확보 (③ 완료)
- [x] ~~정부 공식 API 자동 수집~~ → 한국 외교부/미 국무부/IRNA/Al Jazeera RSS
      연동 완료 (③ 완료)
- [ ] (③) 파이프라인 스케줄링 자동화 (Windows Task Scheduler로 정기 실행)
- [ ] (③) `analyze_signals.py`를 `run_pipeline.py`에 연결
- [ ] (③) 대시보드/리포트 자동 생성 — 기존 `generate_dashboard.py`는 하드코딩된
      가짜 데이터만 그리는 죽은 코드라 삭제함, 실제 DB 연동으로 새로 설계 필요
- [ ] 실제 GitHub 저장소에 push 완료 여부 확인
- [ ] 주간/월간 리포트 자동 발행 스케줄링

## 작업 로그 (새 작업 시작 전 여기에 한 줄 남기기)

형식: `- YYYY-MM-DD HH:MM [트랙①/②/③] 무엇을 시작함`

- 2026-09-08 [트랙③] `monthly_update.py`(고장난 예전 오케스트레이터), `generate_dashboard.py`(하드코딩 가짜 데이터) 삭제. 이 조율 문서(`project-handoff.md`) 신규 작성 — 3개 세션 분업 현황 정리.
- 2026-09-08 [트랙③, 컨트롤타워 역할로 재정의됨] 자동화(수집→분석→결과물) 아이디어를 프로토타입으로 구현: `generate_dashboard_v2.py`(실제 DB 연동, 테스트 DB로 검증 완료), `run_pipeline_scheduled.bat`(Windows 작업 스케줄러용, 로컬 검증 필요), `analyze_signals.py` 파이프라인 연결 제안(코드만 제안, 미적용). 자세한 내용은 `AUTOMATION_PROTOTYPE_HANDOFF.md` 참고.

## 다음 채팅에서 이 문서를 사용하는 법

새 대화를 시작할 때 이 파일(`project-handoff.md`)을 첨부하고 이렇게
말하면 됩니다:

> "이 파일이 지금까지의 프로젝트 진행 상황이야. 나는 [①/②/③]번 트랙을
> 맡을 거고, 이어서 [하고 싶은 작업]을 진행하자."

이렇게 하면 하드웨어 제약, 이미 확정된 기술 스택, 겪었던 에러들, 그리고
**다른 세션이 뭘 하고 있는지**까지 Claude가 다시 물어보지 않고 바로
이어서 작업할 수 있습니다.
