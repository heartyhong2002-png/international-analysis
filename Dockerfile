# Python 3.13 리눅스 기반 경량 컨테이너 환경
FROM python:3.13-slim

# 필수 시스템 패키지 및 UTF-8 로케일 설정
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-mysql-client \
    curl \
    git \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 파이썬 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 코드 복사
COPY . .

CMD ["python", "scripts/run_pipeline.py", "--collect-only"]
