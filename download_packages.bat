@echo off
cd /d "%~dp0"

echo [Step 1/3] Cleaning old packages folder...
if exist packages rmdir /s /q packages
mkdir packages

echo [Step 2/3] Downloading wheel packages (binary only, no source builds)...
pip download -r requirements.txt -d packages\ --only-binary=:all:

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Some packages failed to download as wheels.
    echo Retrying without --only-binary for those packages...
    pip download -r requirements.txt -d packages\
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
