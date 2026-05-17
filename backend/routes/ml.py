"""
API endpoints для ML predictions (интеграция моделей в FastAPI)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import numpy as np
from typing import Optional

from backend.config.database import get_db
from backend.models.models import Transaction, FraudScore, FraudPattern, TransactionStatusEnum
from backend.ml.predictor import get_predictor
from backend.ml.feature_engineering import FeatureEngineer
from backend.services.fraud_service import FraudService
from pydantic import BaseModel

router = APIRouter(prefix="/api/ml", tags=["machine-learning"])


# ═════════════════════════════════════════════════════
# REQUEST/RESPONSE SCHEMAS
# ═════════════════════════════════════════════════════

class PredictFraudRequest(BaseModel):
    """Запрос для предсказания fraud score по признакам"""
    amount: float
    hour: int
    dayofweek: int
    day: int
    month: int
    is_night: int = 0
    sender_country: str = "KZ"
    receiver_country: str = "KZ"
    is_international: int = 0
    num_transactions: int = 0
    unique_receivers: int = 0
    unique_countries: int = 0
    ip_address: str = "0.0.0.0"
    device_id: str = "unknown"


class PredictFraudResponse(BaseModel):
    """Ответ с fraud score"""
    xgboost_score: float
    random_forest_score: float
    isolation_forest_score: float
    lstm_score: float
    final_score: float
    status: str  # "approved", "review", "blocked"
    explanation: Optional[str] = None


class TransactionPredictRequest(BaseModel):
    """Запрос для предсказания по ID транзакции"""
    transaction_id: int


# ═════════════════════════════════════════════════════
# ENDPOINTS
# ═════════════════════════════════════════════════════

@router.post("/predict", response_model=PredictFraudResponse)
def predict_fraud(
    request: PredictFraudRequest,
):
    """
    Предсказать fraud score по признакам транзакции

    Входные данные:
    - amount: сумма транзакции
    - hour, dayofweek, day, month: временные признаки
    - sender_country, receiver_country: коды стран (KZ, RU, DE, US)
    - is_international: 0 или 1
    - num_transactions: кол-во транзакций пользователя
    - unique_receivers: кол-во уникальных получателей
    - unique_countries: кол-во стран-получателей

    Возвращает:
    - Оценки от каждой модели (0.0-1.0)
    - final_score: итоговая оценка от мета-модели
    - status: "approved" / "review" / "blocked"
    """

    try:
        # Подготовка признаков
        transaction_data = {
            'amount': request.amount,
            'timestamp': __import__('datetime').datetime.utcnow(),
            'sender_country': request.sender_country,
            'receiver_country': request.receiver_country,
            'ip_address': request.ip_address,
            'device_id': request.device_id,
        }

        # Извлечение признаков
        features = FeatureEngineer.extract_features(transaction_data)

        # Получение предсказаний
        predictor = get_predictor()
        predictions = predictor.predict(features)

        return PredictFraudResponse(
            xgboost_score=predictions['xgboost_score'],
            random_forest_score=predictions['random_forest_score'],
            isolation_forest_score=predictions['isolation_forest_score'],
            lstm_score=predictions['lstm_score'],
            final_score=predictions['final_score'],
            status=predictions['status'],
            explanation=f"Fraud score: {predictions['final_score']:.1%}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML prediction error: {str(e)}")


@router.post("/predict-transaction")
def predict_transaction(
    request: TransactionPredictRequest,
    db: Session = Depends(get_db)
):
    """
    Предсказать fraud score для сохранённой транзакции

    Процесс:
    1. Загружает транзакцию из БД
    2. Извлекает признаки
    3. Выполняет предсказание
    4. Сохраняет результат в БД (FraudScore)
    5. Обновляет статус транзакции
    """

    try:
        # Получить транзакцию
        transaction = db.query(Transaction).filter(
            Transaction.id == request.transaction_id
        ).first()

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Подготовить данные для признаков
        transaction_data = {
            'amount': transaction.amount,
            'timestamp': transaction.timestamp,
            'sender_country': transaction.sender.country,
            'receiver_country': transaction.receiver.country,
            'ip_address': transaction.ip_address or '0.0.0.0',
            'device_id': transaction.device_id or 'unknown',
        }

        # Извлечение признаков
        features = FeatureEngineer.extract_features(transaction_data)

        # Предсказание
        predictor = get_predictor()
        predictions = predictor.predict(features)

        # Сохранение результата в БД
        fraud_score = FraudService.create_fraud_score(
            db,
            transaction_id=request.transaction_id,
            xgboost_score=predictions['xgboost_score'],
            random_forest_score=predictions['random_forest_score'],
            lstm_score=predictions['lstm_score'],
            isolation_forest_score=predictions['isolation_forest_score'],
            rule_engine_score=None,  # TODO: Rule Engine
            final_score=predictions['final_score'],
            explanation=f"ML Ensemble Prediction: {predictions['final_score']:.1%} fraud probability"
        )

        return {
            "transaction_id": request.transaction_id,
            "fraud_score": fraud_score,
            "status": predictions['status'],
            "message": f"Transaction {'blocked' if predictions['status'] == 'blocked' else 'approved'}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML prediction error: {str(e)}")


@router.get("/model-info")
def get_model_info():
    """
    Получить информацию об используемых моделях
    """
    return {
        "models": [
            {
                "name": "XGBoost",
                "type": "Gradient Boosting",
                "purpose": "Транзакционные паттерны",
                "weight": 0.25
            },
            {
                "name": "Random Forest",
                "type": "Ensemble",
                "purpose": "Поведенческие аномалии",
                "weight": 0.25
            },
            {
                "name": "Isolation Forest",
                "type": "Anomaly Detection",
                "purpose": "Статистические аномалии",
                "weight": 0.20
            },
            {
                "name": "LSTM",
                "type": "Neural Network (TensorFlow)",
                "purpose": "Временные последовательности",
                "weight": 0.20
            },
            {
                "name": "Logistic Regression",
                "type": "Meta-Learner",
                "purpose": "Объединение всех моделей",
                "weight": 1.0
            }
        ],
        "feature_count": 25,
        "training_dataset": "IEEE-CIS Fraud Detection",
        "dataset_size": "590,540 transactions",
        "fraud_rate": "3.48%"
    }


@router.get("/feature-names")
def get_feature_names():
    """
    Получить названия признаков (для интерпретации)
    """
    names = FeatureEngineer.get_feature_names()
    return {
        "feature_names": names,
        "feature_count": len(names),
    }


@router.post("/health")
def ml_health_check():
    """
    Проверка здоровья ML моделей
    """
    try:
        predictor = get_predictor()

        # Тестовое предсказание
        test_features = np.random.randn(1, 25).astype(np.float32)
        predictions = predictor.predict(test_features)

        return {
            "status": "healthy",
            "models_loaded": True,
            "test_prediction": predictions['final_score'],
            "message": "All ML models are operational"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "models_loaded": False,
            "message": "ML models failed to load"
        }
