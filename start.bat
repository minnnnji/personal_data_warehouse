@echo off
cd /d "%~dp0"

if not exist .env (
    echo ERROR: .env file not found.
    echo Copy .env.example to .env and fill in your API keys.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Starting backend (http://localhost:8000) ...
start "Backend" cmd /c "call venv\Scripts\activate.bat && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo Starting frontend (http://localhost:8501) ...
start "Frontend" cmd /c "call venv\Scripts\activate.bat && streamlit run frontend\app.py --server.port 8501"

echo.
echo Running!
echo   Backend API: http://localhost:8000/docs
echo   Frontend:    http://localhost:8501
echo.
pause
