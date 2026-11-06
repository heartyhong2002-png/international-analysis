# Apache Airflow 가이드: Docker 기반 조기경보 오케스트레이션 파이프라인

본 문서는 Apache Airflow 2.10.2를 Docker Compose 기반으로 가동하여,
공급망·지정학 리스크 조기경보 시스템을 안정적으로 오케스트레이션하는 가이드입니다.

---

## 1. 아키텍처 및 DAG 구조

- **DAG ID**: `early_warning_risk_pipeline` (`dags/early_warning_pipeline_dag.py`)
- **스케줄**: `0 */4 * * *` (매 4시간마다 무인 자율 구동)
- **주요 특징**:
  1. **수집기 동시 병렬 실행**: 해협, 백악관/각국 정부 RSS, 싱크탱크, 트렌드, 무인 이상징후 스캐너 병렬 가동
  2. **장애 격리 (Fault Isolation)**: 개별 소스 실패 시에도 배리어가 `none_failed_min_one_success`로 진행
  3. **지능형 전처리**: `scripts/pipeline/bridge_preprocess_lanes.py` 로 레인 원시 데이터를 정형화

---

## 2. Airflow 실행 명령어 (PowerShell / 터미널)

> [!NOTE]
> Docker Desktop이 켜져 있는 상태에서 프로젝트 루트에서 실행합니다.
> MySQL 스택(`docker-compose.mysql.yml`)과 별도입니다.

### 0) 환경 파일 준비 (최초 1회) — 시크릿 없이 기동 불가
```powershell
cp .env.airflow.example .env.airflow
# .env.airflow 에서 아래를 강한 값으로 교체하세요 (절대 git 커밋 금지):
#   POSTGRES_PASSWORD, AIRFLOW__CORE__FERNET_KEY, _AIRFLOW_WWW_USER_PASSWORD
#   MYSQL_PASSWORD  (DAG DB 적재용; MYSQL_HOST=mysql → 공유 네트워크 intl_analysis_net)
#   NOTION_API_KEY  (선택, Notion 동기화 태스크용)

# 로컬 프리플라이트 (값 미출력). 파일 없음/빈 값/예시 placeholder 면 즉시 실패:
./scripts/ops/airflow_preflight.sh
```

> [!IMPORTANT]
> `.env.airflow` 는 gitignore 대상입니다. 저장소에는 `.env.airflow.example` 템플릿만 둡니다.
> **시크릿 강제:** Compose는 (1) 필수 `env_file: .env.airflow`, (2) `MYSQL_PASSWORD` / `AIRFLOW__CORE__FERNET_KEY` 등 `${VAR:?…}` 명시 주입,
> (3) `airflow-preflight` 서비스가 placeholder/빈 값이면 exit 1 — webserver/scheduler는 preflight 성공 전에는 기동하지 않습니다.
> MySQL 스택만 쓸 때는 `docker-compose.mysql.yml` + `.env` 를 쓰며 `.env.airflow`가 필요 없습니다.
>
> **Airflow ↔ MySQL:** 호스트 포트(`127.0.0.1:3306`)가 아니라 Docker 네트워크 `intl_analysis_net` 으로 연결합니다.
> MySQL을 먼저 올리거나 `docker network create intl_analysis_net` 후 Airflow를 시작하세요.
> `MYSQL_HOST=mysql`. `host.docker.internal` / `0.0.0.0` 공개는 쓰지 않습니다.

Fernet 키 생성 예시:
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 1) 권장: 원클릭 기동 (프리플라이트 + 네트워크 + compose)
```powershell
# (권장) MySQL 먼저 — intl_analysis_net 생성
docker compose -f docker-compose.mysql.yml --env-file .env up -d

./scripts/ops/start_airflow.sh
```

### 2) 수동: 최초 DB 초기화 + 관리자 계정 생성
```powershell
docker compose --env-file .env.airflow up airflow-preflight airflow-init
```
(`--env-file` = Compose 변수 치환, `env_file:` = 컨테이너 환경 주입. 둘 다 `.env.airflow`.)

### 3) 수동: Airflow 전체 컨테이너 가동 (백그라운드)
```powershell
docker compose --env-file .env.airflow up -d
```
- 구동되는 서비스:
  - `airflow-preflight` (시크릿 검사 후 종료 — 실패 시 스택 중단)
  - `postgres` (Airflow 메타데이터 DB)
  - `airflow-webserver` (웹 관제 화면, **127.0.0.1:8080** 루프백)
  - `airflow-scheduler` (스케줄러 & LocalExecutor)
- DB/Notion DAG 태스크는 컨테이너 env의 `MYSQL_*` / `NOTION_API_KEY`를 사용합니다 (시크릿 파일 마운트 없음).

### 4) Airflow Web UI 접속
- 브라우저 주소: `http://127.0.0.1:8080`
- 로그인: `.env.airflow`의 `_AIRFLOW_WWW_USER_USERNAME` / `_AIRFLOW_WWW_USER_PASSWORD`
- 새 DAG는 기본적으로 **paused** 상태입니다. UI에서 토글로 활성화하세요.

### 5) 컨테이너 종료
```powershell
docker compose --env-file .env.airflow down
```
(볼륨까지 초기화: `docker compose --env-file .env.airflow down --volumes`)

---

## 3. 웹 UI 관제 포인트

1. `early_warning_risk_pipeline` DAG 활성화 (토글 ON)
2. **Graph View** 클릭:
   - 수집기가 병렬 실행되는 흐름 확인
   - 각 박스(태스크)별 상태: 초록색(성공), 빨간색(실패), 주황색(재시도 대기)
3. **특정 태스크만 재실행**:
   - 실패한 박스를 클릭 → `Clear` 버튼으로 해당 태스크만 재실행

## 4. Host Ollama 연동

컨테이너는 `OLLAMA_HOST=http://host.docker.internal:11434` 를 기본으로 사용합니다.
호스트에서 Ollama가 떠 있어야 LLM 분석 태스크가 동작합니다.
