"""SMS notifications via Africa's Talking (Kenyan SMS gateway)."""
from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)

AFRICASTALKING_USERNAME = os.getenv("AFRICASTALKING_USERNAME", "sandbox")
AFRICASTALKING_API_KEY  = os.getenv("AFRICASTALKING_API_KEY", "")
AFRICASTALKING_SENDER   = os.getenv("AFRICASTALKING_SENDER", "SmartDrive")
SANDBOX = os.getenv("AFRICASTALKING_ENV", "sandbox") == "sandbox"


def send_sms(phone_number: str, message: str) -> dict:
    """
    Send an SMS via Africa's Talking.
    Returns the API response dict, or {'error': reason} on failure.
    Phone number must include country code e.g. +254712345678
    """
    if not AFRICASTALKING_API_KEY:
        logger.warning("SMS not sent — AFRICASTALKING_API_KEY not set.")
        return {"error": "API key not configured"}

    try:
        import requests as req
        base = "sandbox" if SANDBOX else "api"
        url  = f"https://{base}.africastalking.com/version1/messaging"
        headers = {
            "ApiKey": AFRICASTALKING_API_KEY,
            "Accept": "application/json",
        }
        data = {
            "username": AFRICASTALKING_USERNAME,
            "to":       phone_number,
            "message":  message,
            "from":     AFRICASTALKING_SENDER,
        }
        resp = req.post(url, data=data, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("SMS send failed: %s", exc)
        return {"error": str(exc)}


# ── Convenience helpers ───────────────────────────────────────────────────────

def sms_booking_approved(phone: str, customer_name: str, vehicle_name: str) -> dict:
    msg = (
        f"Hello {customer_name}, your SmartDrive booking for {vehicle_name} "
        f"has been APPROVED. Proceed to payment to confirm your reservation. "
        f"SmartDrive - Drive Smart, Go Anywhere."
    )
    return send_sms(phone, msg)


def sms_booking_rejected(phone: str, customer_name: str, vehicle_name: str, reason: str = "") -> dict:
    msg = (
        f"Hello {customer_name}, your SmartDrive booking for {vehicle_name} "
        f"was not approved.{' Reason: ' + reason if reason else ''} "
        f"Contact us at info@smartdrive.co.ke for assistance."
    )
    return send_sms(phone, msg)


def sms_payment_confirmed(phone: str, customer_name: str, vehicle_name: str, amount: float) -> dict:
    msg = (
        f"Hello {customer_name}, payment of KES {amount:,.0f} confirmed for "
        f"{vehicle_name}. Your booking is active. Safe travels! - SmartDrive"
    )
    return send_sms(phone, msg)
