#!/usr/bin/env python3
"""
Скрипт для обработки IEEE-CIS датасета и создания feature-engineered датасета

Этапы:
1. Загрузка train/test данных
2. Merge transaction + identity данных
3. Feature engineering (создание новых признаков)
4. Масштабирование и нормализация
5. Сохранение обработанных данных
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler, LabelEncoder
import warnings

warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)


def load_datasets():
    """Загрузка датасетов"""
    logger.info("📥 Загрузка датасетов...")

    train_trans = pd.read_csv(DATA_RAW / "train_transaction.csv")
    train_ident = pd.read_csv(DATA_RAW / "train_identity.csv")
    test_trans = pd.read_csv(DATA_RAW / "test_transaction.csv")
    test_ident = pd.read_csv(DATA_RAW / "test_identity.csv")

    logger.info(f"✅ Train Transaction: {train_trans.shape}")
    logger.info(f"✅ Train Identity: {train_ident.shape}")
    logger.info(f"✅ Test Transaction: {test_trans.shape}")
    logger.info(f"✅ Test Identity: {test_ident.shape}")

    return train_trans, train_ident, test_trans, test_ident


def merge_datasets(trans, ident):
    """Объединение transaction и identity данных"""
    logger.info("🔗 Объединение transaction + identity...")

    df = trans.merge(ident, on="TransactionID", how="left")
    logger.info(f"✅ Объединённый датасет: {df.shape}")

    return df


def feature_engineering(df):
    """Создание новых признаков (feature engineering)"""
    logger.info("🔧 Feature Engineering...")

    # Копируем dataframe чтобы не менять оригинал
    df = df.copy()

    # ═══════════════════════════════════════════════════
    # 1. TIME-BASED FEATURES (временные признаки)
    # ═══════════════════════════════════════════════════

    df['TransactionDT'] = pd.to_datetime(df['TransactionDT'], unit='s')
    df['Transaction_Hour'] = df['TransactionDT'].dt.hour
    df['Transaction_DayOfWeek'] = df['TransactionDT'].dt.dayofweek
    df['Transaction_Day'] = df['TransactionDT'].dt.day
    df['Transaction_Month'] = df['TransactionDT'].dt.month

    # Ночные часы (02:00-05:00) - паттерн мошенничества
    df['IsNightTime'] = ((df['Transaction_Hour'] >= 2) & (df['Transaction_Hour'] <= 5)).astype(int)

    # ═══════════════════════════════════════════════════
    # 2. AMOUNT-BASED FEATURES (сумма транзакции)
    # ═══════════════════════════════════════════════════

    df['Amount_log'] = np.log1p(df['TransactionAmt'])

    # Средняя сумма по карте
    df['Card_Amount_Mean'] = df.groupby('card1')['TransactionAmt'].transform('mean')
    df['Card_Amount_Std'] = df.groupby('card1')['TransactionAmt'].transform('std')

    # Нормализованная сумма
    df['Amount_Normalized'] = (df['TransactionAmt'] - df['Card_Amount_Mean']) / (df['Card_Amount_Std'] + 1)

    # ═══════════════════════════════════════════════════
    # 3. VELOCITY FEATURES (частота транзакций)
    # ═══════════════════════════════════════════════════

    # Кол-во транзакций по карте за последний день
    df['Card_Transactions_1day'] = df.groupby('card1').size() - df.groupby('card1').cumcount() - 1

    # Кол-во уникальных мерчантов по карте
    df['Card_Unique_Merchants'] = df.groupby('card1')['merchant'].nunique()

    # ═══════════════════════════════════════════════════
    # 4. DEVICE & LOCATION FEATURES
    # ═══════════════════════════════════════════════════

    # Уникальные устройства по карте
    df['Card_Unique_Devices'] = df.groupby('card1')['DeviceInfo'].nunique()

    # IP адреса
    df['IP_Transaction_Count'] = df.groupby('ip1').cumcount() + 1
    df['IP_Unique_Cards'] = df.groupby('ip1')['card1'].nunique()

    # ═══════════════════════════════════════════════════
    # 5. CATEGORICAL FEATURES (кодирование)
    # ═══════════════════════════════════════════════════

    categorical_cols = ['ProductCD', 'card4', 'card6', 'P_emaildomain', 'R_emaildomain', 'DeviceType']

    for col in categorical_cols:
        if col in df.columns:
            df[col + '_encoded'] = pd.factorize(df[col])[0]

    # ═══════════════════════════════════════════════════
    # 6. NULL/MISSING VALUES RATIO
    # ═══════════════════════════════════════════════════

    df['Missing_Count'] = df.isnull().sum(axis=1)

    logger.info(f"✅ Created {len([c for c in df.columns if c not in trans.columns])} новых признаков")

    return df


def handle_missing_values(df):
    """Обработка пропущенных значений"""
    logger.info("🔍 Обработка пропущенных значений...")

    # Заполнение числовых колонок средним значением
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isnull().sum() > 0:
            df[col].fillna(df[col].mean(), inplace=True)

    # Заполнение категориальных колонок модой или 'unknown'
    categorical_cols = df.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        if df[col].isnull().sum() > 0:
            df[col].fillna('unknown', inplace=True)

    logger.info(f"✅ Пропущенные значения обработаны")

    return df


def select_features(df):
    """Выбор важнейших признаков для моделей"""
    logger.info("📊 Выбор признаков...")

    # Признаки которые мы создали или используем
    feature_cols = [
        # Amount features
        'TransactionAmt', 'Amount_log', 'Card_Amount_Mean', 'Card_Amount_Std',
        'Amount_Normalized',

        # Time features
        'Transaction_Hour', 'Transaction_DayOfWeek', 'Transaction_Day',
        'Transaction_Month', 'IsNightTime',

        # Velocity features
        'Card_Transactions_1day', 'Card_Unique_Merchants', 'Card_Unique_Devices',
        'IP_Transaction_Count', 'IP_Unique_Cards',

        # Categorical features (encoded)
        'ProductCD_encoded', 'card4_encoded', 'card6_encoded',
        'DeviceType_encoded',

        # Other
        'Missing_Count',
    ]

    # Проверяем что все колонки есть в датасете
    available_cols = [col for col in feature_cols if col in df.columns]

    logger.info(f"✅ Выбрано {len(available_cols)} признаков для моделей")

    return available_cols


def scale_features(X_train, X_test):
    """Масштабирование признаков"""
    logger.info("📈 Масштабирование признаков...")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    logger.info("✅ Признаки масштабированы (StandardScaler)")

    return X_train_scaled, X_test_scaled, scaler


def process_data():
    """Главная функция обработки данных"""
    logger.info("="*60)
    logger.info("🔄 ОБРАБОТКА IEEE-CIS FRAUD DETECTION ДАТАСЕТА")
    logger.info("="*60)

    # 1. Загрузка данных
    train_trans, train_ident, test_trans, test_ident = load_datasets()

    # 2. Объединение
    train_df = merge_datasets(train_trans, train_ident)
    test_df = merge_datasets(test_trans, test_ident)

    # 3. Feature engineering
    train_df = feature_engineering(train_df)
    test_df = feature_engineering(test_df)

    # 4. Обработка пропущенных значений
    train_df = handle_missing_values(train_df)
    test_df = handle_missing_values(test_df)

    # 5. Выбор признаков
    feature_cols = select_features(train_df)

    # 6. Подготовка X и y
    X_train = train_df[feature_cols].values
    y_train = train_df['isFraud'].values

    X_test = test_df[feature_cols].values

    logger.info(f"\n📊 Финальные размеры данных:")
    logger.info(f"   X_train: {X_train.shape}")
    logger.info(f"   y_train: {y_train.shape}")
    logger.info(f"   X_test: {X_test.shape}")

    # 7. Масштабирование
    X_train_scaled, X_test_scaled, scaler = scale_features(X_train, X_test)

    # 8. Сохранение
    logger.info("\n💾 Сохранение обработанных данных...")

    np.save(DATA_PROCESSED / "X_train.npy", X_train_scaled)
    np.save(DATA_PROCESSED / "y_train.npy", y_train)
    np.save(DATA_PROCESSED / "X_test.npy", X_test_scaled)

    # Сохраняем feature names
    with open(DATA_PROCESSED / "feature_names.txt", 'w') as f:
        for col in feature_cols:
            f.write(f"{col}\n")

    logger.info(f"✅ X_train сохранён в {DATA_PROCESSED / 'X_train.npy'}")
    logger.info(f"✅ y_train сохранён в {DATA_PROCESSED / 'y_train.npy'}")
    logger.info(f"✅ X_test сохранён в {DATA_PROCESSED / 'X_test.npy'}")
    logger.info(f"✅ Feature names сохранены в {DATA_PROCESSED / 'feature_names.txt'}")

    # Статистика по целевой переменной
    fraud_count = np.sum(y_train)
    fraud_rate = fraud_count / len(y_train) * 100

    logger.info(f"\n📈 Статистика по мошенничеству:")
    logger.info(f"   Легитимных: {len(y_train) - fraud_count:,} ({100 - fraud_rate:.2f}%)")
    logger.info(f"   Мошеннических: {fraud_count:,} ({fraud_rate:.2f}%)")

    logger.info("\n✅ Обработка данных завершена!")
    logger.info("   Следующий шаг: python scripts/train_models.py")


if __name__ == "__main__":
    try:
        process_data()
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
