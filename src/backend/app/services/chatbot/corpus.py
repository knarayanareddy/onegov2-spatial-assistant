"""Knowledge corpus assembly for the Phase-1 chatbot.

Sources (all already in the repo — no new data needed):
  1. The v3 design document  (docs/onegov2_design_v3_repo_aligned.md) — methodology.
  2. The data dictionary      (data/_llm_metadata_*.json via helpers.tables)   — datasets.
  3. The sourced assumptions  (scenario.{chloride,human_scale,interventions,official_positions}).
  4. First-class data-caveat passages (tagged "data_limits") so the bot surfaces
     the honest limitations instead of overstating the data.

Every passage carries a Citation (http(s) URL for assumptions/positions, a
repo-relative doc path for the design doc/dictionary). The corpus is built once
and cached; pass explicit paths in tests for determinism.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.services.chatbot.models import Citation, Passage

# Repo-relative path used as the design-doc / dictionary citation "url".
DESIGN_DOC_REL = "docs/onegov2_design_v3_repo_aligned.md"
DESIGN_DOC_TITLE = "OneGov #2 ontwerpdocument v3 (repo-aligned)"

_DATA_LIMIT_HINTS = (
    "caveat", "ship empty", "0 rows", "relative density", "headcount",
    "not absolute", "honestly", "assumption", "geen absolute", "proxy",
)


# --------------------------------------------------------------------- helpers
def _find_design_doc(explicit: Optional[str]) -> Optional[Path]:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / DESIGN_DOC_REL
        if cand.is_file():
            return cand
    return None


def _chunk_markdown(md: str, *, max_chars: int = 1800, window: int = 1200) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) chunks at #/##/### boundaries.

    Long sections are windowed so a single huge table/section doesn't dominate
    or dilute retrieval. The heading text is kept inside the body for matching.
    """
    sections: list[tuple[str, str]] = []
    cur_head = "Inleiding"
    cur_lines: list[str] = []

    def flush() -> None:
        body = _clean_md("\n".join(cur_lines))
        if len(body) < 40:
            return
        if len(body) <= max_chars:
            sections.append((cur_head, body))
            return
        # window long bodies on line boundaries
        buf: list[str] = []
        size = 0
        part = 1
        for line in body.splitlines():
            buf.append(line)
            size += len(line) + 1
            if size >= window:
                sections.append((f"{cur_head} (deel {part})", "\n".join(buf).strip()))
                buf, size, part = [], 0, part + 1
        if buf:
            sections.append((f"{cur_head} (deel {part})", "\n".join(buf).strip()))

    for ln in md.splitlines():
        if re.match(r"^#{1,3}\s+", ln):
            flush()
            cur_head = re.sub(r"^#{1,3}\s+", "", ln).strip()
            cur_lines = [ln]
        else:
            cur_lines.append(ln)
    flush()
    return sections


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "x"


def _clean_md(s: str) -> str:
    """Strip markdown noise (heading markers, emphasis, table pipes) so passages
    read cleanly in both the LLM context and the extractive fallback."""
    s = s.replace("**", "").replace("`", "")
    out: list[str] = []
    for line in s.splitlines():
        line = re.sub(r"^\s*#{1,6}\s*", "", line)        # heading markers
        line = re.sub(r"^\s*\|", "", line)               # leading table pipe
        line = re.sub(r"^\s*[-*]\s+", "", line)          # bullet markers
        line = line.replace(" | ", " — ").replace("|", " ")
        out.append(line.rstrip())
    return "\n".join(out).strip()


# --------------------------------------------------------------------- builders
def _design_doc_passages(explicit: Optional[str]) -> list[Passage]:
    path = _find_design_doc(explicit)
    if not path:
        return []
    md = path.read_text(encoding="utf-8")
    out: list[Passage] = []
    for head, body in _chunk_markdown(md):
        low = (head + " " + body).lower()
        tags = ["methodology"]
        if any(h in low for h in _DATA_LIMIT_HINTS):
            tags.append("data_limits")
        out.append(
            Passage(
                id=f"design:{_slug(head)}",
                text_nl=body,
                citation=Citation(
                    source_id=f"design:{_slug(head)}",
                    title_nl=f"{DESIGN_DOC_TITLE} — {head}",
                    url=DESIGN_DOC_REL,
                    locator=head,
                    kind="doc",
                ),
                tags=tags,
            )
        )
    return out


def _dictionary_passages(data_dir: Optional[str]) -> list[Passage]:
    try:
        from app.services.helpers.tables import load_theme_metadata
    except Exception:
        return []
    try:
        meta = load_theme_metadata(Path(data_dir)) if data_dir else load_theme_metadata()
    except Exception:
        return []

    out: list[Passage] = []
    for theme_name, theme in meta.items():
        label = theme.get("label", theme_name)
        url = f"data/_llm_metadata_{theme_name}.json"
        vbv = theme.get("voorbeeldvragen", []) or []
        theme_text = (
            f"Thema '{label}' ({theme_name}) in het datawoordenboek. "
            f"Voorbeeldvragen: {' | '.join(vbv[:4])}"
        )
        out.append(
            Passage(
                id=f"dict:{theme_name}",
                text_nl=theme_text,
                citation=Citation(
                    source_id=f"dict:{theme_name}",
                    title_nl=f"Datawoordenboek — thema {label}",
                    url=url, locator=theme_name, kind="dictionary",
                ),
                tags=["dictionary", "datasets"],
            )
        )
        for tbl in theme.get("data", []) or []:
            tname = tbl.get("naam", "?")
            cols = tbl.get("kolommen", {}) or {}
            col_bits = []
            for cname, cmeta in list(cols.items())[:24]:
                desc = (cmeta.get("beschrijving", "") or "").strip()
                unit = cmeta.get("eenheid")
                unit_s = f", eenheid {unit}" if unit else ""
                col_bits.append(f"{cname} ({cmeta.get('type','?')}{unit_s}): {desc}")
            body = f"Tabel '{tname}' (thema {label}). Kolommen — " + " ; ".join(col_bits)
            out.append(
                Passage(
                    id=f"dict:{theme_name}:{tname}",
                    text_nl=body,
                    citation=Citation(
                        source_id=f"dict:{theme_name}:{tname}",
                        title_nl=f"Datawoordenboek — tabel {tname}",
                        url=url, locator=tname, kind="dictionary",
                    ),
                    tags=["dictionary", "datasets"],
                )
            )
    return out


def _assumption_passages() -> list[Passage]:
    out: list[Passage] = []

    # Human-scale / demand reference (VEWIN).
    try:
        from app.services.scenario.human_scale import (
            VEWIN_HOUSEHOLD_DAY_M3, VEWIN_LABEL, VEWIN_PERSON_DAY_M3, VEWIN_URL,
        )
        out.append(Passage(
            id="assume:vewin_demand",
            text_nl=(
                f"Aanname (bron {VEWIN_LABEL}): drinkwaterverbruik is ongeveer "
                f"{VEWIN_PERSON_DAY_M3} m³ per persoon per dag en ongeveer "
                f"{VEWIN_HOUSEHOLD_DAY_M3} m³ per huishouden per dag. Hiermee rekent het "
                f"model vraag (m³/dag) om naar een menselijke maat (mensen/huishoudens)."
            ),
            citation=Citation("assume:vewin_demand", f"Aanname drinkwatervraag — {VEWIN_LABEL}",
                              VEWIN_URL, "demand_per_person_m3_day", "assumption"),
            tags=["assumptions", "demand", "methodology"],
        ))
    except Exception:
        pass

    # Chloride threshold fallback (Drinkwaterbesluit).
    try:
        from app.services.scenario.chloride import CHLORIDE_FALLBACK
        out.append(Passage(
            id="assume:chloride_threshold",
            text_nl=(
                f"Aanname chloride-drempelwaarde: {CHLORIDE_FALLBACK['source_label']}. "
                f"Terugvalwaarde {CHLORIDE_FALLBACK['value']} mg/L (bandbreedte "
                f"{CHLORIDE_FALLBACK['value_min']}–{CHLORIDE_FALLBACK['value_max']} mg/L). "
                f"Er bestaat géén drempelwaarde per innamepunt in de data; dit is een "
                f"gemotiveerde, instelbare aanname."
            ),
            citation=Citation("assume:chloride_threshold", f"Aanname chloride — {CHLORIDE_FALLBACK['source_label']}",
                              CHLORIDE_FALLBACK["source_url"], "chloride_threshold_mg_l", "assumption"),
            tags=["assumptions", "verzilting", "methodology"],
        ))
    except Exception:
        pass

    # Intervention catalogue.
    try:
        from app.services.scenario.interventions import INTERVENTION_CATALOGUE
        for intv in INTERVENTION_CATALOGUE:
            effect = []
            if intv.get("buffer_volume_m3"):
                effect.append(f"buffervolume {intv['buffer_volume_m3']:,} m³ over een venster van "
                              f"{intv['planning_window_days']} dagen")
            if intv.get("supply_delta_m3_day"):
                effect.append(f"levering +{intv['supply_delta_m3_day']:,} m³/dag")
            if intv.get("demand_delta_fraction"):
                effect.append(f"vraag {int(intv['demand_delta_fraction']*100)}%")
            out.append(Passage(
                id=f"assume:intv:{intv['id']}",
                text_nl=(
                    f"Maatregel '{intv['label_nl']}' (id {intv['id']}): {', '.join(effect)}. "
                    f"Kosten circa €{intv['cost_eur_low']:,}–€{intv['cost_eur_high']:,}, "
                    f"doorlooptijd ~{intv['lead_time_years']} jaar. Bron: {intv['source_label']}."
                ),
                citation=Citation(f"assume:intv:{intv['id']}", f"Maatregel — {intv['label_nl']}",
                                  intv["source_url"], intv["id"], "assumption"),
                tags=["assumptions", "interventions", "methodology"],
            ))
    except Exception:
        pass

    # Official positions.
    try:
        from app.services.scenario.official_positions import DISCLAIMER_NL, OFFICIAL_POSITIONS
        for key, pos in OFFICIAL_POSITIONS.items():
            docs = pos.documents or []
            primary = docs[0] if docs else {"title": "", "url": "/methodology"}
            doc_list = " | ".join(f"{d.get('title','')} ({d.get('url','')})" for d in docs)
            out.append(Passage(
                id=f"position:{key}",
                text_nl=f"Officieel standpunt ({pos.topic}): {pos.summary_nl} Bronnen: {doc_list}",
                citation=Citation(f"position:{key}", f"Officieel standpunt — {pos.topic}",
                                  primary.get("url", "/methodology"), key, "official_position"),
                tags=["official_position", "beleid"],
            ))
        out.append(Passage(
            id="position:disclaimer",
            text_nl=(
                f"Belangrijk voorbehoud: {DISCLAIMER_NL} Een scenario is een beleidsmatige "
                f"verkenning, geen besluit."
            ),
            citation=Citation("position:disclaimer", "Voorbehoud — beleidsmatige verkenning",
                              DESIGN_DOC_REL, "disclaimer", "official_position"),
            tags=["official_position", "data_limits"],
        ))
    except Exception:
        pass

    return out


def _caveat_passages() -> list[Passage]:
    """First-class honest data caveats (tagged data_limits). Grounded in design
    doc Part C ('Caveats the doc must state honestly') and Part H."""
    doc = Citation("design:part-c-caveats", f"{DESIGN_DOC_TITLE} — Part C (caveats)",
                   DESIGN_DOC_REL, "Part C — Caveats", "doc")
    items = [
        ("caveat:verzilting",
         "Beperking verzilting: de kolom verzilting.ZOUT_CONC is in de praktijk één "
         "verzadigde klasse (bijv. '> 200 mg/l'). Daardoor werkt verzilting in het model als "
         "een masker/aanwezigheidssignaal, niet als een fijnmazige meetwaarde. De 'droogte-knop' "
         "(KNMI) versterkt deze bijdrage; dat is eerlijk omdat ZOUT_CONC een verzadigde enkele klasse is.",
         ["data_limits", "verzilting"]),
        ("caveat:cbs",
         "Beperking CBS-data: de CBS-consumptiecijfers zijn gedownsampled/genormaliseerd "
         "(een relatieve dichtheidsproxy, orde ~46k), géén absolute aantallen inwoners (headcounts). "
         "Behandel 'vraag' dus als een relatief bevolkingsdichtheidssignaal, niet als absolute m³.",
         ["data_limits", "cbs", "demand"]),
        ("caveat:empty_tables",
         "Lege datasets: drinkwater_productieketen (h3_id, Bedrijf, Functie, Locatie) en "
         "toestandsbeoordeling_oppervlaktewaterlichamen (KRW-kwaliteitskolommen) worden leeg "
         "geleverd (0 rijen). Het model leunt er niet op en degradeert netjes.",
         ["data_limits", "krw", "productieketen"]),
        ("caveat:no_m3_lookup",
         "Geen operationele m³/dag-tabellen: er is nergens een capaciteit_m3_dag, vraag_m3_dag of "
         "drempelwaarde chloride per innamepunt. Alle m³/dag-getallen zijn gemotiveerde, "
         "instelbare aannames met bron — geen opzoekwaarden uit de data.",
         ["data_limits", "methodology"]),
        ("caveat:cbs_join",
         "CBS-koppeling (latente starter-gap): CBS levert h3_index als 16-tekenige string met "
         "voorloopnul; de starter doet alleen LOWER(), waardoor CBS niet op de 15-tekens H3-lagen "
         "joinde (0 overlap). De engine kanoniseert de sleutel en herstelt 2.145 overlappende cellen.",
         ["data_limits", "cbs"]),
        ("caveat:not_shipped",
         "Niet meegeleverd: KNMI'23-scenario's, live KRW/chloride (Waterinfo RWS) en DINOloket-"
         "grondwater zitten niet in de geleverde data. Teams voegen ze toe onder extra_data/ met een "
         "bijbehorende _llm_metadata_*.json; het model behandelt hun afwezigheid als de aanname-route.",
         ["data_limits"]),
    ]
    return [Passage(id=i, text_nl=t, citation=doc, tags=tags) for (i, t, tags) in items]


def _faq_passages() -> list[Passage]:
    """The curated FAQ answers are clean, vetted B1-Dutch — fold them into the
    retrieval corpus so the bot can return a curated answer when one fits."""
    try:
        from app.services.chatbot.faq import FAQ_REGISTRY
    except Exception:
        return []
    out: list[Passage] = []
    for f in FAQ_REGISTRY:
        cite = f.citations[0] if f.citations else Citation(
            f"faq:{f.id}", "Veelgestelde vraag", DESIGN_DOC_REL, f.id, "doc")
        out.append(Passage(
            id=f"faq:{f.id}",
            text_nl=f"{f.question_nl} {f.answer_nl}",
            citation=cite,
            tags=["faq"] + list(f.tags),
        ))
    return out


# --------------------------------------------------------------------- entry points
def build_corpus(design_doc_path: Optional[str] = None,
                 data_dir: Optional[str] = None) -> list[Passage]:
    """Assemble the full corpus. Each sub-source is guarded so one missing input
    never empties the corpus."""
    passages: list[Passage] = []
    passages.extend(_caveat_passages())          # always available (no I/O)
    passages.extend(_assumption_passages())      # importable offline
    passages.extend(_faq_passages())             # curated, clean answers
    passages.extend(_design_doc_passages(design_doc_path))
    passages.extend(_dictionary_passages(data_dir))
    return passages


@lru_cache(maxsize=1)
def get_default_corpus() -> tuple[Passage, ...]:
    """Cached default corpus (immutable tuple so the lru_cache value is safe)."""
    return tuple(build_corpus())
