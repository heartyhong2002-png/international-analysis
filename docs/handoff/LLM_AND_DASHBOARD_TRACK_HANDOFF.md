# [인수인계] LLM 표본 검수 자동화 및 인터랙티브 HTML 대시보드 구축 완료 보고서

> **작성 일시**: 2026-09-23 23:46 (KST)  
> **담당 트랙**: LLM 트랙 & 시각화/대시보드 트랙  
> **대상**: 다른 Claude 세션 및 프로젝트 관리자(홍준기님)  
> **문서 위치**: `C:\Users\홍준기\Desktop\international-analysis\docs\handoff\LLM_AND_DASHBOARD_TRACK_HANDOFF.md`

---

## 1. 세션 핵심 성과 요약 (Executive Summary)

본 세션에서는 **ADR-001(LLM 역할 정의 및 휴먼-인-더-루프)** 체계의 2단계 검수 자동화와, 별도 웹 서버 구축 없이 브라우저에서 바로 열 수 있는 **독립형 인터랙티브 HTML 대시보드** 구축을 완결했습니다.

1. **ADR-001 2단계 표본 검수 자동화 모듈 신규 개발**:
   - 21개 이슈 확장으로 인한 전수 검수 불가능 문제를 해결하기 위해, 언어 및 이슈별 층화 표본 추출(20%, 취약 모델 100%) 시스템 구축 완료.
   - 검수 전용 시트 생성 ➔ 검수 완료본 역병합(Sync) ➔ 품질 감사 리포팅 파이프라인 완비.
2. **파이프라인 검수 이력 유실 버그 원천 차단**:
   - 수집 파이프라인 재실행 시 기존에 사람이 검수했던 내용(`human_label`, `correction_note`)이 빈칸으로 덮어써져 날아가던 심각한 문제를 해결하고 영구 보존 로직 적용.
3. **독립형 인터랙티브 HTML 대시보드 개발 (시각화 고민 해결)**:
   - 풀스택 웹 서버 배포 부담 없이, 더블클릭만으로 브라우저에서 동작하는 `Chart.js` 기반 다크 테마 대시보드 구축.
   - 지정학적 리스크 레이더(버블 차트), 미디어 프레이밍(스택 바), 정부 발표 출처(도넛), 실시간 검색 & 필터링 피드 테이블 탑재.
4. **전체 파이프라인 통합 완결**:
   - `scripts/run_pipeline.py` 최종 단계에 대시보드 자동 생성을 통합하여 수집-적재-시각화 원클릭 파이프라인 완성.

---

## 2. 생성 및 수정된 파일 맵 (File Map)

| 파일 경로 | 구분 | 핵심 기능 및 변경 내역 |
| :--- | :---: | :--- |
| [`scripts/sample_for_review.py`](file:///c:/Users/홍준기/Desktop/international-analysis/scripts/sample_for_review.py) | **신규** | • 언어/이슈별 층화 표본 추출 (안정 모델 20%, 약점 모델 `ru`/`ar` 100% 전수)<br>• 검수 시트 생성, 완료본 역병합(`--merge`), 혼동 행렬 감사(`--stats`)<br>• 자체 단위 테스트(`--self-test`) 내장 |
| [`scripts/generate_dashboard_v2.py`](file:///c:/Users/홍준기/Desktop/international-analysis/scripts/generate_dashboard_v2.py) | **고도화** | • MySQL 실데이터(21개 이슈, 298건 정부발표, 380건 기사) 직접 쿼리<br>• Chart.js 버블/스택/도넛 차트 렌더링<br>• 실시간 텍스트 검색 및 톤별 탭 필터링 자바스크립트 탑재<br>• `--open` 플래그로 생성 즉시 브라우저 자동 실행 |
| [`prototype_all_in_one.py`](file:///c:/Users/홍준기/Desktop/international-analysis/prototype_all_in_one.py) | **수정** | • `_write_review_log()` 내 기존 인간 검수 내역 영구 보존 패치<br>• CLI 플래그 `--sample-review`, `--sample-rate` 추가 |
| [`scripts/run_pipeline.py`](file:///c:/Users/홍준기/Desktop/international-analysis/scripts/run_pipeline.py) | **수정** | • 파이프라인 최종 단계(Step 2/2)에 `generate_dashboard_v2.py` 자동 실행 추가<br>• Windows 콘솔 UTF-8 인코딩 예외 방지 패치 |
| [`data/pending_human_review.csv`](file:///c:/Users/홍준기/Desktop/international-analysis/data/pending_human_review.csv) | **산출물** | • 174건 기사 중 층화 추출된 검수 대상 **34건**의 작업 전용 시트 |
| [`output/dashboard/dashboard_latest.html`](file:///c:/Users/홍준기/Desktop/international-analysis/output/dashboard/dashboard_latest.html) | **산출물** | • **최종 결과물**: 브라우저에서 바로 열리는 단일 독립형 인터랙티브 대시보드 (`index.html`과 동일) |

---

## 3. 세부 구현 내용

### ① 표본 추출 및 검수 역병합 시스템 (`scripts/sample_for_review.py`)
- **층화 추출 로직**:
  - 언어(`language`)와 대표 이슈(`issue_ids`)를 기준으로 그룹핑하여 특정 대형 이슈(예: `Trump_Economy`)로 표본이 편중되는 현상 방지.
  - 각 계층별로 최소 1건(`min_samples_per_group=1`) 이상 무작위 추출 보장.
  - 약점 모델(아랍어 `Jais`, 러시아어 `Vikhr`): 프롬프트 예시 복사 위험으로 인해 기본 100%(전수 검수) 추출 적용.
- **역병합 (Sync)**:
  - 검수자가 `data/pending_human_review.csv`에서 `human_label`(`우호적`/`중립적`/`비판적`)과 `correction_note`를 작성하고 저장한 뒤,
  - `python scripts/sample_for_review.py --merge data/pending_human_review.csv`를 실행하면 원본 `data/review_log.csv`에 안전하게 반영되고 타임스탬프 자동 갱신.

### ② 독립형 인터랙티브 HTML 대시보드 (`scripts/generate_dashboard_v2.py`)
- **기술 스택**: 순수 HTML5 + CSS3 + Chart.js (CDN) 기반 단일 파일.
- **화면 구성**:
  1. **헤더 & 실시간 상태**: Live Intelligence 상태 및 생성 일시 표기.
  2. **핵심 KPI 카드**: 추적 이슈 수(21개), 외교적 사각지대(Critical Gap 5건), 수집 정부발표(298건), 인간 검수 일치율(60.0%).
  3. **지정학적 리스크 레이더 (Bubble Chart)**: 대중 관심도(X축) vs 정부 대응(Y축) 버블 차트 (사각지대 이슈는 Red 버블 하이라이트).
  4. **미디어 프레이밍 분석 (Stacked Bar Chart)**: 이슈별 우호/중립/비판 비율 비교.
  5. **정부 발표 출처 비중 (Doughnut Chart)**: 한·미·영·독 외교부 등 채널별 비중.
  6. **HITL 감사 요약 카드**: 모델-인간 일치율 및 과잉 비판 오판 분석.
  7. **실시간 인텔리전스 피드 테이블**: 자바스크립트 기반 키워드 검색, 톤별 필터, 원문 링크, LLM 판단 근거 노출.

---

## 4. 검증 결과 (Verification Results)

1. **단위 테스트 (`sample_for_review.py --self-test`)**:
   - 가상 기사 60건 대상 6개 언어 층화 추출, 약점 모델 100% 추출, 역병합 및 타임스탬프 갱신 검증 100% 통과.
2. **실제 데이터 표본 추출**:
   - `data/review_log.csv`의 174건 기사 중 `matched` 및 `ambiguous` 대상 기사에서 대표 표본 **34건**이 [`data/pending_human_review.csv`](file:///c:/Users/홍준기/Desktop/international-analysis/data/pending_human_review.csv)로 성공적으로 추출됨.
3. **통합 파이프라인 구동 (`run_pipeline.py --only-db`)**:
   - MySQL 적재(`build_database.py`) ➔ 대시보드 렌더링(`generate_dashboard_v2.py`) 연쇄 실행 완료 (총 4초 소요, 종료 코드 0).
4. **브라우저 실행 확인**:
   - PowerShell `Start-Process` 및 `explorer.exe`를 통해 사용자 PC 기본 브라우저 및 탐색기에서 [`output/dashboard/dashboard_latest.html`](file:///c:/Users/홍준기/Desktop/international-analysis/output/dashboard/dashboard_latest.html) 실행 확인.

---

## 5. 다음 세션을 위한 빠른 실행 가이드

새 대화방에서 작업을 이어받는 세션은 아래 명령어로 본 세션의 산출물을 즉시 확인하고 활용할 수 있습니다:

```powershell
# 1. 최신 대시보드 생성 및 브라우저 실행
python scripts/generate_dashboard_v2.py --open

# 2. 미검수 기사 표본 추출 (필요 시)
python scripts/sample_for_review.py

# 3. 작성된 검수 파일 원본 DB/CSV에 병합
python scripts/sample_for_review.py --merge data/pending_human_review.csv

# 4. 검수 현황 통계 감사
python scripts/sample_for_review.py --stats

# 5. 전체 파이프라인 실행 (수집부터 대시보드까지 원클릭)
python scripts/run_pipeline.py --only-db
```
