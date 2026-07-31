#!/usr/bin/env python
"""
Initialize the GreenField AgroWorks database.
Run this once to set up the SQLite database with schema and seed data.
"""

import sqlite3
import os

# Get the project root directory (two levels up from this file)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_DIR = os.path.join(PROJECT_ROOT, "DB")

# Database and schema paths - use absolute paths for cross-platform compatibility
DB_PATH = os.path.join(PROJECT_ROOT, "greenfield.db")
SCHEMA_PATH = os.path.join(DB_DIR, "schema.sql")
SEED_PATH = os.path.join(DB_DIR, "seed.sql")

def create_database():
    """Create and initialize the database."""
    
    # Read schema
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
    
    # Create database and execute schema
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema)
    conn.commit()
    print(f"✓ Schema loaded")
    
    # Read and execute seed data
    with open(SEED_PATH, 'r') as f:
        seed = f.read()
    
    conn.executescript(seed)
    conn.commit()
    print(f"✓ Seed data loaded")
    
    # Verify tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"✓ Tables created: {', '.join(t[0] for t in tables)}")
    
    conn.close()
    print(f"\n✓ Database '{DB_PATH}' created successfully!")

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        response = input(f"Database '{DB_PATH}' already exists. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            exit(0)
        os.remove(DB_PATH)
        print(f"Removed existing database")
    
    create_database()
