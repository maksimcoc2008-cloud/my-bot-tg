FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы
COPY . .

# Делаем скрипт исполняемым
RUN chmod +x start.sh

# Запускаем с exec формой (правильно для Docker)
CMD ["./start.sh"]
