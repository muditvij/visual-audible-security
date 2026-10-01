"""
Central Configuration Settings for EchoSense.
Loads parameters from environment variables with production defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    # Server & Network
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    SERVER_DEBUG: bool = os.getenv("SERVER_DEBUG", "False").lower() in ("true", "1")
    BACKEND_SECRET_KEY: str = os.getenv("BACKEND_SECRET_KEY", "echosense-prod-sec-key-replace-with-uuid4")

    # Device Authentication
    ESP32_API_KEY: str = os.getenv("ESP32_API_KEY", "esp32_auth_token_9472e0a4f5b18")
    ESP8266_API_KEY: str = os.getenv("ESP8266_API_KEY", "esp8266_auth_token_38c92a17df40c")

    # Audio Pipeline
    AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
    AUDIO_CHANNELS: int = int(os.getenv("AUDIO_CHANNELS", "1"))
    AUDIO_SAMPLE_WIDTH: int = int(os.getenv("AUDIO_SAMPLE_WIDTH", "2"))
    AUDIO_WINDOW_SECONDS: float = float(os.getenv("AUDIO_WINDOW_SECONDS", "0.975"))
    AUDIO_STEP_SECONDS: float = float(os.getenv("AUDIO_STEP_SECONDS", "0.5"))
    AUDIO_RMS_THRESHOLD: float = float(os.getenv("AUDIO_RMS_THRESHOLD", "0.015"))
    AUDIO_SILENCE_SNR_DB: float = float(os.getenv("AUDIO_SILENCE_SNR_DB", "12.0"))

    # YAMNet & Validation
    YAMNET_CONFIDENCE_LOW: float = float(os.getenv("YAMNET_CONFIDENCE_LOW", "0.45"))
    YAMNET_CONFIDENCE_VALID: float = float(os.getenv("YAMNET_CONFIDENCE_VALID", "0.65"))
    YAMNET_CONFIDENCE_HIGH: float = float(os.getenv("YAMNET_CONFIDENCE_HIGH", "0.80"))
    TEMPORAL_VALIDATION_WINDOWS: int = int(os.getenv("TEMPORAL_VALIDATION_WINDOWS", "3"))
    TEMPORAL_REQUIRED_CONFIRMATIONS: int = int(os.getenv("TEMPORAL_REQUIRED_CONFIRMATIONS", "2"))
    EVENT_COOLDOWN_SECONDS: float = float(os.getenv("EVENT_COOLDOWN_SECONDS", "25.0"))

    # WhatsApp Notifications
    WHATSAPP_PROVIDER: str = os.getenv("WHATSAPP_PROVIDER", "mock").lower()
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")

    # Twilio Fallback
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "+14155238886")

    # Notification & Contact Limits
    MAX_EMERGENCY_CONTACTS: int = int(os.getenv("MAX_EMERGENCY_CONTACTS", "5"))
    WHATSAPP_RATE_LIMIT_SECONDS: float = float(os.getenv("WHATSAPP_RATE_LIMIT_SECONDS", "15.0"))
    NOTIFY_ON_CRITICAL: bool = os.getenv("NOTIFY_ON_CRITICAL", "True").lower() in ("true", "1")
    NOTIFY_ON_SOS: bool = os.getenv("NOTIFY_ON_SOS", "True").lower() in ("true", "1")
    NOTIFY_ON_WARNING: bool = os.getenv("NOTIFY_ON_WARNING", "False").lower() in ("true", "1")

    # Heartbeat
    HEARTBEAT_TIMEOUT_SECONDS: float = float(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "10.0"))

settings = Settings()
