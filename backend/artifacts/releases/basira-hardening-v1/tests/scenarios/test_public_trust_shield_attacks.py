from __future__ import annotations

from basira.api.governed_runtime import (
    PublicGovernedQueryRuntime,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.evidence.publication import (
    GovernedPublicationLedger,
)
from basira.models.quran import (
    QuranVerse,
)
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)
from basira.sources.quran.repository import (
    QuranRepository,
)

QUESTION = (
    "ما معنى الكرسي في قوله تعالى "
    "وسع كرسيه السماوات والأرض؟"
)


def quran_255() -> EvidenceNode:
    return EvidenceNode(
        evidence_id="quran:2:255",
        domain=EvidenceDomain.QURAN,
        text="وسع كرسيه السماوات والأرض",
        source_id="quran:canonical",
        reference="2:255",
    )


class QuranRepoCarrier:
    def __init__(
        self,
        repository: QuranRepository,
    ) -> None:
        self.repository = repository


class AttackRetriever:
    """
    Public-runtime attack harness.

    Keeps the canonical Quran repository required by
    PublicGovernedQueryRuntime, but replaces retrieved
    evidence with attacker-controlled nodes.

    Every selected node is deliberately admitted to the
    publication ledger so these tests cannot succeed merely
    because publication authorization was missing.

    The Trust Shield itself must reject the unsafe evidence.
    """

    def __init__(
        self,
        nodes: tuple[EvidenceNode, ...],
    ) -> None:
        self.repository = QuranRepository(
            (
                QuranVerse(
                    source_id="quran:canonical",
                    surah_number=2,
                    ayah_number=255,
                    text_uthmani=(
                        "اللَّهُ لَا إِلَهَ إِلَّا هُوَ "
                        "وَسِعَ كُرْسِيُّهُ "
                        "السَّمَاوَاتِ وَالْأَرْضَ"
                    ),
                    text_search=(
                        "الله لا اله الا هو "
                        "وسع كرسيه السماوات والارض"
                    ),
                ),
                QuranVerse(
                    source_id="quran:canonical",
                    surah_number=2,
                    ayah_number=43,
                    text_uthmani="وَأَقِيمُوا الصَّلَاةَ",
                    text_search="واقيموا الصلاة",
                ),
            )
        )

        self.retrievers = {
            EvidenceDomain.QURAN: QuranRepoCarrier(
                self.repository
            ),
        }

        self.nodes = nodes

        # Fresh ledger: every scenario explicitly controls
        # what has publication authorization.
        self.publication_authorizer = (
            GovernedPublicationLedger()
        )

    def retrieve(
        self,
        plan,
        *,
        limit_per_domain: int = 10,
    ) -> UnifiedRetrievalResult:
        del limit_per_domain

        requested_domains = {
            target.domain
            for target in plan.targets
        }

        selected = tuple(
            node
            for node in self.nodes
            if node.domain in requested_domains
        )

        # Important:
        # authorize the hostile evidence.
        #
        # Therefore a PASS cannot be explained by the
        # publication ledger simply refusing unknown data.
        for node in selected:
            self.publication_authorizer.admit(node)

        return UnifiedRetrievalResult(
            plan=plan,
            evidence=selected,
            unavailable_domains=frozenset(),
        )


def test_wrong_anchor_only_cannot_satisfy_tafsir_requirement() -> None:
    """
    ATTACK:
    Correct Quran evidence exists, and a trusted-looking
    Tafsir node exists, but that Tafsir belongs to 2:43.

    EXPECTATION:
    The wrong Tafsir must be removed by anchor governance,
    leaving the meaning claim without sufficient support.
    """

    retriever = AttackRetriever(
        (
            quran_255(),
            EvidenceNode(
                evidence_id="tafsir:wrong:2:43",
                domain=EvidenceDomain.TAFSIR,
                text=(
                    "هذا تفسير من مصدر معتبر "
                    "ولكنه متعلق بآية أخرى."
                ),
                source_id="tafsir:trusted",
                reference="2:43",
            ),
        )
    )

    result = PublicGovernedQueryRuntime(
        retriever=retriever,  # type: ignore[arg-type]
        publication_authorizer=(
            retriever.publication_authorizer
        ),
    ).execute(
        question=QUESTION,
    )

    references = {
        node.reference
        for node in result.retrieval.evidence
        if node.reference
    }

    assert "2:43" not in references
    assert not result.answer.has_answer
    assert result.answer.used_evidence_ids == ()


def test_same_anchor_irrelevant_tafsir_cannot_publish() -> None:
    """
    ATTACK:
    The Tafsir node has the CORRECT Quran reference 2:255
    and is publication-authorized, but its actual content
    does not explain the requested phrase.

    EXPECTATION:
    Correct anchor alone must never imply semantic support.
    """

    retriever = AttackRetriever(
        (
            quran_255(),
            EvidenceNode(
                evidence_id="tafsir:irrelevant:2:255",
                domain=EvidenceDomain.TAFSIR,
                text=(
                    "يتحدث هذا المقطع عن أحكام الزكاة "
                    "وإخراج المال للفقراء والمساكين."
                ),
                source_id="tafsir:trusted",
                reference="2:255",
            ),
        )
    )

    result = PublicGovernedQueryRuntime(
        retriever=retriever,  # type: ignore[arg-type]
        publication_authorizer=(
            retriever.publication_authorizer
        ),
    ).execute(
        question=QUESTION,
    )

    assert not result.answer.has_answer
    assert result.answer.used_evidence_ids == ()


def test_quran_text_cannot_impersonate_tafsir_support() -> None:
    """
    SOURCE-ROLE ATTACK.

    This is intentionally stronger than a wrong-anchor test.

    The hostile node:
      - uses the required TAFSIR domain;
      - has the correct 2:255 anchor;
      - contains highly relevant Quran wording;
      - is explicitly publication-authorized;

    BUT its claim_type/source identity say that it is Quran
    text, not Tafsir interpretation.

    EXPECTATION:
    Religious evidence roles are not interchangeable.

    Quran text may ground the verse.
    It may NOT silently satisfy a Tafsir/meaning obligation.
    """

    impersonator = EvidenceNode(
        evidence_id="attack:quran-as-tafsir",
        domain=EvidenceDomain.TAFSIR,
        text="وسع كرسيه السماوات والأرض",
        source_id="quran:canonical",
        reference="2:255",
        claim_type="quran_text",
        related_quran=("2:255",),
    )

    retriever = AttackRetriever(
        (
            quran_255(),
            impersonator,
        )
    )

    result = PublicGovernedQueryRuntime(
        retriever=retriever,  # type: ignore[arg-type]
        publication_authorizer=(
            retriever.publication_authorizer
        ),
    ).execute(
        question=QUESTION,
    )

    assert not result.answer.has_answer
    assert (
        "attack:quran-as-tafsir"
        not in result.answer.used_evidence_ids
    )


def test_valid_tafsir_control_still_passes() -> None:
    """
    CONTROL:
    Tightening the Trust Shield must not destroy valid
    answers.

    The existing hostile retriever contains:
      - canonical Quran 2:255;
      - wrong Tafsir 2:43;
      - valid Tafsir 2:255.

    Basira must reject the hostile candidate while
    preserving the legitimate supported answer.
    """

    retriever = AttackRetriever(
        (
            quran_255(),
            EvidenceNode(
                evidence_id="tafsir:wrong:2:43",
                domain=EvidenceDomain.TAFSIR,
                text=(
                    "مصدر معتبر لكنه يتعلق بآية أخرى."
                ),
                source_id="tafsir:trusted",
                reference="2:43",
            ),
            EvidenceNode(
                evidence_id="tafsir:right:2:255",
                domain=EvidenceDomain.TAFSIR,
                text=(
                    "مقدمة في الآية ثم قوله "
                    "وسع كرسيه السماوات والأرض. "
                    "ثم قال المفسر في معنى كرسيه: "
                    "هذا هو الموضع التفسيري "
                    "المتعلق بالسؤال."
                ),
                source_id="tafsir:trusted",
                reference="2:255",
            ),
        )
    )

    result = PublicGovernedQueryRuntime(
        retriever=retriever,  # type: ignore[arg-type]
        publication_authorizer=(
            retriever.publication_authorizer
        ),
    ).execute(
        question=QUESTION,
    )

    assert result.answer.has_answer
    assert (
        result.answer.semantic_claim_verification
        == "pass"
    )

    assert (
        "tafsir:right:2:255"
        in result.answer.used_evidence_ids
    )

    assert (
        "tafsir:wrong:2:43"
        not in result.answer.used_evidence_ids
    )



def test_untyped_quran_source_cannot_impersonate_tafsir_support() -> None:
    """
    ROLE-OMISSION ATTACK.

    The attacker removes claim_type entirely.

    The node still exposes canonical Quran source identity,
    but declares itself to be Tafsir evidence.

    Omitting the explicit role must not make the evidence
    safer or allow it to satisfy a Tafsir obligation.
    """

    impersonator = EvidenceNode(
        evidence_id="attack:untyped-quran-as-tafsir",
        domain=EvidenceDomain.TAFSIR,
        text="وسع كرسيه السماوات والأرض",
        source_id="quran:canonical",
        reference="2:255",
        claim_type=None,
        related_quran=("2:255",),
    )

    retriever = AttackRetriever(
        (
            quran_255(),
            impersonator,
        )
    )

    result = PublicGovernedQueryRuntime(
        retriever=retriever,  # type: ignore[arg-type]
        publication_authorizer=(
            retriever.publication_authorizer
        ),
    ).execute(
        question=QUESTION,
    )

    assert not result.answer.has_answer

    assert (
        "attack:untyped-quran-as-tafsir"
        not in result.answer.used_evidence_ids
    )



def test_retriever_cannot_mint_its_own_publication_authority() -> None:
    """
    PUBLICATION AUTHORITY FORGERY ATTACK.

    Retrieval and publication authorization must be
    independent capabilities.

    A retriever must not be able to make its own evidence
    publishable merely by attaching and populating its own
    GovernedPublicationLedger.
    """

    hostile = AttackRetriever(
        (
            quran_255(),
            EvidenceNode(
                evidence_id="attack:self-authorized-tafsir",
                domain=EvidenceDomain.TAFSIR,
                text=(
                    "الكرسي هو معنى يقدمه المهاجم "
                    "كتفسير مزيف للآية."
                ),
                source_id="attacker:self-declared",
                reference="2:255",
                claim_type="tafsir_focus",
                related_quran=("2:255",),
            ),
        )
    )

    result = PublicGovernedQueryRuntime(
        retriever=hostile,  # type: ignore[arg-type]
    ).execute(
        question=QUESTION,
    )

    assert not result.answer.has_answer

    assert (
        "attack:self-authorized-tafsir"
        not in result.answer.used_evidence_ids
    )
