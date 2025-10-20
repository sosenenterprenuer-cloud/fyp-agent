#!/usr/bin/env python3
"""
Export student credentials to CSV for demo distribution.
Outputs a sandbox: data/generated/student_credentials.csv
"""

import os
import sys
import sqlite3
import csv
from pathlib import Path

# Configuration
APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = os.getenv("PLA_DB", os.path.join(APP_DIR, "pla.db"))
OUTPUT_DIR = os.path.join(APP_DIR, "data", "generated")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "student_credentials.csv")

def export_credentials():
    """Export all student credentials to CSV."""
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Get all students
        students = conn.execute("""
            SELECT name, email, program, created_at
            FROM student
            ORDER BY student_id
        """).fetchall()
        
        if not students:
            print("[ERROR] No students found in database")
            sys.exit(1)
        
        # Write CSV
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Email', 'Password', 'Program', 'Created At'])
            
            for student in students:
                # Default password for all students
                writer.writerow([
                    student['name'],
                    student['email'],
                    'Student123!',  # Default password
                    student['program'] or 'BIT',
                    student['created_at']
                ])
        
        print(f"[SUCCESS] Exported {len(students)} student credentials")
        print(f"Output file: {OUTPUT_FILE}")
        
        # Also print to console for easy copy-paste
        print("\n[CREDENTIALS] Student accounts:")
        for student in students:
            print(f"  - {student['name']} ({student['email']}) - Password: Student123!")
        
        # Check for lecturer
        lecturer = conn.execute("""
            SELECT name, email FROM lecturer LIMIT 1
        """).fetchone()
        
        if lecturer:
            print(f"\n[CREDENTIALS] Lecturer account:")
            print(f"  - {lecturer['name']} ({lecturer['email']}) - Password: Admin!234")
        
    except Exception as e:
        print(f"[ERROR] Export failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

def main():
    """Main function."""
    print("=== EXPORT STUDENT CREDENTIALS ===")
    print(f"Database: {DB_PATH}")
    print(f"Output: {OUTPUT_FILE}")
    print()
    
    export_credentials()

if __name__ == "__main__":
    main()


