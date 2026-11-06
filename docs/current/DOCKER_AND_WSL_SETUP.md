# Docker 및 로컬 개발 환경 가이드

**문서 식별자:** `docs/current/DOCKER_AND_WSL_SETUP.md`  
**기준 일자:** 2026-11-06  

---

## 📌 1. 개요

본 프로젝트는 Windows 호스트 환경에서 발생하는 한글 경로 문제, `cp949` 다국어 인코딩 충돌, 로컬 MySQL 설치 복잡도를 해결하기 위해 **Docker 컨테이너(MySQL 8.0)** 및 **WSL2(Ubuntu)** 개발 환경을 지원합니다.

---

## 🐳 2. Docker를 통한 MySQL 8.0 원클릭 실행

로컬 PC에 MySQL을 따로 설치할 필요 없이 Docker Compose로 실행할 수 있습니다.

### 사전 준비
```bash
cp .env.example .env
# .env 에서 MYSQL_PASSWORD 등 값을 직접 설정하세요. 비밀번호는 커밋하지 마세요.
```

MySQL 스택은 Airflow용 `docker-compose.yaml` 과 분리된 **`docker-compose.mysql.yml`** 을 사용합니다 (포트 충돌 방지).

### 실행 명령어 (터미널)
```bash
# MySQL 컨테이너 백그라운드 실행
docker compose -f docker-compose.mysql.yml --env-file .env up -d mysql

# (선택) 웹 기반 DB GUI 도구(phpMyAdmin) 함께 실행
docker compose -f docker-compose.mysql.yml --env-file .env up -d
```

### 접속 정보
* **Host**: `127.0.0.1` (컨테이너 내부 통신 시 `mysql`)
* **Port**: `.env`의 `MYSQL_PORT` (기본 `3306`)
* **User**: `.env`의 `MYSQL_USER` (기본 `root`)
* **Password**: `.env`의 `MYSQL_PASSWORD` (필수 — 저장소에 기본값 없음)
* **Database**: `.env`의 `MYSQL_DATABASE` (기본 `international_analysis`)
* **뷰 DDL**: 테이블 생성 후 `mysql … < scripts/db/create_views.sql` 실행
  (`build_database.py`로 스키마/데이터를 만든 뒤 적용)
* **웹 GUI (phpMyAdmin)**: `http://127.0.0.1:8081` (루프백 전용, Airflow 8080과 분리)

### 컨테이너 관리
```bash
docker compose -f docker-compose.mysql.yml --env-file .env ps
docker compose -f docker-compose.mysql.yml --env-file .env down
```

---

## 🐧 3. WSL2 (Ubuntu) 환경에서 작업하기

Windows 내에 이미 설치된 `Ubuntu`를 활용하여 모든 파이썬 스크립트를 Linux UTF-8 환경에서 구동할 수 있습니다.

### 1) Cursor에서 WSL 연결
1. Cursor 에디터 좌측 하단 원격 연결 아이콘 클릭 (또는 `Ctrl + Shift + P`)
2. `WSL에 다시 연결 (Connect to WSL)` 선택
3. 터미널이 자동으로 `Ubuntu` bash 셸로 열립니다.

### 2) 파이프라인 무인 자동화 실행 (cron)
```bash
crontab -e

# 매일 오전 6시에 가벼운 수집 실행 예시
0 6 * * * cd /mnt/c/dev/international-analysis && python3 scripts/run_pipeline.py --collect-only >> data/automation/cron.log 2>&1
```
