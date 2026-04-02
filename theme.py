"""
Centralized theme management for the Flashcard App.

Usage:
    from theme import ThemeManager
    tm = ThemeManager.instance()
    self.setStyleSheet(tm.style("main"))
    tm.theme_changed.connect(self._on_theme_changed)
"""

import json
import os

from PyQt6.QtCore import QObject, pyqtSignal


_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "settings.json"
)

# ── Colour palettes ────────────────────────────────────────────────────────

DARK = {
    "bg":               "#1e1e2e",
    "surface":          "#181825",
    "panel":            "#1e1e2e",
    "overlay":          "#313244",
    "muted":            "#45475a",
    "text":             "#cdd6f4",
    "subtext":          "#6c7086",
    "blue":             "#89b4fa",
    "green":            "#a6e3a1",
    "red":              "#f38ba8",
    "orange":           "#fab387",
    "yellow":           "#f9e2af",
    "teal":             "#94e2d5",
    "pink":             "#f5c2e7",
    # semantic
    "card_bg":          "#181825",
    "card_border":      "#313244",
    "card_ans_bg":      "#1a2b1e",
    "card_ans_border":  "#a6e3a1",
    "btn_text":         "#1e1e2e",
    "item_text":        "#cdd6f4",
    "item_subtext":     "#6c7086",
    "due_color":        "#f38ba8",
    "ok_color":         "#a6e3a1",
    "empty_color":      "#45475a",
}

LIGHT = {
    "bg":               "#eff1f5",
    "surface":          "#ffffff",
    "panel":            "#e6e9ef",
    "overlay":          "#ccd0da",
    "muted":            "#bcc0cc",
    "text":             "#4c4f69",
    "subtext":          "#8c8fa1",
    "blue":             "#1e66f5",
    "green":            "#40a02b",
    "red":              "#d20f39",
    "orange":           "#fe640b",
    "yellow":           "#df8e1d",
    "teal":             "#179299",
    "pink":             "#ea76cb",
    # semantic
    "card_bg":          "#ffffff",
    "card_border":      "#ccd0da",
    "card_ans_bg":      "#f0fff4",
    "card_ans_border":  "#40a02b",
    "btn_text":         "#ffffff",
    "item_text":        "#4c4f69",
    "item_subtext":     "#8c8fa1",
    "due_color":        "#d20f39",
    "ok_color":         "#40a02b",
    "empty_color":      "#9ca0b0",
}


# ── CSS builders ──────────────────────────────────────────────────────────

def _main_css(c: dict) -> str:
    return f"""
QMainWindow, QWidget {{
    font-family: "Segoe UI", Arial, sans-serif;
    background-color: {c['bg']};
    color: {c['text']};
}}
QWidget#leftPanel {{
    background-color: {c['panel']};
    border-right: 1px solid {c['overlay']};
}}
QWidget#rightPanel {{
    background-color: {c['bg']};
}}
QLabel#panelTitle {{
    color: {c['subtext']};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 2px;
    background: transparent;
}}
QLabel#deckTitle {{
    font-size: 22px;
    font-weight: bold;
    color: {c['text']};
}}
QLabel#cardCount {{
    font-size: 13px;
    color: {c['subtext']};
}}
QListWidget#deckList {{
    background-color: transparent;
    border: none;
    outline: none;
}}
QListWidget#deckList::item {{
    border-radius: 8px;
    margin: 2px 0;
    padding: 0;
}}
QListWidget#deckList::item:selected {{
    background-color: {c['overlay']};
}}
QListWidget#deckList::item:hover:!selected {{
    background-color: {c['muted']}44;
}}
QListWidget#cardList {{
    background-color: {c['surface']};
    border: 1px solid {c['overlay']};
    border-radius: 8px;
    font-size: 14px;
    color: {c['text']};
    outline: none;
}}
QListWidget#cardList::item {{
    padding: 11px 16px;
    border-bottom: 1px solid {c['overlay']};
}}
QListWidget#cardList::item:selected {{
    background-color: {c['overlay']};
}}
QPushButton#primaryBtn {{
    background-color: {c['blue']};
    color: {c['btn_text']};
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton#primaryBtn:hover {{
    background-color: {c['teal']};
}}
QPushButton#primaryBtn:disabled {{
    background-color: {c['overlay']};
    color: {c['muted']};
}}
QPushButton#dangerBtn {{
    background-color: transparent;
    color: {c['red']};
    border: 1px solid {c['red']};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}}
QPushButton#dangerBtn:hover {{
    background-color: {c['red']};
    color: {c['btn_text']};
}}
QPushButton#dangerBtn:disabled {{
    color: {c['muted']};
    border-color: {c['muted']};
}}
QPushButton#studyBtn {{
    background-color: {c['green']};
    color: {c['btn_text']};
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton#studyBtn:hover {{
    background-color: {c['teal']};
}}
QPushButton#studyBtn:disabled {{
    background-color: {c['overlay']};
    color: {c['muted']};
}}
QPushButton#themeBtn {{
    background-color: transparent;
    color: {c['subtext']};
    border: none;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 16px;
}}
QPushButton#themeBtn:hover {{
    color: {c['text']};
    background-color: {c['overlay']};
}}
"""


def _study_css(c: dict) -> str:
    return f"""
QDialog {{
    background-color: {c['bg']};
    color: {c['text']};
    font-family: "Segoe UI", Arial, sans-serif;
}}
QWidget {{
    background-color: transparent;
    color: {c['text']};
    font-family: "Segoe UI", Arial, sans-serif;
}}
QLabel#infoLabel  {{ font-size: 13px; color: {c['subtext']}; }}
QLabel#hintLabel  {{ font-size: 12px; color: {c['muted']}; }}
QProgressBar#progressBar {{
    background-color: {c['overlay']};
    border-radius: 3px;
    border: none;
}}
QProgressBar#progressBar::chunk {{
    background-color: {c['blue']};
    border-radius: 3px;
}}
QFrame#cardFrame {{
    background-color: {c['card_bg']};
    border-radius: 18px;
    border: 1.5px solid {c['card_border']};
}}
QLabel#cardSideLabel {{
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 2px;
    background: transparent;
}}
QLabel#cardText {{
    font-size: 22px;
    color: {c['text']};
    padding: 0 28px;
    background: transparent;
}}
QLabel#intervalLabel {{
    font-size: 11px;
    color: {c['subtext']};
    background: transparent;
}}
QPushButton#revealBtn {{
    background-color: {c['overlay']};
    color: {c['text']};
    border: 1.5px solid {c['muted']};
    border-radius: 8px;
    padding: 11px 40px;
    font-size: 14px;
    font-weight: bold;
    min-width: 180px;
}}
QPushButton#revealBtn:hover {{
    background-color: {c['muted']};
    border-color: {c['blue']};
    color: {c['blue']};
}}
QPushButton#againBtn {{
    background-color: transparent;
    color: {c['red']};
    border: 1.5px solid {c['red']};
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
    min-width: 100px;
}}
QPushButton#againBtn:hover {{ background-color: {c['red']}; color: {c['btn_text']}; }}
QPushButton#hardBtn {{
    background-color: transparent;
    color: {c['orange']};
    border: 1.5px solid {c['orange']};
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
    min-width: 100px;
}}
QPushButton#hardBtn:hover {{ background-color: {c['orange']}; color: {c['btn_text']}; }}
QPushButton#goodBtn {{
    background-color: {c['blue']};
    color: {c['btn_text']};
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
    min-width: 100px;
}}
QPushButton#goodBtn:hover {{ background-color: {c['teal']}; }}
QPushButton#easyBtn {{
    background-color: {c['green']};
    color: {c['btn_text']};
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
    min-width: 100px;
}}
QPushButton#easyBtn:hover {{ background-color: {c['teal']}; }}
QPushButton#mcOptionBtn {{
    background-color: {c['overlay']};
    color: {c['text']};
    border: 1.5px solid {c['muted']};
    border-radius: 8px;
    padding: 14px 20px;
    font-size: 14px;
    font-weight: bold;
    min-width: 220px;
    text-align: left;
}}
QPushButton#mcOptionBtn:hover {{
    background-color: {c['muted']};
    border-color: {c['blue']};
}}
QPushButton#mcOptionBtn:disabled {{
    border-color: {c['overlay']};
}}
QPushButton#focusBtn {{
    background-color: transparent;
    color: {c['subtext']};
    border: 1px solid {c['overlay']};
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 12px;
}}
QPushButton#focusBtn:hover {{
    color: {c['text']};
    border-color: {c['muted']};
    background-color: {c['overlay']};
}}
QPushButton#doneBtn {{
    background-color: {c['blue']};
    color: {c['btn_text']};
    border: none;
    border-radius: 8px;
    padding: 11px 48px;
    font-size: 14px;
    font-weight: bold;
}}
QPushButton#doneBtn:hover {{ background-color: {c['teal']}; }}
"""


def _dialog_css(c: dict) -> str:
    return f"""
QDialog, QWidget {{
    background-color: {c['bg']};
    color: {c['text']};
    font-family: "Segoe UI", Arial, sans-serif;
}}
QLabel {{
    color: {c['text']};
    background: transparent;
}}
QLabel#errorLabel {{
    color: {c['red']};
    font-size: 12px;
    background: transparent;
}}
QLabel#helpLabel {{
    color: {c['subtext']};
    font-size: 12px;
    background: transparent;
}}
QLabel#previewLabel {{
    color: {c['blue']};
    font-size: 13px;
    background: transparent;
}}
QComboBox {{
    background-color: {c['surface']};
    color: {c['text']};
    border: 1px solid {c['overlay']};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    min-height: 28px;
}}
QComboBox::drop-down {{
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {c['surface']};
    color: {c['text']};
    border: 1px solid {c['overlay']};
    selection-background-color: {c['overlay']};
}}
QPlainTextEdit, QLineEdit {{
    background-color: {c['surface']};
    color: {c['text']};
    border: 1px solid {c['overlay']};
    border-radius: 6px;
    padding: 8px;
    font-size: 14px;
    selection-background-color: {c['blue']}55;
}}
QPlainTextEdit:focus, QLineEdit:focus {{
    border-color: {c['blue']};
}}
QPushButton#okBtn {{
    background-color: {c['blue']};
    color: {c['btn_text']};
    border: none;
    border-radius: 6px;
    padding: 9px 28px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton#okBtn:hover {{ background-color: {c['teal']}; }}
QPushButton#cancelBtn {{
    background-color: transparent;
    color: {c['subtext']};
    border: 1px solid {c['overlay']};
    border-radius: 6px;
    padding: 9px 28px;
    font-size: 13px;
}}
QPushButton#cancelBtn:hover {{
    color: {c['text']};
    border-color: {c['muted']};
    background-color: {c['overlay']};
}}
QTabWidget::pane {{
    border: 1px solid {c['overlay']};
    border-radius: 6px;
    background-color: {c['surface']};
}}
QTabBar::tab {{
    background-color: {c['panel']};
    color: {c['subtext']};
    border: 1px solid {c['overlay']};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 8px 20px;
    font-size: 13px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {c['surface']};
    color: {c['text']};
    font-weight: bold;
}}
QTabBar::tab:hover:!selected {{
    background-color: {c['overlay']};
}}
"""


# ── ThemeManager ──────────────────────────────────────────────────────────

class ThemeManager(QObject):
    """Singleton. Holds current theme and emits theme_changed on toggle."""

    theme_changed = pyqtSignal(str)   # "dark" or "light"

    _instance: "ThemeManager | None" = None

    DARK  = "dark"
    LIGHT = "light"

    def __init__(self):
        super().__init__()
        self._current = self.DARK
        self._load()

    # ── singleton ──────────────────────────────────────────────────────────

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── public API ─────────────────────────────────────────────────────────

    def current(self) -> str:
        return self._current

    def is_dark(self) -> bool:
        return self._current == self.DARK

    def colors(self) -> dict:
        return DARK if self.is_dark() else LIGHT

    def color(self, key: str) -> str:
        return self.colors()[key]

    def style(self, context: str = "main") -> str:
        """Return the full QSS string for the given context."""
        c = self.colors()
        if context == "study":
            return _study_css(c)
        if context == "dialog":
            return _dialog_css(c)
        return _main_css(c)

    def toggle(self) -> None:
        self._current = self.LIGHT if self.is_dark() else self.DARK
        self._save()
        self.theme_changed.emit(self._current)

    # ── persistence ────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(_SETTINGS_FILE):
            return
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            t = data.get("theme", self.DARK)
            if t in (self.DARK, self.LIGHT):
                self._current = t
        except Exception:
            pass

    def _save(self) -> None:
        try:
            existing = {}
            if os.path.exists(_SETTINGS_FILE):
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing["theme"] = self._current
            with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
        except Exception:
            pass
