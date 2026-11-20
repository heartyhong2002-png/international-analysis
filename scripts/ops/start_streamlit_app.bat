@echo off
REM Start root Streamlit control center on loopback only (127.0.0.1:8501).
REM Matches scripts/console/app.py HOST binding — not for public deploy.
setlocal
cd /d "%~dp0..\.."

set PYTHON_EXE=.\.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" set PYTHON_EXE=python

echo OK: Streamlit control center -^> http://127.0.0.1:8501 (loopback only)
"%PYTHON_EXE%" -m streamlit run app.py --server.address 127.0.0.1 --server.headless true --browser.serverAddress 127.0.0.1
