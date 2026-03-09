import gspread
from google.oauth2.service_account import Credentials

print("="*50)
print("ТЕСТ ПОДКЛЮЧЕНИЯ К GOOGLE TABLES")
print("="*50)

# ID вашей таблицы
SPREADSHEET_ID = "1-GJftqqLMLDKn6qVHVanAHRn_cTmcn2rXipm8o7TC2Q"

try:
    # 1. Проверяем наличие файла credentials.json
    import os
    if not os.path.exists('credentials.json'):
        print("❌ Файл credentials.json НЕ НАЙДЕН!")
        print("📁 Текущая папка:", os.getcwd())
        print("📄 Файлы в папке:")
        for file in os.listdir('.'):
            print(f"   - {file}")
    else:
        print("✅ Файл credentials.json найден")
        
        # 2. Пробуем загрузить credentials
        print("\n🔄 Загружаем credentials...")
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)
        print("✅ Credentials загружены")
        
        # 3. Пробуем авторизоваться
        print("\n🔄 Авторизуемся в Google...")
        client = gspread.authorize(creds)
        print("✅ Авторизация успешна")
        
        # 4. Пробуем открыть таблицу
        print(f"\n🔄 Открываем таблицу с ID: {SPREADSHEET_ID}")
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"✅ Таблица открыта: '{spreadsheet.title}'")
        
        # 5. Проверяем листы
        print("\n📋 Доступные листы:")
        for sheet in spreadsheet.worksheets():
            print(f"   📄 {sheet.title}")
            
        print("\n🎉 ВСЕ РАБОТАЕТ! Google таблицы подключены успешно!")
        
except Exception as e:
    print(f"\n❌ ОШИБКА: {e}")
    print("\n🔍 Возможные причины:")
    print("1. Неправильный ID таблицы")
    print("2. Нет доступа у сервисного аккаунта к таблице")
    print("3. Проблемы с интернетом")
    print("4. Файл credentials.json поврежден")