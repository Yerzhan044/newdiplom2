"""
Test endpoints для демонстрации fraud detection
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from backend.config.database import get_db
from backend.config.settings import get_settings
from backend.models.models import User, Account, Transaction, TransactionStatusEnum
from backend.services.fraud_service import FraudService
from backend.services.rule_engine import RuleEngine
from backend.services.transaction_service import TransactionService
from backend.services.claude_service import ClaudeService
from backend.ml.predictor import get_predictor
from backend.ml.feature_engineering import FeatureEngineer

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test", tags=["test"])

settings = get_settings()


@router.post("/fraud-transaction")
def create_test_fraud_transaction(db: Session = Depends(get_db)):
    """
    Создать тестовую fraud транзакцию с высоким fraud score
    для демонстрации BLOCKED статуса
    """
    try:
        # Получаем или создаём тестовых пользователей
        sender = db.query(User).filter(User.name == "Alice Smith").first()
        if not sender:
            sender = User(name="Alice Smith", country="KZ", bank="Kaspi Bank")
            db.add(sender)
            db.commit()
            db.refresh(sender)

        receiver = db.query(User).filter(User.name == "Fraud Tester").first()
        if not receiver:
            receiver = User(name="Fraud Tester", country="US", bank="Demo Bank")
            db.add(receiver)
            db.commit()
            db.refresh(receiver)

        # Получаем счет отправителя
        sender_account = db.query(Account).filter(
            Account.user_id == sender.id,
            Account.currency == "USD"
        ).first()

        if not sender_account:
            sender_account = Account(
                user_id=sender.id,
                account_number="ALICEUSD999",
                currency="USD",
                balance=100000.0,
                is_active=True
            )
            db.add(sender_account)
            db.commit()
            db.refresh(sender_account)

        # Создаём или получаем счет получателя
        receiver_account = db.query(Account).filter(
            Account.user_id == receiver.id,
            Account.currency == "USD"
        ).first()

        if not receiver_account:
            receiver_account = Account(
                user_id=receiver.id,
                account_number="FRAUDUSD999",
                currency="USD",
                balance=0.0,
                is_active=True
            )
            db.add(receiver_account)
            db.commit()
            db.refresh(receiver_account)

        # Создаём fraud транзакцию
        txn = Transaction(
            sender_id=sender.id,
            receiver_id=receiver.id,
            account_id=sender_account.id,
            amount=99999.00,  # Structuring
            currency="USD",
            description="TEST FRAUD - VPN + Geo Mismatch + High Amount",
            ip_address="185.220.101.1",  # Tor IP
            location="US",  # Different from sender country
            device_id="vpn_device",
            status=TransactionStatusEnum.PENDING,
            timestamp=datetime.now()
        )

        db.add(txn)
        db.commit()
        db.refresh(txn)

        logger.info(f"✅ Test fraud транзакция создана: {txn.id}")

        # ML предсказание
        features = FeatureEngineer.extract_features({
            'amount': 99999.00,
            'timestamp': txn.timestamp,
            'sender_country': 'KZ',
            'receiver_country': 'US',
            'ip_address': '185.220.101.1',
            'device_id': 'vpn_device',
        })

        predictor = get_predictor()
        ml_predictions = predictor.predict(features)

        # Rule Engine
        user_history = TransactionService.get_user_transactions(db, sender.id, limit=50)
        patterns = RuleEngine.detect_patterns(db, txn, user_history)
        rule_score = RuleEngine.calculate_rule_engine_score(patterns)

        # Final score
        final_score = (ml_predictions['final_score'] + rule_score) / 2

        logger.info(f"🔴 Fraud Score: {final_score:.2%}")

        # AI explanation
        claude_service = ClaudeService()
        explanation = claude_service.explain_fraud_decision(
            final_score,
            patterns,
            {
                'amount': 99999.00,
                'currency': 'USD',
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

        # Determine status
        if final_score < settings.fraud_threshold_approved:
            status = 'approved'
        elif final_score < settings.fraud_threshold_review:
            status = 'review'
        else:
            status = 'blocked'

        txn.status = TransactionStatusEnum[status.upper()]
        db.commit()

        return {
            "success": True,
            "transaction_id": txn.id,
            "status": status,
            "fraud_score": round(final_score, 4),
            "explanation": explanation[:200] + "..." if len(explanation) > 200 else explanation,
            "patterns": [p['pattern_name'] for p in patterns],
            "message": f"✅ Создана тестовая fraud транзакция с статусом {status.upper()}"
        }

    except Exception as e:
        logger.error(f"❌ Ошибка при создании test fraud: {e}")
        return {
            "success": False,
            "message": f"Ошибка: {str(e)}"
        }
