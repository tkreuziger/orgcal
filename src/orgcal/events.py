import datetime as dt
import logging
from dataclasses import dataclass, field
from typing import Any
from zoneinfo import ZoneInfo

import caldav
import caldav.lib.error
import orgparse.node

from orgcal.utils import clean_up_heading, get_datetime_from_org

_BERLIN_TZ = ZoneInfo('Europe/Berlin')


@dataclass
class Event:
    uid: str = ''
    title: str = ''
    description: str = ''
    scheduled: dt.datetime | None = None
    duration: dt.timedelta | None = None
    created_at: dt.datetime | dt.date | None = None
    last_modified_at: dt.datetime | dt.date | None = None
    remote_event: Any = field(default=None, repr=False)


def parse_ical_event(remote_event: Any) -> Event:
    """Create an Event from a remote iCalendar object."""
    if not hasattr(remote_event, 'icalendar_component'):
        raise RuntimeError('remote_event does not have icalendar_component attribute')

    ical = remote_event.icalendar_component
    scheduled = ical.get('DTSTART', None)
    dt_end = ical.get('DTEND', None)
    created_at = ical.get('CREATED', None)
    last_modified_at = ical.get('LAST-MODIFIED', None)

    return Event(
        uid=ical['UID'],
        title=ical['SUMMARY'],
        description=ical.get('DESCRIPTION', ''),
        scheduled=scheduled.dt if scheduled else None,
        duration=(dt_end.dt - scheduled.dt) if dt_end and scheduled else None,
        created_at=created_at.dt if created_at else None,
        last_modified_at=last_modified_at.dt if last_modified_at else None,
        remote_event=remote_event,
    )


def parse_org_event(node: orgparse.node.OrgNode) -> Event:
    """Create an Event from an orgparse node."""
    scheduled_start = node.scheduled.start
    scheduled = (
        scheduled_start.replace(tzinfo=_BERLIN_TZ)
        if isinstance(scheduled_start, dt.datetime)
        else scheduled_start
    )

    effort_key = 'EFFORT' if 'EFFORT' in node.properties else 'Effort'
    effort = node.get_property(effort_key, 0)
    duration = _parse_effort(effort)

    uid = node.get_property('ID')
    created_at_raw = node.get_property('CREATED_AT', '')
    last_modified_at_raw = node.get_property('LAST_MODIFIED_AT', '')

    return Event(
        uid=str(uid) if uid else '',
        title=clean_up_heading(node.heading),
        description=node.get_body(),
        scheduled=scheduled,
        duration=duration,
        created_at=get_datetime_from_org(str(created_at_raw), 'CREATED_AT'),
        last_modified_at=get_datetime_from_org(
            str(last_modified_at_raw), 'LAST_MODIFIED_AT'
        ),
    )


def _parse_effort(effort: Any) -> dt.timedelta | None:
    """Parse an effort value into a timedelta."""
    if isinstance(effort, int):
        return dt.timedelta(minutes=effort)
    if isinstance(effort, str) and ':' in effort:
        hours, minutes = effort.strip().split(':')
        return dt.timedelta(hours=int(hours), minutes=int(minutes))
    return None


def find_remote_event(calendar: Any, uid: str) -> Any | None:
    """Look up a remote calendar event by UID, returning None if not found."""
    try:
        result: Any = calendar.event_by_uid(uid)
        return result
    except caldav.lib.error.NotFoundError:
        return None


def find_event(calendar: Any, uid: str) -> Event | None:
    """Find a remote event by UID and return it as an Event, or None."""
    remote_event = find_remote_event(calendar, uid)
    return parse_ical_event(remote_event) if remote_event else None


def save_event_to_calendar(event: Event, calendar: Any) -> None:
    """Save an event as a new entry on the remote calendar."""
    try:
        calendar.save_event(
            uid=event.uid,
            dtstart=event.scheduled,
            dtend=(
                event.scheduled + event.duration
                if event.scheduled and event.duration
                else event.scheduled
            ),
            summary=event.title,
            description=event.description,
        )
    except caldav.lib.error.PutError as ex:
        logging.error(ex)


def _update_ical_datetime(
    ical: Any, key: str, value: dt.datetime | dt.date | None
) -> None:
    """Update an iCalendar datetime field with proper timezone handling."""
    if value is None:
        return

    ical[key].dt = value
    if isinstance(value, dt.datetime):
        ical[key].params['TZID'] = 'Europe/Berlin'
        ical[key].params.pop('VALUE', None)
    else:
        ical[key].params['VALUE'] = 'DATE'
        ical[key].params.pop('TZID', None)


def update_remote_event(event: Event, remote_event: Any) -> None:
    """Update an existing remote event with this event's data."""
    try:
        if not hasattr(remote_event, 'icalendar_component'):
            raise RuntimeError(
                "'remote_event' does not have icalendar_component attribute."
            )

        ical = remote_event.icalendar_component
        ical['SUMMARY'] = event.title
        ical['DESCRIPTION'] = event.description

        _update_ical_datetime(ical, 'DTSTART', event.scheduled)
        _update_ical_datetime(
            ical,
            'DTEND',
            event.scheduled + event.duration
            if event.scheduled and event.duration
            else event.scheduled,
        )

        remote_event.save()
    except caldav.lib.error.PutError as ex:
        logging.error(ex)


def compare_events(event1: Event, event2: Event) -> bool:
    """Return True if two events have identical title, schedule, duration, and description."""
    return (
        event1.title == event2.title
        and event1.scheduled == event2.scheduled
        and event1.duration == event2.duration
        and event1.description == event2.description
    )


def compare_event_with_ical(event: Event, remote_event: Any) -> bool:
    """Return True if this event matches the data on the remote iCalendar object."""
    return compare_events(event, parse_ical_event(remote_event))
