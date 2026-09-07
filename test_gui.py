"""
test_gui.py — Headless smoke test.
Boots MainWindow against a throwaway local SQLite database and navigates
every screen once, to catch import/construction errors early.
Run with: QT_QPA_PLATFORM=offscreen python test_gui.py
"""
import sys
import os
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Point the app at a throwaway database before importing config/services.
_tmp_dir = tempfile.mkdtemp(prefix="nexlib_test_")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
import config
config.LOCAL_DB_PATH = os.path.join(_tmp_dir, "test.db")

from services.database_helper import DatabaseHelper
from services.auth_service import AuthService
from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        db = DatabaseHelper()
        auth = AuthService(db)
        db.set_school_profile("name", "Test School")
        auth.create_account("admin", "test1234", "Test Admin", "admin")
        auth.sign_in("admin", "test1234")

        window = MainWindow(auth, db)
        print("MainWindow initialized successfully.")

        for key in window._screens.keys():
            window.navigate_to(key)
            print(f"Navigated to {key}")

        print("All screens loaded without crashing.")
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
