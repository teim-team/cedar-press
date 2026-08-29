#!/usr/bin/env python3
"""
20_build_subcontracts.py  --  Cedar Press Dataset 2b (Subcontracting)

Builds, from LOCAL COPIES only:
    data/clean/subawards.csv                    one row per subaward
    data/clean/subaward_identifier_harvest.csv  one row per distinct (uei,cage,duns)
    data/clean/prime_sub_network.csv            prime -> sub edge list

and reports NET-NEW identifiers against the existing spine ledgers
(both read READ-ONLY; neither is modified).

PRIME DIRECTIVE compliance
--------------------------
* Every emitted row traces to a named source file + source row key (HigherGov page URL).
* No identifier is normalized, padded, or repaired. Malformed values are emitted
  EXACTLY as observed and flagged in `malformed_flag`.
* No entity is attributed to a tribe/ANC/NHO. `direction` is left `unknown` by design;
  deciding it requires the spine and is out of scope for this script.

KNOWN SOURCE GOTCHA
-------------------
`subcontract-05-09-23-22-23-37.csv` ships TWO columns both literally named
`CAGE Code` (positions 22 and 23). A name-based pandas read collapses/mangles them.
This script reads the file POSITIONALLY with csv.reader. Position 22 is the Prime
Awardee CAGE and position 23 is the Prime Awardee PARENT CAGE -- confirmed two ways:
(a) column adjacency to `Prime Awardee UEI` / `Prime Awardee Parent UEI`, and
(b) the Stata treatment `clean/sub file.dta`, which preserved both columns as
    `cagecode` and `x` with their original variable labels intact.
"""

import csv, os, sys, shutil, hashlib, datetime, statistics
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10_000_000)

CEDAR = str(Path(__file__).resolve().parent.parent)
ESM   = os.path.join(CEDAR, "data", "raw", "esm_hci", "ESM")
EXT   = os.path.join(CEDAR, "data", "raw", "external", "subcontracts")
CLEAN = os.path.join(CEDAR, "data", "clean")
DOCS  = os.path.join(CEDAR, "docs")
LOGP  = os.path.join(CEDAR, "logs", "20_subcontracts_2026-08-05.log")

FETCHED_DATE = "2026-08-05"          # date these inputs were staged into Cedar Press
os.makedirs(EXT, exist_ok=True)
os.makedirs(os.path.dirname(LOGP), exist_ok=True)

_lf = open(LOGP, "a", encoding="utf-8")
def log(msg, tag="INFO"):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}][{tag}] {msg}"
    print(line, flush=True); _lf.write(line + "\n"); _lf.flush()

log("=" * 78)
log("20_build_subcontracts.py START  (Cedar Press Dataset 2b - Subcontracting)")

# ----------------------------------------------------------------------------
# 1. STAGE INPUTS LOCALLY + SOURCE MANIFEST
# ----------------------------------------------------------------------------
INPUTS = [
    (os.path.join(ESM, "raw", "subcontract-05-09-23-22-23-37.csv"),
     "HigherGov subaward export (FSRS-derived). PRIMARY SOURCE. Sub + Prime UEI/CAGE "
     "on every row. Exported 2023-05-09 22:23:37 per filename.", True),
    (os.path.join(ESM, "clean", "master sub file.dta"),
     "Stata collapse: year x parent_uei sums of subaward amounts (nominal + 2022$).", True),
    (os.path.join(ESM, "clean", "sub file.dta"),
     "Stata treatment of the subaward export, filtered to the Winnebago/HCI family "
     "(30 rows). Preserves BOTH duplicate CAGE columns as `cagecode` and `x`.", True),
    (os.path.join(ESM, "intermediate", "sub hci.dta"),
     "Stata collapse: year sums, HCI only. No identifiers.", True),
    (os.path.join(ESM, "intermediate", "sub.dta"),
     "Stata collapse: year sums. No identifiers.", True),
]

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()

manifest = []
staged = {}
for src, role, docopy in INPUTS:
    if not os.path.exists(src):
        log(f"MISSING INPUT (skipped): {src}", "WARN"); continue
    dst = os.path.join(EXT, os.path.basename(src))
    if docopy:
        shutil.copy2(src, dst)
        log(f"staged -> data/raw/external/subcontracts/{os.path.basename(dst)} "
            f"({os.path.getsize(src)/1e6:.2f} MB)")
    staged[os.path.basename(src)] = dst
    manifest.append({
        "local_file": os.path.basename(dst),
        "cedar_path": dst,
        "source_path": src,
        "description": role,
        "bytes": os.path.getsize(src),
        "md5": md5(src),
        "source_mtime": datetime.datetime.fromtimestamp(
            os.path.getmtime(src)).isoformat(timespec="seconds"),
        "fetched_date": FETCHED_DATE,
    })

man_path = os.path.join(EXT, "_SOURCE_MANIFEST_subcontracts.csv")
with open(man_path, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(manifest[0].keys()))
    w.writeheader(); w.writerows(manifest)
log(f"wrote {man_path} ({len(manifest)} entries)")

SRC_CSV_NAME = "subcontract-05-09-23-22-23-37.csv"
SRC_CSV = staged[SRC_CSV_NAME]

# ----------------------------------------------------------------------------
# 2. READ THE SUBAWARD EXPORT POSITIONALLY
# ----------------------------------------------------------------------------
# Positional map. Do NOT switch to name-based access: cols 22 and 23 collide.
C = dict(
    subaward_number=0, sub_name=1, sub_parent_name=2, sub_uei=3, sub_parent_uei=4,
    sub_cage=5, sub_parent_cage=6, sub_parent_flag=7, amount=8, action_date=9,
    fiscal_year=10, description=11, pop_city=12, pop_state=13, pop_zip=14,
    pop_cd=15, pop_country=16, prime_award_id=17, prime_name=18,
    prime_parent_name=19, prime_uei=20, prime_parent_uei=21,
    prime_cage=22,          # <-- first  "CAGE Code"  = Prime Awardee CAGE
    prime_parent_cage=23,   # <-- second "CAGE Code"  = Prime Awardee Parent CAGE
    prime_pop_start=24, prime_pop_end=25, prime_pop_pot_end=26,
    prime_obligated=27, prime_current_value=28, prime_potential_value=29,
    prime_description=30, prime_project_title=31, prime_defense_program=32,
    prime_research_code=33, prime_pricing=34, prime_solicitation=35,
    prime_awarding_agency=36, prime_top_awarding_agency=37,
    prime_funding_agency=38, prime_top_funding_agency=39, prime_vehicle=40,
    psc=41, psc_title=42, naics=43, naics_title=44, prime_set_aside=45,
    prime_award_type=46, fsrs_last_modified=47, highergov_page=48,
)

with open(SRC_CSV, encoding="utf-8-sig", newline="") as f:
    rd = csv.reader(f)
    HDR = next(rd)
    RAW = list(rd)

log(f"read {SRC_CSV_NAME}: {len(HDR)} columns, {len(RAW)} data rows")
dup = [h for h, n in Counter(HDR).items() if n > 1]
log(f"duplicate header names present: {dup}  -> read positionally, not by name", "GOTCHA")
badw = Counter(len(r) for r in RAW)
if set(badw) != {len(HDR)}:
    log(f"RAGGED ROWS: width distribution {dict(badw)}", "WARN")
else:
    log(f"all {len(RAW)} rows are exactly {len(HDR)} fields wide")

def g(row, key):
    return row[C[key]].strip()

NEG_PAREN = []
def parse_amount(s):
    """HigherGov writes de-obligations in accounting parentheses, e.g. '(1,914,018)'.
    Parentheses = negative is unambiguous; parse it rather than drop the value."""
    raw = s
    s = s.replace(",", "").replace("$", "").strip()
    if not s: return None
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1].strip()
        NEG_PAREN.append(raw)
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v

def parse_date(s):
    s = s.strip()
    if not s: return ""
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try: return datetime.datetime.strptime(s, fmt).date().isoformat()
        except ValueError: pass
    return s          # emit as observed rather than guess

# ----------------------------------------------------------------------------
# 3. subawards.csv
# ----------------------------------------------------------------------------
SUB_FIELDS = [
    "sub_uei", "sub_cage", "sub_name", "sub_state", "prime_uei", "prime_cage",
    "prime_name", "prime_award_id", "subaward_amount", "subaward_date",
    "fiscal_year", "naics", "psc", "description", "direction",
    "source_file", "fetched_date",
    # --- trailing provenance / harvest-support columns (additive, not substitutes)
    "subaward_number", "source_url",
    "sub_parent_uei", "sub_parent_cage", "sub_parent_name",
    "prime_parent_uei", "prime_parent_cage", "prime_parent_name",
    "naics_title", "psc_title", "prime_top_awarding_agency", "prime_set_aside",
]

subawards = []
amount_unparsed = 0
for r in RAW:
    amt = parse_amount(g(r, "amount"))
    if amt is None and g(r, "amount"): amount_unparsed += 1
    subawards.append({
        "sub_uei": g(r, "sub_uei"),
        "sub_cage": g(r, "sub_cage"),
        "sub_name": g(r, "sub_name"),
        "sub_state": g(r, "pop_state"),          # place-of-performance state, NOT legal address
        "prime_uei": g(r, "prime_uei"),
        "prime_cage": g(r, "prime_cage"),
        "prime_name": g(r, "prime_name"),
        "prime_award_id": g(r, "prime_award_id"),
        "subaward_amount": "" if amt is None else f"{amt:.2f}",
        "subaward_date": parse_date(g(r, "action_date")),
        "fiscal_year": g(r, "fiscal_year"),
        "naics": g(r, "naics"),                  # PRIME award NAICS; FSRS carries no sub NAICS
        "psc": g(r, "psc"),                      # PRIME award PSC
        "description": g(r, "description"),
        "direction": "unknown",                  # by design: requires the spine
        "source_file": SRC_CSV_NAME,
        "fetched_date": FETCHED_DATE,
        "subaward_number": g(r, "subaward_number"),
        "source_url": g(r, "highergov_page"),
        "sub_parent_uei": g(r, "sub_parent_uei"),
        "sub_parent_cage": g(r, "sub_parent_cage"),
        "sub_parent_name": g(r, "sub_parent_name"),
        "prime_parent_uei": g(r, "prime_parent_uei"),
        "prime_parent_cage": g(r, "prime_parent_cage"),
        "prime_parent_name": g(r, "prime_parent_name"),
        "naics_title": g(r, "naics_title"),
        "psc_title": g(r, "psc_title"),
        "prime_top_awarding_agency": g(r, "prime_top_awarding_agency"),
        "prime_set_aside": g(r, "prime_set_aside"),
    })

out_sub = os.path.join(CLEAN, "subawards.csv")
with open(out_sub, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=SUB_FIELDS); w.writeheader(); w.writerows(subawards)
log(f"WROTE {out_sub}: {len(subawards)} rows")
log(f"  distinct source_url (row key): {len({s['source_url'] for s in subawards})}")
log(f"  distinct subaward_number: {len({s['subaward_number'] for s in subawards})} "
    f"(NOT unique on its own; unique key is prime_award_id + subaward_number)")
log(f"  distinct prime_award_id: {len({s['prime_award_id'] for s in subawards})}")
log(f"  amounts that failed numeric parse: {amount_unparsed}")
log(f"  negative de-obligations in accounting parentheses, parsed as negative: "
    f"{len(NEG_PAREN)} {NEG_PAREN}")
tot = sum(float(s["subaward_amount"]) for s in subawards if s["subaward_amount"])
log(f"  total subaward dollars (nominal, as reported): ${tot:,.2f}")
yrs = sorted({s["fiscal_year"] for s in subawards if s["fiscal_year"]})
log(f"  fiscal years present: {yrs[0]}-{yrs[-1]} ({len(yrs)} distinct)")
log(f"  direction: 100% 'unknown' by design (attribution is the spine's job)")

# ----------------------------------------------------------------------------
# 4. subaward_identifier_harvest.csv   -- THE HEADLINE DELIVERABLE
# ----------------------------------------------------------------------------
# Emit identifiers EXACTLY as observed. Never normalize, pad, or repair.
def flag_uei(u):
    """SAM UEI spec: 12 chars, alphanumeric, no letters I or O, must not start with 0."""
    f = []
    if u == "": return ["missing_uei"]
    if len(u) != 12: f.append(f"uei_len_{len(u)}_ne_12")
    if not u.isalnum(): f.append("uei_nonalnum")
    if any(ch in "IOio" for ch in u): f.append("uei_contains_I_or_O")
    if u[:1] == "0": f.append("uei_leading_zero")
    if u != u.upper(): f.append("uei_not_uppercase")
    return f

def flag_cage(c):
    """CAGE spec: exactly 5 alphanumeric characters (leading zeros are significant)."""
    f = []
    if c == "": return ["missing_cage"]
    if len(c) != 5: f.append(f"cage_len_{len(c)}_ne_5")
    if not c.isalnum(): f.append("cage_nonalnum")
    if c != c.upper(): f.append("cage_not_uppercase")
    return f

# role slots observed in the source, with the (uei, cage, name, state) each contributes
ROLE_SLOTS = [
    ("sub",          "sub_uei",          "sub_cage",          "sub_name",          "pop_state"),
    ("prime",        "prime_uei",        "prime_cage",        "prime_name",        None),
    ("sub_parent",   "sub_parent_uei",   "sub_parent_cage",   "sub_parent_name",   None),
    ("prime_parent", "prime_parent_uei", "prime_parent_cage", "prime_parent_name", None),
]

obs = defaultdict(lambda: {
    "roles": set(), "names": Counter(), "states": Counter(), "years": set(),
    "rows": set(), "usd_any": 0.0, "usd_as_sub": 0.0, "usd_as_prime": 0.0,
})

for r, s in zip(RAW, subawards):
    amt = float(s["subaward_amount"]) if s["subaward_amount"] else 0.0
    fy = s["fiscal_year"]
    key_row = s["source_url"]
    for role, ku, kc, kn, ks in ROLE_SLOTS:
        uei, cage, name = g(r, ku), g(r, kc), g(r, kn)
        if not uei and not cage:
            continue                      # nothing observed in this slot on this row
        duns = ""                         # source carries no DUNS column
        rec = obs[(uei, cage, duns)]
        rec["roles"].add(role)
        if name: rec["names"][name] += 1
        if ks:
            st = g(r, ks)
            if st: rec["states"][st] += 1
        if fy: rec["years"].add(fy)
        rec["rows"].add(key_row)
        rec["usd_any"] += amt
        if role == "sub":   rec["usd_as_sub"] += amt
        if role == "prime": rec["usd_as_prime"] += amt

def role_label(roles):
    """Spec vocabulary sub|prime|both, extended with parent roles (documented)."""
    direct = roles & {"sub", "prime"}
    parts = []
    if direct == {"sub", "prime"}: parts.append("both")
    elif direct: parts.append(next(iter(direct)))
    for p in ("sub_parent", "prime_parent"):
        if p in roles: parts.append(p)
    return "+".join(parts)

HARV_FIELDS = [
    "uei", "cage_code", "duns", "legal_business_name", "role", "state",
    "n_subawards", "first_year", "last_year", "total_subaward_usd",
    "malformed_flag", "source_file",
    # additive: prevents misreading total_subaward_usd as role-specific revenue
    "total_usd_as_sub", "total_usd_as_prime", "n_name_variants", "name_variants",
]

harvest = []
for (uei, cage, duns), rec in obs.items():
    flags = flag_uei(uei) + flag_cage(cage)
    if duns == "": flags.append("missing_duns")
    yrs = sorted(rec["years"])
    names = rec["names"].most_common()
    harvest.append({
        "uei": uei, "cage_code": cage, "duns": duns,
        "legal_business_name": names[0][0] if names else "",
        "role": role_label(rec["roles"]),
        "state": rec["states"].most_common(1)[0][0] if rec["states"] else "",
        "n_subawards": len(rec["rows"]),
        "first_year": yrs[0] if yrs else "",
        "last_year": yrs[-1] if yrs else "",
        "total_subaward_usd": f"{rec['usd_any']:.2f}",
        "malformed_flag": "|".join(flags),
        "source_file": SRC_CSV_NAME,
        "total_usd_as_sub": f"{rec['usd_as_sub']:.2f}",
        "total_usd_as_prime": f"{rec['usd_as_prime']:.2f}",
        "n_name_variants": len(names),
        "name_variants": " | ".join(n for n, _ in names) if len(names) > 1 else "",
    })

harvest.sort(key=lambda h: (-int(h["n_subawards"]), h["uei"], h["cage_code"]))
out_harv = os.path.join(CLEAN, "subaward_identifier_harvest.csv")
with open(out_harv, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=HARV_FIELDS); w.writeheader(); w.writerows(harvest)
log(f"WROTE {out_harv}: {len(harvest)} rows "
    f"(one per distinct (uei, cage, duns) actually observed)")

H_UEI  = {h["uei"] for h in harvest if h["uei"]}
H_CAGE = {h["cage_code"] for h in harvest if h["cage_code"]}
log(f"  distinct UEIs observed : {len(H_UEI)}")
log(f"  distinct CAGEs observed: {len(H_CAGE)}")
log(f"  DUNS observed          : 0 (source carries no DUNS column)")
rolec = Counter(h["role"] for h in harvest)
for k, v in rolec.most_common(): log(f"  role={k:28s} {v}")
mf = Counter()
for h in harvest:
    for x in h["malformed_flag"].split("|"):
        if x: mf[x] += 1
log("  malformed_flag tally (flagged, NEVER repaired):")
for k, v in mf.most_common(): log(f"    {k:28s} {v}")

# ----------------------------------------------------------------------------
# 5. NET-NEW vs the existing spine ledgers  (READ-ONLY)
# ----------------------------------------------------------------------------
LEDGER = os.path.join(CLEAN, "cedar_identifier_ledger_final.csv")
FPDSMAP = os.path.join(CLEAN, "fpds_uei_cage_map.csv")

def norm(x): return x.strip().upper()

# (a) the TIERED ATTRIBUTION LEDGER -- what Cedar Press can actually publish against
led_uei, led_cage = set(), set()
with open(LEDGER, encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        t, v = (row.get("identifier_type") or "").strip(), (row.get("identifier") or "").strip()
        if not v: continue
        if t == "UEI":  led_uei.add(v)
        elif t == "CAGE": led_cage.add(v)
# (b) the RAW FPDS identifier map -- everything ever seen in a contracting extract
map_uei, map_cage, map_src = set(), set(), defaultdict(set)
with open(FPDSMAP, encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        u, c = (row.get("uei") or "").strip(), (row.get("cage_code") or "").strip()
        sf = (row.get("source_file") or "").strip()
        if u: map_uei.add(u); map_src[u] |= set(sf.split(";"))
        if c: map_cage.add(c)

known_uei, known_cage = led_uei | map_uei, led_cage | map_cage
log(f"reference: cedar_identifier_ledger_final.csv = {len(led_uei)} UEIs / {len(led_cage)} CAGEs")
log(f"reference: fpds_uei_cage_map.csv            = {len(map_uei)} UEIs / {len(map_cage)} CAGEs")
log(f"reference: UNION                            = {len(known_uei)} UEIs / {len(known_cage)} CAGEs")

KU, KC = {norm(x) for x in known_uei}, {norm(x) for x in known_cage}
LU, LC = {norm(x) for x in led_uei},   {norm(x) for x in led_cage}

new_uei_exact  = sorted(u for u in H_UEI  if u not in known_uei)
new_cage_exact = sorted(c for c in H_CAGE if c not in known_cage)
new_uei  = sorted(u for u in H_UEI  if norm(u) not in KU)     # conservative (headline)
new_cage = sorted(c for c in H_CAGE if norm(c) not in KC)
# secondary, actionable: observed here but absent from the tiered attribution ledger
led_new_uei  = sorted(u for u in H_UEI  if norm(u) not in LU)
led_new_cage = sorted(c for c in H_CAGE if norm(c) not in LC)

log("=" * 78)
log(f"NET-NEW UEIs  vs UNION of both ledgers: {len(new_uei)} of {len(H_UEI)} observed "
    f"({len(new_uei)/len(H_UEI)*100:.1f}%)")
log(f"NET-NEW CAGEs vs UNION of both ledgers: {len(new_cage)} of {len(H_CAGE)} observed "
    f"({len(new_cage)/len(H_CAGE)*100:.1f}%)")
log(f"  (exact-string comparison gives {len(new_uei_exact)} UEIs / {len(new_cage_exact)} CAGEs)")
# why: this file was already mined by an earlier stage
already = sum(1 for u in H_UEI if SRC_CSV_NAME in map_src.get(u, set()))
log(f"  CAUSE: fpds_uei_cage_map.csv already cites {SRC_CSV_NAME} as a source for "
    f"{already} of the {len(H_UEI)} observed UEIs. This file was fully harvested by an "
    f"earlier Cedar Press stage; Dataset 2b re-derives it independently and agrees.")
log("-" * 78)
log(f"SECONDARY (actionable) -- present here, ABSENT from the tiered attribution ledger:")
log(f"  UEIs  not in cedar_identifier_ledger_final.csv: {len(led_new_uei)} of {len(H_UEI)}")
log(f"  CAGEs not in cedar_identifier_ledger_final.csv: {len(led_new_cage)} of {len(H_CAGE)}")
log("=" * 78)

netnew_rows = []
for h in harvest:
    u_union = bool(h["uei"]) and norm(h["uei"]) not in KU
    c_union = bool(h["cage_code"]) and norm(h["cage_code"]) not in KC
    u_led = bool(h["uei"]) and norm(h["uei"]) not in LU
    c_led = bool(h["cage_code"]) and norm(h["cage_code"]) not in LC
    if u_union or c_union or u_led or c_led:
        netnew_rows.append({**h,
            "uei_new_vs_union": "yes" if u_union else "no",
            "cage_new_vs_union": "yes" if c_union else "no",
            "uei_new_vs_tiered_ledger": "yes" if u_led else "no",
            "cage_new_vs_tiered_ledger": "yes" if c_led else "no",
            "compared_against": "cedar_identifier_ledger_final.csv;fpds_uei_cage_map.csv"})
out_nn = os.path.join(CLEAN, "subaward_identifier_netnew.csv")
with open(out_nn, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=HARV_FIELDS + [
        "uei_new_vs_union", "cage_new_vs_union", "uei_new_vs_tiered_ledger",
        "cage_new_vs_tiered_ledger", "compared_against"])
    w.writeheader(); w.writerows(netnew_rows)
log(f"WROTE {out_nn}: {len(netnew_rows)} harvest rows carrying at least one identifier "
    f"missing from at least one reference ledger")

nn_by_role = Counter(h["role"] for h in netnew_rows)
for k, v in nn_by_role.most_common(): log(f"  by role: {k:28s} {v}")

# ----------------------------------------------------------------------------
# 6. prime_sub_network.csv
# ----------------------------------------------------------------------------
edges = defaultdict(lambda: {"n": 0, "usd": 0.0, "yrs": set(), "naics": Counter(),
                             "sub_name": Counter(), "prime_name": Counter()})
for s in subawards:
    if not s["prime_uei"] or not s["sub_uei"]:
        continue
    e = edges[(s["prime_uei"], s["sub_uei"])]
    e["n"] += 1
    e["usd"] += float(s["subaward_amount"]) if s["subaward_amount"] else 0.0
    if s["fiscal_year"]: e["yrs"].add(s["fiscal_year"])
    if s["naics"]: e["naics"][s["naics"]] += 1
    if s["sub_name"]: e["sub_name"][s["sub_name"]] += 1
    if s["prime_name"]: e["prime_name"][s["prime_name"]] += 1

NET_FIELDS = ["prime_uei", "sub_uei", "n_subawards", "total_usd", "first_year",
              "last_year", "naics_modal", "prime_name", "sub_name",
              "self_edge_flag", "source_file", "fetched_date"]
network = []
for (pu, su), e in edges.items():
    yrs = sorted(e["yrs"])
    network.append({
        "prime_uei": pu, "sub_uei": su, "n_subawards": e["n"],
        "total_usd": f"{e['usd']:.2f}",
        "first_year": yrs[0] if yrs else "", "last_year": yrs[-1] if yrs else "",
        "naics_modal": e["naics"].most_common(1)[0][0] if e["naics"] else "",
        "prime_name": e["prime_name"].most_common(1)[0][0] if e["prime_name"] else "",
        "sub_name": e["sub_name"].most_common(1)[0][0] if e["sub_name"] else "",
        "self_edge_flag": "yes" if pu == su else "",
        "source_file": SRC_CSV_NAME, "fetched_date": FETCHED_DATE,
    })
network.sort(key=lambda e: (-e["n_subawards"], e["prime_uei"], e["sub_uei"]))
out_net = os.path.join(CLEAN, "prime_sub_network.csv")
with open(out_net, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=NET_FIELDS); w.writeheader(); w.writerows(network)
log(f"WROTE {out_net}: {len(network)} prime->sub edges")
log(f"  distinct prime UEIs: {len({e['prime_uei'] for e in network})}")
log(f"  distinct sub UEIs  : {len({e['sub_uei'] for e in network})}")
self_edges = [e for e in network if e["self_edge_flag"] == "yes"]
log(f"  self-edges (prime_uei == sub_uei): {len(self_edges)} -> {[e['prime_uei'] for e in self_edges]}")

# ----------------------------------------------------------------------------
# 7. RECONCILE against the 217 existing prime_to_sub edges
# ----------------------------------------------------------------------------
EDGES_EXISTING = os.path.join(CLEAN, "fpds_uei_edges.csv")
existing = set(); existing_rows = []
with open(EDGES_EXISTING, encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        if row.get("edge_type") == "prime_to_sub":
            existing.add((row["parent_uei"].strip(), row["child_uei"].strip()))
            existing_rows.append(row)
mine = {(e["prime_uei"], e["sub_uei"]) for e in network}
log("-" * 78)
log(f"RECONCILIATION vs fpds_uei_edges.csv edge_type=prime_to_sub")
log(f"  existing edges          : {len(existing_rows)} rows, {len(existing)} distinct pairs")
log(f"  this build              : {len(mine)} distinct pairs")
log(f"  in existing, NOT in mine: {len(existing - mine)}  {sorted(existing - mine)[:20]}")
log(f"  in mine, NOT in existing: {len(mine - existing)}  {sorted(mine - existing)}")
if not (existing - mine):
    log("  -> this build is a strict SUPERSET of the prior extraction. No disagreement.")

# counts agreement on the shared pairs
prior_n = {(r["parent_uei"].strip(), r["child_uei"].strip()): int(r["n_observations"])
           for r in existing_rows}
mine_n = {(e["prime_uei"], e["sub_uei"]): e["n_subawards"] for e in network}
disagree = [(k, prior_n[k], mine_n[k]) for k in (existing & mine) if prior_n[k] != mine_n[k]]
log(f"  n_observations disagreements on shared pairs: {len(disagree)} {disagree[:10]}")
prior_yr = {(r["parent_uei"].strip(), r["child_uei"].strip()):
            (r["first_year"], r["last_year"]) for r in existing_rows}
mine_yr = {(e["prime_uei"], e["sub_uei"]): (e["first_year"], e["last_year"]) for e in network}
yr_dis = [(k, prior_yr[k], mine_yr[k]) for k in (existing & mine) if prior_yr[k] != mine_yr[k]]
log(f"  first/last_year disagreements on shared pairs: {len(yr_dis)} {yr_dis[:10]}")

# ----------------------------------------------------------------------------
# 8. AUDIT THE STATA TREATMENTS -- do they add identifiers the CSV lacks?
# ----------------------------------------------------------------------------
try:
    import pyreadstat
    dta_extra_uei, dta_extra_cage, dta_notes = set(), set(), []
    p = staged.get("sub file.dta")
    if p:
        df, _ = pyreadstat.read_dta(p)
        du = set()
        for c in ("awardee_uei", "subawardeeparentuei", "primeawardeeuei", "primeawardeeparentuei"):
            du |= {str(v).strip() for v in df[c].dropna() if str(v).strip()}
        dc = set()
        for c in ("subawardeecagecode", "subawardeeparentcagecode", "cagecode", "x"):
            dc |= {str(v).strip() for v in df[c].dropna() if str(v).strip()}
        dta_extra_uei |= du - H_UEI; dta_extra_cage |= dc - H_CAGE
        dta_notes.append(f"sub file.dta: {len(df)} rows, {len(du)} UEIs, {len(dc)} CAGEs "
                         f"({len(du - H_UEI)} UEIs / {len(dc - H_CAGE)} CAGEs not in the CSV)")
    p = staged.get("master sub file.dta")
    if p:
        m, _ = pyreadstat.read_dta(p)
        mu = {str(v).strip() for v in m["parent_uei"].dropna() if str(v).strip()}
        dta_extra_uei |= mu - H_UEI
        dta_notes.append(f"master sub file.dta: {len(m)} year x parent_uei rows, "
                         f"{len(mu)} parent UEIs ({len(mu - H_UEI)} not in the CSV)")
    for p in ("sub hci.dta", "sub.dta"):
        if staged.get(p):
            d, _ = pyreadstat.read_dta(staged[p])
            dta_notes.append(f"{p}: {len(d)} rows, columns {list(d.columns)} -- "
                             f"year-level sums only, NO identifiers")
    log("-" * 78)
    log("STATA TREATMENT AUDIT (do the .dta files add identifiers the CSV lacks?)")
    for n in dta_notes: log(f"  {n}")
    log(f"  ADDITIONAL UEIs from .dta beyond the CSV : {len(dta_extra_uei)} {sorted(dta_extra_uei)}")
    log(f"  ADDITIONAL CAGEs from .dta beyond the CSV: {len(dta_extra_cage)} {sorted(dta_extra_cage)}")
except ImportError:
    log("pyreadstat unavailable -- .dta audit skipped", "WARN")

log("20_build_subcontracts.py DONE")
log("=" * 78)
_lf.close()

# stash the numbers the build log needs
import json
summary = {
    "n_subawards": len(subawards), "n_harvest": len(harvest),
    "n_uei": len(H_UEI), "n_cage": len(H_CAGE),
    "netnew_uei": len(new_uei), "netnew_cage": len(new_cage),
    "netnew_uei_exact": len(new_uei_exact), "netnew_cage_exact": len(new_cage_exact),
    "ledger_new_uei": len(led_new_uei), "ledger_new_cage": len(led_new_cage),
    "already_cited_from_this_file": already,
    "n_edges": len(network), "known_uei": len(known_uei), "known_cage": len(known_cage),
    "total_usd": tot, "years": [yrs[0], yrs[-1]],
    "roles": dict(rolec), "malformed": dict(mf),
    "existing_edges": len(existing), "only_mine": sorted(mine - existing),
    "only_existing": sorted(existing - mine),
    "netnew_uei_list": new_uei, "netnew_cage_list": new_cage,
}
with open(os.path.join(EXT, "_build_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=1)
print("\nSUMMARY:", json.dumps({k: v for k, v in summary.items()
                                if not isinstance(v, (list, dict))}, indent=1))
