"""Spacious and non-overlapping modal for creating actions directly from clicked DOM elements."""

import uuid
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)
from models.action_types import (
    ActionType,
    ClickAction,
    TypeAction,
    WaitAction,
    ExtractTextAction,
    ScreenshotAction,
    WorkflowActionUnion,
)


class QuickActionModal(QDialog):
    """Modal dialog triggered upon clicking an element in Inspect Mode."""

    def __init__(self, element_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Action for Element")
        self.setMinimumWidth(540)
        self.element_data = element_data

        # Root layout with generous spacing
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(16)

        # 1. Element Header Chip
        tag = element_data.get("tag", "element")
        elem_id = element_data.get("id")
        name = element_data.get("name")
        text = element_data.get("text", "")

        chip_box = QFrame()
        chip_box.setStyleSheet(
            "background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 10px;"
        )
        chip_layout = QVBoxLayout(chip_box)
        chip_layout.setContentsMargins(10, 8, 10, 8)
        chip_layout.setSpacing(4)

        title_lbl = QLabel(f"Target Element: <{tag}>")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #58a6ff;")
        chip_layout.addWidget(title_lbl)

        details_parts = []
        if elem_id:
            details_parts.append(f"id=\"{elem_id}\"")
        if name:
            details_parts.append(f"name=\"{name}\"")
        if text:
            details_parts.append(f"text=\"{text[:40]}\"")

        details_lbl = QLabel(" • ".join(details_parts) if details_parts else "Interactive DOM element")
        details_lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
        chip_layout.addWidget(details_lbl)
        layout.addWidget(chip_box)

        # 2. Selector Selection Form
        sel_form = QFormLayout()
        sel_form.setVerticalSpacing(10)
        sel_form.setHorizontalSpacing(15)

        self.selector_combo = QComboBox()
        self.selector_combo.setEditable(True)
        selectors = element_data.get("selectors", [])
        if not selectors and element_data.get("primary_selector"):
            selectors = [element_data["primary_selector"]]

        for s in selectors:
            self.selector_combo.addItem(s)
        if selectors:
            self.selector_combo.setCurrentIndex(0)

        sel_form.addRow("Target Selector:", self.selector_combo)
        layout.addLayout(sel_form)

        # 3. Action Type Selector Buttons (Radio-like button group)
        act_box = QFrame()
        act_box.setStyleSheet("background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 8px;")
        act_layout = QVBoxLayout(act_box)
        act_layout.setContentsMargins(8, 8, 8, 8)
        act_layout.setSpacing(8)

        act_label = QLabel("Select Action Type:")
        act_label.setStyleSheet("font-weight: bold; color: #c9d1d9;")
        act_layout.addWidget(act_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_click = QPushButton("👆 CLICK")
        self.btn_type = QPushButton("⌨️ TYPE")
        self.btn_wait = QPushButton("⏳ WAIT")
        self.btn_extract = QPushButton("📋 EXTRACT")
        self.btn_shot = QPushButton("📸 SCREENSHOT")

        for b in [self.btn_click, self.btn_type, self.btn_wait, self.btn_extract, self.btn_shot]:
            b.setCheckable(True)
            btn_row.addWidget(b)
        act_layout.addLayout(btn_row)
        layout.addWidget(act_box)

        # Button group for mutual exclusion
        self.action_group = QButtonGroup(self)
        self.action_group.addButton(self.btn_click, 1)
        self.action_group.addButton(self.btn_type, 2)
        self.action_group.addButton(self.btn_wait, 3)
        self.action_group.addButton(self.btn_extract, 4)
        self.action_group.addButton(self.btn_shot, 5)
        self.action_group.idClicked.connect(self._on_action_type_selected)

        # 4. Action Parameters Form
        self.params_form = QFormLayout()
        self.params_form.setVerticalSpacing(12)
        self.params_form.setHorizontalSpacing(15)

        # Text input (for TYPE)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text to type into element...")
        self.params_form.addRow("Text to Type:", self.text_input)

        self.clear_first_check = QCheckBox("Clear element before typing")
        self.clear_first_check.setChecked(False)
        self.params_form.addRow("", self.clear_first_check)

        # Milliseconds (for WAIT)
        self.wait_spin = QSpinBox()
        self.wait_spin.setRange(100, 60000)
        self.wait_spin.setValue(1000)
        self.wait_spin.setSingleStep(500)
        self.params_form.addRow("Wait Time (ms):", self.wait_spin)

        # Variable name (for EXTRACT)
        self.var_input = QLineEdit()
        self.var_input.setText(f"extracted_{elem_id or tag}")
        self.params_form.addRow("Variable Name:", self.var_input)

        # Description
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Optional description")
        self.params_form.addRow("Description:", self.desc_input)

        layout.addLayout(self.params_form)

        # 5. Dialog Actions Buttons
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        bottom_row.addWidget(self.cancel_btn)

        self.add_btn = QPushButton("+ Add Action to Workflow")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.setStyleSheet("font-weight: bold; padding: 10px 24px;")
        self.add_btn.clicked.connect(self.accept)
        bottom_row.addWidget(self.add_btn)

        layout.addLayout(bottom_row)

        # Default action type based on element tag
        if tag in ("input", "textarea") and element_data.get("attributes", {}).get("type") not in ("submit", "button", "checkbox", "radio"):
            self.btn_type.setChecked(True)
            self._on_action_type_selected(2)
        else:
            self.btn_click.setChecked(True)
            self._on_action_type_selected(1)

    def _on_action_type_selected(self, btn_id: int):
        # Update styling on buttons
        for b in [self.btn_click, self.btn_type, self.btn_wait, self.btn_extract, self.btn_shot]:
            if b.isChecked():
                b.setStyleSheet("background-color: #1f6feb; color: #ffffff; border-color: #58a6ff;")
            else:
                b.setStyleSheet("")

        # 1: Click, 2: Type, 3: Wait, 4: Extract, 5: Shot
        is_type = (btn_id == 2)
        is_wait = (btn_id == 3)
        is_extract = (btn_id == 4)

        self.text_input.setVisible(is_type)
        self.clear_first_check.setVisible(is_type)
        self.wait_spin.setVisible(is_wait)
        self.var_input.setVisible(is_extract)

    def get_action(self) -> WorkflowActionUnion:
        """Constructs and returns the configured action object."""
        sel = self.selector_combo.currentText().strip()
        desc = self.desc_input.text().strip() or None
        act_id = f"act-{uuid.uuid4().hex[:6]}"

        btn_id = self.action_group.checkedId()
        if btn_id == 2:  # TYPE
            return TypeAction(
                id=act_id,
                selector=sel,
                text=self.text_input.text(),
                clear_first=self.clear_first_check.isChecked(),
                description=desc or f"Type into {sel}",
            )
        elif btn_id == 3:  # WAIT
            return WaitAction(
                id=act_id,
                selector=sel,
                milliseconds=self.wait_spin.value(),
                description=desc or f"Wait for {sel}",
            )
        elif btn_id == 4:  # EXTRACT
            return ExtractTextAction(
                id=act_id,
                selector=sel,
                variable_name=self.var_input.text().strip() or "extracted_text",
                description=desc or f"Extract text from {sel}",
            )
        elif btn_id == 5:  # SCREENSHOT
            return ScreenshotAction(
                id=act_id,
                selector=sel,
                description=desc or f"Capture screenshot of {sel}",
            )
        else:  # CLICK
            return ClickAction(
                id=act_id,
                selector=sel,
                description=desc or f"Click on {sel}",
            )
