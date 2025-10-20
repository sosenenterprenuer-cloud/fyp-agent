#!/usr/bin/env python3
"""
Seed the quiz bank with 30 questions from the embedded QUIZ_BANK_30.
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

def seed_quiz_bank():
    """Seed the database with the 30 questions from QUIZ_BANK_30."""
    if not os.path.exists(DB_PATH):
        print("[ERROR] Database file not found at:", DB_PATH)
        sys.exit(2)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Clear existing quiz data
        print("[SEED] Clearing existing quiz data...")
        cursor.execute("DELETE FROM response WHERE quiz_id IN (SELECT quiz_id FROM quiz)")
        cursor.execute("DELETE FROM quiz")
        
        # Insert the 30 questions from QUIZ_BANK_30
        print("[SEED] Inserting 30 questions...")
        for i, q_data in enumerate(QUIZ_BANK_30, start=1):
            # Convert options to JSON format
            options_json = json.dumps(q_data['options'])
            
            cursor.execute("""
                INSERT INTO quiz (question, options_text, correct_answer, concept_tag, two_category, explanation)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                q_data['question'],
                options_json,
                q_data['correct_text'],
                'Database',  # Default concept_tag
                q_data['two_category'],
                q_data['explanation']
            ))
            
            if i % 10 == 0:
                print(f"  - Inserted {i}/30 questions")
        
        # Verify the insertion
        cursor.execute("SELECT COUNT(*) as count FROM quiz")
        total_count = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT two_category, COUNT(*) as count 
            FROM quiz 
            GROUP BY two_category
        """)
        categories = cursor.fetchall()
        
        conn.commit()
        
        print(f"[SUCCESS] Quiz bank seeded:")
        print(f"  - Total questions: {total_count}")
        for cat in categories:
            print(f"  - {cat['two_category']}: {cat['count']}")
        
        if total_count != 30:
            print(f"[ERROR] Expected 30 questions, found {total_count}")
            sys.exit(3)
        
        fund_count = sum(cat['count'] for cat in categories if cat['two_category'] == 'Data Modeling & DBMS Fundamentals')
        norm_count = sum(cat['count'] for cat in categories if cat['two_category'] == 'Normalization & Dependencies')
        
        if fund_count != 15 or norm_count != 15:
            print(f"[ERROR] Expected 15+15 distribution, found {fund_count}+{norm_count}")
            sys.exit(4)
        
    except Exception as e:
        print(f"[ERROR] Seeding failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    seed_quiz_bank()
