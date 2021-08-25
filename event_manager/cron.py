#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Filename: cron
Author: CJ Lin
"""

import asyncio
import datetime

import dateutil.rrule
import sortedcontainers


class DefaultSortedDict(sortedcontainers.SortedDict):
    def __missing__(self, key):
        self[key] = []
        return self[key]


class crule:
    def __init__(self, frequency):
        minute, hour, day, month, weekday = frequency.split()
        self.rrule = dateutil.rrule.rrule(
            dateutil.rrule.DAILY,
            bymonth=map(int, month.split(",")),
            bymonthday=map(int, day.split(",")),
            byweekday=map(int, weekday.split(",")),
            byhour=map(int, hour.split(",")),
            byminute=map(int, minute.split(",")),
            bysecond=0,
        )

    def get_next_time(self):
        for rule in self.rrule:
            if rule > datetime.datetime.now():
                yield rule


class crontab:
    def __init__(self):
        self.rules = DefaultSortedDict()

    def add_rule(self, frequency, name):
        rule = crule(frequency)
        self.rules[rule.get_next_time()].append((rule, name))

    async def generate(self):
        while True:
            if self.rules:
                at, rule_list = self.rules.popitem(0)
                await asyncio.sleep(at - datetime.datetime.now())

                for rule, name in rule_list:
                    yield at, name
                    self.rules[rule.get_next_time()].append((rule, name))

            else:
                await asyncio.sleep(60)

    def clear_all_rules(self):
        self.rules.clear()
