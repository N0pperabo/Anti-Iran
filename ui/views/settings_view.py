"""Settings view for configuring GitHub credentials, repository information, security keys, and UI theme."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from app.state_manager import ApplicationStateManager
from automation.state import generate_encryption_key


class SettingsView(QWidget):
    """Configuration management page."""

    theme_changed = Signal(str)  # 'dark' or 'light'
    connection_changed = Signal()

    def __init__(self, state_mgr: ApplicationStateManager, parent=None):
        super().__init__(parent)
        self.state_mgr = state_mgr

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # 1. GitHub Connection Settings
        gh_group = QGroupBox("GitHub Actions Integration")
        gh_form = QFormLayout(gh_group)

        self.username_input = QLineEdit()
        self.username_input.setText(self.state_mgr.config.github_username)
        self.username_input.setPlaceholderText("e.g. octocat")
        gh_form.addRow("GitHub Username:", self.username_input)

        self.owner_input = QLineEdit()
        self.owner_input.setText(self.state_mgr.config.repo_owner)
        self.owner_input.setPlaceholderText("e.g. octocat or organization-name")
        gh_form.addRow("Repository Owner:", self.owner_input)

        self.repo_input = QLineEdit()
        self.repo_input.setText(self.state_mgr.config.repo_name)
        self.repo_input.setPlaceholderText("e.g. my-private-automation-repo")
        gh_form.addRow("Repository Name:", self.repo_input)

        self.branch_input = QLineEdit()
        self.branch_input.setText(self.state_mgr.config.default_branch)
        self.branch_input.setPlaceholderText("main")
        gh_form.addRow("Default Branch:", self.branch_input)

        # Token input with show/hide toggle
        token_row = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setPlaceholderText("ghp_... (stored securely in OS Keyring, never committed)")
        existing_token = self.state_mgr.get_token()
        if existing_token:
            self.token_input.setText(existing_token)
        token_row.addWidget(self.token_input)

        self.toggle_token_btn = QPushButton("Show")
        self.toggle_token_btn.clicked.connect(self._toggle_token_visibility)
        token_row.addWidget(self.toggle_token_btn)
        gh_form.addRow("Personal Access Token:", token_row)

        gh_btn_row = QHBoxLayout()
        self.test_conn_btn = QPushButton("Test Connection")
        self.test_conn_btn.clicked.connect(self._test_connection)
        gh_btn_row.addWidget(self.test_conn_btn)
        gh_btn_row.addStretch()
        gh_form.addRow("", gh_btn_row)

        layout.addWidget(gh_group)

        # 2. Browser State Security Settings
        sec_group = QGroupBox("Browser Session Encryption (Security)")
        sec_form = QFormLayout(sec_group)

        key_row = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText("Fernet AES key (stored in OS Keyring)")
        existing_key = self.state_mgr.get_encryption_key()
        if existing_key:
            self.key_input.setText(existing_key)
        key_row.addWidget(self.key_input)

        self.toggle_key_btn = QPushButton("Show")
        self.toggle_key_btn.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self.toggle_key_btn)

        self.gen_key_btn = QPushButton("Generate New Key")
        self.gen_key_btn.clicked.connect(self._generate_key)
        key_row.addWidget(self.gen_key_btn)
        sec_form.addRow("State Encryption Key:", key_row)

        sec_note = QLabel(
            "Important: Copy this key to your private repository's GitHub Action Secrets as 'BROWSER_STATE_KEY' "
            "so the runner can decrypt and persist sessions."
        )
        sec_note.setWordWrap(True)
        sec_note.setStyleSheet("color: #8b949e; font-size: 11px;")
        sec_form.addRow("", sec_note)

        layout.addWidget(sec_group)

        # 3. UI Preferences
        ui_group = QGroupBox("Preferences")
        ui_form = QFormLayout(ui_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark Theme", "dark")
        self.theme_combo.addItem("Light Theme", "light")
        current_theme_idx = 0 if self.state_mgr.config.theme == "dark" else 1
        self.theme_combo.setCurrentIndex(current_theme_idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        ui_form.addRow("Color Theme:", self.theme_combo)

        layout.addWidget(ui_group)

        # Save Button
        save_btn_row = QHBoxLayout()
        save_btn_row.addStretch()
        self.save_all_btn = QPushButton("Save Settings")
        self.save_all_btn.setObjectName("primaryBtn")
        self.save_all_btn.clicked.connect(self._save_settings)
        save_btn_row.addWidget(self.save_all_btn)
        layout.addLayout(save_btn_row)

        layout.addStretch()

    def _toggle_token_visibility(self):
        if self.token_input.echoMode() == QLineEdit.Password:
            self.token_input.setEchoMode(QLineEdit.Normal)
            self.toggle_token_btn.setText("Hide")
        else:
            self.token_input.setEchoMode(QLineEdit.Password)
            self.toggle_token_btn.setText("Show")

    def _toggle_key_visibility(self):
        if self.key_input.echoMode() == QLineEdit.Password:
            self.key_input.setEchoMode(QLineEdit.Normal)
            self.toggle_key_btn.setText("Hide")
        else:
            self.key_input.setEchoMode(QLineEdit.Password)
            self.toggle_key_btn.setText("Show")

    def _generate_key(self):
        new_key = generate_encryption_key()
        self.key_input.setText(new_key)
        self.key_input.setEchoMode(QLineEdit.Normal)
        self.toggle_key_btn.setText("Hide")
        QMessageBox.information(
            self,
            "New Encryption Key",
            f"Generated new Fernet key:\n\n{new_key}\n\nMake sure to add this secret as 'BROWSER_STATE_KEY' in your GitHub Repository Secrets!",
        )

    def _test_connection(self):
        self._save_settings(silent=True)
        res = self.state_mgr.validate_connection()
        if res.valid:
            QMessageBox.information(
                self,
                "Connection Successful",
                f"Successfully connected to GitHub!\n\nRepository: {res.owner}/{res.repo}\nPrivate: {res.is_private}\nBranch: {res.default_branch}\nWorkflows detected: {res.has_workflows}",
            )
        else:
            QMessageBox.critical(
                self,
                "Connection Failed",
                f"Could not connect to GitHub repository:\n\n{res.message}",
            )
        self.connection_changed.emit()

    def _on_theme_changed(self):
        theme = self.theme_combo.currentData()
        self.state_mgr.config.theme = theme
        self.state_mgr.config.save()
        self.theme_changed.emit(theme)

    def _save_settings(self, silent: bool = False):
        cfg = self.state_mgr.config
        cfg.github_username = self.username_input.text().strip()
        cfg.repo_owner = self.owner_input.text().strip()
        cfg.repo_name = self.repo_input.text().strip()
        cfg.default_branch = self.branch_input.text().strip() or "main"
        cfg.save()

        token = self.token_input.text().strip()
        if token:
            self.state_mgr.set_token(token)

        key = self.key_input.text().strip()
        if key:
            self.state_mgr.set_encryption_key(key)

        self.connection_changed.emit()
        if not silent:
            QMessageBox.information(self, "Saved", "Settings saved successfully.")
