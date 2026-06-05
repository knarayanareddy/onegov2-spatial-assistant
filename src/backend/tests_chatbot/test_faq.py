"""Curated FAQ registry."""
from app.services.chatbot.faq import get_faq, list_faqs


def test_registry_nonempty_and_cited():
    faqs = list_faqs()
    assert len(faqs) >= 8
    for f in faqs:
        assert f.question_nl and f.answer_nl and f.citations
        assert f.id


def test_has_data_limitations_faq():
    assert any("data_limits" in f.tags for f in list_faqs())
    f = get_faq("data-beperkingen")
    assert f is not None
    low = f.answer_nl.lower()
    assert "proxy" in low or "leeg" in low or "verzadig" in low


def test_get_faq_lookup():
    assert get_faq("go-caution-stop") is not None
    assert get_faq("does-not-exist") is None
