"""Process-wide singletons, overridable in tests via FastAPI dependency_overrides."""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.gemma import GemmaClient, GemmaUnavailableError, VisionModel
from app.services.storage import Repository, build_repository
from app.services.verifier import HttpPageFetcher, PageFetcher


@lru_cache
def _repo() -> Repository:
    return build_repository(get_settings())


@lru_cache
def _gemma() -> GemmaClient:
    return GemmaClient(get_settings())


def get_repo() -> Repository:
    return _repo()


def get_model() -> VisionModel:
    try:
        return _gemma()
    except GemmaUnavailableError:
        _gemma.cache_clear()
        raise


def get_fetcher() -> PageFetcher:
    s = get_settings()
    return HttpPageFetcher(timeout_s=s.verify_timeout_s, extra_domains=s.extra_official_domains)
