import pymysql
import pymysql.cursors
import configparser


COLLIST_SELECT_USER = "user.id, user.tg_nick, role.name as role, user.tg_chatid"
TABLE_SELECT_USER = "user LEFT JOIN role on (user.role_id = role.id)"
COLLIST_SELECT_TASK_BASE = "task.id, task.name, task.description, task.deadline, task.reminder_sent"


def db_connect(config_path: str):
    """
    Начать сеанс соединения с базой данных в MySQL
    :returns: объект сеанса соединения с базой данных в MySQL
    :param_name config_path: путь к файлу конфигурации подключения к базе данных в MySQL
    Файл конфигурации должен быть формата .ini и содержать заголовок [Connection] со следующими ключами:
    > ip - IP (или домен) сервера, на котором запущена СУБД MySQL (или MariaDB)
    > port - порт, на котором вещает MySQL
    > username - Имя пользователя MySQL с правами доступа к БД системы
    > password - Пароль пользователя MySQL
    > dbname - Наименование базы данных в MySQL
    > dbcharset - Кодировка в БД (обычно выставляют utf8mb4)
    """
    conf = configparser.ConfigParser()
    conf.read(config_path)
    conf_conn = conf["Connection"]
    ip = conf_conn["ip"]
    port = int(conf_conn["port"])
    username = conf_conn["username"]
    password = conf_conn["password"]
    dbname = conf_conn["dbname"]
    charset = conf_conn["dbcharset"]
    dbconn = pymysql.connect(
        host=ip,
        port=port,
        user=username,
        password=password,
        db=dbname,
        charset=charset,
        cursorclass=pymysql.cursors.DictCursor,
    )
    return dbconn


def db_disconnect(dbconn):
    """
    Завершить сеанс соединения с базой данных в MySQL
    """
    dbconn.close()


def db_get_roles(dbconn):
    """
    Список уровней доступа пользователей в системе
    """
    query = "SELECT id, name as role FROM role"
    with dbconn.cursor() as dbc:
        dbc.execute(query)
        return dbc.fetchall()


def db_get_users(dbconn):
    """
    Список пользователей
    """
    global COLLIST_SELECT_USER
    global TABLE_SELECT_USER
    query = "SELECT " + COLLIST_SELECT_USER + " FROM " + TABLE_SELECT_USER
    with dbconn.cursor() as dbc:
        dbc.execute(query)
        return dbc.fetchall()


def db_get_user(dbconn, user_id: int):
    """
    Данные о пользователе по id в БД
    """
    global COLLIST_SELECT_USER
    global TABLE_SELECT_USER
    query = (
        "SELECT "
        + COLLIST_SELECT_USER
        + " FROM "
        + TABLE_SELECT_USER
        + " WHERE user.id = %s"
    )
    params = [user_id]
    with dbconn.cursor() as dbc:
        dbc.execute(query, params)
        return dbc.fetchone()


def db_get_user_by_tg(dbconn, user_tg_nick: str):
    """
    Данные о пользователе по никнейму в Telegram
    """
    global COLLIST_SELECT_USER
    global TABLE_SELECT_USER
    query = (
        "SELECT "
        + COLLIST_SELECT_USER
        + " FROM "
        + TABLE_SELECT_USER
        + " WHERE user.tg_nick = %s"
    )
    params = [user_tg_nick]
    with dbconn.cursor() as dbc:
        dbc.execute(query, params)
        return dbc.fetchone()


def db_get_user_by_tg_chatid(dbconn, user_tg_chatid: int):
    """
    Данные о пользователе по идентификатору чата с ним в Telegram
    """
    global COLLIST_SELECT_USER
    global TABLE_SELECT_USER
    if user_tg_chatid == 0:
        return None
    query = (
        "SELECT "
        + COLLIST_SELECT_USER
        + " FROM "
        + TABLE_SELECT_USER
        + " WHERE user.tg_chatid = %s"
    )
    params = [user_tg_chatid]
    with dbconn.cursor() as dbc:
        dbc.execute(query, params)
        return dbc.fetchone()


def db_get_user_tasks(dbconn, user_id: int):
    """
    Список задач, назначенных пользователю с заданным id
    """
    global COLLIST_SELECT_TASK_BASE
    query = (
        "SELECT "
        + COLLIST_SELECT_TASK_BASE
        + ", task_group.keyname as group_keyname, task_group.remind_in_minutes as org_remind_in_minutes, user_task.again_remind_in_minutes as participant_remind_in_minutes FROM user_task LEFT JOIN task on (task_id=task.id) LEFT JOIN task_group on (task_group_id=task_group.id) WHERE user_id = %s AND task.deadline > now()"
    )
    params = [user_id]
    with dbconn.cursor() as dbc:
        dbc.execute(query, params)
        return dbc.fetchall()


def db_get_task_group_by_keyname(dbconn, keyname: str):
    """
    (Организатор) Группа задач по ключу (keyname)
    """
    query = "SELECT task_group.id, keyname, remind_in_minutes, count(task.id) as n_tasks FROM task_group left join task on (task_group_id=task_group.id) WHERE keyname = %s GROUP BY task_group_id"
    params = [keyname]
    with dbconn.cursor() as dbc:
        dbc.execute(query, params)
        return dbc.fetchone()


def db_get_tasks_in_group(dbconn, task_group_id: int):
    """
    (Организатор) Список задач в группе с заданным id
    """
    global COLLIST_SELECT_TASK_BASE
    query = (
        "SELECT "
        + COLLIST_SELECT_TASK_BASE
        + " FROM task LEFT JOIN task_group on (task_group_id=task_group.id) WHERE task_group.id = %s"
    )
    params = [task_group_id]
    with dbconn.cursor() as dbc:
        dbc.execute(query, params)
        return dbc.fetchall()


def db_get_task_groups(dbconn):
    """
    (Организатор) Список групп задач
    """
    # query = 'SELECT id, keyname, remind_in_minutes FROM task_group'
    query = "SELECT task_group.id, keyname, remind_in_minutes, count(task.id) as n_tasks FROM task_group left join task on (task_group_id=task_group.id) GROUP BY task_group_id"
    with dbconn.cursor() as dbc:
        dbc.execute(query)
        return dbc.fetchall()


def db_get_task_by_id(dbconn, task_id):
    """
    (Система) Задача по ее id
    """
    query = "SELECT task.name, task.description, task.deadline, task_group.keyname FROM task_group INNER JOIN task ON task.task_group_id = task_group.id WHERE task.id = %s"
    params = [task_id]
    with dbconn.cursor() as dbc:
        dbc.execute(query, params)
        return dbc.fetchone()



def db_get_task_participants(dbconn, task_id: int):
    """
    (Организатор) Список участников, которым была назначена задача с заданным id
    """
    global COLLIST_SELECT_USER
    query = (
        "SELECT "
        + COLLIST_SELECT_USER
        + " FROM task INNER JOIN user_task on (task.id=task_id) LEFT JOIN user on (user_id=user.id) LEFT JOIN role on (role_id=role.id) WHERE task.id = %s"
    )
    params = [task_id]
    with dbconn.cursor() as dbc:
        dbc.execute(query, params)
        return dbc.fetchall()


def db_add_user(
    dbconn, tg_nick: str, tg_chatid: int = 0, role_type_id: int | None = None
):
    """
    (Организатор) Добавить пользователя в систему
    :param_name tg_nick: никнейм в Telegram
    :param_name tg_chatid: id чата с пользователем в Telegram (0 - не получен)
    :param_name role_type_id: номер уровня доступа к системе (1 - организатор, 2 - участник (по умолчанию))
    """
    if role_type_id == None:
        query = "INSERT IGNORE INTO user(tg_nick, tg_chatid) VALUES (%s, %s)"
        params = [tg_nick, tg_chatid]
    else:
        query = (
            "INSERT IGNORE INTO user(tg_nick, role_id, tg_chatid) VALUES (%s, %s, %s)"
        )
        params = [tg_nick, role_type_id, tg_chatid]
    with dbconn.cursor() as dbc:
        dbc.execute(query, params)
        dbconn.commit()
        return dbc.lastrowid


def db_set_user_chatid(dbconn, tg_nick: str, tg_chatid: int):
    """
    (Система) Установить id чата с пользователем в Telegram
    :param_name tg_nick: никнейм пользователя в Telegram
    :param_name tg_chatid: новый id чата с пользователем в Telegram
    """
    query = "UPDATE user SET tg_chatid = %s WHERE tg_nick = %s"
    params = [tg_chatid, tg_nick]
    with dbconn.cursor() as dbc:
        n_rows = dbc.execute(query, params)
        dbconn.commit()
        return n_rows != 0


def db_add_task_group(dbconn, keyname: str, remind_in_minutes: int | None = None):
    """
    (Организатор) Добавить группу задач
    :param_name keyname: ключ группы
    :param_name remind_in_minutes: напомнить через минуту
    """
    if remind_in_minutes == None:
        query = "INSERT IGNORE INTO task_group(keyname) VALUES (%s)"
        params = [keyname]
    else:
        query = (
            "INSERT IGNORE INTO task_group(keyname, remind_in_minutes) VALUES (%s, %s)"
        )
        params = [keyname, remind_in_minutes]
    with dbconn.cursor() as dbc:
        dbc.execute(query, params)
        dbconn.commit()
        return dbc.lastrowid


def db_set_tasks(
    dbconn, tasks: list, task_group_id: int, add_mode: bool = True
):  # TODO: НЕОБХОДИМО ТЕСТИРОВАНИЕ. #FIXME преобразовывать deadline в правильную mysql-строку типа datetime
    """
    (Организатор) Заменить задачи в группе (add_mode = False) или добавить к существующим (add_mode = True)
    :param_name tasks: список из словарей с задачами
    :param_name task_group_id: id группы задач
    :param_name add_mode: False - заменить задачи, True - добавить новые задачи
    """
    with dbconn.cursor() as dbc:
        query = "SELECT * FROM task_group WHERE id = %s"
        params = [task_group_id]
        n_groups_by_id_count = dbc.execute(query, params)
        if n_groups_by_id_count == 0:
            raise ValueError("Не найдена такая группа задач")
        if not add_mode:
            query = "DELETE IGNORE FROM task WHERE task_group_id = %s"
            params = [task_group_id]
            dbc.execute(query, params)  # delete tasks of specified group
        query = "INSERT INTO task(name, description, deadline, task_group_id) VALUES (%s, %s, %s, %s)"
        query_sub = "INSERT INTO user_task(user_id, task_id) VALUES (%s, %s)"
        for task in tasks:
            params = [
                task["name"],
                task["description"],
                task["deadline"],
                task_group_id,
            ]
            dbc.execute(query, params)  # insert new task
            rec_id = dbc.lastrowid
            # получить rec_id (id новой записи)
            for task_user_id in task["participants"]:
                params_sub = [task_user_id, rec_id]
                dbc.execute(query_sub, params_sub)
        dbconn.commit()


def db_del_user(dbconn, user_id: int):
    """
    (Организатор) Удалить пользователя из системы
    """
    query = "DELETE FROM user WHERE id = %s"
    params = [user_id]
    with dbconn.cursor() as dbc:
        n_rows = dbc.execute(query, params)
        dbconn.commit()
        return n_rows != 0


def db_del_task_group(dbconn, task_group_id: int):
    """
    (Организатор) Удалить группу задач из системы (вместе с ней удалятся задачи, принадлежащие этой группе)
    """
    query = "DELETE FROM task_group WHERE id = %s"
    params = [task_group_id]
    with dbconn.cursor() as dbc:
        n_rows = dbc.execute(query, params)
        dbconn.commit()
        return n_rows != 0


def db_task_deattach_participant(dbconn, task_id: int, user_id: int):
    """
    (Организатор) Убрать пользователя с id = user_id из списка исполнителей задачи с id = task_id
    """
    query = "DELETE FROM user_task WHERE task_id = %s AND user_id = %s"
    params = [task_id, user_id]
    with dbconn.cursor() as dbc:
        n_rows = dbc.execute(query, params)
        return n_rows != 0


def db_task_deattach_all_participants(dbconn, task_id: int):
    """
    (Организатор) Убрать всех пользователей из списка исполнителей задачи с id = task_id
    """
    query = "DELETE FROM user_task WHERE task_id = %s"
    params = [task_id]
    with dbconn.cursor() as dbc:
        n_rows = dbc.execute(query, params)
        dbconn.commit()
        return n_rows != 0


def db_set_task_group_remind(dbconn, task_group_id: int, remind_mins: int):
    """
    (Организатор) Установить срок напоминания о дедлайне для группы задач
    :param_name remind_mins: за сколько минут до дедлайна
    """
    query = "UPDATE task_group SET remind_in_minutes = %s WHERE id = %s"
    params = [remind_mins, task_group_id]
    with dbconn.cursor() as dbc:
        n_rows = dbc.execute(query, params)
        dbconn.commit()
        return n_rows != 0


def db_set_task_participant_remind(
    dbconn, task_id: int, user_id: int, remind_mins: int
):
    """
    (Участник) Установить индивидуальный срок напоминания о дедлайне для задачи
    :param_name task_id: id задачи
    :param_name user_id: id пользователя - исполнителя задачи
    :param_name remind_mins: за сколько минут до дедлайна
    """
    query = "UPDATE user_task SET again_remind_in_minutes = %s WHERE user_id = %s AND task_id = %s"
    params = [remind_mins, user_id, task_id]
    with dbconn.cursor() as dbc:
        n_rows = dbc.execute(query, params)
        dbconn.commit()
        return n_rows != 0


def db_task_attach_participant(dbconn, task_id: int, user_id: int):
    """
    (Организатор) Добавить нового исполнителя к задаче
    :param_name task_id: id задачи
    :param_name user_id: id пользователя
    """
    query = "INSERT INTO user_task(user_id, task_id) VALUES (%s, %s)"
    params = [user_id, task_id]
    with dbconn.cursor() as dbc:
        dbc.execute(query, params)
        dbconn.commit()

def db_reminder_mark_as_sent_for_group(dbconn, task_id: int):
	query = 'UPDATE task SET reminder_sent = true WHERE id = %s'
	params = [task_id]
	with dbconn.cursor() as dbc:
		dbc.execute(query, params)
		dbconn.commit()

def db_reminder_mark_as_sent_for_user(dbconn, user_id: int, task_id: int):
	query = 'UPDATE user_task SET reminder_sent = true WHERE user_id = %s AND task_id = %s'
	params = [user_id, task_id]
	with dbconn.cursor() as dbc:
		dbc.execute(query, params)
		dbconn.commit()

def db_reminder_unmark_as_sent_for_group(dbconn, task_id: int):
	query = 'UPDATE task SET reminder_sent = false WHERE id = %s'
	params = [task_id]
	with dbconn.cursor() as dbc:
		dbc.execute(query, params)
		dbconn.commit()

def db_reminder_unmark_as_sent_for_user(dbconn, user_id: int, task_id: int):
	query = 'UPDATE user_task SET reminder_sent = false WHERE user_id = %s AND task_id = %s'
	params = [user_id, task_id]
	with dbconn.cursor() as dbc:
		dbc.execute(query, params)
		dbconn.commit()

def db_get_tasks_unnotified_for_groups(dbconn):
	"""
	Получить список id задач, по которым уже необходимо оповестить исполнителей о приближающемся дедлайне; интервал напоминания для группы задач, установленный организатором.
	"""
	query = 'SELECT t.id as task_id FROM (SELECT task.id, task.deadline, TIMESTAMPDIFF(MINUTE,now(),deadline) as minutes_before_deadline, remind_in_minutes AS group_remind_in_minutes FROM task INNER JOIN task_group ON (task_group_id=task_group.id) WHERE task.reminder_sent = false) t WHERE t.minutes_before_deadline - cast(t.group_remind_in_minutes as signed) < 0;'
	with dbconn.cursor() as dbc:
		dbc.execute(query)
		return dbc.fetchall()

def db_get_tasks_unnotified_for_users(dbconn):
	"""
	Получить список id задач, по которым уже необходимо оповестить исполнителей о приближающемся дедлайне; индивидуальный интервал напоминания для задачи, установленный исполнителем.
	"""
	query = 'SELECT t.id as task_id FROM (SELECT task.id, task.deadline, TIMESTAMPDIFF(MINUTE,now(),deadline) as minutes_before_deadline, again_remind_in_minutes AS user_remind_in_minutes FROM task INNER JOIN user_task ON (task_id=task.id) WHERE user_task.reminder_sent = false) t WHERE t.minutes_before_deadline - cast(t.user_remind_in_minutes as signed) < 0;'
	with dbconn.cursor() as dbc:
		dbc.execute(query)
		return dbc.fetchall()
