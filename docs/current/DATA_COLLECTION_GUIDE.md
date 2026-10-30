# 조기경보 데이터 수집 가이드

## 1. 수집 원칙

조기경보 시스템의 데이터는 미래 사건을 맞히기 위한 정답지가 아니라, 위험 신호를 관측하기 위한 센서다. 하나의 출처만으로 경보를 만들지 않고, 공식 신호, 독립 신호, 대중 신호, 시장 신호를 분리해서 수집한 뒤 서로의 차이를 비교한다.

## 2. 조기경보 센서 계층 분류 및 메타데이터 평가

조기경보 시스템의 모든 수집 데이터는 역할과 신뢰 특성에 따라 **[1] 직접 센서**, **[2] 공급망 영향 프록시**, **[3] 교차검증 센서**, **[4] 보조 프록시**의 4단계로 구분한다.

### 2.1 센서 계층별 정의

1. **직접 센서 (Direct Physical Sensors)**:
   - 해협·항만 지연일수, 선박 통항량·유형·우회 경로(AIS/PortWatch), 항만 공지·처리량 등 관측 대상의 물리적 상태를 직접 반영하는 자료.
   - 물리적 기준점으로 활용하되, AIS 공백·스푸핑·지역별 커버리지 한계를 함께 기록한다.
2. **공급망 영향 프록시 (Supply-Chain Impact Proxies)**:
   - 정기선 운임(ZIM/Maersk), 벌크 운임(BDRY), 유조선 주가(FRO), 전쟁보험료 할증률, 국제 유가(Brent/WTI), 천연가스(LNG/Henry Hub).
   - 실제 사건을 직접 관측하는 센서가 아니라 시장이 인식한 영향·기대의 간접 지표로 취급하며, 단독 경보 근거로 사용하지 않는다.
3. **교차검증 센서 (Cross-Verification Sensors)**:
   - GDELT Cloud 구조화 사건(CameoPlus/Conflict), 각국 정부 및 군 공식 발표, 국제/현지/독립 언론 보도, 공개 텔레그램(Telegram OSINT 채널), 공개 포럼(대만 PTT, 중국 핀충).
   - 사건의 발생, 행위자의 의도 및 주장을 다각도로 대조·검증하기 위해 결합하는 센서 계층이다.
4. **보조 프록시 (Auxiliary Proxies & Legacy Features)**:
   - Google Trends 위험 검색어 급등률, Reddit 로컬 서브레딧, 대중 설문조사(Pew, Ipsos), 구형 챗봇/단일 예측 모델 산식.
   - 단독으로는 사실이나 위협 수준을 확정할 수 없으며, 국민 체감 불안도나 서사 확산 속도를 간접 측정하는 보조 징후로만 활용한다.

### 2.2 센서별 품질·취약성 메타데이터 매트릭스

| 센서 명칭 | 계층 | 지연시간 (Latency) | 커버리지 (Coverage) | 편향성 (Bias) | 검열 가능성 (Censorship) | 봇/작전 가능성 (Bot/Astroturf) | 조작 가능성 (Manipulation) | 재현성 (Reproducibility) | 라이선스 및 접근 제한 (License/Access) |
|---|---|---|---|---|---|---|---|---|---|
| **해협 프로필 & 항만 통항 (AIS)** | 직접 | 1~6시간 | 4대 길목 글로벌 주요 선박 | 낮음 (물리적) | 낮음 (단, AIS 스푸핑 국소 존재) | 없음 | 낮음 (스푸핑 주의) | 높음 (해사 공공 DB) | 공공 데이터 / 상용 API 예산 제한 |
| **해상 운임·유조선 (ZIM, FRO, BDRY)** | 영향 프록시 | 실시간 ~ 15분 지연 | 글로벌 상장 선사 | 시장 심리·유동성 반영 | 없음 (공개 시장) | 극히 낮음 | 낮음 (금융 규제) | 높음 (공개 시세) | yfinance / Yahoo Finance 공공 API |
| **에너지 가격 (Brent, WTI, NG)** | 영향 프록시 | 실시간 ~ 15분 지연 | 글로벌 벤치마크 유종 | 시장 심리 반영 | 없음 (공개 시장) | 극히 낮음 | 낮음 (선물 거래소) | 완벽 (공개 시세) | yfinance / 거래소 공공 지표 |
| **전쟁보험료 (War Risk Premium)** | 영향 프록시 | 24~48시간 | 로이즈 합동전쟁위원회(JWC) 지정 구역 | 보수적 위험 평가 | 없음 | 없음 | 극히 낮음 | 높음 (보험사 공시) | 보험 시장 공시 자료 수집 |
| **GDELT Cloud Events (v2)** | 교차검증 | 15분 ~ 1시간 | 글로벌 100+ 언어 다국어 뉴스 | 미디어 보도 편향 | 국가별 언론 통제 반영 | 낮음 (기사 기반) | 보통 (허위 보도 인용 가능) | 높음 (사건 고유 ID 보존) | `GDELT_CLOUD_API_KEY` 필수 / 기본 파이프라인 미호출 / 로컬 월 4,500 QU·일 100 QU 안전상한 / 1페이지 예산 제한 (`complete=false`) |
| **정부·군 공식 발표** | 교차검증 | 수 분 ~ 24시간 | 정부 공식 채널 | 자국 중심 선전/외교적 수사 | 자체 검열 100% | 해당 없음 (공식 계정) | 높음 (기만 전술 가능) | 완벽 (공식 웹 아카이브) | 공개 웹 공시 / 접근 제한 없음 |
| **현지 독립·해외 언론** | 교차검증 | 1~12시간 | 주요 외신 및 망명/독립 매체 | 편집권 편향 | 주재국 추방/차단 압박 | 낮음 | 보통 | 높음 (URL/기사 로그) | RSS / 공공 웹 피드 |
| **공개 텔레그램 (OSINT)** | 교차검증 | 즉시 ~ 30분 | 군사 교전 세력, 현장 채널 | 선전·심리전 극심 | 플랫폼 차단 또는 계정 삭제 | 높음 (채널 봇) | 높음 (가짜 영상/과장) | 보통 (게시물 삭제 시 아카이브 필요) | 공개 채널 웹 프리뷰 (비공개 잠입 절대 금지) |
| **현지 포럼 (PTT, 핀충)** | 교차검증 | 실시간 ~ 2시간 | 대만/중화권 비검열 커뮤니티 | 유저 풀 편향 | 중국 본토 차단(GFW), PTT는 자유 | 보통 (댓글 조작 가능) | 보통 | 보통 | 공개 웹 크롤링 / 방화벽 우회 비필요 |
| **구글 트렌드 (Google Trends)** | 보조 | 24~48시간 | 징집, 대피 등 위험 검색어 급등 | 인터넷 사용자 편향 | 통제국 검색엔진 차단(중국 제외) | 보통 (매크로 검색 가능) | 보통 | 보통 (상대 지수 변동) | PyTrends / Google 비공식 API 요율 제한 |
| **Reddit 로컬 서브레딧** | 보조 | 실시간 | r/taiwan, r/iran 등 | 영문 사용자 편향 | 플랫폼 차단 국가 존재 | 높음 | 보통 | 낮음 | **주의: HTTP 429 빈번 / 차단 위험** |

---

## 3. 정보환경 폐쇄 국가(중국·북한·러시아·이란 등) 특수 처리 규칙

### 3.1 공식 발표의 취급 원칙
- 중국, 북한, 러시아, 이란, 왕정국가, 동남아 통제국가 등의 **정부·국영 매체 발표는 절대 객관적 사실(Ground Truth)로 확정하지 않는다.**
- 정부 발표는 **'국가 행위자의 공식 서사(Official Narrative) 신호'**로만 기록한다.
- 위험 판단은 정부 발표가 아니라, **정부 발표와 현지 독립 언론, 해외 보도, 위성·영상, 금융·물류 지표 사이의 '신호 괴리(Signal Gap)'**를 통해 도출한다.

### 3.2 신호 분리 기록 및 온라인 환경 규정
1. **신호 6대 분리 기록**:
   - `[공식]` 정부 및 군 공식 발표
   - `[현지]` 관영/현지 허가 언론 보도
   - `[독립]` 망명 언론 및 해외 주요 언론 보도
   - `[여론]` 공개 SNS·포럼·텔레그램 표현
   - `[물리]` 위성 관측, 선박 AIS, 항공기 경로, 항만 지연
   - `[시장]` 환율, 증시, 원자재, 운임, 채권 스프레드
2. **SNS 표현의 한계 규정**:
   - SNS 게시물이나 포럼 글을 **"국민 전체 여론"으로 단정하는 것을 엄격히 금지**한다.
   - 반드시 **"온라인 정보환경 신호(Online Information Environment Signal)"**로 한정하여 표기한다.

### 3.3 해외 플랫폼 차단 국가의 수집 조합 전략
- 트위터/유튜브/레딧 등이 차단된 국가의 경우:
  - 검열을 피해 개설된 해외 서버 독립 포럼(예: 중국 핀충, 대만 PTT)
  - 국경 인접국 및 망명 독립 언론(예: 메두자, Radio Farda 등)
  - 공개 웹 아카이브 및 공공 캐시
  - 현지 언어 기반 심층 검색어 모니터링
  - **결정적 실물 프록시(홍콩/대만 환율, 인접 해협 AIS, 통관 무역액)**를 결합하여 정보 공백을 보완한다.

### 3.4 OSINT 수집 한계 및 보안·윤리 절대 준수 수칙 (Red Lines)
- ❌ **비공개 단체 대화방, 비공개 텔레그램 그룹, 비밀 포럼 잠입 수집 금지**
- ❌ **초대 링크(Invite Link)를 요구하는 폐쇄형 채널 진입 금지**
- ❌ **로그인 인증 우회, 방화벽 해킹, 계정 탈취 도구 사용 금지**
- ❌ **민간인 개인 식별 정보(PII) 수집 및 특정 인물 추적 금지**
- ❌ **군사 작전 좌표, 무기 표적 정보, 사이버 취약점 악용 정보 수집 금지**
- ✅ **오직 공개 URL(Web Preview)로 열람 가능한 공개 채널·성명만 수집한다.**

---

## 4. 시계열 검증 시간창(Time Windows) 및 중복 제거(Deduplication) 규칙

### 4.1 센서별 유효 시간창 (Validity Windows)
| 센서 구분 | 유효 관측 시간창 | 근거 및 운용 지침 |
|---|---|---|
| **GDELT Cloud 사건** | 최근 **7일** 이내 | 다국어 기사의 확산 및 사건 코드 부여 주기를 수용 |
| **해협·항만 및 시장 지표** | 최근 **24~72시간** 이내 | 운임 변동, 주가 급등, 항만 혼잡의 단기 충격 반영 |
| **공개 SNS 및 Telegram** | 최근 **48시간** 이내 | 현장 발언 및 군사 성명의 즉시성과 휘발성 반영 |
| **사건 결합 허용 범위** | **기본 ±72시간** | 사건 발생 추정 시점 기준 전후 72시간 이내의 이종 신호만 상호 결합 인정 |

*참고: 위 시간창은 조기경보 프로토타입 기준치이며, 특정 장기 위기(해상 봉쇄 등) 발생 시 설정 파라미터(`--window-hours`)로 유연하게 조정 가능하다.*

### 4.2 중복 제거 및 독립성 검증 규칙 (Deduplication Rules)
1. **사건 고유성 검증 (`event_id`)**:
   - GDELT 및 뉴스 기사의 해시 ID를 1차 키로 등록하여 동일 데이터 재수집을 원천 차단한다.
2. **사건 클러스터링 (Event Clustering)**:
   - 발생일시 차이 $\le 24$시간, 동일 행위자(Actor), 동일 국가/위치, 제목 유사도 $\ge 0.85$인 경우 개별 독립 사건이 아닌 '단일 사건 클러스터'로 통합한다.
3. **출처 독립성(Source Independence) 보장**:
   - 로이터, AP 등 동일 통신사 기사를 여러 언론사가 전재한 경우, 이를 복수 출처로 계산하지 않고 '단일 언론 출처(Single Media Source)'로 정규화한다.
4. **단일 출처 경보 상승 금지 (`single_source_elevate_forbidden = True`)**:
   - 단일 사건 센서(GDELT만 단독 감지)인 경우, 기사 수가 수백 건이어도 `UNVERIFIED` 및 `NORMAL` 등급을 유지하며 임의로 경보 단계를 올리지 않는다.

---

## 5. 과거 사건 기반 오탐(FP)·미탐(FN) 감사 로깅 스키마

조기경보 시스템의 신뢰성을 지속적으로 검증하고 사후 방어하기 위해 다음 스키마를 통해 과거 사건별 성과를 기록한다.

```json
{
  "example_type": "simulated_template",
  "status": "illustrative_only",
  "audit_case_id": "AUDIT-2026-REDSEA-001",
  "event_identifier": {
    "event_id": "cameoplus_00c45344001ccc94",
    "event_title": "United States deploys third carrier strike group toward Iran",
    "geo_region": "Middle East / Hormuz",
    "event_date": "YYYY-MM-DD"
  },
  "observed_signals_at_time": {
    "first_observed_at": "YYYY-MM-DDTHH:MM:SSZ",
    "maritime_chokepoint": "HORMUZ (Critical)",
    "freight_market": "FRO +21.12% Critical Spike",
    "local_opinion": "Middle East Tension Signals detected",
    "telegram_osint": "Naval missile claims observed",
    "distinct_channel_count": 4
  },
  "early_warning_issued": {
    "first_alert_at": "YYYY-MM-DDTHH:MM:SSZ",
    "issued_alert_level": "WARNING",
    "issued_verification_state": "CROSS_VERIFIED"
  },
  "ground_truth_outcome": {
    "verified_at": null,
    "actual_disruption_occurred": null,
    "actual_impact_summary": "실제 검증 자료로 교체하기 전까지 비워 둔다.",
    "lead_time_hours": null
  },
  "performance_evaluation": {
    "audit_label": "PENDING_REVIEW",
    "evaluation_options": ["TIMELY_WARNING", "FALSE_POSITIVE", "FALSE_NEGATIVE", "DELAYED_WARNING"],
    "helpful_sensors": ["freight_market (FRO 주가 선행)", "maritime_chokepoint (보험료 반영)"],
    "failed_or_noisy_sensors": ["local_public_opinion (노이즈 다수)"],
    "lessons_learned": "유조선사 주가가 실제 해군 전개 보도보다 약 12시간 선행하여 리스크를 포착함."
  }
}
```

이 감사 데이터는 취업 포트폴리오 면접 시 **"우리는 단순 미래 예측 성공률을 주장하는 것이 아니라, 센서별 선행 리드타임(Lead Time)과 오탐·미탐 사유를 체계적으로 감사·추적하고 있다"**는 핵심 차별화 증거로 제시한다.

## 6. 미국 국내·동맹·경쟁/대립축 수집 확장 (2026-10-29)

컨트롤타워 결정: **패킷 A(미국 국내 공식)와 패킷 B(동맹 registry)를 동시에** 수집 세션 우선순위로 둔다. Alert Level·당선 예측·전쟁 예측은 수집 세션 범위 밖이다.

### 6.0 표현·역할 규칙

- 미국 국내: **정책·제도 리스크 조기경보** (선거 결과 예측 금지).
- 관계 라벨: 대외 문서는 `ally` / `competitor_adversary_axis`(경쟁·대립축). “적대국”은 내부 role tag로만 사용 가능.
- 모든 신규 레코드: `source_url`, `published_at`, `observed_at`, `source_type`, `parse_status`, `license_access_note` 또는 `access_note`, `raw_ref`/`content_hash`.
- 단일 출처로 경보 단계를 올리지 않는다.

### 6.0-A 패킷 A — 미국 국내 정치·정책 (공식 우선)

| 우선 | 소스 | 레인 | 비고 |
|---|---|---|---|
| 1 | White House Releases RSS | FAST | 기존 `fetch_whitehouse_official.py` |
| 1 | Federal Register API/JSON | FAST | 규칙·관세·제재 고시 |
| 1 | Congress.gov API (법안·표결) | FAST | API 키·쿼터 확인 후 선택 실행 |
| 1 | USTR / Commerce / Treasury 보도·RSS | FAST | 통상·수출통제·제재 |
| 2 | DHS / CBP / DoD 보도자료 | FAST | 이민·국경·군사 공개 신호 |
| 2 | 미 싱크탱크 registry 확장 | CONTEXT | Brookings, CFR, CSIS 등 |
| 3 | Pew / Gallup / AP-NORC 공개물 | BASELINE | RCP Cloudflare 회피 |
| 3 | FRED, 국채·달러·VIX | BASELINE | 정책 불확실성 프록시 |
| 3 | Google Trends(US), Bluesky, 공식 X API만 | OPINION | 국민여론 단정 금지 |

이슈 태그(안): `US_Debt_Ceiling`, `US_Trade_Tariff`, `US_Export_Control`, `US_Immigration_Border`, `US_Industrial_Policy_CHIPS`, `US_Sanctions_OFAC`, `US_Defense_Budget`, `US_Election_Policy_Signal`(공약·법안·행정조치만).

### 6.0-B 패킷 B — 동맹국 공식 registry

`config/source_registry/government_sources.yaml`(및 관련 yaml)에 `relationship_role: ally`, `country`, `fallback`, `license_access_note`를 보강한다.

| 우선 | 행위자 | 소스 유형 |
|---|---|---|
| 1 | 한국 | 외교부·국방부 RSS (기존 유지·스키마 정렬) |
| 1 | 미국 | State / DoD / White House (기존+보강) |
| 1 | 일본·호주·캐나다 | MOFA / DFAT / GAC 공식 RSS·보도 |
| 1 | 영국·독일 | FCDO / Auswärtiges Amt (기존 확인) |
| 2 | NATO · EU EEAS | 공식 뉴스/RSS |
| 2 | 동맹 싱크탱크 | ASPI, IISS, ECFR 등 CONTEXT registry |

### 6.0-C 패킷 C — 경쟁·대립축 (A/B 병행 후 또는 registry에 role만 먼저)

| 우선 | 내용 |
|---|---|
| 1 | 기존 signal_gap 소스(관영↔독립)에 `relationship_role: competitor_adversary_axis` 부여 |
| 1 | OFAC / BIS / OpenSanctions를 FAST 제재 신호로 registry 정리 |
| 2 | 중국·러시아·이란 외교부 공개 RSS/사이트 (사실 확정 금지, 공식 서사만) |
| 2 | GDELT·해협·운임·공개 TG는 기존 센서 재사용, 신규 대량 호출 금지 |

구현 순서(세션 2): **A와 B를 같은 스프린트에서 registry·스키마부터** → 수집기/플래그는 소스별 선택 실행 → C는 role 태깅과 기존 센서 연결을 우선.

## 7. 다음 수집 파이프라인 확장 타임라인

2026-10-04 기준 다음 확장은 검증 세션이나 대시보드 세션과 분리하여 수집 계층에서만 진행한다.

### 7.1 항공 공급망 센서

- 공항별 항공편 수, 화물기·여객기 구분, 지상 대기시간, 결항·우회, ADS-B 관측 공백을 수집 후보로 둔다.
- 인천·홍콩·상하이 푸둥·타이베이·두바이·도하·프랑크푸르트·싱가포르·멕시코시티·파나마시티를 1차 관측 공항으로 검토한다.
- 항공편 수나 ADS-B 신호는 실제 화물 톤수와 동일하지 않으므로 `air_traffic_proxy`와 `uncertainty_note`를 보존한다.

### 7.2 파나마 운하 센서

- 파나마 운하는 수에즈 운하와 분리된 미주 동서 항로 병목으로 관리한다.
- 통항 선박 수, 대기시간, 예약 슬롯, 흘수 제한, 수위·가뭄 공지, LNG·컨테이너·벌크선 통항 변화를 원시 관측값으로 저장한다.

### 7.3 다국가 세관 데이터

- 한국·중국에서 일본·대만·미국·베트남·싱가포르·인도·멕시코·브라질·EU로 확장한다.
- 국가별 API, 공개 다운로드, CSV/Excel, 공식 통계 포털을 `source registry`에서 별도 관리한다.
- 공통 필드는 `reporter`, `partner`, `hs_code`, `period`, `trade_value`, `quantity`, `source_url`, `observed_at`, `access_note`로 정규화한다.

### 7.4 X 공개 정보환경 신호

- 공식 X API를 우선 사용하고, 계정·키워드·언어·시간창을 제한한다.
- `post_id`, `author_id`, `author_type`, `text`, `created_at`, `language`, `public_metrics`, `referenced_posts`, `source_url`, `observed_at`, `api_access_note`를 보존한다.
- X 게시물은 국민 전체 여론이 아니라 `online_information_environment_signal`로 저장한다.

### 7.5 API가 없는 정부 홈페이지

정부 사이트는 다음 순서의 단계형 수집 어댑터를 사용한다.

`official_api → official_rss → official_sitemap → official_html_notice → official_pdf_or_csv → public_json`

각 단계에서 `robots.txt`, 이용약관, 요청 빈도, 공개 접근 여부를 확인하고, 비공개 영역·로그인 우회·접근 제한 회피는 하지 않는다. `source_url`, `page_url`, `document_url`, `published_at`, `observed_at`, `content_hash`, `http_status`, `parser_type`, `robots_checked`, `license_access_note`를 함께 저장한다.

백악관은 `scripts/collection/fetch_whitehouse_official.py`에서 공식 RSS(`https://www.whitehouse.gov/releases/feed/`)를 1순위로 사용한다. 사이트맵 보완은 `--include-sitemap`을 명시한 제한 실행에서만 수행하며, 기본적으로 원문 페이지를 대량 다운로드하지 않고 RSS 메타데이터·해시·수집 영수증을 저장한다. 통합 파이프라인에서도 `--with-whitehouse`를 명시한 경우에만 호출한다.

## 8. GDELT 대체·보조 수집기(2026-10-10)

GDELT Cloud 구독 만료에 대비해 원본 GDELT 2.0과 보조 사건·뉴스 서비스를 별도 수집기로 분리한다.

| 수집기 | 역할 | 인증·제한 | 저장 위치 |
|---|---|---|---|
| `scripts/collection/fetch_gdelt_v2_public.py` | GDELT 2.0 DOC 공개 뉴스 후보 | 공개 API, 429 bounded retry | `data/gdelt_v2_public/latest.json` |
| `scripts/collection/fetch_mediacloud.py` | 매체·국가별 뉴스 확산 보조 신호 | `Authorization: Token` + `cs`/`ss` 필수. 기본 파이프라인 미호출. 1페이지·본문 미요청 | `data/mediacloud/latest.json` |
| `scripts/collection/fetch_acled.py` | 분쟁·시위·정치폭력 사건 | ACLED OAuth 계정 필요 | `data/acled/latest.json` |
| `scripts/collection/fetch_event_registry.py` | 선택적 뉴스 이벤트 클러스터 | `EVENT_REGISTRY_API_KEY`, 학술 승인 우선 | `data/event_registry/latest.json` |

모든 수집기는 인증이 없거나 요금·접근 제한에 걸려도 전체 파이프라인을 중단하지 않고 `AUTH_REQUIRED`, `429`, `complete=false`, `error`를 영수증에 남긴다. 이 데이터는 수집 결과이며 `verification_state`나 Alert Level을 산출하지 않는다.

### GDELT Cloud QU 안전장치

현재 계정은 Academic & Research 플랜(월 5,000 QU)이므로 GDELT Cloud 호출은 쿼터 소진과 계정 오작동 방지를 우선한다.

- `run_pipeline.py`는 기본적으로 GDELT Cloud를 호출하지 않는다. 명시적으로 `--with-gdelt-cloud`를 준 경우에만 제한 수집한다.
- `scripts/collection/gdelt_cloud_budget.py`가 HTTP 요청 시도(재시도 포함)를 로컬 `data/gdelt_cloud/quota_state.json`에 기록한다.
- 기본 로컬 상한은 월 4,500 QU, 일 100 QU이며 `GDELT_CLOUD_MONTHLY_SAFETY_CAP`, `GDELT_CLOUD_DAILY_SAFETY_CAP`으로 더 낮출 수 있다.
- 요청 간 기본 간격은 2초(`GDELT_CLOUD_MIN_INTERVAL_SEC`)다. 로컬 사용량은 안전용 미터이며 실제 사용량은 GDELT Cloud Usage 화면을 기준으로 한다.
- 월·일 상한 또는 상태 파일 오류가 발생하면 요청 전에 중단한다. API 키와 Authorization 헤더는 로그·영수증에 저장하지 않는다.

권장 실행:

```powershell
# 기본 파이프라인: GDELT Cloud 호출 없음
python scripts/run_pipeline.py --collect-only

# 필요할 때만 제한 수집
python scripts/run_pipeline.py --collect-only --with-gdelt-cloud
```

## 8.5 Cloud light collection lane (GitHub Actions, 2026-10-31)

PC가 꺼져 있어도 **가벼운 공개 RSS/HTTP 수집만** 돌리려면 GitHub Actions 워크플로 [`.github/workflows/daily_pipeline.yml`](../../.github/workflows/daily_pipeline.yml)를 사용한다.

| 구분 | 내용 |
|---|---|
| 스케줄 | 매일 07:00 KST (`cron: 0 22 * * *` UTC) + `workflow_dispatch` |
| 포함 | 정부 RSS, 백악관 RSS, signal-gap RSS, financial proxy |
| 제외 | Ollama/LLM, MySQL, GDELT Cloud, 대시보드, Trends/로컬여론/해협, `issue_data_collector` |
| 산출물 | `scripts/data/gov_announcements/`, `data/whitehouse_official/`, `data/signal_gap/` (변경 시 `[skip ci]` 커밋) |
| Kaggle | Secrets(`KAGGLE_USERNAME`/`KAGGLE_KEY`)가 있을 때만 수동 dispatch에서 선택 |

SoT와 무거운 수집·LLM·DB는 계속 로컬 `python scripts/run_pipeline.py --collect-only`(및 선택 플래그)다. Actions 결과는 수집 스냅샷일 뿐 Alert Level이나 `verification_state`를 만들지 않는다.

## 9. Python 수집 파이프라인 실행 그룹(2026-10-10)

Python 스크립트의 역할과 실제 호출 여부는 [`PYTHON_SCRIPT_INVENTORY.md`](PYTHON_SCRIPT_INVENTORY.md)에 기록한다. 수집 세션에서는 다음처럼 후처리와 분리해 실행할 수 있다.

| 목적 | 실행 방법 | 범위 |
|---|---|---|
| 수집·전처리만 | `python scripts/run_pipeline.py --collect-only` | 수집기와 수집 전처리, DB·대시보드 제외 |
| 수집 후 DB 생략 | `python scripts/run_pipeline.py --skip-db` | 수집·검증 단계 실행, DB 적재 제외 |
| 수집 후 대시보드 생략 | `python scripts/run_pipeline.py --skip-dashboard` | 수집·DB 단계 실행, 대시보드 제외 |
| 기존 DB 전용 | `python scripts/run_pipeline.py --only-db` | 수집 생략, DB·대시보드 실행 |

ACLED·Event Registry·Media Cloud·GDELT 2.0 공개 수집기는 인증·요금·엔드포인트 상태가 안정화될 때까지 기본 파이프라인에 연결하지 않는 후보 수집기로 관리한다. 대시보드와 교차검증 로직은 이 세션의 수집 문서 변경 대상이 아니다.

수집 레인과 싱크탱크 registry를 포함한 전체 설계는 [`COLLECTION_PIPELINE_ARCHITECTURE.md`](COLLECTION_PIPELINE_ARCHITECTURE.md)를 참조한다. 출처 목록 초안은 `config/source_registry/`(`SCHEMA.md` + lane별 YAML)에 있으며, `source_role` / `required` / `fallback` / `license_access_note` / `pipeline_default`를 포함한다. 유료·쿼터 API와 PENDING 센서(항공·파나마·다국가 세관·X)는 `pipeline_default: false` 또는 `enabled: false`로 둔다.

2026-10-10 연결 상태:

- **ACLED**: OAuth 인증 성공, 예멘 필터 3건 수집 완료(`HTTP 200`, `complete=true`).
- **Event Registry**: API 키 인증 성공, `Red Sea shipping` 3건 수집 완료(`HTTP 200`, `complete=true`). 보조 센서로 유지한다.
- **Media Cloud** (2026-10-28 재확인): 공식 호스트는 `https://search.mediacloud.org/api/`다. 인증은 `Authorization: Token <MEDIACLOUD_API_KEY>`이며 URL 쿼리 `key=`는 쓰지 않는다. `search/story-list`는 `cs`(컬렉션) 또는 `ss`(소스)가 없으면 HTTP 422다. 구호스트 `api.mediacloud.org`는 DNS 실패라 호출하지 않는다. `fetch_mediacloud.py`는 Search API로 갱신됐으나 기본 파이프라인에는 연결하지 않는다. 응답은 지정 컬렉션의 뉴스 메타데이터일 뿐 경보 근거가 아니다. 키·Authorization 헤더는 로그·영수증·커밋에 남기지 않는다.
- **GDELT 2.0 DOC**: 공개 API 호출 시 `HTTP 429`가 확인되어 호출 간격·캐시·재시도 정책을 조정한다.
