#!/usr/bin/env python3
"""
Cedar Press - 1099: A REGISTRATION WHOSE OWN LEGAL NAME IS ANOTHER SOVEREIGN'S
                    OFFICIAL NAME. THE HO-CHUNK COLLISION, INVERTED - AND IT IS
                    A CLASS, NOT A CASE.

    py -3 code/1099_crosstribe_legalname_audit.py            # measure + flag
    py -3 code/1099_crosstribe_legalname_audit.py verify     # exit 1 on breach
    py -3 code/1099_crosstribe_legalname_audit.py selftest   # prove verify FIRES

THE CASE THAT STARTED IT
------------------------
`cedar_identifier_ledger_final.csv` carries, at tier A, `is_authority = YES`,
and IN `cedar_publishable_identifiers.csv`:

    CAGE 3VFL3 | tribe_id TRBF-WNNBGO-00 Winnebago Tribe of Nebraska
               | legal_business_name  "Ho-Chunk Nation"
               | state                WI
               | attribution_method   bgov_manual

`TRBF-HOCHNK-00` is the **Ho-Chunk Nation of Wisconsin**, `state = WI`, a
separate federally recognized tribe. So Cedar publishes a Wisconsin registration
named for the Wisconsin nation as belonging to the Nebraska nation.

The source row settles it without a single network request
(`entity_crosswalk_bgov.csv`, XW-0729):

    Tribe (as in BGOV file)  Winnebago Tribe of Nebraska
    Performing_Vendor        Ho-Chunk Nation
    Vendor_States            Wisconsin          <- the ONLY Wisconsin row among
    Subsidiary_Flag          1                     the 27 Winnebago rows; every
                                                   other one reads Nebraska

`ENTITY_MATCH_RULES` rule 13 rung 1 is the address, and it answers on its own.

AND THE STRUCTURAL ARGUMENT, WHICH IS THE ONE WORTH KEEPING
------------------------------------------------------------
`Subsidiary_Flag = 1` says the Ho-Chunk Nation is a subsidiary of the Winnebago
Tribe. **A federally recognized tribe cannot be a subsidiary of another
federally recognized tribe.** That is the same shape as
`cedar_domain.village_government_owns_an_anc()` - always False - and it means
this class can be detected without knowing anything about either nation.

The direction already fixed is the other one: `Ho-Chunk, Inc.` IS the Winnebago
Tribe's holding company and is correctly keyed to Winnebago, and 21
`prime_contracts` rows were moved there on `recipient_city_name = WINNEBAGO`.
**`Inc` is the whole discriminator**, so this detector must NOT strip company
forms - the naive `norm()` that folds `Ho-Chunk, Inc.` into `Ho-Chunk` finds the
CORRECT rows and misses this one. A government's official name never carries a
legal form; a firm's always does.

THE PREDICATE - structural, then corroborated. No denylist.
-----------------------------------------------------------
A ledger row is a candidate when ALL of:

  1. `tribe_id` resolves to a GOVERNMENT-class spine entity (federally
     recognized tribe, state-recognized tribe, or federally recognized Alaska
     Native Village);
  2. `legal_business_name` carries **no legal-form token** - it does not present
     as a firm. This is the Ho-Chunk Inc discriminator and it is the reason the
     detector does not fire on the correct rows;
  3. every distinctive token of `legal_business_name` is accounted for by the
     official names of some OTHER government-class entity, with an empty residue
     (`ENTITY_MATCH_RULES` rule 7) - `canonical_name`, `fr_official_name` and
     `aliases`, unioned;
  4. that other entity is UNIQUE. A name reaching two governments resolves to
     neither (rule 13: a token match on `Cherokee` is not weak evidence, it is
     no evidence).

Then each candidate is DISPOSED on the owner's own ladder, and the ladder is
recorded on the row rather than collapsed into a verdict:

    rung 1  the registration state equals the OTHER entity's state and differs
            from the keyed entity's  ->  STATE_CONTRADICTS_KEYED_ENTITY
    rung 1  the two entities share a state; the address cannot separate them
            ->  STATE_CANNOT_SEPARATE
    -       no state on the registration  ->  NO_STATE_ON_RECORD

WHAT THIS SCRIPT DOES **NOT** DO
---------------------------------
It does not repoint anything. `TRBF-...` values, tiers and
`attribution_method`s are untouched, and the md5 of every base field is asserted
unchanged. Two reasons, both house rules:

  * `ENTITY_MATCH_RULES` rule 8 - an agent ruling may not mint tier A, and every
    row here is tier A or tier B on somebody else's authority.
  * the Bristol Bay precedent - a repoint that KEYS DOLLARS awaits the owner.
    One of these keys $3.55M.

So it FLAGS, additively, and files a one-minute ruling with the evidence
attached. A flagged row can be reversed; a repointed one cannot be found again.

MEASURED 2026-09-02 - 13 collisions, $5.72M of prime obligations on 415 rows
-----------------------------------------------------------------------------
    government-keyed ledger rows scanned            5,836
    skipped, a legal form in the name (I2 guard)    2,771
    skipped, the KEYED entity explains the name       857
    skipped, the name reaches >1 government             0
    -----------------------------------------------------
    cross-government name collisions                   13   9 tier A, 4 tier B
      of which in cedar_publishable_identifiers.csv     8

  8 CONTRADICTED - the state on the record names the OTHER nation
    UEI  HLTFBD3FTDG8  A hand        Fort Sill Apache OK -> Warm Springs  OR
                       "Confederated Tribes Of Warm Springs Reservation Of
                        Oregon"   285 rows $3,552,567, recipient_state_code
                        = OR on 285 of 285.  PUBLISHED
    UEI  LWRAHAFNKQ13  A hand        Santee Sioux  NE -> Flandreau  SD  $51,336
    CAGE 50WN1         A bgov_manual Santee Sioux  NE -> Flandreau  SD  $51,336
    CAGE 4AD60         A bgov_manual Santee Sioux  NE -> Flandreau  SD  $24,521
    CAGE 3VFL3         A bgov_manual Winnebago     NE -> Ho-Chunk   WI  $0
    CAGE 3XGD7         A bgov_manual Sac and Fox   OK -> Sac & Fox of Missouri
    CAGE 4XH62         A bgov_manual Yavapai-Apache AZ -> Chignik Lagoon, an
                       ALASKA NATIVE VILLAGE. `state` on the row reads AK.
    UEI  PHLGX6MG6UK1  B cluster_v3  Shoshone-Paiute -> Ely Shoshone (both NV,
                       so STATE_CANNOT_SEPARATE - held, not proposed)

  1 the KEYED entity is right and the SPINE has the gap
    UEI  H1ZEEZK2D6B3  A hand   "San Juan Pueblo Tribal Council" -> Ohkay
                       Owingeh, NM.  113 of 113 awards are in NEW MEXICO, and
                       Ohkay Owingeh IS the renamed San Juan Pueblo. The
                       apparent rival, `TRBF-SNJUAN-00`, is the San Juan
                       SOUTHERN PAIUTE Tribe of ARIZONA. Nothing is wrong with
                       the attribution; `Ohkay Owingeh` simply does not carry
                       `San Juan Pueblo` in `aliases`, so a former name reads
                       as a foreign one. Disposition
                       TRANSACTION_STATE_AGREES_WITH_KEYED_ENTITY and NO
                       repoint is proposed. **A rename with no alias is
                       indistinguishable from a collision until you look at the
                       address** - which is why rung 1 runs on the transaction
                       record too, not only on the registration.

  4 tier B `need_v6` EIN rows with no state anywhere - flagged, not proposed.
    `need_v6` is 6.5% accurate and never publishes alone.

THE NAMED INVARIANTS
--------------------
  I1  every flagged row names a proposed entity that exists in the spine and is
      NOT the entity the row is keyed to.
  I2  the flag never fires on a `legal_business_name` carrying a legal form.
      This is the Ho-Chunk Inc guard; without it the detector inverts.
  I3  a flagged row's proposed entity is unique - the basis records the count.
  I4  CONSERVE. rows unchanged, no column lost, and the md5 of every pre-existing
      field is unchanged: no tribe_id, tier or method was altered.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

LEDGER = ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
PRIME = ROOT / "data" / "clean" / "prime_contracts.csv"
PUBID = ROOT / "data" / "clean" / "cedar_publishable_identifiers.csv"
REGISTER = ROOT / "review" / f"ledger_crossgov_name_collisions_{TODAY}.csv"
MANIFEST = ROOT / "docs" / "CROSSTRIBE_LEGALNAME_AUDIT.json"
BAK_TAG = f".bak_{TODAY}_pre_1099_crosstribe_legalname_audit"

NEW = ["crossgov_name_collision_flag",
       "crossgov_name_collision_proposed_entity_id",
       "crossgov_name_collision_disposition",
       "crossgov_name_collision_basis"]

GOV_CLASSES = {"Federally recognized tribe",
               "State-recognized tribe",
               "Federally recognized Alaska Native Village"}

#: LEGAL FORMS ONLY. Not "holdings", not "enterprises", not "group" - those are
#: words a nation's own name can carry. A token here means the name presents as
#: an incorporated firm, and a sovereign government's official name never does.
LEGAL_FORMS = {"INC", "INCORPORATED", "LLC", "L.L.C", "LTD", "LIMITED",
               "CORP", "CORPORATION", "CO", "COMPANY", "LP", "LLP", "PC",
               "PLLC", "PLC", "LC", "GMBH", "PA"}

#: Words that carry no identifying force between two governments. Used ONLY to
#: compute the residue in rule 7, never to award a match.
STRUCTURAL = {"THE", "OF", "AND", "IN", "AT", "FOR", "A", "AN", "TRIBE",
              "TRIBES", "TRIBAL", "NATION", "NATIONS", "BAND", "BANDS",
              "INDIAN", "INDIANS", "COMMUNITY", "PEOPLE", "PEOPLES",
              "NATIVE", "AMERICAN", "RESERVATION", "PUEBLO", "RANCHERIA",
              "COLONY", "VILLAGE", "CONFEDERATED", "FEDERATED", "COUNCIL"}

TOK = re.compile(r"[^A-Z0-9]+")


def toks(s: str) -> set:
    return {t for t in TOK.split((s or "").upper()) if t}


def distinctive(s: str) -> set:
    return toks(s) - STRUCTURAL


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


def spine_index():
    rows, _ = read_table(SPINE)
    gov = {}
    for r in rows:
        if (r.get("entity_class") or "").strip() not in GOV_CLASSES:
            continue
        tid = (r.get("tribe_id") or "").strip()
        names = [r.get("canonical_name") or "", r.get("fr_official_name") or ""]
        names += [a for a in (r.get("aliases") or "").split("|") if a.strip()]
        gov[tid] = {
            "name": (r.get("canonical_name") or "").strip(),
            "state": (r.get("state") or "").strip().upper(),
            "class": (r.get("entity_class") or "").strip(),
            "tokens": set().union(*[distinctive(n) for n in names]) or set(),
        }
    allrows = {(r.get("tribe_id") or "").strip(): r for r in rows}
    return gov, allrows


def dollars(keys):
    """(rows, obligations, state counter) per identifier, one pass."""
    out = {k: [0, 0.0, {}] for k in keys}
    if not PRIME.exists() or not keys:
        return out
    import pandas as pd
    want = ["awardee_uei", "cage_code", "recipient_state_code",
            "total_obligations"]
    have = pd.read_csv(PRIME, nrows=0).columns.tolist()
    want = [c for c in want if c in have]
    for ch in pd.read_csv(PRIME, dtype=str, keep_default_na=False,
                          usecols=want, chunksize=250_000):
        ob = pd.to_numeric(ch.get("total_obligations"),
                           errors="coerce").fillna(0)
        for (ityp, ival) in keys:
            col = "cage_code" if ityp == "CAGE" else "awardee_uei"
            if col not in ch:
                continue
            m = ch[col] == ival
            if not m.any():
                continue
            a = out[(ityp, ival)]
            a[0] += int(m.sum())
            a[1] += float(ob[m].sum())
            for s in ch.loc[m, "recipient_state_code"]:
                a[2][s] = a[2].get(s, 0) + 1
    return out


def detect():
    gov, _ = spine_index()
    rows, fields = read_table(LEDGER)
    pub = {(r.get("identifier_type"), r.get("identifier"))
           for r in read_table(PUBID)[0]}
    hits = []
    n_gov_keyed = n_legalform_skipped = 0
    n_keyed_explains = n_ambiguous = 0
    for r in rows:
        keyed = (r.get("tribe_id") or "").strip()
        if keyed not in gov:
            continue
        n_gov_keyed += 1
        lbn = (r.get("legal_business_name") or "").strip()
        if not lbn:
            continue
        if toks(lbn) & LEGAL_FORMS:          # I2 - the Ho-Chunk Inc guard
            n_legalform_skipped += 1
            continue
        d = distinctive(lbn)
        if not d:
            continue
        # THE KEYED ENTITY GETS THE FIRST LOOK. If its own official names
        # account for the whole name, there is no contradiction to report -
        # and skipping this test is how the detector fired on `Red Lake Band
        # of Chippewa Indians` -> Red Cliff, whose name is a strict SUPERSET
        # of Red Lake's. A subset test with no incumbent check reports every
        # nation whose name is contained in a longer one.
        keyed_residue = d - gov[keyed]["tokens"]
        if not keyed_residue:
            n_keyed_explains += 1
            continue
        cands = [t for t, g in gov.items()
                 if t != keyed and d <= g["tokens"]]
        if len(cands) != 1:
            if len(cands) > 1:
                n_ambiguous += 1
            continue
        other = cands[0]
        rstate = (r.get("state") or "").strip().upper()
        # normalise a spelled-out state to its postal code where we can
        if len(rstate) > 2:
            rstate = {"WISCONSIN": "WI", "NEBRASKA": "NE", "OKLAHOMA": "OK",
                      "OREGON": "OR", "KANSAS": "KS", "LOUISIANA": "LA",
                      "ALABAMA": "AL", "GEORGIA": "GA", "CALIFORNIA": "CA",
                      "SOUTH DAKOTA": "SD", "TEXAS": "TX",
                      "NORTH DAKOTA": "ND"}.get(rstate, rstate)
        ks, os_ = gov[keyed]["state"], gov[other]["state"]
        if ks and ks == os_:
            disp = "STATE_CANNOT_SEPARATE"
        elif not rstate:
            disp = ""            # filled from the transaction record in build()
        elif rstate == os_:
            disp = "REGISTRATION_STATE_CONTRADICTS_KEYED_ENTITY"
        elif rstate == ks:
            disp = "REGISTRATION_STATE_AGREES_WITH_KEYED_ENTITY"
        else:
            disp = "REGISTRATION_STATE_MATCHES_NEITHER"
        hits.append({
            "identifier_type": r.get("identifier_type"),
            "identifier": r.get("identifier"),
            "keyed_entity_id": keyed,
            "keyed_entity_name": gov[keyed]["name"],
            "keyed_entity_state": ks,
            "keyed_entity_class": gov[keyed]["class"],
            "legal_business_name_as_recorded": lbn,
            "registration_state_as_recorded": r.get("state") or "",
            "proposed_entity_id": other,
            "proposed_entity_name": gov[other]["name"],
            "proposed_entity_state": os_,
            "proposed_entity_class": gov[other]["class"],
            "residue_against_keyed_entity": "|".join(sorted(keyed_residue)),
            "residue_against_proposed_entity": "",
            "n_government_entities_matching_the_name": 1,
            "confidence_tier": r.get("confidence_tier") or "",
            "attribution_method": r.get("attribution_method") or "",
            "is_authority": r.get("is_authority") or "",
            "in_publishable_identifiers":
                "Y" if (r.get("identifier_type"),
                        r.get("identifier")) in pub else "N",
            "source_file": r.get("source_file") or "",
            "disposition": disp,
        })
    return (rows, fields, hits, n_gov_keyed, n_legalform_skipped,
            n_keyed_explains, n_ambiguous)


def build(dry_run=False) -> int:
    (rows, fields, hits, n_gov, n_form, n_keyed,
     n_amb) = detect()
    base = [c for c in fields if c not in NEW]
    before = digest(rows, base)

    keys = {(h["identifier_type"], h["identifier"]) for h in hits}
    money = dollars(keys)
    for h in hits:
        a = money[(h["identifier_type"], h["identifier"])]
        h["prime_rows"] = a[0]
        h["prime_obligations_usd"] = f"{a[1]:.2f}"
        ranked = sorted(a[2].items(), key=lambda kv: -kv[1])
        h["prime_recipient_states"] = "|".join(f"{k}:{v}" for k, v in ranked)
        # RUNG 1 AGAIN, ON THE TRANSACTION RECORD. Where the REGISTRATION
        # carries no state, the awards do - and the owner's ladder says look at
        # the address before anything else. This is what separates a real
        # collision from a RENAME: `San Juan Pueblo Tribal Council` keyed to
        # Ohkay Owingeh looks like a collision with San Juan Southern Paiute
        # (Arizona) and is not one - Ohkay Owingeh IS the renamed San Juan
        # Pueblo, and 113 of 113 awards sit in New Mexico. The spine simply
        # does not carry the former name as an alias, which is a spine gap and
        # not a misattribution.
        if not h["disposition"]:
            modal = ranked[0][0].strip().upper() if ranked else ""
            ks, os_ = h["keyed_entity_state"], h["proposed_entity_state"]
            if not modal:
                h["disposition"] = "NO_STATE_ON_ANY_RECORD"
            elif modal == os_:
                h["disposition"] = "TRANSACTION_STATE_CONTRADICTS_KEYED_ENTITY"
            elif modal == ks:
                h["disposition"] = "TRANSACTION_STATE_AGREES_WITH_KEYED_ENTITY"
            else:
                h["disposition"] = "TRANSACTION_STATE_MATCHES_NEITHER"

    flagged = {(h["identifier_type"], h["identifier"], h["keyed_entity_id"])
               for h in hits}
    hmap = {(h["identifier_type"], h["identifier"], h["keyed_entity_id"]): h
            for h in hits}
    out_fields = list(fields) + [c for c in NEW if c not in fields]
    for r in rows:
        for c in NEW:
            r.setdefault(c, "")
        k = (r.get("identifier_type"), r.get("identifier"),
             (r.get("tribe_id") or "").strip())
        if k not in flagged:
            for c in NEW:
                r[c] = ""
            continue
        h = hmap[k]
        r["crossgov_name_collision_flag"] = "Y"
        r["crossgov_name_collision_proposed_entity_id"] = \
            h["proposed_entity_id"]
        r["crossgov_name_collision_disposition"] = h["disposition"]
        r["crossgov_name_collision_basis"] = (
            "legal_business_name is the official name of exactly one OTHER "
            f"government-class spine entity ({h['proposed_entity_id']} "
            f"{h['proposed_entity_name']}, {h['proposed_entity_state']}); "
            "rule7 residue empty; no legal-form token in the name; "
            f"registration state {h['registration_state_as_recorded'] or '(none)'} "
            f"vs keyed {h['keyed_entity_state']}. FLAG ONLY - nothing "
            "repointed. See review/"
            f"ledger_crossgov_name_collisions_{TODAY}.csv")

    if digest(rows, base) != before:
        print("  [1099] FATAL: a base field changed. Refusing to write.")
        return 1

    if not dry_run:
        write_table(LEDGER, rows, out_fields, tag=BAK_TAG)
        REGISTER.parent.mkdir(parents=True, exist_ok=True)
        cols = list(hits[0].keys()) if hits else ["identifier"]
        with open(REGISTER, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(sorted(hits, key=lambda h: -float(
                h["prime_obligations_usd"])))

    print(f"  [1099] ledger rows {len(rows):,} unchanged | md5(base "
          f"{len(base)} fields) {before}")
    print(f"  [1099] COLUMN DIFF   gained "
          f"{len([c for c in out_fields if c not in fields])}: "
          f"{[c for c in out_fields if c not in fields]}")
    print(f"  [1099]               lost   0: []")
    print(f"  [1099] government-keyed ledger rows scanned      {n_gov:,}")
    print(f"  [1099] skipped, legal form in name (I2 guard)    {n_form:,}")
    print(f"  [1099] skipped, keyed entity explains the name    {n_keyed:,}")
    print(f"  [1099] skipped, name reaches >1 government        {n_amb:,}")
    print(f"  [1099] cross-government name collisions          {len(hits):,}")
    for h in sorted(hits, key=lambda x: -float(x["prime_obligations_usd"])):
        print(f"          {h['identifier_type']:4} {h['identifier']:<13} "
              f"tier {h['confidence_tier']} {h['attribution_method']:<24} "
              f"{h['keyed_entity_name'][:26]:<26} -> "
              f"{h['proposed_entity_name'][:30]:<30} "
              f"{h['disposition']:<32} "
              f"{h['prime_rows']:>5} rows ${float(h['prime_obligations_usd']):,.0f}"
              f"{'  PUBLISHED' if h['in_publishable_identifiers']=='Y' else ''}")
    tot = sum(float(h["prime_obligations_usd"]) for h in hits)
    print(f"  [1099] total prime exposure ${tot:,.0f} across "
          f"{sum(h['prime_rows'] for h in hits):,} rows")
    if not dry_run:
        print(f"  [1099] wrote {REGISTER.relative_to(ROOT)}")
        MANIFEST.write_text(json.dumps({
            "built": TODAY, "script": "1099_crosstribe_legalname_audit.py",
            "ledger": "data/clean/cedar_identifier_ledger_final.csv",
            "government_keyed_rows_scanned": n_gov,
            "skipped_legal_form_in_name": n_form,
            "skipped_keyed_entity_explains_the_name": n_keyed,
            "skipped_name_reaches_more_than_one_government": n_amb,
            "collisions": len(hits),
            "prime_rows_exposed": sum(h["prime_rows"] for h in hits),
            "prime_obligations_usd_exposed": round(tot, 2),
            "by_disposition": {d: sum(1 for h in hits
                                      if h["disposition"] == d)
                               for d in {h["disposition"] for h in hits}},
            "by_tier": {t: sum(1 for h in hits if h["confidence_tier"] == t)
                        for t in {h["confidence_tier"] for h in hits}},
            "register": str(REGISTER.relative_to(ROOT)).replace("\\", "/"),
            "cases": hits,
        }, indent=2), encoding="utf-8")
        print(f"  [1099] wrote {MANIFEST.relative_to(ROOT)}")
    return 0


def verify(path: Path | None = None) -> int:
    p = path or LEDGER
    rows, fields = read_table(p)
    if any(c not in fields for c in NEW):
        print("  [1099] verify: columns absent - run the audit first")
        return 1
    gov, _ = spine_index()
    fails = []
    n = 0
    for r in rows:
        if (r.get("crossgov_name_collision_flag") or "").strip() != "Y":
            if any((r.get(c) or "").strip() for c in NEW[1:]):
                fails.append(("I1", r.get("identifier"),
                              "collision fields set with no flag"))
            continue
        n += 1
        prop = (r.get("crossgov_name_collision_proposed_entity_id") or "").strip()
        keyed = (r.get("tribe_id") or "").strip()
        if prop not in gov:
            fails.append(("I1", r.get("identifier"),
                          f"proposed entity {prop!r} is not a government-class "
                          "spine entity"))
        if prop == keyed:
            fails.append(("I1", r.get("identifier"),
                          "proposed entity is the entity already keyed"))
        lbn = r.get("legal_business_name") or ""
        if toks(lbn) & LEGAL_FORMS:
            fails.append(("I2", r.get("identifier"),
                          "flagged a name carrying a legal form - this is the "
                          "Ho-Chunk Inc guard and it must never fire"))
        basis = r.get("crossgov_name_collision_basis") or ""
        if "exactly one OTHER" not in basis:
            fails.append(("I3", r.get("identifier"),
                          "basis does not record the uniqueness test"))
    print(f"  [1099] verify: {len(rows):,} ledger rows | {n} flagged | "
          f"{len(fails)} breach(es)")
    for f in fails[:20]:
        print(f"          {f[0]}  {f[1]}  {f[2]}")
    return 1 if fails else 0


def selftest() -> int:
    import tempfile
    rows, fields = read_table(LEDGER)
    if any(c not in fields for c in NEW):
        print("  [1099] selftest: run the audit first")
        return 1
    tmp = Path(tempfile.mkdtemp()) / "cedar_identifier_ledger_final.csv"
    cases = []

    def flagged(rs):
        for r in rs:
            if (r.get("crossgov_name_collision_flag") or "") == "Y":
                return r
        raise SystemExit("no flagged row")

    def run(label, mut):
        rs = [dict(r) for r in rows]
        mut(rs)
        write_table(tmp, rs, fields)
        rc = verify(tmp)
        cases.append((label, rc == 1))
        print(f"          {'FIRES ' if rc == 1 else 'SILENT'}  {label}")

    print("  [1099] selftest - inject the violation, assert exit 1")
    run("I1 proposed entity not in the spine",
        lambda rs: flagged(rs).__setitem__(
            "crossgov_name_collision_proposed_entity_id", "TRBF-NOSUCH-00"))
    run("I1 proposed entity is the entity already keyed",
        lambda rs: flagged(rs).__setitem__(
            "crossgov_name_collision_proposed_entity_id",
            flagged(rs)["tribe_id"]))
    run("I2 flag fired on a name carrying a legal form",
        lambda rs: flagged(rs).__setitem__("legal_business_name",
                                           "Ho-Chunk, Inc."))
    run("I3 basis does not record the uniqueness test",
        lambda rs: flagged(rs).__setitem__("crossgov_name_collision_basis",
                                           "looked wrong"))

    def orphan(rs):
        for r in rs:
            if (r.get("crossgov_name_collision_flag") or "") != "Y":
                r["crossgov_name_collision_disposition"] = "SOMETHING"
                return
    run("I1 collision fields populated with no flag", orphan)

    write_table(tmp, rows, fields)
    rc = verify(tmp)
    print(f"          {'PASS  ' if rc == 0 else 'FAIL  '}  restored copy "
          f"verifies clean (exit {rc})")
    ok = all(c[1] for c in cases) and rc == 0
    print(f"  [1099] selftest {sum(c[1] for c in cases)}/{len(cases)} "
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
