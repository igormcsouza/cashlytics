"""Unit tests for the pure month-projection helpers used by the expense service."""

from src.expense.month import (
    home_month,
    is_valid_month,
    month_status_id,
    months_diff,
    project_deadline,
)


def test_is_valid_month():
    assert is_valid_month("2026-07") is True
    assert is_valid_month("2026-01") is True
    assert is_valid_month("2026-12") is True
    assert is_valid_month("2026-7") is False
    assert is_valid_month("not-a-month") is False
    assert is_valid_month("2026-07-01") is False


def test_is_valid_month_rejects_out_of_range_month():
    assert is_valid_month("2026-13") is False
    assert is_valid_month("2026-00") is False


def test_home_month():
    assert home_month("2026-07-15") == "2026-07"


def test_project_deadline_same_day():
    assert project_deadline("2026-07-15", "2026-08") == "2026-08-15"


def test_project_deadline_clamps_to_shorter_month():
    # 2026 is not a leap year: February has 28 days.
    assert project_deadline("2026-01-31", "2026-02") == "2026-02-28"


def test_project_deadline_clamps_on_leap_year():
    assert project_deadline("2024-01-31", "2024-02") == "2024-02-29"


def test_month_status_id():
    assert month_status_id("abc-123", "2026-07") == "abc-123#2026-07"


def test_months_diff_same_month():
    assert months_diff("2026-07", "2026-07") == 0


def test_months_diff_forward_within_year():
    assert months_diff("2026-07", "2026-10") == 3


def test_months_diff_forward_across_year_boundary():
    assert months_diff("2026-11", "2027-02") == 3


def test_months_diff_backward_is_negative():
    assert months_diff("2026-07", "2026-05") == -2
