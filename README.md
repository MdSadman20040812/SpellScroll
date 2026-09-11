# SPELLSCROLL 📜 — AI Webtoon Discovery

[![License: MIT](https://img.shields.io/badge/License-MIT-6d3ee0.svg)](https://opensource.org/licenses/MIT)
[![Django](https://img.shields.io/badge/Django-5-1f6b4c.svg)](https://www.djangoproject.com/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-0f9d72.svg)](https://fastapi.tiangolo.com/)
[![Coverage](https://img.shields.io/badge/provider_coverage-100%25-34d399.svg)](tests/test_provider_coverage.py)

A taste-driven reading feed for colourful webtoons. Describe what you like in
plain language; a LangGraph agent pipeline turns that into a taste signature,
searches a vector index, and rebuilds your feed every time you react to a card.

Ships as **a web app (Windows/macOS/Linux, installable as a PWA)** and **an
Android app** wrapping the same UI.

---

## What's here

| Surface | Path | Notes |
| --- | --- | --- |
| Web app + API | `apps/`, `api/`, `templates/` | Django + FastAPI in one ASGI process |
| Static web app | `spellscroll-web/` | Next.js; shares the design system |
| Android shell | `android/` | WebView wrapper, back nav, pull-to-refresh |
| Agents | `agents/` | LangGraph pipeline with local fallbacks |
| Providers | `services/` | AniList / MangaDex / Kitsu + cover cache |
| Design system | `static/css/` | Tokens + components, single source of truth |

---

## Quick start

```bash
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py sync_catalog --limit 80
python -m uvicorn spellscroll.asgi:application --port 8000
```

Open <http://localhost:8000>. **No API keys required** — metadata and covers
come from unauthenticated public APIs, and recommendations fall back to
deterministic local ranking when no LLM is configured.

Full instructions, including the Next.js app and the Android build, are in
[BACKEND_SETUP.md](BACKEND_SETUP.md).

---

## Cover art that doesn't break

Cover URLs used to be hardcoded MangaDex links pinning specific filenames.
Those change whenever a series' primary cover is replaced, so they rotted — and
a few IDs pointed at the wrong series entirely.

Now every image is served from `/cover/<uuid>/` on our own origin, which
resolves in order:

1. a locally mirrored file under `media/covers/`,
2. a fresh download from the upstream (mirrored for next time),
3. a generated SVG placeholder derived from the title.

A dead provider, a hotlink block or a renamed file degrades to a styled
gradient rather than a broken-image icon. Each cover's dominant colour is
extracted at sync time and drives that card's accent.

### Provider coverage — measured, not claimed

`tests/test_provider_coverage.py` resolves 63 real titles spanning WEBTOON,
Tapas, Lezhin, Manta and Tappytoon originals, Korean manhwa, Chinese manhua and
deliberately obscure long-tail Canvas series:

```
sample size          : 63
resolved             : 63 (100.0%)
  with cover art     : 63 (100.0%)
  with synopsis      : 63 (100.0%)
card-ready           : 63 (100.0%)
resolved by provider : {'anilist': 48, 'mangadex': 14, 'kitsu': 1}
```

```bash
python -m pytest tests/test_provider_coverage.py -s -m network
```

The Archive is not limited to the synced catalogue either: a search that finds
little locally queries AniList and MangaDex **live**, and picking a result
imports it so the ranking agents can use it.

---

## Configuration

Everything is optional. `.env`:

```ini
SECRET_KEY=change-me
DEBUG=True

LLM_PROVIDER=groq      # groq | gemini | openrouter | cerebras | none
LLM_API_KEY=gsk_...
LLM_MODEL=qwen/qwen3.8-27b
```

All four providers speak the OpenAI `/chat/completions` shape and all have a
free tier, so switching is two environment variables — see `services/llm.py`.

| Missing | Behaviour |
| --- | --- |
| No `LLM_API_KEY` | Deterministic local ranking; app fully functional |
| No `chromadb` | In-process vector store with cosine search |
| No `sentence-transformers` | Deterministic 384-dim hash embeddings |
| No `Pillow` | Accent colours fall back to the provider's reported colour |

---

## Design system

`static/css/tokens.css` and `static/css/spellscroll.css` are the single source
of truth for both frontends; `spellscroll-web`'s `predev`/`prebuild` copy them
in, so the two can never drift.

- **Ground** — a silver / dark-green blend with an SVG grain overlay
- **Type** — Cinzel (display), Cinzel Decorative (wordmark), Inter (body), on a
  short modular scale with an 11px floor
- **Colour** — every value is a token; light and dark themes both defined
- **Motion** — one entrance curve, one exit curve, `prefers-reduced-motion`
  honoured throughout

---

## License

MIT. Metadata and cover art courtesy of
[AniList](https://anilist.co), [MangaDex](https://mangadex.org) and
[Kitsu](https://kitsu.io).
