"""intent_classifier.py — 규칙 기반 쿼리 의도 분류 + 이슈 태그 추출

챗봇_구현_세부_계획.md 3.1절 설계를 실제 코드로 옮긴 것. LLM을 부르지 않고
순수 규칙(키워드 매칭)으로 판단하는 이유는 두 가지:
  1) 속도 — 매 요청마다 Ollama를 또 부르면 응답 지연이 배로 늘어난다.
  2) 디버깅 가능성 — "왜 이렇게 분류됐지?"에 바로 답할 수 있어야
     3단계 휴먼인더루프(ADR-001)처럼 나중에 검수/보완하기 쉽다.

규칙 기반의 한계(예: "이란이랑 사우디랑 요즘 어때?"처럼 이슈가 명시 안 된
복합 질문)는 Phase 2에서 LLM 기반 분류로 업그레이드하는 걸 전제로 한다
(챗봇_구현_세부_계획.md "위험 요소 & 대응" 표 참고).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .issues import ISSUES, all_issue_ids

# 의도 카테고리별 트리거 키워드. 순서가 곧 우선순위(먼저 매치되는 쪽이 아니라
# 스코어가 가장 높은 쪽이 채택되므로, 여기서는 카테고리 간 키워드가 최대한
# 겹치지 않도록 구성했다.
INTENT_KEYWORDS: dict[str, list[str]] = {
    "FORECAST": ["앞으로", "미래", "예상", "전망", "될까", "될 거", "향후", "will", "forecast"],
    "COUNTRY_COMPARE": [" vs ", "비교", "관계는", "관계 어때", "관계 어떻게", "relations"],
    "RECENT_NEWS": ["요즘", "요새", "최근", "지금", "어제", "오늘", "이번주", "이번 주", "뉴스", "recent", "latest"],
    "RISK": ["위험", "위협", "긴장", "충돌", "전쟁 날", "터질", "risk", "escalat"],
    "DATA_REQUEST": ["통계", "자료", "데이터", "그래프", "지표", "수치", "몇 퍼센트", "비율"],
    "ISSUE_EXPLAIN": ["설명해줄래", "설명해줘", "뭐야", "뭐임", "배경은", "역사", "언제부터", "알려줘", "what is", "explain"],
}

# 기본값 — 위 카테고리 중 아무것도 안 걸리면 "이슈 설명"으로 취급.
# (질문 자체가 짧고 이슈명만 던지는 경우가 실제 사용자 입력에서 제일 흔함:
#  "이란 핵협상" 한 마디만 치는 식)
DEFAULT_INTENT = "ISSUE_EXPLAIN"


@dataclass
class IntentResult:
    intent: str
    issue_ids: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    confidence: float = 0.0  # 매칭된 키워드 수 기반의 대략적 신뢰도(0~1), 임계값 튜닝용


def classify_intent(query: str) -> IntentResult:
    """쿼리 텍스트를 소문자화해서 카테고리별 키워드 점수를 매기고 최고점을 채택."""
    q = query.lower()

    scores: dict[str, int] = {}
    matched_all: list[str] = []
    for intent, keywords in INTENT_KEYWORDS.items():
        hits = [kw for kw in keywords if kw.lower() in q]
        if hits:
            scores[intent] = len(hits)
            matched_all.extend(hits)

    if not scores:
        intent = DEFAULT_INTENT
        confidence = 0.3  # 낮은 신뢰도 — 기본값으로 떨어진 케이스임을 응답 생성기가 알 수 있게
    else:
        intent = max(scores, key=scores.get)
        total_hits = sum(scores.values())
        confidence = min(1.0, scores[intent] / max(total_hits, 1) + 0.3)

    issue_ids = extract_issue_tags(query)

    return IntentResult(
        intent=intent,
        issue_ids=issue_ids,
        matched_keywords=matched_all,
        confidence=round(confidence, 2),
    )


def extract_issue_tags(query: str) -> list[str]:
    """쿼리에서 21개(+횡단 1개) 이슈 중 관련된 것을 키워드 매칭으로 추출.

    1차 키워드(고유명사)가 하나라도 걸린 이슈가 있으면, 2차 키워드(범용 용어)
    만으로 걸린 이슈는 결과에서 제외한다 — "이란 핵협상"에서 "핵"이라는
    범용어 때문에 North_Korea_Nuclear까지 같이 걸리는 오탐을 막기 위함
    (issues.py 모듈 docstring 참고). "요즘 핵협상 어때"처럼 고유명사가 아예
    없는 질문에서는 2차 키워드만으로도 후보를 내놓는다(폴백).

    여러 이슈가 동시에 걸릴 수 있다(예: "한일관계랑 대만해협이랑 관련있어?").
    매칭 스코어 순으로 정렬해서 반환하므로 호출 측은 issue_ids[0]을 "1순위
    이슈"로 취급하면 된다.
    """
    q = query.lower()
    primary_hits: list[tuple[str, int]] = []
    secondary_hits: list[tuple[str, int]] = []

    for issue_id, info in ISSUES.items():
        p_score = sum(1 for kw in info["keywords_primary"] if kw.lower() in q)
        s_score = sum(1 for kw in info["keywords_secondary"] if kw.lower() in q)
        if p_score > 0:
            primary_hits.append((issue_id, p_score))
        elif s_score > 0:
            secondary_hits.append((issue_id, s_score))

    chosen = primary_hits if primary_hits else secondary_hits
    chosen.sort(key=lambda x: x[1], reverse=True)
    return [issue_id for issue_id, _ in chosen]


if __name__ == "__main__":
    # 간단한 자가 테스트 — pytest 없이도 python -m chatbot_core.intent_classifier로 확인 가능
    test_queries = [
        "미중 무역 전쟁 지금 어때?",
        "이란 핵협상이 뭐야?",
        "한일관계 앞으로 어떻게 될까?",
        "최근 대만 해협에서 뭐가 일어났어?",
        "북한 핵 위협 얼마나 심각해?",
        "우크라이나 전쟁 통계 보여줘",
    ]
    for q in test_queries:
        result = classify_intent(q)
        print(f"Q: {q}")
        print(f"  -> intent={result.intent}, issues={result.issue_ids}, "
              f"confidence={result.confidence}, matched={result.matched_keywords}")
