# 프로젝트 현황 요약 (다른 대화방 전달용)

> 이 문서는 새로운 대화(채팅)에서 Claude가 프로젝트 맥락을 빠르게
> 파악할 수 있도록 작성된 인수인계 문서입니다. 새 채팅을 시작할 때
> 이 파일을 함께 첨부하면 처음부터 다시 설명할 필요가 없습니다.

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
```

## 지금까지 확정된 기술 스택

### LLM 실행 방식
- ❌ `transformers` + `bitsandbytes` 4bit 양자화 → **실패** (GPU/CUDA 전용 기술이라 CPU 환경에서 불가능, `ValueError: Some modules are dispatched on the CPU...` 에러 확인함)
- ✅ **Ollama** (GGUF + llama.cpp 기반) → CPU 환경에 적합, 채택 완료

### 언어별 특화 모델 라우팅 (6개 언어)

다국어 만능 모델(Qwen2.5 단독 사용 등)은 소형 양자화 시 언어가 뒤섞이는
현상(한국어+영어+한자+일본어 조사가 한 문장에 섞임)을 실제로 확인했음.
이 때문에 **언어별로 검증된 특화 모델을 따로 두고 라우팅하는 구조**로
최종 결정함.

| 지역/언어 | 모델 | Ollama pull 명령어 | 크기(4bit) | 상태 |
|-----------|------|---------------------|-----------|------|
| 🇺🇸 영어 | Mistral-7B-Instruct | `ollama pull mistral` | ~4GB | 테스트 완료 |
| 🇰🇷 한국어 | SOLAR-10.7B-Instruct | Modelfile로 직접 등록 (`solar-korean`) | ~6GB | 등록/테스트 완료 |
| 🇨🇳 중국어 | Qwen2.5-7B-Instruct | `ollama pull qwen2.5:7b` | ~4.5GB | 테스트 완료 (순한국어 출력 확인) |
| 🇯🇵 일본어 | ELYZA-Llama3-JP-8B | `ollama pull dsasai/llama3-elyza-jp-8b` | ~4.9GB | 모델 확인만, 실행 테스트 예정 |
| 🇷🇺 러시아어 | Saiga-Mistral-7B | `ollama pull cyberlis/saiga-mistral:7b-lora-q4_K` | ~4.4GB | 모델 확인만, 실행 테스트 예정 |
| 🇸🇦 아랍어 | Jais-Adaptive-7B (Core42/G42) | `ollama pull jwnder/jais-adaptive:7b` | ~4.5GB | 모델 확인만, 실행 테스트 예정 |

**메모리 전략:** 6개 모델을 모두 디스크에 받아두되(총 ~28GB), Ollama가
요청 시점에만 순차적으로 메모리에 로드하고 유휴 시 자동 언로드하는
특성을 활용 → 16GB RAM으로도 6개 언어 지원 가능.

## 지금까지 실제로 겪은 문제 & 해결 (원인 포함)

1. **SOLAR 다운로드 중 Ctrl+C로 중단** → `huggingface_hub`의
   `resume_download=True`로 이어받기 성공
2. **`load_in_4bit=True` 직접 전달 시 에러** (`TypeError: LlamaForCausalLM.__init__() got an unexpected keyword argument 'load_in_4bit'`) → `BitsAndBytesConfig` 객체로 감싸서 전달해야 함 (transformers 최신 버전 변경사항)
3. **`BitsAndBytesConfig`로도 결국 실패** → GPU 없는 환경이라 bitsandbytes 자체가 작동 불가 → **Ollama로 완전히 전환**
4. **Qwen2.5에게 혼합 언어 프롬프트 입력 시 언어 뒤섞임 출력** → 프롬프트를 단일 언어로 통일 + temperature 0.7→0.3으로 낮춰서 해결
5. **Python에서 `qwen2.5:7b` 호출 시 404 에러** (`model not found`) → `ollama pull qwen2.5:7b`로 사전 다운로드 안 하고 바로 호출해서 발생, pull 먼저 실행 후 해결

## GitHub 저장소 구조 (이미 다른 채팅에서 구성 완료)

```
international-analysis/
├── README.md                          # 프로젝트 개요/아키텍처/실행법
├── docs/
│   └── constraints-and-solutions.md   # 위 "문제&해결" 상세 버전
├── src/
│   └── model_router.py                # 언어별 모델 라우팅 함수 (ask_model, translate_and_summarize)
├── requirements.txt                   # requests, pandas, huggingface_hub
├── .gitignore                         # *.gguf, *.safetensors 등 대용량 파일 제외
├── reports/                           # (비어있음, 추후 리포트 저장용)
└── data/                              # (비어있음, 추후 수집 데이터 저장용)
```

**GitHub 업로드 절차 (이미 안내함):**
```bash
cd international-analysis
git init
git add .
git commit -m "Initial commit: 국제정세 분석 시스템 아키텍처 및 문서화"
git branch -M main
git remote add origin https://github.com/[아이디]/international-analysis.git
git push -u origin main
```

## 참고 중인 프로젝트 원본 문서 (Claude 프로젝트 파일로 업로드되어 있음)

- `claude_국제정세_분석_기획서` — 전체 프로젝트 기획서 (분석 목표, KPI, 일정 등)
- `claude_패권국_공식_정부_데이터_API_조사.md` — 미/중/러/EU/일/인도 정부 API 조사
- `claude_대륙별_이슈_분석_프레임워크.md` — 18개 국제이슈 목록 (중동 3개 포함)
- `claude_GDELT_API_완전재작성_가이드` — GDELT 뉴스 데이터 수집 스크립트 재작성 기록

## 아직 안 한 것 (다음 대화에서 이어갈 작업)

- [ ] 일본어/러시아어/아랍어 모델 실제 pull 및 응답 테스트
- [ ] `src/news_pipeline.py` 작성 — 실제 뉴스 배치 수집→분석→리포트 파이프라인
- [ ] `src/report_generator.py` — 마크다운 리포트 자동 생성
- [ ] GDELT API 연동 (기존 가이드 문서 참고)
- [ ] 정부 공식 API(BEA, Eurostat, e-Stat 등) 자동 수집
- [ ] 실제 GitHub 저장소에 push 완료 여부 확인
- [ ] 주간/월간 리포트 자동 발행 스케줄링

## 다음 채팅에서 이 문서를 사용하는 법

새 대화를 시작할 때 이 파일(`project-handoff.md`)을 첨부하고 이렇게
말하면 됩니다:

> "이 파일이 지금까지의 프로젝트 진행 상황이야. 이어서 [하고 싶은 작업]을 진행하자."

이렇게 하면 하드웨어 제약, 이미 확정된 기술 스택, 겪었던 에러들을
Claude가 다시 물어보지 않고 바로 이어서 작업할 수 있습니다.
