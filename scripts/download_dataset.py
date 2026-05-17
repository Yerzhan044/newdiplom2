#!/usr/bin/env python3
"""
Скрипт для загрузки IEEE-CIS Fraud Detection датасета с Kaggle

Используется: https://www.kaggle.com/competitions/ieee-fraud-detection/data

Требование: kaggle CLI installed
    pip install kaggle
    Скачай API ключ с https://www.kaggle.com/settings/account
    Положи в ~/.kaggle/kaggle.json
"""

import os
import sys
import logging
import zipfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def check_kaggle_setup():
    """Проверка что kaggle CLI установлен и настроен"""
    try:
        import kaggle
        logger.info("✅ Kaggle CLI установлен")
    except ImportError:
        logger.error("❌ Kaggle CLI не установлен. Установи: pip install kaggle")
        sys.exit(1)

    kaggle_config = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_config.exists():
        logger.error("❌ Kaggle credentials не найдены")
        logger.error("   1. Скачай API ключ: https://www.kaggle.com/settings/account")
        logger.error("   2. Положи в ~/.kaggle/kaggle.json")
        sys.exit(1)

    logger.info("✅ Kaggle credentials найдены")


def download_dataset():
    """Загрузка IEEE-CIS Fraud Detection датасета"""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()

        logger.info("📥 Загрузка IEEE-CIS Fraud Detection датасета...")
        logger.info("   Это может занять несколько минут (~1-2 GB)...")

        api.competition_download_files(
            "ieee-fraud-detection",
            path=str(DATA_DIR),
            quiet=False
        )

        logger.info("✅ Датасет загружен успешно")

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки: {e}")
        logger.info("   Альтернатива: скачай вручную с https://www.kaggle.com/c/ieee-fraud-detection/data")
        sys.exit(1)


def extract_dataset():
    """Распаковка загруженного архива"""
    zip_file = DATA_DIR / "ieee-fraud-detection.zip"

    if zip_file.exists():
        logger.info("📦 Распаковка архива...")
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(DATA_DIR)
            logger.info("✅ Архив распакован")

            # Удаляем сам архив
            zip_file.unlink()
            logger.info("🗑️  Архив удалён")
        except Exception as e:
            logger.error(f"❌ Ошибка распаковки: {e}")
            sys.exit(1)
    else:
        logger.warning(f"⚠️  Архив не найден: {zip_file}")
        logger.info("   Проверь что загрузка завершилась успешно")


def verify_dataset():
    """Проверка что все файлы датасета присутствуют"""
    required_files = [
        "train_transaction.csv",
        "train_identity.csv",
        "test_transaction.csv",
        "test_identity.csv",
    ]

    logger.info("🔍 Проверка файлов датасета...")
    missing_files = []

    for file in required_files:
        file_path = DATA_DIR / file
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"   ✅ {file} ({size_mb:.1f} MB)")
        else:
            missing_files.append(file)
            logger.warning(f"   ❌ {file} - НЕ НАЙДЕН")

    if missing_files:
        logger.error(f"❌ Отсутствуют файлы: {missing_files}")
        sys.exit(1)

    logger.info("✅ Все файлы датасета присутствуют!")
    return True


def print_dataset_info():
    """Вывести информацию о датасете"""
    logger.info("\n" + "="*60)
    logger.info("📊 ИНФОРМАЦИЯ О IEEE-CIS FRAUD DETECTION ДАТАСЕТЕ")
    logger.info("="*60)

    try:
        import pandas as pd

        train_trans = pd.read_csv(DATA_DIR / "train_transaction.csv", nrows=5)
        train_ident = pd.read_csv(DATA_DIR / "train_identity.csv", nrows=5)

        logger.info(f"\n📋 Train Transaction Shape: {train_trans.shape}")
        logger.info(f"   Колонки: {list(train_trans.columns[:10])}... (+{len(train_trans.columns)-10} more)")

        logger.info(f"\n📋 Train Identity Shape: {train_ident.shape}")
        logger.info(f"   Колонки: {list(train_ident.columns)}")

        logger.info("\n📌 Данные готовы к обработке!")
        logger.info(f"   Расположение: {DATA_DIR}")

    except Exception as e:
        logger.warning(f"⚠️  Не удалось вывести информацию: {e}")


def main():
    """Главная функция"""
    logger.info("="*60)
    logger.info("🔽 IEEE-CIS FRAUD DETECTION DATASET DOWNLOADER")
    logger.info("="*60)

    check_kaggle_setup()
    download_dataset()
    extract_dataset()
    verify_dataset()
    print_dataset_info()

    logger.info("\n✅ Подготовка данных завершена!")
    logger.info("   Следующий шаг: python scripts/prepare_data.py")


if __name__ == "__main__":
    main()
