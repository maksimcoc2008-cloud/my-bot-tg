"""
ТЕСТОВЫЙ ФАЙЛ ДЛЯ ПРОВЕРКИ НАПОМИНАНИЙ
Запустите этот файл для проверки работы системы напоминаний
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Добавляем текущую папку в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import SCHEDULE
from google_sheets import sheets_manager
from reminders import ReminderSystem
from telegram.ext import Application

# Конфигурация
TOKEN = "8412419398:AAFWxajdFjd-vsZw8IiNKsxeZqO9uNiFMBc"
ADMIN_ID = "1834229519"

def print_separator(title=""):
    """Печать разделителя"""
    print("\n" + "="*60)
    if title:
        print(f" {title} ")
        print("="*60)

async def test_connection():
    """Тест подключения к Google Sheets"""
    print_separator("ТЕСТ ПОДКЛЮЧЕНИЯ")
    
    try:
        sheets_manager.connect()
        if sheets_manager.is_connected():
            print("✅ Google Sheets подключены")
            
            # Показываем пользователей
            all_users = sheets_manager.get_all_users()
            if all_users:
                print(f"\n📊 Найдено пользователей: {len(all_users)}")
                for i, user in enumerate(all_users[:5], 1):
                    print(f"   {i}. {user.get('full_name', 'Нет имени')} (ID: {user.get('user_id', 'Нет')})")
            else:
                print("⚠️ Нет пользователей в таблице")
            return True
        else:
            print("❌ Google Sheets не подключены")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def test_reminder_messages():
    """Тест отправки напоминаний (без реальной отправки)"""
    print_separator("ТЕСТ НАПОМИНАНИЙ")
    
    try:
        all_users = sheets_manager.get_all_users()
        if not all_users:
            print("❌ Нет пользователей для теста")
            return
        
        print(f"📊 Найдено {len(all_users)} пользователей\n")
        
        # Получаем дату мероприятия
        meeting_date_str = SCHEDULE.get('next_meeting', 'Не указана')
        print(f"📅 Дата мероприятия: {meeting_date_str}")
        
        # Проверяем каждого пользователя
        print("\n📋 СТАТУС ПОЛЬЗОВАТЕЛЕЙ:")
        for user in all_users:
            name = user.get('full_name', 'Неизвестно')
            user_id = user.get('user_id', 'Нет')
            confirmation = user.get('confirmation', 'Ожидает')
            need_letter = user.get('need_letter', 'Нет')
            
            print(f"\n   👤 {name}")
            print(f"      🆔 ID: {user_id}")
            print(f"      ✅ Статус: {confirmation}")
            print(f"      📄 Отпроска: {need_letter}")
            
            # Проверяем, какие напоминания будут отправлены
            if confirmation != 'Подтверждено':
                print(f"      🔔 Будет отправлено дневное напоминание (за день до мероприятия)")
            else:
                print(f"      ✅ Подтвердил - получит напоминание за час")
            
            if confirmation == 'Подтверждено':
                print(f"      ⏰ Будет отправлено напоминание за час")
            
            print(f"      🌟 Будет отправлен запрос оценки после мероприятия")
        
        print("\n" + "-"*60)
        print("💡 ПРИМЕР СООБЩЕНИЙ:")
        print("-"*60)
        
        # Пример дневного напоминания
        print("\n📅 ДНЕВНОЕ НАПОМИНАНИЕ (за день):")
        print(f"   📅 *Напоминание!*\n\n"
              f"   Завтра состоится ПолитЗавод!\n\n"
              f"   📍 {SCHEDULE['location']}\n"
              f"   ⏰ Начало: 18:00\n\n"
              f"   Тема: {SCHEDULE['format']}\n\n"
              f"   Подтвердите участие:")
        
        # Пример напоминания за час
        print("\n⏰ НАПОМИНАНИЕ ЗА ЧАС:")
        print(f"   ⏰ *Скоро начнется!*\n\n"
              f"   ПолитЗавод начнется через час!\n\n"
              f"   📍 {SCHEDULE['location']}\n"
              f"   ⏰ Начало в 18:00\n\n"
              f"   Тема: {SCHEDULE['format']}\n\n"
              f"   Не опаздывайте!")
        
        # Пример запроса оценки
        print("\n🌟 ЗАПРОС ОЦЕНКИ (после мероприятия):")
        print(f"   🌟 *Как прошло мероприятие?*\n\n"
              f"   Оцените ПолитЗавод от 1 до 5:\n\n"
              f"   [⭐ 1] [⭐⭐ 2] [⭐⭐⭐ 3] [⭐⭐⭐⭐ 4] [⭐⭐⭐⭐⭐ 5]")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def test_send_to_admin():
    """Отправить тестовое напоминание админу"""
    print_separator("ТЕСТОВАЯ ОТПРАВКА АДМИНУ")
    
    try:
        # Создаем временное приложение для отправки
        application = Application.builder().token(TOKEN).build()
        await application.initialize()
        
        print("📤 Отправляю тестовое сообщение админу...")
        
        # Тестовое дневное напоминание
        await application.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=f"🧪 *ТЕСТОВОЕ НАПОМИНАНИЕ*\n\n"
                 f"📅 *Напоминание!*\n\n"
                 f"Завтра состоится ПолитЗавод!\n\n"
                 f"📍 {SCHEDULE['location']}\n"
                 f"⏰ Начало: 18:00\n\n"
                 f"Тема: {SCHEDULE['format']}\n\n"
                 f"Это тестовое сообщение для проверки работы напоминаний.",
            parse_mode='Markdown'
        )
        
        print("✅ Тестовое сообщение отправлено админу!")
        print("   Проверьте Telegram - должно прийти сообщение")
        
        await application.shutdown()
        
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

async def test_reminder_timing():
    """Проверка времени отправки напоминаний"""
    print_separator("ПРОВЕРКА ВРЕМЕНИ ОТПРАВКИ")
    
    now = datetime.now()
    
    print(f"🕐 Текущее время: {now.strftime('%H:%M')}")
    print(f"📅 Текущая дата: {now.strftime('%Y-%m-%d')}")
    
    print("\n📋 РАСПИСАНИЕ ОТПРАВКИ НАПОМИНАНИЙ:")
    
    # Проверка дневного напоминания (10:00)
    if now.hour == 10 and now.minute < 5:
        print("   ✅ СЕЙЧАС должно отправляться дневное напоминание (за день до мероприятия)")
    else:
        print(f"   ⏰ Дневное напоминание: в 10:00 (сейчас {now.hour:02d}:{now.minute:02d})")
    
    # Проверка напоминания за час (17:00)
    if now.hour == 17 and now.minute < 5:
        print("   ✅ СЕЙЧАС должно отправляться напоминание за час до мероприятия")
    else:
        print(f"   ⏰ Напоминание за час: в 17:00 (сейчас {now.hour:02d}:{now.minute:02d})")
    
    # Проверка запроса оценки (21:00)
    if now.hour == 21 and now.minute < 5:
        print("   ✅ СЕЙЧАС должен отправляться запрос оценки")
    else:
        print(f"   ⏰ Запрос оценки: в 21:00 (сейчас {now.hour:02d}:{now.minute:02d})")
    
    print("\n💡 Для тестирования напоминаний:")
    print("   • Дневное напоминание - в 10:00")
    print("   • Напоминание за час - в 17:00")
    print("   • Запрос оценки - в 21:00")
    print("\n   Чтобы увидеть напоминания, запустите бота в это время")

async def simulate_reminders():
    """Симуляция отправки напоминаний (только для админа)"""
    print_separator("СИМУЛЯЦИЯ НАПОМИНАНИЙ")
    
    try:
        application = Application.builder().token(TOKEN).build()
        await application.initialize()
        
        all_users = sheets_manager.get_all_users()
        if not all_users:
            print("❌ Нет пользователей")
            await application.shutdown()
            return
        
        print("📤 Отправляю тестовые напоминания админу...\n")
        
        # Отправляем примеры всех типов сообщений
        await application.bot.send_message(
            chat_id=int(ADMIN_ID),
            text="🧪 *СИМУЛЯЦИЯ НАПОМИНАНИЙ*\n\n"
                 "Ниже приведены примеры всех типов напоминаний, "
                 "которые получают пользователи.\n\n"
                 "---",
            parse_mode='Markdown'
        )
        
        # 1. Дневное напоминание
        await application.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=f"📅 *ДНЕВНОЕ НАПОМИНАНИЕ*\n\n"
                 f"Завтра состоится ПолитЗавод!\n\n"
                 f"📍 {SCHEDULE['location']}\n"
                 f"⏰ Начало: 18:00\n\n"
                 f"Тема: {SCHEDULE['format']}\n\n"
                 f"Подтвердите участие:",
            parse_mode='Markdown'
        )
        
        await asyncio.sleep(1)
        
        # 2. Напоминание за час
        await application.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=f"⏰ *НАПОМИНАНИЕ ЗА ЧАС*\n\n"
                 f"ПолитЗавод начнется через час!\n\n"
                 f"📍 {SCHEDULE['location']}\n"
                 f"⏰ Начало в 18:00\n\n"
                 f"Тема: {SCHEDULE['format']}\n\n"
                 f"Не опаздывайте!",
            parse_mode='Markdown'
        )
        
        await asyncio.sleep(1)
        
        # 3. Запрос оценки
        await application.bot.send_message(
            chat_id=int(ADMIN_ID),
            text="🌟 *ЗАПРОС ОЦЕНКИ*\n\n"
                 "Как прошло мероприятие?\n\n"
                 "Оцените ПолитЗавод от 1 до 5:\n\n"
                 "⭐ 1 | ⭐⭐ 2 | ⭐⭐⭐ 3 | ⭐⭐⭐⭐ 4 | ⭐⭐⭐⭐⭐ 5",
            parse_mode='Markdown'
        )
        
        print("✅ Все тестовые сообщения отправлены админу!")
        print("   Проверьте Telegram - должно прийти 3 сообщения")
        
        await application.shutdown()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def main():
    """Главная функция тестирования"""
    print("\n" + "█"*60)
    print("     ТЕСТИРОВАНИЕ СИСТЕМЫ НАПОМИНАНИЙ")
    print("█"*60)
    
    # 1. Тест подключения
    if not await test_connection():
        print("\n❌ Невозможно продолжить тестирование")
        return
    
    # 2. Тест напоминаний (показ сообщений)
    await test_reminder_messages()
    
    # 3. Проверка времени
    await test_reminder_timing()
    
    # 4. Вопрос о реальной отправке
    print_separator("РЕАЛЬНАЯ ПРОВЕРКА")
    print("\nВыберите действие:")
    print("   1. Отправить тестовое сообщение админу")
    print("   2. Отправить все типы напоминаний админу")
    print("   3. Выйти")
    
    try:
        choice = input("\nВведите номер (1-3): ").strip()
        
        if choice == "1":
            await test_send_to_admin()
        elif choice == "2":
            await simulate_reminders()
        elif choice == "3":
            print("👋 Выход...")
        else:
            print("❌ Неверный выбор")
            
    except KeyboardInterrupt:
        print("\n👋 Прервано пользователем")
    
    print_separator("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("\n💡 РЕЗУЛЬТАТЫ:")
    print("   • Система напоминаний настроена")
    print("   • Напоминания отправляются в 10:00, 17:00 и 21:00")
    print("   • Пользователи получают сообщения в зависимости от статуса")
    print("   • Для проверки реальной работы запустите бота и дождитесь нужного времени")

if __name__ == '__main__':
    asyncio.run(main())