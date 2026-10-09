"""Data contracts shared by the pipeline, API and tests."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

LanguageCode = Literal["en", "hi", "kn"]


class FactCategory(str, Enum):
    deadline = "deadline"
    eligibility = "eligibility"
    fee = "fee"
    requirement = "requirement"
    contact = "contact"
    location = "location"
    other = "other"


class KeyFact(BaseModel):
    id: str
    label: str
    value: str
    # Verbatim text copied from the document, in its original language.
    # Verification matches against this, never against the translated value.
    source_text: str = ""
    category: FactCategory = FactCategory.other
    confidence: Literal["high", "medium", "low"] = "medium"


class Deadline(BaseModel):
    id: str
    label: str
    date: str | None = None  # ISO YYYY-MM-DD when the model could read it
    time: str | None = None
    source_text: str = ""


class ChecklistItem(BaseModel):
    id: str
    step: str
    detail: str = ""
    due_date: str | None = None


class Contact(BaseModel):
    type: Literal["phone", "email", "website", "address", "other"] = "other"
    value: str


class Extraction(BaseModel):
    """What Gemma 4 returns after reading the document."""

    document_type: str = "other"
    title: str = "Untitled document"
    issuing_authority: str | None = None
    summary: str = ""
    language_detected: str | None = None
    key_facts: list[KeyFact] = Field(default_factory=list)
    deadlines: list[Deadline] = Field(default_factory=list)
    eligibility: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    official_links: list[str] = Field(default_factory=list)
    contacts: list[Contact] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VerificationStatus(str, Enum):
    # A claim's key terms were found on an allow-listed official page.
    verified = "verified"
    # Some, not all, key terms were found on an official page.
    partial = "partial"
    # An official page was fetched but the claim's terms did not appear on it.
    not_found_on_source = "not_found_on_source"
    # No official source could be reached or none was available.
    unverified = "unverified"
    # The claim has no concrete value (date, amount, number) that can be checked.
    not_checkable = "not_checkable"


class ClaimVerification(BaseModel):
    claim_id: str
    claim_label: str
    status: VerificationStatus
    source_url: str | None = None
    evidence: str | None = None  # snippet of the official page around the match
    matched_terms: list[str] = Field(default_factory=list)
    missing_terms: list[str] = Field(default_factory=list)


class SourceCheck(BaseModel):
    url: str
    official: bool
    fetched: bool
    reason: str | None = None  # why it was skipped / failed
    title: str | None = None


class VerificationReport(BaseModel):
    overall: VerificationStatus
    claims: list[ClaimVerification] = Field(default_factory=list)
    sources: list[SourceCheck] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    method: str = (
        "Key values (dates, amounts, numbers) copied verbatim from the document were searched "
        "for on allow-listed official websites. 'Verified' means the value literally appears on "
        "that page; the model's own judgement is never used to mark something verified."
    )


class Analysis(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    file_name: str
    mime_type: str
    file_path: str | None = None
    language: LanguageCode = "en"
    model: str
    pages_analyzed: int = 1
    extraction: Extraction
    verification: VerificationReport
    community: str | None = None
    share_slug: str | None = None
    is_public: bool = False
    translations: dict[str, Extraction] = Field(default_factory=dict)


class AnalysisSummary(BaseModel):
    id: str
    created_at: datetime
    title: str
    document_type: str
    issuing_authority: str | None = None
    overall: VerificationStatus
    next_deadline: str | None = None
    share_slug: str | None = None
    community: str | None = None
