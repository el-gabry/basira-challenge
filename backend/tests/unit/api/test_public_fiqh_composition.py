from basira.api.service import (
    build_public_official_retriever,
)
from basira.evidence.models import (
    EvidenceDomain,
)
from basira.retrieval.official_fiqh_retriever import (
    OfficialFiqhDomainRetriever,
)


def test_public_retriever_has_governed_dorar_fiqh_lane() -> None:
    retriever = (
        build_public_official_retriever()
    )

    fiqh = retriever.retrievers[
        EvidenceDomain.FIQH
    ]

    assert isinstance(
        fiqh,
        OfficialFiqhDomainRetriever,
    )

    assert (
        fiqh.publication_ledger
        is retriever.publication_authorizer
    )
