#!/usr/bin/env bash
# Mac / Linux launcher
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

# Use venv if it exists, otherwise system python
if [ -f "$DIR/venv/bin/python" ]; then
    PYTHON="$DIR/venv/bin/python"
else
    PYTHON="python3"
fi

cd "$DIR"
echo "Starting NeuroSense on http://127.0.0.1:5000"
"$PYTHON" app.py
