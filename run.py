"""
Run the application.

Usage:
    python run.py
"""

import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_python_path():
    if os.name == "nt":
        return os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
    return os.path.join(BASE_DIR, "venv", "bin", "python")


def main():
    python_exec = get_python_path()

    if not os.path.exists(python_exec):
        print("❌ Virtual environment not found.")
        print("👉 Run: python build.py first")
        sys.exit(1)

    print("🚀 Starting app on http://127.0.0.1:5000")
    subprocess.call([python_exec, "app.py"])


if __name__ == "__main__":
    main()