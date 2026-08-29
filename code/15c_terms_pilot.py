#!/usr/bin/env python3
"""
15c_terms_pilot.py -- Cedar Press Compacts dataset, Step D (terms PILOT).

Selects a stratified pilot of compact instruments (state x era x approval_type),
re-extracts text PAGE BY PAGE from the local PDFs (the pre-existing .txt sidecars
carry no page delimiters, so they cannot support the required source_page field),
runs candidate term extractors, and writes:

  data/interim/terms_pilot_candidates.csv   machine-readable candidates
  data/interim/terms_pilot_review.md        quote-by-quote sheet for manual adjudication

Nothing here is written to data/clean. Every candidate carries the verbatim
quote and the 1-based PDF page it came from so a human can check it.
"""
import csv, os, re, sys, collections, random, io, json
import fitz  # PyMuPDF

BASE  = r"C:\Users\esm247\Desktop\Cedar Press"
EXT   = os.path.join(BASE, "data", "raw", "external", "compacts")
PDF   = os.path.join(EXT, "pdf")
CLEAN = os.path.join(BASE, "data", "clean")
INT   = os.path.join(BASE, "data", "interim")
os.makedirs(INT, exist_ok=True)

versions = list(csv.DictReader(open(os.path.join(CLEAN, 'compact_versions.csv'), encoding='utf-8')))
compacts = {c['compact_id']: c for c in csv.DictReader(open(os.path.join(CLEAN, 'compacts.csv'), encoding='utf-8'))}

# --------------------------------------------------------------- pilot sample
def era(d):
    y = int(d[:4])
    return '1990s' if y < 2000 else '2000s' if y < 2010 else '2010s' if y < 2020 else '2020s'

pool = [v for v in versions
        if v['has_text'] == '1'
        and v['version_role'] == 'original-instrument'
        and int(v['text_chars']) >= 20000]
for v in pool:
    v['_state'] = compacts[v['compact_id']]['state']
    v['_era'] = era(v['approval_date'])
    v['_tribe'] = compacts[v['compact_id']]['tribe']

# one per (state, era) cell, largest doc first; then top up on approval_type coverage
cells = collections.defaultdict(list)
for v in pool: cells[(v['_state'], v['_era'])].append(v)
pick, seen_tribe = [], set()
for k in sorted(cells):
    best = sorted(cells[k], key=lambda x: -int(x['text_chars']))
    for b in best:
        if b['_tribe'] not in seen_tribe:
            pick.append(b); seen_tribe.add(b['_tribe']); break

# guarantee deemed-approved and secretarial-procedures representation
for at in ('deemed-approved', 'secretarial-procedures'):
    have = sum(1 for p in pick if p['approval_type'] == at)
    if have < 4:
        extra = sorted([v for v in pool if v['approval_type'] == at and v not in pick],
                       key=lambda x: -int(x['text_chars']))
        for e in extra[:4 - have]: pick.append(e)

# cap at 30, keeping state spread
random.seed(20260805)
if len(pick) > 30:
    bystate = collections.defaultdict(list)
    for p in pick: bystate[p['_state']].append(p)
    pick2, i = [], 0
    while len(pick2) < 30:
        added = False
        for s in sorted(bystate):
            if i < len(bystate[s]) and len(pick2) < 30:
                pick2.append(bystate[s][i]); added = True
        if not added: break
        i += 1
    pick = pick2

print(f"pilot size: {len(pick)}")
print("states:", sorted(set(p['_state'] for p in pick)))
print("eras  :", dict(collections.Counter(p['_era'] for p in pick)))
print("atype :", dict(collections.Counter(p['approval_type'] for p in pick)))

# --------------------------------------------------------------- extractors
NUMWORD = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,
           'nine':9,'ten':10,'eleven':11,'twelve':12,'fifteen':15,'twenty':20,
           'twenty-five':25,'thirty':30,'fifty':50,'one hundred':100}

def norm(s):
    s = s.replace('\u00a0', ' ')
    return re.sub(r'[ \t]+', ' ', s)

def ctx(page_text, m, before=180, after=220):
    a = max(0, m.start() - before); b = min(len(page_text), m.end() + after)
    return norm(page_text[a:b]).replace('\n', ' ').strip()

DEVICE = r'(?:gaming\s+devices?|gaming\s+machines?|slot\s+machines?|video\s+lottery\s+terminals?|electronic\s+gaming\s+devices?|player\s+terminals?|video\s+gaming\s+machines?)'

P_CAP = [
    ('machine_cap', re.compile(r'(?:no\s+more\s+than|not\s+(?:to\s+)?exceed(?:ing)?|maximum\s+of|limited\s+to|up\s+to)\s+(?:a\s+total\s+of\s+)?([\d][\d,]{1,7})\s*(?:\([^)]{0,30}\)\s*)?' + DEVICE, re.I)),
    ('machine_cap', re.compile(r'([\d][\d,]{1,7})\s*(?:\([^)]{0,30}\)\s*)?' + DEVICE + r'[^.]{0,60}?(?:maximum|limit|cap\b)', re.I)),
]
P_RATE = [
    ('revenue_share_rate', re.compile(r'([\d]{1,2}(?:\.\d{1,3})?)\s*(?:%|percent)\s+of\s+(?:the\s+)?((?:net\s+win|net\s+revenues?|gross\s+(?:gaming\s+)?revenues?|adjusted\s+gross\s+(?:gaming\s+)?(?:receipts|revenues?)|win|revenue)[^.,;]{0,50})', re.I)),
    ('revenue_share_rate', re.compile(r'(?:shall\s+pay|payment\s+of|contribute)[^.]{0,120}?([\d]{1,2}(?:\.\d{1,3})?)\s*(?:%|percent)', re.I)),
]
P_BASE = [
    ('revenue_share_base', re.compile(r'"?(net\s+win|net\s+revenues?|gross\s+gaming\s+revenues?|adjusted\s+gross\s+(?:gaming\s+)?(?:receipts|revenues?))"?\s+means', re.I)),
]
P_TIER = [
    ('tier_structure', re.compile(r'(?:tier|graduated|schedule\s+of\s+(?:payments|fees)|sliding\s+scale)[^.]{0,200}?\d{1,2}\s*(?:%|percent)', re.I)),
]
P_EXCL = [
    ('exclusivity', re.compile(r'(substantial\s+exclusivity|exclusive\s+right\s+to\s+(?:operate|conduct)|exclusivity\s+(?:provision|clause|of\s+the\s+right))', re.I)),
]
P_LOCAL = [
    ('local_share', re.compile(r'((?:local|county|municipal|city)\s+(?:government|agenc\w+|jurisdiction)[^.]{0,140}?(?:mitigat\w+|payment|fund|contribut\w+))', re.I)),
    ('local_share', re.compile(r'((?:special\s+distribution|revenue\s+sharing\s+trust)\s+fund)', re.I)),
]
P_DISP = [
    ('dispute_provision', re.compile(r'(binding\s+arbitration|American\s+Arbitration\s+Association|arbitration\s+(?:in\s+accordance|pursuant\s+to|shall\s+be)|dispute\s+resolution)', re.I)),
]
P_SCOPE = [
    ('game_scope', re.compile(r'(?:authorized|permitted|may\s+operate|shall\s+be\s+authorized\s+to\s+(?:operate|conduct))[^.]{0,40}?(?:class\s+III\s+gam\w+|the\s+following\s+(?:class\s+III\s+)?games)', re.I)),
    ('game_scope', re.compile(r'(class\s+III\s+games?\s+(?:authorized|permitted)[^.]{0,80})', re.I)),
]
P_TERM = [
    ('_term_years', re.compile(r'(?:this\s+(?:Compact|Agreement)|the\s+(?:Compact|Agreement))[^.]{0,120}?(?:shall\s+(?:be\s+in\s+effect|remain\s+in\s+(?:full\s+force\s+and\s+)?effect|continue\s+in\s+effect|have\s+a\s+term)|for\s+a\s+(?:term|period)\s+of)[^.]{0,60}?((?:\b\w+\b[- ]?\w*)\s*\(\s*(\d{1,2})\s*\)|\b(\d{1,2})\b)\s*(?:\(\d{1,2}\)\s*)?years?', re.I)),
    ('_term_end_date', re.compile(r'(?:shall\s+(?:expire|terminate)|expires?|terminat\w+)\s+on\s+(?:the\s+)?(\w+\s+\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{2,4})', re.I)),
]

ALL = P_CAP + P_RATE + P_BASE + P_TIER + P_EXCL + P_LOCAL + P_DISP + P_SCOPE + P_TERM

FACILITY = re.compile(r'(per\s+(?:gaming\s+)?facilit\w+|at\s+each\s+(?:gaming\s+)?facilit\w+|in\s+any\s+one\s+(?:gaming\s+)?facilit\w+|each\s+such\s+facilit\w+|per\s+(?:casino|establishment)|any\s+single\s+(?:gaming\s+)?facilit\w+)', re.I)
STATEWIDE = re.compile(r'(in\s+the\s+aggregate|total\s+number|aggregate\s+number|all\s+(?:of\s+the\s+)?(?:tribe|tribal)[\'\u2019]?s?\s+(?:gaming\s+)?facilit\w+|throughout\s+the\s+state|tribe\s+may\s+operate)', re.I)

def applies_to(quote):
    if FACILITY.search(quote): return 'facility'
    if STATEWIDE.search(quote): return 'statewide'
    return ''

cands = []
for v in pick:
    p = os.path.join(PDF, v['source_pdf'])
    try:
        doc = fitz.open(p)
    except Exception as e:
        print("OPEN FAIL", v['source_pdf'], e); continue
    pages = [doc[i].get_text() for i in range(len(doc))]
    doc.close()
    seen = set()
    for pi, ptxt in enumerate(pages, start=1):
        pt = norm(ptxt)
        for ttype, rx in ALL:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                key = (ttype, q[:120])
                if key in seen: continue
                seen.add(key)
                val, unit = '', ''
                if ttype == 'machine_cap':
                    val = m.group(1).replace(',', ''); unit = 'devices'
                elif ttype == 'revenue_share_rate':
                    val = m.group(1); unit = 'percent'
                elif ttype == 'revenue_share_base':
                    val = m.group(1).lower(); unit = 'definition'
                elif ttype == '_term_years':
                    val = (m.group(2) or m.group(3) or ''); unit = 'years'
                elif ttype == '_term_end_date':
                    val = m.group(1); unit = 'date'
                else:
                    val = (m.group(1) if m.groups() else m.group(0))[:120]; unit = 'text'
                cands.append(dict(
                    version_id=v['version_id'], compact_id=v['compact_id'],
                    state=v['_state'], tribe=v['_tribe'], approval_type=v['approval_type'],
                    approval_date=v['approval_date'],
                    term_type=ttype, value=val, unit=unit,
                    applies_to=applies_to(q), source_page=pi,
                    quote=q, pattern=rx.pattern[:60],
                    source_pdf=v['source_pdf'], n_pages=len(pages)))

with open(os.path.join(INT, 'terms_pilot_candidates.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['version_id','compact_id','state','tribe','approval_type',
        'approval_date','term_type','value','unit','applies_to','source_page','quote','pattern',
        'source_pdf','n_pages'])
    w.writeheader()
    for c in cands: w.writerow(c)

print(f"\ncandidates: {len(cands)}")
print(dict(collections.Counter(c['term_type'] for c in cands)))
print("docs with >=1 candidate:", len(set(c['version_id'] for c in cands)), "of", len(pick))

# review sheet: cap the noisy categories so a human can actually read it
LIMIT = {'dispute_provision':2, 'exclusivity':2, 'game_scope':2, 'local_share':2,
         'tier_structure':2, 'revenue_share_base':2, 'revenue_share_rate':6,
         'machine_cap':6, '_term_years':3, '_term_end_date':3}
with open(os.path.join(INT, 'terms_pilot_review.md'), 'w', encoding='utf-8') as fh:
    for v in pick:
        cs = [c for c in cands if c['version_id'] == v['version_id']]
        fh.write(f"\n\n## {v['_state']} | {v['_tribe']} | {v['approval_date']} | {v['approval_type']}\n")
        fh.write(f"`{v['source_pdf']}`  ({cs[0]['n_pages'] if cs else '?'} pp)\n\n")
        if not cs:
            fh.write("  (NO CANDIDATES)\n"); continue
        byt = collections.defaultdict(list)
        for c in cs: byt[c['term_type']].append(c)
        for t in sorted(byt):
            fh.write(f"### {t}\n")
            for c in byt[t][:LIMIT.get(t, 3)]:
                fh.write(f"- **{c['value']}** [{c['unit']}] applies_to=`{c['applies_to'] or 'UNSET'}` p.{c['source_page']}\n")
                fh.write(f"  > {c['quote'][:420]}\n")
            if len(byt[t]) > LIMIT.get(t, 3):
                fh.write(f"  _(+{len(byt[t]) - LIMIT.get(t,3)} more)_\n")
print("[written] data/interim/terms_pilot_review.md")
