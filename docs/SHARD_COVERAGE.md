# Shard coverage - the master list, and who has touched it

*Generated 2026-09-02 by `code/528_shard_consolidate.py`. Merged map: `data/staging/cedar_web_map.csv`. This file does NOT write to the spine - promoting a harvested website to `entity_website` is an assertion and goes through 510.*

## Shard status

| shard | slice | state | map rows | entities touched |
|---|---|---|---:|---:|
| `shard_a` | tribal governments, gaming slice 1 | RUNNING_OR_DONE | 219 | 71 |
| `shard_b` | tribal governments, gaming slice 2 | RUNNING_OR_DONE | 474 | 71 |
| `shard_c` | tribal governments, gaming slice 3 | RUNNING_OR_DONE | 533 | 71 |
| `shard_d` | tribal governments, gaming slice 4 + non-gaming | RUNNING_OR_DONE | 476 | 85 |
| `shard_e` | Alaska Native corporations (regional, group, village) | RUNNING_OR_DONE | 568 | 191 |
| `shard_f` | intertribal, urban Indian, consortia, constituency | RUNNING_OR_DONE | 683 | 153 |
| `shard_g` | BIE schools, tribal colleges, CDFIs, financial institutions | RUNNING_OR_DONE | 753 | 315 |
| `shard_h` | Native Hawaiian orgs, state-recognized tribes, individuals | RUNNING_OR_DONE | 315 | 242 |
| `shard_i` | Native nonprofits (np_orgs, not in register) | NOT_STARTED | 0 | 0 |
| `shard_k` | Alaska Native Village governments | RUNNING_OR_DONE | 1,201 | 228 |
| `shard_l` | vendor lists, unsurveyed federally recognized tribes, 1st half | NOT_STARTED | 0 | 0 |
| `shard_m` | vendor lists, unsurveyed federally recognized tribes, 2nd half | NOT_STARTED | 0 | 0 |
| `shard_n` | the coverage tail - every entity no other shard touched | RUNNING_OR_DONE | 212 | 139 |

## Coverage by entity class

*`untouched` is the number that matters. An entity nobody attempted looks the same as an entity with no web presence unless you keep them apart - and only one of those is a gap in our effort.*

| entity class | in register | with a URL | touched, none found | untouched |
|---|---:|---:|---:|---:|
| Federally recognized tribe | 349 | 325 | 24 | 0 |
| Federally recognized Alaska Native Village | 228 | 228 | 0 | 0 |
| Native Hawaiian Organization | 210 | 117 | 93 | 0 |
| BIE School | 185 | 183 | 2 | 0 |
| Alaska Native Village Corporation | 173 | 38 | 135 | 0 |
| Native Community Development Financial Institution | 64 | 61 | 3 | 0 |
| State-recognized tribe | 64 | 62 | 2 | 0 |
| Intertribal Organization | 56 | 49 | 7 | 0 |
| Individually Native-owned business | 45 | 18 | 27 | 0 |
| Urban Indian Organization | 43 | 43 | 0 | 0 |
| Tribal College or University | 37 | 37 | 0 | 0 |
| Native Financial Institution | 29 | 29 | 0 | 0 |
| Federal-level self-governance consortium | 29 | 28 | 1 | 0 |
| Federal-level constituency entity | 22 | 22 | 0 | 0 |
| Alaska Native Regional Corporation | 12 | 12 | 0 | 0 |
| ANCSA Group Corporation | 6 | 0 | 6 | 0 |
| State-level constituency entity | 3 | 2 | 1 | 0 |
| **total** | **1,555** | **1,254** | **301** | **0** |

## URL types harvested

| type | n |
|---|---:|
| government | 596 |
| newsletter | 545 |
| casino | 448 |
| corporate | 422 |
| institution | 419 |
| api_endpoint | 371 |
| organization | 320 |
| form_990 | 299 |
| tribal_council | 254 |
| regulator_record | 238 |
| consortium | 227 |
| press_release | 145 |
| tero | 106 |
| subsidiary_list | 101 |
| gaming_authority | 90 |
| annual_report | 71 |
| none_established | 69 |
| recognition_record | 64 |
| wp_media_pdf | 61 |
| failed_government | 51 |
| failed_casino | 48 |
| membership_list | 46 |
| machine_readable_surface | 46 |
| wp_types | 44 |
| policy_agenda | 44 |
| unverified_government | 42 |
| document_endpoint | 32 |
| failed_newsletter | 26 |
| no_own_site_found | 26 |
| business_licence | 25 |
| unverified_casino | 24 |
| sitemap | 20 |
| procurement | 20 |
| certification | 19 |
| shareholder | 17 |
| failed_gaming_authority | 10 |
| failed_tero | 8 |
| parked_domain | 7 |
| unverified_newsletter | 5 |
| directory_profile | 5 |
| unverified_tero | 4 |
| TERMS_RESTRICTED_DO_NOT_HARVEST | 4 |
| government_blocked_bot_protection | 4 |
| government_refused_robots | 3 |
| closed_property | 2 |
| government_candidate | 1 |
| placeholder_site | 1 |
| unverified_business_licence | 1 |
| DOMAIN_HIJACKED_DO_NOT_LINK | 1 |
| leadership | 1 |
| unverified_organization | 1 |
