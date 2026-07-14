# Orgcal
This is a small program to synchronize your `org-mode` files with a CalDAV server. Headings that have a `SCHEDULED` timestamp are handled as events in a calendar. Multiple calendars and org files can be handled via a config file. For more details about its creation and some thoughts behind it, you can read my blog post about it [here](https://tkreuziger.com/posts/2024-01-10-writing_my_own_calendar_syncing_solution/).

## Requirements

- **Python 3.10+**
- A CalDAV-compatible calendar server (tested with Nextcloud)
- `org-mode` files with `SCHEDULED` timestamps

## Features

- **One-way sync**: Synchronize org-mode headings to CalDAV calendars
- **Multiple calendars**: Configure and sync multiple calendars in a single run
- **Smart filtering**: Only sync events after a configurable cutoff date (today, this week, or specific date)
- **Effort tracking**: Maps org-mode `EFFORT` properties to event duration
- **Change detection**: Only updates remote events when org data changes
- **Cache system**: Tracks synced events to avoid unnecessary API calls
- **Cleanup mode**: Optionally delete remote events that no longer exist in org files
- **Debug logging**: Verbose output for troubleshooting sync issues

## Usage

### Install as a uv tool

```bash
uv tool install orgcal
```

Or run directly without installing:

```bash
uvx orgcal --config config.yml
```

### Development

```bash
uv sync
uv run orgcal --config config.yml
```

If the `--config` argument is omitted, a file with the name `config.yml` in the current directory will be used. Absolute or relative paths can be provided. Optionally, a `--debug` argument can be passed to see more detailed output.

## Configuration
The config file is in YAML format. The file has the following structure:

```yaml
# config.yml
calendars: # this key has to be the root
    - url: SERVER-URL
      id: CALENDAR-ID
      username: USERNAME
      password: PASSWORD
      sync_cutoff: thisweek
      org_files:
          - /path/to/file.org
```

For a Nextcloud CalDAV server, the url should be in the format `https://SERVER-URL/remote.php/dav/calendars/USERNAME/`, where `USERNAME` is the username of the user in the server. As this may be different for other implementations, the provided user name for authentication is not used to construct the url.

The `sync_cutoff` key can be set to "now" or "thisweek" to synchronize only events that are scheduled in the current week. Alternatively, a date in the format "YYYY-MM-DD" can be provided. No item with a scheduled date before this date will be synchronized.

The org_files key has to be a list of org files or directories containing org files. If a directory is provided, all org files within will be added to the list. This does not work recursively.

## Testing
This tool has been tested with a Nextcloud CalDAV server. If you are using another implementation and are experiencing problems, please create an issue on GitHub and I can take a look.

## Limitations

- **One-way sync only**: Changes flow from org files to calendar. Edits made directly in the calendar may be overwritten.
- **Event deletion**: Deleting events in the calendar can cause ID conflicts. Delete from org files first, then use `--delete_remote` to clean up the calendar.
- **Archived events**: Events moved to archive files are no longer visible to the sync. Include archive directories in `org_files` if you want them synced.
- **Timestamp updates**: Switching between all-day events and timed events may not always update correctly on the remote calendar.
- **No recurrence**: Recurring org timestamps are not expanded into multiple calendar events.
- **No conflict resolution**: If both org and calendar are modified, the org version wins without merging.

## License
This program is licensed under the MIT license.
