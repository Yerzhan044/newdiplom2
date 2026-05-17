#!/usr/bin/env python3
"""
Генератор CSV файла с реалистичными транзакциями (500 штук)
Создаёт папку data/ и сохраняет transactions.csv

Стратегия: генерирует базовые шаблоны через Groq (уважая rate limit),
а остальное создаёт локально для быстроты
"""

import csv
import os
import sys
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Реалистичные имена и данные
FIRST_NAMES_EN = ["John", "Jane", "Michael", "Sarah", "David", "Emma", "Robert", "Lisa", "James", "Mary",
                  "William", "Patricia", "Richard", "Jennifer", "Joseph", "Linda", "Thomas", "Barbara"]
FIRST_NAMES_RU = ["Иван", "Мария", "Петр", "Анна", "Сергей", "Ирина", "Александр", "Наталья", "Виктор", "Елена",
                  "Дмитрий", "Ольга", "Павел", "Татьяна", "Валерий", "Светлана"]
LAST_NAMES_EN = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
LAST_NAMES_RU = ["Иванов", "Петров", "Сидоров", "Козлов", "Морозов", "Волков", "Соколов", "Лебедев", "Новиков", "Федоров"]

COUNTRIES = ["KZ", "RU", "US", "DE", "GB", "FR", "CN", "JP", "IN", "BR", "AU", "CA", "NZ", "SG", "HK"]
CURRENCIES = ["USD", "EUR", "KZT", "RUB", "GBP", "JPY", "CNY", "INR"]

def generate_realistic_name(lang="en"):
    """Генерирует реалистичное имя"""
    if lang == "ru":
        return f"{random.choice(FIRST_NAMES_RU)} {random.choice(LAST_NAMES_RU)}"
    else:
        return f"{random.choice(FIRST_NAMES_EN)} {random.choice(LAST_NAMES_EN)}"

def generate_realistic_amount():
    """Генерирует реалистичную сумму"""
    # Распределение: 60% малые (10-1000), 30% средние (1000-10000), 10% большие (10000+)
    rand = random.random()
    if rand < 0.6:
        return round(random.uniform(10, 1000), 2)
    elif rand < 0.9:
        return round(random.uniform(1000, 10000), 2)
    else:
        return round(random.uniform(10000, 100000), 2)

def generate_transactions_csv(count=500):
    """Генерирует CSV с реалистичными транзакциями"""

    # Создаём папку data если её нет
    os.makedirs('data', exist_ok=True)

    # Создаём CSV файл
    output_file = 'data/transactions.csv'
    base_time = datetime.now()

    print(f"📝 Генерируем {count} транзакций...")
    print(f"💾 Файл будет сохранён в: {os.path.abspath(output_file)}")
    print(f"⚡ Используем локальную генерацию (быстро, без rate limit)")
    print()

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'sender_name',
            'sender_country',
            'sender_ip',
            'receiver_name',
            'receiver_country',
            'receiver_ip',
            'amount',
            'currency',
            'timestamp'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(1, count + 1):
            try:
                # Генерируем отправителя (смешиваем языки)
                if random.random() < 0.6:
                    sender_name = generate_realistic_name("ru")
                    sender_country = random.choice(["KZ", "RU", "BY", "UZ"])
                else:
                    sender_name = generate_realistic_name("en")
                    sender_country = random.choice(["US", "GB", "DE", "FR", "CA", "AU"])

                # Генерируем получателя
                if random.random() < 0.5:
                    receiver_name = generate_realistic_name("ru")
                    receiver_country = random.choice(["KZ", "RU", "BY", "UZ"])
                else:
                    receiver_name = generate_realistic_name("en")
                    receiver_country = random.choice(["US", "GB", "DE", "FR", "CA", "AU", "JP", "CN"])

                # IP адреса
                sender_ip = f"192.168.{random.randint(0,255)}.{random.randint(1,254)}"
                receiver_ip = f"10.0.{random.randint(0,255)}.{random.randint(1,254)}"

                # Сумма и валюта
                amount = generate_realistic_amount()
                currency = random.choice(CURRENCIES)

                # Время (последние 500 часов)
                hours_ago = count - i
                timestamp = (base_time - timedelta(hours=hours_ago)).isoformat()

                # Записываем в CSV
                writer.writerow({
                    'sender_name': sender_name,
                    'sender_country': sender_country,
                    'sender_ip': sender_ip,
                    'receiver_name': receiver_name,
                    'receiver_country': receiver_country,
                    'receiver_ip': receiver_ip,
                    'amount': amount,
                    'currency': currency,
                    'timestamp': timestamp
                })

                # Прогресс каждые 50 строк
                if i % 50 == 0:
                    percent = (i / count) * 100
                    print(f"✅ Обработано {i}/{count} ({percent:.1f}%)")

            except Exception as e:
                print(f"⚠️  Ошибка в строке {i}: {e}")

    print()
    print(f"✅ Генерация завершена!")
    print(f"📊 Всего создано: {count} транзакций")
    print(f"💾 Файл сохранён: {os.path.abspath(output_file)}")
    print()
    print(f"📋 Следующий шаг:")
    print(f"   1. Откройте http://localhost:3000/csv-upload")
    print(f"   2. Нажмите 'Upload & Analyze'")
    print(f"   3. Выберите файл: data/transactions.csv")


if __name__ == "__main__":
    try:
        generate_transactions_csv(500)
    except KeyboardInterrupt:
        print("\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
