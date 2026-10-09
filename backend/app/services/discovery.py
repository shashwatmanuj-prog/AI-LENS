"""Find candidate official pages when the document prints no usable link.

Gemma 4 with Google Search grounding (documented as supported on the Gemini API)
proposes pages; we only keep URLs whose final host is an allow-listed official
domain. Gemma's role here is search, never judgement: the verifier still does
the literal matching.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from app.schemas import Extraction
from app.services.gemma import GemmaClient
from app.services.verifier import is_official_host

log = logging.getLogger(__name__)

GROUNDING_REDIRECT_HOST = "vertexaisearch.cloud.google.com"


async def _resolve_grounding_redirect(url: str, timeout_s: int) -> str | None:
    if urlparse(url).hostname != GROUNDING_REDIRECT_HOST:
        return url
    import httpx

    try:
        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=False) as client:
            resp = await client.get(url)
            return resp.headers.get("location")
    except httpx.HTTPError:
        return None


async def discover_official_urls(
    client: GemmaClient, extraction: Extraction, extra_domains: tuple[str, ...], timeout_s: int = 10
) -> list[str]:
    from google.genai import types

    subject = extraction.title
    if extraction.issuing_authority:
        subject += f" issued by {extraction.issuing_authority}"
    prompt = (
        f"Find the official government or institutional web page for: {subject}. "
        "Prefer pages on .gov.in, .nic.in or .ac.in domains. Reply with one sentence."
    )
    try:
        response = await client._client.aio.models.generate_content(
            model=client.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
        )
    except Exception as exc:
        log.info("Source discovery skipped: %s", exc)
        return []

    urls: list[str] = []
    for cand in response.candidates or []:
        meta = getattr(cand, "grounding_metadata", None)
        for chunk in (getattr(meta, "grounding_chunks", None) or []):
            web = getattr(chunk, "web", None)
            if web and web.uri:
                final = await _resolve_grounding_redirect(web.uri, timeout_s)
                if final and is_official_host(urlparse(final).hostname, extra_domains) and final not in urls:
                    urls.append(final)
    return urls[:3]
