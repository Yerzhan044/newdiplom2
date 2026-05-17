"""
Модуль для загрузки обученных ML моделей и выполнения предсказаний

Использует ансамбль из 5 моделей:
- XGBoost
- Random Forest
- Isolation Forest
- LSTM
- Meta-Learner (Logistic Regression)
"""

import numpy as np
import joblib
from pathlib import Path
import logging
from typing import Dict, Tuple, Optional
import tensorflow as tf

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "data" / "models"


class FraudPredictor:
    """Класс для загрузки моделей и выполнения предсказаний"""

    _instance = None  # Для singleton паттерна (одна загрузка моделей)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FraudPredictor, cls).__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if not self._loaded:
            self.load_models()
            self._loaded = True

    def load_models(self):
        """Загрузка всех обученных моделей"""
        logger.info("📂 Загрузка ML моделей...")

        try:
            self.xgb_model = joblib.load(MODELS_DIR / "xgboost_model.joblib")
            logger.info("✅ XGBoost загружена")

            self.rf_model = joblib.load(MODELS_DIR / "randomforest_model.joblib")
            logger.info("✅ Random Forest загружена")

            self.iso_model = joblib.load(MODELS_DIR / "isolation_forest_model.joblib")
            logger.info("✅ Isolation Forest загружена")

            self.lstm_model = tf.keras.models.load_model(
                MODELS_DIR / "lstm_model.h5",
                compile=False
            )
            logger.info("✅ LSTM загружена")

            self.meta_model = joblib.load(MODELS_DIR / "meta_learner.joblib")
            logger.info("✅ Meta-Learner загружена")

            logger.info("✅ Все модели загружены успешно!")

        except FileNotFoundError as e:
            logger.error(f"❌ Модель не найдена: {e}")
            logger.error("   Запусти: python scripts/train_models.py")
            raise

        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке моделей: {e}")
            raise

    def predict(self, features: np.ndarray) -> Dict[str, float]:
        """
        Выполнить предсказание на основе признаков

        Args:
            features: numpy array размером (n_samples, n_features)

        Returns:
            Словарь с оценками всех моделей и финальным score
            {
                'xgboost_score': 0.75,
                'random_forest_score': 0.80,
                'isolation_forest_score': 0.65,
                'lstm_score': 0.70,
                'final_score': 0.72,  # от мета-модели
                'status': 'blocked',  # или 'approved', 'review'
            }
        """

        # Убедимся что features - это numpy array и правильной формы
        if isinstance(features, list):
            features = np.array(features)

        if len(features.shape) == 1:
            features = features.reshape(1, -1)

        try:
            # 1. Предсказания от базовых моделей
            xgb_score = float(self.xgb_model.predict_proba(features)[:, 1][0])

            rf_score = float(self.rf_model.predict_proba(features)[:, 1][0])

            iso_scores = -self.iso_model.score_samples(features)
            iso_normalized = (iso_scores - iso_scores.min()) / (iso_scores.max() - iso_scores.min() + 1e-8)
            iso_score = float(iso_normalized[0])

            # LSTM expects (batch_size, timesteps, features) = (1, 1, 25)
            features_lstm = features.reshape(features.shape[0], 1, features.shape[1])
            lstm_score = float(self.lstm_model.predict(features_lstm, verbose=0)[0, 0])

            # 2. Мета-модель
            X_meta = np.array([[xgb_score, rf_score, iso_score, lstm_score]])
            final_score = float(self.meta_model.predict_proba(X_meta)[:, 1][0])

            # 3. Определение статуса
            from backend.config.settings import get_settings
            settings = get_settings()

            if final_score < settings.fraud_threshold_approved:
                status = "approved"
            elif final_score < settings.fraud_threshold_review:
                status = "review"
            else:
                status = "blocked"

            return {
                'xgboost_score': round(xgb_score, 4),
                'random_forest_score': round(rf_score, 4),
                'isolation_forest_score': round(iso_score, 4),
                'lstm_score': round(lstm_score, 4),
                'final_score': round(final_score, 4),
                'status': status,
            }

        except Exception as e:
            logger.error(f"❌ Ошибка при предсказании: {e}")
            raise

    def predict_batch(self, features_batch: np.ndarray) -> list:
        """
        Выполнить batch предсказания (для нескольких объектов)

        Args:
            features_batch: numpy array размером (batch_size, n_features)

        Returns:
            Список словарей с предсказаниями для каждого объекта
        """

        if len(features_batch.shape) == 1:
            return [self.predict(features_batch)]

        results = []
        for i in range(len(features_batch)):
            results.append(self.predict(features_batch[i:i+1]))

        return results

    @staticmethod
    def get_feature_importance() -> Dict[str, float]:
        """Получить важность признаков из базовых моделей"""
        try:
            xgb_model = joblib.load(MODELS_DIR / "xgboost_model.joblib")
            rf_model = joblib.load(MODELS_DIR / "randomforest_model.joblib")

            xgb_importances = dict(zip(
                range(len(xgb_model.feature_importances_)),
                xgb_model.feature_importances_
            ))

            rf_importances = dict(zip(
                range(len(rf_model.feature_importances_)),
                rf_model.feature_importances_
            ))

            return {
                'xgboost': xgb_importances,
                'random_forest': rf_importances,
            }

        except Exception as e:
            logger.error(f"❌ Ошибка при получении важности признаков: {e}")
            return {}


# Singleton instance
fraud_predictor = None


def get_predictor() -> FraudPredictor:
    """Получить singleton instance предиктора"""
    global fraud_predictor
    if fraud_predictor is None:
        fraud_predictor = FraudPredictor()
    return fraud_predictor
