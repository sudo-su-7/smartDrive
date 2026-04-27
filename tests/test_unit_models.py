"""
UNIT TESTS — Models layer
Tests: User, vehicle helpers, booking document builder, availability checker
Mocks: bcrypt calls where hashing would be slow, ObjectId
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from tests.conftest import make_user_doc, make_vehicle_doc, make_booking_doc, make_mock_db


# ─────────────────────────────────────────────────────────────────────────────
# User model
# ─────────────────────────────────────────────────────────────────────────────

class TestUserModel(unittest.TestCase):

    def setUp(self):
        from app.models.user import User
        self.User = User
        self.doc = make_user_doc()
        self.user = User(self.doc)

    # ── Properties ────────────────────────────────────────────────────────────

    def test_id_returns_string(self):
        self.assertIsInstance(self.user.id, str)
        self.assertEqual(self.user.id, str(self.doc["_id"]))

    def test_name_property(self):
        self.assertEqual(self.user.name, "Test User")

    def test_email_property(self):
        self.assertEqual(self.user.email, "test@example.com")

    def test_role_property_default_user(self):
        self.assertEqual(self.user.role, "user")

    def test_is_active_true(self):
        self.assertTrue(self.user.is_active)

    def test_is_active_false_when_suspended(self):
        doc = make_user_doc({"is_active": False})
        user = self.User(doc)
        self.assertFalse(user.is_active)

    def test_is_active_defaults_true_missing_field(self):
        doc = make_user_doc()
        del doc["is_active"]
        user = self.User(doc)
        self.assertTrue(user.is_active)

    def test_is_admin_false_for_regular_user(self):
        self.assertFalse(self.user.is_admin())

    def test_is_admin_true_for_admin(self):
        doc = make_user_doc({"role": "admin"})
        user = self.User(doc)
        self.assertTrue(user.is_admin())

    def test_phone_empty_string_when_missing(self):
        doc = make_user_doc()
        doc.pop("phone", None)
        user = self.User(doc)
        self.assertEqual(user.phone, "")

    def test_email_verified_property(self):
        self.assertTrue(self.user.email_verified)

    def test_get_id_returns_string(self):
        self.assertIsInstance(self.user.get_id(), str)

    def test_from_db_returns_none_on_none_doc(self):
        result = self.User.from_db(None)
        self.assertIsNone(result)

    def test_from_db_returns_user_on_valid_doc(self):
        user = self.User.from_db(self.doc)
        self.assertIsNotNone(user)
        self.assertEqual(user.name, "Test User")

    # ── Password ───────────────────────────────────────────────────────────────

    @patch("app.models.user.bcrypt")
    def test_hash_password_calls_bcrypt(self, mock_bcrypt):
        mock_bcrypt.hashpw.return_value = b"$2b$12$hashed"
        mock_bcrypt.gensalt.return_value = b"$2b$12$salt"
        result = self.User.hash_password("MyPassword1!")
        mock_bcrypt.hashpw.assert_called_once()
        self.assertIsInstance(result, str)

    @patch("app.models.user.bcrypt")
    def test_check_password_correct(self, mock_bcrypt):
        mock_bcrypt.checkpw.return_value = True
        doc = make_user_doc({"password_hash": "$2b$12$reallyhashedvalue"})
        user = self.User(doc)
        self.assertTrue(user.check_password("correct_password"))

    @patch("app.models.user.bcrypt")
    def test_check_password_wrong(self, mock_bcrypt):
        mock_bcrypt.checkpw.return_value = False
        doc = make_user_doc({"password_hash": "$2b$12$reallyhashedvalue"})
        user = self.User(doc)
        self.assertFalse(user.check_password("wrong_password"))

    @patch("app.models.user.bcrypt")
    def test_check_password_empty_hash(self, mock_bcrypt):
        mock_bcrypt.checkpw.return_value = False
        doc = make_user_doc({"password_hash": ""})
        user = self.User(doc)
        self.assertFalse(user.check_password("anything"))

    # ── make_document ─────────────────────────────────────────────────────────

    @patch("app.models.user.bcrypt")
    def test_make_document_structure(self, mock_bcrypt):
        mock_bcrypt.hashpw.return_value = b"$2b$12$hash"
        mock_bcrypt.gensalt.return_value = b"salt"
        doc = self.User.make_document("Jane Doe", "JANE@Example.COM", "Pass1!", "+254712345678")
        self.assertEqual(doc["email"], "jane@example.com")  # lowercased
        self.assertEqual(doc["name"], "Jane Doe")
        self.assertEqual(doc["role"], "user")
        self.assertFalse(doc["email_verified"])
        self.assertIn("created_at", doc)
        self.assertIn("updated_at", doc)

    @patch("app.models.user.bcrypt")
    def test_make_document_strips_whitespace(self, mock_bcrypt):
        mock_bcrypt.hashpw.return_value = b"$2b$12$hash"
        mock_bcrypt.gensalt.return_value = b"salt"
        doc = self.User.make_document("  Jane  ", "  jane@test.com  ", "Pass1!", "  ")
        self.assertEqual(doc["name"], "Jane")
        self.assertEqual(doc["email"], "jane@test.com")
        self.assertEqual(doc["phone"], "")

    @patch("app.models.user.bcrypt")
    def test_make_document_max_length_name(self, mock_bcrypt):
        mock_bcrypt.hashpw.return_value = b"$2b$12$hash"
        mock_bcrypt.gensalt.return_value = b"salt"
        long_name = "A" * 200
        doc = self.User.make_document(long_name, "e@test.com", "Pass1!")
        self.assertLessEqual(len(doc["name"]), 200)


# ─────────────────────────────────────────────────────────────────────────────
# Vehicle model
# ─────────────────────────────────────────────────────────────────────────────

class TestVehicleModel(unittest.TestCase):

    def test_make_vehicle_document_basic(self):
        from app.models.vehicle import make_vehicle_document
        doc = make_vehicle_document(
            name="Toyota Corolla",
            model="2022",
            plate_number="kda 001a",
            price_per_day=3500.50,
            capacity=5,
            fuel_type="petrol",
            transmission="automatic",
            description="A good car.",
        )
        self.assertEqual(doc["plate_number"], "KDA 001A")  # uppercased
        self.assertEqual(doc["price_per_day"], 3500.50)
        self.assertEqual(doc["status"], "available")
        self.assertIn("created_at", doc)

    def test_make_vehicle_document_strips_whitespace(self):
        from app.models.vehicle import make_vehicle_document
        doc = make_vehicle_document(
            name="  Nissan X-Trail  ", model="  2023  ", plate_number=" KDC 003C ",
            price_per_day=5500, capacity=7, fuel_type="petrol",
            transmission="automatic", description="  Great SUV.  "
        )
        self.assertEqual(doc["name"], "Nissan X-Trail")
        self.assertEqual(doc["description"], "Great SUV.")

    def test_make_vehicle_document_price_rounded(self):
        from app.models.vehicle import make_vehicle_document
        doc = make_vehicle_document("X", "Y", "Z", 3500.123456, 5, "petrol", "auto", "")
        self.assertEqual(doc["price_per_day"], 3500.12)

    def test_make_vehicle_document_zero_price_allowed(self):
        from app.models.vehicle import make_vehicle_document
        doc = make_vehicle_document("X", "Y", "Z", 0, 5, "petrol", "auto", "")
        self.assertEqual(doc["price_per_day"], 0.0)

    def test_make_vehicle_document_negative_capacity_stored_as_int(self):
        """Capacity validation is at form layer; model just stores the value."""
        from app.models.vehicle import make_vehicle_document
        doc = make_vehicle_document("X", "Y", "Z", 100, -1, "petrol", "auto", "")
        self.assertEqual(doc["capacity"], -1)

    # ── vehicle_is_available ──────────────────────────────────────────────────

    def test_vehicle_available_no_conflicting_bookings(self):
        from app.models.vehicle import vehicle_is_available
        db = make_mock_db()
        db.bookings.count_documents.return_value = 0
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 5, tzinfo=timezone.utc)
        result = vehicle_is_available(db, "abc123", start, end)
        self.assertTrue(result)
        db.bookings.count_documents.assert_called_once()

    def test_vehicle_not_available_with_overlap(self):
        from app.models.vehicle import vehicle_is_available
        db = make_mock_db()
        db.bookings.count_documents.return_value = 1
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 5, tzinfo=timezone.utc)
        result = vehicle_is_available(db, "abc123", start, end)
        self.assertFalse(result)

    def test_vehicle_available_excludes_given_booking_id(self):
        from app.models.vehicle import vehicle_is_available
        db = make_mock_db()
        db.bookings.count_documents.return_value = 0
        oid = ObjectId()
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 5, tzinfo=timezone.utc)
        vehicle_is_available(db, "abc123", start, end, exclude_booking_id=str(oid))
        call_args = db.bookings.count_documents.call_args[0][0]
        self.assertIn("$ne", str(call_args))

    def test_vehicle_available_same_start_end_treated_as_one_day(self):
        from app.models.vehicle import vehicle_is_available
        db = make_mock_db()
        db.bookings.count_documents.return_value = 0
        t = datetime(2025, 7, 1, tzinfo=timezone.utc)
        result = vehicle_is_available(db, "abc123", t, t)
        self.assertTrue(result)


# ─────────────────────────────────────────────────────────────────────────────
# Booking model
# ─────────────────────────────────────────────────────────────────────────────

class TestBookingModel(unittest.TestCase):

    def test_make_booking_document_calculates_days(self):
        from app.models.booking import make_booking_document
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 4, tzinfo=timezone.utc)
        doc = make_booking_document("uid", "vid", start, end, 3500.0)
        self.assertEqual(doc["days"], 3)
        self.assertEqual(doc["total_amount"], 10500.0)

    def test_make_booking_document_minimum_one_day(self):
        from app.models.booking import make_booking_document
        same = datetime(2025, 7, 1, tzinfo=timezone.utc)
        doc = make_booking_document("uid", "vid", same, same, 3500.0)
        self.assertEqual(doc["days"], 1)
        self.assertEqual(doc["total_amount"], 3500.0)

    def test_make_booking_document_status_defaults(self):
        from app.models.booking import make_booking_document
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 5, tzinfo=timezone.utc)
        doc = make_booking_document("uid", "vid", start, end, 1000.0)
        self.assertEqual(doc["status"], "pending")
        self.assertEqual(doc["payment_status"], "unpaid")

    def test_make_booking_document_notes_stripped(self):
        from app.models.booking import make_booking_document
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 5, tzinfo=timezone.utc)
        doc = make_booking_document("uid", "vid", start, end, 1000.0, notes="  hello  ")
        self.assertEqual(doc["notes"], "hello")

    def test_make_booking_document_empty_notes(self):
        from app.models.booking import make_booking_document
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 5, tzinfo=timezone.utc)
        doc = make_booking_document("uid", "vid", start, end, 1000.0, notes="")
        self.assertEqual(doc["notes"], "")

    def test_make_booking_document_includes_locations(self):
        from app.models.booking import make_booking_document
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 5, tzinfo=timezone.utc)
        pickup  = {"address": "Westlands", "lat": -1.26, "lng": 36.80}
        dropoff = {"address": "CBD", "lat": -1.28, "lng": 36.82}
        doc = make_booking_document("uid", "vid", start, end, 1000.0,
                                    pickup_location=pickup, dropoff_location=dropoff)
        self.assertEqual(doc["pickup_location"]["address"], "Westlands")
        self.assertEqual(doc["dropoff_location"]["lat"], -1.28)

    def test_make_booking_document_none_locations_default_empty(self):
        from app.models.booking import make_booking_document
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 5, tzinfo=timezone.utc)
        doc = make_booking_document("uid", "vid", start, end, 1000.0)
        self.assertEqual(doc["pickup_location"], {})
        self.assertEqual(doc["dropoff_location"], {})

    def test_make_booking_document_mpesa_fields_null_by_default(self):
        from app.models.booking import make_booking_document
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 5, tzinfo=timezone.utc)
        doc = make_booking_document("uid", "vid", start, end, 1000.0)
        self.assertIsNone(doc["mpesa_checkout_request_id"])
        self.assertIsNone(doc["mpesa_transaction_id"])

    def test_make_booking_document_rounding(self):
        from app.models.booking import make_booking_document
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 4, tzinfo=timezone.utc)
        doc = make_booking_document("uid", "vid", start, end, 3333.333)
        self.assertEqual(doc["total_amount"], 9999.99)  # 3333.33 * 3

    def test_make_booking_document_large_price(self):
        from app.models.booking import make_booking_document
        start = datetime(2025, 7, 1, tzinfo=timezone.utc)
        end   = datetime(2025, 7, 31, tzinfo=timezone.utc)
        doc = make_booking_document("uid", "vid", start, end, 15000.0)
        self.assertEqual(doc["days"], 30)
        self.assertEqual(doc["total_amount"], 450000.0)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestHelpers(unittest.TestCase):

    def test_sanitize_string_strips_html(self):
        from app.utils.helpers import sanitize_string
        self.assertEqual(sanitize_string("<script>alert(1)</script>hello"), "hello")

    def test_sanitize_string_strips_tags(self):
        from app.utils.helpers import sanitize_string
        self.assertEqual(sanitize_string("<b>bold</b>"), "bold")

    def test_sanitize_string_max_length(self):
        from app.utils.helpers import sanitize_string
        result = sanitize_string("A" * 300, max_length=100)
        self.assertEqual(len(result), 100)

    def test_sanitize_string_empty(self):
        from app.utils.helpers import sanitize_string
        self.assertEqual(sanitize_string(""), "")

    def test_sanitize_string_plain_text_unchanged(self):
        from app.utils.helpers import sanitize_string
        self.assertEqual(sanitize_string("Hello Nairobi"), "Hello Nairobi")

    def test_sanitize_string_xss_attempt(self):
        from app.utils.helpers import sanitize_string
        result = sanitize_string('<img src=x onerror="alert(1)">')
        self.assertNotIn("<img", result)
        self.assertNotIn("onerror", result)

    def test_sanitize_string_sql_injection_unchanged(self):
        """SQL injection strings are plain text — bleach shouldn't alter them."""
        from app.utils.helpers import sanitize_string
        sql = "' OR 1=1 --"
        self.assertEqual(sanitize_string(sql), sql)

    def test_paginator_first_page(self):
        from app.utils.helpers import Paginator
        p = Paginator(total=50, page=1, per_page=10)
        self.assertEqual(p.pages, 5)
        self.assertEqual(p.skip, 0)
        self.assertFalse(p.has_prev)
        self.assertTrue(p.has_next)

    def test_paginator_last_page(self):
        from app.utils.helpers import Paginator
        p = Paginator(total=50, page=5, per_page=10)
        self.assertEqual(p.skip, 40)
        self.assertTrue(p.has_prev)
        self.assertFalse(p.has_next)

    def test_paginator_single_page(self):
        from app.utils.helpers import Paginator
        p = Paginator(total=5, page=1, per_page=10)
        self.assertEqual(p.pages, 1)
        self.assertFalse(p.has_prev)
        self.assertFalse(p.has_next)

    def test_paginator_zero_total(self):
        from app.utils.helpers import Paginator
        p = Paginator(total=0, page=1, per_page=10)
        self.assertEqual(p.pages, 1)
        self.assertEqual(p.skip, 0)

    def test_paginator_page_clamped_to_one(self):
        from app.utils.helpers import Paginator
        p = Paginator(total=100, page=-5, per_page=10)
        self.assertEqual(p.page, 1)

    def test_paginator_iter_pages_no_ellipsis_few_pages(self):
        from app.utils.helpers import Paginator
        p = Paginator(total=30, page=2, per_page=10)
        pages = list(p.iter_pages())
        self.assertNotIn(None, pages)
        self.assertEqual(pages, [1, 2, 3])

    def test_paginator_iter_pages_has_ellipsis_many_pages(self):
        from app.utils.helpers import Paginator
        p = Paginator(total=200, page=10, per_page=10)
        pages = list(p.iter_pages())
        self.assertIn(None, pages)

    def test_validate_password_strength_valid(self):
        from app.utils.helpers import validate_password_strength
        ok, msg = validate_password_strength("SecurePass1!")
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_validate_password_strength_too_short(self):
        from app.utils.helpers import validate_password_strength
        ok, msg = validate_password_strength("Ab1!")
        self.assertFalse(ok)

    def test_validate_password_strength_no_special_char(self):
        from app.utils.helpers import validate_password_strength
        ok, msg = validate_password_strength("SecurePass123")
        self.assertFalse(ok)

    def test_validate_password_strength_no_uppercase(self):
        from app.utils.helpers import validate_password_strength
        ok, msg = validate_password_strength("securepass1!")
        self.assertFalse(ok)

    def test_validate_password_strength_empty(self):
        from app.utils.helpers import validate_password_strength
        ok, msg = validate_password_strength("")
        self.assertFalse(ok)


# ─────────────────────────────────────────────────────────────────────────────
# M-Pesa utility
# ─────────────────────────────────────────────────────────────────────────────

class TestMpesaUtils(unittest.TestCase):

    @patch.dict("os.environ", {"MPESA_CONSUMER_KEY": "", "MPESA_CONSUMER_SECRET": ""})
    def test_get_access_token_returns_dummy_when_no_credentials(self):
        from app.utils.mpesa import get_access_token
        token = get_access_token()
        self.assertEqual(token, "dummy-token")

    @patch.dict("os.environ", {"MPESA_CONSUMER_KEY": "key", "MPESA_CONSUMER_SECRET": "secret"})
    @patch("app.utils.mpesa.requests.get")
    def test_get_access_token_success(self, mock_get):
        from app.utils.mpesa import get_access_token
        mock_get.return_value.json.return_value = {"access_token": "real_token_123"}
        mock_get.return_value.raise_for_status = MagicMock()
        token = get_access_token()
        self.assertEqual(token, "real_token_123")

    @patch.dict("os.environ", {"MPESA_CONSUMER_KEY": "key", "MPESA_CONSUMER_SECRET": "secret"})
    @patch("app.utils.mpesa.requests.get")
    def test_get_access_token_network_error_returns_none(self, mock_get):
        from app.utils.mpesa import get_access_token
        mock_get.side_effect = Exception("Network error")
        token = get_access_token()
        self.assertIsNone(token)

    @patch.dict("os.environ", {"MPESA_CONSUMER_KEY": "", "MPESA_CONSUMER_SECRET": ""})
    def test_stk_push_sandbox_simulation(self):
        from app.utils.mpesa import stk_push
        result = stk_push(phone="0712345678", amount=3500, booking_id="booking123")
        self.assertEqual(result["ResponseCode"], "0")
        self.assertIn("CheckoutRequestID", result)
        self.assertIn("SIMULATED", result["CheckoutRequestID"])

    @patch.dict("os.environ", {"MPESA_CONSUMER_KEY": "", "MPESA_CONSUMER_SECRET": ""})
    def test_stk_push_normalises_phone_07_format(self):
        """Phone starting with 07 should be normalised to 2547..."""
        from app.utils.mpesa import stk_push
        result = stk_push(phone="0712345678", amount=1000, booking_id="bk1")
        # No error raised — normalisation succeeded
        self.assertIn("ResponseCode", result)

    @patch.dict("os.environ", {"MPESA_CONSUMER_KEY": "", "MPESA_CONSUMER_SECRET": ""})
    def test_stk_push_normalises_plus254_format(self):
        from app.utils.mpesa import stk_push
        result = stk_push(phone="+254712345678", amount=1000, booking_id="bk1")
        self.assertIn("ResponseCode", result)

    @patch.dict("os.environ", {"MPESA_CONSUMER_KEY": "", "MPESA_CONSUMER_SECRET": ""})
    def test_stk_push_normalises_254_format(self):
        from app.utils.mpesa import stk_push
        result = stk_push(phone="254712345678", amount=1000, booking_id="bk1")
        self.assertIn("ResponseCode", result)

    @patch.dict("os.environ", {
        "MPESA_CONSUMER_KEY": "key", "MPESA_CONSUMER_SECRET": "secret",
        "MPESA_SHORTCODE": "174379", "MPESA_PASSKEY": "testpasskey",
        "MPESA_CALLBACK_URL": "https://example.com/callback",
    })
    @patch("app.utils.mpesa.requests.post")
    @patch("app.utils.mpesa.get_access_token")
    def test_stk_push_real_api_call(self, mock_token, mock_post):
        from app.utils.mpesa import stk_push
        mock_token.return_value = "valid_token"
        mock_post.return_value.json.return_value = {
            "ResponseCode": "0",
            "CheckoutRequestID": "ws_CO_123",
            "ResponseDescription": "Success",
        }
        mock_post.return_value.raise_for_status = MagicMock()
        result = stk_push(phone="0712345678", amount=3500, booking_id="bk123")
        self.assertEqual(result["ResponseCode"], "0")
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["Amount"], 3500)
        self.assertEqual(payload["PhoneNumber"], "254712345678")

    @patch.dict("os.environ", {
        "MPESA_CONSUMER_KEY": "key", "MPESA_CONSUMER_SECRET": "secret",
        "MPESA_SHORTCODE": "174379", "MPESA_PASSKEY": "testpasskey",
    })
    @patch("app.utils.mpesa.requests.post")
    @patch("app.utils.mpesa.get_access_token")
    def test_stk_push_http_error_returns_error_dict(self, mock_token, mock_post):
        from app.utils.mpesa import stk_push
        import requests as req
        mock_token.return_value = "valid_token"
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value.raise_for_status.side_effect = req.HTTPError(response=mock_response)
        result = stk_push(phone="0712345678", amount=3500, booking_id="bk1")
        self.assertIn("error", result)

    @patch.dict("os.environ", {"MPESA_CONSUMER_KEY": "", "MPESA_CONSUMER_SECRET": ""})
    def test_query_stk_status_sandbox_simulation(self):
        from app.utils.mpesa import query_stk_status
        result = query_stk_status("ws_CO_SIMULATED_booking123")
        self.assertEqual(result["ResultCode"], "0")

    def test_stk_push_amount_rounded_to_int(self):
        """Verify amount is sent as integer (M-Pesa doesn't accept decimals)."""
        with patch.dict("os.environ", {
            "MPESA_CONSUMER_KEY": "k", "MPESA_CONSUMER_SECRET": "s",
            "MPESA_SHORTCODE": "174379", "MPESA_PASSKEY": "pk",
            "MPESA_CALLBACK_URL": "https://cb.example.com/callback",
        }):
            with patch("app.utils.mpesa.requests.post") as mock_post, \
                 patch("app.utils.mpesa.get_access_token", return_value="tok"):
                mock_post.return_value.json.return_value = {"ResponseCode": "0", "CheckoutRequestID": "x"}
                mock_post.return_value.raise_for_status = MagicMock()
                from app.utils.mpesa import stk_push
                stk_push("0712345678", 3499.99, "bk1")
                payload = mock_post.call_args.kwargs["json"]
                self.assertEqual(payload["Amount"], 3500)  # rounded
                self.assertIsInstance(payload["Amount"], int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
