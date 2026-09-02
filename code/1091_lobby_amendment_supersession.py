#!/usr/bin/env python3
"""
Cedar Press - 1091: LDA AMENDMENT SUPERSESSION, as flags on the row.

    py -3 code/1091_lobby_amendment_supersession.py measure    # read-only
    py -3 code/1091_lobby_amendment_supersession.py apply      # enrich in place
    py -3 code/1091_lobby_amendment_supersession.py verify     # exit 1 on breach
    py -3 code/1091_lobby_amendment_supersession.py selftest   # prove it FIRES

WHY THIS EXISTS
---------------
`docs/METHODOLOGY_LOBBYING.md` describes the cleaning sequence as "amendments
applied over the originals they replace ... non-standard records
(registrations, terminations) set aside before any total is struck."

**The shipped file has never done this.** Measured 2026-09-02 on the live
`data/clean/native_entity_lobbying_disclosures.csv`, 27,825 rows:

    amendment rows                                       1,416   $41,640,996
    (client_id, registrant_id, filing_year, filing_period)
      groups holding an amendment AND a non-amendment    1,135   <- the doc's
                                                                    figure,
                                                                    reproduced
    naive SUM(spend_usd)                                 $725,743,974.52

and `data/clean/cedar_export_safety.csv` marks the table
`SAFE_TO_AGGREGATE / aggregation_safe = 1` - correctly for what 517 measures
(`filing_uuid` is unique, 0 literal duplicate rows) and NOT correctly for what
a buyer will do with `spend_usd`.

THE $28,961,112 IN THE DOC IS NOT REPRODUCIBLE, AND THE 1,135 IS
----------------------------------------------------------------
`docs/methodology/lobbying.md` states the double-count as "about
$28,961,112 - 4.0% of the $725.74M total". No script in the repo computes it
(grepped: the string appears only in that document, twice). Eight candidate
definitions were measured against the live file on 2026-09-02 and none
produces it:

    money on the non-amendment rows of the 1,135 mixed groups  $39,183,189.22
    money on the amendment rows of those groups                $36,347,996.01
    sum-minus-max within those groups                          $33,218,483.22
    all-but-latest-by-dt_posted within those groups            $40,119,485.01
    all-but-latest over every multi-row group                  $45,805,356.01
    sum-minus-min within those groups                          $47,866,925.01
    ... and the two filtered variants (attribution_withdrawn,
        org_type_barred) move it further away, not closer

The group count reproduces to the row. The dollar figure does not reproduce at
all, so this script publishes the number it can prove and the doc is corrected
to match, rather than the reverse.

THE NAIVE KEY IS AMBIGUOUS AND MUST NOT BE USED AS-IS
------------------------------------------------------
`(client_id, registrant_id, filing_year, filing_period)` puts a REGISTRATION
in the same bucket as the quarterly REPORT that follows it. Worked example,
the third such group in file order:

    key ('153096','43651','1999','mid_year')
      3014138c-...  Registration                 $0       posted 1999-03-29
      f8fa8e38-...  Registration - Amendment     $0       posted 1999-06-03
      bca72f60-...  Mid-Year Report         $60,000       posted 1999-08-13

A naive "the amendment supersedes the group" rule keeps the $0 registration
amendment and DELETES the $60,000 report. So the key here carries a fifth
component - the form family, REGISTRATION or REPORT - and even then it
REFUSES to supersede in the groups that still hold more than one
non-amendment row.

WHAT IT DOES - FLAGS, NEVER DELETIONS
--------------------------------------
Adds four columns to `data/clean/native_entity_lobbying_disclosures.csv`.
No row is dropped, no existing cell is touched, no money column is rewritten,
and no new money column is created (a fourth "tribal lobbying total" is the
last thing this collection needs - see docs/MONEY_TOTALLING_RULES.md).

    supersession_group_id       blake2b-80 digest of the five-part key
    supersession_status         one of the eight values below
    is_superseded               1 = a LATER filing in this group restates it
    superseded_by_filing_uuid   which one, or blank

    AMENDMENT_SURVIVOR                     the latest amendment; total THIS one
    SUPERSEDED_BY_AMENDMENT                an original an amendment replaced
    SUPERSEDED_BY_LATER_AMENDMENT          an amendment a later amendment
                                           replaced
    NOT_SUPERSEDED                         nothing in this group restates it
    AMBIGUOUS_MULTIPLE_ORIGINALS           amendment present, >1 original:
                                           REFUSED
    AMBIGUOUS_ORIGINAL_POSTED_AFTER_AMENDMENT  the last-posted row is not the
                                           amendment: REFUSED
    UNFLAGGED_DUPLICATE_CANDIDATE          >1 identical filing_type_display,
                                           no amendment flag. NOT superseded -
                                           the LDA never said one replaces the
                                           other
    REGISTRATION_NO_MONEY                  registration-family row, $0 by
                                           construction

The correct filing-grain total is `SUM(spend_usd) WHERE is_superseded = 0`.

INVARIANTS, each proved to FIRE by `selftest`
----------------------------------------------
    I1 ROW_CONSERVATION        out rows == in rows
    I2 MONEY_CONSERVATION      sum(income|expenses|spend) unchanged to the cent
    I3 CELL_PRESERVATION       every original column, every row, byte-identical
    I4 KEY_PRESERVATION        filing_uuid set unchanged and still unique
    I5 SUPERSEDER_RESOLVES     every superseded_by_filing_uuid exists, is in
                               the SAME group, and is NOT itself superseded
    I6 ONE_SURVIVOR_PER_GROUP  a group with any superseded row has exactly one
                               un-superseded row
    I7 DROP_ACCOUNTS_EXACTLY   total - superseded total == survivor total
    I8 FLAGS_REPRODUCE         (verify only) the stored flags equal a fresh
                               classification of the same file

Reads/writes  data/clean/native_entity_lobbying_disclosures.csv
Backup        .bak_<date>_pre_1091_lobby_amendment_supersession
"""
from __future__ import annotations

import csv
import hashlib
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLEAN = ROOT / "data" / "clean"
TARGET = CLEAN / "native_entity_lobbying_disclosures.csv"
TODAY = date.today().isoformat()
BAK_TAG = ".bak_%s_pre_1091_lobby_amendment_supersession" % TODAY

csv.field_size_limit(10_000_000)

NEW_COLS = ["supersession_group_id", "supersession_status",
            "is_superseded", "superseded_by_filing_uuid"]

KEY_COLS = ["client_id", "registrant_id", "filing_year", "filing_period"]
MONEY_COLS = ["income_usd", "expenses_usd", "spend_usd"]


# ---------------------------------------------------------------------------
def read_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        return r.fieldnames, list(r)


def money(s):
    s = (s or "").strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def total(rows, col, pred=None):
    return round(sum(money(r[col]) for r in rows
                     if pred is None or pred(r)), 2)


def family(display):
    """REGISTRATION or REPORT. 'Registration - Amendment' is a registration."""
    return "REGISTRATION" if display.startswith("Registration") else "REPORT"


def is_amendment(r):
    return "Amendment" in (r.get("filing_type_display") or "")


def group_key(r):
    return (r["client_id"], r["registrant_id"], r["filing_year"],
            r["filing_period"], family(r["filing_type_display"]))


def group_id(k):
    h = hashlib.blake2b("\x1f".join(k).encode("utf-8"), digest_size=10)
    return "lsg_" + h.hexdigest()


def posted_order(r):
    """Latest-wins ordering. dt_posted is ISO-ish; filing_uuid breaks ties so
    the choice is deterministic across runs and machines."""
    return ((r.get("dt_posted") or ""), r["filing_uuid"])


# ---------------------------------------------------------------------------
def classify(rows):
    """Return {filing_uuid: (group_id, status, is_superseded, by_uuid)}.

    Refuses wherever the key does not identify one filing. Refusing prints as
    a named AMBIGUOUS_* status on the row, never as a silent NOT_SUPERSEDED.
    """
    groups = defaultdict(list)
    for r in rows:
        groups[group_key(r)].append(r)

    out = {}
    for k, g in groups.items():
        gid = group_id(k)
        fam = k[4]
        amd = [r for r in g if is_amendment(r)]
        orig = [r for r in g if not is_amendment(r)]

        def put(r, status, by=""):
            out[r["filing_uuid"]] = (gid, status, "1" if by else "0", by)

        # --- no amendment anywhere: nothing in the LDA says one replaces
        #     another. A repeated filing_type_display is a CANDIDATE and is
        #     labelled as one; it is never superseded on our own authority.
        if not amd:
            dispdup = (len(orig) > 1 and
                       len({r["filing_type_display"] for r in orig}) == 1)
            for r in g:
                if fam == "REGISTRATION":
                    put(r, "REGISTRATION_NO_MONEY")
                elif dispdup:
                    put(r, "UNFLAGGED_DUPLICATE_CANDIDATE")
                else:
                    put(r, "NOT_SUPERSEDED")
            continue

        # --- amendment present but the key holds more than one original:
        #     which original the amendment amends is NOT KNOWABLE from the
        #     LDA fields we hold. Refuse.
        if len(orig) > 1:
            for r in g:
                put(r, "AMBIGUOUS_MULTIPLE_ORIGINALS")
            continue

        survivor = max(amd, key=posted_order)
        last = max(g, key=posted_order)
        # --- the last-posted row in the group is NOT the amendment. Under
        #     "latest restatement wins" that is a contradiction, so refuse
        #     rather than pick.
        if last["filing_uuid"] != survivor["filing_uuid"]:
            for r in g:
                put(r, "AMBIGUOUS_ORIGINAL_POSTED_AFTER_AMENDMENT")
            continue

        if len(g) == 1:
            put(survivor, "NOT_SUPERSEDED")
            continue

        put(survivor, "AMENDMENT_SURVIVOR")
        for r in g:
            if r["filing_uuid"] == survivor["filing_uuid"]:
                continue
            put(r, "SUPERSEDED_BY_LATER_AMENDMENT" if is_amendment(r)
                else "SUPERSEDED_BY_AMENDMENT", survivor["filing_uuid"])
    return out


# ---------------------------------------------------------------------------
def invariants(before_hdr, before, after_hdr, after):
    """Return list of (code, message) failures. Empty list == clean."""
    f = []

    # I1 ROW_CONSERVATION
    if len(before) != len(after):
        f.append(("I1_ROW_CONSERVATION",
                  "%s rows in, %s out" % (len(before), len(after))))

    # I2 MONEY_CONSERVATION
    for c in MONEY_COLS:
        b, a = total(before, c), total(after, c)
        if b != a:
            f.append(("I2_MONEY_CONSERVATION",
                      "%s: %.2f -> %.2f (delta %+.2f)" % (c, b, a, a - b)))

    # I3 CELL_PRESERVATION - every original column, every row, byte-identical
    bidx = {r["filing_uuid"]: r for r in before}
    changed = 0
    example = ""
    for r in after:
        b = bidx.get(r["filing_uuid"])
        if b is None:
            continue
        for c in before_hdr:
            if (b.get(c) or "") != (r.get(c) or ""):
                changed += 1
                if not example:
                    example = "%s.%s: %r -> %r" % (
                        r["filing_uuid"], c, b.get(c), r.get(c))
    if changed:
        f.append(("I3_CELL_PRESERVATION",
                  "%s pre-existing cells changed; e.g. %s" % (changed, example)))

    # I4 KEY_PRESERVATION
    bu = Counter(r["filing_uuid"] for r in before)
    au = Counter(r["filing_uuid"] for r in after)
    if set(bu) != set(au):
        f.append(("I4_KEY_PRESERVATION",
                  "filing_uuid set moved: -%d +%d"
                  % (len(set(bu) - set(au)), len(set(au) - set(bu)))))
    dup = [u for u, n in au.items() if n > 1]
    if dup:
        f.append(("I4_KEY_PRESERVATION",
                  "%s duplicate filing_uuid after write" % len(dup)))

    if not all(c in after_hdr for c in NEW_COLS):
        f.append(("I0_COLUMNS_PRESENT",
                  "not every supersession column is in the header"))
        return f

    byuuid = {r["filing_uuid"]: r for r in after}

    # I5 SUPERSEDER_RESOLVES
    bad = []
    for r in after:
        by = r["superseded_by_filing_uuid"]
        if not by:
            if r["is_superseded"] == "1":
                bad.append("%s is_superseded=1 with no superseder"
                           % r["filing_uuid"])
            continue
        if r["is_superseded"] != "1":
            bad.append("%s has a superseder but is_superseded=0"
                       % r["filing_uuid"])
        t = byuuid.get(by)
        if t is None:
            bad.append("%s -> %s which does not exist" % (r["filing_uuid"], by))
        elif t["supersession_group_id"] != r["supersession_group_id"]:
            bad.append("%s -> %s in a different group" % (r["filing_uuid"], by))
        elif t["is_superseded"] == "1":
            bad.append("%s -> %s which is itself superseded"
                       % (r["filing_uuid"], by))
        elif by == r["filing_uuid"]:
            bad.append("%s supersedes itself" % r["filing_uuid"])
    if bad:
        f.append(("I5_SUPERSEDER_RESOLVES",
                  "%s broken links; e.g. %s" % (len(bad), bad[0])))

    # I6 ONE_SURVIVOR_PER_GROUP
    g = defaultdict(list)
    for r in after:
        g[r["supersession_group_id"]].append(r)
    bad6 = []
    for gid, rs in g.items():
        if any(r["is_superseded"] == "1" for r in rs):
            live = [r for r in rs if r["is_superseded"] == "0"]
            if len(live) != 1:
                bad6.append("%s: %d un-superseded of %d"
                            % (gid, len(live), len(rs)))
    if bad6:
        f.append(("I6_ONE_SURVIVOR_PER_GROUP",
                  "%s groups; e.g. %s" % (len(bad6), bad6[0])))

    # I7 DROP_ACCOUNTS_EXACTLY
    t_all = total(after, "spend_usd")
    t_sup = total(after, "spend_usd", lambda r: r["is_superseded"] == "1")
    t_liv = total(after, "spend_usd", lambda r: r["is_superseded"] == "0")
    if round(t_sup + t_liv, 2) != t_all:
        f.append(("I7_DROP_ACCOUNTS_EXACTLY",
                  "%.2f + %.2f != %.2f" % (t_sup, t_liv, t_all)))
    return f


# ---------------------------------------------------------------------------
def print_measure(hdr, rows, cls):
    n = len(rows)
    print("\n-- DENOMINATOR: %s rows in %s" % (n, TARGET.relative_to(ROOT)))
    print("   distinct filing_uuid            %s"
          % len({r["filing_uuid"] for r in rows}))
    print("   naive SUM(spend_usd)            $%s"
          % format(total(rows, "spend_usd"), ",.2f"))
    amd = [r for r in rows if is_amendment(r)]
    print("   amendment rows                  %s  $%s"
          % (amd and len(amd), format(total(amd, "spend_usd"), ",.2f")))

    naive = defaultdict(list)
    for r in rows:
        naive[tuple(r[c] for c in KEY_COLS)].append(r)
    nm = [k for k, v in naive.items()
          if any(is_amendment(x) for x in v)
          and any(not is_amendment(x) for x in v)]
    print("\n   THE DOC'S KEY %s:" % (tuple(KEY_COLS),))
    print("     groups                        %s" % len(naive))
    print("     amendment + non-amendment     %s   <- docs/methodology/"
          "lobbying.md says 1,135" % len(nm))

    fam = defaultdict(list)
    for r in rows:
        fam[group_key(r)].append(r)
    fm = [k for k, v in fam.items()
          if any(is_amendment(x) for x in v)
          and any(not is_amendment(x) for x in v)]
    print("\n   THIS SCRIPT'S KEY (+ form family):")
    print("     groups                        %s" % len(fam))
    print("     amendment + non-amendment     %s" % len(fm))
    print("     groups with >1 non-amendment  %s   <- REFUSED, never superseded"
          % sum(1 for v in fam.values()
                if sum(1 for x in v if not is_amendment(x)) > 1))

    print("\n-- STATUS")
    for k, v in Counter(s for _, s, _, _ in cls.values()).most_common():
        m = round(sum(money(r["spend_usd"]) for r in rows
                      if cls[r["filing_uuid"]][1] == k), 2)
        print("   %-44s %7s  $%16s" % (k, v, format(m, ",.2f")))

    sup = [r for r in rows if cls[r["filing_uuid"]][2] == "1"]
    t = total(rows, "spend_usd")
    ts = total(sup, "spend_usd")
    print("\n-- THE MEASURED DOUBLE-COUNT")
    print("   rows superseded                 %s" % len(sup))
    print("   spend_usd on superseded rows    $%s" % format(ts, ",.2f"))
    print("   naive total                     $%s" % format(t, ",.2f"))
    print("   total WHERE is_superseded = 0   $%s" % format(t - ts, ",.2f"))
    print("   the double-count                $%s  (%.2f%%)"
          % (format(ts, ",.2f"), 100 * ts / t if t else 0))

    # habit 3: one worked example row, printed whole
    ex = None
    for k, v in fam.items():
        if (len(v) == 3 and any(is_amendment(x) for x in v)
                and sum(1 for x in v if money(x["spend_usd"]) > 0) >= 1
                and any(cls[x["filing_uuid"]][2] == "1" for x in v)):
            ex = (k, v)
            break
    if ex:
        k, v = ex
        print("\n-- ONE WORKED GROUP  %s  (%s)" % (k, group_id(k)))
        for r in sorted(v, key=posted_order):
            g, s, i, by = cls[r["filing_uuid"]]
            print("   %-8s  %-38s $%12s  %s  %s%s"
                  % (r["filing_uuid"][:8], r["filing_type_display"],
                     format(money(r["spend_usd"]), ",.0f"),
                     r["dt_posted"][:10], s,
                     "  -> " + by[:8] if by else ""))
        print("   client=%s  registrant=%s"
              % (v[0]["client_name"][:40], v[0]["registrant_name"][:40]))


# ---------------------------------------------------------------------------
# NOTE ON WHY THIS FUNCTION TAKES NO `path`. `cedar_pipeline.declared_io`
# follows a bound name and reads a write verb off the LINES THAT MENTION IT.
# The first draft wrote through a `path=TARGET` parameter, so no line
# mentioning `TARGET` carried a write verb and `287_build_dependency_manifest`
# filed 1091 under `readers/native_entity_lobbying_disclosures.csv` - a script
# that rewrites the file, invisible to the manifest that exists to stop a
# rebuild reverting an enricher. Same shape as the `845` finding in
# AGENT_FIELD_GUIDE section 3. The write is named on a TARGET line now.
def do_apply(rows, hdr, backup=True):
    cls = classify(rows)
    if backup:
        b = TARGET.with_name(TARGET.name + BAK_TAG)
        # NEVER overwrite an existing backup. `apply` is idempotent and will
        # be re-run; a second run would otherwise replace the true pre-change
        # state with an already-enriched copy and the only evidence of what
        # the file looked like before would be gone.
        if b.exists():
            print("   backup %s already exists - kept, not overwritten"
                  % b.name)
        else:
            shutil.copy2(TARGET, b)
            print("   backup %s" % b.name)
    out_hdr = list(hdr) + [c for c in NEW_COLS if c not in hdr]
    tmp = TARGET.with_name(TARGET.name + ".part")
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_hdr, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            g, s, i, by = cls[r["filing_uuid"]]
            o = dict(r)
            o["supersession_group_id"] = g
            o["supersession_status"] = s
            o["is_superseded"] = i
            o["superseded_by_filing_uuid"] = by
            w.writerow(o)
    tmp.replace(TARGET)        # an interruption must never look like a finish
    return out_hdr


def cmd_measure():
    hdr, rows = read_rows(TARGET)
    if not rows:
        print("UNMEASURED: target is empty or unreadable")
        return 1
    print_measure(hdr, rows, classify(rows))
    return 0


def cmd_apply():
    hdr, rows = read_rows(TARGET)
    if not rows:
        print("UNMEASURED: target is empty or unreadable")
        return 1
    already = [c for c in NEW_COLS if c in hdr]
    print("=== 1091 apply ===\n   BEFORE  %s rows, %s columns"
          % (len(rows), len(hdr)))
    for c in MONEY_COLS:
        print("           sum(%s) = $%s" % (c, format(total(rows, c), ",.2f")))
    if already:
        print("   NOTE: re-running; %d supersession column(s) already "
              "present, they are recomputed" % len(already))
    base_hdr = [c for c in hdr if c not in NEW_COLS]
    before = [{c: r[c] for c in base_hdr} for r in rows]
    do_apply(rows, hdr)
    ahdr, after = read_rows(TARGET)
    print("   AFTER   %s rows, %s columns" % (len(after), len(ahdr)))
    for c in MONEY_COLS:
        print("           sum(%s) = $%s" % (c, format(total(after, c), ",.2f")))
    fails = invariants(base_hdr, before, ahdr, after)
    for code, msg in fails:
        print("   !! %s: %s" % (code, msg))
    if fails:
        print("\nFAILED - the backup beside the file is the pre-write state.")
        return 1
    print("\n   I1..I7 all clean.")
    print_measure(ahdr, after, classify(after))
    return 0


def cmd_verify():
    hdr, rows = read_rows(TARGET)
    if not rows:
        print("UNMEASURED: target is empty or unreadable")
        return 1
    missing = [c for c in NEW_COLS if c not in hdr]
    if missing:
        print("!! I0_COLUMNS_PRESENT: %s absent - run `apply`" % missing)
        return 1
    base_hdr = [c for c in hdr if c not in NEW_COLS]
    fails = invariants(base_hdr, rows, hdr, rows)
    # recompute from scratch and demand the stored flags agree
    cls = classify(rows)
    drift = [r["filing_uuid"] for r in rows
             if (r["supersession_group_id"], r["supersession_status"],
                 r["is_superseded"], r["superseded_by_filing_uuid"])
             != cls[r["filing_uuid"]]]
    if drift:
        fails.append(("I8_FLAGS_REPRODUCE",
                      "%s rows disagree with a fresh classification; e.g. %s"
                      % (len(drift), drift[0])))
    for code, msg in fails:
        print("!! %s: %s" % (code, msg))
    if fails:
        return 1
    t = total(rows, "spend_usd")
    ts = total(rows, "spend_usd", lambda r: r["is_superseded"] == "1")
    print("OK  %s rows - naive $%s - superseded $%s - totalable $%s"
          % (len(rows), format(t, ",.2f"), format(ts, ",.2f"),
             format(t - ts, ",.2f")))
    return 0


# ---------------------------------------------------------------------------
def cmd_selftest():
    """A check does not count until a fixture proves it FIRES.

    Each case injects ONE synthetic violation into an in-memory copy, asserts
    the NAMED invariant is among the failures, then restores and asserts
    clean. AGENT_FIELD_GUIDE 3, habit 1.
    """
    hdr, rows = read_rows(TARGET)
    if not rows:
        print("UNMEASURED: target is empty or unreadable")
        return 1
    base_hdr = [c for c in hdr if c not in NEW_COLS]
    before = [{c: r[c] for c in base_hdr} for r in rows]
    cls = classify(rows)

    def build():
        out = []
        for r in rows:
            g, s, i, by = cls[r["filing_uuid"]]
            o = {c: r[c] for c in base_hdr}
            o.update(supersession_group_id=g, supersession_status=s,
                     is_superseded=i, superseded_by_filing_uuid=by)
            out.append(o)
        return out

    ahdr = base_hdr + NEW_COLS
    clean = build()
    base = invariants(base_hdr, before, ahdr, clean)
    if base:
        print("!! baseline is not clean; cannot prove anything fires")
        for c, m in base:
            print("   ", c, m)
        return 1
    print("baseline clean (0 failures) - now injecting one violation at a "
          "time\n")

    # I6 only speaks about groups that HAVE a superseded row, so the fixture
    # must leave one behind. The first draft picked a superseded row out of a
    # 2-row group; un-superseding it emptied the group of superseded rows and
    # I6's precondition went false - the check printed SILENT on a violation
    # it was written for. Pick from a group with at least TWO superseded rows.
    per_group = defaultdict(list)
    for r in clean:
        per_group[r["supersession_group_id"]].append(r)
    a_sup = next(x for rs in per_group.values()
                 if sum(1 for y in rs if y["is_superseded"] == "1") >= 2
                 for x in rs if x["is_superseded"] == "1")
    a_liv = next(r for r in clean if r["is_superseded"] == "0"
                 and money(r["spend_usd"]) > 0)

    def drop_a_row(rs):
        rs.pop()

    def bend_money(rs):
        next(r for r in rs if money(r["spend_usd"]) > 0)["spend_usd"] = "1"

    def bend_cell(rs):
        rs[0]["client_name"] = rs[0]["client_name"] + " XX"

    def bend_key(rs):
        rs[0]["filing_uuid"] = "not-a-real-uuid"

    def dangling(rs):
        r = next(x for x in rs if x["filing_uuid"] == a_sup["filing_uuid"])
        r["superseded_by_filing_uuid"] = \
            "00000000-0000-0000-0000-000000000000"

    def two_survivors(rs):
        r = next(x for x in rs if x["filing_uuid"] == a_sup["filing_uuid"])
        r["is_superseded"] = "0"
        r["superseded_by_filing_uuid"] = ""

    def flag_without_target(rs):
        r = next(x for x in rs if x["filing_uuid"] == a_liv["filing_uuid"])
        r["is_superseded"] = "1"

    cases = [
        ("I1_ROW_CONSERVATION", drop_a_row),
        ("I2_MONEY_CONSERVATION", bend_money),
        ("I3_CELL_PRESERVATION", bend_cell),
        ("I4_KEY_PRESERVATION", bend_key),
        ("I5_SUPERSEDER_RESOLVES", dangling),
        ("I6_ONE_SURVIVOR_PER_GROUP", two_survivors),
        ("I5_SUPERSEDER_RESOLVES", flag_without_target),
    ]
    bad = 0
    for want, mutate in cases:
        rs = build()
        mutate(rs)
        fails = invariants(base_hdr, before, ahdr, rs)
        codes = {c for c, _ in fails}
        ok = want in codes
        print("   %s  %-28s %-22s -> %s"
              % ("FIRES " if ok else "SILENT", want, mutate.__name__,
                 sorted(codes) or "NOTHING"))
        if not ok:
            bad += 1
        # restore, assert clean again
        if invariants(base_hdr, before, ahdr, build()):
            print("   !! restore did not return to clean")
            bad += 1

    # I7 cannot be broken by a row edit alone (it is an identity over the same
    # column), so it is proved on a two-row hand-built fixture instead.
    fx_before = [dict(before[0]), dict(before[1])]
    fx = [dict(clean[0]), dict(clean[1])]
    fx[0]["is_superseded"] = "9"      # neither 0 nor 1 -> both sides miss it
    fx[0]["spend_usd"] = "1000"
    fx_before[0]["spend_usd"] = "1000"
    f7 = invariants(base_hdr, fx_before, ahdr, fx)
    codes7 = {c for c, _ in f7}
    ok7 = "I7_DROP_ACCOUNTS_EXACTLY" in codes7
    print("   %s  %-28s %-22s -> %s"
          % ("FIRES " if ok7 else "SILENT", "I7_DROP_ACCOUNTS_EXACTLY",
             "is_superseded='9'", sorted(codes7)))
    if not ok7:
        bad += 1

    print("\n%d cases, %d did not fire." % (len(cases) + 1, bad))
    return 1 if bad else 0


# ---------------------------------------------------------------------------
# THE SHIPPED SURFACE. A flag a buyer never reads is not a fix.
#
# `dist/04_lobbying/native_entity_lobbying_disclosures.NOTES.md` promises
# "No silent exclusions - rows we exclude from a total are flagged as columns
# rather than deleted", describes `spend_usd` as "Reported lobbying spend for
# the filing period", and says nothing at all about amendments or about the
# other two tribal-lobbying totals. `tribe_year_lobbying_panel.NOTES.md`
# describes `total_lobbying_spend_usd` as, in full, "Amount."
#
# So the shipped sample COULD be summed to a wrong number innocently. The two
# levers that put the warning in front of a buyer both feed
# `code/87_build_dataset_notes.py`:
#
#   data/clean/series_breaks.csv   -> the "## Comparability" block in NOTES.md
#                                     (added by code/86, three rows, 24 -> 27)
#   data/clean/codebook_master.csv -> the per-variable Description column
#                                     (this command)
#
# Both are DATA, not another agent's script, and 87 regenerates the shipped
# notes from them.
CODEBOOK_MASTER = CLEAN / "codebook_master.csv"
CODEBOOK_FRAG = CLEAN / "codebook" / "04_lobbying.csv"
CB_GROUP = "04_lobbying"

SPEND_USD_DESC = (
    "Reported lobbying spend for the filing period: income_usd for an "
    "outside registrant, expenses_usd for a self-filer, and only one of the "
    "two is ever populated. DO NOT SUM THIS COLUMN BLIND. An amended LD-2 "
    "restates the period it amends and the LDA publishes it as a NEW filing "
    "rather than replacing the original, so a naive SUM double-counts "
    "$37,349,254 - 5.15% of the $725,743,974.52 naive total. The additive "
    "figure is SUM(spend_usd) WHERE is_superseded = 0 = $688,394,720.51. "
    "40.7% of filings (11,314) report no dollar at all, so a 0 here usually "
    "means 'reported nothing', not 'spent nothing'. Every LDA figure is a "
    "good-faith estimate rounded to $10,000 at source. NEVER add this to "
    "tribe_year_lobbying_panel.total_lobbying_spend_usd ($680,561,640.52) or "
    "to lobbying_registrants.spend_reported_usd ($645,052,868.51) - the same "
    "money at three grains. [measured 2026-09-02]")

PANEL_TOTAL_DESC = (
    "Lobbying spend rolled up to one (entity, filing year). A ROLL-UP of "
    "native_entity_lobbying_disclosures.csv, not a second observation: "
    "$680,561,640.52 over 5,001 rows, $45,182,334.00 below the filing-level "
    "$725,743,974.52 because the panel drops withdrawn and organisation-type-"
    "barred attributions. NEVER add it to the filing table or to "
    "lobbying_registrants.spend_reported_usd ($645,052,868.51). It is also "
    "NOT amendment-adjusted - the $37,349,254 of superseded amendment money "
    "is inside this number too. [measured 2026-09-02]")

NEW_COL_DESC = {
    "supersession_group_id":
        "The set of filings that describe ONE reporting obligation: a "
        "blake2b digest over (client_id, registrant_id, filing_year, "
        "filing_period, form family), where form family separates a "
        "REGISTRATION from the REPORT that follows it. Without that fifth "
        "part a $0 registration amendment sits in the same bucket as the "
        "quarterly report and would appear to supersede it.",
    "supersession_status":
        "Why this row is or is not superseded. AMENDMENT_SURVIVOR (the "
        "latest amendment - total this one), SUPERSEDED_BY_AMENDMENT, "
        "SUPERSEDED_BY_LATER_AMENDMENT, NOT_SUPERSEDED, "
        "REGISTRATION_NO_MONEY, UNFLAGGED_DUPLICATE_CANDIDATE (a repeated "
        "filing_type_display the LDA never flagged as an amendment - NOT "
        "superseded, because the source never said one replaces the other), "
        "AMBIGUOUS_MULTIPLE_ORIGINALS and "
        "AMBIGUOUS_ORIGINAL_POSTED_AFTER_AMENDMENT (129 rows where which "
        "filing restates which is not knowable from the LDA fields Cedar "
        "holds - flagged and left IN the total, never guessed).",
    "is_superseded":
        "1 when a later filing in the same supersession_group_id restates "
        "this one. 1,064 of 27,825 rows, carrying $37,349,254.01. The "
        "additive filing-grain total is SUM(spend_usd) WHERE is_superseded "
        "= 0. No superseded row is deleted.",
    "superseded_by_filing_uuid":
        "The filing_uuid of the filing that restates this one, blank where "
        "nothing does. Always resolves to a row in the same "
        "supersession_group_id that is not itself superseded.",
}


def _cb_read(p):
    if not p.exists():
        return None, None
    with open(p, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        return r.fieldnames, list(r)


def cmd_codebook():
    hdr, rows = read_rows(TARGET)
    if not rows:
        print("UNMEASURED: target is empty or unreadable")
        return 1
    n = len(rows)
    fill = {c: round(100.0 * sum(1 for r in rows if (r.get(c) or "").strip())
                     / n, 1) for c in NEW_COLS}
    print("=== 1091 codebook ===")
    print("   measured fill on %s rows: %s" % (n, fill))

    spec = {
        "supersession_group_id": ("text", "code"),
        "supersession_status": ("text", "category"),
        "is_superseded": ("integer", "flag"),
        "superseded_by_filing_uuid": ("text", "code"),
    }
    # CALLED ONCE PER FILE, BY NAME, ON PURPOSE. A `for path in (A, B)` loop
    # is tidier and it made `287_build_dependency_manifest` file 1091 under
    # `readers/` for two files it rewrites: `cedar_pipeline.declared_io`
    # follows a bound name and looks for a write verb on the lines that
    # mention it, and a loop variable hides the write. `write_codebook_block`
    # is a real function that really writes and its name carries the verb.
    rc = 0
    rc |= write_codebook_block(CODEBOOK_MASTER, fill, n, spec)
    rc |= write_codebook_block(CODEBOOK_FRAG, fill, n, spec)
    print("\n   These land in dist/04_lobbying/*.NOTES.md the next time "
          "code/87_build_dataset_notes.py runs.")
    return rc


def write_codebook_block(path, fill, n, spec):
    """Rewrite ONE codebook file in place: add the four supersession
    variables, replace the two money-column descriptions. Row-conserving
    apart from the rows it says it added."""
    f, cb = _cb_read(path)
    if cb is None:
        print("   !! %s absent - UNMEASURED, not clean" % path)
        return 1
    rc = 0
    before = len(cb)
    bak = path.with_name(path.name + BAK_TAG)
    if not bak.exists():
        shutil.copy2(path, bak)
    have = {(r["dataset"], r["variable"]) for r in cb}
    touched = 0
    for r in cb:
        if r["dataset"] != CB_GROUP:
            continue
        if r["variable"] == "spend_usd" and r["description"] != SPEND_USD_DESC:
            r["description"] = SPEND_USD_DESC
            touched += 1
        if (r["variable"] == "total_lobbying_spend_usd"
                and r["description"] != PANEL_TOTAL_DESC):
            r["description"] = PANEL_TOTAL_DESC
            touched += 1
    added = 0
    for c in NEW_COLS:
        if (CB_GROUP, c) in have:
            for r in cb:
                if r["dataset"] == CB_GROUP and r["variable"] == c:
                    r["description"] = NEW_COL_DESC[c]
                    r["pct_filled"] = fill[c]
                    r["n_rows"] = n
            continue
        t, u = spec[c]
        row = {k: "" for k in f}
        row.update({"dataset": CB_GROUP, "variable": c, "type": t,
                    "units": u, "pct_filled": fill[c], "n_rows": n,
                    "published": "1", "access_tier": "public",
                    "description": NEW_COL_DESC[c], "generated": TODAY})
        cb.append(row)
        added += 1
    tmp = path.with_name(path.name + ".part")
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=f, extrasaction="ignore")
        w.writeheader()
        w.writerows(cb)
    tmp.replace(path)
    after = len(cb)
    print("   %-34s %d -> %d rows  (+%d new, %d descriptions rewritten)"
          % (path.name, before, after, added, touched))
    if after - before != added:
        print("   !! ROW CONSERVATION: %d - %d != %d"
              % (after, before, added))
        rc = 1
    return rc


CMDS = {"measure": cmd_measure, "apply": cmd_apply, "verify": cmd_verify,
        "selftest": cmd_selftest, "codebook": cmd_codebook}

if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if c not in CMDS:
        print("usage: %s" % " | ".join(CMDS))
        raise SystemExit(2)
    raise SystemExit(CMDS[c]())
