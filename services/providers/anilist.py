"""AniList GraphQL provider - the primary source for covers and metadata.

AniList is preferred over MangaDex because it serves stable CDN cover *and*
banner images (``s4.anilist.co``, hotlink friendly), a dominant cover colour,
normalised genres, scores and real publisher links - all without an API key.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

from services.http import RateLimiter, request_json
from services.metadata import SeriesMetadata

logger = logging.getLogger(__name__)

ENDPOINT = "https://graphql.anilist.co"
PROVIDER = "anilist"

# AniList permits ~90 requests/minute; ~1.4 req/s keeps a wide margin.
_limiter = RateLimiter(min_interval=0.7)

_MEDIA_FIELDS = """
  id
  title { romaji english native }
  synonyms
  coverImage { extraLarge large color }
  bannerImage
  genres
  tags { name rank isGeneralSpoiler }
  description(asHtml: false)
  averageScore
  popularity
  chapters
  status
  format
  countryOfOrigin
  startDate { year }
  siteUrl
  externalLinks { site url }
  staff(perPage: 4) { edges { role node { name { full } } } }
"""

# Searching through Page (rather than a single Media) lets us restrict to comic
# formats and re-rank candidates ourselves.  AniList's MANGA type also covers
# light novels, so a bare search for "Tower of God" happily returns the novel.
_SEARCH_QUERY = """
query ($search: String) {
  Page(page: 1, perPage: 8) {
    media(search: $search, type: MANGA, format_in: [MANGA, ONE_SHOT], sort: SEARCH_MATCH) { %s }
  }
}
""" % _MEDIA_FIELDS

_SEARCH_MANY_QUERY = """
query ($search: String, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    media(search: $search, type: MANGA, format_in: [MANGA, ONE_SHOT], sort: SEARCH_MATCH) { %s }
  }
}
""" % _MEDIA_FIELDS

_BY_ID_QUERY = """
query ($id: Int) {
  Media(id: $id, type: MANGA) { %s }
}
""" % _MEDIA_FIELDS

_BROWSE_QUERY = """
query ($page: Int, $perPage: Int, $country: CountryCode, $sort: [MediaSort]) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { currentPage lastPage hasNextPage }
    media(type: MANGA, countryOfOrigin: $country, sort: $sort, isAdult: false) { %s }
  }
}
""" % _MEDIA_FIELDS

# Sites that actually host the series for a reader, best first.
_READER_SITES = (
    "WEBTOON",
    "Tapas",
    "Tappytoon",
    "Lezhin",
    "Manta",
    "INKR",
    "Pocket Comics",
    "KakaoPage",
    "Naver Webtoon",
)


def _execute(query: str, variables: Dict[str, Any]) -> Optional[dict]:
    payload = request_json(
        "POST",
        ENDPOINT,
        limiter=_limiter,
        json={"query": query, "variables": variables},
        headers={"Content-Type": "application/json"},
    )
    if not payload:
        return None
    if payload.get("errors"):
        logger.warning("AniList error: %s", payload["errors"][:1])
    return payload.get("data")


def _pick_source_url(media: Dict[str, Any]) -> str:
    links = media.get("externalLinks") or []
    by_site: Dict[str, str] = {}
    for link in links:
        site = (link.get("site") or "").strip()
        url = link.get("url") or ""
        # Prefer the English-language edition when a site is listed many times.
        if site and url and (site not in by_site or "/en/" in url):
            by_site[site] = url
    for site in _READER_SITES:
        if site in by_site:
            return by_site[site]
    return media.get("siteUrl") or ""


def _external_links(media: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for link in media.get("externalLinks") or []:
        site = (link.get("site") or "").strip()
        url = link.get("url") or ""
        if site and url and site not in out:
            out[site] = url
    if media.get("siteUrl"):
        out.setdefault("AniList", media["siteUrl"])
    return out


def _authors(media: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for edge in ((media.get("staff") or {}).get("edges") or []):
        role = (edge.get("role") or "").lower()
        name = ((edge.get("node") or {}).get("name") or {}).get("full")
        if name and any(k in role for k in ("story", "art", "original")):
            if name not in names:
                names.append(name)
    return names[:3]


def _tags(media: Dict[str, Any], limit: int = 8) -> List[str]:
    tags = []
    for tag in media.get("tags") or []:
        if tag.get("isGeneralSpoiler"):
            continue
        if (tag.get("rank") or 0) < 50:
            continue
        name = (tag.get("name") or "").strip().lower()
        if name:
            tags.append(name)
    return tags[:limit]


def to_metadata(media: Dict[str, Any]) -> SeriesMetadata:
    title_group = media.get("title") or {}
    title = title_group.get("english") or title_group.get("romaji") or title_group.get("native") or ""
    cover = media.get("coverImage") or {}
    alt = [t for t in (title_group.get("romaji"), title_group.get("native")) if t and t != title]
    alt += [s for s in (media.get("synonyms") or [])][:4]

    return SeriesMetadata(
        title=title.strip(),
        provider=PROVIDER,
        provider_id=str(media.get("id") or ""),
        anilist_id=media.get("id"),
        alt_titles=alt,
        genres=media.get("genres") or [],
        tags=_tags(media),
        synopsis=media.get("description") or "",
        cover_url=cover.get("extraLarge") or cover.get("large") or "",
        banner_url=media.get("bannerImage") or "",
        accent_color=cover.get("color") or "",
        source_url=_pick_source_url(media),
        external_links=_external_links(media),
        average_score=media.get("averageScore"),
        popularity=media.get("popularity"),
        chapters=media.get("chapters"),
        release_year=((media.get("startDate") or {}).get("year")),
        status=(media.get("status") or "").lower(),
        country=media.get("countryOfOrigin") or "",
        authors=_authors(media),
    )


def _title_keys(*values: Any) -> set:
    keys = set()
    for value in values:
        if isinstance(value, str) and value:
            keys.add("".join(ch for ch in value.lower() if ch.isalnum()))
    return keys


def _match_score(wanted: str, media: Dict[str, Any]) -> float:
    """Rank a search candidate against the requested title.

    An exact title hit dominates; popularity only breaks ties.  Without this,
    AniList's SEARCH_MATCH order routinely puts a spin-off or a re-release
    ahead of the series that was actually asked for.
    """
    titles = media.get("title") or {}
    candidates = _title_keys(
        titles.get("english"), titles.get("romaji"), titles.get("native")
    ) | _title_keys(*(media.get("synonyms") or [])[:6])
    target = "".join(ch for ch in wanted.lower() if ch.isalnum())

    if target in candidates:
        score = 100.0
    elif any(target in candidate or candidate in target for candidate in candidates):
        score = 60.0
    else:
        score = 0.0

    # Sequels and side stories share a prefix with the original; prefer the
    # entry that is closest in length to what was asked for.
    closest = min((abs(len(c) - len(target)) for c in candidates), default=99)
    score -= min(closest, 40) * 0.4
    score += min((media.get("popularity") or 0) / 20000.0, 3.0)
    return score


def search_many(title: str, limit: int = 24) -> List[SeriesMetadata]:
    """All comic-format matches for a query, best match first.

    Used by the catalogue's live search so a reader can reach series that have
    not been imported into the local database yet.
    """
    if not title:
        return []
    data = _execute(_SEARCH_MANY_QUERY, {"search": title, "perPage": min(limit, 50)})
    media_list = ((data or {}).get("Page") or {}).get("media") or []
    ranked = sorted(media_list, key=lambda m: _match_score(title, m), reverse=True)
    return [to_metadata(m) for m in ranked[:limit]]


def search(title: str) -> Optional[SeriesMetadata]:
    """Best-match lookup by title, restricted to comic formats."""
    if not title:
        return None
    data = _execute(_SEARCH_QUERY, {"search": title})
    media_list = ((data or {}).get("Page") or {}).get("media") or []
    if not media_list:
        return None
    best = max(media_list, key=lambda m: _match_score(title, m))
    return to_metadata(best)


def fetch_by_id(anilist_id: int) -> Optional[SeriesMetadata]:
    data = _execute(_BY_ID_QUERY, {"id": int(anilist_id)})
    media = (data or {}).get("Media")
    return to_metadata(media) if media else None


def browse(
    *,
    country: str = "KR",
    limit: int = 50,
    sort: str = "POPULARITY_DESC",
    per_page: int = 50,
) -> List[SeriesMetadata]:
    """Page through AniList's catalogue for a country of origin.

    Used to bootstrap the catalogue with real, currently-popular webtoons
    instead of a hand-maintained list of IDs that rot over time.
    """
    results: List[SeriesMetadata] = []
    page = 1
    while len(results) < limit:
        data = _execute(
            _BROWSE_QUERY,
            {
                "page": page,
                "perPage": min(per_page, 50),
                "country": country,
                "sort": [sort],
            },
        )
        page_data = (data or {}).get("Page") or {}
        media_list: Iterable[Dict[str, Any]] = page_data.get("media") or []
        batch = [to_metadata(m) for m in media_list]
        if not batch:
            break
        results.extend(batch)
        if not (page_data.get("pageInfo") or {}).get("hasNextPage"):
            break
        page += 1
    return results[:limit]
