# 국제정세 분석 챗봇 — 인수인계 README (Phase 1, v2)

**이 문서의 목적**: 이 프로젝트를 처음 보는 새 세션(다른 AI 코딩 세션이든, 준기님
본인이든)이 배경 설명 없이 바로 이어서 작업할 수 있게 하는 것. 왜 이렇게
설계했는지, 뭘 검증했고 뭘 안 했는지, 로컬에서 실제로 부딪혔던 문제와 그
해결법까지 전부 여기 있다.

---

## 1. 이게 뭔가 — 한 문단 요약

기존 국제정세 분석 프로젝트(21개+1 이슈 추적, 다국어 로컬 LLM 톤 분류, RSS/Reddit
수집, 팩트체크 검증)의 최종 산출물을 PDF 보고서·HTML 대시보드 대신 **대화형
챗봇**으로 바꾸기로 했다. 이유: 정적 산출물은 "읽기만 가능"하고 차별성이
없지만, 챗봇은 (1) 기존 7언어 LLM 라우팅 인프라를 그대로 재사용하고, (2)
할루시네이션 없는 데이터 기반 Q&A라는 명확한 기술적 기여가 있고, (3) 포트폴리오/
졸업 산출물로서 "쓸 수 있는 서비스"라는 임팩트가 있다. 배경 논의는 프로젝트
문서함(claude.ai Project "국제정세 분석")의 `챗봇_서비스_전환_전략.md`,
`챗봇_구현_세부_계획.md` 참고.

**핵심 설계 원칙**: 새 LLM 파이프라인을 만드는 게 아니라, `scripts/` 폴더의
기존 검증된 파이프라인(팩트체크, 톤 분류, Reddit 수집) 위에 대화형 껍데기를
얹는다. `chatbot_core/`의 코드는 `scripts/`를 고치지 않고 import만 한다.

---

## 2. 현재 상태 (2026-09-20 기준)

**Phase 1 MVP 코드는 전부 작성 완료, v2까지 나감.** 클라우드 세션에서
직접 실행해 API 서버 기동과 `/chat` 엔드포인트 응답까지 확인했다. 로컬(준기님
PC, Windows + Python 3.9 + Ollama)에서는 서버 기동까지는 확인했고, **실제
Ollama LLM 응답 품질은 아직 확인 전**이다 (마지막으로 확인된 상태: uvicorn이
에러 없이 뜨는 것까지 — 브라우저에서 실제 채팅 테스트 결과는 이 문서 작성
시점까지 전달받지 못함).

### 완료된 것
- [x] 21개(+횡단 경제 1개 = 22개) 이슈 정의 (`issues.py`)
- [x] 규칙 기반 의도 분류 + 이슈 태그 추출 (`intent_classifier.py`)
- [x] CSV 기반 데이터 검색, MySQL은 선택적 (`data_retriever.py`)
- [x] Ollama 연동 + 팩트체크 필터 + 템플릿 폴백 (`response_generator.py`)
- [x] FastAPI 서버, 4개 엔드포인트 (`api_server.py`)
- [x] 채팅 UI (`frontend/index.html`)
- [x] Python 3.9 호환성 수정 (v2 — 아래 "겪었던 문제" 참고)

### 아직 검증 안 된 것 (다음 세션이 이어받을 부분)
- [ ] 로컬에서 실제 Ollama 응답 품질/톤 — 이게 지금 가장 중요한 다음 스텝
- [ ] MySQL 연동 (`data_retriever.py`의 `_fill_from_mysql`은 스키마를 "가정"만
      하고 작성됨, 실 컬럼명 대조 안 함 — 안 맞아도 CSV로 자동 폴백되니 서비스가
      죽지는 않지만, MySQL 쪽 데이터를 실제로 쓰려면 대조 필요)
- [ ] 데이터 볼륨 — 현재 `data/auto_benchmark_results.csv`가 4건, Reddit이
      2건뿐이라 대부분 이슈 질문에 "데이터 없음" 경고가 뜸. 코드 문제 아님,
      `scripts/run_pipeline.py` + `auto_benchmark_verifier.py --limit 20+`
      더 돌려야 함

---

## 3. 파일 구조

```
international-analysis/
├── scripts/                        (기존, 안 건드림)
│   ├── verify_model_consensus.py   ← OLLAMA_HOST, CONSENSUS_MODELS만 재사용
│   ├── verify_factcheck_api.py     ← search_google_factcheck() 재사용 (오프라인 캐시 폴백 내장)
│   ├── auto_benchmark_verifier.py
│   ├── fetch_reddit_opinion.py
│   └── run_pipeline.py
├── data/                           (기존, 안 건드림)
│   ├── auto_benchmark_results.csv  ← data_retriever.py가 읽음
│   └── reddit_signals/
│       ├── reddit_opinion_latest.csv
│       └── reddit_opinion_summary.json
├── chatbot_core/                   (NEW — 이번에 추가된 것 전부 여기)
│   ├── issues.py                   21개+1 이슈 정의 (단일 진실 공급원)
│   ├── intent_classifier.py        의도 분류 + 이슈 태그 추출
│   ├── data_retriever.py           CSV/MySQL에서 이슈별 컨텍스트 검색
│   ├── response_generator.py       LLM 호출(or 템플릿 폴백) + 팩트체크
│   ├── api_server.py               FastAPI (/,  /issues,  /chat,  /history/{id})
│   └── requirements.txt
└── frontend/
    └── index.html                  채팅 UI (API_URL=http://localhost:8000 하드코딩)
```

각 파일 상단에 왜 이렇게 짰는지 설계 이유가 주석으로 달려있다 — 특히
`response_generator.py` 상단은 꼭 읽을 것 (Ollama 재사용 관련 함정 설명).

---

## 4. 로컬 실행 환경 — 준기님 PC 특이사항

- **OS**: Windows, PowerShell 사용
- **Python**: `C:\2024316047\python_3.9\python.exe` — **Python 3.9**, PATH에 잡힌
  기본 `python`이 이 경로를 가리킴. pip 설치할 때 꼭 `python -m pip install ...`로
  (그냥 `pip install`이 다른 python을 쓸 수도 있음)
- **폴더 위치**: `C:\Users\홍준기\Desktop\international-analysis`
- **Ollama**: 로컬에 설치되어 있고 6개 언어 모델 스택 검증됨(ADR-001 참고).
  `ollama serve`로 켜야 하거나, 이미 백그라운드 서비스로 떠 있으면
  `ollama list`로 확인 가능

---

## 5. 실행 방법 (PowerShell)

```powershell
cd "C:\Users\홍준기\Desktop\international-analysis"
python -m pip install -r chatbot_core/requirements.txt
```

Ollama용 창 (안 켜져 있으면):
```powershell
ollama serve
```

API 서버용 창 (새 창에서):
```powershell
cd "C:\Users\홍준기\Desktop\international-analysis"
python -m uvicorn chatbot_core.api_server:app --reload --port 8000
```

`Uvicorn running on http://127.0.0.1:8000`이 에러 없이 뜨면 성공. 그다음
`frontend\index.html`을 브라우저로 열면 됨 (CORS 전체 허용해둬서 `file://`로
열어도 대부분 되지만, 안 되면 아래 6번 "겪었던 문제" 참고).

---

## 6. 겪었던 문제 & 해결법 (다음 세션이 똑같이 삽질 안 하도록)

### 6.1 `&`로 백그라운드 실행 안 됨 (PowerShell)
Windows PowerShell은 `명령어 &`가 유닉스 셸처럼 백그라운드 실행을 의미하지
않는다 (`&`는 다른 예약 연산자). **해결**: 프로세스마다 새 PowerShell 창을
따로 열어서 실행 (Ollama용 창 1개, uvicorn용 창 1개).

### 6.2 zip 압축 풀 때 폴더가 한 겹 더 생김
Windows 탐색기의 "압축 풀기"는 zip 파일명과 같은 이름의 새 폴더를 만들고 그
안에 내용을 푸는 경우가 있다. 그러면 `chatbot_core/`가
`international-analysis\chatbot_core\`가 아니라
`international-analysis\chatbot_prototype\chatbot_core\`처럼 한 단계 더
들어가버려서, `scripts/`, `data/`와 같은 레벨에 있어야 하는 상대 경로 import가
깨진다. **해결**: PowerShell에서 `Expand-Archive -DestinationPath`를
`international-analysis` 폴더 자체로 명시해서 풀기.

### 6.3 Python 3.9에서 `str | None` 문법 크래시 (v1 → v2에서 수정)
`api_server.py`와 `data_retriever.py`에서 pydantic 모델/함수 시그니처에
`str | None` (PEP 604, Python 3.10+ 문법)을 썼는데, `from __future__ import
annotations`가 있어도 pydantic이 런타임에 `typing.get_type_hints()`로 실제
타입을 resolve하려는 순간 Python 3.9는 `type.__or__`를 지원하지 않아서
`TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`로 터진다.

**해결**: `str | None` → `typing.Optional[str]`로 전부 교체 (v2에서 이미 반영됨).
**만약 이 에러를 또 보면**: `chatbot_core/` 안에서 ` | None`, ` | str`, ` | int`
패턴을 grep해서 남은 게 있는지 확인 — dataclass 필드(`intent_classifier.py`의
`IntentResult`, `response_generator.py`의 `ChatResponse`)는 지금까지는 pydantic처럼
강제로 타입을 resolve하지 않아서 문제 없었지만, 만약 나중에 이 dataclass들을
pydantic 모델로 바꾸거나 `dataclasses.fields()` 등으로 타입을 조회하는 코드를
추가하면 같은 문제가 재발할 수 있다.

`list[dict]`, `dict[str, int]` 같은 PEP 585 빌트인 제네릭(대괄호 문법)은
Python 3.9부터 정식 지원이라 문제없음 — 헷갈리지 말 것. 문제는 오직
`X | Y` 유니온 문법(PEP 604, 3.10+)이다.

### 6.4 `Failed to fetch` (프론트엔드에서)
uvicorn이 아예 안 켜져 있거나(6.3 에러로 죽었거나), `file://`로 연 HTML을
브라우저가 로컬 파일 → localhost 요청을 보안상 막는 경우. **진단 순서**:
1. uvicorn 창에 에러 없이 떠 있는지 확인
2. 브라우저 주소창에 직접 `http://localhost:8000/` 쳐서 JSON 응답 오는지 확인 (서버 자체 문제인지 분리)
3. 그래도 `file://`에서만 막히면, `frontend` 폴더에서 `python -m http.server 5500` 띄우고 `http://localhost:5500`으로 접속

---

## 7. 다음에 할 일 (우선순위 순)

1. **로컬에서 실제 채팅 테스트** — 브라우저로 `frontend/index.html` 열고
   예시 질문 눌러서 `mode: "llm"`으로 실제 Ollama 응답이 나오는지 확인.
   `mode: "template_fallback"`이면 Ollama 연결이 아직 안 된 것.
2. 실제 LLM 응답을 보고 `response_generator.py`의 `SYSTEM_PROMPT_TEMPLATE`
   튜닝 (톤이 너무 딱딱하다든가, 데이터를 제대로 안 쓴다든가 하는 문제 확인)
3. 데이터 볼륨 확보: `python scripts/run_pipeline.py`, 
   `python scripts/auto_benchmark_verifier.py --limit 20 --with-factcheck` 실행
4. `data_retriever.py`의 `_fill_from_mysql()`을 실제 MySQL 스키마
   (`DATABASE_SETUP.md` 참고)와 대조 — 컬럼명 다르면 이 메서드만 고치면 됨
5. 의도 분류 정확도 개선 — 지금은 순수 규칙 기반이라 "이란이랑 사우디랑 요즘
   어때?"처럼 이슈가 명시 안 된 복합 질문은 약함. 필요하면 LLM 기반으로 업그레이드
6. 세션 히스토리 영속화 — 지금은 서버 재시작하면 대화 기록이 날아감
   (인메모리 dict, `api_server.py`의 `_SESSION_HISTORY`)

---

## 8. 참고 — 프로젝트 문서함 (claude.ai Project "국제정세 분석")

- `챗봇_서비스_전환_전략.md` — 왜 챗봇인가, 기존 세 정의(정기 출판/포트폴리오/
  이슈 프레임워크) 충돌을 챗봇이 어떻게 통합하는지, 교수님 피드백 대비 논리
- `챗봇_구현_세부_계획.md` — 아키텍처 설계 원본 + 이번 구현에서 실제로
  발견된 버그/설계 수정 사항 기록 (진행 상황 섹션에 계속 업데이트됨)
- `ADR-001_LLM_역할정의_및_감성분석_휴먼인더루프.md` — 챗봇 프롬프트에 이식한
  "비판적" 라벨의 narrative 기준 정의 출처, 6개 언어 모델 스택 검증 기록
- `대륙별_이슈_분석_프레임워크.md` — 21개 이슈 원본 정의 (`issues.py`가 이걸 코드화한 것)
