"""
Аутентификация и регистрация пользователей
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import jwt
import logging
from datetime import datetime, timedelta

from backend.config.database import get_db
from backend.config.settings import get_settings
from backend.models.models import User, Account

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

settings = get_settings()

# JWT Secret (in production should be in .env)
SECRET_KEY = settings.groq_api_key or "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 дней


# ═════════════════════════════════════════════════════════
# SCHEMAS
# ═════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    """Запрос на регистрацию"""
    username: str  # Используем как name
    country: str = "KZ"
    bank: str = "Demo Bank"
    initial_balance: float = 100000.0


class RegisterResponse(BaseModel):
    """Ответ при регистрации"""
    success: bool
    user_id: int
    username: str
    token: str
    message: str


class LoginRequest(BaseModel):
    """Запрос на вход"""
    username: str


class LoginResponse(BaseModel):
    """Ответ при входе"""
    success: bool
    user_id: int
    username: str
    token: str
    message: str


class CurrentUserResponse(BaseModel):
    """Текущий пользователь"""
    user_id: int
    username: str
    country: str
    bank: str
    accounts: list


# ═════════════════════════════════════════════════════════
# JWT HELPERS
# ═════════════════════════════════════════════════════════

def create_access_token(user_id: int, username: str):
    """Создать JWT токен"""
    expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": expires
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> Optional[dict]:
    """Проверить JWT токен"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        return None


def get_current_user(authorization: str = None, db: Session = None) -> Optional[User]:
    """Получить текущего пользователя из токена"""
    if not authorization or not db:
        return None

    try:
        token = authorization.replace("Bearer ", "")
        payload = verify_token(token)
        if not payload:
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        user = db.query(User).filter(User.id == user_id).first()
        return user
    except:
        return None


# ═════════════════════════════════════════════════════════
# ENDPOINTS
# ═════════════════════════════════════════════════════════

@router.post("/register", response_model=RegisterResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Зарегистрировать нового пользователя"""
    try:
        # Проверяем, существует ли пользователь
        existing_user = db.query(User).filter(User.name == request.username).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail=f"Пользователь '{request.username}' уже существует"
            )

        # Создаём пользователя
        new_user = User(
            name=request.username,
            country=request.country,
            bank=request.bank
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"✅ Зарегистрирован новый пользователь: {request.username} (ID: {new_user.id})")

        # Создаём стартовые счета
        for currency in ["USD", "EUR", "KZT"]:
            account = Account(
                user_id=new_user.id,
                account_number=f"{request.username.upper()}{currency}{new_user.id}",
                currency=currency,
                balance=request.initial_balance,
                is_active=True
            )
            db.add(account)
        db.commit()

        # Создаём токен
        token = create_access_token(new_user.id, new_user.name)

        return RegisterResponse(
            success=True,
            user_id=new_user.id,
            username=new_user.name,
            token=token,
            message=f"✅ Добро пожаловать, {request.username}! Созданы 3 счета (USD, EUR, KZT) с балансом {request.initial_balance}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при регистрации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Войти с именем пользователя"""
    try:
        # Ищем пользователя по имени
        user = db.query(User).filter(User.name == request.username).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail=f"Пользователь '{request.username}' не найден"
            )

        # Создаём токен
        token = create_access_token(user.id, user.name)

        logger.info(f"✅ Вход пользователя: {request.username}")

        return LoginResponse(
            success=True,
            user_id=user.id,
            username=user.name,
            token=token,
            message=f"✅ Добро пожаловать назад, {request.username}!"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при входе: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
def get_current_user_info(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Получить информацию о текущем пользователе"""
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Не авторизирован")

        user = get_current_user(authorization, db)
        if not user:
            raise HTTPException(status_code=401, detail="Неверный токен")

        accounts = db.query(Account).filter(Account.user_id == user.id).all()

        logger.info(f"✅ Получена информация для пользователя {user.name} (аккаунтов: {len(accounts)})")

        return {
            "success": True,
            "user": {
                "id": user.id,
                "username": user.name,
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
        logger.error(f"❌ Ошибка при получении информации о пользователе: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
def get_all_users_for_transfer(db: Session = Depends(get_db)):
    """Получить всех пользователей для выбора получателя"""
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
                        "balance": acc.balance
                    }
                    for acc in accounts
                ]
            })

        return {"success": True, "users": result}

    except Exception as e:
        logger.error(f"❌ Ошибка при получении пользователей: {e}")
        raise HTTPException(status_code=500, detail=str(e))
