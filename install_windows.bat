@echo off
setlocal enabledelayedexpansion
echo ============================================
echo  SmartDrive -- Windows Setup
echo ============================================
echo.

echo [1/4] Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Download Python 3.10+ from: https://python.org/downloads
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo    Found Python %PYVER%

echo.
echo [2/4] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Could not create virtual environment.
    pause
    exit /b 1
)

echo.
echo [3/4] Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Dependency installation failed. Check requirements.txt.
    pause
    exit /b 1
)
echo    Dependencies installed successfully.

echo.
echo [4/4] Setting up environment file...
if not exist .env (
    copy .env.example .env >nul
    echo    Created .env from .env.example
    echo.
    echo    ACTION REQUIRED: Edit .env before starting the app:
    echo      - Set SECRET_KEY to a random 64-character string
    echo      - Set ADMIN_EMAIL and ADMIN_PASSWORD
    echo      - Set MPESA_* variables when ready to test payments
) else (
    echo    .env already exists -- skipping
)

echo.
echo ============================================
echo  Setup Complete!
echo ============================================
echo.
echo To start the development server:
echo.
echo    venv\Scripts\activate
echo    python run.py
echo.
echo Then open: http://localhost:5000
echo.
echo Default admin credentials (set in .env):
echo    Email:    admin@smartdrive.com
echo    Password: Admin@SecurePass1!
echo.
echo See README.md for full documentation.
echo.
pause
