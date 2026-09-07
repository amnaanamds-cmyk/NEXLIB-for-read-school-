"""
services/directorate_sync_service.py
Background QThread that pushes college statistics snapshots to the
cental Directorate Server every N minutes. Fully offline-first:
never blocks local operations, queues on failure, retries next cycle.
"""
import json
import time
import requests
from PyQt6.QtCore import QThread, pyqtSignal

import config
from services.database_helper import DatabaseHelper


class DirectorateSyncService(QThread):
    sync_status = pyqtSignal(str)    # status messages
    sync_completed = pyqtSignal()    # fires on successful push

    def __init__(self, db_helper: DatabaseHelper):
        super().__init__()
        self.db = db_helper
        self.running = True
        self.interval_seconds = config.DIRECTORATE_SYNC_INTERVAL * 60

    def stop(self):
        self.running = False

    def trigger_immediate_sync(self):
        """Called after major actions (issue, return, add book/member) to push immediately."""
        self._push_snapshot()

    def run(self):
        time.sleep(10)  # Short startup delay
        while self.running:
            self._push_snapshot()
            # Sleep in increments so we can respond to stop()
            for _ in range(self.interval_seconds * 2):
                if not self.running:
                    break
                time.sleep(0.5)

    def _push_snapshot(self):
        """Compute local stats and push to central server. Queue on failure."""
        if not config.DIRECTORATE_API_KEY or not config.COLLEGE_ID:
            return  # Not configured yet

        try:
            snapshot = self.db.compute_snapshot()
            snapshot["college_id"] = config.COLLEGE_ID
            self._push(snapshot)
        except Exception as e:
            # Queue for retry
            try:
                payload = self.db.compute_snapshot()
                payload["college_id"] = config.COLLEGE_ID
                self.db.queue_directorate_snapshot(payload)
            except Exception:
                pass
            self.sync_status.emit(f"Directorate Offline: {str(e)[:30]}")

        # Also drain any queued snapshots
        self._drain_queue()

    def _push(self, payload: dict):
        """Send payload to central server."""
        url = f"{config.DIRECTORATE_API_URL}/api/sync"
        headers = {"X-College-API-Key": config.DIRECTORATE_API_KEY}
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            self.sync_status.emit("🏛️ Directorate Synced")
            self.sync_completed.emit()
        else:
            raise Exception(f"Server returned {resp.status_code}: {resp.text[:50]}")

    def _drain_queue(self):
        """Retry any previously queued snapshots."""
        pending = self.db.get_pending_directorate_syncs()
        for item in pending:
            try:
                payload = json.loads(item["payload"])
                self._push(payload)
                self.db.remove_directorate_sync(item["id"])
            except Exception:
                break  # Stop on first failure, retry next cycle
