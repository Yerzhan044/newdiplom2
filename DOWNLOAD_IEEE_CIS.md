# 📥 Скачивание IEEE-CIS Fraud Detection Dataset

## Способ 1: Через Kaggle API (Рекомендуется) ✅

### Шаг 1: Получить Kaggle API Token

1. Перейдите на https://www.kaggle.com/settings/account
2. Прокрутите вниз до раздела "API"
3. Нажмите кнопку **"Create New API Token"**
4. Будет загружен файл `kaggle.json`

### Шаг 2: Установить credentials

```bash
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

### Шаг 3: Скачать датасет

```bash
cd /home/yerzhan/Desktop/new_diplom
python backend/scripts/evaluate_ieee_cis.py
```

---

## Способ 2: Скачать вручную с Kaggle

### Шаг 1: Перейти на Kaggle

Откройте https://www.kaggle.com/competitions/ieee-cis-fraud-detection/data

### Шаг 2: Скачать файлы

Нужны следующие файлы:
- ✅ `train_transaction.csv` (1.1 GB)
- ✅ `test_transaction.csv` (0.6 GB)  
- ⭐ `train_identity.csv` (0.15 GB) - опционально
- ⭐ `test_identity.csv` (0.07 GB) - опционально

### Шаг 3: Поместить в проект

```bash
mkdir -p /home/yerzhan/Desktop/new_diplom/data/ieee_cis
# Скопировать CSV файлы в эту директорию
```

### Шаг 4: Запустить оценку

```bash
cd /home/yerzhan/Desktop/new_diplom
python backend/scripts/evaluate_ieee_cis.py
```

---

## Способ 3: Использовать kaggle-cli (если credentials есть)

```bash
# Установить Kaggle CLI (если ещё не установлена)
pip install kaggle

# Скачать датасет
cd /home/yerzhan/Desktop/new_diplom/data/ieee_cis
kaggle competitions download -c ieee-cis-fraud-detection

# Распаковать
unzip -q ieee-cis-fraud-detection.zip
```

---

## 📊 Информация о датасете

| Параметр | Значение |
|----------|---------|
| **Название** | IEEE-CIS Fraud Detection |
| **Размер** | 590,540 транзакций |
| **Классы** | Binary (fraud/non-fraud) |
| **Class Imbalance** | ~3.5% fraud |
| **Признаков** | 394 (43 категориальных + 351 числовых) |
| **Размер файла** | ~1.7 GB сжато, ~5-10 GB распаковано |

---

## ⏱️ Время скачивания

- 🌍 При хорошем интернете: 5-15 минут
- 🐌 При медленном интернете: 30-60 минут

---

## 🎯 Что будет сделано после скачивания

```
EVALUATION FLOW:
1. ✅ Загрузить датасет (590K транзакций)
2. ✅ Предварительная обработка
   - Удалить колонки с >85% пропусков
   - Заполнить пропуски
   - Feature engineering
3. ✅ Переобучить 5 моделей
   - XGBoost
   - Random Forest
   - LSTM
   - Isolation Forest
   - Rule Engine
4. ✅ Оценить метрики
   - F1-Score (требуется 0.90)
   - AUC-ROC (требуется 0.96)
   - Latency (требуется <200ms)
5. ✅ Сохранить результаты в evaluation_results/
```

---

## 🚀 Запуск оценки (после скачивания)

```bash
# Основной скрипт оценки
python /home/yerzhan/Desktop/new_diplom/backend/scripts/evaluate_ieee_cis.py

# Результаты будут сохранены в:
# /home/yerzhan/Desktop/new_diplom/evaluation_results/
```

---

## 🆘 Если возникли проблемы

### Kaggle API не работает

```bash
# Проверить credentials
ls -la ~/.kaggle/kaggle.json

# Проверить права доступа
chmod 600 ~/.kaggle/kaggle.json

# Проверить наличие Kaggle CLI
pip show kaggle

# Переустановить если нужно
pip install --upgrade kaggle
```

### Не хватает места на диске

Датасет занимает ~10 GB распакованным. Убедитесь что свободного места достаточно:

```bash
df -h  # Проверить свободное место
```

### Медленное скачивание

Если интернет медленный, рекомендуется скачивать вручную через браузер.

---

## ✅ Когда готово

После успешного скачивания датасета:

1. В `/home/yerzhan/Desktop/new_diplom/data/ieee_cis/` будут CSV файлы
2. Запустите: `python backend/scripts/evaluate_ieee_cis.py`
3. Результаты будут в `evaluation_results/`
4. Проверьте достигнуты ли требуемые метрики:
   - F1-Score ≥ 0.90
   - AUC-ROC ≥ 0.96
   - Latency ≤ 200 ms

---

## 📞 Следующие шаги

После успешной оценки на IEEE-CIS:

1. ✅ Документирование результатов в EVALUATION.md
2. ✅ Обновление диссертации с результатами
3. ✅ Переход на PostgreSQL (для надежности)
4. ✅ Тесты на 3 ноутбуках

Начнем скачивание! 🚀
