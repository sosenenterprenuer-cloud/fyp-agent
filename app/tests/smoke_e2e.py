#!/usr/bin/env python3
"""
End-to-end smoke tests for the Personalized Learning Recommendation AI application.
Tests the complete user journey from login to quiz submission.
"""

import os
import sys
import json
from pathlib import Path

# --- SSOT Database Path Configuration ---
# SINGLE SOURCE OF TRUTH for DB path (Windows absolute)
DB_PATH = Path(r"C:\Users\Sudarshan\Downloads\fyp-cursor-main (4)\fyp-cursor-main\app\instance\pla.db")

def ensure_db_dir():
    """Ensure database directory exists and set environment variable."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    os.environ["PLA_DB"] = str(DB_PATH)  # also set env for any code that reads PLA_DB
    return DB_PATH

# Add app directory to path
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, app_dir)

def main():
    """Run comprehensive smoke tests."""
    print("=== SMOKE E2E TESTS ===")
    
    # Use SSOT database path
    db_path = str(ensure_db_dir())
    
    print(f"DB path: {db_path}")
    
    # Step 1: Ensure dev_doctor.py passes
    print("\n1. Running dev_doctor.py...")
    import subprocess
    result = subprocess.run([sys.executable, os.path.join(app_dir, "scripts", "dev_doctor.py")], 
                           capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: dev_doctor.py failed with return code {result.returncode}")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
        return 1
    print("OK: dev_doctor.py passed")
    
    # Step 2: Test Flask application
    print("\n2. Testing Flask application...")
    try:
        from app import app
        
        with app.test_client() as c:
            # Test 1: Anonymous pages
            print("   Testing anonymous pages...")
            r = c.get('/')
            if r.status_code != 200:
                print(f"   ERROR: Index page failed: {r.status_code}")
                return 1
            print("   OK: Index page loads")
            
            r = c.get('/login')
            if r.status_code != 200:
                print(f"   ERROR: Login page failed: {r.status_code}")
                return 1
            print("   OK: Login page loads")
            
            # Test 2: Student login
            print("   Testing student login...")
            r = c.post('/login', data={
                'email': 'ngenji@demo.edu',
                'password': 'Student123!'
            })
            if r.status_code != 302:
                print(f"   ERROR: Student login failed: {r.status_code}")
                return 1
            print("   OK: Student login successful")
            
            # Follow redirect to dashboard
            r = c.get(r.headers['Location'])
            if r.status_code != 200:
                print(f"   ERROR: Dashboard redirect failed: {r.status_code}")
                return 1
            print("   OK: Dashboard loads")
            
            # Test 3: Quiz page
            print("   Testing quiz page...")
            r = c.get('/quiz')
            if r.status_code != 200:
                print(f"   ERROR: Quiz page failed: {r.status_code}")
                return 1
            print("   OK: Quiz page loads")
            
            # Test 4: Quiz API (get real attempt_id from quiz page)
            print("   Testing quiz API...")
            # Get the quiz page to extract attempt_id
            quiz_content = c.get('/quiz').get_data(as_text=True)
            if 'attempt_id=' in quiz_content:
                start = quiz_content.find('attempt_id=') + 11
                end = quiz_content.find('`', start)
                attempt_id = quiz_content[start:end]
            else:
                print("   ERROR: Could not find attempt_id in quiz page")
                return 1
            
            r = c.get(f'/api/quiz_progressive?attempt_id={attempt_id}')
            if r.status_code != 200:
                print(f"   ERROR: Quiz API failed: {r.status_code}")
                content = r.get_data(as_text=True)
                print(f"   Content: {content[:200]}...")
                return 1
            
            data = r.get_json()
            questions = data.get('questions', [])
            if len(questions) != 30:
                print(f"   ERROR: Expected 30 questions, got {len(questions)}")
                return 1
            print("   OK: Quiz API returns 30 questions")
            
            # Test 5: Quiz submission (simulate with 2-3 answers)
            print("   Testing quiz submission...")
            sample_answers = []
            for i, q in enumerate(questions[:3]):  # First 3 questions
                options = list(q['options'].keys())
                chosen_option = options[0]  # Choose first option
                sample_answers.append({
                    'quiz_id': q['quiz_id'],
                    'chosen_text': q['options'][chosen_option],
                    'time_sec': 30
                })
            
            r = c.post('/submit', 
                      data=json.dumps({'attempt_id': int(attempt_id), 'answers': sample_answers}),
                      content_type='application/json')
            if r.status_code != 200:
                print(f"   ERROR: Quiz submission failed: {r.status_code}")
                content = r.get_data(as_text=True)
                print(f"   Content: {content[:200]}...")
                return 1
            print("   OK: Quiz submission successful")
            
            # Test 6: Logout
            print("   Testing logout...")
            r = c.get('/logout')
            if r.status_code != 302:
                print(f"   ERROR: Logout failed: {r.status_code}")
                return 1
            print("   OK: Logout successful")
            
            # Test 7: Verify logged out
            r = c.get('/quiz')
            if r.status_code != 302:  # Should redirect to login
                print(f"   ERROR: Quiz access after logout should redirect: {r.status_code}")
                return 1
            print("   OK: Quiz access properly blocked after logout")
            
        print("\n[SUCCESS] All smoke tests passed!")
        return 0
        
    except Exception as e:
        print(f"ERROR: Smoke test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())