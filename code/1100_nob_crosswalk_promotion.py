#!/usr/bin/env python3
"""
Cedar Press - 1100: PROMOTE THE FEDERAL CROSSWALK ONTO THE BUSINESS DIRECTORY,
                    AND APPLY TO THE MERGED HALF OF THE 1070 SWEEP THE REFUSAL
                    THAT WAS APPLIED TO THE OTHER HALF.

    py -3 code/1100_nob_crosswalk_promotion.py            # enrich in place
    py -3 code/1100_nob_crosswalk_promotion.py verify     # exit 1 on breach
    py -3 code/1100_nob_crosswalk_promotion.py selftest   # prove verify FIRES

PART ONE - THE CROSSWALK IS A SIDECAR AND THE TABLE CANNOT SEE IT
------------------------------------------------------------------
`native_business_contract_links.csv` (built by `code/1001`) carries the resolved
federal identity of a directory row - `link_status`, `link_tier`, `link_method`,
`link_rung`, `matched_uei`, `matched_cage`, the corroborator that carried it and
the publish gate. `native_owned_businesses.csv` carries none of it: its
`business_entity_id` reaches **4 of 2,916 rows**, and a buyer holding the
directory alone cannot tell which firms Cedar found in federal contracting.

Measured before this pass:

    link_status  LINKED 203 · PROPOSED 59 · HOLD_AMBIGUOUS 8 · REFUSED 8
                 NO_MATCH 2,115  -> 2,393 rows, 168 distinct UEIs
    all 203 LINKED rows are `identifier_publish_gate = PUBLISH`

**`business_entity_id` is NOT where a UEI goes.** `docs/IDENTIFIER_STANDARD.md`
§2: a UEI identifies a REGISTRATION, and a registration is a sub-hub, not an
entity. Writing a UEI into an `entity_id` column would make 203 registrations
look like 203 Cedar entities. So the promotion adds a declared
`federal_link_*` family and leaves `business_entity_id` for what it means.

**The certification gradient is untouched.** `identity_scope`,
`assertion_class`, `certification_tier`, `certification_number` and
`inclusion_basis` are not read and not written. The published relation stays
**affiliation**: `federal_link_relation` says in as many words that the link
identifies the FIRM in federal data and asserts nothing about who owns it.

**No dollar is written onto a directory row.** The crosswalk holds
`prime_obligations_usd` per row; putting it here invites a roll-up across an
affiliation gradient, which `docs/PUBLICATION_POLICY.md` refuses.
`federal_link_detail_file` names the sidecar instead.

The two writers AGREE and are not being reconciled by force: on the 196 rows
where both `federal_uei_candidate` (written by `code/953`) and `matched_uei`
are populated, **196 of 196 are the same string.** That is checked, not assumed
- `verify` I3 fails if it ever stops being true.

PART TWO - THE REFUSAL THAT WAS APPLIED TO ONE HALF OF A SPLIT
---------------------------------------------------------------
`code/1070_anc_nho_business_sweep.py` staged 1,106 rows. The integrator split
them by `assertion_class`: the 583 OWNERSHIP rows went to NEST, the 523
RELATIONSHIP rows were merged into this table.

NEST then **refused 229 of its 583 on one ground**: *"unreviewed HTML
heading/anchor scrape"*, because the block yields `Blank`, `No Results Found`,
`Employee Resources` **and seven natural persons' names scraped off a
leadership page**, and `docs/NEST_BUILD_LOG.md` records that as a hard rule -
*"a natural person's name may never enter this dataset"*.

The same refusal was never applied to the 523 that came here. Measured on the
live table:

    rows carrying `verification_basis` ... "HTML heading/anchor scrape -
      not a table; review before resolving"                            523
    of those, `business_name_is_person_name`                    -1  on 523
      (-1 means UNDECIDABLE, and 1070 hard-codes it: the detector in
       `code/330` was never run on these rows at all)
    of those, `publishable`                                      Y  on 523

And the rows are what that caveat predicts. Three of the first three inspected:

    "Tribal Enterprise Directory"   <- the page's own heading
    "Rebecca Naragon"               <- a natural person
    "Akwesasne Farmers Market"      <- a real enterprise

So a natural person's name is published as a business name, with the guard
column reading *undecidable* because nothing ever asked it.

WHAT THIS PASS DOES ABOUT IT, AND WHAT IT REFUSES TO DO
--------------------------------------------------------
1. **It runs the detector.** `looks_like_person()` from
   `code/330_build_native_owned_businesses.py` is imported and applied to
   exactly the rows whose flag is `-1` **because 1070 hard-coded it**, never to
   a row where `330` itself decided. A flag another writer computed is not
   re-litigated here.
2. **It puts a publish hold on the unreviewed scrape**, whatever the detector
   says, because the caveat is about the whole block and not about one row:
   `publish_hold = Y`, `publish_hold_basis` naming NEST's identical refusal, and
   `publishable` set to `N`.
3. **It deletes nothing and loses nothing.** The prior value of `publishable`
   is preserved verbatim in `publishable_before_1100`, so the hold is
   reversible by one column copy and the original state is still on the record.
   `docs/AGENTS.md`: flag, never delete.

Holding is the conservative direction and it is the one the house rules require
- a business name is not PII, but a natural person's name is not a business
name, and the row itself says nobody has checked which this is.

THE NAMED INVARIANTS
--------------------
  I1  every row carries a `federal_link_status` from the declared vocabulary.
      `NOT_ATTEMPTED` is a legitimate value and is what the 523 get, because
      `1001` ran before they existed - an honest state, not a gap.
  I2  a `federal_uei_linked` is written ONLY where `federal_link_status` is
      LINKED **and** the crosswalk's own `identifier_publish_gate` is PUBLISH.
      A gate is a policy and re-deriving it here would be a second copy of it.
  I3  where both `federal_uei_candidate` and `federal_uei_linked` are present
      they are the SAME string. Two writers disagreeing about one firm's
      identifier is a defect, not a preference.
  I4  no row is `publishable = Y` while carrying the unreviewed-scrape caveat.
  I5  CONSERVE. rows unchanged, no column lost, and the md5 of every base field
      EXCEPT `publishable` is unchanged - `publishable` is the one field this
      pass may move, and its prior value is retained in a new column.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

TABLE = ROOT / "data" / "clean" / "native_owned_businesses.csv"
LINKS = ROOT / "data" / "clean" / "native_business_contract_links.csv"
MANIFEST = ROOT / "docs" / "NOB_CROSSWALK_PROMOTION.json"
BAK_TAG = f".bak_{TODAY}_pre_1100_nob_crosswalk_promotion"

SCRAPE_CAVEAT = "HTML heading/anchor scrape"

NEW = ["federal_link_status", "federal_link_tier", "federal_link_method",
       "federal_link_rung", "federal_uei_linked", "federal_cage_linked",
       "federal_link_corroboration", "federal_link_publish_gate",
       "federal_link_no_match_reason", "federal_link_relation",
       "federal_link_detail_file", "federal_link_basis",
       "publishable_before_1100", "publish_hold", "publish_hold_basis",
       "person_name_check_1100"]

STATUS_VOCAB = {"LINKED", "PROPOSED", "HOLD_AMBIGUOUS", "REFUSED",
                "NO_MATCH", "NOT_ATTEMPTED"}

RELATION = ("identifies this FIRM in federal contracting data. It is NOT an "
            "ownership claim and does not change identity_scope: the "
            "directory's published relation remains affiliation.")


def load_person_detector():
    """Import `looks_like_person` from 330 without executing its build."""
    p = ROOT / "code" / "330_build_native_owned_businesses.py"
    spec = importlib.util.spec_from_file_location("nob330", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["nob330"] = mod
    spec.loader.exec_module(mod)
    return mod.looks_like_person


def read_table(p: Path):
    if not p.exists():
        return [], []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        r = csv.DictReader(fh)
        return [dict(x) for x in r], list(r.fieldnames or [])


def write_table(p: Path, rows, fields, tag=None):
    if p.exists() and tag:
        b = p.with_name(p.name + tag)
        if not b.exists():
            shutil.copy2(p, b)
    tmp = p.with_suffix(p.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(p)


def digest(rows, fields):
    h = hashlib.md5()
    for r in rows:
        for c in fields:
            h.update((r.get(c) or "").encode("utf-8"))
            h.update(b"\x1f")
        h.update(b"\x1e")
    return h.hexdigest()


def build(dry_run=False) -> int:
    rows, fields = read_table(TABLE)
    links, _ = read_table(LINKS)
    lmap = {(r.get("business_source_id") or ""): r for r in links}

    base = [c for c in fields if c not in NEW]
    frozen = [c for c in base if c != "publishable"]
    before_frozen = digest(rows, frozen)
    n_before = len(rows)

    looks_like_person = load_person_detector()

    st = {"rows": n_before, "status": {}, "uei_written": 0,
          "cage_written": 0, "not_attempted": 0, "scrape_caveat": 0,
          "publishable_flipped": 0, "person_detector_run": 0,
          "person_detector_says_person": 0,
          "person_detector_says_not_person": 0,
          "person_detector_undecidable": 0,
          "candidate_vs_linked_compared": 0,
          "candidate_vs_linked_disagree": 0}

    out_fields = list(fields) + [c for c in NEW if c not in fields]
    for r in rows:
        for c in NEW:
            r.setdefault(c, "")
        bsid = r.get("business_source_id") or ""
        lk = lmap.get(bsid)

        if lk is None:
            r["federal_link_status"] = "NOT_ATTEMPTED"
            r["federal_link_basis"] = (
                "no row in native_business_contract_links.csv: "
                "code/1001 ran before this row was merged into the directory "
                "by the code/1070 sweep. NOT_ATTEMPTED is the honest state "
                "(ADR-010); it is not a no-match.")
            st["not_attempted"] += 1
        else:
            status = (lk.get("link_status") or "").strip()
            r["federal_link_status"] = status
            r["federal_link_tier"] = lk.get("link_tier") or ""
            r["federal_link_method"] = lk.get("link_method") or ""
            r["federal_link_rung"] = lk.get("link_rung") or ""
            r["federal_link_corroboration"] = lk.get("corroboration") or ""
            r["federal_link_publish_gate"] = \
                lk.get("identifier_publish_gate") or ""
            r["federal_link_no_match_reason"] = lk.get("no_match_reason") or ""
            gate = (lk.get("identifier_publish_gate") or "").strip()
            if status == "LINKED" and gate == "PUBLISH":
                r["federal_uei_linked"] = lk.get("matched_uei") or ""
                r["federal_cage_linked"] = lk.get("matched_cage") or ""
                if r["federal_uei_linked"]:
                    st["uei_written"] += 1
                if r["federal_cage_linked"]:
                    st["cage_written"] += 1
            r["federal_link_basis"] = (
                "promoted verbatim from native_business_contract_links.csv "
                f"(built by {lk.get('built_by') or 'code/1001'}, "
                f"{lk.get('built_date') or ''}). tier and method are "
                "INHERITED from that row and are not re-graded here.")
            cand = (r.get("federal_uei_candidate") or "").strip()
            lin = (r.get("federal_uei_linked") or "").strip()
            if cand and lin:
                st["candidate_vs_linked_compared"] += 1
                if cand != lin:
                    st["candidate_vs_linked_disagree"] += 1
        r["federal_link_relation"] = RELATION
        r["federal_link_detail_file"] = \
            "data/clean/native_business_contract_links.csv"
        st["status"][r["federal_link_status"]] = \
            st["status"].get(r["federal_link_status"], 0) + 1

        # -- part two: the unreviewed heading/anchor scrape -----------------
        # WRITE ONCE. A second run would otherwise capture the value THIS
        # script already changed and the original `Y` would be lost - the
        # preserved-value column has to be the one thing that is not
        # recomputed.
        if not (r.get("publishable_before_1100") or "").strip():
            r["publishable_before_1100"] = r.get("publishable") or ""
        if SCRAPE_CAVEAT in (r.get("verification_basis") or ""):
            st["scrape_caveat"] += 1
            if (r.get("business_name_is_person_name") or "").strip() == "-1":
                v = looks_like_person(r.get("business_name_raw") or "", None)
                r["person_name_check_1100"] = str(v)
                st["person_detector_run"] += 1
                st["person_detector_says_person"] += 1 if v == 1 else 0
                st["person_detector_says_not_person"] += 1 if v == 0 else 0
                st["person_detector_undecidable"] += 1 if v == -1 else 0
            r["publish_hold"] = "Y"
            r["publish_hold_basis"] = (
                "the row's own verification_basis says 'HTML heading/anchor "
                "scrape - not a table; review before resolving'. "
                "docs/NEST_BUILD_LOG.md refused 229 rows of the SAME code/1070 "
                "harvest on exactly this ground, because the block yields page "
                "furniture and natural persons' names; the refusal was applied "
                "to the OWNERSHIP half of the split and not to this one. "
                "business_name_is_person_name was hard-coded -1 by 1070, so "
                "nothing had checked. HELD, not deleted: "
                "publishable_before_1100 retains the prior value and "
                "person_name_check_1100 records what the detector says.")
            if (r.get("publishable") or "") == "Y":
                r["publishable"] = "N"
                st["publishable_flipped"] += 1

    if digest(rows, frozen) != before_frozen:
        print("  [1100] FATAL: a frozen base field changed. Refusing to write.")
        return 1
    if len(rows) != n_before:
        print("  [1100] FATAL: row count moved. Refusing to write.")
        return 1

    if not dry_run:
        write_table(TABLE, rows, out_fields, tag=BAK_TAG)

    gained = [c for c in out_fields if c not in fields]
    print(f"  [1100] rows {len(rows):,} unchanged | md5(base {len(frozen)} "
          f"frozen fields) {before_frozen}")
    print(f"  [1100] COLUMN DIFF   gained {len(gained)}: {gained}")
    print(f"  [1100]               lost   0: []")
    print("  [1100] federal_link_status")
    for k, v in sorted(st["status"].items(), key=lambda kv: -kv[1]):
        print(f"          {k:<20} {v:>6,}")
    print(f"  [1100] UEI written {st['uei_written']:,} · CAGE written "
          f"{st['cage_written']:,} (LINKED + gate=PUBLISH only)")
    print(f"  [1100] candidate vs linked compared "
          f"{st['candidate_vs_linked_compared']:,}, disagree "
          f"{st['candidate_vs_linked_disagree']:,}")
    print(f"  [1100] unreviewed heading/anchor scrape rows "
          f"{st['scrape_caveat']:,}")
    print(f"          person detector run on            "
          f"{st['person_detector_run']:>6,}")
    print(f"            IS a natural person's name      "
          f"{st['person_detector_says_person']:>6,}")
    print(f"            is not                          "
          f"{st['person_detector_says_not_person']:>6,}")
    print(f"            undecidable                     "
          f"{st['person_detector_undecidable']:>6,}")
    print(f"          publishable Y -> N                "
          f"{st['publishable_flipped']:>6,}")

    if not dry_run:
        MANIFEST.write_text(json.dumps(
            {"built": TODAY, "script": "1100_nob_crosswalk_promotion.py",
             "table": "data/clean/native_owned_businesses.csv",
             "columns_added": NEW,
             "frozen_base_fields_md5": before_frozen, **st}, indent=2),
            encoding="utf-8")
        print(f"  [1100] wrote {MANIFEST.relative_to(ROOT)}")
    return 0


def verify(path: Path | None = None) -> int:
    p = path or TABLE
    rows, fields = read_table(p)
    if any(c not in fields for c in NEW):
        print("  [1100] verify: columns absent - run the enricher first")
        return 1
    fails = []
    for r in rows:
        bid = r.get("business_source_id")
        s = (r.get("federal_link_status") or "").strip()
        if s not in STATUS_VOCAB:
            fails.append(("I1", bid, f"federal_link_status {s!r} off-vocab"))
        uei = (r.get("federal_uei_linked") or "").strip()
        if uei:
            if s != "LINKED":
                fails.append(("I2", bid, "UEI written on a row that is not "
                                         f"LINKED (status {s})"))
            if (r.get("federal_link_publish_gate") or "").strip() != "PUBLISH":
                fails.append(("I2", bid, "UEI written past a publish gate "
                                         "that is not PUBLISH"))
        cand = (r.get("federal_uei_candidate") or "").strip()
        if cand and uei and cand != uei:
            fails.append(("I3", bid, f"federal_uei_candidate {cand} != "
                                     f"federal_uei_linked {uei}"))
        if SCRAPE_CAVEAT in (r.get("verification_basis") or ""):
            if (r.get("publishable") or "") == "Y":
                fails.append(("I4", bid, "publishable=Y on an unreviewed "
                                         "heading/anchor scrape"))
            if (r.get("publish_hold") or "") != "Y":
                fails.append(("I4", bid, "no publish_hold on an unreviewed "
                                         "heading/anchor scrape"))
    print(f"  [1100] verify: {len(rows):,} rows | {len(fails)} breach(es)")
    for f in fails[:20]:
        print(f"          {f[0]}  {f[1]}  {f[2]}")
    if len(fails) > 20:
        print(f"          ... and {len(fails)-20} more")
    return 1 if fails else 0


def selftest() -> int:
    import tempfile
    rows, fields = read_table(TABLE)
    if any(c not in fields for c in NEW):
        print("  [1100] selftest: run the enricher first")
        return 1
    tmp = Path(tempfile.mkdtemp()) / "native_owned_businesses.csv"
    cases = []

    def run(label, mut):
        rs = [dict(r) for r in rows]
        mut(rs)
        write_table(tmp, rs, fields)
        rc = verify(tmp)
        cases.append((label, rc == 1))
        print(f"          {'FIRES ' if rc == 1 else 'SILENT'}  {label}")

    def linked(rs):
        for r in rs:
            if (r.get("federal_uei_linked") or "").strip():
                return r
        raise SystemExit("no linked row")

    def held(rs):
        for r in rs:
            if (r.get("publish_hold") or "") == "Y":
                return r
        raise SystemExit("no held row")

    print("  [1100] selftest - inject the violation, assert exit 1")
    run("I1 off-vocabulary federal_link_status",
        lambda rs: rs[0].__setitem__("federal_link_status", "MAYBE"))
    run("I2 UEI on a row that is not LINKED",
        lambda rs: linked(rs).__setitem__("federal_link_status", "PROPOSED"))
    run("I2 UEI past a gate that is not PUBLISH",
        lambda rs: linked(rs).__setitem__("federal_link_publish_gate",
                                          "WITHHOLD_PENDING_RULING"))
    run("I3 candidate UEI disagrees with linked UEI",
        lambda rs: linked(rs).__setitem__("federal_uei_candidate",
                                          "ZZZZZZZZZZZZ"))
    run("I4 publishable=Y restored on an unreviewed scrape",
        lambda rs: held(rs).__setitem__("publishable", "Y"))
    run("I4 publish_hold removed from an unreviewed scrape",
        lambda rs: held(rs).__setitem__("publish_hold", ""))

    write_table(tmp, rows, fields)
    rc = verify(tmp)
    print(f"          {'PASS  ' if rc == 0 else 'FAIL  '}  restored copy "
          f"verifies clean (exit {rc})")
    ok = all(c[1] for c in cases) and rc == 0
    print(f"  [1100] selftest {sum(c[1] for c in cases)}/{len(cases)} "
          f"invariants proved to fire; clean copy exit {rc}")
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "verify":
        sys.exit(verify())
    if cmd == "selftest":
        sys.exit(selftest())
    if cmd == "dry":
        sys.exit(build(dry_run=True))
    sys.exit(build())
