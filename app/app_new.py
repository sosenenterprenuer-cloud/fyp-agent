#!/usr/bin/env python3
"""
Personalized Learning Recommendation AI - Flask Application
Implements the SSOT requirements with canonical schema and two-topic model.
"""

import os
import json
import sqlite3
import random
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, g, session, request, redirect, url_for,
    render_template, flash, jsonify
)
from dotenv import load_dotenv

# --- Configuration & Setup ---
load_dotenv()
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-plai")
app.config["JSON_SORT_KEYS"] = False

# Database configuration
DB_PATH = os.environ.get("PLA_DB", os.path.join(os.path.dirname(__file__), "pla.db"))

# --- Database Helper ---
def get_db():
    """Get database connection with proper configuration."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

def is_db_ready() -> bool:
    """Check if database is ready with required tables and data."""
    try:
        conn = get_db()
        # Check required tables exist
        req_tables = {'quiz', 'student', 'attempt', 'response', 'feedback', 'lecturer'}
        names = {r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not req_tables.issubset(names):
            return False
        
        # Check quiz has data
        quiz_count = conn.execute("SELECT COUNT(*) FROM quiz").fetchone()[0]
        if quiz_count < 30:
            return False
            
        return True
    except Exception:
        return False

@app.teardown_appcontext
def close_db(error):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Startup Guard ---
@app.before_request
def startup_guard():
    """Verify database is ready before first request."""
    if hasattr(g, 'db_checked'):
        return
    g.db_checked = True
    
    try:
        conn = get_db()
        
        # Use simplified database readiness check
        if not is_db_ready():
            raise Exception("Database not ready")
        
        # Check required tables
        required_tables = ['student', 'lecturer', 'quiz', 'attempt', 'response', 'feedback']
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t['name'] for t in tables]
        
        missing_tables = [t for t in required_tables if t not in table_names]
        if missing_tables:
            raise Exception(f"Missing required tables: {missing_tables}")
            
    except Exception as e:
        # Render db_not_ready.html with repair command
        return render_template('db_not_ready.html', error=str(e), 
                             repair_command="python scripts/reset_and_seed_17.py --with-attempts")

# --- Authentication Decorators ---
def login_required(f):
    """Require user to be logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    """Require student role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'student':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def lecturer_required(f):
    """Require lecturer role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'lecturer':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
def index():
    """Home page."""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for students and lecturers."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        conn = get_db()
        
        # Check lecturer first
        lecturer = conn.execute(
            "SELECT lecturer_id, name, password_hash FROM lecturer WHERE email = ?",
            (email,)
        ).fetchone()
        
        if lecturer and check_password_hash(lecturer['password_hash'], password):
            session['user_id'] = lecturer['lecturer_id']
            session['role'] = 'lecturer'
            session['name'] = lecturer['name']
            return redirect(url_for('admin'))
        
        # Check student
        student = conn.execute(
            "SELECT student_id, name, password_hash FROM student WHERE email = ?",
            (email,)
        ).fetchone()
        
        if student and check_password_hash(student['password_hash'], password):
            session['user_id'] = student['student_id']
            session['role'] = 'student'
            session['name'] = student['name']
            return redirect(url_for('student_dashboard', student_id=student['student_id']))
        
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Student registration."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not all([name, email, password]):
            flash('Please fill in all fields', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('register.html')
        
        conn = get_db()
        
        # Check if email already exists
        existing = conn.execute(
            "SELECT student_id FROM student WHERE email = ?",
            (email,)
        ).fetchone()
        
        if existing:
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create student
        password_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO student (name, email, password_hash, program) VALUES (?, ?, ?, ?)",
            (name, email, password_hash, 'BIT')
        )
        conn.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logout user."""
    session.clear()
    return redirect(url_for('index'))

# --- Student Routes ---
@app.route('/student/<int:student_id>')
@student_required
def student_dashboard(student_id):
    """Student dashboard with latest attempt metrics."""
    if session['user_id'] != student_id:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    # Get latest finished attempt
    latest_attempt = conn.execute("""
        SELECT * FROM attempt 
        WHERE student_id = ? AND finished_at IS NOT NULL 
        ORDER BY finished_at DESC LIMIT 1
    """, (student_id,)).fetchone()
    
    if not latest_attempt:
        return render_template('student_dashboard.html', 
                             student={'name': session['name']},
                             latest_attempt=None,
                             fund_pct=0,
                             norm_pct=0,
                             unlocked=False,
                             attempts=[],
                             labels=[],
                             scores=[])
    
    # Calculate topic percentages for latest attempt
    responses = conn.execute("""
        SELECT r.is_correct, q.two_category
        FROM response r
        JOIN quiz q ON r.quiz_id = q.quiz_id
        WHERE r.attempt_id = ?
    """, (latest_attempt['attempt_id'],)).fetchall()
    
    fund_correct = sum(1 for r in responses if r['is_correct'] and r['two_category'] == 'Data Modeling & DBMS Fundamentals')
    fund_total = sum(1 for r in responses if r['two_category'] == 'Data Modeling & DBMS Fundamentals')
    norm_correct = sum(1 for r in responses if r['is_correct'] and r['two_category'] == 'Normalization & Dependencies')
    norm_total = sum(1 for r in responses if r['two_category'] == 'Normalization & Dependencies')
    
    fund_pct = round((fund_correct / fund_total * 100), 1) if fund_total > 0 else 0
    norm_pct = round((norm_correct / norm_total * 100), 1) if norm_total > 0 else 0
    
    # Check if unlocked (both topics 100%)
    unlocked = fund_pct == 100.0 and norm_pct == 100.0
    
    # Get all finished attempts for chart
    attempts = conn.execute("""
        SELECT * FROM attempt 
        WHERE student_id = ? AND finished_at IS NOT NULL 
        ORDER BY finished_at DESC LIMIT 10
    """, (student_id,)).fetchall()
    
    # Prepare chart data
    labels = [f"Attempt {i+1}" for i in range(len(attempts))]
    scores = [float(attempt['score_pct']) for attempt in attempts]
    
    return render_template('student_dashboard.html',
                         student={'name': session['name']},
                         latest_attempt=latest_attempt,
                         fund_pct=fund_pct,
                         norm_pct=norm_pct,
                         unlocked=unlocked,
                         attempts=attempts,
                         labels=labels,
                         scores=scores)

@app.route('/quiz')
@student_required
def quiz():
    """Quiz interface - 30 questions in random order."""
    conn = get_db()
    
    # Check for existing in-progress attempt
    existing_attempt = conn.execute("""
        SELECT attempt_id FROM attempt 
        WHERE student_id = ? AND finished_at IS NULL 
        ORDER BY started_at DESC LIMIT 1
    """, (session['user_id'],)).fetchone()
    
    if existing_attempt:
        flash('You have an existing quiz in progress. Continuing...', 'info')
        return render_template('quiz.html', attempt_id=existing_attempt['attempt_id'])
    
    # Create new attempt
    cursor = conn.execute("""
        INSERT INTO attempt (student_id, started_at, source) 
        VALUES (?, datetime('now'), 'web')
    """, (session['user_id'],))
    
    attempt_id = cursor.lastrowid
    conn.commit()
    
    return render_template('quiz.html', attempt_id=attempt_id)

@app.route('/api/quiz_progressive')
@student_required
def api_quiz_progressive():
    """Get 30 questions in random order with shuffled options."""
    conn = get_db()
    
    # Get all 30 questions
    questions = conn.execute("""
        SELECT quiz_id, question, options_json, correct_text, two_category, explanation
        FROM quiz
        ORDER BY RANDOM()
    """).fetchall()
    
    result = []
    for q in questions:
        # Parse options and shuffle them
        options = json.loads(q['options_json'])
        random.shuffle(options)
        
        # Map options to letters
        option_map = {chr(65 + i): options[i] for i in range(len(options))}
        
        result.append({
            'quiz_id': q['quiz_id'],
            'question': q['question'],
            'two_category': q['two_category'],
            'options': option_map,
            'explanation': q['explanation']
        })
    
    return jsonify({
        'attempt_id': request.args.get('attempt_id'),
        'questions': result
    })

@app.route('/submit', methods=['POST'])
@student_required
def submit_quiz():
    """Submit quiz answers and calculate scores."""
    data = request.get_json()
    attempt_id = data.get('attempt_id')
    answers = data.get('answers', [])
    
    if not attempt_id or not answers:
        return jsonify({'error': 'Missing attempt_id or answers'}), 400
    
    conn = get_db()
    
    # Verify attempt belongs to current user
    attempt = conn.execute("""
        SELECT * FROM attempt WHERE attempt_id = ? AND student_id = ?
    """, (attempt_id, session['user_id'])).fetchone()
    
    if not attempt:
        return jsonify({'error': 'Invalid attempt'}), 400
    
    # Process each answer
    correct_count = 0
    total_count = len(answers)
    
    for answer in answers:
        quiz_id = answer.get('quiz_id')
        answer_letter = answer.get('answer_letter', '')
        answer_text = answer.get('answer_text', '')
        response_time = answer.get('response_time', 0)
        
        # Get correct answer from database
        quiz = conn.execute("""
            SELECT correct_text, two_category FROM quiz WHERE quiz_id = ?
        """, (quiz_id,)).fetchone()
        
        if not quiz:
            continue
        
        # Check if correct
        is_correct = 1 if answer_text == quiz['correct_text'] else 0
        if is_correct:
            correct_count += 1
        
        # Store response
        conn.execute("""
            INSERT INTO response (attempt_id, student_id, quiz_id, answer_letter, answer_text, is_correct, response_time_s)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (attempt_id, session['user_id'], quiz_id, answer_letter, answer_text, is_correct, response_time))
    
    # Update attempt
    score_pct = round((correct_count / total_count * 100), 1) if total_count > 0 else 0
    conn.execute("""
        UPDATE attempt 
        SET finished_at = datetime('now'), items_total = ?, items_correct = ?, score_pct = ?
        WHERE attempt_id = ?
    """, (total_count, correct_count, score_pct, attempt_id))
    
    conn.commit()
    
    # Calculate topic percentages
    responses = conn.execute("""
        SELECT r.is_correct, q.two_category
        FROM response r
        JOIN quiz q ON r.quiz_id = q.quiz_id
        WHERE r.attempt_id = ?
    """, (attempt_id,)).fetchall()
    
    fund_correct = sum(1 for r in responses if r['is_correct'] and r['two_category'] == 'Data Modeling & DBMS Fundamentals')
    fund_total = sum(1 for r in responses if r['two_category'] == 'Data Modeling & DBMS Fundamentals')
    norm_correct = sum(1 for r in responses if r['is_correct'] and r['two_category'] == 'Normalization & Dependencies')
    norm_total = sum(1 for r in responses if r['two_category'] == 'Normalization & Dependencies')
    
    fund_pct = round((fund_correct / fund_total * 100), 1) if fund_total > 0 else 0
    norm_pct = round((norm_correct / norm_total * 100), 1) if norm_total > 0 else 0
    
    # Check if unlocked
    unlocked = fund_pct == 100.0 and norm_pct == 100.0
    
    return jsonify({
        'attempt_id': attempt_id,
        'score_pct': score_pct,
        'fund_pct': fund_pct,
        'norm_pct': norm_pct,
        'unlocked': unlocked
    })

@app.route('/review/<int:attempt_id>')
@student_required
def review(attempt_id):
    """Review quiz results with explanations."""
    conn = get_db()
    
    # Get attempt
    attempt = conn.execute("""
        SELECT * FROM attempt WHERE attempt_id = ? AND student_id = ?
    """, (attempt_id, session['user_id'])).fetchone()
    
    if not attempt:
        flash('Attempt not found', 'error')
        return redirect(url_for('student_dashboard', student_id=session['user_id']))
    
    # Get responses with quiz details
    responses = conn.execute("""
        SELECT r.*, q.question, q.correct_text, q.two_category, q.explanation
        FROM response r
        JOIN quiz q ON r.quiz_id = q.quiz_id
        WHERE r.attempt_id = ?
        ORDER BY r.quiz_id
    """, (attempt_id,)).fetchall()
    
    # Calculate topic percentages
    fund_correct = sum(1 for r in responses if r['is_correct'] and r['two_category'] == 'Data Modeling & DBMS Fundamentals')
    fund_total = sum(1 for r in responses if r['two_category'] == 'Data Modeling & DBMS Fundamentals')
    norm_correct = sum(1 for r in responses if r['is_correct'] and r['two_category'] == 'Normalization & Dependencies')
    norm_total = sum(1 for r in responses if r['two_category'] == 'Normalization & Dependencies')
    
    fund_pct = round((fund_correct / fund_total * 100), 1) if fund_total > 0 else 0
    norm_pct = round((norm_correct / norm_total * 100), 1) if norm_total > 0 else 0
    
    # Check if unlocked
    unlocked = fund_pct == 100.0 and norm_pct == 100.0
    
    return render_template('review.html',
                         attempt=attempt,
                         responses=responses,
                         fund_pct=fund_pct,
                         norm_pct=norm_pct,
                         unlocked=unlocked)

@app.route('/thanks')
@student_required
def thanks():
    """Thanks page after quiz completion."""
    return render_template('thanks.html')

@app.route('/api/feedback', methods=['POST'])
@student_required
def api_feedback():
    """Submit feedback (not stored, just success message)."""
    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment', '')
    
    if not rating or rating < 1 or rating > 5:
        return jsonify({'error': 'Invalid rating'}), 400
    
    # Just return success - not storing feedback as per requirements
    return jsonify({'message': 'Feedback submitted successfully'})

# --- Lecturer Routes ---
@app.route('/admin')
@lecturer_required
def admin():
    """Lecturer admin dashboard."""
    conn = get_db()
    
    # Get basic stats
    student_count = conn.execute("SELECT COUNT(*) FROM student").fetchone()[0]
    attempt_count = conn.execute("SELECT COUNT(*) FROM attempt").fetchone()[0]
    response_count = conn.execute("SELECT COUNT(*) FROM response").fetchone()[0]
    
    # Get category accuracy
    category_stats = conn.execute("""
        SELECT q.two_category, 
               AVG(r.is_correct) as avg_correctness,
               COUNT(r.response_id) as response_count
        FROM quiz q
        LEFT JOIN response r ON q.quiz_id = r.quiz_id
        GROUP BY q.two_category
    """).fetchall()
    
    # Get 14-day chart data
    chart_data = conn.execute("""
        SELECT DATE(finished_at) as date, COUNT(*) as attempts
        FROM attempt 
        WHERE finished_at IS NOT NULL 
        AND finished_at >= datetime('now', '-14 days')
        GROUP BY DATE(finished_at)
        ORDER BY date
    """).fetchall()
    
    return render_template('admin_overview.html',
                         student_count=student_count,
                         attempt_count=attempt_count,
                         response_count=response_count,
                         category_stats=category_stats,
                         chart_data=chart_data)

@app.route('/admin/students')
@lecturer_required
def admin_students():
    """List all students."""
    conn = get_db()
    
    students = conn.execute("""
        SELECT s.*, COUNT(a.attempt_id) as attempt_count
        FROM student s
        LEFT JOIN attempt a ON s.student_id = a.student_id
        GROUP BY s.student_id
        ORDER BY s.name
    """).fetchall()
    
    return render_template('admin_students.html', students=students)

@app.route('/admin/rankings')
@lecturer_required
def admin_rankings():
    """Student rankings by performance."""
    conn = get_db()
    
    rankings = conn.execute("""
        SELECT s.name, s.email,
               AVG(a.score_pct) as avg_score,
               MAX(a.score_pct) as best_score,
               MIN(a.score_pct) as last_score,
               COUNT(a.attempt_id) as attempt_count
        FROM student s
        LEFT JOIN attempt a ON s.student_id = a.student_id
        WHERE a.finished_at IS NOT NULL
        GROUP BY s.student_id
        ORDER BY avg_score DESC
    """).fetchall()
    
    return render_template('admin_rankings.html', rankings=rankings)

@app.route('/admin/questions')
@lecturer_required
def admin_questions():
    """Question performance statistics."""
    conn = get_db()
    
    questions = conn.execute("""
        SELECT q.quiz_id, q.question, q.two_category,
               AVG(r.is_correct) as correct_rate,
               COUNT(r.response_id) as response_count
        FROM quiz q
        LEFT JOIN response r ON q.quiz_id = r.quiz_id
        GROUP BY q.quiz_id
        ORDER BY q.quiz_id
    """).fetchall()
    
    return render_template('admin_questions.html', questions=questions)

@app.route('/admin/analytics')
@lecturer_required
def admin_analytics():
    """Detailed analytics."""
    conn = get_db()
    
    # Per-student per-question response times
    response_times = conn.execute("""
        SELECT s.name, q.quiz_id, q.question,
               AVG(r.response_time_s) as avg_time,
               COUNT(r.response_id) as response_count
        FROM student s
        JOIN response r ON s.student_id = r.student_id
        JOIN quiz q ON r.quiz_id = q.quiz_id
        GROUP BY s.student_id, q.quiz_id
        HAVING response_count >= 5
        ORDER BY avg_time DESC
    """).fetchall()
    
    return render_template('admin_analytics.html', response_times=response_times)

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
