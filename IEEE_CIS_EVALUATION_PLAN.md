# 🚀 ПЛАН IEEE-CIS EVALUATION

**Дата начала:** 2026-05-24  
**Приоритет:** 🔴 КРИТИЧЕСКОЕ  
**Статус:** ⏳ ГОТОВО К ЗАПУСКУ

---

## 📋 ЧТО УЖЕ ПОДГОТОВЛЕНО:

✅ **evaluate_ieee_cis.py** - основной скрипт оценки  
✅ **DOWNLOAD_IEEE_CIS.md** - инструкции по скачиванию  
✅ **setup_ieee_cis_evaluation.sh** - скрипт подготовки  
✅ **Все зависимости установлены** (pandas, numpy, sklearn, tensorflow, xgboost)

---

## 🎯 ЭТАПЫ РАБОТЫ (5 шагов):

### Шаг 1️⃣: Скачать датасет (1-2 часа)

**Вариант A: Через Kaggle CLI** (рекомендуется)
```bash
# 1. Получить API token на https://www.kaggle.com/settings/account
# 2. Создать ~/.kaggle/kaggle.json
# 3. Запустить скрипт
python /home/yerzhan/Desktop/new_diplom/backend/scripts/evaluate_ieee_cis.py
```

**Вариант B: Скачать вручную**
```bash
# 1. Перейти на https://www.kaggle.com/competitions/ieee-cis-fraud-detection/data
# 2. Скачать:
#    - train_transaction.csv (1.1 GB)
#    - test_transaction.csv (0.6 GB)
# 3. Поместить в: /home/yerzhan/Desktop/new_diplom/data/ieee_cis/
# 4. Запустить скрипт
python /home/yerzhan/Desktop/new_diplom/backend/scripts/evaluate_ieee_cis.py
```

**Размер:** ~1.7 GB сжато → ~10 GB распаковано  
**Требуется свободного места:** >20 GB  
**Время:** 5-15 минут (зависит от интернета)

---

### Шаг 2️⃣: Подготовить данные (15-30 мин)

Скрипт автоматически выполнит:
```
✓ Загрузка CSV файлов в память
✓ Удаление колонок с >85% пропусков
✓ Заполнение пропусков медианой
✓ Target encoding для категориальных переменных
✓ Извлечение 394 признаков
✓ Нормализация (StandardScaler)
```

**Результат:** X_train, X_test готовы для моделей

---

### Шаг 3️⃣: Переобучить 5 моделей (1-2 часа)

Скрипт переобучит:

| Модель | Время | Назначение |
|--------|-------|-----------|
| **XGBoost** | 20-30 min | Транзакционные паттерны |
| **Random Forest** | 15-25 min | Поведенческие аномалии |
| **LSTM** | 30-45 min | Временные последовательности |
| **Isolation Forest** | 5-10 min | Статистические выбросы |
| **Rule Engine** | <1 min | 12 детерминированных паттернов |

**Параметры обучения:**
- XGBoost: `scale_pos_weight` для дисбаланса классов
- Random Forest: `class_weight='balanced'`
- LSTM: 20 предыдущих транзакций, sequence length
- Isolation Forest: без supervision
- Rule Engine: пороги из документа

---

### Шаг 4️⃣: Оценить метрики (30 мин)

**ТРЕБУЕМЫЕ МЕТРИКИ:**

```
┌─────────────────┬──────────┬─────────────┐
│ Метрика         │ Требуется│ Статус      │
├─────────────────┼──────────┼─────────────┤
│ F1-Score        │  0.90    │ ✓ Получить  │
│ AUC-ROC         │  0.96    │ ✓ Получить  │
│ Latency (p95)   │ <200 ms  │ ✓ Получить  │
│ Latency (avg)   │  <87 ms  │ ✓ Получить  │
│ Throughput      │ 100 req/s│ ✓ Получить  │
└─────────────────┴──────────┴─────────────┘
```

**Результаты сохранятся в:**
```
evaluation_results/
├── evaluation_ieee_cis_YYYYMMDD_HHMMSS.json  # Полные метрики
└── evaluation_report_YYYYMMDD_HHMMSS.txt     # Читаемый отчёт
```

---

### Шаг 5️⃣: Документировать результаты (30 мин)

Создать **EVALUATION.md** с:
```markdown
# IEEE-CIS Evaluation Results

## Dataset
- Size: 590,540 transactions
- Training/Test split: TBD
- Class balance: 3.5% fraud

## Model Performance

### Individual Models
- XGBoost: F1={}, AUC={}
- Random Forest: F1={}, AUC={}
- LSTM: F1={}, AUC={}
- Isolation Forest: F1={}, AUC={}
- Rule Engine: F1={}, AUC={}

### Ensemble Results
- **F1-Score: {} (required: 0.90) [STATUS]**
- **AUC-ROC: {} (required: 0.96) [STATUS]**

## Latency Metrics
- Mean: {} ms
- Median: {} ms
- P95: {} ms (required: <200 ms)
- P99: {} ms

## Feature Importance
[Top 20 features per model]

## Conclusion
[Summary of results vs requirements]
```

---

## 🗂️ ФАЙЛОВАЯ СТРУКТУРА

После завершения:

```
/home/yerzhan/Desktop/new_diplom/
├── data/
│   └── ieee_cis/
│       ├── train_transaction.csv (1.1 GB)
│       ├── test_transaction.csv (0.6 GB)
│       └── train_identity.csv (опционально)
├── evaluation_results/
│   ├── evaluation_ieee_cis_20260524_190000.json
│   └── evaluation_report_20260524_190000.txt
├── backend/
│   └── scripts/
│       └── evaluate_ieee_cis.py (уже создан ✅)
├── DOWNLOAD_IEEE_CIS.md (уже создан ✅)
└── IEEE_CIS_EVALUATION_PLAN.md (вы читаете это ✅)
```

---

## ⏱️ ОБЩЕЕ ВРЕМЯ

| Этап | Время |
|------|-------|
| 1. Скачивание | 5-15 мин |
| 2. Подготовка | 15-30 мин |
| 3. Обучение | 1-2 часа |
| 4. Оценка | 30 мин |
| 5. Документирование | 30 мин |
| **ИТОГО** | **2.5-4 часа** |

---

## 🆘 ЧТО МОЖЕТ ПОЙТИ НЕ ТАК

### Проблема 1: "Kaggle API не найден"
**Решение:** Получить credentials на https://www.kaggle.com/settings/account

### Проблема 2: "Недостаточно места на диске"
**Решение:** Очистить место или скачать на другой диск

### Проблема 3: "Модели не скачиваются / загружаются"
**Решение:** Проверить что моделях в data/models/:
```bash
ls -la /home/yerzhan/Desktop/new_diplom/data/models/
```

### Проблема 4: "Метрики не достигают требуемого значения"
**Решение:** 
- Проверить параметры обучения в скрипте
- Использовать дополнительный feature engineering
- Настроить threshold для classification

### Проблема 5: "Latency слишком высокий"
**Решение:**
- Убедиться что модели загружены в памяти (не с диска)
- Использовать батчи для обработки
- Рассмотреть quantization моделей

---

## ✅ ЧЕКЛИСТ ПЕРЕД ЗАПУСКОМ

- [ ] Свободное место на диске: >20 GB
- [ ] Интернет стабильный (для скачивания)
- [ ] Python 3.8+ установлен
- [ ] Все зависимости установлены:
  ```bash
  pip list | grep -E "pandas|numpy|scikit-learn|tensorflow|xgboost|kaggle"
  ```
- [ ] Прочитан DOWNLOAD_IEEE_CIS.md
- [ ] Подготовлены credentials (если используете Kaggle CLI)

---

## 🚀 ЗАПУСК (ФИНАЛЬНО)

**Вариант 1 - Через Kaggle CLI:**
```bash
cd /home/yerzhan/Desktop/new_diplom
python backend/scripts/evaluate_ieee_cis.py
```

**Вариант 2 - С локальными файлами:**
```bash
# 1. Скачать и разместить CSV в data/ieee_cis/
# 2. Запустить скрипт (он обнаружит файлы автоматически)
cd /home/yerzhan/Desktop/new_diplom
python backend/scripts/evaluate_ieee_cis.py
```

---

## 📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

✅ Должны получить:
```
F1-Score:     0.90+ ✓
AUC-ROC:      0.96+ ✓
Latency P95:  <200ms ✓
Latency Avg:  ~87ms ✓
```

❌ Если результаты ниже:
- Проверить preprocessing логику
- Увеличить объём training данных
- Настроить гиперпараметры моделей
- Добавить новые признаки из 12 паттернов

---

## 📞 ДАЛЬНЕЙШИЕ ШАГИ

После успешной оценки:

1. ✅ Создать EVALUATION.md с результатами
2. ✅ Обновить дипломный документ с результатами
3. ✅ Миграция на PostgreSQL (следующий приоритет)
4. ✅ Подготовка демонстрации на 3 ноутбуках

---

**Готовы начать? 🚀**

Запустите:
```bash
python /home/yerzhan/Desktop/new_diplom/backend/scripts/evaluate_ieee_cis.py
```

Удачи! 💪
