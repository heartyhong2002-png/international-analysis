# MySQL 데이터베이스 통합 — 작업 요약 (2026-09-08 기준)

다른 채팅으로 이어서 작업할 때 참고용 문서. "국제정세 분석" 프로젝트에서 흩어진 CSV/JSON
수집 결과를 MySQL로 통합한 작업 전체를 정리했습니다.

## 1. 왜 이 작업을 했나

포트폴리오 관점에서 SQL/DB 다루는 능력을 보여주기 위해, 그동안 `data/issues/`,
`data/gov_announcements/`에 CSV/JSON으로 흩어져 있던 수집 결과를 정규화된 MySQL DB로
통합했습니다. JOIN/GROUP BY가 실제로 되는 쿼리를 만들어서 이력서/면접 자료로 쓸 수 있게
하는 게 목적입니다.

## 2. 관련 스크립트 (전부 `scripts/` 폴더 안)

| 파일 | 역할 |
|---|---|
| `issue_data_collector.py` | Wikipedia 관심도 + FRED 경제지표 + 제재 데이터 + IMF 무역 수집 |
| `gov_announcements_collector.py` | 한국 외교부(RSS) + 미국 국무부(RSS) 정부 발표 수집, 이슈별 키워드 매칭 |
| `build_database.py` | 위 두 스크립트가 만든 CSV/JSON을 읽어서 MySQL로 적재 |
| `run_pipeline.py` | 위 세 개를 순서대로 한 번에 실행하는 오케스트레이터 |

### `run_pipeline.py` 사용법

```
python scripts\run_pipeline.py                # 전체 파이프라인 (수집 + DB 적재)
python scripts\run_pipeline.py --resume        # Wikipedia 수집만 --resume 모드로
python scripts\run_pipeline.py --skip-gov      # 정부 발표 재수집 생략
python scripts\run_pipeline.py --only-db       # 수집 생략, build_database.py만 실행
```

## 3. MySQL 설치 상태

- 로컬 컴퓨터(Windows)에 **MySQL Server 8.0과 8.4가 둘 다 설치**되어 있음 (`C:\Program Files\MySQL\`
  아래 두 폴더 다 존재). `services.msc`에서 어느 쪽이 실제로 3306 포트에서 돌고 있는지 확인 가능.
  지금까지는 이 중 하나가 3306에서 정상적으로 응답해서 문제없이 접속됨.
- `mysql.exe` (CLI 클라이언트)가 PATH에 등록 안 되어 있었음 → 사용자가 직접 시스템
  환경변수에 추가함. PowerShell/CMD를 새로 열어야 반영됨 (VS Code는 완전히 껐다 켜야 함).
- MySQL Workbench도 설치되어 있음. **스키마 목록이 자동 새로고침 안 되니, 새 DB 만들고 나면
  Workbench의 새로고침 아이콘을 눌러야 보임.**

## 4. `.env` 설정

`build_database.py`는 `python-dotenv`로 프로젝트 루트의 `.env`를 읽습니다. MySQL 관련
변수는 이제 `.env`에 명시적으로 들어가 있습니다 (2026-09-08 업데이트). 로컬 root 계정에
비밀번호가 걸려 있어서, 예전처럼 빈 비밀번호로는 `Access denied for user 'root'@'localhost'`가
납니다. `.env`에 아래 5개 변수가 있어야 접속됩니다:

```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=<로컬 root 비밀번호>   # 실제 값은 .env 파일에만 (git 추적 안 됨)
MYSQL_DATABASE=international_analysis
```

- 실제 비밀번호 문자열은 이 문서에 적지 않습니다 — `DATABASE_SETUP.md`는 커밋 대상이라
  평문 비밀번호가 git 이력에 남기 때문입니다. 값은 `.env`에만 두고, `.env`는 `.gitignore`에
  등록되어 있습니다 (추적 안 됨 확인 완료).
- 코드 기본값은 여전히 `MYSQL_PASSWORD=""`(빈 문자열)이라, `.env`가 없거나 해당 줄이 빠지면
  접속 실패합니다.
- Claude Desktop MCP 연동 시에도 같은 5개 값을
  `%APPDATA%\Claude\claude_desktop_config.json`의 `international-analysis-mysql` 서버
  `env` 블록에 넣습니다.

(DB 자체는 없어도 `build_database.py`가 `CREATE DATABASE IF NOT EXISTS`로 자동 생성함)

필요 패키지 (프로젝트가 실제로 쓰는 파이썬 인터프리터 기준으로 설치 필요):
```
pip install mysql-connector-python python-dotenv
```

## 5. DB 스키마 (`international_analysis`) — 테이블 10종 + 뷰 4종

### 5.1 기본 테이블 (10개)

| 테이블 | Primary/Unique Key | 비고 |
|---|---|---|
| `issue_summary` | (issue, collected_date) | 이슈별 intensity/article_count. 날짜별로 누적됨 |
| `wikipedia_pageviews` | (issue, keyword, date) | 위키백과 일별 조회수 (30일치 시계열) |
| `gov_announcements` | id (AUTO_INCREMENT), UNIQUE(link(768)) | 외교부/국무부 발표문 원문 (`source_type` 컬럼 포함) |
| `issue_gov_match` | (announcement_id, issue) | gov_announcements ↔ issue 다대다 매칭 테이블 |
| `official_statement_extractions` | id (AUTO_INCREMENT), FK(announcement_id) | LLM이 정부 발표문에서 추출한 핵심 주장 및 정책 액션 |
| `tone_review_log` | id (AUTO_INCREMENT), UNIQUE(article_id, issue_ids) | ADR-001 3단계 휴먼인더루프 톤/감성 검수 로그 (206+건) |
| `expert_analysis_extractions` | id (AUTO_INCREMENT), UNIQUE(article_id) | 싱크탱크/전문가 칼럼에서 추출한 전망 및 스탠스 데이터 |
| `fred_indicators` | (indicator, date) | WTI 유가, 환율, 금리 등 거시경제 지표 |
| `sanctions` | (country, collected_date) | OpenSanctions 제재 건수 통계 |
| `imf_trade` | (pair, year, flow, collected_date) | 국가쌍 수출입 무역 데이터 |
| `analysis_reports` | (report_type, issue_key, collected_date) | 생성된 정세 분석 리포트 전문(LONGTEXT) 및 데스크톱 저장 경로 |

모든 테이블에 `collected_date`(수집 시점)와 `source_file`(또는 `file_path`)이 있어서 이력
추적이 가능합니다. `REPLACE INTO`/`INSERT IGNORE` + 위 키 제약으로, 스크립트를 여러 번
실행해도 중복이 쌓이지 않습니다(멱등성).

> **💡 보고서 자동 저장 위치**:
> - 분석보고서 폴더: `C:\Users\홍준기\Desktop\international-analysis\분석보고서`
> - 프로젝트 내: `reports/issues/` 및 `reports/`
> - DB: `international_analysis.analysis_reports` 테이블에 마크다운 전문 및 메타데이터 자동 적재 (`scripts/report_db_saver.py`)

---

### 5.2 포트폴리오용 4대 고급 분석 뷰 (`scripts/create_views.sql`)

면접 및 포트폴리오에서 **고급 SQL(Window 함수, CTE, 피벗 조건부 집계)** 역량을 증명하기 위해
구축된 분석 뷰입니다:

1. **`v_issue_public_vs_gov_daily` (대중 관심도 7일 이동평균 & 외교 대응 시차 뷰)**
   - **기법**: `AVG() OVER (ROWS 6 PRECEDING)` (7일 이동평균), `LAG()` (전일 대비 증감율 DoD %)
   - **용도**: 대중의 검색량 급증과 정부의 공식 발표 간의 시계열적 반응 시차(Lag) 분석

2. **`v_issue_media_framing_summary` (언론 성향별 프레이밍 & 톤 분석 뷰)**
   - **기법**: `CASE WHEN` 피벗 조건부 집계, 톤별 비율(%) 정규화
   - **용도**: 동일 이슈에 대한 매체 유형(뉴스 vs 현지언론 vs 국영매체) 및 성향(Left, Center, Right)별 보도 톤 비교

3. **`v_human_in_the_loop_audit` (ADR-001 모델 품질 및 정확도 감사 뷰)**
   - **기법**: 혼동 행렬(Confusion Matrix) 집계, 검수 커버리지 % 및 모델 정확도(Agreement Rate %) 산출
   - **용도**: LLM 1차 라벨과 사람 2차 검수 간 일치율 측정 및 과잉비판(Over-critical) 오분류 모니터링

4. **`v_issue_geopolitical_risk_matrix` (지정학적 리스크 매트릭스 & 외교 사각지대 뷰)**
   - **기법**: 다중 CTE(`WITH`), Window 순위 함수 `DENSE_RANK() OVER (ORDER BY intensity DESC, total_gov ASC)`
   - **용도**: 대중 관심도(`intensity`)는 최상위인데 정부 발표가 전무한 사각지대 이슈(`CRITICAL_GAP`) 자동 탐지

---

### 5.3 포트폴리오/면접 추천 대표 쿼리 (Top 4)

```sql
-- 1. 외교적 사각지대(관심 극대 / 정부 발표 전무) 이슈 Top 5
SELECT attention_gap_rank, issue, public_intensity, total_gov_matches, diplomatic_status
FROM v_issue_geopolitical_risk_matrix
ORDER BY attention_gap_rank LIMIT 5;

-- 2. ADR-001 LLM 모델 분류 정확도 및 인간 검수율
SELECT language, source_type, total_samples, human_reviewed_count,
       review_coverage_pct, model_accuracy_pct, llm_over_critical_count
FROM v_human_in_the_loop_audit;

-- 3. 특정 이슈에 대한 매체 성향별(Left/Center/Right) 비판적 보도 비중
SELECT issue, source_type, outlet_bias, total_articles, critical_pct
FROM v_issue_media_framing_summary
WHERE issue = 'Trump_Economy'
ORDER BY total_articles DESC;

-- 4. 특정 이슈의 일별 대중 관심도 7일 이동평균 및 정부 개입 여부
SELECT issue, date, total_pageviews, pageviews_7d_ma, dod_growth_pct, gov_reaction_flag
FROM v_issue_public_vs_gov_daily
WHERE issue = 'Israel_Palestine' AND date >= '2026-09-01'
ORDER BY date DESC;
```

`build_database.py`를 실행하면 데이터 적재 후 위 뷰들을 자동 생성(`create_views.sql`)하고,
검증 쿼리 결과를 콘솔에 자동으로 출력합니다.

## 6. 이번 작업 중 실제로 발견/수정한 버그 (중요 — 재발 방지용 기록)

1. **FRED/제재 데이터가 아예 저장이 안 되고 있었음** — `issue_data_collector.py`에서
   `fetch_fred_issue_indicators()`/`fetch_sanctions_data()` 결과가 메모리에서만 쓰이고
   파일로 저장된 적이 없었음. `fred_indicators_{date}.csv`, `sanctions_{date}.csv`로
   저장하도록 수정.

2. **작업 디렉터리에 따라 data 폴더 위치가 달라지는 버그** — `DATA_DIR = "data/issues"`처럼
   상대경로로 되어 있어서, 터미널을 프로젝트 루트에서 여느냐 `scripts/` 폴더에서 여느냐(또는
   VS Code Run 버튼)에 따라 서로 다른 곳에 데이터가 쌓였음. `issue_data_collector.py`,
   `gov_announcements_collector.py`, `build_database.py` 세 개 다 스크립트 파일 위치
   기준(`scripts/data/...`)으로 고정해서, 어디서 실행하든 항상 같은 폴더를 쓰게 수정.
   **실제 데이터는 항상 `scripts/data/` 밑에 있음** (프로젝트 루트의 `data/`는 예전 버전이 남긴
   레거시 폴더라 지금은 안 씀).

3. **`build_database.py`가 MySQL 접속 실패해도 종료 코드 0(성공)을 반환하던 버그** —
   `run_pipeline.py`처럼 subprocess로 호출하는 쪽에서 실패를 못 알아채는 문제였음.
   접속 실패 시 `sys.exit(1)`로 수정.

4. **한국 외교부(MOFA) RSS 피드 한글이 전부 깨져서 저장되던 버그** — 예전에 "MOFA 피드는
   EUC-KR"이라고 확인해서 하드코딩해뒀는데, 그 사이에 외교부가 인코딩을 UTF-8로 바꿈. 코드는
   여전히 EUC-KR로 강제 디코딩해서 한글이 전부 깨진 채(`寃곌낵` 같은 식) DB에 들어가고
   있었고, 그 결과 `match_issue()`의 한글 키워드 매칭도 안 되고 있었음. RSS 응답의 XML 선언
   (`<?xml ... encoding="...">`)을 파싱해서 인코딩을 자동 감지하도록 수정 — 하드코딩된 값에
   의존하지 않아서 나중에 또 바뀌어도 안전함. 실제 라이브 피드로 직접 검증 완료.
   **주의**: 이 버그가 있었을 때 수집된 예전 `gov_announcements` 행들(깨진 한글 제목)이
   DB에 남아있을 수 있음 — 필요하면 정리(삭제) 작업 별도로 하면 됨.

## 7. 아직 안 끝난 것 / 다음에 할 일

- `issue_gov_match` 카운트가 27로 늘어난 것 최종 확인 (MOFA 인코딩 수정 후 재수집·재적재 반영)
- OpenSanctions API 401 에러 — `.env`의 `OPENSANCTIONS_API_KEY`가 잘려서 등록됐을 가능성
  있음(표준 32자보다 짧음). 아직 미해결.
- 예전 깨진 한글로 들어간 `gov_announcements` 행 정리(선택 사항)
- **다음 큰 작업**: 이 MySQL 데이터를 가지고 대시보드 만들기 (Tableau 대체 스킬 어필용)
- `mysql` CLI를 PATH에 등록했으니, 앞으로는 전체 경로 안 쓰고 그냥 `mysql -u root -p`로
  접속 가능 (새 터미널에서)
