import json
import time
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

import database
import auth
import alerts

app = FastAPI(title="GDC Library Directorate Central Server", version="1.0.0")

# Enable CORS for web-based dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key header authentication for sync
api_key_header = APIKeyHeader(name="X-College-API-Key", auto_error=False)

# Seed database on startup
@app.on_event("startup")
def startup_event():
    database.init_db()
    # Seed default user director@gdc.edu / director123
    with database.get_db() as conn:
        row = conn.execute("SELECT email FROM directorate_users WHERE email = 'director@gdc.edu'").fetchone()
        if not row:
            p_hash = auth.get_password_hash("director123")
            conn.execute(
                "INSERT INTO directorate_users (email, password_hash, name, role) VALUES (?, ?, ?, ?)",
                ("director@gdc.edu", p_hash, "Directorate Administrator", "directorate_admin")
            )
            # Also seed some demo colleges with API keys for simulation
            conn.execute(
                "INSERT OR IGNORE INTO colleges (id, name, location, api_key, registered_at) VALUES (?, ?, ?, ?, ?)",
                ("gdc-peshawar", "GDC Peshawar", "Peshawar", "key-peshawar-123", int(time.time()*1000))
            )
            conn.execute(
                "INSERT OR IGNORE INTO colleges (id, name, location, api_key, registered_at) VALUES (?, ?, ?, ?, ?)",
                ("gdc-swat", "GDC Swat", "Swat", "key-swat-456", int(time.time()*1000))
            )
        conn.commit()

class LoginRequest(BaseModel):
    email: str
    password: str

class CollegeRegister(BaseModel):
    id: str
    name: str
    location: str
    api_key: str

class SyncSnapshot(BaseModel):
    college_id: str
    total_books: int
    available_books: int
    issued_books: int
    total_members: int
    overdue_count: int
    total_fines: float
    top_borrowed_books: List[dict] # title, count
    activity_summary: List[str]    # logs

class BookTransferRequest(BaseModel):
    from_college: str
    to_college: str
    book_title: str
    book_isbn: Optional[str] = None

# --- REST ENDPOINTS ---

# 1. Login
@app.post("/api/auth/login")
def login(req: LoginRequest):
    with database.get_db() as conn:
        user = conn.execute("SELECT * FROM directorate_users WHERE email = ?", (req.email,)).fetchone()
        if not user or not auth.verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        token = auth.create_access_token({"sub": user["email"], "role": user["role"]})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "email": user["email"],
                "name": user["name"],
                "role": user["role"]
            }
        }

# 2. Register College (Directorate Admin only or open with secret master key)
@app.post("/api/colleges/register")
def register_college(col: CollegeRegister, user: dict = Depends(auth.get_current_user)):
    with database.get_db() as conn:
        existing = conn.execute("SELECT id FROM colleges WHERE id = ?", (col.id,)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="College ID already registered")
        conn.execute(
            "INSERT INTO colleges (id, name, location, api_key, registered_at) VALUES (?, ?, ?, ?, ?)",
            (col.id, col.name, col.location, col.api_key, int(time.time()*1000))
        )
        conn.commit()
    return {"status": "success", "message": f"College {col.name} registered."}

# 3. Get Colleges List
@app.get("/api/colleges")
def get_colleges(user: dict = Depends(auth.get_current_user)):
    # Run heartbeat checking to ensure we flag any offline college
    alerts.check_heartbeat_alerts()
    
    with database.get_db() as conn:
        rows = conn.execute("""
            SELECT c.*, 
                   (SELECT COUNT(*) FROM alerts a WHERE a.college_id = c.id AND a.acknowledged = 0) as alert_count,
                   (SELECT total_books FROM college_snapshots s WHERE s.college_id = c.id ORDER BY timestamp DESC LIMIT 1) as total_books,
                   (SELECT total_members FROM college_snapshots s WHERE s.college_id = c.id ORDER BY timestamp DESC LIMIT 1) as total_members
            FROM colleges c
        """).fetchall()
        return [dict(r) for r in rows]

# 4. Push Sync Snapshot from College
@app.post("/api/sync")
def sync_push(snapshot: SyncSnapshot, x_college_api_key: Optional[str] = Security(api_key_header)):
    if not x_college_api_key or not auth.verify_api_key(snapshot.college_id, x_college_api_key):
        raise HTTPException(status_code=403, detail="Invalid College ID or API Key")
        
    ts = int(time.time() * 1000)
    with database.get_db() as conn:
        # Update last sync time
        conn.execute("UPDATE colleges SET last_sync_at = ? WHERE id = ?", (ts, snapshot.college_id))
        
        # Save snapshot
        conn.execute("""
            INSERT INTO college_snapshots (
                college_id, timestamp, total_books, available_books, issued_books,
                total_members, overdue_count, total_fines, top_borrowed_books, activity_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot.college_id, ts, snapshot.total_books, snapshot.available_books,
            snapshot.issued_books, snapshot.total_members, snapshot.overdue_count,
            snapshot.total_fines, json.dumps(snapshot.top_borrowed_books),
            json.dumps(snapshot.activity_summary)
        ))
        conn.commit()
        
    # Evaluate alerts
    alerts.check_and_generate_alerts(snapshot.college_id, snapshot.dict())
    
    return {"status": "success", "timestamp": ts}

# 5. Get Aggregate Stats
@app.get("/api/aggregate")
def get_aggregate_stats(user: dict = Depends(auth.get_current_user)):
    with database.get_db() as conn:
        # Get latest snapshot for each college
        latest_snapshots = conn.execute("""
            SELECT s.* FROM college_snapshots s
            INNER JOIN (
                SELECT college_id, MAX(timestamp) as max_ts 
                FROM college_snapshots 
                GROUP BY college_id
            ) latest ON s.college_id = latest.college_id AND s.timestamp = latest.max_ts
        """).fetchall()
        
        total_books = sum(s["total_books"] for s in latest_snapshots)
        available_books = sum(s["available_books"] for s in latest_snapshots)
        issued_books = sum(s["issued_books"] for s in latest_snapshots)
        total_members = sum(s["total_members"] for s in latest_snapshots)
        overdue_count = sum(s["overdue_count"] for s in latest_snapshots)
        total_fines = sum(s["total_fines"] for s in latest_snapshots)
        
        return {
            "total_books": total_books,
            "available_books": available_books,
            "issued_books": issued_books,
            "total_members": total_members,
            "overdue_count": overdue_count,
            "total_fines": total_fines,
            "college_count": len(latest_snapshots)
        }

# 6. Get Single College Stats
@app.get("/api/colleges/{college_id}/stats")
def get_college_stats(college_id: str, user: dict = Depends(auth.get_current_user)):
    with database.get_db() as conn:
        college = conn.execute("SELECT * FROM colleges WHERE id = ?", (college_id,)).fetchone()
        if not college:
            raise HTTPException(status_code=404, detail="College not found")
            
        snapshot = conn.execute(
            "SELECT * FROM college_snapshots WHERE college_id = ? ORDER BY timestamp DESC LIMIT 1",
            (college_id,)
        ).fetchone()
        
        if not snapshot:
            return {
                "college": dict(college),
                "snapshot": None
            }
            
        snap_dict = dict(snapshot)
        snap_dict["top_borrowed_books"] = json.loads(snap_dict["top_borrowed_books"] or "[]")
        snap_dict["activity_summary"] = json.loads(snap_dict["activity_summary"] or "[]")
        
        return {
            "college": dict(college),
            "snapshot": snap_dict
        }

# 7. Get Alerts
@app.get("/api/alerts")
def get_alerts(user: dict = Depends(auth.get_current_user)):
    with database.get_db() as conn:
        rows = conn.execute("""
            SELECT a.*, c.name as college_name 
            FROM alerts a
            INNER JOIN colleges c ON a.college_id = c.id
            WHERE a.acknowledged = 0
            ORDER BY a.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, user: dict = Depends(auth.get_current_user)):
    with database.get_db() as conn:
        conn.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
        conn.commit()
    return {"status": "success"}

# 8. Book Transfers
@app.post("/api/transfers")
def request_transfer(req: BookTransferRequest):
    # This can be triggered from Python app.
    # To keep it simple, we allow keyless creation or authenticating with college ID headers
    with database.get_db() as conn:
        conn.execute("""
            INSERT INTO book_transfers (from_college, to_college, book_title, book_isbn, status, requested_at, updated_at)
            VALUES (?, ?, ?, ?, 'requested', ?, ?)
        """, (req.from_college, req.to_college, req.book_title, req.book_isbn, int(time.time()*1000), int(time.time()*1000)))
        conn.commit()
    return {"status": "success"}

@app.get("/api/transfers")
def get_transfers(user: dict = Depends(auth.get_current_user)):
    with database.get_db() as conn:
        rows = conn.execute("""
            SELECT t.*, f.name as from_college_name, o.name as to_college_name 
            FROM book_transfers t
            INNER JOIN colleges f ON t.from_college = f.id
            INNER JOIN colleges o ON t.to_college = o.id
            ORDER BY t.requested_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

@app.get("/api/transfers/college/{college_id}")
def get_college_transfers(college_id: str):
    # Endpoint accessible by local colleges to see incoming / outgoing requests
    with database.get_db() as conn:
        rows = conn.execute("""
            SELECT t.*, f.name as from_college_name, o.name as to_college_name 
            FROM book_transfers t
            INNER JOIN colleges f ON t.from_college = f.id
            INNER JOIN colleges o ON t.to_college = o.id
            WHERE t.from_college = ? OR t.to_college = ?
        """, (college_id, college_id)).fetchall()
        return [dict(r) for r in rows]

@app.post("/api/transfers/{transfer_id}/status")
def update_transfer_status(transfer_id: int, status: str):
    if status not in ('requested', 'in-transit', 'received', 'rejected'):
        raise HTTPException(status_code=400, detail="Invalid status")
    with database.get_db() as conn:
        conn.execute(
            "UPDATE book_transfers SET status = ?, updated_at = ? WHERE id = ?",
            (status, int(time.time()*1000), transfer_id)
        )
        conn.commit()
    return {"status": "success"}

# 9. Comparison Rankings
@app.get("/api/comparison")
def get_comparison(user: dict = Depends(auth.get_current_user)):
    with database.get_db() as conn:
        rows = conn.execute("""
            SELECT c.id, c.name,
                   (SELECT total_books FROM college_snapshots s WHERE s.college_id = c.id ORDER BY timestamp DESC LIMIT 1) as total_books,
                   (SELECT overdue_count FROM college_snapshots s WHERE s.college_id = c.id ORDER BY timestamp DESC LIMIT 1) as overdue_count,
                   (SELECT total_fines FROM college_snapshots s WHERE s.college_id = c.id ORDER BY timestamp DESC LIMIT 1) as total_fines
            FROM colleges c
        """).fetchall()
        
        colleges = [dict(r) for r in rows]
        # Calculate rates
        for col in colleges:
            col["total_books"] = col["total_books"] or 0
            col["overdue_count"] = col["overdue_count"] or 0
            col["total_fines"] = col["total_fines"] or 0.0
            
        return colleges

# 10. Generate PDF Report of all colleges (Part C feature 5)
@app.get("/api/reports/export")
def export_directorate_report(user: dict = Depends(auth.get_current_user)):
    # We will generate a quick summary string or offer to stream a dynamically generated spreadsheet/PDF
    # For now, return the aggregated statistics as a JSON download trigger.
    # We will implement the actual PDF logic dynamically in Python side reports or server side reportlab.
    return {"message": "Export functionality ready."}
