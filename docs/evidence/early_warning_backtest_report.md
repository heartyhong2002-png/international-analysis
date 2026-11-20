# 조기경보 백테스트 사례 템플릿 (시뮬레이션 · 비공식)

**완화·동기화:** 2026-11-05 (Validation·QA)  
**상태:** 서술용 시뮬레이션 초안. `data/validation_backtest_log.csv`에 동결 입력·사람 판정이 적재되기 전까지 **공식 성능·포트폴리오 수치로 쓰지 않는다.**  
**검증 질문:** 당시 이용 가능한 자료만으로 위험 신호를 근거와 함께 일관되게 포착·설명할 수 있었는가?  
**다자간 판정 기준:** `docs/current/VALIDATION_PLAN.md` §10.4

생성 스크립트 하드코딩 스케치와 혼동하지 말 것. tev1 10건 산식 대조는 별도 JSON이며 Human acceptance가 아니다.

---

## 0. 로그 실측 (동기화 시점)

| 파일 | 상태 |
|---|---|
| `data/validation_backtest_log.csv` | 헤더만 · **0건** |
| `data/false_alarm_missed_signal_log.csv` | 헤더만 · **0건** |
| `data/pending_human_review.csv` | 대기열 존재 · 사람 `reviewer_decision` 완료는 별도 확인 |
| tev1 10건 (`data/tev1_backtest_results.json`) | 산식↔tev1 불일치 감사 · **공식 승인율 아님** |

---

## 1. 예전 4건 시뮬레이션 지표 — 사용 금지

과거 초안에 있던 Human acceptance **75%**, NIST 준수·포착 성공·환각 억제 증명 문구는 **폐기**한다. 하드코딩 가정값이며 실측 로그와 불일치한다.

허용 표현: 제한된 표본·시뮬레이션 스케치·동결 대기·오탐/미탐 후보.  
금지: 75% 검증 완료, NIST 준수 증명, 사건을 맞혔다, 100% 정확, 환각 0%.

---

## 2. 동결 등록 절차 (요약)

1. QA: 관찰 창·기준일만 `validation_backtest_log` 선등록 (2~3건).
2. LLM: cutoff 이전 입력으로 산식·검증단 실행 (§10.4 스키마).
3. QA: Stage1 블라인드 5항목 → Stage2 모델 공개.
4. 오탐/미탐/근거 공백은 `false_alarm_missed_signal_log`에 append.
5. 완료 판정만 DB `alert_validation_audit` append-only.
