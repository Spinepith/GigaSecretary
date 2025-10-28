import os
from src.db import db


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.join(ROOT_DIR, "data")


def create_dirs():
    departments_dir = os.path.join(BASE_DIR, "departments")
    os.makedirs(departments_dir, exist_ok=True)

    departments = db.get_departments()
    if departments:
        for dept in departments:
            os.makedirs(os.path.join(departments_dir, dept), exist_ok=True)
            print(f"# Структура для отдела '{dept}' готова.")


if __name__ == "__main__":
    create_dirs()
    print(f"# СКРИПТ ЗАВЕРШИЛ РАБОТУ")
