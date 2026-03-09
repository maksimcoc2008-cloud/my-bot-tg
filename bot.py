"""
ПОЛНОФУНКЦИОНАЛЬНЫЙ БОТ ДЛЯ СТУДЕНЧЕСКИХ ДЕБАТОВ
"""

import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)

# Импортируем настройки
from config import (
    TELEGRAM_TOKEN, CHAT_LINK, ORGANIZERS, SCHEDULE,
    MGER_LINK, MGER_INFO, CONFIRMATION_TIMEOUT_HOURS,
    REG_NAME, REG_UNIVERSITY, REG_SPECIALTY, REG_COURSE, REG_PHONE,
    REG_CONFIRM, REG_CONFIRM_PARTICIPATION
)

# Импортируем менеджер Google Таблиц
from google_sheets import sheets_manager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные
TOKEN = TELEGRAM_TOKEN
user_sessions = {}  # {user_id: {data}}

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    user = update.effective_user
    
    keyboard = [
        ['🎫 Записаться на дебаты', '📅 Расписание'],
        ['👥 Чат дебатеров', '📋 Правила'],
        ['ℹ️ О клубе', '🏛️ О МГЕР'],
        ['❓ Помощь', '📞 Связь с организатором'],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"👋 Здравствуй, {user.first_name}!\n\n"
        "🎓 Добро пожаловать в Клуб студенческих дебатов!\n\n"
        "👇 Выберите интересующий вас раздел:",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    help_text = (
        "🆘 ЦЕНТР ПОМОЩИ\n\n"
        f"📞 Связь с организатором:\n{ORGANIZERS}\n\n"
        "📋 Основные команды:\n"
        "• /start - главное меню\n"
        "• /register - быстрая регистрация\n"
        "• /schedule - расписание\n"
        "• /rules - правила дебатов\n\n"
        "⚙️ Техподдержка:\n"
        "Если бот не отвечает, перезапустите его командой /start"
    )
    await update.message.reply_text(help_text)

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Правила дебатов"""
    await update.message.reply_text(
        "📋 **ПРАВИЛА ДЕБАТОВ**\n\n"
        "🎯 **Цель:** Убедить аудиторию, используя логику и факты\n\n"
        "📌 **Основные правила:**\n"
        "1. Уважай оппонента\n"
        "2. Не перебивай\n"
        "3. Используй факты, а не эмоции\n"
        "4. Следи за временем\n"
        "5. Будь вежлив\n\n"
        "⏰ **Тайминг:**\n"
        "• Вступление: 30 секунд\n"
        "• Основная речь: 2 минуты\n"
        "• Опровержение: 1 минута\n"
        "• Заключение: 30 секунд\n\n"
        "💡 **Советы новичкам:**\n"
        "• Подготовь 3 сильных аргумента\n"
        "• Практикуйся перед зеркалом\n"
        "• Слушай внимательно оппонента\n"
    )

# ==================== РЕГИСТРАЦИЯ НА ДЕБАТЫ ====================

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало регистрации"""
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        "🎫 РЕГИСТРАЦИЯ НА ДЕБАТЫ\n\n"
        f"🗓️ Дата: {SCHEDULE['next_meeting']}\n"
        f"📍 Место: {SCHEDULE['location']}\n\n"
        "Пожалуйста, напишите свое полное ФИО:"
    )
    
    # Инициализируем сессию
    user_sessions[user_id] = {
        'user_id': user_id,
        'username': update.effective_user.username or update.effective_user.first_name,
        'debate_date': SCHEDULE['next_meeting'],
        'confirmation': 'Ожидает',
        'confirmation_deadline': (datetime.now() + timedelta(hours=CONFIRMATION_TIMEOUT_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return REG_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение ФИО"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. Начните заново /start")
        return ConversationHandler.END
    
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите ФИО или /cancel")
        return REG_NAME
    
    user_sessions[user_id]['full_name'] = text
    
    await update.message.reply_text(
        "✅ Принято!\n\nТеперь напишите полностью своё учебное заведение:"
    )
    return REG_UNIVERSITY

async def get_university(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение университета"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. Начните заново /start")
        return ConversationHandler.END
    
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите название университета или /cancel")
        return REG_UNIVERSITY
    
    user_sessions[user_id]['university'] = text
    
    await update.message.reply_text(
        "🎓 Отлично! Теперь напишите полностью свою специальность:"
    )
    return REG_SPECIALTY

async def get_specialty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение специальности"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. Начните заново /start")
        return ConversationHandler.END
    
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите специальность или /cancel")
        return REG_SPECIALTY
    
    user_sessions[user_id]['specialty'] = text
    
    await update.message.reply_text(
        f"✅ Специальность '{text}' принята!\n\n"
        "На каком вы курсе?\n(Напишите цифру от 1 до 6):"
    )
    return REG_COURSE

async def get_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение курса"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. Начните заново /start")
        return ConversationHandler.END
    
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите номер курса или /cancel")
        return REG_COURSE
    
    try:
        course = int(text)
        if 1 <= course <= 6:
            user_sessions[user_id]['course'] = course
        else:
            await update.message.reply_text("Пожалуйста, введите цифру от 1 до 6:")
            return REG_COURSE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите цифру от 1 до 6:")
        return REG_COURSE
    
    await update.message.reply_text(
        "📱 Теперь напишите свой номер телефона (в формате +7XXXXXXXXXX):"
    )
    return REG_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение телефона"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. Начните заново /start")
        return ConversationHandler.END
    
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите номер телефона или /cancel")
        return REG_PHONE
    
    # Простая валидация
    phone = text.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not (phone.startswith('+7') or phone.startswith('8')) or len(phone) < 11:
        await update.message.reply_text("⚠️ Неверный формат. Введите номер в формате +7XXXXXXXXXX")
        return REG_PHONE
    
    user_sessions[user_id]['phone'] = phone
    
    await update.message.reply_text(
        "📲 И последнее: напишите свой Telegram @username\n(Если нет, напишите 'нет'):"
    )
    return REG_CONFIRM

async def get_tg_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение Telegram username и подтверждение"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. Начните заново /start")
        return ConversationHandler.END
    
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите username или /cancel")
        return REG_CONFIRM
    
    # Обработка Telegram username
    if text.lower() in ['нет', 'no', 'не указан', 'скрыт', '-']:
        tg_username = 'Не указан'
    else:
        tg_username = text if text.startswith('@') else f"@{text}"
    
    user_sessions[user_id]['tg_username'] = tg_username
    
    # Формируем сводку
    user_data = user_sessions[user_id]
    summary = (
        "📋 ПРОВЕРЬТЕ ДАННЫЕ:\n\n"
        f"👤 ФИО: {user_data['full_name']}\n"
        f"🎓 Университет: {user_data['university']}\n"
        f"📚 Специальность: {user_data.get('specialty', 'Не указана')}\n"
        f"📖 Курс: {user_data['course']}\n"
        f"📱 Телефон: {user_data['phone']}\n"
        f"📲 Telegram: {user_data['tg_username']}\n"
        f"🗓️ Дата дебатов: {user_data['debate_date']}\n\n"
        "Всё верно?"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Да, всё верно", callback_data="confirm_yes")],
        [InlineKeyboardButton("✏️ Нет, исправить", callback_data="confirm_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(summary, reply_markup=reply_markup)
    return REG_CONFIRM_PARTICIPATION

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения регистрации"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "confirm_yes":
        # Сохраняем в Google Таблицы
        try:
            success = sheets_manager.register_user(user_sessions[user_id])
        except Exception as e:
            print(f"❌ Ошибка при сохранении: {e}")
            success = False
        
        if success:
            debate_time = SCHEDULE['next_meeting'].split(',')[-1].strip()
            await query.edit_message_text(
                f"🎉 РЕГИСТРАЦИЯ УСПЕШНА!\n\n"
                f"✅ Ждем вас {SCHEDULE['next_meeting']}!\n"
                f"📍 {SCHEDULE['location']}"
            )
        else:
            await query.edit_message_text(
                "❌ ОШИБКА РЕГИСТРАЦИИ\n\n"
                f"Пожалуйста, свяжитесь с организатором: {ORGANIZERS}"
            )
        
        if user_id in user_sessions:
            del user_sessions[user_id]
        
        return ConversationHandler.END
        
    elif data == "confirm_no":
        await query.edit_message_text(
            "Давайте начнем регистрацию заново.\nНапишите свое полное ФИО:"
        )
        if user_id in user_sessions:
            user_sessions[user_id] = {
                'user_id': user_id,
                'username': update.effective_user.username or update.effective_user.first_name,
                'debate_date': SCHEDULE['next_meeting']
            }
        return REG_NAME

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена регистрации"""
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text("❌ Регистрация отменена.")
    await start(update, context)
    return ConversationHandler.END

# ==================== ИНФОРМАЦИОННЫЕ КОМАНДЫ ====================

async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Расписание"""
    await update.message.reply_text(
        f"📅 РАСПИСАНИЕ ДЕБАТОВ\n\n"
        f"🗓️ Ближайший турнир:\n"
        f"{SCHEDULE['next_meeting']}\n"
        f"📍 {SCHEDULE['location']}\n"
        f"🎯 {SCHEDULE['format']}"
    )

async def show_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ссылка на чат"""
    await update.message.reply_text(
        f"👥 ЧАТ КЛУБА ДЕБАТОВ\n\n"
        f"Присоединяйтесь: {CHAT_LINK}"
    )

async def show_about_club(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """О клубе"""
    await update.message.reply_text(
        "ℹ️ О КЛУБЕ СТУДЕНЧЕСКИХ ДЕБАТОВ\n\n"
        "🎯 Наша миссия:\n"
        "Развитие критического мышления и ораторского мастерства у студентов\n\n"
        "✨ Что мы делаем:\n"
        "• Проводим регулярные дебаты\n"
        "• Организуем турниры и чемпионаты\n"
        "• Развиваем лидерские качества"
    )

async def show_mger_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о МГЕР"""
    await update.message.reply_text(
        f"🏛️ МОЛОДАЯ ГВАРДИЯ ЕДИНОЙ РОССИИ\n\n{MGER_INFO}\n\nПодробнее: {MGER_LINK}"
    )

async def contact_organizer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Связь с организатором"""
    await update.message.reply_text(
        f"📞 СВЯЗЬ С ОРГАНИЗАТОРОМ\n\n{ORGANIZERS}"
    )

# ==================== ОБРАБОТКА КНОПОК ГЛАВНОГО МЕНЮ ====================

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок главного меню"""
    text = update.message.text
    
    if text == "🎫 Записаться на дебаты":
        return await start_registration(update, context)
    elif text == "📅 Расписание":
        await show_schedule(update, context)
    elif text == "👥 Чат дебатеров":
        await show_chat(update, context)
    elif text == "📋 Правила":
        await show_rules(update, context)
    elif text == "ℹ️ О клубе":
        await show_about_club(update, context)
    elif text == "🏛️ О МГЕР":
        await show_mger_info(update, context)
    elif text == "📞 Связь с организатором":
        await contact_organizer(update, context)
    elif text == "❓ Помощь":
        await help_command(update, context)
    else:
        await update.message.reply_text("Используйте кнопки меню или /start")
    
    return ConversationHandler.END

# ==================== КОМАНДЫ АДМИНИСТРАТОРА ====================

async def announce_debates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассылка анонса (только для админа)"""
    user_id = update.effective_user.id
    
    if str(user_id) != "1834229519":  # ID Алены
        await update.message.reply_text("❌ Эта команда только для организаторов")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /announce [сообщение]")
        return
    
    message = " ".join(context.args)
    
    try:
        all_users = sheets_manager.get_all_users()
        sent_count = 0
        
        for user in all_users:
            try:
                user_id = str(user.get('ID пользователя'))
                if user_id and user_id.isdigit():
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text=f"📢 **АНОНС ДЕБАТОВ**\n\n{message}"
                    )
                    sent_count += 1
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Ошибка отправки: {e}")
        
        await update.message.reply_text(f"✅ Анонс отправлен {sent_count} пользователям")
    except Exception as e:
        await update.message.reply_text("❌ Ошибка при отправке анонса")

# ==================== ОБРАБОТЧИКИ CALLBACK ====================

async def handle_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопок подтверждения участия"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("confirm_"):
        sheets_manager.update_confirmation(user_id, "Подтверждено")
        debate_time = SCHEDULE['next_meeting'].split(',')[-1].strip()
        await query.edit_message_text(
            f"✅ Спасибо за подтверждение! Ждем вас в {debate_time}!\n📍 {SCHEDULE['location']}"
        )
    elif data.startswith("decline_"):
        sheets_manager.update_confirmation(user_id, "Отказ")
        await query.edit_message_text(
            "❌ Жаль, что не сможете прийти. Будем рады в следующий раз!"
        )

async def handle_rating_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопок с оценками"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("rate_"):
        rating = int(data.split("_")[1])
        sheets_manager.save_feedback(user_id, f"Оценка дебатов: {rating}", rating)
        stars = "⭐" * rating
        await query.edit_message_text(
            f"✅ Спасибо за оценку {rating}/5 {stars}!"
        )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старый обработчик для остальных callback"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⚠️ Неизвестный запрос. Используйте /start")

# ========== ЕДИНЫЙ ОБРАБОТЧИК ДЛЯ ВСЕХ CALLBACK ==========
async def handle_all_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех callback-запросов"""
    query = update.callback_query
    data = query.data
    
    if data in ["confirm_yes", "confirm_no"]:
        # Для подтверждения регистрации
        await handle_confirmation(update, context)
    elif data.startswith("confirm_") or data.startswith("decline_"):
        # Для подтверждения участия (за день до)
        await handle_confirmation_callback(update, context)
    elif data.startswith("rate_"):
        # Для оценок
        await handle_rating_buttons(update, context)
    else:
        # Для всего остального
        await handle_callback_query(update, context)

# ========== ConversationHandler для регистрации ==========
reg_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex('^🎫 Записаться на дебаты$'), start_registration),
        CommandHandler('register', start_registration)
    ],
    states={
        REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        REG_UNIVERSITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_university)],
        REG_SPECIALTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_specialty)],
        REG_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_course)],
        REG_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        REG_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tg_username)],
        REG_CONFIRM_PARTICIPATION: [CallbackQueryHandler(handle_confirmation)],
    },
    fallbacks=[
        CommandHandler('cancel', cancel_registration),
        CommandHandler('start', cancel_registration),
        MessageHandler(filters.Regex('^/'), cancel_registration)
    ]
)

# ========== ГЛАВНАЯ ФУНКЦИЯ ==========
def main():
    """Запуск бота"""
    print("🤖" + "="*60)
    print("ПОЛНОФУНКЦИОНАЛЬНЫЙ БОТ ДЛЯ СТУДЕНЧЕСКИХ ДЕБАТОВ")
    print("="*60)
    
    # Проверка токена
    if not TOKEN or "ВАШ" in TOKEN or "@" in TOKEN or len(TOKEN) < 40:
        print(f"❌ ОШИБКА: Неправильный токен в config.py!")
        return
    
    print(f"✅ Токен: {TOKEN[:10]}...")
    print("🔗 Проверка подключения к Google Таблицам...")
    
    # Проверка подключения к Google Sheets
    try:
        if not sheets_manager.is_connected():
            sheets_manager.connect()
        if sheets_manager.is_connected():
            print("✅ Google Таблицы подключены")
        else:
            print("⚠️ Google Таблицы недоступны")
    except Exception as e:
        print(f"⚠️ Ошибка подключения: {e}")
    
    print("🤖 Запуск бота...")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # ========== СИСТЕМА НАПОМИНАНИЙ ==========
    job_queue = application.job_queue
    if job_queue:
        async def check_reminders(context):
            try:
                from datetime import datetime
                
                if not sheets_manager.is_connected():
                    return
                
                all_users = sheets_manager.get_all_users()
                now = datetime.now()
                
                # Получаем время дебатов из конфига
                debate_time_str = SCHEDULE['next_meeting'].split(',')[-1].strip()
                debate_hour = int(debate_time_str.split(':')[0])
                
                # Расчет времени для напоминаний
                day_before_hour = 10
                hour_before = debate_hour - 1
                after_debate_hour = (debate_hour + 3) % 24
                
                for user in all_users:
                    user_id = user.get('ID пользователя')
                    debate_date_str = user.get('Дата дебатов')
                    confirmation = user.get('Подтверждение', 'Ожидает')
                    
                    if not user_id or not debate_date_str:
                        continue
                    
                    try:
                        current_hour = now.hour
                        
                        # За день до дебатов
                        if current_hour == day_before_hour and confirmation == 'Ожидает':
                            keyboard = [
                                [InlineKeyboardButton("✅ Подтверждаю", callback_data=f"confirm_{user_id}")],
                                [InlineKeyboardButton("❌ Не смогу", callback_data=f"decline_{user_id}")]
                            ]
                            await context.bot.send_message(
                                chat_id=int(user_id),
                                text=f"📅 Завтра в {debate_date_str} дебаты! Подтвердите участие:",
                                reply_markup=InlineKeyboardMarkup(keyboard)
                            )
                        
                        # За час до дебатов
                        elif current_hour == hour_before:
                            await context.bot.send_message(
                                chat_id=int(user_id),
                                text=f"⏰ Дебаты начнутся через час! Ждем вас!"
                            )
                        
                        # Через 3 часа после дебатов
                        elif current_hour == after_debate_hour:
                            rating_keyboard = [
                                [
                                    InlineKeyboardButton("1 ⭐", callback_data="rate_1"),
                                    InlineKeyboardButton("2 ⭐⭐", callback_data="rate_2"),
                                    InlineKeyboardButton("3 ⭐⭐⭐", callback_data="rate_3")
                                ],
                                [
                                    InlineKeyboardButton("4 ⭐⭐⭐⭐", callback_data="rate_4"),
                                    InlineKeyboardButton("5 ⭐⭐⭐⭐⭐", callback_data="rate_5")
                                ]
                            ]
                            await context.bot.send_message(
                                chat_id=int(user_id),
                                text="📝 Оцените мероприятие:",
                                reply_markup=InlineKeyboardMarkup(rating_keyboard)
                            )
                            
                    except Exception as e:
                        print(f"❌ Ошибка: {e}")
                        
            except Exception as e:
                print(f"❌ Ошибка: {e}")
        
        job_queue.run_repeating(check_reminders, interval=3600, first=10)
        print("⏰ Система напоминаний запущена")
    else:
        print("⚠️ Job queue не доступен")
    
    # ========== ДОБАВЛЯЕМ ВСЕ ОБРАБОТЧИКИ ==========
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", show_rules))
    application.add_handler(CommandHandler("schedule", show_schedule))
    application.add_handler(CommandHandler("chat", show_chat))
    application.add_handler(CommandHandler("about", show_about_club))
    application.add_handler(CommandHandler("mger", show_mger_info))
    application.add_handler(CommandHandler("contact", contact_organizer))
    application.add_handler(CommandHandler("announce", announce_debates))
    
    # ConversationHandler для регистрации
    application.add_handler(reg_conv_handler)
    
    # ЕДИНЫЙ обработчик для всех callback
    application.add_handler(CallbackQueryHandler(handle_all_callbacks))
    
    # Обработчик текстовых сообщений (главное меню)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))
    
    # Запускаем бота
    print("✅ Бот запущен!")
    print("📱 Используйте /start в Telegram")
    print("🛑 Для остановки нажмите Ctrl+C")
    print(f"📅 Текущая дата: {SCHEDULE['next_meeting']}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
