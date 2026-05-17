"""
Автоматический генератор реалистичных транзакций

Генерирует транзакции каждые N секунд и обрабатывает их через ML + Rules
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
import random

from backend.config.database import SessionLocal
from backend.models.models import User, Account, Transaction, TransactionStatusEnum
from backend.services.claude_service import ClaudeService
from backend.services.rule_engine import RuleEngine
from backend.services.fraud_service import FraudService
from backend.services.transaction_service import TransactionService
from backend.ml.predictor import get_predictor
from backend.ml.feature_engineering import FeatureEngineer
from backend.routes.websocket import (
    send_transaction_update,
    send_statistics_update,
)

logger = logging.getLogger(__name__)


class TransactionGenerator:
    """Генератор и обработчик транзакций"""

    def __init__(self, interval_seconds: int = 10):
        """
        Args:
            interval_seconds: Интервал между генерациями (секунды)
        """
        self.interval = interval_seconds
        self.claude_service = ClaudeService()
        self.is_running = False

    async def start(self):
        """Начать генерацию транзакций"""
        self.is_running = True
        logger.info(f"🚀 Генератор транзакций запущен (интервал: {self.interval}s)")

        while self.is_running:
            try:
                await self.generate_and_process_transaction()
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error(f"❌ Ошибка при генерации: {e}")
                await asyncio.sleep(self.interval)

    async def stop(self):
        """Остановить генерацию"""
        self.is_running = False
        logger.info("🛑 Генератор транзакций остановлен")

    async def generate_and_process_transaction(self):
        """Генерировать транзакцию и обработать её через ML + Rules"""

        db = SessionLocal()

        try:
            # 1. Генерируем данные транзакции через Claude
            transaction_data = self.claude_service.generate_realistic_transaction()

            # 2. Получаем или создаём пользователей
            sender = self._get_or_create_user(
                db,
                transaction_data['sender_name'],
                transaction_data['sender_country'],
                transaction_data['sender_bank']
            )

            receiver = self._get_or_create_user(
                db,
                transaction_data['receiver_name'],
                transaction_data['receiver_country'],
                transaction_data['receiver_bank']
            )

            # 3. Получаем счёты
            sender_account = self._get_or_create_account(
                db, sender, transaction_data['currency']
            )

            # 4. Создаём транзакцию
            txn = Transaction(
                sender_id=sender.id,
                receiver_id=receiver.id,
                account_id=sender_account.id,
                amount=transaction_data['amount'],
                currency=transaction_data['currency'],
                description=transaction_data['description'],
                ip_address=f"192.168.{random.randint(0,255)}.{random.randint(0,255)}",
                location=transaction_data['sender_country'],
                device_id=f"device_{random.randint(1000, 9999)}",
                status=TransactionStatusEnum.PENDING,
            )

            db.add(txn)
            db.commit()
            db.refresh(txn)

            logger.info(f"✅ Транзакция создана: {txn.id}")

            # 5. ML предсказание
            features = FeatureEngineer.extract_features({
                'amount': txn.amount,
                'timestamp': txn.timestamp,
                'sender_country': sender.country,
                'receiver_country': receiver.country,
                'ip_address': txn.ip_address,
                'device_id': txn.device_id,
            })

            predictor = get_predictor()
            ml_predictions = predictor.predict(features)

            # 6. Rule Engine
            user_history = TransactionService.get_user_transactions(db, sender.id, limit=50)
            patterns = RuleEngine.detect_patterns(db, txn, user_history)
            rule_score = RuleEngine.calculate_rule_engine_score(patterns)

            # 7. Сохраняем fraud score
            final_score = (ml_predictions['final_score'] + rule_score) / 2

            explanation = self.claude_service.explain_fraud_decision(
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

            # 8. Сохраняем паттерны
            for pattern in patterns:
                FraudService.add_fraud_pattern(
                    db,
                    transaction_id=txn.id,
                    pattern_name=pattern['pattern_name'],
                    pattern_description=pattern['description'],
                    confidence=pattern['confidence'],
                    details={'rule': pattern['rule']}
                )

            # 9. Отправляем update через WebSocket
            await send_transaction_update({
                'transaction_id': txn.id,
                'sender': transaction_data['sender_name'],
                'receiver': transaction_data['receiver_name'],
                'amount': txn.amount,
                'currency': txn.currency,
                'fraud_score': final_score,
                'status': txn.status.value,
                'patterns': [p['pattern_name'] for p in patterns],
                'explanation': explanation[:200] + "..." if len(explanation) > 200 else explanation,
            })

            # 10. Обновляем статистику
            stats = FraudService.get_statistics(db)
            await send_statistics_update({
                'total': stats['total_transactions'],
                'approved': stats['approved_count'],
                'review': stats['review_count'],
                'blocked': stats['blocked_count'],
            })

            logger.info(f"✅ Транзакция {txn.id} обработана (score: {final_score:.3f})")

        except Exception as e:
            logger.error(f"❌ Ошибка обработки транзакции: {e}")

        finally:
            db.close()

    @staticmethod
    def _get_or_create_user(db: Session, name: str, country: str, bank: str) -> User:
        """Получить или создать пользователя"""
        # Ищем по имени (упрощённо)
        user = db.query(User).filter(User.name == name).first()

        if not user:
            user = User(name=name, country=country, bank=bank)
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"👤 Создан пользователь: {name}")

        return user

    @staticmethod
    def _get_or_create_account(db: Session, user: User, currency: str) -> Account:
        """Получить или создать счёт"""
        account = db.query(Account).filter(
            Account.user_id == user.id,
            Account.currency == currency
        ).first()

        if not account:
            # Генерируем IBAN
            iban = f"KZ{random.randint(10000000, 99999999)}{random.randint(10000000, 99999999)}"
            account = Account(
                user_id=user.id,
                account_number=iban,
                currency=currency,
                balance=random.uniform(10000, 1000000),
                is_active=True
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            logger.info(f"🏧 Создан счёт: {iban}")

        return account


# Глобальный генератор
_generator: Optional[TransactionGenerator] = None


async def get_generator() -> TransactionGenerator:
    """Получить глобальный экземпляр генератора"""
    global _generator
    if _generator is None:
        _generator = TransactionGenerator(interval_seconds=10)
    return _generator


async def start_transaction_generator():
    """Запустить генератор транзакций"""
    generator = await get_generator()
    await generator.start()


async def stop_transaction_generator():
    """Остановить генератор"""
    global _generator
    if _generator:
        await _generator.stop()
        _generator = None
