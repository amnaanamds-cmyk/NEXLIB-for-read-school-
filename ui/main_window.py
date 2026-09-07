"""
ui/main_window.py
Main application window with collapsible sidebar, dark/light theme toggle,
inactivity auto-logout timer, and role-based navigation. Fully offline —
everything reads and writes the local SQLite database only.
"""
import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
    QSizePolicy, QSpacerItem, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon

import config


class NavButton(QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(f"  {icon}  {label}", parent)
        self.setObjectName("navBtn")
        self.setMinimumHeight(44)
        self.setCheckable(False)
        self._active = False

    def set_active(self, val: bool):
        self._active = val
        self.setProperty("active", "true" if val else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    NAV_ITEMS = [
        ("🏠", "Dashboard",       "dashboard"),
        ("📚", "Books",           "books"),
        ("👥", "Members",         "members"),
        ("📋", "Issue / Return",  "issue_return"),
        ("🔍", "OPAC Monitor",    "opac"),
        ("📦", "Inventory",       "inventory"),
        ("🌍", "ILL Network",     "ill"),
        ("💰", "Acquisitions",    "acquisitions"),
        ("📰", "Serials",         "serials"),
        ("🚀", "Enterprise Feat.", "enterprise"),
        ("📊", "Reports",         "reports"),
        ("⚙️", "Settings",        "settings"),
    ]

    def __init__(self, auth_service, db_helper):
        super().__init__()
        self.auth = auth_service
        self.db = db_helper
        self.is_dark = (config.DEFAULT_THEME == "dark")
        self.current_screen = ""
        self._nav_btns = {}

        # Inactivity timer
        self._last_activity = time.time()
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._check_inactivity)
        self._idle_timer.start(30_000)  # check every 30 s

        self.setWindowTitle(f"{self.db.get_school_name()} — {config.APP_NAME}")
        self.setMinimumSize(1280, 800)
        self._build_ui()
        self._apply_theme()

        self.navigate_to("dashboard")

        # Setup Power User Keyboard Shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        from PyQt6.QtGui import QKeySequence, QShortcut
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self._cmd_search)
        QShortcut(QKeySequence("Ctrl+M"), self).activated.connect(self._cmd_add_member)
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._cmd_add_book)
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(self._cmd_issue)
        QShortcut(QKeySequence("F5"), self).activated.connect(self._cmd_refresh)
        QShortcut(QKeySequence("F1"), self).activated.connect(self._cmd_opac_kiosk)

    def _cmd_search(self):
        if self.current_screen in ("books", "members", "opac"):
            screen = self._screens[self.current_screen]
            if hasattr(screen, "search_bar"):
                screen.search_bar.setFocus()
            elif hasattr(screen, "search_input"):
                screen.search_input.setFocus()

    def _cmd_add_member(self):
        self.navigate_to("members")
        if hasattr(self._screens["members"], "_add_member"):
            self._screens["members"]._add_member()

    def _cmd_add_book(self):
        self.navigate_to("books")
        if hasattr(self._screens["books"], "_add_book"):
            self._screens["books"]._add_book()

    def _cmd_issue(self):
        self.navigate_to("issue_return")
        if hasattr(self._screens["issue_return"], "_issue_book"):
            self._screens["issue_return"]._issue_book()

    def _cmd_refresh(self):
        screen = self._screens.get(self.current_screen)
        if hasattr(screen, "refresh"):
            screen.refresh()

    def _cmd_opac_kiosk(self):
        self.navigate_to("opac")
        if hasattr(self._screens["opac"], "_open_kiosk"):
            self._screens["opac"]._open_kiosk()

    # ── UI Construction ────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(12, 16, 12, 16)
        sb_layout.setSpacing(4)

        # Brand
        brand = QLabel(f"📚 {self.db.get_school_name()}")
        brand.setObjectName("appBrand")
        brand.setWordWrap(True)
        sb_layout.addWidget(brand)

        # User info
        user = self.auth.current_user
        role_badge = user.role.upper() if user else "UNKNOWN"
        self.user_lbl = QLabel(f"👤 {user.name or user.email}\n🔑 {role_badge}")
        self.user_lbl.setObjectName("userInfo")
        self.user_lbl.setWordWrap(True)
        sb_layout.addWidget(self.user_lbl)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #1E3050; margin: 8px 0;")
        sb_layout.addWidget(divider)

        # Nav buttons
        for icon, label, key in self.NAV_ITEMS:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda _, k=key: self.navigate_to(k))
            self._nav_btns[key] = btn
            sb_layout.addWidget(btn)

        sb_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum,
                                            QSizePolicy.Policy.Expanding))

        # Status
        self.status_lbl = QLabel("💾  Local Database")
        self.status_lbl.setObjectName("statusBar")
        self.status_lbl.setStyleSheet("color: #2EC98A;")
        sb_layout.addWidget(self.status_lbl)

        # Theme toggle
        self.theme_btn = QPushButton("☀️  Light Mode" if self.is_dark else "🌙  Dark Mode")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.clicked.connect(self._toggle_theme)
        sb_layout.addWidget(self.theme_btn)

        # Logout
        logout_btn = QPushButton("🚪  Logout")
        logout_btn.setObjectName("logoutBtn")
        logout_btn.clicked.connect(self._do_logout)
        sb_layout.addWidget(logout_btn)

        root.addWidget(self.sidebar)

        # Content area
        self.stack = QStackedWidget()
        root.addWidget(self.stack)
        self._init_screens()

    def _init_screens(self):
        """Lazily import and add all screens."""
        from ui.screens.dashboard_screen import DashboardScreen
        from ui.screens.books_screen import BooksScreen
        from ui.screens.members_screen import MembersScreen
        from ui.screens.issue_return_screen import IssueReturnScreen
        from ui.screens.opac_screen import OpacScreen
        from ui.screens.reports_screen import ReportsScreen
        from ui.screens.settings_screen import SettingsScreen
        from ui.screens.inventory_screen import InventoryScreen
        from ui.screens.acquisitions_screen import AcquisitionsScreen
        from ui.screens.serials_screen import SerialsScreen
        from ui.screens.ill_screen import ILLScreen
        from ui.screens.enterprise_screen import EnterpriseFeaturesScreen

        self._screens = {
            "dashboard":   DashboardScreen(self.db),
            "books":       BooksScreen(self.db, self.auth),
            "members":     MembersScreen(self.db, self.auth),
            "issue_return": IssueReturnScreen(self.db, self.auth),
            "opac":        OpacScreen(self.db),
            "inventory":   InventoryScreen(self.db),
            "ill":         ILLScreen(self.db),
            "acquisitions": AcquisitionsScreen(self.db),
            "serials":     SerialsScreen(self.db),
            "enterprise":  EnterpriseFeaturesScreen(self.db),
            "reports":     ReportsScreen(self.db, self.auth),
            "settings":    SettingsScreen(self.db, self.auth),
        }

        from PyQt6.QtWidgets import QScrollArea
        self._scroll_areas = {}
        for key, screen in self._screens.items():
            # Force a minimum height for static screens to trigger scrolling in small windows
            if key in ("dashboard", "settings", "enterprise"):
                screen.setMinimumHeight(1000)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(screen)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            self.stack.addWidget(scroll)
            self._scroll_areas[key] = scroll

    # ── Navigation ────────────────────────────────────────────────────────────
    def navigate_to(self, key: str):
        if key not in self._scroll_areas:
            return

        self.current_screen = key
        self.stack.setCurrentWidget(self._scroll_areas[key])
        for k, btn in self._nav_btns.items():
            btn.set_active(k == key)

        # Refresh data on screen if it has a refresh method
        screen = self._screens[key]
        if hasattr(screen, "refresh"):
            screen.refresh()

    # ── Theme ─────────────────────────────────────────────────────────────────
    def _toggle_theme(self):
        self.is_dark = not self.is_dark
        self._apply_theme()
        self.theme_btn.setText("☀️  Light Mode" if self.is_dark else "🌙  Dark Mode")

    def _apply_theme(self):
        # Base QSS applied to entire app
        try:
            with open("assets/style.qss", "r") as f:
                base_qss = f.read()
        except Exception:
            base_qss = ""

        # Additional color palette injection
        if self.is_dark:
            colors = """
            QMainWindow, QWidget { background: #0D1B2A; color: #E8EEF8; font-family: 'Segoe UI'; }
            QFrame#sidebar { background: #071428; border-right: 1px solid #1E3050; }
            QPushButton#navBtn { background: transparent; color: #6B8CAE; border: none; text-align: left; padding: 12px; font-weight: bold; border-radius:8px; }
            QPushButton#navBtn:hover { background: rgba(30,95,212,0.15); color: #E8EEF8; }
            QPushButton#navBtn[active="true"] { background: rgba(30,95,212,0.25); color: #E6C96E; border-left: 3px solid #C8A84B; }
            QLabel#appBrand { color: #E6C96E; font-size: 16px; font-weight: 900; }
            """
        else:
            colors = """
            QMainWindow, QWidget { background: #F5F7FA; color: #1A1A2E; font-family: 'Segoe UI'; }
            QFrame#sidebar { background: #FFFFFF; border-right: 1px solid #E0E7EF; }
            QPushButton#navBtn { background: transparent; color: #6B7280; border: none; text-align: left; padding: 12px; font-weight: bold; border-radius:8px; }
            QPushButton#navBtn:hover { background: rgba(30,95,212,0.08); color: #1E5FD4; }
            QPushButton#navBtn[active="true"] { background: rgba(30,95,212,0.12); color: #1E5FD4; border-left: 3px solid #1E5FD4; }
            QLabel#appBrand { color: #1E5FD4; font-size: 16px; font-weight: 900; }
            """

        self.setStyleSheet(base_qss + colors)

    # ── Inactivity ────────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        self._last_activity = time.time()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        self._last_activity = time.time()
        super().keyPressEvent(event)

    def _check_inactivity(self):
        elapsed = time.time() - self._last_activity
        if elapsed > config.INACTIVITY_TIMEOUT:
            self._do_logout(auto=True)

    # ── Logout ────────────────────────────────────────────────────────────────
    def _do_logout(self, auto: bool = False):
        msg = ("You have been logged out due to inactivity."
               if auto else "Are you sure you want to log out?")
        if not auto:
            reply = QMessageBox.question(self, "Logout", msg,
                                         QMessageBox.StandardButton.Yes |
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        self.auth.sign_out()
        self._idle_timer.stop()
        self.logout_requested.emit()
