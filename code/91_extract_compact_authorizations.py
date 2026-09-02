#!/usr/bin/env python3
"""
91_extract_compact_authorizations.py -- Cedar Press gaming, authorization layer.

WHY THIS EXISTS
---------------
`data/clean/gaming_property_capacity_history.csv` is 64,181 observations from a
SINGLE commercial vendor whose method is undisclosed and whose data we may not
resell. This script builds part of the independent replacement from a source we
already hold in full: **1,187 tribal-state gaming compact documents**, retrieved
from bia.gov, with extracted text.

WHAT A COMPACT CAN AND CANNOT TELL YOU
--------------------------------------
A compact states what a tribe is **authorised** to operate. It never states what
the tribe **does** operate. Those are different facts and this build never
conflates them:

    gaming_machines                 <- NEVER produced here
    gaming_machines_authorized_max  <- what this script produces

Same for tables, facilities and wagers. Every metric emitted by this script ends
in `_authorized_max` or is an explicit rule (minimum age, hours), because that
is the only thing the evidence class supports.

RELATIONSHIP TO 15d/15e
-----------------------
`code/15d_terms_extract.py` already extracts compact terms and its measured
failure modes (FM1-FM7 in its docstring) are respected here -- the TOC guard,
the approval-letter zoning, the payout-percentage rejection and the
non-tribal-operator rejection are all reimplemented, because they were paid for
with manual adjudication and re-learning them would be wasteful.

What is new: 15d looks for ONE cap type (`machine_cap`, 63 rows, 54 tribes).
This script widens the vocabulary to table limits, facility-count limits, wager
limits and minimum age, and runs against the full 1,187-document text corpus
rather than the base-instrument subset.

OUTPUT
------
data/interim/compact_authorizations_candidates.csv   -- every candidate, kept or rejected
data/interim/compact_authorizations.csv              -- the kept rows

Nothing is written to data/clean by this script. 92 assembles the published file.
"""
import csv, os, re, sys, collections
from pathlib import Path

BASE = str(Path(__file__).resolve().parent.parent)
EXT = os.path.join(BASE, "data", "raw", "external", "compacts")
TXT = os.path.join(EXT, "text")
CLEAN = os.path.join(BASE, "data", "clean")
INT = os.path.join(BASE, "data", "interim")
os.makedirs(INT, exist_ok=True)

BUILT = "2026-08-06"

# --------------------------------------------------------------- text helpers
def norm(s):
    """Collapse whitespace. The corpus is OCR of scanned compacts, so it also
    carries substitution noise (`Gamin1` for `Gaming`, `\u2022` for `"`). Noise is
    NEVER repaired -- a repaired quote is not a verbatim quote. It is only
    tolerated by the regexes below."""
    return re.sub(r"[ \t]+", " ", s.replace("\u00a0", " "))

def flat(s):
    return norm(s).replace("\n", " ").strip()

DOTS = re.compile(r"\.{5,}|\. \. \. \.|\u00b7{5,}")
PAGENUM = re.compile(r"\s\d{1,3}\s*(?:\n|$)")

def is_toc(window):
    """FM1 (15d): table-of-contents lines match provision regexes but are not
    provisions. Dot leaders and a run of trailing page numbers are the tells."""
    if DOTS.search(window):
        return True
    if len(PAGENUM.findall(window)) >= 3:
        return True
    return False

LETTER_MARK = re.compile(
    r"(Sincerely|Assistant Secretary\s*[-\u2013]?\s*Indian Affairs|"
    r"Principal Deputy Assistant Secretary|Dear (Chairman|Chairwoman|President|Governor|Chairperson))",
    re.I)
BODY_MARK = re.compile(
    r"(WITNESSETH|^\s*RECITALS|TABLE\s+OF\s+CONTENTS|"
    r"^\s*(SECTION|ARTICLE|PART)\s+(1|I|ONE)\b|^\s*PREAMBLE)", re.I | re.M)

def body_offset(text):
    """FM5 (15d): the Secretary's approval letter is bundled at the FRONT of the
    scanned PDF and reads like compact text. In one measured case the letter says
    the compact does NOT provide substantial exclusivity -- extracting from it
    would have recorded the opposite of the truth. Return the character offset
    where the instrument body begins; anything before it is zoned as the letter."""
    m = BODY_MARK.search(text[:60000])
    if not m:
        return 0
    head = text[:m.start()]
    if not LETTER_MARK.search(head):
        return 0
    return m.start()

WORDNUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15,
    "sixteen": 16, "eighteen": 18, "twenty": 20, "twenty-one": 21, "twentyone": 21,
    "twenty-five": 25, "thirty": 30, "forty": 40, "fifty": 50, "seventy-five": 75,
    "one hundred": 100, "two hundred": 200, "two hundred fifty": 250,
    "five hundred": 500, "seven hundred fifty": 750, "one thousand": 1000,
}

def num(s):
    """'2-1/2' -> 2.5; '1,500' -> 1500; 'three' -> 3. Returns None on anything
    unparseable rather than guessing.

    Spelled-out numbers matter: compacts write small counts in words ("the Tribe
    may operate two Gaming Facilities") and digits only for large ones. A
    digits-only extractor therefore misses facility and table limits almost
    entirely while looking like it is working, because the device caps it does
    catch are all in digits."""
    s = s.strip().replace(",", "")
    m = re.match(r"^(\d+)\s*[-\s]\s*1/2$", s)
    if m:
        return float(m.group(1)) + 0.5
    w = WORDNUM.get(re.sub(r"\s+", " ", s.lower().strip()))
    if w is not None:
        return w
    try:
        f = float(s)
        return int(f) if f == int(f) else f
    except ValueError:
        return None

def window(text, m, before=260, after=320):
    a = max(0, m.start() - before)
    b = min(len(text), m.end() + after)
    return flat(text[a:b])

# --------------------------------------------------------------- vocabularies
DEVICE = (r"(?:gaming\s+devices?|gaming\s+machines?|slot\s+machines?|video\s+lottery\s+terminals?"
          r"|electronic\s+gaming\s+devices?|player\s+terminals?|video\s+gaming\s+machines?"
          r"|electronic\s+games?\s+of\s+chance|player\s+stations?|gam[a-z]{0,3}\s+devices?)")
TABLE = (r"(?:table\s+games?|card\s+tables?|gaming\s+tables?|banking\s+card\s+games?"
         r"|house-?banked\s+card\s+games?|blackjack\s+tables?|player\s+terminals?\s+for\s+table)")
FACILITY = r"(?:gaming\s+facilit(?:y|ies)|gaming\s+establishments?|gaming\s+operations?|gaming\s+sites?)"

# A single number written as digits, optionally followed by a spelled-out
# parenthetical -- or the reverse. Compacts do both.
N = r"([\d][\d,]{0,7})"
# Digits OR the small spelled-out numbers in WORDNUM.
NW = (r"([\d][\d,]{0,7}|(?:twenty-one|twenty-five|seventy-five|two hundred fifty|"
      r"seven hundred fifty|one hundred|two hundred|five hundred|one thousand|"
      r"eighteen|sixteen|fifteen|twenty|thirty|forty|fifty|eleven|twelve|"
      r"three|seven|eight|nine|four|five|six|ten|one|two))")

AUTH_VERB = (r"(?:authorized\s+to\s+(?:operate|conduct|have|maintain)|may\s+operate|may\s+conduct|"
             r"shall\s+be\s+(?:permitted|entitled)\s+to\s+operate|shall\s+not\s+operate\s+more\s+than|"
             r"operate\s+no\s+more\s+than|limited\s+to|shall\s+not\s+exceed|not\s+to\s+exceed|"
             r"maximum\s+of|no\s+more\s+than|up\s+to|in\s+excess\s+of)")

# --------------------------------------------------------------- rule table
# Each rule: (metric, unit, compiled regex with ONE numeric group, anchor, reject)
#
# `anchor` must appear in the window for the candidate to be kept: it is the
# evidence that the sentence is granting an authorisation rather than describing
# a payment schedule, a transfer, or somebody else's licence.
#
# `reject` kills the candidate outright. These come from measured 15d failures
# plus this script's own pilot read.

REJECT_COMMON = re.compile(
    # -- 15d FM4, re-learned the hard way on this script's own pilot read.
    # "the Tribe may transfer only up to 1,400 Gaming Devices of its Current
    # Gaming Device Allocation" is a TRANSFER ceiling, not an operating
    # authorisation, and it leaked onto San Carlos Apache and Fort Mojave on the
    # first run. The Arizona compacts are a single common form, so one leak is
    # ~30 wrong rows.
    r"(transfer(?:red|s|ring)?\s+(?:to|from)|to\s+transfer|transfer\s+only|"
    r"Gaming\s+Device\s+Operating\s+Rights|"
    # 15d also had this one and it is why: the AZ form names the Navajo Nation
    # inside a conditional that has nothing to do with the compact's own tribe.
    r"if\s+the\s+tribe\s+is\s+(?:the\s+)?navajo|"
    r"payments?\s+shall\s+be\s+based|"
    r"schedule\s+based\s+on|so\s+long\s+as\s+the\s+tribe\s+operates[^.]{0,140}pay|"
    r"non-?tribal|racino|commercial\s+(?:casino|operator|licensee)|card\s?room|"
    r"horse\s?racing|pari-?mutuel|lottery\s+retailer|"
    r"pay\s?out|payout|prize|jackpot|odds|hold\s+percentage|"
    r"charitable|bingo\s+hall\s+licence|"
    r"another\s+tribe|other\s+tribes|any\s+other\s+tribe)", re.I)

# ---------------------------------------------------------------- applies_to
# The California 1999 compacts describe a STATEWIDE gaming-device licence pool
# in the same sentence grammar a tribe uses for its own ceiling:
#   "Compact Tribes authorized to operate up to and including 1500 gaming
#    devices ... shall be entitled to draw up to an additional 500 licenses,
#    for a total authorization to operate up to 2000 gaming devices"
# That is the pool's tier structure, NOT Morongo's cap, and it landed on Morongo
# on the first run. It cannot be rejected -- it is genuine compact content -- so
# it is LABELLED instead, and the published layer carries only `tribe` and
# `per_facility` rows.
POOL_MARK = re.compile(
    r"(Compact\s+Tribes|each\s+Compact\s+Tribe|draw\s+up\s+to|licenses?\s+from\s+the\s+"
    r"(?:pool|License\s+Pool)|Gaming\s+Device\s+License\s+Pool|entitled\s+to\s+draw|"
    r"available\s+to\s+all\s+tribes|statewide|any\s+Compact\s+Tribe)", re.I)
PERFAC_MARK = re.compile(r"(per\s+(?:gaming\s+)?facilit|at\s+each\s+(?:gaming\s+)?facilit|"
                         r"in\s+any\s+one\s+(?:gaming\s+)?facilit|each\s+such\s+facilit)", re.I)

def applies_to(win):
    if PERFAC_MARK.search(win):
        return "per_facility"
    if POOL_MARK.search(win):
        return "statewide_pool_or_tier"
    return "tribe"

# ---------------------------------------------------------------- qualifier
# A wager limit is almost never one number. North Dakota's compacts set $50 on
# blackjack, $10 on poker and $25 on paddlewheels in three consecutive
# sentences. Publishing "wager_limit_max = 25" for that tribe would be true of
# paddlewheels and false of everything else, so the game is captured and the row
# is qualified by it. Where no game can be identified the row says so.
GAME_MARK = [
    ("blackjack", re.compile(r"black\s?jack", re.I)),
    ("poker", re.compile(r"\bpoker\b", re.I)),
    ("craps", re.compile(r"\bcraps\b", re.I)),
    ("roulette", re.compile(r"\broulette\b", re.I)),
    ("keno", re.compile(r"\bkeno\b", re.I)),
    ("bingo", re.compile(r"\bbingo\b", re.I)),
    ("paddlewheel", re.compile(r"paddle\s?wheel", re.I)),
    ("pull_tabs", re.compile(r"pull[-\s]?tabs?", re.I)),
    ("electronic_table_game", re.compile(r"\bETG\b|electronic\s+table\s+game", re.I)),
    ("gaming_device", re.compile(r"gaming\s+(?:device|machine)|player\s+terminal", re.I)),
]

# ------------------------------------------------- the other-tribe guard
# THE MOST IMPORTANT GUARD IN THIS SCRIPT. Measured on the first run.
#
# The Arizona 2002 compact is a single common form executed by ~20 tribes, and
# its facility-limit section reads:
#
#   "notwithstanding the number of Gaming Facilities specified on Gaming
#    Facilities Annex, if the Tribe is: (i) Tohono O'odham Nation, the Tribe
#    shall not operate more than ... (iii) Gila River Indian Community, the
#    Tribe shall not operate more than four Gaming Facilities in the Phoenix
#    Metropolitan Area ..."
#
# Every one of those tribes' limits appears in EVERY tribe's compact. The first
# run therefore published Gila River's four-facility limit onto Fort Mojave,
# San Juan Southern Paiute and Quechan -- 200 rows, all of them a well-sourced
# verbatim quote attached to the wrong nation. That is the exact failure this
# project ranks as worse than a gap, and it is the same shape as the Navajo
# transfer-limit leak above.
#
# The guard: reject any window naming a tribe that is NOT the compact's own.
# It is deliberately blunt. A real limit stated in a paragraph that happens to
# mention a neighbouring tribe is lost, and that is the correct trade.
CONDITIONAL_LIST = re.compile(r"if\s+the\s+(?:tribe|nation|community)\s+is\s*:", re.I)

# A hand stop-list cannot work here and the first attempt proved it: `Table
# Mountain Rancheria` put "table" in the tribe vocabulary, and the guard then
# rejected every "table games" sentence in the corpus -- 1,359 rejections,
# including all ten correct Oregon table limits. The guard was destroying more
# than it saved, which is precisely the measurement that retired the two guards
# named in AGENTS.md.
#
# So distinctiveness is MEASURED, not asserted. A tribe token counts as
# identifying only if it is rare across the 1,187-document corpus. "o'odham"
# appears in ~2% of documents and identifies a nation; "river", "table",
# "mountain", "valley" appear in most documents and identify nothing.
TRIBE_TOKEN_STOP = {
    "tribe", "tribes", "nation", "nations", "band", "bands", "indian", "indians",
    "of", "the", "community", "communities", "pueblo", "rancheria", "reservation",
    "and", "colony", "village", "group", "confederated", "california", "arizona",
    "washington", "oregon", "wisconsin", "minnesota", "michigan", "oklahoma",
    "nevada", "montana", "dakota", "north", "south", "new", "mexico", "york",
    "a", "in", "at", "for",
}

DF_MAX_SHARE = 0.15   # a token in >15% of documents is ordinary language

def tribe_tokens(name):
    toks = set(re.findall(r"[a-z']{3,}", (name or "").lower()))
    return {t for t in toks if t not in TRIBE_TOKEN_STOP}

def names_other_tribe(win, own_tokens, all_tribe_tokens):
    """True if the window contains a distinctive token belonging to some other
    tribe in the corpus and not to this compact's tribe."""
    wtok = set(re.findall(r"[a-z']{3,}", win.lower()))
    foreign = (wtok & all_tribe_tokens) - own_tokens
    return sorted(foreign)[:3] if foreign else None

def qualifier(win, m):
    """Prefer the game named nearest the matched number, then anything in the
    window. Multiple games in one window is itself reported."""
    near = win
    hits = [g for g, rx in GAME_MARK if rx.search(near)]
    if not hits:
        return "", 0
    return "|".join(hits), len(hits)

RULES = [
    # ---- gaming device authorisation ceiling -------------------------------
    dict(metric="gaming_machines_authorized_max", unit="devices",
         rx=re.compile(AUTH_VERB + r"\s+(?:a\s+total\s+of\s+|an\s+aggregate\s+of\s+)?" + N +
                       r"\s*(?:\([^)]{0,40}\)\s*)?" + DEVICE, re.I),
         anchor=re.compile(r"(authorized\s+to\s+operate|may\s+operate|number\s+of\s+gaming\s+devices|"
                           r"gaming\s+device\s+allocation|authorized\s+number|maximum\s+number|"
                           r"scope\s+of\s+gaming|shall\s+not\s+operate|total\s+number)", re.I)),
    dict(metric="gaming_machines_authorized_max", unit="devices",
         rx=re.compile(r"(?:total\s+(?:number\s+of\s+)?|aggregate\s+(?:number\s+of\s+)?|"
                       r"maximum\s+number\s+of\s+)" + DEVICE +
                       r"[^.]{0,80}?(?:shall\s+not\s+exceed|may\s+not\s+exceed|is|shall\s+be)\s+" + N, re.I),
         anchor=re.compile(r"(shall\s+not\s+exceed|may\s+not\s+exceed|maximum|total\s+number|aggregate)", re.I)),

    # ---- table game authorisation ceiling ----------------------------------
    dict(metric="table_games_authorized_max", unit="tables",
         rx=re.compile(AUTH_VERB + r"\s+(?:a\s+total\s+of\s+|an\s+aggregate\s+of\s+)?" + NW +
                       r"\s*(?:\([^)]{0,40}\)\s*)?(?:\w+\s+){0,2}" + TABLE, re.I),
         anchor=re.compile(r"(authorized\s+to\s+operate|may\s+operate|number\s+of\s+(?:card|gaming)\s+tables|"
                           r"maximum\s+number|scope\s+of\s+gaming|shall\s+not\s+operate|total\s+number|"
                           r"limited\s+to|shall\s+not\s+exceed)", re.I)),
    dict(metric="table_games_authorized_max", unit="tables",
         rx=re.compile(r"(?:total\s+(?:number\s+of\s+)?|aggregate\s+(?:number\s+of\s+)?|"
                       r"maximum\s+number\s+of\s+|number\s+of\s+)" + TABLE +
                       r"[^.]{0,90}?(?:shall\s+not\s+exceed|may\s+not\s+exceed|shall\s+be\s+limited\s+to|"
                       r"is\s+limited\s+to|is|shall\s+be)\s+" + NW, re.I),
         anchor=re.compile(r"(shall\s+not\s+exceed|may\s+not\s+exceed|limited\s+to|maximum|"
                           r"total\s+number|aggregate)", re.I)),

    # ---- how many gaming facilities the tribe may run -----------------------
    dict(metric="gaming_facilities_authorized_max", unit="facilities",
         rx=re.compile(AUTH_VERB + r"\s+(?:a\s+total\s+of\s+|an\s+aggregate\s+of\s+)?" + NW +
                       r"\s*(?:\([^)]{0,40}\)\s*)?(?:\w+\s+){0,2}" + FACILITY, re.I),
         anchor=re.compile(r"(number\s+of\s+gaming\s+facilit|gaming\s+facility\s+locations|"
                           r"may\s+operate|authorized\s+to\s+operate|shall\s+not\s+operate|"
                           r"maximum\s+number|limited\s+to|shall\s+not\s+exceed)", re.I)),
    dict(metric="gaming_facilities_authorized_max", unit="facilities",
         rx=re.compile(r"(?:number\s+of\s+|maximum\s+number\s+of\s+)" + FACILITY +
                       r"[^.]{0,90}?(?:shall\s+not\s+exceed|may\s+not\s+exceed|shall\s+be\s+limited\s+to|"
                       r"is\s+limited\s+to|shall\s+be)\s+" + NW, re.I),
         anchor=re.compile(r"(shall\s+not\s+exceed|may\s+not\s+exceed|limited\s+to|maximum)", re.I)),

    # ---- maximum wager per play --------------------------------------------
    dict(metric="wager_limit_max", unit="usd",
         rx=re.compile(r"(?:maximum\s+wager|wager\s+limit|maximum\s+bet|shall\s+not\s+(?:exceed|be\s+more\s+than))"
                       r"[^.]{0,60}?\$\s*" + N, re.I),
         anchor=re.compile(r"(wager|bet)", re.I)),

    # ---- minimum gambling age ----------------------------------------------
    dict(metric="minimum_gambling_age", unit="years",
         rx=re.compile(r"(?:under\s+the\s+age\s+of|less\s+than|at\s+least|minimum\s+age\s+of|"
                       r"age\s+of)\s+(?:twenty-?one\s*\(?)?" + N +
                       r"\)?\s*(?:years?\s+of\s+age)?[^.]{0,80}?"
                       r"(?:gam(?:e|ing|bl)|wager|casino|gaming\s+facility)", re.I),
         anchor=re.compile(r"(age\s+of|minimum\s+age|years\s+of\s+age)", re.I)),
]

# Plausibility gates. A regex that produces 0 devices or 4,000,000 tables has
# matched something that is not a cap; the gate refuses it rather than
# publishing an absurdity behind a verbatim quote.
GATES = {
    "gaming_machines_authorized_max": (1, 20000),
    "table_games_authorized_max": (1, 1000),
    "gaming_facilities_authorized_max": (1, 40),
    "wager_limit_max": (1, 100000),
    "minimum_gambling_age": (18, 21),
}

# --------------------------------------------------------------- load context
def load_versions():
    p = os.path.join(CLEAN, "compact_versions.csv")
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))

def load_compacts():
    p = os.path.join(CLEAN, "compacts.csv")
    return {r["compact_id"]: r for r in csv.DictReader(open(p, encoding="utf-8-sig"))}

def main():
    versions = load_versions()
    compacts = load_compacts()

    # text_path -> version row. compact_versions carries the mapping already, so
    # no filename heuristics are needed.
    by_txt = {}
    for v in versions:
        tp = (v.get("text_path") or "").strip()
        if tp:
            by_txt[os.path.basename(tp)] = v

    # Distinctive-token index across every tribe in the compact corpus. Used by
    # the other-tribe guard below.
    tribe_tok_by_compact = {}
    all_tribe_tokens = set()
    for cid, r in compacts.items():
        t = tribe_tokens(r.get("tribe", "")) | tribe_tokens(r.get("tribe_canonical_name", ""))
        tribe_tok_by_compact[cid] = t
        all_tribe_tokens |= t

    files = sorted([f for f in os.listdir(TXT) if f.lower().endswith(".txt")])
    print(f"[91] {len(files)} text files, {len(by_txt)} mapped by compact_versions.text_path")

    # ---- pass 1: measure how ordinary each candidate tribe token actually is.
    texts = {}
    df = collections.Counter()
    for fn in files:
        try:
            t = norm(open(os.path.join(TXT, fn), encoding="utf-8", errors="replace").read())
        except Exception:
            t = ""
        texts[fn] = t
        present = set(re.findall(r"[a-z']{3,}", t.lower())) & all_tribe_tokens
        for tok in present:
            df[tok] += 1
    ndocs = max(len(files), 1)
    identifying = {t for t in all_tribe_tokens if df[t] / ndocs <= DF_MAX_SHARE}
    dropped = sorted(all_tribe_tokens - identifying, key=lambda t: -df[t])
    print(f"[91] other-tribe guard: {len(all_tribe_tokens)} tribe tokens -> "
          f"{len(identifying)} identifying (df <= {DF_MAX_SHARE:.0%})")
    print(f"[91]   dropped as ordinary language (top 12): "
          f"{[(t, round(df[t]/ndocs, 2)) for t in dropped[:12]]}")
    tribe_tok_by_compact = {k: (v_ & identifying) for k, v_ in tribe_tok_by_compact.items()}
    all_tribe_tokens = identifying

    cands = []
    seen_files = 0
    unmapped = []

    for fn in files:
        seen_files += 1
        v = by_txt.get(fn)
        if v is None:
            unmapped.append(fn)
        text = texts.get(fn, "")
        if not text:
            continue
        boff = body_offset(text)

        for rule in RULES:
            for m in rule["rx"].finditer(text):
                win = window(text, m)
                raw = m.group(1)
                val = num(raw)
                keep, why = True, ""

                if val is None:
                    keep, why = False, "unparseable_number"
                elif is_toc(win):
                    keep, why = False, "table_of_contents"
                elif m.start() < boff:
                    keep, why = False, "approval_letter_zone"
                elif REJECT_COMMON.search(win):
                    keep, why = False, "reject_pattern:" + REJECT_COMMON.search(win).group(0)[:40]
                elif CONDITIONAL_LIST.search(win):
                    keep, why = False, "conditional_other_tribe_list"
                elif names_other_tribe(win, tribe_tok_by_compact.get((v or {}).get("compact_id", ""), set()),
                                       all_tribe_tokens):
                    keep, why = False, ("names_other_tribe:" + ",".join(
                        names_other_tribe(win,
                                          tribe_tok_by_compact.get((v or {}).get("compact_id", ""), set()),
                                          all_tribe_tokens)))
                elif not rule["anchor"].search(win):
                    keep, why = False, "no_authorisation_anchor"
                else:
                    lo, hi = GATES[rule["metric"]]
                    if not (lo <= val <= hi):
                        keep, why = False, f"outside_plausibility_gate[{lo},{hi}]"

                # applies_to and the game qualifier are read from a NARROW window
                # around the match, not the 580-char evidence window. Measured
                # reason: the Arizona form puts "per Gaming Facility location"
                # in the table-games sentence immediately before the facility
                # authorisation, so the wide window labelled Salt River's
                # three-facility tribal limit as a per-facility limit.
                nearwin = flat(text[max(0, m.start() - 90): min(len(text), m.end() + 130)])
                qual, nqual = qualifier(nearwin, m)
                cands.append(dict(
                    applies_to=applies_to(nearwin),
                    qualifier=qual,
                    n_games_in_window=nqual,
                    text_file=fn,
                    version_id=(v or {}).get("version_id", ""),
                    compact_id=(v or {}).get("compact_id", ""),
                    doc_kind=(v or {}).get("doc_kind", ""),
                    approval_date=(v or {}).get("approval_date", ""),
                    source_pdf=(v or {}).get("source_pdf", ""),
                    source_url=(v or {}).get("source_url", ""),
                    metric=rule["metric"],
                    value=val if val is not None else "",
                    raw_match=raw,
                    unit=rule["unit"],
                    doc_zone="approval_letter" if m.start() < boff else "instrument_text",
                    char_offset=m.start(),
                    quote=win,
                    kept=1 if keep else 0,
                    reject_reason=why,
                ))

    print(f"[91] {len(cands)} candidates from {seen_files} files; {sum(c['kept'] for c in cands)} kept pre-dedup")
    if unmapped:
        print(f"[91] {len(unmapped)} text files not mapped to a compact version (first 5): {unmapped[:5]}")

    # ---------------------------------------------------------------- dedupe
    # A compact repeats its own cap in the definitions, the scope section and
    # sometimes an appendix. One document stating 500 devices four times is ONE
    # fact. Keep the first occurrence in the instrument body per
    # (version_id, metric, value) and count the repeats rather than dropping
    # them silently.
    kept = [c for c in cands if c["kept"]]
    kept.sort(key=lambda c: (c["version_id"], c["metric"], str(c["value"]), c["qualifier"], c["applies_to"], c["char_offset"]))
    out, repeats = [], collections.Counter()
    for c in kept:
        key = (c["version_id"], c["metric"], c["value"], c["qualifier"], c["applies_to"])
        repeats[key] += 1
        if repeats[key] == 1:
            out.append(c)
    for c in out:
        c["n_occurrences_in_document"] = repeats[(c["version_id"], c["metric"], c["value"])]

    # ------------------------------------- disagreement WITHIN one document
    # Two different caps for the same metric in the same instrument is a
    # finding, not something to resolve by taking the max. Flag both.
    bym = collections.defaultdict(list)
    for c in out:
        bym[(c["version_id"], c["metric"])].append(c)
    for k, group in bym.items():
        vals = sorted({g["value"] for g in group})
        for g in group:
            g["n_distinct_values_in_document"] = len(vals)
            g["other_values_in_document"] = ";".join(str(x) for x in vals if x != g["value"])

    # ---------------------------------------------------------------- attach
    for c in out:
        cm = compacts.get(c["compact_id"], {})
        c["tribe"] = cm.get("tribe", "")
        c["state"] = cm.get("state", "")
        c["tribe_id"] = cm.get("tribe_id", "")
        c["tribe_canonical_name"] = cm.get("tribe_canonical_name", "")
        c["entity_id"] = cm.get("entity_id", "")
        c["compact_source_url"] = cm.get("source_url", "")
        c["built_date"] = BUILT

    # ---------------------------------------------------------------- write
    cand_cols = ["text_file", "version_id", "compact_id", "doc_kind", "approval_date",
                 "source_pdf", "source_url", "metric", "value", "raw_match", "unit",
                 "applies_to", "qualifier", "n_games_in_window",
                 "doc_zone", "char_offset", "quote", "kept", "reject_reason"]
    p1 = os.path.join(INT, "compact_authorizations_candidates.csv")
    with open(p1, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cand_cols)
        w.writeheader()
        for c in cands:
            w.writerow({k: c.get(k, "") for k in cand_cols})

    out_cols = cand_cols + ["n_occurrences_in_document", "n_distinct_values_in_document",
                            "other_values_in_document", "tribe", "state", "tribe_id",
                            "tribe_canonical_name", "entity_id", "compact_source_url", "built_date"]
    p2 = os.path.join(INT, "compact_authorizations.csv")
    with open(p2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_cols)
        w.writeheader()
        for c in out:
            w.writerow({k: c.get(k, "") for k in out_cols})

    # ---------------------------------------------------------------- report
    print(f"\n[91] KEPT {len(out)} authorization facts")
    print(f"     -> {p2}")
    print(f"     -> {p1} (all {len(cands)} candidates incl. rejections)\n")
    bymetric = collections.Counter(c["metric"] for c in out)
    for k, n in bymetric.most_common():
        tribes = len({c["tribe_id"] for c in out if c["metric"] == k and c["tribe_id"]})
        print(f"     {n:5d}  {k:36s}  {tribes:4d} tribes")
    print()
    print("     rejections by reason:")
    for k, n in collections.Counter(
            c["reject_reason"].split(":")[0] for c in cands if not c["kept"]).most_common():
        print(f"     {n:5d}  {k}")
    conflicted = {k for k, g in bym.items() if len({x['value'] for x in g}) > 1}
    print(f"\n     {len(conflicted)} (document, metric) pairs state MORE THAN ONE value "
          f"-- flagged, not resolved")

if __name__ == "__main__":
    main()
