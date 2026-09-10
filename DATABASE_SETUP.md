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

## 5. DB 스키마 (`international_analysis`)

| 테이블 | Primary/Unique Key | 비고 |
|---|---|---|
| `issue_summary` | (issue, collected_date) | 이슈별 intensity/article_count. 날짜별로 누적됨 |
| `wikipedia_pageviews` | (issue, keyword, date) | 위키백과 일별 조회수 |
| `gov_announcements` | id (AUTO_INCREMENT), UNIQUE(source, title, pub_date) | 정부 발표 원문 |
| `issue_gov_match` | (announcement_id, issue) | gov_announcements ↔ issue 다대다 매칭 |
| `fred_indicators` | (indicator, date) | WTI 유가, 환율, 금리 등 |
| `sanctions` | (country, collected_date) | OpenSanctions 제재 건수 |
| `imf_trade` | (pair, year, flow, collected_date) | 국가쌍 수출입 데이터 |

모든 테이블에 `collected_date`(수집 시점)와 `source_file`(원본 파일 경로)이 있어서 이력
추적이 가능합니다. `REPLACE INTO`/`INSERT IGNORE` + 위 키 제약으로, 스크립트를 여러 번
실행해도 중복이 쌓이지 않습니다(멱등성 — 직접 재실행 테스트로 확인함).

### 검증용 샘플 쿼리 (JOIN/GROUP BY)

```sql
-- 이슈별 최신 intensity Top 5
SELECT issue, intensity, article_count, collected_date
FROM issue_summary
WHERE collected_date = (SELECT MAX(collected_date) FROM issue_summary)
ORDER BY intensity DESC LIMIT 5;

-- 이슈별 정부 발표 매칭 건수 (JOIN)
SELECT m.issue, COUNT(*) AS matched_count
FROM issue_gov_match m
JOIN gov_announcements g ON g.id = m.announcement_id
GROUP BY m.issue ORDER BY matched_count DESC;

-- 대중 관심(intensity) vs 정부 발표 매칭 비교 (LEFT JOIN + COALESCE)
SELECT s.issue, s.intensity, COALESCE(g.matched_count, 0) AS gov_matches
FROM issue_summary s
LEFT JOIN (
    SELECT issue, COUNT(*) AS matched_count FROM issue_gov_match GROUP BY issue
) g ON g.issue = s.issue
WHERE s.collected_date = (SELECT MAX(collected_date) FROM issue_summary)
ORDER BY s.intensity DESC LIMIT 10;
```

`build_database.py`를 실행하면 이 세 쿼리를 자동으로 실행해서 콘솔에 결과를 보여줍니다.

### CLI로 직접 확인하는 법

```
mysql -u root -p international_analysis
```
```sql
SHOW TABLES;
SELECT 'issue_summary', COUNT(*) FROM issue_summary
UNION ALL SELECT 'wikipedia_pageviews', COUNT(*) FROM wikipedia_pageviews
UNION ALL SELECT 'gov_announcements', COUNT(*) FROM gov_announcements
UNION ALL SELECT 'issue_gov_match', COUNT(*) FROM issue_gov_match
UNION ALL SELECT 'fred_indicators', COUNT(*) FROM fred_indicators
UNION ALL SELECT 'sanctions', COUNT(*) FROM sanctions
UNION ALL SELECT 'imf_trade', COUNT(*) FROM imf_trade;
```

가장 최근 확인된 결과 (2026-09-08, 수집 2회분 누적):
```
issue_summary        42   (이슈 21개 × 수집 2회)
wikipedia_pageviews 1798
gov_announcements    113
issue_gov_match       26  (MOFA 인코딩 버그 수정 후 재수집하면 27로 늘어남 — 아래 6번 참고)
fred_indicators      900  (처음으로 저장되기 시작한 데이터)
sanctions              5
imf_trade             28
```

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
