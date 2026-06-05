"""Dutch text utilities for retrieval: tokenization, stopwords, and compound
splitting (decompounding).

Dutch is heavily compounding ("drinkwaterzekerheid" = drinkwater + zekerheid).
Plain whitespace tokenization tanks recall, so we:
  1. drop a curated Dutch stopword list,
  2. split known/derivable compounds into their parts and index BOTH the whole
     token and its parts (on documents AND queries), so a query for
     "drinkwaterzekerheid" matches a passage that only says "drinkwater" and
     "zekerheid", and vice versa.

No third-party NLP dependency — pure standard library, deterministic.
"""
from __future__ import annotations

import re

# ------------------------------------------------------------------ stopwords
# Curated Dutch stopword list (function words + common question words). Kept
# deliberately conservative so domain terms are never dropped.
DUTCH_STOPWORDS: frozenset[str] = frozenset(
    """
    de het een en of maar want dus als dan toch ook al niet geen wel
    van voor met aan op in uit om bij naar te tot door over onder tussen
    per tegen sinds vanaf binnen buiten zonder via
    ik jij je u hij zij ze wij we jullie men dit dat deze die er hier daar
    mijn jouw uw zijn haar hun ons onze
    is zijn was waren wordt worden werd werden ben bent heb hebt heeft hadden had
    kan kunnen kon konden zal zullen zou zouden moet moeten mag mogen wil willen
    doen doet deed gedaan maken maakt
    wat welke welk wie waar wanneer waarom hoe hoeveel hoezo
    me zich elkaar iets niets alles iemand niemand
    nog meer veel weinig zeer heel erg wat zo te
    een's eens even gewoon graag misschien wellicht ongeveer circa
    """.split()
)

# Critical domain compounds with guaranteed splits (independent of corpus vocab).
COMPOUND_SEED: dict[str, list[str]] = {
    "drinkwaterzekerheid": ["drinkwater", "zekerheid"],
    "drinkwatervoorziening": ["drinkwater", "voorziening"],
    "drinkwaterbedrijven": ["drinkwater", "bedrijven"],
    "drinkwaterbedrijf": ["drinkwater", "bedrijf"],
    "drinkwaterproductie": ["drinkwater", "productie"],
    "drinkwaterinfrastructuur": ["drinkwater", "infrastructuur"],
    "drinkwaterbesluit": ["drinkwater", "besluit"],
    "drinkwaterwet": ["drinkwater", "wet"],
    "grondwater": ["grond", "water"],
    "oppervlaktewater": ["oppervlakte", "water"],
    "oppervlaktewaterlichamen": ["oppervlakte", "water", "lichamen"],
    "zoetwater": ["zoet", "water"],
    "zoetwaterbeschikbaarheid": ["zoet", "water", "beschikbaarheid"],
    "waterbeschikbaarheid": ["water", "beschikbaarheid"],
    "waterkwaliteit": ["water", "kwaliteit"],
    "bronkwaliteit": ["bron", "kwaliteit"],
    "waterprogramma": ["water", "programma"],
    "waterlichamen": ["water", "lichamen"],
    "waterschappen": ["water", "schappen"],
    "klimaatscenario": ["klimaat", "scenario"],
    "klimaatscenarios": ["klimaat", "scenario"],
    "klimaatscenario's": ["klimaat", "scenario"],
    "innamepunt": ["inname", "punt"],
    "innamepunten": ["inname", "punt"],
    "bodemdaling": ["bodem", "daling"],
    "productieketen": ["productie", "keten"],
    "toestandsbeoordeling": ["toestand", "beoordeling"],
    "verziltingsklasse": ["verzilting", "klasse"],
    "bevolkingsgroei": ["bevolking", "groei"],
    "woningbouw": ["woning", "bouw"],
    "datacenter": ["data", "center"],
    "leveringszekerheid": ["levering", "zekerheid"],
}

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?", re.IGNORECASE)


def raw_tokens(text: str) -> list[str]:
    """Lowercase alphanumeric tokens (keeps digits; e.g. '2040', 'h3', '200mg')."""
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def content_tokens(text: str) -> list[str]:
    """Tokens with stopwords and length-1 tokens removed."""
    return [t for t in raw_tokens(text) if len(t) > 1 and t not in DUTCH_STOPWORDS]


def _best_segmentation(s: str, vocab: frozenset[str], min_part: int,
                       memo: dict[str, list[str] | None]) -> list[str] | None:
    """Segment ``s`` into the maximum number of vocab words (>= min_part chars each)."""
    if s == "":
        return []
    if s in memo:
        return memo[s]
    best: list[str] | None = None
    for end in range(min_part, len(s) + 1):
        head = s[:end]
        if head in vocab:
            rest = _best_segmentation(s[end:], vocab, min_part, memo)
            if rest is not None:
                cand = [head] + rest
                if best is None or len(cand) > len(best):
                    best = cand
    memo[s] = best
    return best


def decompound(token: str, vocab: frozenset[str], min_part: int = 4) -> list[str]:
    """Return component parts of a compound token, or [] if it isn't a compound.

    First consult the curated seed map; then attempt a corpus-vocabulary
    segmentation into >= 2 parts. Parts shorter than ``min_part`` are not split.
    """
    if token in COMPOUND_SEED:
        return list(COMPOUND_SEED[token])
    if len(token) < 2 * min_part or not token.isalpha():
        return []
    seg = _best_segmentation(token, vocab, min_part, {})
    if seg and len(seg) >= 2:
        return seg
    return []


def expand_tokens(tokens: list[str], vocab: frozenset[str]) -> list[str]:
    """Each token plus its compound parts (whole token kept for exact matches)."""
    out: list[str] = []
    for t in tokens:
        out.append(t)
        out.extend(decompound(t, vocab))
    return out


def split_sentences_nl(text: str) -> list[str]:
    """Lightweight Dutch sentence splitter for extractive answers."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    # Split on sentence punctuation; keep bullet/line structure reasonable.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [p.strip() for p in parts if p.strip()]
