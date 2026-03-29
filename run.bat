@echo off
REM Windows launcher
cd /d "%~dp0"

IF EXIST "venv\Scripts\python.exe" (
    SET PYTHON=venv\Scripts\python.exe
) ELSE (
    SET PYTHON=python
)

echo Starting NeuroSense on http://127.0.0.1:5000
%PYTHON% app.py
pause
