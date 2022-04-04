import aiogram
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from config import *
from services.log import logging_message
from services.bdWrapper import *
from messages import *

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)

class UserNewOrder(StatesGroup):
    address = State()

@dp.message_handler(state=AdminNews.text, content_types=["text", "photo", "video", "animation"])
async def send(message: types.Message, state: FSMContext):
    try:
        if message.text == REJECT_BUTTON:
            await send_main_keyboard(message.chat.id, ACTION_REJECTED)
            await state.finish()
            return

@dp.message_handler(content_types=["photo"])
async def echo(message: types.Message):
    print(message.photo[-1].file_id)

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

@dp.callback_query_handler()
async def query_show_list(call: types.CallbackQuery):
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


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    logging_message(message.chat.id, message.from_user.username, message.text)
    chat_id, username, text = message.chat.id, message.from_user.username, message.text
    await send_main_keyboard(chat_id, HELLO_MESSAGE)
    if not check_user_presence(chat_id):
        create_user(chat_id, username)
        await bot.send_message(chat_id, FAQ_MESSAGE)



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
