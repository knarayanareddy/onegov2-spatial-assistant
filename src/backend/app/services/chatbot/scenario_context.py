"""Turn an already-produced ScenarioCard into retrievable passages so the chat
can EXPLAIN a result (read-only). We never re-run or recompute anything — we
ground over the card's own reasoning_steps / results / official position, cited
by the scenario hash + stable URL.

Defensive by design: the card arrives as a JSON dict (asdict of ScenarioCard,
possibly from the frontend), so every field is accessed with .get() and coerced
to text. A malformed card yields fewer passages, never an exception.
"""
from __future__ import annotations

from typing import Any

from app.services.chatbot.models import Citation, Passage

_VERDICT_NL = {
    "GO": "GO (haalbaar / lage druk)",
    "CAUTION": "CAUTION (let op / matige druk)",
    "STOP": "STOP (hoge druk / niet zonder maatregelen)",
}


def _card_citation(card: dict, locator: str) -> Citation:
    sid = str(card.get("scenario_id", ""))[:8]
    shash = str(card.get("scenario_hash", ""))[:8]
    url = card.get("stable_url") or (f"/api/scenario/{card.get('scenario_id','')}" if card.get("scenario_id") else "/methodology")
    return Citation(
        source_id=f"scenario:{shash or sid}",
        title_nl=f"Scenario {sid} — {card.get('question_nl', 'scenario')}",
        url=url,
        locator=locator,
        kind="scenario",
    )


def passages_from_card(card: dict[str, Any]) -> list[Passage]:
    if not isinstance(card, dict):
        return []
    sid = str(card.get("scenario_id", "card"))[:8] or "card"
    out: list[Passage] = []

    # 1) Headline results / verdict (skip entirely for an empty/meaningless card).
    results = card.get("results", {}) or {}
    if not results and not card.get("question_nl"):
        return out
    verdict = str(results.get("feasibility_class", "")).upper()
    verdict_nl = _VERDICT_NL.get(verdict, verdict or "onbekend")
    res_bits = [f"Eindoordeel: {verdict_nl}."]
    if results.get("score_avg") is not None:
        res_bits.append(f"Gemiddelde DrinkwaterDruk-score: {results.get('score_avg')} (schaal 0–100).")
    if results.get("stop_share") is not None:
        res_bits.append(f"Aandeel STOP-cellen: {results.get('stop_share')}.")
    for k_nl, k in (("cellen", "n_cells"), ("STOP", "n_stop"), ("CAUTION", "n_caution"), ("GO", "n_go")):
        if results.get(k) is not None:
            res_bits.append(f"{k_nl}: {results.get(k)}")
    themes = results.get("themes_used") or []
    if themes:
        res_bits.append(f"Gebruikte themalagen: {', '.join(map(str, themes))}.")
    out.append(Passage(
        id=f"scen:{sid}:results",
        text_nl=f"Resultaat van dit scenario ('{card.get('question_nl','')}'). " + " ".join(res_bits),
        citation=_card_citation(card, "results"),
        tags=["explain_scenario", "scenario"],
    ))

    # 2) Each reasoning step (the navolgbare redeneerketen).
    for step in card.get("reasoning_steps", []) or []:
        if not isinstance(step, dict):
            continue
        nr = step.get("step_nr", "?")
        label = step.get("label_nl", "stap")
        desc = step.get("description_nl", "")
        calc = step.get("calculated_value")
        ds = step.get("datasets_used") or []
        calc_s = f" Berekende waarde: {calc}." if calc else ""
        ds_s = f" Databronnen: {', '.join(map(str, ds))}." if ds else ""
        out.append(Passage(
            id=f"scen:{sid}:step:{nr}",
            text_nl=f"Redeneerstap {nr} — {label}: {desc}{calc_s}{ds_s}",
            citation=_card_citation(card, f"reasoning_step {nr}: {label}"),
            tags=["explain_scenario", "scenario"],
        ))

    # 3) Official position attached to the card.
    op = card.get("official_position")
    if isinstance(op, dict):
        summaries: list[str] = []
        primary = op.get("primary")
        if isinstance(primary, dict) and primary.get("summary_nl"):
            summaries.append(str(primary["summary_nl"]))
        for pos in op.get("positions", []) or []:
            if isinstance(pos, dict) and pos.get("summary_nl"):
                summaries.append(str(pos["summary_nl"]))
        if op.get("disclaimer_nl"):
            summaries.append(str(op["disclaimer_nl"]))
        if summaries:
            out.append(Passage(
                id=f"scen:{sid}:position",
                text_nl="Officieel standpunt bij dit scenario. " + " ".join(dict.fromkeys(summaries)),
                citation=_card_citation(card, "official_position"),
                tags=["explain_scenario", "scenario", "official_position"],
            ))

    # 4) Source registry entries (extra citeable provenance).
    for i, src in enumerate(card.get("source_registry", []) or []):
        if isinstance(src, dict) and (src.get("label") or src.get("title")):
            label = src.get("label") or src.get("title")
            out.append(Passage(
                id=f"scen:{sid}:src:{i}",
                text_nl=f"Bron gebruikt in dit scenario: {label} ({src.get('url','')}).",
                citation=Citation(f"scenario-src:{sid}:{i}", str(label),
                                  src.get("url", "/methodology"), "source_registry", "scenario"),
                tags=["explain_scenario", "scenario"],
            ))

    return out
