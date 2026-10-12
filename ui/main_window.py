"""Main application window hosting the full-screen interactive studio workspace."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from app.state_manager import ApplicationStateManager
from ui.theme import DARK_THEME, LIGHT_THEME
from ui.views.studio_view import StudioView


class MainWindow(QMainWindow):
    """Primary desktop studio window for browser automation."""

    def __init__(self, state_mgr: ApplicationStateManager):
        super().__init__()
        self.state_mgr = state_mgr

        self.setWindowTitle("GitHub Actions Browser Automation Studio")
        self.resize(1360, 880)
        self.setMinimumSize(1024, 680)

        # Central Studio Workspace
        self.studio_view = StudioView(self.state_mgr, parent=self)
        self.setCentralWidget(self.studio_view)

        # Bottom Sleek Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("background-color: #161b22; color: #8b949e; border-top: 1px solid #30363d; font-size: 11px;")
        self.status_bar.showMessage(
            f"Connected to: {self.state_mgr.config.repo_owner}/{self.state_mgr.config.repo_name} ({self.state_mgr.config.default_branch}) | Interactive Chromium Engine Active"
        )

        # Keyboard shortcuts
        self.f11_shortcut = QShortcut(QKeySequence("F11"), self)
        self.f11_shortcut.activated.connect(self._toggle_fullscreen)

        # Apply dark theme
        self._apply_theme(self.state_mgr.config.theme)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _apply_theme(self, theme_name: str):
        app = QApplication.instance()
        if app:
            qss = DARK_THEME if theme_name == "dark" else LIGHT_THEME
            app.setStyleSheet(qss)
