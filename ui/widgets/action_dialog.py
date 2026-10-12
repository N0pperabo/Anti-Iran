"""Dialog for creating and editing workflow actions."""

import uuid
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)
from models.action_types import (
    ActionType,
    BaseAction,
    ClickAction,
    DoubleClickAction,
    RightClickAction,
    TypeAction,
    ClearAction,
    KeyPressAction,
    WaitAction,
    SelectOptionAction,
    CheckAction,
    UncheckAction,
    ScreenshotAction,
    ExtractTextAction,
    ExtractAttributeAction,
    NavigateAction,
    GoBackAction,
    GoForwardAction,
    ReloadAction,
    WorkflowActionUnion,
)


class ActionDialog(QDialog):
    """Modal dialog to configure action parameters."""

    def __init__(self, action: Optional[BaseAction] = None, parent=None, default_selector: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Edit Action" if action else "Add Action")
        self.setMinimumWidth(500)
        self.existing_action = action

        layout = QVBoxLayout(self)
        self.form = QFormLayout()

        # Action Type selector
        self.type_combo = QComboBox()
        for act in ActionType:
            self.type_combo.addItem(act.value.upper(), act)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.form.addRow("Action Type:", self.type_combo)

        # Description
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Optional human-readable description")
        self.form.addRow("Description:", self.desc_input)

        # Primary Selector
        self.selector_input = QLineEdit()
        self.selector_input.setPlaceholderText("e.g. #submit-btn or input[name='q']")
        if default_selector:
            self.selector_input.setText(default_selector)
        self.form.addRow("Selector:", self.selector_input)

        # Fallback Selectors (comma or newline separated)
        self.fallbacks_input = QLineEdit()
        self.fallbacks_input.setPlaceholderText("Fallback selectors (comma separated)")
        self.form.addRow("Fallbacks:", self.fallbacks_input)

        # Text input (for TYPE)
        self.text_input = QLineEdit()
        self.form.addRow("Text to Type:", self.text_input)

        # Clear first (for TYPE)
        self.clear_first_check = QCheckBox("Clear element before typing")
        self.form.addRow("", self.clear_first_check)

        # Key (for KEY_PRESS)
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("e.g. Enter, Tab, Escape, Control+A")
        self.form.addRow("Key:", self.key_input)

        # Milliseconds (for WAIT)
        self.wait_spin = QSpinBox()
        self.wait_spin.setRange(0, 60000)
        self.wait_spin.setValue(1000)
        self.wait_spin.setSingleStep(500)
        self.form.addRow("Wait (ms):", self.wait_spin)

        # URL (for NAVIGATE)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.form.addRow("Target URL:", self.url_input)

        # Timeout & Retries
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(500, 60000)
        self.timeout_spin.setValue(10000)
        self.timeout_spin.setSingleStep(1000)
        self.form.addRow("Timeout (ms):", self.timeout_spin)

        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(1, 5)
        self.retries_spin.setValue(1)
        self.form.addRow("Retries:", self.retries_spin)

        layout.addLayout(self.form)

        # Dialog Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        # Pre-fill if editing
        if self.existing_action:
            self._populate_fields(self.existing_action)
        else:
            self._update_field_visibilities(ActionType.CLICK)

    def _on_type_changed(self, idx: int):
        act_type: ActionType = self.type_combo.currentData()
        self._update_field_visibilities(act_type)

    def _update_field_visibilities(self, act_type: ActionType):
        is_type = act_type == ActionType.TYPE
        is_key = act_type in (ActionType.KEY_PRESS, ActionType.KEY_DOWN, ActionType.KEY_UP)
        is_wait = act_type == ActionType.WAIT
        is_nav = act_type == ActionType.NAVIGATE
        has_selector = act_type not in (
            ActionType.NAVIGATE, ActionType.GO_BACK, ActionType.GO_FORWARD,
            ActionType.RELOAD, ActionType.MOUSE_MOVE
        )

        self.selector_input.setEnabled(has_selector)
        self.fallbacks_input.setEnabled(has_selector)
        self.text_input.setVisible(is_type)
        self.clear_first_check.setVisible(is_type)
        self.key_input.setVisible(is_key)
        self.wait_spin.setVisible(is_wait)
        self.url_input.setVisible(is_nav)

    def _populate_fields(self, action: BaseAction):
        idx = self.type_combo.findData(action.type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.desc_input.setText(action.description or "")
        self.timeout_spin.setValue(action.timeout_ms)
        self.retries_spin.setValue(action.retry_count)

        if hasattr(action, "selector") and action.selector:
            self.selector_input.setText(action.selector)
        if action.fallback_selectors:
            self.fallbacks_input.setText(", ".join(action.fallback_selectors))

        if isinstance(action, TypeAction):
            self.text_input.setText(action.text)
            self.clear_first_check.setChecked(action.clear_first)
        elif isinstance(action, KeyPressAction):
            self.key_input.setText(action.key)
        elif isinstance(action, WaitAction):
            self.wait_spin.setValue(action.milliseconds)
        elif isinstance(action, NavigateAction):
            self.url_input.setText(action.url)

    def get_action(self) -> WorkflowActionUnion:
        """Constructs and returns the configured action object."""
        act_type: ActionType = self.type_combo.currentData()
        action_id = self.existing_action.id if self.existing_action else f"act-{uuid.uuid4().hex[:6]}"
        desc = self.desc_input.text().strip() or None
        timeout = self.timeout_spin.value()
        retries = self.retries_spin.value()
        selector = self.selector_input.text().strip()
        fallbacks = [s.strip() for s in self.fallbacks_input.text().split(",") if s.strip()]

        common = {
            "id": action_id,
            "description": desc,
            "timeout_ms": timeout,
            "retry_count": retries,
            "fallback_selectors": fallbacks,
        }

        if act_type == ActionType.CLICK:
            return ClickAction(selector=selector, **common)
        elif act_type == ActionType.DOUBLE_CLICK:
            return DoubleClickAction(selector=selector, **common)
        elif act_type == ActionType.RIGHT_CLICK:
            return RightClickAction(selector=selector, **common)
        elif act_type == ActionType.TYPE:
            return TypeAction(
                selector=selector,
                text=self.text_input.text(),
                clear_first=self.clear_first_check.isChecked(),
                **common,
            )
        elif act_type == ActionType.CLEAR:
            return ClearAction(selector=selector, **common)
        elif act_type == ActionType.KEY_PRESS:
            return KeyPressAction(
                key=self.key_input.text() or "Enter",
                selector=selector or None,
                **common,
            )
        elif act_type == ActionType.WAIT:
            return WaitAction(
                milliseconds=self.wait_spin.value(),
                selector=selector or None,
                **common,
            )
        elif act_type == ActionType.NAVIGATE:
            return NavigateAction(
                url=self.url_input.text() or "https://github.com",
                **common,
            )
        elif act_type == ActionType.SCREENSHOT:
            return ScreenshotAction(selector=selector or None, **common)
        elif act_type == ActionType.CHECK:
            return CheckAction(selector=selector, **common)
        elif act_type == ActionType.UNCHECK:
            return UncheckAction(selector=selector, **common)
        elif act_type == ActionType.GO_BACK:
            return GoBackAction(**common)
        elif act_type == ActionType.GO_FORWARD:
            return GoForwardAction(**common)
        elif act_type == ActionType.RELOAD:
            return ReloadAction(**common)
        else:
            return ClickAction(selector=selector, **common)
