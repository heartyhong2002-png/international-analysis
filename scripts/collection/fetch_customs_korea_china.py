"""
관세청 공공데이터 Open API로 한국-중국 반도체(HS 8541/8542) 무역 데이터 수집
- Reporter: 한국(관세청 기준), Partner: 중국
- 트럼프 2기 취임(2025년 1월) 이후 ~ 현재까지, 월별(수출/수입 금액 모두 한 번에 포함)

** 이 스크립트는 준기님 컴퓨터에서 직접 실행해야 합니다 **
(클라우드 세션에서는 외부 API 접속이 막혀 있어 Claude가 대신 실행할 수 없습니다)

--------------------------------------------------------------------------
사용 전 준비:
1. https://www.data.go.kr 무료 회원가입
2. "관세청_품목별 국가별 수출입실적" 데이터셋 검색 → [활용신청]
   (개발계정은 보통 즉시 또는 몇 시간 내 자동 승인됩니다)
3. 마이페이지 > 개발계정에서 발급받은 서비스키(인증키) 확인
   - "일반 인증키(Decoding)" 값을 쓰세요 (Encoding 키 말고)
4. 프로젝트의 .env 파일에 아래 줄 추가:
     CUSTOMS_API_KEY=발급받은키값

--------------------------------------------------------------------------
주의:
- 이 API는 한 번 호출에 조회기간이 "최대 1년"까지만 허용됩니다.
  그래서 2025년 전체 / 2026년 부분, 이렇게 두 번으로 나눠서 호출합니다.
- 품목코드(hsSgn) 필드가 10자리(HSK) 기준이라, 문서 예시는 "1001999090"처럼
  풀자리 코드를 씁니다. 이 스크립트는 먼저 "8541"처럼 4자리(HS heading)만
  넣어서 테스트합니다 - 관세청 API들이 종종 앞자리만 넣어도 그 밑의 세부
  코드를 다 합쳐서 주는 경우가 있어서입니다. 진단 호출 결과가 비어 있으면
  콘솔에 안내 메시지가 뜨니, 그 출력을 그대로 복사해서 Claude에게 보여주세요
  (그러면 10자리 세부코드를 다 나열해서 넣는 버전으로 다시 만들어 드릴 수 있습니다).

설치:
    pip install requests python-dotenv

실행:
    python scripts/fetch_customs_korea_china.py
--------------------------------------------------------------------------
"""

import os
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SERVICE_KEY = os.getenv("CUSTOMS_API_KEY", "")

BASE_URL = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"

# 중국. data.go.kr 문서 예시가 미국을 "US"로 표기(ISO 3166-1 alpha-2 방식)해서
# 그 규칙을 따라 "CN"으로 둡니다. 안 맞으면 진단 호출에서 바로 빈 값/에러로 드러납니다.
COUNTRY_CODE = "CN"

# 반도체 관련 HS 4자리 코드
#   8541: 다이오드·트랜지스터 등 반도체 소자
#   8542: 전자집적회로(IC)
HS_CODES = ["8541", "8542"]

# 관세청 API는 한 번 호출에 최대 1년 범위까지만 허용되어, 연도 단위로 나눠서 호출합니다.
# END는 조회 가능한 가장 최근 달로 필요시 조정하세요 (관세청 통계는 보통 전월/전전월까지 갱신됩니다).
PERIOD_RANGES = [
    ("202501", "202512"),
    ("202601", "202609"),
]

OUTPUT_DIR = Path("data/customs_korea")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_DELAY_SEC = 0.5


def fetch_one(hs_code: str, strt_yymm: str, end_yymm: str) -> str:
    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": strt_yymm,
        "endYymm": end_yymm,
        "cntyCd": COUNTRY_CODE,
        "hsSgn": hs_code,
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_xml(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for item in root.iter("item"):
        row = {child.tag: child.text for child in item}
        items.append(row)
    return items


def diagnostic_test_call() -> list[dict]:
    print("[진단] 테스트 호출: HS 8541, 중국(CN), 2025년 1~12월")
    try:
        xml_text = fetch_one("8541", "202501", "202512")
    except Exception as e:
        print(f"[진단] 예외 발생: {type(e).__name__}: {e}")
        return []

    print("[진단] 응답 원문 (앞 1000자):")
    print(xml_text[:1000])

    # resultCode/resultMsg 먼저 확인 (인증 실패, 파라미터 오류 등은 여기서 드러남)
    try:
        root = ET.fromstring(xml_text)
        result_code = root.findtext(".//resultCode")
        result_msg = root.findtext(".//resultMsg")
        if result_code is not None:
            print(f"[진단] resultCode={result_code}, resultMsg={result_msg}")
    except Exception:
        pass

    try:
        items = parse_xml(xml_text)
    except Exception as e:
        print(f"[진단] XML 파싱 실패: {e}")
        return []

    print(f"[진단] 파싱된 레코드 수: {len(items)}")
    if items:
        print("[진단] 첫 레코드:", items[0])
    return items


def main():
    if not SERVICE_KEY:
        print("✗ CUSTOMS_API_KEY가 비어 있습니다. .env 파일에 발급받은 서비스키를 넣어주세요.")
        print("  (data.go.kr 마이페이지 > 개발계정 > 일반 인증키 Decoding 값)")
        return

    print("=" * 60)
    print("관세청 Open API - 한국↔중국 반도체(HS 8541/8542) 무역 데이터 수집")
    print("=" * 60)

    diag_items = diagnostic_test_call()
    print("=" * 60)
    if not diag_items:
        print("⚠ 진단 호출 결과가 비어 있습니다. 아래 중 하나일 가능성이 높습니다:")
        print("  1) hsSgn에 4자리(8541)만 넣는 게 이 API에서는 안 통함 (10자리 세부코드 필요)")
        print("  2) 국가코드가 'CN'이 아니라 다른 체계일 수 있음")
        print("  3) 서비스키가 아직 승인 대기중이거나 잘못 입력됨")
        print("→ 그래도 전체 수집을 계속 시도합니다. 위 [진단] 원문(XML)을 그대로")
        print("  복사해서 보내주시면 원인을 바로 좁혀드릴 수 있습니다.")
        print("=" * 60)

    all_records = []
    for hs_code in HS_CODES:
        for strt, end in PERIOD_RANGES:
            time.sleep(REQUEST_DELAY_SEC)
            try:
                xml_text = fetch_one(hs_code, strt, end)
                items = parse_xml(xml_text)
            except Exception as e:
                print(f"  ✗ HS {hs_code} {strt}-{end} 실패: {e}")
                continue
            print(f"  ✓ HS {hs_code} {strt}-{end}: {len(items)}건")
            for it in items:
                it["_queried_hs_code"] = hs_code
            all_records.extend(items)

    out_file = OUTPUT_DIR / "korea_china_semiconductor_trade.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"✅ 완료! 총 {len(all_records)}건 수집")
    print(f"📂 저장 위치: {out_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
