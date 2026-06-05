"""Dutch knowledge chatbot endpoint (Phases 1-3).

POST /api/chatbot/ask                          -> SSE: knowledge answer (P1), or a
                                                  validated scenario run (P2).
GET  /api/chatbot/faqs                          -> curated FAQs + published cache, ranked (P3)
GET  /api/chatbot/faqs/suggested                -> moderation queue (auth-gated, P3)
POST /api/chatbot/faqs/suggested/{id}/promote   -> publish a suggestion (auth-gated, P3)
POST /api/chatbot/faqs/suggested/{id}/reject    -> reject a suggestion (auth-gated, P3)
GET  /api/chatbot/faqs/{id}                      -> a single curated FAQ

Mirrors the scenario router's SSE convention. Read-only for knowledge; scenario
runs go through the validated engine path (no code/SQL synthesis). Confident,
grounded answers are cached as moderation *suggestions* (PII anonymised); nothing
publishes without a grounded-with-sources re-check.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.auth import CurrentUser, get_current_user, require_role
from app.config import settings
from app.routers import scenario as scenario_router
from app.services.audit import record_audit
from app.services.data_sources import build_kennisbasis
from app.services.chatbot.faq import get_faq, list_faqs
from app.services.chatbot.faq_cache import capture_answer, get_store, published_as_faqs
from app.services.chatbot.intents import classify_intent
from app.services.chatbot.recipe import execute_recipe, recipe_schema, validate_recipe
from app.services.chatbot.scenario_run import execute_plan, prepare_scenario_request
from app.services.chatbot.service import answer_question

router = APIRouter(tags=["chatbot"])


class ChatAskRequest(BaseModel):
    question: str
    scenario_id: Optional[str] = None       # resolve a stored card to explain
    scenario_card: Optional[dict] = None     # OR pass the card inline (preferred)
    model: str = "qwen3-235b-a22b-instruct-2507"


class RecipeRunRequest(BaseModel):
    """Phase 4 declarative recipe (data, not code)."""
    weights: dict = {}                       # {salinity, demand, flood, protection} summing to 1
    knmi_preset: str = "Hd"
    growth_preset: str = "middel"
    base: str = "salinity"                   # "salinity" | "populated"
    time_horizon: int = 2040
    added_homes: float = 0.0
    location_name: Optional[str] = None
    intake_id: Optional[str] = None


def _sse(event: str, data) -> dict:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False, default=str)}


def _try_load_scenario_card(scenario_id: str) -> Optional[dict]:
    """Best-effort: resolve a stored ScenarioCard by id via the scenario store.
    Decoupled and guarded — returns None if the engine/store isn't available."""
    try:
        from app.routers.scenario import _store
        cached = _store.get_by_id(scenario_id)
        if not cached:
            return None
        result = cached["result_json"]
        return json.loads(result) if isinstance(result, str) else result
    except Exception:
        return None


def _chunk_text(text: str):
    """Yield answer pieces for a streaming feel (line-wise, long lines split)."""
    for line in text.split("\n"):
        if not line:
            yield "\n"
            continue
        if len(line) <= 180:
            yield line + "\n"
        else:
            words, buf = line.split(" "), ""
            for w in words:
                if len(buf) + len(w) + 1 > 180:
                    yield buf + " "
                    buf = w
                else:
                    buf = f"{buf} {w}".strip()
            if buf:
                yield buf + "\n"


@router.post("/api/chatbot/ask")
async def chatbot_ask(req: ChatAskRequest):
    if not (req.question or "").strip():
        raise HTTPException(status_code=422, detail="Vraag mag niet leeg zijn.")

    card = req.scenario_card
    if card is None and req.scenario_id:
        card = _try_load_scenario_card(req.scenario_id)

    intent = classify_intent(req.question, has_scenario_card=card is not None)

    # ---- Phase 2: scenario-from-chat (validate -> run via the engine) ----
    if intent == "scenario_run_request":
        plan = prepare_scenario_request(req.question)

        async def gen_scenario():
            yield _sse("meta", {"message_id": str(uuid.uuid4()), "model": req.model,
                                "timestamp": time.time()})
            yield _sse("intent", {"intent": intent, "runnable": plan.runnable,
                                  "confidence": round(plan.confidence, 3)})
            # Whitelist miss / low confidence -> clarify, never run (no dead ends).
            if not plan.runnable:
                yield _sse("followup_question", {"question_nl": plan.followup_nl})
                yield _sse("done", None)
                return
            # Show the recipe that will run before the result.
            yield _sse("scenario_params_confirmed", plan.recipe_summary)
            try:
                result = await execute_plan(plan, req.question, scenario_router.DATA_DIR)
            except Exception as exc:  # engine failure -> surfaced, never a crash
                yield _sse("error", {"message": f"Kon het scenario niet doorrekenen: {exc}"})
                yield _sse("done", None)
                return
            if result["mode"] == "comparison":
                a = scenario_router._persist(result["card_a"])
                b = scenario_router._persist(result["card_b"])
                for ev in scenario_router._emit_card(a):
                    yield ev
                for ev in scenario_router._emit_card(b):
                    yield ev
                yield _sse("scenario_delta", asdict(result["delta"]))
            else:
                if result.get("followup_nl"):
                    yield _sse("followup_question", {"question_nl": result["followup_nl"]})
                    yield _sse("done", None)
                    return
                card_dict = scenario_router._persist(result["card"])
                for ev in scenario_router._emit_card(card_dict):
                    yield ev
            yield _sse("done", None)

        return EventSourceResponse(gen_scenario())

    # ---- knowledge / data_limits / explain_scenario (Phase 1, read-only) ----
    # Compute off the event loop (the GreenPT call, when keyed, is blocking).
    ans = await asyncio.to_thread(
        answer_question, req.question, scenario_card=card, model=req.model
    )

    # Phase 3: best-effort cache of a confident, grounded answer as a *suggestion*
    # (PII anonymised inside). Never breaks the response.
    try:
        await capture_answer(req.question, ans)
    except Exception:
        pass

    async def gen():
        yield _sse("meta", {
            "message_id": str(uuid.uuid4()),
            "model": req.model,
            "timestamp": time.time(),
        })
        yield _sse("intent", {"intent": ans.intent, "confidence": round(ans.confidence, 3),
                              "used_llm": ans.used_llm, "scenario_id": ans.scenario_id})
        yield _sse("sources_considered", [c.as_dict() for c in ans.sources_considered])
        if ans.followup_nl:
            yield _sse("followup_question", {"question_nl": ans.followup_nl})
        for piece in _chunk_text(ans.answer_nl):
            yield _sse("text", {"content": piece})
        yield _sse("citations", [c.as_dict() for c in ans.citations])
        yield _sse("done", None)

    return EventSourceResponse(gen())


@router.get("/api/chatbot/recipe/schema")
async def chatbot_recipe_schema():
    """The recipe surface (signals, weights, presets, ranges) for a UI form."""
    return recipe_schema()


@router.post("/api/chatbot/recipe/run")
async def chatbot_recipe_run(req: RecipeRunRequest, user: CurrentUser = Depends(get_current_user)):
    """Validate a declarative recipe and run it through the engine (SSE).
    Whitelist/weight-sum miss -> a clarifying message, never code."""
    plan = validate_recipe(req.model_dump())
    await record_audit(user, "recipe.run", "", {"runnable": plan.runnable, "base": req.base})

    async def gen():
        yield _sse("meta", {"message_id": str(uuid.uuid4()), "timestamp": time.time()})
        yield _sse("intent", {"intent": "recipe_run", "runnable": plan.runnable})
        if not plan.runnable:
            yield _sse("followup_question", {"question_nl": plan.followup_nl})
            yield _sse("done", None)
            return
        yield _sse("scenario_params_confirmed", plan.recipe_summary)
        try:
            result = await execute_recipe(plan, scenario_router.DATA_DIR)
        except Exception as exc:
            yield _sse("error", {"message": f"Kon het recept niet doorrekenen: {exc}"})
            yield _sse("done", None)
            return
        card_dict = scenario_router._persist(result["card"])
        for ev in scenario_router._emit_card(card_dict):
            yield ev
        yield _sse("done", None)

    return EventSourceResponse(gen())


@router.get("/api/kennisbasis")
async def kennisbasis():
    """"Wat weet dit systeem?" — the dataset inventory with source links + freshness
    (Phase 5). Powers the always-visible Kennisbasis panel."""
    return build_kennisbasis(scenario_router.DATA_DIR)


@router.get("/api/chatbot/faqs")
async def chatbot_faqs(limit: int = 10):
    """Curated Phase 1 FAQs first, then published cached entries ranked by hits
    (non-stale). The merged 'veelgestelde vragen' surface."""
    curated = [{**f.as_dict(), "origin": "curated"} for f in list_faqs()]
    try:
        cached = await published_as_faqs(limit)
    except Exception:
        cached = []
    return {"faqs": curated + cached}


# NB: declared BEFORE /faqs/{faq_id} so "suggested" isn't captured as an id.
@router.get("/api/chatbot/faqs/suggested")
async def chatbot_faqs_suggested(limit: int = 50,
                                 user: CurrentUser = Depends(get_current_user)):
    """Moderation queue: cached suggestions awaiting review (auth-gated)."""
    entries = await get_store().list_suggestions(limit)
    return {"suggestions": [e.as_dict() for e in entries]}


@router.post("/api/chatbot/faqs/suggested/{entry_id}/promote")
async def chatbot_faq_promote(entry_id: str,
                              user: CurrentUser = Depends(require_role(settings.AUTH_ADMIN_ROLE))):
    """Promote a suggestion to published — admin-only; requires the grounded re-check."""
    ok, reason = await get_store().promote(entry_id)
    if not ok:
        raise HTTPException(status_code=404 if reason == "not_found" else 422, detail=reason)
    await record_audit(user, "faq.promote", entry_id)
    return {"status": "published", "id": entry_id}


@router.post("/api/chatbot/faqs/suggested/{entry_id}/reject")
async def chatbot_faq_reject(entry_id: str,
                             user: CurrentUser = Depends(require_role(settings.AUTH_ADMIN_ROLE))):
    ok, reason = await get_store().reject(entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail=reason)
    await record_audit(user, "faq.reject", entry_id)
    return {"status": "rejected", "id": entry_id}


@router.get("/api/chatbot/faqs/{faq_id}")
async def chatbot_faq(faq_id: str):
    faq = get_faq(faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ niet gevonden.")
    return faq.as_dict()
