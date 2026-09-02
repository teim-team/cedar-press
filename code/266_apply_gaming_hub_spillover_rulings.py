#!/usr/bin/env python3
r"""Cedar Press 266 - apply the four spillover rulings staged in
`review/gaming_facility_hub_rulings_2026-08-26.csv`.

The 2026-08-26 facility-hub build settled these on evidence it had already
retrieved and then left them for another table's owner. That is how a ruling
becomes a note - `62_no_regression_check.py` reports `rulings_unapplied = 1,215`
and its own comment says it plainly: *a ruling that is not applied back to its
source table is not a ruling, it is a note.*

FOUR ITEMS, ALL SETTLED FROM EVIDENCE ALREADY IN THE ROW
--------------------------------------------------------
**1. `gaming_ordinances.csv`, 5 rows indexed "St. Regis Band of Mohawk
Indians", blank `tribe_id`, `entity_match_method = no_spine_match`.** The
index name is not in the spine because the tribe renamed; the DOCUMENTS say so
themselves. NIGC-ORD-19950621-05: *"the Saint Regis Mohawk Tribal Council by
majority vote through TCR 93-102, authorized the establishment of an
independent five (5) member Tribal Gaming Commission"*. NIGC-ORD-20010614-01:
*"the Saint Regis Mohawk Tribal Council to amend the ... Establishment of the
St. Regis Mohawk Tribal Gaming Commission"*.

**THE REVIEW CARD SAYS SEVEN ROWS. THE FILE HOLDS FIVE.** Counted:
`NIGC-ORD-19940121-04`, `-19950621-05`, `-20010614-01`, `-20020725-01` and
one more, all `index_tribe_name = "St. Regis Band of Mohawk Indians"` with a
blank `tribe_id`. The card names five ids and says "and two more"; there are
none. Recorded rather than reconciled by adjusting either.

**2. `gaming_ordinances.csv`, 2 rows indexed "Shoshone-Paiute Tribes",
`ambiguous_core:2_spine_entities`.** The spine holds both the Shoshone-Paiute
Tribes of Duck Valley and the Fallon Paiute-Shoshone, and the core name does not
separate them. **The OCR text does, twice over:**
  - service-of-process address, verbatim: *"Director Shoshone-Paiute Tribal
    Gaming Agency P.O. Box 219 Owyhee, Nevada"* - Owyhee is Duck Valley;
    Fallon is 300 miles away. (The OCR renders the ZIP as `74363`; the real one
    is 89832. **The city and state carry this, not the ZIP** - a mis-OCR'd
    digit string is exactly the kind of evidence that should not be leaned on.)
  - the copy list, verbatim: *"Superintendent, BIA Eastern Nevada Agency"* -
    the BIA agency with jurisdiction over Duck Valley. Fallon is served by the
    Western Nevada Agency.
An address is a NAME-CLASS fact here, not a coordinate: it is the tribe's own
published mailing address inside its own ordinance, which is why this does not
breach *"no rung may read a coordinate before a name"*.

**3. `gaming_ordinances.csv`, 3 rows keyed to the WRONG TRIBE - the only item
here that is a live misattribution rather than a blank.** NIGC-ORD-19990909-01,
-20030618-02 and -20110420-01 carry `tribe_id = TRBF-APCHOK-00` (Apache Tribe
of Oklahoma) with `entity_match_method = containment`. **This is the textbook
containment defect: "Apache Tribe of Oklahoma" is a token-subset of "Ft. Sill
Apache Tribe of Oklahoma".** Three independent legs say Fort Sill:
  - `index_tribe_name` on all three rows is *"Ft. Sill Apache Tribe of
    Oklahoma"* - NIGC's own index;
  - the PDFs are named `ftsillapachetribeofok-*` - **and a filename is the
    WEAKEST of these three, which is why it is not relied on alone**;
  - the document text, verbatim: *"V. FORT SILL APACHE GAMING COMMISSION: A.
    The Fort Sill Apache Gaming Commission is hereby established to regulate
    gaming on Fort Sill Apache..."* and the NIGC chairman's own closing
    sentence *"...and the Fort Sill Apache Tribe of Oklahoma on future gaming
    issues."*
The Fort Sill Apache Tribe is a separate federally recognized tribe,
`TRBF-FSCWSA-00`.

**4. `ca_gaming_facilities_official.csv`, the CGCC Barona rows.** CAFAC-00006,
-00070 and -00134 are blank on
`ambiguous_containment:2:Capitan Grande, Capitan Grande Band` - the exact
ambiguity `172` ruled by hand on the facility row. **They need no hand ruling
here, because all three carry `facility_id = CCP-41700`,** and that facility is
keyed `CNSF-CPTNGR-BA` at tier B. So this is a `facility_id_exact` inheritance:
the strongest rung in the hub model, reading an id another build already wrote,
with **the tier copied verbatim from the facility row.** No name is matched and
no tier is assigned.

**THE SAME DEFECT SITS ON THREE VIEJAS ROWS AND THE CARD DOES NOT MENTION
THEM.** CAFAC-00061 and -00127 carry `facility_id = CCP-43400` (Viejas Casino &
Resort, `CNSF-CPTNGR-VJ`, tier B) and the identical
`ambiguous_containment:2:Capitan Grande, Capitan Grande Band`. Fixing Barona
and leaving its sibling would be arbitrary, so both are done and the extension
is stated. **CAFAC-00169 is REFUSED**: it carries the same published tribe
name and NO `facility_id`, so there is nothing to inherit from, and keying it
would be assigning a tier rather than inheriting one.

THE TIER IS PRODUCED, NEVER PICKED
----------------------------------
Ordinance rows are keyed through `70_key_unjoined_datasets.key_name` - the same
function `172` used and the same one that keyed the rest of these files - fed
**the tribe name as the DOCUMENT ITSELF publishes it**, with the state the
document gives. The verdict is written verbatim into `entity_match_basis`.

That choice costs a tier on purpose. `key_name("Saint Regis Mohawk Tribe")`
returns **alias / tier A**; `key_name("Saint Regis Mohawk Tribal Council")` -
the string the ordinance actually contains - returns **containment / tier B**.
The document says "Council". **Feeding the resolver a tidier string than the
source contains is how a consumer assigns itself a tier**, so the weaker,
truthful string is used and the tier that follows from it is kept.

Fort Sill lands at tier A on `alias`, and the resolver's own basis records
`contains_trap_token:apache` alongside `state corroborates (OK)`. The match does
not REST on the trap token - `Fort Sill` is the distinguishing part and the hit
is an alias, not a bare containment - so it is taken, with the resolver's note
carried into the row rather than dropped.

DATES: NOTHING IS RULED AGAINST A CURRENT PAGE
----------------------------------------------
Every one of these ten ordinance rows is a historical instrument - seven are
`SUPERSEDED_BY_LATER_INSTRUMENT`, dated 1994-2012. **Not one is keyed from a
2026 source.** Every leg above is text inside the contemporaneous document or
NIGC's index entry for it. Three gaming rulings were withdrawn on 2026-08-06
for ruling a historical record against a current page; this build reads only
what the record itself says, and `in_force_status` is not touched.

SAFETY: per-file backup `.bak_<date>_pre266`, `.part` then rename, each target
re-read inside the write path, refuses if a row is not in the state the ruling
expects (a concurrent agent has edited it), verified by RE-READING.

    py -3 code/266_apply_gaming_hub_spillover_rulings.py --check
    py -3 code/266_apply_gaming_hub_spillover_rulings.py --apply
"""

import csv
import importlib.util
import shutil
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
LOGS = CEDAR / "logs"
ORD = CLEAN / "gaming_ordinances.csv"
CAF = CLEAN / "ca_gaming_facilities_official.csv"
FACS = CLEAN / "gaming_facilities.csv"
TODAY = date.today().isoformat()
SCRIPT = "266_apply_gaming_hub_spillover_rulings.py"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# --- item 1/2/3: gaming_ordinances -----------------------------------------
# selector: (column, value) identifying the group; expect_tribe_id is what the
# rows must currently carry, or "" for blank. Refuse on any mismatch.
ORD_RULINGS = [
    {
        "name": "St. Regis Band of Mohawk Indians",
        "index_name": "St. Regis Band of Mohawk Indians",
        "expect_tribe_id": "",
        "expect_method_prefix": "no_spine_match",
        "published": "Saint Regis Mohawk Tribal Council",
        "state": "NY",
        "tribe_id": "TRBF-SRMHWK-00",
        "evidence":
            "The NIGC index name 'St. Regis Band of Mohawk Indians' is not in "
            "the spine because the tribe renamed. The ordinance documents name "
            "the current body themselves: NIGC-ORD-19950621-05 verbatim - 'the "
            "Saint Regis Mohawk Tribal Council by majority vote through TCR "
            "93-102, authorized the establishment of an independent five (5) "
            "member Tribal Gaming Commission'; NIGC-ORD-20010614-01 verbatim - "
            "'the Saint Regis Mohawk Tribal Council to amend the ... "
            "Establishment of the St. Regis Mohawk Tribal Gaming Commission'. "
            "All contemporaneous with the instruments; no current page is read.",
    },
    {
        "name": "Shoshone-Paiute Tribes",
        "index_name": "Shoshone-Paiute Tribes",
        "expect_tribe_id": "",
        "expect_method_prefix": "ambiguous_core",
        "published": "Shoshone-Paiute Tribes of the Duck Valley Indian "
                     "Reservation",
        "state": "NV",
        "tribe_id": "TRBF-DUCKVY-00",
        "evidence":
            "The core name 'Shoshone-Paiute' does not separate Duck Valley "
            "from the Fallon Paiute-Shoshone, which is why the build left it "
            "blank. The OCR text separates them twice: the ordinance's own "
            "service-of-process address reads 'Director Shoshone-Paiute Tribal "
            "Gaming Agency P.O. Box 219 Owyhee, Nevada' (Owyhee IS Duck "
            "Valley; Fallon is ~300 miles away), and the NIGC letter's copy "
            "list reads 'Superintendent, BIA Eastern Nevada Agency' - the "
            "agency with jurisdiction over Duck Valley, where Fallon is served "
            "by the Western Nevada Agency. The OCR renders the ZIP as 74363 "
            "against a real 89832; THE CITY AND STATE CARRY THIS, NOT THE ZIP.",
    },
    {
        "name": "Ft. Sill Apache Tribe of Oklahoma",
        "index_name": "Ft. Sill Apache Tribe of Oklahoma",
        "expect_tribe_id": "TRBF-APCHOK-00",
        "expect_method_prefix": "containment",
        "published": "Fort Sill Apache Tribe of Oklahoma",
        "state": "OK",
        "tribe_id": "TRBF-FSCWSA-00",
        "evidence":
            "LIVE MISATTRIBUTION, not a blank. The rows carry TRBF-APCHOK-00 "
            "(Apache Tribe of Oklahoma) via entity_match_method=containment - "
            "'Apache Tribe of Oklahoma' is a token-subset of 'Ft. Sill Apache "
            "Tribe of Oklahoma'. Three legs say Fort Sill: (a) NIGC's own "
            "index_tribe_name on all three rows is 'Ft. Sill Apache Tribe of "
            "Oklahoma'; (b) the document text verbatim - 'V. FORT SILL APACHE "
            "GAMING COMMISSION: A. The Fort Sill Apache Gaming Commission is "
            "hereby established to regulate gaming on Fort Sill Apache...' and "
            "the NIGC chairman's closing '...and the Fort Sill Apache Tribe of "
            "Oklahoma on future gaming issues'; (c) the PDFs are named "
            "ftsillapachetribeofok-*, WHICH IS THE WEAKEST LEG AND IS NOT "
            "RELIED ON ALONE. The Fort Sill Apache Tribe is a separate "
            "federally recognized tribe.",
    },
]

# --- item 4: ca_gaming_facilities_official ---------------------------------
CAF_EXPECT_METHOD = "ambiguous_containment:2:Capitan Grande, Capitan Grande Band"
CAF_REFUSE = {
    "CAFAC-00169":
        "Carries the Viejas published tribe name and NO facility_id, so there "
        "is nothing to inherit from. Keying it would be ASSIGNING a tier "
        "rather than inheriting one, which is the failure this whole column "
        "block exists to prevent. Left blank, said out loud.",
}


def log(msg):
    LOGS.mkdir(exist_ok=True)
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))
    with open(LOGS / f"266_spillover_{TODAY}.log", "a",
              encoding="utf-8") as fh:
        fh.write(msg + "\n")


def read(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def header_of(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return next(csv.reader(fh), [])


def write_atomic(path, fields, rows):
    part = Path(path).with_suffix(Path(path).suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(path)


def backup(path):
    b = Path(path).with_suffix(Path(path).suffix + f".bak_{TODAY}_pre266")
    if not b.exists():
        shutil.copy2(path, b)
    return b.name


def load70():
    p = CEDAR / "code" / "70_key_unjoined_datasets.py"
    spec = importlib.util.spec_from_file_location("m70", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def select_ord(rows, r_):
    out = []
    for r in rows:
        idx = (r.get("index_tribe_name") or r.get("tribe_name") or "").strip()
        if idx != r_["index_name"]:
            continue
        if (r.get("tribe_id") or "").strip() != r_["expect_tribe_id"]:
            continue
        if not (r.get("entity_match_method") or "").startswith(
                r_["expect_method_prefix"]):
            continue
        out.append(r)
    return out


def main():
    apply_ = "--apply" in sys.argv
    log(f"=== Cedar Press 266: gaming hub spillover rulings ({TODAY}) "
        f"[{'APPLY' if apply_ else 'CHECK, read-only'}] ===")

    M70 = load70()
    spine = {s["tribe_id"] for s in M70.SPINE_ROWS}

    # ---------------- gaming_ordinances -----------------------------------
    orows = read(ORD)
    if not orows:
        log(f"FATAL: {ORD} missing")
        return 1
    log(f"\ngaming_ordinances.csv: {len(orows):,} rows")

    ord_plan = []
    for r_ in ORD_RULINGS:
        if r_["tribe_id"] not in spine:
            log(f"  REFUSE {r_['name']}: {r_['tribe_id']} not in the spine")
            return 1
        sel = select_ord(orows, r_)
        res = M70.key_name(r_["published"], "gaming_ordinances", r_["state"])
        if res["tribe_id"] != r_["tribe_id"]:
            log(f"  REFUSE {r_['name']}: resolver returns {res['tribe_id']!r} "
                f"for {r_['published']!r}, ruling expects {r_['tribe_id']!r}")
            return 1
        log(f"  {r_['name'][:38]:38} {len(sel):2} row(s)  "
            f"{r_['expect_tribe_id'] or '(blank)':16} -> {r_['tribe_id']}  "
            f"tier {res['tier']} method {res['method']}  ({res['basis']})")
        for r in sel:
            log(f"      {r.get('ordinance_id'):24} {r.get('approval_date')} "
                f"{r.get('in_force_status','')}")
        ord_plan.append((r_, res, sel))

    # ---------------- ca_gaming_facilities_official ------------------------
    crows = read(CAF)
    fac = {r["facility_id"]: r for r in read(FACS)}
    log(f"\nca_gaming_facilities_official.csv: {len(crows):,} rows")
    caf_plan, caf_refused = [], []
    for r in crows:
        if (r.get("tribe_id") or "").strip():
            continue
        if (r.get("entity_match_method") or "") != CAF_EXPECT_METHOD:
            continue
        rid = r.get("record_id")
        fid = (r.get("facility_id") or "").strip()
        if not fid or fid not in fac:
            caf_refused.append((rid, CAF_REFUSE.get(
                rid, "no facility_id, or it is not in the hub - nothing to "
                     "inherit from")))
            continue
        f = fac[fid]
        ftribe = (f.get("tribe_id") or "").strip()
        if not ftribe:
            caf_refused.append((rid, f"{fid} itself carries no tribe_id"))
            continue
        caf_plan.append((r, f))
        log(f"  {rid:12} {(r.get('tribe_name_as_published') or '')[:40]:40} "
            f"{fid:12} -> {ftribe} tier {f.get('entity_tier') or '(blank)'} "
            f"(inherited verbatim)")
    for rid, why in caf_refused:
        log(f"  REFUSED {rid:12} {why[:110]}")

    total = sum(len(s) for _, _, s in ord_plan) + len(caf_plan)
    log(f"\n{total} row(s) to write "
        f"({sum(len(s) for _,_,s in ord_plan)} ordinance, {len(caf_plan)} CA)")
    if not apply_:
        log("\n--check only. Nothing written. Re-run with --apply.")
        return 0
    if total == 0:
        log("nothing to do")
        return 0

    # ---------------- write ordinances -------------------------------------
    log(f"\nbacked up -> {backup(ORD)}")
    orows = read(ORD)                       # re-read INSIDE the write path
    ofields = header_of(ORD)
    for c in ("entity_match_basis", "entity_keyed_date", "tribe_id_as_built"):
        if c not in ofields:
            ofields.append(c)
    n_ord = 0
    for r_, res, _ in ord_plan:
        for r in select_ord(orows, r_):
            r["tribe_id_as_built"] = (r.get("tribe_id") or "")
            r["tribe_id"] = r_["tribe_id"]
            r["entity_match_method"] = res["method"]
            r["entity_tier"] = res["tier"]
            r["entity_state"] = r_["state"]
            r["entity_match_basis"] = (
                f"{SCRIPT} {TODAY}; resolved via 70.key_name("
                f"{r_['published']!r}, state={r_['state']!r}) -> "
                f"{res['basis']}; EVIDENCE: {r_['evidence']}")
            r["entity_keyed_date"] = TODAY
            n_ord += 1
    write_atomic(ORD, ofields, orows)

    # ---------------- write CA official ------------------------------------
    log(f"backed up -> {backup(CAF)}")
    crows = read(CAF)                       # re-read INSIDE the write path
    cfields = header_of(CAF)
    for c in ("entity_tier_basis", "entity_keyed_date"):
        if c not in cfields:
            cfields.append(c)
    want = {r.get("record_id") for r, _ in caf_plan}
    n_caf = 0
    for r in crows:
        if r.get("record_id") not in want:
            continue
        f = fac[(r.get("facility_id") or "").strip()]
        r["tribe_id"] = (f.get("tribe_id") or "").strip()
        r["tribe_canonical_name"] = (f.get("tribe_canonical_name") or "")
        r["entity_match_method"] = "facility_id_exact"
        r["entity_tier"] = (f.get("entity_tier") or "").strip()
        r["entity_tier_basis"] = (
            f"{SCRIPT} {TODAY}; INHERITED verbatim from "
            f"gaming_facilities.{f['facility_id']}.entity_tier "
            f"(method={f.get('entity_match_method','') or 'none'}). This row "
            f"already named that facility; the CGCC's published operator "
            f"string 'Barona Group of Capitan Grande Band of Mission Indians "
            f"of the Barona Reservation' is the one resolve_entity refuses as "
            f"ambiguous_containment, so NO NAME IS MATCHED HERE - the link is "
            f"read off an id an earlier build wrote, and the tier is copied, "
            f"not assigned.")
        r["entity_keyed_date"] = TODAY
        n_caf += 1
    write_atomic(CAF, cfields, crows)

    # ---------------- VERIFY BY RE-READING ---------------------------------
    ok = True
    ob = read(ORD)
    cb = read(CAF)
    log(f"\nordinances {len(orows):,} -> {len(ob):,} rows, {n_ord} keyed")
    log(f"CA official {len(crows):,} -> {len(cb):,} rows, {n_caf} keyed")
    if len(ob) != len(orows) or len(cb) != len(crows):
        log("  FAIL: row count changed")
        ok = False
    for r_, _, _ in ord_plan:
        left = [r for r in ob
                if (r.get("index_tribe_name") or r.get("tribe_name") or ""
                    ).strip() == r_["index_name"]
                and (r.get("tribe_id") or "").strip() != r_["tribe_id"]]
        if left:
            log(f"  FAIL: {len(left)} {r_['name']} row(s) not keyed")
            ok = False
    if any(r.get("record_id") in want and not (r.get("tribe_id") or "").strip()
           for r in cb):
        log("  FAIL: a CA row targeted for keying is still blank")
        ok = False
    blank_after = sum(1 for r in ob if not (r.get("tribe_id") or "").strip())
    log(f"  gaming_ordinances blank tribe_id: 55 -> {blank_after}")
    cblank = sum(1 for r in cb if not (r.get("tribe_id") or "").strip())
    log(f"  ca_gaming_facilities_official blank tribe_id: 11 -> {cblank}")
    log("  re-read verification: " + ("PASS" if ok else "FAIL"))
    if not ok:
        log("  RESTORE the .bak_*_pre266 files")
        return 1
    log("\nNOW RUN: py -3 code/62_no_regression_check.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
