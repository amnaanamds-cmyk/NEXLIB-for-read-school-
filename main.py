"""
main.py — Main entry point for the GDC Library50 Desktop Application.
Initializes PyQt6, loads the font, connects Firebase, starts sync engine,
and handles routing between Login and MainWindow.
"""
import sys
import traceback
import logging
import ctypes
from PyQt6.QtWidgets import QApplication, QStackedWidget, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFontDatabase, QFont

import config
from services.firebase_service import FirebaseService
from services.database_helper import DatabaseHelper
from services.sync_service import SyncService
from services.directorate_sync_service import DirectorateSyncService
from services.auth_service import AuthService
from ui.login_screen import LoginScreen
from ui.main_window import MainWindow

# Configure global logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gdc_library.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Feature: Force taskbar icon to show (AppUserModelID)
if sys.platform == 'win32':
    myappid = f"gdc.library50.management.v{config.APP_VERSION}"
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

        # Set Application Icon (Feature Part B)
        self.setWindowIcon(QIcon("assets/gdc_library.ico"))

        # Initialize Services
        self.db_helper = DatabaseHelper()
        try:
            self.fb_service = FirebaseService()
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}", exc_info=True)
            sys.exit(1)
            
        self.auth_service = AuthService(self.fb_service)
        
        # Setup sync service (background thread)
        self.sync_service = SyncService(self.db_helper, self.fb_service)
        self.directorate_sync = DirectorateSyncService(self.db_helper)

        # Setup main router (QStackedWidget)
        self.router = QStackedWidget()
        self.router.setWindowTitle(f"{config.APP_NAME} — {config.APP_ORG}")
        self.router.setMinimumSize(1024, 768)

        # 1. Login Screen
        self.login_screen = LoginScreen(self.auth_service)
        self.login_screen.login_success.connect(self._on_login_success)
        self.router.addWidget(self.login_screen)

        self.router.show()
        self.login_screen.try_auto_login()

    def _on_login_success(self, role: str):
        try:
            # Start Sync Service
            if not self.sync_service.isRunning():
                self.sync_service.start()
            if not self.directorate_sync.isRunning():
                self.directorate_sync.start()

            # 2. Main Window
            self.main_window = MainWindow(self.auth_service, self.fb_service, self.db_helper, self.sync_service, self.directorate_sync)
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
