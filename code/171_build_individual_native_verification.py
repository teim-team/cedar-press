"""171_build_individual_native_verification.py

Assemble the individual-Native OWNERSHIP VERIFICATION TABLE.

Reads the candidate set from 170 plus the web-verification batch outputs, and
writes ONE row per candidate carrying FOUR SEPARATE EVIDENCE FIELDS, the
verbatim sentence, the URL, the fetch date, and a tier that is COMPUTED FROM
THE EVIDENCE PRESENT rather than chosen.

  data/clean/individual_native_ownership_verification.csv

--------------------------------------------------------------------------
THE EVIDENCE MODEL - four fields, never collapsed into one boolean
--------------------------------------------------------------------------

  sam_self_certification   The federal filing: `reported_8a`,
                           `reported_buy_indian`, `reported_indian_business`,
                           `reported_native_preference`, plus `setaside`.
                           A legally-weighted assertion - a false
                           certification to a contracting officer carries
                           False Claims Act exposure - but it is STILL the
                           firm asserting its own status. START_HERE's
                           counter-example is load-bearing: Goldbelt Raven,
                           an ANC subsidiary, certifies
                           `alaskanNativeCorporationOwnedFirm = NO`.

  self_description         What the company's OWN website says, as a VERBATIM
                           SENTENCE with its URL and fetch date.

  third_party              SBA 8(a) / DSBS, a tribal or certifying body's
                           listing, trade press, a court or GAO decision.

  tribal_affiliation_named Does ANY source name the specific tribe or nation?
                           "a citizen of the Cherokee Nation" is a different
                           and stronger fact than "Native American owned".

--------------------------------------------------------------------------
THE INDEPENDENCE RULE - the reason this table exists at all
--------------------------------------------------------------------------

**SAM self-certification and the company website are the SAME PARTY speaking
in two venues.** They are not two sources. When they agree, what has been
established is that the firm is CONSISTENT, which is worth recording and is
not corroboration. Treating them as two legs would manufacture a tier-A
population out of one voice repeated twice - the same error shape as
START_HERE finding #1, where the exactness of an EIN was read as correctness
of the link.

So: **a tier-A row requires at least one leg that is NOT the firm speaking
about itself.** That is what `evidence_independence` records, and it is the
single most important column in the file.

--------------------------------------------------------------------------
TIER, COMPUTED - not assigned
--------------------------------------------------------------------------

Tier is a pure function of which legs are present. The function is here, in
one place, and `tier_basis` names the exact legs on every row so any reader
can recompute it. Nobody picks a tier by eye.

  A  an INDEPENDENT leg (a government/court/regulator/certifying-body/press
     source, or an owner ruling backed by a retrieved third-party document)
     AND a second leg agreeing with it
  B  exactly one non-SAM leg - the firm's own website sentence alone, a
     related-party listing alone, or an owner ruling resting on a narrative
     note
  C  SAM self-certification only: no claim found, no site found, or the site
     was unreachable
  X  a source names a NON-Native owner, contradicting the federal flag.
     This is a FINDING, not a deletion - it goes to review/ with its evidence.

--------------------------------------------------------------------------
WHAT THIS FILE WILL NEVER SAY
--------------------------------------------------------------------------

* `NOT_NATIVE`. Absence of a website claim is `NO_CLAIM_FOUND`. The firm may
  simply not advertise it; many small contractors do not.
* Ownership derived from a NAME. `name_trap_warning` exists to make it visible
  that the name did no work.
* That a 2026 page describes FY2000-2022 ownership. Every candidate row's
  contract activity ends FY2022 or earlier (measured, see the build log), so
  `temporal_caveat` is populated on 100% of rows and must travel with any
  quotation of this table.

SAFE TO RE-RUN. Reads only; writes via .part + rename.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CLEAN = os.path.join(ROOT, "data", "clean")
REVIEW = os.path.join(ROOT, "review")
WEBDIR = os.path.join(
    ROOT, "data", "raw", "web", "individual_native_verification_2026-08-26"
)

CANDIDATES = os.path.join(CLEAN, "individual_native_verification_candidates.csv")
OUT = os.path.join(CLEAN, "individual_native_ownership_verification.csv")
OUT_REVIEW = os.path.join(
    REVIEW, "individual_native_ownership_ambiguous_2026-08-26.csv"
)

TODAY = dt.date.today().isoformat()

# Evidence types on an owner ruling that were RETRIEVED FROM A THIRD PARTY.
# These make the owner's ruling an independent leg. A "Narrative note" does
# not - it records the conclusion without the document behind it.
THIRD_PARTY_EVIDENCE_TYPES = {
    "GAO decision",
    "CAGE registry lookup",
    "OpenCorporates filing",
}
# These are the FIRM speaking about itself, retrieved by the owner. Same voice
# as SAM, so they corroborate consistency, not independence.
SELF_EVIDENCE_TYPES = {
    "Company website",
    "Archived company website",
    "Owner note with URL",
}

# ---------------------------------------------------------------------------
# NOT EVERY "THIRD PARTY" IS A THIRD PARTY.
#
# The researchers flagged this themselves, repeatedly and unprompted: *"every
# directory hit (govtribe, highergov, govconinabox, opengovus) is SAM-derived,
# i.e. the same self-certification the project already has."* A federal-data
# aggregator republishing a SAM socio-economic flag is the FIRM'S OWN VOICE
# arriving by a longer road. Counting it as corroboration would double-count
# `sam_self_certification` and manufacture tier A out of one assertion - the
# exact failure this table's independence rule exists to prevent.
#
# A company-issued press release is the same problem in a different costume:
# PRNewswire and PRLog print what the company pays them to print.
#
# So third-party sources are typed into three buckets, by host:
#
#   INDEPENDENT              a government, court, regulator, certifying body,
#                            or independent journalism. Can carry a row to A.
#   RELATED_PARTY            a parent, JV partner or corporate-family site.
#                            Strong on ENTITY ownership and NOT independent of
#                            the ownership claim - it is the owner speaking.
#                            Counts as a leg; cannot carry a row to A alone.
#   SELF_SOURCED_AGGREGATOR  a SAM mirror, a business-data directory, or a
#                            company press release. NOT A LEG AT ALL.
#
# Anything unrecognised is treated as UNCLASSIFIED and does NOT confer
# independence. Unknown provenance is not independence.
# ---------------------------------------------------------------------------
INDEPENDENT_HOSTS = {
    "www.gao.gov", "gao.gov",
    "www.irs.gov", "irs.gov",
    "www.sba.gov", "sba.gov",
    "www.doa.nc.gov", "doa.nc.gov",          # NC HUB certifying office
    "tethys.pnnl.gov",                       # DOE national laboratory
    "www.ussbchamber.org", "ussbchamber.org",  # chamber / certifying body
    "www.spokanejournal.com",                # independent journalism
    "www.constructionequipment.com",
    "nativebusinesscenter.com",
    "stisha.net",                            # tribal enterprise, not the firm
}
SELF_SOURCED_HOSTS = {
    # SAM / federal-procurement mirrors - republished self-certification
    "www.govcb.com", "govcb.com",
    "www.govcon.com", "govcon.com",
    "fedbizconnect.com", "www.fedbizconnect.com",
    "www.sba8a.com", "sba8a.com",
    "opengovus.com", "www.opengovus.com",
    "govtribe.com", "www.govtribe.com",
    "www.highergov.com", "highergov.com",
    "govconinabox.com", "www.govconinabox.com",
    # business-data directories of unstated provenance
    "www.buzzfile.com", "buzzfile.com",
    "bisprofiles.com", "www.bisprofiles.com",
    "theorg.com", "www.theorg.com",
    "www.salary.com", "salary.com",
    "www.manta.com", "manta.com",
    "www.zoominfo.com", "zoominfo.com",
    # the company's own voice, paid for
    "www.linkedin.com", "linkedin.com",
    "www.prnewswire.com", "prnewswire.com",
    "biz.prlog.org", "prlog.org", "www.prlog.org",
}


def third_party_independence(url: str) -> str:
    """Type a third-party URL by host. Unknown never means independent."""
    if not url or not url.strip():
        return ""
    try:
        from urllib.parse import urlparse

        host = urlparse(url.strip()).netloc.lower()
    except Exception:
        return "UNCLASSIFIED"
    if not host:
        return "UNCLASSIFIED"
    if host in INDEPENDENT_HOSTS:
        return "INDEPENDENT"
    if host in SELF_SOURCED_HOSTS:
        return "SELF_SOURCED_AGGREGATOR"
    # A .gov or .mil host we have not enumerated is still a government source.
    if host.endswith(".gov") or host.endswith(".mil"):
        return "INDEPENDENT"
    # Everything else is most often a parent, JV partner or family site - the
    # owner speaking about what it owns. Real evidence, not independent.
    return "RELATED_PARTY"


NATIVE_KINDS = {
    "INDIVIDUAL_NATIVE",
    "TRIBAL_ENTITY",
    "ALASKA_NATIVE_CORPORATION",
    "NATIVE_HAWAIIAN_ORGANIZATION",
    "NATIVE_UNSPECIFIED",
}

CORP_SUFFIX_RE = re.compile(
    r"\b(inc|llc|l\.l\.c|corp|corporation|company|co|ltd|lp|llp|plc|group|"
    r"services|systems|enterprises|associates|solutions|holdings|technologies|"
    r"construction|consulting|industries|partners|international|joint venture|jv)\b",
    re.I,
)


def _read(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def privacy_class(name: str) -> str:
    """A sole proprietorship's legal name is frequently a private person's name.

    We never publish a page naming a private individual, so the row has to say
    which of its own fields are safe. This is deliberately CONSERVATIVE: a
    two-or-three token name with no corporate form is treated as possibly
    personal even when it is not, because the cost of the two errors is not
    symmetric.
    """
    n = (name or "").strip()
    if not n:
        return "UNKNOWN"
    if CORP_SUFFIX_RE.search(n):
        return "CORPORATE_FORM_PRESENT"
    toks = [t for t in re.split(r"[\s,]+", n) if t]
    if len(toks) <= 3:
        return "POSSIBLE_PERSONAL_NAME"
    return "NO_CORPORATE_FORM"


def compute_tier(row: dict) -> tuple[str, str, str]:
    """Return (tier, tier_basis, evidence_independence).

    Pure function of the legs present. Changing a tier means changing this
    function, in the open, for every row at once.
    """
    legs: list[str] = []
    independent: list[str] = []

    # LEG 1 - the federal filing. Present on every candidate by construction.
    # Self-certification: counted, never independent.
    if row.get("sam_self_certification") == "YES":
        legs.append("SAM_SELF_CERT(" + row.get("sam_flags_asserted", "") + ")")

    # LEG 2 - the firm's own website. Self-description: counted, never
    # independent. Same party as LEG 1.
    if row.get("self_description") == "CLAIM_FOUND" and row.get(
        "self_description_sentence"
    ):
        legs.append("SELF_DESCRIPTION")

    # LEG 3 - a third party, IF it is actually a third party. See
    # `third_party_independence()` above: a SAM mirror or a company press
    # release is the firm's own voice and is not a leg at all.
    tpi = row.get("third_party_independence", "")
    if row.get("third_party") == "FOUND" and row.get("third_party_url"):
        if tpi != "SELF_SOURCED_AGGREGATOR":
            legs.append(
                "THIRD_PARTY(" + row.get("third_party_source_type", "")
                + "/" + (tpi or "UNCLASSIFIED") + ")"
            )
        if tpi == "INDEPENDENT":
            independent.append("THIRD_PARTY")

    # LEG 4 - the project owner's own hand ruling. Independent ONLY when he
    # attached a document retrieved from somewhere other than the firm.
    pr = row.get("prior_owner_ruling")
    if pr:
        et = row.get("prior_owner_ruling_evidence_type", "")
        legs.append(f"OWNER_RULING({pr}/{et or 'unspecified'})")
        if et in THIRD_PARTY_EVIDENCE_TYPES:
            independent.append("OWNER_RULING_THIRD_PARTY_DOC")

    # X - a source contradicts the federal flag by naming a non-Native owner.
    if row.get("self_description_ownership_kind") == "NON_NATIVE_OWNER_NAMED":
        return (
            "X",
            "CONTRADICTION: " + " + ".join(legs),
            "INDEPENDENT_CONTRADICTION",
        )

    non_sam = [x for x in legs if not x.startswith("SAM_SELF_CERT")]
    if independent and len(legs) >= 2:
        tier = "A"
    elif non_sam:
        tier = "B"
    else:
        tier = "C"

    indep = (
        "INDEPENDENT_CORROBORATION"
        if independent
        else ("SELF_ASSERTION_ONLY" if non_sam else "FEDERAL_SELF_CERT_ONLY")
    )
    return tier, " + ".join(legs), indep


def main() -> int:
    cands = _read(CANDIDATES)
    if not cands:
        print("no candidate file - run 170 first")
        return 2

    # ---- merge the web pass, ON A STABLE IDENTIFIER -----------------------
    #
    # CAUGHT IN THE ACT, 2026-08-26 17:57. `verification_id` is POSITIONAL -
    # `INV-nnnn` in descending obligation order - and a concurrent agent
    # rewrote `prime_contracts.csv` between two runs of this pipeline. The
    # candidate set went 334 -> 335, every id below the insertion point shifted
    # by one, and **INV-0307 silently acquired Frontier Electronic Systems'
    # website sentence while naming Cherokee Construction, Inc.**
    #
    # That is a fabricated attribution produced by nothing worse than a rebuild
    # against a moving upstream, and it is the same shape as the Kootenai
    # regression and the re-run-57 regression already in AGENTS.md.
    #
    # The fix is not to freeze the upstream. It is to STOP JOINING ON A
    # POSITION. The input batches record `verification_id -> awardee_uei`, so
    # the web results are re-keyed to UEI (then CAGE, then normalised name) and
    # joined to the candidate set on identity. `web_pass_matched_on` records
    # which key carried each row, and anything that fails to match is reported
    # loudly rather than dropped.
    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (s or "").lower())

    vid_to_identity: dict[str, tuple[str, str, str]] = {}
    for b in sorted(glob.glob(os.path.join(WEBDIR, "input_batch_*.csv"))):
        for r in _read(b):
            vid = (r.get("verification_id") or "").strip()
            if vid:
                vid_to_identity[vid] = (
                    (r.get("awardee_uei") or "").strip().upper(),
                    (r.get("cage_code_modal") or "").strip().upper(),
                    _norm(r.get("awardee_name_modal", "")),
                )

    web_by_uei: dict[str, dict] = {}
    web_by_cage: dict[str, dict] = {}
    web_by_name: dict[str, dict] = {}
    n_web = 0
    orphan_web: list[str] = []
    batches = sorted(glob.glob(os.path.join(WEBDIR, "output_batch_*.csv")))
    for b in batches:
        for r in _read(b):
            vid = (r.get("verification_id") or "").strip()
            if not vid:
                continue
            ident = vid_to_identity.get(vid)
            if not ident:
                # No input row to anchor it. Refuse to guess.
                orphan_web.append(f"{os.path.basename(b)}:{vid}")
                continue
            r["_batch"] = os.path.basename(b)
            r["_vid_at_pass"] = vid
            uei, cage, name = ident
            n_web += 1
            if uei:
                web_by_uei[uei] = r
            if cage:
                web_by_cage.setdefault(cage, r)
            if name:
                web_by_name.setdefault(name, r)
    print(f"web batches present: {len(batches)}  rows re-keyed to identity: {n_web}")
    if orphan_web:
        print(f"  !! {len(orphan_web)} web rows have no input row and were NOT "
              f"merged: {', '.join(orphan_web[:8])}")

    # Prior-ruling evidence TYPE is not on the candidate file; pull it from the
    # prior-rulings file so the tier function can tell a retrieved document
    # from a narrative note.
    prior_ev: dict[str, str] = {}
    for p in _read(os.path.join(CLEAN, "individual_native_prior_rulings.csv")):
        key = (p.get("identifier") or "").upper()
        if key:
            prior_ev[key] = p.get("evidence_type", "")

    # ---- a FINER-GRAINED federal self-certification, where it exists -------
    # `prime_contracts.csv` carries four coarse flags. The SAM FY2000-2007
    # extract carries the field that actually separates the two kinds of Native
    # ownership: `flag_american_indian_owned` (a PERSON) against
    # `flag_tribally_owned_firm` (an ENTITY), plus `flag_sole_proprietorship`.
    # Measured 2026-08-26: McKinzie Construction carries
    # `flag_american_indian_owned = YES` on 122 rows with
    # `flag_tribally_owned_firm` never set - which is the individual class
    # asserted by the filer, in the filer's own federal record.
    #
    # Only the TRIBAL variant of that extract is loaded so far, so this hits 4
    # of 305. The two INDIVIDUAL_NATIVE_OWNED variants (AMERICAN INDIAN,
    # NATIVE AMERICAN) are the right join and are still generating - see the
    # build log. This block is written so it needs no change when they land.
    #
    # NOTE: this is still the SAME PARTY as `sam_self_certification`. It is a
    # sharper reading of one voice, never a second leg.
    sam_fine: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    sam_path = os.path.join(CLEAN, "sam_prime_contracts_fy2000_2007.csv")
    SAM_FINE_FLAGS = (
        "flag_american_indian_owned",
        "flag_sole_proprietorship",
        "flag_tribally_owned_firm",
        "flag_alaskan_native_corporation_owned",
        "flag_native_hawaiian_org_owned",
        "flag_indian_tribe_federally_recognized",
    )
    if os.path.exists(sam_path):
        want = {(c.get("awardee_uei") or "").upper() for c in cands if c.get("awardee_uei")}
        with open(sam_path, encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                u = (r.get("awardee_uei") or "").upper()
                if u not in want:
                    continue
                sam_fine[u]["_rows"] += 1
                for f in SAM_FINE_FLAGS:
                    if r.get(f) == "YES":
                        sam_fine[u][f] += 1
        print(f"SAM FY2000-2007 fine flags matched: {len(sam_fine)} candidate UEIs")

    WEB_FIELDS = [
        "self_description",
        "self_description_sentence",
        "self_description_url",
        "self_description_fetch_date",
        "self_description_http_status",
        "self_description_ownership_kind",
        "third_party",
        "third_party_source_type",
        "third_party_sentence",
        "third_party_url",
        "third_party_fetch_date",
        "tribal_affiliation_named",
        "tribal_affiliation_name",
        "tribal_affiliation_source",
    ]

    out_rows = []
    matched_on = collections.Counter()
    used_web: set[int] = set()
    for c in cands:
        row = dict(c)
        uei = (row.get("awardee_uei") or "").strip().upper()
        cage = (row.get("cage_code_modal") or "").strip().upper()
        nm = _norm(row.get("awardee_name_modal", ""))
        w = None
        how = ""
        if uei and uei in web_by_uei:
            w, how = web_by_uei[uei], "UEI"
        elif cage and cage in web_by_cage:
            w, how = web_by_cage[cage], "CAGE"
        elif nm and nm in web_by_name:
            w, how = web_by_name[nm], "NORMALISED_NAME"
        row["web_pass_matched_on"] = how
        matched_on[how or "NO_WEB_ROW"] += 1
        if w:
            used_web.add(id(w))
            for f in WEB_FIELDS:
                v = (w.get(f) or "").strip()
                if v:
                    row[f] = v
            row["researcher_note"] = (w.get("researcher_note") or "").strip()
            row["web_pass_batch"] = w.get("_batch", "")
            row["web_pass_verification_id"] = w.get("_vid_at_pass", "")
        else:
            row["researcher_note"] = ""
            row["web_pass_batch"] = ""
            row["web_pass_verification_id"] = ""

        sf = sam_fine.get((row.get("awardee_uei") or "").upper())
        row["sam_fine_flags_source"] = (
            "sam_prime_contracts_fy2000_2007.csv (TRIBAL variant only, "
            "2026-08-26)" if sf else ""
        )
        row["sam_fine_flags"] = (
            " | ".join(
                f"{k}={v}/{sf['_rows']}" for k, v in sorted(sf.items()) if k != "_rows"
            )
            if sf
            else ""
        )
        # The one federal field that separates a PERSON from an ENTITY.
        row["sam_individual_vs_entity"] = ""
        if sf:
            ind = sf.get("flag_american_indian_owned", 0)
            ent = (
                sf.get("flag_tribally_owned_firm", 0)
                + sf.get("flag_alaskan_native_corporation_owned", 0)
                + sf.get("flag_indian_tribe_federally_recognized", 0)
            )
            if ind and not ent:
                row["sam_individual_vs_entity"] = "INDIVIDUAL_ASSERTED"
            elif ent and not ind:
                row["sam_individual_vs_entity"] = "ENTITY_ASSERTED"
            elif ind and ent:
                row["sam_individual_vs_entity"] = "BOTH_ASSERTED_ON_DIFFERENT_ROWS"

        row["prior_owner_ruling_evidence_type"] = prior_ev.get(
            (row.get("awardee_uei") or "").upper(),
            prior_ev.get((row.get("cage_code_modal") or "").upper(), ""),
        )

        row["third_party_independence"] = third_party_independence(
            row.get("third_party_url", "")
        )
        tier, basis, indep = compute_tier(row)
        row["evidence_tier"] = tier
        row["tier_basis"] = basis
        row["evidence_independence"] = indep

        # ---- ownership class, from the strongest EVIDENCED source ----------
        # The owner's own ruling outranks everything and is never overwritten.
        if row.get("prior_owner_ruling") in (
            "INDIVIDUAL_NATIVE",
            "INDIVIDUAL_NATIVE_NOT_TRIBAL",
        ):
            row["ownership_class"] = "INDIVIDUAL_NATIVE"
            row["ownership_class_source"] = "OWNER_RULING"
        elif row.get("self_description_ownership_kind") in NATIVE_KINDS:
            row["ownership_class"] = row["self_description_ownership_kind"]
            row["ownership_class_source"] = "SELF_DESCRIPTION"
        elif row.get("self_description_ownership_kind") == "NON_NATIVE_OWNER_NAMED":
            row["ownership_class"] = "NON_NATIVE_OWNER_NAMED"
            row["ownership_class_source"] = "SELF_DESCRIPTION"
        elif row.get("third_party") == "FOUND":
            row["ownership_class"] = "NATIVE_UNSPECIFIED"
            row["ownership_class_source"] = "THIRD_PARTY"
        else:
            # NOT "not Native". Nobody looked, or nobody said.
            row["ownership_class"] = "UNDETERMINED"
            row["ownership_class_source"] = ""

        # ---- privacy -------------------------------------------------------
        pc = privacy_class(row.get("awardee_name_modal", ""))
        row["privacy_class"] = pc
        row["publishable_entity_name"] = "N" if pc == "POSSIBLE_PERSONAL_NAME" else "Y"
        row["publishable_contract_facts"] = "Y"
        row["publishable_sentence"] = (
            "N"
            if pc == "POSSIBLE_PERSONAL_NAME"
            and re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                          row.get("self_description_sentence", "") or "")
            else "Y"
        )
        # Provenance of the D&B question, answered PER FIELD rather than per
        # dataset. These rows come from BGOV `master prime file.dta` and the
        # USAspending award archive, NOT from a SAM entity extract, so the D&B
        # Open Data bulk restriction recorded in START_HERE does not attach.
        row["dnb_open_data_attaches"] = (
            "NO - prime_contracts is BGOV/USAspending-sourced, not SAM entity extract"
        )
        row["verification_built_date"] = TODAY
        row["verification_built_by"] = (
            "code/171_build_individual_native_verification.py"
        )
        out_rows.append(row)

    cols = list(cands[0].keys())
    for extra in [
        "researcher_note",
        "web_pass_batch",
        "web_pass_matched_on",
        "web_pass_verification_id",
        "sam_fine_flags",
        "sam_fine_flags_source",
        "sam_individual_vs_entity",
        "third_party_independence",
        "prior_owner_ruling_evidence_type",
        "evidence_tier",
        "tier_basis",
        "evidence_independence",
        "ownership_class",
        "ownership_class_source",
        "privacy_class",
        "publishable_entity_name",
        "publishable_sentence",
        "publishable_contract_facts",
        "dnb_open_data_attaches",
        "verification_built_date",
        "verification_built_by",
    ]:
        if extra not in cols:
            cols.append(extra)

    def write(path, fieldnames, data):
        part = path + ".part"
        with open(part, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for d in data:
                w.writerow({k: d.get(k, "") for k in fieldnames})
        os.replace(part, path)

    write(OUT, cols, out_rows)

    # ---- anything ambiguous goes to the owner, WITH its evidence -----------
    amb = []
    for r in out_rows:
        why = []
        if r["evidence_tier"] == "X":
            # X is NOT a disproof of the federal flag. It is a dated statement
            # about a firm whose contract rows are years older than the page,
            # and an acquisition inside the award window is the commonest
            # explanation. The caveat rides in the reason so it cannot be read
            # without it.
            why.append(
                "a source names a NON-Native owner against a federal native "
                "flag - READ WITH THE CAVEAT: " + (r.get("temporal_caveat") or "")
                + ". An ownership CHANGE inside the award window would produce "
                  "exactly this and would leave the federal flag correct for "
                  "the years it was filed"
            )
        if (
            r.get("self_description") == "CLAIM_FOUND"
            and r.get("prior_owner_ruling") == "INDIVIDUAL_NATIVE"
            and r.get("self_description_ownership_kind")
            not in ("INDIVIDUAL_NATIVE", "NATIVE_UNSPECIFIED", "")
        ):
            why.append(
                "website says "
                + r.get("self_description_ownership_kind", "")
                + " but your standing ruling is INDIVIDUAL_NATIVE - ruling NOT changed"
            )
        # THE HIGH-VALUE BY-PRODUCT. Every candidate is `attributed_flag = 0`:
        # Cedar attributes it to nobody. A firm whose OWN SITE says it is owned
        # by a tribe, an ANC or an NHO is therefore a MISSING TRIBAL
        # ATTRIBUTION, not an individual-Native firm - and it is missing at
        # whatever dollar figure sits in `total_obligations_usd`. This is the
        # opposite finding from the one the build set out to make, which is
        # exactly why it must not be swallowed.
        if r.get("self_description_ownership_kind") in (
            "TRIBAL_ENTITY",
            "ALASKA_NATIVE_CORPORATION",
            "NATIVE_HAWAIIAN_ORGANIZATION",
        ):
            why.append(
                "MISSING ENTITY ATTRIBUTION: the firm's own site declares "
                + r["self_description_ownership_kind"]
                + " ownership, and Cedar attributes it to nobody "
                  "(attributed_flag = 0) at $"
                + f"{float(r['total_obligations_usd'] or 0):,.0f}"
                + ". Which entity? Do not resolve from the NAME."
            )
        if r.get("third_party_independence") == "SELF_SOURCED_AGGREGATOR":
            why.append(
                "the only 'third party' found is a SAM mirror or a company "
                "press release ("
                + r.get("third_party_url", "")
                + ") - that is the firm's own certification arriving by a "
                  "longer road, so it was NOT counted as a leg"
            )
        if r.get("self_description") == "SITE_UNREACHABLE":
            why.append("site unreachable - retry, not a finding")
        # Only ask him about a class he has NOT already ruled. Re-queueing a
        # settled firm because a website sentence is vaguer than his ruling is
        # re-litigation wearing a question mark.
        if (
            r.get("self_description_ownership_kind") == "NATIVE_UNSPECIFIED"
            and r.get("tribal_affiliation_named") == "NO"
            and not r.get("prior_owner_ruling")
        ):
            why.append(
                "claims Native ownership without saying individual or tribal, "
                "and names no tribe - cannot be classed without you"
            )
        if r.get("name_trap_warning") and r.get("self_description") in (
            "NO_CLAIM_FOUND",
            "NO_SITE_FOUND",
        ):
            why.append(
                "native-sounding name ("
                + r["name_trap_warning"]
                + ") with NO supporting claim - the name is not evidence"
            )
        if not why:
            continue
        amb.append(
            {
                "verification_id": r["verification_id"],
                "awardee_name_modal": r["awardee_name_modal"],
                "awardee_uei": r["awardee_uei"],
                "total_obligations_usd": r["total_obligations_usd"],
                "fy_min": r["fy_min"],
                "fy_max": r["fy_max"],
                "sam_flags_asserted": r["sam_flags_asserted"],
                "self_description": r.get("self_description", ""),
                "self_description_sentence": r.get("self_description_sentence", ""),
                "self_description_url": r.get("self_description_url", ""),
                "third_party_url": r.get("third_party_url", ""),
                "evidence_tier": r["evidence_tier"],
                "tier_basis": r["tier_basis"],
                "temporal_caveat": r["temporal_caveat"],
                "prior_owner_ruling": r.get("prior_owner_ruling", ""),
                "why_queued": " | ".join(why),
                "YOUR_RULING": "",
                "YOUR_NOTE": "",
                "built_date": TODAY,
            }
        )
    write(OUT_REVIEW, list(amb[0].keys()) if amb else ["verification_id"], amb)

    # ---- report ------------------------------------------------------------
    n_unused = n_web - len(used_web)
    print("web join           ", dict(matched_on))
    if n_unused:
        print(f"  !! {n_unused} web rows matched no candidate - the candidate "
              "set moved under the web pass. Investigate before quoting.")
    tiers = collections.Counter(r["evidence_tier"] for r in out_rows)
    indep = collections.Counter(r["evidence_independence"] for r in out_rows)
    sd = collections.Counter(r.get("self_description", "") for r in out_rows)
    kinds = collections.Counter(r["ownership_class"] for r in out_rows)
    print(f"rows                        {len(out_rows):>6}")
    print(f"with a website sentence     "
          f"{sum(1 for r in out_rows if r.get('self_description_sentence')):>6}")
    print(f"with a third-party source   "
          f"{sum(1 for r in out_rows if r.get('third_party') == 'FOUND'):>6}")
    print(f"naming a specific tribe     "
          f"{sum(1 for r in out_rows if r.get('tribal_affiliation_named') == 'YES'):>6}")
    print(f"honouring a prior ruling    "
          f"{sum(1 for r in out_rows if r.get('prior_ruling_honored') == 'YES'):>6}")
    print("tier            ", dict(sorted(tiers.items())))
    print("independence    ", dict(indep))
    print("self_description", dict(sd))
    print("ownership_class ", dict(kinds))
    print(f"queued to review            {len(amb):>6}")
    print()
    print("wrote", os.path.relpath(OUT, ROOT))
    print("wrote", os.path.relpath(OUT_REVIEW, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
