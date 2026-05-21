@echo off
REM [인터넷 연결된 PC에서 실행]
REM 모든 의존성을 packages\ 폴더에 다운로드합니다.
REM 완료 후 packages\, requirements.txt, setup_offline.bat 을 폐쇄망 서버로 전송하세요.

cd /d "%~dp0"

echo 패키지 다운로드 시작...
if not exist packages mkdir packages
pip download -r requirements.txt -d packages\

echo.
echo 완료. 폐쇄망 서버로 아래 항목을 전송하세요:
echo   packages\        (전체 폴더)
echo   requirements.txt
echo   setup_offline.bat
echo.
echo 전송 후 서버에서 setup_offline.bat 을 더블클릭하세요.
pause
