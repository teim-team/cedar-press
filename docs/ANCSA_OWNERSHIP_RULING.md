# ANCSA ownership — the owner's ruling, 2026-08-26

*Settles the largest open attribution question in the project: **334 one-to-many
defects worth $24.52B**, all of the form `ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_
CORPORATION`. Elijah ruled it. Do not re-open it; apply it.*

---

## THE RULE

**1. The default: an ANCSA operating company is owned by the VILLAGE
CORPORATION, not the village government.**
When an 8(a) operating company sits in an ANCSA structure, the owner is the
village corporation (an ANC). This is the usual case and the presumption.

**2. A village GOVERNMENT never owns an ANC.**
This edge does not exist in either direction that matters here. A village
government does not own a village corporation. If an attribution asserts it,
the attribution is wrong.

**3. But a village government CAN directly own an enterprise — and then it is
simply a tribal enterprise.**
This is the tricky case and there are a few real examples. Where an Alaska
Native village GOVERNMENT owns an enterprise directly, that enterprise is
attributed to the village government exactly as any tribal enterprise is
attributed to its tribe. The owner is a federally recognized tribe that happens
to be an Alaska Native village. It is not an ANC and must not be classed as one.

**4. The village-corporation ↔ village-government relationship is ASSOCIATION,
never OWNERSHIP — and the association is ANCESTRAL, not membership.**
They are connected because the *people* are connected. But be precise about how,
because the loose version of this sentence is itself a source of error:

> **A shareholder is not necessarily enrolled in the tribe. A shareholder
> necessarily has ancestry.** (Owner's correction, 2026-08-26.)

ANCSA shares descend by inheritance and by gift, and **village tribal enrollment
has been closed for a long time**. So the ANC shareholder roll and the village
government's enrollment roll are **two different populations that overlap**, not
two views of one list. Never treat one as a proxy for the other, and never infer
a person's tribal enrollment from their shareholding or the reverse.

There are also specific share-transfer rules that bear on who can hold shares at
all — whether adopted persons receive them, and whether shares may be gifted to
non-Natives or to spouses. **These are unresolved here and must be looked up
before any analysis depends on them.** Do not assume an answer. See the open
question below.

None of this is a corporate ownership edge. It must never be written as one, and
must never be used to roll a corporation's dollars up to a government or the
reverse.

**5. The regional corporation relationship is likewise SHAREHOLDING, not
ownership.**
Alaska Natives enrolled to a village hold shares in their village corporation
*and* in the regional corporation for the region their village sits in. The
regional corporation does not own the village corporation. Two separate
corporations with an overlapping shareholder base.

---

## HOW TO APPLY IT

| observed | attribute to | class |
|---|---|---|
| 8(a) operating company under an ANCSA structure | the **village corporation** | Alaska Native Village Corporation |
| enterprise owned directly by the village government | the **village government** | Federally recognized Alaska Native Village |
| village government asserted as owner of an ANC | **nothing — the attribution is wrong** | refuse, send to review |
| shareholder/membership connection only | **no ownership edge at all** | association, record as such |

**Rule 3 is an exception you must EVIDENCE, not assume.** Rule 1 is the
presumption; departing from it requires a source showing the village government
itself owns the enterprise. Absent that evidence, apply rule 1. Never flip an
attribution to the government because the names look alike — the names look
alike *by construction*, since both are named for the same village.

**This changes no tier.** A tier is inherited from the source row. This ruling
tells you WHICH entity is correct; it does not make a weak link strong.

---

## WHY IT MATTERS BEYOND THE 334

`cedar_domain` already carries a `bears_ownership()` concept and a
`NEVER_OWNERSHIP` set. Rules 4 and 5 belong there: **shared shareholders are not
an ownership edge.** Encoding it stops the same defect being re-derived by the
next matcher that notices two entities share a name and a place.

Related open items this ruling touches:
- `review/identifier_one_to_many_defects_2026-08-26.csv` — 334 rows of this
  family; also 301 `MIXED_CLASS`, 42 `CONSTITUENT_BAND_VS_UMBRELLA_TRIBE`
- The `links_on_village_corporations` metric in `62_no_regression_check.py`
- The spine's 173 Alaska Native Village Corporations against 228 federally
  recognized Alaska Native Villages — two populations that name each other

---

## OPEN QUESTION — ANCSA share transfer. **RESOLVED 2026-08-26 FROM A RETRIEVED
## STATUTE.** The original question is kept below, unedited, followed by the answer.

> **Read the answer at the bottom of this file before acting on anything in this
> section.** The question below was correct when written and is preserved because
> its constraints — do not infer, quote verbatim, cite the URL, a finding about one
> corporation is not a finding about the class — are what the answer had to satisfy.
> Nothing above this line was changed. Backup of the pre-answer file:
> `docs/ANCSA_OWNERSHIP_RULING.md.bak_2026-08-26_pre_222_settle_ancsa_7h_from_govinfo`.

---

## OPEN QUESTION — ANCSA share transfer. UNRESOLVED. Do not answer by inference.

Raised by the owner alongside the rule-4 correction, 2026-08-26, and **left open
deliberately**. Rule 4 establishes that the shareholder roll and the tribal
enrollment roll are two overlapping populations rather than one list. It does
*not* establish the boundary of the shareholder roll, and that boundary turns on
share-transfer rules this project has not read:

1. **Do adopted persons receive shares?**
2. **May shares be gifted to non-Natives?**
3. **May shares be gifted to a spouse?**

**Nothing in this repository answers these, and nothing in this repository may
assume an answer.** Reasoning from general principles about ANCSA is exactly the
failure shape `AGENTS.md` records under "a marginal rate cannot be inverted" —
the arithmetic is right, the citation is right, and the answer is wrong.

### What would settle it

- **ANCSA §7(h), 43 U.S.C. §1606(h)**, and its amendments — in particular the
  1987 "1991 Amendments" (Pub. L. 100-241), which changed alienability and
  introduced the settlement-trust and inheritance provisions.
- **Each corporation's own articles and bylaws.** Corporations differ, so a
  single statutory answer may not be the operative one for a given ANC. A
  finding about one corporation is not a finding about the class — the same
  error this file already paid for at the Federal Audit Clearinghouse.
- A retrieved source in both cases, quoted verbatim with its URL, per
  `docs/CROSS_SOURCE_VERIFICATION.md`.

### Does it change any of the 334?

**No — measured, not assumed.** None of the 334 resolutions turns on who may
hold a share. Every one of them is decided by rules 1, 2 and 3, which are about
**which legal person owns an operating company**, not about who may hold that
person's stock. The share-transfer question would bear on a *shareholder-level*
analysis — demographics, per-capita distributions, beneficiary counts — and this
project has none. `code/191_apply_ancsa_ownership_ruling.py` asserts this: it
carries no share-transfer predicate, and if one is ever added the assertion is
where it will surface.

**If a future pass builds a shareholder-level measure, it is blocked on this
question, not merely informed by it.**


---

## APPLIED - 2026-08-26. What the ruling actually resolved.

`code/191_apply_ancsa_ownership_ruling.py` (decide) ->
`code/192_apply_ancsa_resolutions_in_place.py` (write) ->
`code/193_scan_adjacent_families_against_ancsa_ruling.py` (adjacent families) ->
`code/194_write_ancsa_ruling_codebook_fragment.py` (register).
Zero network calls. `62_no_regression_check.py` **green after**, no
regressions; `links_on_village_corporations` rose **911 -> 963**.

### The split, on all 334

| disposition | n | $ observed |
|---|---:|---:|
| **RESOLVED_TO_VILLAGE_CORPORATION** (rule 1) | **322** | **$24,384.6M** |
| RESOLVED_TO_VILLAGE_GOVERNMENT (rule 3, evidenced) | **0** | $0 |
| RULE_3_CANDIDATE - human needed | 2 | $0.4M |
| HELD by an existing ruling - human needed | 2 | $121.2M |
| surviving corporation unverified - human needed | 8 | $11.6M |
| **government-side legs REFUSED under rule 2** | **334** | - |

**Tier changes: 0.** 206 of the 322 resolutions are tier B and still do not
publish. The ruling said which entity is correct; it made nothing stronger.

**Nothing resolved to a village government under rule 3, and that is a measured
result rather than a default.** Of the 334, **238 already carried a SETTLED
human ruling and not one of them named a village government** - every ruled row
resolved to a village corporation, a regional corporation or an intertribal
organisation. The 71 ledger rows that *did* assert a village government were
**all tier B**, every one from `need_v6` (6.5% accurate) or
`cross_dataset_propagation`. Not one was a ruled method. **The evidence base for
rule 3 inside this family is empty; the evidence base for rule 1 is 238 rulings
deep.**

### Rule 3 is NOT vacuous - the real example, and it was already in the repo

The owner said rule 3 has "a few real examples". One is here, ruled by him on
2026-08-06 and **never applied, because the spine could not hold it**:

```
UEI:FM2KJG6M5363 / NAME:copper river family companies
ruling = "Native Village of Eyak"      status = SETTLED
ledger tier_rationale: "owner is Native Village of Eyak, not Kluti Kaah - but
Native Village of Eyak is not in the spine (ambiguous_core:2_spine_entities),
so this could not be re-attributed."
```

**The village is in the spine now** - `AKNF-NVEYAK-00-CHGCCO-CHGCMT`. And that
one village carries **both shapes at once**, which is exactly why the owner
called rule 3 tricky:

| enterprise family | owner | rule |
|---|---|---|
| Copper River Family of Companies | **Native Village of Eyak** - the tribe | **3** |
| EyakTek / Eyak Services / Northtide / Solutions71 / Cordova Central | **Eyak Corporation** - the ANC | **1** |

Two enterprise families, two different owners, one village name. **A matcher
keying on "Eyak" is wrong half the time whichever way it leans.** That is the
whole argument for evidencing rule 3 per identifier and never per name.

The two Copper River rows inside the 334 are filed
`RULE_3_CANDIDATE_HUMAN_NEEDED` and deliberately not auto-resolved: the ruling
naming the Native Village of Eyak is at the **brand-family** level, and a brand
family is a name family, not a legal person. Carrying it onto one identifier
would be the name inference this ruling forbids.

### The bug this application found in its own first pass

The first run resolved `UEI:VJ4MGKFTMVJ8` to Seldovia Native Association on the
strength of a `status = SETTLED` ruling. That ruling's **`outcome` is
`HOLD_OVER_OWNER`** and its text reads *"HOLD - RETRACTION REQUIRED, already
written to the ledger from ..."*.

**`status` says the ruling was PROCESSED. `outcome` says what it DECIDED.**
Reading the first as the second turns a retraction into a confirmation. Only
`outcome = ENTITY` is a settled attribution; a `HOLD*` is an instruction not to
attribute and is the strongest possible signal that a human must look. Encoded
as `SETTLED_ATTRIBUTION_OUTCOME` in script 191. Two rows are now correctly
`HELD_BY_AN_EXISTING_RULING_HUMAN_NEEDED`.

### Every changed attribution - 3,883 rows, tier unchanged on all of them

`review/ancsa_attribution_changes_2026-08-26.csv` lists each one individually.

| file | rows repointed |
|---|---:|
| `data/clean/subawards.csv` | 3,689 |
| `data/clean/prime_contracts.csv` | 127 |
| `data/clean/cedar_identifier_ledger_final.csv` | 67 |

Largest movements: Afognak -> Afognak Native Corporation (1,174) - Alutiiq ->
Afognak Native Corporation (628) - Sun'aq -> Natives of Kodiak (521) - Council
-> Council Native Corporation (314) - Barrow -> Ukpeagvik Inupiat Corporation
(288) - Tyonek -> The Tyonek Native Corporation (223) - Barrow -> Natives of
Kodiak (127 prime rows, the KOMAN family, each on a settled per-identifier
ruling).

Row counts and column sets are unchanged on all three files, and each was
**re-read from disk after the write** rather than trusted from the run log.
Backups are tagged `.bak_2026-08-26_pre_192_apply_ancsa_resolutions_in_place` -
script name, not number.

**The quality-versus-coverage point holds, and is worth restating.** Only 127
prime rows moved. The other ~71,000 prime rows sitting on these identifiers
were **already booked to the corporation** - the ruling CONFIRMED them rather
than changing them. A defect on an already-attributed UEI is usually a second
source disagreeing with a correct attribution, not a wrong attribution.

### Corrections are made, never erased

A refused attribution is **repointed**, keeping its tier and its
`attribution_method`, with the correction prepended to `tier_rationale` - the
form the hand correction of 2026-08-06 already used on `Chenega Infinity, Llc`.
It is **not** re-tiered to X: `169_build_identifier_graph.py` reads tier X as a
node-level BLOCK, so marking the wrong government attribution X would suppress
the correct corporation attribution along with it.

### What the ruling does NOT settle

`review/ancsa_adjacent_family_scan_2026-08-26.csv`, 540 rows.

| family | n | $ | verdict |
|---|---:|---:|---|
| `MIXED_CLASS` | 4 | $472.1M | **CONSTRAINED_NOT_SETTLED** |
| `MIXED_CLASS` | 297 | $8,533.5M | NOT_TOUCHED |
| `TWO_DIFFERENT_TRIBES_ON_ONE_IDENTIFIER` | 188 | $10,360.0M | NOT_TOUCHED |
| `CONSTITUENT_BAND_VS_UMBRELLA_TRIBE` | 42 | $1,297.8M | NOT_TOUCHED |
| `INTERTRIBAL_ORGANISATION_VS_MEMBER_TRIBE` | 9 | $662.9M | NOT_TOUCHED |

**The hypothesis that `MIXED_CLASS` is largely this question in disguise is
wrong, measured.** Only 38 of its 301 rows involve an ANC at all, and **29 of
those are Cook Inlet Region (AK) versus Eastern Shoshone (WY)** - two entities
that share neither a name nor a place. Likewise Gana-A'Yoo/Lumbee (NC),
Aleut/St. Croix (WI), Bethel Native/Apache Tribe of Oklahoma, Council
Native/Lenape of Delaware, Council Native/Big Sandy (CA). **The test is not "is
an ANC involved" but "are these the two legal persons of ONE Alaska village."**

The **4 constrained** rows are `Bering Straits Native Corporation` (ANRC) vs
`Tanadgusix Corporation` (ANVC). **Rule 5 applies and forbids one resolution** -
the regional corporation does not own the village corporation. It does **not**
say which corporation owns the operating company, and a regional corporation
does own its own subsidiaries. Still a human's row, with one fewer wrong
option. `CONSTRAINED_NOT_SETTLED` exists so that middle state is not collapsed
into either neighbour.

`S&K Aerospace` ($2.59B) and `ONEIDA NATION NY vs WI` ($1.11B) are **not Alaska
cases and were left untouched**, as instructed. `constituent_band_of` is
already inside `NEVER_OWNERSHIP`, so no dollar rolls through the 42 band rows
today - the protection that matters is already in place.

### Encoded in `cedar_domain`

`ANCSA_ASSOCIATION_NOT_OWNERSHIP` (9 relationship types, including
`village_corporation_for` and `regional_corporation_for`, **neither of which
was previously in `NEVER_OWNERSHIP`** - they were merely absent from
`OWNERSHIP_BEARING`, which is a weaker guarantee), `ANCSA_CORPORATION_CLASSES`,
`ALASKA_VILLAGE_GOVERNMENT_CLASSES`, `village_government_owns_an_anc()` (always
False, and a function so that callers must ASK), `ancsa_refusal_reason()`
(returns the refusal in words fit to paste into a review row), and
`bears_ownership(rel, owner_class=None, owned_class=None)` - the two class
arguments are optional, so all seven existing callers keep working unchanged.
Two new relationship types, `shares_ancestral_base_with` and
`shareholder_base_overlaps_with`, give a matcher a correct edge to write
instead of inventing an ownership one.

The dated comment block there carries the owner's rule-4 correction verbatim
and says why the loose phrasing is dangerous: **"a shared membership base" is
wrong, and it is wrong in the direction that invites a matcher to treat the two
rolls as one list, and then to treat one list as one owner.**

### A caveat the ruling does not settle, recorded rather than smoothed over

> **SETTLED 2026-08-26, evening — see "ANSWERED" at the foot of this file.**
> Measured: the tier-A evidence was evidence for the CORPORATION all along and
> the stale value was the ENTITY column. 111 keep A; 93 were demoted A → B for
> the opposite reason (their origin row was demoted to B on 2026-08-06 and the
> subaward copy never caught up); 0 could not be established.

**204 of the 3,689 repointed subaward rows carried tier A on the GOVERNMENT
leg.** They keep tier A and now point at the corporation, because the ruling is
explicit: *"This changes no tier. A tier is inherited from the source row."*
That instruction was followed exactly, and 0 tiers moved.

But it is worth writing down what those 204 rows mean. **A tier-A row that was
pointing at the wrong entity is evidence that its A was over-stated** - the
tier was earned by a process that got the entity wrong, so it was never
measuring what it claimed to. Olgoonik, Goldbelt and Bowhead/UIC firms all
appear here at tier A on the village government.

**That is a separate question and this ruling does not answer it.** Re-tiering
them would be a consumer assigning a tier, which is the exact bug this project
already shipped once. It needs its own pass, against whatever produced the A in
`subawards.csv`, and it is flagged here so the next reader sees it rather than
re-deriving it. `review/ancsa_attribution_changes_2026-08-26.csv` carries
`tier_before` on every row, so the 204 are one filter away.

### Prime dollars actually moved

**$5.09M**, all of it the KOMAN family moving off the Native Village of Barrow
to `Natives of Kodiak, Inc.` on 127 rows. Small, and that is the point: 760
prime rows sit on the repointed identifiers and the great majority were already
correct. **The $38.57B on already-attributed prime UEIs was mostly confirmed,
not corrected.**


---

# THE OPEN QUESTION IS ANSWERED — 2026-08-26, FROM A RETRIEVED STATUTE

*Retrieved from **api.govinfo.gov** (GPO), the United States Code 2024 Edition.
Raw HTML and extracted text on disk at
`data/raw/external/untapped_2026-08-26/`; reproduce with
`py -3 code/222_retrieve_ancsa_share_transfer_statute.py`. Full method,
reachability, and the other free federal corpora probed the same day:
`docs/UNTAPPED_FREE_SOURCES_2026-08-26.md`.*

**Nothing below is inferred. Every proposition is a quotation with a citation and
a public, key-free URL.**

| provision | public URL |
|---|---|
| 43 U.S.C. §1606 (ANCSA §7) | `https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1606.htm` |
| 43 U.S.C. §1607 (ANCSA §8, Village Corporations) | `https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1607.htm` |
| 43 U.S.C. §1602 (Definitions) | `https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1602.htm` |
| Pub. L. 100-241, *Alaska Native Claims Settlement Act Amendments of 1987*, 101 Stat. 1788, enacted **1988-02-03** | `https://www.govinfo.gov/content/pkg/STATUTE-101/pdf/STATUTE-101-Pg1788.pdf` |

## FIRST: §1606(h) reaches the VILLAGE corporations, which is our population

§1606 is headed *Regional Corporations*. The bridge is **43 U.S.C. §1607(c)**,
verbatim:

> **"(c) Applicability of section 1606**
> The provisions of subsections (g), (h) (other than paragraph (4)), and (o) of
> section 1606 of this title shall apply in all respects to Village Corporations,
> Urban Corporations, and Group Corporations."

Credit line: *Pub. L. 92-203, §8, Dec. 18, 1971, 85 Stat. 694; … **Pub. L.
100-241, §6, Feb. 3, 1988, 101 Stat. 1795**; Pub. L. 104-10, §1(b), May 18, 1995,
109 Stat. 157.* The 1995 amendment is what inserted *"(other than paragraph (4))"*.

**Without §1607(c) the answer would be about the wrong corporations.**

## THE OPERATIVE TEXT — 43 U.S.C. §1606(h)(1), verbatim

> **(h) Settlement Common Stock**
> **(1) Rights and restrictions**
> …
> **(B)** Except as otherwise provided in this subsection, Settlement Common
> Stock, inchoate rights thereto, and rights to dividends or distributions
> declared with respect thereto shall not be — (i) sold; (ii) pledged;
> (iii) subjected to a lien or judgment execution; (iv) assigned in present or
> future; (v) treated as an asset under — (I) title 11 or any successor statute,
> (II) any other insolvency or moratorium law, or (III) other laws generally
> affecting creditors' rights; or **(vi) otherwise alienated.**
>
> **(C)** Notwithstanding the restrictions set forth in subparagraph (B),
> Settlement Common Stock **may be transferred to a Native or a descendant of a
> Native** —
> **(i)** pursuant to a court decree of separation, divorce, or child support;
> **(ii)** by a holder who is a member of a professional organization,
> association, or board that limits his or her ability to practice his or her
> profession because he or she holds Settlement Common Stock; or
> **(iii)** as an inter vivos gift from a holder to **his or her child,
> grandchild, great-grandchild, niece, nephew, or (if the holder has reached the
> age of majority as defined by the laws of the State of Alaska) brother or
> sister**, notwithstanding an adoption, relinquishment, or termination of
> parental rights that may have altered or severed the legal relationship between
> the gift donor and recipient.

## AND THE TWO DEFINITIONS IT TURNS ON — 43 U.S.C. §1602

> **(b) "Native"** means a citizen of the United States who is a person of
> one-fourth degree or more Alaska Indian … Eskimo, or Aleut blood, or combination
> thereof. **The term includes any Native as so defined either or both of whose
> adoptive parents are not Natives.** …
>
> **(r) "Descendant of a Native"** means — (1) a lineal descendant of a Native or
> of an individual who would have been a Native if such individual were alive on
> December 18, 1971, or **(2) an adoptee of a Native or of a descendant of a
> Native, whose adoption — (A) occurred prior to his or her majority, and (B) is
> recognized at law or in equity;**
>
> **(s) "Alienability restrictions"** means the restrictions imposed on Settlement
> Common Stock by section 1606(h)(1)(B) of this title;

## THE THREE ANSWERS

### 1. Do adopted persons receive shares? **YES — an adoptee is INSIDE the eligible class.**

§1602(r)(2) places *"an adoptee of a Native or of a descendant of a Native"*
squarely within **"descendant of a Native"**, which is the class every transfer in
§1606(h)(1)(C) may run to. §1606(h)(1)(C)(iii) then makes a gift good
*"notwithstanding an adoption, relinquishment, or termination of parental rights
that may have altered or severed the legal relationship between the gift donor and
recipient"* — so adoption does not break the relationship the gift clause requires.
§1602(b) protects the other direction: a Native *"either or both of whose adoptive
parents are not Natives"* remains a Native.

**Two conditions attach and must never be dropped when this is quoted:** the
adoption **occurred prior to majority**, and it is **recognised at law or in
equity**. An adult adoption does not qualify.

### 2. May shares be gifted to non-Natives? **NO.**

Every route in §1606(h)(1)(C) is expressly *"to a Native or a descendant of a
Native"*, and (h)(1)(B)(vi) forecloses the residue — *"otherwise alienated."*

A non-Native can hold Settlement Common Stock only through **death, not gift**.
§1606(h)(2) governs *"Inheritance of Settlement Common Stock"*: the stock passes
*"in accordance with the lawful will of such holder or pursuant to applicable laws
of intestate succession."* Two consequences travel with it, both verbatim:

> the corporation *"shall have the right to purchase at fair value Settlement
> Common Stock transferred pursuant to applicable laws of intestate succession to
> a person not a Native or a descendant of a Native"*

> **(h)(2)(C)** Settlement Common Stock of a Regional Corporation — (i)
> transferred by will or pursuant to applicable laws of intestate succession
> **after February 3, 1988**, or (ii) transferred by any means **prior to February
> 3, 1988**, to a person not a Native or a descendant of a Native **"shall not
> carry voting rights. If at a later date such stock is lawfully transferred to a
> Native or a descendant of a Native, voting rights shall be automatically
> restored."**

So the non-Native holder does exist in the statute, arrives **only by
inheritance**, and holds **non-voting stock the corporation may buy back at fair
value**.

### 3. May shares be gifted to a spouse? **NO — a spouse is not in the list.**

§1606(h)(1)(C)(iii) enumerates exactly: *"his or her child, grandchild,
great-grandchild, niece, nephew, or (if the holder has reached the age of majority
as defined by the laws of the State of Alaska) brother or sister."* **Spouse is
absent, and the list is closed** — (h)(1)(B) is a prohibition and (C) is its
exception, so anything unenumerated stays barred by (B)(vi).

A spouse may still come to hold the stock two other ways: **by will or intestate
succession** under (h)(2), and **under a court decree of separation, divorce, or
child support** under (h)(1)(C)(i) — and that second route, unlike inheritance,
still requires the spouse to be *a Native or a descendant of a Native*.

## THE CAVEATS THAT MUST TRAVEL WITH THIS ANSWER

The second half of the original question — *"Each corporation's own articles and
bylaws. Corporations differ, so a single statutory answer may not be the operative
one for a given ANC"* — **stands, unanswered, and is now the only open part.**

1. **These restrictions are not permanent.** §1606(h)(3) and **43 U.S.C. §1629c**
   provide for the **termination of alienability restrictions** by shareholder vote
   and the exchange of Settlement Common Stock for **Replacement Common Stock**.
   Everything above is conditioned on the statute's own phrase, *"any period in
   which alienability restrictions are in effect"* (§1606(g)(1)(D)). **Whether any
   specific corporation has terminated is a per-corporation fact this repository
   does not hold.** `sec1629c.txt` is on disk at
   `data/raw/external/untapped_2026-08-26/`, retrieved and unread.
2. **A corporation may add restrictions of its own.** §1606(h)(3)(D) lets a
   corporation amend its articles before termination to impose further terms on
   Replacement Common Stock, **including a right of first refusal**; §1606(g) lets
   it issue additional classes of stock. **The statute is a floor, not the
   operative answer for a given ANC** — which is the same "a finding about one
   corporation is not a finding about the class" discipline this file already paid
   for at the Federal Audit Clearinghouse, running in the other direction.
3. **The date label in the question, resolved.** This file said *"the 1987 '1991
   Amendments' (Pub. L. 100-241)"*. Both labels are right and neither is the
   enactment year: GovInfo's Statutes at Large granule **STATUTE-101-Pg1788** is
   titled *"Alaska Native Claims Settlement Act **Amendments of 1987**"* with
   `dateIssued` **1988-02-03**, and §1606's credit line reads **"Pub. L. 100-241,
   §§4, 5, 12(a), Feb. 3, 1988, 101 Stat. 1790, 1792, 1810."** That is why
   **February 3, 1988** is the hinge date written into (h)(2)(C).
4. **The trailing clause of (C)(iii) is from 2000, not 1988.** Amendment note,
   §1606: *"2000—Subsec. (h)(1)(C)(iii). Pub. L. 106-194 inserted before period at
   end ', notwithstanding an adoption, relinquishment, or termination of parental
   rights that may have altered or severed the legal relationship between the gift
   donor and recipient'."* The 1988 Act did the structural work: *"1988— … Subsec.
   (h)(1), (2). Pub. L. 100-241, §5, amended pars. (1) and (2) generally, changing
   structure of each from a single unlettered paragraph to one consisting of
   subpars. (A) to (C)."* **So the adoption clause protecting gift eligibility is
   twelve years younger than the framework it sits in** — do not cite it to a
   pre-2000 fact pattern.

## WHAT THIS CHANGES

**Nothing in the ruling above, and none of the 334.** That was already measured
rather than assumed: none of the 334 turns on who may hold a share, and
`code/191_apply_ancsa_ownership_ruling.py` carries no share-transfer predicate.

**What it unblocks is exactly what this file said it would:** *"If a future pass
builds a shareholder-level measure, it is blocked on this question, not merely
informed by it."* **That block is lifted at the statutory level** and remains in
place at the per-corporation level, pending articles and bylaws.

**And it hardens rule 4.** The owner's correction — *"A shareholder is not
necessarily enrolled in the tribe. A shareholder necessarily has ancestry"* — is
now supported by text rather than by reasoning. §1602(r) defines the
shareholder-eligible class by **lineal descent, or by a qualifying minor adoption**,
with no reference to tribal enrollment anywhere; and §1606(h)(2) admits
**non-Natives by inheritance**, holding non-voting stock. So the shareholder roll is
neither a subset nor a superset of the enrollment roll. **Two overlapping
populations, exactly as ruled — and now with the statute saying so.**

---

## ANSWERED - 2026-08-26, evening. The 204 tier-A subaward rows.

The caveat above deliberately left this open: *"a tier-A row that was pointing
at the wrong entity is evidence that its A was over-stated... That is a separate
question and this ruling does not answer it."*

`code/249_audit_ancsa_tierA_subaward_repoints.py` answered it.
`code/250_demote_stale_tierA_subaward_rows.py` applied the answer.

### The reasoning was right in general and wrong about these 204

**Where the tier on a subaward row actually comes from.** `sub_native_tier` and
`prime_native_tier` are not minted in `subawards.csv`.
`41_match_subawards_to_ledger.py` and `45_promote_subawards.py` write them as,
literally,

```python
row["sub_native_tier"] = sm.get("confidence_tier", "") if sl else ""
```

where `sm` is the `cedar_identifier_ledger_final.csv` row for that UEI. The file
copies a ledger tier at promotion time. So "does the tier-A evidence support the
new entity?" is not a judgement call - **read the origin row.**

**All 20 distinct UEIs behind the 204 already point at the CORPORATION in the
ledger, and have since 2026-08-06** - twenty days before this ruling. Their
tier-A `tier_rationale` says so in its own words:

```
LJJWK5BTBG99  A  web_verified       -> Ukpeagvik Inupiat Corporation
  "Corrected 2026-08-06: 'bowhead' is the ANCSA corporation's brand. Moved from
   the village GOVERNMENT to the CORPORATION - separate legal persons.
   Verified against a retrieved source"
```

**So the tier-A evidence was never evidence for the village government.** It is
evidence for the corporation and it names the corporation. What was stale in
`subawards.csv` was the ENTITY COLUMN - a copy taken before the 2026-08-06
correction, where the tier came across and the entity did not. **This pass did
not repoint a correct-A-wrong-entity row. It caught a stale copy up to a
correction the ledger had already made.**

That is a happier finding than the caveat feared, and it generalises: *a defect
on an already-attributed identifier is usually a stale consumer, not a wrong
adjudication* - the same shape as this document's own note that "the $38.57B on
already-attributed prime UEIs was mostly confirmed, not corrected."

### The 93 that WERE wrong, in the other direction

Staleness cuts both ways. Seven of the twenty UEIs - all Olgoonik - sit at
**tier B** in the ledger today via `agent_research_one_leg`, "single evidence
leg", from the pass AGENTS.md records as *"Two independent legs of evidence =
Tier A. One leg = Tier B. Measured 2026-08-06: 49 single-leg rows were correctly
demoted A -> B."*

`subawards.csv` still carried the **pre-demotion A** on 93 rows. A consumer
holding an A its source row no longer supports is the same invariant this ruling
invokes, read forwards instead of backwards.

| n rows | disposition | why |
|-------:|---|---|
| **111** | **KEEP A** | origin row is tier A today and names the same corporation; its rationale IS the government->corporation correction |
| **93** | **DEMOTE A -> B** | origin row is tier B today; the A predates its single-leg demotion |
| **0** | could not be established | every one of the 20 UEIs carried the row needed to decide it |

`review/ancsa_tierA_subaward_disposition_2026-08-26.csv` records all 204
individually with the origin row's tier, method, entity and rationale beside
each. `review/ancsa_tierA_subaward_demotions_applied_2026-08-26.csv` records
what was written.

**Independent cross-check, because a selection that matches its own audit proves
nothing.** Scanned across the entire 63,548-row file: rows where the subaward
tier is A, the ledger tier is B, and both name the same entity number **exactly
93** - 91 `sub_native_tier` + 2 `prime_native_tier`. Every one is inside the
204. The demotion set is closed.

### How the write was made safe

- Two existing columns only. **No entity touched, no column added, no row added
  or removed, nothing promoted, nothing re-tiered to X.**
- **It moves the file TOWARD what a rebuild would produce, not away from it.**
  Re-running `41` then `45` against today's ledger would write B on all 93 by
  itself. So this is not an in-place enricher a rebuild would revert - the
  `09`/`50` failure shape - it is the same field brought forward to the same
  value.
- Row selection requires the entity to match as well as the tier, so a row some
  later pass repoints cannot be caught by a re-run.
- `121_pull_subawards_api.py pull` was live on this file. The script records
  mtime and size before reading, **re-checks immediately before the rename and
  aborts if the file moved**, backs up to
  `.bak_2026-08-26_pre_250_demote_stale_tierA_subaward_rows` (script NAME),
  writes `.part` then renames, and re-reads from disk to verify - 63,548 rows,
  52 columns, 0 of the audited rows still tier A.

### The rule this earns

**A consumer that COPIES a tier owes the source a re-read.** An inherited tier
is correct only as of the moment it was copied, and a copy that has gone stale
is indistinguishable from a copy that is right.

`subawards.csv` is broadly out of step with today's ledger - thousands of rows
sit at B where the ledger now says A. **That direction is a PROMOTION and must
not be done by hand.** Re-running `41` then `45` is the route, and it is the same
run that would have written these 93 B's.
