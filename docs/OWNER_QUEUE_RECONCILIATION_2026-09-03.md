# Owner adjudication queue — reconciliation, 2026-09-03

Worked by Cedar (not the owner) from public sources, per the owner's instruction of
2026-09-02: *"go through the queue yourself. Look at websites… give me stuff that
actually is hard for you to reconcile."*

Rulings are recorded in `review/cedar_research_rulings_2026-09-03.csv` with
`attribution_method = cedar_web_research`. **That method is deliberately not
`elijah_ruling`.** A ruling made by Cedar from a published corporate disclosure is
not an owner ruling and must never inherit an owner ruling's tier. Per AGENTS.md's
governing rule — *a tier is inherited, never assigned* — every row lands at tier B
on `published_owner_statement`, except the ASRC row, which is tier A because it was
measured in place rather than researched.

---

## The headline: most of the queue was never a real question

The queue presented **72 cards worth a nominal $40,155,242,647**. Measured against
the actual tables, that figure is mostly an artifact of how the cards were built.

As rebuilt by `code/1166_owner_queue_card_builder.py`:

| | cards | dollars shown |
|---|---:|---:|
| Nominal queue | 72 | $40,155,242,647 |
| less: answered from published sources (incl. the $19.26B ASRC no-change) | −22 | −$31,505,806,688 |
| less: diacritics-only, never a conflict | −5 | −$8,027,489,608 |
| less: already ruled tier X — a negative ruling on record | −7 | −$372,002,733 |
| less: already attributed at tier A/B | −7 | −$97,655,634 |
| less: no identifier and no exposure — needs UEI backfill first | −23 | $0 |
| **Left for the owner** | **8** | **$152,287,985** |

The two "already answered" rows sum to 14 cards / **$469,658,366**, which is the
figure measured independently before the rebuilt gates existed. They reconcile to
the dollar.

Three separate defects in the card generator produced that gap. Each is measured,
each is fixable, and none of them is a data defect.

### Defect 1 — parent-cluster dollars printed on a child's card

The $19.26B card read `Broadleaf, Inc — Cedar says The Hawai'i Pacific Foundation,
source says ARCTIC SLOPE REGIONAL CORPORATION`.

Measured in `data/clean/prime_contracts.csv`: `parent_uei = CY16XXPHX213` carries
**92,568 rows summing to $19,255,440,794.89**, spanning FY2000–FY2026 and **93
distinct children** (ASRC Aerospace, Arctic Slope Technical Services, ArcTec Alaska
JV, and others). **Every one of those rows is keyed `cedar_uid = CE-00078-KR`,
`tribe_id = ANRC-ARCSLO-00` — Arctic Slope Regional Corporation.** There is no
contamination and nothing to rule.

Broadleaf itself is 324 of those rows, $137,013,762 — 0.7% of the cluster. The card
took one child's name, one child's disputed prior owner, and the parent's whole
26-year book, and presented them as a single $19.26B conflict.

The underlying fact the card was reaching for is real but small, and it is a
*change*, not an error: Broadleaf, Inc. was founded in 2009 owned by The Hawai'i
Pacific Foundation, a Native Hawaiian Organization, and acquired by ASRC Federal in
April 2023 ([Tribal Business News, 2023-05-01](https://tribalbusinessnews.com/sections/federal-8-a-contracting/14314-alaska-native-corporation-unit-acquires-native-hawaiian-defense-contractor)).
Both owners are correct, on either side of that date.

> **Left open deliberately.** A separate `Broadleaf Services, Inc` (36 rows,
> $1,267,460) still published itself as wholly owned by The Hawai'i Pacific
> Foundation as of September 2024. I did not establish whether the two are one
> company. Do not fold them.

### Defect 2 — one UEI's dollars printed once per card

Four UEIs carry more than one card, and each card shows the **full cluster total**:

| UEI | cards | dollars shown on each |
|---|---:|---:|
| `KZMRSJJJN1L6` (Bowhead / UMIAQ / Rockford) | 8 | $1,605,497,922 |
| `C7XULC6EFUF8` (S&K) | 2 | $1,047,030,215 |
| `QX91C7GZDJS5` (Mission Support) | 2 | $402,913,985 |
| `K3N7G5L6GRY6` (Amee Bay / Ocean Bay) | 2 | $392,194,623 |

Summing the cards double-counts **$13,080,624,275 — 32.6% of the stated queue**.

This also hid a *real* problem worth surfacing: the 8 cards on `KZMRSJJJN1L6` do not
agree with each other. Five key the UEI to `Ukpeaġvik Iñupiat Corporation`; three
key the same UEI to `Barrow`. Cedar holds two contradictory keys for one identifier.
The same is true of `QX91C7GZDJS5` — one card says `Campo`, the other says `Oneida`.
An internal contradiction is not an owner question; it is a bug with a right answer.

### Defect 3 — negative rulings re-asked as open questions

**14 of the 72 cards, $469,658,366, match a ledger row that already carries a
ruling** — 7 cards / $372,002,733 where every row is a refusal, and 7 cards /
$97,655,634 that are already positively attributed at tier A or B *alongside* a
tier-X refusal of some other candidate.

Tier X is not missing data. AGENTS.md:1962 defines it as a *negative ruling* —
"ruled NOT this entity" — and the `tribe_id` on a tier-X row records **which
candidate was rejected**. The 1,089 tier-X rows that carry a `tribe_id` are the
system working exactly as designed: "Onondaga Golf and Country Club is NOT the
Onondaga Nation," "American Eagle Protective Services is NOT the Native Village of
Eagle," "Three Blind Mice Enterprises LLC is NOT Enterprise Rancheria."

The card generator read those refusals as unresolved conflicts and put them back in
the queue. That is precisely the owner's complaint of 2026-09-02 — *"I'm 100% I have
ruled these before and it doesn't clear the queue when I'm done"* — and it is now
reproduced and measured rather than merely reported.

Largest re-asked refusals: AVCP Regional Housing Authority ($366,277,599), Goldbelt
Eagle LLC ($97,590,035), Deco Inc ($5,621,714).

> **A second correction, to the gate rather than the read.** The first version of
> gate 3 suppressed any card whose identifier carried *any* tier-X row, and reported
> 17 cards / $5,286,152,131. That is wrong: an entity can carry a tier-X row
> refusing one candidate and a tier-A row attributing it to another. St George Tanaq
> Corporation carries tiers {A, B, X} for exactly that reason. The gate now tests
> whether the tier set is *entirely* refusals, and the two cases are labelled
> separately.

> **A correction to my own first read.** I initially took the tier-X hubs
> ("Enterprise" absorbing 72 rows, "Eagle" 54, "Barrow" 58) for a clustering bug that
> was swallowing unrelated companies. That was wrong. Those hubs are the refusal
> ledger, and their size is a measure of how much junk the system has correctly
> *rejected*. The bug is downstream, in what reads them.

---

## Rulings made from published sources

Every one is bound to a UEI, never to a name. Full evidence URLs are in the CSV.

| Unlocks | Subject | Ruling | Why Cedar was wrong |
|---:|---|---|---|
| $1.61B | Bowhead family, UMIAQ, Rockford | **Ukpeaġvik Iñupiat Corporation** | Bowhead is UIC's federal contracting division. "Barrow" is the village; UIC is the corporation. Different legal persons. |
| $1.05B | S&K Federal / S&K Logistics | **Confederated Salish and Kootenai Tribes** | Matched the bare token "Kootenai," which is a *different* federally recognized tribe (Kootenai Tribe of Idaho). |
| $805M | Sand Point Generating LLC | **Tanadgusix Corporation (TDX)** | TDX Power operates a plant *in* Sand Point. TDX is the St. Paul Island village corp. Cedar keyed it to the Qagan Tayagungin Tribe **of Sand Point** — the tribe of the town where the plant sits. |
| $799M | Aleut Construction LLC | **The Aleut Corporation** | A *regional* ANC. The Pribilofs are one of four shareholder-origin areas, not the owner. |
| $729M | Vista Defense Technologies | **Bristol Bay Native Corporation** | **Neither side was right.** Cedar matched "Vista" → Buena Vista Rancheria (California Miwok); the source named the company as its own owner. |
| $481M | Tikigaq Technology Services | **Tikigaq Corporation** | Point Hope, Alaska village corp, Iñupiaq shareholders. Cedar said "Paiute of Utah." |
| $403M | Mission Support Services LLC | **Oneida Nation (Wisconsin)** | Matched the token "Mission" → Campo Band of Diegueño **Mission** Indians. |
| $392M | Amee Bay / Ocean Bay | **Old Harbor Native Corporation** | Subsidiaries of **Three Saints Bay LLC**. Cedar matched the word **"Three"** → Three Affiliated Tribes of North Dakota. |
| $332M | Oneida Total Integrated Enterprises | **Oneida Nation (Wisconsin)** | Same family as MS2. |
| $314M | Eagle Eye Electric LLC | **Bering Straits Native Corporation** | **Neither side was right.** Cedar matched "Eagle" → Native Village of Eagle, on the Yukon. |
| $250M | Bowhead Marine Support Services | **Ukpeaġvik Iñupiat Corporation** | Same village-vs-corporation error. |
| $33.3M | MILL CREEK, LLC | **Prairie Band Potawatomi Nation** | Matched the token "Creek" → Berry Creek Rancheria of Maidu Indians (California). Mill Creek → Prairie Band, LLC → PBPN, acquired Oct 2017. All 34 rows are FY2022–2026, so no temporal split is needed; measured sum $33,268,943 reconciles to the card to the dollar. |
| $4.6M | Crow Tribe Of Indians | **Crow Tribe of Montana** | Not the Crow Creek Sioux Tribe of South Dakota. |
| $1.2M | Chugach Regional Resources Commission | **Chugachmiut** | An ISDEAA tribal consortium, not Chugach Alaska Corporation. Cedar matched "Chugach" across two different legal forms. |
| $706K | Flandreau Santee Sioux Tribe | **Flandreau Santee Sioux Tribe (SD)** | Not the Santee Sioux Nation of Nebraska. |
| $65K | Mashpee Wampanoag Tribe | **Mashpee Wampanoag Tribe** | Not the Wampanoag Tribe of Gay Head (Aquinnah). |

### The single pattern under almost all of it

Thirteen of these fifteen are the same failure: **a shared token was treated as a
shared identity.** "Kootenai," "Mission," "Three," "Eagle," "Vista," "Crow,"
"Chugach," "Wampanoag," "Santee Sioux." The exactness of a token says nothing about
the correctness of a link — the same principle AGENTS.md already records for EIN
matching, arriving here by a different road.

Two of them are a second, sharper pattern: **an ANCSA village corporation keyed to
the federally recognized village tribe of the same place.** UIC vs. Barrow; and the
same shape in Kake Tribal Corporation vs. Organized Village of Kake, Klukwan Inc.
vs. Chilkat Indian Village. These are different legal persons under different
statutes (43 U.S.C. §1607 vs. 25 U.S.C. §5123) and must never share a `cedar_uid`.
A registry of these legal forms is being built at
`docs/NATIVE_ENTITY_LEGAL_FORMS.md`.

---

## What is left for the owner

Eight cards, $152,287,985. **Five of them are the same question wearing five
different names**, and answering it once retires all five plus most of the 23 cards
routed to identifier backfill.

### The one question: is a village corporation the same entity as its village?

| Unlocks | Cedar says | Source says |
|---:|---|---|
| $72,685,526 | Port Graham | THE PORT GRAHAM CORPORATION |
| $38,392,734 | Eklutna | EKLUTNA, INC. |
| $15,618,271 | enterprise of Kake | KAKE TRIBAL CORPORATION |
| $36,682 | enterprise of Savoonga | SAVOONGA NATIVE CORPORATION |
| $46,000 | enterprise of Wainwright | OLGOONIK CORPORATION |

In every one, Cedar names the **federally recognized village** and the source names
the **ANCSA village corporation** of the same place. These are different legal
persons: the village government is organized under 25 U.S.C. §5123, the corporation
under 43 U.S.C. §1607. They have different members, different assets, different
liabilities, and different governing law. Neither owns the other.

I deliberately did **not** resolve these by folding the names, even though the fold
is one line of code and would have cleared $126.8M in a keystroke. An earlier pass
did exactly that and would have silently merged a village government into its
corporation. `code/1166_owner_queue_card_builder.py::_fold_for_identity` now strips
diacritics, case and punctuation and *nothing else*, with a comment saying why.

**The ruling needed is one line:** does a `cedar_uid` resolve to the village
corporation, to the village government, or does Cedar carry both and relate them?
Whatever the answer, it should be a rule in `docs/NATIVE_ENTITY_LEGAL_FORMS.md`, not
five card answers. The statutory groundwork for it is being assembled now.

### The three genuinely separate ones

1. **Leech Lake Reservation Business Committee — $14,937,747.** Cedar says
   *Minnesota Chippewa Tribe*; the source says *Leech Lake Band of Ojibwe*. **Both
   are defensible.** The MCT is the federally recognized entity; Leech Lake is one
   of its six constituent bands and runs its own Reservation Business Committee.
   This is the `cedar_uid` question in its purest form, and the answer generalizes
   to the other five bands. A legal determination, not a lookup.

2. **Community Power Corporation — $10,533,624.** Cedar records it as an enterprise
   of Afognak; the source names no owner at all. There are several unrelated
   companies of this name and the card carries no UEI to tell them apart. Needs an
   identifier before it needs a ruling.

3. **Piñon Community School Inc — $37,400.** Correctly keyed to the Navajo Nation,
   but stamped `entity_class = "Federally recognized Alaska Native..."`. Five rows
   in the ledger carry this contamination (four Navajo community schools and Indian
   Health Service against Red Lake). Small, and a class error rather than an
   attribution error, but it is wrong on its face.

### Two questions of policy, not fact

- **Broadleaf temporal split.** Whether the 324 Broadleaf rows ($137,013,762) should
  attribute to The Hawai'i Pacific Foundation before April 2023 and to ASRC after,
  or wholly to ASRC. Cedar's ownership-change layer can express either; the question
  is what the published datasets should say.
- **AVCP Regional Housing Authority ($366,277,599).** Already tier X, so it is out
  of the queue — but see the statutory finding below, which says this class can
  *never* be resolved by a ruling of the usual shape.

---

## Fixes applied to the card generator

All four are implemented in `code/1166_owner_queue_card_builder.py` and the field
sheet has been rebuilt from them:

1. Collapse cards to one per UEI; never print a parent cluster's total on a child's
   card.
2. Exclude any card whose identifier already carries a tier-X row, and say so.
3. Detect and route internal contradictions (one UEI, two Cedar keys) as bugs, not
   as owner questions.
4. Fold diacritic-only differences before calling something a conflict —
   `Ukpeaġvik Iñupiat Corporation` vs `UKPEAGVIK INUPIAT CORPORATION` is one entity.
   **Do not** fold corporate suffixes: `Eklutna` vs `EKLUTNA, INC.` and `Port Graham`
   vs `THE PORT GRAHAM CORPORATION` distinguish a village government from its ANCSA
   corporation, and are load-bearing.

---

## Statutory finding: a TDHE has no single owner, by design

Raised because the queue kept surfacing **AVCP Regional Housing Authority** — Cedar
had keyed it to *Arctic Slope Regional Corporation*, which is wrong twice over: ASRC
is a corporation rather than a tribe, and it is the North Slope regional corporation
while AVCP serves the Yukon–Kuskokwim delta, roughly 700 miles away.

The governing definition is **25 U.S.C. §4103** (NAHASDA), and it settles the class
rather than the instance. A tribally designated housing entity is one

> "established by exercise of the power of self-government of one or more Indian
> tribes independent of State law, or by operation of State law providing
> specifically for housing authorities or housing entities for Indians, **including
> regional housing authorities in the State of Alaska**"

— and it may be *"authorized or established by **one or more** Indian tribes to act
on behalf of **each such tribe**."*

Three consequences for `cedar_uid`:

1. **The statute names this class explicitly.** Alaska regional housing authorities
   are not an anomaly Cedar has to reason about from first principles; Congress
   carved them out by name. There are 14 of them, serving 201 Alaska Native
   communities. AVCP RHA alone is the TDHE for **53 tribes** across 48 communities
   in the Bethel and Kusilvak Census Areas.

2. **A TDHE cannot resolve to one Native entity, and it is not an error that it
   doesn't.** It acts *on behalf of each* authorizing tribe. Forcing a single
   `cedar_uid` onto AVCP RHA would be false whichever of the 53 was chosen. This is
   the first entity class Cedar has hit where the correct answer is structurally
   many-to-many, not a better single key.

3. **The pre-1996 authorities are a different sub-case again.** §4103 separately
   admits entities established before 1996-10-26 under the U.S. Housing Act of 1937.
   Several Alaska regional authorities predate NAHASDA on that footing (AVCP RHA's
   own federal program history runs back to the Indian Housing Act, Pub. L.
   100-358), so "when was it created" changes which limb of the definition applies.

### The entity, the owner and the recipient are three different answers

Added 2026-09-03 after a peer research agent supplied **24 C.F.R. §1000.317**, which
I re-fetched and verified verbatim (via law.cornell.edu — ecfr.gov now 302s to an
unblock page):

> **"Who is the recipient for funds for current assisted stock which is owned by
> state-created Regional Native Housing Authorities in Alaska?"**
>
> "If housing units developed under the 1937 Act are owned by a state-created
> Regional Native Housing Authority in Alaska, and are not located on an Indian
> reservation, then the recipient for funds allocated for the current assisted stock
> portion of NAHASDA funds for the units is **the regional Indian tribe**."

This does not contradict the finding above; it sharpens it. For that slice of the
money, the housing authority may **own the units** while the **regional Indian tribe
is the recipient of the funds**. Attributing those dollars to the authority would be
wrong.

So this class needs three fields, not one:

| question | AVCP RHA answer |
|---|---|
| Who is the entity? | the TDHE itself — no single owner, §4103(22)(B)(ii) |
| Who owns the asset? | the state-created regional housing authority |
| Who receives the money? | the regional Indian tribe, for current assisted stock |

**Scope carefully.** §1000.317 is limited to *current assisted stock* — 1937 Act
units — on *non-reservation* land. It is not a general rule about NAHASDA funds and
must not be generalised into one.

The direct-funding chain, for the record, is **25 U.S.C. §4111(a)(2)** ("the
Secretary shall provide the grant amounts for the tribe directly to the recipient
for the tribe"), with "recipient" defined at **§4103(19)**. §4111(c) and (d) are the
local cooperation agreement and the tax exemption respectively, and are *not* the
direct-funding provisions — a correction supplied by the same peer.

**Verification note.** §4103(22)(B)(ii) and §1000.317 are retrieved and quoted. The
Alaska state-law citations that recur in secondary sources — AS 18.55.995 and .996 —
are **not** verified: three attempts at the statute text and at the leading case
(*Kopanuk v. AVCP Regional Housing Authority*, Alaska 1995) each returned HTTP 403.
Treat those two as unconfirmed until someone reads them.

### Convergent evidence from a second, independent pass

While this reconciliation ran, a separate agent auditing `nest.csv` for ownership-
versus-affiliation defects reached the same structural conclusion from the opposite
direction. Its residual defect class, in its own words, is **"mostly one family:
`X Corporation` keyed to `X village government`."** That is precisely the class that
five of the eight surviving queue cards belong to. Two passes that shared no code
and no inputs found the same fault line, which is worth more than either finding
alone.

That agent's run also closed the 20 negative-constraint violations outstanding from
2026-09-02 (now 0; `846` at 32/32), repointed 371 edges with 56 vetoed and **0 rows
dropped**, and — importantly for how much weight to put on any single audit number
here — flagged that concurrent rebuilds mean *any single audit run is a snapshot*.

---

## Owner ruling 2026-09-03: resolve by identifier, not by name

On the `Eklutna` vs `EKLUTNA, INC.` card:

> "it's sort of like Eklutna versus Eklutna Inc. Like, it's the same thing
> essentially… I checked the cage code and it goes to this website
> [eklutnainc.com]… I don't want you to get cut off in like ASRC Inc versus ASRC
> company. Like, that's stupid."

**He is right, and Cedar already agreed with him — the card was misreporting.**

| UEI | tribe_id | canonical_name |
|---|---|---|
| `JWA7LVNPBSM5` | `ANVC-EKLUTN-00` | **Eklutna, Inc.** (the ANCSA corporation) |
| `ZWNKTD5RK531` | `AKNF-EKLTNA-00-CKINLT` | **Native Village Of Eklutna** (the tribe) |
| `M3NNALGMSSX7` | `ANVC-PRTGRH-00` | **The Port Graham Corporation** |
| `D697ANJLFJL9` | `AKNF-PRTGRM-00-CHGCCO-CHGCMT` | **Port Graham Village Council** |

Cedar holds the corporation and the village government as separate entities on
separate identifiers, correctly, in every one of these cases. The card had
abbreviated `Eklutna, Inc.` down to `Eklutna` and then compared **its own
abbreviation** against the source string. Three more cards, $126,016,008, were this
and nothing else.

### What I got wrong, and the better rule

My earlier note said corporate suffixes are load-bearing and must never be folded.
The *premise* is true — a village government and its ANCSA village corporation are
different legal persons under 25 U.S.C. §5123 and 43 U.S.C. §1607 — but the
conclusion was wrong. It had me comparing two display strings when an identifier was
sitting right there.

`code/1166_owner_queue_card_builder.py` gate 4b now asks the only question that can
actually be wrong: **does the identifier resolve to exactly one entity?** If yes, the
names on the card are decoration. If it resolves to more than one, that is a data
defect to fix, still not an owner question. Tier-X rows are excluded from resolving,
since a refusal records a rejected candidate rather than an answer.

This *strengthens* the village-vs-corporation distinction rather than abandoning it,
by enforcing it where Cedar actually records it.

### A real defect this turned up

Checking Port Graham surfaced six CAGE codes keyed to `TRBF-PGMBSK-00` — **Port
Gamble S'Klallam, Washington State** — that are all **Port Graham, Alaska** entities:

`8P8C0` QUALITY PORT GRAHAM CONSTRUCTION JV · `9KM07` PORT GRAHAM TECHNICAL
SOLUTIONS · `9DNV1` PORT GRAHAM METSON ENGINEERING SERVICES JV · `8FK65` ALLIED PORT
GRAHAM JV · `7BPB1` PORT GRAHAM GOVERNMENT SOLUTIONS · `8PFB2` PORT GRAHAM/E-TERRA

All tier B — **positively attributed**, not merely unresolved — to the wrong tribe in
the wrong state, ~1,500 miles away. `7BPB1` alone carries 12 rows / $2,862,121 in
`prime_contracts.csv`. A seventh row on the same key, `5V3Y3` DEPARTMENT OF PORT
ADMINISTRATION, appears to be a match on the bare word "Port" and is likely wrong
too. Six of eleven rows under that `tribe_id` are misattributed.

`Port Graham` / `Port Gamble` is the same token-collision family as `Three Saints
Bay` → `Three Affiliated`, but nastier: the two names differ by two letters.

### The queue after the ruling

**Five cards, $26,271,977 — and not one of them has a UEI.** Every remaining question
is now blocked on identifier backfill rather than on adjudication: KAKE TRIBAL
CORPORATION ($15.6M), Community Power Corporation ($10.5M), Olgoonik Corporation
($46K), Piñon Community School ($37K), Savoonga Native Corporation ($37K).

That is the honest state of it: **the owner-adjudication queue is empty of things an
owner can usefully adjudicate.** The next unit of work is getting UEIs onto those
five, not asking about them.

---

## The CICD retirement, finished properly

Owner, 2026-09-03: *"I told you not to use these CICD IDs anymore. I don't know
why we still are. We are using our own system."*

He had already ruled this on 2026-09-01, and `code/843_retire_cicd_scheme.py` did
retire it — for **three files, named by hand**. That is why it came back.

### Two passes, because the first one was not enough

**Pass 1, column names.** The rule moved out of `843`'s hardcoded list into
`cedar_publication.publishable_columns()`, which all three extract scripts already
consult. 77 files in `data/clean` carried a bare `tribe_id`; 7 of 12 customer
datasets shipped a NEID as identity. Measured safe first: every row carrying a NEID
already had a `cedar_uid`, counts matching exactly, **zero orphans**.

**Pass 2, and the first pass was still leaving the identifiers behind.** Measured
immediately after pass 1 shipped: **89,680 retired NEID values on 45,213 rows, in
22 columns across 8 datasets**, under names that say nothing about the scheme —
`entity_id`, `owner_hub_handle`, `affiliated_entity_ids`,
`certifying_authority_entity_id`. The owner's complaint was still true after the
fix that was supposed to answer it.

### Deletion was not available, so the identifiers are translated

`nagpra` and `native-owned-businesses` carry **no `cedar_uid` at all**. Those NEID
columns are their only entity keys, and dropping them would have left two datasets
unable to name a party. So `cedar_publication.translate_neid_values()` rewrites the
retired identifier to Cedar's own, member by member inside pipe-delimited cells.

| | before | after |
|---|---:|---:|
| retired NEID values shipping | 89,680 | **1,954** |
| rows carrying one | 45,213 | 1,673 |
| datasets | 8 | 7 |

**97.82% translated. Nothing was guessed.** The 1,954 that remain are exactly the
values of the **12 NEIDs that claim more than one `cedar_uid`** — the same
collisions `code/1167_cedar_uid_identity_collisions.py` reports as MERGE. Picking a
winner there would write an unresolved adjudication into a customer file, so they
are refused and left standing where they stay countable.

**`nagpra` went from no Cedar identity at all to 47,114 `cedar_uid` values across
six columns.** That was the readiness agent's stop-item, and the translation closed
it as a side effect rather than by a separate fix.

All 8 rebuilt datasets reconcile exactly: **0 rows lost**, `1137 verify` 0 problems
on 13 datasets, `1165 selftest` 0 detectors failing to fire.

### Detection is by vocabulary, never by shape

A shape regex for the NEID pattern is wrong in both directions, measured: it matches
`DPW-00229-01` inside a contract description and `SR-2012-11` as a subaward number,
and it **misses** the extended Alaska form `AKNF-ACSRMT-00-CALSTA-ASVCPR`, which 298
of the 1,562 real NEIDs use. Membership in the harvested vocabulary is exact.

### A correction to the audit that checks this

`1165` reported *"NO Cedar identity column survives — the dataset can no longer name
an entity"* for `nagpra` and `native-owned-businesses` **after** the translation had
given them 47,114 and 3,547 Cedar uids respectively. Its test asked whether a column
was *named* `cedar_uid`, not whether the file could name an entity. Corrected to
test values as well as names; those two failures were false and are gone, 17 → 15.
