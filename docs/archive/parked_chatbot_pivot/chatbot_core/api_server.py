"""api_server.py — 챗봇 REST API (FastAPI)

챗봇_구현_세부_계획.md 3.4절 설계 구현. MySQL 연결은 선택적 — 환경변수
CHATBOT_MYSQL_DSN이 없으면 DataRetriever가 CSV 전용으로 동작한다(로컬에서
DB 세팅 전에도 바로 켜볼 수 있게 하려는 의도).

실행법 (로컬, Ollama 켜둔 상태):
    cd international-analysis
    pip install fastapi uvicorn
    python -m uvicorn chatbot_core.api_server:app --reload --port 8000

    브라우저: http://localhost:8000/docs (자동 생성 API 문서)
              frontend/index.html 파일을 직접 열어서 사용 (파일:// 로 열어도 됨,
              CORS를 전체 허용해뒀음)

이 클라우드 세션에서: Ollama가 없어서 모든 응답이 mode="template_fallback"으로
나온다 — 이는 정상이다(response_generator.py 상단 주석 참고). 서버 자체와
검색/의도분류 로직은 이 상태로도 전부 검증 가능하다.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .data_retriever import DataRetriever
from .intent_classifier import classify_intent
from .issues import ISSUES, issue_name_ko
from .response_generator import generate_response

app = FastAPI(
    title="국제정세 분석 챗봇 API",
    description="다국어 로컬 LLM 기반, 데이터 근거 명시형 국제정세 Q&A 서비스 (프로토타입)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _make_mysql_connection():
    """CHATBOT_MYSQL_DSN 환경변수가 있을 때만 연결 시도. 없거나 실패하면
    None을 반환 — DataRetriever가 자동으로 CSV 전용 모드로 동작한다."""
    dsn = os.getenv("CHATBOT_MYSQL_DSN")
    if not dsn:
        return None
    try:
        import mysql.connector  # 로컬에만 설치되어 있을 수 있음 — 선택적 의존성

        return mysql.connector.connect(
            host=os.getenv("CHATBOT_MYSQL_HOST", "localhost"),
            user=os.getenv("CHATBOT_MYSQL_USER"),
            password=os.getenv("CHATBOT_MYSQL_PASSWORD"),
            database=os.getenv("CHATBOT_MYSQL_DB"),
        )
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ MySQL 연결 실패({e}) — CSV 전용 모드로 계속합니다.")
        return None


retriever = DataRetriever(mysql_connection=_make_mysql_connection())

# 세션별 대화 히스토리 — 프로토타입 단계라 인메모리. 서버 재시작하면 날아간다.
# Phase 2에서 data/sessions/{session_id}.json 영속화로 옮길 예정
# (챗봇_구현_세부_계획.md 5.1절 폴더 구조 참고).
_SESSION_HISTORY: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: str = "ko"


class ChatResponsePayload(BaseModel):
    response: str
    mode: str
    intent: str
    issue_id: Optional[str]
    issue_name: Optional[str]
    tone_distribution: str
    sources: list[str]
    warnings: list[str]
    factcheck_notes: list[str]
    session_id: str


@app.get("/")
def root():
    return {
        "service": "국제정세 분석 챗봇",
        "status": "ok",
        "issues_tracked": len(ISSUES),
        "docs": "/docs",
    }


@app.get("/issues")
def list_issues():
    """21개(+횡단 1개) 이슈 목록 — 프론트엔드에서 예시 질문 제안 등에 사용."""
    return [
        {"issue_id": iid, "name_ko": info["name_ko"], "continent": info["continent"]}
        for iid, info in ISSUES.items()
    ]


@app.post("/chat", response_model=ChatResponsePayload)
def chat_endpoint(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    intent_result = classify_intent(req.message)
    top_issue = intent_result.issue_ids[0] if intent_result.issue_ids else None

    ctx = retriever.get_context(top_issue)
    chat_resp = generate_response(req.message, ctx, language=req.language)

    # 히스토리 기록 (세션당 최근 50개로 제한 — 무한 증식 방지)
    history = _SESSION_HISTORY.setdefault(session_id, [])
    history.append({
        "at": datetime.now(timezone.utc).isoformat(),
        "message": req.message,
        "response": chat_resp.text,
        "intent": intent_result.intent,
        "issue_id": top_issue,
    })
    if len(history) > 50:
        del history[:-50]

    return ChatResponsePayload(
        response=chat_resp.text,
        mode=chat_resp.mode,
        intent=intent_result.intent,
        issue_id=top_issue,
        issue_name=issue_name_ko(top_issue) if top_issue else None,
        tone_distribution=chat_resp.tone_distribution_display,
        sources=chat_resp.sources,
        warnings=chat_resp.warnings,
        factcheck_notes=chat_resp.factcheck_notes,
        session_id=session_id,
    )


@app.get("/history/{session_id}")
def get_history(session_id: str):
    return _SESSION_HISTORY.get(session_id, [])
