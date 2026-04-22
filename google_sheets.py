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

# Отключаем прокси
import requests
session = requests.Session()
session.trust_env = False
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

logger = logging.getLogger(__name__)

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
            
            if not os.path.exists(SERVICE_ACCOUNT_FILE):
                print(f"❌ Файл {SERVICE_ACCOUNT_FILE} не найден!")
                return False
            
            self.creds = Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, 
                scopes=SCOPES
            )
            
            self.client = gspread.authorize(self.creds)
            
            if not SPREADSHEET_ID or SPREADSHEET_ID == 'ВАШ_GOOGLE_SHEET_ID':
                print("❌ GOOGLE_SHEET_ID не настроен в config.py!")
                return False
            
            self.spreadsheet = self.client.open_by_key(SPREADSHEET_ID)
            self.connected = True
            print("✅ Подключение к Google Таблицам успешно установлено")
            
            self.show_all_worksheets()
            self.create_letter_sheet()
            self.create_feedback_sheet()
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            traceback.print_exc()
            return False

    def is_connected(self):
        return self.connected

    def show_all_worksheets(self):
        try:
            if not self.connected:
                return
            worksheets = self.spreadsheet.worksheets()
            print(f"\n📋 СУЩЕСТВУЮЩИЕ ЛИСТЫ:")
            for ws in worksheets:
                print(f"   📄 {ws.title}")
            print("")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    def get_worksheet(self, sheet_name):
        try:
            if not self.connected:
                return None
            try:
                return self.spreadsheet.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                return None
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

    def create_letter_sheet(self):
        try:
            if not self.connected:
                return False
            try:
                self.spreadsheet.worksheet("Отпросительные письма")
                print("✅ Лист 'Отпросительные письма' уже существует")
                return True
            except gspread.exceptions.WorksheetNotFound:
                print("📝 Создаю лист 'Отпросительные письма'...")
                sheet = self.spreadsheet.add_worksheet("Отпросительные письма", 1000, 20)
                headers = [
                    'Дата заявки', 'ФИО директора/ректора',
                    'Полное наименование учебного заведения',
                    'Класс/курс (направление)', 'ФИО участника',
                    'Наименование мероприятия', 'Вид письма'
                ]
                sheet.append_row(headers)
                print("✅ Создан лист 'Отпросительные письма'")
                return True
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    def create_feedback_sheet(self):
        try:
            if not self.connected:
                return False
            try:
                self.spreadsheet.worksheet("Обратная связь")
                print("✅ Лист 'Обратная связь' уже существует")
                return True
            except gspread.exceptions.WorksheetNotFound:
                print("📝 Создаю лист 'Обратная связь'...")
                sheet = self.spreadsheet.add_worksheet("Обратная связь", 1000, 20)
                headers = ['Дата', 'ID пользователя', 'ФИО пользователя', 'Текст отзыва', 'Оценка']
                sheet.append_row(headers)
                print("✅ Создан лист 'Обратная связь'")
                return True
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    def save_letter_request(self, user_data):
        try:
            print("\n📄 СОХРАНЕНИЕ ЗАЯВКИ НА ОТПРОСКУ")
            if not self.connected:
                return False
            sheet = self.spreadsheet.worksheet("Отпросительные письма")
            letter_info = user_data.get('letter_info', '')
            if not letter_info:
                return False
            info_parts = [p.strip() for p in letter_info.split(',')]
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                info_parts[0] if len(info_parts) > 0 else '',
                info_parts[1] if len(info_parts) > 1 else '',
                info_parts[2] if len(info_parts) > 2 else '',
                info_parts[3] if len(info_parts) > 3 else user_data.get('full_name', ''),
                info_parts[4] if len(info_parts) > 4 else 'ПолитЗавод',
                info_parts[5] if len(info_parts) > 5 else ''
            ]
            sheet.append_row(row)
            print("✅ ЗАЯВКА СОХРАНЕНА")
            return True
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    def save_feedback(self, user_id, feedback_text, rating):
        try:
            print("\n📝 СОХРАНЕНИЕ ОБРАТНОЙ СВЯЗИ")
            if not self.connected:
                return False
            sheet = self.spreadsheet.worksheet("Обратная связь")
            user_name = ""
            try:
                main_sheet = self.spreadsheet.worksheet("Лист1")
                all_data = main_sheet.get_all_values()
                for row in all_data:
                    if len(row) > 7 and str(row[7]) == str(user_id):
                        user_name = row[1] if len(row) > 1 else ""
                        break
            except:
                pass
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                str(user_id), user_name, feedback_text, str(rating)
            ]
            sheet.append_row(row)
            print("✅ ОБРАТНАЯ СВЯЗЬ СОХРАНЕНА")
            return True
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    def register_user(self, user_data):
        try:
            print(f"\n🔧 РЕГИСТРАЦИЯ {user_data.get('user_id')}")
            if not self.connected:
                return False
            sheet = self.spreadsheet.worksheet("Лист1")
            headers = sheet.row_values(1)
            if not headers or len(headers) < 11:
                new_headers = [
                    'Дата регистрации', 'ФИО', 'Уч. заведение',
                    'Специальность', 'Курс', 'Номер телефона',
                    'Наличие отпроски', 'Telegram user_id пользователя',
                    'Имя пользователя', 'Дата запланированных дебатов',
                    'Статус подтверждения участия'
                ]
                sheet.clear()
                sheet.append_row(new_headers)
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_data.get('full_name', ''),
                user_data.get('university', ''),
                user_data.get('specialty', ''),
                user_data.get('course', ''),
                user_data.get('phone', ''),
                user_data.get('need_letter', 'Нет'),
                str(user_data.get('user_id', '')),
                user_data.get('username', ''),
                user_data.get('debate_date', ''),
                user_data.get('confirmation', 'Ожидает')
            ]
            sheet.append_row(row)
            print("✅ ПОЛЬЗОВАТЕЛЬ ЗАРЕГИСТРИРОВАН")
            if user_data.get('need_letter') == 'Да':
                self.save_letter_request(user_data)
            return True
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    def update_user(self, user_data):
        try:
            print(f"🔄 ОБНОВЛЕНИЕ {user_data.get('user_id')}")
            if not self.connected:
                return False
            sheet = self.spreadsheet.worksheet("Лист1")
            row_num = self.find_user_row(user_data.get('user_id'))
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_data.get('full_name', ''),
                user_data.get('university', ''),
                user_data.get('specialty', ''),
                user_data.get('course', ''),
                user_data.get('phone', ''),
                user_data.get('need_letter', 'Нет'),
                str(user_data.get('user_id', '')),
                user_data.get('username', ''),
                user_data.get('debate_date', ''),
                user_data.get('confirmation', 'Ожидает')
            ]
            if row_num:
                for col, val in enumerate(row, 1):
                    sheet.update_cell(row_num, col, val)
            else:
                sheet.append_row(row)
            if user_data.get('need_letter') == 'Да':
                self.save_letter_request(user_data)
            return True
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    def find_user_row(self, user_id):
        try:
            if not self.connected:
                return None
            sheet = self.spreadsheet.worksheet("Лист1")
            all_data = sheet.get_all_values()
            for i, row in enumerate(all_data):
                if i == 0:
                    continue
                if len(row) > 7 and str(row[7]) == str(user_id):
                    return i + 1
            return None
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

    def is_user_registered(self, user_id):
        try:
            if not self.connected:
                return False
            sheet = self.spreadsheet.worksheet("Лист1")
            all_data = sheet.get_all_values()
            for row in all_data[1:]:
                if len(row) > 7 and str(row[7]) == str(user_id):
                    return True
            return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    def delete_user(self, user_id):
        try:
            if not self.connected:
                return False
            sheet = self.spreadsheet.worksheet("Лист1")
            all_data = sheet.get_all_values()
            for i, row in enumerate(all_data):
                if i == 0:
                    continue
                if len(row) > 7 and str(row[7]) == str(user_id):
                    sheet.delete_rows(i + 1)
                    print(f"✅ Пользователь {user_id} удален")
                    return True
            return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    def get_all_users(self):
        try:
            if not self.connected:
                return []
            sheet = self.spreadsheet.worksheet("Лист1")
            data = sheet.get_all_records()
            formatted = []
            for r in data:
                formatted.append({
                    'date': r.get('Дата регистрации', ''),
                    'full_name': r.get('ФИО', ''),
                    'university': r.get('Уч. заведение', ''),
                    'specialty': r.get('Специальность', ''),
                    'course': r.get('Курс', ''),
                    'phone': r.get('Номер телефона', ''),
                    'need_letter': r.get('Наличие отпроски', ''),
                    'user_id': str(r.get('Telegram user_id пользователя', '')),
                    'username': r.get('Имя пользователя', ''),
                    'debate_date': r.get('Дата запланированных дебатов', ''),
                    'confirmation': r.get('Статус подтверждения участия', '')
                })
            return formatted
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return []

    def get_letter_requests(self):
        try:
            if not self.connected:
                return []
            sheet = self.spreadsheet.worksheet("Отпросительные письма")
            return sheet.get_all_records()
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return []

    def get_feedback_stats(self):
        try:
            if not self.connected:
                return None
            sheet = self.spreadsheet.worksheet("Обратная связь")
            all_data = sheet.get_all_values()
            if len(all_data) <= 1:
                return None
            ratings = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            total = 0
            sum_ratings = 0
            recent = []
            for row in all_data[1:]:
                if len(row) > 4:
                    try:
                        rating = int(row[4])
                        if rating in ratings:
                            ratings[rating] += 1
                            total += 1
                            sum_ratings += rating
                            if len(recent) < 5:
                                name = row[2] if len(row) > 2 else "Неизвестно"
                                date = row[0][:10] if len(row) > 0 else ""
                                recent.append({'name': name, 'rating': rating, 'date': date})
                    except:
                        pass
            if total == 0:
                return None
            return {
                'total': total,
                'average': sum_ratings / total,
                'ratings': ratings,
                'recent': recent
            }
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

    def update_confirmation(self, user_id, status):
        try:
            if not self.connected:
                return False
            sheet = self.spreadsheet.worksheet("Лист1")
            all_data = sheet.get_all_values()
            for i, row in enumerate(all_data):
                if i == 0:
                    continue
                if len(row) > 7 and str(row[7]) == str(user_id):
                    sheet.update_cell(i + 1, 11, status)
                    return True
            return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

sheets_manager = GoogleSheetsManager()