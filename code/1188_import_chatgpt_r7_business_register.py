#!/usr/bin/env python3
"""1188 - freeze and audit ChatGPT's R7 business register. IMPORTS NOTHING.

R7 is ONE immutable input: the delivered ZIP and its checksum. Every R7 table
is read from its exact expected ZIP member. This tool never writes canonical
data (data/spine/, data/clean/); an import, once the owner has decided every
gate, is a separate reviewed change.

TWO STATUSES, NEVER CONFLATED
    INTEGRITY        PASS / FAIL - is the frozen input intact and self-consistent?
    IMPORT APPROVAL  APPROVED / NOT_APPROVED - is every owner decision recorded
                     and CURRENT? Never APPROVED while INTEGRITY fails; even
                     APPROVED imports nothing here.

PROPOSED EQUIVALENCE PAIRS, NOT EQUIVALENCES
    R7 proposes 83 (cedar_uid, business_uid) pairs; each is UNRESOLVED until the
    decisions file holds a CURRENT owner disposition for it. The identifier
    ledger ATTRIBUTES identifiers to owning or controlling Native entities; no
    ledger field records a same-legal-object determination, so generated
    evidence never resolves a pair.

OWNER INPUTS - the only two files a person edits
    docs/imports/R7_OWNER_DECISIONS.json   typed, versioned dispositions; may open gates
        schema cedar.r7.owner_decisions.v2 (load_decisions): exact keys and
        enumerations, no duplicate JSON keys, no future dates, unique ids, one
        head per subject (a change supersedes, never deletes). A pair decision
        is CURRENT only while its evidence_fingerprint equals the pair's
        fingerprint now; otherwise STALE, kept, never counted. Append-only
        against the current bundle.
    docs/imports/R7_OWNER_NOTES.json       commentary only; never opens a gate
        {"schema": "cedar.r7.owner_notes.v1",
         "notes":            [{"pair_key", "note", "updated_by", "updated_on"}],
         "historical_notes": [{"pair_key", "note", "updated_by", "updated_on"}]}
        One entry per pair_key across both lists; "notes" only for proposed
        pairs, "historical_notes" only for pairs no longer proposed. Remove a
        note by deleting its entry. Unknown keys are rejected.

AUDIT BUNDLES (docs/imports/r7_audit/) - generated and immutable; never edit
    bundles/<id>/manifest.json + queue.csv   content-addressed snapshot of the
                                            inputs, evidence, decisions and notes
    CURRENT.json                            pointer; its os.replace is the one commit point
    .lock, .lock.owner.json                 OS-managed lock file; last holder (diagnostic only)
    The report fails closed (exit 4) if any bundle's files disagree with its
    manifest or the pointer. Returning to an earlier exact input state
    reactivates that earlier bundle; no bundle is ever rewritten.

    Bundle bytes are content-addressed: any formatting, quoting or newline change
    inside a bundle is corruption. .gitattributes marks docs/imports/r7_audit/**
    -text so git never converts them.

    freeze and recover hold one OS-managed exclusive lock (msvcrt byte lock on
    Windows, flock elsewhere) on the permanent file .lock for the whole operation:
    acquire; load and verify every consequential input; read CURRENT; validate
    history; prepare; recheck; publish; recheck every consequential input and
    CURRENT again; activate; release. The operating system releases the lock when
    its holder exits or dies, so there is no stale lock, no unlock command, and the
    lock file is never renamed or removed. A held lock is a refusal (exit 5), never
    a wait. .lock.owner.json names the last holder for diagnosis and authorises
    nothing.

    report takes the same lock on the same permanent .lock file, non-blocking, for
    its whole snapshot: it loads every input and reads CURRENT and the bundles
    inside it, so it can never mix inputs from one moment with a store from another.
    It refuses (exit 5) rather than read a store mid-transaction, and it writes
    nothing at all: read_lock opens .lock without a create-capable mode, so an
    uninitialized store is a refusal (exit 6), never something report creates.
    Initialization is freeze's authorized write. If any input changes while the
    report runs, the snapshot it evaluated is stale and it exits 11, never 0 or 10.

RETENTION
    Every activated bundle is kept; freeze and recover never prune. Leftovers of
    failed transactions are renamed to .abandoned-<reason>-<sha12>-<name> (a
    .dupN suffix marks identical content) and listed by the report inventory
    with transaction, operation, reason, time, related bundle and whether they
    hold notes or decisions found in no activated bundle. Deleting or archiving
    any of them is a separate, explicit maintenance step outside this tool.

USAGE (any other argument exits 2)
    py -3 code/1188_import_chatgpt_r7_business_register.py            # report
    py -3 code/1188_import_chatgpt_r7_business_register.py freeze
    py -3 code/1188_import_chatgpt_r7_business_register.py recover
    py -3 -B code/1188_import_chatgpt_r7_business_register_test.py                                                      # tests

EXIT CODES
    report : 0 integrity PASS and every approval CURRENT; 10 integrity PASS but
             NOT_APPROVED; 1 integrity FAIL or invalid owner inputs; 3 incomplete
             transaction or invalid pointer (run recover); 4 bundle content
             corrupt; 5 lock held; 6 audit store not initialized (report creates
             nothing, not even the lock file: run freeze first); 11 an input
             changed while the report ran, so the snapshot it evaluated is stale.
             0 and 10 are then never returned and the evaluation shown is not
             current. 11 is the report's own snapshot going stale; it is not the
             STALE_ARTIFACT bundle status, which says a bundle needs refreezing
    freeze : 0 means audit artifacts were written. It is NOT import approval.
             1 refused; 5 lock held
    recover: 0 clean afterwards; 1 otherwise; 5 lock held
    any    : 2 unknown arguments. No exit code means "import".
"""
from __future__ import annotations

import contextlib
import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import socket
import sys
import tempfile
import zipfile
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.dont_write_bytecode = True  # read-only runs must not leave .pyc files

CEDAR = Path(__file__).resolve().parent.parent
STEM = "1188_import_chatgpt_r7_business_register"
ZIP_SHA256 = "1e1b3a1d703ebbb15f5693729855c7e523b2b74676abb645e64da0ae94375870"
R7_DIR = "Cedar_Tribal_Review_R7_2026-09-14/"
EXPECTED_PREFIX = "Cedar_Complete_Handoff_2026-09-14/" + R7_DIR
RULES_VERSION = "1188-rules-2026-09-14.r3"
MANIFEST_SCHEMA = "cedar.r7.audit_bundle_manifest.v3"
MANIFEST_SCHEMA_V2 = "cedar.r7.audit_bundle_manifest.v2"  # historical bundles only
NOTES_SCHEMA = "cedar.r7.owner_notes.v1"
POINTER_SCHEMA = "cedar.r7.audit_current_pointer.v1"
DECISIONS_SCHEMA = "cedar.r7.owner_decisions.v2"
FREEZE_NOTE = "freeze exit 0 means audit artifacts were written; it is not import approval"
EXIT_NOT_APPROVED, EXIT_TRANSACTION, EXIT_CORRUPT, EXIT_LOCKED = 10, 3, 4, 5
EXIT_NO_STORE, EXIT_SNAPSHOT_STALE = 6, 11


@dataclass(frozen=True)
class Paths:
    zip: Path
    register: Path
    types: Path
    ledger: Path
    identity_code: Path
    policy_code: Path
    decisions: Path
    audit_dir: Path
    notes: Path


PROD = Paths(
    zip=CEDAR / "data/external/Cedar_Complete_Data_and_Claude_Handoff_2026-09-14.zip",
    register=CEDAR / "data/spine/cedar_identity_register.csv",
    types=CEDAR / "data/spine/cedar_entity_types.csv",
    ledger=CEDAR / "data/clean/cedar_identifier_ledger_final.csv",
    identity_code=CEDAR / "code/503_identity.py",
    policy_code=CEDAR / "code/cedar_domain.py",
    decisions=CEDAR / "docs/imports/R7_OWNER_DECISIONS.json",
    audit_dir=CEDAR / "docs/imports/r7_audit",
    notes=CEDAR / "docs/imports/R7_OWNER_NOTES.json",
)

FILES = {
    "registries/Cedar_Business_Register.csv": [
        "cedar_uid", "business_uid", "business_name", "dataset_membership", "owner_cedar_uid",
        "affiliated_native_entity_uids", "chartering_native_entity_uids", "native_entity_uid",
        "resolved_business_uid", "active_record", "record_status_R7"],
    "registries/Cedar_Business_Active_Register.csv": [
        "cedar_uid", "business_uid", "business_name", "dataset_membership", "owner_cedar_uid",
        "resolved_business_uid", "active_record"],
    "registries/Business_ID_Lineage_R7.csv": ["retired_business_uid", "surviving_business_uid", "kind"],
    "registries/Legacy_Business_ID_Crosswalk.csv": [
        "legacy_business_id", "business_uid", "mapping_status", "resolved_business_uid"],
    "registries/Business_Native_Relationships.csv": [
        "relationship_id", "business_uid", "cedar_uid", "relationship_type", "resolved_business_uid"],
    "registries/Business_Parent_Business_Relationships.csv": [
        "child_business_uid", "parent_business_uid", "relationship_type"],
    "registries/Business_Identifier_Assertions.csv": [
        "identifier_assertion_id", "business_uid", "identifier_type", "identifier_value", "resolved_business_uid"],
    "registries/Business_Registration_Pairs.csv": ["business_uid", "uei", "cage_code", "resolved_business_uid"],
    "registries/Business_Entity_Equivalences.csv": [
        "cedar_uid", "business_uid", "equivalence_scope", "resolved_business_uid"],
    "registries/Institution_Observation_Links.csv": ["observation_id", "cedar_uid"],
    "registries/Native_Entity_Identifier_Assertions.csv": ["cedar_uid", "identifier_type", "identifier_value"],
    "registries/Native_Entity_Relationships_Append.csv": ["parent_cedar_uid", "child_cedar_uid", "relationship_type"],
    "registries/Cedar_Entity_Register.csv": ["cedar_uid", "canonical_name", "entity_class", "register_status"],
}
LIVE_REQUIRED = {
    "register": ["cedar_uid", "canonical_name", "entity_class"],
    "types": ["type_code", "statutory_basis"],
    "ledger": ["identifier_type", "identifier", "cedar_uid", "canonical_name", "legal_business_name",
               "attribution_method", "confidence_tier", "tier_rationale", "evidence_url", "verified_date",
               "method_quarantined", "quarantine_disposition", "evidence_url_integrity", "exclusion_id"],
}
REG = "registries/Cedar_Business_Register.csv"
ACT = "registries/Cedar_Business_Active_Register.csv"
LIN = "registries/Business_ID_Lineage_R7.csv"
XWK = "registries/Legacy_Business_ID_Crosswalk.csv"
EQV = "registries/Business_Entity_Equivalences.csv"
IDA = "registries/Business_Identifier_Assertions.csv"
ENT = "registries/Cedar_Entity_Register.csv"

QUEUE_COLUMNS = [
    "pair_key", "owner_note_snapshot", "resolution_status", "decision_status", "decision_id", "owner_disposition",
    "owner_decided_by", "owner_decided_on", "evidence_fingerprint", "generated_assessment", "cedar_uid",
    "entity_name", "entity_class", "business_uid", "business_name", "business_identifiers",
    "relationship_meaning", "evidence_urls", "evidence_status", "supporting_ledger_rows_json",
    "verification_protocol"]
DECISION_COLUMNS = ["resolution_status", "decision_status", "decision_id", "owner_disposition",
                    "owner_decided_by", "owner_decided_on"]
# The layout of queues inside historical v2 bundles (read-only; never regenerated).
QUEUE_COLUMNS_V2 = ["pair_key", "YOUR_NOTES"] + QUEUE_COLUMNS[2:]

EXPECTED_NEW_CES = {"CE-001VX-SE", "CE-001VY-Z7"}
GATE_CODES = {"cb_id_format": "G04", "business_name_publication": "G05", "ship_bars": "G06"}
ALL_GATES = ["G00", "G01", "G02", "G03", "G04", "G05", "G06"]
INTEGRITY_CODES = [f"I{n:02d}" for n in range(1, 13)]
DISPOSITIONS = {"CONFIRMED_SAME_LEGAL_OBJECT", "REFUSED_NOT_SAME_LEGAL_OBJECT"}
R7_CB_RE = re.compile(r"^CB-\d{7}$")
LEGACY_CB_RE = re.compile(r"^CB-\d{6}-[0-9A-Z]{2}$")
CE_RE = re.compile(r"^CE-[0-9A-Z]{5}-[0-9A-Z]{2}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DECISION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
BUNDLE_ID_RE = re.compile(r"^[0-9a-f]{24}$")
PAIR_KEY_RE = re.compile(r"^CE-[0-9A-Z]{5}-[0-9A-Z]{2}\|CB-\d{7}$")
TXID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
ENTITY_COLS = {"cedar_uid", "owner_cedar_uid", "native_entity_uid", "affiliated_native_entity_uids",
               "chartering_native_entity_uids", "parent_cedar_uid", "child_cedar_uid"}
BUSINESS_COLS = {"business_uid", "resolved_business_uid", "retired_business_uid",
                 "surviving_business_uid", "child_business_uid", "parent_business_uid"}
ANCSA_BASIS = re.compile(r"43 U\.S\.C\. 160[67]")


class Refused(Exception):
    """An operation that would lose, overwrite or misstate something is refused."""


# =================================================================== reading
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path):
    return sha256_bytes(p.read_bytes()) if p.exists() else None


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def rel(p: Path) -> str:
    p = Path(p).resolve()
    try:
        return p.relative_to(CEDAR).as_posix()
    except ValueError:
        return p.as_posix()


def parse_csv(data: bytes):
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"), newline="")))
    return {"header": rows[0] if rows else [], "rows": rows[1:]}


def dicts(table):
    return [dict(zip(table["header"], r)) for r in table["rows"]]


def col(table, name):
    i = table["header"].index(name)
    return [r[i] for r in table["rows"]]


def tokens(value):
    return [x.strip() for x in re.split(r"\s*[|;,]\s*", value or "") if x.strip()]


def select_members(names, f):
    """(exact expected member hits, other members that could be mistaken for it)."""
    exact = [k for k, n in enumerate(names) if n == EXPECTED_PREFIX + f]
    ambiguous = [n for n in names if n != EXPECTED_PREFIX + f and n.endswith("/" + R7_DIR + f)]
    return exact, ambiguous


def load(paths: Paths = PROD):
    t = {"paths": paths, "zip_sha": sha256_file(paths.zip), "all_member_names": [], "members": {},
         "ambiguous": {}, "member_sha": {}, "raw": {}, "live_sha": {}, "code_sha": {}}
    if paths.zip.exists():
        with zipfile.ZipFile(paths.zip) as z:
            infos = z.infolist()
            names = [i.filename for i in infos]
            t["all_member_names"] = names
            for f in FILES:
                exact, ambiguous = select_members(names, f)
                t["members"][f] = [names[k] for k in exact]
                t["ambiguous"][f] = ambiguous
                if len(exact) == 1:
                    b = z.open(infos[exact[0]]).read()
                    t["member_sha"][f] = sha256_bytes(b)
                    t["raw"][f] = parse_csv(b)
    for key in ("register", "types", "ledger"):
        b = getattr(paths, key).read_bytes()
        t["raw"]["live:" + key] = parse_csv(b)
        t["live_sha"][key] = sha256_bytes(b)
    t["code_sha"] = {"tool": sha256_file(Path(__file__).resolve()),
                     "identity_code": sha256_file(paths.identity_code),
                     "policy_code": sha256_file(paths.policy_code)}
    t["writer_publishes_names"] = writer_publishes_names(paths.policy_code)
    return refresh_decisions(t)


def refresh_decisions(t):
    """Re-read both owner inputs (decisions and notes)."""
    t = dict(t)
    p = t["paths"]
    t["decisions_bytes"] = p.decisions.read_bytes() if p.decisions.exists() else None
    t["notes_bytes"] = p.notes.read_bytes() if p.notes.exists() else None
    return t


def writer_publishes_names(policy_code: Path):
    """The LIVE policy function's answer for a firm name. Not an export test."""
    try:
        spec = importlib.util.spec_from_file_location("cedar_domain_1188", policy_code)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return bool(mod.may_publish_individual_native_field("canonical_name"))
    except Exception:
        return None


def ident_module(paths: Paths = PROD):
    spec = importlib.util.spec_from_file_location("ident503_1188", paths.identity_code)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# =================================================================== URLs
URL_VALID = "VALID_RECORD_URL_NOT_RETRIEVED"


def classify_url(value, integrity_note=""):
    """Structure only; nothing is fetched. Only URL_VALID can support a candidate."""
    v = (value or "").strip()
    if not v:
        return "MISSING"
    if (integrity_note or "").strip():
        return "DOWNGRADED_BY_INTEGRITY_NOTE"
    if re.match(r"^[A-Za-z]:[\\/]", v) or v.startswith(("/", "\\", "~", "file:")):
        return "LOCAL_PATH"
    if any(ch.isspace() for ch in v):
        return "INVALID"
    try:
        parts = urlsplit(v)
        host = parts.hostname or ""
    except ValueError:
        return "INVALID"
    if parts.scheme not in ("http", "https") or not host or "." not in host.strip("."):
        return "INVALID"
    if parts.path in ("", "/") and not parts.query:
        return "HOST_ROOT_ONLY"  # a site or search homepage, not a record
    return URL_VALID


# =================================================================== integrity
REGRESSIONS = [
    # R7 handoff section 7. Only corrections R7 ties to a Cedar id.
    ("Tiny Tots Learning Center is Individual, CB unchanged",
     lambda s: s["issued"].get("CB-1015175", {}).get("dataset_membership") == "Individual"),
    ("WCA Construction belongs to Ute Mountain Ute, not Southern Ute",
     lambda s: s["issued"].get("CB-1017282", {}).get("owner_cedar_uid") == "CE-001BZ-N0"),
    ("Mahota Textiles is tribally owned and in NEED",
     lambda s: s["issued"].get("CB-1000520", {}).get("dataset_membership") == "NEED"),
    ("Native Sun Energy Company is one business object",
     lambda s: sum(1 for r in s["active"].values()
                   if r["business_name"].strip().lower() == "native sun energy company") == 1),
    ("Sacred Circle Gallery is a program, not a business",
     lambda s: not any("sacred circle gallery" in r["business_name"].lower() for r in s["issued"].values())),
    ("Wasi-siw Land Trust has its own CE, not Washoe's",
     lambda s: s["r7_entities"].get("CE-001VX-SE", {}).get("entity_class") == "Native nonprofit"
     and s["r7_entities"].get("CE-001C1-62", {}).get("canonical_name") == "Washoe"),
    ("Cherokee Elite duplicate resolves through lineage, not deletion",
     lambda s: s["issued"].get("CB-1014755", {}).get("resolved_business_uid") == "CB-1004356"
     and "CB-1014755" not in s["active"]),
]


def _dups(values):
    seen, dup = set(), set()
    for v in values:
        (dup if v in seen else seen).add(v)
    return sorted(dup)


def integrity(t, i02):
    """Raw-row checks first; nothing is keyed until uniqueness is proven.
    Returns (checks, state); state is None when keyed checks cannot run."""
    res = []

    def rec(code, ok, detail=""):
        res.append((code, bool(ok), detail))

    rec("I01", t["zip_sha"] == ZIP_SHA256, f"zip sha {str(t['zip_sha'])[:12]}")
    rec("I02", i02[0], i02[1])
    dup_members = _dups(t["all_member_names"])
    bad = {f: (len(h), t["ambiguous"].get(f, [])) for f, h in t["members"].items()
           if len(h) != 1 or t["ambiguous"].get(f)}
    rec("I03", not dup_members and not bad and len(t["members"]) == len(FILES),
        "each expected file is exactly one expected ZIP member, none ambiguous"
        if not (dup_members or bad) else f"duplicate member names {dup_members[:3]}; bad selection {bad}")
    structural = []
    for name, need in list(FILES.items()) + [("live:" + k, v) for k, v in LIVE_REQUIRED.items()]:
        tab = t["raw"].get(name)
        if tab is None:
            structural.append((name, "unreadable"))
            continue
        h = tab["header"]
        if len(h) != len(set(h)):
            structural.append((name, "duplicate header names"))
        missing = [c for c in need if c not in h]
        if missing:
            structural.append((name, f"missing required columns {missing}"))
        ragged = sum(1 for r in tab["rows"] if len(r) != len(h))
        if ragged:
            structural.append((name, f"{ragged} rows with the wrong number of fields"))
    rec("I04", not structural, f"{len(structural)} structural faults, e.g. {structural[:3]}")
    later = INTEGRITY_CODES[4:]
    if structural or bad:
        for code in later:
            rec(code, False, "not evaluated: structure failed")
        return res, None

    raw = t["raw"]
    dup_r7_ce, dup_live_ce = _dups(col(raw[ENT], "cedar_uid")), _dups(col(raw["live:register"], "cedar_uid"))
    rec("I05", not dup_r7_ce and not dup_live_ce, f"duplicate cedar_uid rows: R7 {dup_r7_ce[:3]}, live {dup_live_ce[:3]}")
    issued_ids, active_ids = col(raw[REG], "business_uid"), col(raw[ACT], "business_uid")
    bad_fmt = [u for u in issued_ids + active_ids if not R7_CB_RE.match(u)]
    dup_i, dup_a = _dups(issued_ids), _dups(active_ids)
    rec("I06", not bad_fmt and not dup_i and not dup_a,
        f"{len(issued_ids)} issued; duplicate issued {dup_i[:3]} active {dup_a[:3]}; bad format {bad_fmt[:3]}")
    if bad_fmt or dup_i or dup_a or dup_r7_ce or dup_live_ce:
        for code in later[2:]:
            rec(code, False, "not evaluated: duplicate keys")
        return res, None

    s = {"issued": {r["business_uid"]: r for r in dicts(raw[REG])},
         "active": {r["business_uid"]: r for r in dicts(raw[ACT])},
         "r7_entities": {r["cedar_uid"]: r for r in dicts(raw[ENT])},
         "live": {r["cedar_uid"]: r for r in dicts(raw["live:register"])},
         "tables": {f: dicts(raw[f]) for f in FILES}}
    lineage = s["tables"][LIN]
    retired = [r["retired_business_uid"] for r in lineage]
    shared = [c for c in raw[ACT]["header"] if c in raw[REG]["header"]]
    contradictions = [(u, c) for u, a in s["active"].items() if u in s["issued"]
                      for c in shared if s["issued"][u][c] != a[c]]
    not_issued = [u for u in s["active"] if u not in s["issued"]]
    rec("I07", not contradictions and not not_issued and set(s["active"]) == set(s["issued"]) - set(retired)
        and all(r["active_record"] == "1" for r in s["active"].values()),
        f"active {len(s['active'])} = issued {len(s['issued'])} - retired {len(set(retired))}; "
        f"shared-field contradictions {contradictions[:2]}; not issued {not_issued[:2]}")
    dup_ret = _dups(retired)
    surviving = {r["surviving_business_uid"] for r in lineage}
    malformed = [r for r in lineage if r["retired_business_uid"] not in s["issued"]
                 or r["surviving_business_uid"] not in s["active"]
                 or s["issued"][r["retired_business_uid"]]["resolved_business_uid"] != r["surviving_business_uid"]]
    chained = sorted(set(retired) & surviving)
    rec("I08", not dup_ret and not malformed and not chained,
        f"duplicate retirement mappings {dup_ret[:3]}; malformed {len(malformed)}; chained {chained[:3]}")
    unresolved, mixed = [], []
    for name, rows in s["tables"].items():
        if name == ENT:
            continue
        for r in rows:
            for c in BUSINESS_COLS & set(r):
                for tok in tokens(r[c]):
                    if not R7_CB_RE.match(tok):
                        mixed.append((name, c, tok))
                    elif tok not in s["issued"]:
                        unresolved.append((name, c, tok))
            if name != XWK and r.get("resolved_business_uid") and r["resolved_business_uid"] not in s["active"]:
                unresolved.append((name, "resolved(not active)", r["resolved_business_uid"]))
            for c in ENTITY_COLS & set(r):
                for tok in tokens(r[c]):
                    if not CE_RE.match(tok) or tok not in s["r7_entities"]:
                        mixed.append((name, c, tok))
    for r in s["tables"][XWK]:
        if r["mapping_status"] == "resolved" and r["resolved_business_uid"] not in s["active"]:
            unresolved.append((XWK, "resolved", r["resolved_business_uid"]))
        if not LEGACY_CB_RE.match(r["legacy_business_id"]) or r["legacy_business_id"] in s["issued"]:
            mixed.append((XWK, "legacy_business_id", r["legacy_business_id"]))
    rec("I09", not unresolved, f"{len(unresolved)} unresolved, e.g. {unresolved[:3]}")
    rec("I10", not mixed, f"{len(mixed)} namespace violations, e.g. {mixed[:3]}")
    nameless = [u for u, r in s["issued"].items() if not r["business_name"].strip()]
    nameless += [u for u, r in s["r7_entities"].items() if not r["canonical_name"].strip()]
    rec("I11", not nameless, f"{len(nameless)} nameless, e.g. {nameless[:3]}")
    failed = []
    for label, fn in REGRESSIONS:
        try:
            if not fn(s):
                failed.append(label)
        except Exception:
            failed.append(label)
    rec("I12", not failed, f"regressed: {failed}")
    return res, s


# =================================================================== evidence
FORM = {"inc": "incorporated", "corp": "corporation", "ltd": "limited", "co": "company"}
CANDIDATE = "CANDIDATE_EVIDENCE_REGISTRANT_NAME_MATCHES_UNRESOLVED"
WEAK = "WEAK_OR_INSUFFICIENT_EVIDENCE_ONLY"
CONFLICT = "CONFLICT_ATTRIBUTED_TO_OTHER_ENTITY"


def _legal(name):
    words = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower().replace("&", " and ")).split()
    return " ".join(FORM.get(w, w) for w in words)


def grade_ledger_row(row, cedar_uid, entity_name):
    """What one attribution row can contribute. Never 'same legal object'."""
    tier = (row.get("confidence_tier") or "").strip().upper()
    quarantined = (row.get("method_quarantined") or "").strip().upper() in ("Y", "YES", "TRUE", "1")
    qdisp = (row.get("quarantine_disposition") or "").strip().upper()
    if tier == "X" or (row.get("exclusion_id") or "").strip():
        return "REFUTED_OR_EXCLUDED"
    if qdisp in ("WITHDRAW", "HOLD", "REPOINT"):
        return f"QUARANTINE_{qdisp}"
    if row.get("cedar_uid") != cedar_uid:
        return "ATTRIBUTED_TO_OTHER_ENTITY" if tier in ("A", "B") and not quarantined \
            else "WEAK_ATTRIBUTION_TO_OTHER_ENTITY"
    if quarantined:
        return "QUARANTINED_METHOD_KEEP"
    if tier != "A":
        return f"TIER_{tier or 'BLANK'}_ATTRIBUTION"
    url = classify_url(row.get("evidence_url"), row.get("evidence_url_integrity"))
    if url != URL_VALID:
        return f"TIER_A_ATTRIBUTION_EVIDENCE_URL_{url}"
    if _legal(row.get("legal_business_name")) and _legal(row.get("legal_business_name")) == _legal(entity_name):
        return "TIER_A_ATTRIBUTION_REGISTRANT_NAME_MATCHES_ENTITY"
    return "TIER_A_ATTRIBUTION_REGISTRANT_NAME_DIFFERS"


def assess_pair(ids, rows, cedar_uid, entity_name):
    if not ids:
        return "NO_IDENTIFIER_ON_BUSINESS"
    if not rows:
        return "IDENTIFIER_NOT_IN_LEDGER"
    grades = {grade_ledger_row(r, cedar_uid, entity_name) for r in rows}
    if "ATTRIBUTED_TO_OTHER_ENTITY" in grades:
        return CONFLICT
    if "TIER_A_ATTRIBUTION_REGISTRANT_NAME_MATCHES_ENTITY" in grades:
        return CANDIDATE
    if grades <= {"REFUTED_OR_EXCLUDED"}:
        return "ATTRIBUTION_REFUTED_OR_EXCLUDED"
    return WEAK


def pair_views(t, s):
    """Everything about each proposed pair that a reviewer's decision depends on."""
    types = {r["type_code"]: r for r in dicts(t["raw"]["live:types"])}
    ancsa = {c for c, r in types.items() if ANCSA_BASIS.search(r["statutory_basis"] or "")}
    ledger = {}
    for r in dicts(t["raw"]["live:ledger"]):
        k = ((r["identifier_type"] or "").strip().upper(), (r["identifier"] or "").strip().upper())
        if k[0] in ("UEI", "CAGE"):
            ledger.setdefault(k, []).append(r)
    biz_ids = {}
    for r in s["tables"][IDA]:
        if r["identifier_type"] in ("UEI", "CAGE"):
            biz_ids.setdefault(r["resolved_business_uid"], set()).add(
                (r["identifier_type"], r["identifier_value"].strip().upper()))
    views = []
    for e in s["tables"][EQV]:
        ce, cb = e["cedar_uid"], e["business_uid"]
        ent = s["live"].get(ce) or s["r7_entities"].get(ce) or {}
        ids = sorted(biz_ids.get(cb, set()))
        rows = sorted((r for i in ids for r in ledger.get(i, [])), key=canonical)
        if ent.get("entity_class") not in ancsa:
            assessment = "REFUSED_BY_TOOL_ENTITY_NOT_AN_ANCSA_CLASS"
        elif cb not in s["active"]:
            assessment = "REFUSED_BY_TOOL_BUSINESS_NOT_ACTIVE"
        else:
            assessment = assess_pair(set(ids), rows, ce, ent.get("canonical_name"))
        basis = {"rules_version": RULES_VERSION, "pair": [ce, cb],
                 "entity": {k: ent.get(k, "") for k in ("cedar_uid", "canonical_name", "entity_class")},
                 "entity_class_statutory_basis": types.get(ent.get("entity_class"), {}).get("statutory_basis", ""),
                 "business": s["issued"].get(cb, {}), "proposal": e, "business_identifiers": ids,
                 "ledger_rows": rows,
                 "url_classes": [classify_url(r["evidence_url"], r["evidence_url_integrity"]) for r in rows]}
        views.append({"key": f"{ce}|{cb}", "ce": ce, "cb": cb, "entity": ent, "ids": ids, "rows": rows,
                      "assessment": assessment, "fingerprint": sha256_bytes(canonical(basis).encode("utf-8"))})
    return views


# =================================================================== decisions
GATE_KEYS = {"decision_id", "status", "value", "decided_by", "decided_on", "basis", "supersedes"}
PAIR_KEYS = {"decision_id", "cedar_uid", "business_uid", "disposition", "evidence_fingerprint",
             "decided_by", "decided_on", "basis", "supersedes"}
EMPTY_DECISIONS = {"gate_heads": {}, "pairs": {}, "records": {}, "snapshot": [],
                   "counts": {"current": 0, "stale": 0, "superseded": 0, "historical": 0}}


def _no_dup_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate JSON key {k!r}")
        out[k] = v
    return out


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def _past_or_today(v, today):
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return "must be YYYY-MM-DD"
    try:
        d = date.fromisoformat(v)
    except ValueError:
        return "is not a real date"
    return "is in the future" if d > today else None


def load_decisions(decisions_bytes, views, today, prior_records=None):
    """(state, errors). Invalid input never yields a partial state."""
    if decisions_bytes is None:
        errs = [f"decision {i} recorded in the current bundle is missing from the decisions file"
                for i in sorted(prior_records or {})]
        return copy.deepcopy(EMPTY_DECISIONS), errs
    try:
        d = json.loads(decisions_bytes.decode("utf-8"), object_pairs_hook=_no_dup_keys)
    except Exception as e:
        return copy.deepcopy(EMPTY_DECISIONS), [f"not valid JSON: {e}"]
    if not isinstance(d, dict) or set(d) != {"schema", "gates", "proposed_equivalence_pairs"}:
        return copy.deepcopy(EMPTY_DECISIONS), ["top level must be exactly {schema, gates, proposed_equivalence_pairs}"]
    errs = [] if d["schema"] == DECISIONS_SCHEMA else [f"schema must be {DECISIONS_SCHEMA!r}"]
    records = {}  # decision_id -> (subject, record)

    def common(where, r, keys):
        if not isinstance(r, dict) or set(r) != keys:
            errs.append(f"{where}: keys must be exactly {sorted(keys)}")
            return False
        ok = True
        if not isinstance(r["decision_id"], str) or not DECISION_ID_RE.match(r["decision_id"]):
            errs.append(f"{where}: malformed decision_id {r['decision_id']!r}"); ok = False
        elif r["decision_id"] in records:
            errs.append(f"{where}: decision_id {r['decision_id']} used twice"); ok = False
        for k in ("decided_by", "basis"):
            if not _text(r[k]):
                errs.append(f"{where}: {k} must be non-empty text"); ok = False
        problem = _past_or_today(r["decided_on"], today)
        if problem:
            errs.append(f"{where}: decided_on {r['decided_on']!r} {problem}"); ok = False
        if r["supersedes"] is not None and not isinstance(r["supersedes"], str):
            errs.append(f"{where}: supersedes must be null or a decision_id"); ok = False
        return ok

    if not isinstance(d["gates"], dict):
        errs.append("gates must be an object")
    else:
        for name, recs in d["gates"].items():
            if name not in GATE_CODES:
                errs.append(f"unknown gate {name!r}"); continue
            if not isinstance(recs, list):
                errs.append(f"gate {name}: must be a list of decisions"); continue
            for i, r in enumerate(recs):
                where = f"gate {name} #{i}"
                if not common(where, r, GATE_KEYS):
                    continue
                if not isinstance(r["status"], str) or r["status"] not in ("APPROVED", "NOT_APPROVED"):
                    errs.append(f"{where}: status must be the string APPROVED or NOT_APPROVED, got {r['status']!r}"); continue
                if not _text(r["value"]):
                    errs.append(f"{where}: value must be non-empty text"); continue
                records[r["decision_id"]] = (("gate", name), r)
    if not isinstance(d["proposed_equivalence_pairs"], list):
        errs.append("proposed_equivalence_pairs must be a list")
    else:
        for i, r in enumerate(d["proposed_equivalence_pairs"]):
            where = f"proposed pair decision #{i}"
            if not common(where, r, PAIR_KEYS):
                continue
            if not (isinstance(r["cedar_uid"], str) and CE_RE.match(r["cedar_uid"])
                    and isinstance(r["business_uid"], str) and R7_CB_RE.match(r["business_uid"])):
                errs.append(f"{where}: malformed ids"); continue
            if not isinstance(r["disposition"], str) or r["disposition"] not in DISPOSITIONS:
                errs.append(f"{where}: disposition must be one of {sorted(DISPOSITIONS)}, got {r['disposition']!r}"); continue
            if not isinstance(r["evidence_fingerprint"], str) or not HEX64.match(r["evidence_fingerprint"]):
                errs.append(f"{where}: evidence_fingerprint must be the 64-hex value from the queue"); continue
            records[r["decision_id"]] = (("pair", f"{r['cedar_uid']}|{r['business_uid']}"), r)

    children = {}
    for did, (subject, r) in records.items():
        sup = r["supersedes"]
        if sup is None:
            continue
        if sup == did or sup not in records:
            errs.append(f"decision {did}: supersedes unknown decision {sup!r}"); continue
        if records[sup][0] != subject:
            errs.append(f"decision {did}: supersedes a decision about a different subject"); continue
        if records[sup][1]["decided_on"] > r["decided_on"]:
            errs.append(f"decision {did}: supersedes a later-dated decision"); continue
        children.setdefault(sup, []).append(did)
    for sup, kids in children.items():
        if len(kids) > 1:
            errs.append(f"decision {sup} is superseded by {sorted(kids)}: history must be one chain")
    for did in records:  # cycles
        seen, cur = set(), did
        while cur is not None and cur in records:
            if cur in seen:
                errs.append(f"decision {did}: supersession cycle"); break
            seen.add(cur)
            cur = records[cur][1]["supersedes"]
    heads = {}
    for did, (subject, _) in records.items():
        if did not in children:
            heads.setdefault(subject, []).append(did)
    for subject, ids in heads.items():
        if len(ids) > 1:
            errs.append(f"{subject[1]} has {len(ids)} undecided-between decisions {sorted(ids)}; "
                        f"a later decision must name the one it supersedes")
    digests = {did: sha256_bytes(canonical(r).encode("utf-8")) for did, (_, r) in records.items()}
    for did, digest in sorted((prior_records or {}).items()):
        if digests.get(did) != digest:
            errs.append(f"decision {did} recorded in the current bundle was removed or altered; history is append-only")
    if errs:
        return copy.deepcopy(EMPTY_DECISIONS), errs

    fp = {v["key"]: v["fingerprint"] for v in views}
    state = copy.deepcopy(EMPTY_DECISIONS)
    state["records"] = digests
    for subject, (did,) in heads.items():
        r = records[did][1]
        if subject[0] == "gate":
            state["gate_heads"][subject[1]] = r
        elif subject[1] not in fp:
            state["counts"]["historical"] += 1
        else:
            status = "CURRENT" if r["evidence_fingerprint"] == fp[subject[1]] else "STALE"
            state["pairs"][subject[1]] = {"record": r, "status": status}
            state["counts"]["current" if status == "CURRENT" else "stale"] += 1
    head_ids = {ids[0] for ids in heads.values()}
    for did in sorted(records):
        (kind, subj), r = records[did]
        if kind == "gate":
            status = "GATE_HEAD" if did in head_ids else "GATE_SUPERSEDED"
        elif did not in head_ids:
            status = "SUPERSEDED"
        elif subj not in fp:
            status = "HISTORICAL"
        else:
            status = state["pairs"][subj]["status"]
        state["snapshot"].append({"decision_id": did, "kind": kind, "subject": subj, "status": status, "record": r})
    state["counts"]["superseded"] = sum(1 for x in state["snapshot"] if x["status"] == "SUPERSEDED")
    return state, []


NOTE_KEYS = {"pair_key", "note", "updated_by", "updated_on"}
EMPTY_NOTES = {"notes": {}, "historical": {}}


def load_notes(notes_bytes, pair_keys, today):
    """(notes, errors). Commentary only: a note never resolves a pair or opens a gate."""
    if notes_bytes is None:
        return copy.deepcopy(EMPTY_NOTES), []
    try:
        d = json.loads(notes_bytes.decode("utf-8"), object_pairs_hook=_no_dup_keys)
    except Exception as e:
        return copy.deepcopy(EMPTY_NOTES), [f"notes file is not valid JSON: {e}"]
    if not isinstance(d, dict) or set(d) != {"schema", "notes", "historical_notes"}:
        return copy.deepcopy(EMPTY_NOTES), ["notes file top level must be exactly {schema, notes, historical_notes}"]
    errs = [] if d["schema"] == NOTES_SCHEMA else [f"notes schema must be {NOTES_SCHEMA!r}"]
    out = copy.deepcopy(EMPTY_NOTES)
    for listname, bucket, proposed in (("notes", "notes", True), ("historical_notes", "historical", False)):
        recs = d[listname]
        if not isinstance(recs, list):
            errs.append(f"{listname} must be a list")
            continue
        for i, r in enumerate(recs):
            where = f"{listname} #{i}"
            if not isinstance(r, dict) or set(r) != NOTE_KEYS:
                errs.append(f"{where}: keys must be exactly {sorted(NOTE_KEYS)}")
                continue
            k = r["pair_key"]
            if not isinstance(k, str) or not PAIR_KEY_RE.match(k):
                errs.append(f"{where}: malformed pair_key {k!r}")
                continue
            if k in out["notes"] or k in out["historical"]:
                errs.append(f"{where}: pair_key {k} has more than one note")
                continue
            if not _text(r["note"]) or not _text(r["updated_by"]):
                errs.append(f"{where}: note and updated_by must be non-empty text (delete the entry to remove a note)")
                continue
            problem = _past_or_today(r["updated_on"], today)
            if problem:
                errs.append(f"{where}: updated_on {r['updated_on']!r} {problem}")
                continue
            if proposed and k not in pair_keys:
                errs.append(f"{where}: {k} is not a proposed pair; move its note to historical_notes")
                continue
            if not proposed and k in pair_keys:
                errs.append(f"{where}: {k} is still a proposed pair; keep its note under notes")
                continue
            out[bucket][k] = r
    return (out if not errs else copy.deepcopy(EMPTY_NOTES)), errs


def notes_snapshot(notes):
    return {"notes": [notes["notes"][k] for k in sorted(notes["notes"])],
            "historical_notes": [notes["historical"][k] for k in sorted(notes["historical"])]}


# =================================================================== queue rows, gates, evaluation
def queue_rows(views, decisions, notes):
    out = []
    for v in views:
        head = decisions["pairs"].get(v["key"])
        r = head["record"] if head else {}
        status = head["status"] if head else ""
        resolution = "UNRESOLVED"
        if status == "CURRENT":
            resolution = {"CONFIRMED_SAME_LEGAL_OBJECT": "OWNER_CONFIRMED",
                          "REFUSED_NOT_SAME_LEGAL_OBJECT": "OWNER_REFUSED"}[r["disposition"]]
        elif status == "STALE":
            resolution = "UNRESOLVED_STALE_DECISION"
        name = v["entity"].get("canonical_name", "")
        out.append({
            "pair_key": v["key"], "owner_note_snapshot": notes["notes"].get(v["key"], {}).get("note", ""),
            "resolution_status": resolution, "decision_status": status,
            "decision_id": r.get("decision_id", ""), "owner_disposition": r.get("disposition", ""),
            "owner_decided_by": r.get("decided_by", ""), "owner_decided_on": r.get("decided_on", ""),
            "evidence_fingerprint": v["fingerprint"], "generated_assessment": v["assessment"],
            "cedar_uid": v["ce"], "entity_name": name, "entity_class": v["entity"].get("entity_class", ""),
            "business_uid": v["cb"], "business_name": "",  # filled by caller
            "business_identifiers": " | ".join(f"{k}:{x}" for k, x in v["ids"]),
            "relationship_meaning": " | ".join(
                f"{x['cedar_uid'] or '(none)'} via {x['attribution_method']} tier {x['confidence_tier']}: "
                f"{grade_ledger_row(x, v['ce'], name)}" for x in v["rows"])
                or "no ledger row; the ledger records attribution, never legal identity",
            "evidence_urls": " | ".join(sorted({x["evidence_url"] for x in v["rows"] if x["evidence_url"]})),
            "evidence_status": " | ".join(
                f"{x['identifier_type']}:{x['identifier']} url={classify_url(x['evidence_url'], x['evidence_url_integrity'])}"
                f" quarantined={x['method_quarantined'] or '-'}/{x['quarantine_disposition'] or '-'}"
                f" excluded={'YES' if (x['exclusion_id'] or '').strip() else 'no'}" for x in v["rows"]),
            "supporting_ledger_rows_json": json.dumps(v["rows"], ensure_ascii=False, sort_keys=True),
            "verification_protocol": _protocol(v["ids"], name),
        })
    return sorted(out, key=lambda r: (r["generated_assessment"], r["entity_name"], r["pair_key"]))


def _protocol(ids, entity_name):
    cage = next((x for k, x in ids if k == "CAGE"), "")
    uei = next((x for k, x in ids if k == "UEI"), "")
    if cage:
        return f"cage.dla.mil: paste CAGE {cage}; expect the registrant to be {entity_name} itself, not a subsidiary or parent"
    if uei:
        return f"sam.gov entity search: paste UEI {uei}; expect the legal business name {entity_name} itself"
    return f"Alaska corporations search: look up {entity_name}; confirm the business record names that corporation itself"


def gates(t, s, ident, decisions, decision_errors, rows):
    res = []

    def rec(code, is_open, detail):
        res.append((code, bool(is_open), detail))

    rec("G00", not decision_errors,
        ("decisions file absent (no decisions yet)" if t["decisions_bytes"] is None else "decisions file valid")
        if not decision_errors else f"INVALID: {decision_errors[:3]}")
    live, ent = s["live"], s["r7_entities"]
    drift = [(u, c) for u, r in live.items() for c, v in r.items() if ent.get(u, {}).get(c) != v]
    rec("G01", not drift, f"{len(drift)} live fields differ in R7, e.g. {drift[:3]}")

    def ordinal(uid):
        n = 0
        for ch in uid.split("-")[1]:
            n = n * 32 + ident.B32.index(ch)
        return n
    extra = set(ent) - set(live)
    base = max(ordinal(u) for u in live)
    want = sorted(extra, key=ordinal)
    seq = [ordinal(u) for u in want] == list(range(base + 1, base + 1 + len(want)))
    rec("G02", extra == EXPECTED_NEW_CES and all(ident.valid(u) for u in extra) and seq,
        f"new {sorted(extra)} next-in-sequence={seq} (reported, never appended)")
    c = decisions["counts"]
    unresolved = sum(1 for r in rows if not r["resolution_status"].startswith("OWNER_"))
    rec("G03", not decision_errors and unresolved == 0,
        f"{len(rows) - unresolved} of {len(rows)} proposed equivalence pairs carry a CURRENT owner disposition; "
        f"{unresolved} UNRESOLVED (decisions: current {c['current']}, stale {c['stale']}, "
        f"superseded {c['superseded']}, historical {c['historical']})")
    for name, code in GATE_CODES.items():
        g = decisions["gate_heads"].get(name)
        ok = not decision_errors and g is not None and g["status"] == "APPROVED"
        detail = (f"owner: {g['status']} ({g['decision_id']}) by {g['decided_by']} on {g['decided_on']}: {g['value']}"
                  if g else "owner: no decision recorded")
        if name == "business_name_publication":
            live_ok = t["writer_publishes_names"] is True
            ok = ok and live_ok
            detail += (f"; live policy function may_publish_individual_native_field('canonical_name') = "
                       f"{t['writer_publishes_names']} (checks the function, not an export)")
        rec(code, ok, detail)
    return res


def evaluate(t, i02=(True, "no current audit bundle yet"), prior_records=None, ident=None, today=None):
    ident = ident or ident_module(t["paths"])
    today = today or date.today()
    checks, s = integrity(t, i02)
    integ = all(ok for _, ok, _ in checks)
    ev = {"integrity": checks, "integrity_pass": integ, "gates": [], "rows": [], "views": [],
          "decisions": copy.deepcopy(EMPTY_DECISIONS), "decision_errors": [], "state": s, "approval": "NOT_APPROVED",
          "notes": copy.deepcopy(EMPTY_NOTES), "notes_errors": []}
    if s is None:
        return ev
    views = pair_views(t, s)
    decisions, derr = load_decisions(t["decisions_bytes"], views, today, prior_records)
    notes, nerr = load_notes(t.get("notes_bytes"), {v["key"] for v in views}, today)
    rows = queue_rows(views, decisions, notes)
    for r in rows:
        r["business_name"] = s["issued"].get(r["business_uid"], {}).get("business_name", "")
    g = gates(t, s, ident, decisions, derr, rows)
    ev.update(views=views, decisions=decisions, decision_errors=derr, rows=rows, gates=g, notes=notes, notes_errors=nerr,
              approval="APPROVED" if integ and not nerr and all(o for _, o, _ in g) else "NOT_APPROVED")
    return ev


def exit_code(ev):
    """Not permission. 0 only when integrity passes AND every approval is CURRENT."""
    if not ev["integrity_pass"] or ev["decision_errors"] or ev["notes_errors"]:
        return 1
    return 0 if ev["approval"] == "APPROVED" else EXIT_NOT_APPROVED


def ledger_measurements(views):
    """Counts over every ledger row behind the proposed pairs. The last field is a
    stated semantic limitation of the ledger, not a computed result."""
    rows = {canonical(r): (r, v) for v in views for r in v["rows"]}

    def count(fn):
        out = {}
        for r, v in rows.values():
            k = fn(r, v)
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))
    same = [(r, v) for r, v in rows.values() if r["cedar_uid"] == v["ce"]]
    name_match = [(r, v) for r, v in same if _legal(r["legal_business_name"])
                  and _legal(r["legal_business_name"]) == _legal(v["entity"].get("canonical_name"))]
    direct = [(r, v) for r, v in name_match
              if grade_ledger_row(r, v["ce"], v["entity"].get("canonical_name")) == "TIER_A_ATTRIBUTION_REGISTRANT_NAME_MATCHES_ENTITY"]
    assessments = {}
    for v in views:
        assessments[v["assessment"]] = assessments.get(v["assessment"], 0) + 1
    return {
        "proposed_pairs": len(views),
        "generated_assessment": dict(sorted(assessments.items())),
        "ledger_rows": len(rows),
        "identifier_type": count(lambda r, v: r["identifier_type"]),
        "attribution_method": count(lambda r, v: r["attribution_method"] or "(blank)"),
        "confidence_tier": count(lambda r, v: r["confidence_tier"] or "(blank)"),
        "method_quarantined": count(lambda r, v: r["method_quarantined"] or "(blank)"),
        "quarantine_disposition": count(lambda r, v: r["quarantine_disposition"] or "(blank)"),
        "excluded_rows": sum(1 for r, _ in rows.values() if (r["exclusion_id"] or "").strip()),
        "evidence_url_class": count(lambda r, v: classify_url(r["evidence_url"], r["evidence_url_integrity"])),
        "attribution_bindings": len(rows),
        "attributed_to_paired_entity": len(same),
        "attributed_to_other_entity": len(rows) - len(same),
        "registrant_name_equals_paired_entity": len(name_match),
        "tier_a_valid_record_url_registrant_name_match": len(direct),
        "semantic_limitation": "ledger rows are identifier-to-owner attributions; no ledger field records a "
                               "same-legal-object determination, so no row by itself establishes equivalence",
    }


# =================================================================== manifest
MANIFEST_KEYS = {"schema", "rules_version", "tool", "package", "files", "live_inputs", "ledger_provenance",
                 "decisions", "notes", "queue", "integrity", "import_approval", "ledger_measurements", "freeze_note"}
LEDGER_KEYS = set(ledger_measurements([]))
RENDERED_COLS = DECISION_COLUMNS + ["owner_note_snapshot", "evidence_fingerprint"]
SNAPSHOT_STATUSES = {"CURRENT", "STALE", "SUPERSEDED", "HISTORICAL", "GATE_HEAD", "GATE_SUPERSEDED"}
CATEGORIES = ("SCHEMA_INVALID", "SEMANTIC_INVALID", "BUNDLE_CORRUPT", "R7_PACKAGE_MISMATCH",
              "LIVE_INPUT_CHANGED", "DECISIONS_CHANGED", "NOTES_CHANGED", "STALE_ARTIFACT")


def build_manifest(t, ev, qbytes):
    """One evaluation snapshot: every derived block below comes from the same `ev`."""
    p = t["paths"]
    subset = sorted({canonical(r) for v in ev["views"] for r in v["rows"]})
    nsnap = notes_snapshot(ev["notes"])
    return {
        "schema": MANIFEST_SCHEMA,
        "rules_version": RULES_VERSION,
        "tool": {"path": f"code/{STEM}.py", "sha256": t["code_sha"]["tool"]},
        "package": {"zip": p.zip.name, "zip_sha256": ZIP_SHA256, "r7_member_prefix": EXPECTED_PREFIX},
        "files": {f: {"zip_member": t["members"][f][0], "sha256": t["member_sha"][f],
                      "rows": len(t["raw"][f]["rows"]), "columns": t["raw"][f]["header"]} for f in FILES},
        "live_inputs": {
            **{k: {"path": rel(getattr(p, k)), "sha256": t["live_sha"][k],
                   "rows": len(t["raw"]["live:" + k]["rows"]), "columns": t["raw"]["live:" + k]["header"]}
               for k in ("register", "types", "ledger")},
            "identity_code": {"path": rel(p.identity_code), "sha256": t["code_sha"]["identity_code"]},
            "policy_code": {"path": rel(p.policy_code), "sha256": t["code_sha"]["policy_code"]}},
        "ledger_provenance": {"path": rel(p.ledger), "tracked_by_git": False, "sha256": t["live_sha"]["ledger"],
                              "subset_rows": len(subset),
                              "subset_sha256": sha256_bytes(("[" + ",".join(subset) + "]").encode("utf-8")),
                              "subset_carried_in": "queue.csv column supporting_ledger_rows_json"},
        "decisions": {"path": rel(p.decisions), "present": t["decisions_bytes"] is not None,
                      "sha256": sha256_bytes(t["decisions_bytes"]) if t["decisions_bytes"] is not None else None,
                      "snapshot": ev["decisions"]["snapshot"],
                      "records": dict(sorted(ev["decisions"]["records"].items())),
                      "counts": dict(ev["decisions"]["counts"])},
        "notes": {"path": rel(p.notes), "present": t.get("notes_bytes") is not None,
                  "sha256": sha256_bytes(t["notes_bytes"]) if t.get("notes_bytes") is not None else None,
                  "snapshot": nsnap, "snapshot_sha256": sha256_bytes(canonical(nsnap).encode("utf-8"))},
        "queue": {"file": "queue.csv", "sha256": sha256_bytes(qbytes), "rows": len(ev["rows"]), "columns": QUEUE_COLUMNS,
                  "pair_keys": sorted(r["pair_key"] for r in ev["rows"]),
                  "rendered": {r["pair_key"]: {c: r[c] for c in RENDERED_COLS} for r in ev["rows"]}},
        "integrity": {"status": "PASS" if ev["integrity_pass"] else "FAIL",
                      "checks": {c: ok for c, ok, _ in ev["integrity"]}},
        "import_approval": {"status": ev["approval"],
                            "gates": {c: {"open": o, "detail": d} for c, o, d in ev["gates"]},
                            "policy_function_publishes": t["writer_publishes_names"]},
        "ledger_measurements": ledger_measurements(ev["views"]),
        "freeze_note": FREEZE_NOTE,
    }


def validate_manifest(m, t=None, queue_bytes=None):
    """Three layers, reported by category:
    structure (SCHEMA_INVALID) -> internal meaning (SEMANTIC_INVALID) and the bytes it
    describes (BUNDLE_CORRUPT) -> reproducibility against live inputs (the *_CHANGED and
    STALE categories). A historical bundle may be stale without being invalid."""
    errs = {c: [] for c in CATEGORIES}

    def bad(msg, cat="SCHEMA_INVALID"):
        errs[cat].append(msg)

    def obj(v, keys, where):
        if not isinstance(v, dict) or set(v) != set(keys):
            bad(f"{where}: keys must be exactly {sorted(keys)}")
            return False
        return True

    def hexv(v):
        return isinstance(v, str) and bool(HEX64.match(v))

    def count(v, positive=True):
        return isinstance(v, int) and not isinstance(v, bool) and (v > 0 if positive else v >= 0)

    def columns(v):
        return isinstance(v, list) and bool(v) and all(_text(c) for c in v) and len(set(v)) == len(v)

    # ---------------- structure
    if not obj(m, MANIFEST_KEYS, "manifest"):
        return errs
    if m["schema"] != MANIFEST_SCHEMA or not _text(m["rules_version"]) or m["freeze_note"] != FREEZE_NOTE:
        bad("schema, rules_version or freeze_note")
    if obj(m["tool"], {"path", "sha256"}, "tool") and (m["tool"]["path"] != f"code/{STEM}.py" or not hexv(m["tool"]["sha256"])):
        bad("tool: path and 64-hex sha256")
    if obj(m["package"], {"zip", "zip_sha256", "r7_member_prefix"}, "package") and (
            not _text(m["package"]["zip"]) or m["package"]["r7_member_prefix"] != EXPECTED_PREFIX or not hexv(m["package"]["zip_sha256"])):
        bad("package: zip, 64-hex zip_sha256, expected member prefix")
    files = m["files"]
    if not isinstance(files, dict) or set(files) != set(FILES):
        bad(f"files must be exactly the {len(FILES)} expected R7 files")
    else:
        for f, e in files.items():
            if obj(e, {"zip_member", "sha256", "rows", "columns"}, f"files[{f}]") and (
                    e["zip_member"] != EXPECTED_PREFIX + f or not hexv(e["sha256"]) or not count(e["rows"]) or not columns(e["columns"])):
                bad(f"files[{f}]: expected member, 64-hex sha256, rows > 0, non-empty unique columns")
    li = m["live_inputs"]
    if obj(li, {"register", "types", "ledger", "identity_code", "policy_code"}, "live_inputs"):
        for k in ("register", "types", "ledger"):
            e = li[k]
            if obj(e, {"path", "sha256", "rows", "columns"}, f"live_inputs.{k}") and (
                    not _text(e["path"]) or not hexv(e["sha256"]) or not count(e["rows"]) or not columns(e["columns"])):
                bad(f"live_inputs.{k}: path, 64-hex sha256, rows > 0, non-empty unique columns")
        for k in ("identity_code", "policy_code"):
            if obj(li[k], {"path", "sha256"}, f"live_inputs.{k}") and (not _text(li[k]["path"]) or not hexv(li[k]["sha256"])):
                bad(f"live_inputs.{k}: path and 64-hex sha256")
    lp = m["ledger_provenance"]
    if obj(lp, {"path", "tracked_by_git", "sha256", "subset_rows", "subset_sha256", "subset_carried_in"}, "ledger_provenance") and (
            lp["tracked_by_git"] is not False or not hexv(lp["sha256"]) or not hexv(lp["subset_sha256"])
            or not count(lp["subset_rows"], positive=False) or not _text(lp["subset_carried_in"]) or not _text(lp["path"])):
        bad("ledger_provenance: path, tracked_by_git false, hashes, subset_rows >= 0, subset_carried_in")
    dec = m["decisions"]
    if obj(dec, {"path", "present", "sha256", "snapshot", "records", "counts"}, "decisions"):
        if not _text(dec["path"]) or not isinstance(dec["present"], bool) \
                or (dec["present"] and not hexv(dec["sha256"])) or (not dec["present"] and dec["sha256"] is not None):
            bad("decisions: path, present bool, sha256 64 hex when present else null")
        if not isinstance(dec["snapshot"], list) or not all(
                isinstance(x, dict) and set(x) == {"decision_id", "kind", "subject", "status", "record"}
                and isinstance(x["decision_id"], str) and DECISION_ID_RE.match(x["decision_id"])
                and x["kind"] in ("gate", "pair") and x["status"] in SNAPSHOT_STATUSES
                and isinstance(x["subject"], str) and isinstance(x["record"], dict) for x in dec["snapshot"]):
            bad("decisions.snapshot entries: decision_id, kind, subject, status, record")
        if not isinstance(dec["records"], dict) or not all(isinstance(k, str) and hexv(v) for k, v in dec["records"].items()):
            bad("decisions.records must map decision_id to 64-hex digest")
        if obj(dec["counts"], {"current", "stale", "superseded", "historical"}, "decisions.counts") and \
                not all(count(v, positive=False) for v in dec["counts"].values()):
            bad("decisions.counts must be integers >= 0")
    nt = m["notes"]
    if obj(nt, {"path", "present", "sha256", "snapshot", "snapshot_sha256"}, "notes"):
        if not _text(nt["path"]) or not isinstance(nt["present"], bool) or not hexv(nt["snapshot_sha256"]) \
                or (nt["present"] and not hexv(nt["sha256"])) or (not nt["present"] and nt["sha256"] is not None):
            bad("notes: path, present bool, sha256 when present else null, 64-hex snapshot_sha256")
        if not obj(nt["snapshot"], {"notes", "historical_notes"}, "notes.snapshot") or not all(
                isinstance(lst, list) and all(isinstance(r, dict) and set(r) == NOTE_KEYS for r in lst)
                for lst in nt["snapshot"].values()):
            bad("notes.snapshot: notes and historical_notes lists of note records")
    q = m["queue"]
    if obj(q, {"file", "sha256", "rows", "columns", "pair_keys", "rendered"}, "queue"):
        if q["file"] != "queue.csv" or not hexv(q["sha256"]) or not count(q["rows"]) or q["columns"] != QUEUE_COLUMNS:
            bad("queue: file queue.csv, 64-hex sha256, rows > 0, exact columns")
        if not isinstance(q["pair_keys"], list) or not all(isinstance(k, str) and PAIR_KEY_RE.match(k) for k in q["pair_keys"]) \
                or len(set(q["pair_keys"])) != len(q["pair_keys"]):
            bad("queue.pair_keys: unique proposed pair keys")
        if not isinstance(q["rendered"], dict) or not all(
                isinstance(v, dict) and set(v) == set(RENDERED_COLS) and all(isinstance(x, str) for x in v.values())
                for v in q["rendered"].values()):
            bad("queue.rendered: each pair maps exactly the rendered columns to text")
    ig = m["integrity"]
    if obj(ig, {"status", "checks"}, "integrity") and (
            ig["status"] not in ("PASS", "FAIL") or not isinstance(ig["checks"], dict)
            or set(ig["checks"]) != set(INTEGRITY_CODES) or not all(isinstance(v, bool) for v in ig["checks"].values())):
        bad("integrity: status PASS/FAIL and all 12 checks as booleans")
    ia = m["import_approval"]
    if obj(ia, {"status", "gates", "policy_function_publishes"}, "import_approval") and (
            ia["status"] not in ("APPROVED", "NOT_APPROVED") or not isinstance(ia["gates"], dict)
            or set(ia["gates"]) != set(ALL_GATES)
            or not all(isinstance(g, dict) and set(g) == {"open", "detail"} and isinstance(g["open"], bool) and _text(g["detail"])
                       for g in ia["gates"].values())
            or ia["policy_function_publishes"] not in (True, False, None)):
        bad("import_approval: status, every gate once as {open, detail}, policy_function_publishes")
    if not isinstance(m["ledger_measurements"], dict) or set(m["ledger_measurements"]) != LEDGER_KEYS:
        bad("ledger_measurements must carry exactly the measured fields")
    if errs["SCHEMA_INVALID"]:
        return errs  # meaning is only checked on a sound structure

    # ---------------- meaning
    sem = lambda msg: bad(msg, "SEMANTIC_INVALID")  # noqa: E731
    if ig["status"] != ("PASS" if all(ig["checks"].values()) else "FAIL"):
        sem("integrity.status disagrees with its checks")
    if ig["status"] != "PASS":
        sem("a bundle is only written when integrity passes")
    # Decisions and notes are re-derived with the production validators. A record is
    # never trusted because its digest matches; a status is never taken as supplied.
    pseudo = [{"key": k, "fingerprint": q["rendered"].get(k, {}).get("evidence_fingerprint", "")} for k in q["pair_keys"]]
    ordered = sorted(dec["snapshot"], key=lambda x: x["decision_id"])

    def derive_decisions(raw_bytes):
        st_, e_ = load_decisions(raw_bytes, pseudo, date.today())
        return (None, e_) if e_ else (st_["snapshot"], [])
    if not dec["present"] and (dec["snapshot"] or dec["records"] or any(dec["counts"].values())):
        sem("decisions.present is false but the manifest carries decision snapshots, records or counts")
    if dec["snapshot"]:
        rebuilt = {"schema": DECISIONS_SCHEMA, "gates": {}, "proposed_equivalence_pairs": []}
        for x in ordered:
            if x["kind"] == "gate":
                rebuilt["gates"].setdefault(x["subject"], []).append(x["record"])
            else:
                rebuilt["proposed_equivalence_pairs"].append(x["record"])
        derived, derr = derive_decisions(canonical(rebuilt).encode("utf-8"))
        if derr:
            sem(f"decision snapshot records fail the decision schema: {derr[:3]}")
        elif derived != ordered:
            sem("decision snapshot statuses or subjects are not what its records derive")
    if nt["present"]:
        _, nerr_ = load_notes(canonical({"schema": NOTES_SCHEMA, **nt["snapshot"]}).encode("utf-8"),
                              set(q["pair_keys"]), date.today())
        if nerr_:
            sem(f"notes snapshot fails the notes schema: {nerr_[:3]}")
    snap = dec["snapshot"]
    ids = [x["decision_id"] for x in snap]
    if len(set(ids)) != len(ids) or set(ids) != set(dec["records"]):
        sem("decisions.snapshot and decisions.records name different decisions")
    for x in snap:
        if dec["records"].get(x["decision_id"]) != sha256_bytes(canonical(x["record"]).encode("utf-8")):
            sem(f"decision {x['decision_id']}: record digest mismatch")
        r = x["record"]
        if x["kind"] == "pair" and x["subject"] != f"{r.get('cedar_uid')}|{r.get('business_uid')}":
            sem(f"decision {x['decision_id']}: subject does not match its record")
        if x["kind"] == "gate" and (x["subject"] not in GATE_CODES or r.get("status") not in ("APPROVED", "NOT_APPROVED")):
            sem(f"decision {x['decision_id']}: not a valid gate decision")
        if (x["kind"] == "gate") != x["status"].startswith("GATE_"):
            sem(f"decision {x['decision_id']}: status {x['status']} does not fit kind {x['kind']}")
    superseded_targets = {x["record"].get("supersedes") for x in snap if x["record"].get("supersedes")}
    for x in snap:
        if (x["status"] in ("SUPERSEDED", "GATE_SUPERSEDED")) != (x["decision_id"] in superseded_targets):
            sem(f"decision {x['decision_id']}: marked {x['status']} but its supersession says otherwise")
    by_status = {s_: sum(1 for x in snap if x["status"] == s_) for s_ in SNAPSHOT_STATUSES}
    if dec["counts"] != {"current": by_status["CURRENT"], "stale": by_status["STALE"],
                         "superseded": by_status["SUPERSEDED"], "historical": by_status["HISTORICAL"]}:
        sem(f"decisions.counts {dec['counts']} disagree with the snapshot")
    heads = {}
    for x in snap:
        if x["status"] in ("CURRENT", "STALE", "HISTORICAL", "GATE_HEAD"):
            if x["subject"] in heads:
                sem(f"{x['subject']}: more than one head decision")
            heads[x["subject"]] = x
    keys = set(q["pair_keys"])
    for subj, x in heads.items():
        if x["status"] in ("CURRENT", "STALE") and subj not in keys:
            sem(f"{subj}: a {x['status']} decision for a pair that is not proposed")
        if x["status"] == "HISTORICAL" and subj in keys:
            sem(f"{subj}: HISTORICAL decision for a pair that is proposed")
    rend = q["rendered"]
    if set(rend) != keys or q["rows"] != len(keys) or m["ledger_measurements"].get("proposed_pairs") != q["rows"]:
        sem("queue rows, pair_keys, rendered pairs and ledger_measurements.proposed_pairs disagree")
    notes_by_key = {}
    for listname in ("notes", "historical_notes"):
        for r in nt["snapshot"][listname]:
            if r["pair_key"] in notes_by_key:
                sem(f"notes: {r['pair_key']} noted twice")
            notes_by_key[r["pair_key"]] = (listname, r)
    if nt["snapshot_sha256"] != sha256_bytes(canonical(nt["snapshot"]).encode("utf-8")):
        sem("notes.snapshot_sha256 does not match the notes snapshot")
    if not nt["present"] and notes_by_key:
        sem("notes snapshot is non-empty but no notes file was present")
    for k, (listname, _) in notes_by_key.items():
        if (listname == "notes") != (k in keys):
            sem(f"notes: {k} is in {listname} but is {'' if k in keys else 'not '}a proposed pair")
    for k in keys & set(rend):
        r, head = rend[k], heads.get(k)
        want_note = notes_by_key[k][1]["note"] if k in notes_by_key and notes_by_key[k][0] == "notes" else ""
        if r["owner_note_snapshot"] != want_note:
            sem(f"{k}: rendered note disagrees with the notes snapshot")
        if head is None:
            want = {"resolution_status": "UNRESOLVED", "decision_status": "", "decision_id": "",
                    "owner_disposition": "", "owner_decided_by": "", "owner_decided_on": ""}
        else:
            rec = head["record"]
            want = {"resolution_status": ({"CONFIRMED_SAME_LEGAL_OBJECT": "OWNER_CONFIRMED",
                                           "REFUSED_NOT_SAME_LEGAL_OBJECT": "OWNER_REFUSED"}.get(rec.get("disposition"), "?")
                                          if head["status"] == "CURRENT" else "UNRESOLVED_STALE_DECISION"),
                    "decision_status": head["status"], "decision_id": head["decision_id"],
                    "owner_disposition": rec.get("disposition", ""), "owner_decided_by": rec.get("decided_by", ""),
                    "owner_decided_on": rec.get("decided_on", "")}
            if (rec.get("evidence_fingerprint") == r["evidence_fingerprint"]) != (head["status"] == "CURRENT"):
                sem(f"{k}: decision status {head['status']} contradicts the fingerprint it was bound to")
        if any(r[c] != v for c, v in want.items()):
            sem(f"{k}: rendered decision columns do not follow from the decision snapshot")
    gates = ia["gates"]
    if not gates["G00"]["open"]:
        sem("G00 must be open in a written bundle (decisions were valid)")
    resolved = all(r["resolution_status"] in ("OWNER_CONFIRMED", "OWNER_REFUSED") for r in rend.values())
    if gates["G03"]["open"] != (resolved and bool(rend)):
        sem("G03 disagrees with the number of resolved proposed pairs")
    for name, code in GATE_CODES.items():
        head = heads.get(name)
        opened = head is not None and head["record"].get("status") == "APPROVED"
        if name == "business_name_publication":
            opened = opened and ia["policy_function_publishes"] is True
        if gates[code]["open"] != opened:
            sem(f"{code} disagrees with the gate decisions snapshot")
    if (ia["status"] == "APPROVED") != (ig["status"] == "PASS" and all(g["open"] for g in gates.values())):
        sem("import_approval.status disagrees with integrity and the gates")

    # ---------------- the bytes the manifest describes
    if queue_bytes is not None:
        if sha256_bytes(queue_bytes) != q["sha256"]:
            bad("queue.csv bytes differ from the manifest hash", "BUNDLE_CORRUPT")
        else:
            table = parse_csv(queue_bytes)
            rows = dicts(table) if table["header"] == q["columns"] and all(len(x) == len(table["header"]) for x in table["rows"]) else None
            order = [(x["generated_assessment"], x["entity_name"], x["pair_key"]) for x in rows] if rows is not None else []
            if rows is None or len(rows) != q["rows"] or sorted(x["pair_key"] for x in rows) != q["pair_keys"] \
                    or order != sorted(order) or any(rend[x["pair_key"]][c] != x[c] for x in rows for c in RENDERED_COLS):
                bad("queue.csv content does not follow from its manifest (rows, order or rendered columns)", "SEMANTIC_INVALID")

    # ---------------- reproducibility against live inputs
    if t is not None:
        if m["rules_version"] != RULES_VERSION or m["tool"]["sha256"] != t["code_sha"]["tool"]:
            bad("tool or rules changed since freeze", "STALE_ARTIFACT")
        if m["package"]["zip_sha256"] != ZIP_SHA256:
            bad("package hash is not the frozen R7 hash", "R7_PACKAGE_MISMATCH")
        for f, e in files.items():
            if e["sha256"] != t["member_sha"].get(f) or e["columns"] != t["raw"].get(f, {}).get("header") \
                    or e["rows"] != len(t["raw"].get(f, {"rows": []})["rows"]):
                bad(f"{f} differs from its ZIP member", "R7_PACKAGE_MISMATCH")
        for k in ("register", "types", "ledger"):
            e = li[k]
            if e["sha256"] != t["live_sha"][k] or e["columns"] != t["raw"]["live:" + k]["header"] \
                    or e["rows"] != len(t["raw"]["live:" + k]["rows"]):
                bad(f"live input {k} changed since freeze", "LIVE_INPUT_CHANGED")
        for k in ("identity_code", "policy_code"):
            if li[k]["sha256"] != t["code_sha"][k]:
                bad(f"{k} changed since freeze", "LIVE_INPUT_CHANGED")
        if lp["sha256"] != t["live_sha"]["ledger"]:
            bad("ledger provenance differs from the live ledger", "LIVE_INPUT_CHANGED")
        now_d = sha256_bytes(t["decisions_bytes"]) if t.get("decisions_bytes") is not None else None
        if dec["sha256"] != now_d:
            bad("decisions file changed since freeze", "DECISIONS_CHANGED")
        elif now_d is not None:
            derived, derr = derive_decisions(t["decisions_bytes"])
            if derr or derived != ordered:
                bad("decision snapshot does not derive from the decisions file with the recorded hash", "SEMANTIC_INVALID")
        now_n = sha256_bytes(t["notes_bytes"]) if t.get("notes_bytes") is not None else None
        if nt["sha256"] != now_n:
            bad("notes file changed since freeze", "NOTES_CHANGED")
        elif now_n is not None:
            nst_, nerr_ = load_notes(t["notes_bytes"], set(q["pair_keys"]), date.today())
            if nerr_ or notes_snapshot(nst_) != nt["snapshot"]:
                bad("notes snapshot does not derive from the notes file with the recorded hash", "SEMANTIC_INVALID")
    return errs


# =================================================================== audit bundle store
POINTER_KEYS = {"schema", "bundle_id", "manifest_sha256", "queue_generated_sha256", "activated_bundles"}
HOOKS = {}  # inert test seams: after_prepare, before_activate, recover_before_activate,
#           report_after_snapshot. Never set in production.
CONTROL_FILES = {".lock", ".lock.owner.json"}
SNAPSHOT_KEYS = ("zip", "register", "types", "ledger", "identity_code", "policy_code", "decisions", "notes")


class Locked(Refused):
    """Another freeze or recover holds the audit lock."""


class Uninitialized(Refused):
    """The audit store does not exist yet. Only freeze may create it; report never does."""


def store_paths(paths):
    return paths.audit_dir / "CURRENT.json", paths.audit_dir / "bundles"


def lock_path(paths):
    return paths.audit_dir / ".lock"


def _token():
    return f"{os.getpid()}.{os.urandom(6).hex()}"


def _utc(ts=None):
    d = datetime.now(timezone.utc) if ts is None else datetime.fromtimestamp(ts, timezone.utc)
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def _tree_digest(p: Path) -> str:
    if p.is_file():
        return sha256_bytes(p.read_bytes())
    parts = [f"{x.relative_to(p).as_posix()}:{sha256_bytes(x.read_bytes())}" for x in sorted(p.rglob("*")) if x.is_file()]
    return sha256_bytes("\n".join(parts).encode("utf-8"))


def _abandon(p: Path, reason: str) -> Path:
    """Rename a leftover aside under a digest-bearing name. Identical content shares a
    digest, so a later identical copy is recognisable (.dupN). Never deletes."""
    base = f".abandoned-{reason}-{_tree_digest(p)[:12]}-{p.name.lstrip('.')}"
    dest, n = p.with_name(base), 1
    while dest.exists():
        dest = p.with_name(f"{base}.dup{n}")
        n += 1
    os.rename(p, dest)
    return dest


# ---- the lock: one OS-managed exclusive lock on one byte of a permanent file
def _os_lock(fh):
    if os.name == "nt":
        import msvcrt
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _os_unlock(fh):
    if os.name == "nt":
        import msvcrt
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _is_conflict(e: OSError) -> bool:
    return isinstance(e, (BlockingIOError, PermissionError)) or getattr(e, "errno", None) in (11, 13, 35, 36)


def last_holder(paths):
    """Diagnostic only: the last process that recorded taking the lock. Authorises nothing."""
    try:
        return json.loads((paths.audit_dir / ".lock.owner.json").read_text(encoding="utf-8"))
    except Exception:
        return "unrecorded"


@contextlib.contextmanager
def transaction_lock(paths, operation):
    """Held for the whole freeze or recover, the only operations authorized to write.
    This is also where the store is initialized: it creates the audit directory and
    the permanent lock file on first use. report never takes this path; it uses
    read_lock, which creates nothing. The operating system releases the lock when the
    holder exits or dies, so there is no stale lock to break: the lock file is never
    renamed or removed, and nothing is decided from recorded metadata."""
    paths.audit_dir.mkdir(parents=True, exist_ok=True)
    try:
        fh = open(lock_path(paths), "a+b")
    except OSError as e:
        raise Refused(f"cannot open the audit lock file: {e}")
    try:
        try:
            _os_lock(fh)
        except OSError as e:
            if _is_conflict(e):
                raise Locked(f"audit store is locked by another freeze or recover (last recorded holder, diagnostic only: "
                             f"{last_holder(paths)})")
            raise Refused(f"cannot take the audit lock: {e}")
        txid = f"{operation}-{_token()}"
        try:
            (paths.audit_dir / ".lock.owner.json").write_text(json.dumps(
                {"transaction_id": txid, "operation": operation, "pid": os.getpid(), "hostname": socket.gethostname(),
                 "started_utc": _utc()}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except OSError:
            pass  # diagnostic only
        try:
            yield txid
        finally:
            _os_unlock(fh)
    finally:
        fh.close()


@contextlib.contextmanager
def read_lock(paths):
    """The same OS lock on the same permanent .lock file, taken for reading only.

    Creates nothing: no audit directory, no lock file, no owner metadata, no
    CURRENT, no bundle, no temporary file. The lock file is opened "r+b", which
    cannot create and cannot truncate, so a store that was never initialized is a
    refusal rather than something this call brings into being. There is no
    check-then-create race: nothing is tested for existence first; the open either
    finds the permanent lock file or it does not."""
    try:
        fh = open(lock_path(paths), "r+b")
    except FileNotFoundError:
        raise Uninitialized(f"no audit lock file at {rel(lock_path(paths))}")
    except OSError as e:
        raise Refused(f"cannot open the audit lock file: {e}")
    try:
        try:
            _os_lock(fh)
        except OSError as e:
            if _is_conflict(e):
                raise Locked(f"audit store is locked by another freeze or recover (last recorded holder, diagnostic only: "
                             f"{last_holder(paths)})")
            raise Refused(f"cannot take the audit lock: {e}")
        try:
            yield
        finally:
            _os_unlock(fh)
    finally:
        fh.close()


def lock_held(paths):
    """Probe without recording anything: True when another handle holds the lock."""
    if not lock_path(paths).exists():
        return False
    with open(lock_path(paths), "a+b") as fh:
        try:
            _os_lock(fh)
        except OSError as e:
            if _is_conflict(e):
                return True
            raise
        _os_unlock(fh)
        return False


# ---- bundles
def _read_bundle(bdir, bid):
    """(manifest, manifest_bytes, queue_bytes, problems). Any edit changes the content id."""
    d = bdir / bid
    try:
        mb, qb = (d / "manifest.json").read_bytes(), (d / "queue.csv").read_bytes()
        extra = sorted(x.name for x in d.iterdir() if x.name not in ("manifest.json", "queue.csv"))
    except OSError as e:
        return None, None, None, [f"BUNDLE_CORRUPT: unreadable ({e})"]
    probs = [f"BUNDLE_CORRUPT: unexpected files {extra}"] if extra else []
    if sha256_bytes(mb + b"\0" + qb)[:24] != bid:
        probs.append("BUNDLE_CORRUPT: content no longer matches its bundle id (bytes inside the bundle changed)")
    try:
        m = json.loads(mb.decode("utf-8"), object_pairs_hook=_no_dup_keys)
    except Exception as e:
        return None, mb, qb, probs + [f"BUNDLE_CORRUPT: manifest is not JSON ({e})"]
    if isinstance(m, dict) and m.get("schema") == MANIFEST_SCHEMA:
        errs = validate_manifest(m, queue_bytes=qb)
        probs += [f"{c}: {x}" for c in ("SCHEMA_INVALID", "SEMANTIC_INVALID", "BUNDLE_CORRUPT") for x in errs[c]]
    elif isinstance(m, dict) and m.get("schema") == MANIFEST_SCHEMA_V2:
        if not isinstance(m.get("queue"), dict) or m["queue"].get("sha256") != sha256_bytes(qb) \
                or not isinstance(m.get("decisions"), dict) or not isinstance(m["decisions"].get("records"), dict):
            probs.append("BUNDLE_CORRUPT: historical v2 bundle disagrees with its manifest")
    else:
        probs.append("SCHEMA_INVALID: unknown manifest schema")
    return m, mb, qb, probs


def read_store(paths):
    cur, bdir = store_paths(paths)
    st = {"pointer": None, "pointer_state": "ABSENT", "pointer_detail": "", "manifest": None, "manifest_bytes": None,
          "queue_bytes": None, "corrupt": {}, "leftovers": [], "orphans": []}
    if paths.audit_dir.exists():
        st["leftovers"] += [p for p in sorted(paths.audit_dir.iterdir())
                            if p.name.startswith(".CURRENT.json.") and p.name.endswith(".tmp")]
    if bdir.exists():
        st["leftovers"] += [p for p in sorted(bdir.iterdir()) if p.name.startswith(".staging-")]
    history = []
    if cur.exists():
        try:
            ptr = json.loads(cur.read_bytes().decode("utf-8"), object_pairs_hook=_no_dup_keys)
            if not isinstance(ptr, dict) or set(ptr) != POINTER_KEYS or ptr["schema"] != POINTER_SCHEMA:
                raise ValueError("pointer keys/schema")
            hist = ptr["activated_bundles"]
            if not (isinstance(ptr["bundle_id"], str) and BUNDLE_ID_RE.match(ptr["bundle_id"]) and isinstance(hist, list)
                    and hist and hist[-1] == ptr["bundle_id"] and len(set(hist)) == len(hist)
                    and all(isinstance(h, str) and BUNDLE_ID_RE.match(h) for h in hist)
                    and all(isinstance(ptr[k], str) and HEX64.match(ptr[k]) for k in ("manifest_sha256", "queue_generated_sha256"))):
                raise ValueError("pointer field types")
            st.update(pointer=ptr, pointer_state="VALID")
            history = hist
        except Exception as e:
            st.update(pointer_state="INVALID", pointer_detail=str(e))
    for bid in history:
        m, mb, qb, probs = _read_bundle(bdir, bid)
        if bid == st["pointer"]["bundle_id"]:
            if mb is not None and sha256_bytes(mb) != st["pointer"]["manifest_sha256"]:
                probs.append("BUNDLE_CORRUPT: manifest differs from the pointer")
            if isinstance(m, dict) and isinstance(m.get("queue"), dict) \
                    and m["queue"].get("sha256") != st["pointer"]["queue_generated_sha256"]:
                probs.append("BUNDLE_CORRUPT: queue hash differs from the pointer")
            st.update(manifest=m, manifest_bytes=mb, queue_bytes=qb)
        if probs:
            st["corrupt"][bid] = probs
    if bdir.exists():
        st["orphans"] = [p for p in sorted(bdir.iterdir())
                         if p.is_dir() and not p.name.startswith(".") and p.name not in set(history)]
    st["transaction"] = "INCOMPLETE" if st["leftovers"] or st["orphans"] else "CLEAN"
    st["state"] = "INVALID_POINTER" if st["pointer_state"] == "INVALID" else "CORRUPT" if st["corrupt"] else st["transaction"]
    return st


def inventory(paths, st=None):
    """Report-only: every artifact in the store and what it is. Deletes nothing."""
    st = st or read_store(paths)
    _, bdir = store_paths(paths)
    history = st["pointer"]["activated_bundles"] if st["pointer"] else []
    owner_work = set()
    for bid in history:
        m = _read_bundle(bdir, bid)[0]
        for k in ("decisions", "notes"):
            if isinstance(m, dict) and isinstance(m.get(k), dict) and m[k].get("sha256"):
                owner_work.add((k, m[k]["sha256"]))
    items = []

    def add(p, state, reason=""):
        tx = re.search(r"((freeze|recover)-\d+\.[0-9a-f]{12})", p.name)
        bid = re.search(r"([0-9a-f]{24})", p.name)
        unique = None
        man = p / "manifest.json"
        if p.is_dir() and man.exists():
            try:
                m = json.loads(man.read_text(encoding="utf-8"))
                unique = any(isinstance(m.get(k), dict) and m[k].get("sha256") and (k, m[k]["sha256"]) not in owner_work
                             for k in ("decisions", "notes"))
            except Exception:
                unique = None
        items.append({"path": rel(p), "state": state, "transaction_id": tx.group(1) if tx else "",
                      "operation": tx.group(2) if tx else "", "reason": reason,
                      "modified_utc": _utc(p.stat().st_mtime) if p.exists() else "",
                      "related_bundle": bid.group(1) if bid else "",
                      "related_bundle_activated": bool(bid and bid.group(1) in history),
                      "may_hold_unique_owner_work": unique})
    for bid in history:
        state = "corrupted" if bid in st["corrupt"] else "active" if bid == st["pointer"]["bundle_id"] else "historical"
        add(bdir / bid, state, "; ".join(st["corrupt"].get(bid, [])))
    for p in st["orphans"]:
        add(p, "orphaned", "complete bundle never activated")
    for p in st["leftovers"]:
        add(p, "staging" if p.name.startswith(".staging-") else "temporary", "uncommitted transaction")
    for root in (paths.audit_dir, bdir):
        if root.exists():
            for p in sorted(root.iterdir()):
                if p.name.startswith(".abandoned-"):
                    mm = re.match(r"\.abandoned-(.+?)-[0-9a-f]{12}-", p.name)
                    add(p, "abandoned" if ".dup" not in p.name else "abandoned-duplicate", mm.group(1) if mm else "")
    return items


def i02_from_store(st, t):
    if st["pointer_state"] == "ABSENT":
        return True, "no current audit bundle yet"
    if st["pointer_state"] == "INVALID":
        return False, f"CURRENT.json invalid: {st['pointer_detail']}"
    if st["corrupt"]:
        return False, f"bundle content corrupt: {dict(list(st['corrupt'].items())[:2])}"
    bid, m = st["pointer"]["bundle_id"], st["manifest"]
    if m.get("schema") == MANIFEST_SCHEMA_V2:
        return True, f"current bundle {bid} is historical schema v2 (content verified against its id); refreeze to v3"
    errs = validate_manifest(m, t, st["queue_bytes"])
    if errs["R7_PACKAGE_MISMATCH"]:
        return False, f"current bundle R7 mismatch {errs['R7_PACKAGE_MISMATCH'][:2]}"
    stale = {c: len(v) for c, v in errs.items() if v}
    return True, f"current bundle {bid} valid; R7 members match" + (f"; refreeze needed: {stale}" if stale else "")


def queue_to_bytes(rows):
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=QUEUE_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def prepare(t, st, ident=None, today=None):
    """Everything a freeze would write, built and validated in memory. Owner state is
    read only from the owner input files, never from a bundle."""
    prior_records = {}
    if st["pointer_state"] == "VALID":
        m = st["manifest"]
        prior_records = m["decisions"]["records"]
        if m.get("schema") == MANIFEST_SCHEMA_V2:
            typed = [o["pair_key"] for o in dicts(parse_csv(st["queue_bytes"])) if (o.get("YOUR_NOTES") or "").strip()]
            if typed:
                raise Refused(f"the current v2 bundle holds notes typed inside it for {typed[:3]}; "
                              f"copy them into {rel(t['paths'].notes)} before freezing")
    ev = evaluate(t, i02_from_store(st, t), prior_records, ident, today)
    if not ev["integrity_pass"]:
        raise Refused("integrity failed; nothing written")
    if ev["decision_errors"]:
        raise Refused(f"decisions invalid; nothing written: {ev['decision_errors'][:3]}")
    if ev["notes_errors"]:
        raise Refused(f"notes invalid; nothing written: {ev['notes_errors'][:3]}")
    qb = queue_to_bytes(ev["rows"])
    manifest = build_manifest(t, ev, qb)
    errs = validate_manifest(manifest, t, qb)
    if any(errs.values()):
        raise Refused(f"prepared manifest failed validation: { {c: v for c, v in errs.items() if v} }")
    mb = (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    return ev, qb, mb, sha256_bytes(mb + b"\0" + qb)[:24]


def _write_new(path: Path, data: bytes):
    with open(path, "xb") as fh:  # never overwrites; exact bytes, no newline translation
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())


# ---- one input snapshot, verified inside the lock and again at activation
def input_snapshot(paths):
    """Hashes of every consequential input as it is on disk now, plus CURRENT."""
    snap = {k: sha256_file(getattr(paths, k)) for k in SNAPSHOT_KEYS}
    snap["tool"] = sha256_file(Path(__file__).resolve())
    snap["CURRENT"] = sha256_file(store_paths(paths)[0])
    return snap


def _snapshot_of(t):
    """The same hashes as recorded when `t` was loaded (CURRENT excluded)."""
    return {"zip": t["zip_sha"], "register": t["live_sha"]["register"], "types": t["live_sha"]["types"],
            "ledger": t["live_sha"]["ledger"], "identity_code": t["code_sha"]["identity_code"],
            "policy_code": t["code_sha"]["policy_code"], "tool": t["code_sha"]["tool"],
            "decisions": sha256_bytes(t["decisions_bytes"]) if t.get("decisions_bytes") is not None else None,
            "notes": sha256_bytes(t["notes_bytes"]) if t.get("notes_bytes") is not None else None}


def changed_inputs(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def load_verified(paths, cached=None):
    """Called only while the lock is held. Returns (t, snapshot) where every hash `t`
    was built from equals disk at snapshot time, or (None, changed_keys)."""
    for source in ([cached] if cached is not None else []) + [None]:
        snap = input_snapshot(paths)
        t = refresh_decisions(dict(source, paths=paths)) if source is not None else load(paths)
        diff = changed_inputs({k: v for k, v in snap.items() if k != "CURRENT"}, _snapshot_of(t))
        if not diff:
            return t, snap
    return None, diff


def _hook(name, paths):
    if name in HOOKS:
        HOOKS[name](paths)


def _refuse_unsafe_store(st):
    if st["pointer_state"] == "INVALID":
        raise Refused(f"CURRENT.json is invalid ({st['pointer_detail']}); nothing written")
    if st["corrupt"]:
        raise Refused(f"bundle content corrupt {sorted(st['corrupt'])}; bundles are never repaired in place")
    if st["transaction"] == "INCOMPLETE":
        raise Refused(f"incomplete audit transaction {[x.name for x in st['leftovers'] + st['orphans']]}; run recover")


def activate(paths, st, bid, mb, qb, txid):
    """The single commit point: one os.replace of the pointer."""
    cur, _ = store_paths(paths)
    history = st["pointer"]["activated_bundles"] if st["pointer_state"] == "VALID" else []
    ptr = {"schema": POINTER_SCHEMA, "bundle_id": bid, "manifest_sha256": sha256_bytes(mb),
           "queue_generated_sha256": sha256_bytes(qb), "activated_bundles": [h for h in history if h != bid] + [bid]}
    tmp = paths.audit_dir / f".CURRENT.json.{txid}.tmp"
    _write_new(tmp, (json.dumps(ptr, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    os.replace(tmp, cur)  # on failure the temp file stays, detectable; the prior pointer is untouched


def _publish(bdir, bid, mb, qb, txid):
    final = bdir / bid
    if final.exists():
        if (final / "manifest.json").read_bytes() != mb or (final / "queue.csv").read_bytes() != qb:
            raise Refused(f"bundle {bid} exists with different content; bundles are never rewritten")
        return "reused"
    staging = bdir / f".staging-{bid}-{txid}"
    staging.mkdir()
    _write_new(staging / "manifest.json", mb)
    _write_new(staging / "queue.csv", qb)
    if (staging / "manifest.json").read_bytes() != mb or (staging / "queue.csv").read_bytes() != qb:
        raise Refused("staged bundle did not read back identically; left in place for recover")
    os.rename(staging, final)
    return "published"


def freeze(paths, ident=None, today=None, cached=None, attempts=3):
    """Inside the lock: load and verify inputs, prepare, recheck, publish, recheck every
    consequential input and CURRENT, activate. `cached` is reused only if its hashes
    still match disk."""
    with transaction_lock(paths, "freeze") as txid:
        for _ in range(attempts):
            t, snap = load_verified(paths, cached)
            if t is None:
                continue
            st = read_store(paths)
            _refuse_unsafe_store(st)
            ev, qb, mb, bid = prepare(t, st, ident, today)
            _hook("after_prepare", paths)
            if changed_inputs(input_snapshot(paths), snap):
                continue  # restart preparation; nothing has been published
            if st["pointer_state"] == "VALID" and st["pointer"]["bundle_id"] == bid:
                return ev, bid, "unchanged"
            _, bdir = store_paths(paths)
            bdir.mkdir(parents=True, exist_ok=True)
            how = _publish(bdir, bid, mb, qb, txid)
            _hook("before_activate", paths)
            diff = changed_inputs(input_snapshot(paths), snap)
            if diff:
                raise Refused(f"inputs changed after publication ({', '.join(diff)}); nothing activated; bundle {bid} "
                              "is left unactivated; run freeze again (after recover) against the new inputs")
            activate(paths, st, bid, mb, qb, txid)
            return ev, bid, "activated" if how == "published" else "reactivated"
        raise Refused("inputs kept changing during preparation; nothing published")


def recover(paths, ident=None, today=None, cached=None):
    """Inside the lock: set leftovers aside; load and verify inputs; activate only the
    unactivated bundle a freeze would produce from those inputs, rechecking every input
    first; set any other orphan aside. Deletes nothing."""
    with transaction_lock(paths, "recover") as txid:
        st = read_store(paths)
        if st["pointer_state"] == "INVALID":
            raise Refused(f"CURRENT.json invalid ({st['pointer_detail']}); recover will not guess")
        if st["corrupt"]:
            raise Refused(f"bundle content corrupt {sorted(st['corrupt'])}; recover never repairs bundles")
        actions = []
        for p in st["leftovers"]:
            dest = _abandon(p, "staging-uncommitted" if p.name.startswith(".staging-") else "pointer-temp-uncommitted")
            actions.append(f"set aside {p.name} -> {dest.name}")
        st = read_store(paths)
        if st["orphans"]:
            t, snap = load_verified(paths, cached)
            expected = None
            if t is None:
                actions.append(f"inputs changed while loading ({snap}); nothing activated")
            else:
                try:
                    _, qb, mb, expected = prepare(t, dict(st, orphans=[], transaction="CLEAN"), ident, today)
                except Refused as e:
                    actions.append(f"expected bundle not computable: {e}")
            for p in st["orphans"]:
                if expected and p.name == expected and (p / "manifest.json").read_bytes() == mb \
                        and (p / "queue.csv").read_bytes() == qb:
                    _hook("recover_before_activate", paths)
                    diff = changed_inputs(input_snapshot(paths), snap)
                    if diff:
                        raise Refused(f"inputs changed during recover ({', '.join(diff)}); nothing activated; {p.name} kept")
                    activate(paths, st, expected, mb, qb, txid)
                    actions.append(f"activated {p.name}")
                else:
                    dest = _abandon(p, "orphan-not-reproducible")
                    actions.append(f"set aside {p.name} -> {dest.name}")
        final = read_store(paths)
        return final["state"] == "CLEAN", actions


# =================================================================== report
def report(paths, ident=None, cached=None):
    """Read-only, and literally so: it creates nothing, not even the audit directory
    or the lock file. Holds the same OS lock as freeze and recover for the whole
    snapshot, so inputs and store are always read from one moment."""
    print(f"  {STEM}  REPORT (writes nothing)")
    try:
        with read_lock(paths):
            return _report_under_lock(paths, ident, cached)
    except Uninitialized as e:
        print(f"  AUDIT STORE NOT INITIALIZED: run the authorized freeze initialization first ({e})")
        print("  the report creates nothing, so it will not initialize the store itself")
        return EXIT_NO_STORE
    except Locked as e:
        print(f"  LOCK: {e}")
        print("  a freeze or recover is running; the report will not read a store mid-transaction")
        return EXIT_LOCKED


def _report_under_lock(paths, ident, cached):
    """Everything here runs with the lock held; nothing it calls takes the lock."""
    p = paths
    t, snap = load_verified(paths, cached)
    if t is None:
        print(f"  INPUTS CHANGED while reading them ({snap}); nothing reported; rerun")
        return 1
    st = read_store(p)
    if st["pointer_state"] == "ABSENT" and st["state"] == "CLEAN":
        print(f"  AUDIT STORE NOT INITIALIZED: run the authorized freeze initialization first "
              f"(no {rel(store_paths(p)[0])}); the report creates nothing")
        return EXIT_NO_STORE
    inv = inventory(p, st)
    tally = {}
    for i in inv:
        tally[i["state"]] = tally.get(i["state"], 0) + 1
    print(f"  INVENTORY: {tally}")
    for i in inv:
        if i["state"] not in ("active", "historical"):
            print(f"    {i['state']}: {i['path']} transaction={i['transaction_id'] or '-'} operation={i['operation'] or '-'} "
                  f"reason={i['reason'] or '-'} modified={i['modified_utc']} bundle={i['related_bundle'] or '-'} "
                  f"bundle_activated={i['related_bundle_activated']} may_hold_unique_owner_work={i['may_hold_unique_owner_work']}")
    if st["state"] == "INVALID_POINTER":
        print(f"  POINTER INVALID: {st['pointer_detail']}; run: py -3 code/{STEM}.py recover (it refuses to guess)")
        return EXIT_TRANSACTION
    if st["state"] == "CORRUPT":
        for bid, probs in st["corrupt"].items():
            print(f"  CORRUPT {bid}: {probs[:3]}")
        print("  bundle content corrupt: files under bundles/ are never edited and never repaired in place")
        return EXIT_CORRUPT
    if st["state"] == "INCOMPLETE":
        print(f"  TRANSACTION: INCOMPLETE; run: py -3 code/{STEM}.py recover")
        return EXIT_TRANSACTION
    prior = st["manifest"]["decisions"]["records"] if st["pointer_state"] == "VALID" else {}
    ev = evaluate(t, i02_from_store(st, t), prior, ident)
    for code, ok, detail in ev["integrity"]:
        print(f"  {code} {'PASS' if ok else 'FAIL'}     {detail}")
    for code, is_open, detail in ev["gates"]:
        print(f"  {code} {'OPEN' if is_open else 'BLOCKED'}  {detail}")
    if st["pointer_state"] == "VALID":
        bid, m = st["pointer"]["bundle_id"], st["manifest"]
        if m.get("schema") == MANIFEST_SCHEMA_V2:
            print(f"  BUNDLE {bid}: historical schema v2, content verified against its id; refreeze to v3")
        else:
            errs = validate_manifest(m, t, st["queue_bytes"])
            print(f"  BUNDLE {bid}: " + ("reproduces from current inputs" if not any(errs.values()) else
                                        "; ".join(f"{c}: {v[:2]}" for c, v in errs.items() if v) + " -> refreeze"))
    else:
        print("  BUNDLE: none yet")
    n = ev["notes"]
    print(f"  OWNER INPUTS: decisions {rel(p.decisions)} ({'present' if t['decisions_bytes'] is not None else 'absent'}); "
          f"notes {rel(p.notes)} ({len(n['notes'])} notes, {len(n['historical'])} historical). "
          f"Edit only these two; never edit files under {rel(p.audit_dir)}/bundles/")
    print("  LEDGER: " + json.dumps(ledger_measurements(ev["views"]) if ev["views"] else {}, ensure_ascii=False))
    print(f"  INTEGRITY: {'PASS' if ev['integrity_pass'] else 'FAIL'}")
    print(f"  IMPORT APPROVAL: {ev['approval']}"
          + ("" if ev["approval"] == "APPROVED" else f" (blocked: {', '.join(c for c, o, _ in ev['gates'] if not o) or 'integrity'})")
          + " - this tool imports nothing either way")
    if ev["decision_errors"]:
        print(f"  DECISIONS INVALID: {ev['decision_errors']}")
    if ev["notes_errors"]:
        print(f"  NOTES INVALID: {ev['notes_errors']}")
    _hook("report_after_snapshot", paths)
    drift = changed_inputs(input_snapshot(paths), snap)
    if drift:
        print(f"  SNAPSHOT STALE: inputs changed while the report ran; rerun required ({', '.join(drift)})")
        print(f"  everything above describes the snapshot taken when the lock was acquired and IS NOT CURRENT: "
              f"the evaluation shown (approval {ev['approval']}) is not an approval of the files on disk now, "
              f"and this run exits {EXIT_SNAPSHOT_STALE} rather than {exit_code(ev)}")
        return EXIT_SNAPSHOT_STALE
    return exit_code(ev)


# =================================================================== main
ARGS = ([], ["freeze"], ["recover"])
USAGE = (f"usage: py -3 code/{STEM}.py [freeze | recover]   (no argument = report; this tool never imports)\n"
         f"       tests: py -3 -B code/1188_import_chatgpt_r7_business_register_test.py")


def main(argv, _probe=False):
    if argv not in ARGS:
        print(f"REFUSED: unknown or conflicting arguments {argv}\n{USAGE}")
        return 2
    if _probe:
        return 0
    if not argv:
        return report(PROD)  # takes the lock first, then loads
    try:
        if argv == ["freeze"]:
            ev, bid, how = freeze(PROD)
            print(f"  froze audit bundle {bid} ({how}) -> {rel(PROD.audit_dir / 'CURRENT.json')}")
            print(f"  INTEGRITY: PASS; IMPORT APPROVAL: {ev['approval']}. {FREEZE_NOTE}")
            return 0
        ok, actions = recover(PROD)
        for a in actions:
            print(f"  {a}")
        print(f"  RECOVER: {'CLEAN' if ok else 'STILL INCOMPLETE'}")
        return 0 if ok else 1
    except Locked as e:
        print(f"LOCKED: {e}")
        return EXIT_LOCKED
    except Refused as e:
        print(f"REFUSED: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
