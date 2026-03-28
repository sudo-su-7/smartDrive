#!/bin/bash
set -e

echo "============================================"
echo " SmartDrive — Linux / macOS Setup"
echo "============================================"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED="3.10"
if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    echo "✅ Python $PYTHON_VERSION detected"
else
    echo "❌ Python 3.10+ required. Found: $PYTHON_VERSION"
    echo "   Download from: https://python.org/downloads"
    exit 1
fi

echo ""
echo "[1/4] Creating virtual environment..."
python3 -m venv venv

echo ""
echo "[2/4] Activating virtual environment and upgrading pip..."
source venv/bin/activate
pip install --upgrade pip --quiet

echo ""
echo "[3/4] Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"

echo ""
echo "[4/4] Setting up environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env from .env.example"
    echo ""
    echo "⚠️  ACTION REQUIRED: Edit .env before starting the app:"
    echo "   - Set SECRET_KEY to a random 64-character string"
    echo "   - Set ADMIN_EMAIL and ADMIN_PASSWORD"
    echo "   - Set MONGO_URI if using a remote MongoDB"
    echo "   - Set MPESA_* variables when ready to test payments"
else
    echo "   .env already exists — skipping"
fi

echo ""
echo "============================================"
echo " Setup Complete!"
echo "============================================"
echo ""
echo "To start the development server:"
echo ""
echo "   source venv/bin/activate"
echo "   python run.py"
echo ""
echo "Then open: http://localhost:5000"
echo ""
echo "Default admin credentials (set in .env):"
echo "   Email:    admin@smartdrive.com"
echo "   Password: Admin@SecurePass1!"
echo ""
echo "See README.md for full documentation including"
echo "M-Pesa setup, production deployment, and more."
echo ""
