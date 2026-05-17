# 🚀 Быстрый старт

## 1. Первый запуск проекта (5 минут)

### Активация виртуального окружения

```bash
# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Проверка установки

```bash
python --version  # Python 3.12+
python -c "import fastapi, pandas, sklearn, xgboost, tensorflow, anthropic; print('✅ OK')"
```

## 2. Структура проекта

```
backend/         → FastAPI сервер + ML модели
frontend/        → React дашборд
data/
  ├── raw/       → Исходные данные (IEEE-CIS Fraud Detection)
  ├── processed/ → Обработанные данные + X_train.npy, y_train.npy
  └── models/    → Сохранённые модели ML
tests/           → Unit и интеграционные тесты
docs/            → Документация (архитектура, API, ML)
logs/            → Логи приложения
scripts/         → Вспомогательные скрипты
```

## 3. Переменные окружения

```bash
# Копируй .env.example в .env
cp .env.example .env

# Отредактируй критические переменные:
# - ANTHROPIC_API_KEY (Claude API для генерации данных)
# - DATABASE_URL (PostgreSQL подключение)
# - MAIN_SERVER_HOST (IP главного сервера в LAN)
```

## 4. Что дальше?

**Шаг 2** → Создание моделей БД (SQLAlchemy) и API endpoints  
**Шаг 3** → Обучение ML моделей на IEEE-CIS датасете  
**Шаг 4** → Реализация правил мошенничества и Rule Engine  
**Шаг 5** → Интеграция Claude API для генерации данных  
**Шаг 6** → Сборка React дашборда  
**Шаг 7** → WebSocket для real-time обновлений  
**Шаг 8** → Развёртывание на 3 ноутбуках

## 5. Полезные команды

```bash
# Проверить что установлено
pip list | grep -E 'fastapi|pandas|xgboost|tensorflow|anthropic'

# Обновить зависимости
pip install --upgrade -r requirements.txt

# Создать новую зависимость в requirements.txt
pip freeze > requirements.txt

# Запустить тесты
pytest tests/ -v

# Форматирование кода
black backend/

# Проверить типы
mypy backend/
```

## 6. Если что-то сломалось

```bash
# Пересоздать окружение
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Проверить зависимости
pip check
```

---

**Готово!** Проект инициализирован и готов к разработке 🎯
