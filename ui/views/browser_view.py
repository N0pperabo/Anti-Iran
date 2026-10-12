"""Browser Preview and DOM Inspector view."""

import base64
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QByteArray, QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from app.state_manager import ApplicationStateManager
from models.inspect_bundle import DOMElementInfo, InspectBundle
from ui.widgets.inspector_panel import InspectorPanel


class LocalInspectWorker(QThread):
    """Background worker executing page inspection locally using Playwright."""

    finished = Signal(object, str)  # (InspectBundle or None, error_message)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        import asyncio
        from automation.browser import BrowserManager
        from automation.inspector import PageInspector

        async def _exec():
            mgr = BrowserManager(headless=True)
            try:
                context, page = await mgr.start(restore_state=False)
                await page.goto(self.url, wait_until="load", timeout=30000)
                inspector = PageInspector(page)
                bundle = await inspector.inspect(capture_screenshot=True)
                return bundle, ""
            except Exception as e:
                return None, str(e)
            finally:
                await mgr.close(save_state=False)

        bundle, err = asyncio.run(_exec())
        self.finished.emit(bundle, err)


class RemoteInspectWorker(QThread):
    """Background worker triggering inspect-page.yml on GitHub Actions, polling, and downloading bundle."""

    status_update = Signal(str)
    finished = Signal(object, str)  # (InspectBundle or None, error_message)

    def __init__(self, state_mgr: ApplicationStateManager, url: str):
        super().__init__()
        self.state_mgr = state_mgr
        self.url = url

    def run(self):
        import json
        import time
        from github.poller import WorkflowPoller

        client = self.state_mgr.get_github_client()
        if not client:
            self.finished.emit(None, "GitHub client is not configured. Check settings.")
            return

        try:
            self.status_update.emit("Dispatching inspect-page.yml on GitHub Actions...")
            dispatch_time = time.time()
            client.dispatch_workflow("inspect-page.yml", inputs={"url": self.url})

            poller = WorkflowPoller(client, poll_interval_sec=3.0)
            self.status_update.emit("Waiting for GitHub Actions runner to pick up job...")
            run_info = poller.wait_for_new_run("inspect-page.yml", dispatch_time, timeout_sec=60.0)
            if not run_info:
                self.finished.emit(None, "Timed out waiting for GitHub Actions run to start.")
                return

            self.status_update.emit(f"Runner active (Job #{run_info.run_number}). Inspecting page...")
            completed_run = poller.poll_run_until_complete(
                run_info.id,
                on_status_update=lambda r, jobs: self.status_update.emit(f"Status: {r.status.value.upper()} (Step logs streaming...)"),
                timeout_sec=300.0,
            )

            self.status_update.emit("Fetching inspection bundle artifacts...")
            artifacts = client.list_artifacts(completed_run.id)
            inspect_art = next((a for a in artifacts if a.name == "inspection-bundle"), None)
            if not inspect_art:
                self.finished.emit(None, "No inspection-bundle artifact found in GitHub Actions run.")
                return

            dest_dir = Path("artifacts/remote_inspect")
            dest_dir.mkdir(parents=True, exist_ok=True)
            client.download_and_extract_artifact(inspect_art.id, dest_dir)

            bundle_file = dest_dir / "inspection-bundle.json"
            if bundle_file.exists():
                data = json.loads(bundle_file.read_text(encoding="utf-8"))
                bundle = InspectBundle.model_validate(data)
                self.finished.emit(bundle, "")
            else:
                self.finished.emit(None, "inspection-bundle.json not found in downloaded artifact.")

        except Exception as e:
            self.finished.emit(None, f"Remote inspection failed: {e}")


class BrowserView(QWidget):
    """Browser preview and interactive element inspector page."""

    action_added = Signal(object)  # BaseAction

    def __init__(self, state_mgr: ApplicationStateManager, parent=None):
        super().__init__(parent)
        self.state_mgr = state_mgr
        self.current_bundle: Optional[InspectBundle] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 1. Navigation & Control Bar
        control_bar = QHBoxLayout()
        control_bar.addWidget(QLabel("Target URL:"))

        self.url_input = QLineEdit()
        self.url_input.setText(self.state_mgr.config.last_url)
        self.url_input.setPlaceholderText("https://example.com")
        control_bar.addWidget(self.url_input)

        self.local_inspect_btn = QPushButton("Local Inspect ⚡")
        self.local_inspect_btn.clicked.connect(self._run_local_inspect)
        control_bar.addWidget(self.local_inspect_btn)

        self.remote_inspect_btn = QPushButton("Inspect on GitHub Actions 🚀")
        self.remote_inspect_btn.setObjectName("primaryBtn")
        self.remote_inspect_btn.clicked.connect(self._run_remote_inspect)
        control_bar.addWidget(self.remote_inspect_btn)

        layout.addLayout(control_bar)

        # Status & Progress bar
        self.status_label = QLabel("Enter a URL and click inspect to render page DOM and scripts.")
        self.status_label.setStyleSheet("color: #8b949e;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 2. Main Content Splitter (Preview + Elements List | Inspector Panel)
        splitter = QSplitter(Qt.Horizontal)

        # Left Container: Preview & Elements
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Preview Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.image_label = QLabel("No page loaded yet. Click Inspect to preview.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #0d1117; color: #8b949e; border: 1px dashed #30363d;")
        self.scroll_area.setWidget(self.image_label)
        left_layout.addWidget(self.scroll_area, stretch=3)

        # Element Search & List
        left_layout.addWidget(QLabel("Interactive & Structural Elements:"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter elements by tag, text, id, or selector...")
        self.filter_input.textChanged.connect(self._filter_elements)
        left_layout.addWidget(self.filter_input)

        self.elements_list = QListWidget()
        self.elements_list.currentItemChanged.connect(self._on_element_selected)
        left_layout.addWidget(self.elements_list, stretch=2)

        splitter.addWidget(left_container)

        # Right Container: Inspector Panel
        self.inspector_panel = InspectorPanel()
        self.inspector_panel.create_action_requested.connect(self._handle_quick_action)
        splitter.addWidget(self.inspector_panel)

        splitter.setSizes([650, 350])
        layout.addWidget(splitter)

    def _run_local_inspect(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid website URL.")
            return

        self.state_mgr.config.last_url = url
        self.state_mgr.config.save()

        self._set_loading(True, f"Running local Chromium inspection on {url}...")
        self.worker = LocalInspectWorker(url)
        self.worker.finished.connect(self._on_inspect_finished)
        self.worker.start()

    def _run_remote_inspect(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid website URL.")
            return

        if not self.state_mgr.get_github_client():
            QMessageBox.warning(self, "Not Connected", "Please configure GitHub Personal Access Token in Settings first.")
            return

        self.state_mgr.config.last_url = url
        self.state_mgr.config.save()

        self._set_loading(True, f"Initiating GitHub Actions inspection on {url}...")
        self.remote_worker = RemoteInspectWorker(self.state_mgr, url)
        self.remote_worker.status_update.connect(lambda msg: self.status_label.setText(msg))
        self.remote_worker.finished.connect(self._on_inspect_finished)
        self.remote_worker.start()

    def _set_loading(self, loading: bool, message: str = ""):
        self.progress_bar.setVisible(loading)
        self.local_inspect_btn.setEnabled(not loading)
        self.remote_inspect_btn.setEnabled(not loading)
        if message:
            self.status_label.setText(message)

    def _on_inspect_finished(self, bundle: Optional[InspectBundle], err: str):
        self._set_loading(False)
        if err or not bundle:
            QMessageBox.critical(self, "Inspection Failed", f"Inspection failed: {err}")
            self.status_label.setText(f"Inspection error: {err}")
            return

        self.current_bundle = bundle
        self.state_mgr.current_inspect_bundle = bundle
        self.status_label.setText(f"Inspection complete: '{bundle.title}' ({len(bundle.dom_elements)} elements, {len(bundle.scripts)} scripts).")

        # Render preview screenshot
        if bundle.screenshot_base64:
            try:
                img_data = base64.b64decode(bundle.screenshot_base64)
                pix = QPixmap()
                pix.loadFromData(img_data)
                self.image_label.setPixmap(pix)
                self.image_label.setScaledContents(False)
            except Exception as e:
                self.image_label.setText(f"Failed to render screenshot: {e}")

        # Populate elements list
        self._populate_elements_list(bundle.dom_elements)

    def _populate_elements_list(self, elements):
        self.elements_list.clear()
        for idx, el in enumerate(elements):
            display = f"<{el.tag}>"
            if el.id:
                display += f" #{el.id}"
            if el.name:
                display += f" name=\"{el.name}\""
            if el.text_content:
                display += f" \"{el.text_content[:30]}\""

            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, el)
            self.elements_list.addItem(item)

        if self.elements_list.count() > 0:
            self.elements_list.setCurrentRow(0)

    def _filter_elements(self, query: str):
        query = query.lower().strip()
        for i in range(self.elements_list.count()):
            item = self.elements_list.item(i)
            el: DOMElementInfo = item.data(Qt.UserRole)
            matches = (
                query in el.tag.lower()
                or (el.id and query in el.id.lower())
                or (el.name and query in el.name.lower())
                or (el.text_content and query in el.text_content.lower())
                or any(query in s.lower() for s in el.suggested_selectors)
            )
            item.setHidden(not matches)

    def _on_element_selected(self, current: Optional[QListWidgetItem], previous):
        if current:
            el: DOMElementInfo = current.data(Qt.UserRole)
            self.inspector_panel.set_element(el)
        else:
            self.inspector_panel.set_element(None)

    def _handle_quick_action(self, action_type_str: str, selector: str):
        """Builds action from inspector and appends to workflow."""
        import uuid
        from models.action_types import (
            ActionType,
            ClickAction,
            TypeAction,
            WaitAction,
            ExtractTextAction,
        )

        act_type = ActionType(action_type_str)
        action_id = f"act-{uuid.uuid4().hex[:6]}"

        if act_type == ActionType.CLICK:
            action = ClickAction(id=action_id, selector=selector, description=f"Click on {selector}")
        elif act_type == ActionType.TYPE:
            action = TypeAction(id=action_id, selector=selector, text="Hello World", description=f"Type into {selector}")
        elif act_type == ActionType.WAIT:
            action = WaitAction(id=action_id, selector=selector, milliseconds=1000, description=f"Wait for {selector}")
        elif act_type == ActionType.EXTRACT_TEXT:
            action = ExtractTextAction(id=action_id, selector=selector, description=f"Extract text from {selector}")
        else:
            action = ClickAction(id=action_id, selector=selector)

        self.state_mgr.current_workflow.actions.append(action)
        self.action_added.emit(action)
        QMessageBox.information(
            self,
            "Action Added",
            f"Added {act_type.value.upper()} action for selector:\n{selector}\nto active workflow!",
        )
