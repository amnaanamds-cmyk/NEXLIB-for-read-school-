"""
ui/screens/ill_screen.py — Inter-Library Loan (ILL) Module.
Create, track, and manage ILL requests to partner institutions.
Stores all requests in the local SQLite database.
"""
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QMessageBox, QDialog, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


PARTNER_INSTITUTIONS = [
    "Punjab University, Lahore",
    "Quaid-i-Azam University, Islamabad",
    "University of Karachi",
    "LUMS, Lahore",
    "NUST, Islamabad",
    "IBA, Karachi",
    "GC University, Lahore",
    "Peshawar University",
    "Bahauddin Zakariya University",
    "Other / Custom",
]

STATUS_OPTIONS = ["Requested", "Approved", "In Transit", "Received", "Returned to Lender", "Cancelled"]


class ILLScreen(QWidget):
    def __init__(self, db_helper=None):
        super().__init__()
        self.db = db_helper
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("🌍  Inter-Library Loan (ILL) Network")
        title.setStyleSheet("font-size:22px;font-weight:800;color:#E8EEF8;font-family:'Segoe UI';")
        hdr.addWidget(title)
        hdr.addStretch()

        new_btn = QPushButton("➕ New ILL Request")
        new_btn.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1E5FD4,stop:1 #2872F0);"
            "color:white;border:none;border-radius:8px;padding:9px 18px;"
            "font-size:13px;font-weight:700;"
        )
        new_btn.clicked.connect(self._new_request)
        hdr.addWidget(new_btn)
        layout.addLayout(hdr)

        sub = QLabel("Request and share resources with partner universities across Pakistan.")
        sub.setStyleSheet("color:#6B8CAE;font-size:13px;")
        layout.addWidget(sub)

        # Filter bar
        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search by title, author, institution…")
        self.search_input.setStyleSheet(
            "background:#0D1F38;border:1.5px solid #1E3050;border-radius:8px;"
            "padding:9px 14px;color:#E8EEF8;font-size:13px;"
        )
        self.search_input.textChanged.connect(self.refresh)

        self.status_combo = QComboBox()
        self.status_combo.addItem("All Statuses")
        self.status_combo.addItems(STATUS_OPTIONS)
        self.status_combo.setStyleSheet(self.search_input.styleSheet())
        self.status_combo.currentTextChanged.connect(self.refresh)

        filter_row.addWidget(self.search_input, stretch=3)
        filter_row.addWidget(self.status_combo, stretch=1)
        layout.addLayout(filter_row)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Book Title", "Author", "Target Institution", "Request Date", "Status", "ID"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setColumnHidden(5, True)  # hide ID column
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #071428; color: #E8EEF8;
                gridline-color: #1E3050; border: none;
                font-size: 13px; font-family: 'Segoe UI';
            }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected { background: rgba(30,95,212,0.3); }
            QHeaderView::section {
                background: #0D1B2A; color: #6B8CAE;
                font-weight: 700; font-size: 11px; padding: 8px;
                border-bottom: 1px solid #1E3050;
            }
            QTableWidget::item:alternate { background: rgba(13,28,55,0.6); }
        """)
        layout.addWidget(self.table)

        # Action bar
        act = QHBoxLayout()
        act.addStretch()

        self.update_btn = QPushButton("📝 Update Status")
        self.update_btn.setStyleSheet(
            "background:#F59E0B;color:#0D1B2A;border:none;border-radius:8px;"
            "padding:8px 16px;font-weight:bold;"
        )
        self.update_btn.clicked.connect(self._update_status)
        act.addWidget(self.update_btn)

        self.cancel_btn = QPushButton("❌ Cancel Request")
        self.cancel_btn.setStyleSheet(
            "background:rgba(239,68,68,0.15);color:#EF4444;border:1px solid rgba(239,68,68,0.3);"
            "border-radius:8px;padding:8px 16px;font-weight:bold;"
        )
        self.cancel_btn.clicked.connect(self._cancel_request)
        act.addWidget(self.cancel_btn)
        layout.addLayout(act)

        self.refresh()

    def refresh(self):
        if not self.db:
            return
        requests = self.db.get_ill_requests()

        # Filter
        q = self.search_input.text().lower()
        s = self.status_combo.currentText()
        if q:
            requests = [r for r in requests
                        if q in str(r.get("bookTitle", "")).lower()
                        or q in str(r.get("author", "")).lower()
                        or q in str(r.get("targetInstitution", "")).lower()]
        if s != "All Statuses":
            requests = [r for r in requests if r.get("status") == s]

        self.table.setRowCount(len(requests))
        for row, r in enumerate(requests):
            self.table.setItem(row, 0, QTableWidgetItem(r.get("bookTitle", "")))
            self.table.setItem(row, 1, QTableWidgetItem(r.get("author", "")))
            self.table.setItem(row, 2, QTableWidgetItem(r.get("targetInstitution", "")))

            ts = r.get("requestDate", 0)
            try:
                dt_str = datetime.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            except Exception:
                dt_str = "—"
            self.table.setItem(row, 3, QTableWidgetItem(dt_str))

            status = r.get("status", "Requested")
            st_item = QTableWidgetItem(status)
            color_map = {
                "Requested": "#F59E0B", "Approved": "#3B82F6",
                "In Transit": "#8B5CF6", "Received": "#10B981",
                "Returned to Lender": "#6B8CAE", "Cancelled": "#EF4444",
            }
            st_item.setForeground(QColor(color_map.get(status, "#A0B4CC")))
            self.table.setItem(row, 4, st_item)

            id_item = QTableWidgetItem(str(r.get("id", "")))
            self.table.setItem(row, 5, id_item)

    def _new_request(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("New Inter-Library Loan Request")
        dlg.setFixedSize(460, 340)
        dlg.setStyleSheet("background:#0D1B2A; color:#E8EEF8; font-family:'Segoe UI';")

        lay = QVBoxLayout(dlg)
        form = QFormLayout()

        def _f(ph=""):
            w = QLineEdit()
            w.setPlaceholderText(ph)
            w.setStyleSheet("background:#0D1F38; border:1.5px solid #1E3050; border-radius:6px; padding:6px; color:#E8EEF8;")
            return w

        book_title = _f("Title of the book you need")
        author = _f("Author name (optional)")
        member_id = _f("Member ID of the requester")
        institution = QComboBox()
        institution.addItems(PARTNER_INSTITUTIONS)
        institution.setStyleSheet("background:#0D1F38; border:1.5px solid #1E3050; border-radius:6px; padding:6px; color:#E8EEF8;")

        form.addRow("Book Title *", book_title)
        form.addRow("Author", author)
        form.addRow("Requester ID", member_id)
        form.addRow("Lending Library", institution)
        lay.addLayout(form)

        btn = QPushButton("📨 Submit ILL Request")
        btn.setStyleSheet("background:#2872F0;color:white;border:none;border-radius:8px;padding:10px;font-weight:bold;")

        def _submit():
            if not book_title.text().strip():
                QMessageBox.warning(dlg, "Required", "Book title is required.")
                return
            mid = 0
            try:
                mid = int(member_id.text().strip())
            except ValueError:
                pass
            self.db.save_ill_request(
                book_title.text().strip(),
                author.text().strip(),
                mid,
                institution.currentText()
            )
            self.db.log_audit_local("system", "ill_request",
                                    f"ILL requested: {book_title.text().strip()} from {institution.currentText()}")
            QMessageBox.information(dlg, "Submitted",
                                    f"ILL request submitted to {institution.currentText()}.\n\n"
                                    "The partner library will be contacted via ISO 18626 protocol.")
            dlg.accept()
            self.refresh()

        btn.clicked.connect(_submit)
        lay.addWidget(btn)
        dlg.exec()

    def _update_status(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select", "Please select a request to update.")
            return
        ill_id = int(self.table.item(row, 5).text())
        current = self.table.item(row, 4).text()

        new_status, ok = QComboBox(), False
        # Use QInputDialog for simplicity
        from PyQt6.QtWidgets import QInputDialog
        new_status, ok = QInputDialog.getItem(
            self, "Update ILL Status", f"Current: {current}\nSelect new status:",
            STATUS_OPTIONS, STATUS_OPTIONS.index(current) if current in STATUS_OPTIONS else 0, False
        )
        if ok and new_status != current:
            self.db.update_ill_status(ill_id, new_status)
            self.db.log_audit_local("system", "ill_status_update",
                                    f"ILL #{ill_id} status → {new_status}")
            self.refresh()

    def _cancel_request(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select", "Please select a request to cancel.")
            return
        ill_id = int(self.table.item(row, 5).text())
        title = self.table.item(row, 0).text()
        reply = QMessageBox.question(
            self, "Cancel ILL", f"Cancel request for '{title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.update_ill_status(ill_id, "Cancelled")
            self.db.log_audit_local("system", "ill_cancelled", f"ILL #{ill_id} cancelled")
            self.refresh()
