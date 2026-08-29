# Nonprofit advocacy pass-through — build log, 2026-08-07

Build script: `code/111_build_advocacy_passthrough.py`
Output: `data/clean/advocacy_passthrough.csv` ·
`review/advocacy_passthrough_unresolved_2026-08-07.csv` ·
`logs/111_build_report_2026-08-07.txt`

Spec: `docs/LOBBYING_EXPANSION_RECONCILIATION.md` ·
inputs from `docs/PHILANTHROPY_DISCOVERY_LOG.md` (funding leg) and
`docs/EARMARKS_SCHEDC_BUILD_LOG.md` (990 lobbying leg).

---

## The question this layer answers

Elijah, 2026-08-07:

> "i imagine the nonprofit data could hide lobbying — like it's funded by a
> Native entity and the funding passes through the nonprofit. that should be
> investigated."

Every advocacy dataset Cedar holds asks **"did this tribe lobby?"** — the LDA
build is keyed to tribes, ANCs, villages and consortia, and answers that
question well. The pass-through question is a different one: **did money from a
Native funder reach an organisation that lobbied?** That is invisible to all of
them, because the LDA client is the nonprofit, not the funder, and no single
source carries both facts.

```
Native funder
    → funds        (Form 990 Schedule I Part II cash grant)
        → nonprofit / intertribal organisation
            → lobbies   (990 Schedule C, Part IX line 11d, or an LDA filing)
```

Both legs are retrieved facts with their own source documents. The chain is the
finding.

**Zero remote requests were made.** Every input was already on disk: the
philanthropy Schedule I pull (script 75), the IRS e-file return cache (script
99, 6,870 XMLs), the LDA corpus (`code/lobbying_pull/raw_filings.jsonl`), the
spine, the ledger and the nonprofit files. No host lock was needed or claimed.

---

## THE FOUR RULES, AND WHERE EACH ONE IS ENFORCED

**1 — Never assert the grant paid for the lobbying.** Money is fungible and
most grants are restricted to program work. There is no causal column. Every
row carries, in `evidence_note` and in words:

> "This row records that a funding relationship and a lobbying activity both
> exist, each with its own source document and date. It does not state that the
> grant paid for the lobbying, and no column in this dataset supports that
> reading."

`same_year_flag` says only that a grant year and a lobbying year coincide, and
the codebook entry says so. Whether a grant was *restricted* is unobservable —
Schedule I gives a purpose line, not the grant agreement — and no row claims
otherwise.

**2 — Membership dues are not a grant, and an intertribal organisation is not a
hidden channel.** `recipient_org_type = MEMBERSHIP_ORGANIZATION` is taken from
the **spine's own `Intertribal Organization` and self-governance-consortium
classes**, not compiled here. Those rows carry:

> "Membership organisation: funded by its tribal members and advocating on
> their behalf is its stated purpose, not a concealed channel."

The two **constituency** classes were deliberately excluded from that mapping
after the first run typed them wrongly: `Fond du Lac` (Federal-level
constituency entity) is a component band of the Minnesota Chippewa Tribe and
`Schaghticoke Tribal Nation` (State-level constituency entity) is a tribe. Both
are governments. They now type as `TRIBAL_GOVERNMENT_CONSTITUENT`.

**3 — 990 lobbying is legitimate, disclosed activity.** A 501(c)(3) may lobby
within limits and many elect 501(h) precisely to do it transparently. No
column, value or note carries a pejorative framing; rows with a lobbying
observation carry the sentence explicitly.

**4 — `serves_native_entities` is not `parent_native_entity`.** This build
writes **no relationship edge of any kind**. `bears_ownership` is imported from
`cedar_domain` and asserted against at module load, so the rule is enforced by
code rather than by memory:

```python
assert not bears_ownership("serves_native_entities")
assert not bears_ownership("affiliated_with")
assert not bears_ownership("member_of")
```

---

## The funding leg — two sources, one admission standard

| Source | Rows in | What it is |
|---|---:|---|
| `data/raw/external/philanthropy/schedule_i_grantees_2026-08-06.csv` | 1,053 | Schedule I Part II of 7 Native grantmakers, 2 tax years each |
| Schedule I parsed out of the 6,870 cached IRS e-file returns | 5,630 recipient lines from 1,205 returns, 477 filers | new in this build; local files, no network |

The second source is the one that reaches **tribal and intertribal
grantmakers** — Tulalip Foundation, Osage Nation Foundation, Kake Tribal
Heritage Foundation, Alaska Native Tribal Health Consortium, Council for Native
Hawaiian Advancement, Northwest Portland Area Indian Health Board, Inter-Tribal
Council of Arizona, National Indian Health Board. None of those appears in the
philanthropy channel.

### A funder enters only on documented Native evidence

A name is never evidence on its own. Four admissible routes, ranked:

1. the funder's own filed Schedule I in the documented philanthropy channel;
2. guarded resolution to the spine (all eight guards below);
3. an `np_orgs.csv` classification ruling of `native_controlled`,
   `tribally_controlled` or `native_serving`;
4. an agent-proposed ruling of `NATIVE_ORG` / `ALREADY_IN_SPINE` from the
   philanthropy review queue — **tier B, awaiting Elijah**.

Hard refusals first: an EIN ruled `place_name_coincidence` or carrying
`excluded_by_prior_ruling = 1` in `np_orgs.csv` is refused whatever else says.

### THE IDENTIFIER LEDGER'S EIN LEG WAS REFUSED WHOLESALE

The first draft admitted `cedar_identifier_ledger_final.csv` EIN rows as
Native-funder evidence. Measured on the output, that produced:

| Filer | Keyed to | Trap |
|---|---|---|
| UNITED WAY OF CAYUGA COUNTY INC | United Auburn | `united` |
| UNITED WAY OF THE GREATER CHIPPEWA VALLEY | United Auburn | `united` |
| YAVAPAI COMMUNITY HOSPITAL ASSOCIATION | Yavapai-Apache | place name |
| PAWNEE VALLEY COMMUNITY HOSPITAL | a tribe | place name |
| UMATILLA ELECTRIC COOPERATIVE | a tribe | place name |
| FIRST UNITED METHODIST CHURCH OF PEORIA | a tribe | `united` / place name |

**1,085 of the ledger's 1,104 EIN rows carry `attribution_method = need_v6`,
which `cedar_domain.METHOD_ACCURACY` records at 6.5% accurate. Not one EIN row
in the whole ledger is `confidence_tier` A** — they are 1,044 B, 4 C and 56 X,
and X is a negative ruling that must never resurface. The route was removed
entirely. This is worth recording as a standing fact about that file: **its EIN
leg is a candidate list, not an attribution.**

---

## The lobbying leg — and the file that turns out not to contain nonprofits

Three observation types were sought per recipient:

| Leg | Source | Key |
|---|---|---|
| Schedule C | `np_financials.csv` (36 columns from script 99) | EIN |
| Part IX line 11d | same | EIN |
| LDA filings | `code/lobbying_pull/raw_filings.jsonl`, 39,448 filings | client name |

**`native_entity_lobbying_disclosures.csv` was measured and found to be keyed
to governments only.** Its 27,796 filings resolve to `TRBF` (23,942), `ANRC`
(2,002), `AKNF` (587), `SGVF` (238), `TRBS` (100), `CNSF` (72) and `CNSS` (14).
**Zero of the spine's 55 Intertribal Organizations have a row in it.** NCAI,
NIGA, USET, NIHB, NARF, NAIHC and NCUIH are absent from Cedar's Native LDA
slice entirely — they sit in `lobbying_unmatched_clients.csv` instead. So the
recipient side of this build had to read the **raw** LDA corpus, where those
organisations are clients under their own names.

That is itself a finding about the existing dataset, and it is the reason the
pass-through layer is not redundant with it.

`bills_lobbied` is parsed from each filing's own specific-issue text with a
**case-sensitive** prefix, because a case-insensitive `S` matched the year in
`is 2024`. `agencies_contacted` is the filing's `government_entities` list.

**LDA client state is the filing address, not the client's.** Measured on the
25,719 already-keyed Cedar rows that carry both, client state and entity state
agree on 91.8% — and 941 of the disagreements are `DC`, i.e. the registrant's
office. So state agreement is corroboration on this leg and never proof, and no
LDA-based link reaches Tier A.

---

## Containment: eight guards, all of them vetoes

`resolve_entity` is **imported** from `code/33_apply_party_rulings.py`.
Standing rule 8: no second matcher was written. Its two pure string helpers are
memoised on the module object — a speed change, not a logic change. Every guard
below is a veto on a match the resolver already proposed.

| # | Guard | The failure it prevents |
|---|---|---|
| 1 | record must be at least as specific as the entity | `NATIVE VILLAGE OF ELIM` → *Elim Native **Corporation*** |
| 2 | containment must be corroborated by an official name the spine already holds | containment may resolve an owner named in evidence, never *detect* a match |
| 3 | a Native identity word in the spine name and absent from the record | `core()` folds `indian` away: National Education Association → National Indian Education Association |
| 4 | trap tokens, on partial overlap only | `united`, `san`, `little`; deliberately does not fire on exact matches, which had dropped `Cherokee Nation` |
| 5 | spine core that is generic English nouns only | `Indian Pueblo Cultural Center` → *Makaha Cultural Learning Center* |
| 6 | a record naming a different kind of institution | Yavapai Community Hospital, United Way of Cayuga County, Umatilla Electric Cooperative |
| 7 | a corporate form the spine name does not share, against a government | `Enterprise Holdings, Inc.` → Enterprise Rancheria |
| 8 | **a separate legal person carrying the institution's name** | Institute of American Indian Arts **Foundation** → the Institute; Tulalip **Foundation** → the Tulalip Tribes; Osage Nation **Foundation** → the Osage Nation |
| 9 | state agreement wherever both sides carry one | and where both are known and agree, that is a genuine second leg and the row may tier on it |

Guard 8 is new here and is the Chickasaw Children's Village failure in a new
place: a foundation, trust or endowment files its own return under its own EIN
and is a different legal person from the institution whose name it carries.
Those organisations still enter the dataset as funders in their own right —
what is refused is keying them to the institution's entity id.

### One name-truncation bug worth remembering

IRS e-file splits a business name across `BusinessNameLine1Txt` and
`BusinessNameLine2Txt` at 35 characters. Reading only line 1 left
`FOND DU LAC TRIBAL AND COMMUNITY` — a Minnesota **state community college** —
looking like the Fond du Lac Band, and it resolved to `CNSF-MINNCH-FL`. It also
produced `AMERICAN INDIAN HIGHER EDUCATION` without its `CONSORTIUM`,
`KLAMATH RIVER INTER-TRIBAL FISH & WATER` without `COMMISSION`, and
`MINNESOTA INDIAN WOMEN'S SEXUAL ASSUALT` without `COALITION`. Both lines are
now joined before anything is resolved.

### Deduplication

Three returns had been pulled twice — once rendered by ProPublica for the
philanthropy channel, once out of the IRS ZIP for the Schedule C cache. The
e-file `object_id` is the return's primary key, so **100 duplicate grant lines
were dropped** rather than counted twice.

---

## Results, run of 2026-08-07

`data/clean/advocacy_passthrough.csv` — 1,620 rows, 27 columns.

| `chain_completeness` | rows |
|---|---:|
| `FUNDING_AND_LOBBYING_BOTH_DOCUMENTED` | **185** |
| `FUNDING_ONLY` | 1,400 |
| `LOBBYING_ONLY` | 35 |

- **1,585 funding edges**, 41 distinct Native funders, 927 distinct recipient
  EINs, **$193.6M** in cash grants.
- **185 complete chains** over **19 funders** and **125 recipients**.
- **116 same-year coincidences** — a grant year and a lobbying year coinciding,
  flagged and explicitly not an inference.
- 130 chains carry bill citations; 185 carry named agencies.
- Tier A 923 · Tier B 697. **Every complete chain is Tier B**, because its
  lobbying leg is an LDA name match and LDA publishes no EIN.

### THE BLIND SPOT — the headline

**136 of the 185 complete chains have a funder that appears nowhere in the LDA
corpus.** Thirteen funders; only 7 of the 44 funders reached appear in LDA at
all.

The money is disclosed on a tax return. The advocacy is disclosed on a lobbying
filing. **No source connects them**, and a reader of LDA alone sees neither the
funder nor the relationship. That is the whole reason this layer exists.

### The non-government subset — the actual pass-through cases

A grant to a **tribal government** is a real funding fact, but that tribe's own
lobbying is already visible in Cedar's LDA dataset under its own name. Elijah's
question is about the others, so they are reported separately rather than
folded into a larger, easier number:

| recipient type | complete chains |
|---|---:|
| TRIBAL_GOVERNMENT | 149 |
| NONPROFIT_UNCLASSIFIED | 17 |
| MEMBERSHIP_ORGANIZATION | 8 |
| TRIBAL_COLLEGE | 8 |
| NATIVE_NONPROFIT | 3 |
| **non-government total** | **36** |

**36 chains** are the cases the existing datasets cannot see at all.

### Membership organisations, typed rather than characterised

**54 rows over 45 organisations** carry
`recipient_org_type = MEMBERSHIP_ORGANIZATION`, taken from the spine's own
classes. All 35 `LOBBYING_ONLY` rows are of this shape and they are exactly the
organisations one would expect — NCAI (40 filings), the Indian Gaming
Association (303), the National American Indian Housing Council (185), the
Alaska Native Tribal Health Consortium (160), the Alaska Federation of Natives
(97), NIEA (77), Midwest Alliance of Sovereign Tribes (65), the Southern
California Tribal Chairmen's Association (64), USET (57), NARF (20).

They are `LOBBYING_ONLY` for a structural reason, not a coverage one:
**membership dues are not a Schedule I grant and appear in no public filing.**
The ordinary way a tribe funds NCAI is invisible by construction. Presenting
their advocacy as a concealed pass-through would be simply wrong, so the file
describes it accurately instead.

### The 990 lobbying leg contributed nothing, and that is a measurement

Only **24 of the 927 recipient EINs** have any row in `np_financials.csv`, and every
one of those filed **no Schedule C** and reported **$0** on Part IX line 11d.
So all 185 complete chains rest on LDA.

This is not a parser failure. Four in five grantees of these funders are
outside the nonprofit corpus entirely — 491 of 601, measured in
`docs/PHILANTHROPY_DISCOVERY_LOG.md` — and the returns that would carry a
Schedule C have never been retrieved for them. The `schedc_basis` values across
those 24 recipients say which absence it is:
`outside_efile_index_coverage` 178 rows, `no_schedule_c_filed` 128,
`no_efile_return_indexed` 25, `indexed_not_retrieved` 14.

**Extending the IRS e-file pull to the 601 philanthropy grantee EINs is the
single highest-value next step in this layer.** The machinery exists in script
99; it is a queue-length problem, not a new access problem.

---

## Caveats that travel with every figure

- **6,453 of 12,764 organisations in `np_orgs.csv` are 990-N filers** and
  report no financial detail at all. Zero lobbying there is the filing regime,
  not a finding. The Schedule C denominator is **6,397 rows / 5,792 EINs**,
  never 12,764.
- **Only 2,195 returns were retrieved — 34.3% of the 6,397 possible.** The IRS
  per-return S3 bucket is retired and returns now live in 81 multi-GB ZIPs read
  by HTTP range.
- **Tribal governments are outside the 990 universe under IRC §7871.** A tribe
  funding a nonprofit appears only on the recipient's side, never on its own
  filing. That asymmetry is why this build works at all — and it is why the two
  largest tribal grantmakers in the country are absent.
- **The LDA corpus was pulled with Native keyword nets.** An organisation
  absent from it is absent from *this corpus*, not from lobbying.
- **Schedule C uses the IRS definition and includes state and local legislative
  activity; LDA covers federal contacts only.** An organisation lobbying
  entirely at a state capitol is correctly on the 990 and correctly absent from
  LDA.

## What this layer structurally cannot see

1. **Tribal government grantmaking.** §7871 again. SMSC's $400M and San
   Manuel's giving appear on no Schedule I anywhere.
2. **Membership dues** — no public filing carries them.
3. **Grants under $5,000** — Schedule I Part II has a floor.
4. **Grants to individuals** — Part III carries no names.
5. **Fiscally sponsored projects** — filed under the sponsor's EIN, so the
   organisation named is not the legal person paid.
6. **Whether a grant was restricted** — Schedule I gives a purpose line, not
   the grant agreement.
7. **Which client a lobbying firm was there for**, where a firm files on behalf
   of several.

## Refusals — the guards doing their job

| reason | grant lines refused |
|---|---:|
| `no_native_evidence_for_funder` | 1,832 |
| `np_orgs_excluded_by_prior_ruling:ambiguous_place_token_no_tribal_purpose` | 1,376 |
| `np_orgs_excluded_by_prior_ruling:place_name_false_positive` | 1,137 |
| `np_orgs_ruled_place_name_coincidence` | 653 |

4,998 grant lines were refused because their filer's Native status is not
documented. Publishing them with a blank or guessed funder would have shipped
exactly the false attribution this project forbids.

## Review queue

`review/advocacy_passthrough_unresolved_2026-08-07.csv` — **697 rows**, each
with the reason it does not publish and a blank `YOUR_RULING`. Two shapes:
chains whose lobbying leg is a name match, and chains whose funder's Native
status rests on a name match or an agent-proposed ruling still awaiting a human
one.

## Files

| Path | What |
|---|---|
| `code/111_build_advocacy_passthrough.py` | the build |
| `data/clean/advocacy_passthrough.csv` | 1,620 rows, 27 columns |
| `data/clean/codebook_master.csv` | +27 variable entries under `04c_advocacy_passthrough` (variables only) |
| `review/advocacy_passthrough_unresolved_2026-08-07.csv` | 697 rows awaiting rulings |
| `logs/111_build_report_2026-08-07.txt` | the authoritative run report |

Nothing owned by another agent was modified. `np_financials.csv`,
`native_entity_lobbying_disclosures.csv`, `np_orgs.csv` and the spine were read
only and are byte-identical after the run. `codebook_master.csv` was backed up
to `codebook_master.csv.bak_2026-08-07_pre111` before the write, and the write
replaces only rows whose `dataset` is `04c_advocacy_passthrough`.

## What would move this furthest next

1. **Extend the IRS e-file pull to the 601 philanthropy grantee EINs.** The 990
   lobbying leg contributed zero chains purely because those returns have not
   been fetched. Highest value per unit of work by a wide margin.
2. **Native American Agriculture Fund 990-PF Part XV** — the $266M Keepseagle
   corpus, still unparsed, and a form the philanthropy channel could not read.
3. **Rule the 697 review rows**, or the top 100 by grant dollar.
4. **Recipient-side capture for tribal-government philanthropy** — grantee
   annual reports name SMSC, San Manuel, Tulalip and Muckleshoot in donor
   listings. That is the only machine-readable trace tribal giving leaves, and
   it inverts the channel.
5. **Key `lobbying_unmatched_clients.csv`'s intertribal organisations to the
   spine.** 55 spine Intertribal Organizations have zero rows in the Native LDA
   slice while lobbying heavily in the raw corpus; closing that would improve
   the lobbying dataset itself, not only this layer.
