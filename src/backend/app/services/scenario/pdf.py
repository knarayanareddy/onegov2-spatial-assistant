"""Citation + PDF export (design doc GAP 3), v3 card shape.

build_citation(): APA-style string + metadata block (dataset versions, git commit,
stable URL). render_scenario_pdf(): a ScenarioCard PDF for an adviesnota.

Unicode-safe: if a Unicode TTF is provided it is used; otherwise text is passed
through an ASCII fallback so the export never crashes (the repo ships no font).
fpdf2 returns bytes from output() — no manual latin-1 encode (fix-pack B1).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from fpdf import FPDF
from fpdf.enums import XPos, YPos

_NX, _NY = XPos.LMARGIN, YPos.NEXT
_ASCII = {"–": "-", "—": "-", "€": "EUR ", "³": "3", "²": "2", "⁻": "-", "≈": "~", "•": "-", "→": "->"}
_VLABEL = {"GO": "HAALBAAR", "CAUTION": "RISICO", "STOP": "NIET HAALBAAR"}


def _safe(s: str) -> str:
    for bad, good in _ASCII.items():
        s = s.replace(bad, good)
    return s


def _type_label(t: str) -> str:
    return {"drop_pin": "Ruimtelijke vraag", "intake_failure": "Inname/verzilting",
            "multi_hazard": "Gecombineerd risico", "intervention": "Interventie"}.get(t, t)


def build_citation(card: dict) -> dict:
    created = card.get("created_at", "")
    try:
        date_nl = datetime.fromisoformat(created).strftime("%-d-%m-%Y %H:%M")
    except Exception:
        date_nl = created
    sid = card.get("scenario_id", "")
    label = f"{_type_label(card.get('scenario_type',''))}, {card.get('params',{}).get('time_horizon','')}"
    apa_nl = (f"Provincie Zuid-Holland Ruimtelijke Assistent. ({date_nl}). "
              f"Scenario: {label} [Scenario-ID: {sid[:8]}]. "
              f"GovTechNL OneGov #2 — Drinkwaterzekerheid. Ophaalbaar via: {card.get('stable_url','')}")
    run_by = card.get("run_by") or {}
    uitgevoerd_door = (run_by.get("name") or run_by.get("oid")) if isinstance(run_by, dict) else None
    metadata = (f"Scenario-ID: {sid}\nScenario-hash: {card.get('scenario_hash','')}\n"
                f"Gegenereerd: {date_nl}\nSoftware: onegov2-spatial-assistant @ {card.get('git_commit','')}")
    if uitgevoerd_door:
        metadata += f"\nUitgevoerd door: {uitgevoerd_door}"
    av = card.get("assumptions_version")
    if av:
        metadata += f"\nAannameversie: {av}"
    vs = card.get("validation_status")
    if vs:
        metadata += f"\nValidatiestatus: {vs}"
    return {"apa_nl": apa_nl, "metadata_block": metadata, "stable_url": card.get("stable_url", ""),
            "scenario_id": sid, "git_commit": card.get("git_commit", ""),
            "uitgevoerd_door": uitgevoerd_door,
            "assumptions_version": av or "", "validation_status": vs or ""}


def render_scenario_pdf(card: dict, font_path: Path | None = None) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    enc: Callable[[str], str]
    if font_path and Path(font_path).exists():
        for st in ("", "B", "I"):
            pdf.add_font("DejaVu", st, str(font_path))
        base = bold = "DejaVu"; enc = lambda x: x  # noqa: E731
    else:
        base, bold, enc = "Helvetica", "Helvetica", _safe

    w = pdf.epw
    results = card.get("results", {})
    fc = results.get("feasibility_class", "")

    pdf.set_font(bold, "B", 16)
    pdf.cell(w, 10, enc("Scenario-uitvoer — Drinkwaterzekerheid ZH"), new_x=_NX, new_y=_NY)
    pdf.set_font(base, "", 10)
    pdf.cell(w, 6, enc(f"Vraag: {card.get('question_nl','')}"), new_x=_NX, new_y=_NY)
    pdf.cell(w, 6, enc(f"Scenario-ID: {card.get('scenario_id','')}"), new_x=_NX, new_y=_NY)
    pdf.ln(3)

    pdf.set_font(bold, "B", 13)
    pdf.cell(w, 8, enc(f"Haalbaarheid: {_VLABEL.get(fc, fc)}"), new_x=_NX, new_y=_NY)
    pdf.set_font(base, "", 10)
    pdf.multi_cell(w, 6, enc(
        f"DrinkwaterDruk: {results.get('score_avg', 0):.0f}/100 over {results.get('n_cells', 0):,} H3-cellen "
        f"({results.get('stop_share', 0) * 100:.0f}% niet-haalbaar-cellen)."), new_x=_NX, new_y=_NY)
    hs = (results.get("human_scale") or {}).get("analogy_nl")
    if hs:
        pdf.multi_cell(w, 6, enc(hs), new_x=_NX, new_y=_NY)
    if results.get("themes_used"):
        pdf.multi_cell(w, 6, enc("Thema's: " + ", ".join(results["themes_used"])), new_x=_NX, new_y=_NY)
    pdf.ln(2)

    pdf.set_font(bold, "B", 11)
    pdf.cell(w, 7, enc("Redeneerproces"), new_x=_NX, new_y=_NY)
    pdf.set_font(base, "", 9)
    for s in card.get("reasoning_steps", []):
        pdf.multi_cell(w, 5, enc(f"{s.get('step_nr','')}. {s.get('label_nl','')}: {s.get('description_nl','')}"),
                       new_x=_NX, new_y=_NY)
    pdf.ln(2)

    ranked = results.get("interventions_ranked", [])
    if ranked:
        pdf.set_font(bold, "B", 11)
        pdf.cell(w, 7, enc("Wat maakt dit haalbaarder?"), new_x=_NX, new_y=_NY)
        pdf.set_font(base, "", 9)
        for i in ranked:
            pdf.multi_cell(w, 5, enc(
                f"- {i.get('label_nl','')}: -> {i.get('new_area_verdict','')} "
                f"(-{i.get('stop_share_reduction_pct',0)}% STOP-cellen) — {i.get('source_label','')}"),
                new_x=_NX, new_y=_NY)
        pdf.ln(2)

    cit = build_citation(card)
    pdf.set_font(bold, "B", 11)
    pdf.cell(w, 7, enc("Citaat"), new_x=_NX, new_y=_NY)
    pdf.set_font(base, "", 9)
    pdf.multi_cell(w, 5, enc(cit["apa_nl"]), new_x=_NX, new_y=_NY)
    pdf.multi_cell(w, 5, enc(cit["metadata_block"]), new_x=_NX, new_y=_NY)
    pdf.ln(2)

    op = card.get("official_position") or {}
    pdf.set_font(base, "I", 8)
    pdf.multi_cell(w, 5, enc(op.get("disclaimer_nl",
                  "Dit scenario is een beleidsmatige verkenning, geen officiële meting of besluit.")),
                   new_x=_NX, new_y=_NY)
    return bytes(pdf.output())
