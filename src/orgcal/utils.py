import argparse
import datetime as dt
import glob
import logging
import os
from typing import Any
from zoneinfo import ZoneInfo

import orgparse.date
import yaml

_DEFAULT_TODO_KEYWORDS = ['NEXT', 'RUNNING', 'PAUSED', 'WAIT', 'CANCELLED', 'DELEGATED']
_DEFAULT_PRIORITIES = ['A', 'B', 'C', 'D', 'E', 'F', 'G']


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments and return an argparse.Namespace object.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='config.yml', help='Config file')
    parser.add_argument(
        '--delete_remote', action='store_true', help='Delete remote events'
    )
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()


def setup_logging(debug: bool = False) -> None:
    """
    Set up logging.
    """

    format = '[%(asctime)s] [%(levelname)s] %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'

    if debug:
        logging.basicConfig(level=logging.DEBUG, format=format, datefmt=datefmt)
    else:
        logging.basicConfig(level=logging.INFO, format=format, datefmt=datefmt)


def get_datetime_from_org(
    org_timestamp: str, timezone: str = 'Europe/Berlin'
) -> dt.datetime | dt.date | None:
    """
    Get a datetime object from an org timestamp.

    Args:
        org_timestamp (str): The org timestamp to convert to a datetime object.
        timezone (str, optional): The timezone to use for the datetime object. Defaults to 'Europe/Berlin'.

    Returns:
        dt.datetime | None: The datetime object or None if the org timestamp is invalid.
    """

    if org_timestamp.startswith('[') or org_timestamp.startswith('<'):
        org_timestamp = org_timestamp[1:-1]

    dt_object = orgparse.date.OrgDate.from_str(org_timestamp).start

    if isinstance(dt_object, dt.datetime):
        result: dt.datetime = dt_object.replace(tzinfo=ZoneInfo(timezone))
        return result
    elif isinstance(dt_object, dt.date):
        return dt_object
    else:
        return None


def clean_up_heading(
    heading: str,
    todo_keywords: list[str] | None = None,
    priorities: list[str] | None = None,
) -> str:
    """
    Remove all todo keywords and priority from heading.
    Explicit values for `todo_keywords` and `priorities` can be specified.
    If none are specified, some default values will be used.

    Args:
        heading (str): The heading to clean up.
        todo_keywords (list[str], optional): The todo keywords to remove from the heading.
        priorities (list[str], optional): The priorities to remove from the heading.

    Returns:
        str: The cleaned up heading.
    """

    todo_keywords = todo_keywords or _DEFAULT_TODO_KEYWORDS
    priorities = priorities or _DEFAULT_PRIORITIES

    for keyword in todo_keywords:
        if heading.startswith(keyword):
            heading = heading.replace(keyword, '').strip()

    for priority in priorities:
        if heading.startswith(f'[#{priority}]'):
            heading = heading.replace(f'[#{priority}]', '').strip()

    return heading


def _collect_org_files(paths: list[str]) -> list[str]:
    """Collect all .org file paths from a mixed list of files and directories."""
    files: list[str] = []
    for path in paths:
        if os.path.isdir(path):
            files.extend(glob.glob(os.path.join(path, '*.org')))
        elif os.path.isfile(path):
            files.append(path)
    return files


def _load_headings_from_file(filename: str, cutoff_date: dt.date) -> list[Any]:
    """Load scheduled headings from a single org file, filtered by cutoff date."""
    if not filename.endswith('.org'):
        logging.error(f'Only org files are supported: {filename}')
        return []

    nodes = []
    root_node = orgparse.load(filename)

    for node in root_node[1:]:
        if not node.scheduled:
            continue
        day = (
            node.scheduled.start.date()
            if isinstance(node.scheduled.start, dt.datetime)
            else node.scheduled.start
        )
        if day >= cutoff_date:
            nodes.append(node)

    return nodes


def load_all_headings_from_mixed_list(
    mixed_list: list[str], cutoff_date: dt.date
) -> list[Any]:
    """Load all scheduled headings from org files/directories, filtered by cutoff date."""
    files = _collect_org_files(mixed_list)
    nodes: list[Any] = []
    for filename in files:
        nodes.extend(_load_headings_from_file(filename, cutoff_date))
    return nodes


def read_config_file(filename: str) -> dict[str, Any] | None:
    """
    Read a YAML config file and return the contents.

    Args:
        filename (str): The name of the YAML config file to read.

    Returns:
        dict | None: The contents of the config file, or None if the file could not be found or read.
    """

    if filename == 'config.yml':
        logging.info('Using default config file.')

    if not os.path.exists(filename):
        logging.error(f'The specified config file could not be found: {filename}')
        return None

    if not os.path.isfile(filename):
        logging.error(f'The specified path is not a file: {filename}')
        return None

    if not (filename.endswith('.yml') or filename.endswith('.yaml')):
        logging.error(f'Only YAML files are supported: {filename}')
        return None

    with open(filename) as config_file:
        result: dict[str, Any] = yaml.safe_load(config_file)
        return result


def parse_cutoff_date(date_str: str) -> dt.date:
    """
    Parse a date string and return a date object.

    Args:
        date_str (str): The date string to parse.

    Returns:
        dt.date: The date object.
    """

    if date_str == 'now':
        return dt.date.today()
    elif date_str == 'thisweek':
        return dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
    else:
        return dt.datetime.strptime(date_str, '%Y-%m-%d').date()


def force_timestamp(scheduled: dt.datetime | dt.date | None) -> dt.datetime:
    """
    Forcibly turn a date or None object into a timestamp object for sorting.

    Args:
        scheduled (dt.datetime | dt.date | None): The date or None object to convert.

    Returns:
        dt.datetime: The timestamp object.
    """

    if isinstance(scheduled, dt.datetime):
        return scheduled
    elif isinstance(scheduled, dt.date):
        date = dt.datetime(scheduled.year, scheduled.month, scheduled.day)
        result: dt.datetime = date.replace(tzinfo=ZoneInfo('Europe/Berlin'))
        return result
    else:
        return dt.datetime.now()
