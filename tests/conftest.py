"""
Shared test fixtures and helpers for the SmartDrive test suite.
Uses stdlib unittest only — no external test framework required.
All MongoDB calls are mocked; no live database needed.
"""
from __future__ import annotations

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone


# ── Shared mock factories ─────────────────────────────────────────────────────

def make_user_doc(overrides: dict | None = None) -> dict:
    from bson import ObjectId
    doc = {
        "_id": ObjectId(),
        "name": "Test User",
        "email": "test@example.com",
        "password_hash": "$2b$12$placeholder_hash",
        "role": "user",
        "is_active": True,
        "email_verified": True,
        "phone": "+254700000000",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    if overrides:
        doc.update(overrides)
    return doc


def make_admin_doc(overrides: dict | None = None) -> dict:
    doc = make_user_doc({"name": "Admin User", "email": "admin@example.com", "role": "admin"})
    if overrides:
        doc.update(overrides)
    return doc


def make_vehicle_doc(overrides: dict | None = None) -> dict:
    from bson import ObjectId
    doc = {
        "_id": ObjectId(),
        "name": "Toyota Corolla",
        "model": "Toyota Corolla 2022",
        "plate_number": "KDA 001A",
        "price_per_day": 3500.0,
        "capacity": 5,
        "fuel_type": "petrol",
        "transmission": "automatic",
        "description": "Reliable sedan.",
        "image": "",
        "status": "available",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    if overrides:
        doc.update(overrides)
    return doc


def make_booking_doc(user_id=None, vehicle_id=None, overrides: dict | None = None) -> dict:
    from bson import ObjectId
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    doc = {
        "_id": ObjectId(),
        "user_id": str(user_id or ObjectId()),
        "vehicle_id": str(vehicle_id or ObjectId()),
        "start_date": now,
        "end_date": now + timedelta(days=3),
        "days": 3,
        "price_per_day": 3500.0,
        "total_amount": 10500.0,
        "notes": "",
        "status": "pending",
        "payment_status": "unpaid",
        "pickup_location": {"address": "Westlands, Nairobi", "lat": -1.2679, "lng": 36.8082},
        "dropoff_location": {},
        "mpesa_checkout_request_id": None,
        "mpesa_transaction_id": None,
        "mpesa_phone": None,
        "created_at": now,
        "updated_at": now,
    }
    if overrides:
        doc.update(overrides)
    return doc


def make_mock_db():
    """Return a MagicMock that mimics PyMongo db with all collections."""
    db = MagicMock()
    db.users       = MagicMock()
    db.vehicles    = MagicMock()
    db.bookings    = MagicMock()
    db.notifications = MagicMock()
    db.chat_rooms  = MagicMock()
    db.chat_messages = MagicMock()
    db.cms         = MagicMock()
    return db
