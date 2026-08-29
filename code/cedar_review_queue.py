#!/usr/bin/env python3
"""
cedar_review_queue - SUBTRACT THE SUBJECTS THE OWNER HAS ALREADY RULED,
before a review queue is written to disk.

    import cedar_review_queue as RQ

    ruled = RQ.already_ruled()                     # built once, reused
    kept, removed, notes = RQ.subtract(rows, ruled)
    RQ.write_removals(path, removed)               # count what you drop, by name

WHY THIS EXISTS
---------------
`review/np_schedule_i_recipients_2026-08-12.csv` asks the owner to rule on
**2,138 recipients**, and **30 of those rows carry an EIN he has already ruled
tier X** - among them `UNITED WAY OF THE GREATER CHIPPEWA VALLEY INC`, the
exact case the whole tier-inheritance rule was built on. Being asked again
about an entity you have already adjudicated is not a small annoyance: it is
the signal that the ruling never reached the thing that generates the
questions, and it is what the owner raised on 2026-08-26.

**The fix has to be structural.** Deleting 30 rows from one file fixes one
file; every queue writer that lands tomorrow re-creates the problem. So the
subtraction lives here, once, and every review-queue writer calls it.

READ THE OUTCOME, NOT THE STATUS
--------------------------------
`data/clean/cedar_ruling_ledger_consolidated.csv` carries both.

    `status`  says the ruling was PROCESSED  - SETTLED / CONFLICT_NOT_APPLIED
    `outcome` says what it DECIDED           - ENTITY / NEGATIVE / HOLD / ...

Filtering on `status == SETTLED` is the defect this project has already paid
for twice in one day: a ruling read SETTLED while its `outcome` was
`HOLD_OVER_OWNER` - "HOLD - RETRACTION REQUIRED". This module never branches
on `status`. It branches on `outcome`, and the three groups below are the whole
policy, written where it can be argued with.

WHAT COUNTS AS ADJUDICATED
--------------------------
**ADJUDICATED** - the owner answered. Subtract it.
  `ENTITY`             he named the owner
  `NEGATIVE`           he said not Native / not this entity
  `CLASS`              he ruled the class rather than the owner
  `HOLD`               he said "do not attribute yet"
  `HOLD_OVER_OWNER`    he said hold, over a positive owner ruling
  `UNRESOLVED_ENTITY`  he answered; Cedar could not resolve the name he gave

`HOLD` is deliberately in that list. `173_consolidate_rulings_ledger.py` says
it in its own docstring: *"HOLD / BLOCKED are DECISIONS, not absences. They are
written as an explicit status **so the subject stops re-entering the queue**."*
A queue that re-asks a HOLD has read a decision as a silence.

**CONFLICTED** - he ruled MORE THAN ONCE and the rulings disagree
(`POSITIVE_VS_NOT_NATIVE`, `TWO_DIFFERENT_UNRESOLVED_OWNERS`,
`OWNER_VS_DIFFERENT_UNRESOLVED_OWNER`, `TWO_DIFFERENT_CLASSES`,
`CLASS_CONTRADICTS_OWNER_SPINE_CLASS`). These are **KEPT**, because a tie
genuinely needs a human - but they are ANNOTATED, so the card says *"you have
ruled this twice and they disagree"* instead of asking as though it were new.
Subtracting them would hide a contradiction; asking blind is what produced it.

**UNKNOWN** - an outcome token in neither group. KEPT and NAMED, never
silently treated as unruled. A new vocabulary upstream must be visible the day
it lands.

THE SECOND SOURCE: the identifier ledger's tier X
-------------------------------------------------
`cedar_identifier_ledger_final.csv` rows at `confidence_tier = X` are the
owner's exclusions on an identifier. Those subjects are adjudicated too, and
they are the leg the Schedule I queue was missing. Tier X is read as a
NEGATIVE adjudication; no other tier is read as anything - a tier-A row means
Cedar attributed it, not that a human ruled it, and that distinction is the
one this project keeps re-learning.

WHAT THIS MODULE WILL NOT DO
----------------------------
  * It never edits a queue in place and never deletes a row from disk. It
    returns two lists and lets the caller write both.
  * It never matches on a name alone when an identifier is present on the row.
    An identifier is exact; a name is a guess, and a queue subtraction that
    guesses removes a question nobody answered.
  * Name matching is exact-normalised only, through
    `173_consolidate_rulings_ledger.norm_name` - the same normaliser that
    built the keys. No containment, no token overlap. The containment defect
    has cost this project five false attributions.
"""

import csv
import importlib.util
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

CONSOLIDATED = CLEAN / "cedar_ruling_ledger_consolidated.csv"
IDENTIFIER_LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

# --------------------------------------------------------------------------
# THE POLICY. Three groups, no fourth, and an unrecognised token is not
# silently folded into any of them.
# --------------------------------------------------------------------------

ADJUDICATED_OUTCOMES = frozenset({
    "ENTITY", "NEGATIVE", "CLASS", "HOLD", "HOLD_OVER_OWNER",
    "UNRESOLVED_ENTITY",
})

CONFLICTED_OUTCOMES = frozenset({
    "POSITIVE_VS_NOT_NATIVE", "TWO_DIFFERENT_UNRESOLVED_OWNERS",
    "OWNER_VS_DIFFERENT_UNRESOLVED_OWNER", "TWO_DIFFERENT_CLASSES",
    "CLASS_CONTRADICTS_OWNER_SPINE_CLASS",
})

#: Column-name shapes that carry a subject identifier on a review row.
IDENT_COLUMN_PATTERNS = (
    ("EIN", re.compile(r"(^|_)ein$|^ein$|_ein$", re.I)),
    ("UEI", re.compile(r"(^|_)uei$|^uei$|_uei$", re.I)),
    ("CAGE", re.compile(r"(^|_)cage(_code)?$", re.I)),
)

#: Column-name shapes that carry a subject NAME. Used only when the row has no
#: identifier at all.
NAME_COLUMN_RE = re.compile(
    r"^(name|subject_name|recipient_name(_as_filed)?|organisation|organization|"
    r"org_name|legal_business_name|entity_name|filer_name|party_name|"
    r"name_as_(filed|recorded)|record_name|observed_name|client_name|"
    r"registrant_name|auditee_name|firm_name|candidate_name)$", re.I)

#: A subject_key column, where a queue already speaks the ledger's language.
SUBJECT_KEY_RE = re.compile(r"^subject_key$", re.I)


def _load_numbered(stem, alias):
    spec = importlib.util.spec_from_file_location(alias, CODE / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm_name(s):
    """The consolidator's own normaliser, imported, never re-implemented.

    Falls back to an equivalent local implementation only if 173 cannot be
    loaded, and SAYS SO on the object, so a caller can tell a real match from
    a degraded one.
    """
    global _NORM
    if _NORM is None:
        try:
            _NORM = _load_numbered("173_consolidate_rulings_ledger",
                                   "m173_rq").norm_name
            norm_name.imported_from_173 = True
        except Exception:                              # noqa: BLE001
            norm_name.imported_from_173 = False

            def _fallback(x):
                x = (x or "").lower()
                x = re.sub(r"[^a-z0-9 ]+", " ", x)
                x = re.sub(r"\b(inc|incorporated|llc|l l c|ltd|limited|co|"
                           r"corp|corporation|company|the|a|an|and|of|llp|lp|"
                           r"plc|pc|dba)\b", " ", x)
                return re.sub(r"\s+", " ", x).strip()
            _NORM = _fallback
    return _NORM(s)


_NORM = None
norm_name.imported_from_173 = None


def digits(s):
    return re.sub(r"\D", "", s or "")


def ein_key(s):
    d = digits(s)
    return d.zfill(9) if d else ""


def _ident_key(kind, value):
    v = (value or "").strip()
    if not v:
        return ""
    if kind == "EIN":
        v = ein_key(v)
        return f"EIN:{v}" if v else ""
    return f"{kind}:{v.upper()}"


# --------------------------------------------------------------------------

class AlreadyRuled:
    """Every subject the owner has adjudicated, and how.

    `.verdict(key)` -> ("ADJUDICATED"|"CONFLICTED"|"UNKNOWN", outcome, why)
    or None when the subject has never been ruled.
    """

    def __init__(self):
        self.by_key = {}            # "EIN:012345678" -> (group, outcome, why)
        self.by_name = {}           # normalised name  -> (group, outcome, why)
        self.counts = Counter()
        self.unknown_outcomes = Counter()
        self.sources = []

    def _put(self, key, group, outcome, why):
        if not key:
            return
        prev = self.by_key.get(key)
        # ADJUDICATED beats CONFLICTED beats UNKNOWN. A subject with one clean
        # ruling and one contested one has been answered at least once, and
        # the contested reading is preserved in `why`.
        rank = {"ADJUDICATED": 0, "CONFLICTED": 1, "UNKNOWN": 2}
        if prev is None or rank[group] < rank[prev[0]]:
            self.by_key[key] = (group, outcome, why)

    def verdict_for_row(self, row):
        """(group, outcome, why, matched_on) or None.

        Identifiers first, in EIN / UEI / CAGE order, then `subject_key`, then
        - only if the row carries no identifier at all - an exact-normalised
        name. A row that has an identifier is NEVER decided on its name.
        """
        for kind, pat in IDENT_COLUMN_PATTERNS:
            for col, val in row.items():
                if not col or not pat.search(col):
                    continue
                k = _ident_key(kind, val)
                if k and k in self.by_key:
                    g, o, w = self.by_key[k]
                    return g, o, w, f"{col}={val}"
        for col, val in row.items():
            if col and SUBJECT_KEY_RE.match(col) and (val or "").strip():
                k = (val or "").strip()
                if ":" in k:
                    kind, ident = k.split(":", 1)
                    k = _ident_key(kind.upper(), ident) or k
                if k in self.by_key:
                    g, o, w = self.by_key[k]
                    return g, o, w, f"subject_key={val}"
        has_ident = any(
            (v or "").strip()
            for kind, pat in IDENT_COLUMN_PATTERNS
            for c, v in row.items() if c and pat.search(c))
        if has_ident:
            return None                 # exact key present and it did not hit
        for col, val in row.items():
            if col and NAME_COLUMN_RE.match(col) and (val or "").strip():
                n = norm_name(val)
                if n and n in self.by_name:
                    g, o, w = self.by_name[n]
                    return g, o, w, f"{col}~{n}"
        return None


def _read(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def already_ruled(consolidated=CONSOLIDATED, ledger=IDENTIFIER_LEDGER,
                  verbose=False):
    """Build the adjudicated-subject index from BOTH sources.

    Absent source files are reported, never silently treated as empty: "no
    rulings on file" and "the file is missing" are opposite findings.
    """
    ar = AlreadyRuled()

    if Path(consolidated).exists():
        rows = _read(consolidated)
        ar.sources.append(f"{Path(consolidated).name} ({len(rows):,} rulings)")
        for r in rows:
            outcome = (r.get("outcome") or "").strip().upper()
            key = (r.get("subject_key") or "").strip()
            if ":" in key:
                kind, ident = key.split(":", 1)
                nk = _ident_key(kind.upper(), ident)
                key = nk or key
            if outcome in ADJUDICATED_OUTCOMES:
                group = "ADJUDICATED"
            elif outcome in CONFLICTED_OUTCOMES:
                group = "CONFLICTED"
            else:
                group = "UNKNOWN"
                ar.unknown_outcomes[outcome or "(blank)"] += 1
            why = (f"{Path(consolidated).name}: outcome={outcome or '(blank)'}"
                   f"; ruled {(r.get('ruling_date') or '?').strip()}"
                   f"; ruling={(r.get('ruling') or '').strip()[:80]}")
            ar.counts[group] += 1
            if key.startswith("NAME:"):
                n = key.split(":", 1)[1]
                if n and (n not in ar.by_name
                          or group == "ADJUDICATED"):
                    ar.by_name[n] = (group, outcome, why)
            else:
                ar._put(key, group, outcome, why)
            nm = norm_name(r.get("subject_name"))
            if nm and group == "ADJUDICATED" and nm not in ar.by_name:
                ar.by_name[nm] = (group, outcome, why)
    else:
        ar.sources.append(f"{Path(consolidated).name} ABSENT - the "
                          f"consolidated-ruling leg of this filter measured "
                          f"NOTHING. That is UNMEASURED, not zero.")

    if Path(ledger).exists():
        rows = _read(ledger)
        n_x = 0
        for r in rows:
            if (r.get("confidence_tier") or "").strip().upper() != "X":
                continue
            n_x += 1
            kind = (r.get("identifier_type") or "").strip().upper()
            key = _ident_key(kind, r.get("identifier"))
            why = (f"{Path(ledger).name}: confidence_tier=X via "
                   f"{(r.get('attribution_method') or '?').strip()}; "
                   f"{(r.get('tier_rationale') or '').strip()[:100]}")
            ar.counts["ADJUDICATED"] += 1
            ar._put(key, "ADJUDICATED", "LEDGER_TIER_X", why)
        ar.sources.append(f"{Path(ledger).name} ({n_x:,} tier-X exclusions)")
    else:
        ar.sources.append(f"{Path(ledger).name} ABSENT - the tier-X leg of "
                          f"this filter measured NOTHING. UNMEASURED, not "
                          f"zero.")

    if verbose:
        print(f"  already-ruled index: "
              f"{len(ar.by_key):,} identifier subjects, "
              f"{len(ar.by_name):,} name subjects")
        for s in ar.sources:
            print(f"    from {s}")
        print(f"    norm_name imported from 173: "
              f"{norm_name.imported_from_173}")
        if ar.unknown_outcomes:
            print(f"    !! outcome tokens in NEITHER declared group - these "
                  f"rows were KEPT, not subtracted:")
            for k, v in ar.unknown_outcomes.most_common():
                print(f"       {k!r}  {v:,}")
    return ar


ANNOTATION_COLUMN = "already_ruled_note"


def decide(rows, ruled=None, annotate=True):
    """One decision per input row, IN INPUT ORDER.

    Yields `(row_out, action)` where `action` is "KEEP" or "REMOVE". This is
    the primitive; `subtract` is the convenience built on it. A caller that
    has to preserve the position of rows it is NOT filtering (an answered
    ruling sitting between two questions) needs the per-row decision, not two
    unordered lists - reconstructing the alignment afterwards is a bug waiting
    to be written.
    """
    ruled = ruled or already_ruled()
    for r in rows:
        v = ruled.verdict_for_row(r)
        if v is None:
            yield r, "KEEP"
            continue
        group, outcome, why, matched = v
        if group == "ADJUDICATED":
            out = dict(r)
            out["removed_because"] = "ALREADY_RULED"
            out["removed_outcome"] = outcome
            out["removed_evidence"] = f"matched on {matched}; {why}"
            yield out, "REMOVE"
        else:
            out = dict(r)
            if annotate:
                out[ANNOTATION_COLUMN] = (
                    f"YOU HAVE RULED THIS BEFORE and the rulings disagree "
                    f"({outcome}). Matched on {matched}. {why}"
                    if group == "CONFLICTED" else
                    f"ruled before with an outcome this filter does not "
                    f"recognise ({outcome}). Matched on {matched}. {why}")
            yield out, "KEEP"


def subtract(rows, ruled=None, annotate=True):
    """(kept, removed, stats).

    `removed` rows carry three extra columns naming WHY they were removed, so
    the drop is auditable and reversible. `kept` rows that were ruled but
    CONFLICTED carry `already_ruled_note` instead of being dropped.
    """
    ruled = ruled or already_ruled()
    kept, removed = [], []
    stats = Counter()
    for out, action in decide(rows, ruled, annotate):
        if action == "REMOVE":
            removed.append(out)
            stats["removed_already_ruled"] += 1
            stats[f"removed_outcome_{out['removed_outcome']}"] += 1
        elif ANNOTATION_COLUMN in out:
            kept.append(out)
            stats["kept_conflicted"] += 1
        else:
            kept.append(out)
            stats["kept_never_ruled"] += 1
    return kept, removed, stats


def write_removals(path, removed):
    """Write the dropped rows out by name. `.part` then rename."""
    path = Path(path)
    if not removed:
        return None
    cols = []
    for r in removed:
        for c in r:
            if c not in cols:
                cols.append(c)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(removed)
    part.replace(path)
    return path


def filter_queue_file(src, dest=None, removals=None, ruled=None):
    """Convenience for a queue that is already on disk.

    Returns (n_in, n_kept, n_removed, stats). Writes nothing unless `dest` is
    given, and NEVER writes over `src` without an explicit `dest == src`.
    """
    src = Path(src)
    rows = _read(src)
    kept, removed, stats = subtract(rows, ruled)
    if removals:
        write_removals(removals, removed)
    if dest:
        dest = Path(dest)
        cols = []
        for r in kept:
            for c in r:
                if c not in cols:
                    cols.append(c)
        part = dest.with_suffix(dest.suffix + ".part")
        with open(part, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(kept)
        part.replace(dest)
    return len(rows), len(kept), len(removed), stats


__all__ = [
    "ADJUDICATED_OUTCOMES", "CONFLICTED_OUTCOMES", "ANNOTATION_COLUMN",
    "AlreadyRuled", "already_ruled", "decide", "subtract", "write_removals",
    "filter_queue_file", "norm_name", "ein_key",
]
