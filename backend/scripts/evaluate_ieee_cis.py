#!/usr/bin/env python3
"""
IEEE-CIS Fraud Detection Dataset Evaluation
=============================================
Загрузка, обработка и оценка моделей на IEEE-CIS датасете.

Требуемые метрики:
- F1-Score = 0.90
- AUC-ROC = 0.96
- Latency < 200 ms
- Throughput >= 100 req/sec
"""

import os
import sys
import json
import logging
import time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List

# Sklearn metrics
from sklearn.metrics import (
    f1_score, roc_auc_score, confusion_matrix,
    classification_report, roc_curve, auc
)
from sklearn.preprocessing import StandardScaler

# Warnings
import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config.database import SessionLocal, init_db
from backend.config.settings import get_settings
from backend.ml.predictor import get_predictor
from backend.ml.feature_engineering import FeatureEngineer
from backend.services.rule_engine import RuleEngine
from backend.models.models import Transaction, User, Account, TransactionStatusEnum
from backend.services.fraud_service import FraudService

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "ieee_cis"
RESULTS_DIR = Path(__file__).parent.parent.parent / "evaluation_results"
MODELS_DIR = Path(__file__).parent.parent.parent / "data" / "models"

REQUIRED_COLUMNS = [
    'TransactionAmt', 'TransactionDT', 'ProductCD', 'card1', 'card2',
    'card3', 'card4', 'card5', 'card6', 'addr1', 'addr2', 'dist1', 'dist2',
    'P_emaildomain', 'R_emaildomain', 'C1', 'C2', 'C3', 'C4', 'C5',
    'C6', 'C7', 'C8', 'C9', 'C10', 'C11', 'C12', 'C13', 'C14',
    'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10',
    'D11', 'D12', 'D13', 'D14', 'D15',
    'V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10',
    'isFraud'
]

# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def download_ieee_cis_dataset() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Скачать IEEE-CIS датасет с Kaggle

    Returns:
        (train_df, test_df): Тренировочный и тестовый датасеты
    """
    logger.info("📥 Скачивание IEEE-CIS датасета с Kaggle...")

    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    train_file = DATA_DIR / "train_transaction.csv"
    test_file = DATA_DIR / "test_transaction.csv"

    if train_file.exists() and test_file.exists():
        logger.info("✅ Датасет уже загружен")
        return pd.read_csv(train_file), pd.read_csv(test_file)

    try:
        logger.info("Используя Kaggle API Python...")
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()

        logger.info(f"📥 Загрузка файлов в {DATA_DIR}...")
        logger.info("   Это может занять 5-15 минут в зависимости от интернета...")
        api.competition_download_files('ieee-cis-fraud-detection', path=DATA_DIR, quiet=False)

        logger.info("📦 Распаковка архива...")
        import zipfile
        zip_file = DATA_DIR / "ieee-cis-fraud-detection.zip"
        if zip_file.exists():
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(DATA_DIR)
            zip_file.unlink()  # Удалим архив после распаковки

        logger.info("✅ Датасет успешно загружен")
        return pd.read_csv(train_file), pd.read_csv(test_file)

    except Exception as e:
        logger.error(f"❌ Ошибка при скачивании: {e}")
        logger.info("💡 Требуется Kaggle API ключ в ~/.kaggle/access_token")
        logger.info("   Получить его можно на https://www.kaggle.com/settings/account")
        raise


def preprocess_ieee_cis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Предварительная обработка IEEE-CIS датасета

    Steps:
    1. Удаление колонок с >85% пропусков
    2. Feature engineering для 12 паттернов
    3. Нормализация
    """
    logger.info(f"🔧 Предварительная обработка {len(df)} транзакций...")

    # Шаг 1: Удаление редких колонок
    missing_threshold = 0.85
    missing_cols = [col for col in df.columns
                   if df[col].isna().sum() / len(df) > missing_threshold]
    df = df.drop(columns=missing_cols)
    logger.info(f"  ✓ Удалено {len(missing_cols)} колонок с >85% пропусков")

    # Шаг 2: Заполнение пропусков
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isna().sum() > 0:
            df[col].fillna(df[col].median(), inplace=True)
    logger.info(f"  ✓ Пропуски заполнены медианой")

    # Шаг 3: Target encoding для категориальных
    categorical_cols = df.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        if col != 'isFraud' and col not in ['TransactionDT']:
            # Используем frequency encoding
            freq_encoding = df[col].value_counts(normalize=True).to_dict()
            df[col] = df[col].map(freq_encoding).fillna(df[col].mode()[0])
    logger.info(f"  ✓ {len(categorical_cols)} категориальных колонок закодировано")

    return df


def extract_features_ieee_cis(df: pd.DataFrame) -> np.ndarray:
    """
    Extract features для предсказания
    """
    logger.info("⚙️ Извлечение признаков...")

    # Выбираем только числовые колонки для модели
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    numeric_cols = [col for col in numeric_cols if col != 'isFraud']

    X = df[numeric_cols].values

    # Нормализация
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    logger.info(f"  ✓ Подготовлено {X_scaled.shape[1]} признаков для {X_scaled.shape[0]} транзакций")

    return X_scaled


def evaluate_models(X_test: np.ndarray, y_test: np.ndarray,
                   model_predictions: Dict) -> Dict:
    """
    Оценка всех моделей
    """
    logger.info("📊 Оценка моделей...")

    results = {
        'models': {},
        'ensemble': {},
        'metrics': {}
    }

    # Оценка каждой модели
    for model_name, y_pred_proba in model_predictions.items():
        y_pred = (y_pred_proba >= 0.5).astype(int)

        f1 = f1_score(y_test, y_pred, average='weighted')
        auc = roc_auc_score(y_test, y_pred_proba)

        results['models'][model_name] = {
            'f1_score': float(f1),
            'auc_roc': float(auc),
            'predictions': y_pred.tolist()[:100]  # Sample
        }

        logger.info(f"  {model_name:20s} F1={f1:.4f}, AUC={auc:.4f}")

    # Ансамблевое предсказание (среднее всех моделей)
    ensemble_proba = np.mean(list(model_predictions.values()), axis=0)
    ensemble_pred = (ensemble_proba >= 0.5).astype(int)

    ensemble_f1 = f1_score(y_test, ensemble_pred, average='weighted')
    ensemble_auc = roc_auc_score(y_test, ensemble_proba)

    results['ensemble'] = {
        'f1_score': float(ensemble_f1),
        'auc_roc': float(ensemble_auc),
    }

    logger.info(f"\n  {'ENSEMBLE':20s} F1={ensemble_f1:.4f}, AUC={ensemble_auc:.4f} ⭐")

    # Требуемые метрики
    logger.info("\n🎯 ТРЕБУЕМЫЕ МЕТРИКИ:")
    logger.info(f"  F1-Score:  {ensemble_f1:.4f} (требуется 0.90) {'✅' if ensemble_f1 >= 0.90 else '❌'}")
    logger.info(f"  AUC-ROC:   {ensemble_auc:.4f} (требуется 0.96) {'✅' if ensemble_auc >= 0.96 else '❌'}")

    return results


def test_latency(predictor, X_test: np.ndarray, n_samples: int = 100) -> Dict:
    """
    Тестирование latency обработки
    """
    logger.info(f"\n⏱️ Тестирование latency ({n_samples} транзакций)...")

    latencies = []

    for i in range(min(n_samples, len(X_test))):
        start = time.time()

        # Имитация обработки как в API
        features = X_test[i:i+1]
        predictions = predictor.predict(features)

        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)

    latencies = np.array(latencies)

    results = {
        'mean': float(np.mean(latencies)),
        'median': float(np.median(latencies)),
        'p95': float(np.percentile(latencies, 95)),
        'p99': float(np.percentile(latencies, 99)),
        'min': float(np.min(latencies)),
        'max': float(np.max(latencies)),
    }

    logger.info(f"  Mean:      {results['mean']:.2f} ms (требуется <87 ms)")
    logger.info(f"  Median:    {results['median']:.2f} ms")
    logger.info(f"  P95:       {results['p95']:.2f} ms (требуется <200 ms)")
    logger.info(f"  P99:       {results['p99']:.2f} ms")

    return results


def save_results(results: Dict, latency_results: Dict):
    """
    Сохранение результатов оценки
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Основные результаты
    report = {
        'timestamp': timestamp,
        'dataset': 'IEEE-CIS Fraud Detection',
        'size': '590,540 transactions',
        'model_results': results['models'],
        'ensemble_results': results['ensemble'],
        'latency': latency_results,
        'requirements': {
            'f1_score': {
                'required': 0.90,
                'achieved': results['ensemble']['f1_score'],
                'status': '✅' if results['ensemble']['f1_score'] >= 0.90 else '❌'
            },
            'auc_roc': {
                'required': 0.96,
                'achieved': results['ensemble']['auc_roc'],
                'status': '✅' if results['ensemble']['auc_roc'] >= 0.96 else '❌'
            },
            'latency_p95': {
                'required': 200,
                'achieved': latency_results['p95'],
                'status': '✅' if latency_results['p95'] <= 200 else '❌'
            }
        }
    }

    # Сохраняем JSON
    json_file = RESULTS_DIR / f"evaluation_ieee_cis_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"\n✅ Результаты сохранены в {json_file}")

    # Сохраняем CSV отчёт
    csv_file = RESULTS_DIR / f"evaluation_report_{timestamp}.txt"
    with open(csv_file, 'w') as f:
        f.write("IEEE-CIS FRAUD DETECTION EVALUATION REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Dataset: IEEE-CIS ({report['size']})\n\n")

        f.write("ENSEMBLE RESULTS:\n")
        f.write("-" * 80 + "\n")
        f.write(f"F1-Score:     {results['ensemble']['f1_score']:.4f} (required: 0.90)\n")
        f.write(f"AUC-ROC:      {results['ensemble']['auc_roc']:.4f} (required: 0.96)\n\n")

        f.write("LATENCY METRICS:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Mean:         {latency_results['mean']:.2f} ms\n")
        f.write(f"Median:       {latency_results['median']:.2f} ms\n")
        f.write(f"P95:          {latency_results['p95']:.2f} ms (required: <200 ms)\n")
        f.write(f"P99:          {latency_results['p99']:.2f} ms\n\n")

        f.write("INDIVIDUAL MODEL RESULTS:\n")
        f.write("-" * 80 + "\n")
        for model_name, scores in results['models'].items():
            f.write(f"{model_name:20s} F1={scores['f1_score']:.4f}, AUC={scores['auc_roc']:.4f}\n")

    logger.info(f"✅ Отчёт сохранён в {csv_file}")

    return json_file, csv_file


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    """
    Основной скрипт оценки
    """
    logger.info("🚀 НАЧАЛО IEEE-CIS EVALUATION")
    logger.info("=" * 80)

    try:
        # 1. Скачиваем датасет
        logger.info("\n📋 ЭТАП 1: Скачивание датасета")
        train_df, test_df = download_ieee_cis_dataset()
        logger.info(f"✅ Loaded: train={len(train_df)}, test={len(test_df)}")

        # 2. Предварительная обработка
        logger.info("\n📋 ЭТАП 2: Предварительная обработка")
        train_df_processed = preprocess_ieee_cis(train_df)
        test_df_processed = preprocess_ieee_cis(test_df)

        # 3. Извлечение признаков
        logger.info("\n📋 ЭТАП 3: Извлечение признаков")
        X_train = extract_features_ieee_cis(train_df_processed)
        X_test = extract_features_ieee_cis(test_df_processed)
        y_test = test_df_processed['isFraud'].values if 'isFraud' in test_df_processed else np.zeros(len(X_test))

        # 4. Загружаем переобученные модели
        logger.info("\n📋 ЭТАП 4: Загрузка переобученных ML моделей")
        import pickle
        models_dir = Path(__file__).parent.parent.parent / "data" / "models"

        with open(models_dir / "xgboost_model.pkl", "rb") as f:
            xgb_model = pickle.load(f)
        with open(models_dir / "rf_model.pkl", "rb") as f:
            rf_model = pickle.load(f)
        with open(models_dir / "iso_model.pkl", "rb") as f:
            iso_model = pickle.load(f)
        with open(models_dir / "meta_model.pkl", "rb") as f:
            meta_model = pickle.load(f)
        with open(models_dir / "scaler.pkl", "rb") as f:
            scaler = pickle.load(f)

        logger.info("✅ Все модели загружены успешно!")

        # 5. Делаем предсказания
        logger.info("\n📋 ЭТАП 5: Предсказания на тестовом наборе")

        # Используем скейлер который был использован при обучении
        X_test_scaled = scaler.transform(X_test)

        # Убираем NaN значения
        X_test_scaled = np.nan_to_num(X_test_scaled, nan=0.0, posinf=0.0, neginf=0.0)

        # Получаем предсказания от каждой модели
        xgb_proba = xgb_model.predict_proba(X_test_scaled)[:, 1]
        rf_proba = rf_model.predict_proba(X_test_scaled)[:, 1]
        iso_scores = -iso_model.score_samples(X_test_scaled)
        iso_scores = (iso_scores - iso_scores.min()) / (iso_scores.max() - iso_scores.min())

        # Meta-learner
        meta_X = np.column_stack([xgb_proba, rf_proba, iso_scores])
        meta_proba = meta_model.predict_proba(meta_X)[:, 1]

        # Ensemble
        ensemble_proba = xgb_proba * 0.3 + rf_proba * 0.25 + iso_scores * 0.2 + meta_proba * 0.25

        logger.info(f"✅ Предсказания выполнены для {len(X_test)} транзакций")

        # 6. Оценка результатов
        logger.info("\n📋 ЭТАП 6: Оценка метрик")

        model_predictions = {
            'XGBoost': xgb_proba,
            'RandomForest': rf_proba,
            'IsolationForest': iso_scores,
            'MetaLearner': meta_proba,
        }

        results = evaluate_models(X_test_scaled, y_test, model_predictions)

        # Добавляем ensemble результаты
        ensemble_pred = (ensemble_proba >= 0.5).astype(int)
        ensemble_f1 = f1_score(y_test, ensemble_pred, average='weighted')
        ensemble_auc = roc_auc_score(y_test, ensemble_proba)
        results['ensemble'] = {'f1_score': float(ensemble_f1), 'auc_roc': float(ensemble_auc)}

        # 7. Тестирование latency
        logger.info("\n📋 ЭТАП 7: Тестирование latency")

        class SimplePredictor:
            def __init__(self, models):
                self.models = models
                self.xgb = models['xgb']
                self.rf = models['rf']
                self.iso = models['iso']
                self.meta = models['meta']
                self.scaler = models['scaler']

            def predict(self, X):
                X_scaled = self.scaler.transform(X)
                X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)
                xgb_p = self.xgb.predict_proba(X_scaled)[:, 1]
                rf_p = self.rf.predict_proba(X_scaled)[:, 1]
                iso_s = -self.iso.score_samples(X_scaled)
                iso_s = (iso_s - iso_s.min()) / (iso_s.max() - iso_s.min())
                meta_X = np.column_stack([xgb_p, rf_p, iso_s])
                meta_X = np.nan_to_num(meta_X, nan=0.0, posinf=0.0, neginf=0.0)
                meta_p = self.meta.predict_proba(meta_X)[:, 1]
                return xgb_p * 0.3 + rf_p * 0.25 + iso_s * 0.2 + meta_p * 0.25

        simple_pred = SimplePredictor({
            'xgb': xgb_model,
            'rf': rf_model,
            'iso': iso_model,
            'meta': meta_model,
            'scaler': scaler
        })

        latency_results = test_latency(simple_pred, X_test_scaled, n_samples=100)

        # 8. Сохранение результатов
        logger.info("\n📋 ЭТАП 8: Сохранение результатов")

        json_file, csv_file = save_results(results, latency_results)

        logger.info("\n" + "=" * 80)
        logger.info("✅ EVALUATION ЗАВЕРШЕНА УСПЕШНО")
        logger.info(f"📊 Результаты: {json_file}")

    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
