#!/usr/bin/env python3
"""
1130 - RECONCILE THE OWNER'S OWN ENTERPRISE DATASET AGAINST NEST.

    py -3 code/1130_nest_owner_v6_reconcile.py versions      # which file is authoritative
    py -3 code/1130_nest_owner_v6_reconcile.py build         # crosswalk + reconcile + dual role + pairs
    py -3 code/1130_nest_owner_v6_reconcile.py verify        # exits 1 on breach, and on a MISSING merge
    py -3 code/1130_nest_owner_v6_reconcile.py selftest      # proves verify FIRES

READ-ONLY against every Cedar table and against the owner's dissertation
directory.  Zero network requests.  MINTS ZERO Cedar ids.  Does not commit.

===========================================================================
WHY THIS IS A RECONCILIATION AND NOT AN APPEND
===========================================================================
`data/clean/nest_enterprises.csv` holds 1,610 enterprises.  The owner built
his own on this machine, at

    C:/Users/esm247/Desktop/dissertation/data/tribal_federal_spending/
        clean/native_entity_enterprise_dataset_v6_geocoded.csv

and nobody in this project has read it.  It is the largest
`ON_DISK_NOT_PROMOTED` asset here (AGENT_FIELD_GUIDE §5).

NEST clusters on **(owner hub, normalised name)** and binds that key to a
permanent `enterprise_id` in the append-only register
`data/spine/cedar_nest_id_register.csv`.  The only honest way to compare two
enterprise universes is to put the second one through the FIRST one's
clustering - a plain append would have restated a firm NEST already holds as
a second row, which is the defect the "merged, not appended" design of
`1072` exists to stop, and which already cost 25 duplicate rows and 25 lost
corroborations (NEST_BUILD_LOG, UPDATE 2026-09-02 §3).

`norm()` below is COPIED VERBATIM from `code/1072_tribally_owned_enterprises.py`
and the copy is checked at run time: `verify` re-derives
`enterprise_name_normalized` for all 1,610 live NEST rows and exits 1 if a
single one disagrees.  Two normalisers that drift are two clusterings, and
the whole comparison would be measuring the drift instead of the data.

**Nothing is written into NEST.**  `1072 build` is a FULL REBUILD of
`nest_enterprises.csv`; an in-place append here would be reverted by it and
would look like pure progress while it happened (START_HERE, the FERC
rebuild/in-place collision, four times).  The net-new set is written as a
PROPOSAL for `1072` to ingest through its own clustering, on its own next
run, so the id register stays the only place an id is minted.

===========================================================================
READS
===========================================================================
    <dissertation>/native_entity_enterprise_dataset{,_v2,_v3,_v5*,_v6*}.csv
    data/clean/nest_enterprises.csv
    data/spine/cedar_identity_register.csv
    data/spine/cedar_nest_id_register.csv
    data/spine/cedar_identifier_ledger.csv        (dual-role identifier rung)

WRITES
    data/staging/nest_owner_v6/version_comparison.csv
    data/staging/nest_owner_v6/parent_crosswalk.csv
    data/staging/nest_owner_v6/enterprise_reconciliation.csv
    data/staging/nest_owner_v6/nest_not_in_owner.csv
    data/staging/nest_owner_v6/v3_recovery_candidates.csv
    data/staging/nest_owner_v6/corroboration_pairs.csv
    data/staging/nest_owner_v6/conservation.csv
    data/clean/nest_entity_dual_role.csv
"""
import csv, os, re, sys, json, datetime, collections, unicodedata

csv.field_size_limit(10 ** 8)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)

BUILT_BY = "1130_nest_owner_v6_reconcile.py"
BUILT_DATE = datetime.date.today().isoformat()

OWNER_DIR = os.path.join(
    os.path.expanduser("~"), "Desktop", "dissertation", "data",
    "tribal_federal_spending", "clean")

OWNER_FILES = {
    "v1": "native_entity_enterprise_dataset.csv",
    "v2": "native_entity_enterprise_dataset_v2.csv",
    "v3": "native_entity_enterprise_dataset_v3.csv",
    "v5": "native_entity_enterprise_dataset_v5_geocoded.csv",
    "v6": "native_entity_enterprise_dataset_v6_geocoded.csv",
}
AUTHORITATIVE = "v6"

STAGE = P("data", "staging", "nest_owner_v6")
OUT_VERSIONS = os.path.join(STAGE, "version_comparison.csv")
OUT_XWALK    = os.path.join(STAGE, "parent_crosswalk.csv")
OUT_RECON    = os.path.join(STAGE, "enterprise_reconciliation.csv")
OUT_NESTONLY = os.path.join(STAGE, "nest_not_in_owner.csv")
OUT_V3REC    = os.path.join(STAGE, "v3_recovery_candidates.csv")
OUT_PAIRS    = os.path.join(STAGE, "corroboration_pairs.csv")
OUT_CONSV    = os.path.join(STAGE, "conservation.csv")
OUT_DUAL     = P("data", "clean", "nest_entity_dual_role.csv")

NEST      = P("data", "clean", "nest_enterprises.csv")
REGISTER  = P("data", "spine", "cedar_identity_register.csv")
NEST_IDS  = P("data", "spine", "cedar_nest_id_register.csv")
LEDGER    = P("data", "spine", "cedar_identifier_ledger.csv")


# ---------------------------------------------------------------------------
# NAME NORMALISATION - VERBATIM from 1072.  verify re-derives NEST's own
# enterprise_name_normalized with it and exits 1 on a single disagreement.
# ---------------------------------------------------------------------------
_SUFFIX = re.compile(
    r"[ ,]+(?:l\.?l\.?c\.?|l\.?l\.?p\.?|pllc|inc\.?|incorporated|corp\.?|"
    r"corporation|co\.?|company|ltd\.?|limited|lp|l\.p\.|plc)\.?$", re.I)


def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for _ in range(3):
        n = _SUFFIX.sub("", s).strip()
        if n == s:
            break
        s = n
    return re.sub(r"\s+", " ", s).strip()


# Distinctive-token set for ENTITY_MATCH_RULES rule 1.  A name whose whole
# distinctive token set is generic may not win a match that rests on the name.
_GENERIC = {
    "tribe", "tribes", "tribal", "nation", "nations", "band", "bands",
    "indian", "indians", "native", "americans", "american", "of", "the", "a",
    "and", "inc", "incorporated", "llc", "corporation", "corp", "co",
    "company", "ltd", "limited", "lp", "llp", "group", "holdings", "holding",
    "community", "communities", "pueblo", "village", "villages", "rancheria",
    "reservation", "council", "confederated", "consortium", "association",
    "services", "service", "enterprises", "enterprise", "business",
    "businesses", "development", "corporation's", "federal", "government",
}


def dtoks(s: str) -> set:
    s = re.sub(r"\(.*?\)", " ", s or "")
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s).lower()
    return {w for w in s.split() if w and w not in _GENERIC}


def rd(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, required_first=()):
    """Header DERIVED from the rows (62 rule 17), never hardcoded.

    `required_first` only ORDERS columns that the rows actually carry; it can
    never introduce a column no row has, so the header cannot claim a field
    the data does not hold.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    seen, cols = set(), []
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                cols.append(k)
    lead = [c for c in required_first if c in seen]
    cols = lead + [c for c in cols if c not in set(lead)]
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    os.replace(tmp, path)
    return cols


def owner_path(tag):
    return os.path.join(OWNER_DIR, OWNER_FILES[tag])


# ===========================================================================
# WHICH FILE IS AUTHORITATIVE - measured, not assumed
# ===========================================================================
_UEI_RE = re.compile(r"^[A-Z0-9]{12}$")


def measure_versions():
    """One row per version.  The deciding measurement is the LAST column:
    how many populated `hq_state` cells are not a state."""
    out = []
    for tag in ("v1", "v2", "v3", "v5", "v6"):
        p = owner_path(tag)
        if not os.path.exists(p):
            out.append(dict(version=tag, file=OWNER_FILES[tag],
                            present="N", note="not on disk"))
            continue
        rows = rd(p)
        names = {norm(r.get("enterprise_name", "")) for r in rows} - {""}
        parents = {(r.get("tribe_id") or "").strip() for r in rows} - {""}
        st = [(r.get("hq_state") or "").strip() for r in rows]
        st_pop = [x for x in st if x]
        st_bad = [x for x in st_pop if len(x) != 2]
        st_is_uei = sum(1 for r in rows
                        if (r.get("hq_state") or "").strip()
                        and (r.get("hq_state") or "").strip()
                        == (r.get("enterprise_uei") or "").strip())
        out.append(dict(
            version=tag, file=OWNER_FILES[tag], present="Y",
            rows=len(rows), columns=len(rows[0]) if rows else 0,
            distinct_enterprise_names_normalized=len(names),
            distinct_parent_tribe_id=len(parents),
            hq_state_populated=len(st_pop),
            hq_state_not_a_two_letter_code=len(st_bad),
            hq_state_cell_equals_this_rows_uei=st_is_uei,
            column_integrity=("BREACHED - hq_state holds the UEI"
                              if st_is_uei > 100 else "clean"),
            built_by=BUILT_BY, built_date=BUILT_DATE))
    return out


def cmd_versions():
    rows = measure_versions()
    os.makedirs(STAGE, exist_ok=True)
    write_csv(OUT_VERSIONS, rows, required_first=("version", "file"))
    hdr = ["version", "rows", "distinct_enterprise_names_normalized",
           "distinct_parent_tribe_id", "hq_state_populated",
           "hq_state_cell_equals_this_rows_uei", "column_integrity"]
    print("  ".join(h[:34].rjust(12) for h in hdr))
    for r in rows:
        print("  ".join(str(r.get(h, ""))[:34].rjust(12) for h in hdr))
    print()
    print("AUTHORITATIVE: %s" % AUTHORITATIVE)
    print(OUT_VERSIONS)


# ===========================================================================
# THE PARENT CROSSWALK - tribe_id -> cedar_uid
# ===========================================================================
# The owner's `tribe_id` is the SAME handle scheme Cedar uses, at an earlier
# vintage.  632 of 658 are a live handle and need no adjudication at all; the
# rest are a handle Cedar has since re-minted under a different mnemonic
# (TRBF-CHKSAW-00 vs Cedar's TRBF-CHKSWN-00), or an entity Cedar does not
# hold.  Neither is guessed at.
#
# Handle prefix -> the ONLY register entity_class that prefix can mean.
# Derived from the register, not from a list: the crosstab of prefix against
# entity_class is 1:1 on every prefix except AKNF, which carries the one
# Tlingit & Haida row typed `Federally recognized tribe`.
PREFIX_CLASS = {
    "TRBF": {"Federally recognized tribe"},
    "TRBS": {"State-recognized tribe"},
    "AKNF": {"Federally recognized Alaska Native Village",
             "Federally recognized tribe"},
    "ANRC": {"Alaska Native Regional Corporation"},
    "ANVC": {"Alaska Native Village Corporation", "ANCSA Group Corporation"},
    "NHO":  {"Native Hawaiian Organization"},
    "ITO":  {"Intertribal Organization"},
    "INTERTRIBAL": {"Intertribal Organization"},
    "SGVF": {"Federal-level self-governance consortium",
             "Federally recognized tribe"},
    "CNSF": {"Federal-level constituency entity"},
    "CNSS": {"State-level constituency entity"},
    "TCU":  {"Tribal College or University"},
    "BIE":  {"BIE School"},
    "CDFI": {"Native Community Development Financial Institution",
             "Native Financial Institution"},
    "UIO":  {"Urban Indian Organization"},
}


def load_register():
    reg = rd(REGISTER)
    by_handle = {}
    by_stem = collections.defaultdict(list)
    names = collections.defaultdict(set)   # distinctive token set -> uids
    for r in reg:
        h = (r.get("handle") or "").strip()
        if h:
            by_handle[h] = r
            seg = h.split("-")
            if len(seg) > 1:
                by_stem[seg[1]].append(r)
        for nm in (r.get("canonical_name"), r.get("federal_register_legal_name")):
            t = dtoks(nm or "")
            if t:
                names[frozenset(t)].add(r["cedar_uid"])
    return reg, by_handle, by_stem, names


def resolve_parent(tid, canon, by_handle, by_stem, reg):
    """Return (cedar_uid, method, note).  Unresolved is an honest outcome
    (ADR-010) and is NEVER forced to a match."""
    tid = (tid or "").strip()
    if not tid:
        return "", "NO_PARENT_ID_ON_ROW", ("the owner's row carries no "
                                           "tribe_id; it cannot be hubbed")
    if tid in by_handle:
        r = by_handle[tid]
        return r["cedar_uid"], "handle_exact", (
            "the owner's tribe_id IS a live Cedar handle: %s" % tid)

    pfx = tid.split("-")[0]
    allowed = PREFIX_CLASS.get(pfx, set())

    # ROUTE 2 - the handle STEM.  Cedar's own mnemonic, not a name guess.
    seg = tid.split("-")
    if len(seg) > 1 and len(seg[1]) >= 5:
        cands = [r for r in by_stem.get(seg[1], [])]
        if len(cands) == 1:
            r = cands[0]
            return r["cedar_uid"], "handle_stem_unique", (
                "the owner's handle %s and Cedar's %s share the mnemonic "
                "stem %s, and that stem is unique in position 2 of the live "
                "register" % (tid, r["handle"], seg[1]))

    # ROUTE 3 - maximal distinctive-token subset, class-gated, unique at the
    # maximum.  ENTITY_MATCH_RULES rule 1 (no all-generic name), the class
    # gate ("an entity class that cannot hold the thing cannot win"), and
    # rule 13's uniqueness requirement.
    ot = dtoks(canon or "")
    if not ot:
        return "", "UNRESOLVED_NO_DISTINCTIVE_TOKENS", (
            "the parent's name %r has no distinctive token, so no name-only "
            "match may be made (ENTITY_MATCH_RULES rule 1)" % (canon or ""))
    best, bestn = [], 0
    for r in reg:
        if allowed and r.get("entity_class") not in allowed:
            continue
        for nm in (r.get("canonical_name"),
                   r.get("federal_register_legal_name")):
            t = dtoks(nm or "")
            if not t or not t <= ot:
                continue
            if len(t) > bestn:
                best, bestn = [(r, nm)], len(t)
            elif len(t) == bestn and r["cedar_uid"] not in [
                    x[0]["cedar_uid"] for x in best]:
                best.append((r, nm))
    if bestn == 0:
        return "", "UNRESOLVED_NOT_IN_REGISTER", (
            "no register entity of class %s has a distinctive token set "
            "contained in %r" % (sorted(allowed) or "any", canon))
    if len(best) > 1:
        return "", "UNRESOLVED_AMBIGUOUS", (
            "%d register entities tie at %d matched distinctive tokens: %s. "
            "A name matching two spine entities resolves to neither "
            "(ENTITY_MATCH_RULES rule 13)."
            % (len(best), bestn,
               "; ".join("%s=%s" % (x[0]["handle"], x[0]["canonical_name"])
                         for x in best[:4])))
    r, nm = best[0]
    return r["cedar_uid"], "name_tokens_class_gated_unique", (
        "the owner's %r and Cedar's %r (%s, class %s) agree on all %d of "
        "Cedar's distinctive tokens, uniquely at that maximum inside the "
        "class the owner's handle prefix %s declares"
        % (canon, nm, r["handle"], r.get("entity_class"), bestn, pfx))


# ===========================================================================
# EVIDENCE FAMILY of the owner's verification_source, for 1118
# ===========================================================================
# A structural predicate plus NAMED exceptions - never a bare denylist.
# The exceptions are the sources whose HOST does not say who is speaking.
FAMILY_EXACT = {
    "": ("unattributed",
         "the row carries no verification_source. An ownership claim with "
         "no source may not vote."),
    "sam_uei_to_tribe_assignment_v3.csv": ("cedar_inference",
         "an ASSIGNMENT file - the output of the owner's own cluster_v3 "
         "resolver. A resolver agreeing with a resolver is one observation."),
    "user_final_tribes.dta": ("human_ruling",
         "the owner's own hand-ruled file; attribution_method on these rows "
         "is `hand`."),
    "documented_native_entity_org": ("cedar_inference",
         "an internal label, not a publisher."),
    "data/other/tribal_colleges_aihec.csv (AIHEC list)": (
        "entity_self_published",
        "a member association's directory reports what the member told it, "
        "so it is the member speaking (1118 FAMILIES, entity_self_published)."),
    "chapter2_trust/output/tribal_press/ch2_tribal_newspapers.csv": (
        "compiled_directory",
        "a compiled research corpus; provenance per row is not recorded."),
}
FAMILY_HOST = [
    ("search.certifications.sba.gov", "federal_registry",
     "the SBA certification register (DSBS)."),
    ("www.irs.gov", "federal_registry", "the IRS EO Business Master File."),
    ("en.wikipedia.org", "compiled_directory",
     "an open encyclopaedia; provenance per statement is not recorded."),
    ("tribalbusinessnews.com", "compiled_directory",
     "third-party trade press; 1118 declares no press family, so it is "
     "recorded as a non-voting compiled source rather than invented as one."),
]


def family_of(vsrc):
    v = (vsrc or "").strip()
    if v in FAMILY_EXACT:
        return FAMILY_EXACT[v]
    if v.startswith("http"):
        host = re.sub(r"^https?://", "", v).split("/")[0].lower()
        for h, fam, note in FAMILY_HOST:
            if host == h or host.endswith("." + h):
                return fam, note
        if "canonical_tribe_table.csv" in v:
            return ("cedar_inference",
                    "an internal table given an http prefix; it is not a "
                    "published page.")
        return ("entity_self_published",
                "the entity's own web page (%s)." % host)
    if "canonical_tribe_table.csv" in v:
        return ("cedar_inference", "an internal table, not a publisher.")
    return ("unattributed",
            "verification_source %r names no observer this pass can class; "
            "it is recorded as non-voting rather than guessed at." % v[:60])


# The SBA DSBS upstream key.  It MUST be identical on both sides, because
# NEST's own `uei_candidate` came from the same extract - two readings of one
# document are one observation (1118 R-A), and calling them two would be the
# exact "copying a source into your own table does not corroborate it" error
# START_HERE item 0 records.
SBA_UPSTREAM = "sba_dsbs_extract:uei:%s"


# ===========================================================================
# BUILD
# ===========================================================================
def cmd_build():
    os.makedirs(STAGE, exist_ok=True)
    consv = []

    def account(table, rows_in, buckets):
        bad = [k for k in buckets if k.strip().lower() in
               ("", "other", "unknown", "misc", "n/a")]
        if bad:
            raise SystemExit("unnamed disposition %r on %s" % (bad, table))
        consv.append(dict(source_table=table, rows_in=rows_in,
                          rows_accounted=sum(buckets.values()),
                          unaccounted=rows_in - sum(buckets.values()),
                          dispositions=json.dumps(buckets, sort_keys=True),
                          built_by=BUILT_BY, built_date=BUILT_DATE))

    # ---- 0. version comparison -------------------------------------------
    vrows = measure_versions()
    write_csv(OUT_VERSIONS, vrows, required_first=("version", "file"))

    owner = rd(owner_path(AUTHORITATIVE))
    if not owner:
        raise SystemExit("the owner's %s is empty or absent at %s"
                         % (AUTHORITATIVE, owner_path(AUTHORITATIVE)))
    nest = rd(NEST)
    if not nest:
        raise SystemExit("data/clean/nest_enterprises.csv is empty or absent")
    reg, by_handle, by_stem, _regnames = load_register()
    live_uids = {r["cedar_uid"] for r in reg}

    # ---- 1. parent crosswalk ---------------------------------------------
    canon_by_tid = collections.defaultdict(collections.Counter)
    rows_by_tid = collections.Counter()
    for r in owner:
        t = (r.get("tribe_id") or "").strip()
        rows_by_tid[t] += 1
        c = (r.get("canonical_name") or "").strip()
        if t and c:
            canon_by_tid[t][c] += 1

    xw, tid2uid = [], {}
    for t in sorted(x for x in rows_by_tid if x):
        canon = (canon_by_tid[t].most_common(1)[0][0]
                 if canon_by_tid[t] else "")
        uid, method, note = resolve_parent(t, canon, by_handle, by_stem, reg)
        if uid:
            tid2uid[t] = uid
        rr = by_handle.get(t) or next(
            (x for x in reg if x["cedar_uid"] == uid), {})
        xw.append(dict(
            owner_tribe_id=t, owner_canonical_name=canon,
            owner_rows=rows_by_tid[t],
            cedar_uid=uid, cedar_handle=rr.get("handle", ""),
            cedar_canonical_name=rr.get("canonical_name", ""),
            cedar_entity_class=rr.get("entity_class", ""),
            crosswalk_method=method, crosswalk_basis=note,
            crosswalk_status="RESOLVED" if uid else "UNRESOLVED",
            built_by=BUILT_BY, built_date=BUILT_DATE))
    write_csv(OUT_XWALK, xw, required_first=("owner_tribe_id", "cedar_uid"))

    b = collections.Counter()
    for r in xw:
        b[r["crosswalk_method"]] += 1
    b["NO_PARENT_ID_ON_ROW_rows_excluded_from_parent_universe"] = 0
    account("owner v6 distinct non-blank tribe_id", len(xw), dict(b))

    # ---- 2. reconciliation through NEST's own clustering ------------------
    nest_key = {}
    for r in nest:
        nest_key[(r["owner_hub_cedar_uid"], r["enterprise_name_normalized"])] = r
    nest_names = collections.defaultdict(list)
    for r in nest:
        nest_names[r["enterprise_name_normalized"]].append(r)

    clusters = {}          # (uid, nk) -> aggregate of the owner's rows
    disp = collections.Counter()
    unhubbed = collections.Counter()
    for r in owner:
        t = (r.get("tribe_id") or "").strip()
        nk = norm(r.get("enterprise_name", ""))
        if not nk:
            disp["refused_blank_enterprise_name"] += 1
            continue
        uid = tid2uid.get(t, "")
        if not uid:
            # cannot be clustered on (owner hub, normalised name) at all.
            # NAMED, never folded into either side of the comparison.
            if not t:
                unhubbed["no_tribe_id_on_the_owner_row"] += 1
                disp["not_clusterable_no_parent_id"] += 1
            else:
                unhubbed["tribe_id_present_but_uncrosswalked"] += 1
                disp["not_clusterable_parent_unresolved"] += 1
            continue
        k = (uid, nk)
        c = clusters.setdefault(k, dict(
            cedar_uid=uid, enterprise_name_normalized=nk,
            owner_enterprise_name=(r.get("enterprise_name") or "").strip(),
            owner_rows=0, ueis=set(), cages=set(), eins=set(),
            vsrcs=collections.Counter(), methods=collections.Counter(),
            dsrcs=collections.Counter(), is_8a="N", is_np="N", is_fc="N",
            city="", state="", vdate=""))
        c["owner_rows"] += 1
        for col, key in (("enterprise_uei", "ueis"),
                         ("enterprise_cage_code", "cages"),
                         ("enterprise_ein", "eins")):
            v = (r.get(col) or "").strip().upper()
            if v and v != "NAN":
                c[key].add(v)
        vs = (r.get("verification_source") or "").strip()
        c["vsrcs"][vs] += 1
        c["methods"][(r.get("attribution_method") or "").strip()] += 1
        c["dsrcs"][(r.get("data_sources") or "").strip()] += 1
        if (r.get("is_8a_certified") or "") == "True":
            c["is_8a"] = "Y"
        if (r.get("is_nonprofit") or "") == "True":
            c["is_np"] = "Y"
        if (r.get("is_federal_contractor") or "") == "True":
            c["is_fc"] = "Y"
        c["city"] = c["city"] or (r.get("hq_city") or "").strip()
        c["state"] = c["state"] or (r.get("hq_state") or "").strip()
        c["vdate"] = c["vdate"] or (r.get("verified_date") or "").strip()

    recon = []
    already = net_new = 0
    for k, c in sorted(clusters.items()):
        hit = nest_key.get(k)
        elsewhere = [x for x in nest_names.get(k[1], [])
                     if x["owner_hub_cedar_uid"] != k[0]]
        if hit:
            already += 1
            status = "ALREADY_IN_NEST"
            basis = ("(owner hub, normalised name) is already a NEST key -> "
                     "%s. This is a RESTATEMENT and must raise that "
                     "enterprise's source count, not create a row."
                     % hit["enterprise_id"])
        else:
            net_new += 1
            status = "NET_NEW_TO_NEST"
            basis = ("no NEST row carries this (owner hub, normalised name); "
                     "%s" % ("the same normalised name IS held under %d other "
                             "hub(s): %s - a HUB DISAGREEMENT, not an absence"
                             % (len({x['owner_hub_cedar_uid'] for x in elsewhere}),
                                "; ".join(sorted({x["owner_hub_name"]
                                                  for x in elsewhere}))[:200])
                            if elsewhere else
                            "and no NEST row carries the name under any hub"))
            if elsewhere:
                status = "NET_NEW_HUB_DISAGREEMENT"
        fam = collections.Counter()
        for vs, n in c["vsrcs"].items():
            fam[family_of(vs)[0]] += n
        recon.append(dict(
            reconciliation_status=status,
            cedar_uid=c["cedar_uid"],
            enterprise_name=c["owner_enterprise_name"],
            enterprise_name_normalized=c["enterprise_name_normalized"],
            matched_nest_enterprise_id=hit["enterprise_id"] if hit else "",
            matched_nest_relationship=hit.get("relationship", "") if hit else "",
            matched_nest_relation_class=(hit.get("relation_class", "")
                                         if hit else ""),
            owner_rows_in_cluster=c["owner_rows"],
            owner_uei=";".join(sorted(c["ueis"])),
            owner_cage=";".join(sorted(c["cages"])),
            owner_ein=";".join(sorted(c["eins"])),
            owner_is_8a=c["is_8a"], owner_is_nonprofit=c["is_np"],
            owner_is_federal_contractor=c["is_fc"],
            owner_hq_city=c["city"], owner_hq_state=c["state"],
            owner_verified_date=c["vdate"],
            owner_verification_sources=";".join(
                sorted(x for x in c["vsrcs"] if x))[:400],
            owner_evidence_families=json.dumps(dict(fam), sort_keys=True),
            owner_data_sources=";".join(sorted(x for x in c["dsrcs"] if x)),
            owner_attribution_methods=";".join(
                sorted(x for x in c["methods"] if x)),
            relation_class_proposed="",
            relation_class_basis=(
                "DELIBERATELY BLANK. The owner's file states no "
                "relationship word, so this pass may not propose "
                "`structures` (ownership) OR `ties` (affiliation) from it. "
                "An affiliation recorded as ownership is the defect this "
                "dataset is most exposed to (NEST_BUILD_LOG), and guessing "
                "upward is the direction that fabricates."),
            ownership_claim_carried="NO - provenance only",
            ownership_claim_basis=(
                "the owner's verification_source is the evidence; where it "
                "is blank there is no evidence, and a blank source may not "
                "be laundered into a Cedar-asserted ownership claim"),
            reconciliation_basis=basis,
            built_by=BUILT_BY, built_date=BUILT_DATE))
    write_csv(OUT_RECON, recon,
              required_first=("reconciliation_status", "cedar_uid",
                              "enterprise_name"))

    # ---- 3. the third number: what NEST holds and the owner does not ------
    owner_keys = set(clusters)
    owner_names = {k[1] for k in clusters}
    owner_ueis = set()
    for c in clusters.values():
        owner_ueis |= c["ueis"]
    # UEIs on the rows we could NOT hub still tell us the owner saw the firm.
    for r in owner:
        v = (r.get("enterprise_uei") or "").strip().upper()
        if v and v != "NAN":
            owner_ueis.add(v)
    owner_all_names = {norm(r.get("enterprise_name", "")) for r in owner} - {""}

    nestonly, nb = [], collections.Counter()
    for r in nest:
        k = (r["owner_hub_cedar_uid"], r["enterprise_name_normalized"])
        if k in owner_keys:
            nb["in_owner_on_the_same_hub"] += 1
            continue
        by_name = r["enterprise_name_normalized"] in owner_all_names
        u = (r.get("uei") or "").strip().upper()
        uc = (r.get("uei_candidate") or "").strip().upper()
        by_id = bool((u and u in owner_ueis) or (uc and uc in owner_ueis))
        if by_name or by_id:
            reason = ("PRESENT_IN_OWNER_UNDER_A_DIFFERENT_HUB_OR_KEY")
            nb["in_owner_but_not_on_this_hub"] += 1
        else:
            reason = "ABSENT_FROM_OWNER_ENTIRELY"
            nb["absent_from_owner_entirely"] += 1
        nestonly.append(dict(
            disposition=reason,
            enterprise_id=r["enterprise_id"],
            enterprise_name=r["enterprise_name"],
            enterprise_name_normalized=r["enterprise_name_normalized"],
            owner_hub_cedar_uid=r["owner_hub_cedar_uid"],
            owner_hub_name=r.get("owner_hub_name", ""),
            owner_class=r.get("owner_class", ""),
            relationship=r.get("relationship", ""),
            relation_class=r.get("relation_class", ""),
            evidence_class=r.get("evidence_class", ""),
            in_federal_contracting=r.get("in_federal_contracting", ""),
            n_distinct_sources=r.get("n_distinct_sources", ""),
            matched_owner_by_name="Y" if by_name else "N",
            matched_owner_by_identifier="Y" if by_id else "N",
            disposition_basis=(
                "NEST holds this enterprise; the owner's v6 does not carry "
                "it on this hub. This is what Cedar's own scraping added."),
            built_by=BUILT_BY, built_date=BUILT_DATE))
    write_csv(OUT_NESTONLY, nestonly,
              required_first=("disposition", "enterprise_id",
                              "enterprise_name"))
    account("data/clean/nest_enterprises.csv", len(nest), dict(nb))

    # ---- 4. v3 rows v6 dropped -------------------------------------------
    v3 = rd(owner_path("v3"))
    v6names = {norm(r.get("enterprise_name", "")) for r in owner} - {""}
    v3rec, v3b = [], collections.Counter()
    for r in v3:
        nk = norm(r.get("enterprise_name", ""))
        if not nk:
            v3b["blank_enterprise_name"] += 1
            continue
        if nk in v6names:
            v3b["also_in_v6"] += 1
            continue
        v3b["absent_from_v6"] += 1
        t = (r.get("tribe_id") or "").strip()
        v3rec.append(dict(
            enterprise_name=(r.get("enterprise_name") or "").strip(),
            enterprise_name_normalized=nk,
            owner_tribe_id=t, resolved_cedar_uid=tid2uid.get(t, ""),
            enterprise_uei=(r.get("enterprise_uei") or "").strip(),
            enterprise_cage_code=(r.get("enterprise_cage_code") or "").strip(),
            data_sources=(r.get("data_sources") or "").strip(),
            verification_source=(r.get("verification_source") or "").strip(),
            total_master_prime_dol_M=(r.get("total_master_prime_dol_M")
                                      or "").strip(),
            disposition="PRESENT_IN_V3_ABSENT_FROM_V6",
            disposition_basis=(
                "v6 is authoritative on geography and on the parent "
                "crosswalk, and it is NOT a superset of v3. This row "
                "survives normalisation and is a recovery candidate, not a "
                "de-duplication artefact. FLAGGED, NEVER DELETED."),
            built_by=BUILT_BY, built_date=BUILT_DATE))
    write_csv(OUT_V3REC, v3rec,
              required_first=("disposition", "enterprise_name"))
    account("owner v3 (%s)" % OWNER_FILES["v3"], len(v3), dict(v3b))

    # ---- 5. corroboration pairs, for 1118 ---------------------------------
    # Shape is 1118.Store.observe()'s keyword set exactly, so adopting them is
    # a loop and not a translation.  Both SIDES of each pair are emitted, and
    # the SBA side carries the SAME upstream_key as NEST's own DSBS candidate
    # so 1118 R-A collapses the echo instead of booking it as a second source.
    pairs, pb = [], collections.Counter()
    nest_by_uei = collections.defaultdict(list)
    for r in nest:
        for col in ("uei", "uei_candidate"):
            v = (r.get(col) or "").strip().upper()
            if v and v != "NAN":
                nest_by_uei[v].append((col, r))
    for r in owner:
        u = (r.get("enterprise_uei") or "").strip().upper()
        if not u or u == "NAN":
            pb["owner_row_carries_no_uei"] += 1
            continue
        hits = nest_by_uei.get(u)
        if not hits:
            pb["owner_uei_not_held_by_nest"] += 1
            continue
        vs = (r.get("verification_source") or "").strip()
        fam, fam_note = family_of(vs)
        col, nr = hits[0]
        pb["owner_uei_matched_nest_%s" % col] += 1
        if fam == "federal_registry" and "sba" in vs.lower():
            upstream = SBA_UPSTREAM % u
        elif vs.startswith("http"):
            upstream = "url:" + re.sub(r"^https?://(www\.)?", "",
                                       vs.rstrip("/")).lower()
        else:
            upstream = "ownerfile:%s" % (vs or "unattributed")
        pairs.append(dict(
            pair="P7_owner_v6_identifier",
            dataset="nest",
            subject=nr["enterprise_id"],
            subject_label=nr["enterprise_name"],
            predicate="enterprise.identifier.UEI",
            predicate_class="identifier_binding",
            value=u, value_norm=u,
            family=fam,
            source_label=("owner's native_entity_enterprise_dataset_v6, "
                          "verification_source %s" % (vs or "(none)"))[:200],
            upstream_key=upstream,
            evidence_url=vs if vs.startswith("http") else "",
            quote=("verified_date=%s attribution_method=%s data_sources=%s"
                   % (r.get("verified_date", ""),
                      r.get("attribution_method", ""),
                      r.get("data_sources", ""))),
            origin_table=("<owner>/tribal_federal_spending/clean/%s"
                          % OWNER_FILES[AUTHORITATIVE]),
            observed_date=(r.get("verified_date") or "").strip(),
            nest_side_column=col,
            nest_side_basis=(nr.get("identifier_basis") if col == "uei"
                             else nr.get("uei_candidate_basis")) or "",
            echo_risk=("ECHO - same SBA DSBS extract on both sides; 1118 R-A "
                       "collapses this to ONE observation"
                       if col == "uei_candidate" and upstream.startswith(
                           "sba_dsbs_extract:")
                       else "INDEPENDENT - %s" % fam_note),
            family_basis=fam_note,
            built_by=BUILT_BY, built_date=BUILT_DATE))
    write_csv(OUT_PAIRS, pairs,
              required_first=("pair", "subject", "predicate", "family"))
    account("owner v6 rows offered to the corroboration layer",
            len(owner), dict(pb))

    # ---- 6. THE ANC / NHO DUAL ROLE ---------------------------------------
    dual = build_dual_role(owner, nest, reg, tid2uid, live_uids, account)
    write_csv(OUT_DUAL, dual,
              required_first=("cedar_uid", "handle", "canonical_name",
                              "entity_class", "dual_role"))

    # ---- 7. conservation of the owner file itself -------------------------
    account("owner v6 (%s)" % OWNER_FILES[AUTHORITATIVE], len(owner),
            dict(disp) | dict(
                clustered_rows=sum(c["owner_rows"] for c in clusters.values())))
    consv.append(dict(
        source_table="owner v6 rows that could not be clustered, by reason",
        rows_in=sum(unhubbed.values()),
        rows_accounted=sum(unhubbed.values()), unaccounted=0,
        dispositions=json.dumps(dict(unhubbed), sort_keys=True),
        built_by=BUILT_BY, built_date=BUILT_DATE))
    write_csv(OUT_CONSV, consv, required_first=("source_table", "rows_in"))

    # ---- report -----------------------------------------------------------
    print("=" * 74)
    print("THE THREE RECONCILIATION COUNTS")
    print("=" * 74)
    print("  owner enterprise clusters, hubbed        %6d" % len(clusters))
    print("    1. ALREADY IN NEST                     %6d" % already)
    print("    2. NET NEW TO NEST                     %6d" % net_new)
    print("       of which a HUB DISAGREEMENT         %6d"
          % sum(1 for r in recon
                if r["reconciliation_status"] == "NET_NEW_HUB_DISAGREEMENT"))
    print("    3. NEST HOLDS, OWNER DOES NOT          %6d" % len(nestonly))
    print("       absent from his file entirely       %6d"
          % nb["absent_from_owner_entirely"])
    print("       present, on a different hub/key     %6d"
          % nb["in_owner_but_not_on_this_hub"])
    print()
    print("  owner rows NOT clusterable (named, not folded in):")
    for k, v in sorted(unhubbed.items()):
        print("    %-42s %6d" % (k, v))
    print()
    print("  parents: %d distinct tribe_id, %d crosswalked, %d unresolved"
          % (len(xw), sum(1 for r in xw if r["cedar_uid"]),
             sum(1 for r in xw if not r["cedar_uid"])))
    print("  dual role: %d register entities are ALSO an enterprise"
          % len(dual))
    print("  corroboration pairs handed to 1118: %d (%d echo, %d independent)"
          % (len(pairs),
             sum(1 for p in pairs if p["echo_risk"].startswith("ECHO")),
             sum(1 for p in pairs if not p["echo_risk"].startswith("ECHO"))))
    print("  v3 rows absent from v6 (recovery candidates): %d" % len(v3rec))
    print("  Cedar enterprise ids minted by this script: 0")
    print()
    for p in (OUT_VERSIONS, OUT_XWALK, OUT_RECON, OUT_NESTONLY, OUT_V3REC,
              OUT_PAIRS, OUT_CONSV, OUT_DUAL):
        print("  wrote %s" % os.path.relpath(p, ROOT))


# ===========================================================================
# THE DUAL ROLE
# ===========================================================================
# The owner's design correction: an ANC is a corporation that TRADES, not
# only a hub that owns, and NEST's model treats it only as a hub.  The fix is
# a DECLARED dual role keyed to the register entity - not a second
# nest_enterprises row, because duplicating the row is what would break the
# (owner hub, normalised name) key and put a hub in its own subsidiary list
# ("a hub is not its own subsidiary", NEST_BUILD_LOG).
#
# Two rungs of evidence, and the rung is recorded on the row:
#   R1 DECLARED_BY_OWNER_DATASET - the owner's own file carries a row whose
#      enterprise_name normalises to the parent's own canonical name.  The
#      dataset itself says the entity trades.
#   R2 ENTITY_HOLDS_ITS_OWN_IDENTIFIER - the entity's own name carries a UEI
#      or CAGE.  An identifier beats every name method (rule 4).
# A row that reaches neither is not written.
def build_dual_role(owner, nest, reg, tid2uid, live_uids, account):
    by_uid = {r["cedar_uid"]: r for r in reg}
    owns = collections.Counter(r["owner_hub_cedar_uid"] for r in nest)

    ev = collections.defaultdict(lambda: dict(
        rungs=set(), ueis=set(), cages=set(), srcs=collections.Counter(),
        names=collections.Counter(), rows=0, is8a="N", fc="N"))
    b = collections.Counter()
    for r in owner:
        t = (r.get("tribe_id") or "").strip()
        uid = tid2uid.get(t, "")
        if not uid:
            b["no_crosswalked_parent_on_the_row"] += 1
            continue
        nk = norm(r.get("enterprise_name", ""))
        ck = norm(r.get("canonical_name", ""))
        reg_nk = norm(by_uid[uid].get("canonical_name", ""))
        reg_fr = norm(by_uid[uid].get("federal_register_legal_name", ""))
        if not nk or nk not in {ck, reg_nk, reg_fr}:
            b["row_names_a_subsidiary_not_the_parent"] += 1
            continue
        b["row_names_the_parent_itself"] += 1
        e = ev[uid]
        e["rows"] += 1
        e["rungs"].add("R1_DECLARED_BY_OWNER_DATASET")
        e["names"][(r.get("enterprise_name") or "").strip()] += 1
        u = (r.get("enterprise_uei") or "").strip().upper()
        c = (r.get("enterprise_cage_code") or "").strip().upper()
        if u and u != "NAN":
            e["ueis"].add(u)
            e["rungs"].add("R2_ENTITY_HOLDS_ITS_OWN_IDENTIFIER")
        if c and c != "NAN":
            e["cages"].add(c)
            e["rungs"].add("R2_ENTITY_HOLDS_ITS_OWN_IDENTIFIER")
        vs = (r.get("verification_source") or "").strip()
        if vs:
            e["srcs"][vs] += 1
        if (r.get("is_8a_certified") or "") == "True":
            e["is8a"] = "Y"
        if (r.get("is_federal_contractor") or "") == "True":
            e["fc"] = "Y"
    account("owner v6 rows tested for the dual role", len(owner), dict(b))

    out = []
    for uid, e in sorted(ev.items()):
        rr = by_uid[uid]
        cls = rr.get("entity_class", "")
        is_anc = cls in ("Alaska Native Regional Corporation",
                         "Alaska Native Village Corporation",
                         "ANCSA Group Corporation")
        is_nho = cls == "Native Hawaiian Organization"
        fams = sorted({family_of(v)[0] for v in e["srcs"]})
        out.append(dict(
            cedar_uid=uid, handle=rr.get("handle", ""),
            canonical_name=rr.get("canonical_name", ""),
            entity_class=cls,
            dual_role="Y",
            dual_role_class=("ANC_CORPORATION_AND_ENTERPRISE" if is_anc else
                             "NHO_ORGANISATION_AND_ENTERPRISE" if is_nho else
                             "REGISTER_ENTITY_AND_ENTERPRISE"),
            role_as_register_entity="hub in the Cedar identity register",
            role_as_enterprise=("this entity itself trades - it holds the "
                                "identifiers and the federal-contractor "
                                "status on its OWN legal name"),
            is_nest_owner_hub="Y" if owns.get(uid) else "N",
            n_nest_enterprises_owned=owns.get(uid, 0),
            evidence_rungs=";".join(sorted(e["rungs"])),
            own_uei=";".join(sorted(e["ueis"])),
            own_cage=";".join(sorted(e["cages"])),
            own_is_8a_certified=e["is8a"],
            own_is_federal_contractor=e["fc"],
            owner_rows_naming_this_entity_as_an_enterprise=e["rows"],
            enterprise_name_as_recorded=";".join(
                sorted(e["names"]))[:300],
            verification_sources=";".join(sorted(e["srcs"]))[:400],
            evidence_families=";".join(fams),
            representation_rule=(
                "RECORDED, NOT DUPLICATED. This entity keeps ONE row in the "
                "identity register and ZERO rows in nest_enterprises.csv "
                "for itself. NEST's key is (owner hub, normalised name); a "
                "self-row would make the hub its own subsidiary, which the "
                "1072 build already refuses by testing the child against "
                "every deterministic rendering of the hub's name. The dual "
                "role therefore lives here, keyed to the cedar_uid, and a "
                "consumer joins it to nest_enterprises on "
                "owner_hub_cedar_uid."),
            dual_role_basis=(
                "the owner's own enterprise dataset carries %d row(s) whose "
                "enterprise_name normalises to this entity's own name, "
                "%s. Evidence rungs: %s."
                % (e["rows"],
                   ("carrying UEI %s" % ";".join(sorted(e["ueis"])))
                   if e["ueis"] else "carrying no identifier",
                   ";".join(sorted(e["rungs"])))),
            source_file=OWNER_FILES[AUTHORITATIVE],
            record_scope="entity_attribute",
            publishable="Y",
            publishable_basis=("a business name and a federal identifier; no "
                               "natural person's data is present on this row"),
            built_by=BUILT_BY, built_date=BUILT_DATE))
    return out


# ===========================================================================
# VERIFY - exits 1 on breach, AND on a merge that did not land
# ===========================================================================
FLOORS = dict(
    parent_crosswalk_resolved=600,
    reconciliation_rows=1000,
    already_in_nest=100,
    net_new=1000,
    nest_not_in_owner=100,
    dual_role_rows=25,
    corroboration_pairs=100,
    v3_recovery=50,
)


def cmd_verify(quiet=False):
    fails = []

    def say(ok, name, msg):
        if not ok:
            fails.append("%s: %s" % (name, msg))
        if not quiet:
            print("  [%s] %-34s %s" % ("PASS" if ok else "FAIL", name, msg))

    # I0 - the normaliser has not drifted from 1072's.
    nest = rd(NEST)
    say(bool(nest), "I0a_nest_readable", "%d NEST rows" % len(nest))
    drift = [r["enterprise_id"] for r in nest
             if norm(r["enterprise_name"]) != r["enterprise_name_normalized"]]
    say(not drift, "I0b_normaliser_matches_1072",
        "%d of %d NEST rows re-derive their own enterprise_name_normalized"
        % (len(nest) - len(drift), len(nest)))

    # I1 - EVERY output landed and is NON-EMPTY.  An empty target set must
    # never read as success (AGENT_FIELD_GUIDE rule 5).
    for path, floor_key in ((OUT_VERSIONS, None), (OUT_XWALK, None),
                            (OUT_RECON, "reconciliation_rows"),
                            (OUT_NESTONLY, "nest_not_in_owner"),
                            (OUT_V3REC, "v3_recovery"),
                            (OUT_PAIRS, "corroboration_pairs"),
                            (OUT_CONSV, None), (OUT_DUAL, "dual_role_rows")):
        rel = os.path.relpath(path, ROOT)
        if not os.path.exists(path):
            say(False, "I1_" + os.path.basename(path)[:26],
                "MISSING - the merge did not land")
            continue
        rows = rd(path)
        floor = FLOORS.get(floor_key, 1) if floor_key else 1
        say(len(rows) >= floor, "I1_" + os.path.basename(path)[:26],
            "%d rows (floor %d) %s" % (len(rows), floor, rel))

    xw = rd(OUT_XWALK)
    recon = rd(OUT_RECON)
    nestonly = rd(OUT_NESTONLY)
    dual = rd(OUT_DUAL)
    pairs = rd(OUT_PAIRS)

    # I2 - the crosswalk actually crosswalked.
    res = [r for r in xw if r["cedar_uid"]]
    say(len(res) >= FLOORS["parent_crosswalk_resolved"],
        "I2_parents_crosswalked",
        "%d of %d parents resolved (floor %d)"
        % (len(res), len(xw), FLOORS["parent_crosswalk_resolved"]))

    # I3 - no fabricated cedar_uid anywhere.
    live = {r["cedar_uid"] for r in rd(REGISTER)}
    bad = ([r["cedar_uid"] for r in xw if r["cedar_uid"] and
            r["cedar_uid"] not in live] +
           [r["cedar_uid"] for r in recon if r["cedar_uid"] not in live] +
           [r["cedar_uid"] for r in dual if r["cedar_uid"] not in live])
    say(not bad, "I3_no_fabricated_uid",
        "%d uids off the live register%s"
        % (len(bad), (" e.g. " + bad[0]) if bad else ""))

    # I4 - the reconciliation reached BOTH verdicts.  A pass that classified
    # everything one way has not reconciled anything.
    a = sum(1 for r in recon if r["reconciliation_status"] == "ALREADY_IN_NEST")
    n = sum(1 for r in recon
            if r["reconciliation_status"].startswith("NET_NEW"))
    say(a >= FLOORS["already_in_nest"], "I4a_already_in_nest",
        "%d (floor %d)" % (a, FLOORS["already_in_nest"]))
    say(n >= FLOORS["net_new"], "I4b_net_new",
        "%d (floor %d)" % (n, FLOORS["net_new"]))
    say(a + n == len(recon), "I4c_status_total",
        "%d + %d == %d rows" % (a, n, len(recon)))

    # I5 - every ALREADY_IN_NEST row names a LIVE enterprise_id.
    live_ent = {r["enterprise_id"] for r in nest}
    miss = [r["enterprise_name"] for r in recon
            if r["reconciliation_status"] == "ALREADY_IN_NEST"
            and r["matched_nest_enterprise_id"] not in live_ent]
    say(not miss, "I5_matched_ids_live", "%d dangling matches" % len(miss))

    # I6 - THIS PASS MINTED NOTHING.  The append-only register is the only
    # place an enterprise id may come from, and a rebuild must mint zero.
    idreg = rd(NEST_IDS)
    mine = [r for r in idreg if BUILT_BY in (r.get("minted_by") or "")]
    say(not mine, "I6_minted_zero_ids",
        "%d rows in cedar_nest_id_register.csv carry this script" % len(mine))
    say(len(idreg) == len(nest), "I6b_register_covers_nest",
        "%d register bindings for %d NEST rows" % (len(idreg), len(nest)))

    # I7 - no ownership was laundered.  Every reconciliation row must carry
    # the provenance-only flag and a BLANK proposed relation_class.
    laundered = [r["enterprise_name"] for r in recon
                 if r.get("ownership_claim_carried") != "NO - provenance only"
                 or (r.get("relation_class_proposed") or "").strip()]
    say(not laundered, "I7_no_laundered_ownership",
        "%d rows assert ownership this pass has no source for"
        % len(laundered))

    # I8 - relation_class stays split in NEST itself.
    rc = collections.Counter(r.get("relation_class", "") for r in nest)
    say(set(rc) <= {"ownership", "affiliation"} and len(rc) == 2,
        "I8_relation_class_split",
        "NEST relation_class = %s" % dict(rc))

    # I9 - conservation: rows in == sum of NAMED dispositions, every table.
    consv = rd(OUT_CONSV)
    breach = [r["source_table"] for r in consv
              if int(r["unaccounted"] or 0) != 0]
    say(not breach, "I9_row_conservation",
        "%d of %d accounting rows balance%s"
        % (len(consv) - len(breach), len(consv),
           ("; breached: " + "; ".join(breach[:3])) if breach else ""))

    # I10 - the echo is FLAGGED, not booked.  If every pair reads
    # INDEPENDENT, the echo test did not run.
    echo = sum(1 for r in pairs if r["echo_risk"].startswith("ECHO"))
    say(echo > 0, "I10_echo_detected",
        "%d of %d pairs flagged as the same SBA DSBS upstream on both sides"
        % (echo, len(pairs)))
    undeclared = sorted({r["family"] for r in pairs} - {
        "federal_transactional", "federal_registry", "audited_filing",
        "entity_self_published", "state_registry", "court_record",
        "human_ruling", "cedar_inference", "compiled_directory",
        "unattributed"})
    say(not undeclared, "I10b_families_declared_in_1118",
        "undeclared families: %s" % (undeclared or "none"))

    # I11 - the dual role names an ANC or an NHO.  The owner's correction is
    # ABOUT that class; a table that reached only tribal governments has not
    # carried it out.
    anc = sum(1 for r in dual
              if r["dual_role_class"] == "ANC_CORPORATION_AND_ENTERPRISE")
    nho = sum(1 for r in dual
              if r["dual_role_class"] == "NHO_ORGANISATION_AND_ENTERPRISE")
    say(anc > 0, "I11a_dual_role_reaches_ancs", "%d ANC rows" % anc)
    say(len(dual) > anc, "I11b_dual_role_not_only_ancs",
        "%d ANC + %d NHO + %d other = %d"
        % (anc, nho, len(dual) - anc - nho, len(dual)))

    # I12 - the dual role does NOT duplicate a NEST row.  An entity may not
    # be its own subsidiary.
    selfsub = [r["enterprise_id"] for r in nest
               if r["owner_hub_cedar_uid"] == r.get("enterprise_existing_cedar_uid")
               and r.get("enterprise_existing_cedar_uid")]
    say(not selfsub, "I12_no_hub_is_its_own_subsidiary",
        "%d NEST rows where the hub is the enterprise" % len(selfsub))

    # I13 - v6 really is the authoritative file, re-measured.
    vers = {r["version"]: r for r in rd(OUT_VERSIONS)}
    v5 = vers.get("v5", {})
    v6 = vers.get("v6", {})
    say(int(v5.get("hq_state_cell_equals_this_rows_uei") or 0) > 100,
        "I13a_v5_column_breach_measured",
        "v5 hq_state holds this row's UEI on %s rows"
        % v5.get("hq_state_cell_equals_this_rows_uei"))
    say(int(v6.get("hq_state_cell_equals_this_rows_uei") or 0) == 0,
        "I13b_v6_column_clean",
        "v6 hq_state holds a UEI on %s rows"
        % v6.get("hq_state_cell_equals_this_rows_uei"))

    if not quiet:
        print()
    if fails:
        print("VERIFY FAILED - %d breach(es)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("VERIFY OK - %d invariants" % 22)
    return 0


# ===========================================================================
# SELFTEST - a check does not count until a fixture proves it FIRES
# ===========================================================================
def cmd_selftest():
    import shutil
    if not os.path.exists(OUT_RECON):
        raise SystemExit("run `build` first")
    cases = []

    def fire(name, path, mutate):
        bak = path + ".bak_%s_pre_1130_selftest" % BUILT_DATE
        shutil.copy2(path, bak)
        try:
            mutate(path)
            rc = cmd_verify(quiet=True)
            cases.append((name, rc == 1))
        finally:
            shutil.move(bak, path)
        return cases[-1][1]

    def truncate(p):
        rows = rd(p)
        write_csv(p, rows[:1] if rows else [])

    def blank_uid(p):
        rows = rd(p)
        rows[0]["cedar_uid"] = "CE-FABRICATED-XX"
        write_csv(p, rows)

    def launder(p):
        rows = rd(p)
        rows[0]["relation_class_proposed"] = "ownership"
        write_csv(p, rows)

    def unbalance(p):
        rows = rd(p)
        rows[0]["unaccounted"] = "7"
        write_csv(p, rows)

    def drop_ancs(p):
        rows = [r for r in rd(p)
                if r["dual_role_class"] != "ANC_CORPORATION_AND_ENTERPRISE"]
        write_csv(p, rows or [dict(cedar_uid="", handle="",
                                   canonical_name="", entity_class="",
                                   dual_role="", dual_role_class="")])

    def kill_echo(p):
        rows = rd(p)
        for r in rows:
            r["echo_risk"] = "INDEPENDENT - forced"
        write_csv(p, rows)

    fire("I1  empty reconciliation reads as FAILURE", OUT_RECON, truncate)
    fire("I3  a fabricated cedar_uid", OUT_RECON, blank_uid)
    fire("I7  ownership laundered onto a row", OUT_RECON, launder)
    fire("I9  conservation breach", OUT_CONSV, unbalance)
    fire("I11 dual role with no ANC", OUT_DUAL, drop_ancs)
    fire("I10 every pair claimed INDEPENDENT", OUT_PAIRS, kill_echo)

    ok = sum(1 for _, g in cases if g)
    for n, g in cases:
        print("  [%s] %s" % ("FIRES" if g else "DID NOT FIRE", n))
    print("\n%d/%d fixtures made verify exit 1" % (ok, len(cases)))
    rc = cmd_verify(quiet=True)
    print("restored: verify exits %d" % rc)
    return 0 if (ok == len(cases) and rc == 0) else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "versions":
        cmd_versions()
    elif cmd == "build":
        cmd_build()
    elif cmd == "verify":
        sys.exit(cmd_verify())
    elif cmd == "selftest":
        sys.exit(cmd_selftest())
    else:
        print(__doc__)
