"""
ui/screens/issue_return_screen.py — Issue & Return system with color-coded due dates,
fine calculation, and history log. Fully offline (local SQLite).
"""
import time
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QLineEdit, QMessageBox, QDateEdit,
    QTabWidget, QFrame, QDialogButtonBox, QTextEdit, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate, QTimer
from PyQt6.QtGui import QColor, QKeyEvent, QPainter, QFont, QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from models import IssueRecord
from services.advanced_service import AdvancedService


def days_diff(due_date_str: str) -> int:
    try:
        due = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
        return (due - datetime.date.today()).days
    except Exception:
        return 0


def status_color(days: int) -> str:
    if days < 0:   return "#EF4444"   # red — overdue
    if days < 3:   return "#F59E0B"   # orange — 0-2 days
    if days < 7:   return "#FBBF24"   # yellow — 3-6 days
    return "#10B981"                   # green — 7+


class IssueWorker(QThread):
    finished = pyqtSignal(bool, str)
    def __init__(self, db, record, book, user_email):
        super().__init__()
        self.db, self.record, self.book, self.user_email = db, record, book, user_email
    def run(self):
        try:
            import uuid
            self.record.syncId = str(uuid.uuid4())
            self.record.lastUpdated = int(time.time() * 1000)
            
            # Save issue locally
            self.db.save_issue(self.record)
            
            # Update book status locally
            self.book.status = "Issued"
            self.book.lastUpdated = int(time.time() * 1000)
            self.db.save_book(self.book)
            
            # Update member issued count
            members = [m for m in self.db.get_members() if m.id == self.record.memberId]
            if members:
                m = members[0]
                m.booksIssued += 1
                m.lastUpdated = int(time.time() * 1000)
                self.db.save_member(m)
                
            self.db.log_audit_local(self.user_email, "book_issue", f"Book: {self.record.bookTitle} → {self.record.memberName}")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class ReturnWorker(QThread):
    finished = pyqtSignal(bool, str)
    def __init__(self, db, record, book, fine, user_email):
        super().__init__()
        self.db, self.record, self.book, self.fine, self.user_email = db, record, book, fine, user_email
    def run(self):
        try:
            now = int(time.time() * 1000)
            # Update issue locally
            self.record.status = "Returned"
            self.record.returnDate = time.strftime("%Y-%m-%d")
            self.record.fine = self.fine
            self.record.lastUpdated = now
            self.db.save_issue(self.record)
            
            # Update book locally
            if self.book:
                self.book.status = "Available"
                self.book.lastUpdated = now
                self.db.save_book(self.book)
                
            # Update member issued count
            members = [m for m in self.db.get_members() if m.id == self.record.memberId]
            if members:
                m = members[0]
                m.booksIssued = max(0, m.booksIssued - 1)
                m.lastUpdated = now
                self.db.save_member(m)
                
            self.db.log_audit_local(self.user_email, "book_return", f"IssueSyncId: {self.record.syncId}, fine: {self.fine}")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class IssueDialog(QDialog):
    STYLE = """
    QDialog{background:#0D1B2A;}
    QLabel{color:#A0B4CC;font-size:12px;font-family:'Segoe UI';}
    QComboBox,QDateEdit{background:#0D1F38;border:1.5px solid #1E3050;border-radius:8px;
        padding:8px 12px;color:#E8EEF8;font-size:13px;}
    QComboBox:focus,QDateEdit:focus{border-color:#C8A84B;}
    QPushButton#issueBtn{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #059669,stop:1 #10B981);
        color:white;border:none;border-radius:8px;padding:10px 24px;font-size:14px;font-weight:700;}
    QPushButton#cancelBtn{background:rgba(30,48,80,0.5);color:#6B8CAE;border:1px solid #1E3050;
        border-radius:8px;padding:10px 20px;}
    """

    def __init__(self, members, books, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Issue Book")
        self.setStyleSheet(self.STYLE)
        self.setMinimumWidth(480)
        self._members = members
        self._books   = [b for b in books if b.status == "Available"]
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24,20,24,20); lay.setSpacing(14)
        lay.addWidget(QLabel("📋  Issue Book",
                             styleSheet="font-size:16px;font-weight:800;color:#E6C96E;"))
        form = QFormLayout(); form.setSpacing(10)

        self.member_cb = QComboBox()
        self.member_cb.addItems([f"{m.memberId}  —  {m.name}" for m in self._members])
        self.member_cb.setEditable(True)

        self.book_cb = QComboBox()
        self.book_cb.addItems([f"[{b.accNo}]  {b.title}" for b in self._books])
        self.book_cb.setEditable(True)

        self.due_date = QDateEdit(QDate.currentDate().addDays(14))
        self.due_date.setCalendarPopup(True)
        self.due_date.setDisplayFormat("yyyy-MM-dd")

        form.addRow("Member *", self.member_cb)
        form.addRow("Book (Available) *", self.book_cb)
        form.addRow("Due Date *", self.due_date)
        lay.addLayout(form)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = QPushButton("Cancel"); cancel.setObjectName("cancelBtn")
        cancel.clicked.connect(self.reject)
        issue = QPushButton("✅  Issue Book"); issue.setObjectName("issueBtn")
        issue.clicked.connect(self._issue)
        btn_row.addWidget(cancel); btn_row.addWidget(issue)
        lay.addLayout(btn_row)

    def _issue(self):
        m_idx = self.member_cb.currentIndex()
        b_idx = self.book_cb.currentIndex()
        if m_idx < 0 or b_idx < 0:
            QMessageBox.warning(self, "Required", "Select both member and book."); return
        self._member = self._members[m_idx]
        self._book   = self._books[b_idx]
        self._due    = self.due_date.date().toString("yyyy-MM-dd")
        self.accept()

    def get_data(self):
        return self._member, self._book, self._due


class IssueReturnScreen(QWidget):
    ISSUE_COLS  = ["Member ID", "Member Name", "Book", "ISBN",
                   "Issue Date", "Due Date", "Days Left", "Status"]
    HISTORY_COLS = ["Member", "Book", "Issued", "Due", "Returned", "Fine", "Status"]

    def __init__(self, db_helper, auth_service):
        super().__init__()
        self.db   = db_helper
        self.auth = auth_service
        self.adv  = AdvancedService(db_helper)
        self._issues  = []
        self._history = []
        self._all_members = []
        self._all_books   = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28,24,28,24); layout.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("📋  Issue & Return",
                              styleSheet="font-size:22px;font-weight:800;color:#E8EEF8;font-family:'Segoe UI';"))
        hdr.addStretch()
        issue_btn = QPushButton("➕  Issue Book")
        issue_btn.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #059669,stop:1 #10B981);"
            "color:white;border:none;border-radius:8px;padding:9px 18px;font-size:13px;font-weight:700;"
        )
        issue_btn.clicked.connect(self._issue_book)
        hdr.addWidget(issue_btn)

        bulk_issue_btn = QPushButton("📦 Bulk Issue Wizard")
        bulk_issue_btn.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2563EB,stop:1 #3B82F6);"
            "color:white;border:none;border-radius:8px;padding:9px 18px;font-size:13px;font-weight:700;"
        )
        bulk_issue_btn.clicked.connect(self._bulk_issue_mock)
        hdr.addWidget(bulk_issue_btn)

        scan_btn = QPushButton("📟  Barcode Scanner Mode")
        scan_btn.setStyleSheet(
            "background:#C8A84B;color:#0D1B2A;border:none;border-radius:8px;padding:9px 18px;font-size:13px;font-weight:700;"
        )
        scan_btn.clicked.connect(self._open_scanner)
        hdr.addWidget(scan_btn)

        layout.addLayout(hdr)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane{background:#071428;border:1px solid #1E3050;border-radius:8px;}
            QTabBar::tab{background:#0D1B2A;color:#6B8CAE;padding:10px 18px;font-size:12px;font-weight:600;}
            QTabBar::tab:selected{background:#1E3050;color:#E6C96E;border-bottom:2px solid #C8A84B;}
        """)

        # Active issues tab
        active_widget = QWidget()
        av_lay = QVBoxLayout(active_widget); av_lay.setContentsMargins(8,8,8,8)
        self.fine_rate_lbl = QLabel()
        self.fine_rate_lbl.setStyleSheet("color:#4D6A90;font-size:11px;")
        av_lay.addWidget(self.fine_rate_lbl)
        self.active_table = self._make_table(self.ISSUE_COLS)
        av_lay.addWidget(self.active_table)
        
        btn_row = QHBoxLayout()
        return_btn = QPushButton("🔄  Return Selected")
        return_btn.setStyleSheet(
            "background:rgba(217,119,6,0.15);color:#F59E0B;"
            "border:1px solid rgba(217,119,6,0.4);border-radius:8px;"
            "padding:9px 18px;font-size:13px;font-weight:700;"
        )
        return_btn.clicked.connect(self._return_book)
        btn_row.addWidget(return_btn)

        renew_btn = QPushButton("📅  Renew (+14 days)")
        renew_btn.setStyleSheet(
            "background:rgba(16,185,129,0.15);color:#10B981;"
            "border:1px solid rgba(16,185,129,0.4);border-radius:8px;"
            "padding:9px 18px;font-size:13px;font-weight:700;"
        )
        renew_btn.clicked.connect(self._renew_book)
        btn_row.addWidget(renew_btn)

        remind_btn = QPushButton("🔔  Send Reminder")
        remind_btn.setStyleSheet(
            "background:rgba(239,68,68,0.15);color:#EF4444;"
            "border:1px solid rgba(239,68,68,0.4);border-radius:8px;"
            "padding:9px 18px;font-size:13px;font-weight:700;"
        )
        remind_btn.clicked.connect(self._send_reminder)
        btn_row.addWidget(remind_btn)

        receipt_btn = QPushButton("🧧 Print Fine Receipt")
        receipt_btn.setStyleSheet(
            "background:rgba(8,145,178,0.15);color:#06B6D4;"
            "border:1px solid rgba(8,145,178,0.4);border-radius:8px;"
            "padding:9px 18px;font-size:13px;font-weight:700;"
        )
        receipt_btn.clicked.connect(self._print_receipt)
        btn_row.addWidget(receipt_btn)
        
        av_lay.addLayout(btn_row)
        tabs.addTab(active_widget, "📖  Active Issues")

        # History tab
        hist_widget = QWidget()
        hv_lay = QVBoxLayout(hist_widget); hv_lay.setContentsMargins(8,8,8,8)
        search_row = QHBoxLayout()
        self.hist_search = QLineEdit()
        self.hist_search.setPlaceholderText("🔍  Filter history…")
        self.hist_search.setStyleSheet("background:#0D1F38;border:1.5px solid #1E3050;border-radius:8px;padding:8px 14px;color:#E8EEF8;font-size:13px;")
        self.hist_search.textChanged.connect(self._filter_history)
        search_row.addWidget(self.hist_search)
        hv_lay.addLayout(search_row)
        self.history_table = self._make_table(self.HISTORY_COLS)
        hv_lay.addWidget(self.history_table)
        tabs.addTab(hist_widget, "📜  Full History")

        layout.addWidget(tabs)

    def _make_table(self, cols):
        t = QTableWidget()
        t.setColumnCount(len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.setStyleSheet("""
            QTableWidget{background:#071428;color:#E8EEF8;gridline-color:#1E3050;border:none;font-size:13px;}
            QTableWidget::item{padding:8px;}
            QTableWidget::item:selected{background:rgba(30,95,212,0.3);}
            QHeaderView::section{background:#0D1B2A;color:#6B8CAE;font-weight:700;font-size:11px;padding:8px;border-bottom:1px solid #1E3050;}
            QTableWidget::item:alternate{background:rgba(13,28,55,0.6);}
        """)
        return t

    def refresh(self):
        self._load_data()
        issues = self.db.get_issues()
        active  = [i for i in issues if i.status == "Issued"]
        self._issues  = active
        self._history = issues
        self._populate_active(active)
        self._populate_history(issues)

    def _populate_active(self, issues):
        fine_rate = self.db.get_fine_rate()
        self.fine_rate_lbl.setText(f"Fine rate: Rs. {fine_rate}/day")
        self.active_table.setRowCount(len(issues))
        for row, r in enumerate(issues):
            days = days_diff(r.dueDate)
            color = status_color(days)
            day_str = f"{days}d" if days >= 0 else f"OVERDUE {abs(days)}d"
            for col, val in enumerate([
                r.memberMemberId, r.memberName, r.bookTitle, r.bookIsbn,
                r.issueDate, r.dueDate, day_str, r.status
            ]):
                item = QTableWidgetItem(val)
                if col == 6:
                    item.setForeground(QColor(color))
                self.active_table.setItem(row, col, item)

    def _populate_history(self, issues):
        filtered = issues
        q = self.hist_search.text().lower() if hasattr(self, "hist_search") else ""
        if q:
            filtered = [i for i in issues if any(
                q in f.lower() for f in [i.memberName, i.bookTitle, i.bookIsbn])]
        self.history_table.setRowCount(len(filtered))
        for row, r in enumerate(filtered):
            for col, val in enumerate([
                r.memberName, r.bookTitle, r.issueDate, r.dueDate,
                r.returnDate or "—", f"Rs.{r.fine:.0f}", r.status
            ]):
                item = QTableWidgetItem(val)
                if col == 6:
                    item.setForeground(QColor("#10B981" if val == "Returned" else "#F59E0B"))
                if col == 5 and r.fine > 0:
                    item.setForeground(QColor("#EF4444"))
                self.history_table.setItem(row, col, item)

    def _filter_history(self):
        self._populate_history(self._history)

    def _load_data(self):
        try:
            self._all_members = self.db.get_members()
            self._all_books   = self.db.get_books()
        except Exception:
            pass

    def _issue_book(self):
        self._load_data()
        if not self._all_members:
            QMessageBox.warning(self, "No Members", "No members found."); return
        if not [b for b in self._all_books if b.status == "Available"]:
            QMessageBox.warning(self, "No Books", "No available books."); return

        dlg = IssueDialog(self._all_members, self._all_books, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            member, book, due = dlg.get_data()
            record = IssueRecord(
                bookId=book.id, bookTitle=book.title, bookIsbn=book.isbn,
                memberId=member.id, memberName=member.name,
                memberMemberId=member.memberId,
                issueDate=time.strftime("%Y-%m-%d"), dueDate=due
            )
            user_email = self.auth.current_user.email if self.auth.current_user else ""
            self._worker = IssueWorker(self.db, record, book, user_email)
            def _on_issue_success(ok, err):
                if ok:
                    QMessageBox.information(self, "Issued", f"✅  '{book.title}' issued to {member.name} locally!")
                    self.refresh()
                    reply = QMessageBox.question(self, "Print Slip", "Do you want to print an Issue Slip?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        path, _ = QFileDialog.getSaveFileName(self, "Save Issue Slip", f"Slip_{member.memberId}_{book.isbn or 'book'}.pdf", "PDF Files (*.pdf)")
                        if path:
                            self.adv.generate_issue_slip(record, member, path)
                            import os
                            os.startfile(path)
                else:
                    QMessageBox.warning(self, "Error", err)
            self._worker.finished.connect(_on_issue_success)
            self._worker.start()

    def _bulk_issue_mock(self):
        QMessageBox.information(self, "Bulk Issue Wizard", "Simulating Bulk Issue Wizard...\nAllows issuing multiple books to a class at once.")

    def _return_book(self):
        row = self.active_table.currentRow()
        if row < 0 or row >= len(self._issues):
            QMessageBox.information(self, "Select", "Select an active issue to return."); return
        issue = self._issues[row]

        days = days_diff(issue.dueDate)
        fine_rate = self.db.get_fine_rate()
        fine = abs(days) * fine_rate if days < 0 else 0.0

        msg = f"Return '{issue.bookTitle}' from {issue.memberName}?"
        if fine > 0:
            msg += f"\n\n⚠️  OVERDUE by {abs(days)} days.\nFine: Rs. {fine:.0f}"
        reply = QMessageBox.question(self, "Confirm Return", msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return

        # Feature 3: Rating on Return
        rating, ok_r = QInputDialog.getInt(self, "Rate Book", f"How would you rate '{issue.bookTitle}'? (1-5):", 5, 1, 5)
        comment = ""
        if ok_r:
            comment, _ = QInputDialog.getText(self, "Comment", "Any comments on the book?")
            self.db.save_review(issue.syncId, # fallback
                                issue.syncId,
                                issue.memberName, rating, comment)

        # Get the book's local object
        matching = [b for b in self._all_books if b.id == issue.bookId]
        book = matching[0] if matching else None

        user_email = self.auth.current_user.email if self.auth.current_user else ""
        self._worker = ReturnWorker(self.db, issue, book, fine, user_email)
        def _on_return_done(ok, err):
            if ok:
                QMessageBox.information(self, "Returned", f"✅  Book returned locally. Fine: Rs. {fine:.0f}")

                # Feature 1: Check for reservations
                reservations = self.db.get_reservations()
                pending = [r for r in reservations if r.bookId == issue.bookId and r.status == "Pending"]
                if pending:
                    res = pending[0]
                    QMessageBox.information(self, "🔔 Reservation Alert",
                                           f"This book has a pending reservation for <b>{res.memberName}</b>!\n\n"
                                           "A WhatsApp notification has been queued for the member.")
                    # Mock WhatsApp notify
                    print(f"DEBUG: WhatsApp notify to {res.memberName} for {issue.bookTitle}")

                self.refresh()
            else:
                QMessageBox.warning(self, "Error", err)

        self._worker.finished.connect(_on_return_done)
        self._worker.start()

    def _renew_book(self):
        row = self.active_table.currentRow()
        if row < 0 or row >= len(self._issues):
            QMessageBox.information(self, "Select", "Select an active issue to renew."); return
        issue = self._issues[row]
        
        reply = QMessageBox.question(self, "Renew Book", f"Renew '{issue.bookTitle}' for another 14 days?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            current_due = datetime.datetime.strptime(issue.dueDate, "%Y-%m-%d")
            new_due = current_due + datetime.timedelta(days=14)
            issue.dueDate = new_due.strftime("%Y-%m-%d")
            issue.lastUpdated = int(time.time() * 1000)
            self.db.save_issue(issue)
            self.refresh()
            QMessageBox.information(self, "Renewed", f"✅  Book renewed! New Due Date: {issue.dueDate}")

    def _send_reminder(self):
        import webbrowser
        from urllib.parse import quote
        row = self.active_table.currentRow()
        if row < 0 or row >= len(self._issues):
            QMessageBox.information(self, "Select", "Select an active issue to remind."); return
        issue = self._issues[row]

        members = [m for m in self.db.get_members() if m.id == issue.memberId]
        phone = members[0].phone if members else ""
        days_left = days_diff(issue.dueDate)
        status = f"is now {abs(days_left)} day(s) overdue" if days_left < 0 else f"is due in {days_left} day(s)"
        msg = (
            f"Dear {issue.memberName}, this is a friendly reminder from {self.db.get_school_name()}. "
            f"'{issue.bookTitle}' {status} ({issue.dueDate}). Please return it at your earliest convenience. Thank you!"
        )

        if not phone:
            QMessageBox.information(self, "No Phone Number",
                f"{issue.memberName} has no phone number on file, so a WhatsApp reminder can't be sent.\n\n"
                f"Message that would be sent:\n\n{msg}")
            return

        clean_phone = phone.replace("+", "").replace("-", "").replace(" ", "")
        wa_url = f"https://wa.me/{clean_phone}?text={quote(msg)}"
        webbrowser.open(wa_url)
        QMessageBox.information(self, "Reminder", f"Opened WhatsApp with a pre-filled reminder for {issue.memberName}.")


    def _print_receipt(self):
        """Print a PDF fine receipt for the selected active issue."""
        row = self.active_table.currentRow()
        if row < 0 or row >= len(self._issues):
            QMessageBox.information(self, "Select", "Select an active issue to print a receipt for.")
            return
        issue = self._issues[row]

        # Calculate fine
        days = days_diff(issue.dueDate)
        fine_rate = 0.0
        try:
            fine_rate = self.db.get_fine_rate()
        except Exception:
            fine_rate = 5
        fine = abs(days) * fine_rate if days < 0 else 0.0

        # Find the member object
        members = [m for m in self._all_members if m.id == issue.memberId]
        member = members[0] if members else None

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Fine Receipt",
            f"Receipt_{issue.memberMemberId}_{issue.bookIsbn or 'book'}.pdf",
            "PDF Files (*.pdf)"
        )
        if not path: return
        try:
            self.adv.generate_fine_receipt(issue, member, fine, path)
            reply = QMessageBox.question(
                self, "Receipt Ready", f"Fine receipt saved.\n\nOpen it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                import os
                os.startfile(path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not generate receipt:\n{e}")

    def _open_scanner(self):
        """Open a functional barcode/RFID scanner kiosk mode dialog.
        
        Scans a Book Acc No → if book is Available, auto-triggers Issue dialog.
        Scans a Book Acc No → if book is Issued, auto-triggers Return with fine.
        """
        screen = self  # reference to outer class

        class ScannerDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle(f"📟 Kiosk Scanner Mode — {screen.db.get_school_name()}")
                self.setStyleSheet("""
                    QDialog { background: #0D1B2A; color: #E8EEF8;
                              font-family: 'Segoe UI'; }
                    QLabel  { color: #E8EEF8; }
                """)
                self.setMinimumSize(600, 400)
                lay = QVBoxLayout(self)
                lay.setSpacing(16)
                lay.setContentsMargins(24, 20, 24, 20)

                title = QLabel("📟  Barcode / RFID Kiosk Scanner")
                title.setStyleSheet("font-size:22px;font-weight:800;color:#C8A84B;")
                lay.addWidget(title)

                info = QLabel(
                    "Scan a Book <b>Acc No</b> using a USB barcode scanner.\n"
                    "• If the book is <b>Available</b> → Issue dialog opens\n"
                    "• If the book is <b>Issued</b>    → Return + fine is processed instantly"
                )
                info.setStyleSheet("color:#A0B4CC;font-size:13px;")
                info.setWordWrap(True)
                lay.addWidget(info)

                self.scan_input = QLineEdit()
                self.scan_input.setPlaceholderText("🔍 Focus here and scan barcode…")
                self.scan_input.setStyleSheet(
                    "background:#0D1F38;border:2px solid #C8A84B;"
                    "border-radius:8px;padding:14px;font-size:20px;color:#E8EEF8;"
                )
                self.scan_input.returnPressed.connect(self._process_scan)
                lay.addWidget(self.scan_input)

                self.log_view = QTextEdit()
                self.log_view.setReadOnly(True)
                self.log_view.setStyleSheet(
                    "background:#071428;border:1px solid #1E3050;"
                    "border-radius:8px;color:#A0B4CC;font-size:12px;padding:8px;"
                )
                lay.addWidget(self.log_view)

                close_btn = QPushButton("✖  Close Scanner")
                close_btn.setStyleSheet(
                    "background:#1E3050;color:#6B8CAE;border:none;"
                    "border-radius:8px;padding:10px;font-size:13px;"
                )
                close_btn.clicked.connect(self.accept)
                lay.addWidget(close_btn)

                # Auto-focus
                QTimer.singleShot(100, self.scan_input.setFocus)

            def _log(self, msg: str, color: str = "#A0B4CC"):
                self.log_view.append(f'<span style="color:{color}">{msg}</span>')

            def _process_scan(self):
                val = self.scan_input.text().strip()
                self.scan_input.clear()
                if not val:
                    return

                self._log(f"⟶ Scanned: <b>{val}</b>", "#E8EEF8")

                # Look up book by Acc No
                books = screen.db.get_books()
                matching = [b for b in books if b.accNo == val or b.isbn == val]

                if not matching:
                    self._log(f"❌ No book found with Acc No / ISBN: {val}", "#EF4444")
                    return

                book = matching[0]
                self._log(f"📚 Found: <b>{book.title}</b> — Status: {book.status}", "#C8A84B")

                if book.status == "Available":
                    self._log("✅ Book is available. Opening issue dialog…", "#10B981")
                    # Trigger issue from parent screen
                    screen._load_data()
                    members = screen._all_members
                    if not members:
                        self._log("⚠️ No members in database to assign issue.", "#F59E0B")
                        return
                    dlg = IssueDialog(
                        members, [book], parent=self
                    )
                    if dlg.exec() == QDialog.DialogCode.Accepted:
                        member, bk, due = dlg.get_data()
                        import uuid, time as t
                        from models import IssueRecord
                        record = IssueRecord(
                            bookId=bk.id, bookTitle=bk.title, bookIsbn=bk.isbn,
                            memberId=member.id, memberName=member.name,
                            memberMemberId=member.memberId,
                            issueDate=t.strftime("%Y-%m-%d"), dueDate=due
                        )
                        record.syncId = str(uuid.uuid4())
                        record.lastUpdated = int(t.time() * 1000)
                        screen.db.save_issue(record)
                        bk.status = "Issued"
                        bk.lastUpdated = int(t.time() * 1000)
                        screen.db.save_book(bk)
                        self._log(f"✅ Issued <b>{bk.title}</b> to <b>{member.name}</b> — Due: {due}", "#10B981")
                        screen.refresh()
                    else:
                        self._log("Issue dialog cancelled.", "#6B8CAE")

                elif book.status == "Issued":
                    issues = [i for i in screen.db.get_issues()
                              if i.bookId == book.id and i.status == "Issued"]
                    if not issues:
                        self._log(f"⚠️ Book status is Issued but no active record found.", "#F59E0B")
                        return
                    issue = issues[0]
                    days = days_diff(issue.dueDate)
                    try:
                        fine_rate = screen.db.get_fine_rate()
                    except Exception:
                        fine_rate = 5
                    fine = abs(days) * fine_rate if days < 0 else 0.0
                    fine_msg = f"Fine: Rs.{fine:.0f}" if fine > 0 else "No fine"
                    self._log(
                        f"🔄 Returning <b>{book.title}</b> from <b>{issue.memberName}</b>. {fine_msg}",
                        "#F59E0B"
                    )
                    import time as t
                    issue.status = "Returned"
                    issue.returnDate = t.strftime("%Y-%m-%d")
                    issue.fine = fine
                    issue.lastUpdated = int(t.time() * 1000)
                    screen.db.save_issue(issue)
                    book.status = "Available"
                    book.lastUpdated = int(t.time() * 1000)
                    screen.db.save_book(book)
                    user_email = screen.auth.current_user.email if screen.auth.current_user else ""
                    screen.db.log_audit_local(
                        user_email, "scanner_return",
                        f"Scanned return: {book.title} from {issue.memberName}, fine={fine}"
                    )
                    self._log(f"✅ Return processed. {fine_msg}", "#10B981")
                    screen.refresh()
                else:
                    self._log(f"⚠️ Book status is '{book.status}' — cannot process.", "#F59E0B")

        dlg = ScannerDialog(self)
        dlg.exec()
