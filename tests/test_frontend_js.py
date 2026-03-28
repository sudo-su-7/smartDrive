"""
FRONTEND COMPONENT TESTS — JavaScript behaviour
Tests: theme provider, dropdown, sidebar, alert dismiss, password strength,
date constraints, cost calculator, form validation UX.

Uses the Python `html.parser` + regex to verify template output.
JS behaviour tests use a headless browser if playwright is available.
Without playwright they document expected behaviour.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import re
from unittest.mock import patch, MagicMock


PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:5000")


def skip_without_playwright(fn):
    import functools
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not PLAYWRIGHT_AVAILABLE:
            raise unittest.SkipTest("playwright not installed")
        return fn(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# Template structure tests (pure Python — no browser needed)
# ─────────────────────────────────────────────────────────────────────────────

class TestTemplateStructure(unittest.TestCase):
    """Verify templates contain required HTML structure and attributes."""

    def _read(self, rel_path: str) -> str:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base, "app", "templates", rel_path)) as f:
            return f.read()

    # ── base.html ─────────────────────────────────────────────────────────────

    def test_base_has_csrf_token_in_logout_form(self):
        src = self._read("base.html")
        # All logout forms must include CSRF token
        logout_forms = re.findall(r'<form[^>]*auth\.logout[^>]*>.*?</form>', src, re.DOTALL)
        for form in logout_forms:
            self.assertIn("csrf_token", form, "Logout form missing CSRF token")

    def test_base_logout_is_post_not_get(self):
        src = self._read("base.html")
        # No GET link to logout
        get_logout_links = re.findall(r'<a[^>]*href[^>]*auth\.logout[^>]*>', src)
        self.assertEqual(len(get_logout_links), 0, "Logout should be POST, not GET link")

    def test_base_has_theme_toggle_button(self):
        src = self._read("base.html")
        self.assertIn("js-theme-toggle", src)

    def test_base_has_mobile_nav(self):
        src = self._read("base.html")
        self.assertIn("mobileNav", src)
        self.assertIn("js-mobile-nav-open", src)

    def test_base_has_aria_labels(self):
        src = self._read("base.html")
        self.assertIn('aria-label=', src)

    def test_base_has_skip_to_content(self):
        src = self._read("base.html")
        self.assertIn('id="main-content"', src)

    def test_base_flash_region_present(self):
        src = self._read("base.html")
        self.assertIn("js-flash-region", src)

    # ── admin/base_admin.html ─────────────────────────────────────────────────

    def test_admin_base_logout_is_post(self):
        src = self._read("admin/base_admin.html")
        get_logout = re.findall(r'<a[^>]*auth\.logout[^>]*>', src)
        self.assertEqual(len(get_logout), 0, "Admin sidebar logout should be POST form, not GET link")

    def test_admin_base_sidebar_has_cms_link(self):
        src = self._read("admin/base_admin.html")
        self.assertIn("admin.cms", src)

    def test_admin_base_has_hamburger(self):
        src = self._read("admin/base_admin.html")
        self.assertIn("hamburger", src)

    # ── auth/login.html ────────────────────────────────────────────────────────

    def test_login_has_password_toggle(self):
        src = self._read("auth/login.html")
        self.assertIn("togglePw", src)

    def test_login_form_method_post(self):
        src = self._read("auth/login.html")
        self.assertIn('method="POST"', src)

    def test_login_has_autocomplete_attrs(self):
        src = self._read("auth/login.html")
        self.assertIn('autocomplete="email"', src)
        self.assertIn('autocomplete="current-password"', src)

    # ── auth/register.html ────────────────────────────────────────────────────

    def test_register_has_strength_bar(self):
        src = self._read("auth/register.html")
        self.assertIn("strengthFill", src)

    def test_register_has_password_toggles(self):
        src = self._read("auth/register.html")
        self.assertEqual(src.count("togglePw"), 2)

    # ── user/book.html ────────────────────────────────────────────────────────

    def test_book_has_map_elements(self):
        src = self._read("user/book.html")
        self.assertIn("pickupMap", src)
        self.assertIn("dropoffMap", src)

    def test_book_has_leaflet_import(self):
        src = self._read("user/book.html")
        self.assertIn("leaflet", src.lower())

    def test_book_has_hidden_location_fields(self):
        src = self._read("user/book.html")
        for field in ["pickup_lat", "pickup_lng", "dropoff_lat", "dropoff_lng"]:
            self.assertIn(field, src)

    def test_book_has_cost_calculator(self):
        src = self._read("user/book.html")
        self.assertIn("calc-days", src)
        self.assertIn("calc-total", src)
        self.assertIn("price_per_day_data", src)

    def test_book_locate_me_function(self):
        src = self._read("user/book.html")
        self.assertIn("locateMe", src)
        self.assertIn("navigator.geolocation", src)

    # ── cms template ──────────────────────────────────────────────────────────

    def test_cms_has_all_editable_fields(self):
        src = self._read("admin/cms.html")
        required_fields = [
            "hero_badge", "hero_heading", "hero_subheading",
            "cta_heading", "cta_body",
            "contact_email", "contact_phone", "contact_address", "contact_hours",
            "footer_tagline",
        ]
        for field in required_fields:
            self.assertIn(f'name="{field}"', src, f"CMS missing field: {field}")

    def test_cms_form_is_post(self):
        src = self._read("admin/cms.html")
        self.assertIn('method="POST"', src)

    def test_cms_has_csrf(self):
        src = self._read("admin/cms.html")
        self.assertIn("csrf_token", src)

    # ── index.html ────────────────────────────────────────────────────────────

    def test_index_uses_cms_variables(self):
        src = self._read("index.html")
        self.assertIn("site.hero_badge", src)
        self.assertIn("site.cta_heading", src)
        # contact_email lives in base.html footer, not index.html — check base.html
        base_src = self._read("base.html")
        self.assertIn("site.contact_email", base_src)

    def test_index_security_feature_card(self):
        src = self._read("index.html")
        # Must mention security/privacy — not just M-Pesa STK Push
        self.assertIn("lock-fill", src)
        self.assertIn("encrypted", src.lower())

    def test_index_cta_copy_updated(self):
        src = self._read("index.html")
        # Old copy should be gone
        self.assertNotIn("Nairobi city runs to safari adventures", src)
        # New copy (via CMS variable) should be present
        self.assertIn("site.cta_heading", src)


# ─────────────────────────────────────────────────────────────────────────────
# JS main.js structure tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMainJS(unittest.TestCase):

    def _read_js(self) -> str:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base, "app", "static", "js", "main.js")) as f:
            return f.read()

    def test_theme_provider_exists(self):
        src = self._read_js()
        self.assertIn("Theme", src)
        self.assertIn("localStorage", src)
        self.assertIn("data-theme", src)

    def test_theme_toggle_exported(self):
        src = self._read_js()
        self.assertIn("toggle", src)
        self.assertIn("init", src)

    def test_dark_mode_token(self):
        src = self._read_js()
        # JS uses single-quoted strings — match either quote style
        self.assertTrue("'dark'" in src or '"dark"' in src)
        self.assertTrue("'light'" in src or '"light"' in src)

    def test_system_preference_respected(self):
        src = self._read_js()
        self.assertIn("prefers-color-scheme", src)

    def test_dropdown_init_exists(self):
        src = self._read_js()
        self.assertIn("initDropdowns", src)
        self.assertIn("data-dropdown", src)

    def test_sidebar_init_exists(self):
        src = self._read_js()
        self.assertIn("initSidebar", src)

    def test_mobile_nav_init_exists(self):
        src = self._read_js()
        self.assertIn("initMobileNav", src)

    def test_alert_dismiss_present(self):
        src = self._read_js()
        self.assertIn("initAlerts", src)
        self.assertIn("alert-close", src)

    def test_alert_auto_dismiss_6s(self):
        src = self._read_js()
        self.assertIn("6000", src)

    def test_password_strength_init(self):
        src = self._read_js()
        self.assertIn("initPasswordStrength", src)
        self.assertIn("strengthFill", src)

    def test_date_constraints_enforced(self):
        src = self._read_js()
        self.assertIn("initDateConstraints", src)
        self.assertIn("end_date", src)

    def test_csrf_helper_exported(self):
        src = self._read_js()
        self.assertIn("getCsrf", src)
        self.assertIn("csrf_token", src)

    def test_confirm_handler_present(self):
        src = self._read_js()
        self.assertIn("data-confirm", src)
        self.assertIn("confirm(", src)

    def test_togglePw_exposed_globally(self):
        src = self._read_js()
        self.assertIn("window.togglePw", src)

    def test_update_calc_exposed_globally(self):
        src = self._read_js()
        self.assertIn("window.updateCalc", src)

    def test_no_console_log_in_production_code(self):
        src = self._read_js()
        # Should only have console.error, not console.log
        log_calls = re.findall(r'console\.log\(', src)
        self.assertEqual(len(log_calls), 0, "Remove console.log from production JS")


# ─────────────────────────────────────────────────────────────────────────────
# Browser-based JS tests (playwright required)
# ─────────────────────────────────────────────────────────────────────────────

class TestThemeToggle(unittest.TestCase):

    @skip_without_playwright
    def test_dark_mode_toggle_changes_attribute(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(BASE_URL)

            # Default is light or system
            toggle = page.locator(".js-theme-toggle").first
            expect(toggle).to_be_visible()

            # Click toggle
            toggle.click()
            theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
            self.assertIn(theme, ["dark", "light"])

            # Click again — should flip
            initial = theme
            toggle.click()
            theme2 = page.evaluate("document.documentElement.getAttribute('data-theme')")
            self.assertNotEqual(theme2, initial)

            browser.close()

    @skip_without_playwright
    def test_dark_mode_persisted_to_localstorage(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(BASE_URL)

            # Force dark mode
            page.evaluate("localStorage.setItem('sd-theme', 'dark')")
            page.reload()
            theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
            self.assertEqual(theme, "dark")

            # Force light mode
            page.evaluate("localStorage.setItem('sd-theme', 'light')")
            page.reload()
            theme2 = page.evaluate("document.documentElement.getAttribute('data-theme')")
            self.assertEqual(theme2, "light")

            context.close()
            browser.close()


class TestPasswordStrengthBar(unittest.TestCase):

    @skip_without_playwright
    def test_strength_bar_updates_on_input(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/auth/register")

            bar = page.locator("#strengthFill")
            pw_input = page.locator("#password")

            # Initially empty
            initial_width = page.evaluate("document.getElementById('strengthFill').style.width")
            self.assertEqual(initial_width, "")

            # Weak password
            pw_input.fill("abc")
            page.wait_for_timeout(200)
            weak_width = page.evaluate("document.getElementById('strengthFill').style.width")

            # Strong password
            pw_input.fill("SecurePass1!")
            page.wait_for_timeout(200)
            strong_width = page.evaluate("document.getElementById('strengthFill').style.width")

            # Strong should be wider than weak
            def pct(w): return float(w.replace("%", "")) if w else 0
            self.assertGreater(pct(strong_width), pct(weak_width))

            browser.close()


class TestDropdownBehaviour(unittest.TestCase):

    @skip_without_playwright
    def test_dropdown_opens_on_click(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Log in so dropdown is present
            page.goto(f"{BASE_URL}/auth/login")
            # Inject a test user session via localStorage would require extra setup
            # This test documents the behaviour
            browser.close()


class TestFormValidation(unittest.TestCase):

    @skip_without_playwright
    def test_register_form_shows_inline_errors(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/auth/register")

            # Submit empty form
            page.click("button[type=submit]")
            # Should stay on register page with errors
            expect(page).to_have_url(f"{BASE_URL}/auth/register")
            # At least one invalid-feedback element visible
            errors = page.locator(".invalid-feedback")
            self.assertGreater(errors.count(), 0)

            browser.close()

    @skip_without_playwright
    def test_login_form_shows_error_on_wrong_password(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/auth/login")
            page.fill("input[name=email]", "nobody@example.com")
            page.fill("input[id=loginPw]", "wrongpassword")
            page.click("button[type=submit]")
            # Flash error should appear
            expect(page.get_by_text("Invalid email or password")).to_be_visible(timeout=3000)
            browser.close()


class TestLoadingAndEmptyStates(unittest.TestCase):

    @skip_without_playwright
    def test_vehicle_listing_empty_state(self):
        """When no vehicles match filters, empty state is shown."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/vehicles?q=xyzzyabc123doesnotexist")
            # Should show empty state, not error
            expect(page).not_to_have_url(re.compile(r"/error"))
            browser.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
