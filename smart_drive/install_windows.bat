@echo off
echo ============================================
echo  SMART DRIVE - Windows Setup Script
echo ============================================

echo.
echo [1/4] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo.
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [3/4] Upgrading pip and installing packages...
python -m pip install --upgrade pip
pip install Flask Flask-Login Flask-WTF Flask-Limiter Flask-Mail pymongo bcrypt python-dotenv WTForms email-validator itsdangerous bleach
pip install Pillow --prefer-binary

echo.
echo [4/4] Setting up environment file...
if not exist .env (
    copy .env.example .env
    echo Created .env from .env.example
    echo IMPORTANT: Edit .env and change SECRET_KEY before running in production!
) else (
    echo .env already exists, skipping.
)

echo.
echo ============================================
echo  Setup Complete!
echo ============================================
echo.
echo To start the app run:
echo   venv\Scripts\activate
echo   python run.py
echo.
echo Then open: http://localhost:5000
echo.
echo Default admin login:
echo   Email:    admin@smartdrive.com
echo   Password: Admin@SecurePass1!
echo.
pause
