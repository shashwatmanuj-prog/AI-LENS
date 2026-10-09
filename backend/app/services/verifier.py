"""Evidence-based verification against official websites.

The contract: a claim is `verified` only when every concrete value in it
(dates, amounts, numbers) literally appears on a page served from an
allow-listed official domain. Everything else is reported honestly as
partial / not found / unverified / not checkable.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin, urlparse

from app.schemas import (
    ClaimVerification,
    Extraction,
    FactCategory,
    SourceCheck,
    VerificationReport,
    VerificationStatus,
)
from app.services import text_match

log = logging.getLogger(__name__)

# Public suffixes reserved for government / academic institutions.
OFFICIAL_SUFFIXES: tuple[str, ...] = (
    "gov.in", "nic.in", "ac.in", "edu.in", "res.in", "gov", "edu", "mil", "int",
)

MAX_PAGE_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT = ("text/html", "application/xhtml+xml", "text/plain", "application/pdf")


class FetchError(Exception):
    pass


@dataclass
class FetchedPage:
    url: str
    text: str
    title: str | None = None


class PageFetcher(Protocol):
    async def fetch(self, url: str) -> FetchedPage: ...


def normalise_url(raw: str) -> str | None:
    raw = (raw or "").strip().rstrip(".,;)")
    if not raw:
        return None
    if not raw.lower().startswith(("http://", "https://")):
        raw = "https://" + raw.lstrip("/")
    parsed = urlparse(raw)
    if not parsed.hostname:
        return None
    return raw


def is_official_host(host: str | None, extra: tuple[str, ...] = ()) -> bool:
    if not host:
        return False
    host = host.lower().rstrip(".")
    try:
        ipaddress.ip_address(host)
        return False  # raw IPs are never "official"
    except ValueError:
        pass
    for suffix in OFFICIAL_SUFFIXES + tuple(extra):
        suffix = suffix.lower().lstrip(".")
        if host == suffix or host.endswith("." + suffix):
            # A bare public suffix like "gov.in" is not a site.
            return host != suffix or suffix in extra
    return False


def check_url_safety(url: str, extra: tuple[str, ...] = ()) -> str | None:
    """Return a reason string if the URL must not be fetched, else None."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return "Only http(s) links are checked."
    if parsed.username or parsed.password:
        return "Links with embedded credentials are not fetched."
    if parsed.port not in (None, 80, 443):
        return "Non-standard ports are not fetched."
    if not is_official_host(parsed.hostname, extra):
        return "Not an allow-listed official domain (e.g. .gov.in, .nic.in, .ac.in)."
    return None


def _resolves_to_public_ip(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


class HttpPageFetcher:
    """Fetches official pages with SSRF guards and per-hop domain checks."""

    def __init__(self, timeout_s: int = 10, extra_domains: tuple[str, ...] = (), max_redirects: int = 3):
        self.timeout_s = timeout_s
        self.extra = extra_domains
        self.max_redirects = max_redirects

    async def fetch(self, url: str) -> FetchedPage:
        import httpx

        current = url
        async with httpx.AsyncClient(
            timeout=self.timeout_s,
            follow_redirects=False,
            headers={"User-Agent": "CommunityLensVerifier/1.0 (+public-interest document checker)"},
        ) as client:
            for _ in range(self.max_redirects + 1):
                reason = check_url_safety(current, self.extra)
                if reason:
                    raise FetchError(reason)
                host = urlparse(current).hostname or ""
                if not await asyncio.to_thread(_resolves_to_public_ip, host):
                    raise FetchError("Host did not resolve to a public address.")
                try:
                    async with client.stream("GET", current) as resp:
                        if resp.status_code in (301, 302, 303, 307, 308):
                            location = resp.headers.get("location")
                            if not location:
                                raise FetchError("Redirect without a location.")
                            current = urljoin(current, location)
                            continue
                        if resp.status_code != 200:
                            raise FetchError(f"Official site returned HTTP {resp.status_code}.")
                        ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                        if ctype and ctype not in ALLOWED_CONTENT:
                            raise FetchError(f"Unsupported content type '{ctype}'.")
                        body = bytearray()
                        async for chunk in resp.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > MAX_PAGE_BYTES:
                                raise FetchError("Page too large to check.")
                except httpx.HTTPError as exc:
                    raise FetchError(f"Could not reach the official site ({exc.__class__.__name__}).") from exc
                return _to_page(current, bytes(body), ctype)
        raise FetchError("Too many redirects.")


def _to_page(url: str, body: bytes, ctype: str) -> FetchedPage:
    if ctype == "application/pdf" or body.startswith(b"%PDF-"):
        try:
            import fitz

            doc = fitz.open(stream=body, filetype="pdf")
            text = "\n".join(doc.load_page(i).get_text("text") for i in range(min(doc.page_count, 30)))
            doc.close()
            return FetchedPage(url=url, text=text, title=None)
        except Exception as exc:
            raise FetchError("Official PDF could not be read.") from exc
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(body, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else None
    return FetchedPage(url=url, text=soup.get_text(" "), title=title)


@dataclass
class _Claim:
    id: str
    label: str
    groups: list[text_match.TermGroup]


def build_claims(extraction: Extraction) -> list[_Claim]:
    claims: list[_Claim] = []
    for d in extraction.deadlines:
        claims.append(_Claim(d.id, d.label, text_match.extract_term_groups(d.source_text, d.date)))
    for f in extraction.key_facts:
        if f.category == FactCategory.contact:
            continue
        claims.append(_Claim(f.id, f.label, text_match.extract_term_groups(f.source_text)))
    return claims


def candidate_urls(extraction: Extraction, user_url: str | None, discovered: list[str] | None = None) -> list[str]:
    raw = list(extraction.official_links)
    raw += [c.value for c in extraction.contacts if c.type == "website"]
    if user_url:
        raw.insert(0, user_url)
    raw += discovered or []
    out: list[str] = []
    for r in raw:
        u = normalise_url(r)
        if u and u not in out:
            out.append(u)
    return out


_RANK = {
    VerificationStatus.verified: 3,
    VerificationStatus.partial: 2,
    VerificationStatus.not_found_on_source: 1,
}


def _match_claim(claim: _Claim, page: FetchedPage) -> ClaimVerification:
    display = text_match.normalise(page.text)
    search = display.lower()
    if len(search) != len(display):  # extremely rare casing edge-case
        display = search
    matched, missing, first_pos = [], [], None
    for group in claim.groups:
        pos = text_match.find_term(search, group)
        if pos:
            matched.append(group.label)
            first_pos = first_pos or pos
        else:
            missing.append(group.label)
    if matched and not missing:
        status = VerificationStatus.verified
    elif matched:
        status = VerificationStatus.partial
    else:
        status = VerificationStatus.not_found_on_source
    return ClaimVerification(
        claim_id=claim.id,
        claim_label=claim.label,
        status=status,
        source_url=page.url,
        evidence=text_match.snippet(display, *first_pos) if first_pos else None,
        matched_terms=matched,
        missing_terms=missing,
    )


def _overall(results: list[ClaimVerification], any_fetched: bool) -> VerificationStatus:
    checkable = [r for r in results if r.status != VerificationStatus.not_checkable]
    if not checkable:
        return VerificationStatus.not_checkable
    if not any_fetched:
        return VerificationStatus.unverified
    if all(r.status == VerificationStatus.verified for r in checkable):
        return VerificationStatus.verified
    if any(r.status in (VerificationStatus.verified, VerificationStatus.partial) for r in checkable):
        return VerificationStatus.partial
    return VerificationStatus.not_found_on_source


async def verify(
    extraction: Extraction,
    fetcher: PageFetcher,
    user_url: str | None = None,
    discovered_urls: list[str] | None = None,
    extra_domains: tuple[str, ...] = (),
    max_urls: int = 5,
) -> VerificationReport:
    sources: list[SourceCheck] = []
    official: list[str] = []
    for url in candidate_urls(extraction, user_url, discovered_urls):
        reason = check_url_safety(url, extra_domains)
        if reason:
            sources.append(SourceCheck(url=url, official=False, fetched=False, reason=reason))
        elif len(official) < max_urls:
            official.append(url)
        else:
            sources.append(SourceCheck(url=url, official=True, fetched=False, reason="Check limit reached."))

    async def _get(u: str):
        try:
            return u, await fetcher.fetch(u), None
        except FetchError as exc:
            return u, None, str(exc)
        except Exception as exc:  # never let one bad page break the report
            log.warning("verification fetch failed for %s: %s", u, exc)
            return u, None, "Unexpected error while fetching."

    pages: list[FetchedPage] = []
    for url, page, err in await asyncio.gather(*(_get(u) for u in official)):
        if page:
            pages.append(page)
            sources.append(SourceCheck(url=page.url, official=True, fetched=True, title=page.title))
        else:
            sources.append(SourceCheck(url=url, official=True, fetched=False, reason=err))

    results: list[ClaimVerification] = []
    for claim in build_claims(extraction):
        if not claim.groups:
            results.append(ClaimVerification(
                claim_id=claim.id, claim_label=claim.label, status=VerificationStatus.not_checkable
            ))
            continue
        best: ClaimVerification | None = None
        for page in pages:
            r = _match_claim(claim, page)
            if best is None or _RANK[r.status] > _RANK[best.status]:
                best = r
        results.append(best or ClaimVerification(
            claim_id=claim.id,
            claim_label=claim.label,
            status=VerificationStatus.unverified,
            missing_terms=[g.label for g in claim.groups],
        ))

    return VerificationReport(overall=_overall(results, bool(pages)), claims=results, sources=sources)
