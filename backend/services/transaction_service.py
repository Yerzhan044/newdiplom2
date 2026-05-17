from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Optional

from backend.models.models import Transaction, User, Account, FraudScore, FraudPattern, TransactionStatusEnum
from backend.schemas.schemas import TransactionCreate


class TransactionService:
    """Сервис для работы с транзакциями"""

    @staticmethod
    def create_transaction(db: Session, transaction_data: TransactionCreate) -> Transaction:
        """Создание новой транзакции"""
        transaction = Transaction(
            sender_id=transaction_data.sender_id,
            receiver_id=transaction_data.receiver_id,
            account_id=transaction_data.account_id,
            amount=transaction_data.amount,
            currency=transaction_data.currency,
            description=transaction_data.description,
            ip_address=transaction_data.ip_address,
            location=transaction_data.location,
            device_id=transaction_data.device_id,
            status=TransactionStatusEnum.PENDING,
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction

    @staticmethod
    def get_transaction_by_id(db: Session, transaction_id: int) -> Optional[Transaction]:
        """Получить транзакцию по ID"""
        return db.query(Transaction).filter(Transaction.id == transaction_id).first()

    @staticmethod
    def get_all_transactions(db: Session, skip: int = 0, limit: int = 100) -> List[Transaction]:
        """Получить все транзакции с пагинацией"""
        return db.query(Transaction).offset(skip).limit(limit).all()

    @staticmethod
    def get_user_transactions(db: Session, user_id: int, limit: int = 50) -> List[Transaction]:
        """Получить все транзакции пользователя (отправленные и полученные)"""
        return db.query(Transaction).filter(
            (Transaction.sender_id == user_id) | (Transaction.receiver_id == user_id)
        ).order_by(Transaction.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_transactions_by_time_range(
        db: Session,
        start_time: datetime,
        end_time: datetime,
        limit: int = 100
    ) -> List[Transaction]:
        """Получить транзакции за временной период"""
        return db.query(Transaction).filter(
            Transaction.timestamp >= start_time,
            Transaction.timestamp <= end_time
        ).order_by(Transaction.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_recent_transactions(db: Session, minutes: int = 60, limit: int = 100) -> List[Transaction]:
        """Получить последние транзакции за N минут"""
        start_time = datetime.utcnow() - timedelta(minutes=minutes)
        return db.query(Transaction).filter(
            Transaction.timestamp >= start_time
        ).order_by(Transaction.timestamp.desc()).limit(limit).all()

    @staticmethod
    def update_transaction_status(db: Session, transaction_id: int, status: TransactionStatusEnum) -> Optional[Transaction]:
        """Обновить статус транзакции"""
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            transaction.status = status
            transaction.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(transaction)
        return transaction

    @staticmethod
    def get_transactions_by_sender(db: Session, sender_id: int, limit: int = 100) -> List[Transaction]:
        """Получить все транзакции отправленные пользователем"""
        return db.query(Transaction).filter(
            Transaction.sender_id == sender_id
        ).order_by(Transaction.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_transactions_by_receiver(db: Session, receiver_id: int, limit: int = 100) -> List[Transaction]:
        """Получить все транзакции полученные пользователем"""
        return db.query(Transaction).filter(
            Transaction.receiver_id == receiver_id
        ).order_by(Transaction.timestamp.desc()).limit(limit).all()

    @staticmethod
    def count_transactions_by_status(db: Session) -> dict:
        """Подсчитать количество транзакций по статусам"""
        result = db.query(
            Transaction.status,
            func.count(Transaction.id).label('count')
        ).group_by(Transaction.status).all()

        stats = {
            "approved": 0,
            "review": 0,
            "blocked": 0,
            "pending": 0,
        }
        for status, count in result:
            if status:
                stats[status.value] = count

        return stats

    @staticmethod
    def get_total_transaction_amount(db: Session) -> float:
        """Получить общую сумму всех транзакций"""
        result = db.query(func.sum(Transaction.amount)).scalar()
        return result or 0.0

    @staticmethod
    def get_average_transaction_amount(db: Session) -> float:
        """Получить среднюю сумму транзакции"""
        result = db.query(func.avg(Transaction.amount)).scalar()
        return result or 0.0

    @staticmethod
    def get_high_value_transactions(db: Session, amount_threshold: float, limit: int = 50) -> List[Transaction]:
        """Получить крупные транзакции выше порога"""
        return db.query(Transaction).filter(
            Transaction.amount >= amount_threshold
        ).order_by(Transaction.amount.desc()).limit(limit).all()

    @staticmethod
    def count_transactions_last_n_minutes(db: Session, minutes: int = 10) -> int:
        """Подсчитать количество транзакций за последние N минут"""
        start_time = datetime.utcnow() - timedelta(minutes=minutes)
        return db.query(func.count(Transaction.id)).filter(
            Transaction.timestamp >= start_time
        ).scalar()

    @staticmethod
    def detect_velocity_attack(db: Session, user_id: int, minutes: int = 10, threshold: int = 50) -> bool:
        """Обнаружить velocity-атаку (50+ транзакций за 10 минут)"""
        count = db.query(func.count(Transaction.id)).filter(
            Transaction.sender_id == user_id,
            Transaction.timestamp >= datetime.utcnow() - timedelta(minutes=minutes)
        ).scalar()
        return count >= threshold
