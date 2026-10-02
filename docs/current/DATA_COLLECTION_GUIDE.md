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
| **GDELT Cloud Events (v2)** | 교차검증 | 15분 ~ 1시간 | 글로벌 100+ 언어 다국어 뉴스 | 미디어 보도 편향 | 국가별 언론 통제 반영 | 낮음 (기사 기반) | 보통 (허위 보도 인용 가능) | 높음 (사건 고유 ID 보존) | `GDELT_CLOUD_API_KEY` 필수 / 1페이지 예산 제한 (`complete=false`) |
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
