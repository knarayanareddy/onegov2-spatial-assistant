"""PII anonymisation for the FAQ cache (Phase 3).

Before a user's question is stored, strip personal data so the cache can't leak
it. Conservative, deterministic regexes — no external NLP. Covered today:
  - Dutch postcodes (1234 AB / 1234AB)
  - e-mail addresses
  - phone numbers (NL-style: +31 or leading 0, 9 following digits)

Add more categories (house numbers, names) later if your policy requires it.
"""
from __future__ import annotations

import re

# 1234 AB — first digit 1-9, then 3 digits, optional space, two letters.
_POSTCODE = re.compile(r"\b[1-9][0-9]{3}\s?[A-Za-z]{2}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# +31 or a leading 0, then 8-9 more digits with optional spaces/dashes.
_PHONE = re.compile(r"(?<!\d)(?:\+31|0)(?:[\s-]?\d){8,9}(?!\d)")


def anonymize_pii(text: str) -> str:
    """Return ``text`` with postcodes, e-mail and phone numbers masked."""
    if not text:
        return text
    out = _EMAIL.sub("[e-mail]", text)
    out = _POSTCODE.sub("[postcode]", out)
    out = _PHONE.sub("[telefoon]", out)
    return out


def contains_pii(text: str) -> bool:
    if not text:
        return False
    return bool(_EMAIL.search(text) or _POSTCODE.search(text) or _PHONE.search(text))
