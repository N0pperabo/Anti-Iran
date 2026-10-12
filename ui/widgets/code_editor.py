"""Code editor and viewer widget with syntax highlighting, line numbers, search, and copy."""

import re
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SimpleSyntaxHighlighter(QSyntaxHighlighter):
    """Basic syntax highlighter for JavaScript, HTML, and JSON."""

    def __init__(self, parent: QTextDocument):
        super().__init__(parent)
        self.highlighting_rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#ff7b72"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "break", "case", "catch", "class", "const", "continue", "debugger", "default",
            "delete", "do", "else", "export", "extends", "finally", "for", "function",
            "if", "import", "in", "instanceof", "new", "return", "super", "switch",
            "this", "throw", "try", "typeof", "var", "void", "while", "with", "yield",
            "async", "await", "let", "true", "false", "null", "undefined"
        ]
        for word in keywords:
            pattern = re.compile(rf"\b{word}\b")
            self.highlighting_rules.append((pattern, keyword_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#a5d6ff"))
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
        self.highlighting_rules.append((re.compile(r"`[^`\\]*(\\.[^`\\]*)*`"), string_format))

        # Numbers
        num_format = QTextCharFormat()
        num_format.setForeground(QColor("#79c0ff"))
        self.highlighting_rules.append((re.compile(r"\b[0-9]+(\.[0-9]+)?\b"), num_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#8b949e"))
        self.highlighting_rules.append((re.compile(r"//[^\n]*"), comment_format))

    def highlightBlock(self, text: str):
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


class LineNumberArea(QWidget):
    """Left gutter widget displaying line numbers."""

    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """Text editor with line numbering and monospaced font."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        font = QFont("Consolas, 'Courier New', monospace", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)

        self.highlighter = SimpleSyntaxHighlighter(self.document())

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(self.blockCount())))
        space = 14 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#161b22"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        painter.setPen(QColor("#484f58"))
        painter.setFont(self.font())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0, top, self.line_number_area.width() - 6, self.fontMetrics().height(),
                    Qt.AlignRight, number
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


class CodeViewerWidget(QWidget):
    """Complete code viewer container with toolbar, search, and copy controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in code...")
        self.search_input.textChanged.connect(self.search_text)
        toolbar.addWidget(self.search_input)

        self.copy_btn = QPushButton("Copy Source")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        toolbar.addWidget(self.copy_btn)

        layout.addLayout(toolbar)

        self.editor = CodeEditor()
        self.editor.setReadOnly(True)
        layout.addWidget(self.editor)

    def set_code(self, code_str: str):
        self.editor.setPlainText(code_str)

    def copy_to_clipboard(self):
        text = self.editor.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.copy_btn.setText("Copied!")
            self.copy_btn.setEnabled(False)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: (self.copy_btn.setText("Copy Source"), self.copy_btn.setEnabled(True)))

    def search_text(self, query: str):
        if not query:
            return
        cursor = self.editor.textCursor()
        document = self.editor.document()
        found_cursor = document.find(query, cursor)
        if not found_cursor.isNull():
            self.editor.setTextCursor(found_cursor)
        else:
            # Wrap search from top
            found_cursor = document.find(query, 0)
            if not found_cursor.isNull():
                self.editor.setTextCursor(found_cursor)
