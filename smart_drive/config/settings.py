import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Core ──────────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-key-replace-in-production"
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")

    # ── MongoDB ───────────────────────────────────────────────────────────────
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "smart_drive")

    # ── Session / Cookie security ─────────────────────────────────────────────
    # NOTE: SESSION_COOKIE_SECURE must be False on HTTP (localhost).
    # It is overridden to True only in ProductionConfig.
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(
        seconds=int(os.environ.get("PERMANENT_SESSION_LIFETIME", 1800))
    )

    # ── CSRF ──────────────────────────────────────────────────────────────────
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = int(os.environ.get("WTF_CSRF_TIME_LIMIT", 3600))

    # ── File uploads ──────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    # Use absolute path so it works regardless of working directory
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "static", "uploads", "vehicles")
    )
    ALLOWED_EXTENSIONS = set(
        os.environ.get("ALLOWED_EXTENSIONS", "png,jpg,jpeg,webp").split(",")
    )

    # ── Mail ──────────────────────────────────────────────────────────────────
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "SMART DRIVE <noreply@smartdrive.com>")

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per day;50 per hour")
    RATELIMIT_STORAGE_URL = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")

    # ── Admin seed ────────────────────────────────────────────────────────────
    ADMIN_NAME = os.environ.get("ADMIN_NAME", "Admin")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@smartdrive.com")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@SecurePass1!")


class DevelopmentConfig(Config):
    FLASK_DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    FLASK_DEBUG = False
    SESSION_COOKIE_SECURE = True


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
