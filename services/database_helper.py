"""
services/database_helper.py — SQLite Local Database Service.
Fully offline storage for Books, Members, Issue Records, Reservations,
staff accounts, and the school profile.
"""
import sqlite3
import threading
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import config
from models import Book, Member, IssueRecord, Reservation
import contextlib

@contextlib.contextmanager
def db_transaction(db_helper):
    """Context manager for running queries within a transaction block."""
    conn = db_helper._get_conn()
    try:
        conn.execute("BEGIN TRANSACTION")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class DatabaseHelper:
    def __init__(self):
        db_path = Path(config.LOCAL_DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path)
        # Serializes "assign the next local id" so two background save
        # workers can never read the same MAX(id) before either commits.
        self._id_lock = threading.Lock()
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            # ── Books Table ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    syncId TEXT PRIMARY KEY,
                    id INTEGER,
                    isbn TEXT,
                    accNo TEXT,
                    title TEXT NOT NULL,
                    author TEXT,
                    publisher TEXT,
                    publisherPlace TEXT,
                    publishDate TEXT,
                    edition TEXT,
                    pages INTEGER,
                    procurement TEXT,
                    volume TEXT,
                    price REAL,
                    status TEXT,
                    isDigital INTEGER,
                    digitalUrl TEXT,
                    category TEXT,
                    lastUpdated INTEGER,
                    deleted INTEGER DEFAULT 0
                )
            """)

            # ── Members Table ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    syncId TEXT PRIMARY KEY,
                    id INTEGER,
                    memberId TEXT,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    department TEXT,
                    memberType TEXT,
                    joinDate TEXT,
                    expiryDate TEXT,
                    booksIssued INTEGER DEFAULT 0,
                    fatherName TEXT,
                    className TEXT,
                    classNo TEXT,
                    address TEXT,
                    photoUri TEXT,
                    designation TEXT,
                    bps TEXT,
                    pin TEXT,
                    lastUpdated INTEGER,
                    deleted INTEGER DEFAULT 0
                )
            """)

            # Simple Migration: Ensure columns exist
            migrations = [
                ("pin", "members", "TEXT"),
                ("lastUpdated", "members", "INTEGER"),
                ("deleted", "members", "INTEGER DEFAULT 0"),
                ("lastUpdated", "books", "INTEGER"),
                ("deleted", "books", "INTEGER DEFAULT 0"),
                ("lastUpdated", "issued_books", "INTEGER"),
                ("deleted", "issued_books", "INTEGER DEFAULT 0"),
                ("lastUpdated", "reservations", "INTEGER"),
                ("deleted", "reservations", "INTEGER DEFAULT 0"),
            ]
            for col, tbl, dtype in migrations:
                try:
                    conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {dtype}")
                except: pass # Column already exists

            # ── Issue Records Table ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS issued_books (
                    syncId TEXT PRIMARY KEY,
                    id INTEGER,
                    bookId INTEGER,
                    bookTitle TEXT,
                    bookIsbn TEXT,
                    memberId INTEGER,
                    memberName TEXT,
                    memberMemberId TEXT,
                    issueDate TEXT,
                    dueDate TEXT,
                    returnDate TEXT,
                    fine REAL DEFAULT 0.0,
                    status TEXT,
                    lastUpdated INTEGER,
                    deleted INTEGER DEFAULT 0
                )
            """)

            # ── Reservations Table ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reservations (
                    syncId TEXT PRIMARY KEY,
                    id INTEGER,
                    bookId INTEGER,
                    bookTitle TEXT,
                    memberId INTEGER,
                    memberName TEXT,
                    reservedDate TEXT,
                    status TEXT,
                    notifiedDate TEXT,
                    lastUpdated INTEGER,
                    deleted INTEGER DEFAULT 0
                )
            """)

            # ── Audit Log Table ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    userEmail TEXT,
                    action TEXT,
                    detail TEXT,
                    timestamp INTEGER,
                    timestampStr TEXT
                )
            """)

            # ── Book Reviews & Ratings ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS book_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bookSyncId TEXT,
                    memberSyncId TEXT,
                    memberName TEXT,
                    rating INTEGER, -- 1 to 5
                    comment TEXT,
                    timestamp INTEGER
                )
            """)

            # ── School Profile (single-school key/value settings) ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS school_profile (
                    key TEXT PRIMARY KEY,
                    val TEXT
                )
            """)

            # ── Staff Accounts (local authentication) ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    name TEXT,
                    role TEXT NOT NULL DEFAULT 'librarian',
                    created_at INTEGER
                )
            """)

            # ── Backup History ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backup_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_path TEXT NOT NULL,
                    backup_type TEXT,  -- 'auto', 'manual', 'migration'
                    file_size INTEGER,
                    created_at INTEGER NOT NULL,
                    created_at_str TEXT
                )
            """)

            # ── New Feature Tables ──
            # 1. Inventory Audits
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inventory_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audit_date INTEGER,
                    total_scanned INTEGER,
                    missing_books INTEGER,
                    misplaced_books INTEGER
                )
            """)

            # 2. Fine Payments
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fine_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memberId INTEGER,
                    amount REAL,
                    method TEXT,
                    reference_id TEXT,
                    timestamp INTEGER
                )
            """)
            
            # 3. Serials & Periodicals
            conn.execute("""
                CREATE TABLE IF NOT EXISTS serials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    issn TEXT,
                    frequency TEXT,
                    publisher TEXT,
                    status TEXT,
                    lastUpdated INTEGER
                )
            """)

            # 4. Inter-Library Loan (ILL)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ill_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bookTitle TEXT,
                    author TEXT,
                    memberId INTEGER,
                    requestDate INTEGER,
                    targetInstitution TEXT,
                    status TEXT
                )
            """)

            # 5. Acquisitions / PO
            conn.execute("""
                CREATE TABLE IF NOT EXISTS purchase_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendorName TEXT,
                    orderDate INTEGER,
                    totalAmount REAL,
                    status TEXT
                )
            """)

            # ── Indices for Performance ──
            conn.execute("CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_books_status ON books(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_issued_member ON issued_books(memberId)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_issued_status ON issued_books(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_members_memberId ON members(memberId)")

            self._repair_missing_ids(conn, "books")
            self._repair_missing_ids(conn, "members")
            self._repair_missing_ids(conn, "issued_books")
            self._repair_missing_ids(conn, "reservations")

            conn.commit()

    def _repair_missing_ids(self, conn, table: str):
        """One-time repair: assign real unique ids to any rows saved with id=0
        (a bug in earlier versions where every new book/member got id=0)."""
        rows = conn.execute(f"SELECT rowid FROM {table} WHERE id IS NULL OR id = 0").fetchall()
        if not rows:
            return
        next_id = conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}").fetchone()[0] + 1
        for r in rows:
            conn.execute(f"UPDATE {table} SET id = ? WHERE rowid = ?", (next_id, r["rowid"]))
            next_id += 1

    # ── Local Books Operations ───────────────────────────────────────────────
    def get_books(self, include_deleted=False) -> List[Book]:
        query = "SELECT * FROM books" if include_deleted else "SELECT * FROM books WHERE deleted = 0"
        with self._get_conn() as conn:
            rows = conn.execute(query).fetchall()
            return [Book.from_dict(dict(r)) for r in rows]

    def get_books_paginated(self, limit: int = 50, offset: int = 0, include_deleted=False) -> List[Book]:
        query = "SELECT * FROM books" if include_deleted else "SELECT * FROM books WHERE deleted = 0"
        query += " LIMIT ? OFFSET ?"
        with self._get_conn() as conn:
            rows = conn.execute(query, (limit, offset)).fetchall()
            return [Book.from_dict(dict(r)) for r in rows]

    def search_books_paginated(self, search_text: str, category: str, status: str, new_arrivals: bool, limit: int = 50, offset: int = 0) -> tuple[List[Book], int]:
        base_query = " FROM books WHERE deleted = 0"
        params = []
        
        if search_text:
            base_query += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ? OR accNo LIKE ?)"
            lk = f"%{search_text}%"
            params.extend([lk, lk, lk, lk])
            
        if category and category != "All Categories":
            base_query += " AND category = ?"
            params.append(category)
            
        if status and status != "All Status":
            base_query += " AND status = ?"
            params.append(status)
            
        if new_arrivals:
            cutoff = (time.time() - (30 * 24 * 3600)) * 1000  # 30 days ago approx
            base_query += " AND publishDate IS NOT NULL"
            
        with self._get_conn() as conn:
            count_row = conn.execute("SELECT COUNT(*)" + base_query, params).fetchone()
            total_count = count_row[0] if count_row else 0
            
            query = "SELECT *" + base_query + " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = conn.execute(query, params).fetchall()
            return [Book.from_dict(dict(r)) for r in rows], total_count

    def save_book(self, book: Book):
        """Save (insert or update) a book locally. Assigns a unique local id on first save."""
        with self._id_lock, self._get_conn() as conn:
            if not book.id:
                book.id = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM books").fetchone()[0]
            conn.execute("""
                INSERT INTO books (
                    syncId, id, isbn, accNo, title, author, publisher, publisherPlace,
                    publishDate, edition, pages, procurement, volume, price, status,
                    isDigital, digitalUrl, category, lastUpdated, deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(syncId) DO UPDATE SET
                    isbn=excluded.isbn, accNo=excluded.accNo, title=excluded.title,
                    author=excluded.author, publisher=excluded.publisher,
                    publisherPlace=excluded.publisherPlace, publishDate=excluded.publishDate,
                    edition=excluded.edition, pages=excluded.pages, procurement=excluded.procurement,
                    volume=excluded.volume, price=excluded.price, status=excluded.status,
                    isDigital=excluded.isDigital, digitalUrl=excluded.digitalUrl,
                    category=excluded.category, lastUpdated=excluded.lastUpdated,
                    deleted=excluded.deleted
            """, (
                book.syncId, book.id, book.isbn, book.accNo, book.title, book.author,
                book.publisher, book.publisherPlace, book.publishDate, book.edition,
                book.pages, book.procurement, book.volume, book.price, book.status,
                1 if book.isDigital else 0, book.digitalUrl, book.category,
                book.lastUpdated, 1 if book.deleted else 0
            ))
            conn.commit()

    # ── Local Members Operations ─────────────────────────────────────────────
    def get_members(self, include_deleted=False) -> List[Member]:
        query = "SELECT * FROM members" if include_deleted else "SELECT * FROM members WHERE deleted = 0"
        with self._get_conn() as conn:
            rows = conn.execute(query).fetchall()
            return [Member.from_dict(dict(r)) for r in rows]

    def get_members_paginated(self, limit: int = 50, offset: int = 0, include_deleted=False) -> List[Member]:
        query = "SELECT * FROM members" if include_deleted else "SELECT * FROM members WHERE deleted = 0"
        query += " LIMIT ? OFFSET ?"
        with self._get_conn() as conn:
            rows = conn.execute(query, (limit, offset)).fetchall()
            return [Member.from_dict(dict(r)) for r in rows]

    def save_member(self, member: Member):
        """Save (insert or update) a member locally. Assigns a unique local id on first save."""
        with self._id_lock, self._get_conn() as conn:
            if not member.id:
                member.id = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM members").fetchone()[0]
            conn.execute("""
                INSERT INTO members (
                    syncId, id, memberId, name, email, phone, department, memberType,
                    joinDate, expiryDate, booksIssued, fatherName, className, classNo,
                    address, photoUri, designation, bps, pin, lastUpdated, deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(syncId) DO UPDATE SET
                    memberId=excluded.memberId, name=excluded.name, email=excluded.email,
                    phone=excluded.phone, department=excluded.department, memberType=excluded.memberType,
                    joinDate=excluded.joinDate, expiryDate=excluded.expiryDate,
                    booksIssued=excluded.booksIssued, fatherName=excluded.fatherName,
                    className=excluded.className, classNo=excluded.classNo, address=excluded.address,
                    photoUri=excluded.photoUri, designation=excluded.designation,
                    bps=excluded.bps, pin=excluded.pin, lastUpdated=excluded.lastUpdated,
                    deleted=excluded.deleted
            """, (
                member.syncId, member.id, member.memberId, member.name, member.email,
                member.phone, member.department, member.memberType, member.joinDate,
                member.expiryDate, member.booksIssued, member.fatherName, member.className,
                member.classNo, member.address, member.photoUri, member.designation,
                member.bps, member.pin, member.lastUpdated, 1 if member.deleted else 0
            ))
            conn.commit()

    # ── Local Issue Records Operations ───────────────────────────────────────
    def get_issues(self, include_deleted=False) -> List[IssueRecord]:
        query = "SELECT * FROM issued_books" if include_deleted else "SELECT * FROM issued_books WHERE deleted = 0"
        with self._get_conn() as conn:
            rows = conn.execute(query).fetchall()
            return [IssueRecord.from_dict(dict(r)) for r in rows]

    def save_issue(self, record: IssueRecord):
        with self._id_lock, self._get_conn() as conn:
            if not record.id:
                record.id = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM issued_books").fetchone()[0]
            conn.execute("""
                INSERT INTO issued_books (
                    syncId, id, bookId, bookTitle, bookIsbn, memberId, memberName,
                    memberMemberId, issueDate, dueDate, returnDate, fine, status, lastUpdated, deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(syncId) DO UPDATE SET
                    bookId=excluded.bookId, bookTitle=excluded.bookTitle, bookIsbn=excluded.bookIsbn,
                    memberId=excluded.memberId, memberName=excluded.memberName,
                    memberMemberId=excluded.memberMemberId, issueDate=excluded.issueDate,
                    dueDate=excluded.dueDate, returnDate=excluded.returnDate, fine=excluded.fine,
                    status=excluded.status, lastUpdated=excluded.lastUpdated, deleted=excluded.deleted
            """, (
                record.syncId, record.id, record.bookId, record.bookTitle, record.bookIsbn,
                record.memberId, record.memberName, record.memberMemberId, record.issueDate,
                record.dueDate, record.returnDate, record.fine, record.status, record.lastUpdated,
                1 if record.deleted else 0
            ))
            conn.commit()

    # ── Local Reservations Operations ────────────────────────────────────────
    def get_reservations(self, include_deleted=False) -> List[Reservation]:
        query = "SELECT * FROM reservations" if include_deleted else "SELECT * FROM reservations WHERE deleted = 0"
        with self._get_conn() as conn:
            rows = conn.execute(query).fetchall()
            return [Reservation.from_dict(dict(r)) for r in rows]

    def save_reservation(self, res: Reservation):
        with self._id_lock, self._get_conn() as conn:
            if not res.id:
                res.id = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM reservations").fetchone()[0]
            conn.execute("""
                INSERT INTO reservations (
                    syncId, id, bookId, bookTitle, memberId, memberName, reservedDate,
                    status, notifiedDate, lastUpdated, deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(syncId) DO UPDATE SET
                    bookId=excluded.bookId, bookTitle=excluded.bookTitle, memberId=excluded.memberId,
                    memberName=excluded.memberName, reservedDate=excluded.reservedDate,
                    status=excluded.status, notifiedDate=excluded.notifiedDate,
                    lastUpdated=excluded.lastUpdated, deleted=excluded.deleted
            """, (
                res.syncId, res.id, res.bookId, res.bookTitle, res.memberId, res.memberName,
                res.reservedDate, res.status, res.notifiedDate, res.lastUpdated, 1 if res.deleted else 0
            ))
            conn.commit()

    # ── Audit Log ─────────────────────────────────────────────────────────────
    def log_audit_local(self, user_email: str, action: str, detail: str):
        now = int(time.time() * 1000)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO audit_log (userEmail, action, detail, timestamp, timestampStr)
                VALUES (?, ?, ?, ?, ?)
            """, (user_email, action, detail, now, now_str))
            conn.commit()

    def get_audit_logs_local(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    # ── Book Reviews & Ratings ──
    def save_review(self, book_sync_id: str, member_sync_id: str, member_name: str, rating: int, comment: str):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO book_reviews (bookSyncId, memberSyncId, memberName, rating, comment, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (book_sync_id, member_sync_id, member_name, rating, comment, int(time.time() * 1000)))
            conn.commit()

    def get_book_reviews(self, book_sync_id: str) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM book_reviews WHERE bookSyncId = ? ORDER BY timestamp DESC", (book_sync_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_average_rating(self, book_sync_id: str) -> float:
        with self._get_conn() as conn:
            row = conn.execute("SELECT AVG(rating) as avg_rating FROM book_reviews WHERE bookSyncId = ?", (book_sync_id,)).fetchone()
            return row["avg_rating"] if row and row["avg_rating"] else 0.0

    # ── School Profile ───────────────────────────────────────────────────────
    def get_school_profile(self) -> Dict[str, str]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM school_profile").fetchall()
            return {r['key']: r['val'] for r in rows}

    def set_school_profile(self, key: str, val: str):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO school_profile (key, val) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET val = excluded.val
            """, (key, val))
            conn.commit()

    def get_school_name(self) -> str:
        return self.get_school_profile().get("name") or "School Library"

    def get_fine_rate(self) -> float:
        val = self.get_school_profile().get("fine_rate_per_day")
        return float(val) if val else config.DEFAULT_FINE_RATE

    def set_fine_rate(self, rate: float):
        self.set_school_profile("fine_rate_per_day", str(rate))

    # ── Staff Accounts (local authentication) ───────────────────────────────
    def create_user(self, username: str, password_hash: str, salt: str, name: str, role: str):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO users (username, password_hash, salt, name, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, password_hash, salt, name, role, int(time.time() * 1000)))
            conn.commit()

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def count_users(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def list_users(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT id, username, name, role, created_at FROM users ORDER BY username").fetchall()
            return [dict(r) for r in rows]

    def update_user_password(self, user_id: int, password_hash: str, salt: str):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                        (password_hash, salt, user_id))
            conn.commit()

    def update_user_role(self, user_id: int, role: str):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
            conn.commit()

    def delete_user(self, user_id: int):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    # ── Backup History ─────────────────────────────────────────────────────────
    def log_backup(self, backup_path: str, backup_type: str, file_size: int):
        now = int(time.time() * 1000)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO backup_history (backup_path, backup_type, file_size, created_at, created_at_str)
                VALUES (?, ?, ?, ?, ?)
            """, (backup_path, backup_type, file_size, now, now_str))
            conn.commit()

    def get_backup_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM backup_history ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Fine Payments ──────────────────────────────────────────────────────────
    def save_fine_payment(self, memberId: int, amount: float, method: str, reference_id: str):
        now = int(time.time() * 1000)
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO fine_payments (memberId, amount, method, reference_id, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (memberId, amount, method, reference_id, now))
            conn.commit()

    def get_fine_payments(self, memberId: int = None) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            if memberId:
                rows = conn.execute("SELECT * FROM fine_payments WHERE memberId = ? ORDER BY timestamp DESC", (memberId,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM fine_payments ORDER BY timestamp DESC").fetchall()
            return [dict(r) for r in rows]

    # ── Inventory Audits ───────────────────────────────────────────────────────
    def save_inventory_audit(self, total_scanned: int, missing_books: int, misplaced_books: int):
        now = int(time.time() * 1000)
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO inventory_audits (audit_date, total_scanned, missing_books, misplaced_books)
                VALUES (?, ?, ?, ?)
            """, (now, total_scanned, missing_books, misplaced_books))
            conn.commit()

    def get_inventory_audits(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM inventory_audits ORDER BY audit_date DESC").fetchall()
            return [dict(r) for r in rows]

    # ── Serials & Periodicals ──────────────────────────────────────────────────
    def save_serial(self, title: str, issn: str, frequency: str, publisher: str, status: str):
        now = int(time.time() * 1000)
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO serials (title, issn, frequency, publisher, status, lastUpdated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, issn, frequency, publisher, status, now))
            conn.commit()

    def get_serials(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM serials ORDER BY title ASC").fetchall()
            return [dict(r) for r in rows]

    # ── Inter-Library Loan (ILL) Requests ──────────────────────────────────────
    def save_ill_request(self, book_title: str, author: str, member_id: int,
                         target_institution: str, status: str = "Requested"):
        now = int(time.time() * 1000)
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO ill_requests (bookTitle, author, memberId, requestDate, targetInstitution, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (book_title, author, member_id, now, target_institution, status))
            conn.commit()

    def get_ill_requests(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM ill_requests ORDER BY requestDate DESC").fetchall()
            return [dict(r) for r in rows]

    def update_ill_status(self, ill_id: int, new_status: str):
        now = int(time.time() * 1000)
        with self._get_conn() as conn:
            conn.execute("UPDATE ill_requests SET status = ? WHERE id = ?", (new_status, ill_id))
            conn.commit()

    # ── Purchase Orders (Acquisitions) ─────────────────────────────────────────
    def save_purchase_order(self, vendor_name: str, book_title: str, qty: int,
                            unit_price: float, status: str = "Pending"):
        now = int(time.time() * 1000)
        total = qty * unit_price
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO purchase_orders (vendorName, orderDate, totalAmount, status)
                VALUES (?, ?, ?, ?)
            """, (vendor_name, now, total, status))
            # Store line-item detail in the totalAmount field (for simplicity)
            # We reuse the existing schema — vendor, date, total, status
            conn.commit()

    def get_purchase_orders(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM purchase_orders ORDER BY orderDate DESC").fetchall()
            return [dict(r) for r in rows]

    def update_purchase_order_status(self, po_id: int, new_status: str):
        with self._get_conn() as conn:
            conn.execute("UPDATE purchase_orders SET status = ? WHERE id = ?", (new_status, po_id))
            conn.commit()

    # ── Data Integrity Health Check ────────────────────────────────────────────
    def run_health_check(self) -> Dict[str, Any]:
        """Run a comprehensive data integrity health check across all tables."""
        results = {
            "total_books": 0,
            "total_members": 0,
            "total_issues": 0,
            "orphan_issues": [],       # issues referencing deleted/missing books or members
            "duplicate_isbns": [],     # books sharing the same ISBN
            "duplicate_member_ids": [],# members sharing the same memberId
            "missing_titles": [],      # books with empty title
            "missing_names": [],       # members with empty name
            "ghost_issued": [],        # books marked "Issued" but no active issue record
            "stuck_returns": [],       # issues marked "Returned" but book still "Issued"
            "expired_members_with_books": [],  # expired members who still have books out
        }

        with self._get_conn() as conn:
            # Counts
            results["total_books"] = conn.execute(
                "SELECT COUNT(*) FROM books WHERE deleted = 0").fetchone()[0]
            results["total_members"] = conn.execute(
                "SELECT COUNT(*) FROM members WHERE deleted = 0").fetchone()[0]
            results["total_issues"] = conn.execute(
                "SELECT COUNT(*) FROM issued_books WHERE deleted = 0").fetchone()[0]

            # Orphan issues (book or member no longer exists)
            orphans = conn.execute("""
                SELECT ib.syncId, ib.bookTitle, ib.memberName
                FROM issued_books ib
                WHERE ib.deleted = 0
                  AND ib.status = 'Issued'
                  AND (
                    ib.bookId NOT IN (SELECT id FROM books WHERE deleted = 0)
                    OR ib.memberId NOT IN (SELECT id FROM members WHERE deleted = 0)
                  )
            """).fetchall()
            results["orphan_issues"] = [dict(r) for r in orphans]

            # Duplicate ISBNs
            dup_isbns = conn.execute("""
                SELECT isbn, COUNT(*) as cnt FROM books
                WHERE deleted = 0 AND isbn != '' AND isbn IS NOT NULL
                GROUP BY isbn HAVING cnt > 1
            """).fetchall()
            results["duplicate_isbns"] = [dict(r) for r in dup_isbns]

            # Duplicate Member IDs
            dup_mids = conn.execute("""
                SELECT memberId, COUNT(*) as cnt FROM members
                WHERE deleted = 0 AND memberId != '' AND memberId IS NOT NULL
                GROUP BY memberId HAVING cnt > 1
            """).fetchall()
            results["duplicate_member_ids"] = [dict(r) for r in dup_mids]

            # Missing titles
            no_title = conn.execute(
                "SELECT syncId, accNo FROM books WHERE deleted = 0 AND (title IS NULL OR title = '')"
            ).fetchall()
            results["missing_titles"] = [dict(r) for r in no_title]

            # Missing names
            no_name = conn.execute(
                "SELECT syncId, memberId FROM members WHERE deleted = 0 AND (name IS NULL OR name = '')"
            ).fetchall()
            results["missing_names"] = [dict(r) for r in no_name]

            # Ghost Issued: book status = 'Issued' but no active issue record
            ghost = conn.execute("""
                SELECT b.syncId, b.title, b.accNo FROM books b
                WHERE b.deleted = 0 AND b.status = 'Issued'
                  AND b.id NOT IN (
                    SELECT bookId FROM issued_books WHERE deleted = 0 AND status = 'Issued'
                  )
            """).fetchall()
            results["ghost_issued"] = [dict(r) for r in ghost]

            # Stuck Returns: issue returned but book still marked "Issued"
            stuck = conn.execute("""
                SELECT ib.syncId, ib.bookTitle, ib.bookId FROM issued_books ib
                WHERE ib.deleted = 0 AND ib.status = 'Returned'
                  AND ib.bookId IN (
                    SELECT id FROM books WHERE deleted = 0 AND status = 'Issued'
                  )
                  AND ib.bookId NOT IN (
                    SELECT bookId FROM issued_books
                    WHERE deleted = 0 AND status = 'Issued'
                  )
            """).fetchall()
            results["stuck_returns"] = [dict(r) for r in stuck]

            # Expired members with active issues
            import datetime
            today = datetime.date.today().isoformat()
            expired_active = conn.execute("""
                SELECT m.name, m.memberId, m.expiryDate, COUNT(ib.syncId) as active_books
                FROM members m
                JOIN issued_books ib ON ib.memberId = m.id AND ib.status = 'Issued' AND ib.deleted = 0
                WHERE m.deleted = 0 AND m.expiryDate < ? AND m.expiryDate != ''
                GROUP BY m.syncId
            """, (today,)).fetchall()
            results["expired_members_with_books"] = [dict(r) for r in expired_active]

        return results

    # ── Sample Data (for trying the app before real records exist) ────────────
    def seed_sample_data(self):
        """Insert a small set of realistic sample books, members, and one active
        issue so a brand-new install isn't empty. Safe to call multiple times —
        each call adds a fresh batch (use reset_all_data() first to start clean)."""
        import datetime
        import time as _time

        sample_books = [
            ("A Brief History of Time", "Stephen Hawking", "Bantam", "Science"),
            ("To Kill a Mockingbird", "Harper Lee", "J. B. Lippincott", "Fiction"),
            ("Introduction to Algorithms", "Cormen, Leiserson, Rivest", "MIT Press", "Computer Science"),
            ("The Diary of a Young Girl", "Anne Frank", "Contact Publishing", "History"),
            ("Sapiens", "Yuval Noah Harari", "Harvill Secker", "History"),
            ("Clean Code", "Robert C. Martin", "Prentice Hall", "Computer Science"),
            ("Pride and Prejudice", "Jane Austen", "T. Egerton", "English Literature"),
            ("Cosmos", "Carl Sagan", "Random House", "Science"),
        ]
        saved_books = []
        for i, (title, author, publisher, category) in enumerate(sample_books):
            book = Book(
                accNo=f"ACC-{1000 + i}", title=title, author=author,
                publisher=publisher, category=category, status="Available",
                price=500.0 + i * 50,
            )
            self.save_book(book)
            saved_books.append(book)

        sample_members = [
            ("Ali Khan", "10A", "Student"),
            ("Sara Ahmed", "10B", "Student"),
            ("Bilal Hussain", "9A", "Student"),
            ("Ayesha Malik", "Staff Room", "Faculty"),
            ("Usman Tariq", "9B", "Student"),
        ]
        saved_members = []
        today = datetime.date.today()
        for i, (name, className, mtype) in enumerate(sample_members):
            member = Member(
                memberId=f"MEM-{2000 + i}", name=name, className=className,
                memberType=mtype, joinDate=today.isoformat(),
                expiryDate=(today.replace(year=today.year + 1)).isoformat(),
                pin=f"{1000 + i}",
            )
            self.save_member(member)
            saved_members.append(member)

        # Issue a couple of books so the dashboard shows real activity.
        for book, member in list(zip(saved_books, saved_members))[:2]:
            book.status = "Issued"
            book.lastUpdated = int(_time.time() * 1000)
            self.save_book(book)
            member.booksIssued += 1
            self.save_member(member)
            record = IssueRecord(
                bookId=book.id, bookTitle=book.title, bookIsbn=book.isbn,
                memberId=member.id, memberName=member.name, memberMemberId=member.memberId,
                issueDate=today.isoformat(),
                dueDate=(today + datetime.timedelta(days=14)).isoformat(),
                status="Issued",
            )
            self.save_issue(record)

        self.log_audit_local("system", "seed_data", f"Seeded {len(saved_books)} books and {len(saved_members)} members")

    def reset_all_data(self):
        """Wipe all library data (books, members, issues, reservations, and
        every feature table) while keeping the school profile and staff
        accounts intact, so nobody gets locked out of their own app."""
        tables = [
            "books", "members", "issued_books", "reservations", "book_reviews",
            "audit_log", "backup_history", "inventory_audits", "fine_payments",
            "serials", "ill_requests", "purchase_orders",
        ]
        with self._get_conn() as conn:
            for table in tables:
                conn.execute(f"DELETE FROM {table}")
            conn.commit()
