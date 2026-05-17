from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from backend.config.database import get_db
from backend.models.models import Transaction, User, Account
from backend.schemas.schemas import (
    TransactionCreate,
    TransactionResponse,
    TransactionDetailResponse,
    TransactionStatisticsResponse,
    FraudDetectionMetricsResponse,
)
from backend.services.transaction_service import TransactionService
from backend.services.fraud_service import FraudService

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


# ═════════════════════════════════════════════════════════════════
# TRANSACTION ENDPOINTS
# ═════════════════════════════════════════════════════════════════

@router.post("/create", response_model=TransactionResponse)
def create_transaction(
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db)
):
    """
    Создание новой транзакции

    - **sender_id**: ID отправителя
    - **receiver_id**: ID получателя
    - **account_id**: ID счёта отправителя
    - **amount**: Сумма транзакции (> 0)
    - **currency**: Валюта (KZT, RUB, EUR, USD)
    - **description**: Описание (опционально)
    """
    # Проверка существования пользователей
    sender = db.query(User).filter(User.id == transaction_data.sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")

    receiver = db.query(User).filter(User.id == transaction_data.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    # Проверка существования счёта
    account = db.query(Account).filter(Account.id == transaction_data.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Проверка баланса
    if account.balance < transaction_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Создание транзакции
    transaction = TransactionService.create_transaction(db, transaction_data)

    return transaction


@router.get("/{transaction_id}", response_model=TransactionDetailResponse)
def get_transaction_details(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """
    Получить полные детали транзакции с fraud score и паттернами

    - **transaction_id**: ID транзакции
    """
    transaction = TransactionService.get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction


@router.get("/", response_model=List[TransactionResponse])
def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Получить список всех транзакций с пагинацией

    - **skip**: Количество пропускаемых записей
    - **limit**: Количество возвращаемых записей (макс 1000)
    """
    transactions = TransactionService.get_all_transactions(db, skip, limit)
    return transactions


@router.get("/user/{user_id}", response_model=List[TransactionResponse])
def get_user_transactions(
    user_id: int,
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Получить все транзакции пользователя (отправленные и полученные)

    - **user_id**: ID пользователя
    - **limit**: Максимум записей
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    transactions = TransactionService.get_user_transactions(db, user_id, limit)
    return transactions


@router.get("/recent/", response_model=List[TransactionResponse])
def get_recent_transactions(
    minutes: int = Query(60, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Получить последние транзакции за N минут

    - **minutes**: Количество минут (по умолчанию 60)
    - **limit**: Максимум записей
    """
    transactions = TransactionService.get_recent_transactions(db, minutes, limit)
    return transactions


# ═════════════════════════════════════════════════════════════════
# FRAUD SCORE ENDPOINTS
# ═════════════════════════════════════════════════════════════════

@router.get("/{transaction_id}/fraud-score")
def get_fraud_score(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """
    Получить fraud score для транзакции

    Возвращает:
    - Оценки от каждой модели (XGBoost, Random Forest, LSTM, etc.)
    - Финальный FRAUD SCORE (0.0 - 1.0)
    - Объяснение от Claude AI
    - Статус (✅ Одобрено / ⚠️ На проверку / ❌ Заблокировано)
    """
    transaction = TransactionService.get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    fraud_score = FraudService.get_fraud_score_by_transaction(db, transaction_id)
    if not fraud_score:
        raise HTTPException(status_code=404, detail="Fraud score not computed yet")

    return fraud_score


@router.get("/{transaction_id}/patterns")
def get_fraud_patterns(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """
    Получить все обнаруженные паттерны мошенничества для транзакции

    Возвращает список паттернов:
    1. Регулярные поступления от разных людей
    2. Одинаковые суммы от множества людей
    3. Ночные переводы (02:00-05:00)
    и т.д.
    """
    transaction = TransactionService.get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    patterns = FraudService.get_fraud_patterns_by_transaction(db, transaction_id)
    return patterns


# ═════════════════════════════════════════════════════════════════
# STATISTICS ENDPOINTS
# ═════════════════════════════════════════════════════════════════

@router.get("/stats/general", response_model=TransactionStatisticsResponse)
def get_transaction_statistics(db: Session = Depends(get_db)):
    """
    Получить общую статистику по транзакциям

    Возвращает:
    - Всего транзакций
    - Одобрено / На проверку / Заблокировано
    - Процент одобрения
    - Общая сумма
    - Средняя сумма
    """
    stats = FraudService.get_statistics(db)

    total = stats["total_transactions"]
    approved = stats["approved_count"]
    review = stats["review_count"]
    blocked = stats["blocked_count"]
    total_amount = stats["total_amount"]
    avg_amount = total_amount / total if total > 0 else 0

    return TransactionStatisticsResponse(
        total_transactions=total,
        approved_count=approved,
        review_count=review,
        blocked_count=blocked,
        total_amount=total_amount,
        average_amount=avg_amount,
        approval_rate=stats["approval_rate"],
        block_rate=stats["block_rate"],
    )


@router.get("/stats/fraud-metrics", response_model=FraudDetectionMetricsResponse)
def get_fraud_detection_metrics(db: Session = Depends(get_db)):
    """
    Получить метрики обнаружения мошенничества

    Возвращает:
    - Всего проанализировано транзакций
    - Обнаружено мошенничества
    - Процент обнаружения
    - Средний fraud score
    - Топ паттерны мошенничества
    """
    stats = FraudService.get_statistics(db)
    top_patterns = FraudService.get_top_fraud_patterns(db, limit=10)

    total = stats["total_transactions"]
    blocked = stats["blocked_count"]
    detection_rate = (blocked / total * 100) if total > 0 else 0

    return FraudDetectionMetricsResponse(
        transactions_analyzed=total,
        frauds_detected=blocked,
        detection_rate=round(detection_rate, 2),
        average_fraud_score=stats["average_fraud_score"],
        top_patterns=top_patterns,
    )


@router.get("/stats/high-risk-users")
def get_high_risk_users(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Получить список пользователей с высоким риском

    (Много заблокированных транзакций и высокий average fraud score)
    """
    return FraudService.get_high_risk_users(db, limit)


@router.get("/stats/top-patterns")
def get_top_patterns(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Получить топ обнаруженных паттернов мошенничества
    """
    return FraudService.get_top_fraud_patterns(db, limit)


# ═════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═════════════════════════════════════════════════════════════════

@router.get("/health")
def health_check():
    """Проверка здоровья API"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow(),
        "service": "Fraud Detection System API"
    }
