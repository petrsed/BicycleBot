import sqlite3
from config import *
from services.log import *

def check_user_presence(chat_id):
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"SELECT id FROM users WHERE telegram_chat_id = '{chat_id}';")
    res = cur.fetchall()
    return len(res) == 1


def create_user(chat_id, username):
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""INSERT INTO users(telegram_chat_id, telegram_username) 
       VALUES('{chat_id}', '{username}');""")
    conn.commit()
    return True

def get_all_categories():
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""SELECT * FROM categories;""")
    res = cur.fetchall()
    return res