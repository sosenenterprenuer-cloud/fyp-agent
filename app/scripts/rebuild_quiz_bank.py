#!/usr/bin/env python3
"""
Rebuild quiz bank script.
Removes the legacy nf_level column and rebuilds the quiz table with only required columns.
"""

import os
import sys
import sqlite3
import json
from pathlib import Path

# Get the app directory (parent of scripts)
APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = os.path.join(APP_DIR, "pla.db")

# Import the embedded quiz bank from app.py
sys.path.insert(0, str(APP_DIR))
from app import QUIZ_BANK_30

def rebuild_quiz_bank():
    """Rebuild the quiz table without the legacy nf_level column."""
    if not os.path.exists(DB_PATH):
        print("[ERROR] Database file not found at:", DB_PATH)
        sys.exit(2)
    
    # Create backup
    backup_path = os.path.join(APP_DIR, "backups", f"pla_rebuild_{int(time.time())}.db")
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
        # Step 1: Create new quiz table without nf_level
        print("[REBUILD] Creating new quiz table schema...")
        cursor.execute("DROP TABLE IF EXISTS quiz_new")
        cursor.execute("""
            CREATE TABLE quiz_new (
                quiz_id INTEGER PRIMARY KEY,
                question TEXT NOT NULL,
                options_text TEXT,
                correct_answer TEXT NOT NULL,
                concept_tag TEXT,
                explanation TEXT,
                two_category TEXT
            )
        """)
        
        # Step 2: Copy data from old table to new table (excluding nf_level)
        print("[REBUILD] Migrating data to new schema...")
        cursor.execute("""
            INSERT INTO quiz_new (quiz_id, question, options_text, correct_answer, concept_tag, explanation, two_category)
            SELECT quiz_id, question, options_text, correct_answer, concept_tag, explanation, two_category
            FROM quiz
        """)
        
        # Step 3: Drop old table and rename new table
        print("[REBUILD] Replacing old table...")
        cursor.execute("DROP TABLE quiz")
        cursor.execute("ALTER TABLE quiz_new RENAME TO quiz")
        
        # Step 4: Recreate indexes if any
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_category ON quiz(two_category)")
        
        # Step 5: Verify the new schema
        cursor.execute("PRAGMA table_info(quiz)")
        columns = cursor.fetchall()
        
        print("[REBUILD] New quiz table schema:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'}")
        
        # Step 6: Verify data integrity
        cursor.execute("SELECT COUNT(*) as count FROM quiz")
        total_count = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT two_category, COUNT(*) as count 
            FROM quiz 
            GROUP BY two_category
        """)
        categories = cursor.fetchall()
        
        print(f"[REBUILD] Data verification:")
        print(f"  - Total questions: {total_count}")
        for cat in categories:
            print(f"  - {cat['two_category']}: {cat['count']}")
        
        if total_count != 30:
            print(f"[WARNING] Expected 30 questions, found {total_count}")
        
        conn.commit()
        print("[SUCCESS] Quiz table rebuilt successfully without nf_level column")
        
    except Exception as e:
        print(f"[ERROR] Rebuild failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    import time
    rebuild_quiz_bank()


