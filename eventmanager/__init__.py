#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
module name: eventmanager
Author: CJ Lin

command line wrapper of eventmanager.
"""

import pathlib
import os
import subprocess
import pkg_resources

import click

from . import eventmanager

CONF_PATH = pathlib.Path(pkg_resources.resource_filename(__name__, 'eventmanager.yml'))
EDITOR = os.environ.get('EDITOR', 'vim')


@click.group(help='This is the entrypoint of EventManager.')
@click.version_option()
def cli():
    """This is the entrypoint of all functions."""
    pass


@cli.command(help='start EventManager')
@click.option('-d', help='watch directory', default='.',
              type=click.Path(exists=True,
                              file_okay=False,
                              resolve_path=True))
@click.option('-f', help='customize config file',
              default=CONF_PATH,
              type=click.Path(exists=True,
                              dir_okay=False,
                              resolve_path=True))
@click.option('-l', help='log prefix (stdout if keep it blank)',
              type=click.Path(resolve_path=True))
@click.option('-c', help='maximum concurrency', type=int, default=10)
@click.option('-r', is_flag=True, help='watch directory recursively')
@click.option('-a', is_flag=True, help='auto refresh when config is updated')
@click.option('-e', is_flag=True, help='delete files after finishing jobs')
@click.option('-v', is_flag=True, help='debug mode')
def start(d, f, l, c, r, a, e, v):
    """start eventmanager"""
    eventmanager.EventManager(eventmanager.GeneralConfig(
        watch=d,
        conf=f,
        log=l,
        concurrent=c,
        recursive=r,
        refresh=a,
        delete=e,
        debug=v,
    )).run()


@cli.group(help='manage config of EventManager')
def config():
    """entrypoint of commands managing config"""
    pass


@config.command(help='show stored config')
def show():
    """show stored config"""
    print(CONF_PATH.read_text())


@config.command(help='edit stored config')
def edit():
    """edit stored config"""
    try:
        subprocess.call([EDITOR, CONF_PATH])
    except FileNotFoundError:
        subprocess.call(['vi', CONF_PATH])
