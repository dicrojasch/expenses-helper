import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "expenses.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table category_mapping
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS category_mapping (
        description TEXT PRIMARY KEY,
        category TEXT NOT NULL
    )
    """)
    
    # Table transactions_staging
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions_staging (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()
