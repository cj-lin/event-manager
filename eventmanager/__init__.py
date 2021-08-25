#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
module name: event_manager
Author: CJ Lin

Command line wrapper of event-manager.
"""

import os
import pathlib
import subprocess
import sys

import click

from . import event_manager

CONF_PATH = pathlib.Path(sys.prefix, "etc", "event-manager.yml")
CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
EDITOR = os.environ.get("EDITOR", "vim")


@click.group(help="This is the entrypoint of event-manager.")
@click.version_option()
def cli():
    """This is the entrypoint of all functions."""
    pass


@cli.command(help="start event-manager")
@click.option(
    "-d",
    help="watch directory",
    default=".",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
@click.option(
    "-f",
    help="customize config file",
    default=CONF_PATH,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
)
@click.option(
    "-l",
    help="log prefix (stdout if keep it blank)",
    type=click.Path(resolve_path=True),
)
@click.option("-c", help="maximum concurrency", type=int, default=10)
@click.option("-r", is_flag=True, help="watch directory recursively")
@click.option("-a", is_flag=True, help="auto refresh when config is updated")
@click.option("-e", is_flag=True, help="delete files after finishing jobs")
@click.option("-v", is_flag=True, help="debug mode")
def start(d, f, l, c, r, a, e, v):
    """start event-manager"""
    event_manager.EventManager(
        event_manager.GeneralConfig(
            watch=d,
            conf=f,
            log=l,
            concurrent=c,
            recursive=r,
            refresh=a,
            delete=e,
            debug=v,
        )
    ).run()


@cli.group(help="manage config of event-manager")
def config():
    """entrypoint of commands managing config"""
    pass


@config.command(help="show stored config")
def show():
    """show stored config"""
    if CONF_PATH.is_file():
        print(CONF_PATH.read_text())
    else:
        print("Config not exists. Use event-manager config edit to create.\n")
        raise FileNotFoundError


@config.command(help="edit stored config")
def edit():
    """edit stored config"""
    try:
        subprocess.call([EDITOR, CONF_PATH])
    except FileNotFoundError:
        subprocess.call(["vi", CONF_PATH])


@config.command(help="update config")
@click.argument(
    "config",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
)
def use(config):
    """update config"""
    if config:
        CONF_PATH.write_text(pathlib.Path(config).read_text())
