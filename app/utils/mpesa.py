"""
M-Pesa Daraja API integration — STK Push (Lipa Na M-Pesa Online).

Environment variables required:
    MPESA_CONSUMER_KEY
    MPESA_CONSUMER_SECRET
    MPESA_SHORTCODE           (your Paybill / Till number)
    MPESA_PASSKEY             (provided by Safaricom)
    MPESA_CALLBACK_URL        (publicly reachable HTTPS URL)
    MPESA_ENV                 (sandbox | production)
"""
from __future__ import annotations

import base64
import logging
import os
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

_SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
_PROD_BASE    = "https://api.safaricom.co.ke"


def _base_url() -> str:
    return _PROD_BASE if os.environ.get("MPESA_ENV", "sandbox") == "production" else _SANDBOX_BASE


def get_access_token() -> str | None:
    """Fetch OAuth token from Daraja."""
    key    = os.environ.get("MPESA_CONSUMER_KEY", "")
    secret = os.environ.get("MPESA_CONSUMER_SECRET", "")
    if not key or not secret:
        logger.warning("MPESA_CONSUMER_KEY / SECRET not set — using dummy token")
        return "dummy-token"

    url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    try:
        r = requests.get(url, auth=(key, secret), timeout=10)
        r.raise_for_status()
        return r.json().get("access_token")
    except Exception as exc:
        logger.error("M-Pesa token fetch failed: %s", exc)
        return None


def _password_and_timestamp() -> tuple[str, str]:
    shortcode = os.environ.get("MPESA_SHORTCODE", "174379")
    passkey   = os.environ.get("MPESA_PASSKEY",   "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919")
    ts        = datetime.now().strftime("%Y%m%d%H%M%S")
    raw       = f"{shortcode}{passkey}{ts}"
    password  = base64.b64encode(raw.encode()).decode()
    return password, ts


def stk_push(phone: str, amount: float, booking_id: str, description: str = "SmartDrive Booking") -> dict:
    """
    Initiate STK Push to phone. Returns Daraja response dict.

    phone   : Kenyan number  e.g. "0712345678" or "+254712345678"
    amount  : amount in KES (will be rounded to nearest int)
    booking_id: used as AccountReference
    """
    # Normalise phone to 254XXXXXXXXX
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if not phone.startswith("254"):
        phone = "254" + phone

    token = get_access_token()
    if not token or token == "dummy-token":
        # Return a sandbox-style simulated response so UI still works in dev
        return {
            "ResponseCode": "0",
            "ResponseDescription": "Success. Request accepted for processing (SANDBOX SIMULATION)",
            "MerchantRequestID": "sandbox-merchant-id",
            "CheckoutRequestID": f"ws_CO_SIMULATED_{booking_id}",
            "CustomerMessage": "Success. Request accepted for processing",
        }

    shortcode    = os.environ.get("MPESA_SHORTCODE", "174379")
    callback_url = os.environ.get("MPESA_CALLBACK_URL", "https://example.com/mpesa/callback")
    password, ts = _password_and_timestamp()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": ts,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(round(amount)),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": booking_id[:12],
        "TransactionDesc": description[:20],
    }

    url = f"{_base_url()}/mpesa/stkpush/v1/processrequest"
    try:
        r = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as exc:
        logger.error("STK push HTTP error %s: %s", exc.response.status_code, exc.response.text)
        return {"error": str(exc), "detail": exc.response.text}
    except Exception as exc:
        logger.error("STK push failed: %s", exc)
        return {"error": str(exc)}


def query_stk_status(checkout_request_id: str) -> dict:
    """Query the status of an STK push transaction."""
    token = get_access_token()
    if not token or token == "dummy-token":
        return {"ResultCode": "0", "ResultDesc": "The service request is processed successfully. (SIMULATION)"}

    shortcode    = os.environ.get("MPESA_SHORTCODE", "174379")
    password, ts = _password_and_timestamp()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": ts,
        "CheckoutRequestID": checkout_request_id,
    }

    url = f"{_base_url()}/mpesa/stkpushquery/v1/query"
    try:
        r = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.error("STK query failed: %s", exc)
        return {"error": str(exc)}
