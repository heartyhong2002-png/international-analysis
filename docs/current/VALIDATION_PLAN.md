# 조기경보 검증 계획

## 1. 검증 대상과 비대상

이 시스템은 미래 사건의 발생 여부나 시점을 예측하지 않는다. 검증 질문은 다음과 같다.

> 특정 시점에 이용 가능한 자료만 사용했을 때, 시스템이 위험 신호를 출처와 근거 문장에 연결하고, 사람 검수에서 일관되게 설명할 수 있었는가?

따라서 "전쟁을 맞혔다", "위기를 예측했다", "경보가 사건을 일으켰다"는 주장을 하지 않는다. 사건 발생 여부는 경보 품질을 재검토하는 맥락 정보이며, 모델의 미래 예측 정답으로 환산하지 않는다.

## 2. 검증 단위와 판정 기준

검증 단위는 **경보 1건**이다. 경보에는 이슈, 관찰 시점, 경보 단계, 입력 출처, 근거 문장, 모델 출력, 사람 검수 결과를 함께 보관한다.

사람 검수자는 다음 다섯 항목을 각각 기록한다.

| 항목 | 허용 값 | 판정 질문 |
|---|---|---|
| 경보 단계 | accept / revise / reject | Watch 또는 Warning 단계가 당시 자료에 비례하는가? |
| 근거 문장 | supported / partial / unsupported | 제시된 원문이 모델의 요약·논조 판단을 실제로 뒷받침하는가? |
| 출처 품질 | primary / reputable_secondary / unknown | 원출처·공식자료인지, 신뢰 가능한 2차 출처인지 확인 가능한가? |
| 해석 수위 | supported / overstated / insufficient | 사실에서 경보로 넘어가는 추론이 과도하지 않은가? |
| 후속 조치 | none / false_alarm_candidate / missed_signal_candidate / evidence_gap | 재검토 또는 개선이 필요한 오류 유형은 무엇인가? |

`accept`는 "위험이 반드시 현실화된다"가 아니라 **당시 근거로 Watch/Warning을 제시하는 것이 타당하다**는 뜻이다.

## 3. 과거 사례 백테스트

### 3.1 목적

과거에 이미 알려진 위험 고조 국면에서, 시스템이 당시 공개돼 있던 자료만으로 설명 가능한 신호를 포착했는지 점검한다. 백테스트는 예측 정확도 측정이 아니라 **시간 순서·근거 연결·경보 수위의 적절성** 감사다.

### 3.2 사례 선정과 동결

초기에는 공급망 연관성이 큰 2~3개 사례만 선정한다. 예: 대만해협 긴장, 미중 무역·수출통제, 중동 에너지·해상물류 위험.

각 사례마다 다음을 `data/validation_backtest_log.csv`에 기록한다.

- 관찰 창 (`observation_window`): 경보 판단에 사용 가능한 시작일·종료일
- 기준일 (`reference_date`): 사건이 널리 알려진 고조 국면의 시작일. 이는 사후 비교용이며 모델 입력에 넣지 않는다.
- 입력 동결 (`data_cutoff`): 기준일 이후 기사·수정된 자료를 제외한 URL, 수집 시각, 발행 시각
- 시스템 결과 (`alert_level`, `signal_type`, `evidence_quote`): Alert Level, 신호 유형, 근거 문장, 출처 수와 출처 유형
- 사람 판정 (`reviewer_decision`, `evidence_quote_supported`, `source_quality`, `interpretation_assessment`): accept / revise / reject, 근거·출처·해석 수위 판정
- 사후 메모 (`post_event_notes`): 경보 이후 위험 변화와 해석상의 제한

### 3.3 백테스트 절차

1. 사례·관찰 창·기준일을 먼저 등록하고 입력을 동결한다.
2. 기준일 이전 자료만으로 파이프라인을 실행한다.
3. 모델 출력과 근거 URL을 검수자에게 제공한다. 검수자는 기준일 이후 결과를 보지 않고 판정한다.
4. 검수 완료 뒤에만 기준일 이후 전개를 비교 메모로 추가한다.
5. 오류·불확실성은 `data/false_alarm_missed_signal_log.csv`에 기록한다.

## 4. 사람 표본 검수

매 실행분에서 최소 15% 또는 20건 중 큰 쪽을 무작위 추출한다. Warning과 데이터 부족/판정 보류 사례는 표본에 반드시 포함한다. 표본 선정 기준과 난수 시드는 `review_batch_id`에 기록한다.

두 명의 검수자가 가능하면 모델 라벨을 가린 상태에서 독립 판정한다. 이 경우 라벨 일치율과 불일치 건수를 보고한다. 한 명만 가능한 경우에는 "단일 검수자 잠정 평가"로 명시하며, 이를 독립 정확도로 부르지 않는다.

`data/pending_human_review.csv`는 대기열, `data/review_log.csv`는 완료·보류·반려를 모두 포함하는 이력으로 사용한다.

## 5. 근거 품질과 신호 괴리 검증

경보가 나오려면 최소 하나의 확인 가능한 URL과 그 URL의 직접 인용 또는 정확한 요약이 있어야 한다. 단일 출처·익명 커뮤니티·제목만 있는 자료는 단독 Warning 근거가 될 수 없고 `확인 필요` 또는 Watch로 제한한다.

정부 발표와 독립·현지 신호의 차이는 "왜곡의 증거"가 아니라 **출처 간 서술 차이**로 기록한다. 신호 괴리율은 탐색적 지표이며, 충분한 동일 기간 표본과 사람 검수가 쌓이기 전까지 Critical 또는 Warning 자동 발령 기준으로 사용하지 않는다.

## 6. 오탐·미탐과 오류 기록

오탐 후보는 "이후 위험이 확대되지 않았다"만으로 확정하지 않는다. 경보 당시 근거가 부실했는지, 위험 완화 조치가 있었는지, 관찰 기간이 짧았는지를 함께 기록한다.

미탐 후보는 사후에 알려진 고조 국면에서 해당 기간의 입력 자료에 충분한 근거가 있었는데도 Watch 이상 경보가 없었던 경우다. 사후에만 공개된 정보는 미탐 판정 근거로 쓰지 않는다.

각 항목에는 `error_type` (false_alarm_candidate, missed_signal_candidate, evidence_gap), `error_detail` (발견일, 당시 사용 가능했던 근거, 원인 가설), `correction_note` (수정 조치), `follow_up_date` (재검토 날짜 및 상태)를 남긴다. 오류 로그는 성능을 좋게 보이게 하기 위한 제외 목록이 아니라 개선 이력이다.

## 7. 보고 지표

| 지표 | 산식 또는 보고 방식 | 해석 제한 |
|---|---|---|
| Human acceptance rate | accept / 완료 검수 건수 | 표본·검수자 수를 함께 표시한다. 미래 사건 정확도가 아니다. |
| Evidence support rate | supported / 근거 검수 건수 | URL 존재만으로 supported가 되지 않는다. |
| Source-quality coverage | primary 또는 reputable_secondary 출처가 있는 경보 비율 | 출처의 정치적 중립성을 의미하지 않는다. |
| Abstention rate | 판단 보류·확인 필요 / 전체 판정 | 낮을수록 좋다는 지표가 아니다. 근거 부족에서의 보류는 안전장치다. |
| False-alarm / missed-signal candidates | 열린·확정·재검토 상태별 건수 | 원인 분석 전에는 단순 오류율로 부르지 않는다. |
| Inter-reviewer agreement | 두 검수자가 있는 배치의 일치율 | 표본이 작으면 수치보다 불일치 사례를 우선 제시한다. |

## 8. 표현 원칙

대시보드·보고서·코드 출력에서는 "100% 정확", "환각 0%", "완벽 검증", "자동 승인", "객관적 사실"을 사용하지 않는다. 대신 다음처럼 표현한다.

- 제한된 표본에서의 회귀 테스트 결과
- 모델 간 일치도이며 정답 보증이 아님
- 지정된 근거 부재 조건에서 판단 보류 규칙을 확인함
- 사람 검수 대기 또는 추가 확인 필요
- 탐색적 신호이며 인과 또는 미래 사건을 단정하지 않음

## 9. 포트폴리오 방어 논리

이 프로젝트의 품질 주장은 미래를 맞힌다는 데 있지 않다. 관찰 가능한 자료를 시간 순서대로 보존하고, 근거와 출력의 연결을 검수하며, 오류·보류·불일치를 숨기지 않고 기록하는 정보시스템이라는 데 있다.

예측에서 조기경보로 바꾼 배경과 대외 발표 흐름은 `docs/history/PROJECT_EVOLUTION_TIMELINE.md` 및 `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md`에서 확인한다.

## 10. 비전공자도 수행할 수 있는 사람 검수 운영안

사람 검수의 대상은 국제정치의 최종 정답이나 외교적 의도 자체가 아니다. 검수자는 시스템이 공개 원문을 과장 없이 사용했는지, 근거와 경보 단계가 연결되는지를 확인한다. 따라서 1차 검수에는 외교학·정치학 전공자가 필수는 아니다.

### 10.1 일반 검수자가 판정하는 항목

친구·동료 학생 또는 프로젝트 작성자가 다음 항목을 판정할 수 있다.

1. 모델이 인용한 표현이 원문에 실제로 있는가?
2. 모델 요약이 원문보다 강한 표현으로 바뀌지 않았는가?
3. 출처 URL과 수집 시각을 확인할 수 있는가?
4. 단일 출처만으로 Warning/Critical 수준을 부여하지 않았는가?
5. 근거가 부족한데도 `확인 필요` 또는 `판단 보류` 대신 단정했는가?

검수자에게는 “국제정치의 정답을 맞혀 달라”가 아니라 “원문과 시스템 설명을 비교해 과장 여부를 확인해 달라”고 안내한다.

### 10.2 도메인 검토가 필요한 항목

다음은 일반 검수 결과와 분리해 `domain_review_needed=yes`로 표시한다.

- 국가의 군사·외교적 의도에 대한 해석
- 역사적 맥락이나 현지 정치문화가 필요한 주장
- 현지 언어의 완곡어법·선전 표현 해석
- 특정 사건이 실제 공급망에 미치는 영향의 전문적 판단

이 항목을 확인할 전문가가 없으면 억지로 승인하지 않고 `확인 필요`로 남긴다. 커뮤니티 댓글이나 단일 AI 응답을 전문가 검토의 대체물로 취급하지 않는다.

### 10.3 표본 구성

초기 한 배치는 30건으로 구성한다.

| 표본층 | 권장 수 | 목적 |
|---|---:|---|
| Watch | 10 | 낮은 단계에서 과잉 경보가 발생하는지 확인 |
| Warning/Critical 후보 | 10 | 경보 단계와 근거 수위 확인 |
| 판단 보류·근거 부족 | 5 | 보류 규칙이 작동하는지 확인 |
| 모델 간 불일치 또는 단일 출처 | 5 | 취약 사례를 우선 점검 |

가능하면 두 명이 15건을 겹쳐서 독립 검수한다. 겹친 표본에서는 사람 간 일치 건수·불일치 건수와 불일치 사유를 기록한다. 한 명만 검수하는 경우 결과는 `single_reviewer_provisional`로 표시하며 독립 검증이나 전문가 검증이라고 부르지 않는다.

### 10.4 검수 순서와 눈가림

1. 검수자는 원문, 출처, 수집 시각, 근거 문장만 먼저 본다.
2. 모델 라벨과 최종 경보 단계는 가린 채 근거 지원 여부와 과장 여부를 기록한다.
3. 그 다음 모델 출력과 경보 단계를 공개하고 `accept / revise / reject`를 판정한다.
4. 모델 출력과 사람 판정이 다른 경우에만 함께 논의하고, 원문 수정이나 라벨 변경 이력을 남긴다.

이 순서를 지켜야 모델의 표현에 끌려가 원문을 재해석하는 현상을 줄일 수 있다.

### 10.5 검수표 최소 필드

`data/review_log.csv`와 `data/pending_human_review.csv`에는 다음 의미가 유지되어야 한다.

| 필드 | 허용 값 |
|---|---|
| `reviewer_decision` | `accept`, `revise`, `reject` |
| `evidence_quote_supported` | `supported`, `partial`, `unsupported` |
| `source_quality` | `primary`, `reputable_secondary`, `unknown` |
| `interpretation_assessment` | `supported`, `overstated`, `insufficient` |
| `domain_review_needed` | `yes`, `no` |
| `error_type` | `none`, `evidence_gap`, `overclaim`, `false_alarm_candidate`, `missed_signal_candidate` |
| `reviewer_id` | 익명화된 검수자 ID |
| `correction_note` | 수정 사유와 다음 조치 |

검수의 목적은 높은 승인율을 만드는 것이 아니다. `revise`, `reject`, `domain_review_needed`가 발견되면 그것 자체가 품질 개선을 위한 유효한 결과다.
## 11. tev1 보조 판정 백테스트 기록 (2026-10-11)

`tev1`은 공식 Alert Level 공급원이 아니라 구조화된 위험 신호를 선택지로 분류하는 보조 판정기다. 1차 시운전에서는 기존 사례 4건의 구조화 특징값을 `/v1/systemone`에 입력하고, 결과를 `data/tev1_backtest_results.json`에 저장했다.

| 사례 | tev1 판정 | 해석 |
|---|---|---|
| 우크라이나 안보 | `CRITICAL` | 높은 점수·다중 출처·교차검증 상태와 일치 |
| 대만해협 | `WARNING` | 부분 확인 상태의 경보 후보와 일치 |
| 홍해 해운 | `WATCH` | `INSUFFICIENT_EVIDENCE` 확률도 높아 확인 필요 |
| 미중 무역 | `CRITICAL` | 높은 점수·다중 출처·교차검증 상태와 대체로 일치 |

이 결과는 실제 시간 동결 원문과 사람 검수 라벨을 이용한 정확도 평가가 아니다. 따라서 공식 경보 성능이나 일반화 성능으로 해석하지 않으며, `confidence`를 정답 확률로 취급하지 않는다. 후속 백테스트에서는 최소 10건 이상의 동결 입력, 근거 URL, 사람 검수 결과, 기존 Risk Signal Score와의 불일치를 함께 기록한다.


## 12. 5대 감시축 10건 동결 사례 백테스트 및 산식-tev1 불일치(Discrepancy) 감사 (2026-10-29)

1차 4건 시운전 이후, 5대 핵심 감시축(`russia_ukraine_europe`, `east_asia_military_tech`, `middle_east_energy_shipping`, `us_china_strategic_trade`, `us_allies_relations`)별로 각 2건씩 총 10건의 시간 동결(time-frozen) 원문 발췌(`frozen_excerpt`), 근거 URL(`evidence_url`), 사람 검수 라벨(`human_review_label`: `accept`/`revise`)을 `scripts/validation/backtest_tev1.py`에 반영했다.

- **이중 대조 구조**: 각 사례에 대해 결정론적 산식(`calculate_alert_assessment`)이 산출한 경보 등급(`관찰`/`주의`/`경보`/`고경보`/`확인 필요` ➔ `NORMAL`/`WATCH`/`WARNING`/`CRITICAL`/`INSUFFICIENT_EVIDENCE`)과 `tev1`의 선택지 판정(`tev1_choice`)을 대조한다.
- **불일치 시 사람 검수 강제 트리거**: 산식 결과와 `tev1` 판정이 불일치(`formula_vs_tev1_discrepancy = true`)할 경우, 점수와 무관하게 `human_review_required = true`로 설정하여 사람 검수 대기열로 이관한다.
- **신호 괴리(Signal Gap) 오탐 방지 검증**: `scripts/analysis/analyze_signal_gap.py`에서 비정치·문화·스포츠 기사를 제외하고 `Title + Summary` 결합 및 복합 인용문 분리 정규화(`_normalize_evidence_phrases`)를 적용해 러시아·중동 권역의 근거 문장 누락 및 비정치 기사 오탐을 교정했다.


| Case ID | 감시축 (`issue_axis`) | 산식 판정 | tev1 판정 | 일치 여부 | 불일치 원인 및 검수 조치 |
|---|---|---|---|---|---|
| `BT-2022-UKR-01` | `russia_ukraine_europe` | 고경보 (`CRITICAL`) | `CRITICAL` | 일치 | 다중 출처 교차검증 및 높은 신호 괴리 일치 |
| `BT-2026-UKR-02` | `russia_ukraine_europe` | 고경보 (`CRITICAL`) | `WARNING` | **불일치** | `PARTIALLY_CONFIRMED` 상태를 반영해 `tev1`이 보수적으로 판정 ➔ 사람 검수 |
| `BT-2024-TWN-01` | `east_asia_military_tech` | 고경보 (`CRITICAL`) | `WARNING` | **불일치** | `PARTIALLY_CONFIRMED` 상태에서 `tev1`이 `WARNING` 선택 ➔ 사람 검수 |
| `BT-2026-TWN-02` | `east_asia_military_tech` | 경보 (`WARNING`) | `WARNING` | 일치 | 중간 수준 괴리·부분 확인 상태 일치 |
| `BT-2024-REDSEA-01` | `middle_east_energy_shipping` | 확인 필요 (`INSUFFICIENT_EVIDENCE`) | `WATCH` | **불일치** | 단일 출처 `UNVERIFIED`에 대해 산식 가드레일이 경보 보류 강제 ➔ 사람 검수 |
| `BT-2026-HORMUZ-02` | `middle_east_energy_shipping` | 고경보 (`CRITICAL`) | `CRITICAL` | 일치 | 해운 프록시·공식/독립 신호 결합 일치 |
| `BT-2018-USCN-01` | `us_china_strategic_trade` | 고경보 (`CRITICAL`) | `CRITICAL` | 일치 | 공식 관세 발표 및 무역 지표 교차검증 일치 |
| `BT-2026-USCN-02` | `us_china_strategic_trade` | 확인 필요 (`INSUFFICIENT_EVIDENCE`) | `WATCH` | **불일치** | 독립 출처 비교 근거 부재 시 산식 가드레일이 `확인 필요` 강제 ➔ 사람 검수 |
| `BT-2026-ALLY-01` | `us_allies_relations` | 경보 (`WARNING`) | `WARNING` | 일치 | 동맹 관세·방위비 협상 신호 괴리 일치 |
| `BT-2026-ALLY-02` | `us_allies_relations` | 관찰 (`NORMAL`) | `WARNING` | **불일치** | 낮은 위험 점수(26.7)임에도 `tev1`이 `CROSS_VERIFIED`에 과민 반응 ➔ 산식으로 오탐 방어 |


## 10. 독립 다자간 검증단 (Multi-Judge Validation Suite) 아키텍처 (2026-11-05)

### 10.1 도입 배경 및 단일 모델 한계 극복
초기에는 `tev1:latest` 단일 의사결정 모델을 통해 조기경보 리스크 상태를 분류했으나, 다음과 같은 취약점이 식별되었습니다:
1. **단일 심판 편향**: 특정 모델의 고유 프롬프트 반응 특성이나 미세조정 가중치로 인한 편향 가능성
2. **논리적 비약 검증 한계**: 선택형 분류(Choice Classification)만으로는 사실에서 경보로 넘어가는 비약적 추론을 심층 논박하기 어려움
3. **원문 충실도(Faithfulness) 감사 필요**: 원문의 사소한 정황이 과잉 경보(False Alarm)로 부풀려지는 현상을 엄격하게 견제할 외부 사실성 감사관 필요

### 10.2 독립 검증단 3심제 + 수학적 가드레일 구성
| 계층 | 모델/도구 | 성격 | 주요 감사 역할 |
|---|---|---|---|
| **주심** | `tev1:latest` | 정량 선택형 분류 | 리스크 지표 및 요약 신호를 바탕으로 5대 조기경보 등급(`NORMAL`, `WATCH`, `WARNING`, `CRITICAL`, `INSUFFICIENT_EVIDENCE`) 1차 판정 |
| **비판관** | `deepseek-r1:7b` | CoT 추론 및 적대적 반박 | Chain-of-Thought 사고 과정을 통해 "과잉 경보가 아닌가?", "지나친 비약은 없는가?"를 비판적으로 반박 검증 (Adversarial Critic) |
| **감사관** | `gemma2:9b` | 사실성 및 원문 충실도 | 구글의 엄격한 사실성 가이드라인을 기반으로, 원문 인용문 대비 모델 주장의 왜곡·환각 유무를 2진/3진 척도로 감사 |
| **수학적 가드레일** | `calculate_alert_assessment()` | 결정론적 산식 | 수집 출처 수, 신호 괴리도(Signal Gap), 합의도(Consensus)를 토대로 LLM의 자의적 판단을 방어하는 수학적 경계선 제공 |

### 10.3 5대 감시축 10건 동결 벤치마크 백테스트 체계
과거 및 2026년 시점의 5대 핵심 감시축(러-우-유럽, 동아시아 안보·반도체, 중동 호르무즈·홍해 해상 물류, 미중 전략 무역·수출통제, 한미/동맹 안보) 10개 대표 사례를 동결(`scripts/validation/backtest_tev1.py`)하여, 검증단 모델들의 판정 일치도와 불일치(Discrepancy)를 지속적으로 정밀 감사합니다. tev1 10건 산식 대조는 **산식↔모델 불일치 감사**이며 Human acceptance·공식 성능이 아니다.

### 10.4 다자간 검증단 판정 기준 (2026-11-05 QA · 외부 자문 합의)

외부 AI 자문(Grok/ChatGPT/Gemini/DeepSeek/Kimi/Claude)을 대조한 뒤 QA가 채택한 운영 기준이다. **3모델 다수결로 Alert Level을 확정하지 않는다.** 최종 권위는 `calculate_alert_assessment` 가드레일과 사람 5항목 검수다.

#### 10.4.1 축 분리 (직교 감사)

| 모델 | 담당 축 | 허용 출력 | 사람 검수 대응 열 | 입력에 넣지 말 것 |
|---|---|---|---|---|
| `tev1:latest` | 경보 단계 | `NORMAL` / `WATCH` / `WARNING` / `CRITICAL` / `INSUFFICIENT_EVIDENCE` | `reviewer_decision`(단계 수용 여부) | **산식 Alert 단계**, 타 모델 출력, 사람 라벨, cutoff 이후 지식 |
| `gemma2:9b` | 근거 충실도 (claim 단위) | `supported` / `partial` / `unsupported` / `unverifiable_source_missing` | `evidence_quote_supported` | 경보 단계, 해석 수위, 타 모델·사람 라벨 |
| `deepseek-r1:7b` | 해석·비약 | `supported` / `overstated` / `insufficient` (+ `leap_type`) | `interpretation_assessment` | 근거 진위 재판정, 타 모델·사람 라벨. **발령 단계·경보 문장은 입력 가능** |

- 같은 5단계 라벨로 3자 투표하지 않는다.
- Gemma는 claim별 판정 후 시스템이 `worst(claims)`로 롤업한다. 모델이 종합 등급을 내지 않는다.
- Gemma가 `unsupported`이면 DeepSeek는 호출·로그는 남기되 집계 시 `INVALIDATED_BY_UNSUPPORTED_FACT`로 표시한다(가짜 사실 위 논리 평가 무의미).
- 스키마 위반·파싱 실패는 유효 판정이 아니다. 재시도 1회 후 실패 시 사람 검수 큐로 보낸다.

#### 10.4.2 최소 출력 스키마 (필드명 고정)

공통: `alert_id`, `schema_version`, `model_id`, `input_snapshot_id` (선택: `leak_suspect` — 확정이 아니라 트리거 신호).

```json
{"alert_id":"A-…","schema_version":"v1","stage_verdict":"WARNING","basis_fields":["source_count","verification_state"],"note":"…"}
```
```json
{"alert_id":"A-…","schema_version":"v1","claims":[{"id":"E-01","fact_verdict":"partial","matched_span":"…","gap_type":"modality_mismatch"}]}
```
```json
{"alert_id":"A-…","schema_version":"v1","inference_verdict":"overstated","leap_type":"causal_leap","cited_evidence_ids":["E-01"],"note":"…"}
```

#### 10.4.3 사람 검수 Stage 1 / Stage 2 (블라인드)

1. `data_cutoff` 이전 원문·출처·산식 단계·경보 요약만 제공. **모델 3종 출력 마스킹.**
2. 사람 5항목 작성 후 `stage1_locked=true`로 보존. 이후 덮어쓰지 않는다.
3. 잠금 확인 뒤에만 모델 출력을 공개(Stage 2). 번복은 `human_final_*` 별도 필드 + 변경 사유.
4. 모델은 사람 라벨을 입력으로 받지 않는다. 모델 간에도 서로의 출력을 공유하지 않는다.
5. 2인 검수가 가능하면 검수자 간 블라인드. 1인이면 “모델 미열람”만 강제하고 `single_reviewer_provisional`로 표시한다.

#### 10.4.4 사람 검수 강제 트리거

다음 중 하나면 `needs_human_review=true` (불일치는 오류 확정이 아니라 감사 지정이다).

| ID | 조건 | 비고 |
|---|---|---|
| T1 | tev1 `stage_verdict` ↔ 산식 Alert 단계 불일치 | tev1은 산식 단계를 보지 않은 독립 판정이어야 함 |
| T2 | Gemma `worst` ∈ {unsupported, unverifiable_source_missing} | 단계와 무관(환각 무관용) |
| T3 | (산식 또는 tev1) ≥ WARNING 이고 Gemma = partial | |
| T4 | (산식 또는 tev1) ≥ WARNING 이고 DeepSeek ∈ {overstated, insufficient} | INVALIDATED면 T4만으로 확정하지 않음 |
| T5 | Gemma ≠ supported 이고 DeepSeek ≠ supported (동시) | 이중 결함 |
| T6 | tev1 = INSUFFICIENT_EVIDENCE | |
| T7 | 임의 모델 `leak_suspect=true` | 사람 확정 전제 |
| T8 | All-pass 중 무작위 ≥15% 또는 배치당 최소 표본 | `RANDOM_AUDIT_SAMPLE`. Warning·확인 필요는 기존 §4대로 강제 포함 |

- `NORMAL`↔`WATCH`만 불일치이고 Gemma·DeepSeek가 모두 supported이면 **우선순위만 낮춤**. 로그는 남긴다.
- 3모델이 모두 “괜찮다”여도 **자동 accept 금지**. 모두 “나쁘다”여도 **자동 reject 금지**.

#### 10.4.5 의미 있는 불일치 vs 노이즈 (요약)

| tev1 | Gemma | DeepSeek | 취급 |
|---|---|---|---|
| WARNING+ | unsupported | overstated | 최우선 감사 |
| WARNING+ | unsupported | supported | 의미 있음 (근거 붕괴) |
| WARNING+ | supported | overstated | 의미 있음 (비약) |
| WARNING+ | partial | supported | 경계 — 사람 판단 |
| WARNING+ | supported | supported | 정상 후보 (자동 accept 금지, T8 표본 가능) |
| NORMAL/WATCH | unsupported | * | 의미 있음 (과소·근거 문제) |
| INSUFFICIENT_EVIDENCE | * | * | 의미 있음 |
| NORMAL | supported | supported | 노이즈 후보 (로그 유지, T8만) |

#### 10.4.6 보고 KPI (만장일치율 제외)

분모는 **사람 검수 완료 경보 수**(TEST fixture·tev1 시운전 단독 행 제외).

- 산식↔tev1 단계 불일치 건수 및 그중 accept/revise/reject 비율
- 근거 미지원·unverifiable 건수 및 사람 판정 비율
- 해석 과장·insufficient 건수 및 사람 판정 비율
- Stage1→Stage2 판정 번복률
- 스키마/실행 실패 건수, 미검수 건수, T8 표본 거짓음성 발견 건수

금지: “검증단 일치율=정확도”, “환각 0%”, “NIST 준수 증명”, tev1 10건을 Human acceptance로 보고.

#### 10.4.7 구현 경계

- QA 소유: 본 절, 사람 검수 열, `validation_backtest_log` / `false_alarm_missed_signal_log` 표현, 벤치마크 **해석 수위**.
- LLM 세션: 모델 라우팅·프롬프트·호출. **산식·임계값 변경 금지.**
- DB 세션: 완료 판정만 `alert_validation_audit`에 append-only.
- 완료 조건 인터페이스: `reviewer_decision` ∈ {accept, revise, reject} 이고 5항목·`reviewed_at`·`stage1_locked`가 채워진 행만 DB 적재 대상.
