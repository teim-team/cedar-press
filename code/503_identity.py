#!/usr/bin/env python3
# lint-ok: class6 - EVERY PHASE HERE IS AN IN-PLACE ENRICHER BY DESIGN, and
# `all` runs them in the only correct order. Orderings are declared in
# cedar_pipeline.KNOWN_ORDERINGS against 24, 152 and 01. Any rebuild of a
# touched table drops what this wrote; re-run `503_identity.py all` after.
"""
Cedar Press - 503: THE IDENTITY LAYER. One script, four phases.

    py -3 code/503_identity.py all --apply     # reconcile -> mint -> stamp
    py -3 code/503_identity.py reconcile       # legacy CICD ids -> Cedar handles
    py -3 code/503_identity.py mint            # permanent cedar_uid register
    py -3 code/503_identity.py stamp           # materialise uid onto 125 tables
    py -3 code/503_identity.py verify          # coverage + validity, read-only

WHY ONE SCRIPT
--------------
These were three files (503/504/505) written the same afternoon, and that was
the script-proliferation this project already guards against with
`code_duplicate_numbers`. They are not three jobs: they are one job - "make
every row say which Native entity it is about" - in dependency order. Splitting
them meant three docstrings, three arg parsers, and three chances to run them
out of order. `all` is now the only ordering anyone needs to remember.

    reconcile  a legacy integer or a filed NAME  -> a Cedar handle (TRBF-...)
    mint       a Cedar handle                    -> a permanent cedar_uid
    stamp      every dataset row                 -> its cedar_uid, in the file

The originals are in graveyard/2026-08-29_identity_consolidation/ with their
build history. Nothing here changed except the entry point.

PHASE DOCS follow inline, each keeping the reasoning that earned it.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)


# ===================== PHASE 1: RECONCILE =====================


import csv
import io
import os
import re
import sys
from datetime import date
from pathlib import Path

SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
ALIASES = ROOT / "data" / "clean" / "entity_aliases.csv"
XWALK = ROOT / "data" / "clean" / "assistance_tribe_id_crosswalk.csv"
TABLE = ROOT / "data" / "clean" / "federal_funding_transactions.csv"
BASIS_TAG = "503_reconcile_assistance_to_cedar_ids"

GOV = {"Federally recognized tribe",
       "Federally recognized Alaska Native Village",
       "State-recognized tribe",
       "Federal-level self-governance consortium",
       # MCT constituent bands (Leech Lake, Mille Lacs, Bois Forte, Grand
       # Portage), Pleasant Point and their kin are CONSTITUENCY-class in the
       # spine. They are governments that receive assistance in their own name;
       # excluding them left $1.5B+ of obvious matches "unmatched".
       "Federal-level constituency entity",
       "State-level constituency entity"}

# Generic vocabulary: words that name WHAT a government is, not WHICH one.
# State and place words are deliberately absent - OKLAHOMA is what separates
# the Seminole Nation of Oklahoma from the Seminole Tribe of Florida.
GENERIC = {"THE", "OF", "AND", "A", "AN", "IN", "AT", "DU", "DE", "LA",
           "NATION", "NATIONS", "TRIBE", "TRIBES", "TRIBAL", "BAND", "BANDS",
           "INDIAN", "INDIANS", "NATIVE", "VILLAGE", "COMMUNITY", "COMMUNITIES",
           "RESERVATION", "RANCHERIA", "PUEBLO", "COLONY", "TOWN",
           "GOVERNMENT", "COUNCIL", "COMMITTEE", "BUSINESS", "EXECUTIVE",
           "INC", "INCORPORATED", "ORGANIZATION"}

CANON_FIX = {"STE": "SAINTE", "ST": "SAINT", "MT": "MOUNT", "FT": "FORT"}


def clean(s: str) -> str:
    s = (s or "").upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"MC ([A-Z])", r"MC", s)      # FT MC DOWELL -> MCDOWELL
    return " ".join(CANON_FIX.get(w, w) for w in s.split())


def light(s: str) -> str:
    words = [w for w in clean(s).split() if w != "THE"]
    # trailing government-suffix noise
    while words and words[-1] in ("GOVERNMENT",):
        words.pop()
    return " ".join(words)


def tokens(s: str) -> frozenset:
    return frozenset(w for w in clean(s).split() if w not in GENERIC)


# Filed names that are the SAME entity under an older or variant name,
# verified against the spine 2026-08-28 (rename, spelling, or full legal name).
# These are equivalences, not matches - the spine row already exists.
# NOT here on purpose: BARONA (-> CNSF-CPTNGR-BA?), BATTLE MOUNTAIN
# (-> CNSF-TEMOAK-BT?), PLEASANT POINT (-> Passamaquoddy constituent?) - those
# are CONSTITUENT identifications, held for an owner ruling.
RESOLUTIONS = {
    "SAN MANUEL BAND OF MISSION INDIANS": ("TRBF-YHVTSM-00", "renamed: Yuhaaviatam of San Manuel Nation"),
    "FT MC DOWELL YAVAPAI NATION": ("TRBF-FMCDWL-00", "spelling: Fort McDowell"),
    "SOKAOGAN CHIPPEWA COMMUNITY": ("TRBF-SOKGON-00", "spelling: Sokaogon"),
    "FORT SILL APACHE TRIBE": ("TRBF-FSCWSA-00", "full name: Fort Sill-Chiricahua-Warm Springs Apache"),
    "COLUSA INDIAN COMMUNITY COUNCIL": ("TRBF-CACHLD-00", "legal name: Cachil DeHe Band of Wintun Indians of the Colusa Indian Community"),
    "AROOSTOOK MICMAC COUNCIL": ("TRBF-MIKMAQ-00", "renamed: Mi'kmaq Nation"),
    "NORTHFORK RANCHERIA OF MONO INDIANS": ("TRBF-NORFRK-00", "spelling: North Fork Rancheria"),
    # --- researched edge cases, 2026-08-28 (owner directive: resolve them) ---
    # FR-combined-listing constituents and joint tribes, each grounded in the
    # spine's own modeling of the Federal Register parentheticals:
    "ONEIDA NATION": ("TRBF-ONDAWI-00",
        "state evidence: 2,208 of 2,210 rows and $890M of $890M are WI"),
    "SHOSHONE-BANNOCK TRIBES OF THE FORT HALL RESERVATION OF IDAHO": ("TRBF-FTHALL-00",
        "the FR lists ONE tribe; money to the joint government, not a band"),
    "PLEASANT POINT INDIAN RESERVATION": ("CNSF-PSMQDY-PP",
        "Sipayik/Pleasant Point constituent of the Passamaquoddy Tribe"),
    "BARONA BAND OF MISSION INDIANS": ("CNSF-CPTNGR-BA",
        "Barona Group of the Capitan Grande combined FR listing"),
    "BATTLE MOUNTAIN BAND COUNCIL": ("CNSF-TEMOAK-BT",
        "Battle Mountain Band, one of Te-Moak's four FR-parenthetical bands"),
    "BISHOP INDIAN TRIBAL COUNCIL": ("TRBF-BISHOP-00", "Bishop Paiute Tribe"),
    # Te-Moak's other three FR-parenthetical bands (Battle Mountain above):
    "ELKO BAND COUNCIL": ("CNSF-TEMOAK-EK", "Elko Band of the Te-Moak Tribe"),
    "SOUTH FORK BAND ENVIRONMENTAL": ("CNSF-TEMOAK-SF", "South Fork Band of the Te-Moak Tribe"),
    "WELLS BAND COUNCIL": ("CNSF-TEMOAK-WL", "Wells Band of the Te-Moak Tribe"),
    # Paiute Indian Tribe of Utah's FR-parenthetical bands:
    "SHIVWITS BAND OF PAIUTES": ("CNSF-PTTRUT-SW", "Shivwits Band, Paiute Indian Tribe of Utah"),
    "KANOSH BAND OF PAIUTE INDIAN": ("CNSF-PTTRUT-KN", "Kanosh Band, Paiute Indian Tribe of Utah"),
    "INDIAN PEAKS BAND OF UTAH PAIUTES": ("CNSF-PTTRUT-IP", "Indian Peaks Band, Paiute Indian Tribe of Utah"),
    # renames the filings predate:
    "NORTHWESTERN BAND OF THE SHOSHON NATION": ("TRBF-NWSSHN-00", "Northwestern Band of the Shoshone Nation (filed with a typo)"),
    "YOMBA TRIBAL COUNCIL INC": ("TRBF-YOMBAT-00", "Yomba Shoshone Tribe"),
    "CORTINA BAND OF WINTUN INDIANS": ("TRBF-KLTSLD-00", "renamed: Kletsel Dehe Wintun Nation"),
    "STEWARTS POINT RANCHERIA": ("TRBF-KASHIA-00", "Kashia Band of Pomo Indians of the Stewarts Point Rancheria"),
    # a tribally-owned ENTERPRISE, attributed to its ultimate owner per the
    # hub model - Suh'dutsing ('cedar' in Paiute) is the Cedar Band's company:
    "SUH'DUTSING TECHNOLOGIES, LLC": ("CNSF-PTTRUT-CD", "enterprise of the Cedar Band of Paiutes (ultimate-owner attribution)"),
    # NOT NATIVE - an Ohio county housing authority that carries a Delaware-
    # origin place name. Excluded, never mapped:
    "TUSCARAWAS METROPOLITAN HOUSING": (None, "EXCLUDED: Tuscarawas County OH metropolitan housing authority - not a Native entity"),
}


def build_index():
    exact = {}
    gov = []           # (distinctive tokens, tid, canonical) - gov-class only
    state_of = {}      # tid -> spine state, for the AGENTS state-agreement guard
    with SPINE.open(encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            tid = (r.get("tribe_id") or "").strip()
            cls = r.get("entity_class", "")
            names = [r.get("canonical_name", "")] + (r.get("aliases") or "").split(";")
            for nm in names:
                k = light(nm)
                if k:
                    exact.setdefault(k, set()).add((tid, cls))
            state_of[tid] = (r.get("state") or "").strip().upper()
            if cls in GOV:
                t = tokens(r.get("canonical_name", ""))
                if t:
                    gov.append((t, tid, r.get("canonical_name", "")))
    if ALIASES.exists():
        with ALIASES.open(encoding="utf-8", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                tid = (r.get("entity_id") or r.get("tribe_id") or "").strip()
                nm = r.get("alias") or r.get("alias_name") or r.get("name") or ""
                k = light(nm)
                if tid and k:
                    exact.setdefault(k, set()).add((tid, r.get("entity_class", "")))
    return exact, gov, state_of


def resolve(filed: str, exact, gov, state_of, top_states=""):
    hit = RESOLUTIONS.get(clean(filed).replace(" THE", "").strip()) or RESOLUTIONS.get((filed or "").strip().upper())
    if hit:
        if hit[0] is None:
            return None, f"EXCLUDED: {hit[1]}"
        return hit[0], f"declared equivalence: {hit[1]}"
    k = light(filed)
    c = exact.get(k, set())
    if len(c) == 1:
        return next(iter(c))[0], "exact normalized name/alias, unique"
    if len(c) > 1:
        g = {t for t, cl in c if cl in GOV}
        if len(g) == 1:
            return next(iter(g)), "exact normalized, unique among government-class"
        # AGENTS state-agreement guard: the filing's own states break the tie
        # (Oneida NY vs Oneida WI is undecidable from the name and decided by
        # the state on the money).
        st = {x.strip().upper() for x in (top_states or "").replace(";", ",").split(",") if x.strip()}
        g2 = {t for t in (g or {x for x, _ in c}) if state_of.get(t) in st}
        if len(g2) == 1:
            return next(iter(g2)), "exact normalized + state agreement (AGENTS guard)"
        return None, "AMBIGUOUS_EXACT:" + ",".join(sorted(t for t, _ in c)[:4])
    ft = tokens(filed)
    if not ft:
        return None, "no distinctive tokens"
    hits = {(tid, canon) for t, tid, canon in gov if t and t <= ft}
    # prefer the most specific candidate: drop any hit whose tokens are a
    # strict subset of another hit's tokens (e.g. 'Seminole' loses to
    # 'Seminole Oklahoma' when both are subsets of the filed name)
    if len(hits) > 1:
        toks = {tid: t for t, tid, _ in gov}
        hits = {(tid, cn) for tid, cn in hits
                if not any(o != tid and toks.get(tid, frozenset()) < toks.get(o, frozenset())
                           for o, _ in hits)}
    if len(hits) == 1:
        tid, canon = next(iter(hits))
        return tid, f"gov-class distinctive-token match on {canon!r}, unique"
    if len(hits) > 1:
        st = {x.strip().upper() for x in (top_states or "").replace(";", ",").split(",") if x.strip()}
        h2 = {(tid, cn) for tid, cn in hits if state_of.get(tid) in st}
        if len(h2) == 1:
            tid, canon = next(iter(h2))
            return tid, f"gov-class token match on {canon!r} + state agreement (AGENTS guard)"
        # coverage: the candidate whose canonical explains strictly more of the
        # filed name wins (CSKT covers CONFEDERATED+SALISH+KOOTENAI; Kootenai
        # Idaho covers one). Runs AFTER the state guard so a same-coverage,
        # different-state pair is already settled.
        pool = h2 if h2 else hits
        toks = {tid: t for t, tid, _ in gov}
        best = sorted(pool, key=lambda h: -len(toks.get(h[0], frozenset()) & ft))
        if len(best) >= 2:
            c0 = len(toks.get(best[0][0], frozenset()) & ft)
            c1 = len(toks.get(best[1][0], frozenset()) & ft)
            if c0 > c1:
                tid, canon = best[0]
                return tid, f"gov-class token match on {canon!r}, covers {c0} vs {c1} filed tokens"
        # leading-token rule: in "X Band of Y Indians", X names the tribe.
        # (Ramona Band of Cahuilla -> Ramona, not Cahuilla Band.)
        lead = clean(filed).split()
        lead = next((w for w in lead if w not in GENERIC), None)
        if lead:
            h3 = {(tid, cn) for tid, cn in pool if lead in toks.get(tid, frozenset())}
            if len(h3) == 1:
                tid, canon = next(iter(h3))
                return tid, f"gov-class token match on {canon!r}, leading filed token"
        # parent/constituent rule: when the candidates share an id stem and one
        # is the parent (-00) of the other, the filed name naming the
        # constituent's own tokens decides for the constituent.
        # (MINNESOTA CHIPPEWA TRIBE - WHITE EARTH BAND -> CNSF-MINNCH-WE.)
        stems = {}
        for tid, cn in pool:
            stems.setdefault(tid.split("-")[1] if "-" in tid else tid, []).append((tid, cn))
        if len(stems) == 1:
            fam = next(iter(stems.values()))
            kids = [(t, c) for t, c in fam if not t.endswith("-00")]
            if len(kids) == 1 and toks.get(kids[0][0], frozenset()) & ft:
                tid, canon = kids[0]
                return tid, f"constituent of same family named in filing ({canon!r})"
        return None, "AMBIGUOUS_TOKEN:" + ",".join(sorted(t for t, _ in hits)[:4])
    return None, "no candidate"


STATE_CACHE = ROOT / "data" / "interim" / "assistance_legacy_state_map.json"


def legacy_states():
    """legacy integer -> set of recipient states, measured from the table.

    The crosswalk's top_states column is blank on the rows that need the
    state-agreement guard most (CSKT, Oneida, Flandreau), so the evidence comes
    from the money itself: recipient_state_code on the lineageA-keyed rows.
    Cached; delete the cache after any rebuild of the table.
    """
    import json
    if STATE_CACHE.exists():
        return {k: set(v) for k, v in json.loads(STATE_CACHE.read_text(encoding="utf-8")).items()}
    out = {}
    with TABLE.open(encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("tribe_id_scheme_resolved") != "lineageA_dofile_integer":
                continue
            t = (row.get("tribe_id") or "").strip()
            st = (row.get("recipient_state_code") or "").strip().upper()
            if t and st:
                out.setdefault(t, set()).add(st)
    STATE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    STATE_CACHE.write_text(json.dumps({k: sorted(v) for k, v in out.items()}), encoding="utf-8")
    return out


def phase_reconcile(argv) -> int:
    apply = "--apply" in argv
    exact, gov, state_of = build_index()
    lstates = legacy_states()

    rows = list(csv.DictReader(XWALK.open(encoding="utf-8", errors="replace", newline="")))
    mapping = {}
    resolved, ambiguous, none_ = [], [], []
    for r in rows:
        st = ",".join(lstates.get(r["legacy_tribe_id"].strip(), r.get("top_states", "").split(",")))
        tid, basis = resolve(r["legacy_name_as_filed"], exact, gov, state_of, st)
        if tid:
            mapping[r["legacy_tribe_id"].strip()] = (tid, basis)
            r["proposed_cedar_tribe_id"] = tid
            r["confidence_tier"] = "A"
            r["match_basis"] = basis
            resolved.append(r)
        elif basis.startswith("AMBIGUOUS"):
            r["match_basis"] = basis
            ambiguous.append(r)
        else:
            none_.append(r)

    dd = lambda L: sum(float(x["obligated_usd"] or 0) for x in L)
    T = dd(rows) or 1
    print(f"  {len(rows)} legacy ids:")
    print(f"    RESOLVED : {len(resolved):>4}  ${dd(resolved)/1e9:6.2f}B  ({100*dd(resolved)/T:.1f}%)")
    print(f"    ambiguous: {len(ambiguous):>4}  ${dd(ambiguous)/1e9:6.2f}B")
    print(f"    unmatched: {len(none_):>4}  ${dd(none_)/1e9:6.2f}B  <- spine gaps, list below")
    for r in sorted(ambiguous, key=lambda x: -float(x["obligated_usd"] or 0))[:6]:
        print(f"      AMBIG ${float(r['obligated_usd'])/1e9:5.2f}B  {r['legacy_name_as_filed'][:44]:46} {r['match_basis'][:56]}")
    for r in sorted(none_, key=lambda x: -float(x["obligated_usd"] or 0))[:12]:
        print(f"      NONE  ${float(r['obligated_usd'])/1e9:5.2f}B  {r['legacy_name_as_filed'][:60]}")

    if not apply:
        print("\n  DRY RUN - pass --apply to write the crosswalk and the table.")
        return 0

    # ---- crosswalk, in place ----
    import shutil
    bak = str(XWALK) + f".bak_{TODAY}_pre503"
    if not os.path.exists(bak):
        shutil.copy2(XWALK, bak)
    tmp = str(XWALK) + ".part"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, XWALK)
    print(f"\n  crosswalk updated ({len(resolved)} resolved rows), backup at {os.path.basename(bak)}")

    # ---- the big table, streamed ----
    bak2 = str(TABLE) + f".bak_{TODAY}_pre503"
    if not os.path.exists(bak2):
        shutil.copy2(TABLE, bak2)
    tmp2 = str(TABLE) + ".part"
    n_upd = 0
    with TABLE.open(encoding="utf-8", errors="replace", newline="") as fin, \
         io.open(tmp2, "w", encoding="utf-8", newline="") as fout:
        rdr = csv.DictReader(fin)
        w = csv.DictWriter(fout, fieldnames=rdr.fieldnames)
        w.writeheader()
        # UEI pass (owner directive 2026-08-28: a row with a code is not
        # unattributable). The ledger row's TIER TRAVELS - the key being exact
        # says nothing about the link:
        #   A -> attribute;  X -> EXCLUDE (owner ruled NOT native - attributing
        #   these is the 317-exclusions-published-as-attributions defect);
        #   B/C -> proposals only, in the columns built for proposals.
        led = {}
        with (ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv").open(
                encoding="utf-8", errors="replace", newline="") as lf:
            for lr in csv.DictReader(lf):
                if lr.get("identifier_type") == "UEI":
                    led[(lr.get("identifier") or "").strip().upper()] = (
                        lr.get("tribe_id"), lr.get("confidence_tier"),
                        lr.get("attribution_method"))
        n_uei_a = n_uei_x = n_uei_prop = 0
        n_native = 0
        for row in rdr:
            sch = row.get("tribe_id_scheme_resolved")
            if sch == "lineageA_dofile_integer":
                hit = mapping.get((row.get("tribe_id") or "").strip())
                if hit:
                    tid, basis = hit
                    row["tribe_id_neid"] = tid
                    row["tribe_id_scheme_resolved"] = "cedar_neid"
                    row["tribe_id_scheme_resolved_basis"] = f"{basis} [{BASIS_TAG} {TODAY}]"
                    n_upd += 1
            elif sch == "cedar_neid" and not (row.get("tribe_id_neid") or "").strip():
                # THE INVARIANT: scheme cedar_neid => tribe_id_neid holds the
                # Cedar ID, on every row. The pre-503 rows kept theirs in
                # tribe_id with tribe_id_neid blank; the 503-promoted rows keep
                # the legacy integer in tribe_id. Without this backfill the one
                # scheme label covered two layouts and a consumer grouping on
                # either column silently mixed keys.
                row["tribe_id_neid"] = (row.get("tribe_id") or "").strip()
                n_native += 1
            elif sch == "unattributed":
                u = (row.get("recipient_uei") or "").strip().upper()
                hit = led.get(u)
                if hit:
                    tid, tier, method = hit
                    if tier == "A":
                        row["tribe_id_neid"] = tid
                        row["tribe_id_scheme_resolved"] = "cedar_neid"
                        row["tribe_id_scheme_resolved_basis"] = (
                            f"UEI {u} in ledger, tier A via {method} [{BASIS_TAG} {TODAY}]")
                        n_uei_a += 1
                    elif tier == "X":
                        row["tribe_id_scheme_resolved"] = "excluded_not_native"
                        row["tribe_id_scheme_resolved_basis"] = (
                            f"UEI {u} owner-ruled NOT native (tier X via {method}) [{BASIS_TAG} {TODAY}]")
                        n_uei_x += 1
                    elif not (row.get("tribe_id_neid_proposed") or "").strip():
                        row["tribe_id_neid_proposed"] = tid
                        row["tribe_id_neid_proposed_tier"] = tier
                        row["tribe_id_neid_proposed_basis"] = (
                            f"UEI {u} in ledger via {method} [{BASIS_TAG} {TODAY}]")
                        n_uei_prop += 1
            w.writerow(row)
    os.replace(tmp2, TABLE)
    print(f"  federal_funding_transactions: {n_upd:,} rows moved to cedar_neid, "
          f"{n_native:,} native backfills; UEI pass: {n_uei_a:,} tier-A attributed, "
          f"{n_uei_x:,} excluded-not-native, {n_uei_prop:,} B/C proposals; "
          f"backup at {os.path.basename(bak2)}")
    print("  legacy integers preserved in `tribe_id` as provenance.")
    return 0



# ===================== PHASE 2: MINT ==========================


import csv
import io
import os
import sys
from datetime import date
from pathlib import Path

SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
XWALK = ROOT / "data" / "clean" / "assistance_tribe_id_crosswalk.csv"

# Crockford base32: no I, L, O, U. A valid uid cannot contain an ambiguous glyph.
B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Dated former names, from docs/NATIVE_ENTITY_NUANCES.md (verified 2026-08-28).
FORMER = {
    "TRBF-YHVTSM-00": "San Manuel Band of Mission Indians (until 2022)",
    "TRBF-KLTSLD-00": "Cortina Band of Wintun Indians (until 2021)",
    "TRBF-KASHIA-00": "Stewarts Point Rancheria (historical filings)",
    "TRBF-MIKMAQ-00": "Aroostook Band of Micmacs (until 2021)",
    "TRBF-OKYOWG-00": "San Juan Pueblo (until 2005)",
    "TRBF-MHATAT-00": "MHA Nation; Mandan, Hidatsa and Arikara Nation",
    "TRBF-FSCWSA-00": "Fort Sill Apache Tribe (short form)",
    "TRBF-CACHLD-00": "Colusa Indian Community (short form)",
    "TRBF-NORFRK-00": "Northfork Rancheria (spelling variant)",
    "TRBF-SOKGON-00": "Sokaogan Chippewa Community (spelling variant)",
    "TRBF-FMCDWL-00": "Ft. McDowell Yavapai Nation (spelling variant)",
    "TRBF-NWSSHN-00": "Northwestern Band of the Shoshon Nation (filing typo)",
}


def encode(n: int) -> str:
    """Sequential int -> 5-char Crockford payload."""
    s = ""
    for _ in range(5):
        s = B32[n % 32] + s
        n //= 32
    return s


# TWO check characters, from two INDEPENDENT weightings.
#
# A single mod-32 character misses ~1 in 32 substitutions - measured 2026-08-28
# on 400 real uids: 382/400 caught, 95.5%. For an identifier a customer will
# transcribe, that is not good enough, and it costs nothing to fix while the
# uids exist only in our own files. Two characters over different weight
# sequences take random-substitution miss rate to ~1/1024, and because the
# second weighting is non-linear (squares) it catches transpositions the linear
# one is blind to.
_W1 = (2, 3, 4, 5, 6)          # linear positional
_W2 = (1, 4, 9, 16, 25)        # quadratic - different null space


def check_chars(payload: str) -> str:
    v = [B32.index(c) for c in payload]
    a = sum(w * x for w, x in zip(_W1, v)) % 32
    b = sum(w * x for w, x in zip(_W2, v)) % 32
    return B32[a] + B32[b]


def check_char(payload: str) -> str:      # kept: older callers/tests
    return check_chars(payload)


def mint(n: int) -> str:
    p = encode(n)
    return f"CE-{p}-{check_chars(p)}"


def valid(uid: str) -> bool:
    try:
        _, p, c = uid.split("-")
        return len(p) == 5 and all(ch in B32 for ch in p) and check_chars(p) == c
    except ValueError:
        return False


def selftest() -> None:
    a = mint(1234)
    assert valid(a), "mint/valid roundtrip"
    p = a.split("-")[1]
    # substitution caught
    bad = p[:2] + B32[(B32.index(p[2]) + 1) % 32] + p[3:]
    assert check_char(bad) != a.split("-")[2], "substitution must break the check"
    # transposition caught
    if p[1] != p[2]:
        tp = p[0] + p[2] + p[1] + p[3:]
        assert check_char(tp) != a.split("-")[2], "transposition must break the check"
    # the zero-for-O error is UNREPRESENTABLE: O is not in the alphabet
    assert "O" not in B32 and "I" not in B32 and "L" not in B32 and "U" not in B32
    print("  self-test OK: check digit catches substitution + transposition; "
          "O/I/L/U cannot appear in a valid uid")


def legacy_map():
    """handle -> comma-joined legacy CICD integers, from the crosswalk."""
    out = {}
    if not XWALK.exists():
        return out
    for r in csv.DictReader(XWALK.open(encoding="utf-8", errors="replace", newline="")):
        tid = (r.get("proposed_cedar_tribe_id") or "").strip()
        if tid:
            out.setdefault(tid, []).append(r["legacy_tribe_id"].strip())
    return {k: ",".join(sorted(set(v))) for k, v in out.items()}


def phase_mint(argv) -> int:
    apply = "--apply" in argv
    verify = "--verify" in argv
    selftest()

    rows = list(csv.DictReader(SPINE.open(encoding="utf-8", errors="replace", newline="")))
    handles = [(r.get("tribe_id") or "").strip() or (r.get("cedar_entity_id") or "").strip()
               for r in rows]
    assert all(handles), "spine row without any handle"
    assert len(set(handles)) == len(handles), "duplicate handles in spine"

    # APPEND-ONLY: existing register assignments are immutable.
    existing = {}
    if REGISTER.exists():
        for r in csv.DictReader(REGISTER.open(encoding="utf-8", errors="replace", newline="")):
            existing[r["handle"]] = r["cedar_uid"]
    next_n = 1 + max((int(u.split("-")[1], 32) if False else 0 for u in existing.values()), default=0)
    # decode payloads to find max sequence
    def seq(uid):
        p = uid.split("-")[1]
        n = 0
        for ch in p:
            n = n * 32 + B32.index(ch)
        return n
    next_n = 1 + max((seq(u) for u in existing.values()), default=0)

    lm = legacy_map()
    register, minted = [], 0
    for r in sorted(rows, key=lambda x: (x.get("tribe_id") or x.get("cedar_entity_id") or "")):
        h = (r.get("tribe_id") or "").strip() or (r.get("cedar_entity_id") or "").strip()
        uid = existing.get(h)
        if not uid:
            uid = mint(next_n); next_n += 1; minted += 1
        register.append({
            "cedar_uid": uid,
            "handle": h,
            "cedar_entity_id": (r.get("cedar_entity_id") or "").strip(),
            "canonical_name": r.get("canonical_name", ""),
            "entity_class": r.get("entity_class", ""),
            "class_since_basis": "as recorded at first mint 2026-08-28; a "
                                 "reclassification updates this attribute and "
                                 "retires the handle to an alias - the uid "
                                 "never changes",
            "former_names": FORMER.get(h, ""),
            "same_as_legacy_cicd": lm.get(h, ""),
            "minted": existing.get(h) and "" or TODAY,
        })

    uids = [x["cedar_uid"] for x in register]
    assert len(set(uids)) == len(uids), "uid collision"
    assert all(valid(u) for u in uids), "invalid uid minted"
    print(f"  {len(register):,} entities -> {minted:,} new uids minted "
          f"({len(existing):,} preserved from existing register)")
    print(f"  sample: {register[0]['cedar_uid']} = {register[0]['handle']} "
          f"({register[0]['canonical_name'][:30]})")
    print(f"  with former names: {sum(1 for x in register if x['former_names'])}")
    print(f"  with CICD same-as: {sum(1 for x in register if x['same_as_legacy_cicd'])}")

    if verify:
        by_handle = {x["handle"]: x["cedar_uid"] for x in register}
        for table, col in [("federal_funding_transactions.csv", "tribe_id_neid"),
                           ("gaming_facilities.csv", "tribe_id")]:
            p = ROOT / "data" / "clean" / table
            n = hit = 0
            with p.open(encoding="utf-8", errors="replace", newline="") as f:
                for row in csv.DictReader(f):
                    v = (row.get(col) or "").strip()
                    if v:
                        n += 1
                        if v in by_handle:
                            hit += 1
            print(f"  TRANSITIVE: {table}.{col}: {hit:,}/{n:,} "
                  f"({100*hit/max(n,1):.1f}%) resolve to a permanent uid")
        return 0

    if not apply:
        print("\n  DRY RUN - pass --apply to write the register and enrich the spine.")
        return 0

    import shutil
    tmp = str(REGISTER) + ".part"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(register[0].keys()))
        w.writeheader(); w.writerows(register)
    os.replace(tmp, REGISTER)
    print(f"  wrote {REGISTER.relative_to(ROOT)}")

    by_handle = {x["handle"]: x["cedar_uid"] for x in register}
    bak = str(SPINE) + f".bak_{TODAY}_pre504"
    if not os.path.exists(bak):
        shutil.copy2(SPINE, bak)
    fields = list(rows[0].keys())
    if "cedar_uid" not in fields:
        fields.append("cedar_uid")
    tmp = str(SPINE) + ".part"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            h = (r.get("tribe_id") or "").strip() or (r.get("cedar_entity_id") or "").strip()
            r["cedar_uid"] = by_handle.get(h, "")
            w.writerow(r)
    os.replace(tmp, SPINE)
    print(f"  spine enriched with cedar_uid (backup {os.path.basename(bak)})")
    print("  every dataset that joins tribe_id -> spine now resolves to the "
          "permanent identity transitively. Run --verify.")
    return 0



# ===================== PHASE 3: STAMP =========================


import csv
import io
import os
import shutil
import sys
from datetime import date
from pathlib import Path

CLEAN = ROOT / "data" / "clean"
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"


# Preference order: the first present in a header is the entity column.
ID_COLS = ("cedar_uid_source", "tribe_id_neid", "tribe_id", "entity_id",
           "cedar_entity_id", "native_entity_id", "resolved_native_entity_id",
           "tribe_entity_id", "recipient_entity_id",
           "cedar_recipient_spine_entity_id", "operator_entity_id",
           "resolved_entity_id", "native_party_entity_id",
           "prime_native_tribe_id", "surrogate_entity_id", "nho_id",
           "acquirer_tribe_id", "parent_native_entity")


def register_map():
    """handle -> uid, INCLUDING the retired CICD integers.

    Two panels (federal_funding_tribe_year_panel, entity_evidence_profile) were
    built before the reconciliation and still key on bare lineage-A integers.
    The register carries `same_as_legacy_cicd` for exactly this reason: a
    retired scheme still has to RESOLVE, or the old panels are orphaned from
    the identity they belong to. The integer is never re-adopted as an identity
    - it is only ever read.
    """
    m, legacy = {}, {}
    with REGISTER.open(encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            uid = r["cedar_uid"]
            for k in ("handle", "cedar_entity_id"):
                v = (r.get(k) or "").strip()
                if v:
                    m[v] = uid
            for old in (r.get("same_as_legacy_cicd") or "").split(","):
                old = old.strip()
                if old:
                    # a legacy integer claimed by two entities is ambiguous and
                    # is dropped rather than resolved by first-wins
                    legacy.setdefault(old, set()).add(uid)
    contested = []
    for old, uids in legacy.items():
        if len(uids) == 1:
            m.setdefault(old, next(iter(uids)))
        else:
            contested.append((old, sorted(uids)))
    for old, uids in sorted(contested):
        print(f"  legacy integer {old!r} claimed by {len(uids)} entities "
              f"({', '.join(uids[:3])}) - left unresolved, never first-wins")
    return m


def entity_col(path: Path):
    try:
        with path.open(encoding="utf-8", errors="replace", newline="") as f:
            hdr = next(csv.reader(f), [])
    except Exception:
        return None, []
    for c in ID_COLS:
        if c in hdr:
            return c, hdr
    return None, hdr


def phase_stamp(argv) -> int:
    apply = "--apply" in argv
    verify = "--verify" in argv
    try:
        import cedar_codebook as CB
        licensed = set(CB.LICENSED_SOURCE_FILES)
    except Exception:
        licensed = set()

    reg = register_map()
    print(f"  register: {len(set(reg.values())):,} entities, {len(reg):,} handles\n")

    stamped = 0
    skipped: list[str] = []
    rows_total = rows_hit = 0
    unknown_examples = {}
    report = []

    for p in sorted(CLEAN.glob("*.csv")):
        if ".bak_" in p.name or p.name.endswith(".part") or p.name in licensed:
            continue
        col, hdr = entity_col(p)
        if not col:
            skipped.append(p.name)
            continue
        # cedar_uid is DERIVED, so an existing column is re-stamped, never
        # skipped. Skipping would freeze a stale uid into a shipped dataset the
        # first time the register legitimately changes - which happened the same
        # day it was built, when the check character went from one char to two.

        n = hit = 0
        unk = set()
        try:
            if apply:
                bak = str(p) + f".bak_{TODAY}_pre505"
                if not os.path.exists(bak):
                    shutil.copy2(p, bak)
                tmp = str(p) + ".part"
                with p.open(encoding="utf-8", errors="replace", newline="") as fin, \
                     io.open(tmp, "w", encoding="utf-8", newline="") as fout:
                    rdr = csv.DictReader(fin)
                    fields = list(rdr.fieldnames or [])
                    if "cedar_uid" not in fields:
                        fields.append("cedar_uid")
                    w = csv.DictWriter(fout, fieldnames=fields)
                    w.writeheader()
                    for row in rdr:
                        v = (row.get(col) or "").strip()
                        if v:
                            n += 1
                            uid = reg.get(v)
                            if uid:
                                row["cedar_uid"] = uid; hit += 1
                            else:
                                row["cedar_uid"] = ""
                                if len(unk) < 3:
                                    unk.add(v)
                        else:
                            row["cedar_uid"] = ""
                        w.writerow(row)
                os.replace(tmp, p)
            else:
                with p.open(encoding="utf-8", errors="replace", newline="") as f:
                    for row in csv.DictReader(f):
                        v = (row.get(col) or "").strip()
                        if v:
                            n += 1
                            if reg.get(v):
                                hit += 1
                            elif len(unk) < 3:
                                unk.add(v)
        except Exception as e:
            report.append((p.name, col, -2, -2))
            print(f"    ERROR {p.name}: {type(e).__name__}")
            continue

        stamped += 1
        rows_total += n
        rows_hit += hit
        if unk:
            unknown_examples[p.name] = sorted(unk)
        report.append((p.name, col, n, hit))

    print(f"  tables carrying an entity column : {stamped:,}")
    print(f"  tables with none (skipped)       : {len(skipped):,}")
    print(f"  entity-bearing rows              : {rows_total:,}")
    print(f"  resolved to a permanent uid      : {rows_hit:,} "
          f"({100*rows_hit/max(rows_total,1):.1f}%)")
    print()
    worst = sorted((r for r in report if r[2] > 0 and r[3] < r[2]),
                   key=lambda r: (r[3] / r[2]))[:10]
    if worst:
        print("  lowest coverage - handles not in the register (blank, never guessed):")
        for name, col, n, hit in worst:
            ex = ", ".join(unknown_examples.get(name, [])[:2])
            print(f"    {name[:44]:46} {col:22} {hit:>7,}/{n:<7,} "
                  f"{100*hit/n:5.1f}%  e.g. {ex[:40]}")
    if apply:
        print(f"\n  stamped {stamped} tables. Backups: *.bak_{TODAY}_pre505")
    elif not verify:
        print("\n  DRY RUN - pass --apply to stamp.")
    return 0




def main() -> int:
    ap = argparse.ArgumentParser(description="Cedar identity layer")
    ap.add_argument("phase", choices=["all", "reconcile", "mint", "stamp", "verify"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-mb", type=float, default=1200.0)
    a, extra = ap.parse_known_args()
    argv = sys.argv[:]

    if a.phase == "verify":
        return phase_mint(["--verify"]) or phase_stamp(["--verify"])
    if a.phase == "reconcile":
        return phase_reconcile(argv)
    if a.phase == "mint":
        return phase_mint(argv)
    if a.phase == "stamp":
        return phase_stamp(argv)

    # all: the only correct order, and the reason this is one script
    for name, fn in (("reconcile", phase_reconcile), ("mint", phase_mint),
                     ("stamp", phase_stamp)):
        print("")
        print("=== " + name.upper() + " ===")
        rc = fn(argv)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
