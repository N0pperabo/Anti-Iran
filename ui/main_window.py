"""Main application window for GitHub Actions Browser Automation Studio."""

import json
import time
from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from app.state_manager import ApplicationStateManager
from models.workflow import WorkflowDefinition
from ui.theme import DARK_THEME, LIGHT_THEME
from ui.views.dashboard_view import DashboardView
from ui.views.browser_view import BrowserView
from ui.views.javascript_view import JavaScriptView
from ui.views.workflow_view import WorkflowView
from ui.views.runs_view import RunsView
from ui.views.settings_view import SettingsView


class MainWindow(QMainWindow):
    """Primary desktop studio window."""

    def __init__(self, state_mgr: ApplicationStateManager):
        super().__init__()
        self.state_mgr = state_mgr

        self.setWindowTitle("GitHub Actions Browser Automation Studio")
        self.resize(1280, 840)
        self.setMinimumSize(1000, 700)

        # Central Widget & Root Layout
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 8, 10, 8)
        root_layout.setSpacing(8)

        # Top Header Strip
        header = QHBoxLayout()
        header.setContentsMargins(4, 2, 4, 4)

        app_title = QLabel("Browser Automation Studio")
        app_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #58a6ff;")
        header.addWidget(app_title)

        header.addSpacing(20)

        self.header_repo_label = QLabel("Repository: -")
        self.header_repo_label.setStyleSheet("color: #8b949e;")
        header.addWidget(self.header_repo_label)

        self.header_branch_label = QLabel("Branch: main")
        self.header_branch_label.setStyleSheet("color: #8b949e;")
        header.addWidget(self.header_branch_label)

        header.addStretch()

        self.header_conn_pill = QLabel("● Checking...")
        self.header_conn_pill.setStyleSheet("font-weight: bold; color: #d29922;")
        header.addWidget(self.header_conn_pill)

        root_layout.addLayout(header)

        # Navigation Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.dashboard_view = DashboardView(self.state_mgr)
        self.dashboard_view.navigate_requested.connect(self._navigate_to_tab)
        self.tabs.addTab(self.dashboard_view, " Dashboard ")

        self.browser_view = BrowserView(self.state_mgr)
        self.browser_view.action_added.connect(self._on_action_added_from_browser)
        self.tabs.addTab(self.browser_view, " Browser & Inspector ")

        self.javascript_view = JavaScriptView(self.state_mgr)
        self.tabs.addTab(self.javascript_view, " JavaScript Viewer ")

        self.workflow_view = WorkflowView(self.state_mgr)
        self.workflow_view.run_workflow_requested.connect(self._on_run_workflow_requested)
        self.tabs.addTab(self.workflow_view, " Workflow Editor ")

        self.runs_view = RunsView(self.state_mgr)
        self.tabs.addTab(self.runs_view, " Runs & History ")

        self.settings_view = SettingsView(self.state_mgr)
        self.settings_view.theme_changed.connect(self._apply_theme)
        self.settings_view.connection_changed.connect(self._update_header_status)
        self.tabs.addTab(self.settings_view, " Settings ")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        root_layout.addWidget(self.tabs)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Remote execution powered by GitHub Actions runners.")

        # Apply initial theme & status
        self._apply_theme(self.state_mgr.config.theme)
        self._update_header_status()

    def _navigate_to_tab(self, tab_name: str):
        mapping = {
            "dashboard": 0,
            "browser": 1,
            "javascript": 2,
            "workflow": 3,
            "runs": 4,
            "settings": 5,
        }
        if tab_name in mapping:
            self.tabs.setCurrentIndex(mapping[tab_name])

    def _on_tab_changed(self, index: int):
        if index == 0:  # Dashboard
            self.dashboard_view.update_status()
        elif index == 2:  # JavaScript
            self.javascript_view.load_scripts_from_state()
        elif index == 3:  # Workflow Editor
            self.workflow_view.refresh_table()
        elif index == 4:  # Runs
            self.runs_view.load_runs()

    def _on_action_added_from_browser(self, action):
        self.workflow_view.refresh_table()
        self.status_bar.showMessage(f"Added action '{action.id}' to workflow.")

    def _on_run_workflow_requested(self, workflow: WorkflowDefinition):
        """Dispatches active workflow to GitHub Actions and switches to Runs view."""
        client = self.state_mgr.get_github_client()
        if not client:
            QMessageBox.warning(
                self,
                "GitHub Not Configured",
                "Please configure your GitHub Repository and Personal Access Token in Settings before running workflows.",
            )
            self._navigate_to_tab("settings")
            return

        confirm = QMessageBox.question(
            self,
            "Execute Workflow",
            f"Dispatch '{workflow.name}' ({len(workflow.actions)} actions) to execute on GitHub Actions runner (ubuntu-latest)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        # Switch to Runs tab
        self._navigate_to_tab("runs")
        self.status_bar.showMessage(f"Dispatching workflow '{workflow.name}' to GitHub Actions...")

        try:
            workflow_json_str = json.dumps(workflow.model_dump())
            dispatch_time = time.time()
            client.dispatch_workflow(
                "browser-automation.yml",
                inputs={
                    "workflow_file": "",
                    "workflow_json": workflow_json_str,
                },
            )

            # Wait briefly and track the run
            QTimer.singleShot(4000, lambda: self._find_and_track_run(dispatch_time))
        except Exception as e:
            QMessageBox.critical(self, "Dispatch Failed", f"Failed to dispatch workflow: {e}")

    def _find_and_track_run(self, dispatch_time: float):
        client = self.state_mgr.get_github_client()
        if not client:
            return

        try:
            runs = client.list_workflow_runs("browser-automation.yml", per_page=3)
            if runs:
                latest = runs[0]
                self.runs_view.load_runs()
                self.runs_view.track_run(latest.id)
                self.status_bar.showMessage(f"Active run #{latest.run_number} monitored on GitHub Actions.")
            else:
                self.status_bar.showMessage("Workflow dispatched. Click 'Refresh Runs List' to track.")
        except Exception as e:
            self.status_bar.showMessage(f"Error fetching dispatched run: {e}")

    def _update_header_status(self):
        cfg = self.state_mgr.config
        self.header_repo_label.setText(f"Repository: {cfg.repo_owner}/{cfg.repo_name}" if cfg.repo_owner else "Repository: Not configured")
        self.header_branch_label.setText(f"Branch: {cfg.default_branch}")

        val = self.state_mgr.last_validation
        if not val:
            val = self.state_mgr.validate_connection()

        if val and val.valid:
            self.header_conn_pill.setText("● Connected")
            self.header_conn_pill.setStyleSheet("font-weight: bold; color: #2ea043;")
        else:
            self.header_conn_pill.setText("● Disconnected")
            self.header_conn_pill.setStyleSheet("font-weight: bold; color: #f85149;")

        self.dashboard_view.update_status()

    def _apply_theme(self, theme_name: str):
        app = QApplication.instance()
        if app:
            qss = DARK_THEME if theme_name == "dark" else LIGHT_THEME
            app.setStyleSheet(qss)
