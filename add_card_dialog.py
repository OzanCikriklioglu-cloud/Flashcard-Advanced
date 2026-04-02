"""
AddCardDialog — unified card creation dialog supporting three card types:
  • Basic        — classic question / answer
  • Cloze        — question with {{word}} blanks; answer auto-derived
  • Multiple Choice — question + correct answer + 3 distractor options
"""

import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QSizePolicy, QStackedWidget,
    QVBoxLayout, QWidget,
)

from theme import ThemeManager


_CLOZE_RE = re.compile(r"\{\{(.+?)\}\}")

# ── Page builders ──────────────────────────────────────────────────────────

class _BasicPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Question"))
        self.q_edit = QPlainTextEdit()
        self.q_edit.setPlaceholderText("Enter the question…")
        self.q_edit.setFixedHeight(90)
        layout.addWidget(self.q_edit)

        layout.addWidget(QLabel("Answer"))
        self.a_edit = QPlainTextEdit()
        self.a_edit.setPlaceholderText("Enter the answer…")
        self.a_edit.setFixedHeight(90)
        layout.addWidget(self.a_edit)

        layout.addStretch()

    def validate(self) -> str | None:
        """Return error string or None if valid."""
        if not self.q_edit.toPlainText().strip():
            return "Question cannot be empty."
        if not self.a_edit.toPlainText().strip():
            return "Answer cannot be empty."
        return None

    def get_data(self) -> dict:
        return {
            "card_type": "basic",
            "question": self.q_edit.toPlainText().strip(),
            "answer": self.a_edit.toPlainText().strip(),
            "distractors": [],
        }


class _ClozePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(8)

        help_lbl = QLabel("Wrap the answer(s) in double braces: {{word}}")
        help_lbl.setObjectName("helpLabel")
        layout.addWidget(help_lbl)

        layout.addWidget(QLabel("Question"))
        self.q_edit = QPlainTextEdit()
        self.q_edit.setPlaceholderText("e.g.  The capital of France is {{Paris}}")
        self.q_edit.setFixedHeight(90)
        self.q_edit.textChanged.connect(self._update_preview)
        layout.addWidget(self.q_edit)

        prev_row = QHBoxLayout()
        prev_row.addWidget(QLabel("Preview: "))
        self.preview_lbl = QLabel("—")
        self.preview_lbl.setObjectName("previewLabel")
        self.preview_lbl.setWordWrap(True)
        prev_row.addWidget(self.preview_lbl, 1)
        layout.addLayout(prev_row)

        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("errorLabel")
        layout.addWidget(self.error_lbl)

        layout.addStretch()

    def _update_preview(self):
        text = self.q_edit.toPlainText()
        preview = _CLOZE_RE.sub("[...]", text)
        self.preview_lbl.setText(preview or "—")

    def validate(self) -> str | None:
        text = self.q_edit.toPlainText().strip()
        if not text:
            return "Question cannot be empty."
        if not _CLOZE_RE.search(text):
            return "Add at least one {{blank}} in the question."
        return None

    def get_data(self) -> dict:
        question = self.q_edit.toPlainText().strip()
        words = _CLOZE_RE.findall(question)
        answer = " / ".join(words)
        return {
            "card_type": "cloze",
            "question": question,
            "answer": answer,
            "distractors": [],
        }


class _MCPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Question"))
        self.q_edit = QPlainTextEdit()
        self.q_edit.setPlaceholderText("Enter the question…")
        self.q_edit.setFixedHeight(72)
        layout.addWidget(self.q_edit)

        layout.addWidget(QLabel("Correct Answer"))
        self.correct_edit = QLineEdit()
        self.correct_edit.setPlaceholderText("The right answer…")
        layout.addWidget(self.correct_edit)

        layout.addWidget(QLabel("Wrong Options  (3 required)"))
        self.d1 = QLineEdit(); self.d1.setPlaceholderText("Wrong option 1")
        self.d2 = QLineEdit(); self.d2.setPlaceholderText("Wrong option 2")
        self.d3 = QLineEdit(); self.d3.setPlaceholderText("Wrong option 3")
        layout.addWidget(self.d1)
        layout.addWidget(self.d2)
        layout.addWidget(self.d3)

        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("errorLabel")
        layout.addWidget(self.error_lbl)

        layout.addStretch()

    def validate(self) -> str | None:
        if not self.q_edit.toPlainText().strip():
            return "Question cannot be empty."
        if not self.correct_edit.text().strip():
            return "Correct answer cannot be empty."
        distractors = [
            self.d1.text().strip(),
            self.d2.text().strip(),
            self.d3.text().strip(),
        ]
        if any(d == "" for d in distractors):
            return "All three wrong options are required."
        return None

    def get_data(self) -> dict:
        return {
            "card_type": "multiple_choice",
            "question": self.q_edit.toPlainText().strip(),
            "answer": self.correct_edit.text().strip(),
            "distractors": [
                self.d1.text().strip(),
                self.d2.text().strip(),
                self.d3.text().strip(),
            ],
        }


# ── Main dialog ────────────────────────────────────────────────────────────

class AddCardDialog(QDialog):
    """
    Tabbed dialog for creating a new card of any type.
    After exec() == Accepted, call get_data() to retrieve the card dict.
    """

    _TYPE_LABELS = ["Basic", "Cloze", "Multiple Choice"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Card")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.setStyleSheet(ThemeManager.instance().style("dialog"))

        self._pages: list[_BasicPage | _ClozePage | _MCPage] = [
            _BasicPage(),
            _ClozePage(),
            _MCPage(),
        ]
        self._result: dict | None = None

        self._build_ui()

    # ── build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Type selector
        type_row = QHBoxLayout()
        type_lbl = QLabel("Card Type")
        type_lbl.setFixedWidth(80)
        self.type_combo = QComboBox()
        self.type_combo.addItems(self._TYPE_LABELS)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_row.addWidget(type_lbl)
        type_row.addWidget(self.type_combo)
        layout.addLayout(type_row)

        # Stacked pages
        self.stack = QStackedWidget()
        for page in self._pages:
            self.stack.addWidget(page)
        layout.addWidget(self.stack)

        # Error label (shared)
        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("errorLabel")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_lbl)

        # OK / Cancel
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton("Add Card")
        ok_btn.setObjectName("okBtn")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._validate_and_accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    # ── slots ──────────────────────────────────────────────────────────────

    def _on_type_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        self.error_lbl.setText("")

    def _validate_and_accept(self):
        page = self._pages[self.stack.currentIndex()]
        err = page.validate()
        if err:
            self.error_lbl.setText(err)
            return
        self._result = page.get_data()
        self.accept()

    # ── public ─────────────────────────────────────────────────────────────

    def get_data(self) -> dict | None:
        """Return card data dict or None if dialog was cancelled / invalid."""
        return self._result
