import builtins
import base64
import ast
import datetime as dt
import hashlib
import importlib
import inspect
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
from functions import utils
from functions import region_parser


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
                depends_on_run_id INTEGER,
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

            CREATE TABLE IF NOT EXISTS run_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                depends_on_run_id INTEGER NOT NULL,
                alias TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(run_id, depends_on_run_id)
            );
            """
        )
        run_columns = {
            row["name"]
            for row in db.execute("PRAGMA table_info(runs)").fetchall()
        }
        if "depends_on_run_id" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN depends_on_run_id INTEGER")
        db.execute(
            """
            INSERT OR IGNORE INTO run_dependencies (run_id, depends_on_run_id, alias, created_at)
            SELECT id, depends_on_run_id, NULL, created_at
            FROM runs
            WHERE depends_on_run_id IS NOT NULL
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
        def read_module_metadata(module_file: Path, category: str, name: str):
            default_metadata = {
                "name": name,
                "display_name": name.replace("_", " ").title(),
                "category": category,
                "description": f"Run module {name}.",
                "requires_region": False,
                "inputs": [],
                "output_type": "json",
                "risk_level": "low",
                "result_view": "default",
                "dependencies": [],
                "dependency_mode": "single",
                "dependency_payload_key": None,
            }
            try:
                source = module_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
                for node in tree.body:
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == "MODULE_METADATA":
                                value = ast.literal_eval(node.value)
                                if isinstance(value, dict):
                                    default_metadata.update(value)
                                    return default_metadata
            except Exception:
                return default_metadata
            return default_metadata

        catalog = []
        for category in sorted(MODULES_DIR.iterdir()):
            if not category.is_dir() or category.name.startswith("__"):
                continue
            for module_file in sorted(category.glob("*.py")):
                if module_file.stem.startswith("__"):
                    continue
                metadata = read_module_metadata(module_file, category.name, module_file.stem)
                catalog.append(
                    {
                        "category": category.name,
                        "name": module_file.stem,
                        "path": f"{category.name}/{module_file.stem}",
                        "metadata": metadata,
                    }
                )
        return catalog

    def _parse_json_or_empty(value):
        if not value:
            return {}
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _present_default(run_row, result_obj):
        data = result_obj.get("data", {}) if isinstance(result_obj, dict) else {}
        errors = result_obj.get("errors", []) if isinstance(result_obj, dict) else []
        return {
            "title": f"{run_row['module_category']}/{run_row['module_name']}",
            "highlights": [
                {"label": "Status", "value": run_row["status"]},
                {"label": "Errors", "value": len(errors)},
            ],
            "sections": [
                {
                    "title": "Data Overview",
                    "columns": ["Key", "Value"],
                    "rows": [{"Key": k, "Value": str(v)} for k, v in data.items()][:50],
                }
            ],
        }

    def _present_ec2_enumerate_instances(run_row, result_obj):
        data = result_obj.get("data", {}) if isinstance(result_obj, dict) else {}
        regions = data.get("regions", {}) if isinstance(data, dict) else {}
        rows = []
        for region, instances in regions.items():
            rows.append({"Region": region, "Instances": len(instances or [])})
        rows.sort(key=lambda r: r["Region"])
        return {
            "title": "EC2 Instance Inventory",
            "highlights": [
                {"label": "Total Instances", "value": data.get("total_instances", 0)},
                {"label": "Regions Scanned", "value": len(regions)},
                {"label": "Regions With Instances", "value": sum(1 for r in rows if r["Instances"] > 0)},
            ],
            "sections": [
                {
                    "title": "Instances by Region",
                    "columns": ["Region", "Instances"],
                    "rows": rows,
                }
            ],
        }

    def _present_ec2_enumerate_user_data(run_row, result_obj):
        data = result_obj.get("data", {}) if isinstance(result_obj, dict) else {}
        regions = data.get("regions", {}) if isinstance(data, dict) else {}
        rows = []
        for region, details in regions.items():
            region_count = 0
            user_data_count = 0
            if isinstance(details, dict):
                region_count = details.get("count_instances", 0)
                user_data_count = details.get("count_with_user_data", 0)
            rows.append(
                {
                    "Region": region,
                    "Instances": region_count,
                    "WithUserData": user_data_count,
                }
            )
        rows.sort(key=lambda r: r["Region"])
        return {
            "title": "EC2 User Data Coverage",
            "highlights": [
                {"label": "Total Instances", "value": data.get("total_instances", 0)},
                {"label": "With User Data", "value": data.get("total_with_user_data", 0)},
                {"label": "Regions Scanned", "value": len(regions)},
            ],
            "sections": [
                {
                    "title": "User Data by Region",
                    "columns": ["Region", "Instances", "WithUserData"],
                    "rows": rows,
                }
            ],
        }

    def _present_iam_enumerate_roles(run_row, result_obj):
        data = result_obj.get("data", {}) if isinstance(result_obj, dict) else {}
        roles = data.get("roles", []) if isinstance(data, dict) else []
        rows = []
        for role in roles[:200]:
            rows.append(
                {
                    "RoleName": role.get("role_name"),
                    "Path": role.get("path"),
                    "Arn": role.get("arn"),
                }
            )
        return {
            "title": "IAM Roles Inventory",
            "highlights": [
                {"label": "Role Count", "value": data.get("count", len(roles))},
            ],
            "sections": [
                {
                    "title": "Roles",
                    "columns": ["RoleName", "Path", "Arn"],
                    "rows": rows,
                }
            ],
        }

    def _present_iam_role_trust(run_row, result_obj):
        data = result_obj.get("data", {}) if isinstance(result_obj, dict) else {}
        roles = data.get("roles", []) if isinstance(data, dict) else []
        rows = []
        for role in roles[:300]:
            entities = role.get("trusted_entities", [])
            sample = ", ".join(
                f"{e.get('principal_type')}:{e.get('value')}" for e in entities[:3]
            )
            rows.append(
                {
                    "RoleName": role.get("role_name"),
                    "TrustedEntities": role.get("trusted_entity_count", 0),
                    "Sample": sample or "-",
                }
            )
        return {
            "title": "IAM Role Trust Relationships",
            "highlights": [
                {"label": "Roles Analyzed", "value": data.get("count_roles", len(roles))},
                {"label": "Total Trusted Entities", "value": data.get("count_trusted_entities", 0)},
                {"label": "Dependency Used", "value": "Yes" if data.get("dependency_used") else "No"},
            ],
            "sections": [
                {
                    "title": "Role Trust Summary",
                    "columns": ["RoleName", "TrustedEntities", "Sample"],
                    "rows": rows,
                }
            ],
        }

    def _build_presenter(run_row, result_obj, result_view=None):
        module_path = f"{run_row['module_category']}/{run_row['module_name']}"
        presenters = {
            "ec2_enumerate_instances": _present_ec2_enumerate_instances,
            "ec2_enumerate_user_data": _present_ec2_enumerate_user_data,
            "iam_enumerate_roles": _present_iam_enumerate_roles,
            "iam_enumerate_role_trust_policy": _present_iam_role_trust,
            "enumeration/ec2_enumerate_instances": _present_ec2_enumerate_instances,
            "enumeration/ec2_enumerate_user_data": _present_ec2_enumerate_user_data,
            "enumeration/iam_enumerate_roles": _present_iam_enumerate_roles,
            "enumeration/iam_enumerate_role_trust_policy": _present_iam_role_trust,
        }
        presenter = presenters.get(result_view) or presenters.get(module_path) or _present_default
        try:
            return presenter(run_row, result_obj)
        except Exception:
            return _present_default(run_row, result_obj)

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

            result_json = None
            error_text = None
            status = "completed"

            input_values = json.loads(run["input_values_json"] or "[]")
            input_iter = iter(input_values)
            original_input = builtins.input
            original_print = builtins.print

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
                module_metadata = getattr(module, "MODULE_METADATA", {}) or {}

                dependency_rows = db.execute(
                    """
                    SELECT
                        d.depends_on_run_id,
                        r.module_category,
                        r.module_name,
                        r.status,
                        r.result_json
                    FROM run_dependencies d
                    JOIN runs r ON r.id = d.depends_on_run_id
                    WHERE d.run_id = ?
                    ORDER BY d.depends_on_run_id DESC
                    """,
                    (run_id,),
                ).fetchall()
                if not dependency_rows and run["depends_on_run_id"]:
                    dependency_rows = db.execute(
                        """
                        SELECT
                            ? AS depends_on_run_id,
                            r.module_category,
                            r.module_name,
                            r.status,
                            r.result_json
                        FROM runs r
                        WHERE r.id = ?
                        """,
                        (run["depends_on_run_id"], run["depends_on_run_id"]),
                    ).fetchall()

                dependency_context = {"by_run_id": {}, "by_module": {}}
                for dep in dependency_rows:
                    parsed_result = {}
                    try:
                        parsed_result = json.loads(dep["result_json"] or "{}")
                    except Exception:
                        parsed_result = {}
                    dep_module_path = f"{dep['module_category']}/{dep['module_name']}"
                    dep_entry = {
                        "run_id": dep["depends_on_run_id"],
                        "module_path": dep_module_path,
                        "status": dep["status"],
                        "result": parsed_result,
                        "data": parsed_result.get("data", {}) if isinstance(parsed_result, dict) else {},
                    }
                    dependency_context["by_run_id"][str(dep["depends_on_run_id"])] = dep_entry
                    dependency_context["by_module"].setdefault(dep_module_path, []).append(dep_entry)

                builtins.input = fake_input
                builtins.print = lambda *args, **kwargs: None
                main_signature = inspect.signature(module.main)
                accepts_context = len(main_signature.parameters) >= 3
                if accepts_context:
                    result = module.main(
                        botoconfig,
                        session_obj,
                        {"dependency_context": dependency_context, "module_metadata": module_metadata},
                    )
                else:
                    result = module.main(botoconfig, session_obj)
                normalized_result = utils.normalize_module_output(result)
                if normalized_result.get("status") == "error" and normalized_result.get("errors"):
                    status = "failed"
                    error_text = "\n".join(normalized_result.get("errors", []))
                result_json = json.dumps(normalized_result, default=str, indent=2)
            except Exception:
                status = "failed"
                tb = traceback.format_exc()
                error_text = tb
                result_json = json.dumps(
                    utils.module_result(
                        status="error",
                        errors=["Module execution failed"],
                        data={"traceback": tb},
                    ),
                    default=str,
                    indent=2,
                )
            finally:
                builtins.input = original_input
                builtins.print = original_print

            db.execute(
                """
                UPDATE runs
                SET status = ?, stdout = ?, stderr = ?, result_json = ?, error_text = ?, finished_at = ?
                WHERE id = ?
                """,
                (status, None, None, result_json, error_text, _now(), run_id),
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
        regions = region_parser.get_regions()
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
        categories = sorted({m["category"] for m in modules})
        dependency_runs = db.execute(
            """
            SELECT
                r.id,
                r.created_at,
                r.credential_id,
                r.module_category,
                r.module_name,
                c.name AS credential_name
            FROM runs r
            JOIN credentials c ON c.id = r.credential_id
            WHERE r.user_id = ?
              AND r.status = 'completed'
            ORDER BY r.id DESC
            LIMIT 300
            """,
            (session["user_id"],),
        ).fetchall()
        return render_template(
            "dashboard.html",
            modules=modules,
            categories=categories,
            credentials=credentials,
            runs=runs,
            regions=regions,
            dependency_runs=dependency_runs,
        )

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
        selected_region = request.form.get("selected_region", "").strip()
        depends_on_run_ids = [v.strip() for v in request.form.getlist("depends_on_run_ids") if v.strip()]

        if "/" not in module_path:
            flash("Invalid module selection.", "error")
            return redirect(url_for("dashboard"))
        if not credential_id:
            flash("Select a credential first.", "error")
            return redirect(url_for("dashboard"))

        category, name = module_path.split("/", 1)
        input_values = [line for line in input_values_text.splitlines() if line.strip()]
        module_key = f"{category}/{name}"
        selected_module = next((m for m in get_modules_catalog() if m["path"] == module_key), None)
        if not selected_module:
            flash("Selected module is invalid or no longer available.", "error")
            return redirect(url_for("dashboard"))
        module_metadata = selected_module.get("metadata", {}) or {}
        module_inputs_meta = module_metadata.get("inputs", []) or []
        accepts_region_input = any(
            isinstance(inp, dict) and inp.get("name") == "region"
            for inp in module_inputs_meta
        )
        if module_metadata.get("requires_region") and not selected_region:
            flash("This module requires an AWS region. Please select one before queueing the run.", "error")
            return redirect(url_for("dashboard"))
        if selected_region and (module_metadata.get("requires_region") or accepts_region_input):
            input_values = [selected_region] + input_values

        module_dependencies = module_metadata.get("dependencies", []) or []
        if not isinstance(module_dependencies, list):
            module_dependencies = []
        dependency_mode = module_metadata.get("dependency_mode", "single")
        required_dependency_count = len(module_dependencies)

        dependency_id_values = []
        if module_dependencies:
            if not depends_on_run_ids:
                flash("This module requires dependency runs before queueing.", "error")
                return redirect(url_for("dashboard"))
            if dependency_mode == "single" and len(depends_on_run_ids) != 1:
                flash("Select exactly one dependency run for this module.", "error")
                return redirect(url_for("dashboard"))
            if dependency_mode == "multiple" and len(depends_on_run_ids) < required_dependency_count:
                flash("Select all required dependency runs for this module.", "error")
                return redirect(url_for("dashboard"))
            try:
                dependency_id_values = [int(dep_id) for dep_id in depends_on_run_ids]
            except ValueError:
                flash("Invalid dependency run selected.", "error")
                return redirect(url_for("dashboard"))

            db = get_db()
            placeholders = ",".join(["?"] * len(dependency_id_values))
            dependency_rows = db.execute(
                f"""
                SELECT id, status, module_category, module_name, credential_id, user_id
                FROM runs
                WHERE id IN ({placeholders})
                """,
                tuple(dependency_id_values),
            ).fetchall()
            dependency_lookup = {int(row["id"]): row for row in dependency_rows}
            selected_dependency_modules = set()
            for dependency_id in dependency_id_values:
                dependency_run = dependency_lookup.get(int(dependency_id))
                if not dependency_run:
                    flash(f"Dependency run #{dependency_id} not found.", "error")
                    return redirect(url_for("dashboard"))
                if int(dependency_run["user_id"]) != int(session["user_id"]):
                    flash(f"Dependency run #{dependency_id} does not belong to current operator.", "error")
                    return redirect(url_for("dashboard"))
                if dependency_run["status"] != "completed":
                    flash(f"Dependency run #{dependency_id} must be completed.", "error")
                    return redirect(url_for("dashboard"))
                dep_module_path = f"{dependency_run['module_category']}/{dependency_run['module_name']}"
                if dep_module_path not in module_dependencies:
                    flash(f"Dependency run #{dependency_id} is not valid for this module.", "error")
                    return redirect(url_for("dashboard"))
                selected_dependency_modules.add(dep_module_path)
                if int(dependency_run["credential_id"]) != int(credential_id):
                    flash(f"Dependency run #{dependency_id} credential must match selected credential.", "error")
                    return redirect(url_for("dashboard"))
            if dependency_mode == "multiple":
                missing_dependencies = [dep for dep in module_dependencies if dep not in selected_dependency_modules]
                if missing_dependencies:
                    flash("Selected dependency runs do not cover all required dependency modules.", "error")
                    return redirect(url_for("dashboard"))

        db = get_db()
        run_cursor = db.execute(
            """
            INSERT INTO runs
            (user_id, module_category, module_name, credential_id, depends_on_run_id, input_values_json, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                category,
                name,
                int(credential_id),
                dependency_id_values[0] if dependency_id_values else None,
                json.dumps(input_values),
                "queued",
                _now(),
            ),
        )
        db.commit()
        run_id = run_cursor.lastrowid
        if dependency_id_values:
            for dependency_id in dependency_id_values:
                db.execute(
                    """
                    INSERT OR IGNORE INTO run_dependencies (run_id, depends_on_run_id, alias, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (run_id, dependency_id, None, _now()),
                )
            db.commit()

        thread = threading.Thread(target=run_module_job, args=(run_id,), daemon=True)
        app.config["RUNNER_THREADS"][run_id] = thread
        thread.start()

        flash(f"Run #{run_id} queued.", "success")
        return redirect(url_for("dashboard"))

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
        dependencies = db.execute(
            """
            SELECT
                r.id,
                r.module_category,
                r.module_name,
                r.status
            FROM run_dependencies d
            JOIN runs r ON r.id = d.depends_on_run_id
            WHERE d.run_id = ?
            ORDER BY r.id DESC
            """,
            (run_id,),
        ).fetchall()
        dependents = db.execute(
            """
            SELECT
                r.id,
                r.module_category,
                r.module_name,
                r.status
            FROM run_dependencies d
            JOIN runs r ON r.id = d.run_id
            WHERE d.depends_on_run_id = ?
            ORDER BY r.id DESC
            """,
            (run_id,),
        ).fetchall()
        result_obj = _parse_json_or_empty(run["result_json"])
        module_path = f"{run['module_category']}/{run['module_name']}"
        modules_catalog = get_modules_catalog()
        selected_module = next((m for m in modules_catalog if m["path"] == module_path), None)
        result_view = None
        if selected_module and isinstance(selected_module.get("metadata"), dict):
            result_view = selected_module["metadata"].get("result_view")
        presenter = _build_presenter(run, result_obj, result_view=result_view)
        return render_template(
            "run_detail.html",
            run=run,
            dependencies=dependencies,
            dependents=dependents,
            result_obj=result_obj,
            presenter=presenter,
        )

    @app.route("/runs/<int:run_id>/delete", methods=["POST"])
    @login_required
    def run_delete(run_id):
        db = get_db()
        db.execute("DELETE FROM run_dependencies WHERE run_id = ? OR depends_on_run_id = ?", (run_id, run_id))
        db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        db.commit()
        flash(f"Run #{run_id} deleted.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/runs/clear", methods=["POST"])
    @login_required
    def runs_clear():
        db = get_db()
        in_progress = db.execute(
            "SELECT COUNT(1) AS c FROM runs WHERE status IN ('queued', 'running')"
        ).fetchone()
        if in_progress and in_progress["c"] > 0:
            flash("Cannot clear runs while executions are queued or running.", "error")
            return redirect(url_for("dashboard"))

        deleted = db.execute("SELECT COUNT(1) AS c FROM runs").fetchone()
        db.execute("DELETE FROM run_dependencies")
        db.execute("DELETE FROM runs")
        db.commit()
        db.execute("VACUUM")
        db.commit()
        flash(f"Cleared {deleted['c']} run(s) and compacted the database.", "success")
        return redirect(url_for("dashboard"))

    with app.app_context():
        init_db()
        ensure_admin()

    return app


app = create_app()
