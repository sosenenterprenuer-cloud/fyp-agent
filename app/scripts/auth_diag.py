#!/usr/bin/env python3
"""
Authentication diagnostic script.
Checks database readiness and credential validation.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Configuration
APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = os.environ.get("PLA_DB", os.path.join(APP_DIR, "pla.db"))

def check_database():
    """Check database file and basic structure."""
    print(f"1) PLA_DB absolute path: {os.path.abspath(DB_PATH)}")
    
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database file does not exist: {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Check table existence
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t['name'] for t in tables]
        
        required_tables = ['student', 'lecturer']
        missing_tables = [t for t in required_tables if t not in table_names]
        
        if missing_tables:
            print(f"[ERROR] Missing required tables: {missing_tables}")
            return False
        
        return True, conn
        
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False

def check_counts(conn):
    """Check user counts."""
    try:
        students_count = conn.execute("SELECT COUNT(*) FROM student").fetchone()[0]
        lecturers_count = conn.execute("SELECT COUNT(*) FROM lecturer").fetchone()[0]
        
        print(f"2) Students: {students_count}, Lecturers: {lecturers_count}")
        
        return students_count, lecturers_count
        
    except Exception as e:
        print(f"[ERROR] Failed to get counts: {e}")
        return 0, 0

def check_credentials(conn):
    """Check first student credentials and password hash."""
    try:
        student = conn.execute("SELECT email, password_hash FROM student LIMIT 1").fetchone()
        
        if not student:
            print("[ERROR] No students found in database")
            return False
        
        email = student['email']
        password_hash = student['password_hash']
        
        print(f"3) First student email: {email}")
        
        if not password_hash:
            print("[ERROR] No password hash found")
            return False
        
        hash_prefix = password_hash[:12]
        is_hashed = password_hash.startswith(('pbkdf2:', 'scrypt:', 'argon2:'))
        
        print(f"4) Password hash prefix: {hash_prefix}...")
        print(f"5) Hash is properly hashed: {is_hashed}")
        
        if not is_hashed:
            print("[WARN] Password hash does not appear to be properly hashed")
            return False
        
        print("6) Password hash OK")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to check credentials: {e}")
        return False

def main():
    """Main diagnostic function."""
    print("=== AUTHENTICATION DIAGNOSTIC ===")
    print()
    
    # Check database
    db_result = check_database()
    if not db_result:
        print("\n[ERROR] Database check failed")
        sys.exit(1)
    
    if isinstance(db_result, tuple):
        conn = db_result[1]
    else:
        print("[ERROR] Database check returned unexpected result")
        sys.exit(1)
    
    try:
        # Check counts
        students_count, lecturers_count = check_counts(conn)
        
        # Check credentials
        if not check_credentials(conn):
            print("\n[ERROR] Credential check failed")
            sys.exit(1)
        
        print("\n[SUCCESS] All authentication checks passed!")
        print(f"Database ready with {students_count} students and {lecturers_count} lecturers")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
