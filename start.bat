@echo off
cd /d "%~dp0"

if not exist .env (
    echo ERROR: .env file not found.
    echo Copy .env.example to .env and fill in your API keys.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Starting server (http://localhost:8000) ...
start "DataWarehouse" cmd /c "call venv\Scripts\activate.bat && uvicorn backend.main:app --host 0.0.0.0 --port 8000"

echo.
echo Running!
echo   App:     http://localhost:8000
echo   API docs: http://localhost:8000/docs
echo.
pause
