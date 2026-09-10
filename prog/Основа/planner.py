# -*- coding: utf-8 -*-
from data_loader import (
    Point, Employee, haversine_km,
    REGION_HOME, REGION_MANDATORY, REGION_EXTRA, REGION_NAMES,
    DAILY_LIMIT, POINT_KIND_AP, POINT_KIND_AT, POINT_KIND_SP,
)
from calendar_builder import build_calendar, week_number

class DayRoute:
    def __init__(self, date, region_type, is_special=None):
        self.date = date
        self.region_type = region_type
        self.is_special = is_special  # для спецдней
        self.stops = []

    @property
    def region_name(self):
        if self.region_type is None:
            return ""
        return REGION_NAMES[self.region_type]

class EmployeeMonthPlan:
    def __init__(self, employee):
        self.employee = employee
        self.days = []
        self.warnings = []

    def add_day(self, day_route):
        self.days.append(day_route)

    def add_warning(self, text):
        self.warnings.append(text)

def region_has_points_to_visit(emp, region_type):
    pts = emp.points_by_region_type(region_type)
    if not pts:
        return False
    for p in pts:
        if p.kind in (POINT_KIND_AP, POINT_KIND_AT) and p.needs_more_visits():
            return True
    for p in pts:
        if p.kind == POINT_KIND_SP and p.visits == 0:
            return True
    return False

def region_fully_exhausted(emp, region_type):
    pts = emp.points_by_region_type(region_type)
    if not pts:
        return True
    for p in pts:
        if p.kind in (POINT_KIND_AP, POINT_KIND_AT) and p.needs_more_visits():
            return False
        if p.kind == POINT_KIND_SP and p.visits == 0:
            return False
    return True


def choose_region_type_for_day(emp, weekly_mandatory_done, available_types):
    has_unfulfilled = {
        rt: region_has_points_to_visit(emp, rt)
        for rt in (REGION_HOME, REGION_MANDATORY, REGION_EXTRA)
    }

    mandatory_available = REGION_MANDATORY in available_types and has_unfulfilled[REGION_MANDATORY]
    home_available = REGION_HOME in available_types and has_unfulfilled[REGION_HOME]
    extra_available = REGION_EXTRA in available_types and has_unfulfilled[REGION_EXTRA]

    if REGION_MANDATORY in available_types and not weekly_mandatory_done and mandatory_available:
        return REGION_MANDATORY
    if home_available:
        return REGION_HOME
    if mandatory_available:
        return REGION_MANDATORY
    if extra_available:
        return REGION_EXTRA

    for rt in (REGION_HOME, REGION_MANDATORY, REGION_EXTRA):
        if rt in available_types:
            return rt
    return None

def pick_next_point(emp, region_type, cur_x, cur_y, wn, weekday, visited_today_ids):
    pts = [p for p in emp.points_by_region_type(region_type) if p.row_id not in visited_today_ids]
    if not pts:
        return None

    candidates_priority = [
        p for p in pts
        if p.kind in (POINT_KIND_AP, POINT_KIND_AT)
        and p.needs_more_visits()
        and p.can_visit_on(wn, weekday)
    ]
    if candidates_priority:
        min_visits = min(p.visits for p in candidates_priority)
        best_pool = [p for p in candidates_priority if p.visits == min_visits]
        return _nearest(best_pool, cur_x, cur_y)

    sp_unvisited = [p for p in pts if p.kind == POINT_KIND_SP and p.visits == 0]
    if sp_unvisited:
        return _nearest(sp_unvisited, cur_x, cur_y)

    sp_all = [p for p in pts if p.kind == POINT_KIND_SP]
    if sp_all:
        return _nearest(sp_all, cur_x, cur_y)
    return None

def _nearest(points, cur_x, cur_y):
    best, best_d = None, None
    for p in points:
        d = haversine_km(cur_x, cur_y, p.x, p.y)
        if best is None or d < best_d:
            best, best_d = p, d
    return best

def plan_day(emp, date, region_type, daily_limit, wn, weekday):
    route = DayRoute(date, region_type)
    cur_x, cur_y = emp.home_x, emp.home_y
    visited_today_ids = set()

    while len(route.stops) < daily_limit:
        nxt = pick_next_point(emp, region_type, cur_x, cur_y, wn, weekday, visited_today_ids)
        if nxt is None:
            break
        nxt.register_visit(date, wn, weekday)
        visited_today_ids.add(nxt.row_id)
        route.stops.append(nxt)
        cur_x, cur_y = nxt.x, nxt.y

    return route

def plan_employee_month(emp, year, month):
    calendar_data = build_calendar(year, month)
    workdays = calendar_data["workdays"]
    price_day = calendar_data["price_monitor_day"]
    callcenter_day = calendar_data["callcenter_monitor_day"]

    available_types = set(emp.region_types_present())
    plan = EmployeeMonthPlan(emp)
    weekly_mandatory_done = {wn: False for wn in calendar_data["weeks"].keys()}

    for d in workdays:
        wn = week_number(d)
        weekday = d.weekday()

        if price_day is not None and d == price_day:
            plan.add_day(DayRoute(d, None, is_special="price_monitor"))
            continue
        if callcenter_day is not None and d == callcenter_day:
            plan.add_day(DayRoute(d, None, is_special="callcenter_monitor"))
            continue

        region_type = choose_region_type_for_day(emp, weekly_mandatory_done[wn], available_types)

        if region_type is None:
            plan.add_day(DayRoute(d, None, is_special="empty_no_region"))
            plan.add_warning(f"{d.isoformat()}: нет доступного региона для построения маршрута.")
            continue

        limit = DAILY_LIMIT[region_type]
        route = plan_day(emp, d, region_type, limit, wn, weekday)
        plan.add_day(route)

        if region_type == REGION_MANDATORY:
            weekly_mandatory_done[wn] = True

        if len(route.stops) < limit:
            plan.add_warning(
                f"{d.isoformat()} ({REGION_NAMES[region_type]}): заполнено только "
                f"{len(route.stops)} из {limit} точек — в регионе не осталось "
                f"доступных для посещения точек по правилам."
            )

    mandatory_exhausted = region_fully_exhausted(emp, REGION_MANDATORY)
    if REGION_MANDATORY in available_types and not mandatory_exhausted:
        for wn, done in weekly_mandatory_done.items():
            if not done:
                plan.add_warning(
                    f"Неделя {wn}: не удалось посетить обязательный регион "
                    f"(не нашлось рабочего дня / точек)."
                )

    for p in emp.points:
        if p.is_monitored() and p.visits < p.required_min_visits():
            plan.add_warning(
                f"Точка '{p.name}' ({p.kind}, регион {p.region_name}): "
                f"выполнено {p.visits} из {p.required_min_visits()} требуемых посещений за месяц."
            )

    return plan