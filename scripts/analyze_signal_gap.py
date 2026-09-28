"""
신호 괴리율(Signal Gap) 및 조기경보 분석 파이프라인.

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

# 모델 라우팅 매핑 (project-handoff.md 기준)
REGION_MODELS = {
    "Russia": "second_constantine/yandex-gpt-5-lite:8b", # 설치된 정확한 모델명으로 수정
    "China": "qwen2.5:7b",                   
    "Middle_East": "falcon3:7b",             # 아직 ollama에 pull 안 된 상태일 수 있음
    "Global_South": "exaone3.5:7.8b"         
}

OLLAMA_URL = "http://localhost:11434/api/generate"
DATA_DIR = Path(__file__).parent.parent / "data" / "signal_gap"
INPUT_CSV = DATA_DIR / "rss_signal_gap_latest.csv"
OUTPUT_JSON = DATA_DIR / "signal_gap_analysis.json"

# 산식 버전을 결과에 함께 남겨 백테스트와 사람 검수 때 기준 변경을 추적한다.
SCORING_VERSION = "early-warning-v1"


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

PROMPT_TEMPLATE = """You are a geopolitical risk-signal analyst.
Below are recent news summaries from an Official State Media and an Independent/Exiled Media concerning the same region.

[Official State Media]
{official_text}

[Independent/Exiled Media]
{independent_text}

Task:
1. Compare only the supplied narratives. Calculate a 'Signal Gap Discrepancy Score' from 0 to 100. (0 = identical narrative, 100 = completely opposing narratives or extreme censorship).
2. Write a brief summary (2-3 sentences) explaining the observed differences and cite up to two short evidence phrases from the supplied text.
3. Do not state or imply that a future event is certain. If the supplied material is insufficient, say that confirmation is needed.

You MUST respond strictly in the following JSON format without any markdown blocks or extra text:
{{
  "discrepancy_score": 85,
  "narrative_differences": "Explanation here...",
  "evidence_phrases": ["phrase from supplied text"]
}}
"""

def call_ollama(model_name, prompt):
    print(f"    🤖 LLM 호출 중 ({model_name})...")
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "format": "json" # Ollama JSON 모드 강제
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if response.status_code == 200:
            result = response.json().get("response", "")
            return json.loads(result)
        elif response.status_code == 404:
            print(f"    ⚠️ '{model_name}' 모델이 설치되지 않았습니다. 기본 모델(qwen2.5:7b)로 우회합니다...")
            payload["model"] = "qwen2.5:7b"
            fallback_response = requests.post(OLLAMA_URL, json=payload, timeout=120)
            if fallback_response.status_code == 200:
                result = fallback_response.json().get("response", "")
                return json.loads(result)
        else:
            print(f"    ⚠️ Ollama 에러: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"    ⚠️ LLM 통신 실패 (Ollama가 실행 중인지 확인하세요): {e}")
    
    # Fallback response
    return {"discrepancy_score": None, "narrative_differences": "LLM Analysis Failed"}

def analyze_signal_gap():
    print("🧠 6대 네이티브 LLM 기반 신호 괴리율(Signal Gap) 분석 시작...")
    
    if not INPUT_CSV.exists():
        print("❌ 수집된 RSS 데이터가 없습니다. 먼저 fetch_signal_gap_rss.py를 실행하세요.")
        return
        
    df = pd.read_csv(INPUT_CSV)
    results = {}
    
    for region in df['Region'].unique():
        print(f"\n[{region}] 권역 분석 준비 중...")
        
        region_df = df[df['Region'] == region]
        official_news = region_df[region_df['Source_Type'] == 'Official']
        independent_news = region_df[region_df['Source_Type'] == 'Independent']
        
        # 텍스트 병합 (상위 5개 기사만 요약용으로 추출하여 토큰 제한 방지)
        off_text = "\n".join(official_news['Summary'].dropna().head(5).tolist())
        ind_text = "\n".join(independent_news['Summary'].dropna().head(5).tolist())
        
        if not off_text or not ind_text:
            assessment = calculate_alert_assessment(
                discrepancy_score=0,
                official_count=len(official_news),
                independent_count=len(independent_news),
                evidence_count=0,
            )
            print(f"    ⚠️ {region}: 비교 자료가 부족함 — {assessment['alert_level']}")
            results[region] = {
                "model_used": None,
                "discrepancy_score": None,
                "narrative_differences": "공식 또는 독립 신호가 부족해 비교 확인이 필요함",
                "evidence_phrases": [],
                **assessment,
                "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            continue
            
        model = REGION_MODELS.get(region, "mistral-nemo")
        prompt = PROMPT_TEMPLATE.format(official_text=off_text, independent_text=ind_text)
        
        analysis = call_ollama(model, prompt)
        
        evidence_phrases = analysis.get("evidence_phrases") or []
        if not isinstance(evidence_phrases, list):
            evidence_phrases = []
        assessment = calculate_alert_assessment(
            discrepancy_score=analysis.get("discrepancy_score"),
            official_count=len(official_news),
            independent_count=len(independent_news),
            evidence_count=len(evidence_phrases),
        )
        print(f"    ✅ 분석 완료! 신호 괴리: {assessment['signal_gap_score']}/100 · 경보: {assessment['alert_level']}")
        print(f"    📝 요약: {analysis.get('narrative_differences')}")
        
        results[region] = {
            "model_used": model,
            "discrepancy_score": analysis.get('discrepancy_score'),
            "narrative_differences": analysis.get('narrative_differences'),
            "evidence_phrases": evidence_phrases,
            **assessment,
            "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    if results:
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 분석 결과가 저장되었습니다: {OUTPUT_JSON}")

if __name__ == "__main__":
    analyze_signal_gap()
