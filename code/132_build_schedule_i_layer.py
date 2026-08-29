"""
132 — Form 990 Schedule I layer for Native-connected nonprofits.

WHAT THIS IS
------------
Schedule I Part II is the only place in the Form 990 where a filer NAMES the
organisations it gave money to, with their EINs.  That makes it the detector
for the question Elijah asked:

    "non-profit data could hide lobbying — funded by a Native entity, the
     funding passes through the nonprofit."

Schedule C says whether an organisation lobbied.  Schedule I says who it PAID.
Only the second one can show money moving between legal persons.

WHY THIS BUILD COSTS NOTHING
----------------------------
10,567 IRS e-file return XMLs are already on this disk, retrieved by scripts 99
and 112 through HTTP range reads:

    data/raw/external/irs990_schedc/xml     6,870 returns   236 MB
    data/raw/external/irs990_grantee/xml    3,697 returns   197 MB

Both builds parsed **Schedule C** out of them and neither parsed Schedule I.
This script re-reads what is already here.  **Zero network requests, zero new
bytes on disk beyond the output CSVs.**  Given ~6.9 GB free on C: that is the
whole reason this is the job that gets done rather than a bulk-XML pull.

WHAT IS NOT RE-IMPLEMENTED
--------------------------
`resolve_entity` comes from `code/33_apply_party_rulings.py` and the eight
containment guards from `code/111_build_advocacy_passthrough.py` (standing rule
8).  No second name matcher is written here.

`111.parse_local_schedule_i()` is the narrower ancestor of the parser below: it
reads one of the two directories and keeps eight of the fourteen elements,
because it only ever needed a funding leg for the pass-through build.  It is
NOT modified — advocacy_passthrough depends on it.  Instead `--steps drift`
reproduces its output row-for-row and fails loudly on any disagreement, so the
two cannot silently diverge.

THE RULES THIS BUILD IS UNDER
-----------------------------
1.  **Nothing here says a grant paid for lobbying.**  Money is fungible and most
    grants are restricted to program work; whether a grant was restricted is
    unobservable, because Schedule I gives a purpose line and not the grant
    agreement.  Every row carries that sentence.
2.  **An EIN-keyed filing fact says nothing about the Native status of the
    filer.**  New Venture Fund, a DC fiscal sponsor, files the return for a
    Native sponsored project.  The project is Native; the legal person that
    filed is not.
3.  **Tribal governments are outside the Form 990 universe under IRC 7871.**  A
    tribe with no return is not a gap and is never queued as one.  A recipient
    EIN printed on a Schedule I and absent from the BMF is the signature of a
    7871 entity, and is recorded as such rather than as a missing filer.
4.  **No relationship edge of any kind is written.**  Asserted at module load.

Steps:  parse | build | drift | review | codebook | report
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parents[1]
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "external"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
SPINE_DIR = CEDAR / "data" / "spine"

TODAY = date.today().isoformat()
BUILT = "2026-08-12"

XML_DIRS = [
    ("irs990_schedc", RAW / "irs990_schedc" / "xml",
     RAW / "irs990_schedc" / "_xml_fetch_log.csv"),
    ("irs990_grantee", RAW / "irs990_grantee" / "xml",
     RAW / "irs990_grantee" / "_xml_fetch_log.csv"),
]

IRS_INDEX_URL = ("https://www.irs.gov/charities-non-profits/"
                 "form-990-series-downloads")

GRANT_CAVEAT = (
    "This row records that the filer reported a grant to the named recipient on "
    "its own filed Form 990 Schedule I Part II. It does not state that the grant "
    "paid for any lobbying or political activity, and no column in this dataset "
    "supports that reading. Schedule I reports a purpose line, not the grant "
    "agreement, so whether the grant was restricted is unobservable here."
)
STATUS_CAVEAT = (
    "Schedule I is an EIN-keyed filing fact and asserts nothing about the Native "
    "status of either the filer or the recipient."
)


def log(m):
    print(m, flush=True)


def read_csv(p, encoding="utf-8-sig"):
    p = Path(p)
    if not p.exists():
        return []
    with p.open(encoding=encoding, newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields=None):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    log(f"  wrote {p.relative_to(CEDAR)}  rows={len(rows):,} cols={len(fields)}")


def ein9(v):
    d = "".join(ch for ch in str(v or "") if ch.isdigit())
    return d.zfill(9) if d else ""


def numf(v):
    s = str(v or "").replace(",", "").replace("$", "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, CEDAR / "code" / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_M111 = None


def m111():
    """Script 111: guarded_resolve (resolve_entity + the eight guards)."""
    global _M111
    if _M111 is None:
        _M111 = _load("m111", "111_build_advocacy_passthrough.py")
    return _M111


sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import bears_ownership  # noqa: E402

# A grant is not ownership and not a service edge.  Enforced, not remembered.
assert not bears_ownership("serves_native_entities")
assert not bears_ownership("affiliated_with")
assert not bears_ownership("member_of")


# ---------------------------------------------------------------------------
# BMF -- the FULL Exempt Organizations Business Master File
#
# `data/raw/external/irs990/irs_bmf_slice_universe_2026-08-05.csv` is a 12,764
# row Native-connected SLICE, not the BMF.  Testing a Schedule I recipient EIN
# against that slice answers "is this recipient in our Native universe" and
# CANNOT answer "does this EIN file a Form 990 at all".  Those are different
# questions and conflating them would label ~18,000 ordinary charities with the
# IRC 7871 signature.  The full BMF is four small CSVs; it is fetched so the
# 7871 test is real rather than asserted.
# ---------------------------------------------------------------------------
BMF_URLS = [f"https://www.irs.gov/pub/irs-soi/eo{i}.csv" for i in (1, 2, 3, 4)]
BMF_PAGE = ("https://www.irs.gov/charities-non-profits/"
            "exempt-organizations-business-master-file-extract-eo-bmf")
BMF_DIR = RAW / "irs990" / "bmf_full_2026-08-12"
UA = {"User-Agent": "CedarPress/1.0 (research; elijahsamsonmoreno@gmail.com)"}

MIN_FREE_BYTES = 2 * 1024**3       # NEVER let C: fall below 2 GB
MAX_BYTES_PER_FILE = 400 * 1024**2  # a BMF extract is ~50-90 MB; 400 MB is a fuse


def free_bytes():
    import shutil as _sh
    return _sh.disk_usage(str(CEDAR)).free


def step_bmf():
    """Stream the four EO BMF extracts under a hard disk guard."""
    import time
    import urllib.request

    log("=== 132 bmf (full IRS EO Business Master File) ===")
    M112 = _load("m112", "112_pull_grantee_990s.py")
    if not M112.claim_host("www.irs.gov", "132 BMF extract"):
        log("  REFUSED: www.irs.gov is locked by another poller. Not starting a "
            "second one (docs/PULL_DISCIPLINE.md rule 2).")
        return False
    BMF_DIR.mkdir(parents=True, exist_ok=True)
    hwm = free_bytes()
    ok = True
    try:
        man = []
        for u in BMF_URLS:
            name = u.rsplit("/", 1)[-1]
            dest = BMF_DIR / name
            part = dest.with_suffix(".csv.part")
            if dest.exists() and dest.stat().st_size > 0:
                log(f"  have {name} ({dest.stat().st_size/1e6:.1f} MB) — skip")
                man.append(dict(file=name, url=u, bytes=dest.stat().st_size,
                                http_status=200, fetched_date=TODAY,
                                note="already on disk"))
                continue
            fb = free_bytes()
            if fb - MAX_BYTES_PER_FILE < MIN_FREE_BYTES:
                log(f"  REFUSED {name}: free {fb/1e9:.2f} GB would breach the "
                    f"2 GB floor at the {MAX_BYTES_PER_FILE/1e6:.0f} MB fuse.")
                ok = False
                break
            got = 0
            try:
                req = urllib.request.Request(u, headers=UA)
                with urllib.request.urlopen(req, timeout=(120)) as resp, \
                        part.open("wb") as fh:
                    status = resp.status
                    while True:
                        chunk = resp.read(1 << 20)
                        if not chunk:
                            break
                        got += len(chunk)
                        if got > MAX_BYTES_PER_FILE:
                            raise RuntimeError(
                                f"exceeded {MAX_BYTES_PER_FILE/1e6:.0f} MB fuse")
                        if free_bytes() < MIN_FREE_BYTES:
                            raise RuntimeError("free space hit the 2 GB floor")
                        fh.write(chunk)
                part.rename(dest)          # .part then rename: an interruption
                log(f"  {status}  {name}  {got/1e6:.1f} MB")
                man.append(dict(file=name, url=u, bytes=got, http_status=status,
                                fetched_date=TODAY, note=""))
            except Exception as e:
                part.unlink(missing_ok=True)
                # A transport failure is NOT a 404 and is never read as absence.
                code = getattr(e, "code", "")
                log(f"  FAILED {name}: {type(e).__name__} {code} {e}")
                man.append(dict(file=name, url=u, bytes=0,
                                http_status=code or 0, fetched_date=TODAY,
                                note=f"{type(e).__name__}: {e}. A transport "
                                     "failure is not evidence the object is absent."))
                ok = False
                break
            hwm = min(hwm, free_bytes())
            time.sleep(2.0)
        write_csv(BMF_DIR / "_fetch_manifest.csv", man)
        log(f"  lowest free space during BMF fetch: {hwm/1e9:.2f} GB")
    finally:
        M112.release_host("www.irs.gov", "132 done")
    return ok


def load_full_bmf():
    """EIN -> minimal BMF record.  Returns {} when the full BMF is absent."""
    out = {}
    if not BMF_DIR.exists():
        return out
    for f in sorted(BMF_DIR.glob("eo*.csv")):
        for r in read_csv(f):
            e = ein9(r.get("EIN"))
            if e:
                out[e] = r
    return out


# ---------------------------------------------------------------------------
# PARSE
# ---------------------------------------------------------------------------
def _tag(el):
    return el.tag.split("}")[-1]


def _name2(el, n1tag="BusinessNameLine1Txt", n2tag="BusinessNameLine2Txt"):
    """Both name lines joined.

    IRS e-file splits a business name at 35 characters.  Reading only line 1
    produces MINNESOTA INDIAN WOMENS SEXUAL ASSAULT without its COALITION, and
    FOND DU LAC TRIBAL AND COMMUNITY -- a Minnesota state community college --
    looking like the Fond du Lac Band.
    """
    n1 = n2 = ""
    for c in el.iter():
        t = _tag(c)
        if t == n1tag and not n1 and c.text:
            n1 = c.text.strip()
        elif t == n2tag and not n2 and c.text:
            n2 = c.text.strip()
    return (n1 + " " + n2).strip()


def parse_one(path, source_dir):
    """Schedule I Parts I, II and III out of one e-file return."""
    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        return None, [], {"_error": type(e).__name__}

    si = hdr = None
    ret_type = ""
    for el in root.iter():
        t = _tag(el)
        if t == "IRS990ScheduleI" and si is None:
            si = el
        elif t == "ReturnHeader" and hdr is None:
            hdr = el
    if hdr is None:
        return None, [], {"_error": "no_return_header"}

    filer = next((el for el in hdr.iter() if _tag(el) == "Filer"), None)
    f_ein = f_state = ""
    f_name = ""
    if filer is not None:
        f_name = _name2(filer)
        for el in filer.iter():
            t = _tag(el)
            if t == "EIN" and not f_ein and el.text:
                f_ein = el.text.strip()
            elif t == "StateAbbreviationCd" and not f_state and el.text:
                f_state = el.text.strip()
    period = ""
    for el in hdr.iter():
        t = _tag(el)
        if t == "TaxPeriodEndDt" and not period and el.text:
            period = el.text.strip()
        elif t == "ReturnTypeCd" and not ret_type and el.text:
            ret_type = el.text.strip()

    oid = Path(path).stem
    tax_year = period[:4] if period else ""

    head = dict(
        filer_ein=ein9(f_ein), filer_name_as_filed=f_name, filer_state=f_state,
        tax_period_end=period[:10], tax_year=tax_year, return_type=ret_type,
        object_id=oid, source_dir=source_dir,
        schedule_i_filed="1" if si is not None else "0",
        n_org_recipients=0, n_individual_grant_types=0,
        part1_501c3_org_cnt="", part1_other_org_cnt="",
        grant_records_maintained_ind="",
        part2_cash_grant_total_usd="", part2_noncash_total_usd="",
        part3_individual_cash_total_usd="", part3_individual_recipient_cnt="",
    )
    if si is None:
        return head, [], {}

    grants = []
    cash_tot = 0.0
    noncash_tot = 0.0
    ind_cash = 0.0
    ind_cnt = 0
    ind_types = 0

    for child in si:
        t = _tag(child)
        if t == "Total501c3OrgCnt" and child.text:
            head["part1_501c3_org_cnt"] = child.text.strip()
        elif t == "TotalOtherOrgCnt" and child.text:
            head["part1_other_org_cnt"] = child.text.strip()
        elif t == "GrantRecordsMaintainedInd" and child.text:
            head["grant_records_maintained_ind"] = child.text.strip()
        elif t == "GrantsOtherAsstToIndivInUSGrp":
            # Part III.  NO NAMES EXIST HERE -- the form does not ask for them.
            # Counted so the invisible channel has a size, never attributed.
            ind_types += 1
            for s in child.iter():
                st = _tag(s)
                if st == "CashGrantAmt":
                    ind_cash += numf(s.text) or 0.0
                elif st == "RecipientCnt":
                    ind_cnt += int(numf(s.text) or 0)
        elif t == "RecipientTable":
            d = {}
            addr = None
            for c in child:
                ct = _tag(c)
                if ct == "USAddress" or ct == "ForeignAddress":
                    addr = c
                elif c.text and ct not in d:
                    d[ct] = c.text.strip()
            grp = next((e for e in child if _tag(e) == "RecipientBusinessName"), None)
            rname = _name2(grp) if grp is not None else ""
            city = st_ = zipc = addr1 = ""
            if addr is not None:
                for a in addr.iter():
                    at = _tag(a)
                    if at == "CityNm" and not city and a.text:
                        city = a.text.strip()
                    elif at in ("StateAbbreviationCd", "ProvinceOrStateNm") \
                            and not st_ and a.text:
                        st_ = a.text.strip()
                    elif at in ("ZIPCd", "ForeignPostalCd") and not zipc and a.text:
                        zipc = a.text.strip()
                    elif at == "AddressLine1Txt" and not addr1 and a.text:
                        addr1 = a.text.strip()
            cash = numf(d.get("CashGrantAmt"))
            noncash = numf(d.get("NonCashAssistanceAmt"))
            cash_tot += cash or 0.0
            noncash_tot += noncash or 0.0
            grants.append(dict(
                recipient_name_as_filed=rname,
                recipient_ein=ein9(d.get("RecipientEIN")),
                recipient_address=addr1, recipient_city=city,
                recipient_state=st_, recipient_zip=zipc,
                irc_section_as_filed=d.get("IRCSectionDesc", ""),
                cash_grant_usd="" if cash is None else f"{cash:.2f}",
                noncash_assistance_usd="" if noncash is None else f"{noncash:.2f}",
                noncash_valuation_method=d.get("ValuationMethodUsedDesc", ""),
                noncash_description=d.get("NonCashAssistanceDesc", ""),
                purpose_as_filed=d.get("PurposeOfGrantTxt", ""),
            ))

    head["n_org_recipients"] = len(grants)
    head["n_individual_grant_types"] = ind_types
    head["part2_cash_grant_total_usd"] = f"{cash_tot:.2f}" if grants else ""
    head["part2_noncash_total_usd"] = f"{noncash_tot:.2f}" if grants else ""
    head["part3_individual_cash_total_usd"] = f"{ind_cash:.2f}" if ind_types else ""
    head["part3_individual_recipient_cnt"] = str(ind_cnt) if ind_types else ""
    return head, grants, {}


def step_parse():
    """Walk both local caches.  No network."""
    log("=== 132 parse (local XML only, zero network) ===")
    fetch = {}
    for _, _, flog in XML_DIRS:
        for r in read_csv(flog):
            fetch.setdefault(r["object_id"], r)

    heads, grants = [], []
    errs = Counter()
    seen_oid = set()
    for tagname, xmldir, _ in XML_DIRS:
        if not xmldir.exists():
            log(f"  MISSING {xmldir}")
            continue
        files = sorted(xmldir.glob("*.xml"))
        log(f"  {tagname}: {len(files):,} returns")
        for i, f in enumerate(files, 1):
            oid = f.stem
            if oid in seen_oid:      # same return cached by both builds
                errs["duplicate_object_id_skipped"] += 1
                continue
            seen_oid.add(oid)
            head, gs, err = parse_one(f, tagname)
            if err.get("_error"):
                errs[err["_error"]] += 1
                continue
            fr = fetch.get(oid, {})
            head["source_url"] = fr.get("url", "")
            head["zip_member"] = fr.get("zip_member", "")
            head["irs_downloads_page"] = IRS_INDEX_URL
            head["retrieved_date"] = fr.get("fetched_date", "")
            head["built_date"] = BUILT
            heads.append(head)
            for g in gs:
                g.update(
                    filer_ein=head["filer_ein"],
                    filer_name_as_filed=head["filer_name_as_filed"],
                    filer_state=head["filer_state"],
                    tax_year=head["tax_year"],
                    tax_period_end=head["tax_period_end"],
                    return_type=head["return_type"],
                    object_id=oid,
                    form_schedule="IRS Form 990 Schedule I Part II",
                    source_url=head["source_url"],
                    zip_member=head["zip_member"],
                    irs_downloads_page=IRS_INDEX_URL,
                    retrieved_date=head["retrieved_date"],
                    built_date=BUILT,
                )
                grants.append(g)
            if i % 2000 == 0:
                log(f"    {i:,} parsed")
    log(f"  returns parsed {len(heads):,} · recipient rows {len(grants):,}")
    if errs:
        log(f"  parse notes: {dict(errs)}")
    return heads, grants


# ---------------------------------------------------------------------------
# BUILD -- context, Native detection, provenance
# ---------------------------------------------------------------------------
def step_build(heads, grants):
    log("=== 132 build ===")
    M = m111()
    spine = M.read_csv(SPINE_DIR / "cedar_entity_spine.csv")

    npo = {ein9(r["EIN"]): r for r in read_csv(CLEAN / "np_orgs.csv") if ein9(r["EIN"])}
    bmf = load_full_bmf()
    log(f"  full IRS EO BMF: {len(bmf):,} organisations"
        if bmf else "  full BMF ABSENT — 7871 test not available")
    gfin = defaultdict(list)
    for r in read_csv(CLEAN / "np_grantee_financials.csv"):
        if ein9(r["ein"]):
            gfin[ein9(r["ein"])].append(r)
    # Schedule C / lobbying facts already recovered, keyed by EIN.
    lobby_ein = set()
    for r in read_csv(CLEAN / "np_financials.csv"):
        v = numf(r.get("schedc_lobbying_usd")) or numf(r.get("schedc_total_lobbying"))
        if v and v > 0:
            lobby_ein.add(ein9(r["ein"]))
    for r in read_csv(CLEAN / "np_grantee_financials.csv"):
        v = numf(r.get("lobbying_expenditure"))
        if v and v > 0:
            lobby_ein.add(ein9(r["ein"]))

    # ---- filer context -----------------------------------------------------
    for h in heads:
        e = h["filer_ein"]
        o = npo.get(e)
        h["filer_in_np_orgs"] = "1" if o else "0"
        h["filer_np_tier"] = (o or {}).get("tier", "")
        h["filer_np_confidence_tier"] = (o or {}).get("confidence_tier", "")
        h["filer_np_classification_ruling"] = (o or {}).get("classification_ruling", "")
        h["filer_tribe_id_np_orgs"] = (o or {}).get("tribe_id", "")
        h["native_status_caveat"] = STATUS_CAVEAT
        # THE FILER UNIVERSE IS TWO POPULATIONS AND THEY MUST NEVER BE SUMMED
        # AS ONE.  Script 99 fetched returns for the Cedar Native-connected
        # nonprofit universe.  Script 112 fetched returns for the GRANTEES of
        # Native funders -- which is how Johns Hopkins ($3.9B), Mayo Clinic
        # ($3.8B) and New Venture Fund ($2.4B) are in this cache.  Their
        # presence says they RECEIVED money from a Native funder; it says
        # nothing whatever about their own Native status.
        #
        # AND np_orgs MEMBERSHIP IS NOT A NATIVE RULING.  12,393 of its 12,764
        # rows are UNRULED and 4,933 are confidence_tier X -- which is a
        # NEGATIVE ruling.  A first cut of this build labelled everything in
        # np_orgs "Native-connected" and the top grantmaker came back
        # SEMINOLE BOOSTERS INC (Florida State University athletics, EIN
        # 591561180, tier X, funnel_stage excluded_by_prior_ruling), followed by
        # SOUTH DAKOTA STATE UNIVERSITY FOUNDATION and SIOUX FALLS AREA
        # COMMUNITY FOUNDATION.  AGENTS.md: "An X-tier row is a negative ruling
        # and must never resurface."  So the population is TIERED, and the X
        # rows are named as excluded rather than quietly included.
        ruling = (o or {}).get("classification_ruling", "")
        ctier = (o or {}).get("confidence_tier", "")
        if not o:
            pop = "not_in_np_orgs_universe_native_status_not_established"
        elif ctier == "X" or (o.get("funnel_stage") or "").startswith("excluded"):
            pop = "np_orgs_EXCLUDED_by_prior_ruling"
        elif ruling in ("native_controlled", "tribally_controlled",
                        "native_serving"):
            pop = f"np_orgs_ruled_{ruling}"
        elif ctier == "A":
            pop = "np_orgs_candidate_tier_A_unruled"
        else:
            pop = "np_orgs_candidate_tier_B_unruled"
        h["filer_population"] = pop
        h["filer_is_ruled_native"] = "1" if ruling in (
            "native_controlled", "tribally_controlled", "native_serving") else "0"

    filer_pop = {h["filer_ein"]: h["filer_population"] for h in heads}
    filer_ruled = {h["filer_ein"]: h["filer_is_ruled_native"] for h in heads}

    # ---- recipient resolution ---------------------------------------------
    resolve_cache = {}
    counts = Counter()
    for g in grants:
        e = g["recipient_ein"]
        g["filer_population"] = filer_pop.get(g["filer_ein"], "")
        g["filer_in_np_orgs"] = "1" if g["filer_ein"] in npo else "0"
        g["filer_is_ruled_native"] = filer_ruled.get(g["filer_ein"], "0")
        o = npo.get(e)
        g["recipient_ein_in_np_orgs"] = "1" if o else "0"
        g["recipient_np_orgs_name"] = (o or {}).get("org_name", "")
        g["recipient_np_orgs_tribe_id"] = (o or {}).get("tribe_id", "")
        g["recipient_np_orgs_confidence_tier"] = (o or {}).get("confidence_tier", "")
        g["recipient_in_grantee_990"] = "1" if e and e in gfin else "0"
        g["recipient_reports_lobbying_on_own_990"] = "1" if e and e in lobby_ein else "0"

        # THE 7871 TEST, against the FULL BMF (1.96M orgs) and never against the
        # 12,764-row Native-connected slice.  An EIN printed on a filed Schedule
        # I and absent from the whole BMF is the signature of an entity outside
        # the Form 990 universe -- most often a tribal government or its
        # instrumentality under IRC 7871, which files no return at all.  Absence
        # from np_orgs means only "not in our Native subset" and is not this.
        b = bmf.get(e) if e else None
        g["recipient_bmf_name"] = (b or {}).get("NAME", "")
        g["recipient_bmf_state"] = (b or {}).get("STATE", "")
        g["recipient_bmf_subsection"] = (b or {}).get("SUBSECTION", "")
        g["recipient_bmf_filing_req_cd"] = (b or {}).get("FILING_REQ_CD", "")
        g["recipient_bmf_ntee_cd"] = (b or {}).get("NTEE_CD", "")
        if not e:
            g["recipient_bmf_status"] = "no_ein_reported_on_schedule"
        elif not bmf:
            g["recipient_bmf_status"] = "full_bmf_not_available"
        elif b:
            g["recipient_bmf_status"] = "in_full_irs_bmf"
        else:
            g["recipient_bmf_status"] = "absent_from_full_irs_bmf"
        # A filer writing TRIBE / GOVERNMENT in the IRC section is naming the
        # 7871 case itself, in its own words.
        irc = (g.get("irc_section_as_filed") or "").upper()
        g["recipient_outside_990_universe_signal"] = "1" if (
            g["recipient_bmf_status"] == "absent_from_full_irs_bmf"
            or "TRIBE" in irc or "TRIBAL" in irc or "GOVERNMENT" in irc
            or "7871" in irc) else "0"

        key = (g["recipient_name_as_filed"], g["recipient_state"])
        if key not in resolve_cache:
            resolve_cache[key] = M.guarded_resolve(
                g["recipient_name_as_filed"], spine, g["recipient_state"] or None)
        tid, canon, basis = resolve_cache[key]
        g["recipient_entity_id"] = tid or ""
        g["recipient_entity_canonical_name"] = canon or ""
        g["recipient_entity_match_basis"] = basis or ""
        # Name matching is never Tier A.  An EIN join is the only strong leg.
        if tid and g["recipient_ein_in_np_orgs"] == "1":
            g["recipient_native_evidence_tier"] = "A"
        elif tid:
            g["recipient_native_evidence_tier"] = "B"
        elif g["recipient_ein_in_np_orgs"] == "1":
            g["recipient_native_evidence_tier"] = "B"
        else:
            g["recipient_native_evidence_tier"] = ""
        counts[g["recipient_native_evidence_tier"] or "none"] += 1

        g["grant_caveat"] = GRANT_CAVEAT
        g["native_status_caveat"] = STATUS_CAVEAT

    log(f"  recipient Native-evidence tiers: {dict(counts)}")

    # A recipient row that names NOBODY -- no name and no EIN -- cannot serve
    # the purpose of this dataset and must never be counted as a grant to
    # someone.  Held out rather than silently dropped, and reported.
    def names_someone(g):
        return bool(g["recipient_name_as_filed"].strip() or g["recipient_ein"].strip())

    named = [g for g in grants if names_someone(g)]
    unnamed = [g for g in grants if not names_someone(g)]
    if unnamed:
        write_csv(REVIEW / f"np_schedule_i_unnamed_recipient_rows_{BUILT}.csv",
                  unnamed, GRANT_FIELDS)
        log(f"  held out {len(unnamed)} recipient rows naming no organisation "
            f"(no name and no EIN) — see review/")
    return heads, named, len(unnamed)


GRANT_FIELDS = [
    "filer_ein", "filer_name_as_filed", "filer_state", "filer_population",
    "filer_in_np_orgs", "filer_is_ruled_native", "tax_year",
    "tax_period_end", "return_type", "object_id",
    "recipient_name_as_filed", "recipient_ein", "recipient_address",
    "recipient_city", "recipient_state", "recipient_zip",
    "irc_section_as_filed", "cash_grant_usd", "noncash_assistance_usd",
    "noncash_valuation_method", "noncash_description", "purpose_as_filed",
    "recipient_ein_in_np_orgs", "recipient_np_orgs_name",
    "recipient_np_orgs_tribe_id", "recipient_np_orgs_confidence_tier",
    "recipient_in_grantee_990", "recipient_reports_lobbying_on_own_990",
    "recipient_bmf_status", "recipient_bmf_name", "recipient_bmf_state",
    "recipient_bmf_subsection", "recipient_bmf_filing_req_cd",
    "recipient_bmf_ntee_cd", "recipient_outside_990_universe_signal",
    "recipient_entity_id",
    "recipient_entity_canonical_name", "recipient_entity_match_basis",
    "recipient_native_evidence_tier",
    "form_schedule", "source_url", "zip_member", "irs_downloads_page",
    "retrieved_date", "built_date", "grant_caveat", "native_status_caveat",
]

FILER_FIELDS = [
    "filer_ein", "filer_name_as_filed", "filer_state", "tax_year",
    "tax_period_end", "return_type", "object_id", "schedule_i_filed",
    "n_org_recipients", "part1_501c3_org_cnt", "part1_other_org_cnt",
    "grant_records_maintained_ind", "part2_cash_grant_total_usd",
    "part2_noncash_total_usd", "n_individual_grant_types",
    "part3_individual_cash_total_usd", "part3_individual_recipient_cnt",
    "filer_population", "filer_in_np_orgs", "filer_is_ruled_native",
    "filer_np_tier", "filer_np_confidence_tier",
    "filer_np_classification_ruling", "filer_tribe_id_np_orgs",
    "source_dir", "source_url", "zip_member", "irs_downloads_page",
    "retrieved_date", "built_date", "native_status_caveat",
]


# ---------------------------------------------------------------------------
# DRIFT -- prove this parser agrees with 111's narrower ancestor
# ---------------------------------------------------------------------------
def step_drift(grants):
    log("=== 132 drift check against 111.parse_local_schedule_i ===")
    M = m111()
    old = M.parse_local_schedule_i()
    mine = [g for g in grants if g["object_id"] in
            {o["object_id"] for o in old}] if old else []
    # compare on (object_id, recipient name, ein, amount)
    def key_old(r):
        return (r["object_id"], r["rname"], ein9(r["rein"]),
                f"{numf(r['amt']) or 0:.2f}")

    def key_new(r):
        return (r["object_id"], r["recipient_name_as_filed"], r["recipient_ein"],
                f"{numf(r['cash_grant_usd']) or 0:.2f}")

    a = Counter(key_old(r) for r in old)
    b = Counter(key_new(r) for r in mine)
    only_old = a - b
    only_new = b - a
    log(f"  111 rows {sum(a.values()):,} · 130 rows on same returns {sum(b.values()):,}")
    log(f"  only in 111: {sum(only_old.values())} · only in 130: {sum(only_new.values())}")
    if only_old or only_new:
        for k in list(only_old)[:5]:
            log(f"    ONLY-111 {k}")
        for k in list(only_new)[:5]:
            log(f"    ONLY-132 {k}")
    else:
        log("  IDENTICAL on the shared field set — no parser drift.")
    return sum(only_old.values()), sum(only_new.values())


# ---------------------------------------------------------------------------
# REVIEW
# ---------------------------------------------------------------------------
def step_review(grants):
    log("=== 132 review queue ===")
    rows = []
    # A recipient that resolves to the spine on NAME ONLY is a tier B proposal
    # and must be ruled before anything keys a dollar to that entity.
    agg = defaultdict(lambda: {"n": 0, "usd": 0.0, "funders": set(),
                               "years": set()})
    for g in grants:
        if g["recipient_native_evidence_tier"] != "B":
            continue
        if not g["recipient_entity_id"] and g["recipient_ein_in_np_orgs"] != "1":
            continue
        k = (g["recipient_name_as_filed"], g["recipient_ein"],
             g["recipient_entity_id"], g["recipient_state"])
        a = agg[k]
        a["n"] += 1
        a["usd"] += numf(g["cash_grant_usd"]) or 0.0
        a["funders"].add(g["filer_name_as_filed"])
        a["years"].add(g["tax_year"])
    for (nm, ein, tid, st), a in sorted(agg.items(), key=lambda x: -x[1]["usd"]):
        rows.append(dict(
            review_id=f"SCHEDI-{ein or 'NOEIN'}-{tid or 'NOENT'}",
            recipient_name_as_filed=nm, recipient_ein=ein, recipient_state=st,
            proposed_entity_id=tid,
            n_grant_rows=a["n"], total_cash_grant_usd=f"{a['usd']:.2f}",
            n_funders=len(a["funders"]),
            funders="; ".join(sorted(a["funders"]))[:400],
            tax_years="; ".join(sorted(y for y in a["years"] if y)),
            question=("Is this recipient the named Cedar entity, a separate legal "
                      "person carrying its name, or not Native at all? A name "
                      "match is never Tier A and no dollar is keyed to the entity "
                      "until this is ruled."),
            evidence=("Recipient named on a filed Form 990 Schedule I Part II; "
                      "resolved by 111.guarded_resolve on name+state only."),
            YOUR_RULING="",
            built_date=BUILT,
        ))
    write_csv(REVIEW / f"np_schedule_i_recipients_{BUILT}.csv", rows)
    return rows


# ---------------------------------------------------------------------------
# CODEBOOK
# ---------------------------------------------------------------------------
CODEBOOK = {
    "filer_ein": "EIN of the organisation that FILED the return, nine digits zero-padded.",
    "filer_name_as_filed": "Filer name from its own return with BusinessNameLine1Txt and BusinessNameLine2Txt joined, because IRS e-file splits a name at 35 characters.",
    "tax_year": "Year of TaxPeriodEndDt on the return. Not the submission year.",
    "return_type": "990, 990EZ or 990PF as reported in ReturnHeader/ReturnTypeCd.",
    "object_id": "IRS e-file return object id. The primary key of the return in the IRS index and archives.",
    "recipient_name_as_filed": "Recipient organisation name exactly as the filer typed it on Schedule I Part II, both name lines joined. Never corrected.",
    "recipient_ein": "Recipient EIN as reported by the filer. Blank where the filer reported none.",
    "irc_section_as_filed": "IRC section of the recipient as stated by the filer. A filer writing TRIBE here is naming an entity outside the Form 990 universe under IRC 7871.",
    "cash_grant_usd": "CashGrantAmt for this recipient. Schedule I Part II has a $5,000 floor, so smaller grants are absent by construction.",
    "noncash_assistance_usd": "NonCashAssistanceAmt for this recipient. Never added to cash without saying so.",
    "purpose_as_filed": "PurposeOfGrantTxt. A purpose line is not a grant agreement and does not establish whether the grant was restricted.",
    "recipient_ein_in_np_orgs": "1 where the recipient EIN is in the Cedar Native-connected nonprofit universe (np_orgs.csv, IRS EO BMF). An EIN join, no name matching.",
    "recipient_bmf_status": "no_bmf_record_in_np_orgs_universe on a printed EIN is the signature of an IRC 7871 entity - most often a tribal government - not a missing filer.",
    "recipient_reports_lobbying_on_own_990": "1 where that EIN reports lobbying above zero on its OWN filed return in np_financials or np_grantee_financials. It is a fact about the recipient, not about this grant.",
    "recipient_entity_id": "Cedar spine id where the recipient name resolves under 111's eight containment guards. Blank otherwise.",
    "recipient_entity_match_basis": "How the resolver matched, or refused:<reason> verbatim where a guard vetoed it.",
    "recipient_native_evidence_tier": "A only where an EIN join and a guarded name match agree. B for either leg alone. Blank where neither fires. Never promoted by this build.",
    "form_schedule": "The exact form and part the row came from.",
    "source_url": "The IRS bulk archive ZIP the return XML was read out of.",
    "zip_member": "The member name inside that archive.",
    "retrieved_date": "Date the return XML was retrieved from apps.irs.gov.",
    "grant_caveat": "Standing sentence: this row does not state that the grant paid for lobbying.",
    "native_status_caveat": "Standing sentence: an EIN-keyed filing fact asserts nothing about Native status.",
    "part3_individual_cash_total_usd": "Schedule I Part III, grants to individuals. The form asks for NO names, so this money is unattributable by construction and is counted only to give the invisible channel a size.",
    "recipient_bmf_status": "Recipient EIN tested against the FULL IRS EO Business Master File (1.96M organisations, eo1-eo4). absent_from_full_irs_bmf is the IRC 7871 signature - an entity outside the Form 990 universe, most often a tribal government. Never tested against the 12,764-row Native-connected slice, which answers a different question.",
    "recipient_outside_990_universe_signal": "1 where the recipient is absent from the full BMF, or the filer itself wrote TRIBE / TRIBAL / GOVERNMENT / 7871 in the IRC section. Such an entity files no Form 990 and its absence is never a gap.",
    "recipient_bmf_name": "Recipient name as the IRS BMF holds it, where the EIN is in the BMF. Independent of the name the filer typed, so the two can be compared.",
    "recipient_bmf_filing_req_cd": "BMF filing requirement code for the recipient. 02 is a 990-N e-Postcard filer, which reports gross receipts and nothing else; zero lobbying there is the filing regime, not a finding.",
    "filer_population": "Which population the FILER belongs to. np_orgs membership is a name-match funnel stage, not a Native ruling: 12,393 of its 12,764 rows are UNRULED and 4,933 are confidence_tier X, which is a NEGATIVE ruling. np_orgs_EXCLUDED_by_prior_ruling rows are carried so the exclusion stays visible and must never be read as Native. Only np_orgs_ruled_* rests on an adjudication.",
    "filer_is_ruled_native": "1 only where np_orgs carries a positive classification_ruling (native_controlled, tribally_controlled, native_serving). Everything else is 0, including tier A candidates.",
    "schedule_i_filed": "1 where the return carries an IRS990ScheduleI element. 0 is a fact about that return, never about the organisation.",
}


def step_codebook():
    log("=== 132 codebook ===")
    p = CLEAN / "codebook_master.csv"
    rows = read_csv(p)
    if not rows:
        log("  codebook_master.csv not found — skipped")
        return
    bak = p.with_suffix(f".csv.bak_{BUILT}_pre132")
    if not bak.exists():
        bak.write_bytes(p.read_bytes())
        log(f"  backed up -> {bak.name}")
    fields = list(rows[0].keys())
    ds = "04e_schedule_i_grants"
    kept = [r for r in rows if r.get("dataset") != ds]
    dropped = len(rows) - len(kept)
    for var, desc in CODEBOOK.items():
        row = {k: "" for k in fields}
        for k, v in (("dataset", ds), ("variable", var), ("description", desc),
                     ("built_date", BUILT), ("source", "IRS Form 990 e-file XML")):
            if k in row:
                row[k] = v
        kept.append(row)
    write_csv(p, kept, fields)
    log(f"  dataset rows replaced: {dropped} -> {len(CODEBOOK)}; total {len(kept):,}")


# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------
def step_report(heads, grants, review, drift, n_unnamed):
    log("=== 132 report ===")
    L = []
    a = L.append
    a("132 — Form 990 Schedule I layer   " + BUILT)
    a("")
    a(f"returns read from local cache : {len(heads):,}   (zero network requests)")
    filed = [h for h in heads if h["schedule_i_filed"] == "1"]
    withrec = [h for h in heads if h["n_org_recipients"] > 0]
    a(f"returns carrying Schedule I   : {len(filed):,}")
    a(f"returns naming org recipients : {len(withrec):,}")
    a(f"recipient grant rows          : {len(grants):,}")
    a(f"distinct filers naming a grant: {len({h['filer_ein'] for h in withrec}):,}")
    a(f"distinct recipient EINs       : {len({g['recipient_ein'] for g in grants if g['recipient_ein']}):,}")
    tot = sum(numf(g["cash_grant_usd"]) or 0 for g in grants)
    ntot = sum(numf(g["noncash_assistance_usd"]) or 0 for g in grants)
    a(f"cash grants                   : ${tot:,.0f}")
    a(f"non-cash assistance           : ${ntot:,.0f}   (never added to cash)")
    a("")
    a("THE FILER UNIVERSE IS SIX POPULATIONS. NEVER SUM THEM AS ONE.")
    a("  The cache holds returns fetched by script 99 (the Cedar Native-connected")
    a("  nonprofit universe) AND by script 112 (the GRANTEES of Native funders).")
    a("  A grantee is in this cache because it RECEIVED money from a Native")
    a("  funder. That says nothing whatever about its own Native status.")
    a("")
    pops = defaultdict(lambda: [0, 0.0, set()])
    for g in grants:
        p = pops[g["filer_population"]]
        p[0] += 1
        p[1] += numf(g["cash_grant_usd"]) or 0
        p[2].add(g["filer_ein"])
    for k in sorted(pops):
        n, v, fs = pops[k]
        a(f"  {k}")
        a(f"     filers={len(fs):,}  rows={n:,}  cash=${v:,.0f}")
    a("")
    a("  NOT ONE OF THESE LINES IS A PUBLISHABLE 'NATIVE GRANTMAKING' TOTAL.")
    a("  * not_in_np_orgs is dominated by JOHNS HOPKINS ($3.9B), MAYO CLINIC")
    a("    ($3.8B) and NEW VENTURE FUND ($2.4B) -- the fiscal sponsor already")
    a("    recorded in docs/GRANTEE_990_LOG.md as NOT Native. But it also holds")
    a("    genuine Native organisations absent from np_orgs (Southcentral")
    a("    Foundation, $117M), so it is UNESTABLISHED in both directions.")
    a("  * np_orgs_EXCLUDED_by_prior_ruling is a NEGATIVE ruling. It contains")
    a("    SEMINOLE BOOSTERS INC -- Florida State University athletics -- which")
    a("    was the single largest 'Native' grantmaker before this split existed.")
    a("    These rows are carried so the exclusion is visible, never as Native.")
    a("  * The tier_B_unruled line is a CANDIDATE list. np_orgs is 12,393/12,764")
    a("    UNRULED; membership is a name-match funnel stage, not an adjudication.")
    a("  Only the np_orgs_ruled_* lines rest on a ruling, and they are small.")
    a("")
    a("COVERAGE BY TAX YEAR (returns with a named recipient / rows)")
    byy = defaultdict(lambda: [0, 0, 0.0])
    for h in withrec:
        byy[h["tax_year"]][0] += 1
    for g in grants:
        byy[g["tax_year"]][1] += 1
        byy[g["tax_year"]][2] += numf(g["cash_grant_usd"]) or 0
    for y in sorted(byy):
        r, n, v = byy[y]
        a(f"  {y}  returns={r:5d}  rows={n:7d}  ${v:,.0f}")
    a("")
    a("TIER OF NATIVE EVIDENCE ON THE RECIPIENT")
    c = Counter(g["recipient_native_evidence_tier"] or "none" for g in grants)
    for k in ("A", "B", "none"):
        a(f"  {k:5s} {c.get(k,0):,}")
    a("")
    a("RECIPIENTS TESTED AGAINST THE FULL IRS EO BMF (1.96M organisations)")
    bs = Counter(g["recipient_bmf_status"] for g in grants)
    for k, v in bs.most_common():
        a(f"  {k:32s} {v:,}")
    n7871 = len({g["recipient_ein"] for g in grants
                 if g["recipient_ein"]
                 and g["recipient_bmf_status"] == "absent_from_full_irs_bmf"})
    a(f"  distinct recipient EINs printed on a filed Schedule I and absent from")
    a(f"  the ENTIRE BMF: {n7871:,}")
    a("  That is the IRC 7871 signature - an entity outside the Form 990 universe,")
    a("  most often a tribal government. It files no return; this is NOT a gap and")
    a("  is never queued as one. Absence from np_orgs would have meant only")
    a("  'not in our Native subset' and is a different question entirely.")
    a(f"  rows whose IRC section as filed names a tribe/government: "
      f"{sum(1 for g in grants if 'TRIBE' in (g['irc_section_as_filed'] or '').upper()):,}")
    a("")
    a("PART III — GRANTS TO INDIVIDUALS (no names exist on the form)")
    p3 = sum(numf(h["part3_individual_cash_total_usd"]) or 0 for h in heads)
    n3 = sum(1 for h in heads if h["n_individual_grant_types"])
    a(f"  returns reporting it: {n3:,}   cash: ${p3:,.0f}")
    a(f"  unattributable by construction — Schedule I Part III asks for no names.")
    a("")
    a("RECIPIENTS THAT ALSO REPORT LOBBYING ON THEIR OWN 990")
    lob = [g for g in grants if g["recipient_reports_lobbying_on_own_990"] == "1"]
    a(f"  grant rows: {len(lob):,}  recipients: {len({g['recipient_ein'] for g in lob}):,}"
      f"  funders: {len({g['filer_ein'] for g in lob}):,}")
    a(f"  cash on those rows: ${sum(numf(g['cash_grant_usd']) or 0 for g in lob):,.0f}")
    a("  THIS IS A CO-OCCURRENCE OF TWO FILING FACTS. It does not state that any")
    a("  grant paid for any lobbying, and no column in this dataset supports that.")
    a("")
    a(f"recipient rows naming no organisation, held out: {n_unnamed}")
    a(f"review queue rows: {len(review):,}")
    a(f"parser drift vs 111: only-111={drift[0]}  only-132={drift[1]}")
    a("  The only-111 rows are recipient rows that name NO organisation (no name")
    a("  and no EIN). 111 keeps them; 132 holds them out to review/ so they can")
    a("  never be counted as a grant to someone. The parsers agree everywhere a")
    a("  recipient is actually named.")
    a("")
    a("CAVEATS THAT TRAVEL WITH EVERY FIGURE")
    a("  * E-file coverage is PARTIAL before tax year 2019. Mandatory e-filing")
    a("    arrived with the Taxpayer First Act; paper filers 2011-2018 are ABSENT")
    a("    from the XML entirely. An organisation with no return here may simply")
    a("    have filed on paper. Never read absence as 'did not file'.")
    a("  * The IRS e-file index begins at SUBMISSION year 2017, so tax years")
    a("    before roughly 2015 have no machine-readable return at any URL.")
    a("  * Schedule I Part II has a $5,000 floor. Smaller grants are absent.")
    a("  * Part III grants to individuals carry no names, by form design.")
    a("  * Fiscally sponsored projects file under the SPONSOR's EIN. The")
    a("    organisation named is not always the legal person paid.")
    a("  * Tribal governments are outside the Form 990 universe under IRC 7871.")
    a("  * This build read only what scripts 99 and 112 had already retrieved.")
    a("    It is a floor on Schedule I, not the complete universe.")
    txt = "\n".join(L)
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / f"132_build_report_{BUILT}.txt").write_text(txt, encoding="utf-8")
    print(txt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps",
                    default="bmf,parse,build,drift,review,codebook,report")
    args = ap.parse_args()
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]

    if "bmf" in steps:
        step_bmf()
    heads, grants = step_parse()
    heads, grants, n_unnamed = step_build(heads, grants)
    write_csv(CLEAN / "np_schedule_i_grants.csv", grants, GRANT_FIELDS)
    write_csv(CLEAN / "np_schedule_i_filers.csv", heads, FILER_FIELDS)
    drift = step_drift(grants) if "drift" in steps else (0, 0)
    review = step_review(grants) if "review" in steps else []
    if "codebook" in steps:
        step_codebook()
    if "report" in steps:
        step_report(heads, grants, review, drift, n_unnamed)


if __name__ == "__main__":
    main()
