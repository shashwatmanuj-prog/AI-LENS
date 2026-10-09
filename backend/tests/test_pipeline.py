"""End-to-end pipeline tests with a fake Gemma 4 and fake official site."""

from __future__ import annotations

import asyncio
import json
import unittest

from app.schemas import VerificationStatus
from app.services.gemma import translate_extraction
from app.services.ingest import UnsupportedFileError, prepare_document
from app.services.json_utils import ModelOutputError
from app.services.pipeline import run_pipeline
from app.services.storage import InMemoryRepository
from tests.fakes import SAMPLE_EXTRACTION, FakeFetcher, FakeModel, png_bytes

PORTAL = "https://ssp.postmatric.karnataka.gov.in"


def run(coro):
    return asyncio.run(coro)


class IngestTests(unittest.TestCase):
    def test_image_is_normalised_to_jpeg(self):
        doc = prepare_document(png_bytes())
        self.assertEqual(doc.kind, "image")
        self.assertEqual(doc.images[0].mime_type, "image/jpeg")
        self.assertTrue(doc.images[0].data.startswith(b"\xff\xd8"))

    def test_rejects_non_documents(self):
        for bad in (b"", b"MZ\x90\x00 executable", b"<html>hi</html>"):
            with self.assertRaises(UnsupportedFileError):
                prepare_document(bad)

    @unittest.skipUnless(__import__("importlib").util.find_spec("fitz"), "PyMuPDF not installed")
    def test_pdf_pages_become_images(self):
        import fitz

        pdf = fitz.open()
        for n in range(3):
            pdf.new_page().insert_text((72, 72), f"Notice page {n + 1}. Last date 15-10-2026")
        raw = pdf.tobytes()
        doc = prepare_document(raw, max_pages=2)
        self.assertEqual(len(doc.images), 2)
        self.assertEqual(doc.total_pages, 3)
        self.assertIn("15-10-2026", doc.pdf_text)
        self.assertTrue(doc.notes)


class PipelineTests(unittest.TestCase):
    def test_upload_to_verified_result(self):
        model = FakeModel()
        fetcher = FakeFetcher(pages={PORTAL: "Last date 15/10/2026. Income up to Rs.2,50,000."})
        repo = InMemoryRepository()
        a = run(run_pipeline(raw=png_bytes(), file_name="poster.png", language="en",
                             model=model, fetcher=fetcher, repo=repo))
        self.assertEqual(a.model, "gemma-4-26b-a4b-it")
        self.assertEqual(model.calls[0][0], 1)  # the image was actually sent to the model
        self.assertIn("English", model.calls[0][1])
        self.assertEqual(a.verification.overall, VerificationStatus.verified)
        self.assertEqual(len(a.extraction.checklist), 1)
        self.assertIsNotNone(run(repo.get(a.id)))

    def test_language_instruction_reaches_model(self):
        model = FakeModel()
        run(run_pipeline(raw=png_bytes(), file_name="p.png", language="kn",
                         model=model, fetcher=FakeFetcher(), repo=InMemoryRepository()))
        self.assertIn("Kannada", model.calls[0][1])

    def test_invalid_json_triggers_one_repair_then_fails_cleanly(self):
        model = FakeModel(replies=["not json", "still not json"])
        with self.assertRaises(ModelOutputError):
            run(run_pipeline(raw=png_bytes(), file_name="p.png", language="en",
                             model=model, fetcher=FakeFetcher(), repo=InMemoryRepository()))
        self.assertEqual(len(model.calls), 2)
        self.assertEqual(model.calls[1][0], 0)  # repair call is text-only

    def test_discovery_used_only_when_no_link_printed(self):
        data = dict(SAMPLE_EXTRACTION, official_links=[])
        model = FakeModel(replies=[json.dumps(data)])
        found = "https://sw.kar.nic.in/pms"
        calls = []

        async def discover(ex):
            calls.append(ex.title)
            return [found]

        fetcher = FakeFetcher(pages={found: "15-10-2026 and 250000"})
        a = run(run_pipeline(raw=png_bytes(), file_name="p.png", language="en", model=model,
                             fetcher=fetcher, repo=InMemoryRepository(), discover=discover))
        self.assertEqual(calls, ["Post-Matric Scholarship 2026-27"])
        self.assertEqual(a.verification.overall, VerificationStatus.verified)


class TranslationTests(unittest.TestCase):
    def test_translation_cannot_alter_verifiable_fields(self):
        from app.services.gemma import parse_extraction

        original = parse_extraction(dict(SAMPLE_EXTRACTION))
        tampered = dict(SAMPLE_EXTRACTION, title="ಸ್ಕಾಲರ್‌ಶಿಪ್", official_links=["https://evil.example"])
        tampered["deadlines"] = [dict(SAMPLE_EXTRACTION["deadlines"][0], date="2027-01-01", label="ಕೊನೆಯ ದಿನ")]
        model = FakeModel(replies=[json.dumps(tampered)])
        t = run(translate_extraction(model, original, "kn"))
        self.assertEqual(t.title, "ಸ್ಕಾಲರ್‌ಶಿಪ್")
        self.assertEqual(t.deadlines[0].label, "ಕೊನೆಯ ದಿನ")
        self.assertEqual(t.deadlines[0].date, "2026-10-15")
        self.assertEqual(t.official_links, original.official_links)


if __name__ == "__main__":
    unittest.main()
