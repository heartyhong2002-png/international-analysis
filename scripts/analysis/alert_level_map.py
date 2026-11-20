"""Map display alert labels to DB evidence-layer vocabulary.

Korean labels from ``calculate_alert_assessment`` are display-facing.
Official ``alert_events.alert_level`` uses only WATCH | WARNING | CRITICAL.
``확인 필요`` and ``관찰`` do not raise an alert_event — scores/gaps may still
be persisted, and human review remains required.
"""

from __future__ import annotations

# Display (Korean) → DB vocab or None (no alert_event)
DISPLAY_TO_DB_ALERT = {
    "주의": "WATCH",
    "경보": "WARNING",
    "고경보": "CRITICAL",
    "WATCH": "WATCH",
    "WARNING": "WARNING",
    "CRITICAL": "CRITICAL",
    # Explicit non-raising states
    "관찰": None,
    "확인 필요": None,
    "NORMAL": None,
    "INSUFFICIENT_EVIDENCE": None,
}

ALLOWED_DB_ALERT_LEVELS = frozenset({"WATCH", "WARNING", "CRITICAL"})


def to_db_alert_level(display_level: str | None) -> str | None:
    """Return WATCH/WARNING/CRITICAL or None when no alert_event should be written."""
    if display_level is None:
        return None
    key = str(display_level).strip()
    if key in DISPLAY_TO_DB_ALERT:
        return DISPLAY_TO_DB_ALERT[key]
    upper = key.upper()
    if upper in ALLOWED_DB_ALERT_LEVELS:
        return upper
    return None


def should_raise_alert(display_level: str | None) -> bool:
    return to_db_alert_level(display_level) is not None
