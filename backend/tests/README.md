# Тестирование Books Portal

## Подготовка к тестированию

1. Убедитесь, что у вас установлен Poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Активируйте виртуальное окружение:
```bash
poetry shell
```

3. Установите зависимости:
```bash
poetry install
```

4. Создайте тестовую базу данных PostgreSQL:
```sql
CREATE DATABASE books_portal_test;
```

## Запуск тестов

### Модульные и интеграционные тесты

Для запуска всех тестов с отчетом о покрытии:
```bash
pytest --cov=app tests/ --cov-report=term-missing
```

Для запуска конкретных тестов:
```bash
# Тесты моделей
pytest tests/test_models.py

# Тесты API
pytest tests/test_api.py

# Тесты безопасности
pytest tests/test_security.py
```

### Нагрузочное тестирование

1. Установите Locust:
```bash
poetry add locust
```

2. Запустите тестовый сервер:
```bash
uvicorn app.main:app --reload
```

3. В отдельном терминале запустите Locust:
```bash
locust -f tests/locustfile.py
```

4. Откройте веб-интерфейс Locust по адресу http://localhost:8089

5. Настройте параметры тестирования:
   - Number of users: 100
   - Spawn rate: 10
   - Host: http://localhost:8000

6. Запустите тест и наблюдайте за метриками

## Критерии успешного тестирования

### Модульные тесты
- Покрытие кода тестами ≥ 90%
- Все тесты проходят успешно
- Нет критических уязвимостей

### Интеграционные тесты
- Все API эндпоинты работают корректно
- Правильная обработка ошибок
- Корректная валидация данных

### Нагрузочное тестирование
- Сервер выдерживает нагрузку 100 RPS
- Время отклика ≤ 500 мс для 95% запросов
- Отсутствие утечек памяти
- Отсутствие ошибок под нагрузкой

### Тестирование безопасности
- Защита от SQL-инъекций
- Корректная работа CORS
- Защита от CSRF-атак
- Безопасное хранение паролей
- Корректная работа JWT-токенов
