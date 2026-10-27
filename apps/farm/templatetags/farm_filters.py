"""Template helpers for farm durations."""

from django import template

register = template.Library()


def _to_days(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_days(days):
    if days is None:
        return "—"
    unit = "day" if days == 1 else "days"
    label = f"{days:,} {unit}"
    if days >= 365:
        return f"{label} (~{days / 365:.1f} years)"
    return label


@register.filter
def days_duration(value):
    """Render a day count, adding a year estimate for long durations."""
    return _format_days(_to_days(value))


@register.filter
def days_range(min_days, max_days):
    """Render a day range; large ranges show years for both endpoints."""
    low, high = _to_days(min_days), _to_days(max_days)
    if low is None or high is None:
        return "—"
    if low >= 365 or high >= 365:
        return f"{_format_days(low)} – {_format_days(high)}"
    return f"{low:,}–{high:,} days"
