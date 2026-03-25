"""
G-Code Editor

LinuxCNC-aware G-code editor with syntax highlighting, line numbers,
error indication, and Python template variable support ({var:default}, {$var}).
"""

from PySide6.QtWidgets import (QPlainTextEdit, QWidget, QTextEdit, QToolTip, QPushButton)
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCursor, QPainter, QPalette, QTextCharFormat, QTextFormat
from PySide6.QtCore import QSize, Qt, QRect, Signal, QTimer
import re
from ..dialogs.dollar_variables_dialog import DollarVariablesDialog


# ── LinuxCNC G-code reference tables ──────────────────────────────────────────

# Motion group
_G_RAPID       = {'0'}
_G_LINEAR      = {'1'}
_G_ARC         = {'2', '3'}

# Threading / probing / splines
_G_SPECIAL     = {'5', '5.1', '5.2', '5.3',
                  '33', '33.1',
                  '38.2', '38.3', '38.4', '38.5',
                  '73', '76'}

# Canned cycles (drilling / boring / tapping)
_G_CANNED      = {'80', '81', '82', '83', '84', '85',
                  '86', '87', '88', '89', '74'}

# Tool compensation / length offsets
_G_TOOL_COMP   = {'40', '41', '41.1', '42', '42.1',
                  '43', '43.1', '43.2', '49', '70', '71',
                  '71.1', '71.2', '72', '72.1', '72.2'}

# Coordinate systems and offsets
_G_COORD       = {'10', '52', '53', '54', '55', '56', '57', '58', '59',
                  '59.1', '59.2', '59.3',
                  '28', '28.1', '30', '30.1',
                  '92', '92.1', '92.2', '92.3'}

# Modal: plane, units, distance mode, feed mode, spindle mode, path mode, dwell
_G_MODAL       = {'17', '17.1', '18', '18.1', '19', '19.1',
                  '20', '21',
                  '61', '61.1', '64',
                  '7', '8',
                  '90', '90.1', '91', '91.1',
                  '93', '94', '96', '97', '98', '99',
                  '4'}

# M-code groups
_M_STOP        = {'0', '1', '2', '30', '60'}
_M_SPINDLE     = {'3', '4', '5', '19'}
_M_COOLANT     = {'7', '8', '9'}
_M_TOOL        = {'6', '61'}
_M_IO          = {'62', '63', '64', '65', '66', '67', '68'}
_M_OVERRIDE    = {'48', '49', '50', '51', '52', '53'}
_M_SAVE        = {'70', '71', '72', '73'}
_M_SUBPROGRAM  = {'98', '99'}
_M_USER        = {'100', '101', '102', '110'}

# O-word keywords (flow control and subroutines)
_O_KEYWORDS    = {'sub', 'endsub', 'call', 'return',
                  'if', 'else', 'elseif', 'endif',
                  'while', 'endwhile', 'do', 'break', 'continue',
                  'repeat', 'endrepeat'}


class GCodeSyntaxHighlighter(QSyntaxHighlighter):
    """LinuxCNC G-code syntax highlighter with Python template variable validation."""

    def __init__(self, document, dollar_variables_info=None):
        super().__init__(document)
        self.dollar_variables_info = dollar_variables_info or {}

        font = QFont('Consolas', 18)
        font.setFixedPitch(True)

        def _fmt(color, bg=None):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bg:
                f.setBackground(QColor(bg))
            f.setFont(font)
            return f

        # Base format applied to every line so unrecognised chars share the font
        self.base_format = _fmt('#bec3c9')

        # Template variables  {var_name:default}  and  {$variable}
        self.variable_format       = _fmt('#ff8c00')              # orange
        self.valid_dollar_format   = _fmt('#23c87b')              # green – valid $var
        self.invalid_dollar_format = _fmt('#ff4a7c', '#2d1f1f')   # red + dark-red bg

        # Motion G-codes
        self.g_rapid_format   = _fmt('#d15e43')   # red-orange  – G0
        self.g_linear_format  = _fmt('#286c34')   # dark green  – G1
        self.g_arc_format     = _fmt('#00b4c8')   # cyan        – G2 / G3

        # Other G-code categories
        self.g_special_format  = _fmt('#bb9af7')  # lavender    – threading, probing, splines
        self.g_canned_format   = _fmt('#e0af68')  # amber       – canned cycles
        self.g_tool_format     = _fmt('#9ece6a')  # lime        – tool comp / length
        self.g_coord_format    = _fmt('#7dcfff')  # sky blue    – coord systems
        self.g_modal_format    = _fmt('#5e9955')  # mid green   – modal words
        self.g_unknown_format  = _fmt('#bec3c9')  # default     – unrecognised G

        # M-code categories
        self.m_stop_format     = _fmt('#f7768e')  # red         – stop / end
        self.m_spindle_format  = _fmt('#ff9e64')  # orange      – spindle
        self.m_coolant_format  = _fmt('#2ac3de')  # teal        – coolant
        self.m_tool_format     = _fmt('#9ece6a')  # lime        – tool change
        self.m_io_format       = _fmt('#bb9af7')  # lavender    – I/O
        self.m_override_format = _fmt('#7dcfff')  # sky blue    – overrides
        self.m_save_format     = _fmt('#c0caf5')  # light blue  – save/restore modal
        self.m_sub_format      = _fmt('#e0af68')  # amber       – M98/M99
        self.m_user_format     = _fmt('#a9b1d6')  # muted blue  – user M-codes
        self.m_unknown_format  = _fmt('#bec3c9')

        # Axis words
        self.x_format = _fmt('#c8b723')  # yellow
        self.y_format = _fmt('#009ccb')  # blue
        self.z_format = _fmt('#ff4a7c')  # pink
        self.a_format = _fmt('#f5a623')  # amber  – rotary A
        self.b_format = _fmt('#e8834a')  # coral  – rotary B
        self.c_format = _fmt('#d4694f')  # brick  – rotary C
        self.u_format = _fmt('#5bc8af')  # mint   – secondary U
        self.v_format = _fmt('#4db8c8')  # teal   – secondary V
        self.w_format = _fmt('#3aa8b8')  # steel  – secondary W

        # Feed / speed / tool / misc words
        self.f_format = _fmt('#e66c00')  # orange  – F feed
        self.s_format = _fmt('#e66c00')  # orange  – S spindle speed
        self.t_format = _fmt('#bb9af7')  # lavender – T tool number
        self.d_format = _fmt('#9ece6a')  # lime    – D tool radius offset
        self.h_format = _fmt('#7dcfff')  # sky     – H tool length offset
        self.p_format = _fmt('#a9b1d6')  # muted   – P parameter
        self.q_format = _fmt('#a9b1d6')  # muted   – Q parameter
        self.k_format = _fmt('#059669')  # emerald – K arc offset
        self.i_format = _fmt('#dc2626')  # red     – I arc offset
        self.j_format = _fmt('#059669')  # emerald – J arc offset
        self.r_format = _fmt('#6320a1')  # purple  – R radius
        self.l_format = _fmt('#BB86FC')  # violet  – L repeat count
        self.n_format = _fmt('#8A817C')  # gray    – N line number
        self.e_format = _fmt('#a9b1d6')  # muted   – E thread pitch

        # LinuxCNC-specific
        self.hash_param_format = _fmt("#b975d4")  # light blue – #5 / #<name>
        self.o_word_format     = _fmt('#ff9e64')  # orange     – o100 sub/call/if…

        # Comments and delimiters
        self.comment_format = _fmt('#636d83')   # dim gray – (…) and ;
        self.percent_format = _fmt('#636d83')   # dim gray – % program delimiter

    # ── Public API ────────────────────────────────────────────────────────────

    def update_dollar_variables(self, dollar_variables_info):
        """Refresh the set of known $variables and re-highlight."""
        self.dollar_variables_info = dollar_variables_info
        self.rehighlight()

    # ── Core highlighting ─────────────────────────────────────────────────────

    def highlightBlock(self, text):
        """Parse and highlight one line of LinuxCNC G-code."""
        length = len(text)

        # Stamp the base format across the whole line first so every character –
        # including unrecognised ones – shares the same font size.
        self.setFormat(0, length, self.base_format)

        i = 0
        while i < length:
            ch = text[i]

            # ── Whitespace ────────────────────────────────────────────────
            if ch.isspace():
                i += 1
                continue

            # ── Percent delimiter (program start/end) ─────────────────────
            if ch == '%':
                self.setFormat(i, 1, self.percent_format)
                i += 1
                continue

            # ── Parenthesis comment  ( … ) ────────────────────────────────
            if ch == '(':
                end = text.find(')', i)
                span = (end - i + 1) if end != -1 else (length - i)
                self.setFormat(i, span, self.comment_format)
                i += span
                continue

            # ── Semicolon comment  ; … ────────────────────────────────────
            if ch == ';':
                self.setFormat(i, length - i, self.comment_format)
                break

            # ── Python template variables  { … } ─────────────────────────
            if ch == '{':
                start = i
                i += 1
                var_content = ''
                while i < length and text[i] != '}':
                    var_content += text[i]
                    i += 1
                if i < length:
                    i += 1  # consume '}'
                var_name = var_content.split(':')[0].strip()
                if var_name.startswith('$'):
                    dollar_key = var_name[1:]
                    if dollar_key in self.dollar_variables_info:
                        self.setFormat(start, i - start, self.valid_dollar_format)
                    else:
                        self.setFormat(start, i - start, self.invalid_dollar_format)
                else:
                    self.setFormat(start, i - start, self.variable_format)
                continue

            # ── LinuxCNC named parameters  #5  #<name>  #[expr] ──────────
            if ch == '#':
                start = i
                i += 1
                if i < length and text[i] == '<':
                    i += 1
                    while i < length and text[i] != '>':
                        i += 1
                    if i < length:
                        i += 1
                elif i < length and text[i] == '[':
                    depth = 0
                    while i < length:
                        if text[i] == '[':
                            depth += 1
                        elif text[i] == ']':
                            depth -= 1
                            if depth == 0:
                                i += 1
                                break
                        i += 1
                else:
                    while i < length and text[i].isdigit():
                        i += 1
                self.setFormat(start, i - start, self.hash_param_format)
                continue

            # ── O-words  o100 sub  /  o<n> call ──────────────────────────
            if ch in 'oO':
                start = i
                i += 1
                if i < length and text[i] == '<':
                    while i < length and text[i] != '>':
                        i += 1
                    if i < length:
                        i += 1
                else:
                    while i < length and text[i].isdigit():
                        i += 1
                # Skip whitespace then read keyword
                while i < length and text[i].isspace():
                    i += 1
                kw_start = i
                while i < length and text[i].isalpha():
                    i += 1
                keyword = text[kw_start:i].lower()
                if keyword in _O_KEYWORDS:
                    self.setFormat(start, i - start, self.o_word_format)
                else:
                    # Unknown o-word – highlight only the o+number part
                    self.setFormat(start, kw_start - start, self.o_word_format)
                    i = kw_start  # re-parse the non-keyword text
                continue

            # ── Letter words ──────────────────────────────────────────────
            if ch.isalpha():
                letter_start = i
                letter = ch.upper()
                i += 1

                # Skip whitespace between letter and value
                while i < length and text[i].isspace():
                    i += 1

                # L only takes plain integers (L1, L24)
                if letter == 'L':
                    value_start = i
                    while i < length and text[i].isdigit():
                        i += 1
                    if i > value_start:
                        self.setFormat(letter_start, i - letter_start, self.l_format)
                    continue

                # All other words: collect a complex value expression
                value_start = i
                i = self._consume_value(text, i)
                total = i - letter_start

                if total > 1:
                    fmt = self._word_format(letter, text[value_start:i].strip())
                    if fmt:
                        self.setFormat(letter_start, total, fmt)
                continue

            # ── Skip anything else ────────────────────────────────────────
            i += 1

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _consume_value(self, text, i):
        """Advance i past a word's value: number, expression, or parameter ref."""
        length = len(text)
        while i < length:
            c = text[i]
            if c.isdigit() or c in '+-*/.':
                i += 1
            elif c == '[':
                # LinuxCNC expression block [...]
                depth = 0
                while i < length:
                    if text[i] == '[':
                        depth += 1
                    elif text[i] == ']':
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
            elif c == '{':
                # Embedded template variable
                close = self._find_closing_brace(text, i)
                i = (close + 1) if close != -1 else (i + 1)
            elif c == '#':
                # Embedded parameter reference
                i += 1
                if i < length and text[i] == '<':
                    while i < length and text[i] != '>':
                        i += 1
                    if i < length:
                        i += 1
                else:
                    while i < length and text[i].isdigit():
                        i += 1
            else:
                break
        return i

    def _word_format(self, letter, value_str):
        """Return the QTextCharFormat for a given word letter and its value."""
        if letter == 'G':
            return self._g_format(value_str)
        if letter == 'M':
            return self._m_format(value_str)
        return {
            'X': self.x_format, 'Y': self.y_format, 'Z': self.z_format,
            'A': self.a_format, 'B': self.b_format, 'C': self.c_format,
            'U': self.u_format, 'V': self.v_format, 'W': self.w_format,
            'I': self.i_format, 'J': self.j_format, 'K': self.k_format,
            'R': self.r_format, 'F': self.f_format, 'S': self.s_format,
            'T': self.t_format, 'D': self.d_format, 'H': self.h_format,
            'P': self.p_format, 'Q': self.q_format, 'E': self.e_format,
            'N': self.n_format,
        }.get(letter)

    def _g_format(self, value_str):
        """Pick a colour based on the numeric G-code value."""
        v = value_str.lstrip('0') or '0'
        if v in _G_RAPID:      return self.g_rapid_format
        if v in _G_LINEAR:     return self.g_linear_format
        if v in _G_ARC:        return self.g_arc_format
        if v in _G_SPECIAL:    return self.g_special_format
        if v in _G_CANNED:     return self.g_canned_format
        if v in _G_TOOL_COMP:  return self.g_tool_format
        if v in _G_COORD:      return self.g_coord_format
        if v in _G_MODAL:      return self.g_modal_format
        return self.g_unknown_format

    def _m_format(self, value_str):
        """Pick a colour based on the numeric M-code value."""
        v = value_str.lstrip('0') or '0'
        if v in _M_STOP:       return self.m_stop_format
        if v in _M_SPINDLE:    return self.m_spindle_format
        if v in _M_COOLANT:    return self.m_coolant_format
        if v in _M_TOOL:       return self.m_tool_format
        if v in _M_IO:         return self.m_io_format
        if v in _M_OVERRIDE:   return self.m_override_format
        if v in _M_SAVE:       return self.m_save_format
        if v in _M_SUBPROGRAM: return self.m_sub_format
        if v in _M_USER:       return self.m_user_format
        return self.m_unknown_format

    def _find_closing_brace(self, text, start):
        """Return the index of the '}' matching the '{' at start, or -1."""
        i = start + 1
        while i < len(text):
            if text[i] == '}':
                return i
            i += 1
        return -1


class LineNumberArea(QWidget):
    """Line number gutter with click-to-show error tooltips."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setMouseTracking(True)
        self.clickedLineNumber = None

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

    def mousePressEvent(self, event):
        """Show error tooltip when clicking on a flagged line number."""
        if event.button() != Qt.LeftButton:
            return

        block = self.editor.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.pos().y():
            if block.isVisible() and bottom >= event.pos().y():
                lineNumber = blockNumber + 1
                if lineNumber in self.editor.errors:
                    if self.clickedLineNumber == lineNumber:
                        self.clickedLineNumber = None
                        QToolTip.hideText()
                    else:
                        self.clickedLineNumber = lineNumber
                        errors = self.editor.errors[lineNumber]
                        tooltip_text = "\n".join(
                            [f"- {trigger} : {message}" for message, trigger, _ in errors]
                        )
                        QToolTip.showText(event.globalPos(), tooltip_text, self)
                else:
                    self.clickedLineNumber = None
                    QToolTip.hideText()
                break

            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            blockNumber += 1


class GCodeEditor(QPlainTextEdit):
    """
    LinuxCNC G-code editor.

    Highlights:
      - G/M-codes grouped by function (motion, canned cycles, coord systems …)
      - All 9 axes: X Y Z A B C U V W
      - LinuxCNC parameters: #5, #<name>, #[expr]
      - O-words: o100 sub / call / if / while …
      - Python template variables: {VAR:default}, {$variable}
      - Both comment styles: (…) and ;
    """

    variables_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.module = parent
        self.lineNumberArea = LineNumberArea(self)
        self.errors = {}
        self.variables = []
        self.selected_text = ''
        self.selection_timer = QTimer()
        self.selection_timer.setSingleShot(True)
        self.selection_timer.timeout.connect(self.highlightSelections)
        self.dollar_variables_info = {}

        # Appearance
        palette = self.palette()
        palette.setColor(QPalette.Base, QColor('#1d1f28'))
        palette.setColor(QPalette.Text, QColor('#bec3c9'))
        self.setPalette(palette)

        self.setFont(QFont('Consolas', 18))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        # Highlighter
        self.highlighter = GCodeSyntaxHighlighter(self.document(), self.dollar_variables_info)

        # Signals
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.onCursorPositionChanged)
        self.textChanged.connect(self.onTextChanged)
        self.selectionChanged.connect(self.onSelectionChanged)

        self.updateLineNumberAreaWidth(0)
        self.create_help_button()

    # ── Help button ───────────────────────────────────────────────────────────

    def create_help_button(self):
        self.help_button = QPushButton('?', self)
        self.help_button.setFixedSize(25, 25)
        self.help_button.setStyleSheet("""
            QPushButton {
                background-color: #BB86FC;
                color: #1d1f28;
                border: none;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover   { background-color: #9965DA; }
            QPushButton:pressed { background-color: #7c4dff; }
        """)
        self.help_button.clicked.connect(self.show_dollar_variables_help)
        self.help_button.setToolTip('Show available $ variables')
        self.position_help_button()

    def position_help_button(self):
        margin = 10
        self.help_button.move(
            self.viewport().width() - self.help_button.width() - margin,
            margin
        )

    # ── Layout events ─────────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(
            QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
        )
        self.position_help_button()

    # ── $ variable management ─────────────────────────────────────────────────

    def set_dollar_variables_info(self, variables_info):
        """Update the set of recognised $variables."""
        self.dollar_variables_info = variables_info
        self.highlighter.update_dollar_variables(variables_info)

    def show_dollar_variables_help(self):
        dialog = DollarVariablesDialog(self.dollar_variables_info, self)
        dialog.variable_selected.connect(self.insert_variable)
        dialog.exec_()

    def insert_variable(self, variable_text):
        self.textCursor().insertText(variable_text)

    # ── Line numbers ──────────────────────────────────────────────────────────

    def lineNumberAreaWidth(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num /= 10
            digits += 1
        return 3 + self.fontMetrics().boundingRect('9').width() * digits

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                if (blockNumber + 1) in self.errors:
                    painter.fillRect(0, top, self.lineNumberArea.width(), bottom - top, QColor('#ff4a7c'))
                    painter.setPen(QColor('#1d1f28'))
                else:
                    painter.fillRect(0, top, self.lineNumberArea.width(), bottom - top, QColor('#1d1f28'))
                    painter.setPen(QColor('#8b95c0'))
                painter.drawText(
                    0, top, self.lineNumberArea.width() - 2,
                    self.fontMetrics().height(), Qt.AlignRight, number
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    # ── Line / selection highlighting ─────────────────────────────────────────

    def onCursorPositionChanged(self):
        self.highlightCurrentLine()
        if hasattr(self.module, 'updatePreviewColors'):
            self.module.updatePreviewColors()

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            lineColor = QColor('#00c4fe')
            lineColor.setAlpha(15)
            cursor = self.textCursor()
            if cursor.hasSelection():
                start = cursor.selectionStart()
                end = cursor.selectionEnd()
                block = self.document().findBlock(start)
                while block.isValid() and block.position() <= end:
                    sel = QTextEdit.ExtraSelection()
                    sel.format.setBackground(lineColor)
                    sel.format.setProperty(QTextFormat.FullWidthSelection, True)
                    sel.cursor = QTextCursor(block)
                    extraSelections.append(sel)
                    block = block.next()
            else:
                sel = QTextEdit.ExtraSelection()
                sel.format.setBackground(lineColor)
                sel.format.setProperty(QTextFormat.FullWidthSelection, True)
                sel.cursor = cursor
                sel.cursor.clearSelection()
                extraSelections.append(sel)
        self.setExtraSelections(extraSelections)

    def onSelectionChanged(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText().strip()
            if len(selected) > 1 and selected != self.selected_text:
                self.selected_text = selected
                self.selection_timer.start(300)
        else:
            self.selected_text = ''
            self.highlightCurrentLine()

    def highlightSelections(self):
        if not self.selected_text:
            self.highlightCurrentLine()
            return

        extraSelections = []

        lineColor = QColor('#00c4fe')
        lineColor.setAlpha(15)
        cursor = self.textCursor()
        if not cursor.hasSelection():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(lineColor)
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel.cursor = cursor
            sel.cursor.clearSelection()
            extraSelections.append(sel)

        selectionColor = QColor('#1e3a8a')
        selectionColor.setAlpha(120)
        doc_cursor = QTextCursor(self.document())
        while True:
            doc_cursor = self.document().find(self.selected_text, doc_cursor)
            if doc_cursor.isNull():
                break
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(selectionColor)
            sel.cursor = doc_cursor
            extraSelections.append(sel)

        self.setExtraSelections(extraSelections)

    def getHighlightedLines(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            startLine = self.document().findBlock(start).blockNumber() + 1
            endLine   = self.document().findBlock(end).blockNumber() + 1
            return list(range(startLine, endLine + 1))
        return [cursor.blockNumber() + 1]

    # ── Template variable extraction ──────────────────────────────────────────

    def onTextChanged(self):
        """Extract {VAR:default} template variables for the variables panel."""
        text = self.toPlainText()
        # Match {LETTER+DIGITS} with optional :default — the template convention
        pattern = r'\{([A-Z]\d+)(?::([0-9.]+))?\}'
        matches = re.findall(pattern, text)

        new_variables = []
        seen = set()
        for var_name, default in matches:
            if var_name not in seen:
                new_variables.append((var_name, default))
                seen.add(var_name)
        new_variables.sort(key=lambda x: x[0])

        if new_variables != self.variables:
            self.variables = new_variables
            self.variables_changed.emit(self.variables)

    def getVariables(self):
        return self.variables.copy()

    def insertVariable(self, variable_name, default_value=None):
        cursor = self.textCursor()
        if default_value:
            cursor.insertText(f'{{{variable_name}:{default_value}}}')
        else:
            cursor.insertText(f'{{{variable_name}}}')

    # ── Utilities ─────────────────────────────────────────────────────────────

    def setErrors(self, errors):
        self.errors = errors
        self.lineNumberArea.update()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if hasattr(self.lineNumberArea, 'clickedLineNumber'):
            self.lineNumberArea.clickedLineNumber = None
            QToolTip.hideText()