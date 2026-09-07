"""
services/sync_service.py — Offline-first Two-Way Synchronization Engine.
Periodically pushes offline changes to Firestore and pulls remote changes.
Handles conflict resolution (latest serverTimestamp / lastUpdated wins).
"""
import time
from PyQt6.QtCore import QThread, pyqtSignal

from services.database_helper import DatabaseHelper
from services.firebase_service import FirebaseService
from models import Book, Member, IssueRecord, Reservation


class SyncService(QThread):
    sync_status = pyqtSignal(str)   # emits messages: "Syncing...", "Sync Complete", "Offline"
    sync_completed = pyqtSignal()   # fires when a sync cycle completes

    def __init__(self, db_helper: DatabaseHelper, fb_service: FirebaseService):
        super().__init__()
        self.db = db_helper
        self.fb = fb_service
        self.running = True
        self.interval = 15  # seconds between sync checks

    def stop(self):
        self.running = False

    def run(self):
        time.sleep(3)  # initial delay on startup
        while self.running:
            try:
                # 1. Test connection
                if not self.fb.test_connection():
                    self.sync_status.emit("Offline (Retrying...)")
                else:
                    self.sync_status.emit("Syncing...")
                    self.perform_sync()

                    # Feature 2: Overdue Auto-Reminder Scheduler
                    self._check_overdue_reminders()

                    self.sync_status.emit("🟢 Synced")
                    self.sync_completed.emit()
            except Exception as e:
                self.sync_status.emit(f"Sync Warning: {str(e)[:25]}...")

            # Sleep in small increments to respond to stop request quickly
            for _ in range(self.interval * 2):
                if not self.running:
                    break
                time.sleep(0.5)

    def _check_overdue_reminders(self):
        """Automatically check for overdue books and log reminders once a day."""
        today = time.strftime("%Y-%m-%d")
        last_check = self.db.get_last_sync_timestamp("overdue_reminder_check")

        # Only run check once every 24 hours
        if int(time.time() * 1000) - last_check < 86400000:
            return

        issues = self.db.get_issues()
        overdue_count = 0
        for i in issues:
            if i.status == "Issued" and i.dueDate and i.dueDate < today:
                # Mock: In a real app, integrate with Twilio/WhatsApp API here
                self.db.log_audit_local("SYSTEM", "auto_overdue_reminder",
                                       f"Auto-Reminder: {i.memberName} is overdue for '{i.bookTitle}'")
                overdue_count += 1

        if overdue_count > 0:
            print(f"DEBUG: Processed {overdue_count} auto-reminders.")

        self.db.set_last_sync_timestamp("overdue_reminder_check", int(time.time() * 1000))

    def perform_sync(self):
        # ── 1. Push local changes to Cloud ──
        pending = self.db.get_pending_sync()
        for item in pending:
            entity_type = item["entityType"]
            sync_id = item["syncId"]
            
            try:
                if entity_type == "books":
                    books = [b for b in self.db.get_books(include_deleted=True) if b.syncId == sync_id]
                    if books:
                        self.fb._books_ref().document(sync_id).set(books[0].to_dict())
                elif entity_type == "members":
                    members = [m for m in self.db.get_members(include_deleted=True) if m.syncId == sync_id]
                    if members:
                        self.fb._members_ref().document(sync_id).set(members[0].to_dict())
                elif entity_type == "issued_books":
                    issues = [i for i in self.db.get_issues(include_deleted=True) if i.syncId == sync_id]
                    if issues:
                        self.fb._issued_ref().document(sync_id).set(issues[0].to_dict())
                elif entity_type == "reservations":
                    res = [r for r in self.db.get_reservations(include_deleted=True) if r.syncId == sync_id]
                    if res:
                        self.fb._reservations_ref().document(sync_id).set(res[0].to_dict())
                
                # Successfully pushed, remove from local queue
                self.db.remove_from_sync_queue(entity_type, sync_id)
            except Exception as e:
                self.sync_status.emit(f"Push Error: {str(e)[:25]}...")
                # Don't delete from queue, retry next cycle

        # ── 2. Pull remote changes from Cloud ──
        self._pull_entity("books", self.fb._books_ref(), Book)
        self._pull_entity("members", self.fb._members_ref(), Member)
        self._pull_entity("issued_books", self.fb._issued_ref(), IssueRecord)
        self._pull_entity("reservations", self.fb._reservations_ref(), Reservation)

    def _pull_entity(self, name: str, ref, model_cls):
        try:
            last_pull = self.db.get_last_sync_timestamp(name)
            
            # Query Firestore for docs updated since last pull
            docs = ref.where("lastUpdated", ">", last_pull).stream()
            
            max_ts = last_pull
            pending_ids = {item["syncId"] for item in self.db.get_pending_sync() if item["entityType"] == name}

            for doc in docs:
                d = doc.to_dict()
                d["syncId"] = doc.id
                obj = model_cls.from_dict(d)
                
                # Check for Conflict
                if obj.syncId in pending_ids:
                    # Get local object to compare timestamps
                    local_obj = None
                    if name == "books":
                        local_obj = next((b for b in self.db.get_books(include_deleted=True) if b.syncId == obj.syncId), None)
                    elif name == "members":
                        local_obj = next((m for m in self.db.get_members(include_deleted=True) if m.syncId == obj.syncId), None)
                    elif name == "issued_books":
                        local_obj = next((i for i in self.db.get_issues(include_deleted=True) if i.syncId == obj.syncId), None)
                    elif name == "reservations":
                        local_obj = next((r for r in self.db.get_reservations(include_deleted=True) if r.syncId == obj.syncId), None)

                    if local_obj and local_obj.lastUpdated > obj.lastUpdated:
                        # Local is newer. Keep pending, log conflict, and DO NOT overwrite local.
                        self.db.log_conflict(name, obj.syncId, local_obj.to_dict(), obj.to_dict())
                        max_ts = max(max_ts, obj.lastUpdated)
                        continue

                    # Otherwise, remote is newer (or same). Overwrite local and remove from queue
                    self.db.remove_from_sync_queue(name, obj.syncId)

                # Save locally (mark as clean, so we don't queue it right back up)
                if name == "books":
                    self.db.save_book(obj, is_clean=True)
                elif name == "members":
                    self.db.save_member(obj, is_clean=True)
                elif name == "issued_books":
                    self.db.save_issue(obj, is_clean=True)
                elif name == "reservations":
                    self.db.save_reservation(obj, is_clean=True)
                    
                max_ts = max(max_ts, obj.lastUpdated)
                
            if max_ts > last_pull:
                self.db.set_last_sync_timestamp(name, max_ts)
        except Exception as e:
            self.sync_status.emit(f"Pull Error: {str(e)[:25]}...")
