#!/bin/bash

# Setup script for IEEE-CIS evaluation
# Подготовка всего необходимого для оценки на IEEE-CIS датасете

set -e

PROJECT_DIR="/home/yerzhan/Desktop/new_diplom"
DATA_DIR="$PROJECT_DIR/data/ieee_cis"
RESULTS_DIR="$PROJECT_DIR/evaluation_results"
SCRIPTS_DIR="$PROJECT_DIR/backend/scripts"

echo "════════════════════════════════════════════════════════════════"
echo "📊 IEEE-CIS FRAUD DETECTION EVALUATION SETUP"
echo "════════════════════════════════════════════════════════════════"

# 1. Создание директорий
echo ""
echo "📁 Создание директорий..."
mkdir -p "$DATA_DIR"
mkdir -p "$RESULTS_DIR"
mkdir -p "$SCRIPTS_DIR"
echo "   ✅ Директории созданы"

# 2. Проверка зависимостей
echo ""
echo "📦 Проверка зависимостей Python..."

python3 << 'EOF'
import sys
import subprocess

required_packages = [
    'pandas',
    'numpy',
    'scikit-learn',
    'tensorflow',
    'xgboost',
    'kaggle',
]

missing = []
for package in required_packages:
    try:
        __import__(package)
        print(f"   ✅ {package}")
    except ImportError:
        print(f"   ❌ {package} ОТСУТСТВУЕТ")
        missing.append(package)

if missing:
    print(f"\n⚠️  Устанавливаем недостающие пакеты: {', '.join(missing)}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + missing)
    print("   ✅ Пакеты установлены")
else:
    print("\n   ✅ Все зависимости установлены!")
EOF

# 3. Проверка Kaggle credentials
echo ""
echo "🔑 Проверка Kaggle credentials..."

if [ -f ~/.kaggle/kaggle.json ]; then
    echo "   ✅ Kaggle credentials найдены"
    echo ""
    echo "🚀 ГОТОВО К СКАЧИВАНИЮ!"
    echo ""
    echo "Запустите:"
    echo "   cd $PROJECT_DIR"
    echo "   python backend/scripts/evaluate_ieee_cis.py"
else
    echo "   ⚠️  Kaggle credentials НЕ найдены"
    echo ""
    echo "ТРЕБУЕТСЯ:"
    echo "   1. Перейдите на https://www.kaggle.com/settings/account"
    echo "   2. Нажмите 'Create New API Token'"
    echo "   3. Сохраните kaggle.json в ~/.kaggle/"
    echo ""
    echo "Или скачайте датасет вручную:"
    echo "   1. https://www.kaggle.com/competitions/ieee-cis-fraud-detection/data"
    echo "   2. Разместите CSV файлы в: $DATA_DIR"
    echo ""
    echo "После этого запустите:"
    echo "   python backend/scripts/evaluate_ieee_cis.py"
fi

# 4. Информация о размере
echo ""
echo "📊 Информация о датасете:"
echo "   • Размер: 590,540 транзакций"
echo "   • Классов: 2 (fraud/non-fraud)"
echo "   • Дисбаланс: ~3.5% fraud"
echo "   • Признаков: 394"
echo "   • Размер на диске: ~10 GB (распакованный)"

# 5. Проверка свободного места
echo ""
echo "💾 Проверка свободного места..."
FREE_SPACE=$(df "$PROJECT_DIR" | awk 'NR==2 {print $4}')
FREE_GB=$((FREE_SPACE / 1024 / 1024))

if [ $FREE_GB -gt 20 ]; then
    echo "   ✅ Свободного места: ${FREE_GB} GB (достаточно)"
else
    echo "   ⚠️  Свободного места: ${FREE_GB} GB (может быть недостаточно)"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ SETUP ЗАВЕРШЕНА!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Дальше прочитайте: $PROJECT_DIR/DOWNLOAD_IEEE_CIS.md"
echo ""
