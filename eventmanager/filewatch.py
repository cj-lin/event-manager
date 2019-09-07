#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Filename: filewatcher
Author: CJ Lin
"""

from inotify_simple import flags, INotify

MASK_DIR = flags.CLOSE_WRITE | flags.MOVED_TO
MASK_REC = MASK_DIR | flags.ISDIR | flags.CREATE | flags.DELETE | flags.MOVED_FROM


class FileWatcher:
    def __init__(self):
        self.inotify = INotify()
        self.watch_dir = {}


    def add_watch(self, directory, rec_flag=False):
        watch = self.inotify.add_watch(directory, MASK_REC if rec_flag else MASK_DIR)
        self.watch_dir[watch] = directory
        self.watch_dir[directory] = watch


    def rec_add_watch(self, directory):
        self.add_watch(directory, rec_flag=True)

        for watch in filter(lambda x: x.is_dir(), directory.rglob('*')):
            self.add_watch(watch, rec_flag=True)


    def remove_watch(self, directory):
        del self.watch_dir[self.watch_dir[directory]]
        del self.watch_dir[directory]


    def read(self):
        for watch, mask, _, name in self.inotify.read():
            masks = flags.from_mask(mask)
            pathname = self.watch_dir[watch] / name
            status = None

            if flags.ISDIR in masks:
                if flags.CREATE in masks or flags.MOVED_TO in masks:
                    status = 'mkdir'
                else:
                    status = 'rmdir'

            elif flags.CLOSE_WRITE in masks or flags.MOVED_TO in masks:
                status = 'file'

            yield status, pathname


    def reset(self):
        self.inotify.close()
        self.watch_dir.clear()
        self.inotify = INotify()
