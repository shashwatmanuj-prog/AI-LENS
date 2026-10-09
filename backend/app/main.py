from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import SUPPORTED_LANGUAGES, get_settings
from app.deps import get_repo
from app.routers import analyses

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()  # fails fast if GEMMA_MODEL is not a Gemma 4 model

app = FastAPI(
    title="CommunityLens AI",
    version="0.1.0",
    description="Multimodal community intelligence powered by Gemma 4.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(analyses.router)


@app.get("/api/health")
async def health() -> dict:
    """Readiness info for the UI. Never returns secrets."""
    return {
        "status": "ok",
        "model": settings.gemma_model,
        "gemma_configured": settings.gemma_configured,
        "storage": get_repo().backend,
        "languages": SUPPORTED_LANGUAGES,
        "max_upload_mb": settings.max_upload_mb,
        "source_discovery": settings.source_discovery,
    }
