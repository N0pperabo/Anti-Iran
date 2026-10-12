"""Spacious and clean settings modal dialog."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from app.state_manager import ApplicationStateManager
from automation.state import generate_encryption_key


class SettingsDialog(QDialog):
    """Spacious configuration modal for GitHub tokens, repository, and encryption keys."""

    settings_saved = Signal()

    def __init__(self, state_mgr: ApplicationStateManager, parent=None):
        super().__init__(parent)
        self.state_mgr = state_mgr
        self.setWindowTitle("Studio Settings & GitHub Configuration")
        self.setMinimumWidth(580)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # 1. GitHub Configuration Group
        gh_group = QGroupBox("GitHub Actions Integration")
        gh_group.setStyleSheet("QGroupBox { font-size: 14px; font-weight: bold; padding-top: 22px; margin-top: 10px; }")
        gh_form = QFormLayout(gh_group)
        gh_form.setVerticalSpacing(12)
        gh_form.setHorizontalSpacing(16)

        self.username_input = QLineEdit(self.state_mgr.config.github_username)
        self.username_input.setPlaceholderText("e.g. N0pperabo")
        gh_form.addRow("GitHub Username:", self.username_input)

        self.owner_input = QLineEdit(self.state_mgr.config.repo_owner)
        self.owner_input.setPlaceholderText("e.g. N0pperabo")
        gh_form.addRow("Repository Owner:", self.owner_input)

        self.repo_input = QLineEdit(self.state_mgr.config.repo_name)
        self.repo_input.setPlaceholderText("e.g. Anti-Iran-Privet")
        gh_form.addRow("Repository Name:", self.repo_input)

        self.branch_input = QLineEdit(self.state_mgr.config.default_branch)
        self.branch_input.setPlaceholderText("main")
        gh_form.addRow("Default Branch:", self.branch_input)

        # Token row
        token_row = QHBoxLayout()
        token_row.setSpacing(8)
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setPlaceholderText("ghp_... (stored securely in Windows Keyring)")
        stored_tok = self.state_mgr.get_token()
        if stored_tok:
            self.token_input.setText(stored_tok)
        token_row.addWidget(self.token_input)

        self.toggle_tok_btn = QPushButton("Show")
        self.toggle_tok_btn.clicked.connect(self._toggle_tok)
        token_row.addWidget(self.toggle_tok_btn)
        gh_form.addRow("Personal Access Token:", token_row)

        test_row = QHBoxLayout()
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self._test_connection)
        test_row.addWidget(self.test_btn)
        test_row.addStretch()
        gh_form.addRow("", test_row)

        layout.addWidget(gh_group)

        # 2. Browser State Security Group
        sec_group = QGroupBox("Browser Session Encryption")
        sec_group.setStyleSheet("QGroupBox { font-size: 14px; font-weight: bold; padding-top: 22px; margin-top: 10px; }")
        sec_form = QFormLayout(sec_group)
        sec_form.setVerticalSpacing(12)
        sec_form.setHorizontalSpacing(16)

        key_row = QHBoxLayout()
        key_row.setSpacing(8)
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText("Fernet AES encryption key")
        stored_key = self.state_mgr.get_encryption_key()
        if stored_key:
            self.key_input.setText(stored_key)
        key_row.addWidget(self.key_input)

        self.toggle_key_btn = QPushButton("Show")
        self.toggle_key_btn.clicked.connect(self._toggle_key)
        key_row.addWidget(self.toggle_key_btn)

        self.gen_key_btn = QPushButton("Generate Key")
        self.gen_key_btn.clicked.connect(self._generate_key)
        key_row.addWidget(self.gen_key_btn)
        sec_form.addRow("State Encryption Key:", key_row)

        note_lbl = QLabel("Must match 'BROWSER_STATE_KEY' secret in your GitHub repository.")
        note_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        sec_form.addRow("", note_lbl)

        layout.addWidget(sec_group)

        # Bottom Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.close_btn = QPushButton("Cancel")
        self.close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.close_btn)

        self.save_btn = QPushButton("Save & Apply")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.setStyleSheet("font-weight: bold; padding: 10px 24px;")
        self.save_btn.clicked.connect(self._save_and_close)
        btn_row.addWidget(self.save_btn)

        layout.addLayout(btn_row)

    def _toggle_tok(self):
        if self.token_input.echoMode() == QLineEdit.Password:
            self.token_input.setEchoMode(QLineEdit.Normal)
            self.toggle_tok_btn.setText("Hide")
        else:
            self.token_input.setEchoMode(QLineEdit.Password)
            self.toggle_tok_btn.setText("Show")

    def _toggle_key(self):
        if self.key_input.echoMode() == QLineEdit.Password:
            self.key_input.setEchoMode(QLineEdit.Normal)
            self.toggle_key_btn.setText("Hide")
        else:
            self.key_input.setEchoMode(QLineEdit.Password)
            self.toggle_key_btn.setText("Show")

    def _generate_key(self):
        new_k = generate_encryption_key()
        self.key_input.setText(new_k)
        self.key_input.setEchoMode(QLineEdit.Normal)
        self.toggle_key_btn.setText("Hide")

    def _test_connection(self):
        self._save_state()
        res = self.state_mgr.validate_connection()
        if res.valid:
            QMessageBox.information(
                self,
                "Connection Successful",
                f"Connected to GitHub!\n\nRepo: {res.owner}/{res.repo}\nPrivate: {res.is_private}\nBranch: {res.default_branch}",
            )
        else:
            QMessageBox.critical(self, "Connection Failed", f"Could not connect: {res.message}")

    def _save_state(self):
        cfg = self.state_mgr.config
        cfg.github_username = self.username_input.text().strip()
        cfg.repo_owner = self.owner_input.text().strip()
        cfg.repo_name = self.repo_input.text().strip()
        cfg.default_branch = self.branch_input.text().strip() or "main"
        cfg.save()

        tok = self.token_input.text().strip()
        if tok:
            self.state_mgr.set_token(tok)

        key = self.key_input.text().strip()
        if key:
            self.state_mgr.set_encryption_key(key)

    def _save_and_close(self):
        self._save_state()
        self.settings_saved.emit()
        self.accept()
