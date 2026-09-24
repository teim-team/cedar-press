"""Shared contract for Cedar Grove Gaming Intelligence component producers.

Gaming is a Cedar Grove collection (`gaming`, shelf `grove` in
500_build_architecture_map.py), not one of the twelve Cedar Press storefront
collections. This module holds ONLY what every Gaming component producer must
share, so the components cannot drift apart:

* where canonical inputs are read from, with a SHA-256 receipt per input;
* derived component identifiers (deterministic from stable source keys; no
  allocator, no register mutation - `cedar_ids.allocate` remains the only
  minting service and is not called here);
* the field-level rights vocabulary and the public-projection gate;
* relationship and evidence vocabularies;
* the table writer and the shared validators every component table passes.

It is NOT a second release runner, catalog, manifest format, ID allocator or
publication policy. Release, catalog, entitlement and rollback go through
`code/build.py release-pilot` and Lumecon Data; public field decisions go
through `data/cedar/field_map.json` via `cedar_publication`. Identifier
bindings live in `cedar_ids.IDENTIFIER_CONTRACTS`.

Public identifiers (see docs/GAMING_GROVE_DATA_CONTRACT.md):
    cedar_uid          Native entity (CE register, 503_identity.py)
    enterprise_id      NEED enterprise (CEDAR-NEST, 1072) - operator/holding co.
    gaming_facility_id physical gaming property = existing cedar_place_id
                       (CEDAR-PLACE, 1129_place_ids.py). The legacy facility_id
                       (CCP-/VP-/TPL-/CEDAR-FAC) is an INTERNAL crosswalk only:
                       CCP- values equal Casino City property numbers.
    component IDs      derived here: <PREFIX>-<12 hex>, from source keys.
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# Canonical inputs live in the populated (ignored) Cedar data workspace, which
# is not this checkout when building from a worktree. Refuse to guess.
DEFAULT_INPUT_ROOT = Path(os.environ.get(
    "CEDAR_GAMING_INPUT_ROOT", str(Path.home() / "Desktop" / "Cedar Press")))

SCHEMA_VERSION = "cedar.grove.gaming.v1"

# ---------------------------------------------------------------- identifiers
# Derived, not minted: the same source key always yields the same ID, so a
# rebuild cannot renumber. Prefixes are a closed set; adding one is a contract
# change recorded in docs/GAMING_GROVE_DATA_CONTRACT.md.
DERIVED_PREFIXES = {
    "GREV": "regional/national revenue observation",
    "GBND": "revenue-band observation",
    "GFNM": "facility name/alias period",
    "GFST": "facility status period or history event",
    "GFCP": "facility capacity/amenity observation",
    "GREL": "facility-entity-enterprise relationship",
    "GPAY": "government payment / revenue-sharing observation",
    "GLIC": "license or regulatory authorization",
    "GREG": "regulatory event",
    "GENV": "environmental review",
    "GLAB": "labor or employment observation",
    "GFIN": "financial disclosure",
    "GLIT": "litigation or administrative proceeding",
    "GADV": "advocacy/lobbying link (points at the Advocacy collection's own ID)",
    "GSRC": "source observation / source registry record",
    "GSBK": "online sportsbook reported unit (brand, license or shared report series)",
    "GFOB": "gaming financial observation (one reported unit x period x revision)",
    "GGAP": "machine-readable coverage gap",
}
_DERIVED_RE = re.compile(r"^(%s)-[0-9A-F]{12}$" % "|".join(DERIVED_PREFIXES))


# OWNER HOLD 2026-09-24: no Gaming identifier is issued until Codex returns the
# CICD identifier-retirement audit and the allowed-ID contract (see
# docs/GAMING_ID_CONTRACT_REQUEST.md). Until then every ID this module renders
# is PROVISIONAL: prefixed `PROV-`, refused by the release path, and only
# rendered at all when CEDAR_GAMING_PROVISIONAL_IDS=1 is set for a local
# structural dry run. Swapping in the approved contract is a change here only.
ID_CONTRACT_STATUS = "PENDING_CICD_RETIREMENT_AUDIT"
# Shape only; the check characters are verified by the one shared validator
# (503_identity.valid via cedar_ids) in is_ce_uid, never re-implemented here.
CE_UID_RE = re.compile(r"^CE-[0-9A-HJKMNP-TV-Z]{5}-[0-9A-HJKMNP-TV-Z]{2}$")


@__import__('functools').lru_cache(maxsize=None)
def is_ce_uid(value: str) -> bool:
    import cedar_ids
    return bool(CE_UID_RE.match(value or "")) and cedar_ids._entity_validator().valid(value)


class IdContractPending(RuntimeError):
    pass


def _require_provisional():
    if ID_CONTRACT_STATUS != "APPROVED" and os.environ.get("CEDAR_GAMING_PROVISIONAL_IDS") != "1":
        raise IdContractPending(
            "Gaming ID creation is paused pending the CICD identifier-retirement audit; "
            "set CEDAR_GAMING_PROVISIONAL_IDS=1 only for a non-promotable dry run")


def facility_id_for(place_id: str) -> str:
    """The ONE place a Gaming facility ID is rendered. The allowed-ID contract
    decides the namespace; until then a provisional wrapper of the existing
    CEDAR-PLACE value is used so lanes can build structure."""
    _require_provisional()
    if not PLACE_ID_RE.match(place_id or ""):
        raise ValueError(f"not a CEDAR-PLACE id: {place_id!r}")
    return "PROV-GFAC:" + place_id if ID_CONTRACT_STATUS != "APPROVED" else place_id


def checked_cedar_uid(value: str) -> str:
    """Current Native entities use only canonical CE- identifiers. Legacy
    CICD/handle prefixes (TRBF-, AKNF-, ANVC-, T-...) are refused, never
    translated here; translation belongs to a named read-only crosswalk."""
    v = (value or "").strip()
    if v and not is_ce_uid(v):
        raise ValueError(f"legacy or malformed entity id refused as cedar_uid: {v!r}")
    return v


def derive_id(prefix: str, *parts) -> str:
    """Stable component ID from stable source-key parts (never names alone)."""
    _require_provisional()
    if prefix not in DERIVED_PREFIXES:
        raise KeyError(f"undeclared Gaming component prefix {prefix!r}")
    clean = [str(p).strip() for p in parts]
    if not clean or not any(clean):
        raise ValueError(f"{prefix}: derived ID needs a nonblank source key")
    digest = hashlib.sha256(("\x1f".join([prefix] + clean)).encode("utf-8")).hexdigest()
    rendered = f"{prefix}-{digest[:12].upper()}"
    return rendered if ID_CONTRACT_STATUS == "APPROVED" else "PROV-" + rendered


def is_derived_id(value: str, prefix: str | None = None) -> bool:
    if ID_CONTRACT_STATUS != "APPROVED" and (value or "").startswith("PROV-"):
        value = value[5:]
    m = _DERIVED_RE.match(value or "")
    return bool(m) and (prefix is None or m.group(1) == prefix)


# Vendor-lineage identifiers that must never appear in a public ID column.
VENDOR_ID_RE = re.compile(r"^(?:CCP|VP|TPL)-\d+$")
PLACE_ID_RE = re.compile(r"^CEDAR-PLACE-\d{6}-[0-9A-Z]{2}$")
ENTERPRISE_ID_RE = re.compile(r"^CEDAR-NEST-\d{6}-[0-9A-Z]{2}$")

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
        leaked = [r[col] for r in rows if VENDOR_ID_RE.match(r.get(col, "") or "")]
        if leaked:
            problems.append(f"{table}.{col}: vendor-lineage ID in public ID column e.g. {leaked[:3]}")
    for col in [c for c in header if c == "cedar_uid" or c.endswith("_cedar_uid")]:
        legacy = [r[col] for r in rows if r.get(col) and not is_ce_uid(r[col])]
        if legacy:
            problems.append(f"{table}.{col}: non-CE entity IDs e.g. {legacy[:3]}")
    if "rights_class" in header:
        bad = Counter(r["rights_class"] for r in rows if r["rights_class"] not in RIGHTS_CLASSES)
        if bad:
            problems.append(f"{table}.rights_class: unknown classes {dict(bad)}")
    for col in contract.get("derived_ids", {}):
        prefix = contract["derived_ids"][col]
        bad = [r[col] for r in rows if r.get(col) and not is_derived_id(r[col], prefix)]
        if bad:
            problems.append(f"{table}.{col}: malformed derived IDs e.g. {bad[:3]}")
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


# ---------------------------------------------------------------- writing
def write_table(out_dir: Path, table: str, header, rows, contract: dict) -> dict:
    """Validate, sort by primary key, write LF UTF-8 CSV; return a receipt."""
    problems = validate_rows(table, header, rows, contract)
    if problems:
        raise GamingContractError("REFUSED: " + "; ".join(problems))
    pk = contract["primary_key"]
    rows = sorted(rows, key=lambda r: tuple(r.get(k, "") for k in pk))
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    w.writerows(rows)
    data = buf.getvalue().encode("utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / table).write_bytes(data)
    return {"table": table, "rows": len(rows), "columns": len(header),
            "sha256": hashlib.sha256(data).hexdigest(), "grain": contract["grain"],
            "primary_key": pk}
