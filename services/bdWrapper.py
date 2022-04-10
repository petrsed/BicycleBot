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

def get_category_products(category_id):
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""SELECT * FROM products WHERE category_id = {category_id};""")
    res = cur.fetchall()
    return res

def get_product_by_id(product_id):
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""SELECT * FROM products WHERE id = {product_id};""")
    res = cur.fetchone()
    return res

def get_category_by_id(category_id):
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""SELECT * FROM categories WHERE id = {category_id};""")
    res = cur.fetchone()
    return res

def get_user_cart(chat_id):
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""SELECT cart FROM users WHERE telegram_chat_id = {chat_id};""")
    res = cur.fetchone()[0]
    if res is None:
        return []
    else:
        items = res.split(";")
        if "" in items:
            items.remove("")
        return items

def change_user_parametr(user_id, parametr_name, parametr_value):
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""UPDATE users SET {parametr_name} = '{parametr_value}' WHERE telegram_chat_id = '{user_id}'""")
    conn.commit()
    return True

def addtocart(chat_id, product_id):
    cart = get_user_cart(chat_id)
    cart.append(str(product_id))
    change_user_parametr(chat_id, "cart", ";".join(cart))

def delincart(chat_id, product_id):
    cart = get_user_cart(chat_id)
    cart.remove(str(product_id))
    change_user_parametr(chat_id, "cart", ";".join(cart))

def add_order(chat_id, address):
    cart = get_user_cart(chat_id)
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""INSERT INTO orders(chat_id, cart, address) 
       VALUES('{chat_id}', '{';'.join(cart)}', '{address}');""")
    conn.commit()
    return get_last_order_id()

def get_last_order_id():
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""SELECT id FROM orders ORDER BY id DESC""")
    res = cur.fetchone()[0]
    return res

def get_order_by_id(order_id):
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""SELECT * FROM orders WHERE id = {order_id};""")
    res = cur.fetchone()
    return res

def get_user_by_id(user_id):
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""SELECT * FROM users WHERE telegram_chat_id = {user_id};""")
    res = cur.fetchone()
    return res

def change_order_parametr(order_id, parametr_name, parametr_value):
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"""UPDATE orders SET {parametr_name} = '{parametr_value}' WHERE id = '{order_id}'""")
    conn.commit()
    return True

def hash_presence(hash):
    conn = sqlite3.connect(BD_FILE_NAME)
    cur = conn.cursor()
    cur.execute(f"SELECT hash FROM orders WHERE hash = '{hash}';")
    res = cur.fetchall()
    return len(res) > 0