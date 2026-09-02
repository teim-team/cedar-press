"""Write review/sec_gaming_1080_adjudication.csv - the hand rulings for 1080.

Run from the repo root:  py -3 code/_1080_adjudication.py

This is a RULING FILE EXPRESSED AS CODE, not a computation. Every ACCEPT and
every REJECT below was written after reading the candidate's own quote; the
rejection reasons are the useful part and are quoted in
docs/SEC_GAMING_FACILITY_REVENUE_BUILD_LOG.md.

It keys on `candidate_id`, which since 2026-09-02 is a DIGEST of the
candidate's content rather than its position in the file (defect class 7). A
re-mine that changes a candidate gives it a new id, and this script then fails
loudly on "UNRULED CANDIDATES" rather than silently applying the old ruling to
a different figure.


Every candidate 1080 mined was read against its own quote. This file records
the ruling, one row per candidate, plus MANUAL- rows for figures a human read
that no pattern caught and DERIVED- rows where the filing states the percentage.
"""
import csv, io, os

CAND = 'review/sec_gaming_1080_candidates.csv'
OUT = 'review/sec_gaming_1080_adjudication.csv'
csv.field_size_limit(2**31 - 1)

cands = list(csv.DictReader(io.open(CAND, encoding='utf-8')))
by = {r['candidate_id']: r for r in cands}

COLS = ['candidate_id', 'adjudication', 'adjudication_note',
        'facility_id', 'facility_name_as_filed', 'tribe_name', 'state',
        'facility_is_on_indian_lands',
        'figure_type_final', 'figure_type_note_final',
        'value_usd_final', 'value_precision', 'fiscal_period_label_final',
        'period_type_final', 'period_end_final', 'fiscal_year',
        'manager_name', 'source_quote_final',
        'derived_from_fee', 'derivation_input_fee_usd',
        'derivation_stated_percentage', 'derivation_percentage_base',
        'derivation_percentage_source_accession',
        'derivation_arithmetic', 'derivation_caveat',
        'fee_formula_verbatim', 'fee_percentage', 'fee_percentage_base',
        'fee_is_tiered', 'contract_term_years', 'contract_expiry_as_stated',
        # MANUAL- rows only
        'form', 'filing_date', 'accession', 'source_url',
        'filer_name', 'filer_cik', 'filer_role', 'value_verbatim',
        'manual_read_basis']

rows = []


def rule(cid, adj, note, **kw):
    r = {c: '' for c in COLS}
    r['candidate_id'] = cid
    r['adjudication'] = adj
    r['adjudication_note'] = note
    c = by.get(cid)
    if c:
        r['facility_id'] = kw.pop('facility_id', c.get('facility_id', ''))
        r['tribe_name'] = kw.pop('tribe_name', c.get('tribe_name', ''))
        r['state'] = kw.pop('state', c.get('state', ''))
        r['facility_is_on_indian_lands'] = kw.pop('facility_is_on_indian_lands',
                                                  c.get('on_indian_lands', ''))
        pe = kw.get('period_end_final') or c.get('period_end', '')
        r['fiscal_year'] = kw.pop('fiscal_year', pe[:4] if pe else '')
    for k, v in kw.items():
        assert k in COLS, k
        r[k] = v
    rows.append(r)


# ----------------------------------------------------------------- REJECTS --
REJ = {
    'SECGF-05076932f4': ('REJECT_DELTA_NOT_LEVEL',
                    'The sentence says management fee income "increased approximately $5.6 million" '
                    'for the twelve months ended December 31, 2000. That is a YEAR-OVER-YEAR CHANGE, '
                    'not a level, and it arises from an early-buyout settlement rather than from '
                    'operations. A delta booked as a level would understate the fee and imply a '
                    'property revenue that was never stated.'),
    'SECGF-21e75c9456': ('REJECT_WRONG_KIND_OF_FEE',
                    'These are CONSTRUCTION management fees PAID BY the Seneca gaming corporations '
                    'to SCMC for demolition and land preparation at the Buffalo Creek site. An '
                    'outflow for construction services, not gaming revenue and not a gaming '
                    'management fee. The word "management fee" is doing all the work here.'),
    'SECGF-4936233ae3': ('REJECT_WRONG_KIND_OF_FEE', 'Same sentence as SECGF-21e75c9456, prior year.'),
    'SECGF-3244b28094': ('REJECT_WRONG_NUMBER_IN_SENTENCE',
                    'The $302,141 in this sentence is a DECREASE IN FOOD AND BEVERAGE REVENUES. '
                    'The pattern found the property name and the nearest dollar figure and they '
                    'belong to different clauses. The sentence does contain a real figure - $5.8 '
                    'million of FireKeepers management fee income for the nine months - and it is '
                    'entered by hand as MANUAL-0003.'),
    'SECGF-93f7a08529': ('REJECT_WRONG_PROPERTY',
                    'The $4.8m/$4.6m are distributions from the DELAWARE operation (Harrington '
                    'Raceway, a non-tribal racino). FireKeepers is named in the preceding sentence '
                    'only. Attributing a Delaware racino distribution to a Michigan tribal casino '
                    'would be the containment defect in a new dress.'),
    'SECGF-136fa9afa4': ('REJECT_WRONG_PROPERTY', 'Same sentence as SECGF-93f7a08529, prior year.'),
    'SECGF-8fbee1b674': ('REJECT_WRONG_PROPERTY', 'Delaware distributions, as SECGF-93f7a08529.'),
    'SECGF-182e09f48c': ('REJECT_WRONG_PROPERTY', 'Delaware distributions, as SECGF-93f7a08529.'),
    'SECGF-fcfccb66b8': ('REJECT_PERIOD_MISREAD',
                    'Same Gun Lake sentence as SECGF-0f9af4d977/92, but the period lookback reached '
                    'forward into the NEXT sentence ("Reimbursable costs ... for the years ended '
                    'December 31, 2019") and stamped 2019 on a 2018 figure. The correctly-periodised '
                    'rows are SECGF-0f9af4d977 and SECGF-04f654c265.'),
    'SECGF-c17b9e304b': ('REJECT_RESTATEMENT_SAME_EVIDENCE_FAMILY',
                    'The FY2005 Seneca Allegany figure restated in an S-4/A three weeks after the '
                    '10-K stated it. Same registrant, same figure, same evidence family - a copy is '
                    'not a corroboration (docs/ASSERTION_LAYER.md). The 10-K row is SECGF-eac4f0dddd.'),
    'SECGF-aa67ca6a1d': ('REJECT_RESTATEMENT_SAME_EVIDENCE_FAMILY', 'As SECGF-c17b9e304b; 10-K row is SECGF-10bf997211.'),
    'SECGF-1f6dca15d4': ('REJECT_RESTATEMENT_SAME_EVIDENCE_FAMILY',
                    'Same FY2005 Seneca Allegany figure again, in the 424B3 prospectus. 10-K row is '
                    'SECGF-eac4f0dddd.'),
    'SECGF-b14e35ce86': ('REJECT_RESTATEMENT_SAME_EVIDENCE_FAMILY', 'As SECGF-1f6dca15d4; 10-K row is SECGF-10bf997211.'),
    'SECGF-7a8976de9a': ('REJECT_INTRA_FILING_DUPLICATE',
                    'The same three Graton management-fee figures appear twice in the same 2021 '
                    '10-K - once in a risk factor and once in the revenue note. SECGF-beab13d386/97/98 '
                    'carry them; this is the second sentence.'),
    'SECGF-6cb4989145': ('REJECT_INTRA_FILING_DUPLICATE', 'As SECGF-7a8976de9a.'),
    'SECGF-bd73f1d67e': ('REJECT_INTRA_FILING_DUPLICATE', 'As SECGF-7a8976de9a.'),
}
for cid, (adj, note) in REJ.items():
    rule(cid, adj, note)

# MGE Niagara - Ontario, outside Cedar's universe
for r in cands:
    if r['alias'].startswith('MGE Niagara') or r['alias'].startswith('Niagara Fallsview'):
        rule(r['candidate_id'], 'REJECT_NOT_A_US_TRIBAL_FACILITY',
             'MGE Niagara Resorts are the Ontario casinos MTGA operates for the Ontario Lottery '
             'and Gaming Corporation. Kept in the alias map and rejected here rather than dropped '
             'silently, so that a reader of the Mohegan segment table can see why the segment '
             'lines do not add to the tribal properties.')

# ---------------------------------------------------------------- ACCEPTS --
SEN = 'Seneca Nation of Indians'
ACC = [
    # (cid, period_end, period_type, note, extra)
    ('SECGF-eac4f0dddd', '2005-09-30', 'FISCAL_YEAR',
     'Seneca Gaming Corporation is a wholly owned instrumentality of the Seneca Nation and files '
     'its own 10-K. This is the property\'s own audited-year net revenue, stated in the annual '
     'report - not a manager\'s fee and not a regional ceiling.', {}),
    ('SECGF-10bf997211', '2005-09-30', 'FISCAL_YEAR', 'As SECGF-eac4f0dddd, Seneca Niagara.', {}),
    ('SECGF-765eb52a8f', '2006-09-30', 'QUARTER',
     'Fourth Quarter of Seneca Gaming\'s fiscal 2006, which ends September 30. The pattern found '
     'no period because the sentence says "During the Fourth Quarter 2006 and 2005" rather than '
     'naming a date. Periodised by hand. The same sentence also states $40.0 million for Q4 FY2005; '
     'that second value is NOT in this table.', {}),
    ('SECGF-f467750f8e', '2006-09-30', 'FISCAL_YEAR',
     'The miner stamped 2006-12-31 because "For Fiscal 2006" carries no month and the unanchored '
     'cue defaults to a December year end. Seneca Gaming\'s fiscal year ends SEPTEMBER 30 (stated '
     'on the cover of the same 10-K). Corrected by hand.', {}),
    ('SECGF-ff2df9f26b', '2006-09-30', 'FISCAL_YEAR', 'As SECGF-f467750f8e, Seneca Niagara.', {}),
    ('SECGF-5c9519eabf', '2007-06-30', 'QUARTER',
     'Third Quarter of fiscal 2007 = the quarter ended June 30, 2007. Periodised by hand; the '
     'sentence names the quarter in words. The same sentence states $37.9 million for Q3 FY2006, '
     'which is not in this table.', {}),
    ('SECGF-46694a338f', '2007-06-30', 'NINE_MONTHS',
     'Nine months ended June 30, 2007 - a year-to-date figure, NOT a fiscal year. Never add it to '
     'a fiscal-year row for the same property.', {}),
    ('SECGF-0f9af4d977', '2018-12-31', 'FISCAL_YEAR',
     'MPM Enterprises LLC is a consolidated VIE of Red Rock; the figure is MPM\'s whole management '
     'fee from Gun Lake, excluding reimbursable expenses, as the sentence says. The agreement '
     'expired in February 2018, so FY2018 is a five-week stub.', {}),
    ('SECGF-04f654c265', '2017-12-31', 'FISCAL_YEAR', 'As SECGF-0f9af4d977, full year.', {}),
    ('SECGF-beab13d386', '2020-12-31', 'FISCAL_YEAR',
     'Graton management fee excluding reimbursable costs. Red Rock reports reimbursable payroll '
     'separately ($5.5m/$5.2m/$6.6m for 2019/2018/2017); the segment line "Native American '
     'management: Management fees" INCLUDES them and is therefore a different number.', {}),
    ('SECGF-d7b7816fdc', '2019-12-31', 'FISCAL_YEAR', 'As SECGF-beab13d386.', {}),
    ('SECGF-7923224e01', '2018-12-31', 'FISCAL_YEAR', 'As SECGF-beab13d386.', {}),
    ('SECGF-b333294f18', '2021-12-31', 'FISCAL_YEAR',
     'Partial year: the Federated Indians of Graton Rancheria terminated the management agreement '
     'on February 5, 2021, as the same sentence states. $7.8m is roughly five weeks of fee plus '
     'post-termination settlement, NOT an annual run rate.', {}),
    ('SECGF-92ac720327', '2020-12-31', 'FISCAL_YEAR', 'Restatement of the FY2020 figure first filed in the 2021 10-K.', {}),
    ('SECGF-711d680328', '2019-12-31', 'FISCAL_YEAR', 'Restatement of the FY2019 figure first filed in the 2021 10-K.', {}),
    ('SECGF-feaa2fc657', '2022-12-31', 'FISCAL_YEAR',
     'Tail payments after the February 2021 termination. Not an operating fee for a managed year.', {}),
    ('SECGF-639ab1bc14', '2021-12-31', 'FISCAL_YEAR', 'Restatement of FY2021.', {}),
    ('SECGF-3475f000c6', '2020-12-31', 'FISCAL_YEAR', 'Restatement of FY2020.', {}),
    ('SECGF-16e86c7272', '2022-12-31', 'FISCAL_YEAR', 'Restatement of FY2022.', {}),
    ('SECGF-0f0348dda3', '2021-12-31', 'FISCAL_YEAR', 'Restatement of FY2021.', {}),
]
for cid, pe, pt, note, extra in ACC:
    rule(cid, 'ACCEPT', note, period_end_final=pe, period_type_final=pt,
         fiscal_year=pe[:4], **extra)

# Mohegan segment-table rows: accept every one, the restatement flag sorts them out
for r in cands:
    if r['extraction_pattern'] != 'C_SEGMENT_TABLE':
        continue
    if not r['facility_id']:
        continue          # MGE Niagara, already rejected above
    rule(r['candidate_id'], 'ACCEPT',
         'Mohegan Tribal Gaming Authority segment table, 10-K, stated in thousands. MTGA is an '
         'instrumentality of the Mohegan Tribe and an SEC registrant in its own right, so this is '
         'the property owner reporting its own property under a federal disclosure obligation. '
         'A 10-K restates the two prior fiscal years; is_first_filing_of_this_fact says which row '
         'is the original.',
         period_type_final='FISCAL_YEAR')

# Mohegan MD&A narrative rows that are NOT MGE Niagara
for r in cands:
    if r['extraction_pattern'].startswith('B_MDNA') and r['facility_id']:
        rule(r['candidate_id'], 'ACCEPT',
             'MTGA MD&A property section, figure and period both stated in the sentence.',
             period_type_final=r['period_type'] or 'FISCAL_YEAR')

# ------------------------------------------------------------ FEE FORMULAS --
# One TERM row per (registrant, property, formula). Later repetitions are the
# same contract described again and are rejected as restatements.
seen_terms = set()

# ONE HAND-PINNED TERM. `('Red Hawk Casino', '30')` is claimed by whichever
# candidate sorts first, which is the 2009-03-13 10-K - and the regex captured
# "30% of net income" there, from a sentence about a DIFFERENT property. The
# Red Hawk fee is 30% of net REVENUE as the management agreement defines it, and
# the 2012-03-16 10-K states it in full including the tiering. The base and the
# verbatim disagreed on the shipped row until this pin was added; a term row
# whose `fee_percentage_base` and `fee_formula_verbatim` describe two different
# formulas is worse than no row.
PIN_TERM_TO_ACCESSION = {('Red Hawk Casino', '30'): '0001193125-12-120010'}
TERM_META = {
    ('Mohegan Sun', '5'): dict(
        fee_formula_verbatim='a fee equal to 5% of Revenues, as defined in the Relinquishment '
                             'Agreement, generated by the Mohegan Sun during the 15-year period '
                             'commencing on January 1, 2000',
        fee_percentage='5', fee_percentage_base='REVENUES_AS_DEFINED_IN_THE_RELINQUISHMENT_AGREEMENT',
        fee_is_tiered='N', contract_term_years='15',
        contract_expiry_as_stated='15 years from January 1, 2000',
        note='NOT a management fee. This is the Trading Cove Associates RELINQUISHMENT fee - the '
             'price MTGA agreed to pay for terminating TCA\'s management rights - and the same '
             'filings define "Revenues" for this purpose as "gross gaming revenues (other than '
             'Class II gaming revenue) and all other facility revenues". That is the closest thing '
             'in this corpus to a stated formula over a tribal property\'s TOTAL revenue. Waterford '
             'holds only a partial interest in TCA and does not disclose the gross 5% payment, so '
             'no revenue is derived from it here.'),
    ('Buena Vista Rancheria', '25'): dict(
        fee_percentage='25', fee_percentage_base='NET_INCOME', fee_is_tiered='N',
        note='Development/management agreement for a casino that had not opened. No fee dollars '
             'were ever disclosed against it in this corpus, so nothing is derived.'),
    ('Four Winds Casino', '30'): dict(
        fee_percentage='30', fee_percentage_base='NET_INCOME', fee_is_tiered='UNSTATED_IN_THIS_FILING',
        note='Lakes/Pokagon Band, Four Winds.'),
    ('Four Winds Casino', '24'): dict(
        fee_percentage='24', fee_percentage_base='NET_INCOME',
        fee_is_tiered='Y',
        fee_formula_verbatim='a management fee equal to 24% of net income up to a certain '
                             'threshold and 19% on net income over that threshold',
        note='TIERED AND THRESHOLDED, and the threshold is not disclosed: "24% of net income up to '
             'a certain threshold and 19% on net income over that threshold". Because the '
             'threshold is unstated, a fee dollar CANNOT be divided by a percentage here - which '
             'is why no Four Winds revenue is derived anywhere in this build.'),
    ('Four Winds Casino Resort', '30'): dict(
        fee_percentage='30', fee_percentage_base='NET_INCOME', fee_is_tiered='UNSTATED_IN_THIS_FILING',
        contract_term_years='5',
        contract_expiry_as_stated='five years from August 2, 2007 (the opening date)',
        note='Lakes/Pokagon Band, Four Winds. Lakes describes the fee as 30% of net income in the '
             'fiscal 2008 and 2009 10-Ks and as 24%/19% around a threshold in others; BOTH '
             'wordings are in the corpus and Cedar records both rather than choosing. The fee was '
             'subordinated to the Pokagon Gaming Authority senior indebtedness, and the Band '
             'bought the contract out on June 30, 2011 for approximately $24.5 million.'),
    ('Four Winds Casino Resort', '24'): dict(
        fee_percentage='24', fee_percentage_base='NET_INCOME', fee_is_tiered='Y',
        fee_formula_verbatim='a management fee equal to 24% of net income up to a certain '
                             'threshold and 19% on net income over that threshold',
        note='Same Lakes/Pokagon term as the 24% row above, described in a later filing under a '
             'slightly different property spelling. The threshold is not disclosed, so no revenue '
             'is derived from a Four Winds fee anywhere in this build.'),
    ('Cimarron Casino', '30'): dict(
        fee_percentage='30', fee_percentage_base='NET_INCOME_FROM_OPERATIONS_IN_EXCESS_OF_4M',
        fee_is_tiered='Y',
        fee_formula_verbatim='an annual fee equal to 30% of net income from operations in excess '
                             'of $4 million as defined in the agreement, through March 2013',
        contract_expiry_as_stated='March 2013',
        note='Lakes/Iowa Tribe of Oklahoma, Cimarron Casino. The fee sits ABOVE a $4 million floor, '
             'so fee/0.30 recovers only the excess over $4m, not the base. Nothing is derived.'),
    ('Red Hawk Casino', '30'): dict(
        fee_percentage='30', fee_percentage_base='NET_REVENUE_AS_DEFINED_IN_THE_MANAGEMENT_AGREEMENT',
        fee_formula_verbatim='a management fee equal to 30% of net revenue (as defined by the '
                             'development and management agreement) ("Net Revenue") of the '
                             'operations annually for the first five years. During years six and '
                             'seven, Lakes will earn a fee equal to 25% of the first $90 million '
                             'of Net Revenue per year, 15% of the next $60 million of Net Revenue '
                             'per year and 5% of Net Revenue over $150 million per year',
        fee_is_tiered='Y', contract_term_years='7',
        contract_expiry_as_stated='seven years from the opening date (opened December 17, 2008)',
        note='TIERED. 30% of Net Revenue (as defined) for the first five years; in years six and '
             'seven, 25% of the first $90m of Net Revenue, 15% of the next $60m and 5% above $150m. '
             'Payment is subordinated to $450m of senior notes and is DEFERRED when operating '
             'results are insufficient - so a fee dollar in a given year is not necessarily 30% of '
             'that year\'s base.'),
    ('FireKeepers', '26'): dict(
        fee_percentage='26', fee_percentage_base='NET_REVENUES', fee_is_tiered='N',
        note='Full House Resorts / Gaming Entertainment (Michigan) LLC, a 50% joint venture, with '
             'the Nottawaseppi Huron Band. Full House also describes the base as "net profits" in '
             'other filings - both wordings are in the corpus and neither is Cedar\'s.'),
    ('FireKeepers Casino', '26'): dict(
        fee_percentage='26', fee_percentage_base='NET_REVENUES', fee_is_tiered='N',
        note='As above.'),
    ('FireKeepers', '30'): dict(
        fee_percentage='', fee_percentage_base='', fee_is_tiered='',
        note='REFUSED AS A CONTRACT TERM: "30% of revenues" here is the IGRA/NIGC statutory CEILING '
             '(25 U.S.C. 2711) recited in the regulatory background section, not this contract\'s '
             'fee. Recording it as FireKeepers\' fee would invent a term.'),
}
for r in cands:
    if r['extraction_pattern'] != 'E_FEE_FORMULA':
        continue
    key = (r['alias'], r['derivation_stated_percentage'])
    dedupe_key = (r['facility_id'] or r['alias'], r['derivation_stated_percentage'])
    meta = TERM_META.get(key)
    if meta is None:
        rule(r['candidate_id'], 'REJECT_UNRULED_FEE_STATEMENT',
             'No ruling written for this (property, percentage) pair; not published rather than '
             'guessed. alias=%s pct=%s' % (r['alias'], r['derivation_stated_percentage']))
        continue
    if meta.get('fee_percentage') == '':
        rule(r['candidate_id'], 'REJECT_STATUTORY_CEILING_NOT_A_CONTRACT_TERM', meta['note'])
        continue
    pin = PIN_TERM_TO_ACCESSION.get(key)
    if pin and r['accession'] != pin:
        rule(r['candidate_id'], 'REJECT_AMBIGUOUS_FEE_BASE_IN_THIS_FILING',
             'This (property, rate) term is pinned to accession %s, where the registrant states '
             'the formula in full. The capture here took its base from an adjacent sentence about '
             'another property.' % pin)
        continue
    if dedupe_key in seen_terms:
        rule(r['candidate_id'], 'REJECT_RESTATEMENT_SAME_EVIDENCE_FAMILY',
             'The same contract term described again in a later filing by the same registrant. '
             'One term row per (registrant, property, formula).')
        continue
    seen_terms.add(dedupe_key)
    kw = {k: v for k, v in meta.items() if k != 'note'}
    kw.setdefault('fee_formula_verbatim', r['value_verbatim'])
    rule(r['candidate_id'], 'ACCEPT', meta['note'], **kw)

# ------------------------------------------------------------ MANUAL ADDS --
LAKES = dict(filer_name='Lakes Entertainment, Inc.', filer_cik='0001071255',
             filer_role='DEVELOPER_MANAGER', manager_name='Lakes Entertainment, Inc.',
             facility_id='CCP-743100', tribe_name='Shingle Springs Band of Miwok Indians',
             state='CA', facility_is_on_indian_lands='Y',
             facility_name_as_filed='Red Hawk Casino')

rows.append(dict({c: '' for c in COLS}, **dict(LAKES, **{
    'candidate_id': 'MANUAL-0001', 'adjudication': 'ACCEPT',
    'adjudication_note':
        'Read by hand. No pattern caught it because the attribution and the figure are in two '
        'different places in the 10-K: the MD&A says the fee came from ONE property, and the '
        'income statement carries the amount. Together they are a per-property figure.',
    'form': '10-K', 'filing_date': '2013-03-15', 'accession': '0001437749-13-003001',
    'source_url': 'https://www.sec.gov/Archives/edgar/data/1071255/000143774913003001/'
                  'lakes_10k-123012.htm',
    'manual_read_basis': 'data/raw/external/sec_edgar_1030/0001437749-13-003001__lakes_10k-123012.htm',
    'figure_type_final': 'MANAGEMENT_FEE_REVENUE',
    'figure_type_note_final': 'management fee revenue recognised by Lakes, sole-sourced by the '
                              'filer to the Red Hawk Casino',
    'value_usd_final': '7726000', 'value_verbatim': '$7,726 thousand',
    'value_precision': 'EXACT_AS_FILED_IN_THOUSANDS',
    'fiscal_period_label_final': 'fiscal year ended December 30, 2012',
    'period_type_final': 'FISCAL_YEAR', 'period_end_final': '2012-12-30', 'fiscal_year': '2012',
    'source_quote_final':
        '"During fiscal 2012, our management fee revenues were derived from the management of the '
        'Red Hawk Casino." ... CONSOLIDATED STATEMENTS OF OPERATIONS (In thousands): '
        '"Revenues: Management fees $ 7,726 | $ 35,397"',
    'derived_from_fee': 'N',
})))

rows.append(dict({c: '' for c in COLS}, **dict(LAKES, **{
    'candidate_id': 'MANUAL-0002', 'adjudication': 'ACCEPT',
    'adjudication_note': 'As MANUAL-0001, the following fiscal year.',
    'form': '10-K', 'filing_date': '2014-03-14', 'accession': '0001437749-14-004229',
    'source_url': 'https://www.sec.gov/Archives/edgar/data/1071255/000143774914004229/'
                  'laco20131231_10k.htm',
    'manual_read_basis': 'data/raw/external/sec_edgar_1030/0001437749-14-004229__laco20131231_10k.htm',
    'figure_type_final': 'MANAGEMENT_FEE_REVENUE',
    'figure_type_note_final': 'management fee revenue recognised by Lakes, sole-sourced by the '
                              'filer to the Red Hawk Casino. PARTIAL YEAR: the same 10-K states '
                              'that the statement of operations carries no Red Hawk management fee '
                              'revenue after August 29, 2013 (Debt Termination Agreement).',
    'value_usd_final': '7762000', 'value_verbatim': '$7,762 thousand',
    'value_precision': 'EXACT_AS_FILED_IN_THOUSANDS',
    'fiscal_period_label_final': 'fiscal year ended December 29, 2013',
    'period_type_final': 'FISCAL_YEAR', 'period_end_final': '2013-12-29', 'fiscal_year': '2013',
    'source_quote_final':
        '"During fiscal 2013, our management fee revenues were derived from the management of the '
        'Red Hawk Casino." ... "Due to entering into the Debt Termination Agreement with the '
        'Shingle Springs Tribe, Lakes\' consolidated statement of operations will not include '
        'management fee revenues related to the management of the Red Hawk Casino subsequent to '
        'August 29, 2013." ... "Revenues: Management fees $ 7,762 | $ 7,726"',
    'derived_from_fee': 'N',
})))

rows.append(dict({c: '' for c in COLS}, **{
    'candidate_id': 'MANUAL-0003', 'adjudication': 'ACCEPT',
    'adjudication_note':
        'Read by hand out of the sentence SECGF-3244b28094 was rejected for. The pattern took the '
        'nearest dollar figure ($302,141, a food-and-beverage decrease); the figure that belongs '
        'to FireKeepers is the $5.8 million earlier in the same sentence.',
    'facility_id': 'CCP-658400', 'facility_name_as_filed': 'FireKeepers casino',
    'tribe_name': 'Nottawaseppi Huron Band of Potawatomi Indians', 'state': 'MI',
    'facility_is_on_indian_lands': 'Y',
    'filer_name': 'Full House Resorts, Inc.', 'filer_cik': '0000891482',
    'filer_role': 'MANAGER', 'manager_name': 'Full House Resorts, Inc.',
    'form': '10-Q', 'filing_date': '2009-11-09', 'accession': '0000950123-09-060144',
    'source_url': 'https://www.sec.gov/Archives/edgar/data/891482/000095012309060144/c92276e10vq.htm',
    'manual_read_basis': 'data/raw/external/sec_edgar_1030/0000950123-09-060144__c92276e10vq.htm',
    'figure_type_final': 'MANAGEMENT_FEE_REVENUE',
    'figure_type_note_final': 'management fee income recognised by Full House from FireKeepers, '
                              'nine months, the casino having opened in August 2009',
    'value_usd_final': '5800000', 'value_verbatim': '$5.8 million',
    'value_precision': 'ROUNDED_TO_TENTHS_OF_A_MILLION_AS_FILED',
    'fiscal_period_label_final': 'nine months ended September 30, 2009',
    'period_type_final': 'NINE_MONTHS', 'period_end_final': '2009-09-30', 'fiscal_year': '2009',
    'source_quote_final':
        '"For the nine months ended September 30, 2009, total operating revenues from continuing '
        'operations increased $5.2 million or 70%, as compared to the prior year, primarily due to '
        'the $5.8 million in management fee income related to the FireKeepers casino which opened '
        'in August 2009, offset by decreases in food and beverage revenues of $302,141, or 19% and '
        'casino revenues of $229,788, or 4%."',
    'derived_from_fee': 'N',
}))

# ---- DERIVED rows: only where the SAME registrant states the percentage.
GRATON = dict(facility_id='CCP-638700', facility_name_as_filed='Graton Resort & Casino',
              tribe_name='Federated Indians of Graton Rancheria', state='CA',
              facility_is_on_indian_lands='Y',
              filer_name='Red Rock Resorts, Inc. (Station Casinos)', filer_cik='0001653653',
              filer_role='MANAGER', manager_name='Red Rock Resorts, Inc. (Station Casinos)',
              form='10-K', filing_date='2021-02-23', accession='0001653653-21-000005',
              source_url='https://www.sec.gov/Archives/edgar/data/1653653/000165365321000005/'
                         'rrr-20201231.htm',
              manual_read_basis='data/raw/external/sec_edgar_1030/'
                                '0001653653-21-000005__rrr-20201231.htm',
              figure_type_final='DERIVED_FACILITY_NET_INCOME_AS_DEFINED',
              derived_from_fee='Y',
              derivation_stated_percentage='27',
              derivation_percentage_base='NET_INCOME_AS_DEFINED_IN_THE_MANAGEMENT_AGREEMENT',
              derivation_percentage_source_accession='0001653653-20-000005',
              value_precision='DERIVED_FROM_A_FEE_ROUNDED_TO_TENTHS_OF_A_MILLION')
DER_CAVEAT = (
    'THIS IS NOT REVENUE. The percentage base is "net income (as defined in the management '
    'agreement)", which under IGRA (25 U.S.C. 2703(9)) is gross gaming revenues less prizes and '
    'less gaming-related operating expenses excluding the management fee - much closer to operating '
    'profit than to revenue. The 27% rate is stated in Red Rock\'s FY2019 10-K (accession '
    '0001653653-20-000005: "24% of Graton Resort\'s net income ... in years 1 through 4 of the '
    'agreement, and is entitled to receive 27% of Graton Resort\'s net income in years 5 through '
    '7"); Graton opened November 5, 2013, so calendar 2018, 2019 and 2020 sit inside years 5-7. '
    'The fee dollars are stated excluding reimbursable costs. The result is the CONTRACT\'S OWN '
    'BASE and nothing else, and it may not be compared with a net-revenues figure for another '
    'property.')
for i, (yr, fee, pe) in enumerate([('2018', 77_500_000, '2018-12-31'),
                                   ('2019', 85_600_000, '2019-12-31'),
                                   ('2020', 77_400_000, '2020-12-31')], start=4):
    rows.append(dict({c: '' for c in COLS}, **dict(GRATON, **{
        'candidate_id': 'MANUAL-%04d' % i, 'adjudication': 'ACCEPT',
        'adjudication_note': 'Derived. The fee row it is derived from is the accepted candidate for '
                             'the same year and filing.',
        'figure_type_note_final': 'Graton Resort net income as the management agreement defines it, '
                                  'recovered from the stated fee and the stated percentage',
        'value_usd_final': '%.0f' % (fee / 0.27),
        'value_verbatim': '$%.1f million fee / 27%%' % (fee / 1e6),
        'fiscal_period_label_final': 'year ended December 31, %s' % yr,
        'period_type_final': 'FISCAL_YEAR', 'period_end_final': pe, 'fiscal_year': yr,
        'derivation_input_fee_usd': str(fee),
        'derivation_arithmetic': '%s / 0.27 = %.0f' % (format(fee, ','), fee / 0.27),
        'derivation_caveat': DER_CAVEAT,
        'source_quote_final':
            '"The Company managed Graton Resort & Casino (\'Graton Resort\') on behalf of the '
            'Federated Indians of Graton Rancheria through February 5, 2021. For the years ended '
            'December 31, 2020, 2019 and 2018, management fees from Graton Resort totaled $77.4 '
            'million, $85.6 million and $77.5 million, respectively." '
            '[percentage, from accession 0001653653-20-000005] "...is entitled to receive a '
            'management fee of 24% of Graton Resort\'s net income (as defined in the management '
            'agreement) in years 1 through 4 of the agreement, and is entitled to receive 27% of '
            'Graton Resort\'s net income in years 5 through 7"',
    })))

# ------------------------------- WATERFORD / TRADING COVE ASSOCIATES -------
# The best evidence in this corpus, and the mandate's thesis working exactly as
# written: a stated percentage, a stated base, and the dollars.
#
# Under the Relinquishment Agreement MTGA pays Trading Cove Associates a fee
# equal to 5% of "Revenues ... generated by the Mohegan Sun" for the 15 years
# from 2000-01-01, and the SAME filings define Revenues for this purpose as
# "gross gaming revenues (other than Class II gaming revenue) and all other
# facility revenues". Waterford Gaming LLC, a TCA partner, files 10-Ks that
# carry TCA's audited financial statements, and those state the fee in dollars
# for every year 2000-2006.
WATERFORD_SRC = {
    '2000': ('0001047469-03-020574', '10-K/A', '2003-06-05',
             'https://www.sec.gov/Archives/edgar/data/1028911/000104746903020574/a2112430z10-ka.txt',
             'data/raw/external/sec_edgar_1030/0001047469-03-020574__a2112430z10-ka.txt'),
    '2001': ('0001047469-03-020574', '10-K/A', '2003-06-05',
             'https://www.sec.gov/Archives/edgar/data/1028911/000104746903020574/a2112430z10-ka.txt',
             'data/raw/external/sec_edgar_1030/0001047469-03-020574__a2112430z10-ka.txt'),
    '2002': ('0001047469-03-020574', '10-K/A', '2003-06-05',
             'https://www.sec.gov/Archives/edgar/data/1028911/000104746903020574/a2112430z10-ka.txt',
             'data/raw/external/sec_edgar_1030/0001047469-03-020574__a2112430z10-ka.txt'),
    '2003': ('0001028911-04-000011', '10-K', '2004-03-26',
             'https://www.sec.gov/Archives/edgar/data/1028911/000102891104000011/final10kwgllc123103.txt',
             'data/raw/external/sec_edgar_1030/0001028911-04-000011__final10kwgllc123103.txt'),
    '2004': ('0001028911-05-000012', '10-K', '2005-03-29',
             'https://www.sec.gov/Archives/edgar/data/1028911/000102891105000012/final10kwgllc123104.txt',
             'data/raw/external/sec_edgar_1030/0001028911-05-000012__final10kwgllc123104.txt'),
    '2005': ('0001028911-06-000010', '10-K', '2006-03-27',
             'https://www.sec.gov/Archives/edgar/data/1028911/000102891106000010/final10kwgllc123105.txt',
             'data/raw/external/sec_edgar_1030/0001028911-06-000010__final10kwgllc123105.txt'),
    '2006': ('0001028911-07-000012', '10-K', '2007-03-21',
             'https://www.sec.gov/Archives/edgar/data/1028911/000102891107000012/final10kwgllc123106.txt',
             'data/raw/external/sec_edgar_1030/0001028911-07-000012__final10kwgllc123106.txt'),
}
WATERFORD_FEE = {
    '2000': 41_003_849, '2001': 45_715_318, '2002': 58_508_703, '2003': 65_099_553,
    '2004': 69_101_491, '2005': 72_964_466, '2006': 76_258_408,
}
WATERFORD_QUOTE = {
    '2000': '"April 25, 2000 $ 4,947,458 / July 26, 2000 15,025,554 / October 25, 2000 5,457,627 / '
            'January 25, 2001 15,573,210 --- Relinquishment Fees earned 2000 $ 41,003,849"',
    '2001': '"For the years ended December 31, 2002, 2001 and 2000, total Relinquishment Fees '
            'earned were $58,508,703, $45,715,318 and $41,003,849, respectively." '
            '[tabulated: "Relinquishment Fees earned 2001 $ 45,715,318"]',
    '2002': '"For the years ended December 31, 2002, 2001 and 2000, total Relinquishment Fees '
            'earned were $58,508,703, $45,715,318 and $41,003,849, respectively." '
            '[tabulated: "Relinquishment Fees earned 2002 $ 58,508,703"]',
    '2003': '"...Relinquishment Fees earned were $65,099,553, $58,508,703 and $45,715,318, '
            'respectively." [tabulated: "Relinquishment Fees earned 2003 $ 65,099,553"]',
    '2004': '"...Relinquishment Fees earned were $69,101,491, $65,099,553 and $58,508,703, '
            'respectively." [tabulated: "Relinquishment Fees earned 2004 $ 69,101,491"]',
    '2005': '"...Relinquishment Fees earned were $72,964,466, $69,101,491 and $65,099,553, '
            'respectively." [tabulated: "Relinquishment Fees earned 2005 $ 72,964,466"]',
    '2006': '"...Relinquishment Fees earned were $76,258,408, $72,964,466 and $69,101,491, '
            'respectively." [tabulated: "Relinquishment Fees earned 2006 $ 76,258,408"]',
}
WATERFORD_TYPO = {
    '2003': ' TWO SPELLINGS IN THE CORPUS: the narrative sentence of the 2004-03-26 10-K types '
            '$65,099,533 in one place and $65,099,553 in another. The tabulation in that filing '
            'and both later 10-Ks say $65,099,553, which is the value recorded. The variant is '
            'noted rather than silently resolved.',
    '2005': ' TWO SPELLINGS IN THE CORPUS: the 2007-03-21 10-K types $72,964,446 in one sentence '
            'and $72,964,466 in another; the 2006-03-21 10-K and the tabulation say $72,964,466, '
            'which is the value recorded.',
}
WATERFORD_BASE = dict(
    facility_id='CCP-45100', facility_name_as_filed='Mohegan Sun',
    tribe_name='Mohegan Tribe', state='CT', facility_is_on_indian_lands='Y',
    filer_name='Waterford Gaming, L.L.C.', filer_cik='0001028911',
    filer_role='RELINQUISHMENT_INTEREST_HOLDER',
    manager_name='Trading Cove Associates (former manager; relinquished 1999-12-31)',
    value_precision='EXACT_TO_THE_DOLLAR_AS_FILED')
PERIOD_CAVEAT = (
    'PERIOD LABEL IS THE FILER\'S. The filing labels each total "Relinquishment Fees earned '
    '<year>" and tabulates four payment dates running April of that year to January of the next '
    '(e.g. 2000: 25 Apr 2000, 26 Jul 2000, 25 Oct 2000, 25 Jan 2001). The fee is divided into '
    'senior and junior payments of 2.5% each and is paid in arrears, so the twelve months of '
    'Mohegan Sun trading the total is 5% OF is not necessarily the calendar year named. Cedar '
    'records the filer\'s own label and does not re-date it.')
DER_CAVEAT_W = (
    'DERIVED, and derived from the strongest formula in this corpus: the SAME filings that state '
    'the dollars also state the rate and define the base. "The Authority agreed to pay to TCA a '
    'fee (the RELINQUISHMENT FEES) equal to 5 percent of Revenues, as defined in the '
    'Relinquishment Agreement, generated by the Mohegan Sun", and Revenues is defined in those '
    'filings as "gross gaming revenues (other than Class II gaming revenue) and all other facility '
    'revenues". So this figure is Mohegan Sun\'s GROSS facility revenues on the agreement\'s '
    'definition - before promotional allowances, and excluding Class II. It is NOT the "net '
    'revenues" MTGA reports in its own 10-K a decade later, and the two must not be plotted as one '
    'series. The period caveat on the fee row applies here unchanged. Cross-check, not a proof: '
    'the derived FY2005 figure of $1.459bn sits above MTGA\'s own reported FY2005 net revenues, '
    'which is the direction a gross-of-promotional-allowance measure should sit.')

for _i, _yr in enumerate(sorted(WATERFORD_FEE), start=100):
    _acc, _form, _fd, _url, _lf = WATERFORD_SRC[_yr]
    _fee = WATERFORD_FEE[_yr]
    rows.append(dict({c: '' for c in COLS}, **dict(WATERFORD_BASE, **{
        'candidate_id': 'MANUAL-%04d' % _i, 'adjudication': 'ACCEPT',
        'adjudication_note': 'Read by hand from TCA\'s audited financial statements inside '
                             'Waterford\'s 10-K. No pattern caught it: the word is '
                             '"relinquishment", not "management".'
                             + WATERFORD_TYPO.get(_yr, ''),
        'form': _form, 'filing_date': _fd, 'accession': _acc, 'source_url': _url,
        'manual_read_basis': _lf,
        'figure_type_final': 'RELINQUISHMENT_PAYMENT',
        'figure_type_note_final': 'relinquishment fee earned by Trading Cove Associates from the '
                                  'Mohegan Tribal Gaming Authority, equal to 5% of Mohegan Sun '
                                  'Revenues as the Relinquishment Agreement defines them',
        'value_usd_final': str(_fee), 'value_verbatim': '$%s' % format(_fee, ','),
        'fiscal_period_label_final': 'Relinquishment Fees earned %s (filer\'s label)' % _yr,
        'period_type_final': 'FISCAL_YEAR', 'period_end_final': '%s-12-31' % _yr,
        'fiscal_year': _yr,
        'source_quote_final': WATERFORD_QUOTE[_yr] + ' ' + PERIOD_CAVEAT,
        'derived_from_fee': 'N',
    })))
    rows.append(dict({c: '' for c in COLS}, **dict(WATERFORD_BASE, **{
        'candidate_id': 'MANUAL-%04d' % (_i + 20), 'adjudication': 'ACCEPT',
        'adjudication_note': 'Derived from MANUAL-%04d.' % _i,
        'form': _form, 'filing_date': _fd, 'accession': _acc, 'source_url': _url,
        'manual_read_basis': _lf,
        'figure_type_final': 'DERIVED_FACILITY_GROSS_REVENUES_AS_DEFINED',
        'figure_type_note_final': 'Mohegan Sun Revenues as the Relinquishment Agreement defines '
                                  'them (gross gaming revenues other than Class II, plus all other '
                                  'facility revenues), recovered from the stated fee and the '
                                  'stated 5%',
        'value_usd_final': '%.0f' % (_fee / 0.05),
        'value_verbatim': '$%s fee / 5%%' % format(_fee, ','),
        'value_precision': 'DERIVED_FROM_AN_EXACT_FEE_AND_A_STATED_RATE',
        'fiscal_period_label_final': 'Relinquishment Fees earned %s (filer\'s label)' % _yr,
        'period_type_final': 'FISCAL_YEAR', 'period_end_final': '%s-12-31' % _yr,
        'fiscal_year': _yr,
        'derived_from_fee': 'Y',
        'derivation_input_fee_usd': str(_fee),
        'derivation_stated_percentage': '5',
        'derivation_percentage_base': 'REVENUES_AS_DEFINED_IN_THE_RELINQUISHMENT_AGREEMENT',
        'derivation_percentage_source_accession': _acc,
        'derivation_arithmetic': '%s / 0.05 = %s' % (format(_fee, ','),
                                                     format(int(_fee / 0.05), ',')),
        'derivation_caveat': DER_CAVEAT_W,
        'source_quote_final': WATERFORD_QUOTE[_yr] + ' [rate and base, same filing] "the Authority '
                              'agreed to pay to TCA a fee (the RELINQUISHMENT FEES) equal to 5 '
                              'percent of Revenues, as defined in the Relinquishment Agreement, '
                              'generated by the Mohegan Sun" ... "Revenues [is] defined in the '
                              'Relinquishment Agreement as gross gaming revenues (other than Class '
                              'II gaming revenue) and all other facility revenues"',
    })))


# every candidate must be ruled
ruled = {r['candidate_id'] for r in rows}
missing = [c['candidate_id'] for c in cands if c['candidate_id'] not in ruled]
if missing:
    raise SystemExit('UNRULED CANDIDATES (%d): %s' % (len(missing), missing[:20]))

os.makedirs('review', exist_ok=True)
with io.open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    for r in sorted(rows, key=lambda z: z['candidate_id']):
        w.writerow(r)
from collections import Counter
print('adjudications written:', len(rows), '->', OUT)
for k, v in Counter(r['adjudication'] for r in rows).most_common():
    print('   %-46s %d' % (k, v))
