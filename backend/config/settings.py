from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",)
    )

    # Database (SQLite по умолчанию)
    database_url: str = "sqlite:///./fraud_detection.db"
    db_echo: bool = False

    # Server (Backend config)
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_debug: bool = False

    # API settings
    api_title: str = "Fraud Detection System API"
    api_version: str = "1.0.0"
    api_description: str = "Real-time fraud detection system for banking transactions"

    # Fraud scoring thresholds (для демонстрации)
    fraud_threshold_approved: float = 0.35  # < 35% = APPROVED
    fraud_threshold_review: float = 0.60    # 35%-60% = REVIEW
    fraud_threshold_blocked: float = 0.60   # >= 60% = BLOCKED

    # Model paths
    model_xgboost_path: str = "data/models/xgboost_model.joblib"
    model_randomforest_path: str = "data/models/randomforest_model.joblib"
    model_lstm_path: str = "data/models/lstm_model.h5"
    model_isolation_forest_path: str = "data/models/isolation_forest_model.joblib"
    model_meta_learner_path: str = "data/models/meta_learner.joblib"

    # AI / Groq API
    groq_api_key: str = ""
    generation_interval_seconds: int = 10

    # Network config
    main_server_host: str = "192.168.1.100"
    main_server_port: int = 8000
    client_a_host: str = "192.168.1.101"
    client_a_port: int = 8001
    client_b_host: str = "192.168.1.102"
    client_b_port: int = 8002

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "logs/fraud_detection.log"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
