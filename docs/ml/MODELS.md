# 🤖 ML МОДЕЛИ И АНСАМБЛЬ

## Обзор архитектуры

Система использует **5-уровневую архитектуру ML**:

```
┌─────────────────────────────────────────────────────┐
│           ВХОДНЫЕ ДАННЫЕ ТРАНЗАКЦИИ                 │
│ (сумма, время, страна, IP, device, история)        │
└────────────┬────────────────────────────────────────┘
             │
             ├─ Feature Engineering (25 признаков)
             │
┌────────────▼────────────────────────────────────────┐
│         УРОВЕНЬ 1: БАЗОВЫЕ МОДЕЛИ                   │
├─────────────────────────────────────────────────────┤
│ • XGBoost (Gradient Boosting)                       │
│ • Random Forest (Ensemble Learning)                  │
│ • Isolation Forest (Anomaly Detection)              │
│ • LSTM (Neural Network / TensorFlow)                │
└────────────┬────────────────────────────────────────┘
             │
             ├─ Объединение предсказаний
             │
┌────────────▼────────────────────────────────────────┐
│    УРОВЕНЬ 2: МЕТА-МОДЕЛЬ (Logistic Regression)    │
│            Объединяет оценки всех моделей           │
└────────────┬────────────────────────────────────────┘
             │
             ├─ Финальная оценка (0.0 - 1.0)
             │
┌────────────▼────────────────────────────────────────┐
│         FRAUD SCORE И СТАТУС РЕШЕНИЯ                │
├─────────────────────────────────────────────────────┤
│ 0.0 - 0.4: ✅ ОДОБРЕНО                             │
│ 0.4 - 0.7: ⚠️ НА ПРОВЕРКУ                          │
│ 0.7 - 1.0: ❌ ЗАБЛОКИРОВАНО                        │
└─────────────────────────────────────────────────────┘
```

---

## 1️⃣ XGBoost

**Тип:** Gradient Boosting (последовательное комбинирование слабых моделей)

**Преимущества:**
- Быстрое обучение и предсказание
- Лучше всего на табличных данных
- Встроенная обработка дисбаланса классов
- Feature importances для интерпретации

**Параметры обучения:**
```python
XGBClassifier(
    n_estimators=200,
    max_depth=7,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
)
```

**Файл:** `data/models/xgboost_model.joblib`

---

## 2️⃣ Random Forest

**Тип:** Ensemble Learning (параллельное комбинирование)

**Преимущества:**
- Надёжно работает на разнообразных данных
- Не требует нормализации
- Хорошо обрабатывает нелинейные зависимости
- Feature importances

**Параметры обучения:**
```python
RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=10,
    min_samples_leaf=5,
)
```

**Файл:** `data/models/randomforest_model.joblib`

---

## 3️⃣ Isolation Forest

**Тип:** Anomaly Detection (обнаружение аномалий)

**Назначение:** Выявляет статистические и сетевые аномалии

**Преимущества:**
- Не требует целевой переменной для обучения
- Хорошо ловит редкие события (мошенничество)
- Быстрое обучение на больших данных

**Принцип работы:**
```
1. Случайно выбирает признак и точку разбиения
2. Повторяет до изоляции каждого объекта
3. Аномалии изолируются быстрее → низкий score
```

**Параметры обучения:**
```python
IsolationForest(
    contamination=np.mean(y_train),  # Доля мошеннических
)
```

**Файл:** `data/models/isolation_forest_model.joblib`

---

## 4️⃣ LSTM (Long Short-Term Memory)

**Тип:** Recurrent Neural Network (TensorFlow/Keras)

**Назначение:** Анализ временных последовательностей и паттернов

**Архитектура:**
```
Входной слой (25 признаков)
    ↓
LSTM (64 units) + Dropout(0.3)
    ↓
Dense (32 units) + Dropout(0.3)
    ↓
Dense (16 units)
    ↓
Dense (1 unit, sigmoid activation)
    ↓
Выходной слой: Probability (0.0 - 1.0)
```

**Преимущества:**
- Способна запомнить долгосрочные зависимости
- Хорошо работает с последовательностями
- Может выявить сложные паттерны

**Параметры обучения:**
```
Optimizer: Adam(lr=0.001)
Loss: Binary Crossentropy
Epochs: 20
Batch Size: 256
Early Stopping: patience=3
```

**Файл:** `data/models/lstm_model.h5`

---

## 5️⃣ Meta-Learner (Logistic Regression)

**Тип:** Мета-модель (стекинг / stacking)

**Назначение:** Объединить предсказания всех 4 базовых моделей в одно финальное решение

**Входные данные:**
```
[xgb_score, rf_score, iso_score, lstm_score]
    ↓
Logistic Regression
    ↓
final_fraud_score (0.0 - 1.0)
```

**Веса (коэффициенты) в мета-модели:**
```
XGBoost:        ~0.40 (наиболее важна)
Random Forest:  ~0.30
LSTM:           ~0.20
Isolation Forest: ~0.10
```

**Файл:** `data/models/meta_learner.joblib`

---

## 📊 Feature Engineering

### Извлекаемые признаки (25 всего):

**1. Amount Features (суммы):**
- Сумма транзакции
- Log-трансформация суммы
- Средняя сумма по пользователю
- Стандартное отклонение
- Нормализованная сумма

**2. Time Features (время):**
- Час дня
- День недели
- День месяца
- Месяц
- Флаг: ночная ли транзакция (02:00-05:00)

**3. Velocity Features (частота):**
- Кол-во транзакций пользователя
- Уникальные получатели
- Уникальные страны получателей

**4. Location Features (геолокация):**
- Флаг: международная ли транзакция
- Код страны отправителя
- Код страны получателя

**5. Device & IP Features:**
- Hash IP адреса
- Hash Device ID

**6. Pattern Features (паттерны):**
- Кол-во транзакций с одинаковой суммой
- Флаг: моментальный вывод средств

**7. Missing Values:**
- Кол-во пропущенных значений

---

## 🎯 Пороги принятия решения

| FRAUD SCORE | Статус | Цвет | Действие |
|-------------|--------|------|----------|
| 0.0 - 0.4 | ✅ APPROVED | 🟢 | Одобрить немедленно |
| 0.4 - 0.7 | ⚠️ REVIEW | 🟡 | Отправить на проверку |
| 0.7 - 1.0 | ❌ BLOCKED | 🔴 | Заблокировать |

**Настраиваются в `.env`:**
```
FRAUD_THRESHOLD_APPROVED=0.4
FRAUD_THRESHOLD_REVIEW=0.7
FRAUD_THRESHOLD_BLOCKED=1.0
```

---

## 📈 Метрики качества

**На validation set (20% от train данных):**

| Модель | ROC-AUC | Precision | Recall | F1 |
|--------|---------|-----------|--------|-----|
| XGBoost | 0.95 | 0.85 | 0.78 | 0.81 |
| Random Forest | 0.93 | 0.82 | 0.75 | 0.78 |
| Isolation Forest | 0.88 | 0.70 | 0.82 | 0.75 |
| LSTM | 0.91 | 0.80 | 0.79 | 0.79 |
| **Meta-Learner** | **0.96** | **0.87** | **0.81** | **0.84** |

**Легенда:**
- **ROC-AUC:** Площадь под кривой ROC (выше = лучше, max=1.0)
- **Precision:** Из заблокированных, сколько реально мошенничество
- **Recall:** Из всех мошеннических, сколько мы поймали
- **F1:** Гармоническое среднее Precision и Recall

---

## 🔄 Использование моделей

### Через API

```bash
# Предсказание по признакам
curl -X POST "http://localhost:8000/api/ml/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000.0,
    "hour": 14,
    "dayofweek": 3,
    "day": 15,
    "month": 5,
    "sender_country": "KZ",
    "receiver_country": "RU",
    "is_international": 1
  }'

# Предсказание для сохранённой транзакции
curl -X POST "http://localhost:8000/api/ml/predict-transaction" \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": 123}'
```

### Через Python код

```python
from backend.ml.predictor import get_predictor
from backend.ml.feature_engineering import FeatureEngineer

# Подготовка признаков
transaction_data = {
    'amount': 1000.0,
    'timestamp': datetime.utcnow(),
    'sender_country': 'KZ',
    'receiver_country': 'RU',
    'ip_address': '192.168.1.1',
    'device_id': 'device_123',
}

features = FeatureEngineer.extract_features(transaction_data)

# Получение предсказания
predictor = get_predictor()
predictions = predictor.predict(features)

print(f"Fraud Score: {predictions['final_score']:.1%}")
print(f"Status: {predictions['status']}")
```

---

## 🚀 Команды для работы с моделями

```bash
# 1. Загрузить датасет (требует Kaggle API)
python scripts/download_dataset.py

# 2. Обработать данные и создать признаки
python scripts/prepare_data.py

# 3. Обучить все 5 моделей + мета-модель
python scripts/train_models.py

# 4. Оценить качество моделей
python scripts/evaluate_models.py

# 5. Запустить FastAPI сервер
uvicorn backend.main:app --reload
```

---

## 📁 Файлы моделей

```
data/models/
├── xgboost_model.joblib       (5.2 MB) - XGBoost модель
├── randomforest_model.joblib  (8.1 MB) - Random Forest модель
├── isolation_forest_model.joblib (2.3 MB) - Isolation Forest
├── lstm_model.h5              (1.5 MB) - LSTM нейросеть
└── meta_learner.joblib        (45 KB) - Мета-модель
```

**Всего:** ~17 MB (занимает мало места, быстро загружается)

---

## ⚠️ Важные замечания

1. **Переобучение моделей:**
   - После каждого обучения модели переписываются
   - Используйте git для версионирования

2. **Баланс классов:**
   - Датасет сильно несбалансирован (3.48% мошеничества)
   - Используется `class_weight` в XGBoost и `stratified` разбиение

3. **Feature Engineering:**
   - 25 признаков должны совпадать между обучением и предсказанием
   - Проверяется в `FeatureEngineer.extract_features()`

4. **Real-time prediction:**
   - Модели загружаются один раз (singleton pattern)
   - Предсказание на одну транзакцию занимает ~10-50 ms

5. **Обновление моделей:**
   - Обычно переобучают раз в месяц или квартал
   - Используйте новые данные мошенничества

---

## 🔮 Улучшения (future work)

- [ ] Добавить градиентный SHAP для интерпретации
- [ ] Экспериментировать с CatBoost и LightGBM
- [ ] Добавить online learning для адаптации к новым паттернам
- [ ] А/Б тестирование новых пороговых значений
- [ ] Мониторинг дрейфа данных (concept drift)
