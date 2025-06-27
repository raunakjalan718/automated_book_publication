@echo off
echo Running SQLite patch...
python sqlite_patch.py

echo Starting application on port 9000...
set PYTHONPATH=%CD%
python -m uvicorn main:app --host 0.0.0.0 --port 9000 --log-level debug
