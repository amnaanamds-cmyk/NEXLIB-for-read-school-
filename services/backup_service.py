"""
services/backup_service.py
Automated Backup & Restore for NexLib Desktop.
Schedules daily SQLite backups, provides manual backup/restore,
and a full ZIP export for archiving or moving to another machine.
"""
import os
import shutil
import time
import json
import zipfile
from pathlib import Path
from typing import List, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal

import config
from services.database_helper import DatabaseHelper


BACKUP_DIR = Path(config.LOCAL_DB_PATH).parent / "backups"
MAX_BACKUPS = 30  # Keep last 30 days
BACKUP_INTERVAL_SECONDS = 86400  # 24 hours


class BackupService(QThread):
    """Background thread that performs daily automated SQLite backups."""
    backup_done = pyqtSignal(str)   # path of new backup
    backup_failed = pyqtSignal(str) # error message

    def __init__(self, db_helper: DatabaseHelper):
        super().__init__()
        self.db = db_helper
        self.running = True
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def stop(self):
        self.running = False

    def run(self):
        """Check daily if a backup is needed."""
        time.sleep(60)  # Wait 1 minute after startup
        while self.running:
            try:
                last_backup_ts = self._get_last_backup_timestamp()
                elapsed = time.time() - (last_backup_ts / 1000)
                if elapsed >= BACKUP_INTERVAL_SECONDS:
                    path = self.do_backup(backup_type="auto")
                    self.backup_done.emit(path)
            except Exception as e:
                self.backup_failed.emit(str(e))

            # Sleep in 1-min increments
            for _ in range(60 * 2):
                if not self.running:
                    break
                time.sleep(0.5)

    def do_backup(self, backup_type: str = "manual") -> str:
        """Copy the SQLite DB file to the backup directory. Returns backup path."""
        src = Path(config.LOCAL_DB_PATH)
        if not src.exists():
            raise FileNotFoundError(f"Database file not found: {src}")

        ts_str = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"library_{ts_str}_{backup_type}.db"
        dest = BACKUP_DIR / backup_name

        shutil.copy2(str(src), str(dest))
        file_size = dest.stat().st_size

        self.db.log_backup(str(dest), backup_type, file_size)
        self._rotate_old_backups()
        return str(dest)

    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore the database from a backup file. Returns True on success."""
        src = Path(backup_path)
        if not src.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        dest = Path(config.LOCAL_DB_PATH)
        # Safety: back up current DB before overwriting
        safety_path = str(dest) + ".pre_restore"
        shutil.copy2(str(dest), safety_path)

        try:
            shutil.copy2(str(src), str(dest))
            return True
        except Exception as e:
            # Restore safety backup
            shutil.copy2(safety_path, str(dest))
            raise e
        finally:
            if os.path.exists(safety_path):
                os.remove(safety_path)

    def export_full_backup_zip(self, output_path: str) -> str:
        """Export a full backup ZIP (DB + metadata) for archiving or moving to another machine."""
        if not output_path.endswith(".zip"):
            output_path = output_path + ".zip"

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. The SQLite DB file
            db_path = Path(config.LOCAL_DB_PATH)
            if db_path.exists():
                zf.write(str(db_path), "library.db")

            # 2. Metadata JSON
            profile = self.db.get_school_profile()
            meta = {
                "school_name": profile.get("name", ""),
                "school_address": profile.get("address", ""),
                "app_version": config.APP_VERSION,
                "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            zf.writestr("metadata.json", json.dumps(meta, indent=2))

        file_size = Path(output_path).stat().st_size
        self.db.log_backup(output_path, "migration", file_size)
        return output_path

    def get_available_backups(self) -> List[Dict[str, Any]]:
        """Return list of backup files with metadata."""
        backups = []
        if not BACKUP_DIR.exists():
            return backups
        for f in sorted(BACKUP_DIR.glob("*.db"), reverse=True):
            stat = f.stat()
            backups.append({
                "path": str(f),
                "name": f.name,
                "size_kb": round(stat.st_size / 1024, 1),
                "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            })
        return backups

    def _get_last_backup_timestamp(self) -> int:
        history = self.db.get_backup_history(1)
        if history:
            return history[0].get("created_at", 0)
        return 0

    def _rotate_old_backups(self):
        """Delete oldest backups if total exceeds MAX_BACKUPS."""
        files = sorted(BACKUP_DIR.glob("library_*_auto.db"),
                       key=lambda f: f.stat().st_mtime)
        while len(files) > MAX_BACKUPS:
            files[0].unlink(missing_ok=True)
            files.pop(0)
