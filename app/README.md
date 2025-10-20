# Personalized Learning Recommendation AI

A Flask-based educational platform for database concepts with adaptive learning and progress tracking.

## 🎯 Project Overview

This application implements a **two-topic model** with exactly **30 questions** (15/15 split) covering:
- **Data Modeling & DBMS Fundamentals** (15 questions)
- **Normalization & Dependencies** (15 questions)

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Virtual environment (recommended)

### Setup
1. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables:**
   ```bash
   # Create .env file
   echo "PLA_DB=pla.db" > .env
   echo "FLASK_SECRET=your-secret-key-here" >> .env
   ```

4. **Initialize database:**
   ```bash
   python scripts/reset_and_seed_17.py --with-attempts
   ```

5. **Verify setup:**
   ```bash
   python scripts/verify_ready.py
   ```

6. **Start the application:**
   ```bash
   python app.py
   ```

7. **Access the application:**
   - Open http://localhost:5000 in your browser
   - Use the exported credentials to login

## 📊 Database Schema

The application uses a canonical SQLite schema with the following tables:

- **student**: User accounts for students
- **lecturer**: Admin accounts for lecturers  
- **quiz**: 30 questions with two categories
- **attempt**: Quiz attempts with scoring
- **response**: Individual question responses
- **feedback**: User feedback (display only)

## 🔧 Scripts

### Core Scripts
- **`scripts/reset_and_seed_17.py`**: Reset database and seed with 17 students
- **`scripts/verify_ready.py`**: Verify database readiness
- **`scripts/check_forbidden.py`**: Check for forbidden strings (nf_level)
- **`scripts/export_credentials.py`**: Export student login credentials

### Usage Examples
```bash
# Reset and seed database
python scripts/reset_and_seed_17.py --with-attempts

# Verify database is ready
python scripts/verify_ready.py

# Check for forbidden strings
python scripts/check_forbidden.py

# Export student credentials
python scripts/export_credentials.py
```

## 👥 User Roles

### Students
- **Dashboard**: View progress, latest attempt metrics, unlock status
- **Quiz**: Take 30-question quizzes with randomized options
- **Review**: See detailed results with explanations
- **Unlock**: Access next topic when scoring 100% in both categories

### Lecturers (Read-Only)
- **Overview**: System statistics and performance metrics
- **Students**: Student roster with attempt counts
- **Rankings**: Student performance leaderboard
- **Questions**: Question-level performance analytics
- **Analytics**: Detailed response time analysis

## 🔐 Authentication

### Student Login
- **Email**: Use exported credentials (e.g., `mohamedaiman@demo.edu`)
- **Password**: `Student123!` (default for all students)

### Lecturer Login
- **Email**: `admin@lct.edu`
- **Password**: `Admin!234`

## 📁 Project Structure

```
app/
├── app.py                          # Main Flask application
├── schema.sql                      # Canonical database schema
├── requirements.txt                # Python dependencies
├── data/
│   ├── quiz_bank.csv              # 30 questions (15/15 split)
│   ├── students_17.csv             # 17 student accounts
│   └── generated/
│       └── student_credentials.csv # Exported login info
├── scripts/
│   ├── reset_and_seed_17.py       # Database reset and seeding
│   ├── verify_ready.py            # Database verification
│   ├── check_forbidden.py         # Forbidden string checker
│   └── export_credentials.py      # Credential exporter
├── templates/                      # Jinja2 templates
├── static/                        # CSS, JS assets
└── tests/                         # Test files
```

## 🛡️ Guardrails & Constraints

### Non-Negotiable Constraints
1. **No `nf_level` column**: Absolutely forbidden in any table
2. **Two topics only**: "Data Modeling & DBMS Fundamentals" and "Normalization & Dependencies"
3. **30 questions total**: Exactly 15 questions per topic
4. **Text-based scoring**: Compare answer text, not letters
5. **Latest attempt unlock**: Unlock based on most recent finished attempt

### Startup Guard
The application includes a startup guard that:
- Verifies no `nf_level` column exists
- Confirms 30 questions with 15/15 split
- Checks all required tables exist
- Shows `db_not_ready.html` if any check fails

## 🧪 Testing

### Run Tests
```bash
# Test the complete application
python test_final_app.py

# Test individual components
python scripts/verify_ready.py
python scripts/check_forbidden.py
```

### Test Coverage
- ✅ Database schema validation
- ✅ Quiz bank distribution (30 questions, 15/15 split)
- ✅ Flask application import
- ✅ Required scripts existence
- ✅ No forbidden strings (except in utility scripts)

## 🚨 Troubleshooting

### Common Issues

1. **Database not ready error**
   ```bash
   python scripts/reset_and_seed_17.py --with-attempts
   ```

2. **Forbidden string violations**
   ```bash
   python scripts/check_forbidden.py
   ```

3. **Missing dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database path issues**
   - Check `PLA_DB` environment variable
   - Ensure database file exists and is accessible

### Debug Mode
```bash
# Run with debug output
FLASK_DEBUG=1 python app.py
```

## 📈 Features

### Student Features
- **Adaptive Learning**: Progress tracking with topic-specific metrics
- **Unlock System**: Access next topic when achieving 100% in both categories
- **Detailed Review**: See chosen vs correct answers with explanations
- **Progress Charts**: Visual progress tracking over time

### Lecturer Features
- **Analytics Dashboard**: System-wide performance metrics
- **Student Management**: View all students and their progress
- **Question Analytics**: Per-question performance statistics
- **Response Time Analysis**: Identify slow/fast questions

## 🔄 Development

### Adding New Questions
1. Edit `data/quiz_bank.csv`
2. Ensure 15/15 split is maintained
3. Run `python scripts/reset_and_seed_17.py --with-attempts`

### Database Migrations
- Use `scripts/reset_and_seed_17.py` for major changes
- Always maintain 30-question constraint
- Never add `nf_level` column

### Code Quality
- Run `python scripts/check_forbidden.py` before commits
- Ensure all tests pass with `python test_final_app.py`
- Follow the two-topic model strictly

## 📝 License

This project is part of a personalized learning recommendation system for database education.

---

**Ready to use!** 🎉

Run `python app.py` and visit http://localhost:5000 to start using the application.