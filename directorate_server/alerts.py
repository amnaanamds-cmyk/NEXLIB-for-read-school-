import time
import database

def check_and_generate_alerts(college_id: str, snapshot: dict):
    """
    Evaluates a college's snapshot data against system-wide warning/critical thresholds.
    Writes new alerts to the central alerts table.
    """
    alerts_to_create = []
    
    total_books = snapshot.get("total_books", 0)
    issued_books = snapshot.get("issued_books", 0)
    overdue_count = snapshot.get("overdue_count", 0)
    total_fines = snapshot.get("total_fines", 0.0)

    # 1. Overdue Rate Alert: If overdue books > 20% of issued books
    if issued_books > 0:
        overdue_rate = (overdue_count / issued_books) * 100
        if overdue_rate > 20.0:
            alerts_to_create.append({
                "alert_type": "overdue_rate",
                "message": f"High Overdue Rate: {overdue_rate:.1f}% of issued books are overdue ({overdue_count}/{issued_books}).",
                "severity": "critical" if overdue_rate > 35.0 else "warning"
            })
            
    # 2. Uncollected Fines Alert: If total fines exceeds Rs. 10,000
    if total_fines > 10000.0:
        alerts_to_create.append({
            "alert_type": "uncollected_fines",
            "message": f"High Uncollected Fines: Accumulated outstanding library fines total Rs. {total_fines:,.2f}.",
            "severity": "critical" if total_fines > 25000.0 else "warning"
        })

    # Save to database
    if alerts_to_create:
        with database.get_db() as conn:
            for alert in alerts_to_create:
                # Check if identical unacknowledged alert already exists for this college
                existing = conn.execute(
                    "SELECT id FROM alerts WHERE college_id = ? AND alert_type = ? AND acknowledged = 0",
                    (college_id, alert["alert_type"])
                ).fetchone()
                
                if not existing:
                    conn.execute("""
                        INSERT INTO alerts (college_id, alert_type, message, severity, created_at, acknowledged)
                        VALUES (?, ?, ?, ?, ?, 0)
                    """, (college_id, alert["alert_type"], alert["message"], alert["severity"], int(time.time() * 1000)))
            conn.commit()

def check_heartbeat_alerts():
    """
    Checks for colleges that have not synced in the last 7 days.
    """
    seven_days_ago = int(time.time() * 1000) - (7 * 24 * 60 * 60 * 1000)
    with database.get_db() as conn:
        stale_colleges = conn.execute(
            "SELECT id, name, last_sync_at FROM colleges WHERE last_sync_at < ? OR last_sync_at IS NULL",
            (seven_days_ago,)
        ).fetchall()
        
        for col in stale_colleges:
            last_sync_str = "Never" if not col["last_sync_at"] else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(col["last_sync_at"]/1000))
            message = f"Offline Alert: College '{col['name']}' has not synced data since {last_sync_str}."
            
            # Check if alert already exists
            existing = conn.execute(
                "SELECT id FROM alerts WHERE college_id = ? AND alert_type = 'no_sync' AND acknowledged = 0",
                (col["id"],)
            ).fetchone()
            
            if not existing:
                conn.execute("""
                    INSERT INTO alerts (college_id, alert_type, message, severity, created_at, acknowledged)
                    VALUES (?, 'no_sync', ?, 'critical', ?, 0)
                """, (col["id"], message, int(time.time() * 1000)))
        conn.commit()
