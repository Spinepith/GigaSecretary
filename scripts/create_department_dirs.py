import os
from src.db import db


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.join(ROOT_DIR, "data")


def create_dirs():
    os.makedirs(BASE_DIR, exist_ok=True)
    departaments = db.get_departments()
    if departaments:
        for dept in departaments:
            os.makedirs(os.path.join(BASE_DIR, dept), exist_ok=True)
            print(f"# Структура для отдела '{dept}' готова.")


if __name__ == "__main__":
    create_dirs()
    print(f"# СКРИПТ ЗАВЕРШИЛ РАБОТУ")
