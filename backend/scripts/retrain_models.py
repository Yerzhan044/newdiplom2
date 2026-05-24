#!/usr/bin/env python3
"""
Переобучение моделей на синтетическом IEEE-CIS датасете
"""

import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
import xgboost as xgb
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path("/home/yerzhan/Desktop/new_diplom/data/ieee_cis")
MODELS_DIR = Path("/home/yerzhan/Desktop/new_diplom/data/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

logger.info("🔨 ПЕРЕОБУЧЕНИЕ МОДЕЛЕЙ НА СИНТЕТИЧЕСКИХ ДАННЫХ")
logger.info("=" * 60)

# Загружаем данные
train_file = DATA_DIR / "train_transaction.csv"
logger.info(f"\n📂 Загрузка данных из {train_file}...")
df = pd.read_csv(train_file)  # Используем ВСЕ данные!

logger.info(f"✓ Загружено {len(df)} транзакций")

# Подготовка признаков (как в evaluate_ieee_cis.py)
from sklearn.preprocessing import LabelEncoder

# Кодируем категориальные колонки
df_encoded = df.copy()
categorical_cols = df_encoded.select_dtypes(include=['object']).columns
for col in categorical_cols:
    le = LabelEncoder()
    df_encoded[col] = le.fit_transform(df_encoded[col].astype(str))

# Выбираем все числовые (кроме isFraud)
numeric_cols = df_encoded.select_dtypes(include=[np.number]).columns
numeric_cols = [col for col in numeric_cols if col != 'isFraud']
X = df_encoded[numeric_cols].values
y = df_encoded['isFraud'].values

logger.info(f"✓ Признаков: {X.shape[1]}, Класс баланс: {y.mean():.3f}")

# Нормализация
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Разделяем данные
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, stratify=y)

logger.info(f"\n📊 Train/Test split: {len(X_train)}/{len(X_test)}")
logger.info(f"✓ Скейлер сохранен")

# ═══════════════════════════════════════════════════════════════
# 1. XGBoost
# ═══════════════════════════════════════════════════════════════
logger.info("\n🌳 Обучение XGBoost...")
xgb_model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=28,  # Для дисбаланса классов
    random_state=42,
    n_jobs=-1
)
xgb_model.fit(X_train, y_train, verbose=0)
xgb_f1 = f1_score(y_test, (xgb_model.predict_proba(X_test)[:, 1] >= 0.5).astype(int))
xgb_auc = roc_auc_score(y_test, xgb_model.predict_proba(X_test)[:, 1])
logger.info(f"✓ XGBoost: F1={xgb_f1:.4f}, AUC={xgb_auc:.4f}")

# ═══════════════════════════════════════════════════════════════
# 2. Random Forest
# ═══════════════════════════════════════════════════════════════
logger.info("\n🌲 Обучение Random Forest...")
rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=15,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
rf_model.fit(X_train, y_train)
rf_f1 = f1_score(y_test, rf_model.predict(X_test))
rf_auc = roc_auc_score(y_test, rf_model.predict_proba(X_test)[:, 1])
logger.info(f"✓ Random Forest: F1={rf_f1:.4f}, AUC={rf_auc:.4f}")

# ═══════════════════════════════════════════════════════════════
# 3. Isolation Forest
# ═══════════════════════════════════════════════════════════════
logger.info("\n🔍 Обучение Isolation Forest...")
iso_model = IsolationForest(contamination=0.035, random_state=42, n_jobs=-1)
iso_model.fit(X_train)  # Обучаем на train данных!
iso_scores_test = -iso_model.score_samples(X_test)  # Инвертируем для вероятности
iso_scores = (iso_scores_test - iso_scores_test.min()) / (iso_scores_test.max() - iso_scores_test.min())
iso_f1 = f1_score(y_test, (iso_scores >= 0.5).astype(int))
iso_auc = roc_auc_score(y_test, iso_scores)
logger.info(f"✓ Isolation Forest: F1={iso_f1:.4f}, AUC={iso_auc:.4f}")

# ═══════════════════════════════════════════════════════════════
# 4. Meta-Learner (Logistic Regression на предсказаниях)
# ═══════════════════════════════════════════════════════════════
logger.info("\n🎯 Обучение Meta-Learner...")
iso_scores_train = -iso_model.score_samples(X_train)
iso_scores_train = (iso_scores_train - iso_scores_train.min()) / (iso_scores_train.max() - iso_scores_train.min())

meta_X = np.column_stack([
    xgb_model.predict_proba(X_train)[:, 1],
    rf_model.predict_proba(X_train)[:, 1],
    iso_scores_train,
])

meta_model = LogisticRegression(random_state=42)
meta_model.fit(meta_X, y_train)

# Оценка
meta_test_X = np.column_stack([
    xgb_model.predict_proba(X_test)[:, 1],
    rf_model.predict_proba(X_test)[:, 1],
    iso_scores,
])
meta_preds = meta_model.predict_proba(meta_test_X)[:, 1]
meta_f1 = f1_score(y_test, (meta_preds >= 0.5).astype(int))
meta_auc = roc_auc_score(y_test, meta_preds)
logger.info(f"✓ Meta-Learner: F1={meta_f1:.4f}, AUC={meta_auc:.4f}")

# ═══════════════════════════════════════════════════════════════
# 5. Ensemble (средневзвешенное)
# ═══════════════════════════════════════════════════════════════
logger.info("\n⭐ ENSEMBLE РЕЗУЛЬТАТЫ:")
ensemble_scores = (
    xgb_model.predict_proba(X_test)[:, 1] * 0.3 +
    rf_model.predict_proba(X_test)[:, 1] * 0.25 +
    iso_scores * 0.2 +
    meta_preds * 0.25
)
ensemble_f1 = f1_score(y_test, (ensemble_scores >= 0.5).astype(int))
ensemble_auc = roc_auc_score(y_test, ensemble_scores)
logger.info(f"✓ ENSEMBLE: F1={ensemble_f1:.4f}, AUC={ensemble_auc:.4f}")

logger.info(f"\n🎯 ТРЕБУЕМЫЕ МЕТРИКИ:")
logger.info(f"  F1-Score:  {ensemble_f1:.4f} (требуется 0.90) {'✅' if ensemble_f1 >= 0.90 else '❌'}")
logger.info(f"  AUC-ROC:   {ensemble_auc:.4f} (требуется 0.96) {'✅' if ensemble_auc >= 0.96 else '❌'}")

# Сохраняем модели
logger.info(f"\n💾 Сохранение моделей в {MODELS_DIR}...")
with open(MODELS_DIR / "xgboost_model.pkl", "wb") as f:
    pickle.dump(xgb_model, f)
with open(MODELS_DIR / "rf_model.pkl", "wb") as f:
    pickle.dump(rf_model, f)
with open(MODELS_DIR / "iso_model.pkl", "wb") as f:
    pickle.dump(iso_model, f)
with open(MODELS_DIR / "meta_model.pkl", "wb") as f:
    pickle.dump(meta_model, f)
with open(MODELS_DIR / "scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)

logger.info("✅ Все модели сохранены")
logger.info("\n" + "=" * 60)
logger.info("✅ ПЕРЕОБУЧЕНИЕ ЗАВЕРШЕНО")
