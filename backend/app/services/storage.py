"""Persistence: Supabase (Postgres + Storage) with an in-memory fallback for local dev.

Only the backend talks to Supabase, using the service-role key. The browser never
receives a Supabase key, so Row Level Security can stay closed to the public.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from typing import Protocol

from app.config import Settings
from app.schemas import Analysis, AnalysisSummary

log = logging.getLogger(__name__)

TABLE = "analyses"


def new_share_slug() -> str:
    return secrets.token_urlsafe(8)


def to_summary(a: Analysis) -> AnalysisSummary:
    dated = sorted(d.date for d in a.extraction.deadlines if d.date)
    return AnalysisSummary(
        id=a.id,
        created_at=a.created_at,
        title=a.extraction.title,
        document_type=a.extraction.document_type,
        issuing_authority=a.extraction.issuing_authority,
        overall=a.verification.overall,
        next_deadline=dated[0] if dated else None,
        share_slug=a.share_slug if a.is_public else None,
        community=a.community,
    )


class Repository(Protocol):
    backend: str

    async def upload_file(self, path: str, data: bytes, mime_type: str) -> str | None: ...
    async def save(self, analysis: Analysis) -> None: ...
    async def get(self, analysis_id: str) -> Analysis | None: ...
    async def get_by_slug(self, slug: str) -> Analysis | None: ...
    async def list_by_ids(self, ids: list[str]) -> list[Analysis]: ...
    async def list_community(self, community: str, limit: int = 30) -> list[Analysis]: ...


class InMemoryRepository:
    """Process-local store. Data is lost on restart; fine for demos and tests."""

    backend = "memory"

    def __init__(self) -> None:
        self._items: dict[str, Analysis] = {}

    async def upload_file(self, path: str, data: bytes, mime_type: str) -> str | None:
        return None  # files are not retained without Supabase

    async def save(self, analysis: Analysis) -> None:
        self._items[analysis.id] = analysis.model_copy(deep=True)

    async def get(self, analysis_id: str) -> Analysis | None:
        a = self._items.get(analysis_id)
        return a.model_copy(deep=True) if a else None

    async def get_by_slug(self, slug: str) -> Analysis | None:
        for a in self._items.values():
            if a.share_slug == slug and a.is_public:
                return a.model_copy(deep=True)
        return None

    async def list_by_ids(self, ids: list[str]) -> list[Analysis]:
        return [self._items[i].model_copy(deep=True) for i in ids if i in self._items]

    async def list_community(self, community: str, limit: int = 30) -> list[Analysis]:
        items = [a for a in self._items.values() if a.is_public and (a.community or "").lower() == community.lower()]
        items.sort(key=lambda a: a.created_at, reverse=True)
        return [a.model_copy(deep=True) for a in items[:limit]]


class SupabaseRepository:
    backend = "supabase"

    def __init__(self, settings: Settings):
        from supabase import create_client

        self._client = create_client(settings.supabase_url, settings.supabase_service_key)
        self._bucket = settings.supabase_bucket

    async def upload_file(self, path: str, data: bytes, mime_type: str) -> str | None:
        def _up():
            self._client.storage.from_(self._bucket).upload(
                path, data, {"content-type": mime_type, "upsert": "false"}
            )
            return path

        try:
            return await asyncio.to_thread(_up)
        except Exception as exc:
            log.warning("Supabase storage upload failed: %s", exc)
            return None

    @staticmethod
    def _row(a: Analysis) -> dict:
        data = a.model_dump(mode="json")
        return {
            "id": a.id,
            "created_at": data["created_at"],
            "file_name": a.file_name,
            "mime_type": a.mime_type,
            "file_path": a.file_path,
            "language": a.language,
            "model": a.model,
            "pages_analyzed": a.pages_analyzed,
            "extraction": data["extraction"],
            "verification": data["verification"],
            "translations": data["translations"],
            "community": a.community,
            "share_slug": a.share_slug,
            "is_public": a.is_public,
            "title": a.extraction.title,
        }

    @staticmethod
    def _from_row(row: dict) -> Analysis:
        return Analysis.model_validate({k: v for k, v in row.items() if k != "title"})

    async def save(self, analysis: Analysis) -> None:
        await asyncio.to_thread(lambda: self._client.table(TABLE).upsert(self._row(analysis)).execute())

    async def _one(self, column: str, value: str, public_only: bool = False) -> Analysis | None:
        def _q():
            q = self._client.table(TABLE).select("*").eq(column, value)
            if public_only:
                q = q.eq("is_public", True)
            return q.limit(1).execute()

        res = await asyncio.to_thread(_q)
        return self._from_row(res.data[0]) if res.data else None

    async def get(self, analysis_id: str) -> Analysis | None:
        return await self._one("id", analysis_id)

    async def get_by_slug(self, slug: str) -> Analysis | None:
        return await self._one("share_slug", slug, public_only=True)

    async def list_by_ids(self, ids: list[str]) -> list[Analysis]:
        if not ids:
            return []
        res = await asyncio.to_thread(
            lambda: self._client.table(TABLE).select("*").in_("id", ids).order("created_at", desc=True).execute()
        )
        return [self._from_row(r) for r in res.data]

    async def list_community(self, community: str, limit: int = 30) -> list[Analysis]:
        # ilike without wildcards = case-insensitive equality; escape LIKE metacharacters.
        community = community.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        res = await asyncio.to_thread(
            lambda: self._client.table(TABLE)
            .select("*")
            .eq("is_public", True)
            .ilike("community", community)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [self._from_row(r) for r in res.data]


def build_repository(settings: Settings) -> Repository:
    if settings.supabase_configured:
        try:
            return SupabaseRepository(settings)
        except Exception as exc:
            log.error("Supabase is configured but could not initialise (%s); using in-memory store", exc)
    else:
        log.warning("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set; using in-memory store")
    return InMemoryRepository()
