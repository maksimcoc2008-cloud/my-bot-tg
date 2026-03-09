"""
СИСТЕМА НАПОМИНАНИЙ
"""
import logging
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class ReminderSystem:
    def __init__(self, application):
        self.application = application
        self.last_event_date = None
        
    async def check_reminders(self, context):
        """Проверка напоминаний"""
        try:
            from google_sheets import sheets_manager
            
            if not sheets_manager.is_connected():
                return
            
            all_users = sheets_manager.get_all_users()
            now = datetime.now()
            
            # Определяем текущую дату дебатов
            current_date = None
            if all_users:
                current_date = all_users[0].get('Дата дебатов') if all_users else None
            
            # Проверяем, изменилась ли дата (новое мероприятие)
            if current_date and self.last_event_date and current_date != self.last_event_date:
                print(f"📦 Новое мероприятие! Архивируем старое: {self.last_event_date}")
                # Здесь можно добавить архивацию
                
            self.last_event_date = current_date
            
            # Отправляем напоминания
            for user in all_users:
                await self.process_user(user, context, now)
                
        except Exception as e:
            logger.error(f"Ошибка: {e}")
    
    async def process_user(self, user, context, now):
        """Обработка одного пользователя"""
        try:
            user_id = user.get('ID пользователя')
            if not user_id:
                return
            
            # Для теста - отправляем разные типы напоминаний
            # В реальности нужно парсить дату из таблицы
            
            # Пример: за день
            if now.hour == 10:  # В 10 утра
                keyboard = [
                    [InlineKeyboardButton("✅ Подтверждаю", callback_data=f"confirm_{user_id}")],
                    [InlineKeyboardButton("❌ Не смогу", callback_data=f"decline_{user_id}")]
                ]
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text="📅 Напоминание: завтра дебаты в 19:00! Подтвердите участие:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
            # За час (пример)
            elif now.hour == 18 and now.minute == 0:  # В 18:00
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text="⏰ Дебаты начнутся через час! Ждем вас!"
                )
            
            # После дебатов
            elif now.hour == 22:  # В 22:00
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text="📝 Как прошли дебаты? Оцените от 1 до 5 (напишите цифру)"
                )
                
        except Exception as e:
            logger.error(f"Ошибка обработки {user_id}: {e}")