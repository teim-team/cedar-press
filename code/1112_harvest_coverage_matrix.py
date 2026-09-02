"""
1112_harvest_coverage_matrix.py  -  AUDIT, not a harvest.

Re-derives, per entity in data/spine/cedar_identity_register.csv (1,555 rows) and
per harvest type, what actually happened.  Nothing here trusts a coverage
document; every cell is derived from an artefact on disk and names it.

Harvest types
    enterprises          parent-company / subsidiary / "our companies" lists
    identifiers          CAGE / UEI / DUNS  (capability statements, gov-contracting pages)
    individual_business  TERO vendor lists, Indian-preference and business-licence registers
    gaming               casino properties, capacity, class, vendor pages
    newsletter           newsletters and press / news channels

Outcome vocabulary - six values, precedence in this order.
    HARVESTED              content rows exist for this entity+type in a table on disk
    REFUSED                robots.txt or stated terms forbade it, at the ENTITY's own host
    FOUND_NOT_EXTRACTED    the surface was located and reached, nothing was pulled into a table
    CHECKED_ABSENT         looked for, positively determined not published
    ATTEMPTED_INCONCLUSIVE an attempt is on record but it could not decide
                           (host unreachable, no host known, page does not name the entity)
    NEVER_CHECKED          no artefact anywhere shows an attempt

The six-way split matters because "checked and it does not exist", "we could not
reach the site" and "nobody looked" are three different things and all three have
been reported as coverage.

Writes  data/clean/cedar_harvest_coverage_matrix.csv   (1,555 x 5 = 7,775 rows)
        data/clean/cedar_harvest_coverage_evidence.csv (every evidence record)
Read-only against everything else.  No network.  Does not commit.

    py -3 code/1112_harvest_coverage_matrix.py build
    py -3 code/1112_harvest_coverage_matrix.py verify     # exits 1 on breach
    py -3 code/1112_harvest_coverage_matrix.py selftest   # proves verify fires
"""
import csv, json, os, sys, glob, datetime, collections

csv.field_size_limit(10 ** 8)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)

BUILT_BY   = "1112_harvest_coverage_matrix.py"
BUILT_DATE = datetime.date.today().isoformat()

TYPES = ["enterprises", "identifiers", "individual_business", "gaming", "newsletter"]

# REFUSED outranks FOUND_NOT_EXTRACTED deliberately.  A located surface on a host
# that has refused us is not a surface we may act on, and recording it as "found"
# is exactly the defect that put 42 2xx rows on 13 hosts which refuse this agent by
# name in robots.txt.  Only robots/terms evidence emits REFUSED; a 403 from a WAF
# is ATTEMPTED_INCONCLUSIVE, because a WAF is not a stated refusal.
PRECEDENCE = ["HARVESTED", "REFUSED", "FOUND_NOT_EXTRACTED",
              "CHECKED_ABSENT", "ATTEMPTED_INCONCLUSIVE", "NEVER_CHECKED"]
RANK = {v: i for i, v in enumerate(PRECEDENCE)}

MATRIX   = P("data", "clean", "cedar_harvest_coverage_matrix.csv")
EVIDENCE = P("data", "clean", "cedar_harvest_coverage_evidence.csv")


# ----------------------------------------------------------------- helpers
def rd(path, **kw):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh, **kw))


def rj(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def s(d, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", "None"):
            return str(v).strip()
    return ""


def is2xx(code):
    c = str(code).strip()
    return len(c) == 3 and c.isdigit() and c[0] == "2"


# ----------------------------------------------------------------- register
REG = rd(P("data", "spine", "cedar_identity_register.csv"))
UID = {r["cedar_uid"]: r for r in REG}
HANDLE2UID = {r["handle"]: r["cedar_uid"] for r in REG if r.get("handle")}
CEID2UID   = {r["cedar_entity_id"]: r["cedar_uid"] for r in REG if r.get("cedar_entity_id")}


def resolve(v):
    """Accept a cedar_uid, a handle, or a cedar_entity_id.  Return a uid or ''."""
    v = (v or "").strip()
    if not v:
        return ""
    if v in UID:
        return v
    if v in HANDLE2UID:
        return HANDLE2UID[v]
    if v in CEID2UID:
        return CEID2UID[v]
    return ""


# ----------------------------------------------------------------- evidence sink
EV = []          # (uid, type, outcome, artefact, detail, date)


def ev(uid, typ, outcome, artefact, detail="", date=""):
    uid = resolve(uid)
    if not uid:
        return False
    if typ not in TYPES or outcome not in RANK:
        raise ValueError("bad evidence %s %s" % (typ, outcome))
    EV.append((uid, typ, outcome, artefact, str(detail)[:300], date or ""))
    return True


# ----------------------------------------------------------------- web map
WEBMAP = rd(P("data", "staging", "cedar_web_map.csv"))

# url_type -> (harvest type, what the row is)
URLTYPE = {
    "subsidiary_list":   ("enterprises", "FOUND"),
    "shareholder":       ("enterprises", "FOUND"),
    "procurement":       ("identifiers", "FOUND"),
    "certification":     ("identifiers", "FOUND"),
    "tero":              ("individual_business", "FOUND"),
    "business_licence":  ("individual_business", "FOUND"),
    "failed_tero":       ("individual_business", "ATTEMPT"),
    "unverified_tero":   ("individual_business", "ATTEMPT"),
    "unverified_business_licence": ("individual_business", "ATTEMPT"),
    "casino":            ("gaming", "FOUND"),
    "gaming_authority":  ("gaming", "FOUND"),
    "closed_property":   ("gaming", "ABSENT"),
    "failed_casino":     ("gaming", "ATTEMPT"),
    "unverified_casino": ("gaming", "ATTEMPT"),
    "failed_gaming_authority": ("gaming", "ATTEMPT"),
    "newsletter":        ("newsletter", "FOUND"),
    "press_release":     ("newsletter", "FOUND"),
    "annual_report":     ("newsletter", "FOUND"),
    "failed_newsletter": ("newsletter", "ATTEMPT"),
    "unverified_newsletter": ("newsletter", "ATTEMPT"),
}
DEAD_URLTYPE = {"parked_domain", "DOMAIN_HIJACKED_DO_NOT_LINK", "placeholder_site",
                "none_established", "no_own_site_found"}
REFUSAL_URLTYPE = {"TERMS_RESTRICTED_DO_NOT_HARVEST", "government_refused_robots",
                   "government_blocked_bot_protection"}

HOST2UID = collections.defaultdict(set)

# harvest_source_id (TBD-*) -> cedar_uid of the entity that PUBLISHED that directory.
# Populated from review/tribal_vendor_list_registry_2026-08-26.csv, the only artefact
# that carries the mapping.  Built before any collector runs because two of them need it.
SOURCE2UID = {}


def build_source2uid():
    for r in rd(P("review", "tribal_vendor_list_registry_2026-08-26.csv")):
        uid = resolve(s(r, "tribe_id"))
        sid = s(r, "harvest_source_id")
        if uid and sid:
            SOURCE2UID[sid] = uid
    # the clean table carries its own source_id -> certifying authority pairing
    for r in rd(P("data", "clean", "native_owned_businesses.csv")):
        uid = resolve(s(r, "certifying_authority_entity_id"))
        sid = s(r, "source_id")
        if uid and sid:
            SOURCE2UID.setdefault(sid, uid)
    return SOURCE2UID


def collect_webmap():
    for r in WEBMAP:
        uid = resolve(s(r, "cedar_uid"))
        if not uid:
            continue
        ut = s(r, "url_type")
        url = s(r, "url")
        st = s(r, "http_status")
        d = s(r, "checked_date")
        host = url.split("//")[-1].split("/")[0].lower()
        if host and ut not in DEAD_URLTYPE and ut not in REFUSAL_URLTYPE:
            HOST2UID[host].add(uid)
        if ut in REFUSAL_URLTYPE:
            for t in TYPES:
                ev(uid, t, "REFUSED", "data/staging/cedar_web_map.csv",
                   "url_type=%s %s" % (ut, url), d)
            continue
        if ut not in URLTYPE:
            continue
        typ, kind = URLTYPE[ut]
        if kind == "ABSENT":
            ev(uid, typ, "CHECKED_ABSENT", "data/staging/cedar_web_map.csv",
               "url_type=%s %s" % (ut, url), d)
        elif kind == "ATTEMPT":
            ev(uid, typ, "ATTEMPTED_INCONCLUSIVE", "data/staging/cedar_web_map.csv",
               "url_type=%s status=%s %s" % (ut, st, url), d)
        else:
            out = "FOUND_NOT_EXTRACTED" if is2xx(st) else "ATTEMPTED_INCONCLUSIVE"
            ev(uid, typ, out, "data/staging/cedar_web_map.csv",
               "url_type=%s status=%s %s" % (ut, st, url), d)


# ------------------------------------------------------- OUTPUT TABLES = HARVESTED
def collect_outputs():
    # --- gaming
    for r in rd(P("data", "clean", "gaming_web_harvest_observations.csv")):
        ev(s(r, "cedar_uid", "tribe_id"), "gaming", "HARVESTED",
           "data/clean/gaming_web_harvest_observations.csv",
           "metric=%s %s" % (s(r, "metric"), s(r, "source_url")), s(r, "retrieved_at")[:10])
    for shard in "abcdefghklmn":
        for fn in ("casino_properties.jsonl", "casino_claims.jsonl", "gaming_authorities.jsonl"):
            for r in rj(P("data", "staging", "tribe_harvest", "shard_" + shard, fn)):
                ev(s(r, "cedar_uid", "tribe_id"), "gaming", "HARVESTED",
                   "data/staging/tribe_harvest/shard_%s/%s" % (shard, fn),
                   s(r, "source_url", "url", "property_name"),
                   s(r, "retrieved_at", "checked_date")[:10])

    # --- newsletter
    for r in rd(P("data", "clean", "tribal_newsletter_corpus.csv")):
        uid = s(r, "cedar_uid")
        st = s(r, "record_status")
        if st == "publication_channel":
            ev(uid, "newsletter", "HARVESTED", "data/clean/tribal_newsletter_corpus.csv",
               "%s %s" % (s(r, "channel_type"), s(r, "channel_url")), s(r, "retrieved_date"))
        elif st == "probe_absence":
            ev(uid, "newsletter", "CHECKED_ABSENT", "data/clean/tribal_newsletter_corpus.csv",
               "record_status=probe_absence %s" % s(r, "note"), s(r, "retrieved_date"))
        else:
            ev(uid, "newsletter", "ATTEMPTED_INCONCLUSIVE",
               "data/clean/tribal_newsletter_corpus.csv",
               "record_status=%s" % st, s(r, "retrieved_date"))
    for r in rj(P("data", "staging", "tribe_harvest", "newsletter_gap_sweep", "gap_sweep.jsonl")):
        uid = s(r, "cedar_uid")
        found = s(r, "found")
        out = "FOUND_NOT_EXTRACTED" if found not in ("", "[]", "None") else "CHECKED_ABSENT"
        # a Disallow of /wp-admin/ or *?lightbox= is not a refusal of a newsletter.
        # Only a whole-site ban, or one naming this agent, is.
        if robots_bans_whole_site(s(r, "robots_disallow")):
            out = "REFUSED"
        ev(uid, "newsletter", out,
           "data/staging/tribe_harvest/newsletter_gap_sweep/gap_sweep.jsonl",
           "outcome=%s requests=%s found=%s" % (s(r, "outcome"), s(r, "requests_made"), found),
           s(r, "checked_date"))

    # --- enterprises
    for r in rd(P("data", "clean", "nest_enterprises.csv")):
        ev(s(r, "owner_hub_cedar_uid", "cedar_uid"), "enterprises", "HARVESTED",
           "data/clean/nest_enterprises.csv",
           "%s rel=%s" % (s(r, "enterprise_name"), s(r, "relationship")), s(r, "retrieved_date"))
    for r in rj(P("data", "staging", "tribal_enterprises", "enterprise_register.jsonl")):
        ev(s(r, "tribe_cedar_uid", "tribe_id"), "enterprises", "HARVESTED",
           "data/staging/tribal_enterprises/enterprise_register.jsonl",
           s(r, "enterprise_name_raw"), s(r, "retrieved_date"))
    for fn in ("shard_e.jsonl", "shard_h.jsonl"):
        for r in rj(P("data", "staging", "anc_subsidiaries", fn)):
            ev(s(r, "parent_cedar_uid"), "enterprises", "HARVESTED",
               "data/staging/anc_subsidiaries/" + fn, s(r, "child_name_raw"),
               s(r, "retrieved_date"))
    for r in rj(P("data", "staging", "native_business_sweep_1070", "business_rows_ancsa.jsonl")):
        ev(s(r, "authority_cedar_uid"), "enterprises", "HARVESTED",
           "data/staging/native_business_sweep_1070/business_rows_ancsa.jsonl",
           "%s %s" % (s(r, "kind"), s(r, "business_name_raw")), "2026-09-02")

    # --- individual native business directories
    NOB = rd(P("data", "clean", "native_owned_businesses.csv"))
    for r in NOB:
        ev(s(r, "certifying_authority_entity_id"), "individual_business", "HARVESTED",
           "data/clean/native_owned_businesses.csv",
           "%s %s" % (s(r, "directory_type"), s(r, "business_name_raw")), s(r, "harvest_date"))
    for r in rj(P("data", "staging", "native_business_sweep_1070", "business_rows.jsonl")):
        ev(s(r, "authority_cedar_uid"), "individual_business", "HARVESTED",
           "data/staging/native_business_sweep_1070/business_rows.jsonl",
           "%s %s" % (s(r, "kind"), s(r, "business_name_raw")), "2026-09-02")
    for shard in "abcdefghklmn":
        for r in rj(P("data", "staging", "tribe_harvest", "shard_" + shard, "tero_pages.jsonl")):
            ev(s(r, "cedar_uid", "tribe_id"), "individual_business", "FOUND_NOT_EXTRACTED",
               "data/staging/tribe_harvest/shard_%s/tero_pages.jsonl" % shard,
               s(r, "source_url"), s(r, "retrieved_at")[:10])

    # --- identifiers  (CAGE / UEI / DUNS)
    xw = rd(P("data", "clean", "native_business_identifier_crosswalk.csv"))
    bsid2auth = {}
    nation2auth = {}
    for r in NOB:
        bsid2auth[s(r, "business_source_id")] = s(r, "certifying_authority_entity_id")
        if s(r, "nation_id"):
            nation2auth[s(r, "nation_id")] = s(r, "certifying_authority_entity_id")
    for r in xw:
        auth = bsid2auth.get(s(r, "business_source_id"), "")
        if s(r, "identifier_type").upper() in ("CAGE", "UEI", "DUNS", "CAGE_CODE"):
            ev(auth, "identifiers", "HARVESTED",
               "data/clean/native_business_identifier_crosswalk.csv",
               "%s=%s tier=%s" % (s(r, "identifier_type"), s(r, "identifier_value"),
                                  s(r, "identifier_tier")), s(r, "built_date"))
    for r in rd(P("data", "clean", "nest_enterprises.csv")):
        if s(r, "uei") or s(r, "cage_code"):
            ev(s(r, "owner_hub_cedar_uid"), "identifiers", "HARVESTED",
               "data/clean/nest_enterprises.csv",
               "%s uei=%s cage=%s" % (s(r, "enterprise_name"), s(r, "uei"), s(r, "cage_code")),
               s(r, "retrieved_date"))
    for r in rj(P("data", "staging", "entity_profiles", "shard_h_identifiers.jsonl")):
        ev(s(r, "cedar_uid", "tribe_id"), "identifiers", "HARVESTED",
           "data/staging/entity_profiles/shard_h_identifiers.jsonl",
           "%s=%s" % (s(r, "identifier_type"), s(r, "identifier_value")), s(r, "retrieved_date"))
    for fn in ("shard_e.jsonl", "shard_h.jsonl"):
        for r in rj(P("data", "staging", "anc_subsidiaries", fn)):
            if s(r, "child_cage_code"):
                ev(s(r, "parent_cedar_uid"), "identifiers", "HARVESTED",
                   "data/staging/anc_subsidiaries/" + fn,
                   "CAGE=%s for %s" % (s(r, "child_cage_code"), s(r, "child_name_raw")),
                   s(r, "retrieved_date"))
    # the identifier PROBE - a capability-statement sweep that found nothing is a real check
    for r in rj(P("data", "staging", "business_registry", "TBD-L00_business_identifiers.jsonl")):
        auth = (SOURCE2UID.get(s(r, "source_id"), "")
                or nation2auth.get(s(r, "nation_id"), "")
                or bsid2auth.get(s(r, "business_source_id"), ""))
        got = s(r, "identifiers")
        out = "HARVESTED" if got not in ("", "[]", "{}", "None") else "CHECKED_ABSENT"
        ev(auth, "identifiers", out,
           "data/staging/business_registry/TBD-L00_business_identifiers.jsonl",
           "probe %s status=%s ids=%s" % (s(r, "probe_path"), s(r, "http_status"), got[:60]),
           s(r, "retrieved_date"))


# --------------------------------------------------- ENTITY-LEVEL VERDICT FILES
V1070 = {
    "LIST_FOUND":                    "HARVESTED",
    "NO_LIST_FOUND":                 "CHECKED_ABSENT",
    "MENTION_ONLY":                  "CHECKED_ABSENT",
    "LIST_REFERENCED_NOT_PUBLISHED": "CHECKED_ABSENT",
    "TERMS_STATED_RESTRICTIVE":      "REFUSED",
    "EXCLUDED_TERMS":                "REFUSED",
    "ROBOTS_DISALLOW":               "REFUSED",
    "UNREACHABLE":                   "ATTEMPTED_INCONCLUSIVE",
    "NO_HOST_KNOWN":                 "ATTEMPTED_INCONCLUSIVE",
    "DOMAIN_NOT_THE_ENTITY":         "ATTEMPTED_INCONCLUSIVE",
    "HIJACKED_OR_WRONG_DOMAIN":      "ATTEMPTED_INCONCLUSIVE",
    "NAME_CHECK_INDETERMINATE":      "ATTEMPTED_INCONCLUSIVE",
    "NOT_SEARCHED_MACHINE_READABLE": "ATTEMPTED_INCONCLUSIVE",
}
ENTERPRISE_KINDS = {"anc_operating_companies", "enterprise_register", "nho_subsidiaries"}
INDIV_KINDS      = {"member_business_list", "nho_member_directory"}


def collect_verdicts():
    # 1070 - the sweep over AK villages, NHOs, ANCs, intertribals, state tribes
    for r in rd(P("data", "staging", "native_business_sweep_1070", "verdicts.csv")):
        uid = resolve(s(r, "cedar_uid") or s(r, "tribe_id"))
        if not uid:
            continue
        v = s(r, "verdict")
        out = V1070.get(v, "ATTEMPTED_INCONCLUSIVE")
        d = s(r, "checked_date")
        art = "data/staging/native_business_sweep_1070/verdicts.csv"
        kinds = set(k for k in s(r, "kinds").split(";") if k)
        detail = "verdict=%s host=%s kinds=%s err=%s" % (v, s(r, "host"), s(r, "kinds"),
                                                         s(r, "errors")[:80])
        if out == "HARVESTED":
            if kinds & ENTERPRISE_KINDS:
                ev(uid, "enterprises", "HARVESTED", art, detail, d)
            if kinds & INDIV_KINDS:
                ev(uid, "individual_business", "HARVESTED", art, detail, d)
            for t in ("enterprises", "individual_business"):
                ev(uid, t, "FOUND_NOT_EXTRACTED", art, detail, d)
        else:
            for t in ("enterprises", "individual_business"):
                ev(uid, t, out, art, detail, d)

    # tribal_enterprises/verdicts.csv - the federally recognised tribe sweep
    TE = {"LIST_FOUND": "HARVESTED", "NO_LIST_FOUND": "CHECKED_ABSENT",
          "MENTION_ONLY": "CHECKED_ABSENT"}
    TERO_VOCAB = {
        "NO_LIST_FOUND": "CHECKED_ABSENT",
        "NO_LIST_FOUND_UNVERIFIED": "ATTEMPTED_INCONCLUSIVE",
        "LIST_REFERENCED_NOT_PUBLISHED": "CHECKED_ABSENT",
        "LIST_FOUND_HTML": "FOUND_NOT_EXTRACTED",
        "LIST_FOUND_PDF": "FOUND_NOT_EXTRACTED",
        "LIST_FOUND_JSON": "FOUND_NOT_EXTRACTED",
        "LIST_FOUND_MACHINE_READABLE": "FOUND_NOT_EXTRACTED",
        "LIST_BEHIND_LOGIN": "REFUSED",
        "SITE_UNREACHABLE": "ATTEMPTED_INCONCLUSIVE",
        "NOT_SEARCHED_MACHINE_READABLE": "ATTEMPTED_INCONCLUSIVE",
        "CANDIDATE_FOUND_UNREVIEWED": "FOUND_NOT_EXTRACTED",
    }
    for r in rd(P("data", "staging", "tribal_enterprises", "verdicts.csv")):
        uid = resolve(s(r, "tribe_cedar_uid") or s(r, "tribe_id"))
        if not uid:
            continue
        art = "data/staging/tribal_enterprises/verdicts.csv"
        d = "2026-09-02"
        nv = s(r, "new_verdict")
        detail = ("new_verdict=%s prior_tero_vocab=%s probed=%s host=%s"
                  % (nv, s(r, "prior_verdict_tero_vocab"), s(r, "probed"), s(r, "host")))
        if s(r, "probed") == "N":
            ev(uid, "enterprises", "ATTEMPTED_INCONCLUSIVE", art,
               detail + " why=" + s(r, "why_not_probed"), d)
        else:
            ev(uid, "enterprises", TE.get(nv, "ATTEMPTED_INCONCLUSIVE"), art, detail, d)
        pv = s(r, "prior_verdict_tero_vocab")
        if pv:
            ev(uid, "individual_business", TERO_VOCAB.get(pv, "ATTEMPTED_INCONCLUSIVE"), art,
               "prior_verdict_tero_vocab=" + pv, d)

    # shard_l - the TERO / vendor-list shard.  SHARD_COVERAGE.md calls it NOT_STARTED.
    SL = {"LIST_FOUND_HTML": "FOUND_NOT_EXTRACTED", "LIST_FOUND_PDF": "FOUND_NOT_EXTRACTED",
          "LIST_FOUND_JSON": "FOUND_NOT_EXTRACTED",
          "LIST_FOUND_MACHINE_READABLE": "FOUND_NOT_EXTRACTED",
          "NO_LIST_FOUND": "CHECKED_ABSENT", "LIST_REFERENCED_NOT_PUBLISHED": "CHECKED_ABSENT",
          "NO_LIST_FOUND_UNVERIFIED": "ATTEMPTED_INCONCLUSIVE",
          "NO_SITE_FOUND": "ATTEMPTED_INCONCLUSIVE",
          "NOT_SEARCHED_MACHINE_READABLE": "ATTEMPTED_INCONCLUSIVE",
          "CANDIDATE_FOUND_UNREVIEWED": "FOUND_NOT_EXTRACTED",
          "REFUSED_ROBOTS": "REFUSED", "NOT_CHECKED": None}
    for fn in ("_verdicts.jsonl", "_verdicts_auto.jsonl"):
        for r in rj(P("data", "staging", "tribe_harvest", "shard_l", fn)):
            uid = resolve(s(r, "tribe_id"))
            if not uid:
                continue
            art = "data/staging/tribe_harvest/shard_l/" + fn
            hs = s(r, "harvest_status")
            best = None
            for col in ("verdict", "verdict_certification", "verdict_vendor_relationship",
                        "verdict_business_licence"):
                o = SL.get(s(r, col))
                if o and (best is None or RANK[o] < RANK[best]):
                    best = o
            if hs.startswith("HARVESTED"):
                best = "HARVESTED"
            if hs == "EXCLUDED_ROBOTS":
                best = "REFUSED"
            if best:
                ev(uid, "individual_business", best, art,
                   "verdict=%s harvest_status=%s" % (s(r, "verdict"), hs), "2026-09-01")

    # review/tribal_vendor_list_registry_2026-08-26.csv - the master per-tribe TERO /
    # vendor-list register.  359 tribes, every tribe_id resolves to a register handle.
    # It also maps harvest_source_id (TBD-*) -> the tribe that published the list, which
    # is the only crosswalk that attaches the staged-only directories to an entity.
    REGV = {
        "LIST_FOUND_HTML": "FOUND_NOT_EXTRACTED", "LIST_FOUND_PDF": "FOUND_NOT_EXTRACTED",
        "LIST_FOUND_JSON": "FOUND_NOT_EXTRACTED",
        "LIST_FOUND_MACHINE_READABLE": "FOUND_NOT_EXTRACTED",
        "LIST_FOUND_TERO_FREE_VOCAB": "FOUND_NOT_EXTRACTED",
        "NO_LIST_FOUND": "CHECKED_ABSENT", "LIST_REFERENCED_NOT_PUBLISHED": "CHECKED_ABSENT",
        "NO_LIST_FOUND_UNVERIFIED": "ATTEMPTED_INCONCLUSIVE",
        "NO_SITE_FOUND": "ATTEMPTED_INCONCLUSIVE",
        "SITE_UNREACHABLE": "ATTEMPTED_INCONCLUSIVE",
        "NOT_SEARCHED_MACHINE_READABLE": "ATTEMPTED_INCONCLUSIVE",
        "NOT_CHECKED": None, "": None,
        "LIST_BEHIND_LOGIN": "REFUSED",
    }
    art = "review/tribal_vendor_list_registry_2026-08-26.csv"
    for r in rd(P("review", "tribal_vendor_list_registry_2026-08-26.csv")):
        uid = resolve(s(r, "tribe_id"))
        if not uid:
            continue
        d = s(r, "checked_date") or "2026-08-26"
        hs = s(r, "harvest_status")
        best = None
        for col in ("verdict", "verdict_certification", "verdict_vendor_relationship",
                    "verdict_business_licence"):
            o = REGV.get(s(r, col), "ATTEMPTED_INCONCLUSIVE")
            if o and (best is None or RANK[o] < RANK[best]):
                best = o
        if hs.startswith("HARVESTED"):
            best = "HARVESTED"
        if hs.startswith("EXCLUDED_TERMS") or s(r, "source_terms_status") in (
                "TERMS_STATED_RESTRICTIVE", "ROBOTS_DISALLOW"):
            best = "REFUSED"
        if best:
            ev(uid, "individual_business", best, art,
               "verdict=%s harvest_status=%s cert=%s vendor=%s licence=%s src=%s"
               % (s(r, "verdict"), hs, s(r, "verdict_certification"),
                  s(r, "verdict_vendor_relationship"), s(r, "verdict_business_licence"),
                  s(r, "harvest_source_id")), d)
        if s(r, "harvest_source_id"):
            SOURCE2UID[s(r, "harvest_source_id")] = uid

    # data/staging/tribal_vendor_lists/tribal_certification_sources_2026-08-26.csv
    art = "data/staging/tribal_vendor_lists/tribal_certification_sources_2026-08-26.csv"
    for r in rd(P("data", "staging", "tribal_vendor_lists",
                  "tribal_certification_sources_2026-08-26.csv")):
        uid = resolve(s(r, "certifying_authority_entity_id"))
        if not uid:
            continue
        o = REGV.get(s(r, "verdict"), "ATTEMPTED_INCONCLUSIVE")
        if o:
            ev(uid, "individual_business", o, art,
               "verdict=%s programme=%s %s" % (s(r, "verdict"), s(r, "programme_name"),
                                               s(r, "list_url")), s(r, "capture_date"))

    # the STAGED-ONLY directories: 18 of 36 TBD-* files in data/staging/business_registry
    # never reached data/clean/native_owned_businesses.csv.  They are harvested content
    # sitting on disk, so the entity has been looked at - the row just was not promoted.
    # lint-ok: class1 - reading the staged artefact IS the job. This is an AUDIT of what
    # is on disk versus what reached the promoted table; the whole finding is that 16 of
    # these files have zero rows in data/clean/native_owned_businesses.csv. Reading the
    # promoted table instead would make the gap invisible, which is the defect inverted.
    for path in sorted(glob.glob(P("data", "staging", "business_registry", "TBD-*.jsonl"))):
        base = os.path.basename(path)
        sid = base.split("_")[0]
        uid = SOURCE2UID.get(sid, "")
        if not uid or sid == "TBD-L00":
            continue
        n = len(rj(path))
        if n:
            ev(uid, "individual_business", "HARVESTED",
               "data/staging/business_registry/" + base,
               "%d staged directory rows, source_id=%s" % (n, sid), "2026-09-01")

    # shard_m - deep probe for vendor / TERO lists on 148 more hosts
    for r in rj(P("data", "staging", "tribe_harvest", "shard_m", "deep_probe.jsonl")):
        uid = resolve(s(r, "cedar_uid"))
        if not uid:
            continue
        hits = s(r, "hits") + s(r, "search_hits")
        reached = s(r, "reached")
        art = "data/staging/tribe_harvest/shard_m/deep_probe.jsonl"
        if reached in ("False", "", "None"):
            out = "ATTEMPTED_INCONCLUSIVE"
        elif hits not in ("", "[]", "0", "None"):
            out = "FOUND_NOT_EXTRACTED"
        else:
            out = "CHECKED_ABSENT"
        ev(uid, "individual_business", out, art,
           "reached=%s requests=%s hits=%s" % (reached, s(r, "requests"), hits[:60]),
           "2026-09-01")
    for r in (rj(P("data", "staging", "tribe_harvest", "shard_m", "host_log.jsonl"))
              + rj(P("data", "staging", "tribe_harvest", "shard_m", "host_log_stage7.jsonl"))):
        uid = resolve(s(r, "cedar_uid"))
        if not uid:
            continue
        art = "data/staging/tribe_harvest/shard_m/host_log.jsonl"
        if s(r, "terms_status") == "TERMS_STATED_RESTRICTIVE":
            ev(uid, "individual_business", "REFUSED", art,
               "terms " + s(r, "terms_url"), s(r, "checked_date"))
        elif robots_bans_whole_site(s(r, "robots_note")):
            ev(uid, "individual_business", "REFUSED", art,
               "robots bans the whole site: " + s(r, "robots_note")[:80], s(r, "checked_date"))


# ------------------------------------------------------------- gaming probes
def collect_gaming_probes():
    for fn, art in (("host_probe.jsonl", "data/staging/gaming_web_harvest/host_probe.jsonl"),
                    ("page_fetch.jsonl", "data/staging/gaming_web_harvest/page_fetch.jsonl"),
                    ("escalation.jsonl", "data/staging/gaming_web_harvest/escalation.jsonl")):
        for r in rj(P("data", "staging", "gaming_web_harvest", fn)):
            uid = resolve(s(r, "cedar_uid") or s(r, "tribe_id"))
            if not uid:
                continue
            rn = s(r, "robots_note")
            if "isallow" in rn or "refus" in rn.lower():
                ev(uid, "gaming", "REFUSED", art, "robots " + rn[:80], s(r, "checked_date"))
            elif is2xx(s(r, "http_status")):
                ev(uid, "gaming", "FOUND_NOT_EXTRACTED", art,
                   "%s %s %s" % (s(r, "endpoint_kind", "page_class"), s(r, "url"),
                                 s(r, "http_status")), s(r, "checked_date"))
            else:
                ev(uid, "gaming", "ATTEMPTED_INCONCLUSIVE", art,
                   "%s status=%s" % (s(r, "url"), s(r, "http_status")), s(r, "checked_date"))
    for r in rd(P("data", "staging", "gaming_web_harvest", "targets.csv")):
        uid = resolve(s(r, "cedar_uid") or s(r, "tribe_id"))
        if uid:
            ev(uid, "gaming", "ATTEMPTED_INCONCLUSIVE",
               "data/staging/gaming_web_harvest/targets.csv",
               "entity was on the gaming harvest target list", "2026-09-02")


# ------------------------------------------------------ generic probe-log sweep
# Any request whose PATH names the thing is a check for that thing, whatever
# script made it.  This is what catches work no verdict file recorded.
KEYWORDS = {
    "individual_business": ("tero", "vendor", "indian-preference", "indianpreference",
                            "business-licen", "businesslicen", "contractor", "procure",
                            "bidder", "supplier"),
    "enterprises":         ("subsidiar", "our-compan", "ourcompanies", "enterprise",
                            "operating-compan", "portfolio", "holdings", "our-business"),
    "identifiers":         ("capabilit", "cage", "uei", "duns", "sam-registration",
                            "gsa-schedule"),
    "gaming":              ("casino", "gaming", "bingo", "resort"),
    "newsletter":          ("newsletter", "press-release", "pressrelease", "/news", "bulletin",
                            "/feed", "rss", "publication"),
}
PROBE_LOGS = [
    "data/staging/tribe_harvest/shard_a/fetch_log.jsonl",
    "data/staging/tribe_harvest/shard_b/_probe_results.jsonl",
    "data/staging/tribe_harvest/shard_d/_probe_results.jsonl",
    "data/staging/tribe_harvest/shard_e/_probe_results.jsonl",
    "data/staging/tribe_harvest/shard_f/_probe_results.jsonl",
    "data/staging/tribe_harvest/shard_f/_fetch_log.jsonl",
    "data/staging/business_registry/1000_web_probe.jsonl",
    "data/staging/native_business_sweep_1070/host_log.jsonl",
    "data/staging/tribal_enterprises/host_log.jsonl",
    "data/staging/deals_from_newsletters/_documents.jsonl",
    "data/staging/deals_from_newsletters/_wp_posts_hosts.jsonl",
]


def collect_probe_sweep():
    paths = [P(*rel.split("/")) for rel in PROBE_LOGS]
    # lint-ok: class1 - these are PROBE LOGS, not a staged copy of a promoted table. No
    # promoted table records which URLs were requested; the log is the only evidence that
    # a check happened at all, and distinguishing "checked" from "never checked" is the
    # entire deliverable.
    paths += sorted(glob.glob(P("data", "staging", "tribe_harvest", "shard_l", "probe*.jsonl")))
    for path in paths:
        art = os.path.relpath(path, ROOT).replace("\\", "/")
        for r in rj(path):
            url = s(r, "url", "candidate_url", "url_probed", "final_url")
            if not url:
                continue
            uids = set()
            u = resolve(s(r, "cedar_uid") or s(r, "tribe_id") or s(r, "tribe_cedar_uid"))
            if u:
                uids.add(u)
            if not uids:
                host = s(r, "host") or url.split("//")[-1].split("/")[0].lower()
                uids = set(HOST2UID.get(host.lower(), ()))
                if len(uids) > 3:     # a shared host proves nothing about one entity
                    continue
            if not uids:
                continue
            low = url.lower()
            st = s(r, "http_status")
            for typ, kws in KEYWORDS.items():
                if not any(k in low for k in kws):
                    continue
                if is2xx(st):
                    out = "FOUND_NOT_EXTRACTED"
                elif st in ("404", "410"):
                    out = "CHECKED_ABSENT"
                elif st in ("403", "401"):
                    out = "ATTEMPTED_INCONCLUSIVE"   # a WAF block is not a stated refusal
                else:
                    out = "ATTEMPTED_INCONCLUSIVE"
                for uid in uids:
                    ev(uid, typ, out, art, "probe %s status=%s" % (url[:120], st),
                       s(r, "checked_date", "fetched_date", "retrieved_date")[:10])


# ---------------------------------------------------------------- applicability
def gaming_universe():
    out = set()
    for r in rd(P("data", "clean", "gaming_facilities.csv")):
        u = resolve(s(r, "cedar_uid"))
        if u:
            out.add(u)
        for x in s(r, "operating_entity_cedar_uids").replace(";", ",").split(","):
            u = resolve(x.strip())
            if u:
                out.add(u)
    return out


# ---------------------------------------------------------------------- build
# ------------------------------------------------------------- contamination
# Three known ways a cell in this matrix can be RIGHT about the artefact and
# WRONG about the world.  Each is re-derived here, not quoted.
STOPWORDS = {"tribe", "tribes", "tribal", "band", "bands", "nation", "nations",
             "village", "villages", "community", "communities", "pueblo", "rancheria",
             "reservation", "indian", "indians", "native", "americans", "american",
             "council", "corporation", "corporations", "corp", "incorporated", "inc",
             "company", "co", "llc", "ltd", "limited", "association", "of", "the",
             "and", "at", "in", "for", "group", "organization", "organisation",
             "traditional", "federated", "confederated", "confederacy", "colony",
             "town", "city", "county", "alaska", "hawaiian", "hawaii", "natives",
             "eek", "ute", "koi"}


def robots_bans_whole_site(note):
    """True only when robots.txt disallows the WHOLE site, or names this agent.

    NOT a simple substring test.  `"Disallow" in note` fires on the string
    'no Disallow directives' (34 hosts in shard_m) and on 'Disallow: /wp-admin/'
    (24 more), neither of which refuses a newsletter or a TERO page.  Measured
    while building this audit; it would have reported 106 refusals where the
    honest number is far smaller, which is this repo's signature defect in a
    detector written to find that defect.
    """
    n = (note or "").replace("Disallow:", " ").replace(",", ";")
    for part in n.split(";"):
        t = part.strip().strip("'\"[] ")
        if t == "/" or t == "/*":
            return True
    low = (note or "").lower()
    return "claudebot" in low or "anthropic" in low


def contamination_flags():
    """cedar_uid -> {harvest_type or '*' : flag}.  Never invents a flag; every one
    is read out of a named artefact or re-derived from the register."""
    flags = collections.defaultdict(lambda: collections.defaultdict(set))
    # 1. a 2xx was recorded from a host that refuses THIS agent by name, or states
    #    restrictive terms.  can_fetch() with our own UA never matches `User-agent: ClaudeBot`.
    for r in rd(P("review", "1020_named_agent_robots_exposure.csv")):
        uid = resolve(s(r, "cedar_uid"))
        if not uid:
            continue
        typ = URLTYPE.get(s(r, "url_type"), (None,))[0] or "*"
        flags[uid][typ].add("SOURCE_REFUSES_THIS_AGENT_OR_STATES_RESTRICTIVE_TERMS"
                            "(review/1020_named_agent_robots_exposure.csv)")
    # 2. the site we hold for this entity does not name it
    for r in rd(P("data", "staging", "native_business_sweep_1070", "verdicts.csv")):
        if s(r, "verdict") in ("DOMAIN_NOT_THE_ENTITY", "HIJACKED_OR_WRONG_DOMAIN"):
            uid = resolve(s(r, "cedar_uid"))
            if uid:
                flags[uid]["*"].add(
                    "SITE_DOES_NOT_NAME_ENTITY(data/staging/native_business_sweep_1070/verdicts.csv"
                    " verdict=%s)" % s(r, "verdict"))
    # 3. a canonical name that is nothing but stopwords cannot be identity-checked
    #    from page text.  Re-derived from the register, not quoted from prose.
    for r in REG:
        toks = [t for t in "".join(ch.lower() if ch.isalnum() else " "
                                   for ch in r["canonical_name"]).split() if t]
        if toks and not [t for t in toks if t not in STOPWORDS]:
            flags[r["cedar_uid"]]["*"].add(
                "NAME_IS_ALL_STOPWORDS_identity_not_checkable_from_page_text"
                "(re-derived from data/spine/cedar_identity_register.csv)")
    return flags


def federal_side_identifier_holders():
    """cedar_uid -> the identifier types Cedar already holds from the FEDERAL side.
    Context only.  A CAGE code recovered from FPDS is not a web harvest of the
    entity's own capability statement, and this column exists so the identifiers
    column of the matrix is not misread as "Cedar has no CAGE codes"."""
    out = collections.defaultdict(set)
    for r in rd(P("data", "clean", "cedar_identifier_ledger_final.csv")):
        u = resolve(s(r, "cedar_uid") or s(r, "tribe_id"))
        t = s(r, "identifier_type")
        if u and t:
            out[u].add(t)
    return out


def build():
    build_source2uid()
    collect_webmap()
    collect_outputs()
    collect_verdicts()
    collect_gaming_probes()
    collect_probe_sweep()

    gam = gaming_universe()
    fed = federal_side_identifier_holders()
    con = contamination_flags()
    by = collections.defaultdict(list)
    for rec in EV:
        by[(rec[0], rec[1])].append(rec)

    rows = []
    for r in REG:
        uid = r["cedar_uid"]
        for typ in TYPES:
            recs = by.get((uid, typ), [])
            if recs:
                recs.sort(key=lambda x: (RANK[x[2]], x[3]))
                best = recs[0]
                outcome, art, detail, date = best[2], best[3], best[4], best[5]
            else:
                outcome, art, date = "NEVER_CHECKED", "", ""
                detail = "no artefact on disk records any attempt for this entity and this thing"
            kinds = sorted({x[2] for x in recs}, key=lambda v: RANK[v])
            arts = sorted({x[3] for x in recs})
            rows.append({
                "cedar_uid": uid,
                "handle": r.get("handle", ""),
                "canonical_name": r.get("canonical_name", ""),
                "entity_class": r.get("entity_class", ""),
                "state": r.get("state", ""),
                "harvest_type": typ,
                "outcome": outcome,
                "proving_artefact": art,
                "proving_detail": detail,
                "outcome_date": date,
                "n_evidence_records": len(recs),
                "n_distinct_artefacts": len(arts),
                "all_outcomes_seen": ";".join(kinds),
                "all_artefacts": ";".join(arts)[:600],
                "applicability": ("KNOWN_GAMING_OPERATOR" if typ == "gaming" and uid in gam
                                  else "NO_KNOWN_GAMING_FACILITY" if typ == "gaming"
                                  else "ALL_ENTITIES"),
                "applicability_basis": ("data/clean/gaming_facilities.csv cedar_uid + "
                                        "operating_entity_cedar_uids" if typ == "gaming" else
                                        "every entity in the register is in scope"),
                "federal_side_identifiers_already_held":
                    (";".join(sorted(fed.get(uid, ()))) or "none") if typ == "identifiers" else "",
                "contamination_flags":
                    ";".join(sorted(con.get(uid, {}).get("*", set())
                                    | con.get(uid, {}).get(typ, set()))),
                "federal_side_identifiers_basis":
                    ("data/clean/cedar_identifier_ledger_final.csv - FEDERAL-side origin, "
                     "NOT a web harvest of this entity's own capability statement"
                     if typ == "identifiers" else ""),
                "built_by": BUILT_BY,
                "built_date": BUILT_DATE,
            })

    hdr = list(rows[0].keys())          # rule 17: the writer derives its own header
    os.makedirs(os.path.dirname(MATRIX), exist_ok=True)
    tmp = MATRIX + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, MATRIX)

    tmp = EVIDENCE + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cedar_uid", "harvest_type", "outcome", "artefact", "detail", "date"])
        w.writerows(sorted(set(EV)))
    os.replace(tmp, EVIDENCE)

    report(rows, gam)
    return rows


def report(rows, gam):
    print("\nentities %d  x types %d  = matrix rows %d" % (len(REG), len(TYPES), len(rows)))
    print("evidence records %d (from %d raw)" % (len(set(EV)), len(EV)))
    print("\n== OUTCOME BY HARVEST TYPE (denominator 1,555 entities each) ==")
    w = 24
    print("outcome".ljust(w) + "".join(t[:19].rjust(21) for t in TYPES))
    for o in PRECEDENCE:
        line = o.ljust(w)
        for t in TYPES:
            n = sum(1 for r in rows if r["harvest_type"] == t and r["outcome"] == o)
            line += "%21s" % format(n, ",")
        print(line)
    print("\n== THE HEADLINE: NEVER_CHECKED, per thing ==")
    for t in TYPES:
        n = sum(1 for r in rows if r["harvest_type"] == t and r["outcome"] == "NEVER_CHECKED")
        ni = sum(1 for r in rows if r["harvest_type"] == t and
                 r["outcome"] in ("NEVER_CHECKED", "ATTEMPTED_INCONCLUSIVE"))
        print("  %-22s never checked %5s / 1,555 (%5.1f%%)   no usable determination %5s (%5.1f%%)"
              % (t, format(n, ","), n / len(REG) * 100, format(ni, ","), ni / len(REG) * 100))
    print("\n== gaming, against the entities that actually operate a facility ==")
    g = [r for r in rows if r["harvest_type"] == "gaming"
         and r["applicability"] == "KNOWN_GAMING_OPERATOR"]
    print("  known gaming operators in the register: %d" % len(g))
    for o in PRECEDENCE:
        n = sum(1 for r in g if r["outcome"] == o)
        if n:
            print("    %-24s%5d" % (o, n))
    print("\n== NEVER_CHECKED on all five things ==")
    per = collections.defaultdict(set)
    for r in rows:
        if r["outcome"] == "NEVER_CHECKED":
            per[r["cedar_uid"]].add(r["harvest_type"])
    allfive = [u for u, ts in per.items() if len(ts) == 5]
    print("  %d entities have NEVER been looked at for ANY of the five" % len(allfive))
    for k, v in collections.Counter(UID[u]["entity_class"] for u in allfive).most_common():
        print("    %5d  %s" % (v, k))
    print("\n== CONTAMINATION: cells that are right about the artefact and may be "
          "wrong about the world ==")
    fl = collections.Counter()
    for r in rows:
        for f in r["contamination_flags"].split(";"):
            if f:
                fl[f.split("(")[0]] += 1
    for k, v in fl.most_common():
        ents = len({r["cedar_uid"] for r in rows if k in r["contamination_flags"]})
        print("  %-58s %5d cells on %4d entities" % (k, v, ents))
    worst = [r for r in rows if r["contamination_flags"]
             and r["outcome"] in ("HARVESTED", "FOUND_NOT_EXTRACTED")]
    print("  of those, %d cells claim HARVESTED or FOUND_NOT_EXTRACTED and are "
          "therefore the ones to re-check first" % len(worst))

    print("\n== NEVER_CHECKED by entity class, per thing ==")
    classes = sorted({r["entity_class"] for r in rows})
    print("class".ljust(52) + "".join(t[:9].rjust(11) for t in TYPES) + "     n")
    for c in classes:
        tot = sum(1 for x in REG if x["entity_class"] == c)
        line = c[:50].ljust(52)
        for t in TYPES:
            n = sum(1 for r in rows if r["entity_class"] == c and r["harvest_type"] == t
                    and r["outcome"] == "NEVER_CHECKED")
            line += "%11s" % format(n, ",")
        print(line + "%6s" % format(tot, ","))


# --------------------------------------------------------------------- verify
INVARIANTS = []


def verify(path=None):
    global INVARIANTS
    path = path or MATRIX
    rows = rd(path)
    fails = []

    def chk(name, ok, detail):
        INVARIANTS.append((name, ok, detail))
        if not ok:
            fails.append("%s: %s" % (name, detail))

    chk("matrix_exists", bool(rows), "%d rows read from %s" % (len(rows), path))
    chk("row_count_is_entities_x_types", len(rows) == len(REG) * len(TYPES),
        "expected %d, got %d" % (len(REG) * len(TYPES), len(rows)))
    uids = {r["cedar_uid"] for r in rows}
    chk("every_register_entity_present", uids == set(UID),
        "register %d vs matrix %d; missing %d, extra %d"
        % (len(UID), len(uids), len(set(UID) - uids), len(uids - set(UID))))
    pairs = {(r["cedar_uid"], r["harvest_type"]) for r in rows}
    chk("one_row_per_entity_per_type", len(pairs) == len(rows),
        "%d duplicate (entity,type) pairs" % (len(rows) - len(pairs)))
    bad = [r for r in rows if r["outcome"] not in RANK]
    chk("outcome_in_vocabulary", not bad, "%d rows with an outcome outside the six" % len(bad))
    bad = [r for r in rows if r["outcome"] != "NEVER_CHECKED" and not r["proving_artefact"]]
    chk("non_never_checked_names_an_artefact", not bad,
        "%d rows claim an outcome with no artefact naming it" % len(bad))
    bad = [r for r in rows if r["outcome"] == "NEVER_CHECKED" and r["n_evidence_records"] != "0"]
    chk("never_checked_has_no_evidence", not bad,
        "%d NEVER_CHECKED rows carry evidence records" % len(bad))
    missing = [r for r in rows if r["proving_artefact"]
               and not os.path.exists(P(*r["proving_artefact"].split("/")))]
    chk("every_named_artefact_exists_on_disk", not missing,
        "%d named artefacts are not on disk"
        % len({x["proving_artefact"] for x in missing}))

    for name, ok, detail in INVARIANTS:
        print(("  ok   " if ok else "  FAIL ") + name.ljust(40) + detail)
    if fails:
        print("\nVERIFY FAILED\n  " + "\n  ".join(fails))
        return 1
    print("\nVERIFY OK")
    return 0


def selftest():
    """Prove verify() exits 1 on a synthetic violation, then restore."""
    global INVARIANTS
    rows = rd(MATRIX)
    if not rows:
        print("selftest needs a built matrix")
        return 1
    tmp = MATRIX + ".selftest"
    hdr = list(rows[0].keys())
    poisoned = [dict(r) for r in rows]
    poisoned[0]["outcome"] = "HARVESTED"
    poisoned[0]["proving_artefact"] = ""            # breaks the artefact invariant
    poisoned = poisoned[:-1]                        # breaks the row-count invariant
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr)
        w.writeheader()
        w.writerows(poisoned)
    print("-- fixture: robots_bans_whole_site must not fire on a partial Disallow --")
    fixtures = [("no Disallow directives", False),
                ("our group (*): no Disallow directives", False),
                ("Disallow: /wp-admin/", False),
                ("['/wp-admin/']", False),
                ("['*?lightbox=']", False),
                ("robots.txt 404", False),
                ("Disallow: /; /CurrentEvents.aspx", True),
                ("['/']", True),
                ("robots.txt disallows ClaudeBot by name", True)]
    fx = [(t, robots_bans_whole_site(t), e) for t, e in fixtures
          if robots_bans_whole_site(t) != e]
    print("   %s  %d cases" % ("PASS" if not fx else "FAIL " + str(fx), len(fixtures)))

    print("\n-- verify against a POISONED copy (must exit 1) --")
    INVARIANTS = []
    rc_bad = verify(tmp)
    named = {n for n, ok, _ in INVARIANTS if not ok}
    os.remove(tmp)
    print("\n-- verify against the real matrix (must exit 0) --")
    INVARIANTS = []
    rc_good = verify(MATRIX)
    ok = (rc_bad == 1 and rc_good == 0 and not fx
          and {"row_count_is_entities_x_types",
               "non_never_checked_names_an_artefact"} <= named)
    print("\nSELFTEST %s - poisoned rc=%s fired=%s clean rc=%s"
          % ("PASS" if ok else "FAIL", rc_bad, sorted(named), rc_good))
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build()
        sys.exit(0)
    elif cmd == "verify":
        sys.exit(verify())
    elif cmd == "selftest":
        sys.exit(selftest())
    else:
        print(__doc__)
        sys.exit(2)
