"""User-facing routes — dashboard, bookings, notifications."""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, abort
)
from flask_login import login_required, current_user

from app.database import get_db
from app.models.booking import make_booking_document
from app.models.vehicle import vehicle_is_available
from app.forms import BookingForm
from app.utils.helpers import Paginator, sanitize_string

user_bp = Blueprint("user", __name__, url_prefix="/dashboard")


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@user_bp.route("/")
@login_required
def dashboard():
    db = get_db()
    uid = current_user.id

    active_bookings = list(db.bookings.find(
        {"user_id": uid, "status": {"$in": ["pending", "approved"]}}
    ).sort("start_date", 1).limit(5))

    recent_bookings = list(db.bookings.find({"user_id": uid})
                           .sort("created_at", -1).limit(5))

    # Enrich with vehicle data
    for b in active_bookings + recent_bookings:
        v = db.vehicles.find_one({"_id": ObjectId(b["vehicle_id"])})
        b["vehicle"] = v

    total_bookings = db.bookings.count_documents({"user_id": uid})
    total_spent = db.bookings.aggregate([
        {"$match": {"user_id": uid, "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}},
    ])
    spent = next(total_spent, {}).get("total", 0)

    unread_notifications = db.notifications.count_documents(
        {"user_id": uid, "read": False}
    )

    return render_template(
        "user/dashboard.html",
        active_bookings=active_bookings,
        recent_bookings=recent_bookings,
        total_bookings=total_bookings,
        total_spent=spent,
        unread_notifications=unread_notifications,
        title="My Dashboard",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Booking history
# ─────────────────────────────────────────────────────────────────────────────

@user_bp.route("/bookings")
@login_required
def bookings():
    db = get_db()
    page = max(1, request.args.get("page", 1, type=int))
    status_filter = request.args.get("status", "")

    query: dict = {"user_id": current_user.id}
    if status_filter:
        query["status"] = status_filter

    total = db.bookings.count_documents(query)
    paginator = Paginator(total, page, 10)
    records = list(
        db.bookings.find(query)
        .sort("created_at", -1)
        .skip(paginator.skip)
        .limit(10)
    )

    for b in records:
        v = db.vehicles.find_one({"_id": ObjectId(b["vehicle_id"])})
        b["vehicle"] = v

    return render_template(
        "user/bookings.html",
        bookings=records,
        paginator=paginator,
        status_filter=status_filter,
        title="My Bookings",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Create booking
# ─────────────────────────────────────────────────────────────────────────────

@user_bp.route("/book/<vehicle_id>", methods=["GET", "POST"])
@login_required
def book_vehicle(vehicle_id):
    db = get_db()
    try:
        vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
    except Exception:
        vehicle = None
    if not vehicle or vehicle["status"] != "available":
        flash("This vehicle is not available for booking.", "warning")
        return redirect(url_for("main.vehicles"))

    form = BookingForm()
    if form.validate_on_submit():
        start = datetime.combine(form.start_date.data, datetime.min.time()).replace(tzinfo=timezone.utc)
        end = datetime.combine(form.end_date.data, datetime.min.time()).replace(tzinfo=timezone.utc)

        if not vehicle_is_available(db, vehicle_id, start, end):
            flash("This vehicle is already booked for the selected dates.", "danger")
            return redirect(url_for("user.book_vehicle", vehicle_id=vehicle_id))

        doc = make_booking_document(
            user_id=current_user.id,
            vehicle_id=vehicle_id,
            start_date=start,
            end_date=end,
            price_per_day=vehicle["price_per_day"],
            notes=sanitize_string(form.notes.data or ""),
        )
        result = db.bookings.insert_one(doc)

        # Create in-app notification
        db.notifications.insert_one({
            "user_id": current_user.id,
            "message": f"Booking request for {vehicle['name']} received. Pending admin review.",
            "link": url_for("user.booking_detail", booking_id=str(result.inserted_id)),
            "read": False,
            "created_at": datetime.now(timezone.utc),
        })

        flash("Booking request submitted! We'll notify you once reviewed.", "success")
        return redirect(url_for("user.booking_detail", booking_id=str(result.inserted_id)))

    return render_template(
        "user/book.html",
        vehicle=vehicle,
        form=form,
        title=f"Book {vehicle['name']}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Booking detail
# ─────────────────────────────────────────────────────────────────────────────

@user_bp.route("/bookings/<booking_id>")
@login_required
def booking_detail(booking_id):
    db = get_db()
    try:
        booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        booking = None

    if not booking or booking["user_id"] != current_user.id:
        abort(404)

    vehicle = db.vehicles.find_one({"_id": ObjectId(booking["vehicle_id"])})
    return render_template(
        "user/booking_detail.html",
        booking=booking,
        vehicle=vehicle,
        title="Booking Detail",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cancel booking
# ─────────────────────────────────────────────────────────────────────────────

@user_bp.route("/bookings/<booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    db = get_db()
    try:
        booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        booking = None

    if not booking or booking["user_id"] != current_user.id:
        abort(404)

    if booking["status"] not in ("pending",):
        flash("Only pending bookings can be cancelled.", "warning")
        return redirect(url_for("user.booking_detail", booking_id=booking_id))

    db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}}
    )
    flash("Booking cancelled.", "info")
    return redirect(url_for("user.bookings"))


# ─────────────────────────────────────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────────────────────────────────────

@user_bp.route("/notifications")
@login_required
def notifications():
    db = get_db()
    notes = list(
        db.notifications.find({"user_id": current_user.id})
        .sort("created_at", -1)
        .limit(50)
    )
    # Mark all as read
    db.notifications.update_many(
        {"user_id": current_user.id, "read": False},
        {"$set": {"read": True}}
    )
    return render_template("user/notifications.html", notifications=notes, title="Notifications")
