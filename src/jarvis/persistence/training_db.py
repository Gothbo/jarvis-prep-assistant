"""SQLite-backed persistence for training conversation sessions.

Stores complete training sessions -- configuration, chat messages, and
scoring results -- so users can review past conversations and track progress
across multiple training runs.

Schema
------
sessions : one row per training session (metadata + final score)
messages : one row per chat message, FK -> sessions.id
scores   : one row per scoring dimension, FK -> sessions.id
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TrainingDB:
    """Manage SQLite storage for JARVIS training sessions.

    Parameters
    ----------
    db_path : str | Path
        Filesystem path for the SQLite database file.  Parent directories
        are created automatically.

    Example
    -------
    >>> db = TrainingDB("/tmp/jarvis_cache/training.db")
    >>> sid = db.save_session(config, messages, scores)
    >>> db.list_sessions()
    [{'id': '...', 'created_at': '...', ...}, ...]
    """

    # ------------------------------------------------------------------ #
    # Construction / connection
    # ------------------------------------------------------------------ #

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self._db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        # Return rows as dicts for ergonomic access
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    # ------------------------------------------------------------------ #
    # Schema bootstrap
    # ------------------------------------------------------------------ #

    def _create_tables(self) -> None:
        """Create tables if they do not already exist."""
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id            TEXT PRIMARY KEY,
                created_at    TEXT NOT NULL,
                industry      TEXT NOT NULL,
                scenario      TEXT NOT NULL,
                personality   TEXT NOT NULL,
                final_score   INTEGER
            );

            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS scores (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                dimension   TEXT    NOT NULL,
                score       INTEGER NOT NULL,
                feedback    TEXT    NOT NULL DEFAULT '',
                FOREIGN KEY (session_id) REFERENCES sessions(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_scores_session
                ON scores(session_id);
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def save_session(
        self,
        config: Any,
        messages: list[Any],
        scores: list[Any],
        *,
        session_id: str | None = None,
    ) -> str:
        """Persist a complete training session and return its id.

        Parameters
        ----------
        config : TrainingConfig
            Dataclass with *industry*, *scenario*, *personality* attributes.
        messages : list[ChatMessage]
            Ordered conversation history.  Each element has *role* and *content*.
        scores : list[ScoreDimension]
            Scoring results.  Each element has *key*, *score*, and *comment*
            (or *label* for the human-readable dimension name).
        session_id : str, optional
            Explicit session identifier.  A UUID is generated when omitted.

        Returns
        -------
        str
            The session id that was saved.
        """
        sid = session_id or uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()

        # Compute a final_score as the mean of all dimension scores (nullable)
        final_score: int | None = None
        if scores:
            final_score = round(
                sum(_attr(s, "score", 0) for s in scores) / len(scores)
            )

        self._conn.execute(
            """
            INSERT INTO sessions (id, created_at, industry, scenario, personality, final_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                sid,
                now,
                _attr(config, "industry", ""),
                _attr(config, "scenario", ""),
                _attr(config, "personality", ""),
                final_score,
            ),
        )

        for msg in messages:
            self._conn.execute(
                """
                INSERT INTO messages (session_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    sid,
                    _attr(msg, "role", ""),
                    _attr(msg, "content", ""),
                    now,
                ),
            )

        for sc in scores:
            self._conn.execute(
                """
                INSERT INTO scores (session_id, dimension, score, feedback)
                VALUES (?, ?, ?, ?)
                """,
                (
                    sid,
                    _attr(sc, "key", "") or _attr(sc, "dimension", ""),
                    _attr(sc, "score", 0),
                    _attr(sc, "comment", "") or _attr(sc, "feedback", ""),
                ),
            )

        self._conn.commit()
        return sid

    def save_messages(
        self,
        session_id: str,
        messages: list[Any],
    ) -> None:
        """Append messages to an existing session.

        Parameters
        ----------
        session_id : str
            The id of the session to append to.
        messages : list[ChatMessage]
            Messages to append.
        """
        now = datetime.now(timezone.utc).isoformat()
        for msg in messages:
            self._conn.execute(
                """
                INSERT INTO messages (session_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    session_id,
                    _attr(msg, "role", ""),
                    _attr(msg, "content", ""),
                    now,
                ),
            )
        self._conn.commit()

    def save_scores(
        self,
        session_id: str,
        scores: list[Any],
    ) -> None:
        """Save scoring results for an existing session.

        Also updates the session's ``final_score`` to the mean of the
        provided dimension scores.

        Parameters
        ----------
        session_id : str
            The id of the session to score.
        scores : list[ScoreDimension]
            Scoring results to persist.
        """
        for sc in scores:
            self._conn.execute(
                """
                INSERT INTO scores (session_id, dimension, score, feedback)
                VALUES (?, ?, ?, ?)
                """,
                (
                    session_id,
                    _attr(sc, "key", "") or _attr(sc, "dimension", ""),
                    _attr(sc, "score", 0),
                    _attr(sc, "comment", "") or _attr(sc, "feedback", ""),
                ),
            )

        if scores:
            avg = round(
                sum(_attr(s, "score", 0) for s in scores) / len(scores)
            )
            self._conn.execute(
                "UPDATE sessions SET final_score = ? WHERE id = ?",
                (avg, session_id),
            )

        self._conn.commit()

    def list_sessions(self) -> list[dict[str, Any]]:
        """Return metadata for every saved session, newest first.

        Returns
        -------
        list[dict]
            Each dict contains: *id*, *created_at*, *industry*, *scenario*,
            *personality*, *final_score*.
        """
        rows = self._conn.execute(
            "SELECT id, created_at, industry, scenario, personality, final_score "
            "FROM sessions ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        """Load the full data for one session.

        Parameters
        ----------
        session_id : str
            The id returned by :meth:`save_session`.

        Returns
        -------
        dict or None
            Keys: *session* (metadata dict), *messages* (list of dicts with
            *role* and *content*), *scores* (list of dicts with *dimension*,
            *score*, *feedback*).  Returns ``None`` when the id is not found.
        """
        session_row = self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if session_row is None:
            return None

        message_rows = self._conn.execute(
            "SELECT role, content FROM messages "
            "WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()

        score_rows = self._conn.execute(
            "SELECT dimension, score, feedback FROM scores "
            "WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()

        return {
            "session": dict(session_row),
            "messages": [dict(m) for m in message_rows],
            "scores": [dict(s) for s in score_rows],
        }

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related messages / scores.

        Parameters
        ----------
        session_id : str
            The id of the session to remove.

        Returns
        -------
        bool
            ``True`` if a row was actually deleted, ``False`` if the id
            did not exist.
        """
        cursor = self._conn.execute(
            "DELETE FROM sessions WHERE id = ?", (session_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    def __enter__(self) -> TrainingDB:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


# ------------------------------------------------------------------ #
# Internal helpers
# ------------------------------------------------------------------ #

def _attr(obj: Any, name: str, default: Any = None) -> Any:
    """Read an attribute from a dataclass, dict, or object.

    Supports both ``obj.name`` (dataclass / object) and ``obj["name"]``
    (dict) access patterns so the DB layer is flexible about input types.
    """
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)
