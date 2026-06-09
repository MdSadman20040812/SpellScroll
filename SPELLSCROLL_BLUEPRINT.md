# SPELLSCROLL — Full System Design Blueprint
**Version:** 1.0 MVP  
**Target Agent:** Cursor / GitHub Copilot / Google AI Studio / Any agentic IDE  
**Stack Summary:** Django + FastAPI · LangGraph · ChromaDB · Cerberus API · MangaDex API · WebSockets · SQLite + JSON hybrid · LangSmith  

---

## 1. PROJECT OVERVIEW

Spellscroll is a personalized, AI-curated colourful webtoon discovery and tracking platform. It operates as a **Django web app (PC)** with a **FastAPI REST backend** integrated in-process. The entire recommendation intelligence is powered by a **LangGraph multi-agent pipeline** backed by **Cerberus API** (free tier, 4 000-token packet limit), with **ChromaDB** as the local vector store and **MangaDex API** for webtoon card assets. The system is designed for offline-first, privacy-respecting local operation, optionally exposable as a hosted Django web service.

---

## 2. TECHNOLOGY STACK

| Layer | Technology |
|---|---|
| Web Framework | Django 5.x (renders pages, session management) |
| REST API | FastAPI (mounted inside Django via `WSGIMiddleware` or run as sidecar) |
| AI Orchestration | LangGraph (stateful multi-agent graph) |
| LLM Provider | Cerberus API (free tier, model: `cerberus-l3-8b` or equivalent) |
| Vector Store | ChromaDB (persistent local, two collections) |
| Embedding Model | `sentence-transformers/all-MiniLM-L6-v2` via HuggingFace (local, no API cost) |
| Relational DB | SQLite (dev) / PostgreSQL (prod) via Django ORM |
| Document Store | JSON files under `media/users/{user_id}/` |
| Asset Fetching | MangaDex API v5 (webtoon covers, chapter cards) |
| Web Scraping | Reddit JSON API (no key needed) + SerpAPI free tier (Google results) |
| Tracing | LangSmith (LANGCHAIN_TRACING_V2=true) |
| Real-time | Django Channels + WebSockets |
| Auth | Django `AbstractUser` (AuthN) + custom permission middleware (AuthZ) |
| Frontend | Django templates + Alpine.js (global state) + Tailwind CSS |
| Task Queue | Celery + Redis (background scraping jobs) |

**Free API Keys Required (obtain before starting):**
- `CERBERUS_API_KEY` — https://cerberusai.io (free tier)
- `MANGADEX_CLIENT_ID` + `MANGADEX_CLIENT_SECRET` — https://api.mangadex.org (public, no key for read)
- `SERPAPI_KEY` — https://serpapi.com (100 free searches/month)
- `LANGSMITH_API_KEY` — https://smith.langchain.com (free)

---

## 3. REPOSITORY STRUCTURE

```
spellscroll/
├── manage.py
├── spellscroll/                  # Django project root
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py                   # Channels ASGI entry
│   └── wsgi.py
├── apps/
│   ├── auth_core/                # AuthN + AuthZ
│   │   ├── models.py             # SpellUser (AbstractUser extension)
│   │   ├── middleware.py         # AuthZ enforcement middleware
│   │   └── views.py
│   ├── webtoons/                 # Webtoon data models + views
│   │   ├── models.py
│   │   ├── views.py
│   │   └── serializers.py
│   ├── feed/                     # Personalised feed logic
│   │   ├── views.py
│   │   └── consumers.py          # WebSocket consumer
│   └── admin_panel/              # Admin overrides
│       └── views.py
├── api/                          # FastAPI app (mounted at /api/v1/)
│   ├── main.py
│   ├── routers/
│   │   ├── onboarding.py
│   │   ├── feed.py
│   │   ├── webtoons.py
│   │   └── admin.py
│   └── middleware.py             # Webhook allowlist (Reddit, Google, MangaDex only)
├── agents/                       # LangGraph agent definitions
│   ├── graph.py                  # Master StateGraph
│   ├── nodes/
│   │   ├── preference_cleaner.py
│   │   ├── webtoon_scraper.py
│   │   ├── rag_retriever.py
│   │   ├── feed_ranker.py
│   │   └── feedback_updater.py
│   └── state.py                  # TypedDict global AgentState
├── vector_store/
│   ├── chroma_client.py          # Two ChromaDB collections
│   ├── collections/
│   │   ├── webtoon_universe.py   # 300+ scraped webtoons (main)
│   │   └── context_window_db.py  # Cerberus context-window substitute
│   └── embedder.py               # Local MiniLM embeddings
├── media/
│   └── users/{user_id}/
│       ├── preferences.json      # Cleaned user preference object
│       ├── cycle_state.json      # Full app operating cycle state
│       └── feedback_log.json
├── static/                       # Tailwind compiled CSS, Alpine.js
├── templates/                    # Django HTML templates
├── requirements.txt
├── README.md                     # What was built
└── BACKEND_SETUP.md              # Beginner server setup guide
```

---

## 4. DATABASE DESIGN (Hybrid SQL + NoSQL)

### 4.1 SQL Models (Django ORM → SQLite/PostgreSQL)

**`SpellUser`** — extends `AbstractUser`
```
id (UUID PK), username, email, password_hash,
display_name, created_at, last_login,
preference_json_path (CharField → media/users/{id}/preferences.json),
onboarding_complete (Boolean), is_admin (Boolean)
```

**`Webtoon`** — master catalogue
```
id (UUID PK), title, slug, genre (ArrayField/JSON),
colour_rating (Float 0-1), popularity_rank (Int),
mangadex_id (CharField), synopsis_200w (TextField),
cover_url (URL), source_url (URL),
scraped_at (DateTime), is_active (Boolean)
```

**`UserWebtoonStatus`** — per-user tracking
```
id, user (FK SpellUser), webtoon (FK Webtoon),
status (ENUM: suggested/reading/completed/skipped),
user_rating (Int 1-5, nullable), feedback_note (Text nullable),
updated_at (DateTime)
```

**`FeedCycle`** — tracks recommendation iteration
```
id, user (FK), cycle_number (Int), webtoons_suggested (JSON Array of IDs),
all_skipped (Boolean), fallback_triggered (Boolean),
scrape_expansion_triggered (Boolean), created_at
```

**`AppOperatingCycle`** — global cycle state (stored also as JSON)
```
id, cycle_id (UUID), phase (ENUM: onboarding/scraping/embedding/feeding/feedback/expanding),
langgraph_run_id (CharField), langsmith_trace_url (URL), metadata (JSON), timestamp
```

### 4.2 JSON Document Store (under `media/users/{id}/`)

**`preferences.json`** — Cerberus-cleaned user preference object:
```json
{
  "user_id": "uuid",
  "raw_input": "I like dark fantasy with romance...",
  "cleaned_genres": ["dark fantasy", "romance", "action"],
  "tone_preferences": ["slow burn", "plot twists"],
  "art_style_preferences": ["vibrant", "detailed"],
  "disliked_themes": ["gore", "mecha"],
  "vector_embedding_id": "chroma_doc_id",
  "last_updated": "ISO8601"
}
```

**`cycle_state.json`** — full operating cycle snapshot for LangGraph resumption.

**`feedback_log.json`** — appended after each completed/skipped action.

---

## 5. AUTHENTICATION & AUTHORISATION

### AuthN (Authentication)
- Django `AbstractUser` with session-based auth + JWT tokens for FastAPI endpoints.
- On first visit: user enters name/email → Django creates `SpellUser` → session initialized.
- Passwords hashed with `argon2` via `django-argon2`.
- JWT issued via `djangorestframework-simplejwt`, stored in HttpOnly cookies.

### AuthZ (Authorization) — Middleware Enforcement
Create `apps/auth_core/middleware.py`:
```python
class SpellAuthZMiddleware:
    PERMITTED_PATHS_PER_ROLE = {
        "user": ["/feed/", "/profile/", "/genres/", "/webtoons/", "/onboarding/"],
        "admin": ["*"]
    }
    # Block any path not in user's permitted list
    # Inject user.id into every request context
    # FastAPI dependency: get_current_user() validates JWT + scope
```
- Users can **only** access: their feed, their profile, genre pages, sign-in page.
- No cross-user data leakage: every DB query filters by `user_id` from JWT payload.
- Admin bypass: separate login form at `/admin-spell/login/` with hardcoded credentials (see §10).

### FastAPI Webhook Middleware (Allowlist)
In `api/middleware.py`, implement `WebhookOriginMiddleware`:
- Only allow inbound webhook POST calls from: `api.mangadex.org`, `www.reddit.com`, `serpapi.com`.
- All others → 403. Validated by `X-Webhook-Source` header + domain check.

---

## 6. LANGGRAPH MULTI-AGENT PIPELINE

Define a single `StateGraph` in `agents/graph.py`. The global `AgentState` (TypedDict) carries all data between nodes, eliminating redundant API calls.

```
AgentState:
  user_id, raw_preferences, cleaned_preferences_json,
  webtoon_universe_loaded (bool), top_20_ids (List),
  feed_cycle_number (int), all_skipped (bool),
  expansion_count (int), scrape_triggered (bool),
  websocket_channel (str), langsmith_run_id (str)
```

### Node Sequence (LangGraph Directed Graph):

```
[START]
  │
  ▼
[onboarding_node]
  Calls Cerberus API with user's raw preference text.
  System prompt: "Extract genre, tone, art style preferences. 
  Return strict JSON only. Under 400 tokens."
  Writes output → preferences.json, embeds in ChromaDB context_window_db.
  │
  ▼ (parallel fork)
  ├──[webtoon_scraper_node]───────────────────────────────────┐
  │   Calls Cerberus API: "Search and return 300 popular      │
  │   colourful webtoon titles as JSON array."                │
  │   Token budget: 2 batches × 2000 tokens.                 │
  │   Falls back to SerpAPI: query="top colourful webtoons    │
  │   site:reddit.com OR site:mangadex.org"                  │
  │   Writes to Webtoon SQL table.                           │
  │                                                          │
  └──[mangadex_fetch_node]────────────────────────────────────┤
      MangaDex API: GET /manga?title={name}&contentRating[]=safe
      Fetches: mangadex_id, cover filename, synopsis.
      Stores cover URL + 200-word synopsis in Webtoon model.
      Batch size: 20 titles per request. Async with asyncio.gather().
  │ (join)
  ▼
[embedding_node]
  Embeds each Webtoon's synopsis_200w using MiniLM (local).
  Upserts into ChromaDB collection: "webtoon_universe".
  Also embeds preferences.json → same collection for cross-query.
  Context-window substitute: embed full scraped text into 
  "context_window_db" collection (used to avoid hitting Cerberus token limits).
  │
  ▼
[rag_retriever_node]
  Query ChromaDB "webtoon_universe" with preferences embedding.
  Retrieve top 20 nearest neighbours.
  Pass IDs to Cerberus API for re-ranking:
  "Given user prefers {cleaned_genres}, rank these 20 webtoons.
  Return JSON: [{id, rank, reason_50_words}]"
  Token-efficient: use context_window_db to inject summaries instead
  of raw text (stays under 4000-token Cerberus limit).
  Emit top_20_ids → FeedCycle record created in SQL.
  │
  ▼
[feed_delivery_node]
  WebSocket push: server → client channel "{user_id}_feed"
  Payload: webtoon cards (title, cover_url, genre, reason).
  MangaDex API fetches chapter preview cards for each title.
  UI renders feed. User clicks: Reading / Completed / Skip.
  │
  ▼
[feedback_collector_node]
  On each "Completed" click: prompt user for 1-5 rating + note.
  Cerberus API: "Update preference profile. Old: {prefs}. 
  New feedback: {feedback_log}. Return updated JSON."
  Writes updated preferences.json. Re-embeds in ChromaDB.
  │
  ▼ (conditional branching)
  ├── [If ≥1 webtoon engaged] → LOOP BACK to rag_retriever_node (next cycle)
  │
  └── [If ALL 20 skipped] → [expansion_node]
        Increment expansion_count.
        Widen ChromaDB query (top_k = 40, then 80).
        If expansion_count ≥ 3:
          → [silent_scrape_node]
              Celery background task.
              SerpAPI: "best colourful webtoons 2024 reddit"
              Reddit JSON API: r/webtoons/top.json?limit=100
              Cerberus: parse + clean 100 new titles.
              Embed + upsert into "webtoon_universe" ChromaDB.
              Trigger rag_retriever_node with refreshed DB.
```

### Cerberus API Token Optimisation Strategy
- Never pass raw HTML to Cerberus. Always pre-summarise with local MiniLM embeddings + ChromaDB retrieval first.
- Use `context_window_db` ChromaDB collection as a "memory injection" layer: retrieve the 3 most relevant webtoon summaries (each ≤ 150 words) and inject into the Cerberus prompt instead of full documents.
- Keep all Cerberus system prompts ≤ 500 tokens. User content ≤ 3 000 tokens. Total ≤ 3 800 (safe under 4 000 limit).
- Use streaming (`stream=True`) on Cerberus where supported to reduce perceived latency.

LangSmith tracing enabled via:
```python
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
os.environ["LANGCHAIN_PROJECT"] = "spellscroll-mvp"
```
Every LangGraph run creates a traceable run. `AppOperatingCycle.langsmith_trace_url` stores the run URL for audit.

---

## 7. WEBSOCKET ARCHITECTURE (Django Channels)

In `apps/feed/consumers.py`, define `FeedConsumer(AsyncWebsocketConsumer)`:
- Channel group name: `feed_{user_id}` (AuthZ enforced: JWT validated in `websocket_connect`).
- Events:
  - `feed.update` → push new webtoon cards JSON
  - `scrape.status` → push background scrape progress ("Expanding your universe… 47/100")
  - `preference.updated` → push notification "Your taste profile has been refined"
  - `error` → push error state

FastAPI also exposes `/api/v1/ws/{user_id}` as an alternative WebSocket for thin clients (Android).

In `api/middleware.py`, `WebhookOriginMiddleware` wraps all `/api/v1/webhooks/*` routes — domain allowlist enforced before any handler runs.

---

## 8. GLOBAL STATE MANAGEMENT (Alpine.js)

In `templates/base.html`, define a single Alpine.js `x-data` store at the `<body>` level:
```javascript
Alpine.store('spellState', {
  user: { id: null, name: null, onboarded: false },
  feed: { webtoons: [], loading: false, cycleNumber: 0 },
  ui: { activeGenre: 'all', sidebarOpen: false, scrapeRunning: false },
  preferences: { genres: [], tone: [], artStyle: [] },
  websocket: null,
  init() { this.connectWS(); },
  connectWS() { /* connect to /ws/feed/{user_id} */ }
})
```
All Django template components bind to `$store.spellState.*`. No page reloads required for feed updates.

---

## 9. UI DESIGN SPECIFICATION

**Design Language:** Dark ambient, ink-and-neon. Inspired by webtoon panel aesthetics.
- **Background:** `#0D0D14` (near-black indigo)
- **Surface:** `#161622`
- **Accent Primary:** `#A78BFA` (violet — magical, scroll-like)
- **Accent Secondary:** `#34D399` (mint — fresh discovery)
- **Text Primary:** `#F1F0FF`
- **Text Muted:** `#6B6B8A`
- **Font Display:** `Cinzel` (Google Fonts — ancient scroll energy)
- **Font Body:** `Inter`

**Pages:**
1. `/` — Landing / Sign-in. Full-bleed animated webtoon panel mosaic bg. Cinzel headline "SPELLSCROLL". Email + name form.
2. `/onboarding/` — Chat-style preference intake. Alpine.js drives step-by-step questions. Each answer submitted to `POST /api/v1/onboarding/preferences`.
3. `/feed/` — Main recommendation feed. 4-column card grid (desktop), 2-column (mobile). Genre filter tabs at top. Real-time WebSocket updates.
4. `/webtoon/{slug}/` — Detail page. Cover, synopsis, MangaDex chapter preview cards, user status selector.
5. `/profile/` — User taste profile visualised. Genre radar chart (Chart.js). Preference JSON human-readable summary.
6. `/genres/` — Genre explorer. All active genres pulled from DB, coloured tags.

---

## 10. ADMIN SYSTEM

**Admin Login URL:** `/admin-spell/login/`  
**Username:** `spellmaster`  
**Password:** `Scroll@Admin2025!`  
*(Change in `settings.py` under `SPELL_ADMIN_CREDENTIALS` before production.)*

Admin capabilities (Django admin + custom `/admin-spell/` views):
- View all users, their preference JSON, feed cycle history.
- Manually trigger `webtoon_scraper_node` for a full DB refresh.
- Edit any Webtoon record (title, genre, colour_rating, active status).
- View LangSmith trace URLs per user cycle.
- Clear/reset ChromaDB collections.
- Toggle maintenance mode (blocks all non-admin routes with 503).
- Accessible from any Android browser at `http://{local_ip}:8000/admin-spell/` on local network.

---

## 11. FASTAPI ROUTER MAP

All routes mounted at `/api/v1/`. JWT required on all except `/auth/`.

```
POST   /auth/register               → Create SpellUser
POST   /auth/login                  → Return JWT
POST   /onboarding/preferences      → Submit raw preference text → trigger onboarding_node
GET    /feed/current                → Return current top_20 for user
POST   /feed/feedback               → Submit status + rating for a webtoon
POST   /feed/expand                 → Manually trigger expansion_node
GET    /webtoons/                   → Paginated webtoon list (genre filter param)
GET    /webtoons/{id}               → Single webtoon detail
GET    /profile/                    → Return preferences.json summary
GET    /genres/                     → All genre tags
WS     /ws/feed/{user_id}           → WebSocket feed channel

--- Admin routes (admin JWT scope required) ---
GET    /admin/users/                → All users list
POST   /admin/scrape/trigger        → Trigger full scrape
PATCH  /admin/webtoons/{id}         → Edit webtoon record
GET    /admin/cycles/               → All FeedCycle records
DELETE /admin/chroma/reset          → Clear ChromaDB collections
```

**Webhook routes (middleware-gated, allowlist: MangaDex, Reddit, SerpAPI):**
```
POST   /webhooks/mangadex/          → Receive cover update events
POST   /webhooks/reddit/            → Receive new post events from r/webtoons
```

---

## 12. CELERY BACKGROUND TASKS

`tasks/scrape_tasks.py`:
- `task: scrape_webtoons_from_web(user_id)` — full scrape pipeline (SerpAPI + Reddit + Cerberus clean). Runs silently. On completion, calls `embedding_node` and pushes `scrape.status` WebSocket event.
- `task: refresh_mangadex_covers()` — periodic task (weekly), re-fetches cover URLs via MangaDex for all active webtoons.
- `task: reembed_preferences(user_id)` — re-embeds updated preferences.json after feedback loop.

Celery broker: Redis (`redis://localhost:6379/0`). Beat scheduler for periodic tasks.

---

## 13. DELIVERABLE FILES TO GENERATE

The agent must also produce:

### `README.md` (What Was Built)
Sections: Project Summary · Architecture Overview · Key Design Decisions · LangGraph Pipeline Walkthrough · ChromaDB Collections Explained · Cerberus Token Strategy · Known Limitations + Future Work.

### `BACKEND_SETUP.md` (Beginner Server Setup)
Step-by-step: Install Python 3.11 → Create virtualenv → `pip install -r requirements.txt` → Set `.env` variables (all API keys) → `python manage.py migrate` → `python manage.py collectstatic` → Start Redis → Start Celery worker → Start Django: `python manage.py runserver` → Access at `http://localhost:8000`. Each step has a "what this does" plain-language explanation.

---

## 14. ENVIRONMENT VARIABLES (`.env`)

```
SECRET_KEY=django-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
CERBERUS_API_KEY=your_cerberus_key
MANGADEX_CLIENT_ID=your_mangadex_id
MANGADEX_CLIENT_SECRET=your_mangadex_secret
SERPAPI_KEY=your_serpapi_key
LANGSMITH_API_KEY=your_langsmith_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=spellscroll-mvp
REDIS_URL=redis://localhost:6379/0
SPELL_ADMIN_USER=spellmaster
SPELL_ADMIN_PASSWORD=Scroll@Admin2025!
CHROMA_PERSIST_DIR=./vector_store/chroma_data
MEDIA_ROOT=./media
```

---

## 15. IMPLEMENTATION PRIORITY (MVP Build Order)

1. Django project scaffold + SpellUser model + AuthN/AuthZ middleware
2. SQLite schema (all models) + Django admin registration
3. FastAPI mount inside Django + JWT auth dependency
4. ChromaDB client + both collections initialised + MiniLM embedder
5. LangGraph `onboarding_node` + `preference_cleaner` with Cerberus API
6. `webtoon_scraper_node` (SerpAPI + Reddit) + `mangadex_fetch_node`
7. `embedding_node` (upsert all webtoons into ChromaDB)
8. `rag_retriever_node` + `feed_ranker_node` with Cerberus re-ranking
9. Django Channels WebSocket consumer + Alpine.js global state connection
10. Frontend: all 6 pages templated with Tailwind (dark ambient design)
11. `feedback_collector_node` + preferences.json update loop
12. `expansion_node` + `silent_scrape_node` + Celery integration
13. Admin panel (`/admin-spell/`) with all controls
14. LangSmith trace URL capture + `AppOperatingCycle` logging
15. `README.md` + `BACKEND_SETUP.md` generation

---

*Blueprint version 1.0 — Spellscroll MVP. All agents should treat this document as the single source of truth. Do not deviate from auth, route, or agent node structure without explicit instruction.*
