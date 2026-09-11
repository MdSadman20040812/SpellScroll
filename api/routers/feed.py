import json
import logging
import os
from typing import List, Optional

from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from django.conf import settings
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from agents.graph import get_agent_graph
from agents.nodes.feedback_updater import update_user_feedback
from api.auth import get_current_user
from api.serializers import webtoon_card
from apps.feed.models import FeedCycle
from apps.webtoons.models import UserWebtoonStatus, Webtoon

logger = logging.getLogger(__name__)

router = APIRouter()

DEFAULT_PREFERENCES = "I like colourful stories."


class FeedbackRequest(BaseModel):
    webtoon_id: str
    status: str = Field(pattern="^(suggested|reading|completed|skipped)$")
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    feedback_note: Optional[str] = Field(default="", max_length=2000)


def _read_preferences(user_id: str) -> str:
    path = os.path.join(settings.MEDIA_ROOT, "users", user_id, "preferences.json")
    if not os.path.exists(path):
        return DEFAULT_PREFERENCES
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle).get("raw_input") or DEFAULT_PREFERENCES
    except (OSError, ValueError):
        return DEFAULT_PREFERENCES


def _reasons_for(user_id: str, webtoon_ids: List[str], cycle=None) -> dict:
    """Recommendation rationales keyed by webtoon id.

    The cycle record is the source of truth because it is durable; the vector
    store is consulted only to fill gaps (for cycles written before reasons
    were persisted).

    The original implementation issued one similarity query per card inside
    the serialisation loop, so a 20-card feed did 20 sequential
    embed-and-search round trips on the request path - for documents whose IDs
    were already known.
    """
    reasons = dict(getattr(cycle, "reasons", None) or {})
    missing = [wid for wid in webtoon_ids if not reasons.get(wid)]
    if not missing:
        return reasons

    from vector_store.chroma_client import chroma_client

    doc_ids = ["reason_{0}_{1}".format(user_id, wid) for wid in missing]
    try:
        documents = chroma_client.get_context_by_ids(doc_ids)
    except Exception as exc:
        logger.warning("reason lookup failed: %s", exc)
        return reasons

    prefix_length = len("reason_{0}_".format(user_id))
    for doc_id, text in documents.items():
        if text:
            reasons[doc_id[prefix_length:]] = text
    return reasons


def _serialize(webtoon_ids: List[str], user_id: str, cycle=None) -> List[dict]:
    webtoons = {
        str(w.id): w for w in Webtoon.objects.filter(id__in=webtoon_ids, is_active=True)
    }
    statuses = {
        str(s.webtoon_id): s.status
        for s in UserWebtoonStatus.objects.filter(
            user_id=user_id, webtoon_id__in=webtoon_ids
        )
    }
    reasons = _reasons_for(user_id, webtoon_ids, cycle=cycle)

    cards = []
    for webtoon_id in webtoon_ids:  # preserve the ranker's ordering
        webtoon = webtoons.get(webtoon_id)
        if webtoon is None:
            continue
        cards.append(
            webtoon_card(
                webtoon,
                reason=reasons.get(webtoon_id) or "Matched to your taste signature.",
                status=statuses.get(webtoon_id, "suggested"),
            )
        )
    return cards


async def serialize_webtoons(
    webtoon_ids: List[str], user_id: str, cycle=None
) -> List[dict]:
    return await sync_to_async(_serialize)(webtoon_ids, user_id, cycle)


@router.get("/current")
async def get_current_feed(user=Depends(get_current_user)):
    user_id = str(user.id)

    latest = await sync_to_async(
        lambda: FeedCycle.objects.filter(user=user).order_by("-created_at").first()
    )()

    if latest is not None:
        return {
            "cycle_number": latest.cycle_number,
            "generated_at": latest.created_at.isoformat(),
            "webtoons": await serialize_webtoons(
                latest.webtoons_suggested, user_id, cycle=latest
            ),
        }

    # No cycle yet: run the pipeline once so the first visit is not an empty
    # screen, then report the cycle the graph actually produced.
    try:
        graph = get_agent_graph()
        result = await sync_to_async(graph.invoke)(
            {
                "user_id": user_id,
                "raw_preferences": _read_preferences(user_id),
                "feed_cycle_number": 1,
            }
        )
    except Exception as exc:
        logger.exception("feed generation failed")
        raise HTTPException(status_code=503, detail="Could not build your feed: {0}".format(exc))

    suggested = result.get("top_20_ids", [])
    created = await sync_to_async(
        lambda: FeedCycle.objects.filter(user=user).order_by("-created_at").first()
    )()

    return {
        "cycle_number": created.cycle_number if created else 1,
        "generated_at": created.created_at.isoformat() if created else None,
        "webtoons": await serialize_webtoons(suggested, user_id, cycle=created),
    }


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest, user=Depends(get_current_user)):
    user_id = str(user.id)

    try:
        webtoon = await sync_to_async(Webtoon.objects.get)(id=req.webtoon_id)
    except (Webtoon.DoesNotExist, ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Webtoon not found")

    await sync_to_async(UserWebtoonStatus.objects.update_or_create)(
        user=user,
        webtoon=webtoon,
        defaults={
            "status": req.status,
            "user_rating": req.rating,
            "feedback_note": req.feedback_note,
        },
    )

    updated_prefs = await sync_to_async(update_user_feedback)(
        user_id=user_id,
        webtoon_id=req.webtoon_id,
        rating=req.rating or 3,
        note=req.feedback_note or "",
    )

    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            await channel_layer.group_send(
                "feed_{0}".format(user_id),
                {"type": "preference.updated", "preferences": updated_prefs},
            )
        except Exception as exc:
            logger.warning("preference broadcast failed: %s", exc)

    return {
        "status": "success",
        "message": "Saved your response to {0}.".format(webtoon.title),
        "preferences": updated_prefs,
    }


@router.post("/expand")
async def trigger_feed_expansion(user=Depends(get_current_user)):
    user_id = str(user.id)

    latest = await sync_to_async(
        lambda: FeedCycle.objects.filter(user=user).order_by("-created_at").first()
    )()
    next_cycle = (latest.cycle_number + 1) if latest else 1

    try:
        graph = get_agent_graph()
        result = await sync_to_async(graph.invoke)(
            {
                "user_id": user_id,
                "raw_preferences": _read_preferences(user_id),
                "feed_cycle_number": next_cycle,
                "expansion_count": latest.cycle_number if latest else 1,
            }
        )
    except Exception as exc:
        logger.exception("feed expansion failed")
        raise HTTPException(status_code=503, detail="Could not expand your feed: {0}".format(exc))

    created = await sync_to_async(
        lambda: FeedCycle.objects.filter(user=user).order_by("-created_at").first()
    )()
    cards = await serialize_webtoons(
        result.get("top_20_ids", []), user_id, cycle=created
    )

    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            await channel_layer.group_send(
                "feed_{0}".format(user_id), {"type": "feed.update", "webtoons": cards}
            )
        except Exception as exc:
            logger.warning("feed broadcast failed: %s", exc)

    return {"status": "success", "cycle_number": next_cycle, "webtoons": cards}
