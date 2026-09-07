"""
ui/screens/director_screen.py — Specialized read-only dashboard for Director.
Focuses heavily on digitalization KPIs and network-level insights.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from ui.screens.dashboard_screen import StatsWorker


class DirectorScreen(QWidget):
    def __init__(self, firebase_service, db_helper):
        super().__init__()
        self.fb = firebase_service
        self.db = db_helper
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        hdr = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("🎯  Director's Dashboard")
        title.setStyleSheet("font-size: 28px; font-weight: 900; color: #C8A84B; font-family: 'Segoe UI';")
        sub = QLabel("High-level Key Performance Indicators (KPIs) and Digitalization Progress")
        sub.setStyleSheet("color: #6B8CAE; font-size: 14px;")
        titles.addWidget(title); titles.addWidget(sub)
        hdr.addLayout(titles)
        hdr.addStretch()
        self.ref_btn = QPushButton("🔄 Refresh")
        self.ref_btn.setStyleSheet("background: #1E3050; color: white; border-radius: 8px; padding: 10px 20px;")
        self.ref_btn.clicked.connect(self.refresh)
        hdr.addWidget(self.ref_btn)
        layout.addLayout(hdr)

        # Top KPIs
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(16)
        
        self.kpi_lbls = {}
        for i, (key, title, icon) in enumerate([
            ("totalBooks", "Network Volumes", "📚"),
            ("totalMembers", "Total Patrons", "👥"),
            ("activeIssues", "Active Circulation", "🔄"),
            ("overdueCount", "Overdue Alerts", "⚠️")
        ]):
            frame = QFrame()
            frame.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0D1B2A,stop:1 #13263B); border: 1px solid #1E3050; border-radius: 12px;")
            l = QVBoxLayout(frame); l.setContentsMargins(20,20,20,20)
            l.addWidget(QLabel(icon, styleSheet="font-size: 32px; background: transparent; border:none;"))
            val = QLabel("—")
            val.setStyleSheet("font-size: 36px; font-weight: 900; color: white; background: transparent; border:none;")
            self.kpi_lbls[key] = val
            l.addWidget(val)
            l.addWidget(QLabel(title, styleSheet="color: #6B8CAE; font-size: 12px; font-weight: 600; background: transparent; border:none;"))
            kpi_grid.addWidget(frame, 0, i)
            
        layout.addLayout(kpi_grid)

        # Digitalization Progress
        dig_frame = QFrame()
        dig_frame.setStyleSheet("background: #0D1F38; border: 1px solid #C8A84B; border-radius: 12px;")
        dl = QVBoxLayout(dig_frame); dl.setContentsMargins(24,24,24,24)
        dl.addWidget(QLabel("🚀  Digitalization Progress (HEC Mandate)", styleSheet="font-size: 18px; font-weight: 700; color: #E6C96E; background: transparent; border:none;"))
        
        dp_row = QHBoxLayout()
        self.isbn_lbl = QLabel("ISBN Tagging: —%")
        self.ebook_lbl = QLabel("E-Book Conversion: —%")
        for lbl in (self.isbn_lbl, self.ebook_lbl):
            lbl.setStyleSheet("font-size: 24px; font-weight: 800; color: white; background: transparent; border:none;")
            dp_row.addWidget(lbl)
        dl.addLayout(dp_row)
        layout.addWidget(dig_frame)
        
        layout.addStretch()

    def refresh(self):
        self.ref_btn.setText("Loading...")
        self.worker = StatsWorker(self.fb, self.db)
        self.worker.finished.connect(self._on_stats)
        self.worker.start()

    def _on_stats(self, stats: dict, logs: list):
        self.ref_btn.setText("🔄 Refresh")
        for k, v in self.kpi_lbls.items():
            v.setText(str(stats.get(k, 0)))
            
        dp = stats.get("digitalizationProgress", {})
        self.isbn_lbl.setText(f"ISBN Tagging: {dp.get('withIsbn', 0)}%")
        self.ebook_lbl.setText(f"E-Book Conversion: {dp.get('withEBook', 0)}%")
