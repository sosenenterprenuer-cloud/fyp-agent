#!/usr/bin/env python3
"""
Hard reset and seed script.
Wipes student data and seeds 17 students with credentials and 1 finished attempt each.
"""

import os
import sys
import sqlite3
import random
import time
from pathlib import Path
from werkzeug.security import generate_password_hash

# Get the app directory (parent of scripts)
APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = os.path.join(APP_DIR, "pla.db")

# 17 student names for seeding
STUDENT_NAMES = [
    "MOHAMED AIMAN",
    "MUHAMMAD FARHAN ADDREEN BIN SARRAFIAN", 
    "NG EN JI",
    "MUHAMMAD MUZAMMIL BIN SALIM",
    "NATALIE CHANG PUI SHAN",
    "LAVANESS A/L SRITHAR",
    "NUR LIYANA BINTI RAMLI",
    "TEE KA HONG",
    "MUHAMMAD AFIQ SHADIQI BIN ZAWAWI",
    "SUKANTHAN A/L SURESH",
    "SRITHARAN A/L RAGU",
    "NUR BATRISYIA BINTI ZOOL HILMI",
    "ANIS AKMA SOFEA BINTI AZMAN",
    "JEMMY O'VEINNEDDICT BULOT",
    "AMANDA FLORA JENOS",
    "SITI FARAH ERLIYANA BINTI MOHD HAIRUL NIZAM",
    "SHARON YEO"
]

def slug_email(name):
    """Convert name to email format."""
    import re
    base = re.sub(r"[^A-Za-z0-9 ]+", "", name).strip()
    parts = base.split()
    if parts:
        base = "".join(parts).lower()
    else:
        base = "student"
    return f"{base}@demo.edu"

def hard_reset_and_seed():
    """Perform hard reset and seed 17 students with attempts."""
    if not os.path.exists(DB_PATH):
        print("[ERROR] Database file not found at:", DB_PATH)
        sys.exit(2)
    
    # Create backup
    backup_path = os.path.join(APP_DIR, "backups", f"pla_backup_{int(time.time())}.db")
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    
    try:
        import shutil
        shutil.copy(DB_PATH, backup_path)
        print(f"[BACKUP] Created backup: {backup_path}")
    except Exception as e:
        print(f"[WARNING] Could not create backup: {e}")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Hard reset: Delete all student data
        print("[RESET] Clearing student data...")
        cursor.execute("DELETE FROM response")
        cursor.execute("DELETE FROM attempt") 
        cursor.execute("DELETE FROM student")
        
        # Try to delete feedback table if it exists
        try:
            cursor.execute("DELETE FROM feedback")
        except sqlite3.OperationalError:
            pass  # Table doesn't exist, that's fine
        
        # Ensure lecturer exists
        cursor.execute("""
            INSERT OR IGNORE INTO lecturer (name, email, password_hash) 
            VALUES ('Admin Lecturer', 'admin@lct.edu', ?)
        """, (generate_password_hash("Admin123!"),))
        
        # Seed 17 students
        print("[SEED] Creating 17 students...")
        student_ids = []
        
        for name in STUDENT_NAMES:
            email = slug_email(name)
            password_hash = generate_password_hash("Student123!")
            
            cursor.execute("""
                INSERT INTO student (name, email, password_hash, program)
                VALUES (?, ?, ?, ?)
            """, (name, email, password_hash, "BIT"))
            
            student_ids.append(cursor.lastrowid)
        
        # Get quiz questions for creating attempts
        cursor.execute("SELECT quiz_id, correct_answer, two_category FROM quiz")
        quiz_questions = cursor.fetchall()
        
        if len(quiz_questions) != 30:
            print(f"[ERROR] Expected 30 quiz questions, found {len(quiz_questions)}")
            sys.exit(3)
        
        # Create one finished attempt per student with realistic scores
        print("[SEED] Creating finished attempts...")
        
        for i, student_id in enumerate(student_ids):
            # Create attempt
            started_at = f"2024-01-{(i % 28) + 1:02d} 10:00:00"
            finished_at = f"2024-01-{(i % 28) + 1:02d} 10:05:00"
            
            cursor.execute("""
                INSERT INTO attempt (student_id, started_at, source)
                VALUES (?, ?, 'seed')
            """, (student_id, started_at))
            
            # Update with completion data
            cursor.execute("""
                UPDATE attempt 
                SET finished_at = ?, items_total = 30
                WHERE attempt_id = ?
            """, (finished_at, cursor.lastrowid))
            
            attempt_id = cursor.lastrowid
            
            # Create responses with varied performance
            correct_count = 0
            
            # Vary difficulty: some students perform better than others
            base_performance = 0.6 + (i % 5) * 0.08  # 60% to 96% range
            
            for q in quiz_questions:
                # Determine if this answer is correct based on performance
                is_correct = random.random() < base_performance
                
                if is_correct:
                    chosen_answer = q['correct_answer']
                    score = 1
                    correct_count += 1
                else:
                    # Choose a wrong answer (simplified - just add "Wrong" prefix)
                    chosen_answer = f"Wrong: {q['correct_answer']}"
                    score = 0
                
                response_time = round(random.uniform(8, 25), 2)
                
                cursor.execute("""
                    INSERT INTO response (student_id, attempt_id, quiz_id, answer, score, response_time_s)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (student_id, attempt_id, q['quiz_id'], chosen_answer, score, response_time))
            
            # Update attempt with final score
            score_pct = round((correct_count / 30) * 100, 1)
            cursor.execute("""
                UPDATE attempt 
                SET items_correct = ?, score_pct = ?
                WHERE attempt_id = ?
            """, (correct_count, score_pct, attempt_id))
            
            print(f"  - Student {i+1}: {correct_count}/30 ({score_pct}%)")
        
        # Ensure at least one perfect student
        cursor.execute("SELECT student_id FROM student ORDER BY student_id LIMIT 1")
        perfect_student = cursor.fetchone()['student_id']
        
        # Update their attempt to be perfect
        cursor.execute("""
            SELECT attempt_id FROM attempt WHERE student_id = ? ORDER BY attempt_id DESC LIMIT 1
        """, (perfect_student,))
        perfect_attempt = cursor.fetchone()['attempt_id']
        
        # Update all responses to be correct
        cursor.execute("""
            UPDATE response SET score = 1, answer = (
                SELECT correct_answer FROM quiz WHERE quiz_id = response.quiz_id
            ) WHERE attempt_id = ?
        """, (perfect_attempt,))
        
        # Update attempt to be perfect
        cursor.execute("""
            UPDATE attempt SET items_correct = 30, score_pct = 100.0 WHERE attempt_id = ?
        """, (perfect_attempt,))
        
        conn.commit()
        
        print("[SUCCESS] Hard reset and seeding completed:")
        print(f"  - Created {len(student_ids)} students")
        print(f"  - Created {len(student_ids)} finished attempts")
        print(f"  - At least one perfect student")
        print(f"  - Backup saved to: {backup_path}")
        
    except Exception as e:
        print(f"[ERROR] Seeding failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    hard_reset_and_seed()
