"""
Интеграция с Groq API для генерации AI объяснений (FREE!)

Используется для:
1. Объяснения почему транзакция заблокирована
2. Автоматической генерации реалистичных транзакций
3. Генерации объяснений на естественном языке

Groq - бесплатный API с отличной скоростью!
"""

import logging
import random
from typing import Optional, Dict, List
from groq import Groq

logger = logging.getLogger(__name__)


class ClaudeService:
    """Сервис для работы с Groq API (Claude-like, но бесплатный!)"""

    def __init__(self, api_key: str = None):
        """
        Инициализация Groq клиента

        Args:
            api_key: Groq API key (если None, берется из environ GROQ_API_KEY)
        """
        if api_key:
            self.client = Groq(api_key=api_key)
        else:
            self.client = Groq()  # Читает из GROQ_API_KEY

        # Groq поддерживает несколько моделей
        self.model = "llama-3.3-70b-versatile"  # Актуальная и быстрая модель
        logger.info("✅ Groq Service инициализирован (Llama 3.3 70B Versatile)")

    def explain_fraud_decision(
        self,
        fraud_score: float,
        detected_patterns: List[Dict],
        transaction_data: Dict,
    ) -> str:
        """
        Генерировать AI объяснение почему транзакция заблокирована

        Args:
            fraud_score: Финальный fraud score (0.0-1.0)
            detected_patterns: Список обнаруженных паттернов
            transaction_data: Данные транзакции

        Returns:
            Объяснение на естественном языке (русский/английский)
        """

        try:
            # Подготовка контекста
            patterns_text = "\n".join([
                f"- {p['pattern_name']}: {p['description']} (confidence: {p['confidence']:.1%})"
                for p in detected_patterns
            ])

            prompt = f"""Ты - система обнаружения мошенничества в банке.
Объясни простым языком почему эта транзакция была заблокирована.

ДАННЫЕ ТРАНЗАКЦИИ:
- Сумма: {transaction_data.get('amount', 0):.2f} {transaction_data.get('currency', 'USD')}
- От: {transaction_data.get('sender_name', 'User')} ({transaction_data.get('sender_country', 'XX')})
- Кому: {transaction_data.get('receiver_name', 'Recipient')} ({transaction_data.get('receiver_country', 'XX')})
- Время: {transaction_data.get('timestamp', 'N/A')}

ОБНАРУЖЕННЫЕ ПАТТЕРНЫ МОШЕННИЧЕСТВА:
{patterns_text}

FRAUD SCORE: {fraud_score:.1%} (выше 70% = БЛОКИРОВКА)

Объясни:
1. Что обнаружила система?
2. Почему это опасно?
3. Что должен сделать пользователь? (2-3 предложения)

Говори дружелюбно, но ясно и определённо."""

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            explanation = response.choices[0].message.content
            logger.info(f"✅ Groq объяснение сгенерировано ({len(explanation)} символов)")
            return explanation

        except Exception as e:
            logger.error(f"❌ Ошибка при генерации объяснения: {e}")
            # Fallback объяснение если Groq не работает
            risk_level = "ВЫСОКИЙ РИСК" if fraud_score > 0.7 else "СРЕДНИЙ РИСК" if fraud_score > 0.4 else "НИЗКИЙ РИСК"
            patterns_summary = ", ".join([p['pattern_name'] for p in detected_patterns]) if detected_patterns else "стандартная проверка"
            return f"{risk_level}. Обнаружено: {patterns_summary}. Fraud score: {fraud_score:.1%}. Свяжитесь с поддержкой для уточнения."

    def generate_realistic_transaction(
        self,
        countries: List[str] = None,
        banks: List[str] = None,
    ) -> Dict:
        """
        Генерировать реалистичную транзакцию через Claude API

        Args:
            countries: Список стран для симуляции (['KZ', 'RU', 'DE', 'US'])
            banks: Список банков (['Kaspi Bank', 'Halyk Bank', 'Сбербанк', 'Deutsche Bank', 'Stripe'])

        Returns:
            Словарь с данными сгенерированной транзакции:
            {
                'sender_name': 'Марат Абиев',
                'sender_country': 'KZ',
                'sender_bank': 'Kaspi Bank',
                'receiver_name': 'John Smith',
                'receiver_country': 'US',
                'receiver_bank': 'Stripe',
                'amount': 5000.00,
                'currency': 'USD',
                'description': 'Payment for goods',
                'is_fraud': False,  # иногда True для демонстрации
            }
        """

        if countries is None:
            countries = ['KZ', 'RU', 'DE', 'US']
        if banks is None:
            banks = ['Kaspi Bank', 'Halyk Bank', 'Сбербанк', 'Deutsche Bank', 'Stripe']

        try:
            prompt = f"""Ты - генератор реалистичных банковских транзакций для тестирования системы обнаружения мошенничества.

Сгенерируй ОДНУ реалистичную транзакцию в JSON формате.

ТРЕБОВАНИЯ:
- 70% обычные легитимные транзакции
- 30% подозрительные/мошеннические

ВАРИАНТЫ СТРАН: {countries}
ВАРИАНТЫ БАНКОВ: {banks}

Верни ТОЛЬКО JSON (без markdown, без объяснений):
{{
  "sender_name": "Имя Фамилия",
  "sender_country": "KZ",
  "sender_bank": "Kaspi Bank",
  "receiver_name": "Name Surname",
  "receiver_country": "US",
  "receiver_bank": "Stripe",
  "amount": 1000.00,
  "currency": "USD",
  "description": "Payment description",
  "is_fraud": false
}}

Генерируй данные прямо!"""

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=400,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = response.choices[0].message.content.strip()

            # Парсим JSON
            import json
            # Убираем markdown блоки если они есть
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            transaction = json.loads(response_text)
            logger.info(f"✅ Транзакция сгенерирована: {transaction['sender_name']} -> {transaction['receiver_name']}")
            return transaction

        except Exception as e:
            logger.error(f"❌ Ошибка при генерации транзакции: {e}")
            # Fallback: реалистичная транзакция с случайными данными
            first_names_en = ["John", "Jane", "Michael", "Sarah", "David", "Emma", "Robert", "Lisa"]
            last_names_en = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
            first_names_ru = ["Иван", "Мария", "Петр", "Анна", "Сергей", "Ирина", "Александр"]
            last_names_ru = ["Иванов", "Петров", "Сидоров", "Козлов", "Морозов", "Волков"]

            countries = countries or ['KZ', 'RU', 'DE', 'US']
            sender_country = random.choice(countries)
            receiver_country = random.choice(countries)

            # Выбираем русские имена для РФ/КЗ, английские для остального
            if sender_country in ['KZ', 'RU']:
                sender_name = f"{random.choice(first_names_ru)} {random.choice(last_names_ru)}"
            else:
                sender_name = f"{random.choice(first_names_en)} {random.choice(last_names_en)}"

            if receiver_country in ['KZ', 'RU']:
                receiver_name = f"{random.choice(first_names_ru)} {random.choice(last_names_ru)}"
            else:
                receiver_name = f"{random.choice(first_names_en)} {random.choice(last_names_en)}"

            return {
                "sender_name": sender_name,
                "sender_country": sender_country,
                "sender_bank": random.choice(banks or ['Kaspi Bank', 'Halyk Bank', 'Сбербанк', 'Deutsche Bank']),
                "receiver_name": receiver_name,
                "receiver_country": receiver_country,
                "receiver_bank": random.choice(banks or ['Stripe', 'Sberbank', 'Deutsche Bank', 'SWIFT']),
                "amount": round(random.uniform(100, 50000), 2),
                "currency": random.choice(['USD', 'EUR', 'KZT', 'RUB']),
                "description": random.choice(['Payment for goods', 'Service payment', 'Invoice payment', 'Transfer']),
                "is_fraud": random.random() < 0.2  # 20% мошеннических
            }

    def generate_transaction_batch(
        self,
        count: int = 5,
        countries: List[str] = None,
        banks: List[str] = None,
    ) -> List[Dict]:
        """
        Генерировать несколько транзакций

        Args:
            count: Количество транзакций (макс 10)
            countries: Список стран
            banks: Список банков

        Returns:
            Список транзакций
        """

        count = min(count, 10)  # Лимит для экономии API
        transactions = []

        for i in range(count):
            txn = self.generate_realistic_transaction(countries, banks)
            transactions.append(txn)

        logger.info(f"✅ Сгенерировано {count} транзакций")
        return transactions

    def generate_summary_report(
        self,
        total_transactions: int,
        approved_count: int,
        review_count: int,
        blocked_count: int,
        top_patterns: List[Dict],
    ) -> str:
        """
        Генерировать AI резюме статистики за день

        Args:
            total_transactions: Всего транзакций
            approved_count: Одобрено
            review_count: На проверку
            blocked_count: Заблокировано
            top_patterns: Топ паттернов

        Returns:
            AI резюме
        """

        try:
            patterns_text = "\n".join([
                f"- {p['name']}: {p['count']} обнаружений ({p['confidence']:.0%})"
                for p in top_patterns[:5]
            ])

            prompt = f"""Ты - аналитик в системе обнаружения мошенничества.
Напиши краткое резюме (3-5 предложений) статистики за день.

СТАТИСТИКА:
- Всего транзакций: {total_transactions}
- Одобрено: {approved_count} ({100*approved_count/max(total_transactions,1):.1f}%)
- На проверку: {review_count} ({100*review_count/max(total_transactions,1):.1f}%)
- Заблокировано: {blocked_count} ({100*blocked_count/max(total_transactions,1):.1f}%)

ТОП ПАТТЕРНОВ:
{patterns_text}

Напиши профессиональное резюме (как в отчёте банка для руководства)."""

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            summary = response.choices[0].message.content
            logger.info(f"✅ Резюме сгенерировано")
            return summary

        except Exception as e:
            logger.error(f"❌ Ошибка при генерации резюме: {e}")
            return f"За день обработано {total_transactions} транзакций. Заблокировано {blocked_count}."
