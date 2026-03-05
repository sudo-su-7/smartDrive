#!/bin/bash
echo "============================================"
echo " SMART DRIVE - Linux/macOS Setup Script"
echo "============================================"

echo ""
echo "[1/4] Creating virtual environment..."
python3 -m venv venv || { echo "ERROR: python3 not found"; exit 1; }

echo ""
echo "[2/4] Activating virtual environment..."
source venv/bin/activate

echo ""
echo "[3/4] Upgrading pip and installing packages..."
pip install --upgrade pip
pip install Flask Flask-Login Flask-WTF Flask-Limiter Flask-Mail \
    pymongo bcrypt python-dotenv WTForms email-validator itsdangerous bleach
pip install Pillow --prefer-binary

echo ""
echo "[4/4] Setting up environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
    echo "IMPORTANT: Edit .env and set SECRET_KEY before production use!"
else
    echo ".env already exists, skipping."
fi

echo ""
echo "============================================"
echo " Setup Complete!"
echo "============================================"
echo ""
echo "To start the app:"
echo "  source venv/bin/activate"
echo "  python run.py"
echo ""
echo "Then open: http://localhost:5000"
echo ""
echo "Default admin: admin@smartdrive.com / Admin@SecurePass1!"
