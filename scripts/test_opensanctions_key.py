"""
test_opensanctions_key.py — OpenSanctions API 키가 401 나는 원인 진단용
=========================================================================

.env에 있는 키가 화면상으로는 발급받은 거랑 "똑같아 보여도" 401이 나는
흔한 원인들:
  1. .env 파일을 Windows 메모장 등으로 저장하면서 앞/뒤에 공백이나
     보이지 않는 문자(BOM, \\r)가 끼어들어감
  2. 키 값을 따옴표로 감싸서 넣음 (OPENSANCTIONS_API_KEY="abc123"처럼
     — python-dotenv는 따옴표를 값의 일부로 읽지는 않지만, 혹시나 확인 필요)
  3. 발급받은 키가 "무료 체험(trial)" 키인데 이미 만료됐거나, 특정
     엔드포인트(search)는 유료 플랜에서만 허용되는 경우
  4. Authorization 헤더 형식이 바뀌었을 가능성 (API 쪽에서 스펙 변경)

이 스크립트는 실제 키 값은 화면에 안 찍고(앞 4자리/뒤 4자리만), 대신
OpenSanctions 서버가 401과 함께 돌려주는 응답 본문(response body)을
그대로 보여줍니다 — 거기에 진짜 원인이 적혀있는 경우가 많습니다
(예: "invalid API key", "expired", "insufficient scope" 등).

사용법:
    python scripts/test_opensanctions_key.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("OPENSANCTIONS_API_KEY", "")


def masked(key):
    if not key:
        return "(비어있음)"
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]} (총 {len(key)}자)"


def main():
    print("=" * 60)
    print("OpenSanctions API 키 진단")
    print("=" * 60)

    if not KEY:
        print("✗ .env에 OPENSANCTIONS_API_KEY가 비어있습니다.")
        return

    print(f"불러온 키: {masked(KEY)}")

    # 앞뒤 공백/개행이 끼어있는지 직접 확인
    stripped = KEY.strip()
    if stripped != KEY:
        print("⚠ 경고: 키 앞/뒤에 공백 또는 개행 문자가 섞여 있습니다! "
              "(.env 파일을 다시 저장하면서 이 부분을 지워보세요)")

    url = "https://api.opensanctions.org/search/default"
    headers = {"Authorization": f"ApiKey {stripped}"}

    print(f"\n요청: GET {url}?q=test")
    print(f"헤더: Authorization: ApiKey {masked(stripped)}")

    try:
        r = requests.get(url, headers=headers, params={"q": "test"}, timeout=15)
    except requests.exceptions.RequestException as e:
        print(f"\n✗ 요청 자체가 실패했습니다 (네트워크 문제일 수 있음): {e}")
        return

    print(f"\n응답 상태 코드: {r.status_code}")
    print("응답 본문:")
    print("-" * 60)
    print(r.text[:2000])
    print("-" * 60)

    if r.status_code == 200:
        print("\n✅ 정상 작동합니다! issue_data_collector.py도 이제 잘 될 거예유.")
    elif r.status_code == 401:
        print("\n✗ 여전히 401입니다. 위 응답 본문에 구체적인 이유가 적혀있을 텐데,")
        print("  보통 'invalid', 'expired', 'revoked' 같은 단어가 있으면 키를")
        print("  https://www.opensanctions.org/docs/api/ 에서 재발급받아야 합니다.")
    else:
        print(f"\n✗ 401은 아니고 {r.status_code}입니다. 위 응답 본문을 참고해서")
        print("  API 쪽 요구사항이 바뀐 건 아닌지 확인이 필요해유.")


if __name__ == "__main__":
    main()
