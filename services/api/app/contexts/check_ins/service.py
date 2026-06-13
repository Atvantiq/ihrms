"""Check-in helpers (pure)."""

_MOOD_LABELS = {1: "struggling", 2: "low", 3: "okay", 4: "good", 5: "great"}


def mood_label(mood: int) -> str:
    return _MOOD_LABELS.get(mood, "okay")
