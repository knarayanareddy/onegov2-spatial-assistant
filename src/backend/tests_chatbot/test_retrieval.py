"""Retrieval: determinism, Dutch stopwords, compound recall, confidence gate."""
from app.services.chatbot.corpus import build_corpus
from app.services.chatbot.models import Citation, Passage
from app.services.chatbot.retrieval import BM25Retriever
from app.services.chatbot.text import content_tokens


def _full():
    return BM25Retriever(build_corpus())


def test_retrieval_is_deterministic():
    r = _full()
    a = [x.passage.id for x in r.retrieve("verzilting en CBS-vraag")]
    b = [x.passage.id for x in r.retrieve("verzilting en CBS-vraag")]
    assert a == b and a


def test_dutch_stopwords_removed():
    toks = content_tokens("de het een van de drinkwaterzekerheid")
    assert "de" not in toks and "een" not in toks and "van" not in toks
    assert "drinkwaterzekerheid" in toks


def test_compound_recall_matches_parts():
    cite = Citation("t", "Test", "http://example.org")
    ps = [
        Passage("p1", "Schoon drinkwater en leveringszekerheid in de regio.", cite),
        Passage("p2", "Iets heel anders over bodemdaling en wegen.", cite),
    ]
    r = BM25Retriever(ps)
    res = r.retrieve("drinkwaterzekerheid", top_k=2)
    assert res and res[0].passage.id == "p1"  # matched via drinkwater + zekerheid


def test_offtopic_has_low_confidence():
    r = _full()
    q = "Wat is de hoofdstad van Frankrijk?"
    assert r.coverage(q, r.retrieve(q)) < 0.34


def test_ontopic_has_high_confidence():
    r = _full()
    q = "Welke databronnen en verzilting gebruikt het model?"
    assert r.coverage(q, r.retrieve(q)) >= 0.34
