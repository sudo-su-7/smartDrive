"""Authentication blueprint — register, login, logout, profile."""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, current_app
)
from flask_login import login_user, logout_user, login_required, current_user

from app.database import get_db
from app.models.user import User
from app.forms import RegistrationForm, LoginForm, ProfileForm, ChangePasswordForm
from app.utils.helpers import sanitize_string

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─────────────────────────────────────────────────────────────────────────────
# Register
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        db = get_db()
        email = form.email.data.lower().strip()

        if db.users.find_one({"email": email}):
            flash("That email is already registered. Please log in.", "warning")
            return redirect(url_for("auth.login"))

        doc = User.make_document(
            name=sanitize_string(form.name.data),
            email=email,
            password=form.password.data,
            phone=sanitize_string(form.phone.data or ""),
        )
        # Auto-verify for development; in production send a verification email
        doc["email_verified"] = True

        db.users.insert_one(doc)
        flash("Account created! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form, title="Create Account")


# ─────────────────────────────────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _redirect_after_login()

    form = LoginForm()
    if form.validate_on_submit():
        db = get_db()
        doc = db.users.find_one({"email": form.email.data.lower().strip()})
        user = User.from_db(doc)

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash("Your account has been suspended. Contact support.", "danger")
                return redirect(url_for("auth.login"))
            login_user(user, remember=form.remember.data)
            session.permanent = True
            flash(f"Welcome back, {user.name}!", "success")
            return _redirect_after_login()

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form, title="Sign In")


def _redirect_after_login():
    next_page = request.args.get("next")
    # Validate next URL to prevent open redirect
    if next_page and next_page.startswith("/") and not next_page.startswith("//"):
        return redirect(next_page)
    if current_user.is_admin():
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("user.dashboard"))


# ─────────────────────────────────────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))


# ─────────────────────────────────────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    form = ProfileForm(
        name=current_user.name,
        phone=current_user.phone,
    )
    if form.validate_on_submit():
        db.users.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": {
                "name": sanitize_string(form.name.data),
                "phone": sanitize_string(form.phone.data or ""),
                "updated_at": datetime.now(timezone.utc),
            }}
        )
        flash("Profile updated successfully.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", form=form, title="My Profile")


# ─────────────────────────────────────────────────────────────────────────────
# Change password
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    db = get_db()
    form = ChangePasswordForm()

    if form.validate_on_submit():
        doc = db.users.find_one({"_id": ObjectId(current_user.id)})
        user = User.from_db(doc)

        if not user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("auth.change_password"))

        new_hash = User.hash_password(form.new_password.data)
        db.users.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": {
                "password_hash": new_hash,
                "updated_at": datetime.now(timezone.utc),
            }}
        )
        flash("Password changed successfully. Please log in again.", "success")
        logout_user()
        session.clear()
        return redirect(url_for("auth.login"))

    return render_template("auth/change_password.html", form=form, title="Change Password")
