from __future__ import annotations

import hashlib
import json
from pathlib import Path

from basira.competition.official_coverage import (
    OfficialDomain,
)


SOURCE_ID = "dawa-center-routing-v1"

PASSPORT_PATH = Path(
    "data/competition/passports/"
    "dawa-center-routing.json"
)


class DawaCenterRoutingAdmissionError(
    RuntimeError
):
    pass


def _load_json(
    path: Path,
) -> dict[str, object]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise (
            DawaCenterRoutingAdmissionError(
                "dawa_center_governance_"
                "artifact_unavailable"
            )
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise (
            DawaCenterRoutingAdmissionError(
                "dawa_center_governance_"
                "artifact_invalid"
            )
        )

    return value


def _sha256(
    path: Path,
) -> str:
    try:
        body = path.read_bytes()
    except OSError as exc:
        raise (
            DawaCenterRoutingAdmissionError(
                "dawa_center_discovery_"
                "artifact_unavailable"
            )
        ) from exc

    return hashlib.sha256(
        body
    ).hexdigest()


class DawaCenterRoutingGate:
    """
    Runtime admission gate for Dawa Center.

    Scope is intentionally narrow:

        Dawa Center
        -> ROUTING_CONTEXT material

    Never:

        Dawa Center
        -> EvidenceNode
        -> religious authority
    """

    def __init__(
        self,
        *,
        repo_root: Path,
    ) -> None:
        self.repo_root = (
            repo_root.resolve()
        )

        self.passport = _load_json(
            self.repo_root
            / PASSPORT_PATH
        )

        self._validate_passport()
        self._validate_discovery_hashes()

    @classmethod
    def from_repo(
        cls,
        repo_root: Path | str,
    ) -> DawaCenterRoutingGate:
        return cls(
            repo_root=Path(
                repo_root
            ),
        )

    def _validate_passport(
        self,
    ) -> None:
        passport = self.passport

        if (
            passport.get("source_id")
            != SOURCE_ID
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_source_"
                    "identity_mismatch"
                )
            )

        if (
            passport.get("status")
            != "ROUTING_ONLY_ADMITTED"
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_not_"
                    "routing_admitted"
                )
            )

        if (
            passport.get(
                "official_locator"
            )
            != "https://dawa.center/"
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_locator_"
                    "mismatch"
                )
            )

        scope = passport.get(
            "admission_scope"
        )

        if not isinstance(
            scope,
            dict,
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_scope_missing"
                )
            )

        if (
            scope.get(
                "official_domain"
            )
            != "dawah_general_content"
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_domain_"
                    "scope_mismatch"
                )
            )

        if (
            scope.get(
                "material_role"
            )
            != "routing_context"
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_role_"
                    "scope_mismatch"
                )
            )

        if (
            scope.get(
                "routing_display_allowed"
            )
            is not True
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_routing_"
                    "display_not_admitted"
                )
            )

        if (
            scope.get(
                "source_native_"
                "answer_content_admitted"
            )
            is not False
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_answer_"
                    "content_illegally_admitted"
                )
            )

        authority = passport.get(
            "authority_boundary"
        )

        if not isinstance(
            authority,
            dict,
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_authority_"
                    "boundary_missing"
                )
            )

        forbidden = (
            "answer_bearing_evidence",
            "universal_primary_evidence",
            "cross_domain_primary_evidence",
            "aqeedah_primary_authority",
            "fiqh_primary_authority",
            "hadith_authentication_authority",
            "tafsir_primary_authority",
            "terminology_authority",
        )

        for key in forbidden:
            if authority.get(key) is not False:
                raise (
                    DawaCenterRoutingAdmissionError(
                        "dawa_center_authority_"
                        f"escalation:{key}"
                    )
                )

        constraints = passport.get(
            "runtime_constraints"
        )

        if not isinstance(
            constraints,
            dict,
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_runtime_"
                    "constraints_missing"
                )
            )

        if (
            constraints.get(
                "evidence_node_creation_allowed"
            )
            is not False
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_evidence_"
                    "creation_illegally_enabled"
                )
            )

        if (
            constraints.get(
                "routing_context_may_"
                "be_displayed"
            )
            is not True
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_routing_"
                    "context_disabled"
                )
            )

        if (
            constraints.get(
                "user_question_may_be_"
                "republished_as_source_text"
            )
            is not False
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_source_"
                    "text_laundering_enabled"
                )
            )

        if (
            constraints.get(
                "content_api_currently_observed"
            )
            is not False
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_content_api_"
                    "claim_mismatch"
                )
            )

        if (
            constraints.get(
                "download_artifact_body_"
                "characterized"
            )
            is not False
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_download_"
                    "body_claim_mismatch"
                )
            )

    def _validate_discovery_hashes(
        self,
    ) -> None:
        frozen = self.passport.get(
            "frozen_discovery"
        )

        if not isinstance(
            frozen,
            dict,
        ) or not frozen:
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_discovery_"
                    "hashes_missing"
                )
            )

        for relative, expected in (
            frozen.items()
        ):
            if (
                not isinstance(
                    relative,
                    str,
                )
                or not isinstance(
                    expected,
                    str,
                )
            ):
                raise (
                    DawaCenterRoutingAdmissionError(
                        "dawa_center_discovery_"
                        "hash_entry_invalid"
                    )
                )

            actual = _sha256(
                self.repo_root
                / relative
            )

            if actual != expected:
                raise (
                    DawaCenterRoutingAdmissionError(
                        "dawa_center_frozen_"
                        "discovery_changed:"
                        + relative
                    )
                )

    def assert_domain(
        self,
        domain: OfficialDomain,
    ) -> None:
        if (
            domain
            is not OfficialDomain
            .DAWAH_GENERAL_CONTENT
        ):
            raise (
                DawaCenterRoutingAdmissionError(
                    "dawa_center_outside_"
                    "admitted_domain"
                )
            )
