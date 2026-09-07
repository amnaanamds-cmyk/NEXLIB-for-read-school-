import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QMessageBox, QDialog, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class SerialsScreen(QWidget):
    def __init__(self, db_helper):
        super().__init__()
        self.db = db_helper
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("📰  Serials & Periodicals Management")
        title.setStyleSheet("font-size:22px;font-weight:800;color:#E8EEF8;font-family:'Segoe UI';")
        hdr.addWidget(title)
        hdr.addStretch()

        self.btn_new_sub = QPushButton("➕ New Subscription")
        self.btn_new_sub.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1E5FD4,stop:1 #2872F0);"
            "color:white;border:none;border-radius:8px;padding:9px 18px;"
            "font-size:13px;font-weight:700;"
        )
        self.btn_new_sub.clicked.connect(self._add_serial)
        hdr.addWidget(self.btn_new_sub)
        layout.addLayout(hdr)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search Journals, Magazines...")
        self.search_input.setStyleSheet(
            "background:#0D1F38;border:1.5px solid #1E3050;border-radius:8px;"
            "padding:9px 14px;color:#E8EEF8;font-size:13px;"
        )
        self.search_input.textChanged.connect(self.refresh)
        
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(["All Frequencies", "Weekly", "Monthly", "Quarterly", "Annual"])
        self.freq_combo.setStyleSheet(self.search_input.styleSheet())
        self.freq_combo.currentTextChanged.connect(self.refresh)

        toolbar.addWidget(self.search_input, stretch=3)
        toolbar.addWidget(self.freq_combo, stretch=1)
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Title", "ISSN", "Frequency", "Publisher", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
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

        # Actions
        act_lay = QHBoxLayout()
        act_lay.addStretch()
        self.recv_btn = QPushButton("📥 Receive Latest Issue")
        self.recv_btn.setStyleSheet("background:#10B981;color:white;border:none;border-radius:8px;padding:8px 16px;font-weight:bold;")
        self.recv_btn.clicked.connect(self._receive_issue)
        act_lay.addWidget(self.recv_btn)
        layout.addLayout(act_lay)

        self.refresh()

    def refresh(self):
        serials = self.db.get_serials()
        
        # Filter
        q = self.search_input.text().lower()
        f = self.freq_combo.currentText()
        if q:
            serials = [s for s in serials if q in str(s.get("title")).lower() or q in str(s.get("issn")).lower()]
        if f != "All Frequencies":
            serials = [s for s in serials if s.get("frequency") == f]

        self.table.setRowCount(len(serials))
        for row, s in enumerate(serials):
            title = QTableWidgetItem(s.get("title", ""))
            issn = QTableWidgetItem(s.get("issn", ""))
            freq = QTableWidgetItem(s.get("frequency", ""))
            pub = QTableWidgetItem(s.get("publisher", ""))
            
            status = s.get("status", "Active")
            stat_item = QTableWidgetItem(status)
            if status == "Active": stat_item.setForeground(QColor("#10B981"))
            
            # Keep ID in data for Receiving
            title.setData(Qt.ItemDataRole.UserRole, s.get("id"))
            
            self.table.setItem(row, 0, title)
            self.table.setItem(row, 1, issn)
            self.table.setItem(row, 2, freq)
            self.table.setItem(row, 3, pub)
            self.table.setItem(row, 4, stat_item)

    def _add_serial(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Serial / Periodical")
        dlg.setFixedSize(400, 300)
        dlg.setStyleSheet("background:#0D1B2A; color:#E8EEF8; font-family:'Segoe UI';")
        
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        
        def _f(ph=""):
            w = QLineEdit(); w.setPlaceholderText(ph)
            w.setStyleSheet("background:#0D1F38; border:1.5px solid #1E3050; border-radius:6px; padding:6px; color:#E8EEF8;")
            return w
            
        title = _f("e.g. National Geographic")
        issn = _f("e.g. 0027-9358")
        freq = QComboBox()
        freq.addItems(["Weekly", "Monthly", "Quarterly", "Annual"])
        freq.setStyleSheet("background:#0D1F38; border:1.5px solid #1E3050; border-radius:6px; padding:6px; color:#E8EEF8;")
        pub = _f("e.g. NatGeo Society")
        
        form.addRow("Title *", title)
        form.addRow("ISSN", issn)
        form.addRow("Frequency", freq)
        form.addRow("Publisher", pub)
        lay.addLayout(form)
        
        btn = QPushButton("Save Subscription")
        btn.setStyleSheet("background:#2872F0; color:white; border:none; border-radius:6px; padding:8px; font-weight:bold;")
        
        def _save():
            if not title.text().strip():
                QMessageBox.warning(dlg, "Error", "Title is required")
                return
            self.db.save_serial(title.text().strip(), issn.text().strip(), freq.currentText(), pub.text().strip(), "Active")
            dlg.accept()
            self.refresh()
            
        btn.clicked.connect(_save)
        lay.addWidget(btn)
        dlg.exec()
        
    def _receive_issue(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select", "Please select a serial to receive an issue for.")
            return
            
        title = self.table.item(row, 0).text()
        
        # Log this in the audit log
        self.db.log_audit_local("system", "serial_received", f"Received latest issue for: {title}")
        QMessageBox.information(self, "Received", f"Successfully logged the receipt of the latest issue for:\n\n{title}")
