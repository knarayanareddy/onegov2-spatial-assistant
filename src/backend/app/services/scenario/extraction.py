"""Scenario parameter extraction.

Two paths, one entry point:
  - extract_scenario_params_rule(): deterministic, keyless rule-based extractor
    (mirrors the design doc §10.1 schema). Used for tests and as the fallback.
  - extract_scenario_params_llm():  GreenPT structured extraction via the repo's
    app.services.llm.make_llm (OpenAI-compatible, temperature pinned low).

extract_scenario_params() auto-selects: it uses GreenPT when GREENPT_KEY is
configured, otherwise the rule extractor; and it ALWAYS falls back to the rule
extractor if the LLM call fails. make_llm is imported lazily so this module
stays importable (and tests stay offline) without langchain/GreenPT installed.
"""
from __future__ import annotations

import os
import re
from typing import Callable, Optional

from app.services.scenario.models import ScenarioParams

_KNMI = ("B", "Hd", "Hn", "Ld", "Ln")
_INTAKES = ("ijssel", "lek", "maas", "hollandse ijssel", "nieuwe maas")


# --------------------------------------------------------------------- rule-based
def _knmi(q: str) -> str:
    m = re.search(r"\bknmi\s*([A-Za-z]{1,2})\b", q, re.I)
    if m and m.group(1).capitalize() in _KNMI:
        return m.group(1).capitalize()
    return "Hd"


def _year(q: str) -> int:
    m = re.search(r"\b(20[2-9]\d)\b", q)
    return int(m.group(1)) if m else 2040


def extract_scenario_params_rule(question: str) -> tuple[ScenarioParams, float]:
    """Deterministic extractor. Returns (params, confidence)."""
    q = question.lower()

    intake = next((i for i in _INTAKES if i in q), None)
    outage = re.search(r"(\d+)\s*we?k", q)
    if intake or "inname" in q or "verzilting" in q or "onbruikbaar" in q:
        intake_id = "IJssel"
        if intake:
            intake_id = "IJssel" if "ijssel" in intake else intake.title().replace(" ", "_")
        return (
            ScenarioParams(scenario_type="intake_failure", knmi_preset=_knmi(q),
                           time_horizon=_year(q), intake_id=intake_id,
                           outage_weeks=int(outage.group(1)) if outage else 6),
            0.9,
        )

    mw = re.search(r"(\d+)\s*mw", q)
    units = re.search(r"(\d[\d\.\,]{2,})\s*(?:nieuwe\s+|extra\s+)?(?:woningen|huizen|woning)", q)
    loc = re.search(r"\b(?:bij|in|te|nabij)\s+([A-Z][\w\-]+(?:\s[A-Z][\w\-]+)?)", question)
    dev_type = dev_mw = dev_units = None
    if mw or "datacenter" in q:
        dev_type, dev_mw = "datacenter_50mw", float(mw.group(1)) if mw else 50.0
    elif units or "woningbouw" in q or "woningen" in q:
        dev_type = "housing_5000"
        dev_units = int(units.group(1).replace(".", "").replace(",", "")) if units else 5000
    return (
        ScenarioParams(scenario_type="drop_pin", knmi_preset=_knmi(q), time_horizon=_year(q),
                       location_name=loc.group(1) if loc else None,
                       development_type=dev_type, development_mw=dev_mw, development_units=dev_units),
        0.85 if (dev_type and loc) else 0.6,
    )


# --------------------------------------------------------------------- GreenPT
EXTRACTION_SYSTEM_PROMPT = (
    "Je bent een expert in het extraheren van scenario-parameters uit Nederlandse beleidsvragen "
    "over drinkwaterzekerheid in Zuid-Holland. Bepaal scenario_type (drop_pin, intake_failure, "
    "multi_hazard, intervention), knmi_preset (B/Hd/Hn/Ld/Ln, default Hd), time_horizon (default 2040), "
    "growth_preset (laag/middel/hoog), en waar van toepassing location_name, development_type "
    "(bijv. datacenter_50mw of housing_5000), development_mw, development_units, intake_id, outage_weeks. "
    "Verzin geen waarden; gebruik null als iets niet is af te leiden. Geef een confidence tussen 0 en 1."
)


def _default_llm_factory(model: str):
    from app.services.llm import make_llm  # lazy: avoids langchain import at module load
    return make_llm(model, streaming=False)


def extract_scenario_params_llm(question: str, model: str = "gemma4",
                                llm_factory: Optional[Callable] = None) -> tuple[ScenarioParams, float]:
    """GreenPT structured extraction. Raises on any failure (caller falls back)."""
    from pydantic import BaseModel  # local import keeps the module light

    class _LLMExtraction(BaseModel):
        scenario_type: str = "drop_pin"
        knmi_preset: str = "Hd"
        time_horizon: int = 2040
        growth_preset: str = "middel"
        location_name: Optional[str] = None
        development_type: Optional[str] = None
        development_mw: Optional[float] = None
        development_units: Optional[int] = None
        intake_id: Optional[str] = None
        outage_weeks: Optional[int] = None
        confidence: float = 0.7

    factory = llm_factory or _default_llm_factory
    structured = factory(model).with_structured_output(_LLMExtraction)
    out = structured.invoke([("system", EXTRACTION_SYSTEM_PROMPT), ("user", question)])
    params = ScenarioParams(
        scenario_type=out.scenario_type or "drop_pin",
        knmi_preset=(out.knmi_preset or "Hd"),
        time_horizon=int(out.time_horizon or 2040),
        growth_preset=(out.growth_preset or "middel"),
        location_name=out.location_name,
        development_type=out.development_type,
        development_mw=out.development_mw,
        development_units=out.development_units,
        intake_id=out.intake_id,
        outage_weeks=out.outage_weeks,
    )
    return params, float(out.confidence)


def extract_scenario_params(question: str, use_llm: Optional[bool] = None,
                            llm_factory: Optional[Callable] = None) -> tuple[ScenarioParams, float]:
    """Auto-select GreenPT vs rule-based, always falling back to the rule extractor."""
    want_llm = use_llm if use_llm is not None else bool(os.getenv("GREENPT_KEY"))
    if want_llm:
        try:
            return extract_scenario_params_llm(question, llm_factory=llm_factory)
        except Exception:
            pass  # GreenPT unavailable / errored -> deterministic fallback
    return extract_scenario_params_rule(question)
