#!/usr/bin/env python3
"""
Cedar Press - 952: GIVE EVERY np_orgs ROW A NAMED DISPOSITION, AND FLAG THE
                   NAME MATCHES THAT REST ON A GENERIC ENGLISH WORD.

    py -3 code/952_nonprofit_disposition.py            # enrich in place
    py -3 code/952_nonprofit_disposition.py verify     # exit 1 on breach
    py -3 code/952_nonprofit_disposition.py selftest   # prove verify FIRES

WHY - PART ONE: A COLUMN THAT SAYS UNRULED FOR EVERYTHING
----------------------------------------------------------
`classification_ruling` reads `UNRULED` on 12,366 of 12,764 rows (96.9%),
including **all 4,651 rows that are excluded** and **all 697 that are verified**.
The real disposition lives in `funnel_stage`, `evidence`, `excluded_by_prior_ruling`
and `placename_risk_flag`, none of which the customer sample shows. A buyer
opening the sample sees `PEORIA AREA TELUGU ASSOCIATION ... UNRULED` beside a
product descriptor claiming non-Native place-name organisations *"are actively
identified and excluded"*. They were. The column just does not say so.

`classification_ruling` is NOT overwritten. It means one specific thing - a
HAND ruling by a named authority, present on 398 rows - and repurposing it
would destroy that distinction, which is the exact error AGENTS.md records as
*"a ruled method is not a positive ruling"*. Instead a new column `disposition`
carries the row's actual state, derived deterministically, with
`disposition_basis` naming the columns and the rule that produced it.

WHY - PART TWO: `ORDER OF THE EASTERN STAR` IS NOT A TRIBE
-----------------------------------------------------------
`docs/WHAT_IS_MISSING.md` names one live false positive: *Order of the Eastern
Star of North Dakota* matched *Chickahominy Indians-Eastern Division* on the
token **EASTERN** and sits unruled at `canonical_name_match`. It asked whether
there are others of that shape.

**There are 258, across 169 distinct organisation names, and every one
inspected is a false positive.** The three largest families:

    55  VETERANS OF FOREIGN WARS OF THE UNITED STATES ...  -> United Auburn
                                                     on the token UNITED
    38  ORDER OF THE EASTERN STAR OF (NORTH|SOUTH) DAKOTA -> Chickahominy
                                                     on the token EASTERN
    ~40 ...DEL PUEBLO / PUEBLO DE DIOS / TEATRO DEL PUEBLO -> Ysleta del Sur,
                                                     Pueblo of Acoma, La Jolla
                                                     on PUEBLO or DEL - Spanish
                                                     for "the town / of the",
                                                     not a Pueblo

Worse cases exist: `PROTESTANT EPISCOPAL CHURCH IN N DAKOTA` -> *Kickapoo Tribe
in Kansas* on the token **IN**, and `NEW LIFE CHRISTIAN FELLOWSHIP OF ONEIDA`
-> *Pueblo of Acoma* on the token **OF**. A stopword keyed a tribe.

THE DETECTOR, AND WHAT IT DOES *NOT* CLAIM
-------------------------------------------
For every row carrying `canonical_name_token_match`, the shared tokens between
the organisation's name and the matched tribe's canonical name are computed and
**recorded on the row** in `name_match_shared_tokens`. `name_match_support`
then takes one of four values:

    distinctive_token                   at least one shared token is not generic
    generic_token_only                  every shared token is a generic English
                                        or civic word - the match is unsupported
                                        by the canonical name it cites
    no_shared_token_with_canonical_name the match shares NO token with the
                                        canonical name shown, so the displayed
                                        evidence does not explain it at all
    not_a_name_match                    no canonical_name_token_match on the row

**This is a statement about the EVIDENCE, never about Native status.** Cedar's
standing rule is that Native status comes from what an organisation says about
itself in its own filing - never from an NTEE code and never from a name. A
generic-token flag therefore does not exclude anything and does not rule
anything: it says the cited name match does not support the link. Rows already
verified from a filing (`verified_strict`, `ruled_native_verified`) keep their
disposition and simply carry the flag as extra evidence. Nothing is deleted.

MEASURED, on 12,764 rows:
    generic_token_only                    578  (258 of them live at
                                               canonical_name_match)
    no_shared_token_with_canonical_name 2,268  (541 live)

A CONFLICT THIS SURFACED
------------------------
Two rows are BOTH `excluded_by_prior_ruling = 1` AND at a funnel stage that
ruled them Native. They get `CONFLICT_EXCLUDED_AND_RULED_NATIVE`, which is a
named state, not a guess at which side is right. Unknown stays unknown.

THE NAMED INVARIANTS
--------------------
  INV-DISPOSITION  every row has a disposition and it is in the declared
                   vocabulary. `other` / `unknown` / `misc` are refused.
  INV-PRECISION    every row labelled `generic_token_only` records at least one
                   shared token and EVERY recorded token is in GENERIC. The
                   label and the evidence on the row must agree.
  INV-CONSERVE     row count unchanged, and the md5 of the 53 base fields is
                   unchanged - so no Native-status column was touched.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
TABLE = ROOT / "data" / "clean" / "np_orgs.csv"
MANIFEST = ROOT / "docs" / "NONPROFIT_DISPOSITION.json"
FALSEPOS = ROOT / "review" / f"np_generic_token_name_matches_{TODAY}.csv"
BAK_TAG = f".bak_{TODAY}_pre_952_nonprofit_disposition"

NEW = ["disposition", "disposition_basis", "name_match_support",
       "name_match_shared_tokens"]

#: Words that carry no identifying force for a tribe. A shared token drawn
#: only from here is a coincidence of English, Spanish or civic vocabulary.
#: Curated by hand from the 169 distinct organisation names the detector
#: surfaced; every addition was justified by a measured false positive.
GENERIC = set("""
EASTERN WESTERN NORTHERN SOUTHERN CENTRAL EAST WEST NORTH SOUTH UPPER LOWER
GRAND LITTLE BIG NEW OLD FIRST SECOND THIRD DIVISION BAND BANDS TRIBE TRIBES
TRIBAL INDIAN INDIANS NATION NATIONS COMMUNITY COMMUNITIES VILLAGE VILLAGES
PUEBLO RANCHERIA COLONY RESERVATION COUNCIL GROUP ASSOCIATION ASSOC THE OF AND
INC INCORPORATED CORP CORPORATION COMPANY LLC FOUNDATION CENTER CENTRE VALLEY
LAKE LAKES RIVER MOUNTAIN MOUNTAINS CREEK SPRING SPRINGS HILL HILLS ISLAND
ISLANDS POINT BAY CITY TOWN COUNTY STATE STAR ORDER PEOPLE PEOPLES NATIVE
AMERICAN AMERICANS AMERICA UNITED FORT PORT SAINT ST LA LE LOS LAS SAN DE DEL
Y A AN AT IN ON FOR CONFEDERATED FEDERATED UNION ALLIANCE SOCIETY CHAPTER
LODGE CLUB HOME HOUSE INDIA
""".split())

#: funnel_stage -> disposition. Exhaustive by construction: an unseen stage
#: RAISES rather than falling into a catch-all.
STAGE = {
    "ruled_not_native":          "EXCLUDED_PLACE_NAME_COINCIDENCE",
    "ruled_native_verified":     "NATIVE_RULED_VERIFIED",
    "ruled_native_needs_elijah": "NATIVE_PROPOSED_AWAITING_OWNER_RULING",
    "verified_strict":           "NATIVE_VERIFIED_STRICT",
    "state_validated":           "CANDIDATE_STATE_VALIDATED",
    "canonical_name_match":      "CANDIDATE_NAME_MATCH_UNVERIFIED",
    "raw_name_candidate":        "CANDIDATE_NAME_ONLY",
}
#: `excluded_by_prior_ruling` is BOTH a funnel_stage and a 0/1 column, and the
#: two do not agree on 32 rows. The stage is listed here so an unmapped stage
#: still RAISES; the disposition for it comes from the branch below.
KNOWN_STAGES = set(STAGE) | {"excluded_by_prior_ruling"}
RULED_NATIVE = {"ruled_native_verified", "ruled_native_needs_elijah"}
VOCAB = set(STAGE.values()) | {
    "EXCLUDED_PRIOR_RULING",
    "CANDIDATE_NAME_MATCH_GENERIC_TOKEN_ONLY",
    "CONFLICT_EXCLUDED_AND_RULED_NATIVE",
}
US = "\x1f"
TOK = re.compile(r"[^A-Z0-9]+")


def tokens(s: str) -> set:
    return {t for t in TOK.split((s or "").upper()) if t}


def support(org: str, canon: str):
    if not (canon or "").strip():
        return "not_a_name_match", ""
    ov = tokens(org) & tokens(canon)
    if not ov:
        return "no_shared_token_with_canonical_name", ""
    lab = "generic_token_only" if ov <= GENERIC else "distinctive_token"
    return lab, "|".join(sorted(ov))


def decide(r: dict, sup: str):
    stage = (r.get("funnel_stage") or "").strip()
    if stage not in KNOWN_STAGES:
        raise SystemExit(f"[952] FATAL: unmapped funnel_stage {stage!r} on EIN "
                         f"{r.get('EIN')!r}. Every dropped or held row gets a "
                         "NAMED reason; there is no catch-all here.")
    excl = ((r.get("excluded_by_prior_ruling") or "").strip() == "1"
            or stage == "excluded_by_prior_ruling")
    if excl and stage in RULED_NATIVE:
        return ("CONFLICT_EXCLUDED_AND_RULED_NATIVE",
                f"excluded_by_prior_ruling=1 AND funnel_stage={stage}. Two "
                "prior decisions disagree on the same organisation. NOT "
                "resolved here - unknown stays unknown.")
    if excl:
        return ("EXCLUDED_PRIOR_RULING",
                f"excluded_by_prior_ruling={r.get('excluded_by_prior_ruling')} "
                f"| funnel_stage={stage}; the ruling and its file are named in "
                "`evidence`. classification_ruling is UNRULED because no HAND "
                "ruling was recorded, which is a different fact.")
    if stage == "canonical_name_match" and sup == "generic_token_only":
        return ("CANDIDATE_NAME_MATCH_GENERIC_TOKEN_ONLY",
                "funnel_stage=canonical_name_match, and every token shared "
                "with the matched tribe's canonical name is a generic English "
                "or civic word (see name_match_shared_tokens). The cited name "
                "match does not support the link. This is a statement about "
                "the EVIDENCE, not a ruling on Native status.")
    return (STAGE[stage], f"funnel_stage={stage}")


def _b(row) -> bytes:
    return US.join(row).encode("utf-8", "replace")


def enrich() -> int:
    with TABLE.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        base = [c for c in hdr if c not in NEW]
        if base != hdr[:len(base)]:
            raise SystemExit("[952] FATAL: base columns are not a prefix of "
                             "the live header")
        rows = [r[:len(base)] + [""] * max(0, len(base) - len(r)) for r in rd]
    h = hashlib.md5()
    h.update(_b(base))
    for r in rows:
        h.update(_b(r))
    digest = h.hexdigest()
    idx = {c: i for i, c in enumerate(base)}

    out, counts, supcounts, flagged = [], {}, {}, []
    for r in rows:
        d = {c: r[idx[c]] for c in base}
        sup, toks = support(d["org_name"], d["canonical_name_token_match"])
        disp, basis = decide(d, sup)
        counts[disp] = counts.get(disp, 0) + 1
        supcounts[sup] = supcounts.get(sup, 0) + 1
        if sup == "generic_token_only":
            flagged.append([d["EIN"], d["org_name"], d["state"],
                            d["funnel_stage"], d["tribe_id_token_match"],
                            d["canonical_name_token_match"], toks, disp])
        out.append(r + [disp, basis, sup, toks])

    bad = sorted(set(counts) - VOCAB)
    if bad:
        raise SystemExit(f"[952] INV-DISPOSITION BREACH at build: {bad}")

    tmp = TABLE.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(base + NEW)
        w.writerows(out)
    bak = Path(str(TABLE) + BAK_TAG)
    if not bak.exists():
        shutil.copyfile(TABLE, bak)
        print(f"  [952] backed up -> {bak.name}")
    os.replace(tmp, TABLE)

    FALSEPOS.parent.mkdir(parents=True, exist_ok=True)
    with FALSEPOS.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["EIN", "org_name", "state", "funnel_stage",
                    "tribe_id_token_match", "canonical_name_token_match",
                    "shared_tokens", "disposition"])
        w.writerows(sorted(flagged, key=lambda x: (x[1], x[0])))

    gained = [c for c in NEW if c not in hdr]
    print(f"  [952] COLUMN DIFF   gained {len(gained)}: {gained}")
    print(f"  [952]               lost   0: []")
    print(f"  [952] rows {len(out):,} unchanged | md5(base {len(base)}) "
          f"{digest}")
    print("  [952] disposition")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"          {k:<44} {v:>6,}  {100.0*v/len(out):5.1f}%")
    print("  [952] name_match_support")
    for k, v in sorted(supcounts.items(), key=lambda kv: -kv[1]):
        print(f"          {k:<44} {v:>6,}  {100.0*v/len(out):5.1f}%")
    print(f"  [952] {len(flagged)} generic-token matches -> "
          f"{FALSEPOS.relative_to(ROOT)}")

    MANIFEST.write_text(json.dumps({
        "built": TODAY, "script": "952_nonprofit_disposition.py",
        "table": "data/clean/np_orgs.csv", "rows": len(out),
        "base_columns": len(base), "md5_base_fields": digest,
        "columns_added": NEW, "disposition_counts": counts,
        "name_match_support_counts": supcounts,
        "generic_token_register":
            str(FALSEPOS.relative_to(ROOT)).replace("\\", "/"),
        "generic_token_rows": len(flagged),
        "generic_token_rows_live_at_canonical_name_match":
            sum(1 for f in flagged if f[3] == "canonical_name_match"),
        "vocabulary": sorted(VOCAB),
    }, indent=2), encoding="utf-8")
    print(f"  [952] wrote {MANIFEST.relative_to(ROOT)}")
    return 0


def verify(path: Path | None = None) -> int:
    p = path or TABLE
    if not MANIFEST.exists():
        print("  [952] verify: no manifest - run the enricher first")
        return 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fails, n = [], 0
    blank = 0
    offvocab = {}
    precision_bad = []
    h = hashlib.md5()
    with p.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        missing = [c for c in NEW if c not in hdr]
        if missing:
            print(f"  [952] INV-SHAPE BREACH: missing {missing}")
            return 1
        base = [c for c in hdr if c not in NEW]
        i = {c: hdr.index(c) for c in hdr}
        h.update(_b(base))
        for row in rd:
            n += 1
            h.update(_b([row[hdr.index(c)] for c in base]))
            d = (row[i["disposition"]] or "").strip()
            if not d:
                blank += 1
            elif d not in VOCAB:
                offvocab[d] = offvocab.get(d, 0) + 1
            if (row[i["name_match_support"]] or "").strip() == \
                    "generic_token_only":
                toks = [t for t in
                        (row[i["name_match_shared_tokens"]] or "").split("|")
                        if t]
                if not toks or any(t not in GENERIC for t in toks):
                    precision_bad.append((row[i["EIN"]], toks))
    digest = h.hexdigest()
    if n != man["rows"]:
        fails.append(f"INV-CONSERVE rows {man['rows']:,} -> {n:,}")
    if digest != man["md5_base_fields"]:
        fails.append("INV-CONSERVE md5 of the base fields moved - a "
                     "pre-existing column was rewritten")
    if blank:
        fails.append(f"INV-DISPOSITION {blank:,} rows have no disposition")
    if offvocab:
        fails.append(f"INV-DISPOSITION off-vocabulary values {offvocab}")
    if precision_bad:
        fails.append(f"INV-PRECISION {len(precision_bad):,} rows labelled "
                     f"generic_token_only record a token that is not generic "
                     f"or record none; e.g. {precision_bad[:3]}")
    print(f"  [952] verify  rows {n:,}   blank dispositions {blank}   "
          f"off-vocabulary {len(offvocab)}   precision breaches "
          f"{len(precision_bad)}   md5(base) "
          f"{'unchanged' if digest == man['md5_base_fields'] else 'MOVED'}")
    for f in fails:
        print(f"  [952] !! {f}")
    return 1 if fails else 0


def selftest() -> int:
    """Prove each NAMED invariant fires, one injection at a time."""
    import contextlib
    if not MANIFEST.exists():
        print("  [952] selftest: run the enricher first")
        return 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fix = ROOT / "data" / "clean" / "_952_selftest_fixture.csv"
    with TABLE.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        rows = [next(rd) for _ in range(400)]
    i = {c: hdr.index(c) for c in hdr}

    def write():
        with fix.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(hdr)
            w.writerows(rows)

    def run():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = verify(fix)
        return code, "\n".join(l for l in buf.getvalue().splitlines()
                               if "!!" in l)

    keep_rows, keep_md5 = man["rows"], man["md5_base_fields"]
    base = [c for c in hdr if c not in NEW]
    h = hashlib.md5()
    h.update(_b(base))
    for r in rows:
        h.update(_b([r[hdr.index(c)] for c in base]))
    man["rows"], man["md5_base_fields"] = len(rows), h.hexdigest()
    MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")
    res = {}
    try:
        write()
        res["A_clean"] = run()

        k = rows[0][i["disposition"]]
        rows[0][i["disposition"]] = ""
        write()
        res["B_blank"] = run()
        rows[0][i["disposition"]] = "other"
        write()
        res["C_vocab"] = run()
        rows[0][i["disposition"]] = k

        hit = next((r for r in rows
                    if r[i["name_match_support"]] == "generic_token_only"),
                   None)
        if hit is None:
            hit = rows[1]
            ks, kt = hit[i["name_match_support"]], \
                hit[i["name_match_shared_tokens"]]
            hit[i["name_match_support"]] = "generic_token_only"
            hit[i["name_match_shared_tokens"]] = "CHICKAHOMINY"
        else:
            ks, kt = hit[i["name_match_support"]], \
                hit[i["name_match_shared_tokens"]]
            hit[i["name_match_shared_tokens"]] = kt + "|CHICKAHOMINY"
        write()
        res["D_precision"] = run()
        hit[i["name_match_support"]], hit[i["name_match_shared_tokens"]] = \
            ks, kt

        drop = rows.pop()
        write()
        res["E_rows"] = run()
        rows.append(drop)

        k2 = rows[0][i["org_name"]]
        rows[0][i["org_name"]] = k2 + " ZZ"
        write()
        res["F_conserve"] = run()
        rows[0][i["org_name"]] = k2
    finally:
        man["rows"], man["md5_base_fields"] = keep_rows, keep_md5
        MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")
        fix.unlink(missing_ok=True)

    checks = [
        ("clean fixture exits 0 and names nothing",
         res["A_clean"] == (0, "")),
        ("blank disposition -> INV-DISPOSITION",
         res["B_blank"][0] == 1 and "INV-DISPOSITION" in res["B_blank"][1]),
        ("`other` -> INV-DISPOSITION off-vocabulary",
         res["C_vocab"][0] == 1 and "off-vocabulary" in res["C_vocab"][1]),
        ("distinctive token under a generic label -> INV-PRECISION",
         res["D_precision"][0] == 1
         and "INV-PRECISION" in res["D_precision"][1]),
        ("a dropped row -> INV-CONSERVE",
         res["E_rows"][0] == 1 and "INV-CONSERVE rows" in res["E_rows"][1]),
        ("a rewritten base field -> INV-CONSERVE md5",
         res["F_conserve"][0] == 1 and "md5" in res["F_conserve"][1]),
    ]
    for label, ok in checks:
        print(f"  [952] selftest  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "enrich"
    sys.exit({"enrich": enrich, "verify": verify,
              "selftest": selftest}[cmd]())
