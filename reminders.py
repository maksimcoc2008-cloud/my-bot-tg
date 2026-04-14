"""
СИСТЕМА НАПОМИНАНИЙ ДЛЯ ПОЛИТЗАВОДА
"""
import logging
from datetime import datetime
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
                print("⚠️ Google Sheets не подключены, напоминания пропущены")
                return
            
            all_users = sheets_manager.get_all_users()
            now = datetime.now()
            
            print(f"⏰ Проверка напоминаний для {len(all_users)} пользователей")
            
            # Отправляем напоминания
            for user in all_users:
                await self.process_user(user, context, now)
                
        except Exception as e:
            logger.error(f"Ошибка в системе напоминаний: {e}")
    
    async def process_user(self, user, context, now):
        """Обработка одного пользователя"""
        try:
            user_id = user.get('ID пользователя')
            if not user_id:
                return
            
            # Для теста - отправляем напоминания в определенное время
            # За день до мероприятия (в 10:00)
            if now.hour == 10 and now.minute < 5:
                keyboard = [
                    [InlineKeyboardButton("✅ Подтверждаю", callback_data=f"confirm_{user_id}")],
                    [InlineKeyboardButton("❌ Не смогу", callback_data=f"decline_{user_id}")]
                ]
                try:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text="📅 Напоминание: завтра ПолитЗавод в 19:00! Подтвердите участие:",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    print(f"✅ Напоминание отправлено {user_id}")
                except Exception as e:
                    print(f"❌ Не удалось отправить {user_id}: {e}")
            
            # За час до мероприятия (в 18:00)
            elif now.hour == 18 and now.minute < 5:
                try:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text="⏰ ПолитЗавод начнется через час! Ждем вас!"
                    )
                except Exception as e:
                    print(f"❌ Не удалось отправить {user_id}: {e}")
            
            # После мероприятия (в 22:00)
            elif now.hour == 22 and now.minute < 5:
                try:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text="📝 Как прошло мероприятие? Оцените от 1 до 5 (напишите цифру)"
                    )
                except Exception as e:
                    print(f"❌ Не удалось отправить {user_id}: {e}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки пользователя {user_id}: {e}")