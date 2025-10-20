#!/usr/bin/env python3
"""
Legacy data cleanup script.
Deletes any old quiz rows/responses not tagged with the two final topics.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Get the app directory (parent of scripts)
APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = os.path.join(APP_DIR, "pla.db")

# Allowed topics
ALLOWED_TOPICS = [
    "Data Modeling & DBMS Fundamentals",
    "Normalization & Dependencies"
]

def cleanup_legacy_data():
    """Remove legacy quiz data that doesn't match the two final topics."""
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
            print("[WARNING] Quiz table does not exist")
            return
        
        # Find legacy quiz questions
        cursor.execute("""
            SELECT quiz_id, question, two_category 
            FROM quiz 
            WHERE two_category NOT IN (?, ?) OR two_category IS NULL OR two_category = ''
        """, ALLOWED_TOPICS)
        
        legacy_questions = cursor.fetchall()
        
        if not legacy_questions:
            print("[OK] No legacy quiz data found")
            return
        
        print(f"[CLEANUP] Found {len(legacy_questions)} legacy quiz questions:")
        for q in legacy_questions:
            category = q['two_category'] or 'NULL'
            print(f"  - Q{q['quiz_id']}: '{q['question'][:50]}...' (category: {category})")
        
        # Get quiz IDs to delete
        legacy_ids = [q['quiz_id'] for q in legacy_questions]
        
        # Delete related responses first (foreign key constraint)
        cursor.execute("""
            DELETE FROM response 
            WHERE quiz_id IN ({})
        """.format(','.join(['?'] * len(legacy_ids))), legacy_ids)
        
        deleted_responses = cursor.rowcount
        print(f"[CLEANUP] Deleted {deleted_responses} related responses")
        
        # Delete legacy quiz questions
        cursor.execute("""
            DELETE FROM quiz 
            WHERE quiz_id IN ({})
        """.format(','.join(['?'] * len(legacy_ids))), legacy_ids)
        
        deleted_questions = cursor.rowcount
        print(f"[CLEANUP] Deleted {deleted_questions} legacy quiz questions")
        
        # Verify remaining quiz count
        cursor.execute("SELECT COUNT(*) as count FROM quiz")
        remaining_count = cursor.fetchone()['count']
        
        # Check category distribution
        cursor.execute("""
            SELECT two_category, COUNT(*) as count 
            FROM quiz 
            GROUP BY two_category
        """)
        categories = cursor.fetchall()
        
        print(f"[CLEANUP] Remaining quiz questions: {remaining_count}")
        for cat in categories:
            print(f"  - {cat['two_category']}: {cat['count']}")
        
        # Validate final state
        if remaining_count != 30:
            print(f"[WARNING] Expected 30 questions after cleanup, found {remaining_count}")
        
        fund_count = sum(cat['count'] for cat in categories if cat['two_category'] == ALLOWED_TOPICS[0])
        norm_count = sum(cat['count'] for cat in categories if cat['two_category'] == ALLOWED_TOPICS[1])
        
        if fund_count != 15 or norm_count != 15:
            print(f"[WARNING] Expected 15+15 distribution, found {fund_count}+{norm_count}")
        
        conn.commit()
        print("[SUCCESS] Legacy data cleanup completed")
        
    except Exception as e:
        print(f"[ERROR] Cleanup failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_legacy_data()


