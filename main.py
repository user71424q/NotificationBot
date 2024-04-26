import telebot
from config import load_configuration
from commands import bot
from threading import Thread
import time
from db_interact import *

def get_message_text(db_conn, task_id: int) -> str:
    """
    Получить текст напоминания для конкретной задачи
    :param_name task_id: id задачи
    """
    # Получаем задачу по ее id
    task = db_get_task_by_id(db_conn, task_id)
    # Формируем текст сообщения
    message_text = (
        f"❗Приближается дедлайн задачи \"{task['name']}\" по \"{task['keyname']}\"❗\n\n"
        f"📆 {task['deadline']}\n\n"
        f"Описание задачи: {task['description']}"
    )
    return message_text


def send_notifications():
    """
    Отправить напоминания о задачах участникам, подписанным на них. Проверка необходимости отправки осуществляется 2 раза в минуту
    """
    db_conn = db_connect("./dbconfig.ini")
    while True:
        time.sleep(30)  # Пауза между проверками уведомлений в секундах
        # Рассылка напоминаний, установленных организаторами
        db_disconnect(db_conn)
        db_conn = db_connect("./dbconfig.ini")
        tasks = db_get_tasks_unnotified_for_groups(db_conn)
        if not tasks:
            continue
        tasks_receivers = []
        for task in tasks:
            users = db_get_task_participants(db_conn, task['task_id'])
            for user in users:
                tasks_receivers.append({'user': user, 'task_id': task['task_id']})
        # Рассылка напоминаний, установленных участниками
        notification_info = db_get_tasks_unnotified_for_users(db_conn)
        for info in notification_info:
            user_id = info['user_id']
            task_id = info['task_id']
            tasks_receivers.append({'user': db_get_user(db_conn, user_id), 'task_id': task_id})
        for notificaton in tasks_receivers:
            try:
                bot.send_message(notificaton['user']['tg_chatid'], get_message_text(db_conn, notificaton['task_id']))
                db_reminder_mark_as_sent_for_group(db_conn, notificaton['task_id'])
            except telebot.apihelper.ApiException as e:
                print(
                    f"Не удалось отправить сообщение пользователю {notificaton['user']['tg_nick']}, возможно он не начинал диалог с ботом: {str(e)}"
                )


notification_thread = Thread(target=send_notifications)
notification_thread.start()

bot.polling(none_stop=True)
