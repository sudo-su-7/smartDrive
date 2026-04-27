"""Shared utility helpers — security, file handling, pagination."""
from __future__ import annotations

import os
import re
import uuid
import bleach
import logging
from functools import wraps
from flask import abort, flash, redirect, url_for, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Access control decorators
# ─────────────────────────────────────────────────────────────────────────────

def admin_required(f):
    """Restrict route to admin users only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated


def verified_required(f):
    """Restrict route to email-verified users."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.email_verified:
            flash("Please verify your email address to continue.", "warning")
            return redirect(url_for("user.dashboard"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────────────────────
# Input sanitisation
# ─────────────────────────────────────────────────────────────────────────────

def sanitize_string(value: str, max_length: int = 255) -> str:
    """Strip HTML tags and truncate."""
    cleaned = bleach.clean(value, tags=[], strip=True)
    return cleaned[:max_length]


PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,128}$"
)


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not PASSWORD_RE.match(password):
        return False, (
            "Password must contain uppercase, lowercase, a digit, "
            "and a special character."
        )
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# File upload helpers
# ─────────────────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config.get("ALLOWED_EXTENSIONS", {"png", "jpg", "jpeg", "webp"})


def save_vehicle_image(file_obj) -> str | None:
    """Validate, resize (if Pillow available), and save uploaded vehicle image. Returns filename or None."""
    if not file_obj or file_obj.filename == "":
        return None
    if not allowed_file(file_obj.filename):
        return None

    original_filename = secure_filename(file_obj.filename)
    ext = original_filename.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, unique_name)

    try:
        if PILLOW_AVAILABLE:
            img = Image.open(file_obj)
            img = img.convert("RGB")
            img.thumbnail((1200, 800), Image.LANCZOS)
            img.save(save_path, optimize=True, quality=85)
        else:
            file_obj.seek(0)
            file_obj.save(save_path)
        return unique_name
    except Exception as exc:
        logger.error("Image save failed: %s", exc)
        return None


def delete_vehicle_image(filename: str):
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as exc:
        logger.warning("Could not delete image %s: %s", filename, exc)


# ─────────────────────────────────────────────────────────────────────────────
# Pagination
# ─────────────────────────────────────────────────────────────────────────────

class Paginator:
    def __init__(self, total: int, page: int, per_page: int = 10):
        self.total = total
        self.page = max(1, page)
        self.per_page = per_page
        self.pages = max(1, (total + per_page - 1) // per_page)
        self.skip = (self.page - 1) * per_page
        self.has_prev = self.page > 1
        self.has_next = self.page < self.pages
        self.prev_num = self.page - 1
        self.next_num = self.page + 1

    def iter_pages(self, edge=2, middle=2):
        """Yield page numbers with None as ellipsis placeholder."""
        left = set(range(1, min(edge + 1, self.pages + 1)))
        right = set(range(max(1, self.pages - edge + 1), self.pages + 1))
        center = set(range(
            max(1, self.page - middle),
            min(self.pages + 1, self.page + middle + 1),
        ))
        pages = sorted(left | center | right)
        last = None
        for p in pages:
            if last and p - last > 1:
                yield None
            yield p
            last = p
