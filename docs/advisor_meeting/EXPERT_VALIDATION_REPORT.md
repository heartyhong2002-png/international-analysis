# 국제정세 조기경보 시스템 전문가·커뮤니티 이중 검증 보고서

- **작성일**: 2026-11-18
- **대상**: 지도교수님 · 연구실 대학원생 (1차 내부 전문가 검수) 및 Bluesky 공개 전문가/커뮤니티 (2차 외부 피드백)
- **검증 원칙 (`VALIDATION_PLAN.md`)**: 본 시스템은 미래 사건 발생 여부를 예측하는 도구가 아니라, **특정 시점 공개 원문을 과장·왜곡 없이 출처·근거 문장·경보 수위에 연결했는지**를 감사하는 조기경보 프로토타입입니다. AI 다수결·자동 승인(`auto_accept`)은 전면 금지되며 최종 권위는 결정론적 산식 가드레일과 사람 검수에 있습니다.

---

## 1. 모델 및 검증 역할 분리 아키텍처

번역·요약 생성 모델이 자신의 출력을 스스로 채점하는 편향(Self-Grading)을 원천 차단하기 위해, 생성 트랙과 검증 트랙의 모델 계열을 완전히 분리했습니다.

| 계층 | 구성 요소 / 모델 | 담당 역할 | 격리·가드레일 원칙 |
| :--- | :--- | :--- | :--- |
| **생성·번역 트랙** | `qwen2.5:7b` · `exaone3.5:7.8b` · `llama3.1:8b` | 다국어 원문 팩트 추출, 한국어 브리핑, 영문 정제 | 검증단 참여 금지 (생성 전용) |
| **결정론적 가드레일** | `calculate_alert_assessment()` | 출처 수·다양성·근거 커버리지·신호 괴리 기반 공식 경보 산출 | LLM 자의적 판단 제어 |
| **독립 배심원 1 (단계)** | `tev1:latest` | 요약 신호 기반 5단계 경보 수위 독립 판정 | 산식 단계·타 모델 출력 비공개 |
| **독립 배심원 2 (사실)** | `gemma2:9b` | `evidence_phrases` 원문 대조 (claim 단위 사실성 감사) | 빈 근거 시 `unverifiable_source_missing` |
| **독립 배심원 3 (논리)** | `nemotron-3-nano:4b` | 사실→경보 추론의 과잉 해석·인과 비약 반박 | 타 모델 출력 비공개 |
| **재판관 (종합 초안)** | `mistral:7b` *(보조 판결관)* | 배심원 3종 판정 + Trigger(`T1~T8`) 종합, 한국어 쟁점 요약 | **최종 확정권 없음** (`auto_accept=false`) |
| **인간 검증 Track 1** | **지도교수님 · 연구실 대학원생** | 블라인드 5항목 검수 + 도메인 전문 판단(`domain_review_needed`) | Stage 1 잠금 후 Stage 2 AI 결과 대조 |
| **인간 검증 Track 2** | **Bluesky 공개 전문가·이용자** | 검수 완료 브리프 게시 후 댓글·반례 수집·전처리·보정 | 전문가 대체물 아님 (보조 교차 신호로 분리) |

---

## 2. 연구실(교수님·대학원생) × Bluesky 이중 검증 운영 절차

1. **Step 1 — 연구실 내부 블라인드 검수 (Stage 1)**: 아래 **3장(블라인드 검수지)**에서 원문 근거와 산식 경보만 보고 5항목 및 도메인 전문 의견을 먼저 기록합니다. *(편향 방지를 위해 AI 배심원·재판관 의견은 부록으로 분리)*
2. **Step 2 — AI 검증단과 교차 대조 (Stage 2)**: Stage 1 기록을 잠근 뒤 **부록**의 AI 검증단 판정(`gemma2`, `nemotron`, `mistral` 등)을 열어 사람이 놓친 환각·논리 비약이 있는지 비교합니다.
3. **Step 3 — Bluesky 외부 피드백 연계 (확장 트랙)**: 연구실 1차 검수를 통과한 분석 요약을 Bluesky에 게시해 외부 연구자·현업자의 댓글/반론을 수집하고, 스팸 필터링·근거 추출 전처리를 거쳐 최종 브리프 수정에 반영합니다.

---

## 3. [Stage 1] 연구실 전문가 블라인드 검수지 (총 7개 권역)

> **검수 안내**: 국제정치의 미래를 맞히는 것이 아니라, **(1) 제시된 근거 문장이 요약을 실제로 뒷받침하는지**, **(2) 경보 수위가 과장되지 않았는지**, **(3) 군사·외교적 의도나 현지 맥락 등 도메인 전문가 해석이 추가로 필요한지**를 표시해 주세요.

### 3.1. `Latin_America_Mexico` (`SG-Latin_America_Mexico`)

- **분석 시각**: `2026-11-13 01:11:41`
- **산식 1차 경보**: `확인 필요` (`INSUFFICIENT_EVIDENCE`) | **위험 점수**: `29.0`
- **수집 메타**: 출처 `83`건 · 출처 다양성 `1` · 근거 커버리지 `20.0%`
- **한국어 헤드라인**: [Latin_America_Mexico] 비교 신호 부족 — 추가 수집 및 확인 필요
- **한국어 브리핑**: 공식 발표 또는 독립 언론 측의 지정학·경제 비교 기사가 부족하여 경보 산정을 보류합니다.
- **산식 사유**: 공식·독립 신호의 비교 근거 또는 근거 문장이 부족해 경보 단계 판단을 보류함
- **제시된 근거 문장 (`evidence_phrases`)**:
(제시된 원문 근거 문장 없음 — 근거 부족 / 확인 필요 대상)

| 검수 항목 | 선택지 (체크) | 비고 / 수정 의견 |
| :--- | :--- | :--- |
| 1) **경보 단계 적절성** | `[ ] accept`  `[ ] revise`  `[ ] reject` | |
| 2) **근거 문장 지원** | `[ ] supported`  `[ ] partial`  `[ ] unsupported` | |
| 3) **출처 품질** | `[ ] primary`  `[ ] reputable_secondary`  `[ ] unknown` | |
| 4) **해석 수위(비약 여부)** | `[ ] supported`  `[ ] overstated`  `[ ] insufficient` | |
| 5) **오류 유형** | `[ ] none` `[ ] evidence_gap` `[ ] overclaim` `[ ] false_alarm_candidate` | |
| 6) **도메인 전문 검토 필요** | `[ ] yes` *(외교의도·현지선전·공급망)*  `[ ] no` | |

### 3.2. `Japan_EastAsia` (`SG-Japan_EastAsia`)

- **분석 시각**: `2026-11-13 01:11:41`
- **산식 1차 경보**: `확인 필요` (`INSUFFICIENT_EVIDENCE`) | **위험 점수**: `29.0`
- **수집 메타**: 출처 `50`건 · 출처 다양성 `1` · 근거 커버리지 `20.0%`
- **한국어 헤드라인**: [Japan_EastAsia] 비교 신호 부족 — 추가 수집 및 확인 필요
- **한국어 브리핑**: 공식 발표 또는 독립 언론 측의 지정학·경제 비교 기사가 부족하여 경보 산정을 보류합니다.
- **산식 사유**: 공식·독립 신호의 비교 근거 또는 근거 문장이 부족해 경보 단계 판단을 보류함
- **제시된 근거 문장 (`evidence_phrases`)**:
(제시된 원문 근거 문장 없음 — 근거 부족 / 확인 필요 대상)

| 검수 항목 | 선택지 (체크) | 비고 / 수정 의견 |
| :--- | :--- | :--- |
| 1) **경보 단계 적절성** | `[ ] accept`  `[ ] revise`  `[ ] reject` | |
| 2) **근거 문장 지원** | `[ ] supported`  `[ ] partial`  `[ ] unsupported` | |
| 3) **출처 품질** | `[ ] primary`  `[ ] reputable_secondary`  `[ ] unknown` | |
| 4) **해석 수위(비약 여부)** | `[ ] supported`  `[ ] overstated`  `[ ] insufficient` | |
| 5) **오류 유형** | `[ ] none` `[ ] evidence_gap` `[ ] overclaim` `[ ] false_alarm_candidate` | |
| 6) **도메인 전문 검토 필요** | `[ ] yes` *(외교의도·현지선전·공급망)*  `[ ] no` | |

### 3.3. `Global_Trade_Investigative` (`SG-Global_Trade_Investigative`)

- **분석 시각**: `2026-11-13 01:11:41`
- **산식 1차 경보**: `확인 필요` (`INSUFFICIENT_EVIDENCE`) | **위험 점수**: `29.0`
- **수집 메타**: 출처 `50`건 · 출처 다양성 `1` · 근거 커버리지 `20.0%`
- **한국어 헤드라인**: [Global_Trade_Investigative] 비교 신호 부족 — 추가 수집 및 확인 필요
- **한국어 브리핑**: 공식 발표 또는 독립 언론 측의 지정학·경제 비교 기사가 부족하여 경보 산정을 보류합니다.
- **산식 사유**: 공식·독립 신호의 비교 근거 또는 근거 문장이 부족해 경보 단계 판단을 보류함
- **제시된 근거 문장 (`evidence_phrases`)**:
(제시된 원문 근거 문장 없음 — 근거 부족 / 확인 필요 대상)

| 검수 항목 | 선택지 (체크) | 비고 / 수정 의견 |
| :--- | :--- | :--- |
| 1) **경보 단계 적절성** | `[ ] accept`  `[ ] revise`  `[ ] reject` | |
| 2) **근거 문장 지원** | `[ ] supported`  `[ ] partial`  `[ ] unsupported` | |
| 3) **출처 품질** | `[ ] primary`  `[ ] reputable_secondary`  `[ ] unknown` | |
| 4) **해석 수위(비약 여부)** | `[ ] supported`  `[ ] overstated`  `[ ] insufficient` | |
| 5) **오류 유형** | `[ ] none` `[ ] evidence_gap` `[ ] overclaim` `[ ] false_alarm_candidate` | |
| 6) **도메인 전문 검토 필요** | `[ ] yes` *(외교의도·현지선전·공급망)*  `[ ] no` | |

### 3.4. `Russia` (`SG-Russia`)

- **분석 시각**: `2026-11-13 01:15:19`
- **산식 1차 경보**: `경보` (`WARNING`) | **위험 점수**: `69.7`
- **수집 메타**: 출처 `70`건 · 출처 다양성 `2` · 근거 커버리지 `53.3%`
- **한국어 헤드라인**: 러시아 공식 발표와 독립 언론 간의 보도 괴리로 인한 지정학적 위험 신호 상승
- **한국어 브리핑**: 러시아의 공식 매체는 주로 군사 및 지정학적 이슈에 초점을 맞추고 있는 반면, 독립 언론은 리더십 변화와 인도주의적 협력 가능성에 더 큰 관심을 보이고 있어, 관측된 위험 신호가 증가하고 있습니다. 이 괴리는 지정학적 불확실성을 증폭시키므로, 한국 정부와 기업은 관련 지역의 공급망 영향 점검과 지속적인 추적 관찰이 필요합니다. 특히, 군사 훈련과 인도주의적 제안 사이의 맥락 변화를 면밀히 모니터링해야 합니다.
- **산식 사유**: 신호 괴리와 자료량이 함께 높아 담당자 확인이 필요함
- **제시된 근거 문장 (`evidence_phrases`)**:
- `[E-01]` Belarus capable of giving immediate crushing response to enemy — defense minister: According to Viktor Khrenin, a training exercise involving territorial defense troops is currently underway in the Mogilev Region
- `[E-02]` Путин предложил провести вместе с Украиной гуманитарную операцию в Константиновке — как в Алешках: Президент РФ Владимир Путин перед началом встречи со спецпосланниками президента США Стивом Уиткоффом и Джаредом Кушнером предложил организовать гуманитарную операцию в Константиновке в Донецкой области

| 검수 항목 | 선택지 (체크) | 비고 / 수정 의견 |
| :--- | :--- | :--- |
| 1) **경보 단계 적절성** | `[ ] accept`  `[ ] revise`  `[ ] reject` | |
| 2) **근거 문장 지원** | `[ ] supported`  `[ ] partial`  `[ ] unsupported` | |
| 3) **출처 품질** | `[ ] primary`  `[ ] reputable_secondary`  `[ ] unknown` | |
| 4) **해석 수위(비약 여부)** | `[ ] supported`  `[ ] overstated`  `[ ] insufficient` | |
| 5) **오류 유형** | `[ ] none` `[ ] evidence_gap` `[ ] overclaim` `[ ] false_alarm_candidate` | |
| 6) **도메인 전문 검토 필요** | `[ ] yes` *(외교의도·현지선전·공급망)*  `[ ] no` | |

### 3.5. `China` (`SG-China`)

- **분석 시각**: `2026-11-13 01:15:41`
- **산식 1차 경보**: `경보` (`WARNING`) | **위험 점수**: `69.7`
- **수집 메타**: 출처 `40`건 · 출처 다양성 `2` · 근거 커버리지 `53.3%`
- **한국어 헤드라인**: 중국 공식 발표와 독립 언론 간의 보도 괴리로 인한 지정학적 위험 신호 상승
- **한국어 브리핑**: 관측된 위험 신호: 중국의 공식 매체는 국제 관계 이슈에 초점을 맞추고 있는 반면, 독립 언론은 국내 경제적 어려움과 디지털 접근성 문제에 더 큰 관심을 보이고 있어 보도 프레임 괴리가 두드러집니다. 이는 국내 경제 불안과 지정학적 긴장이 복합적으로 작용하는 상황을 반영합니다. 추적 관찰 필요: 한국 정부와 기업은 이러한 괴리를 통해 중국 내 경제 불안 요인과 지정학적 변화를 면밀히 모니터링해야 하며, 특히 공급망 안정성을 점검하여 잠재적인 영향을 최소화하는 전략을 마련해야 합니다.
- **산식 사유**: 신호 괴리와 자료량이 함께 높아 담당자 확인이 필요함
- **제시된 근거 문장 (`evidence_phrases`)**:
- `[E-01]` Turkey said Wednesday Israel's new announcements of settlement construction is provocative despite international warnings, a Turkish official statement said.
- `[E-02]` Workers start every month deep in the red as inflation guts official wages and forces reliance on side hustles.

| 검수 항목 | 선택지 (체크) | 비고 / 수정 의견 |
| :--- | :--- | :--- |
| 1) **경보 단계 적절성** | `[ ] accept`  `[ ] revise`  `[ ] reject` | |
| 2) **근거 문장 지원** | `[ ] supported`  `[ ] partial`  `[ ] unsupported` | |
| 3) **출처 품질** | `[ ] primary`  `[ ] reputable_secondary`  `[ ] unknown` | |
| 4) **해석 수위(비약 여부)** | `[ ] supported`  `[ ] overstated`  `[ ] insufficient` | |
| 5) **오류 유형** | `[ ] none` `[ ] evidence_gap` `[ ] overclaim` `[ ] false_alarm_candidate` | |
| 6) **도메인 전문 검토 필요** | `[ ] yes` *(외교의도·현지선전·공급망)*  `[ ] no` | |

### 3.6. `Middle_East` (`SG-Middle_East`)

- **분석 시각**: `2026-11-13 01:16:07`
- **산식 1차 경보**: `경보` (`WARNING`) | **위험 점수**: `69.7`
- **수집 메타**: 출처 `40`건 · 출처 다양성 `2` · 근거 커버리지 `53.3%`
- **한국어 헤드라인**: 중동 권역, 이란의 공식 입장과 독립 언론 보도 간 괴리로 관측된 위험 신호 상승
- **한국어 브리핑**: 중동 권역에서 이란의 공식 매체는 외부 위협에 대한 방어적 입장을 강조하며 현재 상황 유지에 초점을 맞추고 있지만, 독립 언론은 경제 제재의 영향과 사회적 불안을 더 상세히 다루고 있어 보도 프레임 괴리가 관찰됩니다. 이러한 괴리는 이란 내부의 경제적 어려움과 사회적 불만이 외부에 덜 전달되고 있음을 시사합니다. 따라서 한국 정부와 기업은 이란과의 공급망 안정성을 점검하고 지정학적 리스크 변화를 지속적으로 추적 관찰해야 합니다.
- **산식 사유**: 신호 괴리와 자료량이 함께 높아 담당자 확인이 필요함
- **제시된 근거 문장 (`evidence_phrases`)**:
- `[E-01]` The enemy’s plan must be foiled: In an article, Kayhan examined what it described as the enemy’s objective in spreading reports about the possible resumption of war. The newspaper argued that preserving the current situation is not in Iran’s interest...
- `[E-02]` عن الاقتصاد السوري... المليارات في المصارف والأموال تتحرك في حقائب: كيف تحوّل القطاع المصرفي السوري من أداة للتنمية إلى نظام معزول؟ تكشف الأزمة أثر العقوبات والفساد والكاش على المواطنين والتجارة وفرص إعادة الإعمار.

| 검수 항목 | 선택지 (체크) | 비고 / 수정 의견 |
| :--- | :--- | :--- |
| 1) **경보 단계 적절성** | `[ ] accept`  `[ ] revise`  `[ ] reject` | |
| 2) **근거 문장 지원** | `[ ] supported`  `[ ] partial`  `[ ] unsupported` | |
| 3) **출처 품질** | `[ ] primary`  `[ ] reputable_secondary`  `[ ] unknown` | |
| 4) **해석 수위(비약 여부)** | `[ ] supported`  `[ ] overstated`  `[ ] insufficient` | |
| 5) **오류 유형** | `[ ] none` `[ ] evidence_gap` `[ ] overclaim` `[ ] false_alarm_candidate` | |
| 6) **도메인 전문 검토 필요** | `[ ] yes` *(외교의도·현지선전·공급망)*  `[ ] no` | |

### 3.7. `United_States_Policy_Tech` (`SG-United_States_Policy_Tech`)

- **분석 시각**: `2026-11-13 01:16:31`
- **산식 1차 경보**: `경보` (`WARNING`) | **위험 점수**: `69.7`
- **수집 메타**: 출처 `60`건 · 출처 다양성 `2` · 근거 커버리지 `53.3%`
- **한국어 헤드라인**: 미국 정책 기술 권역 내 공식 보도와 독립 언론 간 보도 괴리 심화 관측
- **한국어 브리핑**: 관측된 위험 신호: 미국 공식 매체는 국내 행정 절차에 초점을 맞추고 있는 반면, 독립 언론은 의회 내부 정치 갈등과 비판을 강조하고 있어 보도 프레임 괴리가 두드러집니다. 이는 국내 이슈에 대한 강조와 함께 지정학적 영향력에 대한 잠재적 불확실성을 시사합니다. 추적 관찰 필요: 한국 정부와 기업은 이러한 정치적 불안정성과 관련된 국제 정책 변화를 지속적으로 모니터링해야 합니다. 공급망 영향 점검 필요: 특히 기술 및 외교 분야에서의 변화에 민감하게 반응하여 공급망 리스크를 점검하고 대응 전략을 마련해야 합니다.
- **산식 사유**: 신호 괴리와 자료량이 함께 높아 담당자 확인이 필요함
- **제시된 근거 문장 (`evidence_phrases`)**:
- `[E-01]` STATEMENT OF CONSENT: U.S. PASSPORT ISSUANCE TO A CHILD U.S. Department of State (.gov)
- `[E-02]` Democrats accuse GOP of helping Trump put ‘fox in the henhouse’ at top watchdog: They warn that Republicans are driving a “sham” process to pick the next Government Accountability Office head. <img src="https://static.politico.com/36/4d/4cd24d93458b8d9643c573206fb5/2026-0128-congress-francis-5-1-3...

| 검수 항목 | 선택지 (체크) | 비고 / 수정 의견 |
| :--- | :--- | :--- |
| 1) **경보 단계 적절성** | `[ ] accept`  `[ ] revise`  `[ ] reject` | |
| 2) **근거 문장 지원** | `[ ] supported`  `[ ] partial`  `[ ] unsupported` | |
| 3) **출처 품질** | `[ ] primary`  `[ ] reputable_secondary`  `[ ] unknown` | |
| 4) **해석 수위(비약 여부)** | `[ ] supported`  `[ ] overstated`  `[ ] insufficient` | |
| 5) **오류 유형** | `[ ] none` `[ ] evidence_gap` `[ ] overclaim` `[ ] false_alarm_candidate` | |
| 6) **도메인 전문 검토 필요** | `[ ] yes` *(외교의도·현지선전·공급망)*  `[ ] no` | |

---

## 4. Bluesky 외부 커뮤니티 피드백 연계 설계 (참고)

- **게시 단위**: Stage 1 검수를 거친 권역별 요약 카드 + 출처 링크 + 핵심 질문 1줄
- **수집·전처리**: 공개 API(`app.bsky.feed.getPostThread`)로 답글 수집 ➔ 봇·욕설·단순 감탄 필터링 ➔ 근거 링크 포함 반론/보강 의견만 추출
- **반영 원칙 (`VALIDATION_PLAN.md` §10.2)**: Bluesky 댓글은 **도메인 전문가 검토의 대체물이 아니며**, 연구실/전문가 검수표와 분리된 `external_feedback` 보조 지표로만 기록합니다.

---

## [부록 · Stage 2] AI 독립 검증단 실측 감사 결과 (Stage 1 검수 완료 후 대조용)

- **감사 생성 시각**: `2026-11-18T10:07:56.224357+00:00`
- **주의**: 아래 표는 사람 검수 Stage 1을 먼저 마친 뒤 대조용으로만 확인합니다.

| 권역 | 산식 | `tev1` (단계) | `gemma2` (근거) | Critic (논리) | Judge (권고) | Trigger Flags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Latin_America_Mexico` | `INSUFFICIENT_EVIDENCE` | `INSUFFICIENT_EVIDENCE` | `unverifiable_source_missing` | `supported` | `reject_candidate` | `T2, T6` |
| `Japan_EastAsia` | `INSUFFICIENT_EVIDENCE` | `INSUFFICIENT_EVIDENCE` | `unverifiable_source_missing` | `supported` | `revise_candidate` | `T2, T6` |
| `Global_Trade_Investigative` | `INSUFFICIENT_EVIDENCE` | `INSUFFICIENT_EVIDENCE` | `unverifiable_source_missing` | `supported` | `revise_candidate` | `T2, T6` |
| `Russia` | `WARNING` | `WARNING` | `supported` | `overstated` | `revise_candidate` | `T4` |
| `China` | `WARNING` | `WARNING` | `partial` | `overstated` | `revise_candidate` | `T3, T4, T5` |
| `Middle_East` | `WARNING` | `WARNING` | `unsupported` | `overstated` | `revise_candidate` | `T2, T5` |
| `United_States_Policy_Tech` | `WARNING` | `WARNING` | `unsupported` | `overstated` | `revise_candidate` | `T2, T5` |
