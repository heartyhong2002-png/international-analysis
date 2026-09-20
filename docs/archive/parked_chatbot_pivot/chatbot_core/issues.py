"""issues.py — 21개 국제 이슈 정의 및 키워드 매핑

대륙별_이슈_분석_프레임워크.md 기준. ADR-001에서 확정한 snake_case 이슈 ID
네이밍 컨벤션(예: US_Canada_Trade)을 그대로 따른다 — na-N 같은 대륙코드
스타일은 2026-09-13부로 폐기되었으므로 사용하지 않는다.

이 파일 하나가 "21개 이슈"라는 프로젝트의 스코프를 코드 레벨에서 고정하는
단일 진실 공급원(single source of truth) 역할을 한다. 의도 분류기와
데이터 검색기가 둘 다 이 파일을 import해서 쓴다.
"""

from __future__ import annotations

# 이슈 ID -> (대륙, 한글명, 1차/2차 키워드)
#
# keywords_primary: 그 이슈에만 고유한 표현(국가명 조합, 고유명사, 지명).
#   하나라도 매치되면 그것만으로 이슈를 특정할 수 있을 만큼 변별력이 있는 것만 넣는다.
# keywords_secondary: "핵", "전쟁", "무역", "관계" 처럼 여러 이슈에 공통으로
#   나타나는 일반 용어. 단독으로는 이슈를 특정하지 못하지만, primary 매치가
#   전혀 없을 때 보조 신호로만 쓴다(예: "요즘 무역전쟁 어때" 처럼 국가명이
#   빠진 축약형 질문에 대비).
#
# 두 계층으로 나눈 이유: "이란 핵협상"에서 "핵"만 보고 North_Korea_Nuclear까지
# 같이 걸려버리는 문제(자가 테스트에서 실제로 발견됨)를 막기 위함 —
# extract_issue_tags()가 primary 매치를 secondary보다 우선한다.
ISSUES: dict[str, dict] = {
    # 북미 (3)
    "US_Canada_Trade": {
        "continent": "북미",
        "name_ko": "미-캐 무역 및 이민 갈등",
        "keywords_primary": ["캐나다", "canada", "us-canada"],
        "keywords_secondary": ["무역", "관세", "tariff"],
    },
    "US_Mexico_Immigration": {
        "continent": "북미",
        "name_ko": "미-멕 이민 및 마약 정책",
        "keywords_primary": ["멕시코", "mexico", "cartel"],
        "keywords_secondary": ["이민", "국경", "마약", "border", "immigration"],
    },
    "Trump_Economic_Policy": {
        "continent": "북미",
        "name_ko": "트럼프 미국 경제 정책",
        "keywords_primary": ["트럼프", "trump"],
        "keywords_secondary": ["미국 경제", "관세 정책", "us economy"],
    },
    # 남미 (3)
    "Venezuela_Crisis": {
        "continent": "남미",
        "name_ko": "베네수엘라 정치-경제 위기",
        "keywords_primary": ["베네수엘라", "venezuela", "maduro"],
        "keywords_secondary": ["난민"],
    },
    "Brazil_Politics": {
        "continent": "남미",
        "name_ko": "브라질 정치 & 경제",
        "keywords_primary": ["브라질", "룰라", "brazil", "lula"],
        "keywords_secondary": [],
    },
    "Argentina_Economy": {
        "continent": "남미",
        "name_ko": "아르헨티나 경제 위기",
        "keywords_primary": ["아르헨티나", "argentina", "milei"],
        "keywords_secondary": ["인플레이션", "inflation"],
    },
    # 유럽 (3)
    "Ukraine_War": {
        "continent": "유럽",
        "name_ko": "우크라이나 전쟁",
        "keywords_primary": ["우크라이나", "젤렌스키", "ukraine", "zelensky"],
        "keywords_secondary": ["전쟁", "war"],
    },
    "EU_Russia_Relations": {
        "continent": "유럽",
        "name_ko": "EU-러시아 관계",
        "keywords_primary": ["러시아 제재", "russia sanctions"],
        "keywords_secondary": ["eu", "러시아", "european union"],
    },
    "Nordic_Security": {
        "continent": "유럽",
        "name_ko": "북유럽 안보",
        "keywords_primary": ["나토", "nato", "북유럽", "nordic", "finland", "sweden"],
        "keywords_secondary": [],
    },
    # 중동 (3)
    "Iran_Nuclear": {
        "continent": "중동",
        "name_ko": "이란 핵협상 & 긴장",
        "keywords_primary": ["이란", "jcpoa", "iran", "uranium"],
        "keywords_secondary": ["핵", "nuclear"],
    },
    "Israel_Palestine": {
        "continent": "중동",
        "name_ko": "이스라엘-팔레스타인",
        "keywords_primary": ["이스라엘", "팔레스타인", "가자", "israel", "palestine", "gaza"],
        "keywords_secondary": [],
    },
    "Middle_East_Energy": {
        "continent": "중동",
        "name_ko": "중동 에너지 정책",
        "keywords_primary": ["opec", "걸프"],
        "keywords_secondary": ["석유", "원유", "oil"],
    },
    # 아프리카 (3)
    "Sudan_Conflict": {
        "continent": "아프리카",
        "name_ko": "수단 분쟁",
        "keywords_primary": ["수단", "sudan"],
        "keywords_secondary": [],
    },
    "Ethiopia_Instability": {
        "continent": "아프리카",
        "name_ko": "에티오피아 정치 불안정",
        "keywords_primary": ["에티오피아", "ethiopia"],
        "keywords_secondary": [],
    },
    "Congo_Conflict": {
        "continent": "아프리카",
        "name_ko": "콩고 분쟁",
        "keywords_primary": ["콩고", "congo"],
        "keywords_secondary": ["광물"],
    },
    # 아시아-태평양 (6)
    "North_Korea_Nuclear": {
        "continent": "아시아-태평양",
        "name_ko": "북한 핵 & 트럼프-김정은",
        "keywords_primary": ["북한", "김정은", "north korea", "kim jong un"],
        "keywords_secondary": ["핵", "미사일", "missile", "nuclear"],
    },
    "Taiwan_Strait": {
        "continent": "아시아-태평양",
        "name_ko": "대만 해협 긴장",
        "keywords_primary": ["대만", "해협", "taiwan", "tsmc"],
        "keywords_secondary": ["반도체", "semiconductor"],
    },
    "India_Pakistan": {
        "continent": "아시아-태평양",
        "name_ko": "인도-파키스탄",
        "keywords_primary": ["카슈미르", "kashmir"],
        "keywords_secondary": ["인도", "파키스탄", "india", "pakistan"],
    },
    "South_China_Sea": {
        "continent": "아시아-태평양",
        "name_ko": "남중국해 영유권",
        "keywords_primary": ["남중국해", "south china sea"],
        "keywords_secondary": ["항행의 자유"],
    },
    "Japan_Korea_Relations": {
        "continent": "아시아-태평양",
        "name_ko": "일본-한국 관계",
        "keywords_primary": ["한일", "독도", "위안부", "korea relations"],
        "keywords_secondary": ["일본", "한국", "japan"],
    },
    "Myanmar_Crisis": {
        "continent": "아시아-태평양",
        "name_ko": "미얀마 정치 위기",
        "keywords_primary": ["미얀마", "myanmar"],
        "keywords_secondary": ["쿠데타", "coup"],
    },
    # 경제/무역 — 기획서 3.3절, 이슈 태그와 별도로 언급되어 온 횡단 카테고리
    "US_China_Trade": {
        "continent": "횡단(경제)",
        "name_ko": "미중 무역전쟁",
        "keywords_primary": ["미중", "us-china", "china trade"],
        "keywords_secondary": ["무역전쟁", "관세전쟁"],
    },
}


def all_issue_ids() -> list[str]:
    return list(ISSUES.keys())


def issue_name_ko(issue_id: str) -> str:
    info = ISSUES.get(issue_id)
    return info["name_ko"] if info else issue_id
