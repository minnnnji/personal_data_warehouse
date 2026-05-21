# create_package.ps1 — React 빌드 후 배포용 ZIP 생성
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# packages 폴더 확인
if (-not (Test-Path (Join-Path $root "packages"))) {
    Write-Host "ERROR: packages\ folder not found. Run download_packages.bat first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# .env 경고
if (-not (Test-Path (Join-Path $root ".env"))) {
    Write-Host "WARNING: .env file not found." -ForegroundColor Yellow
}

# Step 1: React 빌드
Write-Host "[Step 1/3] Building React frontend..." -ForegroundColor Cyan
Set-Location (Join-Path $root "web")
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: React build failed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Set-Location $root

# Step 2: ZIP 생성
$zipPath = Join-Path $root "personal_data_warehouse.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }

Write-Host "[Step 2/3] Creating $zipPath ..." -ForegroundColor Cyan

$toZip = @(
    (Join-Path $root "backend"),
    (Join-Path $root "web\dist"),
    (Join-Path $root "packages"),
    (Join-Path $root "requirements.txt"),
    (Join-Path $root "setup_offline.bat"),
    (Join-Path $root "start.bat")
)

Compress-Archive -Path $toZip -DestinationPath $zipPath -Force

if (Test-Path (Join-Path $root ".env")) {
    Compress-Archive -Path (Join-Path $root ".env") -Update -DestinationPath $zipPath
}

# Step 3: 검증
Write-Host "[Step 3/3] Verifying..." -ForegroundColor Cyan
Add-Type -Assembly System.IO.Compression.FileSystem
$z = [IO.Compression.ZipFile]::OpenRead($zipPath)
$entries = $z.Entries | ForEach-Object { $_.FullName }
$z.Dispose()

Write-Host "  backend/ : $(($entries | Where-Object { $_ -like 'backend*' }).Count) files"
Write-Host "  dist/    : $(($entries | Where-Object { $_ -like 'dist*' }).Count) files"
Write-Host "  packages/: $(($entries | Where-Object { $_ -like 'packages*' }).Count) files"

Write-Host ""
Write-Host "Done: personal_data_warehouse.zip" -ForegroundColor Green
Write-Host "Server에서 압축 해제 후 setup_offline.bat 실행하세요."
Read-Host "Press Enter to exit"
