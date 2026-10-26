"""Literal substring search shared by the explicit OC95 resource whitelists."""

MAX_SEARCH_LENGTH = 120


def normalize_search(value: str | None) -> str | None:
    return (value.strip() or None) if value is not None else None


def search_pattern(value: str | None) -> str | None:
    term = normalize_search(value)
    if term is None:
        return None
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
