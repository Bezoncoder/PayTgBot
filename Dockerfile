FROM python:3.12-slim

# Рабочая директория внутри контейнера
WORKDIR /telegram_bot

# Копируем зависимости
COPY telegram_bot/requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бота
COPY telegram_bot/ .

# Команда запуска
CMD ["python", "paybot.py"]