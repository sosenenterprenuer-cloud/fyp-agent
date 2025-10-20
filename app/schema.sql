-- Canonical Schema for Personalized Learning Recommendation AI
-- This schema enforces the two-topic model with exactly 30 questions (15/15 split)

-- STUDENT
CREATE TABLE IF NOT EXISTS student (
  student_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  name           TEXT NOT NULL,
  email          TEXT NOT NULL UNIQUE,
  password_hash  TEXT NOT NULL,
  program        TEXT DEFAULT '',
  created_at     TEXT DEFAULT (datetime('now'))
);

-- LECTURER
CREATE TABLE IF NOT EXISTS lecturer (
  lecturer_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  name           TEXT NOT NULL,
  email          TEXT NOT NULL UNIQUE,
  password_hash  TEXT NOT NULL,
  created_at     TEXT DEFAULT (datetime('now'))
);

-- QUIZ (30 rows total, 15/15 split across the two categories)
CREATE TABLE IF NOT EXISTS quiz (
  quiz_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  two_category   TEXT NOT NULL CHECK (two_category IN (
                   'Data Modeling & DBMS Fundamentals',
                   'Normalization & Dependencies'
                 )),
  question       TEXT NOT NULL,
  options_json   TEXT NOT NULL,              -- JSON array of option strings
  correct_text   TEXT NOT NULL,              -- the correct option text (not letter)
  explanation    TEXT NOT NULL               -- short rationale shown in review
);

-- ATTEMPT
CREATE TABLE IF NOT EXISTS attempt (
  attempt_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id     INTEGER NOT NULL,
  started_at     TEXT NOT NULL,
  finished_at    TEXT,
  items_total    INTEGER DEFAULT 0,
  items_correct  INTEGER DEFAULT 0,
  score_pct      REAL DEFAULT 0,
  source         TEXT DEFAULT 'web',
  FOREIGN KEY(student_id) REFERENCES student(student_id) ON DELETE CASCADE
);

-- RESPONSE (stores letter + text + timing)
CREATE TABLE IF NOT EXISTS response (
  response_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  attempt_id        INTEGER NOT NULL,
  student_id        INTEGER NOT NULL,
  quiz_id           INTEGER NOT NULL,
  answer_letter     TEXT,                     -- 'A'/'B'/'C'/'D'
  answer_text       TEXT,                     -- the visible text picked
  is_correct        INTEGER NOT NULL CHECK (is_correct IN (0,1)),
  response_time_s   REAL DEFAULT 0,
  FOREIGN KEY(attempt_id) REFERENCES attempt(attempt_id) ON DELETE CASCADE,
  FOREIGN KEY(student_id) REFERENCES student(student_id) ON DELETE CASCADE,
  FOREIGN KEY(quiz_id) REFERENCES quiz(quiz_id) ON DELETE CASCADE
);

-- FEEDBACK
CREATE TABLE IF NOT EXISTS feedback (
  feedback_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id     INTEGER NOT NULL,
  attempt_id     INTEGER NOT NULL,
  rating         INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment        TEXT DEFAULT '',
  created_at     TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(student_id) REFERENCES student(student_id) ON DELETE CASCADE,
  FOREIGN KEY(attempt_id) REFERENCES attempt(attempt_id) ON DELETE CASCADE
);

-- Useful indexes
CREATE INDEX IF NOT EXISTS idx_attempt_student ON attempt(student_id, started_at);
CREATE INDEX IF NOT EXISTS idx_response_attempt ON response(attempt_id);
CREATE INDEX IF NOT EXISTS idx_response_quiz ON response(quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_category ON quiz(two_category);