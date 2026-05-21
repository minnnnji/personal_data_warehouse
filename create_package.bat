@echo off
cd /d "%~dp0"

if not exist packages (
    echo ERROR: packages\ folder not found.
    echo Run download_packages.bat first.
    pause
    exit /b 1
)

if not exist .env (
    echo WARNING: .env file not found.
)

echo [Step 1/3] Building React frontend...
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

echo [Step 2/3] Creating %ZIPNAME% ...

rem backend, packages, 스크립트 먼저 압축
powershell -Command "Compress-Archive -Path 'backend','packages','requirements.txt','setup_offline.bat','start.bat' -DestinationPath '%ZIPNAME%' -Force"

rem web\dist 내용을 zip 안에 dist\ 로 추가
powershell -Command "Compress-Archive -Path 'web\dist' -Update -DestinationPath '%ZIPNAME%'"

rem .env 있으면 추가
if exist .env (
    powershell -Command "Compress-Archive -Path '.env' -Update -DestinationPath '%ZIPNAME%'"
)

echo [Step 3/3] Verifying...
powershell -Command " ^
  Add-Type -Assembly System.IO.Compression.FileSystem; ^
  $z = [IO.Compression.ZipFile]::OpenRead('%ZIPNAME%'); ^
  $e = $z.Entries.FullName; ^
  $z.Dispose(); ^
  Write-Host '  backend/ :' ($e -like 'backend*').Count 'files'; ^
  Write-Host '  dist/    :' ($e -like 'dist*').Count 'files'; ^
  Write-Host '  packages/:' ($e -like 'packages*').Count 'files' ^
"

echo.
echo Done: %ZIPNAME%
echo Server에서 압축 해제 후 setup_offline.bat 실행하세요.
pause
