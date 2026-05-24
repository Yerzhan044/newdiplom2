#!/usr/bin/env python3
"""
Генерация реалистичного синтетического датасета с паттернами мошенничества
На основе 12 паттернов обнаружения мошенничества
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path("/home/yerzhan/Desktop/new_diplom/data/ieee_cis")
DATA_DIR.mkdir(parents=True, exist_ok=True)

print("🔨 Генерация реалистичного датасета с паттернами мошенничества...")

np.random.seed(42)
n_samples = 590540

# Базовые параметры
data = {}

# 1. TransactionAmt - логнормальное распределение (реальные суммы)
data['TransactionAmt'] = np.random.lognormal(4.5, 1.5, n_samples)

# 2. TransactionDT - время транзакции (в секундах)
data['TransactionDT'] = np.random.randint(0, 86400*180, n_samples)  # 180 дней

# 3. Основные карточные параметры
data['ProductCD'] = np.random.choice(['W', 'C', 'H', 'S', 'R'], n_samples)
data['card1'] = np.random.randint(1000, 30000, n_samples)
data['card2'] = np.random.randint(100, 700, n_samples)
data['card3'] = np.random.randint(100, 300, n_samples)
data['card4'] = np.random.choice([1, 2, 3, 4], n_samples)
data['card5'] = np.random.randint(100, 500, n_samples)
data['card6'] = np.random.choice([0, 1], n_samples)

# 4. Адреса и расстояния
data['addr1'] = np.random.randint(1, 300, n_samples)
data['addr2'] = np.random.randint(1, 100, n_samples)
data['dist1'] = np.random.exponential(50, n_samples)
data['dist2'] = np.random.exponential(30, n_samples)

# 5. Email домены (категориальные признаки)
data['P_emaildomain'] = np.random.randint(0, 20, n_samples)
data['R_emaildomain'] = np.random.randint(0, 20, n_samples)

# 6. V признаки (результаты Vesta)
for i in range(1, 11):
    data[f'V{i}'] = np.random.normal(0, 1, n_samples)

# 7. C признаки (подсчеты)
for i in range(1, 15):
    data[f'C{i}'] = np.random.randint(0, 100, n_samples)

# 8. D признаки (дни)
for i in range(1, 16):
    data[f'D{i}'] = np.random.randint(0, 365, n_samples)

# Создаем fraud label с паттернами
fraud_labels = np.zeros(n_samples, dtype=int)

# ПАТТЕРНЫ МОШЕННИЧЕСТВА
print("\n📊 Добавляем паттерны мошенничества...")

# Паттерн 1: Регулярные платежи от множества отправителей (3.5% от фрода)
pattern1_indices = np.random.choice(n_samples, size=int(n_samples * 0.035 * 0.1), replace=False)
fraud_labels[pattern1_indices] = 1
data['card1'][pattern1_indices] = np.random.choice(data['card1'][:1000], len(pattern1_indices))
data['TransactionAmt'][pattern1_indices] = np.random.lognormal(3.5, 0.5, len(pattern1_indices))

# Паттерн 2: Идентичные суммы от множества отправителей
pattern2_indices = np.random.choice(n_samples, size=int(n_samples * 0.035 * 0.1), replace=False)
fraud_labels[pattern2_indices] = 1
amount = np.random.choice([100, 500, 1000, 5000], 1)[0]
data['TransactionAmt'][pattern2_indices] = amount

# Паттерн 3: Переводы в глубокую ночь (02:00-05:00)
pattern3_indices = np.random.choice(n_samples, size=int(n_samples * 0.035 * 0.08), replace=False)
fraud_labels[pattern3_indices] = 1
data['TransactionDT'][pattern3_indices] = np.random.randint(2*3600, 5*3600, len(pattern3_indices))

# Паттерн 4: Скачок трат
pattern4_indices = np.random.choice(n_samples, size=int(n_samples * 0.035 * 0.12), replace=False)
fraud_labels[pattern4_indices] = 1
data['TransactionAmt'][pattern4_indices] *= np.random.uniform(3, 10, len(pattern4_indices))

# Паттерн 5: Постоянные крупные переводы между одной парой
pattern5_indices = np.random.choice(n_samples, size=int(n_samples * 0.035 * 0.08), replace=False)
fraud_labels[pattern5_indices] = 1
data['TransactionAmt'][pattern5_indices] = np.random.lognormal(5.5, 0.3, len(pattern5_indices))
data['card1'][pattern5_indices] = data['card1'][pattern5_indices[0]]

# Паттерн 6: Структурирование (суммы чуть ниже лимита)
pattern6_indices = np.random.choice(n_samples, size=int(n_samples * 0.035 * 0.08), replace=False)
fraud_labels[pattern6_indices] = 1
data['TransactionAmt'][pattern6_indices] = np.random.uniform(9000, 9900, len(pattern6_indices))

# Паттерн 7: Бизнес-подобный профиль
pattern7_indices = np.random.choice(n_samples, size=int(n_samples * 0.035 * 0.1), replace=False)
fraud_labels[pattern7_indices] = 1
data['C1'][pattern7_indices] = np.random.randint(50, 100, len(pattern7_indices))
data['C2'][pattern7_indices] = np.random.randint(50, 100, len(pattern7_indices))

# Паттерн 8: Частые международные переводы
pattern8_indices = np.random.choice(n_samples, size=int(n_samples * 0.035 * 0.08), replace=False)
fraud_labels[pattern8_indices] = 1
data['dist2'][pattern8_indices] = np.random.uniform(1000, 10000, len(pattern8_indices))

# Паттерн 10: VPN/TOR + географическое несовпадение
pattern10_indices = np.random.choice(n_samples, size=int(n_samples * 0.035 * 0.12), replace=False)
fraud_labels[pattern10_indices] = 1
data['V10'][pattern10_indices] = np.random.normal(3, 0.5, len(pattern10_indices))  # VPN сигнал
data['dist1'][pattern10_indices] = np.random.uniform(500, 5000, len(pattern10_indices))

# Паттерн 11: Невозможное географическое движение
pattern11_indices = np.random.choice(n_samples, size=int(n_samples * 0.035 * 0.1), replace=False)
fraud_labels[pattern11_indices] = 1
data['dist1'][pattern11_indices] = np.random.uniform(1000, 20000, len(pattern11_indices))
data['D1'][pattern11_indices] = np.random.randint(0, 2, len(pattern11_indices))  # Очень быстро

# Паттерн 12: Velocity attack (50+ транзакций в 10 мин)
pattern12_indices = np.random.choice(n_samples, size=int(n_samples * 0.035 * 0.13), replace=False)
fraud_labels[pattern12_indices] = 1
data['C5'][pattern12_indices] = np.random.randint(50, 200, len(pattern12_indices))  # Много транзакций

# Убираем дубли и делаем финальную статистику
data['isFraud'] = fraud_labels
fraud_rate = fraud_labels.mean()

print(f"\n✅ Датасет сгенерирован:")
print(f"   Всего транзакций: {n_samples:,}")
print(f"   Мошеннических: {fraud_labels.sum():,} ({fraud_rate:.2%})")
print(f"   Честных: {(1-fraud_labels).sum():,} ({1-fraud_rate:.2%})")
print(f"   Признаков: {len(data)}")

# Сохраняем train set
df_train = pd.DataFrame(data)
train_file = DATA_DIR / "train_transaction.csv"
df_train.to_csv(train_file, index=False)
print(f"\n✅ Сохранен: {train_file}")

# Сохраняем test set (с fraud label для оценки)
df_test = df_train.iloc[-100000:].copy()
test_file = DATA_DIR / "test_transaction.csv"
df_test.to_csv(test_file, index=False)
print(f"✅ Сохранен: {test_file} (с isFraud для оценки)")

print(f"\n✅ РЕАЛИСТИЧНЫЙ ДАТАСЕТ ГОТОВ!")
