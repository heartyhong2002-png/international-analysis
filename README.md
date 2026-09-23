# 국제정세 분석 (International Affairs Analysis)

**성격:** 교과목/졸업 과제물
**핵심 주제:** 저사양 로컬 환경(16GB RAM, GPU 없음)에서, 오픈소스 다국어 LLM의 주관적 판단(논조 분류·주장 추출)을 어떻게 신뢰 가능하게 만들 것인가. 현재 목표는 국제정세 사건을 단정적으로 예측하는 것이 아니라, 관측 가능한 데이터 신호를 바탕으로 공급망·지정학 리스크의 조기경보를 제공하는 것이다.
**최종 결과물:** `output/dashboard/index.html` — 인터랙티브 HTML 대시보드

---

## 먼저 읽기 — 왜 예측을 조기경보로 바꾸었나

이 프로젝트의 핵심 성과는 미래 사건을 맞히는 AI를 주장하는 데 있지 않다. 초기 예측 접근을 실제로 검토하면서 **정답 정의의 모호성, 장기 검증 필요성, 오탐·미탐 해석의 어려움**을 확인했고, 그 한계를 해결할 수 있도록 목표를 조기경보로 재설계했다.

| 처음의 질문 | 현재의 질문 |
|---|---|
| “앞으로 어떤 사건이 발생할까?” | “현재 위험 신호가 강해졌고, 사람이 먼저 확인할 근거가 충분한가?” |
| 사건 발생 여부로 평가 | 과거 사례 백테스트, 근거 품질, 사람 검수, 오탐·미탐 기록으로 평가 |
| 예측값 중심 | 경보 단계와 출처·근거 중심 |

따라서 이 시스템은 사건 발생을 보장하거나 단정하지 않는다. 공식 발표, 독립 언론, 대중 여론, 금융·무역 지표의 변화를 비교해 **위험 신호**, **출처 간 신호 괴리**, **경보 단계**, **근거 충분도**를 보여 주고 사람이 추가 확인할 대상을 돕는다.

발표·포트폴리오용 설명 구조와 예상 질문 답변은 [docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md](docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md)에 있다.

---

## 1. 이 시스템이 하는 일

RSS 뉴스, 정부 공식 발표, 현지언론·전문가분석, Reddit 여론, 각종 여론조사·경제지표를
수집해서, 언어별로 라우팅된 로컬 LLM(Ollama)이 논조(우호적/중립적/비판적)와 핵심 주장을
뽑아낸다. 이 결과를 이용해 "앞으로 반드시 어떤 사건이 발생한다"고 예측하지 않고,
이슈별 위험 신호가 평소보다 강해졌는지, 공식 발표와 독립·현지 신호 사이의 괴리가 커졌는지,
사람이 주목해야 할 경보 단계가 올라갔는지를 판단한다. LLM 판단은 그대로 신뢰하지 않고
3단계 절차를 거친다:

1. **1차 — LLM 분류**: 고정 루브릭 + 판단 근거 문장과 함께 태깅
2. **2차 — 사람 표본 검수**: 매주 처리분의 15~20% 검수 (실측 일치율 60%, `data/review_log.csv`)
3. **3차 — 교정 피드백**: 사람과 LLM이 갈린 사례를 모아 few-shot 예시로 프롬프트에 반영 (재학습이 아니라 프롬프트 개선 — GPU 없는 환경이라 실제 파인튜닝 불가)

여기에 AllSides 매체 편향 태깅, Google Fact Check API 대조, **미국 NIST AI RMF 1.0(신뢰성 프레임워크)** 가이드라인 기반의 **3개 모델 'LLM-as-a-judge' 앙상블 합의 엔진**을 더하고, 글로벌 IR 전문가 커뮤니티(`r/IRstudies`) 피어 리뷰를 통해 정립한 **방어적 현실주의(Defensive Realism) 6단계 구조 분석**을 적용하여 "모델의 주관적 편향"과 "데이터가 뒷받침하는 객관적 사실(Overlapping Consensus)"을 구분하려 한 것이 이 프로젝트의 기술적 핵심이다.

초기에는 국제정세 사건 예측 시스템을 목표로 했지만, 미래 사건의 정답 정의와 검증 가능성 문제가 커서 현재는 **AI 기반 국제정세 및 공급망 리스크 조기경보 시스템**으로 방향을 전환했다. 변천 과정은 `docs/history/PROJECT_EVOLUTION_TIMELINE.md`에 보존한다.

## 2. 최종 결과물 — 대시보드

```
output/dashboard/index.html      # 최신 빌드
output/dashboard/dashboard_latest.html
```

브라우저로 직접 열면 된다. 재생성하려면:

```bash
python scripts/generate_dashboard_v2.py
```

나머지 산출물(이슈별 심층 리포트, 정통 인텔리전스 폼 PDF·Word 공식 보고서, 일일 분석, 벤치마크 검증 리포트, MySQL
분석 뷰)은 전부 이 대시보드를 뒷받침하는 **증거 자료**로 취급한다 — 각자 별도의
"최종 결과물"이 아니다. 제출·인쇄가 필요하면 `reports/issues/pdf/` 및
`reports/issues/docx/`의 산출물을 사용한다. 로컬 배포용 복사본은 저장소에 유지하지 않는다.

## 3. 실행

```bash
pip install -r requirements.txt   # 없다면 scripts/ 상단 주석의 개별 패키지 참고
ollama serve                      # 별도 터미널에서 켜두기

python scripts/run_pipeline.py    # 수집 → 태깅 → LLM 분석 → DB 적재까지 한 번에
python scripts/generate_dashboard_v2.py
```

개별 단계(정부 발표 수집, 현지언론/전문가분석 수집 등)를 따로 돌리는 방법은
`docs/current/DATA_COLLECTION_GUIDE.md`에 있다.

## 4. 프로젝트 구조 (실제 기준)

```
international-analysis/
├── README.md                    # 외부용 1페이지 소개
├── PROJECT_CONTEXT.md           # 새 AI 세션이 가장 먼저 읽는 현재 방향 안내서
├── prototype_all_in_one.py     # 언어 라우팅·태깅·톤 분류 핵심 로직 (src/ 아님 — 이 파일 하나에 통합됨)
├── scripts/                     # 수집기·DB 적재·리포트/대시보드 생성 스크립트 전부
│   └── data/                    # gov_announcements, issues 등 일부 수집 원본
├── data/                        # 파이프라인이 실제로 쓰는 최신 수집 데이터 (review_log.csv 포함)
├── output/dashboard/            # 최종 결과물
├── reports/                     # 증거 자료용 심층 리포트·PDF·검증 리포트
├── docs/current/                 # 현재 조기경보 방향의 최신 계획 문서
├── docs/handoff/                 # 트랙별 세션 인수인계 문서
├── docs/evidence/                # 백테스트·피어리뷰 등 검증 근거
├── docs/history/                 # 예측/챗봇 등 폐기·보류된 방향의 변천 기록
├── project-handoff.md           # 내부 개발일지 — 세션 간 인수인계, 결정 경위, 작업 로그
└── docs/archive/                # 목적이 끝났거나 방향이 바뀐 문서 보관함 (아래 참고)
```

## 5. 더 읽을거리

- `PROJECT_CONTEXT.md` — 다른 AI/새 세션이 가장 먼저 읽어야 하는 현재 방향 안내서
- `docs/REPOSITORY_STRUCTURE.md` — 폴더별 역할과 이동 기준
- `docs/SESSION_PROMPTS.md` — 7개 작업 세션별 시작 프롬프트
- `project-handoff.md` — 이 프로젝트의 상세한 의사결정 히스토리, 세션 간 조율 기록. 새 세션은 이 파일을 먼저 읽는다.
- `docs/current/LLM_SYSTEM_SUMMARY.md` — LLM 아키텍처 상세
- `docs/current/DATABASE_SETUP.md` — MySQL 스키마
- `docs/current/PROJECT_PLAN.md` — 현재 조기경보 시스템 기준의 최신 프로젝트 계획
- `docs/current/VALIDATION_PLAN.md` — 예측이 아닌 조기경보 기준 검증 계획
- `docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md` — 교수·면접관 대상 발표 흐름, 핵심 메시지, 질문 대응
- `docs/current/DATA_COLLECTION_GUIDE.md` — 조기경보 신호 데이터 수집 기준
- `docs/history/PROJECT_EVOLUTION_TIMELINE.md` — 예측 → 챗봇 검토 → 조기경보 피벗의 의사결정 타임라인
- `docs/archive/legacy_guides/DATA_COLLECTION_GUIDE_legacy.md` — 기존 수집 운영 매뉴얼
- `docs/archive/` — 예전 기획서(`PLANNING.md`), 목적이 달랐던 이슈 정의 문서(`CONTINENTAL_ISSUES_ANALYSIS.md`), 역할이 끝난 인수인계 문서 5종, 예전 README의 26개 항목 전체 개발일지(`DEVELOPMENT_LOG_README_HISTORY.md`)
- `docs/archive/parked_chatbot_pivot/` — 2026-09-20에 검토했던 "챗봇 서비스 전환" 방향 (프로토타입 코드 포함). 결과물을 대시보드로 확정하면서 보류함. 나중에 재검토할 수 있게 삭제하지 않고 남겨둠.

## 6. 알려진 한계 (2026-09-20 기준)

1. 정부 공식 발표 수집(`official_statement`)에서 이스라엘·이란·사우디는 외교부 자체 RSS가 없어 웹 크롤링이 필요한데 아직 미착수.
2. 남미 3개 이슈, 아태 5개 이슈(대만해협 등)는 현지언론/전문가분석 전용 소스를 아직 못 찾음.
3. **[해소됨]** 준기님의 C드라이브 정리(81GB 여유 공간 확보)로 다국어 통합 모델(qwen2.5 몰아주기)을 전면 철회하고 원래의 **6대 권역별 네이티브 전담 모델(`yandex`, `falcon3`, `elyza`, `qwen2.5`, `mistral-nemo`, `exaone3.5`)** 풀로 100% 복구 완료됨.
4. **[데이터 수집 확장 대기]** 권위주의/통제 국가(러시아·중국·중동·이란)의 공식 발표 왜곡을 극복하기 위해, 해외 망명 독립 언론(Meduza, Raseef22), 검열 삭제 아카이브(CDT), 익명 커뮤니티(r/China_irl, r/NewIran)를 연동하는 3자 교차 수집 파이프라인은 향후 '데이터셋 다운로드' 섹션에서 별도 구축 예정.
5. `venv/`와 `.venv/` 가상환경이 동시에 존재함(패키지 버전 불일치 이력 있음) — 하나로 정리 필요.
6. 2차 검수(사람 표본 검수)는 아직 소규모 수동 진행 — 이슈가 21개로 늘면서 무작위 표본 추출 자동화가 필요해짐.

---

*이 문서는 대외적으로 프로젝트를 처음 보는 사람을 위한 1페이지 요약이다. 실제 개발
과정의 상세한 판단 근거·실패 사례·트랙 간 조율 기록은 `project-handoff.md`와
`docs/archive/`에 전부 남아있다.*
