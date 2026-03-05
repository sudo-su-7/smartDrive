"""Booking model helpers."""
from __future__ import annotations
from datetime import datetime, timezone


STATUSES = ("pending", "approved", "rejected", "cancelled", "completed")


def make_booking_document(
    user_id: str,
    vehicle_id: str,
    start_date: datetime,
    end_date: datetime,
    price_per_day: float,
    notes: str = "",
) -> dict:
    days = max((end_date - start_date).days, 1)
    total_amount = round(price_per_day * days, 2)
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "vehicle_id": vehicle_id,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "price_per_day": price_per_day,
        "total_amount": total_amount,
        "notes": notes.strip(),
        "status": "pending",
        "payment_status": "unpaid",
        "created_at": now,
        "updated_at": now,
    }
