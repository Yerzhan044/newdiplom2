"""
Обработка загруженных CSV файлов с транзакциями
"""

from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
import csv
import io
from datetime import datetime
import random

from backend.config.database import get_db
from backend.models.models import User, Account, Transaction, TransactionStatusEnum
from backend.services.transaction_service import TransactionService
from backend.services.fraud_service import FraudService
from backend.services.rule_engine import RuleEngine
from backend.services.claude_service import ClaudeService
from backend.ml.predictor import get_predictor
from backend.ml.feature_engineering import FeatureEngineer

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/csv", tags=["csv"])


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Загрузить CSV файл и обработать транзакции

    CSV должен содержать колонки:
    - sender_name: Имя отправителя
    - sender_country: Страна отправителя
    - sender_ip: IP адрес отправителя
    - receiver_name: Имя получателя
    - receiver_country: Страна получателя
    - receiver_ip: IP адрес получателя
    - amount: Сумма
    - currency: Валюта
    - timestamp: Время транзакции
    """

    try:
        # Читаем CSV
        contents = await file.read()

        # Пытаемся разные кодировки
        text_data = None
        for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
            try:
                text_data = contents.decode(encoding)
                logger.info(f"✅ CSV прочитан с кодировкой: {encoding}")
                break
            except:
                continue

        if text_data is None:
            raise ValueError("Не удалось прочитать CSV ни в одной из поддерживаемых кодировок (utf-8, utf-16, latin-1, cp1252)")

        csv_reader = csv.DictReader(io.StringIO(text_data))

        results = []
        claude_service = ClaudeService()
        predictor = get_predictor()

        for row_idx, row in enumerate(csv_reader, 1):
            try:
                # Парсим данные из CSV
                sender_name = row.get('sender_name', f'Sender {row_idx}').strip()
                sender_country = row.get('sender_country', 'KZ').strip().upper()
                sender_ip = row.get('sender_ip', f'192.168.{random.randint(0,255)}.{random.randint(0,255)}').strip()

                receiver_name = row.get('receiver_name', f'Receiver {row_idx}').strip()
                receiver_country = row.get('receiver_country', 'US').strip().upper()
                receiver_ip = row.get('receiver_ip', f'192.168.{random.randint(0,255)}.{random.randint(0,255)}').strip()

                amount = float(row.get('amount', 1000))
                currency = row.get('currency', 'USD').strip().upper()

                try:
                    timestamp = datetime.fromisoformat(row.get('timestamp', datetime.utcnow().isoformat()))
                except:
                    timestamp = datetime.utcnow()

                # Создаём пользователей
                sender = _get_or_create_user(db, sender_name, sender_country, 'CSV Import')
                receiver = _get_or_create_user(db, receiver_name, receiver_country, 'CSV Import')

                # Создаём счёты
                sender_account = _get_or_create_account(db, sender, currency)

                # Создаём транзакцию
                txn = Transaction(
                    sender_id=sender.id,
                    receiver_id=receiver.id,
                    account_id=sender_account.id,
                    amount=amount,
                    currency=currency,
                    description=f'CSV Import - Row {row_idx}',
                    ip_address=sender_ip,
                    location=sender_country,
                    device_id=f'csv_{row_idx}',
                    status=TransactionStatusEnum.PENDING,
                    timestamp=timestamp,
                )

                db.add(txn)
                db.commit()
                db.refresh(txn)

                # ML предсказание
                features = FeatureEngineer.extract_features({
                    'amount': txn.amount,
                    'timestamp': txn.timestamp,
                    'sender_country': sender.country,
                    'receiver_country': receiver.country,
                    'ip_address': txn.ip_address,
                    'device_id': txn.device_id,
                })

                ml_predictions = predictor.predict(features)

                # Rule Engine
                user_history = TransactionService.get_user_transactions(db, sender.id, limit=50)
                patterns = RuleEngine.detect_patterns(db, txn, user_history)
                rule_score = RuleEngine.calculate_rule_engine_score(patterns)

                # Финальный score
                final_score = (ml_predictions['final_score'] + rule_score) / 2

                # AI объяснение
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

                # Сохраняем fraud score
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

                # Сохраняем паттерны
                for pattern in patterns:
                    FraudService.add_fraud_pattern(
                        db,
                        transaction_id=txn.id,
                        pattern_name=pattern['pattern_name'],
                        pattern_description=pattern['description'],
                        confidence=pattern['confidence'],
                        details={'rule': pattern['rule']}
                    )

                # Определяем статус (используем settings)
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

                results.append({
                    'row': row_idx,
                    'sender': sender_name,
                    'receiver': receiver_name,
                    'amount': amount,
                    'currency': currency,
                    'fraud_score': round(final_score, 4),
                    'status': status,
                    'patterns': [p['pattern_name'] for p in patterns],
                    'explanation': explanation[:150] + '...' if len(explanation) > 150 else explanation,
                    'error': None
                })

                logger.info(f"✅ Строка {row_idx}: {sender_name} -> {receiver_name} (score: {final_score:.3f})")

            except Exception as e:
                logger.error(f"❌ Ошибка в строке {row_idx}: {e}")
                results.append({
                    'row': row_idx,
                    'error': str(e),
                    'sender': row.get('sender_name', 'N/A'),
                    'receiver': row.get('receiver_name', 'N/A'),
                })

        return {
            'success': True,
            'message': f'Обработано {len(results)} транзакций',
            'results': results
        }

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки CSV: {e}")
        return {
            'success': False,
            'message': f'Ошибка: {str(e)}',
            'results': []
        }


@staticmethod
def _get_or_create_user(db: Session, name: str, country: str, bank: str):
    """Получить или создать пользователя"""
    user = db.query(User).filter(User.name == name).first()

    if not user:
        user = User(name=name, country=country, bank=bank)
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


@staticmethod
def _get_or_create_account(db: Session, user, currency: str):
    """Получить или создать счёт"""
    account = db.query(Account).filter(
        Account.user_id == user.id,
        Account.currency == currency
    ).first()

    if not account:
        iban = f"CSV{random.randint(10000000, 99999999)}{random.randint(10000000, 99999999)}"
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

    return account
