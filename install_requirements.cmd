@echo off
echo ==================================================
echo ASA-Log-Bot-NG by jc0839
echo Discord: https://discord.com/invite/QjtT94TsBE
echo ==================================================
echo.
echo Installing Python dependencies...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found. Installing requirements...
echo.

REM Upgrade pip first
python -m pip install --upgrade pip

REM Install requirements
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install some dependencies!
    echo Please check the error messages above.
    pause
    exit /b 1
) else (
    echo.
    echo All dependencies installed successfully!
    echo You can now run the application using run.cmd
    pause
)