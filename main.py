"""
main.py — Main entry point for the NexLib Desktop Application.
Fully offline: local SQLite only, no network calls. On first run it shows a
one-time setup wizard to create the school profile and the first
administrator account, then routes between Login and MainWindow.
"""
import sys
import traceback
import logging
import ctypes
from PyQt6.QtWidgets import QApplication, QStackedWidget, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFontDatabase, QFont

import config
from services.database_helper import DatabaseHelper
from services.auth_service import AuthService
from services.backup_service import BackupService
from ui.login_screen import LoginScreen
from ui.setup_wizard import SetupWizard
from ui.main_window import MainWindow

# Configure global logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("nexlib.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Feature: Force taskbar icon to show (AppUserModelID)
if sys.platform == 'win32':
    myappid = f"nexlib.desktop.v{config.APP_VERSION}"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

def _global_exception_handler(exc_type, exc_value, exc_tb):
    """Show a dialog for unhandled exceptions instead of silently crashing."""
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.critical(f"Unhandled exception: {msg}")
    try:
        dlg = QMessageBox()
        dlg.setWindowTitle("Unexpected Error")
        dlg.setText("An unexpected error occurred. The application may be unstable.")
        dlg.setDetailedText(msg)
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.exec()
    except Exception:
        pass


sys.excepthook = _global_exception_handler


class LibraryApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName(config.APP_NAME)
        self.setApplicationVersion(config.APP_VERSION)

        font = QFont("Segoe UI", 10)
        self.setFont(font)

        # Load Global Stylesheet
        try:
            with open("assets/style.qss", "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            logger.warning(f"Failed to load stylesheet: {e}")

        # Set Application Icon
        self.setWindowIcon(QIcon("assets/nexlib.ico"))

        # Initialize local services (no network access anywhere)
        self.db_helper = DatabaseHelper()
        self.auth_service = AuthService(self.db_helper)

        # Automated daily local backups
        self.backup_service = BackupService(self.db_helper)
        self.backup_service.start()

        # Setup main router (QStackedWidget) — a single application window
        self.router = QStackedWidget()
        self.router.setWindowTitle(f"{self.db_helper.get_school_name()} — {config.APP_NAME}")
        self.router.setMinimumSize(1024, 768)

        if self.auth_service.has_any_accounts():
            self._show_login()
        else:
            self._show_setup_wizard()

        self.router.show()

    def _show_setup_wizard(self):
        self.setup_wizard = SetupWizard(self.db_helper, self.auth_service)
        self.setup_wizard.setup_complete.connect(self._on_setup_complete)
        self.router.addWidget(self.setup_wizard)
        self.router.setCurrentWidget(self.setup_wizard)

    def _on_setup_complete(self):
        self.router.setWindowTitle(f"{self.db_helper.get_school_name()} — {config.APP_NAME}")
        self._show_login()
        self.router.removeWidget(self.setup_wizard)
        self.setup_wizard.deleteLater()
        self.setup_wizard = None

    def _show_login(self):
        self.login_screen = LoginScreen(self.auth_service, self.db_helper)
        self.login_screen.login_success.connect(self._on_login_success)
        self.router.addWidget(self.login_screen)
        self.router.setCurrentWidget(self.login_screen)

    def _on_login_success(self, role: str):
        try:
            self.main_window = MainWindow(self.auth_service, self.db_helper)
            self.main_window.logout_requested.connect(self._on_logout)

            self.router.addWidget(self.main_window)
            self.router.setCurrentWidget(self.main_window)
            self.router.resize(1366, 800)
        except Exception as e:
            logger.error("Login transition error", exc_info=True)
            QMessageBox.critical(
                self.router,
                "Login Error",
                f"Failed to open the main window:\n\n{e}"
            )

    def _on_logout(self):
        # Remove main window and go back to login
        self.router.removeWidget(self.main_window)
        self.main_window.deleteLater()
        self.main_window = None
        self.router.setCurrentWidget(self.login_screen)
        # Clear password fields
        self.login_screen.pw_input.clear()


if __name__ == "__main__":
    app = LibraryApp(sys.argv)
    sys.exit(app.exec())
