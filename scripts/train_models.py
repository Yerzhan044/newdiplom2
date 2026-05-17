#!/usr/bin/env python3
"""
Обучение 5 моделей ансамбля для обнаружения мошенничества

Модели:
1. XGBoost - быстро, лучше всех на табличных данных
2. Random Forest - надёжно, хорошие feature importances
3. LSTM - нейросеть, учитывает последовательности
4. Isolation Forest - обнаружение аномалий
5. Rule Engine - жёсткие правила (паттерны)

Мета-модель: Logistic Regression (объединяет всех)
"""

import os
import sys
import logging
import numpy as np
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_curve
)

import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "data" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    """Загрузка обработанных данных"""
    logger.info("📥 Загрузка обработанных данных...")

    X_train = np.load(DATA_PROCESSED / "X_train.npy")
    y_train = np.load(DATA_PROCESSED / "y_train.npy")
    X_test = np.load(DATA_PROCESSED / "X_test.npy")

    logger.info(f"✅ X_train: {X_train.shape}, y_train: {y_train.shape}")
    logger.info(f"✅ X_test: {X_test.shape}")

    return X_train, y_train, X_test


def split_data(X, y):
    """Разделение данных на train/val"""
    logger.info("📊 Разделение данных на train/validation...")

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    logger.info(f"✅ Train: {X_train.shape}, Validation: {X_val.shape}")
    logger.info(f"   Train fraud rate: {np.mean(y_train)*100:.2f}%")
    logger.info(f"   Val fraud rate: {np.mean(y_val)*100:.2f}%")

    return X_train, X_val, y_train, y_val


def train_xgboost(X_train, y_train, X_val, y_val):
    """Обучение XGBoost модели"""
    logger.info("\n" + "="*60)
    logger.info("🚀 ОБУЧЕНИЕ XGBOOST")
    logger.info("="*60)

    try:
        import xgboost as xgb

        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=7,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=1,  # class_weight
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )

        logger.info("🔄 Обучение модели...")
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=20,
            verbose=False,
        )

        # Оценка
        y_pred = model.predict(X_val)
        y_pred_proba = model.predict_proba(X_val)[:, 1]

        roc_auc = roc_auc_score(y_val, y_pred_proba)
        precision = precision_score(y_val, y_pred)
        recall = recall_score(y_val, y_pred)
        f1 = f1_score(y_val, y_pred)

        logger.info(f"✅ XGBoost ROC-AUC: {roc_auc:.4f}")
        logger.info(f"   Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")

        # Сохранение
        model_path = MODELS_DIR / "xgboost_model.joblib"
        joblib.dump(model, model_path)
        logger.info(f"💾 Модель сохранена: {model_path}")

        return model, roc_auc

    except Exception as e:
        logger.error(f"❌ Ошибка при обучении XGBoost: {e}")
        return None, 0


def train_random_forest(X_train, y_train, X_val, y_val):
    """Обучение Random Forest модели"""
    logger.info("\n" + "="*60)
    logger.info("🌳 ОБУЧЕНИЕ RANDOM FOREST")
    logger.info("="*60)

    try:
        from sklearn.ensemble import RandomForestClassifier

        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
            verbose=0,
        )

        logger.info("🔄 Обучение модели...")
        model.fit(X_train, y_train)

        # Оценка
        y_pred = model.predict(X_val)
        y_pred_proba = model.predict_proba(X_val)[:, 1]

        roc_auc = roc_auc_score(y_val, y_pred_proba)
        precision = precision_score(y_val, y_pred)
        recall = recall_score(y_val, y_pred)
        f1 = f1_score(y_val, y_pred)

        logger.info(f"✅ Random Forest ROC-AUC: {roc_auc:.4f}")
        logger.info(f"   Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")

        # Сохранение
        model_path = MODELS_DIR / "randomforest_model.joblib"
        joblib.dump(model, model_path)
        logger.info(f"💾 Модель сохранена: {model_path}")

        return model, roc_auc

    except Exception as e:
        logger.error(f"❌ Ошибка при обучении Random Forest: {e}")
        return None, 0


def train_isolation_forest(X_train, y_train, X_val, y_val):
    """Обучение Isolation Forest для обнаружения аномалий"""
    logger.info("\n" + "="*60)
    logger.info("🎯 ОБУЧЕНИЕ ISOLATION FOREST")
    logger.info("="*60)

    try:
        from sklearn.ensemble import IsolationForest

        # Isolation Forest для anomaly detection
        model = IsolationForest(
            contamination=np.mean(y_train),  # Используем proportion мошеннических
            random_state=42,
            n_jobs=-1,
        )

        logger.info("🔄 Обучение модели...")
        model.fit(X_train)

        # Предсказания: -1 (аномалия/fraud), 1 (нормально)
        y_pred_if = model.predict(X_val)  # -1 или 1
        y_scores = -model.score_samples(X_val)  # Инвертируем для score (выше = более аномально)

        # Нормализация скоров на [0, 1]
        y_scores = (y_scores - y_scores.min()) / (y_scores.max() - y_scores.min() + 1e-8)

        # Бинаризация: -1 -> 1 (fraud), 1 -> 0 (normal)
        y_pred = (y_pred_if == -1).astype(int)

        roc_auc = roc_auc_score(y_val, y_scores)
        precision = precision_score(y_val, y_pred)
        recall = recall_score(y_val, y_pred)
        f1 = f1_score(y_val, y_pred)

        logger.info(f"✅ Isolation Forest ROC-AUC: {roc_auc:.4f}")
        logger.info(f"   Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")

        # Сохранение
        model_path = MODELS_DIR / "isolation_forest_model.joblib"
        joblib.dump(model, model_path)
        logger.info(f"💾 Модель сохранена: {model_path}")

        return model, roc_auc

    except Exception as e:
        logger.error(f"❌ Ошибка при обучении Isolation Forest: {e}")
        return None, 0


def train_lstm(X_train, y_train, X_val, y_val):
    """Обучение LSTM нейросети"""
    logger.info("\n" + "="*60)
    logger.info("🧠 ОБУЧЕНИЕ LSTM (TENSORFLOW)")
    logger.info("="*60)

    try:
        from tensorflow import keras
        from tensorflow.keras import layers, models
        from tensorflow.keras.optimizers import Adam

        # Reshape для LSTM (batch_size, timesteps, features)
        # Трактуем каждый признак как timestep
        X_train_lstm = np.expand_dims(X_train, axis=2)
        X_val_lstm = np.expand_dims(X_val, axis=2)

        logger.info(f"   X_train shape for LSTM: {X_train_lstm.shape}")

        # Построение модели
        model = models.Sequential([
            layers.LSTM(64, activation='relu', input_shape=(X_train_lstm.shape[1], 1)),
            layers.Dropout(0.3),
            layers.Dense(32, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(16, activation='relu'),
            layers.Dense(1, activation='sigmoid'),
        ])

        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='binary_crossentropy',
            metrics=['accuracy'],
        )

        logger.info("🔄 Обучение модели...")
        history = model.fit(
            X_train_lstm, y_train,
            validation_data=(X_val_lstm, y_val),
            epochs=20,
            batch_size=256,
            verbose=0,
            callbacks=[
                keras.callbacks.EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True)
            ]
        )

        # Оценка
        y_pred_proba = model.predict(X_val_lstm, verbose=0).flatten()
        y_pred = (y_pred_proba > 0.5).astype(int)

        roc_auc = roc_auc_score(y_val, y_pred_proba)
        precision = precision_score(y_val, y_pred)
        recall = recall_score(y_val, y_pred)
        f1 = f1_score(y_val, y_pred)

        logger.info(f"✅ LSTM ROC-AUC: {roc_auc:.4f}")
        logger.info(f"   Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")

        # Сохранение
        model_path = MODELS_DIR / "lstm_model.h5"
        model.save(model_path)
        logger.info(f"💾 Модель сохранена: {model_path}")

        return model, roc_auc

    except Exception as e:
        logger.error(f"❌ Ошибка при обучении LSTM: {e}")
        return None, 0


def train_meta_learner(
    X_train, y_train, X_val, y_val,
    xgb_model, rf_model, iso_model, lstm_model
):
    """Обучение мета-модели (Logistic Regression) на выходах всех моделей"""
    logger.info("\n" + "="*60)
    logger.info("🎯 ОБУЧЕНИЕ META-LEARNER (LOGISTIC REGRESSION)")
    logger.info("="*60)

    try:
        from sklearn.linear_model import LogisticRegression

        # Собираем предсказания всех моделей
        logger.info("🔄 Сбор предсказаний от базовых моделей...")

        # XGBoost
        xgb_pred_train = xgb_model.predict_proba(X_train)[:, 1]
        xgb_pred_val = xgb_model.predict_proba(X_val)[:, 1]

        # Random Forest
        rf_pred_train = rf_model.predict_proba(X_train)[:, 1]
        rf_pred_val = rf_model.predict_proba(X_val)[:, 1]

        # Isolation Forest
        iso_pred_train = -iso_model.score_samples(X_train)
        iso_pred_val = -iso_model.score_samples(X_val)
        iso_pred_train = (iso_pred_train - iso_pred_train.min()) / (iso_pred_train.max() - iso_pred_train.min() + 1e-8)
        iso_pred_val = (iso_pred_val - iso_pred_val.min()) / (iso_pred_val.max() - iso_pred_val.min() + 1e-8)

        # LSTM
        X_train_lstm = np.expand_dims(X_train, axis=2)
        X_val_lstm = np.expand_dims(X_val, axis=2)
        lstm_pred_train = lstm_model.predict(X_train_lstm, verbose=0).flatten()
        lstm_pred_val = lstm_model.predict(X_val_lstm, verbose=0).flatten()

        # Объединяем в одну матрицу признаков для мета-модели
        X_meta_train = np.column_stack([xgb_pred_train, rf_pred_train, iso_pred_train, lstm_pred_train])
        X_meta_val = np.column_stack([xgb_pred_val, rf_pred_val, iso_pred_val, lstm_pred_val])

        logger.info(f"   Meta-features shape: {X_meta_train.shape}")

        # Обучение логистической регрессии
        meta_model = LogisticRegression(max_iter=1000, random_state=42)
        meta_model.fit(X_meta_train, y_train)

        # Оценка
        y_pred_proba = meta_model.predict_proba(X_meta_val)[:, 1]
        y_pred = meta_model.predict(X_meta_val)

        roc_auc = roc_auc_score(y_val, y_pred_proba)
        precision = precision_score(y_val, y_pred)
        recall = recall_score(y_val, y_pred)
        f1 = f1_score(y_val, y_pred)

        logger.info(f"✅ Meta-Learner ROC-AUC: {roc_auc:.4f}")
        logger.info(f"   Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")

        # Коэффициенты мета-модели (веса для каждой базовой модели)
        logger.info(f"\n📊 Веса базовых моделей в мета-модели:")
        logger.info(f"   XGBoost: {meta_model.coef_[0][0]:.4f}")
        logger.info(f"   Random Forest: {meta_model.coef_[0][1]:.4f}")
        logger.info(f"   Isolation Forest: {meta_model.coef_[0][2]:.4f}")
        logger.info(f"   LSTM: {meta_model.coef_[0][3]:.4f}")

        # Сохранение
        model_path = MODELS_DIR / "meta_learner.joblib"
        joblib.dump(meta_model, model_path)
        logger.info(f"💾 Мета-модель сохранена: {model_path}")

        return meta_model, roc_auc

    except Exception as e:
        logger.error(f"❌ Ошибка при обучении мета-модели: {e}")
        return None, 0


def main():
    """Главная функция"""
    logger.info("="*60)
    logger.info("🤖 ОБУЧЕНИЕ АНСАМБЛЯ ИЗ 5 МОДЕЛЕЙ")
    logger.info("="*60)

    # 1. Загрузка и разделение данных
    X, y, X_test = load_data()
    X_train, X_val, y_train, y_val = split_data(X, y)

    models_scores = {}

    # 2. Обучение базовых моделей
    xgb_model, xgb_score = train_xgboost(X_train, y_train, X_val, y_val)
    rf_model, rf_score = train_random_forest(X_train, y_train, X_val, y_val)
    iso_model, iso_score = train_isolation_forest(X_train, y_train, X_val, y_val)
    lstm_model, lstm_score = train_lstm(X_train, y_train, X_val, y_val)

    models_scores['XGBoost'] = xgb_score
    models_scores['Random Forest'] = rf_score
    models_scores['Isolation Forest'] = iso_score
    models_scores['LSTM'] = lstm_score

    # 3. Обучение мета-модели
    if all([xgb_model, rf_model, iso_model, lstm_model]):
        meta_model, meta_score = train_meta_learner(
            X_train, y_train, X_val, y_val,
            xgb_model, rf_model, iso_model, lstm_model
        )
        models_scores['Meta-Learner'] = meta_score

        # 4. Итоговая таблица
        logger.info("\n" + "="*60)
        logger.info("📊 ИТОГОВАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
        logger.info("="*60)

        for model_name, score in sorted(models_scores.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   {model_name:20} ROC-AUC: {score:.4f}")

        logger.info("\n✅ Все модели обучены и сохранены!")
        logger.info(f"   Директория: {MODELS_DIR}")
        logger.info("\n   Следующий шаг: python scripts/evaluate_models.py")

    else:
        logger.error("❌ Ошибка при обучении некоторых моделей")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
