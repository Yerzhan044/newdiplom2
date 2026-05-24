from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import asyncio
from dotenv import load_dotenv

# Загружаем переменные из .env перед всем остальным
load_dotenv()

from backend.config.database import init_db, SessionLocal
from backend.config.settings import get_settings
from backend.routes.transactions import router as transactions_router
from backend.routes.ml import router as ml_router
from backend.routes.websocket import router as ws_router
from backend.routes.csv_upload import router as csv_router
from backend.routes.accounts import router as accounts_router
from backend.routes.auth import router as auth_router
from backend.routes.test import router as test_router
from backend.services.transaction_generator import start_transaction_generator, stop_transaction_generator
from backend.models.models import User, Account

settings = get_settings()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_demo_accounts():
    """Создаёт 2 демо-аккаунта для тестирования"""
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже такие пользователи
        alice = db.query(User).filter(User.name == "Alice Smith").first()
        bob = db.query(User).filter(User.name == "Bob Johnson").first()

        if not alice:
            alice = User(name="Alice Smith", country="KZ", bank="Kaspi Bank")
            db.add(alice)
            db.commit()
            db.refresh(alice)
            logger.info(f"✅ Создан пользователь Alice (ID: {alice.id})")

            # Создаём счета для Alice
            for currency in ["USD", "EUR", "KZT"]:
                account = Account(
                    user_id=alice.id,
                    account_number=f"ALICE{currency}123456",
                    currency=currency,
                    balance=100000.00,
                    is_active=True
                )
                db.add(account)
            db.commit()
            logger.info(f"✅ Созданы счета для Alice")

        if not bob:
            bob = User(name="Bob Johnson", country="US", bank="Stripe")
            db.add(bob)
            db.commit()
            db.refresh(bob)
            logger.info(f"✅ Создан пользователь Bob (ID: {bob.id})")

            # Создаём счета для Bob
            for currency in ["USD", "EUR", "GBP"]:
                account = Account(
                    user_id=bob.id,
                    account_number=f"BOB{currency}654321",
                    currency=currency,
                    balance=150000.00,
                    is_active=True
                )
                db.add(account)
            db.commit()
            logger.info(f"✅ Созданы счета для Bob")

    except Exception as e:
        logger.error(f"❌ Ошибка при создании демо-аккаунтов: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация приложения при запуске и очистка при завершении"""
    logger.info("🚀 Инициализация приложения...")
    init_db()
    logger.info("✅ База данных инициализирована")

    # Создаём демо-аккаунты
    create_demo_accounts()
    logger.info("✅ Демо-аккаунты готовы (Alice & Bob)")

    # Запуск генератора транзакций в фоне
    generator_task = asyncio.create_task(start_transaction_generator())
    logger.info("✅ Генератор транзакций запущен")

    yield

    # Остановка генератора при завершении
    await stop_transaction_generator()
    generator_task.cancel()
    logger.info("🛑 Завершение приложения...")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan,
)

# Add CORS middleware (для многоноутбучной системы)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production нужно ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(ml_router)
app.include_router(ws_router)
app.include_router(csv_router)
app.include_router(accounts_router)
app.include_router(test_router)


# ═════════════════════════════════════════════════════════
# ROOT ENDPOINTS
# ═════════════════════════════════════════════════════════

@app.get("/")
def read_root():
    """Корневой endpoint"""
    return {
        "message": "🛡️ Fraud Detection System API",
        "version": settings.api_version,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health")
def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "service": "Fraud Detection System",
        "version": settings.api_version,
    }


@app.get("/info")
def api_info():
    """Информация об API и настройках"""
    return {
        "api_title": settings.api_title,
        "api_version": settings.api_version,
        "api_description": settings.api_description,
        "fraud_thresholds": {
            "approved": settings.fraud_threshold_approved,
            "review": settings.fraud_threshold_review,
            "blocked": settings.fraud_threshold_blocked,
        },
        "ai_provider": "Groq (Free)",
        "generation_interval": f"{settings.generation_interval_seconds}s",
    }


# ═════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═════════════════════════════════════════════════════════

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Обработка 404 ошибок"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"Endpoint {request.url.path} not found",
            "status_code": 404,
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Обработка 500 ошибок"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status_code": 500,
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.backend_host,
        port=settings.backend_port,
        log_level=settings.log_level.lower(),
    )
