import pandas as pd
from tkinter import Tk, filedialog

root = Tk()
root.withdraw()
input_path = filedialog.askopenfilename(
    title="Выберите CSV файл",
    filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")]
)
if not input_path:
    print("Файл не выбран. Работа остановлена.")
    exit()

df = pd.read_csv(input_path, sep=";", encoding="cp1251")

# Фильтрация строк, где есть рабочее время и домашняя точка
time_cols = ["рабочее вреям сотрудника С", "По"]  # Опечатка в csv файле, нужно переименовывать
home_cols = ["Дом XC", "Дом YC"]
mask = (
    df[time_cols].notna().all(axis=1) &
    df[home_cols].notna().all(axis=1)
)
df_filtered = df.loc[mask].copy()
df_filtered["Дата"] = pd.to_datetime(df_filtered["Дата"], dayfirst=True)

# Удаляем магазины с отсутствующими или нулевыми координатами,
# я посчитал важным для будущей маршрутизации, тк они могут мешать
df_filtered = df_filtered[
    (df_filtered["x"].notna()) &
    (df_filtered["y"].notna()) &
    (df_filtered["x"] != 0) &
    (df_filtered["y"] != 0)
]

# Базовая сортировка: Дата → Тип региона → ФИО
df_sorted = df_filtered.sort_values(
    by=["Дата", "Тип региона", "ФИО"],
    ascending=[True, True, True]
)

# Приоритет ЦО: АП → АТ → СП
def co_priority(row):
    if pd.notna(row["ЦО АП"]):
        return 1
    if pd.notna(row["ЦО АТ"]):
        return 2
    if pd.notna(row["ЦО СП"]):
        return 3
    return 4 # Если вообще пусто

df_sorted["ЦО_порядок"] = df_sorted.apply(co_priority, axis=1)

df_sorted = df_sorted.sort_values(
    by=["Дата", "Тип региона", "ФИО", "ЦО_порядок"],
    ascending=[True, True, True, True]
).drop(columns=["ЦО_порядок"])

output_path = filedialog.asksaveasfilename(
    title="Сохранить результат как...",
    defaultextension=".xlsx",
    filetypes=[("Excel файлы", "*.xlsx")]
)

if not output_path:
    print("Файл для сохранения не выбран")
    exit()

df_sorted.to_excel(output_path, index=False) # Сохранение

print("Готово! Файл сохранён в:", output_path)