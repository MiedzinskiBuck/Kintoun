import builtins
import base64
import contextlib
import datetime as dt
import hashlib
import importlib
import io
import json
import os
import sqlite3
import threading
import traceback
from functools import wraps
from pathlib import Path

from botocore.config import Config
from cryptography.fernet import Fernet
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from functions import credential_handler


BASE_DIR = Path(__file__).resolve().parents[1]
MODULES_DIR = BASE_DIR / "modules"


def _build_fernet(secret_key: str) -> Fernet:
    key_material = hashlib.sha256(secret_key.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(key_material)
    return Fernet(fernet_key)


def create_app():
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )
    app.config["SECRET_KEY"] = os.getenv("KINTOUN_WEB_SECRET", "kintoun-dev-secret-change-me")
    app.config["DB_PATH"] = os.getenv("KINTOUN_WEB_DB", str(BASE_DIR / "kintoun_web.db"))
    app.config["FERNET"] = _build_fernet(os.getenv("KINTOUN_CRED_KEY", app.config["SECRET_KEY"]))
    app.config["RUNNER_THREADS"] = {}

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"], check_same_thread=False)
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                profile_enc TEXT,
                access_key_enc TEXT,
                secret_key_enc TEXT,
                session_token_enc TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                module_category TEXT NOT NULL,
                module_name TEXT NOT NULL,
                credential_id INTEGER NOT NULL,
                input_values_json TEXT,
                status TEXT NOT NULL,
                stdout TEXT,
                stderr TEXT,
                result_json TEXT,
                error_text TEXT,
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(credential_id) REFERENCES credentials(id)
            );
            """
        )
        db.commit()

    def ensure_admin():
        db = get_db()
        username = os.getenv("KINTOUN_ADMIN_USER", "admin")
        password = os.getenv("KINTOUN_ADMIN_PASS", "admin123!")
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), _now()),
            )
            db.commit()

    def _now():
        return dt.datetime.now(dt.timezone.utc).isoformat()

    def encrypt(value):
        if value is None or value == "":
            return None
        return app.config["FERNET"].encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(value):
        if not value:
            return None
        return app.config["FERNET"].decrypt(value.encode("utf-8")).decode("utf-8")

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            return fn(*args, **kwargs)

        return wrapper

    def get_modules_catalog():
        catalog = []
        for category in sorted(MODULES_DIR.iterdir()):
            if not category.is_dir() or category.name.startswith("__"):
                continue
            for module_file in sorted(category.glob("*.py")):
                if module_file.stem.startswith("__"):
                    continue
                catalog.append(
                    {
                        "category": category.name,
                        "name": module_file.stem,
                        "path": f"{category.name}/{module_file.stem}",
                    }
                )
        return catalog

    def run_module_job(run_id: int):
        with app.app_context():
            db = sqlite3.connect(app.config["DB_PATH"], check_same_thread=False)
            db.row_factory = sqlite3.Row
            db.execute(
                "UPDATE runs SET status = ?, started_at = ? WHERE id = ?",
                ("running", _now(), run_id),
            )
            db.commit()

            run = db.execute(
                """
                SELECT r.*, c.profile_enc, c.access_key_enc, c.secret_key_enc, c.session_token_enc
                FROM runs r
                JOIN credentials c ON c.id = r.credential_id
                WHERE r.id = ?
                """,
                (run_id,),
            ).fetchone()

            stdout_buf = io.StringIO()
            stderr_buf = io.StringIO()
            result_json = None
            error_text = None
            status = "completed"

            input_values = json.loads(run["input_values_json"] or "[]")
            input_iter = iter(input_values)
            original_input = builtins.input

            def fake_input(prompt=""):
                try:
                    return next(input_iter)
                except StopIteration:
                    raise RuntimeError(
                        f"Module requested additional input but none was provided. Last prompt: {prompt}"
                    )

            try:
                credentials = {
                    "profile": decrypt(run["profile_enc"]),
                    "aws_access_key_id": decrypt(run["access_key_enc"]),
                    "aws_secret_access_key": decrypt(run["secret_key_enc"]),
                    "aws_session_token": decrypt(run["session_token_enc"]),
                }
                session_obj = credential_handler.Credential(credentials).session
                botoconfig = Config(user_agent="kintoun-web")

                module_path = f"modules.{run['module_category']}.{run['module_name']}"
                module = importlib.import_module(module_path)

                builtins.input = fake_input
                with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                    result = module.main(botoconfig, session_obj)

                result_json = json.dumps(result, default=str, indent=2)
            except Exception:
                status = "failed"
                error_text = traceback.format_exc()
            finally:
                builtins.input = original_input

            db.execute(
                """
                UPDATE runs
                SET status = ?, stdout = ?, stderr = ?, result_json = ?, error_text = ?, finished_at = ?
                WHERE id = ?
                """,
                (status, stdout_buf.getvalue(), stderr_buf.getvalue(), result_json, error_text, _now(), run_id),
            )
            db.commit()
            db.close()

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def dashboard():
        db = get_db()
        credentials = db.execute("SELECT id, name, created_at FROM credentials ORDER BY name").fetchall()
        runs = db.execute(
            """
            SELECT
                r.id,
                r.module_category,
                r.module_name,
                r.status,
                r.created_at,
                r.started_at,
                r.finished_at,
                r.error_text,
                r.stderr,
                c.name AS credential_name
            FROM runs r
            JOIN credentials c ON c.id = r.credential_id
            ORDER BY r.id DESC
            LIMIT 25
            """
        ).fetchall()
        modules = get_modules_catalog()
        return render_template("dashboard.html", modules=modules, credentials=credentials, runs=runs)

    @app.route("/credentials")
    @login_required
    def credentials_list():
        db = get_db()
        rows = db.execute("SELECT id, name, created_at, updated_at FROM credentials ORDER BY name").fetchall()
        return render_template("credentials.html", credentials=rows)

    @app.route("/credentials/new", methods=["GET", "POST"])
    @login_required
    def credentials_new():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Credential name is required.", "error")
                return render_template("credential_form.html", credential=None)

            db = get_db()
            try:
                db.execute(
                    """
                    INSERT INTO credentials
                    (name, profile_enc, access_key_enc, secret_key_enc, session_token_enc, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        encrypt(request.form.get("profile", "").strip()),
                        encrypt(request.form.get("access_key", "").strip()),
                        encrypt(request.form.get("secret_key", "").strip()),
                        encrypt(request.form.get("session_token", "").strip()),
                        _now(),
                        _now(),
                    ),
                )
                db.commit()
                flash("Credential saved.", "success")
                return redirect(url_for("credentials_list"))
            except sqlite3.IntegrityError:
                flash("Credential name already exists.", "error")
        return render_template("credential_form.html", credential=None)

    @app.route("/credentials/<int:credential_id>/edit", methods=["GET", "POST"])
    @login_required
    def credentials_edit(credential_id):
        db = get_db()
        row = db.execute("SELECT * FROM credentials WHERE id = ?", (credential_id,)).fetchone()
        if not row:
            flash("Credential not found.", "error")
            return redirect(url_for("credentials_list"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Credential name is required.", "error")
                return redirect(url_for("credentials_edit", credential_id=credential_id))
            try:
                db.execute(
                    """
                    UPDATE credentials
                    SET name = ?, profile_enc = ?, access_key_enc = ?, secret_key_enc = ?, session_token_enc = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        encrypt(request.form.get("profile", "").strip()),
                        encrypt(request.form.get("access_key", "").strip()),
                        encrypt(request.form.get("secret_key", "").strip()),
                        encrypt(request.form.get("session_token", "").strip()),
                        _now(),
                        credential_id,
                    ),
                )
                db.commit()
                flash("Credential updated.", "success")
                return redirect(url_for("credentials_list"))
            except sqlite3.IntegrityError:
                flash("Credential name already exists.", "error")

        credential = {
            "id": row["id"],
            "name": row["name"],
            "profile": decrypt(row["profile_enc"]) or "",
            "access_key": decrypt(row["access_key_enc"]) or "",
            "secret_key": decrypt(row["secret_key_enc"]) or "",
            "session_token": decrypt(row["session_token_enc"]) or "",
        }
        return render_template("credential_form.html", credential=credential)

    @app.route("/credentials/<int:credential_id>/delete", methods=["POST"])
    @login_required
    def credentials_delete(credential_id):
        db = get_db()
        db.execute("DELETE FROM credentials WHERE id = ?", (credential_id,))
        db.commit()
        flash("Credential deleted.", "success")
        return redirect(url_for("credentials_list"))

    @app.route("/runs/new", methods=["POST"])
    @login_required
    def runs_new():
        module_path = request.form.get("module_path", "").strip()
        credential_id = request.form.get("credential_id", "").strip()
        input_values_text = request.form.get("input_values", "").strip()

        if "/" not in module_path:
            flash("Invalid module selection.", "error")
            return redirect(url_for("dashboard"))
        if not credential_id:
            flash("Select a credential first.", "error")
            return redirect(url_for("dashboard"))

        category, name = module_path.split("/", 1)
        input_values = [line for line in input_values_text.splitlines() if line.strip()]

        db = get_db()
        run_cursor = db.execute(
            """
            INSERT INTO runs
            (user_id, module_category, module_name, credential_id, input_values_json, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                category,
                name,
                int(credential_id),
                json.dumps(input_values),
                "queued",
                _now(),
            ),
        )
        db.commit()
        run_id = run_cursor.lastrowid

        thread = threading.Thread(target=run_module_job, args=(run_id,), daemon=True)
        app.config["RUNNER_THREADS"][run_id] = thread
        thread.start()

        flash(f"Run #{run_id} queued.", "success")
        return redirect(url_for("run_detail", run_id=run_id))

    @app.route("/runs/<int:run_id>")
    @login_required
    def run_detail(run_id):
        db = get_db()
        run = db.execute(
            """
            SELECT r.*, c.name AS credential_name, u.username
            FROM runs r
            JOIN credentials c ON c.id = r.credential_id
            JOIN users u ON u.id = r.user_id
            WHERE r.id = ?
            """,
            (run_id,),
        ).fetchone()
        if not run:
            flash("Run not found.", "error")
            return redirect(url_for("dashboard"))
        return render_template("run_detail.html", run=run)

    with app.app_context():
        init_db()
        ensure_admin()

    return app


app = create_app()
