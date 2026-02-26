from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
import hashlib
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow React frontend to call this backend

DB_PATH = "ncbw.db"

# ─────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'trainee',
            selected_track TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            track_id TEXT NOT NULL,
            module_index INTEGER NOT NULL,
            course_index INTEGER,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            quiz_score REAL,
            quiz_passed INTEGER DEFAULT 0,
            quiz_attempts INTEGER DEFAULT 0,
            UNIQUE(user_id, track_id, module_index, course_index)
        )
    """)

    # Create default admin if no users exist
    existing = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing == 0:
        admin_id = str(uuid.uuid4())
        c.execute("""
            INSERT INTO users (id, email, password, first_name, last_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (admin_id, "admin@nc100bw.org", hash_password("Admin@1234"),
              "Admin", "User", "admin", datetime.now().isoformat()))
        print("✅ Default admin created: admin@nc100bw.org / Admin@1234")

    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_from_token(token):
    conn = get_db()
    session = conn.execute(
        "SELECT user_id FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    if not session:
        conn.close()
        return None
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    conn.close()
    return dict(user) if user else None

# ─────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────

@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    first_name = data.get("firstName", "")
    last_name = data.get("lastName", "")
    role = data.get("role", "trainee")

    if not all([email, password, first_name, last_name]):
        return jsonify({"success": False, "error": "All fields are required"}), 400

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"success": False, "error": "Email already in use"}), 400

    user_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO users (id, email, password, first_name, last_name, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, email, hash_password(password), first_name, last_name, role,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Account created successfully"})


@app.route("/api/auth/signin", methods=["POST"])
def signin():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ? AND password = ?",
        (email, hash_password(password))
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"success": False, "error": "Invalid email or password"}), 401

    user = dict(user)
    token = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user["id"], datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "accessToken": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "firstName": user["first_name"],
            "lastName": user["last_name"],
            "role": user["role"],
            "selectedTrack": user["selected_track"],
        }
    })


@app.route("/api/auth/user", methods=["GET"])
def get_user():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_from_token(token)
    if not user:
        return jsonify({"success": False, "error": "Invalid token"}), 401

    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "firstName": user["first_name"],
            "lastName": user["last_name"],
            "role": user["role"],
            "selectedTrack": user["selected_track"],
        }
    })


@app.route("/api/auth/signout", methods=["POST"])
def signout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ─────────────────────────────────────────
# TRACK ROUTES
# ─────────────────────────────────────────

@app.route("/api/track/select", methods=["POST"])
def select_track():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_from_token(token)
    if not user:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.json
    track_id = data.get("trackId")
    if not track_id:
        return jsonify({"success": False, "error": "trackId is required"}), 400

    conn = get_db()
    conn.execute(
        "UPDATE users SET selected_track = ? WHERE id = ?",
        (track_id, user["id"])
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "trackId": track_id})


@app.route("/api/track", methods=["GET"])
def get_track():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_from_token(token)
    if not user:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    return jsonify({"success": True, "trackId": user["selected_track"]})

# ─────────────────────────────────────────
# PROGRESS ROUTES
# ─────────────────────────────────────────

@app.route("/api/progress/<track_id>", methods=["GET"])
def get_progress(track_id):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_from_token(token)
    if not user:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM progress WHERE user_id = ? AND track_id = ?",
        (user["id"], track_id)
    ).fetchall()
    conn.close()

    # Build modules dict
    modules = {}
    total_courses = 0
    completed_courses = 0

    for row in rows:
        row = dict(row)
        m = row["module_index"]
        c = row["course_index"]

        if m not in modules:
            modules[m] = {"completed": False, "courses": {}, "quizPassed": False,
                          "quizScore": None, "quizAttempts": 0}

        if c is not None:
            total_courses += 1
            if row["completed"]:
                completed_courses += 1
            modules[m]["courses"][c] = {
                "completed": bool(row["completed"]),
                "completedAt": row["completed_at"]
            }
        else:
            # quiz row
            modules[m]["quizPassed"] = bool(row["quiz_passed"])
            modules[m]["quizScore"] = row["quiz_score"]
            modules[m]["quizAttempts"] = row["quiz_attempts"]

    overall = int((completed_courses / total_courses * 100)) if total_courses > 0 else 0

    return jsonify({
        "success": True,
        "progress": {
            "modules": modules,
            "overallProgress": overall
        }
    })


@app.route("/api/progress/course", methods=["POST"])
def mark_course_complete():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_from_token(token)
    if not user:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.json
    track_id = data.get("trackId")
    module_index = data.get("moduleIndex")
    course_index = data.get("courseIndex")

    conn = get_db()
    conn.execute("""
        INSERT INTO progress (user_id, track_id, module_index, course_index, completed, completed_at)
        VALUES (?, ?, ?, ?, 1, ?)
        ON CONFLICT(user_id, track_id, module_index, course_index)
        DO UPDATE SET completed = 1, completed_at = ?
    """, (user["id"], track_id, module_index, course_index,
          datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()

    return jsonify({"success": True})


@app.route("/api/progress/quiz", methods=["POST"])
def submit_quiz():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_from_token(token)
    if not user:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.json
    track_id = data.get("trackId")
    module_index = data.get("moduleIndex")
    score = data.get("score", 0)
    passed = score >= 70

    conn = get_db()
    conn.execute("""
        INSERT INTO progress (user_id, track_id, module_index, course_index, quiz_score, quiz_passed, quiz_attempts)
        VALUES (?, ?, ?, NULL, ?, ?, 1)
        ON CONFLICT(user_id, track_id, module_index, course_index)
        DO UPDATE SET
            quiz_score = MAX(quiz_score, ?),
            quiz_passed = MAX(quiz_passed, ?),
            quiz_attempts = quiz_attempts + 1
    """, (user["id"], track_id, module_index, score, int(passed), score, int(passed)))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "passed": passed, "score": score})

# ─────────────────────────────────────────
# ADMIN ROUTES
# ─────────────────────────────────────────

@app.route("/api/admin/users", methods=["GET"])
def admin_get_users():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_from_token(token)
    if not user or user["role"] != "admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()

    return jsonify({
        "success": True,
        "users": [{
            "id": u["id"],
            "email": u["email"],
            "firstName": u["first_name"],
            "lastName": u["last_name"],
            "role": u["role"],
            "selectedTrack": u["selected_track"],
            "createdAt": u["created_at"]
        } for u in users]
    })


@app.route("/api/admin/reports", methods=["GET"])
def admin_get_reports():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_from_token(token)
    if not user or user["role"] != "admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    conn = get_db()
    users = conn.execute("SELECT * FROM users WHERE role = 'trainee'").fetchall()

    reports = []
    for u in users:
        progress_rows = conn.execute(
            "SELECT * FROM progress WHERE user_id = ?", (u["id"],)
        ).fetchall()

        completed = sum(1 for r in progress_rows if r["completed"])
        total = len([r for r in progress_rows if r["course_index"] is not None])
        overall = int(completed / total * 100) if total > 0 else 0

        reports.append({
            "userId": u["id"],
            "email": u["email"],
            "firstName": u["first_name"],
            "lastName": u["last_name"],
            "selectedTrack": u["selected_track"],
            "overallProgress": overall,
            "completedCourses": completed
        })

    conn.close()
    return jsonify({"success": True, "reports": reports})


@app.route("/api/admin/users/<user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_from_token(token)
    if not user or user["role"] != "admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.execute("DELETE FROM progress WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("🚀 NCBW Backend running at http://localhost:5000")
    app.run(debug=True, port=5000)
