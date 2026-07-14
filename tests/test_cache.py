"""Tests for orgcal.cache module."""

import os
import tempfile
from pathlib import Path

from orgcal.cache import check_cache_dir, read_cache_file, write_cache_file


class TestCheckCacheDir:
    def test_creates_directory_if_not_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / '.orgcal_cache'
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                check_cache_dir()
                assert cache_dir.exists()
                assert cache_dir.is_dir()
            finally:
                os.chdir(original_dir)

    def test_does_not_fail_if_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / '.orgcal_cache'
            cache_dir.mkdir()
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                check_cache_dir()
                assert cache_dir.exists()
            finally:
                os.chdir(original_dir)


class TestReadWriteCacheFile:
    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / '.orgcal_cache'
            cache_dir.mkdir()
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)

                data = {
                    'cache': {
                        'uid-123': {
                            'title': 'Test Event',
                            'scheduled': '2024-06-24',
                            'duration': '1:00',
                            'description': 'Test description',
                        }
                    }
                }
                write_cache_file('test.yaml', data)

                result = read_cache_file('test.yaml')
                assert result is not None
                assert 'cache' in result
                assert 'uid-123' in result['cache']
                assert result['cache']['uid-123']['title'] == 'Test Event'
            finally:
                os.chdir(original_dir)

    def test_read_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / '.orgcal_cache'
            cache_dir.mkdir()
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = read_cache_file('nonexistent.yaml')
                assert result is None
            finally:
                os.chdir(original_dir)

    def test_write_empty_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / '.orgcal_cache'
            cache_dir.mkdir()
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                write_cache_file('empty.yaml', {'cache': {}})
                result = read_cache_file('empty.yaml')
                assert result is not None
                assert result['cache'] == {}
            finally:
                os.chdir(original_dir)

    def test_write_complex_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / '.orgcal_cache'
            cache_dir.mkdir()
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                data = {
                    'cache': {
                        'uid-1': {'title': 'Event 1', 'scheduled': '2024-06-24'},
                        'uid-2': {'title': 'Event 2', 'scheduled': '2024-06-25'},
                        'uid-3': {'title': 'Event 3', 'scheduled': '2024-06-26'},
                    }
                }
                write_cache_file('complex.yaml', data)
                result = read_cache_file('complex.yaml')
                assert result is not None
                assert len(result['cache']) == 3
            finally:
                os.chdir(original_dir)
