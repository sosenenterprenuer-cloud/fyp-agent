import importlib, os, sys, subprocess
print("[SMOKE] Python compile OK.")
# bank validator
rc = subprocess.call([sys.executable, "scripts/enforce_quiz_bank_30.py"])
if rc != 0:
    sys.exit(rc)
print("[SMOKE] Bank validator passed.")

