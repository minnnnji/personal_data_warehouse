@echo off
cd /d "%~dp0"

echo [Step 1/3] Cleaning old packages folder...
if exist packages rmdir /s /q packages
mkdir packages

echo [Step 2/3] Downloading wheel packages for Python 3.11...
py -3.11 -m pip download -r requirements.txt -d packages\ --only-binary=:all:

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Some packages failed. Check Python 3.11 is installed.
    pause
    exit /b 1
)

echo [Step 3/3] Done!
echo.
echo Transfer these to the offline server:
echo   packages\
echo   requirements.txt
echo   setup_offline.bat
echo   start.bat
echo.
pause
