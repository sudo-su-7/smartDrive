"""Booking model helpers."""
from __future__ import annotations
from datetime import datetime, timezone


STATUSES = ("pending", "approved", "rejected", "cancelled", "completed")
PAYMENT_STATUSES = ("unpaid", "pending_payment", "paid", "refunded")


def make_booking_document(
    user_id: str,
    vehicle_id: str,
    start_date: datetime,
    end_date: datetime,
    price_per_day: float,
    notes: str = "",
    pickup_location: dict | None = None,
    dropoff_location: dict | None = None,
) -> dict:
    """
    Build a booking document for MongoDB insertion.

    pickup_location / dropoff_location shape:
        {"address": str, "lat": float, "lng": float}
    """
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
        # Geolocation
        "pickup_location": pickup_location or {},
        "dropoff_location": dropoff_location or {},
        # M-Pesa
        "mpesa_checkout_request_id": None,
        "mpesa_transaction_id": None,
        "mpesa_phone": None,
        "created_at": now,
        "updated_at": now,
    }
