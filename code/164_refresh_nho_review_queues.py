#!/usr/bin/env python3
r"""
Cedar Press - 164: refresh the two open NHO review queues against current
evidence, so a human can answer them without re-deriving the state first.

WHAT WAS WRONG WITH THEM
------------------------
`review/nho_parent_unknown_2026-08-05.csv` was written by `code/06_verify_nho_via_8a.py`,
which `code/19_rebuild_nho_layer.py` SUPERSEDED the same day - 06 treated an
active 8(a) certification as proof of NHO ownership, and HALOA CONSTRUCTION LLC
disproved it. The queue was never regenerated. Measured today: **31 of its 33
rows have since been ruled**, and the file still asks the same question about
all 33. A reviewer opening it cannot tell which two rows are live.

Worse, it is also INCOMPLETE in the other direction. Three firms that are
unresolved right now - KAPULE LLC, HANA ENTERPRISES INC., HUI HULIAU DEFENSE
SYSTEMS LLC - are absent from it, because 06's question was "does this firm
match a DOI-roster name?" and all three did. A queue that is simultaneously
stale and short is worse than an empty one.

`review/entity_candidates_nho_intertribal.csv` (16 items, NHOIT-001..016) is
younger and its questions are all still open, but four of them are now
answerable-adjacent: `code/163_promote_nho_universe_in_place.py` put the DOI
Office of Native Hawaiian Relations register into the spine, and **whether an
organisation appears on that federal list is now a checkable fact** rather than
an unknown. That is new evidence for six of the sixteen items and it is added
here, measured, not asserted.

THIS SCRIPT ANSWERS NOTHING
---------------------------
`YOUR_RULING` is carried through byte-for-byte and is never populated. Every
column it adds is a MEASUREMENT against a file on disk, named in
`refreshed_from` so the reviewer can repeat it. No row is deleted: a row that
has been answered is marked `RESOLVED` with the answer shown, because deleting
it would destroy the record that the question was asked.

    py -3 code/164_refresh_nho_review_queues.py --check
    py -3 code/164_refresh_nho_review_queues.py

Reads   review/nho_parent_unknown_2026-08-05.csv
        review/entity_candidates_nho_intertribal.csv
        data/clean/nho_verified_entities.csv
        data/clean/nho_register.csv
        data/clean/nho_doi_notification_roster.csv
        data/clean/nho_ito_spine_crosswalk.csv
        data/spine/cedar_entity_spine.csv
        data/clean/cedar_identifier_ledger_final.csv
Writes  review/nho_parent_unknown_2026-08-05.csv        (+ .bak, .part->rename)
        review/entity_candidates_nho_intertribal.csv    (+ .bak, .part->rename)
        logs/164_refresh_nho_review_queues.log
"""

import csv
import importlib.util
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

PARENT_Q = REVIEW / "nho_parent_unknown_2026-08-05.csv"
NHOIT_Q = REVIEW / "entity_candidates_nho_intertribal.csv"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

_spec = importlib.util.spec_from_file_location(
    "m33", CEDAR / "code" / "33_apply_party_rulings.py")
_M33 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_M33)
norm, core = _M33.norm, _M33.core

LOG_LINES = []


def log(msg=""):
    print(msg)
    LOG_LINES.append(msg)


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_atomic(path, rows, fields, tag):
    path = Path(path)
    if path.exists():
        bak = Path(str(path) + f".bak_{TODAY}_{tag}")
        if not bak.exists():
            shutil.copy2(path, bak)
            log(f"  backed up -> {bak.name}")
    part = Path(str(path) + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({f: r.get(f, "") for f in fields})
    part.replace(path)
    log(f"  wrote {path.relative_to(CEDAR)}  ({len(rows):,} rows)")


# ---------------------------------------------------------------------------
# Per-item refresh notes for the NHOIT queue. Each states only what CHANGED
# since the item was written, and each is derived from a file on disk. The
# DOI-list checks are computed below and spliced in, never typed here.
# ---------------------------------------------------------------------------
NHOIT_REFRESH = {
    "NHOIT-001":
        "STILL OPEN, and the evidence AGAINST the current ruling has "
        "strengthened. 'Alaka\u02bbi Foundation Inc' is on the DOI ONHR "
        "notification list (NHO-DOI-0009) and 'Alaka\u02bbi Services Group Inc.' "
        "is NOT - a second, federal source naming the FOUNDATION as the "
        "organisation. The Foundation is already in the spine as N-0018; "
        "code/61 refused ASGI and code/163 left that refusal standing. "
        "Consequence of leaving this open: ASGI's UEI EMNDBXF7JSK9 sits at "
        "tier X in the ledger and its CAGE 8QYZ6 is unbound, so a real 8(a) "
        "firm carries no attribution at all.",
    "NHOIT-002":
        "STILL OPEN. Hoilina Ranch LLC is NOT on the DOI ONHR list, so no "
        "federal source corroborates it as an organisation of any kind, and "
        "13 C.F.R. 124.110's non-profit requirement still rules out an LLC as "
        "the NHO itself. Live cost: its CAGE 6SUD3 is bound in the ledger to "
        "TRBF-CHCKNR-00 (Chicken Ranch, CALIFORNIA) at tier B via need_v6 - "
        "a Keaau, Hawaii firm on a California tribe. See "
        "review/nho_ledger_id_conflations_2026-08-26.csv.",
    "NHOIT-003":
        "STILL OPEN, evidence against strengthened. Ho\u02bbopale Foundation is "
        "NOT on the DOI ONHR list. code/61 refused it (N-0032) and code/163 "
        "honoured that refusal, so Nexus Consulting Group LLC's ruled parent "
        "still does not exist in the spine and its identifiers were REFUSED "
        "rather than forced - see review/nho_firm_parent_spine_gap_2026-08-26.csv. "
        "Pacific Ridge LLC remains tier B UNRESOLVED.",
    "NHOIT-004":
        "STILL OPEN, evidence against strengthened. Kalaimoku Foundation is "
        "NOT on the DOI ONHR list. Refusal N-0033 stands; The Kalaimoku Group "
        "LLC's identifiers were refused for the same spine-gap reason.",
    "NHOIT-005":
        "STILL OPEN. 'Native Hawaiian Organization Charity' is NOT on the DOI "
        "ONHR list, although seven organisations whose names begin 'Native "
        "Hawaiian' are (Chamber of Commerce, Church, Community Development "
        "Corporation, Education Council, Hospitality Association, Legal "
        "Corporation, Philanthropy) - so absence here is a fact about this "
        "organisation, not about the list's coverage of that name pattern. "
        "This matters more than it did: four Lawelawe firms now carry tier-A "
        "ledger links to NHO-HWNRGN-00 on the strength of the ruling alone.",
    "NHOIT-006":
        "STILL OPEN. Neither 'Hui O Hana Pono' nor 'The Hana Group' is on the "
        "DOI ONHR list. HANA ENTERPRISES, INC. is still tier B UNRESOLVED in "
        "nho_verified_entities.csv and has been added to "
        "review/nho_parent_unknown_2026-08-05.csv, which previously omitted it.",
    "NHOIT-007":
        "STILL OPEN. Neither 'Kina\u02bbole Foundation' nor 'Kina\u02bbole Family "
        "of Companies' is on the DOI ONHR list, so that source cannot break "
        "the tie. The Foundation is in the spine as N-0021 at tier B.",
    "NHOIT-008":
        "STILL OPEN but now consequential. Hawaiian Native Corporation is in "
        "the spine as NHO-HAWAII-00, entity_class 'Native Hawaiian "
        "Organization', while nho_parents.csv still labels it ANC. code/163 "
        "wrote DAWSON MCG, INC.'s UEI and CAGE to NHO-HAWAII-00 and took "
        "entity_class from the SPINE row, not from the nho_parents label - so "
        "the ledger now says NHO and nho_parents.csv still says ANC. One of "
        "them is wrong and the disagreement is now visible in two files.",
    "NHOIT-009":
        "STILL OPEN. data/clean/nho_ownership_changes.csv holds the nine "
        "Alaka\u02bbina firms with effective_month 2026-06 and "
        "date_usable_for_attribution = 0 (month only, no day). Nothing has "
        "been merged into ownership_events.csv. The Foundation itself remains "
        "an NHO in the spine (NHO-ALAKAI-00).",
    "NHOIT-010": "STILL OPEN. No new local evidence since 2026-08-06.",
    "NHOIT-011": "STILL OPEN. No new local evidence since 2026-08-06.",
    "NHOIT-012": "STILL OPEN. No new local evidence since 2026-08-06.",
    "NHOIT-013": "STILL OPEN. No new local evidence since 2026-08-06.",
    "NHOIT-014": "STILL OPEN. No new local evidence since 2026-08-06.",
    "NHOIT-015":
        "MATERIALLY CHANGED and now the highest-value item in this queue. The "
        "DOI-list organisations it is about are no longer a tier-C pool "
        "outside the spine: code/163 promoted 179 of them as real entities at "
        "evidence_tier C / evidence_grade doi_roster_only. Accepting an EIN "
        "here now attaches an identifier to a live spine row, so the "
        "suggested disposition (accept the two IRS typos, relax the state "
        "test for mainland civic clubs only, reject the rest) should be ruled "
        "before any EIN-keyed dataset is joined to the new rows. Note the "
        "counterweight named in the item is still real: 'Nakuwauna Foundation' "
        "(84-2031455, HI) must not absorb Nakupuna Foundation.",
    "NHOIT-016": "STILL OPEN. No new local evidence since 2026-08-06.",
}


def main():
    check = "--check" in sys.argv
    log("=== Cedar Press 164: refresh the NHO review queues ===")
    log(f"    mode: {'--check (writes nothing)' if check else 'APPLY'}\n")

    spine = load(SPINE)
    ledger = load(LEDGER)
    verified = load(CLEAN / "nho_verified_entities.csv")
    roster = load(CLEAN / "nho_doi_notification_roster.csv")
    register = load(CLEAN / "nho_register.csv")
    crosswalk = load(CLEAN / "nho_ito_spine_crosswalk.csv")

    spine_by_id = {r["tribe_id"]: r for r in spine}
    spine_norm = {}
    for r in spine:
        spine_norm.setdefault(norm(r["canonical_name"]), r)
        for a in (r.get("aliases") or "").split("|"):
            if a.strip():
                spine_norm.setdefault(norm(a), r)

    roster_norm = {norm(r["organization_name"]) for r in roster}
    roster_core = {core(r["organization_name"]) for r in roster
                   if core(r["organization_name"])}

    def on_doi(name):
        n, c = norm(name), core(name)
        return "YES" if (n in roster_norm or (c and c in roster_core)) else "NO"

    lidx = defaultdict(list)
    for r in ledger:
        lidx[(r["identifier_type"], (r["identifier"] or "").upper())].append(r)

    def ledger_state(idtype, value):
        rows = lidx.get((idtype, (value or "").strip().upper()), [])
        if not rows:
            return "absent from ledger"
        return "; ".join(sorted({
            f"{(r['tribe_id'] or '(unbound)')} tier {r['confidence_tier']} "
            f"[{r['attribution_method']}]" for r in rows}))

    # =====================================================================
    # QUEUE 1 - nho_parent_unknown
    # =====================================================================
    log("[1] review/nho_parent_unknown_2026-08-05.csv")
    q1 = load(PARENT_Q)
    log(f"  rows on file : {len(q1)}")
    ver_by_uei = {(r["uei"] or "").strip().upper(): r for r in verified}
    in_file = {(r["uei"] or "").strip().upper() for r in q1}

    NEW_COLS = ["status_2026_08_26", "current_ruled_parent", "current_source_tier",
                "parent_in_spine", "parent_tribe_id", "uei_in_ledger",
                "cage_in_ledger", "what_changed", "refreshed_from",
                "refreshed_date"]
    q1_fields = list(q1[0].keys())
    for c in NEW_COLS:
        if c not in q1_fields:
            q1_fields.append(c)
    # YOUR_RULING stays LAST so the reviewer's column does not move.
    q1_fields = [c for c in q1_fields if c != "YOUR_RULING"] + ["YOUR_RULING"]

    def refresh_row(row, uei, firm):
        v = ver_by_uei.get(uei)
        row["refreshed_from"] = ("data/clean/nho_verified_entities.csv (rebuilt "
                                 "by code/19) + spine + ledger")
        row["refreshed_date"] = TODAY
        if not v:
            row["status_2026_08_26"] = "NOT_IN_CURRENT_8A_SET"
            row["what_changed"] = (
                "This UEI is no longer in the current 8(a) set that "
                "code/19_rebuild_nho_layer.py produces. Kept, not deleted - "
                "the record that the question was asked is worth more than a "
                "tidy file.")
            return row
        tier = (v["confidence_tier"] or "").strip()
        parent = (v["parent_native_entity"] or "").strip()
        row["current_ruled_parent"] = parent
        row["current_source_tier"] = tier
        hit = spine_norm.get(norm(parent)) if parent else None
        row["parent_in_spine"] = "YES" if hit else ("NO" if parent else "")
        row["parent_tribe_id"] = hit["tribe_id"] if hit else ""
        row["uei_in_ledger"] = ledger_state("UEI", uei)
        row["cage_in_ledger"] = ledger_state("CAGE", v.get("cage_code", ""))

        if tier == "X":
            row["status_2026_08_26"] = "RESOLVED_X"
            row["what_changed"] = (
                "ANSWERED. Ruled NOT NHO-owned - 8(a) here reflects an "
                "individual disadvantaged-business status, not entity "
                "ownership. This is the firm that disproved script 06's whole "
                "premise. No further ruling needed.")
        elif tier == "A" and hit:
            row["status_2026_08_26"] = "RESOLVED"
            row["what_changed"] = (
                f"ANSWERED since this file was written. Parent ruled to "
                f"'{parent}', which is in the spine as {hit['tribe_id']} "
                f"({hit['entity_class']}). code/163 carried this firm's "
                f"identifiers into the ledger at the tier the ruling already "
                f"had.")
        elif tier == "A" and not hit:
            row["status_2026_08_26"] = "OUTSTANDING_SPINE_GAP"
            row["what_changed"] = (
                f"PARTLY answered and still blocked. The parent was ruled "
                f"'{parent}', but that organisation is NOT in the spine - it "
                f"is one of the four code/61 refused on evidence (review items "
                f"NHOIT-001..004). code/163 REFUSED to write this firm's "
                f"identifiers rather than force them onto a substitute. What "
                f"is needed is a ruling on the PARENT's NHO status, not on "
                f"this firm.")
        else:
            row["status_2026_08_26"] = "OUTSTANDING"
            row["what_changed"] = (
                "STILL UNANSWERED. 8(a) certified with ownership class "
                "UNRESOLVED. 8(a) admits both entity-owned and individually "
                "owned firms, so it establishes nothing on its own. A "
                "Hawaiian-language token in the firm name is not evidence "
                "either.")
        return row

    for row in q1:
        refresh_row(row, (row.get("uei") or "").strip().upper(),
                    row.get("firm_name", ""))

    # ADD the currently-unresolved firms this file never contained.
    added_q1 = 0
    for v in verified:
        uei = (v["uei"] or "").strip().upper()
        if uei in in_file:
            continue
        tier = (v["confidence_tier"] or "").strip()
        parent = (v["parent_native_entity"] or "").strip()
        hit = spine_norm.get(norm(parent)) if parent else None
        if tier == "A" and hit:
            continue        # answered and landed; nothing to ask
        row = {c: "" for c in q1_fields}
        row.update({
            "firm_name": v["firm_name"], "uei": uei,
            "cage_code": v.get("cage_code", ""), "city": v.get("city", ""),
            "sba_certifications": v.get("sba_certifications", ""),
            "question": (f"'{v['firm_name']}' holds an active 8(a) "
                         f"certification. 8(a) admits BOTH entity-owned and "
                         f"individually owned firms, so it is not evidence of "
                         f"NHO ownership. Is there an NHO parent, and which?"),
            "YOUR_RULING": "",
        })
        refresh_row(row, uei, v["firm_name"])
        row["what_changed"] = (
            "ADDED 2026-08-26. This firm was never in this queue because "
            "code/06 only asked about firms whose name did NOT match a DOI "
            "roster entry - and a name match is not evidence of ownership. "
            + row["what_changed"])
        q1.append(row)
        added_q1 += 1

    order = {"OUTSTANDING": 0, "OUTSTANDING_SPINE_GAP": 1,
             "NOT_IN_CURRENT_8A_SET": 2, "RESOLVED_X": 3, "RESOLVED": 4}
    q1.sort(key=lambda r: (order.get(r.get("status_2026_08_26", ""), 9),
                           r.get("firm_name", "")))

    c1 = Counter(r["status_2026_08_26"] for r in q1)
    log(f"  rows added (were missing) : {added_q1}")
    log(f"  status distribution       : {dict(c1)}")
    outstanding_1 = c1["OUTSTANDING"] + c1["OUTSTANDING_SPINE_GAP"]
    log(f"  OUTSTANDING for a human   : {outstanding_1}")
    for r in q1:
        if r["status_2026_08_26"].startswith("OUTSTANDING"):
            log(f"      [{r['status_2026_08_26']:22s}] {r['firm_name'][:40]:42s} "
                f"{r['uei']}  parent='{r['current_ruled_parent']}'")

    # =====================================================================
    # QUEUE 2 - entity_candidates_nho_intertribal
    # =====================================================================
    log("\n[2] review/entity_candidates_nho_intertribal.csv")
    q2 = load(NHOIT_Q)
    log(f"  rows on file : {len(q2)}")
    q2_fields = list(q2[0].keys())
    for c in ("status_2026_08_26", "on_doi_onhr_list", "spine_state",
              "what_changed", "refreshed_from", "refreshed_date"):
        if c not in q2_fields:
            q2_fields.append(c)
    q2_fields = [c for c in q2_fields if c != "YOUR_RULING"] + ["YOUR_RULING"]

    cw_by_norm = {norm(r["organization_name"]): r for r in crosswalk}

    for r in q2:
        name = r["entity_name"]
        # The subject name is sometimes a chain or a pair; probe the first
        # named organisation, which is what the item is about.
        probe = name.split(" -> ")[0].split(" vs ")[0].split(" (")[0].strip()
        probe = probe.replace(" - class label", "").strip()
        r["on_doi_onhr_list"] = on_doi(probe)
        hit = spine_norm.get(norm(probe))
        cw = cw_by_norm.get(norm(probe))
        if hit:
            r["spine_state"] = (f"in spine as {hit['tribe_id']} "
                                f"({hit['entity_class']}, evidence_tier "
                                f"{hit.get('evidence_tier', '') or 'n/a'})")
        elif cw:
            r["spine_state"] = f"crosswalk says {cw['status']}: {cw['note'][:60]}"
        else:
            r["spine_state"] = "not in the spine"
        r["what_changed"] = NHOIT_REFRESH.get(
            r["review_id"], "STILL OPEN. No new local evidence.")
        r["status_2026_08_26"] = ("RESOLVED" if (r.get("YOUR_RULING") or "").strip()
                                  else "OUTSTANDING")
        r["refreshed_from"] = ("data/clean/nho_doi_notification_roster.csv + "
                               "spine + nho_ito_spine_crosswalk.csv + ledger")
        r["refreshed_date"] = TODAY

    c2 = Counter(r["status_2026_08_26"] for r in q2)
    log(f"  status distribution     : {dict(c2)}")
    log(f"  OUTSTANDING for a human : {c2['OUTSTANDING']}")
    for r in q2:
        log(f"      {r['review_id']}  on_DOI_list={r['on_doi_onhr_list']:3s} "
            f"{r['entity_name'][:52]}")

    log(f"\n  TOTAL OUTSTANDING across both queues: "
        f"{outstanding_1 + c2['OUTSTANDING']}")

    if check:
        log("\n  --check: nothing written.")
        return

    log("\n[3] Writing")
    write_atomic(PARENT_Q, q1, q1_fields, "pre164")
    write_atomic(NHOIT_Q, q2, q2_fields, "pre164")

    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "164_refresh_nho_review_queues.log").write_text(
        "\n".join(LOG_LINES), encoding="utf-8")


if __name__ == "__main__":
    main()
