"""Provider-agnostic chat completion, aimed at free tiers.

Every provider worth using for this MVP speaks the OpenAI ``/chat/completions``
shape, so one client covers all of them and switching is two environment
variables rather than a code change.

Configure with::

    LLM_PROVIDER=groq            # groq | gemini | openrouter | cerebras | none
    LLM_API_KEY=<key>
    LLM_MODEL=<optional override>

Nothing here is required: with no key configured, :func:`chat` raises
``LLMUnavailable`` and every caller already falls back to its deterministic
local path, which is what keeps the app fully functional offline.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from services.http import get_session

logger = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    """No provider is configured, or the provider call failed."""


@dataclass(frozen=True)
class Provider:
    name: str
    url: str
    default_model: str
    #: Free-tier headline, for the setup docs and admin panel.
    free_tier: str
    supports_json_mode: bool = True


# All OpenAI-compatible; ordered by how painless the free tier is to get.
PROVIDERS = {
    "groq": Provider(
        name="Groq",
        # Groq rotates its catalogue and retires models without notice - the
        # Llama 3.x families this previously defaulted to now 404. Check
        # GET /openai/v1/models against your key if a request fails with
        # model_not_found, and override with LLM_MODEL.
        #
        # qwen3.8-27b is the default because it reliably returns a well-formed
        # 20-item ranking; openai/gpt-oss-20b is faster on short extractions but
        # fails Groq's JSON validation on outputs that large.
        url="https://api.groq.com/openai/v1/chat/completions",
        default_model="qwen/qwen3.8-27b",
        free_tier="Free tier, no card required; generous requests/day.",
    ),
    "gemini": Provider(
        name="Google Gemini",
        url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        default_model="gemini-2.0-flash",
        free_tier="Free tier via AI Studio; large context window.",
    ),
    "openrouter": Provider(
        name="OpenRouter",
        url="https://openrouter.ai/api/v1/chat/completions",
        default_model="meta-llama/llama-3.3-70b-instruct:free",
        free_tier="One key, many `:free` models routed to other providers.",
    ),
    "cerebras": Provider(
        name="Cerebras",
        url="https://api.cerebras.ai/v1/chat/completions",
        default_model="llama3.1-8b",
        free_tier="Free daily token allowance; very fast inference.",
    ),
}


def _config():
    from django.conf import settings

    provider_key = (getattr(settings, "LLM_PROVIDER", "") or "").strip().lower()
    api_key = (getattr(settings, "LLM_API_KEY", "") or "").strip()
    model = (getattr(settings, "LLM_MODEL", "") or "").strip()

    if provider_key in ("", "none", "off"):
        return None, "", ""
    provider = PROVIDERS.get(provider_key)
    if provider is None:
        logger.warning("unknown LLM_PROVIDER %r; falling back to local ranking", provider_key)
        return None, "", ""
    if not api_key:
        return None, "", ""
    return provider, api_key, (model or provider.default_model)


def is_configured() -> bool:
    provider, _, _ = _config()
    return provider is not None


def active_provider_name() -> str:
    provider, _, model = _config()
    return "{0} ({1})".format(provider.name, model) if provider else "local fallback"


def chat(
    system_prompt: str,
    user_prompt: str,
    *,
    json_mode: bool = True,
    temperature: float = 0.2,
    max_tokens: int = 4000,
    timeout: int = 45,
) -> str:
    """Return the assistant's message content, or raise :class:`LLMUnavailable`."""
    provider, api_key, model = _config()
    if provider is None:
        raise LLMUnavailable("No LLM provider configured (set LLM_PROVIDER and LLM_API_KEY).")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode and provider.supports_json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {"Authorization": "Bearer {0}".format(api_key), "Content-Type": "application/json"}
    if provider.name == "OpenRouter":
        # OpenRouter asks clients to identify themselves for free-tier routing.
        headers["HTTP-Referer"] = "https://github.com/MdSadman20040812/SpellScroll"
        headers["X-Title"] = "SpellScroll"

    try:
        response = get_session().post(
            provider.url, headers=headers, json=payload, timeout=timeout
        )
    except Exception as exc:
        raise LLMUnavailable("{0} request failed: {1}".format(provider.name, exc))

    if response.status_code != 200:
        raise LLMUnavailable(
            "{0} returned HTTP {1}: {2}".format(
                provider.name, response.status_code, response.text[:200]
            )
        )

    try:
        return response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError) as exc:
        raise LLMUnavailable("{0} returned an unexpected body: {1}".format(provider.name, exc))


def chat_json(system_prompt: str, user_prompt: str, **kwargs) -> Optional[dict]:
    """Call :func:`chat` and parse the reply as JSON, or return ``None``.

    Models occasionally wrap JSON in prose or a code fence even in JSON mode,
    so the outermost object is extracted rather than trusting the raw string.
    """
    raw = chat(system_prompt, user_prompt, json_mode=True, **kwargs)
    try:
        return json.loads(raw)
    except ValueError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except ValueError:
                pass
    logger.warning("LLM reply was not valid JSON")
    return None
