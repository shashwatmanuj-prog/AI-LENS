
"""Runtime configuration, read from environment variables only.

No secret has a default value. Missing keys degrade features explicitly
(e.g. no Supabase -> in-memory store) rather than failing silently.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from dataclasses import dataclass, field

from dotenv import load_dotenv


# Load backend/.env.local before reading environment variables.
# config.py is located in backend/app/config.py.
BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env.local"

load_dotenv(ENV_FILE)

# Only Gemma 4 instruction-tuned models are accepted.
GEMMA4_MODEL_PATTERN = re.compile(r"^gemma-4-[a-z0-9-]+-it$")

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
}


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )

    gemma_model: str = field(
        default_factory=lambda: os.getenv(
            "GEMMA_MODEL", "gemma-4-26b-a4b-it"
        )
    )

    gemma_thinking: bool = field(
        default_factory=lambda: _bool("GEMMA_THINKING", False)
    )

    gemma_timeout_s: int = field(
        default_factory=lambda: _int("GEMMA_TIMEOUT_S", 120)
    )

    supabase_url: str | None = field(
        default_factory=lambda: os.getenv("SUPABASE_URL")
    )

    supabase_service_key: str | None = field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )

    supabase_bucket: str = field(
        default_factory=lambda: os.getenv("SUPABASE_BUCKET", "documents")
    )

    max_upload_mb: int = field(
        default_factory=lambda: _int("MAX_UPLOAD_MB", 10)
    )

    max_pdf_pages: int = field(
        default_factory=lambda: _int("MAX_PDF_PAGES", 6)
    )

    verify_timeout_s: int = field(
        default_factory=lambda: _int("VERIFY_TIMEOUT_S", 10)
    )

    verify_max_urls: int = field(
        default_factory=lambda: _int("VERIFY_MAX_URLS", 5)
    )

    # Let Gemma 4 + Google Search grounding propose official pages.
    source_discovery: bool = field(
        default_factory=lambda: _bool("ENABLE_SOURCE_DISCOVERY", True)
    )

    # Extra official domains, comma separated.
    extra_official_domains: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            domain.strip().lower()
            for domain in os.getenv("EXTRA_OFFICIAL_DOMAINS", "").split(",")
            if domain.strip()
        )
    )

    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS", "http://localhost:3000"
            ).split(",")
            if origin.strip()
        )
    )

    public_app_url: str = field(
        default_factory=lambda: os.getenv(
            "PUBLIC_APP_URL", "http://localhost:3000"
        )
    )

    @property
    def gemma_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    def validate_model(self) -> None:
        if not GEMMA4_MODEL_PATTERN.fullmatch(self.gemma_model):
            raise ValueError(
                f"GEMMA_MODEL='{self.gemma_model}' is not a "
                "Gemma 4 instruction-tuned model. "
                "CommunityLens only runs on Gemma 4 "
                "(e.g. gemma-4-26b-a4b-it or gemma-4-31b-it)."
            )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings

    if _settings is None:
        _settings = Settings()
        _settings.validate_model()

    return _settings


def reset_settings_for_tests() -> None:
    global _settings
    _settings = None
