"""
ui/screens/transfer_screen.py
Inter-Library Loan / Book Transfer between colleges.
Allows a college to request books from another college's catalog
and track transfer status through the Directorate central server.
"""
import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFrame, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QComboBox, QMessageBox,
    QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import config


class TransferWorker(QThread):
    finished = pyqtSignal(list, list)  # outgoing, incoming

    def __init__(self):
        super().__init__()

    def run(self):
        outgoing, incoming = [], []
        try:
            url = f"{config.DIRECTORATE_API_URL}/api/transfers/college/{config.COLLEGE_ID}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                all_transfers = resp.json()
                outgoing = [t for t in all_transfers if t['from_college'] == config.COLLEGE_ID]
                incoming = [t for t in all_transfers if t['to_college'] == config.COLLEGE_ID]
        except Exception as e:
            print(f"Transfer fetch error: {e}")
        self.finished.emit(outgoing, incoming)


class RequestTransferDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Request Book Transfer")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.book_title_input = QLineEdit()
        self.book_title_input.setPlaceholderText("Enter book title to request")
        self.book_isbn_input = QLineEdit()
        self.book_isbn_input.setPlaceholderText("ISBN (optional)")
        self.to_college_input = QLineEdit()
        self.to_college_input.setPlaceholderText("Target college ID (e.g. gdc-peshawar)")

        form.addRow("Book Title:", self.book_title_input)
        form.addRow("ISBN:", self.book_isbn_input)
        form.addRow("Request from College:", self.to_college_input)
        layout.addLayout(form)

        btns = QHBoxLayout()
        ok_btn = QPushButton("📦 Send Request")
        ok_btn.setStyleSheet("background: #059669; color: white; border-radius: 8px; padding: 8px 20px; font-weight: bold;")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def get_data(self):
        return {
            "from_college": config.COLLEGE_ID,
            "to_college": self.to_college_input.text().strip(),
            "book_title": self.book_title_input.text().strip(),
            "book_isbn": self.book_isbn_input.text().strip() or None
        }


class TransferScreen(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("📦  Inter-Library Book Transfers")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #E8EEF8;")
        hdr.addWidget(title)
        hdr.addStretch()
        req_btn = QPushButton("+ Request Book")
        req_btn.setStyleSheet("background: #059669; color: white; border-radius: 8px; padding: 8px 18px; font-weight: bold;")
        req_btn.clicked.connect(self._request_transfer)
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("background: rgba(30,95,212,0.2); color: #6B8CAE; border: 1px solid #1E3050; border-radius: 8px; padding: 8px 14px;")
        self.refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(req_btn)
        hdr.addWidget(self.refresh_btn)
        layout.addLayout(hdr)

        sub = QLabel("Request books from other colleges via the Directorate network. Track transfer status below.")
        sub.setStyleSheet("color: #6B8CAE; font-size: 13px;")
        layout.addWidget(sub)

        # Tabs: Outgoing / Incoming
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #1E3050; border-radius: 8px; }
            QTabBar::tab { color: #6B8CAE; padding: 8px 18px; }
            QTabBar::tab:selected { color: #E6C96E; border-bottom: 2px solid #C8A84B; }
        """)

        self.out_table = self._make_table(["Book Title", "ISBN", "To College", "Status", "Requested"])
        self.in_table = self._make_table(["Book Title", "ISBN", "From College", "Status", "Requested", "Action"])

        tabs.addTab(self.out_table, "📤 Outgoing Requests")
        tabs.addTab(self.in_table, "📥 Incoming Requests")
        layout.addWidget(tabs)

    def _make_table(self, columns):
        tbl = QTableWidget(0, len(columns))
        tbl.setHorizontalHeaderLabels(columns)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet("""
            QTableWidget { background: #0D1F38; color: #E8EEF8; gridline-color: #1E3050; border: none; }
            QHeaderView::section { background: #071428; color: #6B8CAE; padding: 8px; border: none; }
            QTableWidget::item:alternate { background: rgba(30,48,80,0.3); }
        """)
        return tbl

    def _populate_table(self, table, rows, is_incoming=False):
        table.setRowCount(0)
        for row in rows:
            r = table.rowCount()
            table.insertRow(r)
            status = row.get('status', '')
            status_colors = {
                'requested': '#F59E0B', 'in-transit': '#3B82F6',
                'received': '#10B981', 'rejected': '#EF4444'
            }
            color = status_colors.get(status, '#6B8CAE')

            table.setItem(r, 0, QTableWidgetItem(row.get('book_title', '')))
            table.setItem(r, 1, QTableWidgetItem(row.get('book_isbn', '') or ''))
            if is_incoming:
                table.setItem(r, 2, QTableWidgetItem(row.get('from_college_name', row.get('from_college', ''))))
            else:
                table.setItem(r, 2, QTableWidgetItem(row.get('to_college_name', row.get('to_college', ''))))

            status_item = QTableWidgetItem(status.upper())
            status_item.setForeground(Qt.GlobalColor.white)
            table.setItem(r, 3, status_item)

            import time
            ts = row.get('requested_at', 0)
            ts_str = time.strftime("%Y-%m-%d", time.localtime(ts/1000)) if ts else ''
            table.setItem(r, 4, QTableWidgetItem(ts_str))

            if is_incoming and status == 'requested':
                approve_btn = QPushButton("✅ Accept")
                approve_btn.setStyleSheet("background:#059669;color:white;border-radius:4px;padding:3px 8px;font-size:11px;")
                transfer_id = row.get('id')
                approve_btn.clicked.connect(lambda _, tid=transfer_id: self._update_status(tid, 'in-transit'))
                table.setCellWidget(r, 5, approve_btn)

    def _request_transfer(self):
        if not config.DIRECTORATE_API_KEY:
            QMessageBox.warning(self, "Not Configured", "Please configure your Directorate API Key in Settings first.")
            return
        dlg = RequestTransferDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data['book_title'] or not data['to_college']:
                QMessageBox.warning(self, "Missing Fields", "Book title and target college are required.")
                return
            try:
                url = f"{config.DIRECTORATE_API_URL}/api/transfers"
                resp = requests.post(url, json=data, timeout=10)
                if resp.status_code == 200:
                    QMessageBox.information(self, "Success", "Transfer request sent successfully!")
                    self.refresh()
                else:
                    QMessageBox.warning(self, "Error", f"Server error: {resp.status_code}")
            except Exception as e:
                QMessageBox.critical(self, "Network Error", f"Could not reach directorate server:\n{e}")

    def _update_status(self, transfer_id, status):
        try:
            url = f"{config.DIRECTORATE_API_URL}/api/transfers/{transfer_id}/status"
            resp = requests.post(url, params={'status': status}, timeout=10)
            if resp.status_code == 200:
                self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh(self):
        self.refresh_btn.setEnabled(False)
        self.worker = TransferWorker()
        self.worker.finished.connect(self._on_transfers_loaded)
        self.worker.start()

    def _on_transfers_loaded(self, outgoing, incoming):
        self.refresh_btn.setEnabled(True)
        self._populate_table(self.out_table, outgoing, is_incoming=False)
        self._populate_table(self.in_table, incoming, is_incoming=True)
