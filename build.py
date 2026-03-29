"""
Run this once to set up the project environment.

Usage:
    python build.py
"""

import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BASE_DIR, "venv")


def run(cmd):
    print(f"> {' '.join(cmd)}")
    subprocess.check_call(cmd)


def get_pip_path():
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "pip.exe")
    return os.path.join(VENV_DIR, "bin", "pip")


def main():
    # Step 1: Create virtual environment
    if not os.path.exists(VENV_DIR):
        print("[1/3] Creating virtual environment...")
        run([sys.executable, "-m", "venv", VENV_DIR])
    else:
        print("[1/3] Virtual environment already exists.")

    pip = get_pip_path()

    # Step 2: Install dependencies
    print("[2/3] Installing dependencies...")
    run([pip, "install", "--upgrade", "pip"])

    run([
        pip, "install",
        "Flask>=2.3,<4.0",
        "pymongo>=4.0",
        "bcrypt>=4.0",
        "flask-cors>=4.0",
        "flask-session>=0.5",
        "certifi",
        "python-dotenv",
        "numpy",
        "Pillow"
    ])

    # Step 3: Install PyTorch CPU
    print("[3/3] Installing PyTorch (CPU)...")
    run([
        pip, "install", "torch", "torchvision",
        "--index-url", "https://download.pytorch.org/whl/cpu"
    ])

    print("\n✅ Build complete!")
    print("Run the app using: python run.py")


if __name__ == "__main__":
    main()