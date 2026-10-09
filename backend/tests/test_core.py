"""Unit tests for parsing, matching and verification. No network, no Gemma calls."""

from __future__ import annotations

import asyncio
import copy
import unittest
from datetime import date

from app.config import Settings
from app.schemas import Extraction, VerificationStatus
from app.services import text_match
from app.services.gemma import parse_extraction
from app.services.json_utils import ModelOutputError, extract_json_object
from app.services.verifier import check_url_safety, is_official_host, verify
from tests.fakes import SAMPLE_EXTRACTION, FakeFetcher

PORTAL = "https://ssp.postmatric.karnataka.gov.in"


def run(coro):
    return asyncio.run(coro)


class JsonParsingTests(unittest.TestCase):
    def test_fenced_json(self):
        self.assertEqual(extract_json_object('Here:\n```json\n{"a": 1}\n```'), {"a": 1})

    def test_prose_around_json_and_trailing_comma(self):
        self.assertEqual(extract_json_object('Sure! {"a": [1, 2,], "b": "x}"} done'), {"a": [1, 2], "b": "x}"})

    def test_garbage_raises(self):
        with self.assertRaises(ModelOutputError):
            extract_json_object("I cannot read this image.")

    def test_ids_are_reassigned_and_lists_coerced(self):
        data = copy.deepcopy(SAMPLE_EXTRACTION)
        data["warnings"] = "blurry footer"
        ex = parse_extraction(data)
        self.assertEqual([f.id for f in ex.key_facts], ["f1", "f2", "f3"])
        self.assertEqual(ex.deadlines[0].id, "d1")
        self.assertEqual(ex.warnings, ["blurry footer"])


class ModelGuardTests(unittest.TestCase):
    def test_non_gemma4_model_rejected(self):
        for bad in ("gemini-2.5-flash", "gemma-3-27b-it", "gpt-4o", "gemma-4-31b"):
            with self.assertRaises(ValueError, msg=bad):
                Settings(gemma_model=bad).validate_model()

    def test_gemma4_models_accepted(self):
        for good in ("gemma-4-31b-it", "gemma-4-26b-a4b-it"):
            Settings(gemma_model=good).validate_model()


class TextMatchTests(unittest.TestCase):
    def test_date_found_in_any_common_format(self):
        groups = text_match.extract_term_groups("Last date: 15/10/2026")
        self.assertEqual([g.label for g in groups], ["2026-10-15"])
        for page in ("Apply by 15th October, 2026.", "closing on 15-10-2026", "October 15, 2026",
                     "अंतिम तिथि १५ अक्टूबर 2026", "ಕೊನೆಯ ದಿನಾಂಕ 15 ಅಕ್ಟೋಬರ್ 2026", "15.10.2026",
                     "೧೫ ಅಕ್ಟೋಬರ್ 2026", "Oct. 15, 2026", "15-Oct-2026", "Last date: 15th Oct. 2026"):
            self.assertIsNotNone(text_match.find_term(text_match.search_form(page), groups[0]), page)

    def test_wrong_date_not_matched(self):
        g = text_match.extract_term_groups("", "2026-10-15")[0]
        self.assertIsNone(text_match.find_term(text_match.search_form("Last date 25-10-2026"), g))
        self.assertIsNone(text_match.find_term(text_match.search_form("Last date 15-10-2025"), g))

    def test_amount_with_indian_commas_and_boundaries(self):
        groups = text_match.extract_term_groups("Income should not exceed Rs. 2,50,000")
        self.assertEqual([g.label for g in groups], ["₹250000"])
        self.assertIsNotNone(text_match.find_term(text_match.search_form("limit ₹ 2,50,000 per annum"), groups[0]))
        self.assertIsNone(text_match.find_term(text_match.search_form("limit ₹ 12,50,000"), groups[0]))

    def test_devanagari_digits(self):
        groups = text_match.extract_term_groups("शुल्क ₹५००")
        self.assertEqual(groups[0].label, "₹500")

    def test_qualitative_text_has_no_terms(self):
        self.assertEqual(text_match.extract_term_groups("Apply online only"), [])

    def test_percent(self):
        groups = text_match.extract_term_groups("Minimum 60% marks")
        self.assertEqual(groups[0].label, "60%")

    def test_date_variants_cover_hindi(self):
        self.assertIn("15 अक्टूबर 2026", text_match.date_variants(date(2026, 10, 15)))


class OfficialDomainTests(unittest.TestCase):
    def test_allowlist(self):
        self.assertTrue(is_official_host("scholarships.gov.in"))
        self.assertTrue(is_official_host("vtu.ac.in"))
        self.assertTrue(is_official_host("www.karnataka.gov.in"))
        self.assertFalse(is_official_host("gov.in"))
        self.assertFalse(is_official_host("gov.in.evil.com"))
        self.assertFalse(is_official_host("fakegov.in"))
        self.assertFalse(is_official_host("10.0.0.1"))
        self.assertTrue(is_official_host("bescom.co.in", extra=("bescom.co.in",)))

    def test_url_safety(self):
        self.assertIsNone(check_url_safety("https://upsc.gov.in/notice"))
        self.assertIsNotNone(check_url_safety("https://user:pw@upsc.gov.in/"))
        self.assertIsNotNone(check_url_safety("https://upsc.gov.in:8443/"))
        self.assertIsNotNone(check_url_safety("file:///etc/passwd"))
        self.assertIsNotNone(check_url_safety("https://example.com"))


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.ex = Extraction.model_validate(parse_extraction(copy.deepcopy(SAMPLE_EXTRACTION)).model_dump())

    def status_of(self, report, claim_id):
        return next(c for c in report.claims if c.claim_id == claim_id).status

    def test_verified_only_when_values_appear_on_official_page(self):
        page = "Post-matric scholarship. Last date: 15-10-2026. Income limit Rs 2,50,000 per annum."
        fetcher = FakeFetcher(pages={PORTAL: page})
        report = run(verify(self.ex, fetcher))
        self.assertEqual(self.status_of(report, "d1"), VerificationStatus.verified)
        self.assertEqual(self.status_of(report, "f1"), VerificationStatus.verified)
        self.assertEqual(self.status_of(report, "f2"), VerificationStatus.verified)
        self.assertEqual(self.status_of(report, "f3"), VerificationStatus.not_checkable)
        self.assertEqual(report.overall, VerificationStatus.verified)
        d1 = next(c for c in report.claims if c.claim_id == "d1")
        self.assertEqual(d1.source_url, PORTAL)
        self.assertIn("15-10-2026", d1.evidence)

    def test_non_official_link_is_never_fetched(self):
        fetcher = FakeFetcher(pages={PORTAL: "nothing relevant"})
        report = run(verify(self.ex, fetcher))
        self.assertNotIn("http://scholarship-help.example.com", fetcher.fetched)
        skipped = [s for s in report.sources if not s.official]
        self.assertEqual(len(skipped), 1)
        self.assertIn("official", skipped[0].reason)

    def test_changed_deadline_is_not_verified(self):
        fetcher = FakeFetcher(pages={PORTAL: "Last date extended to 30-10-2026. Income limit 2,50,000"})
        report = run(verify(self.ex, fetcher))
        self.assertEqual(self.status_of(report, "d1"), VerificationStatus.not_found_on_source)
        self.assertEqual(self.status_of(report, "f2"), VerificationStatus.verified)
        self.assertEqual(report.overall, VerificationStatus.partial)

    def test_unreachable_source_means_unverified(self):
        fetcher = FakeFetcher(errors={PORTAL: "Official site returned HTTP 503."})
        report = run(verify(self.ex, fetcher))
        self.assertEqual(report.overall, VerificationStatus.unverified)
        self.assertTrue(all(c.status in (VerificationStatus.unverified, VerificationStatus.not_checkable)
                            for c in report.claims))
        self.assertIn("503", next(s for s in report.sources if s.official).reason)

    def test_no_links_at_all(self):
        ex = self.ex.model_copy(update={"official_links": []})
        report = run(verify(ex, FakeFetcher()))
        self.assertEqual(report.overall, VerificationStatus.unverified)
        self.assertEqual(report.sources, [])

    def test_html_scripts_are_not_treated_as_evidence(self):
        from app.services.verifier import _to_page

        html = b"<html><title>Notice</title><script>var d='15-10-2026'</script><p>Apply soon</p></html>"
        page = _to_page("https://x.gov.in", html, "text/html")
        self.assertEqual(page.title, "Notice")
        self.assertNotIn("15-10-2026", page.text)

    def test_user_supplied_official_url_is_used(self):
        ex = self.ex.model_copy(update={"official_links": []})
        url = "https://sw.kar.nic.in/scholarship"
        fetcher = FakeFetcher(pages={url: "last date 15 October 2026; income 250000"})
        report = run(verify(ex, fetcher, user_url="sw.kar.nic.in/scholarship"))
        self.assertEqual(report.overall, VerificationStatus.verified)


if __name__ == "__main__":
    unittest.main()
