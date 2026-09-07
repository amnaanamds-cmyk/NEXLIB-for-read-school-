"""
ui/login_screen.py — Premium dark-themed login screen.
Authenticates against local staff accounts stored in the SQLite database.
Fully offline — no network calls of any kind.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

import config


class LoginWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, auth_service, username, password):
        super().__init__()
        self.auth = auth_service
        self.username = username
        self.password = password

    def run(self):
        ok, err = self.auth.sign_in(self.username, self.password)
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
    """

    def __init__(self, auth_service, db_helper):
        super().__init__()
        self.auth = auth_service
        self.db = db_helper
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

        title = QLabel(self.db.get_school_name())
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("LIBRARY MANAGEMENT SYSTEM")
        subtitle.setObjectName("appSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        divider = QFrame()
        divider.setFixedHeight(2)
        divider.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                               "stop:0 transparent, stop:0.5 #C8A84B, stop:1 transparent);")
        card_layout.addWidget(divider)

        username_lbl = QLabel("USERNAME")
        username_lbl.setObjectName("fieldLabel")
        card_layout.addWidget(username_lbl)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("your.username")
        card_layout.addWidget(self.username_input)

        pw_lbl = QLabel("PASSWORD")
        pw_lbl.setObjectName("fieldLabel")
        card_layout.addWidget(pw_lbl)
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
        card_layout.addLayout(pw_row)

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
        self.login_btn.clicked.connect(self._do_login)
        card_layout.addWidget(self.login_btn)

        # Status
        self.status_lbl = QLabel("\U0001f512  Role-Based Security Active")
        self.status_lbl.setObjectName("statusLabel")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_lbl)

        root_layout.addWidget(card)

        note = QLabel(f"{self.db.get_school_name()}  ·  {config.APP_NAME} v{config.APP_VERSION}")
        note.setStyleSheet("color: #2A3A50; font-size: 10px; font-family: 'Segoe UI';")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(note)

    def _toggle_password_visibility(self):
        self._pw_visible = not self._pw_visible
        mode = QLineEdit.EchoMode.Normal if self._pw_visible else QLineEdit.EchoMode.Password
        self.pw_input.setEchoMode(mode)
        self._pw_toggle_btn.setText("\U0001f441\U0001f441" if self._pw_visible else "\U0001f441")

    def _do_login(self):
        username = self.username_input.text().strip()
        password = self.pw_input.text()
        if not username or not password:
            self._show_error("Please enter your username and password.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in…")
        self.error_lbl.hide()

        self.worker = LoginWorker(self.auth, username, password)
        self.worker.finished.connect(self._on_login_result)
        self.worker.start()

    def _on_login_result(self, success: bool, error: str):
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Sign In")
        if success:
            role = self.auth.current_user.role if self.auth.current_user else "librarian"
            self.login_success.emit(role)
        else:
            self._show_error(f"⚠  {error}")

    def _show_error(self, msg: str):
        self.error_lbl.setText(msg)
        self.error_lbl.show()

    def try_auto_login(self):
        """No persisted sessions in fully-offline mode; always show the login form."""
        return False
