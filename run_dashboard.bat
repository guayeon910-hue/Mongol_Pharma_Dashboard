@echo off
setlocal

cd /d "%~dp0"
set "PYTHONPATH=%CD%"
set "PY=%CD%\.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo Virtual environment not found.
  echo Run:
  echo   python -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  exit /b 1
)

"%PY%" "%CD%\frontend\server.py" --host 127.0.0.1 --port 8765 --open
