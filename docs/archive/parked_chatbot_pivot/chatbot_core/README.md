# 국제정세 분석 챗봇 — 프로토타입 (Phase 1 MVP)

`챗봇_서비스_전환_전략.md` / `챗봇_구현_세부_계획.md`(프로젝트 문서함)에서 설계한
Phase 1 컴포넌트를 실제 코드로 구현한 것. 기존 `scripts/` 파이프라인(팩트체크,
3모델 합의, Reddit 수집)은 그대로 두고, 그 위에 대화형 인터페이스를 얹었다.

## 구성

```
chatbot_core/
├── issues.py              21개(+횡단 1개) 이슈 정의 — 모든 컴포넌트의 단일 진실 공급원
├── intent_classifier.py   규칙 기반 의도 분류 + 이슈 태그 추출
├── data_retriever.py      CSV(+선택적 MySQL)에서 이슈별 데이터 검색
├── response_generator.py  Ollama LLM 호출 + 팩트체크 필터 + 템플릿 폴백
├── api_server.py          FastAPI 서버 (/chat, /issues, /history)
└── requirements.txt

frontend/
└── index.html              채팅 UI (API_URL만 맞추면 바로 사용 가능)
```

## 로컬(Galaxy Book5 Pro, Ollama 설치된 환경)에서 실행하기

```bash
cd international-analysis
pip install -r chatbot_core/requirements.txt

# Ollama가 이미 떠 있어야 진짜 LLM 응답이 나옴 (없으면 자동으로 템플릿 폴백)
ollama serve &

python -m uvicorn chatbot_core.api_server:app --reload --port 8000
```

그다음 `frontend/index.html`을 브라우저로 그냥 열면 된다 (파일 직접 열기, 별도
웹서버 불필요 — API_URL이 CORS 전체 허용된 `http://localhost:8000`을 가리킴).

API 문서는 `http://localhost:8000/docs`에서 자동 생성된 Swagger UI로 확인 가능.

## 이 프로토타입이 실제로 검증한 것 / 아직 안 된 것

**검증됨 (이 세션, 클라우드 샌드박스에서 실행 확인):**
- 의도 분류 6개 테스트 쿼리 전부 정확히 1개 이슈로 특정 (키워드 계층화로 "핵", "무역" 같은 범용어 오탐 제거)
- 데이터 검색기가 `data/auto_benchmark_results.csv` + `data/reddit_signals/*`를 실제로 읽어서 이슈별 컨텍스트 구성
- FastAPI 서버 기동 + `/`, `/issues`, `/chat` 엔드포인트 실제 HTTP 호출로 응답 확인
- Ollama 미연결 시 조용히 죽지 않고 템플릿 폴백으로 전환 (할루시네이션 없는 안전한 실패)

**아직 검증 안 됨 (로컬 환경 필요):**
- 실제 Ollama 응답 품질 (이 샌드박스엔 Ollama가 없음 — `response_generator.py` 상단 주석 참고)
- MySQL 경로 (`data_retriever.py`의 `_fill_from_mysql`은 DATABASE_SETUP.md 기준 스키마를 "가정"만 하고 작성함 — 실 컬럼명 대조 필요)
- 현재 `auto_benchmark_results.csv`가 4건뿐이라 대부분 이슈에서 기사 데이터가 비어있음 (Reddit 데이터도 1건). `scripts/run_pipeline.py` 정기 실행으로 데이터가 쌓이면 답변 품질이 올라감

## 다음 단계 (Phase 2)

1. 데이터 볼륨 확보 — `run_pipeline.py` + `auto_benchmark_verifier.py --limit 20` 정기 실행
2. 로컬에서 실제 Ollama 응답 톤/품질 확인 → 프롬프트(`response_generator.py`의 `SYSTEM_PROMPT_TEMPLATE`) 튜닝
3. `data_retriever.py`의 MySQL 경로를 실제 스키마와 대조 후 확정
4. 의도 분류 정확도가 부족한 복합 질문(이슈 미언급형) 샘플 수집 → LLM 기반 분류로 업그레이드 검토
5. 세션 히스토리 영속화 (`data/sessions/{session_id}.json`)
