# Contributing to SmartDrive

## Development workflow

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make changes
3. Run syntax checks (see below)
4. Commit with a descriptive message
5. Open a pull request against `main`

## Commit message format

```
<type>: <short description>

type: feat | fix | docs | style | refactor | test | chore
```

Examples:
```
feat: add vehicle availability calendar view
fix: prevent double-booking on concurrent requests
docs: update M-Pesa sandbox setup instructions
```

## Syntax checks before committing

```bash
# Python syntax
python3 -m py_compile app/__init__.py app/database.py app/forms.py \
  app/models/*.py app/routes/*.py app/utils/*.py config/settings.py

# Jinja2 templates
python3 -c "
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
import pathlib
env = Environment(loader=FileSystemLoader('app/templates'))
for p in pathlib.Path('app/templates').rglob('*.html'):
    try: env.parse(p.read_text())
    except TemplateSyntaxError as e: print(f'ERROR {p}: {e}')
print('Templates OK')
"
```

## Adding a new route

1. Define the route in the appropriate blueprint file in `app/routes/`
2. If it handles POST data, create a WTForms class in `app/forms.py`
3. Create a template in `app/templates/<blueprint>/`
4. If the route requires login: add `@login_required`
5. If the route requires admin: add `@login_required` AND `@admin_required`
6. Add the route to the API reference in `README.md` Section 7

## Adding a new collection

1. Design the document schema
2. Add MongoDB index creation to `init_db()` in `app/database.py`
3. Document the schema in `README.md` Section 6

## Environment variables

Never hardcode credentials. Always read from environment variables via `os.environ.get()`. Add new variables to both `.env.example` and the reference table in `README.md` Section 5.

## CSS / Frontend

All styles live in `app/static/css/main.css`. The file uses CSS custom properties (tokens) defined in `:root` and `[data-theme="dark"]`. Always use token values rather than hardcoded colours:

```css
/* ✅ Correct */
color: var(--text-primary);
background: var(--bg-surface);
border: 1px solid var(--border);

/* ❌ Wrong */
color: #0f172a;
background: #ffffff;
border: 1px solid #e2e8f0;
```
