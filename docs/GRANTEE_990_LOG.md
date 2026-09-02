# Grantee 990 pull — build log, 2026-08-07

Build script: `code/112_pull_grantee_990s.py`
(one script, `--steps index,archives,xml,deflate64,fetchlog,build,passthrough,codebook,report`)

Outputs: `data/clean/np_grantee_financials.csv` ·
`data/clean/advocacy_passthrough_2026-08-07.csv` ·
`review/grantee_990_unresolved_2026-08-07.csv` ·
`logs/112_build_report_2026-08-07.txt`

Closes the item ranked first in `docs/ADVOCACY_PASSTHROUGH_LOG.md`
("What would move this furthest next"). Inputs from
`docs/PHILANTHROPY_DISCOVERY_LOG.md` (the grantee list) and
`docs/EARMARKS_SCHEDC_BUILD_LOG.md` (the retrieval machinery).

---

## The gap this closes

The pass-through build produced 185 complete funding → lobbying chains and
**every one of them rested on the LDA leg**. The 990 leg contributed nothing:

> Only **24 of the 927 recipient EINs** had any row in `np_financials.csv`, and
> every one of those filed no Schedule C and reported $0 on Part IX line 11d.

That was never a parser failure. Script 99 filtered the IRS e-file index
against `np_financials` + `np_orgs`, and **491 of the 601 philanthropy grantees
are outside that corpus entirely** — they were never in the filter set, so
their returns were never fetched. This build points the same machinery at the
grantee EIN list.

**It is queue length, not new access.** No new host, no new method, no new
parser. Script 99's `HttpRangeFile`, `zip_manifest`, `parse_schedule_c` and
`_consolidate_lobbying` are imported and called; `resolve_entity` is imported
from `code/33_apply_party_rulings.py` (standing rule 8) and the eight
containment guards are imported from script 111. No second matcher was written.

---

## Target list — 601 named, 927 worked

| Source of the EIN | EINs |
|---|---:|
| Schedule I Part II of the 7 Native grantmakers (`schedule_i_grantees_2026-08-06.csv`) | **601** |
| The philanthropy review queue (`agent_native_org_candidates_philanthropy_2026-08-06.csv`) | 567, a strict subset of the 601 |
| Recipient EINs in the pass-through funding leg | 927 |
| **Worked here** | **927** |

The 326 extra EINs are recipients read out of the LOCAL e-file Schedule I cache
— grantees of Tulalip Foundation, Osage Nation Foundation, ANTHC, NPAIHB, ITCA
and NIHB. They cost nothing: the index stream and the ZIP central directories
have to be read either way. **Both denominators are reported separately
throughout and are never mixed.**

---

## Retrieval — 97.0%, against 34.3% last time

| | script 99 | this build |
|---|---:|---:|
| returns retrieved | 2,195 | **3,697** |
| of possible | 6,397 | 3,811 |
| **retrieval rate** | **34.3%** | **97.0%** |

The rate is not an improvement in method; it is an improvement in *coverage of
the queue*. Script 99 fetched the latest return per EIN over a much larger
universe and stopped; this build fetched **every indexed Schedule-C-bearing
return** for a smaller, fully-worked EIN list.

Of the 601 named grantees: **2,447 returns indexed, 2,376 retrieved (97.1%),
over 388 of the 601 EINs.**

### Bandwidth

5.5 million index rows streamed and filtered in flight (676 MB read, nothing
kept but the 4,021 matched rows). Then **1,449 MB of HTTP range reads** across
82 archives in the two retrieval passes — instead of the ~30 GB those archives
occupy — plus a further ~200 MB of central-directory reads in the provenance
reconciliation. Five DEFLATE64 archives were downloaded whole and deleted one
at a time.

### THE 2022 ARCHIVE THE IRS PAGE DOES NOT LIST

178 returns could not be found in any listed archive, and the reason is a real
gap in the IRS's own download page rather than a defect here:

```
index_2022.csv                  656,503 rows
2022_TEOS_XML_01A.zip           433,529 members   <- the only 2022 archive listed
2022_TEOS_XML_02A.zip           222,974 members   <- not listed anywhere
```

`2022_TEOS_XML_02A.zip` (1,408 MB) exists and serves HTTP 200. It was found by
HEAD-probing the year's naming sequence, and it is admitted on **the status
code, never on the plausibility of the URL** — the same rule script 99 applied
to the unlisted 2017 and 2018 archives. It carries `basis =
probe_verified_http_200_not_page_listed` in
`data/raw/external/irs990_grantee/_zip_manifest_extra.csv`. Script 99's own
`_zip_manifest.csv` was **not modified**; the extra archive lives in a separate
file that this script merges at fetch time.

Note that 2021 is genuinely a single archive — `2021_TEOS_XML_01A.zip` holds
all 589,904 returns of that submission year — so "one archive listed" is not by
itself evidence of a gap. The member count against the index row count is.

### DEFLATE64, again

Five archives (2025 05A/05B/11B, 2026 05A/05B) raised
`NotImplementedError` on 273 members. Downloaded whole, opened with the system
7-Zip, one at a time with each deleted before the next: **255 recovered.**

### What is still missing, stated rather than smoothed

**114 returns (3.0%) are indexed by the IRS and absent from every archive it
publishes** — 102 from submission year 2017 and 12 from 2018. Those archive
sequences were probed to their first non-200 and are complete as published.
This is a source disagreement between the IRS's index and the IRS's archives,
and it is recorded per object id in `_xml_fetch_log.csv` as
`indexed_but_not_retrieved`.

### One provenance bug, found and fixed

A return can arrive by three routes — a range read, the DEFLATE64 recovery, or
a later pass over an unlisted archive — and only the first wrote the archive URL
into the fetch log. The other two left 433 retrieved returns still marked
`indexed_but_not_retrieved` with no URL, which would have published rows citing
no document. The `fetchlog` step re-opens the archives' central directories
(range reads, a few MB each) and writes each object id against **the archive
whose own namelist contains it**. Nothing is inferred.
**Retrieved returns without an archive URL: 0.**

---

## `schedc_expected` IS THE COLUMN THE DENOMINATOR DEPENDS ON

A 990-N filer reports gross receipts under $50,000 and nothing else. Zero
lobbying there is the **filing regime, not a finding**, and no such
organisation is counted as a zero anywhere in this build.

`data/clean/np_grantee_financials.csv` — **4,058 rows over all 927 EINs**:

| | rows | EINs |
|---|---:|---:|
| a return was retrieved and parsed | 3,697 | 566 |
| no return, but one could exist (`schedc_expected = 1`) | 51 | 51 |
| **no return could exist (`schedc_expected = 0`)** | **310** | **310** |

Why each of the 310 is excluded rather than zeroed:

| basis | EINs (of 927) | EINs (of the named 601) |
|---|---:|---:|
| no IRS Business Master File record and no e-filed return — outside the Form 990 universe | 300 | **153** |
| 990-N e-Postcard filer per the BMF filing requirement code | 5 | 5 |
| BMF records no filing requirement | 5 | 4 |

**The 153 figure reproduces `docs/PHILANTHROPY_DISCOVERY_LOG.md` exactly** —
"153 of 601 grantee EINs have no IRS Business Master File record at all, and
most were filed by the funder with IRC section `TRIBE`. An EIN present on a
Schedule I and absent from the BMF is a near-signature of a §7871 entity."
Two independent builds reaching the same 153 is a verification, not a
coincidence.

**Only 5 EINs are confirmed 990-N filers, and the reason that number is small
is itself the finding**: the BMF filing requirement code is only available for
the 110 grantees inside `np_orgs.csv`. For the other 491 there is no BMF record
to read a code from — which is the stronger fact, not a weaker one.

A further **50 EINs hold a BMF record but have no e-filed return indexed for
submission years 2017–2026.** Their filing regime is not established from any
source on disk. They are given `schedc_expected = 1` — the *conservative*
direction, because it makes the retrieval rate look worse rather than better,
and because it never manufactures a zero. Their `confidence` says exactly that.

---

## What was recovered

Across the 927 EINs, from returns retrieved here:

| | rows | EINs |
|---|---:|---:|
| Schedule C filed with the return | **376** | 65 |
| lobbying expenditure above zero | **302** | 53 |
| Part IX line 11d fees above zero | **180** | 36 |
| 501(h) electing (Part II-A completed) | 208 | — |
| non-electing (Part II-B completed) | 153 | — |

**$364,431,943** of lobbying expenditure and **$107,721,406** of Part IX line
11d fees, each with a source URL naming the archive and the return object id.

Restricted to the **601 named philanthropy grantees**: 189 Schedule C filings
over 38 EINs, 124 rows carrying lobbying expenditure over 28 EINs
(**$253,391,592**), and 63 rows carrying Part IX 11d fees over 17 EINs
($32,974,310).

Set against script 99's build, which reached 93 filed schedules and 43 rows
with a lobbying figure across the whole nonprofit corpus, the grantee list is
by a wide margin the more productive queue.

### The two columns are never added, and one filer shows why

The Nature Conservancy's TY2019 return reports **$8,086,325 on Schedule C Part
II-B and the identical $8,086,325 on Part IX line 11d**. Both were read
correctly; the filer reported the same figure on both lines. Adding them would
have produced $16.2M for an organisation that spent $8.1M. Schedule C counts
the organisation's **own** lobbying expenditure; Part IX line 11d counts fees
paid to **outside** lobbyists. They overlap without being the same quantity,
they keep separate columns, and neither is ever a fallback for the other.

### Names: 486 returns would have been truncated

IRS e-file splits a business name across `BusinessNameLine1Txt` and
`BusinessNameLine2Txt` at 35 characters. **486 of the 3,697 retrieved returns
(13.1%) carry a second line**, and reading only line 1 would have produced
`MINNESOTA INDIAN WOMENS SEXUAL ASSAULT` without its `COALITION`,
`AMERICAN INDIAN COMMUNITY HOUSING` without `ORGANIZATION`,
`INTERNATIONAL WILDERNESS LEADERSHIP` without `FOUNDATION INC`, and
`BOYS & GIRLS CLUBS OF THE LEECH LAKE` without `AREA INC`. Both lines are
joined before any name is used, which is the same fix
`docs/ADVOCACY_PASSTHROUGH_LOG.md` recorded for
`FOND DU LAC TRIBAL AND COMMUNITY` — a Minnesota **state** community college.

---

## THE CHAIN — 185 complete chains became 277

`data/clean/advocacy_passthrough_2026-08-07.csv`, 1,620 rows, 27 columns.
`advocacy_passthrough.csv` was **not** modified; the refreshed file is a dated
sibling and the original is byte-identical.

| `chain_completeness` | before | after |
|---|---:|---:|
| `FUNDING_AND_LOBBYING_BOTH_DOCUMENTED` | 185 | **277** |
| `FUNDING_ONLY` | 1,400 | 1,308 |
| `LOBBYING_ONLY` | 35 | 35 |

**92 `FUNDING_ONLY` rows became `FUNDING_AND_LOBBYING_BOTH_DOCUMENTED`**, over
**58 recipients** and **17 funders**, carrying $18,592,196 of grants. **All 92
flipped on the new 990 leg** — none on LDA.

### THE RESULT THAT MATTERS MORE THAN THE COUNT

> Before: **every one of the 185 complete chains was Tier B**, because the
> lobbying leg was an LDA name match and LDA publishes no EIN.
>
> After: **67 complete chains are Tier A.**

A chain reaches Tier A only when **both legs are keyed on the recipient's
EIN** — the grant line names the EIN on the funder's filed Schedule I, and the
lobbying figure comes from that same EIN's own filed Form 990. Nothing rests on
a name. That was structurally unreachable before this pull existed, and it is
the first time this layer produces rows that publish.

Lobbying sources across the 277 complete chains: LDA only 179, Schedule C 79,
Part IX line 11d 8, Schedule C + LDA 5, core-form indicator 5, Part IX + LDA 1.

The non-government subset — the cases Elijah's question is actually about, since
a tribal government's own lobbying is already visible in Cedar's LDA dataset —
grew from **36 to 128** complete chains: 72 `NONPROFIT_UNCLASSIFIED`, 30
`NATIVE_NONPROFIT`, 18 `MEMBERSHIP_ORGANIZATION`, 8 `TRIBAL_COLLEGE`.

---

## THE RULES, AND WHERE EACH IS ENFORCED

**1 — Nothing here says the grant paid for the lobbying.** Money is fungible
and most grants are restricted to program work. Whether a grant was restricted
is unobservable — Schedule I gives a purpose line, not the grant agreement.
Every row of both files carries, in words:

> "It does not state that the grant paid for the lobbying, and no column in
> this dataset supports that reading."

`same_year_flag` says only that a grant year and a lobbying year coincide.
85 of the 92 newly-completed chains carry it, and it is a coincidence of dates,
explicitly not an inference.

**2 — 990 lobbying is lawful, disclosed activity.** A 501(c)(3) may lobby
within limits and many elect 501(h) precisely to report it transparently — 208
of the rows here are from electing filers doing exactly that. No column, value
or note carries a pejorative framing. This documents a structure; it alleges
nothing.

**3 — Membership organisations are not a hidden channel.** Eleven target EINs
type `MEMBERSHIP_ORGANIZATION` from the spine's own `Intertribal Organization`
and self-governance-consortium classes. Five report lobbying on their own 990:
Native American Rights Fund ($139,660), the American Indian Higher Education
Consortium ($103,500), Kawerak Inc ($81,620), Maniilaq Association ($46,000)
and the Intertribal Timber Council ($36,318). Those rows carry:

> "Membership organisation: funded by its tribal members and advocating on
> their behalf is its stated purpose, not a concealed channel. **Membership
> dues are not a Schedule I grant and appear in no public filing**, so the
> ordinary way a tribe funds such a body is invisible by construction."

That last sentence is why NCAI, NIGA, USET, NAIHC and AFN sit in
`LOBBYING_ONLY` and will stay there. Presenting their advocacy as a concealed
pass-through would simply be wrong.

**4 — `serves_native_entities` is not `parent_native_entity`.** This build
writes **no relationship edge of any kind**. `bears_ownership` is imported from
`cedar_domain` and asserted against at module load, so the rule is enforced by
code:

```python
assert not bears_ownership("serves_native_entities")
assert not bears_ownership("affiliated_with")
assert not bears_ownership("member_of")
```

**The identifier ledger was not consulted.** Its EIN leg is a candidate list,
not an attribution: 1,085 of 1,104 rows carry `attribution_method = need_v6`,
which `cedar_domain.METHOD_ACCURACY` records at 6.5% accurate, and not one EIN
row in the file is `confidence_tier` A.

---

## THE FINDING THE 990 LEG MADE VISIBLE — a fiscal sponsor is not a Native org

The single largest lobbying figure this build recovered is **$43,568,567 on the
TY2024 Form 990 of NEW VENTURE FUND** (EIN 20-5806345), a Washington DC fiscal
sponsor with roughly $900M of annual expenses. The
philanthropy review queue proposes `NATIVE_ORG` for that EIN — and its own note
says why: the evidence is First Nations' grantee profile for **Alaska Native
Birthworkers Community**, a fiscally *sponsored project*.

**The project is Native. The legal person that received the money and filed
that return is not.** `docs/PHILANTHROPY_DISCOVERY_LOG.md` already named this
failure mode — "fiscally sponsored projects have no EIN and appear under the
sponsor's; the grantee named is not always the legal person paid" — and the 990
leg is the first thing to put a dollar figure on it. Attaching a $43.6M
national lobbying total to a Native organisation would be exactly the false
attribution this project forbids, and it is Guard 8 in a new place: a separate
legal person carrying another body's work.

Nothing was patched. Those rulings are tier B proposals awaiting Elijah and the
queue belongs to another build. Instead, **17 recipients whose Native typing
rests on an agent-proposed ruling AND which now carry a 990 lobbying figure
were pushed into the review queue with the dollar amount attached**, so the
question cannot be skipped. New Venture Fund is the largest; Sustainable
Economies Law Center ($103,856) and the Pennsylvania Coalition Against Rape
($71,242) are the same shape.

`np_grantee_financials.csv` itself is safe from this either way: it records
EIN-keyed filing facts and makes no claim about any organisation's Native
status. The risk lives entirely in the pass-through's `recipient_org_type`.

---

## Caveats that travel with every figure

- **The retrieval rate is 97.0% (3,697 of 3,811).** State it with any count.
- **114 returns are indexed by the IRS and absent from its archives** — 2017
  and 2018 submission years.
- **Schedule C uses the IRS definition and includes state and local legislative
  activity; LDA covers federal contacts only.** An organisation lobbying
  entirely at a state capitol is correctly on the 990 and correctly absent from
  LDA.
- **Tax years before 2015 have no machine-readable return at any URL.** The
  e-file index begins at submission year 2017.
- **The 501(h) election is derived, not read.** The election is made on Form
  5768 and Schedule C carries no element for it; what the XML shows is which
  part the filer completed, and only an electing organisation completes Part
  II-A.
- **Tribal governments are outside the 990 universe under IRC §7871.** They
  file no return, so no Schedule C exists for any of them.

## What remains structurally invisible

1. **Tribal government grantmaking.** §7871. SMSC's $400M and San Manuel's
   giving appear on no Schedule I anywhere, and 300 of the 927 target EINs have
   no BMF record at all.
2. **Membership dues.** No public filing carries them.
3. **Grants under $5,000** — Schedule I Part II has a floor.
4. **Grants to individuals** — Part III carries no names, which is why the
   scholarship funders returned zero rows in the philanthropy channel.
5. **Fiscally sponsored projects** — filed under the sponsor's EIN, so the
   organisation named is not the legal person paid. See the New Venture Fund
   finding above.
6. **Whether a grant was restricted** — Schedule I gives a purpose line, not
   the grant agreement.
7. **Lobbying below the LDA registration threshold and outside Schedule C's
   reporting triggers.**

## Pull discipline

`logs/_HOSTLOCK_apps.irs.gov.json` was claimed before every remote step and
released after each one; the lock was free (script 99 released it at 20:59 the
previous evening). Sequential, 1.0 s spacing on index files and 0.3 s on range
reads. **Zero refusals, zero throttles, zero edge blocks** — 3,630 successful
range reads across the two retrieval passes and no failed one.

**`api.usaspending.gov` was not touched — zero requests.** The prime-contracts
pull (PIDs 29036 / 30216, `code/44_pull_contracts_transactions.py pull`) was
live against that host throughout, verified with `Win32_Process`. No process
was killed and no `taskkill /F /IM python.exe` was issued.

## Files

| Path | What |
|---|---|
| `code/112_pull_grantee_990s.py` | the build |
| `data/clean/np_grantee_financials.csv` | 4,058 rows, 19 columns, 927 EINs |
| `data/clean/advocacy_passthrough_2026-08-07.csv` | 1,620 rows — the refreshed chain; the original file is untouched |
| `data/clean/codebook_master.csv` | +19 variable entries under `04d_grantee_990_financials` (variables only) |
| `review/grantee_990_unresolved_2026-08-07.csv` | 378 rows — 361 EINs with no retrievable return, 17 typing questions |
| `data/raw/external/irs990_grantee/` | 3,697 return XMLs, `_index_targets.csv` (4,021), `_xml_fetch_log.csv` (3,811), `_zip_manifest_extra.csv` |
| `logs/112_build_report_2026-08-07.txt` | the run report |

`np_financials.csv`, `np_orgs.csv`, `advocacy_passthrough.csv` and the spine
were **read only and are byte-identical after the run**.
`codebook_master.csv` was backed up to `codebook_master.csv.bak_2026-08-07_pre112`,
re-read immediately before the write, and only rows whose `dataset` is
`04d_grantee_990_financials` were replaced. Nothing written by another agent
was dropped, and nothing needed restoring (0 rows). Total rows 1,254 → 1,273.

## Regression check

`code/62_no_regression_check.py` before: **no regressions**, 39 metrics.
After: **no regressions**; `codebook_variables` 1,254 → 1,273,
`codebook_undocumented_public` 0.

## What would move this furthest next

1. **Rule the 17 typing questions**, starting with New Venture Fund. A single
   ruling there moves $43.6M out of a Native-organisation reading.
2. **Native American Agriculture Fund 990-PF Part XV** — the $266M Keepseagle
   corpus, still unparsed, and the one form the philanthropy channel cannot
   read. Unchanged from the last two logs and still the highest-value unworked
   funder.
3. **Extend the same queue to `np_financials`'s own 5,792-EIN Schedule-C-possible
   universe.** This build shows the retrieval rate is a function of queue
   completeness, not of access: 34.3% became 97.0% purely by fetching every
   indexed return rather than the latest one.
4. **Re-check the 2021–2026 archive listings for other unlisted files.** One
   was found for 2022 by comparing member counts against index row counts; that
   comparison is cheap and nobody had run it.
5. **Rule the 361 EINs with no retrievable return.** 300 of them have no BMF
   record at all, which is the §7871 signature and probably the most
   Native-dense group in the whole file.
