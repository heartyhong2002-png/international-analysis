"""
UN Comtrade 무료(Preview) API로 반도체(HS 8541/8542) 무역 데이터 수집
- 트럼프 2기 취임(2025년 1월) 이후 ~ 현재까지, 월별
- 회원가입/구독키 없이 쓸 수 있는 previewFinalData()를 사용합니다

** 이 스크립트는 준기님 컴퓨터에서 직접 실행해야 합니다 **
(클라우드 세션에서는 외부 API 접속이 막혀 있어 Claude가 대신 실행할 수 없습니다)

--------------------------------------------------------------------------
v2에서 수정한 내용 (이전 버전이 "총 0건 수집"으로 끝난 원인):
이전 버전은 period를 "202501,202502,...,202509" 처럼 콤마로 여러 달을 한 번에,
flowCode도 "M,X"로 한 번에 묶어서 요청했습니다. 그런데 uncomtrade가 공식
저장소(comtradeapicall)에 올려둔 실제 동작하는 예시는 previewFinalData()를
호출할 때 period='202205' (달 1개), flowCode='M' (방향 1개) 처럼 항상
단일 값만 씁니다 - 콤마로 여러 개를 묶는 batch 조회는 유료(getFinalData) 쪽
예시에서만 등장합니다. 즉 무료 preview API는 period/flowCode를 여러 개
합쳐서 요청하면 (에러 없이) 그냥 빈 결과를 돌려주는 것으로 보입니다.

그래서 이번 버전은 달 하나 x 방향(수입/수출) 하나 x 품목코드 하나, 이렇게
전부 쪼개서 훨씬 많은 횟수를 호출합니다. 대신 매 호출 사이에 약간의 지연을
넣어 과도한 연속 요청으로 인한 차단을 피합니다.
--------------------------------------------------------------------------

사용 전 설치:
    pip install comtradeapicall pandas

실행:
    python scripts/fetch_uncomtrade_semiconductors.py
"""

import json
import time
from datetime import datetime
from pathlib import Path

import comtradeapicall

OUTPUT_DIR = Path("data/uncomtrade")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# UN 국가코드 (M49). 필요하면 쌍을 더 추가하세요.
COUNTRY_CODES = {
    "USA": "842",
    "CHN": "156",
    "KOR": "410",
}

TRADE_PAIRS = [
    ("USA", "CHN"),
    ("CHN", "USA"),
    ("KOR", "CHN"),
    ("KOR", "USA"),
]

# 반도체 관련 HS 4자리 코드 (하나씩 개별 호출)
#   8541: 다이오드·트랜지스터 등 반도체 소자
#   8542: 전자집적회로(IC)
SEMICONDUCTOR_HS_CODES = ["8541", "8542"]

FLOW_CODES = ["M", "X"]  # M=수입, X=수출 (각각 따로 호출)

# 트럼프 2기 취임(2025-01) ~ 이번 달까지
START_YEAR = 2025
END_YEAR = datetime.now().year
END_MONTH = datetime.now().month

REQUEST_DELAY_SEC = 0.8  # 호출 사이 지연 (차단/스로틀링 방지용)


def all_periods() -> list[str]:
    """2025년 1월부터 이번 달까지 YYYYMM 리스트."""
    periods = []
    for year in range(START_YEAR, END_YEAR + 1):
        end_month = END_MONTH if year == END_YEAR else 12
        for m in range(1, end_month + 1):
            periods.append(f"{year}{m:02d}")
    return periods


def fetch_one(reporter_code, partner_code, period, flow_code, cmd_code):
    """단일 period / 단일 flowCode / 단일 cmdCode로 한 번만 호출합니다.
    (공식 예제와 동일한 형태 - 이게 무료 tier에서 실제로 동작하는 방식입니다)"""
    return comtradeapicall.previewFinalData(
        typeCode="C",
        freqCode="M",
        clCode="HS",
        period=period,
        reporterCode=reporter_code,
        cmdCode=cmd_code,
        flowCode=flow_code,
        partnerCode=partner_code,
        partner2Code=None,
        customsCode=None,
        motCode=None,
        maxRecords=500,
        format_output="JSON",
        aggregateBy=None,
        breakdownMode="classic",
        countOnly=None,
        includeDesc=True,
    )


def diagnostic_test_call():
    """본격적으로 돌리기 전에, 가장 단순한 호출 1건을 실제로 찍어봅니다.
    이게 0건이면 코드 구조 문제가 아니라 계정/네트워크 등 다른 문제입니다."""
    print("[진단] 테스트 호출 1건: 미국(842) -> 중국(156), 2025년 6월, 수출(X), HS 8542")
    try:
        df = fetch_one("842", "156", "202506", "X", "8542")
    except Exception as e:
        print(f"[진단] 예외 발생: {type(e).__name__}: {e}")
        return False

    print(f"[진단] 반환 타입: {type(df)}")
    if df is None:
        print("[진단] None이 반환됨 (API가 아무것도 안 줌)")
        return False

    print(f"[진단] shape: {getattr(df, 'shape', '(shape 없음)')}")
    if hasattr(df, "empty") and not df.empty:
        print("[진단] 컬럼:", list(df.columns))
        print("[진단] 첫 행:")
        print(df.head(1).to_string())
        return True
    else:
        print("[진단] 빈 데이터프레임입니다. 코드가 맞아도 이 기간엔 보고된 데이터가 없을 수 있습니다.")
        return False


def fetch_pair(reporter_iso3: str, partner_iso3: str) -> list[dict]:
    reporter_code = COUNTRY_CODES[reporter_iso3]
    partner_code = COUNTRY_CODES[partner_iso3]

    all_records = []
    periods = all_periods()
    total_calls = len(periods) * len(FLOW_CODES) * len(SEMICONDUCTOR_HS_CODES)
    call_num = 0

    for period in periods:
        for flow_code in FLOW_CODES:
            for cmd_code in SEMICONDUCTOR_HS_CODES:
                call_num += 1
                time.sleep(REQUEST_DELAY_SEC)
                try:
                    df = fetch_one(reporter_code, partner_code, period, flow_code, cmd_code)
                except Exception as e:
                    print(f"  [{call_num}/{total_calls}] {period} {flow_code} {cmd_code} - 실패: {e}")
                    continue

                if df is None or (hasattr(df, "empty") and df.empty):
                    continue  # 데이터 없는 달은 조용히 스킵 (너무 시끄러워지는 것 방지)

                records = df.to_dict(orient="records")
                all_records.extend(records)
                print(f"  [{call_num}/{total_calls}] {period} {flow_code} {cmd_code} - {len(records)}건")

    return all_records


def main():
    print("=" * 60)
    print("UN Comtrade 무료 API - 반도체(HS 8541/8542) 무역 데이터 수집 (v2)")
    print(f"기간: {START_YEAR}-01 ~ {END_YEAR}-{END_MONTH:02d}")
    print("=" * 60)

    ok = diagnostic_test_call()
    print("=" * 60)
    if not ok:
        print("⚠ 진단 호출부터 빈 결과입니다. 아래 중 하나일 가능성이 높습니다:")
        print("  1) previewFinalData가 최신 몇 개월치만 지원하고 2025년 데이터는 범위 밖일 수 있음")
        print("  2) reporterCode/partnerCode/cmdCode 값 자체가 이 API 버전에서 다를 수 있음")
        print("  3) 네트워크/방화벽/VPN이 응답을 조용히 가로채고 있을 수 있음")
        print("→ 그래도 전체 수집을 계속 시도합니다. 결과가 역시 0건이면 위 [진단] 출력 전체를")
        print("  그대로 복사해서 보내주세요 — 그걸 보고 원인을 좁힐 수 있습니다.")
        print("=" * 60)

    combined = {}

    for reporter, partner in TRADE_PAIRS:
        pair_key = f"{reporter}_to_{partner}"
        print(f"\n[{pair_key}] 총 {len(all_periods()) * len(FLOW_CODES) * len(SEMICONDUCTOR_HS_CODES)}건 호출 예정...")
        records = fetch_pair(reporter, partner)
        combined[pair_key] = records

        pair_file = OUTPUT_DIR / f"semiconductor_trade_{pair_key}.json"
        with open(pair_file, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 저장: {pair_file} ({len(records)}건)")

    combined_file = OUTPUT_DIR / f"semiconductor_trade_all_{datetime.now().strftime('%Y%m%d')}.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in combined.values())
    print("\n" + "=" * 60)
    print(f"✅ 완료! 총 {total}건 수집")
    print(f"📂 통합 파일: {combined_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
