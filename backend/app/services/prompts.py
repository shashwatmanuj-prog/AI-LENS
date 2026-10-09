"""Prompts sent to Gemma 4."""

from __future__ import annotations

from datetime import date

from app.config import SUPPORTED_LANGUAGES

SYSTEM_PROMPT = """You are CommunityLens, an assistant that reads real-world documents for Indian communities:
government notices, college announcements, scholarship and exam posters, forms and circulars.

Rules you must follow:
- Only report what is actually visible in the document. Never guess dates, fees, URLs or eligibility.
- If text is blurry, cut off or ambiguous, say so in "warnings" instead of inventing a value.
- "source_text" must be copied character-for-character from the document, in the document's own
  language and script, so that it can be checked against official websites later.
- Copy URLs exactly as printed. Do not add URLs that are not printed in the document.
- You do not decide whether anything is verified or official. Another system does that.
- Flag signs of a possible scam (requests for payment to personal accounts, urgency pressure,
  unofficial email domains, mismatched logos) in "warnings".
- Respond with a single JSON object and nothing else."""

_SCHEMA = """{
  "document_type": "government_notice | college_announcement | scholarship | exam | job | event_poster | form | other",
  "title": "short title",
  "issuing_authority": "organisation that issued it, or null",
  "summary": "3-5 sentence plain-language summary for an ordinary citizen",
  "language_detected": "language(s) the document is written in",
  "key_facts": [
    {"id": "f1", "label": "what this is", "value": "the fact, explained simply",
     "source_text": "exact text copied from the document",
     "category": "deadline | eligibility | fee | requirement | contact | location | other",
     "confidence": "high | medium | low"}
  ],
  "deadlines": [
    {"id": "d1", "label": "what is due", "date": "YYYY-MM-DD or null if unclear", "time": "time or null",
     "source_text": "exact text copied from the document"}
  ],
  "eligibility": ["who can apply / who this applies to"],
  "required_documents": ["documents the reader must keep ready"],
  "instructions": ["instructions given in the document, in order"],
  "checklist": [
    {"id": "c1", "step": "short imperative action", "detail": "how to do it", "due_date": "YYYY-MM-DD or null"}
  ],
  "official_links": ["URLs printed in the document, exactly as printed"],
  "contacts": [{"type": "phone | email | website | address | other", "value": "..."}],
  "warnings": ["unclear parts, missing information, or scam signals"]
}"""


def extraction_prompt(language: str, page_count: int, pdf_text: str | None, today: date | None = None) -> str:
    lang_name = SUPPORTED_LANGUAGES[language]
    today = today or date.today()
    parts = [
        f"Today's date is {today.isoformat()}.",
        f"The document is provided as {page_count} image(s), one per page, in order.",
        "Extract the information below. Write label, value, summary, eligibility, required_documents, "
        f"instructions, checklist and warnings in {lang_name}. Keep source_text and official_links "
        "exactly as they appear in the document (do not translate them).",
        "Turn the document into a practical checklist a first-time applicant could follow, "
        "ordered by what must happen first. Only include steps supported by the document.",
        "Return JSON matching this shape:",
        _SCHEMA,
    ]
    if pdf_text:
        parts.append(
            "The PDF also has an embedded text layer, given below to help you read small print. "
            "If it conflicts with what you see in the images, trust the images and add a warning.\n"
            "<pdf_text>\n" + pdf_text[:12000] + "\n</pdf_text>"
        )
    return "\n\n".join(parts)


def translation_prompt(language: str, extraction_json: str) -> str:
    lang_name = SUPPORTED_LANGUAGES[language]
    return (
        f"Translate the human-readable fields of this JSON into {lang_name}: title, summary, every "
        "'label', 'value', 'step', 'detail', and every string in eligibility, required_documents, "
        "instructions and warnings. Do NOT change ids, dates, source_text, official_links, contacts, "
        "category, confidence or document_type. Do not add or remove items. "
        "Return only the translated JSON object.\n\n" + extraction_json
    )


def repair_prompt(bad_output: str) -> str:
    return (
        "The following was supposed to be a single valid JSON object but could not be parsed. "
        "Return the same content as one valid JSON object and nothing else.\n\n" + bad_output[:20000]
    )
