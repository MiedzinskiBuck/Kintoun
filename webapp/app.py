import builtins
import base64
import ast
import datetime as dt
import hashlib
import importlib
import inspect
import json
import os
import select
import socket
import sqlite3
import threading
import time
import traceback
import urllib.parse
import urllib.request
from functools import wraps
from pathlib import Path

import botocore.client
from botocore.config import Config
from cryptography.fernet import Fernet
from flask import Flask, Response, flash, g, redirect, render_template, request, session, url_for
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
    app.config["WORKER_CONCURRENCY"] = int(os.getenv("KINTOUN_WORKER_CONCURRENCY", "2"))
    app.config["DEFAULT_TIMEOUT_SECONDS"] = int(os.getenv("KINTOUN_DEFAULT_TIMEOUT_SECONDS", "900"))
    app.config["DEFAULT_MAX_API_CALLS"] = int(os.getenv("KINTOUN_DEFAULT_MAX_API_CALLS", "3000"))

    class RunCancelledError(Exception):
        pass

    class RunTimeoutError(Exception):
        pass

    class RunApiLimitError(Exception):
        pass

    guard_state = threading.local()

    def install_api_guard():
        original_make_api_call = botocore.client.BaseClient._make_api_call
        if getattr(original_make_api_call, "_kintoun_guarded", False):
            return

        def guarded_make_api_call(client, operation_name, api_params):
            state = getattr(guard_state, "state", None)
            if state:
                if state["is_cancel_requested"]():
                    raise RunCancelledError("Run cancelled by operator.")
                if time.monotonic() > state["deadline"]:
                    raise RunTimeoutError(
                        f"Run exceeded timeout of {state['timeout_seconds']} seconds."
                    )
                state["api_calls"] += 1
                if state["api_calls"] > state["max_api_calls"]:
                    raise RunApiLimitError(
                        f"Run exceeded API call limit of {state['max_api_calls']}."
                    )
            return original_make_api_call(client, operation_name, api_params)

        guarded_make_api_call._kintoun_guarded = True
        botocore.client.BaseClient._make_api_call = guarded_make_api_call

    install_api_guard()

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
                role TEXT NOT NULL DEFAULT 'operator',
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                owner_user_id INTEGER,
                profile_enc TEXT,
                access_key_enc TEXT,
                secret_key_enc TEXT,
                session_token_enc TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                credential_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, credential_id)
            );

            CREATE TABLE IF NOT EXISTS user_active_credentials (
                user_id INTEGER PRIMARY KEY,
                credential_id INTEGER NOT NULL,
                source TEXT,
                source_run_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_tunnels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                scheme TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, name)
            );

            CREATE TABLE IF NOT EXISTS user_network_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                proxy_url TEXT,
                ca_bundle_path TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, name)
            );

            CREATE TABLE IF NOT EXISTS user_tunnel_chains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, name)
            );

            CREATE TABLE IF NOT EXISTS user_tunnel_chain_hops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                hop_order INTEGER NOT NULL,
                tunnel_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(chain_id, hop_order)
            );

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                module_category TEXT NOT NULL,
                module_name TEXT NOT NULL,
                credential_id INTEGER NOT NULL,
                tunnel_id INTEGER,
                tunnel_label TEXT,
                tunnel_url TEXT,
                network_profile_id INTEGER,
                network_profile_label TEXT,
                network_proxy_url TEXT,
                network_ca_bundle_path TEXT,
                depends_on_run_id INTEGER,
                cancel_requested INTEGER NOT NULL DEFAULT 0,
                canceled_at TEXT,
                api_calls INTEGER,
                timeout_seconds INTEGER,
                max_api_calls INTEGER,
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

            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                credential_id INTEGER NOT NULL,
                module_path TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                description TEXT,
                details_json TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        run_columns = {
            row["name"]
            for row in db.execute("PRAGMA table_info(runs)").fetchall()
        }
        user_columns = {
            row["name"]
            for row in db.execute("PRAGMA table_info(users)").fetchall()
        }
        credential_columns = {
            row["name"]
            for row in db.execute("PRAGMA table_info(credentials)").fetchall()
        }
        if "role" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'operator'")
        if "owner_user_id" not in credential_columns:
            db.execute("ALTER TABLE credentials ADD COLUMN owner_user_id INTEGER")
        if "depends_on_run_id" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN depends_on_run_id INTEGER")
        if "cancel_requested" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN cancel_requested INTEGER NOT NULL DEFAULT 0")
        if "canceled_at" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN canceled_at TEXT")
        if "api_calls" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN api_calls INTEGER")
        if "timeout_seconds" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN timeout_seconds INTEGER")
        if "max_api_calls" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN max_api_calls INTEGER")
        if "tunnel_id" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN tunnel_id INTEGER")
        if "tunnel_label" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN tunnel_label TEXT")
        if "tunnel_url" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN tunnel_url TEXT")
        if "network_profile_id" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN network_profile_id INTEGER")
        if "network_profile_label" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN network_profile_label TEXT")
        if "network_proxy_url" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN network_proxy_url TEXT")
        if "network_ca_bundle_path" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN network_ca_bundle_path TEXT")
        if "tunnel_chain_id" not in run_columns:
            db.execute("ALTER TABLE runs ADD COLUMN tunnel_chain_id INTEGER")
        db.execute(
            """
            INSERT OR IGNORE INTO run_dependencies (run_id, depends_on_run_id, alias, created_at)
            SELECT id, depends_on_run_id, NULL, created_at
            FROM runs
            WHERE depends_on_run_id IS NOT NULL
            """
        )
        db.execute("CREATE INDEX IF NOT EXISTS idx_findings_user_created ON findings(user_id, created_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_findings_run ON findings(run_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_user_credentials_user ON user_credentials(user_id, credential_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_user_active_credentials_credential ON user_active_credentials(credential_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_user_tunnels_user ON user_tunnels(user_id, enabled)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_user_network_profiles_user ON user_network_profiles(user_id, enabled)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_user_tunnel_chains_user ON user_tunnel_chains(user_id, enabled)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_user_tunnel_chain_hops_chain ON user_tunnel_chain_hops(chain_id, hop_order)")
        db.commit()

    def ensure_admin():
        db = get_db()
        username = os.getenv("KINTOUN_ADMIN_USER", "admin")
        password = os.getenv("KINTOUN_ADMIN_PASS", "admin123!")
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO users (username, role, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (username, "admin", generate_password_hash(password), _now()),
            )
        db.execute("UPDATE users SET role = 'admin' WHERE username = ?", (username,))
        admin_row = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if admin_row:
            db.execute(
                "UPDATE credentials SET owner_user_id = ? WHERE owner_user_id IS NULL",
                (int(admin_row["id"]),),
            )
            db.execute(
                """
                INSERT OR IGNORE INTO user_credentials (user_id, credential_id, created_at)
                SELECT ?, id, ?
                FROM credentials
                WHERE owner_user_id = ?
                """,
                (int(admin_row["id"]), _now(), int(admin_row["id"])),
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

    def _current_role():
        return session.get("role", "operator")

    def _has_role(*roles):
        return _current_role() in roles

    def role_required(*roles):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                if not session.get("user_id"):
                    return redirect(url_for("login"))
                if not _has_role(*roles):
                    flash("You do not have permission for this action.", "error")
                    if _current_role() == "admin":
                        return redirect(url_for("users_list"))
                    return redirect(url_for("dashboard"))
                return fn(*args, **kwargs)

            return wrapper

        return decorator

    def _credential_accessible(db, user_id, role, credential_id):
        if role == "admin":
            row = db.execute("SELECT id FROM credentials WHERE id = ?", (credential_id,)).fetchone()
            return row is not None
        row = db.execute(
            """
            SELECT c.id
            FROM credentials c
            LEFT JOIN user_credentials uc ON uc.credential_id = c.id AND uc.user_id = ?
            WHERE c.id = ? AND (c.owner_user_id = ? OR uc.user_id IS NOT NULL)
            """,
            (int(user_id), int(credential_id), int(user_id)),
        ).fetchone()
        return row is not None

    def _list_accessible_credentials(db, user_id, role):
        if role == "admin":
            return db.execute(
                "SELECT id, name, created_at, updated_at, owner_user_id FROM credentials ORDER BY name"
            ).fetchall()
        return db.execute(
            """
            SELECT DISTINCT c.id, c.name, c.created_at, c.updated_at, c.owner_user_id
            FROM credentials c
            LEFT JOIN user_credentials uc ON uc.credential_id = c.id
            WHERE c.owner_user_id = ? OR uc.user_id = ?
            ORDER BY c.name
            """,
            (int(user_id), int(user_id)),
        ).fetchall()

    def _set_active_credential(db, user_id, credential_id, source="manual", source_run_id=None):
        existing = db.execute(
            "SELECT user_id FROM user_active_credentials WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
        if existing:
            db.execute(
                """
                UPDATE user_active_credentials
                SET credential_id = ?, source = ?, source_run_id = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (int(credential_id), source, source_run_id, _now(), int(user_id)),
            )
        else:
            db.execute(
                """
                INSERT INTO user_active_credentials
                (user_id, credential_id, source, source_run_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (int(user_id), int(credential_id), source, source_run_id, _now(), _now()),
            )

    def _clear_active_credential(db, user_id):
        db.execute("DELETE FROM user_active_credentials WHERE user_id = ?", (int(user_id),))

    def _get_active_credential_context(db, user_id, role):
        row = db.execute(
            """
            SELECT
                uac.user_id,
                uac.credential_id,
                uac.source,
                uac.source_run_id,
                c.name AS credential_name
            FROM user_active_credentials uac
            LEFT JOIN credentials c ON c.id = uac.credential_id
            WHERE uac.user_id = ?
            """,
            (int(user_id),),
        ).fetchone()
        if not row:
            return None

        credential_id = row["credential_id"]
        if not credential_id or not _credential_accessible(db, user_id, role, int(credential_id)):
            _clear_active_credential(db, user_id)
            db.commit()
            return None
        if not row["credential_name"]:
            _clear_active_credential(db, user_id)
            db.commit()
            return None

        return {
            "credential_id": int(row["credential_id"]),
            "credential_name": row["credential_name"],
            "source": row["source"] or "manual",
            "source_run_id": row["source_run_id"],
        }

    def _list_user_tunnels(db, user_id):
        return db.execute(
            """
            SELECT id, user_id, name, scheme, host, port, enabled, created_at, updated_at
            FROM user_tunnels
            WHERE user_id = ?
            ORDER BY name
            """,
            (int(user_id),),
        ).fetchall()

    def _list_user_tunnel_chains(db, user_id):
        return db.execute(
            """
            SELECT
                c.id,
                c.user_id,
                c.name,
                c.enabled,
                c.created_at,
                c.updated_at,
                COUNT(h.id) AS hop_count,
                GROUP_CONCAT(t.name, ' -> ') AS hop_names
            FROM user_tunnel_chains c
            LEFT JOIN user_tunnel_chain_hops h ON h.chain_id = c.id
            LEFT JOIN user_tunnels t ON t.id = h.tunnel_id
            WHERE c.user_id = ?
            GROUP BY c.id, c.user_id, c.name, c.enabled, c.created_at, c.updated_at
            ORDER BY c.name
            """,
            (int(user_id),),
        ).fetchall()

    def _list_user_network_profiles(db, user_id):
        return db.execute(
            """
            SELECT id, user_id, name, proxy_url, ca_bundle_path, enabled, created_at, updated_at
            FROM user_network_profiles
            WHERE user_id = ?
            ORDER BY name
            """,
            (int(user_id),),
        ).fetchall()

    def _list_chain_hops(db, user_id, chain_id):
        return db.execute(
            """
            SELECT
                h.hop_order,
                t.id AS tunnel_id,
                t.name,
                t.scheme,
                t.host,
                t.port,
                t.enabled
            FROM user_tunnel_chain_hops h
            JOIN user_tunnel_chains c ON c.id = h.chain_id
            JOIN user_tunnels t ON t.id = h.tunnel_id
            WHERE c.id = ? AND c.user_id = ?
            ORDER BY h.hop_order ASC
            """,
            (int(chain_id), int(user_id)),
        ).fetchall()

    def _normalize_proxy_url(raw_url):
        value = (raw_url or "").strip()
        if not value:
            return ""
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme not in ("http", "https", "socks5", "socks5h"):
            return ""
        if not parsed.hostname or not parsed.port:
            return ""
        return value

    def _proxy_url_to_hop(proxy_url, name="proxy"):
        value = (proxy_url or "").strip()
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme not in ("http", "https", "socks5", "socks5h"):
            raise RuntimeError(f"Unsupported proxy scheme: {parsed.scheme}")
        if not parsed.hostname or not parsed.port:
            raise RuntimeError("Proxy URL must include host and port.")
        username = urllib.parse.unquote(parsed.username) if parsed.username else None
        password = urllib.parse.unquote(parsed.password) if parsed.password else None
        return {
            "name": name,
            "scheme": parsed.scheme,
            "host": parsed.hostname,
            "port": int(parsed.port),
            "username": username,
            "password": password,
        }

    def _build_tunnel_url(scheme, host, port):
        normalized_scheme = (scheme or "").strip().lower()
        normalized_host = (host or "").strip()
        if normalized_scheme not in ("http", "https", "socks5", "socks5h"):
            return None
        if not normalized_host:
            return None
        try:
            normalized_port = int(port)
        except Exception:
            return None
        if normalized_port <= 0 or normalized_port > 65535:
            return None
        return f"{normalized_scheme}://{normalized_host}:{normalized_port}"

    def _recv_until(sock, marker, limit=65536):
        data = b""
        while marker not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if len(data) > limit:
                raise RuntimeError("Proxy response exceeded allowed size.")
        return data

    def _http_reason_phrase(message, fallback="Bad Gateway"):
        if not message:
            return fallback
        filtered = "".join(ch for ch in str(message) if ch not in "\r\n")
        filtered = filtered.strip()
        if not filtered:
            return fallback
        if len(filtered) > 180:
            filtered = filtered[:180]
        return filtered

    def _http_connect(sock, host, port, username=None, password=None):
        headers = []
        if username:
            raw = f"{username}:{password or ''}".encode("utf-8")
            token = base64.b64encode(raw).decode("ascii")
            headers.append(f"Proxy-Authorization: Basic {token}\r\n")
        request_data = (
            f"CONNECT {host}:{int(port)} HTTP/1.1\r\n"
            f"Host: {host}:{int(port)}\r\n"
            "Proxy-Connection: Keep-Alive\r\n"
            + "".join(headers) +
            "\r\n"
        ).encode("utf-8")
        sock.sendall(request_data)
        response = _recv_until(sock, b"\r\n\r\n")
        first_line = response.split(b"\r\n", 1)[0].decode("utf-8", errors="replace")
        if " 200 " not in first_line:
            raise RuntimeError(f"HTTP proxy CONNECT failed: {first_line}")

    def _socks5_connect(sock, host, port, resolve_remote=True):
        sock.sendall(b"\x05\x01\x00")
        greeting = sock.recv(2)
        if len(greeting) < 2 or greeting[0] != 5 or greeting[1] != 0:
            raise RuntimeError("SOCKS5 proxy does not support no-auth mode.")

        target_host = host
        atyp = None
        addr_payload = b""
        if resolve_remote:
            encoded = target_host.encode("idna")
            if len(encoded) > 255:
                raise RuntimeError("SOCKS5 hostname too long.")
            atyp = b"\x03"
            addr_payload = bytes([len(encoded)]) + encoded
        else:
            try:
                ip_bytes = socket.inet_aton(target_host)
                atyp = b"\x01"
                addr_payload = ip_bytes
            except OSError:
                resolved = socket.gethostbyname(target_host)
                ip_bytes = socket.inet_aton(resolved)
                atyp = b"\x01"
                addr_payload = ip_bytes

        port_payload = int(port).to_bytes(2, "big")
        request_data = b"\x05\x01\x00" + atyp + addr_payload + port_payload
        sock.sendall(request_data)
        header = sock.recv(4)
        if len(header) < 4 or header[0] != 5:
            raise RuntimeError("Invalid SOCKS5 response header.")
        if header[1] != 0:
            raise RuntimeError(f"SOCKS5 CONNECT failed with status {header[1]}.")
        addr_type = header[3]
        if addr_type == 1:
            _ = sock.recv(4)
        elif addr_type == 3:
            length_raw = sock.recv(1)
            if not length_raw:
                raise RuntimeError("Invalid SOCKS5 domain response length.")
            _ = sock.recv(length_raw[0])
        elif addr_type == 4:
            _ = sock.recv(16)
        _ = sock.recv(2)

    def _connect_via_chain(hops, dest_host, dest_port, timeout=20):
        if not hops:
            raise RuntimeError("Tunnel chain has no hops.")
        first = hops[0]
        proxy_sock = socket.create_connection((first["host"], int(first["port"])), timeout=timeout)
        proxy_sock.settimeout(timeout)
        try:
            for idx, hop in enumerate(hops):
                scheme = (hop.get("scheme") or "").lower()
                if idx + 1 < len(hops):
                    next_hop = hops[idx + 1]
                    target_host = next_hop["host"]
                    target_port = int(next_hop["port"])
                else:
                    target_host = dest_host
                    target_port = int(dest_port)
                if scheme in ("http", "https"):
                    _http_connect(
                        proxy_sock,
                        target_host,
                        target_port,
                        username=hop.get("username"),
                        password=hop.get("password"),
                    )
                elif scheme in ("socks5", "socks5h"):
                    _socks5_connect(proxy_sock, target_host, target_port, resolve_remote=True)
                else:
                    raise RuntimeError(f"Unsupported proxy scheme in chain: {scheme}")
            proxy_sock.settimeout(None)
            return proxy_sock
        except Exception:
            try:
                proxy_sock.close()
            except Exception:
                pass
            raise

    class ProxyChainRelay:
        def __init__(self, hops):
            self.hops = hops
            self._listener = None
            self._accept_thread = None
            self._stop = threading.Event()
            self._client_threads = set()
            self.bind_host = "127.0.0.1"
            self.bind_port = None

        def start(self):
            self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._listener.bind((self.bind_host, 0))
            self._listener.listen(16)
            self.bind_port = int(self._listener.getsockname()[1])
            self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._accept_thread.start()

        def _accept_loop(self):
            while not self._stop.is_set():
                try:
                    client, _addr = self._listener.accept()
                except OSError:
                    if self._stop.is_set():
                        return
                    continue
                th = threading.Thread(target=self._handle_client, args=(client,), daemon=True)
                self._client_threads.add(th)
                th.start()

        def _handle_client(self, client):
            upstream = None
            try:
                request_blob = _recv_until(client, b"\r\n\r\n")
                request_head = request_blob.decode("utf-8", errors="replace").split("\r\n")
                if not request_head or not request_head[0].startswith("CONNECT "):
                    client.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
                    return
                parts = request_head[0].split(" ")
                if len(parts) < 2 or ":" not in parts[1]:
                    client.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                    return
                dest_host, dest_port_str = parts[1].rsplit(":", 1)
                dest_port = int(dest_port_str)
                upstream = _connect_via_chain(self.hops, dest_host, dest_port)
                client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                self._bridge(client, upstream)
            except Exception as exc:
                try:
                    reason = _http_reason_phrase(str(exc))
                    client.sendall(f"HTTP/1.1 502 {reason}\r\n\r\n".encode("utf-8", errors="replace"))
                except Exception:
                    pass
            finally:
                try:
                    client.close()
                except Exception:
                    pass
                if upstream:
                    try:
                        upstream.close()
                    except Exception:
                        pass

        def _bridge(self, a, b):
            sockets = [a, b]
            while not self._stop.is_set():
                readable, _, _ = select.select(sockets, [], [], 1.0)
                if not readable:
                    continue
                for src in readable:
                    dst = b if src is a else a
                    data = src.recv(16384)
                    if not data:
                        return
                    dst.sendall(data)

        def stop(self):
            self._stop.set()
            if self._listener:
                try:
                    self._listener.close()
                except Exception:
                    pass
            if self._accept_thread and self._accept_thread.is_alive():
                self._accept_thread.join(timeout=1.5)

        @property
        def local_proxy_url(self):
            if not self.bind_port:
                return None
            return f"http://{self.bind_host}:{self.bind_port}"

    def _resolve_credential_session(db, credential_id):
        row = db.execute(
            """
            SELECT profile_enc, access_key_enc, secret_key_enc, session_token_enc
            FROM credentials
            WHERE id = ?
            """,
            (int(credential_id),),
        ).fetchone()
        if not row:
            raise RuntimeError("Credential not found.")
        credentials = {
            "profile": decrypt(row["profile_enc"]),
            "aws_access_key_id": decrypt(row["access_key_enc"]),
            "aws_secret_access_key": decrypt(row["secret_key_enc"]),
            "aws_session_token": decrypt(row["session_token_enc"]),
        }
        return credential_handler.Credential(credentials).session

    def _generate_console_link(session_obj):
        sts_client = session_obj.client("sts", config=Config(user_agent="kintoun-web"))
        identity = sts_client.get_caller_identity()

        frozen = session_obj.get_credentials().get_frozen_credentials()
        session_payload = {
            "sessionId": frozen.access_key,
            "sessionKey": frozen.secret_key,
            "sessionToken": frozen.token,
        }
        if not session_payload.get("sessionToken"):
            try:
                temp = sts_client.get_session_token(DurationSeconds=3600)
                temp_creds = temp.get("Credentials", {})
                session_payload = {
                    "sessionId": temp_creds.get("AccessKeyId"),
                    "sessionKey": temp_creds.get("SecretAccessKey"),
                    "sessionToken": temp_creds.get("SessionToken"),
                }
            except Exception as exc:
                raise RuntimeError(
                    "Unable to obtain temporary session token for AWS console federation. "
                    "Use credentials that include a session token or allow sts:GetSessionToken."
                ) from exc

        if not session_payload.get("sessionId") or not session_payload.get("sessionKey") or not session_payload.get("sessionToken"):
            raise RuntimeError("Credential does not include valid session values for AWS federation login.")

        signin_params = urllib.parse.urlencode(
            {
                "Action": "getSigninToken",
                "Session": json.dumps(session_payload),
            }
        )
        signin_url = f"https://signin.aws.amazon.com/federation?{signin_params}"
        with urllib.request.urlopen(signin_url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        signin_token = payload.get("SigninToken")
        if not signin_token:
            raise RuntimeError("AWS federation endpoint did not return a SigninToken.")

        login_params = urllib.parse.urlencode(
            {
                "Action": "login",
                "Issuer": "Kintoun",
                "Destination": "https://console.aws.amazon.com/",
                "SigninToken": signin_token,
            }
        )
        login_url = f"https://signin.aws.amazon.com/federation?{login_params}"
        return login_url, identity.get("Arn", "unknown")

    def _safe_assumed_credential_name(role_arn, run_id):
        role_tail = (role_arn or "role").split("/")[-1]
        sanitized = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in role_tail).strip("_")
        sanitized = sanitized or "role"
        if len(sanitized) > 48:
            sanitized = sanitized[:48]
        return f"assumed-{sanitized}-run{int(run_id)}"

    def _apply_assume_role_side_effects(db, run_row, normalized_result):
        module_path = f"{run_row['module_category']}/{run_row['module_name']}"
        if module_path != "lateral_movement/iam_assume_role":
            return
        if not isinstance(normalized_result, dict):
            return
        if normalized_result.get("status") != "ok":
            return

        data = normalized_result.get("data")
        if not isinstance(data, dict):
            return
        assumed_credentials = data.pop("assumed_credentials", None)
        if not isinstance(assumed_credentials, dict):
            return

        access_key = assumed_credentials.get("access_key_id")
        secret_key = assumed_credentials.get("secret_access_key")
        session_token = assumed_credentials.get("session_token")
        expiration = assumed_credentials.get("expiration")
        role_arn = assumed_credentials.get("role_arn") or data.get("role_arn")
        if not access_key or not secret_key or not session_token:
            normalized_result.setdefault("errors", []).append(
                "AssumeRole succeeded but returned incomplete temporary credentials."
            )
            return

        credential_name = _safe_assumed_credential_name(role_arn, run_row["id"])
        db.execute(
            """
            INSERT INTO credentials
            (name, owner_user_id, profile_enc, access_key_enc, secret_key_enc, session_token_enc, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                credential_name,
                int(run_row["user_id"]),
                None,
                encrypt(access_key),
                encrypt(secret_key),
                encrypt(session_token),
                _now(),
                _now(),
            ),
        )
        new_credential_id = int(db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
        db.execute(
            """
            INSERT OR IGNORE INTO user_credentials (user_id, credential_id, created_at)
            VALUES (?, ?, ?)
            """,
            (int(run_row["user_id"]), new_credential_id, _now()),
        )
        _set_active_credential(
            db,
            int(run_row["user_id"]),
            new_credential_id,
            source="assume_role",
            source_run_id=int(run_row["id"]),
        )
        data["active_credential"] = {
            "credential_id": new_credential_id,
            "credential_name": credential_name,
            "source": "assume_role",
            "source_run_id": int(run_row["id"]),
            "expiration": expiration,
            "role_arn": role_arn,
        }

    def _can_view_all_runs(role):
        return role == "viewer"

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
                "execution_limits": {
                    "timeout_seconds": app.config["DEFAULT_TIMEOUT_SECONDS"],
                    "max_api_calls": app.config["DEFAULT_MAX_API_CALLS"],
                },
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

    def _present_lambda_enumerate_functions(run_row, result_obj):
        data = result_obj.get("data", {}) if isinstance(result_obj, dict) else {}
        regions = data.get("regions", {}) if isinstance(data, dict) else {}
        rows = []
        region_rows = []
        for region, functions in regions.items():
            fn_list = functions or []
            region_rows.append({"Region": region, "Functions": len(fn_list)})
            for fn in fn_list:
                if not isinstance(fn, dict):
                    continue
                rows.append(
                    {
                        "Region": region,
                        "FunctionName": fn.get("function_name") or "-",
                        "FunctionArn": fn.get("function_arn") or "-",
                        "Role": fn.get("role") or "-",
                        "Runtime": fn.get("runtime") or "-",
                    }
                )
        rows.sort(key=lambda r: (r["Region"], r["FunctionName"]))
        region_rows.sort(key=lambda r: r["Region"])
        return {
            "title": "Lambda Functions Inventory",
            "highlights": [
                {"label": "Total Functions", "value": data.get("total_functions", len(rows))},
                {"label": "Regions Scanned", "value": len(regions)},
                {"label": "Regions With Functions", "value": sum(1 for r in region_rows if r["Functions"] > 0)},
            ],
            "sections": [
                {
                    "title": "Functions by Region",
                    "columns": ["Region", "Functions"],
                    "rows": region_rows,
                },
                {
                    "title": "Functions Detail",
                    "columns": ["Region", "FunctionName", "FunctionArn", "Role", "Runtime"],
                    "rows": rows[:1000],
                },
            ],
        }

    def _build_presenter(run_row, result_obj, result_view=None):
        module_path = f"{run_row['module_category']}/{run_row['module_name']}"
        presenters = {
            "ec2_enumerate_instances": _present_ec2_enumerate_instances,
            "ec2_enumerate_user_data": _present_ec2_enumerate_user_data,
            "iam_enumerate_roles": _present_iam_enumerate_roles,
            "iam_enumerate_role_trust_policy": _present_iam_role_trust,
            "lambda_enumerate_functions": _present_lambda_enumerate_functions,
            "enumeration/ec2_enumerate_instances": _present_ec2_enumerate_instances,
            "enumeration/ec2_enumerate_user_data": _present_ec2_enumerate_user_data,
            "enumeration/iam_enumerate_roles": _present_iam_enumerate_roles,
            "enumeration/iam_enumerate_role_trust_policy": _present_iam_role_trust,
            "enumeration/lambda_enumerate_functions": _present_lambda_enumerate_functions,
        }
        presenter = presenters.get(result_view) or presenters.get(module_path) or _present_default
        try:
            return presenter(run_row, result_obj)
        except Exception:
            return _present_default(run_row, result_obj)

    def _extract_findings(run_row, result_obj):
        module_path = f"{run_row['module_category']}/{run_row['module_name']}"
        data = result_obj.get("data", {}) if isinstance(result_obj, dict) else {}
        findings = []

        def add_finding(
            severity,
            category,
            title,
            description,
            resource_type=None,
            resource_id=None,
            details=None,
        ):
            findings.append(
                {
                    "severity": severity,
                    "category": category,
                    "title": title,
                    "description": description,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "details": details or {},
                }
            )

        if module_path == "enumeration/ec2_enumerate_instances" and isinstance(data, dict):
            regions = data.get("regions", {}) or {}
            for region, instances in regions.items():
                for instance in instances or []:
                    if instance.get("public_ip"):
                        instance_id = instance.get("instance_id")
                        add_finding(
                            "medium",
                            "network_exposure",
                            "EC2 instance has public IP",
                            f"Instance {instance_id} in {region} has a public IP address.",
                            resource_type="ec2_instance",
                            resource_id=instance_id,
                            details={"region": region, "public_ip": instance.get("public_ip")},
                        )

        if module_path == "enumeration/ec2_enumerate_user_data" and isinstance(data, dict):
            regions = data.get("regions", {}) or {}
            sensitive_markers = [
                "aws_access_key_id",
                "aws_secret_access_key",
                "password",
                "secret",
                "token",
                "private_key",
                "-----BEGIN",
            ]
            for region, region_info in regions.items():
                for instance in (region_info or {}).get("instances", []):
                    instance_id = instance.get("instance_id")
                    user_data_text = (instance.get("user_data") or "").lower()
                    if instance.get("has_user_data"):
                        add_finding(
                            "info",
                            "script_exposure",
                            "EC2 instance has user data script",
                            f"Instance {instance_id} in {region} has user data configured.",
                            resource_type="ec2_instance",
                            resource_id=instance_id,
                            details={"region": region},
                        )
                    if user_data_text and any(marker in user_data_text for marker in sensitive_markers):
                        add_finding(
                            "high",
                            "credential_exposure",
                            "Potential secret in EC2 user data",
                            f"Instance {instance_id} in {region} appears to include sensitive material in user data.",
                            resource_type="ec2_instance",
                            resource_id=instance_id,
                            details={"region": region},
                        )

        if module_path == "enumeration/iam_enumerate_role_trust_policy" and isinstance(data, dict):
            roles = data.get("roles", []) or []
            for role in roles:
                role_name = role.get("role_name")
                trusted_entities = role.get("trusted_entities", []) or []
                for entity in trusted_entities:
                    principal_type = entity.get("principal_type")
                    principal_value = entity.get("value")
                    if principal_type == "Wildcard" and principal_value == "*":
                        add_finding(
                            "high",
                            "privilege_escalation",
                            "Role trust policy allows wildcard principal",
                            f"Role {role_name} can be assumed by any principal.",
                            resource_type="iam_role",
                            resource_id=role_name,
                            details=entity,
                        )
                    elif principal_type == "AWS" and isinstance(principal_value, str) and principal_value.endswith(":root"):
                        add_finding(
                            "medium",
                            "privilege_escalation",
                            "Role trust policy allows root principal",
                            f"Role {role_name} trust policy includes root principal {principal_value}.",
                            resource_type="iam_role",
                            resource_id=role_name,
                            details=entity,
                        )
                    elif principal_type == "Service":
                        add_finding(
                            "info",
                            "service_trust",
                            "Role trusted by AWS service",
                            f"Role {role_name} is trusted by service principal {principal_value}.",
                            resource_type="iam_role",
                            resource_id=role_name,
                            details=entity,
                        )

        if module_path == "enumeration/iam_bruteforce_permissions" and isinstance(data, dict):
            summary = data.get("summary", {}) or {}
            total_allowed = int(summary.get("total_allowed", 0) or 0)
            if total_allowed >= 1000:
                add_finding(
                    "high",
                    "broad_permissions",
                    "Large read permission surface detected",
                    f"Bruteforce permission probe reports {total_allowed} allowed actions.",
                    resource_type="aws_identity",
                    resource_id="current_session",
                    details=summary,
                )
            elif total_allowed >= 300:
                add_finding(
                    "medium",
                    "broad_permissions",
                    "Broad read permission surface detected",
                    f"Bruteforce permission probe reports {total_allowed} allowed actions.",
                    resource_type="aws_identity",
                    resource_id="current_session",
                    details=summary,
                )

        return findings[:1000]

    def _persist_findings(db, run_row, findings):
        db.execute("DELETE FROM findings WHERE run_id = ?", (int(run_row["id"]),))
        for finding in findings:
            db.execute(
                """
                INSERT INTO findings
                (run_id, user_id, credential_id, module_path, severity, category, title, resource_type, resource_id, description, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(run_row["id"]),
                    int(run_row["user_id"]),
                    int(run_row["credential_id"]),
                    f"{run_row['module_category']}/{run_row['module_name']}",
                    finding.get("severity", "info"),
                    finding.get("category", "general"),
                    finding.get("title", "Finding"),
                    finding.get("resource_type"),
                    finding.get("resource_id"),
                    finding.get("description"),
                    json.dumps(finding.get("details", {}), default=str),
                    _now(),
                ),
            )
        db.commit()

    def _dispatch_queued_runs():
        db = sqlite3.connect(app.config["DB_PATH"], check_same_thread=False)
        db.row_factory = sqlite3.Row
        try:
            running_count = db.execute(
                "SELECT COUNT(1) AS c FROM runs WHERE status = 'running'"
            ).fetchone()["c"]
            available_slots = max(0, int(app.config["WORKER_CONCURRENCY"]) - int(running_count))
            if available_slots <= 0:
                return

            queued_runs = db.execute(
                """
                SELECT id
                FROM runs
                WHERE status = 'queued' AND COALESCE(cancel_requested, 0) = 0
                ORDER BY id ASC
                LIMIT ?
                """,
                (available_slots,),
            ).fetchall()
            for row in queued_runs:
                run_id = int(row["id"])
                worker = threading.Thread(target=run_module_job, args=(run_id,), daemon=True)
                worker.start()
        finally:
            db.close()

    def start_queue_dispatcher():
        if app.config.get("_dispatcher_started"):
            return
        app.config["_dispatcher_started"] = True

        def _loop():
            while True:
                try:
                    with app.app_context():
                        _dispatch_queued_runs()
                except Exception:
                    pass
                time.sleep(2)

        dispatcher = threading.Thread(target=_loop, daemon=True, name="kintoun-queue-dispatcher")
        dispatcher.start()

    def run_module_job(run_id: int):
        with app.app_context():
            db = sqlite3.connect(app.config["DB_PATH"], check_same_thread=False)
            db.row_factory = sqlite3.Row
            running_cursor = db.execute(
                """
                UPDATE runs
                SET status = ?, started_at = ?
                WHERE id = ? AND status = 'queued' AND COALESCE(cancel_requested, 0) = 0
                """,
                ("running", _now(), run_id),
            )
            db.commit()
            if running_cursor.rowcount == 0:
                db.close()
                return

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
            api_calls_used = 0

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
                chain_relay = None
                tunnel_raw = (run["tunnel_url"] or "").strip() if "tunnel_url" in run.keys() else ""
                network_proxy_raw = (run["network_proxy_url"] or "").strip() if "network_proxy_url" in run.keys() else ""
                verify_path = (run["network_ca_bundle_path"] or "").strip() if "network_ca_bundle_path" in run.keys() else ""
                effective_proxy_url = None
                combined_hops = []
                if tunnel_raw.startswith("chain_json:"):
                    try:
                        chain_hops = json.loads(tunnel_raw[len("chain_json:"):])
                    except Exception:
                        chain_hops = []
                    if not isinstance(chain_hops, list) or not chain_hops:
                        raise RuntimeError("Invalid tunnel chain configuration for run.")
                    for hop in chain_hops:
                        if not isinstance(hop, dict):
                            continue
                        combined_hops.append(
                            {
                                "name": hop.get("name", "tunnel-hop"),
                                "scheme": hop.get("scheme"),
                                "host": hop.get("host"),
                                "port": int(hop.get("port")),
                                "username": hop.get("username"),
                                "password": hop.get("password"),
                            }
                        )
                elif tunnel_raw:
                    combined_hops.append(_proxy_url_to_hop(tunnel_raw, name="tunnel"))

                if network_proxy_raw:
                    combined_hops.append(_proxy_url_to_hop(network_proxy_raw, name="network-profile-proxy"))

                if combined_hops:
                    chain_relay = ProxyChainRelay(combined_hops)
                    chain_relay.start()
                    effective_proxy_url = chain_relay.local_proxy_url

                if effective_proxy_url:
                    botoconfig = Config(
                        user_agent="kintoun-web",
                        proxies={"http": effective_proxy_url, "https": effective_proxy_url},
                    )
                else:
                    botoconfig = Config(user_agent="kintoun-web")

                original_session_client = session_obj.client
                if verify_path:
                    def _client_with_verify(*args, **kwargs):
                        if "verify" not in kwargs:
                            kwargs["verify"] = verify_path
                        return original_session_client(*args, **kwargs)
                    session_obj.client = _client_with_verify

                module_path = f"modules.{run['module_category']}.{run['module_name']}"
                module = importlib.import_module(module_path)
                module_metadata = getattr(module, "MODULE_METADATA", {}) or {}
                execution_limits = module_metadata.get("execution_limits", {}) or {}
                try:
                    timeout_seconds = int(execution_limits.get("timeout_seconds", app.config["DEFAULT_TIMEOUT_SECONDS"]))
                except Exception:
                    timeout_seconds = app.config["DEFAULT_TIMEOUT_SECONDS"]
                try:
                    max_api_calls = int(execution_limits.get("max_api_calls", app.config["DEFAULT_MAX_API_CALLS"]))
                except Exception:
                    max_api_calls = app.config["DEFAULT_MAX_API_CALLS"]
                timeout_seconds = max(30, timeout_seconds)
                max_api_calls = max(50, max_api_calls)

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

                def is_cancel_requested():
                    row = db.execute(
                        "SELECT status, cancel_requested FROM runs WHERE id = ?",
                        (run_id,),
                    ).fetchone()
                    if not row:
                        return True
                    return row["status"] == "canceled" or int(row["cancel_requested"] or 0) == 1

                guard_state.state = {
                    "run_id": run_id,
                    "api_calls": 0,
                    "max_api_calls": max_api_calls,
                    "timeout_seconds": timeout_seconds,
                    "deadline": time.monotonic() + timeout_seconds,
                    "is_cancel_requested": is_cancel_requested,
                }
                if is_cancel_requested():
                    raise RunCancelledError("Run cancelled by operator.")

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
                api_calls_used = int(getattr(guard_state, "state", {}).get("api_calls", 0))
                normalized_result = utils.normalize_module_output(result)
                if normalized_result.get("status") == "error" and normalized_result.get("errors"):
                    status = "failed"
                    error_text = "\n".join(normalized_result.get("errors", []))
                try:
                    _apply_assume_role_side_effects(db, run, normalized_result)
                except Exception as side_effect_exc:
                    normalized_result.setdefault("errors", []).append(
                        f"Assume-role post processing warning: {str(side_effect_exc)}"
                    )
                result_json = json.dumps(normalized_result, default=str, indent=2)
            except RunCancelledError as exc:
                status = "canceled"
                error_text = str(exc)
                result_json = json.dumps(
                    utils.module_result(
                        status="error",
                        errors=[str(exc)],
                        data={"reason": "canceled"},
                    ),
                    default=str,
                    indent=2,
                )
            except RunTimeoutError as exc:
                status = "timed_out"
                error_text = str(exc)
                result_json = json.dumps(
                    utils.module_result(
                        status="error",
                        errors=[str(exc)],
                        data={"reason": "timed_out"},
                    ),
                    default=str,
                    indent=2,
                )
            except RunApiLimitError as exc:
                status = "failed"
                error_text = str(exc)
                result_json = json.dumps(
                    utils.module_result(
                        status="error",
                        errors=[str(exc)],
                        data={"reason": "api_call_limit"},
                    ),
                    default=str,
                    indent=2,
                )
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
                api_calls_used = int(getattr(guard_state, "state", {}).get("api_calls", api_calls_used))
                guard_state.state = None
                builtins.input = original_input
                builtins.print = original_print
                if "chain_relay" in locals() and chain_relay:
                    try:
                        chain_relay.stop()
                    except Exception:
                        pass

            try:
                result_obj = _parse_json_or_empty(result_json)
                extracted_findings = _extract_findings(run, result_obj)
                _persist_findings(db, run, extracted_findings)
            except Exception:
                pass

            db.execute(
                """
                UPDATE runs
                SET status = ?, stdout = ?, stderr = ?, result_json = ?, error_text = ?, finished_at = ?, api_calls = ?, timeout_seconds = ?, max_api_calls = ?, canceled_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    None,
                    None,
                    result_json,
                    error_text,
                    _now(),
                    api_calls_used,
                    timeout_seconds if "timeout_seconds" in locals() else None,
                    max_api_calls if "max_api_calls" in locals() else None,
                    _now() if status == "canceled" else None,
                    run_id,
                ),
            )
            db.commit()
            db.close()

    @app.route("/healthz")
    def healthz():
        return {
            "status": "ok",
            "worker_concurrency": app.config["WORKER_CONCURRENCY"],
            "dispatcher_started": bool(app.config.get("_dispatcher_started")),
        }

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
                session["role"] = user["role"] or "operator"
                if session["role"] == "admin":
                    return redirect(url_for("users_list"))
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "error")
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            password_confirm = request.form.get("password_confirm", "")
            role = request.form.get("role", "operator").strip().lower()

            if not username:
                flash("Username is required.", "error")
                return render_template("register.html")
            if len(password) < 8:
                flash("Password must have at least 8 characters.", "error")
                return render_template("register.html")
            if password != password_confirm:
                flash("Passwords do not match.", "error")
                return render_template("register.html")
            if role not in ("operator", "viewer"):
                flash("Invalid role selected.", "error")
                return render_template("register.html")

            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, role, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (username, role, generate_password_hash(password), _now()),
                )
                db.commit()
                flash("Account created. You can sign in now.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Username already exists.", "error")
        return render_template("register.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def dashboard():
        if _current_role() == "admin":
            return redirect(url_for("users_list"))
        db = get_db()
        role = _current_role()
        user_id = int(session["user_id"])
        credentials = _list_accessible_credentials(db, user_id, role)
        active_credential = _get_active_credential_context(db, user_id, role) if role == "operator" else None
        regions = region_parser.get_regions()
        if _can_view_all_runs(role):
            runs = db.execute(
                """
                SELECT
                    r.id,
                    u.username AS operator_username,
                    r.module_category,
                    r.module_name,
                    r.tunnel_label,
                    r.status,
                    r.created_at,
                    r.started_at,
                    r.finished_at,
                    r.error_text,
                    r.stderr,
                    c.name AS credential_name
                FROM runs r
                JOIN users u ON u.id = r.user_id
                JOIN credentials c ON c.id = r.credential_id
                ORDER BY r.id DESC
                LIMIT 25
                """
            ).fetchall()
        else:
            runs = db.execute(
                """
                SELECT
                    r.id,
                    u.username AS operator_username,
                    r.module_category,
                    r.module_name,
                    r.tunnel_label,
                    r.status,
                    r.created_at,
                    r.started_at,
                    r.finished_at,
                    r.error_text,
                    r.stderr,
                    c.name AS credential_name
                FROM runs r
                JOIN users u ON u.id = r.user_id
                JOIN credentials c ON c.id = r.credential_id
                WHERE r.user_id = ?
                ORDER BY r.id DESC
                LIMIT 25
                """,
                (user_id,),
            ).fetchall()
        modules = get_modules_catalog()
        categories = sorted({m["category"] for m in modules})
        tunnels = _list_user_tunnels(db, user_id) if role == "operator" else []
        tunnel_chains = _list_user_tunnel_chains(db, user_id) if role == "operator" else []
        network_profiles = _list_user_network_profiles(db, user_id) if role == "operator" else []
        if _can_view_all_runs(role):
            dependency_runs = db.execute(
                """
                SELECT
                    r.id,
                    r.created_at,
                    r.credential_id,
                    r.module_category,
                    r.module_name,
                    u.username AS operator_username,
                    c.name AS credential_name
                FROM runs r
                JOIN users u ON u.id = r.user_id
                JOIN credentials c ON c.id = r.credential_id
                WHERE r.status = 'completed'
                ORDER BY r.id DESC
                LIMIT 300
                """
            ).fetchall()
        else:
            dependency_runs = db.execute(
                """
                SELECT
                    r.id,
                    r.created_at,
                    r.credential_id,
                    r.module_category,
                    r.module_name,
                    u.username AS operator_username,
                    c.name AS credential_name
                FROM runs r
                JOIN users u ON u.id = r.user_id
                JOIN credentials c ON c.id = r.credential_id
                WHERE r.user_id = ?
                  AND r.status = 'completed'
                ORDER BY r.id DESC
                LIMIT 300
                """,
                (user_id,),
            ).fetchall()
        if _can_view_all_runs(role):
            recent_findings = db.execute(
                """
                SELECT
                    id,
                    run_id,
                    severity,
                    category,
                    title,
                    resource_type,
                    resource_id,
                    created_at
                FROM findings
                ORDER BY id DESC
                LIMIT 25
                """
            ).fetchall()
            correlated_signals = db.execute(
                """
                SELECT
                    resource_type,
                    resource_id,
                    COUNT(*) AS findings_count,
                    COUNT(DISTINCT category) AS categories_count
                FROM findings
                WHERE COALESCE(resource_id, '') <> ''
                GROUP BY resource_type, resource_id
                HAVING COUNT(DISTINCT category) >= 2
                ORDER BY categories_count DESC, findings_count DESC
                LIMIT 20
                """
            ).fetchall()
        else:
            recent_findings = db.execute(
                """
                SELECT
                    id,
                    run_id,
                    severity,
                    category,
                    title,
                    resource_type,
                    resource_id,
                    created_at
                FROM findings
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 25
                """,
                (user_id,),
            ).fetchall()
            correlated_signals = db.execute(
                """
                SELECT
                    resource_type,
                    resource_id,
                    COUNT(*) AS findings_count,
                    COUNT(DISTINCT category) AS categories_count
                FROM findings
                WHERE user_id = ?
                  AND COALESCE(resource_id, '') <> ''
                GROUP BY resource_type, resource_id
                HAVING COUNT(DISTINCT category) >= 2
                ORDER BY categories_count DESC, findings_count DESC
                LIMIT 20
                """,
                (user_id,),
            ).fetchall()
        return render_template(
            "dashboard.html",
            modules=modules,
            categories=categories,
            credentials=credentials,
            runs=runs,
            regions=regions,
            tunnels=tunnels,
            tunnel_chains=tunnel_chains,
            network_profiles=network_profiles,
            dependency_runs=dependency_runs,
            recent_findings=recent_findings,
            correlated_signals=correlated_signals,
            role=role,
            can_queue=role == "operator",
            generated_console_link=session.get("generated_console_link"),
            generated_console_identity=session.get("generated_console_identity"),
            active_credential_id=active_credential["credential_id"] if active_credential else None,
            active_credential_name=active_credential["credential_name"] if active_credential else None,
            active_credential_source=active_credential["source"] if active_credential else None,
            active_credential_source_run_id=active_credential["source_run_id"] if active_credential else None,
        )

    @app.route("/console/generate", methods=["POST"])
    @role_required("operator")
    def console_generate():
        credential_id = request.form.get("credential_id", "").strip()
        db = get_db()
        if not credential_id:
            active_ctx = _get_active_credential_context(db, int(session["user_id"]), _current_role())
            if active_ctx:
                credential_id = str(active_ctx["credential_id"])
            else:
                flash("Select a credential before generating console link.", "error")
                return redirect(url_for("dashboard"))
        try:
            credential_id_value = int(credential_id)
        except ValueError:
            flash("Invalid credential selection.", "error")
            return redirect(url_for("dashboard"))

        if not _credential_accessible(db, session["user_id"], _current_role(), credential_id_value):
            flash("You do not have access to selected credential.", "error")
            return redirect(url_for("dashboard"))

        try:
            session_obj = _resolve_credential_session(db, credential_id_value)
            login_url, identity_arn = _generate_console_link(session_obj)
        except Exception as exc:
            flash(f"Failed to generate AWS console link: {str(exc)}", "error")
            return redirect(url_for("dashboard"))

        session["generated_console_link"] = login_url
        session["generated_console_identity"] = identity_arn
        flash("AWS console link generated.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/credentials")
    @role_required("operator")
    def credentials_list():
        db = get_db()
        rows = _list_accessible_credentials(db, int(session["user_id"]), _current_role())
        return render_template("credentials.html", credentials=rows, role=_current_role())

    @app.route("/credentials/new", methods=["GET", "POST"])
    @role_required("operator")
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
                    (name, owner_user_id, profile_enc, access_key_enc, secret_key_enc, session_token_enc, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        int(session["user_id"]),
                        encrypt(request.form.get("profile", "").strip()),
                        encrypt(request.form.get("access_key", "").strip()),
                        encrypt(request.form.get("secret_key", "").strip()),
                        encrypt(request.form.get("session_token", "").strip()),
                        _now(),
                        _now(),
                    ),
                )
                credential_id = db.execute("SELECT id FROM credentials WHERE name = ?", (name,)).fetchone()["id"]
                db.execute(
                    """
                    INSERT OR IGNORE INTO user_credentials (user_id, credential_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (int(session["user_id"]), int(credential_id), _now()),
                )
                db.commit()
                flash("Credential saved.", "success")
                return redirect(url_for("credentials_list"))
            except sqlite3.IntegrityError:
                flash("Credential name already exists.", "error")
        return render_template("credential_form.html", credential=None)

    @app.route("/credentials/<int:credential_id>/edit", methods=["GET", "POST"])
    @role_required("operator")
    def credentials_edit(credential_id):
        db = get_db()
        row = db.execute("SELECT * FROM credentials WHERE id = ?", (credential_id,)).fetchone()
        if not row:
            flash("Credential not found.", "error")
            return redirect(url_for("credentials_list"))
        if not _credential_accessible(db, session["user_id"], _current_role(), credential_id):
            flash("You do not have access to this credential.", "error")
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
    @role_required("operator")
    def credentials_delete(credential_id):
        db = get_db()
        if not _credential_accessible(db, session["user_id"], _current_role(), credential_id):
            flash("You do not have access to this credential.", "error")
            return redirect(url_for("credentials_list"))
        db.execute("DELETE FROM user_credentials WHERE credential_id = ?", (credential_id,))
        db.execute("DELETE FROM user_active_credentials WHERE credential_id = ?", (credential_id,))
        db.execute("DELETE FROM credentials WHERE id = ?", (credential_id,))
        db.commit()
        flash("Credential deleted.", "success")
        return redirect(url_for("credentials_list"))

    @app.route("/tunnels")
    @role_required("operator")
    def tunnels_list():
        db = get_db()
        user_id = int(session["user_id"])
        rows = _list_user_tunnels(db, user_id)
        chains = _list_user_tunnel_chains(db, user_id)
        network_profiles = _list_user_network_profiles(db, user_id)
        return render_template("tunnels.html", tunnels=rows, chains=chains, network_profiles=network_profiles)

    @app.route("/tunnels/new", methods=["GET", "POST"])
    @role_required("operator")
    def tunnels_new():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            scheme = request.form.get("scheme", "").strip().lower()
            host = request.form.get("host", "").strip()
            port = request.form.get("port", "").strip()
            enabled = 1 if request.form.get("enabled") == "on" else 0
            tunnel_url = _build_tunnel_url(scheme, host, port)
            if not name:
                flash("Tunnel name is required.", "error")
                return render_template("tunnel_form.html", tunnel=None)
            if not tunnel_url:
                flash("Invalid tunnel configuration.", "error")
                return render_template("tunnel_form.html", tunnel=None)

            db = get_db()
            try:
                db.execute(
                    """
                    INSERT INTO user_tunnels (user_id, name, scheme, host, port, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (int(session["user_id"]), name, scheme, host, int(port), enabled, _now(), _now()),
                )
                db.commit()
                flash("Tunnel saved.", "success")
                return redirect(url_for("tunnels_list"))
            except sqlite3.IntegrityError:
                flash("Tunnel name already exists for this user.", "error")
        return render_template("tunnel_form.html", tunnel=None)

    @app.route("/tunnels/<int:tunnel_id>/edit", methods=["GET", "POST"])
    @role_required("operator")
    def tunnels_edit(tunnel_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM user_tunnels WHERE id = ? AND user_id = ?",
            (tunnel_id, int(session["user_id"])),
        ).fetchone()
        if not row:
            flash("Tunnel not found.", "error")
            return redirect(url_for("tunnels_list"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            scheme = request.form.get("scheme", "").strip().lower()
            host = request.form.get("host", "").strip()
            port = request.form.get("port", "").strip()
            enabled = 1 if request.form.get("enabled") == "on" else 0
            tunnel_url = _build_tunnel_url(scheme, host, port)
            if not name:
                flash("Tunnel name is required.", "error")
                return redirect(url_for("tunnels_edit", tunnel_id=tunnel_id))
            if not tunnel_url:
                flash("Invalid tunnel configuration.", "error")
                return redirect(url_for("tunnels_edit", tunnel_id=tunnel_id))
            try:
                db.execute(
                    """
                    UPDATE user_tunnels
                    SET name = ?, scheme = ?, host = ?, port = ?, enabled = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (name, scheme, host, int(port), enabled, _now(), tunnel_id, int(session["user_id"])),
                )
                db.commit()
                flash("Tunnel updated.", "success")
                return redirect(url_for("tunnels_list"))
            except sqlite3.IntegrityError:
                flash("Tunnel name already exists for this user.", "error")
                return redirect(url_for("tunnels_edit", tunnel_id=tunnel_id))

        tunnel = {
            "id": row["id"],
            "name": row["name"],
            "scheme": row["scheme"],
            "host": row["host"],
            "port": row["port"],
            "enabled": bool(row["enabled"]),
        }
        return render_template("tunnel_form.html", tunnel=tunnel)

    @app.route("/tunnels/<int:tunnel_id>/delete", methods=["POST"])
    @role_required("operator")
    def tunnels_delete(tunnel_id):
        db = get_db()
        chain_refs = db.execute(
            "SELECT COUNT(1) AS c FROM user_tunnel_chain_hops WHERE tunnel_id = ?",
            (int(tunnel_id),),
        ).fetchone()
        if chain_refs and int(chain_refs["c"] or 0) > 0:
            flash("Cannot delete tunnel because it is used by one or more tunnel chains.", "error")
            return redirect(url_for("tunnels_list"))
        db.execute(
            "DELETE FROM user_tunnels WHERE id = ? AND user_id = ?",
            (tunnel_id, int(session["user_id"])),
        )
        db.commit()
        flash("Tunnel deleted.", "success")
        return redirect(url_for("tunnels_list"))

    @app.route("/network-profiles/new", methods=["GET", "POST"])
    @role_required("operator")
    def network_profiles_new():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            proxy_url_raw = request.form.get("proxy_url", "").strip()
            ca_bundle_path = request.form.get("ca_bundle_path", "").strip()
            enabled = 1 if request.form.get("enabled") == "on" else 0
            if not name:
                flash("Profile name is required.", "error")
                return render_template("network_profile_form.html", profile=None)
            proxy_url = _normalize_proxy_url(proxy_url_raw)
            if proxy_url_raw and not proxy_url:
                flash("Invalid proxy URL. Use http(s)/socks5(s)://user:pass@host:port format.", "error")
                return render_template("network_profile_form.html", profile=None)
            db = get_db()
            try:
                db.execute(
                    """
                    INSERT INTO user_network_profiles
                    (user_id, name, proxy_url, ca_bundle_path, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(session["user_id"]),
                        name,
                        proxy_url or None,
                        ca_bundle_path or None,
                        enabled,
                        _now(),
                        _now(),
                    ),
                )
                db.commit()
                flash("Network profile saved.", "success")
                return redirect(url_for("tunnels_list"))
            except sqlite3.IntegrityError:
                flash("Network profile name already exists for this user.", "error")
        return render_template("network_profile_form.html", profile=None)

    @app.route("/network-profiles/<int:profile_id>/edit", methods=["GET", "POST"])
    @role_required("operator")
    def network_profiles_edit(profile_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM user_network_profiles WHERE id = ? AND user_id = ?",
            (profile_id, int(session["user_id"])),
        ).fetchone()
        if not row:
            flash("Network profile not found.", "error")
            return redirect(url_for("tunnels_list"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            proxy_url_raw = request.form.get("proxy_url", "").strip()
            ca_bundle_path = request.form.get("ca_bundle_path", "").strip()
            enabled = 1 if request.form.get("enabled") == "on" else 0
            if not name:
                flash("Profile name is required.", "error")
                return redirect(url_for("network_profiles_edit", profile_id=profile_id))
            proxy_url = _normalize_proxy_url(proxy_url_raw)
            if proxy_url_raw and not proxy_url:
                flash("Invalid proxy URL. Use http(s)/socks5(s)://user:pass@host:port format.", "error")
                return redirect(url_for("network_profiles_edit", profile_id=profile_id))
            try:
                db.execute(
                    """
                    UPDATE user_network_profiles
                    SET name = ?, proxy_url = ?, ca_bundle_path = ?, enabled = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (
                        name,
                        proxy_url or None,
                        ca_bundle_path or None,
                        enabled,
                        _now(),
                        profile_id,
                        int(session["user_id"]),
                    ),
                )
                db.commit()
                flash("Network profile updated.", "success")
                return redirect(url_for("tunnels_list"))
            except sqlite3.IntegrityError:
                flash("Network profile name already exists for this user.", "error")
                return redirect(url_for("network_profiles_edit", profile_id=profile_id))

        profile = {
            "id": row["id"],
            "name": row["name"],
            "proxy_url": row["proxy_url"] or "",
            "ca_bundle_path": row["ca_bundle_path"] or "",
            "enabled": bool(row["enabled"]),
        }
        return render_template("network_profile_form.html", profile=profile)

    @app.route("/network-profiles/<int:profile_id>/delete", methods=["POST"])
    @role_required("operator")
    def network_profiles_delete(profile_id):
        db = get_db()
        db.execute(
            """
            UPDATE runs
            SET network_profile_id = NULL, network_profile_label = NULL, network_proxy_url = NULL, network_ca_bundle_path = NULL
            WHERE user_id = ? AND status = 'queued' AND network_profile_id = ?
            """,
            (int(session["user_id"]), int(profile_id)),
        )
        db.execute(
            "DELETE FROM user_network_profiles WHERE id = ? AND user_id = ?",
            (profile_id, int(session["user_id"])),
        )
        db.commit()
        flash("Network profile deleted.", "success")
        return redirect(url_for("tunnels_list"))

    @app.route("/tunnel-chains/new", methods=["GET", "POST"])
    @role_required("operator")
    def tunnel_chains_new():
        db = get_db()
        user_id = int(session["user_id"])
        tunnels = _list_user_tunnels(db, user_id)
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            enabled = 1 if request.form.get("enabled") == "on" else 0
            hop_ids_raw = request.form.get("hop_tunnel_ids", "")
            hop_ids = [line.strip() for line in hop_ids_raw.splitlines() if line.strip()]
            if not name:
                flash("Chain name is required.", "error")
                return render_template("tunnel_chain_form.html", chain=None, tunnels=tunnels)
            if not hop_ids:
                flash("At least one hop is required.", "error")
                return render_template("tunnel_chain_form.html", chain=None, tunnels=tunnels)
            try:
                hop_ids = [int(x) for x in hop_ids]
            except ValueError:
                flash("Hop IDs must be numeric tunnel IDs.", "error")
                return render_template("tunnel_chain_form.html", chain=None, tunnels=tunnels)
            placeholders = ",".join(["?"] * len(hop_ids))
            rows = db.execute(
                f"""
                SELECT id
                FROM user_tunnels
                WHERE user_id = ? AND id IN ({placeholders})
                """,
                (user_id, *hop_ids),
            ).fetchall()
            existing_ids = {int(r["id"]) for r in rows}
            for hop_id in hop_ids:
                if hop_id not in existing_ids:
                    flash(f"Hop tunnel #{hop_id} is not valid for this user.", "error")
                    return render_template("tunnel_chain_form.html", chain=None, tunnels=tunnels)
            try:
                db.execute(
                    """
                    INSERT INTO user_tunnel_chains (user_id, name, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, name, enabled, _now(), _now()),
                )
                chain_id = int(db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
                for idx, hop_id in enumerate(hop_ids, start=1):
                    db.execute(
                        """
                        INSERT INTO user_tunnel_chain_hops (chain_id, hop_order, tunnel_id, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (chain_id, idx, hop_id, _now()),
                    )
                db.commit()
                flash("Tunnel chain saved.", "success")
                return redirect(url_for("tunnels_list"))
            except sqlite3.IntegrityError:
                flash("Tunnel chain name already exists for this user.", "error")
        return render_template("tunnel_chain_form.html", chain=None, tunnels=tunnels)

    @app.route("/tunnel-chains/<int:chain_id>/edit", methods=["GET", "POST"])
    @role_required("operator")
    def tunnel_chains_edit(chain_id):
        db = get_db()
        user_id = int(session["user_id"])
        chain = db.execute(
            """
            SELECT id, user_id, name, enabled
            FROM user_tunnel_chains
            WHERE id = ? AND user_id = ?
            """,
            (chain_id, user_id),
        ).fetchone()
        if not chain:
            flash("Tunnel chain not found.", "error")
            return redirect(url_for("tunnels_list"))
        tunnels = _list_user_tunnels(db, user_id)
        existing_hops = _list_chain_hops(db, user_id, chain_id)
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            enabled = 1 if request.form.get("enabled") == "on" else 0
            hop_ids_raw = request.form.get("hop_tunnel_ids", "")
            hop_ids = [line.strip() for line in hop_ids_raw.splitlines() if line.strip()]
            if not name:
                flash("Chain name is required.", "error")
                return redirect(url_for("tunnel_chains_edit", chain_id=chain_id))
            if not hop_ids:
                flash("At least one hop is required.", "error")
                return redirect(url_for("tunnel_chains_edit", chain_id=chain_id))
            try:
                hop_ids = [int(x) for x in hop_ids]
            except ValueError:
                flash("Hop IDs must be numeric tunnel IDs.", "error")
                return redirect(url_for("tunnel_chains_edit", chain_id=chain_id))
            placeholders = ",".join(["?"] * len(hop_ids))
            rows = db.execute(
                f"""
                SELECT id
                FROM user_tunnels
                WHERE user_id = ? AND id IN ({placeholders})
                """,
                (user_id, *hop_ids),
            ).fetchall()
            existing_ids = {int(r["id"]) for r in rows}
            for hop_id in hop_ids:
                if hop_id not in existing_ids:
                    flash(f"Hop tunnel #{hop_id} is not valid for this user.", "error")
                    return redirect(url_for("tunnel_chains_edit", chain_id=chain_id))
            try:
                db.execute(
                    """
                    UPDATE user_tunnel_chains
                    SET name = ?, enabled = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (name, enabled, _now(), chain_id, user_id),
                )
                db.execute("DELETE FROM user_tunnel_chain_hops WHERE chain_id = ?", (chain_id,))
                for idx, hop_id in enumerate(hop_ids, start=1):
                    db.execute(
                        """
                        INSERT INTO user_tunnel_chain_hops (chain_id, hop_order, tunnel_id, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (chain_id, idx, hop_id, _now()),
                    )
                db.commit()
                flash("Tunnel chain updated.", "success")
                return redirect(url_for("tunnels_list"))
            except sqlite3.IntegrityError:
                flash("Tunnel chain name already exists for this user.", "error")
                return redirect(url_for("tunnel_chains_edit", chain_id=chain_id))

        chain_obj = {
            "id": int(chain["id"]),
            "name": chain["name"],
            "enabled": bool(chain["enabled"]),
            "hop_tunnel_ids": "\n".join(str(h["tunnel_id"]) for h in existing_hops),
        }
        return render_template("tunnel_chain_form.html", chain=chain_obj, tunnels=tunnels)

    @app.route("/tunnel-chains/<int:chain_id>/delete", methods=["POST"])
    @role_required("operator")
    def tunnel_chains_delete(chain_id):
        db = get_db()
        user_id = int(session["user_id"])
        db.execute(
            """
            UPDATE runs
            SET tunnel_chain_id = NULL, tunnel_label = NULL, tunnel_url = NULL
            WHERE user_id = ? AND status = 'queued' AND tunnel_chain_id = ?
            """,
            (user_id, chain_id),
        )
        db.execute("DELETE FROM user_tunnel_chain_hops WHERE chain_id = ?", (chain_id,))
        db.execute("DELETE FROM user_tunnel_chains WHERE id = ? AND user_id = ?", (chain_id, user_id))
        db.commit()
        flash("Tunnel chain deleted.", "success")
        return redirect(url_for("tunnels_list"))

    @app.route("/users")
    @role_required("admin")
    def users_list():
        db = get_db()
        rows = db.execute(
            """
            SELECT
                u.id,
                u.username,
                u.role,
                u.created_at,
                (SELECT COUNT(1) FROM runs r WHERE r.user_id = u.id) AS runs_count
            FROM users u
            ORDER BY u.username
            """
        ).fetchall()
        return render_template("users.html", users=rows)

    @app.route("/users/new", methods=["GET", "POST"])
    @role_required("admin")
    def users_new():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            role = request.form.get("role", "operator").strip().lower()
            if not username:
                flash("Username is required.", "error")
                return render_template("user_form.html", user=None)
            if role not in ("admin", "operator", "viewer"):
                flash("Invalid role selected.", "error")
                return render_template("user_form.html", user=None)
            if len(password) < 8:
                flash("Password must have at least 8 characters.", "error")
                return render_template("user_form.html", user=None)

            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, role, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (username, role, generate_password_hash(password), _now()),
                )
                db.commit()
                flash("User created.", "success")
                return redirect(url_for("users_list"))
            except sqlite3.IntegrityError:
                flash("Username already exists.", "error")
        return render_template("user_form.html", user=None)

    @app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
    @role_required("admin")
    def users_edit(user_id):
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("users_list"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            role = request.form.get("role", "operator").strip().lower()
            password = request.form.get("password", "")
            if not username:
                flash("Username is required.", "error")
                return redirect(url_for("users_edit", user_id=user_id))
            if role not in ("admin", "operator", "viewer"):
                flash("Invalid role selected.", "error")
                return redirect(url_for("users_edit", user_id=user_id))

            current_is_admin = (user["role"] == "admin")
            target_is_admin = (role == "admin")
            admin_count = db.execute(
                "SELECT COUNT(1) AS c FROM users WHERE role = 'admin'"
            ).fetchone()["c"]
            if current_is_admin and not target_is_admin and int(admin_count) <= 1:
                flash("At least one admin account must remain.", "error")
                return redirect(url_for("users_edit", user_id=user_id))

            try:
                if password:
                    if len(password) < 8:
                        flash("Password must have at least 8 characters.", "error")
                        return redirect(url_for("users_edit", user_id=user_id))
                    db.execute(
                        """
                        UPDATE users
                        SET username = ?, role = ?, password_hash = ?
                        WHERE id = ?
                        """,
                        (username, role, generate_password_hash(password), user_id),
                    )
                else:
                    db.execute(
                        """
                        UPDATE users
                        SET username = ?, role = ?
                        WHERE id = ?
                        """,
                        (username, role, user_id),
                    )
                db.commit()
                flash("User updated.", "success")
                return redirect(url_for("users_list"))
            except sqlite3.IntegrityError:
                flash("Username already exists.", "error")

        user_obj = {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        }
        return render_template("user_form.html", user=user_obj)

    @app.route("/users/<int:user_id>/delete", methods=["POST"])
    @role_required("admin")
    def users_delete(user_id):
        db = get_db()
        user = db.execute("SELECT id, role, username FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("users_list"))
        if int(user["id"]) == int(session["user_id"]):
            flash("You cannot delete your own account.", "error")
            return redirect(url_for("users_list"))
        if user["role"] == "admin":
            admin_count = db.execute("SELECT COUNT(1) AS c FROM users WHERE role = 'admin'").fetchone()["c"]
            if int(admin_count) <= 1:
                flash("Cannot delete the last admin account.", "error")
                return redirect(url_for("users_list"))
        runs_count = db.execute("SELECT COUNT(1) AS c FROM runs WHERE user_id = ?", (user_id,)).fetchone()["c"]
        if int(runs_count) > 0:
            flash("Cannot delete a user that still has run history. Reassign or clear runs first.", "error")
            return redirect(url_for("users_list"))

        db.execute("DELETE FROM user_credentials WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM user_active_credentials WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        flash(f"User {user['username']} deleted.", "success")
        return redirect(url_for("users_list"))

    @app.route("/admin/credentials")
    @role_required("admin")
    def admin_credentials():
        db = get_db()
        credentials = db.execute(
            """
            SELECT
                c.id,
                c.name,
                c.created_at,
                c.updated_at,
                c.owner_user_id,
                u.username AS owner_username
            FROM credentials c
            LEFT JOIN users u ON u.id = c.owner_user_id
            ORDER BY c.name
            """
        ).fetchall()
        operators = db.execute(
            """
            SELECT id, username
            FROM users
            WHERE role = 'operator'
            ORDER BY username
            """
        ).fetchall()
        return render_template("admin_credentials.html", credentials=credentials, operators=operators)

    @app.route("/admin/credentials/<int:credential_id>/owner", methods=["POST"])
    @role_required("admin")
    def admin_credentials_change_owner(credential_id):
        target_owner_id = request.form.get("owner_user_id", "").strip()
        if not target_owner_id:
            flash("Select an operator to assign ownership.", "error")
            return redirect(url_for("admin_credentials"))
        try:
            target_owner_id = int(target_owner_id)
        except ValueError:
            flash("Invalid owner selected.", "error")
            return redirect(url_for("admin_credentials"))

        db = get_db()
        credential = db.execute(
            "SELECT id, name FROM credentials WHERE id = ?",
            (credential_id,),
        ).fetchone()
        if not credential:
            flash("Credential not found.", "error")
            return redirect(url_for("admin_credentials"))

        target_owner = db.execute(
            "SELECT id, username FROM users WHERE id = ? AND role = 'operator'",
            (target_owner_id,),
        ).fetchone()
        if not target_owner:
            flash("Selected user is not a valid operator.", "error")
            return redirect(url_for("admin_credentials"))

        db.execute(
            "UPDATE credentials SET owner_user_id = ?, updated_at = ? WHERE id = ?",
            (target_owner_id, _now(), credential_id),
        )
        db.execute("DELETE FROM user_credentials WHERE credential_id = ?", (credential_id,))
        db.execute(
            """
            INSERT OR IGNORE INTO user_credentials (user_id, credential_id, created_at)
            VALUES (?, ?, ?)
            """,
            (target_owner_id, credential_id, _now()),
        )
        db.commit()
        flash(
            f"Credential '{credential['name']}' ownership transferred to operator '{target_owner['username']}'.",
            "success",
        )
        return redirect(url_for("admin_credentials"))

    @app.route("/runs/new", methods=["POST"])
    @role_required("operator")
    def runs_new():
        module_path = request.form.get("module_path", "").strip()
        credential_id = request.form.get("credential_id", "").strip()
        selected_tunnel_value = request.form.get("tunnel_id", "").strip()
        selected_network_profile_id = request.form.get("network_profile_id", "").strip()
        input_values_text = request.form.get("input_values", "").strip()
        selected_region = request.form.get("selected_region", "").strip()
        depends_on_run_ids = [v.strip() for v in request.form.getlist("depends_on_run_ids") if v.strip()]

        if "/" not in module_path:
            flash("Invalid module selection.", "error")
            return redirect(url_for("dashboard"))
        db = get_db()
        user_id = int(session["user_id"])
        if not credential_id:
            active_ctx = _get_active_credential_context(db, user_id, _current_role())
            if active_ctx:
                credential_id = str(active_ctx["credential_id"])
            else:
                flash("Select a credential first.", "error")
                return redirect(url_for("dashboard"))
        try:
            credential_id_value = int(credential_id)
        except ValueError:
            flash("Invalid credential selection.", "error")
            return redirect(url_for("dashboard"))
        if not _credential_accessible(db, user_id, _current_role(), credential_id_value):
            flash("You do not have access to selected credential.", "error")
            return redirect(url_for("dashboard"))

        tunnel_id_value = None
        tunnel_chain_id_value = None
        tunnel_label = None
        tunnel_url = None
        network_profile_id_value = None
        network_profile_label = None
        network_proxy_url = None
        network_ca_bundle_path = None
        if selected_tunnel_value:
            selected_mode = "legacy"
            selected_id = selected_tunnel_value
            if ":" in selected_tunnel_value:
                selected_mode, selected_id = selected_tunnel_value.split(":", 1)
            try:
                selected_id_value = int(selected_id)
            except ValueError:
                flash("Invalid tunnel selection.", "error")
                return redirect(url_for("dashboard"))

            if selected_mode in ("legacy", "t"):
                tunnel_id_value = selected_id_value
                tunnel_row = db.execute(
                    """
                    SELECT id, name, scheme, host, port, enabled
                    FROM user_tunnels
                    WHERE id = ? AND user_id = ?
                    """,
                    (tunnel_id_value, int(session["user_id"])),
                ).fetchone()
                if not tunnel_row:
                    flash("Selected tunnel was not found.", "error")
                    return redirect(url_for("dashboard"))
                if int(tunnel_row["enabled"] or 0) != 1:
                    flash("Selected tunnel is disabled.", "error")
                    return redirect(url_for("dashboard"))
                tunnel_url = _build_tunnel_url(tunnel_row["scheme"], tunnel_row["host"], tunnel_row["port"])
                if not tunnel_url:
                    flash("Selected tunnel has invalid configuration.", "error")
                    return redirect(url_for("dashboard"))
                tunnel_label = tunnel_row["name"]
            elif selected_mode == "c":
                tunnel_chain_id_value = selected_id_value
                chain_row = db.execute(
                    """
                    SELECT id, name, enabled
                    FROM user_tunnel_chains
                    WHERE id = ? AND user_id = ?
                    """,
                    (tunnel_chain_id_value, int(session["user_id"])),
                ).fetchone()
                if not chain_row:
                    flash("Selected tunnel chain was not found.", "error")
                    return redirect(url_for("dashboard"))
                if int(chain_row["enabled"] or 0) != 1:
                    flash("Selected tunnel chain is disabled.", "error")
                    return redirect(url_for("dashboard"))
                hops = _list_chain_hops(db, int(session["user_id"]), tunnel_chain_id_value)
                if not hops:
                    flash("Selected tunnel chain has no hops.", "error")
                    return redirect(url_for("dashboard"))
                chain_hops = []
                for hop in hops:
                    if int(hop["enabled"] or 0) != 1:
                        flash(f"Tunnel chain hop '{hop['name']}' is disabled.", "error")
                        return redirect(url_for("dashboard"))
                    hop_url = _build_tunnel_url(hop["scheme"], hop["host"], hop["port"])
                    if not hop_url:
                        flash(f"Tunnel chain hop '{hop['name']}' is invalid.", "error")
                        return redirect(url_for("dashboard"))
                    chain_hops.append(
                        {
                            "tunnel_id": int(hop["tunnel_id"]),
                            "name": hop["name"],
                            "scheme": hop["scheme"],
                            "host": hop["host"],
                            "port": int(hop["port"]),
                        }
                    )
                tunnel_label = f"{chain_row['name']} [chain]"
                tunnel_url = "chain_json:" + json.dumps(chain_hops)
            else:
                flash("Unsupported tunnel selection mode.", "error")
                return redirect(url_for("dashboard"))

        if selected_network_profile_id:
            try:
                network_profile_id_value = int(selected_network_profile_id)
            except ValueError:
                flash("Invalid network profile selection.", "error")
                return redirect(url_for("dashboard"))
            profile_row = db.execute(
                """
                SELECT id, name, proxy_url, ca_bundle_path, enabled
                FROM user_network_profiles
                WHERE id = ? AND user_id = ?
                """,
                (network_profile_id_value, int(session["user_id"])),
            ).fetchone()
            if not profile_row:
                flash("Selected network profile was not found.", "error")
                return redirect(url_for("dashboard"))
            if int(profile_row["enabled"] or 0) != 1:
                flash("Selected network profile is disabled.", "error")
                return redirect(url_for("dashboard"))
            network_profile_label = profile_row["name"]
            network_proxy_url = (profile_row["proxy_url"] or "").strip() or None
            network_ca_bundle_path = (profile_row["ca_bundle_path"] or "").strip() or None

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
                if _current_role() != "admin" and int(dependency_run["user_id"]) != int(session["user_id"]):
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
                if int(dependency_run["credential_id"]) != credential_id_value:
                    flash(f"Dependency run #{dependency_id} credential must match selected credential.", "error")
                    return redirect(url_for("dashboard"))
            if dependency_mode == "multiple":
                missing_dependencies = [dep for dep in module_dependencies if dep not in selected_dependency_modules]
                if missing_dependencies:
                    flash("Selected dependency runs do not cover all required dependency modules.", "error")
                    return redirect(url_for("dashboard"))

        run_cursor = db.execute(
            """
            INSERT INTO runs
            (user_id, module_category, module_name, credential_id, tunnel_id, tunnel_chain_id, tunnel_label, tunnel_url, network_profile_id, network_profile_label, network_proxy_url, network_ca_bundle_path, depends_on_run_id, cancel_requested, input_values_json, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                category,
                name,
                credential_id_value,
                tunnel_id_value,
                tunnel_chain_id_value,
                tunnel_label,
                tunnel_url,
                network_profile_id_value,
                network_profile_label,
                network_proxy_url,
                network_ca_bundle_path,
                dependency_id_values[0] if dependency_id_values else None,
                0,
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
        _set_active_credential(
            db,
            user_id,
            credential_id_value,
            source="manual",
            source_run_id=run_id,
        )
        db.commit()

        flash(f"Run #{run_id} queued.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/runs/<int:run_id>")
    @role_required("operator", "viewer")
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
        if not _can_view_all_runs(_current_role()) and int(run["user_id"]) != int(session["user_id"]):
            flash("You do not have access to this run.", "error")
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
        run_findings = db.execute(
            """
            SELECT
                id,
                severity,
                category,
                title,
                resource_type,
                resource_id,
                description,
                details_json,
                created_at
            FROM findings
            WHERE run_id = ?
            ORDER BY id DESC
            LIMIT 500
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
            run_findings=run_findings,
            result_obj=result_obj,
            presenter=presenter,
        )

    @app.route("/runs/<int:run_id>/export.json")
    @role_required("operator", "viewer")
    def run_export_json(run_id):
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
        if not _can_view_all_runs(_current_role()) and int(run["user_id"]) != int(session["user_id"]):
            flash("You do not have access to this run.", "error")
            return redirect(url_for("dashboard"))

        dependencies = db.execute(
            """
            SELECT r.id, r.module_category, r.module_name, r.status
            FROM run_dependencies d
            JOIN runs r ON r.id = d.depends_on_run_id
            WHERE d.run_id = ?
            ORDER BY r.id DESC
            """,
            (run_id,),
        ).fetchall()
        findings = db.execute(
            """
            SELECT severity, category, title, resource_type, resource_id, description, details_json, created_at
            FROM findings
            WHERE run_id = ?
            ORDER BY id DESC
            """,
            (run_id,),
        ).fetchall()
        payload = {
            "run": {
                "id": run["id"],
                "operator": run["username"],
                "credential": run["credential_name"],
                "module_path": f"{run['module_category']}/{run['module_name']}",
                "tunnel_label": run["tunnel_label"],
                "tunnel_url": run["tunnel_url"],
                "status": run["status"],
                "created_at": run["created_at"],
                "started_at": run["started_at"],
                "finished_at": run["finished_at"],
                "api_calls": run["api_calls"],
                "timeout_seconds": run["timeout_seconds"],
                "max_api_calls": run["max_api_calls"],
            },
            "dependencies": [dict(d) for d in dependencies],
            "result": _parse_json_or_empty(run["result_json"]),
            "findings": [
                {
                    **dict(f),
                    "details": _parse_json_or_empty(f["details_json"]),
                }
                for f in findings
            ],
        }
        content = json.dumps(payload, default=str, indent=2)
        filename = f"run_{run_id}.json"
        return Response(
            content,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @app.route("/reports/engagement.json")
    @role_required("operator", "viewer")
    def engagement_report_json():
        db = get_db()
        role = _current_role()
        user_id = int(session["user_id"])
        if _can_view_all_runs(role):
            runs = db.execute(
                """
                SELECT r.id, r.user_id, u.username, c.name AS credential_name, r.module_category, r.module_name, r.tunnel_label, r.status, r.created_at
                FROM runs r
                JOIN users u ON u.id = r.user_id
                JOIN credentials c ON c.id = r.credential_id
                ORDER BY r.id DESC
                LIMIT 1000
                """
            ).fetchall()
            findings = db.execute(
                """
                SELECT run_id, severity, category, title, resource_type, resource_id, description, created_at
                FROM findings
                ORDER BY id DESC
                LIMIT 5000
                """
            ).fetchall()
        else:
            runs = db.execute(
                """
                SELECT r.id, r.user_id, u.username, c.name AS credential_name, r.module_category, r.module_name, r.tunnel_label, r.status, r.created_at
                FROM runs r
                JOIN users u ON u.id = r.user_id
                JOIN credentials c ON c.id = r.credential_id
                WHERE r.user_id = ?
                ORDER BY r.id DESC
                LIMIT 1000
                """,
                (user_id,),
            ).fetchall()
            findings = db.execute(
                """
                SELECT run_id, severity, category, title, resource_type, resource_id, description, created_at
                FROM findings
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 5000
                """,
                (user_id,),
            ).fetchall()

        severity_counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            sev = (f["severity"] or "info").lower()
            if sev not in severity_counts:
                severity_counts[sev] = 0
            severity_counts[sev] += 1

        payload = {
            "generated_at": _now(),
            "scope": "global" if _can_view_all_runs(role) else f"user:{user_id}",
            "summary": {
                "runs_count": len(runs),
                "findings_count": len(findings),
                "severity_counts": severity_counts,
            },
            "runs": [dict(r) for r in runs],
            "findings": [dict(f) for f in findings],
        }
        content = json.dumps(payload, default=str, indent=2)
        return Response(
            content,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=engagement_report.json"},
        )

    @app.route("/reports/engagement.txt")
    @role_required("operator", "viewer")
    def engagement_report_txt():
        db = get_db()
        role = _current_role()
        user_id = int(session["user_id"])
        if _can_view_all_runs(role):
            rows = db.execute(
                """
                SELECT severity, category, title, resource_type, resource_id, run_id
                FROM findings
                ORDER BY id DESC
                LIMIT 2000
                """
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT severity, category, title, resource_type, resource_id, run_id
                FROM findings
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 2000
                """,
                (user_id,),
            ).fetchall()

        lines = [
            "Kintoun Engagement Report",
            f"Generated At: {_now()}",
            f"Scope: {'global' if _can_view_all_runs(role) else f'user:{user_id}'}",
            "",
            "Findings:",
        ]
        for row in rows:
            lines.append(
                f"[{(row['severity'] or 'info').upper()}] {row['title']} | "
                f"category={row['category']} | resource={row['resource_type']}/{row['resource_id']} | run=#{row['run_id']}"
            )
        content = "\n".join(lines)
        return Response(
            content,
            mimetype="text/plain",
            headers={"Content-Disposition": "attachment; filename=engagement_report.txt"},
        )

    @app.route("/runs/<int:run_id>/delete", methods=["POST"])
    @role_required("operator")
    def run_delete(run_id):
        db = get_db()
        run = db.execute("SELECT user_id FROM runs WHERE id = ?", (run_id,)).fetchone()
        if run and _current_role() != "admin" and int(run["user_id"]) != int(session["user_id"]):
            flash("You do not have permission to delete this run.", "error")
            return redirect(url_for("dashboard"))
        db.execute("DELETE FROM findings WHERE run_id = ?", (run_id,))
        db.execute("DELETE FROM run_dependencies WHERE run_id = ? OR depends_on_run_id = ?", (run_id, run_id))
        db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        db.commit()
        flash(f"Run #{run_id} deleted.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/runs/<int:run_id>/cancel", methods=["POST"])
    @role_required("operator")
    def run_cancel(run_id):
        db = get_db()
        run = db.execute(
            "SELECT id, user_id, status FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if not run:
            flash("Run not found.", "error")
            return redirect(url_for("dashboard"))
        if _current_role() != "admin" and int(run["user_id"]) != int(session["user_id"]):
            flash("You cannot cancel runs from another operator.", "error")
            return redirect(url_for("dashboard"))
        if run["status"] in ("completed", "failed", "timed_out", "canceled"):
            flash(f"Run #{run_id} is already finished.", "error")
            return redirect(url_for("dashboard"))

        if run["status"] == "queued":
            db.execute(
                """
                UPDATE runs
                SET status = 'canceled', cancel_requested = 1, canceled_at = ?, finished_at = ?
                WHERE id = ?
                """,
                (_now(), _now(), run_id),
            )
            db.commit()
            flash(f"Run #{run_id} canceled.", "success")
            return redirect(url_for("dashboard"))

        db.execute(
            "UPDATE runs SET cancel_requested = 1, canceled_at = ? WHERE id = ?",
            (_now(), run_id),
        )
        db.commit()
        flash(f"Cancel requested for run #{run_id}. It will stop at the next AWS API call.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/runs/clear", methods=["POST"])
    @role_required("admin")
    def runs_clear():
        db = get_db()
        in_progress = db.execute(
            "SELECT COUNT(1) AS c FROM runs WHERE status IN ('queued', 'running')"
        ).fetchone()
        if in_progress and in_progress["c"] > 0:
            flash("Cannot clear runs while executions are queued or running.", "error")
            return redirect(url_for("dashboard"))

        deleted = db.execute("SELECT COUNT(1) AS c FROM runs").fetchone()
        db.execute("DELETE FROM findings")
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
    start_queue_dispatcher()

    return app


app = create_app()
