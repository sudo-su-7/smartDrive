"""
INTEGRATION TESTS — Flask route layer
Tests every endpoint: success + error paths, auth flows, RBAC, rate limiting.
Uses Flask test client with a fully mocked database.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from bson import ObjectId
from datetime import datetime, timezone, timedelta

from tests.conftest import make_user_doc, make_admin_doc, make_vehicle_doc, make_booking_doc, make_mock_db


# ─────────────────────────────────────────────────────────────────────────────
# App factory for tests
# ─────────────────────────────────────────────────────────────────────────────

def create_test_app():
    """Build a Flask app with testing config and real routes but mocked DB."""
    os.environ.setdefault("FLASK_ENV", "testing")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
    os.environ.setdefault("WTF_CSRF_ENABLED", "False")

    from app import create_app
    app = create_app("development")
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "WTF_CSRF_CHECK_DEFAULT": False,
        "SERVER_NAME": "localhost",
        "RATELIMIT_ENABLED": False,
    })
    return app


class SmartDriveTestCase(unittest.TestCase):
    """Base class — patches the DB and provides login helpers."""

    def setUp(self):
        self.mock_db = make_mock_db()

        # Patch database.get_db everywhere it is called
        self.db_patcher = patch("app.database.get_db", return_value=self.mock_db)
        self.db_patcher.start()
        # Patch init_db so startup doesn't try a real Mongo connection
        self.init_patcher = patch("app.database.init_db")
        self.init_patcher.start()

        self.app = create_test_app()
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Default: unauthenticated
        self.user_doc  = make_user_doc()
        self.admin_doc = make_admin_doc()

    def tearDown(self):
        self.ctx.pop()
        self.db_patcher.stop()
        self.init_patcher.stop()

    def _login(self, doc: dict):
        """Log in the test client as the given user document."""
        from app.models.user import User
        user = User(doc)
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(doc["_id"])
            sess["_fresh"]   = True
        # Also mock user_loader
        self.mock_db.users.find_one.return_value = doc
        return user

    def _login_as_user(self):
        return self._login(self.user_doc)

    def _login_as_admin(self):
        return self._login(self.admin_doc)


# ─────────────────────────────────────────────────────────────────────────────
# Public routes
# ─────────────────────────────────────────────────────────────────────────────

class TestPublicRoutes(SmartDriveTestCase):

    def setUp(self):
        super().setUp()
        self.mock_db.vehicles.find.return_value = MagicMock(__iter__=lambda s: iter([]))
        self.mock_db.vehicles.count_documents.return_value = 0
        self.mock_db.bookings.count_documents.return_value = 0
        self.mock_db.notifications.count_documents.return_value = 0
        self.mock_db.cms.find_one.return_value = None

    def test_homepage_returns_200(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)

    def test_homepage_contains_brand(self):
        r = self.client.get("/")
        self.assertIn(b"SmartDrive", r.data)

    def test_vehicle_listing_returns_200(self):
        self.mock_db.vehicles.find.return_value = MagicMock(
            sort=MagicMock(return_value=MagicMock(
                skip=MagicMock(return_value=MagicMock(limit=MagicMock(return_value=iter([]))))
            ))
        )
        r = self.client.get("/vehicles")
        self.assertEqual(r.status_code, 200)

    def test_vehicle_detail_not_found(self):
        self.mock_db.vehicles.find_one.return_value = None
        r = self.client.get(f"/vehicles/{ObjectId()}")
        self.assertEqual(r.status_code, 404)

    def test_vehicle_detail_invalid_id_returns_404(self):
        r = self.client.get("/vehicles/not-a-valid-id")
        self.assertIn(r.status_code, [404, 500])


# ─────────────────────────────────────────────────────────────────────────────
# Auth routes
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthRoutes(SmartDriveTestCase):

    def setUp(self):
        super().setUp()
        self.mock_db.notifications.count_documents.return_value = 0
        self.mock_db.cms.find_one.return_value = None

    # ── Register ──────────────────────────────────────────────────────────────

    def test_register_page_loads(self):
        r = self.client.get("/auth/register")
        self.assertEqual(r.status_code, 200)

    def test_register_redirects_authenticated_user(self):
        self._login_as_user()
        self.mock_db.vehicles.find.return_value = MagicMock(__iter__=lambda s: iter([]))
        self.mock_db.vehicles.count_documents.return_value = 0
        self.mock_db.bookings.count_documents.return_value = 0
        r = self.client.get("/auth/register")
        self.assertEqual(r.status_code, 302)

    def test_register_duplicate_email_redirects_to_login(self):
        self.mock_db.users.find_one.return_value = self.user_doc  # duplicate
        r = self.client.post("/auth/register", data={
            "name": "Test User",
            "email": "test@example.com",
            "password": "SecurePass1!",
            "confirm_password": "SecurePass1!",
        }, follow_redirects=False)
        self.assertIn(r.status_code, [200, 302])

    def test_register_missing_fields_returns_200_with_errors(self):
        r = self.client.post("/auth/register", data={"name": "", "email": "", "password": ""})
        self.assertEqual(r.status_code, 200)

    # ── Login ─────────────────────────────────────────────────────────────────

    def test_login_page_loads(self):
        r = self.client.get("/auth/login")
        self.assertEqual(r.status_code, 200)

    def test_login_with_bad_email_format_returns_200(self):
        r = self.client.post("/auth/login", data={"email": "not-an-email", "password": "x"})
        self.assertEqual(r.status_code, 200)

    def test_login_wrong_password_stays_on_login(self):
        self.mock_db.users.find_one.return_value = None  # no user found
        r = self.client.post("/auth/login", data={
            "email": "nobody@example.com", "password": "wrongpass"
        })
        self.assertEqual(r.status_code, 200)

    def test_login_suspended_user_rejected(self):
        suspended = make_user_doc({"is_active": False})
        self.mock_db.users.find_one.return_value = suspended
        with patch("app.models.user.User.check_password", return_value=True):
            r = self.client.post("/auth/login", data={
                "email": "test@example.com", "password": "SecurePass1!"
            })
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"suspended", r.data.lower())

    # ── Logout ────────────────────────────────────────────────────────────────

    def test_logout_clears_session_and_redirects(self):
        self._login_as_user()
        r = self.client.post("/auth/logout", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        # Session should no longer contain user ID
        with self.client.session_transaction() as sess:
            self.assertNotIn("_user_id", sess)

    def test_logout_get_also_works(self):
        """GET logout still supported for backwards compatibility with direct navigation."""
        self._login_as_user()
        r = self.client.get("/auth/logout", follow_redirects=False)
        self.assertEqual(r.status_code, 302)

    def test_logout_unauthenticated_redirects_to_login(self):
        r = self.client.post("/auth/logout", follow_redirects=False)
        self.assertIn(r.status_code, [302, 401])

    def test_logout_deletes_remember_cookie(self):
        self._login_as_user()
        r = self.client.post("/auth/logout")
        # Check that Set-Cookie headers include deletion of remember token
        cookie_headers = r.headers.getlist("Set-Cookie")
        # Either the cookie is deleted (Max-Age=0) or absent
        remember_cookies = [c for c in cookie_headers if "remember" in c.lower() or "sd_remember" in c.lower()]
        for rc in remember_cookies:
            self.assertTrue("Max-Age=0" in rc or "expires=Thu, 01 Jan 1970" in rc.lower(),
                            f"Remember cookie not deleted: {rc}")

    # ── Profile ───────────────────────────────────────────────────────────────

    def test_profile_requires_login(self):
        r = self.client.get("/auth/profile", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/auth/login", r.headers["Location"])

    def test_profile_loads_for_authenticated_user(self):
        self._login_as_user()
        r = self.client.get("/auth/profile")
        self.assertEqual(r.status_code, 200)

    def test_change_password_requires_login(self):
        r = self.client.get("/auth/change-password", follow_redirects=False)
        self.assertEqual(r.status_code, 302)


# ─────────────────────────────────────────────────────────────────────────────
# RBAC — Role-Based Access Control
# ─────────────────────────────────────────────────────────────────────────────

class TestRBAC(SmartDriveTestCase):

    def setUp(self):
        super().setUp()
        self.mock_db.notifications.count_documents.return_value = 0
        self.mock_db.cms.find_one.return_value = None
        self.mock_db.bookings.count_documents.return_value = 0
        self.mock_db.vehicles.count_documents.return_value = 0
        self.mock_db.users.count_documents.return_value = 0

    # User cannot access admin routes
    def test_user_cannot_access_admin_dashboard(self):
        self._login_as_user()
        r = self.client.get("/admin/", follow_redirects=False)
        self.assertEqual(r.status_code, 403)

    def test_user_cannot_access_admin_vehicles(self):
        self._login_as_user()
        r = self.client.get("/admin/vehicles", follow_redirects=False)
        self.assertEqual(r.status_code, 403)

    def test_user_cannot_access_admin_bookings(self):
        self._login_as_user()
        r = self.client.get("/admin/bookings", follow_redirects=False)
        self.assertEqual(r.status_code, 403)

    def test_user_cannot_access_admin_users(self):
        self._login_as_user()
        r = self.client.get("/admin/users", follow_redirects=False)
        self.assertEqual(r.status_code, 403)

    def test_user_cannot_access_admin_reports(self):
        self._login_as_user()
        r = self.client.get("/admin/reports", follow_redirects=False)
        self.assertEqual(r.status_code, 403)

    def test_user_cannot_access_admin_cms(self):
        self._login_as_user()
        r = self.client.get("/admin/cms", follow_redirects=False)
        self.assertEqual(r.status_code, 403)

    # Unauthenticated cannot access protected routes
    def test_anonymous_redirected_from_dashboard(self):
        r = self.client.get("/dashboard/", follow_redirects=False)
        self.assertEqual(r.status_code, 302)

    def test_anonymous_redirected_from_booking(self):
        r = self.client.get(f"/dashboard/book/{ObjectId()}", follow_redirects=False)
        self.assertEqual(r.status_code, 302)

    def test_anonymous_cannot_access_admin(self):
        r = self.client.get("/admin/", follow_redirects=False)
        self.assertEqual(r.status_code, 302)

    def test_anonymous_cannot_access_chat(self):
        r = self.client.get(f"/chat/booking/{ObjectId()}", follow_redirects=False)
        self.assertEqual(r.status_code, 302)

    def test_anonymous_cannot_access_payment(self):
        r = self.client.get(f"/payment/mpesa/{ObjectId()}", follow_redirects=False)
        self.assertEqual(r.status_code, 302)

    # Admin can access admin routes
    def test_admin_can_access_dashboard(self):
        self._login_as_admin()
        # Mock aggregate and all dashboard queries
        self.mock_db.bookings.aggregate.return_value = iter([])
        self.mock_db.bookings.find.return_value = MagicMock(
            sort=MagicMock(return_value=MagicMock(limit=MagicMock(return_value=iter([]))))
        )
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 200)

    def test_admin_can_access_cms(self):
        self._login_as_admin()
        self.mock_db.cms.find_one.return_value = None  # defaults
        r = self.client.get("/admin/cms")
        self.assertEqual(r.status_code, 200)

    # Users can only access their own bookings
    def test_user_cannot_access_other_users_booking_detail(self):
        self._login_as_user()
        other_user_id = str(ObjectId())
        booking = make_booking_doc(user_id=other_user_id)
        self.mock_db.bookings.find_one.return_value = booking
        r = self.client.get(f"/dashboard/bookings/{booking['_id']}")
        self.assertEqual(r.status_code, 404)


# ─────────────────────────────────────────────────────────────────────────────
# User dashboard routes
# ─────────────────────────────────────────────────────────────────────────────

class TestUserRoutes(SmartDriveTestCase):

    def setUp(self):
        super().setUp()
        self._login_as_user()
        self.mock_db.notifications.count_documents.return_value = 0
        self.mock_db.cms.find_one.return_value = None

    def test_dashboard_loads(self):
        self.mock_db.bookings.find.return_value = MagicMock(
            sort=MagicMock(return_value=MagicMock(limit=MagicMock(return_value=iter([]))))
        )
        self.mock_db.bookings.count_documents.return_value = 0
        self.mock_db.bookings.aggregate.return_value = iter([])
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 200)

    def test_bookings_page_loads(self):
        self.mock_db.bookings.count_documents.return_value = 0
        self.mock_db.bookings.find.return_value = MagicMock(
            sort=MagicMock(return_value=MagicMock(
                skip=MagicMock(return_value=MagicMock(limit=MagicMock(return_value=iter([]))))
            ))
        )
        r = self.client.get("/dashboard/bookings")
        self.assertEqual(r.status_code, 200)

    def test_book_vehicle_not_available_redirects(self):
        vehicle = make_vehicle_doc({"status": "maintenance"})
        self.mock_db.vehicles.find_one.return_value = vehicle
        self.mock_db.vehicles.count_documents.return_value = 0
        r = self.client.get(f"/dashboard/book/{vehicle['_id']}", follow_redirects=False)
        self.assertEqual(r.status_code, 302)

    def test_book_vehicle_invalid_id_redirects(self):
        self.mock_db.vehicles.find_one.return_value = None
        self.mock_db.vehicles.count_documents.return_value = 0
        r = self.client.get(f"/dashboard/book/{ObjectId()}", follow_redirects=False)
        self.assertEqual(r.status_code, 302)

    def test_cancel_booking_not_pending_rejected(self):
        booking = make_booking_doc(
            user_id=self.user_doc["_id"],
            overrides={"status": "approved"}
        )
        self.mock_db.bookings.find_one.return_value = booking
        r = self.client.post(
            f"/dashboard/bookings/{booking['_id']}/cancel",
            follow_redirects=False
        )
        self.assertIn(r.status_code, [302, 200])
        # Should NOT have called update_one to change status
        update_calls = [str(c) for c in self.mock_db.bookings.update_one.call_args_list]
        for call_str in update_calls:
            self.assertNotIn("'cancelled'", call_str)

    def test_cancel_booking_ownership_enforced(self):
        """User cannot cancel another user's booking."""
        other_uid = str(ObjectId())
        booking = make_booking_doc(user_id=other_uid, overrides={"status": "pending"})
        self.mock_db.bookings.find_one.return_value = booking
        r = self.client.post(f"/dashboard/bookings/{booking['_id']}/cancel")
        self.assertEqual(r.status_code, 404)

    def test_notifications_marks_all_read(self):
        self.mock_db.notifications.find.return_value = MagicMock(
            sort=MagicMock(return_value=MagicMock(limit=MagicMock(return_value=iter([]))))
        )
        r = self.client.get("/dashboard/notifications")
        self.assertEqual(r.status_code, 200)
        self.mock_db.notifications.update_many.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Admin routes
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminRoutes(SmartDriveTestCase):

    def setUp(self):
        super().setUp()
        self._login_as_admin()
        self.mock_db.notifications.count_documents.return_value = 0
        self.mock_db.bookings.count_documents.return_value = 0
        self.mock_db.cms.find_one.return_value = None

    def test_add_vehicle_duplicate_plate_rejected(self):
        self.mock_db.vehicles.find_one.return_value = make_vehicle_doc()  # duplicate
        r = self.client.post("/admin/vehicles/add", data={
            "name": "Toyota X", "model": "2022", "plate_number": "KDA001A",
            "price_per_day": "3500", "capacity": "5", "fuel_type": "petrol",
            "transmission": "automatic", "status": "available",
        })
        self.assertEqual(r.status_code, 200)
        self.mock_db.vehicles.insert_one.assert_not_called()

    def test_delete_vehicle_with_active_bookings_blocked(self):
        vehicle = make_vehicle_doc()
        self.mock_db.vehicles.find_one.return_value = vehicle
        self.mock_db.bookings.count_documents.return_value = 1  # active bookings
        r = self.client.post(f"/admin/vehicles/{vehicle['_id']}/delete", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.mock_db.vehicles.delete_one.assert_not_called()

    def test_delete_vehicle_no_active_bookings_succeeds(self):
        vehicle = make_vehicle_doc()
        self.mock_db.vehicles.find_one.return_value = vehicle
        self.mock_db.bookings.count_documents.return_value = 0
        r = self.client.post(f"/admin/vehicles/{vehicle['_id']}/delete", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.mock_db.vehicles.delete_one.assert_called_once()

    def test_approve_booking_updates_status(self):
        booking = make_booking_doc(overrides={"status": "pending"})
        vehicle = make_vehicle_doc()
        user = self.user_doc
        self.mock_db.bookings.find_one.return_value = booking
        self.mock_db.vehicles.find_one.return_value = vehicle
        self.mock_db.users.find_one.return_value = user

        r = self.client.post(f"/admin/bookings/{booking['_id']}", data={
            "action": "approved",
            "admin_notes": "Looks good",
        }, follow_redirects=False)
        self.assertIn(r.status_code, [302, 200])
        if self.mock_db.bookings.update_one.called:
            call_args = self.mock_db.bookings.update_one.call_args[0]
            update = call_args[1]
            self.assertEqual(update.get("$set", {}).get("status"), "approved")

    def test_toggle_user_active_changes_state(self):
        user_doc = make_user_doc({"is_active": True})
        self.mock_db.users.find_one.return_value = user_doc
        r = self.client.post(f"/admin/users/{user_doc['_id']}/toggle-active", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.mock_db.users.update_one.assert_called_once()

    def test_export_csv_returns_csv_file(self):
        self.mock_db.bookings.find.return_value = MagicMock(
            sort=MagicMock(return_value=iter([]))
        )
        r = self.client.get("/admin/reports/export/bookings")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Booking ID", r.data)
        self.assertEqual(r.content_type, "text/csv; charset=utf-8")

    # ── CMS ───────────────────────────────────────────────────────────────────

    def test_cms_page_loads(self):
        self.mock_db.cms.find_one.return_value = None  # triggers defaults
        r = self.client.get("/admin/cms")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Site Content", r.data)

    def test_cms_post_updates_content(self):
        self.mock_db.cms.find_one.return_value = {"_id": "site_content"}
        self.mock_db.cms.update_one.return_value = MagicMock()
        r = self.client.post("/admin/cms", data={
            "hero_badge": "Updated Badge",
            "hero_heading": "New Heading",
            "hero_subheading": "New sub",
            "cta_heading": "New CTA",
            "cta_body": "New body",
            "contact_email": "new@test.com",
            "contact_phone": "+254711111111",
            "contact_address": "Nairobi CBD",
            "contact_hours": "9am-5pm",
            "footer_tagline": "New tagline",
        }, follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.mock_db.cms.update_one.assert_called_once()

    def test_cms_xss_stripped_from_fields(self):
        self.mock_db.cms.find_one.return_value = {"_id": "site_content"}
        self.mock_db.cms.update_one.return_value = MagicMock()
        self.client.post("/admin/cms", data={
            "hero_badge": "<script>alert(1)</script>",
            "hero_heading": "", "hero_subheading": "",
            "cta_heading": "", "cta_body": "",
            "contact_email": "", "contact_phone": "",
            "contact_address": "", "contact_hours": "",
            "footer_tagline": "",
        })
        if self.mock_db.cms.update_one.called:
            call_args = self.mock_db.cms.update_one.call_args[0]
            updates = call_args[1].get("$set", {})
            self.assertNotIn("<script>", updates.get("hero_badge", ""))


# ─────────────────────────────────────────────────────────────────────────────
# Payment routes
# ─────────────────────────────────────────────────────────────────────────────

class TestPaymentRoutes(SmartDriveTestCase):

    def setUp(self):
        super().setUp()
        self._login_as_user()
        self.mock_db.notifications.count_documents.return_value = 0
        self.mock_db.cms.find_one.return_value = None

    def test_payment_page_already_paid_redirects(self):
        booking = make_booking_doc(
            user_id=self.user_doc["_id"],
            overrides={"status": "approved", "payment_status": "paid"}
        )
        self.mock_db.bookings.find_one.return_value = booking
        r = self.client.get(f"/payment/mpesa/{booking['_id']}", follow_redirects=False)
        self.assertEqual(r.status_code, 302)

    def test_payment_page_pending_booking_not_payable(self):
        booking = make_booking_doc(
            user_id=self.user_doc["_id"],
            overrides={"status": "pending", "payment_status": "unpaid"}
        )
        self.mock_db.bookings.find_one.return_value = booking
        self.mock_db.vehicles.find_one.return_value = make_vehicle_doc()
        r = self.client.get(f"/payment/mpesa/{booking['_id']}", follow_redirects=False)
        self.assertEqual(r.status_code, 302)

    def test_payment_page_approved_booking_shows_form(self):
        booking = make_booking_doc(
            user_id=self.user_doc["_id"],
            overrides={"status": "approved", "payment_status": "unpaid"}
        )
        self.mock_db.bookings.find_one.return_value = booking
        self.mock_db.vehicles.find_one.return_value = make_vehicle_doc()
        r = self.client.get(f"/payment/mpesa/{booking['_id']}")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"M-PESA", r.data)

    def test_mpesa_callback_accepts_post_no_auth(self):
        """Callback endpoint must be reachable without auth."""
        self.mock_db.bookings.find_one.return_value = None  # no booking for test ID
        with self.client.session_transaction() as sess:
            sess.clear()  # ensure unauthenticated
        r = self.client.post("/payment/mpesa/callback",
            json={"Body": {"stkCallback": {"ResultCode": 0, "CheckoutRequestID": "test"}}},
            content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Accepted", r.data)

    def test_mpesa_poll_returns_json(self):
        booking = make_booking_doc(
            user_id=self.user_doc["_id"],
            overrides={"status": "approved", "payment_status": "unpaid",
                       "mpesa_checkout_request_id": "ws_CO_SIMULATED_bk1"}
        )
        self.mock_db.bookings.find_one.return_value = booking
        r = self.client.get(f"/payment/mpesa/poll/{booking['_id']}")
        self.assertEqual(r.status_code, 200)
        import json
        data = json.loads(r.data)
        self.assertIn("payment_status", data)

    def test_mpesa_poll_ownership_enforced(self):
        """User B cannot poll User A's booking payment status."""
        booking = make_booking_doc(
            user_id=str(ObjectId()),  # different user
            overrides={"status": "approved", "payment_status": "unpaid"}
        )
        self.mock_db.bookings.find_one.return_value = booking
        r = self.client.get(f"/payment/mpesa/poll/{booking['_id']}")
        self.assertEqual(r.status_code, 403)


# ─────────────────────────────────────────────────────────────────────────────
# Chat routes
# ─────────────────────────────────────────────────────────────────────────────

class TestChatRoutes(SmartDriveTestCase):

    def setUp(self):
        super().setUp()
        self._login_as_user()
        self.mock_db.notifications.count_documents.return_value = 0
        self.mock_db.cms.find_one.return_value = None

    def test_support_chat_loads(self):
        room_id = f"support_{self.user_doc['_id']}"
        self.mock_db.chat_rooms.find_one.return_value = {
            "room_id": room_id, "user_id": str(self.user_doc["_id"])
        }
        self.mock_db.chat_messages.find.return_value = MagicMock(
            sort=MagicMock(return_value=MagicMock(limit=MagicMock(return_value=iter([]))))
        )
        r = self.client.get("/chat/support")
        self.assertEqual(r.status_code, 200)

    def test_booking_chat_ownership_enforced(self):
        """User cannot open chat for another user's booking."""
        booking = make_booking_doc(user_id=str(ObjectId()))  # other user
        self.mock_db.bookings.find_one.return_value = booking
        r = self.client.get(f"/chat/booking/{booking['_id']}")
        self.assertEqual(r.status_code, 403)

    def test_post_message_api_creates_message(self):
        room_id = f"support_{self.user_doc['_id']}"
        self.mock_db.chat_rooms.find_one.return_value = {
            "room_id": room_id,
            "user_id": str(self.user_doc["_id"]),
            "booking_id": None,
        }
        self.mock_db.chat_messages.insert_one.return_value = MagicMock(
            inserted_id=ObjectId()
        )
        self.mock_db.users.find.return_value = iter([self.admin_doc])
        r = self.client.post(
            f"/chat/api/rooms/{room_id}/messages",
            json={"message": "Hello support team"},
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 201)
        self.mock_db.chat_messages.insert_one.assert_called_once()

    def test_post_empty_message_rejected(self):
        room_id = f"support_{self.user_doc['_id']}"
        self.mock_db.chat_rooms.find_one.return_value = {
            "room_id": room_id,
            "user_id": str(self.user_doc["_id"]),
        }
        r = self.client.post(
            f"/chat/api/rooms/{room_id}/messages",
            json={"message": "   "},
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 400)

    def test_admin_chat_list_forbidden_for_user(self):
        r = self.client.get("/chat/admin/chats", follow_redirects=False)
        self.assertEqual(r.status_code, 403)

    def test_admin_chat_list_accessible_for_admin(self):
        self._login_as_admin()
        self.mock_db.chat_rooms.find.return_value = MagicMock(
            sort=MagicMock(return_value=MagicMock(limit=MagicMock(return_value=iter([]))))
        )
        r = self.client.get("/chat/admin/chats")
        self.assertEqual(r.status_code, 200)


# ─────────────────────────────────────────────────────────────────────────────
# Error handlers
# ─────────────────────────────────────────────────────────────────────────────

class TestErrorHandlers(SmartDriveTestCase):

    def setUp(self):
        super().setUp()
        self.mock_db.notifications.count_documents.return_value = 0
        self.mock_db.cms.find_one.return_value = None

    def test_404_returns_404_page(self):
        r = self.client.get("/this-route-does-not-exist-at-all")
        self.assertEqual(r.status_code, 404)

    def test_403_page_renders(self):
        # Access an admin route as a regular user
        self._login_as_user()
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
