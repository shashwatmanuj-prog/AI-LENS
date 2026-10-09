"""HTTP API tests. Require FastAPI (pip install -r requirements-dev.txt)."""

from __future__ import annotations

import importlib.util
import unittest

HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None


@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx not installed")
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        from app import deps
        from app.main import app
        from app.routers import analyses
        from app.services.storage import InMemoryRepository
        from tests.fakes import FakeFetcher, FakeModel

        cls.repo = InMemoryRepository()
        portal = "https://ssp.postmatric.karnataka.gov.in"
        app.dependency_overrides[analyses._model_or_503] = lambda: FakeModel()
        app.dependency_overrides[deps.get_fetcher] = lambda: FakeFetcher(pages={portal: "15-10-2026 250000"})
        app.dependency_overrides[deps.get_repo] = lambda: cls.repo
        cls.client = TestClient(app)

    def upload(self, **form):
        from tests.fakes import png_bytes

        return self.client.post(
            "/api/analyze",
            files={"file": ("notice.png", png_bytes(), "image/png")},
            data={"language": "en", **form},
        )

    def test_health_has_no_secrets(self):
        body = self.client.get("/api/health").json()
        self.assertTrue(body["model"].startswith("gemma-4"))
        self.assertNotIn("gemini_api_key", str(body).lower())

    def test_analyze_share_and_feed(self):
        r = self.upload(community="Jayanagar Students")
        self.assertEqual(r.status_code, 200, r.text)
        a = r.json()
        self.assertEqual(a["verification"]["overall"], "verified")

        self.assertEqual(self.client.get(f"/api/analyses/{a['id']}").status_code, 200)

        s = self.client.post(f"/api/analyses/{a['id']}/share", json={}).json()
        self.assertTrue(s["share_url"].endswith(s["share_slug"]))
        shared = self.client.get(f"/api/shared/{s['share_slug']}").json()
        self.assertIsNone(shared["file_path"])

        feed = self.client.get("/api/communities/jayanagar students").json()
        self.assertEqual([f["id"] for f in feed], [a["id"]])

    def test_validation(self):
        self.assertEqual(self.upload(language="fr").status_code, 422)
        self.assertEqual(self.upload(community="<script>").status_code, 422)
        bad = self.client.post("/api/analyze", files={"file": ("x.png", b"not an image", "image/png")})
        self.assertEqual(bad.status_code, 415)
        self.assertEqual(self.client.get("/api/analyses/not-a-uuid").status_code, 404)
        self.assertEqual(self.client.get("/api/shared/zz").status_code, 404)

    def test_private_analysis_not_visible_via_share_route(self):
        a = self.upload().json()
        self.assertEqual(self.client.get("/api/communities/Jayanagar Students").status_code, 200)
        self.assertNotIn(a["id"], [f["id"] for f in self.client.get("/api/communities/Jayanagar Students").json()])


if __name__ == "__main__":
    unittest.main()
