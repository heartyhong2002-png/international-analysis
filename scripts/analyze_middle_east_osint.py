"""
중동 OSINT (텔레그램) 분석망 프로토타입
1. Falcon3 (중동 전담 AI)가 텔레그램의 아랍어/페르시아어 원문을 영어로 번역 및 군사적 의도 분석
2. EXAONE 3.5 (한국어 전담 AI)가 그 결과를 바탕으로 한국 기업을 위한 공급망 리스크(유가, 해운) 경고 리포트 작성
"""

import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).parent.parent / "data" / "signal_gap"
INPUT_CSV = DATA_DIR / "telegram_osint_latest.csv"
OUTPUT_TXT = DATA_DIR / "middle_east_risk_analysis.txt"

OLLAMA_URL = "http://localhost:11434/api/generate"

def call_ollama(model_name, prompt):
    print(f"    🤖 LLM 호출 중 ({model_name})...")
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            return f"[Error] {response.status_code}"
    except Exception as e:
        return f"[Error] {e}"

def analyze_middle_east_osint():
    print("🌍 중동 OSINT 텔레그램 분석 파이프라인 가동...")
    
    if not INPUT_CSV.exists():
        print("⚠️ 텔레그램 데이터가 없습니다. 먼저 fetch_telegram_public.py를 실행하세요.")
        return

    df = pd.read_csv(INPUT_CSV)
    
    # 중동 데이터 필터링 (후티 반군 긴급 타겟팅)
    me_df = df[df['Region'].isin(['Yemen_Houthi'])]
    if me_df.empty:
        print("⚠️ 중동 관련 수집 데이터가 없습니다.")
        return
        
    raw_texts = "\n".join([f"- {row['Message_Content']}" for _, row in me_df.iterrows()])
    
    # 1단계: Falcon3 7B (UAE 아랍어/중동 특화 모델)
    print("\n[Step 1] 중동 전담 AI (Falcon3) 분석 중...")
    falcon_prompt = f"""You are a Middle East geopolitical intelligence expert.
Read the following intercepted Telegram messages from a Middle Eastern militant/IRGC affiliated channel.

Raw Messages:
{raw_texts}

Task:
1. Identify if there are any threats to global oil supply chains, the Strait of Hormuz, the Red Sea, or infrastructure.
2. Summarize the military or political intent in 3-4 sentences in English.
"""
    falcon_analysis = call_ollama("falcon3:7b", falcon_prompt)
    print("  ✓ Falcon3 분석 완료!")
    
    # 2단계: EXAONE 3.5 (한국어 특화 모델)
    print("\n[Step 2] 한국어 전담 AI (EXAONE 3.5) 전략 리포트 작성 중...")
    exaone_prompt = f"""당신은 한국 기업 전략기획실의 중동 리스크 전문가입니다.
아래는 현지 아랍어 AI가 번역 및 분석한 중동 무장단체의 텔레그램 동향 요약본입니다.

[현지 동향 요약]
{falcon_analysis}

이 내용을 바탕으로, "한국 정유사 및 해운사(물류)가 대비해야 할 단기 리스크"를 3가지 글머리 기호로 알기 쉽게 한국어로 요약해주세요.
"""
    exaone_analysis = call_ollama("exaone3.5:7.8b", exaone_prompt)
    print("  ✓ EXAONE 한국어 리포트 완료!")
    
    # 결과 저장
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("=== 중동 OSINT 공급망 리스크 보고서 ===\n\n")
        f.write("[현지 AI 분석 원문 (Falcon3)]\n")
        f.write(falcon_analysis + "\n\n")
        f.write("[한국 기업 대응 리포트 (EXAONE)]\n")
        f.write(exaone_analysis + "\n")
        
    print(f"\n✅ 중동 리스크 분석 완료! 결과가 저장되었습니다: {OUTPUT_TXT}")

if __name__ == "__main__":
    analyze_middle_east_osint()
