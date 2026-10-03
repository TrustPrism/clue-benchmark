"""Durable request reservations and exactly-once episode dispatch."""

import json
import sqlite3
from contextlib import contextmanager
from decimal import ROUND_CEILING, Decimal
from pathlib import Path


class BudgetStop(RuntimeError):
    pass


class AccountingStop(RuntimeError):
    pass


def charge_microdollars(usage, prices):
    # Prices are USD per million tokens, so token * price gives microdollars.
    return int(
        (
            Decimal(str(prices["input_per_million"])) * usage["input_tokens"]
            + Decimal(str(prices["output_per_million"])) * usage["output_tokens"]
        ).to_integral_value(rounding=ROUND_CEILING)
    )


class Ledger:
    def __init__(self, path, plan):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS requests (
              id INTEGER PRIMARY KEY, episode TEXT NOT NULL, model TEXT NOT NULL,
              phase TEXT NOT NULL, reserved INTEGER NOT NULL, actual INTEGER,
              status TEXT NOT NULL, usage TEXT, error TEXT,
              created TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS episodes (
              id TEXT PRIMARY KEY, status TEXT NOT NULL, result TEXT);
            CREATE TABLE IF NOT EXISTS models (
              id TEXT PRIMARY KEY, status TEXT NOT NULL, result TEXT);
            """
        )
        ceiling = plan.get("spending", {}).get("combined_google_usd")
        if ceiling is None or not 0 < ceiling <= 50:
            raise ValueError(
                "a positive combined Gemini ceiling of at most $50 is required"
            )
        expected = {"plan_id": plan["plan_id"], "ceiling": str(int(ceiling * 1000000))}
        with self.db:
            existing = dict(self.db.execute("SELECT key,value FROM metadata"))
            if existing and existing != expected:
                raise ValueError("ledger is bound to a different manifest or ceiling")
            if not existing:
                self.db.executemany(
                    "INSERT INTO metadata VALUES (?,?)", expected.items()
                )
        self.ceiling = int(expected["ceiling"])

    def close(self):
        self.db.close()

    def guard(self):
        if self.db.execute(
            "SELECT 1 FROM requests WHERE status IN ('reserved','uncertain') LIMIT 1"
        ).fetchone():
            raise AccountingStop(
                "unresolved request accounting; execution remains stopped"
            )

    def committed(self):
        return self.db.execute(
            "SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM requests"
        ).fetchone()[0]

    def reserve(self, episode, model, phase, amount):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.guard()
            if self.committed() + amount > self.ceiling:
                raise BudgetStop("remaining allowance cannot cover the next request")
            row = self.db.execute(
                "INSERT INTO requests(episode,model,phase,reserved,status) VALUES(?,?,?,?,'reserved')",
                (episode, model, phase, amount),
            )
            self.db.commit()
            return row.lastrowid
        except BaseException:
            self.db.rollback()
            raise

    def settle(self, request_id, usage, actual):
        with self.db:
            row = self.db.execute(
                "SELECT * FROM requests WHERE id=?", (request_id,)
            ).fetchone()
            if row is None or row["status"] != "reserved":
                raise AccountingStop("request is not an outstanding reservation")
            if actual > row["reserved"]:
                self.db.execute(
                    "UPDATE requests SET status='uncertain',error='reservation_exceeded' WHERE id=?",
                    (request_id,),
                )
            else:
                self.db.execute(
                    "UPDATE requests SET actual=?,usage=?,status='settled' WHERE id=?",
                    (actual, json.dumps(usage), request_id),
                )
        if actual > row["reserved"]:
            raise AccountingStop("provider usage exceeded the conservative reservation")

    def uncertain(self, request_id, error):
        with self.db:
            self.db.execute(
                "UPDATE requests SET status='uncertain',error=? WHERE id=? AND status='reserved'",
                (error, request_id),
            )

    def begin_episode(self, episode):
        with self.db:
            return (
                self.db.execute(
                    "INSERT OR IGNORE INTO episodes(id,status) VALUES(?,'started')",
                    (episode,),
                ).rowcount
                == 1
            )

    def finish_episode(self, episode, result):
        with self.db:
            self.db.execute(
                "UPDATE episodes SET status='finished',result=? WHERE id=?",
                (json.dumps(result), episode),
            )

    def episodes(self):
        return {
            row["id"]: json.loads(row["result"])
            if row["result"]
            else {"error": "interrupted_episode", "correct": 0}
            for row in self.db.execute("SELECT * FROM episodes")
        }

    def model(self, model):
        row = self.db.execute("SELECT * FROM models WHERE id=?", (model,)).fetchone()
        return dict(row) if row else None

    def model_status(self, model, status, result):
        with self.db:
            self.db.execute(
                "INSERT INTO models VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,result=excluded.result",
                (model, status, json.dumps(result)),
            )

    def export(self):
        requests = [
            dict(r) for r in self.db.execute("SELECT * FROM requests ORDER BY id")
        ]
        for row in requests:
            if row["usage"]:
                row["usage"] = json.loads(row["usage"])
        return {
            "plan_id": dict(self.db.execute("SELECT key,value FROM metadata"))[
                "plan_id"
            ],
            "ceiling_usd": self.ceiling / 1000000,
            "committed_usd": self.committed() / 1000000,
            "settled_usd": sum(r["actual"] or 0 for r in requests) / 1000000,
            "unresolved_reservations_usd": sum(
                r["reserved"] for r in requests if r["actual"] is None
            )
            / 1000000,
            "remaining_usd": (self.ceiling - self.committed()) / 1000000,
            "requests": requests,
            "models": [
                dict(r) for r in self.db.execute("SELECT * FROM models ORDER BY id")
            ],
        }


@contextmanager
def execution_lock(path):
    # Kernel lock releases after a crash; an old lock file never resets the ledger.
    import fcntl

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(
                "another study runner owns this execution directory"
            ) from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
