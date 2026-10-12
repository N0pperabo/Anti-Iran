"""Modern dark and light stylesheets for PySide6."""

DARK_THEME = """
QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #0d1117;
}

QTabWidget::pane {
    border: 1px solid #30363d;
    background-color: #161b22;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #0d1117;
    color: #8b949e;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #161b22;
    color: #58a6ff;
    border-bottom: 2px solid #58a6ff;
}

QTabBar::tab:hover:!selected {
    background-color: #21262d;
    color: #c9d1d9;
}

QGroupBox {
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: bold;
    color: #58a6ff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #0d1117;
    color: #f0f6fc;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #1f6feb;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #58a6ff;
}

QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}

QPushButton#primaryBtn {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #2ea043;
}

QPushButton#primaryBtn:hover {
    background-color: #2ea043;
}

QPushButton#primaryBtn:pressed {
    background-color: #238636;
}

QPushButton#dangerBtn {
    background-color: #da3633;
    color: #ffffff;
    border: 1px solid #f85149;
}

QPushButton#dangerBtn:hover {
    background-color: #f85149;
}

QTableWidget, QTreeWidget, QListWidget {
    background-color: #0d1117;
    alternate-background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    gridline-color: #21262d;
}

QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px;
    border: 1px solid #30363d;
    font-weight: bold;
}

QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}

QScrollBar:vertical {
    background: #0d1117;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #30363d;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #58a6ff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QProgressBar {
    border: 1px solid #30363d;
    border-radius: 6px;
    text-align: center;
    background-color: #161b22;
    color: #f0f6fc;
}

QProgressBar::chunk {
    background-color: #238636;
    border-radius: 5px;
}

QSplitter::handle {
    background-color: #30363d;
}
"""

LIGHT_THEME = """
QWidget {
    background-color: #f6f8fa;
    color: #24292f;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #ffffff;
}

QTabWidget::pane {
    border: 1px solid #d0d7de;
    background-color: #ffffff;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #f6f8fa;
    color: #57606a;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0969da;
    border-bottom: 2px solid #0969da;
}

QTabBar::tab:hover:!selected {
    background-color: #eaeef2;
}

QGroupBox {
    border: 1px solid #d0d7de;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: bold;
    color: #0969da;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #ffffff;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #0969da;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #0969da;
}

QPushButton {
    background-color: #f6f8fa;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #eaeef2;
    border-color: #8c959f;
}

QPushButton#primaryBtn {
    background-color: #1f883d;
    color: #ffffff;
    border: 1px solid #1a7f37;
}

QPushButton#primaryBtn:hover {
    background-color: #1a7f37;
}

QPushButton#dangerBtn {
    background-color: #cf222e;
    color: #ffffff;
    border: 1px solid #a40e26;
}

QTableWidget, QTreeWidget, QListWidget {
    background-color: #ffffff;
    alternate-background-color: #f6f8fa;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    gridline-color: #eaeef2;
}

QHeaderView::section {
    background-color: #f6f8fa;
    color: #57606a;
    padding: 8px;
    border: 1px solid #d0d7de;
    font-weight: bold;
}

QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #0969da;
    color: #ffffff;
}
"""
