"""
One-time setup: creates a virtual environment and installs all dependencies.
Run once before starting the app:

    python setup.py

Then start the app:
    Mac/Linux:  ./run.sh
    Windows:    run.bat
"""
import subprocess
import sys
import os

VENV = os.path.join(os.path.dirname(__file__), 'venv')

def run(cmd, **kw):
    print(f'  > {" ".join(cmd)}')
    subprocess.check_call(cmd, **kw)

def main():
    # 1. Create venv if missing
    if not os.path.isdir(VENV):
        print('[1/3] Creating virtual environment...')
        run([sys.executable, '-m', 'venv', VENV])
    else:
        print('[1/3] Virtual environment already exists.')

    # 2. Resolve pip path
    pip = os.path.join(VENV, 'Scripts', 'pip.exe') if os.name == 'nt' \
        else os.path.join(VENV, 'bin', 'pip')

    # 3. Install core deps first
    print('[2/3] Installing core dependencies...')
    run([pip, 'install', '--upgrade', 'pip'])
    run([pip, 'install',
         'Flask>=2.3,<4.0', 'pymongo>=4.0', 'bcrypt>=4.0',
         'flask-cors>=4.0', 'flask-session>=0.5',
         'certifi', 'python-dotenv', 'numpy', 'Pillow'])

    # 4. Install torch CPU-only (much smaller, works everywhere)
    print('[3/3] Installing PyTorch (CPU)...')
    run([pip, 'install', 'torch', 'torchvision',
         '--index-url', 'https://download.pytorch.org/whl/cpu'])

    print('\n✓ Setup complete!')
    if os.name == 'nt':
        print('  Start the app:  run.bat')
    else:
        print('  Start the app:  ./run.sh')

if __name__ == '__main__':
    main()
