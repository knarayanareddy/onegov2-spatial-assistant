"""Official government positions — SINGLE SOURCE OF TRUTH.

Fix C5 (+ S4 housing figure). Replaces:
  - §7.9  OFFICIAL_POSITIONS (dataclass instances), key "krw_deadline",
          get_official_position(scenario_type, location)
  - §19.8 OFFICIAL_POSITIONS (plain dicts),       key "krw",
          get_official_position(scenario_type, knmi_preset, involves_housing, involves_krw)

One typed registry, key "krw", one signature returning all relevant
positions + the disclaimer.

S4 FIX: the housing figure is the verified provincial total — 235.460
woningen for Zuid-Holland 2022–2030 (the §19.8 number). The §7.9 "80.000+ in
de Zuidelijke Randstad" conflated scopes; the Zuidelijke Randstad ambition is
~200.000 to 2040. We state one figure per scope with one citation.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OfficialPosition:
    topic: str
    summary_nl: str
    documents: list[dict] = field(default_factory=list)


OFFICIAL_POSITIONS: dict[str, OfficialPosition] = {
    "drinkwater_zh": OfficialPosition(
        topic="drinkwater_zh",
        summary_nl=(
            "De beschikbaarheid van voldoende schoon drinkwater in Zuid-Holland staat onder "
            "druk door groei, klimaat en bronkwaliteit. De provincie werkt met "
            "drinkwaterbedrijven en waterschappen aan een robuuste voorziening tot 2040."
        ),
        documents=[
            {"title": "Regionaal Waterprogramma Zuid-Holland 2022–2027",
             "url": "https://www.pzh.nl/regiovisie-waterprogramma-2022-2027",
             "date": "2022", "publisher": "Provincie Zuid-Holland"},
            {"title": "Nationaal Waterprogramma 2022–2027",
             "url": "https://www.rijksoverheid.nl/onderwerpen/water/nationaal-waterprogramma",
             "date": "2022", "publisher": "Ministerie van Infrastructuur en Waterstaat"},
            {"title": "Ruimtelijk Arrangement Rijk–Zuid-Holland (2 juni 2025)",
             "url": "https://www.rijksoverheid.nl/ruimtelijkarrangement-zh",
             "date": "2025-06-02", "publisher": "Ministerie BZK / Provincie ZH"},
        ],
    ),
    "klimaat_knmi": OfficialPosition(
        topic="klimaat_knmi",
        summary_nl=(
            "KNMI'23 beschrijft vier klimaatscenario's voor Nederland. Scenario Hd (hoge "
            "opwarming, drogere zomers) geeft de grootste druk op zoetwaterbeschikbaarheid."
        ),
        documents=[
            {"title": "KNMI'23 Klimaatscenario's voor Nederland",
             "url": "https://www.knmi.nl/klimaatscenarios",
             "date": "2023", "publisher": "KNMI"},
        ],
    ),
    "woningbouw_zh": OfficialPosition(
        topic="woningbouw_zh",
        # S4 FIX: one consistent, sourced figure with explicit scope.
        summary_nl=(
            "Zuid-Holland heeft een bruto bouwopgave van circa 235.000 woningen in 2022–2030; "
            "in de Zuidelijke Randstad geldt een aparte ambitie van circa 200.000 woningen tot "
            "2040. Beschikbaarheid van drinkwater is benoemd als randvoorwaarde voor "
            "ruimtelijke ontwikkeling."
        ),
        documents=[
            {"title": "Ruimtelijk Arrangement Rijk–Zuid-Holland (2 juni 2025), Onderwerp 9 Drinkwater",
             "url": "https://www.rijksoverheid.nl/ruimtelijkarrangement-zh",
             "date": "2025-06-02", "publisher": "Ministerie BZK / Provincie ZH"},
        ],
    ),
    "krw": OfficialPosition(  # key is "krw" (NOT "krw_deadline")
        topic="krw",
        summary_nl=(
            "De Kaderrichtlijn Water verplicht een goede toestand van waterlichamen; uiterste "
            "deadline 22 december 2027. Voor Zuid-Holland betekent dit extra druk nabij "
            "innamepunten en beschermde waterlichamen."
        ),
        documents=[
            {"title": "Kaderrichtlijn Water — Rijkswaterstaat",
             "url": "https://www.rijkswaterstaat.nl/water/waterbeheer/bescherming-en-gebruik-van-water/drinkwater/kaderrichtlijn-water",
             "date": "2027 deadline", "publisher": "Rijkswaterstaat"},
        ],
    ),
}

DISCLAIMER_NL = (
    "Dit scenario is een beleidsmatige verkenning. Het is geen officieel standpunt van de "
    "Provincie Zuid-Holland of haar partners."
)


def get_official_position(
    scenario_type: str,
    knmi_preset: str = "Hd",
    involves_housing: bool = False,
    involves_krw: bool = False,
) -> dict:
    """Always anchors on drinkwater_zh; adds climate / housing / KRW positions
    when relevant. `scenario_type` is accepted for API symmetry and future use."""
    keys = ["drinkwater_zh"]
    if knmi_preset in ("Hd", "Hn", "Ld", "Ln"):
        keys.append("klimaat_knmi")
    if involves_housing:
        keys.append("woningbouw_zh")
    if involves_krw:
        keys.append("krw")
    positions = [OFFICIAL_POSITIONS[k] for k in keys]
    return {"positions": positions, "primary": positions[0], "disclaimer_nl": DISCLAIMER_NL}
