"""
services/media_service.py — Local storage for uploaded files (book covers,
member photos, etc). Everything is copied into the app's local data folder
so the app never needs network access to store or show attachments.
"""
import shutil
import uuid
from pathlib import Path

import config


def _media_root() -> Path:
    root = Path(config.LOCAL_DB_PATH).parent / "media"
    root.mkdir(parents=True, exist_ok=True)
    return root


def store_file(local_path: str, subfolder: str) -> str:
    """Copy a local file into the app's media folder and return the stored path."""
    if not local_path:
        return ""
    src = Path(local_path)
    if not src.exists():
        return ""

    dest_dir = _media_root() / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{uuid.uuid4().hex}{src.suffix}"
    shutil.copy2(str(src), str(dest))
    return str(dest)
