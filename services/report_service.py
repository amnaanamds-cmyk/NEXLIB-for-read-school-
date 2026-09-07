"""
services/report_service.py
PDF report generation using ReportLab and matplotlib chart rendering.
"""
import io
import time
from typing import List

import config

try:
    import matplotlib
    matplotlib.use("Agg")  # headless backend for rendering to bytes
    import matplotlib.pyplot as plt
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    HAS_REPORTS = True
except ImportError:
    HAS_REPORTS = False

from models import Book, Member, IssueRecord


class ReportService:

    def __init__(self, school_name: str = "School Library", school_address: str = ""):
        self.school_name = school_name or "School Library"
        self.school_address = school_address or "Library Management System"

    def _check_reports_available(self):
        if not HAS_REPORTS:
            raise ImportError("The 'reportlab' and 'matplotlib' libraries are required for PDF reports. "
                             "Please install them using: pip install reportlab matplotlib")

    def _letterhead(self, story, styles, title: str, subtitle: str = ""):
        self._check_reports_available()
        """Add a polished letterhead to the report."""
        gold = colors.HexColor("#C8A84B")
        dark = colors.HexColor("#0D1B2A")

        story.append(Paragraph(
            f"🏛 {self.school_name}",
            ParagraphStyle("header", fontSize=20, textColor=dark,
                           fontName="Helvetica-Bold", alignment=TA_CENTER)
        ))
        story.append(Paragraph(
            self.school_address,
            ParagraphStyle("sub", fontSize=11, textColor=colors.grey,
                           alignment=TA_CENTER)
        ))
        story.append(HRFlowable(width="100%", thickness=2, color=gold))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            title,
            ParagraphStyle("title", fontSize=16, textColor=dark,
                           fontName="Helvetica-Bold", alignment=TA_CENTER)
        ))
        if subtitle:
            story.append(Paragraph(
                subtitle,
                ParagraphStyle("subtitle", fontSize=10, textColor=colors.grey,
                               alignment=TA_CENTER)
            ))
        story.append(Spacer(1, 0.5 * cm))

    def _chart_image(self, fig) -> Image:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)
        return Image(buf, width=15 * cm, height=7 * cm)

    # ── Statistics Report ─────────────────────────────────────────────────────
    def generate_stats_report(self, stats: dict, output_path: str):
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        story = []
        date_str = time.strftime("%B %d, %Y — %I:%M %p")

        self._letterhead(story, styles, "Library Statistics Report", date_str)

        # Summary cards table
        card_data = [
            ["📚 Total Books", str(stats.get("totalBooks", 0)),
             "✅ Available", str(stats.get("availableBooks", 0))],
            ["📖 Issued", str(stats.get("issuedBooks", 0)),
             "👥 Members", str(stats.get("totalMembers", 0))],
            ["⏰ Overdue", str(stats.get("overdueCount", 0)),
             "🔔 Reservations", str(stats.get("pendingReservations", 0))],
        ]
        tbl = Table(card_data, colWidths=[5*cm, 3*cm, 5*cm, 3*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F4FF")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0D1B2A")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1),
             [colors.HexColor("#E8F0FE"), colors.HexColor("#F8F9FF")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.5*cm))

        # Category breakdown chart
        categories = stats.get("categories", {})
        if categories:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.bar(list(categories.keys()), list(categories.values()),
                   color="#1E5FD4", edgecolor="white")
            ax.set_title("Books by Category", fontsize=13, fontweight="bold")
            ax.set_xlabel("Category")
            ax.set_ylabel("Count")
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            story.append(self._chart_image(fig))

        doc.build(story)
        return output_path

    # ── Administrative Summary Report ─────────────────────────────────────────
    def generate_director_report(self, stats: dict, output_path: str):
        """Polished letterhead-style administrative summary PDF for the school head."""
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        story = []
        date_str = time.strftime("%B %d, %Y")
        gold = colors.HexColor("#C8A84B")
        dark = colors.HexColor("#0D1B2A")

        self._letterhead(story, styles,
                         "ADMINISTRATIVE SUMMARY REPORT",
                         f"Library Overview  |  {date_str}")

        # Library KPIs
        story.append(Paragraph("Library Overview", styles["Heading2"]))
        kpi_data = [
            ["Indicator", "Value"],
            ["Total Books", str(stats.get("totalBooks", 0))],
            ["Total Members", str(stats.get("totalMembers", 0))],
            ["Books Currently Issued", str(stats.get("issuedBooks", 0))],
            ["Overdue Books", str(stats.get("overdueCount", 0))],
            ["Pending Reservations", str(stats.get("pendingReservations", 0))],
        ]
        kpi_tbl = Table(kpi_data, colWidths=[10*cm, 6*cm])
        kpi_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), dark),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#F0F4FF"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 0.5*cm))

        # Digitalization Progress
        story.append(Paragraph("Digitalization Progress", styles["Heading2"]))
        dp = stats.get("digitalizationProgress", {})
        prog_data = [
            ["Metric", "Percentage"],
            ["Books with ISBN", f"{dp.get('withIsbn', 0)}%"],
            ["Books with E-Book Link", f"{dp.get('withEBook', 0)}%"],
        ]
        prog_tbl = Table(prog_data, colWidths=[10*cm, 6*cm])
        prog_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), gold),
            ("TEXTCOLOR", (0, 0), (-1, 0), dark),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#FFFBEF"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(prog_tbl)
        story.append(Spacer(1, 0.5*cm))

        # Category distribution pie chart
        categories = stats.get("categories", {})
        if categories:
            fig, ax = plt.subplots(figsize=(8, 5))
            wedge_props = {"linewidth": 2, "edgecolor": "white"}
            ax.pie(
                list(categories.values()),
                labels=list(categories.keys()),
                autopct="%1.1f%%",
                startangle=140,
                wedgeprops=wedge_props,
            )
            ax.set_title("Subject Distribution",
                         fontsize=13, fontweight="bold")
            plt.tight_layout()
            story.append(self._chart_image(fig))

        # Footer
        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=gold))
        story.append(Paragraph(
            f"Generated by {config.APP_NAME}  \u2022  {date_str}  \u2022  CONFIDENTIAL",
            ParagraphStyle("foot", fontSize=8, textColor=colors.grey,
                           alignment=TA_CENTER)
        ))

        doc.build(story)
        return output_path

    # \u2501\u2501\u2501 Feature 6.8: Full Analytics Report \u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
    def generate_full_analytics_report(self, stats: dict, db_helper, output_path: str):
        """Complete analytics report with charts, leaderboards, and financial summary."""
        self._check_reports_available()
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import io

        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        story = []
        date_str = time.strftime("%B %d, %Y \u2014 %I:%M %p")

        self._letterhead(story, styles, "COMPLETE LIBRARY ANALYTICS REPORT", date_str)

        # Executive Summary
        story.append(Paragraph("Executive Summary", styles["Heading2"]))
        summary_data = [
            ["\U0001f4da Total Books", str(stats.get("totalBooks", 0)),
             "\u2705 Available", str(stats.get("availableBooks", 0))],
            ["\U0001f4d6 Issued", str(stats.get("issuedBooks", 0)),
             "\U0001f465 Members", str(stats.get("totalMembers", 0))],
            ["\u23f0 Overdue", str(stats.get("overdueCount", 0)),
             "\U0001f514 Reservations", str(stats.get("pendingReservations", 0))],
            ["\U0001f4b0 Collection Value", f"Rs. {stats.get('totalCollectionValue', 0):,.0f}",
             "\U0001f4b0 Fine Collected", f"Rs. {stats.get('totalFineCollected', 0):,.0f}"],
        ]
        tbl = Table(summary_data, colWidths=[5*cm, 3*cm, 5*cm, 3*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F4FF")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0D1B2A")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.5*cm))

        # Monthly Trend Chart
        this_month = stats.get("thisMonthIssues", 0)
        last_month = stats.get("lastMonthIssues", 0)
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.bar(["Last Month", "This Month"], [last_month, this_month], color=['#6B8CAE', '#10B981'], width=0.4)
        ax.set_title("Monthly Issues Trend", fontsize=12, fontweight='bold')
        for i, v in enumerate([last_month, this_month]):
            ax.text(i, v + 0.2, str(v), ha='center', fontweight='bold')
        plt.tight_layout()
        story.append(self._chart_image(fig))
        story.append(Spacer(1, 0.3*cm))

        # Category Distribution
        categories = stats.get("categories", {})
        if categories:
            story.append(Paragraph("Subject Distribution", styles["Heading2"]))
            fig2, ax2 = plt.subplots(figsize=(8, 4))
            ax2.bar(list(categories.keys()), list(categories.values()), color='#1E5FD4', edgecolor='white')
            ax2.set_title("Books by Category", fontsize=12, fontweight='bold')
            plt.xticks(rotation=30, ha='right')
            plt.tight_layout()
            story.append(self._chart_image(fig2))
            story.append(Spacer(1, 0.3*cm))

        # Top Publishers
        publishers = stats.get("publishers", {})
        if publishers:
            story.append(Paragraph("Top Publishers", styles["Heading2"]))
            top_pubs = dict(sorted(publishers.items(), key=lambda x: -x[1])[:10])
            fig3, ax3 = plt.subplots(figsize=(8, 4))
            ax3.barh(list(top_pubs.keys()), list(top_pubs.values()), color='#C8A84B', height=0.5)
            ax3.set_title("Top 10 Publishers", fontsize=12, fontweight='bold')
            plt.tight_layout()
            story.append(self._chart_image(fig3))
            story.append(Spacer(1, 0.3*cm))

        # Top 10 Books
        top_books = stats.get("topBooks", {})
        if top_books:
            story.append(Paragraph("Most Issued Books (Top 10)", styles["Heading2"]))
            tb_data = [["Rank", "Book Title", "Times Issued"]]
            for i, (title, count) in enumerate(list(top_books.items())[:10]):
                tb_data.append([f"#{i+1}", title[:50], str(count)])
            tb_tbl = Table(tb_data, colWidths=[2*cm, 10*cm, 3*cm])
            tb_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0D1B2A")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
                ("FONTSIZE", (0,0), (-1,-1), 9),
                ("PADDING", (0,0), (-1,-1), 6),
            ]))
            story.append(tb_tbl)
            story.append(Spacer(1, 0.3*cm))

        # Top 10 Borrowers
        top_borrowers = stats.get("topBorrowers", {})
        if top_borrowers:
            story.append(Paragraph("Most Active Borrowers (Top 10)", styles["Heading2"]))
            tbr_data = [["Rank", "Member Name", "Books Borrowed"]]
            for i, (name, count) in enumerate(list(top_borrowers.items())[:10]):
                tbr_data.append([f"#{i+1}", name, str(count)])
            tbr_tbl = Table(tbr_data, colWidths=[2*cm, 10*cm, 3*cm])
            tbr_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#7C3AED")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
                ("FONTSIZE", (0,0), (-1,-1), 9),
                ("PADDING", (0,0), (-1,-1), 6),
            ]))
            story.append(tbr_tbl)
            story.append(Spacer(1, 0.3*cm))

        # Footer
        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=2, color=gold))
        story.append(Paragraph(
            f"Generated by {config.APP_NAME}  \u2022  {date_str}  \u2022  CONFIDENTIAL",
            ParagraphStyle("foot", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        ))

        doc.build(story)
        return output_path
