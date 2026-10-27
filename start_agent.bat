@echo off
echo =======================================================
echo          GetMeHired - Autonomous AI Agent
echo =======================================================

REM Check if .env exists, if not copy from .env.example
if not exist ".env" (
    echo [.env] not found. Initializing from .env.example...
    copy .env.example .env
    echo Please customize .env with your target preferences and credentials.
    echo.
)

echo Checking virtual environment...
if not exist ".venv\Scripts\python.exe" (
    echo Error: .venv virtual environment not found!
    echo Please set up your environment by running:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b
)

echo Starting GetMeHired Agent Dashboard...
echo Open your browser at: http://127.0.0.1:8000
echo.
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
pause

