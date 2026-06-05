"""Corpus: core sources present, caveats first-class, every passage cited."""
from app.services.chatbot.corpus import build_corpus


def test_corpus_has_core_sources():
    c = build_corpus()
    kinds = {p.citation.kind for p in c}
    assert {"doc", "dictionary", "assumption", "official_position"} <= kinds
    assert len(c) >= 50


def test_caveats_are_first_class_and_tagged():
    cav = [p for p in build_corpus() if "data_limits" in p.tags]
    assert cav, "no data_limits-tagged passages"
    text = " ".join(p.text_nl.lower() for p in cav)
    # verzilting saturated-class caveat
    assert "zout_conc" in text and ("verzadig" in text or "masker" in text)
    # CBS relative-density proxy (not headcounts)
    assert ("relatieve dichtheid" in text or "dichtheidsproxy" in text or "headcount" in text)
    # empty tables
    assert "leeg" in text and "productieketen" in text


def test_every_passage_is_cited():
    for p in build_corpus():
        assert p.citation.source_id and p.citation.title_nl
        # external sources must carry an http(s) URL (the source-gate discipline)
        if p.citation.kind in ("assumption", "official_position") and p.id != "position:disclaimer":
            assert p.citation.url.startswith("http"), f"{p.id} missing http source"
