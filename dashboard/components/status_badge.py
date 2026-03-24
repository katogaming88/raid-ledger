"""Status indicator components — icons + text + color (never color alone).

WCAG 2.1 AA: Color is never the only indicator. Every status uses
an icon, text label, and color together.
"""

from __future__ import annotations

# Status display configuration: (icon, label, css_color)
_STATUS_MAP: dict[str, tuple[str, str, str]] = {
    "pass": ("\u2705", "Pass", "#2e7d32"),    # green checkmark
    "fail": ("\u274c", "Fail", "#c62828"),    # red X
    "flag": ("\u26a0\ufe0f", "Flag", "#ef6c00"),  # orange warning
}


def status_icon(status: str) -> str:
    """Return the icon character for a snapshot status."""
    icon, _, _ = _STATUS_MAP.get(status, ("\u2753", "Unknown", "#757575"))
    return icon


def status_label(status: str) -> str:
    """Return 'Icon Label' string for display (e.g., '✅ Pass')."""
    icon, label, _ = _STATUS_MAP.get(status, ("\u2753", "Unknown", "#757575"))
    return f"{icon} {label}"


def status_color(status: str) -> str:
    """Return the CSS color for a status."""
    _, _, color = _STATUS_MAP.get(status, ("\u2753", "Unknown", "#757575"))
    return color


def reason_display(reason: str) -> str:
    """Convert a reason enum value to a human-readable label."""
    labels = {
        "insufficient_keys": "Not enough M+ keys at level",
        "low_ilvl": "Item level below requirement",
        "manual_fail": "Marked as fail by officer",
        "no_data": "No data available (API issue or missing character)",
        "data_anomaly": "Data looks incorrect",
        "approved_absence": "Approved absence",
        "manual_flag": "Flagged for review by officer",
    }
    return labels.get(reason, reason)
