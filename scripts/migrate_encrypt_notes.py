"""One-off migration: encrypt any pre-existing plaintext Note.content rows.

Run this against a database that predates note-content encryption, before
deploying the encrypted version of the app. Idempotent — rows that already
decrypt successfully with the current NOTES_ENCRYPTION_PASSWORD are left
untouched, so it is safe to run more than once.

Usage:
    NOTES_ENCRYPTION_PASSWORD=... python scripts/migrate_encrypt_notes.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.fernet import InvalidToken
from sqlalchemy import text

from app import app
from models import _fernet, db


def migrate():
    with app.app_context():
        conn = db.session.connection()
        rows = conn.execute(text("SELECT id, content FROM notes")).fetchall()
        migrated = 0
        for note_id, content in rows:
            try:
                _fernet.decrypt(content.encode())
                continue
            except InvalidToken:
                pass
            encrypted = _fernet.encrypt(content.encode()).decode()
            conn.execute(
                text("UPDATE notes SET content = :content WHERE id = :id"),
                {"content": encrypted, "id": note_id},
            )
            migrated += 1
        db.session.commit()
        print(f"Migrated {migrated} of {len(rows)} note(s).")


if __name__ == "__main__":
    migrate()
