"""
Configuration management for Model Tester Tool.
Loads API keys and settings from .env file.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class APIConfig:
    """Holds all API credentials and settings."""

    # OpenAI
    openai_api_key: str = ""

    # Google Cloud
    google_credentials_path: str = ""

    # Azure
    azure_speech_key: str = ""
    azure_speech_region: str = "eastus"

    # Anthropic
    anthropic_api_key: str = ""

    # Custom API
    custom_api_url: str = ""
    custom_api_key: str = ""

    # Audio settings
    sample_rate: int = 16000
    audio_channels: int = 1
    recording_duration: int = 10  # seconds

    # Output
    output_dir: str = str(PROJECT_ROOT / "output")

    def __post_init__(self):
        os.makedirs(self.output_dir, exist_ok=True)


def load_config() -> APIConfig:
    """Load configuration from environment variables."""
    return APIConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        google_credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        azure_speech_key=os.getenv("AZURE_SPEECH_KEY", ""),
        azure_speech_region=os.getenv("AZURE_SPEECH_REGION", "eastus"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        custom_api_url=os.getenv("CUSTOM_API_URL", ""),
        custom_api_key=os.getenv("CUSTOM_API_KEY", ""),
    )


@dataclass
class ProviderStatus:
    """Tracks which providers are configured and available."""
    openai: bool = False
    google: bool = False
    azure: bool = False
    local: bool = True  # Always available
    anthropic: bool = False
    custom: bool = False

    @classmethod
    def from_config(cls, config: APIConfig) -> "ProviderStatus":
        return cls(
            openai=bool(config.openai_api_key),
            google=bool(config.google_credentials_path),
            azure=bool(config.azure_speech_key),
            local=True,
            anthropic=bool(config.anthropic_api_key),
            custom=bool(config.custom_api_url),
        )


# Available TTS voices per provider
TTS_VOICES = {
    "openai": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
    "google": ["en-US-Neural2-A", "en-US-Neural2-B", "en-US-Neural2-C", "en-US-Neural2-D"],
    "azure": ["en-US-JennyNeural", "en-US-GuyNeural", "en-US-AriaNeural"],
    "local": ["default"],
}

# Available STT models per provider
STT_MODELS = {
    "openai": ["whisper-1"],
    "google": ["latest_long", "latest_short", "command_and_search", "phone_call"],
    "azure": ["conversation", "dictation"],
    "local": ["vosk-model-small-en-us-0.15"],
}

# Available LLM models
LLM_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
    "anthropic": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    "custom": ["custom-model"],
}
