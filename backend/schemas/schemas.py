from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TransactionStatusEnum(str, Enum):
    APPROVED = "approved"
    REVIEW = "review"
    BLOCKED = "blocked"
    PENDING = "pending"


# ═════════════════════════════════════════
# USER SCHEMAS
# ═════════════════════════════════════════

class UserCreate(BaseModel):
    """Создание нового пользователя"""
    name: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=2, max_length=2)  # ISO код
    bank: str = Field(..., min_length=1, max_length=50)

    @validator("country")
    def validate_country(cls, v):
        valid_countries = ["KZ", "RU", "DE", "US"]
        if v.upper() not in valid_countries:
            raise ValueError(f"Country must be one of {valid_countries}")
        return v.upper()


class UserResponse(BaseModel):
    """Ответ с данными пользователя"""
    id: int
    name: str
    country: str
    bank: str
    created_at: datetime

    class Config:
        from_attributes = True


# ═════════════════════════════════════════
# ACCOUNT SCHEMAS
# ═════════════════════════════════════════

class AccountCreate(BaseModel):
    """Создание нового счёта"""
    user_id: int
    account_number: str = Field(..., min_length=15, max_length=34)
    currency: str = Field(..., min_length=3, max_length=3)
    balance: float = Field(default=0.0, ge=0)

    @validator("currency")
    def validate_currency(cls, v):
        valid_currencies = ["KZT", "RUB", "EUR", "USD"]
        if v.upper() not in valid_currencies:
            raise ValueError(f"Currency must be one of {valid_currencies}")
        return v.upper()


class AccountResponse(BaseModel):
    """Ответ с данными счёта"""
    id: int
    user_id: int
    account_number: str
    currency: str
    balance: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ═════════════════════════════════════════
# TRANSACTION SCHEMAS
# ═════════════════════════════════════════

class TransactionCreate(BaseModel):
    """Создание новой транзакции"""
    sender_id: int
    receiver_id: int
    account_id: int
    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    description: Optional[str] = Field(None, max_length=500)
    ip_address: Optional[str] = None
    location: Optional[str] = None
    device_id: Optional[str] = None

    @validator("amount")
    def validate_amount(cls, v):
        if v < 0.01:
            raise ValueError("Amount must be at least 0.01")
        if v > 10_000_000:
            raise ValueError("Amount cannot exceed 10,000,000")
        return v

    @validator("currency")
    def validate_currency(cls, v):
        valid_currencies = ["KZT", "RUB", "EUR", "USD"]
        if v.upper() not in valid_currencies:
            raise ValueError(f"Currency must be one of {valid_currencies}")
        return v.upper()


# ═════════════════════════════════════════
# FRAUD SCORE SCHEMAS (до TransactionDetailResponse)
# ═════════════════════════════════════════

class FraudScoreResponse(BaseModel):
    """Ответ с fraud score"""
    id: int
    transaction_id: int
    xgboost_score: Optional[float]
    random_forest_score: Optional[float]
    lstm_score: Optional[float]
    isolation_forest_score: Optional[float]
    rule_engine_score: Optional[float]
    final_score: float
    explanation: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ═════════════════════════════════════════
# FRAUD PATTERN SCHEMAS (до TransactionDetailResponse)
# ═════════════════════════════════════════

class FraudPatternResponse(BaseModel):
    """Ответ с обнаруженным паттерном"""
    id: int
    transaction_id: int
    pattern_name: str
    pattern_description: Optional[str]
    confidence: float
    details: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    """Ответ с полными данными транзакции"""
    id: int
    sender_id: int
    receiver_id: int
    account_id: int
    amount: float
    currency: str
    timestamp: datetime
    description: Optional[str]
    ip_address: Optional[str]
    location: Optional[str]
    device_id: Optional[str]
    status: TransactionStatusEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionDetailResponse(TransactionResponse):
    """Расширенный ответ с fraud_score и patterns"""
    sender: Optional[UserResponse] = None
    receiver: Optional[UserResponse] = None
    fraud_score: Optional[FraudScoreResponse] = None
    fraud_patterns: List[FraudPatternResponse] = []

    class Config:
        from_attributes = True


# ═════════════════════════════════════════
# STATISTICS SCHEMAS
# ═════════════════════════════════════════

class TransactionStatisticsResponse(BaseModel):
    """Статистика по транзакциям"""
    total_transactions: int
    approved_count: int
    review_count: int
    blocked_count: int
    total_amount: float
    average_amount: float
    approval_rate: float  # %
    block_rate: float  # %

    class Config:
        from_attributes = True


class FraudDetectionMetricsResponse(BaseModel):
    """Метрики обнаружения мошенничества"""
    transactions_analyzed: int
    frauds_detected: int
    detection_rate: float  # %
    average_fraud_score: float
    top_patterns: List[dict]  # [{name, count, confidence}]
