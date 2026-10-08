# 대시보드 세션 인수인계 프롬프트

먼저 `PROJECT_CONTEXT.md`와 `AGENT_SYNC.md`를 읽고 현재 프로젝트 방향과 다른 AI 세션의 작업 상태를 확인해줘.

이 프로젝트는 국제정세 예측 서비스가 아니라 공급망·지정학 리스크 조기경보 시스템이다. 대시보드는 확정 사실이나 미래 예측을 발표하는 화면이 아니라, 여러 센서에서 관측된 위험 신호와 검증 상태를 사람이 빠르게 검토하는 컨트롤타워 화면이다.

## 이번 대시보드 작업의 목표

첫 화면에서 특정 국가나 단일 이슈가 화면을 독점하지 않도록 **5대 감시축을 동일한 우선순위로 보여주는 이슈 균형 UI**를 유지한다.

5대 감시축:

1. Maritime — 해협·항만·AIS·선박 우회·대기시간
2. Energy — 유가·LNG·전쟁보험료·에너지 운송
3. Information — GDELT·국제/현지 언론·공개 Telegram·공개 포럼·검색 트렌드
4. Finance / Trade — 운임·금융·무역·시장 프록시
5. State / Actor — 정부 발표·군 발표·무장단체 공개 주장·공식 입장 변화

각 축에는 현재 상태, 대표 지표, 가장 강한 경보 후보, `verification_state`, 결합된 센서와 마지막 관측 시각을 표시한다.

## 현재 Figma 시안

- 파일: [Balanced Watchboard](https://www.figma.com/design/pTJxYxSF0Fv6PuEicHVAhI)
- 주요 프레임 ID: `1:2`
- 시안에는 5대 감시축 카드, 축별 후보 사건 목록, 근거 커버리지, 데이터 품질 영역이 있다.
- 상단에는 `ELEVATED SUPPLY-CHAIN RISK / IMMEDIATE REVIEW REQUIRED` 비상 배너와 `WARNING · 2 AXES` 상태 표시가 추가되어 있다.
- 시각적 목표는 어두운 관제센터와 비상상황의 긴장감이지만, 색상만으로 위험을 확정하지 않고 검증 상태와 근거를 함께 보여주는 것이다.

## 구현 대상 파일

- `scripts/dashboard/generate_dashboard_v2.py`
- `scripts/dashboard/streamlit_dashboard.py`
- `output/dashboard/index.html`
- 필요 시 `data/event_cross_verification/verification_latest.json`
- 필요 시 DB 뷰 `v_cross_verified_events_summary`, `v_chokepoint_supply_chain_radar`

작업 시작 전에 `git status --short`를 확인하고, Active Work Board에서 위 파일을 다른 도구가 수정 중인지 확인한다. 기존 사용자 수정은 덮어쓰지 않는다.

## 반드시 지킬 데이터 표현 규칙

- 단일 GDELT·Telegram·AIS·시장 신호만으로 Alert Level을 올리지 않는다.
- `UNVERIFIED`, `PARTIALLY_CONFIRMED`, `CROSS_VERIFIED`, `REFUTED`를 구분한다.
- `complete=false`인 부분 수집은 부분 커버리지로 표시한다.
- SNS·Telegram·포럼 데이터는 국민 전체 여론이 아니라 온라인 정보환경 신호로 표시한다.
- 정부·군·무장단체 발표는 주장 또는 공식 입장으로 저장하고 실제 사건과 분리한다.
- 기사량이나 검색량만으로 위험도를 추론하지 않는다.
- 대시보드에는 `source_url`, `observed_at`, `published_at`, `license/access_note`를 추적할 수 있어야 한다.

## UI 개선 우선순위

1. 5대 감시축 카드의 시각적 균형 유지
2. 비상 배너와 전체 경보 상태의 명확한 표시
3. 축별 대표 후보 사건과 검증 상태 표시
4. 결합된 센서 목록과 마지막 관측 시각 표시
5. 부분 수집·데이터 공백·인간 검토 필요 상태 표시
6. 모바일보다 데스크톱 컨트롤타워 화면을 우선하되, 카드가 특정 국가 중심으로 재편되지 않도록 유지

작업 종료 시 `AGENT_SYNC.md` 또는 `project-handoff.md`에 변경 파일, 실행·검증 결과, 다음 작업, 충돌 주의점을 짧게 기록해줘.

