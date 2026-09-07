"""
ui/screens/opac_screen.py — OPAC (Online Public Access Catalog) Monitor.
A public-facing search kiosk for students with reservation capability,
fully offline (local SQLite).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox,
    QInputDialog, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class ReserveWorker(QThread):
    finished = pyqtSignal(bool, str)
    def __init__(self, db, book, member_id, member_name):
        super().__init__()
        self.db = db
        self.book = book
        self.member_id = member_id
        self.member_name = member_name

    def run(self):
        try:
            import time
            import uuid
            from models import Reservation
            res = Reservation(
                syncId=str(uuid.uuid4()),
                bookId=self.book.id, bookTitle=self.book.title,
                memberId=self.member_id, memberName=self.member_name,
                reservedDate=time.strftime("%Y-%m-%d"),
                status="Pending",
                lastUpdated=int(time.time() * 1000)
            )
            self.db.save_reservation(res)
            self.db.log_audit_local("opac_kiosk", "book_reservation", f"Reserved: {self.book.title} for {self.member_name}")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class OpacScreen(QWidget):
    def __init__(self, db_helper):
        super().__init__()
        self.db = db_helper
        self._books = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Header
        hdr = QHBoxLayout()
        icon = QLabel("🔍")
        icon.setStyleSheet("font-size: 32px;")
        hdr.addWidget(icon)
        
        titles = QVBoxLayout()
        title = QLabel("Online Public Access Catalog")
        title.setStyleSheet("font-size: 26px; font-weight: 900; color: #E8EEF8; font-family: 'Segoe UI';")
        sub = QLabel(f"Search the {self.db.get_school_name()} catalog and reserve books.")
        sub.setStyleSheet("color: #6B8CAE; font-size: 14px;")
        titles.addWidget(title)
        titles.addWidget(sub)
        hdr.addLayout(titles)
        hdr.addStretch()
        layout.addLayout(hdr)

        # Search Bar
        search_frame = QFrame()
        search_frame.setStyleSheet(
            "background: #0D1F38; border: 1.5px solid #1E5FD4; border-radius: 12px;"
        )
        s_lay = QHBoxLayout(search_frame)
        s_lay.setContentsMargins(16, 12, 16, 12)
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by Title, Author, or Category...")
        self.search.setStyleSheet("background: transparent; border: none; color: white; font-size: 16px;")
        self.search.textChanged.connect(self._filter)
        s_lay.addWidget(self.search)
        
        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All Categories")
        self.cat_filter.setStyleSheet(
            "background: #1E3050; border: none; border-radius: 6px; padding: 6px 12px; color: #A0B4CC; font-size: 13px;"
        )
        self.cat_filter.currentTextChanged.connect(self._filter)
        s_lay.addWidget(self.cat_filter)
        
        self.ai_btn = QPushButton("💡 Suggest Books")
        self.ai_btn.setStyleSheet("background: #C8A84B; color: #0D1F38; border-radius: 6px; padding: 6px 12px; font-weight: bold;")
        self.ai_btn.clicked.connect(self._ai_recommend)
        s_lay.addWidget(self.ai_btn)

        self.kiosk_btn = QPushButton("🛒 Self-Checkout")
        self.kiosk_btn.setStyleSheet("background: #10B981; color: white; border-radius: 6px; padding: 6px 12px; font-weight: bold;")
        self.kiosk_btn.clicked.connect(self._open_kiosk)
        s_lay.addWidget(self.kiosk_btn)

        layout.addWidget(search_frame)

        # Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Title", "Author", "Category", "Status", "Digital", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { background: #071428; color: #E8EEF8; gridline-color: #1E3050; border: none; font-size: 14px; }
            QTableWidget::item { padding: 12px 8px; }
            QHeaderView::section { background: #0D1B2A; color: #A0B4CC; font-weight: 700; font-size: 12px; padding: 10px; border-bottom: 2px solid #1E5FD4; }
            QTableWidget::item:alternate { background: rgba(13,28,55,0.6); }
        """)
        layout.addWidget(self.table)
        
        # Reserve button overlay (simulated by action column)
        self.count_lbl = QLabel("Ready")
        self.count_lbl.setStyleSheet("color: #6B8CAE;")
        layout.addWidget(self.count_lbl)

    def refresh(self):
        self._books = self.db.get_books()
        
        # Update categories
        cats = sorted(list(set(b.category for b in self._books if b.category)))
        curr = self.cat_filter.currentText()
        self.cat_filter.clear()
        self.cat_filter.addItem("All Categories")
        self.cat_filter.addItems(cats)
        if curr in cats:
            self.cat_filter.setCurrentText(curr)
            
        self._filter()

    def _filter(self):
        q = self.search.text().lower()
        cat = self.cat_filter.currentText()
        
        filtered = [b for b in self._books
                    if (not q or any(q in (f or "").lower() for f in [b.title, b.author, b.category]))
                    and (cat == "All Categories" or b.category == cat)]
                    
        self.table.setRowCount(len(filtered))
        for row, b in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(b.title))
            self.table.setItem(row, 1, QTableWidgetItem(b.author))
            self.table.setItem(row, 2, QTableWidgetItem(b.category))
            
            st_item = QTableWidgetItem(b.status)
            if b.status == "Available": st_item.setForeground(QColor("#10B981"))
            else: st_item.setForeground(QColor("#F59E0B"))
            self.table.setItem(row, 3, st_item)
            
            dig_item = QTableWidgetItem("📱 Available" if b.isDigital else "")
            dig_item.setForeground(QColor("#3B82F6"))
            self.table.setItem(row, 4, dig_item)
            
            btn = QPushButton("Reserve")
            if b.status == "Available":
                btn.setStyleSheet("background: #1E5FD4; color: white; border-radius: 6px; padding: 6px;")
                btn.clicked.connect(lambda _, bk=b: self._reserve(bk))
            else:
                btn.setStyleSheet("background: #374151; color: #9CA3AF; border-radius: 6px; padding: 6px;")
                btn.setEnabled(False)
            self.table.setCellWidget(row, 5, btn)
            
        self.count_lbl.setText(f"Found {len(filtered)} books")

    def _reserve(self, book):
        pin, ok = QInputDialog.getText(self, "OPAC Reservation", 
                                     f"Reserve '{book.title}'\n\nEnter your 4-digit Member PIN:")
        if not ok or not pin:
            return
            
        # Verify PIN
        try:
            members = self.db.get_members()
            matching = [m for m in members if m.pin == pin and m.pin != ""]
            if not matching:
                QMessageBox.warning(self, "Error", "Invalid PIN. Please ask the librarian if you forgot it.")
                return
            
            member = matching[0]
            
            # Start reservation
            self.worker = ReserveWorker(self.db, book, member.id, member.name)
            self.worker.finished.connect(lambda ok, err: (
                (QMessageBox.information(self, "Success", f"Book reserved for {member.name}!") or self.refresh()) if ok
                else QMessageBox.warning(self, "Error", f"Failed: {err}")
            ))
            self.worker.start()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _ai_recommend(self):
        """Suggest books using local catalog data only — no network required.
        Matches the typed topic against title/author/category, then ranks by
        how often each book has been borrowed."""
        query = self.search.text().strip().lower()
        if not query:
            QMessageBox.information(self, "Suggest Books", "Please type a topic or interest in the search bar first (e.g. 'Science Fiction' or 'Data Science').")
            return

        available = [b for b in self.db.get_books() if b.status == "Available"]
        matches = [b for b in available
                   if query in (b.title or "").lower()
                   or query in (b.author or "").lower()
                   or query in (b.category or "").lower()]

        if not matches:
            cats = sorted({b.category for b in available if b.category})
            hint = f"\n\nTry one of these categories: {', '.join(cats[:8])}" if cats else ""
            QMessageBox.information(self, "Suggest Books", f"No available books matched '{query}'.{hint}")
            return

        issues = self.db.get_issues()
        borrow_counts = {}
        for i in issues:
            borrow_counts[i.bookTitle] = borrow_counts.get(i.bookTitle, 0) + 1
        matches.sort(key=lambda b: borrow_counts.get(b.title, 0), reverse=True)

        lines = "".join(
            f"<li><b>{b.title}</b> by {b.author or 'Unknown'} <i>({b.category or 'Uncategorized'})</i></li>"
            for b in matches[:8]
        )
        QMessageBox.information(
            self, "💡 Suggested Books",
            f"<b>Available books matching '{query}':</b><ul>{lines}</ul>"
        )

    # ── Enterprise: Patron Self-Checkout Kiosk ───────────────────────────────
    def _open_kiosk(self):
        """Kiosk Mode for self-service book checkout by patrons."""
        from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QVBoxLayout, QPushButton, QLabel, QMessageBox
        import datetime, time, uuid
        from models import IssueRecord

        dlg = QDialog(self)
        dlg.setWindowTitle("🛒 Patron Self-Checkout Kiosk")
        dlg.setFixedSize(450, 400)
        dlg.setStyleSheet("QDialog {background:#0D1B2A; color:#E8EEF8;} QLabel {font-size:14px; font-weight:bold; color:#E8EEF8;}")

        lay = QVBoxLayout(dlg)
        
        hdr = QLabel("Self-Checkout Terminal")
        hdr.setStyleSheet("font-size: 22px; font-weight: 900; color: #10B981; margin-bottom:10px;")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hdr)
        
        desc = QLabel("Please scan your Library Card, enter your PIN, and scan the Book barcode to issue it.")
        desc.setStyleSheet("font-size: 13px; color: #A0B4CC; font-weight:normal;")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(16)
        
        def _field(ph, is_pw=False):
            f = QLineEdit()
            f.setPlaceholderText(ph)
            f.setStyleSheet("background:#0D1F38; border:2px solid #1E3050; border-radius:8px; padding:10px; color:white; font-size:16px;")
            if is_pw:
                f.setEchoMode(QLineEdit.EchoMode.Password)
            return f
            
        mid_field = _field("Scan or Type Member ID")
        pin_field = _field("4-Digit PIN", True)
        book_field = _field("Scan or Type Book Acc No / ISBN")
        
        form.addRow("Member ID:", mid_field)
        form.addRow("Secure PIN:", pin_field)
        form.addRow("Book Code:", book_field)
        
        lay.addLayout(form)
        lay.addStretch()
        
        checkout_btn = QPushButton("✅  Complete Checkout")
        checkout_btn.setStyleSheet("background:#10B981; color:white; border:none; border-radius:8px; padding:15px; font-size:18px; font-weight:900;")
        
        def _process():
            mid = mid_field.text().strip()
            pin = pin_field.text().strip()
            code = book_field.text().strip()
            
            if not mid or not pin or not code:
                QMessageBox.warning(dlg, "Missing Information", "Please fill all fields.")
                return
                
            members = self.db.get_members()
            member = next((m for m in members if m.memberId == mid and m.pin == pin), None)
            
            if not member:
                QMessageBox.warning(dlg, "Access Denied", "Invalid Member ID or PIN.")
                return
                
            books = self.db.get_books()
            book = next((b for b in books if (b.accNo == code or b.isbn == code)), None)
            
            if not book:
                QMessageBox.warning(dlg, "Not Found", "Book not found in database.")
                return
                
            if book.status != "Available":
                QMessageBox.warning(dlg, "Unavailable", f"This book is currently '{book.status}' and cannot be issued.")
                return
                
            # Process Issue
            try:
                due_date = (datetime.date.today() + datetime.timedelta(days=14)).strftime("%Y-%m-%d")
                record = IssueRecord(
                    bookId=book.id, bookTitle=book.title, bookIsbn=book.isbn,
                    memberId=member.id, memberName=member.name, memberMemberId=member.memberId,
                    issueDate=time.strftime("%Y-%m-%d"), dueDate=due_date
                )
                record.syncId = str(uuid.uuid4())
                record.lastUpdated = int(time.time() * 1000)
                
                self.db.save_issue(record)
                book.status = "Issued"
                book.lastUpdated = int(time.time() * 1000)
                self.db.save_book(book)
                
                member.booksIssued += 1
                member.lastUpdated = int(time.time() * 1000)
                self.db.save_member(member)
                
                self.db.log_audit_local("kiosk", "self_checkout", f"Self-checkout: {book.title} by {member.name}")
                
                QMessageBox.information(dlg, "Success", f"Book successfully issued to {member.name}!\n\nDue Date: {due_date}")
                dlg.accept()
                self.refresh()
            except Exception as e:
                QMessageBox.critical(dlg, "Error", f"Transaction failed: {e}")
                
        checkout_btn.clicked.connect(_process)
        lay.addWidget(checkout_btn)
        
        dlg.exec()
