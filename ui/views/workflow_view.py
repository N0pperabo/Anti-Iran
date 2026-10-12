"""Workflow Editor view for visual workflow modeling, reordering, and dispatch."""

import json
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from app.state_manager import ApplicationStateManager
from models.action_types import (
    ActionType,
    BaseAction,
    ClickAction,
    KeyPressAction,
    NavigateAction,
    TargetElementAction,
    TypeAction,
    WaitAction,
    WorkflowActionUnion,
)
from models.workflow import WorkflowDefinition
from ui.widgets.action_dialog import ActionDialog


class WorkflowView(QWidget):
    """Visual declarative workflow editor page."""

    run_workflow_requested = Signal(object)  # WorkflowDefinition

    def __init__(self, state_mgr: ApplicationStateManager, parent=None):
        super().__init__(parent)
        self.state_mgr = state_mgr

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 1. Workflow Metadata Bar
        meta_layout = QHBoxLayout()
        meta_layout.addWidget(QLabel("Workflow Name:"))
        self.name_input = QLineEdit(self.state_mgr.current_workflow.name)
        self.name_input.textChanged.connect(self._on_metadata_changed)
        meta_layout.addWidget(self.name_input)

        meta_layout.addWidget(QLabel("Target URL:"))
        self.target_url_input = QLineEdit(self.state_mgr.current_workflow.target_url)
        self.target_url_input.textChanged.connect(self._on_metadata_changed)
        meta_layout.addWidget(self.target_url_input)

        self.restore_state_check = QCheckBox("Restore Session State")
        self.restore_state_check.setChecked(self.state_mgr.current_workflow.restore_state)
        self.restore_state_check.stateChanged.connect(self._on_metadata_changed)
        meta_layout.addWidget(self.restore_state_check)

        self.save_state_check = QCheckBox("Persist Updated State")
        self.save_state_check.setChecked(self.state_mgr.current_workflow.save_state)
        self.save_state_check.stateChanged.connect(self._on_metadata_changed)
        meta_layout.addWidget(self.save_state_check)

        layout.addLayout(meta_layout)

        # 2. Action Operations Toolbar
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Action")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.clicked.connect(self._add_action)
        toolbar.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_action)
        toolbar.addWidget(self.edit_btn)

        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self._duplicate_action)
        toolbar.addWidget(self.duplicate_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.clicked.connect(self._delete_action)
        toolbar.addWidget(self.delete_btn)

        toolbar.addSpacing(15)

        self.move_up_btn = QPushButton("Move Up ↑")
        self.move_up_btn.clicked.connect(self._move_up)
        toolbar.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("Move Down ↓")
        self.move_down_btn.clicked.connect(self._move_down)
        toolbar.addWidget(self.move_down_btn)

        self.toggle_btn = QPushButton("Toggle Enable/Disable")
        self.toggle_btn.clicked.connect(self._toggle_enable)
        toolbar.addWidget(self.toggle_btn)

        toolbar.addStretch()

        self.save_local_btn = QPushButton("Save JSON")
        self.save_local_btn.clicked.connect(self._save_local_json)
        toolbar.addWidget(self.save_local_btn)

        self.load_local_btn = QPushButton("Load JSON")
        self.load_local_btn.clicked.connect(self._load_local_json)
        toolbar.addWidget(self.load_local_btn)

        self.save_repo_btn = QPushButton("Save to Repo")
        self.save_repo_btn.clicked.connect(self._save_to_github_repo)
        toolbar.addWidget(self.save_repo_btn)

        self.run_btn = QPushButton("RUN WORKFLOW 🚀")
        self.run_btn.setObjectName("primaryBtn")
        self.run_btn.setStyleSheet("font-weight: bold; padding: 8px 20px;")
        self.run_btn.clicked.connect(self._trigger_run)
        toolbar.addWidget(self.run_btn)

        layout.addLayout(toolbar)

        # 3. Actions Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "#", "Enabled", "Type", "Selector / Target", "Parameters", "Description", "Timeout (ms)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self._edit_action)
        layout.addWidget(self.table)

        self.refresh_table()

    def refresh_table(self):
        """Rebuilds table rows according to active workflow actions."""
        actions = self.state_mgr.current_workflow.actions
        self.table.setRowCount(len(actions))

        for row, act in enumerate(actions):
            # 0. Index
            idx_item = QTableWidgetItem(str(row + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, idx_item)

            # 1. Enabled
            en_item = QTableWidgetItem("✓" if act.enabled else "✗")
            en_item.setTextAlignment(Qt.AlignCenter)
            en_item.setForeground(Qt.green if act.enabled else Qt.red)
            self.table.setItem(row, 1, en_item)

            # 2. Type
            type_item = QTableWidgetItem(act.type.value.upper())
            type_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, type_item)

            # 3. Selector / Target
            target_str = "-"
            if hasattr(act, "selector") and act.selector:
                target_str = act.selector
            elif isinstance(act, NavigateAction):
                target_str = act.url
            self.table.setItem(row, 3, QTableWidgetItem(target_str))

            # 4. Parameters
            param_str = ""
            if isinstance(act, TypeAction):
                param_str = f"text=\"{act.text}\""
            elif isinstance(act, KeyPressAction):
                param_str = f"key={act.key}"
            elif isinstance(act, WaitAction):
                param_str = f"{act.milliseconds} ms"
            self.table.setItem(row, 4, QTableWidgetItem(param_str))

            # 5. Description
            self.table.setItem(row, 5, QTableWidgetItem(act.description or ""))

            # 6. Timeout
            timeout_item = QTableWidgetItem(str(act.timeout_ms))
            timeout_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 6, timeout_item)

    def _on_metadata_changed(self):
        wf = self.state_mgr.current_workflow
        wf.name = self.name_input.text().strip() or "Untitled Workflow"
        wf.target_url = self.target_url_input.text().strip() or "https://github.com"
        wf.restore_state = self.restore_state_check.isChecked()
        wf.save_state = self.save_state_check.isChecked()

    def _add_action(self):
        dlg = ActionDialog(parent=self)
        if dlg.exec():
            action = dlg.get_action()
            self.state_mgr.current_workflow.actions.append(action)
            self.refresh_table()

    def _edit_action(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.state_mgr.current_workflow.actions):
            QMessageBox.information(self, "Select Action", "Please select an action to edit.")
            return

        action = self.state_mgr.current_workflow.actions[row]
        dlg = ActionDialog(action=action, parent=self)
        if dlg.exec():
            updated = dlg.get_action()
            self.state_mgr.current_workflow.actions[row] = updated
            self.refresh_table()

    def _duplicate_action(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.state_mgr.current_workflow.actions):
            return

        action = self.state_mgr.current_workflow.actions[row]
        cloned_dict = action.model_dump()
        import uuid
        cloned_dict["id"] = f"act-{uuid.uuid4().hex[:6]}"
        from models.action_types import ClickAction
        # Validate through WorkflowDefinition
        from pydantic import TypeAdapter
        from models.action_types import WorkflowActionUnion
        adapter = TypeAdapter(WorkflowActionUnion)
        cloned = adapter.validate_python(cloned_dict)
        self.state_mgr.current_workflow.actions.insert(row + 1, cloned)
        self.refresh_table()
        self.table.selectRow(row + 1)

    def _delete_action(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.state_mgr.current_workflow.actions):
            return

        del self.state_mgr.current_workflow.actions[row]
        self.refresh_table()

    def _move_up(self):
        row = self.table.currentRow()
        if row <= 0:
            return
        actions = self.state_mgr.current_workflow.actions
        actions[row - 1], actions[row] = actions[row], actions[row - 1]
        self.refresh_table()
        self.table.selectRow(row - 1)

    def _move_down(self):
        row = self.table.currentRow()
        actions = self.state_mgr.current_workflow.actions
        if row < 0 or row >= len(actions) - 1:
            return
        actions[row], actions[row + 1] = actions[row + 1], actions[row]
        self.refresh_table()
        self.table.selectRow(row + 1)

    def _toggle_enable(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.state_mgr.current_workflow.actions):
            return
        act = self.state_mgr.current_workflow.actions[row]
        act.enabled = not act.enabled
        self.refresh_table()

    def _save_local_json(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Workflow JSON", "", "JSON Files (*.json)")
        if file_path:
            try:
                data = self.state_mgr.current_workflow.model_dump()
                Path(file_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
                QMessageBox.information(self, "Saved", f"Workflow saved successfully to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Failed", f"Failed to save file: {e}")

    def _load_local_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Workflow JSON", "", "JSON Files (*.json)")
        if file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8")
                data = json.loads(content)
                wf = WorkflowDefinition.model_validate(data)
                self.state_mgr.current_workflow = wf
                self.name_input.setText(wf.name)
                self.target_url_input.setText(wf.target_url)
                self.restore_state_check.setChecked(wf.restore_state)
                self.save_state_check.setChecked(wf.save_state)
                self.refresh_table()
                QMessageBox.information(self, "Loaded", f"Loaded workflow: {wf.name}")
            except Exception as e:
                QMessageBox.critical(self, "Load Failed", f"Invalid workflow file: {e}")

    def _save_to_github_repo(self):
        client = self.state_mgr.get_github_client()
        if not client:
            QMessageBox.warning(self, "Not Connected", "Please configure GitHub connection in Settings.")
            return

        remote_path = f"workflows/{self.state_mgr.current_workflow.id}.json"
        content = json.dumps(self.state_mgr.current_workflow.model_dump(), indent=2)

        try:
            # Check SHA if file already exists
            existing_sha = None
            try:
                _, existing_sha = client.get_file_content(remote_path)
            except Exception:
                pass

            client.create_or_update_file(
                file_path=remote_path,
                content=content,
                commit_message=f"feat: update workflow {self.state_mgr.current_workflow.name}",
                sha=existing_sha,
            )
            QMessageBox.information(self, "Saved to GitHub", f"Workflow committed to:\n{remote_path}")
        except Exception as e:
            QMessageBox.critical(self, "Commit Failed", f"Failed to save workflow to GitHub repository: {e}")

    def _trigger_run(self):
        self._on_metadata_changed()
        self.run_workflow_requested.emit(self.state_mgr.current_workflow)
