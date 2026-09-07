import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

# Mock services
class MockAuth:
    is_director = False
    current_user = type("User", (), {"name": "Test", "email": "test@test.com", "role": "admin"})
    def sign_out(self): pass

class MockFB:
    pass

class MockDB:
    def execute_query(self, *args, **kwargs): return []
    def execute_update(self, *args, **kwargs): pass
    def get_setting(self, *args, **kwargs): return "dark"
    
class MockSync:
    from PyQt6.QtCore import pyqtSignal, QObject
    class Signals(QObject):
        sync_status = pyqtSignal(str)
    
    def __init__(self):
        self.signals = self.Signals()
        self.sync_status = self.signals.sync_status
    def stop(self): pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        window = MainWindow(MockAuth(), MockFB(), MockDB(), MockSync())
        print("MainWindow initialized successfully.")
        
        # Test navigation to all screens
        for key in window._screens.keys():
            window.navigate_to(key)
            print(f"Navigated to {key}")
            
        print("All screens loaded without crashing.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
