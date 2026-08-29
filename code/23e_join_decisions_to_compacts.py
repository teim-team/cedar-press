#!/usr/bin/env python3
"""
23e_join_decisions_to_compacts.py -- Cedar Press Gaming dataset, Phase 1 Step E.

Measures the overlap between the BIA gaming-land decision layer
(gaming_land_decisions.csv, 138 records) and the compact layer
(compacts.csv, 707 instruments) on tribe name + state.

WHAT THIS IS AND IS NOT. This reports a JOIN RATE. It does not force matches and
it does not write a link into either file. Both sides carry BIA's own tribe
strings, which differ in form between the two BIA pages ("Wilton Rancheria,
California" vs "Wilton Rancheria"), so the join is run at three declared
strictness levels and each level's yield is reported separately:

  L1  exact normalized (tribe, state)
  L2  exact normalized tribe, ignoring state
  L3  distinctive-token-set equality within a state -- the token sets must be
      EQUAL after dropping the generic vocabulary (tribe/band/nation/of/the/...),
      not merely overlapping. Token OVERLAP is not used: it produces the
      "Pueblo of Santa Ana" / "Pueblo of Santa Clara" class of false match.

Non-matches stay blank. The output is a diagnostic table, not an authority.

CAVEAT INHERITED FROM THE COMPACT LAYER: STATE_OF_BUILD.md records that the BIA
compact index misaligns its Tribes column with its Title column on 61 of 1,189
rows (5.1%). compacts.csv carries bia_tribes_column_conflict for those rows; any
join through a conflicted row is flagged here rather than silently trusted.
"""
import os, re, csv, io, collections, unicodedata

BASE  = r"C:\Users\esm247\Desktop\Cedar Press"
CLEAN = os.path.join(BASE, "data", "clean")

buf = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")

STATE_ABBR = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","California":"CA","Colorado":"CO",
 "Connecticut":"CT","Florida":"FL","Idaho":"ID","Indiana":"IN","Iowa":"IA","Kansas":"KS",
 "Louisiana":"LA","Maine":"ME","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN",
 "Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV",
 "New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND",
 "Oklahoma":"OK","Oregon":"OR","Rhode Island":"RI","South Carolina":"SC",
 "South Dakota":"SD","Texas":"TX","Washington":"WA","Wisconsin":"WI","Wyoming":"WY"}
def st(v):
    v = (v or "").strip()
    if len(v) == 2: return v.upper()
    return STATE_ABBR.get(v.title(), v.upper()[:2] if v else "")

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9]+", " ", s).lower()).strip()

# generic vocabulary that carries no identifying information
STOP = set("tribe tribes band bands indian indians nation nations community communities "
           "of the a an in and reservation rancheria pueblo village tribal state gaming "
           "compact group people federal register link california arizona oklahoma "
           "washington wisconsin michigan minnesota oregon nevada montana kansas iowa "
           "nebraska louisiana york mexico dakota carolina connecticut florida "
           "massachusetts mississippi missouri texas wyoming idaho indiana".split())
def toks(s):
    return frozenset(w for w in norm(s).split() if w not in STOP and len(w) > 2)

dec = list(csv.DictReader(open(os.path.join(CLEAN, "gaming_land_decisions.csv"),
                               encoding="utf-8")))
cmp_ = list(csv.DictReader(open(os.path.join(CLEAN, "compacts.csv"), encoding="utf-8")))
log(f"gaming_land_decisions.csv : {len(dec)} records, "
    f"{len(set(d['tribe'] for d in dec))} distinct tribe strings")
log(f"compacts.csv              : {len(cmp_)} instruments, "
    f"{len(set(c['tribe'] for c in cmp_))} distinct tribe strings")

by_ns, by_n, by_tok = (collections.defaultdict(list) for _ in range(3))
for c in cmp_:
    a = st(c["state"])
    by_ns[(norm(c["tribe"]), a)].append(c)
    by_n[norm(c["tribe"])].append(c)
    t = toks(c["tribe"])
    if t: by_tok[(t, a)].append(c)

out, level_n = [], collections.Counter()
for d in dec:
    a = d.get("state_abbr") or st(d["state"])
    hits, level = by_ns.get((norm(d["tribe"]), a), []), "L1_exact_tribe_and_state"
    if not hits:
        hits, level = by_n.get(norm(d["tribe"]), []), "L2_exact_tribe_any_state"
    if not hits:
        t = toks(d["tribe"])
        hits, level = (by_tok.get((t, a), []) if t else []), "L3_token_set_equal_within_state"
    if not hits and d.get("bia_tribes_column_conflict") == "1" and d.get("tribe_from_title"):
        # The BIA Tribe(s) column on this decision row is flagged as misaligned with
        # BIA's own title and documents. Retry on the title-derived name, at the same
        # strictness, and label the level so the weaker basis is never invisible.
        alt = d["tribe_from_title"]
        hits = by_n.get(norm(alt), [])
        level = "L4_via_tribe_from_title_bia_column_conflicted"
        if not hits:
            t = toks(alt)
            hits = by_tok.get((t, a), []) if t else []
    if not hits:
        level = "no_match"
    level_n[level] += 1
    conflicted = sum(1 for h in hits if h.get("bia_tribes_column_conflict") == "1")
    out.append(dict(
        decision_id=d["decision_id"], tribe=d["tribe"], state=d["state"],
        decision_status=d["decision_status"], legal_theory=d["legal_theory"],
        decision_date=d["decision_date"],
        match_level=level, n_compacts_matched=len(hits),
        bia_tribes_column_conflict=d.get("bia_tribes_column_conflict", ""),
        tribe_from_title=d.get("tribe_from_title", ""),
        compact_ids="|".join(h["compact_id"] for h in hits),
        compact_tribe_strings="|".join(sorted(set(h["tribe"] for h in hits))),
        earliest_compact_date=min([h["original_effective_date"] for h in hits], default=""),
        latest_compact_date=max([h["original_effective_date"] for h in hits], default=""),
        compacts_with_bia_tribes_column_conflict=conflicted,
        match_basis=("no compact in compacts.csv matches this tribe at any declared "
                     "strictness level; left blank rather than guessed"
                     if level == "no_match" else
                     "compacts.csv joined at strictness level " + level)))

with open(os.path.join(CLEAN, "gaming_decision_compact_join.csv"), "w",
          newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader()
    for r in out: w.writerow(r)

matched = sum(v for k, v in level_n.items() if k != "no_match")
log("")
log("=" * 78); log("DECISION x COMPACT JOIN"); log("=" * 78)
for k in ("L1_exact_tribe_and_state", "L2_exact_tribe_any_state",
          "L3_token_set_equal_within_state",
          "L4_via_tribe_from_title_bia_column_conflicted", "no_match"):
    log(f"   {level_n[k]:>4}  {k}")
log(f"\nJOIN RATE: {matched} of {len(dec)} decisions ({100*matched/len(dec):.1f}%) "
    f"match at least one compact")
log(f"decisions matching a compact whose BIA tribes column is flagged conflicted: "
    f"{sum(1 for r in out if r['compacts_with_bia_tribes_column_conflict'])}")
log(f"distinct compacts touched: "
    f"{len(set(x for r in out for x in r['compact_ids'].split('|') if x))} of {len(cmp_)}")
log("")
log("join rate by decision_status:")
for s_ in ("Approved", "Disapproved", "Pending"):
    sub = [r for r in out if r["decision_status"] == s_]
    m = sum(1 for r in sub if r["match_level"] != "no_match")
    if sub: log(f"   {s_:<12} {m:>3} / {len(sub):<3} ({100*m/len(sub):5.1f}%)")
log("")
log("unmatched decisions (tribe strings absent from compacts.csv):")
un = sorted(set((r["state"], r["tribe"]) for r in out if r["match_level"] == "no_match"))
for a, t in un: log(f"   {a:<16} {t}")
log(f"   -> {len(un)} distinct tribe-state pairs. A tribe with no Class III compact "
    f"legitimately has no compact row; non-match is not necessarily a join failure.")

with open(os.path.join(BASE, "logs", "23_gaming_2026-08-05.log"), "a",
          encoding="utf-8") as fh:
    fh.write("\n\n" + "=" * 78 + "\n23e_join_decisions_to_compacts.py\n"
             + "=" * 78 + "\n" + buf.getvalue())
