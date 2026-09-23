"""
test_language_models.py
------------------------
아직 실제로 톤 분류를 테스트해본 적 없는 3개 언어 모델(일본어/러시아어/아랍어)을
간단한 샘플 기사로 실행해보는 스크립트. `ollama serve`가 켜져 있는 상태에서
프로젝트 루트의 `prototype_all_in_one.py`가 정의한 MODEL_BY_LANGUAGE/프롬프트를
그대로 재사용한다.

실행:
    ollama serve   # 다른 터미널에서 켜두기
    python tests/test_language_models.py

CPU 전용 환경에서는 모델 하나당(특히 8B급) 수십 초~2분 정도 걸릴 수 있다.
"""

import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from prototype_all_in_one import MODEL_BY_LANGUAGE, _call_ollama, TONE_PROMPT

# 언어별 샘플 기사 (실제 뉴스 문장을 흉내낸 간단한 예시)
SAMPLES = {
    "ja": {
        "title": "米国、対中関税を追加で引き上げ",
        "summary": "米政府は中国からの輸入品に対する追加関税を発表した。専門家は物価上昇への影響を懸念している。",
    },
    "ru": {
        "title": "США вводят новые пошлины на импорт из Канады",
        "summary": "Правительство США объявило о повышении тарифов на канадские товары. Аналитики предупреждают о риске роста цен.",
    },
    "ar": {
        "title": "الولايات المتحدة ترفع الرسوم الجمركية على الواردات",
        "summary": "أعلنت الحكومة الأمريكية عن زيادة الرسوم الجمركية على السلع المستوردة. ويحذر المحللون من ارتفاع الأسعار.",
    },
    # 이미 테스트된 3개도 회귀 확인용으로 같이 돌려봄
    "en": {
        "title": "US raises tariffs on imports",
        "summary": "The US government announced higher tariffs on imported goods. Analysts warn of price increases.",
    },
    "ko": {
        "title": "미국, 수입품 관세 인상 발표",
        "summary": "미국 정부가 수입품에 대한 관세를 인상한다고 발표했다. 전문가들은 물가 상승을 우려하고 있다.",
    },
    "zh": {
        "title": "美国对进口商品加征关税",
        "summary": "美国政府宣布对进口商品提高关税。分析人士警告称此举可能导致物价上涨。",
    },
    # 유럽 주요국 (mistral-nemo 검증용)
    "de": {
        "title": "USA erheben zusätzliche Zölle auf Importe",
        "summary": "Die US-Regierung hat zusätzliche Zölle auf Importwaren angekündigt. Analysten warnen vor steigenden Verbraucherpreisen.",
    },
    "fr": {
        "title": "Les États-Unis augmentent les droits de douane sur les importations",
        "summary": "Le gouvernement américain a annoncé une hausse des droits de douane sur les produits importés. Les analystes mettent en garde contre une hausse des prix.",
    },
    "it": {
        "title": "Gli Stati Uniti aumentano i dazi sulle importazioni",
        "summary": "Il governo statunitense ha annunciato un aumento dei dazi sui beni importati. Gli analisti mettono in guardia contro il rischio di aumento dei prezzi.",
    },
}

TARGET_LANGUAGES = ["ja", "ru", "ar", "en", "ko", "zh", "de", "fr", "it"]


def main():
    targets = [arg for arg in sys.argv[1:] if arg in SAMPLES] or TARGET_LANGUAGES
    print(f"{'언어':<6}{'모델':<45}{'결과':<10}{'소요시간':<10}")
    print("-" * 90)
    for lang in targets:
        model = MODEL_BY_LANGUAGE.get(lang, "mistral-nemo:latest")
        sample = SAMPLES[lang]
        prompt = TONE_PROMPT.format(title=sample["title"], summary=sample["summary"])

        start = time.time()
        try:
            result = _call_ollama(model, prompt, temperature=0.3)
            elapsed = time.time() - start
            label = result.get("label", "?")
            evidence = result.get("evidence_quote", "")
            print(f"{lang:<6}{model:<45}{label:<10}{elapsed:.1f}s")
            print(f"       근거: {evidence}")
        except Exception as e:
            elapsed = time.time() - start
            print(f"{lang:<6}{model:<45}{'실패':<10}{elapsed:.1f}s")
            print(f"       에러: {e}")
        print()


if __name__ == "__main__":
    main()
