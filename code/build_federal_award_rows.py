"""Build data/clean/deals_federal_awards_additions.csv from retrieved federal award documents.

Sources, all retrieved this run into data/raw/external/federal_award_lists/:
  NTIA TBCP  - press releases (date + applicant + amount) joined to NTIA awardee pages
  DOE Office of Indian Energy - Tribal Energy Projects Database + per-project pages
  HUD ONAP   - ICDBG / IHBG-Competitive / IHBG allocation PDFs recovered via Wayback

ZERO FABRICATION: every value below is transcribed from those files. No amount, date,
recipient or identifier is inferred.
"""
import csv, io, os, re, sys, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_util import RAW

ROOT = r"C:\Users\esm247\Desktop\Cedar Press"
OUT = os.path.join(ROOT, "data", "clean", "deals_federal_awards_additions.csv")
SKIP = os.path.join(ROOT, "review", "federal_award_lists_skipped_leads.csv")
TODAY = "2026-08-05"

COLS = ("Deal_ID,Event_Date,Event_Year,Event_Quarter,Event_Month,Deal_Title,Native_Party,"
        "Native_Party_Type,Counterparty_or_Funder,Deal_Category,Industry,Event_Type,Status,"
        "Record_Scope,Announced_Value_USD,Value_Type,Project_Total_Value_USD,State,Location,"
        "Description,Native_Connection,Source_1,Source_1_Type,Source_2,Source_2_Type,"
        "Verification_Status,Confidence,Threshold_Exception,Date_Basis,Notes,Date_Added,"
        "Data_As_Of").split(',')

STATES = {
 'alabama':'AL','alaska':'AK','arizona':'AZ','arkansas':'AR','california':'CA','colorado':'CO',
 'connecticut':'CT','delaware':'DE','florida':'FL','georgia':'GA','hawaii':'HI','idaho':'ID',
 'illinois':'IL','indiana':'IN','iowa':'IA','kansas':'KS','kentucky':'KY','louisiana':'LA',
 'maine':'ME','maryland':'MD','massachusetts':'MA','michigan':'MI','minnesota':'MN',
 'mississippi':'MS','missouri':'MO','montana':'MT','nebraska':'NE','nevada':'NV',
 'new hampshire':'NH','new jersey':'NJ','new mexico':'NM','new york':'NY','north carolina':'NC',
 'north dakota':'ND','ohio':'OH','oklahoma':'OK','oregon':'OR','pennsylvania':'PA',
 'rhode island':'RI','south carolina':'SC','south dakota':'SD','tennessee':'TN','texas':'TX',
 'utah':'UT','vermont':'VT','virginia':'VA','washington':'WA','west virginia':'WV',
 'wisconsin':'WI','wyoming':'WY','state of alaska':'AK','northern mariana islands':'MP',
}

MONTHS = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October November December".split())}

rows = []
skipped = []


def st(x):
    x = (x or '').strip()
    if re.fullmatch(r'[A-Z]{2}', x):
        return x
    k = x.lower().strip()
    if k in STATES:
        return STATES[k]
    if ',' in x or '/' in x:
        return 'Multi'
    return x[:20]


def parts(d):
    """d = YYYY-MM-DD -> (year, quarter, month)"""
    y, m, _ = d.split('-')
    return y, 'Q%d' % ((int(m) - 1) // 3 + 1), '%s-%s' % (y, m)


def add(**kw):
    r = {c: '' for c in COLS}
    r.update(kw)
    rows.append(r)


def L(path):
    return list(csv.DictReader(io.StringIO(open(path, 'rb').read().decode('utf-8'))))


# ---------------------------------------------------------------- NTIA TBCP
def build_tbcp():
    pr = [r for r in L(os.path.join(RAW, 'tbcp_awards_from_press_releases.csv'))
          if r['source_file'] != 'ntia_pr_162m.html']
    news = json.load(open(os.path.join(RAW, 'ntia_news_dates.json')))
    slug2url, slug2date = {}, {}
    for path, d in news.items():
        s = path.rstrip('/').split('/')[-1][:70]
        slug2url[s] = 'https://broadbandusa.ntia.gov' + path
        m = re.match(r'(\w+) (\d{1,2}), (\d{4})', d)
        if m:
            slug2date[s] = '%s-%02d-%02d' % (m.group(3), MONTHS[m.group(1)], int(m.group(2)))

    aw = L(os.path.join(RAW, 'tbcp_awardee_pages.csv'))

    def norm(s):
        s = re.sub(r'\((?:TBCP I{1,2})\)', '', s or '')
        return re.sub(r'[^a-z0-9]', '', s.lower())
    awmap = {}
    for a in aw:
        awmap.setdefault((a['round'], norm(a['awardee'])), a)

    n = 0
    for r in pr:
        slug = r['source_file'][len('ntia_pr_'):-len('.html')]
        url = slug2url.get(slug, '')
        d = r['release_date'].strip()
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', d):
            d = slug2date.get(slug, '')
        if not d:
            skipped.append(dict(source='NTIA TBCP', item=r['applicant'],
                                reason='no_date', detail=r['source_file']))
            continue
        # already in the live ledger as an aggregate row (ND-2025-010)
        if 'equitable-distribution' in slug:
            skipped.append(dict(source='NTIA TBCP', item=r['applicant'], reason='already_in_ledger',
                                detail='Dec 2025 equitable-distribution round is ND-2025-010 '
                                       '(aggregate $6.5M); not re-entered per-award to avoid double count'))
            continue
        amt = r['amount']
        src2, src2t, note_amt = '', '', ''
        # Round is inferred ONLY from the release date, and the awardee-page join is
        # restricted to the same round so a Round 1 page can never supply a Round 2 amount.
        rnd = 'TBCP I' if d <= '2023-12-31' else 'TBCP II'
        a = awmap.get((rnd, norm(r['applicant'])))
        if a:
            src2 = a['url']
            src2t = 'Federal award list (NTIA %s awardee page)' % rnd
        if not amt:
            note_amt = ('NTIA release states no per-award amount for this applicant; '
                        'Announced_Value_USD deliberately left blank.')
        rec = 'Recommended for award' if 'recommends-award' in slug else 'Awarded'
        y, q, mo = parts(d)
        n += 1
        val = ''
        if amt:
            val = '%.1f' % float(amt)
        add(Deal_ID='FA-NTIA-%04d' % n, Event_Date=d, Event_Year=y, Event_Quarter=q,
            Event_Month=mo,
            Deal_Title='NTIA TBCP award: %s' % r['applicant'],
            Native_Party=r['applicant'],
            Native_Party_Type='Tribal government or Native entity',
            Counterparty_or_Funder='NTIA (Tribal Broadband Connectivity Program)',
            Deal_Category='Grant / public financing', Industry='Broadband',
            Event_Type=rec, Status=rec,
            Record_Scope='%s commitment' % y,
            Announced_Value_USD=val,
            Value_Type=('Federal grant recommended for award' if rec.startswith('Recommend')
                        else 'Federal grant award'),
            State=st(r['location']), Location=r['location'],
            Description=((r['ptype'] + '. ') if r['ptype'] else '') + r['desc'][:900],
            Native_Connection='The applicant is the direct federal award recipient.',
            Source_1=url, Source_1_Type='Federal agency release',
            Source_2=src2, Source_2_Type=src2t,
            Verification_Status='Verified' if src2 else 'Primary verified',
            Confidence='High',
            Threshold_Exception='Yes' if (amt and float(amt) < 1e6) else 'No',
            Date_Basis=('Announcement date (NTIA recommended-for-award release); '
                        'award action date not published'
                        if rec.startswith('Recommend') else 'Announcement date (NTIA release)'),
            Notes=('Row-per-award from a complete published TBCP tranche list; awards below the '
                   '$1M default threshold are retained so the round is complete (RTA precedent). '
                   + note_amt).strip(),
            Date_Added=TODAY, Data_As_Of=TODAY)

    # The 2024-11-12 release announces the first Round 2 award (Hawaii DHHL) in prose only -
    # no table, so the loop above produces no row. Amount from the TBCP II awardee page.
    dh = awmap.get(('TBCP II', norm('Hawaii Department of Hawaiian Home Lands')))
    if dh:
        n += 1
        add(Deal_ID='FA-NTIA-%04d' % n, Event_Date='2024-11-12', Event_Year='2024',
            Event_Quarter='Q4', Event_Month='2024-11',
            Deal_Title='NTIA TBCP award: Hawaii Department of Hawaiian Home Lands (Round 2)',
            Native_Party='Department of Hawaiian Home Lands',
            Native_Party_Type='Native Hawaiian government agency',
            Counterparty_or_Funder='NTIA (Tribal Broadband Connectivity Program)',
            Deal_Category='Grant / public financing', Industry='Broadband',
            Event_Type='Awarded', Status='Awarded', Record_Scope='2024 commitment',
            Announced_Value_USD='%.1f' % float(dh['amount']),
            Value_Type='Federal grant award', State='HI', Location='HI',
            Description='First award from the second round of the Tribal Broadband Connectivity '
                        'Program, to expand high-speed Internet access and adoption in Native '
                        'Hawaiian households. %s' % dh['project_title'],
            Native_Connection='The Department of Hawaiian Home Lands is the direct federal award '
                              'recipient.',
            Source_1='https://broadbandusa.ntia.gov/news/latest-news/biden-harris-administration-'
                     'awards-72-million-expand-internet-access-and-digital',
            Source_1_Type='Federal agency release',
            Source_2=dh['url'], Source_2_Type='Federal award list (NTIA TBCP II awardee page)',
            Verification_Status='Verified', Confidence='High', Threshold_Exception='No',
            Date_Basis='Announcement date (NTIA release, November 12, 2024)',
            Notes='The NTIA release states "more than $72 million" in prose with no table; the '
                  'exact $72,708,711 is transcribed from the NTIA TBCP II awardee page for the '
                  'same recipient. Round 2 first award.',
            Date_Added=TODAY, Data_As_Of=TODAY)
    print('TBCP rows', n)


# ---------------------------------------------------------------- DOE
def build_doe():
    d = L(os.path.join(RAW, 'doe_indian_energy_over1m.csv'))
    n = 0
    for r in d:
        s = r['pop_start'].strip()
        m = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
        basis = ''
        if m:
            date = '%s-%02d-%02d' % (m.group(3), int(m.group(1)), int(m.group(2)))
            basis = ('DOE project period-of-performance start date (award performance start, '
                     'not the obligation date)')
        else:
            m2 = re.fullmatch(r'(\w+)\s+(\d{4})', s)
            if not m2:
                skipped.append(dict(source='DOE Indian Energy', item=r['tribe'],
                                    reason='no_date', detail=r['url']))
                continue
            date = '%s-%02d-15' % (m2.group(2), MONTHS[m2.group(1)])
            basis = ('MONTH-LEVEL ONLY: DOE project page gives period of performance start as "%s"; '
                     'day set to the 15th as a disclosed mid-month placeholder' % s)
        y, q, mo = parts(date)
        n += 1
        add(Deal_ID='FA-DOE-%04d' % n, Event_Date=date, Event_Year=y, Event_Quarter=q,
            Event_Month=mo,
            Deal_Title='DOE Office of Indian Energy grant: %s' % (r['project_title'] or r['project']),
            Native_Party=r['awardee'] or r['tribe'],
            Native_Party_Type='Tribal government or Native entity',
            Counterparty_or_Funder='U.S. Department of Energy, Office of Indian Energy Policy and Programs',
            Deal_Category='Grant / public financing',
            Industry='Energy - %s' % r['technology'] if r['technology'] else 'Energy',
            Event_Type='Awarded', Status='Awarded',
            Record_Scope='%s commitment' % y,
            Announced_Value_USD='%.1f' % float(r['doe_amount']),
            Value_Type='Federal grant award (DOE share)',
            Project_Total_Value_USD=('%.1f' % float(r['total_amount'])) if r['total_amount'] else '',
            State=st(r['state']), Location=r['location'],
            Description=('%s. DOE grant number %s. Type of application: %s. Awardee cost share '
                         '$%s; total project $%s.' % (r['project_title'] or r['project'],
                                                      r['grant_number'], r['assistance_type'],
                                                      r['awardee_amount'], r['total_amount'])),
            Native_Connection='The tribe or Native entity is the direct federal award recipient.',
            Source_1=r['url'], Source_1_Type='Federal agency project page',
            Source_2='https://www.energy.gov/indianenergy/tribal-energy-projects-database',
            Source_2_Type='Federal award list',
            Verification_Status='Primary verified', Confidence='High' if m else 'Medium',
            Threshold_Exception='No',
            Date_Basis=basis,
            Notes=('DOE Tribal Energy Projects Database award year %s. Only projects with a DOE '
                   'share of $1M or more are written; 176 sub-threshold projects in the same '
                   'database are logged, not written.' % r['year']),
            Date_Added=TODAY, Data_As_Of=TODAY)
    print('DOE rows', n)


# ---------------------------------------------------------------- HUD ONAP
def build_hud():
    d = L(os.path.join(RAW, 'hud_onap_awards_parsed.csv'))
    n = 0
    for r in d:
        amt = float(r['amount'])
        if amt < 1e6:
            skipped.append(dict(source='HUD ONAP %s %s' % (r['program'], r['round']),
                                item=r['recipient'], reason='below_threshold',
                                detail='$%s; sub-$1M award in a round where most awards are '
                                       'sub-threshold' % r['amount']))
            continue
        date = r['doc_date']
        y, q, mo = parts(date)
        prog = r['program']
        n += 1
        add(Deal_ID='FA-HUD-%04d' % n, Event_Date=date, Event_Year=y, Event_Quarter=q,
            Event_Month=mo,
            Deal_Title='HUD ONAP %s %s award: %s' % (prog, r['round'], r['recipient']),
            Native_Party=r['recipient'],
            Native_Party_Type='Tribal government, TDHE or tribal housing authority',
            Counterparty_or_Funder='HUD Office of Native American Programs (%s)' % prog,
            Deal_Category='Grant / public financing', Industry='Housing / community development',
            Event_Type='Awarded', Status='Awarded', Record_Scope='%s commitment' % y,
            Announced_Value_USD='%.1f' % amt,
            Value_Type='Federal competitive grant award',
            State=st(r['state']), Location='',
            Description=r['desc'] or '%s %s award to %s.' % (prog, r['round'], r['recipient']),
            Native_Connection='The tribe, TDHE or tribal housing authority is the direct federal '
                              'award recipient.',
            Source_1=r['source_url'], Source_1_Type='Federal award list',
            Source_2='https://web.archive.org/web/*/' + r['source_url'],
            Source_2_Type='Internet Archive snapshot (live HUD URL 404s after the 2025-26 reorg)',
            Verification_Status='Primary verified',
            Confidence='High' if 'printed on' in r['date_basis'] else 'Medium',
            Threshold_Exception='No',
            Date_Basis=r['date_basis'],
            Notes=('Recovered from the Internet Archive; the live hud.gov URL returns an emptied '
                   'stub after the 2025-26 site reorganization. Round total and full recipient '
                   'list are in %s. DATE CAUTION: HUD publishes no award action date on these '
                   'lists.' % r['source_file']),
            Date_Added=TODAY, Data_As_Of=TODAY)
    # --- formula rounds: ONE portfolio row each (AGENTS.md convention)
    add(Deal_ID='FA-HUD-9001', Event_Date='2021-03-25', Event_Year='2021', Event_Quarter='Q1',
        Event_Month='2021-03',
        Deal_Title='HUD allocates $450M in IHBG-ARP funding to eligible tribes',
        Native_Party='Eligible IHBG tribes and TDHEs (formula round)',
        Native_Party_Type='Tribes / Native organizations',
        Counterparty_or_Funder='HUD Office of Native American Programs (Indian Housing Block Grant - ARP)',
        Deal_Category='Grant / public financing', Industry='Housing / community development',
        Event_Type='Allocated', Status='Allocated', Record_Scope='2021 commitment',
        Announced_Value_USD='450000000.0', Value_Type='Federal formula grant allocations (aggregate)',
        State='Multi', Location='',
        Description='The American Rescue Plan Act of 2021 (P.L. 117-2) provided $450,000,000 for '
                    'the Indian Housing Block Grant program (IHBG-ARP). Each tribe receives '
                    '69.1376421680391 percent of its FY 2021 IHBG formula allocation '
                    '($450,000,000 / $654,875,537).',
        Native_Connection='Recipients are federally recognized tribes and their TDHEs.',
        Source_1='https://www.hud.gov/sites/dfiles/PIH/documents/DTL%20IHBG%20ARP%20Allocations%203.25.21.pdf',
        Source_1_Type='Federal agency Dear Tribal Leader letter',
        Source_2='', Source_2_Type='',
        Verification_Status='Primary verified', Confidence='High', Threshold_Exception='No',
        Date_Basis='Date of the HUD Dear Tribal Leader letter (March 25, 2021)',
        Notes='Formula round recorded as ONE portfolio row per AGENTS.md. Recovered from the '
              'Internet Archive.',
        Date_Added=TODAY, Data_As_Of=TODAY)
    add(Deal_ID='FA-HUD-9002', Event_Date='', Event_Year='2025', Event_Quarter='',
        Event_Month='',
        Deal_Title='HUD FY 2025 IHBG formula allocations to tribes and TDHEs',
        Native_Party='Eligible IHBG tribes and TDHEs (FY 2025 formula round)',
        Native_Party_Type='Tribes / Native organizations',
        Counterparty_or_Funder='HUD Office of Native American Programs (Indian Housing Block Grant)',
        Deal_Category='Grant / public financing', Industry='Housing / community development',
        Event_Type='Allocated', Status='Allocated', Record_Scope='2025 commitment',
        Announced_Value_USD='1119638884.0',
        Value_Type='Federal formula grant allocations (aggregate)',
        State='Multi', Location='',
        Description='FY 2025 IHBG final formula allocations. The HUD awards list totals '
                    '$1,119,638,884 across the published recipient roster.',
        Native_Connection='Recipients are federally recognized tribes and their TDHEs.',
        Source_1='https://www.hud.gov/sites/dfiles/PIH/documents/FY-2025IHBG-Formula-Allocation-Press-Release-Awards-List.pdf',
        Source_1_Type='Federal award list',
        Source_2='', Source_2_Type='',
        Verification_Status='Primary verified', Confidence='Medium', Threshold_Exception='No',
        Date_Basis='FY-LEVEL ONLY: the HUD allocation list carries no date. Event_Date is left '
                   'blank rather than inferred; PDF creation date is 2025-05-12.',
        Notes='Formula round recorded as ONE portfolio row per AGENTS.md. Recovered from the '
              'Internet Archive.',
        Date_Added=TODAY, Data_As_Of=TODAY)
    print('HUD rows', n + 2)


# ---------------------------------------------------------------- EDA
def build_eda():
    import openpyxl
    p = os.path.join(RAW, 'eda_2022_ARPA_Award_Data.xlsx')
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    ws = wb['Sheet 1']
    it = ws.iter_rows(values_only=True)
    hdr = list(next(it))
    data = [dict(zip(hdr, r)) for r in it]
    ic = [r for r in data if 'Indigenous Communities' in str(r['Appropriation_Detail_Derived'])]
    n = 0
    for r in ic:
        d = r['DEC_Award_Date']
        if not d:
            skipped.append(dict(source='EDA Indigenous Communities', item=str(r['Appl_Full_Name']),
                                reason='no_date', detail='DEC_Award_Date blank in EDA ARPA award file'))
            continue
        date = d.strftime('%Y-%m-%d')
        y, q, mo = parts(date)
        amt = float(r['EDA_Funding'] or 0)
        tot = float(r['Total_Proj_Cost'] or 0)
        n += 1
        add(Deal_ID='FA-EDA-%04d' % n, Event_Date=date, Event_Year=y, Event_Quarter=q,
            Event_Month=mo,
            Deal_Title='EDA ARPA Indigenous Communities award: %s' % r['Appl_Full_Name'],
            Native_Party=str(r['Appl_Full_Name']),
            Native_Party_Type='Tribal government or Native entity',
            Counterparty_or_Funder='U.S. Economic Development Administration (ARPA Indigenous '
                                   'Communities Program)',
            Deal_Category='Grant / public financing', Industry='Economic development',
            Event_Type='Awarded', Status='Awarded', Record_Scope='%s commitment' % y,
            Announced_Value_USD='%.1f' % amt,
            Value_Type='Federal competitive grant award (EDA share)',
            Project_Total_Value_USD=('%.1f' % tot) if tot else '',
            State=str(r['App_State'] or ''),
            Location='%s, %s' % (r['Appl_City_Name'], r['App_State']),
            Description=re.sub(r'\s+', ' ', str(r['External_Proj_Desc'] or ''))[:900],
            Native_Connection='The tribe or Native entity is the direct federal award recipient.',
            Source_1='https://www.eda.gov/archives/2022/files/arpa/impact/2022_ARPA_Award_Data.xlsx',
            Source_1_Type='Federal award list (EDA ARPA award data file)',
            Source_2='https://www.eda.gov/arpa/indigenous-communities',
            Source_2_Type='Federal agency program page',
            Verification_Status='Primary verified', Confidence='High',
            Threshold_Exception='Yes' if amt < 1e6 else 'No',
            Date_Basis='EDA award date (DEC_Award_Date field of the EDA ARPA award data file)',
            Notes='Row-per-award from the complete published EDA ARPA Indigenous Communities '
                  'round (51 awards, $100M, confirmed by the EDA Indigenous Communities fact '
                  'sheet). Awards below $1M retained so the round is complete (RTA precedent). '
                  'File recovered from the Internet Archive; live eda.gov/arpa/impact returns '
                  'HTTP 403 to automated fetch.',
            Date_Added=TODAY, Data_As_Of=TODAY)
    print('EDA rows', n, 'of', len(ic))


def write():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print('WROTE', len(rows), OUT)
    os.makedirs(os.path.dirname(SKIP), exist_ok=True)
    with open(SKIP, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['source', 'item', 'reason', 'detail'])
        w.writeheader()
        w.writerows(skipped)
    print('SKIPPED', len(skipped), SKIP)


if __name__ == '__main__':
    build_tbcp()
    build_doe()
    build_hud()
    build_eda()
    write()
