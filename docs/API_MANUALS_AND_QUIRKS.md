# API manuals and source quirks — SAM · FAC · IRS · GovInfo · SEC

*Written 2026-08-27 from an agent sweep that finished after the session stop.
All retrievals 2026-08-26. `api.sam.gov` was never contacted (no quota spent).
Session WebSearch budget was exhausted (200/200) before this sweep began, so
**everything below came from direct fetches against canonical routes** — grey
literature and listserv documentation are **undiscovered, not absent**.*

**Companion files:** `docs/API_TECHNICAL_QUIRK_VERIFICATION.json` (machine-
readable) · `docs/ACCESS_TECHNIQUES.md` (how to reach a blocked route) ·
`docs/ASSUMPTIONS_AND_LIMITATIONS.md` (what a coverage gap does to a finding).

---

## THE SEVEN THAT CHANGE WHAT WE DO

Ranked by what they break if ignored. Everything else in this file is reference.

1. **FAC truncates at exactly 20,000 rows and returns HTTP 200.** `federal_awards`
   is ~2.5M rows. Any status-code-only check has been ingesting a truncated
   slice. Detect with `Prefer: count=exact` → read `Content-Range`.
2. **FAC's own documented pagination example loses a row per page.** It prints
   `limit=4999&offset=0`, then `offset=5000`. Row 4999 of every 5,000 is never
   fetched. Use `limit=5000`. *(Verified against raw HTML — this is FAC's error,
   not a rendering artefact.)*
3. **`awardeeBusinessTypeName=INDIAN` is an actively dangerous query.** Matching
   is substring and **unanchored on both sides**, so it sweeps in
   `"Subcontinent Asian (Asian-Indian) American Owned"` (code `QZ`) — a South
   Asian ethnicity category. `TRIBAL` catches `"Housing Authorities
   Public/Tribal"` (`8B`). Use exact full names from §1.5.
4. **The IRS 990 S3 bucket is EMPTY.** Probed live: bucket answers 200, zero
   objects; every documented index and example object 404s. Current IRS
   distribution covers **2019–2026 only**. **Filings from 2011–2018 have no
   surviving official public channel** — if anyone has a mirror of the old
   bucket, it is irreplaceable, archive it now.
5. **Tribal suppression under 2 CFR 200.512 hides narrative text ONLY.** All
   structured tribal single-audit data — expenditures, awards, findings and
   their severity — is served to an ordinary key. **Our quantitative tribal
   audit work needs no special access.** But a join from `general` to
   `findings_text` silently drops suppressed rows.
6. **Revoked nonprofits are DELETED from the BMF, not flagged in it.** Every BMF
   snapshot contains only survivors (~1.8M of ~3.8M ever). The censoring is
   non-random and correlated with the outcome.
7. **A SEC 403 usually means a missing User-Agent, not a rate limit** — and the
   block page is *titled* "Request Rate Threshold Exceeded" regardless. Same URL,
   seconds apart: with UA = 200, without = 403.

---

## 1. SAM.gov

### 1.1 Rate limits — five tiers, and the trigger is holding *any* role

Verbatim from `https://open.gsa.gov/api/entity-api/` (and identically on
`contract-awards`, `exclusions-api`, `sam-entity-extracts-api`):

```
Non-federal user with no Role in SAM.gov  | Personal API key       |     10 requests/day
Non-federal user with a Role in SAM.gov   | Personal API key       |  1,000 requests/day
Federal User                              | Personal API key       |  1,000 requests/day
Non-federal System user                   | System account API key |  1,000 requests/day
Federal System user                       | System account API key | 10,000 requests/day
```

The trigger is literally `"with no Role"` vs `"with a Role"` — **not** a special
API grant. This is what the pending org role request buys us. Note a *federal*
user with a personal key gets the same 1,000/day; only a **federal system
account** reaches 10,000, which we will never have.

**Exception — Federal Hierarchy is a separate quota regime.**
`https://open.gsa.gov/api/fh-public-api/` documents only two tiers and never
mentions roles: `"Rate limit for Non-Federal User is 10 requests/day"`. **On its
face our role will not lift us there.** Do not assume the role generalises.

**Quota-exhaustion error is UNDOCUMENTED on SAM.** The Contract Awards
response-code table documents 200/204/400/403/500 and has **no rate-limit row at
all**. The answer only exists at the gateway
(`https://api.data.gov/docs/developer-manual/`): HTTP **429**,
`"OVER_RATE_LIMIT"`. Note the window mismatch — api.data.gov's default is
*hourly*, SAM overrides with *daily* caps.

### 1.2 `emailId` — our hard-won finding is right, and the docs never say so

Verbatim parameter row from the raw source of `contract-awards.md`:

> `emailId` | `"When used in conjunction with the format parameter, allows user
> to get JSON or CSV asynchronous file download links with tokens sent to the
> email address associated to the API key used in the request.<br>Example:
> emailId=Yes&format=JSON"` | `No` | **`String`** | `v1`

Precisely:
- Declared type is **`String`**, not Boolean. The name implies an address; it
  does not accept one.
- The prose rules out the address reading **only by implication** — the
  destination is derived from your key, so the parameter cannot be the address.
- **The value `Yes` appears nowhere except the example string.** The legal value
  set, whether `NO` exists, and the behaviour on passing an actual address are
  all **UNDOCUMENTED**.

Three more traps in the same async flow, verbatim:

> `"If the request is executed successfully, then a file downloadable URL with
> Token will be returned. This URL can also be obtained in emails by providing
> "emailId=Yes"... In the file downloadable URL, the phrase REPLACE_WITH_API_KEY
> must be replaced with a valid API Key and sent as another request. If the file
> is not ready for download, then the users will need to try again in some time."`

So `emailId` is **redundant** (the URL is already in the response body); the
returned URL contains the literal placeholder **`REPLACE_WITH_API_KEY`**; and
readiness polling has **no documented interval, timeout, readiness field, or
distinct status code**. Case-sensitivity of `format` is undocumented — prose says
`format=csv`, the example says `format=JSON`.

### 1.3 String matching is per-parameter, in free text, and unanchored

`awardeeBusinessTypeName`: `"Allows partial or complete value search."` —
substring matching is **official, intended behaviour**. Undocumented:
case-insensitivity, that matching is **unanchored on both sides**, and **any way
to force an exact match**.

There is **no global statement of matching semantics anywhere in the SAM docs**.
It is declared per-parameter with inconsistent capitalisation
(`"Allows partial or complete value search."` on `legalBusinessName`,
`"Allows Partial or Complete value."` on `dbaName`), and many parameters say only
`"Allows a text"`, for which semantics are undocumented.

### 1.4 Extracts omit all-empty columns — UNDOCUMENTED, and do not generalise

Searched `contract-awards` (rendered + raw), `entity-api`, and
`sam-entity-extracts-api`: **none contains a CSV schema, column list, or column-
order guarantee**. Our measured absent `cageCode` is undocumented behaviour.
**Parse by header name, never by index.**

**Contrast:** the *flat-file* Entity Management Extract has a rigid documented
schema — `SAM Master Extract Mapping v6.0 Public File V2 Layout.xlsx` has an
explicit `"Column Order"` column, **142 numbered fields**, `CAGE CODE` fixed at
position 4, terminating in `"END OF RECORD INDICATOR"`. Different product,
different rules. Don't carry the dynamic-header assumption across.

### 1.5 Business type codes — the full tribal-relevant set

From the XLSX, sheet `"STRING Clarification"`, section `"Bus Type String"`.
**Eleven codes, and they mean different things:**

| Code | Name |
|---|---|
| `3I` | Tribal Government |
| `XY` | Indian Tribe (Federally Recognized) |
| `1B` | Tribally Owned Firm |
| `OW` | American Indian Owned |
| `NB` | Native American Owned |
| `05` | Alaskan Native Corporation Owned Firm |
| `8U` | Native Hawaiian Organization Owned Firm |
| `1E` | Indian Economic Enterprise |
| `1S` | Indian Small Business Economic Enterprise |
| `HS` | Tribal College |
| `8B` | Housing Authorities Public/Tribal |
| `G3` / `G5` | Alaskan Native / Native Hawaiian Servicing Institution |

`OW` and `NB` are **two separate codes with near-synonymous names** and the docs
give **no disambiguation** — always check both. Others we use: `27` Self
Certified Small Disadvantaged, `QZ` Subcontinent Asian (Asian-Indian) American
Owned, `A2` Woman Owned, `A5` Veteran Owned, `QF` Service Disabled Veteran
Owned, `23` Minority Owned.

**8(a) and HUBZone are NOT in that list.** They live in a separate
`"SBA Business Types String"` with its own namespace — `A6` SBA Certified 8A
Program Participant, `JT` SBA Certified 8A Joint Venture, `XX` SBA Certified Hub
Zone Firm — and its own counter. Verbatim: `"The first 2 positions of SBA
Certifications is an SBA Business Code followed by an expiration date"` in
`"YYYYMMDD format."`, e.g. `~A620110101~XX20110102~`.

**Two fields, two counters** (`BUSINESS TYPE COUNTER` pos. 31, `SBA BUSINESS
TYPES COUNTER` pos. 117) — **querying the wrong one silently returns nothing**.
Storage is a tilde-delimited string: `23~27~2X~8E~8W~A2~FR~HQ~LJ~VW`.
**An 8(a) code with a past date is a LAPSED certification** — we must not read
it as current.

*This does not change the owner's ruling that the labels are near-worthless for
our purpose. We verify Native ownership independently. The codes are for
recall — a net to find candidates — never for a determination.*

### 1.6 Auth status codes are inconsistent across the SAM family

Docs say **403 only**: `"403 Forbidden: An invalid API key was supplied."`
Gateway agrees (`API_KEY_MISSING` / `API_KEY_INVALID` / `API_KEY_DISABLED` all
403). **Neither 401 nor 404 is documented for a key problem anywhere.**

Our measured 404 was probably one of: api.data.gov `NOT_FOUND` 404 =
`"An API could not be found at the given URL"` (**wrong route**), or Federal
Hierarchy's `"404 – No Data found"` (**empty result set**). The Extracts API
routes key errors through **400**, not 403.

**Branch on the response body's `error.code` string, not the status.** This is
the same shape as our existing rule that a 403 is a fact about one route.

### 1.7 The D&B restriction and the DUNS→UEI cutover — both found, verbatim

Both live on **`https://sam.gov/about/terms-of-use`**, not in the API docs.

> "For the purposes of the following limitation on permissible use of D&B data...
> "D&B Open Data" is defined as the following data elements: Legal Business Name,
> Street Address, City Name, State/Province Name, Country Name, County Code,
> State/Province Code, State/Province Abbreviation, ZIP/Postal Code, Country Name
> and Country Code... **Applicable records containing D&B data include all entity
> registration records with a last updated date earlier than 4/4/2022, all
> exclusions records with a created date earlier than 4/4/2022, and all base
> award notices with an award date earlier than 4/4/2022.**"

> "you agree that you **shall not use D&B Open Data without giving written
> attribution to the source of such data (i.e., D&B) and shall not access, use or
> disseminate D&B Open Data in bulk**"

> "**Systematic access (electronic harvesting) or extraction of content from the
> website, including the use of "bots" or "spiders," is prohibited.**"

**2022-04-04 CONFIRMED, and it is a three-way cutover** — registrations by
last-updated, exclusions by created, awards by award date. Our existing rule said
"every base award before 2022-04-04"; that is the award leg only. **Update the
licensing constraint to name all three keys.**

**Practical:** a `dnbOpenData` field still exists in the live Entity API,
documented with one sentence stating no restriction. The restriction lives only
in the Terms of Use. Attribution **and** the bulk-redistribution prohibition
apply to anything we republish from before the cutover.

**Structural corroboration:** position 2 of the flat-file layout is
`"BLANK (DEPRECATED)"`, max length **0**, `"Blank Spaces, formerly occupied by
the prior Entity identifier"`. The DUNS field was **hollowed out in place, not
deleted** — the docs won't even name DUNS. Old parsers still find a field 2; it
is always blank.

---

## 2. Federal Audit Clearinghouse

### 2.1 The 20,000-row silent truncation

`https://www.fac.gov/api/results-management/`, verbatim:

> **"To keep the FAC running smoothly for all users, we limit requests to 20,000
> results at a time."**

FAC is PostgREST; this is `db-max-rows`, documented upstream as
`"A hard limit to the number of rows PostgREST will fetch"`. **It is a fetch
ceiling, not a validation error** — a query exceeding it returns **200/206 with
exactly 20,000 rows and no error**. FAC documents the cap in prose only and
documents **no** error, status, or warning on truncation.

**Detection:** send `Prefer: count=exact`, read `Content-Range` (`0-24/3573458`).
FAC **never documents this header** — it works because FAC is PostgREST.
⚠️ **Unverified whether it survives the api.data.gov proxy. Test before relying
on it.** FAC's page mentions only `limit`/`offset`, never `Range` or `Prefer`.

### 2.2 FAC's documented pagination skips a row per page

Verbatim from the page source:

```
...?limit=4999&offset=0
...?limit=4999&offset=5000
...?limit=4999&offset=10000
```

`limit=4999&offset=0` returns rows 0–4998; the next page starts at 5000. **Row
4999 of every 5,000 is never fetched** — a silent ~0.02% loss compounding across
every page. Use `limit=5000&offset=n*5000`.

### 2.3 Gateway limits — and our DEMO_KEY prior was wrong

Registered key: `"Hourly Limit: 1,000 requests per hour"` ✅ our prior.
DEMO_KEY: **`"30 requests per IP address per hour"`** and **`"50 requests per IP
address per day"`** — our "~7" was wrong, and the cap is keyed to **IP, not
key**, so a shared NAT exhausts it for everyone behind it.

429 headers documented: `X-RateLimit-Limit`, `X-RateLimit-Remaining`.
**`Retry-After` is NOT documented** — don't build backoff on it. Back off to the
top of the next hour (`"counters... reset on a rolling basis"`).

Verbatim guidance worth adopting project-wide: `"error handling use the HTTP
status code or the error code value for error handling (and not the content of
the message description)"`.

### 2.4 The 2016 floor and the broken bridge

API `"dating back to 2016"`; downloads page offers `"Current Data (2016–Present)"`,
`"Historic Data (1998-2015)"`, `"Migration Metadata (2016-2023)"`.

**`DBKEY` — the Census-era primary key — is `"Not yet incorporated into the GSA
FAC API. This value does not exist for 2023 and future years."`** Also unmapped:
whole tables **REVISIONS, AGENCY, DUNS**. Bridging pre-2016 to post-2016 requires
fuzzy EIN + name + fiscal-year matching. Migrated records carry `-CENSUS-` in
report IDs (`2022-06-CENSUS-0000091651`).

### 2.5 2 CFR 200.512 — CITATION CORRECTION, and it is an opt-out

⚠️ **The provision renumbered.** Our cite **200.512(b)(2)** is correct for the
pre-October-2024 text; in the **current** eCFR it is **200.512(b)(3)**. **Cite by
year or cite both.** *(The human eCFR route 302s to a bot-block interstitial; the
API renderer at `ecfr.gov/api/renderer/v1/content/enhanced/current/...` works.)*

§200.512(b)(3), verbatim in full:

> "(3) An auditee that is an Indian Tribe or a tribal organization (as defined in
> the Indian Self-Determination, Education and Assistance Act (ISDEAA), 25 U.S.C.
> 450b(l)) **may opt not to authorize** the FAC to make the reporting package
> publicly available on a website. To opt-out, an Indian Tribe or tribal
> organization must exclude the authorization described in paragraph (b)(2)(iv)...
> In these instances, the Indian Tribe is responsible for submitting the reporting
> package directly to any pass-through entities... Unless restricted by Federal
> statute or regulation, if the Indian Tribe opts not to authorize publication, it
> must make copies of the reporting package available for public inspection."

**Our reading is confirmed exactly. It is an auditee opt-out election, not a
bar** — the verb is `"may opt not to authorize"` and the mechanism is declining
to check a box. What is withheld is **only FAC web publication of the reporting
package**. What still happens regardless: submission to the FAC is
**unconditional** (§200.512(d); FAC is `"the repository of record"`), direct
distribution to pass-throughs is **mandatory and triggered by the opt-out**, and
**public inspection is still required** from the Tribe.

### 2.6 `is_public = false` suppresses narrative text ONLY

**Exactly three views are gated, identically across `api_v1_1_0` (the DEFAULT),
`api_v1_1_1`, and `api_v1_2_0`:** `findings_text`, `corrective_action_plans`,
`notes_to_sefa`. Plus `combined`, which exists only in `api_v1_1_1` and is also
gated.

**Ungated in every version, served to any ordinary key:** `general`,
`federal_awards`, `findings`, `passthrough`, `secondary_auditors`,
`additional_ueis`, `additional_eins`, `resubmission`.

**Suppression is narrative-only, not record-level.** For a suppressed tribal
audit we still get, with no special access: the audit in `general` (auditee name,
UEI, EIN, city, state, `total_amount_expended`, `dollar_threshold`, outcome
flags, and the `is_public` column itself), every award row in `federal_awards`,
and every finding in `findings` including `is_material_weakness`,
`is_questioned_costs`, `is_repeat_finding`, `type_requirement`.

**So: expenditures, program mix, finding counts and severity, repeat findings —
all available, unaffected by the opt-out.** Only narrative text-mining hits the
wall. **Sibling trap: a join from `general` to `findings_text` silently drops
suppressed rows** — always quantify against `general` filtered on
`is_public = false`, or you will report a tribal universe smaller than it is and
biased by which tribes exercised the election.

*(FAC's own framing is looser than the regulation — `"suppress parts of their
single audit report data from our public search results"`. Read the view SQL,
not the prose.)*

### 2.7 Census-era archive — data-quality warnings that bite

Archive is **live on fac.gov**, not archive.org: a combined
`"Download full 1998-2015 dataset (413 MB)"` plus per-year `census-[YEAR].zip`.
Legacy hosts `harvester.census.gov/facdissem/` → `facdissem.census.gov/` →
`fac.gov` (redirect chain confirmed) — Census-era hosts are retired.

FAC's own caveat, verbatim:

> **"The quality of data validations were limited in the beginning, and improved
> over the years. The current Clearinghouse is unable to answer any questions
> about the historic data at this time; it is provided as part of the public
> record."**

Tables are `ELEC*`-prefixed (**ELECAUDITHEADER, ELECAUDITS, ELECAUDITFINDINGS,
ELECEINS, ELECUEIS, ELECCPAS, ELECPASSTHROUGH**) — **not** the
`gen.txt`/`cfda.txt`/`captext.txt` names in our brief. Columns are defined across
**six era bands: 1997-2000, 2001-2003, 2004-2007, 2008-2009, 2010-2012,
2013-2015**, many fields `"n/a"` in early bands. **Never concatenate the per-year
CSVs naively** — build an explicit band-by-band crosswalk. Unresolved: prose says
1998–2015 but the first band is labelled 1997-2000.

Ten documented reliability concerns; the ones that bite, verbatim:
**"The fiscal year start and end date in migrated records are one day early."** ·
**"The accepted date in migrated records used the wrong historical date field."** ·
`"The value for a historical field was incorrectly mapped from Census to GSA"`
(**MATERIALWEAKNESS**) · `"The audit report for some historical SF-SACs are not
present."` · `"Report IDs are based in part on (possibly incorrect) user-entered
data."` · "Duplicate Valid Submissions."

**The off-by-one fiscal-year shift on all migrated records is silent and
systematic** — it misclassifies any record whose FY begins on the 1st. The
**MATERIALWEAKNESS mismapping hits a headline outcome variable.**

Eight Census-era rollup fields no longer exist and must be user-reconstructed:
**ALN (prev. CFDA), COGOVER, QCOSTS, CYFINDINGS, TYPEREPORT_MP,
MATERIALWEAKNESS_MP, REPORTABLECONDITION_MP, PYSCHEDULE**.

---

## 3. IRS — 990 e-file corpus and the EO BMF

### 3.1 The S3 bucket is dead — probed, not assumed

`registry.opendata.aws/irs990/` carries a deprecation notice:
`"The provider of this dataset will no longer maintain this dataset, and the
historic data will no longer be available via the Registry of Open Data on AWS."`

**Live probe 2026-08-26:** `index_2019.json` → **404** · `2011_index.csv` →
**404** · the README's own example object → **404** · bucket listing
`?max-keys=3` → **HTTP 200 with zero `<Contents>` elements**.

**The bucket exists and answers, but holds no objects.** Any pipeline resolving
`s3://irs-form-990/...` is dead.

**Current distribution** (`irs.gov/charities-non-profits/form-990-series-
downloads`): `https://apps.irs.gov/pub/epostcard/990/xml/{YYYY}/{YYYY}_TEOS_XML_
{MM}{A-D}.zip` with `index_{YYYY}.csv`, **2019–2026 only**. Verbatim:
`"Some months may have more than one entry due to the size of the download."`
(splits are size-driven, not calendar-driven).

⚠️ **COVERAGE CLIFF: 2011–2018 filings have NO surviving official public
distribution channel.** Check whether we hold a mirror. If we do, it is
irreplaceable — archive it and record its provenance.

**Index fields:** `"Return ID, Filing Type, EIN, Tax Period, Submission Date,
Taxpayer Name, DLN and Object ID."` — **no `URL` field** in the IRS-era index.
The IRS's own FAQ is titled *"How do I convert the index file from scientific to
text?"* — **the IRS documents that DLN and Object ID get coerced to scientific
notation and silently destroyed** by naive parsers. **Read both as strings.**

**Filing-year, not tax-year:** filename prefixes and index files are organised by
**the year the filing was received**.

### 3.2 BMF layout — URL correction and the real code tables

⚠️ **`https://www.irs.gov/pub/irs-soi/eo_info.pdf` (the URL in our notes) returns
404.** Live document is **`https://www.irs.gov/pub/foia/ig/tege/eo-info.pdf`**
(hyphen, FOIA/TEGE path), January 2026. Landing page dated 2026-08-11;
**1,957,340 records**; `"This is a cumulative file, and the data are the most
recent information the IRS has for these organizations."`

**FILING REQUIREMENT CODE — the real table:**

| Code | Definition |
|---|---|
| 01 | 990 (all other) or 990EZ return |
| 02 | 990 - Required to file Form 990-N - Income less than $25,000 per year |
| 03 | 990 - Group return |
| 04 | 990 - Required to file Form 990-BL, Black Lung Trusts |
| 06 | 990 - Not required to file (church) |
| 07 | 990 - Government 501(c)(1) |
| 13 | 990 - Not required to file (religious organization) |
| 14 | 990 - Not required to file (instrumentalities of states or political subdivisions) |
| 00 | 990 - Not required to file (all other) |

Every code we guessed is confirmed; the table adds **03, 04, 07, 00**. **`00` is
a distinct, large, easily-misread category — not a missing value.** And **code
02's gloss is stale**: it says `$25,000` when the actual 990-N threshold is
`$50,000` — an error still present in January-2026 IRS documentation.

Other quirks, all verbatim-sourced:
- **`NTEE_CD`**: `"The fourth digit further defines the classification of the
  organization and is not defined here."` — **the IRS documents only 3 of the 4
  characters of its own field.** `Z = "Unknown"` is a real populated value.
- **`CLASSIFICATION` is not a single code**: `"One to four different
  classification codes may be present."` Parsing it as an integer is wrong.
- **`FOUNDATION` `00` = `"All organizations except 501(c)(3)"`** — i.e. "not a
  501(c)(3) at all", **not** "not a foundation".
- **`STATUS` has only four codes and all are good-standing** (01 Unconditional,
  02 Conditional, 12 §4947(a)(2) trust, 25 terminating PF status). **There is no
  "revoked" value.**
- **BMF `STATE` is a mailing address**: `"generally represent the location of an
  organization's headquarters, which may or may not represent the state(s) in
  which an organization has operations."`
- **`TAX_PERIOD` is `"the latest return filed"`** — financial fields are a single
  stale snapshot, **not a panel**. `INCOME_AMT ≠ REVENUE_AMT` by construction.
- Legacy activity code `923 "Indians (tribes, cultures, etc.)"` is populated
  **only for pre-1995 determinations** — **not a reliable tribal identifier.**

### 3.3 §6033(j) auto-revocation — a survivorship filter, not a flag

The decisive BMF sentence, verbatim:

> **"If an organization's exemption is revoked... the organization's name is
> removed from publicly accessible venues, including this file."**

**Revoked organizations are DELETED from the BMF, not flagged within it.**
Combined with the four good-standing-only STATUS codes, **any BMF snapshot
contains only survivors** — NCCS quantifies it as `"~3.8 million organizations
ever"` vs `"~1.8 million currently active"`.

The censoring is **non-random and correlated with the outcome**: revocation is
triggered by three consecutive years of non-filing (§6033(j)(1)(B)), concentrated
among small volunteer-run organizations. Reconstructing history requires joining
the separate Auto-Revocation List back in — and Pub. 5891 warns:
`"Just because an organization appears in this dataset doesn't mean that the
organization is currently revoked, as they may have been reinstated."`

**Distributed data error, still present in the June 2026 file:**
> **"Organizations on the auto-revocation list with a revocation date between
> April 1 and July 14, 2020, should have a revocation date of July 15, 2020."**

Every revocation date in that window is wrong and must be recoded.

### 3.4 Form 990-N carries no financial data at all

Eight items only: EIN; tax year; legal name and mailing address; other names;
principal officer name and address; website; **confirmation that gross receipts
are $50,000 or less**; termination statement if applicable. §6033(i) confirms it
structurally — **it contains no financial quantity of any kind.**

**Absent from the XML corpus** (two independent statements): AWS README
`"Forms 990-N (e-Postcard) are not available withing this data set."` *(sic)* and
Pub. 5891 `"This dataset does not include Form 990-N information."`

**Consequence:** 990-N filers **are** in the BMF (`FILING_REQ_CD = 02`) but
**not** in the 990 corpus. **A denominator from the BMF and a numerator from the
e-file corpus are mismatched populations.** Also the $50k threshold is **not a
clean RD** — the "normally" test uses 1/2/3-year lookbacks at
$75,000/$60,000/$50,000.

### 3.5 Taxpayer First Act — a size-correlated hole, one year wide

> "for tax years ending July 31, 2020 and later MUST be filed electronically"
> (990 and 990-PF)
> **"For tax years ending July 31, 2021, and later, Forms 990-EZ must be filed
> electronically."**

**Small organizations are missing from the XML corpus a full year longer than
large ones**, so a pooled 2019–2021 panel has size-correlated missingness whose
composition changes year over year. Corroborated in the literature — Ely,
Calabrese & Jung (2023): `"older nonprofits with greater capacity and
sophisticated financial characteristics are historically more likely to e-file."`

Pub. 5891: **"Note: The XML dataset contains only e-filed returns."** And:
`"As of December 26, 2023 the IRS will no longer accept electronically filed
returns for years 2020 and older."` — **late filings for old tax years revert to
paper and re-enter the XML gap even post-mandate.**

### 3.6 §7871 — tribes are outside the BMF entirely

§7871(a) opens `"An Indian tribal government shall be treated as a State—"`
followed by a **closed enumeration** of seven purposes: §170/2055/2106(a)(2)/2522
deductibility, certain excise taxes, §164, §103 bonds, §511(a)(2)(B),
§§105(e)/403(b)(1)(A)(ii)/454(b)(2), and chapters 41/42.

**§501(a), §501(c)(3), and §6033 are not on that list.** Charitable deductibility
for gifts *to* a tribe flows from §7871(a)(1)/§170 — **not** from the tribe
holding 501(c)(3) status. IRS: `"As governmental entities, federally recognized
tribes are not subject to income taxes."` (cite §7871 and Rev. Rul. 67-284, not
the FAQ — it carries a "not legal authority" disclaimer).

**The three-way distinction:**
- **(a) The tribe itself** — not a 501(c)(3), not "tax-exempt" in the §501 sense
  at all, but a **sovereign not subject to federal income tax**. §6033 doesn't
  reach it → **not in the EO BMF, files no Form 990.**
- **(b) Political subdivisions of the tribe** — §7871(a)(1) covers `"a political
  subdivision thereof"`; same conclusion.
- **(c) Tribally-chartered nonprofits — DIFFERENT.** A separately organized
  nonprofit with §501(c)(3) recognition **is** in the BMF (`SUBSECTION = 03`) and
  **does** file the 990 series under normal §6033 and §6033(j) rules. Tribal
  housing authorities, colleges, health boards and charitable foundations
  commonly fall here.

⚠️ **First-order consequence for Cedar Press.** A 990/BMF measure of "nonprofit
activity in Indian Country" captures **only category (c)** and is structurally
blind to (a) and (b). Since tribal governments deliver much of what is elsewhere
nonprofit-provided (health, housing, education, social services), **BMF/990 data
systematically understate capacity on tribal lands, and the understatement varies
with how much each tribe channels through government vs. chartered nonprofits.**
**Cross-tribal or reservation-vs-non-reservation comparisons on 990 counts or
revenue measure organizational form choice, not underlying activity.**
Compounding it: BMF `STATE` is a mailing address, so an off-reservation-
headquartered tribal nonprofit geocodes off-reservation.

**→ This belongs in `ASSUMPTIONS_AND_LIMITATIONS.md` before any nonprofit trend
ships.**

Also note `FILING_REQ_CD = 14` (instrumentalities) and `SUBSECTION/CLASSIFICATION
= 01/1` ("Government Instrumentality") — **entities that are in the BMF but file
no 990**.

> Honest caveat: **Publication 4076 could not be retrieved (404, apparently
> withdrawn)** and nothing is quoted from it. No single IRS sentence saying
> "tribes are not required to file Form 990" was found. The conclusion is
> assembled from the §7871(a) closed enumeration + §6033's predicate on §501(a) +
> the IRS "not subject to income taxes" statements, all quoted verbatim.

### 3.7 The NCCS quirks document is the find

`https://urbaninstitute.github.io/nccs-data-core/11-upstream-source-quirks.html`
— the single most valuable methodological document in the sweep:

> **"The py2014 990 .dat file has one malformed row around row 2,980. fread
> default behavior would truncate the read at the bad row, returning ~2,978 of
> the 299,405 rows."** ← **99% silent data loss**
> "In the py2015 IRS source files, several column-name headers have the letters Y
> and N substituted for the digits 1 and 2, consistently in both directions."
> "The IRS did not publish a 990-PF extract for processing years 2017, 2018, or
> 2019."
> "SOI did not re-encode nonpfrea after the form revision. Code 9 in the data
> continues to mean 509(a)(2)... not 'agricultural research organization'."
> "py2012–py2017 extracts are space-delimited .dat files; py2018+ are .csv"

Also: `"Legacy duplicate rates can be large (e.g. ~36% of 1998/990combined rows
are duplicates)"`, and pre-2012 you **cannot distinguish 990 from 990-EZ**.

**The IRS's own caveat on the SOI extract:**

> "These extracts contain selected financial data... **collected for program
> administrative purposes**. During IRS administrative processing, some
> adjustments are made which can result in **differences between the information
> as originally reported and the data on this extract**... **We will periodically
> update the extracts to include appropriate corrections.**"

**The SOI extract is not the as-filed return** — which is why it will never
reconcile with the e-file XML — **and it is silently revised in place.** Two
downloads of the "same" year at different times can differ. **Record the download
date and archive the raw pull.** *(This is our existing vintage discipline; it
now has a source-side justification to cite.)*

**Peer-reviewed, all verified via the Crossref API** (bibliographic data
confirmed; quotes are publisher-deposited abstracts; **no full texts read**):

- **Boland, Neely & Tinkelman (2026)**, "Research Note: Form 990 Data Quality and
  Reliability," *NVSQ*, DOI `10.1177/08997640261434934` — **the "not audited"
  citation**: `"IRS Form 990 data—the most widely used nonprofit data set—raises
  reliability concerns because it is unaudited and follows tax, rather than
  Generally Accepted Accounting Principles (GAAP) rules."`
- **Froelich, Knoepfle & Pollak (2000)**, *NVSQ* 29(2):232–254, DOI
  `10.1177/0899764000292002` — canonical 990-vs-audit validation study.
- **Ely, Calabrese & Jung (2023)**, *Voluntas* 34:20–28, DOI
  `10.1007/s11266-021-00398-8` — the e-file selection-bias citation.
- **Abu-Khadra & Olsen (2023)**, *J. Information Systems* 37:169–188, DOI
  `10.2308/isys-2022-031`.
- Bibliographic only: Krishnan/Yetman/Yetman (2006) `10.2308/accr.2006.81.2.399` ·
  Yetman & Yetman (2012) `10.2308/accr-50367` · Yetman/Yetman/Badertscher (2009)
  `10.1177/0899764008315878` · Lecy & Searing (2014) `10.1177/0899764014527175` ·
  Lecy/Searing/Li (2023) `10.4337/9781800888289.00011` · Gupta & Park (2025)
  `10.1080/14719037.2025.2557857`.

---

## 4. GovInfo

### 4.1 36,000/hour — our 1,000/hr prior was wrong here

The Swagger UI at `api.govinfo.gov/docs/` is JS-only. **The real manual is
`https://raw.githubusercontent.com/usgpo/api/main/README.md`.** Verbatim:

> "- 36,000 requests per hour (Primary Rate limit)
> - 1,200 requests per minute
> - 40 requests per second"

**GovInfo is fronted by api.data.gov but has a raised limit — 36× the default.**
We have been pacing GovInfo far more conservatively than required.

### 4.2 The 10,000-record wall and `offsetMark`

> "`offsetMark`: starting record. The initial request should always be `*`, and
> the API will provide the correct offsetMark value for the next page's
> information in the `nextPage` key. **Note:** offsetMark effectively replaces the
> `offset` parameter. The advantage... is that it allows traversals of the results
> past the first 10,000 **recors**" *(sic)*

**Plain `offset` cannot traverse past 10,000 records.** Always start
`offsetMark=*` and follow `nextPage`. `pageSize` max **1000**.

ZIP generation is lazy: `"you may receive a HTTP503 response with a Retry-After
header"` — body `{"message":"Generating ZIP file. Please retry your request again
after 30 seconds"}`. **A 503 here is not a failure.**

### 4.3 `lastModified` ≠ publication date — the reappearing-documents trap

> "`lastModifiedStartDate` and `lastModifiedEndDate`... represents the time that
> this package was added or updated... **It is not the equivalent to Date
> Published, Date Issued, or Date Ingested in MODS.**"

**`/collections/...` returns packages MODIFIED in your window — a re-touched 1994
document reappears in a 2026 query.** For publication-date semantics use the
**`/published`** endpoint with `dateIssuedStartDate`/`dateIssuedEndDate`.

**This directly affects our incremental-refresh cadence work** — a
`lastModified`-keyed poller measures GPO system activity, not new publication,
and will report churn as growth.

### 4.4 Coverage — "select" is doing real work

- Congressional Record (Daily): **1994 to Present**
- Federal Register: **1936 to Present**
- United States Courts Opinions: **"Select Courts from 2004 to Present"**
- Statutes at Large: 1789 to Present
- Congressional Hearings: **"Select Hearings Back to the 85th Congress"** —
  `"GovInfo has select House and Senate hearings for the 104th Congress (1995-96)
  forward. Hearings from earlier congresses are being digitized."`

**GovInfo is explicitly NOT a complete archive for several collections. Treat
absence as unknown, not as non-existence.** This is the same rule as our 403
discipline, applied to coverage.

32 collections enumerated in `samples/collections/collections-formatted.json`
(`USCOURTS`, `BILLS`, `CHRG`, `FR`, `GAOREPORTS`, `CRPT`, `CPD`, `CFR`, `PLAW`,
`CREC`, `CDOC`, `CRECB`, `CPRT`, `USCODE`, `BUDGET`, `LSA`, `STATUTE`, `HOB`,
`GOVMAN`, `CDIR`, `HMAN`, `HJOURNAL`, `SMAN`, …). `BILLSTATUS` appears in README
examples but is not in that list.

---

## 5. SEC EDGAR

**Method note that is itself a finding:** `sec.gov` returned **HTTP 403 to
WebFetch on every attempt**, and `web.archive.org` was unavailable. **All SEC
pages were retrieved successfully via `curl` with a declared User-Agent** — which
is exactly what SEC policy requires.

### 5.1 Fair access — 10 req/sec and a mandatory UA

> **"Current max request rate: 10 requests/second."**
> **"The SEC does not allow botnets or automated tools to crawl the site."**
> **"Please declare your user agent in request headers:
> User-Agent: Sample Company Name AdminContact@<sample company domain>.com"**

Both our priors confirmed verbatim, with the exact sample format.

Also: `"EDGAR started in 1994/1995."` · `"Indexes to all public filings are
available from 1994Q3 through the present"` · and an under-appreciated one:
`"The full and quarterly index files are rebuilt weekly, early on Saturday
mornings, so that any post-acceptance correction (PAC) deletes or updates are
incorporated."` — **daily indexes never reflect later removals; only the weekly
rebuild does.** A daily-index-only pipeline accumulates withdrawn filings.

### 5.2 A 403 means check your UA first

One request with an **empty** User-Agent, to a page already retrieved
successfully, returned **403**:

> **"SEC.gov | Request Rate Threshold Exceeded**
> Automated access to our sites must comply with SEC.gov's Privacy and Security
> Policy... Reference ID: 0.1778ce17.1787793136.65a3ffb"

**The block page is titled "Request Rate Threshold Exceeded" even though the
cause was a missing User-Agent and the request rate was one.** The error actively
misdiagnoses itself. **A 403 from SEC almost never means the document is absent
and often does not mean you were rate-limited.**

### 5.3 Full-text search — 2001 floor, and an undocumented 10,000 cap that saturates

> **"Full-Text Search will allow you to search the full text of all EDGAR filings
> submitted electronically since 2001. The full text of a filing includes all data
> in the filing itself as well as all attachments (such as exhibits)."**

`"since 2001"` — **no more precise date is officially stated.** Do not write
`2001-01-01`.

**No SEC document states a result cap.** A single probe of
`efts.sec.gov/LATEST/search-index?q=test` returned:

```json
"hits":{"total":{"value":10000,"relation":"gte"}
```

**`relation: "gte"` is the tell** — Elasticsearch reports "10,000 or more", not
the true count. **`hits.total.value` saturates at exactly 10,000 and stops
counting.** Any code reading it as a result count silently reports 10,000 for
every large query. Partition by date or form type to stay under the window.
*(Inferred from Elasticsearch's `max_result_window` default + the empirical
probe. Labelled inferred, not documented.)*

Query syntax worth having: wildcards only as a trailing `*`, never leading or
medial, and not in phrases or booleans · `AND` is implicit and **not recognized**
· `NOT`/`OR`/`NEAR()` must be capitalised · `NEAR()` defaults to 10 words.

### 5.4 data.sec.gov — the submissions sharding quirk

`"These APIs do not require any authentication or API keys to access."`

> "**The object's property path contains at least one year's of filing or to
> 1,000 (whichever is more) of the most recent filings... If the entity has
> additional filings, `files` will contain an array of additional JSON files and
> the date range for the filings each one contains.**"

**`submissions/CIK##########.json` gives only ~1,000 recent filings. A prolific
filer's older history lives in additional shards listed under `files[]`.**
Reading only the top-level object silently truncates filing history — **and it
truncates more for exactly the entities that file most.**

XBRL: `/api/xbrl/companyconcept/...`, `/companyfacts/...`, `/frames/...`. Frames
caveat: `"the frame data is assembled by the dates that best align with a
calendar quarter or year"` — different reporting start/end dates land in one
frame. Periods: `CY####` (365±30 days), `CY####Q#` (91±30), `CY####Q#I`
(instantaneous). Bulk `companyfacts.zip` / `submissions.zip` are
`"republished nightly at approximately 3:00 a.m. ET."` — **that is the refresh
cadence to key on, not a stated schedule.** Also: `"data.sec.gov does not support
Cross Origin Resource Scripting (CORS)."`

---

## CORRECTIONS TO OUR STATED PRIORS

| Prior | Verdict |
|---|---|
| SAM: non-federal 10/day → role grants 1,000/day | ✅ **Confirmed**, 5 tiers; trigger is holding *any* role |
| SAM `emailId` is a boolean, not an address | ✅ **Correct**; declared type `String`; semantics **UNDOCUMENTED** |
| SAM `awardeeBusinessTypeName` is substring | ✅ **Documented** — and unanchored both sides |
| SAM extracts drop all-empty columns | ⚠️ **UNDOCUMENTED**; true for the CSV, **false** for the 142-field flat file |
| SAM invalid key → 401 and 404 | ❌ Docs say **403 only**. Our 404 was likely a wrong route or an empty result |
| DUNS→UEI cutover 2022-04-04 | ✅ **Confirmed verbatim**, and it is a **three-way** cutover |
| FAC silent row cap "~20,000" | ✅ **Exactly 20,000**, prose only, **no error on truncation** |
| api.data.gov 1,000/hr | ✅ for FAC; ❌ **GovInfo is 36,000/hr** |
| DEMO_KEY throttles after ~7 calls | ❌ **30/hour, 50/day, per IP** |
| FAC API starts 2016, archive to FY1998 | ✅ Confirmed; `DBKEY` is gone, so no clean bridge |
| 2 CFR 200.512(b)(2) tribal opt-out | ✅ Opt-out confirmed — ⚠️ **renumbered to (b)(3)** |
| Tribal suppression hides tribal audit data | ❌ **Narrative text only.** All structured data is public |
| GovInfo offset limit 10,000 | ✅ `offsetMark=*` is the documented escape; `pageSize` max 1000 |
| SEC 10 req/sec + mandatory UA | ✅ **Both confirmed verbatim** |
| EDGAR FTS floors at 2001 | ✅ `"since 2001"` — **no more precise date is official** |
| EDGAR FTS 10,000 result cap | ⚠️ **UNDOCUMENTED**; empirically confirmed; `hits.total.value` **saturates** |
| efts 403 = missing UA | ✅ **Demonstrated** — and the block page misdiagnoses itself |

---

## MANUALS NOT RETRIEVED — where to resume

**Highest value:** **IRM 25.7.1 — Exempt Organizations Business Master File.**
The authoritative source behind the BMF layout, and the likely resolution of the
stale `$25,000` in Filing Requirement Code 02.

**SAM** — Data Services Entity Information Data Dictionary (JS-only Angular SPA;
worked around via the extract XLSX) · Entity Management OpenAPI spec (path
undetermined) · Exclusions extract layout PDF (not fetched) · FOUO/Sensitive
layouts (not attempted) · full Entity Structure code list (the XLSX cell is
**truncated mid-word** at `"CY - Cou"`).
*Dead routes, recorded as facts:* `github.com/GSA/sam-api-docs` **404, does not
exist** — the real repo is `GSA/open-gsa-redesign`, `_apidocs/` ·
`open.gsa.gov/api/entity-information-api/` **404 — there is no such API, treat
the name as non-existent** · five GSA IAE pages, all 404.

**FAC** — `api.fac.gov/` OpenAPI root **403** (so **whether `Prefer`/`Range`
survive the proxy is unverified**) · `/data/reliability/validations/` and
`/curation/` referenced but not retrieved (curation matters for reproducibility:
post-hoc record changes) · `/api/terms/` not retrieved (**may carry bulk-access
restrictions**) · the Tribal Data API Access Attestation form is named with no
URL, Helpdesk only, **eligibility for non-federal researchers unknown** · the
interior of any `census-YEAR.zip` (open: do historic narrative tables exist? does
`census-1997.zip` exist?).

**IRS** — **Pub. 4076 "Federal Tax Considerations for Indian Tribal Governments"
404, apparently withdrawn** · TEOS main page 403 (Akamai) · **historical XML
schema version list — the page lists only TY2023–2026, so the version strings in
our notes are unconfirmed and are not quoted** · **any documentation of an index
restatement does not exist in any official source checked** (AWS README,
registry, downloads page, TEOS FAQ, Pub. 5891, SOI page) — the same-filing-in-
multiple-years phenomenon is documented for the *SOI extracts* by NCCS
(`"Duplicates on this key are exactly the rows where is_amendment == TRUE"`) but
that was **not verified on the XML index itself** · Nonprofit Open Data
Collective concordance file (the main community resource for cross-year XPath
harmonization) referenced only · Rev. Rul. 67-284 full text not fetched ·
P.L. 116-25 §3101 section number unverified · all §3.7 article full texts are
paywalled.

**GovInfo** — `api.govinfo.gov/docs/` Swagger UI is JS-only ·
`govinfo.gov/help/<collection>` "What's Available" bodies are client-side
rendered (only the static title line, which carries the coverage range, is
fetchable).

**Session-wide** — **WebSearch budget was exhausted (200/200) before this sweep
ran; zero web searches were performed.** Everything was reached by direct URL
fetch. **Grey literature and any paper not surfaced by targeted Crossref queries
are undiscovered, not absent.**

---

## RULES THIS SWEEP EARNED

- **A cap documented in prose with no error on the wire is a silent truncation.**
  FAC returns 200 with exactly 20,000 rows. Ask for the count, don't infer it
  from the absence of an error.
- **A source's own example can be wrong.** FAC's documented pagination loses a
  row per page. Read examples as claims, not as tested code.
- **A count field can saturate.** EDGAR's `hits.total.value` stops at 10,000 and
  says so only in a sibling field (`relation: "gte"`).
- **A block page can misdiagnose itself.** SEC says "Request Rate Threshold
  Exceeded" when the real cause is a missing header. *(Companion to our existing
  rule that a 403 is a fact about one route.)*
- **Deletion is not the same as a flag, and it biases the survivors.** Revoked
  nonprofits leave the BMF entirely; the STATUS column has no value for them.
- **A modification timestamp is not a publication date.** GovInfo's
  `lastModified` makes 1994 documents reappear in a 2026 window.
- **Undocumented is not unknowable, and it is not settled either.** Every
  UNDOCUMENTED label above is a measured behaviour we should re-measure, not a
  fact we can cite.
