from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from backend.config.database import Base


class User(Base):
    """Пользователь (отправитель или получатель)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    country = Column(String(2), nullable=False)  # ISO 3166-1 alpha-2 (KZ, RU, DE, US)
    bank = Column(String(50), nullable=False)  # Kaspi Bank, Halyk Bank, Сбербанк, Deutsche Bank, Stripe
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    transactions_sent = relationship("Transaction", foreign_keys="Transaction.sender_id", back_populates="sender")
    transactions_received = relationship("Transaction", foreign_keys="Transaction.receiver_id", back_populates="receiver")

    def __repr__(self):
        return f"<User {self.name} ({self.country})>"


class Account(Base):
    """Банковский счёт пользователя"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_number = Column(String(34), nullable=False, unique=True, index=True)  # IBAN
    currency = Column(String(3), nullable=False)  # KZT, RUB, EUR, USD
    balance = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

    def __repr__(self):
        return f"<Account {self.account_number} ({self.currency})>"


class TransactionStatusEnum(str, enum.Enum):
    APPROVED = "approved"       # ✅ Одобрено (score < 0.4)
    REVIEW = "review"           # ⚠️ На проверку (0.4 <= score < 0.7)
    BLOCKED = "blocked"         # ❌ Заблокировано (score >= 0.7)
    PENDING = "pending"         # Ожидание обработки


class Transaction(Base):
    """Финансовая транзакция"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)

    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)  # KZT, RUB, EUR, USD

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    description = Column(String(500))

    # Дополнительные данные
    ip_address = Column(String(45), nullable=True)  # IPv4 или IPv6
    location = Column(String(100), nullable=True)  # Country code
    device_id = Column(String(100), nullable=True)

    # Fraud status
    status = Column(Enum(TransactionStatusEnum), default=TransactionStatusEnum.PENDING, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    sender = relationship("User", foreign_keys=[sender_id], back_populates="transactions_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="transactions_received")
    account = relationship("Account", back_populates="transactions")
    fraud_score = relationship("FraudScore", back_populates="transaction", uselist=False, cascade="all, delete-orphan")
    fraud_patterns = relationship("FraudPattern", back_populates="transaction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transaction {self.sender_id}->{self.receiver_id}: {self.amount} {self.currency}>"


class FraudScore(Base):
    """Результат ML оценки мошенничества"""
    __tablename__ = "fraud_scores"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, unique=True, index=True)

    # Оценки от разных моделей (0.0 - 1.0)
    xgboost_score = Column(Float, nullable=True)      # XGBoost score
    random_forest_score = Column(Float, nullable=True)  # Random Forest score
    lstm_score = Column(Float, nullable=True)         # LSTM score
    isolation_forest_score = Column(Float, nullable=True)  # Isolation Forest score
    rule_engine_score = Column(Float, nullable=True)  # Rule-based engine score

    # Финальная оценка (мета-модель)
    final_score = Column(Float, nullable=False)  # 0.0 - 1.0

    # Объяснение от Claude AI
    explanation = Column(String(1000), nullable=True)  # Почему была заблокирована

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relations
    transaction = relationship("Transaction", back_populates="fraud_score")

    def __repr__(self):
        return f"<FraudScore {self.final_score:.3f}>"


class FraudPattern(Base):
    """Обнаруженный паттерн мошенничества"""
    __tablename__ = "fraud_patterns"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)

    pattern_name = Column(String(100), nullable=False, index=True)  # Название паттерна
    pattern_description = Column(String(500))  # Описание паттерна
    confidence = Column(Float, nullable=False)  # Уверенность 0.0-1.0

    # JSON данные для анализа
    details = Column(JSON, nullable=True)  # Дополнительные детали

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relations
    transaction = relationship("Transaction", back_populates="fraud_patterns")

    def __repr__(self):
        return f"<FraudPattern {self.pattern_name} ({self.confidence:.1%})>"
