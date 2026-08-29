#!/usr/bin/env python3
"""
23b_build_gaming_land_decisions.py -- Cedar Press Gaming dataset, Phase 1 Step B.

Parses the LOCAL archive of the BIA Office of Indian Gaming "Gaming Land
Decisions" index (fetched by 23a) into:

    data/clean/gaming_land_decisions.csv    one row per BIA index record
    data/clean/gaming_decision_events.csv   one row per dated status event

PRIME DIRECTIVE -- ZERO FABRICATION.
Every field is either copied verbatim from the BIA index HTML or derived by a
deterministic rule that is named in a *_basis column on the same row. No date,
status, or classification is inferred from silence.

WHY AN EVENT TABLE.
BIA's "Decision Status" column is a single current-state field. It cannot
represent Scotts Valley (approved 01/10/2025, gaming eligibility rescinded
effective 03/27/2025 -- still listed "Approved") or Koi Nation (approved
01/13/2025, land acquisition reversed by a Federal Register notice published
04/02/2026 -- still listed "Approved"). Collapsing those to a current status
destroys the reversal, which is the part no directory product carries. So the
status column is kept verbatim AND every dated statement BIA publishes about
the record is emitted as its own event row with the verbatim evidence text.

EVENT DERIVATION RULES (deterministic; the rule id is written to each row):
  E1  Every index record emits one event from BIA's own Decision Status + Date
      columns. event_type = decision_approved | decision_disapproved |
      decision_pending.
  E2  Every Federal Register link emits one event. event_date = the publication
      date in the FR URL path (/documents/YYYY/MM/DD/docnum/slug) -- the date is
      IN the URL, not inferred. event_type is taken from the literal leading
      words of the FR slug ('reversal-of-land-acquisition' -> reversal;
      'land-acquisitions' -> land_acquisition_notice); anything else stays
      federal_register_notice.
  E3  The free-text note BIA publishes under the <hr> in the Title cell is split
      into its source paragraphs, then on semicolons. A clause gets a date ONLY
      if it contains exactly one full "Month D, YYYY" date AND carries no
      cross-reference cue. Two cues disqualify a date: the word "see", and a date
      immediately followed by "decision". Both forms name ANOTHER record's date
      ("See September 19, 2013 Decision"; "Affirming September 18, 2015
      decision"), and dating this row with them would move an event between
      records. Such clauses are still emitted, verbatim, but undated. Bare years
      ("in 2011") are never promoted to a date.
  E4  A document link whose LABEL literally begins "Month D, YYYY - ..." emits
      an event on that date with the rest of the label as the description.

  event_type on E3/E4 is a keyword TAG over the verbatim text, not an
  interpretation: the full source wording travels in evidence_text on every row.

STAGE DISCIPLINE. This table is the federal-action layer. It records decisions,
not facilities. It contains no machine counts, square footages, or dollar
figures, because the index publishes none -- those live in the NEPA documents,
which Phase 2 extracts under the proposed/approved/built/current stage schema.

entity_id is intentionally left BLANK. Spine linking is a separate, ruled step.
"""
import os, re, csv, io, html, collections, datetime, unicodedata
from pathlib import Path

BASE  = str(Path(__file__).resolve().parent.parent)
RAW   = os.path.join(BASE, "data", "raw", "external", "gaming",
                     "bia_gaming_land_decisions")
CLEAN = os.path.join(BASE, "data", "clean")
os.makedirs(CLEAN, exist_ok=True)

FETCHED  = "2026-08-05"
INDEX_URL   = "https://www.bia.gov/as-ia/oig/gaming-land-decisions"
PENDING_URL = "https://www.bia.gov/as-ia/oig/gaming-land-decisions/pending"
SITE = "https://www.bia.gov"

buf = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")

# ------------------------------------------------------------------ helpers
def txt(s):
    """HTML fragment -> plain text, entities decoded, whitespace normalized.
    Wording is preserved verbatim; only markup and runs of space are removed."""
    s = re.sub(r"<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def slug(s, n=40):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()[:n].strip("-")

def cell(row_html, col):
    m = re.search(r'<td headers="' + col + r'"[^>]*>(.*?)</td>', row_html, re.S)
    return m.group(1) if m else ""

COL = dict(state="view-field-us-state-s-1-table-column",
           tribe="view-name-table-column",
           title="view-nothing-table-column",
           theory="view-field-legal-theory-decisions-table-column",
           status="view-field-decision-type-table-column",
           date="view-field-date-table-column")

MONTHS = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October "
    "November December".split())}
FULLDATE = re.compile(r"\b(" + "|".join(MONTHS) + r")\.?\s+(\d{1,2}),\s*(\d{4})\b")
ABBR = {"Jan":"January","Feb":"February","Mar":"March","Apr":"April","Jun":"June",
        "Jul":"July","Aug":"August","Sept":"September","Sep":"September",
        "Oct":"October","Nov":"November","Dec":"December"}
ABBRDATE = re.compile(r"\b(" + "|".join(ABBR) + r")\.?\s+(\d{1,2}),\s*(\d{4})\b")

def full_dates(s):
    """All unambiguous 'Month D, YYYY' dates in s, ISO, in order of appearance.
    A bare year is NEVER a date."""
    out = []
    for m in FULLDATE.finditer(s):
        out.append((m.start(), MONTHS[m.group(1)], int(m.group(2)), int(m.group(3))))
    for m in ABBRDATE.finditer(s):
        out.append((m.start(), MONTHS[ABBR[m.group(1)]], int(m.group(2)), int(m.group(3))))
    iso = []
    for _, mo, dd, yy in sorted(set(out)):
        try: iso.append(datetime.date(yy, mo, dd).isoformat())
        except ValueError: pass
    return iso

# --------------------------------------------------- document type vocabulary
# Literal keyword tags. Multiple tags allowed. Never a guess: if no literal
# phrase is present the type is 'unclassified'.
DOCTYPE = [
 ("record_of_decision",      r"record of decision|\bROD\b"),
 ("fonsi",                   r"finding[s]? of no significant impact|\bFONSI\b"),
 ("environmental_impact_statement", r"environmental impact statement|\bF?EIS\b|\bDEIS\b"),
 ("environmental_assessment",r"environmental assessment|(?<![A-Za-z])EA(?![A-Za-z])"),
 ("notice_of_availability",  r"notice of availability|\bNOA\b"),
 ("notice_of_intent",        r"notice of intent|\bNOI\b|notice of preparation|\bNOP\b"),
 ("scoping",                 r"\bscoping\b"),
 ("decision_letter",         r"decision letter|decision package|final decision"),
 ("trust_acquisition_document", r"trust acqui\w+"),
 ("denial_letter",           r"\bdenial\b|\bdenied\b"),
 ("two_part_determination",  r"two[- ]part"),
 ("governor_correspondence", r"\bgovernor"),
 ("findings_of_fact",        r"finding[s]? of fact"),
 ("reconsideration",         r"reconsider"),
 ("remand",                  r"\bremand"),
 ("withdrawal",              r"\bwithdraw"),
 ("extension",               r"\bextension\b"),
 ("fact_sheet",              r"fact sheet|q&a|q_a"),
 ("comment_letters",         r"comment letter"),
 ("map_or_exhibit",          r"\bmap\b|aerial photograph|legal description|\bexhibit\b"),
 ("memorandum",              r"memorandum|\bmemo\b|\bopinion\b"),
 ("federal_register_notice", r"federal.register|fed.reg"),
 ("appendix",                r"\bappendix\b|\battachment\b|\benclosure\b"),
]
# NOTE ON SEPARATORS: document_urls / document_labels / document_types are three
# PARALLEL pipe-delimited lists -- element i of each describes the same document.
# Tags WITHIN one document are therefore joined with '+', never '|', or the
# columns would not align. Labels have any literal '|' replaced with '/'.
def doctypes(label, url):
    hay = (label or "") + " " + (url or "").replace("_", " ").replace("-", " ")
    hits = [t for t, p in DOCTYPE if re.search(p, hay, re.I)]
    return "+".join(hits) if hits else "unclassified"

# ---------------------------------------------------- note event keyword tags
# Ordered; first literal match wins. Tag over verbatim text -- never a reading
# of what BIA "meant".
NOTE_TAG = [
 ("rescission_stated_in_note",              r"\brescind"),
 ("vacatur_stated_in_note",                 r"\bvacat"),
 ("reversal_stated_in_note",                r"\brevers"),
 ("reconsideration_stated_in_note",         r"\breconsider"),
 ("governor_nonconcurrence_stated_in_note", r"non-?concur|did not concur|declin\w* to concur"),
 ("governor_concurrence_stated_in_note",    r"\bconcur"),
 ("withdrawal_stated_in_note",              r"\bwithdr"),
 ("affirmance_stated_in_note",              r"\baffirm"),
 ("approval_stated_in_note",                r"\bapprov"),
 ("denial_stated_in_note",                  r"\bdeni(?:al|ed|es)\b|\bdeny\b"),
 ("remand_stated_in_note",                  r"\bremand"),
 ("appeal_stated_in_note",                  r"\bappeal"),
 ("litigation_stated_in_note",              r"\bv\.\s|\bF\.\s*Supp|\bF\.3d\b|\bF\.2d\b|D\.D\.C\.|Cir\."),
]
def note_tag(s):
    for t, p in NOTE_TAG:
        if re.search(p, s, re.I): return t
    return "stated_in_bia_note"

# A clause cross-references ANOTHER record when it says "see ...", or when its
# date is immediately followed by the word "decision" ("the May 25, 2012
# decision", "Affirming September 18, 2015 decision"). In both forms the date is
# the OTHER record's date; dating this row with it would move an event between
# records. The clause is still emitted -- with its verbatim text -- but undated.
XREF = re.compile(r"\bsee\b|\b(?:" + "|".join(MONTHS) + r")\s+\d{1,2},\s*\d{4}\s+decision\b",
                  re.I)

# ------------------------------------------------------------------------
# SOURCE DEFECT CHECK -- BIA's Tribe(s) column vs its own Title / document set.
# STATE_OF_BUILD.md records that the BIA *compact* index misaligns its Tribes
# column with its Title column on 5.1% of rows. The same check is therefore run
# here on the *decisions* index, and it fires: the row whose Tribe(s) column
# reads "Tonawanda Band of Seneca" / "Louisiana" is titled "Tunica-Biloxi Indian
# Tribe Decision" and links only Tunica-Biloxi, Avoyelles Parish documents.
# BIA's value is NEVER overwritten -- it is preserved verbatim, flagged, and the
# title-derived candidate is published alongside so a consumer can choose.
# ------------------------------------------------------------------------
TRIBE_STOP = set("tribe tribes band bands indian indians nation nations community "
                 "communities of the a an in and reservation rancheria pueblo village "
                 "tribal state gaming compact group people federal register link "
                 "decision project casino resort site".split())
def tribe_tokens(x):
    x = re.sub(r"[^A-Za-z ]", " ", (x or "").lower())
    return set(w for w in x.split() if w not in TRIBE_STOP and len(w) > 2)

TITLE_TAIL = re.compile(r"\s+(?:decision|reconsideration\s+decision|project|"
                        r"casino\s+project).*$", re.I)
def tribe_from_title(t):
    t = re.sub(r"\s+", " ", t or "").strip()
    m = TITLE_TAIL.search(t)
    if m: t = t[:m.start()]
    return t.strip(" ,-")

# ---------------------------------------------------------------- FR parsing
FRURL = re.compile(r"https://www\.federalregister\.gov/documents/"
                   r"(\d{4})/(\d{2})/(\d{2})/([^/\"]+)/([^\"?#]+)")
def fr_parse(url):
    m = FRURL.match(url)
    if not m: return "", "", ""
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", m.group(4), m.group(5)

def fr_type(fslug):
    s = (fslug or "").lower()
    if s.startswith("reversal-of-land-acquisition"): return "federal_register_reversal_of_land_acquisition"
    if s.startswith("land-acquisitions"):            return "federal_register_land_acquisition_notice"
    if s.startswith("indian-gaming"):                return "federal_register_indian_gaming_notice"
    return "federal_register_notice"

# ============================================================== load the index
idx_file = os.path.join(RAW, "gaming_land_decisions_all.html")
H = open(idx_file, encoding="utf-8").read()
body = H[H.find("<tbody"):H.find("</tbody>")]
rows_html = re.split(r"<tr>", body)[1:]
log(f"BIA Gaming Land Decisions index rows parsed : {len(rows_html)}")

# state abbreviations come from BIA's own facet <select>, not a hand table
STATE_ABBR = {}
d_file = os.path.join(RAW, "gaming_land_decisions_default.html")
if os.path.exists(d_file):
    dh = open(d_file, encoding="utf-8").read()
    m = re.search(r'name="field_us_state_s__value_selective"[^>]*>(.*?)</select>', dh, re.S)
    if m:
        for v, n in re.findall(r'<option value="([A-Z]{2})">([^<]+)</option>', m.group(1)):
            STATE_ABBR[html.unescape(n).strip()] = v
log(f"state abbreviations taken from BIA facet select : {len(STATE_ABBR)}")

# the /pending companion list -- used ONLY to corroborate the Pending set
pend_projects = set()
p_file = os.path.join(RAW, "gaming_land_decisions_pending_all.html")
if os.path.exists(p_file):
    ph = open(p_file, encoding="utf-8").read()
    pb = ph[ph.find("<tbody"):ph.find("</tbody>")]
    pend_projects = set(re.findall(r'<h3><a href="(/as-ia/oig/gaming-decisions/[^"]+)"', pb))
    log(f"/pending companion list rows                : {len(re.split(chr(60)+'tr>', pb)) - 1}")

# individual project pages fetched by 23a (document lists for Pending rows)
PROJ_DOCS = {}
for f in os.listdir(RAW):
    if not f.startswith("project_"): continue
    ph = open(os.path.join(RAW, f), encoding="utf-8", errors="replace").read()
    docs = []
    for m in re.finditer(r'<a href="(/sites/default/files/[^"]+)"[^>]*>(.*?)</a>', ph, re.S):
        lab = txt(m.group(2))
        if lab: docs.append((lab, SITE + m.group(1)))
    seen, ded = set(), []
    for lab, u in docs:
        if u in seen: continue
        seen.add(u); ded.append((lab, u))
    PROJ_DOCS[f] = ded
log(f"individual project pages with document lists: {len(PROJ_DOCS)} "
    f"({sum(len(v) for v in PROJ_DOCS.values())} documents)")

def proj_key(path):
    return "project_" + path.rstrip("/").rsplit("/", 1)[-1][:80] + ".html"

# ================================================================== build rows
decisions, events = [], []
id_used = collections.Counter()
n_note, n_fr, n_ffd, n_conflict = 0, 0, 0, 0
pending_seen = set()

for pos, rh in enumerate(rows_html):
    state  = txt(cell(rh, COL["state"]))
    tribe  = txt(cell(rh, COL["tribe"]))
    theory = txt(cell(rh, COL["theory"]))
    status = txt(cell(rh, COL["status"]))
    dcell  = cell(rh, COL["date"])
    m = re.search(r'datetime="(\d{4})-(\d{2})-(\d{2})', dcell)
    ddate = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""
    ddisp = txt(dcell)
    tcell = cell(rh, COL["title"])

    # -- title / project page
    h3 = re.search(r"<h3>(.*?)</h3>", tcell, re.S)
    title = txt(h3.group(1)) if h3 else ""
    plink = re.search(r'<h3><a href="([^"]+)"', tcell)
    project_page_url = (SITE + plink.group(1)) if plink else ""
    if plink: pending_seen.add(plink.group(1))

    # -- documents (index)
    docs = []
    for m in re.finditer(r'<span class="file file--mime[^"]*">\s*<a href="([^"]+)"[^>]*>(.*?)</a>',
                         tcell, re.S):
        u = m.group(1)
        docs.append((txt(m.group(2)), SITE + u if u.startswith("/") else u))
    docs_basis = "bia_gaming_land_decisions_index_row"
    # -- documents (individual project page) for rows the index leaves empty
    if not docs and project_page_url:
        pd = PROJ_DOCS.get(proj_key(plink.group(1)), [])
        if pd:
            docs = pd
            docs_basis = "bia_individual_project_page (index row lists no documents)"

    # -- Federal Register
    fr_urls = re.findall(r'href="(https://www\.federalregister\.gov/[^"]+)"', tcell)
    fr_url = fr_urls[0] if fr_urls else ""
    if len(fr_urls) > 1: n_fr += 1
    fr_date, fr_doc, fr_slug = fr_parse(fr_url) if fr_url else ("", "", "")

    # -- note (everything BIA publishes under the <hr>)
    note_html = tcell.split("<hr>", 1)[1] if "<hr>" in tcell else ""
    note = txt(note_html)
    if note: n_note += 1
    if "\ufffd" in note or any("\ufffd" in l for l, _ in docs): n_ffd += 1

    # -- BIA tribes-column vs title/document cross-check
    a, b = tribe_tokens(tribe), tribe_tokens(title)
    docblob = " ".join(l for l, _ in docs)
    conflict, tribe_alt = 0, ""
    if not b:
        tbasis = "bia_index_Tribe(s)_column, verbatim (no title to cross-check)"
    elif a & b:
        tbasis = "bia_index_Tribe(s)_column, verbatim (agrees with the BIA title)"
    else:
        cand = tribe_from_title(title)
        ct = tribe_tokens(cand)
        if ct and ct & tribe_tokens(docblob):
            conflict, tribe_alt = 1, cand
            tbasis = ("bia_index_Tribe(s)_column, verbatim BUT CONFLICTED: it shares no "
                      "distinctive token with the BIA title, and the title's name is "
                      "corroborated by the linked document labels. See tribe_from_title.")
        else:
            conflict, tribe_alt = 1, cand
            tbasis = ("bia_index_Tribe(s)_column, verbatim BUT CONFLICTED: it shares no "
                      "distinctive token with the BIA title; the documents do not "
                      "corroborate either name.")
    n_conflict += conflict

    # -- id
    st = STATE_ABBR.get(state, slug(state, 4).upper() or "XX")
    base = f"GLD-{st}-{slug(tribe) or 'no-tribe-listed'}-{ddate.replace('-', '')}"
    id_used[base] += 1
    did = base if id_used[base] == 1 else f"{base}-{id_used[base]}"

    decisions.append(dict(
        decision_id=did, entity_id="", tribe=tribe, state=state, state_abbr=st,
        legal_theory=theory, decision_status=status, decision_date=ddate,
        decision_date_displayed=ddisp, decision_title=title,
        document_urls="|".join(u for _, u in docs),
        document_labels="|".join(l.replace("|", "/") for l, _ in docs),
        document_types="|".join(doctypes(l, u) for l, u in docs),
        n_documents=len(docs), document_urls_basis=docs_basis,
        federal_register_url=fr_url, federal_register_date=fr_date,
        federal_register_doc_number=fr_doc, federal_register_slug=fr_slug,
        project_page_url=project_page_url,
        bia_note_text=note,
        source_url=PENDING_URL if status == "Pending" else INDEX_URL,
        index_row_position=pos + 1, fetched_date=FETCHED,
        tribe_basis=tbasis, bia_tribes_column_conflict=conflict,
        tribe_from_title=tribe_alt,
        legal_theory_basis="bia_index_Legal_Theory_column, verbatim",
        decision_status_basis="bia_index_Decision_Status_column, verbatim (current state only; see gaming_decision_events.csv)",
        decision_date_basis="bia_index_Date_column <time datetime> attribute",
    ))

    # ------------------------------------------------------------ events
    def emit(etype, edate, desc, evid, rule, basis, url=""):
        events.append(dict(
            event_id=f"{did}-E{len([e for e in events if e['decision_id']==did]) + 1:02d}",
            decision_id=did, tribe=tribe, state=state,
            event_date=edate, event_type=etype,
            description=desc, evidence_text=evid,
            derivation_rule=rule, event_date_basis=basis,
            document_url=url, source_url=INDEX_URL, fetched_date=FETCHED))

    # E1 -- the record's own decision
    et = {"Approved": "decision_approved", "Disapproved": "decision_disapproved",
          "Pending": "decision_pending"}.get(status, "decision_status_" + slug(status or "blank"))
    emit(et, ddate, title or status,
         f'Decision Status="{status}"; Date="{ddisp}"', "E1",
         "bia_index Date column" if ddate else "no date published in the BIA index row")

    # E2 -- Federal Register notices
    for u in fr_urls:
        fd, fdoc, fsl = fr_parse(u)
        emit(fr_type(fsl), fd, fsl.replace("-", " "),
             f"Federal Register link on the BIA index row: {u}", "E2",
             "publication date in the Federal Register URL path" if fd
             else "URL does not carry a publication date", u)

    # E3 -- BIA's published note, paragraph then semicolon clauses
    if note_html:
        paras = re.split(r"</p>|<br\s*/?>", note_html)
        clauses = []
        for p in paras:
            t = txt(p)
            if len(t) < 4: continue
            for c in re.split(r";\s*", t):
                c = c.strip()
                if len(c) > 3: clauses.append(c)
        for c in clauses:
            ds = full_dates(c)
            if len(ds) == 1 and not XREF.search(c):
                ed, basis = ds[0], "single unambiguous 'Month D, YYYY' date stated in the BIA note clause"
            elif XREF.search(c):
                ed, basis = "", "clause cross-references another record (contains 'see', or a date immediately followed by 'decision'); dating it would attach another record's event here"
            elif len(ds) > 1:
                ed, basis = "", f"clause states {len(ds)} dates ({', '.join(ds)}); none assigned"
            else:
                ed, basis = "", "no full 'Month D, YYYY' date stated in the clause (bare years are not promoted to dates)"
            emit(note_tag(c), ed, c, c, "E3", basis)

    # E4 -- document labels that literally begin with a date
    for l, u in docs:
        m = re.match(r"^\s*((?:" + "|".join(MONTHS) + r")\s+\d{1,2},\s*\d{4})\s*[-\u2013\u2014]\s*(.+)$", l)
        if not m: continue
        ds = full_dates(m.group(1))
        if not ds: continue
        emit(note_tag(m.group(2)), ds[0], m.group(2), l, "E4",
             "date stated at the start of the BIA document link label", u)

# ------------------------------------------------------------------- validate
missing_pending = pend_projects - pending_seen
log(f"/pending project links corroborated in the main index: "
    f"{len(pend_projects & pending_seen)} of {len(pend_projects)}"
    + (f"  MISSING: {sorted(missing_pending)}" if missing_pending else ""))

# ---------------------------------------------------------------------- write
DFIELDS = ["decision_id","entity_id","tribe","state","state_abbr","legal_theory",
           "decision_status","decision_date","document_urls","federal_register_url",
           "source_url","fetched_date",
           "decision_date_displayed","decision_title","document_labels",
           "document_types","n_documents","document_urls_basis",
           "federal_register_date","federal_register_doc_number",
           "federal_register_slug","project_page_url","bia_note_text",
           "index_row_position","tribe_basis","bia_tribes_column_conflict",
           "tribe_from_title","legal_theory_basis",
           "decision_status_basis","decision_date_basis"]
EFIELDS = ["event_id","decision_id","tribe","state","event_date","event_type",
           "description","evidence_text","derivation_rule","event_date_basis",
           "document_url","source_url","fetched_date"]

def dump(name, fields, data):
    with open(os.path.join(CLEAN, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in data: w.writerow(r)

dump("gaming_land_decisions.csv", DFIELDS, decisions)
dump("gaming_decision_events.csv", EFIELDS, events)

# ------------------------------------------------------------------- report
log("")
log("=" * 78); log("GAMING LAND DECISIONS BUILT"); log("=" * 78)
log(f"gaming_land_decisions.csv rows  : {len(decisions)}")
log(f"gaming_decision_events.csv rows : {len(events)}")
log("")
log("decision_status (BIA verbatim):")
for k, v in collections.Counter(d["decision_status"] for d in decisions).most_common():
    log(f"   {k or '(blank)':<12} {v}")
log("")
log("legal_theory (BIA verbatim):")
for k, v in collections.Counter(d["legal_theory"] for d in decisions).most_common():
    log(f"   {v:>4}  {k or '(blank -- BIA publishes no legal theory for this record)'}")
log("")
log(f"states                          : {len(set(d['state'] for d in decisions))}")
log(f"distinct tribe strings          : {len(set(d['tribe'] for d in decisions))}")
log(f"date range                      : {min(d['decision_date'] for d in decisions)} .. "
    f"{max(d['decision_date'] for d in decisions)}")
log(f"rows with >=1 document          : {sum(1 for d in decisions if d['n_documents'])}")
log(f"documents linked (total)        : {sum(d['n_documents'] for d in decisions)}")
log(f"rows with a Federal Register url: {sum(1 for d in decisions if d['federal_register_url'])}")
log(f"rows with a BIA note            : {n_note}")
log(f"rows carrying U+FFFD in BIA text: {n_ffd}  (source-side encoding damage, preserved verbatim)")
log(f"decision_id collisions resolved : {sum(1 for k, v in id_used.items() if v > 1)}")
log(f"BIA Tribe(s)-column conflicts   : {n_conflict} of {len(decisions)} "
    f"({100*n_conflict/len(decisions):.1f}%) -- same defect class STATE_OF_BUILD.md "
    f"records for the BIA compact index; BIA value preserved, flagged, and the "
    f"title-derived candidate published in tribe_from_title")
for d in decisions:
    if d["bia_tribes_column_conflict"]:
        log(f"     {d['decision_id']}")
        log(f"       Tribe(s) column : {d['tribe']}  ({d['state']})")
        log(f"       BIA title       : {d['decision_title']}")
        log(f"       documents       : {d['document_labels'][:100]}")
log("")
log("event_type:")
for k, v in collections.Counter(e["event_type"] for e in events).most_common():
    log(f"   {v:>4}  {k}")
log("")
log("derivation_rule:")
for k, v in collections.Counter(e["derivation_rule"] for e in events).most_common():
    log(f"   {v:>4}  {k}")
log(f"events carrying a date          : {sum(1 for e in events if e['event_date'])} "
    f"of {len(events)}")
log("")
log("document_types tagged (a document may carry several tags, joined with '+'):")
c = collections.Counter(); ndoc = 0
for d in decisions:
    if not d["document_types"]: continue
    for t in d["document_types"].split("|"):
        ndoc += 1
        for tag in t.split("+"):
            if tag: c[tag] += 1
for k, v in c.most_common(): log(f"   {v:>4}  {k}")
log(f"   (over {ndoc} document links; 'unclassified' = no literal type phrase "
    f"in the BIA label or filename)")
# alignment invariant -- the three document lists must be element-wise parallel
bad = [d["decision_id"] for d in decisions
       if len(d["document_urls"].split("|")) != len(d["document_types"].split("|"))
       or len(d["document_urls"].split("|")) != len(d["document_labels"].split("|"))]
log(f"   document_urls/labels/types alignment failures: {len(bad)} {bad[:5]}")
log("")
log("records whose status is Approved but which carry a reversal/rescission event:")
byid = collections.defaultdict(list)
for e in events: byid[e["decision_id"]].append(e)
n_rev = 0
for d in decisions:
    if d["decision_status"] != "Approved": continue
    ev = [e for e in byid[d["decision_id"]]
          if "revers" in e["event_type"] or "rescission" in e["event_type"]
          or "vacatur" in e["event_type"]]
    if ev:
        n_rev += 1
        log(f"   {d['decision_id']}  {d['tribe']}")
        for e in ev:
            log(f"       {e['event_date'] or '(no date)'}  {e['event_type']}  :: {e['description'][:110]}")
log(f"   -> {n_rev} record(s). These are why decision_status is never used alone.")

with open(os.path.join(BASE, "logs", "23_gaming_2026-08-05.log"), "a",
          encoding="utf-8") as fh:
    fh.write("\n\n" + "=" * 78 + "\n23b_build_gaming_land_decisions.py\n"
             + "=" * 78 + "\n" + buf.getvalue())
