"""Shape the Research: Cedar Points, priorities, allocations and requests.

A Cedar Press subscription earns points for using the product and spends
them on what Cedar should research or build next. This module is the whole
of that rule, and the store it keeps.

THE RULE
- A subscription (the ACCOUNT, not each person on it) earns points once per
  calendar month, the first time anyone on it signs in that month: Cedar
  Press 1, Cedar Press+ 2. A second sign-in, a refresh, a fortieth session
  earn nothing more. A month with no sign-in earns nothing.
- Points accumulate and expire twelve months after the month they were
  earned if unspent, oldest spent first, so nobody returns after years with
  a stockpile.
- A subscriber puts points on priorities in whatever amounts they choose,
  and can take them back. Every priority shows its points AND how many
  subscriptions put them there: 30 points from 25 organizations is not 30
  from 5.
- Points inform; they do not decide. Feasibility, data quality, research
  value and Cedar's editorial judgment sit beside them, and the customer
  copy says so.

THE LEDGER IS APPEND-ONLY. A balance is a sum over rows that say why each
point came or went (monthly_activity, allocation, refund, expiration), so
any balance can be explained and nothing is overwritten. Allocations are a
derived table kept for the totals.

THE PRIORITIES ARE EDITORIAL DATA. ``data/cedar/priorities.json`` is the
owner's: titles, descriptions, types, statuses, what got published, what
evolved into what. The store re-seeds those fields from the file on every
start and never writes them back; points and subscriber counts live only
here. A research question that turns out to need a dataset is marked
``evolved_from`` on the dataset, which is the public record of why it is
being built.

The store is SQLite through the standard library: one file, no service to
run, and the same code answers from ``:memory:`` in the tests. When the
subscriber table arrives the account id here is its key.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import math
import os
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
SEED_PATH = _REPO / "data" / "cedar" / "priorities.json"

POINTS_PER_ACTIVE_MONTH = {"press": 1, "press_pro": 2}
EXPIRY_MONTHS = 12
TYPES = ("research_question", "dataset")
STATUSES = (
    "interest",
    "under_review",
    "research_underway",
    "data_construction_underway",
    "published",
)
REASONS = ("monthly_activity", "allocation", "refund", "expiration")
REQUEST_STATUSES = ("received", "under_review", "associated", "answered", "declined")


@dataclasses.dataclass(frozen=True)
class Account:
    """Who earns and spends: the subscription, and the person acting on it."""

    account_id: str
    user_id: str
    tier: str


class PointsError(ValueError):
    """A refusal the caller can show: not enough points, unknown priority."""


def month_of(day: dt.date | None = None) -> str:
    """The calendar month as ``YYYY-MM``, in UTC."""
    day = day or dt.datetime.now(dt.timezone.utc).date()
    return f"{day.year:04d}-{day.month:02d}"


def months_before(month: str, count: int) -> str:
    """``month`` minus ``count`` calendar months."""
    year, mon = (int(part) for part in month.split("-"))
    index = year * 12 + (mon - 1) - count
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def next_month(month: str) -> str:
    return months_before(month, -1)


# ── Related priorities ─────────────────────────────────────────────────────

_STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "how",
        "in",
        "into",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "there",
        "these",
        "this",
        "to",
        "was",
        "we",
        "what",
        "which",
        "who",
        "will",
        "with",
        "you",
        "your",
        "i",
        "wish",
        "had",
        "dataset",
        "data",
        "showing",
        "show",
        "more",
        "about",
        "would",
        "like",
        "want",
        "need",
    ]
)


def tokens(text: str) -> set[str]:
    """The words that carry meaning: lowercase, three letters or more, no stop words."""
    return {
        w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) >= 3 and w not in _STOP
    }


def relatedness(query: str, priority: dict[str, Any]) -> float:
    """Cosine-like overlap between a request and a priority's title and description."""
    q = tokens(query)
    p = tokens(f"{priority.get('title', '')} {priority.get('description', '')}")
    if not q or not p:
        return 0.0
    return len(q & p) / math.sqrt(len(q) * len(p))


RELATED_THRESHOLD = 0.2


def related(query: str, priorities: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    """The priorities a request reads as being about, best first, none below the threshold.

    The same function, word for word, lives in ``src/features/grove/pressPriorities.js``
    so the form can suggest before the request is sent and the service agrees.
    """
    scored = [(relatedness(query, p), p) for p in priorities]
    scored = [(s, p) for s, p in scored if s >= RELATED_THRESHOLD]
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [dict(p, relatedness=round(s, 3)) for s, p in scored[:limit]]


# ── The store ──────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS priorities (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'interest',
  created_by TEXT,
  published_output TEXT,
  evolved_from TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_points_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL,
  user_id TEXT,
  amount INTEGER NOT NULL,
  reason TEXT NOT NULL,
  priority_id TEXT,
  month TEXT,
  created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ledger_one_credit_a_month
  ON research_points_ledger (account_id, month) WHERE reason = 'monthly_activity';
CREATE INDEX IF NOT EXISTS ledger_by_account ON research_points_ledger (account_id);
CREATE TABLE IF NOT EXISTS priority_allocations (
  account_id TEXT NOT NULL,
  priority_id TEXT NOT NULL,
  points INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (account_id, priority_id)
);
CREATE TABLE IF NOT EXISTS research_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL,
  user_id TEXT,
  text TEXT NOT NULL,
  priority_id TEXT,
  use_case TEXT,
  status TEXT NOT NULL DEFAULT 'received',
  created_at TEXT NOT NULL
);
-- What a reader says they work on (the client's readerWork.js): one
-- optional answer per seat, never per subscription, because two seats of one
-- organization can do different work. Kept beside the ledger because it is
-- the other thing the service remembers about a reader, and a deployment
-- that names CEDAR_PRESS_DB keeps both across restarts.
CREATE TABLE IF NOT EXISTS reader_profiles (
  email TEXT PRIMARY KEY,
  work TEXT,
  updated_at TEXT NOT NULL
);
"""

_EDITORIAL = ("type", "title", "description", "status", "published_output", "evolved_from")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class Priorities:
    """The store and the rule, over one SQLite file (or ``:memory:``)."""

    def __init__(self, path: str | os.PathLike[str] = ":memory:") -> None:
        self._path = str(path)
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self._path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._db.executescript(_SCHEMA)
            self._db.commit()

    # ── seed ──

    def seed(self, source: Path | dict[str, Any] = SEED_PATH) -> int:
        """Insert or refresh the editorial fields of every seeded priority; never the counts."""
        data = (
            json.loads(Path(source).read_text(encoding="utf-8"))
            if not isinstance(source, dict)
            else source
        )
        rows = data.get("priorities", [])
        with self._lock:
            for row in rows:
                if row.get("type") not in TYPES:
                    raise ValueError(f"priority {row.get('id')}: type must be one of {TYPES}")
                if row.get("status", "interest") not in STATUSES:
                    raise ValueError(f"priority {row.get('id')}: status must be one of {STATUSES}")
                self._db.execute(
                    "INSERT INTO priorities (id, type, title, description, status, "
                    "created_by, published_output, evolved_from, created_at) "
                    "VALUES (?, ?, ?, ?, ?, 'cedar', ?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET type=excluded.type, title=excluded.title, "
                    "description=excluded.description, "
                    "status=excluded.status, published_output=excluded.published_output, "
                    "evolved_from=excluded.evolved_from",
                    (
                        row["id"],
                        row["type"],
                        row["title"],
                        row.get("description", ""),
                        row.get("status", "interest"),
                        row.get("published_output"),
                        row.get("evolved_from"),
                        _now(),
                    ),
                )
            self._db.commit()
        return len(rows)

    # ── earning ──

    def accrue(self, account: Account, month: str | None = None) -> int:
        """Credit the month's points once per subscription; expire what is twelve months old.

        Idempotent: the unique index refuses a second monthly credit for the
        same account and month, so a refresh, a sign-out and back, or forty
        sessions in a day credit nothing more. Returns what was credited.
        """
        month = month or month_of()
        amount = POINTS_PER_ACTIVE_MONTH.get(account.tier, 0)
        credited = 0
        with self._lock:
            if amount > 0:
                try:
                    self._db.execute(
                        "INSERT INTO research_points_ledger (account_id, user_id, amount, "
                        "reason, priority_id, month, created_at) "
                        "VALUES (?, ?, ?, 'monthly_activity', NULL, ?, ?)",
                        (account.account_id, account.user_id, amount, month, _now()),
                    )
                    credited = amount
                except sqlite3.IntegrityError:
                    credited = 0
            self._expire(account.account_id, month)
            self._db.commit()
        return credited

    def _expire(self, account_id: str, month: str) -> int:
        """Write off credits older than the expiry window that were never spent.

        Spending consumes the oldest credits first, so what can expire is the
        credits earned before the cutoff, less everything ever spent (net of
        refunds), less what already expired. Idempotent: once written, the
        next call finds nothing left to expire.
        """
        cutoff = months_before(month, EXPIRY_MONTHS)
        old_credits = self._sum(
            "SELECT COALESCE(SUM(amount), 0) FROM research_points_ledger WHERE account_id = ? "
            "AND reason = 'monthly_activity' AND month <= ?",
            (account_id, cutoff),
        )
        spent = -self._sum(
            "SELECT COALESCE(SUM(amount), 0) FROM research_points_ledger WHERE account_id = ? "
            "AND reason IN ('allocation', 'refund')",
            (account_id,),
        )
        expired = -self._sum(
            "SELECT COALESCE(SUM(amount), 0) FROM research_points_ledger WHERE account_id = ? "
            "AND reason = 'expiration'",
            (account_id,),
        )
        expirable = old_credits - spent - expired
        if expirable <= 0:
            return 0
        self._db.execute(
            "INSERT INTO research_points_ledger (account_id, user_id, amount, reason, "
            "priority_id, month, created_at) "
            "VALUES (?, NULL, ?, 'expiration', NULL, ?, ?)",
            (account_id, -expirable, month, _now()),
        )
        return expirable

    def _sum(self, sql: str, params: tuple) -> int:
        return int(self._db.execute(sql, params).fetchone()[0])

    def balance(self, account_id: str) -> int:
        return self._sum(
            "SELECT COALESCE(SUM(amount), 0) FROM research_points_ledger WHERE account_id = ?",
            (account_id,),
        )

    # ── spending ──

    def allocate(self, account: Account, priority_id: str, points: int) -> dict[str, Any]:
        """Put points on a priority (positive) or take them back (negative)."""
        if not isinstance(points, int) or points == 0:
            raise PointsError("Choose how many points to move.")
        with self._lock:
            if (
                self._db.execute("SELECT 1 FROM priorities WHERE id = ?", (priority_id,)).fetchone()
                is None
            ):
                raise PointsError("That priority does not exist.")
            row = self._db.execute(
                "SELECT points FROM priority_allocations WHERE account_id = ? AND priority_id = ?",
                (account.account_id, priority_id),
            ).fetchone()
            held = int(row["points"]) if row else 0
            if points > 0 and points > self.balance(account.account_id):
                raise PointsError("Not enough points available.")
            if points < 0 and -points > held:
                raise PointsError("You have fewer points on this priority than that.")
            reason = "allocation" if points > 0 else "refund"
            self._db.execute(
                "INSERT INTO research_points_ledger (account_id, user_id, amount, reason, "
                "priority_id, month, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    account.account_id,
                    account.user_id,
                    -points,
                    reason,
                    priority_id,
                    month_of(),
                    _now(),
                ),
            )
            now = _now()
            self._db.execute(
                "INSERT INTO priority_allocations (account_id, priority_id, points, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(account_id, priority_id) DO UPDATE SET points = points + "
                "excluded.points, updated_at = excluded.updated_at",
                (account.account_id, priority_id, points, now, now),
            )
            self._db.execute("DELETE FROM priority_allocations WHERE points <= 0")
            self._db.commit()
            return {
                "priority": self.priority(priority_id),
                "points_available": self.balance(account.account_id),
                "your_points": held + points,
            }

    # ── reading ──

    def _totals(self) -> dict[str, dict[str, int]]:
        rows = self._db.execute(
            "SELECT priority_id, COALESCE(SUM(points), 0) AS points, COUNT(DISTINCT "
            "account_id) AS subscribers "
            "FROM priority_allocations WHERE points > 0 GROUP BY priority_id"
        ).fetchall()
        return {
            r["priority_id"]: {"points": int(r["points"]), "subscribers": int(r["subscribers"])}
            for r in rows
        }

    def _shape(self, row: sqlite3.Row, totals: dict[str, dict[str, int]]) -> dict[str, Any]:
        t = totals.get(row["id"], {"points": 0, "subscribers": 0})
        return {
            "id": row["id"],
            "type": row["type"],
            "title": row["title"],
            "description": row["description"],
            "status": row["status"],
            "published_output": row["published_output"],
            "evolved_from": row["evolved_from"],
            "points": t["points"],
            "subscribers": t["subscribers"],
        }

    def priority(self, priority_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM priorities WHERE id = ?", (priority_id,)
            ).fetchone()
            return self._shape(row, self._totals()) if row else None

    def priorities(self) -> list[dict[str, Any]]:
        """Every priority with its points and subscriber count, most supported first."""
        with self._lock:
            totals = self._totals()
            rows = [
                self._shape(r, totals)
                for r in self._db.execute("SELECT * FROM priorities").fetchall()
            ]
        rows.sort(key=lambda p: (-p["points"], -p["subscribers"], p["title"]))
        return rows

    def influence(self, account: Account, month: str | None = None) -> dict[str, Any]:
        """What this subscription has and has done: the profile's card."""
        month = month or month_of()
        with self._lock:
            credited = (
                self._db.execute(
                    "SELECT 1 FROM research_points_ledger WHERE account_id = ? AND month = ? "
                    "AND reason = 'monthly_activity'",
                    (account.account_id, month),
                ).fetchone()
                is not None
            )
            allocations = [
                {
                    "priority_id": r["priority_id"],
                    "title": r["title"],
                    "type": r["type"],
                    "status": r["status"],
                    "points": int(r["points"]),
                }
                for r in self._db.execute(
                    "SELECT a.priority_id, a.points, p.title, p.type, p.status FROM "
                    "priority_allocations a "
                    "JOIN priorities p ON p.id = a.priority_id WHERE a.account_id = ? AND "
                    "a.points > 0 ORDER BY a.points DESC, p.title",
                    (account.account_id,),
                ).fetchall()
            ]
            activity = [
                {
                    "amount": int(r["amount"]),
                    "reason": r["reason"],
                    "priority_id": r["priority_id"],
                    "title": r["title"],
                    "month": r["month"],
                    "at": r["created_at"],
                }
                for r in self._db.execute(
                    "SELECT l.amount, l.reason, l.priority_id, l.month, l.created_at, p.title "
                    "FROM research_points_ledger l "
                    "LEFT JOIN priorities p ON p.id = l.priority_id WHERE l.account_id = ? "
                    "ORDER BY l.id DESC LIMIT 24",
                    (account.account_id,),
                ).fetchall()
            ]
            requests = [
                {
                    "id": int(r["id"]),
                    "text": r["text"],
                    "use_case": r["use_case"],
                    "status": r["status"],
                    "at": r["created_at"],
                    "priority_id": r["priority_id"],
                    "title": r["title"],
                }
                for r in self._db.execute(
                    "SELECT r.*, p.title FROM research_requests r LEFT JOIN priorities p ON "
                    "p.id = r.priority_id "
                    "WHERE r.account_id = ? ORDER BY r.id DESC",
                    (account.account_id,),
                ).fetchall()
            ]
            available = self.balance(account.account_id)
        rate = POINTS_PER_ACTIVE_MONTH.get(account.tier, 0)
        return {
            "account_id": account.account_id,
            "tier": account.tier,
            "month": month,
            "points_available": available,
            "points_per_active_month": rate,
            "credited_this_month": credited,
            "next_credit": {"points": rate, "month": next_month(month) if credited else month},
            "expiry_months": EXPIRY_MONTHS,
            "allocations": allocations,
            "activity": activity,
            "requests": requests,
        }

    # ── requests ──

    def submit_request(
        self,
        account: Account,
        text: str,
        use_case: str | None = None,
        priority_id: str | None = None,
    ) -> dict[str, Any]:
        """A subscriber's own words, kept beside the priority they read as related, if any."""
        text = (text or "").strip()
        if len(text) < 12:
            raise PointsError("Say a little more about what you need.")
        with self._lock:
            if (
                priority_id
                and self._db.execute(
                    "SELECT 1 FROM priorities WHERE id = ?", (priority_id,)
                ).fetchone()
                is None
            ):
                raise PointsError("That priority does not exist.")
            status = "associated" if priority_id else "received"
            cursor = self._db.execute(
                "INSERT INTO research_requests (account_id, user_id, text, priority_id, "
                "use_case, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    account.account_id,
                    account.user_id,
                    text,
                    priority_id,
                    (use_case or "").strip() or None,
                    status,
                    _now(),
                ),
            )
            self._db.commit()
            return {"id": int(cursor.lastrowid), "status": status, "priority_id": priority_id}

    def evidence(self, priority_id: str) -> dict[str, Any]:
        """What sits behind a priority, for Cedar's own reading.

        Points, subscriptions, and the requests in subscribers' own words.
        """
        with self._lock:
            p = self.priority(priority_id)
            if p is None:
                raise PointsError("That priority does not exist.")
            reqs = self._db.execute(
                "SELECT text, use_case, account_id, created_at FROM research_requests WHERE "
                "priority_id = ? ORDER BY id",
                (priority_id,),
            ).fetchall()
        uses: dict[str, int] = {}
        for r in reqs:
            if r["use_case"]:
                uses[r["use_case"]] = uses.get(r["use_case"], 0) + 1
        return {
            **p,
            "requests": len(reqs),
            "requesting_accounts": len({r["account_id"] for r in reqs}),
            "common_needs": sorted(uses, key=lambda u: (-uses[u], u)),
        }

    # ── the reader's declared work ──

    def profile(self, email: str) -> dict[str, Any]:
        """What this seat declared, or ``{"work": None}`` when it never answered."""
        with self._lock:
            row = self._db.execute(
                "SELECT work, updated_at FROM reader_profiles WHERE email = ?", (email,)
            ).fetchone()
        if row is None:
            return {"work": None, "updated_at": None}
        return {"work": row["work"], "updated_at": row["updated_at"]}

    def set_profile(self, email: str, work: str | None) -> dict[str, Any]:
        """Record the answer; ``None`` withdraws it. The caller validates the vocabulary."""
        with self._lock:
            if work is None:
                self._db.execute("DELETE FROM reader_profiles WHERE email = ?", (email,))
            else:
                self._db.execute(
                    "INSERT INTO reader_profiles (email, work, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(email) DO UPDATE SET work=excluded.work, "
                    "updated_at=excluded.updated_at",
                    (email, work, _now()),
                )
            self._db.commit()
        return self.profile(email)

    def close(self) -> None:
        with self._lock:
            self._db.close()
