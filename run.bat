@echo off
cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt

if not exist "data" mkdir data

echo.
echo Starting Chess Federation...
echo http://localhost:5000
echo.
python -c "from app import create_app; create_app().run(debug=True, host='0.0.0.0', port=5000)"
