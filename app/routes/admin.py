"""Admin blueprint — vehicles, bookings, users, reports."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from bson import ObjectId
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, abort, Response, current_app
)
from flask_login import login_required, current_user

from app.database import get_db
from app.forms import VehicleForm, BookingActionForm
from app.models.vehicle import make_vehicle_document
from app.utils.helpers import admin_required, Paginator, sanitize_string, save_vehicle_image, delete_vehicle_image

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    db = get_db()

    stats = {
        "total_vehicles": db.vehicles.count_documents({}),
        "available_vehicles": db.vehicles.count_documents({"status": "available"}),
        "total_bookings": db.bookings.count_documents({}),
        "pending_bookings": db.bookings.count_documents({"status": "pending"}),
        "approved_bookings": db.bookings.count_documents({"status": "approved"}),
        "total_users": db.users.count_documents({"role": "user"}),
    }

    revenue = list(db.bookings.aggregate([
        {"$match": {"status": {"$in": ["approved", "completed"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}},
    ]))
    stats["total_revenue"] = revenue[0]["total"] if revenue else 0

    recent_bookings = list(
        db.bookings.find().sort("created_at", -1).limit(10)
    )
    for b in recent_bookings:
        b["user"] = db.users.find_one({"_id": ObjectId(b["user_id"])})
        b["vehicle"] = db.vehicles.find_one({"_id": ObjectId(b["vehicle_id"])})

    # Monthly booking trend (last 6 months)
    pipeline = [
        {"$group": {
            "_id": {"year": {"$year": "$created_at"}, "month": {"$month": "$created_at"}},
            "count": {"$sum": 1},
            "revenue": {"$sum": "$total_amount"},
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}},
        {"$limit": 6},
    ]
    monthly = list(db.bookings.aggregate(pipeline))

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_bookings=recent_bookings,
        monthly=monthly,
        pending_count=stats["pending_bookings"],
        title="Admin Dashboard",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Vehicle management
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/vehicles")
@login_required
@admin_required
def vehicles():
    db = get_db()
    page = max(1, request.args.get("page", 1, type=int))
    search = request.args.get("q", "").strip()

    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"model": {"$regex": search, "$options": "i"}},
            {"plate_number": {"$regex": search, "$options": "i"}},
        ]

    total = db.vehicles.count_documents(query)
    paginator = Paginator(total, page, 12)
    vehicles_list = list(
        db.vehicles.find(query)
        .sort("created_at", -1)
        .skip(paginator.skip)
        .limit(12)
    )

    pending_count = db.bookings.count_documents({"status": "pending"})
    return render_template(
        "admin/vehicles.html",
        vehicles=vehicles_list,
        paginator=paginator,
        search=search,
        pending_count=pending_count,
        title="Manage Vehicles",
    )


@admin_bp.route("/vehicles/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_vehicle():
    db = get_db()
    form = VehicleForm()

    if form.validate_on_submit():
        # Check plate uniqueness
        plate = form.plate_number.data.upper().strip()
        if db.vehicles.find_one({"plate_number": plate}):
            flash("A vehicle with that plate number already exists.", "danger")
            pending_count = db.bookings.count_documents({"status": "pending"})
            return render_template("admin/vehicle_form.html", form=form, title="Add Vehicle", mode="add", pending_count=pending_count)

        image_filename = ""
        if form.image.data:
            saved = save_vehicle_image(form.image.data)
            if saved:
                image_filename = saved
            else:
                flash("Image upload failed. Please use PNG/JPG under 5 MB.", "warning")

        doc = make_vehicle_document(
            name=sanitize_string(form.name.data),
            model=sanitize_string(form.model.data),
            plate_number=plate,
            price_per_day=float(form.price_per_day.data),
            capacity=form.capacity.data,
            fuel_type=form.fuel_type.data,
            transmission=form.transmission.data,
            description=sanitize_string(form.description.data or ""),
            image_filename=image_filename,
        )
        doc["status"] = form.status.data
        db.vehicles.insert_one(doc)
        flash("Vehicle added successfully.", "success")
        return redirect(url_for("admin.vehicles"))

    pending_count = db.bookings.count_documents({"status": "pending"})
    return render_template("admin/vehicle_form.html", form=form, title="Add Vehicle", mode="add", pending_count=pending_count)


@admin_bp.route("/vehicles/<vehicle_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_vehicle(vehicle_id):
    db = get_db()
    try:
        vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
    except Exception:
        vehicle = None
    if not vehicle:
        abort(404)

    form = VehicleForm(obj=None)

    if request.method == "GET":
        form.name.data = vehicle.get("name")
        form.model.data = vehicle.get("model")
        form.plate_number.data = vehicle.get("plate_number")
        form.price_per_day.data = vehicle.get("price_per_day")
        form.capacity.data = vehicle.get("capacity")
        form.fuel_type.data = vehicle.get("fuel_type")
        form.transmission.data = vehicle.get("transmission")
        form.status.data = vehicle.get("status")
        form.description.data = vehicle.get("description")

    if form.validate_on_submit():
        plate = form.plate_number.data.upper().strip()
        # Check plate uniqueness excluding current vehicle
        duplicate = db.vehicles.find_one({
            "plate_number": plate,
            "_id": {"$ne": ObjectId(vehicle_id)},
        })
        if duplicate:
            flash("Another vehicle already has that plate number.", "danger")
            pending_count2 = db.bookings.count_documents({"status": "pending"})
            return render_template("admin/vehicle_form.html", form=form, vehicle=vehicle, title="Edit Vehicle", mode="edit", pending_count=pending_count2)

        update: dict = {
            "name": sanitize_string(form.name.data),
            "model": sanitize_string(form.model.data),
            "plate_number": plate,
            "price_per_day": float(form.price_per_day.data),
            "capacity": form.capacity.data,
            "fuel_type": form.fuel_type.data,
            "transmission": form.transmission.data,
            "status": form.status.data,
            "description": sanitize_string(form.description.data or ""),
            "updated_at": datetime.now(timezone.utc),
        }

        if form.image.data:
            saved = save_vehicle_image(form.image.data)
            if saved:
                # Delete old image
                delete_vehicle_image(vehicle.get("image", ""))
                update["image"] = saved
            else:
                flash("Image upload failed. Old image kept.", "warning")

        db.vehicles.update_one({"_id": ObjectId(vehicle_id)}, {"$set": update})
        flash("Vehicle updated.", "success")
        return redirect(url_for("admin.vehicles"))

    pending_count = db.bookings.count_documents({"status": "pending"})
    return render_template(
        "admin/vehicle_form.html",
        form=form,
        vehicle=vehicle,
        title="Edit Vehicle",
        mode="edit",
        pending_count=pending_count,
    )


@admin_bp.route("/vehicles/<vehicle_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_vehicle(vehicle_id):
    db = get_db()
    try:
        vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
    except Exception:
        vehicle = None
    if not vehicle:
        abort(404)

    # Block deletion if active bookings exist
    active = db.bookings.count_documents({
        "vehicle_id": vehicle_id,
        "status": {"$in": ["pending", "approved"]},
    })
    if active:
        flash("Cannot delete a vehicle with active bookings.", "danger")
        return redirect(url_for("admin.vehicles"))

    delete_vehicle_image(vehicle.get("image", ""))
    db.vehicles.delete_one({"_id": ObjectId(vehicle_id)})
    flash("Vehicle deleted.", "info")
    return redirect(url_for("admin.vehicles"))


# ─────────────────────────────────────────────────────────────────────────────
# Booking management
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/bookings")
@login_required
@admin_required
def bookings():
    db = get_db()
    page = max(1, request.args.get("page", 1, type=int))
    status_filter = request.args.get("status", "")

    query = {}
    if status_filter:
        query["status"] = status_filter

    total = db.bookings.count_documents(query)
    paginator = Paginator(total, page, 15)
    records = list(
        db.bookings.find(query)
        .sort("created_at", -1)
        .skip(paginator.skip)
        .limit(15)
    )

    for b in records:
        b["user"] = db.users.find_one({"_id": ObjectId(b["user_id"])})
        b["vehicle"] = db.vehicles.find_one({"_id": ObjectId(b["vehicle_id"])})

    pending_count = db.bookings.count_documents({"status": "pending"})
    return render_template(
        "admin/bookings.html",
        bookings=records,
        paginator=paginator,
        status_filter=status_filter,
        pending_count=pending_count,
        title="Manage Bookings",
    )


@admin_bp.route("/bookings/<booking_id>", methods=["GET", "POST"])
@login_required
@admin_required
def booking_detail(booking_id):
    db = get_db()
    try:
        booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        booking = None
    if not booking:
        abort(404)

    user = db.users.find_one({"_id": ObjectId(booking["user_id"])})
    vehicle = db.vehicles.find_one({"_id": ObjectId(booking["vehicle_id"])})
    form = BookingActionForm()

    if form.validate_on_submit() and booking["status"] == "pending":
        action = form.action.data
        admin_notes = sanitize_string(form.admin_notes.data or "")
        db.bookings.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": {
                "status": action,
                "admin_notes": admin_notes,
                "reviewed_at": datetime.now(timezone.utc),
                "reviewed_by": current_user.id,
                "updated_at": datetime.now(timezone.utc),
            }}
        )

        # In-app notification for user
        msg = (
            f"Your booking for {vehicle['name']} has been {'approved ✅' if action == 'approved' else 'rejected ❌'}."
            f"{' ' + admin_notes if admin_notes else ''}"
        )
        db.notifications.insert_one({
            "user_id": booking["user_id"],
            "message": msg,
            "link": url_for("user.booking_detail", booking_id=booking_id),
            "read": False,
            "created_at": datetime.now(timezone.utc),
        })

        flash(f"Booking {action}.", "success")
        return redirect(url_for("admin.bookings"))

    pending_count = db.bookings.count_documents({"status": "pending"})
    return render_template(
        "admin/booking_detail.html",
        booking=booking,
        user=user,
        vehicle=vehicle,
        form=form,
        pending_count=pending_count,
        title="Booking Review",
    )


# ─────────────────────────────────────────────────────────────────────────────
# User management
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/users")
@login_required
@admin_required
def users():
    db = get_db()
    page = max(1, request.args.get("page", 1, type=int))
    search = request.args.get("q", "").strip()

    query: dict = {"role": "user"}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]

    total = db.users.count_documents(query)
    paginator = Paginator(total, page, 15)
    users_list = list(
        db.users.find(query, {"password_hash": 0})
        .sort("created_at", -1)
        .skip(paginator.skip)
        .limit(15)
    )

    for u in users_list:
        u["booking_count"] = db.bookings.count_documents({"user_id": str(u["_id"])})

    pending_count = db.bookings.count_documents({"status": "pending"})
    return render_template(
        "admin/users.html",
        users=users_list,
        paginator=paginator,
        search=search,
        pending_count=pending_count,
        title="Manage Users",
    )


@admin_bp.route("/users/<user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_user_active(user_id):
    db = get_db()
    try:
        user = db.users.find_one({"_id": ObjectId(user_id), "role": "user"})
    except Exception:
        user = None
    if not user:
        abort(404)

    new_state = not user.get("is_active", True)
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": new_state, "updated_at": datetime.now(timezone.utc)}}
    )
    status = "activated" if new_state else "suspended"
    flash(f"User account {status}.", "success")
    return redirect(url_for("admin.users"))



@admin_bp.route("/bookings/<booking_id>/complete", methods=["POST"])
@login_required
@admin_required
def complete_booking(booking_id):
    """Mark an approved booking as completed (vehicle returned)."""
    db = get_db()
    try:
        booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        booking = None
    if not booking:
        abort(404)

    if booking["status"] != "approved":
        flash("Only approved bookings can be marked as completed.", "warning")
        return redirect(url_for("admin.booking_detail", booking_id=booking_id))

    db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {
            "status": "completed",
            "payment_status": "paid",
            "completed_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }}
    )

    # Notify user
    vehicle = db.vehicles.find_one({"_id": ObjectId(booking["vehicle_id"])})
    db.notifications.insert_one({
        "user_id": booking["user_id"],
        "message": f"Your booking for {vehicle['name'] if vehicle else 'vehicle'} has been marked as completed. Thank you!",
        "link": url_for("user.booking_detail", booking_id=booking_id),
        "read": False,
        "created_at": datetime.now(timezone.utc),
    })

    flash("Booking marked as completed.", "success")
    return redirect(url_for("admin.booking_detail", booking_id=booking_id))


# ─────────────────────────────────────────────────────────────────────────────
# Reports & Export
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/reports")
@login_required
@admin_required
def reports():
    db = get_db()

    # Revenue by month
    revenue_pipeline = [
        {"$match": {"status": {"$in": ["approved", "completed"]}}},
        {"$group": {
            "_id": {"year": {"$year": "$created_at"}, "month": {"$month": "$created_at"}},
            "count": {"$sum": 1},
            "revenue": {"$sum": "$total_amount"},
        }},
        {"$sort": {"_id.year": -1, "_id.month": -1}},
        {"$limit": 12},
    ]
    monthly_revenue = list(db.bookings.aggregate(revenue_pipeline))

    # Top vehicles
    top_vehicles_pipeline = [
        {"$group": {"_id": "$vehicle_id", "count": {"$sum": 1}, "revenue": {"$sum": "$total_amount"}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    top_vehicles = list(db.bookings.aggregate(top_vehicles_pipeline))
    for tv in top_vehicles:
        v = db.vehicles.find_one({"_id": ObjectId(tv["_id"])})
        tv["vehicle"] = v

    # Status distribution
    status_dist = list(db.bookings.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]))

    pending_count = db.bookings.count_documents({"status": "pending"})
    return render_template(
        "admin/reports.html",
        monthly_revenue=monthly_revenue,
        top_vehicles=top_vehicles,
        status_dist=status_dist,
        pending_count=pending_count,
        title="Reports & Analytics",
    )


@admin_bp.route("/reports/export/bookings")
@login_required
@admin_required
def export_bookings_csv():
    db = get_db()
    bookings = list(db.bookings.find().sort("created_at", -1))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Booking ID", "User Email", "Vehicle", "Plate",
        "Start Date", "End Date", "Days", "Amount (KES)",
        "Status", "Payment Status", "Created At"
    ])

    for b in bookings:
        user = db.users.find_one({"_id": ObjectId(b["user_id"])})
        vehicle = db.vehicles.find_one({"_id": ObjectId(b["vehicle_id"])})
        writer.writerow([
            str(b["_id"]),
            user["email"] if user else "N/A",
            vehicle["name"] if vehicle else "N/A",
            vehicle["plate_number"] if vehicle else "N/A",
            b["start_date"].strftime("%Y-%m-%d") if b.get("start_date") else "",
            b["end_date"].strftime("%Y-%m-%d") if b.get("end_date") else "",
            b.get("days", ""),
            b.get("total_amount", ""),
            b.get("status", ""),
            b.get("payment_status", ""),
            b["created_at"].strftime("%Y-%m-%d %H:%M") if b.get("created_at") else "",
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=bookings_{datetime.now().strftime('%Y%m%d')}.csv"
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# CMS — Site content management
# ─────────────────────────────────────────────────────────────────────────────

def _get_cms(db) -> dict:
    """Return current CMS document, creating defaults if absent."""
    doc = db.cms.find_one({"_id": "site_content"})
    if doc:
        return doc
    defaults = {
        "_id": "site_content",
        "hero_badge":       "Kenya's #1 Vehicle Hire Platform",
        "hero_heading":     "Drive Smart,\nGo Anywhere.",
        "hero_subheading":  "Your journey starts with a tap. SmartDrive puts Kenya's most trusted vehicle fleet at your fingertips — built for business travel, school runs, upcountry trips, and every road in between.",
        "cta_heading":      "Every Journey Deserves a Great Vehicle",
        "cta_body":         "Stop settling for unreliable transport. Join thousands of Kenyans who book smarter, travel safer, and pay easier with SmartDrive.",
        "contact_email":    "info@smartdrive.co.ke",
        "contact_phone":    "+254 700 000 000",
        "contact_address":  "Westlands, Nairobi, Kenya",
        "contact_hours":    "Mon–Fri 8am–8pm EAT",
        "footer_tagline":   "Kenya's intelligent vehicle hire platform. Fast, secure, M-Pesa ready.",
        "updated_at":       None,
    }
    db.cms.insert_one(defaults)
    return defaults


@admin_bp.route("/cms", methods=["GET", "POST"])
@login_required
@admin_required
def cms():
    db = get_db()
    doc = _get_cms(db)
    error = None
    success_msg = None

    if request.method == "POST":
        allowed_fields = {
            "hero_badge", "hero_heading", "hero_subheading",
            "cta_heading", "cta_body",
            "contact_email", "contact_phone", "contact_address", "contact_hours",
            "footer_tagline",
        }
        updates: dict = {"updated_at": datetime.now(timezone.utc)}
        for field in allowed_fields:
            val = request.form.get(field, "").strip()
            updates[field] = sanitize_string(val, max_length=1000)

        db.cms.update_one(
            {"_id": "site_content"},
            {"$set": updates},
            upsert=True,
        )
        # Refresh doc
        doc = _get_cms(db)
        success_msg = "Site content updated successfully."
        flash(success_msg, "success")
        return redirect(url_for("admin.cms"))

    pending_count = db.bookings.count_documents({"status": "pending"})
    return render_template(
        "admin/cms.html",
        cms=doc,
        pending_count=pending_count,
        title="Site Content",
    )
