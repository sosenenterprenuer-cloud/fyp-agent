import csv, json, sys, os
CSV = os.path.join("data", "quiz_bank.csv")
errs = []

if not os.path.exists(CSV):
    print("[ERROR] data/quiz_bank.csv not found."); sys.exit(2)

rows = []
with open(CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

if len(rows) != 30:
    errs.append(f"Expected 30 questions, found {len(rows)}")

allowed = {"Data Modeling & DBMS Fundamentals", "Normalization & Dependencies"}

for i, r in enumerate(rows, start=1):
    q = r.get("question","").strip()
    cat = r.get("two_category","").strip()
    opts = [r.get("option_a","").strip(), r.get("option_b","").strip(),
            r.get("option_c","").strip(), r.get("option_d","").strip()]
    correct = r.get("correct_text","").strip()
    expl = r.get("explanation","").strip()
    if not q: errs.append(f"Q{i}: question empty")
    if cat not in allowed: errs.append(f"Q{i}: invalid two_category '{cat}'")
    if any(not o for o in opts): errs.append(f"Q{i}: all 4 options must be filled")
    if correct not in opts: errs.append(f"Q{i}: correct_text not in options")
    if not expl: errs.append(f"Q{i}: explanation required")
if errs:
    print("[ERROR] Quiz bank invalid:")
    for e in errs: print(" -", e)
    sys.exit(3)
print("[OK] Quiz bank valid (30 rows, 4 options each, categories ok, correct in options, explanation present).")

