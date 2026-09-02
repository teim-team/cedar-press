# Philanthropy as a Native-entity discovery channel

*Run 2026-08-06. Scripts: `code/75_philanthropy_schedule_i.py` (pull),
`code/76_philanthropy_classify.py` (triage), `code/77_philanthropy_review_queue.py`
(rulings). Output: `review/agent_native_org_candidates_philanthropy_2026-08-06.csv`,
567 rows. Raw evidence: `data/raw/external/philanthropy/`.*

## The idea, and why it is different from every roster before it

Elijah, 2026-08-06:

> "native americans in philanthropy is also a big org and you can look at the
> shakopee and who they give money to same with san manuel band and we can prob
> find more native orgs we could be missing"

Every roster this project has used is a **list of a kind** — federally recognised
tribes, ANCSA corporations, NHOs, tribal colleges, Native CDFIs. A roster can
only contain organisations that fit its category, so an organisation that fits no
category is invisible to all of them at once.

A grantee list is not a list of a kind. It is a list of **who Native money
actually goes to**, assembled by practitioners who do not care what category an
organisation falls into. That is a different generating process, and it produces
a different population.

The measurement bears this out. Of the **601 distinct grantee EINs** recovered
here, **491 are absent from `data/clean/np_orgs.csv`** — the 12,764-row nonprofit
candidate universe built from a tribal-token scan of the whole IRS Business Master
File. Four out of five grantees of the largest Native grantmakers in the country
were not in the nonprofit corpus at all. They were missed because a name scan can
only find organisations whose names contain tribal words, and a large part of the
Native nonprofit world does not name itself that way: `Nkwusm`, `Ukwakhwa`,
`Hui o Kuapā`, `Waawaate Programs`, `Xinewh-ding`, `He Sapa Otipi`,
`Coup Council`, `Manidoo Ogitigaan`, `Khimstonik`, `Hipeexnu Kii U Nuun Wisiix`.

## What was worked

### Task 1 — Form 990 Schedule I (the structured source)

Schedule I Part II, "Grants and Other Assistance to Domestic Organizations and
Domestic Governments", names every grantee over $5,000 with EIN, address, IRC
section, cash amount and stated purpose. It is a filed federal tax schedule, so
it is a primary document, and it is machine-readable.

Two tax years were pulled for each funder.

| Funder | EIN | Schedule I rows | Cash grants in those rows |
|---|---|---:|---:|
| First Nations Development Institute | 54-1254491 | 575 | $29,214,006 |
| NDN Collective Inc | 82-3776329 | 150 | $25,750,200 |
| Seventh Generation Fund for Indigenous Peoples | 68-0027247 | 123 | $3,935,168 |
| Potlatch Fund | 73-1712905 | 87 | $1,040,743 |
| American Indian College Fund | 52-1573446 | 78 | $31,561,698 |
| Native Americans in Philanthropy | 56-1849598 | 23 | $5,430,883 |
| Indian Land Tenure Foundation | 41-2014273 | 17 | $2,823,735 |
| **Total** | | **1,053** | **$99,756,433** |

Worked and yielded nothing, for reasons worth recording:

- **Native American Agriculture Fund** (83-1326044) files a **990-PF**, not a 990.
  Private-foundation grants live in Part XV, not Schedule I, and the
  `/IRS990ScheduleI` render 404s. NAAF holds the $266M Keepseagle corpus and
  gives almost exclusively to Native agricultural organisations, so this is the
  single most valuable unworked funder in the channel. **Next session: parse
  990-PF Part XV.**
- **Native Ways Federation** (32-0248892) — same, 990-PF.
- **Notah Begay III Foundation**, **American Indian Graduate Center Scholars**,
  **Chickasaw Foundation** — file 990s, but Schedule I Part II is empty. Their
  giving is to *individuals* (scholarships), which is Part III and carries no
  names.
- **Cherokee Nation Education Corporation** (73-1497804) — no e-filed returns
  indexed.

### Task 2 — published grantee lists

**First Nations Development Institute publishes a full Awarded Grants database**
covering 1994–2026 at `https://www.firstnations.org/listing/awarded-grants/`
(464 result pages), plus a per-grantee profile page at
`/grantee-profiles/<slug>/`. Each profile carries the number of grants, total
awarded, years, a project **description**, and — decisively — a **Community
Partners** field naming the affiliated tribe. Example, verbatim from
`https://www.firstnations.org/grantee-profiles/apache-stronghold/`:

> Apache Stronghold | San Carlos, AZ | 6 Grants | $250,000 Total Awarded |
> 2021 - 2025 | … Community Partners: White Mountain Apache Tribe of the Fort
> Apache Reservation, Arizona … Description: This project connects Apache people
> and other Native and non-Native allies to protect Chi'chil Bi'dagoteel (also
> known as Oak Flat), a sacred site for Apache people and many other Indigenous
> people, from copper mining.

78 grantee profiles were retrieved. This is the strongest evidence the channel
offers, because it is the funder writing about its own grantee and naming the
tribal community.

**The tribal funders Elijah named publish no grantee roster, and file no 990.**
That is not a failure of searching; it is a structural fact and the single most
important finding of this run.

## The §7871 finding — why Shakopee and San Manuel cannot be worked this way

ProPublica's Nonprofit Explorer returns **HTTP 404 — no organisation at all** for
every one of these queries, run 2026-08-06:

```
Shakopee Mdewakanton Sioux Community    404
San Manuel Band of Mission Indians      404
Yuhaaviatam of San Manuel Nation        404
Tulalip Tribes Charitable Fund          404
Muckleshoot Charity Fund                404
Morongo Band of Mission Indians         404
Pechanga Band of Indians                404
Seminole Tribe of Florida               404
```

Tribal governments are outside the Form 990 universe under IRC §7871 and related
treatment. They have EINs, they give hundreds of millions of dollars, and **none
of it is reportable on a 990 that anyone can read.** SMSC states on its own site
(https://shakopeedakota.org/philanthropy/initiatives-reports/, retrieved
2026-08-06):

> "Since the 1980s, the tribe has donated more than $400 million to tribal
> communities, local governments, and various causes, and provided $500 million
> in low-interest loans to help other tribes work toward financial stability and
> self-sufficiency."

$400 million of grantmaking, and the site names five recipients: IndigeFit Kids,
the University of Minnesota, Seeds of Native Health, Understand Native Minnesota,
and the American Indian College Fund. There is no grantee list on
`/philanthropy/`, `/philanthropy/smscgives/`, `/philanthropy/initiatives-reports/`
or the `/category/donations/` newsroom feed — only campaign highlights and
announcement stories.

San Manuel is worse: `sanmanuel-nsn.gov` returns **403 to automated fetch**. The
Wayback Machine holds its Charitable Giving section back to 2004, and the pages
that would carry recipients are stubs — `charitable-R2_NEWS-RECENT-GIFTS.php`
(2010) says only:

> "Each year, San Manuel recognizes outstanding local and Native American
> organizations in each of our four program areas at our Forging Hope luncheon."

The 2019 "Community Giving Impact Summary" is referenced on the 2020 page but no
PDF is archived; a CDX query filtered to `mimetype:application/pdf` across
`sanmanuel-nsn.gov*` returns nothing.

**Consequence for the dataset:** the two largest tribal philanthropies in the
country are structurally unreachable through this channel. Reaching them needs
press-release mining, recipient-side acknowledgements (annual-report donor
listings), or a direct ask — all of which are per-recipient work, not a pull.
This is a finding to publish, not a gap to hide: *the largest Native grantmaking
in the United States leaves no machine-readable trace anywhere.*

Note also the trap the search itself surfaced: querying **"Mohegan Tribe"**
returns `Great Council Of Pennsylvania Improved Order Of Red Men` and
`Great Council Of West Virginia Improved Order Of Red Men` — the same fraternal-
lodge trap already recorded for `Sioux Tribe 128`. Querying
**"Mashantucket Pequot"** returns an International Association of Fire Fighters
local whose mailing address is in Mashantucket, CT.

## Method

1. **Funder resolution** — ProPublica Nonprofit Explorer search API, one query
   per funder name.
2. **Schedule I extraction** — the org HTML page yields `object_id` per filing;
   `https://projects.propublica.org/nonprofits/full_text/<object_id>/IRS990ScheduleI`
   renders the schedule. Access notes, measured:
   - `download-xml?object_id=…` → **403 Security Check** (Cloudflare-style).
   - `s3.amazonaws.com/irs-form-990/<object_id>_public.xml` → **404 NoSuchKey**;
     the AWS mirror is no longer updated, IRS moved to per-year ZIPs.
   - Responses are gzipped; `curl` needs `--compressed`.
3. **EIN resolution** — every grantee EIN queried against the ProPublica
   organisation record for its legal name, city, state, NTEE and filing status.
4. **Mission pass** — for any grantee whose *name* carries no Native identifier,
   its own Form 990 Part I/III mission statement was retrieved. This is the step
   that reaches the invisible class: the organisation's own words about itself,
   in a filed federal document.
5. **Funder-profile pass** — First Nations grantee profiles for anything still
   unruled.
6. **Spine check** — `code/33_apply_party_rulings.resolve_entity`, imported, not
   re-implemented (standing rule 8).

Pull discipline: `logs/_HOSTLOCK_projects.propublica.org.json` claimed before the
first request; strictly sequential, 1.2 s spacing, exponential backoff on 429/503.
**`api.usaspending.gov` was not touched — zero requests** (the subaward puller,
PID 15684, held that host throughout, verified via `Win32_Process.CommandLine`).

## What the channel produced

| Ruling | Rows |
|---|---:|
| `NATIVE_ORG` | 347 |
| `ALREADY_IN_SPINE` | 85 |
| `UNRESOLVED` | 78 |
| `NOT_NATIVE` | 57 |
| **In the queue** | **567** |
| Held for the TCU- agent (not proposed) | 34 |

`NATIVE_ORG` breaks down by *what document carried the ruling*, which matters
more than the count:

| Evidence that carried the ruling | Rows |
|---|---:|
| The organisation's own 990 mission statement | 162 |
| A Native identifier in the organisation's own IRS legal name | 84 |
| The funder certified the grantee as a tribe under IRC 7871 | 63 |
| **The funder published the affiliated tribe** (First Nations profile) | **31** |
| The funder's published project description | 7 |

The 200 rows carried by a mission statement, a funder profile or a funder
description are the ones no roster and no name filter could have produced.

**`UNRESOLVED` is a real ruling here, not a dodge.** 78 organisations had no
retrievable evidence in either direction — 990-N postcard filers, non-filers, or
EINs with no e-filed return. Calling them `NOT_NATIVE` would be a false
attribution in the negative direction, which the standing rule forbids just as
firmly as the positive one. They are handed to Elijah as an explicit refusal to
assert.

### Which funder's list was most productive

| Funder | Candidates | Ruled `NATIVE_ORG` | Grantees no other funder revealed |
|---|---:|---:|---:|
| First Nations Development Institute | 310 | 213 | 253 |
| NDN Collective | 132 | 76 | 88 |
| Seventh Generation Fund | 106 | 71 | 66 |
| Potlatch Fund | 71 | 38 | 53 |
| Native Americans in Philanthropy | 19 | 5 | 13 |
| Indian Land Tenure Foundation | 14 | 8 | 9 |
| American Indian College Fund | 7 | 5 | 6 |

**First Nations Development Institute is the channel.** It revealed 213 of the
347 Native organisations, 253 of them exclusive to its list, and it is the only
funder that also publishes a grantee database with tribal affiliations. If only
one funder is ever refreshed, refresh this one.

American Indian College Fund gave the most money of any funder here ($31.6M) and
produced the fewest candidates (7), because its grantees are tribal colleges — a
closed, already-known population, held out for the TCU- agent. **Dollars are a
poor predictor of discovery value; grantee heterogeneity is the predictor.**

## What this channel is good for, and what it is not

**Good for:**
- Native organisations that fit no category and therefore appear on no roster —
  language-revitalisation collectives, food-sovereignty projects, land trusts,
  cultural centres, birthworker collectives, buffalo programmes.
- Organisations whose names are in an Indigenous language and contain no English
  tribal token. A name filter cannot see these; a grantee list names them.
- Non-federally-recognised and state-recognised tribal bodies
  (`Chihene Nde Nation of New Mexico`, `Tubatulabals of Kern Valley`,
  `Yaquis of Southern California`, `United Confederation of Taino People`) that
  fall out of contracting-flag universes entirely.
- Tribal governments and instrumentalities: **153 of 601 grantee EINs have no
  IRS Business Master File record at all**, and most were filed by the funder
  with IRC section `TRIBE`. An EIN present on a Schedule I and absent from the
  BMF is a near-signature of a §7871 entity.
- **Correcting the exclusion list.** Seven grantee EINs sit in
  `data/spine/nonprofit_exclusion_rulings.csv`. Four are documented false
  negatives of that mechanical filter, each now ruled `NATIVE_ORG` here on the
  organisation's own filed mission statement:

  | EIN | Organisation | Its own Form 990 mission, verbatim |
  |---|---|---|
  | 85-0232968 | Indian Pueblo Cultural Center Inc | "TO PRESERVE AND PERPETUATE PUEBLO CULTURE AND TO ADVANCE UNDERSTANDING BY PRESENTING WITH DIGNITY AND RESPECT THE ACCOMPLISHMENTS AND EVOLVING HISTORY OF THE PUEBLO PEOPLE OF NEW MEXICO." |
  | 42-1552956 | Dakota Wicohan | "PRESERVING DAKOTA AS A LIVING LANGUAGE AND THROUGH IT TRANSMIT DAKOTA LIFE WAYS TO FUTURE GENERATIONS" |
  | 46-0990639 | Laguna Community Foundation | ruled on grant evidence and IRS record; Pueblo of Laguna, NM |
  | 84-1848251 | Mahchiwminahnahtik Chippewa and Cree Language | ruled on grant evidence and IRS record; Rocky Boy, MT |

  Two are correct exclusions and stay excluded on their own filed missions —
  `NORTH DAKOTA COMMUNITY FOUNDATION` ("TO IMPROVE THE QUALITY OF LIFE FOR
  NORTH DAKOTA'S CITIZENS THROUGH CHARITABLE GIVING AND PROMOTING
  PHILANTHROPY.") and `DAKOTA RURAL ACTION` ("...to protect the agricultural
  economy and lifestyle of South Dakota."). The seventh,
  `NAVAJO TECHNICAL COLLEGE`, is held for the TCU- agent; note that its
  exclusion was already flagged as probably wrong in
  `docs/NONPROFIT_BUILD_LOG_2026-08-05.md` §5, and the grant evidence here
  (First Nations, $1,198,051 across two years) supports that reading.

**Not good for:**
- **Tribal government philanthropy.** See §7871 above. SMSC's $400M and San
  Manuel's giving are invisible. Any claim that this dataset covers "Native
  philanthropy" would be false; it covers *Native foundation* philanthropy.
- **Ownership.** A grantee list says who received money, never who controls the
  board. Every `NATIVE_ORG` row here carries `ownership=unknown` unless the
  funder certified the grantee as a tribe. Ownership and service are recorded in
  separate fields for exactly this reason.
- **Completeness in time.** Two tax years were pulled. First Nations' published
  database goes back to 1994; the 990 route reaches 2015 at best.
- **Small grants.** Schedule I Part II has a $5,000 floor. Below it, nothing.
- **Individual grants.** Part III carries no names. Scholarship funders are
  therefore invisible in this channel even when they file 990s — which is why
  Notah Begay III, AIGC Scholars and the Chickasaw Foundation returned zero rows.
- **Fiscally sponsored projects.** They have no EIN and appear under the sponsor's.
  Measured here: `MOTHER KUSKOKWIM TRIBAL COALITION` is filed under EIN
  68-0535413, which the IRS records as **Native Movement**; the
  `TONGVA BASKET COLLECTIVE` grant is filed under **Regents of the University of
  California**. The grantee named is not always the legal person paid.

## Defects found and reported, not patched

**1. The shared resolver's `containment` tier misfires on nonprofit names.**
`resolve_entity` has four tiers; `exact`, `alias` and `core` behaved correctly on
all 601 grantees. `containment` did not. It fired 125 times and conflates two
different things:

- correct: a tribal government under its long official name
  (`FOND DU LAC BAND OF LAKE SUPERIOR CHIPPEWA` → spine `Fond du Lac`);
- wrong: a distinct legal person that merely carries a tribe's name
  (`Tulalip Foundation`, `Rosebud Economic Development Corporation`,
  `Hopi School Inc`) — which this channel exists to find;
- plainly wrong: `Indian Pueblo Cultural Center Inc` (NM) →
  `Makaha Cultural Learning Center` (HI). `STRUCTURAL` eats *indian* and
  *pueblo*, leaving `{center, cultural}`, which is a subset of
  `{makaha, learning, center, cultural}`. Also
  `International Indian Treaty Council` → `Council Native Corporation`,
  `Native Sister Circle Inc` → `Circle`,
  `United Tribes of Bristol Bay` → `Bristol Bay Native Corporation`,
  `Ahtna Intertribal Resource Commission` → `Ahtna, Incorporated`.

Common shape: once `STRUCTURAL` strips indian/native/tribal/pueblo/band/nation/
corporation, what remains is a generic English noun (council, center, circle,
bay) and containment matches on the residue. Script 77 therefore accepts
`containment` as `ALREADY_IN_SPINE` **only** when the residual words are
government form words with no organisational descriptor, and flags every other
containment match in the note. The resolver itself was **not modified** — one
resolver, and a name-matching change belongs to its owner.

**2. Two bugs in this pass's own first draft, both caught and fixed, both worth
remembering because they are the generic shape of the failure:**

- A boilerplate filter written as `^(…|none|n/?a|…)` matched the first two
  letters of `NATIVE GOVERNANCE CENTER` and discarded the mission of an
  organisation that describes itself as "A NATIVE-LED NONPROFIT" — which then
  fell through to `NOT_NATIVE`. Short alternations need a full-string test, not a
  prefix test.
- Token matching by substring matched `reservation` inside `PRESERVATION` and
  promoted `PAWNEE SEED PRESERVATION SOCIETY` and
  `TATANKA OYATE PRESERVATION SOCIETY` on a syllable. Substring matching on a
  name is how a place-name *filter* becomes a place-name *generator*. Word
  boundaries are mandatory.

**2b. Two copies of the same constant, and the stale one is the one that
fired.** `REFUSE_ALONE` was defined in script 76 (for NAMES) and again in
script 77 (for MISSION text). `dakota` was added to the first and not the
second, so the mission reader happily promoted `North Dakota Community
Foundation` — mission "TO IMPROVE THE QUALITY OF LIFE FOR NORTH DAKOTA'S
CITIZENS THROUGH CHARITABLE GIVING AND PROMOTING PHILANTHROPY" — and
`Dakota Rural Action` — "to protect the agricultural economy and lifestyle of
South Dakota" — to `NATIVE_ORG`. Both are now `NOT_NATIVE` on their own filed
missions, and the state mask is applied to mission and funder-description text
as well as to names. Duplicated constants drift; if a later pass consolidates
these lists into one module, that is a real improvement and not tidying.

**2c. The spine-match guard needed a STATE check, not just a word check.**
`Indian Pueblo Cultural Center Inc` (NM) resolved by containment to
`Makaha Cultural Learning Center` (HI), and the residual-word guard could not
catch it because the residue was `{indian, pueblo, inc}` — all government form
words. A containment match is now rejected outright when the spine row's state
conflicts with the grantee's state, or when the spine name's distinctive
content is only generic English nouns. Seven misfires were caught by these two
guards; the affected rows carry `RESOLVER MISFIRE, do not trust it` in the note.

**3. A new place-name trap, same shape as the 282 withdrawals.** `dakota` is a
state name in `North Dakota Community Foundation` (ND) and `Dakota Rural Action`
(SD). It has been added to `REFUSE_ALONE`, and `North/South Dakota`,
`New Mexico`, `Indiana` are masked out of the name before tokenising, exactly as
`Umatilla County` had to be.

**4. Unrelated to this work, observed while running the guard:**
`code/62_no_regression_check.py` reports `tier_A FELL 2,149 -> 2,148` in
`data/clean/cedar_identifier_ledger_final.csv`. Nothing in this pass writes that
file — this pass wrote only to `review/`, `data/raw/external/philanthropy/`,
`code/` and `logs/`. It belongs to whichever concurrent agent owns the ledger.
The spine also grew from 952 to 1,310 entities during this session as the TCU/
CDFI/BIE/UIO agents worked; the spine check here was re-run against the freshest
snapshot at build time, and 86 grantees resolved to it.

## Boundaries respected

- `TCU-`, `CDFI-`, `BIE-`, `UIO-` classes belong to other agents. 34 grantees
  that are plainly tribal colleges were **held out of the queue** and written to
  `data/raw/external/philanthropy/_held_for_other_agents_2026-08-06.csv` instead,
  as a cross-check against the TCU agent's roster rather than as competing
  proposals. Note that `Spruce Root Inc` was already picked up by the CDFI agent
  during this session and now resolves as `CDFI-SPRCRT-00`; any remaining
  finance-shaped candidate in this queue should be checked against that agent's
  work before minting.
- Nothing under `data/spine/`, `data/clean/cedar_*` or `review/cedar_*.html` was
  modified. `code/00_run_all.py` was not run.

## Next, ranked

1. **Native American Agriculture Fund 990-PF Part XV.** $266M Keepseagle corpus,
   exclusively Native agricultural grantees, and a form this pass cannot yet
   parse. Highest value per unit of work in the channel.
2. **First Nations' full Awarded Grants database, 1994–2026** — 464 pages, each
   grant carrying a description. The 2-year 990 window used here is a sample of
   it. Paginating `?pg=N` would multiply the population and add three decades of
   history that the 990 route cannot reach.
3. **Rule the 81 `UNRESOLVED`.** Most are 990-N filers; a web search per
   organisation is the only route, and it is the class most likely to be genuinely
   Native.
4. **Reverse the exclusion list on the four documented false negatives.**
5. **Recipient-side capture for tribal-government philanthropy** — grantee annual
   reports name SMSC, San Manuel, Tulalip and Muckleshoot in donor listings. That
   is the only machine-readable trace tribal giving leaves, and it inverts the
   channel: instead of reading the funder's return, read the recipients'.
