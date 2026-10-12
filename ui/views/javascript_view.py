"""JavaScript Viewer view displaying client-side script trees and syntax-highlighted sources."""

from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from app.state_manager import ApplicationStateManager
from models.inspect_bundle import JavaScriptResource
from ui.widgets.code_editor import CodeViewerWidget


class JavaScriptView(QWidget):
    """Page for browsing and inspecting client-side JavaScript sources."""

    def __init__(self, state_mgr: ApplicationStateManager, parent=None):
        super().__init__(parent)
        self.state_mgr = state_mgr
        self.scripts: List[JavaScriptResource] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("Client-Side JavaScript Resources (Extracted during inspection)"))
        header.addStretch()
        self.count_label = QLabel("0 Scripts")
        self.count_label.setStyleSheet("color: #8b949e; font-weight: bold;")
        header.addWidget(self.count_label)
        layout.addLayout(header)

        # Splitter: Tree List | Code Editor
        splitter = QSplitter(Qt.Horizontal)

        # Left: Search & Scripts List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter scripts by name or url...")
        self.search_input.textChanged.connect(self._filter_scripts)
        left_layout.addWidget(self.search_input)

        self.script_list = QListWidget()
        self.script_list.currentItemChanged.connect(self._on_script_selected)
        left_layout.addWidget(self.script_list)
        splitter.addWidget(left_widget)

        # Right: Code Viewer
        self.code_viewer = CodeViewerWidget()
        splitter.addWidget(self.code_viewer)

        splitter.setSizes([320, 680])
        layout.addWidget(splitter)

    def load_scripts_from_state(self):
        """Loads scripts from the current inspection bundle in state manager."""
        bundle = self.state_mgr.current_inspect_bundle
        if not bundle or not bundle.scripts:
            self.script_list.clear()
            self.code_viewer.set_code("// No scripts available.\n// Run Page Inspection in the Browser tab to extract client-side JavaScript.")
            self.count_label.setText("0 Scripts")
            return

        self.scripts = bundle.scripts
        self.count_label.setText(f"{len(self.scripts)} Scripts")
        self.script_list.clear()

        for s in self.scripts:
            prefix = "[Inline]" if s.is_inline else "[Ext]"
            size_str = f" ({s.size_bytes} B)" if s.size_bytes > 0 else ""
            item_text = f"{prefix} {s.name}{size_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, s)
            self.script_list.addItem(item)

        if self.script_list.count() > 0:
            self.script_list.setCurrentRow(0)

    def _on_script_selected(self, current: Optional[QListWidgetItem], previous):
        if not current:
            return
        script: JavaScriptResource = current.data(Qt.UserRole)
        header = f"// Script: {script.name}\n"
        if script.src:
            header += f"// Source URL: {script.src}\n"
        header += f"// Type: {script.script_type or 'text/javascript'}\n"
        header += f"// Size: {script.size_bytes} bytes\n\n"

        code = script.content or "// [Source not fetched inline - see Source URL above]"
        self.code_viewer.set_code(header + code)

    def _filter_scripts(self, query: str):
        query = query.lower().strip()
        for i in range(self.script_list.count()):
            item = self.script_list.item(i)
            s: JavaScriptResource = item.data(Qt.UserRole)
            matches = query in s.name.lower() or (s.src and query in s.src.lower())
            item.setHidden(not matches)
