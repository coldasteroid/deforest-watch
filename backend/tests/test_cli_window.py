"""The CLI compositing window must be the length it claims.

`end.replace(day=end.day - days)` cannot cross a month boundary, so any date
in the first fortnight of a month silently produced a short window: 5 November
gave four days. A live Landsat 9 fetch failed on it, since a 16-day revisit
rarely places a scene inside four days, and the failure looked like missing
imagery rather than a bad request.
"""

from datetime import date

import pytest

from deforestwatch.cli import _window


@pytest.mark.parametrize("value", ["2026-11-05", "2026-11-15", "2026-03-02", "2026-01-10", "2026-02-28"])
def test_window_is_always_the_requested_length(value):
    window = _window(value)
    assert (window.end - window.start).days == 14
    assert window.end == date.fromisoformat(value)


def test_window_crosses_a_month_boundary():
    window = _window("2026-11-05")
    assert window.start == date(2026, 10, 22)


def test_window_crosses_a_year_boundary():
    window = _window("2026-01-10")
    assert window.start == date(2025, 12, 27)


def test_window_length_is_configurable():
    assert (_window("2026-06-30", days=75).end - _window("2026-06-30", days=75).start).days == 75
