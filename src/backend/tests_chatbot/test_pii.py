"""PII anonymisation (Phase 3)."""
from app.services.chatbot.pii import anonymize_pii, contains_pii


def test_postcode_masked():
    out = anonymize_pii("Ik woon op 2611 AB in Delft")
    assert "[postcode]" in out and "2611" not in out


def test_email_masked():
    assert anonymize_pii("mail mij op jan.de.vries@gemeente.nl graag").count("[e-mail]") == 1


def test_phone_masked():
    assert "[telefoon]" in anonymize_pii("bel 0612345678") and "0612345678" not in anonymize_pii("bel 0612345678")


def test_year_is_not_pii():
    assert "2040" in anonymize_pii("hoeveel woningen in 2040?")


def test_contains_pii():
    assert contains_pii("postcode 2611 AB")
    assert not contains_pii("een vraag zonder persoonsgegevens")
