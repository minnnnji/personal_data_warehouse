@echo off
cd /d "%~dp0"

if not exist packages (
    echo ERROR: packages\ folder not found.
    echo Run download_packages.bat on an internet-connected PC first.
    pause
    exit /b 1
)

if not exist requirements.txt (
    echo ERROR: requirements.txt not found.
    pause
    exit /b 1
)

echo [Step 1/3] Creating virtual environment...
python -m venv venv

echo [Step 2/3] Activating virtual environment...
call venv\Scripts\activate.bat

echo [Step 3/3] Installing packages offline...
pip install --no-index --find-links=packages\ -r requirements.txt

echo.
echo Done! Run start.bat to launch the app.
pause
