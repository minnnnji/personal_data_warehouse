@echo off
REM [폐쇄망 서버에서 실행 — 더블클릭 가능]
REM venv를 생성하고 오프라인으로 패키지를 설치합니다.
REM 사전 조건: packages\ 폴더와 requirements.txt 가 같은 디렉토리에 있어야 합니다.

cd /d "%~dp0"

if not exist packages (
    echo 오류: packages\ 폴더가 없습니다.
    echo 인터넷 연결된 PC에서 download_packages.bat 을 먼저 실행하고 전송하세요.
    pause
    exit /b 1
)

if not exist requirements.txt (
    echo 오류: requirements.txt 파일이 없습니다.
    pause
    exit /b 1
)

echo 가상 환경 ^(venv^) 생성 중...
python -m venv venv

echo 가상 환경 활성화...
call venv\Scripts\activate.bat

echo 패키지 설치 중 ^(오프라인^)...
pip install --no-index --find-links=packages\ -r requirements.txt

echo.
echo 설치 완료! 앱 실행은 start.bat 을 사용하세요.
pause
