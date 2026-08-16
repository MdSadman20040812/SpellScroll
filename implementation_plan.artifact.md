# Implementation Plan - SpellScroll Improvements

This plan covers fixing bugs, elevating backend operations (specifically LLM integration and database efficiency), and enhancing the visual experience of the SpellScroll platform.

## User Review Required

> [!IMPORTANT]
> I will be removing the "Anti-Inspection Security" scripts from `base.html` as they are non-standard and can interfere with legitimate debugging and user experience. Please let me know if you wish to keep them.

> [!NOTE]
> The Cerebras API update will change the environment variable name from `CEREBRAS_API_KEY` to `CEREBRAS_API_KEY`. You will need to update your `.env` file accordingly.

## Proposed Changes

### 1. Backend Optimization & LLM Update

#### [MODIFY] [preference_cleaner.py](file:///D:/github%20projects/SpellScroll/agents/nodes/preference_cleaner.py)
- Rename `call_Cerebras_api` to `call_cerebras_api`.
- Update API endpoint to `https://api.cerebras.ai/v1/chat/completions`.
- Update default model to `llama3.1-8b`.
- Replace `datetime.utcnow()` with `datetime.now(datetime.timezone.utc)`.

#### [MODIFY] [feed_ranker.py](file:///D:/github%20projects/SpellScroll/agents/nodes/feed_ranker.py) & [feedback_updater.py](file:///D:/github%20projects/SpellScroll/agents/nodes/feedback_updater.py)
- Update calls to the renamed Cerebras API function.

#### [MODIFY] [feed.py](file:///D:/github%20projects/SpellScroll/api/routers/feed.py)
- Optimize `serialize_webtoons` to avoid N+1 ChromaDB queries.
- Use `sync_to_async` for Django ORM calls to prevent blocking the FastAPI event loop.

#### [MODIFY] [settings.py](file:///D:/github%20projects/SpellScroll/spellscroll/settings.py)
- Rename `CEREBRAS_API_KEY` to `CEREBRAS_API_KEY`.

---

### 2. Visual & UI Elevation

#### [MODIFY] [base.html](file:///D:/github%20projects/SpellScroll/templates/base.html)
- Remove anti-inspection scripts.
- Refine Tailwind theme with better gradients and subtle "glow" effects.
- Add "Cinzel" font more prominently for titles.

#### [MODIFY] [feed.html](file:///D:/github%20projects/SpellScroll/templates/feed.html)
- Enhance card hover effects with "neon border" animations.
- Improve the loading state with a more themed "magical" spinner.
- Refine the feed expansion button.

---

### 3. Documentation & Cleanup

#### [MODIFY] [README.md](file:///D:/github%20projects/SpellScroll/README.md) & [SPELLSCROLL_BLUEPRINT.md](file:///D:/github%20projects/SpellScroll/SPELLSCROLL_BLUEPRINT.md)
- Update all references of "Cerebras" to "Cerebras".
- Update API keys and model names in documentation.

## Verification Plan

### Automated Tests
- I will check the syntax of modified Python files.
- I will verify that the FastAPI routes still function (logic check).

### Manual Verification
- Verify the new UI elements render correctly in a mock environment (mental check).
- Ensure the API key rename is consistent across the codebase.
