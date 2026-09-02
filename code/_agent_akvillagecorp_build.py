#!/usr/bin/env python3
"""Agent working script: build review/agent_rulings_akvillagecorp_2026-08-06.csv.

Not part of the pipeline. Writes one row at a time and flushes after each so a
dropped connection never leaves an empty file.

Slice: the 142 Alaska entities in review/unreconciled_entities.csv whose
entity_class is 'Alaska Native Village Corporation' (136) or
'ANCSA Group Corporation' (6).

The governing distinction: an ANCSA village CORPORATION is not the namesake
village GOVERNMENT. They are separate legal persons with separate money and,
as this script demonstrates, separate UEIs in the same federal datasets.
"""
import csv, json, re, sys
from collections import defaultdict, Counter
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
OUT = CEDAR / "review" / "agent_rulings_akvillagecorp_2026-08-06.csv"
DOCS = CEDAR / "code" / "_agent_akvillagecorp_docs.json"
COLS = ["review_id", "queue", "uei", "cage_code", "entity_or_firm",
        "question", "YOUR_RULING", "YOUR_NOTE"]

SUFFIX = (r"\b(corporation|corporations|corp|incorporated|incorporation|inc|"
          r"limited|ltd|llc|l l c|company|co|association|assoc|the|native|natives)\b")
JV_RE = re.compile(r"\b(jv|j v|joint venture)\b|jv[-\s]?\d|\bjv\d", re.I)


def core(n):
    n = n.lower()
    for ch in ".,'\u2019-/":
        n = n.replace(ch, " ")
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = re.sub(SUFFIX, " ", n)
    return " ".join(n.split())


def flat(n):
    n = n.lower()
    for ch in ".,'\u2019-/":
        n = n.replace(ch, " ")
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", n).split())


def rd(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


unrec = rd(CEDAR / "review" / "unreconciled_entities.csv")
MINE = [r for r in unrec if r["entity_class"] in
        ("Alaska Native Village Corporation", "ANCSA Group Corporation")]
MYIDS = {r["tribe_id"]: r for r in MINE}
spine = {r["tribe_id"]: r for r in rd(CEDAR / "data/spine/cedar_entity_spine.csv")}

cand = defaultdict(list)
for c in rd(CEDAR / "review" / "identifier_candidates_for_unreconciled.csv"):
    if c["tribe_id"] in MYIDS:
        cand[c["tribe_id"]].append(c)

ledger = defaultdict(list)
for r in rd(CEDAR / "data/clean/cedar_identifier_ledger_final.csv"):
    ledger[(r["identifier_type"].upper(), r["identifier"].strip().upper())].append(r)

DOCUMENTS = json.load(open(DOCS, encoding="utf-8")) if DOCS.exists() else {}

# raw recipient names that share a normalised core with one of my entities but
# are provably a different legal person
BLOCK_FLAT = {
    "ANVC-KSKKWM-00": {"kuskokwim native association", "kuskokwim native associaton",
                       "kuskokwim native assocation"},
}
EXTRA_CORE = {  # spelling variants the exact-core rule would miss
    "ANVC-CHCKL1-00": {"chickaloon moosecreek"},
    "ANVC-CHFRNR-00": {"chefarnmute"},
    "ANVC-PTKSPN-00": {"pitkas point"},
}

# Shee Atika: Elijah's own EXCL-0068 rules UEI LRJDF5JLG4X5 'not tribally owned',
# extracted from hci_analysis.do - a lower-48-tribe study in which ANCs appear
# only as scope exclusions (its twin, EXCL-0112, carries the ruling note "anc").
# An agent may not revise Elijah's ruling, so the whole family is held on one
# question rather than attributed.
FROZEN = {"ANVC-SHEEAT-00": (
    "Elijah's exclusion EXCL-0068 marks UEI LRJDF5JLG4X5 (Shee Atika, "
    "Incorporated) 'not tribally owned', evidence cage.dla.mil/Search/Details?"
    "id=714349, source hci_analysis.do line 1411. That do-file identifies "
    "lower-48 tribes only and, per the project's own audit, ANCs appear in it "
    "solely as exclusions - its sibling ruling EXCL-0112 carries the literal "
    "note 'anc'. So EXCL-0068 reads as a SCOPE exclusion from a lower-48 study, "
    "not a finding that the ANCSA urban corporation for Sitka is not Native-"
    "owned. An agent may not revise an Elijah ruling, so nothing here is "
    "attributed. ONE ruling from Elijah settles the whole family.")}

corp_ids = defaultdict(lambda: defaultdict(lambda: {
    "n": 0, "d": 0.0, "src": set(), "cfda": Counter(), "city": Counter(),
    "cage": set(), "name": Counter(), "selfpar": 0}))
subs = defaultdict(lambda: defaultdict(lambda: {
    "n": 0, "d": 0.0, "name": Counter(), "par": Counter(), "cage": set()}))

CORES = {}
for tid, r in MYIDS.items():
    CORES[tid] = ({core(r["canonical_name"])} | EXTRA_CORE.get(tid, set())) - {""}


def which(nm):
    c, f = core(nm), flat(nm)
    if not c:
        return []
    return [t for t, s in CORES.items()
            if c in s and f not in BLOCK_FLAT.get(t, set())]


for r in rd(CEDAR / "data/clean/federal_funding_transactions.csv"):
    u = (r["recipient_uei"] or "").strip().upper()
    if not u:
        continue
    try:
        d = float(r["obligated_usd"] or 0)
    except ValueError:
        d = 0.0
    for tid in which(r["recipient_name"]):
        e = corp_ids[tid][u]
        e["n"] += 1; e["d"] += d; e["src"].add("federal_funding")
        e["cfda"][r["cfda"]] += 1; e["name"][r["recipient_name"]] += 1
        e["city"][f"{r['recipient_city_name']}, {r['recipient_state_code']}"] += 1

for r in rd(CEDAR / "data/clean/faads_transactions.csv"):
    u = (r.get("recipient_uei") or "").strip().upper()
    if not u:
        continue
    try:
        d = float(r["obligated_usd"] or 0)
    except ValueError:
        d = 0.0
    for tid in which(r["recipient_name"]):
        e = corp_ids[tid][u]
        e["n"] += 1; e["d"] += d; e["src"].add("faads")
        e["cfda"][r.get("cfda_program", "")] += 1; e["name"][r["recipient_name"]] += 1
        e["city"][f"{r.get('recipient_city','')}, {r.get('recipient_state','')}"] += 1

prime = rd(CEDAR / "data/clean/prime_contracts.csv")
for r in prime:
    u = (r["awardee_uei"] or "").strip().upper()
    if not u:
        continue
    try:
        d = float(r["total_obligations"] or 0)
    except ValueError:
        d = 0.0
    for tid in which(r["awardee_name"]):
        e = corp_ids[tid][u]
        e["n"] += 1; e["d"] += d; e["src"].add("contracting")
        e["name"][r["awardee_name"]] += 1
        if (r["parent_uei"] or "").strip().upper() == u:
            e["selfpar"] += 1
        cg = (r["cage_code"] or "").strip().upper()
        if cg:
            e["cage"].add(cg)
        e["city"][f"{r.get('recipient_city_name','')}, "
                  f"{r.get('recipient_state_code','')}"] += 1

OWN = {tid: set(d) for tid, d in corp_ids.items()}
OWN_NAMES = {tid: {flat(n) for e in d.values() for n in e["name"]}
             for tid, d in corp_ids.items()}

# every declared non-self parent UEI per awardee, so a minority or conflicting
# declaration can be spotted rather than silently believed
declared = defaultdict(Counter)
for r in prime:
    u = (r["awardee_uei"] or "").strip().upper()
    pu = (r["parent_uei"] or "").strip().upper()
    if u and pu and pu != u:
        declared[u][pu] += 1

for r in prime:
    u = (r["awardee_uei"] or "").strip().upper()
    pu = (r["parent_uei"] or "").strip().upper()
    if not u or not pu or pu == u:
        continue
    try:
        d = float(r["total_obligations"] or 0)
    except ValueError:
        d = 0.0
    for tid, own in OWN.items():
        if pu in own:
            e = subs[tid][u]
            e["n"] += 1; e["d"] += d
            e["name"][r["awardee_name"]] += 1
            e["par"][f"{r.get('parent_name','')}|{pu}"] += 1
            cg = (r["cage_code"] or "").strip().upper()
            if cg:
                e["cage"].add(cg)

# a second UEI carrying a legal name already confirmed for the corporation
# total prime rows per awardee, so a lone parent declaration among hundreds of
# contrary ones is treated as the outlier it is rather than as ownership
awardee_rows = Counter((r["awardee_uei"] or "").strip().upper() for r in prime)


def hold_reason(tid, uei, firm):
    """Why this candidate subsidiary must not be attributed, or None."""
    if JV_RE.search(firm):
        return "jv"
    others = {p: n for p, n in declared[uei].items() if p not in OWN.get(tid, ())}
    mine_n = sum(n for p, n in declared[uei].items() if p in OWN.get(tid, ()))
    if others and mine_n <= sum(others.values()):
        return "conflict"
    tot = awardee_rows.get(uei, 0)
    if tot and mine_n and mine_n < 5 and mine_n / tot < 0.10:
        return "outlier"
    return None


HELD_SUB = set()
for tid, d0 in subs.items():
    for uei, e in d0.items():
        if hold_reason(tid, uei, e["name"].most_common(1)[0][0]):
            HELD_SUB.add((tid, uei))

# Suffix-stripped so "X, Llc" / "X Limited Liability Company" / "X Incorporated"
# collapse together (the DBA-variant collapse pattern). Three tokens minimum so
# nothing short and generic can collide. Firms that will be held are excluded so
# a held firm cannot smuggle its siblings in.
NAME2TID = defaultdict(set)
for tid, d0 in list(corp_ids.items()) + list(subs.items()):
    for uei, e in d0.items():
        if (tid, uei) in HELD_SUB:
            continue
        for n in e["name"]:
            c = core(n)
            if len(c.split()) >= 2:  # two tokens minimum: 'api' must not match
                NAME2TID[c].add(tid)
SIBLING = {}
for r in prime:
    u = (r["awardee_uei"] or "").strip().upper()
    if not u:
        continue
    hits = NAME2TID.get(core(r["awardee_name"]))
    if not hits:
        continue
    try:
        d = float(r["total_obligations"] or 0)
    except ValueError:
        d = 0.0
    for tid in hits:
        if u in OWN.get(tid, ()):
            continue
        if u in subs.get(tid, {}) and not SIBLING.get((tid, u)):
            continue
        SIBLING[(tid, u)] = True
        e = subs[tid][u]
        e["n"] += 1; e["d"] += d
        e["name"][r["awardee_name"]] += 1
        e["par"]["same legal name as a confirmed registration"] += 1

GOVT_RE = re.compile(
    r"\b(village|villages|tribal council|traditional council|community association|"
    r"ira council|tribe|city of|borough|housing authority|school district)\b", re.I)

ANCSA_CFDA = {
    "21.019": ("Treasury CARES Act Coronavirus Relief Fund - the Title V stream "
               "that Yellen v. Confederated Tribes of the Chehalis Reservation "
               "(2021) held ANCSA corporations eligible for, so an ANCSA "
               "corporation is exactly the kind of recipient expected here"),
    "10.912": ("NRCS Environmental Quality Incentives Program, a LANDOWNER "
               "payment - under ANCSA the corporation holds fee title to the "
               "village lands, the village government does not"),
    "10.914": "NRCS Wildlife Habitat Incentive Program, a landowner payment",
    "10.924": "NRCS Conservation Stewardship Program, a landowner payment",
    "15.055": ("BIA Alaskan Indian Allotments and Subsistence Preference "
               "(ANILCA), an Alaska-specific land program"),
    "15.241": "BIA Indian Self-Determination Act contracts and grants",
}

fh = open(OUT, "w", encoding="utf-8", newline="")
w = csv.DictWriter(fh, fieldnames=COLS)
w.writeheader()
fh.flush()
STATS = Counter()


def emit(rid, uei, cage, firm, question, ruling, note):
    w.writerow({"review_id": rid, "queue": "akvillagecorp", "uei": uei,
                "cage_code": cage, "entity_or_firm": firm, "question": question,
                "YOUR_RULING": ruling, "YOUR_NOTE": " ".join(note.split())})
    fh.flush()
    STATS["rows"] += 1
    STATS["hold" if ruling.startswith("HOLD")
          else "nosep" if ruling.startswith("NO SEPARATE")
          else "attributed"] += 1


def lstate(kind, ident):
    rows = ledger.get((kind, ident.upper()), [])
    if not rows:
        return "this identifier is not currently in cedar_identifier_ledger_final"
    return "; ".join(sorted({
        f"ledger today: {r['tribe_id'] or 'unattributed'}"
        f"/{r['canonical_name'] or '-'} tier {r['confidence_tier']}"
        f" ({r['attribution_method']})" for r in rows}))


def doc_for(tid, firmname):
    d = DOCUMENTS.get(tid)
    if not d:
        return None
    fn = flat(firmname)
    if any(n.strip() in fn for n in d.get("names", [])):
        return d
    return None


def M(d):
    return f"${d/1e6:.3f}M"


for r in MINE:
    tid, canon = r["tribe_id"], r["canonical_name"]
    sp = spine.get(tid, {})
    fr = (sp.get("fr_official_name") or "").strip()
    reg = (sp.get("ancsa_region_entity_id") or "").strip()
    own, mysubs = corp_ids.get(tid, {}), subs.get(tid, {})
    frozen = FROZEN.get(tid)
    emitted, attributed_any = set(), False

    for uei, e in sorted(own.items(), key=lambda x: -x[1]["d"]):
        emitted.add(uei.upper())
        firm = e["name"].most_common(1)[0][0]
        cg = ";".join(sorted(x for x in e["cage"] if x))
        q = (f"Does UEI {uei} ('{firm}') belong to {canon}, the ANCSA village "
             f"corporation, rather than to the namesake village government?")
        if frozen:
            emit(f"UEI:{uei}", uei, cg, firm, q,
                 "HOLD - Elijah's own exclusion governs this family",
                 f"{frozen} This identifier registers as '{firm}' in "
                 f"{'/'.join(sorted(e['src']))}, {e['n']} transactions, "
                 f"{M(e['d'])}. {lstate('UEI', uei)}.")
            continue
        cfl = [c for c in e["cfda"] if c]
        why = [ANCSA_CFDA[c] for c in cfl if c in ANCSA_CFDA]
        d = doc_for(tid, canon) or doc_for(tid, firm)
        struct = e["selfpar"] > 0
        note = (
            f"CONFIRMED as {canon}'s own identifier. The recipient legal name in "
            f"{'/'.join(sorted(e['src']))} is '{firm}', which normalises exactly "
            f"to the spine name for {canon}: {e['n']} transactions, {M(e['d'])}, "
            f"recipient city {'; '.join(sorted(e['city'])[:2])}. Assistance "
            f"programs on this identifier: {', '.join(cfl[:5]) or 'n/a'}."
            + (" " + why[0] + "." if why else "") +
            f" The namesake village GOVERNMENT files in the same datasets under a "
            f"different legal name and a different UEI, so this is the "
            f"corporation and not the government. {lstate('UEI', uei)}."
        )
        if struct:
            note += (f" Structural leg: the firm itself declares "
                     f"ultimate_parent_uei = {uei} on {e['selfpar']} FPDS prime "
                     f"awards, i.e. it registers as its own ultimate parent.")
        if d:
            note += f" Retrieved document: {d['url']} - {d['quote']}"
        if struct and d:
            note += (" TWO LEGS: firm-declared FPDS ultimate_parent_uei plus a "
                     "retrieved document.")
        else:
            note += (" ONE LEG only ("
                     + ("firm-declared FPDS parent" if struct else
                        "federal award recipient registration")
                     + (", no retrieved corporate document" if not d else
                        ", no FPDS parent record")
                     + "), so tier B - visible, not publishable.")
        emit(f"UEI:{uei}", uei, cg, firm, q, canon, note)
        attributed_any = True

    for uei, e in sorted(mysubs.items(), key=lambda x: -x[1]["d"]):
        if uei.upper() in emitted:
            continue
        emitted.add(uei.upper())
        firm = e["name"].most_common(1)[0][0]
        par = e["par"].most_common(1)[0][0]
        cg = ";".join(sorted(x for x in e["cage"] if x))
        q = f"Is {firm} (UEI {uei}) a subsidiary of {canon}?"
        others = {p: n for p, n in declared[uei].items() if p not in OWN.get(tid, ())}
        mine_n = sum(n for p, n in declared[uei].items() if p in OWN.get(tid, ()))
        if frozen:
            emit(f"UEI:{uei}", uei, cg, firm, q,
                 "HOLD - Elijah's own exclusion governs this family",
                 f"{frozen} FPDS declares this firm's ultimate parent as '{par}'. "
                 f"{e['n']} prime awards, {M(e['d'])}. {lstate('UEI', uei)}.")
            continue
        reason = None if SIBLING.get((tid, uei)) else hold_reason(tid, uei, firm)
        if reason == "outlier" and doc_for(tid, firm):
            d = doc_for(tid, firm)
            emit(f"UEI:{uei}", uei, cg, firm, q, canon,
                 f"CONFIRMED on the document leg alone. The FPDS parent field is "
                 f"NOT relied on here: only {mine_n} of {awardee_rows.get(uei,0)} "
                 f"prime rows name {canon} as ultimate parent, which is too thin "
                 f"to stand on. What does stand is the retrieved document: "
                 f"{d['url']} - {d['quote']} The firm carries that documented "
                 f"brand in its legal name. {e['n']} awards, {M(e['d'])}. "
                 f"{lstate('UEI', uei)}. ONE LEG (retrieved document), tier B.")
            continue
        if reason == "outlier":
            emit(f"UEI:{uei}", uei, cg, firm, q,
                 "HOLD - lone parent declaration among contrary ones",
                 f"FLAGGED, NOT ATTRIBUTED. Only {mine_n} of "
                 f"{awardee_rows.get(uei,0)} FPDS prime rows for this awardee "
                 f"name {canon}'s registration as ultimate parent; the rest "
                 f"declare the firm as its own parent. A single stray field is "
                 f"not evidence of ownership - it is as likely a data-entry "
                 f"artefact - so {M(e['d'])} is left unattributed rather than "
                 f"booked to {canon} on one row. {lstate('UEI', uei)}.")
            continue
        if reason == "jv":
            emit(f"UEI:{uei}", uei, cg, firm, q,
                 "HOLD - joint venture, ownership is shared",
                 f"FLAGGED, NOT ATTRIBUTED. FPDS declares ultimate parent '{par}' "
                 f"on {e['n']} prime awards, {M(e['d'])}, which does link this "
                 f"vehicle to {canon}. But the legal name is a joint venture, so "
                 f"the equity is shared with at least one other party and booking "
                 f"the whole obligation to {canon} would overstate it. Recorded "
                 f"the same way the Bristol Industries joint ownership was "
                 f"recorded rather than assigned. {lstate('UEI', uei)}.")
            continue
        if reason == "conflict":
            emit(f"UEI:{uei}", uei, cg, firm, q,
                 "HOLD - conflicting parent declarations",
                 f"FLAGGED, NOT ATTRIBUTED. FPDS carries more than one declared "
                 f"ultimate parent for this firm: {mine_n} award(s) name "
                 f"{canon}'s registration, but {sum(others.values())} name a "
                 f"different parent UEI ({', '.join(sorted(others)[:3])}). A "
                 f"minority declaration is not proof of ownership and could be a "
                 f"stale or mistyped FPDS field. {M(e['d'])} across {e['n']} "
                 f"awards left unattributed. {lstate('UEI', uei)}.")
            continue
        d = doc_for(tid, firm)
        if SIBLING.get((tid, uei)):
            note = (
                f"CONFIRMED as a second registration of a company already "
                f"confirmed under {canon}. This UEI carries the same legal name, "
                f"suffix variants aside, as a registration whose FPDS "
                f"ultimate_parent_uei is {canon}'s: {e['n']} prime awards, "
                f"{M(e['d'])}. Identifiers change on re-registration, so one "
                f"company legitimately holds several UEIs over time. "
                f"{lstate('UEI', uei)}. ONE LEG only (matching legal-name "
                f"registration; this UEI has no FPDS parent declaration of its "
                f"own), so tier B.")
        else:
            note = (
                f"CONFIRMED subsidiary of {canon}. Structural leg: on {e['n']} "
                f"FPDS prime awards ({M(e['d'])}) the firm itself declares its "
                f"ultimate_parent_uei as '{par}', which is {canon}'s own "
                f"registration. {lstate('UEI', uei)}."
            )
            if d:
                note += (f" Retrieved document: {d['url']} - {d['quote']} TWO "
                         f"LEGS: firm-declared FPDS ultimate_parent_uei plus a "
                         f"retrieved document naming this company in {canon}'s "
                         f"family.")
            else:
                note += (" ONE LEG only (firm-declared FPDS parent); no retrieved "
                         "corporate page names this company, so tier B.")
        emit(f"UEI:{uei}", uei, cg, firm, q, canon, note)
        attributed_any = True

    for c in cand.get(tid, []):
        for col in ("recipient_uei", "awardee_uei", "prime_uei", "sub_uei"):
            u = (c.get(col) or "").strip().upper()
            if not u or u in emitted:
                continue
            emitted.add(u)
            mn = c.get("matched_name", "")
            lg = ledger.get(("UEI", u), [])
            owner = lg[0]["tribe_id"] if lg else ""
            if core(mn) in CORES[tid]:
                emit(f"UEI:{u}", u, "", mn,
                     f"Is UEI {u} ('{mn}') {canon}'s?", canon,
                     f"CONFIRMED and REDIRECTED. '{mn}' normalises to {canon}'s "
                     f"own legal name. {lstate('UEI', u)} - if that shows an "
                     f"AKNF- village government, it is the corporation/government "
                     f"conflation this queue exists to fix. One evidence leg "
                     f"(registration name), tier B.")
                attributed_any = True
            elif "APACHE" in mn.upper():
                emit(f"UEI:{u}", u, "", mn,
                     f"Is UEI {u} ('{mn}') {canon}'s?",
                     "HOLD - not this entity; different tribe entirely",
                     f"REJECTED for {canon}. '{mn}' is the White Mountain Apache "
                     f"Tribe of Arizona, a lower-48 federally recognised tribe "
                     f"with no relation to the ANCSA village corporation at White "
                     f"Mountain, Alaska. The match is a 'White Mountain' token "
                     f"trap. {canon}'s own identifier is UEI FJD5P5RM49F4, ruled "
                     f"separately in this file. {lstate('UEI', u)}.")
            elif GOVT_RE.search(mn) or owner.startswith("AKNF-"):
                emit(f"UEI:{u}", u, "", mn,
                     f"Is UEI {u} ('{mn}') {canon}'s?",
                     "HOLD - not this entity; belongs to the namesake village "
                     "government",
                     f"REJECTED for {canon}. The proposed match was '{mn}', the "
                     f"Alaska Native village GOVERNMENT - a separate legal person "
                     f"from the ANCSA village corporation of the same place name. "
                     f"{lstate('UEI', u)}. Attributing it to {canon} would book "
                     f"tribal government money as corporation revenue, which is "
                     f"the error this queue exists to prevent. Held rather than "
                     f"excluded: the identifier is valid, it simply belongs to "
                     f"the government.")
            else:
                emit(f"UEI:{u}", u, "", mn,
                     f"Is UEI {u} ('{mn}') {canon}'s?",
                     "HOLD - insufficient evidence",
                     f"HELD for {canon}. Candidate string '{mn}' from dataset "
                     f"{c.get('dataset','')} at strength {c.get('strength','')}. "
                     f"It does not normalise to {canon}'s legal name and no firm-"
                     f"declared FPDS parent links it to {canon}, so there is no "
                     f"evidence leg to attribute on. {lstate('UEI', u)}.")
        cg = (c.get("cage_code") or "").strip().upper()
        if cg and f"CAGE:{cg}" not in emitted:
            emitted.add(f"CAGE:{cg}")
            mn = c.get("matched_name", "")
            if core(mn) in CORES[tid] and not frozen:
                emit(f"CAGE:{cg}", "", cg, mn,
                     f"Is CAGE {cg} ('{mn}') {canon}'s?", canon,
                     f"CONFIRMED. CAGE {cg} is registered to '{mn}', which "
                     f"normalises to {canon}'s legal name, and appears on the "
                     f"same FPDS prime awards as {canon}'s UEI. "
                     f"{lstate('CAGE', cg)}. One evidence leg (FPDS/SAM "
                     f"registration), tier B.")
                attributed_any = True
            else:
                emit(f"CAGE:{cg}", "", cg, mn,
                     f"Is CAGE {cg} ('{mn}') {canon}'s?",
                     "HOLD - not this entity; belongs to the namesake village "
                     "government",
                     f"REJECTED for {canon}. CAGE {cg} is registered to '{mn}', "
                     f"the village government rather than the ANCSA corporation. "
                     f"{lstate('CAGE', cg)}.")

    if not attributed_any and not frozen:
        reason = ("no UEI, CAGE or EIN appears under this corporation's legal "
                  "name, or any normalised variant of it, anywhere in the local "
                  "federal funding (2008-2023), FAADS, prime contracting, "
                  "subaward, lobbying or nonprofit files")
        if cand.get(tid):
            reason += ("; every candidate proposed for it resolved to the "
                       "namesake village government and was rejected above")
        emit(f"ENTITY:{tid}", "", "", canon,
             f"Does {canon} have any federal identifier of its own?",
             f"NO SEPARATE IDENTIFIER - {reason}",
             f"Searched exact legal name, spine aliases"
             + (f", Federal Register official name '{fr}'" if fr else "")
             + f", and a leading-token brand sweep across all six local datasets. "
             f"{reason}. The ANCSA region on the spine is {reg or 'none recorded'} "
             f"and is a statutory region, not an owner, so it supplies no "
             f"identifier. Recorded so this entity is not re-queried "
             f"indefinitely; revisit only if a new source is ingested.")

# A concurrent agent ran script 56 against an earlier draft of this file, so some
# identifiers are already in the ledger under rulings this final logic no longer
# makes. A HOLD is a no-op in script 56 and cannot undo an applied attribution,
# so each one is recorded explicitly as needing a retraction by hand.
APPLIED = CEDAR / "review" / "agent_identifier_rulings_applied.csv"
if APPLIED.exists():
    already = set()
    with open(OUT, encoding="utf-8-sig", newline="") as f2:
        for r in csv.DictReader(f2):
            already.add(r["review_id"].upper())
    fh = open(OUT, "a", encoding="utf-8", newline="")
    w = csv.DictWriter(fh, fieldnames=COLS)
    for a in rd(APPLIED):
        if OUT.name not in a.get("src", ""):
            continue
        rid = a["review_id"].upper()
        if rid in already:
            continue
        cur = ledger.get(tuple(rid.split(":", 1)), [])
        state = "; ".join(f"{x['tribe_id'] or 'unattributed'} tier "
                          f"{x['confidence_tier']}" for x in cur[:2]) or "absent"
        emit(rid, rid[4:] if rid.startswith("UEI:") else "",
             rid[5:] if rid.startswith("CAGE:") else "", a.get("firm", ""),
             f"Should the ledger keep the attribution of {rid} to "
             f"{a.get('ruling','')}?",
             "HOLD - RETRACTION REQUIRED, already written to the ledger from an "
             "earlier draft of this file",
             f"CORRECTION. A concurrent run of script 56 applied an earlier draft "
             f"of this file and wrote {rid} ('{a.get('firm','')}') to "
             f"{a.get('ruling','')} at tier {a.get('tier','')}. The final logic "
             f"here does NOT attribute it: either the only FPDS row naming that "
             f"parent is a lone outlier among contrary ones, or the legal name is "
             f"too generic to carry a same-name inference, or the related firm is "
             f"itself held for conflicting parent declarations. A HOLD cannot "
             f"reverse an applied attribution, so this needs a hand retraction in "
             f"the ledger. Current state: {state}.")
    fh.close()

print(f"wrote {OUT}")
for k, v in STATS.most_common():
    print(f"  {k:12s} {v}")
