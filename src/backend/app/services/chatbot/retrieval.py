"""Keyword retrieval over the knowledge corpus — Okapi BM25, pure Python.

Why BM25 and not embeddings: the corpus is small (tens of passages) and we want
keyless, offline, deterministic retrieval. GreenPT *does* expose an OpenAI-style
``/v1/embeddings`` endpoint (verified: returns 401, i.e. it exists and needs a
key), so an embedding-backed retriever is a drop-in upgrade later — but it is not
needed for Phase 1 and would break offline determinism.

Dutch specifics (per the brief):
  - a curated Dutch stopword list (see text.DUTCH_STOPWORDS), and
  - compound splitting so "drinkwaterzekerheid" matches "drinkwater"/"zekerheid".
Both documents and queries are expanded with compound parts.
"""
from __future__ import annotations

import math
from collections import Counter

from app.services.chatbot.models import Passage, RetrievedPassage
from app.services.chatbot.text import (
    COMPOUND_SEED,
    content_tokens,
    expand_tokens,
    raw_tokens,
)

# Below this query-term coverage we decline to answer confidently and ask a
# clarifying question instead (the "no dead ends" rule).
CONFIDENCE_THRESHOLD = 0.34


class BM25Retriever:
    def __init__(self, passages: list[Passage], k1: float = 1.5, b: float = 0.75):
        self.passages = list(passages)
        self.k1 = k1
        self.b = b

        # Build the vocabulary from raw content tokens first; decompounding uses it.
        vocab_counter: Counter[str] = Counter()
        for p in self.passages:
            vocab_counter.update(content_tokens(p.text_nl))
        # Only words long enough to be compound components belong in the split vocab.
        self.vocab: frozenset[str] = frozenset(w for w in vocab_counter if len(w) >= 4)

        self.doc_terms: list[list[str]] = [self._terms(p.text_nl) for p in self.passages]
        self._terms_by_id: dict[str, list[str]] = {
            p.id: terms for p, terms in zip(self.passages, self.doc_terms)
        }
        self.doc_freqs: list[Counter[str]] = [Counter(t) for t in self.doc_terms]
        self.doc_len: list[int] = [len(t) for t in self.doc_terms]
        self.avgdl: float = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0

        # Document frequency + idf.
        df: Counter[str] = Counter()
        for terms in self.doc_terms:
            for term in set(terms):
                df[term] += 1
        n = len(self.passages)
        self.idf: dict[str, float] = {
            term: math.log(1 + (n - dfi + 0.5) / (dfi + 0.5)) for term, dfi in df.items()
        }

    # ------------------------------------------------------------------ internals
    def _terms(self, text: str) -> list[str]:
        return expand_tokens(content_tokens(text), self.vocab)

    def _query_terms(self, query: str) -> list[str]:
        return expand_tokens(content_tokens(query), self.vocab)

    def _score(self, q_terms: list[str], doc_idx: int) -> float:
        freqs = self.doc_freqs[doc_idx]
        dl = self.doc_len[doc_idx]
        score = 0.0
        for term in set(q_terms):
            if term not in freqs:
                continue
            idf = self.idf.get(term, 0.0)
            tf = freqs[term]
            denom = tf + self.k1 * (1 - self.b + self.b * (dl / self.avgdl if self.avgdl else 1))
            score += idf * (tf * (self.k1 + 1)) / denom
        return score

    # ------------------------------------------------------------------ public API
    def retrieve(self, query: str, top_k: int = 6,
                 boost_tags: tuple[str, ...] = (), boost: float = 1.6,
                 boost_kinds: tuple[str, ...] = ()) -> list[RetrievedPassage]:
        """Top-k passages by BM25, with optional tag/kind boosting.

        ``boost_tags`` (e.g. ("data_limits",)) and ``boost_kinds`` (e.g.
        ("scenario",)) multiply the score so caveats / scenario-card passages are
        foregrounded for the matching intent. Ties break on passage id for
        deterministic ordering.
        """
        q_terms = self._query_terms(query)
        scored: list[RetrievedPassage] = []
        for i, p in enumerate(self.passages):
            s = self._score(q_terms, i)
            if boost_tags and any(t in p.tags for t in boost_tags):
                s *= boost
            if boost_kinds and p.citation.kind in boost_kinds:
                s *= boost
            if s > 0:
                scored.append(RetrievedPassage(passage=p, score=s))
        scored.sort(key=lambda rp: (-rp.score, rp.passage.id))
        return scored[:top_k]

    # Unseen query terms (not in the corpus) are, by definition, uninformative
    # for THIS knowledge base, so they carry a small idf floor rather than
    # dominating the confidence denominator.
    IDF_FLOOR = 0.2

    def _idf_for(self, term: str) -> float:
        return self.idf.get(term, self.IDF_FLOOR)

    def coverage(self, query: str, retrieved: list[RetrievedPassage]) -> float:
        """idf-weighted fraction of the query's content-terms found in the
        retrieved set — a transparent, deterministic confidence proxy.

        Weighting by idf means matching a rare domain term (e.g. "verzilting")
        yields high confidence, while leaving generic words (e.g. "leg",
        "meetelt") unmatched barely moves the needle. A query term counts as
        covered if it — or one of its compound parts — appears in the retrieved
        documents.
        """
        q_content = list(dict.fromkeys(content_tokens(query)))
        if not q_content:
            return 0.0
        found_terms: set[str] = set()
        for rp in retrieved:
            found_terms.update(self._terms_by_id.get(rp.passage.id, ()))
        covered_mass, total_mass = 0.0, 0.0
        for t in q_content:
            # Confidence uses a STRICT query-side match: the whole token or its
            # curated-seed compound parts only. Generic vocab decompounding stays
            # in retrieval (recall) but is excluded here so foreign/non-domain
            # words (e.g. "frankrijk") can't be spuriously "covered" by a shared
            # subword. Document terms are still expanded, so a doc-side compound
            # covers a query part.
            candidates = {t} | set(COMPOUND_SEED.get(t, ()))
            weight = max((self._idf_for(c) for c in candidates), default=self.IDF_FLOOR)
            total_mass += weight
            if candidates & found_terms:
                covered_mass += weight
        return covered_mass / total_mass if total_mass else 0.0
