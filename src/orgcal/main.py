import datetime as dt
import logging
from typing import Any

import caldav

from orgcal.cache import check_cache_dir, read_cache_file, write_cache_file
from orgcal.events import (
    Event,
    compare_event_with_ical,
    find_remote_event,
    parse_org_event,
    save_event_to_calendar,
    update_remote_event,
)
from orgcal.utils import (
    force_timestamp,
    load_all_headings_from_mixed_list,
    parse_args,
    parse_cutoff_date,
    read_config_file,
    setup_logging,
)


def _load_events(calendar: dict[str, Any]) -> list[Event]:
    """Load and sort events from org files for a calendar config."""
    cutoff_date = parse_cutoff_date(calendar['sync_cutoff'])
    logging.info(f'Sync cutoff date: {cutoff_date}')

    nodes = load_all_headings_from_mixed_list(calendar['org_files'], cutoff_date)
    return sorted(
        map(parse_org_event, nodes),
        key=lambda e: force_timestamp(e.scheduled),
    )


def _load_old_cache(
    calendar_id: str, cutoff_date: dt.date
) -> tuple[dict[str, Any], list[str]]:
    """Load cache file and return (full_cache, list of uids past cutoff)."""
    cache_filename = f'{calendar_id}.yaml'
    cache_file = read_cache_file(cache_filename)

    if not cache_file:
        write_cache_file(cache_filename, {'cache': {}})
        return {}, []

    old_cache = cache_file.get('cache', {})
    old_events = [
        uid
        for uid, event in old_cache.items()
        if event.get('scheduled')
        and _parse_cache_date(event['scheduled']) >= cutoff_date
    ]
    return old_cache, old_events


def _parse_cache_date(date_str: str) -> dt.date:
    """Parse a date string from the cache file."""
    fmt = '%Y-%m-%d %H:%M:%S%z' if ':' in date_str else '%Y-%m-%d'
    return dt.datetime.strptime(date_str, fmt).date()


def _sync_events(
    events: list[Event],
    remote_calendar: Any,
    old_cache: dict[str, Any],
    old_events: list[str],
    delete_remote_events: bool,
) -> dict[str, Any]:
    """Sync events with remote calendar and return the new cache."""
    new_cache: dict[str, Any] = {} if delete_remote_events else dict(old_cache)

    for i, event in enumerate(events):
        time_str = f'{event.scheduled:%Y-%m-%d %H:%M}'
        if event.scheduled and event.duration:
            time_str += f'--{event.scheduled + event.duration:%H:%M}'

        status_string = f'[{i + 1:03}/{len(events):03}] [{time_str}] {event.title}'

        if event.uid in old_events:
            old_events.remove(event.uid)

        new_cache[event.uid] = {
            'title': event.title,
            'scheduled': event.scheduled,
            'duration': event.duration,
            'description': event.description,
        }

        prefix = _sync_single_event(event, remote_calendar)
        logging.info(prefix + status_string)

    if delete_remote_events:
        _delete_old_events(old_events, old_cache, remote_calendar)

    return new_cache


def _sync_single_event(event: Event, remote_calendar: Any) -> str:
    """Sync a single event with the remote calendar. Return status prefix."""
    if remote := find_remote_event(remote_calendar, event.uid):
        if compare_event_with_ical(event, remote):
            logging.debug(f'No changes for event: {event.title}')
            return '= '
        logging.debug(f'Updating event: {event.title}')
        update_remote_event(event, remote)
        return '~ '

    logging.debug(f'Creating event: {event.title}')
    save_event_to_calendar(event, remote_calendar)
    return '+ '


def _delete_old_events(
    old_events: list[str], old_cache: dict[str, Any], remote_calendar: Any
) -> None:
    """Delete events from remote calendar that are no longer in org files."""
    for uid in old_events:
        if remote_event := find_remote_event(remote_calendar, uid):
            logging.info(f'Removing cached event "{old_cache[uid]["title"]}".')
            remote_event.delete()


def process_calendar(
    calendar: dict[str, Any], delete_remote_events: bool = False
) -> None:
    """Synchronize org-mode headings with a remote CalDAV calendar."""
    server_url = calendar['url']
    calendar_id = calendar['id']
    calendar_url = server_url + calendar_id

    logging.info(f'Processing calendar: {calendar_id}')
    cutoff_date = parse_cutoff_date(calendar['sync_cutoff'])
    events = _load_events(calendar)

    old_cache, old_events = _load_old_cache(calendar_id, cutoff_date)

    with caldav.DAVClient(  # type: ignore[operator]
        url=server_url,
        username=calendar['username'],
        password=calendar['password'],
    ) as client:
        remote_calendar = client.calendar(url=calendar_url)
        if not remote_calendar:
            logging.error(f'Calendar not found: {calendar_id}')
            return

        new_cache = _sync_events(
            events, remote_calendar, old_cache, old_events, delete_remote_events
        )

    cache_filename = f'{calendar_id}.yaml'
    write_cache_file(cache_filename, {'cache': new_cache})


def main(
    config_file: str = 'config.yml',
    debug: bool = False,
    delete_remote_events: bool = False,
) -> None:
    """Load config and process each calendar defined in it."""
    try:
        if not (config := read_config_file(config_file)):
            return

        for calendar in config.get('calendars', []):
            process_calendar(calendar, delete_remote_events)

    except Exception as ex:
        if debug:
            logging.exception(ex)
        else:
            logging.error(ex)


def cli() -> None:
    """Entry point for the orgcal command-line tool."""
    try:
        args = parse_args()
        setup_logging(args.debug)
        check_cache_dir()
        main(args.config, args.debug, args.delete_remote)

    except KeyboardInterrupt:
        print()
        logging.info('Exited.')
