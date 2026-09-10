"""
신호 분석 모듈 (analyze_signals.py) - 초안 v1
================================================

지금까지 수집한 신호들(Wikipedia 대중 관심도 + 정부 공식 발표)을 한데 모아
로컬 LLM(Ollama)에 넣고, 이슈별로 "지금 무슨 일이 벌어지고 있는지"와
"각국 정부의 공식 입장이 뭔지"를 종합한 한국어 분석 리포트를 생성합니다.

NOTE: 처음엔 SOLAR-10.7B(uncensored 버전)로 테스트했는데 한국어로 물어봐도
영어로만 답하는 문제가 있었습니다. 원인 확인해보니 SOLAR-10.7B-Instruct-v1.0
자체가 업스테이지 공식 모델 카드에 language: en으로 명시된 "영어 전용" 모델
이었습니다 (업스테이지가 한국 회사라고 해서 한국어 특화 모델은 아니었음).
-> Qwen2.5:7b로 테스트해보니 한국어 응답이 자연스럽게 나와서 기본 모델을
   Qwen2.5:7b로 바꿨습니다. (LG의 EXAONE 3.5도 후보로 남겨둠 - 아래
   --model 옵션으로 언제든 바꿔서 비교 가능)

입력 데이터 (없는 건 건너뛰고 있는 것만으로 분석합니다):
  - data/issues/issues_summary_*.csv           (Wikipedia 관심도 지수, 최신 파일 자동 탐색)
  - data/gov_announcements/by_issue_*.json      (정부 발표문, 이슈별 매칭, 최신 파일 자동 탐색)

출력:
  - reports/analysis_YYYYMMDD.md   (이슈별 한국어 분석 리포트, 신호 강한 이슈 순)

사용법:
    python scripts/analyze_signals.py
    python scripts/analyze_signals.py --model exaone3.5:7.8b   # 다른 모델로 비교
    python scripts/analyze_signals.py --min-intensity 0        # 신호 약한 이슈도 다 포함
"""

import argparse
import glob
import json
import os
import re
import time
from datetime import datetime

import pandas as pd
import requests

ISSUES_DIR = "data/issues"
GOV_DIR = "data/gov_announcements"
REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

OLLAMA_API = "http://localhost:11434/api/generate"
# NOTE (수정 사항 v1.2): Qwen2.5:7b와 EXAONE 3.5:7.8b를 같은 프롬프트로
# 비교 테스트해봤는데, EXAONE이 더 자연스럽고 뉘앙스 있는 한국어를 냈다
# (LG AI Research가 처음부터 한국어+영어 이중언어로 설계한 모델이라
# Qwen처럼 다국어 중 하나로 한국어를 지원하는 것과는 차이가 있었다).
# -> 기본 모델을 EXAONE 3.5로 변경. Qwen2.5는 --model 옵션으로 언제든
#    다시 비교 가능하도록 남겨둠.
DEFAULT_MODEL = "exaone3.5:7.8b"
REQUEST_TIMEOUT_SEC = 180  # CPU 추론이라 길게 잡음 (GPU 없는 노트북 기준)

# NOTE (수정 사항 v1.1 — 환각/hallucination 방지):
# 첫 실행 결과를 보니, 정부 발표 데이터가 프롬프트에 아예 없었는데도
# (data/gov_announcements/by_issue_*.json을 못 찾아서 gov_items=[] 상태였음)
# 모델이 "정부 발표문에 따르면..."이라면서 존재하지 않는 자료를 있는 것처럼
# 지어내는 걸 확인했다. 시스템 프롬프트에 "지어내지 마라"고만 써놓은 걸로는
# 부족했다 — [정부 입장] 섹션이 통째로 비어있으면 모델이 그 빈 공간을
# 자기가 사전에 학습한 일반 지식으로 채워버리는 경향이 있었다.
# -> (1) build_prompt()가 정부 발표가 없을 땐 "[정부 공식 발표] 수집된
#    데이터 없음"이라고 프롬프트에 명시적으로 박아넣고, (2) 시스템 프롬프트에
#    "그 경우엔 정부 입장을 반드시 '수집된 정부 발표 없음'이라고만 써라,
#    사전 지식으로 추측하지 마라"는 규칙을 못박았다.
SYSTEM_PROMPT = (
    "너는 국제정세를 분석하는 애널리스트다. 아래 규칙을 반드시 지켜라.\n"
    "1. 모든 답변은 반드시 한국어로만 작성한다. 영어 단어나 문장을 절대 섞지 않는다.\n"
    "2. 오직 아래 프롬프트에 실제로 주어진 신호(위키백과 관심도, 정부 발표문)만 근거로 "
    "분석한다. 네가 사전에 알고 있는 일반 지식으로 빈 곳을 채우지 않는다.\n"
    "3. [정부 공식 발표]에 '수집된 데이터 없음'이라고 되어 있으면, [정부 입장] 항목은 "
    "반드시 그대로 '수집된 정부 발표 없음 — 판단 불가'라고만 쓴다. "
    "'~것으로 보인다', '~할 것으로 시사된다' 같은 식으로 추측해서 채우지 않는다.\n"
    "4. 신호가 전반적으로 부족하면 '신호가 부족해 판단하기 어렵다'고 솔직하게 말한다.\n"
    "5. 아래 형식을 그대로 따른다:\n"
    "   [요약] 지금 이 이슈에서 무슨 일이 벌어지고 있는지 2~3문장\n"
    "   [정부 입장] 수집된 정부 발표에서 확인되는 공식 입장 (없으면 규칙 3 그대로 적용)\n"
    "   [주목할 점] 대중 관심도(위키백과 조회수)와 정부 발표 사이에 눈에 띄는 차이나 "
    "특이사항이 있으면 지적 (정부 발표 자체가 없으면 '특이사항 없음' 대신 "
    "'정부 발표 데이터 부재로 비교 불가'라고 쓴다)"
)


def find_latest(pattern):
    """glob 패턴에 맞는 파일 중 가장 최근(파일명 기준 정렬) 것을 반환. 없으면 None."""
    matches = sorted(glob.glob(pattern))
    return matches[-1] if matches else None


def load_wikipedia_summary():
    """
    data/issues/issues_summary_*.csv 중 최신 파일을 읽어서
    {issue_name: {"intensity":.., "article_count":..}} 형태로 반환.
    """
    path = find_latest(f"{ISSUES_DIR}/issues_summary_*.csv")
    if not path:
        print(f"⚠ Wikipedia 요약 CSV를 못 찾음 ({ISSUES_DIR}/issues_summary_*.csv) — 이 신호 없이 진행")
        return {}, None

    df = pd.read_csv(path)
    result = {}
    for _, row in df.iterrows():
        result[row["issue"]] = {
            "intensity": row.get("intensity", 0),
            "article_count": row.get("article_count", 0),
        }
    print(f"✓ Wikipedia 요약 로드: {path} ({len(result)}개 이슈)")
    return result, path


def load_gov_announcements():
    """
    data/gov_announcements/by_issue_*.json 중 최신 파일을 읽어서
    {issue_name: [announcement, ...]} 형태로 반환.
    """
    path = find_latest(f"{GOV_DIR}/by_issue_*.json")
    if not path:
        print(f"⚠ 정부 발표 JSON을 못 찾음 ({GOV_DIR}/by_issue_*.json) — 이 신호 없이 진행")
        return {}, None

    with open(path, "r", encoding="utf-8") as f:
        result = json.load(f)
    total = sum(len(v) for v in result.values())
    print(f"✓ 정부 발표 로드: {path} ({len(result)}개 이슈, 총 {total}건)")
    return result, path


def build_prompt(issue_name, wiki_signal, gov_items):
    """
    이슈 하나에 대해 LLM에 넣을 프롬프트를 조립합니다.
    신호가 하나도 없으면 None을 반환 (분석할 게 없다는 뜻).
    """
    if not wiki_signal and not gov_items:
        return None

    lines = [f"이슈: {issue_name}", ""]

    if wiki_signal:
        lines.append("[대중 관심도 신호 - 위키백과 조회수 기반]")
        lines.append(f"- 이슈 강도 지수: {wiki_signal['intensity']:.1f}/100")
        lines.append(f"- 최근 30일 총 조회수: {int(wiki_signal['article_count']):,}")
        lines.append("")

    # NOTE (v1.1): gov_items가 비어있을 때 이 섹션을 통째로 생략해버리면,
    # 모델이 "정부 발표문에 따르면..."이라고 없는 자료를 지어내는 걸
    # 실제로 확인했다 (환각). 그래서 없으면 없다고 프롬프트에 명시적으로
    # 박아넣는다 — 시스템 프롬프트 규칙 3과 짝을 이룬다.
    lines.append("[정부 공식 발표]")
    if gov_items:
        lines.append(f"(최근 매칭된 {len(gov_items)}건)")
        # 프롬프트가 너무 길어지지 않도록 최대 8건만 (제목 + pub_date만)
        for item in gov_items[:8]:
            lines.append(f"- ({item.get('source', '?')}, {item.get('pub_date', '?')}) {item.get('title', '')}")
        if len(gov_items) > 8:
            lines.append(f"  ...외 {len(gov_items) - 8}건 더")
    else:
        lines.append("수집된 데이터 없음")
    lines.append("")

    lines.append("위 신호들을 바탕으로 분석해줘. 주어지지 않은 내용은 절대 추측해서 채우지 마.")
    return "\n".join(lines)


def call_ollama(model, prompt, max_retries=2):
    """
    Ollama 로컬 API를 호출해서 분석 결과를 받아옵니다.
    CPU 추론이라 느릴 수 있어서 타임아웃을 넉넉하게 잡았습니다.
    """
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(
                OLLAMA_API,
                json={
                    "model": model,
                    "system": SYSTEM_PROMPT,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                timeout=REQUEST_TIMEOUT_SEC,
            )
            r.raise_for_status()
            return r.json().get("response", "").strip()

        except requests.exceptions.ConnectionError:
            print("  ✗ Ollama에 연결 실패 — 'ollama serve'가 실행 중인지 확인하세요.")
            return None
        except requests.exceptions.Timeout:
            print(f"  ✗ 시도 {attempt}/{max_retries}: 응답 시간 초과 ({REQUEST_TIMEOUT_SEC}초)")
            if attempt < max_retries:
                time.sleep(3)
        except requests.exceptions.RequestException as e:
            print(f"  ✗ 시도 {attempt}/{max_retries}: {str(e)[:150]}")
            if attempt < max_retries:
                time.sleep(3)

    return None


def main():
    parser = argparse.ArgumentParser(description="수집된 신호를 로컬 LLM으로 분석해서 한국어 리포트 생성")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                         help=f"사용할 Ollama 모델 이름 (기본값: {DEFAULT_MODEL})")
    parser.add_argument("--min-intensity", type=float, default=1.0,
                         help="이 값 미만인 이슈는 건너뜀 (기본값: 1.0, 0으로 주면 다 포함)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🧠 Signal Analysis (로컬 LLM 기반)")
    print(f"   모델: {args.model}")
    print("=" * 60)

    wiki_data, wiki_path = load_wikipedia_summary()
    gov_data, gov_path = load_gov_announcements()

    all_issues = sorted(set(wiki_data.keys()) | set(gov_data.keys()))
    if not all_issues:
        print("\n✗ 분석할 신호가 하나도 없습니다. 먼저 issue_data_collector.py와 "
              "gov_announcements_collector.py를 실행하세요.")
        return

    # 신호가 강한 이슈부터 (위키 강도 기준, 없으면 정부 발표 건수 기준)
    def sort_key(issue):
        w = wiki_data.get(issue, {}).get("intensity", 0)
        g = len(gov_data.get(issue, []))
        return (w, g)

    all_issues.sort(key=sort_key, reverse=True)

    report_sections = []
    analyzed_count = 0

    for issue_name in all_issues:
        wiki_signal = wiki_data.get(issue_name)
        gov_items = gov_data.get(issue_name, [])

        intensity = wiki_signal["intensity"] if wiki_signal else 0
        if intensity < args.min_intensity and not gov_items:
            continue  # 신호 자체가 거의 없는 이슈는 건너뜀 (LLM 호출 낭비 방지)

        prompt = build_prompt(issue_name, wiki_signal, gov_items)
        if not prompt:
            continue

        print(f"\n📊 분석 중: {issue_name} (강도 {intensity:.1f}, 정부발표 {len(gov_items)}건)")
        analysis = call_ollama(args.model, prompt)

        if analysis is None:
            print(f"   ✗ 분석 실패 — 건너뜀")
            continue

        print(f"   ✓ 완료 ({len(analysis)}자)")
        analyzed_count += 1

        report_sections.append(
            f"## {issue_name}\n\n"
            f"- 이슈 강도: {intensity:.1f}/100"
            + (f" · 정부 발표 {len(gov_items)}건" if gov_items else "")
            + f"\n\n{analysis}\n"
        )

    if not report_sections:
        print("\n✗ 분석된 이슈가 없습니다 (--min-intensity 낮춰서 다시 시도해보세요).")
        return

    today = datetime.now().strftime("%Y%m%d")
    report_path = f"{REPORTS_DIR}/analysis_{today}.md"
    header = (
        f"# 국제정세 분석 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
        f"- 사용 모델: {args.model}\n"
        f"- 분석된 이슈: {analyzed_count}개\n"
        f"- 데이터 출처: "
        + (f"{os.path.basename(wiki_path)}" if wiki_path else "")
        + (f", {os.path.basename(gov_path)}" if gov_path else "")
        + "\n\n---\n\n"
    )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(report_sections))

    print("\n" + "=" * 60)
    print(f"✅ 리포트 저장 완료: {report_path}")
    print(f"   ({analyzed_count}개 이슈 분석)")
    print("=" * 60)


if __name__ == "__main__":
    main()
