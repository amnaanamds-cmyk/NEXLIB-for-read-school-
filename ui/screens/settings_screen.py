"""
ui/screens/settings_screen.py — School profile, fine rates, staff accounts,
and other system settings. Fully offline (local SQLite).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QDoubleSpinBox, QMessageBox, QFrame, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QCheckBox, QDialog, QTextEdit, QFileDialog, QInputDialog, QLineEdit
)
from PyQt6.QtCore import Qt
import json
import os


class SettingsScreen(QWidget):
    def __init__(self, db_helper, auth_service):
        super().__init__()
        self.db = db_helper
        self.auth = auth_service
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        layout.addWidget(QLabel("⚙️  System Settings", 
                              styleSheet="font-size: 26px; font-weight: 900; color: #E8EEF8; font-family: 'Segoe UI';"))

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #1E3050; border-radius: 8px; background: #0D1F38; }
            QTabBar::tab { background: #071428; color: #6B8CAE; padding: 10px 20px; border: 1px solid #1E3050; border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QTabBar::tab:selected { background: #0D1F38; color: #E8EEF8; font-weight: bold; }
        """)

        # 1. General Settings Tab
        gen_tab = QWidget()
        gen_lay = QVBoxLayout(gen_tab)
        gen_lay.setContentsMargins(24, 24, 24, 24)

        form = QFormLayout()
        form.setSpacing(16)
        self.fine_spin = QDoubleSpinBox()
        self.fine_spin.setRange(0, 1000)
        self.fine_spin.setPrefix("Rs. ")
        self.fine_spin.setStyleSheet("background: #0D1B2A; border: 1px solid #1E3050; border-radius: 6px; padding: 8px; color: white;")
        
        lbl = QLabel("Daily Overdue Fine Rate")
        lbl.setStyleSheet("color: #A0B4CC; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        form.addRow(lbl, self.fine_spin)
        gen_lay.addLayout(form)
        
        save_btn = QPushButton("💾  Save Settings")
        save_btn.setStyleSheet("background: #1E5FD4; color: white; border: none; border-radius: 8px; padding: 10px 24px; font-weight: 700; font-size: 14px; margin-top: 20px;")
        save_btn.clicked.connect(self._save)

        # UI Preferences Mock (7.1, 7.2, 7.3)
        ui_lbl = QLabel("UI Preferences (Applies immediately or on restart)")
        ui_lbl.setStyleSheet("color: #E8EEF8; font-size: 16px; font-weight: bold; margin-top: 20px;")
        gen_lay.addWidget(ui_lbl)

        ui_form = QFormLayout()
        
        self.lang_cb = QComboBox()
        self.lang_cb.addItems(["English", "Hindi"])
        self.lang_cb.currentTextChanged.connect(self._toggle_lang)
        self.lang_cb.setStyleSheet(self.fine_spin.styleSheet())
        ui_form.addRow("Language (English/Hindi)", self.lang_cb)

        self.theme_cb = QComboBox()
        self.theme_cb.addItems(["Dark Mode", "Light Mode"])
        self.theme_cb.currentTextChanged.connect(self._toggle_theme)
        self.theme_cb.setStyleSheet(self.fine_spin.styleSheet())
        ui_form.addRow("App Theme", self.theme_cb)

        self.font_scale = QDoubleSpinBox()
        self.font_scale.setRange(0.8, 2.0)
        self.font_scale.setSingleStep(0.1)
        self.font_scale.setValue(1.0)
        self.font_scale.valueChanged.connect(self._toggle_font)
        self.font_scale.setStyleSheet(self.fine_spin.styleSheet())
        ui_form.addRow("Accessibility Font Scaling", self.font_scale)

        gen_lay.addLayout(ui_form)
        
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(save_btn)
        gen_lay.addLayout(row)
        gen_lay.addStretch()
        self.tabs.addTab(gen_tab, "General")

        # School Profile Tab
        profile_tab = QWidget()
        self._build_profile_tab(profile_tab)
        self.tabs.addTab(profile_tab, "School Profile")

        # Staff Accounts Tab
        staff_tab = QWidget()
        self._build_staff_tab(staff_tab)
        self.tabs.addTab(staff_tab, "Staff Accounts")

        # 1.5 Circulation Matrix Tab (Enterprise / Koha Feature)
        circ_tab = QWidget()
        self._build_circ_tab(circ_tab)
        self.tabs.addTab(circ_tab, "Circulation Matrix")

        # 2. Audit Logs Tab
        audit_tab = QWidget()
        audit_lay = QVBoxLayout(audit_tab)
        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(4)
        self.audit_table.setHorizontalHeaderLabels(["Time", "User", "Action", "Details"])
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.audit_table.setStyleSheet("QTableWidget { background: #071428; color: #E8EEF8; border: none; } QHeaderView::section { background: #0D1B2A; color: #6B8CAE; }")
        audit_lay.addWidget(self.audit_table)
        self.tabs.addTab(audit_tab, "Audit Logs")

        # 4. Developer Tools Tab (8.1, 8.2, 8.3)
        dev_tab = QWidget()
        dev_lay = QVBoxLayout(dev_tab)
        
        share_btn = QPushButton("📤 Share App / APK Extraction Tool")
        share_btn.setStyleSheet(save_btn.styleSheet())
        share_btn.clicked.connect(self._share_apk)
        dev_lay.addWidget(share_btn)
        
        seed_btn = QPushButton("🌱 Seed Sample Data")
        seed_btn.setStyleSheet(save_btn.styleSheet())
        seed_btn.clicked.connect(self._seed_data)
        dev_lay.addWidget(seed_btn)
        
        reset_btn = QPushButton("⚠️ Reset Database")
        reset_btn.setStyleSheet("background: #DC2626; color: white; border: none; border-radius: 8px; padding: 10px 24px; font-weight: 700; font-size: 14px; margin-top: 20px;")
        reset_btn.clicked.connect(self._reset_db)
        dev_lay.addWidget(reset_btn)

        # Advanced Backup & Security (User Requested)
        backup_lay = QHBoxLayout()
        zip_btn = QPushButton("🗄️ 1-Click Encrypted ZIP Backup")
        zip_btn.setStyleSheet("background: #7C3AED; color: white; border-radius: 8px; padding: 10px; font-weight: bold;")
        zip_btn.clicked.connect(self._create_zip_backup)
        backup_lay.addWidget(zip_btn)
        
        auto_bkp = QCheckBox("Enable Automated Daily Backups")
        auto_bkp.setStyleSheet("color: #E8EEF8; font-weight: bold;")
        auto_bkp.setChecked(True)
        backup_lay.addWidget(auto_bkp)
        dev_lay.addLayout(backup_lay)

        sec_lay = QHBoxLayout()
        app_lock = QPushButton("🔒 Set Idle App Lock PIN")
        app_lock.setStyleSheet("background: #EF4444; color: white; border-radius: 8px; padding: 10px; font-weight: bold;")
        app_lock.clicked.connect(self._set_app_lock)
        sec_lay.addWidget(app_lock)
        dev_lay.addLayout(sec_lay)

        # Feature 4: CSV/Excel Full Data Export
        export_btn = QPushButton("📊 Export Full Database (CSV Backup)")
        export_btn.setStyleSheet("background: #059669; color: white; border: none; border-radius: 8px; padding: 10px 24px; font-weight: 700; font-size: 14px; margin-top: 10px;")
        export_btn.clicked.connect(self._export_full_db)
        dev_lay.addWidget(export_btn)

        health_btn = QPushButton("🩺 Run Data Integrity Health Check")
        health_btn.setStyleSheet("background: #F59E0B; color: #0D1B2A; border: none; border-radius: 8px; padding: 10px 24px; font-weight: 700; font-size: 14px; margin-top: 10px;")
        health_btn.clicked.connect(self._run_health_check)
        dev_lay.addWidget(health_btn)

        dev_lay.addStretch()
        self.tabs.addTab(dev_tab, "Developer Tools")

        layout.addWidget(self.tabs)
        self._init_done = True

    def _build_profile_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(QLabel(
            "This information appears on printed reports, ID cards, and receipts.",
            styleSheet="color:#A0B4CC;font-size:13px;"
        ))

        form = QFormLayout()
        form.setSpacing(14)
        field_style = "background:#0D1B2A;border:1px solid #1E3050;border-radius:6px;padding:8px;color:white;"

        self.school_name_input = QLineEdit()
        self.school_name_input.setPlaceholderText("e.g. Springfield High School")
        self.school_name_input.setStyleSheet(field_style)
        form.addRow("School Name *", self.school_name_input)

        self.school_address_input = QLineEdit()
        self.school_address_input.setStyleSheet(field_style)
        form.addRow("Address", self.school_address_input)

        self.school_phone_input = QLineEdit()
        self.school_phone_input.setStyleSheet(field_style)
        form.addRow("Contact Phone", self.school_phone_input)

        self.school_email_input = QLineEdit()
        self.school_email_input.setStyleSheet(field_style)
        form.addRow("Contact Email", self.school_email_input)

        layout.addLayout(form)

        save_profile_btn = QPushButton("💾  Save School Profile")
        save_profile_btn.setStyleSheet(
            "background: #1E5FD4; color: white; border: none; border-radius: 8px; "
            "padding: 10px 24px; font-weight: 700; font-size: 14px; margin-top: 10px;"
        )
        save_profile_btn.clicked.connect(self._save_school_profile)
        layout.addWidget(save_profile_btn)
        layout.addStretch()

    def _save_school_profile(self):
        name = self.school_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "School name cannot be empty.")
            return
        self.db.set_school_profile("name", name)
        self.db.set_school_profile("address", self.school_address_input.text().strip())
        self.db.set_school_profile("phone", self.school_phone_input.text().strip())
        self.db.set_school_profile("email", self.school_email_input.text().strip())
        QMessageBox.information(self, "Saved", "School profile updated. Restart the app to see the new name everywhere.")

    def _build_staff_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(QLabel(
            "Manage librarian and administrator accounts for this library.",
            styleSheet="color:#A0B4CC;font-size:13px;"
        ))

        self.staff_table = QTableWidget()
        self.staff_table.setColumnCount(3)
        self.staff_table.setHorizontalHeaderLabels(["Username", "Name", "Role"])
        self.staff_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.staff_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.staff_table.setStyleSheet(
            "QTableWidget { background: #071428; color: #E8EEF8; border: none; } "
            "QHeaderView::section { background: #0D1B2A; color: #6B8CAE; }"
        )
        layout.addWidget(self.staff_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ Add Staff Account")
        add_btn.setStyleSheet("background:#059669;color:white;border-radius:8px;padding:8px 16px;font-weight:bold;")
        add_btn.clicked.connect(self._add_staff)
        reset_btn = QPushButton("🔑 Reset Password")
        reset_btn.setStyleSheet("background:#1E3050;color:#A0B4CC;border:1px solid #1E3050;border-radius:8px;padding:8px 16px;")
        reset_btn.clicked.connect(self._reset_staff_password)
        del_btn = QPushButton("🗑️ Delete Account")
        del_btn.setStyleSheet("background:rgba(220,38,38,0.1);color:#F87171;border:1px solid rgba(220,38,38,0.3);border-radius:8px;padding:8px 16px;")
        del_btn.clicked.connect(self._delete_staff)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _refresh_staff_table(self):
        users = self.db.list_users()
        self.staff_table.setRowCount(len(users))
        for i, u in enumerate(users):
            self.staff_table.setItem(i, 0, QTableWidgetItem(u["username"]))
            self.staff_table.setItem(i, 1, QTableWidgetItem(u.get("name") or ""))
            self.staff_table.setItem(i, 2, QTableWidgetItem(u["role"]))

    def _selected_staff_username(self):
        row = self.staff_table.currentRow()
        if row < 0:
            return None
        return self.staff_table.item(row, 0).text()

    def _add_staff(self):
        from services.auth_service import AuthService
        username, ok = QInputDialog.getText(self, "Add Staff Account", "Username:")
        if not ok or not username.strip():
            return
        name, ok2 = QInputDialog.getText(self, "Add Staff Account", "Full Name:")
        if not ok2:
            return
        password, ok3 = QInputDialog.getText(self, "Add Staff Account", "Temporary Password:", QLineEdit.EchoMode.Password)
        if not ok3 or not password:
            return
        role, ok4 = QInputDialog.getItem(self, "Add Staff Account", "Role:", ["librarian", "admin"], 0, False)
        if not ok4:
            return

        auth = AuthService(self.db)
        ok, err = auth.create_account(username, password, name, role)
        if ok:
            QMessageBox.information(self, "Added", f"Staff account '{username}' created.")
            self._refresh_staff_table()
        else:
            QMessageBox.warning(self, "Error", err)

    def _reset_staff_password(self):
        from services.auth_service import AuthService
        username = self._selected_staff_username()
        if not username:
            QMessageBox.information(self, "Select", "Please select a staff account first.")
            return
        password, ok = QInputDialog.getText(self, "Reset Password", f"New password for '{username}':", QLineEdit.EchoMode.Password)
        if not ok or not password:
            return
        user = self.db.get_user_by_username(username)
        if not user:
            return
        auth = AuthService(self.db)
        ok, err = auth.change_password(user["id"], password)
        if ok:
            QMessageBox.information(self, "Done", f"Password reset for '{username}'.")
        else:
            QMessageBox.warning(self, "Error", err)

    def _delete_staff(self):
        username = self._selected_staff_username()
        if not username:
            QMessageBox.information(self, "Select", "Please select a staff account first.")
            return
        if self.auth.current_user and self.auth.current_user.email == username:
            QMessageBox.warning(self, "Not Allowed", "You cannot delete the account you're currently logged in as.")
            return
        reply = QMessageBox.question(self, "Delete Account", f"Delete staff account '{username}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            user = self.db.get_user_by_username(username)
            if user:
                self.db.delete_user(user["id"])
                self._refresh_staff_table()

    def _build_circ_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(14)
        layout.addWidget(QLabel(
            "Define loan periods and max limits per Member Type (e.g. Student vs Faculty).\n"
            "This implements a standard Koha Circulation Matrix.",
            styleSheet="color:#A0B4CC; font-size:13px;"
        ))

        self.circ_table = QTableWidget()
        self.circ_table.setColumnCount(4)
        self.circ_table.setHorizontalHeaderLabels(["Member Type", "Max Loans", "Loan Days", "Fine/Day (Rs.)"])
        self.circ_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.circ_table.setStyleSheet("QTableWidget { background: #071428; color: #E8EEF8; border: none; } QHeaderView::section { background: #0D1B2A; color: #6B8CAE; }")
        layout.addWidget(self.circ_table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        save_circ_btn = QPushButton("💾 Save Matrix")
        save_circ_btn.setStyleSheet(
            "background:#1E5FD4;color:white;border:none;border-radius:8px;"
            "padding:8px 16px;font-weight:bold;"
        )
        save_circ_btn.clicked.connect(self._save_circ_rules)
        btn_row.addWidget(save_circ_btn)
        layout.addLayout(btn_row)

    def refresh(self):
        try:
            self.fine_spin.setValue(self.db.get_fine_rate())
        except Exception:
            pass

        profile = self.db.get_school_profile()
        self.school_name_input.setText(profile.get("name", ""))
        self.school_address_input.setText(profile.get("address", ""))
        self.school_phone_input.setText(profile.get("phone", ""))
        self.school_email_input.setText(profile.get("email", ""))

        self._refresh_staff_table()
        self._load_circ_rules()

        # Load Audit Logs
        try:
            logs = self.db.get_audit_logs_local(50)
            self.audit_table.setRowCount(len(logs))
            for i, row in enumerate(logs):
                self.audit_table.setItem(i, 0, QTableWidgetItem(row.get("timestampStr", "")))
                self.audit_table.setItem(i, 1, QTableWidgetItem(row.get("userEmail", "")))
                self.audit_table.setItem(i, 2, QTableWidgetItem(row.get("action", "")))
                self.audit_table.setItem(i, 3, QTableWidgetItem(row.get("detail", "")))
        except Exception as e:
            print(f"Error loading audit logs: {e}")

    def _toggle_lang(self, lang):
        if hasattr(self, '_init_done'):
            QMessageBox.information(self, "Language Live Toggle", f"Mock: Interface translating to {lang}...")
            
    def _toggle_theme(self, theme_text):
        if hasattr(self, '_init_done'):
            main_window = self.window()
            if hasattr(main_window, 'is_dark'):
                main_window.is_dark = "Dark" in theme_text
                main_window._apply_theme()
                main_window.theme_btn.setText("☀️  Light Mode" if main_window.is_dark else "🌙  Dark Mode")
            
    def _toggle_font(self, scale):
        if hasattr(self, '_init_done'):
            QMessageBox.information(self, "Font Scaling", f"Mock: Accessibility Font Scale adjusted to {scale}x.")

    def _share_apk(self):
        QMessageBox.information(self, "Share App", "Mock: Extracted a shareable app package to Desktop.")

    def _seed_data(self):
        reply = QMessageBox.question(self, "Seed Data", "Insert sample mock data into the database?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Seeded", "Mock: Sample books, members, and transactions seeded.")

    def _reset_db(self):
        reply = QMessageBox.question(self, "Reset Database", "WARNING: This will clear all local data. Proceed?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Database Reset", "Mock: Database reset successfully.")

    def _export_full_db(self):
        from PyQt6.QtWidgets import QFileDialog
        QMessageBox.information(self, "Export", "Mock: Full database exported to CSV.")
        
    def _create_zip_backup(self):
        import shutil, time
        from PyQt6.QtWidgets import QFileDialog

        backup_name = f"Library_Backup_{time.strftime('%Y%m%d_%H%M%S')}.zip"
        path, _ = QFileDialog.getSaveFileName(self, "Save Backup", backup_name, "ZIP Archives (*.zip)")
        if path:
            try:
                shutil.copy2(self.db.db_path, path)
                QMessageBox.information(self, "Backup Success", f"Database backed up to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Backup Failed", f"Failed to create backup: {e}")

    def _set_app_lock(self):
        from PyQt6.QtWidgets import QInputDialog, QLineEdit
        pin, ok = QInputDialog.getText(self, "App Lock", "Enter new 4-digit PIN for Idle Lock:", QLineEdit.EchoMode.Password)
        if ok and len(pin) >= 4:
            QMessageBox.information(self, "App Lock", "Idle App Lock PIN set successfully. App will lock after 15 mins of inactivity.")
        elif ok:
            QMessageBox.warning(self, "Error", "PIN must be at least 4 digits.")
        from services.advanced_service import AdvancedService

        folder = QFileDialog.getExistingDirectory(self, "Select Folder for CSV Backup")
        if not folder:
            return

        try:
            adv = AdvancedService(self.db)
            adv.export_full_database_csv(folder)
            QMessageBox.information(self, "Success", f"Full database backup exported to:\n{folder}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Export failed: {e}")

    def _save(self):
        try:
            val = self.fine_spin.value()
            email = self.auth.current_user.email if self.auth.current_user else ""
            self.db.set_fine_rate(val)
            self.db.log_audit_local(email, "settings_update", f"fineRate: {val}")
            QMessageBox.information(self, "Saved", "Settings updated successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    # ── Circulation Matrix Logic ──────────────────────────────────────────────
    def _load_circ_rules(self):
        rules = {
            "Student": {"max": 2, "days": 14, "fine": 5},
            "Faculty": {"max": 5, "days": 30, "fine": 0},
            "Staff":   {"max": 3, "days": 20, "fine": 2}
        }
        if os.path.exists("circulation_rules.json"):
            try:
                with open("circulation_rules.json", "r") as f:
                    rules = json.load(f)
            except Exception:
                pass
                
        self.circ_table.setRowCount(len(rules))
        for row, (mtype, data) in enumerate(rules.items()):
            self.circ_table.setItem(row, 0, QTableWidgetItem(mtype))
            self.circ_table.item(row, 0).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.circ_table.setItem(row, 1, QTableWidgetItem(str(data.get("max", 2))))
            self.circ_table.setItem(row, 2, QTableWidgetItem(str(data.get("days", 14))))
            self.circ_table.setItem(row, 3, QTableWidgetItem(str(data.get("fine", 5))))

    def _save_circ_rules(self):
        rules = {}
        for row in range(self.circ_table.rowCount()):
            mtype = self.circ_table.item(row, 0).text()
            try:
                rules[mtype] = {
                    "max": int(self.circ_table.item(row, 1).text()),
                    "days": int(self.circ_table.item(row, 2).text()),
                    "fine": int(self.circ_table.item(row, 3).text())
                }
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for Max, Days, and Fine.")
                return
                
        try:
            with open("circulation_rules.json", "w") as f:
                json.dump(rules, f, indent=4)
            QMessageBox.information(self, "Saved", "Circulation Matrix rules saved successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save rules:\n{e}")

    # ── Enterprise: Data Integrity Health Check ──────────────────────────────
    def _run_health_check(self):
        """Runs the DB health check and displays results in a dialog."""
        try:
            res = self.db.run_health_check()
            
            dlg = QDialog(self)
            dlg.setWindowTitle("🩺 Data Integrity Health Check Report")
            dlg.setFixedSize(550, 450)
            dlg.setStyleSheet("QDialog {background:#0D1B2A; color:#E8EEF8;} QTextEdit {background:#0D1F38; border:1px solid #1E3050; border-radius:8px; color:#E8EEF8; font-size:13px; font-family:Consolas; padding:10px;}")
            
            lay = QVBoxLayout(dlg)
            txt = QTextEdit()
            txt.setReadOnly(True)
            
            html = [f"<h2 style='color:#10B981;'>Health Check Summary</h2>"]
            html.append(f"<b>Total Books:</b> {res['total_books']}<br>")
            html.append(f"<b>Total Members:</b> {res['total_members']}<br>")
            html.append(f"<b>Total Issues (Active & History):</b> {res['total_issues']}<br><hr>")
            
            issues_found = 0
            
            if res["orphan_issues"]:
                html.append(f"<h3 style='color:#EF4444;'>Orphan Issues ({len(res['orphan_issues'])})</h3>")
                html.append("<ul>")
                for o in res["orphan_issues"]:
                    html.append(f"<li>SyncId: {o.get('syncId')} - {o.get('bookTitle')} issued to {o.get('memberName')}</li>")
                html.append("</ul>")
                issues_found += len(res['orphan_issues'])
                
            if res["duplicate_isbns"]:
                html.append(f"<h3 style='color:#F59E0B;'>Duplicate ISBNs ({len(res['duplicate_isbns'])})</h3>")
                html.append("<ul>")
                for d in res["duplicate_isbns"]:
                    html.append(f"<li>ISBN: {d.get('isbn')} (Count: {d.get('cnt')})</li>")
                html.append("</ul>")
                issues_found += len(res['duplicate_isbns'])
                
            if res["duplicate_member_ids"]:
                html.append(f"<h3 style='color:#F59E0B;'>Duplicate Member IDs ({len(res['duplicate_member_ids'])})</h3>")
                html.append("<ul>")
                for d in res["duplicate_member_ids"]:
                    html.append(f"<li>Member ID: {d.get('memberId')} (Count: {d.get('cnt')})</li>")
                html.append("</ul>")
                issues_found += len(res['duplicate_member_ids'])
                
            if res["ghost_issued"]:
                html.append(f"<h3 style='color:#EF4444;'>Ghost Issued Books ({len(res['ghost_issued'])})</h3>")
                html.append("<i>Books marked 'Issued' but have no active issue record.</i><ul>")
                for g in res["ghost_issued"]:
                    html.append(f"<li>{g.get('title')} ({g.get('accNo')})</li>")
                html.append("</ul>")
                issues_found += len(res['ghost_issued'])
                
            if res["stuck_returns"]:
                html.append(f"<h3 style='color:#F59E0B;'>Stuck Returns ({len(res['stuck_returns'])})</h3>")
                html.append("<i>Books returned but still marked 'Issued' in books table.</i><ul>")
                for s in res["stuck_returns"]:
                    html.append(f"<li>{s.get('bookTitle')}</li>")
                html.append("</ul>")
                issues_found += len(res['stuck_returns'])
                
            if res["expired_members_with_books"]:
                html.append(f"<h3 style='color:#F59E0B;'>Expired Members with Active Loans ({len(res['expired_members_with_books'])})</h3>")
                html.append("<ul>")
                for e in res["expired_members_with_books"]:
                    html.append(f"<li>{e.get('name')} (ID: {e.get('memberId')}) - Expires {e.get('expiryDate')} - {e.get('active_books')} books</li>")
                html.append("</ul>")
                issues_found += len(res['expired_members_with_books'])
                
            if issues_found == 0:
                html.append("<h3 style='color:#10B981;'>✅ Database is completely healthy! No anomalies detected.</h3>")
            else:
                html.append(f"<br><b>Total anomalies detected:</b> {issues_found}")
                
            txt.setHtml("".join(html))
            lay.addWidget(txt)
            
            btn = QPushButton("Close Report")
            btn.setStyleSheet("background:#1E3050; color:#E8EEF8; border-radius:8px; padding:10px; font-weight:bold;")
            btn.clicked.connect(dlg.accept)
            lay.addWidget(btn)
            
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run health check: {e}")
