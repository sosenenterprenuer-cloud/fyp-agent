#!/usr/bin/env python3
"""
Check for forbidden strings in tracked files.
Fails if nf_level appears anywhere in the codebase.
"""

import os
import sys
import subprocess
from pathlib import Path

# Configuration
APP_DIR = Path(__file__).resolve().parents[1]
FORBIDDEN_STRINGS = ['nf_level']

def get_tracked_files():
    """Get list of tracked files from git."""
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split('\n')
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[WARNING] Git not available, scanning all files...")
        return []

def scan_file_for_forbidden(file_path):
    """Scan a single file for forbidden strings."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        violations = []
        for forbidden in FORBIDDEN_STRINGS:
            if forbidden in content:
                # Find line numbers
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if forbidden in line:
                        violations.append({
                            'string': forbidden,
                            'file': file_path,
                            'line': i,
                            'content': line.strip()
                        })
        
        return violations
    except Exception as e:
        print(f"[WARNING] Could not scan {file_path}: {e}")
        return []

def scan_directory():
    """Scan all files in the directory for forbidden strings."""
    violations = []
    
    # Get tracked files or scan all files
    tracked_files = get_tracked_files()
    
    if tracked_files:
        files_to_scan = [f for f in tracked_files if f and os.path.exists(os.path.join(APP_DIR, f))]
    else:
        # Scan all files if not in git repo
        files_to_scan = []
        for root, dirs, files in os.walk(APP_DIR):
            # Skip common ignore directories
            dirs[:] = [d for d in dirs if d not in ['.venv', '__pycache__', 'node_modules', '.git']]
            for file in files:
                if file.endswith(('.py', '.sql', '.html', '.js', '.css', '.md', '.txt', '.csv')):
                    files_to_scan.append(os.path.join(root, file))
    
    print(f"Scanning {len(files_to_scan)} files for forbidden strings...")
    
    for file_path in files_to_scan:
        full_path = os.path.join(APP_DIR, file_path) if not os.path.isabs(file_path) else file_path
        if os.path.exists(full_path):
            file_violations = scan_file_for_forbidden(full_path)
            violations.extend(file_violations)
    
    return violations

def main():
    """Main function."""
    print("=== FORBIDDEN STRING CHECK ===")
    print(f"Checking for: {', '.join(FORBIDDEN_STRINGS)}")
    print(f"Directory: {APP_DIR}")
    print()
    
    violations = scan_directory()
    
    if not violations:
        print("[SUCCESS] No forbidden strings found!")
        sys.exit(0)
    else:
        print(f"[ERROR] Found {len(violations)} violations:")
        print()
        
        for violation in violations:
            print(f"  {violation['string']} in {violation['file']}:{violation['line']}")
            print(f"    {violation['content']}")
            print()
        
        print("Please remove or replace all occurrences of forbidden strings.")
        sys.exit(1)

if __name__ == "__main__":
    main()
