from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse

from basira.competition.dorar_fiqh_source import (
    DorarFiqhSourceDocument,
)
from basira.competition.fiqh_policy import (
    FiqhSourceEligibility,
    FiqhSourceFamily,
)

PASSPORT_PATH = Path(
    "data/competition/passports/dorar-fiqh.json"
)

MANIFEST_PATH = Path(
    "data/competition/manifests/fiqh/"
    "dorar-fiqh-live-v1.json"
)

AUDIT_PATH = Path(
    "data/competition/audits/fiqh/"
    "dorar-fiqh-adversarial-v1.json"
)

DORAR_FIQH_SOURCE_ID = "dorar:fiqh"

_ARTICLE_PATH = re.compile(
    r"^/feqhia/\d+(?:/.*)?$"
)


class DorarFiqhAdmissionError(
    ValueError
):
    """Dorar Fiqh failed governed runtime admission."""


@dataclass(
    frozen=True,
    slots=True,
)
class DorarFiqhRuntimeAdmission:
    source_id: str

    source_family: FiqhSourceFamily

    provider: str

    runtime_eligibility: (
        FiqhSourceEligibility
    )

    canonical_url: str

    response_sha256: str


def _load_json(
    path: Path,
) -> dict[str, object]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise DorarFiqhAdmissionError(
            f"cannot_load_governance_artifact:{path}"
        ) from exc

    if not isinstance(value, dict):
        raise DorarFiqhAdmissionError(
            f"governance_artifact_not_object:{path}"
        )

    return value


class DorarFiqhRuntimeGate:
    """
    Technical runtime admission for the competition-
    allowed Dorar Fiqh source.

    Competition authority already allows:
        dorar.net/feqhia

    This gate does NOT choose religious authority.
    It proves that the runtime document is actually
    the governed Dorar Fiqh source whose source
    structure passed Basira's adversarial audit.
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

        self.manifest = _load_json(
            self.repo_root
            / MANIFEST_PATH
        )

        self.audit = _load_json(
            self.repo_root
            / AUDIT_PATH
        )

        self._validate_governance()

    @classmethod
    def from_repo(
        cls,
        repo_root: Path | str,
    ) -> DorarFiqhRuntimeGate:
        return cls(
            repo_root=Path(repo_root)
        )

    def _validate_governance(
        self,
    ) -> None:
        if (
            self.passport.get("source_id")
            != DORAR_FIQH_SOURCE_ID
        ):
            raise DorarFiqhAdmissionError(
                "fiqh_passport_source_identity_mismatch"
            )

        if (
            self.manifest.get("source_id")
            != DORAR_FIQH_SOURCE_ID
        ):
            raise DorarFiqhAdmissionError(
                "fiqh_manifest_source_identity_mismatch"
            )

        if (
            self.audit.get("source_family")
            != "DORAR_FIQH"
        ):
            raise DorarFiqhAdmissionError(
                "fiqh_audit_source_family_mismatch"
            )

        if (
            self.audit.get("provider")
            != "Dorar al-Sunniyyah"
        ):
            raise DorarFiqhAdmissionError(
                "fiqh_audit_provider_mismatch"
            )

        if self.audit.get("result") != "PASS":
            raise DorarFiqhAdmissionError(
                "fiqh_adversarial_audit_not_passed"
            )

        failures = self.audit.get(
            "failures"
        )

        if failures not in (
            [],
            (),
        ):
            raise DorarFiqhAdmissionError(
                "fiqh_adversarial_failures_present"
            )

        checks = self.audit.get(
            "checks"
        )

        if not isinstance(
            checks,
            dict,
        ):
            raise DorarFiqhAdmissionError(
                "fiqh_audit_checks_missing"
            )

        required = {
            "canonical_article_capture":
                "PASS",
            "disagreement_preserved":
                "PASS",
            "automated_tarjih":
                "PROHIBITED",
            "majority_vote":
                "PROHIBITED",
            "personal_fatwa":
                "PROHIBITED",
            (
                "consensus_inference_"
                "from_madhhab_count"
            ):
                "PROHIBITED",
        }

        for key, expected in (
            required.items()
        ):
            if checks.get(key) != expected:
                raise DorarFiqhAdmissionError(
                    "fiqh_audit_invariant_failed:"
                    f"{key}"
                )

        # Historical audit stopped here waiting for
        # source-passport verification. This runtime
        # gate performs that missing verification.
        state = self.audit.get(
            "runtime_admission"
        )

        if state not in {
            "PENDING_SOURCE_PASSPORT",
            "ADMITTED",
        }:
            raise DorarFiqhAdmissionError(
                "unexpected_fiqh_runtime_admission_state"
            )

    def admit(
        self,
        document: DorarFiqhSourceDocument,
    ) -> DorarFiqhRuntimeAdmission:
        parsed = urlparse(
            document.canonical_url
        )

        if (
            parsed.scheme != "https"
            or parsed.hostname != "dorar.net"
            or not _ARTICLE_PATH.match(
                parsed.path
            )
        ):
            raise DorarFiqhAdmissionError(
                "non_canonical_dorar_fiqh_document"
            )

        content_type = (
            document.content_type
            or ""
        ).lower()

        if not content_type.startswith(
            "text/html"
        ):
            raise DorarFiqhAdmissionError(
                "dorar_fiqh_document_not_html"
            )

        digest = (
            document.response_sha256
            or ""
        ).strip()

        if not digest:
            raise DorarFiqhAdmissionError(
                "dorar_fiqh_response_hash_missing"
            )

        body = document.body

        body_bytes = (
            body
            if isinstance(body, bytes)
            else str(body).encode("utf-8")
        )

        actual_digest = (
            sha256(body_bytes)
            .hexdigest()
        )

        if actual_digest != digest:
            raise DorarFiqhAdmissionError(
                "dorar_fiqh_response_hash_mismatch"
            )

        return DorarFiqhRuntimeAdmission(
            source_id=DORAR_FIQH_SOURCE_ID,
            source_family=(
                FiqhSourceFamily.DORAR_FIQH
            ),
            provider=(
                "Dorar al-Sunniyyah"
            ),
            runtime_eligibility=(
                FiqhSourceEligibility.ELIGIBLE
            ),
            canonical_url=(
                document.canonical_url
            ),
            response_sha256=digest,
        )
