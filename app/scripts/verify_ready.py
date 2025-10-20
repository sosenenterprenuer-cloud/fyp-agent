#!/usr/bin/env python3
"""
Verify database is ready for the application.
Checks for nf_level absence, 30 questions with 15/15 split, and required tables.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Configuration
APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = os.getenv("PLA_DB", os.path.join(APP_DIR, "pla.db"))

def check_database_exists():
    """Check if database file exists."""
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        return False
    return True

def check_no_nf_level():
    """Verify no nf_level column exists in quiz table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Get quiz table schema
        columns = conn.execute("PRAGMA table_info(quiz)").fetchall()
        column_names = [col[1] for col in columns]
        
        if 'nf_level' in column_names:
            print("[ERROR] Found forbidden 'nf_level' column in quiz table")
            return False
        
        print("[OK] No 'nf_level' column found")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to check quiz schema: {e}")
        return False
    finally:
        conn.close()

def check_quiz_bank():
    """Verify 30 questions with 15/15 split."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Count total questions
        total_count = conn.execute("SELECT COUNT(*) as count FROM quiz").fetchone()['count']
        
        if total_count != 30:
            print(f"[ERROR] Expected 30 questions, found {total_count}")
            return False
        
        # Check category distribution
        categories = conn.execute("""
            SELECT two_category, COUNT(*) as count 
            FROM quiz 
            GROUP BY two_category
        """).fetchall()
        
        fund_count = 0
        norm_count = 0
        
        for cat in categories:
            if cat['two_category'] == 'Data Modeling & DBMS Fundamentals':
                fund_count = cat['count']
            elif cat['two_category'] == 'Normalization & Dependencies':
                norm_count = cat['count']
        
        if fund_count != 15:
            print(f"[ERROR] Expected 15 Fundamentals questions, found {fund_count}")
            return False
        
        if norm_count != 15:
            print(f"[ERROR] Expected 15 Normalization questions, found {norm_count}")
            return False
        
        print(f"[OK] Quiz bank: {total_count} questions ({fund_count} Fundamentals, {norm_count} Normalization)")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to check quiz bank: {e}")
        return False
    finally:
        conn.close()

def check_required_tables():
    """Verify all required tables exist."""
    required_tables = ['student', 'lecturer', 'quiz', 'attempt', 'response', 'feedback']
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Get all tables
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t['name'] for t in tables]
        
        missing_tables = []
        for table in required_tables:
            if table not in table_names:
                missing_tables.append(table)
        
        if missing_tables:
            print(f"[ERROR] Missing required tables: {missing_tables}")
            return False
        
        print(f"[OK] All required tables exist: {', '.join(required_tables)}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to check tables: {e}")
        return False
    finally:
        conn.close()

def check_data_integrity():
    """Check basic data integrity."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Check for students
        student_count = conn.execute("SELECT COUNT(*) as count FROM student").fetchone()['count']
        print(f"[OK] Students: {student_count}")
        
        # Check for attempts
        attempt_count = conn.execute("SELECT COUNT(*) as count FROM attempt").fetchone()['count']
        print(f"[OK] Attempts: {attempt_count}")
        
        # Check for responses
        response_count = conn.execute("SELECT COUNT(*) as count FROM response").fetchone()['count']
        print(f"[OK] Responses: {response_count}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to check data integrity: {e}")
        return False
    finally:
        conn.close()

def main():
    """Main verification function."""
    print("=== DATABASE READINESS VERIFICATION ===")
    print(f"Database: {DB_PATH}")
    print()
    
    all_checks_passed = True
    
    # Run all checks
    checks = [
        ("Database exists", check_database_exists),
        ("No nf_level column", check_no_nf_level),
        ("Quiz bank (30 questions, 15/15)", check_quiz_bank),
        ("Required tables", check_required_tables),
        ("Data integrity", check_data_integrity)
    ]
    
    for check_name, check_func in checks:
        print(f"Checking {check_name}...")
        if not check_func():
            all_checks_passed = False
        print()
    
    if all_checks_passed:
        print("[SUCCESS] ALL CHECKS PASSED - Database is ready!")
        sys.exit(0)
    else:
        print("[ERROR] SOME CHECKS FAILED - Database is not ready")
        print("Run 'python scripts/reset_and_seed_17.py --with-attempts' to fix")
        sys.exit(1)

if __name__ == "__main__":
    main()
