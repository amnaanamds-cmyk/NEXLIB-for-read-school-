"""
ui/screens/members_screen.py — Student/Member Management with PIN reset and history.
"""
import uuid
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QComboBox, QMessageBox, QFileDialog, QInputDialog, QTabWidget, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from models import Member


class MemberFormDialog(QDialog):
    STYLE = """
    QDialog { background: #0D1B2A; }
    QLabel { color: #A0B4CC; font-size: 12px; font-family: 'Segoe UI'; }
    QLineEdit, QComboBox {
        background: #0D1F38; border: 1.5px solid #1E3050;
        border-radius: 8px; padding: 8px 12px;
        color: #E8EEF8; font-size: 13px;
    }
    QLineEdit:focus { border-color: #C8A84B; }
    QPushButton#saveBtn {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1E5FD4,stop:1 #2872F0);
        color:white;border:none;border-radius:8px;padding:10px 24px;
        font-size:14px;font-weight:700;
    }
    QPushButton#cancelBtn {
        background:rgba(30,48,80,0.5);color:#6B8CAE;
        border:1px solid #1E3050;border-radius:8px;padding:10px 20px;
    }
    """

    def __init__(self, member: Member = None, parent=None):
        super().__init__(parent)
        self.member = member or Member()
        self.photo_path = None
        self.setWindowTitle("Add Member" if not member else "Edit Member")
        self.setStyleSheet(self.STYLE)
        self.setMinimumWidth(520)
        self._build()

    def _f(self, val, ph=""): f = QLineEdit(val or ""); f.setPlaceholderText(ph); return f

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

        lay.addWidget(QLabel("👤  Member Details",
                             styleSheet="font-size:16px;font-weight:800;color:#E6C96E;"))

        form = QFormLayout(); form.setSpacing(10)
        self.memberId   = self._f(self.member.memberId,   "S101")
        self.name       = self._f(self.member.name,       "Full Name")
        self.email      = self._f(self.member.email,      "email@college.edu")
        self.phone      = self._f(self.member.phone,      "03001234567")
        self.fatherName = self._f(self.member.fatherName, "Father's Name")
        self.className  = self._f(self.member.className,  "Class/Section")
        self.classNo    = self._f(self.member.classNo,    "Roll/Class No")
        self.dept       = self._f(self.member.department, "Computer Science")
        self.designation= self._f(self.member.designation,"Student/Teacher")
        self.bps        = self._f(self.member.bps,        "BPS-17")
        self.address    = self._f(self.member.address,    "Address")
        self.joinDate   = self._f(self.member.joinDate,   "2024-01-01")
        self.expiryDate = self._f(self.member.expiryDate, "2027-12-31")
        self.pin        = self._f(self.member.pin,        "4-digit PIN")

        self.mtype = QComboBox()
        self.mtype.addItems(["Student", "Faculty", "Staff", "Admin"])
        if self.member.memberType:
            self.mtype.setCurrentText(self.member.memberType)

        for lbl, w in [
            ("Member ID *", self.memberId), ("Full Name *", self.name),
            ("Email", self.email), ("Phone", self.phone),
            ("Father Name", self.fatherName), ("Class", self.className),
            ("Class/Roll No", self.classNo), ("Department", self.dept),
            ("Member Type", self.mtype), ("Designation", self.designation),
            ("BPS", self.bps), ("Address", self.address),
            ("Join Date", self.joinDate), ("Expiry Date", self.expiryDate),
            ("OPAC PIN", self.pin),
        ]:
            form.addRow(lbl, w)
        lay.addLayout(form)

        # Photo picker
        photo_row = QHBoxLayout()
        self.photo_lbl = QLabel("No photo selected")
        self.photo_lbl.setStyleSheet("color:#4D6A90;font-size:11px;")
        pick_btn = QPushButton("📷  Choose Photo")
        pick_btn.setStyleSheet("background:#1E3050;color:#6B8CAE;border:1px solid #1E3050;"
                               "border-radius:6px;padding:6px 12px;")
        pick_btn.clicked.connect(self._pick_photo)
        photo_row.addWidget(self.photo_lbl); photo_row.addWidget(pick_btn)
        lay.addLayout(photo_row)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Action Buttons (Fixed at bottom)
        btn_container = QWidget()
        btn_container.setStyleSheet("background: #0D1B2A; border-top: 1px solid #1E3050;")
        btn_row = QHBoxLayout(btn_container)
        btn_row.setContentsMargins(24, 12, 24, 16)
        btn_row.addStretch()
        cancel = QPushButton("Cancel"); cancel.setObjectName("cancelBtn")
        cancel.clicked.connect(self.reject)
        save = QPushButton("💾  Save Member"); save.setObjectName("saveBtn")
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(save)
        main_layout.addWidget(btn_container)

        self.setMinimumHeight(600)

    def _pick_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Photo", "",
                                              "Images (*.png *.jpg *.jpeg)")
        if path:
            self.photo_path = path
            self.photo_lbl.setText(f"📷 {path.split('/')[-1]}")

    def _save(self):
        if not self.memberId.text().strip() or not self.name.text().strip():
            QMessageBox.warning(self, "Required", "Member ID and Name are required.")
            return
        self.member.memberId    = self.memberId.text().strip()
        self.member.name        = self.name.text().strip()
        self.member.email       = self.email.text().strip()
        self.member.phone       = self.phone.text().strip()
        self.member.fatherName  = self.fatherName.text().strip()
        self.member.className   = self.className.text().strip()
        self.member.classNo     = self.classNo.text().strip()
        self.member.department  = self.dept.text().strip()
        self.member.memberType  = self.mtype.currentText()
        self.member.designation = self.designation.text().strip()
        self.member.bps         = self.bps.text().strip()
        self.member.address     = self.address.text().strip()
        self.member.joinDate    = self.joinDate.text().strip()
        self.member.expiryDate  = self.expiryDate.text().strip()
        self.member.pin         = self.pin.text().strip()
        self.accept()

    def get_member(self): return self.member
    def get_photo_path(self): return self.photo_path


class SaveMemberWorker(QThread):
    finished = pyqtSignal(bool, str)
    def __init__(self, fb, db, member, user_email, photo_path=None):
        super().__init__()
        self.fb, self.db, self.member, self.user_email, self.photo_path = fb, db, member, user_email, photo_path
    def run(self):
        try:
            if self.photo_path:
                remote = f"photos/{self.member.syncId or uuid.uuid4()}.jpg"
                try:
                    url = self.fb.upload_file(self.photo_path, remote)
                    self.member.photoUri = url
                except Exception:
                    pass
            self.db.save_member(self.member)
            self.db.log_audit_local(self.user_email, "member_save", f"Member: {self.member.name} ({self.member.syncId})")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class MembersScreen(QWidget):
    TABLE_COLS = ["Member ID", "Name", "Email", "Phone", "Dept",
                  "Type", "Books Issued", "Expiry"]

    def __init__(self, firebase_service, db_helper, auth_service, read_only=False):
        super().__init__()
        self.fb = firebase_service
        self.db = db_helper
        self.auth = auth_service
        self.read_only = read_only
        self._members = []
        self._listener = None
        
        # Pagination state
        self.current_page = 0
        self.page_size = 50
        self.total_count = 0

        from services.advanced_service import AdvancedService
        self.adv = AdvancedService(self.db)
        
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        hdr = QHBoxLayout()
        title = QLabel("👥  Member Management")
        title.setStyleSheet("font-size:22px;font-weight:800;color:#E8EEF8;font-family:'Segoe UI';")
        hdr.addWidget(title); hdr.addStretch()
        
        if not self.read_only:
            # Import / Export
            self.imp_btn = QPushButton("📥 Import Documents")
            self.exp_btn = QPushButton("📤 Export CSV")
            for b in (self.imp_btn, self.exp_btn):
                b.setStyleSheet("background:#1E3050;color:#A0B4CC;border:1px solid #1E3050;border-radius:6px;padding:6px 12px;font-size:11px;")
            self.imp_btn.clicked.connect(self._import_doc)
            self.exp_btn.clicked.connect(self._export_csv)
            hdr.addWidget(self.imp_btn)
            hdr.addWidget(self.exp_btn)

            add_btn = QPushButton("➕  Add Member")
            add_btn.setStyleSheet(
                "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7C3AED,stop:1 #8B5CF6);"
                "color:white;border:none;border-radius:8px;padding:9px 18px;font-size:13px;font-weight:700;"
            )
            add_btn.clicked.connect(self._add_member)
            hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        # Search
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search by name, member ID, email…")
        self.search.setStyleSheet(
            "background:#0D1F38;border:1.5px solid #1E3050;border-radius:8px;"
            "padding:9px 14px;color:#E8EEF8;font-size:13px;"
        )
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.count_lbl = QLabel("Loading…")
        self.count_lbl.setStyleSheet("color:#4D6A90;font-size:11px;")
        layout.addWidget(self.count_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.TABLE_COLS))
        self.table.setHorizontalHeaderLabels(self.TABLE_COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { background:#071428;color:#E8EEF8;gridline-color:#1E3050;
                border:none;font-size:13px;font-family:'Segoe UI'; }
            QTableWidget::item { padding:8px; }
            QTableWidget::item:selected { background:rgba(124,58,237,0.3); }
            QHeaderView::section { background:#0D1B2A;color:#6B8CAE;font-weight:700;
                font-size:11px;padding:8px;border-bottom:1px solid #1E3050; }
            QTableWidget::item:alternate { background:rgba(13,28,55,0.6); }
        """)
        self.table.doubleClicked.connect(self._edit_member)
        layout.addWidget(self.table)
        
        # Pagination Controls
        pag_row = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self._next_page)
        self.page_lbl = QLabel("Page 1")
        self.page_lbl.setStyleSheet("color:#A0B4CC;font-weight:bold;")
        
        pag_row.addStretch()
        pag_row.addWidget(self.prev_btn)
        pag_row.addWidget(self.page_lbl)
        pag_row.addWidget(self.next_btn)
        pag_row.addStretch()
        layout.addLayout(pag_row)

        if not self.read_only:
            action_row = QHBoxLayout(); action_row.addStretch()
            self.edit_btn = QPushButton("✏️  Edit")
            self.edit_btn.clicked.connect(self._edit_member)
            self.del_btn  = QPushButton("🗑️  Delete")
            self.del_btn.clicked.connect(self._delete_member)
            self.pin_btn  = QPushButton("🔑  Reset PIN")
            self.pin_btn.clicked.connect(self._reset_pin)
            self.copy_pin_btn = QPushButton("📋  Copy PIN")
            self.copy_pin_btn.clicked.connect(self._copy_pin)
            self.hist_btn = QPushButton("📋  View History")
            self.hist_btn.clicked.connect(self._view_history)
            self.rec_btn = QPushButton("🧠 AI Recommend")
            self.rec_btn.clicked.connect(self._ai_recommend)
            self.idcard_btn = QPushButton("🪪 Print ID Card")
            self.idcard_btn.clicked.connect(self._print_id_card_single)
            self.overdue_btn = QPushButton("⏰ Overdue Check")
            self.overdue_btn.clicked.connect(self._check_overdue)
            self.ledger_btn = QPushButton("💰 Fines Ledger")
            self.ledger_btn.clicked.connect(self._view_fines_ledger)

            for b in (self.edit_btn, self.del_btn, self.pin_btn, self.copy_pin_btn, self.hist_btn,
                      self.rec_btn, self.idcard_btn, self.overdue_btn, self.ledger_btn):
                b.setStyleSheet(
                    "background:#1E3050;color:#A0B4CC;border:1px solid #1E3050;"
                    "border-radius:8px;padding:8px 14px;font-size:12px;"
                )
            self.del_btn.setStyleSheet(
                "background:rgba(220,38,38,0.1);color:#F87171;"
                "border:1px solid rgba(220,38,38,0.3);border-radius:8px;padding:8px 14px;font-size:12px;"
            )
            self.rec_btn.setStyleSheet(
                "background:#7C3AED;color:white;border:none;border-radius:8px;padding:8px 14px;font-size:12px;font-weight:bold;"
            )
            self.idcard_btn.setStyleSheet(
                "background:#0891B2;color:white;border:none;border-radius:8px;padding:8px 14px;font-size:12px;font-weight:bold;"
            )
            self.overdue_btn.setStyleSheet(
                "background:rgba(217,119,6,0.15);color:#F59E0B;border:1px solid rgba(217,119,6,0.4);"
                "border-radius:8px;padding:8px 14px;font-size:12px;"
            )
            self.ledger_btn.setStyleSheet(
                "background:rgba(16,185,129,0.15);color:#10B981;border:1px solid rgba(16,185,129,0.4);"
                "border-radius:8px;padding:8px 14px;font-size:12px;font-weight:bold;"
            )
            for b in (self.edit_btn, self.del_btn, self.pin_btn, self.copy_pin_btn, self.hist_btn,
                      self.rec_btn, self.idcard_btn, self.overdue_btn, self.ledger_btn):
                action_row.addWidget(b)
            layout.addLayout(action_row)

    def refresh(self):
        self.current_page = 0
        self._filter()
        
    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._filter()
            
    def _next_page(self):
        if (self.current_page + 1) * self.page_size < self.total_count:
            self.current_page += 1
            self._filter()

    def _filter(self):
        # We need a proper DB search method for members, but for now we fallback
        # to fetching all if we don't have search_members_paginated in db_helper yet.
        # Actually I will implement search_members_paginated below.
        q = self.search.text().lower()
        
        # Since I didn't add search_members_paginated yet, I will use get_members_paginated 
        # and manually filter if there's a search. Wait, I should fetch all if searching, 
        # or implement it correctly. To be completely functional without breaking:
        all_members = self.db.get_members()
        filtered = [m for m in all_members
                    if not q or any(q in f.lower() for f in
                                    [m.name, m.memberId, m.email, m.phone])]
                                    
        self.total_count = len(filtered)
        start = self.current_page * self.page_size
        end = start + self.page_size
        self._members = filtered[start:end]
        
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(end < self.total_count)
        self.page_lbl.setText(f"Page {self.current_page + 1} (Total: {self.total_count})")
        
        self._populate(self._members)

    def _populate(self, members):
        self.table.setRowCount(len(members))
        for row, m in enumerate(members):
            vals = [
                m.memberId, m.name, m.email, m.phone, m.department,
                m.memberType, str(m.booksIssued), m.expiryDate
            ]
            for col, val in enumerate(vals):
                self.table.setItem(row, col, QTableWidgetItem(val))
        self.count_lbl.setText(f"Showing {len(members)} member(s)  |  Total matches: {self.total_count}")

    def _get_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._members): return None
        return self._members[row]

    def _add_member(self):
        dlg = MemberFormDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._save_member(dlg.get_member(), dlg.get_photo_path())

    def _edit_member(self):
        m = self._get_selected()
        if not m:
            QMessageBox.information(self, "Select", "Please select a member."); return
        dlg = MemberFormDialog(m, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._save_member(dlg.get_member(), dlg.get_photo_path())

    def _save_member(self, member, photo_path):
        user_email = self.auth.current_user.email if self.auth.current_user else ""
        self._worker = SaveMemberWorker(self.fb, self.db, member, user_email, photo_path)

        def _on_finished(ok, err):
            if ok:
                QMessageBox.information(self, "Saved", "Member saved locally and queued for synchronization!")
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", err)

        self._worker.finished.connect(_on_finished)
        self._worker.start()

    def _ai_recommend(self):
        m = self._get_selected()
        if not m:
            QMessageBox.information(self, "Select", "Please select a member to generate recommendations.")
            return
            
        recs = self.adv.get_recommendations_for_member(m.id)
        
        if not recs:
            QMessageBox.information(self, "AI Recommend", f"No available recommendations for {m.name} right now.")
            return
            
        msg = f"<b>Smart Recommendations for {m.name}:</b><ul>"
        for r in recs:
            msg += f"<li><b>{r.title}</b> by {r.author} <i>({r.category})</i></li>"
        msg += "</ul>"
        
        QMessageBox.information(self, "🧠 Smart Recommendations", msg)

    def _delete_member(self):
        m = self._get_selected()
        if not m:
            QMessageBox.information(self, "Select", "Please select a member."); return
        reply = QMessageBox.question(self, "Delete",
                                     f"Delete member '{m.name}'?\nThis will update it locally and sync deletes to cloud.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            m.deleted = True
            m.lastUpdated = int(time.time() * 1000)
            self.db.save_member(m)
            user_email = self.auth.current_user.email if self.auth.current_user else ""
            self.db.log_audit_local(user_email, "member_delete", f"MemberSyncId: {m.syncId}")
            self.refresh()

    def _reset_pin(self):
        m = self._get_selected()
        if not m:
            QMessageBox.information(self, "Select", "Please select a member."); return
        pin, ok = QInputDialog.getText(self, "Reset PIN",
                                       f"Enter new 4-digit PIN for {m.name}:")
        if ok and pin:
            if not pin.isdigit() or len(pin) != 4:
                QMessageBox.warning(self, "Invalid", "PIN must be exactly 4 digits.")
                return
            m.pin = pin
            m.lastUpdated = int(time.time() * 1000)
            self.db.save_member(m)
            user_email = self.auth.current_user.email if self.auth.current_user else ""
            self.db.log_audit_local(user_email, "member_pin_reset", f"MemberSyncId: {m.syncId}")
            QMessageBox.information(self, "Done", f"PIN reset locally for {m.name} and queued for sync.")
            self.refresh()

    def _copy_pin(self):
        m = self._get_selected()
        if not m:
            QMessageBox.information(self, "Select", "Please select a member."); return
        if not m.pin:
            QMessageBox.information(self, "No PIN", f"{m.name} does not have a PIN set.")
            return
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(m.pin)
        QMessageBox.information(self, "Copied", f"PIN for {m.name} copied to clipboard!")

    def _view_history(self):
        m = self._get_selected()
        if not m:
            QMessageBox.information(self, "Select", "Please select a member."); return
        try:
            records = [r for r in self.db.get_issues() if r.memberMemberId == m.memberId]
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Borrowing History — {m.name}")
            dlg.setStyleSheet("QDialog{background:#0D1B2A;}")
            dlg.setMinimumSize(600, 400)
            lay = QVBoxLayout(dlg)
            tbl = QTableWidget(len(records), 6)
            tbl.setHorizontalHeaderLabels(["Book", "ISBN", "Issued", "Due", "Returned", "Fine"])
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            tbl.setStyleSheet("background:#071428;color:#E8EEF8;font-size:12px;")
            for row, r in enumerate(records):
                for col, val in enumerate([
                    r.bookTitle, r.bookIsbn, r.issueDate, r.dueDate,
                    r.returnDate or "—", f"Rs.{r.fine:.0f}"
                ]):
                    item = QTableWidgetItem(val)
                    if col == 5 and r.fine > 0:
                        item.setForeground(QColor("#EF4444"))
                    tbl.setItem(row, col, item)
            lay.addWidget(tbl)
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _import_doc(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Members Document", "", "Documents (*.csv *.xlsx *.xls *.json *.pdf)")
        if not path: return
        succ, fails, errs = self.adv.import_members(path)
        msg = f"Successfully imported {succ} members.\nFailed: {fails}"
        if errs:
            msg += f"\n\nErrors:\n" + "\n".join(errs[:5])
        QMessageBox.information(self, "Import Complete", msg)
        self.refresh()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Students CSV", "Student_Directory_Export.csv", "CSV Files (*.csv)")
        if not path: return
        try:
            self.adv.export_members_csv(path)
            QMessageBox.information(self, "Success", f"CSV exported to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    # ── Enterprise: Student ID Card Generator ─────────────────────────────────
    def _print_id_card_single(self):
        m = self._get_selected()
        if not m:
            QMessageBox.information(self, "Select", "Please select a member."); return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save ID Card PDF",
            f"ID_Card_{m.memberId}.pdf", "PDF Files (*.pdf)"
        )
        if not path: return
        try:
            self.adv.generate_id_cards_pdf([m], path)
            reply = QMessageBox.question(
                self, "ID Card Ready",
                f"ID Card for {m.name} saved.\n\nOpen now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                import os
                os.startfile(path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"ID Card generation failed:\n{e}")

    # ── Enterprise: Overdue Check for selected member ─────────────────────────
    def _check_overdue(self):
        m = self._get_selected()
        if not m:
            QMessageBox.information(self, "Select", "Please select a member."); return
        import time
        today = time.strftime("%Y-%m-%d")
        issues = [i for i in self.db.get_issues()
                  if i.memberId == m.id and i.status == "Issued" and i.dueDate < today]
        if not issues:
            QMessageBox.information(
                self, "✅ No Overdue",
                f"{m.name} has no overdue books."
            )
        else:
            fine_rate = 5  # Rs/day fallback
            try:
                fine_rate = self.fb.get_fine_rate()
            except Exception:
                pass
            msg = f"<b>{m.name}</b> has <b>{len(issues)}</b> overdue book(s):<br><br>"
            total_fine = 0.0
            for i in issues:
                from datetime import datetime, date
                try:
                    due = datetime.strptime(i.dueDate, "%Y-%m-%d").date()
                    days_late = (date.today() - due).days
                except Exception:
                    days_late = 0
                fine = days_late * fine_rate
                total_fine += fine
                msg += f"📖 <b>{i.bookTitle}</b> — {days_late}d overdue — Fine: Rs.{fine:.0f}<br>"
            msg += f"<br><b>Total Fine: Rs.{total_fine:.0f}</b>"
            QMessageBox.warning(self, "⏰ Overdue Alert", msg)

    # ── Enterprise: Patron Fines Ledger & Payments ────────────────────────────
    def _view_fines_ledger(self):
        m = self._get_selected()
        if not m:
            QMessageBox.information(self, "Select", "Please select a member."); return
            
        self._show_ledger_dialog(m)
        
    def _show_ledger_dialog(self, m):
        issues = self.db.get_issues()
        # Find returned issues with a fine (Debits)
        fine_history = [i for i in issues if i.memberId == m.id and i.status == "Returned" and (i.fine or 0) > 0]
        # Get payments/waivers (Credits)
        payments = self.db.get_fine_payments(m.id)
        
        total_fines = sum(i.fine or 0 for i in fine_history)
        total_paid = sum(p["amount"] for p in payments)
        balance = total_fines - total_paid
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"💰 Patron Fines Ledger — {m.name}")
        dlg.setFixedSize(650, 480)
        dlg.setStyleSheet("background:#0D1B2A; color:#E8EEF8; font-family:'Segoe UI';")
        
        lay = QVBoxLayout(dlg)
        header_lay = QHBoxLayout()
        header_lay.addWidget(QLabel(f"💰 Account Ledger for <b>{m.name}</b> ({m.memberId})", styleSheet="font-size:18px;font-weight:bold;color:#10B981;"))
        header_lay.addStretch()
        
        bal_lbl = QLabel(f"Outstanding Balance: <b>Rs. {balance:.2f}</b>")
        bal_lbl.setStyleSheet(f"font-size:16px;font-weight:bold;color:{'#EF4444' if balance > 0 else '#10B981'};")
        header_lay.addWidget(bal_lbl)
        lay.addLayout(header_lay)
        
        tabs = QTabWidget()
        tabs.setStyleSheet("QTabBar::tab{background:#1E3050;color:#A0B4CC;padding:8px 16px;} QTabBar::tab:selected{background:#2872F0;color:white;}")
        
        # Debits Tab
        debits_w = QWidget(); dl = QVBoxLayout(debits_w)
        if not fine_history:
            dl.addWidget(QLabel("✅ This patron has a clean record with no fines.", styleSheet="color:#A0B4CC;font-size:14px;"))
        else:
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Book Title", "Returned On", "Days Late", "Fine Accrued (Rs.)"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            table.setStyleSheet(self.table.styleSheet())
            table.setRowCount(len(fine_history))
            for row, i in enumerate(fine_history):
                fine = i.fine or 0
                
                from datetime import datetime
                try:
                    due = datetime.strptime(i.dueDate, "%Y-%m-%d").date()
                    ret = datetime.strptime(i.returnDate, "%Y-%m-%d").date()
                    days = (ret - due).days
                except Exception:
                    days = "?"
                    
                table.setItem(row, 0, QTableWidgetItem(i.bookTitle or "Unknown"))
                table.setItem(row, 1, QTableWidgetItem(i.returnDate or "Unknown"))
                table.setItem(row, 2, QTableWidgetItem(str(days)))
                
                fine_item = QTableWidgetItem(f"{fine:.2f}")
                fine_item.setForeground(QColor("#EF4444"))
                table.setItem(row, 3, fine_item)
            dl.addWidget(table)
        tabs.addTab(debits_w, "Fines (Debits)")
        
        # Credits Tab
        credits_w = QWidget(); cl = QVBoxLayout(credits_w)
        if not payments:
            cl.addWidget(QLabel("No payment history.", styleSheet="color:#A0B4CC;font-size:14px;"))
        else:
            ptable = QTableWidget()
            ptable.setColumnCount(4)
            ptable.setHorizontalHeaderLabels(["Date", "Method", "Reference", "Amount (Rs.)"])
            ptable.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            ptable.setStyleSheet(self.table.styleSheet())
            ptable.setRowCount(len(payments))
            for row, p in enumerate(payments):
                import datetime as dt
                dstr = dt.datetime.fromtimestamp(p["timestamp"]/1000).strftime("%Y-%m-%d %H:%M")
                ptable.setItem(row, 0, QTableWidgetItem(dstr))
                ptable.setItem(row, 1, QTableWidgetItem(p["method"]))
                ptable.setItem(row, 2, QTableWidgetItem(p["reference_id"]))
                amt_item = QTableWidgetItem(f"{p['amount']:.2f}")
                amt_item.setForeground(QColor("#10B981"))
                ptable.setItem(row, 3, amt_item)
            cl.addWidget(ptable)
        tabs.addTab(credits_w, "Payments (Credits)")
        
        lay.addWidget(tabs)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        if balance > 0:
            pay_btn = QPushButton("💵 Process Payment")
            pay_btn.setStyleSheet("background:#2563EB;color:white;border:none;border-radius:8px;padding:8px 16px;font-weight:bold;")
            pay_btn.clicked.connect(lambda: self._process_payment(m, balance, dlg))
            btn_row.addWidget(pay_btn)
            
            waive_btn = QPushButton("🚫 Waive Fine")
            waive_btn.setStyleSheet("background:#D97706;color:white;border:none;border-radius:8px;padding:8px 16px;font-weight:bold;")
            waive_btn.clicked.connect(lambda: self._waive_fine(m, balance, dlg))
            btn_row.addWidget(waive_btn)
            
        close_btn = QPushButton("Close Ledger")
        close_btn.setStyleSheet("background:#1E3050;color:#6B8CAE;border:none;border-radius:8px;padding:8px 16px;")
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(close_btn)
        
        lay.addLayout(btn_row)
        dlg.exec()
        
    def _process_payment(self, m, balance, parent_dlg):
        amt, ok = QInputDialog.getDouble(parent_dlg, "Process Payment", f"Enter amount to pay (Max Rs.{balance:.2f}):", balance, 1, balance, 2)
        if ok and amt > 0:
            methods = ["Cash", "Card", "Bank Transfer", "Online/UPI"]
            method, ok_m = QInputDialog.getItem(parent_dlg, "Payment Method", "Select method:", methods, 0, False)
            if ok_m:
                ref, _ = QInputDialog.getText(parent_dlg, "Reference", "Enter receipt/reference number (optional):")
                self.db.save_fine_payment(m.id, amt, method, ref or "N/A")
                user_email = self.auth.current_user.email if self.auth.current_user else ""
                self.db.log_audit_local(user_email, "fine_payment", f"Paid Rs.{amt} via {method} for {m.name}")
                QMessageBox.information(parent_dlg, "Success", f"Payment of Rs.{amt:.2f} processed successfully.")
                parent_dlg.accept()
                self._show_ledger_dialog(m)
                
    def _waive_fine(self, m, balance, parent_dlg):
        amt, ok = QInputDialog.getDouble(parent_dlg, "Waive Fine", f"Enter amount to waive (Max Rs.{balance:.2f}):", balance, 1, balance, 2)
        if ok and amt > 0:
            reason, ok_r = QInputDialog.getText(parent_dlg, "Waiver Reason", "Reason for waiving fine:")
            if ok_r:
                self.db.save_fine_payment(m.id, amt, "Waiver", reason or "Admin Waiver")
                user_email = self.auth.current_user.email if self.auth.current_user else ""
                self.db.log_audit_local(user_email, "fine_waiver", f"Waived Rs.{amt} for {m.name}. Reason: {reason}")
                QMessageBox.information(parent_dlg, "Success", f"Waiver of Rs.{amt:.2f} applied successfully.")
                parent_dlg.accept()
                self._show_ledger_dialog(m)
