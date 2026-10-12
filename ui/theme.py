"""Refined modern dark and light stylesheets with generous padding, preventing box overlaps."""

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

/* Toolbars */
QToolBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 6px 12px;
    spacing: 8px;
}

/* Inputs & Form Controls */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #0d1117;
    color: #f0f6fc;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 20px;
    selection-background-color: #1f6feb;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #58a6ff;
}

/* Buttons */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    min-height: 20px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton:checked {
    background-color: #1f6feb;
    color: #ffffff;
    border-color: #58a6ff;
}

QPushButton#primaryBtn {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #2ea043;
}

QPushButton#primaryBtn:hover {
    background-color: #2ea043;
}

QPushButton#dangerBtn {
    background-color: #da3633;
    color: #ffffff;
    border: 1px solid #f85149;
}

QPushButton#dangerBtn:hover {
    background-color: #f85149;
}

/* GroupBox with plenty of margin to prevent title overlap */
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 24px;
    padding: 20px 14px 14px 14px;
    font-weight: bold;
    color: #58a6ff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 2px;
    padding: 0 6px;
    background-color: #0d1117;
}

/* Tables & Lists */
QTableWidget, QTreeWidget, QListWidget {
    background-color: #0d1117;
    alternate-background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    gridline-color: #21262d;
    padding: 2px;
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

/* ScrollBars */
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

QProgressBar {
    border: 1px solid #30363d;
    border-radius: 6px;
    text-align: center;
    background-color: #161b22;
    color: #f0f6fc;
    min-height: 18px;
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

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #d0d7de;
    padding: 6px 12px;
    spacing: 8px;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #ffffff;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 20px;
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
    min-height: 20px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #eaeef2;
    border-color: #8c959f;
}

QPushButton:checked {
    background-color: #0969da;
    color: #ffffff;
    border-color: #0969da;
}

QPushButton#primaryBtn {
    background-color: #1f883d;
    color: #ffffff;
    border: 1px solid #1a7f37;
}

QPushButton#dangerBtn {
    background-color: #cf222e;
    color: #ffffff;
    border: 1px solid #a40e26;
}

QGroupBox {
    border: 1px solid #d0d7de;
    border-radius: 8px;
    margin-top: 24px;
    padding: 20px 14px 14px 14px;
    font-weight: bold;
    color: #0969da;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 2px;
    padding: 0 6px;
    background-color: #ffffff;
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
