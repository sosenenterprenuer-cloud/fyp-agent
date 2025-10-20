#!/usr/bin/env python3
"""
Development doctor - comprehensive database and codebase health check.
"""

import os
import sys
import sqlite3
import glob
from pathlib import Path

# --- SSOT Database Path Configuration ---
# SINGLE SOURCE OF TRUTH for DB path (Windows absolute)
DB_PATH = Path(r"C:\Users\Sudarshan\Downloads\fyp-cursor-main (4)\fyp-cursor-main\app\instance\pla.db")

def ensure_db_dir():
    """Ensure database directory exists and set environment variable."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    os.environ["PLA_DB"] = str(DB_PATH)  # also set env for any code that reads PLA_DB
    return DB_PATH

def main():
    """Run comprehensive development doctor checks."""
    print("=== DEVELOPMENT DOCTOR ===")
    
    # Use SSOT database path
    db_path = str(ensure_db_dir())
    
    print(f"App DB path: {db_path}")
    print(f"ENV: {'PLA_DB' if 'PLA_DB' in os.environ else 'default'}")
    
    # Check 1: Database path consistency
    print("\n1. Database Path Consistency:")
    if not os.path.exists(db_path):
        print(f"ERROR: Database file not found at {os.path.abspath(db_path)}")
        return 1
    print("OK: Database file exists")
    
    # Check 2: Required tables exist
    print("\n2. Required Tables:")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        required_tables = {'student', 'attempt', 'quiz', 'response', 'feedback', 'lecturer'}
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {t['name'] for t in tables}
        
        missing_tables = required_tables - table_names
        if missing_tables:
            print(f"ERROR: Missing tables: {missing_tables}")
            return 1
        print("OK: All required tables exist")
        
        # Check 3: Column schema matches expectations
        print("\n3. Column Schema:")
        for table in required_tables:
            columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
            column_names = [col[1] for col in columns]
            
            # Check for forbidden NF columns
            nf_columns = [col for col in column_names if col.startswith('nf_')]
            if nf_columns:
                print(f"ERROR: Forbidden NF columns in {table}: {nf_columns}")
                return 1
        
        print("OK: No forbidden NF columns found")
        
        # Check 4: Quiz bank (30 questions, 15/15 split)
        print("\n4. Quiz Bank:")
        quiz_count = conn.execute("SELECT COUNT(*) FROM quiz").fetchone()[0]
        if quiz_count != 30:
            print(f"ERROR: Expected 30 questions, found {quiz_count}")
            return 1
        print("OK: 30 questions found")
        
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
        
        if fund_count != 15 or norm_count != 15:
            print(f"ERROR: Expected 15/15 split, found {fund_count}/{norm_count}")
            return 1
        print("OK: 15/15 category split correct")
        
        # Check 5: No legacy NF references in codebase
        print("\n5. Codebase NF References:")
        offenders = []
        for pattern in ["**/*.py", "**/*.sql", "**/*.html"]:
            for p in glob.glob(pattern, recursive=True):
                # Skip utility/check scripts
                if any(skip in p.lower() for skip in ['dev_doctor', 'check_forbidden', 'verify_ready', 'rebuild']):
                    continue
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if 'nf_scope' in content or 'nf_level' in content:
                            offenders.append(p)
                except:
                    pass
        
        if offenders:
            print(f"ERROR: Legacy NF references found in: {offenders}")
            return 1
        print("OK: No legacy NF references in codebase")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: Database check failed: {e}")
        return 1
    
    print("\n[SUCCESS] All checks passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())