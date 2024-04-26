import telebot
from telebot import types
from config import load_configuration
from TODO import *
from db_interact import *
from datetime import datetime
from data_parsing import *

# Путь к файлу конфигурации
config_path = "./config.ini"
try:
    config_data = load_configuration(config_path)
    admins = set(
        config_data["admins"]
    )  # Преобразуем список в множество для ускорения проверки
    print("Конфигурация успешно загружена.")
    print("Токен бота:", config_data["token"])
    print("Администраторы:", config_data["admins"])
    db_conn = db_connect("./dbconfig.ini")
    print("Подключение к БД успешно")
    bot = telebot.TeleBot(config_data["token"])
except Exception as e:
    print("Ошибка:", str(e))
    exit(1)


# ДЕКОРАТОР ADMIN ONLY COMMAND
def admin_required(func):
    def wrapped(message):
        user_username = message.from_user.username
        if not user_username:
            bot.send_message(
                message.chat.id,
                "Ваш профиль не имеет тега (username), который необходим для использования этой функции.",
            )
            return
        if not (user_username in admins or "@" + user_username in admins):
            bot.send_message(
                message.chat.id, "Извините, но эта команда только для администраторов."
            )
            return
        return func(message)

    return wrapped


@bot.message_handler(commands=["start"])
def handle_start(message):
    """
    Обработать начало работы с ботом, отправить приветствие.
    Если пользователь является администратором или не имеет установленного телеграм-тега, то указать на это.
    :param_name message: Сообщение от пользователя
    """
    # Получаем username пользователя в виде строки, если он есть
    user_username = message.from_user.username
    welcome_text = "Добро пожаловать в нашего бота!"
    if user_username:
        welcome_text += f" Ваш телеграм тег: @{user_username}."
        if user_username in admins or "@" + user_username in admins:
            welcome_text += " Вы являетесь администратором этого бота."
            db_add_user(db_conn, f"{user_username}", role_type_id=1)
            db_set_user_chatid(db_conn, user_username, message.chat.id)
        else:
            welcome_text += " Наслаждайтесь использованием!"
            db_add_user(db_conn, f"{user_username}", role_type_id=2)
            db_set_user_chatid(db_conn, user_username, message.chat.id)
    else:
        welcome_text += " Внимание: у Вас не установлен телеграм тег, некоторые функции могут быть недоступны."

    bot.send_message(message.chat.id, welcome_text)


@bot.message_handler(commands=["listme"])
def list_events_for_user(message):
    """
    Получить список мероприятий, на которые подписан пользователь, и связанных с ними задач.
    :param_name message: Сообщение от пользователя
    """
    # Получаем тег пользователя
    user_tag = message.from_user.username
    if not user_tag:
        bot.send_message(
            message.chat.id,
            "Ваш профиль не имеет тега (username), который необходим для использования этой функции.",
        )
        return

    # Вызываем функцию, которая возвращает список событий и дедлайны из базы данных
    user_id = db_get_user_by_tg(db_conn, user_tag)["id"]
    events = db_get_user_tasks(db_conn, user_id)

    if not events:
        bot.send_message(message.chat.id, "Вы пока не подписаны ни на одно событие.")
        return
    response_message = "Вы подписаны на следующие события и дедлайны:\n"
    grouped_tasks = {}
    for event in events:
        group_keyname = event["group_keyname"]
        if group_keyname not in grouped_tasks:
            grouped_tasks[group_keyname] = []
        grouped_tasks[group_keyname].append(event)
    for group, tasks in grouped_tasks.items():
        response_message += f"📅 {group}:\n"
        for task in tasks:
            deadline_str = task["deadline"].strftime("%Y-%m-%d %H:%M:%S")
            response_message += f"   - {task['name']}: {deadline_str}\n"
        remind_info = (
            f"Вы получите напоминание за {task['org_remind_in_minutes']} минут до дедлайна."
            if task["org_remind_in_minutes"] is not None
            else "Напоминание не установлено."
        )
        response_message += f"   {remind_info}\n"
    bot.send_message(message.chat.id, response_message)


# Словарь для управления состояниями пользователей и их данными
user_data = {}


def get_user_step(user_tag: str) -> str:
    """
    Получить текущее состояния пользователя (step)
    :param_name user_tag: Телеграм-тег пользователя без @
    """
    if user_tag in user_data:
        return user_data[user_tag]["step"]
    else:
        return "AWAITING_COMMANDS"


@bot.message_handler(commands=["newevent"])
@admin_required
def new_event(message):
    """
    Начать создание или редактирования мероприятия и перейти в состояние ожидания файла с информацией о задачах
    :param_name message: Сообщение от пользователя
    """
    user_tag = message.from_user.username
    if user_tag not in user_data:
        user_data[user_tag] = {"step": None, "file_id": None, "event_name": None}
    markup = types.ForceReply(selective=False)
    bot.send_message(
        message.chat.id,
        "Отправьте файл Excel с задачами и их дедлайнами, оформленный по шаблону.",
        reply_markup=markup,
    )
    user_data[user_tag]["step"] = "AWAITING_FILE"


@bot.message_handler(
    func=lambda message: get_user_step(message.from_user.username) == "AWAITING_FILE",
    content_types=["document"],
)
def handle_document(message):
    """
    Получить Excel файл с информацией о задачах или сообщить пользователю, что файл неверного формата
    :param_name message: Сообщение от пользователя
    """
    user_tag = message.from_user.username
    file_name = message.document.file_name
    if not (file_name.endswith(".xls") or file_name.endswith(".xlsx")):
        bot.send_message(message.chat.id, "Пожалуйста, отправьте файл в формате Excel.")
        return
    user_data[user_tag]["file_id"] = message.document.file_id
    file_id = user_data[user_tag]["file_id"]
    downloaded_file = bot.download_file(bot.get_file(file_id).file_path)
    try:
        data_list = parse_pandas_dataframe(parse_excel(downloaded_file))
        user_data[user_tag]["data_list"] = data_list
        user_data[user_tag]["step"] = "AWAITING_EVENT_NAME"
        bot.send_message(
            message.chat.id, "Файл принят. Теперь введите уникальное название мероприятия.")
    except ValueError:
        bot.send_message(
            message.chat.id, "Excel-файл заполнен с ошибками. Пожалуйста, обратите внимание на требуемый формат времени: YYYY-mm-dd HH:MM:SS"
        )


@bot.message_handler(
    func=lambda message: get_user_step(message.from_user.username)
    == "AWAITING_EVENT_NAME"
)
def event_name_received(message):
    """
    Получить название мероприятия. Оно должно быть уникальным и не длиннее, чем 12 символов
    :param_name message: Сообщение от пользователя
    """
    event_name = message.text
    if len(event_name) > 12:
        bot.send_message(
            message.chat.id,
            f"Название слишком длинное. Пожалуйста, введите название, длина которого не превышает 12 символов.",
        )
    elif '/' in event_name:
        bot.send_message(
            message.chat.id,
            f"Недопустимый символ для названия мероприятия: /. Повторите попытку",
        )
    else:
        user_tag = message.from_user.username
        user_data[user_tag]["step"] = "AWAITING_REMIND_TIME"
        user_data[user_tag]["event_name"] = event_name
        bot.send_message(
            message.chat.id,
            f"Пожалуйста, введите время в минутах, за которое отправляются уведомления всем получателям",
        )


@bot.message_handler(
    func=lambda message: get_user_step(message.from_user.username)
    == "AWAITING_REMIND_TIME"
)
def time_received(message):
    """
    Получить время в минутах, за которое отправляются уведомления всем получателям.
    Например, число 120 будет означать, что напоминание будет выслано за 2 часа до дедлайна.
    :param_name message: Сообщение от пользователя
    """
    try:
        user_tag = message.from_user.username
        remind_time = int(message.text)             # Попытка перевести текст сообщения в число
        if remind_time > 0:                         # Проверка на то, что число положительное
            event_name = user_data[user_tag]["event_name"]
            # Создание мероприятия, если его еще нет в БД
            db_add_task_group(db_conn, event_name, remind_time)     
            # Редактирование времени до дедлайна, если мероприятие уже есть в БД        
            db_set_task_group_remind(db_conn, db_get_task_group_by_keyname(db_conn, event_name)["id"], remind_time) 
            unique_participants = set()
            for event in user_data[user_tag]["data_list"]:
                unique_participants.update(event['participants'])
            for participant in unique_participants:
                if len(participant) >= 5:
                    db_add_user(db_conn, participant)
            filtered_events = [
                {**event, 'participants': [db_get_user_by_tg(db_conn, p)["id"] for p in event['participants'] if len(p) >= 5]}
                for event in user_data[user_tag]["data_list"]
            ]
            db_set_tasks(
                db_conn, filtered_events,
                db_get_task_group_by_keyname(db_conn, event_name)["id"],
                False,
            )
            bot.send_message(
                message.chat.id,
                f"Событие '{event_name}' создано/отредактировано.",
            )
            user_data[user_tag]["step"] = "AWAITING_COMMANDS"
        else:
            bot.send_message(message.chat.id, "Неверное число. Пожалуйста, введите целое положительное число")
    except ValueError:
        bot.send_message(message.chat.id, "Неверное число. Пожалуйста, введите целое положительное число")


@bot.message_handler(commands=["listall"])
@admin_required
def listall(message):
    """
    Получить список всех мероприятий и связанных с ними задач, созданных организаторами.
    :param_name message: Сообщение от пользователя
    """
    events = db_get_task_groups(db_conn)
    if not events:
        bot.send_message(
            message.chat.id, "В данный момент вы не создали ни одного события"
        )
    else:
        formatted_info = ""
        for event in events:
            tasks = db_get_tasks_in_group(db_conn, event['id'])
            unfinished_event_count = 0
            for task in tasks:
                if task['reminder_sent'] == 0:
                    unfinished_event_count += 1
                    break
            if unfinished_event_count == 0: continue
            formatted_info += (
                f"🔹 {event['keyname']}: \n"
                f"Задач: {event['n_tasks']}, "
                f"напоминание за {event['remind_in_minutes']} минут до начала.\n"
            )
        bot.send_message(message.chat.id, formatted_info)


@bot.message_handler(commands=["delete_task"])
@admin_required
def delete(message):
    user_tag = message.from_user.username
    if user_tag not in user_data:
        user_data[user_tag] = {}
    bot.send_message(message.chat.id, 'Введите название события, которое вы хотите удалить')
    user_data[user_tag]["step"] = "AWAITING_DELETION"


@bot.message_handler(func=lambda message: get_user_step(message.from_user.username)
    == "AWAITING_DELETION")
def deletion_name(message):
    user_tag = message.from_user.username
    user_data[user_tag]["step"] = "AWAITING_COMMANDS"
    task_name = message.text
    try:
        db_del_task_group(db_conn, db_get_task_group_by_keyname(db_conn, task_name)['id'])
        bot.send_message(message.chat.id, 'Удаление успешно')
    except:
        bot.send_message(message.chat.id, 'Пожалуйста, проверьте правильность введенного названия')