from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_required, login_user, logout_user, current_user

from models import db, User, Note, utcnow

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///notes.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


with app.app_context():
    db.create_all()


# --- Auth routes ---

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm = request.form["confirm_password"]
        if password != confirm:
            flash("Passwords do not match.", "error")
        elif User.query.filter_by(username=username).first():
            flash("Username already taken.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Account created — please log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# --- Note routes ---

@app.route("/")
@login_required
def index():
    query = request.args.get("q", "").strip()
    if query:
        # Content is encrypted non-deterministically, so it can't be
        # searched in SQL — fetch and decrypt, then filter in Python.
        candidates = (
            Note.query.filter(Note.user_id == current_user.id)
            .order_by(Note.created_at.desc())
            .all()
        )
        needle = query.lower()
        notes = [n for n in candidates if needle in n.title.lower() or needle in n.content.lower()]
    else:
        notes = (
            db.session.query(Note.id, Note.title, Note.created_at)
            .filter(Note.user_id == current_user.id)
            .order_by(Note.created_at.desc())
            .all()
        )
    return render_template("index.html", notes=notes, query=query)


@app.route("/notes/new", methods=["GET", "POST"])
@login_required
def new_note():
    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        if not title or not content:
            flash("Title and content are required.", "error")
        else:
            note = Note(title=title, content=content, user_id=current_user.id)
            db.session.add(note)
            db.session.commit()
            return redirect(url_for("view_note", note_id=note.id))
    return render_template("new.html")


def _get_owned_note(note_id):
    note = db.get_or_404(Note, note_id)
    if note.user_id != current_user.id:
        abort(403)
    return note


@app.route("/notes/<int:note_id>")
@login_required
def view_note(note_id):
    note = _get_owned_note(note_id)
    return render_template("view.html", note=note)


@app.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    note = _get_owned_note(note_id)
    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        if not title or not content:
            flash("Title and content are required.", "error")
        else:
            note.title = title
            note.content = content
            note.updated_at = utcnow()
            db.session.commit()
            return redirect(url_for("view_note", note_id=note.id))
    return render_template("edit.html", note=note)


@app.route("/notes/<int:note_id>/delete", methods=["GET", "POST"])
@login_required
def delete_note(note_id):
    note = _get_owned_note(note_id)
    if request.method == "POST":
        db.session.delete(note)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("delete.html", note=note)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
