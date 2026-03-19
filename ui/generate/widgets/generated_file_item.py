"""
Generated File Item Widget

Full-height G-code preview using the existing GCodeEditor (read-only).
"Edit" button opens the full dialog editor.
Border/background reflects sync state: grey → green → red.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QDialog
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from ...widgets.themed_widgets import ThemedLabel


# State colour palette
_STATES = {
    'empty':    {'border': '#6f779a', 'bg': '#282a36'},
    'synced':   {'border': '#23c87b', 'bg': '#1a2420'},
    'unsynced': {'border': '#ff4444', 'bg': '#241a1a'},
}


class GCodeEditDialog(QDialog):
    """Full G-code editor dialog (reuses GCodeEditor)"""

    def __init__(self, title, content, main_window=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit {title}")
        self.setModal(True)
        self.resize(800, 600)
        self.main_window = main_window

        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint |
                            Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint |
                            Qt.WindowCloseButtonHint)

        self.setStyleSheet("""
            GCodeEditDialog { background-color: #282a36; color: #ffffff; }
            QPushButton {
                background-color: #1d1f28; color: #23c87b;
                border: 2px solid #23c87b; border-radius: 4px;
                padding: 6px 12px; min-width: 80px;
            }
            QPushButton:hover { background-color: #000000; color: #1a945b; border: 2px solid #1a945b; }
            QPushButton:pressed { background-color: #23c87b; color: #1d1f28; }
            QPushButton#cancel_button { color: #BB86FC; border: 2px solid #BB86FC; }
            QPushButton#cancel_button:hover { color: #9965DA; border: 2px solid #9965DA; }
        """)

        self._setup_ui(content)

    def _setup_ui(self, content):
        from ...gcode_ide import GCodeEditor
        layout = QVBoxLayout(self)

        self.editor = GCodeEditor(self)
        if self.main_window:
            dollar_vars = self.main_window.get_dollar_variable()
            self.editor.set_dollar_variables_info(dollar_vars)
        self.editor.setPlainText(content)
        layout.addWidget(self.editor)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_button")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

    def get_content(self):
        return self.editor.toPlainText()


class GeneratedFileItem(QFrame):
    """Full-height G-code preview panel with state-based border/background"""

    content_changed = Signal(str)

    def __init__(self, name, file_type, side, main_window=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.file_type = file_type
        self.side = side
        self.main_window = main_window

        self.content = ""
        self.is_synced = True

        self._setup_ui()
        self._apply_state()

    # ── UI Setup ──────────────────────────────────────────────────────────

    def _setup_ui(self):
        from ...gcode_ide import GCodeEditor

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        layout.addLayout(header)

        self._title = ThemedLabel(self.name)
        self._title.setFont(QFont("Arial", 11, QFont.Bold))
        header.addWidget(self._title)
        header.addStretch()

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setFixedHeight(26)
        self._edit_btn.setCursor(Qt.PointingHandCursor)
        self._edit_btn.clicked.connect(self._open_editor)
        header.addWidget(self._edit_btn)

        # G-code preview using the real GCodeEditor in read-only mode
        self._preview = GCodeEditor(self)
        self._preview.setReadOnly(True)
        self._preview.setFont(QFont("Consolas", 10))
        self._preview.setPlaceholderText("No G-code generated yet — click Generate Files.")
        layout.addWidget(self._preview, 1)

    # ── Content Management ────────────────────────────────────────────────

    def update_content(self, content):
        self.content = content or ""
        self._preview.setPlainText(self.content)
        self._apply_state()

    def get_content(self):
        return self.content

    def has_content(self):
        return bool(self.content and self.content.strip())

    # ── Sync Status ───────────────────────────────────────────────────────

    def set_sync_status(self, is_synced):
        self.is_synced = is_synced
        self._apply_state()

    def _state_key(self):
        if not self.has_content():
            return 'empty'
        return 'synced' if self.is_synced else 'unsynced'

    def _apply_state(self):
        p = _STATES[self._state_key()]
        border = p['border']
        bg = p['bg']

        self.setStyleSheet(f"""
            GeneratedFileItem {{
                background-color: {bg};
                border: 3px solid {border};
                border-radius: 6px;
            }}
        """)

        self._edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {border};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 2px 10px;
                font-size: 9px;
            }}
            QPushButton:hover {{
                background-color: {border};
                color: #1d1f28;
            }}
        """)

    # ── Editor ────────────────────────────────────────────────────────────

    def _open_editor(self):
        dialog = GCodeEditDialog(
            f"{self.side.title()} {self.name}",
            self.content,
            self.main_window,
            self
        )
        if dialog.exec_() == QDialog.Accepted:
            new_content = dialog.get_content()
            self.content = new_content
            self._preview.setPlainText(new_content)
            self._apply_state()
            self.content_changed.emit(new_content)
