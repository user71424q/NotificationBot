
# Чат-бот – помощник составления расписания

Этот проект представляет собой Telegram-бота, который позволяет создавать расписание мероприятий и связанных с ними задач с дедлайнами.

Проект предназначен для организаторов различных мероприятий, например, акселератора проектов, обучающих курсов.

## Особенности

- 2 роли: организатор и участник
- Загрузка информации о задачах из Excel-файла
- Организатор может создать несколько мероприятий, каждое из которых может содержать несколько задач с дедлайнами
- Организатор может настроить получателей для каждой задачи в отдельности
- Организатор может настроить, за сколько минут до дедлайна пользователь получит напоминание
- При получении напоминания участник может настроить, за сколько минут до дедлайна получить повторное напоминание

## Установка и настройка

Чтобы развернуть у себя этот проект, выполните следующие шаги:

1. Создайте телеграм-бота и получите его токен.
2. В файл config.ini впишите токен бота и телеграм-теги (никнеймы) организатора или нескольких организаторов через запятую.
3. Создайте базу данных и подключение MySQL (или MariaDB).
4. В файл dbconfig.ini впишите следующие параметры:
- ip - IP (или домен) сервера, на котором запущена СУБД MySQL (или MariaDB)
- port - Порт, на котором вещает MySQL, обычно 3306
- dbcharset - Кодировка в БД, обычно utf8mb4
- username - Имя пользователя MySQL с правами доступа к БД системы
- password - Пароль пользователя MySQL
- dbname - Наименование базы данных в MySQL
5. Попросите участников сообщить Вам телеграм-теги (никнеймы), если они Вам неизвестны.
6. Попросите участников написать боту /start, так как телеграм-боты не могут начинать диалог.


## Авторы

- [@user71424q](https://github.com/user71424q)
- [@st4rkaliv3](https://github.com/st4rkaliv3)
- [@Alinochka184](https://github.com/Alinochka184)
- [@EkaterinaIsupova](https://github.com/EkaterinaIsupova)


