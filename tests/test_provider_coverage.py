"""Measured coverage of the metadata provider chain.

This is a *live network* check, not a unit test: it asks how much of the real
webtoon landscape SpellScroll can actually resolve to a card (title + cover +
synopsis). Run it explicitly::

    python -m pytest tests/test_provider_coverage.py -s -m network

The sample below is deliberately mixed rather than a list of hits:

  * platform originals from WEBTOON, Tapas, Lezhin, Manta, Tappytoon
  * Korean manhwa, Chinese manhua and Japanese full-colour webtoons
  * mega-hits, mid-tier series and deliberately obscure long-tail titles
  * a few Canvas/indie series, which is where provider coverage genuinely
    thins out

Reporting the honest number matters more than hitting a target: the resolver
is only useful if we know where it fails.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spellscroll.settings")

import django  # noqa: E402

try:
    django.setup()
except Exception:  # pragma: no cover - settings already configured
    pass

from services import catalog  # noqa: E402

# ---------------------------------------------------------------------------
# Sample of real, currently-published series across platforms and tiers.
# ---------------------------------------------------------------------------

MEGA_HITS = [
    "Solo Leveling",
    "Tower of God",
    "Omniscient Reader's Viewpoint",
    "Lore Olympus",
    "True Beauty",
    "Eleceed",
    "Lookism",
    "Sweet Home",
    "The God of High School",
    "Noblesse",
    "unOrdinary",
    "Let's Play",
    "Bastard",
    "Nano Machine",
    "The Beginning After the End",
]

MID_TIER = [
    "The Greatest Estate Developer",
    "SSS-Class Revival Hunter",
    "Legend of the Northern Blade",
    "Return of the Mount Hua Sect",
    "Villain to Kill",
    "Study Group",
    "Wind Breaker",
    "Weak Hero",
    "Viral Hit",
    "Hardcore Leveling Warrior",
    "The Boxer",
    "Reaper of the Drifting Moon",
    "Kill the Hero",
    "Mercenary Enrollment",
    "Debut or Die",
]

ROMANCE_DRAMA = [
    "Who Made Me a Princess",
    "The Remarried Empress",
    "Under the Oak Tree",
    "Villains Are Destined to Die",
    "Death Is the Only Ending for the Villainess",
    "I Shall Master This Family",
    "Doctor Elise",
    "A Business Proposal",
    "Cheese in the Trap",
    "Age Matters",
    "Something About Us",
    "My Deepest Secret",
]

MANHUA_AND_JP = [
    "Tales of Demons and Gods",
    "Battle Through the Heavens",
    "Soul Land",
    "The Beginning After the End",
    "Release That Witch",
    "Apotheosis",
    "Martial Peak",
    "ReLIFE",
    "Fastest Man Alive",
]

LONG_TAIL = [
    "Girls of the Wild's",
    "Cursed Princess Club",
    "Not Even Bones",
    "Down to Earth",
    "Muted",
    "Winter Moon",
    "SubZero",
    "Purple Hyacinth",
    "Yumi's Cells",
    "Space Boy",
    "Gourmet Hound",
    "Melvina's Therapy",
]

SAMPLE = MEGA_HITS + MID_TIER + ROMANCE_DRAMA + MANHUA_AND_JP + LONG_TAIL


def _measure(titles):
    rows = []
    for title in titles:
        try:
            meta = catalog.resolve(title, enrich=True)
        except Exception as exc:  # a provider blowing up counts as a miss
            rows.append((title, None, "error: {0}".format(exc)))
            continue
        rows.append((title, meta, ""))
    return rows


@pytest.mark.network
def test_provider_chain_coverage():
    rows = _measure(SAMPLE)

    resolved = [m for _, m, _ in rows if m is not None]
    with_cover = [m for m in resolved if m.cover_url]
    with_synopsis = [m for m in resolved if m.synopsis]
    # A card needs artwork and a blurb to be worth rendering at all.
    card_ready = [m for m in resolved if m.cover_url and m.synopsis]

    total = len(SAMPLE)
    misses = [title for title, m, _ in rows if m is None]
    coverless = [m.title for m in resolved if not m.cover_url]

    print("\n" + "=" * 66)
    print("PROVIDER CHAIN COVERAGE  (AniList -> MangaDex -> Kitsu)")
    print("=" * 66)
    print("sample size          : {0}".format(total))
    print("resolved             : {0} ({1:.1f}%)".format(len(resolved), 100 * len(resolved) / total))
    print("  with cover art     : {0} ({1:.1f}%)".format(len(with_cover), 100 * len(with_cover) / total))
    print("  with synopsis      : {0} ({1:.1f}%)".format(len(with_synopsis), 100 * len(with_synopsis) / total))
    print("card-ready           : {0} ({1:.1f}%)".format(len(card_ready), 100 * len(card_ready) / total))

    by_provider = {}
    for meta in resolved:
        by_provider[meta.provider] = by_provider.get(meta.provider, 0) + 1
    print("resolved by provider : {0}".format(by_provider))

    if misses:
        print("\nUNRESOLVED ({0}):".format(len(misses)))
        for title in misses:
            print("  - {0}".format(title))
    if coverless:
        print("\nRESOLVED BUT NO COVER ({0}):".format(len(coverless)))
        for title in coverless:
            print("  - {0}".format(title))
    print("=" * 66)

    # The bar the product needs: a card must render for the overwhelming
    # majority of real series a user could plausibly search for.
    ratio = len(card_ready) / total
    assert ratio >= 0.95, (
        "card-ready coverage {0:.1%} is below the 95% bar; "
        "unresolved={1} coverless={2}".format(ratio, misses, coverless)
    )
