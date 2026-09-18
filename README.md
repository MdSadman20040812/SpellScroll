# SPELLSCROLL 📜 — AI Webtoon Discovery

**Taste-driven reading feed. Describe what you like; get a curated feed.**

![License: MIT](https://img.shields.io/badge/License-MIT-6d3ee0.svg)
![Django](https://img.shields.io/badge/Django-5-1f6b4c.svg)
![FastAPI](https://img.shields.io/badge/API-FastAPI-0f9d72.svg)
![Coverage](https://img.shields.io/badge/provider_coverage-100%25-34d399.svg)

---

A taste-driven reading feed for webtoons. Describe what you like in plain language — a LangGraph agent pipeline turns that into a taste signature, searches a vector index, and rebuilds your feed every time you react to a card.

Ships as **a web app (Windows/macOS/Linux, installable as a PWA)** and **an Android app**.

---

## What's Here

| Surface | Path | Notes |
| --- | --- | --- |
| Web app + API | `apps/`, `api/`, `templates/` | Django + FastAPI in one ASGI process |
| Static web app | `spellscroll-web/` | Next.js; shares the design system |
| Android shell | `android/` | WebView wrapper, back nav, pull-to-refresh |
| Agents | `agents/` | LangGraph pipeline with local fallbacks |
| Providers | `services/` | AniList / MangaDex / Kitsu + cover cache |
| Design system | `static/css/` | Tokens + components, single source of truth |

---

## Quick Start

```bash
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py sync_catalog --limit 80
python -m uvicorn spellscroll.asgi:application --port 8000
```

Open <http://localhost:8000>. **No API keys required** — metadata and covers come from unauthenticated public APIs, and recommendations fall back to deterministic local ranking when no LLM is configured.

Full instructions in [BACKEND_SETUP.md](BACKEND_SETUP.md).

---

## Cover Art That Doesn't Break

Every image is served from `/cover/<uuid>/` on our own origin:

1. **Local mirror** under `media/covers/`
2. **Fresh download** from upstream (mirrored for next time)
3. **Generated SVG placeholder** derived from the title

A dead provider, hotlink block, or renamed file degrades to a styled gradient — never a broken-image icon.

---

## Provider Coverage — Measured, Not Claimed

`tests/test_provider_coverage.py` resolves 63 real titles spanning WEBTOON, Tapas, Lezhin, Manta, Tappytoon, Korean manhwa, Chinese manhua, and obscure long-tail Canvas series:

```
sample size          : 63
resolved             : 63 (100.0%)
  with cover art     : 63 (100.0%)
  with synopsis      : 63 (100.0%)
card-ready           : 63
```

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│  Web App    │────▶│  FastAPI    │────▶│  LangGraph      │
│  (Django)   │     │  Gateway    │     │  Agent Pipeline │
└─────────────┘     └─────────────┘     └────────┬────────┘
                                                 │
                                          ┌──────▼──────┐
                                          │  ChromaDB   │
                                          │  Vector Idx │
                                          └─────────────┘
```

---

## Structure

```
SpellScroll/
├── apps/                    # Django apps
├── api/                     # FastAPI routes
├── agents/                  # LangGraph pipeline
├── services/                # Provider integrations + cover cache
├── templates/               # Django templates
├── static/css/              # Design system
├── spellscroll-web/         # Next.js static app
├── android/                 # Android WebView shell
├── tests/
│   └── test_provider_coverage.py
├── requirements.txt
├── BACKEND_SETUP.md
└── README.md
```

---

## License

MIT © Md Sadman Bin Masud
