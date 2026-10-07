from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
)

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)

_VISITOR_PATTERN = re.compile(
    r"^[A-Za-z0-9_-]{16,128}$"
)

_INIT_LOCK = threading.Lock()
_INITIALIZED_PATHS: set[str] = set()

MAX_HISTORY_PER_VISITOR = 50


class ChatHistoryCreate(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )
    language: Literal["ar", "en"]
    response: dict[str, Any]


class ChatHistoryEntry(BaseModel):
    id: str
    question: str
    language: Literal["ar", "en"]
    response: dict[str, Any]
    created_at: str


class ChatHistoryResponse(BaseModel):
    items: list[ChatHistoryEntry]


def _database_path() -> Path:
    configured = os.getenv(
        "BASIRA_CHAT_DB_PATH"
    )

    if configured:
        return Path(
            configured
        ).expanduser().resolve()

    return (
        PROJECT_ROOT
        / "data"
        / "runtime"
        / "basira-chat.sqlite3"
    )


def _validate_visitor_id(
    value: str,
) -> str:
    visitor_id = value.strip()

    if not _VISITOR_PATTERN.fullmatch(
        visitor_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid visitor identifier.",
        )

    return visitor_id


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        path,
        timeout=5.0,
    )

    connection.row_factory = (
        sqlite3.Row
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        "PRAGMA busy_timeout = 5000"
    )

    return connection


def _ensure_database() -> None:
    path = str(
        _database_path()
    )

    if path in _INITIALIZED_PATHS:
        return

    with _INIT_LOCK:
        if path in _INITIALIZED_PATHS:
            return

        with _connect() as connection:
            connection.execute(
                "PRAGMA journal_mode = WAL"
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                chat_history (
                    id TEXT PRIMARY KEY,
                    visitor_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    language TEXT NOT NULL
                        CHECK (
                            language IN (
                                'ar',
                                'en'
                            )
                        ),
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_chat_history_visitor_created
                ON chat_history (
                    visitor_id,
                    created_at DESC
                )
                """
            )

        _INITIALIZED_PATHS.add(
            path
        )


def _row_to_entry(
    row: sqlite3.Row,
) -> ChatHistoryEntry:
    return ChatHistoryEntry(
        id=row["id"],
        question=row["question"],
        language=row["language"],
        response=json.loads(
            row["response_json"]
        ),
        created_at=row["created_at"],
    )


@router.get(
    "/history",
    response_model=ChatHistoryResponse,
)
def get_chat_history(
    visitor_header: Annotated[
        str,
        Header(
            alias="X-Basira-Visitor"
        ),
    ],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
        ),
    ] = 20,
) -> ChatHistoryResponse:
    visitor_id = (
        _validate_visitor_id(
            visitor_header
        )
    )

    _ensure_database()

    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                question,
                language,
                response_json,
                created_at
            FROM chat_history
            WHERE visitor_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (
                visitor_id,
                limit,
            ),
        ).fetchall()

    return ChatHistoryResponse(
        items=[
            _row_to_entry(row)
            for row in rows
        ]
    )


@router.post(
    "/history",
    response_model=ChatHistoryEntry,
)
def save_chat_history(
    payload: ChatHistoryCreate,
    visitor_header: Annotated[
        str,
        Header(
            alias="X-Basira-Visitor"
        ),
    ],
) -> ChatHistoryEntry:
    visitor_id = (
        _validate_visitor_id(
            visitor_header
        )
    )

    _ensure_database()

    entry_id = str(
        uuid4()
    )

    created_at = (
        datetime.now(UTC)
        .isoformat()
    )

    response_json = json.dumps(
        payload.response,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO chat_history (
                id,
                visitor_id,
                question,
                language,
                response_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id,
                visitor_id,
                payload.question,
                payload.language,
                response_json,
                created_at,
            ),
        )

        # Bound storage per visitor.
        # History is convenience memory,
        # never religious evidence.
        connection.execute(
            """
            DELETE FROM chat_history
            WHERE visitor_id = ?
              AND id NOT IN (
                SELECT id
                FROM chat_history
                WHERE visitor_id = ?
                ORDER BY created_at DESC
                LIMIT ?
              )
            """,
            (
                visitor_id,
                visitor_id,
                MAX_HISTORY_PER_VISITOR,
            ),
        )

    return ChatHistoryEntry(
        id=entry_id,
        question=payload.question,
        language=payload.language,
        response=payload.response,
        created_at=created_at,
    )


@router.delete(
    "/history",
)
def clear_chat_history(
    visitor_header: Annotated[
        str,
        Header(
            alias="X-Basira-Visitor"
        ),
    ],
) -> dict[str, bool]:
    visitor_id = (
        _validate_visitor_id(
            visitor_header
        )
    )

    _ensure_database()

    with _connect() as connection:
        connection.execute(
            """
            DELETE FROM chat_history
            WHERE visitor_id = ?
            """,
            (visitor_id,),
        )

    return {
        "cleared": True,
    }
