"""Constraint engine: validates entries against a challenge's constraints.

Hard violations block submission; soft violations only inform scoring and
humanity tracking. The linguistic checks (rhyme, adjectives) are deliberately
lightweight heuristics — no NLP dependencies in the MVP.
"""

import re

from app.schemas.challenge import Constraint, ConstraintResult

# Common emoji blocks (excludes variation selector U+FE0F / ZWJ to avoid double counting).
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002B00-\U00002BFF\U0001F900-\U0001F9FF]"
)

# Small built-in list of frequent English adjectives for the soft no_adjectives check.
_ADJECTIVES = frozenset(
    ["good", "bad", "big", "small", "large", "great", "huge", "tiny", "little", "new", "old", "young", "hot", "cold", "warm", "cool", "fast", "slow", "quick", "late", "early", "happy", "sad", "angry", "calm", "easy", "hard", "tough", "soft", "nice", "kind", "mean", "funny", "boring", "interesting", "amazing", "awesome", "terrible", "awful", "horrible", "lovely", "pretty", "ugly", "beautiful", "smart", "dumb", "stupid", "clever", "brave", "shy", "loud", "silent", "strange", "weird", "perfect", "wrong", "right", "real", "fake", "true", "false", "sweet", "sour", "bitter", "salty", "spicy", "crispy", "fluffy", "soggy", "fresh", "stale", "rich", "poor", "cheap", "expensive", "strong", "weak", "heavy", "light", "dark", "bright", "dull", "shiny", "dirty", "clean", "wet", "dry", "thick", "thin", "long", "short", "tall", "wide", "narrow", "deep", "full", "empty", "open", "closed", "free", "busy", "lazy", "quiet", "proud", "humble", "honest", "rude", "polite", "silly", "serious", "dramatic"]
)


def _last_word(clause: str) -> str:
    words = clause.strip().split()
    return words[-1].strip(".,!?;:'\"()").lower() if words else ""


def _rhymes(a: str, b: str) -> bool:
    if len(a) < 2 or len(b) < 2:
        return False
    return a[-3:] == b[-3:] if len(a) >= 3 and len(b) >= 3 else a[-2:] == b[-2:]


class ConstraintEngine:
    """Validates an entry against a list of constraints, splitting hard/soft violations."""

    def validate(self, entry: str, constraints: list[Constraint]) -> ConstraintResult:
        hard: list[str] = []
        soft: list[str] = []
        for constraint in constraints:
            handler = getattr(self, f"_check_{constraint.type}")
            violation = handler(entry, constraint)
            if violation:
                (hard if constraint.is_hard else soft).append(violation)
        return ConstraintResult(valid=not hard, hard_violations=hard, soft_violations=soft)

    def _check_max_words(self, entry: str, constraint: Constraint) -> str | None:
        count = len(entry.split())
        limit = int(constraint.value)  # type: ignore[arg-type]
        if count > limit:
            return f"too many words ({count} > {limit})"
        return None

    def _check_max_characters(self, entry: str, constraint: Constraint) -> str | None:
        count = len(entry)
        limit = int(constraint.value)  # type: ignore[arg-type]
        if count > limit:
            return f"too many characters ({count} > {limit})"
        return None

    def _check_must_include_theme(self, entry: str, constraint: Constraint) -> str | None:
        theme = str(constraint.value or "").lower()
        if theme and theme not in entry.lower():
            return f"must mention '{theme}'"
        return None

    def _check_exactly_n_emojis(self, entry: str, constraint: Constraint) -> str | None:
        expected = int(constraint.value)  # type: ignore[arg-type]
        found = len(_EMOJI_RE.findall(entry))
        if found != expected:
            return f"expected exactly {expected} emoji(s), found {found}"
        return None

    def _check_no_letter_e(self, entry: str, constraint: Constraint) -> str | None:
        if "e" in entry.lower():
            return "contains the letter 'e'"
        return None

    def _check_one_sentence_only(self, entry: str, constraint: Constraint) -> str | None:
        sentences = [part for part in re.split(r"[.!?]+", entry) if part.strip()]
        if len(sentences) > 1:
            return "must be a single sentence"
        return None

    def _check_must_rhyme(self, entry: str, constraint: Constraint) -> str | None:
        clauses = [part for part in re.split(r"[,.!?;\n]+", entry) if part.strip()]
        finals = [_last_word(clause) for clause in clauses]
        finals = [word for word in finals if len(word) >= 2]
        if len(finals) >= 2 and any(
            _rhymes(finals[i], finals[j])
            for i in range(len(finals))
            for j in range(i + 1, len(finals))
        ):
            return None
        return "does not appear to rhyme"

    def _check_no_adjectives(self, entry: str, constraint: Constraint) -> str | None:
        found = [
            word.strip(".,!?;:'\"()").lower()
            for word in entry.split()
            if word.strip(".,!?;:'\"()").lower() in _ADJECTIVES
        ]
        if found:
            return f"contains adjective(s): {', '.join(sorted(set(found)))}"
        return None
