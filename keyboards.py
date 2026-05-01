from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Зробити замовлення")],
        [KeyboardButton(text="👤 Мої замовлення")],
        [KeyboardButton(text="ℹ️ Про нас")]
    ],
    resize_keyboard=True
)

phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Поділитися телефоном", request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)