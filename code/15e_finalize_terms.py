#!/usr/bin/env python3
"""
15e_finalize_terms.py -- Cedar Press Compacts dataset, Step E.

Turns the corpus-wide candidate file into:
  data/clean/compact_terms.csv        (plan enum only: machine_cap, game_scope,
                                       exclusivity, revenue_share_rate,
                                       revenue_share_base, tier_structure,
                                       local_share, dispute_provision)
  data/interim/compact_duration_candidates.csv
                                      (term length / term end / renewal quotes --
                                       these are NOT compact_terms term_types;
                                       they feed compacts.term_end and
                                       compacts.renewal_provisions)
and back-fills compacts.csv term_end / renewal_provisions / status.

term_end rules (no inference):
  T1  explicit end date stated in the instrument               -> basis 'instrument_text'
  T2  explicit end date stated in the BIA extension title      -> basis set in 15b, kept
  T3  stated term length N years AND the text ties the term to
      the effective date ("from the date it becomes effective")
      AND original_effective_date is known                     -> arithmetic, basis recorded
  Anything else stays blank.
"""
import csv, os, re, collections, datetime, io

BASE  = r"C:\Users\esm247\Desktop\Cedar Press"
CLEAN = os.path.join(BASE, "data", "clean")
INT   = os.path.join(BASE, "data", "interim")
RUNDATE = datetime.date(2026, 8, 5)

buf = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")

ENUM = {'machine_cap','game_scope','exclusivity','revenue_share_rate',
        'revenue_share_base','tier_structure','local_share','dispute_provision'}

cand = list(csv.DictReader(open(os.path.join(INT, 'terms_candidates_full.csv'), encoding='utf-8')))
compacts = list(csv.DictReader(open(os.path.join(CLEAN, 'compacts.csv'), encoding='utf-8')))
versions = list(csv.DictReader(open(os.path.join(CLEAN, 'compact_versions.csv'), encoding='utf-8')))
cbyid = {c['compact_id']: c for c in compacts}
vbyid = {v['version_id']: v for v in versions}

# Re-stamp version_id / compact_id / tribe from the CURRENT versions table using
# source_pdf as the join key. The extraction run and the index build are separate
# steps; this guarantees the terms table never carries a stale identifier.
by_pdf = collections.defaultdict(list)
for v in versions:
    if v['source_pdf']: by_pdf[v['source_pdf']].append(v)
n_restamp = n_drop = 0
fixed = []
for c in cand:
    vs = by_pdf.get(c['source_pdf'], [])
    if len(vs) != 1:
        n_drop += 1; continue          # ambiguous or missing -- do not guess
    v = vs[0]
    if c['version_id'] != v['version_id']: n_restamp += 1
    c['version_id'], c['compact_id'] = v['version_id'], v['compact_id']
    c['tribe'] = cbyid[v['compact_id']]['tribe']
    c['state'] = cbyid[v['compact_id']]['state']
    fixed.append(c)
cand = fixed

log("=" * 78); log("STEP E -- TERMS FINALISATION"); log("=" * 78)
log(f"candidates in: {len(cand)}  (restamped ids: {n_restamp}; dropped ambiguous/unmatched pdf: {n_drop})")
log(f"by term_type : {dict(collections.Counter(c['term_type'] for c in cand))}")

# ------------------------------------------------------------------ compact_terms
TF = ['version_id','term_type','value','unit','applies_to','source_page',
      'compact_id','tribe','state','quote','doc_zone','extraction_method',
      'pilot_validated_type','source_pdf']
PILOT_N = {
 'machine_cap':        'pilot 1/1; corpus spot check 11/12 values correct, applies_to errs toward UNSET',
 'game_scope':         'pilot 6/6 (locates the authorised-games section; does not enumerate games)',
 'exclusivity':        'pilot 12/12 sampled pre-dedup',
 'revenue_share_rate': 'pilot 4/4; corpus spot check 7/12 clear, 2/12 wrong, 3/12 unverifiable '
                       '-> strict quote re-verification applied in 15e',
 'revenue_share_base': 'pilot 14/14 sampled of 19; correct as DEFINED TERM, over-claims where the '
                       'instrument defines the term but shares no revenue',
 'dispute_provision':  'pilot 8/8',
 'tier_structure':     'NO pilot hits; corpus sample 8/10 correct content; value is located '
                       'schedule text, brackets are NOT parsed',
 'local_share':        'NO pilot hits; corpus sample 9/10 correct as a located provision'}

# ---------------------------------------------------------------- re-verification
# A corpus-scale spot check (12 random rows per type) showed revenue_share_rate
# degrading badly outside the 34-document pilot: the "pay ... N percent" form
# allows up to 140 characters between the payment verb and the numeral, so it
# picked up numbers belonging to a different clause (Little Traverse Bay 2010
# returned 10 from a sentence stating 8%; Pokagon returned 2 from a heading
# about payments to LOCAL units of government). machine_cap likewise re-admitted
# one recital of a PRIOR compact whose "WHEREAS" fell outside the match window
# (Cahuilla: "...by which the Tribe WAS AUTHORIZED to operate up to 2,000").
#
# Rather than re-run the corpus, each surviving candidate is re-verified against
# its own retained quote with a strict pattern. Rows that cannot be re-derived
# from their quote are DROPPED, not downgraded.
def rate_verified(value, quote):
    v = re.escape(value.rstrip('0').rstrip('.') if '.' in value else value)
    tok = rf'{v}(?:\.\d+)?\s*(?:%|percent)'
    # (a) numeral sits close to a payment verb, or
    if re.search(rf'(?:pay|pays|shall\s+pay|contribut\w+|remit\w*|payment)[^.]{{0,60}}?{tok}',
                 quote, re.I): return True
    # (b) numeral is immediately qualified by the revenue base it applies to
    if re.search(rf'{tok}\s*\)?\s*(?:\([^)]{{0,20}}\)\s*)?of\s+(?:the\s+|its\s+)?'
                 r'(?:annual\s+|quarterly\s+|adjusted\s+|combined\s+)?'
                 r'(?:net\s+win|net\s+revenue|gross\s+(?:gaming\s+)?revenue|'
                 r'adjusted\s+gross|class\s+I{2,3}\s+net\s+win)', quote, re.I): return True
    return False

CAP_RECITAL = re.compile(r'(WHEREAS|was\s+authorized\s+to\s+operate|'
                         r'pact"\)\s*,?\s*by\s+which|under\s+the\s+\d{4}\s+Compact)', re.I)

terms, dropped = [], collections.Counter()
for c in cand:
    if c['term_type'] not in ENUM: continue
    if c['term_type'] == 'revenue_share_rate' and not rate_verified(c['value'], c['quote']):
        dropped['revenue_share_rate'] += 1; continue
    if c['term_type'] == 'machine_cap' and CAP_RECITAL.search(c['quote']):
        dropped['machine_cap'] += 1; continue
    # tier_structure's raw regex groups are unusable as a value; the schedule
    # itself lives in the quote, so the value is the located schedule text.
    if c['term_type'] == 'tier_structure':
        m = re.search(r'\d{1,2}(?:\.\d+)?\s*(?:%|percent).{0,220}', c['quote'], re.S)
        c['value'] = re.sub(r'\s+', ' ', m.group(0)).strip() if m else ''
        c['unit'] = 'schedule_text_located'
    terms.append(dict(c,
        extraction_method='regex v4 (15d_terms_extract.py) + quote re-verification (15e), '
                          'verbatim quote and PDF page retained',
        pilot_validated_type=PILOT_N.get(c['term_type'], '')))
log(f"re-verification drops: {dict(dropped)}")

with open(os.path.join(CLEAN, 'compact_terms.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=TF, extrasaction='ignore'); w.writeheader()
    for t in sorted(terms, key=lambda r: (r['version_id'], r['term_type'], int(r['source_page']))):
        w.writerow(t)
log("")
log(f"compact_terms.csv rows : {len(terms)}")
log(f"  by term_type         : {dict(collections.Counter(t['term_type'] for t in terms))}")
log(f"  by doc_zone          : {dict(collections.Counter(t['doc_zone'] for t in terms))}")
log(f"  applies_to           : {dict(collections.Counter(t['applies_to'] or 'UNSET' for t in terms))}")
log(f"  distinct versions     : {len(set(t['version_id'] for t in terms))} of {len(versions)}")
log(f"  distinct compacts     : {len(set(t['compact_id'] for t in terms))} of {len(compacts)}")

# ------------------------------------------------------------------ duration layer
dur = [c for c in cand if c['term_type'].startswith('_')]
with open(os.path.join(INT, 'compact_duration_candidates.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(cand[0].keys()), extrasaction='ignore'); w.writeheader()
    for d in dur: w.writerow(d)
log("")
log(f"duration candidates    : {len(dur)}  {dict(collections.Counter(d['term_type'] for d in dur))}")

MONTHS = {m.lower(): i for i, m in enumerate(
    ['January','February','March','April','May','June','July','August',
     'September','October','November','December'], 1)}
def parse_date(s):
    s = s.strip()
    m = re.match(r'^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})$', s)
    if m and m.group(1).lower() in MONTHS:
        try: return datetime.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
        except ValueError: return None
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', s)
    if m:
        y = int(m.group(3)); y += (2000 if y < 70 else 1900) if y < 100 else 0
        try: return datetime.date(y, int(m.group(1)), int(m.group(2)))
        except ValueError: return None
    return None

TIED = re.compile(r'(from\s+the\s+date\s+it\s+becomes\s+effective|from\s+the\s+effective\s+date|'
                  r'following\s+the\s+effective\s+date|after\s+(?:this|the)\s+Compact\s+becomes\s+effective|'
                  r'from\s+the\s+date\s+of\s+(?:its\s+)?(?:approval|publication))', re.I)

# index duration evidence by compact, preferring the original instrument
by_compact = collections.defaultdict(lambda: collections.defaultdict(list))
for d in dur:
    v = vbyid.get(d['version_id'])
    if not v: continue
    by_compact[d['compact_id']][d['term_type']].append((v['version_role'], d))

n_t1 = n_t3 = n_renew = 0
for c in compacts:
    ev = by_compact.get(c['compact_id'], {})
    # T1 explicit end date
    if not c['term_end']:
        for role, d in sorted(ev.get('_term_end_date', []), key=lambda x: x[0] != 'original-instrument'):
            dt = parse_date(d['value'])
            if dt:
                c['term_end'] = dt.isoformat()
                c['term_end_basis'] = (f"explicit termination date in instrument text, "
                                       f"{d['source_pdf']} p.{d['source_page']}")
                n_t1 += 1
                break
    # T3 stated term length tied to the effective date
    if not c['term_end'] and c['original_effective_date']:
        for role, d in sorted(ev.get('_term_years', []), key=lambda x: x[0] != 'original-instrument'):
            if not TIED.search(d['quote']): continue
            try:
                y = int(d['value'])
                eff = datetime.date.fromisoformat(c['original_effective_date'])
                c['term_end'] = eff.replace(year=eff.year + y).isoformat()
                c['term_end_basis'] = (f"computed: stated term of {y} years running from the "
                                       f"effective date ({c['original_effective_date']}, "
                                       f"{c['original_effective_date_basis']}); quote at "
                                       f"{d['source_pdf']} p.{d['source_page']}")
                n_t3 += 1
            except (ValueError, KeyError):
                pass
            break
    # renewal provisions -- verbatim quote, never paraphrased
    if not c['renewal_provisions']:
        rs = sorted(ev.get('_renewal', []), key=lambda x: x[0] != 'original-instrument')
        if rs:
            d = rs[0][1]
            c['renewal_provisions'] = re.sub(r'\s+', ' ', d['value'])[:300]
            n_renew += 1

# recompute status now that term_end may exist
sc = collections.Counter()
for c in compacts:
    if c['successor_compact_id']:
        c['status'] = 'renegotiated'
        c['status_basis'] = 'a later base instrument for the same state+tribe appears in the BIA index'
    elif c['term_end']:
        d = datetime.date.fromisoformat(c['term_end'])
        c['status'] = 'expired' if d < RUNDATE else 'active'
        c['status_basis'] = f"term_end ({c['term_end_basis'][:60]}...) compared to run date {RUNDATE}"
    else:
        c['status'] = 'unknown'
        c['status_basis'] = 'no successor in BIA index and no explicitly stated term_end'
    sc[c['status']] += 1

hdr = list(compacts[0].keys())
with open(os.path.join(CLEAN, 'compacts.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=hdr); w.writeheader()
    for c in compacts: w.writerow(c)

log("")
log(f"term_end filled from explicit instrument date (T1) : {n_t1}")
log(f"term_end computed from stated term + eff date (T3) : {n_t3}")
log(f"term_end total populated                           : {sum(1 for c in compacts if c['term_end'])} of {len(compacts)}")
log(f"renewal_provisions populated                       : {sum(1 for c in compacts if c['renewal_provisions'])}")
log(f"status                                             : {dict(sc)}")

with open(os.path.join(BASE, 'logs', '15_compacts_2026-08-05.log'), 'a', encoding='utf-8') as fh:
    fh.write("\n\n" + buf.getvalue())
