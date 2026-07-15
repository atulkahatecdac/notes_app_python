# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A small Flask + SQLite notes app with per-user auth. Full spec lives in [SPECS.MD](SPECS.MD) — read it for the data model and feature scope; it also asks for concise, low-verbosity replies when working in this repo.

## Running

```
pip install -r requirements.txt
NOTES_ENCRYPTION_PASSWORD=password python app.py
```

`NOTES_ENCRYPTION_PASSWORD` is required — `models.py` derives the `Note.content` encryption key from it and fails fast at import time if it's unset. Runs the Flask dev server (debug mode, no reloader) on the default port.

Run tests with `pytest` (repo root — `tests/conftest.py` sets a default `NOTES_ENCRYPTION_PASSWORD` for the test run and puts the repo root on `sys.path`).

The SQLite DB (`instance/notes.db`) is created automatically via `db.create_all()` on app startup — there are no schema migrations (no Flask-Migrate/Alembic). Schema changes require either deleting `instance/notes.db` (dev only, destroys data) or hand-writing a migration.

`Note.content` is encrypted at rest ([models.py](models.py)'s `EncryptedText` type, backed by Fernet). Any database with content written before encryption was added has plaintext rows — run `python scripts/migrate_encrypt_notes.py` (idempotent) before deploying encryption against such a database, or reads will raise a `ValueError` pointing at the script. This migration is one-way at the application level: rolling the code back after migrating does not restore plaintext, since old code has no decryption step and will display raw ciphertext instead of note content.

## Architecture

Everything lives in two files:

- [models.py](models.py) — SQLAlchemy models: `User` (Flask-Login `UserMixin`, password hashing via Werkzeug) and `Note` (owned by a `User` via `user_id` FK).
- [app.py](app.py) — single Flask app: config, `db.init_app`, `LoginManager` setup, and all routes (auth + note CRUD) in one module. No blueprints.

Templates in `templates/` extend [base.html](templates/base.html) (Jinja2 blocks `title`/`content`); styling is one global stylesheet at `static/style.css`.

Key pattern: every note route resolves the note through `_get_owned_note()` in [app.py](app.py) rather than a bare `db.get_or_404`, which enforces that a note's `user_id` matches `current_user.id` (404/403 otherwise) — replicate this pattern for any new note-scoped route rather than querying `Note` directly.

`SECRET_KEY` and the DB URI are hardcoded in `app.py` (dev-only placeholder secret) — no environment-based config layer exists.
