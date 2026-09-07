"""
ui/setup_wizard.py — First-run setup screen.
Runs once, the very first time the app is opened on a machine: collects the
school's profile and creates the first administrator account. After that,
the app always goes straight to the login screen. Nothing here touches the
network — everything is written to the local SQLite database.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QGraphicsDropShadowEffect, QDoubleSpinBox,
    QFormLayout, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

import config


class SetupWizard(QWidget):
    setup_complete = pyqtSignal()

    STYLE = """
    QWidget#setupRoot {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #060C18, stop:0.5 #0D1B2A, stop:1 #060C18);
    }
    QFrame#card {
        background: rgba(13,28,55,0.95);
        border-radius: 20px;
        border: 1px solid rgba(30,80,160,0.5);
    }
    QLabel#title { color: #E6C96E; font-size: 24px; font-weight: 900; font-family: 'Segoe UI'; }
    QLabel#subtitle { color: #4D6A90; font-size: 12px; font-family: 'Segoe UI'; }
    QLabel#sectionLbl { color: #C8A84B; font-size: 14px; font-weight: 700; font-family: 'Segoe UI'; margin-top: 10px; }
    QLabel#fieldLabel { color: #A0B4CC; font-size: 12px; font-family: 'Segoe UI'; }
    QLineEdit, QDoubleSpinBox {
        background: #0D1F38; border: 1.5px solid #1E3050; border-radius: 8px;
        padding: 10px 12px; color: #E8EEF8; font-size: 13px; font-family: 'Segoe UI';
    }
    QLineEdit:focus, QDoubleSpinBox:focus { border: 1.5px solid #C8A84B; }
    QPushButton#createBtn {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1E5FD4, stop:1 #2872F0);
        color: white; border: none; border-radius: 10px; padding: 14px;
        font-size: 15px; font-weight: 700; font-family: 'Segoe UI';
    }
    QPushButton#createBtn:hover {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2872F0, stop:1 #3D8EFF);
    }
    QLabel#errorLabel {
        color: #F08080; font-size: 12px; background: rgba(224,82,82,0.1);
        border: 1px solid rgba(224,82,82,0.3); border-radius: 8px; padding: 8px;
        font-family: 'Segoe UI';
    }
    """

    def __init__(self, db_helper, auth_service):
        super().__init__()
        self.db = db_helper
        self.auth = auth_service
        self.setObjectName("setupRoot")
        self.setStyleSheet(self.STYLE)
        self._build_ui()

    def _field(self, placeholder="", password=False):
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        if password:
            f.setEchoMode(QLineEdit.EchoMode.Password)
        return f

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(480)
        card.setMaximumHeight(680)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(60)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 32, 36, 32)
        card_layout.setSpacing(6)

        icon = QLabel("📚")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 44px;")
        card_layout.addWidget(icon)

        title = QLabel(f"Welcome to {config.APP_NAME}")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("Let's set up your library — this only happens once.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        form_host = QWidget()
        form_lay = QVBoxLayout(form_host)
        form_lay.setContentsMargins(0, 10, 0, 0)
        form_lay.setSpacing(8)

        form_lay.addWidget(QLabel("SCHOOL / COLLEGE PROFILE", objectName="sectionLbl"))
        self.school_name = self._field("School or College Name *")
        self.school_address = self._field("Address (optional)")
        self.school_phone = self._field("Contact Phone (optional)")
        self.school_email = self._field("Contact Email (optional)")
        for w in (self.school_name, self.school_address, self.school_phone, self.school_email):
            form_lay.addWidget(w)

        self.fine_rate = QDoubleSpinBox()
        self.fine_rate.setRange(0, 1000)
        self.fine_rate.setPrefix("Rs. ")
        self.fine_rate.setValue(config.DEFAULT_FINE_RATE)
        fine_row = QFormLayout()
        fine_lbl = QLabel("Daily overdue fine rate")
        fine_lbl.setObjectName("fieldLabel")
        fine_row.addRow(fine_lbl, self.fine_rate)
        form_lay.addLayout(fine_row)

        form_lay.addWidget(QLabel("ADMINISTRATOR ACCOUNT", objectName="sectionLbl"))
        self.admin_name = self._field("Your Full Name *")
        self.admin_username = self._field("Choose a Username *")
        self.admin_password = self._field("Choose a Password *", password=True)
        self.admin_confirm = self._field("Confirm Password *", password=True)
        for w in (self.admin_name, self.admin_username, self.admin_password, self.admin_confirm):
            form_lay.addWidget(w)

        scroll.setWidget(form_host)
        card_layout.addWidget(scroll)

        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("errorLabel")
        self.error_lbl.setWordWrap(True)
        self.error_lbl.hide()
        card_layout.addWidget(self.error_lbl)

        create_btn = QPushButton("Create Library & Continue")
        create_btn.setObjectName("createBtn")
        create_btn.setMinimumHeight(50)
        create_btn.clicked.connect(self._do_setup)
        card_layout.addWidget(create_btn)

        outer.addWidget(card)

    def _show_error(self, msg):
        self.error_lbl.setText(f"⚠  {msg}")
        self.error_lbl.show()

    def _do_setup(self):
        school_name = self.school_name.text().strip()
        admin_name = self.admin_name.text().strip()
        username = self.admin_username.text().strip()
        password = self.admin_password.text()
        confirm = self.admin_confirm.text()

        if not school_name:
            self._show_error("Please enter your school or college name.")
            return
        if not admin_name or not username or not password:
            self._show_error("Please fill in all required administrator fields.")
            return
        if password != confirm:
            self._show_error("Passwords do not match.")
            return

        ok, err = self.auth.create_account(username, password, admin_name, "admin")
        if not ok:
            self._show_error(err)
            return

        self.db.set_school_profile("name", school_name)
        self.db.set_school_profile("address", self.school_address.text().strip())
        self.db.set_school_profile("phone", self.school_phone.text().strip())
        self.db.set_school_profile("email", self.school_email.text().strip())
        self.db.set_fine_rate(self.fine_rate.value())

        self.setup_complete.emit()
