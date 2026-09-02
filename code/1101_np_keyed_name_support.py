#!/usr/bin/env python3
"""
Cedar Press - 1101: np_orgs' `name_match_support` DOES NOT MEASURE THE NAME
                    MATCH THAT IS LIVE ON THE ROW. AND THE REMEDY FOR THE
                    EASTERN STAR FAMILY IS A REDIRECT, NOT A BLOCK.

    py -3 code/1101_np_keyed_name_support.py            # enrich in place
    py -3 code/1101_np_keyed_name_support.py verify     # exit 1 on breach
    py -3 code/1101_np_keyed_name_support.py selftest   # prove verify FIRES

PART ONE - A CHECK THAT DOES NOT MEASURE ITS OWN NAME. THE FOURTEENTH.
------------------------------------------------------------------------
`code/952` documents `name_match_support` as *"the match shares NO token with
the canonical name shown"*. It computes it as

    support(d["org_name"], d["canonical_name_token_match"])

`canonical_name_token_match` is the candidate the **token-match funnel stage**
proposed. It is not the tribe the row is keyed to. On the live table, over the
1,423 rows that carry a live `tribe_id`:

    canonical_name_token_match is BLANK                            585
      -> the column reports `not_a_name_match` for a row that HAS a key
    canonical_name_token_match names a DIFFERENT tribe             288
    recomputed against the tribe the row actually cites:
      shares at least one token                                  1,421
      shares none                                                    2
    as recorded by 952:
      `no_shared_token_with_canonical_name`                          71

Worked example, which is what makes it obvious:

    EIN 873791650  CAHUILLA ELEMENTARY PARENT TEACHER ORGANIZATION
      tribe_id                    TRBF-CHLLAB-00   Cahuilla
      canonical_name_token_match  Agua Caliente        <- measured against THIS
      name_match_support          no_shared_token_with_canonical_name

The organisation's name contains CAHUILLA. It shares no token with *Agua
Caliente*, and that is all the column ever said.

**So the standing figure - "2,268 rows share no token at all with the canonical
name they cite (541 live)" - is right about the token-match funnel and wrong
about the live attributions.** Of the 2,268, 1,594 are already
`excluded_by_prior_ruling` and only **71 carry a live key at all**; on 71 of
those 71 the organisation name DOES share a token with the tribe it is keyed to.
The "541 live" is the `funnel_stage = canonical_name_match` slice, where the
column IS measuring the right thing - those rows are candidates, not keys.

952's column is NOT overwritten. It is correct within its own slice and it is
the evidence of what the funnel proposed. This pass adds
`keyed_name_match_*`, which measures the row's **live** key, and
`name_match_support_measured_against`, which says on the row itself which name
the older column was scored on. A mis-aimed check is repaired by naming its
aim, not by silently re-pointing it.

PART TWO - THE 71 ARE NOT VINDICATED. THEY FAIL A DIFFERENT TEST.
-------------------------------------------------------------------
Every one of the 71 shares a distinctive token with the tribe it is keyed to,
and the token is a PLACE NAME:

    OLD PROS OF LAGUNA WOODS VILLAGE               -> Pueblo of Laguna (NM)
    CALIFORNIA CLUB OF LAGUNA WOODSVILLAGE         -> Pueblo of Laguna (NM)
    FIRST NATIONAL BANK IN WICHITA CHARITABLE TRUST-> Wichita (OK)
    NORTH END WICHITA HISTORICAL SOCIETY           -> Wichita (OK)
    WESTERN DAKOTA ESTATE PLANNING COUNCIL INC     -> Council Native Corp (AK)

This is the Umatilla defect (`ENTITY_MATCH_RULES` rule 1) and the flag that was
supposed to catch it pointed somewhere else. The honest reading of the two
measurements together is: **the recorded flag found the wrong rows for the
wrong reason, and the rows it should have found were labelled
`distinctive_token`, which reads as supported.**

PART THREE - EASTERN: A REDIRECT, NOT A BLOCK
-----------------------------------------------
`952` flagged 258 rows as `CANDIDATE_NAME_MATCH_GENERIC_TOKEN_ONLY`; **26 of
them still carry a live `tribe_id`** - ST THOMAS THE APOSTLE PARISH CHICKASAW
to the Chickasaw Nation on `ST`, UNITED WAY OF SENECA COUNTY to the Seneca
Nation on `UNITED`, ORDER OF THE EASTERN STAR OF SOUTH CAROLINA 5 SENECA to the
Seneca Nation on `EASTERN`. Flagging the evidence left the key live.

And a blanket exclusion on the token would bury the thing worth finding. Three
rows in the EASTERN family are **genuine Native organisations keyed to the
wrong nation**:

    EASTERN CHEROKEE SOUTHERN IROQUOIS AND UNITED TRIBES OF SOUTH CAROLIN  SC
        keyed  ITO-NTDSTH-00  United South and Eastern Tribes, Inc.  (TN)
        should be TRBS-ECSIUT-00, which IS IN THE SPINE, in SC, and whose
        official name accounts for every distinctive word in the filing
        (`CAROLIN` is the filing's own truncation of `CAROLINA` - rule 7
        already accepts `RESERVATI` as a spelling variant)         -> REDIRECT

    WIQUAPAUG EASTERN PEQUOT INDIAN TRIBE                                  RI
        keyed  TRBS-EPQUOT-00  Eastern Pequot Tribal Nation  (CT)
        residue WIQUAPAUG, state RI vs CT, no RI Pequot in the spine -> HOLD,
        and the spine gap is named

    EASTERN BAND OF CHICKASAW INDIANS FOUNDATION INC                       TN
        keyed  TRBF-CHKSWN-00  The Chickasaw Nation  (OK)
        residue EASTERN|FOUNDATION, state TN vs OK, no TN Chickasaw entity
        in the spine                                              -> HOLD

All three keep `disposition` and their Native status. **A refusal says only
"this is not THAT entity"** (`ENTITY_MATCH_RULES`), and Native status comes from
what an organisation says about itself in its own filing.

THE THREE DISPOSITIONS, WHAT THEY MEASURED, AND WHY NOTHING IS BLANKED
------------------------------------------------------------------------
Over the 1,423 rows carrying a live `tribe_id`:

    SUPPORTED                     888   62.4%
    HELD_STATE_DISAGREES          461   32.4%
    REFUSED_GENERIC_TOKEN_ONLY     61    4.3%
    REDIRECT_PROPOSED              13    0.9%

**HELD_STATE_DISAGREES is the headline and it is the Umatilla defect at scale.**
The keyed nation's name is contained in the organisation's, the states disagree,
and 2+ distinctive words are unaccounted for. What that finds:

    ISLAMIC ASSOCIATION OF MID KANSAS AT WICHITA KANSAS  KS -> Wichita (OK)
    WINNEBAGO PORK PRODUCERS                             IL -> Winnebago (NE)
    IRON CROW THEATRE COMPANY INC                        MD -> Crow (MT)
    LAGUNA BEACH FIREFIGHTERS ASSOCIATION                CA -> Pueblo of Laguna
    SANTAS CLOSET OF WINNEBAGO COUNTY INC                WI -> Winnebago (NE)
    WHITE POINT CEMETERY OF COMANCHE COUNTY CORPORATION  TX -> Comanche (OK)

Concentrated on six nations whose names are also American place names: Crow 63,
Pueblo of Laguna 61, Fond du Lac 58, Seneca 53, Winnebago 26, Wichita 22.
**50 of the 461 carry `disposition = NATIVE_VERIFIED_STRICT`.**

The existing `placename_risk_flag` reaches **160 of the 461**, so **301 are
newly flagged**; it also fires on 202 rows this pass calls SUPPORTED, so the two
are measuring different things and neither supersedes the other.

    REFUSED_GENERIC_TOKEN_ONLY  every token shared with the KEYED entity's own
                                names is generic. Unarguable; the link rests on
                                a word of English. 61 rows - more than 952's 26,
                                because this measures against the keyed entity's
                                full name set (canonical + FR official + alias)
                                rather than the funnel's candidate.
    REDIRECT_PROPOSED           exactly one OTHER spine entity accounts for
                                every distinctive word of the filed name, in
                                the organisation's own state, BIDIRECTIONALLY.

The 13 redirects, and they are the whole argument for a redirect over a block:

    EASTERN CHEROKEE SOUTHERN IROQUOIS AND UNITED TRIBES OF SOUTH CAROLIN
        United South and Eastern Tribes (TN)  ->  TRBS-ECSIUT-00 (SC)
    AMERICAN INDIAN COUNCIL ON ALCOHOLISM INC
        Council Native Corporation (AK!)      ->  its own spine entity
    MAKAHA HAWAIIAN CIVIC CLUB, NATIVE HAWAIIAN EDUCATION ASSOCIATION,
    NATIVE HAWAIIAN HOSPITALITY ASSOCIATION, NATIVE HAWAIIAN LEGAL
    CORPORATION, NATIVE HAWAIIAN PHILANTHROPY
        all five keyed to `Hawaiian Native Corporation` -> their own entities
    YUROK ALLIANCE FOR NORTHERN CALIFORNIA HOUSING, SENECA NATION OF INDIANS
    ECONOMIC DEVELOPMENT COMPANY, CHEHALIS TRIBAL LOAN FUND, INDIAN HEALTH
    CENTER OF SANTA CLARA VALLEY, LEECH LAKE FINANCIAL SERVICES,
    WHITE EARTH INVESTMENT INITIATIVE
        each keyed to its NATION -> its own spine entity. Rule 7 exactly: a
        tribal college, a loan fund and a clinic are real entities and they are
        not the nation.

`tribe_id`, `cedar_uid` and `disposition` are NOT blanked, following
`code/610`, which flags and never deletes for the same reason: a deleted row
asserts nothing, a flagged row says what was refused and can be reversed.
The redirect is a PROPOSAL on the row and mints no tier
(`ENTITY_MATCH_RULES` rule 8).

WHAT SURVIVED THE TIGHTENING, AND WHY IT IS RECORDED
------------------------------------------------------
The first version of the redirect rule proposed **37** moves and six of them
were wrong in the same way - one-way containment onto a longer name:

    LUMBEE NATIONS INC                    -> Lumbee Guaranty Bank
    JEMEZ SPRINGS COMMUNITY FOUNDATION    -> Jemez Day School
    THE CHEHALIS FOUNDATION               -> Chehalis Tribal Loan Fund
    ALASKA NATIVE TRIBAL HEALTH CONSORTIUM-> Southeast Alaska Regional Health
    INDIAN ASSOCIATION OF SOUTH SANTA CLARA COUNTY -> Indian Health Center of
                                             Santa Clara Valley
    MAKAHA COMMUNITY CENTER               -> Makaha Hawaiian Civic Club

Requiring the match to hold in BOTH directions killed all six and cost none of
the 13. That is rule 7's argument restated: containment is not identity, and it
is not identity in whichever direction you run it.

THE NAMED INVARIANTS
--------------------
  I1  `keyed_name_match_support` is in the declared vocabulary on every row
      that carries a live `tribe_id`, and blank on every row that does not.
  I2  every recorded shared token really is shared between the organisation
      name and the KEYED entity's own names - the label and the evidence agree.
  I3  a `REFUSED_GENERIC_TOKEN_ONLY` row records at least one shared token and
      EVERY recorded token is generic.
  I4  a `key_redirect_proposed_entity_id` exists in the spine, is not the
      entity already keyed, and its state equals the organisation's state.
  I5  CONSERVE. rows unchanged, no column lost, and the md5 of every
      pre-existing field is unchanged - no key, tier or disposition was moved.
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
try:                                    # a console codepage is not a finding
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
TODAY = date.today().isoformat()

TABLE = ROOT / "data" / "clean" / "np_orgs.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
MANIFEST = ROOT / "docs" / "NP_KEYED_NAME_SUPPORT.json"
REGISTER = ROOT / "review" / f"np_live_key_review_{TODAY}.csv"
BAK_TAG = f".bak_{TODAY}_pre_1101_np_keyed_name_support"

NEW = ["name_match_support_measured_against",
       "keyed_name_match_support", "keyed_name_match_shared_tokens",
       "keyed_name_match_residue", "keyed_state_agreement",
       "key_review_disposition", "key_review_basis",
       "key_redirect_proposed_entity_id", "key_redirect_proposed_name"]

SUPPORT_VOCAB = {"distinctive_token", "generic_token_only",
                 "no_shared_token_with_keyed_entity"}
DISPO_VOCAB = {"SUPPORTED", "REFUSED_GENERIC_TOKEN_ONLY",
               "HELD_STATE_DISAGREES", "REDIRECT_PROPOSED"}

TOK = re.compile(r"[^A-Z0-9]+")

#: Reused verbatim from `code/952`. Same list, same justification - a shared
#: token drawn only from here is a coincidence of English, Spanish or civic
#: vocabulary. Copied rather than imported because 952 owns its own copy and
#: two writers must not silently drift apart; `verify` I3 tests the label
#: against THIS set, so a drift shows up as a breach rather than as a quiet
#: difference of opinion.
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


def toks(s: str) -> set:
    return {t for t in TOK.split((s or "").upper()) if t}


def residue(org_tokens: set, entity_tokens: set) -> set:
    """Rule 7 residue, with the spelling-variant tolerance rule 7 already
    grants (`RESERVATI` for `RESERVATION`). A residue token that is a strict
    prefix of an entity token, 5 characters or more, is a TRUNCATION and is
    accounted for. `CAROLIN` for `CAROLINA` is the case that needs it and the
    IRS filing is where the truncation comes from."""
    out = set()
    for t in org_tokens - entity_tokens:
        if len(t) >= 5 and any(e.startswith(t) or t.startswith(e)
                               for e in entity_tokens if len(e) >= 5):
            continue
        out.add(t)
    return out


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
    idx = {}
    for r in rows:
        tid = (r.get("tribe_id") or "").strip()
        if not tid:
            continue
        names = [r.get("canonical_name") or "", r.get("fr_official_name") or ""]
        names += [a for a in (r.get("aliases") or "").split("|") if a.strip()]
        idx[tid] = {
            "name": (r.get("canonical_name") or "").strip(),
            "state": (r.get("state") or "").strip().upper(),
            "class": (r.get("entity_class") or "").strip(),
            "tokens": set().union(*[toks(n) for n in names]) if names else set(),
        }
    return idx


def build(dry_run=False) -> int:
    rows, fields = read_table(TABLE)
    spine = spine_index()
    base = [c for c in fields if c not in NEW]
    before = digest(rows, base)
    n_before = len(rows)

    # entities indexed by state, for the redirect search
    by_state = {}
    for tid, g in spine.items():
        by_state.setdefault(g["state"], []).append(tid)

    st = {"rows": n_before, "live_keyed": 0, "support": {}, "dispo": {},
          "recorded_support_disagrees_with_keyed": 0,
          "recorded_no_shared_but_keyed_shares": 0,
          "redirects": []}
    reg = []
    out_fields = list(fields) + [c for c in NEW if c not in fields]

    for r in rows:
        for c in NEW:
            r.setdefault(c, "")
        r["name_match_support_measured_against"] = \
            (r.get("canonical_name_token_match") or "") or "(blank)"
        tid = (r.get("tribe_id") or "").strip()
        if not tid or tid not in spine:
            for c in NEW[1:]:
                r[c] = ""
            continue
        st["live_keyed"] += 1
        g = spine[tid]
        ot = toks(r.get("org_name"))
        shared = ot & g["tokens"]
        res = residue(ot, g["tokens"]) - GENERIC
        if not shared:
            sup = "no_shared_token_with_keyed_entity"
        elif shared <= GENERIC:
            sup = "generic_token_only"
        else:
            sup = "distinctive_token"
        r["keyed_name_match_support"] = sup
        r["keyed_name_match_shared_tokens"] = "|".join(sorted(shared))
        r["keyed_name_match_residue"] = "|".join(sorted(res))
        st["support"][sup] = st["support"].get(sup, 0) + 1

        rec = (r.get("name_match_support") or "").strip()
        if rec and rec != "not_a_name_match":
            mapped = {"no_shared_token_with_canonical_name":
                      "no_shared_token_with_keyed_entity"}.get(rec, rec)
            if mapped != sup:
                st["recorded_support_disagrees_with_keyed"] += 1
            if (rec == "no_shared_token_with_canonical_name"
                    and sup != "no_shared_token_with_keyed_entity"):
                st["recorded_no_shared_but_keyed_shares"] += 1

        ostate = (r.get("state") or "").strip().upper()
        agree = ("UNKNOWN" if not (ostate and g["state"])
                 else ("Y" if ostate == g["state"] else "N"))
        r["keyed_state_agreement"] = agree

        # ---- THE REDIRECT SEARCH ------------------------------------------
        # Three conditions, and the second and third are what keep it honest.
        #
        #  a. the KEYED entity must leave a residue. If the nation's own name
        #     already accounts for the filed name there is nothing to redirect
        #     - and without this, `LUMBEE NATIONS INC` proposes a move from the
        #     Lumbee Tribe to Lumbee Guaranty Bank.
        #  b. the match must be BIDIRECTIONAL on distinctive tokens: the filed
        #     name accounts for the candidate AND the candidate accounts for
        #     the filed name. One-way containment is what rule 7 refuses, and
        #     it is what proposed `JEMEZ SPRINGS COMMUNITY FOUNDATION` ->
        #     Jemez Day School, `THE CHEHALIS FOUNDATION` -> Chehalis Tribal
        #     Loan Fund and `ALASKA NATIVE TRIBAL HEALTH CONSORTIUM` ->
        #     Southeast Alaska Regional Health Consortium. All three die here.
        #  c. the candidate must be UNIQUE in the organisation's own state.
        #
        # Truncation tolerance runs in both directions, which is what lets the
        # IRS's own `... UNITED TRIBES OF SOUTH CAROLIN` reach `... of South
        # Carolina`.
        redirect = ""
        od = (ot - GENERIC)
        if ostate and od and (res):
            cands = []
            for t in by_state.get(ostate, []):
                if t == tid:
                    continue
                et2 = spine[t]["tokens"]
                ed = et2 - GENERIC
                if not ed:
                    continue
                if residue(ot, et2) - GENERIC:
                    continue                      # filed name has residue
                if residue(ed, ot) - GENERIC:
                    continue                      # candidate has residue
                cands.append(t)
            if len(cands) == 1:
                redirect = cands[0]

        if redirect:
            dispo = "REDIRECT_PROPOSED"
            r["key_redirect_proposed_entity_id"] = redirect
            r["key_redirect_proposed_name"] = spine[redirect]["name"]
            basis = (f"exactly one OTHER spine entity in {ostate} accounts for "
                     "every distinctive word of the filed name with an empty "
                     f"rule-7 residue: {redirect} "
                     f"{spine[redirect]['name']}. The keyed entity {tid} "
                     f"({g['name']}, {g['state']}) leaves residue "
                     f"{'|'.join(sorted(res)) or '(none)'}. PROPOSAL - no tier "
                     "is minted (ENTITY_MATCH_RULES rule 8).")
            st["redirects"].append(
                {"EIN": r.get("EIN"), "org_name": r.get("org_name"),
                 "state": ostate, "from_entity_id": tid,
                 "from_entity_name": g["name"], "to_entity_id": redirect,
                 "to_entity_name": spine[redirect]["name"]})
        elif sup == "generic_token_only":
            dispo = "REFUSED_GENERIC_TOKEN_ONLY"
            basis = ("every token shared with the KEYED entity's own names is "
                     "generic English or civic vocabulary "
                     f"({'|'.join(sorted(shared))}). ENTITY_MATCH_RULES rule "
                     "1: an entity whose whole shared token set is generic may "
                     "not win a name-only match. This refuses THIS LINK; it "
                     "says nothing about whether the organisation is Native.")
        elif agree == "N" and len(res) >= 2:
            dispo = "HELD_STATE_DISAGREES"
            basis = (f"organisation is in {ostate}, the keyed entity "
                     f"{tid} ({g['name']}) is in {g['state']}, and the filed "
                     f"name leaves {len(res)} distinctive words unaccounted "
                     f"for ({'|'.join(sorted(res))}). No unique alternative "
                     f"entity exists in {ostate}, so this is a SPINE GAP or a "
                     "wrong key and the evidence does not separate them. Held "
                     "(ADR-010); nothing blanked.")
        else:
            dispo = "SUPPORTED"
            basis = (f"shares {'|'.join(sorted(shared - GENERIC)) or '(none)'} "
                     f"with the keyed entity; state agreement {agree}; "
                     f"residue {len(res)}.")
        r["key_review_disposition"] = dispo
        r["key_review_basis"] = basis
        st["dispo"][dispo] = st["dispo"].get(dispo, 0) + 1
        if dispo != "SUPPORTED":
            reg.append({
                "EIN": r.get("EIN"), "org_name": r.get("org_name"),
                "org_state": ostate, "keyed_entity_id": tid,
                "keyed_entity_name": g["name"], "keyed_entity_state": g["state"],
                "keyed_name_match_support": sup,
                "shared_tokens": r["keyed_name_match_shared_tokens"],
                "residue": r["keyed_name_match_residue"],
                "recorded_name_match_support": rec,
                "recorded_measured_against":
                    r["name_match_support_measured_against"],
                "disposition": dispo,
                "redirect_to": r["key_redirect_proposed_entity_id"],
                "redirect_to_name": r["key_redirect_proposed_name"],
                "np_disposition": r.get("disposition") or "",
                "basis": basis})

    if digest(rows, base) != before:
        print("  [1101] FATAL: a base field changed. Refusing to write.")
        return 1
    if len(rows) != n_before:
        print("  [1101] FATAL: row count moved. Refusing to write.")
        return 1

    if not dry_run:
        write_table(TABLE, rows, out_fields, tag=BAK_TAG)
        REGISTER.parent.mkdir(parents=True, exist_ok=True)
        if reg:
            with open(REGISTER, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(reg[0].keys()))
                w.writeheader()
                w.writerows(sorted(reg, key=lambda x: (x["disposition"],
                                                       x["org_name"])))

    gained = [c for c in out_fields if c not in fields]
    print(f"  [1101] rows {len(rows):,} unchanged | md5(base {len(base)} "
          f"fields) {before}")
    print(f"  [1101] COLUMN DIFF   gained {len(gained)}: {gained}")
    print(f"  [1101]               lost   0: []")
    print(f"  [1101] live-keyed rows {st['live_keyed']:,}")
    print("  [1101] keyed_name_match_support (measured against the LIVE key)")
    for k, v in sorted(st["support"].items(), key=lambda kv: -kv[1]):
        print(f"          {k:<40} {v:>6,}")
    print(f"  [1101] recorded name_match_support disagrees with the keyed "
          f"measurement on {st['recorded_support_disagrees_with_keyed']:,} rows")
    print(f"  [1101] rows recorded `no_shared_token_with_canonical_name` that "
          f"DO share a token with the tribe they cite: "
          f"{st['recorded_no_shared_but_keyed_shares']:,}")
    print("  [1101] key_review_disposition")
    for k, v in sorted(st["dispo"].items(), key=lambda kv: -kv[1]):
        print(f"          {k:<32} {v:>6,}")
    for d in st["redirects"]:
        print(f"          REDIRECT  {d['EIN']}  {d['org_name'][:52]:<52} "
              f"{d['from_entity_name'][:28]:<28} -> {d['to_entity_name'][:38]}")
    if not dry_run:
        print(f"  [1101] wrote {REGISTER.relative_to(ROOT)} ({len(reg)} rows)")
        MANIFEST.write_text(json.dumps(
            {"built": TODAY, "script": "1101_np_keyed_name_support.py",
             "table": "data/clean/np_orgs.csv", "columns_added": NEW,
             "base_fields_md5": before, **st}, indent=2), encoding="utf-8")
        print(f"  [1101] wrote {MANIFEST.relative_to(ROOT)}")
    return 0


def verify(path: Path | None = None) -> int:
    p = path or TABLE
    rows, fields = read_table(p)
    if any(c not in fields for c in NEW):
        print("  [1101] verify: columns absent - run the enricher first")
        return 1
    spine = spine_index()
    fails = []
    n = 0
    for r in rows:
        tid = (r.get("tribe_id") or "").strip()
        sup = (r.get("keyed_name_match_support") or "").strip()
        dispo = (r.get("key_review_disposition") or "").strip()
        ein = r.get("EIN")
        if not tid or tid not in spine:
            if sup or dispo:
                fails.append(("I1", ein, "keyed columns set on a row with no "
                                         "live key"))
            continue
        n += 1
        if sup not in SUPPORT_VOCAB:
            fails.append(("I1", ein, f"keyed_name_match_support {sup!r} "
                                     "off-vocabulary"))
        if dispo not in DISPO_VOCAB:
            fails.append(("I1", ein, f"key_review_disposition {dispo!r} "
                                     "off-vocabulary"))
        ot = toks(r.get("org_name"))
        et = spine[tid]["tokens"]
        rec = {t for t in (r.get("keyed_name_match_shared_tokens")
                           or "").split("|") if t}
        if rec - (ot & et):
            fails.append(("I2", ein, "a recorded shared token is not shared "
                                     "with the KEYED entity"))
        if dispo == "REFUSED_GENERIC_TOKEN_ONLY":
            if not rec:
                fails.append(("I3", ein, "generic-token refusal records no "
                                         "shared token"))
            if rec - GENERIC:
                fails.append(("I3", ein, "generic-token refusal records a "
                                         "NON-generic shared token"))
        red = (r.get("key_redirect_proposed_entity_id") or "").strip()
        if red:
            if red not in spine:
                fails.append(("I4", ein, f"redirect target {red} not in spine"))
            elif red == tid:
                fails.append(("I4", ein, "redirect target is the entity "
                                         "already keyed"))
            elif spine[red]["state"] != (r.get("state") or "").strip().upper():
                fails.append(("I4", ein, "redirect target's state is not the "
                                         "organisation's state"))
    print(f"  [1101] verify: {len(rows):,} rows | {n:,} live-keyed | "
          f"{len(fails)} breach(es)")
    for f in fails[:20]:
        print(f"          {f[0]}  {f[1]}  {f[2]}")
    if len(fails) > 20:
        print(f"          ... and {len(fails)-20} more")
    return 1 if fails else 0


def selftest() -> int:
    import tempfile
    rows, fields = read_table(TABLE)
    if any(c not in fields for c in NEW):
        print("  [1101] selftest: run the enricher first")
        return 1
    tmp = Path(tempfile.mkdtemp()) / "np_orgs.csv"
    cases = []

    def run(label, mut):
        rs = [dict(r) for r in rows]
        mut(rs)
        write_table(tmp, rs, fields)
        rc = verify(tmp)
        cases.append((label, rc == 1))
        print(f"          {'FIRES ' if rc == 1 else 'SILENT'}  {label}")

    def keyed(rs):
        for r in rs:
            if (r.get("keyed_name_match_support") or "").strip():
                return r
        raise SystemExit("no keyed row")

    def refused(rs):
        for r in rs:
            if (r.get("key_review_disposition")
                    or "") == "REFUSED_GENERIC_TOKEN_ONLY":
                return r
        return None

    def redirected(rs):
        for r in rs:
            if (r.get("key_redirect_proposed_entity_id") or "").strip():
                return r
        return None

    print("  [1101] selftest - inject the violation, assert exit 1")
    run("I1 off-vocabulary keyed_name_match_support",
        lambda rs: keyed(rs).__setitem__("keyed_name_match_support", "maybe"))
    run("I1 off-vocabulary key_review_disposition",
        lambda rs: keyed(rs).__setitem__("key_review_disposition", "other"))
    run("I2 a recorded shared token that is not shared",
        lambda rs: keyed(rs).__setitem__("keyed_name_match_shared_tokens",
                                         "ZZZNOTATOKEN"))
    if refused(rows) is not None:
        run("I3 generic refusal recording a non-generic token",
            lambda rs: refused(rs).__setitem__(
                "keyed_name_match_shared_tokens", "CHICKASAW"))
    if redirected(rows) is not None:
        run("I4 redirect target that is not in the spine",
            lambda rs: redirected(rs).__setitem__(
                "key_redirect_proposed_entity_id", "TRBF-NOSUCH-00"))

    write_table(tmp, rows, fields)
    rc = verify(tmp)
    print(f"          {'PASS  ' if rc == 0 else 'FAIL  '}  restored copy "
          f"verifies clean (exit {rc})")
    ok = all(c[1] for c in cases) and rc == 0
    print(f"  [1101] selftest {sum(c[1] for c in cases)}/{len(cases)} "
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
