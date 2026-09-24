"""Shared contract for Cedar Grove Gaming Intelligence component producers.

Gaming is a Cedar Grove collection (`gaming`, shelf `grove` in
500_build_architecture_map.py), not one of the twelve Cedar Press storefront
collections. This module holds ONLY what every Gaming component producer must
share, so the components cannot drift apart:

* where canonical inputs are read from, with a SHA-256 receipt per input;
* component identity: stable source keys -> key tokens -> registered Cedar
  object IDs bound through the Gaming ID binding register (no live register
  mutation; `cedar_ids` stays the only ID service, and the Gaming blocks are
  declared to it with `declare_static_block`);
* the field-level rights vocabulary and the public-projection gate;
* relationship and evidence vocabularies;
* the table writer and the shared validators every component table passes.

It is NOT a second release runner, catalog, manifest format, ID allocator or
publication policy. Release, catalog, entitlement and rollback go through
`code/build.py release-pilot` and Lumecon Data; public field decisions go
through `data/cedar/field_map.json` via `cedar_publication`. Identifier
bindings for other collections live in `cedar_ids.IDENTIFIER_CONTRACTS`.

Public identifiers (ratified contract, docs/IDENTIFIER_STANDARD.md section
"CICD retirement contract and Gaming handoff (2026-09-24)"):
    cedar_uid          Native entity (CE register, 503_identity.py)
    business_uid       distinct legal business (CB, gated R7 register; none
                       bound yet, so blank with a held status)
    enterprise_id      an EXISTING Cedar NEED enterprise (legacy prefix
                       CEDAR-NEST), only when that enterprise independently
                       qualifies; Gaming never creates one
    gaming_facility_id physical gaming property = the existing cedar_place_id
                       (CEDAR-PLACE, 1129_place_ids.py), unwrapped. The legacy
                       facility_id (CCP-/VP-/TPL-/CEDAR-FAC) is an INTERNAL
                       source key only: CCP- values equal Casino City numbers.
    component IDs      CEDAR-OBS / CEDAR-EVENT / CEDAR-REL / CEDAR-SRC /
                       CEDAR-CONTRACT, bound from source keys (see below).
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cedar_ids  # noqa: E402

# Canonical inputs live in the populated (ignored) Cedar data workspace, which
# is not this checkout when building from a worktree. Refuse to guess.
DEFAULT_INPUT_ROOT = Path(os.environ.get(
    "CEDAR_GAMING_INPUT_ROOT", str(Path.home() / "Desktop" / "Cedar Press")))

SCHEMA_VERSION = "cedar.grove.gaming.v1"

# ---------------------------------------------------------------- identifiers
# RATIFIED 2026-09-24. Every public Gaming ID is a REGISTERED Cedar object ID.
#
# A producer still names a component by its STABLE SOURCE KEY through
# `derive_id(KEY_CLASS, *source_key_parts)`. That no longer renders an ID: it
# renders an internal key TOKEN (`GKEY~<class>~<base64url source key>~`) which
# the candidate runner (`build.py candidate gaming` -> `bind_candidate`)
# replaces, in every component table, with the ID bound to that source key in
# the Gaming ID binding register. Existing bindings are reused exactly; a new
# key gets the next ordinal of its prefix's Gaming block, in sorted
# source_key_sha256 order, with status PROPOSED. Only an ISSUED binding in the
# LIVE register can ship (`build.py release-pilot` refuses anything else), and
# promotion PROPOSED -> ISSUED is a separate controlled step
# (docs/GAMING_GROVE_INFRASTRUCTURE_NOTES.md section 10). The key class (GREV,
# GPAY, ...) and the old derived hash survive only inside that internal
# register. VP-/CCP-/TPL-/CEDAR-FAC- facility values and legacy entity handles
# are internal source keys, never public IDs.
ID_CONTRACT_STATUS = "RATIFIED_CANDIDATE_BINDINGS"

# key class -> (registered object prefix, what it keys). Closed set: adding one
# is a contract change recorded in docs/GAMING_GROVE_DATA_CONTRACT.md.
KEY_CLASSES = {
    "GREV": ("CEDAR-OBS", "regional/national revenue observation"),
    "GBND": ("CEDAR-OBS", "revenue-band observation"),
    "GSRC": ("CEDAR-OBS", "reported revenue observation or compact-term observation"),
    "GFIN": ("CEDAR-OBS", "financial disclosure observation"),
    "GFNM": ("CEDAR-OBS", "facility name/alias observation"),
    "GFCP": ("CEDAR-OBS", "facility capacity/amenity observation"),
    "GLAB": ("CEDAR-OBS", "labor or employment observation"),
    "GFOB": ("CEDAR-OBS", "online sportsbook financial observation (reported unit x period x revision)"),
    "GPAY": ("CEDAR-EVENT", "government payment / revenue-sharing event"),
    "GREG": ("CEDAR-EVENT", "regulatory event or land-eligibility decision"),
    "GENV": ("CEDAR-EVENT", "environmental review"),
    "GLIT": ("CEDAR-EVENT", "litigation or administrative proceeding"),
    "GLIC": ("CEDAR-EVENT", "license issuance or regulatory authorization"),
    "GFST": ("CEDAR-EVENT", "facility history event or status observation"),
    "GREL": ("CEDAR-REL", "facility or reported-unit relationship"),
    "GADV": ("CEDAR-REL", "advocacy/lobbying link (points at the Advocacy collection's own ID)"),
    "GSBK": ("CEDAR-SRC", "online sportsbook reported-unit source series"),
    "GCMP": ("CEDAR-CONTRACT", "tribal-state compact instrument (BIA index compact key kept as source ID)"),
    "GCMV": ("CEDAR-CONTRACT", "compact version: amendment, extension or renewal instrument"),
}
# Kept under its old name for build.py's contract check: the declared
# `derived_ids` values of every CONTRACTS entry are these key classes.
DERIVED_PREFIXES = {k: v[1] for k, v in KEY_CLASSES.items()}

# Gaming static blocks. Chosen far above every live counter measured
# 2026-09-24 in data/spine/_id_registry.json (CEDAR-REL 16044, CEDAR-PLACE 997;
# no CEDAR-OBS/EVENT/SRC/CONTRACT counter and no other caller of those
# prefixes in code/), sized for >= 3x today's keys (CEDAR-EVENT carries ~53k
# payment events that grow monthly), and declared through the ID service so
# any `cedar_ids.allocate` in a process that imports this module steps over
# them. `declare_static_block` refuses an overlap with another owner's block.
GAMING_BLOCKS = {
    "CEDAR-OBS": (500_000_001, 509_999_999),
    "CEDAR-EVENT": (500_001, 799_999),
    "CEDAR-REL": (50_000_001, 50_999_999),
    "CEDAR-SRC": (500_000_001, 500_999_999),
    "CEDAR-CONTRACT": (10_000_001, 10_099_999),
}
BLOCK_OWNER = "gaming_grove.py (Cedar Grove Gaming ID bindings)"
BLOCK_WHY = ("Gaming component objects bound from stable source keys through the Gaming "
             "ID binding register; ratified contract docs/IDENTIFIER_STANDARD.md 2026-09-24")
for _prefix, (_lo, _hi) in GAMING_BLOCKS.items():
    cedar_ids.declare_static_block(_prefix, _lo, _hi, BLOCK_OWNER, BLOCK_WHY)
del _prefix, _lo, _hi

ISSUED_RE = {p: re.compile(r"^%s-(\d{%d})$" % (re.escape(p), cedar_ids.PREFIXES[p][1]))
             for p in GAMING_BLOCKS}
# A Gaming object ID anywhere in a cell (pipe lists, prose).
ISSUED_ANY_RE = re.compile(r"(?<![A-Za-z0-9-])CEDAR-(?:OBS|EVENT|REL|SRC|CONTRACT)-\d+(?![0-9])")
TOKEN_RE = re.compile(r"GKEY~([A-Z]{4})~([A-Za-z0-9_-]+)~")

# Shape only; the check characters are verified by the one shared validator
# (503_identity.valid via cedar_ids) in is_ce_uid, never re-implemented here.
CE_UID_RE = re.compile(r"^CE-[0-9A-HJKMNP-TV-Z]{5}-[0-9A-HJKMNP-TV-Z]{2}$")


@lru_cache(maxsize=None)
def is_ce_uid(value: str) -> bool:
    return bool(CE_UID_RE.match(value or "")) and cedar_ids._entity_validator().valid(value)


@lru_cache(maxsize=None)
def _checked_sub_hub(value: str, prefix: str) -> bool:
    """CEDAR-PLACE / CEDAR-NEST: 6-digit ordinal + 503 check characters."""
    m = re.fullmatch(r"%s-(\d{6})-([0-9A-HJKMNP-TV-Z]{2})" % prefix, value or "")
    if not m:
        return False
    identity = cedar_ids._entity_validator()
    return m.group(2) == identity.check_chars(identity.encode(int(m.group(1))))


def is_place_id(value: str) -> bool:
    return _checked_sub_hub(value, "CEDAR-PLACE")


def is_enterprise_id(value: str) -> bool:
    """An existing Cedar NEED enterprise ID (legacy prefix CEDAR-NEST)."""
    return _checked_sub_hub(value, "CEDAR-NEST")


def facility_id_for(place_id: str) -> str:
    """The ONE place a Gaming facility ID is rendered: the existing CEDAR-PLACE
    value itself. A facility without a place stays unresolved; no wrapper and
    no second facility allocator."""
    if not is_place_id(place_id):
        raise ValueError(f"not a checked CEDAR-PLACE id: {place_id!r}")
    return place_id


def checked_cedar_uid(value: str) -> str:
    """Current Native entities use only canonical CE- identifiers. Legacy
    CICD/handle prefixes (TRBF-, AKNF-, ANVC-, T-...) are refused, never
    translated here; translation is `legacy_handle_uid`, a read-only reader."""
    v = (value or "").strip()
    if v and not is_ce_uid(v):
        raise ValueError(f"legacy or malformed entity id refused as cedar_uid: {v!r}")
    return v


def legacy_handle_uid(handle: str) -> str:
    """cedar_uid for a retired entity handle ONLY via the ratified read-only
    reader `cedar_publication.resolve_retired_entity_handle` (exact historical
    membership, one binding); unknown or contested -> "" (unresolved). Never
    prefix-strips or manufactures a CE value. The caller keeps the handle in
    an internal provenance column, never a public one."""
    import cedar_publication
    try:
        return cedar_publication.resolve_retired_entity_handle(handle)
    except ValueError:
        return ""


def _clean_parts(key_class, parts):
    if key_class not in KEY_CLASSES:
        raise KeyError(f"undeclared Gaming key class {key_class!r}")
    clean = [str(p).strip() for p in parts]
    if not clean or not any(clean):
        raise ValueError(f"{key_class}: a component key needs a nonblank source key")
    return clean


def source_key_of(key_class: str, *parts) -> str:
    """Canonical, readable source key: compact JSON [class, *parts]."""
    return json.dumps([key_class] + _clean_parts(key_class, parts), ensure_ascii=False,
                      separators=(",", ":"))


def source_key_sha256(source_key: str) -> str:
    """The pre-migration derived hash, kept ONLY as the internal dedup key of
    the binding register: sha256 of the unit-separator-joined [class, *parts]."""
    return hashlib.sha256("\x1f".join(json.loads(source_key)).encode("utf-8")).hexdigest()


def derive_id(key_class: str, *parts) -> str:
    """Internal key token for the component keyed by these STABLE source-key
    parts (never names alone). Replaced by its bound registered ID before the
    candidate is validated; a token surviving into a checked table is refused."""
    key = source_key_of(key_class, *parts)
    enc = base64.urlsafe_b64encode(key.encode("utf-8")).decode("ascii").rstrip("=")
    return f"GKEY~{key_class}~{enc}~"


def decode_token(token: str) -> tuple[str, str]:
    """(key class, source key) of one token."""
    m = TOKEN_RE.fullmatch(token or "")
    if not m:
        raise ValueError(f"not a Gaming key token: {str(token)[:60]!r}")
    enc = m.group(2)
    key = base64.urlsafe_b64decode(enc + "=" * (-len(enc) % 4)).decode("utf-8")
    if json.loads(key)[0] != m.group(1):
        raise ValueError("key token class disagrees with its source key")
    return m.group(1), key


def provisional_value(key_class: str, source_key: str) -> str:
    """What the pre-migration (PROV-) build rendered for this key; crosswalk only."""
    return f"PROV-{key_class}-{source_key_sha256(source_key)[:12].upper()}"


def issued_ordinal(value: str, prefix: str | None = None):
    """Ordinal of a Gaming object ID inside its declared block, else None."""
    for p, rx in ISSUED_RE.items():
        if prefix and p != prefix:
            continue
        m = rx.match(value or "")
        if m:
            n = int(m.group(1))
            lo, hi = GAMING_BLOCKS[p]
            return n if lo <= n <= hi else None
    return None


def is_derived_id(value: str, key_class: str | None = None) -> bool:
    """A key token of this class (pre-binding) or a bound object ID of its
    registered prefix inside the Gaming block (post-binding)."""
    m = TOKEN_RE.fullmatch(value or "")
    if m:
        return key_class is None or m.group(1) == key_class
    prefix = KEY_CLASSES[key_class][0] if key_class else None
    return issued_ordinal(value, prefix) is not None


# Source-scoped identifiers that must never appear in a public ID column.
VENDOR_ID_RE = re.compile(r"^(?:CCP|VP|TPL|CEDAR-FAC)-\d+$")
PLACE_ID_RE = re.compile(r"^CEDAR-PLACE-\d{6}-[0-9A-Z]{2}$")
ENTERPRISE_ID_RE = re.compile(r"^CEDAR-NEST-\d{6}-[0-9A-Z]{2}$")
BUSINESS_UID_RE = re.compile(r"^CB-[0-9]{7}$")
# Held statuses for identifier columns that are blank on purpose.
BUSINESS_BINDING_STATUSES = {"held_business_unbound", "not_applicable"}

# ---------------------------------------------------------------- ID binding register
BINDINGS_TABLE = "gaming_id_bindings.csv"
MIGRATION_CROSSWALK_TABLE = "gaming_id_migration_crosswalk.csv"
# Written by the candidate runner, not by a producer: internal, never sampled.
RUNNER_TABLES = (BINDINGS_TABLE, MIGRATION_CROSSWALK_TABLE)
BINDING_HEADER = ["object_prefix", "key_class", "source_key", "source_key_sha256", "issued_id",
                  "table", "column", "status", "first_seen_as_of"]
BINDING_STATUSES = {"PROPOSED", "ISSUED"}
# Relative to an input root. Read-only here; only the controlled promotion
# step (infrastructure notes section 10) may ever write it.
LIVE_BINDINGS = "data/spine/gaming_id_bindings.csv"


class BindingError(ValueError):
    pass


def read_bindings(path: Path | None) -> list[dict]:
    """Rows of a prior binding register, fully re-checked; absent -> []."""
    if path is None or not Path(path).is_file():
        return []
    text = Path(path).read_bytes().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if list(reader.fieldnames or []) != BINDING_HEADER:
        raise BindingError(f"binding register {path} header is not {BINDING_HEADER}")
    rows = list(reader)
    seen_key, seen_id = set(), set()
    for r in rows:
        prefix, klass = r["object_prefix"], r["key_class"]
        if KEY_CLASSES.get(klass, ("",))[0] != prefix:
            raise BindingError(f"binding {r['issued_id']}: key class {klass} is not bound to {prefix}")
        if r["status"] not in BINDING_STATUSES:
            raise BindingError(f"binding {r['issued_id']}: status {r['status']!r}")
        if issued_ordinal(r["issued_id"], prefix) is None:
            raise BindingError(f"binding {r['issued_id']!r} is outside the Gaming {prefix} block")
        try:
            parts = json.loads(r["source_key"])
        except ValueError as exc:
            raise BindingError(f"binding {r['issued_id']}: unreadable source_key") from exc
        if not isinstance(parts, list) or parts[:1] != [klass] or source_key_sha256(r["source_key"]) != r["source_key_sha256"]:
            raise BindingError(f"binding {r['issued_id']}: source_key_sha256 does not match its source_key")
        if r["source_key_sha256"] in seen_key:
            raise BindingError(f"source key bound twice: {r['source_key_sha256']}")
        if r["issued_id"] in seen_id:
            raise BindingError(f"issued ID bound twice: {r['issued_id']}")
        seen_key.add(r["source_key_sha256"])
        seen_id.add(r["issued_id"])
    return rows


def assign_bindings(found: dict, prior: list[dict], as_of: str):
    """Bind every found token. `found`: token -> {"table", "column"} (its owner).

    Returns (token -> issued ID, register rows, summary). Prior bindings are
    reused byte-exactly and never dropped; new keys take the next ordinals of
    their block in sorted source_key_sha256 order, status PROPOSED.
    """
    by_sha = {r["source_key_sha256"]: r for r in prior}
    top = {p: lo - 1 for p, (lo, _hi) in GAMING_BLOCKS.items()}
    for r in prior:
        top[r["object_prefix"]] = max(top[r["object_prefix"]], issued_ordinal(r["issued_id"]))
    decoded = {}
    for token in found:
        klass, key = decode_token(token)
        decoded[token] = (klass, key, source_key_sha256(key))
    mapping, new_rows = {}, []
    summary = defaultdict(Counter)
    for token in sorted(found, key=lambda t: (KEY_CLASSES[decoded[t][0]][0], decoded[t][2])):
        klass, key, sha = decoded[token]
        prefix = KEY_CLASSES[klass][0]
        if sha in by_sha:
            if by_sha[sha]["source_key"] != key:
                raise BindingError(f"source_key_sha256 collision for {key[:80]}")
            mapping[token] = by_sha[sha]["issued_id"]
            summary[prefix]["reused_" + by_sha[sha]["status"]] += 1
            continue
        top[prefix] += 1
        if top[prefix] > GAMING_BLOCKS[prefix][1]:
            raise cedar_ids.IdCollision(f"Gaming {prefix} block {GAMING_BLOCKS[prefix]} is EXHAUSTED; "
                                        "widen the declared block, never spill past it")
        issued = cedar_ids.format_id(prefix, top[prefix])
        mapping[token] = issued
        owner = found[token]
        row = {"object_prefix": prefix, "key_class": klass, "source_key": key, "source_key_sha256": sha,
               "issued_id": issued, "table": owner["table"], "column": owner["column"],
               "status": "PROPOSED", "first_seen_as_of": as_of}
        new_rows.append(row)
        by_sha[sha] = row
        summary[prefix]["new_PROPOSED"] += 1
    seen = {decoded[t][2] for t in found}
    for r in prior:
        if r["source_key_sha256"] not in seen:
            summary[r["object_prefix"]]["carried_not_seen_" + r["status"]] += 1
    rows = sorted(list(prior) + new_rows, key=lambda r: (r["object_prefix"], r["issued_id"]))
    for r in rows:
        summary[r["object_prefix"]]["register_rows"] += 1
    return mapping, rows, {p: dict(sorted(c.items())) for p, c in sorted(summary.items())}


def csv_bytes(header, rows) -> bytes:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _read_csv(path: Path):
    csv.field_size_limit(10_000_000)
    reader = csv.DictReader(io.StringIO(path.read_bytes().decode("utf-8"), newline=""))
    return list(reader.fieldnames or []), list(reader)


def _bind_cell(value: str, mapping: dict) -> str:
    """Substitute bound IDs. A pipe list made only of key tokens is an ID
    list: it is re-sorted by bound ID so its order is canonical, not an
    artifact of the token encoding."""
    if not TOKEN_RE.search(value):
        return value
    parts = value.split("|")
    if len(parts) > 1 and all(TOKEN_RE.fullmatch(p) for p in parts):
        return "|".join(sorted(mapping[p] for p in parts))
    return TOKEN_RE.sub(lambda m: mapping[m.group(0)], value)


def bind_candidate(components: Path, contracts: dict, prior_path: Path | None, as_of: str) -> dict:
    """Replace every key token in the component tables with its bound ID.

    `contracts`: {table: contract} for every declared table. Rewrites each
    table (re-sorted by primary key, same serialization as write_table),
    writes the updated register to components/gaming_id_bindings.csv and
    returns {"rewritten": {table: (old sha, new sha)}, "tokens": per-token
    use, "mapping", "summary"}. Never reads or writes the live register
    except `prior_path`, which it only reads.
    """
    prior = read_bindings(prior_path)
    tables = {}
    uses = defaultdict(Counter)          # token -> table -> rows
    owner = {}
    for table in sorted(contracts):
        path = components / table
        if not path.is_file():
            continue
        header, rows = _read_csv(path)
        tables[table] = (header, rows)
        derived = contracts[table].get("derived_ids", {})
        pk = contracts[table]["primary_key"]
        for r in rows:
            row_tokens = set()
            for col in header:
                for m in TOKEN_RE.finditer(r.get(col) or ""):
                    tok = m.group(0)
                    row_tokens.add(tok)
                    rank = (0 if col in pk else 1) if derived.get(col) == m.group(1) else 2
                    if tok not in owner or (rank, table, col) < owner[tok][0]:
                        owner[tok] = ((rank, table, col), {"table": table, "column": col})
            for tok in row_tokens:
                uses[tok][table] += 1
    found = {tok: o[1] for tok, o in owner.items()}
    mapping, register, summary = assign_bindings(found, prior, as_of)
    rewritten = {}
    for table, (header, rows) in tables.items():
        if not any(TOKEN_RE.search(v or "") for r in rows for v in r.values()):
            continue
        old = (components / table).read_bytes()
        out = [{c: _bind_cell(r.get(c) or "", mapping) for c in header} for r in rows]
        pk = contracts[table]["primary_key"]
        out.sort(key=lambda r: tuple(r.get(k, "") for k in pk))
        data = csv_bytes(header, out)
        (components / table).write_bytes(data)
        rewritten[table] = (hashlib.sha256(old).hexdigest(), hashlib.sha256(data).hexdigest())
    (components / BINDINGS_TABLE).write_bytes(csv_bytes(BINDING_HEADER, register))
    return {"rewritten": rewritten, "uses": {t: dict(c) for t, c in uses.items()},
            "mapping": mapping, "summary": summary,
            "status": {r["issued_id"]: r["status"] for r in register}}


MIGRATION_HEADER = ["key_family", "source_key", "public_identifier", "status", "tables", "affected_rows"]
_SOURCE_FACILITY_RE = re.compile(r"(?<![A-Za-z0-9])(?:CCP|VP|TPL|CEDAR-FAC)-\d+(?![0-9])")
_FACILITY_STATUS = {"mapped": "internal_source_key_public_id_is_place",
                    "merged_into": "internal_source_key_merged_into_place",
                    "not_a_gaming_facility": "held_not_a_facility",
                    "unresolved": "held_unresolved"}


def migration_crosswalk(loaded: dict, bound: dict, contracts: dict, *, retired_pattern=None,
                        receipts=None):
    """Before/after crosswalk of every provisional or source key the Gaming
    build used: its public identifier or held status and the rows it touches.
    Internal (never sampled or released). Returns (header, rows, summary)."""
    rows = []

    def add(family, key, public, status, uses):
        rows.append({"key_family": family, "source_key": key, "public_identifier": public, "status": status,
                     "tables": ";".join(sorted(uses)), "affected_rows": str(sum(uses.values()))})

    # 1. component keys: PROV-<class> (or the BIA compact key) -> bound ID
    for token, issued in sorted(bound["mapping"].items(), key=lambda kv: kv[1]):
        klass, key = decode_token(token)
        if klass in ("GCMP", "GCMV"):
            family = "BIA compact key" if klass == "GCMP" else "BIA compact version key"
            old = json.loads(key)[1]
        else:
            family, old = "PROV-" + klass, provisional_value(klass, key)
        add(family, old, issued, "bound_" + bound["status"][issued], bound["uses"].get(token, {}))
    # 2. facility IDs (PROV-GFAC wrapper dropped) and source facility keys
    place_uses = defaultdict(Counter)
    source_uses = defaultdict(Counter)
    for table, (header, trows) in sorted(loaded.items()):
        fcols = [c for c in header if c == "gaming_facility_id" or c.endswith("_gaming_facility_id")]
        for r in trows:
            seen_place, seen_src = set(), set()
            for c in fcols:
                if r.get(c):
                    seen_place.add(r[c])
            for v in r.values():
                if v and "-" in v:
                    seen_src.update(_SOURCE_FACILITY_RE.findall(v))
            for v in seen_place:
                place_uses[v][table] += 1
            for v in seen_src:
                source_uses[v][table] += 1
    for place, uses in sorted(place_uses.items()):
        add("PROV-GFAC", "PROV-GFAC:" + place, place, "existing_CEDAR-PLACE_unwrapped", uses)
    xw = loaded.get("gaming_facility_crosswalk.csv", ([], []))[1]
    legacy = {}
    for r in xw:
        if r.get("key_scheme") == "legacy_facility_id":
            public = r.get("gaming_facility_id") or r.get("merged_into_gaming_facility_id") or ""
            legacy[r["legacy_facility_id"]] = (r["legacy_id_scheme"], public,
                                               _FACILITY_STATUS.get(r["disposition"], "held_unresolved"))
        elif r.get("rekeyed_cedar_uid") or (r.get("key_scheme") in ("ca_cgcc_record_id", "capacity_official_observation_id")
                                            and r.get("disposition") == "not_a_gaming_facility"
                                            and r.get("legacy_id_scheme") == "VP"):
            add("tribe-level record on a not-a-facility VP key", r["key_value"], r.get("rekeyed_cedar_uid", ""),
                "rekeyed_to_native_entity_no_facility" if r.get("rekeyed_cedar_uid") else "held_unresolved",
                {r["source_table"]: 1})
    for key in sorted(set(legacy) | set(source_uses)):
        scheme, public, status = legacy.get(key, ("CEDAR-FAC" if key.startswith("CEDAR-FAC") else key.split("-")[0],
                                                  "", "internal_source_key_not_in_1201_crosswalk"))
        add(scheme, key, public, status, source_uses.get(key, {}))
    # 3. coverage gaps: natural composite key, no minted ID
    for r in loaded.get("gaming_coverage_gaps.csv", ([], []))[1]:
        parts = r["coverage_gap_id"].split("|")
        old = "PROV-GGAP-" + hashlib.sha256("\x1f".join(["GGAP"] + parts).encode("utf-8")).hexdigest()[:12].upper()
        add("PROV-GGAP", old, r["coverage_gap_id"], "natural_composite_key_no_minted_id",
            {"gaming_coverage_gaps.csv": 1})
    # 4. operators / legal businesses: reported text only, CB unbound
    ops = defaultdict(Counter)
    for table, (header, trows) in sorted(loaded.items()):
        if "business_binding_status" not in header:
            continue
        for r in trows:
            if r["business_binding_status"] == "held_business_unbound":
                ops[r.get("party_external_id") or r.get("party_name") or "(unnamed)"][table] += 1
    for key, uses in sorted(ops.items()):
        add("operator_as_reported (business)", key, "", "held_business_unbound", uses)
    # 5. legacy entity handles: where they still sit (internal provenance) and
    #    input columns producers dropped without translating
    if retired_pattern is not None:
        hits = defaultdict(Counter)
        for table, (header, trows) in sorted(loaded.items()):
            rights = contracts.get(table, {}).get("field_rights", {})
            for r in trows:
                for c in header:
                    if r.get(c) and "-" in r[c] and retired_pattern.search(r[c]):
                        public = rights.get(c) in PUBLIC_RIGHTS and r.get("rights_class", "public_official") in PUBLIC_RIGHTS
                        hits[(table + "." + c, "PUBLIC_LEAK" if public else "internal_only_provenance")][table] += 1
        for (key, status), uses in sorted(hits.items()):
            add("legacy entity handle (column)", key, "", status, uses)
    for script, receipt in sorted((receipts or {}).items()):
        for key, n in sorted((receipt.get("legacy_entity_ids_dropped") or {}).items()):
            add("legacy entity handle (input column)", key, "", "dropped_not_translated", {script: int(n)})
    summary = defaultdict(lambda: defaultdict(lambda: {"keys": 0, "rows": 0}))
    for r in rows:
        cell = summary[r["key_family"]][r["status"]]
        cell["keys"] += 1
        cell["rows"] += int(r["affected_rows"])
    by_table = defaultdict(Counter)
    for token, uses in bound["uses"].items():
        prefix = KEY_CLASSES[decode_token(token)[0]][0]
        for table, n in uses.items():
            by_table[table][prefix] += n
    return MIGRATION_HEADER, rows, {
        "by_key_family": {f: {s: dict(v) for s, v in sorted(st.items())} for f, st in sorted(summary.items())},
        "bound_id_values_by_table_and_prefix": {t: dict(sorted(c.items())) for t, c in sorted(by_table.items())}}


# ---------------------------------------------------------------- vocabularies
RIGHTS_CLASSES = {
    "public_official": "Official government/tribal publication; attributed, publishable after transformation review",
    "public_derived": "Computed only from public_official fields by a documented method",
    "public_first_party": "Self-published by the operator/property/tribe (e.g. a casino's own site); publishable for self-description (name, address, status, self-described affiliation), never independent proof of ownership, legal control, revenue allocation or tribal retention",
    "secondary_corroboration": "Secondary compilation (press, industry tracker) reproducing figures; source-limited until matched to the original regulator record",
    "internal_vendor": "Commercial directory / Casino City Press / trade-directory lineage; internal QA only",
    "internal_model": "Modeled, estimated, IMPLAN or research-inferred value; internal QA only",
    "internal_crosswalk": "Identifier kept for reconciliation, never a public key",
    "withheld_unverified": "No independent publishable evidence yet; withheld",
    "withheld_suppressed": "Source-suppressed or confidentiality-limited; withheld",
}
PUBLIC_RIGHTS = {"public_official", "public_derived", "public_first_party"}

RELATIONSHIP_TYPES = {
    "owner", "operator", "affiliate", "licensee", "landholder", "beneficiary",
    "management_contractor", "other_documented",
    # reported-unit relationships (online sportsbook series, shared reports)
    "reported_for", "licensed_to", "operated_by", "located_at",
}
# A shared reported total is stored once; linked entities never receive a copy.
ALLOCATION_STATUSES = {"not_allocated", "source_allocated", "allocation_unknown", "single_entity"}
REVIEW_STATUSES = {"source_asserted", "machine_matched", "reviewed_confirmed",
                   "reviewed_disputed", "unresolved"}
CONFIDENCE = {"high", "medium", "low"}
DATE_PRECISIONS = {"day", "month", "year", "fiscal_year", "unknown"}
PUBLICATION_STATUSES = {"public", "internal", "withheld", "unresolved", "source_limited"}

ISO_DATE_RE = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")

# Columns every evidence-bearing component row carries (subset per table allowed
# only when declared in its contract's `evidence_exempt`).
EVIDENCE_COLUMNS = ("source_system", "source_record_id", "source_url",
                    "source_date", "retrieved_date", "rights_class")


# ---------------------------------------------------------------- inputs
class Inputs:
    """Read canonical CSVs once, with byte hashes recorded for the manifest."""

    def __init__(self, root: Path | str | None = None):
        self.root = Path(root or DEFAULT_INPUT_ROOT).resolve()
        if not (self.root / "data" / "clean").is_dir():
            raise SystemExit(f"REFUSED: no populated data/clean under {self.root}")
        self.receipts: dict[str, dict] = {}

    def path(self, relative: str) -> Path:
        return self.root / relative

    def read(self, relative: str, required: bool = True):
        """Return (header, rows). Relative to the input root, e.g. data/clean/x.csv."""
        p = self.path(relative)
        if not p.is_file():
            if required:
                raise SystemExit(f"REFUSED: missing required input {relative}")
            self.receipts[relative] = {"path": relative, "status": "ABSENT"}
            return [], []
        raw = p.read_bytes()
        self.receipts[relative] = {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(),
                                   "bytes": len(raw), "status": "READ"}
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="strict"), newline=""))
        rows = list(reader)
        self.receipts[relative]["rows"] = len(rows)
        return list(reader.fieldnames or []), rows

    def clean(self, name: str, required: bool = True):
        return self.read("data/clean/" + name, required)

    def repository(self, relative: str):
        """A reviewed disposition file tracked in this repository (e.g.
        docs/GAMING_VP_DISPOSITIONS_2026-09-24.csv), hashed like an input.
        Recorded with scope `repository` so the runner rechecks it there."""
        p = HERE.parent / relative
        raw = p.read_bytes()
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="strict"), newline=""))
        rows = list(reader)
        self.receipts[relative] = {"path": relative, "scope": "repository", "status": "READ",
                                   "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                                   "rows": len(rows)}
        return list(reader.fieldnames or []), rows


# ---------------------------------------------------------------- validation
class GamingContractError(ValueError):
    pass


def validate_rows(table: str, header, rows, contract: dict) -> list[str]:
    """Shared structural checks. Returns problems; callers refuse on any."""
    problems = []
    pk = contract["primary_key"]
    missing = [c for c in contract.get("required", []) + pk if c not in header]
    if missing:
        return [f"{table}: missing declared columns {missing}"]
    seen = Counter(tuple(r.get(k, "") for k in pk) for r in rows)
    dup = [k for k, n in seen.items() if n > 1]
    if dup:
        problems.append(f"{table}: {len(dup)} duplicate primary keys e.g. {dup[:3]}")
    if any(not all(k) for k in seen):
        problems.append(f"{table}: blank primary-key part")
    for col, allowed in contract.get("enums", {}).items():
        bad = Counter(r.get(col, "") for r in rows if r.get(col, "") not in allowed)
        if bad:
            problems.append(f"{table}.{col}: values outside vocabulary {dict(bad.most_common(5))}")
    for col in contract.get("dates", []):
        bad = [r.get(col) for r in rows if r.get(col) and not ISO_DATE_RE.match(r[col])]
        if bad:
            problems.append(f"{table}.{col}: {len(bad)} non-ISO dates e.g. {bad[:3]}")
    for lo, hi in contract.get("intervals", []):
        bad = [r for r in rows if r.get(lo) and r.get(hi) and r[hi] < r[lo]]
        if bad:
            problems.append(f"{table}: {len(bad)} rows with {hi} before {lo}")
    for col in contract.get("public_id_columns", []):
        leaked = [r[col] for r in rows if VENDOR_ID_RE.match(r.get(col, "") or "")
                  or (r.get(col) or "").startswith("PROV-")]
        if leaked:
            problems.append(f"{table}.{col}: vendor-lineage or provisional ID in public ID column e.g. {leaked[:3]}")
    for col in [c for c in header if c == "cedar_uid" or c.endswith("_cedar_uid")]:
        legacy = [r[col] for r in rows if r.get(col) and not is_ce_uid(r[col])]
        if legacy:
            problems.append(f"{table}.{col}: non-CE entity IDs e.g. {legacy[:3]}")
    for col in [c for c in header if c == "gaming_facility_id" or c.endswith("_gaming_facility_id")]:
        bad = [r[col] for r in rows if r.get(col) and not is_place_id(r[col])]
        if bad:
            problems.append(f"{table}.{col}: not a checked CEDAR-PLACE facility ID e.g. {bad[:3]}")
    for col in [c for c in header if c == "enterprise_id" or c.endswith("_enterprise_id")]:
        bad = [r[col] for r in rows if r.get(col) and not is_enterprise_id(r[col])]
        if bad:
            problems.append(f"{table}.{col}: not an existing Cedar NEED enterprise ID e.g. {bad[:3]}")
    for col in [c for c in header if c == "business_uid" or c.endswith("_business_uid")]:
        bad = [r[col] for r in rows if r.get(col) and not BUSINESS_UID_RE.match(r[col])]
        if bad:
            problems.append(f"{table}.{col}: not a CB business ID e.g. {bad[:3]}")
    if "rights_class" in header:
        bad = Counter(r["rights_class"] for r in rows if r["rights_class"] not in RIGHTS_CLASSES)
        if bad:
            problems.append(f"{table}.rights_class: unknown classes {dict(bad)}")
    for col in contract.get("derived_ids", {}):
        prefix = contract["derived_ids"][col]
        bad = [r[col] for r in rows if r.get(col) and not is_derived_id(r[col], prefix)]
        if bad:
            problems.append(f"{table}.{col}: malformed component IDs e.g. {bad[:3]}")
    return problems


def public_projection(table: str, header, rows, field_rights: dict):
    """Drop every field whose rights class is not public, and every row whose
    row-level rights_class is not public. Refuses an unclassified field."""
    unclassified = [c for c in header if c not in field_rights]
    if unclassified:
        raise GamingContractError(f"{table}: unclassified fields {unclassified}")
    keep = [c for c in header if field_rights[c] in PUBLIC_RIGHTS]
    out = [{c: r.get(c, "") for c in keep} for r in rows
           if r.get("rights_class", "public_official") in PUBLIC_RIGHTS]
    return keep, out


# ---------------------------------------------------------------- public leak gate
_PROV_RE = re.compile(r"(?<![A-Za-z0-9])PROV-")
_VENDOR_ANY_RE = re.compile(r"(?<![A-Za-z0-9])(?:CCP|VP|TPL|CEDAR-FAC)-\d+(?![0-9])")


def leak_findings(table: str, header, rows, *, retired_pattern=None, bindings_status=None,
                  require_issued=False) -> Counter:
    """Counter[(finding, column)] over already-public rows. Findings:
    provisional, key token, vendor/source facility key, retired entity handle
    (exact historical membership via `retired_pattern`), non-CE uid, malformed
    Gaming object ID, place/enterprise ID failing its check characters, and
    (require_issued) a Gaming object ID whose binding is not ISSUED."""
    found = Counter()
    for r in rows:
        for col in header:
            v = r.get(col) or ""
            if not v:
                continue
            if _PROV_RE.search(v):
                found[("provisional identifier (PROV-)", col)] += 1
            if TOKEN_RE.search(v) or "GKEY~" in v:
                found[("unbound key token", col)] += 1
            if _VENDOR_ANY_RE.search(v):
                found[("vendor/source facility key", col)] += 1
            if retired_pattern is not None and retired_pattern.search(v):
                found[("retired entity handle", col)] += 1
            if (col == "cedar_uid" or col.endswith("_cedar_uid")) and not all(
                    is_ce_uid(p.strip()) for p in v.split("|") if p.strip()):
                found[("non-CE entity identifier", col)] += 1
            if (col == "gaming_facility_id" or col.endswith("_gaming_facility_id")) and not is_place_id(v):
                found[("unchecked facility identifier", col)] += 1
            if (col == "enterprise_id" or col.endswith("_enterprise_id")) and not is_enterprise_id(v):
                found[("non-NEED enterprise identifier", col)] += 1
            for m in ISSUED_ANY_RE.finditer(v):
                oid = m.group(0)
                if issued_ordinal(oid) is None:
                    found[("malformed Gaming object identifier", col)] += 1
                elif require_issued and (bindings_status or {}).get(oid) != "ISSUED":
                    found[("Gaming identifier not ISSUED in the live binding register", col)] += 1
    return found


# ---------------------------------------------------------------- writing
def write_table(out_dir: Path, table: str, header, rows, contract: dict) -> dict:
    """Validate, sort by primary key, write LF UTF-8 CSV; return a receipt."""
    problems = validate_rows(table, header, rows, contract)
    if problems:
        raise GamingContractError("REFUSED: " + "; ".join(problems))
    pk = contract["primary_key"]
    rows = sorted(rows, key=lambda r: tuple(r.get(k, "") for k in pk))
    data = csv_bytes(header, rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / table).write_bytes(data)
    return {"table": table, "rows": len(rows), "columns": len(header),
            "sha256": hashlib.sha256(data).hexdigest(), "grain": contract["grain"],
            "primary_key": pk}
