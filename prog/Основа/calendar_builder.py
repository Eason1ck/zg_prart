# -*- coding: utf-8 -*-
import calendar
import datetime as dt

WORK_WEEKDAYS = {1, 2, 3, 4, 5}  # вт=1 ... сб=5

def month_workdays(year, month):
    last_day = calendar.monthrange(year, month)[1]
    days = []
    for day in range(1, last_day + 1):
        d = dt.date(year, month, day)
        if d.weekday() in WORK_WEEKDAYS:
            days.append(d)
    return days

def week_number(d):
    return d.isocalendar()[1]

def pick_special_days(workdays):
    price_range = [d for d in workdays if 10 <= d.day <= 14]
    callcenter_range = [d for d in workdays if 15 <= d.day <= 20]
    price_day = price_range[0] if price_range else None
    callcenter_day = callcenter_range[0] if callcenter_range else None
    return price_day, callcenter_day

def build_calendar(year, month):
    workdays = month_workdays(year, month)
    weeks = {}
    for d in workdays:
        weeks.setdefault(week_number(d), []).append(d)
    price_day, callcenter_day = pick_special_days(workdays)
    return {
        "workdays": workdays,
        "weeks": weeks,
        "price_monitor_day": price_day,
        "callcenter_monitor_day": callcenter_day,
    }
