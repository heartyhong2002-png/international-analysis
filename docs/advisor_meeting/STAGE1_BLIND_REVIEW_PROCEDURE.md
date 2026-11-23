# Stage 1 사람 블라인드 검수 절차 (1장 안내)

- **작성일**: 2026-11-22 · **적용 대상**: 7개 권역 (`data/validation/pending_blind_review_stage1.csv`)
- **규약 근거**: `docs/current/VALIDATION_PLAN.md` §10.4.3(Stage 1/2 블라인드)·§10.4.4(강제 트리거)·§10.4.6(KPI)
- **이 문서의 성격**: 절차 안내만 담습니다. 권역별 AI 판정·재판관 권고는 Stage 1 잠금 후에만 `EXPERT_VALIDATION_REPORT.md` 말미 [부록 · Stage 2]에서 열어봅니다(아래 표에 AI 결과를 옮기면 블라인드가 무너집니다).

## 0. 시작 전 확인 (1회)

```
.venv\Scripts\python.exe scripts\validation\human_blind_review.py --status
```

`Stage 1 잠금 완료 0건 / 7건`이면 아직 검수 미착수 상태입니다. `--status`는 읽기 전용이라 몇 번 실행해도 안전합니다.

## 1. 경로 선택 — 착수 전에 반드시 결정 (되돌릴 수 없음)

| 경로 | Stage 2 번복 기록 | 용도 |
| :--- | :--- | :--- |
| **A. 시트 작성 → `--reveal`** | 번복 입력 창이 없음(`stage2_overridden=False`로 확정) | 엑셀에서 여럿이 나눠 작성한 뒤 일괄 잠금 |
| **B. `--interactive`** | 1건씩 Stage 1 잠금 직후 모델 결과·재판관 권고를 보고 번복 가능 | 번복 기록까지 남길 권역, 1인 순차 검수 |

- 한 번 `stage1_locked=true`가 된 권역은 **두 경로 모두 다시 열지 않습니다**(§10.4.3 2항: 잠금 후 덮어쓰기 금지).
- B는 시트에서 잠기지 않은 권역을 **감사 파일 순서대로 전부** 진행하며, 권역을 골라 받지 않습니다. 섞어 쓰려면 나머지 권역에서 `Ctrl+C`로 중단하면 그때까지 잠긴 분량만 저장되고, 이후 남은 권역은 A로 마저 잠그면 됩니다.
- 단, B로 끝까지 가면 2번째 권역의 Stage 1을 쓰기 전에 1번째 권역의 모델 판정을 열람한 상태가 되어 §10.4.3의 "모델 미열람" 전제가 흐트러집니다. **엄격한 블라인드를 우선하면 A(모든 권역 Stage 1 완료 후 일괄 열람)**, Stage 2 번복 기록을 우선하면 B를 택하세요.

## 2. Stage 1 — 마스킹된 시트에서 5항목 작성

1. 필요 시 시트 재생성(모델 출력 완전 마스킹): `... human_blind_review.py --export`
   - 이미 잠긴 권역의 판정 값은 자동 보존되고, 미잠금 권역만 빈 칸으로 나옵니다.
2. `data/validation/pending_blind_review_stage1.csv`를 **UTF-8(BOM) 유지**로 열어 아래 8칸을 채웁니다. **7개 권역 전부** 작성해야 하며, `확인 필요`(INSUFFICIENT_EVIDENCE) 3개 권역도 검수 대상입니다.

| CSV 열 | 허용값(대소문자 무시, 이 문자열 그대로) |
| :--- | :--- |
| `reviewer_id` | 검수자 ID (비우면 잠금 보류) |
| `reviewer_decision` | `accept` / `revise` / `reject` |
| `evidence_quote_supported` | `supported` / `partial` / `unsupported` |
| `source_quality` | `primary` / `reputable_secondary` / `unknown` |
| `interpretation_assessment` | `supported` / `overstated` / `insufficient` |
| `error_type` | `none` / `evidence_gap` / `overclaim` / `false_alarm_candidate` / `missed_signal_candidate` |
| `domain_review_needed` | `no` / `yes` |
| `stage1_note` | 선택(비어 있어도 잠금 가능) |

3. 볼 것은 이 6개뿐입니다: **분석 시각(`analyzed_at`)·산식 경보 단계·위험 점수/출처 메타·한국어 헤드라인·브리핑·근거 문장(E-01/E-02)**입니다.
   - 근거 문장이 `(근거 문장 없음)`이면 "요약을 뒷받침할 근거가 없다"는 사실 자체를 2번 항목(`unsupported`)으로 기록하면 됩니다.
   - **금지**: `EXPERT_VALIDATION_REPORT.md` §3의 권역 순서와 AI 부록 표를 Side-by-Side로 펼쳐놓고 작성(§10.4.3 1·5항). 2인 검수는 `--dual-blind`로 표기하고 검수자 간에도 결과를 가립니다.
   - 참고: `error_type`의 `missed_signal_candidate`(미탐 후보)는 보고서 검수지 인쇄본 선택지에 없으므로, 미탐 의심 건은 CSV에서 직접 입력하거나 `stage1_note`에 남기세요.

## 3. 잠금 (Stage 1 → Stage 2 경계)

```
.venv\Scripts\python.exe scripts\validation\human_blind_review.py --reveal data/validation/pending_blind_review_stage1.csv
```

- 항목별 허용값 검증 후 통과 건만 `human_blind_reviews.json`에 `stage1_locked=true` + `stage1_locked_at`으로 기록되고, `data/validation/human_blind_review_log.csv`가 갱신됩니다. 미작성·잘못된 값은 `⚠️ ... 잠금 보류` 출력 후 건너뜁니다(부분 잠금 가능, 시트는 그대로).
- 단독 검수면 `review_mode=single_reviewer_provisional`이 자동 기록됩니다(§10.4.3 5항).

## 4. Stage 2 — 잠금 확인 후에만 열기

`data/validation/stage2_comparison_sheet.csv`(잠금 건만 모델 출력 공개) 또는 보고서 [부록 · Stage 2]와 대조해 환각·비약을 확인합니다. 번복은 경로 B에서만 입력되며, Stage 1 원본은 보존되고 `human_final_*` + `stage2_override_reason`만 별도 갱신됩니다.

## 5. 완료 판정 & 다음

- `--status`에서 `Stage 1 잠금 완료 7건 / 7건`이면 §10.4.6 KPI(산식↔tev1 불일치 비율, Stage1→2 번복률, 미검수 0건) 보고가 가능해집니다.
- DB 적재(`alert_validation_audit` append-only)는 5항목 + `stage1_locked`가 채워진 행만 대상입니다(§10.4.7).
- **금지**: 판정 열 임의 기입·덮어쓰기, `stage1_locked` 직접 설정, 시트 재생성으로 사람 작성 행 소실(잠금 전 사람 행이 존재하면 `--export` 대신 현재 시트를 유지하고 `--status`로 현황만 확인).
