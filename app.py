import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("LICENSE_DB_PATH", os.path.join(APP_DIR, "licenses.db"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "")

app = Flask(__name__)
app.secret_key = SECRET_KEY or os.urandom(32)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                device_id TEXT PRIMARY KEY,
                license_code TEXT NOT NULL DEFAULT '7STAR',
                plan TEXT NOT NULL DEFAULT 'Gold',
                plan_id INTEGER NOT NULL DEFAULT 81,
                status INTEGER NOT NULL DEFAULT 1,
                expiry_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
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
    if session.get("admin_ok"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

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
    with db() as conn:
        rows = conn.execute("SELECT * FROM licenses ORDER BY created_at DESC").fetchall()
    return render_template("dashboard.html", licenses=rows, now=now_text())

@app.route("/admin/save", methods=["POST"])
@admin_required
def save_license():
    device_id = request.form.get("device_id", "").strip()
    expiry_date = request.form.get("expiry_date", "").strip()
    license_code = request.form.get("license_code", "7STAR").strip() or "7STAR"
    plan = request.form.get("plan", "Gold").strip() or "Gold"
    notes = request.form.get("notes", "").strip()
    action = request.form.get("action", "save")
    if not device_id or not expiry_date:
        flash("Device ID aur expiry date lazmi hain.", "error")
        return redirect(url_for("dashboard"))
    try:
        # HTML date input is YYYY-MM-DD; normalize to the API's expected datetime.
        datetime.strptime(expiry_date[:10], "%Y-%m-%d")
        expiry_date = expiry_date[:10] + " 23:59:59"
    except ValueError:
        flash("Expiry date ka format durust nahi.", "error")
        return redirect(url_for("dashboard"))
    status = 2 if action == "activate" else 3 if action == "deactivate" else int(request.form.get("status", "2"))
    with db() as conn:
        existing = conn.execute("SELECT created_at FROM licenses WHERE device_id=?", (device_id,)).fetchone()
        created = existing["created_at"] if existing else now_text()
        conn.execute("""
            INSERT INTO licenses(device_id, license_code, plan, plan_id, status, expiry_date, created_at, plan_type, notes)
            VALUES (?, ?, ?, 81, ?, ?, ?, 2, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                license_code=excluded.license_code,
                plan=excluded.plan,
                status=excluded.status,
                expiry_date=excluded.expiry_date,
                notes=excluded.notes
        """, (device_id, license_code, plan, status, expiry_date, created, notes))
    flash("License save/update ho gaya.", "success")
    return redirect(url_for("dashboard"))

@app.post("/admin/status/<device_id>")
@admin_required
def change_status(device_id):
    status = 2 if request.form.get("status") == "2" else 3
    with db() as conn:
        conn.execute("UPDATE licenses SET status=? WHERE device_id=?", (status, device_id))
    flash("License status update ho gaya.", "success")
    return redirect(url_for("dashboard"))

@app.post("/admin/delete/<device_id>")
@admin_required
def delete_license(device_id):
    with db() as conn:
        conn.execute("DELETE FROM licenses WHERE device_id=?", (device_id,))
    flash("License delete ho gaya.", "success")
    return redirect(url_for("dashboard"))

def license_payload(device_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM licenses WHERE device_id=?", (device_id,)).fetchone()
    current = now_text()
    if not row:
        return {
            "license_code": "", "expiry_date": "", "plan": "", "planId": 81,
            "status": 1, "created_at": current, "current_date": current,
            "groupTitle": None, "planType": 2, "perDayCost": 0,
            "perDayCostUsd": 0, "pairExpiryDate": ""
        }
    return {
        "license_code": row["license_code"],
        "expiry_date": row["expiry_date"],
        "plan": row["plan"],
        "planId": row["plan_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "current_date": current,
        "groupTitle": None,
        "planType": row["plan_type"],
        "perDayCost": 0,
        "perDayCostUsd": 0,
        "pairExpiryDate": row["expiry_date"]
    }

@app.get("/api/ns/license/<path:device_id>")
def api_ns_license(device_id):
    return jsonify(license_payload(device_id))

@app.get("/api/license/<path:device_id>")
def api_license(device_id):
    return jsonify(license_payload(device_id))

@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "7Star License API"})

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
