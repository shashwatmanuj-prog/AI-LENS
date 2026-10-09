"""Deterministic text normalisation and claim-term matching.

A "term group" is a set of equivalent spellings of one value (e.g. a date written
as 15-10-2026, 15 October 2026, 15 अक्टूबर 2026). A group matches if any of its
variants appears in the page. No fuzzy matching, no model involvement.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

_DIGIT_MAP = {ord(c): str(i) for i, c in enumerate("०१२३४५६७८९")}
_DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate("೦೧೨೩೪೫೬೭೮೯")})

MONTHS_EN = [
    ("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"),
    ("may", "may"), ("june", "jun"), ("july", "jul"), ("august", "aug"),
    ("september", "sep"), ("october", "oct"), ("november", "nov"), ("december", "dec"),
]
MONTHS_HI = [
    ("जनवरी",), ("फरवरी", "फ़रवरी"), ("मार्च",), ("अप्रैल",), ("मई",), ("जून",),
    ("जुलाई",), ("अगस्त",), ("सितंबर", "सितम्बर"), ("अक्टूबर",), ("नवंबर", "नवम्बर"), ("दिसंबर", "दिसम्बर"),
]
MONTHS_KN = [
    ("ಜನವರಿ",), ("ಫೆಬ್ರವರಿ",), ("ಮಾರ್ಚ್",), ("ಏಪ್ರಿಲ್",), ("ಮೇ",), ("ಜೂನ್",),
    ("ಜುಲೈ",), ("ಆಗಸ್ಟ್",), ("ಸೆಪ್ಟೆಂಬರ್",), ("ಅಕ್ಟೋಬರ್",), ("ನವೆಂಬರ್",), ("ಡಿಸೆಂಬರ್",),
]

_MONTH_LOOKUP: dict[str, int] = {}
for _i, names in enumerate(MONTHS_EN, start=1):
    for _n in names:
        _MONTH_LOOKUP[_n] = _i
_MONTH_LOOKUP["sept"] = 9
for _table in (MONTHS_HI, MONTHS_KN):
    for _i, names in enumerate(_table, start=1):
        for _n in names:
            _MONTH_LOOKUP[unicodedata.normalize("NFC", _n)] = _i

_NUMERIC_DATE = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})(?!\d)")
_ORDINAL = re.compile(r"(?<=\d)(st|nd|rd|th)\b", re.IGNORECASE)
_DIGIT_COMMA = re.compile(r"(?<=\d),(?=\d)")
_WS = re.compile(r"\s+")
_LETTER = r"A-Za-zऀ-ॿಀ-೿"
_DIGIT_WORD_HYPHEN = re.compile(rf"(?<=\d)-(?=[{_LETTER}])|(?<=[{_LETTER}])-(?=\d)")
_ABBR_DOT = re.compile(r"(?<=\b[A-Za-z]{3})\.(?=\s|\d)|(?<=\b[A-Za-z]{4})\.(?=\s|\d)")


def normalise(text: str) -> str:
    """Normalise text for matching. Length-changing but script-preserving."""
    text = unicodedata.normalize("NFC", text or "").translate(_DIGIT_MAP)
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = _DIGIT_COMMA.sub("", text)
    text = _ORDINAL.sub("", text)
    text = _NUMERIC_DATE.sub(lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}", text)
    # "15-Oct-2026" -> "15 Oct 2026"; "Oct. 15" -> "Oct 15"
    text = _DIGIT_WORD_HYPHEN.sub(" ", text)
    text = _ABBR_DOT.sub("", text)
    text = text.replace(",", " ")
    text = _WS.sub(" ", text)
    return text.strip()


def search_form(text: str) -> str:
    return normalise(text).lower()


def date_variants(d: date) -> list[str]:
    dd, mm, yyyy, yy = f"{d.day:02d}", f"{d.month:02d}", str(d.year), str(d.year)[2:]
    day, mon = str(d.day), str(d.month)
    full, short = MONTHS_EN[d.month - 1]
    variants = {
        f"{dd}-{mm}-{yyyy}", f"{day}-{mon}-{yyyy}", f"{dd}-{mm}-{yy}", f"{yyyy}-{mm}-{dd}",
        f"{day} {full} {yyyy}", f"{dd} {full} {yyyy}", f"{day} {short} {yyyy}", f"{dd} {short} {yyyy}",
        f"{full} {day} {yyyy}", f"{short} {day} {yyyy}", f"{full} {dd} {yyyy}",
    }
    if d.month == 9:
        variants |= {f"{day} sept {yyyy}", f"sept {day} {yyyy}"}
    for table in (MONTHS_HI, MONTHS_KN):
        for name in table[d.month - 1]:
            variants.add(f"{day} {name} {yyyy}")
            variants.add(f"{dd} {name} {yyyy}")
    return sorted(search_form(v) for v in variants)


def parse_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


@dataclass(frozen=True)
class TermGroup:
    label: str  # human-readable form shown in the UI
    variants: tuple[str, ...]


def _month_name_pattern() -> str:
    names = sorted(_MONTH_LOOKUP, key=len, reverse=True)
    return "|".join(re.escape(n) for n in names)


_MONTHS_RE = _month_name_pattern()
_DATE_DMY_WORD = re.compile(rf"(?<!\d)(\d{{1,2}})\s*(?:-\s*)?({_MONTHS_RE})\.?\s*(?:-\s*)?(\d{{4}})")
_DATE_MDY_WORD = re.compile(rf"({_MONTHS_RE})\.?\s+(\d{{1,2}})\s+(\d{{4}})")
_DATE_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_DATE_NUM = re.compile(r"(?<!\d)(\d{1,2})-(\d{1,2})-(\d{4}|\d{2})(?!\d)")
_AMOUNT = re.compile(r"(?:₹|rs\.?|inr|रु\.?|रुपये)\s*(\d+(?:\.\d+)?)")
_PERCENT = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*%")
_NUMBER = re.compile(r"(?<![\d.])(\d{3,})(?![\d])")


def _safe_date(y: int, m: int, d: int) -> date | None:
    if y < 100:
        y += 2000
    try:
        return date(y, m, d)
    except ValueError:
        return None


def extract_term_groups(source_text: str, iso_date: str | None = None) -> list[TermGroup]:
    """Pull checkable values out of a verbatim document snippet."""
    groups: list[TermGroup] = []
    seen_dates: set[date] = set()

    def add_date(d: date | None) -> None:
        if d and d not in seen_dates:
            seen_dates.add(d)
            groups.append(TermGroup(label=d.isoformat(), variants=tuple(date_variants(d))))

    add_date(parse_iso(iso_date))

    text = search_form(source_text)
    consumed = text
    for m in _DATE_DMY_WORD.finditer(text):
        add_date(_safe_date(int(m.group(3)), _MONTH_LOOKUP.get(m.group(2), 0), int(m.group(1))))
        consumed = consumed.replace(m.group(0), " ")
    for m in _DATE_MDY_WORD.finditer(text):
        add_date(_safe_date(int(m.group(3)), _MONTH_LOOKUP.get(m.group(1), 0), int(m.group(2))))
        consumed = consumed.replace(m.group(0), " ")
    for m in _DATE_ISO.finditer(text):
        add_date(_safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        consumed = consumed.replace(m.group(0), " ")
    for m in _DATE_NUM.finditer(text):
        # Indian documents use day-first ordering.
        add_date(_safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
        consumed = consumed.replace(m.group(0), " ")

    seen_values: set[str] = set()
    for m in _AMOUNT.finditer(consumed):
        value = m.group(1).rstrip("0").rstrip(".") if "." in m.group(1) else m.group(1)
        if value not in seen_values:
            seen_values.add(value)
            groups.append(TermGroup(label=f"₹{value}", variants=(value,)))
    for m in _PERCENT.finditer(consumed):
        value = m.group(1)
        if value not in seen_values:
            seen_values.add(value)
            groups.append(TermGroup(label=f"{value}%", variants=(f"{value}%", f"{value} %")))
    for m in _NUMBER.finditer(consumed):
        value = m.group(1)
        if value not in seen_values and not (1900 <= int(value) <= 2100 and seen_dates):
            seen_values.add(value)
            groups.append(TermGroup(label=value, variants=(value,)))
    return groups


def _term_regex(term: str) -> re.Pattern[str]:
    prefix = r"(?<!\d)" if term[:1].isdigit() else (r"(?<![a-z])" if term[:1].isascii() and term[:1].isalpha() else "")
    suffix = r"(?!\d)" if term[-1:].isdigit() else (r"(?![a-z])" if term[-1:].isascii() and term[-1:].isalpha() else "")
    return re.compile(prefix + re.escape(term) + suffix)


def find_term(page_search_text: str, group: TermGroup) -> tuple[int, int] | None:
    for variant in group.variants:
        m = _term_regex(variant).search(page_search_text)
        if m:
            return m.start(), m.end()
    return None


def snippet(text: str, start: int, end: int, radius: int = 110) -> str:
    lo, hi = max(0, start - radius), min(len(text), end + radius)
    prefix = "…" if lo > 0 else ""
    suffix = "…" if hi < len(text) else ""
    return prefix + text[lo:hi].strip() + suffix
