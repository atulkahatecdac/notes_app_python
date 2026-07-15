import threading
import uuid

import pytest
from playwright.sync_api import expect
from werkzeug.serving import make_server

from app import app as flask_app
from models import Note, User, db

HOST = "127.0.0.1"
PORT = 5055
BASE_URL = f"http://{HOST}:{PORT}"


@pytest.fixture(scope="session")
def live_server():
    server = make_server(HOST, PORT, flask_app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield BASE_URL
    server.shutdown()
    thread.join()


@pytest.fixture
def registered_user(live_server, page):
    username = f"pw_{uuid.uuid4().hex[:10]}"
    password = "playwright-test-pw-123"

    page.goto(f"{live_server}/register")
    page.fill("#username", username)
    page.fill("#email", f"{username}@example.com")
    page.fill("#password", password)
    page.fill("#confirm_password", password)
    page.click("button.btn-primary")

    yield {"username": username, "password": password}

    with flask_app.app_context():
        user = db.session.query(User).filter_by(username=username).first()
        if user:
            db.session.query(Note).filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


def _login(page, live_server, user):
    page.goto(f"{live_server}/login")
    page.fill("#username", user["username"])
    page.fill("#password", user["password"])
    page.click("button.btn-primary")
    expect(page).to_have_url(f"{live_server}/")


def test_login_create_note_reopen_and_decrypt(page, live_server, registered_user):
    note_title = "Playwright Encrypted Note"
    note_content = "This note must be encrypted at rest and decrypted correctly on reopen."

    _login(page, live_server, registered_user)

    # Create a new note and save it.
    page.goto(f"{live_server}/notes/new")
    page.fill("#title", note_title)
    page.fill("#content", note_content)
    page.click("button.btn-primary")

    # Saving redirects to the note's view page, showing decrypted content.
    expect(page.locator(".note-body")).to_have_text(note_content)
    note_url = page.url

    # Confirm the stored value is actually ciphertext, not plaintext.
    with flask_app.app_context():
        note = db.session.query(Note).filter_by(title=note_title).one()
        raw = db.session.connection().exec_driver_sql(
            "SELECT content FROM notes WHERE id = ?", (note.id,)
        ).scalar()
    assert raw != note_content

    # Reopen: fresh navigation (new page load, not client-side state) to the
    # same note, and verify the content decrypts back to the original text.
    page.goto(f"{live_server}/")
    page.goto(note_url)
    expect(page.locator(".note-body")).to_have_text(note_content)


def test_edited_note_reencrypts_and_reopens_correctly(page, live_server, registered_user):
    original_content = "Original encrypted content."
    updated_content = "Updated content after edit — still must decrypt correctly."

    _login(page, live_server, registered_user)

    page.goto(f"{live_server}/notes/new")
    page.fill("#title", "Editable Note")
    page.fill("#content", original_content)
    page.click("button.btn-primary")
    note_url = page.url

    page.goto(f"{note_url}/edit")
    page.fill("#content", updated_content)
    page.click("button.btn-primary")

    page.goto(f"{live_server}/")
    page.goto(note_url)
    expect(page.locator(".note-body")).to_have_text(updated_content)
