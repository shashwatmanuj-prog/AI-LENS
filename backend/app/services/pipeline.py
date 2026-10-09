"""Upload -> Gemma 4 analysis -> extraction -> official verification -> stored result."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable

from app.schemas import Analysis, Extraction
from app.services.gemma import VisionModel, extract_document
from app.services.ingest import prepare_document
from app.services.storage import Repository
from app.services.verifier import PageFetcher, verify

log = logging.getLogger(__name__)

Discoverer = Callable[[Extraction], Awaitable[list[str]]]


async def run_pipeline(
    *,
    raw: bytes,
    file_name: str,
    language: str,
    model: VisionModel,
    fetcher: PageFetcher,
    repo: Repository,
    official_url: str | None = None,
    community: str | None = None,
    discover: Discoverer | None = None,
    extra_domains: tuple[str, ...] = (),
    max_pdf_pages: int = 6,
    max_verify_urls: int = 5,
) -> Analysis:
    doc = prepare_document(raw, max_pages=max_pdf_pages)

    extraction, model_version = await extract_document(model, doc.images, language, doc.pdf_text)
    extraction.warnings = doc.notes + extraction.warnings

    discovered: list[str] = []
    has_printed_link = bool(extraction.official_links) or any(c.type == "website" for c in extraction.contacts)
    if discover and not official_url and not has_printed_link:
        try:
            discovered = await discover(extraction)
        except Exception as exc:  # discovery is best-effort
            log.info("source discovery failed: %s", exc)

    report = await verify(
        extraction,
        fetcher,
        user_url=official_url,
        discovered_urls=discovered,
        extra_domains=extra_domains,
        max_urls=max_verify_urls,
    )

    analysis_id = str(uuid.uuid4())
    ext = "pdf" if doc.kind == "pdf" else doc.mime_type.split("/")[-1]
    file_path = await repo.upload_file(f"{analysis_id}/original.{ext}", raw, doc.mime_type)

    analysis = Analysis(
        id=analysis_id,
        file_name=file_name[:200] or "upload",
        mime_type=doc.mime_type,
        file_path=file_path,
        language=language,  # type: ignore[arg-type]
        model=model_version,
        pages_analyzed=len(doc.images),
        extraction=extraction,
        verification=report,
        community=community,
    )
    await repo.save(analysis)
    return analysis
