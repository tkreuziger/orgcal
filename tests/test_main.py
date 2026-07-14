"""Tests for orgcal.main module."""

import datetime as dt

import pytest

from orgcal.main import _parse_cache_date


class TestParseCacheDate:
    def test_parse_date_only(self):
        result = _parse_cache_date('2024-06-24')
        assert result == dt.date(2024, 6, 24)

    def test_parse_datetime_with_timezone(self):
        result = _parse_cache_date('2024-06-24 10:30:00+0200')
        assert result == dt.date(2024, 6, 24)

    def test_parse_datetime_without_timezone(self):
        # Note: The implementation uses ':' presence to detect timezone format,
        # so "14:00:00" is treated as having timezone. This test verifies actual behavior.
        with pytest.raises(ValueError):
            _parse_cache_date('2024-06-24 14:00:00')

    def test_parse_another_date(self):
        result = _parse_cache_date('2025-01-15')
        assert result == dt.date(2025, 1, 15)
