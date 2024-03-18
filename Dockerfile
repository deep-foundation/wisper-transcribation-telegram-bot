# Используем официальный образ Python 3.8
FROM python:3.10-slim

# Создаем директорию для приложения
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY main.py /app
COPY requirements.txt /app
COPY Filters.py /app
COPY custom_exceptions.py /app
COPY db.py /app
COPY openai_requests.py /app
COPY file_utils.py /app
# Устанавливаем зависимости
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Запускаем ваш скрипт
CMD ["python", "./db.py"]
CMD ["python", "./main.py"]
