import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, select, text

from models import EncryptedText, _fernet


def _notes_table(metadata):
    return Table(
        "notes",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("content", EncryptedText),
    )


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:")
    _notes_table(MetaData()).metadata.create_all(engine)
    return engine


def test_content_round_trips_through_encryption(engine):
    metadata = MetaData()
    notes = _notes_table(metadata)

    with engine.begin() as conn:
        conn.execute(notes.insert().values(id=1, content="secret payload"))

    with engine.connect() as conn:
        result = conn.execute(select(notes.c.content).where(notes.c.id == 1)).scalar_one()

    assert result == "secret payload"


def test_content_is_ciphertext_at_rest(engine):
    metadata = MetaData()
    notes = _notes_table(metadata)

    with engine.begin() as conn:
        conn.execute(notes.insert().values(id=1, content="secret payload"))

    with engine.connect() as conn:
        raw = conn.execute(text("SELECT content FROM notes WHERE id = 1")).scalar_one()

    assert raw != "secret payload"
    assert _fernet.decrypt(raw.encode()).decode() == "secret payload"


def test_legacy_plaintext_content_raises_clear_error(engine):
    metadata = MetaData()
    notes = _notes_table(metadata)

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO notes (id, content) VALUES (1, 'plain legacy text')"))

    with engine.connect() as conn:
        with pytest.raises(ValueError, match="migrate_encrypt_notes"):
            conn.execute(select(notes.c.content).where(notes.c.id == 1)).scalar_one()
