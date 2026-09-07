"""
services/firebase_service.py
Firestore + Firebase Storage integration using firebase-admin SDK.
Credentials loaded from .env — never hardcoded.

Collection paths match the Android KMP shared module exactly:
  institutions/{college_id}/books/{syncId}
  institutions/{college_id}/members/{syncId}
  institutions/{college_id}/issued_books/{syncId}
  institutions/{college_id}/reservations/{syncId}
"""
import os
import time
import uuid
from pathlib import Path
from typing import Callable, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore, storage

import config
from models import Book, Member, IssueRecord, Reservation


# ─── Initialise Firebase (singleton) ─────────────────────────────────────────
def _init_firebase() -> bool:
    """Returns True if successfully initialized, False if key is missing."""
    if not firebase_admin._apps:
        cred_path = Path(config.FIREBASE_CRED_PATH)
        if not cred_path.is_absolute():
            cred_path = Path(__file__).parent.parent / cred_path
        if not cred_path.exists():
            print(f"Warning: Firebase credentials key not found at {cred_path}. Starting in Offline Demo mode.")
            return False
        try:
            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred, {
                "storageBucket": config.FIREBASE_STORAGE_BUCKET
            })
            return True
        except Exception as e:
            print(f"Warning: Failed to load Firebase credentials: {e}. Starting in Offline Demo mode.")
            return False
    return True


# ─── FirebaseService ─────────────────────────────────────────────────────────
class FirebaseService:
    """
    Central service for all Firestore and Storage operations.
    If credentials are not found, falls back to a safe mock state.
    """

    def __init__(self):
        self.mock_mode = not _init_firebase()
        if not self.mock_mode:
            self.db = firestore.client()
        else:
            self.db = None
        self.college_id = config.COLLEGE_ID

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _inst_ref(self):
        if self.mock_mode or not self.db: return None
        return self.db.collection("institutions").document(self.college_id)

    def _books_ref(self):
        ref = self._inst_ref()
        return ref.collection("books") if ref else None

    def _members_ref(self):
        ref = self._inst_ref()
        return ref.collection("members") if ref else None

    def _issued_ref(self):
        ref = self._inst_ref()
        return ref.collection("issued_books") if ref else None

    def _reservations_ref(self):
        ref = self._inst_ref()
        return ref.collection("reservations") if ref else None

    def _audit_ref(self):
        ref = self._inst_ref()
        return ref.collection("audit_log") if ref else None

    def _settings_ref(self):
        ref = self._inst_ref()
        return ref.collection("settings").document("library_settings") if ref else None

    # ── Connectivity Test ─────────────────────────────────────────────────────
    def test_connection(self) -> bool:
        if self.mock_mode or not self.db:
            return False
        try:
            self._inst_ref().get()
            return True
        except Exception:
            return False

    # ── Books ─────────────────────────────────────────────────────────────────
    def get_all_books(self) -> List[Book]:
        ref = self._books_ref()
        if not ref: return []
        docs = ref.where("deleted", "==", False).stream()
        return [Book.from_dict({**d.to_dict(), "syncId": d.id}) for d in docs]

    def listen_books(self, callback: Callable[[List[Book]], None]):
        """Real-time listener — fires callback whenever books change."""
        ref = self._books_ref()
        if not ref: return None
        def on_snapshot(col_snapshot, changes, read_time):
            books = []
            for doc in col_snapshot:
                b = Book.from_dict({**doc.to_dict(), "syncId": doc.id})
                if not b.deleted:
                    books.append(b)
            callback(books)
        return ref.on_snapshot(on_snapshot)

    def save_book(self, book: Book, user_email: str = "") -> str:
        if not book.syncId:
            book.syncId = str(uuid.uuid4())
        book.lastUpdated = int(time.time() * 1000)
        ref = self._books_ref()
        if ref:
            ref.document(book.syncId).set(book.to_dict())
            self._log_audit(user_email, "book_save", f"Book: {book.title} ({book.syncId})")
        return book.syncId

    def delete_book(self, sync_id: str, user_email: str = ""):
        ref = self._books_ref()
        if ref:
            ref.document(sync_id).update({
                "deleted": True,
                "lastUpdated": int(time.time() * 1000)
            })
            self._log_audit(user_email, "book_delete", f"BookSyncId: {sync_id}")

    def update_book_status(self, sync_id: str, status: str, user_email: str = ""):
        ref = self._books_ref()
        if not ref or self.mock_mode: return
        @firestore.transactional
        def _txn(transaction, r):
            snap = r.get(transaction=transaction)
            if snap.exists:
                transaction.update(r, {
                    "status": status,
                    "lastUpdated": int(time.time() * 1000)
                })
        doc_ref = ref.document(sync_id)
        _txn(self.db.transaction(), doc_ref)
        self._log_audit(user_email, "book_status_update", f"SyncId: {sync_id} → {status}")

    # ── Members ───────────────────────────────────────────────────────────────
    def get_all_members(self) -> List[Member]:
        ref = self._members_ref()
        if not ref: return []
        docs = ref.where("deleted", "==", False).stream()
        return [Member.from_dict({**d.to_dict(), "syncId": d.id}) for d in docs]

    def listen_members(self, callback: Callable[[List[Member]], None]):
        ref = self._members_ref()
        if not ref: return None
        def on_snapshot(col_snapshot, changes, read_time):
            members = []
            for doc in col_snapshot:
                m = Member.from_dict({**doc.to_dict(), "syncId": doc.id})
                if not m.deleted:
                    members.append(m)
            callback(members)
        return ref.on_snapshot(on_snapshot)

    def save_member(self, member: Member, user_email: str = "") -> str:
        if not member.syncId:
            member.syncId = str(uuid.uuid4())
        member.lastUpdated = int(time.time() * 1000)
        ref = self._members_ref()
        if ref:
            ref.document(member.syncId).set(member.to_dict())
            self._log_audit(user_email, "member_save", f"Member: {member.name} ({member.syncId})")
        return member.syncId

    def delete_member(self, sync_id: str, user_email: str = ""):
        ref = self._members_ref()
        if ref:
            ref.document(sync_id).update({
                "deleted": True,
                "lastUpdated": int(time.time() * 1000)
            })
            self._log_audit(user_email, "member_delete", f"MemberSyncId: {sync_id}")

    def reset_member_pin(self, sync_id: str, new_pin: str, user_email: str = ""):
        ref = self._members_ref()
        if ref:
            ref.document(sync_id).update({
                "pin": new_pin,
                "lastUpdated": int(time.time() * 1000)
            })
            self._log_audit(user_email, "member_pin_reset", f"MemberSyncId: {sync_id}")

    # ── Issue / Return ────────────────────────────────────────────────────────
    def get_active_issues(self) -> List[IssueRecord]:
        ref = self._issued_ref()
        if not ref: return []
        docs = ref.where("status", "==", "Issued").where("deleted", "==", False).stream()
        return [IssueRecord.from_dict({**d.to_dict(), "syncId": d.id}) for d in docs]

    def get_all_issues(self) -> List[IssueRecord]:
        ref = self._issued_ref()
        if not ref: return []
        docs = ref.where("deleted", "==", False).stream()
        return [IssueRecord.from_dict({**d.to_dict(), "syncId": d.id}) for d in docs]

    def get_member_issues(self, member_id: int) -> List[IssueRecord]:
        ref = self._issued_ref()
        if not ref: return []
        docs = ref.where("memberId", "==", member_id).where("deleted", "==", False).stream()
        return [IssueRecord.from_dict({**d.to_dict(), "syncId": d.id}) for d in docs]

    def listen_issues(self, callback: Callable[[List[IssueRecord]], None]):
        ref = self._issued_ref()
        if not ref: return None
        def on_snapshot(col_snapshot, changes, read_time):
            issues = [
                IssueRecord.from_dict({**doc.to_dict(), "syncId": doc.id})
                for doc in col_snapshot
                if not doc.to_dict().get("deleted", False)
            ]
            callback(issues)
        return ref.on_snapshot(on_snapshot)

    def issue_book(self, record: IssueRecord, book_sync_id: str, user_email: str = "") -> str:
        """Atomically create issue record + set book to 'Issued'."""
        record.syncId = str(uuid.uuid4())
        record.lastUpdated = int(time.time() * 1000)
        if self.mock_mode or not self.db: return record.syncId

        @firestore.transactional
        def _txn(transaction):
            issue_ref = self._issued_ref().document(record.syncId)
            book_ref = self._books_ref().document(book_sync_id)
            transaction.set(issue_ref, record.to_dict())
            transaction.update(book_ref, {
                "status": "Issued",
                "lastUpdated": int(time.time() * 1000)
            })

        _txn(self.db.transaction())
        self._log_audit(user_email, "book_issue",
                        f"Book: {record.bookTitle} → {record.memberName}")
        return record.syncId

    def return_book(self, issue_sync_id: str, book_sync_id: str,
                    fine: float, user_email: str = ""):
        """Atomically mark returned + set book to 'Available'."""
        return_date = time.strftime("%Y-%m-%d")
        now = int(time.time() * 1000)
        if self.mock_mode or not self.db: return

        @firestore.transactional
        def _txn(transaction):
            issue_ref = self._issued_ref().document(issue_sync_id)
            book_ref = self._books_ref().document(book_sync_id)
            transaction.update(issue_ref, {
                "status": "Returned",
                "returnDate": return_date,
                "fine": fine,
                "lastUpdated": now,
            })
            transaction.update(book_ref, {
                "status": "Available",
                "lastUpdated": now,
            })

        _txn(self.db.transaction())
        self._log_audit(user_email, "book_return",
                        f"IssueSyncId: {issue_sync_id}, fine: {fine}")

    # ── Reservations ──────────────────────────────────────────────────────────
    def get_pending_reservations(self) -> List[Reservation]:
        ref = self._reservations_ref()
        if not ref: return []
        docs = ref.where("status", "==", "Pending").where("deleted", "==", False).stream()
        return [Reservation.from_dict({**d.to_dict(), "syncId": d.id}) for d in docs]

    def listen_reservations(self, callback: Callable[[List[Reservation]], None]):
        ref = self._reservations_ref()
        if not ref: return None
        def on_snapshot(col_snapshot, changes, read_time):
            res = [
                Reservation.from_dict({**doc.to_dict(), "syncId": doc.id})
                for doc in col_snapshot
                if not doc.to_dict().get("deleted", False)
            ]
            callback(res)
        return ref.on_snapshot(on_snapshot)

    def fulfill_reservation(self, sync_id: str, user_email: str = ""):
        ref = self._reservations_ref()
        if ref:
            ref.document(sync_id).update({
                "status": "Fulfilled",
                "notifiedDate": time.strftime("%Y-%m-%d"),
                "lastUpdated": int(time.time() * 1000)
            })
            self._log_audit(user_email, "reservation_fulfilled", f"SyncId: {sync_id}")

    # ── Settings ──────────────────────────────────────────────────────────────
    def get_fine_rate(self) -> float:
        ref = self._settings_ref()
        if not ref:
            return config.DEFAULT_FINE_RATE
        try:
            doc = ref.get()
            if doc.exists:
                return float(doc.to_dict().get("fineRatePerDay", config.DEFAULT_FINE_RATE))
        except Exception:
            pass
        return config.DEFAULT_FINE_RATE

    def save_settings(self, fine_rate: float, user_email: str = ""):
        ref = self._settings_ref()
        if ref:
            ref.set({"fineRatePerDay": fine_rate}, merge=True)
            self._log_audit(user_email, "settings_update", f"fineRate: {fine_rate}")

    # ── Audit Log ─────────────────────────────────────────────────────────────
    def _log_audit(self, user_email: str, action: str, detail: str):
        ref = self._audit_ref()
        if ref:
            ref.add({
                "userEmail": user_email,
                "action": action,
                "detail": detail,
                "timestamp": int(time.time() * 1000),
                "timestampStr": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

    def get_audit_log(self, limit: int = 100) -> list:
        ref = self._audit_ref()
        if not ref: return []
        docs = ref.order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).limit(limit).stream()
        return [d.to_dict() for d in docs]

    # ── Storage (Cover / Photo upload) ────────────────────────────────────────
    def upload_file(self, local_path: str, remote_path: str) -> str:
        """Upload a file to Firebase Storage and return the public URL."""
        if self.mock_mode: return ""
        bucket = storage.bucket()
        blob = bucket.blob(remote_path)
        blob.upload_from_filename(local_path)
        blob.make_public()
        return blob.public_url

    # ── Statistics (for Director Dashboard) ──────────────────────────────────
    def get_statistics(self) -> dict:
        if self.mock_mode: return {}
        books = self.get_all_books()
        members = self.get_all_members()
        issues = self.get_active_issues()
        reservations = self.get_pending_reservations()

        total_books = len(books)
        available = sum(1 for b in books if b.status == "Available")
        issued_count = sum(1 for b in books if b.status == "Issued")
        overdue = []
        today = time.strftime("%Y-%m-%d")
        for rec in issues:
            if rec.dueDate and rec.dueDate < today:
                overdue.append(rec)

        categories = {}
        for b in books:
            categories[b.category] = categories.get(b.category, 0) + 1

        digital = sum(1 for b in books if b.isDigital)
        with_isbn = sum(1 for b in books if b.isbn)

        return {
            "totalBooks": total_books,
            "availableBooks": available,
            "issuedBooks": issued_count,
            "totalMembers": len(members),
            "activeIssues": len(issues),
            "overdueCount": len(overdue),
            "pendingReservations": len(reservations),
            "categories": categories,
            "digitalizationProgress": {
                "withIsbn": round(with_isbn / total_books * 100, 1) if total_books else 0,
                "withEBook": round(digital / total_books * 100, 1) if total_books else 0,
            },
        }
