import os
import time
from typing import Optional, List

import psycopg2

from ..bot import utils
from ..config import *

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.join(ROOT_DIR, 'data')

connection = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)

connection.autocommit = True
cursor = connection.cursor()


def get_assigned_employee_name(document_id: int) -> Optional[str]:
    try:
        cursor.execute("""
            SELECT e.employee_id 
            FROM documents d 
            JOIN employees e ON d.assigned_employee_id = e.employee_id 
            WHERE d.id = %s
        """, (document_id,))

        result = cursor.fetchone()
        if result:
            employee_id = result[0]
            return employee_id
        return None

    except psycopg2.Error as e:
        print(f"Ошибка при получении сотрудника для документа: {e}")
        return None


def get_departments() -> List[str]:
    try:
        cursor.execute("SELECT name FROM departments ORDER BY name")
        departments = [row[0] for row in cursor.fetchall()]
        return departments
    except psycopg2.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
        return []


def get_all_documents_from_db() -> List[tuple]:
    try:
        cursor.execute("SELECT id, file_path FROM documents")
        return cursor.fetchall()
    except psycopg2.Error as e:
        print(f"Ошибка при получении документов из БД: {e}")
        return []


def delete_document_from_db(document_id: int):
    try:
        cursor.execute("DELETE FROM documents WHERE id = %s", (document_id,))
        print(f"Удалена запись документа с ID: {document_id}")
    except psycopg2.Error as e:
        print(f"Ошибка при удалении документа из БД: {e}")


def get_department_id_by_name(department_name: str) -> int:
    try:
        cursor.execute("SELECT id, name FROM departments WHERE name = %s", (department_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        print(f"Ошибка при получении ID отдела: {e}")
        return None


def insert_document_to_db(file_path: str, department_name: str) -> Optional[int]:
    try:
        department_id = get_department_id_by_name(department_name)

        if not department_id:
            print(f"Ошибка: Отдел '{department_name}' не найден в БД")
            return None

        cursor.execute(
            "INSERT INTO documents (file_path, department_id) VALUES (%s, %s) RETURNING id",
            (file_path, department_id)
        )

        document_id = cursor.fetchone()[0]
        print(f"Добавлен новый документ: {file_path} в отдел '{department_name}'")

        return document_id

    except psycopg2.Error as e:
        print(f"Ошибка при добавлении документа в БД: {e}")
        return None


def process_new_document(file_path: str, department_name: str) -> str:
    document_id = insert_document_to_db(file_path, department_name)

    if document_id:

        time.sleep(0.1)

        employee_name = get_assigned_employee_name(document_id)

        if employee_name:
            return employee_name
        else:
            return "Не назначен"

    return "Ошибка при обработке"


def monitor_files_with_delay(delay_seconds: int = 20):
    print(f"Запуск мониторинга с интервалом {delay_seconds} секунд...")

    try:
        while True:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Проверка файлов...")

            if not os.path.exists(BASE_DIR):
                print(f"Папка {BASE_DIR} не существует")
                time.sleep(delay_seconds)
                continue

            db_documents = get_all_documents_from_db()
            db_file_paths = {file_path for _, file_path in db_documents}

            deleted_count = 0
            new_files_count = 0

            for doc_id, file_path in db_documents:
                full_path = os.path.join(BASE_DIR, file_path)

                if not os.path.exists(full_path):
                    print(f"Удален файл: {file_path}")
                    delete_document_from_db(doc_id)
                    deleted_count += 1

            all_files_found = []

            for root, dirs, files in os.walk(BASE_DIR):
                if root == BASE_DIR and not files:
                    continue

                for file in files:
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, BASE_DIR)
                    all_files_found.append((relative_path, file, os.path.basename(root)))

            for relative_path, file, department_name in all_files_found:
                if relative_path not in db_file_paths:
                    departments = get_departments()

                    if department_name in departments:
                        print(f"Обнаружен новый файл: {file} в отделе '{department_name}'")

                        assigned_employee = process_new_document(relative_path, department_name)

                        print(f"Файл назначен сотруднику: {assigned_employee}")

                        new_files_count += 1
                    else:
                        print(f"Файл в неизвестном отделе: {file} (папка '{department_name}')")

            if deleted_count > 0 or new_files_count > 0:
                print(f"Итог: удалено {deleted_count}, добавлено {new_files_count}")
            else:
                print("Изменений нет")

            time.sleep(delay_seconds)

    except KeyboardInterrupt:
        print("\nМониторинг остановлен пользователем")
    except Exception as e:
        print(f"Ошибка при мониторинге файлов: {e}")


def close_connection():
    cursor.close()
    connection.close()


if __name__ == "__main__":
    print("ЗАПУСК МОНИТОРИНГА ФАЙЛОВ")
    print(f"Мониторинг папки: {BASE_DIR}")
    print("=" * 50)
    #frf44
    try:
        monitor_files_with_delay()
    finally:
        close_connection()