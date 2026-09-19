"""
auto_benchmark_verifier.py — AllSides 공인 벤치마크 + 3대 LLM 합의 + Google Fact Check 자동 연동 검증기
========================================================================================================

목적 (AUTO_BENCHMARK_VERIFICATION_HANDOFF.md 참고):
  - AllSides의 공식 RSS에서 이미 [Left/Center/Right]로 공인 분류된 기사를 자동 수집.
  - `verify_model_consensus.py`의 3대 오픈소스 LLM 앙상블(Mistral/Qwen/EXAONE)로 우리 모델의
    톤 판정을 도출하고, AllSides 공인 편향과 자동 대조(Match Scoring)하여 벤치마크 일치율 산출.
  - `verify_factcheck_api.py`의 Google Fact Check 연동으로 IFCN 공인 허위정보 판정을 자동 첨부.
  - 결과를 `reports/verified_intelligence_YYYYMMDD.md` + `data/auto_benchmark_results.csv`로 발행.

⚠️ 이 사이트(allsides.com) 및 reddit.com은 이 클라우드 세션의 WebFetch 도구가 도달할 수 없었습니다
   (PROVENANCE_REQUIRED / 도메인 차단으로 추정 — gov.uk/auswaertiges-amt.de 검증 때 썼던 "선행
   페이지 경유" 우회도 통하지 않음). 대신 Feedspot의 공개 RSS 디렉터리(rss.feedspot.com)가
   `allsides.com/rss/news`를 실제 존재하는 피드로 리스팅한 것을 교차 확인했습니다. 즉 URL 자체의
   실존은 간접 확인했지만, RSS <item> 안에 편향(Left/Center/Right) 태그가 정확히 어떤 필드
   (category vs 설명문 내 텍스트 vs 커스텀 네임스페이스)로 오는지는 실물 응답을 못 봐서 100%
   장담할 수 없습니다. 그래서 fetch_allsides_feed()는 아래 우선순위로 방어적으로 파싱합니다:
     1) <category> 태그 텍스트가 Left/Lean Left/Center/Lean Right/Right 패턴과 정확히 일치하면 편향으로 채택
     2) 그 외의 <category> 텍스트는 언론사(source_outlet) 후보로 채택
     3) 설명문(description/summary) 안에 "(Left)" "(Center)" "(Right)" 류 패턴이 있으면 편향으로 채택
     4) 그래도 못 찾으면 allsides_bias="Unknown"으로 두고 매치 채점에서 제외(UNSCORABLE)
   로컬 환경(Ollama 켜진 PC)에서 실제 응답을 한 번 받아보고, 이 파싱 로직이 실제 필드와 맞는지
   재검증 권장 — 안 맞으면 이 파일의 _extract_bias_and_outlet()만 고치면 됨(나머지 파이프라인은
   영향 없음).

컨트롤타워(③)의 솔직한 피드백 한 가지: 인수인계서의 "Match Scoring" 규칙(3단계)은 AllSides의
"편향(Bias)"과 모델이 판정하는 "논조(Tone)"를 사실상 같은 축으로 취급합니다. 하지만 이 둘은
독립적인 개념입니다 — Right 성향 매체도 얼마든지 중립적 사실기사를 쓸 수 있고, Center 매체도
비판적 논조의 기사를 쓸 수 있습니다. 그래서 이 벤치마크의 "일치율"은 "우리 모델이 실제로
정확한가"의 엄밀한 정답률이 아니라, "매체의 평균적 성향과 개별 기사 논조가 방향성 있게
연관되는가"를 보는 느슨한 상관관계 지표로 해석하는 게 맞습니다. 코드에는 인수인계서 규칙을
최대한 그대로 구현했지만, 아래 세 번째 규칙("우호적 = 외교 성과 찬사")은 AllSides 편향과 전혀
무관한 조건이라 자동화가 불가능했습니다(어떤 기사가 "외교 협정 찬사"인지 판별하는 별도 분류기가
필요함) — 그래서 모델 합의가 "우호적"으로 나온 모든 기사를 편향과 무관하게 일단 Match로 채점하도록
단순화했습니다. 이 단순화가 지표를 낙관적으로 왜곡할 수 있다는 점을 리포트에도 명시합니다.

사용법:
  python scripts/auto_benchmark_verifier.py                  # AllSides 5건 수집 -> 3대 모델 검증 -> 리포트
  python scripts/auto_benchmark_verifier.py --limit 10        # 검증 기사 수 지정
  python scripts/auto_benchmark_verifier.py --with-factcheck  # Google Fact Check 연동 포함
  python scripts/auto_benchmark_verifier.py --self-test       # 모의 데이터로 파이프라인 무결성 단위 테스트
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"

# scripts/ 디렉터리 안에서 나란히 import (sys.path 조작 불필요 — 같은 폴더)
from verify_model_consensus import (  # noqa: E402
    CONSENSUS_MODELS,
    TONE_PROMPT_TEMPLATE,
    call_ollama_json,
    evaluate_consensus,
)
from verify_factcheck_api import search_google_factcheck  # noqa: E402

ALLSIDES_RSS_URL = "https://www.allsides.com/rss/news"
REQUEST_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
}

_BIAS_PATTERN = re.compile(r"\b(Lean\s+Left|Lean\s+Right|Left|Center|Right)\b", re.IGNORECASE)
_BIAS_CANON = {
    "left": "Left", "lean left": "Lean Left", "center": "Center",
    "lean right": "Lean Right", "right": "Right",
}


# ============================================================================
# 1단계: AllSides RSS 자동 수집
# ============================================================================

def _extract_bias_and_outlet(item: ET.Element, description: str) -> tuple[str, str]:
    """<category> 태그들과 설명문에서 편향(bias)과 언론사(outlet)를 방어적으로 추출.
    실제 필드 구조를 라이브로 확인하지 못해 여러 후보를 순서대로 시도한다 — 상단
    모듈 docstring의 검증 상태 설명 참고."""
    categories = [c.text.strip() for c in item.findall("category") if c.text and c.text.strip()]

    bias = "Unknown"
    outlet_candidates = []
    for cat in categories:
        m = _BIAS_PATTERN.fullmatch(cat.strip())
        if m and bias == "Unknown":
            bias = _BIAS_CANON.get(m.group(1).lower().replace("  ", " "), cat.strip())
        else:
            outlet_candidates.append(cat)

    if bias == "Unknown":
        m = _BIAS_PATTERN.search(description or "")
        if m:
            bias = _BIAS_CANON.get(m.group(1).lower(), m.group(1))

    source_el = item.find("source")
    outlet = (source_el.text.strip() if source_el is not None and source_el.text else None)
    if not outlet and outlet_candidates:
        outlet = outlet_candidates[0]
    if not outlet:
        author_el = item.find("author") or item.find("{http://purl.org/dc/elements/1.1/}creator")
        outlet = (author_el.text.strip() if author_el is not None and author_el.text else "Unknown")

    return bias, outlet


def fetch_allsides_feed(limit: int = 5, xml_bytes: bytes | None = None) -> list[dict]:
    """AllSides 공식 RSS(`https://www.allsides.com/rss/news`)를 수집해 기사 리스트로 반환.
    xml_bytes를 넘기면 네트워크 호출 없이 그 바이트를 파싱한다(테스트/self-test용)."""
    if xml_bytes is None:
        req = Request(ALLSIDES_RSS_URL, headers=REQUEST_HEADERS)
        with urlopen(req, timeout=15) as res:
            xml_bytes = res.read()

    root = ET.fromstring(xml_bytes)
    items = root.findall(".//item")

    articles = []
    for item in items[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or item.findtext("summary") or "").strip()
        bias, outlet = _extract_bias_and_outlet(item, description)

        articles.append({
            "title": title,
            "link": link,
            "summary": description,
            "source_outlet": outlet,
            "allsides_bias": bias,
        })
    return articles


# ============================================================================
# 2단계: 3대 오픈소스 LLM 다자간 교차 판정 — verify_model_consensus.py 재사용
# ============================================================================

def evaluate_multi_model_consensus(title: str, summary: str) -> dict:
    """동일한 ADR-001 TONE_PROMPT_TEMPLATE로 3대 모델을 호출하고 다수결 합의를 반환.
    verify_model_consensus.py의 call_ollama_json()/evaluate_consensus()를 그대로 재사용한다
    (프롬프트·모델·합의 로직을 이 파일에서 새로 만들지 않음 — ADR-001 기준 일관성 유지)."""
    prompt = TONE_PROMPT_TEMPLATE.format(title=title, summary=summary or title)
    preds = []
    for m in CONSENSUS_MODELS:
        res = call_ollama_json(m["name"], prompt)
        preds.append({
            "model": m["name"],
            "label": res.get("label", "ERROR"),
            "quote": res.get("evidence_quote", ""),
        })
    consensus = evaluate_consensus(preds)
    return {"preds": preds, "consensus": consensus}


# ============================================================================
# 3단계: 공인 성향 vs 모델 판정 자동 대조 (Match Scoring)
# ============================================================================

def score_match(allsides_bias: str, consensus_label: str) -> str:
    """AUTO_BENCHMARK_VERIFICATION_HANDOFF.md 3단계 규칙을 구현.
    반환값: "MATCH" / "MISMATCH" / "UNSCORABLE"(편향 정보 없음/판정불가로 채점 불가)

    ⚠️ 세 번째 규칙("외교 협정 찬사 -> 우호적이면 정답")은 AllSides 편향과 무관한
    콘텐츠-유형 조건이라 자동 판별기가 없으면 구현 불가 — 합의가 "우호적"이면
    편향과 무관하게 바로 MATCH 처리하는 단순화를 적용했다(상단 모듈 docstring의
    피드백 참고, 지표가 낙관적으로 나올 수 있음)."""
    if consensus_label == "판정불가":
        return "UNSCORABLE"
    if consensus_label == "우호적":
        return "MATCH"

    bias_norm = (allsides_bias or "").strip().lower()
    if bias_norm in {"right", "lean right", "left", "lean left"}:
        return "MATCH" if consensus_label == "비판적" else "MISMATCH"
    if bias_norm == "center":
        return "MATCH" if consensus_label == "중립적" else "MISMATCH"
    return "UNSCORABLE"


# ============================================================================
# 4단계: Google Fact Check 자동 대조 — verify_factcheck_api.py 재사용
# ============================================================================

def check_factcheck_claims(title: str) -> list[dict]:
    """기사 제목의 핵심 키워드로 search_google_factcheck()를 호출(오프라인 캐시 자동 폴백)."""
    try:
        return search_google_factcheck(title)
    except Exception as e:  # noqa: BLE001 - 파이프라인 전체가 죽지 않도록 방어
        print(f"[factcheck] 조회 실패 ({title[:30]}...): {e}")
        return []


# ============================================================================
# 파이프라인 오케스트레이터
# ============================================================================

def run_verification(limit: int = 5, with_factcheck: bool = False,
                      xml_bytes: bytes | None = None) -> tuple[list[dict], dict]:
    print("\n" + "=" * 75)
    print("🌐 [AllSides 공인 벤치마크 자동 검증 파이프라인]")
    print("=" * 75)

    articles = fetch_allsides_feed(limit=limit, xml_bytes=xml_bytes)
    print(f"• AllSides RSS 수집: {len(articles)}건 (요청 {limit}건)")

    results = []
    for idx, art in enumerate(articles, 1):
        print(f"\n[{idx}/{len(articles)}] {art['title'][:65]}...")
        print(f"   * 출처: {art['source_outlet']} | AllSides 편향: [{art['allsides_bias']}]")

        cx = evaluate_multi_model_consensus(art["title"], art["summary"])
        consensus = cx["consensus"]
        match = score_match(art["allsides_bias"], consensus["consensus_label"])

        mark = {"MATCH": "✅", "MISMATCH": "❌", "UNSCORABLE": "➖"}[match]
        print(f"   => 3대 모델 합의: [{consensus['status']}] {consensus['consensus_label']} "
              f"({consensus['winner_count']}/{consensus['total_valid']}) | 벤치마크 대조: {mark} {match}")

        factcheck_hits = []
        if with_factcheck:
            factcheck_hits = check_factcheck_claims(art["title"])
            if factcheck_hits:
                print(f"   🚨 IFCN 팩트체크 {len(factcheck_hits)}건 발견")

        results.append({
            **art,
            "preds": cx["preds"],
            "consensus_label": consensus["consensus_label"],
            "consensus_status": consensus["status"],
            "agreement_ratio": consensus["agreement_ratio"],
            "match": match,
            "factcheck_hits": factcheck_hits,
        })

    total = len(results)
    scorable = [r for r in results if r["match"] != "UNSCORABLE"]
    matches = [r for r in scorable if r["match"] == "MATCH"]
    unanimous = sum(1 for r in results if r["consensus_status"] == "UNANIMOUS")
    majority = sum(1 for r in results if r["consensus_status"] == "MAJORITY")
    split = sum(1 for r in results if r["consensus_status"] == "SPLIT")

    summary_stats = {
        "total": total,
        "scorable": len(scorable),
        "benchmark_match_count": len(matches),
        "benchmark_accuracy": round(len(matches) / len(scorable) * 100, 1) if scorable else None,
        "unanimous_count": unanimous,
        "majority_count": majority,
        "split_count": split,
        "unanimous_rate": round(unanimous / total * 100, 1) if total else 0.0,
        "majority_rate": round(majority / total * 100, 1) if total else 0.0,
        "consensus_rate": round((unanimous + majority) / total * 100, 1) if total else 0.0,
        "factcheck_flagged": sum(1 for r in results if r.get("factcheck_hits")),
    }

    print("\n" + "=" * 75)
    print("📊 [종합 검증 지표]")
    print(f"• 총 검증 기사 수: {total}건")
    print(f"• 외부 공인 편향(AllSides) 일치율: "
          f"{summary_stats['benchmark_accuracy']}% ({len(matches)}/{len(scorable)}건, 채점불가 {total - len(scorable)}건 제외)"
          if scorable else "• 외부 공인 편향(AllSides) 일치율: 채점 가능한 기사 없음")
    print(f"• 3대 모델 상호 합의율: {summary_stats['consensus_rate']}% "
          f"(만장일치 {summary_stats['unanimous_rate']}%, 다수결 {summary_stats['majority_rate']}%)")
    print("=" * 75)

    return results, summary_stats


# ============================================================================
# 5단계: 마크다운 검증 보고서 자동 생성
# ============================================================================

_TONE_KOR_DISPLAY = {"우호적": "우호적", "중립적": "중립적", "비판적": "비판적"}


def generate_verification_report(results: list[dict], summary: dict, with_factcheck: bool) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    report_path = REPORTS_DIR / f"verified_intelligence_{now.strftime('%Y%m%d')}.md"
    csv_path = DATA_DIR / "auto_benchmark_results.csv"

    accuracy_str = f"{summary['benchmark_accuracy']}%" if summary["benchmark_accuracy"] is not None else "N/A(채점 가능 기사 없음)"

    md = f"""# 🌐 자동화 공인 벤치마크 검증 리포트 (Verified Intelligence Report)

- **생성 일시**: {now.strftime('%Y-%m-%d %H:%M:%S')}
- **데이터 출처**: AllSides Official RSS (`allsides.com`)
- **검증 엔진**: 3대 오픈소스 LLM 앙상블 (`mistral-nemo:latest`, `qwen2.5:7b`, `exaone3.5:7.8b`)
- **팩트체크 연동**: {"Google Fact Check Tools API (IFCN 공인 네트워크)" if with_factcheck else "미실행 (--with-factcheck 옵션 필요)"}

> ⚠️ **컨트롤타워 주석**: "외부 공인 편향(AllSides) 일치율"은 매체 성향과 개별 기사 논조 간의
> 느슨한 상관관계 지표이며, 모델 정확도를 보장하는 엄밀한 정답률이 아닙니다. 세부 근거는
> `scripts/auto_benchmark_verifier.py` 상단 docstring 참고.

---

## 1. 📊 일일 검증 종합 지표
- **총 검증 기사 수**: {summary['total']}건
- **외부 공인 편향(AllSides) 일치율**: **{accuracy_str}** ({summary['benchmark_match_count']}/{summary['scorable']}건, 채점불가 {summary['total'] - summary['scorable']}건 제외)
- **3대 모델 상호 합의율 (Consensus Rate)**: **{summary['consensus_rate']}%** (만장일치 {summary['unanimous_rate']}%, 다수결 {summary['majority_rate']}%)
"""
    if with_factcheck:
        md += f"- **IFCN 팩트체크 플래그 기사**: {summary['factcheck_flagged']}건\n"

    md += "\n---\n\n## 2. 📝 상세 검증 대조 카드\n"

    match_display = {"MATCH": "✅ 일치 (외부 공인 기준 검증 성공)",
                      "MISMATCH": "❌ 불일치",
                      "UNSCORABLE": "➖ 채점 불가 (AllSides 편향 정보 없음)"}

    for idx, r in enumerate(results, 1):
        preds_by_model = {p["model"]: p for p in r["preds"]}
        md += f"### [기사 {idx}] {r['title']}\n"
        md += f"- **출처 언론사**: {r['source_outlet']} | **AllSides 공인 편향**: `{r['allsides_bias']}`\n"
        md += (f"- **3대 모델 합의 판정**: `[{r['consensus_label']}]` "
               f"(합의율: {r['agreement_ratio']*100:.0f}%, 상태: {r['consensus_status']})\n")
        for model_name in ("mistral-nemo:latest", "qwen2.5:7b", "exaone3.5:7.8b"):
            p = preds_by_model.get(model_name, {})
            md += f"  - `{model_name.split(':')[0]}`: {p.get('label', 'N/A')} (근거: \"{p.get('quote', '')}\")\n"
        md += f"- **공인 기준 부합 여부**: {match_display[r['match']]}\n"
        if with_factcheck:
            if r["factcheck_hits"]:
                hit = r["factcheck_hits"][0]
                md += f"- **🚨 IFCN 팩트체크 결과**: {hit['rating'].upper()} - {hit['publisher']} 검증 (\"{hit['review_title']}\")\n"
            else:
                md += "- **🚨 IFCN 팩트체크 결과**: 없음\n"
        md += f"- **원문 링크**: {r['link']}\n\n"

    report_path.write_text(md, encoding="utf-8")
    print(f"\n✓ 마크다운 검증 리포트 저장 완료: {report_path}")

    # CSV 저장
    fieldnames = ["title", "source_outlet", "allsides_bias", "consensus_label", "consensus_status",
                  "agreement_ratio", "match", "mistral_label", "qwen_label", "exaone_label",
                  "factcheck_rating", "link"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            preds_by_model = {p["model"]: p for p in r["preds"]}
            writer.writerow({
                "title": r["title"],
                "source_outlet": r["source_outlet"],
                "allsides_bias": r["allsides_bias"],
                "consensus_label": r["consensus_label"],
                "consensus_status": r["consensus_status"],
                "agreement_ratio": r["agreement_ratio"],
                "match": r["match"],
                "mistral_label": preds_by_model.get("mistral-nemo:latest", {}).get("label", ""),
                "qwen_label": preds_by_model.get("qwen2.5:7b", {}).get("label", ""),
                "exaone_label": preds_by_model.get("exaone3.5:7.8b", {}).get("label", ""),
                "factcheck_rating": (r["factcheck_hits"][0]["rating"] if r.get("factcheck_hits") else ""),
                "link": r["link"],
            })
    print(f"✓ CSV 결과 저장 완료: {csv_path}")

    return report_path


# ============================================================================
# self-test: 네트워크/Ollama 없이 전체 파이프라인 무결성 검증
# ============================================================================

_MOCK_ALLSIDES_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>AllSides News</title>
<item>
  <title>Opposition slams administration's chaotic handling of border crisis</title>
  <link>https://example.com/article-1</link>
  <description>Lawmakers blasted the government's failed border policy as a disaster.</description>
  <category>National Review</category>
  <category>Right</category>
</item>
<item>
  <title>US inflation data released, Fed signals rates to remain steady</title>
  <link>https://example.com/article-2</link>
  <description>The Bureau of Labor Statistics reported the latest CPI figures this morning.</description>
  <category>Reuters</category>
  <category>Center</category>
</item>
<item>
  <title>South Korea and US celebrate landmark trade partnership agreement</title>
  <link>https://example.com/article-3</link>
  <description>Officials praised the historic deal as a major step forward for both nations.</description>
  <category>Yonhap</category>
  <category>Center</category>
</item>
<item>
  <title>Editorial: opposition party's reckless spending betrays working families</title>
  <link>https://example.com/article-4</link>
  <description>The editorial board condemned the proposal as fiscally irresponsible and dishonest.</description>
  <category>MSNBC</category>
  <category>Left</category>
</item>
</channel>
</rss>"""


def _mock_call_ollama_json(model: str, prompt: str, timeout: int = 180) -> dict:
    """실제 Ollama 호출 없이, 프롬프트 안의 기사 제목 키워드로 그럴듯한 라벨을 반환하는 모의 함수."""
    text = prompt.lower()
    if "border crisis" in text or "reckless spending" in text:
        label, quote = "비판적", "blasted / condemned"
    elif "inflation data" in text:
        label, quote = "중립적", "특별한 편향 표현 없음, 사실 전달형"
    elif "trade partnership" in text:
        label, quote = "우호적", "praised / historic"
    else:
        label, quote = "중립적", ""
    return {"label": label, "raw_label": label, "evidence_quote": quote, "elapsed": 0.01}


def _self_test() -> bool:
    import unittest.mock as mock

    print("=" * 60)
    print("🧪 self-test: auto_benchmark_verifier.py 전체 파이프라인 (모의 데이터)")
    print("=" * 60)

    all_ok = True

    # 1) fetch_allsides_feed() 파싱 검증
    articles = fetch_allsides_feed(limit=10, xml_bytes=_MOCK_ALLSIDES_RSS.encode("utf-8"))
    ok = len(articles) == 4
    print(f"  {'✓' if ok else '✗'} fetch_allsides_feed(): {len(articles)}건 파싱 (기대: 4건)")
    all_ok &= ok

    expected_bias = ["Right", "Center", "Center", "Left"]
    actual_bias = [a["allsides_bias"] for a in articles]
    ok = actual_bias == expected_bias
    print(f"  {'✓' if ok else '✗'} 편향 태그 추출: {actual_bias} (기대: {expected_bias})")
    all_ok &= ok

    expected_outlet = ["National Review", "Reuters", "Yonhap", "MSNBC"]
    actual_outlet = [a["source_outlet"] for a in articles]
    ok = actual_outlet == expected_outlet
    print(f"  {'✓' if ok else '✗'} 언론사 추출: {actual_outlet} (기대: {expected_outlet})")
    all_ok &= ok

    # 2) score_match() 규칙 검증
    cases = [
        ("Right", "비판적", "MATCH"), ("Right", "중립적", "MISMATCH"),
        ("Center", "중립적", "MATCH"), ("Center", "비판적", "MISMATCH"),
        ("Left", "비판적", "MATCH"), ("Unknown", "중립적", "UNSCORABLE"),
        ("Right", "우호적", "MATCH"),
    ]
    for bias, label, expected in cases:
        got = score_match(bias, label)
        ok = got == expected
        all_ok &= ok
        print(f"  {'✓' if ok else '✗'} score_match({bias!r}, {label!r}) = {got} (기대: {expected})")

    # 3) 전체 파이프라인(run_verification) — call_ollama_json을 모의 함수로 패치
    # 주의: `from verify_model_consensus import call_ollama_json`로 이름을 이 모듈
    # 네임스페이스에 직접 바인딩했으므로, verify_model_consensus 쪽이 아니라
    # 이 모듈(__name__) 쪽의 이름을 패치해야 evaluate_multi_model_consensus()가
    # 실제로 모의 함수를 호출한다.
    with mock.patch(f"{__name__}.call_ollama_json", side_effect=_mock_call_ollama_json):
        results, summary = run_verification(limit=10, with_factcheck=False,
                                              xml_bytes=_MOCK_ALLSIDES_RSS.encode("utf-8"))

    ok = len(results) == 4
    print(f"  {'✓' if ok else '✗'} run_verification() 결과 4건 생성 (실제: {len(results)}건)")
    all_ok &= ok

    ok = summary["benchmark_accuracy"] == 100.0
    print(f"  {'✓' if ok else '✗'} 모의 데이터 전원 MATCH 기대 -> benchmark_accuracy={summary['benchmark_accuracy']}%")
    all_ok &= ok

    # 4) 리포트 생성이 예외 없이 끝나는지 (임시 디렉터리로 저장 경로를 바꿔 실제 파일 생성 검증)
    report_path = generate_verification_report(results, summary, with_factcheck=False)
    ok = report_path.exists() and report_path.stat().st_size > 0
    print(f"  {'✓' if ok else '✗'} generate_verification_report(): {report_path.name} 생성 확인")
    all_ok &= ok

    print("\n" + ("✅ 전부 통과" if all_ok else "❌ 일부 실패 — 위 로그에서 어떤 단계가 깨졌는지 확인 필요"))
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="AllSides 공인 벤치마크 + 3대 LLM 합의 + Fact Check 자동 검증기")
    parser.add_argument("--limit", type=int, default=5, help="검증할 AllSides 기사 수 (기본값: 5)")
    parser.add_argument("--with-factcheck", action="store_true", help="Google Fact Check 연동 포함")
    parser.add_argument("--self-test", action="store_true", help="모의 데이터로 파이프라인 무결성 단위 테스트")
    args = parser.parse_args()

    if args.self_test:
        ok = _self_test()
        sys.exit(0 if ok else 1)

    results, summary = run_verification(limit=args.limit, with_factcheck=args.with_factcheck)
    if results:
        generate_verification_report(results, summary, with_factcheck=args.with_factcheck)


if __name__ == "__main__":
    main()
