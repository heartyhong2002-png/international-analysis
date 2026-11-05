# Docker 및 로컬 개발 환경 가이드

**문서 식별자:** `docs/current/DOCKER_AND_WSL_SETUP.md`  
**기준 일자:** 2026-11-03  

---

## 📌 1. 개요

본 프로젝트는 Windows 호스트 환경에서 발생하는 한글 경로 문제, `cp949` 다국어 인코딩 충돌, 로컬 MySQL 설치 복잡도를 해결하기 위해 **Docker 컨테이너(MySQL 8.0)** 및 **WSL2(Ubuntu)** 개발 환경을 지원합니다.

---

## 🐳 2. Docker를 통한 MySQL 8.0 원클릭 실행

로컬 PC에 MySQL을 따로 설치할 필요 없이 Docker Compose로 1초 만에 실행할 수 있습니다.

### 실행 명령어 (터미널)
```bash
# MySQL 컨테이너 백그라운드 실행
docker compose up -d mysql

# (선택) 웹 기반 DB GUI 도구(phpMyAdmin) 함께 실행
docker compose up -d
```

### 접속 정보
* **Host**: `localhost` (컨테이너 내부 통신 시 `mysql`)
* **Port**: `3306`
* **User**: `root`
* **Password**: `jk614623!!` (.env 설정값)
* **Database**: `international_analysis` (초기 구동 시 자동 생성)
* **초기 DDL 뷰 자동 주입**: `scripts/db/create_views.sql` 자동 마운트
* **웹 GUI 관리자 (phpMyAdmin)**: 브라우저에서 `http://localhost:8080` 접속 (Root 계정 로그인)

### 컨테이너 관리
```bash
# 상태 확인
docker compose ps

# 컨테이너 중지 (데이터는 docker volume에 영구 보존됨)
docker compose down
```

---

## 🐧 3. WSL2 (Ubuntu) 환경에서 작업하기

Windows 내에 이미 설치된 `Ubuntu-26.04`를 활용하여 모든 파이썬 스크립트를 Linux UTF-8 환경에서 구동할 수 있습니다.

### 1) Cursor에서 WSL 연결
1. Cursor 에디터 좌측 하단 초록색/파란색 원격 연결 아이콘 클릭 (또는 `Ctrl + Shift + P`)
2. `WSL에 다시 연결 (Connect to WSL)` 선택
3. 터미널이 자동으로 `Ubuntu` bash 셸로 열립니다.

### 2) 파이프라인 무인 자동화 실행 (cron)
Ubuntu 터미널에서 리눅스 크론탭을 통해 주기적 수집을 안전하게 백그라운드로 실행할 수 있습니다.
```bash
# 크론탭 편집
crontab -e

# 매일 오전 6시에 가벼운 수집 실행 예시
0 6 * * * cd /mnt/c/dev/international-analysis && python3 scripts/run_pipeline.py --collect-only >> data/automation/cron.log 2>&1
```
