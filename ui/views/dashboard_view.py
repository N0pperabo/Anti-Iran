"""Dashboard view presenting GitHub connection status, repository metrics, and quick actions."""

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from app.state_manager import ApplicationStateManager


class DashboardView(QWidget):
    """Main dashboard page."""

    navigate_requested = Signal(str)  # Tab name: 'browser', 'workflow', 'runs', 'settings'

    def __init__(self, state_mgr: ApplicationStateManager, parent=None):
        super().__init__(parent)
        self.state_mgr = state_mgr

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header Title
        title_box = QHBoxLayout()
        title_label = QLabel("GitHub Actions Browser Automation Studio")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #58a6ff;")
        title_box.addWidget(title_label)
        title_box.addStretch()

        self.refresh_btn = QPushButton("Refresh Status")
        self.refresh_btn.clicked.connect(self.update_status)
        title_box.addWidget(self.refresh_btn)
        layout.addLayout(title_box)

        # Status Cards Grid
        grid = QGridLayout()
        grid.setSpacing(16)

        # Card 1: GitHub Connection
        conn_group = QGroupBox("GitHub Actions Execution Plane")
        c_layout = QVBoxLayout(conn_group)
        self.status_badge = QLabel("● Checking Connection...")
        self.status_badge.setStyleSheet("font-size: 15px; font-weight: bold; color: #d29922;")
        c_layout.addWidget(self.status_badge)

        self.repo_label = QLabel("Repository: -")
        self.branch_label = QLabel("Branch: -")
        self.privacy_label = QLabel("Visibility: -")
        c_layout.addWidget(self.repo_label)
        c_layout.addWidget(self.branch_label)
        c_layout.addWidget(self.privacy_label)

        self.connect_btn = QPushButton("Test / Reconnect")
        self.connect_btn.clicked.connect(lambda: self.navigate_requested.emit("settings"))
        c_layout.addWidget(self.connect_btn)
        grid.addWidget(conn_group, 0, 0)

        # Card 2: Browser Session & State
        state_group = QGroupBox("Browser Session & Storage State")
        s_layout = QVBoxLayout(state_group)
        self.state_status_label = QLabel("Encrypted State: Checking...")
        self.state_key_label = QLabel("Encryption Key: Checking...")
        s_layout.addWidget(self.state_status_label)
        s_layout.addWidget(self.state_key_label)

        state_hint = QLabel("Session cookies & storage are encrypted using AES/Fernet and persisted in private repository.")
        state_hint.setWordWrap(True)
        state_hint.setStyleSheet("color: #8b949e; font-size: 11px;")
        s_layout.addWidget(state_hint)

        self.settings_key_btn = QPushButton("Manage Security & Key")
        self.settings_key_btn.clicked.connect(lambda: self.navigate_requested.emit("settings"))
        s_layout.addWidget(self.settings_key_btn)
        grid.addWidget(state_group, 0, 1)

        layout.addLayout(grid)

        # Card 3: Quick Navigation Actions
        actions_group = QGroupBox("Quick Launch")
        a_layout = QHBoxLayout(actions_group)

        self.quick_inspect_btn = QPushButton("Inspect Web Page")
        self.quick_inspect_btn.setObjectName("primaryBtn")
        self.quick_inspect_btn.clicked.connect(lambda: self.navigate_requested.emit("browser"))
        a_layout.addWidget(self.quick_inspect_btn)

        self.quick_workflow_btn = QPushButton("Edit Workflow")
        self.quick_workflow_btn.clicked.connect(lambda: self.navigate_requested.emit("workflow"))
        a_layout.addWidget(self.quick_workflow_btn)

        self.quick_runs_btn = QPushButton("View Run History")
        self.quick_runs_btn.clicked.connect(lambda: self.navigate_requested.emit("runs"))
        a_layout.addWidget(self.quick_runs_btn)

        layout.addWidget(actions_group)

        # Active Workflow Snapshot
        wf_group = QGroupBox("Active Workflow in Studio")
        wf_layout = QVBoxLayout(wf_group)
        self.wf_info_label = QLabel("Name: GitHub Search Demo | Target: https://github.com | Actions: 4")
        wf_layout.addWidget(self.wf_info_label)
        layout.addWidget(wf_group)

        layout.addStretch()

        self.update_status()

    def update_status(self):
        """Refreshes connection metrics and state information."""
        cfg = self.state_mgr.config
        self.repo_label.setText(f"Repository: {cfg.repo_owner}/{cfg.repo_name}" if cfg.repo_owner else "Repository: Not configured")
        self.branch_label.setText(f"Branch: {cfg.default_branch}")

        # Check validation
        validation = self.state_mgr.last_validation
        if not validation:
            validation = self.state_mgr.validate_connection()

        if validation and validation.valid:
            priv_badge = "Private (Secure)" if validation.is_private else "PUBLIC (Warning: not private)"
            self.status_badge.setText("● Connected to GitHub Actions")
            self.status_badge.setStyleSheet("font-size: 15px; font-weight: bold; color: #2ea043;")
            self.privacy_label.setText(f"Visibility: {priv_badge}")
        else:
            self.status_badge.setText("● Disconnected / Unconfigured")
            self.status_badge.setStyleSheet("font-size: 15px; font-weight: bold; color: #f85149;")
            self.privacy_label.setText(f"Status: {validation.message if validation else 'Not connected'}")

        # Check browser state file
        state_file = Path("state/browser_state.enc")
        if state_file.exists():
            size = state_file.stat().st_size
            self.state_status_label.setText(f"Encrypted State: Present ({size} bytes)")
        else:
            self.state_status_label.setText("Encrypted State: None (will be generated upon first run)")

        key = self.state_mgr.get_encryption_key()
        if key:
            self.state_key_label.setText("Encryption Key: Stored in OS Keyring")
        else:
            self.state_key_label.setText("Encryption Key: Not set (using unencrypted fallback)")

        # Update active workflow info
        wf = self.state_mgr.current_workflow
        self.wf_info_label.setText(f"Workflow: {wf.name} | Target: {wf.target_url} | Total Actions: {len(wf.actions)}")
