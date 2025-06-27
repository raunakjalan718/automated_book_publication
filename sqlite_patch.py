# sqlite_patch.py
import sqlite3
import sys

# Monkey patch sqlite3 to show the version
print(f"SQLite version: {sqlite3.sqlite_version}")

# Check if version meets minimum requirements
sqlite_version = tuple(map(int, sqlite3.sqlite_version.split('.')))
min_version = (3, 35, 0)

if sqlite_version < min_version:
    print(f"WARNING: Your SQLite version {sqlite3.sqlite_version} is below the recommended minimum {'.'.join(map(str, min_version))}")
    print("ChromaDB may not work properly with this version.")
    
    # Optional: Set environment variable to ignore version check
    import os
    os.environ["CHROMA_IGNORE_VERSION"] = "True"
