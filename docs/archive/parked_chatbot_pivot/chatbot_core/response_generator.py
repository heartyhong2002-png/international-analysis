"""response_generator.py — 검색된 데이터로 LLM 응답 생성 + 팩트체크 필터

verify_model_consensus.py(Ollama 호출부)와 verify_factcheck_api.py(Google Fact
Check, 오프라인 캐시 폴백 내장)를 그대로 import해서 재사용한다 — 이 챗봇이
"새 LLM 파이프라인"이 아니라 "기존 검증된 파이프라인 위에 얹은 대화형 껍데기"라는
점이 핵심이다 (챗봇_서비스_전환_전략.md 5절).

⚠️ 이 파일을 지금 이 클라우드 세션에서 실행하면 Ollama 서버가 없어서
   call_ollama_json()이 항상 실패한다 — 이건 버그가 아니라 환경 차이다.
   준기님 로컬(Galaxy Book5 Pro, Ollama 켜진 상태)에서 실행해야 실제 LLM 응답이
   나온다. 그 전까지 이 파일은 TEMPLATE_FALLBACK 모드로 동작을 검증할 수 있게
   만들어뒀다 — Ollama 연결 실패 시 조용히 죽는 대신, 검색된 데이터를 그대로
   구조화해서 보여주는 템플릿 응답을 낸다(할루시네이션 없음, 그냥 LLM 문장력이
   빠진 버전).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from .data_retriever import RetrievedContext, format_tone_distribution  # noqa: E402
from .issues import issue_name_ko  # noqa: E402

try:
    # call_ollama_json()은 verify_model_consensus.py에서 톤 분류 전용으로 쓰인다
    # (format="json" 강제 + {"label", "evidence_quote"} 필드 파싱 하드코딩) — 챗봇의
    # 자유 텍스트 응답 생성과는 응답 형식이 안 맞아서 그대로 재사용할 수 없다.
    # 대신 OLLAMA_HOST/CONSENSUS_MODELS 같은 설정값만 가져오고, 호출부는 아래
    # _call_ollama_freeform()으로 별도 구현한다.
    from verify_model_consensus import OLLAMA_HOST, CONSENSUS_MODELS  # noqa: E402
    OLLAMA_IMPORT_OK = True
except Exception:
    OLLAMA_IMPORT_OK = False
    OLLAMA_HOST = "http://localhost:11434"
    CONSENSUS_MODELS = []

try:
    from verify_factcheck_api import search_google_factcheck  # noqa: E402
    FACTCHECK_IMPORT_OK = True
except Exception:
    FACTCHECK_IMPORT_OK = False


def _call_ollama_freeform(model: str, prompt: str, timeout: int = 180) -> str:
    """자유 텍스트 응답용 Ollama 호출. call_ollama_json과 달리 format="json"을
    강제하지 않는다 — 챗봇 답변은 자연어 문장이지 {label, evidence_quote} 구조가
    아니기 때문. 실패 시 예외를 던진다(호출부에서 템플릿 폴백으로 잡음)."""
    import requests

    res = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.3}},
        timeout=timeout,
    )
    if res.status_code != 200:
        raise RuntimeError(f"HTTP {res.status_code}")
    data = res.json()
    text = data.get("response", "").strip()
    if not text:
        raise RuntimeError("빈 응답")
    return text


# ADR-001에서 정의한 "비판적"의 narrative 기준 정의를 챗봇 프롬프트에도 그대로
# 이식한다 — 검수 단계에서 확립된 정의가 챗봇 응답에서 흔들리면 두 파이프라인의
# 톤 분류가 서로 다른 기준으로 갈라지는 문제가 생긴다.
SYSTEM_PROMPT_TEMPLATE = """당신은 국제정세 분석 AI 어시스턴트입니다.

핵심 규칙 (반드시 지킬 것):
1. 아래 [제공 데이터] 섹션에 없는 사실은 절대 지어내지 마시오. 데이터가 부족하면
   "현재 수집된 데이터로는 확인이 어렵습니다"라고 명시하시오.
2. 톤 분포가 있으면 반드시 인용하시오 (예: "비판적 60%, 중립적 40%").
3. "비판적"은 사건 내용이 부정적인지가 아니라, 기사가 narrative 차원에서 특정
   주체(정부·인물·국가)의 책임을 지적하는 표현을 쓰는지로 판단된 라벨입니다.
4. 기사 출처는 반드시 명시하시오 (언론사명, 서브레딧명 등).
5. 한국에 미치는 영향이 데이터에서 추론 가능하면 짧게 포함하시오. 근거가
   없으면 이 항목은 생략하시오(추측 금지).
6. 사용자 언어: {language}로 답변하시오.

[관련 이슈]: {issue_name}

[제공 데이터]
{context_block}

[사용자 질문]: {query}
"""


@dataclass
class ChatResponse:
    text: str
    mode: str  # "llm" | "template_fallback"
    tone_distribution_display: str
    sources: list[str]
    warnings: list[str]
    factcheck_notes: list[str]


def _build_context_block(ctx: RetrievedContext) -> str:
    lines = []
    if ctx.articles:
        lines.append(f"최근 기사 {len(ctx.articles)}건:")
        for a in ctx.articles[:8]:
            lines.append(f"  - \"{a['title']}\" ({a.get('outlet', '출처 미상')}, 톤: {a.get('tone', '미분류')})")
    if ctx.reddit_posts:
        lines.append(f"\nReddit 커뮤니티 반응 {len(ctx.reddit_posts)}건:")
        for r in ctx.reddit_posts[:5]:
            lines.append(f"  - r/{r['subreddit']}: \"{r['title']}\" (감성: {r.get('sentiment', '미분류')})")
    if ctx.tone_distribution:
        lines.append(f"\n전체 톤 분포: {format_tone_distribution(ctx.tone_distribution)}")
    if not lines:
        lines.append("(해당 이슈에 대해 현재 수집된 기사/의견 데이터가 없습니다.)")
    return "\n".join(lines)


def _template_fallback_response(query: str, ctx: RetrievedContext, language: str) -> str:
    """LLM 없이 검색된 데이터를 그대로 구조화 — 문장력은 없지만 할루시네이션도 없음."""
    if ctx.is_empty():
        return (
            f"'{issue_name_ko(ctx.issue_id) if ctx.issue_id else query}'에 대해 "
            "현재 수집된 데이터가 없습니다. 데이터 수집 파이프라인(scripts/run_pipeline.py)을 "
            "먼저 실행하면 답변할 수 있는 범위가 넓어집니다."
        )

    parts = [f"[{issue_name_ko(ctx.issue_id)}] 관련 수집 데이터 요약\n"]
    if ctx.tone_distribution:
        parts.append(f"톤 분포: {format_tone_distribution(ctx.tone_distribution)}\n")
    if ctx.articles:
        parts.append("주요 기사:")
        for a in ctx.articles[:5]:
            parts.append(f"  • {a['title']} — {a.get('outlet', '출처 미상')} (톤: {a.get('tone', '미분류')})")
    if ctx.reddit_posts:
        parts.append("\nReddit 여론:")
        for r in ctx.reddit_posts[:3]:
            parts.append(f"  • r/{r['subreddit']}: {r.get('summary_ko') or r['title']} (감성: {r.get('sentiment')})")
    parts.append(
        "\n⚠️ 이 답변은 템플릿 폴백 모드입니다 (로컬 Ollama 미연결). "
        "실제 서비스에서는 이 데이터를 바탕으로 LLM이 자연어 응답을 생성합니다."
    )
    return "\n".join(parts)


def generate_response(query: str, ctx: RetrievedContext, language: str = "ko") -> ChatResponse:
    context_block = _build_context_block(ctx)
    issue_name = issue_name_ko(ctx.issue_id) if ctx.issue_id else "미특정"

    factcheck_notes: list[str] = []
    if FACTCHECK_IMPORT_OK and ctx.issue_id:
        try:
            fc_query = issue_name.split(" ")[0]  # 이슈명 앞 단어로 대략 검색 — 정교화는 Phase 2
            fc_results = search_google_factcheck(fc_query)
            for r in fc_results[:2]:
                factcheck_notes.append(f"⚠️ 관련 팩트체크: \"{r['claim_text']}\" → 판정: {r['rating']} ({r['publisher']})")
        except Exception as e:  # noqa: BLE001
            ctx.warnings.append(f"팩트체크 조회 실패: {e}")

    if not OLLAMA_IMPORT_OK:
        text = _template_fallback_response(query, ctx, language)
        return ChatResponse(
            text=text, mode="template_fallback",
            tone_distribution_display=format_tone_distribution(ctx.tone_distribution),
            sources=ctx.sources, warnings=ctx.warnings, factcheck_notes=factcheck_notes,
        )

    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        language=language, issue_name=issue_name, context_block=context_block, query=query,
    )

    try:
        # verify_model_consensus.py의 CONSENSUS_MODELS 중 첫 모델로 단일 호출.
        # (3모델 합의는 톤 벤치마크용 — 대화 응답 생성은 지연시간 때문에 1개 모델만 사용)
        # CONSENSUS_MODELS는 {"name", "role", "origin"} 딕셔너리 리스트이므로 ["name"]으로 모델명만 뽑는다.
        model = CONSENSUS_MODELS[0]["name"] if CONSENSUS_MODELS else "mistral:latest"
        text = _call_ollama_freeform(model, prompt)
        mode = "llm"
    except Exception as e:  # noqa: BLE001 — Ollama 미기동 등, 이 세션에서는 항상 여기로 빠짐
        ctx.warnings.append(f"LLM 호출 실패({e}) — 템플릿 폴백으로 전환합니다.")
        text = _template_fallback_response(query, ctx, language)
        mode = "template_fallback"

    return ChatResponse(
        text=text, mode=mode,
        tone_distribution_display=format_tone_distribution(ctx.tone_distribution),
        sources=ctx.sources, warnings=ctx.warnings, factcheck_notes=factcheck_notes,
    )
