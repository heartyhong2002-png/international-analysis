"""
신호 괴리율(Signal Gap) 및 조기경보 3단계(3-Tier Canonical Pivot) 분석 파이프라인.

[아키텍처 (갤럭시 북5 프로 16GB RAM 최적화)]
- 1단계 (다국어 분석 & 팩트 추출): `qwen2.5:7b`
  러시아어, 아랍어, 중국어, 일본어, 유럽/중남미어, 영미권 원문을 판독하여
  표준 영문 JSON(신호 괴리 점수, 핵심 인용구, 영문 요약)으로 추출.
- 2-A단계 (한국어 특화 재분석): `exaone3.5:7.8b`
  표준 영문 JSON을 바탕으로 한국 공급망·외교 관점의 조기경보 브리핑 및 대시보드 문구 생성.
- 2-B단계 (영어 특화 정밀 분석): `llama3.1:8b`
  표준 영문 JSON을 바탕으로 글로벌 싱크탱크 스타일의 영문 브리핑 및 대시보드 문구 생성.

이 모듈은 미래 사건을 단정하지 않는다. 관측된 공식·독립·대중 신호의
괴리, 증거 범위, 자료량, 모델 합의도를 분리해 ``risk_signal_score``와
``alert_level``을 계산한다. 자료가 부족하면 점수가 높아도 경보를 올리지
않고 ``확인 필요``로 반환한다.
"""

import os
import json
import pandas as pd
import requests
from datetime import datetime
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 3단계 순차 파이프라인 모델 구성 (16GB 통합 메모리 최적화)
MULTILINGUAL_EXTRACTOR_MODEL = "qwen2.5:7b"
KOREAN_SPECIALIST_MODEL = "exaone3.5:7.8b"
ENGLISH_SPECIALIST_MODEL = "llama3.1:8b"

# 하위 호환성을 위한 권역별 1차 추출 모델 매핑
REGION_MODELS = {
    "Russia": MULTILINGUAL_EXTRACTOR_MODEL,
    "China": MULTILINGUAL_EXTRACTOR_MODEL,
    "Middle_East": MULTILINGUAL_EXTRACTOR_MODEL,
    "Global_South": MULTILINGUAL_EXTRACTOR_MODEL,
}

OLLAMA_URL = "http://localhost:11434/api/generate"
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "signal_gap"
INPUT_CSV = DATA_DIR / "rss_signal_gap_latest.csv"
OUTPUT_JSON = DATA_DIR / "signal_gap_analysis.json"

# 산식 버전을 결과에 함께 남겨 백테스트와 사람 검수 때 기준 변경을 추적한다.
SCORING_VERSION = "early-warning-v1"
PIPELINE_VERSION = "3-tier-canonical-pivot-v1"


def _clamp(value, low=0.0, high=100.0) -> float:
    """잘못된 LLM 수치나 결측값이 경보 산식을 오염시키지 않게 제한한다."""
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low


def calculate_alert_assessment(
    discrepancy_score,
    official_count: int,
    independent_count: int,
    public_count: int = 0,
    consensus_agreement=None,
    evidence_count: int = 0,
) -> dict:
    """관측 신호를 0~100 위험 신호 점수와 단계화된 경보로 변환한다.

    구성: 신호 괴리 40%, 자료량 25%, 근거 범위 20%, 모델 합의 15%.
    ``consensus_agreement``가 없다면 합의 점수는 0점으로 둔다. 즉, 미측정
    합의를 높은 신뢰도로 간주하지 않는다. 공식/독립 두 흐름이 모두 없거나
    근거가 충분하지 않으면 어떤 점수도 경보 승격의 근거가 될 수 없다.
    """
    official_count = max(0, int(official_count or 0))
    independent_count = max(0, int(independent_count or 0))
    public_count = max(0, int(public_count or 0))
    evidence_count = max(0, int(evidence_count or 0))
    source_groups = sum(bool(n) for n in (official_count, independent_count, public_count))
    total_items = official_count + independent_count + public_count

    # 비교할 양쪽 신호가 모두 있을수록 LLM이 낸 괴리 수치를 신뢰할 수 있다.
    comparability = min(1.0, min(official_count, independent_count) / 3.0)
    signal_gap_score = round(_clamp(discrepancy_score) * (0.5 + 0.5 * comparability), 1)
    volume_score = min(100.0, total_items / 15.0 * 100.0)
    coverage_score = min(100.0, source_groups / 3.0 * 60.0 + min(evidence_count, 6) / 6.0 * 40.0)
    agreement_score = _clamp(consensus_agreement) if consensus_agreement is not None else 0.0
    risk_signal_score = round(
        signal_gap_score * 0.40 + volume_score * 0.25 + coverage_score * 0.20 + agreement_score * 0.15,
        1,
    )

    evidence_sufficient = source_groups >= 2 and official_count >= 1 and independent_count >= 1 and evidence_count >= 2
    if not evidence_sufficient:
        alert_level = "확인 필요"
        alert_reason = "공식·독립 신호의 비교 근거 또는 근거 문장이 부족해 경보 단계 판단을 보류함"
        human_review_required = True
    elif risk_signal_score < 30:
        alert_level = "관찰"
        alert_reason = "관측된 위험 신호는 있으나 현재 산식상 경보 상향 근거가 제한적임"
        human_review_required = False
    elif risk_signal_score < 55:
        alert_level = "주의"
        alert_reason = "복수 출처에서 위험 신호가 확인되어 추적 관찰이 필요함"
        human_review_required = False
    elif risk_signal_score < 75:
        alert_level = "경보"
        alert_reason = "신호 괴리와 자료량이 함께 높아 담당자 확인이 필요함"
        human_review_required = True
    else:
        alert_level = "고경보"
        alert_reason = "복수 근거의 위험 신호가 강하게 관측되어 우선 확인이 필요함"
        human_review_required = True

    return {
        "scoring_version": SCORING_VERSION,
        "risk_signal_score": risk_signal_score,
        "signal_gap_score": signal_gap_score,
        "evidence_coverage": round(coverage_score, 1),
        "source_diversity": source_groups,
        "source_item_count": total_items,
        "consensus_agreement": agreement_score if consensus_agreement is not None else None,
        "alert_level": alert_level,
        "alert_reason": alert_reason,
        "human_review_required": human_review_required,
    }


# [1단계] 다국어 원문 -> 표준 영문 JSON (Canonical English Pivot) 추출 프롬프트
PROMPT_STAGE1_EXTRACT = """You are a multilingual geopolitical and supply-chain risk-signal analyst.
Below are recent news items (headline + summary, potentially in Russian, Arabic, Chinese, Japanese, Korean, Spanish, French, German, Portuguese, or English) from an Official State Media and an Independent/Exiled Media concerning the [{region}] region.

[Official State Media]
{official_text}

[Independent/Exiled Media]
{independent_text}

Task:
1. Focus ONLY on geopolitical, security, military, sanctions, trade, energy, maritime, or governance topics. Ignore sports, entertainment, lifestyle, folklore, or purely religious reflections.
2. Compare the supplied geopolitical/economic narratives and calculate a 'Signal Gap Discrepancy Score' from 0 to 100 (0 = identical framing, 100 = opposing framing or state omission of critical crisis/sanction/security events). If either side has no geopolitical/economic items, set discrepancy_score to 0.
3. Write a brief summary (2-3 sentences in English) explaining the observed narrative gap on geopolitical/economic risk signals, and cite at least two short verbatim evidence phrases (translated into English if originally in another script, one from Official State Media, one from Independent/Exiled Media).
4. Do not state or imply that a future event is certain. Use observable risk-signal and verification language only.

You MUST respond strictly in the following JSON format without any markdown blocks or extra text:
{{
  "discrepancy_score": 85,
  "narrative_differences": "Explanation of geopolitical/economic framing differences in English...",
  "evidence_phrases": [
    "verbatim quote from Official State Media",
    "verbatim quote from Independent/Exiled Media"
  ]
}}
"""

# [2-A단계] 영문 표준 피벗 -> 한국어 특화 브리핑 및 대시보드 생성 프롬프트 (EXAONE 3.5)
PROMPT_STAGE2A_KOREAN = """당신은 공급망·지정학 리스크 조기경보 시스템의 한국어 수석 분석가입니다.
아래는 다국어 분석 모델이 [{region}] 권역의 공식 발표와 독립 언론 보도 간 괴리를 분석한 표준 영문 데이터입니다.

- 권역: {region}
- 산출 경보 단계: {alert_level} (위험 신호 점수: {risk_signal_score}/100, 신호 괴리: {signal_gap_score}/100)
- 영문 괴리 분석 요약: {narrative_differences}
- 핵심 근거 인용구: {evidence_phrases}

작성 규칙:
1. 미래 사건을 단정적으로 예측하는 표현("전쟁 확정", "발생 확실", "예측됨" 등)을 절대 사용하지 마세요.
2. 반드시 "관측된 위험 신호", "보도 프레임 괴리", "추적 관찰 필요", "공급망 영향 점검 필요" 등 조기경보 용어를 사용하세요.
3. 한국어 대시보드 카드용 1줄 헤드라인(korean_headline)과 한국 정부·기업 관점의 2~3문장 브리핑(korean_briefing)을 작성하세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "korean_headline": "권역 핵심 위험 신호 1줄 요약 (한국어)",
  "korean_briefing": "공식 매체와 독립 언론 간의 보도 괴리 및 공급망·지정학 리스크 점검 포인트 2~3문장 (한국어)"
}}
"""

# [2-B단계] 영문 표준 피벗 -> 영어 특화 글로벌 싱크탱크 브리핑 프롬프트 (Llama 3.1)
PROMPT_STAGE2B_ENGLISH = """You are a senior geopolitical intelligence editor at an international policy think tank.
Below is the canonical risk-signal assessment extracted from official vs. independent media for the [{region}] region.

- Region: {region}
- Alert Level: {alert_level} (Risk Signal Score: {risk_signal_score}/100, Signal Gap: {signal_gap_score}/100)
- Raw Narrative Gap Summary: {narrative_differences}
- Evidence Quotes: {evidence_phrases}

Instructions:
1. Never use deterministic predictions ("will happen", "inevitable", "predicted"). Use strict early-warning and verification terminology ("observed signal divergence", "requires monitoring", "supply-chain risk indicator").
2. Refine the findings into a concise 1-line dashboard headline (english_headline) and a polished 2-3 sentence executive summary (english_executive_summary) suitable for an international intelligence dashboard.

Respond strictly in the following JSON format:
{{
  "english_headline": "Concise 1-line executive risk signal headline",
  "english_executive_summary": "Polished 2-3 sentence think-tank style intelligence summary on narrative divergence and supply-chain implications."
}}
"""


def _normalize_evidence_phrases(raw_phrases) -> list[str]:
    """LLM이 단일 문자열 안에 여러 인용문을 묶어 반환하더라도 개별 근거 문장 리스트로 정규화한다."""
    if isinstance(raw_phrases, str):
        raw_phrases = [raw_phrases]
    if not isinstance(raw_phrases, list):
        return []
    normalized = []
    for item in raw_phrases:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text:
            continue
        if (text.startswith("'") and text.endswith("'") and "', '" in text) or (
            text.startswith('"') and text.endswith('"') and '", "' in text
        ):
            sep = "', '" if "', '" in text else '", "'
            parts = [p.strip(" '\"") for p in text.split(sep) if p.strip(" '\"")]
            normalized.extend(parts)
        elif "\n" in text:
            parts = [p.strip(" -•'\"") for p in text.splitlines() if p.strip(" -•'\"")]
            normalized.extend(parts)
        else:
            normalized.append(text.strip("'\" "))
    return [p for p in normalized if p]


def _build_news_digest(news_df: pd.DataFrame, max_items: int = 6) -> str:
    """Title과 Summary를 결합하여 요약 누락 기사를 보존하고 문맥 정확도를 높인다."""
    lines = []
    for _, row in news_df.head(max_items).iterrows():
        title = str(row.get("Title", "") or "").strip()
        summary = str(row.get("Summary", "") or "").strip()
        if title.lower() == "nan":
            title = ""
        if summary.lower() == "nan":
            summary = ""
        if len(summary) > 220:
            summary = summary[:217] + "..."
        if title and summary:
            lines.append(f"- {title}: {summary}")
        elif title:
            lines.append(f"- {title}")
        elif summary:
            lines.append(f"- {summary}")
    return "\n".join(lines)


def call_ollama(model_name: str, prompt: str, keep_alive: str = "15s") -> dict:
    """16GB RAM 환경을 고려해 컨텍스트를 4096으로 제한하고 순차 실행 후 빠르게 메모리를 반환한다."""
    print(f"    🤖 LLM 호출 중 ({model_name})...")
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": keep_alive,
        "options": {
            "num_ctx": 4096,
            "temperature": 0.2,
        },
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=240)
        if response.status_code == 200:
            result = response.json().get("response", "")
            return json.loads(result)
        elif response.status_code == 404:
            print(f"    ⚠️ '{model_name}' 모델이 설치되지 않았습니다. 기본 모델({MULTILINGUAL_EXTRACTOR_MODEL})로 우회합니다...")
            payload["model"] = MULTILINGUAL_EXTRACTOR_MODEL
            fallback_response = requests.post(OLLAMA_URL, json=payload, timeout=180)
            if fallback_response.status_code == 200:
                result = fallback_response.json().get("response", "")
                return json.loads(result)
        else:
            print(f"    ⚠️ Ollama 에러: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"    ⚠️ LLM 통신 실패 (Ollama가 실행 중인지 확인하세요): {e}")

    return {}


def analyze_signal_gap():
    print("🧠 3단계(다국어 Qwen2.5 -> 한국어 EXAONE3.5 & 영어 Llama3.1) 신호 괴리율 분석 파이프라인 시작...")

    if not INPUT_CSV.exists():
        print("❌ 수집된 RSS 데이터가 없습니다. 먼저 fetch_signal_gap_rss.py를 실행하세요.")
        return

    df = pd.read_csv(INPUT_CSV)
    results = {}
    stage1_cache = {}

    # =========================================================================
    # [Stage 1] 다국어 원문 분석 및 표준 영문 JSON 피벗 추출 (qwen2.5:7b)
    # 동일 모델을 연속 호출하여 모델 스왑 횟수를 최소화한 뒤, 완료 시 언로드한다.
    # =========================================================================
    print(f"\n[Stage 1/3] 다국어 원문 팩트 및 신호 괴리 추출 ({MULTILINGUAL_EXTRACTOR_MODEL})...")
    regions = list(df['Region'].unique())

    for idx, region in enumerate(regions):
        print(f"  -> [{region}] 권역 원문 분석 중...")
        region_df = df[df['Region'] == region]
        official_news = region_df[region_df['Source_Type'] == 'Official']
        independent_news = region_df[region_df['Source_Type'] == 'Independent']

        off_text = _build_news_digest(official_news, max_items=6)
        ind_text = _build_news_digest(independent_news, max_items=6)

        if not off_text or not ind_text:
            assessment = calculate_alert_assessment(
                discrepancy_score=0,
                official_count=len(official_news),
                independent_count=len(independent_news),
                evidence_count=0,
            )
            print(f"    ⚠️ {region}: 비교 자료가 부족함 — {assessment['alert_level']}")
            results[region] = {
                "pipeline_version": PIPELINE_VERSION,
                "model_used": None,
                "models_pipeline": {
                    "stage1_multilingual": None,
                    "stage2a_korean": None,
                    "stage2b_english": None,
                },
                "discrepancy_score": None,
                "narrative_differences": "공식 또는 독립 신호가 부족해 비교 확인이 필요함",
                "korean_headline": f"[{region}] 비교 신호 부족 — 추가 수집 및 확인 필요",
                "korean_briefing": "공식 발표 또는 독립 언론 측의 지정학·경제 비교 기사가 부족하여 경보 산정을 보류합니다.",
                "english_headline": f"[{region}] Insufficient comparative signals — verification required",
                "english_executive_summary": "Comparative official or independent media items are insufficient to establish a verified narrative gap.",
                "evidence_phrases": [],
                **assessment,
                "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            continue

        # 마지막 권역 처리 후에는 즉시 메모리에서 언로드("2s")하여 Stage 2 모델을 위한 RAM 확보
        keep_alive = "2s" if idx == len(regions) - 1 else "2m"
        prompt_s1 = PROMPT_STAGE1_EXTRACT.format(
            region=region,
            official_text=off_text,
            independent_text=ind_text,
        )
        analysis_s1 = call_ollama(MULTILINGUAL_EXTRACTOR_MODEL, prompt_s1, keep_alive=keep_alive)

        evidence_phrases = _normalize_evidence_phrases(analysis_s1.get("evidence_phrases"))
        assessment = calculate_alert_assessment(
            discrepancy_score=analysis_s1.get("discrepancy_score"),
            official_count=len(official_news),
            independent_count=len(independent_news),
            evidence_count=len(evidence_phrases),
        )
        narrative_en = analysis_s1.get("narrative_differences") or "LLM Analysis Failed"
        print(f"    ✅ 1단계 완료! 신호 괴리: {assessment['signal_gap_score']}/100 · 경보: {assessment['alert_level']}")

        stage1_cache[region] = {
            "discrepancy_score": analysis_s1.get("discrepancy_score"),
            "narrative_differences_en": narrative_en,
            "evidence_phrases": evidence_phrases,
            "assessment": assessment,
        }

    # =========================================================================
    # [Stage 2-A] 한국어 특화 모델 재분석 및 브리핑 생성 (exaone3.5:7.8b)
    # =========================================================================
    active_regions = list(stage1_cache.keys())
    if active_regions:
        print(f"\n[Stage 2-A/3] 한국어 특화 공급망·조기경보 브리핑 생성 ({KOREAN_SPECIALIST_MODEL})...")
        for idx, region in enumerate(active_regions):
            s1 = stage1_cache[region]
            ass = s1["assessment"]
            keep_alive = "2s" if idx == len(active_regions) - 1 else "2m"
            prompt_kr = PROMPT_STAGE2A_KOREAN.format(
                region=region,
                alert_level=ass["alert_level"],
                risk_signal_score=ass["risk_signal_score"],
                signal_gap_score=ass["signal_gap_score"],
                narrative_differences=s1["narrative_differences_en"],
                evidence_phrases=json.dumps(s1["evidence_phrases"], ensure_ascii=False),
            )
            kr_res = call_ollama(KOREAN_SPECIALIST_MODEL, prompt_kr, keep_alive=keep_alive)
            s1["korean_headline"] = kr_res.get("korean_headline") or f"[{region}] {ass['alert_level']} 단계 위험 신호 감지"
            s1["korean_briefing"] = kr_res.get("korean_briefing") or s1["narrative_differences_en"]
            print(f"    🇰🇷 [{region}] {s1['korean_headline']}")

    # =========================================================================
    # [Stage 2-B] 영어 특화 모델 정밀 분석 및 영문 보고서 생성 (llama3.1:8b)
    # =========================================================================
    if active_regions:
        print(f"\n[Stage 2-B/3] 글로벌 싱크탱크 영문 브리핑 정제 ({ENGLISH_SPECIALIST_MODEL})...")
        for idx, region in enumerate(active_regions):
            s1 = stage1_cache[region]
            ass = s1["assessment"]
            keep_alive = "2s" if idx == len(active_regions) - 1 else "2m"
            prompt_en = PROMPT_STAGE2B_ENGLISH.format(
                region=region,
                alert_level=ass["alert_level"],
                risk_signal_score=ass["risk_signal_score"],
                signal_gap_score=ass["signal_gap_score"],
                narrative_differences=s1["narrative_differences_en"],
                evidence_phrases=json.dumps(s1["evidence_phrases"], ensure_ascii=False),
            )
            en_res = call_ollama(ENGLISH_SPECIALIST_MODEL, prompt_en, keep_alive=keep_alive)
            s1["english_headline"] = en_res.get("english_headline") or f"[{region}] Risk Signal Alert: {ass['alert_level']}"
            s1["english_executive_summary"] = en_res.get("english_executive_summary") or s1["narrative_differences_en"]
            print(f"    🌐 [{region}] {s1['english_headline']}")

            # 최종 결과 병합 (기존 대시보드/노션 호환을 위해 narrative_differences에 한/영 병기 또는 한국어 브리핑 매핑)
            results[region] = {
                "pipeline_version": PIPELINE_VERSION,
                "model_used": f"{MULTILINGUAL_EXTRACTOR_MODEL} -> {KOREAN_SPECIALIST_MODEL} / {ENGLISH_SPECIALIST_MODEL}",
                "models_pipeline": {
                    "stage1_multilingual": MULTILINGUAL_EXTRACTOR_MODEL,
                    "stage2a_korean": KOREAN_SPECIALIST_MODEL,
                    "stage2b_english": ENGLISH_SPECIALIST_MODEL,
                },
                "discrepancy_score": s1["discrepancy_score"],
                "narrative_differences": s1["korean_briefing"],
                "narrative_differences_en": s1["narrative_differences_en"],
                "korean_headline": s1["korean_headline"],
                "korean_briefing": s1["korean_briefing"],
                "english_headline": s1["english_headline"],
                "english_executive_summary": s1["english_executive_summary"],
                "evidence_phrases": s1["evidence_phrases"],
                **ass,
                "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

    if results:
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 3단계 파이프라인 분석 결과가 저장되었습니다: {OUTPUT_JSON}")


if __name__ == "__main__":
    analyze_signal_gap()
