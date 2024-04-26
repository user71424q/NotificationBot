import configparser
import os
import sys


def load_configuration(file_path):
    if not os.path.exists(file_path):
        print(
            "Файл конфигурации не найден. Проверьте правильность пути: {}".format(
                file_path
            )
        )
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(file_path)

    # Проверяем, есть ли секция с необходимыми данными
    if "Bot" not in config:
        print("В файле конфигурации отсутствует необходимая секция [Bot].")
        sys.exit(1)

    # Проверяем, задан ли токен
    if "token" not in config["Bot"]:
        print("Токен бота не найден в файле конфигурации.")
        sys.exit(1)

    # Проверяем, задан ли список администраторов
    if "admins" not in config["Bot"]:
        print("Список администраторов не найден в файле конфигурации.")
        sys.exit(1)

    # Возвращаем данные в виде словаря
    return {
        "token": config["Bot"]["token"],
        "admins": config["Bot"]["admins"].split(","),
    }
