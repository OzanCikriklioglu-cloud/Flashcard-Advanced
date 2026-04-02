from datetime import date

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

import sm2 as SRS
from add_card_dialog import AddCardDialog
from data import Card, Deck, load_decks, new_id, save_decks
from study_window import StudyWindow
from theme import ThemeManager


_TYPE_BADGE = {
    "basic":           "",
    "cloze":           "[C] ",
    "multiple_choice": "[M] ",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flashcard App")
        self.setMinimumSize(860, 600)
        self.decks = load_decks()
        self.current_deck: Deck | None = None

        self._build_ui()

        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current())

        self._refresh_deck_list()

    # ------------------------------------------------------------------ build

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Toolbar ────────────────────────────────────────────────────────
        self.toolbar = QWidget()
        self.toolbar.setObjectName("toolbar")
        self.toolbar.setFixedHeight(44)
        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(16, 0, 16, 0)

        app_name = QLabel("Flashcard App")
        app_name.setObjectName("appName")
        app_name.setStyleSheet("font-size: 15px; font-weight: bold;")

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setFixedSize(36, 30)
        self.theme_btn.clicked.connect(self._toggle_theme)

        tb_layout.addWidget(app_name)
        tb_layout.addStretch()
        tb_layout.addWidget(self.theme_btn)
        outer.addWidget(self.toolbar)

        # ── Main content ───────────────────────────────────────────────────
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self._build_left_panel())
        content_layout.addWidget(self._build_right_panel())
        outer.addWidget(content, 1)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("leftPanel")
        panel.setFixedWidth(240)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        hdr = QHBoxLayout()
        title = QLabel("DECKS")
        title.setObjectName("panelTitle")
        hdr.addWidget(title)
        hdr.addStretch()
        layout.addLayout(hdr)

        self.deck_list = QListWidget()
        self.deck_list.setObjectName("deckList")
        self.deck_list.setSpacing(2)
        self.deck_list.currentItemChanged.connect(self._on_deck_selected)
        layout.addWidget(self.deck_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.add_deck_btn = QPushButton("+ New Deck")
        self.add_deck_btn.setObjectName("primaryBtn")
        self.add_deck_btn.clicked.connect(self._add_deck)

        self.del_deck_btn = QPushButton("Delete")
        self.del_deck_btn.setObjectName("dangerBtn")
        self.del_deck_btn.clicked.connect(self._delete_deck)
        self.del_deck_btn.setEnabled(False)

        btn_row.addWidget(self.add_deck_btn)
        btn_row.addWidget(self.del_deck_btn)
        layout.addLayout(btn_row)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("rightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.deck_title_label = QLabel("Select a deck")
        self.deck_title_label.setObjectName("deckTitle")
        self.study_btn = QPushButton("Study")
        self.study_btn.setObjectName("studyBtn")
        self.study_btn.setEnabled(False)
        self.study_btn.clicked.connect(self._start_study)
        header.addWidget(self.deck_title_label)
        header.addStretch()
        header.addWidget(self.study_btn)
        layout.addLayout(header)

        self.card_count_label = QLabel("")
        self.card_count_label.setObjectName("cardCount")
        layout.addWidget(self.card_count_label)

        self.card_list = QListWidget()
        self.card_list.setObjectName("cardList")
        self.card_list.currentItemChanged.connect(self._on_card_selected)
        layout.addWidget(self.card_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.add_card_btn = QPushButton("+ Add Card")
        self.add_card_btn.setObjectName("primaryBtn")
        self.add_card_btn.clicked.connect(self._add_card)
        self.add_card_btn.setEnabled(False)

        self.del_card_btn = QPushButton("Delete Card")
        self.del_card_btn.setObjectName("dangerBtn")
        self.del_card_btn.clicked.connect(self._delete_card)
        self.del_card_btn.setEnabled(False)

        btn_row.addWidget(self.add_card_btn)
        btn_row.addWidget(self.del_card_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return panel

    # ------------------------------------------------------------------ theme

    def _apply_theme(self, _theme_name: str = ""):
        tm = ThemeManager.instance()
        self.setStyleSheet(tm.style("main"))

        # Theme toggle button icon
        self.theme_btn.setText("☀" if tm.is_dark() else "🌙")

        # Toolbar needs explicit background (child widget of root)
        c = tm.colors()
        self.toolbar.setStyleSheet(
            f"QWidget#toolbar {{ background-color: {c['panel']}; "
            f"border-bottom: 1px solid {c['overlay']}; }}"
        )

        self._refresh_deck_list()

    def _toggle_theme(self):
        ThemeManager.instance().toggle()

    # ------------------------------------------------------------------ refresh

    def _refresh_deck_list(self):
        selected_id = self.current_deck.id if self.current_deck else None
        c = ThemeManager.instance().colors()

        self.deck_list.blockSignals(True)
        self.deck_list.clear()

        for deck in self.decks:
            due   = SRS.due_count(deck)
            total = len(deck.cards)

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, deck.id)
            item.setSizeHint(QSize(220, 56))
            self.deck_list.addItem(item)

            w = QWidget()
            w.setAutoFillBackground(False)
            w.setStyleSheet("background: transparent;")
            inner = QVBoxLayout(w)
            inner.setContentsMargins(10, 8, 10, 8)
            inner.setSpacing(2)

            name_lbl = QLabel(deck.name)
            name_lbl.setStyleSheet(
                f"color: {c['item_text']}; font-size: 14px; background: transparent;"
            )

            if total == 0:
                info_text  = "Empty"
                info_color = c["empty_color"]
            elif due > 0:
                info_text  = f"{due} due  ·  {total} total"
                info_color = c["due_color"]
            else:
                info_text  = f"All caught up  ·  {total} total"
                info_color = c["ok_color"]

            info_lbl = QLabel(info_text)
            info_lbl.setStyleSheet(
                f"color: {info_color}; font-size: 11px; background: transparent;"
            )

            inner.addWidget(name_lbl)
            inner.addWidget(info_lbl)
            self.deck_list.setItemWidget(item, w)

        self.deck_list.blockSignals(False)

        # Restore selection
        if selected_id:
            for i in range(self.deck_list.count()):
                it = self.deck_list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == selected_id:
                    self.deck_list.setCurrentItem(it)
                    break

    def _refresh_card_list(self):
        self.card_list.clear()
        if not self.current_deck:
            return

        total = len(self.current_deck.cards)
        due   = SRS.due_count(self.current_deck)
        today = date.today()

        if total == 0:
            self.study_btn.setEnabled(False)
            self.study_btn.setText("Study")
            self.card_count_label.setText("No cards yet")
        elif due > 0:
            self.study_btn.setEnabled(True)
            self.study_btn.setText(f"Study Due ({due})")
            self.card_count_label.setText(f"{due} due  ·  {total} total")
        else:
            self.study_btn.setEnabled(True)
            self.study_btn.setText("Study All")
            self.card_count_label.setText(f"All caught up  ·  {total} total")

        for card in self.current_deck.cards:
            is_due = SRS.is_due(card.next_review)

            if not card.last_reviewed:
                status = "🆕"
            elif is_due:
                status = "📅"
            else:
                due_date = date.fromisoformat(card.next_review)
                days = (due_date - today).days
                status = f"✓ {days}d"

            badge = _TYPE_BADGE.get(card.card_type, "")
            display = card.question[:70].replace("\n", " ")
            item = QListWidgetItem(f"{status}  {badge}{display}")
            item.setData(Qt.ItemDataRole.UserRole, card.id)
            item.setToolTip(f"Answer: {card.answer}\nReviewed: {card.repetitions}x")
            self.card_list.addItem(item)

    # ------------------------------------------------------------------ slots

    def _on_deck_selected(self, current, _previous):
        if current is None:
            self.current_deck = None
            self.deck_title_label.setText("Select a deck")
            self.card_count_label.setText("")
            self.card_list.clear()
            self.add_card_btn.setEnabled(False)
            self.del_deck_btn.setEnabled(False)
            self.study_btn.setEnabled(False)
            self.study_btn.setText("Study")
            return

        deck_id = current.data(Qt.ItemDataRole.UserRole)
        self.current_deck = next((d for d in self.decks if d.id == deck_id), None)
        if self.current_deck:
            self.deck_title_label.setText(self.current_deck.name)
            self.add_card_btn.setEnabled(True)
            self.del_deck_btn.setEnabled(True)
            self._refresh_card_list()

    def _on_card_selected(self, current, _previous):
        self.del_card_btn.setEnabled(current is not None)

    def _add_deck(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Deck", "Deck name:")
        if ok and name.strip():
            deck = Deck(id=new_id(), name=name.strip())
            self.decks.append(deck)
            save_decks(self.decks)
            self._refresh_deck_list()
            self.deck_list.setCurrentRow(self.deck_list.count() - 1)

    def _delete_deck(self):
        if not self.current_deck:
            return
        reply = QMessageBox.question(
            self,
            "Delete Deck",
            f"Delete '{self.current_deck.name}' and all its cards?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.decks = [d for d in self.decks if d.id != self.current_deck.id]
            self.current_deck = None
            save_decks(self.decks)
            self._refresh_deck_list()
            self._on_deck_selected(None, None)

    def _add_card(self):
        if not self.current_deck:
            return
        dlg = AddCardDialog(self)
        if dlg.exec() != AddCardDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data:
            return
        card = Card(
            id=new_id(),
            question=data["question"],
            answer=data["answer"],
            card_type=data["card_type"],
            distractors=data["distractors"],
        )
        self.current_deck.cards.append(card)
        save_decks(self.decks)
        self._refresh_card_list()

    def _delete_card(self):
        item = self.card_list.currentItem()
        if not item or not self.current_deck:
            return
        card_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_deck.cards = [
            c for c in self.current_deck.cards if c.id != card_id
        ]
        save_decks(self.decks)
        self._refresh_card_list()

    def _start_study(self):
        if not self.current_deck:
            return

        due_cards = [c for c in self.current_deck.cards if SRS.is_due(c.next_review)]

        if due_cards:
            cards_to_study = due_cards
        else:
            reply = QMessageBox.question(
                self,
                "All Caught Up",
                f"No cards are due today in '{self.current_deck.name}'.\n\n"
                "Would you like to review all cards anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            cards_to_study = self.current_deck.cards

        StudyWindow(self.current_deck, cards_to_study, self.decks, self).exec()
        self._refresh_card_list()
        self._refresh_deck_list()
