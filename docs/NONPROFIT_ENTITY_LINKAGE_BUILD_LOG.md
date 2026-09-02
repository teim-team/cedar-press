# NONPROFIT ENTITY LINKAGE BUILD LOG — the EIN hub

*Built 2026-08-26 by `code/167_link_nonprofit_family_via_ein_hub.py`.
Report: `logs/167_report_2026-08-26.txt`.*

**Numbering note.** This was written as `163_` and renumbered to `167_` mid-session,
because three other agents claimed 163 concurrently
(`163_promote_nho_universe_in_place.py`, `163_link_adjudication_hubs.py`,
`163_load_sam_contract_awards.py`). `ls code/<n>_*` before claiming a number.

---

## THE PROBLEM

Five nonprofit-family tables joined to nothing, despite a large part of their mass
being Native organisations by construction:

| table | rows | linked before |
|---|---:|---:|
| `np_orgs.csv` | 12,764 | 54 (`entity_id`) |
| `np_schedule_i_grants.csv` | 58,685 | 552 (`recipient_np_orgs_tribe_id`) |
| `np_schedule_i_filers.csv` | 10,314 | 1,652 (`filer_tribe_id_np_orgs`) |
| `np_financials.csv` | 8,507 | 0 — no entity column existed |
| `grantmaker_funding_flows.csv` | 18,656 | 0 — no entity column existed |

Every one of them is keyed on an **EIN**, and nobody had joined on it.

## THE RESULT

| table | rows | before | after | % |
|---|---:|---:|---:|---:|
| `np_orgs` | 12,764 | 54 | **1,456** | 11.4% |
| `np_schedule_i_filers` | 10,314 | 1,652 | **2,051** | 19.9% |
| `np_schedule_i_grants` (recipient) | 58,685 | 552 | **3,508** | 6.0% |
| `np_schedule_i_grants` (filer) | 58,685 | 0 | **2,872** | 4.9% |
| `np_schedule_i_grants` (**either side**) | 58,685 | 552 | **5,265** | 9.0% |
| `np_financials` | 8,507 | 0 | **2,815** | 33.1% |
| `grantmaker_funding_flows` (funder) | 18,656 | 0 | **0** | 0.0% |
| `grantmaker_funding_flows` (recipient) | 18,656 | 0 | **0** | 0.0% |

`np_orgs.entity_id` — the publishable key, which script 70 sets only at tier A —
rose **54 → 84**, additively, never overwriting a value script 70 wrote.
`62_no_regression_check.py` records `keyed_np_orgs rose 54 -> 84`, no regressions.

New tier distribution, at the row level:

| table | tier A rows | tier B rows |
|---|---:|---:|
| `np_orgs` | 84 | 1,372 |
| `np_schedule_i_grants` recipient | 1,802 | 1,706 |
| `np_schedule_i_grants` filer | 1,423 | 1,449 |

**Schedule I cash grants naming a linked Native recipient rose $144.2M -> $411.5M.**

## THE HUB — `data/clean/np_ein_entity_hub.csv`, 2,303 EINs

| tier | | class (from the SPINE row) | |
|---|---:|---|---:|
| A | 504 | tribe | 1,760 |
| B | 1,799 | native org | 381 |
| | | ANC | 88 |
| | | NHO | 74 |

Sources, by the row each link's tier was inherited from:

| source | EINs |
|---|---:|
| `np_orgs` (script 70's name pass) | 1,398 |
| `fac_tribal_single_audits` (script 147) | 786 |
| `nho_register` | 53 |
| `advocacy_passthrough` (script 111) | 32 |
| `bie_uio_identifier_links` (script 75) | 9 |
| `intertribal_orgs` register | 4 |
| `np_ein_uei_bridge` → ledger UEI leg | 3 |

208 EINs are corroborated by two or more independent Cedar tables. **That does not
raise the tier**, and the file says so on every row: two-leg promotion is a ledger
method (`agent_research_two_leg`), not a consumer's to mint.

### The best source in the build was already on disk

`fac_tribal_single_audits.csv` carries 843 distinct `auditee_ein` values keyed to
spine entities by script 147, and it is the strongest Native-status evidence in the
nonprofit family: **the auditee told the federal government it is an Indian tribe
or tribal organisation, and the EIN on the filing is its own.** It contributed
786 hub EINs, 2,533 Schedule I recipient rows and 27 `np_orgs` rows that no name
pass had reached — Little Priest Tribal College, Oglala Lakota College, Marty Indian
School Board, Nebraska Urban Indian Health Coalition, Lakota Fund, Native American
Lifelines.

---

## WHAT WAS REFUSED AS A LINK SOURCE, AND WHY

### 1. The identifier ledger's EIN leg. All 1,104 rows.

Measured 2026-08-26:

```
need_v6                 B 1,029 | C 1 | X 13      6.5% accurate (cedar_domain)
elijah_ruling           X 42                      EVERY ONE IS A NEGATIVE RULING
institution_exact_name  B 15 | C 3 | X 1
tier A                  ZERO
```

**Not one EIN row in the ledger is tier A, and every hand ruling on the EIN leg is
an exclusion.** Of the 1,011 positive ledger EINs that also sit in `np_orgs`, 599
propose a link `np_orgs` does not have:

```
ONONDAGA GOLF AND COUNTRY CLUB        -> Onondaga Nation
TUSCARORA GOLF CLUB INC               -> Tuscarora Nation
LENAPE VALLEY SOCCER CLUB INC         -> Lenape Indian Tribe of Delaware
AKWESASNE BOYS & GIRLS CLUB           -> St. Croix (WISCONSIN)
ONONDAGA COMMUNITY COLLEGE FOUNDATION -> Onondaga Nation
```

The ledger's EIN leg therefore enters this build **only through its 56 tier-X rows,
as exclusions.** Its 1,044 positive rows are not imported in either direction — not
as links and not as conflicts, because a 6.5%-accurate disagreement is not evidence
about the row it disagrees with, and 97 such disagreements in a review queue is 97
ways to spend a person's attention on `need_v6`.

> **FIXED 2026-08-26, and the count below was understated.** See
> "THE 148 TRAP IS CLOSED" at the foot of this file. The ledger holds **317**
> `elijah_ruling` EIN rows carrying a `tribe_id`, not 42, and every one is
> tier X. **`code/293_lint_bug_classes.py` is the standing detector**
> (`--class 3` for this class in full); it re-derives the number rather than
> quoting it. `code/248_audit_tier_inheritance_patterns.py` was a second
> detector for the same class and is **RETIRED as of 2026-08-26** — a stub that
> points at 293 and exits non-zero. Today's figure from 293:
> **380 rows a `ruled method → tier A` consumer would over-state, 344 of them
> tier X (EIN 317 · UEI 22 · CAGE 5).**

**A REAL TRAP, still live in `code/148_resolve_schedule_i_recipients.py`.** That
script contains

```python
RULED = {"hand", "bgov_manual", "elijah_ruling", ...}
tier = "A" if meth in RULED else (r.get("confidence_tier") or "B")
```

`elijah_ruling` on the EIN leg is *always* tier X. That line promotes 42 negative
rulings to tier A — `COLVILLE ROTARY CHARITABLE FOUNDATION` → Confederated Colville,
`KIOWA COUNTY FARM BUREAU` → Kiowa Tribe, `COWLITZ COUNTY DIVE RESCUE ASSOCIATION`
→ Cowlitz — and would publish them. The lesson AGENTS.md draws from the United Way
case ("a tier is inherited, never assigned") has a second half: **a RULED method is
not automatically a POSITIVE ruling.** Check the sign of the ruling before you
inherit its authority. Script 148's proposals in
`review/np_schedule_i_recipients_2026-08-12.csv` are unruled and should not be
applied without this fix.

### 2. `np_ein_uei_bridge.csv`'s `tribe_id_token_match` column

`UNITED HOUMA NATION INC` → *United Auburn*. `MACHIS LOWER CREEK INDIAN TRIBE OF
ALABAMA` → *Confederated Coos*. `DOUGLAS-CHEROKEE ECONOMIC AUTHORITY` (Tennessee)
→ *Douglas* (Alaska). `KICKAPOO TRIBE OF OKLAHOMA` → *Kickapoo Tribe in Kansas*.
Not used.

**What that file IS good for is its other identifier.** `EIN → UEI` is real, and the
ledger's UEI leg is a different and far better population (`cluster_v3`, 97.7%
accurate). 24 of its 28 UEIs resolve there, and the UEI answer **corrects the token
column** on both Houma (→ `TRBS-UHOUMA-00`) and Kickapoo (→ `TRBF-KCKPOK-00`).

### 3. Any name path other than exact / alias / core

Containment has failed ten documented ways in this repo and nonprofit names are
where it lands. This build's name pass is deliberately narrower than script 148's,
which used containment and a distinctive-token path. Guards, all pre-existing:
`NAME_TRAPS` (a whole-name match carrying a trap needs state agreement),
`PLACE_SUFFIXES`, state disagreement, and the organisation-type bar from script 65 —
applied *after* resolution, so the queue records only bars that actually stopped a
match.

The name route produced 640 row-links across the five tables (517 in the grants
file, 86 filers, 37 financials), and they read correctly:
tribal colleges, Alaska Native village governments, and — new since the spine's NHO
class grew from 31 to 210 this afternoon — Hawaiian organisations the diacritic fold
handles: `AHA PUNANA LEO` → ʻAha Pūnana Leo, `MALAMA LOKO EA FOUNDATION` → Mālama
Loko Ea Foundation, `KAKOO OIWI` → Kākoʻo ʻŌiwi, `PAI FOUNDATION` → PAʻI Foundation.

---

## `grantmaker_funding_flows.csv` LINKS TO NOTHING, AND THAT IS THE RIGHT ANSWER

The task premise was that "a grantmaker and its grantees are BOTH potentially native
entities." **For this file that is false by construction, and forcing it would have
been the worst error available here.**

The 14 funders are the conservative-foundation panel script 140 assembled to test
whether the funders of anti-ICWA litigation also fund Hoover and Mercatus: John
Templeton, DonorsTrust, Charles Koch (×3 vehicles), Lynde and Harry Bradley, F M
Kirby, Adolph Coors, Sarah Scaife, Diana Davis Spencer, Searle Freedom Trust, Ed
Uihlein, Donors Capital, The JM Foundation. **Not one is a Native entity**, and
`recipient_target_key` points at tracked policy institutions, not at the spine.

Both sides were nevertheless checked, because refusing without measuring is not a
finding:

- **14 of 14 funder EINs**: absent from `np_orgs`, absent from the ledger, no spine
  name match. Zero links.
- **6,937 distinct recipient names / 1,424 recipient EINs**: zero deterministic spine
  matches. 6,571 names return `no_spine_match` outright. The 325 near-misses are all
  the containment defect — `Baca`, `Clark`, `Cook`, `Salmon`, `Town`, and
  `American Council of Trustees and Alumni` / `American Legislative Exchange Council`
  colliding with the spine's single-word entity **Council** (`AKNF-COUNCL-00`, the
  Native Village of Council) and **Council Native Corporation**. Every one refused.
- Exactly **one** recipient EIN sits in the nonprofit exclusion rulings and is
  blocked there.

**A trap worth recording:** in this file `IHS` is the **Institute for Humane Studies**,
not the Indian Health Service. It is the third most common `recipient_target_key`.

---

## WHAT WENT TO REVIEW RATHER THAN BEING FORCED

| file | rows | what it holds |
|---|---:|---|
| `review/np_ein_hub_conflicts_2026-08-26.csv` | 33 | one EIN, two Cedar tables, two different entities |
| `review/np_ein_hub_exclusion_hits_2026-08-26.csv` | 33 | an EIN a ruling forbids, that some table still links |
| `review/np_name_candidates_2026-08-26.csv` | 3,294 | names refused by the name pass |

143,735 row-instances were left unlinked with **no spine candidate at all** — ordinary
charities present only because a Native filer gave to them. Leaving them alone is the
point; a false positive here manufactures a Native grant relationship that does not
exist.

### Conflicts: 18 auto-resolved by specificity precedence, 15 refused

Where exactly one candidate is supported by a deterministic method (exact / core /
alias) and every rival rests only on containment, the deterministic one wins. This is
not a new judgement — it is AGENTS.md's own repair for the containment defect
("require the record to be at least as specific as the entity"), applied to two
answers that already exist.

It matters because the losing side is always the same defect, **the program entity
booked to its parent government**:

```
RED LAKE NATION COLLEGE        np_orgs: Red Lake Band      FAC: Red Lake Nation College
COLLEGE OF THE MENOMINEE NATION np_orgs: Menominee Tribe    FAC: College of Menominee Nation
LAC COURTE OREILLES OJIBWE UNIV np_orgs: Lac Courte Oreilles FAC: LCO Ojibwe University
WHITE EARTH TRIBAL & COMM COLL  np_orgs: White Earth        FAC: White Earth TCC
TURTLE MOUNTAIN COLLEGE         np_orgs: Turtle Mountain    FAC: Turtle Mountain College
MAKAHA HAWAIIAN CIVIC CLUB      np_orgs: "Hawaiian Native Corporation"  NHO reg: Makaha Hawaiian Civic Club
```

That last one is the Department of Hawaiian Home Lands trap from `START_HERE.md`,
arriving through a different door.

The 15 refusals are the cases where **both** candidates rest on containment and
precedence cannot separate them — `QUILEUTE TRIBAL SCHOOL` (Quileute Tribe vs
Quileute Tribal School), `STANDING ROCK COMMUNITY GRANT SCHOOL`, `SAN CARLOS APACHE
COLLEGE`, `RAMAH NAVAJO SCHOOL BOARD`. Each is almost certainly the specific
institution; none is written.

### 27 links a ruling already forbids are STILL IN `np_orgs.tribe_id`

Of the 33 exclusion hits, **27 are links `np_orgs` already carries**:

```
COLVILLE ROTARY CHARITABLE FOUNDATION  tribe_id = TRBF-COLVLL-00
KIOWA COUNTY FARM BUREAU ASSOCIATION   tribe_id = TRBF-KIOWAT-00
COWLITZ COUNTY DRUG COURT FOUNDATION   tribe_id = TRBF-COWLTZ-00
CHICKASAW COUNTY HISTORICAL SOCIETY    tribe_id = TRBF-CHKSWN-00
JEMEZ MOUNTAINS ELECTRIC FOUNDATION    tribe_id = TRBF-JEMEZP-00
```

Every one is an Elijah `elijah_ruling` tier-X row in the ledger. **They were not
overwritten**, because `tribe_id` is script 70's column and patching another script's
output is how the `09_import_rulings.py` regression happens. Instead this build's
`cedar_link_tier` is `X` on those rows with the ruling quoted in `cedar_link_basis`,
and all 33 are in the review file with the exact correction.

**Follow-up, cheap and worth doing:** feed those 27 through
`code/124_apply_rulings_in_place.py` so the ruling clears `tribe_id` at source, or add
the exclusion check to script 70's nonprofit pass, which currently consults
`excluded_by_prior_ruling` and `funnel_stage` but not the ledger's tier-X EIN leg.

### Name candidates are triaged, because 2,463 containment refusals bury the rest

`triage` is `PLAUSIBLE` (1,060) where the name carries a word occurring in exactly one
spine entity and not in `NAME_TRAPS`, and `CONTAINMENT_NOISE` (2,234) otherwise.
**Triage is not a match and never creates a link** — it exists so the queue is
readable.

---

## WHAT WAS WRITTEN, AND HOW

- **`data/clean/np_ein_entity_hub.csv` is the durable artefact.** The five tables are
  rebuilt from their own inputs by scripts 132/140 and appended columns would be
  destroyed on the next run — the `09_import_rulings.py` failure shape, which script
  148 refused in-place writing for exactly this reason. The hub survives that: re-run
  this script after any rebuild and the links come back.
- The five tables additionally carry namespaced columns, backed up first
  (`*.csv.bak_2026-08-26_pre167`), written `.part` then renamed.
- Columns are `cedar_[side_]spine_entity_id`, `…spine_canonical_name`,
  `…spine_entity_class`, `…native_entity_class`, `…link_tier`, `…link_basis`,
  `…link_key`, `…link_sources`.
  **`spine_entity_id`, deliberately not `entity_id`.** The spine's own
  `cedar_entity_id` is a different identifier system — a short public code (T-, A-,
  N-, E-, I-, NP-) — and reusing that name for a `tribe_id` would invite a join
  between two things that are not the same key. Same reason `link_tier` is not
  `entity_tier`: `np_orgs` already carries `entity_tier` from script 70.
- `link_key` says which key carried the link: `EIN <n>` or `NAME <string>`.
- Codebook **fragment** at `data/clean/codebook/06b_np_entity_hub.csv`, 72 variables
  across six datasets. `codebook_master.csv` was not touched.

## CAVEATS THAT TRAVEL WITH THE OUTPUT

- **A blank link is not "not Native."** 6,453 of the 12,764 organisations are 990-N
  filers reporting no financial detail at all. Zero lobbying or zero revenue on those
  rows is the filing regime, not a finding.
- **A Schedule I row proves money moved.** It does not prove what the money paid for,
  and it does not make either party Native.
- **An EIN-keyed filing fact says nothing about the Native status of the filer** — the
  New Venture Fund rule. A fiscal sponsor holds the EIN and files the return; the
  sponsored project has no separate legal existence.
- `cedar_link_tier = X` means an existing ruling forbids a link on that EIN and the
  row is deliberately left unlinked. It is not a missing value.

## THE GUARD

`62_no_regression_check.py` after this build: no regressions attributable to it,
`keyed_np_orgs rose 54 -> 84`. The one failing invariant,
`codebook_undocumented_public = 45`, is **not from this build** — all 45 rows are
`dataset = 07o_nigc_declinations`, generated 2026-08-26 by another agent. All 56
`cedar_*` variables from this build carry descriptions and `published = 0`.

## CONCURRENCY NOTE

The spine grew **1,310 → 1,489 during this session** (`163_promote_nho_universe_in_place.py`
added 179 NHOs, taking that class from 31 to 210). Nothing here writes to the spine;
it is read once per run. Re-running this script after a spine change is safe and
picks the new entities up — the NHO hub links rose from 27 to 74 on exactly that.

---

## THE 148 TRAP IS CLOSED, AND THE 27 FORBIDDEN LINKS ARE GONE (2026-08-26, evening)

Both follow-ups this log left open were done. Scripts `248`–`251`.

### 1. The 148 trap — fixed, and the count was 317, not 42

This log said *"That line promotes 42 negative rulings to tier A."* Re-measured
against the live ledger the same evening — `code/248_audit_tier_inheritance_
patterns.py` re-derives it rather than quoting it:

```
EIN rows in cedar_identifier_ledger_final.csv   1,104
...tier A                                           0
...`elijah_ruling`, ALL TIER X                    317
```

**317.** The ledger has grown since this log was written (20,559 -> 20,577 rows)
and `elijah_ruling` X rows on the EIN leg with a `tribe_id` now number 317. The
shape of the finding was exactly right; only the magnitude was understated. Tier
X `elijah_ruling` rows across all identifier types: EIN 317, UEI 22, CAGE 5.

**The fix.** The tier is inherited verbatim; a tier-X row is loaded as an
EXCLUSION on the `(EIN, entity)` pair rather than as a link. Verified end to end
on a full `--check` run:

| | before | after |
|---|---:|---:|
| tier-A proposals | 317 (all exclusions) | **0** |
| EINs carrying an exclusion | 0 (ignored) | **319** |
| name-path matches refused by a ruling | 0 | **4** |

Zero tier-A proposals is the *correct* state and the script now says so in its
own output: not one EIN row in the ledger is tier A, so a tier-A proposal here
would have to come from a tier-A source row, and there are none.

**The corollary, and why it needed its own guard.** Blocking the EIN route alone
hands the same bad match straight back through the name resolver. Four real
cases, caught by the run:

```
COWLITZ CHILD ADVOCATES            -x- Cowlitz     (name/resolver)
FISH OF COWLITZ COUNTY             -x- Cowlitz     (name/resolver)
Onondaga Environmental Institute   -x- Onondaga    (name/resolver)  x2
```

The exclusion is **not** a blanket block on the EIN. The ruling says this EIN is
not THAT entity; another entity is still reachable. Over-blocking would suppress
a correct attribution, which is why `169_build_identifier_graph.py` makes
corrections repoint rather than blacklist.

`review/np_schedule_i_recipients_2026-08-12.csv` predates the fix and must not
be applied. Re-run 148 and use its output.

**And that queue has a second problem, measured while checking the first: 30 of
its 2,138 rows ask the owner about an EIN he has already ruled tier X.**
`UNITED WAY OF THE GREATER CHIPPEWA VALLEY` — the case AGENTS.md is built
around — is in there, alongside seven Yavapai-area organisations, PAWNEE VALLEY
COMMUNITY HOSPITAL (twice, once misspelled `PAWWNEE`), ONONDAGA ENVIRONMENTAL
INSTITUTE and LEGACY TRADITIONAL SCHOOL - PEORIA. All 2,138 rows are `UNRULED`
and **all 30 of these carry a blank `proposed_entity_id`**, so the queue asks an
open question about an organisation that is already settled. None proposes the
exact entity the ruling forbids, so nothing here would have reversed a ruling by
itself — but re-asking a settled question spends the one resource this project
cannot buy more of, and an answer given twice is an opportunity to disagree with
itself. A ruling queue should subtract the ledger's tier-X rows before it is
shown to anyone.

### 2. A SECOND defect in 148, found while fixing the first: the dollar column does not exist

148 summed `cash_grant_amount` / `total_cash_grant_usd`. **`np_schedule_i_grants.
csv` carries neither.** The real column is `cash_grant_usd`. So every proposal
carried `$0.00`, the run reported *"dollars represented: $0.0M"*, and — the part
that mattered — `props.sort(key=-total_cash_grant_usd)` **sorted a 5,746-row
review queue by a constant**. The largest grant relationships were not at the
top and nothing said so.

This is AGENTS.md standing rule 8 in a new place: *"An absent column name reads
as an empty source... a coverage computation must RAISE on a missing column,
never print a zero."* Script 102 printed 0.0% coverage for 19 days on the same
shape. 148 now **raises** on a missing dollar column instead of falling back to
zero.

Confirmed on a full re-run: *"dollars represented: **$4,198.1M**"*, against
$0.0M before. Same run, both fixes together — **5,780 proposals, tier A 0**,
319 exclusions honoured, 4 name-path refusals ($0.4M).

**And repairing the sort immediately earned its keep, by exposing what sits at
the top of the queue.** With the rows finally ordered by dollars, the twelve
largest proposals are almost entirely the containment defect:

```
$126.88M  SAVE THE CHILDREN               -> Chickasaw Children's Village
$262.69M  LA COASTAL PROTECTION & RESTOR. -> Cherokee Fire Protection, Llc
$110.36M  SOUTHWEST RESEARCH INSTITUTE    -> Southwest Native Asset Coalition
$ 58.88M  MS DEPT OF ENVIRONMENTAL QUALITY-> National Tribal Environmental ...
$140.37M  MCHS--SOUTHEAST MINNESOTA REGION-> Cook Inlet Region, Incorporated
```

`SAVE THE CHILDREN -> Chickasaw Children's Village` is the *exact* pairing
AGENTS.md names as the containment defect's direction-1 case, the one that
booked $2.8B onto a school. **Every one is tier B and none publishes**, which is
the system working. But it means the top of this ruling queue is nearly all
noise, and for four months nobody could see that, because the ordering column
was a constant zero. **A queue sorted by a broken key does not look broken - it
looks arbitrary, and arbitrary looks like unsorted data rather than a bug.**
Triage this queue by refusing the containment rungs before it goes to a human,
not by asking a human to wade through them.

### 3. The 27 forbidden links in `np_orgs.tribe_id` — applied, both halves

This log's own follow-up read: *"feed those 27 through
`code/124_apply_rulings_in_place.py` so the ruling clears `tribe_id` at source,
or add the exclusion check to script 70's nonprofit pass."* **Both were done,
because either alone leaves the defect live.**

- **`70_key_unjoined_datasets.py` now defers to the ruling at source.** New
  `ledger_negative_ein_rulings()` reads the ledger's tier-X EIN leg, and
  `do_np_orgs` blocks on it before any name resolution. That is what survives a
  rebuild: `17_build_nonprofit_990.py` rebuilds `np_orgs.csv` from the IRS BMF
  and re-derives `excluded_by_prior_ruling` from its own exclusion file, so an
  in-place patch alone would have been reverted the next time 17 ran.
- **`code/251_apply_np_ein_exclusions_to_np_orgs.py`** applied the same decision
  to the live file, on those 27 rows only. A narrow write, because re-running 70
  is a whole-file re-key against a spine that has grown 1,310 -> 1,534 since it
  last ran — the "re-running 57 loses work" trap.

**What the 27 look like, and why the refusal was never close.** Every one
arrived by `containment` **with a state conflict already recorded on its own
row** — `resolver_containment;state_conflict:KS!=OK`, `IA!=OK`, `CO!=OK` — and
every one carries a ledger row that is tier X via `elijah_ruling` reading,
identically on all 27: *"Ruled by Elijah 2026-08-12: not a Native entity."*

Written on those rows, with provenance: `tribe_id` and `tribe_canonical_name`
cleared, `entity_tier = X`, `entity_match_method = ruled_not_a_native_entity`,
`excluded_by_prior_ruling = 1`, `funnel_stage = ruled_not_native`,
`confidence_tier = X`, `classification_ruling = place_name_coincidence`, and
`entity_match_basis` / `exclusion_reason` carrying the ruling verbatim with its
source. `review/np_orgs_exclusions_applied_2026-08-26.csv` records what each row
held before.

**Deliberately NOT cleared:** `tribe_id_token_match` and
`canonical_name_token_match`. The evidence of what was matched — and the state
conflict that should have stopped it — stays on the row. A correction is made,
never erased.

**`entity_id`, the publishable key, was blank on all 27**, because 70 writes it
only at tier A and these sat at B. So the forbidden links were never publishing;
they were live in a shipping column, which is a different and still unacceptable
thing. `251` asserts the blank rather than assuming it and refuses outright if a
forbidden link is ever found in `entity_id`.

**Only the blanket-negative grammar blocks.** *"not a Native entity"* is a ruling
about the ORGANISATION. Where a ruling names a different owner the correct
handling is a REDIRECT and never a block, so `251` requires that grammar and
leaves redirects to the appliers that own them.

### A latent defect this work surfaced, recorded not fixed

`169_build_identifier_graph.py` decides "ruled Native" as

```python
if classification_ruling not in ("", "UNRULED", "place_name_coincidence"):
    np_ruled_native.add(ein)
```

An **allow-list of negatives** — the wrong polarity. Any new negative-ruling
token silently becomes *ruled Native*. Writing `not_a_native_entity` here, the
obvious value, would have done exactly that; `251` reuses the existing
`place_name_coincidence` token instead. 169 belongs to its own pass.

---

## UPDATE 2026-09-02 — `name_match_support` was scored against a different tribe, and the EASTERN remedy is 13 redirects

*`code/1101_np_keyed_name_support.py`. Full write-up:
**`docs/ENTITY_LAYER_DEEPENING_2026-09-02.md`** section 5.*

**1. The fourteenth instance of this repo's signature defect.** `code/952`
documents `name_match_support` as *"the match shares NO token with the canonical
name shown"* and computes it as
`support(org_name, canonical_name_token_match)`. **That column holds the
TOKEN-MATCH FUNNEL's candidate, not the tribe the row is keyed to.**

```
EIN 873791650  CAHUILLA ELEMENTARY PARENT TEACHER ORGANIZATION
  tribe_id                    TRBF-CHLLAB-00   Cahuilla
  canonical_name_token_match  Agua Caliente        <- scored against THIS
  name_match_support          no_shared_token_with_canonical_name
```

Over the 1,423 live-keyed rows the two names disagree on 288 and
`canonical_name_token_match` is blank on 585. Recomputed against the tribe
actually cited: **1,421 of 1,423 share a token; 2 do not.**

So ~~"2,268 rows share no token at all with the canonical name they cite (541
live)"~~ is correct about the funnel and wrong about the live attributions —
1,594 of the 2,268 are already `excluded_by_prior_ruling`, only **71 carry a
live key**, and all 71 DO share a token with the tribe they cite. 952's column
is **not overwritten**: it is right within its own slice, and the new
`name_match_support_measured_against` says on the row which name it was scored
against.

**2. The 71 are not vindicated.** Every one shares a distinctive token that is a
PLACE NAME — `OLD PROS OF LAGUNA WOODS VILLAGE`, `FIRST NATIONAL BANK IN
WICHITA CHARITABLE TRUST`, `WESTERN DAKOTA ESTATE PLANNING COUNCIL INC`. The
flag found the wrong rows for the wrong reason, and the rows it should have
found were labelled `distinctive_token`, which reads as supported.

**3. 461 of 1,423 live keys are the Umatilla defect.**

```
SUPPORTED                     888   62.4%
HELD_STATE_DISAGREES          461   32.4%     50 of them NATIVE_VERIFIED_STRICT
REFUSED_GENERIC_TOKEN_ONLY     61    4.3%
REDIRECT_PROPOSED              13    0.9%
```

`ISLAMIC ASSOCIATION OF MID KANSAS AT WICHITA KANSAS` to Wichita (OK);
`WINNEBAGO PORK PRODUCERS` (IL) to Winnebago (NE); `IRON CROW THEATRE COMPANY`
(MD) to Crow (MT). Concentrated on six nations whose names are also American
place names: Crow 63, Pueblo of Laguna 61, Fond du Lac 58, Seneca 53,
Winnebago 26, Wichita 22. The existing `placename_risk_flag` reaches **160 of
the 461** — 301 are newly flagged — and it fires on 202 rows this pass calls
SUPPORTED, so neither measurement supersedes the other.

**4. A redirect, not a block.** `EASTERN CHEROKEE SOUTHERN IROQUOIS AND UNITED
TRIBES OF SOUTH CAROLIN` (SC) was keyed to **United South and Eastern Tribes**
and redirects to **`TRBS-ECSIUT-00`**, which is in the spine, in SC, and
accounts for every distinctive word — the filing's own truncation `CAROLIN` is
handled by rule 7's existing spelling-variant allowance (`RESERVATI`). Twelve
more redirects came with it, including all five Native Hawaiian organisations
keyed to the junk `Hawaiian Native Corporation`, `AMERICAN INDIAN COUNCIL ON
ALCOHOLISM INC` keyed to **Council Native Corporation** (an Alaska village
corporation — the `code/610` defect, redirected instead of merely refused), and
six tribal colleges, loan funds and clinics keyed to their NATION rather than to
themselves.

The other two EASTERN rows are **HELD with the spine gap stated** — no
alternative exists in their state: `WIQUAPAUG EASTERN PEQUOT INDIAN TRIBE` (RI,
keyed to the Eastern Pequot Tribal Nation of **CT**) and `EASTERN BAND OF
CHICKASAW INDIANS FOUNDATION INC` (TN, keyed to The Chickasaw Nation of **OK**).
Both keep their Native status: a refusal says only *this is not THAT entity*.

**The rule the tightening earned.** The first version proposed **37** redirects
and six were wrong the same way — one-way containment onto a longer name
(`LUMBEE NATIONS INC` to Lumbee Guaranty Bank, `THE CHEHALIS FOUNDATION` to
Chehalis Tribal Loan Fund, `ALASKA NATIVE TRIBAL HEALTH CONSORTIUM` to
Southeast Alaska Regional Health Consortium). **Requiring the match to hold in
BOTH directions killed all six and cost none of the 13.**

Nothing was blanked (`code/610`'s convention): `tribe_id`, `cedar_uid` and
`disposition` are untouched, asserted by an md5 over all 57 base fields.
`review/np_live_key_review_2026-09-02.csv`.
