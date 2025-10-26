import re
import atexit
import threading

import telebot

from telebot import types

from . import utils
from . import gigasecretary

from ..db import db
from ..config import *


bot = telebot.TeleBot(BOT_TOKEN)

active_users = set()
pending_files = {}


@bot.message_handler(commands=['start'])
def start_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Классификация документа'))
    markup.add(types.KeyboardButton('Остальные функции'))

    bot.send_message(
        message.chat.id,
        '<b>Здравствуйте!\n'
        'Я - ваш умный секретарь РСЭД.\n\n</b>'
        'Здесь вы можете отправлять документы, получать шаблоны ответов и быть уверены, что они автоматически попадут в нужный отдел.\n'
        'Я понимаю свободную речь, поэтому вы можете просто написать свой вопрос, и я постараюсь помочь!\n\n'
        '<em>Основные действия осуществляются через кнопки - они помогут вам быстро найти нужную информацию.</em>',
        reply_markup=markup,
        parse_mode='html'
    )


@bot.message_handler(commands=['classdoc'])
def document_classification(message):
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text="Отменить", callback_data="<cancel>"))
    msg = bot.send_message(message.chat.id, "Отправьте файл (.pdf, .docx, .txt) или текст для классификации", reply_markup=markup)
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


@bot.message_handler(content_types=["document"])
def process_file(message):
    process_document(message)


@bot.message_handler(content_types=["text"])
def not_command(message):
    if message.text.lower() == 'классификация документа':
        document_classification(message)
    elif message.text.lower() == 'остальные функции':
        functions_list(message)
    else:
        pass
        # utils.log_file(f'TG_ID: {message.from_user.id} - Пользователю будет отвечать GigaChat.')
        #
        # user_id = message.from_user.id
        # vacancies_list = db.get_vacancies()
        # response = gigasecretary.get_response(user_id, message.text, vacancies_list)
        #
        # bot.send_message(user_id, response)
        # utils.log_file(f'TG_ID: {message.from_user.id} - Пользователю успешно ответил GigaChat.')


@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data == "<classdoc>":
        user_id = callback.from_user.id

        if user_id in active_users:
            bot.answer_callback_query(callback.id, "Подождите, обработка уже идёт...")
            return

        active_users.add(user_id)
        bot.answer_callback_query(callback.id)
        document_classification(callback.message)

    if callback.data == "<routing>":
        pass

    if callback.data == "<cancel>":
        bot.edit_message_reply_markup(callback.message.chat.id, callback.message.message_id, reply_markup=None)
        active_users.discard(callback.from_user.id)
        bot.clear_step_handler(callback.message)
        bot.answer_callback_query(callback.id, "Процесс отменён")

    if "<send>" in callback.data:
        bot.edit_message_reply_markup(callback.message.chat.id, callback.message.message_id, reply_markup=None)
        try:
            user_id = callback.from_user.id

            if user_id not in pending_files:
                bot.answer_callback_query(callback.id, "Файл не найден")
                return

            file_data = pending_files[user_id]
            department = file_data['department']
            filename = file_data['file_name']
            extension = file_data['extension']
            content = file_data['content']

            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = str(os.path.join(root_dir, "data", department, f"{filename}{extension}"))

            with open(file_path, "wb") as file:
                file.write(content)

            db.insert_document(user_id, file_path, department)

            bot.send_message(
                callback.message.chat.id,
                f"<b>УСПЕШНО</b>\n\nФайл {filename}{extension} отправлен в отдел {department}.",
                parse_mode="html"
            )

        except:
            bot.send_message(
                callback.message.chat.id,
                f"<b>ОШИБКА</b>\n\nФайл не был отправлен.\nПопробуйте еще раз.",
                parse_mode="html"
            )
            utils.log_file(f"TG_ID: {callback.from_user.id} -> Ошибка при отправке файла")


def process_document(message):
    try:
        if message.content_type == 'text':
            bot.send_message(message.chat.id, "Обрабатываю текст")
            text = message.text
            classification_result = gigasecretary.analyze_document(text)
            bot.send_message(
                message.chat.id,
                f"<b>Результат классификации:</b>\n\n{classification_result}",
                parse_mode="html"
            )

        elif message.content_type == 'document':
            bot.send_message(message.chat.id, "Обрабатываю документ")
            file = bot.get_file(message.document.file_id)

            downloaded_file = bot.download_file(file.file_path)
            file_name = os.path.splitext(message.document.file_name)[0]
            extension = os.path.splitext(message.document.file_name)[1]

            text = utils.extract_text(downloaded_file, extension)
            classification_result = "{department: Аналитический отдел}"
            department = re.search(r"\{department:\s*(.+?)\}", classification_result)
            department = department.group(1).strip() if department else ""
            all_departments = db.get_departments()

            pending_files[message.from_user.id] = {
                "department": department,
                "file_name": file_name,
                "extension": extension,
                "content": downloaded_file
            }

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="Отправить", callback_data=f"<send>"))
            if all_departments:
                for i in all_departments:
                    markup.add(types.InlineKeyboardButton(text=i, callback_data=f"a123"))

            bot.send_message(
                message.chat.id,
                f"<b>Результат классификации:</b>\n\n{classification_result}",
                reply_markup=markup,
                parse_mode="html"
            )
            
        else:
            bot.send_message(message.chat.id, "<b>Произошла ошибка</b>.\nПожалуйста, отправьте текстовое сообщение или файл", parse_mode="html")
    except:
        bot.send_message(message.chat.id, f"<b>Произошла ошибка</b>.\nПопробуйте еще раз.", parse_mode="html")
        utils.log_file(f'TG_ID: {message.from_user.id} -> Ошибка при попытке классификации документа.')

    finally:
        active_users.discard(message.from_user.id)


def start_bot():
    try:
        print("\n# БОТ ЗАПУЩЕН\nЧТОБЫ ОСТАНОВИТЬ - НАЖМИТЕ Ctrl + C ИЛИ Control + C")
        utils.log_file("БОТ ЗАПУЩЕН")

        threading.Thread(target=db.monitor_files, daemon=True).start()
        threading.Thread(target=db.monitor_notifications, daemon=True).start()

        atexit.register(lambda: db.close_connection())
        bot.polling()

        utils.log_file("БОТ ЗАВЕРШИЛ РАБОТУ")
        print("# БОТ ЗАВЕРШИЛ РАБОТУ\n")
    except Exception as e:
        utils.log_file(e)
        print(f"# БОТ ЗАВЕРШИЛ РАБОТУ С ОШИБКОЙ\n{e}\n")
