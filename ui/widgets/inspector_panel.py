"""DOM Inspector panel displaying element attributes, computed selectors, and action builders."""

from typing import Callable, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from models.inspect_bundle import DOMElementInfo
from models.action_types import ActionType


class InspectorPanel(QWidget):
    """Right-side DOM element inspector and action shortcut panel."""

    create_action_requested = Signal(str, str)  # (action_type, selector)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_element: Optional[DOMElementInfo] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # 1. Element Summary
        summary_group = QGroupBox("Element Metadata")
        form = QFormLayout(summary_group)
        self.tag_label = QLabel("-")
        self.id_label = QLabel("-")
        self.classes_label = QLabel("-")
        self.role_label = QLabel("-")
        self.text_label = QLabel("-")
        self.text_label.setWordWrap(True)

        form.addRow("Tag:", self.tag_label)
        form.addRow("ID:", self.id_label)
        form.addRow("Classes:", self.classes_label)
        form.addRow("Role / Name:", self.role_label)
        form.addRow("Text Content:", self.text_label)
        layout.addWidget(summary_group)

        # 2. Stable Selector Ranking List
        selectors_group = QGroupBox("Computed Selectors (Ranked by Stability)")
        sel_layout = QVBoxLayout(selectors_group)
        self.selectors_list = QListWidget()
        self.selectors_list.setSelectionMode(QListWidget.SingleSelection)
        sel_layout.addWidget(self.selectors_list)

        sel_btn_row = QHBoxLayout()
        self.copy_sel_btn = QPushButton("Copy Selector")
        self.copy_sel_btn.clicked.connect(self._copy_selected_selector)
        sel_btn_row.addWidget(self.copy_sel_btn)
        sel_layout.addLayout(sel_btn_row)
        layout.addWidget(selectors_group)

        # 3. Attributes Table
        attrs_group = QGroupBox("Attributes")
        attr_layout = QVBoxLayout(attrs_group)
        self.attrs_table = QTableWidget()
        self.attrs_table.setColumnCount(2)
        self.attrs_table.setHorizontalHeaderLabels(["Attribute", "Value"])
        self.attrs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        attr_layout.addWidget(self.attrs_table)
        layout.addWidget(attrs_group)

        # 4. Action Builder Shortcuts
        actions_group = QGroupBox("Quick Actions for Selected Element")
        act_layout = QVBoxLayout(actions_group)
        btn_row1 = QHBoxLayout()
        self.add_click_btn = QPushButton("+ CLICK")
        self.add_click_btn.setObjectName("primaryBtn")
        self.add_click_btn.clicked.connect(lambda: self._emit_action(ActionType.CLICK))
        self.add_type_btn = QPushButton("+ TYPE")
        self.add_type_btn.clicked.connect(lambda: self._emit_action(ActionType.TYPE))
        btn_row1.addWidget(self.add_click_btn)
        btn_row1.addWidget(self.add_type_btn)

        btn_row2 = QHBoxLayout()
        self.add_wait_btn = QPushButton("+ WAIT")
        self.add_wait_btn.clicked.connect(lambda: self._emit_action(ActionType.WAIT))
        self.add_extract_btn = QPushButton("+ EXTRACT")
        self.add_extract_btn.clicked.connect(lambda: self._emit_action(ActionType.EXTRACT_TEXT))
        btn_row2.addWidget(self.add_wait_btn)
        btn_row2.addWidget(self.add_extract_btn)

        act_layout.addLayout(btn_row1)
        act_layout.addLayout(btn_row2)
        layout.addWidget(actions_group)

    def set_element(self, element: Optional[DOMElementInfo]):
        """Populates panel with inspected element information."""
        self.current_element = element
        if not element:
            self.tag_label.setText("-")
            self.id_label.setText("-")
            self.classes_label.setText("-")
            self.role_label.setText("-")
            self.text_label.setText("-")
            self.selectors_list.clear()
            self.attrs_table.setRowCount(0)
            return

        self.tag_label.setText(f"<{element.tag}>")
        self.id_label.setText(element.id or "(none)")
        self.classes_label.setText(", ".join(element.classes) if element.classes else "(none)")
        role_text = f"role={element.role}" if element.role else ""
        if element.name:
            role_text += f" name={element.name}"
        self.role_label.setText(role_text or "(none)")
        self.text_label.setText(element.text_content or "(none)")

        # Populate selectors
        self.selectors_list.clear()
        for idx, sel in enumerate(element.suggested_selectors):
            item = QListWidgetItem(f"[{idx + 1}] {sel}")
            item.setData(Qt.UserRole, sel)
            self.selectors_list.addItem(item)
        if self.selectors_list.count() > 0:
            self.selectors_list.setCurrentRow(0)

        # Populate attributes table
        self.attrs_table.setRowCount(len(element.attributes))
        for row, (k, v) in enumerate(element.attributes.items()):
            self.attrs_table.setItem(row, 0, QTableWidgetItem(k))
            self.attrs_table.setItem(row, 1, QTableWidgetItem(v))

    def get_selected_selector(self) -> str:
        current_item = self.selectors_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        if self.current_element and self.current_element.suggested_selectors:
            return self.current_element.suggested_selectors[0]
        return ""

    def _copy_selected_selector(self):
        sel = self.get_selected_selector()
        if sel:
            QApplication.clipboard().setText(sel)
            self.copy_sel_btn.setText("Copied!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.copy_sel_btn.setText("Copy Selector"))

    def _emit_action(self, action_type: ActionType):
        sel = self.get_selected_selector()
        self.create_action_requested.emit(action_type.value, sel)
