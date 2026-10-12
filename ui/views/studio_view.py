"""Full-Screen Interactive Browser Studio Workspace with live Chromium engine and collapsible drawer."""

import json
import time
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QByteArray, QEvent, QObject, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
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
    TypeAction,
    WaitAction,
    WorkflowActionUnion,
)
from models.workflow import WorkflowDefinition
from ui.widgets.action_dialog import ActionDialog
from ui.widgets.quick_action_modal import QuickActionModal
from ui.widgets.settings_dialog import SettingsDialog
from ui.widgets.web_inspector_script import INSPECTOR_JS_CODE
from github.models import RunConclusion, RunStatus, WorkflowRunInfo
from github.poller import WorkflowPoller


class StudioWebPage(QWebEnginePage):
    """Custom QWebEnginePage intercepting console messages from inspector script."""

    element_inspected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        if message.startswith("STUDIO_INSPECT:"):
            try:
                json_str = message[len("STUDIO_INSPECT:"):]
                data = json.loads(json_str)
                self.element_inspected.emit(data)
            except Exception as e:
                print(f"Failed to parse inspect payload: {e}")
        else:
            # Pass through standard console messages
            super().javaScriptConsoleMessage(level, message, line_number, source_id)


class StudioView(QWidget):
    """Unified full-screen interactive studio workspace."""

    run_status_updated = Signal(str)

    def __init__(self, state_mgr: ApplicationStateManager, parent=None):
        super().__init__(parent)
        self.state_mgr = state_mgr
        self.inspect_mode_active = False

        # Main vertical layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Sleek Toolbar
        self.toolbar = QFrame()
        self.toolbar.setStyleSheet("background-color: #161b22; border-bottom: 1px solid #30363d; padding: 4px 10px;")
        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(6, 4, 6, 4)
        tb_layout.setSpacing(8)

        # Brand pill
        logo_lbl = QLabel("⚡ Studio")
        logo_lbl.setStyleSheet("font-weight: bold; color: #58a6ff; font-size: 14px; padding-right: 6px;")
        tb_layout.addWidget(logo_lbl)

        # Navigation buttons
        self.back_btn = QPushButton("◀")
        self.back_btn.setToolTip("Back")
        self.back_btn.setFixedWidth(36)
        self.back_btn.clicked.connect(self._nav_back)
        tb_layout.addWidget(self.back_btn)

        self.fwd_btn = QPushButton("▶")
        self.fwd_btn.setToolTip("Forward")
        self.fwd_btn.setFixedWidth(36)
        self.fwd_btn.clicked.connect(self._nav_forward)
        tb_layout.addWidget(self.fwd_btn)

        self.reload_btn = QPushButton("🔄")
        self.reload_btn.setToolTip("Reload")
        self.reload_btn.setFixedWidth(36)
        self.reload_btn.clicked.connect(self._nav_reload)
        tb_layout.addWidget(self.reload_btn)

        # URL Input Bar
        self.url_input = QLineEdit()
        self.url_input.setText(self.state_mgr.config.last_url)
        self.url_input.setPlaceholderText("https://github.com or any website URL...")
        self.url_input.returnPressed.connect(self._load_url_from_input)
        tb_layout.addWidget(self.url_input, stretch=1)

        self.go_btn = QPushButton("Go")
        self.go_btn.setFixedWidth(50)
        self.go_btn.clicked.connect(self._load_url_from_input)
        tb_layout.addWidget(self.go_btn)

        tb_layout.addSpacing(10)

        # Inspect Mode Toggle Button
        self.inspect_btn = QPushButton("🎯 Inspect Mode")
        self.inspect_btn.setCheckable(True)
        self.inspect_btn.setToolTip("Toggle Inspect Mode: Hover over and click any element on the page to build an action")
        self.inspect_btn.clicked.connect(self._toggle_inspect_mode)
        tb_layout.addWidget(self.inspect_btn)

        # Workflow Drawer Toggle Button
        self.drawer_btn = QPushButton("📋 Actions (0)")
        self.drawer_btn.setCheckable(True)
        self.drawer_btn.setChecked(False)
        self.drawer_btn.setToolTip("Show / Hide Workflow Actions Drawer")
        self.drawer_btn.clicked.connect(self._toggle_drawer)
        tb_layout.addWidget(self.drawer_btn)

        # Run on GitHub Actions Primary Button
        self.run_btn = QPushButton("🚀 RUN ON GITHUB ACTIONS")
        self.run_btn.setObjectName("primaryBtn")
        self.run_btn.setStyleSheet("font-weight: bold; padding: 8px 18px;")
        self.run_btn.clicked.connect(self._execute_workflow_on_github)
        tb_layout.addWidget(self.run_btn)

        tb_layout.addSpacing(6)

        # Settings Button
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.clicked.connect(self._open_settings_dialog)
        tb_layout.addWidget(self.settings_btn)

        # Fullscreen Toggle Button
        self.fullscreen_btn = QPushButton("⛶ Fullscreen")
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        tb_layout.addWidget(self.fullscreen_btn)

        root_layout.addWidget(self.toolbar)

        # 2. Inspect Mode Floating Notification Bar
        self.inspect_banner = QFrame()
        self.inspect_banner.setStyleSheet("background-color: #1f6feb; color: #ffffff; padding: 6px 16px; border-bottom: 1px solid #388bfd;")
        b_layout = QHBoxLayout(self.inspect_banner)
        b_layout.setContentsMargins(12, 4, 12, 4)
        banner_msg = QLabel("🎯 INSPECT MODE ACTIVE: Hover over any button, input, or box on the webpage and click it to create an automation action.")
        banner_msg.setStyleSheet("font-weight: bold; color: #ffffff;")
        b_layout.addWidget(banner_msg)
        b_layout.addStretch()

        self.exit_inspect_btn = QPushButton("Done Inspecting ✕")
        self.exit_inspect_btn.setStyleSheet("background-color: #0d1117; color: #ffffff; border: 1px solid #ffffff; font-size: 11px; padding: 4px 10px;")
        self.exit_inspect_btn.clicked.connect(lambda: self.inspect_btn.setChecked(False) or self._toggle_inspect_mode())
        b_layout.addWidget(self.exit_inspect_btn)
        self.inspect_banner.setVisible(False)
        root_layout.addWidget(self.inspect_banner)

        # 3. Main Center Splitter: Browser View (Full width) + Collapsible Drawer Panel
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(4)

        # Central Chromium Browser
        self.browser_container = QWidget()
        bc_layout = QVBoxLayout(self.browser_container)
        bc_layout.setContentsMargins(0, 0, 0, 0)
        bc_layout.setSpacing(0)

        self.web_view = QWebEngineView()
        self.web_page = StudioWebPage(self.web_view)
        self.web_page.element_inspected.connect(self._on_element_inspected)
        self.web_view.setPage(self.web_page)
        self.web_view.loadFinished.connect(self._on_page_load_finished)
        self.web_view.urlChanged.connect(self._on_url_changed)

        bc_layout.addWidget(self.web_view)
        self.splitter.addWidget(self.browser_container)

        # Right-side Drawer / Workflow & Runs Panel
        self.drawer_widget = QWidget()
        self.drawer_widget.setMinimumWidth(360)
        self.drawer_widget.setMaximumWidth(520)
        d_layout = QVBoxLayout(self.drawer_widget)
        d_layout.setContentsMargins(14, 12, 14, 12)
        d_layout.setSpacing(10)

        # Drawer Header
        d_header = QHBoxLayout()
        d_title = QLabel("Workflow Actions & Runs")
        d_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #58a6ff;")
        d_header.addWidget(d_title)
        d_header.addStretch()

        close_d_btn = QPushButton("✕")
        close_d_btn.setFixedSize(28, 28)
        close_d_btn.clicked.connect(lambda: self.drawer_btn.setChecked(False) or self._toggle_drawer())
        d_header.addWidget(close_d_btn)
        d_layout.addLayout(d_header)

        # Workflow Name Field
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self.wf_name_input = QLineEdit(self.state_mgr.current_workflow.name)
        self.wf_name_input.textChanged.connect(self._on_wf_name_changed)
        name_row.addWidget(self.wf_name_input)
        d_layout.addLayout(name_row)

        # Actions Table
        self.actions_table = QTableWidget()
        self.actions_table.setColumnCount(4)
        self.actions_table.setHorizontalHeaderLabels(["#", "Type", "Selector / Target", "Details"])
        self.actions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.actions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.actions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.actions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.actions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.actions_table.setSelectionMode(QTableWidget.SingleSelection)
        self.actions_table.doubleClicked.connect(self._edit_selected_action)
        d_layout.addWidget(self.actions_table, stretch=2)

        # Action Reorder / Manage Toolbar
        act_tools = QHBoxLayout()
        self.add_manual_btn = QPushButton("+ Action")
        self.add_manual_btn.clicked.connect(self._add_manual_action)
        act_tools.addWidget(self.add_manual_btn)

        self.edit_act_btn = QPushButton("Edit")
        self.edit_act_btn.clicked.connect(self._edit_selected_action)
        act_tools.addWidget(self.edit_act_btn)

        self.del_act_btn = QPushButton("Delete")
        self.del_act_btn.clicked.connect(self._delete_selected_action)
        act_tools.addWidget(self.del_act_btn)

        self.up_btn = QPushButton("↑")
        self.up_btn.setFixedWidth(30)
        self.up_btn.clicked.connect(self._move_action_up)
        act_tools.addWidget(self.up_btn)

        self.down_btn = QPushButton("↓")
        self.down_btn.setFixedWidth(30)
        self.down_btn.clicked.connect(self._move_action_down)
        act_tools.addWidget(self.down_btn)
        d_layout.addLayout(act_tools)

        # Storage & Persistence Buttons
        store_row = QHBoxLayout()
        self.save_repo_btn = QPushButton("Save to Repo")
        self.save_repo_btn.clicked.connect(self._save_to_github_repo)
        store_row.addWidget(self.save_repo_btn)

        self.save_json_btn = QPushButton("Save JSON")
        self.save_json_btn.clicked.connect(self._save_local_json)
        store_row.addWidget(self.save_json_btn)

        self.load_json_btn = QPushButton("Load JSON")
        self.load_json_btn.clicked.connect(self._load_local_json)
        store_row.addWidget(self.load_json_btn)
        d_layout.addLayout(store_row)

        # Run Status Card
        run_box = QFrame()
        run_box.setStyleSheet("background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 10px;")
        rb_layout = QVBoxLayout(run_box)
        rb_layout.setContentsMargins(8, 8, 8, 8)
        rb_layout.setSpacing(6)

        rb_top = QHBoxLayout()
        self.run_status_badge = QLabel("● IDLE")
        self.run_status_badge.setStyleSheet("font-weight: bold; color: #8b949e;")
        rb_top.addWidget(self.run_status_badge)
        rb_top.addStretch()

        self.refresh_runs_btn = QPushButton("History")
        self.refresh_runs_btn.clicked.connect(self._show_runs_history)
        rb_top.addWidget(self.refresh_runs_btn)
        rb_layout.addLayout(rb_top)

        self.run_progress = QProgressBar()
        self.run_progress.setRange(0, 0)
        self.run_progress.setVisible(False)
        rb_layout.addWidget(self.run_progress)

        self.step_logs = QTextEdit()
        self.step_logs.setReadOnly(True)
        self.step_logs.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background-color: #0d1117; border: none;")
        self.step_logs.setMaximumHeight(150)
        self.step_logs.setPlaceholderText("Execution step logs will stream here...")
        rb_layout.addWidget(self.step_logs)

        d_layout.addWidget(run_box)

        # Add drawer to splitter, hidden by default for maximum screen estate!
        self.splitter.addWidget(self.drawer_widget)
        self.drawer_widget.setVisible(False)

        root_layout.addWidget(self.splitter)

        # Initial Page Load
        initial_url = self.state_mgr.config.last_url or "https://github.com"
        self.web_view.setUrl(QUrl(initial_url))

        self.refresh_actions_table()

    def _nav_back(self):
        self.web_view.back()

    def _nav_forward(self):
        self.web_view.forward()

    def _nav_reload(self):
        self.web_view.reload()

    def _load_url_from_input(self):
        raw = self.url_input.text().strip()
        if not raw:
            return
        if not raw.startswith("http://") and not raw.startswith("https://") and not raw.startswith("file://"):
            raw = "https://" + raw
        self.url_input.setText(raw)
        self.state_mgr.config.last_url = raw
        self.state_mgr.config.save()
        self.web_view.setUrl(QUrl(raw))

    def _on_url_changed(self, qurl: QUrl):
        url_str = qurl.toString()
        self.url_input.setText(url_str)
        self.state_mgr.current_workflow.target_url = url_str

    def _on_page_load_finished(self, success: bool):
        # Inject our DOM inspector script whenever the page loads
        self.web_view.page().runJavaScript(INSPECTOR_JS_CODE)
        if self.inspect_mode_active:
            self.web_view.page().runJavaScript("window.__STUDIO_SET_INSPECT_MODE(true);")

    def _toggle_inspect_mode(self):
        self.inspect_mode_active = self.inspect_btn.isChecked()
        self.inspect_banner.setVisible(self.inspect_mode_active)

        if self.inspect_mode_active:
            self.inspect_btn.setStyleSheet("background-color: #1f6feb; color: #ffffff; border-color: #58a6ff; font-weight: bold;")
            self.web_view.page().runJavaScript("window.__STUDIO_SET_INSPECT_MODE(true);")
        else:
            self.inspect_btn.setStyleSheet("")
            self.web_view.page().runJavaScript("window.__STUDIO_SET_INSPECT_MODE(false);")

    def _toggle_drawer(self):
        is_open = self.drawer_btn.isChecked()
        self.drawer_widget.setVisible(is_open)
        if is_open:
            self.splitter.setSizes([self.width() - 420, 420])

    def _toggle_fullscreen(self):
        win = self.window()
        if win.isFullScreen():
            win.showNormal()
            self.fullscreen_btn.setText("⛶ Fullscreen")
        else:
            win.showFullScreen()
            self.fullscreen_btn.setText("🗗 Windowed")

    def _open_settings_dialog(self):
        dlg = SettingsDialog(self.state_mgr, parent=self)
        dlg.exec()

    def _on_element_inspected(self, element_data: dict):
        """Called when user clicks an element in Inspect Mode."""
        # Pop up the spacious quick action modal
        modal = QuickActionModal(element_data, parent=self)
        if modal.exec() == QDialog.Accepted:
            action = modal.get_action()
            self.state_mgr.current_workflow.actions.append(action)
            self.refresh_actions_table()

            # Ensure drawer is open so user sees their new action
            if not self.drawer_widget.isVisible():
                self.drawer_btn.setChecked(True)
                self._toggle_drawer()

    def refresh_actions_table(self):
        """Updates the actions table with active workflow items."""
        actions = self.state_mgr.current_workflow.actions
        self.drawer_btn.setText(f"📋 Actions ({len(actions)})")
        self.actions_table.setRowCount(len(actions))

        for row, act in enumerate(actions):
            # Index
            idx_item = QTableWidgetItem(str(row + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            self.actions_table.setItem(row, 0, idx_item)

            # Type
            type_item = QTableWidgetItem(act.type.value.upper())
            type_item.setTextAlignment(Qt.AlignCenter)
            self.actions_table.setItem(row, 1, type_item)

            # Selector
            sel = getattr(act, "selector", "-") or "-"
            self.actions_table.setItem(row, 2, QTableWidgetItem(sel))

            # Details
            details = ""
            if isinstance(act, TypeAction):
                details = f"\"{act.text}\""
            elif isinstance(act, KeyPressAction):
                details = act.key
            elif isinstance(act, WaitAction):
                details = f"{act.milliseconds}ms"
            self.actions_table.setItem(row, 3, QTableWidgetItem(details))

    def _on_wf_name_changed(self, text: str):
        self.state_mgr.current_workflow.name = text.strip() or "Untitled Workflow"

    def _add_manual_action(self):
        dlg = ActionDialog(parent=self)
        if dlg.exec():
            action = dlg.get_action()
            self.state_mgr.current_workflow.actions.append(action)
            self.refresh_actions_table()

    def _edit_selected_action(self):
        row = self.actions_table.currentRow()
        if row < 0 or row >= len(self.state_mgr.current_workflow.actions):
            return
        action = self.state_mgr.current_workflow.actions[row]
        dlg = ActionDialog(action=action, parent=self)
        if dlg.exec():
            updated = dlg.get_action()
            self.state_mgr.current_workflow.actions[row] = updated
            self.refresh_actions_table()

    def _delete_selected_action(self):
        row = self.actions_table.currentRow()
        if row < 0 or row >= len(self.state_mgr.current_workflow.actions):
            return
        del self.state_mgr.current_workflow.actions[row]
        self.refresh_actions_table()

    def _move_action_up(self):
        row = self.actions_table.currentRow()
        if row <= 0:
            return
        actions = self.state_mgr.current_workflow.actions
        actions[row - 1], actions[row] = actions[row], actions[row - 1]
        self.refresh_actions_table()
        self.actions_table.selectRow(row - 1)

    def _move_action_down(self):
        row = self.actions_table.currentRow()
        actions = self.state_mgr.current_workflow.actions
        if row < 0 or row >= len(actions) - 1:
            return
        actions[row], actions[row + 1] = actions[row + 1], actions[row]
        self.refresh_actions_table()
        self.actions_table.selectRow(row + 1)

    def _save_local_json(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Workflow JSON", "", "JSON Files (*.json)")
        if file_path:
            try:
                data = self.state_mgr.current_workflow.model_dump()
                Path(file_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
                QMessageBox.information(self, "Saved", f"Workflow saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Failed", str(e))

    def _load_local_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Workflow JSON", "", "JSON Files (*.json)")
        if file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8")
                wf = WorkflowDefinition.model_validate(json.loads(content))
                self.state_mgr.current_workflow = wf
                self.wf_name_input.setText(wf.name)
                self.refresh_actions_table()
                if wf.target_url:
                    self.web_view.setUrl(QUrl(wf.target_url))
                QMessageBox.information(self, "Loaded", f"Loaded workflow: {wf.name}")
            except Exception as e:
                QMessageBox.critical(self, "Load Failed", str(e))

    def _save_to_github_repo(self):
        client = self.state_mgr.get_github_client()
        if not client:
            self._open_settings_dialog()
            return

        remote_path = f"workflows/{self.state_mgr.current_workflow.id}.json"
        content = json.dumps(self.state_mgr.current_workflow.model_dump(), indent=2)

        try:
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
            QMessageBox.information(self, "Committed to GitHub", f"Workflow saved directly to private repository:\n{remote_path}")
        except Exception as e:
            QMessageBox.critical(self, "Commit Failed", f"Failed to commit workflow to GitHub: {e}")

    def _execute_workflow_on_github(self):
        client = self.state_mgr.get_github_client()
        if not client:
            self._open_settings_dialog()
            return

        wf = self.state_mgr.current_workflow
        if not wf.actions:
            QMessageBox.warning(self, "Empty Workflow", "Please add at least one action before executing.")
            return

        confirm = QMessageBox.question(
            self,
            "Execute on GitHub Actions",
            f"Dispatch '{wf.name}' ({len(wf.actions)} actions) to execute remotely on Ubuntu runner in '{client.owner}/{client.repo}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        # Open drawer so user sees live logs
        if not self.drawer_widget.isVisible():
            self.drawer_btn.setChecked(True)
            self._toggle_drawer()

        self.run_status_badge.setText("● DISPATCHING TO GITHUB...")
        self.run_status_badge.setStyleSheet("font-weight: bold; color: #d29922;")
        self.run_progress.setVisible(True)
        self.step_logs.clear()
        self.step_logs.append(f"Dispatched '{wf.name}' to GitHub Actions runner...")

        try:
            wf_json = json.dumps(wf.model_dump())
            client.dispatch_workflow("browser-automation.yml", inputs={"workflow_json": wf_json})
            self.step_logs.append("Workflow dispatch event accepted by GitHub REST API.")

            # Poll for run status after 3 seconds
            QTimer.singleShot(3500, self._poll_dispatched_run)
        except Exception as e:
            self.run_status_badge.setText("● DISPATCH FAILED")
            self.run_status_badge.setStyleSheet("font-weight: bold; color: #f85149;")
            self.run_progress.setVisible(False)
            self.step_logs.append(f"\nError dispatching workflow: {e}")

    def _poll_dispatched_run(self):
        client = self.state_mgr.get_github_client()
        if not client:
            return

        try:
            runs = client.list_workflow_runs("browser-automation.yml", per_page=3)
            if runs:
                latest = runs[0]
                self.run_status_badge.setText(f"● RUNNING #{latest.run_number}")
                self.run_status_badge.setStyleSheet("font-weight: bold; color: #2ea043;")
                self.step_logs.append(f"Tracking Job #{latest.run_number} on GitHub runner...")

                # Stream status periodically
                self.active_run_id = latest.id
                self.poll_timer = QTimer(self)
                self.poll_timer.setInterval(3000)
                self.poll_timer.timeout.connect(self._check_run_progress)
                self.poll_timer.start()
        except Exception as e:
            self.step_logs.append(f"Polling error: {e}")

    def _check_run_progress(self):
        client = self.state_mgr.get_github_client()
        if not client or not hasattr(self, "active_run_id"):
            return

        try:
            run_info = client.get_run(self.active_run_id)
            jobs = client.get_run_jobs(self.active_run_id)

            log_lines = [f"=== GitHub Actions Run #{run_info.run_number} ==="]
            for j in jobs:
                log_lines.append(f"Job: {j.name} ({j.status})")
                for s in j.steps:
                    c = f"[{s.conclusion.upper()}]" if s.conclusion else f"({s.status})"
                    log_lines.append(f"  • {s.name}: {c}")

            self.step_logs.setPlainText("\n".join(log_lines))

            if run_info.status == RunStatus.COMPLETED:
                self.poll_timer.stop()
                self.run_progress.setVisible(False)
                is_success = run_info.conclusion == RunConclusion.SUCCESS
                color = "#2ea043" if is_success else "#f85149"
                status_txt = run_info.conclusion.value.upper() if run_info.conclusion else "COMPLETED"
                self.run_status_badge.setText(f"● {status_txt}")
                self.run_status_badge.setStyleSheet(f"font-weight: bold; color: {color};")
                self.step_logs.append(f"\nCompleted with conclusion: {status_txt}")

        except Exception as e:
            pass

    def _show_runs_history(self):
        client = self.state_mgr.get_github_client()
        if not client:
            return
        try:
            runs = client.list_workflow_runs(per_page=10)
            lines = ["Recent Runs:"]
            for r in runs:
                conc = r.conclusion.value.upper() if r.conclusion else r.status.value.upper()
                lines.append(f"#{r.run_number}: {r.name} -> {conc} ({r.created_at})")
            self.step_logs.setPlainText("\n".join(lines))
        except Exception as e:
            self.step_logs.setText(f"Error fetching history: {e}")
