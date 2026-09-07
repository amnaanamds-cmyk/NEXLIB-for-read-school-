"""
config.py — Central configuration loader for NexLib Desktop.
Fully offline app: settings load from an optional local .env file.
Never hardcodes secrets, and never makes network calls.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this script
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

# ─── Security ────────────────────────────────────────────────────────────────
INACTIVITY_TIMEOUT: int = int(os.getenv("INACTIVITY_TIMEOUT", "900"))  # seconds

# ─── Library Settings ────────────────────────────────────────────────────────
DEFAULT_FINE_RATE: float = float(os.getenv("DEFAULT_FINE_RATE", "5.0"))

# ─── UI ──────────────────────────────────────────────────────────────────────
DEFAULT_THEME: str = os.getenv("DEFAULT_THEME", "dark")

# ─── Local Database ──────────────────────────────────────────────────────────
LOCAL_DB_PATH: str = str(
    Path.home() / "NexLib" / "nexlib.db"
)

# ─── App Info ────────────────────────────────────────────────────────────────
APP_NAME: str = "NexLib"
APP_VERSION: str = "1.0.0"

# ─── Roles ───────────────────────────────────────────────────────────────────
ROLE_ADMIN: str = "admin"
ROLE_LIBRARIAN: str = "librarian"
