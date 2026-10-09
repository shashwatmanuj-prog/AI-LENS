# CommunityLens AI

Turn a photo or PDF of a government notice, college circular or scholarship poster into
a plain-language summary, deadlines, a step-by-step checklist, and facts checked against the
official website. Results in English, Hindi or Kannada. Powered by **Gemma 4**.

```
Upload ──► Gemma 4 reads the page images ──► structured extraction ──► official-site verification ──► dashboard + share
 (photo/PDF)   (gemma-4-26b-a4b-it)           (deadlines, eligibility,     (deterministic, no LLM)       (Supabase)
                                                checklist, links)
```

## What Gemma 4 does, and what it doesn't

| Step | Who does it |
|---|---|
| Reading images and PDF pages (rasterised), extracting facts, writing the checklist | **Gemma 4** (multimodal) |
| Output in English / Hindi / Kannada, and on-demand translation of results | **Gemma 4** |
| Finding a candidate official page when the notice prints no link (optional) | **Gemma 4** with Google Search grounding |
| Deciding whether something is **verified** | **Plain code**, never the model |

There is no fallback model. `GEMMA_MODEL` must match `gemma-4-*-it` or the server refuses to start,
and responses reporting a non-Gemma-4 `model_version` are rejected.

**API facts this is built on** (checked Oct 2026, [Gemma on the Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)):
model ids `gemma-4-31b-it` and `gemma-4-26b-a4b-it`; image input, system instructions, thinking toggle
and Google Search grounding are supported. PDF input and JSON mode are *not* documented for Gemma,
so PDFs are rendered to images with PyMuPDF and JSON is parsed from text (with one repair retry).

## How verification works

A claim is marked **Verified** only if every concrete value in it (dates, ₹ amounts, percentages,
3+ digit numbers), copied verbatim from the notice, literally appears on a page served from an
allow-listed official domain (`.gov.in`, `.nic.in`, `.ac.in`, `.edu.in`, `.res.in`, `.gov`, `.edu`,
plus anything in `EXTRA_OFFICIAL_DOMAINS`).

- Dates match across formats and scripts: `15/10/2026`, `15th October, 2026`, `15 अक्टूबर 2026`, `೧೫ ಅಕ್ಟೋಬರ್ 2026`.
- `₹2,50,000` matches `250000` but not `12,50,000`.
- Each result shows the official page and a text snippet as evidence.
- Other statuses: **Partly confirmed**, **Not found on official site** (page opened, values absent:
  often an outdated or fake notice), **Not verified** (no official page reachable), **Nothing to check**
  (qualitative claims like "apply online only").
- Links to non-official domains printed on a notice are listed but never fetched. Fetching has SSRF
  guards: no IPs, no private addresses, ports 80/443 only, every redirect hop re-checked.

Limits worth knowing: a value appearing on the right site is strong evidence, not proof the notice
is genuine; a JavaScript-rendered official page may show no text to the checker (result: not found);
and the domain allow-list is coarse (any `.ac.in` counts as official).

## Project layout

```
backend/            FastAPI service
  app/main.py         app + /api/health
  app/routers/        /api/analyze, /analyses/{id}, /translate, /share, /shared/{slug}, /communities/{name}
  app/services/
    ingest.py           file sniffing, image normalising, PDF → page images
    gemma.py            Gemma 4 client, prompt → JSON → validated Extraction
    verifier.py         official-domain allow-list, safe fetching, claim matching
    text_match.py       date/amount normalisation across English, Hindi, Kannada
    discovery.py        optional Gemma 4 + Search grounding to find official pages
    storage.py          Supabase repository + in-memory fallback
    pipeline.py         orchestrates the whole flow
  tests/              unit + pipeline + API tests (Gemma and websites are faked)
frontend/           Next.js 15, TypeScript, Tailwind, shadcn/ui
supabase/schema.sql  table, RLS, storage bucket
```

## Run locally

Prerequisites: Python 3.11+, Node 20+, a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # set GEMINI_API_KEY (Supabase optional)
uvicorn app.main:app --reload --env-file .env
# → http://localhost:8000/api/health   (interactive docs at /docs)

# 2. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev
# → http://localhost:3000
```

### First thing to test

The Gemma call could not be exercised while building (no API key in the build sandbox), so
before a demo, upload one real notice and check `/api/health` shows `"gemma_configured": true`.
If Gemma answers but extraction fails, the backend logs say why (usually a JSON-shape issue).

### Supabase (for saving and sharing across restarts)

1. Create a project, open the SQL editor, run `supabase/schema.sql`.
2. Put the project URL and **service-role** key in `backend/.env`.
3. Restart the backend; `/api/health` should report `"storage": "supabase"`.

The browser never receives a Supabase key. RLS is on with no public policies; the backend is the only client.

## Tests

```bash
cd backend && pytest            # 34 tests; API tests need fastapi installed
cd frontend && npm test         # date + translation-completeness tests (vitest)
cd frontend && npm run typecheck && npm run build
```

## Deploy

- **Backend → AWS App Runner (or ECS/Fargate):** `backend/Dockerfile`. Set the env vars from
  `.env.example`, port 8000. Gemma calls on multi-page PDFs can take 30-90 s, which is why the backend
  should not run as a short-timeout serverless function.
- **Frontend → Vercel:** set the project root to `frontend/` and `NEXT_PUBLIC_API_URL` to the backend URL.
  Then set the backend's `CORS_ORIGINS` and `PUBLIC_APP_URL` to the Vercel domain.

## Not built (deliberately, for an MVP)

User accounts (saved items are remembered per device; sharing is by unguessable link), rate limiting,
OCR outside Gemma, and integrations with specific government APIs (none with stable public access
were confirmed for this scope).
