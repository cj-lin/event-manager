#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Filename: filewatcher
Author: CJ Lin

Multi-platform file watcher using watchfiles library.
"""

import pathlib
import threading
from collections import deque

from watchfiles import Change, watch

# Thread join timeout in seconds
_THREAD_JOIN_TIMEOUT = 1.0


class FileWatcher:
    """Multi-platform file watcher using watchfiles library.

    Note: With watchfiles, the directories to watch are configured at start time.
    Dynamic addition/removal of watches requires stopping and restarting the watcher.
    In recursive mode, watchfiles automatically handles subdirectory watching.
    """

    def __init__(self):
        self.watch_dirs = set()
        self.watch_dir = {}  # Keep for compatibility
        self.recursive = False
        self._changes = deque()
        self._stop_event = threading.Event()
        self._watcher_thread = None

    def add_watch(self, directory: pathlib.Path, rec_flag: bool = False):
        """Add a directory to watch.

        Args:
            directory: Directory path to watch.
            rec_flag: If True, watch recursively (applies to all watched dirs).
        """
        self.watch_dirs.add(directory)
        self.watch_dir[directory] = directory  # Keep for compatibility
        if rec_flag:
            self.recursive = True

    def rec_add_watch(self, directory: pathlib.Path):
        """Add a directory to watch recursively.

        Args:
            directory: Directory path to watch recursively.
        """
        self.add_watch(directory, rec_flag=True)

    def remove_watch(self, directory: pathlib.Path):
        """Remove a directory from watch list.

        Note: With watchfiles, changes to watch_dirs don't take effect until
        the watcher is restarted. In recursive mode, watchfiles automatically
        handles directory removal events.

        Args:
            directory: Directory path to remove from watch.
        """
        self.watch_dirs.discard(directory)
        self.watch_dir.pop(directory, None)

    def start(self):
        """Start the file watcher in a background thread."""
        self._stop_event.clear()
        self._watcher_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watcher_thread.start()

    def _watch_loop(self):
        """Internal method that runs the watchfiles generator in a thread."""
        if not self.watch_dirs:
            return

        for changes in watch(
            *self.watch_dirs,
            stop_event=self._stop_event,
            recursive=self.recursive,
            watch_filter=None,
        ):
            for change_type, path in changes:
                pathname = pathlib.Path(path)
                status = None

                if change_type == Change.added:
                    if pathname.is_dir():
                        status = "mkdir"
                    else:
                        status = "file"
                elif change_type == Change.modified:
                    if pathname.is_file():
                        status = "file"
                elif change_type == Change.deleted:
                    # For deleted items, we can't check if it was a dir
                    # We mark it as rmdir to signal a deletion event
                    status = "rmdir"

                if status:
                    self._changes.append((status, pathname))

    def read(self):
        """Read pending changes from the watcher.

        Yields:
            Tuple of (status, pathname) where status is one of
            'mkdir', 'rmdir', or 'file'.
        """
        while self._changes:
            yield self._changes.popleft()

    def has_changes(self):
        """Check if there are pending changes.

        Returns:
            True if there are changes to read.
        """
        return len(self._changes) > 0

    def reset(self):
        """Reset the file watcher."""
        self._stop_event.set()
        if self._watcher_thread and self._watcher_thread.is_alive():
            self._watcher_thread.join(timeout=_THREAD_JOIN_TIMEOUT)
        self.watch_dirs.clear()
        self.watch_dir.clear()
        self._changes.clear()
        self._stop_event.clear()
        self.recursive = False
        self._watcher_thread = None

    def stop(self):
        """Stop the file watcher."""
        self._stop_event.set()
        if self._watcher_thread and self._watcher_thread.is_alive():
            self._watcher_thread.join(timeout=_THREAD_JOIN_TIMEOUT)
