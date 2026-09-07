"""
ui/login_screen.py — Premium dark-themed login screen with role-based routing.
Supports: Email/Password login, Admin PIN (1234), Librarian PIN (0000),
          Password visibility toggle, biometric placeholder.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame, QGraphicsDropShadowEffect,
    QStackedWidget, QTabBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class LoginWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, auth_service, email, password, remember):
        super().__init__()
        self.auth = auth_service
        self.email = email
        self.password = password
        self.remember = remember

    def run(self):
        ok, err = self.auth.sign_in(self.email, self.password, self.remember)
        self.finished.emit(ok, err)


class LoginScreen(QWidget):
    login_success = pyqtSignal(str)

    STYLE = """
    QWidget#loginRoot {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #060C18, stop:0.5 #0D1B2A, stop:1 #060C18);
    }
    QFrame#card {
        background: rgba(13,28,55,0.95);
        border-radius: 20px;
        border: 1px solid rgba(30,80,160,0.5);
    }
    QLabel#appTitle {
        color: #E6C96E;
        font-size: 26px;
        font-weight: 900;
        font-family: 'Segoe UI';
    }
    QLabel#appSubtitle {
        color: #4D6A90;
        font-size: 11px;
        font-family: 'Segoe UI';
        letter-spacing: 2px;
    }
    QLabel#fieldLabel {
        color: #A0B4CC;
        font-size: 11px;
        font-weight: 700;
        font-family: 'Segoe UI';
        letter-spacing: 1px;
    }
    QLineEdit {
        background: #0D1F38;
        border: 1.5px solid #1E3050;
        border-radius: 10px;
        padding: 12px 16px;
        color: #E8EEF8;
        font-size: 14px;
        font-family: 'Segoe UI';
        selection-background-color: #1E5FD4;
    }
    QLineEdit:focus {
        border: 1.5px solid #C8A84B;
        background: #0F2444;
    }
    QPushButton#loginBtn {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #1E5FD4, stop:1 #2872F0);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 14px;
        font-size: 15px;
        font-weight: 700;
        font-family: 'Segoe UI';
    }
    QPushButton#loginBtn:hover {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #2872F0, stop:1 #3D8EFF);
    }
    QPushButton#loginBtn:disabled {
        background: #2A3A50;
        color: #4D6A90;
    }
    QPushButton#togglePw {
        background: transparent;
        border: none;
        color: #6B8CAE;
        font-size: 16px;
        padding: 4px 8px;
    }
    QPushButton#togglePw:hover {
        color: #E6C96E;
    }
    QPushButton#pinBtn {
        background: rgba(200,168,75,0.15);
        color: #C8A84B;
        border: 1px solid rgba(200,168,75,0.4);
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 12px;
        font-weight: 600;
        font-family: 'Segoe UI';
    }
    QPushButton#pinBtn:hover {
        background: rgba(200,168,75,0.25);
    }
    QPushButton#pinBtn[active="true"] {
        background: rgba(200,168,75,0.35);
        border: 1px solid #C8A84B;
    }
    QCheckBox {
        color: #6B8CAE;
        font-size: 12px;
        font-family: 'Segoe UI';
    }
    QCheckBox::indicator:checked {
        background: #1E5FD4;
        border-radius: 3px;
    }
    QLabel#errorLabel {
        color: #F08080;
        font-size: 12px;
        background: rgba(224,82,82,0.1);
        border: 1px solid rgba(224,82,82,0.3);
        border-radius: 8px;
        padding: 8px;
        font-family: 'Segoe UI';
    }
    QLabel#statusLabel {
        color: #2EC98A;
        font-size: 11px;
        font-family: 'Segoe UI';
    }
    QLabel#biometricLabel {
        color: #4D6A90;
        font-size: 11px;
        font-family: 'Segoe UI';
        font-style: italic;
    }
    """

    def __init__(self, auth_service):
        super().__init__()
        self.auth = auth_service
        self.worker = None
        self._pw_visible = False
        self.setObjectName("loginRoot")
        self.setStyleSheet(self.STYLE)
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(440)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(60)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(12)

        icon = QLabel("\U0001f4da")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 48px; margin-bottom: 4px;")
        card_layout.addWidget(icon)

        title = QLabel("GDC Library50")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("DESKTOP MANAGEMENT SYSTEM")
        subtitle.setObjectName("appSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        divider = QFrame()
        divider.setFixedHeight(2)
        divider.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                               "stop:0 transparent, stop:0.5 #C8A84B, stop:1 transparent);")
        card_layout.addWidget(divider)

        # ── Login Mode Tabs (Email/PIN) ──
        mode_row = QHBoxLayout()
        self._email_mode_btn = QPushButton("Email / Password")
        self._pin_mode_btn = QPushButton("PIN Login")
        for btn in (self._email_mode_btn, self._pin_mode_btn):
            btn.setObjectName("pinBtn")
            btn.clicked.connect(lambda _, b=btn: self._switch_mode(b))
            mode_row.addWidget(btn)
        card_layout.addLayout(mode_row)

        # ── Stacked Widget for Email vs PIN modes ──
        self._login_stack = QStackedWidget()

        # Page 0: Email/Password
        email_page = QWidget()
        ep_lay = QVBoxLayout(email_page)
        ep_lay.setContentsMargins(0, 0, 0, 0)
        ep_lay.setSpacing(10)

        email_lbl = QLabel("EMAIL ADDRESS")
        email_lbl.setObjectName("fieldLabel")
        ep_lay.addWidget(email_lbl)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("admin@college.edu")
        ep_lay.addWidget(self.email_input)

        pw_lbl = QLabel("PASSWORD")
        pw_lbl.setObjectName("fieldLabel")
        ep_lay.addWidget(pw_lbl)
        pw_row = QHBoxLayout()
        self.pw_input = QLineEdit()
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_input.setPlaceholderText("••••••••")
        self.pw_input.returnPressed.connect(self._do_login)
        pw_row.addWidget(self.pw_input, stretch=1)

        self._pw_toggle_btn = QPushButton("\U0001f441")
        self._pw_toggle_btn.setObjectName("togglePw")
        self._pw_toggle_btn.setFixedWidth(40)
        self._pw_toggle_btn.setToolTip("Show/Hide Password")
        self._pw_toggle_btn.clicked.connect(self._toggle_password_visibility)
        pw_row.addWidget(self._pw_toggle_btn)
        ep_lay.addLayout(pw_row)

        self.remember_cb = QCheckBox("Remember me")
        ep_lay.addWidget(self.remember_cb)
        self._login_stack.addWidget(email_page)

        # Page 1: PIN Login
        pin_page = QWidget()
        pp_lay = QVBoxLayout(pin_page)
        pp_lay.setContentsMargins(0, 0, 0, 0)
        pp_lay.setSpacing(10)

        pin_info = QLabel("Enter your 4-digit PIN to login.\nAdmin PIN: 1234 | Librarian PIN: 0000")
        pin_info.setObjectName("biometricLabel")
        pin_info.setWordWrap(True)
        pp_lay.addWidget(pin_info)

        pin_lbl = QLabel("ACCESS PIN")
        pin_lbl.setObjectName("fieldLabel")
        pp_lay.addWidget(pin_lbl)
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setPlaceholderText("••••")
        self.pin_input.setMaxLength(4)
        self.pin_input.returnPressed.connect(self._do_pin_login)
        pp_lay.addWidget(self.pin_input)
        self._login_stack.addWidget(pin_page)

        card_layout.addWidget(self._login_stack)

        # Error label
        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("errorLabel")
        self.error_lbl.setWordWrap(True)
        self.error_lbl.hide()
        card_layout.addWidget(self.error_lbl)

        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setObjectName("loginBtn")
        self.login_btn.setMinimumHeight(50)
        self.login_btn.clicked.connect(self._do_action)
        card_layout.addWidget(self.login_btn)

        # Biometric button (Simulated for 1.1 & 1.2)
        self.bio_btn = QPushButton("\U0001f4b0  Biometric / Windows Hello Unlock")
        self.bio_btn.setObjectName("pinBtn")
        self.bio_btn.clicked.connect(self._do_biometric_login)
        card_layout.addWidget(self.bio_btn)

        # Status
        self.status_lbl = QLabel("\U0001f512  Role-Based Security Active")
        self.status_lbl.setObjectName("statusLabel")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_lbl)

        root_layout.addWidget(card)

        note = QLabel("Government Degree College Ziam Sherpao  \u00b7  Library System v1.0")
        note.setStyleSheet("color: #2A3A50; font-size: 10px; font-family: 'Segoe UI';")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(note)

        # Set initial mode
        self._switch_mode(self._email_mode_btn)

    def _switch_mode(self, active_btn):
        is_pin = active_btn is self._pin_mode_btn
        self._login_stack.setCurrentIndex(1 if is_pin else 0)
        self._email_mode_btn.setProperty("active", "true" if not is_pin else "false")
        self._pin_mode_btn.setProperty("active", "true" if is_pin else "false")
        for btn in (self._email_mode_btn, self._pin_mode_btn):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if is_pin:
            self.login_btn.setText("Login with PIN")
        else:
            self.login_btn.setText("Sign In")

    def _toggle_password_visibility(self):
        self._pw_visible = not self._pw_visible
        mode = QLineEdit.EchoMode.Normal if self._pw_visible else QLineEdit.EchoMode.Password
        self.pw_input.setEchoMode(mode)
        self._pw_toggle_btn.setText("\U0001f441\U0001f441" if self._pw_visible else "\U0001f441")

    def _do_action(self):
        if self._login_stack.currentIndex() == 1:
            self._do_pin_login()
        else:
            self._do_login()

    def _do_login(self):
        email = self.email_input.text().strip()
        password = self.pw_input.text()
        if not email or not password:
            self._show_error("Please enter your email and password.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in\u2026")
        self.error_lbl.hide()

        self.worker = LoginWorker(
            self.auth, email, password, self.remember_cb.isChecked()
        )
        self.worker.finished.connect(self._on_login_result)
        self.worker.start()

    def _do_pin_login(self):
        pin = self.pin_input.text().strip()
        if not pin:
            self._show_error("Please enter your 4-digit PIN.")
            return
        if not pin.isdigit() or len(pin) != 4:
            self._show_error("PIN must be exactly 4 digits.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Authenticating\u2026")
        self.error_lbl.hide()

        # Feature 1.4: Admin PIN = 1234, Feature 1.5: Librarian PIN = 0000
        if pin == "1234":
            self.auth._current_user = __import__("models.reservation", fromlist=["User"]).User(
                uid="pin-admin", email="admin@pin.local", name="Admin (PIN)", role="admin"
            )
            self.login_success.emit("admin")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Login with PIN")
        elif pin == "0000":
            self.auth._current_user = __import__("models.reservation", fromlist=["User"]).User(
                uid="pin-librarian", email="librarian@pin.local", name="Librarian (PIN)", role="librarian"
            )
            self.login_success.emit("librarian")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Login with PIN")
        else:
            self._show_error("Invalid PIN. Please try again.")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Login with PIN")

    def _do_biometric_login(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, 'Windows Hello', 'Simulate Biometric / Facial unlock?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            self.auth._current_user = __import__("models.reservation", fromlist=["User"]).User(
                uid="bio-admin", email="admin@bio.local", name="Admin (Biometric)", role="admin"
            )
            self.login_success.emit("admin")

    def _on_login_result(self, success: bool, error: str):
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Sign In")
        if success:
            role = self.auth.current_user.role if self.auth.current_user else "admin"
            self.login_success.emit(role)
        else:
            self._show_error(f"\u26a0  {error}")

    def _show_error(self, msg: str):
        self.error_lbl.setText(msg)
        self.error_lbl.show()

    def try_auto_login(self):
        if self.auth.try_restore_session():
            role = self.auth.current_user.role if self.auth.current_user else "admin"
            self.login_success.emit(role)
