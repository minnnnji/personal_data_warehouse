@echo off
cd /d "%~dp0"

echo [Step 1/2] Downloading packages to packages\ folder...
if not exist packages mkdir packages
pip download -r requirements.txt -d packages\

echo.
echo [Step 2/2] Done!
echo.
echo Transfer these to the offline server:
echo   packages\
echo   requirements.txt
echo   setup_offline.bat
echo   start.bat
echo.
pause
