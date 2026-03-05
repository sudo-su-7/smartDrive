"""
Database layer — thin wrapper around PyMongo.
All collections are accessed through `get_db()`.
Indexes are created once at application startup via `init_db()`.
"""
from __future__ import annotations

from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import ConnectionFailure
from flask import current_app, g
import logging

logger = logging.getLogger(__name__)

_client: MongoClient | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Connection helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = current_app.config["MONGO_URI"]
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    """Return a per-request DB handle cached on Flask's `g`."""
    if "db" not in g:
        client = get_client()
        g.db = client[current_app.config["MONGO_DB_NAME"]]
    return g.db


def close_db(e=None):
    g.pop("db", None)


# ─────────────────────────────────────────────────────────────────────────────
# Index / collection bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def init_db(app):
    """Create indexes and seed admin. Called once from app factory."""
    with app.app_context():
        try:
            client = MongoClient(
                app.config["MONGO_URI"], serverSelectionTimeoutMS=5000
            )
            db = client[app.config["MONGO_DB_NAME"]]

            # ── users ─────────────────────────────────────────────────────────
            db.users.create_index([("email", ASCENDING)], unique=True)
            db.users.create_index([("role", ASCENDING)])
            db.users.create_index([("created_at", DESCENDING)])

            # ── vehicles ──────────────────────────────────────────────────────
            db.vehicles.create_index([("status", ASCENDING)])
            db.vehicles.create_index([("plate_number", ASCENDING)], unique=True)
            db.vehicles.create_index(
                [("name", TEXT), ("model", TEXT)], name="vehicle_text"
            )

            # ── bookings ──────────────────────────────────────────────────────
            db.bookings.create_index([("user_id", ASCENDING)])
            db.bookings.create_index([("vehicle_id", ASCENDING)])
            db.bookings.create_index([("status", ASCENDING)])
            db.bookings.create_index([("start_date", ASCENDING)])
            db.bookings.create_index([("end_date", ASCENDING)])

            # ── notifications ─────────────────────────────────────────────────
            db.notifications.create_index([("user_id", ASCENDING)])
            db.notifications.create_index([("read", ASCENDING)])

            logger.info("Database indexes ensured.")

            # ── Seed admin ────────────────────────────────────────────────────
            _seed_admin(db, app)

            client.close()
        except ConnectionFailure as exc:
            logger.error("Could not connect to MongoDB: %s", exc)
            raise


def _seed_admin(db, app):
    import bcrypt

    admin_email = app.config["ADMIN_EMAIL"]
    if db.users.find_one({"email": admin_email}):
        return  # already seeded

    pw = app.config["ADMIN_PASSWORD"].encode()
    pw_hash = bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12)).decode()

    from datetime import datetime, timezone

    db.users.insert_one(
        {
            "name": app.config["ADMIN_NAME"],
            "email": admin_email,
            "password_hash": pw_hash,
            "role": "admin",
            "is_active": True,
            "email_verified": True,
            "phone": "",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    logger.info("Admin user seeded: %s", admin_email)


def _seed_vehicles(db):
    """Seed 8 sample vehicles on first run so the fleet is not empty."""
    if db.vehicles.count_documents({}) > 0:
        return  # already seeded

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    sample_vehicles = [
        {
            "name": "Toyota Corolla",
            "model": "Toyota Corolla 2022",
            "plate_number": "KDA 001A",
            "price_per_day": 3500.00,
            "capacity": 5,
            "fuel_type": "petrol",
            "transmission": "automatic",
            "description": "Reliable and fuel-efficient sedan. Perfect for city and highway driving.",
            "image": "",
            "status": "available",
            "created_at": now,
            "updated_at": now,
        },
        {
            "name": "Toyota Land Cruiser",
            "model": "Toyota Land Cruiser V8 2021",
            "plate_number": "KDB 002B",
            "price_per_day": 12000.00,
            "capacity": 8,
            "fuel_type": "diesel",
            "transmission": "automatic",
            "description": "Powerful 4x4 SUV ideal for off-road adventures and safaris.",
            "image": "",
            "status": "available",
            "created_at": now,
            "updated_at": now,
        },
        {
            "name": "Nissan X-Trail",
            "model": "Nissan X-Trail 2023",
            "plate_number": "KDC 003C",
            "price_per_day": 5500.00,
            "capacity": 7,
            "fuel_type": "petrol",
            "transmission": "automatic",
            "description": "Spacious crossover SUV with advanced safety features.",
            "image": "",
            "status": "available",
            "created_at": now,
            "updated_at": now,
        },
        {
            "name": "Toyota Hiace",
            "model": "Toyota Hiace 2020",
            "plate_number": "KDD 004D",
            "price_per_day": 8000.00,
            "capacity": 14,
            "fuel_type": "diesel",
            "transmission": "manual",
            "description": "High-capacity van suitable for group travel and airport transfers.",
            "image": "",
            "status": "available",
            "created_at": now,
            "updated_at": now,
        },
        {
            "name": "Subaru Forester",
            "model": "Subaru Forester 2022",
            "plate_number": "KDE 005E",
            "price_per_day": 6000.00,
            "capacity": 5,
            "fuel_type": "petrol",
            "transmission": "automatic",
            "description": "All-wheel drive comfort SUV, great for upcountry travel.",
            "image": "",
            "status": "available",
            "created_at": now,
            "updated_at": now,
        },
        {
            "name": "Mercedes Benz C200",
            "model": "Mercedes Benz C200 2023",
            "plate_number": "KDF 006F",
            "price_per_day": 15000.00,
            "capacity": 5,
            "fuel_type": "petrol",
            "transmission": "automatic",
            "description": "Premium executive sedan for corporate travel and special occasions.",
            "image": "",
            "status": "available",
            "created_at": now,
            "updated_at": now,
        },
        {
            "name": "Toyota Probox",
            "model": "Toyota Probox 2019",
            "plate_number": "KDG 007G",
            "price_per_day": 2500.00,
            "capacity": 5,
            "fuel_type": "petrol",
            "transmission": "manual",
            "description": "Budget-friendly and economical for short errands and deliveries.",
            "image": "",
            "status": "available",
            "created_at": now,
            "updated_at": now,
        },
        {
            "name": "Mitsubishi Pajero",
            "model": "Mitsubishi Pajero 2021",
            "plate_number": "KDH 008H",
            "price_per_day": 10000.00,
            "capacity": 7,
            "fuel_type": "diesel",
            "transmission": "automatic",
            "description": "Robust off-road SUV perfect for game drives and rough terrain.",
            "image": "",
            "status": "available",
            "created_at": now,
            "updated_at": now,
        },
    ]

    db.vehicles.insert_many(sample_vehicles)
    logger.info("Seeded %d sample vehicles.", len(sample_vehicles))
