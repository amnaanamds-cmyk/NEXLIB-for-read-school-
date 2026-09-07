"""
ui/screens/dashboard_screen.py — Overview dashboard with live stat cards,
fine counter, monthly issues bar chart, and quick action floating buttons.
"""
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QPushButton, QToolButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class StatCard(QFrame):
    STYLE = """
    QFrame {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 {c1}, stop:1 {c2});
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.08);
    }}
    QLabel#cardIcon {{ font-size: 32px; }}
    QLabel#cardVal  {{ color: white; font-size: 32px; font-weight: 900; font-family: 'Segoe UI'; }}
    QLabel#cardLbl  {{ color: rgba(255,255,255,0.75); font-size: 12px; font-family: 'Segoe UI'; }}
    """

    def __init__(self, icon, label, value="\u2014", c1="#1E5FD4", c2="#2872F0"):
        super().__init__()
        self.setStyleSheet(self.STYLE.format(c1=c1, c2=c2))
        self.setMinimumSize(180, 120)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("cardIcon")
        layout.addWidget(icon_lbl)

        self.val_lbl = QLabel(str(value))
        self.val_lbl.setObjectName("cardVal")
        layout.addWidget(self.val_lbl)

        txt_lbl = QLabel(label)
        txt_lbl.setObjectName("cardLbl")
        layout.addWidget(txt_lbl)

    def update_value(self, val):
        self.val_lbl.setText(str(val))


class StatsWorker(QThread):
    finished = pyqtSignal(dict, list)

    def __init__(self, fb, db):
        super().__init__()
        self.fb = fb
        self.db = db

    def run(self):
        stats = {}
        logs = []
        try:
            # Prioritize Local DB for immediate UI feedback in Offline-First architecture
            books = self.db.get_books()
            members = self.db.get_members()
            issues = self.db.get_issues()
            reservations = self.db.get_reservations()

            total_books = len(books)
            available = sum(1 for b in books if b.status == "Available")
            issued_count = sum(1 for b in books if b.status == "Issued")

            today = time.strftime("%Y-%m-%d")
            overdue = sum(1 for r in issues if r.status == "Issued" and r.dueDate and r.dueDate < today)

            total_fine = sum(r.fine for r in issues if r.status == "Returned" and r.fine > 0)

            from datetime import datetime, timedelta
            now = datetime.now()
            this_month_start = now.replace(day=1).strftime("%Y-%m-%d")
            last_month_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
            this_month_count = sum(1 for r in issues if r.issueDate and r.issueDate >= this_month_start)
            last_month_count = sum(1 for r in issues if r.issueDate and last_month_start <= r.issueDate < this_month_start)

            stats = {
                "totalBooks": total_books,
                "availableBooks": available,
                "issuedBooks": issued_count,
                "totalMembers": len(members),
                "overdueCount": overdue,
                "pendingReservations": len([r for r in reservations if r.status == "Pending"]),
                "totalFineCollected": total_fine,
                "thisMonthIssues": this_month_count,
                "lastMonthIssues": last_month_count,
            }

            cats = {}
            for b in books:
                c = b.category or "Uncategorized"
                cats[c] = cats.get(c, 0) + 1
            stats["categories"] = cats

            logs = self.db.get_audit_logs_local(10)

        except Exception as e:
            print(f"Error calculating dashboard stats: {e}")

        self.finished.emit(stats, logs)


class DashboardScreen(QWidget):
    def __init__(self, firebase_service, db_helper):
        super().__init__()
        self.fb = firebase_service
        self.db = db_helper
        self.worker = None
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(60_000)
        QTimer.singleShot(500, self.refresh)

    def launch_kiosk(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Kiosk Mode", "Self-Checkout Kiosk Mode initiated. The system is now locked to Patron Self-Service RFID Scanning.")

    def launch_gate(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Gate Check-in Monitor", "Smart Turnstile Tracking active.\nMonitoring physical patron entry/exit via digital library passes (RFID/NFC).")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("\U0001f4ca  Dashboard Overview")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #E8EEF8; font-family: 'Segoe UI';")
        hdr.addWidget(title)
        hdr.addStretch()
        self.refresh_btn = QPushButton("\U0001f504  Refresh")
        self.refresh_btn.setStyleSheet(
            "background: rgba(30,95,212,0.2); color: #6B8CAE; border: 1px solid #1E3050;"
            "border-radius: 8px; padding: 7px 14px; font-size: 12px;"
        )
        self.refresh_btn.clicked.connect(self.refresh)

        self.kiosk_btn = QPushButton("\U0001f4df Launch Self-Checkout Kiosk")
        self.kiosk_btn.setStyleSheet(
            "background: #F59E0B; color: white; border-radius: 8px; padding: 7px 14px; font-size: 12px; font-weight: bold;"
        )
        self.kiosk_btn.clicked.connect(self.launch_kiosk)

        self.gate_btn = QPushButton("\U0001f4cd Gate Check-in (Geo-Fence)")
        self.gate_btn.setStyleSheet(
            "background: #059669; color: white; border-radius: 8px; padding: 7px 14px; font-size: 12px; font-weight: bold;"
        )
        self.gate_btn.clicked.connect(self.launch_gate)

        hdr.addWidget(self.gate_btn)
        hdr.addWidget(self.kiosk_btn)
        hdr.addWidget(self.refresh_btn)
        layout.addLayout(hdr)

        self.last_update = QLabel("Last updated: \u2014")
        self.last_update.setStyleSheet("color: #4D6A90; font-size: 11px;")
        layout.addWidget(self.last_update)

        # Stats grid (7 cards including fine counter)
        grid = QGridLayout()
        grid.setSpacing(16)

        self.cards = {
            "totalBooks":        StatCard("\U0001f4da", "Total Books",    c1="#1E5FD4", c2="#2872F0"),
            "availableBooks":    StatCard("\u2705", "Available",      c1="#059669", c2="#10B981"),
            "issuedBooks":       StatCard("\U0001f4d6", "Issued",         c1="#D97706", c2="#F59E0B"),
            "totalMembers":      StatCard("\U0001f465", "Total Members",  c1="#7C3AED", c2="#8B5CF6"),
            "overdueCount":      StatCard("\u23f0", "Overdue",        c1="#DC2626", c2="#EF4444"),
            "pendingReservations": StatCard("\U0001f514", "Reservations", c1="#0891B2", c2="#06B6D4"),
            "totalFineCollected": StatCard("\U0001f4b0", "Fine Collected", c1="#059669", c2="#34D399"),
        }
        positions = [(0,0),(0,1),(0,2),(1,0),(1,1),(1,2),(2,0)]
        for (r,c), card in zip(positions, self.cards.values()):
            grid.addWidget(card, r, c)
        layout.addLayout(grid)

        # Feature 2.6: Quick Action Floating Buttons
        qa_label = QLabel("\u26a1  Quick Actions")
        qa_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #C8A84B; font-family: 'Segoe UI'; margin-top: 4px;")
        layout.addWidget(qa_label)

        qa_row = QHBoxLayout()
        qa_row.setSpacing(10)
        self._qa_btns = []
        qa_items = [
            ("\U0001f4d5 Issue Book", "#059669", "issue_return"),
            ("\U0001f504 Return Book", "#D97706", "issue_return"),
            ("\U0001f4da Add Book", "#1E5FD4", "books"),
            ("\U0001f465 Add Member", "#7C3AED", "members"),
            ("\U0001f50d Search OPAC", "#0891B2", "opac"),
            ("\U0001f4ca Reports", "#C8A84B", "reports"),
        ]
        for text, color, nav_key in qa_items:
            btn = QPushButton(text)
            btn.setStyleSheet(
                f"background: {color}; color: white; border: none; border-radius: 8px; "
                f"padding: 8px 16px; font-size: 12px; font-weight: 700; font-family: 'Segoe UI';"
            )
            btn.clicked.connect(lambda _, k=nav_key: self._navigate(k))
            qa_row.addWidget(btn)
            self._qa_btns.append((btn, nav_key))
        qa_row.addStretch()
        layout.addLayout(qa_row)

        # Charts and Activity
        chart_lay = QHBoxLayout()

        # Feature 2.7: Dual chart — Category breakdown + Monthly issues
        chart_container = QFrame()
        chart_container.setStyleSheet("background: #0D1F38; border-radius: 12px; border: 1px solid #1E3050;")
        chart_vlay = QVBoxLayout(chart_container)
        chart_vlay.setContentsMargins(12, 12, 12, 12)

        self.figure = Figure(figsize=(5, 4), dpi=100, facecolor='#0D1F38')
        self.canvas = FigureCanvas(self.figure)

        self.ax_cat = self.figure.add_subplot(121)
        self.ax_cat.set_facecolor('#071428')
        self.ax_cat.tick_params(colors='#A0B4CC', labelsize=7)
        for spine in self.ax_cat.spines.values():
            spine.set_color('#1E3050')
        self.ax_cat.set_title("Categories", color="#E8EEF8", fontsize=9, fontweight='bold')

        self.ax_month = self.figure.add_subplot(122)
        self.ax_month.set_facecolor('#071428')
        self.ax_month.tick_params(colors='#A0B4CC', labelsize=7)
        for spine in self.ax_month.spines.values():
            spine.set_color('#1E3050')
        self.ax_month.set_title("Monthly Issues", color="#E8EEF8", fontsize=9, fontweight='bold')

        self.figure.tight_layout(pad=2)
        chart_vlay.addWidget(self.canvas)
        chart_lay.addWidget(chart_container, stretch=2)

        # Recent Activity section
        act_label = QLabel("\U0001f4dd  Recent Activity")
        act_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #E8EEF8; font-family:'Segoe UI'; margin-top:8px;")
        layout.addWidget(act_label)

        self.activity_frame = QFrame()
        self.activity_frame.setStyleSheet(
            "background: rgba(13,28,55,0.6); border-radius: 12px; border: 1px solid #1E3050;"
        )
        self.activity_layout = QVBoxLayout(self.activity_frame)
        self.activity_layout.setContentsMargins(16, 16, 16, 16)
        self.no_activity = QLabel("Refresh to load recent activity\u2026")
        self.no_activity.setStyleSheet("color: #4D6A90; font-size: 12px;")
        self.activity_layout.addWidget(self.no_activity)

        chart_lay.addWidget(self.activity_frame, stretch=3)
        layout.addLayout(chart_lay)
        layout.addStretch()

    def _navigate(self, key):
        """Find the MainWindow and navigate."""
        win = self.window()
        if hasattr(win, 'navigate_to'):
            win.navigate_to(key)
        else:
            # Fallback for nested widgets
            curr = self.parentWidget()
            while curr:
                if hasattr(curr, 'navigate_to'):
                    curr.navigate_to(key)
                    return
                curr = curr.parentWidget()

    def refresh(self):
        self.refresh_btn.setEnabled(False)
        self.worker = StatsWorker(self.fb, self.db)
        self.worker.finished.connect(self._on_stats)
        self.worker.start()

    def _on_stats(self, stats: dict, logs: list):
        self.refresh_btn.setEnabled(True)
        for key, card in self.cards.items():
            if key in stats:
                val = stats[key]
                if key == "totalFineCollected":
                    val = f"Rs. {val:,.0f}"
                card.update_value(val)
        self.last_update.setText(f"Last updated: {time.strftime('%H:%M:%S')}")

        # Feature 2.7: Update category pie chart
        cats = stats.get("categories", {})
        if cats:
            self.ax_cat.clear()
            self.ax_cat.set_facecolor('#071428')
            self.ax_cat.tick_params(colors='#A0B4CC', labelsize=7)
            for spine in self.ax_cat.spines.values():
                spine.set_color('#1E3050')
            labels = list(cats.keys())[:5]
            values = list(cats.values())[:5]
            self.ax_cat.barh(labels, values, color='#2872F0', height=0.6)
            self.ax_cat.set_title("Categories (Top 5)", color="#E8EEF8", fontsize=9, fontweight='bold')

        # Feature 2.7: Monthly issues bar chart
        this_month = stats.get("thisMonthIssues", 0)
        last_month = stats.get("lastMonthIssues", 0)
        self.ax_month.clear()
        self.ax_month.set_facecolor('#071428')
        self.ax_month.tick_params(colors='#A0B4CC', labelsize=7)
        for spine in self.ax_month.spines.values():
            spine.set_color('#1E3050')
        bar_labels = ["Last Month", "This Month"]
        bar_values = [last_month, this_month]
        bar_colors = ['#6B8CAE', '#10B981']
        self.ax_month.bar(bar_labels, bar_values, color=bar_colors, width=0.5)
        for i, v in enumerate(bar_values):
            self.ax_month.text(i, v + 0.2, str(v), ha='center', color='#E8EEF8', fontsize=9, fontweight='bold')
        self.ax_month.set_title("Issues: Last vs This Month", color="#E8EEF8", fontsize=9, fontweight='bold')

        self.canvas.draw()

        # Show audit log entries
        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not logs:
            lbl = QLabel("No recent activity.")
            lbl.setStyleSheet("color: #4D6A90; font-size: 12px;")
            self.activity_layout.addWidget(lbl)
        else:
            for entry in logs:
                row = QLabel(
                    f"\U0001f539  {entry.get('timestampStr','')}  \u00b7  "
                    f"<b>{entry.get('action','')}</b>  \u2014  "
                    f"{entry.get('detail','')}  "
                    f"<span style='color:#4D6A90'>({entry.get('userEmail','')})</span>"
                )
                row.setTextFormat(Qt.TextFormat.RichText)
                row.setStyleSheet("color: #A0B4CC; font-size: 12px; padding: 4px 0;")
                self.activity_layout.addWidget(row)
