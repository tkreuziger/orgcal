import logging
import os
from typing import Any

import yaml

_CACHE_DIR = '.orgcal_cache'


def check_cache_dir() -> None:
    """Create the cache directory if it does not exist."""
    if not os.path.exists(_CACHE_DIR):
        logging.debug(f'Creating cache directory: {_CACHE_DIR}')
        os.makedirs(_CACHE_DIR)


def read_cache_file(filename: str) -> dict[str, Any] | None:
    """Read and return the contents of a YAML cache file, or None on error."""
    full_filename = os.path.join(_CACHE_DIR, filename)

    if not os.path.exists(full_filename):
        logging.warning(f'The specified cache file could not be found: {full_filename}')
        return None

    if not os.path.isfile(full_filename):
        logging.error(f'The specified path is not a file: {full_filename}')
        return None

    if not full_filename.endswith('.yaml') or full_filename.endswith('.yml'):
        logging.error(f'Only YAML files are supported: {full_filename}')
        return None

    with open(full_filename) as cache_file:
        result: dict[str, Any] = yaml.load(cache_file, yaml.BaseLoader)
        return result


def write_cache_file(filename: str, data: dict[str, Any]) -> None:
    """Write data to a YAML cache file in the cache directory."""
    with open(os.path.join(_CACHE_DIR, filename), 'w') as cache_file:
        yaml.dump(data, cache_file)
