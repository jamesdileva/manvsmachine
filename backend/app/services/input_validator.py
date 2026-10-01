"""Input validation per challenge input type."""

from app.schemas.challenge import ValidationResult

VALID_INPUT_TYPES = {"text_single_line", "text_multi_line"}


class InputValidator:
    """Rejects empty entries and enforces structural input-type rules."""

    def validate(self, entry: str | None, input_type: str) -> ValidationResult:
        if input_type not in VALID_INPUT_TYPES:
            return ValidationResult(valid=False, errors=[f"unknown input type: {input_type}"])
        if entry is None or not entry.strip():
            return ValidationResult(valid=False, errors=["entry is empty"])
        errors: list[str] = []
        if input_type == "text_single_line" and "\n" in entry:
            errors.append("single-line input must not contain newlines")
        return ValidationResult(valid=not errors, errors=errors)
