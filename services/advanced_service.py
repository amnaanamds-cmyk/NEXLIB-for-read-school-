"""
services/advanced_service.py — Advanced Utilities: Bulk CSV Import/Export & Barcode Generation.
Includes CSV validation and ReportLab barcode generation sheet.
"""
import csv
import io
import json
import uuid
import time
import requests
from typing import List, Tuple, Dict
import pandas as pd

# Optional imports for Barcodes
try:
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics.barcodes import code39
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from models import Book, Member
from services.database_helper import DatabaseHelper
from collections import Counter


class AdvancedService:
    def __init__(self, db_helper: DatabaseHelper):
        self.db = db_helper

    # ─── Bulk Import: Books (CSV, Excel, JSON) ───────────────────────────────
    def import_books(self, file_path: str) -> Tuple[int, int, List[str]]:
        """
        Import books from a CSV, Excel, or JSON file.
        Returns: (success_count, fail_count, list_of_error_messages)
        """
        success = 0
        fails = 0
        errors = []

        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path)
            elif file_path.endswith('.pdf'):
                try:
                    import pdfplumber
                except ImportError:
                    return 0, 1, ["The 'pdfplumber' library is required for PDF import. Please run: pip install pdfplumber"]
                
                rows = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        table = page.extract_table()
                        if table:
                            rows.extend(table)
                if not rows or len(rows) < 2:
                    return 0, 1, ["No tabular data found in PDF or missing headers."]
                df = pd.DataFrame(rows[1:], columns=rows[0])
            elif file_path.endswith('.mrc'):
                try:
                    from pymarc import MARCReader
                except ImportError:
                    return 0, 1, ["The 'pymarc' library is required for MARC21 import. Please run: pip install pymarc"]
                
                with open(file_path, 'rb') as f:
                    reader = MARCReader(f)
                    for record in reader:
                        if record is None:
                            fails += 1
                            continue
                        try:
                            title = record.title() if record.title() else "Unknown Title"
                            author = record.author() if record.author() else ""
                            isbn = record.isbn() if record.isbn() else ""
                            acc_no = record['001'].data if '001' in record else ""
                            publisher = record.publisher() if hasattr(record, 'publisher') and record.publisher() else ""
                            pub_year = record.pubyear() if hasattr(record, 'pubyear') and record.pubyear() else ""
                            
                            book = Book(
                                syncId=str(uuid.uuid4()),
                                isbn=isbn,
                                accNo=acc_no,
                                title=title,
                                author=author,
                                publisher=publisher,
                                publishDate=pub_year,
                                status="Available",
                                category="Uncategorized",
                                lastUpdated=int(time.time() * 1000),
                                deleted=False
                            )
                            self.db.save_book(book)
                            success += 1
                        except Exception as row_err:
                            errors.append(f"MARC Record Error: {str(row_err)}")
                            fails += 1
                return success, fails, errors
            else:
                return 0, 1, ["Unsupported file format. Please use CSV, Excel, JSON, or MRC."]

            # Lowercase columns for case-insensitive matching
            df.columns = [str(c).strip().lower() for c in df.columns]

            # Replace NaNs with empty strings
            df = df.fillna('')
            
            # Verify headers
            required = {"title"}
            headers = set(df.columns)
            if not required.issubset(headers):
                missing = required - headers
                return 0, 1, [f"Document missing required columns: {', '.join(missing)}"]
            
            for index, row in df.iterrows():
                try:
                    title = str(row.get("title", "")).strip()
                    if not title:
                        errors.append(f"Row {index+2}: Title is empty.")
                        fails += 1
                        continue

                    isbn = str(row.get("isbn", "")).replace("-", "").replace(" ", "")
                    acc_no = str(row.get("accno", "")).strip()
                    
                    book = Book(
                        syncId=str(uuid.uuid4()),
                        isbn=isbn,
                        accNo=acc_no,
                        title=title,
                        author=str(row.get("author", "")).strip(),
                        publisher=str(row.get("publisher", "")).strip(),
                        publisherPlace=str(row.get("publisherplace", "")).strip(),
                        publishDate=str(row.get("publishdate", "")).strip(),
                        edition=str(row.get("edition", "")).strip(),
                        pages=int(row.get("pages", 0) or 0),
                        procurement=str(row.get("procurement", "")).strip(),
                        volume=str(row.get("volume", "")).strip(),
                        price=float(row.get("price", 0.0) or 0.0),
                        status="Available",
                        category=str(row.get("category", "Uncategorized")).strip() or "Uncategorized",
                        lastUpdated=int(time.time() * 1000),
                        deleted=False
                    )
                    self.db.save_book(book)
                    success += 1
                except Exception as row_err:
                    errors.append(f"Row {index+2}: {str(row_err)}")
                    fails += 1
        except Exception as e:
            return 0, 1, [f"Could not open file: {e}"]

        return success, fails, errors

    # ─── Bulk Import: Members (CSV, Excel, JSON) ─────────────────────────────
    def import_members(self, file_path: str) -> Tuple[int, int, List[str]]:
        """
        Import members from CSV, Excel, or JSON.
        """
        success = 0
        fails = 0
        errors = []

        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path)
            elif file_path.endswith('.pdf'):
                try:
                    import pdfplumber
                except ImportError:
                    return 0, 1, ["The 'pdfplumber' library is required for PDF import. Please run: pip install pdfplumber"]
                
                rows = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        table = page.extract_table()
                        if table:
                            rows.extend(table)
                if not rows or len(rows) < 2:
                    return 0, 1, ["No tabular data found in PDF or missing headers."]
                df = pd.DataFrame(rows[1:], columns=rows[0])
            else:
                return 0, 1, ["Unsupported file format. Please use CSV, Excel, or JSON."]

            # Lowercase columns for case-insensitive matching
            df.columns = [str(c).strip().lower() for c in df.columns]

            df = df.fillna('')
                
            required = {"name"}
            headers = set(df.columns)
            if not required.issubset(headers):
                missing = required - headers
                return 0, 1, [f"Document missing columns: {', '.join(missing)}"]
            
            for index, row in df.iterrows():
                try:
                    name = str(row.get("name", "")).strip()
                    member_id = str(row.get("memberid", "")).strip()
                    pin = str(row.get("pin", "1234")).strip()
                    
                    if not name:
                        errors.append(f"Row {index+2}: Name is required.")
                        fails += 1
                        continue

                    member = Member(
                        syncId=str(uuid.uuid4()),
                        memberId=member_id,
                        name=name,
                        email=str(row.get("email", "")).strip(),
                        phone=str(row.get("phone", "")).strip(),
                        department=str(row.get("department", "")).strip(),
                        memberType=str(row.get("membertype", "Student")).strip() or "Student",
                        joinDate=str(row.get("joindate", "")).strip() or time.strftime("%Y-%m-%d"),
                        expiryDate=str(row.get("expirydate", "")).strip() or "2027-12-31",
                        fatherName=str(row.get("fathername", "")).strip(),
                        className=str(row.get("classname", "")).strip(),
                        classNo=str(row.get("classno", "")).strip(),
                        address=str(row.get("address", "")).strip(),
                        designation=str(row.get("designation", "")).strip(),
                        pin=pin,
                        lastUpdated=int(time.time() * 1000),
                        deleted=False
                    )
                    self.db.save_member(member)
                    success += 1
                except Exception as row_err:
                    errors.append(f"Row {index+2}: {str(row_err)}")
                    fails += 1
        except Exception as e:
            return 0, 1, [f"Could not open file: {e}"]

        return success, fails, errors

    # ─── Bulk Import: Issues (CSV, Excel, JSON) ──────────────────────────────
    def import_issues(self, file_path: str) -> Tuple[int, int, List[str]]:
        """
        Import issue/return transactions from CSV, Excel, or JSON.
        """
        success = 0
        fails = 0
        errors = []

        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path)
            else:
                return 0, 1, ["Unsupported file format. Please use CSV, Excel, or JSON."]

            df.columns = [str(c).strip().lower() for c in df.columns]
            df = df.fillna('')
                
            required = {"memberid", "bookaccno"}
            headers = set(df.columns)
            if not required.issubset(headers):
                missing = required - headers
                return 0, 1, [f"Document missing columns: {', '.join(missing)}"]
            
            for index, row in df.iterrows():
                try:
                    member_id = str(row.get("memberid", "")).strip()
                    book_accno = str(row.get("bookaccno", "")).strip()
                    
                    if not member_id or not book_accno:
                        errors.append(f"Row {index+2}: MemberID and BookAccNo are required.")
                        fails += 1
                        continue

                    # Look up member and book names/ids (mock lookup since we might not have them loaded, or we save directly)
                    # For simplicity, we just save the issue record directly to the database.
                    # In a real app we'd fetch the book and member to get their names.
                    members = [m for m in self.db.get_members() if m.memberId == member_id]
                    books = [b for b in self.db.get_books() if b.accNo == book_accno]
                    
                    member_name = members[0].name if members else "Unknown Member"
                    member_db_id = members[0].id if members else 0
                    book_title = books[0].title if books else "Unknown Book"
                    book_isbn = books[0].isbn if books else "Unknown"
                    
                    issue = IssueRecord(
                        syncId=str(uuid.uuid4()),
                        memberId=member_db_id,
                        memberMemberId=member_id,
                        memberName=member_name,
                        bookTitle=book_title,
                        bookIsbn=book_isbn,
                        issueDate=str(row.get("issuedate", "")).strip() or time.strftime("%Y-%m-%d"),
                        dueDate=str(row.get("duedate", "")).strip() or time.strftime("%Y-%m-%d"),
                        returnDate=str(row.get("returndate", "")).strip() or None,
                        status=str(row.get("status", "Issued")).strip(),
                        fine=float(row.get("fine", 0.0) or 0.0),
                        lastUpdated=int(time.time() * 1000)
                    )
                    self.db.save_issue(issue)
                    success += 1
                except Exception as row_err:
                    errors.append(f"Row {index+2}: {str(row_err)}")
                    fails += 1
        except Exception as e:
            return 0, 1, [f"Could not open file: {e}"]

        return success, fails, errors

    # ─── Export Grid to CSV ──────────────────────────────────────────────────
    def export_books_csv(self, file_path: str):
        books = self.db.get_books()
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Title", "Author", "ISBN", "AccNo", "Publisher", "Category", "Status", "DigitalUrl"])
            for b in books:
                writer.writerow([b.title, b.author, b.isbn, b.accNo, b.publisher, b.category, b.status, b.digitalUrl or ""])

    def export_members_csv(self, file_path: str):
        members = self.db.get_members()
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["MemberID", "Name", "Email", "Phone", "Department", "Type", "JoinDate", "ExpiryDate"])
            for m in members:
                writer.writerow([m.memberId, m.name, m.email, m.phone, m.department, m.memberType, m.joinDate, m.expiryDate])

    def export_full_database_csv(self, folder_path: str):
        """Export all tables to CSV files for full backup."""
        import os
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # 1. Books
        self.export_books_csv(os.path.join(folder_path, "books_full_export.csv"))

        # 2. Members
        self.export_members_csv(os.path.join(folder_path, "members_full_export.csv"))

        # 3. Transactions (Issued Books)
        issues = self.db.get_issues(include_deleted=True)
        with open(os.path.join(folder_path, "transactions_export.csv"), mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["SyncID", "BookTitle", "MemberName", "IssueDate", "DueDate", "ReturnDate", "Fine", "Status"])
            for i in issues:
                writer.writerow([i.syncId, i.bookTitle, i.memberName, i.issueDate, i.dueDate, i.returnDate or "", i.fine, i.status])

        # 4. Audit Log
        logs = self.db.get_audit_logs_local(10000)
        with open(os.path.join(folder_path, "audit_log_export.csv"), mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "User", "Action", "Detail", "Time"])
            for l in logs:
                writer.writerow([l.get("id"), l.get("userEmail"), l.get("action"), l.get("detail"), l.get("timestampStr")])

    # ─── Barcode Labels Sheet PDF Generation ─────────────────────────────────
    def generate_barcode_labels_pdf(self, output_path: str):
        """
        Creates an A4 print sheet of barcode labels (Code39) for books in the inventory.
        Uses ReportLab graphics components.
        """
        if not HAS_REPORTLAB:
            raise ImportError("The 'reportlab' library is required for barcode generation. "
                             "Please install it using: pip install reportlab")

        books = [b for b in self.db.get_books() if b.accNo]
        if not books:
            raise ValueError("No books with Acc No found to generate barcodes.")

        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                leftMargin=10*mm, rightMargin=10*mm,
                                topMargin=10*mm, bottomMargin=10*mm)

        data = []
        row = []
        for i, book in enumerate(books):
            # Draw barcode
            d = Drawing(55*mm, 25*mm)
            # Add a white background rect
            d.add(Rect(0, 0, 55*mm, 25*mm, fillColor=None, strokeColor=None))
            
            # Draw standard Code39 barcode
            bc = code39.Extended39(book.accNo, barWidth=0.3*mm, barHeight=12*mm)
            bc.drawOn(d, 5*mm, 8*mm)
            
            # Text descriptors
            # Slice title to avoid overlap
            title_clean = book.title[:20] + "..." if len(book.title) > 20 else book.title
            d.add(String(27.5*mm, 22*mm, title_clean, textAnchor="middle", fontName="Helvetica-Bold", fontSize=8))
            d.add(String(27.5*mm, 2*mm, f"Acc No: {book.accNo}", textAnchor="middle", fontName="Helvetica", fontSize=8))
            
            row.append(d)
            if len(row) == 3:  # 3 columns of barcodes per row
                data.append(row)
                row = []
                
        if row:
            while len(row) < 3:
                row.append("")
            data.append(row)

        tbl = Table(data, colWidths=[63*mm, 63*mm, 63*mm])
        tbl.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6*mm),
            ("TOPPADDING", (0, 0), (-1, -1), 6*mm),
        ]))

        doc.build([tbl])

    # ─── Enterprise Feature: ISBN Auto-Fetch (Multi-Provider: OpenLibrary + Google Books) ──────
    def fetch_book_by_isbn(self, isbn: str) -> Dict[str, str]:
        """
        Queries multiple APIs to automatically retrieve book metadata.
        Provider order: 1. OpenLibrary, 2. Google Books (fallback)
        """
        clean_isbn = isbn.replace("-", "").replace(" ", "").strip()
        if not clean_isbn:
            raise ValueError("ISBN cannot be empty.")
            
        # 1. Try OpenLibrary
        try:
            ol_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{clean_isbn}&jscmd=data&format=json"
            response = requests.get(ol_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                key = f"ISBN:{clean_isbn}"
                if key in data:
                    book_data = data[key]
                    authors = book_data.get("authors", [])
                    publishers = book_data.get("publishers", [])
                    cover = book_data.get("cover", {})
                    return {
                        "title": book_data.get("title", ""),
                        "author": ", ".join([a.get("name", "") for a in authors]),
                        "publisher": ", ".join([p.get("name", "") for p in publishers]),
                        "publishDate": book_data.get("publish_date", ""),
                        "pages": book_data.get("number_of_pages", 0),
                        "cover_url": cover.get("large", cover.get("medium", ""))
                    }
        except Exception:
            pass # Silent fail to try fallback

        # 2. Try Google Books (Indian editions are more common here)
        try:
            gb_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{clean_isbn}"
            resp = requests.get(gb_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("totalItems", 0) > 0:
                    info = data["items"][0]["volumeInfo"]
                    return {
                        "title": info.get("title", ""),
                        "author": ", ".join(info.get("authors", [])),
                        "publisher": info.get("publisher", ""),
                        "publishDate": info.get("publishedDate", ""),
                        "pages": info.get("pageCount", 0),
                        "cover_url": info.get("imageLinks", {}).get("thumbnail", "")
                    }
        except Exception:
            pass

        return {} # Not found anywhere

    # ─── Enterprise Feature: Student/Member ID Card Generator ──────────────────
    def generate_id_cards_pdf(self, members: list, output_path: str):
        """
        Generate a printable PDF sheet of Library ID Cards (2 per row) using ReportLab.
        Each card includes: Name, Member ID, Dept, Type, Expiry.
        """
        if not HAS_REPORTLAB:
            raise ImportError("reportlab is required. Run: pip install reportlab")

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER

        gold = colors.HexColor("#C8A84B")
        dark = colors.HexColor("#0D1B2A")

        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                leftMargin=10*mm, rightMargin=10*mm,
                                topMargin=10*mm, bottomMargin=10*mm)

        name_style = ParagraphStyle("name", fontName="Helvetica-Bold",
                                    fontSize=10, textColor=dark, spaceAfter=2)
        sub_style  = ParagraphStyle("sub", fontName="Helvetica",
                                    fontSize=8, textColor=colors.grey, spaceAfter=1)
        hdr_style  = ParagraphStyle("hdr", fontName="Helvetica-Bold",
                                    fontSize=7, textColor=colors.white, alignment=TA_CENTER)

        cards_data = []
        row_pair = []

        for m in members:
            header = Table([[Paragraph("GDC LIBRARY CARD", hdr_style)]], colWidths=[80*mm])
            header.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), dark),
                ("PADDING", (0,0), (-1,-1), 4),
            ]))
            from reportlab.graphics.shapes import Drawing
            from reportlab.graphics.barcodes import code39
            
            barcode_drawing = Drawing(40*mm, 15*mm)
            if m.memberId:
                bc = code39.Extended39(m.memberId, barWidth=0.25*mm, barHeight=10*mm)
                bc.drawOn(barcode_drawing, 5*mm, 2*mm)

            inner = [
                [header],
                [Paragraph(m.name or "—", name_style)],
                [Paragraph(f"ID: {m.memberId or '—'}", sub_style)],
                [Paragraph(f"Dept: {m.department or '—'}", sub_style)],
                [Paragraph(f"Type: {m.memberType or 'Student'}", sub_style)],
                [Paragraph(f"Expiry: {m.expiryDate or '—'}", sub_style)],
                [Paragraph(f"Class: {m.className or '—'}  |  {m.classNo or ''}", sub_style)],
                [barcode_drawing]
            ]
            card = Table(inner, colWidths=[80*mm])
            card.setStyle(TableStyle([
                ("BOX", (0,0), (-1,-1), 1.5, gold),
                ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F8FAFF")),
                ("PADDING", (0,0), (-1,-1), 5),
                ("TOPPADDING", (0,0), (0,0), 0),
            ]))
            row_pair.append(card)
            if len(row_pair) == 2:
                cards_data.append(row_pair)
                row_pair = []

        if row_pair:
            while len(row_pair) < 2:
                row_pair.append("")
            cards_data.append(row_pair)

        if not cards_data:
            raise ValueError("No members provided for ID card generation.")

        sheet = Table(cards_data, colWidths=[90*mm, 90*mm])
        sheet.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("PADDING", (0,0), (-1,-1), 5),
        ]))
        doc.build([sheet])

    # ─── Enterprise Feature: Fine Receipt PDF Generator ────────────────────────
    def generate_fine_receipt(self, issue_record, member, fine: float, output_path: str):
        """Generate a printable Fine/Return Receipt PDF for a single transaction."""
        if not HAS_REPORTLAB:
            raise ImportError("reportlab is required. Run: pip install reportlab")

        from reportlab.lib.pagesizes import A5
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, HRFlowable)
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        import time

        gold = colors.HexColor("#C8A84B")
        dark = colors.HexColor("#0D1B2A")

        doc = SimpleDocTemplate(output_path, pagesize=A5,
                                topMargin=1*cm, bottomMargin=1*cm,
                                leftMargin=1.5*cm, rightMargin=1.5*cm)
        story = []

        story.append(Paragraph("GDC Library50", ParagraphStyle(
            "h", fontName="Helvetica-Bold", fontSize=14, textColor=dark, alignment=TA_CENTER)))
        story.append(Paragraph("Return / Fine Receipt", ParagraphStyle(
            "sub", fontName="Helvetica", fontSize=9, textColor=colors.grey, alignment=TA_CENTER)))
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width="100%", thickness=1.5, color=gold))
        story.append(Spacer(1, 0.3*cm))
        receipt_no = f"RCPT-{int(time.time())}-{issue_record.syncId[:4] if issue_record.syncId else '0000'}"
        story.append(Paragraph(f"Receipt No: {receipt_no}", ParagraphStyle(
            "sub", fontName="Helvetica-Bold", fontSize=10, textColor=dark, alignment=TA_CENTER)))
        story.append(Spacer(1, 0.3*cm))

        rows = [
            ["Member", member.name if member else "—"],
            ["Member ID", member.memberId if member else "—"],
            ["Book", issue_record.bookTitle or "—"],
            ["ISBN", issue_record.bookIsbn or "—"],
            ["Issued", issue_record.issueDate or "—"],
            ["Due Date", issue_record.dueDate or "—"],
            ["Return Date", issue_record.returnDate or time.strftime("%Y-%m-%d")],
            ["Fine", f"Rs. {fine:.2f}"],
        ]
        tbl = Table(rows, colWidths=[5*cm, 8*cm])
        fine_color = colors.HexColor("#DC2626") if fine > 0 else colors.HexColor("#059669")
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("TEXTCOLOR", (0,0), (-1,-1), dark),
            ("ROWBACKGROUNDS", (0,0), (-1,-1),
             [colors.HexColor("#F0F4FF"), colors.white]),
            ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING", (0,0), (-1,-1), 7),
            ("TEXTCOLOR", (1,7), (1,7), fine_color),
            ("FONTNAME", (1,7), (1,7), "Helvetica-Bold"),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.5*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            f"Receipt generated: {time.strftime('%Y-%m-%d %H:%M:%S')}  —  GDC Library50",
            ParagraphStyle("foot", fontName="Helvetica", fontSize=7,
                           textColor=colors.grey, alignment=TA_CENTER)))
        doc.build(story)

    def generate_issue_slip(self, issue_record, member, output_path: str):
        """Generate a printable Issue Slip PDF for a single transaction."""
        if not HAS_REPORTLAB:
            raise ImportError("reportlab is required. Run: pip install reportlab")

        from reportlab.lib.pagesizes import A5
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, HRFlowable)
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        import time

        gold = colors.HexColor("#C8A84B")
        dark = colors.HexColor("#0D1B2A")

        doc = SimpleDocTemplate(output_path, pagesize=A5,
                                topMargin=1*cm, bottomMargin=1*cm,
                                leftMargin=1.5*cm, rightMargin=1.5*cm)
        story = []

        story.append(Paragraph("GDC Library50", ParagraphStyle(
            "h", fontName="Helvetica-Bold", fontSize=14, textColor=dark, alignment=TA_CENTER)))
        story.append(Paragraph("Issue Slip", ParagraphStyle(
            "sub", fontName="Helvetica", fontSize=9, textColor=colors.grey, alignment=TA_CENTER)))
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width="100%", thickness=1.5, color=gold))
        story.append(Spacer(1, 0.3*cm))

        slip_no = f"ISSUE-{int(time.time())}-{issue_record.syncId[:4] if issue_record.syncId else '0000'}"
        story.append(Paragraph(f"Slip No: {slip_no}", ParagraphStyle(
            "sub", fontName="Helvetica-Bold", fontSize=10, textColor=dark, alignment=TA_CENTER)))
        story.append(Spacer(1, 0.3*cm))

        rows = [
            ["Member", member.name if member else "—"],
            ["Member ID", member.memberId if member else "—"],
            ["Book", issue_record.bookTitle or "—"],
            ["ISBN", issue_record.bookIsbn or "—"],
            ["Issued", issue_record.issueDate or "—"],
            ["Due Date", issue_record.dueDate or "—"],
        ]
        tbl = Table(rows, colWidths=[5*cm, 8*cm])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("TEXTCOLOR", (0,0), (-1,-1), dark),
            ("ROWBACKGROUNDS", (0,0), (-1,-1),
             [colors.HexColor("#F0F4FF"), colors.white]),
            ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING", (0,0), (-1,-1), 7),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.5*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            f"Slip generated: {time.strftime('%Y-%m-%d %H:%M:%S')}  —  GDC Library50",
            ParagraphStyle("foot", fontName="Helvetica", fontSize=7,
                           textColor=colors.grey, alignment=TA_CENTER)))
        doc.build(story)


    # ─── Enterprise Feature: Overdue Members Report ────────────────────────────
    def generate_overdue_report(self, issues: list, fine_rate: float, output_path: str):
        """Generate a full overdue books report PDF listing all overdue members and fine totals."""
        if not HAS_REPORTLAB:
            raise ImportError("reportlab is required. Run: pip install reportlab")

        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, HRFlowable)
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.enums import TA_CENTER
        import time
        from datetime import datetime, date

        gold = colors.HexColor("#C8A84B")
        dark = colors.HexColor("#0D1B2A")
        red  = colors.HexColor("#DC2626")
        today = date.today()

        overdue = []
        for i in issues:
            if i.status != "Issued": continue
            try:
                due = datetime.strptime(i.dueDate, "%Y-%m-%d").date()
                days = (today - due).days
                if days > 0:
                    overdue.append((i, days, days * fine_rate))
            except Exception:
                continue

        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4),
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("OVERDUE BOOKS REPORT", ParagraphStyle(
            "h", fontName="Helvetica-Bold", fontSize=16, textColor=dark, alignment=TA_CENTER)))
        story.append(Paragraph(
            f"GDC Library50  •  Generated: {time.strftime('%Y-%m-%d %H:%M')}  •  Fine Rate: Rs.{fine_rate}/day",
            ParagraphStyle("sub", fontName="Helvetica", fontSize=9,
                           textColor=colors.grey, alignment=TA_CENTER)))
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width="100%", thickness=2, color=gold))
        story.append(Spacer(1, 0.4*cm))

        if not overdue:
            story.append(Paragraph("No overdue books at this time.", styles["Normal"]))
        else:
            data = [["Member", "Member ID", "Book", "Due Date", "Days Overdue", "Fine (Rs.)"]]
            total_fine = 0.0
            for i, days, fine in overdue:
                data.append([
                    i.memberName or "—", i.memberMemberId or "—",
                    i.bookTitle or "—", i.dueDate or "—",
                    str(days), f"{fine:.0f}",
                ])
                total_fine += fine
            data.append(["", "", "", "", "TOTAL FINE:", f"Rs. {total_fine:.0f}"])

            col_widths = [5*cm, 3*cm, 6*cm, 3*cm, 3*cm, 3*cm]
            tbl = Table(data, colWidths=col_widths)
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), dark),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE", (0,0), (-1,-1), 9),
                ("ROWBACKGROUNDS", (0,1), (-1,-2),
                 [colors.HexColor("#FEF2F2"), colors.white]),
                ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#FEF2F2")),
                ("TEXTCOLOR", (4,-1), (-1,-1), red),
                ("FONTNAME", (4,-1), (-1,-1), "Helvetica-Bold"),
                ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
                ("PADDING", (0,0), (-1,-1), 6),
                ("ALIGN", (4,0), (-1,-1), "CENTER"),
            ]))
            story.append(tbl)

        doc.build(story)

    # ─── Koha Feature 1: MARC21 Export ─────────────────────────────────────────
    def export_marc21(self, books: list, output_path: str):
        """Export local catalog to standard MARC21 (.mrc) format for ILS interoperability."""
        try:
            from pymarc import Record, Field
        except ImportError:
            raise ImportError("pymarc is required. Run: pip install pymarc")

        with open(output_path, 'wb') as f:
            for book in books:
                record = Record()
                
                # Control field (001) - Acc No or ID
                if book.accNo:
                    record.add_field(Field(tag='001', data=book.accNo))
                    
                # ISBN (020)
                if book.isbn:
                    record.add_field(Field(
                        tag='020', indicators=[' ', ' '],
                        subfields=['a', book.isbn]
                    ))
                    
                # Title (245)
                title = book.title or "Unknown Title"
                record.add_field(Field(
                    tag='245', indicators=['0', '0'],
                    subfields=['a', title]
                ))
                
                # Author (100)
                if book.author:
                    record.add_field(Field(
                        tag='100', indicators=['1', ' '],
                        subfields=['a', book.author]
                    ))
                    
                # Publication Info (260/264)
                pub_fields = []
                if book.publisherPlace:
                    pub_fields.extend(['a', book.publisherPlace])
                if book.publisher:
                    pub_fields.extend(['b', book.publisher])
                if book.publishDate:
                    pub_fields.extend(['c', str(book.publishDate)])
                
                if pub_fields:
                    record.add_field(Field(
                        tag='260', indicators=[' ', ' '],
                        subfields=pub_fields
                    ))
                    
                # Physical Description (300) - Pages
                if book.pages:
                    record.add_field(Field(
                        tag='300', indicators=[' ', ' '],
                        subfields=['a', f"{book.pages} p."]
                    ))
                    
                # Subject (650)
                if book.category:
                    record.add_field(Field(
                        tag='650', indicators=[' ', '0'],
                        subfields=['a', book.category]
                    ))

                f.write(record.as_marc())

    # ─── Koha Feature 2: Spine Label Generator ─────────────────────────────────
    def generate_spine_labels_pdf(self, books: list, output_path: str):
        """Generate PDF of Spine Labels for physical books (Call No, Author Initials, Acc No)."""
        if not HAS_REPORTLAB:
            raise ImportError("reportlab is required. Run: pip install reportlab")

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib import colors

        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                leftMargin=10*mm, rightMargin=10*mm,
                                topMargin=10*mm, bottomMargin=10*mm)

        label_style = ParagraphStyle("lbl", fontName="Helvetica-Bold",
                                     fontSize=11, alignment=TA_CENTER, leading=14)
        sub_style = ParagraphStyle("sub", fontName="Helvetica",
                                   fontSize=8, alignment=TA_CENTER)

        labels = []
        row = []

        for book in books:
            # Generate Call Number (e.g. "FIC" for Fiction, or DDC if we had it)
            cat_code = book.category[:3].upper() if book.category else "GEN"
            author_code = book.author[:3].upper() if book.author else "XXX"
            acc_no = book.accNo or "N/A"
            
            p = Paragraph(f"{cat_code}<br/>{author_code}<br/><br/>{acc_no}", label_style)
            p_sub = Paragraph(book.title[:20], sub_style)
            
            cell = Table([[p], [p_sub]], colWidths=[40*mm])
            cell.setStyle(TableStyle([
                ("BOX", (0,0), (-1,-1), 0.5, colors.grey),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("PADDING", (0,0), (-1,-1), 8),
            ]))
            
            row.append(cell)
            if len(row) == 4:  # 4 labels per row
                labels.append(row)
                row = []

        if row:
            while len(row) < 4:
                row.append("")
            labels.append(row)

        if not labels:
            raise ValueError("No books provided for spine labels.")

            sheet = Table(labels, colWidths=[45*mm]*4)
        sheet.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("PADDING", (0,0), (-1,-1), 5),
        ]))
        doc.build([sheet])

    # ─── Koha Feature 3: Smart Book Recommendation Engine ──────────────────────
    def get_recommendations_for_member(self, member_id: int) -> List[Book]:
        """
        Suggests 3-5 books based on a member's borrowing history (category & author).
        """
        issues = self.db.get_issues()
        member_issues = [i for i in issues if i.memberId == member_id]
        
        if not member_issues:
            # If no history, recommend recent generic available books
            books = self.db.get_books_paginated(limit=5)
            return [b for b in books if b.status == "Available"]
            
        # Get history ISBNs to not recommend read books
        read_isbns = {i.bookIsbn for i in member_issues if i.bookIsbn}
        
        # Determine favorite author and category
        authors = Counter()
        categories = Counter()
        
        all_books = self.db.get_books() # Ideally we just query DB but in-memory is fast
        for issue in member_issues:
            # match book to get category and author
            book = next((b for b in all_books if b.isbn == issue.bookIsbn), None)
            if book:
                if book.author: authors[book.author] += 1
                if book.category: categories[book.category] += 1
                
        fav_author = authors.most_common(1)[0][0] if authors else None
        fav_category = categories.most_common(1)[0][0] if categories else None
        
        recommendations = []
        for b in all_books:
            if b.status != "Available" or b.isbn in read_isbns:
                continue
            if b.author == fav_author or b.category == fav_category:
                recommendations.append(b)
                if len(recommendations) >= 5:
                    break
                    
        # Fallback if we didn't find enough
        if len(recommendations) < 5:
            for b in all_books:
                if b.status == "Available" and b.isbn not in read_isbns and b not in recommendations:
                    recommendations.append(b)
                    if len(recommendations) >= 5:
                        break
                        
        return recommendations

