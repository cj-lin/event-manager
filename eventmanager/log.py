#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Filename: log
Author: CJ Lin
"""

import logging
import logging.handlers


def get_logger(prefix, is_debug):
    if prefix:
        prefix.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.TimedRotatingFileHandler(prefix, when='midnight')
        handler.suffix = '%Y%m%d'
    else:
        handler = logging.StreamHandler()

    log = logging.getLogger()
    log.setLevel(logging.DEBUG if is_debug else logging.INFO)
    handler.setFormatter(logging.Formatter('%(asctime)s\n%(message)s\n'))
    log.addHandler(handler)

    return log
