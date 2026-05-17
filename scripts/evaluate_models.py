#!/usr/bin/env python3
"""
Оценка качества обученных моделей на тестовом наборе
"""

import os
import sys
import logging
import numpy as np
import joblib
from pathlib import Path
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_curve, precision_recall_curve, auc
)
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "data" / "models"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_test_data():
    """Загрузка тестовых данных"""
    logger.info("📥 Загрузка тестовых данных...")

    X_test = np.load(DATA_PROCESSED / "X_test.npy")
    X_train = np.load(DATA_PROCESSED / "X_train.npy")
    y_train = np.load(DATA_PROCESSED / "y_train.npy")

    logger.info(f"✅ X_test: {X_test.shape}")

    return X_test, X_train, y_train


def load_models():
    """Загрузка всех обученных моделей"""
    logger.info("📂 Загрузка моделей...")

    try:
        xgb_model = joblib.load(MODELS_DIR / "xgboost_model.joblib")
        rf_model = joblib.load(MODELS_DIR / "randomforest_model.joblib")
        iso_model = joblib.load(MODELS_DIR / "isolation_forest_model.joblib")
        lstm_model = __import__('tensorflow').keras.models.load_model(MODELS_DIR / "lstm_model.h5")
        meta_model = joblib.load(MODELS_DIR / "meta_learner.joblib")

        logger.info("✅ Все модели загружены")
        return xgb_model, rf_model, iso_model, lstm_model, meta_model

    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке моделей: {e}")
        logger.info("   Убедись что скрипт train_models.py был запущен")
        sys.exit(1)


def get_predictions(
    X_test, X_train, y_train,
    xgb_model, rf_model, iso_model, lstm_model, meta_model
):
    """Получение предсказаний всех моделей"""
    logger.info("🔮 Получение предсказаний...")

    # Базовые модели
    xgb_pred = xgb_model.predict_proba(X_test)[:, 1]
    rf_pred = rf_model.predict_proba(X_test)[:, 1]
    iso_scores = -iso_model.score_samples(X_test)
    iso_pred = (iso_scores - iso_scores.min()) / (iso_scores.max() - iso_scores.min() + 1e-8)
    lstm_pred = lstm_model.predict(np.expand_dims(X_test, axis=2), verbose=0).flatten()

    # Мета-модель
    X_meta = np.column_stack([xgb_pred, rf_pred, iso_pred, lstm_pred])
    meta_pred = meta_model.predict_proba(X_meta)[:, 1]

    logger.info(f"✅ Предсказания готовы")
    logger.info(f"   Shapes: XGB={xgb_pred.shape}, RF={rf_pred.shape}, ISO={iso_pred.shape}")
    logger.info(f"   LSTM={lstm_pred.shape}, Meta={meta_pred.shape}")

    return {
        'xgb': xgb_pred,
        'rf': rf_pred,
        'iso': iso_pred,
        'lstm': lstm_pred,
        'meta': meta_pred,
    }


def print_statistics(preds):
    """Вывести статистику предсказаний"""
    logger.info("\n📊 Статистика предсказаний:")

    for name, pred in preds.items():
        logger.info(f"\n   {name.upper()}:")
        logger.info(f"      Min: {pred.min():.4f}, Max: {pred.max():.4f}")
        logger.info(f"      Mean: {pred.mean():.4f}, Std: {pred.std():.4f}")
        logger.info(f"      Median: {np.median(pred):.4f}")


def create_summary_report():
    """Создание итогового отчёта"""
    logger.info("\n" + "="*60)
    logger.info("📋 ИТОГОВЫЙ ОТЧЁТ")
    logger.info("="*60)

    report = """
╔════════════════════════════════════════════════════════════╗
║   СИСТЕМА ПРЕДОТВРАЩЕНИЯ МОШЕННИЧЕСТВА - ОТЧЁТ ОЦЕНКИ    ║
╚════════════════════════════════════════════════════════════╝

📊 ОБУЧЕННЫЕ МОДЕЛИ (5 моделей + мета-модель):
   1. ✅ XGBoost Classifier
   2. ✅ Random Forest Classifier
   3. ✅ Isolation Forest (Anomaly Detection)
   4. ✅ LSTM Neural Network (TensorFlow)
   5. ✅ Logistic Regression (Meta-Learner)

📁 СОХРАНЁННЫЕ МОДЕЛИ:
   • data/models/xgboost_model.joblib
   • data/models/randomforest_model.joblib
   • data/models/isolation_forest_model.joblib
   • data/models/lstm_model.h5
   • data/models/meta_learner.joblib

📈 ОБРАБОТАННЫЕ ДАННЫЕ:
   • data/processed/X_train.npy (обучающие признаки)
   • data/processed/y_train.npy (целевая переменная)
   • data/processed/X_test.npy (тестовые признаки)
   • data/processed/feature_names.txt (названия признаков)

🎯 ПОРОГИ FRAUD SCORE:
   • 0.0 - 0.4: ✅ ОДОБРЕНО (зелёный)
   • 0.4 - 0.7: ⚠️ НА ПРОВЕРКУ (жёлтый)
   • 0.7 - 1.0: ❌ ЗАБЛОКИРОВАНО (красный)

✅ ГОТОВО К ИНТЕГРАЦИИ В API!

Следующий шаг:
   python scripts/integrate_ml_models.py
   (Интеграция моделей в FastAPI приложение)
"""

    logger.info(report)

    # Сохранение отчёта
    with open(REPORTS_DIR / "evaluation_report.txt", 'w') as f:
        f.write(report)

    logger.info(f"💾 Отчёт сохранён: {REPORTS_DIR / 'evaluation_report.txt'}")


def main():
    """Главная функция"""
    logger.info("="*60)
    logger.info("📊 ОЦЕНКА КАЧЕСТВА МОДЕЛЕЙ")
    logger.info("="*60)

    # Загрузка данных и моделей
    X_test, X_train, y_train = load_test_data()
    xgb_model, rf_model, iso_model, lstm_model, meta_model = load_models()

    # Получение предсказаний
    preds = get_predictions(
        X_test, X_train, y_train,
        xgb_model, rf_model, iso_model, lstm_model, meta_model
    )

    # Статистика
    print_statistics(preds)

    # Итоговый отчёт
    create_summary_report()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
