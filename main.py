import aiogram
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from config import *
from services.log import logging_message
from services.bdWrapper import *
from services.qiwiWrapper import *
from messages import *

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

class UserNewOrder(StatesGroup):
    address = State()

class AdminAddCategory(StatesGroup):
    name = State()

class AdminAddProduct(StatesGroup):
    name = State()
    description = State()
    photo = State()
    price = State()

@dp.message_handler(state=UserNewOrder.address)
async def send(message: types.Message, state: FSMContext):
    if message.text == REJECT_BUTTON:
        await send_main_keyboard(message.chat.id, ACTION_REJECTED)
        await state.finish()
        return
    address = message.text
    order_id = add_order(message.chat.id, address)
    await send_receipt(order_id)
    await state.finish()

@dp.message_handler(state=AdminAddCategory.name)
async def send(message: types.Message, state: FSMContext):
    if message.text == REJECT_BUTTON:
        await send_main_keyboard(message.chat.id, ACTION_REJECTED)
        await state.finish()
        return
    addcategory(message.text)
    await send_main_keyboard(message.chat.id, "Категория добавлена!")
    await state.finish()

@dp.message_handler(state=AdminAddProduct.name)
async def send(message: types.Message, state: FSMContext):
    if message.text == REJECT_BUTTON:
        await send_main_keyboard(message.chat.id, ACTION_REJECTED)
        await state.finish()
        return
    async with state.proxy() as state_data:
        state_data["name"] = message.text
    await bot.send_message(message.chat.id, "Введите описание товара:")
    await AdminAddProduct.description.set()

@dp.message_handler(state=AdminAddProduct.description)
async def send(message: types.Message, state: FSMContext):
    if message.text == REJECT_BUTTON:
        await send_main_keyboard(message.chat.id, ACTION_REJECTED)
        await state.finish()
        return
    async with state.proxy() as state_data:
        state_data["description"] = message.text
    await bot.send_message(message.chat.id, "Введите стоимость товара:")
    await AdminAddProduct.price.set()

@dp.message_handler(state=AdminAddProduct.price)
async def send(message: types.Message, state: FSMContext):
    if message.text == REJECT_BUTTON:
        await send_main_keyboard(message.chat.id, ACTION_REJECTED)
        await state.finish()
        return
    try:
        price = int(message.text)
    except Exception as e:
        await bot.send_message(message.chat.id, "Неверный формат сообщения!")
        return
    async with state.proxy() as state_data:
        state_data["price"] = price
    await bot.send_message(message.chat.id, "Пришлите фотографию товара:")
    await AdminAddProduct.photo.set()

@dp.message_handler(state=AdminAddProduct.photo, content_types=["text", "photo"])
async def send(message: types.Message, state: FSMContext):
    try:
        if message.text == REJECT_BUTTON:
            await send_main_keyboard(message.chat.id, ACTION_REJECTED)
            await state.finish()
            return
    except Exception as e:
        pass
    async with state.proxy() as state_data:
        category_id = state_data["category_id"]
        name = state_data["name"]
        description = state_data["description"]
        price = state_data["price"]
    addgood(category_id, name, description, price, message.photo[-1].file_id)
    await send_main_keyboard(message.chat.id, "Товар добавлен!")
    await state.finish()


@dp.message_handler(content_types=["photo"])
async def echo(message: types.Message):
    print(message.photo[-1].file_id)

async def send_receipt(order_id):
    msg = RECEIPT_TEXT
    order = get_order_by_id(order_id)
    items = sort_items(order[2].split(";"))
    items_text = ""
    all_amount = 0
    for item in items:
        product = get_product_by_id(item)
        amount = items[item]
        items_text += f"{product[2]}: {product[5]} x {amount} = {product[5] * amount} руб.\n"
        all_amount += product[5] * amount
    msg = msg.replace("{PRODCUTS}", items_text)
    msg = msg.replace("{AMOUNT}", str(all_amount))
    change_order_parametr(order_id, "amount", all_amount)
    url = f"https://oplata.qiwi.com/create?publicKey={QIWI_KEY}&amount={all_amount}&comment={order_id}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(PAY_BUTTON, url=url))
    markup.add(types.InlineKeyboardButton(CHECK_PAY_BUTTON, callback_data=f"checkorder_{order_id}"))
    await bot.send_message(order[1], msg, parse_mode="HTML", reply_markup=markup)

def get_prev_next_products(product_id):
    product = get_product_by_id(product_id)
    category_products = [category[0] for category in get_category_products(product[1])]
    product_index = category_products.index(int(product_id))
    prev_id, next_id = product_index - 1, product_index + 1
    if next_id == len(category_products):
        next_id = 0
    prev_product = get_product_by_id(category_products[prev_id])
    next_product = get_product_by_id(category_products[next_id])
    return prev_product[0], next_product[0]

def sort_items(items):
    items_dict = {}
    for item in items:
        if item in items_dict:
            items_dict[item] += 1
        else:
            items_dict[item] = 1
    return items_dict

async def send_main_keyboard(chat_id, text=MAIN_KEYBOARD_MESSAGE):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(CATALOG_BUTTON, CART_BUTTON)
    markup.add(FAQ_BUTTON, SUPPORT_BUTTON)
    await bot.send_message(chat_id, text, reply_markup=markup)


async def send_categories(chat_id, text=CHOICE_CATEGORY, msg_id=None):
    categories = get_all_categories()
    markup = types.InlineKeyboardMarkup()
    for category in categories:
        markup.add(types.InlineKeyboardButton(category[1], callback_data=f"category_{category[0]}"))
    if msg_id is None:
        await bot.send_message(chat_id, text, reply_markup=markup)
    else:
        await bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)

async def order_notice(order_id):
    order = get_order_by_id(order_id)
    user = get_user_by_id(order[1])
    items = sort_items(order[2].split(";"))
    items_text = ""
    all_amount = 0
    for item in items:
        product = get_product_by_id(item)
        amount = items[item]
        items_text += f"{product[2]}: {product[5]} x {amount} = {product[5] * amount} руб.\n"
        all_amount += product[5] * amount
    msg = NEW_ORDER_NOTICE
    msg = msg.replace("{PRODCUTS}", items_text)
    msg = msg.replace("{AMOUNT}", str(all_amount))
    msg = msg.replace("{ID}", str(user[1]))
    msg = msg.replace("{LOGIN}", str(user[2]))
    msg = msg.replace("{ADDRESS}", str(order[3]))
    await bot.send_message(NOTICE_ID, msg)

async def send_admin_delcategories(chat_id, msg_id=None):
    categories = get_all_categories()
    markup = types.InlineKeyboardMarkup()
    for category in categories:
        markup.add(types.InlineKeyboardButton(category[1], callback_data=f"admin_categoriesdel_{category[0]}"))
    markup.add(types.InlineKeyboardButton(RETURN_BUTTON, callback_data=f"admin_categories"))
    await bot.edit_message_text("Нажмите на категория для удаления:", chat_id, msg_id, reply_markup=markup)

async def send_good_slider(chat_id, product_id, msg_id=None, delete_old_message=False):
    cart = get_user_cart(chat_id)
    amount = cart.count(str(product_id))
    product = get_product_by_id(product_id)
    category = get_category_by_id(product[1])
    prev_product_id, next_product_id = get_prev_next_products(product_id)
    msg = PRODUCT_TEXT
    msg = msg.replace("{CATEGORY}", category[1])
    msg = msg.replace("{NAME}", product[2])
    msg = msg.replace("{DESCRIPTION}", product[3])
    msg = msg.replace("{PRICE}", str(product[5]))
    markup = types.InlineKeyboardMarkup()
    button = IN_CART_BUTTON
    button = button.replace("{PRICE}", str(product[5]))
    button = button.replace("{AMOUNT}", str(amount))
    button = button.replace("{ALL_PRICE}", str(amount * product[5]))
    markup.add(types.InlineKeyboardButton(button, callback_data="none"))
    markup.add(types.InlineKeyboardButton(MINUS_EMOJI, callback_data=f"delincart_{product_id}_0"),
               types.InlineKeyboardButton(PLUS_EMOJI, callback_data=f"addtocart_{product_id}_0"))
    markup.add(types.InlineKeyboardButton(LEFT_EMOJI, callback_data=f"product_{prev_product_id}"),
               types.InlineKeyboardButton(RIGHT_EMOJI, callback_data=f"product_{next_product_id}"))
    markup.add(types.InlineKeyboardButton(RETURN_BUTTON, callback_data=f"catalog"))
    if msg_id is not None:
        if delete_old_message:
            await bot.delete_message(chat_id, msg_id)
        else:
            await bot.edit_message_media(types.InputMediaPhoto(product[4], caption=msg, parse_mode="HTML"), chat_id, msg_id, reply_markup=markup)
            return
    await bot.send_photo(chat_id, product[4], caption=msg, parse_mode="HTML", reply_markup=markup)

async def send_cart(chat_id, msg_id=None):
    items = get_user_cart(chat_id)
    items = sort_items(items)
    markup = types.InlineKeyboardMarkup()
    all_amount = 0
    for item in items:
        product = get_product_by_id(item)
        amount = items[item]
        button = ITEM_CART_BUTTON
        button = button.replace("{ITEM}", product[2])
        button = button.replace("{PRICE}", str(product[5]))
        button = button.replace("{AMOUNT}", str(amount))
        button = button.replace("{ALL_PRICE}", str(product[5] * amount))
        markup.add(types.InlineKeyboardButton(button, callback_data="none"))
        markup.add(types.InlineKeyboardButton(MINUS_EMOJI, callback_data=f"delincart_{product[0]}_1"),
                   types.InlineKeyboardButton(PLUS_EMOJI, callback_data=f"addtocart_{product[0]}_1"))
        all_amount += product[5] * amount
    button = ALL_AMOUNT_TEXT
    button = button.replace("{ALL_AMOUNT}", str(all_amount))
    markup.add(types.InlineKeyboardButton(button, callback_data="none"))
    markup.add(types.InlineKeyboardButton(START_ORDER, callback_data="startorder"))
    if msg_id is None:
        await bot.send_message(chat_id, CART_TEXT, reply_markup=markup)
    else:
        await bot.edit_message_text(CART_TEXT, chat_id, msg_id, reply_markup=markup)

async def send_admin_keyboard(chat_id, msg_id=None):
    if chat_id in ADMIN_IDS:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Категории", callback_data=f"admin_categories"))
        markup.add(types.InlineKeyboardButton("Товары", callback_data=f"admin_products"))
        if msg_id is None:
            await bot.send_message(chat_id, "Админ-панель:", reply_markup=markup)
        else:
            await bot.edit_message_text("Админ-панель:", chat_id, msg_id, reply_markup=markup)

@dp.callback_query_handler()
async def query_show_list(call: types.CallbackQuery, state: FSMContext):
    logging_message(call.from_user.id, call.from_user.username, call.data)
    chat_id, username, data = call.from_user.id, call.from_user.username, call.data
    if "category_" in data:
        category_id = data.split("_")[1]
        products = get_category_products(category_id)
        await send_good_slider(chat_id, products[0][0], call.message.message_id, delete_old_message=True)
    elif data == "catalog":
        await bot.delete_message(chat_id, call.message.message_id)
        await send_categories(chat_id)
    elif "delincart_" in data:
        product_id, status_id = data.split("_")[1], int(data.split("_")[2])
        delincart(chat_id, product_id)
        if status_id == 0:
            await send_good_slider(chat_id, product_id, call.message.message_id)
        elif status_id == 1:
            await send_cart(chat_id, call.message.message_id)
    elif "addtocart_" in data:
        product_id, status_id = data.split("_")[1], int(data.split("_")[2])
        addtocart(chat_id, product_id)
        if status_id == 0:
            await send_good_slider(chat_id, product_id, call.message.message_id)
        elif status_id == 1:
            await send_cart(chat_id, call.message.message_id)
    elif "product_" in data:
        product_id = data.split("_")[1]
        await send_good_slider(chat_id, product_id, call.message.message_id)
    elif data == "startorder":
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(REJECT_BUTTON)
        await UserNewOrder.address.set()
        await bot.send_message(chat_id, ENTER_ADDRESS_TEXT, reply_markup=keyboard)
    elif "checkorder_" in data:
        change_user_parametr(chat_id, "cart", "")
        order_id = data.split("_")[1]
        if check_pay(order_id):
            await order_notice(order_id)
            change_order_parametr(order_id, "status", 1)
            await bot.edit_message_text(ORDER_CREATED, chat_id, call.message.message_id)
        else:
            await bot.send_message(chat_id, PAY_NOT_FOUND)
    elif data == "admin_categories":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Список категорий", callback_data=f"admin_categorieslist"))
        markup.add(types.InlineKeyboardButton("Добавить категорию", callback_data=f"admin_categoriesadd"))
        markup.add(types.InlineKeyboardButton("Удалить категорию", callback_data=f"admin_categoriesdel"))
        markup.add(types.InlineKeyboardButton(RETURN_BUTTON, callback_data=f"admin_return"))
        await bot.edit_message_text("Категории:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif data == "admin_products":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Список товаров", callback_data=f"admin_prodcutslist"))
        markup.add(types.InlineKeyboardButton("Добавить товар", callback_data=f"admin_prodcutsadd"))
        markup.add(types.InlineKeyboardButton("Удалить товар", callback_data=f"admin_prodcutsdel"))
        markup.add(types.InlineKeyboardButton(RETURN_BUTTON, callback_data=f"admin_return"))
        await bot.edit_message_text("Товары:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif data == "admin_return":
        await send_admin_keyboard(chat_id, call.message.message_id)
    elif data == "admin_categorieslist":
        categories = get_all_categories()
        markup = types.InlineKeyboardMarkup()
        for category in categories:
            markup.add(types.InlineKeyboardButton(category[1], callback_data=f"none"))
        markup.add(types.InlineKeyboardButton(RETURN_BUTTON, callback_data=f"admin_categories"))
        await bot.edit_message_text("Список категорий:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif data == "admin_categoriesadd":
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(REJECT_BUTTON)
        await bot.send_message(chat_id, "Введите имя категории:", reply_markup=keyboard)
        await AdminAddCategory.name.set()
    elif data == "admin_categoriesdel":
        await send_admin_delcategories(chat_id, call.message.message_id)
    elif "admin_categoriesdel_" in data:
        category_id = data.split("_")[2]
        delcategory(category_id)
        await send_admin_delcategories(chat_id, call.message.message_id)
        await bot.send_message(chat_id, "Категория удалена!")
    elif data == "admin_prodcutslist":
        categories = get_all_categories()
        markup = types.InlineKeyboardMarkup()
        for category in categories:
            markup.add(types.InlineKeyboardButton(category[1], callback_data=f"admin_prodcutslist_{category[0]}"))
        markup.add(types.InlineKeyboardButton(RETURN_BUTTON, callback_data=f"admin_products"))
        await bot.edit_message_text("Список товаров:\n\nВыберите категорию:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif "admin_prodcutslist_" in data:
        category_id = data.split("_")[2]
        prodcuts = get_category_products(category_id)
        markup = types.InlineKeyboardMarkup()
        for prodcut in prodcuts:
            markup.add(types.InlineKeyboardButton(prodcut[2], callback_data=f"none"))
        markup.add(types.InlineKeyboardButton(RETURN_BUTTON, callback_data=f"admin_prodcutslist"))
        await bot.edit_message_text("Список товаров:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif data == "admin_prodcutsadd":
        categories = get_all_categories()
        markup = types.InlineKeyboardMarkup()
        for category in categories:
            markup.add(types.InlineKeyboardButton(category[1], callback_data=f"admin_prodcutsadd_{category[0]}"))
        markup.add(types.InlineKeyboardButton(RETURN_BUTTON, callback_data=f"admin_products"))
        await bot.edit_message_text("Добавление товара:\n\nВыберите категорию:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif "admin_prodcutsadd_" in data:
        category_id = data.split("_")[2]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(REJECT_BUTTON)
        await bot.send_message(chat_id, "Введите имя товара:", reply_markup=keyboard)
        await AdminAddProduct.name.set()
        async with state.proxy() as state_data:
            state_data["category_id"] = category_id
    elif data == "admin_prodcutsdel":
        categories = get_all_categories()
        markup = types.InlineKeyboardMarkup()
        for category in categories:
            markup.add(types.InlineKeyboardButton(category[1], callback_data=f"admin_prodcutsdel_{category[0]}"))
        markup.add(types.InlineKeyboardButton(RETURN_BUTTON, callback_data=f"admin_products"))
        await bot.edit_message_text("Удаление товара:\n\nВыберите категорию:", call.message.chat.id,
                                    call.message.message_id, reply_markup=markup)
    elif "admin_prodcutsdel_" in data:
        category_id = data.split("_")[2]
        prodcuts = get_category_products(category_id)
        markup = types.InlineKeyboardMarkup()
        for prodcut in prodcuts:
            markup.add(types.InlineKeyboardButton(prodcut[2], callback_data=f"admin_prodcutdel_{category_id}_{prodcut[0]}"))
        markup.add(types.InlineKeyboardButton(RETURN_BUTTON, callback_data=f"admin_prodcutsdel"))
        await bot.edit_message_text("Нажмите на товар для удаления:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif "admin_prodcutdel_" in data:
        category_id, product_id = data.split("_")[2], data.split("_")[3]
        delproduct(product_id)
        await bot.send_message(chat_id, "Товар удалён!")
        prodcuts = get_category_products(category_id)
        markup = types.InlineKeyboardMarkup()
        for prodcut in prodcuts:
            markup.add(types.InlineKeyboardButton(prodcut[2], callback_data=f"admin_prodcutdel_{category_id}_{prodcut[0]}"))
        markup.add(types.InlineKeyboardButton(RETURN_BUTTON, callback_data=f"admin_prodcutsdel"))
        await bot.edit_message_text("Нажмите на товар для удаления:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    logging_message(message.chat.id, message.from_user.username, message.text)
    chat_id, username, text = message.chat.id, message.from_user.username, message.text
    await send_main_keyboard(chat_id, HELLO_MESSAGE)
    if not check_user_presence(chat_id):
        create_user(chat_id, username)
        await bot.send_message(chat_id, FAQ_MESSAGE)

@dp.message_handler(commands=['admin'])
async def send_welcome(message: types.Message):
    logging_message(message.chat.id, message.from_user.username, message.text)
    chat_id, username, text = message.chat.id, message.from_user.username, message.text
    if chat_id in ADMIN_IDS:
        await send_admin_keyboard(chat_id)

@dp.message_handler()
async def echo(message: types.Message):
    logging_message(message.chat.id, message.from_user.username, message.text)
    chat_id, username, text = message.chat.id, message.from_user.username, message.text
    if text == CATALOG_BUTTON:
        await send_categories(chat_id)
    elif text == FAQ_BUTTON:
        await bot.send_message(chat_id, FAQ_MESSAGE)
    elif text == SUPPORT_BUTTON:
        await bot.send_message(chat_id, SUPPORT_TEXT)
    elif text == CART_BUTTON:
        await send_cart(chat_id)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
