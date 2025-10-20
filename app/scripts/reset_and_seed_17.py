#!/usr/bin/env python3
"""
Reset and seed database with 30 questions and 17 students.
"""

import os
import sys
import sqlite3
import csv
import json
from pathlib import Path
from werkzeug.security import generate_password_hash

# --- SSOT Database Path Configuration ---
# SINGLE SOURCE OF TRUTH for DB path (Windows absolute)
DB_PATH = Path(r"C:\Users\Sudarshan\Downloads\fyp-cursor-main (4)\fyp-cursor-main\app\instance\pla.db")

def ensure_db_dir():
    """Ensure database directory exists and set environment variable."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    os.environ["PLA_DB"] = str(DB_PATH)  # also set env for any code that reads PLA_DB
    return DB_PATH

def main():
    """Reset and seed the database."""
    print("=== RESET AND SEED 17 STUDENTS ===")
    
    # Parse command line arguments
    force = '--force' in sys.argv
    with_attempts = '--with-attempts' in sys.argv
    
    # Use SSOT database path
    db_path = str(ensure_db_dir())
    
    print(f"Database: {db_path}")
    print(f"ENV: {'PLA_DB' if 'PLA_DB' in os.environ else 'default'}")
    print(f"Force: {force}")
    print(f"With attempts: {with_attempts}")
    
    # Remove existing database if force is specified
    if force and os.path.exists(db_path):
        os.remove(db_path)
        print("[RESET] Dropping existing database...")
    
    # Create new database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    
    # Read and execute schema
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    conn.executescript(schema_sql)
    print("[RESET] Database schema created successfully")
    
    # Load quiz questions
    quiz_csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "quiz_bank.csv")
    if not os.path.exists(quiz_csv_path):
        print(f"ERROR: Quiz CSV not found at {quiz_csv_path}")
        return 1
    
    print("[QUIZ] Loading quiz bank from CSV...")
    questions = []
    with open(quiz_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(row)
    
    if len(questions) != 30:
        print(f"ERROR: Expected 30 questions, found {len(questions)}")
        return 1
    
    # Validate categories
    fund_count = sum(1 for q in questions if q['two_category'] == 'Data Modeling & DBMS Fundamentals')
    norm_count = sum(1 for q in questions if q['two_category'] == 'Normalization & Dependencies')
    
    if fund_count != 15 or norm_count != 15:
        print(f"ERROR: Expected 15/15 split, found {fund_count}/{norm_count}")
        return 1
    
    # Insert questions
    for q in questions:
        # Create options JSON array
        options = [q['option_a'], q['option_b'], q['option_c'], q['option_d']]
        options_json = json.dumps(options)
        
        conn.execute("""
            INSERT INTO quiz (question, options_json, correct_text, two_category, explanation)
            VALUES (?, ?, ?, ?, ?)
        """, (
            q['question'],
            options_json,
            q['correct_text'],
            q['two_category'],
            q['explanation']
        ))
    
    print(f"[QUIZ] Loaded 30 questions ({fund_count} Fundamentals, {norm_count} Normalization)")
    
    # Load students
    students_csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "students_17.csv")
    if not os.path.exists(students_csv_path):
        print(f"ERROR: Students CSV not found at {students_csv_path}")
        return 1
    
    print("[STUDENTS] Loading students from CSV...")
    students = []
    with open(students_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            students.append(row)
    
    if len(students) != 17:
        print(f"ERROR: Expected 17 students, found {len(students)}")
        return 1
    
    # Insert students
    for student in students:
        password_hash = generate_password_hash("Student123!")
        conn.execute("""
            INSERT INTO student (name, email, password_hash, program, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (
            student['name'],
            student['email'].lower(),
            password_hash,
            'BIT'
        ))
    
    print(f"[STUDENTS] Loaded {len(students)} students")
    
    # Create lecturer
    lecturer_hash = generate_password_hash("Lecturer123!")
    conn.execute("""
        INSERT INTO lecturer (name, email, password_hash)
        VALUES (?, ?, ?)
    """, (
        "Admin Lecturer",
        "admin@lct.edu",
        lecturer_hash
    ))
    
    print("[LECTURER] Created admin account: admin@lct.edu")
    
    # Validation
    print("[VALIDATION] First 3 student emails:")
    for i, student in enumerate(students[:3]):
        print(f"  - {student['email']}")
    
    # Check password hash
    first_student = conn.execute("SELECT password_hash FROM student LIMIT 1").fetchone()
    if first_student and first_student['password_hash'].startswith(('pbkdf2:', 'scrypt:', 'argon2:')):
        print("[VALIDATION] Password hash OK")
    else:
        print("[VALIDATION] WARNING: Password hash does not look hashed")
    
    conn.commit()
    
    # Create attempts if requested
    if "--with-attempts" in sys.argv:
        print("[ATTEMPTS] Creating finished attempts...")
        
        # Get all students
        student_rows = conn.execute("SELECT student_id, name, email FROM student").fetchall()
        
        for student in student_rows:
            # Create varied scores for each student
            if student['email'] == 'ngenji@demo.edu':
                # Perfect score for NG EN JI
                score_pct = 100.0
                items_correct = 30
            else:
                # Random score between 50-95%
                import random
                score_pct = round(random.uniform(50, 95), 1)
                items_correct = int(score_pct * 30 / 100)
            
            # Create attempt
            cursor = conn.execute("""
                INSERT INTO attempt (student_id, started_at, source)
                VALUES (?, datetime('now', '-1 hour'), 'web')
            """, (student['student_id'],))
            
            attempt_id = cursor.lastrowid
            
            # Update attempt with results
            conn.execute("""
                UPDATE attempt 
                SET finished_at = datetime('now'), score_pct = ?, items_total = 30, items_correct = ?
                WHERE attempt_id = ?
            """, (score_pct, items_correct, attempt_id))
            
            # Create responses for NG EN JI (perfect)
            if student['email'] == 'ngenji@demo.edu':
                # Get all quiz questions
                quiz_questions = conn.execute("SELECT quiz_id FROM quiz").fetchall()
                
                for quiz in quiz_questions:
                    conn.execute("""
                        INSERT INTO response (student_id, attempt_id, quiz_id, answer_letter, answer_text, is_correct, response_time_s)
                        VALUES (?, ?, ?, 'A', 'Perfect answer', 1, ?)
                    """, (
                        student['student_id'],
                        attempt_id,
                        quiz['quiz_id'],
                        round(5 + (hash(str(quiz['quiz_id'])) % 8), 1)  # 5-12 seconds
                    ))
            
            print(f"  - {student['name']}: {items_correct}/30 ({score_pct}%)")
        
        print("[ATTEMPTS] Created finished attempts for all students")
    
    conn.commit()
    conn.close()
    
    print("\n[SUCCESS] Database reset and seeded successfully!")
    print("Run 'python scripts/verify_ready.py' to verify the setup.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())