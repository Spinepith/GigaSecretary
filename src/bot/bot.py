import re
import sys
import time
import atexit
import signal
import threading

import telebot

from telebot import types

from . import utils
from . import gigasecretary

from ..db import db
from ..config import *


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

bot = telebot.TeleBot(BOT_TOKEN)

active_users = set()
employees = {}
pending_files = {}


keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(types.KeyboardButton('Классификация документа'))
keyboard.add(types.KeyboardButton('Остальные функции'))


@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(
        message.chat.id,
        '<b>Здравствуйте!\n'
        'Я - ваш умный секретарь РСЭД.\n\n</b>'
        'Здесь вы можете отправлять документы, получать шаблоны ответов и быть уверены, что они автоматически попадут в нужный отдел.\n'
        'Я понимаю свободную речь, поэтому вы можете просто написать свой вопрос, и я постараюсь помочь!\n\n'
        '<em>Основные действия осуществляются через кнопки - они помогут вам быстро найти нужную информацию.</em>',
        reply_markup=keyboard,
        parse_mode='html'
    )


@bot.message_handler(commands=['classdoc'])
def document_classification(message):
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text="Отменить", callback_data="<cancel>"))
    msg = bot.send_message(message.chat.id, "Отправьте файл (PDF, WORD, TXT) или текст для классификации", reply_markup=markup)
    bot.register_next_step_handler(msg, process_document)


@bot.message_handler(commands=['functions'])
def functions_list(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text='Классификация документа', callback_data=f'<classdoc>'))
    markup.add(types.InlineKeyboardButton(text='Маршрутизация документов', callback_data=f'<routing>'))
    markup.add(types.InlineKeyboardButton(text='Шаблоны документов', callback_data=f'<templates>'))
    markup.add(types.InlineKeyboardButton(text='Проверка на соответствие нормативам', callback_data=f'<checkdoc>'))

    bot.send_message(
        message.chat.id,
        "<b><em>СПИСОК ФУНКЦИЙ</em></b>",
        parse_mode="html",
        reply_markup=markup
    )


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(
        message.chat.id,
        '/classdoc - классификация документа\n'
        '/functions - список всех функций\n'
        '/help - список всех команд\n'
    )


@bot.message_handler(commands=[CHANGE_STATUS_COMMAND])
def change_status_command(message):
    if message.from_user.id not in employees:
        is_free = db.get_status(message.from_user.id)
        status = "я свободен" if is_free else "я занят"

        employees[message.from_user.id] = status
        keyboard.add(types.KeyboardButton(status))
        bot.send_message(message.chat.id, "вам доступна новая кнопка :)", reply_markup=keyboard)


@bot.message_handler(content_types=["document"])
def process_file(message):
    process_document(message)


@bot.message_handler(content_types=["text"])
def not_command(message):
    if message.text.lower() == 'классификация документа':
        document_classification(message)
    elif message.text.lower() == 'остальные функции':
        functions_list(message)
    elif message.from_user.id in employees:
        prev_status = "я свободен" if db.get_status(message.from_user.id) else "я занят"
        db.change_status(message.from_user.id)

        new_status = db.get_status(message.from_user.id)
        status_text = "я свободен" if new_status else "я занят"

        for row in keyboard.keyboard:
            for btn in row:
                btn_text = getattr(btn, "text", None) or btn.get("text", None)
                if btn_text in ("я занят", "я свободен"):
                    if isinstance(btn, dict):
                        btn["text"] = status_text
                    else:
                        btn.text = status_text

                    employees[message.from_user.id] = status_text
                    bot.send_message(
                        message.chat.id,
                        f"Вы изменили статус на: <b><em>{prev_status}</em></b>",
                        parse_mode="html",
                        reply_markup=keyboard
                    )
                    break
    else:
        utils.log_file(f'TG_ID: {message.from_user.id} - Пользователю будет отвечать GigaChat.')
        response = gigasecretary.ask(message.from_user.id, message.text)
        bot.send_message(message.chat.id, response)
        utils.log_file(f'TG_ID: {message.from_user.id} - Пользователю успешно ответил GigaChat.')


@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data == "<classdoc>":
        user_id = callback.from_user.id

        if user_id in active_users:
            bot.answer_callback_query(callback.id, "Подождите, обработка уже идёт...")
            return

        bot.answer_callback_query(callback.id)
        document_classification(callback.message)

    if callback.data == "<routing>":
        departments = [[i[1], f"<dprt>{i[0]}"] for i in db.get_departments_id()]
        bot.send_message(
            callback.message.chat.id,
            "<b><em>Выберите отдел, в который хотите отправить файл</em></b>",
            parse_mode="html",
            reply_markup=utils.inline_buttons_list("departments", departments, 0, 7)
        )

    if callback.data == "<templates>":
        pending_files[callback.from_user.id] = {
            "templates": [[j, f"<tmplt-give>{i}"] for i, j in enumerate(utils.get_templates())]
        }

        bot.send_message(
            callback.message.chat.id,
            "<b><em>ШАБЛОНЫ ДОКУМЕНТОВ</em></b>",
            parse_mode="html",
            reply_markup=utils.inline_buttons_list("templates-give", pending_files[callback.from_user.id]["templates"], 0, 7)
        )

    if callback.data == "<checkdoc>":
        pending_files[callback.from_user.id] = {
            "templates": [[j, f"<tmplt-compare>{i}"] for i, j in enumerate(utils.get_templates())]
        }
        bot.send_message(
            callback.message.chat.id,
            "Выберите шаблон для сравнения вашего файла",
            reply_markup=utils.inline_buttons_list("templates-compare", pending_files[callback.from_user.id]["templates"], 0, 7)
        )

    if callback.data == "<send>":
        bot.edit_message_reply_markup(callback.message.chat.id, callback.message.message_id, reply_markup=None)
        save_file(callback)

    if callback.data == "<cancel>":
        bot.edit_message_reply_markup(callback.message.chat.id, callback.message.message_id, reply_markup=None)
        active_users.discard(callback.from_user.id)
        bot.clear_step_handler(callback.message)
        bot.answer_callback_query(callback.id, "Процесс отменён")

    if "<dprt>" in callback.data:
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text="Отменить", callback_data="<cancel>"))
        msg = bot.send_message(callback.message.chat.id, "Отправьте файл (PDF, WORD, TXT) или текст для классификации", reply_markup=markup)
        department = db.get_department_name_by_id(callback.data.split(">")[1])
        bot.register_next_step_handler(msg, wait_file, department, True)

    if "<tmplt-give>" in callback.data:
        document_id = int(callback.data.split(">")[1])
        if not (callback.from_user.id in pending_files and "templates" in pending_files[callback.from_user.id]):
            pending_files[callback.from_user.id] = {
                "templates": [[j, f"<tmplt-give>{i}"] for i, j in enumerate(utils.get_templates())]
            }
        document_name = next((j[0] for i, j in enumerate(pending_files[callback.from_user.id]["templates"]) if i == document_id), None)

        if document_name:
            file_path = os.path.join(ROOT_DIR, "data", "templates", document_name)
            if os.path.exists(file_path):
                with open(file_path, "rb") as file:
                    extension = os.path.splitext(document_name)[1]
                    text = utils.extract_text(file.read(), extension)
                    # caption = gigasecretary.analyze_text(text)
                    caption = "Абобус Хаги Ваги 1000-7 зебра стакан Ъ"
                    file.seek(0)
                    bot.send_document(callback.message.chat.id, file, caption=caption, visible_file_name=document_name)
                return

        bot.send_message(
            callback.message.chat.id,
            "<b>ОШИБКА</b>\n\nНе удалось найти шаблон документа.\nПопробуйте еще раз.",
            parse_mode="html",
        )
        utils.log_file(f'TG_ID: {callback.from_user.id} -> Ошибка при попытке получить шаблон документа.')

    if "<tmplt-compare>" in callback.data:
        document_id = int(callback.data.split(">")[1])
        document_name = next((j[0] for i, j in enumerate(pending_files[callback.from_user.id]["templates"]) if i == document_id), None)
        msg = bot.send_message(
            callback.message.chat.id,
            f"<b>{document_name}</b>\n\nОтправьте файл, который хотите сравнить",
            parse_mode="html",
        )
        bot.register_next_step_handler(msg, compare_document, document_name)

    if callback.data.startswith("<page/"):
        buttons_list = []
        list_type = ""

        if callback.data.startswith("<page/departments>"):
            buttons_list = [[i[1], f"<dprt>{i[0]}"] for i in db.get_departments_id()]
            list_type = "departments"

        if callback.data.startswith("<page/templates-give>"):
            if not (callback.from_user.id in pending_files and "templates" in pending_files[callback.from_user.id]):
                pending_files[callback.from_user.id] = {
                    "templates": [[j, f"<tmplt-give>{i}"] for i, j in enumerate(utils.get_templates())]
                }
            buttons_list = pending_files[callback.from_user.id]["templates"]
            list_type = "templates-give"

        if callback.data.startswith("<page/templates-compare>"):
            if not (callback.from_user.id in pending_files and "templates" in pending_files[callback.from_user.id]):
                pending_files[callback.from_user.id] = {
                    "templates": [[j, f"<tmplt-compare>{i}"] for i, j in enumerate(utils.get_templates())]
                }
            buttons_list = pending_files[callback.from_user.id]["templates"]
            list_type = "templates-compare"

        new_page = int(callback.data.split(">")[1])
        bot.edit_message_reply_markup(
            callback.message.chat.id,
            callback.message.message_id,
            reply_markup=utils.inline_buttons_list(list_type, buttons_list, new_page, 7)
        )


def process_document(message):
    try:
        active_users.add(message.from_user.id)

        if message.content_type == 'text':
            bot.send_message(message.chat.id, "Обрабатываю текст")
            text = message.text
            classification_result = gigasecretary.analyze_document(message.from_user.id, text)
            bot.send_message(
                message.chat.id,
                f"<b>Результат классификации:</b>\n\n{classification_result}",
                parse_mode="html"
            )

        elif message.content_type == 'document':
            bot.send_message(message.chat.id, "Обрабатываю документ")
            wait_file(message)

            downloaded_file = pending_files[message.from_user.id]["content"]
            extension = pending_files[message.from_user.id]["extension"]

            text = utils.extract_text(downloaded_file, extension)
            classification_result = gigasecretary.analyze_document(message.from_user.id, text)
            department = re.search(r"\[Отдел:\s*(.+?)\]", classification_result)
            department = department.group(1).strip() if department else "Неизвестно"

            pending_files[message.from_user.id]["department"] = department

            markup = types.InlineKeyboardMarkup()
            if department != "Неизвестно":
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(text="Отправить", callback_data=f"<send>"))

            bot.send_message(
                message.chat.id,
                f"<b>Результат классификации:</b>\n\n{classification_result}",
                reply_markup=markup,
                parse_mode="html"
            )

        else:
            bot.send_message(
                message.chat.id,
                "<b>Произошла ошибка</b>.\nПожалуйста, отправьте текстовое сообщение или файл нужного формата",
                parse_mode="html"
            )
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, f"<b>Произошла ошибка</b>.\nПопробуйте еще раз.", parse_mode="html")
        utils.log_file(f'TG_ID: {message.from_user.id} -> Ошибка при попытке классификации документа.')

    finally:
        active_users.discard(message.from_user.id)


def compare_document(message, to_compare: str):
    try:
        active_users.add(message.from_user.id)

        if message.content_type == 'document':
            bot.send_message(message.chat.id, "Обрабатываю документ")
            wait_file(message)

            downloaded_file = pending_files[message.from_user.id]["content"]
            extension = pending_files[message.from_user.id]["extension"]
            user_text = utils.extract_text(downloaded_file, extension)

            template_path = os.path.join(ROOT_DIR, "data", "templates", to_compare)
            with open(template_path, "rb") as file:
                template_text = utils.extract_text(file.read(), os.path.splitext(template_path)[1])

            compare_result = gigasecretary.compare_documents(message.from_user.id, user_text, template_text)
            department = re.search(r"\[Отдел:\s*(.+?)\]", compare_result)
            department = department.group(1).strip() if department else ""

            pending_files[message.from_user.id]["department"] = department

            markup = types.InlineKeyboardMarkup()
            if department != "" or department != "Неизвестно":
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(text="Отправить", callback_data=f"<send>"))

            bot.send_message(
                message.chat.id,
                f"<b>Результат сравнения:</b>\n\n{compare_result}",
                reply_markup=markup,
                parse_mode="html"
            )

        else:
            bot.send_message(
                message.chat.id,
                "<b>Произошла ошибка</b>.\nПожалуйста, отправьте файл нужного формата",
                parse_mode="html"
            )
    except Exception as e:
        bot.send_message(message.chat.id, f"<b>Произошла ошибка</b>.\nПопробуйте еще раз.", parse_mode="html")
        utils.log_file(f'TG_ID: {message.from_user.id} -> Ошибка при сравнении пользовательского документа с шаблоном.')

    finally:
        active_users.discard(message.from_user.id)


def wait_file(message, department: str = None, save: bool = False):
    file = bot.get_file(message.document.file_id)

    downloaded_file = bot.download_file(file.file_path)
    file_name = os.path.splitext(message.document.file_name)[0]
    extension = os.path.splitext(message.document.file_name)[1]

    if extension not in (".pdf", ".doc", ".docx", ".txt"):
        bot.send_message(
            message.chat.id,
            "<b>Произошла ошибка</b>.\nПожалуйста, отправьте текстовое сообщение или файл нужного формата",
            parse_mode="html"
        )
        return

    pending_files[message.from_user.id] = {
        "department": department,
        "file_name": file_name,
        "extension": extension,
        "content": downloaded_file
    }

    if save:
        save_file(message)


def save_file(message):
    user_id = message.from_user.id
    chat_id = message.chat.id if isinstance(message, types.Message) else message.message.chat.id

    try:
        if user_id not in pending_files:
            raise Exception("Пользователь не найден в active_users")

        file_data = pending_files[user_id]
        department = file_data['department']
        filename = file_data['file_name']
        extension = file_data['extension']
        content = file_data['content']
        pending_files.clear()

        file_path = utils.unique_file_path(
            os.path.join(
                ROOT_DIR, "data", "departments", department, f"{filename}{extension}"
            )
        )

        with open(file_path, "wb") as file:
            file.write(content)

        db.insert_document(user_id, file_path, department)

        bot.send_message(
            chat_id,
            f"<b>УСПЕШНО</b>\n\nФайл {filename}{extension} отправлен в отдел {department}.",
            parse_mode="html"
        )
        utils.log_file(f'TG_ID: {user_id} -> Файл успешно отправлен в БД.')
    except:
        bot.send_message(
            chat_id,
            f"<b>ОШИБКА</b>\n\nФайл не был отправлен.\nПопробуйте еще раз.",
            parse_mode="html"
        )
        utils.log_file(f"TG_ID: {user_id} -> Ошибка при отправке файла")


def signal_handler(sig, name):
    sys.exit(0)


def start_bot():
    threading.Thread(target=db.monitor_files, daemon=True).start()
    threading.Thread(target=db.monitor_notifications, daemon=True).start()
    atexit.register(lambda: db.close_connection())
    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            print("\n# БОТ ЗАПУЩЕН\nЧТОБЫ ОСТАНОВИТЬ - НАЖМИТЕ Ctrl + C ИЛИ Control + C")
            utils.log_file("БОТ ЗАПУЩЕН")

            bot.polling(none_stop=False, interval=1, timeout=10)

            utils.log_file("БОТ ЗАВЕРШИЛ РАБОТУ")
            print("# БОТ ЗАВЕРШИЛ РАБОТУ\n")
        except Exception as e:
            utils.log_file(e)
            print(f"# КРИТИЧЕСКАЯ ОШИБКА. БОТ ЗАВЕРШИЛ РАБОТУ\n{e}\n\nБОТ БУДЕТ ПЕРЕЗАПУЩЕН ЧЕРЕЗ 5 СЕКУНД")
            time.sleep(5)
