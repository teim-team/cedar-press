#!/usr/bin/env python3
"""
23d_build_gaming_facilities.py -- Cedar Press Gaming dataset, Phase 1 Step D.

Builds the DIRECTORY CORE from the local copies staged by 23c:

    data/clean/gaming_facilities.csv         one row per facility
    data/clean/gaming_facility_metrics.csv   one row per quantity OBSERVATION

WHY TWO FILES. Stage discipline is the design. A facility does not have "a slot
count" -- it has a slot count as observed by a named source on a named date at a
named stage. Casino City Press published 43 waves between 2001-09 and 2023-01,
and 466 of those observations are of properties it lists as Planned or Under
Construction -- proposal-stage numbers that must never be quoted as facility
facts. gaming_facility_metrics.csv keeps every observation with its own
observation_status, date and value_basis. gaming_facilities.csv is the
convenience row: identity plus the LATEST observation, each field still carrying
its basis and its observation date.

VALUE_BASIS VOCABULARY (on every numeric field, no exceptions):
  reported          the source publishes this exact quantity
                    (Casino City capacity; CT slot win; source-archived state
                    payment amounts)
  payments_derived  a revenue figure obtained by inverting a compact rate on a
                    payment that IS source-archived and verified
                    (OK exclusivity fee /0.05; CT slot contribution /0.25)
  reverse_engineered a revenue figure obtained by inverting a rate on a payment
                    that is hand-written and NOT source-verified
                    (MI /0.02, OR /0.06, NY /0.25, OK compact share, WA, WI)
  modelled          IMPLAN output, or a direct estimate not published by the
                    operator or a regulator (MIGA self-reported estimates;
                    Seminole Hollywood/Tampa industry estimates)

THE TRAP THIS FILE AVOIDS. per_property_gaming_revenue_FINAL_v3_audited.csv
labels 435 of 512 rows `tier2A_agent_verified_real`. That label certifies the
PAYMENT was verified against an archived source document; it does NOT mean the
revenue figure was reported. 372 of those 435 rows are rate inversions. Cedar
Press therefore derives value_basis from the metric, never from that tier.

REVENUE IS NOT PUT ON THE FACILITY ROW. The property-name join between the
revenue panel and the address file matches 0.8% of rows -- the revenue panel's
"properties" are overwhelmingly tribes. Revenue and payment observations
therefore live in gaming_facility_metrics.csv at entity_level='tribe', and a
facility row never carries a dollar figure it cannot legitimately claim.

MATCHING IS CONSERVATIVE. Cross-source facility matching is exact-on-normalized
(name, state) only. Near matches are NOT made; unmatched records become their own
rows carrying duplicate_risk=1. Per the project rule: a missing link is
recoverable, a false one is not.

entity_id is left BLANK. Spine linking is a separate, ruled step.
"""
import os, re, csv, io, sys, math, collections, datetime, unicodedata, warnings
warnings.filterwarnings("ignore")
import pandas as pd
from pathlib import Path

BASE  = str(Path(__file__).resolve().parent.parent)
SRC   = os.path.join(BASE, "data", "raw", "external", "gaming", "directory_core")
CLEAN = os.path.join(BASE, "data", "clean")
FETCHED = "2026-08-05"

buf = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")

def norm(s):
    if s is None or (isinstance(s, float) and math.isnan(s)): return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", " ", s).lower().strip()
    return re.sub(r"\s+", " ", s)

def s(v):
    """Scalar -> clean string; NaN/None -> ''."""
    if v is None: return ""
    if isinstance(v, float) and math.isnan(v): return ""
    v = str(v).strip()
    return "" if v.lower() in ("nan", "nat", "none") else v

STATE_ABBR = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA",
 "Colorado":"CO","Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA","Idaho":"ID",
 "Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA",
 "Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN",
 "Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV",
 "New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY",
 "North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR",
 "Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD",
 "Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA",
 "Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}
def st(v):
    v = s(v)
    if len(v) == 2: return v.upper()
    return STATE_ABBR.get(v.title(), v.upper()[:2] if v else "")

def ccp_date(v):
    """Casino City stores dates as '31mar2016'. Deterministic parse; anything
    that does not match the format is returned verbatim rather than guessed."""
    v = s(v)
    if not v: return ""
    try: return datetime.datetime.strptime(v, "%d%b%Y").date().isoformat()
    except ValueError: return v

# ===========================================================================
# 1. Casino City Press panel -- the capacity backbone
# ===========================================================================
CAP = [  # (source column, cedar metric, unit)
 ("slots",                   "gaming_machines",        "machines"),
 ("tablegames",              "table_games",            "tables"),
 ("pokertables",             "poker_tables",           "tables"),
 ("bingoseats",              "bingo_seats",            "seats"),
 ("casinosquarefootage",     "gaming_square_feet",     "sq_ft"),
 ("conventionsquarefootage", "convention_square_feet", "sq_ft"),
 ("rooms",                   "hotel_rooms",            "rooms"),
 ("parkingspaces",           "parking_spaces",         "spaces"),
 ("employees",               "employees",              "persons"),
 ("restaurants",             "restaurants",            "outlets"),
]
# Casino City property status -> Cedar observation_status. The literal source
# value travels alongside in source_status_literal on every row.
STAGE = {"Planned": "proposed", "Under Construction": "approved",
         "Open": "current", "Temporarily Closed": "current"}

ccp = pd.read_stata(os.path.join(SRC, "tribal_casino_panel.dta"),
                    convert_categoricals=False)
log(f"Casino City panel loaded            : {len(ccp):,} obs, "
    f"{ccp['propertyid'].nunique()} properties, "
    f"{ccp['datadate'].min().date()} .. {ccp['datadate'].max().date()}")

metrics = []
CCP_SRC = "Casino City Press gaming-property panel (tribal_casino_panel.dta)"
CCP_NOTE = ("published capacity figure; the source stores integer 0 for missing, "
            "so 0 is emitted as no observation, never as a zero count")

for r in ccp.itertuples(index=False):
    pid = s(r.propertyid)
    if not pid: continue
    dd = r.datadate.date().isoformat() if pd.notna(r.datadate) else ""
    lit = s(r.propertystatus)
    stage = STAGE.get(lit, "")
    for col, metric, unit in CAP:
        v = getattr(r, col, None)
        if v is None or (isinstance(v, float) and math.isnan(v)): continue
        try: v = float(v)
        except (TypeError, ValueError): continue
        if v <= 0: continue                     # 0 == missing at source
        metrics.append(dict(
            facility_id="CCP-" + pid, entity_id="", entity_level="facility",
            tribe=s(r.tribename), facility_name=s(r.gamingpropertyname),
            state=st(r.state), metric=metric, measure_type="capacity",
            value=int(v) if float(v).is_integer() else v, unit=unit,
            observation_date=dd, observation_period="",
            observation_status=stage or "unknown",
            source_status_literal=lit,
            value_basis="reported",
            value_verification="published_by_source",
            value_basis_detail=CCP_NOTE,
            source=CCP_SRC, source_file="tribal_casino_panel.dta",
            fetched_date=FETCHED))

log(f"Casino City capacity observations   : {len(metrics):,}")

# ---- facility identity + latest observation, per property
ccp_sorted = ccp.sort_values("datadate")
facilities = {}
for r in ccp_sorted.itertuples(index=False):
    pid = s(r.propertyid)
    if not pid: continue
    fid = "CCP-" + pid
    f = facilities.setdefault(fid, dict(
        facility_id=fid, entity_id="", tribe="", facility_name="", company="",
        address="", city="", state="", postal_code="", latitude="", longitude="",
        coords_basis="", property_status="", property_status_literal="",
        property_status_observed_date="", observation_status="",
        open_date="", open_date_basis="", open_date_source_url="",
        close_date="", close_date_basis="", close_date_source_url="",
        casino_city_id=pid, n_capacity_observations=0,
        first_observed_date="", last_observed_date="",
        source_datasets="casino_city_press", match_status="", match_basis="",
        duplicate_risk=0, native_american_flag="", property_type="",
        fetched_date=FETCHED))
    dd = r.datadate.date().isoformat() if pd.notna(r.datadate) else ""
    if not f["first_observed_date"]: f["first_observed_date"] = dd
    f["last_observed_date"] = dd
    f["n_capacity_observations"] += 1
    # latest non-empty wins (rows are in ascending datadate order)
    for k, v in (("tribe", r.tribename), ("facility_name", r.gamingpropertyname),
                 ("company", r.company), ("address", r.address), ("city", r.city),
                 ("postal_code", r.postalcode), ("native_american_flag", r.nativeamerican),
                 ("property_type", r.propertytype)):
        if s(v): f[k] = s(v)
    if s(r.state): f["state"] = st(r.state)
    if s(r.latitude) and s(r.longitude):
        f["latitude"], f["longitude"] = s(r.latitude), s(r.longitude)
        f["coords_basis"] = ("Casino City Press coordinates; locationprecision="
                             + (s(r.locationprecision) or "not stated"))
    if s(r.propertystatus):
        f["property_status_literal"] = s(r.propertystatus)
        f["property_status"] = STAGE.get(s(r.propertystatus), "unknown")
        f["property_status_observed_date"] = dd
        f["observation_status"] = STAGE.get(s(r.propertystatus), "unknown")
    if s(r.opendate) and not f["open_date"]:
        f["open_date"] = ccp_date(s(r.opendate))
        f["open_date_basis"] = ("Casino City Press opendate, source string '"
                                + s(r.opendate) + "' parsed as %d%b%Y")

log(f"Casino City facilities              : {len(facilities)}")

# ---- Tribal Property List: same Casino City ID space -> exact, safe join
# NOTE: read as dict records, NOT itertuples -- pandas mangles column names with
# spaces into positional _0/_1 fields, which silently dropped every date on the
# first pass of this build.
tpl = pd.read_excel(os.path.join(SRC, "Tribal Property List.xlsx"))
tpl.columns = [str(c).strip() for c in tpl.columns]
missing_cols = [c for c in ("Casino City ID", "Gaming Property Name", "Tribe Name",
                            "State", "Open Date", "1st Close Date") if c not in tpl.columns]
if missing_cols:
    log("FATAL: Tribal Property List is missing expected columns: " + repr(missing_cols))
    sys.exit(1)
n_tpl_new, n_tpl_dates, n_tpl_hit, n_tpl_dup = 0, 0, 0, 0
for d in tpl.to_dict("records"):
    cid = s(d.get("Casino City ID"))
    if cid.endswith(".0"): cid = cid[:-2]
    name = s(d.get("Gaming Property Name")); tribe = s(d.get("Tribe Name"))
    state = st(d.get("State"))
    od = d.get("Open Date"); cd = d.get("1st Close Date")
    od = od.date().isoformat() if hasattr(od, "date") and pd.notna(od) else ""
    cd = cd.date().isoformat() if hasattr(cd, "date") and pd.notna(cd) else ""
    fid = "CCP-" + cid if cid else ""
    if fid and fid in facilities:
        f = facilities[fid]
        n_tpl_hit += 1
        if od:
            f["open_date"] = od
            f["open_date_basis"] = "Casino City Tribal Property List, 'Open Date'"
            n_tpl_dates += 1
        if cd:
            f["close_date"] = cd
            f["close_date_basis"] = "Casino City Tribal Property List, '1st Close Date'"
        if "tribal_property_list" not in f["source_datasets"]:
            f["source_datasets"] += "|tribal_property_list"
    elif name:
        n_tpl_new += 1
        fid = "CCP-" + cid if cid else "TPL-%04d" % n_tpl_new
        if fid in facilities:      # two roster rows share one Casino City ID
            n_tpl_dup += 1
            facilities[fid]["duplicate_risk"] = 1
            facilities[fid]["match_basis"] = (
                "the Casino City Tribal Property List carries more than one row for "
                "this Casino City ID; only the first is kept")
            continue
        facilities[fid] = dict(
            facility_id=fid, entity_id="", tribe=tribe, facility_name=name, company="",
            address=s(d.get("Address", "")), city=s(d.get("City", "")), state=state,
            postal_code="", latitude="", longitude="", coords_basis="",
            property_status="", property_status_literal="",
            property_status_observed_date="", observation_status="",
            open_date=od, open_date_basis=("Casino City Tribal Property List, 'Open Date'" if od else ""),
            open_date_source_url="",
            close_date=cd, close_date_basis=("Casino City Tribal Property List, '1st Close Date'" if cd else ""),
            close_date_source_url="",
            casino_city_id=cid, n_capacity_observations=0,
            first_observed_date="", last_observed_date="",
            source_datasets="tribal_property_list", match_status="", match_basis="",
            duplicate_risk=0, native_american_flag="", property_type="",
            fetched_date=FETCHED)
log(f"Tribal Property List rows           : {len(tpl)}  "
    f"(matched on Casino City ID: {n_tpl_hit}; new facilities added: {n_tpl_new}; "
    f"open dates attached: {n_tpl_dates}; roster rows sharing an ID with an existing facility: {n_tpl_dup})")

# ---- indexes for conservative cross-source matching.
# Two exact keys only: normalized (name, state), then normalized (address, state).
# No fuzzy matching, no token-subset matching. A missed link is recoverable; a
# false one is not (AGENTS.md, "Cherokee Inc." trap).
def key(name, state): return (norm(name), st(state))
idx = collections.defaultdict(list)
addr_idx = collections.defaultdict(list)
name_only_idx = collections.defaultdict(list)
for fid, f in facilities.items():
    if f["facility_name"]:
        idx[key(f["facility_name"], f["state"])].append(fid)
        name_only_idx[norm(f["facility_name"])].append(fid)
    if f["address"]:
        addr_idx[key(f["address"], f["state"])].append(fid)

# ===========================================================================
# 2. votingpatterns canonical casino addresses (411) -- identity + coordinates
# ===========================================================================
vp = pd.read_csv(os.path.join(SRC, "canonical_casino_addresses_supplement.csv"),
                 dtype=str, keep_default_na=False)
n_vp_match, n_vp_new, n_vp_ambig, n_vp_addr = 0, 0, 0, 0
for i, r in enumerate(vp.to_dict("records"), 1):
    name, state = r.get("casino_name", ""), r.get("state", "")
    hits = idx.get(key(name, state), [])
    how = "exact match on normalized (facility_name, state)"
    if len(hits) != 1 and r.get("address"):
        ahits = addr_idx.get(key(r["address"], state), [])
        if len(ahits) == 1:
            hits, how = ahits, "exact match on normalized (street address, state)"
            n_vp_addr += 1
    src_url = r.get("source", "")
    cbasis = ("votingpatterns canonical_casino_addresses; coordinates hand-curated "
              "from " + (src_url or "an unrecorded source"))
    if len(hits) == 1:
        f = facilities[hits[0]]
        n_vp_match += 1
        if "votingpatterns_canonical" not in f["source_datasets"]:
            f["source_datasets"] += "|votingpatterns_canonical"
        f["match_status"] = "matched_casino_city_and_votingpatterns"
        f["match_basis"] = how
        if not f["latitude"] and r.get("latitude"):
            f["latitude"], f["longitude"] = r["latitude"], r.get("longitude", "")
            f["coords_basis"] = cbasis
        if not f["address"]: f["address"] = r.get("address", "")
        if not f["city"]:    f["city"] = r.get("city", "")
    else:
        if len(hits) > 1: n_vp_ambig += 1
        n_vp_new += 1
        fid = "VP-%04d" % i
        facilities[fid] = dict(
            facility_id=fid, entity_id="", tribe=r.get("tribe_canonical", ""),
            facility_name=name, company="", address=r.get("address", ""),
            city=r.get("city", ""), state=st(state), postal_code=r.get("zip", ""),
            latitude=r.get("latitude", ""), longitude=r.get("longitude", ""),
            coords_basis=cbasis, property_status="", property_status_literal="",
            property_status_observed_date="", observation_status="",
            open_date="", open_date_basis="", open_date_source_url="",
            close_date="", close_date_basis="", close_date_source_url="",
            casino_city_id="", n_capacity_observations=0,
            first_observed_date="", last_observed_date="",
            source_datasets="votingpatterns_canonical",
            match_status=("ambiguous_multiple_casino_city_candidates" if len(hits) > 1
                          else "votingpatterns_only_no_exact_casino_city_match"),
            match_basis=("%d Casino City candidates share the normalized name+state; "
                         "left unmatched rather than guessed" % len(hits)) if len(hits) > 1
                        else "no exact normalized (name, state) match in Casino City",
            duplicate_risk=1, native_american_flag="", property_type="",
            fetched_date=FETCHED)
log(f"votingpatterns canonical addresses  : {len(vp)}  "
    f"(matched {n_vp_match} [{n_vp_addr} of them via street address], "
    f"unmatched-added {n_vp_new}, of which ambiguous {n_vp_ambig})")
# How much of the unmatched residue is plausibly duplicate rather than genuinely
# new? Reported, not acted on -- no near-match is ever committed.
vp_only = [f for f in facilities.values() if f["facility_id"].startswith("VP-")]
ccp_tribes = set(norm(f["tribe"]) for f in facilities.values()
                 if f["facility_id"].startswith("CCP-") and f["tribe"])
same_tribe = sum(1 for f in vp_only if norm(f["tribe"]) in ccp_tribes)
log(f"   of the {len(vp_only)} unmatched votingpatterns rows, {same_tribe} belong to a "
    f"tribe that already appears in Casino City -- i.e. duplicate_risk=1 is a real "
    f"upper bound on new facilities, not a count of new facilities")

# ===========================================================================
# 3. Indian Gaming Dataset -- opening/closing dates WITH source URLs
# ===========================================================================
igd = pd.read_excel(os.path.join(SRC, "Indian Gaming Dataset.xlsx"), sheet_name="Sheet1")
igd.columns = [str(c).strip() for c in igd.columns]
n_igd_match, n_igd_dates = 0, 0
for r in igd.to_dict("records"):
    name, state = s(r.get("company")), st(r.get("state"))
    if not name: continue
    hits = idx.get(key(name, state), [])
    if len(hits) != 1: continue
    f = facilities[hits[0]]
    n_igd_match += 1
    if "indian_gaming_dataset" not in f["source_datasets"]:
        f["source_datasets"] += "|indian_gaming_dataset"
    od, ourl = r.get("openingdate1"), s(r.get("openingdate1 source"))
    if pd.notna(od) and s(od):
        f["open_date"] = od.date().isoformat() if hasattr(od, "date") else s(od)
        f["open_date_basis"] = ("Indian Gaming Dataset, hand-coded opening event with a "
                                "per-event source URL")
        f["open_date_source_url"] = ourl
        n_igd_dates += 1
    cd, curl = r.get("closingdate1"), s(r.get("closingdate1 source"))
    if pd.notna(cd) and s(cd) and not str(cd).startswith("http"):
        f["close_date"] = cd.date().isoformat() if hasattr(cd, "date") else s(cd)
        f["close_date_basis"] = "Indian Gaming Dataset, hand-coded closing event"
        f["close_date_source_url"] = curl
log(f"Indian Gaming Dataset rows          : {len(igd)}  "
    f"(exact-matched {n_igd_match}, opening dates upgraded {n_igd_dates})")

# ===========================================================================
# 4. Revenue and payments -- tribe level, every row basis-labeled
# ===========================================================================
# metric -> (measure_type, value_basis for the IMPLIED GGR row, detail)
# Rates are quoted from per_property_gaming_revenue_FINAL_v2_README.md, which
# states the inversions verbatim; each is re-confirmed by the exact multiplier
# observed between the payment file and the implied-GGR file.
GGR_BASIS = {
 "ok_exclusivity_fee_annual":       ("payments_derived",  "state exclusivity fee / 0.05; the fee is source-archived (OK OMES gaming compliance reports). README: 'OK exclusivity fees / 0.05 (4-6% avg rate on AGR)'. The 5% is an average, not the tribe's actual tier rate."),
 "ct_slot_contribution_annual":     ("payments_derived",  "CT slot contribution / 0.25; the contribution is source-archived (data.ct.gov). README: 'CT slot contributions / 0.25 (25% to state)'."),
 "ct_slot_win_annual":              ("reported",          "actual slot win published by CT (data.ct.gov). Slots only -- excludes table games and non-gaming."),
 "mi_2_pct_state_payment":          ("reverse_engineered","MI 2% payment / 0.02, where the payment itself is a hand-written estimate that was never source-verified (published_revenue_audit_REPORT.md)."),
 "or_local_government_share":       ("reverse_engineered","OR local-government share / 0.06 on a hand-written, unverified payment."),
 "ok_compact_share_annual":         ("reverse_engineered","OK compact share / 0.05 on a legacy hand-written payment."),
 "ny_compact_payment_annual":       ("reverse_engineered","NY compact payment / 0.25 on a hand-written, unverified payment."),
 "wa_compact_payment_annual":       ("reverse_engineered","WA compact payment / per-compact rate on a hand-written payment. One rate is 0.13%, producing a ~769x multiplier -- treat as not usable."),
 "wi_compact_payment_annual":       ("reverse_engineered","WI compact payment / per-compact rate on a hand-written payment."),
 "implan_revenue":                  ("modelled",          "IMPLAN model input/output from Lumecon Box files (Mashantucket Pequot 2017, Otoe-Missouria). Model output, not an observed revenue."),
 "mn_no_state_share_estimated_GGR": ("modelled",          "MIGA tribally-self-reported estimate for a no-revenue-share state. README: 'explicitly labeled estimates'."),
 "property_estimated_GGR_annual":   ("modelled",          "industry estimate. Audit report: Seminole Hollywood/Tampa GGRs 'are industry estimates, not Seminole-published per-property'."),
 "ca_RSTF_per_device":              ("reverse_engineered","CA RSTF per-device figure; audit report: 'RSTF formula is real; specific tribe-quarter values are estimates'."),
 "ca_SDF_payment":                  ("reverse_engineered","CA Special Distribution Fund payment; hand-written estimate, not source-verified."),
 "az_state_distribution_annual":    ("reported",          "Arizona STATE-LEVEL aggregate distribution (AZ JLBC). AZ compacts prohibit per-tribe disclosure -- this is a state total and must never be split across tribes. 19 per-tribe AZ rows in the v2 vintage were fabricated by proportional guessing and were removed."),
}

pp = pd.read_csv(os.path.join(SRC, "per_property_gaming_revenue_FINAL_v3_audited.csv"),
                 dtype=str, keep_default_na=False)
unknown = sorted(set(pp["metric"]) - set(GGR_BASIS))
if unknown:
    log("FATAL: revenue metrics with no declared value_basis: " + repr(unknown))
    sys.exit(1)

n_rev = collections.Counter()
n_rev_fac = 0
for r in pp.to_dict("records"):
    m = r["metric"]
    basis, detail = GGR_BASIS[m]
    try: val = float(r["implied_GGR_millions"])
    except (TypeError, ValueError): continue
    non_gaming = (s(r.get("is_gaming")) == "0")
    tribe = r.get("tribe_canonical", "")
    prop = r.get("property_name", "")
    # Attach to a facility ONLY when the normalized property name resolves to
    # exactly one facility in the whole directory. Otherwise the observation
    # stays at tribe level -- the revenue panel's "properties" are mostly tribes.
    fac = ""
    if prop and not non_gaming:
        h = name_only_idx.get(norm(prop), [])
        if len(h) == 1:
            fac = h[0]; n_rev_fac += 1
    metrics.append(dict(
        facility_id=fac, entity_id="",
        entity_level=("implan_sector_line_item" if non_gaming
                      else ("facility" if fac else "tribe")),
        tribe=tribe,
        facility_name=(prop if not non_gaming else ""),
        state="", metric=("implied_gaming_revenue" if not non_gaming
                          else "implan_sector_output_non_gaming"),
        measure_type="gaming_revenue",
        value=val, unit="usd_millions",
        observation_date="", observation_period=s(r.get("year")),
        observation_status="current",
        source_status_literal=s(r.get("data_quality_tier_audited")),
        value_basis=basis,
        value_verification=("source_archived" if basis in ("reported", "payments_derived")
                            else "not_source_verified"),
        value_basis_detail=detail + " | underlying source metric: " + m,
        source=s(r.get("source")),
        source_file="per_property_gaming_revenue_FINAL_v3_audited.csv",
        fetched_date=FETCHED))
    n_rev[basis] += 1

pub = pd.read_csv(os.path.join(SRC, "published_tribal_gaming_revenue_v3_audited.csv"),
                  dtype=str, keep_default_na=False)
unknown = sorted(set(pub["metric"]) - set(GGR_BASIS))
if unknown:
    log("FATAL: payment metrics with no declared value_basis: " + repr(unknown))
    sys.exit(1)

n_pay = collections.Counter()
for r in pub.to_dict("records"):
    m = r["metric"]
    try: val = float(r["value_usd_millions"])
    except (TypeError, ValueError): continue
    ver = s(r.get("verification_status"))
    arch = s(r.get("data_archived_at"))
    # The PAYMENT itself is reported when the state's report is archived; it is a
    # hand-written estimate otherwise. This is independent of whether the derived
    # GGR is defensible.
    if ver == "agent_verified":
        basis, verification = "reported", "source_archived: " + (arch or "unstated")
    elif ver == "agent_state_aggregate":
        basis, verification = "reported", "source_archived state aggregate: " + (arch or "unstated")
    else:
        basis, verification = "modelled", "not_source_verified (hand-written estimate)"
    is_rev = m in ("ct_slot_win_annual", "mn_no_state_share_estimated_GGR",
                   "property_estimated_GGR_annual")
    metrics.append(dict(
        facility_id="", entity_id="", entity_level="tribe",
        tribe=s(r.get("geo_name")), facility_name="", state="",
        metric=m, measure_type=("gaming_revenue" if is_rev else "payment_to_government"),
        value=val, unit="usd_millions",
        observation_date="", observation_period=s(r.get("fiscal_year")),
        observation_status="current",
        source_status_literal=ver,
        value_basis=basis, value_verification=verification,
        value_basis_detail=(s(r.get("notes")) or GGR_BASIS[m][1]),
        source=s(r.get("source")),
        source_file="published_tribal_gaming_revenue_v3_audited.csv",
        fetched_date=FETCHED))
    n_pay[basis] += 1

log(f"per-property implied revenue rows   : {sum(n_rev.values())}  {dict(n_rev)}")
log(f"   of which resolved to a single named facility: {n_rev_fac} "
    f"(the rest stay at tribe level)")
log(f"state-published payment rows        : {sum(n_pay.values())}  {dict(n_pay)}")

# ===========================================================================
# 5. Facility row: latest observation of each capacity metric
# ===========================================================================
latest = {}
for m in metrics:
    if m["entity_level"] != "facility" or m["measure_type"] != "capacity": continue
    k = (m["facility_id"], m["metric"])
    if k not in latest or (m["observation_date"] or "") > (latest[k]["observation_date"] or ""):
        latest[k] = m

for fid, f in facilities.items():
    for _, metric, unit in CAP:
        m = latest.get((fid, metric))
        if m:
            f[metric] = m["value"]
            f[metric + "_value_basis"] = "reported"
            f[metric + "_observation_status"] = m["observation_status"]
            f[metric + "_observed_date"] = m["observation_date"]
        else:
            f[metric] = ""
            f[metric + "_value_basis"] = ("not_published" if f["casino_city_id"]
                                          else "no_capacity_source_for_this_facility")
            f[metric + "_observation_status"] = ""
            f[metric + "_observed_date"] = ""
    if not f["match_status"]:
        f["match_status"] = "casino_city_only"
        f["match_basis"] = "no exact normalized (name, state) match from another source"

# ===========================================================================
# 6. Write
# ===========================================================================
FFIELDS = (["facility_id", "entity_id", "tribe", "facility_name", "company",
            "address", "city", "state", "postal_code", "latitude", "longitude",
            "coords_basis", "observation_status", "property_status",
            "property_status_literal", "property_status_observed_date",
            "open_date", "open_date_basis", "open_date_source_url",
            "close_date", "close_date_basis", "close_date_source_url"]
           + [c for _, m, _ in CAP for c in
              (m, m + "_value_basis", m + "_observation_status", m + "_observed_date")]
           + ["casino_city_id", "n_capacity_observations", "first_observed_date",
              "last_observed_date", "native_american_flag", "property_type",
              "source_datasets", "match_status", "match_basis", "duplicate_risk",
              "fetched_date"])
MFIELDS = ["facility_id", "entity_id", "entity_level", "tribe", "facility_name",
           "state", "metric", "measure_type", "value", "unit", "observation_date",
           "observation_period", "observation_status", "source_status_literal",
           "value_basis", "value_verification", "value_basis_detail", "source",
           "source_file", "fetched_date"]

def dump(name, fields, data):
    with open(os.path.join(CLEAN, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in data: w.writerow(r)

frows = sorted(facilities.values(), key=lambda x: (x["state"], x["facility_name"]))
dump("gaming_facilities.csv", FFIELDS, frows)
dump("gaming_facility_metrics.csv", MFIELDS, metrics)

# ===========================================================================
# 7. Report
# ===========================================================================
log("")
log("=" * 78); log("DIRECTORY CORE BUILT"); log("=" * 78)
log(f"gaming_facilities.csv rows       : {len(frows)}")
log(f"gaming_facility_metrics.csv rows : {len(metrics):,}")
log("")
log("facilities by source_datasets:")
for k, v in collections.Counter(f["source_datasets"] for f in frows).most_common():
    log(f"   {v:>5}  {k}")
log("")
log("facilities by match_status:")
for k, v in collections.Counter(f["match_status"] for f in frows).most_common():
    log(f"   {v:>5}  {k}")
log(f"   duplicate_risk=1 (unmatched, may duplicate a Casino City row): "
    f"{sum(1 for f in frows if f['duplicate_risk'] == 1)}")
log("")
log("facility observation_status (latest Casino City wave):")
for k, v in collections.Counter(f["observation_status"] or "(no casino city status)"
                                for f in frows).most_common():
    log(f"   {v:>5}  {k}")
log("")
log("capacity fill on the facility row (latest observation):")
for _, m, unit in CAP:
    n = sum(1 for f in frows if f[m] != "")
    log(f"   {m:<24} {n:>5} / {len(frows)}  ({100*n/len(frows):4.1f}%)  [{unit}]")
log("")
log("gaming_facility_metrics.csv -- observation_status x measure_type:")
c = collections.Counter((m["measure_type"], m["observation_status"]) for m in metrics)
for (mt, os_), v in sorted(c.items(), key=lambda kv: -kv[1]):
    log(f"   {v:>6}  {mt:<22} {os_}")
log("")
log("gaming_facility_metrics.csv -- value_basis (THE COLUMN THAT MATTERS):")
for k, v in collections.Counter(m["value_basis"] for m in metrics).most_common():
    log(f"   {v:>6}  {k}")
log("")
log("revenue/payment observations only, by value_basis:")
rv = [m for m in metrics if m["measure_type"] != "capacity"]
for k, v in collections.Counter(m["value_basis"] for m in rv).most_common():
    log(f"   {v:>6}  {k}")
log(f"   total dollar observations: {len(rv)}")
log(f"   REPORTED gaming-revenue observations: "
    f"{sum(1 for m in rv if m['measure_type'] == 'gaming_revenue' and m['value_basis'] == 'reported')}")
log(f"   gaming-revenue observations that are NOT reported: "
    f"{sum(1 for m in rv if m['measure_type'] == 'gaming_revenue' and m['value_basis'] != 'reported')}")
log("")
log("PROPOSAL-STAGE capacity observations (Casino City 'Planned' / 'Under Construction')")
log("-- these must never be quoted as facility facts:")
c = collections.Counter((m["observation_status"], m["metric"]) for m in metrics
                        if m["measure_type"] == "capacity"
                        and m["observation_status"] in ("proposed", "approved"))
log(f"   {sum(c.values())} observations across "
    f"{len(set(m['facility_id'] for m in metrics if m['measure_type']=='capacity' and m['observation_status'] in ('proposed','approved')))} facilities")
for k, v in c.most_common(8): log(f"      {v:>4}  {k[0]:<9} {k[1]}")

with open(os.path.join(BASE, "logs", "23_gaming_2026-08-05.log"), "a",
          encoding="utf-8") as fh:
    fh.write("\n\n" + "=" * 78 + "\n23d_build_gaming_facilities.py\n"
             + "=" * 78 + "\n" + buf.getvalue())
