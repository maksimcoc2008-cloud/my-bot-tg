"""
ТЕСТОВЫЙ ФАЙЛ ДЛЯ ПРОВЕРКИ НАПОМИНАНИЙ И ПОДТВЕРЖДЕНИЯ
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
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
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
                    status = user.get('confirmation', 'Ожидает')
                    status_icon = "✅" if status == "Подтверждено" else "❌" if status == "Отказ" else "⏳"
                    print(f"   {i}. {user.get('full_name', 'Нет имени')} {status_icon} {status}")
            else:
                print("⚠️ Нет пользователей в таблице")
            return True
        else:
            print("❌ Google Sheets не подключены")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def test_confirmation_buttons():
    """Тест кнопок подтверждения"""
    print_separator("ТЕСТ КНОПОК ПОДТВЕРЖДЕНИЯ")
    
    # Кнопки для подтверждения/отказа
    keyboard = [
        [
            InlineKeyboardButton("✅ Буду!", callback_data="confirm_attendance_yes"),
            InlineKeyboardButton("❌ Не смогу", callback_data="confirm_attendance_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    print("📋 ПРИМЕР КНОПОК ПОДТВЕРЖДЕНИЯ:")
    print("   [✅ Буду!]  [❌ Не смогу]")
    print("\n💡 При нажатии:")
    print("   • '✅ Буду!' → статус в таблице меняется на 'Подтверждено'")
    print("   • '❌ Не смогу' → статус в таблице меняется на 'Отказ'")
    print("   • Без ответа → статус 'Ожидает'")
    
    return reply_markup

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
        
        # Статистика по статусам
        stats = {
            'Подтверждено': 0,
            'Отказ': 0,
            'Ожидает': 0
        }
        
        print("\n📋 СТАТУС ПОЛЬЗОВАТЕЛЕЙ:")
        for user in all_users:
            name = user.get('full_name', 'Неизвестно')
            user_id = user.get('user_id', 'Нет')
            confirmation = user.get('confirmation', 'Ожидает')
            need_letter = user.get('need_letter', 'Нет')
            
            stats[confirmation] = stats.get(confirmation, 0) + 1
            
            status_icon = "✅" if confirmation == "Подтверждено" else "❌" if confirmation == "Отказ" else "⏳"
            print(f"\n   {status_icon} {name}")
            print(f"      🆔 ID: {user_id}")
            print(f"      Статус: {confirmation}")
            print(f"      📄 Отпроска: {need_letter}")
            
            # Какие напоминания получит
            if confirmation == "Подтверждено":
                print(f"      🔔 Получит: дневное напоминание + напоминание за час")
            elif confirmation == "Отказ":
                print(f"      🔕 Не получит напоминаний (отказался)")
            else:
                print(f"      ⏳ Получит: дневное напоминание с кнопками")
        
        print("\n" + "-"*60)
        print("📊 СТАТИСТИКА СТАТУСОВ:")
        print(f"   ✅ Подтвердили: {stats['Подтверждено']}")
        print(f"   ❌ Отказались: {stats['Отказ']}")
        print(f"   ⏳ Ожидают: {stats['Ожидает']}")
        
        print("\n" + "-"*60)
        print("💡 ПРИМЕРЫ СООБЩЕНИЙ:")
        print("-"*60)
        
        # Пример дневного напоминания с кнопками
        print("\n📅 ДНЕВНОЕ НАПОМИНАНИЕ (за день) с кнопками:")
        print(f"   ⏰ НАПОМИНАНИЕ ЗА ДЕНЬ!\n")
        print(f"   Завтра, {meeting_date_str}, состоится мероприятие «ПолитЗавод».\n")
        print(f"   📍 {SCHEDULE['location']}\n")
        print(f"   🎯 {SCHEDULE['format']}\n")
        print(f"   Пожалуйста, подтвердите своё участие:\n")
        print(f"   [✅ Буду!]  [❌ Не смогу]")
        
        # Пример сообщения после подтверждения
        print("\n✅ СООБЩЕНИЕ ПОСЛЕ ПОДТВЕРЖДЕНИЯ:")
        print(f"   ✅ СПАСИБО ЗА ПОДТВЕРЖДЕНИЕ!\n")
        print(f"   Ждем вас завтра!\n")
        print(f"   📍 {SCHEDULE['location']}\n")
        print(f"   ⏰ Начало в 18:00\n")
        print(f"   До встречи! 🎉")
        
        # Пример напоминания за час
        print("\n⏰ НАПОМИНАНИЕ ЗА ЧАС (только подтвердившим):")
        print(f"   ⏰ СКОРО НАЧНЕТСЯ!\n")
        print(f"   ПолитЗавод начнется через час!\n")
        print(f"   📍 {SCHEDULE['location']}\n")
        print(f"   ⏰ Начало в 18:00\n")
        print(f"   Не опаздывайте!")
        
        # Пример запроса оценки
        print("\n🌟 ЗАПРОС ОЦЕНКИ (после мероприятия):")
        print(f"   🌟 КАК ПРОШЛО МЕРОПРИЯТИЕ?\n")
        print(f"   Оцените ПолитЗавод от 1 до 5:\n")
        print(f"   [⭐ 1] [⭐⭐ 2] [⭐⭐⭐ 3] [⭐⭐⭐⭐ 4] [⭐⭐⭐⭐⭐ 5]")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def test_reminder_timing():
    """Проверка времени отправки напоминаний"""
    print_separator("ПРОВЕРКА ВРЕМЕНИ ОТПРАВКИ")
    
    now = datetime.now()
    meeting_date_str = SCHEDULE.get('next_meeting', '')
    
    print(f"🕐 Текущее время: {now.strftime('%H:%M')}")
    print(f"📅 Текущая дата: {now.strftime('%Y-%m-%d')}")
    print(f"📅 Дата мероприятия: {meeting_date_str}")
    
    print("\n📋 РАСПИСАНИЕ ОТПРАВКИ НАПОМИНАНИЙ:")
    print("   • За день до мероприятия (10:00) → отправка с кнопками")
    print("   • В день мероприятия (17:00) → только подтвердившим")
    print("   • На следующий день (21:00) → запрос оценки")
    
    # Проверка, когда будет следующее напоминание
    try:
        from reminders import ReminderSystem
        reminder = ReminderSystem(None)
        meeting_date = reminder.parse_meeting_date()
        
        if meeting_date:
            today = datetime.now().date()
            meeting_day = meeting_date.date()
            days_until = (meeting_day - today).days
            
            print(f"\n⏰ ДО МЕРОПРИЯТИЯ: {days_until} дней")
            
            if days_until == 1:
                print("   🟢 СЕГОДНЯ в 10:00 будет отправлено напоминание с кнопками!")
            elif days_until == 0:
                print("   🟢 СЕГОДНЯ в 17:00 будет отправлено напоминание подтвердившим!")
            elif days_until == -1:
                print("   🟢 СЕГОДНЯ в 21:00 будет отправлен запрос оценки!")
            else:
                print(f"   🟡 Следующее напоминание через {days_until} дней")
    except:
        pass

async def test_send_to_admin():
    """Отправить тестовое напоминание админу"""
    print_separator("ТЕСТОВАЯ ОТПРАВКА АДМИНУ")
    
    try:
        application = Application.builder().token(TOKEN).build()
        await application.initialize()
        
        print("📤 Отправляю тестовое сообщение с кнопками админу...")
        
        # Кнопки для подтверждения
        keyboard = [
            [
                InlineKeyboardButton("✅ Буду!", callback_data="confirm_attendance_yes"),
                InlineKeyboardButton("❌ Не смогу", callback_data="confirm_attendance_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        meeting_date_str = SCHEDULE.get('next_meeting', 'дата уточняется')
        
        await application.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=f"🧪 *ТЕСТОВОЕ НАПОМИНАНИЕ С ПОДТВЕРЖДЕНИЕМ*\n\n"
                 f"⏰ *НАПОМИНАНИЕ ЗА ДЕНЬ!*\n\n"
                 f"Завтра, {meeting_date_str}, состоится мероприятие «ПолитЗавод».\n\n"
                 f"📍 {SCHEDULE['location']}\n"
                 f"🎯 {SCHEDULE['format']}\n\n"
                 f"<b>Пожалуйста, подтвердите своё участие:</b>\n\n"
                 f"✅ «Буду!» — мы ждём вас\n"
                 f"❌ «Не смогу» — освободим место другому",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        print("✅ Тестовое сообщение с кнопками отправлено админу!")
        print("   Проверьте Telegram и нажмите на кнопку!")
        
        await application.shutdown()
        
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

async def show_table_stats():
    """Показать статистику из таблицы"""
    print_separator("СТАТИСТИКА ИЗ ТАБЛИЦЫ")
    
    try:
        all_users = sheets_manager.get_all_users()
        if not all_users:
            print("❌ Нет данных")
            return
        
        total = len(all_users)
        confirmed = sum(1 for u in all_users if u.get('confirmation') == 'Подтверждено')
        declined = sum(1 for u in all_users if u.get('confirmation') == 'Отказ')
        waiting = sum(1 for u in all_users if u.get('confirmation') == 'Ожидает')
        
        print(f"📊 ОБЩАЯ СТАТИСТИКА:")
        print(f"   👥 Всего участников: {total}")
        print(f"   ✅ Подтвердили участие: {confirmed}")
        print(f"   ❌ Отказались: {declined}")
        print(f"   ⏳ Ожидают ответа: {waiting}")
        
        if confirmed > 0:
            print(f"\n📋 СПИСОК ПОДТВЕРДИВШИХ:")
            for user in all_users:
                if user.get('confirmation') == 'Подтверждено':
                    print(f"   ✅ {user.get('full_name', 'Неизвестно')} - {user.get('phone', 'нет телефона')}")
        
        if waiting > 0:
            print(f"\n⏳ СПИСОК ОЖИДАЮЩИХ ОТВЕТА:")
            for user in all_users:
                if user.get('confirmation') == 'Ожидает':
                    print(f"   ⏳ {user.get('full_name', 'Неизвестно')}")
                    
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def main():
    """Главная функция тестирования"""
    print("\n" + "█"*60)
    print("     ТЕСТИРОВАНИЕ СИСТЕМЫ НАПОМИНАНИЙ И ПОДТВЕРЖДЕНИЯ")
    print("█"*60)
    
    # 1. Тест подключения
    if not await test_connection():
        print("\n❌ Невозможно продолжить тестирование")
        return
    
    # 2. Тест кнопок
    await test_confirmation_buttons()
    
    # 3. Тест напоминаний
    await test_reminder_messages()
    
    # 4. Проверка времени
    await test_reminder_timing()
    
    # 5. Статистика из таблицы
    await show_table_stats()
    
    # 6. Вопрос о реальной отправке
    print_separator("РЕАЛЬНАЯ ПРОВЕРКА")
    print("\nВыберите действие:")
    print("   1. Отправить тестовое сообщение с кнопками админу")
    print("   2. Показать статистику из таблицы")
    print("   3. Выйти")
    
    try:
        choice = input("\nВведите номер (1-3): ").strip()
        
        if choice == "1":
            await test_send_to_admin()
        elif choice == "2":
            await show_table_stats()
        elif choice == "3":
            print("👋 Выход...")
        else:
            print("❌ Неверный выбор")
            
    except KeyboardInterrupt:
        print("\n👋 Прервано пользователем")
    
    print_separator("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("\n💡 РЕЗУЛЬТАТЫ:")
    print("   • Система напоминаний с подтверждением настроена")
    print("   • Напоминания отправляются в 10:00 (за день)")
    print("   • Пользователи нажимают кнопки 'Буду' или 'Не смогу'")
    print("   • Статус сохраняется в Google Таблицу")
    print("   • В день мероприятия напоминание получают только подтвердившие")
    print("\n📊 Статусы в таблице:")
    print("   • 'Подтверждено' → придёт")
    print("   • 'Отказ' → не придёт")
    print("   • 'Ожидает' → ещё не ответил")

if __name__ == '__main__':
    asyncio.run(main())