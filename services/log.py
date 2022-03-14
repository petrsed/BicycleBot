import logging
from config import LOGGING_MESSAGES_FILE, LOGGING_ACTIONS_FILE
from datetime import datetime


def logging_message(user_id, user_name, message):
    logging.basicConfig(filename=LOGGING_MESSAGES_FILE, level=logging.INFO)
    text = f"{datetime.now()} - {user_id} - {user_name} - {message}"
    logging.info(text)
    print(text)


def logging_action(user_id, user_name, action):
    logging.basicConfig(filename=LOGGING_ACTIONS_FILE, level=logging.INFO)
    text = f"{datetime.now()} - {user_id} - {user_name} - {action}"
    logging.info(text)
    print(text)
