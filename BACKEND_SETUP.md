# SpellScroll — setup & operations

## 1. Install

```bash
python -m venv venv
venv\Scripts\activate        # Windows;  source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

`chromadb` and `sentence-transformers` are optional. Without them the app runs
on a deterministic hash-embedding fallback and an in-process vector store —
everything still works, recommendations are just less semantically sharp.

## 2. Configure

Create `.env` in the repository root:

```ini
SECRET_KEY=change-me
DEBUG=True

# Optional. Leave unset to run with no LLM at all.
LLM_PROVIDER=groq          # groq | gemini | openrouter | cerebras | none
LLM_API_KEY=gsk_...
LLM_MODEL=qwen/qwen3.8-27b # optional; each provider has a sensible default

SPELL_ADMIN_USER=spellmaster
SPELL_ADMIN_PASSWORD=change-me
```

No key is needed for metadata or cover art — AniList, MangaDex and Kitsu are
all used unauthenticated.

## 3. Migrate and populate

```bash
python manage.py migrate
python manage.py sync_catalog --limit 80     # fetches live from the providers
python manage.py export_catalog              # snapshot for spellscroll-web
```

`sync_catalog` discovers popular full-colour webtoons via AniList, fills gaps
from MangaDex and Kitsu, mirrors every cover to `media/covers/`, and derives an
accent colour per cover. Useful flags:

| Flag | Effect |
| --- | --- |
| `--limit N` | Target catalogue size (default 80) |
| `--refresh-only` | Re-sync existing rows; discover nothing new |
| `--covers-only` | Only re-mirror artwork and re-derive accents |
| `--force` | Re-download artwork already cached |
| `--no-images` | Metadata only |
| `--no-chapters` | Skip resolving MangaDex IDs for chapter lists |

## 4. Run

```bash
python -m uvicorn spellscroll.asgi:application --host 127.0.0.1 --port 8000
```

This serves Django, the FastAPI REST API under `/api/v1/`, and the feed
WebSocket from one ASGI process. `manage.py runserver` also works but does not
exercise the unified routing.

## 5. The web app (`spellscroll-web/`)

```bash
cd spellscroll-web
npm install
npm run dev
```

`predev`/`prebuild` copy `static/css/{tokens,spellscroll}.css` into
`app/styles/`, so both frontends always share one design system. Edit the files
under `static/css/` — never the copies.

## 6. Android (`android/`)

```bash
cd android
echo "sdk.dir=/path/to/Android/Sdk" > local.properties
./gradlew assembleDebug
```

The shell points at `http://10.0.2.2:8000` (the host machine as seen from the
emulator). For a physical device on your LAN, or a deployed instance:

```bash
./gradlew assembleDebug -PspellscrollUrl=http://192.168.1.20:8000
./gradlew assembleRelease -PspellscrollUrl=https://your-host
```

Cleartext HTTP is permitted only for `10.0.2.2`, `127.0.0.1` and `localhost`
(`res/xml/network_security_config.xml`); anything else must be HTTPS.

---

## Architecture notes

### Cover art never breaks

Templates and API payloads point at `/cover/<uuid>/` on our own origin, not at
a provider CDN. That view resolves, in order:

1. a locally mirrored file under `media/covers/`,
2. a fresh download from the upstream (mirrored for next time),
3. a generated SVG placeholder derived from the title.

So a dead provider, a hotlink block or a changed filename degrades to a styled
gradient instead of a broken image.

### Provider chain

`services/catalog.py` resolves AniList → MangaDex → Kitsu, then tops up blank
fields from the providers it did not use first. AniList leads because it is the
only one that reliably supplies a cover *and* a banner *and* a dominant colour.

Measured coverage (`tests/test_provider_coverage.py`, 63 real titles spanning
WEBTOON/Tapas/Lezhin/Manta originals, manhwa, manhua and long-tail Canvas
series): **100% card-ready** — resolved with both cover art and a synopsis.
Resolution split: AniList 48, MangaDex 14, Kitsu 1.

Run it yourself (it hits live APIs, so it is excluded from the default run):

```bash
python -m pytest tests/test_provider_coverage.py -s -m network
```

### Reaching beyond the local catalogue

The Archive is not limited to what has been synced. When a search returns few
local results, `services.catalog.search_providers` queries AniList and MangaDex
live and renders the results under "Beyond the archive"; picking one imports it
into the catalogue so the ranking agents can use it.

### LLM provider

Every supported provider speaks the OpenAI `/chat/completions` shape, so
switching is two environment variables (`services/llm.py`). All have a free
tier. With none configured, `agents/nodes/*` fall back to deterministic local
ranking — the app is fully functional with no key and no network.

**Currently configured: Groq, `qwen/qwen3.8-27b`.**

Two nodes use it:

* `preference_cleaner` turns the onboarding paragraph into structured genre,
  tone, art-style and dislike arrays.
* `feed_ranker` orders the 20 retrieved candidates and writes the one-sentence
  rationale shown on each card.

Model choice on Groq matters more than it looks:

| Model | Preference extraction | 20-item ranking |
| --- | --- | --- |
| `qwen/qwen3.8-27b` | good | **works** (~2.5s) |
| `openai/gpt-oss-20b` | good, fastest | fails Groq's JSON validation |
| `openai/gpt-oss-120b` | mislabels dislikes as likes | untested at size |

Groq retires models without notice — the Llama 3.x families this originally
targeted now 404. If a call fails with `model_not_found`, list what your key
can actually reach:

```bash
curl -s https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY" | python -m json.tool
```

Candidates are sent to the ranker by **integer index, never by UUID**. Models
garble long opaque identifiers, and an earlier version trusted the `id` string
that came back — so rationales were keyed to non-existent rows and rendered
against the wrong series. Indices are validated against the candidate set on
return, and anything the model omits falls back to the local explanation.

### Optional dependency behaviour

| Missing package | Behaviour |
| --- | --- |
| `chromadb` | In-process dict vector store with cosine search |
| `sentence-transformers` | Deterministic 384-dim hash embeddings |
| `Pillow` | Accent colours fall back to the provider's reported colour |
