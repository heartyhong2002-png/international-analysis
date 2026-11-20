# 국제정세·공급망 조기경보 시스템 — 현황 종합 보고서

- 기준일: 2026-10-31
- 성격: 취업용 개인 포트폴리오 · OSINT 기반 리스크 인텔리전스 프로토타입
- 최종 산출물: `output/dashboard/index.html` (컨트롤타워 조기경보 화면)
- 이 문서는 **예측 적중**이 아니라 **관측 신호·근거·검증 상태·데이터 공백**을 요약한다.

---

## 1. 한 줄 요약

예측 시스템을 폐기하고, 다출처 공개 신호를 교차검증해 사람이 검토할 경보 후보를 제시하는 조기경보 프로토타입이 동작 중이다. HTML 대시보드는 공식 경보 뷰를 읽고, 공식 행이 없으면 임의 Critical을 만들지 않으며, SNS·검색량은 국민 여론이 아닌 온라인 정보환경 신호로 표시한다.

---

## 2. 프로젝트 정체성 (변경되지 않은 원칙)

| 항목 | 현재 기준 |
|---|---|
| 하는 일 | 위험 신호·신호 괴리·Alert Level·근거·검증 상태를 사람에게 제시 |
| 하지 않는 일 | 미래 사건 확정 예측, 발생 보장, “100% 정확/환각 0%” 주장 |
| 성공 질문 | “사건을 맞혔는가”가 아니라 “근거 기반으로 위험 신호를 일관되게 포착·설명할 수 있는가” |
| 검증 | 백테스트·사람 표본 검수·오탐/미탐 후보 기록 (예측 정확도 아님) |

대외 메시지는 “예측의 검증 한계를 발견하고, 이미 구축한 수집·분석 자산을 감사 가능한 조기경보로 재설계했다”이다.

---

## 3. 감시축 구조 (혼동 주의)

두 층위를 구분한다.

### 3.1 이슈 감시축 (6대) — 무엇을 감시하는가

컨트롤타워 2026-10-29 결정:

1. 동아시아 군사·기술
2. 러시아·우크라이나 및 유럽 안보
3. 미국 국내 정치·정책 리스크 (당선 예측 금지 · 정책·제도 신호만)
4. 미국–동맹국 관계
5. 미국–경쟁·대립축 관계 (`adversary/competitor` role tag)
6. 중동 에너지·해운

명시적 비범위: 대선/중간선거 승패 확률, 적대국 전쟁 발발 시점 예측, 자동 게시, 챗봇 전환.

### 3.2 센서 UI 축 (5대) — 대시보드 Balanced Watchboard

1. Maritime
2. Energy
3. Information
4. Finance / Trade
5. State / Actor

센서 축 ≠ 이슈 축. Figma 시안: https://www.figma.com/design/pTJxYxSF0Fv6PuEicHVAhI (프레임 1:2)

---

## 4. 트랙별 현재 상태

### 4.1 대시보드·보고서

| 항목 | 상태 |
|---|---|
| HTML 생성기 `generate_dashboard_v2.py` | 동작. Alert Level은 `v_dashboard_current_alerts`만 사용 |
| `output/dashboard/index.html` | 재생성 가능. 공백/미연결 시에도 화면 유지 |
| Streamlit | Active Work Board상 ANTIGRAVITY 소유(`in-progress`) — 타 세션 비접촉 |
| 표현 교정 (2026-10-28) | Telegram 하드코딩 Critical 제거, “국민 체감 불안도” 제거, ENERGY 임의 WATCH 후보 → 확인 필요, SNS/Trends를 온라인 정보환경 신호로 표기 |
| 미완 | `v_alert_evidence_trace`를 `alert_event_id`로 경보 카드에 연결 |

### 4.2 DB·증거 계층

| 항목 | 상태 |
|---|---|
| `evidence_writer.py` | scoring/gap/alert/evidence/validation 트랜잭션 저장 |
| 공식 뷰 | fixture(`TEST_*`)는 운영 집계에서 제외 |
| 최근 확인된 운영 스냅샷 | `RSS_RUSSIA` Critical · `human_review_required` · `PARTIALLY_CONFIRMED` (임의 생성 아님 · 사람 검수 필요) |
| 주의 | TEST fixture를 precision/성과로 보고하지 않음. `REPLACE INTO` 금지 |

### 4.3 데이터 수집·레지스트리

| 항목 | 상태 |
|---|---|
| source_registry | SCHEMA + government/expert/local_media/opinion/customs YAML 초안 |
| 패킷 A+B registry | Federal Register·Congress·USTR·동맹국 RSS 등 보강. 일부 403/타임아웃 → `enabled:false` 또는 PENDING |
| Media Cloud | `search.mediacloud.org` + Token 인증으로 갱신. 기본 파이프라인 미연결 |
| GDELT Cloud | 기본 비활성. `--with-gdelt-cloud` + 월/일 QU 안전상한 |
| 이상 징후 스캐너 | `scripts/automation/` 초안. Anomaly Score ≠ Alert Level. 기본 파이프라인 미연결 |
| 다음 수집 | Federal Register 선택 수집기. 패킷 C(경쟁·대립축 role)는 A/B 정렬 후 |

### 4.4 런타임·문서·동기화

| 항목 | 상태 |
|---|---|
| Python | 표준 런타임 **3.13** (`.venv`, PR #5) |
| Trio-Sync | MD(`AGENT_SYNC`) ↔ Notion(보드/문서/보고서) ↔ GitHub |
| Notion 허브 | https://app.notion.com/p/3eede224b44181f0bd20ea55620bf5c4 |

### 4.5 LLM·경보 산식

ANTIGRAVITY 소유 영역(`prototype_all_in_one.py`, signal gap/scoring). 대시보드 세션은 임계값·산식을 임의 변경하지 않는다. tev1은 보조 판정이며 공식 Alert Level 공급원이 아니다.

---

## 5. 데이터 계약 (화면·보고서가 지켜야 할 규칙)

1. Alert Level → `v_dashboard_current_alerts`만
2. 근거 → `v_alert_evidence_trace`를 `alert_event_id`로 연결
3. 공식 행 없음 → “확인 필요” 또는 “공식 경보 뷰 연결됨 · 최신 산출 스냅샷 없음”
4. `UNVERIFIED` / `PARTIALLY_CONFIRMED` / `CROSS_VERIFIED` / `REFUTED` 구분
5. `complete=false` → 부분 커버리지
6. SNS·Telegram·포럼 → 국민 여론이 아닌 온라인 정보환경 신호
7. 기사 수·논조·검색량만으로 Critical/Warning 확정 금지
8. 단일 출처로 Alert Level 격상 금지

---

## 6. 열린 다음 작업 (우선순위)

1. 경보 카드에 `v_alert_evidence_trace` 근거 링크 연결 후 HTML 재생성
2. Federal Register 선택 수집기 (`--with-federal-register`) + White House 공통 스키마/dedupe
3. LLM/scoring → `evidence_writer.save_scoring_run` 호출 연결
4. Streamlit 5축 UI는 소유권 확인(ANTIGRAVITY) 후에만
5. 패킷 C: competitor/adversary `relationship_role` 태깅·OFAC/BIS registry
6. 보고서 제목/요약은 “조기경보 근거” 표현 유지 (예측·발생 확정 금지)

---

## 7. 한계와 해석 주의

- 현재 대시보드의 Critical 등은 **확정 사실·미래 예측이 아니라** 공식 뷰에 적재된 검토용 경보 단계다. `human_review_required`이면 추가 검수가 필요하다.
- 교차검증·해협·시장 프록시는 강한 보조 신호이나, AIS·운임만으로 사건 원인을 단정하지 않는다.
- GDELT·Media Cloud·ACLED·Event Registry·White House·Federal Register는 기본 `--collect-only`에서 자동 호출하지 않는 경우가 많다.
- 이 보고서는 포트폴리오·세션 조율용 현황 요약이며, 운영 Alert를 새로 발령하지 않는다.

---

## 8. 관련 문서

- `PROJECT_CONTEXT.md` — 현재 방향 진입점
- `AGENT_SYNC.md` — 세션 작업판·handoff
- `docs/current/PROJECT_PLAN.md` — 6대 이슈 감시축
- `docs/current/VALIDATION_PLAN.md` — 경보 품질 검증
- `docs/current/DASHBOARD_SESSION_PROMPT.md` — 대시보드 UI 계약
- `docs/current/PORTFOLIO_AND_REPORT_GUIDE.md` — 대외 스토리
- `reports/EARLY_WARNING_DELIVERABLES.md` — 화면·제출 산출물 명세
