"""
중동 OSINT (텔레그램) 3단계 분석 파이프라인
1. Qwen 2.5 7B (다국어 전담 AI)가 텔레그램의 아랍어/페르시아어 원문을 표준 영문 요약으로 변환 및 위험 신호 추출
2. EXAONE 3.5 7.8B (한국어 전담 AI)가 한국 기업을 위한 공급망 리스크(유가, 해운) 경고 리포트 작성
3. Llama 3.1 8B (영어 전담 AI)가 글로벌 해운·에너지 이해관계자용 영문 브리핑 작성
"""

import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "signal_gap"
INPUT_CSV = DATA_DIR / "telegram_osint_latest.csv"
OUTPUT_TXT = DATA_DIR / "middle_east_risk_analysis.txt"

OLLAMA_URL = "http://localhost:11434/api/generate"


def call_ollama(model_name, prompt):
    print(f"    🤖 LLM 호출 중 ({model_name})...")
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "15s",
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
    print("🌍 중동 OSINT 텔레그램 3단계 분석 파이프라인 가동...")

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

    # 1단계: Qwen 2.5 7B (다국어/아랍어 분석 및 표준 영문 추출)
    print("\n[Step 1] 다국어 전담 AI (qwen2.5:7b) 아랍어 원문 분석 및 표준 영문 추출 중...")
    qwen_prompt = f"""You are a Middle East geopolitical risk-signal analyst.
Read the following intercepted Telegram messages from a Middle Eastern militant/IRGC affiliated channel.

Raw Messages:
{raw_texts}

Task:
1. Identify any observable risk signals concerning global oil supply chains, the Strait of Hormuz, the Red Sea, or maritime infrastructure.
2. Summarize the observed claims and operational signals in 3-4 sentences in objective English. Do not assert future events as certain.
"""
    canonical_en_analysis = call_ollama("qwen2.5:7b", qwen_prompt)
    print("  ✓ Qwen 2.5 다국어 분석 완료!")

    # 2-A단계: EXAONE 3.5 (한국어 특화 모델)
    print("\n[Step 2-A] 한국어 전담 AI (exaone3.5:7.8b) 한국 공급망 리스크 리포트 작성 중...")
    exaone_prompt = f"""당신은 한국 기업 전략기획실의 중동 공급망 리스크 분석가입니다.
아래는 다국어 AI가 아랍어 원문에서 추출한 중동 해협·무장단체 동향 영문 요약본입니다.

[표준 영문 동향 요약]
{canonical_en_analysis}

이 내용을 바탕으로, "한국 정유사 및 해운사(물류)가 점검해야 할 단기 공급망 위험 신호와 확인 필요 사항"을 3가지 글머리 기호로 한국어로 작성해주세요.
단정적 예측 표현(전쟁 발발 확정 등)은 금지하며, 관측된 위험 신호와 근거 중심으로 서술하세요.
"""
    exaone_analysis = call_ollama("exaone3.5:7.8b", exaone_prompt)
    print("  ✓ EXAONE 3.5 한국어 리포트 완료!")

    # 2-B단계: Llama 3.1 8B (영어 특화 모델)
    print("\n[Step 2-B] 영어 전담 AI (llama3.1:8b) 글로벌 싱크탱크 영문 브리핑 작성 중...")
    llama_prompt = f"""You are a senior maritime & energy risk analyst at an international think tank.
Based on the extracted risk signals below, compose a concise, neutral executive intelligence briefing (3 bullet points) in English.
Use strict early-warning and verification language only (no deterministic predictions).

[Extracted Signals]
{canonical_en_analysis}
"""
    llama_analysis = call_ollama("llama3.1:8b", llama_prompt)
    print("  ✓ Llama 3.1 글로벌 영문 브리핑 완료!")

    # 결과 저장
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("=== 중동 OSINT 공급망 리스크 보고서 (3-Tier Pipeline) ===\n\n")
        f.write("[1단계: 다국어 원문 표준 영문 추출 (qwen2.5:7b)]\n")
        f.write(canonical_en_analysis + "\n\n")
        f.write("[2-A단계: 한국 기업 공급망 대응 리포트 (exaone3.5:7.8b)]\n")
        f.write(exaone_analysis + "\n\n")
        f.write("[2-B단계: 글로벌 영문 인텔리전스 브리핑 (llama3.1:8b)]\n")
        f.write(llama_analysis + "\n")

    print(f"\n✅ 중동 리스크 3단계 분석 완료! 결과가 저장되었습니다: {OUTPUT_TXT}")


if __name__ == "__main__":
    analyze_middle_east_osint()
