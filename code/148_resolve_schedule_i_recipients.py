#!/usr/bin/env python3
"""
Cedar Press - 145: resolve Form 990 Schedule I grant recipients to the spine.

THE GAP
-------
`np_schedule_i_grants.csv` holds 58,685 named grant recipients. Only **2,442
(4%)** carry a `recipient_entity_id`. 55,522 (95%) carry an EIN. The unresolved
mass is where Native-entity grant relationships are hiding.

WHAT THIS IS NOT
----------------
Most recipients are ordinary charities - Johns Hopkins, Mayo Clinic, New Venture
Fund - present only because a Native funder gave to them. **The goal is not to
resolve everything.** It is to find the Native recipients and leave the rest
alone, because a false positive here manufactures a Native grant relationship
that does not exist.

THE GUARDS, all measured today
------------------------------
1. **Containment must rest on a token unique to ONE spine entity.** "DENVER
   INDIAN HEALTH & FAMILY SERVICES" matched the spine entity "Native Health" at
   85% on the shared word "health" - 6 characters, so a length test passed it,
   and generic enough to appear in hundreds of names.
2. **NAME_TRAPS applies to the token path too.** Blocking containment alone just
   pushes the same bad match down one level - measured: "Boys & Girls Clubs of
   Wichita Falls" still hit the Wichita Tribe at 70% after the containment fix.
3. **A tribe name followed by a place suffix is a PLACE.** Wichita Falls is a
   city in Texas.
4. **An EIN match beats every name match** and is the only tier that resolves
   without a name heuristic at all.

WHAT IT REFUSES
---------------
- **Writes a PROPOSAL file. Does not touch `np_schedule_i_grants.csv`.** That
  file is rebuilt by script 132 from its own inputs; appended columns would be
  silently destroyed on the next run - the `09_import_rulings.py` failure shape.
- **Never treats a grant as evidence of purpose.** A Schedule I row proves money
  moved. It does not prove what the money paid for.
- **Never promotes `np_orgs` membership to a Native ruling.** Script 132 already
  learned this the hard way: its first cut reported "$1.01B of Native
  grantmaking" whose top grantmaker was SEMINOLE BOOSTERS INC - Florida State
  athletics, already ruled tier X.
- **Never inherits a ruling's AUTHORITY without reading its SIGN.** See the
  fix note below.

DEFECT FIXED 2026-08-26 - A RULED METHOD IS NOT A POSITIVE RULING
-----------------------------------------------------------------
The EIN index used to read `tier = "A" if meth in RULED else ...`. Every one
of the ledger's 317 `elijah_ruling` EIN rows is **tier X - a NEGATIVE ruling**,
and not one EIN row in the ledger is tier A. The line therefore turned 317
exclusions into publishable positive attributions (COLVILLE ROTARY ->
Confederated Colville at tier A, and 316 more).

The tier is now inherited verbatim and a tier-X row is loaded as an EXCLUSION
on the (EIN, entity) pair - blocking the EIN path AND the two name paths for
that entity, because blocking one bad-match path only pushes it to the next.
It is not a blanket block on the EIN: the ruling says this EIN is not THAT
entity and says nothing about any other, and over-blocking would suppress a
correct attribution. Refusals are written to
`review/schedule_i_recipient_ruling_refusals_<date>.csv`.

The proposals in `review/np_schedule_i_recipients_2026-08-12.csv` predate this
fix and must not be applied. Re-run this script and use its output instead.

    py -3 code/145_resolve_schedule_i_recipients.py --check
    py -3 code/145_resolve_schedule_i_recipients.py
"""

import csv
import importlib.util
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
SRC = CLEAN / "np_schedule_i_grants.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

SHORT_OK = {"zuni", "hopi", "crow", "ute", "sac", "fox", "yurok", "hoopa",
            "makah", "lummi", "quinault", "tlingit", "haida", "aleut",
            "inupiat", "koniag", "chugach", "doyon", "calista", "ahtna",
            "sealaska"}
STOP = {"the", "of", "and", "inc", "incorporated", "llc", "corporation",
        "company", "corp", "ltd", "limited", "tribe", "tribal", "nation",
        "native", "indian", "alaska", "alaskan", "village", "community",
        "band", "pueblo", "council", "group", "services", "service", "center",
        "centre", "foundation", "institute", "association", "society",
        "enterprises", "enterprise", "holdings", "health", "housing",
        "authority", "school", "college", "university", "fund", "trust",
        "development", "management", "program", "programs", "project",
        "america", "american", "united", "national", "regional", "county",
        "state", "city", "north", "south", "east", "west", "new"}
PLACE_SUFFIXES = {"falls", "city", "county", "springs", "heights", "valley",
                  "park", "beach", "ridge", "lake", "lakes", "river", "hills",
                  "junction", "township", "borough", "village", "plains",
                  "bay", "harbor", "island"}


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def main():
    check = "--check" in sys.argv
    print("=== 145: resolve Schedule I recipients ===\n")

    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m33 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m33)
    dspec = importlib.util.spec_from_file_location(
        "cedar_domain", CEDAR / "code" / "cedar_domain.py")
    dom = importlib.util.module_from_spec(dspec)
    dspec.loader.exec_module(dom)
    TRAPS = dom.NAME_TRAPS

    spine = load(SPINE)
    ledger = load(CLEAN / "cedar_identifier_ledger_final.csv")

    # EIN -> entity. An EIN match is only as good as the row that carries it.
    #
    # MEASURED 2026-08-12, and this was my bug: the first version treated ANY
    # ledger EIN hit as tier A. But 873 of 1,104 EIN rows sit on 52 entities
    # carrying 5+ EINs each (Onondaga 38, Rosebud 38, Apache Tribe of Oklahoma
    # 36), and 821 of those are tier B via `need_v6` - a method cedar_domain
    # documents as "6.5% accurate against rulings - never publishes alone".
    #
    # The ledger was behaving correctly; weak matches sat at B and did not
    # publish. Promoting them to A on my side laundered them. Concretely it
    # produced UNITED WAY OF THE GREATER CHIPPEWA VALLEY (EIN 39-1077901,
    # Wisconsin) -> United Auburn Indian Community (California) at tier A.
    #
    # So the EIN tier is INHERITED from the ledger row.
    #
    # (This comment used to end "...and only a RULED method earns A". That
    # clause was the bug, and it is corrected immediately below.)
    #
    # ------------------------------------------------------------------
    # DEFECT FIXED 2026-08-26 (code/248_audit_tier_inheritance_patterns.py).
    # The comment above was right and the LINE UNDER IT WAS WRONG. It read:
    #
    #     tier = "A" if meth in RULED else (r.get("confidence_tier") or "B")
    #
    # **A RULED METHOD IS NOT AUTOMATICALLY A POSITIVE RULING.**
    #
    # `elijah_ruling` is in RULED because a human made the decision. It says
    # WHO decided, never WHAT was decided. Measured on this ledger 2026-08-26:
    #
    #     EIN rows                    1,104
    #     ...tier A                       0
    #     ...`elijah_ruling`            317, **EVERY ONE OF THEM TIER X**
    #
    # Tier X is a NEGATIVE ruling - "this EIN is NOT that entity". The line
    # above turned all 317 exclusions into confident positive attributions at
    # the project's only publishable tier. Live examples it produced:
    #
    #     COLVILLE ROTARY CHARITABLE FOUNDATION -> Confederated Colville   [A]
    #     KIOWA COUNTY FARM BUREAU ASSOCIATION  -> Kiowa Tribe             [A]
    #     COWLITZ COUNTY DIVE RESCUE ASSOCIATION-> Cowlitz                 [A]
    #
    # This is the second half of the United Way lesson AGENTS.md already
    # carries. The first half is "a tier is INHERITED from the source row,
    # never assigned by the consumer". The second half is: **before you
    # inherit a ruling's authority, read the ruling's SIGN.** The same trap
    # bit the ANCSA pass on a different column the same day - it read
    # `status = SETTLED` as confirmation when the `outcome` was
    # `HOLD_OVER_OWNER` / "HOLD - RETRACTION REQUIRED".
    # **`status` says the ruling was PROCESSED; `outcome` says what it DECIDED.**
    #
    # WHAT REPLACES IT
    #   1. The tier is inherited verbatim. Nothing is minted here, ever.
    #   2. A tier-X row is loaded as an EXCLUSION on (EIN -> that tribe_id),
    #      never as a link. It also blocks the NAME path from re-proposing the
    #      same entity for the same organisation, because blocking one
    #      bad-match path only pushes it to the next one (AGENTS.md).
    #   3. It is NOT a blanket block on the EIN. The ruling says this EIN is
    #      not THAT entity; it says nothing about any other entity, and
    #      over-blocking would suppress a correct attribution - the same
    #      reason 169_build_identifier_graph.py's node-level X block means
    #      corrections are repointed, not blacklisted.
    #   4. Among positive rows on one EIN, a better tier wins, and at equal
    #      tier a RULED method wins. Neither comparison can create an A.
    # ------------------------------------------------------------------
    RULED = {"hand", "bgov_manual", "elijah_ruling", "elijah_ruling_redirect",
             "ruling", "web_verified"}
    TIER_RANK = {"A": 3, "B": 2, "C": 1}      # X is not on this scale at all
    by_ein = {}
    ein_excluded = defaultdict(dict)          # ein -> {tribe_id: rationale}
    n_excl_rows = 0
    for r in ledger:
        if (r.get("identifier_type") or "").upper() != "EIN":
            continue
        v = re.sub(r"\D", "", r.get("identifier") or "")
        if not (v and r.get("tribe_id")):
            continue
        meth = (r.get("attribution_method") or "").strip()
        tier = (r.get("confidence_tier") or "").strip().upper() or "B"

        if tier == "X":
            # A NEGATIVE ruling. It never becomes a link, at any tier.
            ein_excluded[v][r["tribe_id"]] = (
                f"ledger EIN row is tier X via '{meth}' - a NEGATIVE ruling: "
                f"{(r.get('tier_rationale') or '').strip()[:180]}")
            n_excl_rows += 1
            continue

        prev = by_ein.get(v)
        better = (prev is None
                  or TIER_RANK.get(tier, 0) > TIER_RANK.get(prev[2], 0)
                  or (TIER_RANK.get(tier, 0) == TIER_RANK.get(prev[2], 0)
                      and meth in RULED and prev[3] not in RULED))
        if better:
            by_ein[v] = (r["tribe_id"], r.get("canonical_name", ""), tier, meth)

    # tokens appearing in exactly ONE spine entity
    tok = defaultdict(list)
    for r in spine:
        for w in norm(r.get("canonical_name")).split():
            if w in STOP or (len(w) < 5 and w not in SHORT_OK):
                continue
            tok[w].append(r)
    tok = {k: v[0] for k, v in tok.items() if len(v) == 1}
    print(f"  spine entities            : {len(spine):,}")
    print(f"  EINs in ledger (positive) : {len(by_ein):,}")
    print(f"  EINs carrying an EXCLUSION: {len(ein_excluded):,} "
          f"({n_excl_rows:,} tier-X ledger rows, NOT promoted)")
    print(f"  spine tokens unique to one: {len(tok):,}")

    rows = load(SRC)

    # THE DOLLAR COLUMN DOES NOT EXIST, AND THE ZERO LOOKED LIKE A FACT.
    # Found 2026-08-26 while fixing the tier bug. This script summed
    # `cash_grant_amount` or `total_cash_grant_usd`; `np_schedule_i_grants.csv`
    # carries NEITHER. The real column is `cash_grant_usd`. Every proposal
    # therefore carried $0.00, the run printed "dollars represented: $0.0M",
    # and `props.sort(key=-total_cash_grant_usd)` sorted a review queue of
    # 5,746 rows by a constant - so the biggest grant relationships were not at
    # the top and nothing said so.
    #
    # AGENTS.md standing rule 8: "An absent column name reads as an empty
    # source... A coverage computation must RAISE on a missing column, never
    # print a zero." Script 102 printed 0.0% coverage for 19 days on exactly
    # this shape. So this RAISES rather than falling back.
    AMOUNT_COL = "cash_grant_usd"
    if rows and AMOUNT_COL not in rows[0]:
        raise SystemExit(
            f"REFUSING: {SRC.name} has no column {AMOUNT_COL!r}. Its dollar "
            f"column has been renamed. Fix AMOUNT_COL - do NOT let it fall "
            f"back to 0, which is what produced a $0.0M review queue sorted "
            f"by a constant. Columns present: {sorted(rows[0])[:12]}...")

    # distinct recipients, aggregated
    rec = defaultdict(lambda: {"rows": 0, "usd": 0.0, "ein": "", "state": "",
                               "funders": set(), "years": set(),
                               "already": "", "already_name": ""})
    for r in rows:
        nm = (r.get("recipient_name_as_filed") or "").strip()
        if not nm:
            continue
        e = rec[nm]
        e["rows"] += 1
        try:
            e["usd"] += float(r.get(AMOUNT_COL) or 0)
        except ValueError:
            pass
        e["ein"] = e["ein"] or re.sub(r"\D", "", r.get("recipient_ein") or "")
        e["state"] = e["state"] or (r.get("recipient_state") or "")
        f = (r.get("filer_name_as_filed") or "").strip()
        if f:
            e["funders"].add(f)
        y = (r.get("tax_year") or "").strip()
        if y:
            e["years"].add(y)
        if (r.get("recipient_entity_id") or "").strip():
            e["already"] = r["recipient_entity_id"]
            e["already_name"] = r.get("recipient_entity_canonical_name", "")
    print(f"  grant rows                : {len(rows):,}")
    print(f"  distinct recipients       : {len(rec):,}")

    props, refusals, stats = [], [], Counter()
    for nm, e in rec.items():
        if e["already"]:
            stats["already resolved"] += 1
            continue
        tid = cname = basis = ""
        tier = ""
        # Entities an owner ruling forbids for THIS EIN. Empty for almost all.
        forbidden = ein_excluded.get(e["ein"], {}) if e["ein"] else {}

        def refuse(bad_tid, bad_name, path):
            refusals.append({
                "recipient_name_as_filed": nm,
                "recipient_ein": e["ein"],
                "recipient_state": e["state"],
                "refused_entity_id": bad_tid,
                "refused_canonical_name": bad_name,
                "refused_via_path": path,
                "ruling": forbidden.get(bad_tid, ""),
                "n_grant_rows": e["rows"],
                "total_cash_grant_usd": round(e["usd"], 2),
                "note": "A tier-X ledger row is a NEGATIVE ruling on this "
                        "(EIN, entity) pair. It is not a weak link and it is "
                        "not a missing value. Only a NEW ruling reverses it. "
                        "Other entities are NOT blocked on this EIN.",
                "built_date": TODAY,
            })

        # 1. EIN - strongest, no heuristic. Tier INHERITED, sign CHECKED.
        if e["ein"] and e["ein"] in by_ein:
            ltid, lname, ltier, lmeth = by_ein[e["ein"]]
            if ltid in forbidden:
                # One EIN carrying both a positive row and a negative ruling
                # that names the same entity. The ruling wins - that is what a
                # ruling is for.
                refuse(ltid, lname, "EIN")
                stats["EIN REFUSED - an owner ruling forbids this entity"] += 1
                continue
            tid, cname, tier = ltid, lname, ltier
            basis = (f"EIN matches a ledger row carrying method '{lmeth}' "
                     f"at tier {ltier} - INHERITED, not promoted")
            stats[f"EIN match -> {ltier} ({lmeth})"] += 1
        else:
            if forbidden:
                stats["EIN carries ONLY exclusions - name path, ruled "
                      "entity barred"] += 1
            words = norm(nm).split()
            # 2. shared resolver, but refuse weak containment
            rid, rname, how = m33.resolve_entity(nm, spine)
            weak = False
            if rid and "contain" in (how or "").lower():
                shared = (set(norm(rname).split()) & set(words))
                good = [w for w in shared
                        if w not in STOP and (len(w) >= 5 or w in SHORT_OK)]
                weak = not any(w in tok for w in good)
            if rid and rid in forbidden:
                # BLOCKING ONE PATH PUSHES THE MATCH TO THE NEXT ONE.
                # COLVILLE ROTARY is ruled X against Confederated Colville on
                # its EIN; the name path would hand back the same answer
                # through a different door. The ruling is about the pair, not
                # about the key that carried it.
                refuse(rid, rname, "name/resolver")
                stats["name REFUSED - an owner ruling forbids this entity"] += 1
                continue
            if rid and not weak:
                tid, cname = rid, rname
                basis, tier = f"spine resolver ({how})", "B"
                stats["resolver -> B"] += 1
            else:
                # 3. distinctive-token path, honouring traps and place suffixes
                hit = None
                for i, w in enumerate(words):
                    if w not in tok or w in TRAPS:
                        continue
                    if i + 1 < len(words) and words[i + 1] in PLACE_SUFFIXES:
                        continue
                    hit = tok[w]
                    break
                if hit and hit["tribe_id"] in forbidden:
                    refuse(hit["tribe_id"], hit["canonical_name"], "token")
                    stats["token REFUSED - an owner ruling forbids this "
                          "entity"] += 1
                    continue
                if hit:
                    tid, cname = hit["tribe_id"], hit["canonical_name"]
                    basis, tier = "distinctive spine token in the name", "B"
                    stats["token -> B"] += 1
                else:
                    stats["no candidate"] += 1
                    continue
        props.append({
            "recipient_name_as_filed": nm,
            "recipient_ein": e["ein"],
            "recipient_state": e["state"],
            "proposed_entity_id": tid,
            "proposed_canonical_name": cname,
            "match_basis": basis,
            "confidence_tier": tier,
            "n_grant_rows": e["rows"],
            "total_cash_grant_usd": round(e["usd"], 2),
            "n_funders": len(e["funders"]),
            "funders": "; ".join(sorted(e["funders"])[:3]),
            "tax_years": "; ".join(sorted(e["years"])),
            "caveat": "A Schedule I row proves money moved. It does NOT prove "
                      "what the money paid for, and does not make the recipient "
                      "Native - that is the ruling being requested.",
            "built_date": TODAY,
        })

    props.sort(key=lambda r: -r["total_cash_grant_usd"])
    refusals.sort(key=lambda r: -r["total_cash_grant_usd"])
    print("\n[outcomes]")
    for k, v in stats.most_common():
        print(f"  {k:56s} {v:>6,}")
    a = [p for p in props if p["confidence_tier"] == "A"]
    print(f"\n  proposals: {len(props):,}  (tier A {len(a)}, "
          f"other {len(props)-len(a)})")
    print(f"  dollars represented: ${sum(p['total_cash_grant_usd'] for p in props)/1e6:,.1f}M")
    print(f"  REFUSED by an owner ruling: {len(refusals):,} "
          f"(${sum(r['total_cash_grant_usd'] for r in refusals)/1e6:,.1f}M)")
    if not a:
        print("  NOTE: zero tier-A proposals is the CORRECT state today - not "
              "one EIN row in the ledger is tier A (measured: 1,104 rows, "
              "A=0). A tier-A proposal here would have to come from a tier-A "
              "source row.")

    if check:
        print("\n  --check: nothing written")
        for p in props[:12]:
            print(f"    ${p['total_cash_grant_usd']/1e6:>8.2f}M  "
                  f"{p['recipient_name_as_filed'][:42]:42s} -> "
                  f"{p['proposed_canonical_name'][:30]}  [{p['confidence_tier']}]")
        for r in refusals[:8]:
            print(f"    REFUSED  {r['recipient_name_as_filed'][:42]:42s} -x- "
                  f"{r['refused_canonical_name'][:30]} ({r['refused_via_path']})")
        return

    def write(dest, data):
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
        tmp.replace(dest)
        print(f"  wrote {dest.relative_to(CEDAR)} ({len(data):,} rows)")

    print()
    if props:
        write(REVIEW / f"schedule_i_recipient_resolution_{TODAY}.csv", props)
    if refusals:
        write(REVIEW / f"schedule_i_recipient_ruling_refusals_{TODAY}.csv",
              refusals)
    print("  np_schedule_i_grants.csv NOT modified")


if __name__ == "__main__":
    main()
