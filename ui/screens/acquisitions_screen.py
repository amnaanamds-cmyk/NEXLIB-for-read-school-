"""
ui/screens/acquisitions_screen.py — Acquisition & Budgeting Module.
Create purchase orders, track vendor spending, and manage acquisition workflow.
"""
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QMessageBox, QFrame, QDialog, QFormLayout,
    QSpinBox, QDoubleSpinBox, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


PO_STATUSES = ["Pending", "Approved", "Ordered", "Shipped", "Received", "Cancelled"]


class AcquisitionsScreen(QWidget):
    def __init__(self, db_helper=None):
        super().__init__()
        self.db = db_helper
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("💰  Acquisitions & Budgeting")
        title.setStyleSheet("font-size:22px;font-weight:800;color:#E8EEF8;font-family:'Segoe UI';")
        hdr.addWidget(title)
        hdr.addStretch()

        new_btn = QPushButton("➕ New Purchase Order")
        new_btn.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1E5FD4,stop:1 #2872F0);"
            "color:white;border:none;border-radius:8px;padding:9px 18px;"
            "font-size:13px;font-weight:700;"
        )
        new_btn.clicked.connect(self._new_order)
        hdr.addWidget(new_btn)
        layout.addLayout(hdr)

        # Budget Overview Cards
        self.budget_frame = QFrame()
        self.budget_frame.setStyleSheet(
            "background:#0D1F38;border-radius:12px;border:1px solid #1E3050;"
        )
        budget_layout = QHBoxLayout(self.budget_frame)
        budget_layout.setContentsMargins(20, 16, 20, 16)

        self.lbl_total = self._make_stat_card("Total Orders", "0", "#3B82F6")
        self.lbl_spent = self._make_stat_card("Total Spent", "Rs. 0", "#F59E0B")
        self.lbl_pending = self._make_stat_card("Pending", "0", "#EF4444")
        self.lbl_received = self._make_stat_card("Received", "0", "#10B981")

        for card in (self.lbl_total, self.lbl_spent, self.lbl_pending, self.lbl_received):
            budget_layout.addWidget(card)

        layout.addWidget(self.budget_frame)

        # Filter row
        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search vendors, order details…")
        self.search_input.setStyleSheet(
            "background:#0D1F38;border:1.5px solid #1E3050;border-radius:8px;"
            "padding:9px 14px;color:#E8EEF8;font-size:13px;"
        )
        self.search_input.textChanged.connect(self.refresh)

        self.status_combo = QComboBox()
        self.status_combo.addItem("All Statuses")
        self.status_combo.addItems(PO_STATUSES)
        self.status_combo.setStyleSheet(self.search_input.styleSheet())
        self.status_combo.currentTextChanged.connect(self.refresh)

        filter_row.addWidget(self.search_input, stretch=3)
        filter_row.addWidget(self.status_combo, stretch=1)
        layout.addLayout(filter_row)

        # Orders Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Vendor", "Order Date", "Total Amount (Rs.)", "Status", "ID"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setColumnHidden(4, True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #071428; color: #E8EEF8;
                gridline-color: #1E3050; border: none;
                font-size: 13px; font-family: 'Segoe UI';
            }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected { background: rgba(30,95,212,0.3); }
            QHeaderView::section {
                background: #0D1B2A; color: #6B8CAE;
                font-weight: 700; font-size: 11px; padding: 8px;
                border-bottom: 1px solid #1E3050;
            }
            QTableWidget::item:alternate { background: rgba(13,28,55,0.6); }
        """)
        layout.addWidget(self.table)

        # Action bar
        act = QHBoxLayout()
        act.addStretch()

        self.approve_btn = QPushButton("✅ Approve / Update")
        self.approve_btn.setStyleSheet(
            "background:#10B981;color:white;border:none;border-radius:8px;"
            "padding:8px 16px;font-weight:bold;"
        )
        self.approve_btn.clicked.connect(self._update_status)
        act.addWidget(self.approve_btn)

        self.cancel_btn = QPushButton("❌ Cancel Order")
        self.cancel_btn.setStyleSheet(
            "background:rgba(239,68,68,0.15);color:#EF4444;border:1px solid rgba(239,68,68,0.3);"
            "border-radius:8px;padding:8px 16px;font-weight:bold;"
        )
        self.cancel_btn.clicked.connect(self._cancel_order)
        act.addWidget(self.cancel_btn)
        layout.addLayout(act)

        self.refresh()

    def _make_stat_card(self, label, value, color):
        card = QFrame()
        card.setStyleSheet("background:transparent;")
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setStyleSheet("color:#6B8CAE;font-size:11px;")
        val = QLabel(value)
        val.setObjectName(f"stat_{label.replace(' ', '_')}")
        val.setStyleSheet(f"color:{color};font-size:22px;font-weight:bold;")
        vbox.addWidget(lbl)
        vbox.addWidget(val)
        return card

    def refresh(self):
        if not self.db:
            return
        orders = self.db.get_purchase_orders()

        # Update summary cards
        total_spent = sum(o.get("totalAmount", 0) or 0 for o in orders)
        pending_count = sum(1 for o in orders if o.get("status") == "Pending")
        received_count = sum(1 for o in orders if o.get("status") == "Received")

        self.lbl_total.findChild(QLabel, "stat_Total_Orders").setText(str(len(orders)))
        self.lbl_spent.findChild(QLabel, "stat_Total_Spent").setText(f"Rs. {total_spent:,.0f}")
        self.lbl_pending.findChild(QLabel, "stat_Pending").setText(str(pending_count))
        self.lbl_received.findChild(QLabel, "stat_Received").setText(str(received_count))

        # Filter
        q = self.search_input.text().lower()
        s = self.status_combo.currentText()
        if q:
            orders = [o for o in orders if q in str(o.get("vendorName", "")).lower()]
        if s != "All Statuses":
            orders = [o for o in orders if o.get("status") == s]

        self.table.setRowCount(len(orders))
        for row, o in enumerate(orders):
            self.table.setItem(row, 0, QTableWidgetItem(o.get("vendorName", "")))

            ts = o.get("orderDate", 0)
            try:
                dt_str = datetime.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            except Exception:
                dt_str = "—"
            self.table.setItem(row, 1, QTableWidgetItem(dt_str))

            amt = o.get("totalAmount", 0) or 0
            amt_item = QTableWidgetItem(f"{amt:,.2f}")
            amt_item.setForeground(QColor("#C8A84B"))
            self.table.setItem(row, 2, amt_item)

            status = o.get("status", "Pending")
            st_item = QTableWidgetItem(status)
            color_map = {
                "Pending": "#F59E0B", "Approved": "#3B82F6",
                "Ordered": "#8B5CF6", "Shipped": "#06B6D4",
                "Received": "#10B981", "Cancelled": "#EF4444",
            }
            st_item.setForeground(QColor(color_map.get(status, "#A0B4CC")))
            self.table.setItem(row, 3, st_item)

            self.table.setItem(row, 4, QTableWidgetItem(str(o.get("id", ""))))

    def _new_order(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("New Purchase Order")
        dlg.setFixedSize(440, 340)
        dlg.setStyleSheet("background:#0D1B2A; color:#E8EEF8; font-family:'Segoe UI';")

        lay = QVBoxLayout(dlg)
        form = QFormLayout()

        def _f(ph=""):
            w = QLineEdit()
            w.setPlaceholderText(ph)
            w.setStyleSheet("background:#0D1F38; border:1.5px solid #1E3050; border-radius:6px; padding:6px; color:#E8EEF8;")
            return w

        vendor = _f("e.g. Oxford University Press")
        book_title = _f("e.g. Advanced Physics")
        qty = QSpinBox()
        qty.setRange(1, 9999)
        qty.setValue(1)
        qty.setStyleSheet("background:#0D1F38; border:1.5px solid #1E3050; border-radius:6px; padding:6px; color:#E8EEF8;")
        unit_price = QDoubleSpinBox()
        unit_price.setRange(1, 999999)
        unit_price.setValue(500)
        unit_price.setPrefix("Rs. ")
        unit_price.setStyleSheet(qty.styleSheet())

        form.addRow("Vendor *", vendor)
        form.addRow("Book / Item", book_title)
        form.addRow("Quantity", qty)
        form.addRow("Unit Price", unit_price)
        lay.addLayout(form)

        btn = QPushButton("📋 Create Purchase Order")
        btn.setStyleSheet("background:#2872F0;color:white;border:none;border-radius:8px;padding:10px;font-weight:bold;")

        def _save():
            if not vendor.text().strip():
                QMessageBox.warning(dlg, "Required", "Vendor name is required.")
                return
            self.db.save_purchase_order(
                vendor.text().strip(),
                book_title.text().strip(),
                qty.value(),
                unit_price.value()
            )
            self.db.log_audit_local("system", "purchase_order",
                                    f"PO created: {vendor.text().strip()} — Rs.{qty.value() * unit_price.value():,.0f}")
            QMessageBox.information(dlg, "Created", "Purchase order created successfully.")
            dlg.accept()
            self.refresh()

        btn.clicked.connect(_save)
        lay.addWidget(btn)
        dlg.exec()

    def _update_status(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select", "Please select an order to update.")
            return
        po_id = int(self.table.item(row, 4).text())
        current = self.table.item(row, 3).text()

        new_status, ok = QInputDialog.getItem(
            self, "Update PO Status", f"Current: {current}\nSelect new status:",
            PO_STATUSES,
            PO_STATUSES.index(current) if current in PO_STATUSES else 0,
            False
        )
        if ok and new_status != current:
            self.db.update_purchase_order_status(po_id, new_status)
            self.db.log_audit_local("system", "po_status_update",
                                    f"PO #{po_id} status → {new_status}")
            self.refresh()

    def _cancel_order(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select", "Please select an order to cancel.")
            return
        po_id = int(self.table.item(row, 4).text())
        vendor = self.table.item(row, 0).text()
        reply = QMessageBox.question(
            self, "Cancel PO", f"Cancel order from '{vendor}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.update_purchase_order_status(po_id, "Cancelled")
            self.db.log_audit_local("system", "po_cancelled", f"PO #{po_id} cancelled")
            self.refresh()
