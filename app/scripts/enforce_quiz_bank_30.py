#!/usr/bin/env python3
"""
Quiz bank validation script.
Fails if the 'quiz' table does not have exactly 30 questions.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Get the app directory (parent of scripts)
APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = os.path.join(APP_DIR, "pla.db")

def validate_quiz_bank():
    """Validate that the quiz bank has exactly 30 questions."""
    if not os.path.exists(DB_PATH):
        print("[ERROR] Database file not found at:", DB_PATH)
        sys.exit(2)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check if quiz table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quiz'")
        if not cursor.fetchone():
            print("[ERROR] Quiz table does not exist")
            sys.exit(3)
        
        # Count total questions
        cursor.execute("SELECT COUNT(*) as count FROM quiz")
        total_count = cursor.fetchone()['count']
        
        if total_count != 30:
            print(f"[ERROR] Expected 30 questions, found {total_count}")
            sys.exit(4)
        
        # Check category distribution
        cursor.execute("""
            SELECT two_category, COUNT(*) as count 
            FROM quiz 
            GROUP BY two_category
        """)
        categories = cursor.fetchall()
        
        fund_count = 0
        norm_count = 0
        
        for row in categories:
            if row['two_category'] == 'Data Modeling & DBMS Fundamentals':
                fund_count = row['count']
            elif row['two_category'] == 'Normalization & Dependencies':
                norm_count = row['count']
        
        if fund_count != 15:
            print(f"[ERROR] Expected 15 Fundamentals questions, found {fund_count}")
            sys.exit(5)
        
        if norm_count != 15:
            print(f"[ERROR] Expected 15 Normalization questions, found {norm_count}")
            sys.exit(6)
        
        # Validate question structure
        cursor.execute("""
            SELECT quiz_id, question, two_category, correct_answer, explanation
            FROM quiz
            ORDER BY quiz_id
        """)
        questions = cursor.fetchall()
        
        for q in questions:
            if not q['question'] or not q['question'].strip():
                print(f"[ERROR] Question {q['quiz_id']} has empty question")
                sys.exit(7)
            
            if q['two_category'] not in ['Data Modeling & DBMS Fundamentals', 'Normalization & Dependencies']:
                print(f"[ERROR] Question {q['quiz_id']} has invalid category: {q['two_category']}")
                sys.exit(8)
            
            if not q['correct_answer'] or not q['correct_answer'].strip():
                print(f"[ERROR] Question {q['quiz_id']} has empty correct_answer")
                sys.exit(9)
            
            if not q['explanation'] or not q['explanation'].strip():
                print(f"[ERROR] Question {q['quiz_id']} has empty explanation")
                sys.exit(10)
        
        print("[OK] Quiz bank validation passed:")
        print(f"  - Total questions: {total_count}")
        print(f"  - Fundamentals: {fund_count}")
        print(f"  - Normalization: {norm_count}")
        print("  - All questions have required fields")
        
    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    validate_quiz_bank()