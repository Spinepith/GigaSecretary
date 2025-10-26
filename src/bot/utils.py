import os
import tempfile
import traceback

from datetime import datetime

import docx
import PyPDF2

from telebot import types


# РАБОТА С ФАЙЛАМИ
def extract_text(downloaded_file: bytes, extension: str):
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
        temp_file.write(downloaded_file)
        temp_file_path = temp_file.name
        
    try:
        text_content = extract_text_from_file(temp_file_path, extension)
        if text_content:
            return text_content
        else:          
            return "Не удалось извлечь текст из файла"
        
    except Exception as e:
        log_file(f"Ошибка при обработке файла -> {e}")
    
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def extract_text_from_file(file_path: str, extension: str):
    match extension:
        case ".pdf":
            return text_from_pdf(file_path)
        case ".docx" | ".doc":
            return text_from_docx(file_path)
        case ".txt":
            return text_from_txt(file_path)
        case _:
            return None
        

def text_from_pdf(file_path: str):
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        log_file(f"Ошибка при чтении PDF -> {e}")


def text_from_docx(file_path: str):
    try:
        text = ""
        doc = docx.Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        log_file(f"Ошибка при чтении DOCX -> {e}")


def text_from_txt(file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except Exception as e:
        log_file(f"Ошибка при чтении TXT -> {e}")


def unique_file_path(file_path):
    base, ext = os.path.splitext(file_path)
    counter = 1

    while os.path.exists(file_path):
        file_path = f"{base} ({counter}){ext}"
        counter += 1

    return file_path


# КРАСИВЫЙ СПИСОК КНОПОК
def inline_buttons_list(list_name: str, buttons_list: list[list[str]], current_page: int = 1, max_buttons: int = 1):
    markup = types.InlineKeyboardMarkup()

    pages_count = (len(buttons_list) + max_buttons - 1) // max_buttons

    start = current_page * max_buttons
    end = start + max_buttons
    page_buttons = buttons_list[start:end]

    for button_text, button_callback in page_buttons:
        markup.add(types.InlineKeyboardButton(text=button_text, callback_data=button_callback))

    if pages_count > 1:
        prev_page = current_page - 1 if current_page > 0 else pages_count - 1
        button_prev = types.InlineKeyboardButton(text='<', callback_data=f'<page/{list_name}>{prev_page}')

        button_page = types.InlineKeyboardButton(text=f'{current_page + 1}/{pages_count}', callback_data='page_button')

        next_page = current_page + 1 if current_page < pages_count - 1 else 0
        button_next = types.InlineKeyboardButton(text='>', callback_data=f'<page/{list_name}>{next_page}')

        markup.row(button_prev, button_page, button_next)

    return markup


# ЛОГИРОВАНИЕ КЛЮЧЕВЫХ ДЕЙСТВИЙ
def log_file(data: str | Exception):
    path = 'logs'
    os.makedirs(path, exist_ok=True)

    is_error = isinstance(data, Exception)
    prefix = "ERROR" if is_error else "ACTION"

    existing_files = [f for f in os.listdir(path) if f.startswith(prefix)]
    current_file = None
    if existing_files:
        existing_files.sort()
        candidate = os.path.join(path, existing_files[-1])
        if os.path.getsize(candidate) < 1 * 1024 * 1024 * 1024:
            current_file = candidate

    if not current_file:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        current_file = os.path.join(path, f"{prefix}_{timestamp}.log")

    if is_error:
        log_text = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {str(data)}\n"
        log_text += traceback.format_exc() + "\n\n"
    else:
        log_text = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {data}\n"

    with open(current_file, "a", encoding="utf-8") as f:
        f.write(log_text)
