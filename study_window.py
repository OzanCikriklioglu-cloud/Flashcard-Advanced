import random
import re
import time
from datetime import date
from functools import partial

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QStackedWidget,
    QVBoxLayout, QWidget,
)

import sm2 as SRS
from data import Deck, save_decks
from theme import ThemeManager

_CLOZE_RE = re.compile(r"\{\{(.+?)\}\}")


class StudyWindow(QDialog):
    """
    Modal study session.

    Supports three card types:
      • basic          — question → flip → answer → quality buttons
      • cloze          — blanked question → flip → highlighted answer → quality buttons
      • multiple_choice — question + 4 option buttons → auto-graded with visual feedback
    """

    def __init__(self, deck: Deck, cards, all_decks: list, parent=None):
        super().__init__(parent)
        self.deck      = deck
        self.all_decks = all_decks
        self.cards     = list(cards)
        random.shuffle(self.cards)

        self.current_index  = 0
        self.showing_answer = False
        self._think_start: float = 0.0
        self._think_ms:    int   = 0
        self._focus_mode   = False
        self._mc_answered  = False

        self.counts = {SRS.AGAIN: 0, SRS.HARD: 0, SRS.GOOD: 0, SRS.EASY: 0}

        self.setWindowTitle(f"Study — {deck.name}")
        self.setMinimumSize(700, 580)
        self.setModal(True)

        self._build_ui()
        self._apply_theme()

        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)

        self._show_card()

    # ------------------------------------------------------------------ build

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)
        self.stack.addWidget(self._build_study_page())    # 0
        self.stack.addWidget(self._build_results_page())  # 1

    def _build_study_page(self) -> QWidget:
        page = QWidget()
        self._page_layout = QVBoxLayout(page)
        layout = self._page_layout
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(0)

        # ── Top bar ────────────────────────────────────────────────────────
        top = QHBoxLayout()
        self.progress_label = QLabel()
        self.progress_label.setObjectName("infoLabel")
        self.stats_label = QLabel()
        self.stats_label.setObjectName("infoLabel")
        self.focus_btn = QPushButton("⛶  Focus")
        self.focus_btn.setObjectName("focusBtn")
        self.focus_btn.setFixedHeight(26)
        self.focus_btn.clicked.connect(self._toggle_focus)

        top.addWidget(self.progress_label)
        top.addStretch()
        top.addWidget(self.stats_label)
        top.addSpacing(12)
        top.addWidget(self.focus_btn)
        layout.addLayout(top)
        layout.addSpacing(8)

        # ── Progress bar ───────────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        layout.addWidget(self.progress_bar)
        layout.addSpacing(16)

        # ── Memory info ────────────────────────────────────────────────────
        self._mem_row_widget = QWidget()
        mem_row = QHBoxLayout(self._mem_row_widget)
        mem_row.setContentsMargins(0, 0, 0, 0)
        self.memory_label = QLabel()
        self.seen_label   = QLabel()
        self.seen_label.setObjectName("infoLabel")
        mem_row.addWidget(self.memory_label)
        mem_row.addStretch()
        mem_row.addWidget(self.seen_label)
        layout.addWidget(self._mem_row_widget)
        layout.addSpacing(10)

        # ── Card ───────────────────────────────────────────────────────────
        self.card_frame = QFrame()
        self.card_frame.setObjectName("cardFrame")
        self.card_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self.card_frame.mousePressEvent = lambda _: self._flip_card()

        card_inner = QVBoxLayout(self.card_frame)
        card_inner.setContentsMargins(32, 28, 32, 28)
        card_inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card_side_label = QLabel()
        self.card_side_label.setObjectName("cardSideLabel")
        self.card_side_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card_text = QLabel()
        self.card_text.setObjectName("cardText")
        self.card_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_text.setWordWrap(True)
        self.card_text.setTextFormat(Qt.TextFormat.RichText)

        card_inner.addStretch()
        card_inner.addWidget(self.card_side_label)
        card_inner.addSpacing(14)
        card_inner.addWidget(self.card_text)
        card_inner.addStretch()

        layout.addWidget(self.card_frame, 1)
        layout.addSpacing(12)

        # ── Hint line ──────────────────────────────────────────────────────
        self.hint_label = QLabel()
        self.hint_label.setObjectName("hintLabel")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_label)
        layout.addSpacing(16)

        # ── Bottom area (stacked) ──────────────────────────────────────────
        self.bottom_stack = QStackedWidget()
        self.bottom_stack.setFixedHeight(120)

        # Page 0 — reveal button (basic / cloze)
        reveal_page = QWidget()
        rl = QHBoxLayout(reveal_page)
        rl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reveal_btn = QPushButton("Reveal Answer")
        self.reveal_btn.setObjectName("revealBtn")
        self.reveal_btn.clicked.connect(self._flip_card)
        rl.addWidget(self.reveal_btn)

        # Page 1 — quality buttons (basic / cloze after flip)
        quality_page = QWidget()
        ql = QVBoxLayout(quality_page)
        ql.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ql.setSpacing(4)

        q_btn_row = QHBoxLayout()
        q_btn_row.setSpacing(10)
        q_btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.again_btn = QPushButton("Again"); self.again_btn.setObjectName("againBtn")
        self.hard_btn  = QPushButton("Hard");  self.hard_btn.setObjectName("hardBtn")
        self.good_btn  = QPushButton("Good");  self.good_btn.setObjectName("goodBtn")
        self.easy_btn  = QPushButton("Easy");  self.easy_btn.setObjectName("easyBtn")

        self.again_btn.clicked.connect(lambda: self._apply_quality(SRS.AGAIN))
        self.hard_btn.clicked.connect( lambda: self._apply_quality(SRS.HARD))
        self.good_btn.clicked.connect( lambda: self._apply_quality(SRS.GOOD))
        self.easy_btn.clicked.connect( lambda: self._apply_quality(SRS.EASY))

        self.again_lbl = QLabel(); self.again_lbl.setObjectName("intervalLabel"); self.again_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hard_lbl  = QLabel(); self.hard_lbl.setObjectName("intervalLabel");  self.hard_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.good_lbl  = QLabel(); self.good_lbl.setObjectName("intervalLabel");  self.good_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.easy_lbl  = QLabel(); self.easy_lbl.setObjectName("intervalLabel");  self.easy_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for btn, lbl in (
            (self.again_btn, self.again_lbl),
            (self.hard_btn,  self.hard_lbl),
            (self.good_btn,  self.good_lbl),
            (self.easy_btn,  self.easy_lbl),
        ):
            col = QVBoxLayout()
            col.setSpacing(3)
            col.addWidget(btn)
            col.addWidget(lbl)
            q_btn_row.addLayout(col)

        ql.addLayout(q_btn_row)

        # Page 2 — multiple choice (2×2 grid)
        mc_page = QWidget()
        mc_grid = QGridLayout(mc_page)
        mc_grid.setSpacing(10)
        mc_grid.setContentsMargins(0, 0, 0, 0)

        self._mc_buttons: list[QPushButton] = []
        for idx in range(4):
            btn = QPushButton()
            btn.setObjectName("mcOptionBtn")
            btn.clicked.connect(partial(self._handle_mc_answer, idx))
            self._mc_buttons.append(btn)
            mc_grid.addWidget(btn, idx // 2, idx % 2)

        self.bottom_stack.addWidget(reveal_page)   # 0
        self.bottom_stack.addWidget(quality_page)  # 1
        self.bottom_stack.addWidget(mc_page)       # 2

        layout.addWidget(self.bottom_stack)

        return page

    def _build_results_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.res_emoji     = QLabel(); self.res_emoji.setAlignment(Qt.AlignmentFlag.AlignCenter); self.res_emoji.setStyleSheet("font-size: 54px;")
        self.res_title     = QLabel("Session Complete!"); self.res_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.res_score     = QLabel(); self.res_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.res_breakdown = QLabel(); self.res_breakdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.res_next      = QLabel(); self.res_next.setAlignment(Qt.AlignmentFlag.AlignCenter)

        done_btn = QPushButton("Done")
        done_btn.setObjectName("doneBtn")
        done_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(done_btn)
        btn_row.addStretch()

        layout.addStretch()
        layout.addWidget(self.res_emoji)
        layout.addSpacing(6)
        layout.addWidget(self.res_title)
        layout.addWidget(self.res_score)
        layout.addWidget(self.res_breakdown)
        layout.addSpacing(8)
        layout.addWidget(self.res_next)
        layout.addSpacing(28)
        layout.addLayout(btn_row)
        layout.addStretch()

        return page

    # ------------------------------------------------------------------ theme

    def _apply_theme(self, _=""):
        tm = ThemeManager.instance()
        self.setStyleSheet(tm.style("study"))
        c = tm.colors()

        # Results labels need explicit colors (inside stacked widget)
        self.res_title.setStyleSheet(
            f"font-size: 26px; font-weight: bold; color: {c['text']};"
        )
        self.res_score.setStyleSheet(f"font-size: 16px; color: {c['subtext']};")
        self.res_breakdown.setStyleSheet(f"font-size: 13px; color: {c['muted']};")
        self.res_next.setStyleSheet(f"font-size: 13px; color: {c['blue']};")

        # Re-apply card frame style for current state
        if self.showing_answer:
            self._set_card_answer_style()
        else:
            self._set_card_question_style()

    def _set_card_question_style(self):
        c = ThemeManager.instance().colors()
        self.card_frame.setStyleSheet(
            f"QFrame#cardFrame {{ background-color: {c['card_bg']}; "
            f"border-radius: 18px; border: 1.5px solid {c['card_border']}; }}"
        )
        self.card_side_label.setStyleSheet(
            f"color: {c['blue']}; font-size: 11px; font-weight: bold; letter-spacing: 2px;"
        )

    def _set_card_answer_style(self):
        c = ThemeManager.instance().colors()
        self.card_frame.setStyleSheet(
            f"QFrame#cardFrame {{ background-color: {c['card_ans_bg']}; "
            f"border-radius: 18px; border: 2px solid {c['card_ans_border']}; }}"
        )
        self.card_side_label.setStyleSheet(
            f"color: {c['green']}; font-size: 11px; font-weight: bold; letter-spacing: 2px;"
        )

    # ------------------------------------------------------------------ logic

    def _show_card(self):
        if self.current_index >= len(self.cards):
            self._show_results()
            return

        card = self.cards[self.current_index]
        self.showing_answer = False
        self._mc_answered   = False
        self._think_start   = time.perf_counter()

        total = len(self.cards)
        self.progress_label.setText(f"Card {self.current_index + 1} / {total}")
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(self.current_index)

        # Session stats
        a, h, g, e = (self.counts[k] for k in (SRS.AGAIN, SRS.HARD, SRS.GOOD, SRS.EASY))
        self.stats_label.setText(
            f"<span style='color:#f38ba8'>✕ {a}</span>  "
            f"<span style='color:#fab387'>◐ {h}</span>  "
            f"<span style='color:#89b4fa'>✓ {g}</span>  "
            f"<span style='color:#a6e3a1'>★ {e}</span>"
        )

        # Memory / forgetting info
        prob     = SRS.forgetting_prob(card.last_reviewed, card.interval, card.easiness_factor)
        prob_pct = int(prob * 100)

        if not card.last_reviewed:
            self.memory_label.setText("🆕  New card")
            self.memory_label.setStyleSheet("font-size: 12px; color: #89b4fa; font-weight: bold;")
            self.seen_label.setText("")
        else:
            last_date = date.fromisoformat(card.last_reviewed)
            days_ago  = (date.today() - last_date).days
            seen_str  = (
                "seen today" if days_ago == 0 else
                "seen yesterday" if days_ago == 1 else
                f"seen {days_ago}d ago" if days_ago < 30 else
                f"seen {days_ago // 7}w ago"
            )
            color, icon = (
                ("#a6e3a1", "🟢") if prob_pct < 20 else
                ("#f9e2af", "🟡") if prob_pct < 50 else
                ("#fab387", "🟠") if prob_pct < 75 else
                ("#f38ba8", "🔴")
            )
            self.memory_label.setText(f"{icon}  {prob_pct}% likely to forget")
            self.memory_label.setStyleSheet(f"font-size: 12px; color: {color};")
            self.seen_label.setText(seen_str)

        # Card type dispatch
        self.card_side_label.setText("QUESTION")
        self._set_card_question_style()

        if card.card_type == "cloze":
            blanked = _CLOZE_RE.sub("[...]", card.question)
            self.card_text.setText(blanked)
            self.hint_label.setText("Click card or Space to reveal  ·  F = focus mode")
            self.bottom_stack.setCurrentIndex(0)  # reveal button

        elif card.card_type == "multiple_choice":
            self.card_text.setText(card.question)
            self.hint_label.setText("Click an answer  ·  1–4 to select  ·  F = focus mode")
            self._setup_mc_options(card)
            self.bottom_stack.setCurrentIndex(2)  # MC buttons

        else:  # basic
            self.card_text.setText(card.question)
            self.hint_label.setText(
                "Click card or Space to reveal  ·  1 Again  2 Hard  3 Good  4 Easy  ·  F = focus"
            )
            self.bottom_stack.setCurrentIndex(0)  # reveal button

    def _setup_mc_options(self, card):
        options = (card.distractors[:3] + [card.answer])
        random.shuffle(options)
        self._mc_correct_index = options.index(card.answer)
        c = ThemeManager.instance().colors()
        for btn, opt in zip(self._mc_buttons, options):
            btn.setText(opt)
            btn.setEnabled(True)
            btn.setStyleSheet("")  # reset previous round's color

    def _flip_card(self):
        if self.showing_answer:
            return
        card = self.cards[self.current_index]
        if card.card_type == "multiple_choice":
            return  # MC never uses flip

        self._think_ms      = int((time.perf_counter() - self._think_start) * 1000)
        self.showing_answer = True

        self.card_side_label.setText("ANSWER")
        self._set_card_answer_style()

        if card.card_type == "cloze":
            # Highlight the revealed words in the question
            revealed = _CLOZE_RE.sub(
                lambda m: f"<b style='color:#a6e3a1'>{m.group(1)}</b>",
                card.question,
            )
            self.card_text.setText(revealed)
        else:
            self.card_text.setText(card.answer)

        # Think-time + speed modifier note
        think_s = self._think_ms / 1000
        mod     = SRS.speed_modifier(self._think_ms)
        note    = {1: "  ⚡ Fast (+1)", -1: "  🐢 Slow (−1)", -2: "  🐢🐢 Very slow (−2)"}.get(mod, "")
        self.hint_label.setText(f"⏱  {think_s:.1f}s{note}")

        # Interval previews for each quality button
        ef, interval, reps = card.easiness_factor, card.interval, card.repetitions
        for base_q, lbl in (
            (SRS.AGAIN, self.again_lbl),
            (SRS.HARD,  self.hard_lbl),
            (SRS.GOOD,  self.good_lbl),
            (SRS.EASY,  self.easy_lbl),
        ):
            adj_q = SRS.apply_quality(base_q, self._think_ms)
            lbl.setText(SRS.format_interval(SRS.preview_interval(ef, interval, reps, adj_q)))

        self.bottom_stack.setCurrentIndex(1)  # quality buttons

    def _handle_mc_answer(self, btn_index: int):
        if self._mc_answered:
            return
        self._mc_answered   = True
        self._think_ms      = int((time.perf_counter() - self._think_start) * 1000)
        self.showing_answer = True

        is_correct = (btn_index == self._mc_correct_index)

        c = ThemeManager.instance().colors()
        for i, btn in enumerate(self._mc_buttons):
            btn.setEnabled(False)
            if i == self._mc_correct_index:
                btn.setStyleSheet(f"background-color: {c['green']}; color: {c['btn_text']}; border: none;")
            elif i == btn_index and not is_correct:
                btn.setStyleSheet(f"background-color: {c['red']}; color: {c['btn_text']}; border: none;")

        quality = SRS.GOOD if is_correct else SRS.AGAIN
        if is_correct:
            think_s = self._think_ms / 1000
            if think_s < 3:
                quality = SRS.EASY
            elif think_s > 12:
                quality = SRS.HARD

        self.hint_label.setText("✓ Correct!" if is_correct else "✗ Wrong")
        QTimer.singleShot(1100, lambda: self._apply_quality(quality))

    def _apply_quality(self, base_quality: int):
        if self.current_index >= len(self.cards):
            return
        card = self.cards[self.current_index]

        adj = SRS.apply_quality(base_quality, self._think_ms)
        ef, interval, reps, next_review = SRS.update_card(
            card.easiness_factor, card.interval, card.repetitions, adj
        )
        card.easiness_factor = ef
        card.interval        = interval
        card.repetitions     = reps
        card.next_review     = next_review
        card.last_reviewed   = date.today().isoformat()

        self.counts[base_quality] += 1
        save_decks(self.all_decks)

        self.current_index += 1
        self._show_card()

    def _show_results(self):
        total   = len(self.cards)
        a, h, g, e = (self.counts[k] for k in (SRS.AGAIN, SRS.HARD, SRS.GOOD, SRS.EASY))
        correct = h + g + e
        pct     = int((correct / total) * 100) if total else 0

        self.res_emoji.setText("🎉" if pct >= 70 else "📚")
        self.res_score.setText(f"{correct} / {total} answered correctly  ({pct}%)")
        self.res_breakdown.setText(f"Again: {a}   ·   Hard: {h}   ·   Good: {g}   ·   Easy: {e}")

        today  = date.today()
        future = [
            date.fromisoformat(c.next_review)
            for c in self.deck.cards
            if c.next_review
        ]
        future = [d for d in future if d > today]
        if future:
            days = (min(future) - today).days
            self.res_next.setText(
                "Next cards due tomorrow" if days == 1 else f"Next cards due in {days} days"
            )
        elif any(SRS.is_due(c.next_review) for c in self.deck.cards):
            self.res_next.setText("Some cards are already due again")
        else:
            self.res_next.setText("")

        # Exit focus mode before showing results
        if self._focus_mode:
            self._toggle_focus()

        self.stack.setCurrentIndex(1)

    # ------------------------------------------------------------------ focus

    def _toggle_focus(self):
        self._focus_mode = not self._focus_mode

        hidden = self._focus_mode
        self.progress_label.setVisible(not hidden)
        self.stats_label.setVisible(not hidden)
        self.focus_btn.setVisible(not hidden)   # hide the button itself in focus
        self.progress_bar.setVisible(not hidden)
        self._mem_row_widget.setVisible(not hidden)
        self.hint_label.setVisible(not hidden)

        # Larger card text in focus mode
        c = ThemeManager.instance().colors()
        size = "32px" if self._focus_mode else "22px"
        self.card_text.setStyleSheet(
            f"font-size: {size}; color: {c['text']}; padding: 0 28px; background: transparent;"
        )

        if self._focus_mode:
            self.showMaximized()
        else:
            self.showNormal()
            self.resize(700, 580)

    # ------------------------------------------------------------------ keyboard

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key.Key_Escape and self._focus_mode:
            self._toggle_focus()
            return

        if key == Qt.Key.Key_F:
            self._toggle_focus()
            return

        if self.stack.currentIndex() == 1:  # results page
            super().keyPressEvent(event)
            return

        if key == Qt.Key.Key_Space:
            self._flip_card()

        elif self.showing_answer:
            if key == Qt.Key.Key_1: self._apply_quality(SRS.AGAIN)
            elif key == Qt.Key.Key_2: self._apply_quality(SRS.HARD)
            elif key == Qt.Key.Key_3: self._apply_quality(SRS.GOOD)
            elif key == Qt.Key.Key_4: self._apply_quality(SRS.EASY)

        elif not self.showing_answer:
            # MC keyboard shortcuts
            card = self.cards[self.current_index] if self.current_index < len(self.cards) else None
            if card and card.card_type == "multiple_choice":
                mc_keys = {
                    Qt.Key.Key_1: 0,
                    Qt.Key.Key_2: 1,
                    Qt.Key.Key_3: 2,
                    Qt.Key.Key_4: 3,
                }
                if key in mc_keys:
                    self._handle_mc_answer(mc_keys[key])
                    return

        else:
            super().keyPressEvent(event)
