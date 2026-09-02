# Nonprofit classification research log

*Run 2026-08-05. Agent research pass over `review/agent_research_queue_2026-08-05.csv` (375 EINs).*
*Output: `review/rulings_inbox_2026-08-05_agent_nonprofit.csv` (375 rows, rulings-inbox format).*
*Run log: `logs/38_nonprofit_classification.log`.*

## What this pass was

Every row in the queue asks one question: is this organisation Native, or does it merely carry a
tribe-derived place name? The queue exists because tier A leaked place-named organisations
(the $603M electric co-op, the $464M hospital) into a Native nonprofit dataset. The flag runs both
ways — the same queue also held real tribal colleges and tribal housing entities sitting in the
exclusion pile. Both directions were ruled here.

Taxonomy used, exactly as specified: `tribally_controlled`, `native_controlled`, `native_serving`,
`place_name_coincidence`, `unresolved`.

## Findings by class

| Ruling | Orgs | Revenue represented | Share of queue revenue |
|---|---:|---:|---:|
| `place_name_coincidence` | 282 | $1580.6M | 95.5% |
| `native_controlled` | 71 | $6.4M | 0.4% |
| `tribally_controlled` | 11 | $66.6M | 4.0% |
| `native_serving` | 7 | $697K | 0.0% |
| `unresolved` | 4 | $11K | 0.0% |
| **total** | **375** | **$1654.3M** | **100%** |

Confidence distribution: medium 231, high 116, low 24, n/a 4.

## Revenue settled

- Total revenue attached to the queue: **$1654.3M** across 169 rows carrying a revenue figure.
- Revenue settled with a ruling and an evidence URL: **$1654.3M (100.0%)**.
- Revenue left `unresolved`: **$11K**. All four unresolved rows are at or below $10K.
- Revenue demoted out of tier A as place-name leakage: **$1580.6M (95.5%)** — the queue is overwhelmingly a demotion problem by dollars, and a promotion problem by count.
- Revenue promoted or confirmed as Native: **$73.7M**.

Concentration held as forecast: the top 5 rows are 80.5% of queue revenue and the top 25 are 96.8%.
Fifteen rulings settle 93.3% of the dollars.

## Top 25 by revenue, with the ruling

| # | EIN | Organisation | ST | Revenue | Ruling | Conf | Basis |
|---:|---|---|---|---:|---|---|---|
| 1 | 930300375 | Umatilla Electric Cooperative Association | OR | $603.1M | `place_name_coincidence` | high | Member-owned co-op incorporated 1937; seven directors elected by member districts and who are themselves customers; site states no tribal ownership... |
| 2 | 860098923 | Yavapai Community Hospital Association | AZ | $464.1M | `place_name_coincidence` | high | dba Dignity Health Yavapai Regional Medical Center; 990 mission is to care for people in western Yavapai County AZ; parent is CommonSpirit/Dignity ... |
| 3 | 560305124 | Lumbee River Electric Membership Corporation | NC | $158.2M | `place_name_coincidence` | medium | 501(c)(12) member-owned co-op inc. 1940, named for the Lumbee/Lumber River. The Lumbee Tribe's own release treats LREMC as an outside partner-donor... |
| 4 | 850098061 | Jemez Mountains Electric Cooperative Inc | NM | $56.4M | `place_name_coincidence` | high | Own site: 'member-owned utility founded in 1948', 31,000 members across five NM counties, eleven trustees elected by the membership by district. No... |
| 5 | 562259380 | Lumbee Land Development Inc | NC | $50.5M | `tribally_controlled` | high | 990 governing body IS the Lumbee Tribal Council - John L Lowery (Tribal Chairman), Sharon Hunt (Council Speaker), Wendy Moore (Vice Chair), Ricky H... |
| 6 | 860206928 | West Yavapai Guidance Clinic | AZ | $39.4M | `place_name_coincidence` | high | dba Polara Health. Own site: founded 1966 by volunteers, largest local nonprofit behavioral-health and crisis provider in Yavapai County AZ, ~9,300... |
| 7 | 620752586 | Douglas-Cherokee Economic Authority Inc | TN | $30.4M | `place_name_coincidence` | medium | Own site: 'Established in 1965, DCEA, Inc. is a Community Action Agency serving 30 counties in Tennessee and 2 counties in Kentucky.' General antip... |
| 8 | 752684716 | Kickapoo Springs Foundation | TX | $24.3M | `place_name_coincidence` | medium | IRS record: private grantmaking foundation, NTEE T50Z, Abilene TX, care-of John A. Matthews Jr., ruling 1998. Grants to Texas/DC education and comm... |
| 9 | 440418245 | Sac Osage Electric Cooperative Inc | MO | $24.1M | `place_name_coincidence` | medium | 990: 'Sac-Osage Electric Cooperative provides electric service to approximately 9,000 members...' Member-owned REC in El Dorado Springs (Cedar Coun... |
| 10 | 251797771 | Tuscarora Intermediate Unit Capital Insurance Trust | PA | $22.5M | `place_name_coincidence` | high | 990 mission: 'To provide health, medical, and vision Insurance coverage to employees of ten school districts in order to contain Insurance costs.' ... |
| 11 | 481253246 | Pawnee Valley Community Hospital Inc | KS | $21.5M | `place_name_coincidence` | high | Own site: critical access hospital at 923 Carroll Ave, Larned, Pawnee County KS; operates as part of HaysMed and the Northwest Kansas Alliance. No ... |
| 12 | 930937286 | Umatilla-Morrow County Head Start Inc | OR | $14.1M | `place_name_coincidence` | high | 990 mission is general early-childhood development; Head Start grantee for Umatilla and Morrow Counties OR, governed by a board plus an elected par... |
| 13 | 391773613 | College Of The Menominee Nation | WI | $13.9M | `tribally_controlled` | high | Own site: 'a tribal Land Grant college, chartered by the Menominee People', established 1993 and recognized by Congress in 1994; campuses in Keshen... |
| 14 | 810405434 | Rosebud Community Hospital Inc | MT | $11.4M | `place_name_coincidence` | high | Rosebud Health Care Center, 383 N 17th Ave, Forsyth MT, in Rosebud County; independent 501(c)(3) formed 1980; critical access hospital + long-term ... |
| 15 | 460215360 | Rosebud Electric Cooperative Inc | SD | $10.0M | `place_name_coincidence` | medium | Own site: 'Serving Gregory, Tripp, and Lyman Counties since 1945'; tenth largest REC in South Dakota; HQ 512 Rosebud Ave, Gregory SD. Member-owned;... |
| 16 | 812350661 | Legacy Traditional School-Peoria | AZ | $8.1M | `place_name_coincidence` | medium | IRS record: NTEE B29 charter school, HQ 3125 S Gilbert Rd, Chandler AZ. A campus of the Legacy Traditional Schools network located in Peoria, Arizo... |
| 17 | 731153337 | Ascension Living Via Christi Village Ponca City | MO | $7.2M | `place_name_coincidence` | medium | IRS record: NTEE P75Z senior continuing-care, care of Ascension Living, PO Box 45998 Saint Louis MO. Catholic senior-living facility located in Pon... |
| 18 | 822016290 | Society Of St Vincent De Paul Peoria Council | IL | $7.0M | `place_name_coincidence` | medium | IRS record: NTEE X20 Roman Catholic, PO Box 3073 Peoria IL. Catholic lay charitable council for the Diocese of Peoria, Illinois. No Native connection. |
| 19 | 161363413 | Onondaga Case Management Services Inc | NY | $6.9M | `place_name_coincidence` | medium | IRS record: NTEE P800 human services, 620 Erie Blvd W Ste 302, Syracuse NY. County-scope case-management provider named for Onondaga County; the On... |
| 20 | 222318303 | Onondaga Community College Foundation Inc | NY | $6.4M | `place_name_coincidence` | high | Fundraising foundation of Onondaga Community College, which its own site describes as part of SUNY and 'locally sponsored by Onondaga County', gove... |
| 21 | 150406690 | Onondaga Golf And Country Club | NY | $5.4M | `place_name_coincidence` | medium | IRS record: 501(c)(7) social club, NTEE N50, Marvelle Road, Fayetteville NY (Onondaga County). Private country club named for the county. No Native... |
| 22 | 237232985 | Yavapai College Foundation | AZ | $5.2M | `place_name_coincidence` | medium | IRS record: NTEE B12 fund-raising for a single institution, 1100 E Sheldon St, Prescott AZ. Foundation of Yavapai College, the public community col... |
| 23 | 300176646 | Onondaga Community College Housing Development Corp | NY | $4.7M | `place_name_coincidence` | high | Student-housing affiliate at the OCC campus address, 4585 W Seneca Tpke Syracuse NY. OCC's own site: part of SUNY, 'locally sponsored by Onondaga C... |
| 24 | 421301885 | St Lukes Health Foundation Of Sioux City Iowa | IA | $4.0M | `place_name_coincidence` | medium | IRS record: hospital foundation at 2720 Stone Park Blvd, Sioux City IA. Named for the city of Sioux City, Iowa. No Native control or Native-targete... |
| 25 | 161607731 | Akwesasne Boys & Girls Club St Regis Mohawk Tribe | NY | $2.8M | `native_controlled` | medium | Own site: serves youth 'from in and around the Akwesasne Mohawk territory' since 2001 across five clubhouses; 'the first Native American Club in Ne... |

### The five that carry 80% of the dollars

1. **Umatilla Electric Cooperative ($603.1M)** — `place_name_coincidence`. Member-owned co-op
   incorporated 1937, seven directors elected by member district, no tribal role stated anywhere on
   its own governance pages. Named for Umatilla County/River. The CTUIR is a separate government in
   the same county.
2. **Yavapai Community Hospital Association ($464.1M)** — `place_name_coincidence`. dba Dignity
   Health Yavapai Regional Medical Center; its 990 mission is to serve western Yavapai County;
   parent is CommonSpirit/Dignity Health.
3. **Lumbee River EMC ($158.2M)** — `place_name_coincidence`, and the row that most deserved the
   scrutiny. 501(c)(12) member-owned co-op incorporated 1940, named for the Lumbee/Lumber River. The
   decisive evidence is the **Lumbee Tribe's own press release**, which treats LREMC as an outside
   partner and donor ($40K gift, $200K committed over five years) — a tribal instrumentality does not
   donate to its own tribe. Board is district-elected by members, not tribe-appointed.
   **Flagged for Elijah:** the board and CEO carry the characteristic Lumbee surnames (Locklear,
   Oxendine, Chavis, Hammonds, Lowery, Goins). A `native_controlled` reading — majority-Native board,
   independent of the tribe — is plausible and I could not document it either way. Surname inference
   is not evidence, so the ruling stands at `place_name_coincidence`/medium. If any row in this file
   is worth a human second look, it is this one.
4. **Jemez Mountains Electric Cooperative ($56.4M)** — `place_name_coincidence`. Own site: member-
   owned utility founded 1948, 31,000 members across five NM counties, eleven trustees elected by
   the membership. Serves Pueblo communities but is not owned by them — service area is not control.
5. **Lumbee Land Development Inc ($50.5M)** — **`tribally_controlled`. PROMOTION.** Its 990
   governing body *is* the Lumbee Tribal Council (Chairman John L. Lowery, Council Speaker Sharon
   Hunt, Vice Chair Wendy Moore, Tribal Administrator Ricky Harris), and its IRS address is the
   Lumbee Tribe of North Carolina headquarters at 6984 NC Hwy 711, Pembroke. This is the tribe's
   housing and social-services delivery entity filing under its own EIN. The single largest
   promotion by revenue.

## Promotions found

89 of 375 rows (24%) are genuine Native organisations that the place-name filter had swept up.

### Tribally controlled (11)

| EIN | Organisation | ST | Revenue | Conf |
|---|---|---|---:|---|
| 562259380 | Lumbee Land Development Inc | NC | $50.5M | high |
| 391773613 | College Of The Menominee Nation | WI | $13.9M | high |
| 720742264 | United Houma Nation Inc | LA | $1.4M | high |
| 680443662 | Klamath River Inter-Tribal Fish And Water Commission | OR | $613K | high |
| 562247884 | Lumbee Nation Tribal Programs Inc | NC | $140K | high |
| 932143915 | Boys And Girls Club Of The Kickapoo Tribe | KS | no revenue on file | medium |
| 480941796 | Kickapoo Nation School | KS | no revenue on file | high |
| 731018494 | Kickapoo Tribe Of Oklahoma | OK | no revenue on file | high |
| 222365230 | Seneca Nation Library | NY | no revenue on file | medium |
| 161448788 | Seneca Nation Of Indians Economic Development Company | NY | no revenue on file | high |
| 320671686 | Winnebago Tribe Of Nebraska | NE | no revenue on file | high |

The four flagged in advance as likely promotions all confirmed:

- **College of the Menominee Nation ($13.9M)** — `tribally_controlled`, high. Own site: "a tribal
  Land Grant college, chartered by the Menominee People," established 1993, congressionally
  recognised 1994, campus in Keshena on the reservation.
- **Akwesasne Boys & Girls Club, St Regis Mohawk Tribe ($2.8M)** — `native_controlled`, medium.
  Own site: serves youth "from in and around the Akwesasne Mohawk territory," five clubhouses,
  "the first Native American Club in New York State," operating inside the Akwesasne Mohawk Board
  of Education and St Regis Mohawk schools. Coded `native_controlled` rather than
  `tribally_controlled` because its 990 shows its own Akwesasne board, not the tribal council.
- **Lumbee Regional Development Association ($1.9M)** — `native_controlled`, high. Own site: "LRDA
  was created to provide services for the Lumbee Indian communities," and "The Board of Directors
  for many years served as the governing body of the Lumbee Tribe of North Carolina."
- **United Houma Nation Inc ($1.4M)** — `tribally_controlled`, high. Own site: a state-recognised
  tribe of ~19,000 members across six Louisiana parishes. The filer is the tribal government.

A fifth large promotion was not on the advance list: **Lumbee Land Development Inc ($50.5M)**,
above. And **Klamath River Inter-Tribal Fish and Water Commission ($613K)** is a clean intertribal
instrumentality — "designated Representatives of the Hoopa Valley, Karuk, Klamath and Yurok Tribes."

### Native controlled (71)

The bulk of this class is the long tail of state-recognised tribes, unrecognised bands and
petitioning groups, Native heritage/community associations, and Native-member membership bodies
(Indian veterans organisations, tribal community organisations). These are Native-controlled
regardless of federal recognition status; recognition status is recorded per row in the note.

| EIN | Organisation | ST | Revenue | Conf |
|---|---|---|---:|---|
| 161607731 | Akwesasne Boys & Girls Club St Regis Mohawk Tribe | NY | $2.8M | medium |
| 560943997 | Lumbee Regional Developement Association Inc | NC | $1.9M | high |
| 161002392 | Mohawk Indian Housing Corporation | NY | $533K | medium |
| 460451277 | Oglala Sioux Tribe Partnership For Housing Inc | SD | $276K | medium |
| 810659126 | Tuscarora Nation Of Indians Of The Carolinas | NC | $224K | medium |
| 382419477 | Burt Lake Band Of Ottawa And Chippewa Indians Inc | MI | $142K | high |
| 561735439 | Tuscarora Nation Of North Carolina Inc | NC | $134K | medium |
| 882853731 | Kansas Cherokee Community Organization Inc | OK | $84K | low |
| 570791346 | Paia Lower Eastern Cherokee Nation | SC | $77K | high |
| 261472753 | Yavapai Indian Foundation | AZ | $53K | medium |
| 431618356 | Northern Cherokee Nation | MO | $41K | medium |
| 272616666 | Colorado Cherokee Circle | CO | $37K | high |
| 631142216 | Echota Cherokee Tribe Of Alabama Inc | AL | $36K | high |
| 630849027 | Cherokee Tribe Of Northeast Alabama | AL | $25K | medium |
| 371423274 | Lumbee Community Development Corporation Inc | NC | $20K | medium |
| 043589019 | Western Cherokee | AR | $16K | medium |
| 050559524 | Georgia Tribe Of Eastern Cherokee Inc | GA | $11K | medium |
| 432089919 | Lumbee Warriors Association | NC | $7K | medium |
| 871919155 | Lumbee Community Development Outreach | NC | $2K | low |
| 731014291 | Cheyenne Cultural Center Inc | OK | -- | high |
| 860928837 | Navajo Language Academy Inc | AZ | -- | medium |
| 990811928 | Siletz Regalia Sharing Co-Op | OR | no revenue on file | medium |
| 731726455 | Washington County Cherokee Association | OK | no revenue on file | medium |
| 541923783 | Appalachian Cherokee Nation Inc | SC | no revenue on file | medium |
| 621814973 | Central Band Of Cherokee | TN | no revenue on file | medium |
| 452122878 | Central Texas Cherokee Township | TX | no revenue on file | high |
| 921118435 | Cherokee Nation At-Large Mutual Assistance Incorporated | OK | no revenue on file | high |
| 921134356 | Cherokee Nation Cemeteries Association | OK | no revenue on file | low |
| 731497804 | Cherokee Nation Education Corporation | OK | no revenue on file | medium |
| 300162438 | Cherokee Nation Of Sequoyah In Mex Tx & Us Reservation & Church | TX | no revenue on file | medium |
| 933416427 | Cherokee Of Arkansas And Missouri Tribe | NE | no revenue on file | low |
| 621835798 | Cherokee Wolf Clan Native American Church | TN | no revenue on file | low |
| 582328510 | Eastern Cherokee Southern Iroquois And United Tribes Of South Carolin | SC | no revenue on file | medium |
| 824591056 | Echota Cherokee Tribe Of Texas Inc | TX | no revenue on file | low |
| 263650885 | Florida Tribe Of Cherokee Indians | FL | no revenue on file | low |
| 721295150 | Four Winds Tribe Louisiana Cherokee | LA | no revenue on file | high |
| 843544935 | Georgia Cherokee Community Alliance | GA | no revenue on file | high |
| 871855423 | Georgia Tribe Of Eastern Cherokee Foundation | GA | no revenue on file | medium |
| 883700972 | Indian Creek Tribe Chickamauga Creek And Cherokee Nation Inc | VA | no revenue on file | low |
| 273058626 | Kansas City Cherokee Community | MO | no revenue on file | high |
| 331846891 | Kiowa Comanche Apache Indian Veterans Organization | OK | no revenue on file | medium |
| 394121012 | Kiowa Tribal Princess Sorority Inc | OK | no revenue on file | medium |
| 731114159 | Kiowa Veterans Organization | OK | no revenue on file | medium |
| 943152365 | Klamath-Modoc Yahooskin Band Of Snake Indians Development Inc | OR | no revenue on file | low |
| 882008513 | Lower Illinois Cherokee Connection | OK | no revenue on file | low |
| 831054092 | Lumbee Nations Inc | NC | no revenue on file | medium |
| 383460087 | Mackinac Bands Of Chippewa And Ottawa Indians Inc | MI | no revenue on file | medium |
| 331865120 | Menominee Nation Youth Athletics Corporation | WI | no revenue on file | medium |
| 133844128 | North Eastern Band Of Cherokee | NY | no revenue on file | low |
| 844788368 | North Tulsa Cherokee Community Organization | OK | no revenue on file | medium |
| 922364475 | Old Saline Cherokee Association | OK | no revenue on file | high |
| 275339170 | Ouachita Cherokee Of Cherokee Nation West Benevolent Services | AR | no revenue on file | medium |
| 431594614 | Sac River And White River Bands Of The Chichamauga Cherokee Nation Of | MO | no revenue on file | medium |
| 113806131 | San Diego Cherokee Community Inc | CA | no revenue on file | low |
| 352515575 | Sjarure Katehnuaka Tuscarora Nation | NC | no revenue on file | medium |
| 383902520 | Southern Cherokee Cultural Center | MO | no revenue on file | low |
| 833159108 | Southern Cherokee Helpers | OK | no revenue on file | low |
| 993945974 | Sovereign Chickamauga Cherokee Tribe Inc | AR | no revenue on file | low |
| 561427255 | The Tuscarora Tribe Of North Carolina Inc | NC | no revenue on file | medium |
| 922617394 | Tuscarora Band Of Six Nations Indians | NC | no revenue on file | medium |
| 393246263 | Tuscarora Council Of The Great | NC | no revenue on file | medium |
| 874031049 | Tuscarora Indian Nation Of North Carolina Prospect Longhouse | NC | no revenue on file | medium |
| 831510507 | Tuscarora Tribal Judiciary | NC | no revenue on file | medium |
| 883977790 | United Cherokee Alliance | OK | no revenue on file | low |
| 631211252 | United Cherokee Aniyunwiya Nation | AL | no revenue on file | high |
| 541916852 | United Cherokee Indian Tribe Of Virginia Inc | VA | no revenue on file | medium |
| 942590599 | United Lumbee Nation Of N C & America Inc | CA | no revenue on file | medium |
| 372054196 | Western Cherokee Nation Inc | MO | no revenue on file | medium |
| 262327623 | Western United Cherokee Nfp | IL | no revenue on file | low |
| 932284761 | Wolf Creek Cherokee Tribe Of Virginia | VA | no revenue on file | low |
| 481156633 | Wyandotte Nation Of Kansas | KS | no revenue on file | medium |

### Native serving (7)

Mission targets Native people; control not established. Mostly denominational missions and
churches serving Native communities, plus one grantmaker.

| EIN | Organisation | ST | Revenue | Conf |
|---|---|---|---:|---|
| 113756317 | Osage Nation Foundation | TX | $697K | medium |
| 731472496 | Kickapoo Friends Center | OK | no revenue on file | medium |
| 561951219 | Lumbee River Christian College | NC | no revenue on file | medium |
| 541103251 | Pamunkey Indian Baptist Church | VA | no revenue on file | medium |
| 731087829 | Rainy Mountain Kiowa Indian Baptist Church | OK | no revenue on file | medium |
| 166073527 | Tuscarora Indian Mission | NY | no revenue on file | medium |
| 226500878 | Leonard D Hubbard Onondaga Nation Scholarship Trust | NY | -- | medium |

## Left unresolved, and why

Four rows. Combined revenue **$11K** — nothing material rides on them.

- **Sioux Nation Leathernecks Mc (EIN 462070912, SD, $10K)** — ProPublica and CauseIQ show only a small Harrisburg SD veterans-support fundraising group ('raffles and swap meets... toiletries, socks' for VA hospital patients); no retrievable evidence of Native control, Native-targeted mission, or a place-name origin.
- **Lumbee River Productions Inc (EIN 811658622, GA, $1K)** — CauseIQ/ProPublica show only a dormant film-and-video 501(c)(3) in Loganville GA, president David Bryan Crespo, ~$700 lifetime revenue, with no mission statement. No retrievable evidence of Native control, Native-focused mission, or place-name origin.
- **Little Shell Pembina Chippewa Band Of North Dakota (EIN 301280950, ND, no revenue on file)** — Wikipedia describes the similarly named ND Little Shell Pembina Band of North America as a sovereign citizens group of mostly white militia members, unrecognized federally and by ND. Cannot confirm the Crary ND filer is that entity.
- **Yavapai Regional Shelter & Resource Empowerment Center Inc (EIN 822166026, AZ, no revenue on file)** — Only the IRS record was retrievable (Phoenix AZ; NTEE P20 human services; ruling 2018). Phoenix is outside Yavapai County; could not determine whether 'Yavapai' means the county or the Yavapai people. Search sources unavailable.

The Little Shell Pembina row is the important one: a similarly named North Dakota group is
described in public sources as a sovereign-citizens organisation rather than a Native band, and the
filer could not be confirmed to be either. Ruling `native_controlled` on the name alone would have
been exactly the error this queue exists to catch.

## Traps caught (rows that read Native but are not)

These are worth preserving as rulebook entries — they generalise beyond this queue:

- **Northeast Comanche Tribe (PA)** and **Northwest Comanche Tribe Inc (WA)** — chapters of the
  International Comanche Society, a club for **Piper Comanche aircraft owners**. ICS calls its
  regional chapters "tribes" and their officers "Tribe Chief."
- **Golden Comanche Indian Tribe (LA)** — a New Orleans Mardi Gras Indian / Black Masking Indian
  krewe. An African American Carnival tradition, not a Native tribe.
- **Sioux Tribe 128 Charity Fund (OH)** — a lodge of the Improved Order of Red Men, a fraternal
  order that calls its local units "tribes."
- **Seneca Valley Raider Nation Football Boosters (PA)** — "Raider Nation" is the school fan name.
- **Umatilla Band Boosters (FL)** — marching-band boosters in Umatilla, Florida.
- **Samish Co-op Preschool (WA)** — a Sedro-Woolley parent cooperative, not the Samish Indian Nation.
- **Yavapai AZ Chapter (AZ)** — a Harley Owners Group chapter.
- **Greater Marysville Tulalip Chamber of Commerce (WA)** — offices sit in Quil Ceda Village on
  Tulalip land, but it is a general 501(c)(6) regional business chamber, exempt since 1953.
- **Pawnee Community Chamber of Commerce (OK)** — the town chamber in the Pawnee Nation's seat, but
  the town's general business chamber with no tribal control shown.
- **Klamath Family Head Start (OR)** — an independent county Head Start grantee serving Klamath and
  Lake counties, not a Klamath Tribes program.

Note on the three "not a place name, but also not Native" cases (the two aircraft-society chapters
and the Mardi Gras krewe): they were filed as `place_name_coincidence` because that is the
taxonomy's only "no Native connection" bucket. If a `name_coincidence_non_place` value is ever
added, those are the rows to recode.

## Method and evidence standard

Zero fabrication. Every non-`unresolved` row carries an evidence URL that was actually retrieved,
plus a quote or close paraphrase in the note. No URL means `unresolved` — the merge script enforces
this and would have demoted any row that arrived without one.

Signal order applied per organisation: (1) the org's own self-description as tribal, tribally
chartered, or a tribal instrumentality; (2) board composition or appointment by a tribe; (3) mission
explicitly targeting Native populations; (4) nothing Native beyond a place name in the title.

Two rules were applied throughout and are worth restating because they did real work:

- Native control was never inferred from a tribe-named place.
- Native control was never inferred from a reservation service area alone — that is `native_serving`
  at most. This is what kept Jemez Mountains Electric and Lumbee River EMC out of tier A.

The IRC 7871 caveat was honoured: filing status never drove a ruling. Lumbee Land Development and
Lumbee Nation Tribal Programs both look odd in IRS data (a tribal council as the 990 governing body)
and both are real tribal entities.

### Sources used

- Organisations' own websites (about / mission / governance / board pages) — the strongest evidence,
  used wherever a site existed.
- ProPublica Nonprofit Explorer: the API (`/api/v2/organizations/<EIN>.json`) for the IRS record
  (legal name, DBA, address, NTEE, subsection, revenue) and the **HTML org page**, which lists
  officers and their titles. The HTML page was decisive on several rows — it is what showed the
  Lumbee Tribal Council sitting as the governing body of two filers.
- CauseIQ org pages (`causeiq.com/organizations/<slug>,<ein>/`), which surface the 990 mission and
  program text the ProPublica API omits.
- Tribal government websites (lumbeetribe.com, srmt-nsn.gov, unitedhoumanation.org) for the
  relationship from the tribe's side.
- Wikipedia's state-recognised-tribes and self-identifying-tribes lists for recognition status only.

### Caveats on this pass

1. **40 rows cite a search-results page as the evidence URL** rather than an underlying source. The
   quoted snippets in those notes are real and were retrieved, but the citation is weaker than a
   primary page. All 40 are below $500K and 30 of them carry no revenue at all. Listed in the run log.
2. **24 rows are `low` confidence** — name, NTEE code and location inference only, with board control
   not independently verified. None is above $10M; the rule that low confidence over $10M becomes
   `unresolved` was enforced in the merge and fired zero times.
3. Revenue figures are as supplied in the queue. Several disagree with the current ProPublica
   record (e.g. Lumbee Land Development shows $38.2M in FY2024 against the queue's $50.5M, Klamath
   Family Head Start shows $10.4M against a blank). Filing lag, not error — but do not quote queue
   revenue as current.
4. `native_controlled` for state-recognised and unrecognised groups is a control ruling, not a
   recognition ruling. Recognition status is in each row's note and should stay visible downstream.

## Files

- Input: `review/agent_research_queue_2026-08-05.csv` (375 rows)
- Output: `review/rulings_inbox_2026-08-05_agent_nonprofit.csv` (375 rows, rulings-inbox columns)
- Run log: `logs/38_nonprofit_classification.log`

Nothing under `data/spine/`, `data/clean/cedar_*` or `review/cedar_review*.html` was touched.
