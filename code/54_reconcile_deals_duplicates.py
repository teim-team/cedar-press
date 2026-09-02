#!/usr/bin/env python3
"""
Cedar Press - 54: Reconcile the deals ledger's known double-counts, apply the
four audited-filing corrections, and scan for further duplicates.

Three jobs, in this order, because the third depends on the first two.

1. THE DATING RULE, APPLIED
   `ND-2026-077` records UIC's acquisition of Northbank Civil & Marine as a
   2026 event dated 2026-01-16 from a UIC newsroom release. UIC's AUDITED
   financial statements say "On December 31, 2025, the Company acquired a 51%
   ownership in Northbank Civil & Marine, LLC (NCM) for cash consideration of
   $11,730,000" and consolidate NCM from that date. The same run wrote the
   audited version as `ANCSA2-2025-006`. Both rows are in the ledger, which
   double-counts the transaction, and the 2026 row also overstates 2026 YTD.

   Audited financial statements outrank a newsroom release on dating and on
   value. The 2025 row survives; the 2026 row is WITHDRAWN to
   `review/deals_withdrawn_duplicates.csv`, whole, with its reason - not
   deleted. Its newsroom URL is carried onto the surviving row as a second
   source, so nothing retrieved is lost.

2. FOUR CORRECTIONS FROM AUDITED FILINGS
   Documented in `docs/ANCSA_PORTAL_V2_LOG.md` §5 and
   `review/deals_skipped_ancsa_portal_v2.csv` (SK2-ANCSA-001..004), logged but
   never written. Each is re-verified here against the staged filing text in
   `data/interim/ancsa_txt*/` before it is applied - the quoted sentence must
   be present in the local document or the correction is refused.

   Applying the MA2020-001 correction CREATES a double count, because
   `ANCSA2-2020-003` is the same UIC/Johansen transaction. That row is
   therefore withdrawn as well, after its richer accounting detail (the
   noncontrolling interest, the excluded contingent payments) is merged into
   MA2020-001. This is the one merge this script performs beyond the
   instructed Northbank fix, and it is performed only because the source
   agent had already adjudicated the two rows as one transaction and
   cross-listed it as `duplicate_in_live_ledger` (SK2-ANCSA-003). Every other
   candidate is reported, never merged.

3. DUPLICATE SCAN
   Writes `review/deals_duplicate_candidates.csv`. NOTHING is auto-merged.
   A near-duplicate is often two genuine tranches of one financing -
   `ND-2013-004` and `ND-2013-005` are a $43.6M and a $9.855M leg of one Coos
   bond exchange on one day, and merging them would destroy real money.

Idempotent: re-running re-verifies and reports "already applied".

Reads  deals_2026_ytd.csv, deals_historical_2020_2025.csv,
       data/clean/deals_*_additions.csv, data/interim/ancsa_txt*/
Writes the two root ledgers + deals_2026_ytd_additions.csv,
       deals_ancsa_portal_v2_additions.csv  (backups alongside)
       review/deals_withdrawn_duplicates.csv
       review/deals_duplicate_candidates.csv
"""

import csv
import datetime
import glob
import itertools
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
INTERIM = CEDAR / "data" / "interim"
REVIEW = CEDAR / "review"
TODAY = datetime.date.today().isoformat()

LEDGERS = [CEDAR / "deals_2026_ytd.csv",
           CEDAR / "deals_historical_2020_2025.csv"]

STAR = "https://portal.akdbsstar.us/StarWebPortal/ViewFile.aspx?Id="
STAR_TYPE = ("ANCSA corporation annual report filed with the Alaska Division "
             "of Banking and Securities (STAR portal)")

# ---------------------------------------------------------------------------
# The corrections. Each carries the sentence that must be found in the staged
# filing text before anything is written. `verify_needle` is checked against
# every local .txt whose name contains `verify_file_hint`; a correction whose
# sentence cannot be found locally is REFUSED and reported, never guessed.
# ---------------------------------------------------------------------------
CORRECTIONS = [
    {
        "deal_id": "MA2020-001",
        "ledger": "deals_historical_2020_2025.csv",
        "lead": "SK2-ANCSA-003",
        "verify_file_hint": "Ukpeagvik",
        "verify_needle": ("On March 31, 2020, the Company acquired a 51% "
                          "ownership in Johansen Construction Company, LLC"),
        "source_url": STAR + "00def1d3-f92b-40e8-a9c9-65c8bb6d7710",
        "set": {
            "Event_Date": "2020-03-31",
            "Event_Quarter": "Q1",
            "Event_Month": "2020-03",
            "Status": "Completed",
            "Announced_Value_USD": "4080000",
            "Value_Type": (
                "Cash consideration as stated in the business acquisition "
                "note. The acquisition-date table subtracts a noncontrolling "
                "interest of $3,708,377 to reach this figure. Seller payments "
                "of up to $800,000 contingent on JCC pre-tax net income "
                "2020-2023 are EXCLUDED: the filing states they are "
                "contingent on continued employment and were excluded from "
                "acquisition accounting."),
            "Source_1": STAR + "00def1d3-f92b-40e8-a9c9-65c8bb6d7710",
            "Source_1_Type": STAR_TYPE,
            "Verification_Status": "Primary verified",
            "Confidence": "High",
            "Date_Basis": (
                "Transaction date stated in the business acquisition note: "
                "'On March 31, 2020, the Company acquired a 51% ownership in "
                "Johansen Construction Company, LLC (JCC) and its wholly "
                "owned subsidiary, Highmark Concrete Contractors, LLC (HCC) "
                "for cash consideration of $4,080,000.'"),
            "Description": (
                "UIC acquired a 51% ownership in Johansen Construction "
                "Company, LLC (JCC) and its wholly owned subsidiary Highmark "
                "Concrete Contractors, LLC (HCC), both organised in "
                "Washington, expanding UIC into the Pacific Northwest."),
        },
        "note": (
            "CORRECTED {today} from UIC's audited financial statements "
            "(SK2-ANCSA-003, docs/ANCSA_PORTAL_V2_LOG.md S5). Supplies the "
            "exact date, the exact consideration, the 51% interest and a "
            "primary source; this row is no longer UNSOURCED. Goodwill of "
            "$220,261 is an allocation component and acquisition-related "
            "costs of $339,675 are costs, not consideration. The duplicate "
            "harvest row ANCSA2-2020-003 was withdrawn in favour of this "
            "row; see review/deals_withdrawn_duplicates.csv."),
    },
    {
        "deal_id": "MA2020-003",
        "ledger": "deals_historical_2020_2025.csv",
        "lead": "SK2-ANCSA-004",
        "verify_file_hint": "Bering",
        "verify_needle": "18,324",
        "source_url": STAR + "be368e17-cf57-4f3a-a702-2942dda9a794",
        "set": {
            "Announced_Value_USD": "18324000",
            "Value_Type": (
                "Fair value of total consideration transferred, per the "
                "business acquisition note: cash of $17,803 thousand plus a "
                "final working capital adjustment of $521 thousand. "
                "Cross-foots to identifiable net assets of $6,874 thousand "
                "plus goodwill of $11,450 thousand."),
            "Source_2": STAR + "be368e17-cf57-4f3a-a702-2942dda9a794",
            "Source_2_Type": STAR_TYPE,
            "Verification_Status": "Primary verified",
            "Confidence": "High",
        },
        "note": (
            "VALUE ADDED {today} from BSNC's audited financial statements "
            "(SK2-ANCSA-004, docs/ANCSA_PORTAL_V2_LOG.md S5). The FY2023 "
            "annual report states the consideration table in whole "
            "thousands; the FY2022 report carries the same note but its "
            "total OCRs incompletely, so the FY2023 filing is cited. The "
            "2020-05-22 date was already correct and is unchanged."),
    },
    {
        "deal_id": "ND-2026-004",
        "ledger": "deals_2026_ytd.csv",
        "lead": "SK2-ANCSA-001",
        "verify_file_hint": "Cook_Inlet",
        "verify_needle": ("On January 21, 2026 the Company acquired 100% of "
                          "the outstanding equity interests of"),
        "source_url": STAR + "4360ed40-049b-4431-a314-888fca64163c",
        "set": {
            "Event_Date": "2026-01-21",
            "Event_Month": "2026-01",
            "Announced_Value_USD": "42100000",
            "Value_Type": (
                "Total consideration stated in the CIRI 2025 annual report "
                "subsequent-events note, subject to customary working "
                "capital adjustments."),
            "Source_2": STAR + "4360ed40-049b-4431-a314-888fca64163c",
            "Source_2_Type": STAR_TYPE,
            "Verification_Status": "Primary verified",
            "Date_Basis": (
                "Transaction date stated in the subsequent-events note: 'On "
                "January 21, 2026 the Company acquired 100% of the "
                "outstanding equity interests of ISYS, Incorporated, dba I2X "
                "Technologies ... for total consideration of $42,100,000.'"),
        },
        "note": (
            "CORRECTED {today} from CIRI's audited financial statements "
            "(SK2-ANCSA-001, docs/ANCSA_PORTAL_V2_LOG.md S5). The row "
            "previously carried the 2026-02-02 company-release date and no "
            "value; the audited filing dates the transaction 12 days "
            "earlier. Displaced source (kept for provenance): "
            "https://www.ciri.com/ravens-circle/ciri-expands-with-two-"
            "strategic-acquisitions/ (Tribal/ANC website)."),
    },
    {
        "deal_id": "ND-2026-005",
        "ledger": "deals_2026_ytd.csv",
        "lead": "SK2-ANCSA-002",
        "verify_file_hint": "Cook_Inlet",
        "verify_needle": ("On January 29, 2026, the Company acquired 100% of "
                          "the equity interest of HABCO Industries"),
        "source_url": STAR + "4360ed40-049b-4431-a314-888fca64163c",
        "set": {
            "Event_Date": "2026-01-29",
            "Event_Month": "2026-01",
            "Announced_Value_USD": "60612000",
            "Value_Type": (
                "Consideration stated in the CIRI 2025 annual report "
                "subsequent-events note, subject to customary working "
                "capital adjustments."),
            "Source_2": STAR + "4360ed40-049b-4431-a314-888fca64163c",
            "Source_2_Type": STAR_TYPE,
            "Verification_Status": "Primary verified",
            "Date_Basis": (
                "Transaction date stated in the subsequent-events note: 'On "
                "January 29, 2026, the Company acquired 100% of the equity "
                "interest of HABCO Industries ... for consideration of "
                "$60,612,000.'"),
        },
        "note": (
            "CORRECTED {today} from CIRI's audited financial statements "
            "(SK2-ANCSA-002, docs/ANCSA_PORTAL_V2_LOG.md S5). The row "
            "previously carried the 2026-02-04 syndication date and no "
            "value; the audited filing dates the transaction 6 days "
            "earlier. Displaced source (kept for provenance): "
            "https://www.ciri.com/ravens-circle/ciri-expands-with-two-"
            "strategic-acquisitions/ (Tribal/ANC website)."),
    },
]

# ---------------------------------------------------------------------------
# Withdrawals. `keep` is the surviving Deal_ID; `carry_source` is a URL from
# the withdrawn row moved onto the survivor so no retrieved evidence is lost.
# ---------------------------------------------------------------------------
WITHDRAWALS = [
    {
        "withdraw": "ND-2026-077",
        "file": CLEAN / "deals_2026_ytd_additions.csv",
        "keep": "ANCSA2-2025-006",
        "keep_file": CLEAN / "deals_ancsa_portal_v2_additions.csv",
        "lead": "SK2-ANCSA-005",
        "reason": (
            "Same transaction as ANCSA2-2025-006: UIC acquires 51% of "
            "Northbank Civil & Marine. ND-2026-077 dates it 2026-01-16 from "
            "a uicalaska.com newsroom release; UIC's AUDITED financial "
            "statements date it 2025-12-31 for cash consideration of "
            "$11,730,000 and consolidate NCM from that date. Audited "
            "financial statements outrank a newsroom release on both date "
            "and value, so the transaction belongs to 2025. Keeping both "
            "double-counted it and the 2026 row overstated 2026 "
            "year-to-date by one acquisition."),
        "carry_source": ("https://uicalaska.com/2026/01/16/ukpeagvik-inupiat-"
                         "corporation-acquires-majority-interest-in-northbank-"
                         "civil-and-marine-inc/"),
        "carry_source_type": "Native parent press release (announcement date)",
    },
    {
        "withdraw": "ANCSA2-2020-003",
        "file": CLEAN / "deals_ancsa_portal_v2_additions.csv",
        "keep": "MA2020-001",
        "keep_file": CEDAR / "deals_historical_2020_2025.csv",
        "lead": "SK2-ANCSA-003",
        "reason": (
            "Same transaction as MA2020-001: UIC acquires 51% of Johansen "
            "Construction and Highmark Concrete, 2020-03-31, $4,080,000. The "
            "harvest run itself adjudicated the two as one transaction and "
            "cross-listed this row as duplicate_in_live_ledger. Its audited "
            "date, value, source and accounting detail have been merged into "
            "MA2020-001, which is the live-ledger Deal_ID other files "
            "reference. Keeping both would have double-counted $4,080,000 "
            "the moment the MA2020-001 correction was applied."),
        "carry_source": "",
        "carry_source_type": "",
    },
]

# ---------------------------------------------------------------------------
# Duplicate scan
# ---------------------------------------------------------------------------
STRUCTURAL = {
    "nation", "nations", "tribe", "tribes", "tribal", "band", "bands",
    "pueblo", "community", "communities", "rancheria", "village", "villages",
    "colony", "indians", "indian", "native", "peoples", "people",
    "reservation", "confederated", "of", "the", "and",
    "inc", "llc", "ltd", "limited", "incorporated", "corporation", "corp",
    "company",
}
# Role words describe what an organisation DOES. Two housing authorities share
# them, so leaving them in makes every pair of authorities look 50% similar and
# the scan returns 210 pairs of unrelated HUD awards.
ROLE = {"housing", "authority", "authorities", "board", "entity", "tdhe",
        "tdhes"}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("\u02bb", "").replace("\u02bc", "").replace("\u2018", "")
    s = s.replace("\u0142", "l")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def core(s):
    return frozenset(t for t in norm(s).split() if t not in STRUCTURAL)


def ident(s):
    return frozenset(t for t in core(s) if t not in ROLE)


def jac(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return [], []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd), list(rd.fieldnames or [])


def write_csv(p, rows, fields):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def ledger_files():
    return LEDGERS + sorted(CLEAN.glob("deals_*_additions.csv"))


def parse_date(r):
    try:
        return datetime.date.fromisoformat((r.get("Event_Date") or "").strip())
    except ValueError:
        return None


def parse_value(r):
    s = (r.get("Announced_Value_USD") or "").replace(",", "").replace("$", "")
    try:
        v = float(s.strip())
        return v if v > 0 else None
    except ValueError:
        return None


def verify(hint, needle):
    """Is the quoted sentence actually in a locally staged filing?

    Cedar Press is self-contained: the ANCSA filings were downloaded and their
    text extracted into data/interim, so a correction can be re-verified
    against the primary document without touching the network.
    """
    for d in ("ancsa_txt", "ancsa_txt_v2"):
        for f in (INTERIM / d).glob("*.txt"):
            if hint.lower() not in f.name.lower():
                continue
            t = f.read_text(encoding="utf-8", errors="replace")
            if needle in t:
                return f.name
    return None


def main():
    print("=== Cedar Press 54: reconcile deals duplicates ===\n")

    # ---- 1. verify every correction against a local filing FIRST -----------
    print("verifying corrections against staged filing text")
    for c in CORRECTIONS:
        c["_verified_in"] = verify(c["verify_file_hint"], c["verify_needle"])
        state = c["_verified_in"] or "*** NOT FOUND - correction refused ***"
        print(f"  {c['deal_id']:<16} {c['lead']:<14} {state[:70]}")
    print()

    touched = {}   # path -> (rows, fields)

    def load(p):
        p = Path(p)
        if p not in touched:
            rows, fields = read_csv(p)
            touched[p] = [rows, fields]
        return touched[p]

    def find(p, deal_id):
        rows, _ = load(p)
        for r in rows:
            if (r.get("Deal_ID") or "").strip() == deal_id:
                return r
        return None

    # ---- 2. apply the corrections ------------------------------------------
    print("corrections")
    applied = Counter()
    for c in CORRECTIONS:
        if not c["_verified_in"]:
            applied["REFUSED (sentence not found locally)"] += 1
            continue
        path = CEDAR / c["ledger"] if (CEDAR / c["ledger"]).exists() \
            else CLEAN / c["ledger"]
        row = find(path, c["deal_id"])
        if row is None:
            print(f"  {c['deal_id']}: NOT FOUND in {c['ledger']} - skipped")
            applied["not found"] += 1
            continue
        changes = []
        for k, v in c["set"].items():
            if k not in row:
                continue
            if (row.get(k) or "").strip() != v:
                changes.append(f"{k}: '{(row.get(k) or '')[:28]}' -> '{v[:28]}'")
                row[k] = v
        note = c["note"].format(today=TODAY)
        if note[:40] not in (row.get("Notes") or ""):
            row["Notes"] = ((row.get("Notes") or "").strip() + " " + note).strip()
            changes.append("Notes appended")
        if changes:
            row["Data_As_Of"] = TODAY
        print(f"  {c['deal_id']:<16} {len(changes):2d} field(s) changed"
              if changes else f"  {c['deal_id']:<16} already applied")
        for ch in changes:
            print(f"      {ch}")
        applied["applied" if changes else "already applied"] += 1
    print()

    # ---- 3. withdrawals -----------------------------------------------------
    print("withdrawals")
    withdrawn_path = REVIEW / "deals_withdrawn_duplicates.csv"
    existing, wfields = read_csv(withdrawn_path)
    already = {(r.get("Deal_ID") or "").strip() for r in existing}
    new_withdrawn = []

    for w in WITHDRAWALS:
        rows, _ = load(w["file"])
        row = next((r for r in rows
                    if (r.get("Deal_ID") or "").strip() == w["withdraw"]), None)
        if row is None:
            print(f"  {w['withdraw']:<16} already withdrawn (not in ledger)")
            continue

        survivor = find(w["keep_file"], w["keep"])
        if survivor is None:
            print(f"  {w['withdraw']:<16} SURVIVOR {w['keep']} NOT FOUND "
                  f"- refusing to withdraw")
            continue

        # Move the withdrawn row's own source onto the survivor so no
        # retrieved evidence is lost by the withdrawal.
        if w["carry_source"] and w["carry_source"] not in \
                " ".join(str(v) for v in survivor.values()):
            slot = "Source_2" if not (survivor.get("Source_2") or "").strip() \
                else None
            if slot:
                survivor[slot] = w["carry_source"]
                survivor[slot + "_Type"] = w["carry_source_type"]
                print(f"  {w['keep']:<16} carried source into {slot}")
            else:
                survivor["Notes"] = (survivor.get("Notes", "") +
                                     f" Corroborating source from the "
                                     f"withdrawn {w['withdraw']}: "
                                     f"{w['carry_source']}").strip()

        marker = f"RECONCILED {TODAY}: duplicate {w['withdraw']} withdrawn"
        if marker[:30] not in (survivor.get("Notes") or ""):
            survivor["Notes"] = ((survivor.get("Notes") or "").strip() + " " +
                                 marker + f" ({w['lead']}); see "
                                 f"review/deals_withdrawn_duplicates.csv and "
                                 f"the dating rule in docs/datasets/01_deals.md."
                                 ).strip()
            survivor["Data_As_Of"] = TODAY

        rows.remove(row)
        rec = dict(row)
        rec["_withdrawn_date"] = TODAY
        rec["_withdrawn_from_file"] = Path(w["file"]).name
        rec["_superseded_by_deal_id"] = w["keep"]
        rec["_superseded_by_file"] = Path(w["keep_file"]).name
        rec["_reason"] = w["reason"]
        rec["_evidence_lead"] = w["lead"]
        new_withdrawn.append(rec)
        print(f"  {w['withdraw']:<16} withdrawn -> kept {w['keep']}")

    if new_withdrawn:
        keep = [r for r in existing
                if (r.get("Deal_ID") or "").strip() not in
                {x["Deal_ID"] for x in new_withdrawn}]
        allw = keep + new_withdrawn
        fields = list(new_withdrawn[0].keys())
        for r in allw:
            for k in r:
                if k not in fields:
                    fields.append(k)
        write_csv(withdrawn_path, allw, fields)
        print(f"  wrote {withdrawn_path.relative_to(CEDAR)} "
              f"({len(allw)} rows)")
    print()

    # ---- 4. flush every ledger we touched ----------------------------------
    for p, (rows, fields) in touched.items():
        bak = p.with_suffix(f".csv.bak_{TODAY}_pre54")
        if not bak.exists():
            shutil.copy2(p, bak)
        write_csv(p, rows, fields)
        print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")
    print()

    # ---- 5. duplicate scan --------------------------------------------------
    rows = []
    for f in ledger_files():
        rs, _ = read_csv(f)
        for r in rs:
            r["_file"] = f.name
            rows.append(r)
    print(f"scanning {len(rows):,} deal rows across {len(ledger_files())} files")

    cp_freq = Counter(norm(r.get("Counterparty_or_Funder")) for r in rows)
    tok_freq = Counter()
    for r in rows:
        for t in ident(r.get("Native_Party")):
            tok_freq[t] += 1

    blocks = defaultdict(list)
    for r in rows:
        for t in ident(r.get("Native_Party")):
            # A token carried by a third of the ledger is not a party name.
            if tok_freq[t] <= 120:
                blocks[t].append(r)

    cands = {}
    for grp in blocks.values():
        for a, b in itertools.combinations(grp, 2):
            key = tuple(sorted(((a.get("Deal_ID") or ""),
                                (b.get("Deal_ID") or ""))))
            if key in cands or key[0] == key[1]:
                continue
            ia, ib = ident(a.get("Native_Party")), ident(b.get("Native_Party"))
            if not (ia <= ib or ib <= ia or jac(ia, ib) >= 0.7):
                continue

            ca = core(a.get("Counterparty_or_Funder"))
            cb = core(b.get("Counterparty_or_Funder"))
            cp_match = bool(ca and cb) and (jac(ca, cb) >= 0.6
                                            or ca <= cb or cb <= ca)
            federal = cp_freq[norm(a.get("Counterparty_or_Funder"))] >= 5

            da, db = parse_date(a), parse_date(b)
            dd = abs((da - db).days) if da and db else None
            va, vb = parse_value(a), parse_value(b)
            v_match = (va is not None and vb is not None
                       and abs(va - vb) <= max(1.0, 0.02 * max(va, vb)))
            t_match = norm(a.get("Deal_Title")) == norm(b.get("Deal_Title"))
            title_sim = jac(core(a.get("Deal_Title")), core(b.get("Deal_Title")))

            why = None
            if t_match:
                why = "identical Deal_Title"
            elif cp_match and not federal and dd is not None and dd <= 180:
                why = "same party, same counterparty, dates within 180 days"
            elif (cp_match and not federal and dd is None
                  and a.get("Event_Year") == b.get("Event_Year")):
                why = ("same party, same counterparty, same year, "
                       "one row has no date")
            elif cp_match and federal and v_match and dd is not None and dd <= 31:
                why = ("same party, same federal funder, same amount, "
                       "dates within 31 days")
            elif (v_match and not cp_match and dd is not None and dd <= 60
                  and title_sim >= 0.5):
                why = ("same party, same amount, dates within 60 days, "
                       "counterparty text differs")
            if not why:
                continue

            cands[key] = {
                "deal_id_a": a.get("Deal_ID"), "file_a": a["_file"],
                "date_a": a.get("Event_Date"), "party_a": a.get("Native_Party"),
                "counterparty_a": a.get("Counterparty_or_Funder"),
                "value_a": a.get("Announced_Value_USD"),
                "title_a": a.get("Deal_Title"),
                "source_a": a.get("Source_1"),
                "deal_id_b": b.get("Deal_ID"), "file_b": b["_file"],
                "date_b": b.get("Event_Date"), "party_b": b.get("Native_Party"),
                "counterparty_b": b.get("Counterparty_or_Funder"),
                "value_b": b.get("Announced_Value_USD"),
                "title_b": b.get("Deal_Title"),
                "source_b": b.get("Source_1"),
                "date_diff_days": "" if dd is None else dd,
                "value_match": int(v_match),
                "same_file": int(a["_file"] == b["_file"]),
                "counterparty_is_federal_program": int(federal),
                "why_flagged": why,
                "YOUR_RULING": "",
                "YOUR_NOTE": "",
            }

    out = sorted(cands.values(),
                 key=lambda r: (r["counterparty_is_federal_program"],
                                str(r["date_diff_days"]).rjust(6)))
    write_csv(REVIEW / "deals_duplicate_candidates.csv", out, list(out[0].keys()))
    print(f"  wrote review/deals_duplicate_candidates.csv  ({len(out)} pairs)"
          f"  <- REPORTED, NOT MERGED")

    print("\ncandidate pairs")
    for r in out:
        print(f"  {r['deal_id_a']:>16} | {r['deal_id_b']:<17} "
              f"dd={str(r['date_diff_days']):>5}  {r['why_flagged'][:48]}")


if __name__ == "__main__":
    main()
