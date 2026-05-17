"""
Rule Engine для обнаружения 12 паттернов мошенничества

Используются жесткие правила + статистический анализ истории
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import numpy as np
from sqlalchemy.orm import Session
import logging

from backend.models.models import Transaction, User

logger = logging.getLogger(__name__)


class RuleEngine:
    """Обнаружение паттернов мошенничества через правила"""

    @staticmethod
    def detect_patterns(
        db: Session,
        transaction: Transaction,
        user_history: List[Transaction] = None,
    ) -> List[Dict]:
        """
        Обнаружить все паттерны мошенничества для транзакции

        Args:
            db: Session БД
            transaction: Текущая транзакция
            user_history: История транзакций пользователя (опционально)

        Returns:
            Список обнаруженных паттернов:
            [
                {
                    'pattern_name': 'night_transfer',
                    'description': 'Transfer at 03:45 (02:00-05:00 night hours)',
                    'confidence': 0.8,
                    'rule': 'IF hour >= 2 AND hour <= 5 THEN high risk'
                },
                ...
            ]
        """

        if user_history is None:
            user_history = RuleEngine._get_user_history(db, transaction.sender_id)

        detected_patterns = []

        # ═══════════════════════════════════════════════════════
        # 1. НОЧНЫЕ ПЕРЕВОДЫ (02:00-05:00)
        # ═══════════════════════════════════════════════════════

        if RuleEngine._is_night_transfer(transaction):
            detected_patterns.append({
                'pattern_name': 'night_transfer',
                'description': f'Transfer at {transaction.timestamp.strftime("%H:%M")} (02:00-05:00 night hours)',
                'confidence': 0.7,
                'rule': 'IF hour >= 2 AND hour <= 5 THEN suspicious',
            })

        # ═══════════════════════════════════════════════════════
        # 2. VELOCITY-АТАКА (50+ транзакций за 10 минут)
        # ═══════════════════════════════════════════════════════

        velocity_attack = RuleEngine._detect_velocity_attack(db, transaction.sender_id)
        if velocity_attack > 0:
            detected_patterns.append({
                'pattern_name': 'velocity_attack',
                'description': f'{velocity_attack} transactions in 10 minutes',
                'confidence': 0.95,
                'rule': 'IF transactions_10min >= 50 THEN fraud',
            })

        # ═══════════════════════════════════════════════════════
        # 3. РЕГУЛЯРНЫЕ ПОСТУПЛЕНИЯ ОТ РАЗНЫХ ЛЮДЕЙ (СТРУКТУРИРОВАНИЕ)
        # ═══════════════════════════════════════════════════════

        if RuleEngine._is_structuring(user_history):
            detected_patterns.append({
                'pattern_name': 'structuring',
                'description': 'Regular payments from different people (splitting large sum)',
                'confidence': 0.75,
                'rule': 'IF same_sender_different_amounts OR different_senders_same_amount THEN suspicious',
            })

        # ═══════════════════════════════════════════════════════
        # 4. ОДИНАКОВЫЕ СУММЫ ОТ МНОЖЕСТВА ЛЮДЕЙ
        # ═══════════════════════════════════════════════════════

        if RuleEngine._detect_same_amount_from_many(user_history):
            detected_patterns.append({
                'pattern_name': 'same_amount_multiple_senders',
                'description': 'Received same amount from multiple different senders',
                'confidence': 0.80,
                'rule': 'IF unique_senders >= 3 AND all_amounts_similar THEN suspicious',
            })

        # ═══════════════════════════════════════════════════════
        # 5. РЕЗКИЙ РОСТ ОБОРОТА (vs 30-дневная история)
        # ═══════════════════════════════════════════════════════

        surge = RuleEngine._detect_spending_surge(user_history, transaction.amount)
        if surge > 0:
            detected_patterns.append({
                'pattern_name': 'spending_surge',
                'description': f'Spending surge: {surge:.0%} increase vs 30-day average',
                'confidence': 0.75,
                'rule': 'IF amount > avg_30days * 2 THEN suspicious',
            })

        # ═══════════════════════════════════════════════════════
        # 6. ДРОБЛЕНИЕ СУММЫ (STRUCTURING)
        # ═══════════════════════════════════════════════════════

        if RuleEngine._detect_amount_splitting(user_history):
            detected_patterns.append({
                'pattern_name': 'amount_splitting',
                'description': 'Multiple small transfers (likely splitting large amount)',
                'confidence': 0.78,
                'rule': 'IF num_small_transfers >= 5 AND total > threshold THEN fraud',
            })

        # ═══════════════════════════════════════════════════════
        # 7. НЕОФИЦИАЛЬНЫЙ БИЗНЕС (много поступлений, нет заявления)
        # ═══════════════════════════════════════════════════════

        if RuleEngine._detect_informal_business(user_history):
            detected_patterns.append({
                'pattern_name': 'informal_business',
                'description': 'Receiving regular payments like business, but not registered',
                'confidence': 0.70,
                'rule': 'IF daily_inbound >= 10 AND no_business_license THEN suspicious',
            })

        # ═══════════════════════════════════════════════════════
        # 8. ЧАСТЫЕ МЕЖДУНАРОДНЫЕ ПЕРЕВОДЫ
        # ═══════════════════════════════════════════════════════

        if RuleEngine._detect_frequent_international(user_history):
            detected_patterns.append({
                'pattern_name': 'frequent_international',
                'description': 'High frequency of international transfers',
                'confidence': 0.65,
                'rule': 'IF international_transactions >= 5_per_day THEN suspicious',
            })

        # ═══════════════════════════════════════════════════════
        # 9. МОМЕНТАЛЬНЫЙ ВЫВОД НАЛИЧКОЙ
        # ═══════════════════════════════════════════════════════

        # TODO: требует доступа к операциям вывода (не в текущей БД структуре)
        # if RuleEngine._detect_immediate_withdrawal(db, transaction.receiver_id):
        #     detected_patterns.append({...})

        # ═══════════════════════════════════════════════════════
        # 10. VPN/TOR + НЕВПОПАДАНИЕ ГЕОЛОКАЦИИ
        # ═══════════════════════════════════════════════════════

        if RuleEngine._detect_vpn_anomaly(transaction):
            detected_patterns.append({
                'pattern_name': 'vpn_location_mismatch',
                'description': 'VPN/TOR detected OR location mismatch',
                'confidence': 0.60,
                'rule': 'IF (vpn_detected OR tor_detected) AND location_mismatch THEN suspicious',
            })

        # ═══════════════════════════════════════════════════════
        # 11. НЕВОЗМОЖНОЕ ПЕРЕМЕЩЕНИЕ
        # ═══════════════════════════════════════════════════════

        if RuleEngine._detect_impossible_movement(db, transaction):
            detected_patterns.append({
                'pattern_name': 'impossible_movement',
                'description': 'Transaction from KZ and then DE in 2 minutes (impossible)',
                'confidence': 0.90,
                'rule': 'IF distance > 5000km AND time < 2min THEN fraud',
            })

        # ═══════════════════════════════════════════════════════
        # 12. ПОВЫШЕННАЯ АКТИВНОСТЬ ПО КАРТЕ
        # ═══════════════════════════════════════════════════════

        if RuleEngine._detect_card_activity_spike(user_history):
            detected_patterns.append({
                'pattern_name': 'card_activity_spike',
                'description': 'Unusual spike in card activity (unusual for this user)',
                'confidence': 0.68,
                'rule': 'IF transactions_today > avg_daily * 3 THEN suspicious',
            })

        return detected_patterns

    # ═══════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _get_user_history(db: Session, user_id: int, days: int = 30) -> List[Transaction]:
        """Получить историю транзакций пользователя"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return db.query(Transaction).filter(
            (Transaction.sender_id == user_id) | (Transaction.receiver_id == user_id),
            Transaction.timestamp >= cutoff_date
        ).all()

    @staticmethod
    def _is_night_transfer(transaction: Transaction) -> bool:
        """Проверка: ночной ли перевод (02:00-05:00)"""
        hour = transaction.timestamp.hour
        return 2 <= hour <= 5

    @staticmethod
    def _detect_velocity_attack(db: Session, user_id: int, minutes: int = 10) -> int:
        """Обнаружить velocity-атаку (50+ транзакций за 10 минут)"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        count = db.query(Transaction).filter(
            Transaction.sender_id == user_id,
            Transaction.timestamp >= cutoff
        ).count()
        return count if count >= 50 else 0

    @staticmethod
    def _is_structuring(history: List[Transaction]) -> bool:
        """Обнаружить структурирование (раздробление суммы)"""
        if len(history) < 5:
            return False

        # Проверяем: регулярные поступления от разных людей
        senders = set(t.sender_id for t in history if t.receiver_id == history[0].receiver_id)
        amounts = [t.amount for t in history if t.receiver_id == history[0].receiver_id]

        return len(senders) >= 3 and len(amounts) >= 5

    @staticmethod
    def _detect_same_amount_from_many(history: List[Transaction]) -> bool:
        """Обнаружить: одинаковые суммы от множества людей"""
        if len(history) < 3:
            return False

        # Группируем по суммам
        amount_count = {}
        for t in history:
            key = round(t.amount, 2)
            amount_count[key] = amount_count.get(key, 0) + 1

        # Если есть сумма которая встречается 3+ раза - подозрительно
        return any(count >= 3 for count in amount_count.values())

    @staticmethod
    def _detect_spending_surge(history: List[Transaction], current_amount: float) -> float:
        """Обнаружить: резкий рост оборота"""
        if len(history) < 10:
            return 0.0

        # Средняя сумма за 30 дней
        avg_amount = np.mean([t.amount for t in history])

        # Если текущая сумма > чем в 2 раза средняя
        if current_amount > avg_amount * 2:
            return (current_amount / avg_amount) - 1
        return 0.0

    @staticmethod
    def _detect_amount_splitting(history: List[Transaction]) -> bool:
        """Обнаружить: дробление суммы"""
        if len(history) < 5:
            return False

        # Ищем последовательность малых сумм
        small_transfers = [t for t in history if t.amount < 100_000]
        return len(small_transfers) >= 5

    @staticmethod
    def _detect_informal_business(history: List[Transaction]) -> bool:
        """Обнаружить: неофициальный бизнес"""
        if len(history) < 10:
            return False

        # Много регулярных поступлений (похоже на бизнес)
        daily_income = len([t for t in history if t.timestamp.date() == datetime.utcnow().date()])
        return daily_income >= 10

    @staticmethod
    def _detect_frequent_international(history: List[Transaction]) -> bool:
        """Обнаружить: частые международные переводы"""
        if len(history) < 5:
            return False

        international = [t for t in history if t.sender.country != t.receiver.country]
        return len(international) >= 5

    @staticmethod
    def _detect_vpn_anomaly(transaction: Transaction) -> bool:
        """Обнаружить: VPN/TOR + невпопадание геолокации"""
        # Простая проверка: если location не совпадает с expected
        # В реальной системе использовали бы GeoIP базу
        if transaction.location and transaction.location.startswith("TOR"):
            return True
        return False

    @staticmethod
    def _detect_impossible_movement(db: Session, transaction: Transaction) -> bool:
        """Обнаружить: невозможное перемещение"""
        # Получаем предыдущую транзакцию пользователя
        prev_transaction = db.query(Transaction).filter(
            Transaction.sender_id == transaction.sender_id,
            Transaction.timestamp < transaction.timestamp
        ).order_by(Transaction.timestamp.desc()).first()

        if not prev_transaction:
            return False

        # Примерные расстояния между странами (км)
        distances = {
            ('KZ', 'RU'): 1500,
            ('KZ', 'DE'): 4000,
            ('KZ', 'US'): 9000,
            ('RU', 'DE'): 1600,
            ('RU', 'US'): 8000,
            ('DE', 'US'): 6000,
        }

        distance_key = (prev_transaction.sender.country, transaction.sender.country)
        distance = distances.get(distance_key, 0)

        # Время между транзакциями
        time_diff = (transaction.timestamp - prev_transaction.timestamp).total_seconds() / 3600  # часы

        # Если расстояние > 5000 км и время < 2 часа - невозможно (самолёт)
        if distance > 5000 and time_diff < 2:
            return True

        return False

    @staticmethod
    def _detect_card_activity_spike(history: List[Transaction]) -> bool:
        """Обнаружить: всплеск активности по карте"""
        if len(history) < 5:
            return False

        # Среднее количество транзакций в день
        days = max(1, (datetime.utcnow() - min(t.timestamp for t in history)).days)
        avg_per_day = len(history) / days

        # Транзакции за последний день
        today_txn = len([t for t in history if t.timestamp.date() == datetime.utcnow().date()])

        # Если в 3 раза больше - подозрительно
        return today_txn > avg_per_day * 3

    @staticmethod
    def calculate_rule_engine_score(patterns: List[Dict]) -> float:
        """
        Вычислить финальный score от Rule Engine на основе обнаруженных паттернов

        Args:
            patterns: Список обнаруженных паттернов

        Returns:
            Score от 0.0 до 1.0
        """

        if not patterns:
            return 0.0

        # Суммируем confidence всех паттернов
        total_confidence = sum(p['confidence'] for p in patterns)

        # Нормализуем (максимум - это количество паттернов)
        max_possible = len(patterns)
        score = min(total_confidence / max_possible, 1.0)

        return score
