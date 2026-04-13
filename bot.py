#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import json
import traceback
from datetime import datetime

# --- Отключаем прокси PythonAnywhere для Telegram API ---
os.environ['NO_PROXY'] = 'api.telegram.org'

import telebot
from telebot import types, apihelper
apihelper.proxy = {}  # Явное отключение прокси

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Конфигурация (вставьте свои данные) ---
BOT_TOKEN = "8660030771:AAEskFGCw7aFor-qqYuS0gxCxABbiGya26U"
ADMIN_ID = 1427887057
BOT_ENABLED = True  # Статус бота

# --- Google Sheets ---
def get_sheet():
    """Подключение к Google Таблице"""
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open("Энергогарант - Реестр").sheet1
        return sheet
    except Exception as e:
        logger.error(f"Ошибка подключения к Google Sheets: {e}")
        return None

# --- Хранилище состояний ---
user_data = {}

# Состояния
STATE_WAITING_FIO = 'waiting_fio'
STATE_WAITING_BIRTHDATE = 'waiting_birthdate'
STATE_WAITING_PHONE = 'waiting_phone'
STATE_CONFIRMING = 'confirming'
STATE_EDITING_FIO = 'editing_fio'
STATE_EDITING_BIRTHDATE = 'editing_birthdate'
STATE_EDITING_PHONE = 'editing_phone'

# --- Клавиатуры ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🛒 Купить сертификат Энергогарант"))
    return markup

def phone_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📱 Поделиться контактом", request_contact=True))
    return markup

def remove_keyboard():
    return types.ReplyKeyboardRemove()

def confirm_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Данные верны", callback_data="confirm"))
    markup.add(types.InlineKeyboardButton("✏️ Исправить ФИО", callback_data="edit_fio"))
    markup.add(types.InlineKeyboardButton("✏️ Исправить дату рождения", callback_data="edit_birthdate"))
    markup.add(types.InlineKeyboardButton("✏️ Исправить телефон", callback_data="edit_phone"))
    return markup

# --- Декоратор проверки статуса бота ---
def check_bot_enabled(func):
    def wrapper(message):
        if not BOT_ENABLED:
            bot.send_message(
                message.chat.id,
                "🔧 <b>Технические работы</b>\n\n"
                "Бот временно недоступен.\n"
                "Приносим извинения за неудобства.\n\n"
                "⏰ Работы займут несколько часов.\n"
                "Попробуйте позже или свяжитесь с нами:\n"
                "@vasilishhka",
                parse_mode="HTML"
            )
            return
        return func(message)
    return wrapper

def show_summary(chat_id, user_id):
    """Показывает сводку данных и кнопки подтверждения"""
    data = user_data.get(user_id, {})
    phone = data.get('phone', 'не указан')
    phone_display = f"<code>{phone}</code>" if phone != 'не указан' else "не указан"

    summary = (
        f"📋 <b>Проверьте данные:</b>\n\n"
        f"👤 ФИО: <code>{data.get('fio', '')}</code>\n"
        f"🎂 Дата рождения: <code>{data.get('birthdate', '')}</code>\n"
        f"📱 Телефон: {phone_display}\n"
        f"💰 Сумма: <b>200 ₽</b>\n\n"
        "Всё верно?"
    )
    bot.send_message(chat_id, summary, reply_markup=confirm_keyboard(), parse_mode="HTML")
    user_data[user_id]['state'] = STATE_CONFIRMING

# --- Инициализация бота ---
bot = telebot.TeleBot(BOT_TOKEN)

# === Команды ===
@bot.message_handler(commands=['start'])
@check_bot_enabled
def cmd_start(message):
    user_id = message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    bot.send_message(
        message.chat.id,
        "🏥 <b>Сертификат Энергогарант</b>\n\n"
        "💉 Защита от укуса клеща: иммуноглобулин в больницах по всей России\n"
        "💰 Стоимость: <b>200 ₽</b>\n"
        "📅 Действует до: <b>31 декабря 2025</b>\n\n"
        "Нажмите кнопку ниже или выберите команду в меню:",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

@bot.message_handler(commands=['help'])
@check_bot_enabled
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        "❓ <b>Как работает сертификат:</b>\n\n"
        "1️⃣ Оформляете заявку в боте\n"
        "2️⃣ Оплачиваете 200 ₽\n"
        "3️⃣ Получаете подтверждение\n"
        "4️⃣ При укусе клеща обращаетесь в <b>любую больницу-партнёра</b> с паспортом\n"
        "5️⃣ Вам ставят иммуноглобулин <b>бесплатно</b>\n\n"
        "📅 Сертификат действует до 31.12.2025 независимо от даты покупки",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['contacts'])
@check_bot_enabled
def cmd_contacts(message):
    bot.send_message(
        message.chat.id,
        "📞 <b>Связаться с нами:</b>\n\n"
        "По вопросам работы сертификата:\n"
        "@vasilishhka\n\n"
        "Техническая поддержка:\n"
        "Ответим в течение 24 часов",
        parse_mode="HTML"
    )

# === Начало оформления ===
@bot.message_handler(func=lambda message: message.text == "🛒 Купить сертификат Энергогарант")
@check_bot_enabled
def start_order(message):
    user_id = message.from_user.id
    user_data[user_id] = {'state': STATE_WAITING_FIO}
    bot.send_message(
        message.chat.id,
        "Введите <b>ФИО</b> полностью:\nПример: <code>Иванов Иван Иванович</code>",
        reply_markup=remove_keyboard(),
        parse_mode="HTML"
    )

# === Обработка текста (конечный автомат) ===
@bot.message_handler(func=lambda message: True)
@check_bot_enabled
def handle_user_input(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.strip() if message.text else ""

    if user_id not in user_data:
        return
    state = user_data[user_id].get('state')

    if state == STATE_WAITING_FIO:
        user_data[user_id]['fio'] = text
        user_data[user_id]['state'] = STATE_WAITING_BIRTHDATE
        bot.send_message(chat_id, "Введите <b>дату рождения</b>:\nФормат: <code>ДД.ММ.ГГГГ</code>", parse_mode="HTML")

    elif state == STATE_WAITING_BIRTHDATE:
        try:
            datetime.strptime(text, "%d.%m.%Y")
        except ValueError:
            bot.send_message(chat_id, "❌ Неверный формат. Введите как ДД.ММ.ГГГГ")
            return
        user_data[user_id]['birthdate'] = text
        user_data[user_id]['state'] = STATE_WAITING_PHONE
        bot.send_message(chat_id, "📱 <b>Поделитесь номером телефона</b> для связи:\n\nНажмите кнопку ниже 👇",
                         reply_markup=phone_keyboard(), parse_mode="HTML")

    elif state == STATE_WAITING_PHONE:
        bot.send_message(chat_id, "❌ Пожалуйста, нажмите кнопку <b>«Поделиться контактом»</b> ниже 👇",
                         reply_markup=phone_keyboard(), parse_mode="HTML")

    elif state == STATE_EDITING_FIO:
        user_data[user_id]['fio'] = text
        user_data[user_id]['state'] = STATE_CONFIRMING
        show_summary(chat_id, user_id)

    elif state == STATE_EDITING_BIRTHDATE:
        try:
            datetime.strptime(text, "%d.%m.%Y")
        except ValueError:
            bot.send_message(chat_id, "❌ Неверный формат. Введите как ДД.ММ.ГГГГ")
            return
        user_data[user_id]['birthdate'] = text
        user_data[user_id]['state'] = STATE_CONFIRMING
        show_summary(chat_id, user_id)

    elif state == STATE_EDITING_PHONE:
        bot.send_message(chat_id, "❌ Нажмите кнопку <b>«Поделиться контактом»</b> 👇",
                         reply_markup=phone_keyboard(), parse_mode="HTML")

# === Обработка контакта ===
@bot.message_handler(content_types=['contact'])
@check_bot_enabled
def handle_contact(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in user_data:
        bot.send_message(chat_id, "Пожалуйста, начните с команды /start")
        return

    state = user_data[user_id].get('state')
    phone = message.contact.phone_number

    if state == STATE_WAITING_PHONE:
        user_data[user_id]['phone'] = phone
        bot.send_message(chat_id, "✅ Контакт получен!", reply_markup=remove_keyboard())
        show_summary(chat_id, user_id)
    elif state == STATE_EDITING_PHONE:
        user_data[user_id]['phone'] = phone
        bot.send_message(chat_id, "✅ Телефон обновлён!", reply_markup=remove_keyboard())
        show_summary(chat_id, user_id)
    else:
        bot.send_message(chat_id, "✅ Контакт получен!", reply_markup=remove_keyboard())

# === Callback-обработчик (подтверждение, редактирование) ===
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    data_key = call.data

    if user_id not in user_data:
        bot.answer_callback_query(call.id, "Сессия устарела. Начните заново с /start")
        return

    if data_key == "confirm":
        data = user_data[user_id]
        username = call.from_user.username
        if username:
            contact = f"@{username}"
        else:
            first_name = call.from_user.first_name or ""
            last_name = call.from_user.last_name or ""
            contact = f"{first_name} {last_name}".strip() or "нет контакта"
        phone = data.get('phone', 'не указан')
        sheet_saved = False

        try:
            sheet = get_sheet()
            if sheet:
                row = [
                    datetime.now().strftime("%d.%m.%Y %H:%M"),
                    data['fio'],
                    data['birthdate'],
                    "ОЖИДАЕТ ОПЛАТЫ",
                    "НЕТ",
                    contact,
                    str(call.from_user.id),
                    phone
                ]
                sheet.append_row(row)
                sheet_saved = True
                logger.info(f"✅ Сохранено: {data['fio']}, тел: {phone}")
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"⚠️ Ошибка сохранения: {e}\n{error_trace}")
            bot.send_message(
                ADMIN_ID,
                f"❌ <b>Ошибка сохранения в таблицу</b>\n\n"
                f"Пользователь: {data.get('fio', 'неизвестно')}\n"
                f"Ошибка: <code>{str(e)}</code>\n\n"
                f"<pre>{error_trace[-500:]}</pre>",
                parse_mode="HTML"
            )

        # Уведомление админу
        bot.send_message(
            ADMIN_ID,
            f"🆕 <b>Новая заявка!</b>\n\n"
            f"👤 {data['fio']}\n"
            f"🎂 {data['birthdate']}\n"
            f"📱 Телефон: <code>{phone}</code>\n"
            f"💰 200 ₽\n"
            f"🔗 {contact}\n"
            f"💾 В таблице: {'✅' if sheet_saved else '❌'}",
            parse_mode="HTML"
        )

        # Ответ пользователю
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=(
                "✅ <b>Заявка принята!</b>\n\n"
                f"👤 {data['fio']}\n"
                f"🎂 {data['birthdate']}\n"
                f"📱 Телефон: <code>{phone}</code>\n"
                "📞 <b>С вами свяжутся для оплаты</b>\n"
                "📅 Действует до: <b>31.12.2025</b>"
            ),
            parse_mode="HTML"
        )
        del user_data[user_id]
        bot.answer_callback_query(call.id)

    elif data_key == "edit_fio":
        user_data[user_id]['state'] = STATE_EDITING_FIO
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="✏️ Введите <b>новое ФИО</b>:\nПример: <code>Иванов Иван Иванович</code>",
            parse_mode="HTML"
        )
        bot.answer_callback_query(call.id)

    elif data_key == "edit_birthdate":
        user_data[user_id]['state'] = STATE_EDITING_BIRTHDATE
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="✏️ Введите <b>новую дату рождения</b>:\nФормат: <code>ДД.ММ.ГГГГ</code>",
            parse_mode="HTML"
        )
        bot.answer_callback_query(call.id)

    elif data_key == "edit_phone":
        user_data[user_id]['state'] = STATE_EDITING_PHONE
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(
            chat_id,
            "📱 <b>Поделитесь номером телефона</b>:\n\nНажмите кнопку ниже 👇",
            reply_markup=phone_keyboard(),
            parse_mode="HTML"
        )
        bot.answer_callback_query(call.id)

# === Админ-команды ===
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    status = "🟢 Работает" if BOT_ENABLED else "🔧 Технические работы"
    bot.send_message(
        message.chat.id,
        f"🔧 <b>Админ-панель</b>\n\n"
        f"Статус: {status}\n\n"
        "/stats — статистика\n"
        "/enable — включить бота\n"
        "/disable — выключить бота (тех. работы)",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['enable'])
def enable_bot(message):
    global BOT_ENABLED
    if message.from_user.id != ADMIN_ID:
        return
    BOT_ENABLED = True
    bot.send_message(message.chat.id, "🟢 <b>Бот включён!</b>\nТеперь пользователи могут оформлять заявки.", parse_mode="HTML")

@bot.message_handler(commands=['disable'])
def disable_bot(message):
    global BOT_ENABLED
    if message.from_user.id != ADMIN_ID:
        return
    BOT_ENABLED = False
    bot.send_message(message.chat.id, "🔧 <b>Бот выключен.</b>\nПользователи видят сообщение о технических работах.", parse_mode="HTML")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        sheet = get_sheet()
        if sheet:
            data = sheet.get_all_values()
            total = len(data) - 1
            bot.send_message(message.chat.id, f"📊 Всего заявок: {total}")
        else:
            bot.send_message(message.chat.id, "❌ Нет подключения к таблице")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

# --- Запуск ---
if __name__ == "__main__":
    logger.info("🚀 Бот запущен! Статус: работает")
    bot.infinity_polling()
