"""
fetch_google_trends.py — 국가별 위험 키워드 구글 트렌드 수집기
======================================================================

조기경보 관점:
  구글 트렌드는 '검열된 말'이 아닌 '실제 행동(검색)'을 측정한다.
  정부가 침묵해도 국민이 무엇을 두려워하는지 검색량으로 드러난다.

  예) 러시아 동원령 직후: "징집 면제", "국경 넘기", "비행기 표" 검색 폭증
      중국 봉쇄 시기: "생필품", "Run(润)", "이민" 급증
      중동 위기: "항공편", "대피", "연료" 급등

수집 논리:
  - pytrends 라이브러리를 통해 Google Trends Unofficial API를 호출한다.
  - 국가별 위험 감지용 키워드 세트를 주제 카테고리별로 정의한다.
  - 최근 90일 대비 현재 검색 급등 여부를 수치화한다.
  - 결과를 CSV + JSON으로 저장하며, 대시보드 및 경보 로직과 연동한다.

주의:
  - pytrends는 Google의 비공식 API를 사용하므로 과다 요청 시 429가 발생할 수 있다.
  - 요청 간 최소 3초 딜레이를 지킨다.
  - 한 번에 최대 5개 키워드만 비교 가능하다 (Google Trends 제한).

저장 위치:
  data/google_trends/trends_latest.csv
  data/google_trends/trends_summary.json
  data/google_trends/history/trends_{timestamp}.csv

사용법:
  python scripts/fetch_google_trends.py                   # 기본 실행 (모든 국가·키워드)
  python scripts/fetch_google_trends.py --country RU      # 러시아만
  python scripts/fetch_google_trends.py --country CN KR   # 중국, 한국
  python scripts/fetch_google_trends.py --days 30         # 최근 30일 기준
  python scripts/fetch_google_trends.py --top-only        # 급등 키워드만 출력
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ----- 경로 설정 -----
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "google_trends"
HISTORY_DIR = DATA_DIR / "history"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ======================================================================
# 조기경보 키워드 정의
# ======================================================================
# 각 국가별로 '국민의 공포와 불안 행동'을 드러내는 키워드를 설정한다.
# 단순 뉴스 토픽이 아니라, 위기 상황에서 현지인이 실제로 검색하는 단어들.
# ======================================================================

COUNTRY_PROFILES: dict[str, dict] = {
    "RU": {
        "name": "러시아",
        "geo": "RU",
        "lang": "ru",
        "keywords": [
            # 징집·병역 회피 관련
            ["как избежать мобилизации", "выезд из России", "Финляндия граница", "эмиграция", "военный билет"],
            # 경제·물가 충격 관련
            ["санкции", "доллар курс", "инфляция", "дефицит товаров", "закрытие банков"],
            # 전쟁 피로·반전 여론 관련
            ["конец войны", "мирные переговоры", "потери армии", "антивоенный", "арест протест"],
        ],
        "risk_theme": "군사동원·경제제재 충격·전쟁피로",
        "supply_chain_relevance": "에너지·곡물 공급망 핵심",
    },
    "CN": {
        "name": "중국",
        "geo": "CN",
        "lang": "zh-CN",
        "keywords": [
            # 경제·실업·탈출 의향 관련
            ["失业", "润", "移民", "股市暴跌", "存款"],
            # 대만 분쟁·군사 긴장 관련
            ["台湾", "战争", "封锁", "军事演习", "台海"],
            # 봉쇄·공급망 혼란 관련
            ["断供", "物价上涨", "房价", "经济衰退", "汇率"],
        ],
        "risk_theme": "경제위기·대만긴장·부동산버블",
        "supply_chain_relevance": "반도체·배터리·희토류 핵심",
    },
    "IR": {
        "name": "이란",
        "geo": "IR",
        "lang": "fa",
        "keywords": [
            # 경제·환율 충격
            ["دلار", "تورم", "بیکاری", "اعتراض", "فرار سرمایه"],
            # 분쟁·봉쇄 위기
            ["جنگ", "حمله", "تنگه هرمز", "نفت", "تحریم"],
        ],
        "risk_theme": "경제제재·원유봉쇄·정치불안",
        "supply_chain_relevance": "에너지·호르무즈 해협",
    },
    "KR": {
        "name": "한국 (대조군)",
        "geo": "KR",
        "lang": "ko",
        "keywords": [
            # 수출·공급망 충격 체감 지표
            ["수출 감소", "반도체 위기", "무역적자", "원달러 환율", "물가"],
            # 북한 리스크 관련
            ["북한 도발", "전쟁 위기", "대피소", "미사일", "안보"],
        ],
        "risk_theme": "한국 내 공급망·안보 체감도 (대조군)",
        "supply_chain_relevance": "한국 공급망 영향 직접 측정",
    },
    "SA": {
        "name": "사우디아라비아",
        "geo": "SA",
        "lang": "ar",
        "keywords": [
            # 에너지·후티·지역 긴장
            ["الحوثيون", "هجوم", "أرامكو", "النفط", "اليمن"],
            # 경제·물가
            ["تضخم", "بطالة", "الريال", "أسعار النفط", "اقتصاد"],
        ],
        "risk_theme": "후티 위협·에너지 수출 리스크",
        "supply_chain_relevance": "한국 에너지 수입 핵심",
    },
    "JP": {
        "name": "일본 (대조군)",
        "geo": "JP",
        "lang": "ja",
        "keywords": [
            # 경제·엔화·지정학
            ["円安", "物価上昇", "景気後退", "中国リスク", "台湾有事"],
        ],
        "risk_theme": "엔화약세·공급망·대만리스크",
        "supply_chain_relevance": "반도체 소재·부품 공급망",
    },
}


def fetch_trends_for_country(
    country_code: str,
    profile: dict,
    timeframe: str = "today 3-m",
    delay: float = 4.0,
) -> list[dict]:
    """한 국가에 대해 모든 키워드 그룹의 트렌드 데이터를 수집한다."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("  ✗ pytrends 미설치. 'pip install pytrends' 실행 후 재시도.")
        return []

    results: list[dict] = []
    geo = profile["geo"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pytrends = TrendReq(hl=profile.get("lang", "en"), tz=540)

    for kw_group in profile["keywords"]:
        print(f"    키워드 그룹: {kw_group}")
        try:
            pytrends.build_payload(kw_group, cat=0, timeframe=timeframe, geo=geo, gprop="")
            df = pytrends.interest_over_time()

            if df.empty:
                print(f"      ⚠️  데이터 없음 (해당 기간 트렌드 없음)")
                time.sleep(delay)
                continue

            # 최근 7일 평균 vs 전체 기간 평균 비교로 '급등률' 계산
            for kw in kw_group:
                if kw not in df.columns:
                    continue
                series = df[kw].dropna()
                if series.empty:
                    continue

                recent_7d = series.tail(7).mean()
                period_avg = series.mean()
                period_max = series.max()
                surge_ratio = round((recent_7d / period_avg) if period_avg > 0 else 0.0, 2)

                # 급등 신호 판정
                if surge_ratio >= 2.0:
                    signal = "SURGE"        # 최근 7일 평균이 전체 평균의 2배 이상
                elif surge_ratio >= 1.5:
                    signal = "rising"       # 1.5배 이상
                elif surge_ratio >= 1.2:
                    signal = "slight_up"
                else:
                    signal = "stable"

                results.append({
                    "country_code": country_code,
                    "country_name": profile["name"],
                    "risk_theme": profile["risk_theme"],
                    "supply_chain_relevance": profile["supply_chain_relevance"],
                    "keyword": kw,
                    "timeframe": timeframe,
                    "period_avg_score": round(float(period_avg), 1),
                    "recent_7d_avg_score": round(float(recent_7d), 1),
                    "period_max_score": int(period_max),
                    "surge_ratio": surge_ratio,
                    "signal": signal,
                    "fetched_at": now_str,
                })

            time.sleep(delay)

        except Exception as e:
            err = str(e)
            print(f"      ✗ 수집 실패: {err[:80]}")
            if "429" in err or "Too Many" in err:
                print(f"      🔴 Rate limit 감지 — {delay * 5:.0f}초 대기 후 재개")
                time.sleep(delay * 5)
            else:
                time.sleep(delay)
            continue

    return results


def save_results(all_results: list[dict]) -> None:
    """수집 결과를 CSV + JSON으로 저장한다."""
    if not all_results:
        print("\n⚠️  저장할 데이터가 없습니다.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fieldnames = [
        "country_code", "country_name", "risk_theme", "supply_chain_relevance",
        "keyword", "timeframe", "period_avg_score", "recent_7d_avg_score",
        "period_max_score", "surge_ratio", "signal", "fetched_at",
    ]

    # 최신본
    latest_csv = DATA_DIR / "trends_latest.csv"
    with open(latest_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    print(f"\n✅ CSV 저장: {latest_csv} ({len(all_results)}건)")

    # 이력 보관
    history_csv = HISTORY_DIR / f"trends_{timestamp}.csv"
    with open(history_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)

    # 요약 JSON (급등 신호만 추려서 경보 판단에 활용)
    surge_items = [r for r in all_results if r["signal"] in ("SURGE", "rising")]
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_keywords_tracked": len(all_results),
        "surge_count": len(surge_items),
        "surge_alerts": surge_items,
        "by_country": {},
    }
    for r in all_results:
        cc = r["country_code"]
        if cc not in summary["by_country"]:
            summary["by_country"][cc] = {
                "country_name": r["country_name"],
                "total": 0,
                "surge": 0,
                "top_keywords": [],
            }
        summary["by_country"][cc]["total"] += 1
        if r["signal"] in ("SURGE", "rising"):
            summary["by_country"][cc]["surge"] += 1
            summary["by_country"][cc]["top_keywords"].append({
                "keyword": r["keyword"],
                "surge_ratio": r["surge_ratio"],
                "signal": r["signal"],
            })

    summary_json = DATA_DIR / "trends_summary.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"✅ 요약 JSON 저장: {summary_json}")

    # 결과 요약 출력
    print("\n" + "=" * 60)
    print("📊 국가별 위험 키워드 급등 현황")
    print("=" * 60)
    for cc, info in summary["by_country"].items():
        surge = info["surge"]
        total = info["total"]
        bar = "🔴" if surge >= 3 else ("🟠" if surge >= 1 else "🟢")
        print(f"  {bar} [{cc}] {info['country_name']:12s} — 급등 {surge}/{total}개")
        for kw_info in info["top_keywords"][:3]:
            print(f"       ↑ '{kw_info['keyword']}' (x{kw_info['surge_ratio']})")


def main() -> None:
    parser = argparse.ArgumentParser(description="국가별 구글 트렌드 위험 키워드 조기경보 수집기")
    parser.add_argument("--country", nargs="+", default=list(COUNTRY_PROFILES.keys()),
                        help=f"수집할 국가 코드 (기본: 전체). 선택: {list(COUNTRY_PROFILES.keys())}")
    parser.add_argument("--days", type=int, default=90, choices=[7, 30, 90],
                        help="분석 기준 기간 (기본: 90일)")
    parser.add_argument("--delay", type=float, default=4.0,
                        help="요청 간 딜레이(초). Google 차단 방지를 위해 4초 이상 권장 (기본: 4)")
    parser.add_argument("--top-only", action="store_true",
                        help="급등(SURGE/rising) 신호가 있는 키워드만 출력")
    args = parser.parse_args()

    # 기간 문자열 변환
    days_map = {7: "now 7-d", 30: "today 1-m", 90: "today 3-m"}
    timeframe = days_map[args.days]

    print("=" * 60)
    print("🔍 Google Trends 위험 키워드 조기경보 수집 시작")
    print(f"   대상 국가: {args.country}")
    print(f"   분석 기간: {args.days}일 ({timeframe})")
    print(f"   요청 딜레이: {args.delay}초")
    print("=" * 60)

    all_results: list[dict] = []

    for cc in args.country:
        cc = cc.upper()
        if cc not in COUNTRY_PROFILES:
            print(f"\n⚠️  알 수 없는 국가 코드: {cc} (지원: {list(COUNTRY_PROFILES.keys())})")
            continue

        profile = COUNTRY_PROFILES[cc]
        print(f"\n[{cc}] {profile['name']} 수집 중...")
        print(f"  위험 주제: {profile['risk_theme']}")
        print(f"  공급망 관련성: {profile['supply_chain_relevance']}")

        results = fetch_trends_for_country(cc, profile, timeframe=timeframe, delay=args.delay)
        all_results.extend(results)
        print(f"  ✓ {len(results)}개 키워드 트렌드 수집 완료")

    if args.top_only:
        all_results = [r for r in all_results if r["signal"] in ("SURGE", "rising")]

    save_results(all_results)


if __name__ == "__main__":
    main()

