"""Tests for orgcal.utils module."""

import datetime as dt
import tempfile
from pathlib import Path

from orgcal.utils import (
    _collect_org_files,
    clean_up_heading,
    force_timestamp,
    get_datetime_from_org,
    parse_cutoff_date,
    read_config_file,
    setup_logging,
)


class TestCleanUpHeading:
    def test_removes_default_todo_keywords(self):
        assert clean_up_heading('NEXT Buy groceries') == 'Buy groceries'
        assert clean_up_heading('RUNNING Deploy service') == 'Deploy service'
        assert clean_up_heading('PAUSED Review PR') == 'Review PR'

    def test_removes_custom_todo_keywords(self):
        assert clean_up_heading('TODO Fix bug', todo_keywords=['TODO']) == 'Fix bug'
        assert clean_up_heading('DONE Ship it', todo_keywords=['DONE']) == 'Ship it'

    def test_removes_priorities(self):
        assert clean_up_heading('[#A] Important task') == 'Important task'
        assert clean_up_heading('[#B] Medium task') == 'Medium task'
        assert clean_up_heading('[#C] Low priority') == 'Low priority'

    def test_removes_both_todo_and_priority(self):
        assert clean_up_heading('NEXT [#A] Urgent task') == 'Urgent task'
        # Note: Function processes in order, doesn't loop back
        assert clean_up_heading('[#B] RUNNING Important') == 'RUNNING Important'

    def test_no_modifications_needed(self):
        assert clean_up_heading('Regular task') == 'Regular task'
        assert clean_up_heading('Another task') == 'Another task'

    def test_empty_heading(self):
        assert clean_up_heading('') == ''


class TestParseCutoffDate:
    def test_parse_now(self):
        result = parse_cutoff_date('now')
        assert result == dt.date.today()

    def test_parse_thisweek(self):
        result = parse_cutoff_date('thisweek')
        expected = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
        assert result == expected

    def test_parse_specific_date(self):
        result = parse_cutoff_date('2024-06-24')
        assert result == dt.date(2024, 6, 24)

    def test_parse_another_date(self):
        result = parse_cutoff_date('2025-01-15')
        assert result == dt.date(2025, 1, 15)


class TestForceTimestamp:
    def test_datetime_passthrough(self):
        scheduled = dt.datetime(2024, 6, 24, 10, 30)
        result = force_timestamp(scheduled)
        assert result == scheduled

    def test_date_to_datetime(self):
        scheduled = dt.date(2024, 6, 24)
        result = force_timestamp(scheduled)
        assert isinstance(result, dt.datetime)
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 24
        assert result.hour == 0
        assert result.minute == 0

    def test_none_to_now(self):
        before = dt.datetime.now()
        result = force_timestamp(None)
        after = dt.datetime.now()
        assert before <= result <= after


class TestGetDatetimeFromOrg:
    def test_datetime_with_brackets(self):
        result = get_datetime_from_org('[2024-06-24 Mon 10:30]')
        assert isinstance(result, dt.datetime)
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 24
        assert result.hour == 10
        assert result.minute == 30

    def test_datetime_with_angle_brackets(self):
        result = get_datetime_from_org('<2024-06-24 Mon 14:00>')
        assert isinstance(result, dt.datetime)
        assert result.hour == 14
        assert result.minute == 0

    def test_date_only(self):
        result = get_datetime_from_org('[2024-06-24 Mon]')
        assert isinstance(result, dt.date)
        assert not isinstance(result, dt.datetime)
        assert result == dt.date(2024, 6, 24)

    def test_custom_timezone(self):
        result = get_datetime_from_org('[2024-06-24 Mon 10:30]', 'UTC')
        assert isinstance(result, dt.datetime)
        assert result.tzinfo is not None


class TestCollectOrgFiles:
    def test_collect_from_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / 'test1.org'
            file2 = Path(tmpdir) / 'test2.org'
            file1.write_text('* Task 1')
            file2.write_text('* Task 2')

            result = _collect_org_files([str(file1), str(file2)])
            assert len(result) == 2
            assert str(file1) in result
            assert str(file2) in result

    def test_collect_from_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / 'file1.org').write_text('* Task 1')
            (Path(tmpdir) / 'file2.org').write_text('* Task 2')
            (Path(tmpdir) / 'file3.txt').write_text('Not org')

            result = _collect_org_files([tmpdir])
            assert len(result) == 2
            assert all(f.endswith('.org') for f in result)

    def test_mixed_files_and_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / 'subdir'
            subdir.mkdir()
            (subdir / 'file1.org').write_text('* Task 1')
            (subdir / 'file2.org').write_text('* Task 2')

            standalone = Path(tmpdir) / 'standalone.org'
            standalone.write_text('* Task 3')

            result = _collect_org_files([str(subdir), str(standalone)])
            assert len(result) == 3

    def test_empty_list(self):
        result = _collect_org_files([])
        assert result == []


class TestReadConfigFile:
    def test_read_valid_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.yml'
            config_file.write_text(
                'calendars:\n'
                '  - url: https://example.com\n'
                '    id: test-cal\n'
                '    username: user\n'
                '    password: pass\n'
            )

            result = read_config_file(str(config_file))
            assert result is not None
            assert 'calendars' in result
            assert len(result['calendars']) == 1
            assert result['calendars'][0]['id'] == 'test-cal'

    def test_read_nonexistent_file(self):
        result = read_config_file('/nonexistent/config.yml')
        assert result is None

    def test_read_non_yaml_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.txt'
            config_file.write_text('not yaml')

            result = read_config_file(str(config_file))
            assert result is None


class TestSetupLogging:
    def test_setup_info_level(self):
        import logging

        # Reset logging configuration
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        setup_logging(debug=False)
        assert logging.getLogger().level == logging.INFO

    def test_setup_debug_level(self):
        import logging

        # Reset logging configuration
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        setup_logging(debug=True)
        assert logging.getLogger().level == logging.DEBUG
