#!/usr/bin/env python3
"""Cedar dataset pipeline — the one-file exemplar.

One script, one markdown (PIPELINE.md), one database. Every Cedar dataset
should look like this file: registry-driven, staleness-aware, and honest about
what it observed. Today the database is a local SQLite mock of the eventual
production store; the interface (`Database`) is the seam where that swap
happens without touching anything else.

The pipeline decides for itself what needs work:

  due?      last successful run older than the source's cadence (from the
            registry), or never run.
  changed?  the fetched artifact's content hash differs from the last
            snapshot — identical bytes mean no extraction at all.
  stale?    the newest artifact is older than 2x cadence, or the registry
            itself marks the source Stale — surfaced, never guessed around.
  record    canonical record_hash covers semantic fields only (casefolded,
  changed?  whitespace-normalized, digits-only phones, sorted arrays), so a
            record "changes" only when its meaning changes. Vanished records
            flip is_current to false — history is never deleted.

Guardrails inherited from the registry (binding, see CLAUDE.md):
respectful fetching (robots.txt, >=2s per domain, identifying User-Agent with
a contact email, back off on 403/429 — never rotate around a block), never
fabricate (extraction fails loudly on unrecognized layouts), schema validation
failure fails the run, raw snapshots are immutable.

Usage:
  python3 pipeline.py status            # what is due / fresh / stale / blocked
  python3 pipeline.py sync [TBD-###...] # run every due source (or just these)
  python3 pipeline.py sync TBD-030 --from-file export.csv   # offline artifact
  python3 pipeline.py demo              # end-to-end run on a synthetic fixture
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"          # raw snapshots + cedar.db live here (gitignored)
CONTACT_ENV = "CEDAR_CONTACT_EMAIL"

PRIORITY_CLASS = {
    "Tribal Primary": "tribal_primary",
    "Tribal Secondary": "tribal_secondary",
    "Tribal Partnership": "tribal_partnership",
    "Cross-Reference": "cross_reference",
    "Discovery Only": "discovery_only",
    "Coverage Frame": "coverage_frame",
}
CADENCE_DAYS = {"nightly": 1, "daily": 1, "weekly": 7, "biweekly": 14,
                "monthly": 30, "bimonthly": 60, "quarterly": 91, "annual": 365}


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PipelineError(Exception):
    """Loud failure: fabricating past it is never the answer."""


# ---------------------------------------------------------------- registry --
def load_registry() -> dict[str, dict]:
    rows = {}
    for line in (ROOT / "sources.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["source_id"]] = row
    ranks = {}
    for line in (ROOT / "scrape_queue.jsonl").read_text().splitlines():
        if line.strip():
            q = json.loads(line)
            ranks[q["source_id"]] = q["queue_rank"]
    for sid, row in rows.items():
        row["queue_rank"] = ranks.get(sid, 10_000)
    return rows


def cadence_days(source: dict) -> int:
    text = (source.get("suggested_cadence") or "").lower()
    for word, days in CADENCE_DAYS.items():
        if word in text:
            return days
    return 30  # registry rows without a stated cadence default to monthly


# ------------------------------------------------- canonical record hashing --
# The hash covers normalized semantic fields ONLY (no timestamps, run ids, or
# formatting), so a record changes iff its meaning changes.
SEMANTIC_FIELDS = [
    "source_business_key", "business_name_raw", "dba_name", "owner_name_raw",
    "identity_claim_text", "ownership_percent", "tribal_affiliation_raw",
    "certification_number", "certification_tier", "certification_start",
    "certification_expiration", "business_license_number",
    "service_category_raw", "naics", "description_raw", "address_raw", "city",
    "state_province", "postal_code", "phone", "email", "website",
    "relationship_basis_raw", "certification_event_status",
]


def _canon(field: str, value):
    if value is None:
        return None
    if field == "phone":
        digits = re.sub(r"\D", "", str(value))
        return digits or None
    if isinstance(value, str):
        return " ".join(value.split()).casefold() or None
    if isinstance(value, list):
        return sorted(_canon("", v) for v in value)
    return value


def record_hash(record: dict) -> str:
    canon = {f: _canon(f, record.get(f)) for f in SEMANTIC_FIELDS}
    canon = {k: v for k, v in canon.items() if v is not None}
    blob = json.dumps(canon, sort_keys=True, ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(blob).hexdigest()


# ------------------------------------------------------------- snapshot store --
class SnapshotStore:
    """Immutable raw artifacts under raw/{source_id}/{run_id}/ — body plus a
    meta.json with final URL, HTTP status, headers, and content hash. Paths are
    never overwritten; auditability beats disk space."""

    def __init__(self, base: Path):
        self.base = base

    def save(self, source_id: str, run_id: str, body: bytes, meta: dict) -> Path:
        d = self.base / "raw" / source_id / run_id
        if d.exists():
            raise PipelineError(f"snapshot path exists (immutable): {d}")
        d.mkdir(parents=True)
        (d / "body").write_bytes(body)
        meta = dict(meta, content_sha256=hashlib.sha256(body).hexdigest(),
                    saved_at=iso(now()))
        (d / "meta.json").write_text(json.dumps(meta, indent=1))
        return d

    def latest(self, source_id: str) -> dict | None:
        d = self.base / "raw" / source_id
        if not d.exists():
            return None
        runs = sorted(p for p in d.iterdir() if (p / "meta.json").exists())
        if not runs:
            return None
        meta = json.loads((runs[-1] / "meta.json").read_text())
        meta["path"] = str(runs[-1])
        return meta


# ------------------------------------------------------------------ database --
class Database:
    """The convenient database — SQLite today, the production store later.
    Everything above this class stays identical when the backend swaps."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS runs (
      run_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, started_at TEXT,
      artifact_sha256 TEXT, http_status INTEGER, outcome TEXT,
      appeared INTEGER, changed INTEGER, unchanged INTEGER, vanished INTEGER,
      detail TEXT);
    CREATE TABLE IF NOT EXISTS source_records (
      business_source_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
      record_hash TEXT NOT NULL, first_seen TEXT NOT NULL,
      last_seen TEXT NOT NULL, is_current INTEGER NOT NULL,
      payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS record_events (
      run_id TEXT NOT NULL, business_source_id TEXT NOT NULL,
      event TEXT NOT NULL, record_hash TEXT, at TEXT NOT NULL);
    """

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.executescript(self.SCHEMA)

    def last_success(self, source_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT run_id, started_at, artifact_sha256 FROM runs WHERE "
            "source_id=? AND outcome='ok' ORDER BY started_at DESC LIMIT 1",
            (source_id,)).fetchone()
        return row and {"run_id": row[0], "started_at": row[1],
                        "artifact_sha256": row[2]}

    def log_run(self, run_id, source_id, artifact_sha, status, outcome,
                counts=(0, 0, 0, 0), detail=None):
        self.conn.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, source_id, iso(now()), artifact_sha, status, outcome,
             *counts, detail))
        self.conn.commit()

    def upsert(self, source_id: str, run_id: str, records: list[dict]) -> tuple:
        """Append-mostly load: new hash -> changed; same hash -> touch
        last_seen; missing from this pull -> is_current=0 (never deleted)."""
        ts = iso(now())
        current = dict(self.conn.execute(
            "SELECT business_source_id, record_hash FROM source_records "
            "WHERE source_id=? AND is_current=1", (source_id,)).fetchall())
        appeared = changed = unchanged = 0
        seen = set()
        for rec in records:
            bsid, rhash = rec["business_source_id"], rec["record_hash"]
            seen.add(bsid)
            if bsid not in current:
                event, appeared = "appeared", appeared + 1
                self.conn.execute(
                    "INSERT OR REPLACE INTO source_records VALUES (?,?,?,?,?,1,?)",
                    (bsid, source_id, rhash, rec["first_seen"], ts,
                     json.dumps(rec, ensure_ascii=False)))
            elif current[bsid] != rhash:
                event, changed = "changed", changed + 1
                self.conn.execute(
                    "UPDATE source_records SET record_hash=?, last_seen=?, "
                    "is_current=1, payload=? WHERE business_source_id=?",
                    (rhash, ts, json.dumps(rec, ensure_ascii=False), bsid))
            else:
                event, unchanged = "unchanged", unchanged + 1
                self.conn.execute(
                    "UPDATE source_records SET last_seen=? WHERE business_source_id=?",
                    (ts, bsid))
            if event != "unchanged":
                self.conn.execute("INSERT INTO record_events VALUES (?,?,?,?,?)",
                                  (run_id, bsid, event, rhash, ts))
        vanished = 0
        for bsid in set(current) - seen:
            vanished += 1
            self.conn.execute(
                "UPDATE source_records SET is_current=0 WHERE business_source_id=?",
                (bsid,))
            self.conn.execute("INSERT INTO record_events VALUES (?,?,?,?,?)",
                              (run_id, bsid, "vanished", None, ts))
        self.conn.commit()
        return appeared, changed, unchanged, vanished


# ------------------------------------------------------------ respectful fetch --
class Fetcher:
    """Every rule here is a registry guardrail, not a suggestion."""

    MIN_INTERVAL = 2.0  # seconds per domain

    def __init__(self, contact: str | None):
        if not contact or "@" not in contact:
            raise PipelineError(
                f"set {CONTACT_ENV} to a monitored contact email — Cedar does "
                "not fetch tribal sites anonymously")
        self.ua = f"CedarPressBot/0.1 (+mailto:{contact})"
        self._last: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    def _allowed(self, url: str) -> bool:
        host = urllib.parse.urlsplit(url).netloc
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser(
                f"https://{host}/robots.txt")
            try:
                rp.read()
            except OSError:
                rp = None  # robots unreachable: proceed politely, log nothing false
            self._robots[host] = rp
        rp = self._robots[host]
        return rp is None or rp.can_fetch(self.ua, url)

    def get(self, url: str) -> tuple[bytes, dict]:
        if not self._allowed(url):
            raise PipelineError(f"robots.txt disallows {url} — respected, not bypassed")
        host = urllib.parse.urlsplit(url).netloc
        wait = self.MIN_INTERVAL - (time.monotonic() - self._last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": self.ua})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                meta = {"url": url, "final_url": resp.geturl(),
                        "http_status": resp.status,
                        "headers": dict(resp.headers.items())}
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                raise PipelineError(
                    f"HTTP {e.code} from {host}: backing off — a block is a "
                    "signal to stop, never to rotate around") from e
            raise PipelineError(f"HTTP {e.code} fetching {url}") from e
        finally:
            self._last[host] = time.monotonic()
        return body, meta


# --------------------------------------------------------------- extractors --
# One small adapter per source, registered by source_id. An adapter maps ONE
# artifact layout to partial Layer-1 records; anything it does not recognize
# is a loud failure, never a guess.

def _csv_rows(body: bytes) -> list[dict]:
    text = body.decode("utf-8-sig", errors="strict")
    return list(csv.DictReader(io.StringIO(text)))


def _pick(row: dict, *names: str):
    """Match a column by normalized header name; None when absent."""
    canon = {re.sub(r"\W+", "", k).casefold(): v for k, v in row.items() if k}
    for name in names:
        v = canon.get(re.sub(r"\W+", "", name).casefold())
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def extract_tulalip_naob(body: bytes) -> list[dict]:
    """TBD-030 — Tulalip NAOB registry CSV export. Registry fields_observed:
    business, cert no., address, phones, email, site, applicant, tribe of
    affiliation, Tulalip %, small-business flag. 'Tulalip Owned %' measures
    Tulalip-MEMBER ownership only (never read it as Native ownership %)."""
    records = []
    for row in _csv_rows(body):
        name = _pick(row, "Business", "Business Name")
        if not name:
            raise PipelineError(
                f"TBD-030: unrecognized CSV layout (no business column in "
                f"{sorted(k for k in row if k)}) — refusing to guess")
        pct = _pick(row, "Tulalip Owned %", "Tulalip %")
        records.append({
            "source_business_key": _pick(row, "Cert No", "Certification Number"),
            "business_name_raw": name,
            "owner_name_raw": _pick(row, "Applicant"),
            "tribal_affiliation_raw": _pick(row, "Tribe of Affiliation", "Tribe"),
            "ownership_percent": float(re.sub(r"[^\d.]", "", pct)) if pct and
                                 re.search(r"\d", pct) else None,
            "certification_number": _pick(row, "Cert No", "Certification Number"),
            "address_raw": _pick(row, "Address"),
            "phone": _pick(row, "Phone", "Phones"),
            "email": _pick(row, "Email"),
            "website": _pick(row, "Site", "Website"),
            "description_raw": _pick(row, "Summary", "Description"),
            "directory_type": "tero",
            "identity_scope": "any_native",
            "identity_claim_text": "TERO-certified Native American-owned business",
            "verification_basis": "tribal_certification",
        })
    return records


EXTRACTORS = {"TBD-030": extract_tulalip_naob}


def envelope(source: dict, partial: dict, run_id: str, snapshot_uri: str,
             method: str) -> dict:
    """Wrap an extractor's partial record into a schema-valid Layer-1 row."""
    ts = iso(now())
    rec = {
        "source_id": source["source_id"],
        "source_url": source["directory_url"],
        "first_seen": ts, "last_seen": ts,
        "ingestion_method": method,
        "raw_snapshot_uri": snapshot_uri,
        "refresh_run_id": run_id,
        "source_priority_class": PRIORITY_CLASS[source["source_priority_class"]],
        "cross_reference_only":
            PRIORITY_CLASS[source["source_priority_class"]] != "tribal_primary"
            and PRIORITY_CLASS[source["source_priority_class"]] != "tribal_secondary",
        **partial,
    }
    key = rec.get("source_business_key") or record_hash(rec)[:23]
    rec["business_source_id"] = f"{source['source_id']}:{key}"
    rec["record_hash"] = record_hash(rec)
    return rec


def validate(records: list[dict]) -> None:
    """Schema validation failure fails the run — nothing partial is loaded."""
    import jsonschema
    schema = json.loads((ROOT / "schema/source_record.schema.json").read_text())
    v = jsonschema.Draft202012Validator(schema)
    problems = [f"{r.get('business_source_id')}: {e.message}"
                for r in records for e in v.iter_errors(r)]
    if problems:
        raise PipelineError("schema validation failed:\n  " + "\n  ".join(problems[:10]))


# ----------------------------------------------------------- staleness logic --
def assess(source: dict, db: Database, store: SnapshotStore) -> dict:
    sid = source["source_id"]
    days = cadence_days(source)
    last = db.last_success(sid)
    state, why = "due", "never run"
    if last:
        age = (now() - datetime.fromisoformat(last["started_at"])).days
        state, why = (("due", f"last run {age}d ago >= {days}d cadence")
                      if age >= days else ("fresh", f"ran {age}d ago (cadence {days}d)"))
    if sid not in EXTRACTORS:
        state, why = "no_extractor", "no adapter registered yet"
    if source["status_group"] != "Live":
        state, why = "not_live", f"registry status {source['status_group']}"
    snap = store.latest(sid)
    stale = source["status_group"] == "Stale" or (
        snap and (now() - datetime.fromisoformat(snap["saved_at"])).days > 2 * days)
    return {"source_id": sid, "state": state, "why": why, "stale": bool(stale),
            "rank": source["queue_rank"], "cadence_days": days}


# ------------------------------------------------------------------ commands --
def run_source(source, db, store, body, fetch_meta, method) -> str:
    sid = source["source_id"]
    run_id = f"{now():%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"
    sha = hashlib.sha256(body).hexdigest()
    last = db.last_success(sid)
    if last and last["artifact_sha256"] == sha:
        db.log_run(run_id, sid, sha, fetch_meta.get("http_status"), "ok",
                   detail="artifact unchanged; extraction skipped")
        return f"{sid}: artifact unchanged ({sha[:12]}) — nothing to extract"
    snap = store.save(sid, run_id, body, fetch_meta)
    try:
        partials = EXTRACTORS[sid](body)
        records = [envelope(source, p, run_id, str(snap / "body"), method)
                   for p in partials]
        validate(records)
    except PipelineError as e:
        db.log_run(run_id, sid, sha, fetch_meta.get("http_status"), "failed",
                   detail=str(e))
        raise
    counts = db.upsert(sid, run_id, records)
    db.log_run(run_id, sid, sha, fetch_meta.get("http_status"), "ok", counts)
    a, c, u, v = counts
    return (f"{sid}: {len(records)} records — {a} appeared, {c} changed, "
            f"{u} unchanged, {v} vanished")


def cmd_status(db, store, registry):
    rows = sorted((assess(s, db, store) for s in registry.values()
                   if s["source_id"] in EXTRACTORS or s["status_group"] == "Live"),
                  key=lambda r: r["rank"])
    for r in rows:
        flag = " STALE" if r["stale"] else ""
        print(f"{r['source_id']:8} {r['state']:12}{flag:6} {r['why']}")
    covered = sum(1 for r in rows if r["state"] not in ("no_extractor", "not_live"))
    print(f"\n{covered} runnable / {len(EXTRACTORS)} adapters / "
          f"{len(rows)} live-or-adapted sources")


def cmd_sync(db, store, registry, ids, from_file, contact) -> int:
    targets = [registry[i] for i in ids] if ids else [
        registry[a["source_id"]] for a in
        sorted((assess(s, db, store) for s in registry.values()), key=lambda r: r["rank"])
        if a["state"] == "due"]
    if not targets:
        print("nothing due")
        return 0
    fetcher, failures = None, 0
    for source in targets:
        sid = source["source_id"]
        if sid not in EXTRACTORS:
            print(f"{sid}: skipped — no adapter registered")
            continue
        try:
            if from_file:
                body = Path(from_file).read_bytes()
                meta = {"url": f"file://{Path(from_file).resolve()}",
                        "http_status": None,
                        "note": "operator-supplied artifact (offline ingest)"}
                method = "csv"
            else:
                fetcher = fetcher or Fetcher(contact)
                body, meta = fetcher.get(source["directory_url"])
                method = "csv"
            print(run_source(source, db, store, body, meta, method))
        except PipelineError as e:
            failures += 1
            print(f"{sid}: FAILED — {e}", file=sys.stderr)
    return failures


FIXTURE_V1 = """Business,Cert No,Applicant,Tribe of Affiliation,Tulalip Owned %,Address,Phone,Email,Site,Summary
Example Cedarworks LLC,SYN-001,Alex Example,Example Nation,0,"1 Fixture Way, Demo WA",555-000-0001,fixture-a@example.invalid,https://example.invalid/a,Synthetic fixture record
Sample Salmon Co,SYN-002,Sam Sample,Example Nation,100,"2 Fixture Way, Demo WA",555-000-0002,fixture-b@example.invalid,https://example.invalid/b,Synthetic fixture record
Placeholder Print Shop,SYN-003,Pat Placeholder,Example Nation,51,"3 Fixture Way, Demo WA",555-000-0003,fixture-c@example.invalid,https://example.invalid/c,Synthetic fixture record
"""
FIXTURE_V2 = """Business,Cert No,Applicant,Tribe of Affiliation,Tulalip Owned %,Address,Phone,Email,Site,Summary
Example Cedarworks LLC,SYN-001,Alex Example,Example Nation,0,"1 Fixture Way, Demo WA",(555) 000-0001,fixture-a@example.invalid,https://example.invalid/a,Synthetic fixture record
Sample Salmon Co,SYN-002,Sam Sample,Example Nation,100,"9 Moved St, Demo WA",555-000-0002,fixture-b@example.invalid,https://example.invalid/b,Synthetic fixture record
New Demo Weaving,SYN-004,Nia Newcomer,Example Nation,100,"4 Fixture Way, Demo WA",555-000-0004,fixture-d@example.invalid,https://example.invalid/d,Synthetic fixture record
"""


def cmd_demo(scratch: Path):
    """Full lifecycle on SYNTHETIC data (source TBD-000, .invalid domains —
    nothing here is a real business) in a scratch directory. Pull 2 proves the
    staleness machinery: a formatting-only phone change is 'unchanged' (hash
    canonicalization), a moved address is 'changed', a dropped row 'vanished'."""
    demo_source = {
        "source_id": "TBD-000", "status_group": "Live", "queue_rank": 0,
        "directory_url": "https://example.invalid/naob.csv",
        "suggested_cadence": "Weekly", "source_priority_class": "Tribal Primary",
    }
    EXTRACTORS["TBD-000"] = extract_tulalip_naob
    db = Database(scratch / "cedar.db")
    store = SnapshotStore(scratch)
    print("pull 1 (initial):")
    print(" ", run_source(demo_source, db, store, FIXTURE_V1.encode(),
                          {"url": demo_source["directory_url"], "http_status": 200,
                           "note": "synthetic fixture"}, "csv"))
    print("pull 2 (same bytes):")
    print(" ", run_source(demo_source, db, store, FIXTURE_V1.encode(),
                          {"url": demo_source["directory_url"], "http_status": 200,
                           "note": "synthetic fixture"}, "csv"))
    print("pull 3 (edition changed):")
    print(" ", run_source(demo_source, db, store, FIXTURE_V2.encode(),
                          {"url": demo_source["directory_url"], "http_status": 200,
                           "note": "synthetic fixture"}, "csv"))
    del EXTRACTORS["TBD-000"]
    n_current = db.conn.execute(
        "SELECT COUNT(*) FROM source_records WHERE is_current=1").fetchone()[0]
    n_all = db.conn.execute("SELECT COUNT(*) FROM source_records").fetchone()[0]
    print(f"database: {n_current} current / {n_all} total records, "
          f"history preserved in record_events ({scratch}/cedar.db)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["status", "sync", "demo"])
    ap.add_argument("source_ids", nargs="*", help="restrict sync to these TBD ids")
    ap.add_argument("--from-file", help="ingest a local artifact instead of fetching")
    ap.add_argument("--data-dir", default=str(DATA_DIR))
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    if args.command == "demo":
        import tempfile
        cmd_demo(Path(tempfile.mkdtemp(prefix="cedar-demo-")))
        return 0
    registry = load_registry()
    db = Database(data_dir / "cedar.db")
    store = SnapshotStore(data_dir)
    if args.command == "status":
        cmd_status(db, store, registry)
        return 0
    import os
    failures = cmd_sync(db, store, registry, args.source_ids, args.from_file,
                        os.environ.get(CONTACT_ENV))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
