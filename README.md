# SiteProbe — Deep Website & Web App Testing Platform

Crawl a website in a real browser, run deep multi-category tests, and review
**every issue on annotated screenshots** that show exactly where the problem is.

## What it checks

| Engine | What it finds |
|---|---|
| **Crawler** | BFS same-domain crawl, `robots.txt` + `sitemap.xml` aware, max-pages limit |
| **Functional** | Broken internal/external links, broken images, 4xx/5xx pages, dead in-page anchors, `javascript:` links, horizontal overflow per viewport |
| **Console & Network** | JS console errors/warnings, unhandled exceptions, failed requests, HTTP 4xx/5xx resources, mixed content |
| **Accessibility** | axe-core (WCAG 2.1 A/AA + best practice) with selector + element screenshots |
| **SEO** | title/meta description, h1 structure, heading skips, missing `alt`, canonical, viewport meta, lang, OG tags, favicon, duplicate titles across pages |
| **Security** | HTTPS, CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, cookie flags, server version disclosure |
| **Performance** | TTFB, FCP, LCP, CLS, page weight, DOM size, request count, slowest resources |

## Key behaviors

- **No login / no credentials needed**: SiteProbe scans public pages only. If a URL redirects to a login wall, it reports an informational issue ("content behind authentication") instead of failing.
- **Scan without restrictions**: `robots.txt` is OFF by default (opt-in via checkbox); sitemap discovery always runs; max pages raised to 500. Self-signed/sloppy TLS is tolerated.
- **Resilient page loading**: navigates with `load → domcontentloaded → commit` fallbacks under a shared time budget, so sites that never reach "network idle" still scan. Pages that partially render are tested with an explanatory note rather than failing.
- **SPA-aware**: hashbang (`#!/route`) and hash (`#/route`) links are recognized as client-side navigation, not flagged as broken anchors.
- **CSP-safe accessibility**: axe-core is injected via a same-origin Playwright route, so strict Content-Security-Policy headers don't block it.
- **Realistic browser fingerprint**: uses a genuine Chrome user-agent so CDN/WAF bot-protection doesn't block scans.

## First-load experience

On startup the API seeds **4 realistic demo scans** (all against reserved `example.*` domains) with full issue data, generated screenshots, and downloadable reports — so the dashboard feels alive immediately. Demo runs are tagged with a ✦ demo badge and never affect your real scans.

## Artifacts per run (`server/runs/<run_id>/`)

- `screenshots/<page>__<viewport>/fullpage.png` — full-page screenshot per page/viewport
- `screenshots/<page>__<viewport>/issue-NNN.png` — **full page with a red box drawn at the issue location**
- `screenshots/<page>__<viewport>/issue-NNN-element.png` — zoomed crop of the offending element
- `report.json` — machine-readable results
- `report.html` — standalone human-readable report (screenshots embedded, opens anywhere)
- `site-report.zip` — everything bundled for download

## Stack

- **Backend:** Python 3.11 · FastAPI · Playwright (async Chromium) · httpx · Pillow · Pydantic v2
- **Frontend:** React 18 · Vite 5 · TypeScript · Tailwind CSS · WebSocket live progress (dashboard on port **4500**)

## Setup

### 1. Backend

```bash
cd server
python3 -m venv .venv            # or: uv venv --python 3.11 .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

> **No sudo? No problem.** If `python3 -m venv` fails (Ubuntu split packages),
> install [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
> and run `uv venv --python 3.11 .venv` + `uv pip install --python .venv/bin/python -r requirements.txt`.
> uv ships its own Python, no root required.

If Chromium fails to launch, system libraries may be missing:
`sudo .venv/bin/python -m playwright install-deps chromium` (or ask your admin).

### 2. Frontend

```bash
cd client
npm install
```

> Node 18+ is required for Vite 5. With nvm: `nvm install 20 && nvm use 20`.

### 3. Run

```bash
./scripts/dev.sh
# dashboard: http://localhost:4500
# API docs:  http://127.0.0.1:8000/docs
```

Or separately:

```bash
cd server && .venv/bin/python -m uvicorn app.main:app --port 8000 --reload
cd client && npm run dev   # serves on port 4500 (strict)
```

## Tests

```bash
cd server
.venv/bin/python -m pytest tests -q
```

- `tests/test_urls.py` — URL utilities (fast unit tests)
- `tests/test_scan_integration.py` — full end-to-end scan against a deliberately
  broken local fixture site (requires Chromium); asserts issues are found in
  every category, screenshots/annotations are written, and reports are generated.

## API summary

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/runs` | Start a scan (`RunOptions` body) |
| `GET` | `/api/runs` | List runs + summaries |
| `GET` | `/api/runs/{id}` | Full run detail (issues, pages, scores) |
| `GET` | `/api/runs/{id}/issues?category=&severity=&page=` | Filtered/paginated issues |
| `DELETE` | `/api/runs/{id}` | Cancel a running scan |
| `GET` | `/api/runs/{id}/report.json` / `report.html` / `site-report.zip` | Downloads |
| `GET` | `/artifacts/{run_id}/…` | Screenshots (static) |
| `WS` | `/ws/{run_id}` | Live progress events |

## Notes & limits

- In-memory run store + one scan task per run (single process). For horizontal
  scaling swap `core/store.py` for Redis-backed queues.
- Page visits are sequential per run to keep console/network attribution exact.
- External link checks are capped per page (`link_check_cap`) with a concurrency
  semaphore to stay polite.
