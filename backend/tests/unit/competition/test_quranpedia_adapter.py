from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.quranpedia_adapter import (
    QuranpediaEvidenceAdapter,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalRequest,
    CompetitionSourceUnavailable,
)


def _write_json(
    path: Path,
    value,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _build_fixture(
    root: Path,
) -> Path:
    snapshot = (
        root / "data/competition/normalized/quranpedia/" / "2026-10-04/mushafs-1.json"
    )

    _write_json(
        snapshot,
        {
            "schema": "test",
            "license": {},
            "data": [
                {
                    "surah": {
                        "number": 2,
                        "ayahs": [
                            {
                                "id": 262,
                                "number": 255,
                                "surah": "2",
                                "page_number": 42,
                                "text": ("\ufeffاللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ"),
                                "juz": 3,
                                "number_in_hafs": [255],
                            },
                            {
                                "id": 263,
                                "number": 256,
                                "surah": "2",
                                "page_number": 42,
                                "text": ("\ufeffلَا إِكْرَاهَ فِي الدِّينِ"),
                                "juz": 3,
                                "number_in_hafs": [256],
                            },
                        ],
                    }
                }
            ],
        },
    )

    digest = sha256(snapshot.read_bytes()).hexdigest()

    _write_json(
        root / "data/competition/manifests/quran/" / "quranpedia-hafs-2026-10-04.json",
        {
            "provider": "Quranpedia",
            "provider_release": "2026-10-04",
            "role": "quran",
            "source_id": "quranpedia:mushaf:1",
            "runtime": {
                "eligible": True,
                "status": "ELIGIBLE",
            },
            "snapshot": {
                "path": (
                    "data/competition/normalized/quranpedia/2026-10-04/mushafs-1.json"
                ),
                "record_count": 2,
                "sha256": digest,
            },
        },
    )

    _write_json(
        root / "data/competition/passports/" / "quranpedia-hafs.json",
        {
            "provider": "Quranpedia",
            "role": "quran",
            "source_id": "quranpedia:mushaf:1",
            "runtime": {
                "eligible": True,
            },
            "artifact": {
                "snapshot_sha256": digest,
            },
            "witness": {
                "riwaya": "حفص عن عاصم",
            },
        },
    )

    return snapshot


def test_governed_quranpedia_reference_becomes_evidence(
    tmp_path: Path,
) -> None:
    _build_fixture(tmp_path)

    adapter = QuranpediaEvidenceAdapter(repo_root=tmp_path)

    nodes = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=OfficialDomain.QURAN,
            query="2:255",
        )
    )

    assert len(nodes) == 1

    node = nodes[0]

    assert node.reference == "2:255"
    assert node.source_id == "quranpedia:mushaf:1"
    assert node.claim_type == "quran_text"
    assert node.related_quran == ("2:255",)
    assert node.text.startswith("اللَّهُ لَا إِلَٰهَ")


def test_quranpedia_snapshot_hash_tampering_fails_closed(
    tmp_path: Path,
) -> None:
    snapshot = _build_fixture(tmp_path)

    snapshot.write_text(
        snapshot.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    adapter = QuranpediaEvidenceAdapter(repo_root=tmp_path)

    with pytest.raises(CompetitionSourceUnavailable):
        adapter.retrieve(
            CompetitionRetrievalRequest(
                official_domain=(OfficialDomain.QURAN),
                query="2:255",
            )
        )


def test_quranpedia_non_quran_domain_is_rejected(
    tmp_path: Path,
) -> None:
    _build_fixture(tmp_path)

    adapter = QuranpediaEvidenceAdapter(repo_root=tmp_path)

    from basira.competition.retrieval_bridge import (
        CompetitionAuthorityBoundaryError,
    )

    with pytest.raises(CompetitionAuthorityBoundaryError):
        adapter.retrieve(
            CompetitionRetrievalRequest(
                official_domain=(OfficialDomain.HADITH),
                query="2:255",
            )
        )


def test_quranpedia_is_registered_through_ready_competition_bridge(
    tmp_path: Path,
) -> None:
    _build_fixture(tmp_path)

    from basira.competition.retrieval_adapters import (
        build_ready_competition_adapters,
    )
    from basira.competition.retrieval_bridge import (
        CompetitionRetrievalBridge,
    )

    quran = QuranpediaEvidenceAdapter(repo_root=tmp_path)

    adapters = build_ready_competition_adapters(quran=quran)

    assert adapters.evidence[OfficialDomain.QURAN] is quran

    bridge = CompetitionRetrievalBridge(
        evidence_adapters=adapters.evidence,
        material_adapters=adapters.materials,
    )

    result = bridge.retrieve(
        CompetitionRetrievalRequest(
            official_domain=OfficialDomain.QURAN,
            query="2:255",
        )
    )

    assert result.unavailable is False
    assert len(result.evidence) == 1

    node = result.evidence[0]

    assert node.source_id == "quranpedia:mushaf:1"
    assert node.reference == "2:255"
    assert node.claim_type == "quran_text"
