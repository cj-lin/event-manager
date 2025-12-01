#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Filename: filewatcher
Author: CJ Lin

Multi-platform file watcher using watchfiles library.
"""

import logging
import pathlib
import threading
from collections import deque

from watchfiles import Change, watch

# Thread join timeout in seconds
_THREAD_JOIN_TIMEOUT = 1.0

logger = logging.getLogger(__name__)


class FileWatcher:
    """Multi-platform file watcher using watchfiles library.

    Note: With watchfiles, the directories to watch are configured at start time.
    Dynamic addition/removal of watches requires stopping and restarting the watcher.
    In recursive mode, watchfiles automatically handles subdirectory watching.

    Thread Safety:
        The internal _changes deque is protected by a lock for thread-safe access
        between the watcher thread and the main thread. The read() method is safe
        to call without checking has_changes() first.

    Recursive Mode:
        Setting rec_flag=True on any add_watch() call enables recursive watching
        for ALL directories, not just the specified one. This is by design since
        watchfiles applies the recursive setting globally to all watched paths.

    API Compatibility:
        The watch_dir dictionary is maintained for compatibility but only maps
        directory -> directory (not the bidirectional watch_descriptor mapping
        from the original inotify implementation).
    """

    def __init__(self):
        self.watch_dirs = set()
        self.watch_dir = {}  # Keep for compatibility (directory -> directory only)
        self.recursive = False
        self._changes = deque()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._watcher_thread = None
        self._known_dirs = set()  # Track known directories for deletion detection

    def add_watch(self, directory: pathlib.Path, rec_flag: bool = False):
        """Add a directory to watch.

        WARNING: The recursive setting is GLOBAL for all watched directories.
        If you set rec_flag=True for any directory, ALL watched directories will be
        watched recursively. Mixing recursive and non-recursive watches will result
        in ALL directories being watched recursively.

        Args:
            directory: Directory path to watch.
            rec_flag: If True, enables recursive watching for ALL watched dirs.
        """
        # Warn if mixing recursive and non-recursive watches
        if rec_flag and not self.recursive and len(self.watch_dirs) > 0:
            logger.warning(
                "Mixing recursive and non-recursive watches: "
                "Setting rec_flag=True will cause ALL watched directories "
                "to be watched recursively."
            )
        elif not rec_flag and self.recursive:
            logger.warning(
                "Adding a non-recursive watch after recursive mode is enabled: "
                "ALL watched directories will still be watched recursively."
            )
        self.watch_dirs.add(directory)
        self.watch_dir[directory] = directory  # Keep for compatibility
        self._known_dirs.add(directory)
        if rec_flag:
            self.recursive = True

    def rec_add_watch(self, directory: pathlib.Path):
        """Add a directory to watch recursively.

        Args:
            directory: Directory path to watch recursively.
        """
        self.add_watch(directory, rec_flag=True)
        # Pre-populate known directories in recursive mode
        try:
            if directory.is_dir():
                for subdir in directory.glob("**/*"):
                    try:
                        if subdir.is_dir():
                            self._known_dirs.add(subdir)
                    except OSError:
                        # Handle permission denied, network issues, etc.
                        pass
        except OSError:
            # Handle permission denied, network issues, etc.
            pass

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
        self._known_dirs.discard(directory)

    def start(self):
        """Start the file watcher in a background thread.

        Does nothing if a watcher thread is already running.
        """
        if self._watcher_thread and self._watcher_thread.is_alive():
            return
        self._stop_event.clear()
        self._watcher_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watcher_thread.start()

    def _watch_loop(self):
        """Internal method that runs the watchfiles generator in a thread."""
        if not self.watch_dirs:
            return

        try:
            for changes in watch(
                *self.watch_dirs,
                stop_event=self._stop_event,
                recursive=self.recursive,
                watch_filter=None,
            ):
                for change_type, path in changes:
                    file_path = pathlib.Path(path)
                    status = None

                    if change_type == Change.added:
                        try:
                            if file_path.is_dir():
                                status = "mkdir"
                                self._known_dirs.add(file_path)
                            else:
                                status = "file"
                        except OSError:
                            # Path no longer exists or permission denied, skip event
                            pass
                    elif change_type == Change.modified:
                        # Directory modifications are ignored as they don't represent
                        # meaningful file content changes for trigger matching
                        try:
                            if file_path.is_file():
                                status = "file"
                        except OSError:
                            # Path no longer exists or permission denied, skip event
                            pass
                    elif change_type == Change.deleted:
                        # Check if this was a known directory
                        if file_path in self._known_dirs:
                            status = "rmdir"
                            self._known_dirs.discard(file_path)
                        else:
                            # Deleted files are not processed as triggers
                            # since the file content is no longer available
                            pass

                    if status:
                        with self._lock:
                            self._changes.append((status, file_path))
        except Exception as e:
            logger.error("File watcher thread error: %s", e)

    def read(self):
        """Read pending changes from the watcher.

        Thread-safe method that can be called without checking has_changes() first.

        Yields:
            Tuple of (status, file_path) where status is one of
            'mkdir', 'rmdir', or 'file'.
        """
        while True:
            with self._lock:
                if not self._changes:
                    break
                yield self._changes.popleft()

    def has_changes(self):
        """Check if there are pending changes.

        Note: Due to potential race conditions between threads, it's recommended
        to call read() directly instead of checking has_changes() first.

        Returns:
            True if there are changes to read.
        """
        with self._lock:
            return len(self._changes) > 0

    def reset(self):
        """Reset the file watcher by stopping it and clearing all state."""
        self.stop()
        self.watch_dirs.clear()
        self.watch_dir.clear()
        with self._lock:
            self._changes.clear()
        self.recursive = False
        self._watcher_thread = None
        self._known_dirs.clear()

    def stop(self):
        """Stop the file watcher.

        Note: stop() only stops the thread but leaves watch state intact.
        Use reset() to stop the thread AND clear all state.
        """
        self._stop_event.set()
        if self._watcher_thread and self._watcher_thread.is_alive():
            self._watcher_thread.join(timeout=_THREAD_JOIN_TIMEOUT)
            if self._watcher_thread.is_alive():
                logger.warning("File watcher thread did not stop within timeout")
