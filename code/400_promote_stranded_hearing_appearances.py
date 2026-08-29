#!/usr/bin/env python3
r"""400_promote_stranded_hearing_appearances.py -- Cedar Press.

Lands the ONE genuine stranding that the 399 sweep found, and refuses the
seventy-five that look identical from the outside.

WHAT IS STRANDED, AND WHY IT IS STRANDED
----------------------------------------
`98_build_oira_and_hearings.py` sweeps every House/Senate committee hearing
since the 112th Congress into `data/interim/hearing_appearances_corpus.csv`
(70,380 rows) and publishes the NATIVE SLICE to
`data/clean/hearing_appearances.csv` (2,667). That split is correct and is
declared in 98's own source; the corpus is context, not a product, and 399
records it as INTERMEDIATE-BY-DESIGN.

But the slice was computed on **2026-08-07, against the spine as it stood that
day.** The spine has grown to 1,534 entities since - the NHO layer landed later
(19 / 163). A corpus row whose `resolution_basis` is **`no_spine_match`** was
not refused; the entity simply DID NOT EXIST YET. Those rows are stranded by
nothing but calendar order, and re-running 98 to recover them is impossible
without a universe-wide network sweep.

    7 hearing appearances. Papa Ola Lokahi x5 -> NHO-PPLLKH-00,
    Kamehameha Schools x2 -> NHO-KMHMHS-00. Senate Committee on Indian
    Affairs hearings, 111th-119th Congress.

THE SEVENTY-FIVE THAT ARE NOT STRANDED, AND THE RULE THAT SAVES THEM
--------------------------------------------------------------------
83 corpus rows carry an EXACT normalised match to a current spine canonical
name or alias. Only 8 of them are `no_spine_match`. The other 75 carry an
EXPLICIT REFUSAL that 98's resolver already wrote down:

    refused_specificity                34   (Fort Belknap Indian Community,
                                             NAFOA, NCAI, and `DC)` / `DC:`)
    refused_missing_native_identity_word 10
    refused_single_token_uncorroborated 10   (Circle, FirstBank, Georgetown,
                                             Hopi, Enterprise, "Hamilton")
    ambiguous_core:2_spine_entities      7
    refused_containment_uncorroborated   7
    refused_state_disagreement           6
    ambiguous_containment:3              1

**A REFUSAL IS A RULING. Reading `entity_id == ""` as "unresolved" and
re-matching it is DEFECT 3 wearing a new coat** - the same shape as `148`
reading a RULED method as a POSITIVE ruling and publishing 317 owner
exclusions as confident attributions. `Circle` and `Georgetown` and `Hamilton`
are Alaska Native village names that are also ordinary English place words;
`FirstBank` is a CDFI name that is also a bank; `DC)` is a fragment of an
address. Script 262 paid for this exact lesson three hours ago with `Eagle`.

    THIS SCRIPT PROMOTES ONLY `resolution_basis == "no_spine_match"`.
    Anything beginning `refused_` or `ambiguous_` is REFUSED HERE TOO and
    written to review/, never silently dropped.

TIER IS INHERITED, NOT ASSIGNED
-------------------------------
The employment repair (262) and the top of START_HERE both say it: a tier is
INHERITED from the source row, never assigned by the consumer. This script
never picks a tier. It reads the tier/confidence that 98 ITSELF assigns to
`resolution_basis == "exact_name_only"` **out of the live published table** and
mirrors it. If 98's mapping ever changes, this script follows it; if the
published table holds more than one tier for that basis, this script REFUSES
to run rather than choose.

GUARD
-----
Every candidate is passed through `code/cedar_match_guard.py` - the central
veto layer whose eleven refuse-cases are eleven defects that reached
production. Its self-test must pass before a row is written.

SAFETY
  * refuses to write if `data/clean/hearing_appearances.csv` changed under it
  * backup tagged with THIS SCRIPT'S NAME (concurrency rule 1), never `pre400`
  * `.part` then rename (an interruption must not look like a completion)
  * dedupe on `hearing_appearance_id`, a deterministic id minted by 98 from
    the CHRG package id - never a rank, never a hash of a process
  * NEVER blanks an existing `entity_id`. A row already carrying a link keeps
    it; this script only fills blanks.
  * IN-PLACE ENRICHER. `98_build_oira_and_hearings.py` is a FULL REBUILD of
    this file and would revert it (defect 6). The `.bak_*_pre_400_*` file
    beside the output is the signal. If 98 is ever re-run, RUN THIS AFTER IT.

    py -3 code/400_promote_stranded_hearing_appearances.py --dry-run
    py -3 code/400_promote_stranded_hearing_appearances.py --apply
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
INTERIM = CEDAR / "data" / "interim"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"

sys.path.insert(0, str(CODE))
import cedar_domain as DOM                                       # noqa: E402
import cedar_match_guard as GUARD                                # noqa: E402

# Imported from cedar_domain, never re-spelled here - standing rule 8 applied to
# a vocabulary. If the class is renamed there, this refusal follows it.
DOM_INDIVIDUAL_NATIVE_CLASSES = frozenset({DOM.INDIVIDUAL_NATIVE_CLASS})

csv.field_size_limit(1 << 30)

SCRIPT = Path(__file__).stem
TODAY = dt.date.today().isoformat()

TARGET = CLEAN / "hearing_appearances.csv"
CORPUS = INTERIM / "hearing_appearances_corpus.csv"
SPINE_F = SPINE / "cedar_entity_spine.csv"

PROMOTABLE_BASIS = "no_spine_match"
MIRROR_BASIS = "exact_name_only"          # what this match IS, in 98's vocabulary

NEW_COLS = ["promoted_by_script", "promotion_basis"]


def read_rows(p: Path):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd), (rd.fieldnames or [])


def need(cols, *names, where=""):
    """DEFECT 2b. An absent column reads as an empty source; raise instead."""
    for n in names:
        if n not in cols:
            raise SystemExit("%s: column %r ABSENT. present: %s"
                             % (where, n, sorted(cols)[:14]))


def norm(s):
    """Case-fold FIRST, then strip punctuation.

    Written the other way round on the first draft - `re.sub(r"[^a-z0-9]+", " ",
    s).lower()` - and the dry run caught it: the character class also matches
    every UPPERCASE letter, so `AARP Foundation` normalised to `oundation`, as
    did a spine alias, and the script proposed to publish AARP, UPS, TD Bank and
    POPVOX as Native entities. 29 rows, every one confident-looking.

    It is defect 2 in a new place: OUR defect, dressed as a fact about the
    source. Keeping the note because the shape recurs - `[^a-z0-9]` is a
    case-SENSITIVE class and reads as a case-insensitive one.
    """
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def build_index(spine):
    """canonical + alias -> (tribe_id, spine_row, how). First writer wins, so
    a canonical name is never displaced by another entity's alias."""
    idx = {}
    for r in spine:
        n = norm(r["canonical_name"])
        if n and n not in idx:
            idx[n] = (r["tribe_id"], r, "canonical")
        for a in (r.get("aliases") or "").split("|"):
            an = norm(a)
            if an and an not in idx:
                idx[an] = (r["tribe_id"], r, "alias")
    return idx


def inherited_tier(clean_rows):
    """Read 98's OWN tier for `exact_name_only` out of the published table.

    NEVER assign. If the published table disagrees with itself, refuse.
    """
    seen = Counter((r["tier"], r["confidence"]) for r in clean_rows
                   if r.get("resolution_basis") == MIRROR_BASIS)
    if len(seen) != 1:
        raise SystemExit(
            "the published table holds %d distinct (tier, confidence) pairs for "
            "resolution_basis=%r: %s. This script will not choose one."
            % (len(seen), MIRROR_BASIS, seen.most_common()))
    (tier, conf), n = seen.most_common(1)[0]
    return tier, conf, n


def main():
    apply_ = "--apply" in sys.argv
    if not apply_ and "--dry-run" not in sys.argv:
        raise SystemExit(__doc__.strip().splitlines()[-2].strip())

    print("=" * 78)
    print("400 PROMOTE STRANDED HEARING APPEARANCES -- %s" % TODAY)
    print("=" * 78)

    # ---- concurrency rule 6: mtimes BEFORE anything ----------------------
    stamps = {p: p.stat().st_mtime for p in (TARGET, CORPUS, SPINE_F)}
    for p, t in stamps.items():
        age = (dt.datetime.now().timestamp() - t) / 60.0
        print("  %-46s %s  (%.0f min old)"
              % (p.relative_to(CEDAR).as_posix(),
                 dt.datetime.fromtimestamp(t).isoformat(timespec="seconds"), age))
        if age < 5:
            raise SystemExit(
                "%s was written under 5 minutes ago. Concurrency rule 6: a "
                "live writer owns it. Re-check and re-run." % p.name)

    if GUARD.__name__ and not hasattr(GUARD, "guard"):
        raise SystemExit("cedar_match_guard has no guard()")

    clean, ccols = read_rows(TARGET)
    corpus, xcols = read_rows(CORPUS)
    spine, scols = read_rows(SPINE_F)
    need(ccols, "hearing_appearance_id", "entity_id", "tier", "confidence",
         "organization_class", "resolution_basis", "native_slice_basis",
         where="hearing_appearances.csv")
    need(xcols, "hearing_appearance_id", "witness_organization", "entity_id",
         "resolution_basis", where="hearing_appearances_corpus.csv")
    need(scols, "tribe_id", "canonical_name", "aliases",
         where="cedar_entity_spine.csv")
    print("\n  published slice %6d rows" % len(clean))
    print("  corpus          %6d rows" % len(corpus))
    print("  spine           %6d entities" % len(spine))

    tier, conf, n_basis = inherited_tier(clean)
    print("  INHERITED tier for resolution_basis=%r: tier=%r confidence=%r "
          "(from %d published rows)" % (MIRROR_BASIS, tier, conf, n_basis))

    idx = build_index(spine)
    print("  spine exact-name keys: %d" % len(idx))

    # ---- candidates -------------------------------------------------------
    existing = {r["hearing_appearance_id"] for r in clean}
    cands, refused = [], []
    for r in corpus:
        if str(r.get("entity_id") or "").strip():
            continue                                  # already linked - leave it
        hit = idx.get(norm(r["witness_organization"]))
        if not hit:
            continue
        basis = (r.get("resolution_basis") or "").strip()
        tid, srow, how = hit
        if basis != PROMOTABLE_BASIS:
            refused.append((r, tid, srow, how, basis,
                            "EXISTING RULING: 98 recorded %r for this row. A "
                            "refusal is a ruling; re-matching it is defect 3."
                            % basis))
            continue
        # FAIL CLOSED ON THE INDIVIDUALLY NATIVE-OWNED CLASS.
        #
        # `cedar_domain.may_publish_individual_native_field` defaults to
        # WITHHOLDING and says so - "unknown field: withhold. Fail closed." -
        # because a firm's own website statement is our EVIDENCE, never its
        # PERMISSION. Attaching a named congressional witness to an
        # individually Native-owned FIRM is a linkage that class has its own
        # rules for, and those rules are a person's, not a table's. This
        # script does not have a ruling for it, so it does not make one.
        if (srow.get("entity_class", "") or "") in DOM_INDIVIDUAL_NATIVE_CLASSES:
            refused.append((r, tid, srow, how, basis,
                            "entity_class=%r is the individually Native-owned "
                            "class; cedar_domain.may_publish_individual_native_"
                            "field fails closed without an explicit consent "
                            "ruling. NEEDS-A-RULING, not an automatic link."
                            % srow.get("entity_class", "")))
            continue
        ok, why = GUARD.guard(
            r["witness_organization"],
            {"canonical_name": srow["canonical_name"],
             "entity_class": srow.get("entity_class", ""),
             "state": srow.get("state", "")},
            how="exact", context={})
        if not ok:
            refused.append((r, tid, srow, how, basis,
                            "cedar_match_guard veto: %s" % why))
            continue
        cands.append((r, tid, srow, how))

    print("\n  exact-name candidates in the corpus : %d"
          % (len(cands) + len(refused)))
    print("  REFUSED                             : %d" % len(refused))
    for b, n in Counter(x[4] for x in refused).most_common():
        print("        %-44s %d" % (b, n))
    print("  promotable (%s, guard clean)  : %d"
          % (PROMOTABLE_BASIS, len(cands)))

    promote = [c for c in cands if c[0]["hearing_appearance_id"] not in existing]
    enrich = [c for c in cands if c[0]["hearing_appearance_id"] in existing]
    print("\n  NEW rows to append   : %d" % len(promote))
    print("  EXISTING rows to link: %d  (already in the slice as an "
          "UNRESOLVED_NATIVE_MARKER; this only fills the blank entity_id)"
          % len(enrich))
    for r, tid, srow, how in promote:
        print("      + %-26s %-22s %s %s  -> %s (%s)"
              % (r["hearing_appearance_id"][:26], r["witness_organization"][:22],
                 r.get("congress", ""), r.get("hearing_date", ""), tid, how))
    for r, tid, srow, how in enrich:
        print("      ~ %-26s %-22s -> %s (%s)"
              % (r["hearing_appearance_id"][:26], r["witness_organization"][:22],
                 tid, how))

    if not apply_:
        print("\n  DRY RUN. nothing written. re-run with --apply")
        return 0

    # ---- build the new table ---------------------------------------------
    out_cols = list(ccols) + [c for c in NEW_COLS if c not in ccols]
    by_id = {}
    for r in clean:
        row = {c: r.get(c, "") for c in out_cols}
        by_id[r["hearing_appearance_id"]] = row

    n_enriched = 0
    for r, tid, srow, how in enrich:
        row = by_id[r["hearing_appearance_id"]]
        if str(row.get("entity_id") or "").strip():
            continue                       # never overwrite an existing link
        row["entity_id"] = tid
        row["organization_class"] = "NATIVE_ENTITY_SPINE"
        row["resolution_basis"] = MIRROR_BASIS
        row["native_slice_basis"] = "WITNESS_ORG_RESOLVED"
        row["tier"] = tier
        row["confidence"] = conf
        row["promoted_by_script"] = SCRIPT
        row["promotion_basis"] = (
            "entity_id filled from cedar_entity_spine on an exact %s-name match; "
            "corpus resolution_basis was %s (the spine did not hold this entity "
            "when 98 ran on 2026-08-07); tier inherited from 98's own mapping "
            "for %s" % (how, PROMOTABLE_BASIS, MIRROR_BASIS))
        n_enriched += 1

    n_added = 0
    for r, tid, srow, how in promote:
        row = {c: r.get(c, "") for c in out_cols}
        row["entity_id"] = tid
        row["organization_class"] = "NATIVE_ENTITY_SPINE"
        row["resolution_basis"] = MIRROR_BASIS
        row["native_slice_basis"] = "WITNESS_ORG_RESOLVED"
        row["tier"] = tier
        row["confidence"] = conf
        row["promoted_by_script"] = SCRIPT
        row["promotion_basis"] = (
            "promoted from data/interim/hearing_appearances_corpus.csv on an "
            "exact %s-name match to cedar_entity_spine; corpus resolution_basis "
            "was %s (the spine did not hold this entity when 98 ran on "
            "2026-08-07); cedar_match_guard clean; tier inherited from 98's own "
            "mapping for %s" % (how, PROMOTABLE_BASIS, MIRROR_BASIS))
        by_id[r["hearing_appearance_id"]] = row      # dedupe on the id
        n_added += 1

    rows_out = list(by_id.values())
    if len(rows_out) != len(clean) + n_added:
        raise SystemExit("row arithmetic: %d != %d + %d"
                         % (len(rows_out), len(clean), n_added))

    # ---- mtime re-check, then write --------------------------------------
    if TARGET.stat().st_mtime != stamps[TARGET]:
        raise SystemExit("hearing_appearances.csv CHANGED under this run. "
                         "Nothing written. Re-run.")

    bak = TARGET.with_name(TARGET.name + ".bak_%s_pre_%s" % (TODAY, SCRIPT))
    shutil.copy2(TARGET, bak)
    print("\n  backup  %s" % bak.name)

    part = TARGET.with_suffix(".csv.part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols)
        w.writeheader()
        w.writerows(rows_out)
    os.replace(part, TARGET)
    print("  wrote   %s  (%d -> %d rows, +%d columns)"
          % (TARGET.name, len(clean), len(rows_out), len(out_cols) - len(ccols)))
    print("  linked  %d existing row(s)" % n_enriched)

    # ---- the refusals go to review/, never to a counter -------------------
    # DEFECT 2c: a drop counter that does not NAME what it dropped is invisible.
    REVIEW.mkdir(parents=True, exist_ok=True)
    rp = REVIEW / ("hearing_appearance_exact_name_refused_%s.csv" % TODAY)
    rpart = rp.with_suffix(".csv.part")
    with open(rpart, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hearing_appearance_id", "witness_organization",
                    "witness_name", "congress", "chamber", "hearing_date",
                    "corpus_resolution_basis", "corpus_organization_class",
                    "spine_entity_that_matched", "spine_canonical_name",
                    "matched_via", "refusal_reason", "refused_by", "refused_date"])
        for r, tid, srow, how, basis, why in refused:
            w.writerow([r["hearing_appearance_id"], r["witness_organization"],
                        r.get("witness_name", ""), r.get("congress", ""),
                        r.get("chamber", ""), r.get("hearing_date", ""),
                        basis, r.get("organization_class", ""),
                        tid, srow["canonical_name"], how, why, SCRIPT, TODAY])
    os.replace(rpart, rp)
    print("  refusals -> review/%s  (%d rows, each naming the spine entity it "
          "would have matched and why it was refused)" % (rp.name, len(refused)))

    # ---- re-read and verify (concurrency rule 4) -------------------------
    back, bcols = read_rows(TARGET)
    ids = [r["hearing_appearance_id"] for r in back]
    assert len(ids) == len(set(ids)), "duplicate hearing_appearance_id after write"
    got = sum(1 for r in back if r.get("promoted_by_script") == SCRIPT)
    lost = [c for c in ccols if c not in bcols]
    if lost:
        raise SystemExit("COLUMNS LOST: %s" % lost)
    print("\n  RE-READ: %d rows, %d columns, %d carry promoted_by_script=%s, "
          "0 duplicate ids, 0 columns lost" % (len(back), len(bcols), got, SCRIPT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
