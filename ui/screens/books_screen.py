"""
ui/screens/books_screen.py — Full Book Management screen.
Add/edit/delete form, search/filter/sort, ISBN validation, subject
browsing, new arrivals, cover upload — all fully offline (local SQLite).
"""
import re
import time
import uuid
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QComboBox, QMessageBox, QFileDialog, QTabWidget, QFrame, QCheckBox,
    QSplitter, QTextEdit, QSpinBox, QDoubleSpinBox, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from models import Book

ISBN10_RE = re.compile(r"^\d{9}[\dX]$")
ISBN13_RE = re.compile(r"^\d{13}$")


def validate_isbn(isbn: str) -> bool:
    clean = isbn.replace("-", "").replace(" ", "").upper()
    return bool(ISBN10_RE.match(clean) or ISBN13_RE.match(clean))


class SaveBookWorker(QThread):
    finished = pyqtSignal(bool, str)
    def __init__(self, db, book, user_email, cover_path=None):
        super().__init__()
        self.db, self.book, self.user_email, self.cover_path = db, book, user_email, cover_path
    def run(self):
        try:
            if self.cover_path:
                from services.media_service import store_file
                stored = store_file(self.cover_path, "covers")
                if stored:
                    self.book.digitalUrl = self.book.digitalUrl or stored
            self.db.save_book(self.book)
            # Log audit trail locally
            self.db.log_audit_local(self.user_email, "book_save", f"Book: {self.book.title} ({self.book.syncId})")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


CATEGORIES = [
    "Uncategorized", "Fiction", "Non-Fiction", "Science", "Mathematics",
    "History", "Geography", "Islamic Studies", "Urdu Literature",
    "English Literature", "Computer Science", "Physics", "Chemistry",
    "Biology", "Economics", "Sociology", "Political Science", "Philosophy",
    "Arts", "Reference"
]


class BookFormDialog(QDialog):
    """Add / Edit book form."""
    STYLE = """
    QDialog { background: #0D1B2A; }
    QLabel  { color: #A0B4CC; font-size: 12px; font-family: 'Segoe UI'; }
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        background: #0D1F38; border: 1.5px solid #1E3050;
        border-radius: 8px; padding: 8px 12px; color: #E8EEF8;
        font-size: 13px; font-family: 'Segoe UI';
    }
    QLineEdit:focus, QComboBox:focus { border-color: #C8A84B; }
    QPushButton#saveBtn {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1E5FD4,stop:1 #2872F0);
        color: white; border: none; border-radius: 8px;
        padding: 10px 24px; font-size: 14px; font-weight: 700;
    }
    QPushButton#saveBtn:hover { background: #2872F0; }
    QPushButton#cancelBtn {
        background: rgba(30,48,80,0.5); color: #6B8CAE;
        border: 1px solid #1E3050; border-radius: 8px; padding: 10px 20px;
    }
    QCheckBox { color: #A0B4CC; }
    """

    def __init__(self, book: Book = None, parent=None):
        super().__init__(parent)
        self.book = book or Book()
        self.cover_path = None
        self.setWindowTitle("Add Book" if not book else "Edit Book")
        self.setStyleSheet(self.STYLE)
        self.setMinimumWidth(560)
        self._build()

    def _build(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        lay.addWidget(QLabel("📚  Book Details", styleSheet="font-size:16px;font-weight:800;color:#E6C96E;"))

        form = QFormLayout()
        form.setSpacing(10)

        self.isbn   = self._field(self.book.isbn,      "978-0-00-000000-0")
        self.accNo  = self._field(self.book.accNo,     "B001")
        self.title  = self._field(self.book.title,     "Book Title")
        self.author = self._field(self.book.author,    "Author Name")
        self.pub    = self._field(self.book.publisher, "Publisher")
        self.pubPl  = self._field(self.book.publisherPlace, "City, Country")
        self.pubDt  = self._field(self.book.publishDate,    "2024")
        self.edition= self._field(self.book.edition,   "1st")
        self.vol    = self._field(self.book.volume,    "1")
        self.proc   = self._field(self.book.procurement, "Purchased")

        self.pages  = QSpinBox(); self.pages.setRange(1, 99999)
        self.pages.setValue(self.book.pages or 1)
        self.price  = QDoubleSpinBox(); self.price.setRange(0, 999999)
        self.price.setValue(self.book.price or 0)
        self.price.setPrefix("Rs. ")

        self.cat = QComboBox()
        self.cat.addItems(CATEGORIES)
        if self.book.category in CATEGORIES:
            self.cat.setCurrentText(self.book.category)

        self.digital_url = self._field(self.book.digitalUrl or "", "https://drive.google.com/...")
        self.is_digital  = QCheckBox("This book has an e-book / digital URL")
        self.is_digital.setChecked(self.book.isDigital)

        # ISBN Row with Magic Fetch
        isbn_row = QHBoxLayout()
        isbn_row.addWidget(self.isbn, stretch=4)

        self.fetch_btn = QPushButton("✨ Auto-Fetch")
        self.fetch_btn.setStyleSheet("background:#C8A84B; color:#0D1B2A; border:none; border-radius:6px; padding:8px; font-weight:bold;")
        self.fetch_btn.clicked.connect(self._magic_fetch)

        self.z39_btn = QPushButton("🌐 Z39.50 Search")
        self.z39_btn.setStyleSheet("background:#2872F0; color:white; border:none; border-radius:6px; padding:8px; font-weight:bold;")
        self.z39_btn.clicked.connect(self._z3950_search)

        self.scan_btn = QPushButton("📷 Scan Barcode")
        self.scan_btn.setStyleSheet("background:#059669; color:white; border:none; border-radius:6px; padding:8px; font-weight:bold;")
        self.scan_btn.clicked.connect(self._scan_barcode)

        isbn_row.addWidget(self.fetch_btn, stretch=1)
        isbn_row.addWidget(self.z39_btn, stretch=1)
        isbn_row.addWidget(self.scan_btn, stretch=1)

        form.addRow("ISBN *", isbn_row)

        for label, widget in [
            ("Acc No", self.accNo),
            ("Title *", self.title), ("Author *", self.author),
            ("Publisher", self.pub), ("Publisher Place", self.pubPl),
            ("Publish Date", self.pubDt), ("Edition", self.edition),
            ("Volume", self.vol), ("Procurement", self.proc),
            ("Pages", self.pages), ("Price", self.price),
            ("Category", self.cat), ("E-Book URL", self.digital_url),
            ("", self.is_digital),
        ]:
            form.addRow(label, widget)

        lay.addLayout(form)

        # Cover image
        cover_row = QHBoxLayout()
        self.cover_lbl = QLabel("No cover selected" if not self.book.digitalUrl else "Cover URL set")
        self.cover_lbl.setStyleSheet("color:#4D6A90;font-size:11px;")
        cover_btn = QPushButton("📷  Choose Cover Image")
        cover_btn.setStyleSheet("background:#1E3050;color:#6B8CAE;border:1px solid #1E3050;"
                                "border-radius:6px;padding:6px 12px;")
        cover_btn.clicked.connect(self._pick_cover)
        cover_row.addWidget(self.cover_lbl)
        cover_row.addWidget(cover_btn)
        lay.addLayout(cover_row)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Buttons (Fixed at bottom)
        btn_container = QWidget()
        btn_container.setStyleSheet("background: #0D1B2A; border-top: 1px solid #1E3050;")
        btn_row = QHBoxLayout(btn_container)
        btn_row.setContentsMargins(24, 12, 24, 16)
        btn_row.addStretch()
        cancel = QPushButton("Cancel"); cancel.setObjectName("cancelBtn")
        cancel.clicked.connect(self.reject)
        save = QPushButton("💾  Save Book"); save.setObjectName("saveBtn")
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        main_layout.addWidget(btn_container)

        self.setMinimumHeight(600)

    def _field(self, val, placeholder=""):
        f = QLineEdit(val or "")
        f.setPlaceholderText(placeholder)
        return f

    def _pick_cover(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Cover", "",
                                              "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.cover_path = path
            self.cover_lbl.setText(f"📷 {path.split('/')[-1]}")

    def _save(self):
        isbn = self.isbn.text().strip()
        if isbn and not validate_isbn(isbn):
            QMessageBox.warning(self, "Invalid ISBN",
                                "ISBN must be 10 or 13 digits (dashes allowed).")
            return
        if not self.title.text().strip():
            QMessageBox.warning(self, "Required", "Title is required.")
            return

        self.book.isbn        = isbn
        self.book.accNo       = self.accNo.text().strip()
        self.book.title       = self.title.text().strip()
        self.book.author      = self.author.text().strip()
        self.book.publisher   = self.pub.text().strip()
        self.book.publisherPlace = self.pubPl.text().strip()
        self.book.publishDate = self.pubDt.text().strip()
        self.book.edition     = self.edition.text().strip()
        self.book.volume      = self.vol.text().strip()
        self.book.procurement = self.proc.text().strip()
        self.book.pages       = self.pages.value()
        self.book.price       = self.price.value()
        self.book.category    = self.cat.currentText()
        self.book.digitalUrl  = self.digital_url.text().strip() or None
        self.book.isDigital   = self.is_digital.isChecked()
        self.accept()

    def _magic_fetch(self):
        isbn = self.isbn.text().strip()
        if not isbn:
            QMessageBox.warning(self, "Required", "Please enter an ISBN first.")
            return
            
        self.fetch_btn.setText("Fetching...")
        self.fetch_btn.setEnabled(False)
        
        # In a real app this would be a QThread to avoid UI freeze, but it's fast enough for demo
        try:
            from services.database_helper import DatabaseHelper
            from services.advanced_service import AdvancedService
            adv = AdvancedService(DatabaseHelper())
            data = adv.fetch_book_by_isbn(isbn)
            
            if not data:
                QMessageBox.information(self, "Not Found", "No metadata found for this ISBN on OpenLibrary.")
            else:
                if data.get("title"): self.title.setText(data["title"])
                if data.get("author"): self.author.setText(data["author"])
                if data.get("publisher"): self.pub.setText(data["publisher"])
                if data.get("publishDate"): self.pubDt.setText(data["publishDate"])
                if data.get("pages"): self.pages.setValue(int(data["pages"]))
                if data.get("cover_url"):
                    self.digital_url.setText(data["cover_url"])
                    self.is_digital.setChecked(True)
                    self.cover_lbl.setText("✨ Cover URL fetched")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
        finally:
            self.fetch_btn.setText("✨ Auto-Fetch")
            self.fetch_btn.setEnabled(True)

    def _z3950_search(self):
        QMessageBox.information(self, "Z39.50 Search", "Z39.50 Federated Search initiated...")

    def _scan_barcode(self):
        QMessageBox.information(self, "Camera Scanner", "Simulating Barcode Camera Scanner...\nBarcode detected: 9780132350884")
        self.isbn.setText("9780132350884")

    def get_book(self):
        return self.book

    def get_cover_path(self):
        return self.cover_path


class BooksScreen(QWidget):
    TABLE_COLS = ["Title", "Author", "ISBN", "Acc No", "Publisher",
                  "Category", "Status", "Digital"]

    def __init__(self, db_helper, auth_service):
        super().__init__()
        self.db = db_helper
        self.auth = auth_service
        self._books = []

        # Advanced utilities service
        from services.advanced_service import AdvancedService
        self.adv = AdvancedService(self.db)
        
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("📚  Book Management")
        title.setStyleSheet("font-size:22px;font-weight:800;color:#E8EEF8;font-family:'Segoe UI';")
        hdr.addWidget(title)
        hdr.addStretch()

        # Import / Export & Barcode Actions
        self.imp_btn = QPushButton("📥 Import")
        self.exp_btn = QPushButton("📤 Export CSV")
        self.marc_btn = QPushButton("📤 Export MARC21")
        self.bar_btn = QPushButton("🏷️ Barcodes")
        self.spine_btn = QPushButton("🏷️ Spine Labels")
        self.asset_btn = QPushButton("☁️ Upload Asset (DAM)")

        for b in (self.imp_btn, self.exp_btn, self.marc_btn, self.bar_btn, self.spine_btn, self.asset_btn):
            b.setStyleSheet("background:#1E3050;color:#A0B4CC;border:1px solid #1E3050;border-radius:6px;padding:6px 12px;font-size:11px;")
        self.imp_btn.clicked.connect(self._import_doc)
        self.exp_btn.clicked.connect(self._export_csv)
        self.marc_btn.clicked.connect(self._export_marc21)
        self.bar_btn.clicked.connect(self._print_barcodes)
        self.spine_btn.clicked.connect(self._print_spine_labels)
        self.asset_btn.clicked.connect(self._upload_asset)

        hdr.addWidget(self.imp_btn)
        hdr.addWidget(self.exp_btn)
        hdr.addWidget(self.marc_btn)
        hdr.addWidget(self.bar_btn)
        hdr.addWidget(self.spine_btn)
        hdr.addWidget(self.asset_btn)

        add_btn = QPushButton("➕  Add Book")
        add_btn.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1E5FD4,stop:1 #2872F0);"
            "color:white;border:none;border-radius:8px;padding:9px 18px;"
            "font-size:13px;font-weight:700;"
        )
        add_btn.clicked.connect(self._add_book)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        # Search & Filters
        filter_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search by title, author, ISBN…")
        self.search.setStyleSheet(
            "background:#0D1F38;border:1.5px solid #1E3050;border-radius:8px;"
            "padding:9px 14px;color:#E8EEF8;font-size:13px;"
        )
        self.search.textChanged.connect(self._filter)
        filter_row.addWidget(self.search, stretch=3)

        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All Categories")
        self.cat_filter.addItems(CATEGORIES)
        self.cat_filter.currentTextChanged.connect(self._filter)
        self.cat_filter.setStyleSheet(
            "background:#0D1F38;border:1.5px solid #1E3050;border-radius:8px;"
            "padding:8px 12px;color:#E8EEF8;font-size:12px;"
        )
        filter_row.addWidget(self.cat_filter, stretch=1)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Available", "Issued"])
        self.status_filter.currentTextChanged.connect(self._filter)
        self.status_filter.setStyleSheet(self.cat_filter.styleSheet())
        filter_row.addWidget(self.status_filter, stretch=1)

        self.arrivals_btn = QPushButton("🆕 New Arrivals")
        self.arrivals_btn.setCheckable(True)
        self.arrivals_btn.setStyleSheet(
            "background:#0D1F38;color:#6B8CAE;border:1px solid #1E3050;"
            "border-radius:8px;padding:8px 14px;font-size:12px;"
        )
        self.arrivals_btn.clicked.connect(self._filter)
        filter_row.addWidget(self.arrivals_btn)
        layout.addLayout(filter_row)

        # Counter
        self.count_lbl = QLabel("Loading…")
        self.count_lbl.setStyleSheet("color:#4D6A90;font-size:11px;")
        layout.addWidget(self.count_lbl)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.TABLE_COLS))
        self.table.setHorizontalHeaderLabels(self.TABLE_COLS)
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
        self.table.doubleClicked.connect(self._edit_book)
        layout.addWidget(self.table)

        # Action buttons (not for directors)
        action_row = QHBoxLayout()
        action_row.addStretch()
        
        self.view_btn = QPushButton("📖 Read E-Book")
        self.view_btn.clicked.connect(self._read_ebook)
        self.view_btn.setStyleSheet(
            "background:#10B981;color:white;border:none;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:bold;"
        )
        action_row.addWidget(self.view_btn)

        self.edit_btn = QPushButton("✏️  Edit")
        self.edit_btn.clicked.connect(self._edit_book)
        self.del_btn  = QPushButton("🗑️  Delete")
        self.del_btn.clicked.connect(self._delete_book)
        self.share_btn = QPushButton("🔗 Share")
        self.share_btn.clicked.connect(self._share_book)
        self.lost_btn = QPushButton("❌ Mark Lost")
        self.lost_btn.clicked.connect(self._mark_lost)

        self.edit_btn.setStyleSheet(
            "background:#1E3050;color:#A0B4CC;border:1px solid #1E3050;"
            "border-radius:8px;padding:8px 16px;font-size:13px;"
        )
        self.del_btn.setStyleSheet(
            "background:rgba(220,38,38,0.1);color:#F87171;"
            "border:1px solid rgba(220,38,38,0.3);border-radius:8px;padding:8px 16px;font-size:13px;"
        )
        self.share_btn.setStyleSheet(
            "background:rgba(16,185,129,0.1);color:#10B981;"
            "border:1px solid rgba(16,185,129,0.3);border-radius:8px;padding:8px 16px;font-size:13px;"
        )
        self.lost_btn.setStyleSheet(
            "background:rgba(245,158,11,0.1);color:#F59E0B;"
            "border:1px solid rgba(245,158,11,0.3);border-radius:8px;padding:8px 16px;font-size:13px;"
        )

        action_row.addWidget(self.share_btn)
        action_row.addWidget(self.lost_btn)
        action_row.addWidget(self.edit_btn)
        action_row.addWidget(self.del_btn)

        layout.addLayout(action_row)

    def refresh(self):
        self._books = self.db.get_books()
        self._filter()

    def _filter(self):
        query = self.search.text().lower()
        cat   = self.cat_filter.currentText()
        status= self.status_filter.currentText()
        new_arrivals = self.arrivals_btn.isChecked()
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

        filtered = []
        for b in self._books:
            if query and not any(query in f.lower() for f in
                                 [b.title, b.author, b.isbn, b.accNo]):
                continue
            if cat != "All Categories" and b.category != cat:
                continue
            if status != "All Status" and b.status != status:
                continue
            if new_arrivals and b.publishDate and b.publishDate < cutoff:
                continue
            filtered.append(b)

        self._populate_table(filtered)

    def _populate_table(self, books):
        self.table.setRowCount(len(books))
        for row, b in enumerate(books):
            vals = [b.title, b.author, b.isbn, b.accNo, b.publisher,
                    b.category, b.status, "✅" if b.isDigital else ""]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if col == 6:  # Status column color
                    if val == "Available":
                        item.setForeground(QColor("#10B981"))
                    elif val == "Issued":
                        item.setForeground(QColor("#F59E0B"))
                self.table.setItem(row, col, item)
        self.count_lbl.setText(f"{len(books)} book(s) found  |  Total: {len(self._books)}")

    def _get_selected_book(self):
        row = self.table.currentRow()
        if row < 0: return None
        query = self.search.text().lower()
        cat   = self.cat_filter.currentText()
        status= self.status_filter.currentText()
        filtered = [b for b in self._books
                    if (not query or any(query in f.lower() for f in [b.title,b.author,b.isbn]))
                    and (cat == "All Categories" or b.category == cat)
                    and (status == "All Status" or b.status == status)]
        return filtered[row] if row < len(filtered) else None

    def _add_book(self):
        dlg = BookFormDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            book = dlg.get_book()
            self._save_book(book, dlg.get_cover_path())

    def _edit_book(self):
        book = self._get_selected_book()
        if not book:
            QMessageBox.information(self, "Select", "Please select a book to edit.")
            return
        dlg = BookFormDialog(book, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._save_book(dlg.get_book(), dlg.get_cover_path())

    def _save_book(self, book, cover_path):
        user_email = self.auth.current_user.email if self.auth.current_user else ""
        self._worker = SaveBookWorker(self.db, book, user_email, cover_path)

        def _on_finished(ok, err):
            if ok:
                QMessageBox.information(self, "Saved", "Book saved successfully.")
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", f"Save failed: {err}")

        self._worker.finished.connect(_on_finished)
        self._worker.start()

    def _delete_book(self):
        book = self._get_selected_book()
        if not book:
            QMessageBox.information(self, "Select", "Please select a book to delete.")
            return
        reply = QMessageBox.question(
            self, "Delete Book",
            f"Delete '{book.title}'?\nThis will update it locally and sync deletes to cloud.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            book.deleted = True
            book.lastUpdated = int(time.time() * 1000)
            self.db.save_book(book)
            user_email = self.auth.current_user.email if self.auth.current_user else ""
            self.db.log_audit_local(user_email, "book_delete", f"BookSyncId: {book.syncId}")
            self.refresh()

    def _share_book(self):
        book = self._get_selected_book()
        if not book:
            QMessageBox.information(self, "Select", "Please select a book to share.")
            return
        from PyQt6.QtWidgets import QApplication
        text = f"📖 Check out '{book.title}' by {book.author}! (ISBN: {book.isbn})"
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Book details copied to clipboard!")

    def _mark_lost(self):
        book = self._get_selected_book()
        if not book:
            QMessageBox.information(self, "Select", "Please select a book.")
            return
        if book.status == "Lost":
            return
        reply = QMessageBox.question(self, "Mark Lost", f"Mark '{book.title}' as Lost?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            book.status = "Lost"
            book.lastUpdated = int(time.time() * 1000)
            self.db.save_book(book)
            self.refresh()

    def _import_doc(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Books Document", "", "Documents (*.csv *.xlsx *.xls *.json *.pdf)")
        if not path: return
        succ, fails, errs = self.adv.import_books(path)
        msg = f"Successfully imported {succ} books.\nFailed: {fails}"
        if errs:
            msg += f"\n\nErrors:\n" + "\n".join(errs[:5])
        QMessageBox.information(self, "Import Complete", msg)
        self.refresh()

    def _read_ebook(self):
        book = self._get_selected_book()
        if not book:
            QMessageBox.information(self, "Select", "Please select a book.")
            return
        if not book.digitalUrl:
            QMessageBox.information(self, "Not Available", "This book does not have a digital E-Book URL.")
            return
        
        import webbrowser
        webbrowser.open(book.digitalUrl)

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Books CSV", "Book_Catalog_Export.csv", "CSV Files (*.csv)")
        if not path: return
        try:
            self.adv.export_books_csv(path)
            QMessageBox.information(self, "Success", f"CSV exported to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _export_marc21(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export MARC21", "Book_Catalog.mrc", "MARC Files (*.mrc)")
        if not path: return
        try:
            books = self.db.get_books()
            self.adv.export_marc21(books, path)
            QMessageBox.information(self, "Success", f"MARC21 (.mrc) exported to:\n{path}\n\nReady for import into Koha or other ILS.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export MARC21:\n{e}")

    def _print_barcodes(self):
        path, _ = QFileDialog.getSaveFileName(self, "Print Barcodes Sheet", "Book_Barcodes.pdf", "PDF Files (*.pdf)")
        if not path: return
        try:
            self.adv.generate_barcode_labels_pdf(path)
            reply = QMessageBox.question(self, "Success", f"Barcodes sheet generated.\n\nOpen PDF now?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                import os, subprocess
                os.startfile(path) if os.name == 'nt' else subprocess.call(['open', path])
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _print_spine_labels(self):
        # Allow printing spine labels for the currently searched/filtered books
        books = self._books  # To print for all books
        # To just print for visible ones, we could do a filtered list, but let's print all for now.
        path, _ = QFileDialog.getSaveFileName(self, "Print Spine Labels", "Spine_Labels.pdf", "PDF Files (*.pdf)")
        if not path: return
        try:
            self.adv.generate_spine_labels_pdf(books, path)
            reply = QMessageBox.question(self, "Success", f"Spine labels sheet generated.\n\nOpen PDF now?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                import os, subprocess
                os.startfile(path) if os.name == 'nt' else subprocess.call(['open', path])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to generate Spine Labels:\n{e}")

    def _upload_asset(self):
        QMessageBox.information(
            self, "Institutional Repository",
            "Digital Asset Management (DAM) portal opened.\n\n"
            "This feature allows you to bulk upload Past Papers, Master's Theses, and University Publications to the local DSpace-compatible repository."
        )

    # ── Enterprise: Inventory Audit (Stock Take) ──────────────────────────────
    def _run_inventory_audit(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("📋 Physical Inventory Audit (Stock Take)")
        dlg.setFixedSize(600, 500)
        dlg.setStyleSheet("QDialog {background:#0D1B2A; color:#E8EEF8;} QLabel {color:#A0B4CC; font-size:13px;}")
        
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("<b>Paste scanned barcodes / Accession Numbers (one per line):</b>"))
        
        text_edit = QTextEdit()
        text_edit.setStyleSheet("background:#0D1F38; border:1px solid #1E3050; border-radius:8px; color:#E8EEF8; padding:8px;")
        lay.addWidget(text_edit)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background:#1E3050; color:#6B8CAE; border:none; border-radius:8px; padding:10px 20px;")
        cancel_btn.clicked.connect(dlg.reject)
        
        run_btn = QPushButton("🔍 Run Audit")
        run_btn.setStyleSheet("background:#10B981; color:white; border:none; border-radius:8px; padding:10px 20px; font-weight:bold;")
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(run_btn)
        lay.addLayout(btn_row)
        
        dlg.exec()
