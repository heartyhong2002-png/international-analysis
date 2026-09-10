@echo off
REM run_pipeline_scheduled.bat — Windows 작업 스케줄러용 프로토타입
REM ================================================================
REM 컨트롤타워 세션이 만든 프로토타입입니다. schtasks로 등록해서 테스트
REM 실행까지 확인했으나(수동 실행 기준), 실제 예약 실행 환경(로그온 안 한
REM 상태 등)에서의 동작은 이어받는 세션에서 재확인 필요합니다.
REM
REM 등록 방법 (관리자 권한 필요 없음, 로그인 계정 기준으로 등록됨):
REM   schtasks /create /tn "국제정세분석_자동수집" ^
REM     /tr "C:\Users\홍준기\Desktop\international-analysis\scripts\run_pipeline_scheduled.bat" ^
REM     /sc daily /st 07:00
REM
REM 확인:
REM   schtasks /query /tn "국제정세분석_자동수집" /v /fo list
REM 삭제:
REM   schtasks /delete /tn "국제정세분석_자동수집" /f
REM
REM ⚠️ 주의: 아래에서 쓰는 파이썬 경로(PYTHON_EXE)가 실제로 requests/pandas/
REM mysql-connector-python이 설치된 그 인터프리터인지 꼭 확인하세요.
REM (이번 세션에서 인터프리터 불일치로 ModuleNotFoundError가 여러 번 났었습니다.)
REM "where python"으로 확인한 경로를 아래에 넣으세요.

setlocal

set PROJECT_DIR=C:\Users\홍준기\Desktop\international-analysis
set SCRIPTS_DIR=%PROJECT_DIR%\scripts
set PYTHON_EXE=python
set LOG_DIR=%PROJECT_DIR%\logs
set LOG_FILE=%LOG_DIR%\pipeline_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%.log

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

cd /d "%SCRIPTS_DIR%"

echo [%date% %time%] 파이프라인 시작 >> "%LOG_FILE%"

REM 1단계: 수집 + DB 적재 (검증 완료, 이미 이번 세션에서 여러 번 테스트함)
"%PYTHON_EXE%" run_pipeline.py >> "%LOG_FILE%" 2>&1

if errorlevel 1 (
    echo [%date% %time%] ✗ run_pipeline.py 실패 (종료 코드 %errorlevel%^) >> "%LOG_FILE%"
    exit /b 1
)

REM 2단계: 대시보드 갱신 (프로토타입 — 실제 DB로 테스트 완료, 로컬에서 재확인 권장)
"%PYTHON_EXE%" generate_dashboard_v2.py >> "%LOG_FILE%" 2>&1

REM 3단계: 분석 리포트 (analyze_signals.py) — 기본은 꺼둠.
REM Ollama가 항상 켜져있어야 하고, 예약 실행 환경에서 로컬 LLM 서버가
REM 살아있는지 확인이 안 된 상태라 컨트롤타워 세션에서는 검증 못 했습니다.
REM 로컬에서 직접 한 번 돌려보고 문제없으면 아래 REM만 지우고 활성화하세요.
REM "%PYTHON_EXE%" analyze_signals.py >> "%LOG_FILE%" 2>&1

echo [%date% %time%] 파이프라인 완료 >> "%LOG_FILE%"

endlocal
