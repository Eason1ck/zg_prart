# -*- coding: utf-8 -*-
INPUT_PATH = "try2.xlsx"                       # входной файл (положите рядом с .py файлами)
YEAR = 2026                                    # год
MONTH = 6                                      # месяц (1-12)
OUTPUT_PATH = "план_маршрутов_июнь_2026.xlsx"  # имя выходного файла

from data_loader import load_employees
from planner import plan_employee_month
from excel_export import export_plans_to_excel

def main():
    print(f"Загружаю данные из {INPUT_PATH}...")
    employees = load_employees(INPUT_PATH)
    print(f"Найдено АК/ЦО: {len(employees)}")

    plans = []
    for emp in employees:
        print(f"  Строю маршрут: {emp.co_name} ({emp.fio}), точек: {len(emp.points)}")
        plan = plan_employee_month(emp, YEAR, MONTH)
        plans.append(plan)
        if plan.warnings:
            print(f"    Предупреждений: {len(plan.warnings)}")

    print(f"Сохраняю результат в {OUTPUT_PATH}...")
    export_plans_to_excel(plans, YEAR, MONTH, OUTPUT_PATH)
    print("Готово.")

if __name__ == "__main__":
    main()
