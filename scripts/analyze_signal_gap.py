"""
신호 괴리율(Signal Gap) 분석 파이프라인
- 수집된 RSS 데이터(관영 vs 독립)를 6대 네이티브 로컬 LLM에 주입하여 괴리율 점수(0~100)를 산출합니다.
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

PROMPT_TEMPLATE = """You are a geopolitical intelligence analyst.
Below are recent news summaries from an Official State Media and an Independent/Exiled Media concerning the same region.

[Official State Media]
{official_text}

[Independent/Exiled Media]
{independent_text}

Task:
1. Compare the narratives. Calculate a 'Signal Gap Discrepancy Score' from 0 to 100. (0 = identical narrative, 100 = completely opposing narratives or extreme censorship).
2. Write a brief summary (2-3 sentences) explaining the key differences in their reporting.

You MUST respond strictly in the following JSON format without any markdown blocks or extra text:
{{
  "discrepancy_score": 85,
  "narrative_differences": "Explanation here..."
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
            print(f"    ⚠️ {region}: 관영 매체 또는 독립 매체의 데이터가 부족하여 비교 불가")
            continue
            
        model = REGION_MODELS.get(region, "mistral-nemo")
        prompt = PROMPT_TEMPLATE.format(official_text=off_text, independent_text=ind_text)
        
        analysis = call_ollama(model, prompt)
        
        print(f"    ✅ 분석 완료! 괴리율 점수: {analysis.get('discrepancy_score')}/100")
        print(f"    📝 요약: {analysis.get('narrative_differences')}")
        
        results[region] = {
            "model_used": model,
            "discrepancy_score": analysis.get('discrepancy_score'),
            "narrative_differences": analysis.get('narrative_differences'),
            "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    if results:
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 분석 결과가 저장되었습니다: {OUTPUT_JSON}")

if __name__ == "__main__":
    analyze_signal_gap()
