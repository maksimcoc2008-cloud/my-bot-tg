FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы бота
COPY . .

# Запускаем бота
CMD ["python", "bot.py"]
