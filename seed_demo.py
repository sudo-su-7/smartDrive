"""
seed_demo.py — Run once before your presentation to populate SmartDrive with
realistic Kenyan demo data.

Usage:
    python seed_demo.py

Requires: .env configured with MONGODB_URI (or defaults to localhost).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

# ── Bootstrap Flask app ───────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app
from app.database import get_db

import bcrypt
from bson import ObjectId

app = create_app()


VEHICLES = [
    {"name": "Toyota Hilux", "model": "Hilux Revo 2022", "plate_number": "KDA 001A",
     "price_per_day": 7500, "capacity": 5, "fuel_type": "diesel",
     "transmission": "manual", "status": "available",
     "description": "Rugged double-cab pickup, ideal for upcountry trips."},
    {"name": "Nissan X-Trail", "model": "X-Trail T32 2021", "plate_number": "KDB 002B",
     "price_per_day": 6000, "capacity": 7, "fuel_type": "petrol",
     "transmission": "automatic", "status": "available",
     "description": "Comfortable 7-seater SUV with panoramic sunroof."},
    {"name": "Toyota Land Cruiser", "model": "LC 200 2020", "plate_number": "KDC 003C",
     "price_per_day": 12000, "capacity": 8, "fuel_type": "diesel",
     "transmission": "automatic", "status": "available",
     "description": "Premium off-road SUV for executive transport."},
    {"name": "Isuzu D-Max", "model": "D-Max LS 2023", "plate_number": "KDD 004D",
     "price_per_day": 6500, "capacity": 5, "fuel_type": "diesel",
     "transmission": "automatic", "status": "available",
     "description": "Heavy-duty pickup for business and leisure."},
    {"name": "Toyota Noah", "model": "Noah 2022", "plate_number": "KDE 005E",
     "price_per_day": 5000, "capacity": 8, "fuel_type": "petrol",
     "transmission": "automatic", "status": "available",
     "description": "Spacious minivan, perfect for family or group travel."},
    {"name": "Ford Ranger", "model": "Ranger Wildtrak 2021", "plate_number": "KDF 006F",
     "price_per_day": 7000, "capacity": 5, "fuel_type": "diesel",
     "transmission": "automatic", "status": "available",
     "description": "Stylish pickup with advanced safety features."},
]

USERS = [
    {"name": "John Mwangi",   "email": "john.mwangi@demo.com",   "phone": "+254712000001"},
    {"name": "Jane Achieng",  "email": "jane.achieng@demo.com",  "phone": "+254712000002"},
    {"name": "Brian Otieno",  "email": "brian.otieno@demo.com",  "phone": "+254712000003"},
    {"name": "Amina Hassan",  "email": "amina.hassan@demo.com",  "phone": "+254712000004"},
    {"name": "Peter Kamau",   "email": "peter.kamau@demo.com",   "phone": "+254712000005"},
]

DEMO_PASSWORD_HASH = bcrypt.hashpw(b"Demo@1234", bcrypt.gensalt()).decode()
ADMIN_PASSWORD_HASH = bcrypt.hashpw(b"Admin@1234", bcrypt.gensalt()).decode()

BOOKING_STATUSES = [
    ("completed", "paid"),
    ("completed", "paid"),
    ("completed", "paid"),
    ("approved",  "paid"),
    ("approved",  "pending"),
    ("pending",   "pending"),
    ("pending",   "pending"),
    ("rejected",  "pending"),
    ("cancelled", "pending"),
    ("completed", "paid"),
    ("approved",  "paid"),
    ("pending",   "pending"),
]


def seed():
    with app.app_context():
        db = get_db()

        # ── Admin account ─────────────────────────────────────────────────────
        if not db.users.find_one({"email": "admin@smartdrive.co.ke"}):
            db.users.insert_one({
                "name": "Admin SmartDrive",
                "email": "admin@smartdrive.co.ke",
                "password_hash": ADMIN_PASSWORD_HASH,
                "role": "admin",
                "is_active": True,
                "phone": "+254700000000",
                "created_at": datetime.now(timezone.utc),
            })
            print("✅ Admin account created  →  admin@smartdrive.co.ke / Admin@1234")
        else:
            print("⏭  Admin account already exists")

        # ── Demo customer accounts ────────────────────────────────────────────
        user_ids = []
        for u in USERS:
            existing = db.users.find_one({"email": u["email"]})
            if existing:
                user_ids.append(str(existing["_id"]))
                continue
            result = db.users.insert_one({
                **u,
                "password_hash": DEMO_PASSWORD_HASH,
                "role": "user",
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
            })
            user_ids.append(str(result.inserted_id))
        print(f"✅ {len(USERS)} demo customer accounts ready  (password: Demo@1234)")

        # ── Vehicles ──────────────────────────────────────────────────────────
        vehicle_ids = []
        for v in VEHICLES:
            existing = db.vehicles.find_one({"plate_number": v["plate_number"]})
            if existing:
                vehicle_ids.append(str(existing["_id"]))
                continue
            result = db.vehicles.insert_one({
                **v,
                "image": "",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })
            vehicle_ids.append(str(result.inserted_id))
        print(f"✅ {len(VEHICLES)} vehicles seeded")

        # ── Bookings ──────────────────────────────────────────────────────────
        if db.bookings.count_documents({}) >= len(BOOKING_STATUSES):
            print("⏭  Bookings already seeded")
        else:
            import random
            random.seed(42)
            now = datetime.now(timezone.utc)
            inserted = 0
            for i, (status, pay_status) in enumerate(BOOKING_STATUSES):
                uid = user_ids[i % len(user_ids)]
                vid = vehicle_ids[i % len(vehicle_ids)]
                vehicle = db.vehicles.find_one({"_id": ObjectId(vid)})
                days  = random.randint(2, 7)
                start = now - timedelta(days=random.randint(5, 60))
                end   = start + timedelta(days=days)
                amount = vehicle["price_per_day"] * days if vehicle else 5000 * days
                db.bookings.insert_one({
                    "user_id": uid,
                    "vehicle_id": vid,
                    "start_date": start,
                    "end_date": end,
                    "days": days,
                    "pickup_location": "Westlands, Nairobi",
                    "total_amount": amount,
                    "status": status,
                    "payment_status": pay_status,
                    "admin_notes": "",
                    "created_at": start - timedelta(days=1),
                    "updated_at": now,
                })
                inserted += 1
            print(f"✅ {inserted} demo bookings created")

        print("\n🎉 Seeding complete!")
        print("   Admin login  →  admin@smartdrive.co.ke  /  Admin@1234")
        print("   Demo user    →  john.mwangi@demo.com    /  Demo@1234")


if __name__ == "__main__":
    seed()
