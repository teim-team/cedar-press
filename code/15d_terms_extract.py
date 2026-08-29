#!/usr/bin/env python3
"""
15d_terms_extract.py -- Cedar Press Compacts dataset, Step D2 (terms, v2).

v1 (15c) was run on a 30-document stratified pilot and manually adjudicated.
Measured failure modes, and the v2 response to each:

  FM1  Table-of-contents lines matched as if they were substantive provisions
       (dominant failure for dispute_provision / game_scope).
       -> TOC guard: reject any window with dot-leaders, or >=3 trailing page
          numbers, or on a page whose text is >25% dot characters.
  FM2  Theoretical-payout percentages ("shall pay out a minimum of 80 percent
       of the amount wagered") extracted as revenue-sharing rates.
       -> revenue_share_rate now REQUIRES a payment-to-state anchor and REJECTS
          payout/jackpot/withholding/odds windows.
  FM3  "two and one-half percent (2-1/2%)" captured as 2.
       -> parenthesised numeral preferred; "n-1/2" / "n 1/2" normalized.
  FM4  Machine-cap regex caught transfer limits and revenue-tier thresholds
       ("so long as the Tribe operates no more than 750 Gaming Devices ... its
       payments shall be based on the following schedule").
       -> cap now REQUIRES an authorisation anchor and REJECTS transfer/payment
          windows; tier thresholds are routed to tier_structure instead.
  FM5  Quotes taken from the Secretary's approval letter bundled at the front of
       the PDF were indistinguishable from compact text -- and in one case
       (Pueblo of Santa Ana 1997) the letter says the compact does NOT provide
       substantial exclusivity, which the v1 exclusivity extractor would have
       recorded as exclusivity present.
       -> every candidate carries doc_zone (approval_letter | instrument_text);
          exclusivity additionally rejects negated windows.
  FM6  tier_structure never fired (0 recall).
       -> rewritten around the "N% of the first/next $X" construction.

Outputs data/interim/terms_candidates_v2.csv and a review sheet. Nothing goes
to data/clean until the pilot re-adjudication in 15e.
"""
import csv, os, re, sys, collections, io, argparse
import fitz
from pathlib import Path

BASE  = str(Path(__file__).resolve().parent.parent)
EXT   = os.path.join(BASE, "data", "raw", "external", "compacts")
PDF   = os.path.join(EXT, "pdf")
CLEAN = os.path.join(BASE, "data", "clean")
INT   = os.path.join(BASE, "data", "interim")

# ------------------------------------------------------------------ helpers
def norm(s):
    return re.sub(r'[ \t]+', ' ', s.replace('\u00a0', ' '))

DOTS = re.compile(r'\.{5,}|\. \. \. \.|\·{5,}')
PAGENUM = re.compile(r'\s\d{1,3}\s*(?:\n|$)')
def is_toc(window, page_text):
    if DOTS.search(window): return True
    if page_text.count('.') > 0.18 * max(len(page_text), 1): return True
    if len(PAGENUM.findall(window)) >= 3: return True
    if re.search(r'TABLE\s+OF\s+CONTENTS', page_text[:2500], re.I) and len(window) < 600 \
       and len(re.findall(r'\b\d{1,3}\b', window)) >= 4: return True
    return False

LETTER = re.compile(r'(Sincerely|Assistant Secretary\s*[-\u2013]?\s*Indian Affairs|'
                    r'Principal Deputy Assistant Secretary|Dear (Chairman|Chairwoman|President|Governor|Chairperson))', re.I)
BODY = re.compile(r'(WITNESSETH|^\s*RECITALS|TABLE\s+OF\s+CONTENTS|'
                  r'^\s*(SECTION|ARTICLE|PART)\s+(1|I|ONE)\b|^\s*PREAMBLE)', re.I | re.M)
def letter_pages(pages):
    """v3: the Secretary's transmittal/approval letter is the LEADING run of
    pages before the instrument body begins. v2 took the last letter-marker page
    within the first 25, which mis-zoned signature blocks inside the compact
    (observed on Standing Rock 2020 and Hannahville 1993)."""
    first_body = None
    for i, p in enumerate(pages[:40]):
        if BODY.search(p): first_body = i; break
    if first_body is None:
        last = -1
        for i, p in enumerate(pages[:10]):
            if LETTER.search(p): last = i
        return set(range(0, last + 1)) if last >= 0 else set()
    if not any(LETTER.search(p) for p in pages[:max(first_body, 1)]): return set()
    return set(range(0, first_body))

def num(s):
    """'2-1/2' -> 2.5 ; '12' -> 12 ; '7.5' -> 7.5"""
    s = s.strip().replace(',', '')
    m = re.match(r'^(\d+)\s*[-\s]\s*1/2$', s)
    if m: return float(m.group(1)) + 0.5
    m = re.match(r'^(\d+)\s*[-\s]\s*1/4$', s)
    if m: return float(m.group(1)) + 0.25
    m = re.match(r'^(\d+)\s*[-\s]\s*3/4$', s)
    if m: return float(m.group(1)) + 0.75
    try:
        f = float(s)
        return int(f) if f == int(f) else f
    except ValueError:
        return None

def ctx(t, m, before=200, after=260):
    a = max(0, m.start() - before); b = min(len(t), m.end() + after)
    return norm(t[a:b]).replace('\n', ' ').strip()

DEVICE = (r'(?:gaming\s+devices?|gaming\s+machines?|slot\s+machines?|video\s+lottery\s+terminals?'
          r'|electronic\s+gaming\s+devices?|player\s+terminals?|video\s+gaming\s+machines?'
          r'|electronic\s+games?\s+of\s+chance)')
PCT = r'(\d{1,2}(?:\.\d{1,3})?|\d{1,2}\s*[-\s]\s*(?:1/2|1/4|3/4))'

# ------------------------------------------------------------------ extractors
CAP_RX = [
 re.compile(r'(?:authorized\s+to\s+operate|may\s+operate|shall\s+(?:not\s+)?operate|'
            r'operate\s+no\s+more\s+than|limited\s+to|shall\s+not\s+exceed|not\s+to\s+exceed|'
            r'maximum\s+of|no\s+more\s+than|up\s+to)\s+(?:a\s+total\s+of\s+)?([\d][\d,]{1,7})'
            r'\s*(?:\([^)]{0,30}\)\s*)?' + DEVICE, re.I),
 re.compile(r'(?:total\s+(?:number\s+of\s+)?|aggregate\s+(?:number\s+of\s+)?|maximum\s+number\s+of\s+)'
            + DEVICE + r'[^.]{0,60}?(?:shall\s+not\s+exceed|is|shall\s+be)\s+([\d][\d,]{1,7})', re.I),
]
CAP_ANCHOR = re.compile(r'(authorized\s+to\s+operate|may\s+operate|number\s+of\s+gaming\s+devices|'
                        r'gaming\s+device\s+allocation|authorized\s+number|maximum\s+number|'
                        r'scope\s+of\s+gaming|shall\s+not\s+operate|slots\s+only)', re.I)
CAP_REJECT = re.compile(r'(transfer|payments?\s+shall\s+be\s+based|schedule\s+based\s+on|'
                        r'so\s+long\s+as\s+the\s+tribe\s+operates[^.]{0,120}payment|'
                        r'if\s+the\s+tribe\s+is\s+(?:the\s+)?navajo|'
                        # v3 FM7: a limit on NON-tribal operators is not the tribe's cap
                        # (Pueblo of Tesuque 2015: "racinos may operate a maximum of 750")
                        r'non-?tribal|racino|commercial\s+(?:casino|operator)|card\s?room|'
                        r'pari-?mutuel\s+permit|'
                        # v3 FM8: recitals describing a PRIOR instrument
                        # (Chemehuevi 2021 procedures reciting the 1999 Compact)
                        r'WHEREAS|\b(?:19|20)\d{2}\s+Compact\b|previously\s+authorized|'
                        r'under\s+the\s+prior)', re.I)
# v3 FM9: the capped operator must be the tribe itself
CAP_SUBJECT = re.compile(r'(the\s+Tribes?\b[^.]{0,80}?(?:is|are|shall\s+be)\s+authorized|'
                         r'the\s+Tribes?\s+(?:may|shall)\s+(?:not\s+)?operate|'
                         r'the\s+(?:Tribes?|Pueblo|Nation|Band|Community)\b[^.]{0,60}?'
                         r'(?:authorized\s+to\s+operate|may\s+operate|shall\s+operate)|'
                         r'authorized\s+number\s+of\s+gaming\s+devices|'
                         r'gaming\s+device\s+allocation)', re.I)

RATE_RX = [
 re.compile(r'(?:pay|contribute|remit|transfer)[^.]{0,140}?' + PCT + r'\s*(?:%|percent)', re.I),
 # v3 FM13 (recall): "Eight Percent (8.00%) of the Adjusted Net Win" -- the
 # closing paren after the numeral defeated the v2 form. Otoe-Missouria 2020.
 re.compile(PCT + r'\s*(?:%|percent)\s*\)?\s*(?:\([^)]{0,20}\)\s*)?of\s+(?:the\s+|its\s+)?'
            r'(?:annual\s+|quarterly\s+|adjusted\s+)?(net\s+win|net\s+revenues?|'
            r'gross\s+(?:gaming\s+)?revenues?|adjusted\s+gross\s+(?:gaming\s+)?(?:receipts|revenues?)|'
            r'class\s+I{2,3}\s+net\s+win)', re.I),
]
RATE_ANCHOR = re.compile(r'(pay\s+(?:to\s+)?the\s+state|payments?\s+to\s+the\s+state|'
                         r'contribut\w+\s+to\s+the\s+state|tribal\s+contribution|revenue[- ]shar\w+|'
                         r'state[\'\u2019]?s?\s+share|remit\w*\s+to\s+the\s+state|shall\s+pay\s+the\s+state|'
                         r'pay\s+to\s+the\s+(?:commonwealth|state)|revenue\s+sharing\s+trust\s+fund|'
                         r'consideration\s+for\s+the\s+substantial\s+exclusivity)', re.I)
RATE_REJECT = re.compile(r'(pay\s*out|payout|theoretical|amount\s+wagered|jackpot|'
                         r'return\s+to\s+the\s+player|prize|odds|withhold|w-?2g|'
                         r'interest|penalt|probability|hold\s+percentage|payback|'
                         # v3 FM10: derived, directional or installment percentages
                         # (Seminole "Monthly Payment shall be 8.333% of the estimated
                         # Revenue Share Payment"; "reduced by 10 percent"; Fort Sill
                         # "payment FROM the State to eligible tribes of 50%")
                         r'reduce[d]?\s+by|reduction\s+of|increase[d]?\s+by|'
                         r'of\s+the\s+estimated|monthly\s+payment\s+shall\s+be|'
                         r'payment\s+from\s+the\s+State|State\s+shall\s+pay|'
                         r'to\s+eligible\s+tribes|any\s+increase\s+in)', re.I)

TIER_RX = [
 re.compile(PCT + r'\s*(?:%|percent)\s+of\s+the\s+(first|next|last|remaining)\s*\$?\s*'
            r'([\d][\d,\.]{0,15})\s*(million|billion)?', re.I),
 re.compile(r'(?:in\s+excess\s+of|exceed(?:ing|s)?|over)\s+\$?\s*([\d][\d,\.]{0,15})\s*(million|billion)?'
            r'[^.]{0,60}?' + PCT + r'\s*(?:%|percent)', re.I),
]

BASE_RX = [
 re.compile(r'"?(net\s+win|net\s+revenues?|gross\s+gaming\s+revenues?|'
            r'adjusted\s+gross\s+(?:gaming\s+)?(?:receipts|revenues?)|class\s+I{2,3}\s+net\s+win)"?\s*'
            r'(?:means|shall\s+mean|is\s+defined)', re.I),
]

EXCL_RX = [
 re.compile(r'(substantial\s+exclusivity|exclusive\s+right\s+to\s+(?:operate|conduct)|'
            r'exclusivity\s+(?:covenant|provision)s?)', re.I),
]
EXCL_REJECT = re.compile(r'(does\s+not\s+provide|questions?\s+whether|fails?\s+to\s+provide|'
                         r'no\s+substantial\s+exclusivity|lack\w*\s+substantial|'
                         r'has\s+consistently\s+recognized|the\s+department\s+has)', re.I)

LOCAL_RX = [
 re.compile(r'((?:local\s+revenue\s+sharing\s+board|county|municipal|city|local\s+government)'
            r'[^.]{0,160}?(?:shall\s+(?:receive|be\s+paid)|payment\s+of|semi-?annual\s+payment|'
            r'shall\s+pay|mitigation\s+(?:payment|fund)))', re.I),
 re.compile(r'((?:mitigation|impact)\s+(?:payment|fund|agreement)[^.]{0,120}?'
            r'(?:county|city|local|municipal))', re.I),
]

DISP_RX = [
 re.compile(r'(shall\s+be\s+submitted\s+to\s+binding\s+arbitration|'
            r'submitted\s+to\s+(?:non-?)?binding\s+arbitration|'
            r'(?:may|shall)\s+invoke\s+arbitration|'
            r'arbitration\s+(?:shall\s+be\s+)?conducted\s+under\s+the\s+[^.]{0,60}rules)', re.I),
 re.compile(r'(consent\s+to\s+(?:the\s+)?jurisdiction\s+of\s+the\s+(?:United\s+States\s+)?[Dd]istrict\s+[Cc]ourt|'
            r'limited\s+waiver\s+of\s+sovereign\s+immunity[^.]{0,120}(?:dispute|enforce))', re.I),
]

SCOPE_RX = [
 re.compile(r'(?:may\s+(?:lawfully\s+)?(?:conduct|operate|engage\s+in)|is\s+authorized\s+to\s+'
            r'(?:conduct|operate|offer|engage\s+in)|shall\s+have\s+the\s+right\s+to\s+operate)'
            r'[^.]{0,90}?(?:the\s+)?following[^.]{0,60}?(?:class\s+I{2,3}\s+)?gam\w+', re.I),
]

# v3 FM11: the duration verb must attach to the Compact itself. v2's looser
# "shall be binding" branch swept in the WA three-year AMENDMENT MORATORIUM
# (Skokomish / Tulalip / Upper Skagit all returned 3 instead of the real term).
TERM_RX = [
 re.compile(r'(?:this|the)\s+(?:Compact|Agreement|Procedures)\s+shall\s+'
            r'(?:be\s+in\s+(?:full\s+force\s+and\s+)?effect|remain\s+in\s+(?:full\s+force\s+and\s+)?effect|'
            r'continue\s+in\s+(?:full\s+force\s+and\s+)?effect|have\s+a\s+term\s+of|'
            r'be\s+binding[^.]{0,70})'
            r'[^.]{0,80}?\(\s*(\d{1,3})\s*\)\s*years?', re.I),
 re.compile(r'(?:term|duration)\s+of\s+(?:this|the)\s+(?:Compact|Agreement|Procedures)'
            r'[^.]{0,70}?\(\s*(\d{1,3})\s*\)\s*years?', re.I),
]
TERM_REJECT = re.compile(r'(license|permit|certificat|board\s+member|commissioner|'
                         r'statute\s+of\s+limitation|retain\w*\s+for|records?\s+shall\s+be\s+'
                         r'(?:kept|maintained|retained)|insurance|employ\w+\s+for|'
                         r'moratorium|seek\s+no\s+amendment|notice\s+period|cure\s+period)', re.I)

# v3 FM12: "automatically be extended to <date>" is a conditional extension, not
# the termination date (Rincon 2016 procedures: terminate 12/31/2037, auto-extend
# to 6/30/2039 -- v2 returned the latter).
TERMEND_RX = [
 re.compile(r'(?:this|these)\s+(?:Compact|Agreement|Procedures)\s+shall\s+(?:expire|terminate)'
            r'\s+on\s+(?:the\s+)?(\w+\s+\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{2,4})', re.I),
 re.compile(r'(?:shall\s+be\s+in\s+(?:full\s+force\s+and\s+)?effect|shall\s+remain\s+in\s+effect)'
            r'[^.]{0,70}?until\s+(\w+\s+\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{2,4})', re.I),
]
TERMEND_REJECT = re.compile(r'(automatically\s+be\s+extended|may\s+be\s+extended\s+to)', re.I)

RENEW_RX = [
 re.compile(r'((?:automatically\s+)?(?:renew\w*|extend\w*)[^.]{0,180}?'
            r'(?:for\s+(?:an?\s+)?(?:additional|successive|further)[^.]{0,60}?years?|'
            r'periods?\s+of\s+[^.]{0,30}years?))', re.I),
]

FACILITY = re.compile(r'(per\s+(?:gaming\s+)?facilit\w+|at\s+each\s+(?:gaming\s+)?facilit\w+|'
                      r'in\s+any\s+one\s+(?:gaming\s+)?facilit\w+|each\s+such\s+facilit\w+|'
                      r'per\s+(?:casino|establishment|premise|location)|at\s+any\s+premise|'
                      r'any\s+single\s+(?:gaming\s+)?facilit\w+|per\s+(?:gaming\s+)?site)', re.I)
STATEWIDE = re.compile(r'(in\s+the\s+aggregate|total\s+of|aggregate\s+number|total\s+number|'
                       r'all\s+(?:of\s+the\s+)?(?:tribe|tribal)[\'\u2019]?s?\s+(?:gaming\s+)?facilit\w+|'
                       r'tribe\s+is\s+authorized\s+to\s+operate|the\s+tribe\s+may\s+operate)', re.I)
# v3 FM14: a cap stated for a named/described single site is facility-scoped even
# when phrased as "a total of N" (Standing Rock 2020: "a total of 1,000 slot
# machines in a tribal establishment located in the SE1/4 of Section 35").
# Never propagate a facility-specific term tribewide -- when the two signals
# conflict and neither dominates, applies_to is left UNSET rather than guessed.
SINGLE_SITE = re.compile(r'(in\s+a\s+(?:tribal\s+)?(?:establishment|facility|casino)|'
                         r'located\s+in\s+the\s+|located\s+(?:at|on|within)\s+|'
                         r'at\s+the\s+[A-Z][A-Za-z\']+\s+(?:Casino|Facility|Center))')
def applies_to(q):
    f, s, one = FACILITY.search(q), STATEWIDE.search(q), SINGLE_SITE.search(q)
    if one: return 'facility'
    if f and not s: return 'facility'
    if f and s:     return ''          # ambiguous -- do not guess
    if s:           return 'statewide'
    return ''

SPECS = [
 ('machine_cap',        CAP_RX,     'devices', CAP_ANCHOR,  CAP_REJECT),
 ('revenue_share_rate', RATE_RX,    'percent', RATE_ANCHOR, RATE_REJECT),
 ('tier_structure',     TIER_RX,    'percent_of_bracket', RATE_ANCHOR, RATE_REJECT),
 ('revenue_share_base', BASE_RX,    'defined_term', None, None),
 ('exclusivity',        EXCL_RX,    'text',    None, EXCL_REJECT),
 ('local_share',        LOCAL_RX,   'text',    None, None),
 ('dispute_provision',  DISP_RX,    'text',    None, None),
 ('game_scope',         SCOPE_RX,   'text',    None, None),
 ('_term_years',        TERM_RX,    'years',   None, TERM_REJECT),
 ('_term_end_date',     TERMEND_RX, 'date',    None, TERMEND_REJECT),
 ('_renewal',           RENEW_RX,   'text',    None, None),
]

def extract(pdf_path):
    doc = fitz.open(pdf_path)
    pages = [doc[i].get_text() for i in range(len(doc))]
    doc.close()
    lp = letter_pages(pages)
    out, seen = [], set()
    for pi, raw in enumerate(pages):
        pt = norm(raw)
        zone = 'approval_letter' if pi in lp else 'instrument_text'
        for ttype, rxs, unit, anchor, reject in SPECS:
            for rx in rxs:
                for m in rx.finditer(pt):
                    q = ctx(pt, m)
                    if is_toc(q, pt): continue
                    if anchor and not anchor.search(q): continue
                    if reject and reject.search(q): continue
                    if ttype == 'machine_cap' and not CAP_SUBJECT.search(q): continue
                    if ttype == 'machine_cap':
                        v = num(m.group(1))
                        if v is None or v < 5 or v > 100000: continue
                        val = str(int(v))
                    elif ttype == 'revenue_share_rate':
                        g = [x for x in m.groups() if x and re.match(r'^[\d]', x)]
                        if not g: continue
                        v = num(g[0])
                        if v is None or v <= 0 or v > 60: continue
                        val = str(v)
                    elif ttype == 'tier_structure':
                        val = ' | '.join(x for x in m.groups() if x)
                    elif ttype == '_term_years':
                        v = num(m.group(1))
                        if v is None or v < 1 or v > 99: continue
                        val = str(int(v))
                    elif ttype in ('_term_end_date',):
                        val = m.group(1)
                    else:
                        val = (m.group(1) if m.groups() else m.group(0))[:160]
                    key = (ttype, val, q[:100])
                    if key in seen: continue
                    seen.add(key)
                    out.append(dict(term_type=ttype, value=val, unit=unit,
                                    applies_to=applies_to(q), source_page=pi + 1,
                                    doc_zone=zone, quote=q, n_pages=len(pages)))
    return out

# ------------------------------------------------------------------ driver
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--pilot', default=os.path.join(INT, 'pilot_versions.txt'))
    ap.add_argument('--out', default='terms_candidates_v2')
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()

    versions = list(csv.DictReader(open(os.path.join(CLEAN, 'compact_versions.csv'), encoding='utf-8')))
    compacts = {c['compact_id']: c for c in csv.DictReader(open(os.path.join(CLEAN, 'compacts.csv'), encoding='utf-8'))}
    if a.all:
        targets = [v for v in versions if v['has_text'] == '1' and v['source_pdf']]
    else:
        ids = set(l.strip() for l in open(a.pilot, encoding='utf-8') if l.strip())
        targets = [v for v in versions if v['version_id'] in ids]
    print(f"targets: {len(targets)}")

    rows = []
    for i, v in enumerate(targets, 1):
        if i % 100 == 0: print(f"  {i}/{len(targets)}", flush=True)
        c = compacts[v['compact_id']]
        try:
            for r in extract(os.path.join(PDF, v['source_pdf'])):
                r.update(version_id=v['version_id'], compact_id=v['compact_id'],
                         state=c['state'], tribe=c['tribe'],
                         approval_type=v['approval_type'], approval_date=v['approval_date'],
                         source_pdf=v['source_pdf'])
                rows.append(r)
        except Exception as e:
            print("FAIL", v['source_pdf'], repr(e)[:120])

    # ---- dedup: presence-style terms repeat on every page that mentions them
    # (exclusivity fired 91 times across 10 pilot documents). Keep the best
    # evidence per (version, term_type[, value]) instead of shipping repeats.
    PRESENCE = {'exclusivity': 1, 'dispute_provision': 2, 'game_scope': 2}
    BYVALUE  = {'revenue_share_base', 'machine_cap', 'revenue_share_rate',
                'tier_structure', 'local_share', '_term_years', '_term_end_date', '_renewal'}
    def rank(r):  # instrument text first, then earliest page
        return (0 if r['doc_zone'] == 'instrument_text' else 1, int(r['source_page']))
    kept, bucket = [], collections.defaultdict(list)
    for r in rows:
        key = (r['version_id'], r['term_type'],
               r['value'].lower().strip() if r['term_type'] in BYVALUE else '')
        bucket[key].append(r)
    for (vid, tt, _), rs in bucket.items():
        rs.sort(key=rank)
        kept.extend(rs[:PRESENCE.get(tt, 1)])
    print(f"deduped {len(rows)} -> {len(kept)} candidates")
    rows = sorted(kept, key=lambda r: (r['version_id'], r['term_type'], int(r['source_page'])))

    F = ['version_id','compact_id','state','tribe','approval_type','approval_date',
         'term_type','value','unit','applies_to','source_page','doc_zone','quote',
         'source_pdf','n_pages']
    with open(os.path.join(INT, a.out + '.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=F, extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow(r)
    print(f"candidates: {len(rows)}")
    print(dict(collections.Counter(r['term_type'] for r in rows)))
    print("zone:", dict(collections.Counter(r['doc_zone'] for r in rows)))
    print("docs with >=1:", len(set(r['version_id'] for r in rows)), "of", len(targets))

    if not a.all:
        LIM = {'dispute_provision':2,'exclusivity':3,'game_scope':2,'local_share':2,
               'tier_structure':4,'revenue_share_base':2,'revenue_share_rate':6,
               'machine_cap':6,'_term_years':2,'_term_end_date':2,'_renewal':2}
        with open(os.path.join(INT, a.out + '_review.md'), 'w', encoding='utf-8') as fh:
            for v in targets:
                cs = [r for r in rows if r['version_id'] == v['version_id']]
                c = compacts[v['compact_id']]
                fh.write(f"\n\n## {c['state']} | {c['tribe']} | {v['approval_date']} | {v['approval_type']}\n")
                fh.write(f"`{v['source_pdf']}`\n\n")
                if not cs: fh.write("  (NO CANDIDATES)\n"); continue
                byt = collections.defaultdict(list)
                for r in cs: byt[r['term_type']].append(r)
                for t in sorted(byt):
                    fh.write(f"### {t}\n")
                    for r in byt[t][:LIM.get(t, 3)]:
                        fh.write(f"- **{r['value']}** [{r['unit']}] applies_to=`{r['applies_to'] or 'UNSET'}` "
                                 f"p.{r['source_page']} zone={r['doc_zone']}\n  > {r['quote'][:400]}\n")
                    if len(byt[t]) > LIM.get(t, 3):
                        fh.write(f"  _(+{len(byt[t])-LIM.get(t,3)} more)_\n")
        print("[written] review sheet")
