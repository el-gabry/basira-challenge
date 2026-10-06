from __future__ import annotations

import hashlib

from basira.models.scholarly import ScholarlyPassage
from basira.retrieval.shamela_fts import (
    ShamelaFtsIndex,
)
from basira.retrieval.shamela_scout import (
    ShamelaSearchHit,
    ShamelaSearchTask,
)
from basira.sources.shamela.contracts import (
    ShamelaPassageIdentity,
)


class ShamelaFtsBackend:
    """
    Persistent governed-search backend for the
    bounded Shamela Evidence Scout.

    Responsibilities:
    - execute deterministic FTS retrieval;
    - honor structural domain/madhhab filters;
    - validate returned passage provenance;
    - convert retrieval results into the Scout's
      existing ShamelaSearchHit contract.

    Non-responsibilities:
    - religious judgment;
    - semantic entailment;
    - deciding the preferred madhhab;
    - declaring corpus-wide absence.

    The current corpus is intentionally partial,
    therefore attests_complete_absence is always
    False.
    """

    def __init__(
        self,
        index: ShamelaFtsIndex,
        *,
        expected_index_fingerprint: (str | None) = None,
        expected_corpus_fingerprint: (str | None) = None,
    ) -> None:
        self.index = index

        stats = index.stats

        if (
            expected_index_fingerprint is not None
            and stats.index_fingerprint != expected_index_fingerprint
        ):
            raise ValueError(
                "Shamela FTS index fingerprint does not match expected value"
            )

        if (
            expected_corpus_fingerprint is not None
            and stats.corpus_fingerprint != expected_corpus_fingerprint
        ):
            raise ValueError(
                "Shamela FTS corpus fingerprint does not match expected value"
            )

    @property
    def is_available(
        self,
    ) -> bool:
        return True

    @property
    def attests_complete_absence(
        self,
    ) -> bool:
        # A selected-book corpus must never be used
        # to infer that no scholarly position exists.
        return False

    def search(
        self,
        task: ShamelaSearchTask,
        *,
        limit: int = 10,
    ) -> tuple[
        ShamelaSearchHit,
        ...,
    ]:
        if limit <= 0:
            return ()

        candidate_limit = max(
            limit * 8,
            40,
        )

        # A bound policy with an empty primary allowlist
        # means "allow none", not "search everything".
        if (
            task.policy_fingerprint is not None
            and not task.allowed_work_ids
        ):
            return ()

        fts_hits = self.index.search(
            task.query,
            limit=candidate_limit,
            domains=tuple(task.domains),
            madhhabs=tuple(task.requested_madhhabs),
            excluded_madhhabs=tuple(task.excluded_madhhabs),
            book_ids=tuple(task.allowed_work_ids),
        )

        collected: list[ShamelaSearchHit] = []

        seen: set[str] = set()

        for fts_hit in fts_hits:
            passage = fts_hit.passage

            self._require_valid_passage(passage)

            identity = ShamelaPassageIdentity.from_passage(passage)

            evidence_id = passage.passage_id

            if evidence_id in seen:
                continue

            seen.add(evidence_id)

            collected.append(
                ShamelaSearchHit(
                    passage=passage,
                    identity=identity,
                    score=fts_hit.score,
                    parent_context=(identity.parent_text),
                )
            )

        collected.sort(
            key=lambda hit: (
                -hit.score,
                hit.identity.book_id,
                hit.identity.page_id,
            )
        )

        return tuple(collected[:limit])

    @staticmethod
    def _require_valid_passage(
        passage: ScholarlyPassage,
    ) -> None:
        """
        Fail closed if the derivative SQLite index
        no longer matches the governed evidence
        identity stored in the passage metadata.
        """

        metadata = passage.metadata

        if metadata.get("physical_source") != "shamela":
            raise ValueError("FTS passage is not marked as Shamela source material")

        evidence_span_id = metadata.get("evidence_span_id")

        if evidence_span_id != passage.passage_id:
            raise ValueError("FTS passage ID does not match governed evidence span ID")

        book_id = metadata.get("shamela_book_id")

        if (
            passage.work_id is None
            or book_id is None
            or str(passage.work_id) != str(book_id)
        ):
            raise ValueError("FTS passage book identity is inconsistent")

        expected_text_hash = metadata.get("raw_text_sha256")

        if (
            not isinstance(
                expected_text_hash,
                str,
            )
            or len(expected_text_hash) != 64
        ):
            raise ValueError("FTS passage is missing governed raw-text SHA-256")

        actual_text_hash = hashlib.sha256(passage.text.encode("utf-8")).hexdigest()

        if actual_text_hash != expected_text_hash:
            raise ValueError("FTS passage text hash does not match governed evidence")

        # This validates the remaining structural
        # identity contract, including snapshot hash.
        ShamelaPassageIdentity.from_passage(passage)
