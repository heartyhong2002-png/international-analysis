"""
prototype_llm_tone_extraction.py — ADR-001 연동 프로토타입
================================================================

⚠️ 컨트롤타워 세션이 만든 프로토타입입니다. ADR-001("LLM 역할정의 및
감성분석 휴먼인더루프", 2026-09-10, LLM 트랙 작성)에서 정의한 구조를
제가 수집하는 gov_announcements 데이터에 실제로 연결하는 첫 시도입니다.

무엇을 검증했고, 무엇을 못 했는지:
  ✅ 프롬프트 구성 로직, LLM 응답(JSON) 파싱 로직 — mock 응답으로 실제 테스트함
     (이 파일 맨 아래 __main__ 부분에서 `python prototype_llm_tone_extraction.py --self-test`
     로 재현 가능)
  ✅ MySQL에 넣을 두 테이블의 스키마 설계 — ADR의 "검수 로그 데이터 스키마"
     표와 1:1로 맞춤
  ❌ 실제 Ollama 호출 — 클라우드 샌드박스에는 로컬 Ollama가 없어서 실행 자체를
     못 해봤습니다. 로컬에서 `ollama serve`가 켜진 상태에서 실제로 돌려보고
     검증 필요합니다.
  ❌ DB에 실제로 적재하는 부분(INSERT) — 스키마 설계만 하고 build_database.py에는
     아직 반영 안 함. SQL 트랙(①번)이 검토 후 반영하는 걸 추천 — 저는 create_schema()
     내용을 안 건드렸습니다.

ADR-001과의 대응 관계:
  - "정부 공식 보도자료는 뉴스와 분리된 '공식 입장' 레이어" (ADR 결정 2)
    → gov_announcements_collector.py에 추가한 source_type이 이 구분을 담당.
      이 스크립트는 source_type == 'official_statement'인 행만 우선 처리합니다.
  - "톤/감성 분류는 LLM + 3단계 휴먼인더루프" (ADR 결정 3)
    → extract_and_classify()가 1차 LLM 분류(=이 스크립트)를 담당. 2차(사람 표본
      검수), 3차(교정 피드백)는 아직 없음 — 이어받는 세션이 검수용 화면/스프레드시트
      등을 만들어야 함.
  - ADR의 "검수 로그 데이터 스키마" 표 → SCHEMA_DDL 참고.

사용법 (로컬에서, Ollama 켜진 상태로):
    python scripts/prototype_llm_tone_extraction.py --limit 5
    python scripts/prototype_llm_tone_extraction.py --self-test   # Ollama 없이 파싱 로직만 확인
"""

import argparse
import json
import os
import re
import sys

import requests
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")  # ADR 컨텍스트에서 이미 검증된 모델

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "international_analysis")

# ============================================================================
# ADR-001의 "검수 로그 데이터 스키마" 표 + 구조화 추출 필드를 반영한 DDL 제안
# (프로토타입 — SQL 트랙이 build_database.py의 create_schema()에 반영할지 검토)
# ============================================================================
SCHEMA_DDL = """
-- LLM이 정부 발표문에서 구조화 추출한 내용 (ADR 결정 2: "주장"으로 추출)
CREATE TABLE IF NOT EXISTS official_statement_extractions (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    announcement_id   INT NOT NULL,
    extracted_entity  VARCHAR(200),   -- 발표 주체 (예: "대한민국 외교부")
    statement_date    VARCHAR(60),
    mentioned_countries VARCHAR(500), -- 콤마 구분 (예: "이란,미국")
    key_claim         TEXT,           -- 핵심 주장
    policy_action     TEXT,           -- 정책 액션
    extraction_model  VARCHAR(100),   -- 예: "qwen2.5:7b"
    extracted_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (announcement_id) REFERENCES gov_announcements(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ADR-001의 "검수 로그 데이터 스키마" 표와 1:1 대응
CREATE TABLE IF NOT EXISTS tone_review_log (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    article_id          INT NOT NULL,        -- gov_announcements.id
    language            VARCHAR(10),
    issue_id            VARCHAR(100),
    source_type         VARCHAR(30),         -- official_statement | state_media_news
    llm_label           VARCHAR(20),         -- 우호적 / 중립적 / 비판적
    llm_evidence_quote  TEXT,
    human_label         VARCHAR(20),         -- 2차 검수 후 채움 (NULL이면 미검수)
    correction_note     TEXT,
    reviewed_at         DATETIME NULL,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES gov_announcements(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# ADR 결정 3: "고정 루브릭(우호적 / 중립적 / 비판적)"
TONE_LABELS = ["우호적", "중립적", "비판적"]

PROMPT_TEMPLATE = """당신은 국제정세 분석 보조원입니다. 아래 정부/외교 발표문을 읽고,
반드시 아래 JSON 형식으로만 답하세요. 다른 설명은 붙이지 마세요.

발표문 소스: {source}
제목: {title}
본문: {description}

다음을 추출하세요:
1. extracted_entity: 이 발표를 한 주체 (기관명)
2. mentioned_countries: 언급된 상대국 목록 (리스트)
3. key_claim: 핵심 주장을 한 문장으로
4. policy_action: 언급된 구체적 정책/행동이 있으면 한 문장으로 (없으면 null)
5. tone_label: 아래 3개 중 정확히 하나 — "우호적", "중립적", "비판적"
6. evidence_quote: tone_label 판단의 근거가 되는 원문 인용 한 문장

JSON 형식:
{{
  "extracted_entity": "...",
  "mentioned_countries": ["...", "..."],
  "key_claim": "...",
  "policy_action": "..." 또는 null,
  "tone_label": "우호적" 또는 "중립적" 또는 "비판적",
  "evidence_quote": "..."
}}
"""


def build_prompt(item):
    """gov_announcements 한 행(dict: source, title, description)으로 프롬프트를 만듭니다."""
    return PROMPT_TEMPLATE.format(
        source=item.get("source", ""),
        title=item.get("title", ""),
        description=(item.get("description", "") or "")[:800],
    )


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_llm_response(raw_text):
    """
    LLM 응답에서 JSON을 파싱합니다. 실제로 로컬 LLM(특히 소형 양자화 모델)은
    ```json ... ``` 코드펜스를 붙이거나, JSON 앞뒤에 군더더기 설명을 붙이는
    경우가 흔합니다 — 그래서 응답 전체를 그대로 json.loads()하지 않고, 가장
    바깥쪽 {...} 블록만 정규식으로 뽑아서 파싱합니다.

    실패 시 None을 반환합니다 (호출 쪽에서 "파싱 실패" 건으로 따로 집계해서,
    나중에 프롬프트를 개선할 근거로 쓸 수 있게).
    """
    match = _JSON_BLOCK_RE.search(raw_text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None

    if data.get("tone_label") not in TONE_LABELS:
        # 루브릭 밖의 값을 내놓으면(예: "긍정적"처럼 살짝 다른 단어) 신뢰 안 함
        return None

    return data


def call_ollama(prompt, model=OLLAMA_MODEL, timeout=60):
    """
    ⚠️ 이 함수는 로컬에서 검증 못 했습니다 (샌드박스에 Ollama 없음).
    Ollama REST API(/api/generate) 표준 호출 방식이라 동작할 것으로 예상하지만,
    실제 model 이름/서버 주소가 로컬 환경과 맞는지 확인 필요합니다.
    """
    resp = requests.post(
        OLLAMA_URL,
        json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.3}},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def extract_and_classify(item):
    """gov_announcements 한 행을 받아서 구조화 추출 + 톤 분류 결과를 반환."""
    prompt = build_prompt(item)
    raw = call_ollama(prompt)
    parsed = parse_llm_response(raw)
    if parsed is None:
        return {"ok": False, "raw_response": raw}
    return {"ok": True, **parsed}


def _self_test():
    """Ollama 없이 파싱 로직만 검증. mock LLM 응답 4종(정상/코드펜스/설명덧붙임/루브릭이탈)으로 테스트."""
    print("=" * 60)
    print("🧪 self-test: parse_llm_response()")
    print("=" * 60)

    cases = [
        ("정상 JSON", '''{
          "extracted_entity": "대한민국 외교부",
          "mentioned_countries": ["이란"],
          "key_claim": "한국은 이란과의 대화를 지지한다",
          "policy_action": "고위급 회담 추진",
          "tone_label": "우호적",
          "evidence_quote": "우리 정부는 이란과의 건설적 대화를 지지합니다"
        }'''),
        ("코드펜스로 감싸짐", '''물론입니다, 아래 JSON으로 답변드립니다:
        ```json
        {"extracted_entity": "US State Dept", "mentioned_countries": ["Iran"],
         "key_claim": "The US condemns the action.", "policy_action": null,
         "tone_label": "비판적", "evidence_quote": "We strongly condemn this."}
        ```
        이상입니다.'''),
        ("루브릭 이탈(신뢰 안 함)", '{"extracted_entity": "x", "mentioned_countries": [], "key_claim": "y", "policy_action": null, "tone_label": "긍정적", "evidence_quote": "z"}'),
        ("JSON 아님(파싱 실패)", "죄송합니다, JSON으로 답변드릴 수 없습니다."),
    ]

    all_ok = True
    for name, raw in cases:
        result = parse_llm_response(raw)
        if name in ("정상 JSON", "코드펜스로 감싸짐"):
            ok = result is not None and result["tone_label"] in TONE_LABELS
        else:
            ok = result is None
        status = "✓" if ok else "✗"
        if not ok:
            all_ok = False
        print(f"  {status} {name}: {'파싱 성공 → ' + str(result.get('tone_label')) if result else '파싱 실패(의도대로)'}")

    print("\n" + ("✅ 전부 통과 — 파싱 로직은 신뢰 가능" if all_ok else "❌ 일부 실패 — parse_llm_response() 점검 필요"))
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="ADR-001 연동 프로토타입 — gov_announcements → LLM 구조화 추출/톤 분류")
    parser.add_argument("--self-test", action="store_true", help="Ollama 없이 파싱 로직만 검증")
    parser.add_argument("--limit", type=int, default=5, help="테스트로 처리할 건수 (DB 연동은 아직 미구현)")
    args = parser.parse_args()

    if args.self_test:
        ok = _self_test()
        sys.exit(0 if ok else 1)

    print("⚠️ DB에서 gov_announcements를 읽어와서 실제로 Ollama에 넣는 부분은")
    print("   아직 프로토타입 단계라 여기 안 붙였습니다. 먼저 --self-test로")
    print("   파싱 로직부터 확인하시고, 그다음 call_ollama()가 로컬 Ollama랑")
    print("   잘 통하는지 작은 샘플로 확인한 뒤에 DB 연동을 이어서 만들어주세요.")


if __name__ == "__main__":
    main()
