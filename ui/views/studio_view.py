"""Full-Screen Interactive Browser Studio with Natural Action Recording, Remote Cloud Execution, and Zero Local Traffic."""

import base64
import json
import time
import uuid
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QByteArray, QEvent, QObject, QThread, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWebEngineCore import QWebEnginePage
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
from models.inspect_bundle import InspectBundle
from models.workflow import WorkflowDefinition
from ui.widgets.action_dialog import ActionDialog
from ui.widgets.settings_dialog import SettingsDialog
from ui.widgets.web_inspector_script import INSPECTOR_JS_CODE
from github.models import RunConclusion, RunStatus, WorkflowRunInfo
from github.poller import WorkflowPoller


class RemotePageFetchWorker(QThread):
    """Background worker that dispatches inspect-page.yml to fetch target page in cloud."""

    status_update = Signal(str)
    finished = Signal(object, str)

    def __init__(self, state_mgr: ApplicationStateManager, url: str):
        super().__init__()
        self.state_mgr = state_mgr
        self.url = url

    def run(self):
        client = self.state_mgr.get_github_client()
        if not client:
            self.finished.emit(None, "GitHub client not configured. Open Settings first.")
            return

        try:
            self.status_update.emit(f"Dispatching fetch for '{self.url}' on Ubuntu runner...")
            dispatch_time = time.time()
            client.dispatch_workflow("inspect-page.yml", inputs={"url": self.url})

            poller = WorkflowPoller(client, poll_interval_sec=3.0)
            self.status_update.emit("Waiting for GitHub Actions runner to start...")
            run_info = poller.wait_for_new_run("inspect-page.yml", dispatch_time, timeout_sec=60.0)
            if not run_info:
                self.finished.emit(None, "Timed out waiting for runner to pick up job.")
                return

            self.status_update.emit(f"Runner Active (Job #{run_info.run_number}). Fetching page in cloud Chromium...")
            completed_run = poller.poll_run_until_complete(
                run_info.id,
                on_status_update=lambda r, jobs: self.status_update.emit(f"Status: {r.status.value.upper()} on cloud runner..."),
                timeout_sec=300.0,
            )

            self.status_update.emit("Downloading rendered page snapshot...")
            artifacts = client.list_artifacts(completed_run.id)
            inspect_art = next((a for a in artifacts if a.name == "inspection-bundle"), None)
            if not inspect_art:
                self.finished.emit(None, "No inspection-bundle artifact found in completed run.")
                return

            dest_dir = Path("artifacts/remote_fetch")
            dest_dir.mkdir(parents=True, exist_ok=True)
            client.download_and_extract_artifact(inspect_art.id, dest_dir)

            bundle_file = dest_dir / "inspection-bundle.json"
            if bundle_file.exists():
                data = json.loads(bundle_file.read_text(encoding="utf-8"))
                bundle = InspectBundle.model_validate(data)
                self.finished.emit(bundle, "")
            else:
                self.finished.emit(None, "inspection-bundle.json not found in downloaded bundle.")

        except Exception as e:
            self.finished.emit(None, str(e))


class RemoteWorkflowExecutionWorker(QThread):
    """Background worker that dispatches browser-automation.yml, streams step logs, and downloads resulting page."""

    status_update = Signal(str)
    step_log_received = Signal(str)
    finished = Signal(object, object, str)

    def __init__(self, state_mgr: ApplicationStateManager, workflow: WorkflowDefinition):
        super().__init__()
        self.state_mgr = state_mgr
        self.workflow = workflow

    def run(self):
        client = self.state_mgr.get_github_client()
        if not client:
            self.finished.emit(None, None, "GitHub client not configured.")
            return

        try:
            wf_json = json.dumps(self.workflow.model_dump())
            self.status_update.emit(f"Dispatching '{self.workflow.name}' to GitHub Actions...")
            dispatch_time = time.time()
            client.dispatch_workflow("browser-automation.yml", inputs={"workflow_json": wf_json})

            poller = WorkflowPoller(client, poll_interval_sec=3.0)
            self.status_update.emit("Waiting for Ubuntu runner to start...")
            run_info = poller.wait_for_new_run("browser-automation.yml", dispatch_time, timeout_sec=60.0)
            if not run_info:
                self.finished.emit(None, None, "Timed out waiting for workflow run to start.")
                return

            self.status_update.emit(f"Runner Active (Job #{run_info.run_number}). Executing actions...")

            def _on_update(r: WorkflowRunInfo, jobs):
                log_lines = [f"=== GitHub Actions Run #{r.run_number} ==="]
                for j in jobs:
                    log_lines.append(f"Job: {j.name} ({j.status})")
                    for s in j.steps:
                        c = f"[{s.conclusion.upper()}]" if s.conclusion else f"({s.status})"
                        log_lines.append(f"  • {s.name}: {c}")
                self.step_log_received.emit("\n".join(log_lines))

            completed_run = poller.poll_run_until_complete(
                run_info.id,
                on_status_update=_on_update,
                timeout_sec=300.0,
            )

            # Download resulting artifacts
            self.status_update.emit("Retrieving execution bundle & updated page state...")
            artifacts = client.list_artifacts(completed_run.id)
            run_art = next((a for a in artifacts if a.name == "run-bundle"), None)
            bundle: Optional[InspectBundle] = None

            if run_art:
                dest_dir = Path(f"artifacts/run_{completed_run.run_number}")
                dest_dir.mkdir(parents=True, exist_ok=True)
                client.download_and_extract_artifact(run_art.id, dest_dir)

                bundle_file = dest_dir / "inspection-bundle.json"
                if bundle_file.exists():
                    data = json.loads(bundle_file.read_text(encoding="utf-8"))
                    bundle = InspectBundle.model_validate(data)

            self.finished.emit(completed_run, bundle, "")

        except Exception as e:
            self.finished.emit(None, None, str(e))


class SecureStudioWebPage(QWebEnginePage):
    """Custom QWebEnginePage that blocks ALL local outbound navigation requests and captures recorded actions."""

    action_recorded = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

    def acceptNavigationRequest(self, url: QUrl, nav_type: QWebEnginePage.NavigationType, is_main_frame: bool) -> bool:
        """Blocks local browser from navigating to external web servers (zero local network traffic)."""
        url_str = url.toString()
        if url_str.startswith("data:") or url_str.startswith("about:") or url_str.startswith("blob:"):
            return True
        # Block any external HTTP/HTTPS request from executing locally
        print(f"[Studio Network Guard] Blocked local outbound navigation to: {url_str}")
        return False

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        if message.startswith("STUDIO_RECORD:"):
            try:
                payload = json.loads(message[len("STUDIO_RECORD:"):])
                self.action_recorded.emit(payload)
            except Exception as e:
                print(f"Error parsing recorded action: {e}")
        else:
            super().javaScriptConsoleMessage(level, message, line_number, source_id)


class StudioView(QWidget):
    """Unified full-screen interactive studio workspace with natural action recording and cloud execution."""

    def __init__(self, state_mgr: ApplicationStateManager, parent=None):
        super().__init__(parent)
        self.state_mgr = state_mgr
        self.current_page_url = self.state_mgr.config.last_url or "https://github.com"

        # Root layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Sleek Toolbar
        self.toolbar = QFrame()
        self.toolbar.setStyleSheet("background-color: #161b22; border-bottom: 1px solid #30363d; padding: 4px 10px;")
        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(8)

        # Brand
        logo_lbl = QLabel("⚡ Studio")
        logo_lbl.setStyleSheet("font-weight: bold; color: #58a6ff; font-size: 14px; padding-right: 4px;")
        tb_layout.addWidget(logo_lbl)

        # URL Input Bar
        self.url_input = QLineEdit()
        self.url_input.setText(self.current_page_url)
        self.url_input.setPlaceholderText("Enter website URL to fetch via GitHub Actions (e.g. https://github.com)...")
        self.url_input.returnPressed.connect(self._fetch_url_via_github)
        tb_layout.addWidget(self.url_input, stretch=1)

        # Fetch button
        self.fetch_btn = QPushButton("🌐 Fetch via GitHub 🚀")
        self.fetch_btn.setToolTip("Opens target website remotely in GitHub cloud (zero local traffic)")
        self.fetch_btn.clicked.connect(self._fetch_url_via_github)
        tb_layout.addWidget(self.fetch_btn)

        tb_layout.addSpacing(10)

        # Actions Drawer Button
        self.drawer_btn = QPushButton("📋 Actions Queue (0)")
        self.drawer_btn.setCheckable(True)
        self.drawer_btn.setChecked(False)
        self.drawer_btn.setToolTip("Open / Close Workflow Actions Drawer")
        self.drawer_btn.clicked.connect(self._toggle_drawer)
        tb_layout.addWidget(self.drawer_btn)

        # Run Workflow on GitHub Primary Button
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

        # Fullscreen Button
        self.fullscreen_btn = QPushButton("⛶ Fullscreen")
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        tb_layout.addWidget(self.fullscreen_btn)

        root_layout.addWidget(self.toolbar)

        # 2. Status Banner (Cloud fetch indicator)
        self.status_banner = QFrame()
        self.status_banner.setStyleSheet("background-color: #1f6feb; color: #ffffff; padding: 6px 16px; border-bottom: 1px solid #388bfd;")
        sb_layout = QHBoxLayout(self.status_banner)
        sb_layout.setContentsMargins(12, 4, 12, 4)

        self.banner_msg = QLabel("Ready.")
        self.banner_msg.setStyleSheet("font-weight: bold; color: #ffffff;")
        sb_layout.addWidget(self.banner_msg)
        sb_layout.addStretch()

        self.banner_close_btn = QPushButton("✕")
        self.banner_close_btn.setStyleSheet("background-color: transparent; color: #ffffff; font-weight: bold; border: none; font-size: 14px;")
        self.banner_close_btn.clicked.connect(lambda: self.status_banner.setVisible(False))
        sb_layout.addWidget(self.banner_close_btn)
        self.status_banner.setVisible(False)
        root_layout.addWidget(self.status_banner)

        # 3. Center Splitter: Chromium Canvas + Collapsible Drawer
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(4)

        # Browser Container
        self.browser_container = QWidget()
        bc_layout = QVBoxLayout(self.browser_container)
        bc_layout.setContentsMargins(0, 0, 0, 0)
        bc_layout.setSpacing(0)

        self.web_view = QWebEngineView()
        self.web_page = SecureStudioWebPage(self.web_view)
        self.web_page.action_recorded.connect(self._on_action_recorded_from_page)
        self.web_view.setPage(self.web_page)
        self.web_view.loadFinished.connect(self._on_page_load_finished)

        bc_layout.addWidget(self.web_view)
        self.splitter.addWidget(self.browser_container)

        # Right-side Drawer Panel
        self.drawer_widget = QWidget()
        self.drawer_widget.setMinimumWidth(380)
        self.drawer_widget.setMaximumWidth(520)
        d_layout = QVBoxLayout(self.drawer_widget)
        d_layout.setContentsMargins(14, 12, 14, 12)
        d_layout.setSpacing(10)

        # Drawer Header
        d_header = QHBoxLayout()
        d_title = QLabel("Recorded Workflow Actions")
        d_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #58a6ff;")
        d_header.addWidget(d_title)
        d_header.addStretch()

        close_d_btn = QPushButton("✕")
        close_d_btn.setFixedSize(28, 28)
        close_d_btn.clicked.connect(lambda: self.drawer_btn.setChecked(False) or self._toggle_drawer())
        d_header.addWidget(close_d_btn)
        d_layout.addLayout(d_header)

        # Workflow Name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self.wf_name_input = QLineEdit(self.state_mgr.current_workflow.name)
        self.wf_name_input.textChanged.connect(lambda t: setattr(self.state_mgr.current_workflow, "name", t.strip() or "Workflow"))
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

        # Action Management Buttons
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

        self.clear_queue_btn = QPushButton("Clear")
        self.clear_queue_btn.setToolTip("Clear recorded actions")
        self.clear_queue_btn.clicked.connect(self._clear_actions)
        act_tools.addWidget(self.clear_queue_btn)

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
        rb_layout.addLayout(rb_top)

        self.run_progress = QProgressBar()
        self.run_progress.setRange(0, 0)
        self.run_progress.setVisible(False)
        rb_layout.addWidget(self.run_progress)

        self.step_logs = QTextEdit()
        self.step_logs.setReadOnly(True)
        self.step_logs.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background-color: #0d1117; border: none;")
        self.step_logs.setMaximumHeight(160)
        self.step_logs.setPlaceholderText("Execution step logs will stream here...")
        rb_layout.addWidget(self.step_logs)

        d_layout.addWidget(run_box)

        self.splitter.addWidget(self.drawer_widget)
        self.drawer_widget.setVisible(False)

        root_layout.addWidget(self.splitter)

        # Initial Welcome Screen
        self._load_welcome_screen()
        self.refresh_actions_table()

    def _load_welcome_screen(self):
        welcome_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    background-color: #0d1117;
                    color: #c9d1d9;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 80vh;
                    margin: 0;
                    padding: 20px;
                }}
                .card {{
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 32px 40px;
                    max-width: 640px;
                    text-align: center;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
                }}
                h1 {{ color: #58a6ff; margin-top: 0; font-size: 26px; }}
                p {{ color: #8b949e; line-height: 1.6; font-size: 15px; }}
                .step {{
                    background-color: #21262d;
                    padding: 10px 16px;
                    border-radius: 8px;
                    margin: 10px 0;
                    text-align: left;
                    font-size: 14px;
                    color: #f0f6fc;
                }}
                .highlight {{ color: #2ea043; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>⚡ Browser Automation Studio</h1>
                <p>100% Remote Cloud Execution on GitHub Actions Ubuntu Runners.</p>
                <div class="step">1. Enter target URL above and click <span class="highlight">"🌐 Fetch via GitHub 🚀"</span>.</div>
                <div class="step">2. The page loads completely from the cloud (Zero local network traffic).</div>
                <div class="step">3. <b>Interact naturally:</b> Click buttons or type into boxes. Every action is recorded automatically!</div>
                <div class="step">4. Click <span class="highlight">"🚀 RUN ON GITHUB ACTIONS"</span>. The cloud runner executes your actions and updates your screen!</div>
            </div>
        </body>
        </html>
        """
        self.web_view.setHtml(welcome_html)

    def _fetch_url_via_github(self):
        """Fetches the target webpage using GitHub Actions runner in cloud."""
        raw = self.url_input.text().strip()
        if not raw:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid website URL.")
            return

        if not raw.startswith("http://") and not raw.startswith("https://"):
            raw = "https://" + raw
        self.url_input.setText(raw)
        self.current_page_url = raw
        self.state_mgr.config.last_url = raw
        self.state_mgr.config.save()
        self.state_mgr.current_workflow.target_url = raw

        client = self.state_mgr.get_github_client()
        if not client:
            self._open_settings_dialog()
            return

        # Show banner
        self.status_banner.setStyleSheet("background-color: #d29922; color: #0d1117; padding: 6px 16px;")
        self.banner_msg.setText(f"🌐 FETCHING VIA GITHUB RUNNER: Opening {raw} in cloud (zero local PC network traffic)...")
        self.status_banner.setVisible(True)
        self.fetch_btn.setEnabled(False)

        # Run background worker
        self.fetch_worker = RemotePageFetchWorker(self.state_mgr, raw)
        self.fetch_worker.status_update.connect(lambda msg: self.banner_msg.setText(f"🌐 GITHUB ACTIONS: {msg}"))
        self.fetch_worker.finished.connect(self._on_remote_fetch_finished)
        self.fetch_worker.start()

    def _on_remote_fetch_finished(self, bundle: Optional[InspectBundle], error_msg: str):
        self.fetch_btn.setEnabled(True)
        if error_msg or not bundle:
            self.status_banner.setStyleSheet("background-color: #da3633; color: #ffffff; padding: 6px 16px;")
            self.banner_msg.setText(f"❌ FETCH FAILED: {error_msg}")
            QMessageBox.critical(self, "Remote Fetch Error", f"Failed to fetch page via GitHub Actions:\n{error_msg}")
            return

        # Render the fetched HTML snapshot
        self.status_banner.setStyleSheet("background-color: #238636; color: #ffffff; padding: 6px 16px;")
        self.banner_msg.setText(f"✓ Loaded from GitHub Cloud: '{bundle.title}' - Interact naturally to record actions.")

        html_content = bundle.html_snapshot or "<h1>Page snapshot loaded successfully</h1>"
        self.web_view.setHtml(html_content, QUrl(bundle.url))
        self.url_input.setText(bundle.url)
        self.current_page_url = bundle.url
        self.state_mgr.current_workflow.target_url = bundle.url
        self.state_mgr.current_inspect_bundle = bundle

    def _on_page_load_finished(self, success: bool):
        # Inject natural recorder and network protection script
        self.web_view.page().runJavaScript(INSPECTOR_JS_CODE)

    def _on_action_recorded_from_page(self, payload: dict):
        """Called automatically whenever the user clicks an element or types on the page."""
        act_type = payload.get("type", "click")
        selector = payload.get("selector", "")
        desc = payload.get("description", "")
        fallbacks = payload.get("fallback_selectors", [])
        act_id = f"act-{uuid.uuid4().hex[:6]}"

        action = None
        if act_type == "click":
            action = ClickAction(
                id=act_id,
                selector=selector,
                fallback_selectors=fallbacks,
                description=desc or f"Click on {selector}",
            )
        elif act_type == "type":
            text_val = payload.get("text", "")
            action = TypeAction(
                id=act_id,
                selector=selector,
                fallback_selectors=fallbacks,
                text=text_val,
                description=desc or f"Type into {selector}",
            )
        elif act_type == "key_press":
            key_val = payload.get("key", "Enter")
            action = KeyPressAction(
                id=act_id,
                key=key_val,
                description=desc or f"Press key {key_val}",
            )

        if action:
            self.state_mgr.current_workflow.actions.append(action)
            self.refresh_actions_table()

            # Open drawer so user sees their recorded action
            if not self.drawer_widget.isVisible():
                self.drawer_btn.setChecked(True)
                self._toggle_drawer()

    def refresh_actions_table(self):
        """Updates the actions table."""
        actions = self.state_mgr.current_workflow.actions
        self.drawer_btn.setText(f"📋 Actions Queue ({len(actions)})")
        self.actions_table.setRowCount(len(actions))

        for row, act in enumerate(actions):
            idx_item = QTableWidgetItem(str(row + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            self.actions_table.setItem(row, 0, idx_item)

            type_item = QTableWidgetItem(act.type.value.upper())
            type_item.setTextAlignment(Qt.AlignCenter)
            self.actions_table.setItem(row, 1, type_item)

            sel = getattr(act, "selector", "-") or "-"
            self.actions_table.setItem(row, 2, QTableWidgetItem(sel))

            details = ""
            if isinstance(act, TypeAction):
                details = f"\"{act.text}\""
            elif isinstance(act, KeyPressAction):
                details = act.key
            elif isinstance(act, WaitAction):
                details = f"{act.milliseconds}ms"
            self.actions_table.setItem(row, 3, QTableWidgetItem(details))

    def _clear_actions(self):
        self.state_mgr.current_workflow.actions.clear()
        self.refresh_actions_table()

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
                    self.url_input.setText(wf.target_url)
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
            QMessageBox.information(self, "Committed", f"Workflow saved to private repository:\n{remote_path}")
        except Exception as e:
            QMessageBox.critical(self, "Commit Failed", str(e))

    def _execute_workflow_on_github(self):
        """Dispatches active workflow to GitHub Actions runner, streams logs, and updates the resulting page!"""
        client = self.state_mgr.get_github_client()
        if not client:
            self._open_settings_dialog()
            return

        wf = self.state_mgr.current_workflow
        if not wf.actions:
            QMessageBox.warning(self, "Empty Workflow", "Please record or add at least one action to execute.")
            return

        if self.current_page_url and not self.current_page_url.startswith("about:"):
            wf.target_url = self.current_page_url

        # Open drawer so user sees live logs
        if not self.drawer_widget.isVisible():
            self.drawer_btn.setChecked(True)
            self._toggle_drawer()

        self.run_status_badge.setText("● DISPATCHING TO GITHUB...")
        self.run_status_badge.setStyleSheet("font-weight: bold; color: #d29922;")
        self.run_progress.setVisible(True)
        self.run_btn.setEnabled(False)
        self.step_logs.clear()
        self.step_logs.append(f"Dispatching '{wf.name}' ({len(wf.actions)} actions) to cloud runner...")

        # Run background execution worker
        self.exec_worker = RemoteWorkflowExecutionWorker(self.state_mgr, wf)
        self.exec_worker.status_update.connect(lambda msg: self.run_status_badge.setText(f"● {msg.upper()}"))
        self.exec_worker.step_log_received.connect(lambda log: self.step_logs.setPlainText(log))
        self.exec_worker.finished.connect(self._on_remote_execution_finished)
        self.exec_worker.start()

    def _on_remote_execution_finished(self, completed_run: Optional[WorkflowRunInfo], bundle: Optional[InspectBundle], error_msg: str):
        self.run_progress.setVisible(False)
        self.run_btn.setEnabled(True)

        if error_msg:
            self.run_status_badge.setText("● EXECUTION FAILED")
            self.run_status_badge.setStyleSheet("font-weight: bold; color: #f85149;")
            self.step_logs.append(f"\nExecution error: {error_msg}")
            QMessageBox.critical(self, "Execution Error", f"Workflow execution failed:\n{error_msg}")
            return

        if completed_run:
            is_success = (completed_run.conclusion == RunConclusion.SUCCESS)
            color = "#2ea043" if is_success else "#f85149"
            status_txt = completed_run.conclusion.value.upper() if completed_run.conclusion else "COMPLETED"
            self.run_status_badge.setText(f"● {status_txt}")
            self.run_status_badge.setStyleSheet(f"font-weight: bold; color: {color};")
            self.step_logs.append(f"\nCompleted on GitHub Actions with status: {status_txt}")

            # 1. Update the live page with the resulting snapshot from runner!
            if bundle and bundle.html_snapshot:
                self.web_view.setHtml(bundle.html_snapshot, QUrl(bundle.url))
                self.url_input.setText(bundle.url)
                self.current_page_url = bundle.url
                self.state_mgr.current_workflow.target_url = bundle.url
                self.state_mgr.current_inspect_bundle = bundle
                self.status_banner.setStyleSheet("background-color: #238636; color: #ffffff; padding: 6px 16px;")
                self.banner_msg.setText(f"✓ Actions executed in cloud! Page updated: {bundle.url}")
                self.status_banner.setVisible(True)

            # 2. CLEAR the executed actions queue so user can begin next actions!
            self.state_mgr.current_workflow.actions.clear()
            self.refresh_actions_table()
            self.step_logs.append("\n✓ Executed action queue cleared.")
