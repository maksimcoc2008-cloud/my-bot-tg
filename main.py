import asyncio
import logging
import re
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)

from config import (
    TELEGRAM_TOKEN, CHAT_LINK, ORGANIZERS, SCHEDULE,
    MGER_LINK,
    REG_NAME, REG_UNIVERSITY, REG_SPECIALTY, REG_COURSE, REG_PHONE,
    REG_LETTER, REG_LETTER_INFO, REG_CONFIRM_PARTICIPATION
)
from google_sheets import sheets_manager

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = TELEGRAM_TOKEN
user_sessions = {}
ADMIN_ID = "1834229519"

# Множество для хранения ID пользователей, о которых уже отправили отчёт
reported_users = set()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def escape_html(text: str) -> str:
    if not text:
        return text
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))

def get_meeting_date_text():
    """Возвращает текст даты мероприятия или сообщение об отсутствии"""
    if SCHEDULE.get('has_meeting', True) and SCHEDULE['next_meeting'] != "Нет":
        return f"🗓️ <b>Дата:</b> {escape_html(SCHEDULE['next_meeting'])}"
    else:
        return "📢 <b>Дата мероприятия уточняется</b> — сообщим в боте!"

def get_full_schedule_text():
    """Полный текст расписания"""
    if SCHEDULE.get('has_meeting', True) and SCHEDULE['next_meeting'] != "Нет":
        return (
            f"📅 <b>РАСПИСАНИЕ ПОЛИТЗАВОДА</b>\n\n"
            f"🗓️ <b>Ближайшая встреча:</b>\n{escape_html(SCHEDULE['next_meeting'])}\n\n"
            f"📍 <b>Место:</b>\n{escape_html(SCHEDULE['location'])}\n\n"
            f"🎯 <b>Тема:</b>\n{escape_html(SCHEDULE['format'])}\n\n"
            "⏰ <b>Начало:</b> 18:00\n\n"
            "❗ Не опаздывай — будет интересно!"
        )
    else:
        return (
            "📅 <b>РАСПИСАНИЕ ПОЛИТЗАВОДА</b>\n\n"
            "⚠️ <b>В данный момент ближайших мероприятий нет</b>\n\n"
            "Мы обязательно сообщим о новых встречах в этом боте!\n"
            "📢 Следите за анонсами.\n\n"
            "💬 Вопросы можно задать организаторам: /contact"
        )

async def safe_send_message(update: Update, text: str, parse_mode: str = 'HTML', **kwargs):
    try:
        await update.message.reply_text(text, parse_mode=parse_mode, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        clean_text = re.sub(r'<[^>]+>', '', text)
        await update.message.reply_text(clean_text, **kwargs)

async def safe_edit_message(query, text: str, parse_mode: str = 'HTML', **kwargs):
    try:
        await query.edit_message_text(text, parse_mode=parse_mode, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        clean_text = re.sub(r'<[^>]+>', '', text)
        await query.edit_message_text(clean_text, **kwargs)

# ==================== ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ ====================

async def send_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет админу отчёт о новых пользователях раз в неделю"""
    global reported_users
    
    try:
        one_week_ago = datetime.now() - timedelta(days=7)
        all_users = sheets_manager.get_all_users()
        
        if not all_users:
            return
        
        new_users = []
        for user in all_users:
            user_id = str(user.get('user_id', ''))
            if user_id in reported_users:
                continue
            
            reg_date_str = user.get('date', '')
            if reg_date_str:
                try:
                    reg_date = datetime.strptime(reg_date_str, '%Y-%m-%d %H:%M:%S')
                    if reg_date >= one_week_ago:
                        new_users.append(user)
                        reported_users.add(user_id)
                except:
                    new_users.append(user)
                    reported_users.add(user_id)
        
        if not new_users:
            return
        
        week_start = one_week_ago.strftime('%d.%m.%Y')
        week_end = datetime.now().strftime('%d.%m.%Y')
        
        report = f"📊 *ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ*\n\n"
        report += f"📅 Период: {week_start} - {week_end}\n"
        report += f"👥 Новых пользователей: {len(new_users)}\n\n"
        report += "*Список новых пользователей:*\n\n"
        
        for i, user in enumerate(new_users, 1):
            name = user.get('full_name', 'Не указано')
            user_id = user.get('user_id', 'Нет ID')
            uni = user.get('university', 'Не указан')
            phone = user.get('phone', 'Не указан')
            
            report += f"👤 *{i}. {escape_html(name)}*\n"
            report += f"   🆔 ID: `{user_id}`\n"
            report += f"   🎓 Вуз: {escape_html(uni)}\n"
            report += f"   📞 Телефон: {escape_html(phone)}\n\n"
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=report,
            parse_mode='Markdown'
        )
        
        logger.info(f"Отчёт отправлен админу. Новых пользователей: {len(new_users)}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке отчёта: {e}")

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    
    # Сохраняем информацию о новом пользователе
    try:
        if not sheets_manager.is_user_registered(user_id):
            sheets_manager.save_first_contact(user_id, user.username or "", user.first_name)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    
    keyboard = [
        ['📝 Регистрация на ПолитЗавод', '📅 Расписание'],
        ['👥 Чат ПолитЗавода', 'ℹ️ О ПолитЗаводе'],
        ['🏛️ О МГЕР', '📞 Связь с организатором'],
        ['❓ Помощь'],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await safe_send_message(
        update,
        f"👋 <b>Здравствуй, {escape_html(user.first_name)}!</b>\n\n"
        "🏭 <b>«ПолитЗавод»</b> — твой старт в большую политику!\n\n"
        "👇 <b>Выбери интересующий раздел:</b>",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🆘 <b>ЦЕНТР ПОМОЩИ</b>\n\n"
        f"📞 <b>Связь с организатором:</b>\n{escape_html(ORGANIZERS)}\n\n"
        "<b>📋 Основные команды:</b>\n"
        "• /start - главное меню\n"
        "• /register - быстрая регистрация\n"
        "• /schedule - расписание\n"
        "• /cancel - отмена регистрации"
    )
    await safe_send_message(update, help_text)

# ==================== ИНФОРМАЦИОННЫЕ КОМАНДЫ ====================

async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send_message(update, get_full_schedule_text())

async def show_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send_message(
        update,
        f"👥 <b>ЧАТ ПОЛИТЗАВОДА</b>\n\n"
        "🗣️ Общайся, спорь, обсуждай политику\n"
        "🤝 Находи единомышленников\n"
        "📢 Узнавай новости первым\n\n"
        f"Присоединяйтесь: {escape_html(CHAT_LINK)}"
    )

async def show_about_club(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send_message(
        update,
        "🏭 <b>«ПОЛИТЗАВОД»</b> — кадрово-образовательный проект\n"
        "«Молодой Гвардии Единой России»\n\n"
        "🎯 Проект открывает для молодежи <b>реальные возможности</b>\n"
        "для входа в общественно-политическую сферу страны.\n\n"
        "<b>📚 Что получает участник:</b>\n"
        "• Практико-ориентированное обучение\n"
        "• Наставничество и полезные знакомства\n"
        "• Реальные возможности карьерного роста в политике\n"
        "• Стажировки в органах государственной власти\n\n"
        "<b>📈 Карьерные перспективы по итогам проекта:</b>\n"
        "• Депутат законодательного органа\n"
        "• Помощник депутата\n"
        "• Стажировка в Администрации города\n"
        "• Стажировка в Правительстве области\n\n"
        "<b>🌟 Результаты проекта за 2025 год:</b>\n"
        "• Более 80 участников по всей стране стали депутатами\n"
        "• Более 500 человек получили стажировки в органах власти\n\n"
        "🚀 <b>Стань частью команды будущих лидеров! /register</b>"
    )

async def show_mger_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send_message(
        update,
        "🏛️ <b>МОЛОДАЯ ГВАРДИЯ ЕДИНОЙ РОССИИ</b>\n\n"
        "МГЕР — это <b>всероссийская сеть</b>, которая объединяет тех,\n"
        "кто хочет <b>влиять на решения уже сегодня</b>.\n\n"
        "💪 Мы — <b>кадровый резерв</b> для работы в депутатском корпусе,\n"
        "органах власти и управленческих структурах.\n\n"
        "<b>📌 Наши направления:</b>\n"
        "• 🏛️ Политическая деятельность\n"
        "• 📱 Медиа и информационная работа\n"
        "• 🇷🇺 Патриотическое воспитание\n"
        "• 🤝 Волонтерство и добровольчество\n"
        "• ⚽ Спортивные и культурные проекты\n\n"
        "<b>✨ Что это дает тебе:</b>\n"
        "• Опыт работы с депутатами и чиновниками\n"
        "• Участие в федеральных проектах\n"
        "• Возможность заявить о себе на региональном и всероссийском уровне\n\n"
        f"🔗 <b>Подробнее:</b> {escape_html(MGER_LINK)}\n\n"
        "💬 <b>Хочешь стать частью команды?</b>\n"
        "👉 Присоединяйся: https://clck.ru/3RLeNJ"
    )

async def contact_organizer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send_message(
        update,
        f"📞 <b>СВЯЗЬ С ОРГАНИЗАТОРОМ</b>\n\n"
        f"{escape_html(ORGANIZERS)}\n\n"
        "<b>📌 По каким вопросам можно обращаться:</b>\n"
        "• Регистрация на мероприятия\n"
        "• Технические проблемы с ботом\n"
        "• Предложения и идеи\n"
        "• Сотрудничество\n"
        "• Вопросы по проектам МГЕР\n\n"
        "<b>⏰ Время ответа:</b>\n"
        "Стараемся отвечать в течение 2 часов\n\n"
        "💬 Пиши, мы всегда на связи!"
    )

# ==================== РЕГИСТРАЦИЯ ====================

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"\n🚀 НАЧАЛО РЕГИСТРАЦИИ для {user_id}")
    
    # ПРОВЕРКА: есть ли мероприятие
    if not SCHEDULE.get('has_meeting', True) or SCHEDULE['next_meeting'] == "Нет":
        keyboard = [
            [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")]
        ]
        await update.message.reply_text(
            "⏸️ <b>РЕГИСТРАЦИЯ ВРЕМЕННО НЕДОСТУПНА</b>\n\n"
            "На данный момент нет запланированных мероприятий.\n"
            "Как только появится новая дата, мы сразу сообщим в боте!\n\n"
            "📢 Следите за обновлениями в разделе /schedule",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    meeting_info = get_meeting_date_text()
    
    try:
        if sheets_manager.is_connected():
            if sheets_manager.is_user_registered(str(user_id)):
                keyboard = [
                    [InlineKeyboardButton("📝 Перезаписаться", callback_data="force_registration")],
                    [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")]
                ]
                await update.message.reply_text(
                    "⚠️ <b>ВНИМАНИЕ!</b>\n\nВы уже регистрировались.\nХотите обновить данные?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
                return REG_NAME
    except Exception as e:
        print(f"Ошибка: {e}")
    
    await safe_send_message(
        update,
        f"📝 <b>РЕГИСТРАЦИЯ НА ПОЛИТЗАВОД</b>\n\n"
        f"{meeting_info}\n\n"
        f"📍 <b>Место:</b> {escape_html(SCHEDULE['location'])}\n"
        f"🎯 <b>Тема:</b> {escape_html(SCHEDULE['format'])}\n\n"
        "Пожалуйста, напишите свое полное ФИО:"
    )
    
    current_date = SCHEDULE['next_meeting'] if SCHEDULE.get('has_meeting', True) else "Дата уточняется"
    
    user_sessions[user_id] = {
        'user_id': str(user_id),
        'username': update.effective_user.username or update.effective_user.first_name,
        'debate_date': current_date,
        'confirmation': 'Ожидает',
        'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    return REG_NAME

async def handle_registration_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if query.data == "force_registration":
        await safe_edit_message(query, "📝 Напишите свое полное ФИО:")
        if user_id in user_sessions:
            del user_sessions[user_id]
        current_date = SCHEDULE['next_meeting'] if SCHEDULE.get('has_meeting', True) else "Дата уточняется"
        user_sessions[user_id] = {
            'user_id': str(user_id),
            'username': update.effective_user.username or update.effective_user.first_name,
            'debate_date': current_date,
            'confirmation': 'Ожидает',
            'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        return REG_NAME
    elif query.data == "back_to_menu":
        if user_id in user_sessions:
            del user_sessions[user_id]
        await safe_edit_message(query, "Возвращаемся в меню...")
        keyboard = [
            ['📝 Регистрация на ПолитЗавод', '📅 Расписание'],
            ['👥 Чат ПолитЗавода', 'ℹ️ О ПолитЗаводе'],
            ['🏛️ О МГЕР', '📞 Связь с организатором'],
            ['❓ Помощь'],
        ]
        await context.bot.send_message(
            chat_id=user_id,
            text="👋 Выберите раздел:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if user_id not in user_sessions:
        current_date = SCHEDULE['next_meeting'] if SCHEDULE.get('has_meeting', True) else "Дата уточняется"
        user_sessions[user_id] = {
            'user_id': str(user_id),
            'username': update.effective_user.username or update.effective_user.first_name,
            'debate_date': current_date,
            'confirmation': 'Ожидает',
            'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите ФИО или /cancel")
        return REG_NAME
    user_sessions[user_id]['full_name'] = text
    await update.message.reply_text("✅ Принято!\n\nТеперь напишите учебное заведение:")
    return REG_UNIVERSITY

async def get_university(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. /start")
        return ConversationHandler.END
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите название вуза")
        return REG_UNIVERSITY
    user_sessions[user_id]['university'] = text
    await update.message.reply_text("🎓 Отлично! Теперь напишите специальность:")
    return REG_SPECIALTY

async def get_specialty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. /start")
        return ConversationHandler.END
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите специальность")
        return REG_SPECIALTY
    user_sessions[user_id]['specialty'] = text
    await update.message.reply_text("✅ Принято!\n\nНа каком вы курсе?")
    return REG_COURSE

async def get_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. /start")
        return ConversationHandler.END
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите курс (1-6)")
        return REG_COURSE
    try:
        course = int(text)
        if 1 <= course <= 6:
            user_sessions[user_id]['course'] = course
        else:
            await update.message.reply_text("Введите цифру от 1 до 6:")
            return REG_COURSE
    except ValueError:
        await update.message.reply_text("Введите цифру от 1 до 6:")
        return REG_COURSE
    await update.message.reply_text("📱 Теперь напишите номер телефона:")
    return REG_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. /start")
        return ConversationHandler.END
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите номер телефона")
        return REG_PHONE
    phone = text.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not (phone.startswith('+7') or phone.startswith('8')) or len(phone) < 11:
        await update.message.reply_text("⚠️ Введите номер в формате +7XXXXXXXXXX")
        return REG_PHONE
    user_sessions[user_id]['phone'] = phone
    await update.message.reply_text("📄 Нужно ли вам отпросительное письмо?\nОтветьте: Да или Нет")
    return REG_LETTER

async def get_letter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. /start")
        return ConversationHandler.END
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите Да или Нет")
        return REG_LETTER
    if text in ['да', 'yes', 'lf', '+']:
        user_sessions[user_id]['need_letter'] = 'Да'
        await update.message.reply_text(
            "❤️ *Если вам необходимо отпросительное письмо, вышлите информацию:*\n\n"
            "1️⃣ ФИО директора/ректора\n"
            "2️⃣ Полное наименование учебного заведения\n"
            "3️⃣ Класс/курс\n"
            "4️⃣ Ваше ФИО\n"
            "5️⃣ Наименование мероприятия\n"
            "6️⃣ Вид письма: Оригинал/Электронное\n\n"
            "📝 *Напишите одним сообщением, разделяя запятыми:*\n\n"
            "`Иванов И.И., ТюмГУ, 3 курс, Петров П.П., ПолитЗавод, Электронное`",
            parse_mode='Markdown'
        )
        return REG_LETTER_INFO
    elif text in ['нет', 'no', 'ytn', '-']:
        user_sessions[user_id]['need_letter'] = 'Нет'
        user_data = user_sessions[user_id]
        summary = (
            "📋 <b>ПРОВЕРЬТЕ ДАННЫЕ:</b>\n\n"
            f"👤 <b>ФИО:</b> {escape_html(user_data['full_name'])}\n"
            f"🎓 <b>Университет:</b> {escape_html(user_data['university'])}\n"
            f"📚 <b>Специальность:</b> {escape_html(user_data.get('specialty', 'Не указана'))}\n"
            f"📖 <b>Курс:</b> {user_data['course']}\n"
            f"📱 <b>Телефон:</b> {escape_html(user_data['phone'])}\n"
            f"📄 <b>Отпроска:</b> Нет\n"
            f"🗓️ <b>Дата:</b> {escape_html(user_data['debate_date'])}\n\n"
            "Всё верно?"
        )
        keyboard = [
            [InlineKeyboardButton("✅ Да, всё верно", callback_data="confirm_yes")],
            [InlineKeyboardButton("✏️ Нет, исправить", callback_data="confirm_no")]
        ]
        await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return REG_CONFIRM_PARTICIPATION
    else:
        await update.message.reply_text("❌ Ответьте Да или Нет")
        return REG_LETTER

async def get_letter_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ Сессия устарела. /start")
        return ConversationHandler.END
    if text.startswith('/'):
        if text == '/cancel':
            return await cancel_registration(update, context)
        await update.message.reply_text("❌ Введите информацию или /cancel")
        return REG_LETTER_INFO
    user_sessions[user_id]['letter_info'] = text
    user_data = user_sessions[user_id]
    summary = (
        "📋 <b>ПРОВЕРЬТЕ ДАННЫЕ:</b>\n\n"
        f"👤 <b>ФИО:</b> {escape_html(user_data['full_name'])}\n"
        f"🎓 <b>Университет:</b> {escape_html(user_data['university'])}\n"
        f"📚 <b>Специальность:</b> {escape_html(user_data.get('specialty', 'Не указана'))}\n"
        f"📖 <b>Курс:</b> {user_data['course']}\n"
        f"📱 <b>Телефон:</b> {escape_html(user_data['phone'])}\n"
        f"📄 <b>Отпроска:</b> Да\n"
        f"📝 <b>Информация:</b>\n{escape_html(user_data['letter_info'])}\n\n"
        f"🗓️ <b>Дата:</b> {escape_html(user_data['debate_date'])}\n\n"
        "Всё верно?"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Да, всё верно", callback_data="confirm_yes")],
        [InlineKeyboardButton("✏️ Нет, исправить", callback_data="confirm_no")]
    ]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return REG_CONFIRM_PARTICIPATION

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data
    
    if data == "confirm_yes":
        # Сразу показываем сообщение о сохранении
        await safe_edit_message(
            query,
            "⏳ <b>ПОДОЖДИТЕ...</b>\n\n"
            "Ваши данные сохраняются в таблицу.\n"
            "Пожалуйста, не нажимайте кнопку повторно 🙏"
        )
        
        try:
            if sheets_manager.is_connected():
                if sheets_manager.is_user_registered(str(user_id)):
                    success = sheets_manager.update_user(user_sessions[user_id])
                    action = "обновлена"
                else:
                    success = sheets_manager.register_user(user_sessions[user_id])
                    action = "сохранена"
            else:
                success = False
        except Exception as e:
            success = False
            logger.error(f"Ошибка сохранения: {e}")
        
        if success:
            if SCHEDULE.get('has_meeting', True) and SCHEDULE['next_meeting'] != "Нет":
                success_text = (
                    f"🎉 <b>РЕГИСТРАЦИЯ УСПЕШНА!</b>\n\n"
                    f"✅ Ваша запись {action}!\n"
                    f"🗓️ Ждем вас {escape_html(SCHEDULE['next_meeting'])}!\n"
                    f"📍 {escape_html(SCHEDULE['location'])}\n"
                    f"🎯 Тема: {escape_html(SCHEDULE['format'])}"
                )
            else:
                success_text = (
                    f"🎉 <b>РЕГИСТРАЦИЯ УСПЕШНА!</b>\n\n"
                    f"✅ Ваша запись {action}!\n"
                    f"📢 О дате следующего мероприятия мы сообщим дополнительно в этом боте.\n\n"
                    f"💬 Вопросы: {escape_html(ORGANIZERS)}"
                )
            await safe_edit_message(query, success_text)
        else:
            await safe_edit_message(
                query,
                f"❌ <b>ОШИБКА РЕГИСТРАЦИИ</b>\n\n"
                f"Данные не сохранились. Свяжитесь с организатором:\n"
                f"{escape_html(ORGANIZERS)}"
            )
        
        if user_id in user_sessions:
            del user_sessions[user_id]
        return ConversationHandler.END
        
    elif data == "confirm_no":
        await safe_edit_message(query, "🔄 Начнем заново.\nНапишите ФИО:")
        if user_id in user_sessions:
            current_date = SCHEDULE['next_meeting'] if SCHEDULE.get('has_meeting', True) else "Дата уточняется"
            user_sessions[user_id] = {
                'user_id': str(user_id),
                'username': update.effective_user.username or update.effective_user.first_name,
                'debate_date': current_date,
                'confirmation': 'Ожидает',
                'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        return REG_NAME

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    await update.message.reply_text("❌ Регистрация отменена.")
    await start(update, context)
    return ConversationHandler.END

# ==================== КОМАНДЫ АДМИНИСТРАТОРА ====================

async def announce_debates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ Только для организаторов")
        return
    if not context.args:
        await update.message.reply_text("📢 /announce [текст]")
        return
    message = " ".join(context.args)
    status_msg = await update.message.reply_text("🔄 Рассылка...")
    try:
        all_users = sheets_manager.get_all_users()
        if not all_users:
            await status_msg.edit_text("❌ Нет пользователей")
            return
        sent, failed = 0, 0
        for user in all_users:
            try:
                uid = str(user.get('user_id', ''))
                if uid and uid.isdigit():
                    await context.bot.send_message(
                        chat_id=int(uid),
                        text=f"📢 *АНОНС*\n\n{message}",
                        parse_mode='Markdown'
                    )
                    sent += 1
                    await asyncio.sleep(0.05)
                else:
                    failed += 1
            except:
                failed += 1
        await status_msg.edit_text(f"✅ Рассылка\n\n✅ {sent}\n❌ {failed}", parse_mode='Markdown')
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")

async def test_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ Только для админа")
        return
    try:
        all_users = sheets_manager.get_all_users()
        if not all_users:
            await update.message.reply_text("❌ Нет пользователей")
            return
        report = "📊 *ПОЛЬЗОВАТЕЛИ*\n\n"
        for i, user in enumerate(all_users, 1):
            report += f"👤 *{i}. {user.get('full_name', 'Нет')}*\n"
            report += f"   🆔 ID: `{user.get('user_id', 'Нет')}`\n"
            report += f"   📄 Отпроска: {user.get('need_letter', 'Нет')}\n\n"
        await update.message.reply_text(report, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def show_letter_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ Только для админа")
        return
    try:
        requests = sheets_manager.get_letter_requests()
        if not requests:
            await update.message.reply_text("❌ Нет заявок")
            return
        report = "📄 *ЗАЯВКИ НА ОТПРОСКУ*\n\n"
        for i, req in enumerate(requests, 1):
            report += f"👤 *{i}. {req.get('student_name', 'Нет')}*\n"
            report += f"   👨‍💼 Директор: {req.get('director', 'Нет')}\n"
            report += f"   🏛️ Вуз: {req.get('university', 'Нет')}\n"
            report += f"   📖 Курс: {req.get('course', 'Нет')}\n"
            report += f"   📝 Мероприятие: {req.get('event', 'Нет')}\n"
            report += f"   📄 Вид: {req.get('type', 'Нет')}\n"
            report += f"   📅 Дата: {req.get('date', 'Нет')}\n\n"
        await update.message.reply_text(report, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def send_rating_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ Только для организаторов")
        return
    
    status_msg = await update.message.reply_text("🔄 Отправляю опрос...")
    
    try:
        all_users = sheets_manager.get_all_users()
        if not all_users:
            await status_msg.edit_text("❌ Нет пользователей")
            return
        
        keyboard = [
            [InlineKeyboardButton("⭐ 1", callback_data="rate_1"),
             InlineKeyboardButton("⭐⭐ 2", callback_data="rate_2"),
             InlineKeyboardButton("⭐⭐⭐ 3", callback_data="rate_3")],
            [InlineKeyboardButton("⭐⭐⭐⭐ 4", callback_data="rate_4"),
             InlineKeyboardButton("⭐⭐⭐⭐⭐ 5", callback_data="rate_5")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sent_count = 0
        failed_count = 0
        
        for user in all_users:
            try:
                user_id_str = str(user.get('user_id', ''))
                if user_id_str and user_id_str.isdigit():
                    await context.bot.send_message(
                        chat_id=int(user_id_str),
                        text="🌟 *Оцените мероприятие «ПолитЗавод»!*\n\n"
                             "Насколько вам понравилось?\n"
                             "Выберите оценку:",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                    await asyncio.sleep(0.05)
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                print(f"❌ Ошибка: {e}")
        
        await status_msg.edit_text(
            f"✅ *ОПРОС ОТПРАВЛЕН!*\n\n"
            f"📊 Отправлено: {sent_count}\n"
            f"❌ Не отправлено: {failed_count}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")

async def rating_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ Только для админа")
        return
    await update.message.reply_text("📊 Собираю статистику...")
    try:
        stats = sheets_manager.get_feedback_stats()
        if not stats:
            await update.message.reply_text("❌ Нет данных")
            return
        ratings = stats['ratings']
        total = stats['total']
        avg = stats['average']
        recent = stats['recent']
        max_rating = max(ratings.values()) if ratings.values() else 1
        def get_bar(c):
            if max_rating == 0:
                return "░░░░░░░░░░░░░░░░░░░░"
            filled = int(c / max_rating * 20)
            return "█" * filled + "░" * (20 - filled)
        report = f"📊 *СТАТИСТИКА ОЦЕНОК*\n\n"
        report += f"📝 Всего: {total}\n⭐ Средний: {avg:.2f}\n\n"
        report += "*Распределение:*\n"
        report += f"⭐ 1: {ratings[1]} {get_bar(ratings[1])}\n"
        report += f"⭐⭐ 2: {ratings[2]} {get_bar(ratings[2])}\n"
        report += f"⭐⭐⭐ 3: {ratings[3]} {get_bar(ratings[3])}\n"
        report += f"⭐⭐⭐⭐ 4: {ratings[4]} {get_bar(ratings[4])}\n"
        report += f"⭐⭐⭐⭐⭐ 5: {ratings[5]} {get_bar(ratings[5])}\n\n"
        report += "*Проценты:*\n"
        report += f"⭐ 1: {ratings[1]/total*100:.1f}%\n"
        report += f"⭐⭐ 2: {ratings[2]/total*100:.1f}%\n"
        report += f"⭐⭐⭐ 3: {ratings[3]/total*100:.1f}%\n"
        report += f"⭐⭐⭐⭐ 4: {ratings[4]/total*100:.1f}%\n"
        report += f"⭐⭐⭐⭐⭐ 5: {ratings[5]/total*100:.1f}%\n\n"
        if recent:
            report += "*Последние:*\n"
            for r in recent:
                rating_val = r.get('rating', 0)
                name = r.get('name', 'Неизвестно')
                date = r.get('date', '')
                report += f"   • {name} - {rating_val}⭐ ({date})\n"
        await update.message.reply_text(report, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ Только для админа")
        return
    if not context.args:
        await update.message.reply_text("📝 /remove_user [id]\nПример: /remove_user 123456789")
        return
    target = context.args[0]
    try:
        if not target.isdigit():
            await update.message.reply_text("❌ ID должен содержать только цифры")
            return
        if sheets_manager.delete_user(target):
            await update.message.reply_text(f"✅ Пользователь {target} удален")
        else:
            await update.message.reply_text(f"❌ Пользователь {target} не найден")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def stats_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ Только для админа")
        return
    try:
        all_users = sheets_manager.get_all_users()
        if not all_users:
            await update.message.reply_text("❌ Нет пользователей")
            return
        total = len(all_users)
        need_letter = sum(1 for u in all_users if u.get('need_letter') == 'Да')
        confirmed = sum(1 for u in all_users if u.get('confirmation') == 'Подтверждено')
        courses = {1:0, 2:0, 3:0, 4:0, 5:0, 6:0}
        for u in all_users:
            c = u.get('course')
            if c and str(c).isdigit():
                c_int = int(c)
                if c_int in courses:
                    courses[c_int] += 1
        report = f"📊 *ОБЩАЯ СТАТИСТИКА*\n\n"
        report += f"👥 Всего: {total}\n"
        report += f"📄 Отпроска: {need_letter}\n"
        report += f"✅ Подтвердили: {confirmed}\n"
        report += f"⏳ Ожидают: {total - confirmed}\n\n"
        report += "*По курсам:*\n"
        for c, count in courses.items():
            if count > 0:
                report += f"   • {c} курс: {count} чел.\n"
        await update.message.reply_text(report, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def set_meeting_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновить дату мероприятия (только для админа)"""
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ Только для организаторов")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 <b>Использование:</b>\n"
            "/set_date [дата] - установить дату\n"
            "/set_date none - убрать дату (нет мероприятий)\n\n"
            "<b>Пример:</b>\n"
            "/set_date 25 апреля 2026, 18:00",
            parse_mode='HTML'
        )
        return
    
    new_date = " ".join(context.args)
    
    if new_date.lower() == "none":
        SCHEDULE['has_meeting'] = False
        await update.message.reply_text("✅ Режим: <b>нет ближайших мероприятий</b>", parse_mode='HTML')
    else:
        SCHEDULE['next_meeting'] = new_date
        SCHEDULE['has_meeting'] = True
        await update.message.reply_text(f"✅ Дата обновлена: <b>{new_date}</b>", parse_mode='HTML')

async def send_test_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить тестовый отчёт (только для админа)"""
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ Только для организаторов")
        return
    
    await update.message.reply_text("🔄 Отправляю тестовый отчёт...")
    await send_weekly_report(context)
    await update.message.reply_text("✅ Отчёт отправлен!")

# ==================== ОБРАБОТКА КНОПОК МЕНЮ ====================

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if user_id in user_sessions:
        return
    if text == "📝 Регистрация на ПолитЗавод":
        return await start_registration(update, context)
    elif text == "📅 Расписание":
        await show_schedule(update, context)
    elif text == "👥 Чат ПолитЗавода":
        await show_chat(update, context)
    elif text == "ℹ️ О ПолитЗаводе":
        await show_about_club(update, context)
    elif text == "🏛️ О МГЕР":
        await show_mger_info(update, context)
    elif text == "📞 Связь с организатором":
        await contact_organizer(update, context)
    elif text == "❓ Помощь":
        await help_command(update, context)
    return ConversationHandler.END

# ==================== ОБРАБОТЧИКИ CALLBACK ====================

async def handle_rating_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    if data.startswith("rate_"):
        rating = int(data.split("_")[1])
        sheets_manager.save_feedback(str(user_id), f"Оценка: {rating}", rating)
        stars = "⭐" * rating
        await query.edit_message_text(f"✅ Спасибо! {rating}/5 {stars}")

async def handle_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    if data.startswith("confirm_"):
        sheets_manager.update_confirmation(str(user_id), "Подтверждено")
        await query.edit_message_text("✅ Спасибо! Ждем вас!")
    elif data.startswith("decline_"):
        sheets_manager.update_confirmation(str(user_id), "Отказ")
        await query.edit_message_text("❌ Жаль! Будем рады в следующий раз!")

async def handle_all_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data in ["confirm_yes", "confirm_no"]:
        await handle_confirmation(update, context)
    elif data in ["force_registration", "back_to_menu"]:
        await handle_registration_choice(update, context)
    elif data.startswith("confirm_") or data.startswith("decline_"):
        await handle_confirmation_callback(update, context)
    elif data.startswith("rate_"):
        await handle_rating_buttons(update, context)
    else:
        await query.answer()
        await safe_edit_message(query, "⚠️ Неизвестный запрос")

# ========== CONVERSATION HANDLER ==========
reg_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex('^📝 Регистрация на ПолитЗавод$'), start_registration),
        CommandHandler('register', start_registration),
        CallbackQueryHandler(handle_registration_choice, pattern="^(force_registration|back_to_menu)$")
    ],
    states={
        REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        REG_UNIVERSITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_university)],
        REG_SPECIALTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_specialty)],
        REG_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_course)],
        REG_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        REG_LETTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_letter)],
        REG_LETTER_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_letter_info)],
        REG_CONFIRM_PARTICIPATION: [CallbackQueryHandler(handle_confirmation)],
    },
    fallbacks=[
        CommandHandler('cancel', cancel_registration),
        CommandHandler('start', start),
        MessageHandler(filters.Regex('^/'), cancel_registration)
    ],
    name="registration_conversation",
    persistent=False,
    allow_reentry=True
)

# ========== ГЛАВНАЯ ФУНКЦИЯ ==========
def main():
    print("🤖" + "="*60)
    print("БОТ ДЛЯ ПОЛИТЗАВОДА")
    print("="*60)
    if not TOKEN or len(TOKEN) < 40:
        print("❌ Неправильный токен!")
        return
    print(f"✅ Токен: {TOKEN[:10]}...")
    
    try:
        sheets_manager.connect()
        if sheets_manager.is_connected():
            print("✅ Система данных готова")
        else:
            print("⚠️ Ошибка данных")
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
    
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )
    
    # Job queue для напоминаний и отчётов
    job_queue = application.job_queue
    if job_queue:
        try:
            from reminders import ReminderSystem
            reminder_system = ReminderSystem(application)
            async def check_reminders(context):
                await reminder_system.check_reminders(context)
            job_queue.run_repeating(check_reminders, interval=3600, first=10)
            print("⏰ Система напоминаний запущена")
        except Exception as e:
            print(f"⚠️ Ошибка напоминаний: {e}")
        
        # Запускаем еженедельный отчёт (каждые 7 дней)
        try:
            job_queue.run_repeating(send_weekly_report, interval=604800, first=60)
            print("📊 Еженедельный отчёт о новых пользователях запущен")
        except Exception as e:
            print(f"⚠️ Ошибка запуска отчёта: {e}")
    else:
        print("⚠️ Job queue не доступен")
    
    # Обработчики
    application.add_handler(reg_conv_handler)
    application.add_handler(CallbackQueryHandler(handle_all_callbacks))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("schedule", show_schedule))
    application.add_handler(CommandHandler("chat", show_chat))
    application.add_handler(CommandHandler("about", show_about_club))
    application.add_handler(CommandHandler("mger", show_mger_info))
    application.add_handler(CommandHandler("contact", contact_organizer))
    application.add_handler(CommandHandler("announce", announce_debates))
    application.add_handler(CommandHandler("test_users", test_users))
    application.add_handler(CommandHandler("letter_requests", show_letter_requests))
    application.add_handler(CommandHandler("rate_poll", send_rating_poll))
    application.add_handler(CommandHandler("rating_stats", rating_stats))
    application.add_handler(CommandHandler("remove_user", remove_user))
    application.add_handler(CommandHandler("stats_all", stats_all))
    application.add_handler(CommandHandler("set_date", set_meeting_date))
    application.add_handler(CommandHandler("test_report", send_test_report))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))
    
    print("✅ Бот запущен!")
    print("📱 Используйте /start")
    print("📊 Для теста отчёта: /test_report")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES, poll_interval=1.0, timeout=30, drop_pending_updates=True)
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    main()