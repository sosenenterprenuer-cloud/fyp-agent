#!/usr/bin/env python3
"""
Generic quiz bank loader.
Used to load data from a CSV into the quiz table.
"""

import os
import sys
import csv
import json
import sqlite3
from pathlib import Path

# Get the app directory (parent of scripts)
APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = os.path.join(APP_DIR, "pla.db")

# Expected CSV headers
EXPECTED_HEADERS = [
    "question",
    "two_category", 
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_text",
    "explanation"
]

# Allowed categories
ALLOWED_CATEGORIES = [
    "Data Modeling & DBMS Fundamentals",
    "Normalization & Dependencies"
]

def import_questions_from_csv(csv_path):
    """Import questions from CSV file into quiz table."""
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV file not found: {csv_path}")
        sys.exit(2)
    
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database file not found: {DB_PATH}")
        sys.exit(3)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Read CSV file
        print(f"[IMPORT] Reading CSV file: {csv_path}")
        questions = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Validate headers
            if reader.fieldnames != EXPECTED_HEADERS:
                print(f"[ERROR] Invalid CSV headers. Expected: {EXPECTED_HEADERS}")
                print(f"Found: {reader.fieldnames}")
                sys.exit(4)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                # Validate required fields
                if not row['question'] or not row['question'].strip():
                    print(f"[ERROR] Row {row_num}: Empty question")
                    sys.exit(5)
                
                if row['two_category'] not in ALLOWED_CATEGORIES:
                    print(f"[ERROR] Row {row_num}: Invalid category '{row['two_category']}'")
                    print(f"Allowed categories: {ALLOWED_CATEGORIES}")
                    sys.exit(6)
                
                # Validate options
                options = [
                    row['option_a'].strip(),
                    row['option_b'].strip(), 
                    row['option_c'].strip(),
                    row['option_d'].strip()
                ]
                
                if any(not opt for opt in options):
                    print(f"[ERROR] Row {row_num}: All 4 options must be filled")
                    sys.exit(7)
                
                # Validate correct answer is in options
                correct_text = row['correct_text'].strip()
                if correct_text not in options:
                    print(f"[ERROR] Row {row_num}: correct_text not in options")
                    print(f"Correct: '{correct_text}'")
                    print(f"Options: {options}")
                    sys.exit(8)
                
                if not row['explanation'] or not row['explanation'].strip():
                    print(f"[ERROR] Row {row_num}: Empty explanation")
                    sys.exit(9)
                
                # Store options as JSON
                options_json = json.dumps(options)
                
                questions.append({
                    'question': row['question'].strip(),
                    'two_category': row['two_category'].strip(),
                    'options_text': options_json,
                    'correct_answer': correct_text,
                    'explanation': row['explanation'].strip()
                })
        
        print(f"[IMPORT] Validated {len(questions)} questions")
        
        # Clear existing quiz data
        print("[IMPORT] Clearing existing quiz data...")
        cursor.execute("DELETE FROM response WHERE quiz_id IN (SELECT quiz_id FROM quiz)")
        cursor.execute("DELETE FROM quiz")
        
        # Insert new questions
        print("[IMPORT] Inserting questions...")
        for i, q in enumerate(questions, start=1):
            cursor.execute("""
                INSERT INTO quiz (question, options_text, correct_answer, concept_tag, two_category, explanation)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                q['question'],
                q['options_text'], 
                q['correct_answer'],
                'Database',  # Default concept_tag
                q['two_category'],
                q['explanation']
            ))
            
            if i % 10 == 0:
                print(f"  - Imported {i}/{len(questions)} questions")
        
        # Verify import
        cursor.execute("SELECT COUNT(*) as count FROM quiz")
        imported_count = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT two_category, COUNT(*) as count 
            FROM quiz 
            GROUP BY two_category
        """)
        categories = cursor.fetchall()
        
        conn.commit()
        
        print(f"[SUCCESS] Import completed:")
        print(f"  - Total questions: {imported_count}")
        for cat in categories:
            print(f"  - {cat['two_category']}: {cat['count']}")
        
        # Validate final state
        if imported_count != 30:
            print(f"[WARNING] Expected 30 questions, imported {imported_count}")
        
        fund_count = sum(cat['count'] for cat in categories if cat['two_category'] == ALLOWED_CATEGORIES[0])
        norm_count = sum(cat['count'] for cat in categories if cat['two_category'] == ALLOWED_CATEGORIES[1])
        
        if fund_count != 15 or norm_count != 15:
            print(f"[WARNING] Expected 15+15 distribution, found {fund_count}+{norm_count}")
        
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) != 2:
        print("Usage: python import_questions.py <csv_file>")
        print("Example: python import_questions.py ../data/quiz_bank.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    import_questions_from_csv(csv_path)

if __name__ == "__main__":
    main()
