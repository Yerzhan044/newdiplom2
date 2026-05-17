"""
Feature engineering для обработки данных транзакции перед подачей в ML модели

Извлекает из транзакции ~25 признаков для предсказания fraud score
"""

import numpy as np
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Класс для извлечения признаков из транзакции"""

    @staticmethod
    def extract_features(
        transaction: Dict,
        user_history: List[Dict] = None,
    ) -> np.ndarray:
        """
        Извлечь признаки для ML моделей

        Args:
            transaction: Словарь с данными транзакции
                {
                    'amount': 1000.0,
                    'timestamp': datetime,
                    'sender_country': 'KZ',
                    'receiver_country': 'RU',
                    'sender_id': 1,
                    'ip_address': '192.168.1.1',
                    'device_id': 'device_123',
                    ...
                }
            user_history: История предыдущих транзакций пользователя

        Returns:
            numpy array размером (1, n_features) для подачи в модель
        """

        features = []

        # ═══════════════════════════════════════════════════
        # 1. AMOUNT FEATURES (сумма)
        # ═══════════════════════════════════════════════════

        amount = transaction.get('amount', 0.0)
        features.append(amount)  # 0
        features.append(np.log1p(amount))  # 1 - log transform

        # Средняя сумма по пользователю (из истории)
        if user_history:
            amounts = [t.get('amount', 0) for t in user_history]
            avg_amount = np.mean(amounts) if amounts else amount
            std_amount = np.std(amounts) if len(amounts) > 1 else 1.0
            features.append(avg_amount)  # 2
            features.append(std_amount)  # 3
            # Нормализация
            normalized = (amount - avg_amount) / (std_amount + 1e-8)
            features.append(normalized)  # 4
        else:
            features.extend([amount, 1.0, 0.0])  # default values

        # ═══════════════════════════════════════════════════
        # 2. TIME FEATURES (временные)
        # ═══════════════════════════════════════════════════

        timestamp = transaction.get('timestamp', datetime.utcnow())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        features.append(timestamp.hour)  # 5 - час дня
        features.append(timestamp.weekday())  # 6 - день недели (0=пн, 6=вс)
        features.append(timestamp.day)  # 7 - день месяца
        features.append(timestamp.month)  # 8 - месяц

        # Ночное время (02:00-05:00) - паттерн мошенничества
        is_night = 1 if (timestamp.hour >= 2 and timestamp.hour <= 5) else 0
        features.append(is_night)  # 9

        # ═══════════════════════════════════════════════════
        # 3. VELOCITY FEATURES (частота)
        # ═══════════════════════════════════════════════════

        if user_history:
            # Кол-во транзакций пользователя
            features.append(len(user_history))  # 10

            # Кол-во уникальных получателей
            unique_receivers = len(set(t.get('receiver_id', None) for t in user_history))
            features.append(unique_receivers)  # 11

            # Кол-во уникальных стран
            unique_countries = len(set(t.get('receiver_country', None) for t in user_history))
            features.append(unique_countries)  # 12
        else:
            features.extend([0, 0, 0])

        # ═══════════════════════════════════════════════════
        # 4. LOCATION FEATURES
        # ═══════════════════════════════════════════════════

        sender_country = transaction.get('sender_country', 'XX')
        receiver_country = transaction.get('receiver_country', 'XX')

        # Международная ли транзакция?
        is_international = 0 if sender_country == receiver_country else 1
        features.append(is_international)  # 13

        # Кодируем страны
        countries = {'KZ': 1, 'RU': 2, 'DE': 3, 'US': 4, 'XX': 0}
        features.append(countries.get(sender_country, 0))  # 14
        features.append(countries.get(receiver_country, 0))  # 15

        # ═══════════════════════════════════════════════════
        # 5. DEVICE & IP FEATURES
        # ═══════════════════════════════════════════════════

        ip_address = transaction.get('ip_address', '0.0.0.0')
        device_id = transaction.get('device_id', 'unknown')

        # Hash IP адреса для унификации
        ip_hash = hash(ip_address) % 10000
        features.append(ip_hash / 10000)  # 14 - normalized

        # Hash device id
        device_hash = hash(device_id) % 10000
        features.append(device_hash / 10000)  # 15 - normalized

        # ═══════════════════════════════════════════════════
        # 6. TRANSACTION PATTERNS (паттерны)
        # ═══════════════════════════════════════════════════

        if user_history:
            # Одинаковые суммы - признак структурирования?
            amounts = [t.get('amount', 0) for t in user_history]
            # Кол-во транзакций с почти одинаковой суммой
            same_amount_count = sum(1 for a in amounts if abs(a - amount) < 100)
            features.append(same_amount_count)  # 16

            # Паттерн: все средства сразу выводятся?
            # (это будет считаться после зачисления, пока ставим 0)
            features.append(0)  # 17
        else:
            features.extend([0, 0])

        # ═══════════════════════════════════════════════════
        # 7. MISSING VALUES INDICATOR
        # ═══════════════════════════════════════════════════

        missing_count = sum(1 for v in transaction.values() if v is None or v == '')
        features.append(missing_count / 10)  # 18 - normalized

        # ═══════════════════════════════════════════════════
        # Padding до 25 признаков (если нужно для совместимости)
        # ═══════════════════════════════════════════════════

        while len(features) < 25:
            features.append(0.0)

        # Ограничиваем до 25 признаков
        features = features[:25]

        # Преобразуем в numpy array
        return np.array([features], dtype=np.float32)

    @staticmethod
    def get_feature_names() -> List[str]:
        """Получить названия признаков (для объяснения)"""
        return [
            'amount',
            'amount_log',
            'avg_amount',
            'std_amount',
            'normalized_amount',
            'hour',
            'dayofweek',
            'day',
            'month',
            'is_night',
            'num_transactions',
            'unique_receivers',
            'unique_countries',
            'is_international',
            'sender_country',
            'receiver_country',
            'ip_hash',
            'device_hash',
            'same_amount_count',
            'immediate_withdrawal',
            'missing_values',
            'padding_1',
            'padding_2',
            'padding_3',
            'padding_4',
        ]
