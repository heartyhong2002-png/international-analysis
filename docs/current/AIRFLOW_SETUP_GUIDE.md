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

### 0) 환경 파일 준비 (최초 1회)
```powershell
cp .env.airflow.example .env.airflow
# .env.airflow 에서 POSTGRES_PASSWORD, AIRFLOW__CORE__FERNET_KEY,
# _AIRFLOW_WWW_USER_PASSWORD 를 강한 값으로 교체하세요.
```

Fernet 키 생성 예시:
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 1) 최초 DB 초기화 + 관리자 계정 생성
```powershell
docker compose --env-file .env.airflow up airflow-init
```

### 2) Airflow 전체 컨테이너 가동 (백그라운드)
```powershell
docker compose --env-file .env.airflow up -d
```
- 구동되는 서비스:
  - `postgres` (Airflow 메타데이터 DB)
  - `airflow-webserver` (웹 관제 화면, **127.0.0.1:8080** 루프백)
  - `airflow-scheduler` (스케줄러 & LocalExecutor)

### 3) Airflow Web UI 접속
- 브라우저 주소: `http://127.0.0.1:8080`
- 로그인: `.env.airflow`의 `_AIRFLOW_WWW_USER_USERNAME` / `_AIRFLOW_WWW_USER_PASSWORD`
- 새 DAG는 기본적으로 **paused** 상태입니다. UI에서 토글로 활성화하세요.

### 4) 컨테이너 종료
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
