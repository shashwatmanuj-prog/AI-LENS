from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import SUPPORTED_LANGUAGES, get_settings
from app.deps import get_fetcher, get_model, get_repo
from app.schemas import Analysis, AnalysisSummary
from app.services.discovery import discover_official_urls
from app.services.gemma import GemmaClient, GemmaUnavailableError, VisionModel, translate_extraction
from app.services.ingest import UnsupportedFileError
from app.services.json_utils import ModelOutputError
from app.services.pipeline import run_pipeline
from app.services.storage import Repository, new_share_slug, to_summary
from app.services.verifier import PageFetcher, normalise_url

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analyses"])

_COMMUNITY_RE = re.compile(r"^[\w][\w \-]{1,58}[\w]$", re.UNICODE)
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _clean_community(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    value = " ".join(value.split())
    if not _COMMUNITY_RE.match(value):
        raise HTTPException(422, "Community name: 3-60 letters, numbers, spaces or hyphens.")
    return value


def _check_lang(language: str) -> str:
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(422, f"language must be one of {sorted(SUPPORTED_LANGUAGES)}")
    return language


def _check_id(analysis_id: str) -> str:
    if not _UUID_RE.match(analysis_id):
        raise HTTPException(404, "Analysis not found.")
    return analysis_id


def _model_or_503() -> VisionModel:
    try:
        return get_model()
    except (GemmaUnavailableError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/analyze", response_model=Analysis)
async def analyze(
    file: UploadFile = File(...),
    language: str = Form("en"),
    official_url: str | None = Form(None),
    community: str | None = Form(None),
    model: VisionModel = Depends(_model_or_503),
    fetcher: PageFetcher = Depends(get_fetcher),
    repo: Repository = Depends(get_repo),
) -> Analysis:
    settings = get_settings()
    _check_lang(language)
    community = _clean_community(community)
    official = normalise_url(official_url) if official_url else None

    limit = settings.max_upload_mb * 1024 * 1024
    raw = await file.read(limit + 1)
    if len(raw) > limit:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB.")

    discover = None
    if settings.source_discovery and isinstance(model, GemmaClient):
        async def discover(extraction):  # noqa: E306
            return await discover_official_urls(
                model, extraction, settings.extra_official_domains, settings.verify_timeout_s
            )

    try:
        return await run_pipeline(
            raw=raw,
            file_name=file.filename or "upload",
            language=language,
            model=model,
            fetcher=fetcher,
            repo=repo,
            official_url=official,
            community=community,
            discover=discover,
            extra_domains=settings.extra_official_domains,
            max_pdf_pages=settings.max_pdf_pages,
            max_verify_urls=settings.verify_max_urls,
        )
    except UnsupportedFileError as exc:
        raise HTTPException(415, str(exc)) from exc
    except GemmaUnavailableError as exc:
        raise HTTPException(502, str(exc)) from exc
    except ModelOutputError as exc:
        log.warning("unparseable Gemma output: %s", exc)
        raise HTTPException(502, "Gemma 4 returned a response we could not read. Please try again.") from exc


@router.get("/analyses/{analysis_id}", response_model=Analysis)
async def get_analysis(analysis_id: str, repo: Repository = Depends(get_repo)) -> Analysis:
    a = await repo.get(_check_id(analysis_id))
    if not a:
        raise HTTPException(404, "Analysis not found.")
    return a


class TranslateRequest(BaseModel):
    language: str


@router.post("/analyses/{analysis_id}/translate", response_model=Analysis)
async def translate(
    analysis_id: str,
    body: TranslateRequest,
    repo: Repository = Depends(get_repo),
    model: VisionModel = Depends(_model_or_503),
) -> Analysis:
    lang = _check_lang(body.language)
    a = await repo.get(_check_id(analysis_id))
    if not a:
        raise HTTPException(404, "Analysis not found.")
    if lang == a.language or lang in a.translations:
        return a
    try:
        a.translations[lang] = await translate_extraction(model, a.extraction, lang)
    except (GemmaUnavailableError, ModelOutputError) as exc:
        raise HTTPException(502, f"Translation failed: {exc}") from exc
    await repo.save(a)
    return a


class ShareRequest(BaseModel):
    community: str | None = Field(default=None, max_length=60)


class ShareResponse(BaseModel):
    share_slug: str
    share_url: str
    community: str | None


@router.post("/analyses/{analysis_id}/share", response_model=ShareResponse)
async def share(analysis_id: str, body: ShareRequest, repo: Repository = Depends(get_repo)) -> ShareResponse:
    a = await repo.get(_check_id(analysis_id))
    if not a:
        raise HTTPException(404, "Analysis not found.")
    community = _clean_community(body.community) or a.community
    a.is_public = True
    a.community = community
    a.share_slug = a.share_slug or new_share_slug()
    await repo.save(a)
    base = get_settings().public_app_url.rstrip("/")
    return ShareResponse(share_slug=a.share_slug, share_url=f"{base}/s/{a.share_slug}", community=community)


@router.get("/shared/{slug}", response_model=Analysis)
async def get_shared(slug: str, repo: Repository = Depends(get_repo)) -> Analysis:
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,32}", slug):
        raise HTTPException(404, "Shared item not found.")
    a = await repo.get_by_slug(slug)
    if not a:
        raise HTTPException(404, "Shared item not found.")
    a.file_path = None  # never expose storage paths publicly
    return a


class SummariesRequest(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=100)


@router.post("/analyses/summaries", response_model=list[AnalysisSummary])
async def summaries(body: SummariesRequest, repo: Repository = Depends(get_repo)) -> list[AnalysisSummary]:
    ids = [i for i in body.ids if _UUID_RE.match(i)]
    return [to_summary(a) for a in await repo.list_by_ids(ids)]


@router.get("/communities/{community}", response_model=list[AnalysisSummary])
async def community_feed(community: str, repo: Repository = Depends(get_repo)) -> list[AnalysisSummary]:
    name = _clean_community(community)
    if not name:
        raise HTTPException(404, "Community not found.")
    return [to_summary(a) for a in await repo.list_community(name)]
