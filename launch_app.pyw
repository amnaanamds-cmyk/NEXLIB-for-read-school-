"""
launch_app.pyw
Launches NexLib without a console window.
Identical to main.py but uses the .pyw extension for windowed execution.
"""
import sys
from main import LibraryApp

if __name__ == "__main__":
    app = LibraryApp(sys.argv)
    sys.exit(app.exec())
