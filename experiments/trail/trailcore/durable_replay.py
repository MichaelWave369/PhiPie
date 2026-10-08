"""Crash-persistent, fail-closed replay ledger for local ΦTrail lab handoffs.

SQLite enforces one monotonic sequence per provisioned key and unique observation
IDs per key across process restarts. Not a distributed consensus or secure
hardware monotonic counter. Do not silently reinitialize an existing lost DB.
"""
from __future__ import annotations

from pathlib import Path
from contextlib import closing
import os
import sqlite3


class DurableReplayWindow:
    """Drop-in replay-store interface for SomaIntake.receive.

    All errors fail closed. Persistent DB path should live off removable media
    when possible; deletion/replacement of its history invalidates replay proof.
    """
    def __init__(self, db_path: str | Path, *, max_records: int = 100_000) -> None:
        self.path = Path(db_path)
        if (not isinstance(max_records, int) or isinstance(max_records, bool)
                or not 1 <= max_records <= 1_000_000):
            raise ValueError("invalid replay-record limit")
        self.max_records = max_records
        if not self.path.parent.is_dir() or self.path.is_symlink():
            raise ValueError("parent directory missing or replay file is symlink")
        # Initialization is explicit and must be run once by an operator.
        # Running against a missing file must not create new replay history.
        if not self.path.is_file():
            raise FileNotFoundError("replay database missing; initialize explicitly")
        self._check_file()
        try:
            with closing(self._connect()) as db:
                names = {row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'")}
                if not {"highwater", "observation_ids", "ledger_marker"} <= names:
                    raise ValueError("uninitialized replay schema")
                marker = db.execute("SELECT id, protocol FROM ledger_marker").fetchall()
                if marker != [(1, "trail-durable-replay-v0.1")]:
                    raise ValueError("invalid replay marker")
                check = db.execute("PRAGMA integrity_check").fetchone()
                if check is None or check[0] != "ok":
                    raise ValueError("replay database integrity check failed")
        except sqlite3.Error as exc:
            raise ValueError("unusable replay database") from exc

    def _check_file(self) -> None:
        if not self.path.is_file() or self.path.is_symlink():
            raise ValueError("unsafe replay database path")
        if os.name == "posix" and self.path.stat().st_mode & 0o077:
            raise PermissionError("replay database must be owner-only")

    def _connect(self) -> sqlite3.Connection:
        # SQLite URI mode rw avoids accidental DB reinitialization after deletion.
        db = sqlite3.connect(self.path.resolve().as_uri() + "?mode=rw", uri=True,
                             timeout=1.5, isolation_level=None)
        db.execute("PRAGMA busy_timeout=1500")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA journal_mode=DELETE")  # avoids unchecked WAL sidecars in pilot
        return db

    @staticmethod
    def initialize(db_path: str | Path) -> None:
        path = Path(db_path)
        if not path.parent.is_dir() or path.is_symlink():
            raise ValueError("unsafe replay database destination")
        # Exclusive creation ensures no overwrite/truncation of replay history.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        try:
            with sqlite3.connect(str(path)) as db:
                db.execute("PRAGMA journal_mode=DELETE")
                db.execute("PRAGMA synchronous=FULL")
                db.executescript("""
                    CREATE TABLE ledger_marker(
                        id INTEGER PRIMARY KEY CHECK(id=1),
                        protocol TEXT NOT NULL);
                    INSERT INTO ledger_marker(id, protocol)
                    VALUES(1, 'trail-durable-replay-v0.1');
                    CREATE TABLE highwater(
                        key_id TEXT PRIMARY KEY, seq INTEGER NOT NULL);
                    CREATE TABLE observation_ids(
                        key_id TEXT NOT NULL, observation_id TEXT NOT NULL,
                        PRIMARY KEY(key_id, observation_id));
                """)
                db.commit()
        except BaseException:
            # No auto-recovery. Leave corrupt/incomplete DB visible for operator.
            raise

    def admit(self, key_id: str, sequence: int, observation_id: str) -> bool:
        if (not isinstance(key_id, str) or not isinstance(observation_id, str)
                or type(sequence) is not int or not 1 <= sequence < 2**53):
            return False
        try:
            self._check_file()
            db = self._connect()
            try:
                db.execute("BEGIN IMMEDIATE")
                # Re-read the marker inside the write transaction. A replaced or
                # wrong-protocol DB must not silently become a new sequence store.
                marker = db.execute("SELECT protocol FROM ledger_marker WHERE id=1").fetchone()
                if marker != ("trail-durable-replay-v0.1",):
                    db.execute("ROLLBACK")
                    return False
                count = db.execute("SELECT count(*) FROM observation_ids").fetchone()[0]
                if count >= self.max_records:
                    db.execute("ROLLBACK")
                    return False
                prev = db.execute("SELECT seq FROM highwater WHERE key_id=?", (key_id,)).fetchone()
                if prev is not None and sequence <= prev[0]:
                    db.execute("ROLLBACK")
                    return False
                if db.execute("SELECT 1 FROM observation_ids WHERE key_id=? AND observation_id=?",
                              (key_id, observation_id)).fetchone():
                    db.execute("ROLLBACK")
                    return False
                db.execute("INSERT INTO highwater(key_id,seq) VALUES (?,?) ON CONFLICT(key_id) "
                           "DO UPDATE SET seq=excluded.seq", (key_id, sequence))
                db.execute("INSERT INTO observation_ids(key_id,observation_id) VALUES (?,?)",
                           (key_id, observation_id))
                db.execute("COMMIT")
                return True
            finally:
                db.close()
        except (sqlite3.Error, OSError, ValueError):
            return False
