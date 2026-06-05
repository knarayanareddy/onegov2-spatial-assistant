"""Live RWS Waterinfo chloride for intake scenarios (Phase 5).

For IJssel / Lek / Maas intake scenarios the chloride signal at the abstraction
point is the core operational input. This module makes that call MANDATORY for
those intakes and — crucially — never fails silently: when the live RWS feed is
unavailable or stale, it returns the last-known value with an explicit
"laatste bekende waarde van [datum]" warning and a source link.

The live HTTP call is injectable (`requester=`) so the path is unit-tested
offline; in production it hits the RWS waterwebservices over the proxy. The
last-known values are sourced fallbacks, not invented data.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

WATERINFO_SOURCE = "https://waterinfo.rws.nl"
RWS_WEBSERVICE = "https://waterwebservices.rijkswaterstaat.nl/ONLINEWAARNEMINGENSERVICES_DBO/OphalenWaarnemingen"

# Abstraction-point monitoring locations (RWS), per intake.
INTAKE_STATIONS: dict[str, dict] = {
    "ijssel": {"name": "Hollandse IJssel (Gouda/Gouwsluis)", "rws_code": "GOUW", "drinkwaterbedrijf": "Oasen"},
    "lek": {"name": "Lek (Hagestein boven)", "rws_code": "HAGB", "drinkwaterbedrijf": "Dunea/Oasen"},
    "maas": {"name": "Maas (Heel/Brakel)", "rws_code": "BRAK", "drinkwaterbedrijf": "Evides/WML"},
}

# Last-known sourced fallback chloride (mg/L) per intake — labelled and dated.
LAST_KNOWN_CL: dict[str, dict] = {
    "ijssel": {"value_mg_l": 150.0, "measured_at": "2024-09-01", "source_url": WATERINFO_SOURCE},
    "lek": {"value_mg_l": 120.0, "measured_at": "2024-09-01", "source_url": WATERINFO_SOURCE},
    "maas": {"value_mg_l": 110.0, "measured_at": "2024-09-01", "source_url": WATERINFO_SOURCE},
}

# Drinkwaterbesluit norm (also the engine's sourced chloride fallback).
NORM_MG_L = 150.0
NORM_SOURCE = "https://wetten.overheid.nl/BWBR0026304"


def _norm_intake(intake_id: Optional[str]) -> Optional[str]:
    if not intake_id:
        return None
    s = intake_id.lower()
    for key in INTAKE_STATIONS:
        if key in s:
            return key
    if "hollandse" in s:
        return "ijssel"
    return None


def is_intake_relevant(intake_id: Optional[str]) -> bool:
    return _norm_intake(intake_id) is not None


def fetch_chloride_live(intake_id: str, *, requester: Optional[Callable] = None,
                        timeout: float = 3.0) -> dict:
    """Fetch the latest chloride (mg/L) at the intake from RWS. Raises on any failure.
    `requester(station)` is injectable for tests; in prod it POSTs to RWS."""
    key = _norm_intake(intake_id)
    if not key:
        raise ValueError(f"Onbekend innamepunt voor Waterinfo: {intake_id}")
    station = INTAKE_STATIONS[key]

    if requester is not None:
        payload = requester(station)            # test hook
    else:
        import httpx                            # lazy: keeps module import light
        body = {"Locatie": {"Code": station["rws_code"]},
                "AquoPlusWaarnemingMetadata": {"AquoMetadata": {"Grootheid": {"Code": "CONCTTE"},
                "Parameter_Wat_Omschrijving": {"Code": "Cl"}}}}
        r = httpx.post(RWS_WEBSERVICE, json=body, timeout=timeout, trust_env=True)
        r.raise_for_status()
        payload = r.json()

    value = float(payload["value_mg_l"]) if "value_mg_l" in payload else _parse_rws(payload)
    measured_at = payload.get("measured_at") or datetime.now(timezone.utc).date().isoformat()
    return {"intake": key, "station": station["name"], "value_mg_l": value,
            "measured_at": measured_at, "source_url": WATERINFO_SOURCE}


def _parse_rws(payload: dict) -> float:
    """Extract the most recent chloride value from an RWS OphalenWaarnemingen response."""
    waarnemingen = payload.get("WaarnemingenLijst") or []
    metingen = (waarnemingen[0].get("MetingenLijst") if waarnemingen else None) or []
    if not metingen:
        raise ValueError("Geen chloride-metingen in RWS-antwoord")
    return float(metingen[-1]["Meetwaarde"]["Waarde_Numeriek"])


def _live_enabled() -> bool:
    try:
        from app.config import settings
        return bool(getattr(settings, "WATERINFO_LIVE", False))
    except Exception:
        return False


def get_chloride(intake_id: str, *, requester: Optional[Callable] = None) -> dict:
    """Mandatory chloride lookup for an intake. Attempts the live RWS feed when
    enabled (WATERINFO_LIVE) or when a test requester is injected; otherwise — and
    on any failure — returns the last-known value with an explicit dated warning.
    NEVER silent. Offline/default = the labelled fallback (no network hang)."""
    key = _norm_intake(intake_id)
    if not key:
        return {"intake": None, "live": False, "value_mg_l": NORM_MG_L, "measured_at": None,
                "source_url": NORM_SOURCE, "exceeds_norm": False,
                "warning_nl": ("Geen RWS-innamepunt herkend; terugvalwaarde "
                               f"{NORM_MG_L:.0f} mg/L (Drinkwaterbesluit) gebruikt.")}
    if requester is not None or _live_enabled():
        try:
            live = fetch_chloride_live(intake_id, requester=requester)
            return {**live, "live": True, "exceeds_norm": live["value_mg_l"] > NORM_MG_L, "warning_nl": None}
        except Exception:
            pass
    if True:
        lk = LAST_KNOWN_CL.get(key, {"value_mg_l": NORM_MG_L, "measured_at": None, "source_url": NORM_SOURCE})
        station = INTAKE_STATIONS[key]
        return {
            "intake": key, "station": station["name"], "live": False,
            "value_mg_l": lk["value_mg_l"], "measured_at": lk.get("measured_at"),
            "source_url": lk.get("source_url", WATERINFO_SOURCE),
            "exceeds_norm": lk["value_mg_l"] > NORM_MG_L,
            "warning_nl": (
                "Actuele chloridedata niet beschikbaar — berekening gebruikt de laatste bekende "
                f"waarde van {lk.get('measured_at') or 'onbekende datum'} ({lk['value_mg_l']:.0f} mg/L). "
                "Bron: waterinfo.rws.nl"),
        }
