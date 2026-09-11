import json
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.webtoons.models import UserWebtoonStatus, Webtoon

# Starting points offered during onboarding.  ``phrase`` is what gets appended
# to the free-text box, so it reads as natural language to the preference agent
# rather than as a bare tag.
TASTE_SEEDS = [
    {"label": "Slow-burn romance", "phrase": "slow-burn romance with real emotional stakes"},
    {"label": "Dark fantasy", "phrase": "dark fantasy with a heavy atmosphere"},
    {"label": "Power fantasy", "phrase": "power fantasy where the lead grows stronger over time"},
    {"label": "Cultivation", "phrase": "murim and cultivation stories"},
    {"label": "Psychological", "phrase": "psychological thrillers that get under my skin"},
    {"label": "Comedy", "phrase": "comedy with sharp character writing"},
    {"label": "Isekai", "phrase": "isekai and regression premises"},
    {"label": "Slice of life", "phrase": "gentle slice-of-life stories"},
    {"label": "Bold art", "phrase": "bold, high-contrast art that goes wild during action scenes"},
    {"label": "Mystery", "phrase": "mysteries with a real payoff"},
    {"label": "Sports", "phrase": "sports stories about obsession and rivalry"},
    {"label": "Horror", "phrase": "horror that actually unsettles me"},
]


@login_required
def onboarding_view(request):
    if request.user.onboarding_complete:
        return redirect("feed_home")
    return render(request, "onboarding.html", {"seeds": TASTE_SEEDS})


@login_required
def feed_home_view(request):
    if not request.user.onboarding_complete:
        return redirect("onboarding")

    # Statuses are rendered client-side from the feed payload; this seeds the
    # initial paint so previously-rated cards do not flicker into place.
    statuses = {
        str(status.webtoon_id): status.status
        for status in UserWebtoonStatus.objects.filter(user=request.user)
    }

    return render(
        request,
        "feed.html",
        {
            "statuses_json": json.dumps(statuses),
            "user_id": str(request.user.id),
        },
    )


@login_required
def profile_view(request):
    user_id = str(request.user.id)
    pref_path = os.path.join(settings.MEDIA_ROOT, "users", user_id, "preferences.json")

    preferences = {}
    if os.path.exists(pref_path):
        try:
            with open(pref_path, "r", encoding="utf-8") as handle:
                preferences = json.load(handle)
        except (OSError, ValueError):
            preferences = {}

    statuses = list(
        UserWebtoonStatus.objects.filter(user=request.user).select_related("webtoon")
    )

    completed = [s for s in statuses if s.status == "completed"]
    reading = [s for s in statuses if s.status == "reading"]
    skipped = [s for s in statuses if s.status == "skipped"]

    # Genre affinity: finishing or reading a series counts for it, skipping
    # counts against.  Rendered as bar meters rather than a radar chart, which
    # needed a charting library and was unreadable at five near-equal points.
    affinity = {}
    for status in statuses:
        weight = 2 if status.status in ("completed", "reading") else -1
        for genre in status.webtoon.genres or []:
            affinity[genre] = affinity.get(genre, 0) + weight

    ranked = sorted(affinity.items(), key=lambda pair: pair[1], reverse=True)
    positive = [(name, score) for name, score in ranked if score > 0][:8]
    peak = max((score for _, score in positive), default=1)
    genre_meters = [
        {"name": name, "score": score, "percent": round(score / peak * 100)}
        for name, score in positive
    ]

    rated = [s for s in statuses if s.user_rating]
    average_rating = round(sum(s.user_rating for s in rated) / len(rated), 1) if rated else None

    return render(
        request,
        "profile.html",
        {
            "preferences": preferences,
            "completed_count": len(completed),
            "reading_count": len(reading),
            "skipped_count": len(skipped),
            "tracked_count": len(statuses),
            "average_rating": average_rating,
            "genre_meters": genre_meters,
            "reading_list": [s.webtoon for s in reading][:12],
            "completed_list": [s.webtoon for s in completed][:12],
            "catalogue_count": Webtoon.objects.filter(is_active=True).count(),
        },
    )
