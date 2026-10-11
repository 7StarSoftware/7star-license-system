import os
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "")

app = Flask(__name__)
app.secret_key = SECRET_KEY or os.urandom(32)

def db_connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is missing")
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(DATABASE_URL, sslmode="require", row_factory=dict_row)

def init_db():
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS public.licenses (
                device_id TEXT PRIMARY KEY,
                license_code TEXT NOT NULL DEFAULT '7STAR',
                plan TEXT NOT NULL DEFAULT 'Gold',
                plan_id INTEGER NOT NULL DEFAULT 81,
                status INTEGER NOT NULL DEFAULT 1,
                expiry_date DATE NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                plan_type INTEGER NOT NULL DEFAULT 2,
                notes TEXT NOT NULL DEFAULT ''
            )
        """)

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_ok"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.get("/")
def home():
    return redirect(url_for("dashboard" if session.get("admin_ok") else "login"))

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if not ADMIN_PASSWORD:
        return render_template("setup_error.html"), 503
    if request.method == "POST":
        if request.form.get("password", "") == ADMIN_PASSWORD:
            session["admin_ok"] = True
            return redirect(url_for("dashboard"))
        flash("Password ghalat hai.", "error")
    return render_template("login.html")

@app.get("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/admin")
@admin_required
def dashboard():
    with db_connect() as conn:
        rows = conn.execute("SELECT * FROM public.licenses ORDER BY created_at DESC").fetchall()
    return render_template("dashboard.html", licenses=rows)

@app.post("/admin/save")
@admin_required
def save_license():
    device_id = request.form.get("device_id", "").strip()
    expiry_date = request.form.get("expiry_date", "").strip()[:10]
    license_code = request.form.get("license_code", "7STAR").strip() or "7STAR"
    plan = request.form.get("plan", "Gold").strip() or "Gold"
    notes = request.form.get("notes", "").strip()
    action = request.form.get("action", "save")
    if not device_id or not expiry_date:
        flash("Device ID aur expiry date lazmi hain.", "error")
        return redirect(url_for("dashboard"))
    try:
        datetime.strptime(expiry_date, "%Y-%m-%d")
    except ValueError:
        flash("Expiry date ka format durust nahi.", "error")
        return redirect(url_for("dashboard"))
    status = 2 if action == "activate" else 3 if action == "deactivate" else int(request.form.get("status", "2"))
    with db_connect() as conn:
        conn.execute("""
            INSERT INTO public.licenses(device_id, license_code, plan, plan_id, status, expiry_date, created_at, plan_type, notes)
            VALUES (%s, %s, %s, 81, %s, %s, NOW(), 2, %s)
            ON CONFLICT(device_id) DO UPDATE SET
                license_code=EXCLUDED.license_code,
                plan=EXCLUDED.plan,
                status=EXCLUDED.status,
                expiry_date=EXCLUDED.expiry_date,
                notes=EXCLUDED.notes
        """, (device_id, license_code, plan, status, expiry_date, notes))
    flash("License save/update ho gaya.", "success")
    return redirect(url_for("dashboard"))

@app.post("/admin/status/<path:device_id>")
@admin_required
def change_status(device_id):
    status = 2 if request.form.get("status") == "2" else 3
    with db_connect() as conn:
        conn.execute("UPDATE public.licenses SET status=%s WHERE device_id=%s", (status, device_id))
    flash("License status update ho gaya.", "success")
    return redirect(url_for("dashboard"))

@app.post("/admin/delete/<path:device_id>")
@admin_required
def delete_license(device_id):
    with db_connect() as conn:
        conn.execute("DELETE FROM public.licenses WHERE device_id=%s", (device_id,))
    flash("License delete ho gaya.", "success")
    return redirect(url_for("dashboard"))

def license_payload(device_id):
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM public.licenses WHERE device_id=%s", (device_id,)).fetchone()
    current = now_text()
    if not row:
        return {
            "license_code": "", "expiry_date": "", "plan": "", "planId": 81,
            "status": 1, "created_at": current, "current_date": current,
            "groupTitle": None, "planType": 2, "perDayCost": 0,
            "perDayCostUsd": 0, "pairExpiryDate": ""
        }
    expiry = row["expiry_date"].isoformat() if hasattr(row["expiry_date"], "isoformat") else str(row["expiry_date"])
    created = row["created_at"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(row["created_at"], "strftime") else str(row["created_at"])
    return {
        "license_code": row["license_code"], "expiry_date": expiry,
        "plan": row["plan"], "planId": row["plan_id"], "status": row["status"],
        "created_at": created, "current_date": current, "groupTitle": None,
        "planType": row["plan_type"], "perDayCost": 0, "perDayCostUsd": 0,
        "pairExpiryDate": expiry
    }

@app.get("/api/ns/license/<path:device_id>")
def api_ns_license(device_id):
    return jsonify(license_payload(device_id))

@app.get("/api/license/<path:device_id>")
def api_license(device_id):
    return jsonify(license_payload(device_id))

@app.get("/health")
def health():
    try:
        with db_connect() as conn:
            conn.execute("SELECT 1")
        return jsonify({"ok": True, "service": "7Star License API", "database": "connected"})
    except Exception:
        app.logger.exception("Health check failed")
        return jsonify({"ok": False, "service": "7Star License API", "error": "Database connection failed"}), 500

try:
    init_db()
except Exception:
    app.logger.exception("Database initialization failed; check DATABASE_URL and database access")

