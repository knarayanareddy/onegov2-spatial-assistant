"""Deterministic scenario hashing — SINGLE SOURCE OF TRUTH.

Fix C2. Replaces two divergent definitions:
  - §18:   compute_scenario_hash(params, assumption_overrides)[:16]
  - §19.2: compute_scenario_hash(params)[:32]   (omitted overrides!)

Decisions:
  - assumption_overrides ARE part of identity (a slider re-run is a
    different scenario and must not collide with the baseline).
  - Recursive normalization: sorted dict keys, lowercased/trimmed strings,
    integral floats collapsed to int (2040.0 == 2040), order-independent lists.
  - SHA-256 truncated to 32 hex chars.

`params` may be a dataclass (ScenarioParams) or a plain dict — duck-typed,
so this module has no repo-internal imports.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def _normalize(obj: Any) -> Any:
    # bool must be checked before int (bool is a subclass of int)
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in sorted(obj.items())}
    if isinstance(obj, (list, tuple)):
        # order-independent (e.g. the interventions list)
        return sorted(
            (_normalize(i) for i in obj),
            key=lambda x: json.dumps(x, sort_keys=True, default=str),
        )
    if isinstance(obj, float):
        r = round(obj, 4)
        return int(r) if r == int(r) else r  # 2040.0 and 2040 hash identically
    if isinstance(obj, str):
        return obj.lower().strip()
    return obj


def compute_scenario_hash(
    params: Any,
    assumption_overrides: dict[str, float] | None = None,
) -> str:
    """Deterministic SHA-256 of normalized params + overrides → 32 hex chars."""
    params_dict = params.__dict__ if hasattr(params, "__dict__") else dict(params)
    payload = {
        "params": _normalize(params_dict),
        "overrides": _normalize(assumption_overrides or {}),
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:32]
