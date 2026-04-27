"""Vehicle model helpers."""
from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId


STATUSES = ("available", "booked", "maintenance")


def make_vehicle_document(
    name: str,
    model: str,
    plate_number: str,
    price_per_day: float,
    capacity: int,
    fuel_type: str,
    transmission: str,
    description: str,
    image_filename: str = "",
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "name": name.strip(),
        "model": model.strip(),
        "plate_number": plate_number.upper().strip(),
        "price_per_day": round(float(price_per_day), 2),
        "capacity": int(capacity),
        "fuel_type": fuel_type.strip(),
        "transmission": transmission.strip(),
        "description": description.strip(),
        "image": image_filename,
        "status": "available",
        "created_at": now,
        "updated_at": now,
    }


def vehicle_is_available(db, vehicle_id: str, start_date, end_date, exclude_booking_id=None) -> bool:
    """Return True if no overlapping confirmed/pending bookings exist."""
    query: dict = {
        "vehicle_id": vehicle_id,
        "status": {"$in": ["pending", "approved", "confirmed"]},
        "$or": [
            {"start_date": {"$lt": end_date}, "end_date": {"$gt": start_date}},
        ],
    }
    if exclude_booking_id:
        query["_id"] = {"$ne": ObjectId(exclude_booking_id)}
    return db.bookings.count_documents(query) == 0
