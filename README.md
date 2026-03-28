# SmartDrive — Technical Documentation

**Version:** 3.0.0  
**Stack:** Python 3.10+ · Flask 3 · MongoDB · Vanilla CSS · Leaflet.js · M-Pesa Daraja API  
**Last updated:** March 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Local Development Setup](#4-local-development-setup)
5. [Environment Variables Reference](#5-environment-variables-reference)
6. [Database Schema](#6-database-schema)
7. [Application Routes](#7-application-routes)
8. [Feature Guide](#8-feature-guide)
9. [M-Pesa Integration — Sandbox to Production](#9-m-pesa-integration--sandbox-to-production)
10. [Geolocation (Map Picker)](#10-geolocation-map-picker)
11. [Chat System](#11-chat-system)
12. [Email Notifications](#12-email-notifications)
13. [Security Model](#13-security-model)
14. [Production Deployment](#14-production-deployment)
15. [Nginx Configuration](#15-nginx-configuration)
16. [Systemd Service](#16-systemd-service)
17. [MongoDB in Production](#17-mongodb-in-production)
18. [Troubleshooting](#18-troubleshooting)
19. [Version History & Changelog](#19-version-history--changelog)

---

## 1. Project Overview

SmartDrive is a vehicle hire and fleet management platform built for the Kenyan market. It provides:

- **Public-facing** vehicle browsing, booking with map-based pickup/drop-off selection, and M-Pesa STK Push payment
- **User dashboard** for tracking bookings, payments, and live chat with support
- **Admin panel** for fleet management, booking approval/rejection, user management, revenue reports, and CSV export
- **Real-time chat** between customers and admin, scoped per booking or as general support

### Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask 3, Flask-Login, Flask-WTF, Flask-Limiter, Flask-Mail |
| Database | MongoDB 6+ via PyMongo 4 |
| Frontend | Vanilla CSS design system (no Bootstrap), Bootstrap Icons, Chart.js 4, Leaflet.js 1.9 |
| Payments | Safaricom Daraja API v1 — Lipa Na M-Pesa Online (STK Push) |
| Maps | OpenStreetMap tiles via Leaflet, Nominatim geocoding |
| Security | bcrypt (12 rounds), CSRF, rate limiting, bleach sanitisation, security headers |

---

## 2. Architecture

```
smart_drive/
├── run.py                        # Entry point — creates and runs the Flask app
├── requirements.txt
├── .env.example                  # Template — copy to .env and fill in
├── install_linux.sh              # One-command setup (Linux/macOS)
├── install_windows.bat           # One-command setup (Windows)
│
├── config/
│   └── settings.py               # DevelopmentConfig / ProductionConfig, loaded from .env
│
└── app/
    ├── __init__.py               # Application factory — registers blueprints, extensions, error handlers
    ├── database.py               # PyMongo connection, index bootstrap, admin + vehicle seeding
    ├── forms.py                  # All Flask-WTF form classes with server-side validation
    │
    ├── models/
    │   ├── user.py               # User class (Flask-Login UserMixin), password hashing
    │   ├── vehicle.py            # Vehicle document builder, availability checker
    │   └── booking.py            # Booking document builder (includes location + M-Pesa fields)
    │
    ├── routes/
    │   ├── main.py               # Public — home, vehicle listing, vehicle detail
    │   ├── auth.py               # Register, login, logout, profile, change password
    │   ├── user.py               # User dashboard, booking flow, cancel, notifications
    │   ├── admin.py              # Fleet CRUD, booking management, user management, reports, CSV
    │   ├── chat.py               # Chat rooms, REST message API, admin chat list
    │   └── payment.py            # M-Pesa STK Push, Daraja callback, polling endpoint
    │
    ├── utils/
    │   ├── helpers.py            # Decorators, sanitisation, file upload, Paginator
    │   ├── mpesa.py              # Daraja API client (token, STK push, status query)
    │   └── email.py              # Transactional email helpers (booking created/approved/rejected)
    │
    ├── static/
    │   ├── css/main.css          # Full design system — 60+ CSS tokens, light/dark mode
    │   ├── js/main.js            # Theme, sidebar, dropdowns, alerts, form helpers
    │   └── uploads/vehicles/     # User-uploaded vehicle images (auto-created)
    │
    └── templates/
        ├── base.html             # Public shell — topbar, mobile nav, flash, footer
        ├── index.html            # Homepage
        ├── admin/
        │   ├── base_admin.html   # Admin shell — sidebar + topbar app layout
        │   ├── dashboard.html    # Stats + Chart.js booking trend
        │   ├── vehicles.html     # Vehicle table with search
        │   ├── vehicle_form.html # Add / Edit vehicle form
        │   ├── bookings.html     # Booking table with status filters
        │   ├── booking_detail.html  # Review/approve/reject + location + chat link
        │   ├── users.html        # User table, suspend/activate
        │   └── reports.html      # Revenue chart, status doughnut, top vehicles
        ├── auth/                 # login, register, profile, change_password
        ├── chat/                 # room.html (user + admin), admin_list.html
        ├── errors/               # 400, 403, 404, 429, 500
        ├── payment/              # mpesa.html (pay form), status.html (polling page)
        ├── user/                 # dashboard, bookings, book (with map), booking_detail, notifications
        └── vehicles/             # listing, detail
```

### Request flow

```
Browser → Nginx (SSL termination) → Gunicorn (WSGI) → Flask app
                                                      ├── Blueprint routes
                                                      ├── MongoDB (PyMongo)
                                                      └── Daraja API (outbound HTTPS)

Safaricom servers → POST /payment/mpesa/callback → Flask (no auth, validates by CheckoutRequestID)
```

---

## 3. Prerequisites

### Required software

| Software | Minimum version | Download |
|---|---|---|
| Python | 3.10 | https://python.org/downloads |
| MongoDB Community | 6.0 | https://www.mongodb.com/try/download/community |
| Git | Any | https://git-scm.com |

### Optional (production)

| Software | Purpose |
|---|---|
| Nginx | Reverse proxy, SSL termination |
| Gunicorn | Production WSGI server |
| Certbot | Free SSL certificates (Let's Encrypt) |
| ngrok | Expose localhost for Daraja callback testing |

---

## 4. Local Development Setup

### Automatic (recommended)

**Linux / macOS:**
```bash
git clone <your-repo-url>
cd smart_drive
chmod +x install_linux.sh
./install_linux.sh
```

**Windows:**
```
Double-click install_windows.bat
```
or from PowerShell:
```powershell
.\install_windows.bat
```

Both scripts: create a virtual environment, install all dependencies, and copy `.env.example` → `.env`.

### Manual setup

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Open .env and fill in your values (see Section 5)

# 4. Start MongoDB (if not running as a service)
mongod --dbpath /data/db          # Linux/macOS
# Or start the MongoDB service on Windows

# 5. Run the development server
python run.py
```

The app will be available at **http://localhost:5000**

On first run, the application automatically:
- Creates all MongoDB indexes
- Seeds the admin account (credentials from `.env`)
- Seeds 8 sample vehicles so the fleet is not empty

### Default admin login
```
Email:    admin@smartdrive.com     (from ADMIN_EMAIL in .env)
Password: Admin@SecurePass1!       (from ADMIN_PASSWORD in .env)
```
> **Important:** Change the admin password immediately after first login in production.

---

## 5. Environment Variables Reference

Copy `.env.example` to `.env`. Never commit `.env` to version control.

```bash
cp .env.example .env
```

### Core Flask

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | `dev-key-…` | Flask secret for sessions/CSRF. Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | No | `development` | Set to `production` on live servers |
| `PORT` | No | `5000` | Port the dev server listens on |

### MongoDB

| Variable | Required | Default | Description |
|---|---|---|---|
| `MONGO_URI` | No | `mongodb://localhost:27017/` | Full MongoDB connection string. For MongoDB Atlas: `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `MONGO_DB_NAME` | No | `smart_drive` | Name of the database |

### Admin seed

| Variable | Required | Default | Description |
|---|---|---|---|
| `ADMIN_NAME` | No | `Admin` | Display name for the auto-created admin account |
| `ADMIN_EMAIL` | No | `admin@smartdrive.com` | Admin login email |
| `ADMIN_PASSWORD` | No | `Admin@SecurePass1!` | Admin login password — **change this** |

### Email (Flask-Mail)

| Variable | Required | Default | Description |
|---|---|---|---|
| `MAIL_SERVER` | No | `smtp.gmail.com` | SMTP server hostname |
| `MAIL_PORT` | No | `587` | SMTP port (587 = TLS, 465 = SSL) |
| `MAIL_USERNAME` | No | — | SMTP username / email address |
| `MAIL_PASSWORD` | No | — | SMTP password or app-specific password |
| `MAIL_DEFAULT_SENDER` | No | `SMART DRIVE <noreply@smartdrive.co.ke>` | From address in outgoing emails |

**Gmail setup:**
1. Enable 2-Factor Authentication on your Google account
2. Go to Google Account → Security → App Passwords
3. Generate a new app password for "Mail"
4. Use that 16-character password as `MAIL_PASSWORD`

### M-Pesa Daraja API

| Variable | Required | Default | Description |
|---|---|---|---|
| `MPESA_ENV` | No | `sandbox` | `sandbox` for testing, `production` for live payments |
| `MPESA_CONSUMER_KEY` | **Yes (live)** | — | From Daraja developer portal |
| `MPESA_CONSUMER_SECRET` | **Yes (live)** | — | From Daraja developer portal |
| `MPESA_SHORTCODE` | **Yes (live)** | `174379` | Your Paybill or Till number. `174379` is the sandbox test shortcode |
| `MPESA_PASSKEY` | **Yes (live)** | sandbox default | Provided by Safaricom when you create your app on Daraja |
| `MPESA_CALLBACK_URL` | **Yes (live)** | — | Public HTTPS URL where Safaricom will POST payment results. Must be reachable from the internet |

### Rate limiting

| Variable | Required | Default | Description |
|---|---|---|---|
| `RATELIMIT_DEFAULT` | No | `200 per day;50 per hour` | Global rate limit applied to all routes |
| `RATELIMIT_STORAGE_URL` | No | `memory://` | Use `redis://localhost:6379` in production for distributed deployments |

### File uploads

| Variable | Required | Default | Description |
|---|---|---|---|
| `MAX_CONTENT_LENGTH` | No | `5242880` | Max upload size in bytes (default = 5 MB) |
| `UPLOAD_FOLDER` | No | `app/static/uploads/vehicles` | Absolute path to vehicle image storage |

### Session

| Variable | Required | Default | Description |
|---|---|---|---|
| `PERMANENT_SESSION_LIFETIME` | No | `1800` | Session expiry in seconds (default = 30 minutes) |

---

## 6. Database Schema

SmartDrive uses MongoDB. All collections are created automatically. Indexes are bootstrapped on startup by `app/database.py`.

### `users`
```json
{
  "_id":              "ObjectId",
  "name":             "string",
  "email":            "string (unique, lowercase)",
  "password_hash":    "string (bcrypt)",
  "role":             "string (user | admin)",
  "is_active":        "boolean",
  "email_verified":   "boolean",
  "phone":            "string",
  "created_at":       "ISODate",
  "updated_at":       "ISODate"
}
```

**Indexes:** `email` (unique), `role`, `created_at` (desc)

### `vehicles`
```json
{
  "_id":           "ObjectId",
  "name":          "string",
  "model":         "string",
  "plate_number":  "string (unique, uppercase)",
  "price_per_day": "number (KES)",
  "capacity":      "integer",
  "fuel_type":     "string (petrol | diesel | electric | hybrid)",
  "transmission":  "string (automatic | manual)",
  "description":   "string",
  "image":         "string (filename in uploads/vehicles/)",
  "status":        "string (available | maintenance | booked)",
  "created_at":    "ISODate",
  "updated_at":    "ISODate"
}
```

**Indexes:** `status`, `plate_number` (unique), text index on `name + model`

### `bookings`
```json
{
  "_id":                        "ObjectId",
  "user_id":                    "string (user ObjectId as string)",
  "vehicle_id":                 "string (vehicle ObjectId as string)",
  "start_date":                 "ISODate",
  "end_date":                   "ISODate",
  "days":                       "integer",
  "price_per_day":              "number",
  "total_amount":               "number",
  "notes":                      "string",
  "status":                     "string (pending | approved | rejected | cancelled | completed)",
  "payment_status":             "string (unpaid | pending_payment | paid | refunded)",
  "pickup_location": {
    "address":  "string",
    "lat":      "number",
    "lng":      "number"
  },
  "dropoff_location": {
    "address":  "string",
    "lat":      "number",
    "lng":      "number"
  },
  "mpesa_checkout_request_id":  "string | null",
  "mpesa_transaction_id":       "string | null",
  "mpesa_phone":                "string | null",
  "admin_notes":                "string",
  "reviewed_at":                "ISODate",
  "reviewed_by":                "string (admin user_id)",
  "paid_at":                    "ISODate",
  "completed_at":               "ISODate",
  "created_at":                 "ISODate",
  "updated_at":                 "ISODate"
}
```

**Indexes:** `user_id`, `vehicle_id`, `status`, `start_date`, `end_date`, `mpesa_checkout_request_id` (sparse)

### `notifications`
```json
{
  "_id":        "ObjectId",
  "user_id":    "string",
  "message":    "string",
  "link":       "string (URL path)",
  "read":       "boolean",
  "created_at": "ISODate"
}
```

**Indexes:** `user_id`, `read`

### `chat_rooms`
```json
{
  "_id":         "ObjectId",
  "room_id":     "string (booking_<id> or support_<user_id>)",
  "booking_id":  "string | null",
  "user_id":     "string",
  "last_message":"string",
  "created_at":  "ISODate",
  "updated_at":  "ISODate"
}
```

**Indexes:** `room_id` (unique), `user_id`, `updated_at` (desc)

### `chat_messages`
```json
{
  "_id":          "ObjectId",
  "room_id":      "string",
  "sender_id":    "string",
  "sender_name":  "string",
  "sender_role":  "string (user | admin)",
  "message":      "string",
  "created_at":   "ISODate"
}
```

**Indexes:** `room_id`, `created_at`

---

## 7. Application Routes

### Public (`main_bp`, prefix: `/`)

| Method | Path | Description |
|---|---|---|
| GET | `/` | Homepage — featured vehicles and stats |
| GET | `/vehicles` | Vehicle listing with search and filters |
| GET | `/vehicles/<vehicle_id>` | Vehicle detail page |

### Auth (`auth_bp`, prefix: `/auth`)

| Method | Path | Description |
|---|---|---|
| GET/POST | `/auth/register` | Create account |
| GET/POST | `/auth/login` | Sign in |
| GET | `/auth/logout` | Sign out (login required) |
| GET/POST | `/auth/profile` | View/update profile (login required) |
| GET/POST | `/auth/change-password` | Change password (login required) |

### User (`user_bp`, prefix: `/dashboard`)

| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/` | User dashboard |
| GET | `/dashboard/bookings` | Booking history (paginated, filterable) |
| GET/POST | `/dashboard/book/<vehicle_id>` | Booking form with map picker |
| GET | `/dashboard/bookings/<booking_id>` | Booking detail with payment & chat links |
| POST | `/dashboard/bookings/<booking_id>/cancel` | Cancel a pending booking |
| GET | `/dashboard/notifications` | Notification centre (marks all read) |

### Admin (`admin_bp`, prefix: `/admin`)

| Method | Path | Description |
|---|---|---|
| GET | `/admin/` | Admin dashboard — stats + chart |
| GET | `/admin/vehicles` | Vehicle table with search |
| GET/POST | `/admin/vehicles/add` | Add vehicle form |
| GET/POST | `/admin/vehicles/<id>/edit` | Edit vehicle form |
| POST | `/admin/vehicles/<id>/delete` | Delete vehicle (blocked if active bookings) |
| GET | `/admin/bookings` | Booking table with status filter |
| GET/POST | `/admin/bookings/<id>` | Review booking (approve / reject) |
| POST | `/admin/bookings/<id>/complete` | Mark booking as completed |
| GET | `/admin/users` | User table with search |
| POST | `/admin/users/<id>/toggle-active` | Suspend / activate user |
| GET | `/admin/reports` | Revenue charts, top vehicles |
| GET | `/admin/reports/export/bookings` | Download all bookings as CSV |

### Chat (`chat_bp`, prefix: `/chat`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/chat/booking/<booking_id>` | Login + ownership | Booking-scoped chat room |
| GET | `/chat/support` | Login | General support chat |
| GET | `/chat/admin/chats` | Admin | List all chat rooms with unread counts |
| GET | `/chat/api/rooms/<room_id>/messages` | Login + ownership | Fetch messages (JSON, supports `?after=ISO_TIMESTAMP`) |
| POST | `/chat/api/rooms/<room_id>/messages` | Login + ownership | Post a message (JSON body: `{"message": "text"}`) |

### Payment (`payment_bp`, prefix: `/payment`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET/POST | `/payment/mpesa/<booking_id>` | Login + ownership | M-Pesa payment form — initiates STK Push |
| GET | `/payment/mpesa/status/<booking_id>` | Login + ownership | Payment status polling page |
| GET | `/payment/mpesa/poll/<booking_id>` | Login + ownership | JSON poll endpoint — returns `{"payment_status": "…"}` |
| POST | `/payment/mpesa/callback` | **None** (Safaricom webhook) | Daraja payment result receiver |

---

## 8. Feature Guide

### Booking lifecycle

```
User creates booking (status: pending, payment_status: unpaid)
        ↓
Admin reviews → Approves (status: approved) or Rejects (status: rejected)
        ↓ (if approved)
User pays via M-Pesa STK Push (payment_status: pending_payment → paid)
        ↓
Admin marks vehicle returned (status: completed)
```

A user can cancel their own booking only while it is in `pending` status.

### Availability check

Before creating a booking, `vehicle_is_available()` in `app/models/vehicle.py` queries for any overlapping bookings with status `pending` or `approved`. If an overlap exists, the booking is rejected and the user is shown an error.

### Image handling

Vehicle images are uploaded by admin, validated (extension + Pillow decode), resized to max 1200×800 px at 85% JPEG quality, and saved with a UUID filename. Old images are deleted when a vehicle image is replaced. The upload folder is served as static files by Flask in development; in production, Nginx should serve `app/static/uploads/` directly for performance.

---

## 9. M-Pesa Integration — Sandbox to Production

This is the most critical integration in the system. Read this section carefully before going live.

### How the payment flow works

```
1. User clicks "Pay with M-Pesa" on an approved booking
2. User enters their Safaricom phone number and submits
3. App calls Daraja → /mpesa/stkpush/v1/processrequest
4. Safaricom sends STK Push prompt to user's phone
5. User enters their M-Pesa PIN on the phone
6. Safaricom POSTs the result to your MPESA_CALLBACK_URL
7. App marks booking payment_status = "paid"
8. User's browser polls /payment/mpesa/poll/<booking_id> every 5 seconds
9. Polling endpoint detects payment_status = "paid" and redirects user to success
```

### Step 1 — Create a Daraja developer account

1. Go to https://developer.safaricom.co.ke
2. Click **Sign Up** and create an account
3. Verify your email address
4. Log in to the Daraja portal

### Step 2 — Create a sandbox app (for testing)

1. In the portal, click **My Apps** → **Add a New App**
2. Give it a name (e.g. `SmartDrive Dev`)
3. Select the **Lipa Na M-Pesa Sandbox** API
4. Click **Create App**
5. Copy your **Consumer Key** and **Consumer Secret** from the app credentials tab

Set in `.env`:
```bash
MPESA_ENV=sandbox
MPESA_CONSUMER_KEY=<your sandbox consumer key>
MPESA_CONSUMER_SECRET=<your sandbox consumer secret>
MPESA_SHORTCODE=174379
MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919
MPESA_CALLBACK_URL=https://<your-ngrok-or-server-url>/payment/mpesa/callback
```

The shortcode `174379` and the passkey shown above are Safaricom's **official sandbox test values**. Do not change them for sandbox testing.

### Step 3 — Expose your callback URL for sandbox testing

Safaricom's servers need to reach your `MPESA_CALLBACK_URL`. In development your machine is not publicly accessible, so you need a tunnel.

**Using ngrok (recommended for local testing):**

```bash
# Install ngrok: https://ngrok.com/download
# Start tunnel on port 5000
ngrok http 5000
```

ngrok will print a URL like `https://abc123.ngrok.io`. Use it:
```bash
MPESA_CALLBACK_URL=https://abc123.ngrok.io/payment/mpesa/callback
```

> **Important:** ngrok URLs change every time you restart ngrok (on the free plan). Update `.env` and restart the app whenever this happens. ngrok Pro gives you a fixed subdomain.

**Alternative — use a VPS even in development:**
Deploy the app to a VPS (see Section 14) and run it with `MPESA_ENV=sandbox`. This is more stable than ngrok for extended testing.

### Step 4 — Test in sandbox

Safaricom provides test Safaricom numbers for sandbox:

| Test phone | Description |
|---|---|
| `254708374149` | Always succeeds — use this to confirm the full payment flow works |
| `254711111111` | Always fails with "insufficient funds" |
| `254722000000` | Always times out (user doesn't respond) |

When you initiate a sandbox payment to `254708374149`, the STK Push is **simulated** — no real phone prompt appears. Safaricom automatically sends a success callback to your `MPESA_CALLBACK_URL` within a few seconds.

**Verify the callback is received:**
```bash
# In your app's terminal, look for log output like:
# INFO app.routes.payment: M-Pesa callback received: {...}
# INFO app.utils.mpesa: Booking <id> marked as paid. TxnID: <txn>
```

### Step 5 — Apply for a production Paybill or Till number

Before going live, you need a **real Safaricom Paybill or Till number**. This is a business-level account, not a personal M-Pesa account.

**Option A — Paybill (recommended for businesses)**
- Used when customers pay to a business number and enter an account number (your booking ID)
- Apply at: https://www.safaricom.co.ke/business/sme/paybill
- Requires: business registration certificate (Certificate of Incorporation or Business Name certificate), KRA PIN, director ID

**Option B — Buy Goods (Till Number)**
- Simpler to set up
- Customer pays and gets a confirmation immediately, no account reference
- Apply at your nearest Safaricom shop or via the M-Pesa Business portal

Processing time is typically **3–7 business days** after submitting complete documents.

### Step 6 — Create a production Daraja app

1. In the Daraja portal → **My Apps** → **Add a New App**
2. Select **Lipa Na M-Pesa Online** (production API, not sandbox)
3. Enter your live Paybill/Till number as the **Business Short Code**
4. Submit — Safaricom may require additional business verification
5. Once approved, copy the production **Consumer Key**, **Consumer Secret**, and **Passkey**

### Step 7 — Switch `.env` to production

```bash
MPESA_ENV=production
MPESA_CONSUMER_KEY=<production consumer key>
MPESA_CONSUMER_SECRET=<production consumer secret>
MPESA_SHORTCODE=<your real Paybill or Till number>
MPESA_PASSKEY=<production passkey from Daraja>
MPESA_CALLBACK_URL=https://yourdomain.co.ke/payment/mpesa/callback
```

> **Critical:** `MPESA_CALLBACK_URL` **must be HTTPS** in production. Safaricom will reject HTTP callback URLs. Ensure your SSL certificate is valid (see Section 15 for Nginx + Certbot setup).

### Step 8 — Verify the callback endpoint is reachable

Before going live, test that Safaricom can reach your callback:

```bash
# From any external server or your phone's internet:
curl -X POST https://yourdomain.co.ke/payment/mpesa/callback \
  -H "Content-Type: application/json" \
  -d '{"Body":{"stkCallback":{"ResultCode":0,"CheckoutRequestID":"test"}}}'

# Expected response: {"ResultCode": 0, "ResultDesc": "Accepted"}
```

The callback route has no authentication (Safaricom doesn't send auth headers). It's safe because it only looks up bookings by `CheckoutRequestID` — an attacker without a valid ID cannot manipulate any booking.

### M-Pesa configuration summary

| Setting | Sandbox | Production |
|---|---|---|
| `MPESA_ENV` | `sandbox` | `production` |
| API base URL | `https://sandbox.safaricom.co.ke` | `https://api.safaricom.co.ke` |
| Shortcode | `174379` | Your Paybill/Till number |
| Passkey | Sandbox default (in `.env.example`) | Your production passkey |
| Callback URL | ngrok HTTPS tunnel | Your domain HTTPS URL |
| Test phone | `254708374149` (always succeeds) | Real M-Pesa registered number |

### Handling payment failures in production

The polling endpoint at `/payment/mpesa/poll/<booking_id>` queries the Daraja status API every time the frontend polls. The status codes it handles:

| Daraja `ResultCode` | Meaning | App action |
|---|---|---|
| `0` | Success | Mark `payment_status = "paid"` |
| `1032` | Request cancelled by user | Reset to `unpaid`, show retry button |
| `1` | Insufficient funds | Reset to `unpaid`, show retry button |
| `17` | M-Pesa system internal error | Reset to `unpaid`, show retry button |

---

## 10. Geolocation (Map Picker)

The booking form uses **Leaflet.js** with **OpenStreetMap** tiles for the map and **Nominatim** for geocoding. No API key is required.

### How it works

1. Two Leaflet maps are rendered on the booking form — one for pickup, one for drop-off
2. The user can click on the map to place a marker, search by address (uses Nominatim), or press "My Location" which calls `navigator.geolocation.getCurrentPosition()`
3. When a marker is placed, the latitude and longitude are written into hidden form fields (`pickup_lat`, `pickup_lng`, etc.)
4. The address is reverse-geocoded from the coordinates and written into the address text field
5. On form submission, the coordinates and address are stored in the `bookings.pickup_location` and `bookings.dropoff_location` subdocuments

### Nominatim usage policy

OpenStreetMap's Nominatim service is used for address search and reverse geocoding. The code adds a 600ms debounce to search requests to avoid hammering the API. For production at scale (>1 request/second), you should:

1. Host your own Nominatim instance (https://nominatim.org/release-docs/develop/Installation/), or
2. Use a commercial geocoding API such as Google Maps Geocoding API or Mapbox and update the fetch calls in `user/book.html`

### Browser permission

The `Permissions-Policy` header is set to `geolocation=(self)` in `app/__init__.py`, which allows geolocation on the app's own origin. Users will be shown the browser's standard location permission dialog when they click "My Location".

---

## 11. Chat System

### Architecture

The chat system uses a **REST polling** approach rather than WebSockets. The frontend polls `/chat/api/rooms/<room_id>/messages?after=<timestamp>` every 3 seconds. This was chosen for simplicity and compatibility — it works without any additional infrastructure (no Redis, no Socket.IO server).

For a high-traffic deployment, you can replace the polling with WebSockets using Flask-SocketIO + eventlet (the dependency is already in `requirements.txt`).

### Room naming

| Room type | Room ID format | Who can access |
|---|---|---|
| Booking chat | `booking_<booking_ObjectId>` | Booking owner + any admin |
| Support chat | `support_<user_ObjectId>` | That user + any admin |

### Notifications

When a message is sent, the app creates a notification for the other party:
- If admin sends a message → notification created for the booking's user
- If user sends a message → notification created for all admin accounts

Notifications appear as a badge count in the topbar bell icon.

---

## 12. Email Notifications

Email is sent for three booking events using the helpers in `app/utils/email.py`:

| Event | Template | Triggered by |
|---|---|---|
| Booking created | `_BOOKING_CREATED_BODY` | `user.book_vehicle` route after `db.bookings.insert_one` |
| Booking approved | `_BOOKING_APPROVED_BODY` | `admin.booking_detail` route after approve action |
| Booking rejected | `_BOOKING_REJECTED_BODY` | `admin.booking_detail` route after reject action |

> **Note:** The email helper functions are defined and the templates are ready, but the actual `notify_*` calls are not wired into the routes by default (they require a configured SMTP server). To enable them, import `mail` from `app` and the `notify_*` functions from `app.utils.email` in `app/routes/admin.py` and `app/routes/user.py`, then call them after the relevant database operations.

### Testing email locally

Use Mailpit or Mailtrap to catch emails without a real SMTP server:

```bash
# Mailpit (https://mailpit.axllent.org)
# macOS: brew install mailpit && mailpit
# Linux: see mailpit docs

# Set in .env:
MAIL_SERVER=localhost
MAIL_PORT=1025
MAIL_USERNAME=
MAIL_PASSWORD=
```

---

## 13. Security Model

### Authentication and authorisation

- Sessions managed by Flask-Login with `session_protection = "basic"`
- Session cookie: `HttpOnly=True`, `SameSite=Lax`, `Secure=True` in production
- Session lifetime: 30 minutes (configurable via `PERMANENT_SESSION_LIFETIME`)
- Admin routes protected by `@admin_required` decorator (403 if not admin)
- Booking routes check `booking["user_id"] == current_user.id` before serving

### Password security

- Hashed with bcrypt at cost factor 12 (≈350ms per hash on commodity hardware)
- Server-side strength validation: min 8 chars, uppercase, lowercase, digit, special character
- Client-side strength bar provides visual feedback (does not replace server validation)

### CSRF protection

- Flask-WTF CSRF tokens on all POST forms (`{{ form.hidden_tag() }}`)
- Token validity: 1 hour (configurable via `WTF_CSRF_TIME_LIMIT`)
- API endpoints (chat, payment poll) are JSON-only and include `X-CSRFToken` header

### Input sanitisation

All user-supplied strings pass through `bleach.clean(value, tags=[], strip=True)` before storage. This strips all HTML tags. Additionally, WTForms validates field types, lengths, and formats.

### Rate limiting

- All routes: 200/day, 50/hour (configurable)
- Auth blueprint: additional 10/minute limit applied at registration
- Uses in-memory storage by default; use Redis in production for multi-process deployments

### Security headers

Set on every response in `app/__init__.py`:

| Header | Value |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `SAMEORIGIN` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(self), microphone=()` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (production only) |

### File upload security

1. Extension whitelist: `.png`, `.jpg`, `.jpeg`, `.webp`
2. Pillow `Image.open()` decode — rejects non-image files that have image extensions
3. UUID-based filename — prevents path traversal and filename collision
4. Resize to 1200×800 max — strips EXIF metadata and prevents zip-bomb images
5. 5 MB max upload size enforced by Flask (`MAX_CONTENT_LENGTH`)

### MongoDB injection prevention

PyMongo parameterises all queries by default when using dict-based query operators. String interpolation into queries is not used anywhere in the codebase. BSON `ObjectId()` conversion happens inside try/except blocks to handle malformed IDs gracefully.

---

## 14. Production Deployment

### Server requirements

| Component | Minimum | Recommended |
|---|---|---|
| RAM | 1 GB | 2 GB |
| CPU | 1 vCPU | 2 vCPU |
| Storage | 20 GB | 40 GB |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| Python | 3.10 | 3.12 |

### Install dependencies on the server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python, pip, Nginx, Certbot
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# Install MongoDB 6.0
curl -fsSL https://www.mongodb.org/static/pgp/server-6.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl start mongod && sudo systemctl enable mongod
```

### Deploy the application

```bash
# Create application user
sudo useradd -m -s /bin/bash smartdrive

# Clone repository
sudo -u smartdrive git clone <your-repo-url> /home/smartdrive/app
cd /home/smartdrive/app


# Create virtual environment and install dependencies
sudo -u smartdrive python3 -m venv venv
sudo -u smartdrive venv/bin/pip install --upgrade pip
sudo -u smartdrive venv/bin/pip install -r requirements.txt
sudo -u smartdrive venv/bin/pip install gunicorn

# Create and configure .env
sudo -u smartdrive cp .env.example .env
sudo -u smartdrive nano .env  # fill in all production values
```

### Set production `.env` values

```bash
SECRET_KEY=<64-character-random-hex>   # python3 -c "import secrets; print(secrets.token_hex(32))"
FLASK_ENV=production
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=smart_drive
ADMIN_EMAIL=<your-admin-email>
ADMIN_PASSWORD=<strong-password>
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=<your-email>
MAIL_PASSWORD=<app-password>
MPESA_ENV=production
MPESA_CONSUMER_KEY=<production-key>
MPESA_CONSUMER_SECRET=<production-secret>
MPESA_SHORTCODE=<your-paybill>
MPESA_PASSKEY=<production-passkey>
MPESA_CALLBACK_URL=https://yourdomain.co.ke/payment/mpesa/callback
RATELIMIT_STORAGE_URL=memory://
```

### Test the production setup manually before setting up Systemd

```bash
cd /home/smartdrive/app
source venv/bin/activate
gunicorn -w 2 -b 127.0.0.1:8000 run:app

# In another terminal, test it responds:
curl http://127.0.0.1:8000/
```

---

## 15. Nginx Configuration

### Install and configure Nginx

```bash
sudo nano /etc/nginx/sites-available/smartdrive
```

Paste the following (replace `yourdomain.co.ke` with your actual domain):

```nginx
server {
    listen 80;
    server_name yourdomain.co.ke www.yourdomain.co.ke;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.co.ke www.yourdomain.co.ke;

    # SSL — managed by Certbot (see below)
    ssl_certificate     /etc/letsencrypt/live/yourdomain.co.ke/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.co.ke/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 1d;
    add_header Strict-Transport-Security "max-age=63072000" always;

    # Client upload size (match MAX_CONTENT_LENGTH in .env)
    client_max_body_size 6M;

    # Serve static files directly (faster than going through Gunicorn)
    location /static/ {
        alias /home/smartdrive/app/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Proxy everything else to Gunicorn
    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_redirect     off;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }
}
```

Enable the site and obtain an SSL certificate:

```bash
sudo ln -s /etc/nginx/sites-available/smartdrive /etc/nginx/sites-enabled/
sudo nginx -t   # verify config is valid
sudo systemctl reload nginx

# Obtain SSL certificate (replace with your domain and email)
sudo certbot --nginx -d yourdomain.co.ke -d www.yourdomain.co.ke --email admin@yourdomain.co.ke --agree-tos --no-eff-email

# Certbot auto-renewal (runs twice daily via systemd timer — verify it's active)
sudo systemctl status certbot.timer
```

---

## 16. Systemd Service

Create a systemd service so the app starts automatically on boot and restarts on crash.

```bash
sudo nano /etc/systemd/system/smartdrive.service
```

Paste:

```ini
[Unit]
Description=SmartDrive Flask Application
After=network.target mongod.service
Requires=mongod.service

[Service]
User=smartdrive
Group=smartdrive
WorkingDirectory=/home/smartdrive/app
Environment="PATH=/home/smartdrive/app/venv/bin"
EnvironmentFile=/home/smartdrive/app/.env
ExecStart=/home/smartdrive/app/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --log-level info \
    --access-logfile /var/log/smartdrive/access.log \
    --error-logfile /var/log/smartdrive/error.log \
    run:app
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# Create log directory
sudo mkdir -p /var/log/smartdrive
sudo chown smartdrive:smartdrive /var/log/smartdrive

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable smartdrive
sudo systemctl start smartdrive

# Check status
sudo systemctl status smartdrive

# View logs
sudo journalctl -u smartdrive -f
```

### Gunicorn worker count

Set `--workers` to `(2 × CPU cores) + 1`. For a 2-vCPU server, use 5 workers. For a 1-vCPU server, 3 workers is appropriate.

---

## 17. MongoDB in Production

### Enable authentication

```bash
# Open mongosh
mongosh

# Create admin user
use admin
db.createUser({
  user: "smartdrive_admin",
  pwd: "StrongPassword123!",
  roles: [{ role: "dbOwner", db: "smart_drive" }]
})
exit

# Enable auth in /etc/mongod.conf
sudo nano /etc/mongod.conf
```

Add under `security:`:
```yaml
security:
  authorization: enabled
```

```bash
sudo systemctl restart mongod
```

Update `.env`:
```bash
MONGO_URI=mongodb://smartdrive_admin:StrongPassword123!@localhost:27017/smart_drive?authSource=smart_drive
```

### Backups

Set up daily backups with `mongodump`:

```bash
# Create backup script
sudo nano /etc/cron.daily/smartdrive-backup
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/smartdrive"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
mongodump --uri="mongodb://smartdrive_admin:PASSWORD@localhost:27017/smart_drive?authSource=smart_drive" \
  --out="$BACKUP_DIR/$DATE" \
  --gzip
# Keep only the last 7 days of backups
find "$BACKUP_DIR" -maxdepth 1 -mtime +7 -exec rm -rf {} +
```

```bash
sudo chmod +x /etc/cron.daily/smartdrive-backup
```

### MongoDB Atlas (alternative to self-hosted)

If you prefer a managed database, MongoDB Atlas free tier is sufficient for development and low-traffic production:

1. Create account at https://www.mongodb.com/atlas
2. Create a free M0 cluster
3. Add your server's IP to the IP access list
4. Create a database user
5. Copy the connection string and set as `MONGO_URI` in `.env`

---

## 18. Troubleshooting

### App won't start — "Address already in use"

```bash
# Find and kill process using port 5000 (development)
lsof -ti:5000 | xargs kill -9

# Or change the port in .env:
PORT=5001
```

### "CSRF token missing or invalid"

This occurs when the session cookie is not being sent. Common causes:
- `SESSION_COOKIE_SECURE=True` on an HTTP (non-HTTPS) connection — set it to `False` in development
- The CSRF token `{{ form.hidden_tag() }}` is missing from a form template
- The session has expired (`PERMANENT_SESSION_LIFETIME`) — the user needs to log in again

### M-Pesa callback not received

1. Confirm `MPESA_CALLBACK_URL` is reachable from the internet: `curl -X POST <your-callback-url>`
2. Confirm it returns HTTP 200 and `{"ResultCode": 0, "ResultDesc": "Accepted"}`
3. Check that the URL is HTTPS with a valid certificate (not self-signed)
4. Check app logs: `sudo journalctl -u smartdrive -f | grep mpesa`
5. In sandbox, use Safaricom's test phone `254708374149` — real phone numbers won't receive sandbox STK Pushes

### M-Pesa error "Invalid Access Token"

The Daraja access token expires every hour. The `get_access_token()` function in `mpesa.py` fetches a fresh token on every call. If you're getting this error:
- Confirm `MPESA_CONSUMER_KEY` and `MPESA_CONSUMER_SECRET` are correct
- Confirm `MPESA_ENV` matches the credentials (`sandbox` keys don't work with `production` and vice versa)
- Test token fetch manually: `curl -u <key>:<secret> https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials`

### Vehicle images not displaying

- Ensure the `UPLOAD_FOLDER` directory exists and is writable by the app user: `ls -la app/static/uploads/vehicles/`
- In production with Nginx, confirm the `location /static/` block points to the correct path
- Check file permissions: `sudo chown -R smartdrive:smartdrive /home/smartdrive/app/app/static/uploads/`

### Map not loading (blank/grey tiles)

- This is usually a network issue — the server can't reach OpenStreetMap tile servers
- Check firewall rules allow outbound HTTP/HTTPS
- Confirm browser console has no mixed-content errors (map loaded over HTTP on an HTTPS page)

### MongoDB connection refused

```bash
# Check if MongoDB is running
sudo systemctl status mongod

# Start if stopped
sudo systemctl start mongod

# Check MongoDB logs for errors
sudo cat /var/log/mongodb/mongod.log | tail -50
```

### Rate limit errors (429 Too Many Requests)

- If legitimate users are being rate limited, increase `RATELIMIT_DEFAULT` in `.env`
- The auth routes have a separate 10/minute limit to prevent brute force; this is intentional
- In production with multiple Gunicorn workers, use Redis for rate limit storage: `RATELIMIT_STORAGE_URL=redis://localhost:6379`

---

## 19. Version History & Changelog

### v3.0.0 (March 2026) — Current

**Frontend redesign (complete rebuild):**
- New design system — 60+ CSS custom properties, zero Bootstrap dependency
- Light/dark mode with `localStorage` persistence and system preference detection
- App shell architecture: sidebar + topbar for admin; topbar + mobile drawer for public
- Mobile-first responsive layout (320px → 1440px+)
- All 30 templates rewritten consistently

**New features (carried from v2.0.0):**
- M-Pesa Daraja STK Push payment integration
- Leaflet.js interactive map picker for pickup and drop-off locations
- Real-time chat system (REST polling) per booking and general support
- Admin support chat list with unread message counts

**Bug fixes (from v2.0.0):**
- `_seed_vehicles()` was defined but never called — fleet now auto-seeds on first run
- `Permissions-Policy: geolocation=()` header was blocking the map picker — changed to `geolocation=(self)`
- `complete_booking` was auto-marking `payment_status = "paid"` without actual payment verification
- `vehicle_is_available()` was checking for status `"confirmed"` which doesn't exist in the schema

### v2.0.0 (March 2026)

- Added M-Pesa STK Push, geolocation map picker, chat system
- Updated `booking.py` model to include location and M-Pesa fields
- Added MongoDB indexes for `chat_rooms`, `chat_messages`, and `mpesa_checkout_request_id`
- New blueprints: `chat_bp`, `payment_bp`

### v1.0.0 (February 2026) — Baseline

- Vehicle fleet management (CRUD with image upload)
- User registration, login, booking flow
- Admin dashboard with Chart.js analytics
- CSV export, in-app notifications
- Role-based access control, CSRF, rate limiting, bcrypt
