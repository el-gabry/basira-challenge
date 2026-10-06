from __future__ import annotations

from basira.evidence.models import (
    EvidenceNode,
)
from basira.evidence.quran_adapter import (
    QuranEvidenceAdapter,
)
from basira.models.source_usage import (
    RuntimeUse,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstanding,
)
from basira.retrieval.retrieval_plan import (
    RetrievalTarget,
)
from basira.sources.quran.repository import (
    QuranRepository,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)

_QUERY_SCAFFOLDING = frozenset(
    {
        "ما",
        "ماذا",
        "معنى",
        "معني",
        "شرح",
        "تفسير",
        "اية",
        "آية",
        "الاية",
        "الآية",
        "سورة",
        "يعني",
        "تعني",
    }
)


def _entity_value(
    understanding: BasiraQueryUnderstanding,
    entity_type: str,
) -> str | None:
    for entity in understanding.entities:
        if entity.entity_type == entity_type:
            return entity.value

    return None


def _search_candidates(
    understanding: BasiraQueryUnderstanding,
) -> tuple[str, ...]:
    values = [
        understanding.query.original_text,
        understanding.query.intent_text,
    ]

    meaningful_tokens = [
        token
        for token in (understanding.query.intent_text.split())
        if token not in _QUERY_SCAFFOLDING
        and not any(character.isdigit() for character in token)
    ]

    if meaningful_tokens:
        values.append(" ".join(meaningful_tokens))

    seen: set[str] = set()
    result = []

    for value in values:
        cleaned = value.strip()

        if not cleaned or cleaned in seen:
            continue

        seen.add(cleaned)
        result.append(cleaned)

    return tuple(result)


def _parse_quran_target_reference(
    value: str,
) -> tuple[int, int] | None:
    parts = value.strip().split(
        ":",
        maxsplit=1,
    )

    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None

    surah = int(parts[0])
    ayah = int(parts[1])

    if surah <= 0 or ayah <= 0:
        return None

    return (
        surah,
        ayah,
    )


class QuranDomainRetriever:
    """
    Deterministic Quran retrieval backed by the
    existing QuranRepository.

    Runtime source authorization is checked before
    Quran evidence leaves the retriever.
    """

    def __init__(
        self,
        *,
        repository: QuranRepository,
        runtime: FailClosedSourceRuntime,
        adapter: QuranEvidenceAdapter | None = None,
    ) -> None:
        self.repository = repository
        self.runtime = runtime

        self.adapter = adapter or QuranEvidenceAdapter()

    def _authorized(
        self,
        source_id: str,
    ) -> bool:
        return self.runtime.allows(
            source_id=source_id,
            runtime_use=(RuntimeUse.RETRIEVE_PASSAGES),
        )

    def retrieve(
        self,
        *,
        understanding: BasiraQueryUnderstanding,
        target: RetrievalTarget,
        limit: int = 10,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        if limit <= 0:
            return ()

        if target.references:
            verses = []

            seen: set[tuple[int, int]] = set()

            for value in target.references:
                reference = _parse_quran_target_reference(value)

                if reference is None:
                    continue

                if reference in seen:
                    continue

                verse = self.repository.get(*reference)

                if verse is None or not self._authorized(verse.source_id):
                    continue

                seen.add(reference)
                verses.append(verse)

                if len(verses) >= limit:
                    break

            return tuple(self.adapter.from_verse(verse) for verse in verses)

        surah_value = _entity_value(
            understanding,
            "surah_number",
        )

        ayah_value = _entity_value(
            understanding,
            "ayah_number",
        )

        if surah_value is not None and ayah_value is not None:
            verse = self.repository.get(
                int(surah_value),
                int(ayah_value),
            )

            if verse is None or not self._authorized(verse.source_id):
                return ()

            return (self.adapter.from_verse(verse),)

        verses = []

        seen: set[tuple[int, int]] = set()

        for candidate in _search_candidates(understanding):
            matches = self.repository.find_exact(candidate)

            if not matches:
                matches = self.repository.find_containing(candidate)

            for verse in matches:
                reference = (
                    verse.surah_number,
                    verse.ayah_number,
                )

                if reference in seen:
                    continue

                if not self._authorized(verse.source_id):
                    continue

                seen.add(reference)
                verses.append(verse)

                if len(verses) >= limit:
                    break

            if len(verses) >= limit:
                break

        return tuple(self.adapter.from_verse(verse) for verse in verses)
