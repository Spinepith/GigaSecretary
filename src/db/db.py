import time

import psycopg2

from ..bot import bot
from ..bot import utils
from ..config import *

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.join(ROOT_DIR, 'data', 'departments')

connection = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)
connection.autocommit = True
cursor = connection.cursor()


def get_departments():
    try:
        cursor.execute("SELECT name FROM departments ORDER BY name")
        departments = [row[0] for row in cursor.fetchall()]
        return departments
    except psycopg2.Error as e:
        utils.log_file(f"Ошибка при работе с бд -> {e}")
        return None


def get_departments_id():
    try:
        cursor.execute("SELECT id, name FROM departments ORDER BY name")
        departments = [list(row) for row in cursor.fetchall()]
        return departments
    except psycopg2.Error as e:
        utils.log_file(f"Ошибка при работе с бд -> {e}")
        return None


def get_department_id_by_name(department_name: str):
    try:
        cursor.execute("SELECT id, name FROM departments WHERE name = %s", (department_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        utils.log_file(f"Ошибка при получении ID отдела -> {e}")
        return None


def get_department_name_by_id(department_id: str):
    try:
        cursor.execute("SELECT id, name FROM departments WHERE id = %s", (department_id,))
        result = cursor.fetchone()
        return result[1] if result else None
    except psycopg2.Error as e:
        utils.log_file(f"Ошибка при получении ID отдела -> {e}")
        return None


def get_all_documents():
    try:
        cursor.execute("SELECT * FROM documents")
        return cursor.fetchall()
    except psycopg2.Error as e:
        utils.log_file(f"Ошибка при получении документов из БД -> {e}")
        return None


def delete_document(document_id: int):
    try:
        cursor.execute("DELETE FROM documents WHERE id = %s", (document_id,))
    except psycopg2.Error as e:
        utils.log_file(f"Ошибка при удалении документа из БД -> {e}")


def insert_document(id_author: int, file_path: str, department_name: str):
    try:
        corrected_path = os.path.normpath(file_path)

        exists = "СУЩЕСТВУЕТ" if os.path.exists(corrected_path) else "НЕ СУЩЕСТВУЕТ"
        utils.log_file(f"Файл {exists}: {corrected_path}")

        cursor.execute("SELECT id, name FROM departments WHERE name = %s", (department_name,))
        department_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO documents (id_author, file_path, department_id) VALUES (%s, %s, %s) RETURNING id, assigned_employee_id",
            (id_author, corrected_path, department_id)
        )

        result = cursor.fetchone()
        document_id = result[0]
        assigned_employee_id = result[1]

        abs_path = os.path.join(BASE_DIR, corrected_path)

        document_name = os.path.basename(abs_path)

        with open(abs_path, "rb") as file:
            bot.bot.send_document(
                assigned_employee_id,
                file,
                visible_file_name=document_name,
                caption=f"Вам назначен новый документ: {document_name}"
            )
        bot.update_status_button(assigned_employee_id, get_status(assigned_employee_id))

        utils.log_file(f"Документ успешно отправлен!")
        return document_id, assigned_employee_id

    except Exception as e:
        utils.log_file(f"Ошибка при отправке документа -> {e}")
        return None, None


def get_status(user_id: int):
    try:
        cursor.execute("SELECT is_busy FROM employees WHERE employee_id = %s", (str(user_id),))
        result = cursor.fetchone()
        return result[0] if result else False
    except (TypeError, psycopg2.Error) as e:
        utils.log_file(f"Ошибка при получении статуса сотрудника в БД -> {e}")


def change_status(user_id: int):
    try:
        status = get_status(user_id)
        cursor.execute(
            "UPDATE employees SET is_busy = %s WHERE employee_id = %s",
            (not status, str(user_id))
        )
    except (TypeError, psycopg2.Error) as e:
        utils.log_file(f"Ошибка при изменении статуса сотрудника в БД -> {e}")


def is_employee(tg_id: str):
    try:
        cursor.execute("SELECT 1 FROM employees WHERE employee_id = %s LIMIT 1;", (tg_id,))
        result = cursor.fetchone()
        return result is not None
    except Exception as e:
        utils.log_file(f"Ошибка при проверке сотрудника: {e}")
        return False


def monitor_files(delay_seconds: int = 20):
    try:
        while True:
            utils.log_file("ПРОВЕРКА ФАЙЛОВ")

            if not os.path.exists(BASE_DIR):
                utils.log_file(f"Папка {BASE_DIR} не существует")
                time.sleep(delay_seconds)
                continue

            db_documents = get_all_documents() or []
            departments = get_departments() or []

            deleted_count = 0
            new_files_count = 0

            # Проверка удаленных файлов
            for doc in db_documents:
                doc_id = doc[0]  # ID
                file_path = doc[3]  # file_path
                full_path = os.path.join(BASE_DIR, file_path)

                if not os.path.exists(full_path):
                    utils.log_file(f"Удален файл: {file_path}")
                    delete_document(doc_id)
                    deleted_count += 1

            # Поиск новых файлов
            for root, dirs, files in os.walk(BASE_DIR):
                for file in files:
                    full_path = os.path.join(root, file)
                    corrected_path = os.path.normpath(full_path)
                    department_name = os.path.basename(root)

                    # Проверяем, есть ли уже такой файл в БД
                    existing_doc = next((doc for doc in db_documents if doc[3] == corrected_path), None)
                    author_id = existing_doc[1] if existing_doc else -1

                    if not existing_doc and department_name in departments:
                        utils.log_file(f"Добавлен файл: {file} в отдел '{department_name}'")
                        doc_id, assigned_employee = insert_document(author_id, corrected_path, department_name)
                        if doc_id:
                            new_files_count += 1
                    elif not existing_doc:
                        utils.log_file(f"Файл в неизвестном отделе: {file} (папка '{department_name}')")

            if deleted_count > 0 or new_files_count > 0:
                utils.log_file(f"Итог: удалено {deleted_count}, добавлено {new_files_count}")
            else:
                utils.log_file("Изменений нет")

            time.sleep(delay_seconds)

    except Exception as e:
        utils.log_file(f"Ошибка при мониторинге файлов -> {e}")


def close_connection():
    cursor.close()
    connection.close()
