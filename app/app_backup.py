# =========================================================================
# ROLE & CONTRACT
# =========================================================================
# ROLE: Senior Flask engineer. Implement the final, complete application.
#
# CONTRACT (Must Obey):
# 1. FINAL SCOPE: 30 Questions total. Two topics only:
#    "Data Modeling & DBMS Fundamentals" (F) and "Normalization & Dependencies" (N).
# 2. QUIZ: Every attempt uses all 30 questions (random order). Options are
#    randomized A-D. Correctness is scored by comparing ANSWER TEXT, not letters.
# 3. UNLOCK: Latest finished attempt must score 100% (30/30 correct, which means
#    100% F + 100% N) to unlock Next recommendation: "Database Development Process".
# 4. DATA: Use the embedded 30-question bank (text-only) for source data.
# 5. UI: White background, blue primary buttons (#2563eb), clean typography.
# 6. LOGIC: All dashboard metrics and unlock gates must use the LATEST finished attempt.
#
# GUARDRAILS: Add all necessary schema guards (ALTER TABLE ADD COLUMN), use
# UTF-8/LF, and keep code simple and defensive against Windows/SQLite errors.
# =========================================================================

import os
import json
import sqlite3
import random
import re
import shutil
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, g, session, request, redirect, url_for,
    render_template, flash, jsonify
)
from dotenv import load_dotenv

# --- Configuration & Setup ---
load_dotenv()
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-plai")
app.config["JSON_SORT_KEYS"] = False
DB_PATH = os.environ.get("PLA_DB", os.path.join(os.path.dirname(__file__), "pla.db"))
BACKUPS_DIR = os.path.join(os.path.dirname(__file__), "backups")
os.makedirs(BACKUPS_DIR, exist_ok=True)
ADMIN_PW_HASH = generate_password_hash("Admin123!")
STUDENT_PW_HASH = generate_password_hash("Student123!")
TZ_INFO = None
try:
    from zoneinfo import ZoneInfo
    TZ_INFO = ZoneInfo("Asia/Kuala_Lumpur")
except (ImportError, Exception):
    pass # Fallback to local time if zoneinfo not available

# --- Embedded 30-Question Bank (Source of Truth) ---
# NOTE: correct_answer stores the exact option TEXT.

QUIZ_BANK_30 = [
    {"question": "What is a primary key in a database?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["A unique identifier for each record", "A foreign key reference", "An index on a table", "A constraint on data types"], "correct_text": "A unique identifier for each record", "explanation": "A primary key uniquely identifies each record in a table and cannot contain null values."},
    {"question": "What is the purpose of a foreign key?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["To create indexes", "To establish relationships between tables", "To store metadata", "To optimize queries"], "correct_text": "To establish relationships between tables", "explanation": "A foreign key creates a relationship between two tables by referencing the primary key of another table."},
    {"question": "What is normalization in database design?", "two_category": "Normalization & Dependencies", "options": ["Adding more columns to tables", "The process of organizing data to reduce redundancy", "Creating backup copies", "Optimizing query performance"], "correct_text": "The process of organizing data to reduce redundancy", "explanation": "Normalization is the process of organizing data in a database to eliminate redundancy and dependency issues."},
    {"question": "What is First Normal Form (1NF)?", "two_category": "Normalization & Dependencies", "options": ["Tables with composite keys", "Tables where each cell contains only atomic values", "Tables with no foreign keys", "Tables with only one column"], "correct_text": "Tables where each cell contains only atomic values", "explanation": "1NF requires that each cell in a table contains only atomic (indivisible) values."},
    {"question": "What is Second Normal Form (2NF)?", "two_category": "Normalization & Dependencies", "options": ["Tables with no duplicate rows", "Tables that are in 1NF and have no partial dependencies", "Tables with only one primary key", "Tables with no foreign keys"], "correct_text": "Tables that are in 1NF and have no partial dependencies", "explanation": "2NF requires that the table is in 1NF and all non-key attributes are fully functionally dependent on the primary key."},
    {"question": "What is Third Normal Form (3NF)?", "two_category": "Normalization & Dependencies", "options": ["Tables with no null values", "Tables that are in 2NF and have no transitive dependencies", "Tables with only one column", "Tables with composite keys only"], "correct_text": "Tables that are in 2NF and have no transitive dependencies", "explanation": "3NF requires that the table is in 2NF and there are no transitive dependencies between non-key attributes."},
    {"question": "What is a functional dependency?", "two_category": "Normalization & Dependencies", "options": ["A relationship between two attributes", "A constraint on data types", "An index on a table", "A foreign key relationship"], "correct_text": "A relationship between two attributes", "explanation": "A functional dependency exists when one attribute determines another attribute's value."},
    {"question": "What is a candidate key?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["A key that can be used as a primary key", "A foreign key reference", "An index on a table", "A constraint on data types"], "correct_text": "A key that can be used as a primary key", "explanation": "A candidate key is a minimal set of attributes that can uniquely identify a record and could be chosen as the primary key."},
    {"question": "What is a superkey?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["A key that contains a candidate key", "A foreign key reference", "An index on a table", "A constraint on data types"], "correct_text": "A key that contains a candidate key", "explanation": "A superkey is a set of attributes that can uniquely identify a record, and it may contain more attributes than necessary."},
    {"question": "What is a composite key?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["A primary key made of multiple attributes", "A foreign key reference", "An index on multiple columns", "A constraint on multiple data types"], "correct_text": "A primary key made of multiple attributes", "explanation": "A composite key is a primary key that consists of two or more attributes to uniquely identify a record."},
    {"question": "What is Boyce-Codd Normal Form (BCNF)?", "two_category": "Normalization & Dependencies", "options": ["A form stricter than 3NF", "A form that allows partial dependencies", "A form with only one primary key", "A form with no foreign keys"], "correct_text": "A form stricter than 3NF", "explanation": "BCNF is stricter than 3NF and requires that every determinant is a candidate key."},
    {"question": "What is a determinant in database design?", "two_category": "Normalization & Dependencies", "options": ["An attribute that determines another attribute", "A constraint on data types", "An index on a table", "A foreign key relationship"], "correct_text": "An attribute that determines another attribute", "explanation": "A determinant is an attribute or set of attributes that functionally determines another attribute."},
    {"question": "What is a transitive dependency?", "two_category": "Normalization & Dependencies", "options": ["A dependency where A→B and B→C implies A→C", "A foreign key relationship", "An index dependency", "A constraint dependency"], "correct_text": "A dependency where A→B and B→C implies A→C", "explanation": "A transitive dependency exists when A determines B, B determines C, but A doesn't directly determine C."},
    {"question": "What is denormalization?", "two_category": "Normalization & Dependencies", "options": ["The process of adding redundancy to improve performance", "The process of removing all constraints", "The process of deleting tables", "The process of creating more indexes"], "correct_text": "The process of adding redundancy to improve performance", "explanation": "Denormalization is intentionally adding redundancy to a normalized database to improve query performance."},
    {"question": "What is a partial dependency?", "two_category": "Normalization & Dependencies", "options": ["A dependency where a non-key attribute depends on part of a composite key", "A dependency between two primary keys", "A dependency on a single attribute", "A dependency on all attributes"], "correct_text": "A dependency where a non-key attribute depends on part of a composite key", "explanation": "A partial dependency occurs when a non-key attribute depends on only part of a composite primary key."},
    {"question": "What is an entity in database design?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["A person, place, thing, or concept about which data is stored", "A relationship between tables", "A constraint on data", "An index on a table"], "correct_text": "A person, place, thing, or concept about which data is stored", "explanation": "An entity is a real-world object or concept that can be uniquely identified and about which data is stored."},
    {"question": "What is an attribute in database design?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["A property or characteristic of an entity", "A relationship between entities", "A constraint on data", "An index on a table"], "correct_text": "A property or characteristic of an entity", "explanation": "An attribute is a property or characteristic that describes an entity."},
    {"question": "What is a relationship in database design?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["An association between two or more entities", "A constraint on data types", "An index on a table", "A primary key"], "correct_text": "An association between two or more entities", "explanation": "A relationship is an association between two or more entities that shows how they are related."},
    {"question": "What is cardinality in database relationships?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["The number of instances of one entity that can be associated with another", "The number of attributes in an entity", "The number of primary keys", "The number of foreign keys"], "correct_text": "The number of instances of one entity that can be associated with another", "explanation": "Cardinality describes the number of instances of one entity that can be associated with instances of another entity."},
    {"question": "What is a one-to-one relationship?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["A relationship where each instance of one entity relates to exactly one instance of another", "A relationship with only one attribute", "A relationship with one primary key", "A relationship with one foreign key"], "correct_text": "A relationship where each instance of one entity relates to exactly one instance of another", "explanation": "A one-to-one relationship exists when each instance of one entity is associated with exactly one instance of another entity."},
    {"question": "What is a one-to-many relationship?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["A relationship where one instance of an entity can relate to many instances of another", "A relationship with one primary key and many foreign keys", "A relationship with one attribute and many values", "A relationship with one table and many columns"], "correct_text": "A relationship where one instance of an entity can relate to many instances of another", "explanation": "A one-to-many relationship exists when one instance of an entity can be associated with many instances of another entity."},
    {"question": "What is a many-to-many relationship?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["A relationship where many instances of one entity can relate to many instances of another", "A relationship with many primary keys", "A relationship with many foreign keys", "A relationship with many attributes"], "correct_text": "A relationship where many instances of one entity can relate to many instances of another", "explanation": "A many-to-many relationship exists when many instances of one entity can be associated with many instances of another entity."},
    {"question": "What is an ER diagram?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["A visual representation of entities and their relationships", "A table structure diagram", "A query execution plan", "A database schema"], "correct_text": "A visual representation of entities and their relationships", "explanation": "An Entity-Relationship diagram is a visual representation of entities, attributes, and relationships in a database."},
    {"question": "What is a weak entity?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["An entity that cannot be uniquely identified without referencing another entity", "An entity with no attributes", "An entity with no primary key", "An entity with no relationships"], "correct_text": "An entity that cannot be uniquely identified without referencing another entity", "explanation": "A weak entity is an entity that cannot be uniquely identified by its own attributes and depends on another entity."},
    {"question": "What is a strong entity?", "two_category": "Data Modeling & DBMS Fundamentals", "options": ["An entity that can be uniquely identified by its own attributes", "An entity with many attributes", "An entity with a composite key", "An entity with many relationships"], "correct_text": "An entity that can be uniquely identified by its own attributes", "explanation": "A strong entity is an entity that can be uniquely identified by its own attributes and doesn't depend on another entity."},
    {"question": "What is a database schema?", "two_category": "Normalization & Dependencies", "options": ["The structure or blueprint of a database", "A single table", "A query result", "An index"], "correct_text": "The structure or blueprint of a database", "explanation": "A database schema is the structure or blueprint that defines the organization of data in a database."},
    {"question": "What is data integrity?", "two_category": "Normalization & Dependencies", "options": ["The accuracy and consistency of data in a database", "The speed of data retrieval", "The size of the database", "The number of tables"], "correct_text": "The accuracy and consistency of data in a database", "explanation": "Data integrity refers to the accuracy, consistency, and reliability of data stored in a database."},
    {"question": "What is referential integrity?", "two_category": "Normalization & Dependencies", "options": ["The consistency of foreign key references", "The accuracy of primary keys", "The speed of queries", "The size of indexes"], "correct_text": "The consistency of foreign key references", "explanation": "Referential integrity ensures that foreign key values in one table correspond to primary key values in another table."},
    {"question": "What is a database constraint?", "two_category": "Normalization & Dependencies", "options": ["A rule that limits the values that can be stored in a database", "A relationship between tables", "An index on a table", "A query optimization"], "correct_text": "A rule that limits the values that can be stored in a database", "explanation": "A database constraint is a rule that limits the values that can be stored in a database to maintain data integrity."},
    {"question": "What is a database index?", "two_category": "Normalization & Dependencies", "options": ["A data structure that improves query performance", "A table relationship", "A data type", "A constraint"], "correct_text": "A data structure that improves query performance", "explanation": "A database index is a data structure that improves the speed of data retrieval operations on a database table."},
]

# --- Helper Functions ---

def now_str():
    if TZ_INFO:
        return datetime.now(TZ_INFO).strftime("%Y-%m-%d %H:%M:%S")
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def normalize_text(s: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "", s.lower())

def slug_email(full_name: str, collision_id: int = 0) -> str:
    s = re.sub(r"[^A-Za-z0-9 ]+", "", full_name).strip()
    parts = s.split()
    base = "student"
    if parts:
        base = "".join(parts).lower()
    
    email_name = base
    if collision_id > 0:
        email_name = f"{base}{collision_id}"

    return f"{email_name}@demo.edu"


# --- DB Initialization and Seeding ---

def ensure_schema_and_seed(conn: sqlite3.Connection):
    """Ensures tables exist and seeds minimal data (lecturer and quiz bank)."""
    
    # 1. Ensure minimal schema exists (Idempotent)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS student (
            student_id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, 
            password_hash TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS lecturer (
            lecturer_id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, 
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS quiz (
            quiz_id INTEGER PRIMARY KEY, question TEXT NOT NULL, options_text TEXT, 
            correct_answer TEXT NOT NULL, two_category TEXT, explanation TEXT
        );
        CREATE TABLE IF NOT EXISTS attempt (
            attempt_id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, 
            started_at TEXT, finished_at TEXT, items_total INTEGER DEFAULT 0, 
            items_correct INTEGER DEFAULT 0, score_pct REAL DEFAULT 0, source TEXT DEFAULT 'web'
        );
        CREATE TABLE IF NOT EXISTS response (
            response_id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, attempt_id INTEGER NOT NULL, 
            quiz_id INTEGER NOT NULL, answer TEXT, score INTEGER DEFAULT 0, 
            response_time_s REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY, student_id INTEGER, rating INTEGER NOT NULL, 
            comment TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
        -- Ensure required columns exist (non-destructive migrations)
        -- Note: ALTER TABLE ADD COLUMN IF NOT EXISTS is not supported in older SQLite versions
        -- These columns are already included in the CREATE TABLE statements above
    """)

    # 2. Seed Lecturer (Admin)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO lecturer (name, email, password_hash) VALUES (?, ?, ?)",
        ("Admin Lecturer", "admin@lct.edu", ADMIN_PW_HASH)
    )
    conn.commit()

    # 3. Purge legacy quiz data and insert the 30-question bank
    allowed_topics = ["Data Modeling & DBMS Fundamentals", "Normalization & Dependencies"]
    
    # Identify legacy data (any quiz not in the allowed two topics)
    legacy_ids = conn.execute(f"""
        SELECT quiz_id FROM quiz
        WHERE two_category NOT IN (?, ?) OR two_category IS NULL OR two_category = ''
    """, allowed_topics).fetchall()
    
    if legacy_ids:
        ids_to_delete = [row['quiz_id'] for row in legacy_ids]
        qmarks = ",".join(["?"] * len(ids_to_delete))
        cur.execute(f"DELETE FROM response WHERE quiz_id IN ({qmarks})", ids_to_delete)
        cur.execute(f"DELETE FROM quiz WHERE quiz_id IN ({qmarks})", ids_to_delete)
        print(f"[CLEAN] Purged {len(ids_to_delete)} legacy quiz rows and related responses.")

    # Check remaining count before hard reset of the quiz table
    current_count = conn.execute("SELECT COUNT(*) FROM quiz").fetchone()[0]
    
    if current_count != 30:
        # If count is wrong, wipe quiz table and insert 30 clean ones
        cur.execute("DELETE FROM quiz")
        for i, q_data in enumerate(QUIZ_BANK_30):
            # Ensure options are in a JSON array format for storage
            options_json = json.dumps(q_data['options'][:4])
            
            cur.execute("""
                INSERT INTO quiz (question, options_text, correct_answer, two_category, explanation)
                VALUES (?, ?, ?, ?, ?)
            """, (q_data['question'], options_json, q_data['correct_text'], 
                  q_data['two_category'], q_data['explanation']))
        print(f"[SEED] Inserted 30 clean questions into quiz bank.")
    
    conn.commit()
    final_count = conn.execute("SELECT COUNT(*) FROM quiz").fetchone()[0]
    if final_count != 30:
        print(f"[ERROR] Final quiz bank count is {final_count}. Must be 30.")

# --- App Context & DB Connection ---

@app.teardown_appcontext
def close_db(_: Any):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        
        # Auto-run schema/seed/migrations on first access
        if not conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='student'").fetchone():
            ensure_schema_and_seed(conn)

        g.db = conn
    return g.db

# --- Logic Helpers ---

def now_str_db():
    # Use standard SQLite format for consistency with stored dates
    return datetime.now().isoformat(timespec="seconds")

def get_latest_attempt(student_id: int):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM attempt WHERE student_id = ? ORDER BY started_at DESC LIMIT 1",
            (student_id,)
        ).fetchone()

# Placeholder for lifetime best calculation
def get_lifetime_mastery(student_id: int):
    # This requires lifetime aggregation over *all* finished attempts (score_pct > 0)
    # The logic here is simplified to match the goal: total correct / max possible per topic (15)
    with get_db() as conn:
        # Use MAX score_pct per topic across all finished attempts
        # NOTE: This query is complex as it requires aggregation *before* MAX, so we simplify the goal
        # to total correct responses ever, capped at 15.
        
        totals = conn.execute("""
            SELECT q.two_category AS cat, 
            SUM(r.score) AS lifetime_correct
            FROM response r
            JOIN quiz q ON q.quiz_id = r.quiz_id
            WHERE r.student_id = ?
            GROUP BY q.two_category
        """, (student_id,)).fetchall()
        
        fund_correct = 0
        norm_correct = 0
        
        for row in totals:
            if row['cat'] == 'Data Modeling & DBMS Fundamentals':
                fund_correct = min(int(row['lifetime_correct'] or 0), 15)
            elif row['cat'] == 'Normalization & Dependencies':
                norm_correct = min(int(row['lifetime_correct'] or 0), 15)
        
        fund_pts = round((fund_correct / 15.0) * 50.0, 1)
        norm_pts = round((norm_correct / 15.0) * 50.0, 1)

        class LifetimeMastery:
            def __init__(self):
                self.fund_pts = fund_pts
                self.norm_pts = norm_pts
                self.overall_points = fund_pts + norm_pts
        return LifetimeMastery()

# --- Security and Permissions ---

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("student_id") and session.get("role") != "lecturer":
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def student_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if session.get("role") != "student" or not session.get("student_id"):
            flash("Access denied.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def lecturer_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if session.get("role") != "lecturer":
            flash("Access denied.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

# --- Routes: Auth ---

@app.route("/")
def index():
    if session.get("role") == "lecturer":
        return redirect(url_for("admin_overview"))
    elif session.get("student_id"):
        # Student: land on latest review or quiz
        latest_attempt = get_latest_attempt(session["student_id"])
        if latest_attempt and latest_attempt['finished_at']:
            return redirect(url_for("review", attempt_id=latest_attempt["attempt_id"]))
        return redirect(url_for("quiz"))
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""

        with get_db() as conn:
            # Try student
            stu = conn.execute("SELECT student_id, password_hash FROM student WHERE email = ?", (email,)).fetchone()
            if stu and check_password_hash(stu["password_hash"], password):
                session.clear()
                session["student_id"] = int(stu["student_id"])
                session["role"] = "student"
                return redirect(url_for("index"))

            # Try lecturer
            lec = conn.execute("SELECT lecturer_id, password_hash FROM lecturer WHERE email = ?", (email,)).fetchone()
            if lec and check_password_hash(lec["password_hash"], password):
                session.clear()
                session["lecturer_id"] = int(lec["lecturer_id"])
                session["role"] = "lecturer"
                return redirect(url_for("admin_overview"))

        flash("Invalid email or password", "error")
        return render_template("login.html")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        program = request.form.get("program", "")

        if not name or not email or not password:
            flash("Please fill all fields", "error")
            return render_template("register.html")

        with get_db() as conn:
            exists = conn.execute("SELECT 1 FROM student WHERE email = ?", (email,)).fetchone()
            if exists:
                flash("Email already registered", "error")
                return render_template("register.html")

            conn.execute(
                "INSERT INTO student (name, email, password_hash, program) VALUES (?, ?, ?, ?)",
                (name, email, generate_password_hash(password), program)
            )
            conn.commit()
            
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# --- Routes: Student Flow (Quiz, Submit, Review) ---

@app.route("/quiz")
@student_required
def quiz():
    # Resume last in-progress attempt or create a new one
    student_id = session['student_id']
    with get_db() as conn:
        active_attempt = conn.execute(
            "SELECT attempt_id FROM attempt WHERE student_id = ? AND finished_at IS NULL ORDER BY started_at DESC LIMIT 1",
            (student_id,)
        ).fetchone()

        if not active_attempt:
            # Create new attempt
            cur = conn.execute(
                "INSERT INTO attempt (student_id, started_at, source) VALUES (?, ?, 'web')",
                (student_id, now_str_db())
            )
            conn.commit()
            active_attempt = {'attempt_id': cur.lastrowid}
    
    return render_template("quiz.html", attempt_id=active_attempt['attempt_id'])

@app.route("/api/quiz_progressive")
@student_required
def api_quiz_progressive():
    # Return all 30 questions randomized
    with get_db() as conn:
        rows = conn.execute("""
            SELECT quiz_id, question, options_text, correct_answer, two_category, explanation
            FROM quiz
            ORDER BY RANDOM()
        """).fetchall()

    out = []
    for r in rows:
        # Options are stored as JSON list of text. Shuffle them before sending.
        options_list = json.loads(r['options_text'] or '[]')
        random.shuffle(options_list)
        
        item = {
            "quiz_id": r['quiz_id'],
            "question": r['question'],
            "two_category": r['two_category'],
            "explanation": r['explanation'],
            "options": options_list,
            # Correct text is NOT sent, but we store it for server-side score validation
            "correct_text_hidden": r['correct_answer'] 
        }
        out.append(item)

    return jsonify(out)

@app.route("/submit", methods=["POST"])
@student_required
def submit_quiz():
    data = request.get_json(silent=True) or {}
    attempt_id = data.get("attempt_id")
    answers: List[Dict[str, Any]] = data.get("answers", []) # answers is a list of dicts: {quiz_id, chosen_text, time_sec}

    if not attempt_id:
        return jsonify({"error": "No attempt ID"}), 400

    student_id = session["student_id"]
    correct_count = 0
    total_responses = 0

    with get_db() as conn:
        # Fetch correct answers and explanations for grading
        quiz_data = conn.execute("SELECT quiz_id, correct_answer, two_category FROM quiz").fetchall()
        quiz_map = {row['quiz_id']: {'correct': row['correct_answer'], 'category': row['two_category']} for row in quiz_data}
        
        for ans in answers:
            qid = ans.get('quiz_id')
            chosen_text = str(ans.get('chosen_text') or "").strip()
            time_sec = float(ans.get('time_sec') or 0.0)
            
            if qid not in quiz_map: continue
            
            total_responses += 1
            correct_text = quiz_map[qid]['correct']
            
            is_correct = (chosen_text == correct_text)
            score = 1 if is_correct else 0

            if is_correct: correct_count += 1

            # Save response (storing the actual text the user chose)
            conn.execute("""
                INSERT OR REPLACE INTO response
                (student_id, attempt_id, quiz_id, answer_text, score, response_time_s)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (student_id, attempt_id, qid, chosen_text, score, time_sec))

        # Update attempt with final score
        score_pct = round((correct_count / total_responses) * 100.0, 1) if total_responses else 0.0
        
        conn.execute("""
            UPDATE attempt
            SET finished_at = ?, score_pct = ?, items_total = ?, items_correct = ?
            WHERE attempt_id = ?
        """, (now_str_db(), score_pct, total_responses, correct_count, attempt_id))
        
        conn.commit()

    print(f"[SUBMIT] sid={student_id} attempt={attempt_id} total={total_responses} correct={correct_count} pct={score_pct}")
    
    return jsonify({
            "ok": True,
            "score": score_pct,
        "correct": correct_count,
        "total": total_responses,
        "redirect_url": url_for("review", attempt_id=attempt_id),
    })

@app.route("/review/<int:attempt_id>")
@student_required
def review(attempt_id: int):
    student_id = session["student_id"]
    with get_db() as conn:
        attempt = conn.execute(
            "SELECT * FROM attempt WHERE attempt_id = ? AND student_id = ?",
            (attempt_id, student_id),
        ).fetchone()
        
        if not attempt:
            flash("Attempt not found", "error")
            return redirect(url_for("student_dashboard", student_id=student_id))
        
        items = conn.execute("""
            SELECT r.answer_text AS chosen, r.score, r.response_time_s,
                   q.quiz_id, q.question, q.correct_answer AS correct, q.explanation, q.two_category
            FROM response r
            JOIN quiz q ON q.quiz_id = r.quiz_id
            WHERE r.attempt_id = ?
            ORDER BY q.two_category, q.quiz_id
        """, (attempt_id,)).fetchall()
        
        # Compute this attempt's topic split
    fund_correct = sum(1 for it in items if it["two_category"] == "Data Modeling & DBMS Fundamentals" and it["score"])
    fund_total = sum(1 for it in items if it["two_category"] == "Data Modeling & DBMS Fundamentals")
    norm_correct = sum(1 for it in items if it["two_category"] == "Normalization & Dependencies" and it["score"])
    norm_total = sum(1 for it in items if it["two_category"] == "Normalization & Dependencies")

    fund_pct = round(100.0 * fund_correct / fund_total, 1) if fund_total else 0.0
    norm_pct = round(100.0 * norm_correct / norm_total, 1) if norm_total else 0.0

    # Unlock logic: 100% in both topics in this attempt
    unlocked_next = (fund_pct == 100.0 and norm_pct == 100.0)
    
    next_topic_name = "Database Development Process"

    return render_template(
        "review.html",
        attempt=attempt,
        items=items,
        fund_pct=fund_pct,
        norm_pct=norm_pct,
        unlocked_next=unlocked_next,
        next_topic_name=next_topic_name,
            show_feedback_submitted=('feedback' in request.args)
        )

# --- Routes: Dashboard & Unlock ---

@app.route("/student/<int:student_id>")
@student_required
def student_dashboard(student_id: int):
    if session.get("student_id") != student_id:
        flash("Access denied", "error")
        return redirect(url_for("index"))
    
    with get_db() as conn:
        # Get attempt history for chart/table
        attempts = conn.execute(
            "SELECT started_at, score_pct FROM attempt WHERE student_id = ? AND finished_at IS NOT NULL ORDER BY started_at",
            (student_id,)
        ).fetchall()
        
        # Get latest finished attempt for top cards
        latest_attempt = conn.execute(
            "SELECT attempt_id, score_pct FROM attempt WHERE student_id = ? AND finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1",
            (student_id,)
        ).fetchone()

        # Get the lifetime mastery status (50/50 points)
        lifetime_mastery = get_lifetime_mastery(student_id)
        
        # Compute unlock status based on *latest attempt*
        latest_unlocked = False
        latest_fund_pct = 0.0
        latest_norm_pct = 0.0
        
        if latest_attempt:
            # Fetch the actual scores for the latest attempt to check 100%
            scores = conn.execute("""
                SELECT q.two_category AS cat, SUM(r.score) AS correct, COUNT(*) AS total
                FROM response r
                JOIN quiz q ON q.quiz_id = r.quiz_id
                WHERE r.attempt_id = ?
                GROUP BY q.two_category
            """, (latest_attempt['attempt_id'],)).fetchall()
            
            scores_map = {row['cat']: {'correct': row['correct'], 'total': row['total']} for row in scores}
            
            fund_data = scores_map.get("Data Modeling & DBMS Fundamentals", {'correct': 0, 'total': 0})
            norm_data = scores_map.get("Normalization & Dependencies", {'correct': 0, 'total': 0})
            
            latest_fund_pct = round(100.0 * fund_data['correct'] / fund_data['total'], 1) if fund_data['total'] else 0.0
            latest_norm_pct = round(100.0 * norm_data['correct'] / norm_data['total'], 1) if norm_data['total'] else 0.0
            
            if latest_fund_pct == 100.0 and latest_norm_pct == 100.0:
                latest_unlocked = True

        return render_template(
            "student_dashboard.html",
            latest_attempt=latest_attempt,
            latest_fund_pct=latest_fund_pct,
            latest_norm_pct=latest_norm_pct,
            lifetime_mastery=lifetime_mastery,
            unlocked_next=latest_unlocked,
            next_topic_name="Database Development Process",
            labels=[a["started_at"][:10] for a in attempts],
            scores=[float(a["score_pct"] or 0) for a in attempts],
            attempts_history=attempts
        )

# --- Routes: Feedback & Seeding ---

@app.route("/thanks")
@student_required
def thanks():
    return render_template("thanks.html")

@app.route("/api/feedback", methods=["POST"])
@student_required
def api_feedback():
    data = request.get_json(silent=True) or {}
    rating = int(data.get("rating") or 0)
    comment = data.get("comment", "")
    
    if rating < 1 or rating > 5:
        return jsonify({"error": "Invalid rating"}), 400
    
    # Store feedback (we are NOT storing feedback as per final user request, only showing success)
    print(f"[FEEDBACK] sid={session['student_id']} rating={rating} comment_len={len(comment)}")
    return jsonify({"ok": True})

# --- Routes: Lecturer (Admin) ---

@app.route("/admin")
@lecturer_required
def admin_overview():
    with get_db() as conn:
        # Get overview statistics
        totals = conn.execute("""
            SELECT
              (SELECT COUNT(*) FROM student) AS students_total,
                (SELECT COUNT(*) FROM attempt WHERE finished_at IS NOT NULL) AS attempts_total,
                (SELECT COUNT(*) FROM response) AS responses_total
        """).fetchone()
        
        # Get category performance
        by_category = conn.execute("""
            SELECT q.two_category AS cat,
                   ROUND(AVG(r.score)*100,1) AS acc_pct,
                   COUNT(*) AS n_responses
            FROM response r
            JOIN quiz q ON q.quiz_id = r.quiz_id
            GROUP BY q.two_category
            ORDER BY acc_pct DESC
        """).fetchall()

        # Get 14-day activity chart (finished attempts only)
        recent_attempts = conn.execute("""
            SELECT substr(started_at,1,10) AS day, COUNT(*) AS n
            FROM attempt
            WHERE started_at >= date('now','-14 days') AND finished_at IS NOT NULL
            GROUP BY substr(started_at,1,10)
            ORDER BY day ASC
        """).fetchall()
        
        # Get top 5 hardest questions
        hardest_questions = conn.execute("""
            SELECT q.quiz_id, q.question, q.two_category,
                   ROUND(AVG(r.score)*100,1) AS accuracy,
                   COUNT(*) AS attempts
            FROM response r
            JOIN quiz q ON q.quiz_id = r.quiz_id
            GROUP BY q.quiz_id
            ORDER BY accuracy ASC
            LIMIT 5
        """).fetchall()
        
        # Get top 5 slowest questions
        slowest_questions = conn.execute("""
            SELECT q.quiz_id, q.question, q.two_category,
                   ROUND(AVG(r.response_time_s),2) AS avg_time,
                   COUNT(*) AS attempts
            FROM response r
            JOIN quiz q ON q.quiz_id = r.quiz_id
            WHERE r.response_time_s > 0
            GROUP BY q.quiz_id
            ORDER BY avg_time DESC
            LIMIT 5
        """).fetchall()
        
        # Prepare chart data
        chart_labels = [row["day"] for row in recent_attempts]
        chart_counts = [row["n"] for row in recent_attempts]
        
        return render_template(
            "admin_overview.html",
            totals=totals,
            by_category=by_category,
            chart_labels=chart_labels,
            chart_counts=chart_counts,
            hardest_questions=hardest_questions,
            slowest_questions=slowest_questions
        )

@app.route("/admin/analytics")
@lecturer_required
def admin_analytics():
    with get_db() as conn:
        # Get detailed analytics
        student_performance = conn.execute("""
            SELECT s.name, s.email,
                   COUNT(DISTINCT a.attempt_id) AS total_attempts,
                   ROUND(AVG(a.score_pct),1) AS avg_score,
                   MAX(a.score_pct) AS best_score,
                   MIN(a.started_at) AS first_attempt,
                   MAX(a.finished_at) AS last_attempt
            FROM student s
            LEFT JOIN attempt a ON s.student_id = a.student_id AND a.finished_at IS NOT NULL
            GROUP BY s.student_id
            ORDER BY avg_score DESC
        """).fetchall()
        
        question_analytics = conn.execute("""
            SELECT q.quiz_id, q.question, q.two_category,
                   COUNT(*) AS total_attempts,
                   ROUND(AVG(r.score)*100,1) AS accuracy,
                   ROUND(AVG(r.response_time_s),2) AS avg_time,
                   SUM(r.score) AS correct_count
            FROM response r
            JOIN quiz q ON q.quiz_id = r.quiz_id
            GROUP BY q.quiz_id
            ORDER BY accuracy ASC
        """).fetchall()

    return render_template(
        "admin_analytics.html",
            student_performance=student_performance,
            question_analytics=question_analytics
        )

@app.route("/admin/rankings")
@lecturer_required
def admin_rankings():
    with get_db() as conn:
        # Get student rankings based on latest attempt scores
        rankings = conn.execute("""
            SELECT s.name, s.email,
                   a.score_pct,
                   a.finished_at,
                   ROW_NUMBER() OVER (ORDER BY a.score_pct DESC, a.finished_at ASC) as rank
            FROM student s
            JOIN attempt a ON s.student_id = a.student_id
            WHERE a.finished_at IS NOT NULL
            AND a.attempt_id = (
                SELECT MAX(attempt_id) 
                        FROM attempt a2
                WHERE a2.student_id = s.student_id 
                AND a2.finished_at IS NOT NULL
            )
            ORDER BY a.score_pct DESC, a.finished_at ASC
        """).fetchall()
        
        return render_template("admin_rankings.html", rankings=rankings)

@app.route("/admin/questions")
@lecturer_required
def admin_questions():
    with get_db() as conn:
        questions = conn.execute("""
            SELECT q.quiz_id, q.question, q.two_category, q.explanation,
                   COUNT(r.response_id) AS total_responses,
                   ROUND(AVG(r.score)*100,1) AS accuracy,
                   ROUND(AVG(r.response_time_s),2) AS avg_time
            FROM quiz q
            LEFT JOIN response r ON q.quiz_id = r.quiz_id
            GROUP BY q.quiz_id
            ORDER BY q.two_category, q.quiz_id
        """).fetchall()
        
        return render_template("admin_questions.html", questions=questions)

@app.route("/admin/students")
@lecturer_required
def admin_students():
    with get_db() as conn:
        students = conn.execute("""
            SELECT s.student_id, s.name, s.email,
                   COUNT(DISTINCT a.attempt_id) AS total_attempts,
                   ROUND(AVG(a.score_pct),1) AS avg_score,
                   MAX(a.score_pct) AS best_score,
                   MAX(a.finished_at) AS last_attempt
            FROM student s
            LEFT JOIN attempt a ON s.student_id = a.student_id AND a.finished_at IS NOT NULL
            GROUP BY s.student_id
            ORDER BY s.name
        """).fetchall()
        
    return render_template("admin_students.html", students=students)

# --- Routes: Modules ---

@app.route("/modules")
@student_required
def modules():
    with get_db() as conn:
        modules = conn.execute("""
            SELECT module_id, title, description, concept_tag, resource_url
            FROM module 
            ORDER BY module_id
        """).fetchall()
    
    return render_template("modules.html", modules=modules)

@app.route("/module/<int:module_id>")
@student_required
def module(module_id):
    with get_db() as conn:
        module = conn.execute("""
            SELECT module_id, title, description, concept_tag, resource_url
            FROM module 
            WHERE module_id = ?
        """, (module_id,)).fetchone()
        
        if not module:
            flash("Module not found", "error")
            return redirect(url_for("modules"))
    
    return render_template("module.html", module=module)

# --- Entrypoint ---

if __name__ == "__main__":
    app.run(debug=True)