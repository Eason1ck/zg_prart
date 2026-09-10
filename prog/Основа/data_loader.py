# -*- coding: utf-8 -*-
import math
import pandas as pd

POINT_KIND_AP = "АП"
POINT_KIND_AT = "АТ"
POINT_KIND_SP = "СП"

REGION_HOME = 1
REGION_MANDATORY = 2
REGION_EXTRA = 3

REGION_NAMES = {
    REGION_HOME: "Домашний",
    REGION_MANDATORY: "Обязательный",
    REGION_EXTRA: "Дополнительный",
}

DAILY_LIMIT = {
    REGION_HOME: 17,
    REGION_MANDATORY: 16,
    REGION_EXTRA: 15,
}

MONITOR_MIN_VISITS = {
    POINT_KIND_AP: 2,
    POINT_KIND_AT: 3,
}


class Point:
    __slots__ = (
        "row_id", "name", "short_code", "tt_type", "region_name", "region_type",
        "x", "y", "kind", "visits", "visit_dates", "visit_weeks",
        "visit_weekdays",
    )

    def __init__(self, row_id, name, short_code, tt_type, region_name, region_type, x, y, kind):
        self.row_id = row_id
        self.name = name
        self.tt_type = tt_type
        self.region_name = region_name
        self.region_type = region_type
        self.x = x
        self.y = y
        self.kind = kind
        self.short_code = short_code

        self.visits = 0
        self.visit_dates = []
        self.visit_weeks = []
        self.visit_weekdays = []

    def required_min_visits(self):
        return MONITOR_MIN_VISITS.get(self.kind, 0)

    def is_monitored(self):
        return self.kind in MONITOR_MIN_VISITS

    def needs_more_visits(self):
        if not self.is_monitored():
            return self.visits == 0
        return self.visits < self.required_min_visits()

    def can_visit_on(self, week_num, weekday):
        if not self.is_monitored():
            return True
        if week_num in self.visit_weeks:
            return False
        if weekday in self.visit_weekdays:
            return False
        return True

    def register_visit(self, visit_date, week_num, weekday):
        self.visits += 1
        self.visit_dates.append(visit_date)
        self.visit_weeks.append(week_num)
        self.visit_weekdays.append(weekday)


def classify_kind(row):
    if pd.notna(row.get("ЦО АП")):
        return POINT_KIND_AP
    if pd.notna(row.get("ЦО АТ")):
        return POINT_KIND_AT
    return POINT_KIND_SP


def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


class Employee:
    def __init__(self, fio, co_name):
        self.fio = fio
        self.co_name = co_name
        self.home_x = None
        self.home_y = None
        self.points = []

    def add_point(self, point):
        self.points.append(point)

    def points_by_region_type(self, region_type):
        return [p for p in self.points if p.region_type == region_type]

    def region_types_present(self):
        return sorted(set(p.region_type for p in self.points))


def load_employees(filepath, sheet_name=0):
    df = pd.read_excel(filepath, sheet_name=sheet_name, header=0)

    dedup_keys = ["ФИО", "наименование ТТ", "x", "y"]
    before = len(df)
    df = df.drop_duplicates(subset=dedup_keys, keep="first").reset_index(drop=True)
    after = len(df)
    if before != after:
        print(f"[data_loader] Дедупликация: убрано {before - after} дублей точек (осталось {after} строк).")

    employees = {}
    for idx, row in df.iterrows():
        fio = row["ФИО"]
        co_name = row["наименование ЦО"]
        if fio not in employees:
            emp = Employee(fio, co_name)
            emp.home_x = row["Дом XC"]
            emp.home_y = row["Дом YC"]
            employees[fio] = emp
        emp = employees[fio]

        kind = classify_kind(row)
        point = Point(
            row_id=idx,
            name=row["наименование ТТ"],
            short_code=row["кр.код ТТ"],
            tt_type=row["тип ТТ"],
            region_name=row["Регион ТТ"],
            region_type=int(row["Тип региона"]),
            x=float(row["x"]),
            y=float(row["y"]),
            kind=kind,
        )
        emp.add_point(point)

    return list(employees.values())