import base64
import hashlib
import os
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.types import TypeDecorator, Text
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

try:
    _ENCRYPTION_PASSWORD = os.environ["NOTES_ENCRYPTION_PASSWORD"]
except KeyError as exc:
    raise RuntimeError(
        "NOTES_ENCRYPTION_PASSWORD environment variable must be set "
        "to encrypt/decrypt note content."
    ) from exc

_ENCRYPTION_KEY = base64.urlsafe_b64encode(hashlib.sha256(_ENCRYPTION_PASSWORD.encode()).digest())
_fernet = Fernet(_ENCRYPTION_KEY)


class EncryptedText(TypeDecorator):
    """Text column that is transparently encrypted at rest."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return _fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        try:
            return _fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise ValueError(
                "Could not decrypt note content — it may predate encryption "
                "support, or NOTES_ENCRYPTION_PASSWORD doesn't match the key "
                "it was encrypted with. Run scripts/migrate_encrypt_notes.py "
                "to migrate pre-existing plaintext rows."
            ) from exc


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    notes = db.relationship("Note", backref="author", lazy=True)

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(EncryptedText, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
