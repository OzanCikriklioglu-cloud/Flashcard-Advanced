import json
import os
import uuid
from dataclasses import dataclass, field
from typing import List


@dataclass
class Card:
    id: str
    question: str
    answer: str
    # SM-2 spaced repetition fields
    easiness_factor: float = 2.5   # EF ≥ 1.3; higher = reviewed less often
    interval: int = 0              # days until next review (0 = new)
    repetitions: int = 0          # consecutive correct answers
    next_review: str = ""          # ISO date; "" means new card (always due)
    last_reviewed: str = ""        # ISO date of last review session
    # Card type fields
    card_type: str = "basic"       # "basic" | "cloze" | "multiple_choice"
    distractors: List[str] = field(default_factory=list)  # wrong options for MC

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "easiness_factor": self.easiness_factor,
            "interval": self.interval,
            "repetitions": self.repetitions,
            "next_review": self.next_review,
            "last_reviewed": self.last_reviewed,
            "card_type": self.card_type,
            "distractors": self.distractors,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            id=d["id"],
            question=d["question"],
            answer=d["answer"],
            # Use .get() so old JSON files without these fields load fine
            easiness_factor=d.get("easiness_factor", 2.5),
            interval=d.get("interval", 0),
            repetitions=d.get("repetitions", 0),
            next_review=d.get("next_review", ""),
            last_reviewed=d.get("last_reviewed", ""),
            card_type=d.get("card_type", "basic"),
            distractors=d.get("distractors", []),
        )


@dataclass
class Deck:
    id: str
    name: str
    cards: List[Card] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "cards": [c.to_dict() for c in self.cards],
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            id=d["id"],
            name=d["name"],
            cards=[Card.from_dict(c) for c in d.get("cards", [])],
        )


DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flashcards.json")


def load_decks() -> List[Deck]:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Deck.from_dict(d) for d in data]


def save_decks(decks: List[Deck]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([d.to_dict() for d in decks], f, indent=2, ensure_ascii=False)


def new_id() -> str:
    return str(uuid.uuid4())
