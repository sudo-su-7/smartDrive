"""Application factory."""
from __future__ import annotations

import logging
import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config.settings import config_map

login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_map.get(config_name, config_map["default"]))

    # ── Logging ───────────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # ── Extensions ────────────────────────────────────────────────────────────
    csrf.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "basic"  # "strong" kills sessions on localhost IPv4/IPv6 switch

    # ── User loader ───────────────────────────────────────────────────────────
    from bson import ObjectId
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.database import get_db
        try:
            db = get_db()
            doc = db.users.find_one({"_id": ObjectId(user_id)})
            return User.from_db(doc)
        except Exception:
            return None

    # ── Database ──────────────────────────────────────────────────────────────
    from app.database import close_db, init_db
    app.teardown_appcontext(close_db)
    init_db(app)

    # ── Security headers ──────────────────────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        if app.config.get("FLASK_ENV") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ── Context processor ─────────────────────────────────────────────────────
    from flask_login import current_user

    @app.context_processor
    def inject_globals():
        unread = 0
        if current_user.is_authenticated:
            from app.database import get_db
            db = get_db()
            unread = db.notifications.count_documents(
                {"user_id": current_user.id, "read": False}
            )
        return {"unread_notifications": unread}

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.user import user_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    # ── Rate limit on auth routes ─────────────────────────────────────────────
    limiter.limit("10 per minute")(auth_bp)

    # ── Error handlers ────────────────────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("errors/500.html"), 500

    return app
