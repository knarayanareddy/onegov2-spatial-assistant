"""MLflow scenario tracing (Phase 5) — closes the Should "navolgbaar" axis.

A guarded span around a scenario run. When MLFLOW_ENABLED is false (the default)
this is a zero-cost no-op and MLflow is never imported, so tests and keyless runs
are unaffected. When enabled, each scenario run becomes a traceable span tagged
with its inputs and resulting verdict — auditable in the MLflow UI alongside the
descriptive flow's traces.
"""
from __future__ import annotations

from contextlib import contextmanager


def _enabled() -> bool:
    try:
        from app.config import settings
        return bool(settings.MLFLOW_ENABLED)
    except Exception:
        return False


@contextmanager
def scenario_span(name: str, **tags):
    """Best-effort MLflow span. Yields the span (or None). Never raises."""
    if not _enabled():
        yield None
        return
    try:
        import mlflow
        with mlflow.start_span(name=name) as span:
            try:
                if span is not None and tags:
                    span.set_attributes({k: str(v) for k, v in tags.items() if v is not None})
            except Exception:
                pass
            yield span
    except Exception:
        yield None


def annotate(span, **attrs) -> None:
    """Set result attributes on a span if tracing is active. Never raises."""
    if span is None:
        return
    try:
        span.set_attributes({k: str(v) for k, v in attrs.items() if v is not None})
    except Exception:
        pass
