#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Filename: event_manager
Author: CJ Lin

Watch filesystem using watchfiles, react and monitor subprocess when event is generated.
"""

import asyncio
import dataclasses
import os.path
import pathlib
import re
import shutil
import string

import psutil
import yaml

from . import cron, file_watch, log


def resolve_path_all(path: pathlib.Path, resolve: bool = True) -> pathlib.Path:
    """Expand environment variables and resolve path.

    Args:
        path (pathlib.Path): [description]
        resolve (bool, optional): [description]. Defaults to True.

    Returns:
        pathlib.Path: [description]
    """
    if path:
        path = pathlib.Path(os.path.expandvars(path)).expanduser()
        if resolve:
            path = path.resolve()
    return path


class GroupTemplate(string.Template):
    """Overwrite idpattern to enable $1 $2 ...

    Args:
        string ([type]): [description]
    """

    idpattern = r"\w+"


@dataclasses.dataclass
class GeneralConfig:
    """Global config"""

    watch: str
    conf: str
    log: str = None
    concurrent: int = 10
    recursive: bool = False
    refresh: bool = False
    delete: bool = False
    debug: bool = False

    def __post_init__(self):
        self.watch = resolve_path_all(self.watch)
        self.conf = resolve_path_all(self.conf)
        self.log = log.get_logger(resolve_path_all(self.log), self.debug)


@dataclasses.dataclass
class TriggerItem:
    """
    Instances of file triggers. The relationship to event is many to one.

    Pattern is precompiled from file name to save match time.
    """

    file: str
    event: str
    watch: dataclasses.InitVar[pathlib.Path]
    backup: str = None
    pattern: re.Pattern = None

    def __post_init__(self, watch):
        self.file = (watch / resolve_path_all(self.file, False)).resolve()
        self.pattern = re.compile(str(self.file))
        if self.backup:
            self.backup = (watch / resolve_path_all(self.backup, False)).resolve()


@dataclasses.dataclass
class EventItem:
    """Instances of events"""

    process: str
    timeout: int
    success: str
    fail: str
    mapping: dict = None
    sub: str = None

    def __post_init__(self):
        if isinstance(self.process, str):
            self.sub = self.process
            self.process = GroupTemplate(self.process)
        if self.mapping:
            self.sub = self.process.safe_substitute(**self.mapping)


class EventManager:
    """This is the core of event manager."""

    def __init__(self, config):
        self.config = config
        self.triggers = None
        self.events = None
        self.filewatcher = file_watch.FileWatcher()
        self.crontab = cron.crontab()
        self.queue = asyncio.Queue()
        self.event_loop = asyncio.get_event_loop()
        self.load_config()

    def load_config(self):
        """Load the yaml config and do initial settings."""
        yml_conf = yaml.safe_load(self.config.conf.read_text())
        if "General" in yml_conf:
            self.config = dataclasses.replace(
                self.config,
                **yml_conf["General"],
            )
        self.triggers = []
        self.events = {}

        for name, item in yml_conf["Events"].items():
            if "Process" in item:
                self.events[name] = EventItem(
                    process=item["Process"],
                    timeout=item.get("Timeout"),
                    success=item.get("Success"),
                    fail=item.get("Fail"),
                )

                if "File" in item:
                    trigger = TriggerItem(
                        file=item["File"],
                        event=name,
                        backup=item.get("Backup"),
                        watch=self.config.watch,
                    )
                    self.triggers.append(trigger)

                    if not self.config.recursive and trigger.file.parent.is_dir():
                        self.filewatcher.add_watch(trigger.file.parent)

                elif "Cron" in item:
                    self.crontab.add_rule(item["Cron"], name)

        if self.config.recursive:
            self.filewatcher.rec_add_watch(self.config.watch)

        if not self.filewatcher.watch_dir:
            raise Exception("No vaild triggers, exit.")

        if self.config.refresh:
            self.filewatcher.add_watch(self.config.conf.parent)

        self.config.log.info(
            "%s eventmanager start %s\nwatch: %s\nconf: %s\nlog: %s\nconcurrent: %s\n"
            "recursive: %s\nauto_refresh: %s\ndelete_file: %s\ndebug: %s",
            "-" * 30,
            "-" * 30,
            *dataclasses.astuple(self.config),
        )

    def run(self):
        """Run the event loop."""
        self.filewatcher.start()
        self.event_loop.run_until_complete(
            asyncio.gather(
                *[self.worker() for _ in range(self.config.concurrent)],
                self.read_cron_event(),
                self.poll_file_events(),
            )
        )

    async def poll_file_events(self):
        """Poll for file events from the file watcher."""
        while True:
            self.read_file_event()
            await asyncio.sleep(0.5)

    def read_file_event(self):
        """Handle file events."""
        for status, pathname in self.filewatcher.read():
            if self.config.refresh and pathname.samefile(self.config.conf):
                self.filewatcher.reset()
                self.crontab.clear_all_rules()
                self.load_config()
                self.filewatcher.start()

            elif status == "mkdir":
                # With watchfiles, recursive watching is handled automatically
                self.config.log.debug("detected new directory %s", str(pathname))

            elif status == "rmdir":
                # With watchfiles, directory removal is handled automatically
                self.config.log.debug("detected directory removal %s", str(pathname))
                # Update internal watch state to remove deleted directory
                self.filewatcher.watch_dirs.discard(pathname)
                self.filewatcher.watch_dir.pop(pathname, None)

            elif status == "file":
                self.config.log.debug("detected file %s", str(pathname))

                for trigger in self.triggers:
                    match = trigger.pattern.match(str(pathname))
                    if match:
                        mapping = {
                            **match.groupdict(),
                            **{str(i): j for i, j in enumerate(match.groups(), 1)},
                            "file": pathname,
                        }

                        self.queue.put_nowait(
                            dataclasses.replace(
                                self.events[trigger.event],
                                mapping=mapping,
                            )
                        )

                        if trigger.backup:
                            backup = GroupTemplate(str(trigger.backup)).safe_substitute(
                                **mapping
                            )
                            pathlib.Path(backup).parent.mkdir(
                                parents=True, exist_ok=True
                            )
                            shutil.copyfile(pathname, backup)
                            self.config.log.info("backup file to %s", backup)

                if self.config.delete and pathname.is_file():
                    pathname.unlink()
                    self.config.log.info("remove file %s", str(pathname))

    async def read_cron_event(self):
        async for at, name in self.crontab.generate():
            self.queue.put_nowait(
                dataclasses.replace(
                    self.events[name],
                    mapping={
                        "year": at.year,
                        "month": at.month,
                        "day": at.day,
                        "hour": at.hour,
                        "minute": at.minute,
                    },
                )
            )

    async def worker(self):
        """Monitor Processes and put next events into the queue after finished."""
        while True:
            event = await self.queue.get()
            process = await asyncio.create_subprocess_shell(event.sub)
            self.config.log.debug("Start: %s\nPid: %s", event.sub, process.pid)

            try:
                await asyncio.wait_for(process.wait(), event.timeout)

            except TimeoutError:
                for child in psutil.Process(process.pid).children(True):
                    child.kill()
                process.kill()
                stats = "Timeout"

            else:
                stats = "fail" if process.returncode else "success"
                next_event = getattr(event, stats)

                if next_event:
                    self.queue.put_nowait(
                        dataclasses.replace(
                            self.events[next_event],
                            mapping=event.mapping,
                        )
                    )

            self.config.log.info(
                "%s: %s\nPid: %s%s",
                stats.capitalize(),
                event.sub,
                process.pid,
                f"\nNext: {next_event}" if next_event else "",
            )
