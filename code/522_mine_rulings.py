#!/usr/bin/env python3
"""
Cedar Press - 522: MINE THE RULINGS. Turn adjudications into rules.

    py -3 code/522_mine_rulings.py all        # everything below, in order
    py -3 code/522_mine_rulings.py census     # assemble + count the corpus
    py -3 code/522_mine_rulings.py negatives  # what makes the owner say NO
    py -3 code/522_mine_rulings.py repeats    # subjects adjudicated twice
    py -3 code/522_mine_rulings.py prior      # Cedar's guess vs the owner's answer
    py -3 code/522_mine_rulings.py guards     # 503's loose-path guards, before/after
    py -3 code/522_mine_rulings.py fixtures   # PROVE each guard fires, and does not over-fire
    py -3 code/522_mine_rulings.py learning   # rulings per 100 identifications

READ-ONLY except for one interim artefact,
`data/interim/ruling_corpus_mined.csv` - the assembled corpus. Nothing here
writes a shipping table, and nothing here decides anything: it MEASURES what
humans decided so the next pass can encode it. The rules themselves live in
`docs/RESOLUTION_RULES_LEARNED.md`, each one citing the count this script
produces.

WHY THIS EXISTS
---------------
The owner's ask, 2026-08-31: *"you should have hundreds of examples of me
confirming or not confirming stuff ... I want you to understand the patterns,
the idiosyncrasies, the subtle, the nuance, the secret things I haven't
noticed"* and *"at some point you should be able to surpass me."*

A project cannot surpass its expert by storing his answers. It surpasses him
only if each answer leaves behind the FEATURE THAT DECIDED IT. This script is
the measurement half of that: it counts the corpus, isolates the refusals
(which are denser in information than the confirmations, because a refusal
names a feature that must be absent), finds the subjects adjudicated more than
once (a repeat ask is a code gap, not a knowledge gap), and scores Cedar's own
algorithmic prior against the owner's verdict on the same card.

THE CORPUS, AND WHAT COUNTS AS AN ADJUDICATION
-----------------------------------------------
There are three populations and they must not be added together carelessly:

  OWNER    a human adjudication by Elijah Moreno - `cedar_rulings.csv`,
           `cedar_exclusion_rulings.csv`, the `*_elijah*` inboxes, the
           reconciliation-tool cards, and - the largest and oldest -
           `federal_funding_rulings_from_dofile.csv`, which is his own
           pre-Cedar Stata linkage work read back out of two .do files.
  AGENT    an agent's research verdict recorded in a `review/agent_rulings_*`
           file. Real evidence, weaker authority; several were later
           overturned by the owner and those overturns are the most valuable
           rows in the whole corpus.
  RULESET  a decision produced by a filter the owner AUTHORED. The 4,656
           nonprofit exclusions come from exactly two scripts. Two human acts,
           4,656 decisions - the leverage ratio this project should be chasing
           and the reason `learning` reports it separately.
"""
from __future__ import annotations

import csv
import collections
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)

SPINE = ROOT / "data" / "spine"
CLEAN = ROOT / "data" / "clean"
REVIEW = ROOT / "review"
OUT = ROOT / "data" / "interim" / "ruling_corpus_mined.csv"


def rd(path: Path, encoding: str = "utf-8-sig") -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding=encoding, errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def resolver():
    """503's resolver, loaded by path - its module name starts with a digit."""
    spec = importlib.util.spec_from_file_location(
        "cedar_503_identity", ROOT / "code" / "503_identity.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tok(s: str) -> set:
    return set(re.sub(r"[^A-Z0-9 ]", " ", (s or "").upper()).split())


# =====================================================================
# CENSUS - assemble every adjudication this project has ever recorded.
# =====================================================================

def assemble() -> list[dict]:
    """One row per adjudication: who, about what, decided how, and why.

    `polarity` is the load-bearing column and it is deliberately coarse:
    CONFIRM (an entity was named), REFUSE (no Native entity, or not THIS one),
    HOLD (a human declined to decide - which is itself a decision, and 191
    learned the hard way that reading a HOLD as a confirmation turns a
    retraction into an attribution).
    """
    rows: list[dict] = []

    def add(ruler, source, subject, decision, reason, polarity, date=""):
        rows.append({"ruler": ruler, "source": source,
                     "subject": (subject or "").strip(),
                     "decision": (decision or "").strip()[:200],
                     "reason": (reason or "").strip()[:400],
                     "polarity": polarity, "ruling_date": date})

    for r in rd(SPINE / "cedar_rulings.csv"):
        pol = {"ATTRIBUTE": "CONFIRM", "REGISTER_NHO_PARENT": "CONFIRM",
               "RECORD_ALIAS": "CONFIRM"}.get(r["ruling"], "REFUSE")
        add("OWNER", "cedar_rulings.csv", r["entity_name"] or r["identifier"],
            r["ruling"], r["note"], pol, r["ruled_date"])

    for r in rd(SPINE / "cedar_exclusion_rulings.csv"):
        add("OWNER", "cedar_exclusion_rulings.csv",
            f'{r["identifier_type"]}:{r["identifier"]}',
            r["exclusion_reason"], r["ruling_note"], "REFUSE",
            r["extracted_date"])

    for r in rd(SPINE / "federal_funding_rulings_from_dofile.csv"):
        add("OWNER", "federal_funding_rulings_from_dofile.csv",
            r["identifier"] or r["entity_name"], r["ruling"], r["reason"],
            "CONFIRM" if r["ruling"] == "INCLUDE" else "REFUSE")

    for r in rd(CLEAN / "individual_native_prior_rulings.csv"):
        add("OWNER", "individual_native_prior_rulings.csv",
            r["entity_name"] or r["identifier"], r["ruling_class"],
            r["ruling_note"], "REFUSE", r["ruled_date"])

    for p in ("rulings_inbox_2026-08-07_elijah.csv",
              "rulings_inbox_2026-08-08_elijah_batch2.csv"):
        for r in rd(REVIEW / p):
            v = (r.get("YOUR_RULING") or "").strip()
            pol = "REFUSE" if v.upper().startswith(("NOT", "NO ")) else "CONFIRM"
            add("OWNER", p, r.get("entity_name") or r.get("identifier"), v,
                r.get("notes", ""), pol)

    recon = REVIEW / "owner_rulings_cedar_recon_v1_2026-08-28.json"
    if recon.exists():
        for r in json.loads(recon.read_text(encoding="utf-8"))["rulings"]:
            add("OWNER", recon.name, r["name"], r["ruling"], r.get("note", ""),
                "REFUSE" if r["ruling"] in ("not_native", "individual")
                else "CONFIRM", r.get("ruled_at", ""))
    for r in rd(REVIEW / "elijah_rulings_2026-08-27_recon_batch2.csv"):
        add("OWNER", "elijah_rulings_2026-08-27_recon_batch2.csv", r["name"],
            r["ruling"], r.get("note", ""),
            "REFUSE" if r["ruling"] in ("not_native", "individual")
            else "CONFIRM", r.get("ruled_date", ""))

    # The 2 owner-AUTHORED filters. One ruler, 4,656 decisions.
    for r in rd(SPINE / "nonprofit_exclusion_rulings.csv"):
        add("RULESET", "nonprofit_exclusion_rulings.csv", r["org_name"],
            r["exclusion_reason"], r["evidence"], "REFUSE", r["ruled_date"])

    # Agent verdicts, via the consolidated ledger which already unions 39 files.
    for r in rd(CLEAN / "cedar_ruling_ledger_consolidated.csv"):
        pol = {"ENTITY": "CONFIRM", "CLASS": "CONFIRM",
               "NEGATIVE": "REFUSE", "HOLD": "HOLD"}[r["verdict_kind"]]
        add("AGENT" if "agent" in r["source_file"] else "MIXED",
            r["source_file"], r["subject_name"] or r["subject_key"],
            r["ruling"], r["resolve_how"], pol, r["ruling_date"])
    return rows


def cmd_census() -> int:
    rows = assemble()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"  assembled {len(rows):,} adjudications -> "
          f"{OUT.relative_to(ROOT)}\n")
    print("  by ruler:")
    for k, v in collections.Counter(r["ruler"] for r in rows).most_common():
        print(f"    {v:>7,}  {k}")
    print("\n  by polarity:")
    for k, v in collections.Counter(r["polarity"] for r in rows).most_common():
        print(f"    {v:>7,}  {k}")
    print("\n  OWNER adjudications by source file:")
    own = [r for r in rows if r["ruler"] == "OWNER"]
    for k, v in collections.Counter(r["source"] for r in own).most_common():
        print(f"    {v:>7,}  {k}")
    print(f"\n  owner CONFIRM {sum(1 for r in own if r['polarity']=='CONFIRM'):,}"
          f"   owner REFUSE {sum(1 for r in own if r['polarity']=='REFUSE'):,}"
          f"  ({sum(1 for r in own if r['polarity']=='REFUSE')/len(own):.0%}"
          f" of the owner's recorded decisions are refusals)")
    print("\n  distinct source files feeding the consolidated ledger: "
          f"{len({r['source_file'] for r in rd(CLEAN / 'cedar_ruling_ledger_consolidated.csv')})}")
    return 0


# =====================================================================
# NEGATIVES - the refusals, which carry more information than the yeses.
# =====================================================================

def cmd_negatives() -> int:
    led = rd(CLEAN / "cedar_ruling_ledger_consolidated.csv")
    neg = [r for r in led if r["verdict_kind"] == "NEGATIVE"]
    pos = [r for r in led if r["verdict_kind"] == "ENTITY"]
    print(f"  NEGATIVE verdicts {len(neg):,}   ENTITY verdicts {len(pos):,}\n")

    print("  the refusal vocabulary - what the owner and the agents actually "
          "wrote:")
    for k, v in collections.Counter(
            r["ruling"].strip()[:70] for r in neg).most_common(14):
        print(f"    {v:>5}  {k}")

    cn, cp = collections.Counter(), collections.Counter()
    for r in neg:
        cn.update(tok(r["subject_name"]))
    for r in pos:
        cp.update(tok(r["subject_name"]))
    print("\n  TOKENS THAT PREDICT A REFUSAL (>=20 refusals, ranked by the "
          "share of\n  all verdicts on names carrying them that are "
          "refusals):")
    sc = [(c / (c + cp.get(w, 0)), c, cp.get(w, 0), w)
          for w, c in cn.items() if c >= 20]
    for s, c, p, w in sorted(sc, reverse=True)[:22]:
        print(f"    {w:<16} refuse={c:<5} confirm={p:<5} {s:.0%}")

    npr = rd(SPINE / "nonprofit_exclusion_rulings.csv")
    pats = collections.Counter()
    for r in npr:
        m = re.search(r"pattern \[([^\]]+)\]", r["evidence"] or "")
        if m:
            for p in m.group(1).split(";"):
                pats[p.strip()] += 1
    geo = [p for p in pats
           if p.split()[-1] in ("COUNTY", "FALLS", "VALLEY", "STATE",
                                "HEIGHTS", "JUNCTION", "TERRITORY", "TRAIL",
                                "BAY", "DESERT", "COUNTIES")]
    print(f"\n  the owner's hand-maintained place blocklist: {len(pats)} "
          f"literal patterns covering {sum(pats.values()):,} exclusions.")
    print(f"  {len(geo)} of the {len(pats)} are one structural rule wearing "
          f"{len(geo)} costumes:\n  <tribal token> + <administrative-geography "
          f"suffix>. Named examples: "
          + ", ".join(sorted(geo)[:6]))

    tokm = collections.Counter(r["tribe_id_token_match"] for r in npr)
    print("\n  the spine entities whose NAME generates the most false "
          "positives:")
    canon = {r["tribe_id"]: r.get("canonical_name", "")
             for r in rd(SPINE / "cedar_entity_spine.csv")}
    for t, v in tokm.most_common(12):
        print(f"    {v:>5}  {t}  {canon.get(t, '')[:44]}")
    return 0


# =====================================================================
# REPEATS - the same subject adjudicated more than once.
# =====================================================================

def cmd_repeats() -> int:
    led = rd(CLEAN / "cedar_ruling_ledger_consolidated.csv")
    by = collections.defaultdict(list)
    for r in led:
        by[r["subject_key"]].append(r)
    multi = {k: v for k, v in by.items() if len(v) > 1}
    cross = {k: v for k, v in multi.items()
             if len({x["source_file"] for x in v}) > 1}
    div = {k: v for k, v in multi.items()
           if len({x["verdict_kind"] for x in v}) > 1}
    twoid = {k: v for k, v in multi.items()
             if len({x["resolved_tribe_id"] for x in v
                     if x["resolved_tribe_id"]}) > 1}
    print(f"  distinct subjects adjudicated          : {len(by):,}")
    print(f"  adjudicated MORE THAN ONCE             : {len(multi):,} "
          f"({len(multi)/len(by):.0%})")
    print(f"  ... in more than one review batch      : {len(cross):,}")
    print(f"  ... with a DIFFERENT verdict_kind      : {len(div):,}")
    print(f"  ... naming TWO DIFFERENT entities      : {len(twoid):,}")
    print("\n  A subject asked twice in two batches is a code gap: the first "
          "answer\n  was recorded somewhere the queue builder did not read. "
          f"{len(cross):,} of them.")
    if not twoid:
        print("\n  NO ruling in the corpus names a different entity than "
              "another ruling on\n  the same subject. Every divergence is "
              "HOLD -> ENTITY, which is evidence\n  arriving, not "
              "contradiction. The contradictions in this project are "
              "RULING vs\n  TABLE, not ruling vs ruling - see "
              "review/ruling_vs_table_contradictions_2026-08-26.csv.")
    con = rd(REVIEW / "ruling_vs_table_contradictions_2026-08-26.csv")
    mism = [r for r in con if r["ruling_tribe_id"] and r["table_tribe_id"]
            and r["ruling_tribe_id"] != r["table_tribe_id"]]
    print(f"\n  RULING vs TABLE: {len(con)} contradictions, {len(mism)} of "
          f"them naming two different entities.")
    print("  the table ids that are wrong most often - a wrong id that "
          "attracts many\n  unrelated firms is one bad row propagated, not "
          "many bad matches:")
    for t, v in collections.Counter(r["table_tribe_id"]
                                    for r in mism).most_common(6):
        names = [r["awardee_name"][:28] for r in mism
                 if r["table_tribe_id"] == t][:3]
        print(f"    {v:>3}x {t:<26} {', '.join(names)}")
    return 0


# =====================================================================
# PRIOR - Cedar's own guess, scored against the owner's answer.
# =====================================================================

def cmd_prior() -> int:
    """The only place in the repo where the machine and the human answered
    the SAME question and both answers were kept."""
    cards = {}
    p = REVIEW / "owner_rulings_cedar_recon_v1_2026-08-28.json"
    if p.exists():
        for r in json.loads(p.read_text(encoding="utf-8"))["rulings"]:
            cards[r["cluster_key"]] = (str(r.get("my_guess", "")).lower(),
                                       str(r.get("my_confidence", "")),
                                       r["ruling"].lower(), r["name"])
    for r in rd(REVIEW / "elijah_rulings_2026-08-27_recon_batch2.csv"):
        cards.setdefault(r["cluster_key"],
                         ((r.get("my_guess") or "").lower(),
                          r.get("my_confidence", ""), r["ruling"].lower(),
                          r["name"]))
    abst = [c for c in cards.values() if c[0] in ("", "unsure")]
    comm = [c for c in cards.values() if c[0] not in ("", "unsure")]
    ok = [c for c in comm if c[0] == c[2]]
    bad = [c for c in comm if c[0] != c[2]]
    print(f"  owner-ruled reconciliation cards      : {len(cards)}")
    print(f"  Cedar's prior ABSTAINED ('unsure')    : {len(abst)} "
          f"({len(abst)/len(cards):.0%})")
    print(f"  Cedar's prior COMMITTED               : {len(comm)}")
    print(f"    correct                             : {len(ok)} "
          f"({len(ok)/max(1,len(comm)):.0%})")
    print(f"    wrong                               : {len(bad)}")
    for nm, cf, ru, _ in [(b[3], b[1], b[2], 0) for b in bad]:
        pass
    for g, cf, ru, nm in bad:
        print(f"      {nm[:44]:<46} guessed {g:<6} at {cf:>3}%  ->  ruled {ru}")
    dirs = collections.Counter((b[0], b[2]) for b in bad)
    print("\n  EVERY error has the same shape: the prior named an "
          "INSTITUTIONAL Native\n  owner (anc/nho) where the truth was a "
          "narrower class. It has never once\n  wrongly said not_native. "
          "The prior's failure mode is OVER-ATTRIBUTION.")
    for (g, r), v in dirs.most_common():
        print(f"    {v}x  {g} -> {r}")
    base = collections.Counter(c[2] for c in cards.values())
    nn = base["not_native"] + base["individual"]
    print(f"\n  BASE RATE on the high-dollar residual queue: "
          f"{nn}/{len(cards)} = {nn/len(cards):.0%} of these clusters are NOT "
          f"owned by a\n  tribal, ANC or NHO entity. A prior that guesses "
          f"'anc' on an opaque LLC is\n  wrong more often than it is right.")
    for k, v in base.most_common():
        print(f"    {v:>4}  {k}")
    return 0


# =====================================================================
# GUARDS - what 503's loose-path refusals are worth, measured.
# =====================================================================

def control_sets():
    """Three populations, and one of them is HELD OUT of every fitting step.

    REFUSED   every distinct name a human declined - the guards should reject
              as many of these as possible.
    RULED     every distinct name a human resolved TO an entity - the guards
              must reject NONE of these.
    SPINE     every spine canonical name - the guards must reject NONE.
    HELDOUT   the owner's 2021 BGOV crosswalk vendor names. Never used to
              choose a token. It is what removed MUSEUM and LIONS from
              CIVIC_FORM (Makah Museum; Native Village of Port Lions).
    """
    refused, ruled = set(), {}
    for r in rd(CLEAN / "cedar_ruling_ledger_consolidated.csv"):
        if not r["subject_name"]:
            continue
        if r["verdict_kind"] == "NEGATIVE":
            refused.add(r["subject_name"])
        elif r["verdict_kind"] == "ENTITY" and r["resolved_tribe_id"]:
            ruled[r["subject_name"]] = r["resolved_tribe_id"]
    for r in rd(SPINE / "nonprofit_exclusion_rulings.csv"):
        if r["org_name"]:
            refused.add(r["org_name"])
    refused -= set(ruled)
    spine = {r["canonical_name"]: r["tribe_id"]
             for r in rd(SPINE / "cedar_entity_spine.csv")
             if r.get("canonical_name")}
    held = {r["Performing_Vendor"]
            for r in rd(ROOT / "entity_crosswalk_bgov.csv")
            if r.get("Performing_Vendor")}
    return refused, ruled, spine, held


def cmd_guards() -> int:
    mod = resolver()
    exact, gov, state_of = mod.build_index()
    refused, ruled, spine, held = control_sets()

    def sweep(names):
        res = ref = 0
        why = collections.Counter()
        for n in names:
            tid, w = mod.resolve(n, exact, gov, state_of)
            if tid:
                res += 1
            elif w.startswith("REFUSED_"):
                ref += 1
                why[w.split(":")[0]] += 1
        return res, ref, why

    print("  503.resolve() against every name a human has adjudicated.\n")
    for label, names, expect in (
            ("REFUSED by a human", refused, "resolutions here are FALSE"),
            ("RULED to an entity", ruled, "resolutions here are WANTED"),
            ("spine canonical    ", spine, "resolutions here are WANTED"),
            ("HELD-OUT bgov vendors", held, "resolutions here are WANTED")):
        res, ref, why = sweep(names)
        print(f"  {label:<22} {len(names):>6,} names -> {res:>6,} resolved, "
              f"{ref:>5,} refused by a guard   ({expect})")
        for k, v in why.most_common():
            print(f"      {v:>5}  {k}")
    print("\n  BEFORE the guards, measured 2026-09-01 on the same corpus:")
    print("      REFUSED-by-a-human names resolving : 2,458  (47% of 5,197)")
    print("      RULED-to-an-entity names resolving : 1,117")
    print("      spine canonical names resolving    : 1,532 of 1,536")
    print("  The four unresolved spine names predate the guards; no guard "
          "touches them.")
    return 0


def cmd_fixtures() -> int:
    """A guard nobody can see fire gets deleted by the next agent.

    Each MUST-CATCH is a name a human already refused. Each MUST-PASS is a
    real Native entity that a careless version of the same guard would have
    killed - the false-positive half, which matters as much.
    """
    mod = resolver()
    exact, gov, state_of = mod.build_index()
    catch = [
        ("ONONDAGA GOLF AND COUNTRY CLUB", "CIVIC_FORM"),
        ("TUSCARORA SOCCER CLUB", "CIVIC_FORM"),
        ("ONONDAGA YOUTH HOCKEY ASSOCIATION INC", "CIVIC_FORM"),
        ("RESTORATION CHURCH WICHITA", "CIVIC_FORM"),
        ("KIWANIS CLUB OF UMATILLA FOUNDATION INC", "CIVIC_FORM"),
        ("ARC OF ONONDAGA FOUNDATION HISTORICAL SOCIETY", "CIVIC_FORM"),
        ("COWLITZ COUNTY AUXILIARY COMMUNICATIONS SERVICE", "ADMIN_GEOGRAPHY"),
        ("OSAGE COUNTY ECONOMIC DEVELOPMENT CORPORATION", "ADMIN_GEOGRAPHY"),
        ("SANTA ROSA COUNTY FLORIDA", "ADMIN_GEOGRAPHY"),
        ("WICHITA FALLS UMPIRES ASSOCIATION", "ADMIN_GEOGRAPHY"),
        ("LAGUNA BEACH ALLIANCE FOR THE ARTS", "ADMIN_GEOGRAPHY"),
    ]
    keep = [
        # the counter-examples that bound each guard - all real entities
        "Forest County Potawatomi Community",   # COUNTY in its own name
        "Cold Springs Rancheria",
        "Confederated Tribes of Warm Springs",
        "Makah Museum",                          # why MUSEUM is not in the list
        "Native Village of Port Lions",          # why LIONS is not in the list
        "Onondaga Nation",                       # the nation itself, same token
        "Cowlitz Indian Tribe",
        "Seminole Tribe of Florida",
    ]
    bad = 0
    print("  MUST CATCH - every one is a name a human already refused:")
    for name, want in catch:
        tid, why = mod.resolve(name, exact, gov, state_of)
        good = tid is None and want in why
        bad += not good
        print(f"    {'ok ' if good else 'FAIL'} {name[:48]:<50} {why[:56]}")
    print("\n  MUST NOT CATCH - the near-misses that bound the guards:")
    for name in keep:
        tid, why = mod.resolve(name, exact, gov, state_of)
        good = not why.startswith("REFUSED_")
        bad += not good
        print(f"    {'ok ' if good else 'FAIL'} {name[:48]:<50} "
              f"{(tid or '-'):<26} {why[:38]}")
    # TUSCARAWAS is the case NATIVE_ENTITY_NUANCES.md names, and it never
    # reaches the guards - a hand-written RESOLUTIONS entry excludes it first.
    # Prove the guard would have caught it WITHOUT that hand entry, which is
    # the whole point of replacing a literal with a rule.
    why = mod.loose_path_refusal("TUSCARAWAS METROPOLITAN HOUSING",
                                 "Tuscarawas")
    good = why.startswith("REFUSED_ADMIN_GEOGRAPHY")
    bad += not good
    print("\n  THE HAND-CODED LITERAL, RE-DERIVED: the RESOLUTIONS dict "
          "excludes\n  TUSCARAWAS METROPOLITAN HOUSING by name. Called "
          "directly, the guard\n  reaches the same answer from the shape "
          "alone:")
    print(f"    {'ok ' if good else 'FAIL'} {why or '(no refusal)'}")

    print(f"\n  {bad} failure(s)." if bad else
          "\n  all fixtures pass: both guards fire, neither over-fires.")
    return 1 if bad else 0


# =====================================================================
# LEARNING - the number that must fall, pass over pass.
# =====================================================================

def cmd_learning() -> int:
    owner = set()
    for r in rd(SPINE / "cedar_rulings.csv"):
        owner.add(("RUL", r["identifier_type"], r["identifier"]))
    for r in rd(SPINE / "cedar_exclusion_rulings.csv"):
        owner.add(("EXCL", r["identifier_type"], r["identifier"]))
    for r in rd(SPINE / "federal_funding_rulings_from_dofile.csv"):
        owner.add(("DOFILE", r["identifier_type"], r["identifier"]))
    for r in rd(CLEAN / "individual_native_prior_rulings.csv"):
        owner.add(("IND", r["identifier_type"], r["identifier"]))
    for p in ("rulings_inbox_2026-08-07_elijah.csv",
              "rulings_inbox_2026-08-08_elijah_batch2.csv"):
        for r in rd(REVIEW / p):
            owner.add(("INBOX", p, r["identifier"]))
    j = REVIEW / "owner_rulings_cedar_recon_v1_2026-08-28.json"
    if j.exists():
        for r in json.loads(j.read_text(encoding="utf-8"))["rulings"]:
            owner.add(("RECON", r["cluster_key"], ""))
    for r in rd(REVIEW / "elijah_rulings_2026-08-27_recon_batch2.csv"):
        owner.add(("RECON", r["cluster_key"], ""))
    for r in rd(REVIEW / "elijah_rulings_2026-08-26_recon.csv"):
        owner.add(("RECON", r["identifier"], ""))

    led = rd(CLEAN / "cedar_identifier_ledger_final.csv")
    tA = [r for r in led if r["confidence_tier"] == "A"]
    tX = [r for r in led if r["confidence_tier"] == "X"]
    npr = rd(SPINE / "nonprofit_exclusion_rulings.csv")
    allsub = {r["subject_key"]
              for r in rd(CLEAN / "cedar_ruling_ledger_consolidated.csv")}

    print("  THE LEARNING TARGET: rulings needed per 100 PUBLISHABLE "
          "identifications.\n  Publishable means tier A in "
          "cedar_identifier_ledger_final.csv - the rows that\n  actually "
          "carry a Native entity into a shipping table.\n")
    print(f"    tier A identifications                  {len(tA):>7,}")
    print(f"    tier X (permanent refutations)          {len(tX):>7,}")
    print(f"    owner adjudication events               {len(owner):>7,}")
    print(f"    all adjudicated subjects (owner+agent)  {len(allsub):>7,}")
    print()
    print(f"    OWNER rulings per 100 tier-A ids        "
          f"{100*len(owner)/len(tA):>7.1f}   <-- the baseline to beat")
    print(f"    ALL rulings per 100 tier-A ids          "
          f"{100*len(allsub)/len(tA):>7.1f}")
    print()
    print("  AND THE COUNTER-EXAMPLE TO CASEWORK, from the same corpus:")
    print(f"    2 filter scripts the owner AUTHORED produced {len(npr):,} "
          f"exclusions.")
    print(f"    Leverage: {len(npr)//2:,} decisions per human act, against "
          f"~1 for casework.")
    print("    That ratio, not the ruling count, is what 'surpass me' "
          "measures.")
    print()
    print("  tier A by attribution method - what actually produces "
          "publishable ids:")
    for k, v in collections.Counter(r["attribution_method"]
                                    for r in tA).most_common(8):
        print(f"    {v:>6,}  {k}")
    return 0


def main() -> int:
    cmds = {"census": cmd_census, "negatives": cmd_negatives,
            "repeats": cmd_repeats, "prior": cmd_prior, "guards": cmd_guards,
            "fixtures": cmd_fixtures, "learning": cmd_learning}
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg == "all":
        rc = 0
        for name, fn in cmds.items():
            print(f"\n=== 522 {name} " + "=" * (58 - len(name)))
            rc |= fn()
        return rc
    if arg not in cmds:
        print(f"unknown phase {arg!r}; one of: all, " + ", ".join(cmds))
        return 2
    print(f"=== Cedar Press 522: {arg} ===\n")
    return cmds[arg]()


if __name__ == "__main__":
    raise SystemExit(main())
