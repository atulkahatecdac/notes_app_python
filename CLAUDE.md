# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A small Flask + SQLite notes app with per-user auth. Full spec lives in [SPECS.MD](SPECS.MD) — read it for the data model and feature scope; it also asks for concise, low-verbosity replies when working in this repo.

## Running

```
pip install -r requirements.txt
python app.py
```

Runs the Flask dev server (debug mode, no reloader) on the default port. There is no test suite, linter, or build step configured in this repo.

The SQLite DB (`instance/notes.db`) is created automatically via `db.create_all()` on app startup — there are no migrations (no Flask-Migrate/Alembic). Schema changes require either deleting `instance/notes.db` (dev only, destroys data) or hand-writing a migration.

## Architecture

Everything lives in two files:

- [models.py](models.py) — SQLAlchemy models: `User` (Flask-Login `UserMixin`, password hashing via Werkzeug) and `Note` (owned by a `User` via `user_id` FK).
- [app.py](app.py) — single Flask app: config, `db.init_app`, `LoginManager` setup, and all routes (auth + note CRUD) in one module. No blueprints.

Templates in `templates/` extend [base.html](templates/base.html) (Jinja2 blocks `title`/`content`); styling is one global stylesheet at `static/style.css`.

Key pattern: every note route resolves the note through `_get_owned_note()` in [app.py](app.py) rather than a bare `db.get_or_404`, which enforces that a note's `user_id` matches `current_user.id` (404/403 otherwise) — replicate this pattern for any new note-scoped route rather than querying `Note` directly.

`SECRET_KEY` and the DB URI are hardcoded in `app.py` (dev-only placeholder secret) — no environment-based config layer exists.
