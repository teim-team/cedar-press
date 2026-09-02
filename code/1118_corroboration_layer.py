#!/usr/bin/env python3
"""
1118 - THE CORROBORATION LAYER.  How many INDEPENDENT EVIDENCE FAMILIES
       support each fact, and where two of them disagree.

    py -3 code/1118_corroboration_layer.py build
    py -3 code/1118_corroboration_layer.py verify     # exits 1 on breach
    py -3 code/1118_corroboration_layer.py selftest   # proves verify FIRES

READ-ONLY against every dataset.  Writes only its own five tables.  No
network.  Does not commit.  Does not edit another dataset's table - what
should merge is named in `docs/CORROBORATION_LAYER_2026-09-02.md`.

===========================================================================
WHY
===========================================================================
`docs/ASSERTION_LAYER.md` measured the deepest structural weakness in Cedar:
every fact rests on exactly one observation.  Re-measured today from
`data/clean/cedar_resolved_facts.csv`: of 9,204 single-valued facts, 5,445
have ZERO evidence families, 3,757 have one, and 2 have two.

The assertion layer owns entity-grade facts.  This layer asks the same
question one level out, for the SHIPPING datasets, and answers it with a
number that cannot be inflated by copying a source into a second table.

===========================================================================
THE DEFINITION THIS LAYER TURNS ON
===========================================================================
An EVIDENCE FAMILY is a class of OBSERVER, not a file, a row, or a URL.

    federal_transactional   FPDS / FSRS / USAspending.  The federal
                            government recording that a transaction
                            happened, with the identifiers used on it.
    federal_registry        SAM, the Federal Register tribal list, NIGC,
                            IRS BMF, BIE, IHS, SBA.  A federal body
                            maintaining a register of who exists.
    audited_filing          ANCSA AS 45.55.139 annual report, Form 990
                            return, Single Audit, SEC filing.  A statement
                            the entity is legally obliged to make.
    entity_self_published   The entity's own website, capability statement,
                            company list, newsletter, press release.
    state_registry          A state regulator's own record.  A state is an
                            INDEPENDENT observer of an entity the federal
                            government also observes.
    court_record            IBIA / IBLA / a docket.  An adversarial process
                            with a party motivated to contradict.
    human_ruling            An owner ruling with a recorded reason.

Three things are named families here and DELIBERATELY DO NOT VOTE.  Naming
them rather than dropping them is what makes the exposure countable:

    cedar_inference         a name match, a containment link, cluster_v3, a
                            resolver output.  CEDAR AGREEING WITH ITSELF.
                            This is the largest thing that would otherwise
                            have been miscounted: `np_orgs.n_coders_agree`
                            reads like five sources and four of its five
                            coders are reading one IRS BMF row.
    compiled_directory      Casino City Press, the legacy CICD product, a
                            vendor property list.  Compiled, provenance
                            unknown, and in Cedar's case licence-constrained.
                            `data/spine/cedar_source_registry.csv` already
                            carries `independence_is_unverified = 1` on
                            LR_CICD for exactly this reason; this is the same
                            ruling applied to the gaming vendor directories.
    unattributed            no provenance was ever recorded.

===========================================================================
THE THREE RULES THAT STOP AN ECHO COUNTING AS A SECOND SOURCE
===========================================================================
R-A  SAME UPSTREAM DOCUMENT IS ONE OBSERVATION.
     Every observation carries an `upstream_key`; two sharing one collapse
     before families are counted.  The key is normalised, so a
     `web.archive.org/web/<stamp>/<url>` snapshot has the same upstream as
     the live `<url>`, because it IS that page.  Measured cost of not doing
     this: 220 of 651 two-source deals cite the SAME URL twice.

R-B  SAME PUBLISHER IS ONE OBSERVER unless the two documents are of
     different KINDS.  Two paths on one host are one observer; a Form 8-K
     body and its own Exhibit 99.1 are one document.  361 further deals are
     two paths on one host.  A host may still carry two kinds - an audited
     filing hosted on a state portal is not the portal's opinion - so the
     collapse is applied only where the FAMILY is also equal.

R-C  A FAMILY PAIR THAT SHARES AN UPSTREAM FOR THIS PREDICATE COLLAPSES.
     `SHARED_UPSTREAM` is predicate-scoped, because independence is not a
     property of two sources in general - it is a property of two sources
     ABOUT ONE THING.  USAspending's recipient NAME is copied from the SAM
     registration, so federal_transactional and federal_registry are ONE
     family for a name.  The same two are genuinely TWO for an identifier
     BINDING, because a CAGE is issued by DLA and a UEI by SAM.gov, and FPDS
     records the binding actually used on an award - three parties, not one
     registrant talking to itself.

===========================================================================
THE SIX PAIRS, AND WHAT EACH TESTS
===========================================================================
P1  nest_identifier    an enterprise CAGE the PARENT published on its own
                       site, against the same CAGE in `fpds_uei_cage_map`.
                       entity_self_published + federal_transactional.
P2  nest_ownership     `data/staging/nest/ownership_edges_staged.jsonl` at
                       OBSERVATION grain (3,796 rows for 1,610 enterprises),
                       plus the FPDS declared-parent column.
                       audited_filing + entity_self_published
                       + federal_transactional.
P3  deals              `Source_1`/`Source_2` in `deals_classified.csv`.
                       This pair mostly REMOVES corroboration Cedar already
                       claims in `Verification_Status`, and that is the
                       point of running it.
P4  nonprofit_native   `np_orgs.disposition` against the organisation's OWN
                       WORDS in its Form 990 narrative.
                       cedar_inference (0 votes) + audited_filing.
P5  gaming_affiliation the facility->tribe binding: the CGCC's own published
                       list against the property's own site.
                       state_registry + entity_self_published.
                       The NIGC roster link is read and REFUSED for this
                       predicate - the NIGC location map states a name and
                       an address and NO TRIBE, so the tribe on those rows is
                       Cedar's own.  It corroborates existence, not identity.
P6  gaming_ownership   who the property's own site says owns or operates it,
                       against Cedar's curated owner (which is a vendor
                       directory plus a Cedar match, so it does not vote).

Every source row read lands in exactly one NAMED bucket in
`cedar_corroboration_conservation.csv` - the I13 pattern from `510`.

===========================================================================
WRITES
===========================================================================
    data/clean/cedar_corroboration_observations.csv   one row per observation
    data/clean/cedar_fact_corroboration.csv           one row per fact
    data/clean/cedar_corroboration_disagreements.csv  both sides, both quoted
    data/clean/cedar_corroboration_census.csv         per shipping dataset
    data/clean/cedar_corroboration_conservation.csv   rows in = sum(buckets)
"""
import csv, json, os, sys, re, hashlib, datetime, collections

csv.field_size_limit(10 ** 8)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)

BUILT_BY   = "1118_corroboration_layer.py"
BUILT_DATE = datetime.date.today().isoformat()

OBS    = P("data", "clean", "cedar_corroboration_observations.csv")
FACTS  = P("data", "clean", "cedar_fact_corroboration.csv")
DISAG  = P("data", "clean", "cedar_corroboration_disagreements.csv")
CENSUS = P("data", "clean", "cedar_corroboration_census.csv")
CONSV  = P("data", "clean", "cedar_corroboration_conservation.csv")

# ---------------------------------------------------------------------------
# THE FAMILIES.  `votes` is the whole argument: a family that cannot be shown
# to be an independent OBSERVER may not raise a corroboration count.
# ---------------------------------------------------------------------------
FAMILIES = {
    "federal_transactional": dict(votes=1, note=(
        "FPDS / FSRS / USAspending. The federal government recording that a "
        "transaction happened, with the identifiers actually used on it.")),
    "federal_registry": dict(votes=1, note=(
        "SAM, the Federal Register list, NIGC, IRS BMF, BIE, IHS, SBA. A "
        "federal body maintaining a register of who exists.")),
    "audited_filing": dict(votes=1, note=(
        "ANCSA AS 45.55.139 annual report, Form 990 return, Single Audit, SEC "
        "filing. A statement the entity is legally obliged to make.")),
    "entity_self_published": dict(votes=1, note=(
        "The entity's own website, capability statement, company list, "
        "newsletter or press release. A member association's directory is "
        "folded in here rather than given a family of its own: it reports "
        "what the member told it, so it is the member speaking.")),
    "state_registry": dict(votes=1, note=(
        "A state regulator's own record - gaming commission, securities "
        "regulator, secretary of state.")),
    "court_record": dict(votes=1, note=(
        "IBIA / IBLA / a court docket. An adversarial process.")),
    "human_ruling": dict(votes=1, note=(
        "An owner ruling with a recorded reason.")),
    "cedar_inference": dict(votes=0, note=(
        "A name match, a containment link, cluster_v3, a resolver output. "
        "Cedar agreeing with itself. Never corroboration.")),
    "compiled_directory": dict(votes=0, note=(
        "A commercial or compiled directory - Casino City Press, the legacy "
        "CICD product, a vendor property list. Provenance unknown; the source "
        "registry already carries independence_is_unverified=1 on LR_CICD.")),
    "unattributed": dict(votes=0, note=(
        "No provenance was ever recorded. The ABSENCE of a source, made "
        "countable so it can be paid down.")),
}
VOTING = {k for k, v in FAMILIES.items() if v["votes"]}

# R-C.  (family_a, family_b, predicate_class) -> reason they collapse to one.
SHARED_UPSTREAM = {
    ("federal_registry", "federal_transactional", "legal_name"): (
        "USAspending / FPDS recipient identity fields are COPIED from the SAM "
        "registration. Agreeing about a name is one fact counted twice. "
        "data/spine/cedar_source_registry.csv: LR_USASPENDING derives_from "
        "LR_SAM."),
    ("federal_registry", "cedar_inference", "native_status"): (
        "np_orgs' Native determination IS a name match over an IRS BMF row. "
        "The IRS never asserts that an organisation is Native, so the "
        "register and Cedar's inference over it are one observation."),
}
def shared_upstream(a, b, pclass):
    return (SHARED_UPSTREAM.get((a, b, pclass))
            or SHARED_UPSTREAM.get((b, a, pclass)))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def norm_url(u):
    """R-A. The upstream a URL points AT, not the way it was retrieved."""
    u = (u or "").strip()
    if not u:
        return ""
    m = re.match(r"https?://web\.archive\.org/web/[^/]*?/(https?://.*)$", u, re.I)
    if m:
        u = m.group(1)
    else:
        m = re.match(r"https?://web\.archive\.org/web/[^/]*?/(.*)$", u, re.I)
        if m:
            u = m.group(1)
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = re.sub(r"^www\.", "", u, flags=re.I)
    u = u.split("#")[0].strip().rstrip("/").rstrip("*").rstrip("/")
    return u.lower()


def url_host(u):
    n = norm_url(u)
    return n.split("/")[0] if n else ""


def nname(s):
    """Fold a company name for comparison. Corporate SUFFIXES only."""
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\b(llc|l l c|inc|incorporated|corp|corporations?|company|co|"
               r"ltd|limited|lp|llp|plc|holdings?|group|the|of|and)\b", " ", s)
    return re.sub(r"\s+", "", s)


def toks(s):
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower())
            if len(t) > 2}


def fid(*parts):
    return "CORR-" + hashlib.sha1("|".join(str(p) for p in parts)
                                  .encode("utf-8")).hexdigest()[:14].upper()


def rd(p):
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def rj(p):
    out = []
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def wr(path, rows, cols):
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# CARDINALITY AND AGREEMENT.  Two lessons taken directly from
# docs/ASSERTION_LAYER.md rather than rediscovered:
#
# 1. R00 MULTI_VALUED_NO_CONTEST. One entity there holds 90 UEIs, all real,
#    and the first resolver read them as 90 competing answers to one question.
#    The same trap is live here: Nakupuna Foundation publishes EIGHT CAGE
#    codes on one page. Under a (subject, predicate) fact key that is one
#    fact with eight competing values, and it was reported CONTESTED before
#    this block existed. An identifier is multi-valued; the FACT is the
#    BINDING, so the value belongs in the key.
#
# 2. AGREEMENT IS NOT STRING EQUALITY for a name. The CGCC publishes
#    "Campo Band of Diegueno Mission Indians of the Campo Indian Reservation";
#    the property's own site says "Campo Kumeyaay Nation". Those are one
#    answer in two registers, and folding only corporate suffixes reported
#    five fabricated conflicts. Both sides are already pinned to ONE
#    facility_id, so the question is not "which entity is this" - rule 1 of
#    ENTITY_MATCH_RULES governs that and is untouched - but "do these two
#    statements about a known facility name the same nation".
MULTI_VALUED_CLASSES = {"identifier_binding"}

TRIBAL_DESCRIPTORS = {
    "band", "bands", "tribe", "tribes", "tribal", "nation", "nations",
    "indian", "indians", "mission", "reservation", "rancheria", "community",
    "pueblo", "village", "native", "american", "confederated", "federated",
    "the", "and", "for", "inc", "incorporated", "corporation", "corp", "llc",
    "authority", "gaming", "casino", "enterprises", "enterprise", "group",
    "california", "government", "council", "people", "peoples", "of",
}


def distinctive(s):
    return {t for t in toks(s) if t not in TRIBAL_DESCRIPTORS}


def values_agree(pclass, values):
    """AGREE / DISAGREE / NOT_COMPARABLE.

    NOT_COMPARABLE is a third answer on purpose. When one side's whole name
    is tribal descriptors - "the Confederated Tribes" - there is nothing
    distinctive left to compare, and returning AGREE there would be an
    absence of evidence printed as evidence of agreement.
    """
    vals = [v for v in values if v]
    if len(set(vals)) <= 1:
        return "AGREE"
    if pclass == "affiliation":
        sets = [distinctive(v) for v in vals]
        if any(not s for s in sets):
            return "NOT_COMPARABLE"
        return "AGREE" if set.intersection(*sets) else "DISAGREE"
    return "DISAGREE"


def factid(pair, subject, predicate, pclass, value_norm):
    """The value is part of the key for a MULTI-VALUED predicate (R00)."""
    if pclass in MULTI_VALUED_CLASSES:
        return fid(pair, subject, predicate, value_norm)
    return fid(pair, subject, predicate)


def clip(s, n=400):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s[:n]


# ---------------------------------------------------------------------------
# the accumulator
# ---------------------------------------------------------------------------
class Store:
    def __init__(self):
        self.obs = []
        self.consv = []
        self.disag = []
        self._seen = set()

    def observe(self, *, pair, dataset, subject, subject_label, predicate,
                predicate_class, value, value_norm, family, source_label,
                upstream_key, evidence_url="", quote="", origin_table="",
                observed_date=""):
        if family not in FAMILIES:
            raise SystemExit(
                "C1 at write time: undeclared evidence family %r from %s"
                % (family, pair))
        oid = fid(pair, subject, predicate, family, upstream_key, value_norm)
        if oid in self._seen:
            return
        self._seen.add(oid)
        self.obs.append(dict(
            observation_id=oid,
            fact_id=factid(pair, subject, predicate, predicate_class,
                           value_norm),
            pair=pair, dataset=dataset,
            subject=subject, subject_label=clip(subject_label, 200),
            predicate=predicate, predicate_class=predicate_class,
            object_value=clip(value, 300), object_norm=clip(value_norm, 300),
            evidence_family=family, family_votes=FAMILIES[family]["votes"],
            source_label=clip(source_label, 200),
            upstream_key=clip(upstream_key, 300),
            evidence_url=clip(evidence_url, 300),
            supporting_quote=clip(quote, 400),
            origin_table=origin_table, observed_date=observed_date,
            built_by=BUILT_BY, built_date=BUILT_DATE))

    def account(self, source_table, rows_in, buckets):
        """I13 pattern: rows in must equal the sum of NAMED dispositions."""
        bad = [k for k in buckets
               if k.strip().lower() in ("other", "unknown", "misc", "n/a", "")]
        if bad:
            raise SystemExit("C6: unnamed disposition reason %r on %s"
                             % (bad, source_table))
        self.consv.append(dict(
            source_table=source_table, rows_in=rows_in,
            rows_accounted=sum(buckets.values()),
            unaccounted=rows_in - sum(buckets.values()),
            dispositions=json.dumps(buckets, sort_keys=True),
            built_by=BUILT_BY, built_date=BUILT_DATE))

    def disagree(self, *, pair, dataset, fact_id, subject_label, predicate,
                 verdict, a_family, a_value, a_source, a_url, a_quote,
                 b_family, b_value, b_source, b_url, b_quote, note):
        self.disag.append(dict(
            disagreement_id=fid("D", pair, fact_id, a_value, b_value),
            fact_id=fact_id, pair=pair, dataset=dataset,
            subject_label=clip(subject_label, 200), predicate=predicate,
            verdict=verdict,
            side_a_family=a_family, side_a_value=clip(a_value, 300),
            side_a_source=clip(a_source, 200), side_a_url=clip(a_url, 300),
            side_a_quote=clip(a_quote, 400),
            side_b_family=b_family, side_b_value=clip(b_value, 300),
            side_b_source=clip(b_source, 200), side_b_url=clip(b_url, 300),
            side_b_quote=clip(b_quote, 400),
            resolution="REFUSED - recorded, not reconciled",
            note=clip(note, 600), built_by=BUILT_BY, built_date=BUILT_DATE))


# ===========================================================================
# P1  NEST identifier: a CAGE the parent published, against FPDS
# ===========================================================================
def p1_nest_identifier(S):
    nest = rd(P("data", "clean", "nest_enterprises.csv"))
    fmap = rd(P("data", "clean", "fpds_uei_cage_map.csv"))
    by_cage = collections.defaultdict(list)
    for r in fmap:
        c = (r.get("cage_code") or "").strip().upper()
        if c:
            by_cage[c].append(r)

    b = collections.Counter()
    for r in nest:
        basis = (r.get("identifier_basis") or "").strip()
        cage = (r.get("cage_code") or "").strip().upper()
        if not basis:
            b["no_self_published_identifier_basis"] += 1
            continue
        if not cage:
            b["self_published_basis_but_no_cage_value"] += 1
            continue
        sid = r.get("enterprise_id") or r.get("enterprise_name")
        lbl = r.get("enterprise_name", "")
        # side A - the parent's own page
        S.observe(pair="P1_nest_identifier", dataset="nest",
                  subject=sid, subject_label=lbl,
                  predicate="enterprise.identifier.CAGE",
                  predicate_class="identifier_binding",
                  value=cage, value_norm=cage,
                  family="entity_self_published",
                  source_label="parent's own published company page (%s)"
                               % clip(r.get("evidence_class"), 60),
                  upstream_key="url:" + (norm_url(r.get("source_url"))
                                         or "nest:" + str(sid)),
                  evidence_url=r.get("source_url", ""),
                  quote=basis,
                  origin_table="data/clean/nest_enterprises.csv")
        hits = by_cage.get(cage, [])
        if not hits:
            b["self_published_cage_absent_from_fpds"] += 1
            continue
        b["self_published_cage_matched_in_fpds"] += 1
        h = max(hits, key=lambda x: int(x.get("n_observations") or 0))
        S.observe(pair="P1_nest_identifier", dataset="nest",
                  subject=sid, subject_label=lbl,
                  predicate="enterprise.identifier.CAGE",
                  predicate_class="identifier_binding",
                  value=cage, value_norm=cage,
                  family="federal_transactional",
                  source_label="FPDS award records, CAGE<->UEI binding "
                               "(%s obs, %s-%s)" % (h.get("n_observations"),
                                                    h.get("first_year"),
                                                    h.get("last_year")),
                  upstream_key="fpds_uei_cage_map:" + cage,
                  evidence_url="",
                  quote="uei=%s legal_business_name=%s"
                        % (h.get("uei"), h.get("legal_business_name")),
                  origin_table="data/clean/fpds_uei_cage_map.csv")
        # disagreement test - the federal legal name against NEST's name
        fed = (h.get("legal_business_name") or "").strip()
        if fed and nname(fed) and nname(lbl) and nname(fed) != nname(lbl):
            if not (toks(fed) & toks(lbl)):
                S.disagree(
                    pair="P1_nest_identifier", dataset="nest",
                    fact_id=factid("P1_nest_identifier", sid,
                                   "enterprise.identifier.CAGE",
                                   "identifier_binding", cage),
                    subject_label=lbl,
                    predicate="enterprise.identifier.CAGE -> legal name",
                    verdict="SAME_CAGE_DIFFERENT_LEGAL_NAME",
                    a_family="entity_self_published", a_value=lbl,
                    a_source="parent's own company page",
                    a_url=r.get("source_url", ""), a_quote=basis,
                    b_family="federal_transactional", b_value=fed,
                    b_source="fpds_uei_cage_map.csv",
                    b_url="", b_quote="CAGE %s -> %s (%s FPDS observations)"
                                      % (cage, fed, h.get("n_observations")),
                    note="The parent publishes this CAGE for this firm; the "
                         "federal award record binds the same CAGE to a name "
                         "sharing no distinctive token. One of the two is "
                         "about a different legal person.")
    S.account("data/clean/nest_enterprises.csv (P1 self-published CAGE)",
              len(nest), dict(b))


# ===========================================================================
# P2  NEST ownership at OBSERVATION grain
# ===========================================================================
EVIDENCE_CLASS_FAMILY = {
    "audited_annual_report_as_45_55_139": "audited_filing",
    "parent_self_published_company_list": "entity_self_published",
    "nation_self_published_enterprise_register": "entity_self_published",
    "parent_declared_subsidiary_list": "entity_self_published",
}


def p2_nest_ownership(S):
    edges = rj(P("data", "staging", "nest", "ownership_edges_staged.jsonl"))
    b = collections.Counter()
    for e in edges:
        ec = e.get("evidence_class", "")
        fam = EVIDENCE_CLASS_FAMILY.get(ec)
        if not fam:
            b["evidence_class_not_mapped_to_a_family"] += 1
            continue
        child = e.get("child_name_raw") or ""
        hub = (e.get("hub_cedar_uid") or e.get("hub_handle")
               or e.get("hub_name") or "")
        if not child or not hub:
            b["edge_missing_child_or_hub"] += 1
            continue
        b["emitted_ownership_observation"] += 1
        subj = "%s|%s" % (hub, nname(child))
        # An audited filing is one FILER speaking, however many fiscal years
        # it filed; the upstream is the filer+source_id, not the document.
        if fam == "audited_filing":
            up = "as45.55.139:%s" % (e.get("hub_name") or hub)
        else:
            up = "url:" + (norm_url(e.get("source_url"))
                           or "src:" + str(e.get("source_id")))
        S.observe(pair="P2_nest_ownership", dataset="nest",
                  subject=subj, subject_label=child,
                  predicate="enterprise.owned_by",
                  predicate_class="ownership",
                  value=e.get("hub_name") or hub,
                  value_norm=nname(e.get("hub_name") or hub),
                  family=fam,
                  source_label="%s (%s)" % (ec, e.get("source_id")),
                  upstream_key=up,
                  evidence_url=e.get("source_url", ""),
                  quote=e.get("quote", ""),
                  observed_date=e.get("source_edition_date", ""),
                  origin_table="data/staging/nest/ownership_edges_staged.jsonl")
    S.account("data/staging/nest/ownership_edges_staged.jsonl",
              len(edges), dict(b))

    # the FPDS declared-parent family, already adjudicated by 1102
    nest = rd(P("data", "clean", "nest_enterprises.csv"))
    b2 = collections.Counter()
    for r in nest:
        v = (r.get("fpds_parent_corroboration") or "").strip()
        hub = (r.get("owner_hub_cedar_uid") or r.get("owner_hub_handle")
               or r.get("owner_hub_name") or "")
        child = r.get("enterprise_name") or ""
        subj = "%s|%s" % (hub, nname(child))
        if v == "CORROBORATED":
            b2["fpds_declared_parent_corroborates"] += 1
            S.observe(pair="P2_nest_ownership", dataset="nest",
                      subject=subj, subject_label=child,
                      predicate="enterprise.owned_by",
                      predicate_class="ownership",
                      value=r.get("owner_hub_name", ""),
                      value_norm=nname(r.get("owner_hub_name", "")),
                      family="federal_transactional",
                      source_label="parent DECLARED BY THE CHILD to FPDS "
                                   "(%s)" % clip(
                                       r.get("fpds_parent_corroboration_route"),
                                       60),
                      upstream_key="fpds_uei_edges:%s" % (
                          r.get("fpds_declared_parent_uei") or child),
                      evidence_url="",
                      quote=clip(r.get("fpds_parent_corroboration_basis"), 400),
                      origin_table="data/clean/nest_enterprises.csv")
        elif v == "CONTRADICTED":
            b2["fpds_declared_parent_contradicts"] += 1
            S.disagree(
                pair="P2_nest_ownership", dataset="nest",
                fact_id=factid("P2_nest_ownership", subj,
                               "enterprise.owned_by", "ownership", ""),
                subject_label=child, predicate="enterprise.owned_by",
                verdict="DECLARED_PARENT_IS_A_DIFFERENT_ENTITY",
                a_family="audited_filing/entity_self_published",
                a_value=r.get("owner_hub_name", ""),
                a_source="NEST evidence_class=%s source_id=%s"
                         % (r.get("evidence_class"), r.get("source_id")),
                a_url=r.get("source_url", ""),
                a_quote=clip(r.get("hub_resolution_note")
                             or r.get("relationship_as_recorded"), 400),
                b_family="federal_transactional",
                b_value=r.get("fpds_parent_resolves_to")
                        or r.get("fpds_declared_parent_name", ""),
                b_source="fpds_uei_edges.csv, declared parent at 20+ "
                         "observations",
                b_url="", b_quote=clip(r.get("fpds_parent_corroboration_basis"),
                                       400),
                note="The firm told FPDS a parent that resolves to a Cedar "
                     "entity other than the owner NEST publishes. "
                     "ENTITY_MATCH_RULES rule 12 says suspect the PARENT row "
                     "first; this layer records the conflict and refuses to "
                     "pick.")
        elif v:
            b2["fpds_" + v.lower()] += 1
        else:
            b2["fpds_column_blank"] += 1
    S.account("data/clean/nest_enterprises.csv (P2 FPDS declared parent)",
              len(nest), dict(b2))


# ===========================================================================
# P3  deals - the two-source claim, audited
# ===========================================================================
def deal_family(t):
    """Order matters and each early return earned its place.

    `moody` is tested BEFORE `press release`, because
    "Moody's Investors Service rating action (public press release...)"
    otherwise typed a rating agency as the entity speaking about itself - and
    the C3 probe caught it: one moodys.com URL wearing two families.
    """
    t = (t or "").lower()
    if not t.strip():
        return "unattributed", "no source type recorded"
    if "moody" in t or "rating agency" in t or "rating action" in t \
       or "s&p" in t or "fitch" in t:
        return "third_party_press", "a rating agency, not the issuer"
    if "sec filing" in t or "edgar" in t:
        return "audited_filing", "SEC"
    if "audited" in t or "annual report" in t or "as 45.55.139" in t \
       or "alaska division of banking" in t or "star portal" in t:
        return "audited_filing", "audited annual report"
    if "single audit" in t or "form 990" in t:
        return "audited_filing", "audited return"
    if "federal award" in t or "federal agency" in t or "usaspending" in t \
       or "fpds" in t or "cedar observation from fede" in t:
        return "federal_transactional", "federal award record or agency release"
    if "federal register" in t or "nigc" in t or "sam.gov" in t \
       or "senate" in t or "congress" in t or "committee" in t \
       or "justice.gov" in t:
        return "federal_registry", "a federal register or a chamber's own record"
    if "state agency" in t or "municipal" in t or ("state" in t and
            ("commission" in t or "regulator" in t or "secretary of state" in t
             or "release" in t)):
        return "state_registry", "a state or municipal body's own record"
    if "court" in t or "bankruptcy" in t or "docket" in t:
        return "court_record", "court"
    if "website" in t or "web site" in t or "press release" in t \
       or "newsroom" in t or "company release" in t or "newsletter" in t \
       or "tribal press" in t or "wordpress" in t or "corporate history" in t \
       or "transaction party" in t:
        return "entity_self_published", "the party's own announcement or site"
    if "advisor release" in t or "adviser release" in t:
        # the bank or law firm on the deal, announcing its own mandate. Not
        # the entity, not press - but it is a party to the transaction, and a
        # party's announcement is the same observer class as the entity's.
        return "entity_self_published", ("a transaction adviser's own release "
                                         "- a party to the deal, not a "
                                         "third-party observer")
    if "press" in t or "news" in t or "trade" in t or "radio" in t \
       or "journal" in t or "magazine" in t or "media" in t:
        return "third_party_press", "press"
    if "aggregator" in t or "database" in t or "directory" in t:
        return "compiled_directory", "a compiled product, provenance unknown"
    # LAST, not first. "Moody's Investors Service rating action (public press
    # release, retrieved via Internet Archive)" names an OBSERVER and then a
    # RETRIEVAL METHOD, and testing the retrieval method first typed a rating
    # agency as no observer at all. C3 caught it; the parenthetical only wins
    # when nothing else in the string names anybody.
    if "internet archive" in t or "wayback" in t:
        return "RETRIEVAL_METHOD", ("an Internet Archive snapshot is a way of "
                                    "RETRIEVING a page, not a second observer")
    return "UNMAPPED", t[:80]


# `third_party_press` is a real observer but it is not one of the seven
# declared families, and folding it into entity_self_published would be a lie
# (a trade journal is not the entity). It is mapped to its own family below so
# the taxonomy stays honest; it votes, because a reporter is an independent
# observer, but it can never corroborate a press release it is quoting - which
# R-A catches whenever both cite one URL.
FAMILIES["third_party_press"] = dict(votes=1, note=(
    "A trade journal, wire service, regional paper or rating agency. An "
    "independent observer, and the eighth family this layer had to add: the "
    "mandate's seven had nowhere honest to put a Trade press citation, and "
    "putting it in entity_self_published would have claimed a reporter is the "
    "entity. It cannot corroborate a press release it is reprinting - R-A "
    "catches that whenever both sides cite one URL."))
VOTING.add("third_party_press")


def p3_deals(S):
    deals = rd(P("data", "clean", "deals_classified.csv"))

    # PASS 0 - one document, one family, ACROSS THE WHOLE TABLE.
    # The same Moody's release is Source_2 of ND-2007-301 and Source_1 of
    # ND-2013-301, and the two rows type it differently. Unifying only within
    # a row left C3 failing on exactly that pair.
    global_family = {}
    for r in deals:
        for s, t in ((r.get("Source_1"), r.get("Source_1_Type")),
                     (r.get("Source_2"), r.get("Source_2_Type"))):
            s = (s or "").strip()
            if not s:
                continue
            fam, _ = deal_family(t)
            if fam in ("RETRIEVAL_METHOD", "UNMAPPED", "unattributed"):
                continue
            global_family.setdefault(
                "url:" + (norm_url(s) or "text:" + clip(s, 120)), fam)

    b = collections.Counter()
    for r in deals:
        did = r.get("Deal_ID") or ""
        title = r.get("Deal_Title") or ""
        s1, t1 = (r.get("Source_1") or "").strip(), r.get("Source_1_Type") or ""
        s2, t2 = (r.get("Source_2") or "").strip(), r.get("Source_2_Type") or ""
        if not did:
            b["row_has_no_deal_id"] += 1
            continue
        if not s1 and not s2:
            b["no_source_cited_at_all"] += 1
            continue
        sides = []
        for s, t, n in ((s1, t1, "Source_1"), (s2, t2, "Source_2")):
            if not s:
                continue
            fam, why = deal_family(t)
            sides.append((s, t, n, fam, why))
        if not sides:
            b["no_source_cited_at_all"] += 1
            continue

        if len(sides) == 1:
            b["one_source_cited"] += 1
        else:
            u = {norm_url(s) or "text:" + clip(s, 120) for s, _, _, _, _ in sides}
            h = {url_host(s) for s, _, _, _, _ in sides if url_host(s)}
            fams = {f for _, _, _, f, _ in sides}
            if len(u) == 1:
                b["two_citations_ONE_URL"] += 1
            elif len(h) == 1:
                b["two_citations_one_HOST"] += 1
            elif len(fams) == 1:
                b["two_citations_one_FAMILY"] += 1
            else:
                b["two_citations_two_families"] += 1

        # TWO CITATIONS OF ONE DOCUMENT MUST WEAR ONE FAMILY.
        # C3 caught two ways this went wrong: a Wayback snapshot typed
        # `unattributed` beside the live hud.gov PDF typed
        # `federal_transactional`, and a moodys.com rating action cited twice
        # where only one side carried a type string. The rule is the same in
        # both cases - unify on the most specific family present, because the
        # document does not change identity with the citation.
        upk = dict(global_family)
        resolved = []
        for s, t, n, fam, why in sides:
            u = "url:" + (norm_url(s) or "text:" + clip(s, 120))
            if fam == "RETRIEVAL_METHOD":
                fam2 = upk.get(u, "unattributed")
                why = ("Internet Archive snapshot - a RETRIEVAL METHOD, not "
                       "an observer. R-A collapses it onto the live URL and "
                       "it takes that page's family (%s)." % fam2)
                fam = fam2
            elif fam == "UNMAPPED":
                fam2 = upk.get(u)
                if fam2:
                    why = ("source type %r not mapped, but this citation is "
                           "the same document as a typed one; taking %s"
                           % (t[:80], fam2))
                    fam = fam2
                else:
                    fam = "unattributed"
                    why = "source type string not mapped to a family: " + t[:120]
            elif upk.get(u) and upk[u] != fam:
                why = ("two citations of one document disagreed on family "
                       "(%s vs %s); unified on the first specific one"
                       % (fam, upk[u]))
                fam = upk[u]
            resolved.append((s, t, n, fam, why))
        sides = resolved
        for s, t, n, fam, why in sides:
            S.observe(pair="P3_deals", dataset="deals",
                      subject=did, subject_label=title,
                      predicate="deal.event_occurred",
                      predicate_class="event",
                      value=r.get("Event_Date") or "",
                      value_norm=(r.get("Event_Date") or "")[:10],
                      family=fam, source_label="%s: %s" % (n, clip(t, 150)),
                      upstream_key="url:" + (norm_url(s)
                                             or "text:" + clip(s, 120)),
                      evidence_url=s, quote=why,
                      observed_date=r.get("Event_Date", ""),
                      origin_table="data/clean/deals_classified.csv")

    S.account("data/clean/deals_classified.csv", len(deals), dict(b))
    return {(r.get("Deal_ID") or ""): (r.get("Verification_Status") or "",
                                       (r.get("Source_1") or "").strip(),
                                       (r.get("Source_2") or "").strip(),
                                       r.get("Deal_Title") or "")
            for r in deals}


def p3_audit_verification_labels(S, facts, deal_meta):
    """A LABEL IS NOT EVIDENCE.

    Run AFTER independence is computed, because that is the only point at
    which Cedar's own `Verification_Status` can be compared with the number
    of independent observers actually cited. Only labels that unambiguously
    claim a second, independent observer are flagged; a bare "Verified" is
    reported in the doc as context rather than called a contradiction,
    because it does not say what it was verified against.
    """
    n = 0
    for f in facts:
        if f["pair"] != "P3_deals":
            continue
        vs, s1, s2, title = deal_meta.get(f["subject"], ("", "", "", ""))
        low = vs.lower()
        if not ("independent" in low or "corroborat" in low):
            continue
        if int(f["n_independent_families"]) >= 2:
            continue
        n += 1
        same_url = (s1 and s2 and norm_url(s1) == norm_url(s2))
        S.disagree(
            pair="P3_deals", dataset="deals", fact_id=f["fact_id"],
            subject_label=title, predicate="deal.verification_status",
            verdict=("VERIFICATION_CLAIM_RESTS_ON_ONE_DOCUMENT" if same_url
                     else "VERIFICATION_CLAIM_RESTS_ON_ONE_EVIDENCE_FAMILY"),
            a_family="cedar_inference", a_value=vs,
            a_source="deals_classified.Verification_Status",
            a_url="", a_quote="Cedar records this deal as %r" % vs,
            b_family=f["independent_families"] or "none",
            b_value="%s independent evidence famil%s cited"
                    % (f["n_independent_families"],
                       "y" if str(f["n_independent_families"]) == "1"
                       else "ies"),
            b_source="measured from the citations on the row",
            b_url=s2 or s1,
            b_quote="Source_1=%s | Source_2=%s" % (s1 or "(none)",
                                                   s2 or "(none)"),
            note=("The two cited sources are one page retrieved two ways; "
                  "R-A: a Wayback snapshot of a URL IS that URL."
                  if same_url else
                  "The label claims independent corroboration. The citations "
                  "reach %s independent observer(s) after R-A/R-B/R-C. The "
                  "label is the claim; this is the measurement."
                  % f["n_independent_families"]))
    return n


# ===========================================================================
# P4  nonprofit Native status: Cedar's inference vs the org's own 990 words
# ===========================================================================
# The organisation's own narrative CORROBORATES only where it gives a
# positive Native signal. `placename_only` and `no_native_signal` are SILENT:
# an absence of evidence is not evidence of absence, and the field guide's
# habit 4 exists because this project has published the opposite before.
MISSION_VERDICT = {
    "subject_classification": "CORROBORATES",
    "named_entity": "CORROBORATES",
    "program_authority": "CORROBORATES",
    "geographic": "CORROBORATES",
    "native_serving_not_native_controlled": "CONTRADICTS_CONTROL",
    "placename_only": "SILENT",
    "no_native_signal": "SILENT",
    "no_mission_text": "UNMEASURED",
}
NATIVE_DISPOSITIONS = {"NATIVE_VERIFIED_STRICT", "NATIVE_RULED_VERIFIED",
                       "NATIVE_PROPOSED_AWAITING_OWNER_RULING"}


def p4_nonprofit_native(S):
    mis = {}
    for d in rj(P("data", "staging", "np_mission", "inclusion_basis.jsonl")):
        mis[(d.get("ein") or "").strip().lstrip("0")] = d
    orgs = rd(P("data", "clean", "np_orgs.csv"))
    b = collections.Counter()
    for r in orgs:
        ein = (r.get("EIN") or "").strip().lstrip("0")
        disp = (r.get("disposition") or "").strip()
        if disp not in NATIVE_DISPOSITIONS:
            b["disposition_is_not_a_native_claim"] += 1
            continue
        subj = "EIN:" + ein
        lbl = r.get("org_name", "")
        ruling = (r.get("ruling_authority") or "").strip()
        fam_a = "human_ruling" if ruling == "elijah_ruling" else "cedar_inference"
        S.observe(pair="P4_nonprofit_native", dataset="nonprofits",
                  subject=subj, subject_label=lbl,
                  predicate="org.is_native_entity",
                  predicate_class="native_status",
                  value="yes", value_norm="yes",
                  family=fam_a,
                  source_label="np_orgs.disposition=%s (%s)"
                               % (disp, ruling or "name match over IRS BMF"),
                  upstream_key=("ruling:" + ein) if fam_a == "human_ruling"
                               else ("irs_bmf_name_match:" + ein),
                  evidence_url=r.get("source_url", ""),
                  quote=clip(r.get("evidence"), 400),
                  origin_table="data/clean/np_orgs.csv")
        d = mis.get(ein)
        if not d:
            b["native_claim_no_local_990_return"] += 1
            continue
        basis = d.get("inclusion_basis", "")
        verdict = MISSION_VERDICT.get(basis, "UNMEASURED")
        b["native_claim_990_" + verdict.lower()] += 1
        if verdict == "CORROBORATES":
            S.observe(pair="P4_nonprofit_native", dataset="nonprofits",
                      subject=subj, subject_label=lbl,
                      predicate="org.is_native_entity",
                      predicate_class="native_status",
                      value="yes", value_norm="yes",
                      family="audited_filing",
                      source_label="the organisation's OWN Form 990 narrative "
                                   "(%s)" % basis,
                      upstream_key="irs990_return:" + str(d.get("source_file")),
                      evidence_url="", quote=d.get("quote", ""),
                      observed_date=str(d.get("tax_period") or ""),
                      origin_table="data/staging/np_mission/"
                                   "inclusion_basis.jsonl")
        elif verdict in ("SILENT", "CONTRADICTS_CONTROL"):
            state_conflict = "state_conflict" in (r.get("cedar_link_basis") or "")
            if verdict == "CONTRADICTS_CONTROL":
                v = "OWN_990_SAYS_NATIVE_SERVING_NOT_NATIVE_CONTROLLED"
            elif state_conflict:
                v = "OWN_990_SILENT_AND_THE_LINK_CROSSES_A_STATE_LINE"
            else:
                v = "OWN_990_SILENT_ON_NATIVE_IDENTITY"
            S.disagree(
                pair="P4_nonprofit_native", dataset="nonprofits",
                fact_id=factid("P4_nonprofit_native", subj,
                               "org.is_native_entity", "native_status", ""),
                subject_label=lbl, predicate="org.is_native_entity",
                verdict=v,
                a_family=fam_a, a_value=disp,
                a_source="np_orgs.csv (%s)"
                         % (ruling or "name match over the IRS BMF"),
                a_url=r.get("source_url", ""),
                a_quote=clip(r.get("evidence"), 400),
                b_family="audited_filing",
                b_value="990 narrative basis = " + basis,
                b_source="the organisation's own Form 990 (%s)"
                         % d.get("source_file"),
                b_url="", b_quote=d.get("quote", ""),
                note=("SILENCE IS NOT REFUTATION. The organisation's own "
                      "words give no Native signal beyond a place name; that "
                      "weakens the claim, it does not disprove it. "
                      "Tongass Tlingit Cultural Heritage Institute scores "
                      "placename_only and is plainly Native. The subset worth "
                      "a human is the one where the Cedar link ALSO crosses a "
                      "state line." if verdict == "SILENT" else
                      "The organisation's own narrative describes serving "
                      "Native people without claiming Native control. "
                      "np_orgs asserts the stronger fact."))
    S.account("data/clean/np_orgs.csv (P4 Native-status claims)",
              len(orgs), dict(b))


# ===========================================================================
# P5 / P6  gaming
# ===========================================================================
def p5_gaming_affiliation(S):
    fac = rd(P("data", "clean", "gaming_facilities.csv"))
    known = {}
    b = collections.Counter()
    for r in fac:
        f = (r.get("facility_id") or "").strip()
        if not f:
            b["facility_row_has_no_facility_id"] += 1
            continue
        known[f] = r
        tribe = (r.get("tribe_canonical_name") or r.get("tribe") or "").strip()
        if not tribe:
            b["facility_has_no_tribe_attributed"] += 1
            continue
        b["cedar_curated_affiliation_emitted"] += 1
        # The vendor directory supplies the property; Cedar's matcher supplies
        # the tribe. Neither votes. Recorded so the exposure is countable.
        S.observe(pair="P5_gaming_affiliation", dataset="gaming",
                  subject="FAC:" + f, subject_label=r.get("facility_name", ""),
                  predicate="facility.affiliated_tribe",
                  predicate_class="affiliation",
                  value=tribe, value_norm=nname(tribe),
                  family="cedar_inference",
                  source_label="gaming_facilities.entity_match_method=%s over "
                               "%s" % (r.get("entity_match_method"),
                                       clip(r.get("source_datasets"), 80)),
                  upstream_key="cedar_match:" + f,
                  evidence_url="", quote=clip(r.get("entity_match_basis"), 400),
                  origin_table="data/clean/gaming_facilities.csv")
    S.account("data/clean/gaming_facilities.csv", len(fac), dict(b))

    # --- state_registry: the CGCC publishes facility AND tribe in one row ---
    ca = rd(P("data", "clean", "ca_gaming_facilities_official.csv"))
    b2 = collections.Counter()
    for r in ca:
        f = (r.get("facility_id") or "").strip()
        pub = (r.get("tribe_name_as_published") or "").strip()
        if not f:
            b2["cgcc_row_not_matched_to_a_cedar_facility"] += 1
            continue
        if not pub:
            b2["cgcc_row_publishes_no_tribe_name"] += 1
            continue
        b2["cgcc_state_observation_emitted"] += 1
        S.observe(pair="P5_gaming_affiliation", dataset="gaming",
                  subject="FAC:" + f,
                  subject_label=r.get("facility_name_as_published", ""),
                  predicate="facility.affiliated_tribe",
                  predicate_class="affiliation",
                  value=pub, value_norm=nname(pub),
                  family="state_registry",
                  source_label="California Gambling Control Commission, %s"
                               % r.get("list_type"),
                  upstream_key="cgcc:%s:%s" % (r.get("list_type"), f),
                  evidence_url=r.get("source_url", ""),
                  quote=r.get("source_quote", ""),
                  observed_date=r.get("as_of_date", ""),
                  origin_table="data/clean/ca_gaming_facilities_official.csv")
    S.account("data/clean/ca_gaming_facilities_official.csv", len(ca), dict(b2))

    # --- entity_self_published: the property's own site ---
    sp = rd(P("data", "clean",
              "gaming_property_self_published_assertions.csv"))
    b3 = collections.Counter()
    for r in sp:
        cls = (r.get("assertion_class") or "").strip()
        f = (r.get("facility_id") or "").strip()
        if cls not in ("SELF_PUBLISHED_OWNERSHIP_ASSERTION",
                       "SELF_PUBLISHED_MANAGEMENT_ASSERTION",
                       "SELF_PUBLISHED_IDENTITY_ASSERTION"):
            b3["assertion_class_is_not_identity_or_ownership"] += 1
            continue
        if not f:
            b3["self_published_row_not_attributed_to_one_facility"] += 1
            continue
        if (r.get("facility_attribution_status") or "") == \
           "TRIBE_LEVEL_MULTI_FACILITY_NOT_DISAMBIGUATED":
            b3["tribe_level_not_disambiguated_to_a_facility"] += 1
            continue
        val = (r.get("asserted_value") or "").strip()
        if cls == "SELF_PUBLISHED_IDENTITY_ASSERTION":
            b3["identity_assertion_states_a_name_not_a_tribe"] += 1
            continue
        if not val:
            b3["ownership_assertion_with_no_asserted_value"] += 1
            continue
        b3["self_published_ownership_observation_emitted"] += 1
        S.observe(pair="P5_gaming_affiliation", dataset="gaming",
                  subject="FAC:" + f, subject_label=r.get("facility_name", ""),
                  predicate="facility.affiliated_tribe",
                  predicate_class="affiliation",
                  value=val, value_norm=nname(val),
                  family="entity_self_published",
                  source_label="the property's own site (%s, %s)"
                               % (r.get("site_host"),
                                  r.get("assertion_subclass")),
                  upstream_key="url:" + (norm_url(r.get("source_url"))
                                         or "host:" + str(r.get("site_host"))),
                  evidence_url=r.get("source_url", ""),
                  quote=r.get("source_quote", ""),
                  observed_date=r.get("as_of_date", ""),
                  origin_table="data/clean/"
                               "gaming_property_self_published_assertions.csv")
        # MEASURE THE AGREEMENT HERE rather than inheriting the upstream
        # `agrees_with_curated_owner` string. The upstream field reports
        # `no_distinctive_token_either_side` on 57 rows, which is a statement
        # about token availability, not about disagreement. Re-measured with
        # this layer's own descriptor-stripped test the two answers coincide
        # on the DISAGREE set (2 facilities) - which is the point of checking.
        cur = (r.get("cedar_curated_owner") or "").strip()
        if cur and values_agree("affiliation", {cur, val}) == "DISAGREE":
            S.disagree(
                pair="P5_gaming_affiliation", dataset="gaming",
                fact_id=factid("P5_gaming_affiliation", "FAC:" + f,
                               "facility.affiliated_tribe", "affiliation", ""),
                subject_label=r.get("facility_name", ""),
                predicate="facility.affiliated_tribe",
                verdict="SELF_PUBLISHED_OWNER_NAMES_A_DIFFERENT_NATION",
                a_family="cedar_inference", a_value=cur,
                a_source="gaming_facilities curated owner (vendor directory "
                         "+ Cedar match)",
                a_url="", a_quote="cedar_curated_owner=%s" % cur,
                b_family="entity_self_published", b_value=val,
                b_source="the property's own site, %s" % r.get("site_host"),
                b_url=r.get("source_url", ""),
                b_quote=r.get("source_quote", ""),
                note="Neither side shares a distinctive token with the other. "
                     "Recorded, not reconciled: a management brand is not "
                     "ownership (Caesars MANAGES Harrah's Cherokee, EBCI OWNS "
                     "it), so a mismatch here can be a real difference of "
                     "SUBJECT rather than a wrong answer.")
    S.account("data/clean/gaming_property_self_published_assertions.csv",
              len(sp), dict(b3))

    # --- federal_registry, READ AND REFUSED for this predicate ---
    nl = rd(P("data", "clean", "gaming_nigc_roster_link.csv"))
    S.account("data/clean/gaming_nigc_roster_link.csv (P5 - refused)",
              len(nl),
              {"nigc_map_states_a_name_and_address_but_no_tribe": len(nl)})


# ===========================================================================
# P7  THE HEADLINE PAIR: an identifier the ENTITY published about ITSELF,
#     against the same identifier held on the federal side.
#
#     Every UEI, CAGE and EIN Cedar holds arrived from the federal side -
#     SAM, FPDS, the IRS BMF.  An entity's own capability statement, JSON-LD
#     block or about page stating the SAME identifier is a genuinely
#     independent family for that binding, because a CAGE is issued by DLA,
#     a UEI by SAM.gov and an EIN by the IRS: three issuers, and the entity
#     is a fourth party restating what it was issued.
#
#     R-C note: federal_registry and federal_transactional collapse for a
#     legal NAME (USAspending copies SAM) but NOT for an identifier binding,
#     which is why `predicate_class` is `identifier_binding` here.
# ===========================================================================
# THIS REGEX WAS WRONG ONCE AND THE WRONG VERSION IS WORTH KEEPING VISIBLE.
# v1 was  (?:\bEIN\b|Employer\s+Identification|Tax\s*ID|TIN)[^0-9]{0,24}(\d{9})
# and it produced 81 "disagreements", of which the most common single value
# was 314192535 - Facebook's `facebookAppId`, reached because `TIN` carried no
# word boundary and so matched inside "marketing", and because a bare nine
# digits needs no label at all to look like an EIN. A detector that fires on a
# tracking pixel is the repo's signature defect: it produced a number, the
# number was plausible, and it was about something else.
#
# v2 requires a LABELLED occurrence and, for the bare nine-digit form, a
# STRONG label. Strictness is the safe direction here: a missed corroboration
# is silence, a false one is a fabricated disagreement about a real
# organisation.
_EIN_STRONG = (r"(?:\bE\.?I\.?N\.?\b|Employer\s+Identification(?:\s+Number)?"
               r"|\bFederal\s+Tax\s*(?:ID|Identification|Number)"
               r"|\bTax\s*ID(?:entification)?(?:\s*(?:#|No\.?|Number))?)")
EIN_LABEL = re.compile(
    _EIN_STRONG + r"[\s:#=\-]{0,6}(?:is\s+)?(?:(\d{2})\s*-\s*(\d{7})|(\d{9})\b)",
    re.I)


def eins_in(text):
    """Every labelled EIN in a page, normalised to nine digits."""
    out = set()
    for a, b, c in EIN_LABEL.findall(text):
        out.add((a + b) if a else c)
    return out


def _ledger_index():
    """cedar_uid -> set of identifiers Cedar holds FEDERALLY, and the reverse."""
    fed = collections.defaultdict(set)
    who = collections.defaultdict(set)
    rows = rd(P("data", "clean", "cedar_identifier_ledger_final.csv"))
    for r in rows:
        v = (r.get("identifier") or "").strip().upper().replace("-", "")
        t = (r.get("identifier_type") or "").strip().upper()
        uid = (r.get("cedar_uid") or "").strip()
        tier = (r.get("confidence_tier") or "").strip().upper()
        if not v:
            continue
        if tier == "X":          # a tier X row is a REFUTATION of the link
            continue
        fed[(t, v)].add(uid)
        if uid:
            who[uid].add((t, v))
    return rows, fed, who


def p7_self_published_identifiers(S):
    ledger_rows, fed, _ = _ledger_index()
    fmap = rd(P("data", "clean", "fpds_uei_cage_map.csv"))
    fed_uei = {(r.get("uei") or "").strip().upper() for r in fmap}
    fed_cage = {(r.get("cage_code") or "").strip().upper() for r in fmap}

    def federal_side(t, v):
        """Return (family, source_label, upstream_key) or None."""
        if (t, v) in fed:
            return ("federal_registry",
                    "cedar_identifier_ledger_final.csv - the federal-side "
                    "register (SAM / IRS BMF), tier not X",
                    "federal_ledger:%s:%s" % (t, v))
        if t == "UEI" and v in fed_uei:
            return ("federal_transactional",
                    "fpds_uei_cage_map.csv - the identifier used on a "
                    "federal award", "fpds_uei_cage_map:UEI:" + v)
        if t == "CAGE" and v in fed_cage:
            return ("federal_transactional",
                    "fpds_uei_cage_map.csv - the identifier used on a "
                    "federal award", "fpds_uei_cage_map:CAGE:" + v)
        return None

    def emit(route, subject, label, ityp, ival, url, quote, origin):
        S.observe(pair="P7_self_published_identifier", dataset="_entity_layer",
                  subject=subject, subject_label=label,
                  predicate="identifier." + ityp,
                  predicate_class="identifier_binding",
                  value=ival, value_norm=ival,
                  family="entity_self_published",
                  source_label="the entity's own %s" % route,
                  upstream_key="url:" + (norm_url(url) or route + ":" + subject),
                  evidence_url=url, quote=quote, origin_table=origin)
        f = federal_side(ityp, ival)
        if not f:
            return False
        fam, lab, up = f
        S.observe(pair="P7_self_published_identifier", dataset="_entity_layer",
                  subject=subject, subject_label=label,
                  predicate="identifier." + ityp,
                  predicate_class="identifier_binding",
                  value=ival, value_norm=ival,
                  family=fam, source_label=lab, upstream_key=up,
                  evidence_url="", quote="%s %s is held federally" % (ityp, ival),
                  origin_table="data/clean/cedar_identifier_ledger_final.csv")
        return True

    # --- 7a  firm capability statements, via the business crosswalk ---------
    xw = rd(P("data", "clean", "native_business_identifier_crosswalk.csv"))
    b = collections.Counter()
    for r in xw:
        if r.get("identifier_method") != "self_published_on_firm_website":
            b["identifier_read_from_the_federal_side_not_self_published"] += 1
            continue
        ityp = (r.get("identifier_type") or "").strip().upper()
        ival = (r.get("identifier_value") or "").strip().upper()
        if not ityp or not ival:
            b["self_published_row_with_no_identifier_value"] += 1
            continue
        ok = emit("capability statement", "BUS:" + (r.get("business_source_id")
                                                    or ival),
                  r.get("business_name_raw", ""), ityp, ival,
                  r.get("identifier_source_url", ""),
                  r.get("identifier_evidence", ""),
                  "data/clean/native_business_identifier_crosswalk.csv")
        b["self_published_" + ityp.lower() +
          ("_matched_federally" if ok else "_absent_from_the_federal_side")] += 1
    S.account("data/clean/native_business_identifier_crosswalk.csv",
              len(xw), dict(b))

    # --- 7b  code/1114's capability-statement harvest ----------------------
    # SNAPSHOT. 1114 is another workstream's live harvest; its row count is
    # printed in the conservation table so this number is re-derivable rather
    # than trusted.
    cap = rd(P("data", "staging", "capability_1114", "identifier_findings.csv"))
    b2 = collections.Counter()
    for r in cap:
        ityp = (r.get("identifier_type") or "").strip().upper()
        ival = (r.get("identifier") or "").strip().upper()
        if not ityp or not ival:
            b2["finding_with_no_identifier_value"] += 1
            continue
        ok = emit("capability statement / our-companies page",
                  r.get("cedar_uid") or ival, r.get("canonical_name", ""),
                  ityp, ival, r.get("source_url", ""),
                  r.get("evidence_quote", ""),
                  "data/staging/capability_1114/identifier_findings.csv")
        b2["self_published_" + ityp.lower() +
           ("_matched_federally" if ok else "_absent_from_the_federal_side")] += 1
    S.account("data/staging/capability_1114/identifier_findings.csv "
              "(SNAPSHOT of a live harvest)", len(cap), dict(b2))

    # --- 7c  JSON-LD identifier blocks surfaced in the web map -------------
    wm = rd(P("data", "staging", "cedar_web_map.csv"))
    b3 = collections.Counter()
    PUB = re.compile(r"PUBLISHES ITS OWN IDENTIFIERS:\s*(.+?)(?:\s*\||$)")
    for r in wm:
        ev = r.get("evidence") or ""
        m = PUB.search(ev)
        if not m:
            b3["web_map_row_states_no_self_published_identifier"] += 1
            continue
        # CONSERVATION IS AT ROW GRAIN. One row can publish four identifiers;
        # counting identifiers here made rows_in - sum(buckets) = -5 and C6
        # fired on it. The identifier tally rides in its own table below.
        found = 0
        matched = 0
        for lab, val in re.findall(r"(SAM UEI|CAGE Code|TIN/EIN|DUNS)\s*=\s*"
                                   r"([A-Z0-9\-]+)", m.group(1)):
            ityp = {"SAM UEI": "UEI", "CAGE Code": "CAGE",
                    "TIN/EIN": "EIN", "DUNS": "DUNS"}[lab]
            ival = val.replace("-", "").strip().upper()
            ok = emit("published JSON-LD identifier block",
                      r.get("cedar_uid") or ival, r.get("canonical_name", ""),
                      ityp, ival, r.get("url", ""), clip(m.group(1), 300),
                      "data/staging/cedar_web_map.csv")
            found += 1
            matched += 1 if ok else 0
        if not found:
            b3["self_published_marker_present_but_no_parseable_identifier"] += 1
        elif matched:
            b3["row_publishes_identifiers_at_least_one_held_federally"] += 1
        else:
            b3["row_publishes_identifiers_none_held_federally"] += 1
    S.account("data/staging/cedar_web_map.csv", len(wm), dict(b3))

    # --- 7d  a nonprofit's own about page stating its own EIN --------------
    pages_dir = P("data", "staging", "np_harvest", "raw", "pages")
    orgs = {(r.get("EIN") or "").strip().zfill(9): r
            for r in rd(P("data", "clean", "np_orgs.csv"))}
    b4 = collections.Counter()
    files = sorted(os.listdir(pages_dir)) if os.path.isdir(pages_dir) else []
    for fn in files:
        m = re.match(r"^(\d{9})_", fn)
        if not m:
            b4["filename_carries_no_ein"] += 1
            continue
        ein = m.group(1)
        org = orgs.get(ein)
        if not org:
            b4["page_ein_is_not_in_np_orgs"] += 1
            continue
        try:
            with open(os.path.join(pages_dir, fn), encoding="utf-8",
                      errors="ignore") as f:
                txt = f.read()
        except OSError:
            b4["page_unreadable"] += 1
            continue
        stated = eins_in(txt)
        if not stated:
            b4["page_states_no_labelled_ein"] += 1
            continue
        if ein not in stated:
            b4["page_states_a_DIFFERENT_ein_than_the_irs_side"] += 1
            S.disagree(
                pair="P7_self_published_identifier", dataset="nonprofits",
                fact_id=factid("P7_self_published_identifier", "EIN:" + ein,
                               "identifier.EIN", "identifier_binding", ein),
                subject_label=org.get("org_name", ""),
                predicate="identifier.EIN",
                verdict="SELF_PUBLISHED_EIN_DIFFERS_FROM_THE_IRS_SIDE_EIN",
                a_family="federal_registry", a_value=ein,
                a_source="IRS Exempt Organizations BMF via np_orgs.csv",
                a_url="", a_quote="np_orgs holds EIN %s for %s"
                                  % (ein, org.get("org_name")),
                b_family="entity_self_published",
                b_value=",".join(sorted(stated)),
                b_source="the organisation's own page, %s" % fn,
                b_url=org.get("source_url", ""),
                b_quote=clip(EIN_LABEL.search(txt).group(0), 200),
                note="The page harvested under this EIN states a different "
                     "one. Either the page belongs to a different "
                     "organisation or one of the two numbers is wrong. "
                     "Recorded, not reconciled.")
            continue
        b4["page_states_the_SAME_ein_as_the_irs_side"] += 1
        q = ""
        mm = EIN_LABEL.search(txt)
        if mm:
            s = max(0, mm.start() - 90)
            q = re.sub(r"<[^>]+>", " ", txt[s:mm.end() + 40])
        S.observe(pair="P7_self_published_identifier", dataset="nonprofits",
                  subject="EIN:" + ein, subject_label=org.get("org_name", ""),
                  predicate="identifier.EIN",
                  predicate_class="identifier_binding",
                  value=ein, value_norm=ein,
                  family="entity_self_published",
                  source_label="the organisation's own web page (%s)" % fn,
                  upstream_key="np_harvest_page:" + fn,
                  evidence_url=org.get("source_url", ""), quote=q,
                  origin_table="data/staging/np_harvest/raw/pages/")
        S.observe(pair="P7_self_published_identifier", dataset="nonprofits",
                  subject="EIN:" + ein, subject_label=org.get("org_name", ""),
                  predicate="identifier.EIN",
                  predicate_class="identifier_binding",
                  value=ein, value_norm=ein,
                  family="federal_registry",
                  source_label="IRS Exempt Organizations BMF (eo1-eo4)",
                  upstream_key="irs_bmf:" + ein,
                  evidence_url="", quote="BMF holds EIN %s for %s"
                                         % (ein, org.get("org_name")),
                  origin_table="data/clean/np_orgs.csv")
    S.account("data/staging/np_harvest/raw/pages/ (self-stated EIN)",
              len(files), dict(b4))


# ===========================================================================
# independence
# ===========================================================================
def independence(observations):
    """Return (n_independent_families, sorted families, collapse notes).

    R-A  one upstream_key is one observation
    R-B  one host + one family is one observer
    R-C  a family pair sharing an upstream for this predicate class collapses
    """
    notes = []
    # R-A
    by_up = {}
    for o in observations:
        by_up.setdefault(o["upstream_key"], []).append(o)
    if len(by_up) < len(observations):
        notes.append("R-A collapsed %d observations onto %d upstream documents"
                     % (len(observations), len(by_up)))
    survivors = [v[0] for v in by_up.values()]
    # R-B
    by_hf = {}
    for o in survivors:
        h = url_host(o["evidence_url"])
        k = (h, o["evidence_family"]) if h else (o["upstream_key"],
                                                 o["evidence_family"])
        by_hf.setdefault(k, []).append(o)
    if len(by_hf) < len(survivors):
        notes.append("R-B collapsed %d observations onto %d publisher/family "
                     "pairs" % (len(survivors), len(by_hf)))
    survivors = [v[0] for v in by_hf.values()]
    fams = sorted({o["evidence_family"] for o in survivors})
    voting = sorted(f for f in fams if f in VOTING)
    nonvoting = sorted(f for f in fams if f not in VOTING)
    if nonvoting:
        notes.append("non-voting families present and not counted: "
                     + ",".join(nonvoting))
    # R-C
    pclass = observations[0]["predicate_class"] if observations else ""
    dropped = set()
    for i, a in enumerate(voting):
        for bfam in voting[i + 1:]:
            if a in dropped or bfam in dropped:
                continue
            why = shared_upstream(a, bfam, pclass)
            if why:
                dropped.add(bfam)
                notes.append("R-C collapsed %s into %s: %s" % (bfam, a, why))
    voting = [f for f in voting if f not in dropped]
    return len(voting), voting, nonvoting, notes


# ===========================================================================
# build
# ===========================================================================
# Read off docs/DATASET_READINESS.md. It was FOURTEEN rows when this pass
# began and is FIFTEEN now - `newsletters` landed the same day (code/1105).
# Hard-coding the list is deliberate: C8 must fail loudly when the scoreboard
# grows, rather than silently measuring a shrinking denominator.
SHIPPING_DATASETS = [
    "_entity_layer", "contractors", "deals", "federal-register", "funding",
    "gaming", "legislation", "lobbying", "nagpra", "native-owned-businesses",
    "natural-resources", "nest", "newsletters", "nonprofits", "subcontracting",
]
# What this layer actually reached, and if not, WHY NOT - never a blank.
CENSUS_REASON = {
    "_entity_layer": ("NOT_REACHED_BY_THIS_PASS", "Only the identifier "
        "bindings in P7 were examined here; the rest of the entity layer "
        "belongs to the assertion layer (code/510), whose own measurement "
        "stands: 9,204 single-valued facts, 2 with two independent families."),
    "contractors": ("SINGLE_FAMILY_BY_CONSTRUCTION", "Every row IS the "
        "federal transaction record. A second family would have to be the "
        "vendor's own statement of the award; none is on disk."),
    "federal-register": ("SINGLE_FAMILY_BY_CONSTRUCTION", "The Federal "
        "Register is the source and the fact. A republication of it is the "
        "same family - measured by 510: harvesting the roster moved the "
        "corroborated count by zero."),
    "funding": ("SINGLE_FAMILY_BY_CONSTRUCTION", "USAspending assistance "
        "transactions. The recipient identity fields are copied from SAM, so "
        "SAM cannot corroborate them (R-C, legal_name)."),
    "legislation": ("NOT_REACHED_BY_THIS_PASS", "Roll-call and bill records "
        "come from one congressional source; no second observer harvested."),
    "lobbying": ("NOT_REACHED_BY_THIS_PASS", "LDA filings are self-reported "
        "to one registry. Form 990 Schedule C is a genuine second family for "
        "the same spend and IS on disk (data/staging/np_mission/"
        "schedule_c_lobbying.csv, 553 filers in np_orgs) - the highest-value "
        "unbuilt pair this pass found."),
    "nagpra": ("SINGLE_FAMILY_BY_CONSTRUCTION", "A NAGPRA notice IS the "
        "Federal Register record."),
    "newsletters": ("SINGLE_FAMILY_BY_CONSTRUCTION", "A finding aid for what "
        "an entity publishes. Every row IS the entity's own channel, so the "
        "one family it can have is entity_self_published and there is no "
        "second observer of a masthead. The 15th collection, added the same "
        "day as this layer by code/1105."),
    "native-owned-businesses": ("NOT_REACHED_BY_THIS_PASS", "The directories "
        "publish no federal identifiers, so the crosswalk runs from the "
        "federal side and the two sides are one family by construction "
        "(NATIVE_BUSINESS_IDENTIFIER_CROSSWALK_LOG). A tribal certification "
        "register is the independent family; 26 rows are staged."),
    "natural-resources": ("NOT_REACHED_BY_THIS_PASS", "ONRR and state "
        "severance tables cover different revenue streams rather than the "
        "same fact twice; state and federal figures for ONE stream would be "
        "a real pair and were not tested here."),
    "subcontracting": ("SINGLE_FAMILY_BY_CONSTRUCTION", "FSRS is the prime's "
        "own report to one federal system."),
}


def build():
    S = Store()
    p1_nest_identifier(S)
    p2_nest_ownership(S)
    deal_meta = p3_deals(S)
    p4_nonprofit_native(S)
    p5_gaming_affiliation(S)
    p7_self_published_identifiers(S)

    groups = collections.defaultdict(list)
    for o in S.obs:
        groups[o["fact_id"]].append(o)

    facts = []
    for f, os_ in groups.items():
        n, voting, nonvoting, notes = independence(os_)
        o0 = os_[0]
        pclass = o0["predicate_class"]
        vals = {o["object_norm"] for o in os_ if o["object_norm"]}
        voting_vals = {o["object_value"] for o in os_
                       if o["evidence_family"] in VOTING and o["object_value"]}
        agree = values_agree(pclass, voting_vals)
        if n >= 2:
            verdict = {"AGREE": "CORROBORATED",
                       "DISAGREE": "CONTESTED",
                       "NOT_COMPARABLE": "TWO_FAMILIES_VALUE_NOT_COMPARABLE"
                       }[agree]
        elif n == 1:
            verdict = "TRACEABLE_SINGLE_FAMILY"
        else:
            verdict = "NO_VOTING_FAMILY"
        if agree == "NOT_COMPARABLE":
            notes.append("values not comparable: one side's whole name is "
                         "generic descriptors, nothing distinctive to match")
        facts.append(dict(
            fact_id=f, pair=o0["pair"], dataset=o0["dataset"],
            subject=o0["subject"], subject_label=o0["subject_label"],
            predicate=o0["predicate"], predicate_class=o0["predicate_class"],
            object_value=sorted(vals)[0] if len(vals) == 1 else
                         " | ".join(sorted(vals)),
            n_observations=len(os_),
            n_distinct_upstreams=len({o["upstream_key"] for o in os_}),
            n_independent_families=n,
            independent_families=",".join(voting),
            non_voting_families=",".join(nonvoting),
            n_distinct_values=len(vals),
            corroboration_verdict=verdict,
            value_agreement=agree,
            collapse_notes=clip("; ".join(notes), 600),
            built_by=BUILT_BY, built_date=BUILT_DATE))

    n_lbl = p3_audit_verification_labels(S, facts, deal_meta)

    # ---- census ----
    per_ds = collections.defaultdict(lambda: collections.Counter())
    for r in facts:
        c = per_ds[r["dataset"]]
        c["facts"] += 1
        c["fam_%d" % min(r["n_independent_families"], 3)] += 1
        if r["n_independent_families"] >= 2:
            c["multi"] += 1
        if r["corroboration_verdict"] == "CONTESTED":
            c["contested"] += 1
    dis_ds = collections.Counter(d["dataset"] for d in S.disag)

    census = []
    for ds in SHIPPING_DATASETS:
        if ds in per_ds:
            c = per_ds[ds]
            extra = CENSUS_REASON.get(ds, ("", ""))[1]
            census.append(dict(
                dataset=ds, status="MEASURED_BY_1118",
                facts_examined=c["facts"],
                facts_zero_families=c["fam_0"],
                facts_one_family=c["fam_1"],
                facts_two_or_more_families=c["multi"],
                facts_contested=c["contested"],
                disagreements_recorded=dis_ds.get(ds, 0),
                wholly_single_sourced="N" if c["multi"] else "Y",
                reason=("%d of %d facts examined reach two independent "
                        "evidence families. %s"
                        % (c["multi"], c["facts"], extra)).strip(),
                built_by=BUILT_BY, built_date=BUILT_DATE))
        else:
            st, why = CENSUS_REASON.get(
                ds, ("NOT_REACHED_BY_THIS_PASS", "not examined"))
            census.append(dict(
                dataset=ds, status=st, facts_examined=0,
                facts_zero_families="", facts_one_family="",
                facts_two_or_more_families=0, facts_contested="",
                disagreements_recorded=0, wholly_single_sourced="Y",
                reason=why, built_by=BUILT_BY, built_date=BUILT_DATE))

    wr(OBS, S.obs, ["observation_id", "fact_id", "pair", "dataset", "subject",
                    "subject_label", "predicate", "predicate_class",
                    "object_value", "object_norm", "evidence_family",
                    "family_votes", "source_label", "upstream_key",
                    "evidence_url", "supporting_quote", "origin_table",
                    "observed_date", "built_by", "built_date"])
    wr(FACTS, facts, ["fact_id", "pair", "dataset", "subject", "subject_label",
                      "predicate", "predicate_class", "object_value",
                      "n_observations", "n_distinct_upstreams",
                      "n_independent_families", "independent_families",
                      "non_voting_families", "n_distinct_values",
                      "corroboration_verdict", "value_agreement",
                      "collapse_notes",
                      "built_by", "built_date"])
    wr(DISAG, S.disag, ["disagreement_id", "fact_id", "pair", "dataset",
                        "subject_label", "predicate", "verdict",
                        "side_a_family", "side_a_value", "side_a_source",
                        "side_a_url", "side_a_quote", "side_b_family",
                        "side_b_value", "side_b_source", "side_b_url",
                        "side_b_quote", "resolution", "note", "built_by",
                        "built_date"])
    wr(CENSUS, census, ["dataset", "status", "facts_examined",
                        "facts_zero_families", "facts_one_family",
                        "facts_two_or_more_families", "facts_contested",
                        "disagreements_recorded", "wholly_single_sourced",
                        "reason", "built_by", "built_date"])
    wr(CONSV, S.consv, ["source_table", "rows_in", "rows_accounted",
                        "unaccounted", "dispositions", "built_by",
                        "built_date"])

    print("observations   %6d" % len(S.obs))
    print("facts          %6d" % len(facts))
    print("disagreements  %6d" % len(S.disag))
    hist = collections.Counter(r["n_independent_families"] for r in facts)
    for k in sorted(hist):
        print("  %d independent families : %6d facts" % (k, hist[k]))
    print()
    for r in census:
        print("  %-26s %-28s facts=%-6s >=2fam=%-5s single=%s"
              % (r["dataset"], r["status"], r["facts_examined"],
                 r["facts_two_or_more_families"], r["wholly_single_sourced"]))
    return 0


# ===========================================================================
# verify - seven invariants, every one proven to FIRE by `selftest`
# ===========================================================================
def verify():
    fails = []

    def bad(code, msg):
        fails.append("%s: %s" % (code, msg))

    obs = rd(OBS)
    facts = rd(FACTS)
    disag = rd(DISAG)
    consv = rd(CONSV)
    census = rd(CENSUS)
    if not obs or not facts:
        print("C0 UNMEASURED: the layer has not been built. Run `build`.")
        return 1

    by_fact = collections.defaultdict(list)
    for o in obs:
        by_fact[o["fact_id"]].append(o)

    # C1 every family is declared
    for o in obs:
        if o["evidence_family"] not in FAMILIES:
            bad("C1", "undeclared evidence family %r on %s"
                % (o["evidence_family"], o["observation_id"]))
            break

    # C2 no fact claims more families than its observations support
    for r in facts:
        os_ = by_fact.get(r["fact_id"], [])
        if not os_:
            bad("C2", "fact %s has no observations" % r["fact_id"])
            break
        n, voting, _, _ = independence(os_)
        if int(r["n_independent_families"]) != n:
            bad("C2", "fact %s claims %s independent families; its "
                      "observations support %d (%s)"
                % (r["fact_id"], r["n_independent_families"], n,
                   ",".join(voting)))
            break

    # C3 ONE UPSTREAM DOCUMENT WEARS ONE FAMILY, everywhere in the store.
    #
    # This is not C2 restated. C2 asks whether a fact's COUNT matches its
    # observations; C3 asks whether the TYPING is coherent. A single document
    # carrying two families is a family-assignment bug, and it is invisible to
    # C2 because R-A collapses the pair to one observation and the count comes
    # out right for the wrong reason.
    #
    # It found three real bugs on its first run, all in P3:
    #   * six hud.gov award PDFs typed `federal_transactional` on the live URL
    #     and `unattributed` on the Wayback snapshot of the same PDF;
    #   * one moodys.com rating action typed `third_party_press` on one side
    #     and `entity_self_published` on the other, because the type string
    #     contains the words "press release" and the rating-agency test ran
    #     after it;
    #   * one beringstraits.com page, unmapped on one side.
    fam_by_up = collections.defaultdict(set)
    for o in obs:
        fam_by_up[o["upstream_key"]].add(o["evidence_family"])
    for up, fams in fam_by_up.items():
        if len(fams) > 1:
            bad("C3", "upstream document %r is typed to %d evidence families "
                      "(%s). One document is one observer."
                % (up[:120], len(fams), ",".join(sorted(fams))))
            break

    # C4 a non-voting family never contributes
    for r in facts:
        for f in (r["independent_families"] or "").split(","):
            if f and f not in VOTING:
                bad("C4", "fact %s counts non-voting family %r"
                    % (r["fact_id"], f))
                break

    # C5 every disagreement quotes BOTH sides
    for d in disag:
        if not (d["side_a_quote"].strip() or d["side_a_url"].strip()):
            bad("C5", "disagreement %s has no evidence on side A"
                % d["disagreement_id"])
            break
        if not (d["side_b_quote"].strip() or d["side_b_url"].strip()):
            bad("C5", "disagreement %s has no evidence on side B"
                % d["disagreement_id"])
            break

    # C6 source-row conservation, named reasons only
    for c in consv:
        if int(c["unaccounted"]) != 0:
            bad("C6", "%s: %s rows unaccounted"
                % (c["source_table"], c["unaccounted"]))
            break
        for k in json.loads(c["dispositions"]):
            if k.strip().lower() in ("other", "unknown", "misc", "n/a", ""):
                bad("C6", "%s: unnamed disposition %r" % (c["source_table"], k))
                break

    # C7 CORROBORATED means >=2 families AND one agreed value
    for r in facts:
        if r["corroboration_verdict"] == "CORROBORATED":
            if int(r["n_independent_families"]) < 2:
                bad("C7", "fact %s is CORROBORATED on %s families"
                    % (r["fact_id"], r["n_independent_families"]))
                break
            voting_vals = {o["object_value"] for o in by_fact[r["fact_id"]]
                           if o["evidence_family"] in VOTING
                           and o["object_value"]}
            if values_agree(r["predicate_class"], voting_vals) != "AGREE":
                bad("C7", "fact %s is CORROBORATED but its voting families "
                          "do not agree (%s): %s"
                    % (r["fact_id"],
                       values_agree(r["predicate_class"], voting_vals),
                       " | ".join(sorted(voting_vals))[:180]))
                break

    # C8 the census names every shipping dataset, with a reason, never blank
    seen = {c["dataset"] for c in census}
    for ds in SHIPPING_DATASETS:
        if ds not in seen:
            bad("C8", "census omits shipping dataset %r" % ds)
            break
    for c in census:
        if not c["reason"].strip():
            bad("C8", "census row %r carries no reason" % c["dataset"])
            break

    if fails:
        for f in fails:
            print("FAIL " + f)
        print("\n%d invariant(s) breached." % len(fails))
        return 1
    print("verify OK - C1..C8 clean over %d observations, %d facts, "
          "%d disagreements." % (len(obs), len(facts), len(disag)))
    return 0


# ===========================================================================
# selftest - inject the violation, assert exit 1 AND the named invariant
# ===========================================================================
def selftest():
    import shutil
    targets = [OBS, FACTS, DISAG, CENSUS, CONSV]
    for t in targets:
        if not os.path.exists(t):
            print("selftest UNMEASURED: build first.")
            return 1
    baks = {}
    for t in targets:
        baks[t] = t + ".bak_%s_pre_1118_selftest" % BUILT_DATE
        shutil.copy2(t, baks[t])

    import io, contextlib

    def run():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = verify()
        return rc, buf.getvalue()

    results = []
    try:
        rc, out = run()
        results.append(("baseline", rc == 0, "expected 0, got %d" % rc, out))

        def mutate(path, fn, code):
            rows = rd(path)
            cols = list(rows[0].keys())
            fn(rows)
            wr(path, rows, cols)
            rc, out = run()
            ok = rc == 1 and ("FAIL " + code) in out
            results.append((code, ok,
                            "expected exit 1 naming %s" % code,
                            out.strip().splitlines()[0] if out.strip() else ""))
            shutil.copy2(baks[path], path)

        mutate(OBS, lambda R: R[0].__setitem__("evidence_family",
                                               "made_up_family"), "C1")

        # C3: give one upstream document a second family, leaving every count
        # untouched, so nothing but C3 can catch it.
        def two_families_one_document(R):
            up = R[0]["upstream_key"]
            fam = R[0]["evidence_family"]
            twin = dict(R[0])
            twin["observation_id"] = twin["observation_id"] + "-SELFTEST"
            twin["evidence_family"] = ("state_registry"
                                       if fam != "state_registry"
                                       else "court_record")
            R.insert(1, twin)
        mutate(OBS, two_families_one_document, "C3")
        # C2: inflate a family count that the observations do not support
        def infl(R):
            for r in R:
                if r["n_independent_families"] == "1":
                    r["n_independent_families"] = "7"
                    return
            R[0]["n_independent_families"] = "7"
        mutate(FACTS, infl, "C2")

        def nonvote(R):
            for r in R:
                if int(r["n_independent_families"]) >= 1:
                    r["independent_families"] = "cedar_inference"
                    return
        mutate(FACTS, nonvote, "C4")

        if rd(DISAG):
            mutate(DISAG, lambda R: (R[0].__setitem__("side_b_quote", ""),
                                     R[0].__setitem__("side_b_url", "")),
                   "C5")

        def unacct(R):
            R[0]["unaccounted"] = "13"
        mutate(CONSV, unacct, "C6")

        def unnamed(R):
            R[0]["dispositions"] = json.dumps({"other": 1})
            R[0]["unaccounted"] = "0"
        mutate(CONSV, unnamed, "C6")

        def corr(R):
            for r in R:
                if int(r["n_independent_families"]) < 2:
                    r["corroboration_verdict"] = "CORROBORATED"
                    return
        mutate(FACTS, corr, "C7")

        def dropds(R):
            for i, r in enumerate(R):
                if r["dataset"] == "gaming":
                    del R[i]
                    return
        mutate(CENSUS, dropds, "C8")

        rc, out = run()
        results.append(("restored", rc == 0, "expected 0, got %d" % rc, out))
    finally:
        for t, b in baks.items():
            shutil.copy2(b, t)
            os.remove(b)

    allok = True
    for name, ok, expect, detail in results:
        print("%-10s %s   %s" % (name, "PASS" if ok else "FAIL",
                                 "" if ok else expect + " | " + detail[:160]))
        allok = allok and ok
    print("\nselftest %s" % ("PASS - every invariant fires on a synthetic "
                             "violation and the layer is clean again after "
                             "restore." if allok else "FAIL"))
    return 0 if allok else 1


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        return build()
    if cmd == "verify":
        return verify()
    if cmd == "selftest":
        return selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
