# The coverage tail — shard N

*Generated 2026-09-02 by `code/1020_tail_web_probe.py`. Map: `data/staging/tribe_web_map/shard_n.csv`. STAGING — promoting any URL here to `entity_website` is an assertion and goes through 510.*

Shard N's slice is derived, not listed: every register entity that no other shard map has a row for. That set was **139** when this ran, and it is exactly the `untouched` column of `docs/SHARD_COVERAGE.md` — the column that says nobody tried.

## Four outcomes, and none of them is the others

| entity class | has a site of its own | site exists, we are refused or challenged | no site of its own; another party publishes about it | checked, no web presence located |
|---|---|---|---|---|
| Native Hawaiian Organization | 4 | 0 | 11 | 54 |
| Federally recognized tribe | 54 | 3 | 4 | 1 |
| Individually Native-owned business | 0 | 0 | 1 | 7 |
| **total** | **58** | **3** | **16** | **62** |

*`checked, no web presence located` is a FINDING. Every one of those entities carries a row naming the routes run and the date. For **64 of the 69** Native Hawaiian Organizations here, the route that settled it was the organisation's own entry in the DOI Office of Native Hawaiian Relations notification list, which records `Website: None listed`. That is the organisation telling its registrar it has none — not us failing to find one.*

## Rows by type

| url_type | n | meaning |
|---|---:|---|
| `none_established` | 60 | checked, nothing found at all |
| `government` | 54 | verified tribal government site |
| `machine_readable_surface` | 53 | the host answers wp-json / sitemap / feed — a harvestable surface for the next agent |
| `no_own_site_found` | 21 | checked; something was found but not a site of the entity's own |
| `form_990` | 16 | IRS filing record ABOUT the entity; not its website |
| `directory_profile` | 5 | a consortium or directory page about the entity, published in the BIA `website` field |
| `organization` | 4 | verified organisation site |
| `government_blocked_bot_protection` | 4 | site exists; 403 to research UA AND to browser headers |
| `parked_domain` | 2 |  |
| `government_refused_robots` | 1 | site exists; robots.txt Disallow: / — refused by every route |
| `unverified_organization` | 1 | URL published by DOI that did not answer |

## Reached but not harvestable — 19

*These are not coverage gaps and they are not absences. Filing either one as `none found` would misreport a nation's own decision, or an edge WAF, as an empty web presence.*

| entity | class | outcome | what was seen |
|---|---|---|---|
| Fort Bidwell | Federally recognized tribe | no site of its own; another party publishes about it | `directory_profile` https://caltribalfamilies.org/places/fort-bidwell-indian-community/ |
| Grindstone | Federally recognized tribe | no site of its own; another party publishes about it | `directory_profile` https://caltribalfamilies.org/places/grindstone-indian-rancheria/ |
| Guidiville | Federally recognized tribe | no site of its own; another party publishes about it | `directory_profile` https://caltribalfamilies.org/places/guidiville-rancheria/ |
| Inaja | Federally recognized tribe | no site of its own; another party publishes about it | `directory_profile` https://sctca.net/inaja-cosmit-band-of-indians/ |
| Koi | Federally recognized tribe | site exists, we are refused or challenged | `government_blocked_bot_protection` https://www.koinationsonoma.com/ |
| Paiute of Utah | Federally recognized tribe | site exists, we are refused or challenged | `government_blocked_bot_protection` https://pitu.gov/ |
| Potter Valley | Federally recognized tribe | site exists, we are refused or challenged | `government_blocked_bot_protection` https://pottervalleytribe.com/ |
| Cherokee Unlimited, Inc | Individually Native-owned business | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/630930547 |
| Ahonui Homestead Association | Native Hawaiian Organization | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/833506697 |
| Captain Kimo's Hawaiian Adventures | Native Hawaiian Organization | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/884330264 |
| Kalama‘ula Homesteaders Association | Native Hawaiian Organization | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/990285067 |
| Kauhakō Ohana Association | Native Hawaiian Organization | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/853839392 |
| Kupeke Ahupua‘a | Native Hawaiian Organization | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/850499990 |
| Maku‘u Farmers Association | Native Hawaiian Organization | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/990320097 |
| Malama Anahola | Native Hawaiian Organization | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/853075140 |
| Paukukalo Hawaiian Homes Community Association | Native Hawaiian Organization | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/990271231 |
| Pele Defense Fund | Native Hawaiian Organization | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/384045236 |
| Piihonua Hawaiian Homestead Community Association | Native Hawaiian Organization | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/453368519 |
| Royal Hawaiian Academy of Traditional Arts | Native Hawaiian Organization | no site of its own; another party publishes about it | `form_990` https://projects.propublica.org/nonprofits/organizations/990339530 |
