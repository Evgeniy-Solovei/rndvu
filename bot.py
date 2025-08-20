import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, WebAppInfo, InlineKeyboardMarkup, BotCommand
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv


# Bot token can be obtained via https://t.me/BotFather
load_dotenv()
TOKEN = os.getenv("TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")
# Initialize Bot instance with default bot properties which will be passed to all API calls
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# All handlers should be attached to the Dispatcher
dp = Dispatcher()


async def set_commands():
    commands = [
        BotCommand(command="/start", description="Играть"),
    ]
    await bot.set_my_commands(commands)


@dp.message(CommandStart())
async def handle_start(message: types.Message):
    await message.delete()
    logging.info(f"Получено сообщение: {message.text}")
    text = "🔥 Привет, рады видеть тебя в нашем приложении Rndvu !!!\n\n"

    # Берем всю строку после "/start"
    command_parts = message.text.split(maxsplit=1)
    logging.info(f"Сплит: {command_parts}")

    if len(command_parts) > 1:
        # Заменяем "id_" на "id=" и сохраняем все параметры
        referrer_id = command_parts[1].replace("id_", "id=")
        logging.info(f"referrer_id: {referrer_id}")
        web_app_url = f'{WEB_APP_URL}?{referrer_id}'
    else:
        web_app_url = WEB_APP_URL
    logging.info(f"Отдаю фронту Web App URL: {web_app_url}")
    # Создаем клавиатуру с кнопкой
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Запуск", web_app=WebAppInfo(url=web_app_url))]])

    # Отправляем сообщение
    await message.answer(text, reply_markup=keyboard)


async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())


