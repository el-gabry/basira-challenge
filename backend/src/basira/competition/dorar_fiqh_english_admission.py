from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

SOURCE_ID = "dorar:fiqh:en"

PROVIDER = "Dorar al-Sunniyyah"

PASSPORT_PATH = Path(
    "data/competition/passports/"
    "dorar-fiqh-en.json"
)

MANIFEST_PATH = Path(
    "data/competition/manifests/fiqh/"
    "dorar-fiqh-en-live-v1.json"
)

AUDIT_PATH = Path(
    "data/competition/audits/fiqh/"
    "dorar-fiqh-en-adversarial-v1.json"
)

ARTICLE_PATH = re.compile(
    r"^/en/feqhia/(\d+)$"
)


class DorarEnglishFiqhAdmissionError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class DorarEnglishFiqhAdmission:
    source_id: str

    provider: str

    canonical_url: str

    article_id: str

    response_sha256: str


def _load(
    path: Path,
) -> dict[str, object]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(value, dict):
        raise DorarEnglishFiqhAdmissionError(
            "english_fiqh_governance_not_object"
        )

    return value


def canonical_english_fiqh_url(
    value: str,
) -> tuple[
    str,
    str,
] | None:
    parsed = urlsplit(value)

    if parsed.scheme != "https":
        return None

    if parsed.hostname != "dorar.net":
        return None

    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return None

    match = ARTICLE_PATH.fullmatch(
        parsed.path.rstrip("/")
    )

    if match is None:
        return None

    article_id = match.group(1)

    return (
        (
            "https://dorar.net/en/feqhia/"
            + article_id
        ),
        article_id,
    )


class DorarEnglishFiqhRuntimeGate:
    def __init__(
        self,
        *,
        repo_root: Path,
    ) -> None:
        self.repo_root = (
            repo_root.resolve()
        )

        self.passport = _load(
            self.repo_root
            / PASSPORT_PATH
        )

        self.manifest = _load(
            self.repo_root
            / MANIFEST_PATH
        )

        self.audit = _load(
            self.repo_root
            / AUDIT_PATH
        )

        self._validate_governance()

    @classmethod
    def from_repo(
        cls,
        repo_root: Path | str,
    ) -> DorarEnglishFiqhRuntimeGate:
        return cls(
            repo_root=Path(repo_root)
        )

    def _validate_governance(
        self,
    ) -> None:
        for artifact in (
            self.passport,
            self.manifest,
            self.audit,
        ):
            if (
                artifact.get("source_id")
                != SOURCE_ID
            ):
                raise (
                    DorarEnglishFiqhAdmissionError(
                        "english_fiqh_source_"
                        "identity_mismatch"
                    )
                )

            if (
                artifact.get("provider")
                != PROVIDER
            ):
                raise (
                    DorarEnglishFiqhAdmissionError(
                        "english_fiqh_provider_"
                        "identity_mismatch"
                    )
                )

        if (
            self.passport.get(
                "official_eligibility"
            )
            != "VERIFIED"
        ):
            raise DorarEnglishFiqhAdmissionError(
                "english_fiqh_not_verified"
            )

        if (
            self.audit.get("status")
            != "PASSED"
        ):
            raise DorarEnglishFiqhAdmissionError(
                "english_fiqh_audit_not_passed"
            )

    def admit(
        self,
        *,
        canonical_url: str,
        body: bytes,
        response_sha256: str,
        content_type: str | None,
    ) -> DorarEnglishFiqhAdmission:
        identity = (
            canonical_english_fiqh_url(
                canonical_url
            )
        )

        if identity is None:
            raise DorarEnglishFiqhAdmissionError(
                "english_fiqh_noncanonical_url"
            )

        if (
            content_type is not None
            and "html"
            not in content_type.casefold()
        ):
            raise DorarEnglishFiqhAdmissionError(
                "english_fiqh_not_html"
            )

        actual = sha256(
            body
        ).hexdigest()

        if actual != response_sha256:
            raise DorarEnglishFiqhAdmissionError(
                "english_fiqh_response_"
                "hash_mismatch"
            )

        canonical, article_id = identity

        return DorarEnglishFiqhAdmission(
            source_id=SOURCE_ID,
            provider=PROVIDER,
            canonical_url=canonical,
            article_id=article_id,
            response_sha256=actual,
        )
