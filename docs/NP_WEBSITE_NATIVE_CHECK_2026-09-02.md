# Asking the nonprofit's own website — build log, 2026-09-02

*`code/1125_np_website_native_check.py`. Every figure below was re-derived from
the live files on 2026-09-02 by `1125 plan` / `1125 build`; nothing here is
quoted from another document. `1125 verify` exits 1 on breach and `1125
selftest` proves each of its seven checks fires on an injected violation.*

**The owner:** *"with the nonprofits, if they have a website, check the website
too."*

---

## Why this is the sharpest possible use of that instruction

`docs/CORROBORATION_LAYER_2026-09-02.md` P4 measured that **Cedar's nonprofit
Native-status claim has ZERO independent evidence families.**
`np_orgs.disposition = NATIVE_VERIFIED_STRICT` is a **name match over an IRS
BMF row**, and the IRS never asserts that an organisation is Native — it lists
a name, an address and an NTEE code. `n_coders_agree` reads like five sources;
four of them are reading the same BMF row and the fifth derives from SAM.

So the determination is `cedar_inference`, which does not vote, and until today
the only other observer available was the organisation's own Form 990
narrative. **An organisation's own website is the first genuinely independent
observer of the IRS side that this dataset can have.**

`START_HERE.md` item 0 lists `entity.website` from `org_self_statement` as a
**dead authority — declared authoritative, asserts 0 times.** This pass gives
it its first eleven assertions.

---

## The ladder — computed, never typed

Re-derived by `1125 plan`, written to
`data/staging/np_website_check/_ladder.json`, and re-checked by `verify` V6
against the live `np_orgs.csv` on every run:

```
12,764   rows in np_orgs.csv
   697   disposition = NATIVE_VERIFIED_STRICT
   293   ...with a Form 990 on THIS disk (data/staging/np_mission/inclusion_basis.jsonl)
   214   ...whose own 990 gives NO Native signal (inclusion_basis = placename_only)
    28   ...and whose Cedar link ALSO crosses a state line
```

The corroboration layer's `OWN_990_SILENT_AND_THE_LINK_CROSSES_A_STATE_LINE`
verdict counts **29**, not 28. Both are right: 1118 runs that test over three
dispositions (`NATIVE_VERIFIED_STRICT`, `NATIVE_RULED_VERIFIED`,
`NATIVE_PROPOSED_AWAITING_OWNER_RULING`) and this pass's population is the
first of them alone. The 29th row is a Native claim of a different disposition.
Say which population, every time.

The 293 break down as `placename_only` 214 · `subject_classification` 24 ·
`named_entity` 22 · `no_mission_text` 22 · `geographic` 7 ·
`program_authority` 4.

---

## Where the URLs came from, and the one route that was refused

**No domain was guessed.** A guessed domain that returns 200 is fabrication
with a status code next to it. Every URL probed came from a field the filer
typed on its own IRS return:

| route | organisations | network cost to find it |
|---|---:|---|
| Form 990 `WebsiteAddressTxt`, newest local return | 252 | **0 requests** — the XML was already on this disk |
| shard-I's completed probe of the same filer-typed fields | 61 | 0 |
| IRS Form 990-N e-Postcard `Website URL` field | 1 | 0 |
| **no URL Cedar holds at all** | **383** | — |

**ProPublica was tested and is NOT a URL source.** 200 cached payloads in
`data/raw/external/propublica_990/` were inspected: **0 carry a website field**
in the `organization` object. Measured, so it is recorded as absent rather than
assumed to be present.

**The entity layer's web map was refused, and the refusal is the finding.**
`np_orgs.cedar_uid` names the entity Cedar **keyed the nonprofit to** — the
tribe or the corporation — not the nonprofit. **26 of the 293** (218 of all
697) have no filer-typed website field and a `cedar_uid` whose site sits in
`cedar_web_map.csv`. Reading it would ask *Ahtna, Incorporated's* website
whether **AHTNA INTERTRIBAL RESOURCE COMMISSION** is Native. **A tribe's own
site is Native by construction**, so that route manufactures a "yes" on every
row it touches and corroborates nothing. It is counted in `plan` and never
fetched.

> **A blank key is a key, and it cost a wrong label on 15 rows.** The first
> pass keyed `cedar_web_map.csv` on a possibly-blank `cedar_uid`, so `"" in wm`
> was True and 15 organisations for which Cedar holds **no URL at all** were
> written as *"refused, we only hold the keyed entity's site"* — 41 instead of
> 26. No page was wrongly fetched or wrongly skipped; both states are
> `NOT_CHECKED`. But they are different facts, and one of them is a task while
> the other is a fact about the world. **It was caught only because the refusal
> list prints the organisations it refused and several of them had an empty
> keyed entity printed beside them** — which is the entire argument for naming
> what you dropped instead of counting it. Corrected at `build`, which
> re-derives the no-URL reason from a web-map index that skips blank keys.

---

## The four things a page can be, and why four

The first classifier scored a **land acknowledgement** as a Native
self-description. `COMMUNITIES IN SCHOOLS PUYALLUP` writes *"this land
acknowledgement is one small step toward true allyship"*; `LUMMI ISLAND
HISTORICAL SOCIETY` writes *"Our deepest respect and gratitude for our
Indigenous neighbours, the Lummi Nation"*. **Both sentences name a nation in
order to say the organisation is not it.** Scored as identity they would have
manufactured exactly the corroboration this pass exists to test for.

So the vocabulary separates four findings that a single "does the page mention
Native" test collapses into one:

| verdict | what the page did |
|---|---|
| `WEBSITE_SAYS_NATIVE_AND_STATES_A_CONTROL_RELATIONSHIP` | first-person identity **and** a charter / ownership / instrumentality relationship |
| `WEBSITE_SAYS_NATIVE` | describes **itself** as Native, tribal, or a body of a named nation |
| `WEBSITE_SAYS_IT_SERVES_NATIVE_PEOPLE` | says it **serves** Native people and does not claim to **be** Native. The nonprofits methodology already refuses to infer control from service |
| `WEBSITE_ACKNOWLEDGES_A_NATION_BUT_DOES_NOT_CLAIM_TO_BE_ONE` | the only Native language is a land acknowledgement or a statement of allyship |
| `WEBSITE_USES_NATIVE_LANGUAGE_UNSPECIFICALLY` | Native language that is none of the above. A human read is what this is for |
| `WEBSITE_NAMES_A_DIFFERENT_COMMUNITY` | names a non-Native community, place or institution type **for itself** |
| `CHECKED_NO_SIGNAL` | read in full, no Native language. **SILENCE IS NOT REFUTATION** |
| `NOT_CHECKED_*` | no URL, not a URL, no readable page, too thin, robots, access-controlled path |

`CHECKED_NO_SIGNAL` carries that caveat in its own `verdict_basis` on every
row, and `verify` V2 fails if any row loses it.

**Verdicts are re-derived at `build` from the saved bytes, never trusted from
the fetch.** The raw pages are on disk under
`data/staging/np_website_check/pages/`, so sharpening the classifier costs no
network and re-asks no host. It has already paid for itself once: the
acknowledgement rule moved 21 rows without a single new request.

---

## What the websites said

**697 organisations attempted. A page was actually read for 167 (24.0%).**

| verdict | all 697 | the 214 whose own 990 is silent | the 28 that also cross a state line |
|---|---:|---:|---:|
| `WEBSITE_SAYS_NATIVE_AND_STATES_A_CONTROL_RELATIONSHIP` | 2 | 0 | 0 |
| `WEBSITE_SAYS_NATIVE` | 9 | 0 | 0 |
| `WEBSITE_SAYS_IT_SERVES_NATIVE_PEOPLE` | 3 | 0 | 0 |
| `WEBSITE_USES_NATIVE_LANGUAGE_UNSPECIFICALLY` | 15 | 6 | 0 |
| `WEBSITE_ACKNOWLEDGES_A_NATION_BUT_DOES_NOT_CLAIM_TO_BE_ONE` | 2 | 1 | 0 |
| `WEBSITE_NAMES_A_DIFFERENT_COMMUNITY` | 35 | 26 | 4 |
| `CHECKED_NO_SIGNAL` | 101 | 47 | 6 |
| `NOT_CHECKED_NO_URL_PUBLISHED` | 383 | 33 | 6 |
| `NOT_CHECKED_URL_FIELD_IS_NOT_A_URL` | 95 | 73 | 10 |
| `NOT_CHECKED_NO_READABLE_PAGE` | 44 | 26 | 2 |
| `NOT_CHECKED_PAGE_TOO_THIN` | 6 | 1 | 0 |
| `NOT_CHECKED_ROBOTS_DISALLOW` | 2 | 1 | 0 |
| **a page was read** | **167** | **80** | **10** |

HTTP outcomes across the 314 URLs probed: `200` 176 · `202` 8 · `000`
(DNS/TLS/connect) 21 · `404` 8 · `403` 2 · `301` 2 · robots-disallowed 2.

### The eleven organisations whose own words say they are Native

These are the first eleven `org_self_statement` assertions this dataset has
ever carried on Native status. Every quote is a literal substring of bytes on
disk beside it, and `verify` V5 re-finds each one in the saved page.

| organisation | state | its own 990 | its own website says |
|---|---|---|---|
| SHINNECOCK KELP FARMERS INCORPORATED | NY | `named_entity` | *"We are a multi-generation collective of Indigenous women who are enrolled members of the Shinnecock Indian Nation…"* |
| NORTH DAKOTA TRIBAL COLLEGE SYSTEM | ND | `program_authority` | *"Chartered by federally recognized Tribal governments, North Dakota's Tribal colleges…"* |
| YAKUTAT TLINGIT TRIBE | AK | `named_entity` | *"…become recognized as a tribal government under the authority of the Indian Reorganization Act."* |
| YTT NORTHERN CHUMASH NONPROFIT | CA | `subject_classification` | *"Currently our Tribe has status as an Acknowledged Tribe by the California Native American Heritage Commission."* |
| LENAPE NATION INC | PA | `subject_classification` | *"An easy answer is that we are the indigenous people of this land now called Pennsylvania."* |
| OGLALA LAKOTA HOUSING AUTHORITY | SD | `named_entity` | *"PROGRAMS FOR OUR TRIBAL MEMBERS… Oglala Sioux Lakota Housing offers a variety of services…"* |
| BLACKFEET ECO KNOWLEDGE INC | MT | `named_entity` | *"…Traditional Ecological Knowlege and Indigenous Lead Organization"* |
| BLACKFEET MMIP | MT | *no local 990* | *"Blackfeet Missing and Murdered Indigenous People (MMIP) is a Montana-based, grassroots 501(c)(3) nonprofit organization…"* |
| NIPMUC NATION TRIBAL COUNCIL INC | MA | *no local 990* | *"Hassanamisco Tribe of Nipmuc Nation… Hassanamisco Nipmuc Tribal Council"* |
| NISENAN MIWOK COLLECTIVE | CA | *no local 990* | *"…lands unlawfully taken during the Gold Rush era, where our people experienced state-sanctioned violence…"* |
| TLINGIT & HAIDA FOUNDATION | AK | *no local 990* | *"…the Foundation strengthens the Tribe's programs and services that uplift tribal citizens and communities."* |

### An important limit on what those eleven corroborate

**A 990 narrative and a website are the SAME SPEAKER.** Seven of the eleven
also have a Native signal in their own filed return. That agreement is worth
having, and it is **one organisation saying the same thing twice, in two
regimes** — not two observers. Under `ASSERTION_LAYER`'s evidence-lineage rule
the honest statement is:

* against the **IRS BMF name match**, the website is a genuinely new observer
  and these eleven rows now rest on something other than Cedar's own inference;
* against the organisation's **own Form 990**, it is not an independent family,
  and booking it as one is exactly the mistake the corroboration layer was
  built to catch.

A third-party observer for nonprofit Native status — a tribe's own site naming
the nonprofit as its instrumentality, or a federal filing that asserts it — is
still absent, and is the next thing worth building.

---

## Does the website settle the 214? Mostly not, and here is the honest count

**Of the 214 whose own Form 990 gives no Native signal, 80 (37.4%) had a page
read at all, and NOT ONE of them says it is Native.**

| what the website did for the 214 | rows | is it a settlement? |
|---|---:|---|
| named a different community for itself | 26 | **the strongest evidence available against the IRS-side row**, and still not a refutation |
| read in full, no Native language | 47 | **no.** Silence in a second place is still silence |
| Native language, unspecific | 6 | no — a human read |
| a land acknowledgement only | 1 | leans against, in the organisation's own voice |
| no page could be read | 134 | no evidence either way |

**So: 26 of 214 are settled as far as evidence can settle them without a
ruling, 54 more were genuinely checked and are still open, and 134 could not be
checked at all.** The dominant reason is not refusal — it is that **the filer
published no website**: 33 have no URL anywhere Cedar holds and 73 typed
something into the 990 field that is not a URL (`N/A` is the commonest value).

### The 28 that cross a state line — one line each

Ten had a page read. Four name a different community in their own words:

| organisation | state | verdict | the page's own words |
|---|---|---|---|
| KANSAS HUMANE SOCIETY OF WICHITA INC | KS | `WEBSITE_NAMES_A_DIFFERENT_COMMUNITY` | *"HILLSIDE, WICHITA, KANSAS 67219 … WELCOME TO THE KANSAS HUMANE SOCIETY!"* |
| WAMPANOAG COUNTRY CLUB INC | CT | `WEBSITE_NAMES_A_DIFFERENT_COMMUNITY` | *"Premier Private Club in CT — Wampanoag Country Club … Dining Reservations Pool Paddle Tennis Golf Membership"* |
| CHICKASAW CIVIC THEATRE | AL | `WEBSITE_NAMES_A_DIFFERENT_COMMUNITY` | *"…the theater relocated to a former scout hut… located in the hollow between Paul Devine Park and Chickasaw E[lementary]"* |
| CALIFORNIA CLUB OF LAGUNA WOODS VILLAGE | CA | `WEBSITE_NAMES_A_DIFFERENT_COMMUNITY` | *"Featuring dazzling costume changes, stellar live vocals… 28 Classic Hits"* |
| CHICKASAW WELLNESS COMPLEX INC | IA | `CHECKED_NO_SIGNAL` | — |
| CHRISTMAS IN ACTION WICHITA TX INC | TX | `CHECKED_NO_SIGNAL` | — |
| MOHEGAN COLONY ASSOCIATION INC | NY | `CHECKED_NO_SIGNAL` | — |
| MOHEGAN VOLUNTEER FIRE ASSOCIATION INC | NY | `CHECKED_NO_SIGNAL` | — |
| MOHEGAN VOLUNTEER FIRE ASSOCIATION VOL. AUX. | NY | `CHECKED_NO_SIGNAL` | — |
| **UTAH NAVAJO HEALTH SYSTEM INCORPORATED** | UT | `CHECKED_NO_SIGNAL` | **see below** |
| CHICKASAW INKANA FOUNDATION | MS | `NOT_CHECKED_NO_READABLE_PAGE` | — |
| PASADENA ROSEBUD ACADEMY CHARTER SCHOOL | CA | `NOT_CHECKED_NO_READABLE_PAGE` | — |
| CHICKASAW ATHLETIC BOOSTER CLUB · CHICKASAW COMMUNITY PARK ASSOCIATION · CHICKASAW DEVELOPMENT CORPORATION · CHICKASAW DEVELOPMENT FOUNDATION · MOHEGAN VOLUNTEER EXEMPT FIREMEN'S BENEVOLENT ASSN · NORTH LAGUNA CREEK VALLEY HI COMMUNITY ASSN · RANCHO LA LAGUNA INC · RED ROSEBUD FOUNDATION · ROSEBUD COMMUNITY PARK ASSOCIATION · ROSEBUD ECONOMIC DEVELOPMENT CORP | various | `NOT_CHECKED_URL_FIELD_IS_NOT_A_URL` | the 990 website field is `N/A` |
| CHICKASAW ELEMENTARY SCHOOL PTA · ROSEBUD FOUNDATION · ROSEBUD GROVE INC · SANTA ROSA BAND OF LOWER MUSCOGEE INC · UNITED HABESHA COMMUNITY OF WICHITA UHCW INC · ZUNI HILLS ELEMENTARY PTSO | various | `NOT_CHECKED_NO_URL_PUBLISHED` | — |

**The place-name families are now visible as families**, which is itself the
finding: *Chickasaw* (a city in **Alabama**, a county in **Iowa** and
**Mississippi**), *Mohegan* (a hamlet in Westchester County, **New York**),
*Rosebud* (towns in Missouri, Texas, Montana and Oklahoma), *Laguna*
(California), *Wichita* and *Zuni Hills* (a Phoenix subdivision). Five
Westchester Mohegan volunteer-fire and colony associations sit in this
population. `UNITED HABESHA COMMUNITY OF WICHITA` names the Ethiopian and
Eritrean diaspora and publishes no site.

### The counter-example, and it is why none of this is written as a refutation

**UTAH NAVAJO HEALTH SYSTEM INCORPORATED** scores `CHECKED_NO_SIGNAL`. It is
plainly Native-serving and plainly not a place-name accident. Its site simply
did not put a Native sentence where this reader could find one. It is the same
lesson as *Tongass Tlingit Cultural Heritage Institute* scoring `placename_only`
in the 990 pass: **the instrument scored the page, not the organisation.**

Three more of the same shape: three rows whose **own 990 corroborates** Native
status also score `WEBSITE_NAMES_A_DIFFERENT_COMMUNITY` — the two sources
disagree, and neither is automatically the loser.

---

## What was not changed

**`np_orgs.csv` was not opened for writing.** No `disposition`, no `tier`, no
`classification_ruling` moved. This is an evidence layer: it produces
`review/np_website_native_check_2026-09-02.csv`, one row per organisation, with
the URL, its publisher-side source, the HTTP outcome, the verdict, the verbatim
quote and the path to the bytes.

Nothing here is a ruling. The 26 that name a different community and the 4
cross-state ones among them are appended to `review/OWNER_DECISION_QUEUE.md`.

---

## Discipline actually observed

* **Pull discipline** — robots.txt fetched once per host with the same UA used
  for content (never `urllib.robotparser`, which reads a 403 as `disallow_all`
  and cost shard H 22 phantom blocks); ≥2.5 s per host, ≥0.8 s global; single
  stream; **no retry loop**; at most two content requests per organisation;
  RUN_DEADLINE on the run; host lock at
  `logs/_HOSTLOCK_1125_np_website_check.json`, released with its counts.
* **Terms** — `TERMS-OWNER-RULING-2026-09-02`: terms language on a tribal or
  nonprofit website no longer blocks harvest. What still binds and was
  honoured: **technical access controls** (a `FORBIDDEN` path test that
  *raises* rather than skips, covering `/wp-admin`, `/admin`, `/.env`,
  `/.git`, `/staging`, backups, dumps and login paths) and **a natural
  person's data apart from their public role**.
* **Privacy, and the check that caught it.** `verify` V7 scans every published
  quote for an email address or a telephone number and **it failed on its first
  run** — `LEGACY TRADITIONAL SCHOOL MARICOPA`'s quote carried a phone number.
  Published quotes are now redacted at `build`; the raw bytes keep the original
  in `data/staging/`, and V5 checks a redacted quote **in fragments** so a
  redaction can hide a phone number and cannot hide a fabrication.
* **No second matcher.** The fetch, robots, decode, sentence and evidence
  machinery is **imported** from `data/staging/np_harvest/web_probe.py`; only
  the output directories are overridden, so nothing is written into shard-I's
  directory. Two matchers for one job drift, and a drifted matcher is worse
  than none because it is trusted.

## Reproduce

```
py -3 code/1125_np_website_native_check.py plan --population nvs
py -3 code/1125_np_website_native_check.py fetch --population nvs --minutes 45
py -3 code/1125_np_website_native_check.py build
py -3 code/1125_np_website_native_check.py verify     # exit 1 on breach
py -3 code/1125_np_website_native_check.py selftest   # 7/7 injections fire
```

## What is worth doing next, in order

1. **The 134 of 214 with no readable page are not one problem.** 73 typed
   something that is not a URL into their own 990 and 33 published nothing;
   those are `SOURCE_DOES_NOT_PUBLISH`, a fact about the world. 26 returned no
   readable page and 2 were robots-disallowed; those are a real retry.
2. **383 of the 697 have no URL Cedar holds at all.** The 990-N e-Postcard
   corpus is already local (`data/staging/np_harvest/raw/data-download-epostcard.zip`,
   93 MB, 2026-08-31 vintage) and the integrator has been asked to promote it
   to `data/raw/external/irs990n/`. Widening the seed to every EIN in it, not
   only those shard-I indexed, is the cheapest remaining coverage.
3. **A third-party observer.** A tribe's own site naming the nonprofit as its
   instrumentality would be the first family that is neither the IRS nor the
   organisation itself. `fac_tribal_single_audits` is the other candidate and
   is already the strongest Native-status evidence in the nonprofit family.
