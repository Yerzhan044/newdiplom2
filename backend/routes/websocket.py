"""
WebSocket endpoints для real-time обновлений дашборда

Позволяет отправлять live обновления о новых транзакциях,
fraud scores и статистике на фронтенд в реальном времени
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import json
from datetime import datetime
from typing import Set

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Управление WebSocket подключениями"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Добавить новое подключение"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"✅ WebSocket подключился (всего: {len(self.active_connections)})")

    def disconnect(self, websocket: WebSocket):
        """Удалить подключение"""
        self.active_connections.discard(websocket)
        logger.info(f"❌ WebSocket отключился (осталось: {len(self.active_connections)})")

    async def broadcast(self, data: dict):
        """Отправить сообщение всем подключённым клиентам"""
        if not self.active_connections:
            return

        # Добавляем timestamp
        data['timestamp'] = datetime.utcnow().isoformat()

        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"Ошибка отправки: {e}")
                disconnected.add(connection)

        # Удаляем мёртвые подключения
        self.active_connections -= disconnected


# Глобальный менеджер подключений
manager = ConnectionManager()


@router.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket для live транзакций

    Отправляет в реальном времени:
    - Новые транзакции
    - Fraud scores
    - Обновления статистики
    - Обнаруженные паттерны
    """

    await manager.connect(websocket)

    try:
        while True:
            # Ждём сообщений от клиента (если нужны)
            data = await websocket.receive_text()

            # Можно обработать команды от клиента
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket закрыт")

    except Exception as e:
        logger.error(f"WebSocket ошибка: {e}")
        manager.disconnect(websocket)


async def send_transaction_update(transaction_data: dict):
    """
    Отправить обновление о новой транзакции всем клиентам

    Args:
        transaction_data: Данные транзакции с fraud score
    """

    message = {
        "type": "transaction",
        "data": transaction_data
    }

    await manager.broadcast(message)


async def send_statistics_update(stats: dict):
    """
    Отправить обновление статистики

    Args:
        stats: Статистика (одобрено/проверка/заблокировано)
    """

    message = {
        "type": "statistics",
        "data": stats
    }

    await manager.broadcast(message)


async def send_fraud_pattern_alert(pattern: dict):
    """
    Отправить алерт об обнаруженном паттерне

    Args:
        pattern: Данные паттерна
    """

    message = {
        "type": "fraud_pattern",
        "data": pattern
    }

    await manager.broadcast(message)


async def send_system_message(message_text: str, level: str = "info"):
    """
    Отправить системное сообщение

    Args:
        message_text: Текст сообщения
        level: "info", "warning", "error"
    """

    message = {
        "type": "system",
        "level": level,
        "message": message_text
    }

    await manager.broadcast(message)
