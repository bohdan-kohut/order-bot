import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


BOT_TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()


# 👉 клавіатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Зробити замовлення")],
        [KeyboardButton(text="ℹ️ Про нас")]
    ],
    resize_keyboard=True
)


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Привіт! 👋\n\nЯ бот для прийому замовлень.\nОбери дію:",
        reply_markup=main_keyboard
    )


# 👉 обробка кнопок
@dp.message(F.text == "📦 Зробити замовлення")
async def order_handler(message: Message):
    await message.answer("Введи своє ім'я:")


@dp.message(F.text == "ℹ️ Про нас")
async def about_handler(message: Message):
    await message.answer(
        "Ми приймаємо замовлення через Telegram 🚀"
    )


async def main():
    if not BOT_TOKEN:
        print("Нема токена!")
        return

    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())