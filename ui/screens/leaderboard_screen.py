import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame
)
from PyQt6.QtCore import Qt

class Colors:
    PRIMARY = "#1E5FD4"
    SECONDARY = "#2872F0"
    SURFACE = "#0D1F38"
    SURFACE_VARIANT = "#1E3050"
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    DANGER = "#EF4444"

class LeaderboardScreen(QWidget):
    def __init__(self, db_helper):
        super().__init__()
        self.db = db_helper
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QLabel("🏆 Gamification & Leaderboard")
        header.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {Colors.PRIMARY};")
        
        sub = QLabel("Encouraging reading culture through points, ranks, and digital badges.")
        sub.setStyleSheet("color: #6B8CAE; font-size: 14px;")
        
        layout.addWidget(header)
        layout.addWidget(sub)

        # Top 3 Podium (Simulated UI)
        podium_layout = QHBoxLayout()
        podium_layout.addStretch()
        
        podium_layout.addWidget(self.create_podium_card("🥈 2nd Place", "Alice Smith", "1,250 pts", "Avid Reader", "#C0C0C0"))
        podium_layout.addWidget(self.create_podium_card("🥇 1st Place", "John Doe", "1,500 pts", "Top Scholar", "#FFD700"))
        podium_layout.addWidget(self.create_podium_card("🥉 3rd Place", "Bob Johnson", "950 pts", "Bookworm", "#CD7F32"))
        
        podium_layout.addStretch()
        layout.addLayout(podium_layout)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Rank", "Member Name", "Books Read", "Total Points", "Current Badge"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: #071428; color: white; border: 1px solid {Colors.SURFACE_VARIANT}; border-radius: 5px; }}
            QHeaderView::section {{ background-color: {Colors.PRIMARY}; color: white; padding: 5px; font-weight: bold; border: none; }}
        """)
        layout.addWidget(self.table)
        self.load_data()

    def create_podium_card(self, rank, name, points, badge, color):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {Colors.SURFACE}; border: 2px solid {color}; border-radius: 10px;")
        frame.setFixedSize(180, 150)
        v = QVBoxLayout(frame)
        
        l_rank = QLabel(rank)
        l_rank.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        l_rank.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        l_name = QLabel(name)
        l_name.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        l_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        l_pts = QLabel(points)
        l_pts.setStyleSheet("color: #2EC98A; font-size: 14px;")
        l_pts.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        l_badge = QLabel(f"🛡️ {badge}")
        l_badge.setStyleSheet("color: #6B8CAE; font-size: 12px;")
        l_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        v.addWidget(l_rank)
        v.addWidget(l_name)
        v.addWidget(l_pts)
        v.addWidget(l_badge)
        return frame

    def load_data(self):
        try:
            members = self.db.get_members()
            # Sort members by booksIssued descending
            members.sort(key=lambda x: x.booksIssued, reverse=True)
            
            self.table.setRowCount(len(members))
            for row, m in enumerate(members):
                points = m.booksIssued * 50
                badge = "Top Scholar" if points > 1000 else "Avid Reader" if points > 500 else "Novice"
                
                self.table.setItem(row, 0, QTableWidgetItem(f"#{row+1}"))
                self.table.setItem(row, 1, QTableWidgetItem(m.name))
                self.table.setItem(row, 2, QTableWidgetItem(str(m.booksIssued)))
                self.table.setItem(row, 3, QTableWidgetItem(f"{points} pts"))
                self.table.setItem(row, 4, QTableWidgetItem(badge))
        except Exception as e:
            pass
