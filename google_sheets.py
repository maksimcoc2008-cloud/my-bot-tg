"""
МОДУЛЬ ДЛЯ РАБОТЫ С GOOGLE ТАБЛИЦАМИ
"""

import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID as SPREADSHEET_ID
import logging
import os
import traceback

logger = logging.getLogger(__name__)

# Настройка доступа к Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'

class GoogleSheetsManager:
    def __init__(self):
        self.creds = None
        self.client = None
        self.spreadsheet = None
        self.connected = False
        
    def connect(self):
        """Подключение к Google Таблицам"""
        try:
            print("🔄 Подключаюсь к Google Таблицам...")
            
            # Проверяем наличие файла с ключами
            if not os.path.exists(SERVICE_ACCOUNT_FILE):
                print(f"❌ Файл {SERVICE_ACCOUNT_FILE} не найден!")
                print("   Создайте файл credentials.json с ключами сервисного аккаунта")
                return False
            
            # Создаем учетные данные
            self.creds = Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, 
                scopes=SCOPES
            )
            
            # Авторизуемся
            self.client = gspread.authorize(self.creds)
            
            # Открываем таблицу
            if not SPREADSHEET_ID or SPREADSHEET_ID == 'ВАШ_GOOGLE_SHEET_ID':
                print("❌ GOOGLE_SHEET_ID не настроен в config.py!")
                return False
            
            self.spreadsheet = self.client.open_by_key(SPREADSHEET_ID)
            
            # Проверяем существование основного листа
            try:
                worksheet = self.spreadsheet.worksheet("Лист1")
                print("✅ Основной лист найден")
            except gspread.exceptions.WorksheetNotFound:
                print("ℹ️ Лист 'Лист1' не найден, будет создан автоматически")
            
            self.connected = True
            print("✅ Подключение к Google Таблицам успешно установлено")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка подключения к Google Таблицам: {e}")
            traceback.print_exc()
            return False

    def is_connected(self):
        """Проверка состояния подключения"""
        return self.connected

    def get_worksheet(self, sheet_name="Лист1"):
        """Получение рабочего листа (создает при необходимости)"""
        try:
            if not self.connected:
                print("⚠️ Нет подключения к Google Таблицам")
                return None
            
            try:
                # Пытаемся получить существующий лист
                worksheet = self.spreadsheet.worksheet(sheet_name)
                print(f"✅ Лист '{sheet_name}' получен")
                return worksheet
                
            except gspread.exceptions.WorksheetNotFound:
                # Создаем новый лист
                print(f"📝 Создаю новый лист '{sheet_name}'...")
                worksheet = self.spreadsheet.add_worksheet(
                    title=sheet_name, 
                    rows=1000, 
                    cols=20
                )
                
                # Если это основной лист для регистрации, добавляем заголовки
                if sheet_name == "Лист1":
                    headers = [
                        'Дата регистрации', 'ФИО', 'Уч. заведение', 
                        'Специальность', 'Курс', 'Номер телефона', 'Telegram ID',
                        'ID пользователя', 'Username', 'Дата дебатов',
                        'Подтверждение', 'Дедлайн подтверждения'
                    ]
                    worksheet.append_row(headers)
                    print(f"✅ Добавлены заголовки: {headers}")
                
                print(f"✅ Лист '{sheet_name}' создан")
                return worksheet
                
        except Exception as e:
            print(f"❌ Ошибка получения листа '{sheet_name}': {e}")
            return None

    def register_user(self, user_data):
        """Регистрация пользователя в таблице"""
        try:
            print(f"\n🔧 Начинаю сохранение пользователя {user_data.get('user_id')}")
            print(f"📊 Полученные данные: {user_data}")
            
            if not self.connected:
                print("❌ Нет подключения к Google Таблицам")
                return False
            
            # Получаем основной лист
            sheet = self.get_worksheet("Лист1")
            if not sheet:
                print("❌ Не удалось получить доступ к листу")
                return False
            
            # Проверяем заголовки
            headers = sheet.row_values(1)
            print(f"📝 Заголовки в таблице: {headers}")
            
            # Если таблица почти пустая, добавляем заголовки
            if not headers or len(headers) < 3:
                new_headers = [
                    'Дата регистрации', 'ФИО', 'Уч. заведение', 
                    'Специальность', 'Курс', 'Номер телефона', 'Telegram ID',
                    'ID пользователя', 'Username', 'Дата дебатов',
                    'Подтверждение', 'Дедлайн подтверждения'
                ]
                sheet.clear()
                sheet.append_row(new_headers)
                print(f"✅ Установлены новые заголовки: {new_headers}")
            
            # Формируем строку данных
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Дата регистрации
                user_data.get('full_name', ''),               # ФИО
                user_data.get('university', ''),              # Уч. заведение
                user_data.get('specialty', ''),               # Специальность
                user_data.get('course', ''),                  # Курс
                user_data.get('phone', ''),                   # Номер телефона
                user_data.get('tg_username', ''),             # Telegram ID
                str(user_data.get('user_id', '')),            # ID пользователя
                user_data.get('username', ''),                # Username
                user_data.get('debate_date', ''),             # Дата дебатов
                user_data.get('confirmation', 'Ожидает'),     # Подтверждение
                user_data.get('confirmation_deadline', '')    # Дедлайн подтверждения
            ]
            
            print(f"📝 Сохраняемая строка: {row}")
            
            # Добавляем строку в таблицу
            sheet.append_row(row)
            
            # Проверяем, что данные сохранились
            all_data = sheet.get_all_values()
            last_row = all_data[-1] if all_data else []
            
            print(f"✅ Данные сохранены! Всего строк: {len(all_data)}")
            print(f"📋 Последняя сохраненная строка: {last_row}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при сохранении пользователя: {e}")
            traceback.print_exc()
            return False

    def get_all_users(self):
        """Получение всех пользователей"""
        try:
            if not self.connected:
                print("⚠️ Нет подключения к Google Таблицам")
                return []
            
            sheet = self.get_worksheet("Лист1")
            if not sheet:
                return []
            
            # Получаем данные
            data = sheet.get_all_records()
            print(f"📋 Получено {len(data)} записей из таблицы")
            
            return data
            
        except Exception as e:
            print(f"❌ Ошибка получения пользователей: {e}")
            return []

    def update_confirmation(self, user_id, confirmation):
        """Обновление подтверждения участия"""
        try:
            if not self.connected:
                return False
            
            sheet = self.get_worksheet("Лист1")
            if not sheet:
                return False
            
            # Находим пользователя по ID
            cell = sheet.find(str(user_id))
            if cell:
                # Обновляем статус подтверждения (колонка K, 11-я колонка)
                sheet.update_cell(cell.row, 11, confirmation)
                print(f"✅ Подтверждение для {user_id} обновлено: {confirmation}")
                return True
            else:
                print(f"⚠️ Пользователь {user_id} не найден в таблице")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка обновления подтверждения: {e}")
            return False
    def update_confirmation(self, user_id, confirmation_status):
        """Обновление статуса подтверждения в таблице"""
        try:
            if not self.connected:
                return False
            
            sheet = self.get_worksheet("Лист1")
            if not sheet:
                return False
            
            # Получаем все данные
            all_data = sheet.get_all_values()
            
            # Ищем пользователя по ID (колонка H, индекс 7)
            for i, row in enumerate(all_data):
                if len(row) > 7 and str(row[7]) == str(user_id):
                    # Обновляем статус в колонке K (индекс 10)
                    sheet.update_cell(i + 1, 11, confirmation_status)
                    print(f"✅ Подтверждение для {user_id} обновлено на '{confirmation_status}'")
                    
                    # Если подтвердил, сохраняем время
                    if confirmation_status == "Подтверждено":
                        sheet.update_cell(i + 1, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    
                    return True
            
            print(f"❌ Пользователь {user_id} не найден")
            return False
            
        except Exception as e:
            print(f"❌ Ошибка обновления подтверждения: {e}")
            return False

    def save_feedback(self, user_id, feedback_text, rating):
        """Сохранение обратной связи"""
        try:
            if not self.connected:
                return False
            
            # Получаем или создаем лист для обратной связи
            sheet = self.get_worksheet("Обратная связь")
            if not sheet:
                return False
            
            # Проверяем заголовки
            headers = sheet.row_values(1)
            if not headers or len(headers) < 3:
                new_headers = [
                    'Дата', 'ID пользователя', 'Текст отзыва', 
                    'Оценка', 'Статус'
                ]
                sheet.clear()
                sheet.append_row(new_headers)
            
            # Формируем строку
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [
                timestamp,
                str(user_id),
                feedback_text,
                str(rating),
                'Новый'
            ]
            
            # Сохраняем
            sheet.append_row(row)
            print(f"✅ Обратная связь от {user_id} сохранена")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения обратной связи: {e}")
            return False

    def save_survey(self, user_id, answers):
        """Сохранение результатов опроса"""
        try:
            if not self.connected:
                return False
            
            # Получаем или создаем лист для опросов
            sheet = self.get_worksheet("Опросы")
            if not sheet:
                return False
            
            # Проверяем заголовки
            headers = sheet.row_values(1)
            if not headers or len(headers) < 3:
                new_headers = ['Дата', 'ID пользователя', 'Ответы']
                sheet.clear()
                sheet.append_row(new_headers)
            
            # Формируем строку
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Преобразуем список ответов в строку
            if isinstance(answers, list):
                answers_str = " | ".join([str(a) for a in answers])
            else:
                answers_str = str(answers)
            
            row = [timestamp, str(user_id), answers_str]
            
            # Сохраняем
            sheet.append_row(row)
            print(f"✅ Опрос от {user_id} сохранен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения опроса: {e}")
            return False

    def get_pending_confirmations(self):
        """Получение списка ожидающих подтверждения"""
        try:
            if not self.connected:
                return []
            
            users = self.get_all_users()
            pending = []
            
            for user in users:
                if user.get('Подтверждение') == 'Ожидает':
                    pending.append(user)
            
            print(f"📊 Найдено {len(pending)} ожидающих подтверждения")
            return pending
            
        except Exception as e:
            print(f"❌ Ошибка получения ожидающих подтверждения: {e}")
            return []

# Глобальный экземпляр менеджера
sheets_manager = GoogleSheetsManager()