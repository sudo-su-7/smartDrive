"""
Chat blueprint — real-time messaging between users and admin.
Uses Flask-SocketIO for WebSocket support, with a REST fallback.

Rooms are named: "booking_<booking_id>"  (booking-scoped chat)
             or: "support_<user_id>"     (general support)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson import ObjectId
from flask import (
    Blueprint, render_template, request, abort, jsonify
)
from flask_login import login_required, current_user

from app.database import get_db
from app.utils.helpers import sanitize_string

logger = logging.getLogger(__name__)
chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


# ─────────────────────────────────────────────────────────────────────────────
# REST helpers (used when SocketIO is not available / SSR fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_create_room(db, room_id: str, booking_id: str | None, user_id: str) -> dict:
    room = db.chat_rooms.find_one({"room_id": room_id})
    if not room:
        now = datetime.now(timezone.utc)
        doc = {
            "room_id": room_id,
            "booking_id": booking_id,
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
        }
        db.chat_rooms.insert_one(doc)
        room = doc
    return room


@chat_bp.route("/booking/<booking_id>")
@login_required
def booking_chat(booking_id: str):
    """Chat room scoped to a specific booking."""
    db = get_db()
    try:
        booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        booking = None

    if not booking:
        abort(404)

    # Only the booking's owner or an admin can access the chat
    if not current_user.is_admin() and booking["user_id"] != current_user.id:
        abort(403)

    room_id = f"booking_{booking_id}"
    _get_or_create_room(db, room_id, booking_id, booking["user_id"])

    messages = list(
        db.chat_messages.find({"room_id": room_id})
        .sort("created_at", 1)
        .limit(100)
    )

    vehicle = db.vehicles.find_one({"_id": ObjectId(booking["vehicle_id"])}) if booking else None

    return render_template(
        "chat/room.html",
        room_id=room_id,
        booking=booking,
        vehicle=vehicle,
        messages=messages,
        title="Booking Chat",
    )


@chat_bp.route("/support")
@login_required
def support_chat():
    """General support chat for a user."""
    db = get_db()
    room_id = f"support_{current_user.id}"
    _get_or_create_room(db, room_id, None, current_user.id)

    messages = list(
        db.chat_messages.find({"room_id": room_id})
        .sort("created_at", 1)
        .limit(100)
    )

    return render_template(
        "chat/room.html",
        room_id=room_id,
        booking=None,
        vehicle=None,
        messages=messages,
        title="Support Chat",
    )


# ─────────────────────────────────────────────────────────────────────────────
# REST API endpoints (used by the frontend fetch + SocketIO fallback)
# ─────────────────────────────────────────────────────────────────────────────

@chat_bp.route("/api/rooms/<room_id>/messages", methods=["GET"])
@login_required
def get_messages(room_id: str):
    db = get_db()
    _assert_room_access(db, room_id)
    after = request.args.get("after")  # ISO timestamp for polling
    query: dict = {"room_id": room_id}
    if after:
        try:
            after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
            query["created_at"] = {"$gt": after_dt}
        except ValueError:
            pass

    msgs = list(db.chat_messages.find(query).sort("created_at", 1).limit(50))
    return jsonify([_serialize_message(m) for m in msgs])


@chat_bp.route("/api/rooms/<room_id>/messages", methods=["POST"])
@login_required
def post_message(room_id: str):
    db = get_db()
    _assert_room_access(db, room_id)

    body = request.get_json(silent=True) or {}
    text = sanitize_string(body.get("message", "").strip(), max_length=1000)
    if not text:
        return jsonify({"error": "Empty message"}), 400

    now = datetime.now(timezone.utc)
    doc = {
        "room_id": room_id,
        "sender_id": current_user.id,
        "sender_name": current_user.name,
        "sender_role": current_user.role,
        "message": text,
        "created_at": now,
    }
    result = db.chat_messages.insert_one(doc)
    doc["_id"] = result.inserted_id

    # Update room's updated_at
    db.chat_rooms.update_one(
        {"room_id": room_id},
        {"$set": {"updated_at": now, "last_message": text[:80]}}
    )

    # Notify the other party (if they're not the sender)
    room = db.chat_rooms.find_one({"room_id": room_id})
    if room:
        target_user_id = room["user_id"]
        if current_user.is_admin():
            # Admin is replying → notify user
            _create_chat_notification(db, target_user_id, room_id, text, room.get("booking_id"))
        else:
            # User sent a message → notify all admins
            admins = db.users.find({"role": "admin"})
            for admin in admins:
                _create_chat_notification(db, str(admin["_id"]), room_id, text, room.get("booking_id"), sender_name=current_user.name)

    return jsonify(_serialize_message(doc)), 201


@chat_bp.route("/admin/chats")
@login_required
def admin_chat_list():
    """Admin view: all open chat rooms."""
    if not current_user.is_admin():
        abort(403)
    db = get_db()
    rooms = list(db.chat_rooms.find().sort("updated_at", -1).limit(50))
    for room in rooms:
        room["unread"] = db.chat_messages.count_documents({
            "room_id": room["room_id"],
            "sender_role": "user",
            "read_by_admin": {"$ne": True},
        })
        # Attach user info
        user = db.users.find_one({"_id": ObjectId(room["user_id"])}, {"password_hash": 0}) if room.get("user_id") else None
        room["user_doc"] = user

    pending_count = db.bookings.count_documents({"status": "pending"})
    return render_template(
        "chat/admin_list.html",
        rooms=rooms,
        pending_count=pending_count,
        title="Support Chats",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _assert_room_access(db, room_id: str):
    """Raise 403 if the current user has no right to this room."""
    if current_user.is_admin():
        return  # admins can access any room
    room = db.chat_rooms.find_one({"room_id": room_id})
    if not room:
        abort(404)
    if room["user_id"] != current_user.id:
        abort(403)


def _serialize_message(m: dict) -> dict:
    return {
        "id": str(m["_id"]),
        "room_id": m["room_id"],
        "sender_id": m.get("sender_id"),
        "sender_name": m.get("sender_name", "Unknown"),
        "sender_role": m.get("sender_role", "user"),
        "message": m.get("message", ""),
        "created_at": m["created_at"].isoformat() if m.get("created_at") else None,
    }


def _create_chat_notification(db, target_user_id: str, room_id: str, message_preview: str, booking_id: str | None, sender_name: str = "Support"):
    from flask import url_for
    if booking_id:
        link = url_for("chat.booking_chat", booking_id=booking_id)
    else:
        link = url_for("chat.support_chat")

    db.notifications.insert_one({
        "user_id": target_user_id,
        "message": f"💬 New message from {sender_name}: {message_preview[:60]}",
        "link": link,
        "read": False,
        "created_at": datetime.now(timezone.utc),
    })
