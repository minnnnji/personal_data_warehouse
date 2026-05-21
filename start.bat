@echo off
REM Personal Data Warehouse — 백엔드 + 프론트엔드 동시 실행
cd /d "%~dp0"

if not exist .env (
    echo 오류: .env 파일이 없습니다.
    echo .env.example 을 복사하고 API 키를 입력하세요.
    pause
    exit /b 1
)

echo 가상 환경 활성화...
call venv\Scripts\activate.bat

echo 백엔드 시작 ^(http://localhost:8000^) ...
start "Backend" cmd /c "venv\Scripts\activate.bat && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo 프론트엔드 시작 ^(http://localhost:8501^) ...
start "Frontend" cmd /c "venv\Scripts\activate.bat && streamlit run frontend\app.py --server.port 8501"

echo.
echo 실행 중!
echo   백엔드  API: http://localhost:8000/docs
echo   프론트엔드:  http://localhost:8501
echo.
echo 창을 닫으면 이 런처만 종료됩니다 ^(백엔드/프론트엔드는 별도 창에서 실행 중^).
pause
