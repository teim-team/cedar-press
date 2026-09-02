"""1110 - TRIBAL DEBT DISTRESS, FROM THE COURT RECORD.

WHY THIS EXISTS
---------------
`code/1082_tribal_debt_holdings_disclosure.py` built the HOLDINGS side: 1,585
fund-holding observations, 14 obligors, 199 registered funds - and **zero**
distress flags.  It diagnosed the reason correctly: Form N-PORT begins in 2019
and the significant tribal restructurings predate it.  **The channel is younger
than the distress.**

So the distress record is in the courts.  This script opens that channel
through the CourtListener REST API (v4), which the owner's token authorises.

WHAT A TRIBAL DEFAULT IS NOT
----------------------------
A tribal obligor is a SOVEREIGN.  Sovereign immunity, limited waivers,
limited-recourse structures and the NIGC management-contract approval
requirement mean the legal shape is genuinely different from a corporate
default, and the leading case is the proof:

    Wells Fargo Bank, N.A. v. Lake of the Torches Resort Casino, Inc.
    658 F.3d 684 (7th Cir. 2011)

there the bond INDENTURE was held void as an unapproved management contract
under IGRA.  A naive reader records "the tribe did not pay bondholders" as a
default.  The court found the contract UNENFORCEABLE.  Those are opposite
findings and this table must never collapse them.

Hence three columns that are not decoration:

    event_type              typed ONLY by an explicit phrase rule, and the
                            phrase that fired is recorded in event_type_basis.
                            No phrase -> UNTYPED_NEEDS_HUMAN.  Never guessed.
    assertion_or_finding    ALLEGATION_BY_A_PARTY vs COURT_FINDING vs
                            PROCEDURAL_RECORD.  A complaint alleges; a
                            judgment finds.
    as_of_date              every row is dated.  An event is not a running
                            condition: a 2012 restructuring says nothing about
                            a nation's finances in 2026, and
                            `currency_caution` says so on every row.

TERMS
-----
`docs/PUBLICATION_POLICY.md` TERMS-SCOPE: *"The distinction is authorship, not
subject matter."*  A court docket is the COURT's record, not the tribe's, so no
tribal source's terms of use reach it.  **EMMA is CONSTRAINED and is not
touched by this script** - its terms bar the output "either commercially or
free of charge", name "or any manual process", and CUSIP Global Services is a
second licensor.  Queued as TD-1 in `review/OWNER_DECISION_QUEUE.md`.

NATURAL PERSONS
---------------
Tribal officials and counsel acting in a public role in a filed case are
public; individual members are not.  This script emits NO party-person table.
It records the court's own caption, and screens every candidate: a caption
whose shape is an individual against a tribe (per-capita, disenrollment,
employment, tort) is held in `review/1110_person_screen_held.csv` and never
staged.

BUDGET
------
The free authenticated tier is 5/min, 50/hr, 125/day, PER TOKEN.  `code/366`
already meters that token, so this script APPENDS TO THE SAME LEDGER
(`data/raw/external/courtlistener_2026-08-26/_request_ledger.json`).  Two
scripts with two private ledgers would each believe it had 125.

STAGES
------
py -3 code/1110_tribal_debt_court_distress.py targets    # 0 requests
py -3 code/1110_tribal_debt_court_distress.py probe      # 1 request, shape only
py -3 code/1110_tribal_debt_court_distress.py search --max N
py -3 code/1110_tribal_debt_court_distress.py opinions --max N
py -3 code/1110_tribal_debt_court_distress.py build      # 0 requests
py -3 code/1110_tribal_debt_court_distress.py verify     # exit 1 on breach
py -3 code/1110_tribal_debt_court_distress.py selftest   # proves verify fires
py -3 code/1110_tribal_debt_court_distress.py spend      # 0 requests
"""
import argparse
import csv
import datetime
import gzip
import json
import os
import pathlib
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

csv.field_size_limit(10 ** 8)

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
STAGING = ROOT / "data" / "staging"
REVIEW = ROOT / "review"
LOGS = ROOT / "logs"
RAW = ROOT / "data" / "raw" / "external" / "tribal_debt_court_1110"
RAW.mkdir(parents=True, exist_ok=True)
STAGING.mkdir(parents=True, exist_ok=True)

SCRIPT = "1110_tribal_debt_court_distress.py"
HOST = "www.courtlistener.com"
API = "https://www.courtlistener.com/api/rest/v4"
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
TODAY = datetime.date.today().isoformat()

SPEND = (ROOT / "data" / "raw" / "external" / "courtlistener_2026-08-26"
         / "_request_ledger.json")
PER_MIN, PER_HOUR, PER_DAY = 5, 50, 125
GAP_S = 60.0 / PER_MIN + 0.6
RUN_DEADLINE_S = 100 * 60
MAX_CONSEC_REFUSALS = 3
START = time.time()

TARGETS = REVIEW / "1110_targets.csv"
HITS = REVIEW / "1110_search_hits.csv"
MANIFEST = REVIEW / "1110_fetch_manifest.csv"
HELD = REVIEW / "1110_person_screen_held.csv"
REJECTED = REVIEW / "1110_rejected_hits.csv"
UNREACHED = REVIEW / "1110_unreached_cases.csv"
EVENTS = STAGING / "tribal_debt_court_events.csv"
DOCS = STAGING / "tribal_debt_court_documents.csv"
DOCKETS = STAGING / "tribal_debt_court_dockets.csv"

CURRENCY_CAUTION = (
    "AN EVENT IS NOT A RUNNING CONDITION. This row is dated. It describes what "
    "a court record shows on that date and asserts nothing about the obligor's "
    "finances at any later date, including today.")
SOVEREIGN_CAUTION = (
    "A tribal obligor is a sovereign. Sovereign immunity, limited waivers, "
    "limited-recourse structures and the NIGC management-contract approval "
    "requirement mean a tribal default is not a corporate default. Quote the "
    "instrument and the court; do not characterise a nation's finances.")
NOT_SUMMABLE = (
    "an amount recited in a court record is the amount THAT DOCUMENT states, "
    "at that date. NEVER sum amount_usd across events, across courts or across "
    "dates, and never add it to tribal_debt_holdings.principal_usd, "
    "deals_classified.Announced_Value_USD or tribal_bond_issuances.par_amount.")


def log(m):
    try:
        print(m, flush=True)
    except UnicodeEncodeError:
        print(m.encode("ascii", "replace").decode(), flush=True)


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


# ------------------------------------------------------------------ token
def get_token():
    t = (os.environ.get("COURTLISTENER_API_TOKEN")
         or os.environ.get("COURTLISTENER_TOKEN"))
    if t:
        return t.strip(), "process_env"
    envf = ROOT / ".env.local"
    if envf.exists():
        for line in envf.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("COURTLISTENER") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'"), ".env.local"
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            for name in ("COURTLISTENER_API_TOKEN", "COURTLISTENER_TOKEN"):
                try:
                    v, _ = winreg.QueryValueEx(k, name)
                    if v:
                        return str(v).strip(), "HKCU_Environment"
                except FileNotFoundError:
                    continue
    except Exception:
        pass
    return "", "NOT_FOUND"


TOKEN, TOKEN_SOURCE = get_token()


def redact(s):
    s = str(s)
    if TOKEN and TOKEN in s:
        s = s.replace(TOKEN, "REDACTED")
    return s


# ------------------------------------------------------------- host lock
def claim_host(note):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    if p.exists():
        cur = json.loads(p.read_text(encoding="utf-8"))
        if cur.get("active"):
            cur.setdefault("queue", []).append(
                {"script": f"code/{SCRIPT}", "note": note})
            p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            log(f"HOSTLOCK held by {cur.get('script')}; queued and exiting")
            return False
    p.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(), "script": f"code/{SCRIPT}",
        "started": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "active": True, "queue": [], "note": note,
        "auth": "Token header, value never logged",
        "policy": (f"ONE poller, sequential, >={GAP_S:.1f}s gap; caps "
                   f"{PER_MIN}/min {PER_HOUR}/hr {PER_DAY}/day SHARED WITH "
                   f"code/366 via one ledger; stop after "
                   f"{MAX_CONSEC_REFUSALS} refusals"),
    }, indent=1), encoding="utf-8")
    return True


def release_host(note, extra=None):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"host": HOST}
    cur["active"] = False
    cur["released"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur["note"] = note
    if extra:
        cur.update(extra)
    p.write_text(json.dumps(cur, indent=1), encoding="utf-8")


# ---------------------------------------------------------- spend ledger
def load_spend():
    if SPEND.exists():
        return json.loads(SPEND.read_text(encoding="utf-8"))
    return {"requests": [], "note": "one entry per REQUEST SENT, token redacted"}


def save_spend(led):
    tmp = SPEND.with_suffix(".json.part")
    tmp.write_text(redact(json.dumps(led, indent=1)), encoding="utf-8")
    tmp.replace(SPEND)


def spent_counts(led):
    now = time.time()
    return (sum(1 for r in led["requests"] if now - r["t"] < 86400),
            sum(1 for r in led["requests"] if now - r["t"] < 3600),
            sum(1 for r in led["requests"] if now - r["t"] < 60))


# ------------------------------------------- header DERIVED FROM THE FILE
def derive_header(path, rows):
    """RULE 17.  The header is the UNION of what is on disk and what we built,
    on-disk order first.  A fixed literal - or `rows[0].keys()`, which only
    looks derived - silently drops a column an enricher added."""
    on_disk = []
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as f:
            try:
                on_disk = next(csv.reader(f))
            except StopIteration:
                on_disk = []
    cols = list(on_disk)
    for row in rows:
        for k in row:
            if k not in cols:
                cols.append(k)
    return cols


def write_csv(path, rows):
    cols = derive_header(path, rows)
    tmp = path.with_suffix(path.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    tmp.replace(path)


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# =========================================================== THE TARGETS
# Each target is a QUESTION, and the question is recorded so that an empty
# answer is still a recorded answer rather than a blank row.
#
# `obligor_label` is the 1082 obligor label where one exists, so the join is
# built in rather than reconstructed afterwards.  Where the obligor is NOT in
# 1082 the field is blank and `cedar_uid` still carries the entity.

CASES = [
    # ---- P1  the leading case.  A bond indenture held VOID, not defaulted.
    dict(priority="1_LEADING_CASE", q="Lake of the Torches", types="or",
         obligor_label="", cedar_uid="CE-00166-6Z",
         obligor_name="Lac du Flambeau Band of Lake Superior Chippewa Indians",
         question=("Wells Fargo v. Lake of the Torches: did a court hold the "
                   "bond indenture a void management contract under IGRA?")),
    dict(priority="1_LEADING_CASE", q="Saybrook Tax Exempt Investors", types="or",
         obligor_label="", cedar_uid="CE-00166-6Z",
         obligor_name="Lac du Flambeau Band of Lake Superior Chippewa Indians",
         question="the successor bondholder suit on the same Lake of the Torches paper"),
    dict(priority="1_LEADING_CASE",
         q="Lac du Flambeau Band of Lake Superior Chippewa Indians", types="or",
         obligor_label="", cedar_uid="CE-00166-6Z",
         obligor_name="Lac du Flambeau Band of Lake Superior Chippewa Indians",
         question=("the tribe by name - debt-collection and sovereign-immunity "
                   "litigation, including the 2023 Bankruptcy Code case")),

    # ---- P2  obligors that ALSO appear in 1082's holdings register.
    dict(priority="2_JOINS_1082", q="Mashantucket Pequot", types="or",
         obligor_label="Mashantucket (Western) Pequot Tribe",
         cedar_uid="CE-0017C-F5", obligor_name="Mashantucket (Western) Pequot Tribe",
         question="the ~$2.3B Foxwoods restructuring - what reached a court?"),
    dict(priority="2_JOINS_1082", q="Mohegan Tribal Gaming Authority", types="or",
         obligor_label="Mohegan Tribal Gaming Authority",
         cedar_uid="CE-0016X-GY", obligor_name="Mohegan Tribal Gaming Authority",
         question="any default, forbearance or restructuring litigation"),
    dict(priority="2_JOINS_1082", q="River Rock Entertainment Authority", types="or",
         obligor_label="River Rock Entertainment Authority",
         cedar_uid="CE-00143-AM", obligor_name="River Rock Entertainment Authority",
         question="the 2011 note exchange and any bondholder suit"),
    dict(priority="2_JOINS_1082", q="Inn of the Mountain Gods", types="or",
         obligor_label="Inn of the Mountain Gods Resort and Casino",
         cedar_uid="CE-0017A-3K", obligor_name="Inn of the Mountain Gods Resort and Casino",
         question="the 2009-2010 senior note default and its resolution"),
    dict(priority="2_JOINS_1082", q="Cabazon Band of Mission Indians", types="or",
         obligor_label="Cabazon Band of Mission Indians",
         cedar_uid="CE-0012P-JF", obligor_name="Cabazon Band of Mission Indians",
         question="any financing default or lender suit"),

    # ---- P3  the canonical distress cases with no 1082 holdings row.
    dict(priority="3_CANONICAL_NO_HOLDING",
         q="Chukchansi Economic Development Authority", types="or",
         obligor_label="", cedar_uid="CE-0018X-TY",
         obligor_name="Picayune Rancheria of the Chukchansi Indians",
         question="the noteholder litigation and the receivership"),
    dict(priority="3_CANONICAL_NO_HOLDING",
         q="Picayune Rancheria of the Chukchansi Indians", types="or",
         obligor_label="", cedar_uid="CE-0018X-TY",
         obligor_name="Picayune Rancheria of the Chukchansi Indians",
         question="the tribe as a party in the same distress"),
    dict(priority="3_CANONICAL_NO_HOLDING", q="Santa Ysabel", types="or",
         obligor_label="", cedar_uid="CE-00156-1F",
         obligor_name="Iipay Nation of Santa Ysabel",
         question="the Santa Ysabel Resort and Casino default and closure"),
    dict(priority="3_CANONICAL_NO_HOLDING", q="Iipay Nation of Santa Ysabel", types="or",
         obligor_label="", cedar_uid="CE-00156-1F",
         obligor_name="Iipay Nation of Santa Ysabel",
         question="the tribe as a party in the same distress"),

    # ---- P4  the DOCTRINE.  These queries are not about one obligor; they
    #      find the cases that decide what a tribal default legally IS, which
    #      is the material this table exists to keep straight.  Opinions only:
    #      a doctrine is decided in an opinion, and a RECAP keyword sweep would
    #      spend requests on unrelated dockets.
    dict(priority="4_DOCTRINE", types="o",
         q="management contract Indian Gaming Regulatory Act void indenture bonds",
         obligor_label="", cedar_uid="", obligor_name="",
         question="which financings were held void for want of NIGC approval?"),
    dict(priority="4_DOCTRINE", types="o",
         q="tribal bond indenture limited waiver of sovereign immunity event of default",
         obligor_label="", cedar_uid="", obligor_name="",
         question="how have courts read a limited waiver in a tribal indenture?"),
    dict(priority="4_DOCTRINE", types="o",
         q="tribal gaming authority forbearance agreement noteholders restructuring",
         obligor_label="", cedar_uid="", obligor_name="",
         question="forbearance in the tribal gaming context"),
    dict(priority="4_DOCTRINE", types="o",
         q="receiver appointed tribal casino indenture trustee gaming revenues",
         obligor_label="", cedar_uid="", obligor_name="",
         question="receivership over a tribal gaming operation"),

    # ---- P5  ROUND TWO, added after reading round one.  Round one asked for
    #      NATIONS; the paper is issued by their INSTRUMENTALITIES, and the
    #      instrumentality's name is what a lender puts in a caption.
    #      `Wells Fargo Bank NA v. Cabazon Band of Mission Indians` came back
    #      with `East Valley Tourist Development Authority` in its party array
    #      - a name no round-one query contained.
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="Lake of the Torches Economic Development Corporation",
         obligor_label="", cedar_uid="CE-00166-6Z",
         obligor_name="Lac du Flambeau Band of Lake Superior Chippewa Indians",
         question="the issuer itself, rather than the nation"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="East Valley Tourist Development Authority",
         obligor_label="Cabazon Band of Mission Indians", cedar_uid="CE-0012P-JF",
         obligor_name="Cabazon Band of Mission Indians",
         question="Cabazon's borrowing instrumentality, named in the Wells Fargo party array"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="Chukchansi Gold Resort", obligor_label="", cedar_uid="CE-0018X-TY",
         obligor_name="Picayune Rancheria of the Chukchansi Indians",
         question="the property that secured the notes"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="Mohegan Tribal Finance Authority",
         obligor_label="Mohegan Tribal Gaming Authority", cedar_uid="CE-0016X-GY",
         obligor_name="Mohegan Tribal Gaming Authority",
         question="the financing entity rather than the gaming authority"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="Mashantucket Western Pequot Tribal Nation",
         obligor_label="Mashantucket (Western) Pequot Tribe", cedar_uid="CE-0017C-F5",
         obligor_name="Mashantucket (Western) Pequot Tribe",
         question="the nation's own legal name, as a bond obligor"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="Foxwoods Resort Casino",
         obligor_label="Mashantucket (Western) Pequot Tribe", cedar_uid="CE-0017C-F5",
         obligor_name="Mashantucket (Western) Pequot Tribe",
         question="the property behind the ~$2.3B restructuring"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="Santa Ysabel Resort and Casino", obligor_label="", cedar_uid="CE-00156-1F",
         obligor_name="Iipay Nation of Santa Ysabel",
         question="the property that defaulted and closed"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="Dry Creek Rancheria Band of Pomo Indians",
         obligor_label="River Rock Entertainment Authority", cedar_uid="CE-00143-AM",
         obligor_name="River Rock Entertainment Authority",
         question="the nation behind River Rock's notes"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="Mescalero Apache Tribe",
         obligor_label="Inn of the Mountain Gods Resort and Casino",
         cedar_uid="CE-0017A-3K", obligor_name="Inn of the Mountain Gods Resort and Casino",
         question="the nation behind the Inn of the Mountain Gods notes"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="Downstream Development Authority",
         obligor_label="Downstream Development Authority", cedar_uid="CE-0018Z-6G",
         obligor_name="Quapaw Nation",
         question="Quapaw's 144A issuer, an obligor in 1082"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="Catawba Nation Gaming Authority",
         obligor_label="Catawba Nation Gaming Authority", cedar_uid="CE-0012V-GC",
         obligor_name="Catawba Nation Gaming Authority",
         question="a current 1082 obligor - any litigation at all?"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="or",
         q="PCI Gaming Authority",
         obligor_label="PCI Gaming Authority (Poarch Band of Creek Indians)",
         cedar_uid="CE-0018H-JJ", obligor_name="PCI Gaming Authority (Poarch Band of Creek Indians)",
         question="a current 1082 obligor - any litigation at all?"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="o",
         q="tribal casino bond default indenture trustee foreclose gaming revenues",
         obligor_label="", cedar_uid="", obligor_name="",
         question="a second doctrine sweep on the enforcement side"),
    dict(priority="5_OBLIGOR_INSTRUMENTALITY", types="o",
         q="Indian tribe promissory note collateral casino revenues void NIGC approval",
         obligor_label="", cedar_uid="", obligor_name="",
         question="a second doctrine sweep on the void-instrument side"),

    # ---- P6  ROUND THREE, from names the ROUND-TWO DOCKETS handed us.  The
    #      RECAP party arrays are a name source in their own right:
    #      `U.S. Bank v. Mashantucket Pequot Gaming Enterprise` and
    #      `Sonoma Falls Developers, LLC v. Dry Creek Rancheria` are both
    #      captions no query of ours contained.
    dict(priority="6_FROM_A_DOCKET_PARTY_ARRAY", types="or",
         q="Mashantucket Pequot Gaming Enterprise",
         obligor_label="Mashantucket (Western) Pequot Tribe",
         cedar_uid="CE-0017C-F5", obligor_name="Mashantucket (Western) Pequot Tribe",
         question="the legal person U.S. Bank sued, rather than the nation"),
    dict(priority="6_FROM_A_DOCKET_PARTY_ARRAY", types="or",
         q="Sonoma Falls Developers",
         obligor_label="River Rock Entertainment Authority", cedar_uid="CE-00143-AM",
         obligor_name="River Rock Entertainment Authority",
         question="the Dry Creek casino-development financing dispute"),
    dict(priority="6_FROM_A_DOCKET_PARTY_ARRAY", types="o",
         q="senior notes tribal economic development authority indenture event of default acceleration",
         obligor_label="", cedar_uid="", obligor_name="",
         question="acceleration on tribal senior notes"),
    dict(priority="6_FROM_A_DOCKET_PARTY_ARRAY", types="o",
         q="casino financing sole proprietary interest management contract NIGC chairman approval void",
         obligor_label="", cedar_uid="", obligor_name="",
         question="the sole-proprietary-interest test that voids a financing"),

    # ---- 0  CONTROL.  A case name built so that it cannot exist.  If this
    #      returns an opinion, every positive above is worthless.
    dict(priority="0_CONTROL_ABSENT", q="Kwithluk Sentinel Indenture Trustee Holdings",
         types="or", obligor_label="", cedar_uid="", obligor_name="",
         question="does this endpoint return something for anything?"),
]


def step_targets():
    rows = []
    for i, c in enumerate(CASES):
        for stype, sname in (("o", "opinions"), ("r", "recap_dockets")):
            if stype not in c.get("types", "or"):
                continue
            rows.append({
                "target_id": f"T{i:02d}_{stype}",
                "priority": c["priority"],
                "search_type": stype,
                "search_type_name": sname,
                "query": c["q"],
                "obligor_label_1082": c["obligor_label"],
                "cedar_uid": c["cedar_uid"],
                "obligor_name": c["obligor_name"],
                "question": c["question"],
                "built_by_script": f"code/{SCRIPT}",
                "built_date": TODAY,
            })
    # the control is cheap; run it FIRST in both indexes.
    order = {"0_CONTROL_ABSENT": 0, "1_LEADING_CASE": 1, "2_JOINS_1082": 2,
             "3_CANONICAL_NO_HOLDING": 3, "4_DOCTRINE": 4,
             "5_OBLIGOR_INSTRUMENTALITY": 5, "6_FROM_A_DOCKET_PARTY_ARRAY": 6}
    rows.sort(key=lambda r: (order[r["priority"]], r["target_id"]))
    write_csv(TARGETS, rows)
    log(f"{len(rows)} targets ({len(CASES)} questions x 2 indexes) -> {TARGETS.name}"
        f"   (0 requests spent)")
    for r in rows[:8]:
        log(f"  {r['priority']:24s} {r['search_type_name']:14s} {r['query'][:46]}")
    return 0


# ================================================================ fetching
def cl_get(url):
    hdr = {"User-Agent": UA, "Accept": "application/json"}
    if TOKEN:
        hdr["Authorization"] = f"Token {TOKEN}"
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace"))


def cache_path(kind, key):
    safe = re.sub(r"[^A-Za-z0-9]+", "_", str(key))[:80]
    return RAW / f"{kind}_{safe}.json.gz"


def cache_write(path, obj):
    tmp = path.with_suffix(".gz.part")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        f.write(redact(json.dumps(obj)))
    tmp.replace(path)


def cache_read(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def manifest_append(rows):
    have = read_csv(MANIFEST)
    keys = {r.get("request_key") for r in have}
    for r in rows:
        if r["request_key"] not in keys:
            have.append(r)
            keys.add(r["request_key"])
    write_csv(MANIFEST, have)


def _metered(led, urls_and_keys, kind, note):
    """Send each URL once, sequentially, inside the shared budget.

    Returns (results, stopped_reason).  `results` is a list of
    (key, status, payload_or_None).
    """
    out, consec, stopped, sent = [], 0, None, 0
    for key, url in urls_and_keys:
        if time.time() - START > RUN_DEADLINE_S:
            stopped = "RUN_DEADLINE"
            break
        d, h, _ = spent_counts(led)
        if d >= PER_DAY:
            stopped = "PER_DAY"
            break
        if h >= PER_HOUR:
            stopped = "PER_HOUR"
            break
        while spent_counts(led)[2] >= PER_MIN:
            time.sleep(2)
        if sent:
            time.sleep(GAP_S)
        led["requests"].append({
            "t": time.time(),
            "iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "script": f"code/{SCRIPT}", "target": str(key),
            "url": redact(url), "status": "SENT"})
        save_spend(led)
        sent += 1
        try:
            status, js = cl_get(url)
            led["requests"][-1]["status"] = status
            led["requests"][-1]["reported_count"] = js.get("count")
            led["requests"][-1]["retrieved"] = len(js.get("results") or []) \
                if isinstance(js.get("results"), list) else 1
            save_spend(led)
            out.append((key, status, js))
            consec = 0
        except urllib.error.HTTPError as e:
            led["requests"][-1]["status"] = f"HTTP {e.code}"
            save_spend(led)
            out.append((key, f"HTTP {e.code}", None))
            log(f"  {str(key)[:50]:50s} HTTP {e.code}")
            # 404 and 403 are FACTS ABOUT THE OBJECT, not the host refusing us.
            if e.code in (404, 403):
                consec = 0
                continue
            consec += 1
            if e.code == 429:
                stopped = "HTTP_429"
                break
            if consec >= MAX_CONSEC_REFUSALS:
                stopped = f"{consec} consecutive refusals"
                break
        except Exception as e:
            led["requests"][-1]["status"] = f"ERR {redact(str(e))[:120]}"
            save_spend(led)
            out.append((key, f"ERR {redact(str(e))[:120]}", None))
            consec += 1
            if consec >= MAX_CONSEC_REFUSALS:
                stopped = f"{consec} consecutive errors"
                break
    return out, stopped


def step_probe():
    """ONE request.  Learn the response shape before spending a budget on it."""
    if not TOKEN:
        log("NO TOKEN. Refusing to run.")
        return 2
    if not claim_host("shape probe, 1 request"):
        return 3
    led = load_spend()
    d, h, _ = spent_counts(led)
    log(f"budget before: {d}/{PER_DAY} today, {h}/{PER_HOUR} this hour "
        f"(SHARED ledger with code/366)")
    url = API + "/search/?" + urllib.parse.urlencode(
        {"q": '"Lake of the Torches"', "type": "o", "order_by": "dateFiled desc"})
    res, stopped = _metered(led, [("probe_lake_of_the_torches", url)], "search", "probe")
    release_host("probe complete")
    for key, status, js in res:
        log(f"status={status}")
        if js:
            cache_write(cache_path("probe", key), js)
            log(f"count={js.get('count')}  results={len(js.get('results') or [])}")
            r0 = (js.get("results") or [None])[0]
            if r0:
                log("TOP-LEVEL RESULT KEYS: " + ", ".join(sorted(r0.keys())))
                log(json.dumps({k: v for k, v in r0.items()
                                if k not in ("opinions", "recap_documents")},
                               indent=1)[:2500])
                subs = r0.get("opinions") or r0.get("recap_documents") or []
                if subs:
                    log("SUB KEYS: " + ", ".join(sorted(subs[0].keys())))
                    log(json.dumps(subs[0], indent=1)[:1500])
    return 0


def step_search(max_requests):
    if not TOKEN:
        log("NO TOKEN. Refusing to run.")
        return 2
    targets = read_csv(TARGETS)
    if not targets:
        log("no targets - run `targets` first")
        return 2
    done = {r["target_id"] for r in read_csv(HITS)}
    todo = [t for t in targets if t["target_id"] not in done]
    if not todo:
        log("every target already answered; nothing sent")
        return 0
    led = load_spend()
    d, h, _ = spent_counts(led)
    room = max(0, min(PER_DAY - d, PER_HOUR - h, max_requests))
    log(f"budget: {d}/{PER_DAY} today, {h}/{PER_HOUR} this hour -> room {room}")
    if room <= 0:
        log("no budget in this window; nothing sent")
        return 0
    todo = todo[:room]
    if not claim_host(f"tribal debt court distress search, {len(todo)} requests"):
        return 3

    reqs = []
    for t in todo:
        # RELEVANCE order, deliberately.  `dateFiled desc` on a 25-hit query
        # whose page holds 20 pushes the LEADING case off the page - the
        # 7th Circuit's 2011 Lake of the Torches decision is the oldest thing
        # a date sort would show and the first thing relevance shows.
        params = {"q": '"%s"' % t["query"] if t["priority"] != "4_DOCTRINE"
                  else t["query"],
                  "type": t["search_type"]}
        reqs.append((t["target_id"], API + "/search/?" + urllib.parse.urlencode(params)))
    res, stopped = _metered(led, reqs, "search", "search")

    by_id = {t["target_id"]: t for t in todo}
    hits = read_csv(HITS)
    man = []
    for key, status, js in res:
        t = by_id[key]
        man.append({"request_key": key, "kind": "search", "status": str(status),
                    "query": t["query"], "search_type": t["search_type"],
                    "reported_count": (js or {}).get("count", ""),
                    "retrieved": len((js or {}).get("results") or []),
                    "when": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        if js is None:
            hits.append({"target_id": key, "query": t["query"],
                         "search_type": t["search_type"],
                         "priority": t["priority"], "cedar_uid": t["cedar_uid"],
                         "obligor_label_1082": t["obligor_label_1082"],
                         "obligor_name": t["obligor_name"],
                         "question": t["question"],
                         "outcome": f"REQUEST_REFUSED {status}"})
            continue
        cache_write(cache_path("search", key), js)
        # class 4: retrieved-vs-reported is recorded on every query, inside
        # hit_rows, so the cache and the live pass cannot drift.
        hits.extend(hit_rows(t, js))
    write_csv(HITS, hits)
    manifest_append(man)
    release_host(f"search complete; stopped={stopped}")
    d, h, _ = spent_counts(led)
    log(f"{len(res)} requests sent; {len(hits)} hit rows; budget now {d}/{PER_DAY} today")
    if stopped:
        log(f"STOPPED EARLY: {stopped}")
    return 0


def hit_rows(t, js):
    """Turn one cached search response into hit rows.  Separate from the fetch
    so `remine` can re-derive every field from the cache with ZERO requests -
    `docket_absolute_url`, `cause`, `chapter` and `dateTerminated` were all
    already on disk when the first pass wrote a blank `source_url`."""
    key = t["target_id"]
    results = js.get("results") or []
    reported = js.get("count")
    completeness = ("COMPLETE" if reported is not None and len(results) >= int(reported)
                    else f"PARTIAL retrieved={len(results)} reported={reported}")
    base = {"target_id": key, "query": t["query"],
            "search_type": t["search_type"], "priority": t["priority"],
            "cedar_uid": t["cedar_uid"],
            "obligor_label_1082": t["obligor_label_1082"],
            "obligor_name": t["obligor_name"], "question": t["question"],
            "completeness": completeness, "reported_count": reported}
    if not results:
        return [dict(base, outcome="NO_RESULT")]
    out = []
    for r in results:
        url = r.get("absolute_url") or r.get("docket_absolute_url") or ""
        out.append(dict(
            base, outcome="RESULT",
            cluster_id=r.get("cluster_id", ""),
            docket_id=r.get("docket_id", ""),
            case_name=r.get("caseName", ""),
            court=r.get("court", ""),
            court_id=r.get("court_id", ""),
            citation=" | ".join(r.get("citation") or []),
            date_filed=r.get("dateFiled", ""),
            date_terminated=r.get("dateTerminated") or "",
            docket_number=r.get("docketNumber", ""),
            precedential_status=r.get("status", ""),
            cause=r.get("cause") or "",
            bankruptcy_chapter=r.get("chapter") or "",
            absolute_url=("https://www.courtlistener.com" + url) if url else "",
            suit_nature=r.get("suitNature", ""),
            sub_ids=" | ".join(str(s.get("id")) for s in (r.get("opinions") or [])
                               if s.get("id") is not None),
            party=" | ".join(r.get("party") or []),
            n_recap_documents=len(r.get("recap_documents") or []),
            snippet=((((r.get("opinions") or r.get("recap_documents")
                        or [{}]))[0]).get("snippet") or "")[:600],
        ))
    return out


def step_remine():
    """Re-derive every hit row from the cached responses.  ZERO requests."""
    targets = {t["target_id"]: t for t in read_csv(TARGETS)}
    hits, n = [], 0
    for p in sorted(RAW.glob("search_*.json.gz")):
        key = p.name[len("search_"):-len(".json.gz")]
        t = targets.get(key)
        if not t:
            log(f"  cached response {key} has no target row; skipped")
            continue
        hits.extend(hit_rows(t, cache_read(p)))
        n += 1
    if not n:
        raise RuntimeError("no cached search responses - UNMEASURED, not empty")
    write_csv(HITS, hits)
    log(f"remined {n} cached responses -> {len(hits)} hit rows (0 requests)")
    return 0


# ------------------------------------------------- opinion full text fetch
# A snippet is not a quote.  To characterise anything we need the court's own
# words, so the shortlisted opinions are fetched whole and cached.
DEBT_WORDS = re.compile(
    r"\b(indenture|bond|note[s]?|noteholder|debenture|loan|credit agreement|"
    r"forbearance|default|restructur|receiver|trustee|principal|interest|"
    r"amortiz|maturit|refinanc|acceleration|accelerate)\b", re.I)

# A caption is evidence in itself.  `Wells Fargo Bank, N.A. v. Chukchansi
# Economic Development Authority` is a debt case on its face and its snippet
# happens to open on a procedural sentence with no debt word in it - the first
# draft of this filter rejected it, and that is the single most important
# Chukchansi opinion in the corpus.  A snippet is the first ~600 characters of
# a document, not a summary of it, and filtering on it alone measures where the
# opinion starts rather than what it is about.
FINANCIAL_PARTY = re.compile(
    r"\b(bank|bancorp|banco|trust co|trust company|trustee|indenture|"
    r"bondholder|noteholder|capital|investors?|funding|finance|financial|"
    r"credit|securities|savings|lender|mortgage|n\.a\.)\b", re.I)
FINANCIAL_SUIT_NATURE = re.compile(
    r"(contract|consumer credit|securities|bankruptcy|negotiable instrument|"
    r"recovery of overpayment|foreclosure)", re.I)

# WORD BOUNDARIES, not containment.  1082 admitted a South Carolina paper-mill
# conduit issuer because `"nation"` is a substring of `"INTERnationAL"`.  The
# same bug is available here and this is the same fix.
TRIBAL_GENERIC = re.compile(
    r"\b(tribe|tribes|tribal|nation|band|pueblo|rancheria|indian|indians|"
    r"chippewa|sioux|apache|navajo|cherokee|creek|choctaw|seminole|"
    r"reservation|ranchería|native village|community of|gaming authority)\b",
    re.I)
_TRIBAL_NAME_RX = None


def tribal_name_lexicon():
    """Distinctive spine name tokens, so a caption naming `Nooksack Business
    Corp` reads as tribal even though it carries no generic tribal word."""
    global _TRIBAL_NAME_RX
    if _TRIBAL_NAME_RX is not None:
        return _TRIBAL_NAME_RX
    generic = {
        "tribe", "tribes", "tribal", "nation", "band", "indian", "indians",
        "pueblo", "rancheria", "village", "native", "community", "council",
        "reservation", "corporation", "incorporated", "company", "authority",
        "development", "economic", "enterprises", "enterprise", "gaming",
        "casino", "resort", "united", "states", "america", "north", "south",
        "eastern", "western", "northern", "southern", "upper", "lower",
        "confederated", "federated", "association", "consortium", "district",
        "county", "city", "town", "school", "health", "housing", "services",
        "group", "holdings", "of", "the", "and", "for", "inc", "llc",
    }
    toks = set()
    p = SPINE / "cedar_entity_spine.csv"
    if p.exists():
        for r in read_csv(p):
            for t in re.findall(r"[A-Za-z']{6,}", r.get("canonical_name") or ""):
                if t.lower() not in generic:
                    toks.add(t.lower())
    if not toks:
        raise RuntimeError(
            "the spine produced NO tribal name tokens - UNMEASURED, not empty. "
            "Refusing to score every caption non-tribal.")
    _TRIBAL_NAME_RX = re.compile(
        r"\b(" + "|".join(sorted(re.escape(t) for t in toks)) + r")\b", re.I)
    return _TRIBAL_NAME_RX


def tribal_in_caption(caption):
    m = TRIBAL_GENERIC.search(caption or "")
    if m:
        return f"generic tribal word {m.group(0)!r} in the caption"
    m = tribal_name_lexicon().search(caption or "")
    if m:
        return f"spine entity name token {m.group(0)!r} in the caption"
    return ""


def shortlist(hits):
    """Which opinions are worth a whole-document request.

    A hit qualifies when the query name (or the obligor name) appears in the
    CASE NAME and the snippet carries debt vocabulary, or when the target is a
    doctrine query and the snippet carries debt vocabulary.  Everything else
    is written to review/1110_rejected_hits.csv with the reason - a refusal is
    recorded, never silently dropped.
    """
    keep, drop = [], []
    for h in hits:
        if h.get("outcome") != "RESULT" or h.get("search_type") != "o":
            continue
        if not h.get("sub_ids"):
            drop.append(dict(h, reject_reason="no opinion id on the cluster"))
            continue
        cap_only = h.get("case_name", "")

        # 1. the natural-person screen runs FIRST, so a held caption never
        #    costs a request either.
        pm = PERSON_SHAPE.search(cap_only)
        if pm:
            drop.append(dict(h, reject_reason=(
                f"natural-person screen: caption carries {pm.group(0)!r}")))
            continue

        # 2. SUBJECT.  A search hit is not a party (the code/219
        #    Seminole-as-a-surname rule).
        why = []
        if h["priority"] == "4_DOCTRINE":
            t = tribal_in_caption(cap_only)
            if not t:
                drop.append(dict(h, reject_reason=(
                    "doctrine query, and no tribal party in the caption - "
                    "Hexion Specialty Chemicals is not tribal debt")))
                continue
            why.append(t)
            # the doctrine query's own terms ARE the debt test: the engine
            # matched "indenture", "default", "receiver" in the DOCUMENT, which
            # is a stronger statement than anything the snippet can make.
            why.append("doctrine query matched debt terms in the full document text")
        else:
            want = norm(h["query"])
            cap = norm(cap_only)
            if want not in cap and norm(h.get("obligor_name", "")) not in cap:
                drop.append(dict(h, reject_reason=(
                    "query name absent from the caption - a search hit is not "
                    "a party (the code/219 Seminole-as-a-surname rule)")))
                continue
            why.append("the queried obligor is named in the caption")

            # 3. DEBT.  Only the name queries need it; a name query returns a
            #    tribe's whole docket, most of which is torts and employment.
            text = " ".join([cap_only, h.get("snippet", ""), h.get("suit_nature", "")])
            debt = []
            if DEBT_WORDS.search(text):
                debt.append("debt vocabulary in caption/snippet/suitNature")
            if FINANCIAL_PARTY.search(cap_only):
                debt.append("a financial institution is a named party in the caption")
            if FINANCIAL_SUIT_NATURE.search(h.get("suit_nature", "")):
                debt.append("suitNature is a contract/credit/securities nature")
            if not debt:
                drop.append(dict(h, reject_reason=(
                    "no debt vocabulary, no financial party in the caption and "
                    "no contract-shaped suitNature")))
                continue
            why += debt
        keep.append(dict(h, shortlist_basis="; ".join(why)))
    return keep, drop


def step_opinions(max_requests):
    if not TOKEN:
        log("NO TOKEN. Refusing to run.")
        return 2
    hits = read_csv(HITS)
    keep, drop = shortlist(hits)
    write_csv(REJECTED, drop)
    log(f"shortlist: {len(keep)} opinion clusters worth a whole-document "
        f"request; {len(drop)} rejected (recorded, not dropped)")
    want = []
    seen = set()
    for h in keep:
        for oid in (h.get("sub_ids") or "").split(" | "):
            oid = oid.strip()
            if oid and oid not in seen:
                seen.add(oid)
                want.append((oid, h))
    have = {p.name.split("_", 1)[1].rsplit(".json", 1)[0]
            for p in RAW.glob("opinion_*.json.gz")}
    todo = [(oid, h) for oid, h in want if oid not in have]
    log(f"{len(want)} opinion documents wanted, {len(want) - len(todo)} already cached")
    if not todo:
        return 0
    led = load_spend()
    d, h_, _ = spent_counts(led)
    room = max(0, min(PER_DAY - d, PER_HOUR - h_, max_requests))
    log(f"budget: {d}/{PER_DAY} today, {h_}/{PER_HOUR} this hour -> room {room}")
    if room <= 0:
        return 0
    todo = todo[:room]
    if not claim_host(f"opinion full-text fetch, {len(todo)} requests"):
        return 3
    reqs = [(oid, f"{API}/opinions/{oid}/") for oid, _ in todo]
    res, stopped = _metered(led, reqs, "opinion", "opinions")
    man = []
    for key, status, js in res:
        man.append({"request_key": f"opinion_{key}", "kind": "opinion",
                    "status": str(status), "query": "", "search_type": "",
                    "reported_count": "", "retrieved": 1 if js else 0,
                    "when": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        if js:
            cache_write(cache_path("opinion", key), js)
    manifest_append(man)
    release_host(f"opinion fetch complete; stopped={stopped}")
    if stopped:
        log(f"STOPPED EARLY: {stopped}")
    return 0


# ================================================================== BUILD
# Typing is done ONLY by an explicit phrase rule and the phrase that fired is
# recorded.  Order matters: the FIRST rule that fires wins, and the rules are
# ordered so that "held void / unenforceable" beats "default", because that is
# exactly the Lake of the Torches trap.
EVENT_RULES = [
    ("LITIGATION_OUTCOME_INSTRUMENT_HELD_VOID_OR_UNENFORCEABLE",
     r"(management contract[^.]{0,200}?(void|unenforceable|invalid)"
     r"|(void|unenforceable|invalid)[^.]{0,200}?management contract"
     r"|indenture[^.]{0,160}?(is|was|be|were)[^.]{0,40}?(void|unenforceable|invalid))"),
    ("LITIGATION_OUTCOME_SOVEREIGN_IMMUNITY_BARS_THE_CLAIM",
     r"(sovereign immunity[^.]{0,200}?(bar|dismiss|lack(s|ed)? jurisdiction)"
     r"|(did not|has not|no)[^.]{0,60}?waive[d]?[^.]{0,80}?immunity)"),
    ("LITIGATION_OUTCOME_WAIVER_OF_IMMUNITY_ENFORCED",
     r"(waiver of (its )?sovereign immunity[^.]{0,200}?(valid|effective|enforceable|clear and unequivocal))"),
    ("RECEIVERSHIP",
     r"(appoint\w*[^.]{0,120}?receiver|receiver was appointed|receivership)"),
    ("BANKRUPTCY_OR_INSOLVENCY_PROCEEDING",
     r"(chapter (7|9|11)\b|bankruptcy petition|debtor[- ]in[- ]possession)"),
    ("RESTRUCTURING_OR_EXCHANGE",
     r"(restructur\w+|exchange offer|debt exchange|refinanc\w+|"
     r"amended and restated (indenture|credit agreement))"),
    ("FORBEARANCE",
     r"(forbearance agreement|agreed to forbear|forbear\w+ from exercising)"),
    ("ACCELERATION",
     r"(declare[d]? .{0,60}?(immediately )?due and payable|accelerat\w+ the (notes|loan|indebtedness))"),
    ("DEFAULT_ASSERTED_OR_FOUND",
     r"(event of default|in default (on|under)|failed to (make|pay)[^.]{0,80}?"
     r"(payment|interest|principal))"),
]
EVENT_RULES = [(n, re.compile(p, re.I | re.S)) for n, p in EVENT_RULES]

# A caption shaped like an individual matter is HELD, never staged.
PERSON_SHAPE = re.compile(
    r"\b(per capita|disenroll|wrongful (death|termination|discharge)|"
    r"employment discrimination|personal injury|slip and fall|"
    r"habeas|in re marriage|adoption of|estate of|guardianship)\b", re.I)

ORG_MARKER = re.compile(
    r"\b(inc|incorporated|llc|l\.l\.c|corp|corporation|co|company|bank|n\.a|"
    r"authority|nation|tribe|tribal|band|pueblo|rancheria|trust|association|"
    r"lp|l\.p|llp|group|enterprises?|holdings?|partners|fund|funds|"
    r"united states|state of|people of|commonwealth|county|city of|"
    r"department|commission|board|bureau|secretary|university|"
    r"casino|resort|gaming|services|systems|management|capital|"
    r"investors?|securities|financial|savings|credit union)\b", re.I)


def side_is_a_natural_person(side):
    """A caption side with no organisational marker and at most three tokens is
    almost certainly a person.  Deliberately conservative: it errs towards
    calling something a person, because the cost of that error is a held row
    and the cost of the opposite error is publishing a private individual."""
    s = re.sub(r"[,.]", " ", side or "").strip()
    if not s:
        return False
    if ORG_MARKER.search(side or ""):
        return False
    return len(s.split()) <= 3


_CAP_STOP = {"co", "company", "inc", "incorporated", "llc", "lc", "lp", "llp",
             "na", "n", "a", "national", "association", "assn", "ass", "corp",
             "corporation", "the", "of", "and", "sc", "pc", "ltd", "limited",
             "et", "al", "state"}


def caption_key(caption):
    """A caption written by a clerk and a caption written by a reporter of
    decisions are the same case in different clothes: `Stifel, Nicolaus & Co.`
    and `Stifel, Nicolaus & Company, Inc.`  Strip the clothes."""
    toks = [t for t in norm(caption).split() if t not in _CAP_STOP]
    return " ".join(toks)


def caption_key_match(a, b):
    a, b = caption_key(a), caption_key(b)
    if not a or not b:
        return False
    return a == b or a.startswith(b[:45]) or b.startswith(a[:45])


def caption_sides(caption):
    parts = re.split(r"\s+v[\.s]?\.?\s+", caption or "", maxsplit=1, flags=re.I)
    return (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (caption or "", "")


INSTRUMENT_RX = re.compile(
    r"\b(indentures?|bonds?|senior notes?|secured notes?|notes?|debentures?|"
    r"credit agreements?|loan agreements?|term loans?|loans?|"
    r"promissory notes?|forbearance agreements?|trust agreements?|"
    r"security agreements?|guarant(?:y|ee|ies)|leases?|"
    r"equipment financing|line of credit)\b", re.I)

AMOUNT = re.compile(
    r"\$\s?([0-9][0-9,]*(?:\.[0-9]+)?)\s*(billion|million|thousand)?", re.I)


def find_sentences(text, rx, window=1):
    """Return whole sentences containing a match.  A verbatim quote must be a
    sentence, not a regex span - a clipped span is how a characterisation gets
    invented."""
    out = []
    parts = re.split(r"(?<=[.;])\s+", text)
    for i, p in enumerate(parts):
        if rx.search(p):
            lo = max(0, i - (window - 1))
            out.append(" ".join(parts[lo:i + 1]).strip())
    return out


def strip_tags(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html or "")
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = (html.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">")
                .replace("&#8217;", "'").replace("&quot;", '"'))
    return re.sub(r"\s+", " ", html).strip()


def opinion_text(js):
    for k in ("plain_text", "html_with_citations", "html", "html_lawbox",
              "html_columbia", "xml_harvard", "html_anon_2020"):
        v = js.get(k)
        if v and str(v).strip():
            return (strip_tags(v) if k != "plain_text"
                    else re.sub(r"\s+", " ", v)), k
    return "", "NO_TEXT_FIELD_POPULATED"


ALLEGATION_CUE = re.compile(
    r"\b(allege[sd]?|alleging|complaint (states|asserts|alleges)|"
    r"plaintiff (claims|contends|asserts)|according to the complaint|"
    r"purport(s|ed|edly))\b", re.I)
FINDING_CUE = re.compile(
    r"\b(we hold|we conclude|the court (finds|holds|concludes)|"
    r"it is (hereby )?ordered|we affirm|we reverse|we vacate|"
    r"judgment is entered|the district court (found|held|concluded))\b", re.I)


def classify_speaker(sentence):
    if ALLEGATION_CUE.search(sentence):
        return ("ALLEGATION_BY_A_PARTY",
                "the sentence carries an allegation cue - a party asserts this, "
                "a court has not found it")
    if FINDING_CUE.search(sentence):
        return ("COURT_FINDING",
                "the sentence carries a holding cue - this is the court speaking")
    return ("PROCEDURAL_RECORD",
            "the sentence recites the record without a holding or allegation cue; "
            "read the document before characterising it")


def load_holdings_index():
    idx = {}
    p = STAGING / "tribal_debt_obligors.csv"
    for r in read_csv(p):
        idx[r["obligor_label"]] = r
    return idx


_SPINE_ROWS = None


def spine_rows():
    global _SPINE_ROWS
    if _SPINE_ROWS is None:
        _SPINE_ROWS = read_csv(SPINE / "cedar_entity_spine.csv")
        if not _SPINE_ROWS:
            raise RuntimeError("the spine is empty - UNMEASURED, not unresolved")
    return _SPINE_ROWS


def resolve_obligor_from_caption(caption):
    """Whole-token-run containment of a spine canonical name in the caption.

    TIER B, and DESCRIPTIVE ONLY.  `AGENTS.md` forbids containment from keying a
    dollar and it keys none here: no money in this table is attributed to an
    entity by this link.  The longest match wins so that `Lac du Flambeau Band
    of Lake Superior Chippewa Indians` beats `Lac du Flambeau`.
    """
    cap = " " + norm(caption) + " "
    best = None
    for r in spine_rows():
        nm = norm(r.get("canonical_name") or "")
        if len(nm) < 6:
            continue
        if (" " + nm + " ") in cap:
            if best is None or len(nm) > len(best[0]):
                best = (nm, r)
    if not best:
        return "", "", "", ""
    nm, r = best
    return (r.get("cedar_uid", ""), r.get("tribe_id", ""),
            r.get("canonical_name", ""),
            f"spine_canonical_name_{nm!r}_is_a_whole_token_run_inside_the_"
            f"court_caption_CONTAINMENT_descriptive_only_never_keys_a_dollar")


def build_dockets(hits, holdings, event_captions=()):
    """The docket index: court, docket number, date filed, party array.

    This is where the mandate's "court and docket number" actually lives - a
    published opinion frequently omits the district docket number, and the
    RECAP index always carries it.  Zero extra requests: every field is already
    in the search response.

    THE PARTY ARRAY IS THE CLERK OF COURT, and it is the only verification that
    counts (code/366): a name in a caption is not a party, and `code/219`'s
    `Seminole v. Berkebile` is a prisoner case about a surname.

    EVERY DOCKET WITH A NATURAL PERSON IN ITS PARTY ARRAY IS DROPPED.  The
    Lake of the Torches query alone returns four consumer payday-lending
    dockets - `Morgan v. West Side Lending`, `KNOTTS v. CRANE LENDING`,
    `RANSOM v. GREATPLAINS FINANCE`, `Mee v. Clarity Services` - in which a
    tribal lender is the CREDITOR and the borrower is a private individual.
    That is neither tribal debt distress nor anything a private person's name
    belongs in.
    """
    rows, dropped = [], []
    seen = set()
    for h in hits:
        if h.get("search_type") != "r" or h.get("outcome") != "RESULT":
            continue
        did = h.get("docket_id", "")
        if not did or did in seen:
            continue
        cap = h.get("case_name", "")
        parties = [p.strip() for p in (h.get("party") or "").split(" | ") if p.strip()]

        persons = [p for p in parties if side_is_a_natural_person(p)]
        if persons or PERSON_SHAPE.search(cap):
            dropped.append(dict(h, reject_reason=(
                "a natural person is in the party array or the caption: "
                + "; ".join(persons[:4] or [cap]))))
            continue
        if not parties:
            dropped.append(dict(h, reject_reason=(
                "no party array on this docket - a caption is not a party "
                "(code/366), so there is nothing to verify against")))
            continue

        blob = cap + " | " + " | ".join(parties)
        fin = FINANCIAL_PARTY.search(blob)
        # A DOCKET WHOSE OPINION IS ALREADY STAGED IS A DEBT DOCKET, and the
        # opinion is better evidence of that than any docket metadata.
        # `Stifel, Nicolaus & Co. v. Lac du Flambeau` is docketed
        # `950 Constitutional - State Statute` and is a bond case.
        opinion_backed = any(caption_key_match(cap, c) for c in event_captions)
        #
        # THE NATURE-OF-SUIT CODE WAS TRIED AS A THIRD ROUTE AND IS REFUSED.
        # It admitted `State of Wisconsin v. Ho-Chunk Nation`,
        # `State of California v. Paskenta Band of Nomlaki Indians`,
        # `California Valley Miwok Tribe v. California Gambling Control
        # Commission` and three `... v. Iipay Nation of Santa Ysabel` dockets
        # - all coded `Contract: Other`, every one a compact or regulatory
        # dispute with no lender, no instrument and no debt. The code measures
        # which box the filer ticked on a civil cover sheet, not whether
        # anybody lent anybody money: this repo's signature defect, a check
        # that does not measure its own name. Recorded so it is not re-added.
        signal = ("a financial institution is a party: " + fin.group(0)) if fin \
            else ("an opinion in this case is already staged as a debt "
                  "event") if opinion_backed else ""
        if not signal:
            dropped.append(dict(h, reject_reason=(
                "no financial institution among the parties and no staged "
                "opinion - a docket of the tribe's, not a debt docket. "
                "suitNature was deliberately NOT used as a signal: it admitted "
                "six compact/regulatory dockets coded 'Contract: Other'.")))
            continue

        # THE OBLIGOR IS RESOLVED FROM THE DOCUMENT: the clerk's party array
        # first, the caption second.  Never from the query that found it.
        ob_uid, ob_handle, ob_name, ob_method = "", "", "", ""
        for p in parties:
            u, hd, nm, mth = resolve_obligor_from_caption(p)
            if u and (not ob_name or len(nm) > len(ob_name)):
                ob_uid, ob_handle, ob_name = u, hd, nm
                ob_method = ("the CLERK OF COURT's party array names this "
                             "entity: " + mth)
        match_class = "VERIFIED_PARTY" if ob_uid else ""
        if not ob_uid:
            ob_uid, ob_handle, ob_name, ob_method = resolve_obligor_from_caption(cap)
            if ob_uid:
                match_class = "NAME_IN_CAPTION_ONLY"
        want = norm(h.get("query", ""))
        in_party = any(want and (want in norm(p) or norm(p) in want) for p in parties)
        in_caption = bool(want) and want in norm(cap)
        if not ob_uid and h.get("cedar_uid") and (in_party or in_caption):
            ob_uid = h["cedar_uid"]
            ob_name = h.get("obligor_name", "")
            ob_method = ("the obligor this docket was sought for is named in "
                         "its party array or caption")
            match_class = "VERIFIED_PARTY" if in_party else "NAME_IN_CAPTION_ONLY"
            for r in spine_rows():
                if r.get("cedar_uid") == ob_uid:
                    ob_handle = r.get("tribe_id", "")
                    break
        if not ob_uid:
            dropped.append(dict(h, reject_reason=(
                "no Cedar entity in the party array or the caption")))
            continue

        # WHICH SIDE IS THE NATION ON.  A nation sued BY a bank is the
        # distress shape; a nation suing its own investment manager
        # (`Picayune Rancheria v. Goldenwise Capital Management`) is not, and
        # nothing in a docket number tells them apart.
        pl_side, df_side = caption_sides(cap)
        nname = norm(ob_name)
        on_pl = bool(nname) and nname in norm(pl_side)
        on_df = bool(nname) and nname in norm(df_side)
        role = ("DEFENDANT" if on_df and not on_pl else
                "PLAINTIFF" if on_pl and not on_df else "BOTH_OR_UNCLEAR")
        role_basis = (
            f"the resolved entity name {ob_name!r} appears on the "
            f"{'defendant' if role == 'DEFENDANT' else 'plaintiff' if role == 'PLAINTIFF' else 'unclear'}"
            f" side of the court's own caption. DEFENDANT beside a lender is "
            f"the distress shape; PLAINTIFF is not, on its own, distress at all.")

        lbl = h.get("obligor_label_1082", "") if (in_party or in_caption) else ""
        hold_row = holdings.get(lbl, {})
        seen.add(did)
        rows.append({
            "docket_row_id": f"TDCD-{h.get('court_id','')}-{did}",
            "obligor_name": ob_name,
            "obligor_cedar_uid": ob_uid,
            "obligor_cedar_handle": ob_handle,
            "obligor_entity_match_method": ob_method,
            "obligor_entity_tier": "B",
            "obligor_label_1082": lbl,
            "joins_1082_holdings": "yes" if hold_row else "no",
            "holdings_observations_1082": hold_row.get("observations", ""),
            "holdings_cusips_1082": hold_row.get("cusips", ""),
            "event_type": "CASE_FILED_IN_A_COURT_OF_RECORD",
            "event_type_basis": ("the docket exists and carries a filing date; "
                                 "NOTHING about its outcome is asserted here"),
            "assertion_or_finding": "PROCEDURAL_RECORD",
            "assertion_or_finding_basis": (
                "a docket is the court's index of a case. A complaint on it "
                "ALLEGES; only a judgment FINDS. Read the documents before "
                "characterising anything."),
            "as_of_date": h.get("date_filed", ""),
            "as_of_date_basis": "the date the case was filed, per CourtListener/RECAP",
            "court": h.get("court", ""),
            "court_id": h.get("court_id", ""),
            "docket_number": h.get("docket_number", ""),
            "case_name_as_captioned": cap,
            "parties_as_recorded_by_the_clerk": " | ".join(parties),
            "debt_signal_basis": signal,
            "tribal_party_role": role,
            "tribal_party_role_basis": role_basis,
            "match_class": match_class,
            "n_recap_documents_indexed": h.get("n_recap_documents", ""),
            "docket_id": did,
            "source_authority": "CourtListener / Free Law Project RECAP index, REST API v4",
            "source_document_type": "COURT_DOCKET_SHEET",
            "source_url": h.get("absolute_url", ""),
            "sovereign_immunity_caution": SOVEREIGN_CAUTION,
            "currency_caution": CURRENCY_CAUTION,
            "not_summable_with": NOT_SUMMABLE,
            "assertion_class": "COURT_RECORD_DOCKET_INDEX",
            "record_scope": "ONE DOCKET IN ONE COURT",
            "built_by_script": f"code/{SCRIPT}",
            "built_date": TODAY,
        })
    return rows, dropped


def step_build():
    hits = read_csv(HITS)
    holdings = load_holdings_index()
    # One opinion is returned by several queries.  Pick the hit whose QUERY is
    # actually in the caption - first-wins handed `Saybrook Tax Exempt
    # Investors, LLC v. Lake of Torches` to the Lac du Flambeau full-text
    # query, which then failed the caption test and dropped a real case.
    by_opinion = {}
    for h in hits:
        for oid in (h.get("sub_ids") or "").split(" | "):
            oid = oid.strip()
            if not oid:
                continue
            cur = by_opinion.get(oid)
            named = norm(h.get("query", "")) in norm(h.get("case_name", ""))
            if cur is None or (named and norm(cur.get("query", ""))
                               not in norm(cur.get("case_name", ""))):
                by_opinion[oid] = h

    docs, events, held, rejected_events = [], [], [], []
    n_text = 0
    for p in sorted(RAW.glob("opinion_*.json.gz")):
        oid = p.name[len("opinion_"):-len(".json.gz")]
        js = cache_read(p)
        h = by_opinion.get(oid, {})
        text, text_field = opinion_text(js)
        if text:
            n_text += 1
        caption = h.get("case_name", "") or js.get("case_name", "")
        docs.append({
            "document_id": f"CLOP-{oid}",
            "opinion_id": oid,
            "cluster_id": h.get("cluster_id", ""),
            "case_name_as_captioned": caption,
            "court": h.get("court", ""),
            "court_id": h.get("court_id", ""),
            "docket_number": h.get("docket_number", ""),
            "date_filed": h.get("date_filed", ""),
            "citation": h.get("citation", ""),
            "precedential_status": h.get("precedential_status", ""),
            "document_type": "JUDICIAL_OPINION",
            "source_authority": "CourtListener / Free Law Project REST API v4",
            "source_url": h.get("absolute_url", ""),
            "api_url": f"{API}/opinions/{oid}/",
            "text_field_used": text_field,
            "text_chars": len(text),
            "cached_at": p.name,
            "terms_basis": ("a court opinion is the COURT's record, not the "
                            "tribe's - docs/PUBLICATION_POLICY.md TERMS-SCOPE, "
                            "the distinction is authorship, not subject matter"),
            "built_by_script": f"code/{SCRIPT}",
            "built_date": TODAY,
        })
        if not text:
            continue

        pm = PERSON_SHAPE.search(caption)
        if pm:
            held.append({
                "opinion_id": oid, "case_name_as_captioned": caption,
                "hold_reason": ("caption is shaped like an individual matter, "
                                "not a debt matter - a natural person's data "
                                "held apart from a public role is never staged"),
                "matched_phrase": pm.group(0),
                "built_by_script": f"code/{SCRIPT}", "built_date": TODAY})
            continue

        # THE DEBTOR-SIDE PERSON SCREEN.  `Mashantucket Pequot Gaming
        # Enterprise v. Renzulli` is a tribal enterprise collecting from a
        # PATRON.  The debt in that case is a private individual's, the
        # obligor is not the nation, and it belongs in neither direction of
        # this table.  A person on the PLAINTIFF side (a contractor suing a
        # tribe) is a counterparty in a public commercial case and stays,
        # flagged.
        plaintiff, defendant = caption_sides(caption)
        if side_is_a_natural_person(defendant) and not side_is_a_natural_person(plaintiff):
            held.append({
                "opinion_id": oid, "case_name_as_captioned": caption,
                "hold_reason": ("the DEBTOR side of this caption is a natural "
                                "person - the obligor is an individual, not a "
                                "nation, and an individual's debt is never "
                                "staged"),
                "matched_phrase": defendant,
                "built_by_script": f"code/{SCRIPT}", "built_date": TODAY})
            continue
        person_flag = ("yes" if (side_is_a_natural_person(plaintiff)
                                 or side_is_a_natural_person(defendant)) else "no")
        person_flag_basis = (
            "a natural person appears in the court's own caption of a filed "
            "commercial case, on the CREDITOR/claimant side. The caption is the "
            "court's public record; nothing about this person is published "
            "beyond it." if person_flag == "yes" else
            "every side of the caption carries an organisational marker")

        # THE OBLIGOR COMES FROM THE DOCUMENT, NEVER FROM THE QUERY THAT FOUND
        # IT.  CourtListener searches FULL TEXT, so the query
        # "Lac du Flambeau Band of Lake Superior Chippewa Indians" returns
        # `Outsource Services Management, LLC v. Nooksack Business Corp.` and
        # `Colombe v. Rosebud Sioux Tribe` - because those opinions CITE the
        # Lake of the Torches decisions.  The first draft of this build read
        # the obligor off the target row and attributed Nooksack's loan and
        # Rosebud's to Lac du Flambeau.  A citation is not a party, exactly as
        # a caption is not a party (code/219).  Caught by reading the
        # twenty-five-row table end to end, not by any check.
        obligor_label = h.get("obligor_label_1082", "")
        ob_uid = ob_handle = ob_name = ob_method = ob_tier = ""
        ncap = norm(caption)
        if (h.get("cedar_uid")
                and (norm(h.get("query", "")) in ncap
                     or norm(h.get("obligor_name", "")) in ncap)):
            ob_uid = h["cedar_uid"]
            ob_name = h.get("obligor_name", "")
            ob_tier = "B"
            ob_method = ("the obligor this case was sought for is NAMED IN THE "
                         "CAPTION of this document")
            for r in spine_rows():
                if r.get("cedar_uid") == ob_uid:
                    ob_handle = r.get("tribe_id", "")
                    if not ob_name:
                        ob_name = r.get("canonical_name", "")
                    break
        else:
            obligor_label = ""      # a 1082 join follows the obligor, not the query
            ob_uid, ob_handle, ob_name, ob_method = resolve_obligor_from_caption(caption)
            if ob_uid:
                ob_tier = "B"
        if not ob_uid:
            rejected_events.append({
                "opinion_id": oid, "case_name_as_captioned": caption,
                "would_be_event_type": "(all)",
                "reject_reason": ("no Cedar entity is named in this caption. The "
                                  "document reached the shortlist through a "
                                  "full-text citation, not because a tribal "
                                  "obligor is a party to it."),
                "passage": "", "built_by_script": f"code/{SCRIPT}",
                "built_date": TODAY})
            continue
        hold_row = holdings.get(obligor_label, {})
        for ev_name, rx in EVENT_RULES:
            sents = find_sentences(text, rx)
            if not sents:
                continue
            # ONE event row per (document, event_type).  Several sentences
            # supporting one type is one event with the strongest quote, not
            # several events - counting sentences would inflate the record.
            #
            # "Strongest" is the COURT SPEAKING, then a sentence that names the
            # instrument, then length.  Sorting by length alone picked
            # recitations of the record over holdings and made
            # `assertion_or_finding` read PROCEDURAL_RECORD on cases that
            # plainly hold something.
            sents.sort(key=lambda s: (bool(FINDING_CUE.search(s)),
                                      bool(INSTRUMENT_RX.search(s)), len(s)),
                       reverse=True)
            quote = sents[0][:1200]
            # QUOTE THE INSTRUMENT.  If the sentence that fired does not name
            # the instrument, widen the window once; if it still does not, the
            # event is REFUSED rather than staged with a bare characterisation.
            if not INSTRUMENT_RX.search(quote):
                wider = find_sentences(text, rx, window=3)
                wider.sort(key=len, reverse=True)
                if wider and INSTRUMENT_RX.search(wider[0]):
                    quote = wider[0][:1500]
            instruments = sorted(set(
                w.lower() for w in INSTRUMENT_RX.findall(quote)))
            if not instruments:
                rejected_events.append({
                    "opinion_id": oid, "case_name_as_captioned": caption,
                    "would_be_event_type": ev_name,
                    "reject_reason": ("the passage that fired names no "
                                      "instrument. The mandate is quote the "
                                      "instrument and the court; an event we "
                                      "cannot quote an instrument for is a "
                                      "characterisation, not a record."),
                    "passage": sents[0][:600],
                    "built_by_script": f"code/{SCRIPT}", "built_date": TODAY})
                continue
            m = rx.search(quote) or rx.search(text)
            speaker, speaker_basis = classify_speaker(quote)
            am = AMOUNT.search(quote)
            amt, amt_basis = "", ""
            if am:
                amt = am.group(0).strip()
                amt_basis = ("as recited in the quoted sentence; NOT normalised, "
                             "NOT verified against the instrument")
            events.append({
                "event_id": f"TDCE-{oid}-{ev_name[:24]}",
                "obligor_name": ob_name,
                "obligor_cedar_uid": ob_uid,
                "obligor_cedar_handle": ob_handle,
                "obligor_entity_match_method": ob_method,
                "obligor_entity_tier": ob_tier,
                "obligor_label_1082": obligor_label,
                "joins_1082_holdings": "yes" if hold_row else "no",
                "holdings_observations_1082": hold_row.get("observations", ""),
                "holdings_cusips_1082": hold_row.get("cusips", ""),
                "event_type": ev_name,
                "event_type_basis": (
                    f"phrase rule matched: {(m.group(0) if m else '')[:160]!r}"),
                "assertion_or_finding": speaker,
                "assertion_or_finding_basis": speaker_basis,
                "as_of_date": h.get("date_filed", ""),
                "as_of_date_basis": "the date the opinion was filed, per CourtListener",
                "court": h.get("court", ""),
                "court_id": h.get("court_id", ""),
                "docket_number": h.get("docket_number", ""),
                "case_name_as_captioned": caption,
                "citation": h.get("citation", ""),
                "precedential_status": h.get("precedential_status", ""),
                "instrument_as_described": " | ".join(instruments),
                "instrument_basis": ("every word here appears in "
                                     "verbatim_quote; nothing is inferred"),
                "caption_names_a_natural_person": person_flag,
                "caption_names_a_natural_person_basis": person_flag_basis,
                "amount_as_recited": amt,
                "amount_basis": amt_basis,
                "verbatim_quote": quote,
                "verbatim_quote_scope": ("one whole sentence from the opinion, "
                                         "unedited except for whitespace"),
                "document_id": f"CLOP-{oid}",
                "source_authority": "CourtListener / Free Law Project REST API v4",
                "source_document_type": "JUDICIAL_OPINION",
                "source_url": h.get("absolute_url", ""),
                "sovereign_immunity_caution": SOVEREIGN_CAUTION,
                "currency_caution": CURRENCY_CAUTION,
                "not_summable_with": NOT_SUMMABLE,
                "assertion_class": "COURT_RECORD_JUDICIAL_OPINION",
                "record_scope": "ONE EVENT TYPE IN ONE COURT DOCUMENT",
                "built_by_script": f"code/{SCRIPT}",
                "built_date": TODAY,
            })

    dockets, docket_drops = build_dockets(
        hits, holdings,
        event_captions=[e["case_name_as_captioned"] for e in events])

    # backfill the district docket number onto opinion events.  A published
    # opinion often carries the appellate number or none at all; the RECAP
    # index always carries the district one.  Matched on court + caption, and
    # the source of the number is recorded so it is never mistaken for the
    # opinion's own.
    for e in events:
        d = next((x for x in dockets
                  if caption_key_match(e["case_name_as_captioned"],
                                       x["case_name_as_captioned"])), None)
        # TWO SOURCES DISAGREEING IS A FINDING, NOT A TIE-BREAK.  CourtListener
        # files the district Lake of the Torches opinion under `wied` while its
        # own RECAP docket for the same caption is `wiwd 3:09-cv-00768`
        # (W.D. Wis. 09-cv-768). Both values are kept; neither is overwritten.
        if d and d["court_id"] and e.get("court_id") and d["court_id"] != e["court_id"]:
            e["court_disagreement"] = (
                f"the opinion record files this under {e['court_id']!r} and the "
                f"RECAP docket for the same caption under {d['court_id']!r} "
                f"({d['docket_number']}). Both are CourtListener's. Neither is "
                f"corrected here; check before citing the court.")
        if d:
            e["recap_docket_number"] = d["docket_number"]
            e["recap_docket_url"] = d["source_url"]
        if e.get("docket_number"):
            e["docket_number_basis"] = "as carried by the opinion record"
            continue
        if d:
            e["docket_number"] = d["docket_number"]
            e["docket_number_basis"] = (
                f"NOT from the opinion - taken from the RECAP docket index for "
                f"the same caption in {d['court_id']} "
                f"({d['source_url']})")
        else:
            e["docket_number_basis"] = ("the opinion record carries no docket "
                                        "number and no RECAP docket matched")

    write_csv(DOCS, docs)
    write_csv(EVENTS, events)
    write_csv(DOCKETS, dockets)
    write_csv(HELD, held)
    write_csv(REVIEW / "1110_rejected_events.csv", rejected_events)
    write_csv(REVIEW / "1110_rejected_dockets.csv", docket_drops)

    # what we could not reach, named rather than left as an absence
    unreached = []
    for h in hits:
        if h.get("outcome") in ("NO_RESULT",) or str(h.get("outcome", "")).startswith("REQUEST_REFUSED"):
            unreached.append({
                "query": h.get("query", ""), "search_type": h.get("search_type", ""),
                "obligor_name": h.get("obligor_name", ""),
                "cedar_uid": h.get("cedar_uid", ""),
                "question": h.get("question", ""),
                "outcome": h.get("outcome", ""),
                "state": ("SOURCE_DOES_NOT_PUBLISH - CourtListener's free "
                          "corpus does not hold this matter (state courts, "
                          "tribal courts and unuploaded PACER dockets are "
                          "outside it)" if h.get("outcome") == "NO_RESULT"
                          else "NOT_ACQUIRED - the request was refused"),
                "built_by_script": f"code/{SCRIPT}", "built_date": TODAY})
    write_csv(UNREACHED, unreached)

    log(f"documents {len(docs)}  (with text {n_text})")
    log(f"events    {len(events)}")
    log(f"dockets   {len(dockets)}  ({len(docket_drops)} rejected, recorded)")
    log(f"held by the natural-person screen  {len(held)}")
    log(f"refused for naming no instrument   {len(rejected_events)}")
    log(f"unreached questions                {len(unreached)}")
    return 0


# ================================================================= VERIFY
INVARIANTS = [
    "I1_every_event_names_a_court_and_a_source_url",
    "I2_every_event_is_dated",
    "I3_event_type_is_never_guessed_the_phrase_that_fired_is_recorded",
    "I4_every_event_declares_assertion_or_finding",
    "I5_every_event_carries_the_sovereign_immunity_and_currency_cautions",
    "I6_no_event_asserts_a_summable_total",
    "I7_every_event_carries_a_verbatim_quote_that_is_present_in_the_cached_document",
    "I8_no_event_row_survives_the_natural_person_screen",
    "I9_every_event_quotes_an_instrument_that_appears_in_its_own_quote",
    "I10_entity_tier_is_blank_when_there_is_no_entity_link",
]
DOCKET_INVARIANTS = [
    "D1_every_docket_names_a_court_a_docket_number_and_a_source_url",
    "D2_every_docket_is_dated",
    "D3_no_docket_names_a_natural_person_among_its_parties",
    "D4_every_docket_carries_the_sovereign_and_currency_cautions",
    "D5_every_docket_declares_which_side_of_the_caption_the_nation_is_on",
    "D6_every_docket_records_how_the_entity_was_matched",
]


def _verify_rows():
    events = read_csv(EVENTS)
    breaches = {k: [] for k in INVARIANTS}
    cache = {}
    for e in events:
        eid = e.get("event_id", "?")
        if not e.get("court") or not e.get("source_url"):
            breaches[INVARIANTS[0]].append(eid)
        if not e.get("as_of_date"):
            breaches[INVARIANTS[1]].append(eid)
        if (not e.get("event_type")
                or not e.get("event_type_basis")
                or "phrase rule matched" not in e.get("event_type_basis", "")):
            breaches[INVARIANTS[2]].append(eid)
        if e.get("assertion_or_finding") not in (
                "ALLEGATION_BY_A_PARTY", "COURT_FINDING", "PROCEDURAL_RECORD"):
            breaches[INVARIANTS[3]].append(eid)
        if (SOVEREIGN_CAUTION[:40] not in e.get("sovereign_immunity_caution", "")
                or CURRENCY_CAUTION[:40] not in e.get("currency_caution", "")):
            breaches[INVARIANTS[4]].append(eid)
        if "NEVER sum" not in e.get("not_summable_with", ""):
            breaches[INVARIANTS[5]].append(eid)
        # I7 - the quote must actually be in the cached document.  A quote
        # nobody can re-read is a characterisation.
        q = re.sub(r"\s+", " ", e.get("verbatim_quote", "")).strip()
        oid = e.get("document_id", "").replace("CLOP-", "")
        p = cache_path("opinion", oid)
        if not q or not p.exists():
            breaches[INVARIANTS[6]].append(eid)
        else:
            if oid not in cache:
                cache[oid] = opinion_text(cache_read(p))[0]
            if q[:200] not in cache[oid]:
                breaches[INVARIANTS[6]].append(eid)
        cap = e.get("case_name_as_captioned", "")
        pl, df = caption_sides(cap)
        if (PERSON_SHAPE.search(cap)
                or (side_is_a_natural_person(df) and not side_is_a_natural_person(pl))):
            breaches[INVARIANTS[7]].append(eid)
        # I9 - quote the instrument.  Every word in instrument_as_described
        # must be IN the quote, and there must be at least one.
        inst = [w for w in (e.get("instrument_as_described") or "").split(" | ") if w]
        if not inst or any(w.lower() not in q.lower() for w in inst):
            breaches[INVARIANTS[8]].append(eid)
        # I10 - a tier without a link is a tier about nothing (1082's I5).
        if bool(e.get("obligor_entity_tier")) != bool(e.get("obligor_cedar_uid")):
            breaches[INVARIANTS[9]].append(eid)
    return events, breaches


def _verify_dockets():
    rows = read_csv(DOCKETS)
    breaches = {k: [] for k in DOCKET_INVARIANTS}
    for d in rows:
        did = d.get("docket_row_id", "?")
        if not (d.get("court") and d.get("docket_number") and d.get("source_url")):
            breaches[DOCKET_INVARIANTS[0]].append(did)
        if not d.get("as_of_date"):
            breaches[DOCKET_INVARIANTS[1]].append(did)
        parties = [p.strip() for p in
                   (d.get("parties_as_recorded_by_the_clerk") or "").split(" | ")
                   if p.strip()]
        if (not parties or any(side_is_a_natural_person(p) for p in parties)
                or PERSON_SHAPE.search(d.get("case_name_as_captioned", ""))):
            breaches[DOCKET_INVARIANTS[2]].append(did)
        if (SOVEREIGN_CAUTION[:40] not in d.get("sovereign_immunity_caution", "")
                or CURRENCY_CAUTION[:40] not in d.get("currency_caution", "")
                or "NEVER sum" not in d.get("not_summable_with", "")):
            breaches[DOCKET_INVARIANTS[3]].append(did)
        if d.get("tribal_party_role") not in ("DEFENDANT", "PLAINTIFF",
                                              "BOTH_OR_UNCLEAR"):
            breaches[DOCKET_INVARIANTS[4]].append(did)
        if not d.get("obligor_entity_match_method") or not d.get("match_class"):
            breaches[DOCKET_INVARIANTS[5]].append(did)
    return rows, breaches


def step_verify(quiet=False):
    events, breaches = _verify_rows()
    dockets, dbreaches = _verify_dockets()
    breaches.update(dbreaches)
    bad = 0
    for name in INVARIANTS + DOCKET_INVARIANTS:
        n = len(breaches[name])
        verdict = "ok" if n == 0 else f"BREACH x{n}  e.g. {breaches[name][:3]}"
        if n:
            bad += 1
        if not quiet:
            log("%-70s %s" % (name, verdict))
    if not quiet:
        log(f"event rows checked: {len(events)}   docket rows checked: {len(dockets)}")
    return 1 if bad else 0


def _named_invariant_fired(out, name):
    """Reconstruct the exact line verify prints.  No string arithmetic - the
    366/1082 selftest bug was an offset window that missed the verdict."""
    for line in out.splitlines():
        if line.startswith("%-70s " % name):
            return "BREACH" in line
    return False


def step_selftest():
    import io
    import contextlib

    if not EVENTS.exists():
        log("no staged events - run `build` first")
        return 2
    if step_verify(quiet=True) != 0:
        log("REFUSING: baseline is already RED. A violation injected into a "
            "broken baseline proves nothing.")
        return 2
    original = EVENTS.read_bytes()
    original_dk = DOCKETS.read_bytes() if DOCKETS.exists() else None
    rows = read_csv(EVENTS)
    drows = read_csv(DOCKETS)
    if not rows or not drows:
        log("no rows to mutate; selftest cannot prove anything")
        return 2

    docket_mutations = [
        (DOCKET_INVARIANTS[0], {"docket_number": ""}),
        (DOCKET_INVARIANTS[1], {"as_of_date": ""}),
        (DOCKET_INVARIANTS[2], {"parties_as_recorded_by_the_clerk":
                                "Jane Doe | Wells Fargo Bank NA"}),
        (DOCKET_INVARIANTS[3], {"not_summable_with": "total tribal debt"}),
        (DOCKET_INVARIANTS[4], {"tribal_party_role": "PROBABLY_THE_BORROWER"}),
        (DOCKET_INVARIANTS[5], {"obligor_entity_match_method": ""}),
    ]

    mutations = [
        (INVARIANTS[0], {"court": ""}),
        (INVARIANTS[1], {"as_of_date": ""}),
        (INVARIANTS[2], {"event_type_basis": "because it looked like one"}),
        (INVARIANTS[3], {"assertion_or_finding": "PROBABLY_A_DEFAULT"}),
        (INVARIANTS[4], {"sovereign_immunity_caution": ""}),
        (INVARIANTS[5], {"not_summable_with": "total tribal debt"}),
        (INVARIANTS[6], {"verbatim_quote":
                         "The tribe was insolvent and could not pay its bills."}),
        (INVARIANTS[7], {"case_name_as_captioned": "Doe v. Tribe (per capita)"}),
        (INVARIANTS[8], {"instrument_as_described": ""}),
        # a tier asserted with no link, which is exactly 1082's I5 and the
        # START_HERE trap-1 shape: the tier says WHAT was decided, and here
        # nothing was.
        (INVARIANTS[9], {"obligor_entity_tier": "A", "obligor_cedar_uid": ""}),
    ]
    ok = True
    try:
        for target, base, muts in ((EVENTS, rows, mutations),
                                   (DOCKETS, drows, docket_mutations)):
            for name, cols in muts:
                mut = [dict(r) for r in base]
                for col, val in cols.items():
                    mut[0][col] = val
                write_csv(target, mut)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = step_verify()
                fired = _named_invariant_fired(buf.getvalue(), name)
                log("%-70s %s" % (name,
                                  "FIRES" if (rc == 1 and fired) else "DID NOT FIRE"))
                if not (rc == 1 and fired):
                    ok = False
            # restore this table before mutating the next one, so a docket
            # mutation is never evaluated against a still-broken events file.
            (EVENTS if target is EVENTS else DOCKETS).write_bytes(
                original if target is EVENTS else original_dk)
    finally:
        EVENTS.write_bytes(original)
        if original_dk is not None:
            DOCKETS.write_bytes(original_dk)
    rc = step_verify(quiet=True)
    log(f"restored byte-for-byte; verify is {'GREEN' if rc == 0 else 'RED'}")
    return 0 if (ok and rc == 0) else 1


def step_spend():
    led = load_spend()
    d, h, m = spent_counts(led)
    mine = [r for r in led["requests"] if r.get("script") == f"code/{SCRIPT}"]
    log(f"token budget (SHARED with code/366): {d}/{PER_DAY} today, "
        f"{h}/{PER_HOUR} this hour, {m}/{PER_MIN} this minute")
    log(f"ledger holds {len(led['requests'])} requests; {len(mine)} are 1110's")
    import collections
    log(str(collections.Counter(str(r.get("status")) for r in mine)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["targets", "probe", "search", "remine",
                                      "opinions", "build", "verify", "selftest",
                                      "spend"])
    ap.add_argument("--max", type=int, default=20)
    a = ap.parse_args()
    return {
        "targets": step_targets,
        "probe": step_probe,
        "search": lambda: step_search(a.max),
        "remine": step_remine,
        "opinions": lambda: step_opinions(a.max),
        "build": step_build,
        "verify": step_verify,
        "selftest": step_selftest,
        "spend": step_spend,
    }[a.stage]()


if __name__ == "__main__":
    sys.exit(main())
