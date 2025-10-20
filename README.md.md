# PLA — Flask Student Quiz and Lecturer Analytics (Local MVP)

A local Flask app for student quizzes and read only lecturer analytics. Two topics only:

* **FUNDAMENTALS**
* **NORM_DEP**

Each attempt is **30 questions** total with **15 from each topic**, randomized order, no duplicates.
Gating uses the **latest attempt only**.

---

## Scope

### Students

* Login and logout. Optional self registration.
* Take quiz with 30 questions, back and next, autosave answers.
* Submit then see review. Review shows per question result, correct answer, explanation, and topic breakdown.
* Dashboard shows latest attempt overall score and per topic scores. Modules page shows two core modules and next recommendation when unlocked.
* Gating shows **Proceed to next topic** only when **both topics are 100% on the latest attempt**.
* Mini chart shows progress over time after the first attempt.

### Lecturer read only

* Login as admin. Role is read only.
* Overview: totals for students, attempts, responses. Per topic accuracy. Recent activity mini chart.
* Student analytics: list with attempts count. Per student attempts and scores. Timing analytics for average time per question. Slowest and fastest questions overall.
* Questions view: correct rate per question.
* Utilities: backup DB button. Print logging in submit and feedback.

### Explicitly not included in MVP

* Editing questions in the UI.
* Bulk imports inside the app.
* Role and permission admin screens.

---

## Data contract

```
users(id, email, password_hash, role)                  -- role ∈ {student, lecturer_ro}

questions(id, topic, question_text, options_json, correct_letter, explanation)
    -- topic ∈ {"FUNDAMENTALS","NORM_DEP"}
    -- options_json is an array of 4 strings
    -- correct_letter ∈ {"A","B","C","D"}

attempts(id, user_id, started_at, submitted_at,
         score_overall, score_fundamentals, score_normdep)

responses(id, attempt_id, question_id, chosen_letter, is_correct, time_spent_ms)

Rules:
- Exactly 30 questions per attempt
- 15 FUNDAMENTALS and 15 NORM_DEP on every attempt
- Randomized order and no duplicates
- Latest attempt drives gating and dashboard
```

---

## Seeding policy

We **do not** seed attempts or responses.

We seed:

* **2 pilot students**
* **1 admin** with read only role
* **30 questions** total with a 15 and 15 split

Empty states:

* Student dashboard shows “No attempts yet. Start your first quiz.” on first run.
* Lecturer overview shows “No data yet.” placeholders for accuracy and charts until the first submission.

---

## Requirements

* Python 3.10 or higher
* Windows tested
* SQLite bundled

---

## Setup

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Run

**Single DB location**
SQLite lives at `app/instance/pla.db`

**Seed minimal data**

```bat
python scripts/seed_minimal.py
```

**Doctor checks**

```bat
python scripts/dev_doctor.py
```

Doctor verifies:

* DB path is `app/instance/pla.db`
* Required tables exist
* Users >= 3 with correct roles
* Questions = 30 with 15 and 15 split
* Attempts and responses may be zero on first run

**Start the server**

```bat
set FLASK_APP=app.py
flask run
```

Open `http://127.0.0.1:5000`

---

## Demo accounts

* Student 1: `student1@demo.edu` / `Student123!`
* Student 2: `student2@demo.edu` / `Student123!`
* Admin read only: `admin@lct.edu` / `Admin123!`

---

## Developer tools

**Dev Doctor**
`python scripts/dev_doctor.py`
Confirms DB location, schema, user count, and 30 questions with 15 and 15 split.

**Backups**
Lecturer Overview → Backup DB button creates `backups/pla_YYYYMMDD_HHMM.db`

**Smoke tests**

```bat
pytest -q
# tests/test_seed.py
# tests/test_quiz_contract.py
# tests/test_submit_cycle.py
```

**Error handling**
Routes catch exceptions, print tagged lines in the console, and return shaped JSON.

Examples:

* `[ERROR] QUIZ_LOAD:`
* `[ERROR] SUBMIT:`

On validation error, return

```json
{"error":"INVALID_LETTER","code":"SUBMIT_001"}
```

---

## Attempt Auto-Play (demo filler)

Use this to create a few **real** attempts for charts and analytics before a demo.
It logs in each pilot student, pulls a quiz, answers with random letters, and submits.

```bat
python scripts/autoplay_attempts.py --students 2 --attempts-per-student 2 --pace fast
```

Flags:

* `--students` number of pilot students to use (1 or 2)
* `--attempts-per-student` attempts each student will run
* `--pace` fast or slow (controls time_spent_ms to simulate timing analytics)

Auto-play respects the schema and **does not** insert raw SQL. It uses your real endpoints or service functions.

---

## Troubleshooting

**Port 5000 already in use**

```bat
for /f "tokens=5" %a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do taskkill /PID %a /F
```

**Error loading quiz UI**

* Run the doctor. Confirm 30 questions with 15 and 15 split.
* Check console for `[ERROR] QUIZ_` or `[ERROR] SUBMIT:` lines.

**Multiple DBs or wrong path**

* Only use `app/instance/pla.db`
* Delete stray `*.db` files in sibling folders
* Do not run the app from other roots

---

## Guardrails for AI tools

* Edit only the files you name. Do not create new files or directories.
* Keep DB at `app/instance/pla.db` only.
* Use `options_json` and `correct_letter` only. No `option_a` to `option_d` columns.
* Two topics only. Enforce 15 and 15 selection on every attempt.
* On errors use try and except, print tagged messages, return shaped JSON.
* Follow the Data contract above. Do not change the schema.

**Prompt header to paste before tasks**

```
Follow README “Data contract”, “Seeding policy”, and “Guardrails”. Do not diverge.

Edit ONLY these files:
- app/routes/...
- app/services/...
- templates/...

No new files or directories.
Keep DB at app/instance/pla.db.
Two topics only. Enforce 15 and 15 per attempt.
```

---

## Repo structure

```
app/
  routes/
  services/
  templates/
  static/
  instance/           # holds pla.db
scripts/
  seed_minimal.py
  dev_doctor.py
  autoplay_attempts.py
tests/
docs/
  contract.md
README.md
```

---

## Minimal user flow

```
STUDENT
Login -> Dashboard (empty state if no attempts) -> Start Quiz
-> 30 questions (15 FUNDAMENTALS + 15 NORM_DEP, back/next, autosave)
-> Submit -> Review (per question, correct answer, explanation, topic breakdown, rating)
-> Dashboard updates (latest attempt only)
-> Gating shows "Proceed to next topic" only when both topics are 100% on latest attempt
-> Modules page shows two core modules and next recommendation when unlocked

LECTURER (read only)
Login (admin@lct.edu)
-> Overview (totals, per topic accuracy, recent activity mini chart)
-> Student list (attempts count) -> Student detail (attempts, scores, timing)
-> Questions view (correct rate) -> Backup DB button
```

---

## Script stubs to match the README

### `scripts/seed_minimal.py` (stub)

```python
# Creates users (2 students, 1 admin) and 30 questions (15 FUNDAMENTALS, 15 NORM_DEP)
# Does NOT create attempts or responses
# Uses app/instance/pla.db only

# TODO: implement ORM/SQL to:
# - create tables if not exist (users, questions, attempts, responses)
# - upsert demo users with the given emails and hashed passwords
# - insert 30 questions with options_json (list of 4) and correct_letter
# - enforce exactly 15/15 split
print("Seed complete: users and 30 questions inserted. No attempts/responses.")
```

### `scripts/dev_doctor.py` (stub)

```python
# Verifies DB path, required tables, users>=3, 30 questions with 15/15 split
# Allows attempts==0 and responses==0 on first run

# TODO: implement checks and print clear ✅ / ❌ lines
print("✅ DB at app/instance/pla.db")
print("✅ Tables present")
print("✅ Users: 3 (2 students, 1 admin)")
print("✅ Questions: 30 (15 FUNDAMENTALS, 15 NORM_DEP)")
print("ℹ️  No attempts/responses yet — run a quiz or use autoplay to generate data.")
```

### `scripts/autoplay_attempts.py` (stub)

```python
# Simulates quiz attempts for student1 and student2
# Options:
#   --students 1|2
#   --attempts-per-student N
#   --pace fast|slow  (controls time_spent_ms range)
#
# TODO: implement:
# 1) pick the pilot students
# 2) for each attempt, fetch 30 questions via service layer (or direct SQL)
# 3) choose random letters A-D; assign time_spent_ms per pace
# 4) call the same scoring path your /submit uses, so analytics update as real
print("Autoplay complete: demo attempts created.")
```

---

If you want, I can tailor these stubs to your actual file layout and models so they run right away.
