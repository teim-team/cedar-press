#!/usr/bin/env python3
"""
Cedar Press - 251: apply the owner's negative EIN rulings to `np_orgs.tribe_id`.

THE DEFECT
----------
`review/np_ein_hub_exclusion_hits_2026-08-26.csv` holds 33 EINs an owner ruling
forbids. **27 of them are links `np_orgs.csv` still carries in `tribe_id`:**

    COLVILLE ROTARY CHARITABLE FOUNDATION   tribe_id = TRBF-COLVLL-00
    KIOWA COUNTY FARM BUREAU ASSOCIATION    tribe_id = TRBF-KIOWAT-00
    COWLITZ COUNTY DRUG COURT FOUNDATION    tribe_id = TRBF-COWLTZ-00
    CHICKASAW COUNTY HISTORICAL SOCIETY     tribe_id = TRBF-CHKSWN-00
    JEMEZ MOUNTAINS ELECTRIC FOUNDATION     tribe_id = TRBF-JEMEZP-00

Every one of the 27 arrived by `containment` **with a state conflict already
recorded on the row** - `resolver_containment;state_conflict:KS!=OK` - which is
the place-name defect AGENTS.md has paid for ten documented times. Every one
carries a ledger row that is tier X via `elijah_ruling` reading, verbatim and
identically on all 27:

    "Ruled by Elijah 2026-08-12: not a Native entity"

`167_link_nonprofit_family_via_ein_hub.py` found them and **did not overwrite
them**, because `tribe_id` is script 70's column and patching another script's
output is how the `09_import_rulings.py` regression happens. It set its own
`cedar_link_tier = X` and filed the review row. That caution was correct, and
it left a forbidden link live in a shipping column, which is not an outcome.

THE DECISION
------------
**Both halves of the fix, because either alone leaves the defect live.**

1. **`code/70_key_unjoined_datasets.py` now defers to the ruling at source.**
   A new `ledger_negative_ein_rulings()` reads the ledger's tier-X EIN leg, and
   `do_np_orgs` blocks on it before any name resolution. 70's nonprofit pass
   previously consulted `excluded_by_prior_ruling` and `funnel_stage` and never
   the ledger, which is where the owner's nonprofit exclusions actually live.
   This is what makes the fix survive a rebuild: `17_build_nonprofit_990.py`
   rebuilds `np_orgs.csv` from the IRS BMF and re-derives
   `excluded_by_prior_ruling` from its own exclusion file, so an in-place patch
   alone would be reverted the next time 17 ran.

2. **This script applies the same decision to the live file now**, on those 27
   rows only, so nothing waits on someone re-running 70 - which is a WHOLE-FILE
   re-key against a spine that has grown 1,310 -> 1,489 since it last ran, and
   is exactly the "re-running 57 rebuilds from the current spine and loses
   work" trap. A narrow in-place write is the smaller risk.

WHY THE BLOCK IS THE WHOLE EIN AND NOT ONE ENTITY
-------------------------------------------------
"not a Native entity" is a ruling about the ORGANISATION. It is not a redirect
naming a better owner. Where a ruling names a different owner the correct
handling is a REDIRECT and never a block (`elijah_ruling_redirect`, and
`docs/ANCSA_OWNERSHIP_RULING.md`: "corrections are made, never erased"), so
this script requires the blanket-negative grammar and leaves redirects to the
appliers that own them.

AND WHY THIS DOES NOT VIOLATE "REPOINT, DON'T BLACKLIST"
--------------------------------------------------------
That rule exists because `169_build_identifier_graph.py` reads tier X as a
NODE-LEVEL BLOCK, so marking a wrong attribution X would suppress the correct
attribution on the same identifier too. It applies where the identifier is
otherwise sound and a correct attribution exists. **Here there is none to
suppress**: the owner ruled the organisation is not Native, so the exclusion is
the answer rather than a way of hiding one. 169 already blocks these 27 EINs
today on `np_orgs.cedar_link_tier = X`, which 167 set - this script makes
`tribe_id` agree with a block the graph is already honouring.

WHAT IS WRITTEN, AND WHAT IS DELIBERATELY PRESERVED
---------------------------------------------------
Cleared / set on the 27 rows:

    tribe_id, tribe_canonical_name  -> ""      (the forbidden link)
    entity_tier                     -> "X"
    entity_match_method             -> ruled_not_a_native_entity
    entity_match_basis              -> the refusal, with the ruling quoted
    excluded_by_prior_ruling        -> "1"     (the column 70 already consults)
    exclusion_reason                -> the ruling, quoted, with provenance
    funnel_stage                    -> ruled_not_native
    confidence_tier                 -> "X"
    classification_ruling           -> place_name_coincidence

`entity_id` is asserted blank and left blank - it already is, because 70 writes
it only at tier A. `tribe_id_token_match` and `canonical_name_token_match` are
NOT cleared: the evidence of what was matched, and the state conflict that
should have stopped it, stay on the row. A correction is made, never erased.

`classification_ruling = place_name_coincidence` is the project's existing
negative token, set by `34_apply_nonprofit_rulings.py` for this exact shape and
recognised as non-Native by `169_build_identifier_graph.py`. It is reused rather
than invented - see the LATENT note below for why inventing one would be unsafe.

LATENT DEFECT FOUND WHILE DOING THIS - FIXED 2026-08-26, SEE BELOW
-------------------------------------------------------------------
`169_build_identifier_graph.py` decided "ruled Native" as

    if classification_ruling not in ("", "UNRULED", "place_name_coincidence"):
        np_ruled_native.add(ein)

That is an ALLOW-LIST OF NEGATIVES, which is the wrong polarity: **any new
negative ruling token silently becomes "ruled Native".** Writing
`not_a_native_entity` here - the obvious choice - would have done exactly that,
which is why this script reuses `place_name_coincidence`.

**FIXED 2026-08-26 by the 293 lint-consolidation pass.** 169 now calls
`cedar_domain.np_ruling_is_native()`, an ALLOW-LIST OF POSITIVES
(`native_controlled`, `tribally_controlled`, `native_serving`), and an
unrecognised token is UNKNOWN - never Native - and is counted and NAMED in
169's own output. Verified behaviour-identical on today's file: 89 EINs read as
ruled Native under both tests, because no unexpected token exists yet. **The
reuse of `place_name_coincidence` above is still correct and should stay** -
`34_apply_nonprofit_rulings.py` writes it and three other scripts recognise it -
but inventing a new negative token is no longer unsafe in 169.

    py -3 code/251_apply_np_ein_exclusions_to_np_orgs.py            # dry run
    py -3 code/251_apply_np_ein_exclusions_to_np_orgs.py --apply
"""

import csv
import os
import re
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
NP = CLEAN / "np_orgs.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
TODAY = date.today().isoformat()
SCRIPT = "251_apply_np_ein_exclusions_to_np_orgs"
BACKUP = NP.with_name(NP.name + f".bak_{TODAY}_pre_{SCRIPT}")

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

NEGATIVE_GRAMMAR = "not a native entity"


def load(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames), list(rd)


def negative_ein_rulings():
    """Re-derived from the LEDGER, not read from the review file.

    The review file is a report; the ledger is the ruling. Deriving it again
    means this script cannot apply an exclusion the ledger no longer holds.
    """
    _, rows = load(LEDGER)
    neg = {}
    for r in rows:
        if (r.get("identifier_type") or "").strip().upper() != "EIN":
            continue
        if (r.get("confidence_tier") or "").strip().upper() != "X":
            continue
        why = (r.get("tier_rationale") or "").strip()
        if NEGATIVE_GRAMMAR not in why.lower():
            continue
        e = re.sub(r"\D", "", r.get("identifier") or "")
        if e:
            neg.setdefault(e, (why,
                               (r.get("attribution_method") or "").strip(),
                               (r.get("canonical_name") or "").strip()))
    return neg


def main():
    apply = "--apply" in sys.argv
    print(f"=== 251: apply negative EIN rulings to np_orgs.tribe_id "
          f"({'APPLY' if apply else 'DRY RUN'}) ===\n")

    neg = negative_ein_rulings()
    print(f"  ledger EIN rows, tier X, blanket-negative grammar: {len(neg):,}")

    st0 = NP.stat()
    print(f"  np_orgs.csv mtime {st0.st_mtime_ns}  size {st0.st_size:,}")
    fields, rows = load(NP)
    print(f"  rows {len(rows):,}  columns {len(fields)}")

    hit, tally = [], Counter()
    for r in rows:
        e = re.sub(r"\D", "", r.get("EIN") or "")
        if not e or e not in neg:
            continue
        tally["EIN carries a negative ruling"] += 1
        if not (r.get("tribe_id") or "").strip():
            tally["...already unlinked, nothing to clear"] += 1
            continue
        # entity_id is the PUBLISHABLE key. It must already be blank, because
        # 70 writes it only at tier A. If it is not, that is a different and
        # larger defect and this script must not paper over it.
        if (r.get("entity_id") or "").strip():
            raise SystemExit(
                f"REFUSING: EIN {e} carries a FORBIDDEN link in the "
                f"publishable `entity_id` column ({r['entity_id']}), not only "
                f"in `tribe_id`. That is a bigger finding than this script's "
                f"scope. Nothing written.")
        # Capture the priors BEFORE anything is mutated - the review file has
        # to say what was cleared, and the row will not remember.
        hit.append((r, e, {
            "org_name": r.get("org_name", ""),
            "state": r.get("state", ""),
            "tribe_id": r.get("tribe_id", ""),
            "tribe_canonical_name": r.get("tribe_canonical_name", ""),
            "entity_tier": r.get("entity_tier", ""),
            "entity_match_method": r.get("entity_match_method", ""),
            "entity_match_basis": r.get("entity_match_basis", ""),
            "confidence_tier": r.get("confidence_tier", ""),
            "funnel_stage": r.get("funnel_stage", ""),
        }))
        tally["...link cleared"] += 1

    print()
    for k, v in tally.most_common():
        print(f"  {k:44s} {v:>5,}")
    print(f"\n  rows to change: {len(hit)}")
    for r, e, prior in hit:
        print(f"    {e:<10} {prior['org_name'][:48]:<48} "
              f"{prior['tribe_id']:<16} [{prior['entity_match_method']}]")

    if not hit:
        print("\n  nothing to do.")
        return
    if not apply:
        print("\n  dry run - nothing written. Re-run with --apply.")
        return

    for r, e, prior in hit:
        why, meth, against = neg[e]
        prov = (f"Applied {TODAY} by code/{SCRIPT} from the ledger's tier-X "
                f"EIN leg ({meth}, against {against}). Ruling, verbatim: "
                f"\"{why}\". The match this replaces was "
                f"'{prior['entity_match_basis'].strip()}' - "
                f"containment with a recorded state conflict, the place-name "
                f"defect. Evidence of the refused match is kept in "
                f"tribe_id_token_match / canonical_name_token_match; a "
                f"correction is made, never erased. "
                f"review/np_ein_hub_exclusion_hits_2026-08-26.csv")
        r["tribe_id"] = ""
        r["tribe_canonical_name"] = ""
        r["entity_tier"] = "X"
        r["entity_match_method"] = "ruled_not_a_native_entity"
        r["entity_match_basis"] = prov
        r["entity_keyed_date"] = TODAY
        r["excluded_by_prior_ruling"] = "1"
        r["exclusion_reason"] = prov
        r["funnel_stage"] = "ruled_not_native"
        r["confidence_tier"] = "X"
        r["classification_ruling"] = "place_name_coincidence"
        r["ruling_authority"] = meth or "elijah_ruling"
        r["ruling_date"] = "2026-08-12"

    st1 = NP.stat()
    if (st1.st_mtime_ns, st1.st_size) != (st0.st_mtime_ns, st0.st_size):
        raise SystemExit("REFUSING: np_orgs.csv changed while being read. "
                         "Another agent is live on it. Nothing written.")
    shutil.copy2(NP, BACKUP)
    print(f"\n  backed up to {BACKUP.name}")

    tmp = NP.with_suffix(NP.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    st2 = NP.stat()
    if (st2.st_mtime_ns, st2.st_size) != (st0.st_mtime_ns, st0.st_size):
        os.remove(tmp)
        raise SystemExit("REFUSING at the last moment: np_orgs.csv changed "
                         "between read and rename. .part removed.")
    tmp.replace(NP)
    print("  renamed .part -> np_orgs.csv")

    f2, back = load(NP)
    assert f2 == fields, "columns changed - restore from the backup"
    assert len(back) == len(rows), "row count changed - restore from the backup"
    live = 0
    for r in back:
        e = re.sub(r"\D", "", r.get("EIN") or "")
        if e in neg and ((r.get("tribe_id") or "").strip()
                         or (r.get("entity_id") or "").strip()):
            live += 1
    print(f"\n  re-read: {len(back):,} rows, {len(f2)} columns, "
          f"{live} forbidden links still live (must be 0)")
    assert live == 0, "exclusion did not land - restore from the backup"

    dest = REVIEW / f"np_orgs_exclusions_applied_{TODAY}.csv"
    tmp2 = dest.with_suffix(dest.suffix + ".part")
    with open(tmp2, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ein", "org_name", "state", "cleared_tribe_id",
                    "cleared_tribe_canonical_name", "prior_entity_tier",
                    "prior_match_method", "prior_match_basis",
                    "prior_confidence_tier", "prior_funnel_stage",
                    "ruling_verbatim", "ruling_method", "ruling_against",
                    "applied_date"])
        for r, e, prior in hit:
            why, meth, against = neg[e]
            w.writerow([e, prior["org_name"], prior["state"],
                        prior["tribe_id"], prior["tribe_canonical_name"],
                        prior["entity_tier"], prior["entity_match_method"],
                        prior["entity_match_basis"],
                        prior["confidence_tier"], prior["funnel_stage"],
                        why, meth, against, TODAY])
    tmp2.replace(dest)
    print(f"  wrote {dest.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
