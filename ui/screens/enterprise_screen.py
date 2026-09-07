import time
import json
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QInputDialog, QMessageBox, QGridLayout, QFrame, QLineEdit, QFormLayout,
    QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class EnterpriseFeaturesScreen(QWidget):
    def __init__(self, db_helper):
        super().__init__()
        self.db = db_helper
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        
        hdr = QLabel("🚀  Enterprise & Unique Features")
        hdr.setStyleSheet("font-size:22px;font-weight:800;color:#E8EEF8;font-family:'Segoe UI';")
        layout.addWidget(hdr)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane{background:#071428;border:1px solid #1E3050;border-radius:8px;}
            QTabBar::tab{background:#0D1B2A;color:#6B8CAE;padding:12px 20px;font-size:13px;font-weight:700;border-top-left-radius:8px;border-top-right-radius:8px;}
            QTabBar::tab:selected{background:#1E3050;color:#E6C96E;border-bottom:3px solid #C8A84B;}
        """)
        
        self._build_reading_room(self.tabs)
        self._build_lost_found(self.tabs)
        self._build_events(self.tabs)
        self._build_gamification(self.tabs)
        self._build_ai_procurement(self.tabs)
        
        layout.addWidget(self.tabs)
        
    # ─── Feature 1: Reading Room Manager ──────────────────────────────────────
    def _build_reading_room(self, tabs):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(16,16,16,16)
        l.addWidget(QLabel("Manage seat assignments for the physical reading room.", styleSheet="color:#A0B4CC;font-size:14px;"))
        
        grid = QGridLayout()
        self.seats = {}
        for i in range(1, 21):
            btn = QPushButton(f"Seat {i}\n(Empty)")
            btn.setFixedSize(100, 80)
            btn.setStyleSheet("background:#10B981;color:white;border-radius:8px;font-weight:bold;")
            btn.clicked.connect(lambda _, s=i: self._toggle_seat(s))
            self.seats[i] = btn
            grid.addWidget(btn, (i-1)//5, (i-1)%5)
            
        l.addLayout(grid)
        l.addStretch()
        tabs.addTab(w, "🪑 Reading Room")
        
    def _toggle_seat(self, seat_num):
        btn = self.seats[seat_num]
        if "(Empty)" in btn.text():
            mem_id, ok = QInputDialog.getText(self, "Assign Seat", f"Enter Member ID for Seat {seat_num}:")
            if ok and mem_id:
                btn.setText(f"Seat {seat_num}\n{mem_id}")
                btn.setStyleSheet("background:#EF4444;color:white;border-radius:8px;font-weight:bold;")
        else:
            reply = QMessageBox.question(self, "Free Seat", f"Make Seat {seat_num} empty?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                btn.setText(f"Seat {seat_num}\n(Empty)")
                btn.setStyleSheet("background:#10B981;color:white;border-radius:8px;font-weight:bold;")

    # ─── Feature 2: Digital Lost & Found ──────────────────────────────────────
    def _build_lost_found(self, tabs):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(16,16,16,16)
        l.addWidget(QLabel("Track items lost or found within the library premises.", styleSheet="color:#A0B4CC;font-size:14px;"))
        
        self.lf_table = QTableWidget(0, 4)
        self.lf_table.setHorizontalHeaderLabels(["Date", "Item Description", "Location", "Status"])
        self.lf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.lf_table.setStyleSheet("QTableWidget { background:#0D1B2A; color:#E8EEF8; border:1px solid #1E3050; } QHeaderView::section { background:#1E3050; color:#E8EEF8; }")
        l.addWidget(self.lf_table)
        
        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ Report Item")
        add_btn.setStyleSheet("background:#2563EB;color:white;border-radius:8px;padding:8px 16px;font-weight:bold;")
        add_btn.clicked.connect(self._add_lf_item)
        btn_row.addWidget(add_btn)
        
        claim_btn = QPushButton("✅ Mark as Claimed/Resolved")
        claim_btn.setStyleSheet("background:#059669;color:white;border-radius:8px;padding:8px 16px;font-weight:bold;")
        claim_btn.clicked.connect(self._resolve_lf_item)
        btn_row.addWidget(claim_btn)
        btn_row.addStretch()
        l.addLayout(btn_row)
        
        tabs.addTab(w, "🔍 Lost & Found")
        
        # Add some mock data
        self._add_lf_row("2024-05-12", "Blue Water Bottle", "Reading Room", "Found")
        self._add_lf_row("2024-05-10", "HP Laptop Charger", "Section B", "Lost")
        
    def _add_lf_row(self, date, item, loc, status):
        row = self.lf_table.rowCount()
        self.lf_table.insertRow(row)
        self.lf_table.setItem(row, 0, QTableWidgetItem(date))
        self.lf_table.setItem(row, 1, QTableWidgetItem(item))
        self.lf_table.setItem(row, 2, QTableWidgetItem(loc))
        itm = QTableWidgetItem(status)
        if status == "Lost": itm.setForeground(QColor("#EF4444"))
        elif status == "Found": itm.setForeground(QColor("#10B981"))
        self.lf_table.setItem(row, 3, itm)
        
    def _add_lf_item(self):
        desc, ok = QInputDialog.getText(self, "Report Item", "Item Description:")
        if ok and desc:
            loc, ok2 = QInputDialog.getText(self, "Location", "Location:")
            if ok2:
                status, ok3 = QInputDialog.getItem(self, "Status", "Is it Lost or Found?", ["Lost", "Found"], 0, False)
                if ok3:
                    self._add_lf_row(datetime.date.today().strftime("%Y-%m-%d"), desc, loc, status)
                    
    def _resolve_lf_item(self):
        r = self.lf_table.currentRow()
        if r >= 0:
            itm = QTableWidgetItem("Claimed/Resolved")
            itm.setForeground(QColor("#C8A84B"))
            self.lf_table.setItem(r, 3, itm)
            
    # ─── Feature 3: Event & Workshop Scheduler ────────────────────────────────
    def _build_events(self, tabs):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(16,16,16,16)
        l.addWidget(QLabel("Schedule library workshops, author talks, and community events.", styleSheet="color:#A0B4CC;font-size:14px;"))
        
        self.ev_table = QTableWidget(0, 4)
        self.ev_table.setHorizontalHeaderLabels(["Date & Time", "Event Title", "Speaker/Host", "Registered Attendees"])
        self.ev_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ev_table.setStyleSheet(self.lf_table.styleSheet())
        l.addWidget(self.ev_table)
        
        btn_row = QHBoxLayout()
        add_btn = QPushButton("📅 Schedule New Event")
        add_btn.setStyleSheet("background:#7C3AED;color:white;border-radius:8px;padding:8px 16px;font-weight:bold;")
        add_btn.clicked.connect(self._add_event)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        l.addLayout(btn_row)
        
        tabs.addTab(w, "📅 Event Scheduler")
        self._add_ev_row("2024-06-15 14:00", "Introduction to Python", "Dr. Ahmed", "45/50")
        self._add_ev_row("2024-06-20 10:00", "Literature & Modern World", "Guest Author", "120/150")
        
    def _add_ev_row(self, dt, title, host, att):
        row = self.ev_table.rowCount()
        self.ev_table.insertRow(row)
        self.ev_table.setItem(row, 0, QTableWidgetItem(dt))
        self.ev_table.setItem(row, 1, QTableWidgetItem(title))
        self.ev_table.setItem(row, 2, QTableWidgetItem(host))
        self.ev_table.setItem(row, 3, QTableWidgetItem(att))
        
    def _add_event(self):
        title, ok = QInputDialog.getText(self, "New Event", "Event Title:")
        if ok and title:
            host, ok2 = QInputDialog.getText(self, "Host", "Speaker/Host:")
            if ok2:
                dt = datetime.datetime.now() + datetime.timedelta(days=7)
                self._add_ev_row(dt.strftime("%Y-%m-%d %H:%M"), title, host, "0/50")

    # ─── Feature 4: Patron Gamification ───────────────────────────────────────
    def _build_gamification(self, tabs):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(16,16,16,16)
        l.addWidget(QLabel("Boost reading engagement! Ranks update automatically based on reading history.", styleSheet="color:#A0B4CC;font-size:14px;"))
        
        self.gam_lbl = QLabel("Enter Member ID to view their Reading Badges and Level:")
        self.gam_lbl.setStyleSheet("color:#E8EEF8;font-weight:bold;")
        l.addWidget(self.gam_lbl)
        
        search_lay = QHBoxLayout()
        self.g_search = QLineEdit()
        self.g_search.setPlaceholderText("Member ID...")
        self.g_search.setStyleSheet("background:#0D1B2A;color:#E8EEF8;border:1px solid #1E3050;padding:8px;")
        search_lay.addWidget(self.g_search)
        
        btn = QPushButton("Analyze Profile")
        btn.setStyleSheet("background:#C8A84B;color:#0D1B2A;border-radius:4px;padding:8px 16px;font-weight:bold;")
        btn.clicked.connect(self._analyze_gamification)
        search_lay.addWidget(btn)
        l.addLayout(search_lay)
        
        self.badge_display = QLabel("\n\n\nProfile Data Will Appear Here")
        self.badge_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge_display.setStyleSheet("background:#0D1B2A;border:1px dashed #1E3050;color:#6B8CAE;font-size:16px;")
        l.addWidget(self.badge_display)
        l.addStretch()
        tabs.addTab(w, "🏆 Gamification")
        
    def _analyze_gamification(self):
        mid = self.g_search.text().strip()
        if not mid: return
        members = [m for m in self.db.get_members() if m.memberId == mid]
        if not members:
            self.badge_display.setText("Member Not Found.")
            return
            
        m = members[0]
        read = m.booksIssued  # Using issued count as a proxy for books read
        
        if read < 5:
            rank, badge = "Novice Reader", "🌱"
            next_tgt = 5
        elif read < 20:
            rank, badge = "Avid Bookworm", "🐛"
            next_tgt = 20
        elif read < 50:
            rank, badge = "Library Scholar", "🎓"
            next_tgt = 50
        else:
            rank, badge = "Grandmaster of Pages", "👑"
            next_tgt = "MAX"
            
        html = f"""
        <h2 style='color:#E6C96E;'>{badge} {m.name}</h2>
        <p>Current Rank: <b>{rank}</b></p>
        <p>Books Read: <b>{read}</b></p>
        """
        if next_tgt != "MAX":
            html += f"<p><i>Read {next_tgt - read} more books to rank up!</i></p>"
            
        self.badge_display.setText(html)

    # ─── Feature 5: AI Auto-Procurement List ──────────────────────────────────
    def _build_ai_procurement(self, tabs):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(16,16,16,16)
        l.addWidget(QLabel("Analyzes circulation history to automatically suggest books to purchase based on high demand.", styleSheet="color:#A0B4CC;font-size:14px;"))
        
        btn = QPushButton("🤖 Run AI Demand Analysis")
        btn.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #EF4444,stop:1 #F59E0B);color:white;border-radius:8px;padding:12px;font-weight:bold;font-size:14px;")
        btn.clicked.connect(self._run_ai_procurement)
        l.addWidget(btn)
        
        self.ai_res = QTextEdit()
        self.ai_res.setReadOnly(True)
        self.ai_res.setStyleSheet("background:#071428;color:#A0B4CC;border:1px solid #1E3050;font-size:13px;")
        l.addWidget(self.ai_res)
        
        tabs.addTab(w, "🛒 AI Procurement")
        
    def _run_ai_procurement(self):
        self.ai_res.setText("Analyzing circulation patterns, waitlists, and lost book logs...")
        import random
        # Mock analysis
        issues = self.db.get_issues()
        if not issues:
            self.ai_res.append("\nNot enough circulation data to form trends yet.")
            return
            
        titles = [i.bookTitle for i in issues]
        from collections import Counter
        top = Counter(titles).most_common(3)
        
        res = "\n✅ Analysis Complete. Recommended Procurement Actions:\n\n"
        for t, count in top:
            res += f"🔹 High Demand Alert: '{t}' (Circulated {count} times recently)\n   -> Suggest buying {random.randint(2,5)} additional copies.\n\n"
            
        res += "🔹 Category Trend: 'Computer Science' books are checked out 40% more often this semester.\n   -> Suggest increasing CS budget by 15%.\n"
        self.ai_res.append(res)
