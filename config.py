"""
config.py — Central configuration loader for GDC Library50 Desktop.
Loads all settings from the .env file. Never hardcodes secrets.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this script
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

# ─── Firebase ────────────────────────────────────────────────────────────────
FIREBASE_CRED_PATH: str = os.getenv("FIREBASE_CRED_PATH", "serviceAccountKey.json")
FIREBASE_STORAGE_BUCKET: str = os.getenv("FIREBASE_STORAGE_BUCKET", "")
FIREBASE_WEB_API_KEY: str = os.getenv("FIREBASE_WEB_API_KEY", "")

# ─── Google Generative AI ────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ─── Institution ─────────────────────────────────────────────────────────────
COLLEGE_ID: str = os.getenv("COLLEGE_ID", "gdc-ziam-sherpao")

# ─── Security ────────────────────────────────────────────────────────────────
INACTIVITY_TIMEOUT: int = int(os.getenv("INACTIVITY_TIMEOUT", "900"))  # seconds
KEYRING_SERVICE_NAME: str = "GDCLibrary50Desktop"

# ─── Library Settings ────────────────────────────────────────────────────────
DEFAULT_FINE_RATE: float = float(os.getenv("DEFAULT_FINE_RATE", "5.0"))

# ─── UI ──────────────────────────────────────────────────────────────────────
DEFAULT_THEME: str = os.getenv("DEFAULT_THEME", "dark")

# ─── Local Database ──────────────────────────────────────────────────────────
LOCAL_DB_PATH: str = str(
    Path.home() / "GDCLibrary50" / "gdc_library.db"
)

# ─── App Info ────────────────────────────────────────────────────────────────
APP_NAME: str = "GDC Library50 Desktop"
APP_VERSION: str = "1.0.0"
APP_ORG: str = "Government Degree College"

# ─── Directorate Central Sync ─────────────────────────────────────────────────
DIRECTORATE_API_URL: str = os.getenv("DIRECTORATE_API_URL", "http://localhost:8000")
DIRECTORATE_API_KEY: str = os.getenv("DIRECTORATE_API_KEY", "")
COLLEGE_NAME: str = os.getenv("COLLEGE_NAME", "Government Degree College")
COLLEGE_LOCATION: str = os.getenv("COLLEGE_LOCATION", "Pakistan")
DIRECTORATE_SYNC_INTERVAL: int = int(os.getenv("DIRECTORATE_SYNC_INTERVAL", "5"))  # minutes

# ─── Role Hierarchy ──────────────────────────────────────────────────────────
ROLE_DIRECTORATE_ADMIN: str = "directorate_admin"
ROLE_COLLEGE_ADMIN: str = "college_admin"
ROLE_LIBRARIAN: str = "librarian"
ROLE_DIRECTOR: str = "director"  # backward compat alias for college_admin
ROLE_ADMIN: str = "admin"  # backward compat alias for college_admin
