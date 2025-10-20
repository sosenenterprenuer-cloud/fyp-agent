#!/usr/bin/env python3
"""
Personalized Learning Recommendation AI - Flask Application
Minimal, stable demo with self-healing database.
"""

import os
import json
import sqlite3
import random
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, g, session, request, redirect, url_for,
    render_template, flash, jsonify
)
from dotenv import load_dotenv

# --- Database Configuration ---
APP_ROOT = Path(__file__).resolve().parent
INSTANCE_DIR = APP_ROOT / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
DB_PATH = INSTANCE_DIR / "pla.db"

def get_db():
    """Get database connection with proper configuration."""
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

# --- Configuration & Setup ---
load_dotenv()
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-plai")
app.config["JSON_SORT_KEYS"] = False

@app.teardown_appcontext
def close_db(_=None):
    """Close database connection."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

# --- Self-Healing Database Initializer ---
def ensure_schema_and_min_seed():
    """Ensure database schema exists and seed with minimal demo data."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    # Create clean schema (only the tables we use)
    cur.executescript("""
    PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS student(
      student_id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS lecturer(
      lecturer_id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS attempt(
      attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_id INTEGER NOT NULL,
      started_at TEXT NOT NULL,
      finished_at TEXT,
      score_pct REAL DEFAULT 0,
      items_total INTEGER DEFAULT 0,
      items_correct INTEGER DEFAULT 0,
      FOREIGN KEY(student_id) REFERENCES student(student_id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS quiz(
      quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
      question TEXT NOT NULL,
      two_category TEXT NOT NULL,
      options_json TEXT NOT NULL,
      correct_answer TEXT NOT NULL,
      explanation TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS response(
      response_id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_id INTEGER NOT NULL,
      attempt_id INTEGER NOT NULL,
      quiz_id INTEGER NOT NULL,
      answer TEXT NOT NULL,
      score INTEGER NOT NULL,
      response_time_s REAL DEFAULT 0,
      FOREIGN KEY(student_id) REFERENCES student(student_id) ON DELETE CASCADE,
      FOREIGN KEY(attempt_id) REFERENCES attempt(attempt_id) ON DELETE CASCADE,
      FOREIGN KEY(quiz_id) REFERENCES quiz(quiz_id) ON DELETE CASCADE
    );
    """)

    # If no data or wrong counts, seed deterministic demo data
    total_q = cur.execute("SELECT COUNT(*) AS n FROM quiz").fetchone()["n"]
    total_s = cur.execute("SELECT COUNT(*) AS n FROM student").fetchone()["n"]
    if total_q != 30 or total_s < 2:
        cur.execute("DELETE FROM response")
        cur.execute("DELETE FROM attempt")
        cur.execute("DELETE FROM quiz")
        cur.execute("DELETE FROM student")
        cur.execute("DELETE FROM lecturer")

        # 2 students + 1 lecturer
        cur.execute("INSERT INTO student(name,email,password_hash) VALUES(?,?,?)",
                    ("NG EN JI","ngenji@demo.edu", generate_password_hash("Student123!")))
        cur.execute("INSERT INTO student(name,email,password_hash) VALUES(?,?,?)",
                    ("MUHAMMAD FARHAN","farhan@demo.edu", generate_password_hash("Student123!")))
        cur.execute("INSERT INTO lecturer(name,email,password_hash) VALUES(?,?,?)",
                    ("Admin","admin@lct.edu", generate_password_hash("Admin123!")))

        # 30 questions from provided CSV data
        questions = []
        def add(cat, q, opts, correct_letter, exp=""):
            questions.append((q, cat, json.dumps(opts), correct_letter, exp))

        # --- Add 15 Fundamentals ---
        add("Data Modeling & DBMS Fundamentals",
            "Which statement best describes a primary key?",
            ["Uniquely identifies each row and cannot be NULL","Allows duplicate values and NULLs","Identifies groups of rows but not a single row","Is only used in views"],
            "A","Primary keys must uniquely identify rows and be NOT NULL.")
        
        add("Data Modeling & DBMS Fundamentals",
            "What is a candidate key?",
            ["Any attribute that stores numeric values","Any superkey with redundant attributes removed","A key chosen for indexing only","The foreign key of a table"],
            "B","A candidate key is a minimal superkey (no redundant attributes).")
        
        add("Data Modeling & DBMS Fundamentals",
            "What is a superkey?",
            ["A set of attributes that uniquely identifies rows","An attribute with many NULLs","A key used only across tables","A non-unique composite index"],
            "A","Any attribute set that uniquely identifies a tuple is a superkey.")
        
        add("Data Modeling & DBMS Fundamentals",
            "What does a foreign key enforce?",
            ["Table partitioning","Functional dependency","Referential integrity between tables","Transaction isolation"],
            "C","Foreign keys enforce referential integrity with the referenced table.")
        
        add("Data Modeling & DBMS Fundamentals",
            "Which example is ONE-to-MANY?",
            ["Each order has exactly one customer; a customer has many orders","Each order has many customers","A product belongs to many categories and each category has many products","Each order has one product and each product has one order"],
            "A","One customer → many orders is 1:M.")
        
        add("Data Modeling & DBMS Fundamentals",
            "What is a composite key?",
            ["A key automatically generated by the DBMS","A key composed of more than one attribute","Any unique index","A key that changes frequently"],
            "B","Composite keys contain two or more attributes.")
        
        add("Data Modeling & DBMS Fundamentals",
            "What is a surrogate key?",
            ["A business-meaningful key","A randomly generated or sequence-based key without business meaning","A natural key used in reports","A foreign key with default value"],
            "B","Surrogate keys are system-generated and free of business meaning.")
        
        add("Data Modeling & DBMS Fundamentals",
            "In ER modeling, what is cardinality?",
            ["The number of attributes in an entity","The number of rows in a table","The count of entity instances that can participate in a relationship","The number of foreign keys in a schema"],
            "C","Cardinality describes participation counts in relationships.")
        
        add("Data Modeling & DBMS Fundamentals",
            "A weak entity typically requires what?",
            ["A multivalued attribute","An identifying relationship and a partial key","Only a surrogate key","No relationship to any other entity"],
            "B","Weak entities depend on owners via an identifying relationship.")
        
        add("Data Modeling & DBMS Fundamentals",
            "Schema vs. instance — which is true?",
            ["A schema changes every transaction","An instance is the INTENT; a schema is the CONTENT","A schema is the structure; an instance is the current data","A schema is per row; instance is per column"],
            "C","Schema = structure; instance = data at a point in time.")
        
        add("Data Modeling & DBMS Fundamentals",
            "Which constraint type prevents duplicate non-NULL values?",
            ["CHECK","DEFAULT","UNIQUE","FOREIGN KEY"],
            "C","UNIQUE prevents duplicate non-NULL values.")
        
        add("Data Modeling & DBMS Fundamentals",
            "How should a multivalued attribute be mapped to relations?",
            ["Store as comma-separated values in one column","Create a separate relation to hold the values","Duplicate columns up to a fixed max","Merge into the parent key column"],
            "B","Multivalued attributes are mapped to a separate relation.")
        
        add("Data Modeling & DBMS Fundamentals",
            "Which best describes a tuple?",
            ["A row in a relation","A column in a relation","A relationship between two tables","A file in the database"],
            "A","Tuple is the relational model term for row.")
        
        add("Data Modeling & DBMS Fundamentals",
            "What is the main purpose of indexing?",
            ["Guarantee logical data independence","Speed up data retrieval at the cost of extra writes","Ensure BCNF","Prevent deadlocks"],
            "B","Indexes accelerate reads with write/storage overhead.")
        
        add("Data Modeling & DBMS Fundamentals",
            "Which is true of normalization at a high level?",
            ["Ensures security roles","Eliminates concurrency issues","Reduces redundancy and anomalies","Forces star schemas"],
            "C","Normalization reduces redundancy and anomalies by structuring data.")

        # --- Add 15 Normalization ---
        add("Normalization & Dependencies",
            "Which best defines a functional dependency?",
            ["Two tables joined on a key","One attribute (or set) uniquely determines another","Two rows referencing the same foreign key","Two attributes always having the same domain"],
            "B","FD: X→Y means X determines Y.")
        
        add("Normalization & Dependencies",
            "Which violates FD theory?",
            ["Two rows share key but differ in non-key","Two rows differ only in key","Two rows have same non-key and same key","Rows are in different tables"],
            "A","If key matches, all dependent attributes must match.")
        
        add("Normalization & Dependencies",
            "What does 1NF require?",
            ["No NULLs","Only numeric values","Atomic (indivisible) attribute values","All attributes must be keys"],
            "C","1NF requires atomic values (no repeating groups).")
        
        add("Normalization & Dependencies",
            "Partial dependency is when a non-key attribute depends on…",
            ["The whole key only","A non-key attribute","Part of a composite key","Any superkey"],
            "C","2NF removes partial dependencies on part of a composite key.")
        
        add("Normalization & Dependencies",
            "2NF removes which anomaly source?",
            ["Transitive dependency","Partial dependency","Multivalued dependency","Key substitution"],
            "B","2NF addresses partial dependencies.")
        
        add("Normalization & Dependencies",
            "Transitive dependency means…",
            ["A→B and B→C implies A→C where C is non-prime","All attributes determine the key","Every FD has a superkey LHS","No determinants exist"],
            "A","3NF eliminates transitive dependencies on keys.")
        
        add("Normalization & Dependencies",
            "Which is allowed in 3NF?",
            ["NonKey→Key","Key→NonKey","NonKey→NonKey","PartKey→NonKey"],
            "B","3NF allows dependencies from keys to non-keys; forbids transitive from non-keys.")
        
        add("Normalization & Dependencies",
            "BCNF requires…",
            ["Every FD has a superkey on the left","Every FD has a candidate key on the right","No NULLs allowed","Only surrogate keys"],
            "A","BCNF: for every X→Y, X must be a superkey.")
        
        add("Normalization & Dependencies",
            "Main goal of normalization is to reduce…",
            ["Joins in queries","Storage size only","Redundancy and anomalies","Number of tables"],
            "C","Normalization reduces redundancy/anomalies, not just table count.")
        
        add("Normalization & Dependencies",
            "Which property defines a lossless-join decomposition?",
            ["Every projection is BCNF","Joining the decomposed tables never loses tuples","All FDs are preserved automatically","No NULLs in results"],
            "B","Lossless join means no information loss after join.")
        
        add("Normalization & Dependencies",
            "What is dependency preservation?",
            ["All original FDs can be enforced without joining tables","All FDs are eliminated","All joins are avoided","All keys become surrogate keys"],
            "A","Dependency preservation avoids enforcing FDs across joins.")
        
        add("Normalization & Dependencies",
            "Closure of an attribute set X (X+ ) is…",
            ["Set of attributes functionally determined by X","Minimal cover of FDs","The set of keys in the schema","The set of non-prime attributes"],
            "A","Closure lists all attributes determined by X.")
        
        add("Normalization & Dependencies",
            "To fix a 2NF issue you should…",
            ["Create more indexes","Denormalize the table","Decompose to remove partial dependencies","Drop foreign keys"],
            "C","Decompose to eliminate partial dependencies (reach 2NF).")
        
        add("Normalization & Dependencies",
            "Which update anomaly is reduced by 3NF?",
            ["Security escalation","Update anomalies on repeated facts","Deadlock anomalies","Lock escalation"],
            "B","3NF reduces update anomalies by isolating facts.")
        
        add("Normalization & Dependencies",
            "Given FD A,B→C and key (A,B), which is true?",
            ["C partially depends on the key","C transitively depends on the key","C is unrelated to the key","C violates BCNF"],
            "A","Non-key C depends on the whole composite key; not partial on a subset.")
        
        add("Normalization & Dependencies",
            "When decomposing for BCNF, what's the usual trade-off?",
            ["You may lose dependency preservation","You always lose lossless join","You must denormalize other tables","You must remove all keys"],
            "A","BCNF may sacrifice dependency preservation while keeping lossless join when possible.")

        cur.executemany(
            "INSERT INTO quiz(question,two_category,options_json,correct_answer,explanation) VALUES (?,?,?,?,?)",
            questions
        )

        # Create one perfect attempt for NG EN JI (unlocks next topic)
        ngenji_id = cur.execute("SELECT student_id FROM student WHERE email=?",
                                ("ngenji@demo.edu",)).fetchone()["student_id"]
        cur.execute("INSERT INTO attempt(student_id,started_at,finished_at,score_pct,items_total,items_correct) VALUES (?,?,?,?,?,?)",
                    (ngenji_id, "2025-10-19T09:00:00", "2025-10-19T09:15:00", 100.0, 30, 30))
        attempt_id = cur.lastrowid
        quiz_ids = [row["quiz_id"] for row in cur.execute("SELECT quiz_id, correct_answer FROM quiz").fetchall()]
        for qid in quiz_ids:
            # save all correct
            correct = cur.execute("SELECT correct_answer FROM quiz WHERE quiz_id=?", (qid,)).fetchone()["correct_answer"]
            cur.execute("INSERT INTO response(student_id,attempt_id,quiz_id,answer,score,response_time_s) VALUES (?,?,?,?,?,?)",
                        (ngenji_id, attempt_id, qid, correct, 1, 10.0))

        db.commit()
    db.close()

# Initialize database on startup
ensure_schema_and_min_seed()

# Startup logging
print(f"[BOOT] Database: {DB_PATH}")
student_count = sqlite3.connect(DB_PATH).execute("SELECT COUNT(*) FROM student").fetchone()[0]
quiz_count = sqlite3.connect(DB_PATH).execute("SELECT COUNT(*) FROM quiz").fetchone()[0]
print(f"[BOOT] Students: {student_count}, Questions: {quiz_count}")

# --- Debug Helper Route ---
@app.get("/_doctor/dbpath")
def _dbpath():
    """Debug route to show exact DB path and existence."""
    return {"db_path": str(DB_PATH), "exists": DB_PATH.exists()}

# --- Context Processor ---
@app.context_processor
def inject_session_flags():
    return {
        "sess_role": session.get("role"),
        "sess_student_id": session.get("student_id"),
        "sess_lecturer_id": session.get("lecturer_id"),
    }

# --- Authentication Decorators ---
def login_required(f):
    """Require user to be logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    """Require student role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'student':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def lecturer_required(f):
    """Require lecturer role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'lecturer':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
def index():
    """Home page."""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for students and lecturers."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        conn = get_db()
        
        # Check student first (as per requirements)
        student = conn.execute(
            "SELECT student_id, name, password_hash FROM student WHERE email = ?",
            (email,)
        ).fetchone()
        
        if student:
            if check_password_hash(student['password_hash'], password):
                session['user_id'] = student['student_id']
                session['role'] = 'student'
                session['name'] = student['name']
                session['student_id'] = student['student_id']
                
                # Check if student has a latest finished attempt
                conn = get_db()
                latest_attempt = conn.execute("""
                    SELECT attempt_id FROM attempt 
                    WHERE student_id = ? AND finished_at IS NOT NULL 
                    ORDER BY finished_at DESC LIMIT 1
                """, (student['student_id'],)).fetchone()
                
                if latest_attempt:
                    return redirect(url_for('review', attempt_id=latest_attempt['attempt_id']))
                else:
                    return redirect(url_for('quiz'))
            else:
                print(f"[AUTH] Password mismatch for {email} (role=student)")
        else:
            print(f"[AUTH] Email not found (student)")
        
        # Check lecturer
        lecturer = conn.execute(
            "SELECT lecturer_id, name, password_hash FROM lecturer WHERE email = ?",
            (email,)
        ).fetchone()
        
        if lecturer:
            if check_password_hash(lecturer['password_hash'], password):
                session['user_id'] = lecturer['lecturer_id']
                session['role'] = 'lecturer'
                session['name'] = lecturer['name']
                return redirect(url_for('admin'))
            else:
                print(f"[AUTH] Password mismatch for {email} (role=lecturer)")
        else:
            print(f"[AUTH] Email not found (lecturer)")
        
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Student registration."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not all([name, email, password]):
            flash('Please fill in all fields', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('register.html')
        
        conn = get_db()
        
        # Check if email already exists
        existing = conn.execute(
            "SELECT student_id FROM student WHERE email = ?",
            (email,)
        ).fetchone()
        
        if existing:
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create student
        password_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO student (name, email, password_hash, program) VALUES (?, ?, ?, ?)",
            (name, email, password_hash, 'BIT')
        )
        conn.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logout user."""
    session.clear()
    return redirect(url_for('index'))

# --- Student Routes ---
@app.route('/student/<int:student_id>')
@student_required
def student_dashboard(student_id):
    """Student dashboard with latest attempt metrics."""
    if session['user_id'] != student_id:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    # Get latest finished attempt
    latest_attempt = conn.execute("""
        SELECT * FROM attempt 
        WHERE student_id = ? AND finished_at IS NOT NULL 
        ORDER BY finished_at DESC LIMIT 1
    """, (student_id,)).fetchone()
    
    if not latest_attempt:
        return render_template('student_dashboard.html', 
                             student={'name': session['name']},
                             latest_attempt=None,
                             fund_pct=0,
                             norm_pct=0,
                             unlocked=False,
                             unlocked_next=False,
                             next_topic_name="Database Development Process",
                             attempts=[],
                             labels=[],
                             scores=[])
    
    # Calculate topic percentages for latest attempt
    responses = conn.execute("""
        SELECT r.is_correct, q.two_category
        FROM response r
        JOIN quiz q ON r.quiz_id = q.quiz_id
        WHERE r.attempt_id = ?
    """, (latest_attempt['attempt_id'],)).fetchall()
    
    fund_correct = sum(1 for r in responses if r['is_correct'] and r['two_category'] == 'Data Modeling & DBMS Fundamentals')
    fund_total = sum(1 for r in responses if r['two_category'] == 'Data Modeling & DBMS Fundamentals')
    norm_correct = sum(1 for r in responses if r['is_correct'] and r['two_category'] == 'Normalization & Dependencies')
    norm_total = sum(1 for r in responses if r['two_category'] == 'Normalization & Dependencies')
    
    fund_pct = round((fund_correct / fund_total * 100), 1) if fund_total > 0 else 0
    norm_pct = round((norm_correct / norm_total * 100), 1) if norm_total > 0 else 0
    
    # Check if unlocked (both topics 100%)
    unlocked = fund_pct == 100.0 and norm_pct == 100.0
    
    # Get all finished attempts for chart
    attempts = conn.execute("""
        SELECT * FROM attempt 
        WHERE student_id = ? AND finished_at IS NOT NULL 
        ORDER BY finished_at DESC LIMIT 10
    """, (student_id,)).fetchall()
    
    # Prepare chart data
    labels = [f"Attempt {i+1}" for i in range(len(attempts))]
    scores = [float(attempt['score_pct']) for attempt in attempts]
    
    return render_template('student_dashboard.html',
                         student={'name': session['name']},
                         latest_attempt=latest_attempt,
                         fund_pct=fund_pct,
                         norm_pct=norm_pct,
                         unlocked=unlocked,
                         unlocked_next=unlocked,
                         next_topic_name="Database Development Process",
                         attempts=attempts,
                         labels=labels,
                         scores=scores)

@app.route('/quiz')
@student_required
def quiz():
    """Quiz interface - 30 questions in random order."""
    conn = get_db()
    
    # Check for existing in-progress attempt
    existing_attempt = conn.execute("""
        SELECT attempt_id FROM attempt 
        WHERE student_id = ? AND finished_at IS NULL 
        ORDER BY started_at DESC LIMIT 1
    """, (session['user_id'],)).fetchone()
    
    if existing_attempt:
        flash('You have an existing quiz in progress. Continuing...', 'info')
        return render_template('quiz.html', attempt_id=existing_attempt['attempt_id'])
    
    # Create new attempt
    cursor = conn.execute("""
        INSERT INTO attempt (student_id, started_at, source) 
        VALUES (?, datetime('now'), 'web')
    """, (session['user_id'],))
    
    attempt_id = cursor.lastrowid
    conn.commit()
    
    return render_template('quiz.html', attempt_id=attempt_id)

@app.route("/api/quiz_progressive")
@student_required
def api_quiz_progressive() -> Any:
    """Get 30 questions in random order with robust option parsing."""
    try:
        # Ensure we have an active attempt
        atid = session.get("current_attempt_id")
        if not atid:
            conn = get_db()
            conn.execute(
                "INSERT INTO attempt (student_id, started_at) VALUES (?, ?)",
                (session["student_id"], datetime.now().isoformat())
            )
            conn.commit()
            row = conn.execute(
                "SELECT attempt_id FROM attempt WHERE student_id=? ORDER BY started_at DESC LIMIT 1",
                (session["student_id"],)
            ).fetchone()
            atid = row["attempt_id"]
            session["current_attempt_id"] = atid

        conn = get_db()
        rows = conn.execute("""
            SELECT quiz_id, question, two_category, options_json, correct_letter, explanation
            FROM quiz
            ORDER BY RANDOM()
            LIMIT 60
        """).fetchall()

        # Debug: Print total quiz count
        total_quiz_count = conn.execute("SELECT COUNT(*) FROM quiz").fetchone()[0]
        print(f"[DEBUG] Total quiz count: {total_quiz_count}")

        def normalize_question(r) -> dict | None:
            """Normalize a question row to required format or return None if invalid."""
            # Parse options_json
            opts = []
            try:
                parsed = json.loads(r["options_json"])
                if isinstance(parsed, list) and len(parsed) >= 4:
                    opts = [str(x) for x in parsed[:4]]
                else:
                    print(f"[WARNING] Invalid options_json for quiz_id {r['quiz_id']}: {r['options_json']}")
                    return None
            except (json.JSONDecodeError, TypeError) as e:
                print(f"[WARNING] Failed to parse options_json for quiz_id {r['quiz_id']}: {e}")
                return None
            
            # Get correct_letter (already validated by DB constraint)
            correct_letter = r.get("correct_letter", "A")
            
            # Debug logging for first 3 rows
            if len([q for q in [r] if q]) <= 3:  # Simple way to track first few
                print(f"[DEBUG] Quiz {r['quiz_id']}: correct_letter={correct_letter}")
            
            return {
                "quiz_id": r["quiz_id"],
                "two_category": r["two_category"],
                "question": r["question"],
                "option_a": opts[0],
                "option_b": opts[1],
                "option_c": opts[2],
                "option_d": opts[3],
                "correct_letter": correct_letter,
                "explanation": r.get("explanation", "")
            }

        structured = []
        skipped = 0
        
        for r in rows:
            normalized = normalize_question(dict(r))
            if normalized:
                structured.append(normalized)
                if len(structured) == 30:
                    break
            else:
                skipped += 1

        if len(structured) == 0:
            print(f"[ERROR] No questions could be normalized (skipped {skipped})")
            return jsonify({"error": "no_questions"}), 500

        print(f"[DEBUG] Returning {len(structured)} questions (skipped {skipped})")
        return jsonify(structured), 200
        
    except Exception as e:
        print(f"[ERROR] QUIZ_LOAD_FAILURE: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "quiz_build_failed"}), 500

@app.route('/submit', methods=['POST'])
@student_required
def submit_quiz():
    """Submit quiz answers and calculate scores."""
    try:
        data = request.get_json()
        attempt_id = data.get('attempt_id')
        answers = data.get('answers', [])
        
        if not attempt_id or not answers:
            return jsonify({'error': 'Missing attempt_id or answers'}), 400
        
        conn = get_db()
        
        # Verify attempt belongs to current user
        attempt = conn.execute("""
            SELECT * FROM attempt WHERE attempt_id = ? AND student_id = ?
        """, (attempt_id, session['student_id'])).fetchone()
        
        if not attempt:
            return jsonify({'error': 'Invalid attempt'}), 400
        
        def get_correct_letter_for_quiz(quiz_id):
            """Get the correct letter for a quiz (already stored as A/B/C/D)."""
            quiz_row = conn.execute("""
                SELECT correct_letter FROM quiz WHERE quiz_id = ?
            """, (quiz_id,)).fetchone()
            
            if not quiz_row:
                return "A"
            
            # correct_letter is already validated by DB constraint
            return quiz_row.get("correct_letter", "A")
        
        # Process each answer
        correct_count = 0
        total_count = len(answers)
        
        for answer in answers:
            quiz_id = answer.get('quiz_id')
            user_answer = answer.get('answer', 'A')  # User's selected letter
            response_time = answer.get('response_time', 0)
            
            # Get correct letter using same logic as quiz API
            correct_letter = get_correct_letter_for_quiz(quiz_id)
            
            # Check if correct (strict letter comparison)
            is_correct = 1 if user_answer == correct_letter else 0
            if is_correct:
                correct_count += 1
            
            # Store response
            conn.execute("""
                INSERT INTO response (student_id, attempt_id, quiz_id, answer, score, response_time_s)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session['student_id'], attempt_id, quiz_id, user_answer, is_correct, response_time))
        
        # Update attempt
        score_pct = round((correct_count / total_count * 100), 1) if total_count > 0 else 0
        conn.execute("""
            UPDATE attempt 
            SET finished_at = datetime('now'), items_total = ?, items_correct = ?, score_pct = ?
            WHERE attempt_id = ?
        """, (total_count, correct_count, score_pct, attempt_id))
        
        conn.commit()
        
        # Log submission
        print(f"[DEBUG] QUIZ_SUBMIT: attempt_id={attempt_id}, total={total_count}, correct={correct_count}, score={score_pct:.1f}%")
        
        return jsonify({
            'ok': True,
            'redirect_url': f'/review/{attempt_id}',
            'attempt_id': attempt_id,
            'score_pct': score_pct
        })
        
    except Exception as e:
        print(f"[ERROR] SUBMIT_FAILURE: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "submit_failed"}), 500

@app.route('/review/<int:attempt_id>')
@student_required
def review(attempt_id):
    """Review quiz results with explanations."""
    conn = get_db()
    
    # Get attempt
    attempt = conn.execute("""
        SELECT * FROM attempt WHERE attempt_id = ? AND student_id = ?
    """, (attempt_id, session['user_id'])).fetchone()
    
    if not attempt:
        flash('Attempt not found', 'error')
        return redirect(url_for('student_dashboard', student_id=session['user_id']))
    
    # Get responses with quiz details
    responses = conn.execute("""
        SELECT r.*, q.question, q.correct_text, q.two_category, q.explanation
        FROM response r
        JOIN quiz q ON r.quiz_id = q.quiz_id
        WHERE r.attempt_id = ?
        ORDER BY r.quiz_id
    """, (attempt_id,)).fetchall()
    
    # Calculate topic percentages
    fund_correct = sum(1 for r in responses if r['is_correct'] and r['two_category'] == 'Data Modeling & DBMS Fundamentals')
    fund_total = sum(1 for r in responses if r['two_category'] == 'Data Modeling & DBMS Fundamentals')
    norm_correct = sum(1 for r in responses if r['is_correct'] and r['two_category'] == 'Normalization & Dependencies')
    norm_total = sum(1 for r in responses if r['two_category'] == 'Normalization & Dependencies')
    
    fund_pct = round((fund_correct / fund_total * 100), 1) if fund_total > 0 else 0
    norm_pct = round((norm_correct / norm_total * 100), 1) if norm_total > 0 else 0
    
    # Check if unlocked
    unlocked = fund_pct == 100.0 and norm_pct == 100.0
    
    return render_template('review.html',
                         attempt=attempt,
                         responses=responses,
                         fund_pct=fund_pct,
                         norm_pct=norm_pct,
                         unlocked=unlocked)

@app.route('/thanks')
@student_required
def thanks():
    """Thanks page after quiz completion."""
    return render_template('thanks.html')

@app.route('/api/feedback', methods=['POST'])
@student_required
def api_feedback():
    """Submit feedback (not stored, just success message)."""
    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment', '')
    
    if not rating or rating < 1 or rating > 5:
        return jsonify({'error': 'Invalid rating'}), 400
    
    # Just return success - not storing feedback as per requirements
    return jsonify({'message': 'Feedback submitted successfully'})

@app.route('/debug/authcheck')
def debug_authcheck():
    """Diagnostic endpoint for authentication debugging (dev only)."""
    if os.environ.get('APP_MODE') == 'prod':
        return jsonify({'error': 'Not available in production'}), 404
    
    conn = get_db()
    
    # Get basic counts
    students_count = conn.execute("SELECT COUNT(*) FROM student").fetchone()[0]
    lecturers_count = conn.execute("SELECT COUNT(*) FROM lecturer").fetchone()[0]
    
    # Get sample student data
    sample_student = conn.execute("SELECT email, password_hash FROM student LIMIT 1").fetchone()
    
    result = {
        'db_path': os.path.abspath(DB_PATH),
        'students_count': students_count,
        'lecturers_count': lecturers_count
    }
    
    if sample_student:
        result['sample_student_email'] = sample_student['email']
        result['hash_prefix'] = sample_student['password_hash'][:12] if sample_student['password_hash'] else None
        result['hash_is_pbkdf2'] = sample_student['password_hash'].startswith('pbkdf2:') if sample_student['password_hash'] else False
    
    return jsonify(result)

# --- Lecturer Routes ---
@app.route('/admin')
@lecturer_required
def admin():
    """Lecturer admin dashboard."""
    conn = get_db()
    
    # Get basic stats
    student_count = conn.execute("SELECT COUNT(*) FROM student").fetchone()[0]
    attempt_count = conn.execute("SELECT COUNT(*) FROM attempt").fetchone()[0]
    response_count = conn.execute("SELECT COUNT(*) FROM response").fetchone()[0]
    
    # Get category accuracy
    category_stats = conn.execute("""
        SELECT q.two_category, 
               AVG(r.is_correct) as avg_correctness,
               COUNT(r.response_id) as response_count
        FROM quiz q
        LEFT JOIN response r ON q.quiz_id = r.quiz_id
        GROUP BY q.two_category
    """).fetchall()
    
    # Get 14-day chart data
    chart_data = conn.execute("""
        SELECT DATE(finished_at) as date, COUNT(*) as attempts
        FROM attempt 
        WHERE finished_at IS NOT NULL 
        AND finished_at >= datetime('now', '-14 days')
        GROUP BY DATE(finished_at)
        ORDER BY date
    """).fetchall()
    
    return render_template('admin_overview.html',
                         student_count=student_count,
                         attempt_count=attempt_count,
                         response_count=response_count,
                         category_stats=category_stats,
                         chart_data=chart_data)

@app.route('/admin/students')
@lecturer_required
def admin_students():
    """List all students."""
    conn = get_db()
    
    students = conn.execute("""
        SELECT s.*, COUNT(a.attempt_id) as attempt_count
        FROM student s
        LEFT JOIN attempt a ON s.student_id = a.student_id
        GROUP BY s.student_id
        ORDER BY s.name
    """).fetchall()
    
    return render_template('admin_students.html', students=students)

@app.route('/admin/rankings')
@lecturer_required
def admin_rankings():
    """Student rankings by performance."""
    conn = get_db()
    
    rankings = conn.execute("""
        SELECT s.name, s.email,
               AVG(a.score_pct) as avg_score,
               MAX(a.score_pct) as best_score,
               MIN(a.score_pct) as last_score,
               COUNT(a.attempt_id) as attempt_count
        FROM student s
        LEFT JOIN attempt a ON s.student_id = a.student_id
        WHERE a.finished_at IS NOT NULL
        GROUP BY s.student_id
        ORDER BY avg_score DESC
    """).fetchall()
    
    return render_template('admin_rankings.html', rankings=rankings)

@app.route('/admin/questions')
@lecturer_required
def admin_questions():
    """Question performance statistics."""
    conn = get_db()
    
    questions = conn.execute("""
        SELECT q.quiz_id, q.question, q.two_category,
               AVG(r.is_correct) as correct_rate,
               COUNT(r.response_id) as response_count
        FROM quiz q
        LEFT JOIN response r ON q.quiz_id = r.quiz_id
        GROUP BY q.quiz_id
        ORDER BY q.quiz_id
    """).fetchall()
    
    return render_template('admin_questions.html', questions=questions)

@app.route('/admin/analytics')
@lecturer_required
def admin_analytics():
    """Detailed analytics."""
    conn = get_db()
    
    # Per-student per-question response times
    response_times = conn.execute("""
        SELECT s.name, q.quiz_id, q.question,
               AVG(r.response_time_s) as avg_time,
               COUNT(r.response_id) as response_count
        FROM student s
        JOIN response r ON s.student_id = r.student_id
        JOIN quiz q ON r.quiz_id = q.quiz_id
        GROUP BY s.student_id, q.quiz_id
        HAVING response_count >= 5
        ORDER BY avg_time DESC
    """).fetchall()
    
    return render_template('admin_analytics.html', response_times=response_times)

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
