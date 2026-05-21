@echo off
cd /d "%~dp0"

if not exist packages (
    echo ERROR: packages\ folder not found.
    echo Run download_packages.bat first.
    pause
    exit /b 1
)

if not exist .env (
    echo WARNING: .env file not found. ZIP will be created without it.
    echo Fill in .env before transferring to the offline server.
)

echo [Step 1/2] Building React frontend...
cd web
call npm run build
if errorlevel 1 (
    echo ERROR: React build failed.
    pause
    exit /b 1
)
cd ..

set ZIPNAME=personal_data_warehouse.zip

if exist %ZIPNAME% del %ZIPNAME%

echo [Step 2/2] Creating %ZIPNAME% ...

powershell -Command ^
  "Compress-Archive -Path 'backend','web\dist','packages','requirements.txt','setup_offline.bat','start.bat' -DestinationPath '%ZIPNAME%' -Force"

if exist .env (
    powershell -Command ^
      "Compress-Archive -Path '.env' -Update -DestinationPath '%ZIPNAME%'"
)

echo.
echo Done: %ZIPNAME%
echo Transfer this file to the offline server, extract it, then run setup_offline.bat.
pause
