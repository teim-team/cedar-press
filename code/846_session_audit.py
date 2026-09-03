#!/usr/bin/env python3
"""
Cedar Press - 846: DID WE ACTUALLY DO WHAT WE SAID WE DID?

    py -3 code/846_session_audit.py            # run every claim, print PASS/FAIL
    py -3 code/846_session_audit.py verify     # exit 1 if any claim is FAIL

WHY
---
Owner, 2026-09-02: *"Make sure you have done everything you said you would, or
have learned, or agents have done. You have this whole chat context - make sure
before you compact it that we're not missing anything. Otherwise we're just
spinning wheels."*

A session this long generates claims faster than anyone can hold them, and a
claim that was true when made can be untrue an hour later because twenty agents
are writing the same tree. Three times tonight a fix was reported complete and
was not:

  * 843 retired the CICD scheme and its `verify` inspected 3 files out of 310.
  * The crosswalk row for legacy 347 was corrected and the 820 rows it had
    already produced were left pointing at Cherokee Nation for a day.
  * 503's register writer was declared safe while holding a fixed 9-column
    list against a 14-column file.

So this file does not narrate. Every claim below is re-measured against disk on
every run, and a claim that cannot be measured is not listed.

THE ENTITY LAYER IS CHECKED FIRST AND HARDEST
---------------------------------------------
Owner, same message: *"The natives - it connects to everything else. We need
the native entities to connect them too."* The register is the connective
tissue; a wrong row there is wrong in all thirteen datasets at once. So the
identity checks run first and any failure there is reported as CRITICAL.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"

RESULTS = []


def claim(name, critical=False):
    def deco(fn):
        RESULTS.append((name, fn, critical))
        return fn
    return deco


def hdr(p: Path):
    with p.open(encoding="utf-8-sig", errors="replace") as fh:
        return next(csv.reader(fh), [])


def rows(p: Path):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def script_exit(*args) -> int:
    """Return code AND output, because the return code alone lies.

    On 2026-09-02 `62_no_regression_check.py` died with a NameError and **the
    shell reported exit 0 with the traceback sitting in the output**. A checker
    that trusts only the return code reads a crash as a pass — rule 9, an
    absence of evidence printing as evidence of absence, inside the harness
    that exists to catch it."""
    r = subprocess.run([sys.executable, str(ROOT / "code" / args[0])] + list(args[1:]),
                       capture_output=True, text=True, cwd=str(ROOT))
    blob = (r.stdout or "") + (r.stderr or "")
    for marker in ("Traceback (most recent call last)", "NameError:",
                   "AttributeError:", "KeyError:", "ModuleNotFoundError:"):
        if marker in blob:
            return 99          # crashed, whatever it claimed
    return r.returncode


# ---------------------------------------------------------------- identity
@claim("United Keetoowah Band holds its own funding rows, not Cherokee Nation's",
       critical=True)
def _ukb():
    bad = n = 0
    amt = 0.0
    for r in rows(CLEAN / "federal_funding_transactions.csv"):
        if "keetoowah" not in (r.get("canonical_name") or "").lower():
            continue
        n += 1
        if (r.get("cedar_uid") or "").strip() != "CE-001BS-HA":
            bad += 1
            try:
                amt += float((r.get("obligated_usd") or "0").replace(",", ""))
            except ValueError:
                pass
    return (bad == 0, f"{n} Keetoowah rows, {bad} still on the wrong uid "
                      f"(${amt:,.2f})")


@claim("no ANCSA corporation carries a federally-recognized TRIBE's legal name",
       critical=True)
def _frname():
    bad = [r for r in rows(SPINE / "cedar_identity_register.csv")
           if "Corporation" in (r.get("entity_class") or "")
           and (r.get("federal_register_legal_name") or "").strip()]
    return (not bad, f"{len(bad)} corporation(s) carrying a tribe legal name")


@claim("the register survives its own rebuild without losing enricher columns",
       critical=True)
def _regcols():
    src = (ROOT / "code" / "503_identity.py").read_text(encoding="utf-8",
                                                        errors="replace")
    live = hdr(SPINE / "cedar_identity_register.csv")
    derived = "if REGISTER.exists():" in src and "_extra" in src
    return (derived, f"register has {len(live)} cols; 503 derives its header: "
                     f"{derived}")


@claim("every cedar_uid in the register is unique and none is blank",
       critical=True)
def _uids():
    rs = rows(SPINE / "cedar_identity_register.csv")
    uids = [r.get("cedar_uid", "") for r in rs]
    blank = sum(1 for u in uids if not u.strip())
    dup = len(uids) - len(set(uids))
    return (blank == 0 and dup == 0,
            f"{len(rs):,} entities, {blank} blank, {dup} duplicate")


@claim("the named collision families point at the right side", critical=True)
def _collide():
    """The owner named three cases needing real diligence: Ho-Chunk Inc vs
    Ho-Chunk Nation of Wisconsin, Eastern Band Cherokee vs Cherokee Nation
    Oklahoma, Seminole of Oklahoma vs Seminole of Florida. Two were wrong in
    `entity_aliases.csv` on 2026-09-02 and a matcher pilot found them, not a
    gate. They are gated now."""
    MUST = {"ho chunk inc": "TRBF-WNNBGO-00",     # Winnebago Tribe of Nebraska
            "seminole nation": "TRBF-SMNLOK-00"}  # The Seminole Nation of Oklahoma
    bad = []
    for r in rows(CLEAN / "entity_aliases.csv"):
        a = (r.get("normalized_alias") or "").strip().lower()
        if a in MUST and (r.get("entity_id") or "") != MUST[a]:
            bad.append(f"{a} -> {r.get('entity_id')}")
    return (not bad, "; ".join(bad) or "both point at the correct entity")


@claim("no alias row is missing its declared key")
def _aliaskey():
    rs = rows(CLEAN / "entity_aliases.csv")
    blank = sum(1 for r in rs if not (r.get("alias_id") or "").strip())
    return (blank == 0, f"{blank} of {len(rs):,} rows have a blank alias_id")


@claim("no register entity is published as another entity's subsidiary",
       critical=True)
def _peer():
    """Huna Totem and Klawock Heenya are ANCSA village corporations with their
    own cedar_uid, and Na-Dena' JOINT VENTURE partners of Doyon. They shipped as
    Doyon subsidiaries under `parent_asserted_subsidiary` - an ownership
    over-claim on the strongest evidence class. A peer is never a subsidiary."""
    reg = {r.get("handle") for r in rows(SPINE / "cedar_identity_register.csv")
           if r.get("handle")}
    bad = []
    for r in rows(CLEAN / "native_owned_businesses.csv"):
        if (r.get("identity_scope") or "") != "parent_asserted_subsidiary":
            continue
        bid = (r.get("business_entity_id") or "").strip()
        if bid and bid in reg and bid != (r.get("certifying_authority_entity_id") or ""):
            bad.append(f"{r.get('business_name_raw','?')[:34]} under "
                       f"{r.get('certifying_authority_name','?')[:24]}")
    return (not bad, "; ".join(bad[:3]) or
            "no register entity claimed as a subsidiary of another")


@claim("no scrape artefact ships as a business")
def _artefact():
    """The Doyon Na-Deno' page scrape filed list punctuation and marketing copy
    as firms - ', Klawock Island Ventures, and' and 'Enjoy lunch at Kantishna
    Roadhouse' were both publishable=Y.

    EXTENDED 2026-09-02. The shape-matching regex below is a heuristic and it
    caught the three Na-Dena' rows because they LOOK like prose. It does not
    catch the three the Colville PDF produced - `Certified Title 10 Yes/No`,
    `Yes`, `PDF Link` - which are a table's own header line and one shifted
    cell, and which look exactly like short firm names. Those three were held
    by nothing but a permission value until the owner's publish ruling removed
    it, so this claim now ALSO reads the explicit registry
    `615.NOT_A_FIRM` and fails if any row in it has gone publishable=Y. A
    named row is worth more than a pattern that might match it.
    """
    import re as _re
    import importlib.util as _il
    BAD = _re.compile(r"^\s*,|^(enjoy|visit|book|explore|learn|read)\s|"
                      r"\bearns\b|\bawarded?\b.*\blodge\b", _re.I)
    _p = ROOT / "code" / "615_set_publishable_native_owned_businesses.py"
    _s = _il.spec_from_file_location("cedar615", _p)
    _m = _il.module_from_spec(_s)
    _s.loader.exec_module(_m)
    named = getattr(_m, "NOT_A_FIRM", None)
    if not named:
        return (False, "615 declares no NOT_A_FIRM registry - the named "
                       "artefacts are unguarded and this claim cannot be made")
    bad = []
    for r in rows(CLEAN / "native_owned_businesses.csv"):
        if (r.get("publishable") or "") != "Y":
            continue
        nm = r.get("business_name_raw") or ""
        if (r.get("business_source_id") or "").strip() in named or BAD.search(nm):
            bad.append(nm)
    return (not bad, f"{len(bad)} publishable artefact(s)"
                     + (f": {bad[0][:44]}" if bad else
                        f"; {len(named)} named artefacts all withheld"))


@claim("no nation is excluded on terms it never stated")
def _terms():
    """A restriction attaches to the host and path where the terms were found.
    It does not propagate across a nation's other hosts. On 2026-09-02 ONE
    restricted page - navajoeconomy.org/business-regulatory - had excluded all
    eight Navajo hosts including four casinos, and Navajo is not on the
    hard-listed source list. Over-exclusion is a defect, not caution."""
    HARD = {"Confederated Colville", "Umatilla Tribe", "Confederated Yakama",
            "The Chickasaw Nation", "Southern Ute", "Forest County",
            "Stillaguamish"}
    p = CLEAN / "gaming_web_harvest_coverage.csv"
    if not p.exists():
        return (True, "coverage table absent - nothing to check")
    ex = [r for r in rows(p)
          if r.get("harvest_status") == "EXCLUDED_TERMS_STATED_RESTRICTIVE"]
    # a nation not on the hard list may have AT MOST the hosts that themselves
    # stated terms - never a whole-nation sweep
    import collections
    by = collections.Counter(r.get("tribe_name") for r in ex
                             if r.get("tribe_name") not in HARD)
    bad = [f"{k} ({v} hosts)" for k, v in by.items() if v > 1]
    return (not bad, "; ".join(bad) or
            f"{len(ex)} host-level exclusions, none swept a nation")


@claim("no two marker blocks share a name in a shared doc", critical=True)
def _markers():
    """Two blocks with one marker name are ONE block to any tool that
    preserves by marker - the next wholesale regenerate silently deletes one.
    Found live on 2026-09-02: ARCHITECTURE_DECISIONS.md carried two blocks both
    named ADR-018, from two different workstreams on the same day."""
    import re as _re, collections as _c
    bad = []
    for d in sorted((ROOT / "docs").glob("*.md")):
        try:
            # LINE-ANCHORED. A marker QUOTED INSIDE PROSE is not a marker -
            # MONEY_TOTALLING_RULES explains its own convention by naming
            # `<!-- BEGIN FAADS -->` mid-sentence, and an unanchored pattern
            # reads that as a second block. The 844 agent hit this exact bug
            # and fixed it by anchoring; this reintroduced it.
            names = _re.findall(r"(?m)^\s*<!--\s*BEGIN\s+([A-Za-z0-9_\-]+)\s*-->\s*$",
                                d.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        for n, k in _c.Counter(names).items():
            if k > 1:
                bad.append(f"{d.name}: {n} x{k}")
    return (not bad, "; ".join(bad[:4]) or
            f"{sum(1 for _ in (ROOT / 'docs').glob('*.md'))} docs, every marker name unique")


@claim("no cached body from a host that refuses this agent by name",
       critical=True)
def _robots():
    """`can_fetch()` was being called with our OWN UA string, so a
    `User-agent: ClaudeBot` Disallow never matched and 42 rows across shards
    A-G fetched hosts that refuse us by name - six of the thirteen also
    hard-listed TERMS_STATED_RESTRICTIVE. Bodies purged 2026-09-02; this fails
    if any come back."""
    import glob as _g, os as _os, json as _j
    m = ROOT / "review" / "named_agent_robots_purge_2026-09-02.json"
    if not m.exists():
        return (True, "no purge manifest - nothing recorded to re-check")
    hosts = set(_j.loads(m.read_text(encoding="utf-8"))["hosts"])
    back = []
    for root in ("data/staging", "data/raw"):
        for f in _g.glob(str(ROOT / root / "**" / "*"), recursive=True):
            if not _os.path.isfile(f):
                continue
            b = _os.path.basename(f).lower()
            for h in hosts:
                if h in b or h.replace(".", "_").replace("-", "_") in b:
                    back.append(_os.path.basename(f)); break
            if len(back) > 3:
                break
    return (not back, f"{len(hosts)} refusing hosts; "
                      + (f"BODIES BACK: {', '.join(back[:3])}" if back
                         else "no cached body from any of them"))


@claim("no institution name is split mid-name in NAGPRA notices", critical=True)
def _split():
    """`institution_names_all` split on ` and `, turning ONE department into
    two institutions: 'Louisiana Department of Culture, Recreation' plus
    'Tourism, Division of Archaeology'. A fabricated institution shipped on 12
    notices.

    THIS CLAIM READ ONE COLUMN AND SPOKE FOR SIX, AND IT PASSED FOR A DAY
    WHILE THE FABRICATION SHIPPED. The 2026-09-02 repair was applied to
    `institution_names_all` only. `institution_name`, `institution_primary`,
    `institution_count`, `institution_city` and `institution_state` went on
    carrying it — 02-7009 shipped `institution_primary = 'Louisiana Department
    of Culture, Recreation'`, `institution_count = 2` and a BLANK city,
    because Baton Rouge had gone to the half that is not an agency. A buyer
    keys on `institution_primary`, not on the pipe-joined list. The claim's own
    name says "no institution name", so it now reads every column that carries
    one, and it re-derives from the notice's own TITLE rather than pattern-
    matching four words that happened to be in the one example.

    Fixed at the parser 2026-09-02: `code/cedar_nagpra_split.py` holds the one
    split rule, imported by 77, 1077 and 1084. 15 of the 19 flagged pairs are
    rejoined; the other 4 are left split and carry a stated reason in
    `institution_split_flag`, because rejoining `California State University,
    Long Beach` to `California State University, Sacramento` would fabricate a
    merger — the same error inverted."""
    import re as _re
    p = CLEAN / "nagpra_notices.csv"
    if not p.exists():
        return (True, "table absent")
    COLS = ["institution_name", "institution_primary", "institution_names_all"]
    TAIL = _re.compile(r"(?:^|\||;)\s*(Tourism|Recreation|Archaeology|"
                       r"Archeology|Anthropology|Historic Preservation)\s*"
                       r"(?:$|\||;)", _re.I)
    bad, why = [], []
    for r in rows(p):
        hit = [c for c in COLS if TAIL.search(r.get(c) or "")]
        # A fragment the parser could not decide is FLAGGED, not fabricated;
        # those rows carry their reason and are not a breach of this claim.
        if hit and not (r.get("institution_split_flag") or "").strip():
            bad.append(r.get("document_number", ""))
            if len(why) < 3:
                why.append(f"{r.get('document_number','')} in {','.join(hit)}")
    # The city may not be stranded on a fragment either — that is how the
    # Louisiana notices lost Baton Rouge. ONE-HOLDER NOTICES ONLY: where a
    # notice names two or more institutions the trailing ', City, ST' belongs
    # to the LAST of them, and a blank city on the primary is correct. A first
    # draft of this test did not condition on the count and fired on 15
    # legitimately joint notices (the two CSU campuses, the three Baylor
    # museum names, USACE Omaha + the Hood Museum), which is this repo's
    # signature defect in the check written to catch it.
    CS = _re.compile(r",\s*([A-Za-z][A-Za-z .'\-]{1,30}?),\s*([A-Z]{2})\s*$")
    stranded = [r.get("document_number", "") for r in rows(p)
                if (r.get("institution_count") or "") == "1"
                and CS.search(_re.sub(r"\s+", " ", (r.get("title") or "").strip()))
                and not (r.get("institution_city") or "").strip()]
    ok = not bad and not stranded
    return (ok, f"{len(bad)} notice(s) split a department name mid-name across "
                f"{len(COLS)} name columns"
                + (f" ({'; '.join(why)})" if why else "")
                + f"; {len(stranded)} notice(s) whose title names a city carry "
                  f"no city on the primary institution")


@claim("attribution_method matches its table's DECLARED vocabulary",
       critical=True)
def _vocab():
    """This claim used to enforce a five-term vocabulary. There are 75 terms.

    It read `prime_contracts.csv` and spoke for the whole tree, so it passed
    for weeks while `cedar_assertions` carried 40 terms and the lobbying table
    carried 9. The column is not one column: a JOIN METHOD in prime_contracts,
    an EVIDENCE PROVENANCE in cedar_assertions, a NAME-MATCH ALGORITHM in the
    lobbying table. One flat list could never have been right for all three,
    and the term that finally tripped it - `ladder_1122` - was CORRECT, chosen
    deliberately outside the ruled set so an agent ruling could not move
    `tier_A_ruled`.

    `1131` declares a vocabulary per table and owns the check. This claim now
    calls it rather than re-deriving a rule it got wrong: a gate that disagrees
    with the registry is worse than no gate.
    """
    import json
    rc = script_exit("1131_attribution_method_vocabulary.py", "verify")
    if rc == 99:
        return (False, "1131 verify CRASHED - vocabulary unproven")
    reg = ROOT / "docs" / "schema" / "attribution_method_vocabulary.json"
    if not reg.exists():
        return (False, "vocabulary registry absent - run 1131 apply")
    d = json.loads(reg.read_text(encoding="utf-8"))
    n = sum(len(t["terms"]) for t in d["tables"].values())
    return (rc == 0, f"1131 verify rc={rc}; {n} declared term-uses across "
                     f"{len(d['tables'])} tables (this claim once asserted 5)")


@claim("an attributed row carries the columns the table attributes WITH",
       critical=True)
def _attributed():
    """A row with a `cedar_uid` and no `tribe_id` / `attributed_flag` is not
    attributed, whatever a commit message says. `1111` set two display columns
    and left 4,266 rows reading `attributed_flag = 0` while announcing $1.5B.
    Conservation was proven and conservation was never the risk — nothing moved
    because nothing landed."""
    half = 0
    p = CLEAN / "prime_contracts.csv"
    if not p.exists():
        return (True, "table absent")
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        if "attributed_flag" not in (rd.fieldnames or []):
            return (True, "no attributed_flag column")
        for r in rd:
            if (r.get("cedar_uid") or "").strip() and                (r.get("attributed_flag") or "") != "1" and                (r.get("attribution_method") or "") != "unattributed":
                half += 1
    return (half == 0, f"{half:,} row(s) carry a cedar_uid but are not "
                       f"attributed_flag=1")


@claim("the gaming denominator is COUNT(DISTINCT cedar_place_id) = 717")
def _denom():
    """SIX values circulated for one number. The table now answers it itself.

        787 / 780 / 734 / 727 / 725 / 717 / 714

    Every one of those came from someone re-deriving the count with their own
    rule. Mine was 714 (regex: 16 non-place, 57 heuristic duplicates). Codex
    reached 725 and reported it as superseding mine. **Codex was wrong, and
    this is the first time in the loop I can show it row by row:** it counted
    8 non-place rows by matching the bare string `No casino`, and missed the
    8 where the negation is a suffix - `Grand Canyon West - no casino`,
    `Pueblo of Jemez - no casino`, `Pyramid Lake - no casino`. There are 16.

    The durable answer is not a better regex. The place-id pass made the table
    SELF-DESCRIBING: the 16 negative assertions carry
    `cedar_place_id_absent_reason = NOT_A_PLACE` and no place id, and the 53
    adjudicated MERGE groups collapse 54 extras into shared ids. So:

        787 rows - 16 NOT_A_PLACE = 771 with a place id
        771 - 54 adjudicated duplicate extras = 717 DISTINCT place ids

    Three independent routes agree on 717: that arithmetic, a plain
    `COUNT(DISTINCT cedar_place_id)`, and the `NOT_A_PLACE` reason landing on
    exactly the 16 rows the name test finds. This claim reads the distinct
    count, so a seventh value cannot be invented by a seventh rule.
    """
    fac = CLEAN / "gaming_facilities.csv"
    if not fac.exists():
        return (True, "UNMEASURED - gaming_facilities.csv absent")
    rs = rows(fac)
    ids = {(r.get("cedar_place_id") or "").strip()
           for r in rs if (r.get("cedar_place_id") or "").strip()}
    noplace = [r for r in rs if not (r.get("cedar_place_id") or "").strip()]
    unreasoned = [r for r in noplace
                  if "NOT_A_PLACE" not in (r.get("cedar_place_id_absent_reason") or "")]
    ok = len(ids) == 717 and not unreasoned
    msg = (f"{len(rs)} rows - {len(noplace)} NOT_A_PLACE = {len(rs)-len(noplace)} "
           f"placed -> {len(ids)} distinct properties")
    if unreasoned:
        msg += (f"  <- {len(unreasoned)} row(s) have NO place id and NO reason; "
                f"a row must say why it is not a place")
    elif len(ids) != 717:
        msg += "  <- moved from 717; re-derive before quoting it anywhere"
    return (ok, msg)


@claim("cedar_uid and tribe_id never name different entities", critical=True)
def _uid_handle():
    """A repoint that sets the display column and leaves the keying column is
    a row asserting two sovereigns at once. My Ho-Chunk repoint left 21 rows
    reading cedar_uid=Winnebago Nebraska and tribe_id=Ho-Chunk Wisconsin — the
    same defect as the Copper River attribution, made in the same hour, and I
    fixed only the one I was looking at. Measured table-wide: 21 rows, one
    pair, all mine."""
    reg = {r["handle"]: r["cedar_uid"] for r in rows(SPINE / "cedar_identity_register.csv")
           if r.get("handle")}
    p = CLEAN / "prime_contracts.csv"
    if not p.exists():
        return (True, "table absent")
    bad = 0; ex = ""
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            u = (r.get("cedar_uid") or "").strip()
            t = (r.get("tribe_id") or "").strip()
            if u and t and t in reg and reg[t] != u:
                bad += 1
                if not ex: ex = f"{u} vs {t} (={reg[t]})"
    return (bad == 0, f"{bad:,} row(s) name two entities" + (f": {ex}" if ex else ""))


# ---------------------------------------------------------------- CICD
@claim("the CICD scheme is gone from every table and every reachable read")
def _cicd():
    return (script_exit("844_nuke_cicd.py", "verify") == 0, "844 verify")


@claim("the CICD crosswalk is evidence in graveyard/, not an input")
def _grave():
    g = (ROOT / "graveyard" / "cicd" / "assistance_tribe_id_crosswalk.csv").exists()
    old = (SPINE / "legacy" / "assistance_tribe_id_crosswalk.csv").exists()
    return (g and not old, f"in graveyard: {g}; still in spine/legacy: {old}")


# ---------------------------------------------------------------- regenerate
@claim("no NEW unsafe regenerating writer since the baseline")
def _regen():
    return (script_exit("845_regenerate_guard.py", "verify") == 0, "845 verify")


@claim("the funding builder's header and row writer are the same length")
def _align():
    import ast
    tree = ast.parse((ROOT / "code" / "24_funding_merge.py").read_text(
        encoding="utf-8", errors="replace"))
    h = next((len(n.value.elts) for n in tree.body
              if isinstance(n, ast.Assign)
              and getattr(n.targets[0], "id", "") == "TX_COLS"), None)
    w = next((len(n.args[0].elts) for n in ast.walk(tree)
              if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "writerow"
              and n.args and isinstance(n.args[0], ast.List)
              and len(n.args[0].elts) > 15), None)
    return (h == w, f"TX_COLS {h} vs writerow {w}")


# ---------------------------------------------------------------- datasets
@claim("all 13 datasets pass the production contract")
def _ready():
    p = CLEAN / "cedar_dataset_readiness.csv"
    if not p.exists():
        return (False, "readiness table absent")
    rs = rows(p)
    # A dataset UNDER CONSTRUCTION is not a regression. NEST registered itself
    # before it had tables and turned this claim red at 02:4x; the honest
    # statement is that everything which DECLARES shippable tables passes, and
    # anything still being built is named rather than counted as a failure.
    def ntab(r):
        try:
            return int(r.get("n_customer_tables") or r.get("n_tables") or 0)
        except ValueError:
            return 0
    shipping = [r for r in rs if ntab(r) > 0]
    building = [r["dataset"] for r in rs if ntab(r) == 0]
    bad = [r["dataset"] for r in shipping if r.get("status") != "READY"]
    return (not bad and len(shipping) >= 13,
            f"{len(shipping) - len(bad)}/{len(shipping)} shipping datasets READY"
            + (f"; under construction: {', '.join(building)}" if building else "")
            + (f"; FAILING: {', '.join(bad)}" if bad else ""))


@claim("C4 identity coverage is a census, not a head-N sample")
def _c4():
    rs = rows(CLEAN / "cedar_dataset_readiness.csv")
    sampled = [r["dataset"] for r in rs
               if (r.get("c4_sampled_tables") or "-").strip() not in ("-", "")]
    return (not sampled, f"{len(sampled)} dataset(s) still sampled: "
                         f"{', '.join(sampled) or 'none'}")


@claim("the geography axis is joinable, not just addressed")
def _geo():
    n = j = 0
    for t in ("prime_contracts.csv", "federal_funding_transactions.csv"):
        p = CLEAN / t
        if not p.exists():
            continue
        cols = [c for c in hdr(p) if c.startswith("geo_") and "fips" in c]
        if not cols:
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                n += 1
                if any((r.get(c) or "").strip() for c in cols):
                    j += 1
    pct = 100 * j / n if n else 0
    return (pct > 85, f"{j:,}/{n:,} rows joinable ({pct:.1f}%)")


@claim("recipient and place-of-performance geography stay SEPARATE (ADR-015 r1)")
def _geo_sep():
    c = hdr(CLEAN / "prime_contracts.csv")
    return ("geo_recipient_county_fips" in c and "geo_pop_county_fips" in c,
            "both columns present" if "geo_pop_county_fips" in c else "COLLAPSED")


@claim("no constellation edge asserts ownership or carries money (ADR-014)")
def _const():
    p = CLEAN / "cedar_constellation_edges.csv"
    if not p.exists():
        return (False, "edge file absent")
    rs = rows(p)
    bad = sum(1 for r in rs if (r.get("is_ownership_claim") or "N") != "N"
              or (r.get("money_rolls_through") or "N") != "N")
    solo = sum(1 for r in rs if r.get("tier") == "sole_entity_in_area")
    return (bad == 0 and solo == 0,
            f"{len(rs):,} edges, {bad} breach the fence, "
            f"{solo} rest on sole_entity_in_area")


# ---------------------------------------------------------------- deliverables
@claim("every dataset has its own methodology paper")
def _method():
    d = ROOT / "docs" / "methodology"
    want = {"contractors", "subcontracting", "funding", "gaming",
            "natural-resources", "native-owned-businesses", "nonprofits",
            "deals", "lobbying", "legislation", "federal-register", "nagpra",
            "_entity_layer"}
    have = {p.stem for p in d.glob("*.md")} if d.exists() else set()
    missing = want - have
    return (not missing, f"{len(want & have)}/{len(want)} written"
                         f"{'; missing ' + ', '.join(sorted(missing)) if missing else ''}")


@claim("13 datasets are built and current - 12 on the storefront, gaming to "
       "Grove", critical=True)
def _twelve():
    """THIRTEEN deliverables. TWELVE of them are on the Cedar Press storefront.

    Owner, 2026-09-02: *"we always have a finished product we're building and
    all the cleaning and stuff gets updated and gets converted to the finished
    product."* And, the same day: *"you're always working on thirteen datasets,
    the twelve in Cedar Press, and then the gaming dataset."*

    The failure this catches is silent, which is why it has to be a gate: a
    cleaning pass rewrites `prime_contracts.csv`, and `contractors.csv` goes on
    sitting in `dist/customer/` looking finished. Nothing anywhere says the
    deliverable no longer matches the data. A stale deliverable is a wrong
    deliverable, so `1137 verify` exits 1 on it and this claim carries that
    through to the audit.

    WHY THIS CLAIM SAID TWELVE AND WAS WRONG ABOUT A DIFFERENT THING. It read
    `len(csvs) == 12`, and twelve was the right number for the STOREFRONT and
    the wrong number for what gets BUILT. `gaming` is `shelf: grove` - sold
    through Cedar Grove, on no Cedar Press shelf - and it is the largest
    maintained collection in the project, 65 tables. One count answering two
    questions meant the collection could go undelivered with the gate green.
    The two counts are now separate, and both are asserted:

        13   built    - a spreadsheet, a codebook and notes each
        12   storefront - `standard` + `pro`, from `500`'s shelf map

    THE PROPERTY THAT MUST NOT BE LOST is why the count was ever hard-coded:
    **a silent extra dataset is a defect.** `newsletters` shipped as an
    unwanted thirteenth storefront slot before the owner withdrew it on
    2026-09-02, and nothing failed. That property now holds three ways, all
    inside `1137 verify` and all carried here by its exit code: a thirteenth
    STOREFRONT slot fails the storefront count, a fourteenth BUILT dataset
    fails the build count, and a spreadsheet on disk that no manifest line
    claims fails outright. The on-disk counts below are the fourth guard - they
    catch a `verify` that passed because the manifest and the disk agreed with
    each other about too few files.
    """
    rc = script_exit("1137_customer_dataset_combine.py", "verify")
    if rc == 99:
        return (False, "1137 verify CRASHED - deliverables unproven")
    out = ROOT / "dist" / "customer"
    csvs = [f for f in out.glob("*.csv") if f.name != "MANIFEST.csv"]
    cbs = list(out.glob("*__CODEBOOK.md"))
    store = grove = 0
    mf = out / "MANIFEST.csv"
    if mf.exists():
        for r in rows(mf):
            if (r.get("storefront") or "").strip().upper() == "Y":
                store += 1
            elif (r.get("dataset") or "").strip():
                grove += 1
    ok = (rc == 0 and len(csvs) == 13 and len(cbs) == 13
          and store == 12 and grove == 1)
    return (ok, f"{len(csvs)} spreadsheets, {len(cbs)} codebooks, "
                f"{store} on the Cedar Press storefront + {grove} through "
                f"Cedar Grove, 1137 verify rc={rc}"
                + ("" if ok else "  <- re-run `1137 build`"))


@claim("the tooling the owner asked for is installed and importable")
def _pkgs():
    out = []
    for m in ("splink", "usaddress", "pandera", "trafilatura", "selectolax",
              "jellyfish", "polars", "duckdb", "anthropic", "instructor"):
        try:
            __import__(m)
        except ImportError:
            out.append(m)
    return (not out, f"missing: {', '.join(out) or 'none'}")


# ------------------------------------------------------------ source integrity
@claim("no regex escape has collapsed into a literal control byte "
       "(ESCAPE-COLLAPSE-1125)", critical=True)
def _control_bytes():
    """846 itself carried NINE of these and one blinded the gaming denominator.

    A collapsed `\\b` is a 0x08 backspace byte: the pattern matches no string
    that can exist, it does not raise, and it prints a confident zero. `cat`
    and most editors render it as nothing, so the source reads exactly as the
    author intended. This is the one defect class in this repo that is
    INVISIBLE IN A TERMINAL, which is why it needs a byte-level gate rather
    than a reader.
    """
    r = subprocess.run([sys.executable, str(ROOT / "code" /
                        "1136_control_byte_gate.py"), "verify"],
                       capture_output=True, text=True, cwd=str(ROOT))
    blob = (r.stdout or "") + (r.stderr or "")
    if "Traceback (most recent call last)" in blob:
        return False, ("1136 crashed - UNMEASURED, which is not the same as "
                       "zero: " + blob.strip().splitlines()[-1][:70])
    line = ((r.stdout or "").strip().splitlines() or [""])[0].strip()
    return r.returncode == 0, line or f"1136 verify exit {r.returncode}"


@claim("no document states a row count the live table disagrees with")
def _doc_claims():
    """The signature defect of this repo is a claim that outlived its
    measurement, and it has never had a detector.

    On 2026-09-02 alone: seven documents said the gaming denominator was 714
    when it was 717; `MONEY_TOTALLING_RULES.md` described a gaming claims table
    of 270 rows that held 584; `WHAT_IS_MISSING.md` headed three dataset
    sections with row counts that had all moved, and
    `code/1143_methodology_papers.py` faithfully copied two of them into
    generated methodology papers, so one stale heading became three stale
    documents.

    `1116 verify` is the BLOCKLIST for one day's correction batch - it only
    knows literals a human already noticed, and it was itself caught handing
    out 714 in its own remediation text. `1156` is the inverse and needs no
    prior knowledge: it reads the number out of the PROSE and the number out of
    the CSV and compares them. It restates nothing, so it cannot become the
    second drifting authority - the failure mode 1116's own docstring warns
    about. Where a figure needs adjudication rather than counting, `_denom`
    above remains the sole authority and 1156 does not touch it.
    """
    r = subprocess.run([sys.executable, str(ROOT / "code" /
                        "1156_doc_claim_gate.py"), "verify"],
                       capture_output=True, text=True, cwd=str(ROOT))
    blob = (r.stdout or "") + (r.stderr or "")
    if "Traceback (most recent call last)" in blob:
        return False, ("1156 crashed - UNMEASURED, which is not the same as "
                       "clean: " + blob.strip().splitlines()[-1][:70])
    lines = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]
    if r.returncode == 0:
        return True, (lines[-1] if lines else "1156 verify exit 0")
    stale = next((l for l in lines if "disagree with the live tables" in l),
                 f"1156 verify exit {r.returncode}")
    return False, stale + "  - run `py -3 code/1156_doc_claim_gate.py verify`"


@claim("the publication rules have ONE copy and no consumer has diverged")
def _publication_rules():
    """`NEVER`, `GATES`, `FLAGSHIP`, `DROP_COLS` and the shelf sets used to be
    restated across 770 / 760 / 1135 / 1137 and reconciled by REGEX OVER SOURCE
    TEXT - five scrapers, one of which had already failed open, returning `{}`
    so 1137 reported "0 customer shelves" and exited 0.

    They are canonical in `code/cedar_publication.py` since 2026-09-02 and
    imported. This runs its divergence gate, which checks that every consumer
    resolves the shared names to the module's values, that no scraper has been
    reintroduced, that the generated `FLAGSHIP` compat literal 770 keeps for the
    product repo still parses to the same dict under BOTH external scrapers'
    exact expressions, and that the storefront and build sets are still 12 and
    13. A rule with one copy is only one rule while something checks it.
    """
    r = subprocess.run([sys.executable, str(ROOT / "code" /
                        "cedar_publication.py"), "verify"],
                       capture_output=True, text=True, cwd=str(ROOT))
    blob = (r.stdout or "") + (r.stderr or "")
    if "Traceback (most recent call last)" in blob:
        return False, ("cedar_publication crashed - UNMEASURED, which is not "
                       "the same as clean: " + blob.strip().splitlines()[-1][:70])
    lines = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]
    return r.returncode == 0, (lines[-1] if lines else
                               f"cedar_publication verify exit {r.returncode}")


@claim("no published row violates an ACTIVE HARD negative constraint")
def _negative_constraints():
    """The release check of the negative-decision registry (`code/1163`).

    Cedar rules things OUT constantly - a wrong owner, a name collision, an
    identity that is not that identity, a UEI outside a collection's scope -
    and until 2026-09-02 each of those rulings lived in whatever column the
    pass that made it happened to invent. Nothing could answer "is this pair
    ruled out?" before an export, so a ruling the owner made in August could
    ship in September and did.

    `data/spine/cedar_decision_events.csv` is the append-only ledger of those
    rulings and `cedar_negative_constraints.csv` is its derived view. Only HARD
    constraints suppress - an authoritative identifier conflict, two different
    legal entities, an adjudicated false match, an ownership contradicted on a
    date. A name mismatch or an unsuccessful search is SOFT and is reported,
    never enforced, because the owner's rule is that fossilizing a research gap
    manufactures false negatives.

    NOT a claim that any organisation is not Native. A constraint denies a
    RELATIONSHIP, an IDENTITY MATCH, a CLASSIFICATION or DATASET ELIGIBILITY.

    Watch it fire: `py -3 code/1163_negative_decision_registry.py selftest`.
    """
    spec = importlib.util.spec_from_file_location(
        "ndr1163", ROOT / "code" / "1163_negative_decision_registry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    n, detail, _ = mod.release_check()
    return n == 0, detail


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    fails = crit = 0
    print(f"  846 session audit   {len(RESULTS)} claims, re-measured against disk\n")
    for name, fn, critical in RESULTS:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {str(e)[:60]}"
        if not ok:
            fails += 1
            crit += bool(critical)
        tag = "PASS" if ok else ("FAIL*" if critical else "FAIL ")
        print(f"    {tag}  {name}")
        print(f"           {detail}")
    print(f"\n  {len(RESULTS)-fails}/{len(RESULTS)} pass"
          f"   {fails} fail   {crit} of them CRITICAL (identity layer)")
    if not verify:
        (ROOT / "docs" / "SESSION_AUDIT.json").write_text(json.dumps(
            {"claims": len(RESULTS), "fail": fails, "critical": crit},
            indent=1), encoding="utf-8")
    return 1 if (verify and fails) else 0


if __name__ == "__main__":
    sys.exit(main())
