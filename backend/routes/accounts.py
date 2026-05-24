"""
API для управления аккаунтами и отправки переводов между ними
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
import logging

from backend.config.database import get_db
from backend.models.models import User, Account, Transaction, TransactionStatusEnum
from backend.services.fraud_service import FraudService
from backend.services.rule_engine import RuleEngine
from backend.services.transaction_service import TransactionService
from backend.services.claude_service import ClaudeService
from backend.ml.predictor import get_predictor
from backend.ml.feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


# ═════════════════════════════════════════════════════════
# SCHEMAS
# ═════════════════════════════════════════════════════════

class AccountResponse(BaseModel):
    """Информация о счете"""
    id: int
    user_id: int
    account_number: str
    currency: str
    balance: float
    is_active: bool

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Информация о пользователе с счетами"""
    id: int
    name: str
    country: str
    bank: str
    accounts: List[AccountResponse]

    class Config:
        from_attributes = True


class TransferRequest(BaseModel):
    """Запрос на отправку перевода"""
    sender_account_id: int
    receiver_user_id: int
    amount: float
    description: Optional[str] = "Transfer"


class TransferResponse(BaseModel):
    """Результат отправки перевода"""
    transaction_id: int
    status: str
    fraud_score: float
    explanation: str
    message: str


# ═════════════════════════════════════════════════════════
# ENDPOINTS
# ═════════════════════════════════════════════════════════

@router.get("/")
def get_all_accounts(db: Session = Depends(get_db)):
    """Получить всех пользователей с их счетами"""
    try:
        users = db.query(User).all()
        result = []

        for user in users:
            accounts = db.query(Account).filter(Account.user_id == user.id).all()
            result.append({
                "id": user.id,
                "name": user.name,
                "country": user.country,
                "bank": user.bank,
                "accounts": [
                    {
                        "id": acc.id,
                        "account_number": acc.account_number,
                        "currency": acc.currency,
                        "balance": acc.balance,
                        "is_active": acc.is_active
                    }
                    for acc in accounts
                ]
            })

        return {"success": True, "users": result}
    except Exception as e:
        logger.error(f"❌ Ошибка при получении аккаунтов: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
def get_user_accounts(user_id: int, db: Session = Depends(get_db)):
    """Получить счета конкретного пользователя"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        accounts = db.query(Account).filter(Account.user_id == user_id).all()

        return {
            "success": True,
            "user": {
                "id": user.id,
                "name": user.name,
                "country": user.country,
                "bank": user.bank,
            },
            "accounts": [
                {
                    "id": acc.id,
                    "account_number": acc.account_number,
                    "currency": acc.currency,
                    "balance": acc.balance,
                    "is_active": acc.is_active
                }
                for acc in accounts
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при получении аккаунта: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{sender_account_id}/transfer")
async def send_transfer(
    sender_account_id: int,
    receiver_user_id: int,
    amount: float,
    description: str = "Transfer",
    db: Session = Depends(get_db)
):
    """
    Отправить перевод от одного счета к другому

    Query parameters:
    - sender_account_id: ID счета отправителя
    - receiver_user_id: ID пользователя получателя
    - amount: Сумма
    - description: Описание (optional)
    """
    try:
        # Получаем счет отправителя
        sender_account = db.query(Account).filter(Account.id == sender_account_id).first()
        if not sender_account:
            raise HTTPException(status_code=404, detail="Sender account not found")

        # Получаем пользователя отправителя
        sender = db.query(User).filter(User.id == sender_account.user_id).first()
        if not sender:
            raise HTTPException(status_code=404, detail="Sender user not found")

        # Получаем получателя
        receiver = db.query(User).filter(User.id == receiver_user_id).first()
        if not receiver:
            raise HTTPException(status_code=404, detail="Receiver user not found")

        # Проверяем баланс
        if sender_account.balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        # Получаем или создаём счет получателя в той же валюте
        receiver_account = db.query(Account).filter(
            Account.user_id == receiver_user_id,
            Account.currency == sender_account.currency
        ).first()

        if not receiver_account:
            receiver_account = Account(
                user_id=receiver_user_id,
                account_number=f"{receiver.name.upper().replace(' ', '')}{sender_account.currency}",
                currency=sender_account.currency,
                balance=0.0,
                is_active=True
            )
            db.add(receiver_account)
            db.commit()
            db.refresh(receiver_account)

        # Создаём транзакцию
        txn = Transaction(
            sender_id=sender.id,
            receiver_id=receiver.id,
            account_id=sender_account.id,
            amount=amount,
            currency=sender_account.currency,
            description=description,
            ip_address="127.0.0.1",  # Local network
            location=sender.country,
            device_id="client-app",
            status=TransactionStatusEnum.PENDING,
            timestamp=datetime.now()
        )

        db.add(txn)
        db.commit()
        db.refresh(txn)

        logger.info(f"✅ Создана транзакция: {txn.id}")

        # ═════════════════════════════════════════════════════════
        # ML FRAUD DETECTION
        # ═════════════════════════════════════════════════════════

        # Feature extraction
        features = FeatureEngineer.extract_features({
            'amount': txn.amount,
            'timestamp': txn.timestamp,
            'sender_country': sender.country,
            'receiver_country': receiver.country,
            'ip_address': txn.ip_address,
            'device_id': txn.device_id,
        })

        # ML predictions
        predictor = get_predictor()
        ml_predictions = predictor.predict(features)

        # Rule Engine
        user_history = TransactionService.get_user_transactions(db, sender.id, limit=50)
        patterns = RuleEngine.detect_patterns(db, txn, user_history)
        rule_score = RuleEngine.calculate_rule_engine_score(patterns)

        # Final score
        final_score = (ml_predictions['final_score'] + rule_score) / 2

        # AI explanation
        claude_service = ClaudeService()
        explanation = claude_service.explain_fraud_decision(
            final_score,
            patterns,
            {
                'amount': txn.amount,
                'currency': txn.currency,
                'sender_name': sender.name,
                'sender_country': sender.country,
                'receiver_name': receiver.name,
                'receiver_country': receiver.country,
                'timestamp': txn.timestamp.isoformat(),
            }
        )

        # Save fraud score
        fraud_score = FraudService.create_fraud_score(
            db,
            transaction_id=txn.id,
            xgboost_score=ml_predictions['xgboost_score'],
            random_forest_score=ml_predictions['random_forest_score'],
            lstm_score=ml_predictions['lstm_score'],
            isolation_forest_score=ml_predictions['isolation_forest_score'],
            rule_engine_score=rule_score,
            final_score=final_score,
            explanation=explanation
        )

        # Save patterns
        for pattern in patterns:
            FraudService.add_fraud_pattern(
                db,
                transaction_id=txn.id,
                pattern_name=pattern['pattern_name'],
                pattern_description=pattern['description'],
                confidence=pattern['confidence'],
                details={'rule': pattern['rule']}
            )

        # Determine status (using settings thresholds)
        from backend.config.settings import get_settings
        settings = get_settings()

        if final_score < settings.fraud_threshold_approved:
            status = 'approved'
        elif final_score < settings.fraud_threshold_review:
            status = 'review'
        else:
            status = 'blocked'

        txn.status = TransactionStatusEnum[status.upper()]
        db.commit()

        # Update balances
        sender_account.balance -= amount
        receiver_account.balance += amount
        db.commit()

        logger.info(f"✅ Перевод обработан: {sender.name} -> {receiver.name}")

        return {
            "success": True,
            "transaction_id": txn.id,
            "status": status,
            "fraud_score": round(final_score, 4),
            "explanation": explanation[:200] + "..." if len(explanation) > 200 else explanation,
            "message": f"Перевод {amount} {sender_account.currency} от {sender.name} к {receiver.name}. Статус: {status}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке перевода: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
