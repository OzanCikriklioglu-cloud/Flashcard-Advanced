import math
from datetime import date, timedelta

# Base quality constants
AGAIN = 0   # complete fail / didn't know
HARD  = 2   # knew it but struggled
GOOD  = 4   # knew it correctly
EASY  = 5   # trivially easy


def speed_modifier(think_ms: int) -> int:
    """Quality modifier based on time taken to flip the card."""
    s = think_ms / 1000
    if s < 3:
        return 1      # very fast → easier than rated
    elif s < 8:
        return 0      # normal pace → no change
    elif s < 15:
        return -1     # slow → harder than rated
    else:
        return -2     # very slow → much harder


def apply_quality(base: int, think_ms: int) -> int:
    """
    Adjust quality score with speed modifier.
    AGAIN and EASY are never adjusted (they are clear signals).
    Result is clamped to [0, 5].
    """
    if base in (AGAIN, EASY):
        return base
    return max(0, min(5, base + speed_modifier(think_ms)))


def update_card(ef: float, interval: int, reps: int, quality: int):
    """
    SM-2 algorithm core.

    Args:
        ef:       easiness factor (≥ 1.3, starts at 2.5)
        interval: current interval in days
        reps:     consecutive correct answers
        quality:  0–5 rating

    Returns:
        (new_ef, new_interval, new_reps, next_review_iso_date_str)
    """
    if quality < 3:
        # Failed — reset streak, review again tomorrow
        reps = 0
        interval = 1
    else:
        # Passed — advance interval
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ef)
        reps += 1

    # Update easiness factor
    ef = ef + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    ef = max(1.3, round(ef, 4))

    next_review = (date.today() + timedelta(days=interval)).isoformat()
    return ef, interval, reps, next_review


def preview_interval(ef: float, interval: int, reps: int, quality: int) -> int:
    """Return the interval that would result from a given quality, without modifying state."""
    _, days, _, _ = update_card(ef, interval, reps, quality)
    return days


def forgetting_prob(last_reviewed: str, interval: int, ef: float) -> float:
    """
    Estimate probability of forgetting using the Ebbinghaus forgetting curve.

    Formula: R = e^(-t / S)  →  P(forget) = 1 - R
    where S (memory stability) ≈ interval × EF

    Returns a float in [0.0, 1.0].
    """
    if not last_reviewed or interval == 0:
        return 1.0   # new card — assume forgotten
    try:
        days_since = (date.today() - date.fromisoformat(last_reviewed)).days
    except ValueError:
        return 1.0

    stability = interval * ef
    if stability <= 0:
        return 1.0

    retention = math.exp(-days_since / stability)
    return round(1.0 - retention, 4)


def is_due(next_review: str) -> bool:
    """Return True if the card is new (no next_review) or due today."""
    if not next_review:
        return True
    try:
        return date.fromisoformat(next_review) <= date.today()
    except ValueError:
        return True


def due_count(deck) -> int:
    """Count how many cards in a deck are due for review."""
    return sum(1 for c in deck.cards if is_due(c.next_review))


def format_interval(days: int) -> str:
    """Human-readable interval: '<1d', '3d', '2mo', '1y'."""
    if days <= 0:
        return "<1d"
    if days == 1:
        return "1d"
    if days < 31:
        return f"{days}d"
    if days < 365:
        months = max(1, round(days / 30))
        return f"{months}mo"
    years = max(1, round(days / 365))
    return f"{years}y"
