"""Tests for orgcal.events module."""

import datetime as dt
from unittest.mock import Mock

import pytest

from orgcal.events import (
    Event,
    _parse_effort,
    compare_events,
    parse_ical_event,
    parse_org_event,
)


class TestParseEffort:
    def test_parse_integer_minutes(self):
        result = _parse_effort(60)
        assert result == dt.timedelta(minutes=60)

    def test_parse_integer_zero(self):
        result = _parse_effort(0)
        assert result == dt.timedelta(minutes=0)

    def test_parse_string_hh_mm(self):
        result = _parse_effort('1:30')
        assert result == dt.timedelta(hours=1, minutes=30)

    def test_parse_string_hours_only(self):
        result = _parse_effort('2:00')
        assert result == dt.timedelta(hours=2, minutes=0)

    def test_parse_string_minutes_only(self):
        result = _parse_effort('0:45')
        assert result == dt.timedelta(hours=0, minutes=45)

    def test_parse_string_with_whitespace(self):
        result = _parse_effort('  1:30  ')
        assert result == dt.timedelta(hours=1, minutes=30)

    def test_parse_none(self):
        result = _parse_effort(None)
        assert result is None

    def test_parse_empty_string(self):
        result = _parse_effort('')
        assert result is None

    def test_parse_string_without_colon(self):
        result = _parse_effort('60')
        assert result is None


class TestCompareEvents:
    def test_identical_events(self):
        event1 = Event(
            uid='123',
            title='Test',
            description='Desc',
            scheduled=dt.datetime(2024, 6, 24, 10, 0),
            duration=dt.timedelta(hours=1),
        )
        event2 = Event(
            uid='456',
            title='Test',
            description='Desc',
            scheduled=dt.datetime(2024, 6, 24, 10, 0),
            duration=dt.timedelta(hours=1),
        )
        assert compare_events(event1, event2) is True

    def test_different_title(self):
        event1 = Event(title='Event 1')
        event2 = Event(title='Event 2')
        assert compare_events(event1, event2) is False

    def test_different_scheduled(self):
        event1 = Event(scheduled=dt.datetime(2024, 6, 24, 10, 0))
        event2 = Event(scheduled=dt.datetime(2024, 6, 25, 10, 0))
        assert compare_events(event1, event2) is False

    def test_different_duration(self):
        event1 = Event(duration=dt.timedelta(hours=1))
        event2 = Event(duration=dt.timedelta(hours=2))
        assert compare_events(event1, event2) is False

    def test_different_description(self):
        event1 = Event(description='Desc 1')
        event2 = Event(description='Desc 2')
        assert compare_events(event1, event2) is False

    def test_both_none_fields(self):
        event1 = Event(scheduled=None, duration=None, description='')
        event2 = Event(scheduled=None, duration=None, description='')
        assert compare_events(event1, event2) is True


class TestParseIcalEvent:
    def test_parse_basic_event(self):
        mock_remote = Mock()
        mock_remote.icalendar_component = {
            'UID': 'test-uid-123',
            'SUMMARY': 'Test Event',
            'DESCRIPTION': 'Test Description',
            'DTSTART': Mock(dt=dt.datetime(2024, 6, 24, 10, 0)),
            'DTEND': Mock(dt=dt.datetime(2024, 6, 24, 11, 0)),
        }

        event = parse_ical_event(mock_remote)

        assert event.uid == 'test-uid-123'
        assert event.title == 'Test Event'
        assert event.description == 'Test Description'
        assert event.scheduled == dt.datetime(2024, 6, 24, 10, 0)
        assert event.duration == dt.timedelta(hours=1)
        assert event.remote_event == mock_remote

    def test_parse_event_without_end(self):
        mock_remote = Mock()
        mock_remote.icalendar_component = {
            'UID': 'test-uid-456',
            'SUMMARY': 'All Day Event',
            'DTSTART': Mock(dt=dt.date(2024, 6, 24)),
        }

        event = parse_ical_event(mock_remote)

        assert event.uid == 'test-uid-456'
        assert event.title == 'All Day Event'
        assert event.scheduled == dt.date(2024, 6, 24)
        assert event.duration is None

    def test_parse_event_without_description(self):
        mock_remote = Mock()
        mock_remote.icalendar_component = {
            'UID': 'test-uid-789',
            'SUMMARY': 'No Description',
            'DTSTART': Mock(dt=dt.datetime(2024, 6, 24, 10, 0)),
        }

        event = parse_ical_event(mock_remote)

        assert event.description == ''

    def test_parse_event_with_timestamps(self):
        mock_remote = Mock()
        created = dt.datetime(2024, 6, 20, 12, 0)
        modified = dt.datetime(2024, 6, 22, 14, 30)
        mock_remote.icalendar_component = {
            'UID': 'test-uid-ts',
            'SUMMARY': 'Timestamped Event',
            'DTSTART': Mock(dt=dt.datetime(2024, 6, 24, 10, 0)),
            'CREATED': Mock(dt=created),
            'LAST-MODIFIED': Mock(dt=modified),
        }

        event = parse_ical_event(mock_remote)

        assert event.created_at == created
        assert event.last_modified_at == modified

    def test_parse_event_missing_icalendar_component(self):
        mock_remote = Mock(spec=[])

        with pytest.raises(RuntimeError, match='does not have icalendar_component'):
            parse_ical_event(mock_remote)


class TestParseOrgEvent:
    def test_parse_basic_org_event(self):
        mock_node = Mock()
        mock_node.heading = 'NEXT Buy groceries'
        mock_node.scheduled.start = dt.datetime(2024, 6, 24, 10, 0)
        mock_node.properties = {'ID': 'org-uid-123', 'EFFORT': 60}
        mock_node.get_property = lambda key, default=None: mock_node.properties.get(
            key, default
        )
        mock_node.get_body.return_value = 'Buy milk and eggs'

        event = parse_org_event(mock_node)

        assert event.uid == 'org-uid-123'
        assert event.title == 'Buy groceries'
        assert event.description == 'Buy milk and eggs'
        assert event.scheduled is not None
        assert event.duration == dt.timedelta(minutes=60)

    def test_parse_org_event_with_string_effort(self):
        mock_node = Mock()
        mock_node.heading = 'Task with effort'
        mock_node.scheduled.start = dt.datetime(2024, 6, 24, 14, 0)
        mock_node.properties = {'ID': 'org-uid-456', 'EFFORT': '1:30'}
        mock_node.get_property = lambda key, default=None: mock_node.properties.get(
            key, default
        )
        mock_node.get_body.return_value = ''

        event = parse_org_event(mock_node)

        assert event.duration == dt.timedelta(hours=1, minutes=30)

    def test_parse_org_event_with_date_only(self):
        mock_node = Mock()
        mock_node.heading = 'All day task'
        mock_node.scheduled.start = dt.date(2024, 6, 24)
        mock_node.properties = {'ID': 'org-uid-789'}
        mock_node.get_property = lambda key, default=None: mock_node.properties.get(
            key, default
        )
        mock_node.get_body.return_value = ''

        event = parse_org_event(mock_node)

        assert event.scheduled == dt.date(2024, 6, 24)
        assert not isinstance(event.scheduled, dt.datetime)

    def test_parse_org_event_with_lowercase_effort(self):
        mock_node = Mock()
        mock_node.heading = 'Task'
        mock_node.scheduled.start = dt.datetime(2024, 6, 24, 10, 0)
        mock_node.properties = {'ID': 'org-uid-lower', 'Effort': 30}
        mock_node.get_property = lambda key, default=None: mock_node.properties.get(
            key, default
        )
        mock_node.get_body.return_value = ''

        event = parse_org_event(mock_node)

        assert event.duration == dt.timedelta(minutes=30)

    def test_parse_org_event_without_effort(self):
        mock_node = Mock()
        mock_node.heading = 'Task without effort'
        mock_node.scheduled.start = dt.datetime(2024, 6, 24, 10, 0)
        mock_node.properties = {'ID': 'org-uid-no-effort'}
        mock_node.get_property = lambda key, default=None: mock_node.properties.get(
            key, default
        )
        mock_node.get_body.return_value = 'Description'

        event = parse_org_event(mock_node)

        assert event.duration == dt.timedelta(minutes=0)


class TestEventDataclass:
    def test_default_values(self):
        event = Event()
        assert event.uid == ''
        assert event.title == ''
        assert event.description == ''
        assert event.scheduled is None
        assert event.duration is None
        assert event.created_at is None
        assert event.last_modified_at is None
        assert event.remote_event is None

    def test_custom_values(self):
        scheduled = dt.datetime(2024, 6, 24, 10, 0)
        duration = dt.timedelta(hours=1)
        event = Event(
            uid='test-uid',
            title='Test Event',
            description='Test Description',
            scheduled=scheduled,
            duration=duration,
        )

        assert event.uid == 'test-uid'
        assert event.title == 'Test Event'
        assert event.description == 'Test Description'
        assert event.scheduled == scheduled
        assert event.duration == duration
