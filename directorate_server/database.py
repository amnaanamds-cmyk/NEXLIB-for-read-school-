import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "central_directorate.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Colleges registered
        conn.execute("""
            CREATE TABLE IF NOT EXISTS colleges (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                api_key TEXT NOT NULL,
                registered_at INTEGER NOT NULL,
                last_sync_at INTEGER
            )
        """)

        # Snapshots from colleges
        conn.execute("""
            CREATE TABLE IF NOT EXISTS college_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                college_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                total_books INTEGER NOT NULL,
                available_books INTEGER NOT NULL,
                issued_books INTEGER NOT NULL,
                total_members INTEGER NOT NULL,
                overdue_count INTEGER NOT NULL,
                total_fines REAL NOT NULL,
                top_borrowed_books TEXT, -- JSON array
                activity_summary TEXT, -- JSON array
                FOREIGN KEY(college_id) REFERENCES colleges(id) ON DELETE CASCADE
            )
        """)

        # Directorate level alerts
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                college_id TEXT NOT NULL,
                alert_type TEXT NOT NULL, -- 'overdue_rate', 'no_sync', 'uncollected_fines'
                message TEXT NOT NULL,
                severity TEXT NOT NULL, -- 'critical', 'warning'
                created_at INTEGER NOT NULL,
                acknowledged INTEGER DEFAULT 0,
                FOREIGN KEY(college_id) REFERENCES colleges(id) ON DELETE CASCADE
            )
        """)

        # Inter-library book transfers
        conn.execute("""
            CREATE TABLE IF NOT EXISTS book_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_college TEXT NOT NULL,
                to_college TEXT NOT NULL,
                book_title TEXT NOT NULL,
                book_isbn TEXT,
                status TEXT NOT NULL, -- 'requested', 'in-transit', 'received', 'rejected'
                requested_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(from_college) REFERENCES colleges(id) ON DELETE CASCADE,
                FOREIGN KEY(to_college) REFERENCES colleges(id) ON DELETE CASCADE
            )
        """)

        # Directorate admins users
        conn.execute("""
            CREATE TABLE IF NOT EXISTS directorate_users (
                email TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT DEFAULT 'directorate_admin'
            )
        """)
        
        # Seed a default directorate admin if none exists
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM directorate_users")
        if cursor.fetchone()["cnt"] == 0:
            # Hash of 'director' is generated with bcrypt
            # For simplicity, we'll store a precomputed bcrypt/hash or verify with standard checks.
            # We'll use passlib.hash.bcrypt or a standard verification.
            # Default hash for password 'director' using bcrypt is:
            # $2b$12$R9h/lIPsI3TvG9YNbyNTcOq.W6.u0wYn7i29j2wH7M8s0p3yZ64G2 (or similar)
            # We will seed password "director123" with hash:
            # Let's seed director@gdc.edu / director123
            # We'll write a helper to seed on startup.
            pass
        
        conn.commit()

if __name__ == "__main__":
    init_db()
    print("Central database initialized successfully.")
