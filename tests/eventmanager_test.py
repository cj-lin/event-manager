#!/usr/bin/env python
# -*- coding: utf-8 -*-

import dataclasses
import os
import pathlib
import subprocess
import time
import pkg_resources

import pytest


@dataclasses.dataclass
class AllItem:
    root: pathlib.Path
    data: pathlib.Path = None
    backup: pathlib.Path = None
    conf: pathlib.Path = pathlib.Path(pkg_resources.resource_filename(__name__, 'eventmanager.yml'))
    proc: subprocess.Popen = None

    def __post_init__(self):
        os.environ['TMPROOT'] = str(self.root)

        self.data = self.root / 'data'
        self.data.mkdir()
        os.environ['TMPDATA'] = str(self.data)

        self.backup = self.root / 'backup'
        self.backup.mkdir()
        os.environ['TMPBACKUP'] = str(self.backup)

        self.proc = subprocess.Popen(
            f'eventmanager start -d {self.root} -f {self.conf} -rav',
            shell=True,
        )
        time.sleep(1)

    def close(self):
        self.proc.terminate()


@pytest.fixture()
def create_eventmanager(tmp_path):
    item = AllItem(root=tmp_path)
    yield item
    item.close()


def test_relative_path(create_eventmanager):
    (create_eventmanager.data / 'test1').touch()
    time.sleep(1)
    assert (create_eventmanager.backup / 'test1').exists()


def test_environment_variables(create_eventmanager):
    (create_eventmanager.data / 'test2').touch()
    time.sleep(1)
    assert (create_eventmanager.backup / 'test2').exists()


def test_create_directories(create_eventmanager):
    (create_eventmanager.data / 'test3').mkdir()
    time.sleep(1)
    (create_eventmanager.data / 'test3' / 'test3').touch()
    time.sleep(1)
    assert (create_eventmanager.backup / 'test3' / 'test3').exists()


def test_refresh(create_eventmanager):
    create_eventmanager.conf.touch()
    time.sleep(1)
    assert create_eventmanager.proc.poll() == None
