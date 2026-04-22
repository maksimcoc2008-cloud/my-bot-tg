"""
СИСТЕМА НАПОМИНАНИЙ И ПОДТВЕРЖДЕНИЯ УЧАСТИЯ
"""

from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import SCHEDULE, ORGANIZERS
from google_sheets import sheets_manager
import logging
import re

logger = logging.getLogger(__name__)

class ReminderSystem:
    def __init__(self, application):
        self.application = application
    
    def parse_meeting_date(self):
        """Парсит дату мероприятия из SCHEDULE"""
        try:
            date_str = SCHEDULE.get('next_meeting', '')
            # Пример формата: "25 апреля 2026, 18:00"
            # Парсим русскую дату
            months = {
                'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
                'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
                'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
            }
            
            for month_ru, month_num in months.items():
                if month_ru in date_str:
                    # Извлекаем день
                    day_match = re.search(r'(\d+)', date_str)
                    year_match = re.search(r'(\d{4})', date_str)
                    time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
                    
                    if day_match and year_match and time_match:
                        day = int(day_match.group(1))
                        year = int(year_match.group(1))
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2))
                        
                        return datetime(year, month_num, day, hour, minute)
            return None
        except Exception as e:
            logger.error(f"Ошибка парсинга даты: {e}")
            return None
    
    async def send_day_before_reminder(self, context):
        """Отправляет напоминание за день с кнопками подтверждения"""
        meeting_date = self.parse_meeting_date()
        if not meeting_date:
            return
        
        # Форматируем дату для сообщения
        date_str = meeting_date.strftime("%d.%m.%Y в %H:%M")
        
        # Кнопки для подтверждения/отказа
        keyboard = [
            [
                InlineKeyboardButton("✅ Буду!", callback_data="confirm_attendance_yes"),
                InlineKeyboardButton("❌ Не смогу", callback_data="confirm_attendance_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Текст напоминания
        text = f"""⏰ <b>НАПОМИНАНИЕ ЗА ДЕНЬ!</b>

Завтра, {date_str}, состоится мероприятие «ПолитЗавод».

📍 <b>Место:</b> {SCHEDULE['location']}
🎯 <b>Тема:</b> {SCHEDULE['format']}

<b>Пожалуйста, подтвердите своё участие:</b>

✅ «Буду!» — мы ждём вас
❌ «Не смогу» — освободим место другому

Ответьте, нажав на кнопку ниже 👇"""
        
        # Рассылаем всем зарегистрированным пользователям
        users = sheets_manager.get_all_users()
        sent = 0
        failed = 0
        
        for user in users:
            try:
                user_id = user.get('user_id')
                if user_id and str(user_id).isdigit():
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text=text,
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
                    sent += 1
                    logger.info(f"Напоминание отправлено пользователю {user_id}")
            except Exception as e:
                failed += 1
                logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
        
        logger.info(f"Напоминания отправлены: ✅ {sent}, ❌ {failed}")
    
    async def send_day_of_reminder(self, context):
        """Отправляет напоминание в день мероприятия (только подтвердившим)"""
        meeting_date = self.parse_meeting_date()
        if not meeting_date:
            return
        
        date_str = meeting_date.strftime("%d.%m.%Y в %H:%M")
        
        text = f"""🔥 <b>СЕГОДНЯ В {meeting_date.strftime('%H:%M')}!</b>

Мероприятие «ПолитЗавод» уже сегодня!

📍 <b>Место:</b> {SCHEDULE['location']}
🎯 <b>Тема:</b> {SCHEDULE['format']}

<b>Не опаздывайте!</b> Будет интересно!

Возникли вопросы? {ORGANIZERS}"""
        
        # Отправляем только тем, кто подтвердил участие
        users = sheets_manager.get_all_users()
        sent = 0
        
        for user in users:
            try:
                confirmation = user.get('confirmation', '')
                user_id = user.get('user_id')
                
                if confirmation == 'Подтверждено' and user_id and str(user_id).isdigit():
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text=text,
                        parse_mode='HTML'
                    )
                    sent += 1
            except Exception as e:
                logger.error(f"Ошибка: {e}")
        
        logger.info(f"Дневные напоминания отправлены: {sent} пользователям")
    
    async def send_feedback_request(self, context):
        """Отправляет запрос на оценку мероприятия (на следующий день)"""
        # Кнопки для оценки
        keyboard = [
            [
                InlineKeyboardButton("⭐ 1", callback_data="rate_1"),
                InlineKeyboardButton("⭐⭐ 2", callback_data="rate_2"),
                InlineKeyboardButton("⭐⭐⭐ 3", callback_data="rate_3"),
                InlineKeyboardButton("⭐⭐⭐⭐ 4", callback_data="rate_4"),
                InlineKeyboardButton("⭐⭐⭐⭐⭐ 5", callback_data="rate_5")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""📝 <b>КАК ПРОШЛО МЕРОПРИЯТИЕ?</b>

Оцените «ПолитЗавод» от 1 до 5 звёзд:

⭐ 1 — очень плохо
⭐⭐⭐ 3 — нормально
⭐⭐⭐⭐⭐ 5 — отлично!

Ваше мнение очень важно для нас!"""
        
        # Отправляем всем, кто был на мероприятии
        users = sheets_manager.get_all_users()
        sent = 0
        
        for user in users:
            try:
                confirmation = user.get('confirmation', '')
                user_id = user.get('user_id')
                
                if confirmation == 'Подтверждено' and user_id and str(user_id).isdigit():
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text=text,
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
                    sent += 1
            except Exception as e:
                logger.error(f"Ошибка: {e}")
        
        logger.info(f"Запросы на оценку отправлены: {sent} пользователям")
    
    async def check_reminders(self, context):
        """Проверяет и отправляет напоминания в зависимости от дня"""
        try:
            if not SCHEDULE.get('has_meeting', False):
                logger.info("Нет активных мероприятий")
                return
            
            meeting_date = self.parse_meeting_date()
            if not meeting_date:
                logger.warning("Не удалось распарсить дату мероприятия")
                return
            
            today = datetime.now().date()
            meeting_day = meeting_date.date()
            days_until = (meeting_day - today).days
            
            logger.info(f"До мероприятия: {days_until} дней")
            
            if days_until == 1:
                # За день до мероприятия
                logger.info("Отправка напоминаний за день")
                await self.send_day_before_reminder(context)
                
            elif days_until == 0:
                # В день мероприятия (только утром)
                current_hour = datetime.now().hour
                if current_hour < 12:  # Отправляем только до 12 дня
                    logger.info("Отправка дневных напоминаний")
                    await self.send_day_of_reminder(context)
                    
            elif days_until == -1:
                # На следующий день после мероприятия
                logger.info("Отправка запроса на оценку")
                await self.send_feedback_request(context)
                
        except Exception as e:
            logger.error(f"Ошибка в check_reminders: {e}")

    async def handle_attendance_confirmation(self, update, context):
        """Обрабатывает подтверждение/отказ от участия"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if data == "confirm_attendance_yes":
            # Подтверждение участия
            sheets_manager.update_confirmation(str(user_id), "Подтверждено")
            await query.edit_message_text(
                "✅ <b>СПАСИБО ЗА ПОДТВЕРЖДЕНИЕ!</b>\n\n"
                "Ждем вас завтра!\n"
                f"📍 {SCHEDULE['location']}\n"
                f"⏰ Начало в 18:00\n\n"
                "До встречи! 🎉",
                parse_mode='HTML'
            )
            
        elif data == "confirm_attendance_no":
            # Отказ от участия
            sheets_manager.update_confirmation(str(user_id), "Отказ")
            await query.edit_message_text(
                "❌ <b>ЖАЛЬ, ЧТО НЕ СМОЖЕТЕ ПРИЙТИ</b>\n\n"
                "Мы будем рады видеть вас на следующих мероприятиях!\n"
                "Следите за анонсами в боте. 👋",
                parse_mode='HTML'
            )