# 🚗 SMART DRIVE
### A Centralized Platform for Mobility Resource Allocation

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+ · Flask 3 · Flask-Login · Flask-WTF · Flask-Limiter · Flask-Mail |
| Frontend | HTML5 · CSS3 · Bootstrap 5.3 · Bootstrap Icons · Chart.js |
| Database | MongoDB (via PyMongo) |
| Security | bcrypt · CSRF tokens · rate limiting · input sanitisation (bleach) · security headers |

---

## Quick Start

### Prerequisites
- Python 3.10+ → https://python.org/downloads
- MongoDB Community → https://www.mongodb.com/try/download/community

---

### Windows (Recommended — use the installer script)

```bat
:: Double-click or run in PowerShell:
install_windows.bat
```

Then start the app:
```bat
venv\Scripts\activate
python run.py
```

### Manual install (Windows PowerShell)

```powershell
python -m venv venv
venv\Scripts\activate

# Upgrade pip first — important on Windows
python -m pip install --upgrade pip

# Install packages individually (avoids build issues)
pip install Flask Flask-Login Flask-WTF Flask-Limiter Flask-Mail
pip install pymongo bcrypt python-dotenv WTForms email-validator itsdangerous bleach
pip install Pillow --prefer-binary     # --prefer-binary avoids C compilation errors

copy .env.example .env   # then edit .env
python run.py
```

### Linux / macOS
```bash
chmod +x install_linux.sh && ./install_linux.sh
source venv/bin/activate && python run.py
```

---

> App starts at **http://localhost:5000**  
> DB indexes + admin account are created automatically on first run.

---

## Default Admin Credentials
Change immediately after first login.

```
Email:       
Password: Admin@SecurePass1!
```
(Both are set via `.env` — `ADMIN_EMAIL` and `ADMIN_PASSWORD`)

---

## Project Structure

```
smart_drive/
├── run.py                   # Entry point
├── requirements.txt
├── .env.example
├── config/
│   └── settings.py          # Config classes (Dev / Prod)
└── app/
    ├── __init__.py          # Application factory
    ├── database.py          # PyMongo connection + index bootstrap
    ├── forms.py             # Flask-WTF form definitions
    ├── models/
    │   ├── user.py          # User model (Flask-Login mixin)
    │   ├── vehicle.py       # Vehicle helpers
    │   └── booking.py       # Booking helpers
    ├── routes/
    │   ├── main.py          # Public pages (home, vehicle listing)
    │   ├── auth.py          # Register, login, logout, profile
    │   ├── user.py          # User dashboard, bookings
    │   └── admin.py         # Admin CRUD, reports, CSV export
    ├── utils/
    │   ├── helpers.py       # Decorators, sanitisation, file upload, paginator
    │   └── email.py         # Email notification helpers
    ├── static/
    │   ├── css/main.css
    │   ├── js/main.js
    │   └── uploads/vehicles/   # Uploaded vehicle images
    └── templates/
        ├── base.html
        ├── index.html
        ├── auth/            # login, register, profile, change_password
        ├── vehicles/        # listing, detail
        ├── user/            # dashboard, bookings, book, booking_detail, notifications
        ├── admin/           # dashboard, vehicles, vehicle_form, bookings, booking_detail, users, reports
        └── errors/          # 400, 403, 404, 429, 500
```

---

## Security Features

| Feature | Implementation |
|---|---|
| Password hashing | bcrypt with 12 rounds |
| CSRF protection | Flask-WTF on all POST forms |
| Rate limiting | Flask-Limiter (10/min on auth routes) |
| Session security | HttpOnly, SameSite=Lax, configurable Secure flag |
| Input sanitisation | bleach strips all HTML from text inputs |
| Role-based access | `@admin_required` decorator on all admin routes |
| Open redirect prevention | `next` param validated to start with `/` |
| Security headers | X-Content-Type-Options, X-Frame-Options, CSP-ready, HSTS in prod |
| Image validation | Extension check + Pillow decode + resize before save |
| Password strength | Min 8 chars, upper, lower, digit, special char — enforced server-side and shown client-side |
| Double-booking prevention | Overlap query before creating booking |

---

## Feature Checklist

### Users
- [x] Register / Login / Logout
- [x] Profile management
- [x] Password change (with current password verification)
- [x] Browse & filter vehicles
- [x] Book vehicles with date selection
- [x] Real-time total calculation (JS)
- [x] View booking history with status tabs
- [x] Cancel pending bookings
- [x] In-app notification centre

### Admin
- [x] Fleet management (add, edit, delete with image upload)
- [x] Booking approval / rejection with admin notes
- [x] User management (activate / suspend)
- [x] Admin dashboard with charts (Chart.js)
- [x] Reports & analytics (revenue, top vehicles, status distribution)
- [x] CSV export of all bookings

---

## Production Deployment

```bash
# Install gunicorn
pip install gunicorn

# Run
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

Set in `.env`:
```
FLASK_ENV=production
SESSION_COOKIE_SECURE=True
```

Use NGINX as reverse proxy with HTTPS (Let's Encrypt / Certbot).

---

## Future Enhancements (from SRS)

- M-Pesa payment integration
- Email verification on registration  
- GPS vehicle tracking
- Mobile app (React Native / Flutter)
- AI demand prediction
- Multi-branch fleet management
