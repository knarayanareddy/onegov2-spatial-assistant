"""Curated Dutch FAQ registry (Phase 1, static).

Hand-written, B1-Dutch, grounded answers with citations — the "veelgestelde
vragen" the UI can show without a model call. Phase 3 will add cached/promoted
user questions on top of this static base; for now these are the vetted answers.

Includes an explicit data-limitations FAQ (per the brief), so reliability is a
first-class, always-available answer.
"""
from __future__ import annotations

from app.services.chatbot.models import Citation, FAQEntry

# Shared citations.
_DESIGN = Citation("design:overview", "OneGov #2 ontwerpdocument v3", "docs/onegov2_design_v3_repo_aligned.md", "Part D", "doc")
_DESIGN_CAVEAT = Citation("design:part-c-caveats", "OneGov #2 ontwerpdocument v3 — Part C (caveats)", "docs/onegov2_design_v3_repo_aligned.md", "Part C — Caveats", "doc")
_VEWIN = Citation("assume:vewin_demand", "VEWIN Waterstatistiek", "https://www.vewin.nl/publicaties/waterstatistiek", "demand_per_person", "assumption")
_KNMI = Citation("position:klimaat_knmi", "KNMI'23 Klimaatscenario's", "https://www.knmi.nl/klimaatscenarios", "klimaat_knmi", "official_position")
_PZH = Citation("position:drinkwater_zh", "Regionaal Waterprogramma Zuid-Holland 2022–2027", "https://www.pzh.nl/regiovisie-waterprogramma-2022-2027", "drinkwater_zh", "official_position")
_KRW = Citation("position:krw", "Kaderrichtlijn Water — Rijkswaterstaat", "https://www.rijkswaterstaat.nl/water/waterbeheer/bescherming-en-gebruik-van-water/drinkwater/kaderrichtlijn-water", "krw", "official_position")
_DICT = Citation("dict:overview", "Datawoordenboek (GET /api/dictionary)", "data/_llm_metadata_drinkwaterzekerheid.json", "dictionary", "dictionary")


FAQ_REGISTRY: list[FAQEntry] = [
    FAQEntry(
        id="wat-is-drinkwaterdruk",
        question_nl="Wat is de DrinkwaterDruk-score?",
        answer_nl=(
            "De DrinkwaterDruk-score is een getal van 0 tot 100 per H3-cel (een zeshoek van ~0,1 km²). "
            "Het is een gewogen som van deelsignalen uit echte kaartlagen — verzilting, overstroming, "
            "beschermingszone (zes-uurszones) en CBS-bevolking — elk gestuurd door aannames met bron. "
            "Hoe hoger de score, hoe groter de druk op de drinkwaterzekerheid."
        ),
        citations=[_DESIGN, _DICT],
        tags=["methodology"],
    ),
    FAQEntry(
        id="go-caution-stop",
        question_nl="Wat betekenen GO, CAUTION en STOP?",
        answer_nl=(
            "Dit is het eindoordeel per cel, afgeleid van de score: GO bij een score onder 33 (lage druk), "
            "CAUTION tussen 33 en 66 (let op), en STOP vanaf 66 (hoge druk). Voor een heel gebied geldt STOP "
            "als meer dan een bepaald aandeel cellen STOP is (standaard 20%). Deze drempels zijn instelbare aannames."
        ),
        citations=[_DESIGN],
        tags=["methodology"],
    ),
    FAQEntry(
        id="welke-databronnen",
        question_nl="Welke databronnen gebruikt het systeem?",
        answer_nl=(
            "Het model combineert echte themalagen op H3-resolutie 9: verzilting (ZOUT_CONC), "
            "overstromingskwetsbaarheid, zes-uurszones drinkwater (bescherming) en CBS-bevolking als vraagproxy. "
            "Alle kolommen staan in het datawoordenboek (GET /api/dictionary). Niet elk getal komt uit de data: "
            "waarden die er niet in staan zijn aannames met een verplichte bron."
        ),
        citations=[_DICT, _DESIGN],
        tags=["datasets"],
    ),
    FAQEntry(
        id="data-beperkingen",
        question_nl="Hoe betrouwbaar zijn de data en wat zijn de beperkingen?",
        answer_nl=(
            "Wees voorzichtig met de cijfers. Verzilting (ZOUT_CONC) is in de praktijk één verzadigde klasse, "
            "dus het werkt als een masker, niet als fijne meetwaarde. CBS-verbruik is een relatieve "
            "dichtheidsproxy (orde ~46k), géén absolute aantallen inwoners. De tabellen "
            "drinkwater_productieketen en toestandsbeoordeling_oppervlaktewaterlichamen zijn leeg (0 rijen). "
            "En er bestaan geen operationele m³/dag-tabellen: alle m³/dag-getallen zijn aannames met bron, geen opzoekwaarden."
        ),
        citations=[_DESIGN_CAVEAT],
        tags=["data_limits"],
    ),
    FAQEntry(
        id="wat-is-verzilting",
        question_nl="Wat is verzilting en hoe wordt het gemeten?",
        answer_nl=(
            "Verzilting is het zouter worden van water, wat de drinkwaterwinning bemoeilijkt. In de data zit het "
            "als de klasse verzilting.ZOUT_CONC (bijvoorbeeld '> 200 mg/l'). Omdat dit één verzadigde klasse is, "
            "gebruikt het model het als aanwezigheidssignaal; de KNMI-droogteknop versterkt de bijdrage. "
            "De chloride-drempelwaarde is een aanname (terugval 150 mg/L, bandbreedte 150–250) op basis van het Drinkwaterbesluit."
        ),
        citations=[_DESIGN_CAVEAT, Citation("assume:chloride_threshold", "Drinkwaterbesluit", "https://wetten.overheid.nl/BWBR0026304", "chloride", "assumption")],
        tags=["data_limits", "verzilting"],
    ),
    FAQEntry(
        id="knmi-presets",
        question_nl="Wat zijn de KNMI-presets (B, Hd, Hn, Ld, Ln)?",
        answer_nl=(
            "Dit zijn de KNMI'23-klimaatscenario's. De letters staan voor de mate van opwarming en het neerslagpatroon. "
            "Scenario Hd (hoge opwarming, drogere zomers) geeft de grootste druk op de zoetwaterbeschikbaarheid en is de standaard. "
            "In het model verhoogt een droger scenario de droogte-vermenigvuldiger en daarmee de verziltingsbijdrage."
        ),
        citations=[_KNMI, _DESIGN],
        tags=["methodology"],
    ),
    FAQEntry(
        id="hoe-werkt-scenario",
        question_nl="Hoe werkt een scenario en welke aannames zitten erin?",
        answer_nl=(
            "Een scenario kiest een gebied (H3-cellen), berekent per cel de DrinkwaterDruk-score uit de kaartlagen, "
            "gestuurd door aannames, en aggregeert naar GO/CAUTION/STOP. Belangrijke 'knoppen' (aannames met bron) zijn: "
            "het KNMI-scenario, bevolkingsgroei, verbruik per persoon (VEWIN ~0,119 m³/dag), de weging van de deelsignalen "
            "en de verdict-drempels. Elk scenario krijgt een hash voor reproduceerbaarheid en een navolgbare redeneerketen."
        ),
        citations=[_DESIGN, _VEWIN],
        tags=["methodology"],
    ),
    FAQEntry(
        id="lege-datasets",
        question_nl="Welke datasets zijn leeg of ontbreken?",
        answer_nl=(
            "drinkwater_productieketen en toestandsbeoordeling_oppervlaktewaterlichamen worden leeg geleverd (0 rijen); "
            "het model leunt er niet op. Daarnaast zitten KNMI'23-scenario's, live KRW/chloride (Waterinfo) en "
            "DINOloket-grondwater niet in de geleverde data — teams voegen die optioneel toe onder extra_data/. "
            "Hun afwezigheid valt terug op de aanname-route, nooit stilzwijgend."
        ),
        citations=[_DESIGN_CAVEAT, _KRW],
        tags=["data_limits"],
    ),
    FAQEntry(
        id="officieel-standpunt",
        question_nl="Is een scenario een officieel standpunt van de provincie?",
        answer_nl=(
            "Nee. Een scenario is een beleidsmatige verkenning en geen officieel standpunt van de Provincie Zuid-Holland "
            "of haar partners. Het verbindt de uitkomst wel aan relevante officiële documenten (zoals het Regionaal "
            "Waterprogramma en KNMI'23), zodat je de context kunt nalezen."
        ),
        citations=[_PZH, _KNMI],
        tags=["beleid"],
    ),
    FAQEntry(
        id="reproduceerbaar",
        question_nl="Hoe weet ik dat een resultaat reproduceerbaar en navolgbaar is?",
        answer_nl=(
            "Elk scenario krijgt een scenario-hash (32 tekens) die de parameters én de aanname-overrides vastlegt, plus een "
            "stabiele URL. De rekenstappen zijn deterministisch; GreenPT wordt alleen op temperatuur 0 gebruikt om parameters "
            "te lezen en tekst te schrijven. De redeneerketen is zichtbaar in het Insight-paneel en wordt in MLflow vastgelegd."
        ),
        citations=[_DESIGN],
        tags=["methodology"],
    ),
]

_BY_ID = {f.id: f for f in FAQ_REGISTRY}


def list_faqs() -> list[FAQEntry]:
    return list(FAQ_REGISTRY)


def get_faq(faq_id: str) -> FAQEntry | None:
    return _BY_ID.get(faq_id)
