"""
ui/screens/inventory_screen.py — Koha-style Stocktaking & Inventory Module.
Allows scanning of book barcodes to verify physical shelf inventory against the database.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class InventoryScreen(QWidget):
    def __init__(self, db_helper):
        super().__init__()
        self.db = db_helper
        self._all_books = []
        self._found_ids = set()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header
        title = QLabel("📦  Inventory & Stocktaking")
        title.setStyleSheet("font-size:22px;font-weight:800;color:#E8EEF8;")
        layout.addWidget(title)

        info = QLabel(
            "Use this Koha-equivalent tool to perform shelf reading. "
            "Scan book barcodes (Acc No or ISBN) below to mark them as 'Found'.\n"
            "Books not scanned will remain in the 'Missing' list."
        )
        info.setStyleSheet("color:#A0B4CC;font-size:13px;")
        layout.addWidget(info)

        # Controls
        ctrl_lay = QHBoxLayout()
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("🔍 Scan Barcode / Acc No here...")
        self.scan_input.setStyleSheet(
            "background:#0D1F38;border:2px solid #C8A84B;border-radius:8px;"
            "padding:10px 14px;font-size:16px;color:#E8EEF8;"
        )
        self.scan_input.returnPressed.connect(self._process_scan)
        ctrl_lay.addWidget(self.scan_input, stretch=3)

        self.reset_btn = QPushButton("🔄 Reset Session")
        self.reset_btn.setStyleSheet(
            "background:#1E3050;color:#A0B4CC;border:1px solid #1E3050;"
            "border-radius:8px;padding:10px 16px;font-size:13px;font-weight:bold;"
        )
        self.reset_btn.clicked.connect(self.refresh)
        ctrl_lay.addWidget(self.reset_btn)
        
        self.export_btn = QPushButton("📤 Export Missing Report")
        self.export_btn.setStyleSheet(
            "background:rgba(220,38,38,0.1);color:#F87171;border:1px solid rgba(220,38,38,0.3);"
            "border-radius:8px;padding:10px 16px;font-size:13px;font-weight:bold;"
        )
        self.export_btn.clicked.connect(self._export_missing)
        ctrl_lay.addWidget(self.export_btn)
        
        layout.addLayout(ctrl_lay)

        # Progress
        self.progress_lbl = QLabel("Progress: 0 / 0 Found")
        self.progress_lbl.setStyleSheet("color:#6B8CAE;font-size:12px;font-weight:bold;")
        layout.addWidget(self.progress_lbl)
        
        self.progress = QProgressBar()
        self.progress.setStyleSheet(
            "QProgressBar { background: #0D1F38; border-radius: 4px; text-align: center; color: transparent; }"
            "QProgressBar::chunk { background: #10B981; border-radius: 4px; }"
        )
        self.progress.setFixedHeight(8)
        layout.addWidget(self.progress)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Acc No", "Title", "Author", "Status", "Inventory Status"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { background: #071428; color: #E8EEF8; gridline-color: #1E3050; border: none; font-size: 13px; }
            QHeaderView::section { background: #0D1B2A; color: #6B8CAE; font-weight: bold; font-size: 11px; padding: 8px; border-bottom: 1px solid #1E3050; }
            QTableWidget::item:alternate { background: rgba(13,28,55,0.6); }
        """)
        layout.addWidget(self.table)

    def refresh(self):
        self._all_books = self.db.get_books()
        self._found_ids.clear()
        self._update_table()
        self.scan_input.setFocus()

    def _process_scan(self):
        val = self.scan_input.text().strip()
        self.scan_input.clear()
        if not val: return

        # Find book
        matching = [b for b in self._all_books if b.accNo == val or b.isbn == val]
        if not matching:
            QMessageBox.warning(self, "Not Found", f"No book found with Acc No / ISBN: {val}")
            return
            
        book = matching[0]
        if book.id in self._found_ids:
            # Already scanned, ignore but give visual feedback maybe
            pass
        else:
            self._found_ids.add(book.id)
            self._update_table()

    def _update_table(self):
        total = len(self._all_books)
        found = len(self._found_ids)
        self.progress_lbl.setText(f"Progress: {found} / {total} Found ({(found/total*100) if total else 0:.1f}%)")
        self.progress.setMaximum(total)
        self.progress.setValue(found)

        self.table.setRowCount(total)
        
        # Sort so that "Missing" (not found) are at the top
        sorted_books = sorted(self._all_books, key=lambda b: (b.id in self._found_ids, b.title))
        
        for row, b in enumerate(sorted_books):
            is_found = b.id in self._found_ids
            status_text = "✅ Found" if is_found else "❌ Missing"
            
            vals = [b.accNo, b.title, b.author, b.status, status_text]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val or "")
                if col == 4:
                    item.setForeground(QColor("#10B981") if is_found else QColor("#EF4444"))
                self.table.setItem(row, col, item)

    def _export_missing(self):
        missing = [b for b in self._all_books if b.id not in self._found_ids]
        if not missing:
            QMessageBox.information(self, "Great Job!", "No books are missing! 100% Inventory match.")
            return
            
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export Missing Books", "Missing_Books_Report.csv", "CSV Files (*.csv)")
        if not path: return
        
        try:
            import csv
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Acc No", "ISBN", "Title", "Author", "System Status"])
                for b in missing:
                    writer.writerow([b.accNo, b.isbn, b.title, b.author, b.status])
            QMessageBox.information(self, "Success", f"Missing books report saved to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not export report:\n{e}")
