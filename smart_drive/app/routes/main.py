"""Public-facing routes — home, vehicle listing, vehicle detail."""
from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for
from app.database import get_db
from app.utils.helpers import Paginator

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    db = get_db()
    # Featured available vehicles (latest 6)
    vehicles = list(
        db.vehicles.find({"status": "available"})
        .sort("created_at", -1)
        .limit(6)
    )
    stats = {
        "total_vehicles": db.vehicles.count_documents({}),
        "available_vehicles": db.vehicles.count_documents({"status": "available"}),
        "total_bookings": db.bookings.count_documents({}),
    }
    return render_template("index.html", vehicles=vehicles, stats=stats, title="Home")


@main_bp.route("/vehicles")
def vehicles():
    db = get_db()
    page = max(1, request.args.get("page", 1, type=int))
    search = request.args.get("q", "").strip()
    fuel = request.args.get("fuel", "").strip()
    trans = request.args.get("transmission", "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    per_page = 9

    query: dict = {"status": "available"}

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"model": {"$regex": search, "$options": "i"}},
            {"plate_number": {"$regex": search, "$options": "i"}},
        ]
    if fuel:
        query["fuel_type"] = fuel
    if trans:
        query["transmission"] = trans
    if min_price is not None or max_price is not None:
        price_filter: dict = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        query["price_per_day"] = price_filter

    total = db.vehicles.count_documents(query)
    paginator = Paginator(total, page, per_page)
    vehicles_list = list(
        db.vehicles.find(query)
        .sort("price_per_day", 1)
        .skip(paginator.skip)
        .limit(per_page)
    )

    return render_template(
        "vehicles/listing.html",
        vehicles=vehicles_list,
        paginator=paginator,
        search=search,
        fuel=fuel,
        trans=trans,
        min_price=min_price,
        max_price=max_price,
        title="Available Vehicles",
    )


@main_bp.route("/vehicles/<vehicle_id>")
def vehicle_detail(vehicle_id):
    from bson import ObjectId
    db = get_db()
    try:
        vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
    except Exception:
        vehicle = None
    if not vehicle:
        return render_template("errors/404.html"), 404
    return render_template("vehicles/detail.html", vehicle=vehicle, title=vehicle["name"])
