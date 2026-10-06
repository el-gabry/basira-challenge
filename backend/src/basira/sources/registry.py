from __future__ import annotations

from collections.abc import Iterable

from basira.models.source_manifest import (
    SourceDomain,
    SourceManifest,
)


class DuplicateSourceError(ValueError):
    """Raised when a source ID is already registered."""


class SourceNotFoundError(KeyError):
    """Raised when a requested source is not registered."""


class TrustedSourceRegistry:
    """
    Central registry for governed Basira knowledge sources.

    Registration alone does not make a source trusted for runtime use.
    Runtime consumers should request approved sources through this registry.
    """

    def __init__(
        self,
        manifests: Iterable[SourceManifest] | None = None,
    ) -> None:
        self._sources: dict[str, SourceManifest] = {}

        if manifests is not None:
            for manifest in manifests:
                self.register(manifest)

    def register(
        self,
        manifest: SourceManifest,
    ) -> None:
        """
        Register a source manifest.

        Duplicate source IDs are rejected rather than silently replacing
        an existing trusted source.
        """

        if manifest.source_id in self._sources:
            raise DuplicateSourceError(
                f"Source '{manifest.source_id}' is already registered."
            )

        self._sources[manifest.source_id] = manifest

    def get(
        self,
        source_id: str,
    ) -> SourceManifest | None:
        """Return a registered source, or None if it does not exist."""

        return self._sources.get(source_id)

    def require(
        self,
        source_id: str,
    ) -> SourceManifest:
        """Return a registered source or raise SourceNotFoundError."""

        manifest = self.get(source_id)

        if manifest is None:
            raise SourceNotFoundError(
                f"Source '{source_id}' is not registered."
            )

        return manifest

    def all(
        self,
    ) -> tuple[SourceManifest, ...]:
        """Return all registered source manifests."""

        return tuple(self._sources.values())

    def runtime_approved(
        self,
    ) -> tuple[SourceManifest, ...]:
        """
        Return only sources approved and integrity-verified for runtime use.
        """

        return tuple(
            manifest
            for manifest in self._sources.values()
            if manifest.is_runtime_approved
        )

    def runtime_approved_for_domain(
        self,
        domain: SourceDomain,
    ) -> tuple[SourceManifest, ...]:
        """
        Return runtime-approved sources belonging to a specific domain.
        """

        return tuple(
            manifest
            for manifest in self._sources.values()
            if (
                manifest.domain is domain
                and manifest.is_runtime_approved
            )
        )

    def is_runtime_approved(
        self,
        source_id: str,
    ) -> bool:
        """
        Return whether a registered source may participate in runtime
        verification.
        """

        manifest = self.get(source_id)

        if manifest is None:
            return False

        return manifest.is_runtime_approved

    def __len__(self) -> int:
        return len(self._sources)