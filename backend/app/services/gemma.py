"""Gemma 4 client (Gemini API, `google-genai` SDK).

Verified against https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api (Oct 2026):
model ids `gemma-4-31b-it` and `gemma-4-26b-a4b-it`, image input supported,
system instructions supported, thinking toggled via `thinking_level`.
PDF input and JSON mode are NOT documented for Gemma, so PDFs are rasterised to
images upstream and JSON is parsed from text.

There is deliberately no fallback model. If Gemma 4 fails, the request fails.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from app.config import Settings
from app.schemas import Extraction
from app.services import prompts
from app.services.json_utils import ModelOutputError, extract_json_object

log = logging.getLogger(__name__)


class GemmaUnavailableError(RuntimeError):
    """Gemma 4 could not be called (missing key, network, quota, wrong model)."""


@dataclass
class ImageInput:
    data: bytes
    mime_type: str


@dataclass
class ModelReply:
    text: str
    model_version: str | None


class VisionModel(Protocol):
    model_name: str

    async def generate(self, images: list[ImageInput], prompt: str) -> ModelReply: ...


class GemmaClient:
    """Thin async wrapper over google-genai, locked to a Gemma 4 model id."""

    def __init__(self, settings: Settings):
        settings.validate_model()
        if not settings.gemini_api_key:
            raise GemmaUnavailableError("GEMINI_API_KEY is not set. Get one from Google AI Studio.")
        from google import genai  # imported lazily so tests run without the SDK

        self._settings = settings
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = settings.gemma_model

    def _config(self):
        from google.genai import types

        kwargs = {"system_instruction": prompts.SYSTEM_PROMPT, "temperature": 0.1}
        level = "high" if self._settings.gemma_thinking else "minimal"
        try:
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=level)
        except (TypeError, ValueError, AttributeError):
            # Older SDKs lack thinking_level; the model default is used instead.
            log.warning("google-genai SDK does not support thinking_level; using model default")
        return types.GenerateContentConfig(**kwargs)

    async def generate(self, images: list[ImageInput], prompt: str) -> ModelReply:
        from google.genai import types

        contents: list = [types.Part.from_bytes(data=img.data, mime_type=img.mime_type) for img in images]
        contents.append(prompt)
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self.model_name, contents=contents, config=self._config()
                ),
                timeout=self._settings.gemma_timeout_s,
            )
        except asyncio.TimeoutError as exc:
            raise GemmaUnavailableError("Gemma 4 did not respond in time.") from exc
        except Exception as exc:  # SDK raises several error types; surface them honestly.
            raise GemmaUnavailableError(f"Gemma 4 request failed: {exc}") from exc

        version = getattr(response, "model_version", None)
        if version and not version.startswith("gemma-4"):
            raise GemmaUnavailableError(
                f"API answered with model '{version}', not Gemma 4. Refusing to use the result."
            )
        return ModelReply(text=response.text or "", model_version=version or self.model_name)


async def _generate_json(model: VisionModel, images: list[ImageInput], prompt: str) -> tuple[dict, str]:
    reply = await model.generate(images, prompt)
    try:
        return extract_json_object(reply.text), reply.model_version or model.model_name
    except ModelOutputError:
        log.info("Gemma output was not valid JSON; asking Gemma to repair it once")
        repaired = await model.generate([], prompts.repair_prompt(reply.text))
        return extract_json_object(repaired.text), repaired.model_version or model.model_name


def _assign_ids(data: dict) -> dict:
    """Guarantee stable, unique ids even if the model omits or repeats them."""
    for key, prefix in (("key_facts", "f"), ("deadlines", "d"), ("checklist", "c")):
        items = data.get(key) or []
        if not isinstance(items, list):
            data[key] = []
            continue
        for i, item in enumerate(items, start=1):
            if isinstance(item, dict):
                item["id"] = f"{prefix}{i}"
    return data


def _coerce_lists(data: dict) -> dict:
    for key in ("eligibility", "required_documents", "instructions", "official_links", "warnings"):
        value = data.get(key)
        if value is None:
            data[key] = []
        elif isinstance(value, str):
            data[key] = [value]
        else:
            data[key] = [str(v) for v in value if v not in (None, "")]
    return data


def parse_extraction(data: dict) -> Extraction:
    data = _coerce_lists(_assign_ids(dict(data)))
    try:
        return Extraction.model_validate(data)
    except ValidationError as exc:
        raise ModelOutputError(f"Gemma output did not match the expected structure: {exc}") from exc


async def extract_document(
    model: VisionModel, images: list[ImageInput], language: str, pdf_text: str | None = None
) -> tuple[Extraction, str]:
    if not images:
        raise ValueError("At least one page image is required.")
    prompt = prompts.extraction_prompt(language, len(images), pdf_text)
    data, version = await _generate_json(model, images, prompt)
    return parse_extraction(data), version


async def translate_extraction(model: VisionModel, extraction: Extraction, language: str) -> Extraction:
    prompt = prompts.translation_prompt(language, extraction.model_dump_json())
    data, _ = await _generate_json(model, [], prompt)
    translated = parse_extraction(data)
    # Never let translation alter what verification depends on.
    return _restore_invariants(extraction, translated)


def _restore_invariants(original: Extraction, translated: Extraction) -> Extraction:
    t = translated.model_copy(deep=True)
    t.official_links = original.official_links
    t.contacts = original.contacts
    t.document_type = original.document_type
    if len(t.key_facts) == len(original.key_facts):
        for new, old in zip(t.key_facts, original.key_facts):
            new.source_text, new.category, new.confidence = old.source_text, old.category, old.confidence
    else:
        t.key_facts = original.key_facts
    if len(t.deadlines) == len(original.deadlines):
        for new, old in zip(t.deadlines, original.deadlines):
            new.date, new.time, new.source_text = old.date, old.time, old.source_text
    else:
        t.deadlines = original.deadlines
    if len(t.checklist) == len(original.checklist):
        for new, old in zip(t.checklist, original.checklist):
            new.due_date = old.due_date
    else:
        t.checklist = original.checklist
    return t
