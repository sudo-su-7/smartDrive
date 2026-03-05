"""Email notification helpers."""
from __future__ import annotations
import logging
from flask import current_app, render_template_string
from flask_mail import Message

logger = logging.getLogger(__name__)

BOOKING_CREATED_SUBJECT = "Booking Request Received – SMART DRIVE"
BOOKING_APPROVED_SUBJECT = "Booking Approved – SMART DRIVE"
BOOKING_REJECTED_SUBJECT = "Booking Update – SMART DRIVE"

_BOOKING_CREATED_BODY = """
Hi {{ name }},

Your booking request for <strong>{{ vehicle }}</strong> has been received.<br>
<strong>Dates:</strong> {{ start }} to {{ end }}<br>
<strong>Total:</strong> KES {{ amount }}<br><br>

Our admin will review and confirm shortly.<br><br>
Thank you for choosing SMART DRIVE.
"""

_BOOKING_APPROVED_BODY = """
Hi {{ name }},<br><br>

Great news! Your booking for <strong>{{ vehicle }}</strong> has been <strong>approved</strong>.<br>
<strong>Dates:</strong> {{ start }} to {{ end }}<br>
<strong>Total:</strong> KES {{ amount }}<br><br>

Please complete payment to finalise your reservation.<br><br>
SMART DRIVE Team
"""

_BOOKING_REJECTED_BODY = """
Hi {{ name }},<br><br>

We're sorry — your booking request for <strong>{{ vehicle }}</strong>
from {{ start }} to {{ end }} could not be approved at this time.<br><br>

Please contact us or try different dates.<br><br>
SMART DRIVE Team
"""


def _send(mail, recipients: list[str], subject: str, html: str):
    try:
        msg = Message(subject=subject, recipients=recipients, html=html)
        mail.send(msg)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", recipients, exc)


def notify_booking_created(mail, user_name: str, email: str, vehicle: str,
                            start: str, end: str, amount: float):
    from jinja2 import Environment
    env = Environment()
    html = env.from_string(_BOOKING_CREATED_BODY).render(
        name=user_name, vehicle=vehicle, start=start, end=end, amount=amount
    )
    _send(mail, [email], BOOKING_CREATED_SUBJECT, html)


def notify_booking_approved(mail, user_name: str, email: str, vehicle: str,
                             start: str, end: str, amount: float):
    from jinja2 import Environment
    env = Environment()
    html = env.from_string(_BOOKING_APPROVED_BODY).render(
        name=user_name, vehicle=vehicle, start=start, end=end, amount=amount
    )
    _send(mail, [email], BOOKING_APPROVED_SUBJECT, html)


def notify_booking_rejected(mail, user_name: str, email: str, vehicle: str,
                              start: str, end: str):
    from jinja2 import Environment
    env = Environment()
    html = env.from_string(_BOOKING_REJECTED_BODY).render(
        name=user_name, vehicle=vehicle, start=start, end=end
    )
    _send(mail, [email], BOOKING_REJECTED_SUBJECT, html)
