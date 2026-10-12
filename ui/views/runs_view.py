"""Runs view for tracking GitHub Actions workflow executions, live logs, and artifacts."""

import json
from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from app.state_manager import ApplicationStateManager
from github.models import ArtifactInfo, JobInfo, RunConclusion, RunStatus, WorkflowRunInfo
from github.poller import WorkflowPoller


class RunMonitoringWorker(QThread):
    """Background worker polling GitHub Actions run progress until completion."""

    status_changed = Signal(object, list)  # (WorkflowRunInfo, List[JobInfo])
    finished = Signal(object, str)        # (WorkflowRunInfo or None, error_message)

    def __init__(self, state_mgr: ApplicationStateManager, run_id: int):
        super().__init__()
        self.state_mgr = state_mgr
        self.run_id = run_id

    def run(self):
        client = self.state_mgr.get_github_client()
        if not client:
            self.finished.emit(None, "GitHub client not initialized")
            return

        poller = WorkflowPoller(client, poll_interval_sec=3.0)
        try:
            completed_run = poller.poll_run_until_complete(
                run_id=self.run_id,
                on_status_update=lambda r, jobs: self.status_changed.emit(r, jobs),
                timeout_sec=600.0,
            )
            self.finished.emit(completed_run, "")
        except Exception as e:
            self.finished.emit(None, str(e))


class RunsView(QWidget):
    """Workflow execution monitoring, logs, and artifacts view."""

    def __init__(self, state_mgr: ApplicationStateManager, parent=None):
        super().__init__(parent)
        self.state_mgr = state_mgr
        self.active_worker: Optional[RunMonitoringWorker] = None
        self.selected_run: Optional[WorkflowRunInfo] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Toolbar
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("GitHub Actions Automation Runs"))
        toolbar.addStretch()

        self.refresh_btn = QPushButton("Refresh Runs List")
        self.refresh_btn.clicked.connect(self.load_runs)
        toolbar.addWidget(self.refresh_btn)
        layout.addLayout(toolbar)

        # Splitter: Runs List | Run Details & Logs
        splitter = QSplitter(Qt.Horizontal)

        # Left: Runs Table
        left_box = QWidget()
        l_layout = QVBoxLayout(left_box)
        l_layout.setContentsMargins(0, 0, 0, 0)

        self.runs_table = QTableWidget()
        self.runs_table.setColumnCount(4)
        self.runs_table.setHorizontalHeaderLabels(["Run #", "Workflow", "Status", "Created At"])
        self.runs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.runs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.runs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.runs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.runs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.runs_table.setSelectionMode(QTableWidget.SingleSelection)
        self.runs_table.itemSelectionChanged.connect(self._on_run_selected)
        l_layout.addWidget(self.runs_table)
        splitter.addWidget(left_box)

        # Right: Run Details, Live Logs, and Failure Artifacts
        right_box = QWidget()
        r_layout = QVBoxLayout(right_box)
        r_layout.setContentsMargins(0, 0, 0, 0)

        # Status & Control Card
        details_group = QGroupBox("Selected Run Status")
        d_layout = QVBoxLayout(details_group)

        meta_row = QHBoxLayout()
        self.status_pill = QLabel("● IDLE")
        self.status_pill.setStyleSheet("font-size: 15px; font-weight: bold; color: #8b949e;")
        meta_row.addWidget(self.status_pill)
        meta_row.addStretch()

        self.open_gh_btn = QPushButton("Open on GitHub")
        self.open_gh_btn.clicked.connect(self._open_in_browser)
        meta_row.addWidget(self.open_gh_btn)

        self.download_art_btn = QPushButton("Download Artifacts")
        self.download_art_btn.clicked.connect(self._download_artifacts)
        meta_row.addWidget(self.download_art_btn)
        d_layout.addLayout(meta_row)

        self.run_info_label = QLabel("Select a run to view execution timeline and step logs.")
        self.run_info_label.setStyleSheet("color: #8b949e;")
        d_layout.addWidget(self.run_info_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        d_layout.addWidget(self.progress_bar)
        r_layout.addWidget(details_group)

        # Step Logs & Diagnostic Viewer
        logs_group = QGroupBox("Execution Step Logs & Diagnostics")
        log_layout = QVBoxLayout(logs_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: Consolas, monospace; background-color: #0d1117;")
        log_layout.addWidget(self.log_text)

        # Failure Screenshot Preview
        self.failure_shot_label = QLabel()
        self.failure_shot_label.setAlignment(Qt.AlignCenter)
        self.failure_shot_label.setVisible(False)
        self.failure_shot_label.setStyleSheet("border: 1px solid #f85149; background-color: #0d1117;")
        log_layout.addWidget(self.failure_shot_label)

        r_layout.addWidget(logs_group)

        splitter.addWidget(right_box)
        splitter.setSizes([400, 600])
        layout.addWidget(splitter)

    def load_runs(self):
        """Fetches recent runs from GitHub Actions."""
        client = self.state_mgr.get_github_client()
        if not client:
            return

        try:
            runs = client.list_workflow_runs(per_page=20)
            self.state_mgr.recent_runs = runs
            self.runs_table.setRowCount(len(runs))

            for row, r in enumerate(runs):
                self.runs_table.setItem(row, 0, QTableWidgetItem(f"#{r.run_number}"))
                self.runs_table.setItem(row, 1, QTableWidgetItem(r.name))

                # Status & Conclusion
                status_str = r.status.value.upper()
                if r.conclusion:
                    status_str = f"{r.conclusion.value.upper()}"
                status_item = QTableWidgetItem(status_str)
                if r.conclusion == RunConclusion.SUCCESS:
                    status_item.setForeground(Qt.green)
                elif r.conclusion in (RunConclusion.FAILURE, RunConclusion.TIMED_OUT):
                    status_item.setForeground(Qt.red)
                elif r.status in (RunStatus.IN_PROGRESS, RunStatus.QUEUED):
                    status_item.setForeground(Qt.yellow)
                self.runs_table.setItem(row, 2, status_item)

                created = r.created_at.replace("T", " ").replace("Z", "")
                self.runs_table.setItem(row, 3, QTableWidgetItem(created))

            if runs and self.runs_table.currentRow() < 0:
                self.runs_table.selectRow(0)
        except Exception as e:
            self.run_info_label.setText(f"Failed to fetch runs: {e}")

    def track_run(self, run_id: int):
        """Starts live monitoring of an actively dispatched workflow run."""
        self.progress_bar.setVisible(True)
        self.status_pill.setText("● RUNNING ON GITHUB RUNNER")
        self.status_pill.setStyleSheet("font-size: 15px; font-weight: bold; color: #2ea043;")
        self.log_text.clear()
        self.log_text.append(f"Tracking GitHub Actions Run #{run_id}...\nWaiting for step execution output...\n")

        self.active_worker = RunMonitoringWorker(self.state_mgr, run_id)
        self.active_worker.status_changed.connect(self._on_live_status_update)
        self.active_worker.finished.connect(self._on_live_run_finished)
        self.active_worker.start()

    def _on_live_status_update(self, run_info: WorkflowRunInfo, jobs: List[JobInfo]):
        self.selected_run = run_info
        status_text = run_info.status.value.upper()
        if run_info.conclusion:
            status_text = run_info.conclusion.value.upper()
        self.status_pill.setText(f"● {status_text}")

        # Update log steps
        log_lines = [f"=== Workflow Run #{run_info.run_number}: {run_info.name} ===", f"Status: {status_text}\n"]
        for j in jobs:
            log_lines.append(f"Job: {j.name} ({j.status})")
            for s in j.steps:
                conc = f"[{s.conclusion.upper()}]" if s.conclusion else f"({s.status})"
                log_lines.append(f"  [{s.number}] {s.name}: {conc}")

        self.log_text.setPlainText("\n".join(log_lines))

    def _on_live_run_finished(self, completed_run: Optional[WorkflowRunInfo], error_msg: str):
        self.progress_bar.setVisible(False)
        if error_msg:
            self.status_pill.setText("● ERROR TRACKING RUN")
            self.status_pill.setStyleSheet("color: #f85149;")
            self.log_text.append(f"\nMonitoring error: {error_msg}")
            return

        if completed_run:
            self.selected_run = completed_run
            is_success = completed_run.conclusion == RunConclusion.SUCCESS
            color = "#2ea043" if is_success else "#f85149"
            self.status_pill.setText(f"● {completed_run.conclusion.value.upper() if completed_run.conclusion else 'COMPLETED'}")
            self.status_pill.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {color};")
            self.log_text.append(f"\nWorkflow finished with conclusion: {completed_run.conclusion}")
            # Automatically try to fetch artifacts
            self._download_artifacts()
            self.load_runs()

    def _on_run_selected(self):
        row = self.runs_table.currentRow()
        if row < 0 or row >= len(self.state_mgr.recent_runs):
            return

        run_info = self.state_mgr.recent_runs[row]
        self.selected_run = run_info
        status_text = run_info.status.value.upper()
        if run_info.conclusion:
            status_text = run_info.conclusion.value.upper()

        is_success = run_info.conclusion == RunConclusion.SUCCESS
        color = "#2ea043" if is_success else ("#f85149" if run_info.conclusion else "#8b949e")
        self.status_pill.setText(f"● {status_text}")
        self.status_pill.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {color};")

        self.run_info_label.setText(
            f"Run ID: {run_info.id} | Run #{run_info.run_number} | Branch: {run_info.head_branch} | Event: {run_info.event}"
        )

        # Fetch job steps for this run
        client = self.state_mgr.get_github_client()
        if client:
            try:
                jobs = client.get_run_jobs(run_info.id)
                log_lines = [f"=== Workflow Run #{run_info.run_number}: {run_info.name} ===", f"Status: {status_text}\n"]
                for j in jobs:
                    log_lines.append(f"Job: {j.name} ({j.status})")
                    for s in j.steps:
                        conc = f"[{s.conclusion.upper()}]" if s.conclusion else f"({s.status})"
                        log_lines.append(f"  [{s.number}] {s.name}: {conc}")
                self.log_text.setPlainText("\n".join(log_lines))
            except Exception as e:
                self.log_text.setPlainText(f"Could not fetch jobs: {e}")

    def _open_in_browser(self):
        if self.selected_run and self.selected_run.html_url:
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(self.selected_run.html_url))

    def _download_artifacts(self):
        if not self.selected_run:
            return
        client = self.state_mgr.get_github_client()
        if not client:
            return

        try:
            artifacts = client.list_artifacts(self.selected_run.id)
            if not artifacts:
                self.log_text.append("\nNo artifacts found for this run.")
                return

            dest_dir = Path(f"artifacts/run_{self.selected_run.run_number}")
            for a in artifacts:
                client.download_and_extract_artifact(a.id, dest_dir)
                self.log_text.append(f"\nDownloaded artifact '{a.name}' ({a.size_in_bytes} bytes) to {dest_dir}")

            # If run_report.json exists in downloaded artifacts, show summary
            report_file = dest_dir / "run_report.json"
            if report_file.exists():
                data = json.loads(report_file.read_text(encoding="utf-8"))
                self.log_text.append(f"\n=== Structured Automation Report ===\n{json.dumps(data, indent=2)}")

            # If failure screenshot exists, display it
            failure_shots = list(dest_dir.glob("failure_*.png"))
            if failure_shots:
                pix = QPixmap(str(failure_shots[0]))
                self.failure_shot_label.setPixmap(pix.scaledToWidth(500, Qt.SmoothTransformation))
                self.failure_shot_label.setVisible(True)
                self.log_text.append(f"\nLoaded failure screenshot: {failure_shots[0].name}")
            else:
                self.failure_shot_label.setVisible(False)

        except Exception as e:
            self.log_text.append(f"\nFailed to retrieve artifacts: {e}")
