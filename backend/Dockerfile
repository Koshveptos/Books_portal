# Создайте новый файл Dockerfile в backend/
FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем весь backend проект
COPY . .

# Установка poetry и исправление psycopg2
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    sed -i 's/psycopg2 (>=2.9.10,<3.0.0)/psycopg2-binary (>=2.9.10,<3.0.0)/g' pyproject.toml && \
    poetry install

EXPOSE 8000

# Установка переменной среды PYTHONPATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]