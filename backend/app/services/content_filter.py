"""Content filter: prompt-injection protection and AI response sanitization.

No unfiltered LLM output reaches the player (Master Architecture §9.9/§13.3):
meta-mentions ("as an AI") are stripped, sentences echoing the system prompt are
dropped, injection attempts are flagged, and length is capped. The checks are
deliberately lightweight pattern matching — no NLP dependencies in the MVP.
"""

import re
from typing import ClassVar

from app.schemas.challenge import ChallengeDefinition, ValidationResult
from app.schemas.prompt import InjectionRisk
from app.services.constraint_engine import ConstraintEngine

# Responses that self-identify as AI give away the game (Master Architecture §3.2).
_META_PATTERNS = [
    "as an AI",
    "as a language model",
    "I'm an AI",
    "I'm a language model",
    "as an artificial intelligence",
    "I don't have feelings",
    "I'm not capable of",
]

# Responses that echo instructions or attempt to inject giveaways (Master Architecture §13.3).
_INJECTION_PATTERNS = [
    "ignore all previous instructions",
    "new instructions:",
    "system prompt",
    "you are now",
    "you are a different",
]

# Leakage markers: the injection patterns plus first-person instruction references.
_LEAKAGE_PATTERNS = _INJECTION_PATTERNS + [
    "my instructions",
    "my prompt",
    "i was instructed",
    "as instructed",
]

_PUNCT = ",.;:!?"


def _compile(pattern: str) -> re.Pattern[str]:
    """Escape a literal pattern; apostrophes match straight or curly variants."""
    body = r"['\u2019]".join(re.escape(part) for part in pattern.split("'"))
    return re.compile(body, re.IGNORECASE)


class ContentFilter:
    """Sanitizes raw AI responses before they are stored or shown to players."""

    META_PATTERNS: ClassVar[list[str]] = list(_META_PATTERNS)
    INJECTION_PATTERNS: ClassVar[list[str]] = list(_INJECTION_PATTERNS)
    LEAKAGE_PATTERNS: ClassVar[list[str]] = list(_LEAKAGE_PATTERNS)
    MAX_RESPONSE_LENGTH: ClassVar[int] = 500

    def __init__(self) -> None:
        self._meta_re = [_compile(p) for p in self.META_PATTERNS]
        self._injection_re = [_compile(p) for p in self.INJECTION_PATTERNS]
        self._leakage_re = [_compile(p) for p in self.LEAKAGE_PATTERNS]
        self._constraint_engine = ConstraintEngine()

    # ---------------------------------------------------------------------------
    # Detection

    def check_meta_mentions(self, text: str) -> list[str]:
        """The meta-mention patterns found in `text` (empty when clean)."""
        return [
            pattern
            for pattern, regex in zip(self.META_PATTERNS, self._meta_re)
            if regex.search(text)
        ]

    def validate_no_meta_mentions(self, text: str) -> bool:
        """True when the response never self-identifies as an AI."""
        return not self.check_meta_mentions(text)

    def check_prompt_injection(self, text: str) -> InjectionRisk:
        """Flag responses that echo or attempt to inject system instructions."""
        matched = [
            pattern
            for pattern, regex in zip(self.INJECTION_PATTERNS, self._injection_re)
            if regex.search(text)
        ]
        return InjectionRisk(is_injection=bool(matched), matched_patterns=matched)

    # ---------------------------------------------------------------------------
    # Sanitization

    def strip_system_prompt_leakage(self, text: str) -> str:
        """Drop sentences that echo system-prompt content (whole-sentence removal:
        the rest of the entry is unrelated to the challenge and would read as broken)."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        kept = [s for s in sentences if not any(rx.search(s) for rx in self._leakage_re)]
        return " ".join(kept)

    def sanitize_ai_response(self, raw: str, max_length: int = MAX_RESPONSE_LENGTH) -> str:
        """Strip meta-mentions and leakage, collapse artifacts, truncate to `max_length`."""
        text = self.strip_system_prompt_leakage(raw)
        for regex in self._meta_re:
            text = regex.sub("", text)
        return self._truncate(self._cleanup(text), max_length)

    def sanitize(self, raw: str, max_length: int = MAX_RESPONSE_LENGTH) -> str:
        """Alias for `sanitize_ai_response` (Implementation Guide §5.6 naming)."""
        return self.sanitize_ai_response(raw, max_length)

    def validate_response(self, raw: str, challenge: ChallengeDefinition) -> ValidationResult:
        """Full gate: meta mentions, injection, length, and challenge constraints."""
        errors: list[str] = []
        for mention in self.check_meta_mentions(raw):
            errors.append(f"contains meta-mention: '{mention}'")
        injection = self.check_prompt_injection(raw)
        if injection.is_injection:
            errors.append(f"possible prompt injection: '{injection.matched_patterns[0]}'")
        if len(raw) > self.MAX_RESPONSE_LENGTH:
            errors.append(f"response exceeds {self.MAX_RESPONSE_LENGTH} characters ({len(raw)})")
        constraints = self._constraint_engine.validate(raw, challenge.constraints)
        errors.extend(constraints.hard_violations)
        return ValidationResult(valid=not errors, errors=errors)

    # ---------------------------------------------------------------------------
    # Internals

    def _cleanup(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(rf"\s+([{re.escape(_PUNCT)}])", r"\1", text)
        text = re.sub(r"^[\s,;:\u2013\u2014-]+", "", text)
        text = re.sub(r"[\s,;:\u2013\u2014-]+$", "", text)
        return text.strip()

    @staticmethod
    def _truncate(text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        cut = text[:max_length]
        boundary = cut.rfind(" ")
        if boundary > max_length // 2:
            cut = cut[:boundary]
        return cut.strip()
