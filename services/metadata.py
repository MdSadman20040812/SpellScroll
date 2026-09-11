"""Provider-neutral metadata record.

Each provider maps its own payload onto :class:`SeriesMetadata` so the rest of
the application never has to know which upstream a field came from.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# Genre vocabulary normalisation: providers disagree on casing and wording, and
# the feed's genre filter is only useful if "Sci-Fi", "sci fi" and "Science
# Fiction" collapse to one chip.
_GENRE_ALIASES = {
    "sci-fi": "sci-fi",
    "sci fi": "sci-fi",
    "science fiction": "sci-fi",
    "slice of life": "slice of life",
    "girls love": "romance",
    "boys love": "romance",
    "shoujo ai": "romance",
    "shounen ai": "romance",
    "mahou shoujo": "fantasy",
    "supernatural": "supernatural",
    "psychological": "psychological",
    "mecha": "mecha",
}

_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def normalise_genre(raw: str) -> str:
    cleaned = _WHITESPACE.sub(" ", (raw or "").strip().lower())
    return _GENRE_ALIASES.get(cleaned, cleaned)


def clean_description(raw: Optional[str], max_words: int = 200) -> str:
    """Strip provider HTML/markup and clamp to a card-sized synopsis."""
    if not raw:
        return ""
    text = raw.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
    text = _HTML_TAG.sub(" ", text)
    text = (
        text.replace("&quot;", '"')
        .replace("&#039;", "'")
        .replace("&amp;", "&")
        .replace("&mdash;", "—")
        .replace("&ldquo;", "\u201c")
        .replace("&rdquo;", "\u201d")
    )
    # Provider blurbs routinely end with a "(Source: ...)" credit line.
    text = re.sub(r"\(Source:.*?\)", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = _WHITESPACE.sub(" ", text).strip()
    words = text.split(" ")
    if len(words) > max_words:
        text = " ".join(words[:max_words]).rstrip(",;:") + "\u2026"
    return text


@dataclass
class SeriesMetadata:
    """One webtoon as described by an upstream provider."""

    title: str
    provider: str = ""
    provider_id: str = ""
    anilist_id: Optional[int] = None
    mangadex_id: str = ""
    alt_titles: List[str] = field(default_factory=list)
    genres: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    synopsis: str = ""
    cover_url: str = ""
    banner_url: str = ""
    accent_color: str = ""
    source_url: str = ""
    external_links: Dict[str, str] = field(default_factory=dict)
    average_score: Optional[int] = None
    popularity: Optional[int] = None
    chapters: Optional[int] = None
    release_year: Optional[int] = None
    status: str = ""
    country: str = ""
    authors: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        seen: set = set()
        normalised: List[str] = []
        for genre in self.genres:
            value = normalise_genre(genre)
            if value and value not in seen:
                seen.add(value)
                normalised.append(value)
        self.genres = normalised
        self.synopsis = clean_description(self.synopsis)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def merge(self, other: "SeriesMetadata") -> "SeriesMetadata":
        """Fill this record's empty fields from ``other`` (a fallback provider).

        The primary provider always wins on fields it actually populated; the
        fallback only contributes what would otherwise be blank.
        """
        for key, value in other.to_dict().items():
            if key in ("provider", "provider_id"):
                continue
            current = getattr(self, key)
            if current in ("", None, [], {}) and value not in ("", None, [], {}):
                setattr(self, key, value)
        if not self.genres:
            self.genres = other.genres
        return self


def colour_rating_from(meta: SeriesMetadata) -> float:
    """Estimate how visually colourful a series is, in the range 0..1.

    SpellScroll ranks on "colourfulness"; no provider exposes such a field, so
    it is inferred from format and genre signals.  Korean/Chinese webtoons are
    full-colour by production convention, while Japanese manga is not, and
    horror/thriller/psychological work skews darker regardless of origin.
    """
    if meta.country in ("KR", "CN", "TW"):
        score = 0.86
    elif meta.country == "JP":
        score = 0.30
    else:
        score = 0.55

    genres = set(meta.genres)
    bright = {"romance", "comedy", "slice of life", "fantasy", "adventure", "sports"}
    dark = {"horror", "thriller", "psychological", "mystery", "drama"}
    score += 0.04 * len(genres & bright)
    score -= 0.05 * len(genres & dark)

    if meta.average_score:
        # Nudge well-regarded series up a touch; polish correlates with art.
        score += (meta.average_score - 70) / 1000.0

    return round(max(0.05, min(1.0, score)), 3)
