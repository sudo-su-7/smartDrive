# SmartDrive Test Suite

## Overview

| File | Tests | Requires |
|---|---|---|
| `test_unit_models.py` | 55 tests — User, Vehicle, Booking models, Helpers, M-Pesa | `pip install -r requirements.txt` |
| `test_integration_routes.py` | 45 tests — all routes, auth flows, RBAC, CMS, payment, chat | Same |
| `test_frontend_js.py` | 42 tests — template structure, JS analysis (no browser), Playwright (browser) | Stdlib only for static; `playwright` for browser tests |
| `test_e2e_playwright.py` | 4 journeys — full user flows in real browser | `playwright` + running server |

## Running Tests

### 1. Static analysis tests (no dependencies needed — runs now)
```bash
python3 -m unittest tests.test_frontend_js.TestTemplateStructure tests.test_frontend_js.TestMainJS -v
```

### 2. Full test suite (requires project dependencies)
```bash
# Install dependencies
pip install -r requirements.txt

# Run all unit + integration tests
python3 -m unittest discover tests -v

# With coverage report
pip install pytest pytest-cov
pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
# Open htmlcov/index.html for coverage report
```

### 3. E2E Playwright tests (requires running server + playwright)
```bash
# Install playwright
pip install playwright pytest-playwright
playwright install chromium

# Start the dev server in another terminal
python run.py

# Run E2E tests (pointing at localhost by default)
E2E_BASE_URL=http://localhost:5000 pytest tests/test_e2e_playwright.py -v

# Run against staging
E2E_BASE_URL=https://staging.smartdrive.co.ke pytest tests/test_e2e_playwright.py -v

# Screenshot on failure (playwright handles this automatically)
pytest tests/test_e2e_playwright.py --screenshot=on --video=retain-on-failure
```

## Coverage Targets

| Layer | Target | What's covered |
|---|---|---|
| Models + utils | 95%+ | All model factories, validators, helpers, M-Pesa utils |
| Routes (integration) | 80%+ | Happy path + error path for every endpoint |
| Templates | 100% | Structure, CSRF, accessibility attributes |
| E2E journeys | 4 critical paths | Registration, logout, approval+payment, CMS |

## CI/CD Integration (GitHub Actions example)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:6.0
        ports: ["27017:27017"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt pytest pytest-cov
      - run: pytest tests/ -v --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v3
```
