"""Cover image caching, accent-colour extraction and placeholder generation.

Remote cover hosts are outside our control: MangaDex rewrites filenames,
AniList can rate-limit, and any of them can be unreachable when a user loads
the feed.  Rather than let a card render a broken image, every cover is served
through :func:`cache_image`, which mirrors the bytes onto local disk once and
serves them from there afterwards.  When no upstream has anything usable, a
deterministic SVG placeholder is generated from the title so the grid still
reads as a grid.
"""
from __future__ import annotations

import colorsys
import hashlib
import logging
import os
import re
from typing import Optional, Tuple

from services.http import DEFAULT_TIMEOUT, get_session

logger = logging.getLogger(__name__)

try:
    from PIL import Image

    HAS_PILLOW = True
except ImportError:  # pragma: no cover - Pillow is optional
    HAS_PILLOW = False

_EXT_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "image/gif": ".gif",
}

MAX_BYTES = 8 * 1024 * 1024  # refuse absurd downloads

# Hosts we are willing to mirror covers from.  Anything else is ignored, so a
# stray URL in the database can never turn the proxy into an open relay.
ALLOWED_HOSTS = (
    "s4.anilist.co",
    "uploads.mangadex.org",
    "mangadex.org",
    "media.kitsu.io",
    "media.kitsu.app",
    "kitsu.io",
    "swebtoon-phinf.pstatic.net",
    "webtoon-phinf.pstatic.net",
)


def cache_dir() -> str:
    from django.conf import settings

    path = os.path.join(settings.MEDIA_ROOT, "covers")
    os.makedirs(path, exist_ok=True)
    return path


def is_allowed(url: str) -> bool:
    match = re.match(r"https?://([^/:]+)", url or "")
    if not match:
        return False
    host = match.group(1).lower()
    return any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_HOSTS)


def cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def cached_path(url: str) -> Optional[str]:
    """Return the on-disk path for ``url`` if it has already been mirrored."""
    if not url:
        return None
    key = cache_key(url)
    directory = cache_dir()
    for ext in (".jpg", ".png", ".webp", ".avif", ".gif"):
        candidate = os.path.join(directory, key + ext)
        if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
            return candidate
    return None


def cache_image(url: str, *, force: bool = False) -> Optional[str]:
    """Mirror ``url`` into the local cache and return the file path.

    Returns ``None`` when the host is not allowed, the download fails, or the
    response is not actually an image.
    """
    if not url or not is_allowed(url):
        return None

    if not force:
        existing = cached_path(url)
        if existing:
            return existing

    headers = {"Accept": "image/avif,image/webp,image/jpeg,image/png,*/*"}
    if "mangadex" in url:
        # MangaDex serves covers only to clients that look like a real referrer.
        headers["Referer"] = "https://mangadex.org/"

    try:
        response = get_session().get(
            url, headers=headers, timeout=DEFAULT_TIMEOUT, stream=True
        )
    except Exception as exc:
        logger.warning("cover download failed for %s: %s", url, exc)
        return None

    with response:
        if response.status_code != 200:
            logger.warning("cover %s returned HTTP %s", url, response.status_code)
            return None

        content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        ext = _EXT_BY_CONTENT_TYPE.get(content_type)
        if ext is None:
            logger.warning("cover %s has non-image type %r", url, content_type)
            return None

        destination = os.path.join(cache_dir(), cache_key(url) + ext)
        tmp = destination + ".part"
        size = 0
        try:
            with open(tmp, "wb") as handle:
                for chunk in response.iter_content(64 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError("cover exceeds size limit")
                    handle.write(chunk)
            os.replace(tmp, destination)
        except Exception as exc:
            logger.warning("cover write failed for %s: %s", url, exc)
            if os.path.exists(tmp):
                os.remove(tmp)
            return None

    return destination


def dominant_colour(path: str) -> Optional[str]:
    """Pick a saturated, readable accent colour from a cached cover.

    The result is used for the card glow and the detail-page wash, so it is
    deliberately pushed toward mid-lightness: raw dominant pixels are often
    near-black or near-white and would read as no accent at all.
    """
    if not HAS_PILLOW or not path or not os.path.exists(path):
        return None
    try:
        with Image.open(path) as img:
            img = img.convert("RGB").resize((64, 64))
            pixels = list(img.getdata())
    except Exception as exc:
        logger.warning("colour extraction failed for %s: %s", path, exc)
        return None

    best: Optional[Tuple[float, Tuple[int, int, int]]] = None
    for r, g, b in pixels:
        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        # Favour colourful mid-tones over the black borders most covers have.
        weight = s * (1.0 - abs(l - 0.55) * 1.6)
        if best is None or weight > best[0]:
            best = (weight, (r, g, b))

    if best is None:
        return None

    r, g, b = best[1]
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    l = min(0.68, max(0.46, l))
    s = min(0.85, max(0.45, s))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{0:02x}{1:02x}{2:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def hue_from_title(title: str) -> int:
    """Stable hue so a given title always gets the same placeholder colour."""
    digest = hashlib.md5((title or "").encode("utf-8")).hexdigest()
    return int(digest[:4], 16) % 360


def placeholder_svg(title: str, *, width: int = 400, height: int = 600) -> str:
    """Deterministic gradient placeholder carrying the title's initials.

    Rendered as SVG so it costs nothing to generate, scales cleanly, and needs
    no image library at request time.
    """
    hue = hue_from_title(title)
    initials = "".join(word[0] for word in re.findall(r"[A-Za-z0-9]+", title or "?")[:2]).upper()
    safe_title = (
        (title or "Untitled")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        'width="{w}" height="{h}" role="img" aria-label="{alt}">'
        "<defs>"
        '<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="hsl({h1},58%,26%)"/>'
        '<stop offset="55%" stop-color="hsl({h2},52%,16%)"/>'
        '<stop offset="100%" stop-color="hsl({h3},46%,9%)"/>'
        "</linearGradient>"
        '<radialGradient id="v" cx="50%" cy="34%" r="70%">'
        '<stop offset="0%" stop-color="hsl({h1},70%,55%)" stop-opacity="0.32"/>'
        '<stop offset="100%" stop-color="hsl({h1},70%,55%)" stop-opacity="0"/>'
        "</radialGradient>"
        "</defs>"
        '<rect width="{w}" height="{h}" fill="url(#g)"/>'
        '<rect width="{w}" height="{h}" fill="url(#v)"/>'
        '<text x="50%" y="47%" text-anchor="middle" dominant-baseline="middle" '
        'font-family="Georgia, serif" font-size="{fs}" font-weight="700" '
        'fill="#ffffff" fill-opacity="0.9" letter-spacing="4">{initials}</text>'
        '<text x="50%" y="62%" text-anchor="middle" font-family="system-ui, sans-serif" '
        'font-size="{sfs}" fill="#ffffff" fill-opacity="0.45" '
        'letter-spacing="3">NO COVER</text>'
        "</svg>"
    ).format(
        w=width,
        h=height,
        h1=hue,
        h2=(hue + 28) % 360,
        h3=(hue + 56) % 360,
        alt=safe_title,
        fs=int(width * 0.28),
        sfs=max(9, int(width * 0.035)),
        initials=initials or "?",
    )
