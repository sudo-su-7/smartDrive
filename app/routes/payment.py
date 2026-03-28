"""
Payment blueprint — M-Pesa STK Push integration.

Routes:
  POST /payment/mpesa/initiate/<booking_id>   — trigger STK Push
  POST /payment/mpesa/callback                — Daraja webhook (no auth)
  GET  /payment/mpesa/status/<booking_id>     — poll payment status (JSON)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.database import get_db
from app.utils.mpesa import stk_push, query_stk_status
from app.utils.helpers import sanitize_string
from app.forms import MpesaPaymentForm

logger = logging.getLogger(__name__)
payment_bp = Blueprint("payment", __name__, url_prefix="/payment")


# ─────────────────────────────────────────────────────────────────────────────
# Initiate STK Push
# ─────────────────────────────────────────────────────────────────────────────

@payment_bp.route("/mpesa/<booking_id>", methods=["GET", "POST"])
@login_required
def mpesa_pay(booking_id: str):
    db = get_db()
    try:
        booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        booking = None

    if not booking or booking["user_id"] != current_user.id:
        abort(404)

    if booking.get("payment_status") == "paid":
        flash("This booking has already been paid for.", "info")
        return redirect(url_for("user.booking_detail", booking_id=booking_id))

    if booking["status"] not in ("approved",):
        flash("Payment is only available for approved bookings.", "warning")
        return redirect(url_for("user.booking_detail", booking_id=booking_id))

    vehicle = db.vehicles.find_one({"_id": ObjectId(booking["vehicle_id"])})
    form = MpesaPaymentForm()

    # Pre-fill phone from user profile
    if request.method == "GET" and current_user.phone:
        form.phone.data = current_user.phone

    if form.validate_on_submit():
        phone = form.phone.data.strip()
        amount = booking["total_amount"]

        response = stk_push(
            phone=phone,
            amount=amount,
            booking_id=booking_id,
            description=f"SmartDrive Booking",
        )

        if response.get("ResponseCode") == "0" or "CheckoutRequestID" in response:
            checkout_id = response.get("CheckoutRequestID", "")
            db.bookings.update_one(
                {"_id": ObjectId(booking_id)},
                {"$set": {
                    "payment_status": "pending_payment",
                    "mpesa_checkout_request_id": checkout_id,
                    "mpesa_phone": phone,
                    "updated_at": datetime.now(timezone.utc),
                }}
            )
            flash(
                f"M-Pesa payment request sent to {phone}. Enter your PIN on your phone to complete payment.",
                "success"
            )
            return redirect(url_for("payment.mpesa_status_page", booking_id=booking_id))
        else:
            error_msg = response.get("errorMessage") or response.get("error") or "Payment initiation failed."
            flash(f"Payment failed: {error_msg}", "danger")

    return render_template(
        "payment/mpesa.html",
        booking=booking,
        vehicle=vehicle,
        form=form,
        title="Pay with M-Pesa",
    )


@payment_bp.route("/mpesa/status/<booking_id>")
@login_required
def mpesa_status_page(booking_id: str):
    """Polling page that shows payment status."""
    db = get_db()
    try:
        booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        booking = None

    if not booking or booking["user_id"] != current_user.id:
        abort(404)

    vehicle = db.vehicles.find_one({"_id": ObjectId(booking["vehicle_id"])})
    return render_template(
        "payment/status.html",
        booking=booking,
        vehicle=vehicle,
        title="Payment Status",
    )


@payment_bp.route("/mpesa/poll/<booking_id>")
@login_required
def mpesa_poll(booking_id: str):
    """JSON endpoint polled by the frontend every few seconds."""
    db = get_db()
    try:
        booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        abort(404)

    if not booking or booking["user_id"] != current_user.id:
        abort(403)

    payment_status = booking.get("payment_status", "unpaid")

    # If still pending, query Daraja
    if payment_status == "pending_payment":
        checkout_id = booking.get("mpesa_checkout_request_id")
        if checkout_id and not checkout_id.startswith("ws_CO_SIMULATED"):
            resp = query_stk_status(checkout_id)
            result_code = str(resp.get("ResultCode", ""))
            if result_code == "0":
                # Successful
                _mark_paid(db, booking_id, checkout_id)
                payment_status = "paid"
            elif result_code in ("1032", "1", "17"):
                # Cancelled / failed
                db.bookings.update_one(
                    {"_id": ObjectId(booking_id)},
                    {"$set": {"payment_status": "unpaid", "updated_at": datetime.now(timezone.utc)}}
                )
                payment_status = "unpaid"

    return jsonify({"payment_status": payment_status, "booking_id": booking_id})


# ─────────────────────────────────────────────────────────────────────────────
# Daraja Callback (webhook — no auth, validated by transaction ID)
# ─────────────────────────────────────────────────────────────────────────────

@payment_bp.route("/mpesa/callback", methods=["POST"])
def mpesa_callback():
    """
    Receives STK push result from Safaricom Daraja.
    Must be publicly reachable via HTTPS.
    """
    data = request.get_json(silent=True) or {}
    logger.info("M-Pesa callback received: %s", data)

    try:
        body = data.get("Body", {})
        stk_callback = body.get("stkCallback", {})
        result_code = stk_callback.get("ResultCode")
        checkout_id = stk_callback.get("CheckoutRequestID")

        db = get_db()
        booking = db.bookings.find_one({"mpesa_checkout_request_id": checkout_id})
        if not booking:
            logger.warning("M-Pesa callback: no booking for CheckoutRequestID %s", checkout_id)
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

        if result_code == 0:
            # Extract transaction ID from metadata
            metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            txn_id = next(
                (item["Value"] for item in metadata if item.get("Name") == "MpesaReceiptNumber"),
                None
            )
            _mark_paid(db, str(booking["_id"]), checkout_id, txn_id)
        else:
            desc = stk_callback.get("ResultDesc", "Payment failed")
            logger.info("M-Pesa payment failed for booking %s: %s", booking["_id"], desc)
            db.bookings.update_one(
                {"_id": booking["_id"]},
                {"$set": {"payment_status": "unpaid", "updated_at": datetime.now(timezone.utc)}}
            )
    except Exception as exc:
        logger.error("M-Pesa callback processing error: %s", exc)

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mark_paid(db, booking_id: str, checkout_id: str, txn_id: str | None = None):
    now = datetime.now(timezone.utc)
    update = {
        "payment_status": "paid",
        "mpesa_transaction_id": txn_id or checkout_id,
        "paid_at": now,
        "updated_at": now,
    }
    db.bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": update})

    booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
    if booking:
        vehicle = db.vehicles.find_one({"_id": ObjectId(booking["vehicle_id"])})
        from flask import url_for
        db.notifications.insert_one({
            "user_id": booking["user_id"],
            "message": f"✅ Payment confirmed for {vehicle['name'] if vehicle else 'your booking'}. Amount: KES {booking['total_amount']:,.0f}",
            "link": url_for("user.booking_detail", booking_id=booking_id),
            "read": False,
            "created_at": now,
        })
    logger.info("Booking %s marked as paid. TxnID: %s", booking_id, txn_id)
