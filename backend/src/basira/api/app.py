from __future__ import annotations

import os

from fastapi import (
    FastAPI,
    HTTPException,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from basira.api.presenter import (
    present_query,
)
from basira.api.schemas import (
    EvidenceDetailResponse,
    QueryRequest,
    QueryResponse,
)
from basira.api.service import (
    BasiraQueryService,
    build_default_query_service,
)


def _cors_origins() -> list[str]:
    configured = os.getenv("BASIRA_CORS_ORIGINS")

    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]

    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def _build_query_service() -> BasiraQueryService:
    return build_default_query_service()


def get_query_service() -> BasiraQueryService:
    try:
        return _build_query_service()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=(f"Basira runtime is not configured: {exc}"),
        ) from exc


app = FastAPI(
    title="Basira Verify API",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_private_network=True,
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "OPTIONS",
    ],
    allow_headers=["*"],
)


@app.get(
    "/api/v1/health",
)
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "basira-verify",
    }


@app.get(
    "/api/v1/evidence/{evidence_id:path}",
    response_model=EvidenceDetailResponse,
)
def evidence_detail(
    evidence_id: str,
) -> EvidenceDetailResponse:
    service = get_query_service()

    passage = service.get_publishable_tafsir(evidence_id)

    if passage is None:
        # Deliberately do not reveal whether an
        # unpublished / unauthorized passage exists.
        raise HTTPException(
            status_code=404,
            detail="Evidence not found.",
        )

    resolved_id = (
        getattr(
            passage,
            "passage_id",
            None,
        )
        or getattr(
            passage,
            "evidence_id",
            evidence_id,
        )
    )

    reference = (
        getattr(
            passage,
            "quran_reference",
            None,
        )
        or getattr(
            passage,
            "reference",
            None,
        )
        or getattr(
            passage,
            "section_title",
            None,
        )
        or getattr(
            passage,
            "chapter_title",
            None,
        )
    )

    return EvidenceDetailResponse(
        evidence_id=resolved_id,
        domain=passage.domain.value,
        source_id=passage.source_id,
        source_version=(
            passage.source_version
        ),
        reference=reference,
        source_url=passage.source_url,
        work_title=passage.work_title,
        author_name=passage.author_name,
        institution=passage.institution,
        publisher=passage.publisher,
        text=passage.text,
    )


@app.post(
    "/api/v1/query",
    response_model=QueryResponse,
)
def query(
    payload: QueryRequest,
) -> QueryResponse:
    service = get_query_service()

    try:
        execution = service.execute(
            question=payload.question,
            quran_reference=(payload.quran_reference),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return present_query(
        execution,
        language=payload.language,
    )
