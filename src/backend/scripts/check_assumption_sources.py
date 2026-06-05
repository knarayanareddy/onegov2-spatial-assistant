"""CI gate (design doc §7.2 / §26): every assumption / intervention / official
document / human-scale conversion MUST carry a non-empty http(s) source_url.
Blocks the build on empty or non-URL sources. Run: PYTHONPATH=. python scripts/check_assumption_sources.py
"""
import sys

from app.services.scenario.chloride import CHLORIDE_FALLBACK
from app.services.scenario.human_scale import VEWIN_URL
from app.services.scenario.interventions import INTERVENTION_CATALOGUE
from app.services.scenario.official_positions import OFFICIAL_POSITIONS


def _ok(u) -> bool:
    return isinstance(u, str) and u.strip().startswith("http")


def main() -> int:
    errors: list[str] = []
    for i in INTERVENTION_CATALOGUE:
        if not _ok(i.get("source_url")):
            errors.append(f"intervention '{i.get('id')}' has empty/invalid source_url")
    for key, pos in OFFICIAL_POSITIONS.items():
        for doc in pos.documents:
            if not _ok(doc.get("url")):
                errors.append(f"official_position '{key}' document '{doc.get('title')}' has empty/invalid url")
    if not _ok(CHLORIDE_FALLBACK.get("source_url")):
        errors.append("chloride fallback assumption has empty/invalid source_url")
    if not _ok(VEWIN_URL):
        errors.append("human_scale VEWIN_URL is empty/invalid")

    if errors:
        print("ASSUMPTION SOURCE GATE: FAILED")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("ASSUMPTION SOURCE GATE: PASSED — every source is a non-empty http(s) URL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
