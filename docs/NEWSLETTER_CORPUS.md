# The tribal newsletter corpus

*Generated 2026-09-02 by `code/995_write_newsletter_docs.py`. Every number here is read out of the tables at write time - none of it is typed.*

Owner, twice: *"Don't forget tribal newsletters, especially for deals"* and *"even just keeping track of your newsletters could be a potential different dataset down the road."* This is both halves: a catalogue of what Indian Country publishes, and the deal-extraction route that runs off it.

## What it is

| | |
|---|---:|
| publication channels catalogued | 1394 |
| rows in the corpus file | 1889 |
| entities publishing at least one | 694 |
| named publications (a masthead, not just a news page) | 286 |
| archives spanning 10 years or more | 140 |
| deepest single archive | 57 years (United Keetoowah Band of Cherokee Indians in Oklahoma) |
| spine entities in the coverage denominator | 1555 |

**Filter `record_status` before you count anything.** The file holds 1889 rows and 1394 publication channels: 1394 `publication_channel`, 481 `probe_absence`, 13 `flagged_not_native_publisher`, 1 `contact_point_only`. A recorded absence keeps a row on purpose, so the negative sits beside the positives and `discovery_technique` can name which routes ran. Counting rows instead of filtering the column overstates the channel count by 36%.

Grain is **(entity, channel URL)**. A nation that prints a newspaper, posts PDFs to a WordPress media library and files shareholder reports with the State of Alaska has three rows, because those are three channels with three different archive depths.

## Coverage, by entity class

`found`, `attempted, none found` and `not probed` are three different claims and the table keeps them apart. A `not probed` row is `NOT_SEARCHED_MACHINE_READABLE`, which is not an absence.

| entity class | in spine | found | attempted, none found | not probed | found rate of those probed |
|---|---:|---:|---:|---:|---:|
| Federally recognized tribe | 349 | 264 | 70 | 8 | 79% |
| Federally recognized Alaska Native Village | 228 | 130 | 53 | 45 | 71% |
| Native Hawaiian Organization | 210 | 11 | 102 | 97 | 10% |
| BIE School | 185 | 0 | 0 | 183 | n/a |
| Alaska Native Village Corporation | 173 | 54 | 119 | 0 | 31% |
| State-recognized tribe | 64 | 17 | 45 | 2 | 27% |
| Native Community Development Financial Institution | 64 | 47 | 13 | 4 | 78% |
| Intertribal Organization | 56 | 43 | 10 | 3 | 81% |
| Individually Native-owned business | 45 | 1 | 15 | 29 | 6% |
| Urban Indian Organization | 43 | 34 | 9 | 0 | 79% |
| Tribal College or University | 37 | 31 | 6 | 0 | 84% |
| Federal-level self-governance consortium | 29 | 22 | 7 | 0 | 76% |
| Native Financial Institution | 29 | 18 | 11 | 0 | 62% |
| Federal-level constituency entity | 22 | 11 | 11 | 0 | 50% |
| Alaska Native Regional Corporation | 12 | 11 | 0 | 0 | 100% |
| ANCSA Group Corporation | 6 | 0 | 6 | 0 | 0% |
| State-level constituency entity | 3 | 0 | 3 | 0 | 0% |
| **all** | **1555** | **694** | **480** | **371** | **59%** |

## Read the coverage table with `site_url_class`, or you will read it wrong

A single-digit found rate in the table above is not Cedar failing to look. `has_live_site` answers a narrower question than it appears to: it is `yes` whenever the web map holds ANY reachable URL for the entity, and for a large share of some classes that URL is a Wayback capture of a dead site, an IRS-derived profile page, or - found 2026-09-02 - a **federal ArcGIS API endpoint that returns data about the entity**, which the web map had recorded as 45 Alaska Native Villages' website. None of those can be probed for a newsletter. `site_url_class` states which it is, per row.

**The honest denominator is entities that operate their own site.** Against it, the picture changes:

| entity class | in spine | operates own site | found ON that site | found rate on its own site | found ANYWHERE | no site of any kind |
|---|---:|---:|---:|---:|---:|---:|
| Federally recognized tribe | 349 | 328 | 257 | 78% | 264 | 21 |
| Federally recognized Alaska Native Village | 228 | 107 | 91 | 85% | 130 | 121 |
| Native Hawaiian Organization | 210 | 102 | 11 | 11% | 11 | 108 |
| BIE School | 185 | 176 | 0 | 0% | 0 | 9 |
| Alaska Native Village Corporation | 173 | 38 | 33 | 87% | 54 | 135 |
| State-recognized tribe | 64 | 58 | 16 | 28% | 17 | 6 |
| Native Community Development Financial Institution | 64 | 60 | 47 | 78% | 47 | 4 |
| Intertribal Organization | 56 | 10 | 10 | 100% | 43 | 46 |
| Individually Native-owned business | 45 | 15 | 1 | 7% | 1 | 30 |
| Urban Indian Organization | 43 | 11 | 11 | 100% | 34 | 32 |
| Tribal College or University | 37 | 36 | 30 | 83% | 31 | 1 |
| Federal-level self-governance consortium | 29 | 10 | 9 | 90% | 22 | 19 |
| Native Financial Institution | 29 | 28 | 17 | 61% | 18 | 1 |
| Federal-level constituency entity | 22 | 16 | 10 | 62% | 11 | 6 |
| Alaska Native Regional Corporation | 12 | 12 | 11 | 92% | 11 | 0 |
| ANCSA Group Corporation | 6 | 0 | 0 | n/a | 0 | 6 |
| State-level constituency entity | 3 | 1 | 0 | 0% | 0 | 2 |

**`found ANYWHERE` exceeding `found ON that site` is a finding, not an arithmetic error.** It counts entities whose only publication channel lives on someone else's host: a village corporation's statutory filing on the State of Alaska's portal, or a village government's news carried in its regional consortium's newsletter. Those rows say so - `served_tribe_id` names the nation served when the publisher is not it.

Three findings this makes visible, each of which reads as a Cedar gap on the first table and is a fact about the world on this one:

* **Native Hawaiian Organizations: 108 of 210 have no website at all.** Of the 102 that do, every one has now been probed on every machine-readable route and 11 publish. The class rate is 5%; the rate among NHOs with a site is 11%. `SOURCE_DOES_NOT_PUBLISH` is the honest state (`docs/AGENT_FIELD_GUIDE.md` section 5), and it is a finding about how this sector is organised - many NHOs are small homestead associations and civic clubs whose public presence is a Facebook page or an IRS filing - not a backlog.
* **Village corporations look like a 31% class and are a 87% class.** Only 38 of 173 operate a website - but 54 publish, because 21 of them were found through the **State of Alaska DBS STAR portal**, where ANCSA corporations file shareholder communications by statute. A corporation with no website still has a statutory publication channel, and the channel is on the state's host, not theirs.
* **The probeable frontier is closed.** 371 entities remain `not_probed`: 183 are BIE schools, excluded on purpose, and the other 188 have no site to probe. There is no entity left that operates a live site, is in scope, and has never been looked at - and that is not a claim, it is invariant 10 in `990_build_newsletter_corpus.py`, which fails the build if it stops being true.

## The deepest back runs

Archive depth is the span of years the channel's own index or media library exposes. It is a floor, not a ceiling: a paper printing since 1966 whose site only indexes 2002 onward shows as 2002.

| publisher | publication | years | channel |
|---|---|---|---|
| United Keetoowah Band of Cherokee Indi | Giduwa News | 1970-2026 | [link](https://www.ukb-nsn.gov/giduwa-cherokee-news) |
| Assiniboine and Sioux | JES Online Resources / Fort Peck Community C | 1970-2025 | [link](https://www.fpcc.edu/community/online-resources) |
| Colorado River | Colorado River Indian Tribes | 1980-2026 | [link](https://crit-nsn.gov/) |
| Confederated Salish | Confederated Salish & Kootenai Tribes | 1980-2026 | [link](https://cskt.org/) |
| Ak Chin | Official Website of the Ak-Chin Indian Commu | 1987-2025 | [link](https://ak-chin.nsn.us/) |
| Cherokee Nation | cherokeephoenix.org | 2000-2027 | [link](https://www.cherokeephoenix.org/) |
| Saginaw Chippewa | Tribal Observer Tribal Observer | 1999-2026 | [link](https://www.sagchip.org/tribalobserver/) |
| Saginaw Chippewa | Tribal Observer Tribal Observer | 1999-2026 | [link](https://www.sagchip.org/tribalobserver/archive_current.aspx) |
| Confederated Salish | charkoosta.com / The Official News Publicati | 2000-2026 | [link](https://www.charkoosta.com/) |
| Eastern Cherokee | The Cherokee One Feather | 2002-2026 | [link](https://theonefeather.com/) |
| Muckleshoot | Muckleshoot Messenger | 2003-2026 | [link](https://www.muckleshoot.nsn.us/messenger) |
| Keweenaw | KBIC Newsletter | 2004-2026 | [link](https://www.kbic-nsn.gov/newsletter/) |
| Leech Lake | DeBahJiMon Newspaper | 2003-2025 | [link](https://www.llojibwe.org/news/news.html) |
| Bristol Bay Native Association | Newsletters | 2000-2021 | [link](https://bbna.com/reports/newsletters/) |
| Native Americans in Philanthropy | Partner News The cornerstone of our work is  | 2006-2026 | [link](https://nativephilanthropy.org/partner-news) |
| Pascua Yaqui | Yaqui Times - Pascua Yaqui Tribe | 2006-2026 | [link](https://www.pascuayaqui-nsn.gov/yaqui-times/) |
| Kawerak Incorporated | Latest News | 2007-2026 | [link](http://kawerak.org/news/) |
| Pueblo of Isleta | Pueblo of Isleta Newsletter | 2007-2026 | [link](https://www.isletapueblo.com/newsletters/) |
| The Osage Nation | Newsletters / Osage Nation | 2007-2025 | [link](https://www.osagenation-nsn.gov/who-we-are/minerals-council/newsletters) |
| Hualapai | Gam'Yu Newsletter | 2009-2026 | [link](https://hualapai-nsn.gov/community/gamyu_newsletter.php) |
| Pawnee Nation of Oklahoma | Chaticks si Chaticks / Pawnee Nation of Okla | 2009-2026 | [link](https://pawneenation.org/chaticks-si-chaticks/) |
| Absentee-Shawnee | Newsletters / Absentee Shawnee Tribe | 2010-2026 | [link](https://www.astribe.com/newsletters) |
| Cowlitz | Publications / The Cowlitz Indian Tribe | 2010-2026 | [link](https://www.cowlitz.org/publications) |
| Quapaw Nation | News Flash &#x2022; Quapaw Tribe, OK | 2011-2027 | [link](https://www.quapawnation.com/m/newsflash?cat=1) |
| Sault Ste. Marie | Win Awenen Nisitotung | 2010-2026 | [link](https://www.saulttribe.com/newsroom/sault-tribe-newspaper) |

## How they were found

| route | channels |
|---|---:|
| HIDDEN_DATA #3 wp-json media | 310 |
| shard F org web probe | 193 |
| cedar_web_map | 130 |
| shard I nonprofit probe | 126 |
| shard E ANC probe | 85 |
| HIDDEN_DATA #3 wp-json search | 79 |
| rendered page + hidden-endpoint sweep | 75 |
| shard D web probe | 66 |
| Alaska DBS STAR portal | 58 |
| rendered homepage link | 48 |
| HIDDEN_DATA #13 feeds | 48 |
| HIDDEN_DATA_TECHNIQUES #3 WordPress REST API | 47 |
| rendered homepage links - fallback, nothing richer was exposed | 23 |
| rendered page link | 22 |

### The gap sweep: what search alone had missed

`code/991_newsletter_gap_sweep.py` re-ran the machine-readable routes against entities no prior probe had touched. It is the direct test of the project's own rule that a negative from search alone is not a negative.

| | |
|---|---:|
| entities in scope | 5 |
| attempted | 317 |
| **newsletter channel found where none was known** | **148** |
| absence confirmed across every route run | 169 |
| hosts quarantined for serving one body to many URLs | 0 |
| total requests | 1516 |

| technique that produced the finding | count |
|---|---:|
| HIDDEN_DATA #3 wp-json media | 310 |
| HIDDEN_DATA #3 wp-json search | 79 |
| rendered homepage link (last resort) | 48 |
| HIDDEN_DATA #13 feeds | 48 |
| HIDDEN_DATA #4 sitemap | 16 |
| HIDDEN_DATA #4 sitemap (articles collapsed to the channel path) | 4 |
| HIDDEN_DATA #4 sitemap (nested) (articles collapsed to the channel pat | 1 |
| HIDDEN_DATA #3 wp-json search (articles collapsed to the channel path) | 1 |

Skipped, with the reason recorded rather than silently dropped: 183 deliberately_out_of_scope; 122 no_live_site; 45 site_url_is_a_third_party_api_endpoint; 21 site_url_is_a_wayback_snapshot.

## Deals out of the tribal press

Two extraction routes, one extractor. `992` fetches the issue and article URLs the corpus already indexes; `993` calls each WordPress host's `/wp-json/wp/v2/posts?search=` for full article bodies. `994` applies the precision screen and writes the merge proposal.

| | |
|---|---:|
| documents fetched (issue route) | 1077 |
| documents with extractable text | 994 |
| distinct document hashes | 1020 |
| repeated-body fetches refused | 2 |
| hosts probed (WordPress posts route) | 469 |
| of those with the REST posts API open | 285 (61%) |
| articles read | 1172 |
| hosts caught ignoring `?search=` | 8 |
| candidates extracted (generous pass) | 650 |
| rejected by the precision screen | 29 |
| needing a human read | 309 |
| corporate-parentage statements routed to the hub, not to deals | 26 |
| **promotable, duplicates removed** | **258** |
| of those carrying a stated value | 36 |
| of those carrying a date | 250 |
| sentences dropped by the private-life screen | 4 |

The proposal itself is `data/staging/deals_from_newsletters/MERGE_PROPOSAL.md`. Nothing has been written to `data/clean/deals_classified.csv`.

## What is deliberately not here

* **Private personal news.** A tribal newspaper carries obituaries, birthdays, funeral notices and family announcements about people who are not public figures. Cedar harvests the publication and records what it is; it does not extract a natural person's private news from it. The screen runs before anything is written, and the invariant is re-checked at every downstream stage.
* **Back issues.** Depth is measured from the index and the media library. Issues are downloaded only where a deal route needs the text, and never in bulk.
* **The eight `TERMS_STATED_RESTRICTIVE` publishers** - Confederated Colville, CTUIR/Umatilla, Yakama, Chickasaw, NANA/Akima, Southern Ute, Forest County Potawatomi and Stillaguamish - excluded by every route. Their newspapers are among the best in Indian Country (the *Tribal Tribune*, the *Confederated Umatilla Journal*, the *Southern Ute Drum*, the *Chickasaw Times*) and that is precisely why the exclusion is by HOST as well as by entity: those mastheads do not carry the nation's name and a name-only filter would have missed all four. **Asking is the route back in.**

## Rebuild

```
python code/990_build_newsletter_corpus.py            # no network
python code/991_newsletter_gap_sweep.py               # resumable
python code/992_newsletter_deal_candidates.py         # resumable
python code/993_newsletter_wp_posts_deals.py          # resumable
python code/994_screen_newsletter_deal_candidates.py  # no network
python code/995_write_newsletter_docs.py              # this file
```

Each takes `verify`, and `verify --selftest` proves each invariant fires on a synthetic violation before it is trusted on real data.

