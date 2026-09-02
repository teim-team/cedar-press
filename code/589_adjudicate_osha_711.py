#!/usr/bin/env python3
"""
Cedar Press - 586: adjudicate the 711 held OSHA ITA establishments.
WORKSTREAM INT-1 (LABOR).  NO NETWORK - every signal used here is on disk.

THE HOLD FILE, AND WHY ITS HEADLINE IS STALE
--------------------------------------------
`review/employment_osha_unmatched_2026-08-07.csv` holds **711 establishments /
1,879 Form 300A filings**, `YOUR_RULING` blank on all 711.  Every one was held
for the same stated reason: *"shares a distinctive token with a Cedar property
but no exact name+state match."*  Pearl River Resort, Choctaw MS, 3,233
employees, on the token `pearl`.

**That reason is exactly the defect `docs/ENTITY_MATCH_RULES.md` was written to
stop, and holding on it was right.**  A shared token is never evidence.  `pearl`
is not why Pearl River Resort belongs to the Mississippi Band of Choctaw
Indians; the filing saying "Mississippi Band of Choctaw Indinas" is.

But the file is a snapshot from 2026-08-07 and two later passes have moved
under it.  Measured today against `data/clean/` and the 2026-08-26 hold file:

     66 of 711  are ALREADY IN gaming_employment_observations.csv
    344 of 711  were ruled `blocked_commercial` by 157 on 2026-08-26
    301 of 711  are genuinely still open, carrying 720 filings

So the real backlog is 301 establishments, not 711, and 720 filings, not 1,879.
Only the 301 are adjudicated here.

THE EVIDENCE LADDER, STRONGEST FIRST
------------------------------------
`ENTITY_MATCH_RULES.md` rule 4: *an identifier beats every name method*, and a
weak match needs a second independent signal.  The ITA 300A record carries
street address and ZIP on 100% of rows and an EIN on 3,475 of 5,062, none of
which the 2026-08-07 pass used.  That is the corroboration the hold was waiting
for, and it was on disk the whole time.

  A1  EIN  - the filing's EIN is an EIN Cedar already attributes to an entity
             in `data/spine/cedar_identifier_ledger.csv`. An identifier, so it
             stands alone.
  A2  ADDRESS - normalised street number+name AND ZIP both match one
             `gaming_facilities.csv` row. Two independent geographic signals
             agreeing on one property; this one can carry a `facility_id`.
  A3  ZIP  - the filing's ZIP is the ZIP of a Cedar gaming facility belonging to
             exactly one tribe, AND the city agrees. A casino ZIP is specific;
             requiring one tribe is what stops a Las Vegas ZIP resolving.
  A4  GOVERNMENT NAMED - every distinctive token of a spine entity's name is in
             the filing, the filing carries a governmental word, the state
             agrees, and no other spine entity in that state matches.
  A5  CEDAR FACILITY BRAND - the filed name carries the same distinctive tokens
             as a `gaming_facilities.facility_name` for exactly one tribe in
             that state. Cedar's own curated table, the same pass-B evidence
             157 used for 345 of its 502 rows.

**A shared token corroborates nothing and is never a rule here.**  Anything the
ladder does not reach stays `unresolved`, which ADR-010 makes an honest record
scope.  A wrong attribution is worse than no attribution, and 3,233 employees
on the wrong tribe is a customer-facing error.

Two guards, both carried over from 583 where each caught a live false positive:
`entity_class` must be one that actually owns a row in `gaming_facilities.csv`
(otherwise *Yakama Nation Legends Casino Hotel* goes to the Yakama Nation
tribal SCHOOL), and a national brand match needs a governmental word (otherwise
*Double Eagle Hotel & Casino*, Cripple Creek CO, goes to the Spokane Tribe).

usage:
    py -3 code/589_adjudicate_osha_711.py            # measure, write review
    py -3 code/589_adjudicate_osha_711.py --apply    # + promote
"""
import csv
import re
import sys
import shutil
import hashlib
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
REVIEW = ROOT / "review"

EMP = CLEAN / "gaming_employment_observations.csv"
FACS = CLEAN / "gaming_facilities.csv"
SPINE_F = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
LEDGER = ROOT / "data" / "spine" / "cedar_identifier_ledger.csv"
HELD711 = REVIEW / "employment_osha_unmatched_2026-08-07.csv"
HOLDS826 = REVIEW / "osha_gambling_unresolved_2026-08-26.csv"
POOL = ROOT / "data" / "raw" / "external" / "osha_ita" / "_gambling_naics_rows.csv"

TODAY = "2026-09-01"
BY = "589_adjudicate_osha_711.py"

GOV_WORDS = set(
    "tribe tribes tribal nation nations band bands pueblo rancheria community "
    "indians indian village villages nsn reservation keetoowah".split())
NOISE = set(
    "of the and a in at for inc llc l p lp corp corporation co ltd dba d b "
    "casino casinos resort resorts hotel hotels gaming game games enterprise "
    "enterprises authority board group holdings development commission plan "
    "benefit employees employee retirement welfare savings trust k 401 bingo "
    "travel plaza center centre lodge spa".split())
CAN_OWN_A_CASINO = {
    "Federally recognized tribe",
    "Federal-level constituency entity",
    "Federally recognized Alaska Native Village",
}
# Street-type words. Dropped before comparing addresses so "2655 Everett
# Freeman Way" and "2655 Everett Freeman Wy" are the same address, while the
# house number - the part that actually identifies the site - is kept.
STREET = set("st street ave avenue rd road dr drive blvd boulevard way wy ln "
             "lane hwy highway route rt pkwy parkway ct court cir circle pl "
             "place ste suite n s e w north south east west".split())


def rd(p):
    with open(p, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def wr(p, rows, fields=None):
    if not rows:
        return 0
    fields = fields or list(rows[0].keys())
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def distinctive(s):
    return set(norm(s).split()) - NOISE - GOV_WORDS


def addr_key(s):
    t = [w for w in norm(s).split() if w not in STREET]
    return " ".join(t)


def zip5(s):
    d = re.sub(r"[^0-9]", "", s or "")
    return d[:5] if len(d) >= 5 else ""


def ein9(s):
    d = re.sub(r"[^0-9]", "", s or "")
    return d.zfill(9) if 0 < len(d) <= 9 else ""


def obs_id(r):
    """Stable id derived from the row, never from a counter (class 7)."""
    key = "|".join((r["establishment_name"].strip().lower(),
                    (r.get("company_name") or "").strip().lower(),
                    r["state"], r["year_filing_for"],
                    str(r["annual_average_employees"])))
    return "EMP-OSHATRIBE-B" + hashlib.sha1(
        key.encode("utf-8")).hexdigest()[:10].upper()


OSHA_NOTE = (
    "The ESTABLISHMENT'S OWN FILED annual average employees, rolled to the "
    "tribe that owns it. It is a headcount, not an FTE and not a payroll. OSHA "
    "ITA coverage is NOT a census: electronic submission is required only of "
    "establishments above size thresholds in covered industries, and compliance "
    "is uneven. AN ESTABLISHMENT ABSENT FROM ITA IS NOT AN ESTABLISHMENT WITH "
    "ZERO EMPLOYEES - it is an establishment that did not file. The set of "
    "establishments filing under one tribe CHANGES YEAR TO YEAR, so a tribe-year "
    "SUM of these rows is not a consistent panel and must never be differenced "
    "as if it were.")


def main():
    apply = "--apply" in sys.argv
    emp = rd(EMP)
    facs = rd(FACS)
    spine = {r["tribe_id"]: r for r in rd(SPINE_F)}
    pool = rd(POOL)

    # ---------------- triage the 711 against what has happened since --------
    held = rd(HELD711)

    def k(n, s):
        return (n.strip().lower(), s)

    in_clean = {k(r["establishment_name"], r["state"]) for r in emp
                if r["establishment_name"]}
    blocked = collections.defaultdict(set)
    for h in rd(HOLDS826):
        blocked[k(h["establishment_name"], h["state"])].add(h["verdict"])

    already, commercial, still_open = [], [], []
    for r in held:
        key = k(r["establishment_name"], r["state"])
        if key in in_clean:
            already.append(r)
        elif key in blocked and blocked[key] <= {"blocked_commercial"}:
            commercial.append(r)
        else:
            still_open.append(r)

    def nf(rows):
        return sum(int(r["n_filings"] or 0) for r in rows)

    print(f"review/employment_osha_unmatched_2026-08-07.csv: {len(held)} "
          f"establishments / {nf(held):,} filings, YOUR_RULING blank on all")
    print(f"  ALREADY PROMOTED since the snapshot : {len(already):>3} "
          f"establishments / {nf(already):>4} filings")
    print(f"  RULED blocked_commercial by 157     : {len(commercial):>3} "
          f"establishments / {nf(commercial):>4} filings")
    print(f"  GENUINELY STILL OPEN                : {len(still_open):>3} "
          f"establishments / {nf(still_open):>4} filings")

    # ---------------- evidence indexes --------------------------------------
    ein_owner = {}
    for r in rd(LEDGER):
        if r["identifier_type"] != "EIN":
            continue
        e = ein9(r["identifier"])
        if e and r["tribe_id"] in spine:
            ein_owner.setdefault(e, set()).add(r["tribe_id"])

    by_addr, by_zip, brand_state, brand_any = {}, {}, {}, {}
    for f in facs:
        t = f["tribe_id"]
        if not t or spine.get(t, {}).get("entity_class") not in CAN_OWN_A_CASINO:
            continue
        a, z = addr_key(f["address"]), zip5(f["postal_code"])
        if a and z:
            by_addr.setdefault((a, z), set()).add((t, f["facility_id"]))
        if z:
            by_zip.setdefault(z, set()).add((t, norm(f["city"])))
        d = frozenset(distinctive(f["facility_name"]))
        if d:
            brand_state.setdefault((d, f["state"]), set()).add(t)
            brand_any.setdefault(d, set()).add(t)

    names = []
    for s in spine.values():
        if s["entity_class"] not in CAN_OWN_A_CASINO:
            continue
        for n in [s["canonical_name"]] + [
                a for a in (s.get("aliases") or "").split("|") if a.strip()]:
            d = distinctive(n)
            if d:
                names.append((frozenset(d), s["tribe_id"], s["state"], norm(n)))

    # ---------------- the raw filings behind the open establishments --------
    open_keys = {k(r["establishment_name"], r["state"]) for r in still_open}
    filings = [p for p in pool
               if k(p["establishment_name"], p["state"]) in open_keys]
    print(f"\n  raw 300A filings behind the {len(still_open)} open "
          f"establishments: {len(filings)}")

    def rule(p):
        """-> (tribe_id, facility_id, rule, evidence) or (None, ...)."""
        txt = norm(p["company_name"]) + " | " + norm(p["establishment_name"])
        toks = set(txt.replace("|", " ").split())
        gov = bool(toks & GOV_WORDS)

        e = ein9(p["ein"])
        if e and len(ein_owner.get(e, ())) == 1:
            t = next(iter(ein_owner[e]))
            return (t, "", "A1_ein_in_cedar_identifier_ledger",
                    f'EIN {e} is attributed to {t} in '
                    f'cedar_identifier_ledger.csv; an identifier beats every '
                    f'name method (ENTITY_MATCH_RULES rule 4)')

        a, z = addr_key(p["street_address"]), zip5(p["zip_code"])
        hit = by_addr.get((a, z)) if a and z else None
        if hit and len({t for t, _ in hit}) == 1:
            t, fid = sorted(hit)[0]
            return (t, fid, "A2_street_address_and_zip",
                    f'street "{p["street_address"]}" and ZIP {z} both match '
                    f'gaming_facilities row {fid}; two independent geographic '
                    f'signals agreeing on one property')

        # A4 and A5 run BEFORE A3. THE FILING'S OWN WORDS OUTRANK GEOGRAPHY.
        # Both orderings were tested. ZIP-first attributed
        # "HARRAH'S SOUTHERN CALIFORNIA (RINCON)", 1,400 employees, to
        # SAN PASQUAL - because ZIP 92082, Valley Center CA, holds Rincon's
        # Harrah's AND San Pasqual's Valley View - and
        # "Twenty Nine Palms Band of Mission Indians", 720 employees, to
        # AUGUSTINE, because ZIP 92236 holds both Coachella casinos. In each
        # case the establishment name PRINTS the right tribe. A ZIP is a strong
        # corroborator and a poor gate (ENTITY_MATCH_RULES, "Why state
        # agreement is not the fix either").
        named = {}
        if gov:
            for d, t, st, shown in names:
                if st == p["state"] and d <= toks:
                    if len(shown) > len(named.get(t, "")):
                        named[t] = shown
        if len(named) == 1:
            t, shown = next(iter(named.items()))
            return (t, "", "A4_filing_names_the_government",
                    f'every distinctive token of spine name "{shown}" is '
                    f'in the filing, which carries a governmental word; '
                    f'state {p["state"]} agrees and no other spine entity '
                    f'in {p["state"]} matches')
        if len(named) > 1:
            return (None, "", None,
                    "UNRESOLVED ambiguous - filing matches "
                    + ", ".join(sorted(named)))

        branded, brand_ev = set(), ""
        for fld in ("establishment_name", "company_name"):
            d = frozenset(distinctive(p[fld]))
            h = brand_state.get((d, p["state"])) if d else None
            if h and len(h) == 1:
                t = next(iter(h))
                branded.add(t)
                brand_ev = (f'{fld}="{p[fld]}" carries the same distinctive '
                            f'tokens as a gaming_facilities.facility_name for '
                            f'exactly one tribe in {p["state"]}')
        if not branded:
            # SUPERSET arm. The filer prints the brand plus a qualifier the
            # facility table does not carry: "HARRAH'S SOUTHERN CALIFORNIA
            # RINCON" against Cedar's "Harrah's Resort Southern California".
            # Requires the CONTAINED set to be the facility's, unique in state,
            # and at least two distinctive tokens, so a one-word brand can
            # never win this way.
            for fld in ("establishment_name", "company_name"):
                d = frozenset(distinctive(p[fld]))
                if len(d) < 2:
                    continue
                sup = {t for (fd, st), ts in brand_state.items()
                       if st == p["state"] and len(fd) >= 2 and fd <= d
                       for t in ts}
                if len(sup) == 1:
                    branded |= sup
                    brand_ev = (
                        f'{fld}="{p[fld]}" CONTAINS every distinctive token of '
                        f'a gaming_facilities.facility_name belonging to '
                        f'exactly one tribe in {p["state"]}, and adds only a '
                        f'qualifier')
                    break
        if len(branded) == 1:
            return (next(iter(branded)), "", "A5_cedar_facility_brand",
                    brand_ev)
        if len(branded) > 1:
            return (None, "", None,
                    "UNRESOLVED ambiguous - filed names brand to "
                    + ", ".join(sorted(branded)))

        # Every spine entity in this state the filing text could be naming,
        # WITHOUT requiring a governmental word. Used only to veto A3 below -
        # never to award a match, because a bare place-name token is exactly
        # what ENTITY_MATCH_RULES refuses.
        mentioned = {t for d, t, st, _ in names
                     if st == p["state"] and d <= toks}

        hz = by_zip.get(z) if z else None
        if hz and len({t for t, _ in hz}) == 1:
            t = sorted(hz)[0][0]
            if norm(p["city"]) in {c for _, c in hz}:
                # VETO: if the filing itself names or brands a DIFFERENT tribe,
                # geography does not get to overrule it.
                other = (set(named) | branded | mentioned) - {t}
                if other:
                    return (None, "", None,
                            f"UNRESOLVED - ZIP {z} points at {t} but the "
                            f"filing's own text names or brands "
                            f"{', '.join(sorted(other))}. The filing outranks "
                            f"the ZIP and the two disagree")
                return (t, "", "A3_zip_and_city",
                        f'ZIP {z} and city "{p["city"]}" are those of a Cedar '
                        f'gaming facility belonging to exactly one tribe, and '
                        f'nothing in the filing names a different tribe')

        return (None, "", None,
                "UNRESOLVED - no identifier, no address or ZIP match, no "
                "governmental word, no Cedar facility brand. The shared token "
                "the 2026-08-07 pass held on is NOT evidence "
                "(docs/ENTITY_MATCH_RULES.md)")

    have = {(r["establishment_name"].strip().lower(), r["state"], r["year"])
            for r in emp
            if r["measurement_type"] == "OSHA_TRIBE_LEVEL_REPORTED"}
    promoted, unresolved = [], []
    for p in filings:
        t, fid, rl, ev = rule(p)
        if not t:
            unresolved.append({**p, "adjudication": ev})
            continue
        nk = (p["establishment_name"].strip().lower(), p["state"],
              p["year_filing_for"])
        if nk in have:
            unresolved.append({**p, "adjudication":
                               "ALREADY PRESENT in "
                               "gaming_employment_observations"})
            continue
        hours = p.get("total_hours_worked") or ""
        try:
            fte = round(float(hours) / 2080.0, 1) if hours else ""
            hpe = (round(float(hours) / float(p["annual_average_employees"]))
                   if hours and float(p["annual_average_employees"]) else "")
        except (TypeError, ValueError, ZeroDivisionError):
            fte, hpe = "", ""
        promoted.append({
            "observation_id": obs_id(p),
            "facility_id": fid,
            "tribe_id": t,
            "entity_id": t,
            "entity_level": "facility" if fid else "tribe",
            "geographic_level": ("establishment" if fid
                                 else "establishment_rolled_to_tribe"),
            "year": p["year_filing_for"],
            "employment": p["annual_average_employees"],
            "measurement_type": "OSHA_TRIBE_LEVEL_REPORTED",
            "measurement_type_status": "ACTIVE in cedar_domain.MeasurementType",
            "total_hours_worked": hours,
            "fte_2080": fte,
            "fte_divisor": "2080" if hours else "",
            "fte_is_derived_not_filed": "1" if hours else "",
            "hours_per_employee": hpe,
            "hours_per_employee_plausible": (
                "1" if hpe != "" and 200 <= hpe <= 5000 else
                ("0" if hpe != "" else "")),
            "establishment_name": p["establishment_name"],
            "company_name": p["company_name"],
            "establishment_id": p.get("establishment_id", ""),
            "ein": p.get("ein", ""),
            "street_address": p.get("street_address", ""),
            "city": p.get("city", ""),
            "state": p["state"],
            "naics": p["naics_code"],
            "name_in_source": p["establishment_name"],
            "match_rule": rl,
            "matched_on_field": rl,
            "state_mismatch_flag": "0",
            "source_url": "https://www.osha.gov/itadata",
            "source_name": ("OSHA Injury Tracking Application, Form 300A "
                            "establishment summary"),
            "source_record": p.get("_file", ""),
            "source_quote": (
                f'company_name="{p["company_name"]}"; '
                f'establishment_name="{p["establishment_name"]}"; '
                f'street_address="{p.get("street_address", "")}"; '
                f'city="{p.get("city", "")}"; state="{p["state"]}"; '
                f'zip_code="{p.get("zip_code", "")}"; '
                f'ein="{p.get("ein", "")}"; '
                f'naics_code="{p["naics_code"]}"; '
                f'annual_average_employees="{p["annual_average_employees"]}"; '
                f'year_filing_for="{p["year_filing_for"]}"'),
            "measurement_note": OSHA_NOTE,
            "confidence": "high" if rl.startswith(("A1", "A2")) else "medium",
            "flags": ("TRIBE_LEVEL_ROLLUP_NOT_A_FACILITY_FIGURE;"
                      "ITA_COVERAGE_IS_NOT_A_CENSUS;"
                      "DO_NOT_SUM_ACROSS_YEARS_WITHOUT_A_BALANCED_PANEL;"
                      "ADJUDICATED_FROM_711_HOLD_2026-09-01"),
            "attribution_repair_basis": ev,
            "attribution_repaired_by": BY,
            "attribution_repair_date": TODAY,
            "fetched_date": "2026-08-07",
            "built_date": TODAY,
            "built_by_script": BY,
            "cedar_entity_name": spine.get(t, {}).get("canonical_name", ""),
            "entity_class": spine.get(t, {}).get("entity_class", ""),
        })
        have.add(nk)

    byrule = collections.Counter(p["match_rule"] for p in promoted)
    print(f"\n  PROMOTABLE: {len(promoted)} filings over "
          f"{len({p['tribe_id'] for p in promoted})} tribes")
    for kk, v in byrule.most_common():
        print(f"     {v:>4}  {kk}")
    print(f"  UNRESOLVED (honest, ADR-010): {len(unresolved)} filings over "
          f"{len({(u['establishment_name'], u['state']) for u in unresolved})} "
          f"establishments")

    # ---- the ruled file: every one of the 711 gets a written decision ------
    ruled_by_est = collections.defaultdict(list)
    for p in promoted:
        ruled_by_est[k(p["establishment_name"], p["state"])].append(p)
    unres_by_est = collections.defaultdict(list)
    for u in unresolved:
        unres_by_est[k(u["establishment_name"], u["state"])].append(u)

    out = []
    for r in held:
        key = k(r["establishment_name"], r["state"])
        if key in ruled_by_est:
            pr = ruled_by_est[key][0]
            ruling, tid, ev = "PROMOTE", pr["tribe_id"], \
                pr["attribution_repair_basis"]
        elif r in already:
            ruling, tid, ev = "ALREADY_PROMOTED", "", (
                "present in gaming_employment_observations.csv before this "
                "pass; the 2026-08-07 snapshot predates it")
        elif r in commercial:
            ruling, tid, ev = "REFUSE_COMMERCIAL", "", (
                "ruled blocked_commercial by 157 on 2026-08-26 - a commercial "
                "gambling operator, not a tribal one. NAICS 7132/721120 is the "
                "gambling industry, not the tribal gambling industry")
        elif key in unres_by_est:
            ruling, tid, ev = "UNRESOLVED", "", \
                unres_by_est[key][0]["adjudication"]
        else:
            ruling, tid, ev = "UNRESOLVED", "", (
                "no 300A filing found in the gambling-NAICS pool under this "
                "establishment name and state")
        out.append({**r, "YOUR_RULING": ruling, "ruled_tribe_id": tid,
                    "evidence": ev, "ruled_by": BY, "ruled_date": TODAY})
    wr(REVIEW / f"employment_osha_711_ruled_{TODAY}.csv", out)
    print(f"\n  -> review/employment_osha_711_ruled_{TODAY}.csv  "
          f"({len(out)} rows, YOUR_RULING filled on all)")
    print("     " + ", ".join(
        f"{v} {kk}" for kk, v in
        collections.Counter(o["YOUR_RULING"] for o in out).most_common()))

    if not apply:
        print("\nDRY RUN. Re-run with --apply to write.")
        return

    shutil.copy2(EMP, EMP.with_suffix(f".csv.bak_{TODAY}_pre586"))
    fields = list(emp[0].keys())
    rows = emp + [{f: p.get(f, "") for f in fields} for p in promoted]
    wr(EMP, rows, fields)
    print(f"\n  promoted {len(promoted)} rows; "
          f"gaming_employment_observations.csv {len(emp):,} -> {len(rows):,}")


if __name__ == "__main__":
    main()
