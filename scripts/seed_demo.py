import os, csv, sqlite3, time, random, hashlib
from werkzeug.security import generate_password_hash

DB = os.environ.get("PLA_DB", "pla.db")
CSV = os.path.join("data","quiz_bank.csv")
os.makedirs("backups", exist_ok=True)
bkp = os.path.join("backups", f"pla_{time.strftime('%Y%m%d_%H%M%S')}.db")
if os.path.exists(DB):
    import shutil; shutil.copy(DB, bkp)

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
cur = con.cursor()
cur.execute("PRAGMA foreign_keys=ON")

# minimal schema (create if not exists)
cur.executescript("""
CREATE TABLE IF NOT EXISTS student(
  student_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
  program TEXT, password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lecturer(
  lecturer_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quiz(
  quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
  question TEXT NOT NULL,
  two_category TEXT NOT NULL,
  option_a TEXT NOT NULL, option_b TEXT NOT NULL, option_c TEXT NOT NULL, option_d TEXT NOT NULL,
  correct_text TEXT NOT NULL,
  explanation TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS attempt(
  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  items_total INTEGER DEFAULT 0,
  items_correct INTEGER DEFAULT 0,
  score_pct REAL DEFAULT 0,
  source TEXT DEFAULT 'web',
  FOREIGN KEY(student_id) REFERENCES student(student_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS response(
  response_id INTEGER PRIMARY KEY AUTOINCREMENT,
  attempt_id INTEGER NOT NULL,
  student_id INTEGER NOT NULL,
  quiz_id INTEGER NOT NULL,
  answer_text TEXT NOT NULL,
  score INTEGER NOT NULL CHECK(score IN (0,1)),
  response_time_s REAL DEFAULT 0,
  FOREIGN KEY(attempt_id) REFERENCES attempt(attempt_id) ON DELETE CASCADE,
  FOREIGN KEY(student_id) REFERENCES student(student_id) ON DELETE CASCADE,
  FOREIGN KEY(quiz_id) REFERENCES quiz(quiz_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_resp_attempt ON response(attempt_id);
CREATE INDEX IF NOT EXISTS idx_attempt_student ON attempt(student_id, started_at);
""")

# load quiz from CSV (clear old quiz first)
cur.execute("DELETE FROM quiz")
with open(CSV,"r",encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
    for r in rows:
        cur.execute("""
        INSERT INTO quiz(question,two_category,option_a,option_b,option_c,option_d,correct_text,explanation)
        VALUES(?,?,?,?,?,?,?,?)
        """, (r["question"].strip(), r["two_category"].strip(),
              r["option_a"].strip(), r["option_b"].strip(), r["option_c"].strip(), r["option_d"].strip(),
              r["correct_text"].strip(), r["explanation"].strip()))

# lecturer
cur.execute("INSERT OR IGNORE INTO lecturer(name,email,password_hash) VALUES(?,?,?)",
            ("Admin", "admin@lct.edu", generate_password_hash("Admin!234")))

names = [
"MOHAMED AIMAN","MUHAMMAD FARHAN ADDREEN BIN SARRAFIAN","NG EN JI",
"MUHAMMAD MUZAMMIL BIN SALIM","NATALIE CHANG PUI SHAN","LAVANESS A/L SRITHAR",
"NUR LIYANA BINTI RAMLI","TEE KA HONG","MUHAMMAD AFIQ SHADIQI BIN ZAWAWI",
"SUKANTHAN A/L SURESH","SRITHARAN A/L RAGU","NUR BATRISYIA BINTI ZOOL HILMI",
"ANIS AKMA SOFEA BINTI AZMAN","JEMMY O'VEINNEDDICT BULOT","AMANDA FLORA JENOS",
"SITI FARAH ERLIYANA BINTI MOHD HAIRUL NIZAM","SHARON YEO"
]
def slug_email(n):
    base = "".join(ch.lower() if ch.isalnum() else "." for ch in n)
    base = ".".join([p for p in base.split(".") if p])
    return f"{base}@demo.edu"

# seed students
for nm in names:
    email = slug_email(nm)
    cur.execute("INSERT OR IGNORE INTO student(name,email,password_hash,program) VALUES(?,?,?,?)",
                (nm, email, generate_password_hash("Passw0rd!"), "BIT"))

# create exactly 1 finished attempt per student with realistic spread
import time as _t, random as _r
cur.execute("SELECT quiz_id, two_category, correct_text, option_a, option_b, option_c, option_d FROM quiz")
quiz = cur.fetchall()

cur.execute("SELECT student_id FROM student")
students = [r["student_id"] for r in cur.fetchall()]

for sid in students:
    cur.execute("INSERT INTO attempt(student_id, started_at, finished_at, source) VALUES(?, datetime('now','-1 day'), datetime('now','-1 day','+5 minutes'), 'seed')", (sid,))
    aid = cur.lastrowid
    correct_count = 0
    for q in quiz:
        # vary difficulty: some wrong, some right (ensure at least one perfect across cohort)
        opts = [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
        # 65% correct on average, shifted by student id to create variety
        p = 0.55 + 0.02 * (sid % 5)
        choose_correct = (_r.random() < p)
        ans = q["correct_text"] if choose_correct else _r.choice([o for o in opts if o != q["correct_text"]])
        score = 1 if ans == q["correct_text"] else 0
        if score: correct_count += 1
        rt = round(8 + _r.random()*18, 2)  # 8–26s
        cur.execute("""INSERT INTO response(attempt_id,student_id,quiz_id,answer_text,score,response_time_s)
                       VALUES(?,?,?,?,?,?)""", (aid, sid, q["quiz_id"], ans, score, rt))
    pct = round(correct_count/30*100, 1)
    cur.execute("UPDATE attempt SET items_total=?, items_correct=?, score_pct=? WHERE attempt_id=?",
                (30, correct_count, pct, aid))

# ensure at least one perfect student
cur.execute("SELECT student_id FROM student ORDER BY student_id LIMIT 1")
perfect_sid = cur.fetchone()["student_id"]
# overwrite their attempt to be 30/30
cur.execute("SELECT attempt_id FROM attempt WHERE student_id=? ORDER BY attempt_id DESC LIMIT 1", (perfect_sid,))
aid = cur.fetchone()["attempt_id"]
cur.execute("DELETE FROM response WHERE attempt_id=?", (aid,))
for q in quiz:
    cur.execute("""INSERT INTO response(attempt_id,student_id,quiz_id,answer_text,score,response_time_s)
                   VALUES(?,?,?,?,?,?)""", (aid, perfect_sid, q["quiz_id"], q["correct_text"], 1, 12.0))
cur.execute("UPDATE attempt SET items_total=30, items_correct=30, score_pct=100.0 WHERE attempt_id=?", (aid,))

con.commit(); con.close()
print("[OK] Seeded demo data with 17 students and 30-question attempts.")
