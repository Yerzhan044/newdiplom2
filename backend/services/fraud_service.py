from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
from datetime import datetime

from backend.models.models import FraudScore, FraudPattern, Transaction, TransactionStatusEnum
from backend.config.settings import get_settings


settings = get_settings()


class FraudService:
    """Сервис для работы с fraud scoring и паттернами"""

    @staticmethod
    def create_fraud_score(
        db: Session,
        transaction_id: int,
        xgboost_score: Optional[float],
        random_forest_score: Optional[float],
        lstm_score: Optional[float],
        isolation_forest_score: Optional[float],
        rule_engine_score: Optional[float],
        final_score: float,
        explanation: Optional[str] = None
    ) -> FraudScore:
        """Создание оценки мошенничества"""
        fraud_score = FraudScore(
            transaction_id=transaction_id,
            xgboost_score=xgboost_score,
            random_forest_score=random_forest_score,
            lstm_score=lstm_score,
            isolation_forest_score=isolation_forest_score,
            rule_engine_score=rule_engine_score,
            final_score=final_score,
            explanation=explanation,
        )
        db.add(fraud_score)
        db.commit()
        db.refresh(fraud_score)

        # Обновить статус транзакции на основе final_score
        FraudService.update_transaction_status_by_score(db, transaction_id, final_score)

        return fraud_score

    @staticmethod
    def get_fraud_score_by_transaction(db: Session, transaction_id: int) -> Optional[FraudScore]:
        """Получить fraud score по ID транзакции"""
        return db.query(FraudScore).filter(FraudScore.transaction_id == transaction_id).first()

    @staticmethod
    def add_fraud_pattern(
        db: Session,
        transaction_id: int,
        pattern_name: str,
        pattern_description: str,
        confidence: float,
        details: Optional[dict] = None
    ) -> FraudPattern:
        """Добавить обнаруженный паттерн мошенничества"""
        fraud_pattern = FraudPattern(
            transaction_id=transaction_id,
            pattern_name=pattern_name,
            pattern_description=pattern_description,
            confidence=confidence,
            details=details or {},
        )
        db.add(fraud_pattern)
        db.commit()
        db.refresh(fraud_pattern)
        return fraud_pattern

    @staticmethod
    def get_fraud_patterns_by_transaction(db: Session, transaction_id: int) -> List[FraudPattern]:
        """Получить все паттерны для транзакции"""
        return db.query(FraudPattern).filter(FraudPattern.transaction_id == transaction_id).all()

    @staticmethod
    def get_all_fraud_patterns(db: Session, limit: int = 100) -> List[FraudPattern]:
        """Получить все обнаруженные паттерны"""
        return db.query(FraudPattern).order_by(FraudPattern.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_fraud_patterns_by_name(db: Session, pattern_name: str, limit: int = 100) -> List[FraudPattern]:
        """Получить паттерны по названию"""
        return db.query(FraudPattern).filter(
            FraudPattern.pattern_name == pattern_name
        ).order_by(FraudPattern.confidence.desc()).limit(limit).all()

    @staticmethod
    def update_transaction_status_by_score(db: Session, transaction_id: int, final_score: float) -> Transaction:
        """Обновить статус транзакции на основе fraud score"""
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

        if transaction:
            if final_score < settings.fraud_threshold_approved:
                transaction.status = TransactionStatusEnum.APPROVED
            elif final_score < settings.fraud_threshold_review:
                transaction.status = TransactionStatusEnum.REVIEW
            else:
                transaction.status = TransactionStatusEnum.BLOCKED

            transaction.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(transaction)

        return transaction

    @staticmethod
    def get_statistics(db: Session) -> Dict:
        """Получить статистику мошенничества"""
        total_transactions = db.query(func.count(Transaction.id)).scalar()

        approved = db.query(func.count(Transaction.id)).filter(
            Transaction.status == TransactionStatusEnum.APPROVED
        ).scalar()
        review = db.query(func.count(Transaction.id)).filter(
            Transaction.status == TransactionStatusEnum.REVIEW
        ).scalar()
        blocked = db.query(func.count(Transaction.id)).filter(
            Transaction.status == TransactionStatusEnum.BLOCKED
        ).scalar()

        avg_fraud_score = db.query(func.avg(FraudScore.final_score)).scalar()
        total_amount = db.query(func.sum(Transaction.amount)).scalar()

        blocked_amount = db.query(func.sum(Transaction.amount)).filter(
            Transaction.status == TransactionStatusEnum.BLOCKED
        ).scalar()

        return {
            "total_transactions": total_transactions or 0,
            "approved_count": approved or 0,
            "review_count": review or 0,
            "blocked_count": blocked or 0,
            "approval_rate": round((approved or 0) / (total_transactions or 1) * 100, 2),
            "block_rate": round((blocked or 0) / (total_transactions or 1) * 100, 2),
            "average_fraud_score": round(avg_fraud_score or 0, 3),
            "total_amount": round(total_amount or 0, 2),
            "total_saved": round(blocked_amount or 0, 2),
        }

    @staticmethod
    def get_top_fraud_patterns(db: Session, limit: int = 10) -> List[Dict]:
        """Получить топ паттернов мошенничества"""
        patterns = db.query(
            FraudPattern.pattern_name,
            func.count(FraudPattern.id).label('count'),
            func.avg(FraudPattern.confidence).label('avg_confidence')
        ).group_by(FraudPattern.pattern_name).order_by(
            func.count(FraudPattern.id).desc()
        ).limit(limit).all()

        return [
            {
                "name": pattern[0],
                "count": pattern[1],
                "confidence": round(pattern[2], 3)
            }
            for pattern in patterns
        ]

    @staticmethod
    def get_high_risk_users(db: Session, limit: int = 20) -> List[Dict]:
        """Получить пользователей с высоким риском (много заблокированных транзакций)"""
        result = db.query(
            Transaction.sender_id,
            func.count(Transaction.id).label('blocked_count'),
            func.avg(FraudScore.final_score).label('avg_score')
        ).join(
            FraudScore, Transaction.id == FraudScore.transaction_id
        ).filter(
            Transaction.status == TransactionStatusEnum.BLOCKED
        ).group_by(Transaction.sender_id).order_by(
            func.count(Transaction.id).desc()
        ).limit(limit).all()

        return [
            {
                "user_id": user_id,
                "blocked_transactions": count,
                "average_fraud_score": round(avg_score, 3)
            }
            for user_id, count, avg_score in result
        ]

    @staticmethod
    def get_false_positive_rate(db: Session, days: int = 30) -> float:
        """Получить rate false positive (заблокировано, но затем одобрено)"""
        # Логика: если позже пришла актуализирующая информация и статус изменился
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        total_blocked = db.query(func.count(Transaction.id)).filter(
            Transaction.status == TransactionStatusEnum.BLOCKED,
            Transaction.created_at >= cutoff_date
        ).scalar()

        if total_blocked == 0:
            return 0.0

        # В реальной системе нужно отслеживать переводы статуса
        # Здесь это упрощенный пример
        return 0.0
