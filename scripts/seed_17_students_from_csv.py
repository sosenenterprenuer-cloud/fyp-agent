#!/usr/bin/env python3
"""
Seed 17 students from FIXED list with their first finished attempts.
Creates students with credentials and inserts their first finished attempt (30 responses each).
"""
import os
import csv
import sqlite3
import re
import random
from werkzeug.security import generate_password_hash
from datetime import datetime
from typing import Dict, List, Tuple

# --- Configuration ---
DB = os.getenv("PLA_DB", "pla.db")
DEFAULT_PW = os.getenv("SEED_PW", "Student123!")

# --- Fixed Name List and Scoring Targets ---
FIXED_STUDENT_NAMES = [
    "MOHAMED AIMAN", "MUHAMMAD FARHAN ADDREEN BIN SARRAFIAN", "NG EN JI",
    "MUHAMMAD MUZAMMIL BIN SALIM", "NATALIE CHANG PUI SHAN", "LAVANESS A/L SRITHAR",
    "NUR LIYANA BINTI RAMLI", "TEE KA HONG", "MUHAMMAD AFIQ SHADIQI BIN ZAWAWI",
    "SUKANTHAN A/L SURESH", "SRITHARAN A/L RAGU", "NUR BATRISYIA BINTI ZOOL HILMI",
    "ANIS AKMA SOFEA BINTI AZMAN", "JEMMY O'VEINNEDDICT BULOT", "AMANDA FLORA JENOS",
    "SITI FARAH ERLIYANA BINTI MOHD HAIRUL NIZAM", "SHARON YEO"
]

# Varied per-topic targets (used to simulate scores: 100% means 30/30, 90% means 27/30, etc.)
SCORING_PROFILES = [
    (100, 100), (90, 85), (75, 95), (60, 50), (99, 99), (70, 70), (85, 65), (55, 45), 
    (92, 78), (88, 80), (79, 90), (68, 62), (81, 75), (52, 50), (95, 87), (80, 82), (76, 73)
]

# --- Helper Functions ---

def now_str() -> str:
    """Returns the current local time string for database insertion."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def normalize_text(s: str) -> str:
    """Slugifies name for email usage (mohamedaiman)."""
    return "".join(ch.lower() if ch.isalnum() else "" for ch in s).replace(" ", "")

def slug_email(full_name: str) -> str:
    """Generates a unique, slugified email."""
    base = normalize_text(full_name)
    if not base:
        base = "student" + str(random.randint(1, 99))
    return f"{base}@demo.edu"

def get_db_connection() -> sqlite3.Connection:
    """Returns a new DB connection."""
    con = sqlite3.connect(os.getenv("PLA_DB", DB))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def ensure_tables_and_columns(con: sqlite3.Connection) -> None:
    """Creates missing core tables and ensures all required columns exist."""
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS student (
            student_id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, 
            password_hash TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS lecturer (
            lecturer_id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, 
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY, student_id INTEGER, rating INTEGER NOT NULL, 
            comment TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
        -- Ensure response table exists minimally
        CREATE TABLE IF NOT EXISTS response (
            response_id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, attempt_id INTEGER NOT NULL, 
            quiz_id INTEGER NOT NULL, score INTEGER DEFAULT 0,
            answer_text TEXT, response_time_s REAL DEFAULT 0.0
        );
    """)

    # --- MIGRATION: Ensure columns exist on response (idempotent) ---
    cols = [c[1] for c in con.execute("PRAGMA table_info(response)").fetchall()]
    if 'answer_text' not in cols:
        try:
            con.execute("ALTER TABLE response ADD COLUMN answer_text TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists
    if 'response_time_s' not in cols:
        try:
            con.execute("ALTER TABLE response ADD COLUMN response_time_s REAL DEFAULT 0.0")
        except sqlite3.OperationalError:
            pass
    
    con.commit()

def main() -> None:
    """Main seeding function."""
    
    con = get_db_connection()
    cur = con.cursor()
    
    # Ensure tables and critical columns exist
    ensure_tables_and_columns(con)
    
    # 1. CLEANUP OLD STUDENT DATA
    print("[CLEANUP] Deleting old student/attempt/response/feedback data...")
    cur.execute("DELETE FROM feedback")
    cur.execute("DELETE FROM response")
    cur.execute("DELETE FROM attempt")
    # Delete all students (we rely on the embedded FIXED_STUDENT_NAMES list now)
    cur.execute("DELETE FROM student") 
    con.commit()
    
    # 2. PREPARE QUIZ DATA
    quiz_data = cur.execute("SELECT quiz_id, correct_answer, two_category FROM quiz").fetchall()
    
    if len(quiz_data) != 30:
        print(f"[FATAL ERROR] Quiz bank count is {len(quiz_data)}. Must be 30. ABORTING.")
        con.close()
        return

    # 3. SEED STUDENTS AND ATTEMPTS
    created_credentials = []
    
    for i, full_name in enumerate(FIXED_STUDENT_NAMES):
        # 3a. Create Student
        email = slug_email(full_name)
        password_hash = generate_password_hash(DEFAULT_PW)
        
        cur.execute(
            "INSERT INTO student (name, email, password_hash, program) VALUES (?, ?, ?, ?)",
            (full_name, email, password_hash, "BIT"),
        )
        student_id = cur.lastrowid
        created_credentials.append((full_name, email, DEFAULT_PW))

        # 3b. Insert finished attempt (source='live') - FIX: nf_scope removed
        target_f, target_n = SCORING_PROFILES[i % len(SCORING_PROFILES)]
        
        cur.execute(
            "INSERT INTO attempt (student_id, started_at, finished_at, source) VALUES (?, ?, ?, ?)",
            (student_id, now_str(), now_str(), "web"),
        )
        attempt_id = cur.lastrowid
        
        correct = 0
        total = 0
        
        # 3c. Insert 30 responses based on target percentage
        for quiz_row in quiz_data:
            total += 1
            is_fund = (quiz_row["two_category"] == "Data Modeling & DBMS Fundamentals")
            target_pct = target_f if is_fund else target_n
            
            # Determine correctness based on target_pct
            is_correct = (random.randint(1, 100) <= target_pct)
            
            # Use the correct answer text for the response
            answer_text = quiz_row["correct_answer"]
            
            # Score is 1/0
            score = 1 if is_correct else 0
            
            # Corrected logic:
            if not is_correct:
                # If wrong, provide a generic incorrect placeholder text
                answer_text = "Incorrect Placeholder"

            cur.execute(
                """
                INSERT INTO response (student_id, attempt_id, quiz_id, answer_text, score, response_time_s)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (student_id, attempt_id, quiz_row["quiz_id"], answer_text, score, round(random.uniform(8.0, 20.0), 2))
            )
            # Update counters used for attempt summary
            correct += score


        # 3d. Update attempt scores
        score_pct = round(100 * correct / total, 1) if total else 0.0
        cur.execute(
            "UPDATE attempt SET items_total=?, items_correct=?, score_pct=? WHERE attempt_id=?",
            (total, correct, score_pct, attempt_id)
        )
        print(f"[ATTEMPT] {email}: {correct}/{total} ({score_pct}%)")

    con.commit()
    con.close()
    
    # 4. FINAL OUTPUT
    print("\n[SUCCESS] Custom Seeding complete with 17 students.")
    print(f"[SUCCESS] Default student password: {DEFAULT_PW}")
    print("\n[CREDENTIALS] Student accounts created (Password: Student123!):")
    for full_name, email, pwd in created_credentials:
        print(f" - {full_name} ({email})")
    print(f"\n[CREDENTIALS] Lecturer account: admin@lct.edu (Password: Admin!234)")


if __name__ == "__main__":
    main()