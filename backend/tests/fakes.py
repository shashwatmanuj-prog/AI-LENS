"""Test doubles. The real Gemma 4 API is never called in tests."""

from __future__ import annotations

import json

from app.services.gemma import ImageInput, ModelReply
from app.services.verifier import FetchError, FetchedPage

SAMPLE_EXTRACTION = {
    "document_type": "scholarship",
    "title": "Post-Matric Scholarship 2026-27",
    "issuing_authority": "Department of Social Welfare, Karnataka",
    "summary": "Students can apply for the post-matric scholarship online.",
    "language_detected": "English",
    "key_facts": [
        {"id": "x", "label": "Last date", "value": "15 October 2026",
         "source_text": "Last date to apply: 15/10/2026", "category": "deadline", "confidence": "high"},
        {"id": "x", "label": "Income limit", "value": "Family income up to ₹2,50,000",
         "source_text": "Annual family income should not exceed Rs. 2,50,000", "category": "eligibility",
         "confidence": "high"},
        {"id": "x", "label": "Mode", "value": "Online only",
         "source_text": "Apply online only", "category": "requirement", "confidence": "high"},
    ],
    "deadlines": [
        {"id": "x", "label": "Application closes", "date": "2026-10-15", "time": None,
         "source_text": "Last date to apply: 15/10/2026"}
    ],
    "eligibility": ["Karnataka students in post-matric courses"],
    "required_documents": ["Aadhaar", "Income certificate"],
    "instructions": ["Register on the portal", "Upload documents"],
    "checklist": [{"id": "x", "step": "Register", "detail": "Create an account", "due_date": "2026-10-15"}],
    "official_links": ["https://ssp.postmatric.karnataka.gov.in", "http://scholarship-help.example.com"],
    "contacts": [{"type": "phone", "value": "080-12345678"}],
    "warnings": [],
}


class FakeModel:
    model_name = "gemma-4-26b-a4b-it"

    def __init__(self, replies: list[str] | None = None, version: str = "gemma-4-26b-a4b-it"):
        self.replies = replies or ["```json\n" + json.dumps(SAMPLE_EXTRACTION) + "\n```"]
        self.version = version
        self.calls: list[tuple[int, str]] = []

    async def generate(self, images: list[ImageInput], prompt: str) -> ModelReply:
        self.calls.append((len(images), prompt))
        text = self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]
        return ModelReply(text=text, model_version=self.version)


class FakeFetcher:
    def __init__(self, pages: dict[str, str] | None = None, errors: dict[str, str] | None = None):
        self.pages = pages or {}
        self.errors = errors or {}
        self.fetched: list[str] = []

    async def fetch(self, url: str) -> FetchedPage:
        self.fetched.append(url)
        if url in self.errors:
            raise FetchError(self.errors[url])
        if url not in self.pages:
            raise FetchError("Official site returned HTTP 404.")
        return FetchedPage(url=url, text=self.pages[url], title="Official page")


def png_bytes() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(buf, format="PNG")
    return buf.getvalue()
