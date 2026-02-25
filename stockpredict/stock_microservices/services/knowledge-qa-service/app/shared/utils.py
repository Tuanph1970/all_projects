"""Text processing utilities."""
import re


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to max_length, breaking at word boundaries."""
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.8:
        truncated = truncated[:last_space]
    return truncated + "..."


def clean_text(text: str) -> str:
    """Clean text by removing excessive whitespace."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()
