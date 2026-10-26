"""Pure GK9 text functions, independently unit-testable."""

import re

MAX_INPUT_LENGTH = 1200
TELEGRAM_SAFE_LENGTH = 3800

CHANGE_CASE = "Change Case"
COUNT_WORDS = "Count Words"
CLEAN_TEXT = "Clean Text"


def clean_text(text: str) -> str:
    """Collapse horizontal whitespace and remove empty lines."""
    lines = [re.sub(r"[^\S\r\n]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _telegram_length(text: str) -> int:
    """Measure Telegram's UTF-16 message length, including emoji."""
    return len(text.encode("utf-16-le")) // 2


def process_text(tool: str, text: str) -> str:
    """Apply a user-selected text tool, returning a ready-to-send answer."""
    if not text.strip():
        return "Please send some non-empty text."
    if len(text) > MAX_INPUT_LENGTH:
        return (
            f"Your message is too long. Please send up to "
            f"{MAX_INPUT_LENGTH} characters."
        )

    if tool == CHANGE_CASE:
        response = (
            f"UPPERCASE:\n{text.upper()}\n\n"
            f"lowercase:\n{text.lower()}\n\n"
            f"Title Case:\n{text.title()}"
        )
    elif tool == COUNT_WORDS:
        words = len(text.split())
        characters = len(text)
        without_whitespace = sum(not char.isspace() for char in text)
        lines = max(1, len(text.splitlines()))
        response = (
            f"Words: {words}\n"
            f"Characters (including spaces): {characters}\n"
            f"Characters (excluding whitespace): {without_whitespace}\n"
            f"Lines: {lines}"
        )
    elif tool == CLEAN_TEXT:
        cleaned = clean_text(text)
        response = f"Cleaned text:\n{cleaned}"
    else:
        return "Please choose one of the three text tools."

    if _telegram_length(response) > TELEGRAM_SAFE_LENGTH:
        return "Your text expands too much after conversion. Please send shorter text."
    return response
