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


def insert_document(id_author: str, file_path: str, department_name: str):
    try:
        cursor.execute("SELECT id, name FROM departments WHERE name = %s", (department_name,))
        department_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO documents (id_author, file_path, department_id) VALUES (%s, %s, %s)",
            (id_author, file_path, department_id)
        )
    except (TypeError, psycopg2.Error) as e:
        utils.log_file(f"Ошибка при добавлении документа в БД -> {e}")


def get_status(user_id: int):
    try:
        cursor.execute("SELECT is_busy FROM employees WHERE employee_id = %s", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else False
    except (TypeError, psycopg2.Error) as e:
        utils.log_file(f"Ошибка при получении статуса сотрудника в БД -> {e}")


def change_status(user_id: int):
    try:
        status = get_status(user_id)
        cursor.execute(
            "UPDATE employees SET is_busy = %s WHERE employee_id = %s",
            (not status, user_id)
        )
    except (TypeError, psycopg2.Error) as e:
        utils.log_file(f"Ошибка при изменении статуса сотрудника в БД -> {e}")


def monitor_files(delay_seconds: int = 60):
    try:
        while True:
            utils.log_file("ПРОВЕРКА ФАЙЛОВ")

            if not os.path.exists(BASE_DIR):
                utils.log_file(f"Папка {BASE_DIR} не существует")
                time.sleep(delay_seconds)
                continue

            db_documents = get_all_documents() or []

            id_index = 0
            author_id_index = 1
            file_path_index = 3

            deleted_count = 0
            new_files_count = 0

            for doc in db_documents:
                doc_id = doc[id_index]
                file_path = doc[file_path_index]
                full_path = os.path.join(BASE_DIR, file_path)

                if not os.path.exists(full_path):
                    utils.log_file(f"Удален файл: {file_path}")
                    delete_document(doc_id)
                    deleted_count += 1

            all_files_found = []

            for root, dirs, files in os.walk(BASE_DIR):
                if root == BASE_DIR and not files:
                    continue

                for file in files:
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, BASE_DIR)
                    department_name = os.path.basename(root)
                    all_files_found.append((relative_path, file, department_name))

            for relative_path, file, department_name in all_files_found:
                existing_doc = next((doc for doc in db_documents if doc[file_path_index] == relative_path), None)

                if existing_doc:
                    author_id = existing_doc[author_id_index]
                    departments = get_departments()

                    if department_name in departments:
                        utils.log_file(f"Добавлен файл: {file} в отдел '{department_name}'")
                        insert_document(author_id, relative_path, department_name)
                        new_files_count += 1
                    else:
                        utils.log_file(f"Файл в неизвестном отделе: {file} (папка '{department_name}')")

            if deleted_count > 0 or new_files_count > 0:
                utils.log_file(f"Итог: удалено {deleted_count}, добавлено {new_files_count}")
            else:
                utils.log_file("Изменений нет")

            time.sleep(delay_seconds)

    except Exception as e:
        utils.log_file(f"Ошибка при мониторинге файлов -> {e}")


def monitor_notifications(delay_seconds: int = 60):
    prev_status = {}

    try:
        while True:
            try:
                cursor.execute("SELECT employee_id, is_busy FROM employees")
                rows = cursor.fetchall() or []

                for employee_id, is_busy in rows:
                    was = prev_status.get(employee_id)

                    if was is None:
                        prev_status[employee_id] = is_busy
                        continue

                    if was is False and is_busy is True:
                        cursor.execute(
                            """
                            SELECT id, file_path 
                            FROM documents
                            WHERE assigned_employee_id = %s
                            ORDER BY id DESC LIMIT 1
                            """,
                            (employee_id,)
                        )
                        doc = cursor.fetchone()

                        if doc:
                            doc_id, file_path = doc
                            abs_path = os.path.join(BASE_DIR, file_path)

                            if os.path.exists(abs_path):
                                try:
                                    with open(abs_path, "rb") as file:
                                        bot.send_document(int(employee_id), file, visible_file_name=os.path.basename(file_path))
                                    utils.log_file(f"Файл '{file_path}' отправлен сотруднику {employee_id} (doc_id={doc_id})")
                                except Exception as e:
                                    utils.log_file(f"Ошибка отправки файла сотруднику {employee_id}: {e}")
                            else:
                                utils.log_file(f"Файл не найден для документа {doc_id}: {abs_path}")

                    prev_status[employee_id] = is_busy

            except Exception as loop_err:
                utils.log_file(f"Ошибка в цикле monitor_notifications: {loop_err}")

            time.sleep(delay_seconds)

    except Exception as e:
        utils.log_file(f"Критическая ошибка monitor_notifications: {e}")

def close_connection():
    cursor.close()
    connection.close()
