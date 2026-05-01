import asyncio
import os
import re
import requests

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN, ADMIN_ID
from keyboards import main_keyboard, phone_keyboard
from database import (
    create_table,
    save_order,
    save_payment_info,
    get_orders,
    get_user_orders,
    get_order_by_id,
    update_order_status,
    update_payment_status,
)

load_dotenv()

MONO_TOKEN = os.getenv("MONO_TOKEN")
PAYMENT_AMOUNT_UAH = int(os.getenv("PAYMENT_AMOUNT_UAH", "500"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class OrderState(StatesGroup):
    name = State()
    phone = State()
    description = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def is_valid_phone(phone: str) -> bool:
    phone = phone.replace(" ", "").replace("-", "")
    pattern = r"^\+?\d{9,15}$"
    return bool(re.match(pattern, phone))


def format_status(status: str) -> str:
    if status == "new":
        return "🆕 Нове"
    if status == "in_progress":
        return "🛠 В роботі"
    if status == "done":
        return "✅ Виконано"
    return status


def format_payment_status(status: str) -> str:
    if status == "pending":
        return "⏳ Очікує оплату"
    if status == "paid":
        return "✅ Оплачено"
    if status == "failed":
        return "❌ Помилка оплати"
    return status


def admin_order_keyboard(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📦 Деталі", callback_data=f"order_{order_id}"),
                InlineKeyboardButton(text="🛠 В роботі", callback_data=f"progress_{order_id}"),
            ],
            [
                InlineKeyboardButton(text="✅ Виконано", callback_data=f"done_{order_id}"),
                InlineKeyboardButton(text="💳 Оплачено", callback_data=f"paid_{order_id}"),
            ],
        ]
    )


def payment_keyboard(payment_url: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатити замовлення", url=payment_url)]
        ]
    )


def manager_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Зв'язатися з менеджером",
                    url="https://t.me/bogdan4446",
                )
            ]
        ]
    )


def create_mono_invoice(order_id: int, amount_uah: int):
    if not MONO_TOKEN:
        return None, None

    url = "https://api.monobank.ua/api/merchant/invoice/create"

    payload = {
        "amount": amount_uah * 100,
        "ccy": 980,
        "merchantPaymInfo": {
            "reference": f"order_{order_id}",
            "destination": f"Order #{order_id}",
            "comment": f"Order #{order_id}",
        },
        "redirectUrl": "https://t.me/",
    }

    headers = {
        "X-Token": MONO_TOKEN,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)

        if response.status_code != 200:
            print("Mono error:", response.status_code, response.text)
            return None, None

        data = response.json()
        return data.get("invoiceId"), data.get("pageUrl")

    except Exception as e:
        print("Payment error:", e)
        return None, None


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Привіт! 👋\n\n"
        "Я бот для прийому замовлень.\n"
        "Обери дію:",
        reply_markup=main_keyboard,
    )


@dp.message(Command("admin"))
async def admin_handler(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебе немає доступу до адмін-панелі.")
        return

    orders = get_orders()

    if not orders:
        await message.answer("📭 Замовлень поки немає.")
        return

    await message.answer("📋 Останні замовлення:")

    for order in orders:
        (
            order_id,
            user_id,
            name,
            phone,
            description,
            status,
            amount,
            invoice_id,
            payment_url,
            payment_status,
        ) = order

        text = (
            f"🆔 Замовлення #{order_id}\n"
            f"👤 Ім'я: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"💰 Сума: {amount} грн\n"
            f"📌 Статус: {format_status(status)}\n"
            f"💳 Оплата: {format_payment_status(payment_status)}"
        )

        await message.answer(text, reply_markup=admin_order_keyboard(order_id))


@dp.message(F.text == "👤 Мої замовлення")
async def my_orders_handler(message: Message):
    orders = get_user_orders(message.from_user.id)

    if not orders:
        await message.answer("📭 У тебе ще немає замовлень.")
        return

    text = "👤 Твої останні замовлення:\n\n"

    for order in orders:
        order_id, name, phone, description, status, amount, payment_status = order

        text += (
            f"🆔 Замовлення #{order_id}\n"
            f"📝 Опис: {description}\n"
            f"💰 Сума: {amount} грн\n"
            f"📌 Статус: {format_status(status)}\n"
            f"💳 Оплата: {format_payment_status(payment_status)}\n"
            f"----------------------\n"
        )

    await message.answer(text)


@dp.callback_query(F.data.startswith("order_"))
async def order_detail_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Немає доступу")
        return

    order_id = int(callback.data.replace("order_", ""))
    order = get_order_by_id(order_id)

    if not order:
        await callback.answer("❌ Замовлення не знайдено")
        return

    (
        order_id,
        user_id,
        name,
        phone,
        description,
        status,
        amount,
        invoice_id,
        payment_url,
        payment_status,
    ) = order

    await callback.message.answer(
        f"📦 Замовлення #{order_id}\n\n"
        f"👤 Ім'я: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📝 Опис: {description}\n"
        f"💰 Сума: {amount} грн\n"
        f"📌 Статус: {format_status(status)}\n"
        f"💳 Оплата: {format_payment_status(payment_status)}"
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("progress_"))
async def progress_order_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Немає доступу")
        return

    order_id = int(callback.data.replace("progress_", ""))
    order = get_order_by_id(order_id)

    if not order:
        await callback.answer("❌ Замовлення не знайдено")
        return

    (
        order_id,
        user_id,
        name,
        phone,
        description,
        status,
        amount,
        invoice_id,
        payment_url,
        payment_status,
    ) = order

    update_order_status(order_id, "in_progress")

    await callback.message.answer(f"🛠 Замовлення #{order_id} взято в роботу.")

    await bot.send_message(
        user_id,
        f"🛠 Ваше замовлення №{order_id} вже в роботі.\n"
        "Ми повідомимо вас після виконання.",
    )

    await callback.answer("В роботі 🛠")


@dp.callback_query(F.data.startswith("done_"))
async def done_order_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Немає доступу")
        return

    order_id = int(callback.data.replace("done_", ""))
    order = get_order_by_id(order_id)

    if not order:
        await callback.answer("❌ Замовлення не знайдено")
        return

    (
        order_id,
        user_id,
        name,
        phone,
        description,
        status,
        amount,
        invoice_id,
        payment_url,
        payment_status,
    ) = order

    if status == "done":
        await callback.answer("Це замовлення вже виконане")
        return

    update_order_status(order_id, "done")

    await callback.message.answer(f"✅ Замовлення #{order_id} позначено як виконане.")

    await bot.send_message(
        user_id,
        f"✅ Ваше замовлення №{order_id} виконане.\n\n"
        "Очікуйте, будь ласка.\n"
        "Дякуємо за співпрацю 🤝",
    )

    await callback.answer("Готово ✅")


@dp.callback_query(F.data.startswith("paid_"))
async def paid_order_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Немає доступу")
        return

    order_id = int(callback.data.replace("paid_", ""))
    order = get_order_by_id(order_id)

    if not order:
        await callback.answer("❌ Замовлення не знайдено")
        return

    update_payment_status(order_id, "paid")

    (
        order_id,
        user_id,
        name,
        phone,
        description,
        status,
        amount,
        invoice_id,
        payment_url,
        payment_status,
    ) = order

    await callback.message.answer(f"💳 Замовлення #{order_id} позначено як оплачене.")

    await bot.send_message(
        user_id,
        f"✅ Оплату за замовлення №{order_id} підтверджено.\n"
        "Дякуємо 🤝",
    )

    await callback.answer("Оплату підтверджено ✅")


@dp.message(F.text == "ℹ️ Про нас")
async def about_handler(message: Message):
    await message.answer(
        "🚀 Ми створюємо Telegram-ботів для бізнесу, каналів та автоматизації.\n\n"
        "Можемо зробити:\n"
        "• прийом замовлень\n"
        "• заявки\n"
        "• адмін-панель\n"
        "• базу клієнтів\n"
        "• оплату\n"
        "• автоматизацію процесів"
    )


@dp.message(F.text == "📦 Зробити замовлення")
async def order_start(message: Message, state: FSMContext):
    await state.set_state(OrderState.name)
    await message.answer("Введи своє ім'я:")


@dp.message(OrderState.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OrderState.phone)

    await message.answer(
        "Введи номер телефону або натисни кнопку нижче:",
        reply_markup=phone_keyboard,
    )


@dp.message(OrderState.phone, F.contact)
async def get_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number

    await state.update_data(phone=phone)
    await state.set_state(OrderState.description)

    await message.answer(
        "Опиши, що потрібно зробити:",
        reply_markup=main_keyboard,
    )


@dp.message(OrderState.phone)
async def get_phone_text(message: Message, state: FSMContext):
    phone = message.text

    if not is_valid_phone(phone):
        await message.answer(
            "❌ Введи коректний номер телефону.\n"
            "Наприклад: +380661234567"
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(OrderState.description)

    await message.answer(
        "Опиши, що потрібно зробити:",
        reply_markup=main_keyboard,
    )


@dp.message(OrderState.description)
async def get_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)

    data = await state.get_data()

    user_id = message.from_user.id
    name = data["name"]
    phone = data["phone"]
    description = data["description"]
    amount = PAYMENT_AMOUNT_UAH

    order_id = save_order(user_id, name, phone, description, amount)

    invoice_id, payment_url = create_mono_invoice(order_id, amount)

    if invoice_id and payment_url:
        save_payment_info(order_id, invoice_id, payment_url)

    admin_text = (
        f"🆕 Нове замовлення #{order_id}!\n\n"
        f"👤 Ім'я: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📝 Опис: {description}\n"
        f"💰 Сума: {amount} грн\n"
        f"📌 Статус: 🆕 Нове\n"
        f"💳 Оплата: ⏳ Очікує оплату"
    )

    await bot.send_message(
        ADMIN_ID,
        admin_text,
        reply_markup=admin_order_keyboard(order_id),
    )

    if payment_url:
        await message.answer(
            f"✅ Замовлення №{order_id} створено!\n\n"
            f"💰 Сума: {amount} грн\n"
            "👇 Натисни щоб оплатити:",
            reply_markup=payment_keyboard(payment_url),
        )
    else:
        await message.answer(
            f"✅ Замовлення №{order_id} створено!\n\n"
            "❗ Оплата тимчасово недоступна.\n"
            "Можеш зв'язатися з менеджером:",
            reply_markup=manager_keyboard(),
        )

    await state.clear()


async def main():
    create_table()
    print("✅ Бот запущений...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())