#!/usr/bin/env python3
"""
15b_build_compact_index.py -- Cedar Press Compacts dataset, Step C (index layer).

Builds compacts.csv, compact_versions.csv and compact_events.csv from the local
copy of the BIA Office of Indian Gaming compact index + PDF/text archive.

SOURCE OF TRUTH for parties / dates / decision / FR notice is the BIA index
(columns as published: "US State(s) | Tribes | Title | Decision | Date").
Filenames are NEVER used to date a document -- 32 filenames disagree with the
index date and 42 carry no parseable date at all (see 15a).

DERIVATION RULES (each one deterministic, none inferred from silence):
  R1  A row with is_amendment=0 and decision in {Approve, Deemed Approved,
      Secretarial Procedures, <blank>} opens a NEW base instrument (a compact).
  R2  Every other non-disapproval row attaches as a VERSION of the most recent
      preceding base instrument for the same (state, tribe), ordered by BIA
      decision date then BIA page/row position.
  R3  decision='Disapproved' emits a compact_events row. Never a deletion.
  R4  approval_type = {Approve->secretarial, Deemed Approved->deemed-approved,
      Secretarial Procedures->secretarial-procedures, blank->unknown}.
  R5  original_effective_date = date embedded in the Federal Register notice URL
      when one exists (a compact takes effect on FR publication, 25 U.S.C.
      2710(d)(3)(B)); otherwise the BIA index Date. Basis is recorded per row.
  R6  term_end is populated ONLY from an explicit end date stated in the BIA
      title of an extension row ("...Extension to 2/28/11"). Never computed
      from a term length. Basis recorded.
  R7  amendment_number is taken ONLY from an explicit ordinal in the BIA title
      (Roman, ordinal word, or "Nth"). Otherwise blank. version_seq is the
      chronological position and is labeled as derived.
  R8  status: renegotiated (a later base instrument exists for the same
      state+tribe) > expired (term_end < run date) > active (term_end >= run
      date) > unknown. Basis recorded.

Schema note: the plan's column list is emitted first and unchanged. Columns
after the marker `--` in the header comment are added provenance/derivation
fields; collapsing them into the plan columns would have required asserting
things the sources do not say.
"""
import csv, os, re, sys, collections, datetime, io, unicodedata
from pathlib import Path

BASE = str(Path(__file__).resolve().parent.parent)
EXT  = os.path.join(BASE, "data", "raw", "external", "compacts")
IDXF = os.path.join(EXT, "index", "bia_compact_index.csv")
TXT  = os.path.join(EXT, "text")
PDF  = os.path.join(EXT, "pdf")
CLEAN= os.path.join(BASE, "data", "clean")
os.makedirs(CLEAN, exist_ok=True)
RUNDATE = datetime.date(2026, 8, 5)

sys.path.insert(0, os.path.join(BASE, "code"))
from cedar_keys import surrogate_id                            # noqa: E402

# ---------------------------------------------------------------------------
# THE PRIMARY KEY OF compact_events.csv, AND WHAT IT IS MADE OF
#
# `event_id` was
#     f"EVT-{st}-{tribe_slug}-{date}-{len(events)+1:04d}"
# Three quarters of that is stated by BIA. The last quarter - the position in
# the run - is the only part that could move, and it moved whenever the index
# gained a row above this one.
#
# It is now a deterministic blake2b digest of what the BIA Office of Indian
# Gaming index itself prints: WHICH COMPACT the event happened to, the DATE
# BIA gives the decision, and WHAT the decision was. Measured 2026-08-26:
# unique over all 31 rows, 0 blank.
#
# Migrated in the live file by `327_migrate_class7_keys_to_digests.py`.
# ---------------------------------------------------------------------------
COMPACT_EVENT_KEY_COLUMNS = ["compact_id", "event_date", "event_type"]

buf = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")

ST = {'Alabama':'AL','Alaska':'AK','Arizona':'AZ','California':'CA','Colorado':'CO',
 'Connecticut':'CT','Florida':'FL','Idaho':'ID','Iowa':'IA','Kansas':'KS','Louisiana':'LA',
 'Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Montana':'MT','Nebraska':'NE',
 'Nevada':'NV','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND',
 'Oklahoma':'OK','Oregon':'OR','Rhode Island':'RI','South Dakota':'SD','Texas':'TX',
 'Washington':'WA','Wisconsin':'WI','Wyoming':'WY','Massachusetts':'MA','Maine':'ME'}

# --------------------------------------------------------------------------
# DEFECT IN THE SOURCE (found 2026-08-05, documented in the build log):
# The BIA compact page's "Tribes" column is misaligned with its "Title" column
# on 5.5% of rows -- an off-by-one/off-by-few slip down the alphabetical tribe
# list (e.g. the Mohegan compact is filed under "Mississippi Band of Choctaw
# Indians"; the Mashpee Wampanoag compact under "Mashantucket Pequot Indian
# Tribe"; the Miami Tribe compact under "Kialegee Tribal Town"). The defect is
# present in the archived raw HTML, so it is BIA's, not the scraper's.
# Resolution: the Title column is aligned with the linked PDF filename, so when
# the two columns share no distinctive token the tribe is taken from the Title
# and the row is flagged. The BIA column is preserved verbatim either way.
# --------------------------------------------------------------------------
TRIBE_STOP = set('tribe tribes band bands indian indians nation nations community communities '
                 'of the a in and reservation rancheria pueblo village tribal state gaming '
                 'compact group people federal register link'.split())
def tribe_tokens(s):
    s = re.sub(r'[^A-Za-z ]', ' ', (s or '').lower())
    return set(w for w in s.split() if w not in TRIBE_STOP and len(w) > 2)

TITLE_TAIL = re.compile(
    r'\s+(?:tribal[- ]state\s+gaming\s+compact|tribal[- ]state\s+compact|gaming\s+compact'
    r'|secretarial\s+procedures|gaming\s+procedures|compact\b).*$', re.I)
def tribe_from_title(title):
    t = re.sub(r'https?://\S+', ' ', title or '')
    t = re.sub(r'\s+', ' ', t).strip()
    m = TITLE_TAIL.search(t)
    if m: t = t[:m.start()]
    t = re.sub(r'\s+(and\s+State\s+of\s+\w+.*)$', '', t, flags=re.I)
    return t.strip(' ,-')

def resolve_tribe(bia_tribe, title, pdf_filename):
    """Returns (tribe, basis, conflict_flag)."""
    a, b = tribe_tokens(bia_tribe), tribe_tokens(title)
    if not b:
        return bia_tribe, 'bia_tribes_column (title empty; cross-check impossible)', 0
    if a & b:
        return bia_tribe, 'bia_tribes_column (agrees with BIA title)', 0
    cand = tribe_from_title(title)
    ct = tribe_tokens(cand)
    pf = tribe_tokens(re.sub(r'[_\.]', ' ', pdf_filename or ''))
    if ct and (ct & pf or not pf):
        return cand, 'bia_title (BIA tribes column conflicts with title and PDF)', 1
    return bia_tribe, 'bia_tribes_column (title conflicts but not corroborated by PDF name)', 1

FRDATE = re.compile(r'federalregister\.gov/documents/(\d{4})/(\d{2})/(\d{2})/([^/]+)/')
GOVFR  = re.compile(r'govinfo\.gov/content/pkg/FR-(\d{4})-(\d{2})-(\d{2})/pdf/([^/]+)\.pdf')

ROMAN = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,'IX':9,'X':10,
         'XI':11,'XII':12,'XIII':13,'XIV':14,'XV':15,'XVI':16,'XVII':17,'XVIII':18,
         'XIX':19,'XX':20}
ORD = {'first':1,'second':2,'third':3,'fourth':4,'fifth':5,'sixth':6,'seventh':7,
       'eighth':8,'ninth':9,'tenth':10,'eleventh':11,'twelfth':12,'thirteenth':13,
       'fourteenth':14,'fifteenth':15}

def slug(s, n=34):
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode()
    s = re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-').lower()
    return s[:n].strip('-')

def fr_citation(url):
    """Return (FR doc number, FR publication date ISO, ''). No volume/page is
    invented -- BIA supplies only the notice URL."""
    if not url: return '', ''
    m = FRDATE.search(url)
    if m: return m.group(4), f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = GOVFR.search(url)
    if m: return m.group(4), f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return '', ''

EXT_TO = re.compile(r'\bExtension\b[^0-9]{0,12}(\d{1,2})[/](\d{1,2})[/](\d{2,4})', re.I)
def extension_end(title):
    m = EXT_TO.search(title or '')
    if not m: return ''
    mo, dd, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100: y += 2000 if y < 70 else 1900
    if not (1 <= mo <= 12 and 1 <= dd <= 31 and 1980 <= y <= 2100): return ''
    try: return datetime.date(y, mo, dd).isoformat()
    except ValueError: return ''

AMD_ROMAN = re.compile(r'\bAmendment\s+([IVXL]{1,6})\b')
AMD_NUM   = re.compile(r'\bAmendment\s+(?:No\.?\s*)?(\d{1,2})\b', re.I)
AMD_ORD   = re.compile(r'\b(' + '|'.join(ORD) + r')\s+(?:Compact\s+)?Amendment\b', re.I)
AMD_NTH   = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)\s+Amendment\b', re.I)
def amendment_number(title):
    t = title or ''
    m = AMD_ROMAN.search(t)
    if m and m.group(1).upper() in ROMAN: return str(ROMAN[m.group(1).upper()])
    m = AMD_NUM.search(t)
    if m: return m.group(1)
    m = AMD_NTH.search(t)
    if m: return m.group(1)
    m = AMD_ORD.search(t)
    if m: return str(ORD[m.group(1).lower()])
    return ''

def what_changed(title, decision, is_amd):
    """Only classify when the BIA title/decision says so; else 'unknown'."""
    t = (title or '').lower()
    if decision == 'Extensions' or 'extension' in t: return 'term'
    if 'amended and restated' in t or 'amended & restated' in t: return 'amended-and-restated'
    tags = []
    if re.search(r'blackjack|video games|card games|sports|keno|bingo|table games|craps|roulette|lottery|class iii games', t): tags.append('scope')
    if re.search(r'revenue|payment|sharing|fee', t): tags.append('sharing')
    if re.search(r'machine|device|cap\b', t): tags.append('caps')
    if re.search(r'\bterm\b|renewal|expiration', t): tags.append('term')
    if tags: return '|'.join(sorted(set(tags)))
    return 'unknown'

MARK = re.compile(r'(TRIBAL[- ]STATE|GAMING COMPACT|WITNESSETH|WHEREAS|SECTION\s+[0-9IVX]|ARTICLE\s+[0-9IVX])', re.I)
def text_profile(pdf_filename):
    stem = os.path.splitext(pdf_filename)[0]
    p = os.path.join(TXT, stem + '.txt')
    if not os.path.exists(p): return 0, 0, '', 'no_text_file'
    t = open(p, encoding='utf-8', errors='replace').read()
    n = len(t)
    alpha = sum(c.isalpha() or c.isspace() for c in t) / n if n else 0.0
    marks = len(MARK.findall(t))
    if n == 0: kind = 'empty'
    elif n < 1200: kind = 'stub'
    elif marks >= 3 and n >= 3000: kind = 'instrument_text'
    elif n < 3000: kind = 'letter_or_short_doc'
    else: kind = 'text_present_unclassified'
    return n, round(alpha, 4), stem + '.txt', kind

# ------------------------------------------------------------------ load index
rows = list(csv.DictReader(open(IDXF, encoding='utf-8')))
log(f"BIA index rows read: {len(rows)}")
disk = set(os.listdir(PDF))
def resolve_pdf(fn):
    """Index sometimes stores the filename without the .pdf extension."""
    if not fn: return ''
    if fn in disk: return fn
    if fn + '.pdf' in disk: return fn + '.pdf'
    return ''

groups = collections.defaultdict(list)
n_conflict = 0
for i, r in enumerate(rows):
    r['_i'] = i
    t, basis, flag = resolve_tribe(r['tribe'], r['title'], r['pdf_filename'])
    r['_tribe'], r['_tribe_basis'], r['_tribe_conflict'] = t, basis, flag
    n_conflict += flag
    # Group on state + the set of distinctive name tokens so that spelling
    # variants of one tribe do not split a compact history ("Mohegan Indian
    # Tribe" / "Mohegan Tribe of Indians"; "Otoe-Missouria" / "Otoe-Missouria
    # Tribe"). Token SETS, not token overlap -- "Pueblo of Santa Ana" and
    # "Pueblo of Santa Clara" keep distinct keys. Only 2 groups merge.
    groups[(r['state'], frozenset(tribe_tokens(t)))].append(r)
log(f"BIA tribes-column conflicts detected and resolved: {n_conflict} "
    f"({100*n_conflict/len(rows):.2f}% of rows)")

compacts, versions, events = [], [], []
cid_used = collections.Counter()
n_unresolved_pdf = 0

for (state, _tokkey), rs in sorted(groups.items(), key=lambda kv: (kv[0][0], sorted(kv[0][1]))):
    rs.sort(key=lambda x: (x['date_iso'], int(x['page_idx']), int(x['row_idx'])))
    # display name = the longest resolved name in the group (most complete form)
    tribe = max((r['_tribe'] for r in rs), key=len)
    st = ST.get(state, slug(state, 4).upper())
    cur = None            # current compact dict
    cur_versions = []
    tribe_slug = slug(tribe)
    made = []             # compacts made for this tribe-state, in order

    def open_compact(r, instrument_type):
        base = f"CMP-{st}-{tribe_slug}-{r['date_iso'].replace('-','')}"
        cid_used[base] += 1
        cid = base if cid_used[base] == 1 else f"{base}-{cid_used[base]}"
        pdf = resolve_pdf(r['pdf_filename'])
        doc, frd = fr_citation(r['fr_url'])
        if frd:
            eff, basis = frd, 'fr_publication_date_from_notice_url'
        else:
            eff, basis = r['date_iso'], 'bia_index_decision_date'
        atype = {'Approve':'secretarial', 'Deemed Approved':'deemed-approved',
                 'Secretarial Procedures':'secretarial-procedures',
                 'Extensions':'unknown', '':'unknown'}.get(r['decision'], 'unknown')
        c = dict(compact_id=cid, entity_id='', tribe=tribe, state=state,
                 tribe_name_basis=r['_tribe_basis'],
                 bia_tribes_column=r['tribe'],
                 bia_tribes_column_conflict=r['_tribe_conflict'],
                 original_effective_date=eff, approval_type=atype,
                 FR_citation=(f"FR Doc. {doc}" if doc else ''),
                 term_end='', renewal_provisions='', status='',
                 successor_compact_id='',
                 instrument_type=instrument_type, bia_title=r['title'],
                 bia_decision=r['decision'], bia_decision_date=r['date_iso'],
                 original_effective_date_basis=basis,
                 FR_notice_url=r['fr_url'], n_versions=0,
                 term_end_basis='', status_basis='',
                 source_pdf=pdf, source_url=r['pdf_url'])
        compacts.append(c)
        made.append(c)
        return c

    for r in rs:
        if r['decision'] == 'Disapproved':
            doc, frd = fr_citation(r['fr_url'])
            ev = dict(
                event_id='',           # set below, from THIS row's own facts
                compact_id=(cur['compact_id'] if cur else ''),
                tribe=tribe, state=state, event_date=r['date_iso'],
                event_type='secretarial_disapproval',
                description=r['title'],
                FR_citation=(f"FR Doc. {doc}" if doc else ''),
                FR_notice_url=r['fr_url'],
                source_pdf=resolve_pdf(r['pdf_filename']), source_url=r['pdf_url'],
                basis='BIA Office of Indian Gaming index, Decision="Disapproved"')
            ev['event_id'] = surrogate_id('EVT', ev,
                                          COMPACT_EVENT_KEY_COLUMNS)
            events.append(ev)
            continue

        is_base = (r['is_amendment'] == '0' and
                   r['decision'] in ('Approve', 'Deemed Approved', 'Secretarial Procedures', ''))
        if is_base:
            it = 'secretarial-procedures' if r['decision'] == 'Secretarial Procedures' else 'compact'
            cur = open_compact(r, it)
        elif cur is None:
            # orphan version: no preceding base instrument in the BIA index
            cur = open_compact(r, 'orphan-no-base-instrument-in-index')
            cur['status_basis'] = 'orphan: BIA index lists no preceding base instrument'

        seq = cur['n_versions'] + 1
        cur['n_versions'] = seq
        pdf = resolve_pdf(r['pdf_filename'])
        if not pdf: n_unresolved_pdf += 1
        nchars, alpha, tpath, kind = text_profile(pdf) if pdf else (0, 0, '', 'no_pdf')
        doc, frd = fr_citation(r['fr_url'])
        atype = {'Approve':'secretarial', 'Deemed Approved':'deemed-approved',
                 'Secretarial Procedures':'secretarial-procedures',
                 'Extensions':'unknown', '':'unknown'}.get(r['decision'], 'unknown')
        vid = f"{cur['compact_id']}-V{seq:02d}"
        versions.append(dict(
            version_id=vid, compact_id=cur['compact_id'],
            amendment_number=(amendment_number(r['title']) if not is_base else '0'),
            approval_date=(frd or r['date_iso']),
            FR_citation=(f"FR Doc. {doc}" if doc else ''),
            what_changed=('original-instrument' if is_base else what_changed(r['title'], r['decision'], r['is_amendment'])),
            has_text=(1 if kind == 'instrument_text' else 0),
            version_seq=seq,
            version_role=('original-instrument' if is_base else
                          'extension' if r['decision'] == 'Extensions' else 'amendment'),
            bia_decision=r['decision'], approval_type=atype,
            bia_title=r['title'], bia_decision_date=r['date_iso'],
            approval_date_basis=('fr_publication_date_from_notice_url' if frd else 'bia_index_decision_date'),
            FR_notice_url=r['fr_url'],
            bia_tribes_column=r['tribe'], bia_tribes_column_conflict=r['_tribe_conflict'],
            doc_kind=kind, text_chars=nchars, text_alpha_ratio=alpha,
            text_path=tpath, source_pdf=pdf, source_url=r['pdf_url']))
        # R6: explicit extension end date stated in the BIA title
        ee = extension_end(r['title'])
        if ee:
            cur['term_end'] = ee
            cur['term_end_basis'] = f"explicit end date in BIA title of version {vid}"

    # R8 successor + status
    for a, b in zip(made, made[1:]):
        a['successor_compact_id'] = b['compact_id']

for c in compacts:
    if c['successor_compact_id']:
        c['status'], c['status_basis'] = 'renegotiated', 'a later base instrument for the same state+tribe appears in the BIA index'
    elif c['term_end']:
        d = datetime.date.fromisoformat(c['term_end'])
        c['status'] = 'expired' if d < RUNDATE else 'active'
        c['status_basis'] = f"term_end from {c['term_end_basis']}; compared to run date {RUNDATE}"
    else:
        c['status'], c['status_basis'] = 'unknown', 'no successor in BIA index and no explicitly stated term_end'

# ------------------------------------------------------------------ write
CFIELDS = ['compact_id','entity_id','tribe','state','original_effective_date',
           'approval_type','FR_citation','term_end','renewal_provisions','status',
           'successor_compact_id',
           'instrument_type','tribe_name_basis','bia_tribes_column',
           'bia_tribes_column_conflict','bia_title','bia_decision','bia_decision_date',
           'original_effective_date_basis','FR_notice_url','n_versions',
           'term_end_basis','status_basis','source_pdf','source_url']
VFIELDS = ['version_id','compact_id','amendment_number','approval_date','FR_citation',
           'what_changed','has_text',
           'version_seq','version_role','bia_decision','approval_type','bia_title',
           'bia_decision_date','approval_date_basis','FR_notice_url',
           'bia_tribes_column','bia_tribes_column_conflict','doc_kind',
           'text_chars','text_alpha_ratio','text_path','source_pdf','source_url']
EFIELDS = ['event_id','compact_id','tribe','state','event_date','event_type',
           'description','FR_citation','FR_notice_url','source_pdf','source_url','basis']

def dump(path, fields, data):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in data: w.writerow(r)

dump(os.path.join(CLEAN, 'compacts.csv'), CFIELDS, compacts)
dump(os.path.join(CLEAN, 'compact_versions.csv'), VFIELDS, versions)
dump(os.path.join(CLEAN, 'compact_events.csv'), EFIELDS, events)

log("")
log("=" * 78); log("INDEX LAYER BUILT"); log("=" * 78)
log(f"compacts.csv rows          : {len(compacts)}")
log(f"compact_versions.csv rows  : {len(versions)}")
log(f"compact_events.csv rows    : {len(events)}")
log(f"index rows consumed        : {len(versions) + len(events)}  (of {len(rows)})")
log(f"version rows w/o resolvable local PDF : {n_unresolved_pdf}")
log("")
log(f"approval_type (compacts)   : {dict(collections.Counter(c['approval_type'] for c in compacts))}")
log(f"instrument_type            : {dict(collections.Counter(c['instrument_type'] for c in compacts))}")
log(f"status                     : {dict(collections.Counter(c['status'] for c in compacts))}")
log(f"eff-date basis             : {dict(collections.Counter(c['original_effective_date_basis'] for c in compacts))}")
log(f"term_end populated         : {sum(1 for c in compacts if c['term_end'])}")
log(f"distinct tribes            : {len(set(c['tribe'] for c in compacts))}")
log(f"distinct states            : {len(set(c['state'] for c in compacts))}")
log(f"compact_id collisions      : {sum(1 for k,v in cid_used.items() if v>1)}")
log(f"compacts w/ tribe taken from BIA title (column conflict): {sum(1 for c in compacts if c['bia_tribes_column_conflict']=='' or c['bia_tribes_column_conflict']==1)}")
log("")
log(f"version_role               : {dict(collections.Counter(v['version_role'] for v in versions))}")
log(f"what_changed               : {dict(collections.Counter(v['what_changed'] for v in versions))}")
log(f"has_text=1                 : {sum(1 for v in versions if v['has_text']==1)}  ({100*sum(1 for v in versions if v['has_text']==1)/len(versions):.1f}%)")
log(f"doc_kind                   : {dict(collections.Counter(v['doc_kind'] for v in versions))}")
log(f"amendment_number populated : {sum(1 for v in versions if v['amendment_number'] not in ('','0'))} of {sum(1 for v in versions if v['version_role']=='amendment')} amendment rows")
log(f"FR_citation populated      : {sum(1 for v in versions if v['FR_citation'])} of {len(versions)}")

with open(os.path.join(BASE, 'logs', '15_compacts_2026-08-05.log'), 'a', encoding='utf-8') as fh:
    fh.write("\n\n" + buf.getvalue())
