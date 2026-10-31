# Ghatnachakra

Chapter-wise PYQ practice: build a timed test from any chapters, submit it, and get marks, mistakes and test-wise progress.
A public landing page explains the workflow, the test evaluator and the architecture; sign-in opens a dashboard.

```
web/       static frontend (HTML + CSS + vanilla JS, no build step)  -> Vercel
backend/   Django + DRF API (accounts, tests, evaluator, crops)      -> Render
data/      question bank: manifest.json, q/<chapter>.json, answers.json (the server's answer key)
tools/     one-off pipeline that builds data/ from the book PDFs (extract -> parse -> OCR verify -> build)
```

## Run locally

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ..   # once
./run.sh        # API on :8010, app on http://127.0.0.1:5174
```

`web/dev.py` serves `web/` and forwards `/api/*` to Django, so the browser sees one origin, as in production.
Tests: `cd backend && .venv/bin/python manage.py test`.

## Accounts

Same design as Arcloop: register with email + username + password, sign in with username **or** email. The browser gets an
HttpOnly `ghatnachakra_session` cookie (path `/api/`, SameSite=Strict, Secure in production) plus a CSRF cookie that the page
echoes in `X-CSRFToken`. Tokens are stored hashed, expire after 14 days, and are revoked on log-out. There is no password reset
or email yet (no mail provider is configured).

## Deploy

1. **Render** (API): the repository root must contain `mcq-portal/` and the five book PDFs; use `render.yaml` (repo root).
   Set `FRONTEND_URL` (the Vercel https URL) and `DATABASE_URL` (Postgres). Without `DATABASE_URL` it falls back to SQLite,
   which Render wipes on every deploy. The PDFs are only used to crop the original page for image-style questions
   (`/api/v1/crop/`); keep the repository private.
2. **Vercel** (frontend): project root = `mcq-portal/web`, framework "Other", no build command. In `web/vercel.json` replace
   `ghatnachakra-api.onrender.com` with the real API host. The rewrite keeps the app and the API on one origin, so cookies
   are first-party and no CORS is needed.
3. After rebuilding `data/`, run `python3 tools/build_answer_index.py` too (it writes `data/answers.json`).

## API (all under `/api/v1/`)

| Route | Notes |
| --- | --- |
| `auth/register/`, `auth/login/`, `auth/logout/`, `auth/me/` | session cookie (`transport: "cookie"`) |
| `stats/` | public counts for the landing page |
| `data/manifest.json`, `data/q/<chapter>.json` | question bank, sign-in required |
| `attempts/` (GET, POST), `attempts/<id>/` (GET, DELETE) | marking happens on the server |
| `qstats/` | per-question history of the signed-in user |
| `crop/?book=&segs=` | PNG of the original book page |
