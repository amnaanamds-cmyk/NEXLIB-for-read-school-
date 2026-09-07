"""
ui/screens/reports_screen.py — Generate and export PDF reports.
Features: Financial valuation, Top Publishers chart, Availability donut,
           Leaderboards, WhatsApp reminders, Full PDF analytics.
"""
import os
import subprocess
import time
import webbrowser
from urllib.parse import quote
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QFileDialog, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from services.report_service import ReportService
from services.advanced_service import AdvancedService


class ReportWorker(QThread):
    finished = pyqtSignal(bool, str)
    def __init__(self, db, report_type, path):
        super().__init__()
        self.db = db
        self.report_type = report_type
        self.path = path

    def run(self):
        try:
            stats = self._compute_local_stats()
            profile = self.db.get_school_profile()
            rs = ReportService(profile.get("name", "School Library"), profile.get("address", ""))
            if self.report_type == "stats":
                rs.generate_stats_report(stats, self.path)
            elif self.report_type == "director":
                rs.generate_director_report(stats, self.path)
            elif self.report_type == "full_analytics":
                rs.generate_full_analytics_report(stats, self.db, self.path)
            self.finished.emit(True, self.path)
        except Exception as e:
            self.finished.emit(False, str(e))

    def _compute_local_stats(self):
        from datetime import datetime, timedelta
        books = self.db.get_books()
        members = self.db.get_members()
        issues = self.db.get_issues()
        reservations = self.db.get_reservations()

        total_books = len(books)
        available = sum(1 for b in books if b.status == "Available")
        issued = sum(1 for b in books if b.status == "Issued")
        today = time.strftime("%Y-%m-%d")
        overdue = sum(1 for r in issues if r.status == "Issued" and r.dueDate and r.dueDate < today)

        cats = {}
        publishers = {}
        for b in books:
            c = b.category or "Uncategorized"
            cats[c] = cats.get(c, 0) + 1
            p = b.publisher or "Unknown"
            publishers[p] = publishers.get(p, 0) + 1

        total_value = sum(b.price for b in books if b.price > 0)
        total_fine = sum(r.fine for r in issues if r.fine > 0)

        now = datetime.now()
        this_month = now.replace(day=1).strftime("%Y-%m-%d")
        last_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
        this_month_count = sum(1 for r in issues if r.issueDate and r.issueDate >= this_month)
        last_month_count = sum(1 for r in issues if r.issueDate and last_month <= r.issueDate < this_month)

        top_borrowers = {}
        top_books = {}
        for r in issues:
            top_borrowers[r.memberName] = top_borrowers.get(r.memberName, 0) + 1
            top_books[r.bookTitle] = top_books.get(r.bookTitle, 0) + 1

        digital = sum(1 for b in books if b.isDigital)
        with_isbn = sum(1 for b in books if b.isbn)

        return {
            "totalBooks": total_books, "availableBooks": available, "issuedBooks": issued,
            "totalMembers": len(members), "overdueCount": overdue,
            "pendingReservations": len([r for r in reservations if r.status == "Pending"]),
            "categories": cats, "publishers": publishers,
            "totalCollectionValue": total_value, "totalFineCollected": total_fine,
            "thisMonthIssues": this_month_count, "lastMonthIssues": last_month_count,
            "topBorrowers": dict(sorted(top_borrowers.items(), key=lambda x: -x[1])[:10]),
            "topBooks": dict(sorted(top_books.items(), key=lambda x: -x[1])[:10]),
            "digitalizationProgress": {
                "withIsbn": round(with_isbn / total_books * 100, 1) if total_books else 0,
                "withEBook": round(digital / total_books * 100, 1) if total_books else 0,
            },
        }


class ReportsScreen(QWidget):
    def __init__(self, db_helper, auth_service):
        super().__init__()
        self.db = db_helper
        self.auth = auth_service
        self.adv = AdvancedService(db_helper)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        hdr = QLabel("\U0001f4ca  Library Reports & Analytics")
        hdr.setStyleSheet("font-size: 26px; font-weight: 900; color: #E8EEF8; font-family: 'Segoe UI';")
        layout.addWidget(hdr)
        layout.addWidget(QLabel("Generate professional reports, interactive charts, and send WhatsApp reminders.",
                              styleSheet="color: #6B8CAE; font-size: 14px; margin-bottom: 10px;"))

        # Feature 6.1: Total Library Financial Valuation
        val_frame = QFrame()
        val_frame.setStyleSheet("background: #0D1F38; border: 2px solid #C8A84B; border-radius: 12px; padding: 16px;")
        val_lay = QHBoxLayout(val_frame)
        val_lay.setContentsMargins(24, 16, 24, 16)
        val_lay.setSpacing(30)
        val_lay.addWidget(QLabel("\U0001f3e6", styleSheet="font-size: 42px; border:none; background:transparent;"))
        self._val_lbl = QLabel("Total Collection Value: Calculating...")
        self._val_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #C8A84B; border:none; background:transparent;")
        val_lay.addWidget(self._val_lbl)
        val_btn = QPushButton("\U0001f50d Calculate")
        val_btn.setStyleSheet("background:#C8A84B;color:#0D1B2A;border:none;border-radius:8px;padding:10px 20px;font-weight:bold;")
        val_btn.clicked.connect(self._calc_valuation)
        val_lay.addWidget(val_btn)
        layout.addWidget(val_frame)

        # Feature 6.2 & 6.3: Charts row
        charts_row = QHBoxLayout()

        # 6.2: Top Publishers bar chart
        pub_card = self._make_card(
            "\U0001f4ca", "Top Publishers",
            "Interactive bar chart of the most represented publishers in your collection.",
            "Generate Publishers Chart", self._gen_publishers_chart,
            color="#1E5FD4"
        )
        charts_row.addWidget(pub_card)

        # 6.3: Availability Ratio donut chart
        avail_card = self._make_card(
            "\U0001f967", "Availability Ratio",
            "Interactive donut chart showing Available vs Issued vs Lost books.",
            "Generate Availability Donut", self._gen_availability_donut,
            color="#10B981"
        )
        charts_row.addWidget(avail_card)
        layout.addLayout(charts_row)

        # Feature 6.4 & 6.5: Leaderboard row
        lb_row = QHBoxLayout()

        lb_books_card = self._make_card(
            "\U0001f3c6", "Leaderboard: Most Issued Books",
            "Top 10 most borrowed books of all time — identify your collection's star performers.",
            "Generate Books Leaderboard", self._gen_books_leaderboard,
            color="#D97706"
        )
        lb_row.addWidget(lb_books_card)

        lb_borrowers_card = self._make_card(
            "\U0001f3c5", "Leaderboard: Most Active Borrowers",
            "Top 10 most active patrons — reward your power users.",
            "Generate Borrowers Leaderboard", self._gen_borrowers_leaderboard,
            color="#7C3AED"
        )
        lb_row.addWidget(lb_borrowers_card)
        layout.addLayout(lb_row)

        # Feature 6.6 & 6.7: WhatsApp Reminders
        wa_frame = QFrame()
        wa_frame.setStyleSheet("background: #0D1F38; border: 1px solid #25D366; border-radius: 12px;")
        wa_lay = QVBoxLayout(wa_frame)
        wa_lay.setContentsMargins(24, 20, 24, 20)
        wa_lay.setSpacing(12)
        wa_lay.addWidget(QLabel("\U0001f4f1  WhatsApp Overdue Reminders",
                              styleSheet="font-size: 18px; font-weight: 700; color: #25D366; border:none; background:transparent;"))
        wa_lay.addWidget(QLabel("Send polite, auto-filled WhatsApp messages to patrons with overdue books. One click opens WhatsApp with pre-filled text.",
                              styleSheet="color:#A0B4CC;font-size:13px;border:none;background:transparent;"))
        wa_btn = QPushButton("\U0001f4f1  1-Click Send All Overdue Reminders via WhatsApp")
        wa_btn.setStyleSheet(
            "background: #25D366; color: white; border: none; border-radius: 8px; "
            "padding: 12px 24px; font-size: 14px; font-weight: 700; font-family: 'Segoe UI';"
        )
        wa_btn.clicked.connect(self._send_whatsapp_reminders)
        wa_lay.addWidget(wa_btn)
        layout.addWidget(wa_frame)

        # Row 2: Standard report cards
        cards_lay = QHBoxLayout()
        cards_lay.setSpacing(20)

        staff_card = self._make_card(
            "\U0001f4c8", "General Statistics",
            "Internal report detailing current inventory, issued books, and active members.",
            "Generate Statistics PDF", self._gen_stats,
            color="#1E5FD4"
        )
        cards_lay.addWidget(staff_card)

        dir_card = self._make_card(
            "\U0001f3af", "Director Pitch Summary",
            "Polished letterhead summary report for the school head or administration.",
            "Generate Pitch PDF", self._gen_director,
            color="#C8A84B"
        )
        cards_lay.addWidget(dir_card)

        overdue_card = self._make_card(
            "\u23f0", "Overdue Books Report",
            "Landscape PDF of all overdue members, days late, and accumulated fine totals.",
            "Generate Overdue PDF", self._gen_overdue,
            color="#DC2626"
        )
        cards_lay.addWidget(overdue_card)
        layout.addLayout(cards_lay)

        # Row 3: Bulk & Full Analytics
        cards_lay2 = QHBoxLayout()
        cards_lay2.setSpacing(20)

        bulk_id_card = self._make_card(
            "\U0001faaa", "Bulk ID Card Print",
            "Generate printable PDF of library ID cards for ALL members (2 per row, A4 format).",
            "Print All ID Cards PDF", self._gen_bulk_id_cards,
            color="#0891B2"
        )
        cards_lay2.addWidget(bulk_id_card)

        full_analytics_card = self._make_card(
            "\U0001f4d1", "Full PDF Analytics Report",
            "Complete analytics report with charts, leaderboards, and financial summary — all in one PDF.",
            "Generate Full Analytics PDF", self._gen_full_analytics,
            color="#9C27B0"
        )
        cards_lay2.addWidget(full_analytics_card)
        layout.addLayout(cards_lay2)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        layout.addWidget(self.progress)

        layout.addStretch()

    def _make_card(self, icon, title, desc, btn_text, callback, color):
        frame = QFrame()
        frame.setStyleSheet(f"background: #0D1F38; border: 1px solid #1E3050; border-top: 4px solid {color}; border-radius: 12px;")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)
        lay.addWidget(QLabel(icon, styleSheet="font-size: 42px; background: transparent; border: none;"))
        lay.addWidget(QLabel(title, styleSheet="font-size: 18px; font-weight: 700; color: #E8EEF8; background: transparent; border: none;"))
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #A0B4CC; font-size: 13px; line-height: 1.4; background: transparent; border: none;")
        lay.addWidget(desc_lbl)
        lay.addStretch()
        btn = QPushButton(btn_text)
        btn.setStyleSheet(f"""
            QPushButton {{ background: {color}; color: {'#0D1B2A' if color=='#C8A84B' else 'white'};
                          border: none; border-radius: 8px; padding: 12px; font-weight: 700; font-size: 14px; }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        btn.clicked.connect(callback)
        lay.addWidget(btn)
        return frame

    # ── Feature 6.1: Financial Valuation ──────────────────────────────────────
    def _calc_valuation(self):
        books = self.db.get_books()
        total_value = sum(b.price for b in books if b.price > 0)
        total_books = len(books)
        priced = sum(1 for b in books if b.price > 0)
        avg_price = total_value / priced if priced > 0 else 0
        self._val_lbl.setText(
            f"Total Collection Value: Rs. {total_value:,.0f}  |  "
            f"{priced}/{total_books} books priced  |  Avg: Rs. {avg_price:,.0f}"
        )

    # ── Feature 6.2: Top Publishers Chart ─────────────────────────────────────
    def _gen_publishers_chart(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Publishers Chart", "Top_Publishers_Chart.pdf", "PDF Files (*.pdf)")
        if not path: return
        self.progress.setRange(0, 0); self.progress.show()
        try:
            from services.advanced_service import AdvancedService
            adv = AdvancedService(self.db)
            books = self.db.get_books()
            publishers = {}
            for b in books:
                p = b.publisher or "Unknown"
                publishers[p] = publishers.get(p, 0) + 1
            top_pubs = dict(sorted(publishers.items(), key=lambda x: -x[1])[:10])

            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Image as RLImage
            from reportlab.lib.units import cm
            import io

            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor('#0D1F38')
            ax.set_facecolor('#071428')
            bars = ax.barh(list(top_pubs.keys()), list(top_pubs.values()), color='#2872F0', height=0.6)
            ax.set_title("Top 10 Publishers by Book Count", color="#E8EEF8", fontsize=13, fontweight='bold')
            ax.set_xlabel("Number of Books", color="#A0B4CC")
            ax.tick_params(colors='#A0B4CC')
            for spine in ax.spines.values():
                spine.set_color('#1E3050')
            for bar, val in zip(bars, top_pubs.values()):
                ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2, str(val),
                       va='center', color='#E8EEF8', fontsize=10, fontweight='bold')
            plt.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)

            doc = SimpleDocTemplate(path, pagesize=A4)
            doc.build([RLImage(buf, width=16*cm, height=8*cm)])
            self.progress.hide()
            reply = QMessageBox.information(self, "Success", f"Chart saved to:\n{path}\n\nOpen now?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(path) if os.name == 'nt' else subprocess.call(['open', path])
        except Exception as e:
            self.progress.hide()
            QMessageBox.warning(self, "Error", str(e))

    # ── Feature 6.3: Availability Donut ───────────────────────────────────────
    def _gen_availability_donut(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Availability Donut", "Availability_Ratio.pdf", "PDF Files (*.pdf)")
        if not path: return
        self.progress.setRange(0, 0); self.progress.show()
        try:
            books = self.db.get_books()
            available = sum(1 for b in books if b.status == "Available")
            issued = sum(1 for b in books if b.status == "Issued")
            lost = sum(1 for b in books if b.status == "Lost")
            other = len(books) - available - issued - lost

            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Image as RLImage
            from reportlab.lib.units import cm
            import io

            fig, ax = plt.subplots(figsize=(8, 8))
            fig.patch.set_facecolor('#0D1F38')
            sizes = [available, issued, lost, max(other, 0)]
            labels = [f'Available ({available})', f'Issued ({issued})', f'Lost ({lost})', f'Other ({max(other,0)})']
            colors_list = ['#10B981', '#F59E0B', '#EF4444', '#6B8CAE']
            nonzero = [(s, l, c) for s, l, c in zip(sizes, labels, colors_list) if s > 0]
            if nonzero:
                sz, lb, cl = zip(*nonzero)
                wedges, texts, autotexts = ax.pie(sz, labels=lb, colors=cl, autopct='%1.1f%%',
                    startangle=90, wedgeprops={"linewidth": 2, "edgecolor": "#0D1F38"},
                    textprops={"color": "#E8EEF8", "fontsize": 12})
                for t in autotexts:
                    t.set_fontweight('bold')
            ax.set_title("Book Availability Ratio", color="#E8EEF8", fontsize=16, fontweight='bold')
            plt.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)

            doc = SimpleDocTemplate(path, pagesize=A4)
            doc.build([RLImage(buf, width=14*cm, height=14*cm)])
            self.progress.hide()
            reply = QMessageBox.information(self, "Success", f"Donut chart saved to:\n{path}\n\nOpen now?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(path) if os.name == 'nt' else subprocess.call(['open', path])
        except Exception as e:
            self.progress.hide()
            QMessageBox.warning(self, "Error", str(e))

    # ── Feature 6.4: Most Issued Books Leaderboard ───────────────────────────
    def _gen_books_leaderboard(self):
        self._gen_leaderboard_pdf("books")

    # ── Feature 6.5: Most Active Borrowers Leaderboard ────────────────────────
    def _gen_borrowers_leaderboard(self):
        self._gen_leaderboard_pdf("borrowers")

    def _gen_leaderboard_pdf(self, mode):
        kind = "Most Issued Books" if mode == "books" else "Most Active Borrowers"
        path, _ = QFileDialog.getSaveFileName(self, f"Save {kind} Leaderboard",
                                               f"Leaderboard_{mode.title()}.pdf", "PDF Files (*.pdf)")
        if not path: return
        self.progress.setRange(0, 0); self.progress.show()
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER
            from reportlab.lib.units import cm

            issues = self.db.get_issues()
            if mode == "books":
                counts = {}
                for r in issues:
                    key = f"{r.bookTitle} | {r.bookIsbn}"
                    counts[key] = counts.get(key, 0) + 1
                sorted_items = sorted(counts.items(), key=lambda x: -x[1])[:10]
                headers = ["Rank", "Book Title | ISBN", "Times Issued"]
                rows = [[f"#{i+1}", k, str(v)] for i, (k, v) in enumerate(sorted_items)]
            else:
                counts = {}
                for r in issues:
                    counts[r.memberName] = counts.get(r.memberName, 0) + 1
                sorted_items = sorted(counts.items(), key=lambda x: -x[1])[:10]
                headers = ["Rank", "Member Name", "Books Borrowed"]
                rows = [[f"#{i+1}", k, str(v)] for i, (k, v) in enumerate(sorted_items)]

            gold = colors.HexColor("#C8A84B")
            dark = colors.HexColor("#0D1B2A")

            doc = SimpleDocTemplate(path, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
            styles = getSampleStyleSheet()
            story = []
            story.append(Paragraph(f"LEADERBOARD: {kind.upper()}", ParagraphStyle(
                "h", fontSize=18, fontName="Helvetica-Bold", textColor=dark, alignment=TA_CENTER)))
            story.append(Paragraph(f"{self.db.get_school_name()}  \u2022  Generated: {time.strftime('%B %d, %Y')}",
                ParagraphStyle("sub", fontSize=10, textColor=colors.grey, alignment=TA_CENTER)))
            story.append(Spacer(1, 0.3*cm))
            story.append(HRFlowable(width="100%", thickness=2, color=gold))
            story.append(Spacer(1, 0.5*cm))

            if rows:
                data = [headers] + rows
                tbl = Table(data, colWidths=[2*cm, 10*cm, 4*cm])
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0), dark),
                    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                    ("FONTSIZE", (0,0), (-1,-1), 11),
                    ("ALIGN", (0,0), (0,-1), "CENTER"),
                    ("ALIGN", (2,0), (2,-1), "CENTER"),
                    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#F0F4FF"), colors.white]),
                    ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
                    ("PADDING", (0,0), (-1,-1), 8),
                ]))
                story.append(tbl)
            else:
                story.append(Paragraph("No data available yet.", styles["Normal"]))

            doc.build(story)
            self.progress.hide()
            reply = QMessageBox.information(self, "Success", f"Leaderboard saved to:\n{path}\n\nOpen now?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(path) if os.name == 'nt' else subprocess.call(['open', path])
        except Exception as e:
            self.progress.hide()
            QMessageBox.warning(self, "Error", str(e))

    # ── Features 6.6 & 6.7: WhatsApp Overdue Reminders ───────────────────────
    def _send_whatsapp_reminders(self):
        issues = self.db.get_issues()
        members_db = self.db.get_members()
        member_map = {m.id: m for m in members_db}
        today = time.strftime("%Y-%m-%d")
        overdue = [r for r in issues if r.status == "Issued" and r.dueDate and r.dueDate < today]

        if not overdue:
            QMessageBox.information(self, "No Overdue", "No overdue books found. All patrons are on time!")
            return

        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
        dlg = QDialog(self)
        dlg.setWindowTitle(f"\U0001f4f1 WhatsApp Reminders — {len(overdue)} Overdue Book(s)")
        dlg.setMinimumSize(700, 500)
        dlg.setStyleSheet("background:#0D1B2A; color:#E8EEF8;")
        lay = QVBoxLayout(dlg)

        lay.addWidget(QLabel(f"Select patrons to send WhatsApp reminders ({len(overdue)} overdue):",
                            styleSheet="font-size:14px; color:#25D366; font-weight:bold;"))

        table = QTableWidget(len(overdue), 5)
        table.setHorizontalHeaderLabels(["Send", "Member", "Phone", "Book", "Days Overdue"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet("background:#071428;color:#E8EEF8;gridline-color:#1E3050;")

        from datetime import datetime
        for row, r in enumerate(overdue):
            member = member_map.get(r.memberId)
            phone = member.phone if member else ""
            try:
                days = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(r.dueDate, "%Y-%m-%d")).days
            except:
                days = 0

            from PyQt6.QtWidgets import QTableWidgetItem as QTI
            send_cb = QTableWidgetItem()
            send_cb.setCheckState(Qt.CheckState.Checked)
            table.setItem(row, 0, send_cb)
            table.setItem(row, 1, QTableWidgetItem(r.memberName or "Unknown"))
            table.setItem(row, 2, QTableWidgetItem(phone))
            table.setItem(row, 3, QTableWidgetItem(r.bookTitle or ""))
            table.setItem(row, 4, QTableWidgetItem(f"{days} days"))

        lay.addWidget(table)

        btn_row = QHBoxLayout()
        send_btn = QPushButton("\U0001f4f1  Send Selected WhatsApp Messages")
        send_btn.setStyleSheet("background:#25D366;color:white;border:none;border-radius:8px;padding:12px 24px;font-size:14px;font-weight:bold;")
        send_btn.clicked.connect(lambda: self._open_whatsapp_batch(table, overdue, member_map, dlg))
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background:#1E3050;color:#6B8CAE;border:none;border-radius:8px;padding:10px 20px;")
        close_btn.clicked.connect(dlg.accept)
        btn_row.addStretch()
        btn_row.addWidget(send_btn)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)
        dlg.exec()

    def _open_whatsapp_batch(self, table, overdue, member_map, dlg):
        """Open WhatsApp for each selected overdue patron with pre-filled message."""
        from datetime import datetime
        today = time.strftime("%Y-%m-%d")
        opened = 0
        for row in range(table.rowCount()):
            if table.item(row, 0).checkState() == Qt.CheckState.Checked:
                issue = overdue[row]
                member = member_map.get(issue.memberId)
                phone = member.phone if member else ""
                try:
                    days = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(issue.dueDate, "%Y-%m-%d")).days
                except:
                    days = 0

                # Feature 6.7: Auto-filled polite message
                msg = (
                    f"Dear {issue.memberName}, this is a friendly reminder from {self.db.get_school_name()}. "
                    f"'{issue.bookTitle}' was due on {issue.dueDate} and is now {days} day(s) overdue. "
                    f"Please return it at your earliest convenience to avoid further fines. Thank you!"
                )

                if phone:
                    clean_phone = phone.replace("+", "").replace("-", "").replace(" ", "")
                    if not clean_phone.startswith("92"):
                        clean_phone = "92" + clean_phone.lstrip("0")
                    wa_url = f"https://wa.me/{clean_phone}?text={quote(msg)}"
                else:
                    wa_url = f"https://wa.me/?text={quote(msg)}"

                try:
                    webbrowser.open(wa_url)
                    opened += 1
                except Exception:
                    pass

        if opened > 0:
            QMessageBox.information(dlg, "Sent", f"Opened WhatsApp for {opened} patron(s) with pre-filled reminders.")
        else:
            QMessageBox.warning(dlg, "No Selection", "No patrons were selected.")
        dlg.accept()

    # ── Feature 6.8: Full PDF Analytics Report ───────────────────────────────
    def _gen_full_analytics(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Full Analytics Report",
                                               "Full_Analytics_Report.pdf", "PDF Files (*.pdf)")
        if not path: return
        self._gen_report("full_analytics", path)

    # ── Standard Reports ──────────────────────────────────────────────────────
    def _gen_stats(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "Library_Statistics_Report.pdf", "PDF Files (*.pdf)")
        if not path: return
        self._gen_report("stats", path)

    def _gen_director(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "Administrative_Summary_Report.pdf", "PDF Files (*.pdf)")
        if not path: return
        self._gen_report("director", path)

    def _gen_overdue(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Overdue Report", "Overdue_Books_Report.pdf", "PDF Files (*.pdf)")
        if not path: return
        self.progress.setRange(0, 0); self.progress.show()
        try:
            issues = self.db.get_issues()
            try:
                fine_rate = self.db.get_fine_rate()
            except Exception:
                fine_rate = 5.0
            self.adv.generate_overdue_report(issues, fine_rate, path)
            self.progress.hide()
            reply = QMessageBox.information(self, "Success", f"Overdue report saved to:\n{path}\n\nOpen it now?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(path) if os.name == 'nt' else subprocess.call(['open', path])
        except Exception as e:
            self.progress.hide()
            QMessageBox.warning(self, "Error", f"Failed to generate overdue report:\n{e}")

    def _gen_bulk_id_cards(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save ID Cards PDF", "All_Member_ID_Cards.pdf", "PDF Files (*.pdf)")
        if not path: return
        self.progress.setRange(0, 0); self.progress.show()
        try:
            members = self.db.get_members()
            if not members:
                self.progress.hide()
                QMessageBox.information(self, "No Members", "No members found in local database.")
                return
            self.adv.generate_id_cards_pdf(members, path)
            self.progress.hide()
            reply = QMessageBox.information(self, "Success",
                f"ID cards for {len(members)} member(s) saved to:\n{path}\n\nOpen now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(path) if os.name == 'nt' else subprocess.call(['open', path])
        except Exception as e:
            self.progress.hide()
            QMessageBox.warning(self, "Error", f"Failed to generate ID cards:\n{e}")

    def _gen_report(self, r_type, default_name):
        self.progress.setRange(0, 0); self.progress.show()
        self.worker = ReportWorker(self.db, r_type, default_name)
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    def _on_done(self, ok, res):
        self.progress.hide()
        if ok:
            reply = QMessageBox.information(self, "Success", f"Report saved to:\n{res}\n\nOpen it now?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(res) if os.name == 'nt' else subprocess.call(['open', res])
        else:
            QMessageBox.warning(self, "Error", f"Failed to generate report: {res}")
