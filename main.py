import aiogram
from aiogram import Bot, Dispatcher, executor, types
from config import *
from services.log import logging_message
from services.bdWrapper import *
from messages import *

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)

async def send_main_keyboard(chat_id, text=MAIN_KEYBOARD_MESSAGE):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(CATALOG_BUTTON, CART_BUTTON)
    markup.add(FAQ_BUTTON, SUPPORT_BUTTON)
    await bot.send_message(chat_id, text, reply_markup=markup)


async def send_categories(chat_id, text=CHOICE_CATEGORY):
    categories = get_all_categories()
    markup = types.InlineKeyboardMarkup()
    for category in categories:
        markup.add(types.InlineKeyboardButton(category[1], callback_data=f"category_{category[0]}"))
    await bot.send_message(chat_id, text, reply_markup=markup)

@dp.callback_query_handler()
async def query_show_list(call: types.CallbackQuery):
    logging_message(call.from_user.id, call.from_user.username, call.data)
    chat_id, username, data = call.from_user.id, call.from_user.username, call.data


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    logging_message(message.chat.id, message.from_user.username, message.text)
    chat_id, username, text = message.chat.id, message.from_user.username, message.text
    await send_main_keyboard(chat_id, HELLO_MESSAGE)
    if not check_user_presence(chat_id):
        create_user(chat_id, username)
        await bot.send_message(chat_id, WELCOME_MESSAGE)



@dp.message_handler()
async def echo(message: types.Message):
    logging_message(message.chat.id, message.from_user.username, message.text)
    chat_id, username, text = message.chat.id, message.from_user.username, message.text


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
