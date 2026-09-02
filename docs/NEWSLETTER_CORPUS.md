# The tribal newsletter corpus

*Generated 2026-09-02 by `code/995_write_newsletter_docs.py`. Every number here is read out of the tables at write time - none of it is typed.*

Owner, twice: *"Don't forget tribal newsletters, especially for deals"* and *"even just keeping track of your newsletters could be a potential different dataset down the road."* This is both halves: a catalogue of what Indian Country publishes, and the deal-extraction route that runs off it.

## What it is

| | |
|---|---:|
| publication channels catalogued | 888 |
| entities publishing at least one | 546 |
| named publications (a masthead, not just a news page) | 160 |
| archives spanning 10 years or more | 94 |
| deepest single archive | 56 years (Assiniboine and Sioux) |
| spine entities in the coverage denominator | 1555 |

Grain is **(entity, channel URL)**. A nation that prints a newspaper, posts PDFs to a WordPress media library and files shareholder reports with the State of Alaska has three rows, because those are three channels with three different archive depths.

## Coverage, by entity class

`found`, `attempted, none found` and `not probed` are three different claims and the table keeps them apart. A `not probed` row is `NOT_SEARCHED_MACHINE_READABLE`, which is not an absence.

| entity class | in spine | found | attempted, none found | not probed | found rate of those probed |
|---|---:|---:|---:|---:|---:|
| Federally recognized tribe | 349 | 160 | 0 | 182 | 100% |
| Federally recognized Alaska Native Village | 228 | 100 | 0 | 128 | 100% |
| Native Hawaiian Organization | 210 | 7 | 82 | 121 | 8% |
| BIE School | 185 | 0 | 0 | 185 | n/a |
| Alaska Native Village Corporation | 173 | 54 | 119 | 0 | 31% |
| State-recognized tribe | 64 | 8 | 32 | 24 | 20% |
| Native Community Development Financial Institution | 64 | 47 | 13 | 4 | 78% |
| Intertribal Organization | 56 | 43 | 6 | 7 | 88% |
| Individually Native-owned business | 45 | 0 | 12 | 33 | 0% |
| Urban Indian Organization | 43 | 34 | 9 | 0 | 79% |
| Tribal College or University | 37 | 31 | 6 | 0 | 84% |
| Federal-level self-governance consortium | 29 | 22 | 6 | 1 | 79% |
| Native Financial Institution | 29 | 18 | 8 | 3 | 69% |
| Federal-level constituency entity | 22 | 11 | 10 | 1 | 52% |
| Alaska Native Regional Corporation | 12 | 11 | 0 | 0 | 100% |
| ANCSA Group Corporation | 6 | 0 | 6 | 0 | 0% |
| State-level constituency entity | 3 | 0 | 2 | 1 | 0% |
| **all** | **1555** | **546** | **311** | **690** | **64%** |

## The deepest back runs

Archive depth is the span of years the channel's own index or media library exposes. It is a floor, not a ceiling: a paper printing since 1966 whose site only indexes 2002 onward shows as 2002.

| publisher | publication | years | channel |
|---|---|---|---|
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
| Sault Ste. Marie | Press Releases - The Sault Tribe of Chippewa | 2010-2026 | [link](https://www.saulttribe.com/newsroom/press-releases) |

## How they were found

| route | channels |
|---|---:|
| shard F org web probe | 193 |
| cedar_web_map | 130 |
| shard I nonprofit probe | 126 |
| shard E ANC probe | 85 |
| rendered page + hidden-endpoint sweep | 75 |
| shard D web probe | 66 |
| Alaska DBS STAR portal | 58 |
| HIDDEN_DATA_TECHNIQUES #3 WordPress REST API | 47 |
| rendered homepage links - fallback, nothing richer was exposed | 23 |
| rendered page link | 22 |
| hand-verified tribal newspaper | 22 |
| HIDDEN_DATA_TECHNIQUES #13 feeds | 17 |
| HIDDEN_DATA_TECHNIQUES #13 feeds, discovered from <link rel=alternate> | 9 |
| sitemap_xml; json_ld | 5 |

### The gap sweep: what search alone had missed

`code/991_newsletter_gap_sweep.py` re-ran the machine-readable routes against entities no prior probe had touched. It is the direct test of the project's own rule that a negative from search alone is not a negative.

| | |
|---|---:|
| entities in scope | 233 |
| attempted | 10 |
| **newsletter channel found where none was known** | **3** |
| absence confirmed across every route run | 7 |
| hosts quarantined for serving one body to many URLs | 0 |
| total requests | 52 |

| technique that produced the finding | count |
|---|---:|
| rendered homepage link (last resort) | 2 |
| HIDDEN_DATA #4 sitemap (nested) (articles collapsed to the channel pat | 1 |

Skipped, with the reason recorded rather than silently dropped: 201 no_live_site; 185 deliberately_out_of_scope; 71 site_url_is_a_wayback_snapshot.

## Deals out of the tribal press

Two extraction routes, one extractor. `992` fetches the issue and article URLs the corpus already indexes; `993` calls each WordPress host's `/wp-json/wp/v2/posts?search=` for full article bodies. `994` applies the precision screen and writes the merge proposal.

| | |
|---|---:|
| documents fetched (issue route) | 30 |
| documents with extractable text | 20 |
| distinct document hashes | 20 |
| repeated-body fetches refused | 0 |
| hosts probed (WordPress posts route) | 12 |
| of those with the REST posts API open | 6 (50%) |
| articles read | 3 |
| hosts caught ignoring `?search=` | 0 |
| sentences dropped by the private-life screen | 0 |

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

