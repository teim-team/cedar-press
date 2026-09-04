# Cedar entity types

*Drafted 2026-09-04 against `data/spine/cedar_identity_register.csv` (1,555 rows)
and `data/spine/cedar_retired_neid_crosswalk.csv` (1,555 rows). Every count in
this file was measured from those two files on that date. Definitions are quoted
or adapted from `docs/CEDAR_TAXONOMY.json` → `layers.entity_class`, which is the
repo's own authored vocabulary; where this document departs from it, it says so.*

---

## What a Cedar entity is, and what `cedar_uid` identifies

A **Cedar entity** is a Native legal person that Cedar treats as a subject in its
own right — a *hub*. It is the thing that can hold a federal identifier, receive
a dollar, sign an instrument, or be named on a federal list. It is deliberately
not every Native-adjacent name in the world: an enterprise a nation owns, a
gaming property it operates, and a school building are all *sub-hubs* of an
entity rather than entities themselves, and they carry their own id families
(`CEDAR-NEST-…`, `CEDAR-PLACE-…`) instead of a `CE-` uid.

Every entity carries a **`cedar_uid`** of the form `CE-1A7K3-MQ`: a namespace,
five characters of Crockford base32, and two check characters computed from two
independent weightings. `I`, `L`, `O` and `U` are absent from the alphabet, so
the classic zero-for-O transcription error is *unrepresentable* rather than
merely detectable, and the two check characters catch 100% of single
substitutions and 100% of adjacent transpositions on the live register.

**The uid encodes nothing, on purpose.**

> "Everything about an entity can change except its identity … An identifier that
> encodes class is an identifier that must be rewritten the day the class
> changes, and rewriting an identity is the one unforgivable act in an identity
> system."
> — `docs/IDENTIFIER_STANDARD.md` §0

So when a state-recognized tribe wins federal recognition, its `entity_class`
changes, its readable handle changes (`TRBS-…` → `TRBF-…`), and **its `cedar_uid`
does not**. No row in any dataset is rewritten, because every row carries the
uid and is already correct. A uid is never reused, even after an entity is
retired.

### The `entity_class` column is the classification. The handle prefix is not.

Rows also carry a retired, class-prefixed handle (`TRBF-ACOMAP-00`,
`ANVC-AFOGNA-00`). That code was **the CICD Native Entity Connector Crosswalk
identifier, inherited from an external source**, and it has been retired from
every dataset — it is preserved in `cedar_retired_neid_crosswalk.csv` so
historical joins keep resolving. It is a display attribute, not an identity, and
it is not a reliable guide to class:

- **`ANVC-`** carries both **Alaska Native Village Corporation** (173) and
  **ANCSA Group Corporation** (6).
- **`CDFI-`** carries both **Native Community Development Financial Institution**
  (64) and **Native Financial Institution** (29).
- **`AKNF-`** carries 228 Alaska Native villages **and one federally recognized
  tribe** — Tlingit & Haida (`CE-0006B-0K`), a regional tribal government rather
  than a village. A documented exception, not a defect.

Grouping on the prefix instead of the class is wrong for **272 entities**. Read
`entity_class`.

The prefixes also come from two different eras, which is why they are not a
coherent scheme. Seven — `TRBF`, `AKNF`, `TRBS`, `CNSF`, `ANRC`, `SGVF`, `CNSS`
— arrived with the NEID seed itself (*"NEID (CICD Native Entity Connector
Crosswalk, Feb 2026) SEEDED the entity spine … 687 entities as delivered, 7
prefixes"*, `AGENTS.md:721`). The other eight — `NHO`, `ITO`, `TCU`, `CDFI`,
`BIE`, `UIO`, `ANVC`, `CEDAR-ENT` — were minted by later Cedar builds as new
classes were added. That split explains the shape of the vocabulary: the NEID
seven are governments and ANCSA corporations, and everything else is a class
Cedar built afterwards.

One further trap: a **compound handle is not a broken one**. `AKNF-MTLKTL-00-TLNGHD`
and `CNSF-MINNCH-LL` are canonical; the AKNF suffixes chain a village to its
regional corporation and consortium. Never strip a suffix to make a join work —
the apparent "base" is generally not in the register at all.

---

## The vocabulary

Seventeen classes, 1,555 rows, no blanks and no spelling variants inside the
register. All 1,555 rows are `register_status = active`.

| rows | `entity_class` | retired prefix |
|---:|---|---|
| 349 | Federally recognized tribe | `TRBF` (348), `AKNF` (1) |
| 228 | Federally recognized Alaska Native Village | `AKNF` |
| 210 | Native Hawaiian Organization | `NHO` |
| 185 | BIE School | `BIE` |
| 173 | Alaska Native Village Corporation | `ANVC` |
| 64 | Native Community Development Financial Institution | `CDFI` |
| 64 | State-recognized tribe | `TRBS` |
| 56 | Intertribal Organization | `ITO` |
| 45 | Individually Native-owned business | `CEDAR-ENT` |
| 43 | Urban Indian Organization | `UIO` |
| 37 | Tribal College or University | `TCU` |
| 29 | Native Financial Institution | `CDFI` |
| 29 | Federal-level self-governance consortium | `SGVF` |
| 22 | Federal-level constituency entity | `CNSF` |
| 12 | Alaska Native Regional Corporation | `ANRC` |
| 6 | ANCSA Group Corporation | `ANVC` |
| 3 | State-level constituency entity | `CNSS` |

---

## Federally recognized tribe — 349 rows

A tribal government on the Secretary of the Interior's list published under
**25 U.S.C. 5131**, excluding the Alaska Native villages, which Cedar holds as a
separate class. It is the **government**, not its companies: a tribal enterprise
is a sub-hub of this entity, never a row of this class.

**Not** the whole federally recognized universe — 349 here plus 228 Alaska Native
villages is **577**, so quoting 349 as "the federally recognized tribes"
understates it by 40%. **Not** a state-recognized tribe.

Examples: `CE-0011W-HN` Pueblo of Acoma (NM) · `CE-0011Y-X7` Ak Chin (AZ).
348 of 349 rows carry a matched Federal Register legal name from the BIA annual
list (FR doc 2026-01899, 91 FR 4102, 2026-01-30).

## Federally recognized Alaska Native Village — 228 rows

An Alaska Native **village government** — a federally recognized tribe that
happens to be a village. It is a separate class because the split is geographic,
not legal; both classes sit on the same 25 U.S.C. 5131 list.

It may own an enterprise directly (ANCSA ruling **rule 3**), and that enterprise
is then an ordinary tribal enterprise. It is **not** an ANCSA corporation in
either direction: a village government never owns an ANC (**rule 2**) and an ANC
never owns the village government (**rule 4**). The two share a name and a place
*by statute*, so a shared name is not weak evidence of one owner — it is no
evidence at all.

Examples: `CE-00001-6S` Asa'carsarmiut · `CE-00003-JB` Agdaagux.
180 of 228 carry a matched Federal Register legal name; 48 are marked
`NOT_IN_SOURCE` — federally recognised, but no roster entry keyed to that uid.

## Native Hawaiian Organization — 210 rows

A Native Hawaiian community organization. **13 C.F.R. 124.110** requires an NHO
to be a **non-profit** organization, and that requirement does the excluding.

**Not** a state agency — the Department of Hawaiian Home Lands is a State of
Hawaii agency and was refused. **Not** an LLC — *Hoilina Ranch LLC* was refused
because an LLC cannot satisfy 124.110. An NHO-**owned** firm is a subsidiary, not
an NHO.

Examples: `CE-000SS-K1` ʻAha Kāne · `CE-000SW-5C` ʻAha Pūnana Leo. All 210 are HI.
This is one of only two classes where `verification_route` is populated on every
row (source: DOI Office of Native Hawaiian Relations roster plus the NHOA
directory, each row with an evidence URL and a verbatim quote).

## BIE School — 185 rows

An elementary or secondary school in the Bureau of Indian Education directory,
split by BIE's own `bie_operation_type` into Bureau-Operated and
Tribally-Controlled.

**Not tribally owned by default.** 56 of the 185 are **federally** operated, and
their blank parent is a ruling, not missing data. BIE's `Navajo_Operation` field
is an administrative grouping, not ownership — trusting it books 35 schools to
the Navajo Nation. Post-secondary institutions are **not** here; they belong to
Tribal College or University.

Examples: `CE-000D5-ZD` Ahfachkee School (FL) · `CE-000D6-56` Alamo Navajo
Community School (NM).

## Alaska Native Village Corporation — 173 rows

A for-profit corporation organised under **ANCSA §8, 43 U.S.C. 1607**, for a
named Alaska Native village.

**Not** the village government. **Not** a subsidiary of its regional corporation
— ANCSA ruling **rule 5**: they are two corporations with an overlapping
shareholder base, and treating the regional as owner once moved **$32.87B**
wrongly.

**And today, not only village corporations.** The four ANCSA **Urban**
Corporations sit in this class because Cedar has no class for them; 43 U.S.C.
1607(c) names them as a distinct statutory form. Recorded as the gap
`ANCSA_URBAN_CORPORATION_HAS_NO_CLASS`.

Examples: `CE-0007J-FJ` Afognak Native Corporation · `CE-0007K-NB` Akutan
Corporation.

## Native Community Development Financial Institution — 64 rows

An institution carrying **US Treasury CDFI Fund certification** with the
`Native CDFI (Y/N)` flag set. The certification is what qualifies it; nothing
else does.

**Not** the same as *Native Financial Institution*, which is the broader
Minneapolis Fed NAFI universe without Treasury certification. Both classes sit
under the retired `CDFI-` prefix, so the prefix does not identify the class here.
The edge written for this class is `chartered_by` and never `subsidiary_of`, so
no dollar rolls through it.

Examples: `CE-000JY-EE` Akiptan, Inc. (SD) · `CE-000JZ-M7` Bay Bank (WI).

## State-recognized tribe — 64 rows

A tribe recognised by a **state** and not by the United States. It has no ISDEAA
relationship, no 25 U.S.C. 5131 listing, and it is **not** eligible under the
SLFRF definition of "Tribal government" at **42 U.S.C. 802(g)(7)**. Pooling it
with the federal class changes the recipient universe, which is why it is a
separate class rather than an attribute.

Examples: `CE-001CP-4F` Accohannock Indian Tribe (MD) · `CE-001CQ-A8` Adai Caddo
Indians of Louisiana (LA).

## Intertribal Organization — 56 rows

An organisation whose **members** are tribes.

**Not** owned by its member tribes — membership is recorded as `member_of` /
`affiliated_with`, both of which sit in `NEVER_OWNERSHIP`, so no dollar rolls
from the organisation up to a member. Distinguished from a self-governance
consortium by function: an intertribal organization represents or convenes; it
does not hold a member's ISDEAA self-governance compact in its own name.

Examples: `CE-000R1-YS` Inter Tribal Council of Arizona, Inc. · `CE-000R3-AB`
Inter-Tribal Council of California, Inc.

## Individually Native-owned business — 45 rows

An ordinary firm — LLC, S-corp, sole proprietorship — whose **owner is an
individual Native person**. Ruled into existence by the owner on 2026-08-07.

**Not** a tribal entity, **not** a false positive, and **not** excluded from the
product; it simply never rolls up. `parent_native_entity` is permanently NULL and
**that blank is a ruling**. Five of the 45 rulings read *"Not a Native entity —
individually Native-owned firm"*, which refuses the **tribal link** and
**affirms** Native ownership; read literally as "not Native" it inverts the
owner's meaning, and it already has once.

**Publication rule:** `may_publish_individual_native_field()` withholds every
name and address, and — for a firm whose legal name is a person's — the UEI and
CAGE, absent recorded `OPTED_IN` consent. Example uids `CE-000NV-BK` and
`CE-000NW-HC`; names are withheld here under that rule.

## Urban Indian Organization — 43 rows

A non-profit in the IHS Urban Indian Organization programme holding a **Title V
Indian Health Care Improvement Act** contract with the Indian Health Service,
serving Native people in an urban area.

**Not tribally owned — owned by no tribe at all.** It serves people of many
tribal affiliations because that is the design of the programme, not a gap in the
data. Serving a population is not being owned by it: `serves_native_entities` is
never evidence of ownership. **Not** resolvable by place name — *Riverside San
Bernardino County Indian Health Inc* was refused an autoresolution to
`UIO-HEALTH-00`, which is "Native Health", **Arizona**.

Examples: `CE-001EP-EF` Bakersfield American Indian Health Project (CA) ·
`CE-001FZ-90` Seattle Indian Health Board (WA).

## Tribal College or University — 37 rows

A tribally chartered or federally chartered post-secondary institution in the
**AIHEC** roster (34 regular, 1 associate, 2 developing members).

**Not** its chartering tribe. The edge written is `chartered_by`, which is not in
`OWNERSHIP_BEARING`: a tribe chartering a college does not own it, and the
college's federal dollars are not the tribe's. Before this class existed,
name-containment resolved *Bay Mills Community College* onto the Bay Mills Indian
Community and *United Tribes Technical College* onto United Auburn Rancheria.
**Not** a BIE School.

Examples: `CE-0010N-2P` Blackfeet Community College (MT) · `CE-0010P-8F` Bay Mills
Community College (MI).

## Native Financial Institution — 29 rows

A Native-controlled financial institution in the **Minneapolis Fed NAFI**
universe that is **not** a certified Native CDFI. The distinction from the CDFI
class is Treasury certification and nothing else, and that single fact is the
whole reason the two classes exist separately. Shares the retired `CDFI-` prefix
with certified Native CDFIs, so the prefix cannot tell them apart.

Examples: `CE-000K0-ZG` Black Hills Community Loan Fund (SD) · `CE-000KF-S7`
Eagle Bank (MT).

## Federal-level self-governance consortium — 29 rows · **partial**

Cedar's stated definition is *"a consortium of tribes exercising self-governance
authority jointly"*, and it is **not** an owner of its member tribes' activity
and **not** owned by them.

**The definition and the data have drifted apart.** It was written when the class
held **9** Alaska regional consortia (Association of Village Council Presidents,
Tanana Chiefs Conference, Maniilaq, Kawerak and similar). The class now holds
**29** rows, and the 20 added since include single-facility health corporations
in CA, AZ, UT and OK — *Winslow Indian Health Care Center*, *Chapa-De Indian
Health Program*, *Feather River Tribal Health* — which hold ISDEAA Title V
compacts but are not obviously consortia *of tribes*.

Treat the operative test as **"holds an ISDEAA self-governance compact in its own
name"**, and read the row before relying on the class name.

Examples: `CE-0010B-6W` Association of Village Council Presidents (AK) ·
`CE-0010M-WX` Tanana Chiefs Conference, Incorporated (AK).

## Federal-level constituency entity — 22 rows · **partial**

A constituent band, community or pueblo sitting inside an umbrella tribal
government which is itself the federally listed entity — the Minnesota Chippewa
Tribe's six bands, the five bands of the Paiute Indian Tribe of Utah, the four
Te-Moak bands, the two Fort Hall bands.

**Not a subsidiary.** `constituent_band_of` sits in `GOVERNMENTAL_RELATIONSHIPS`
and therefore in `NEVER_OWNERSHIP`: a band's contracts are not the umbrella's.
Mapping a flat parent column wholesale would have rolled all 22 into their
umbrellas.

**Unresolved:** Cedar's taxonomy says such a band is *"itself named on the
federal list"*, but the register marks 21 of the 22 rows
`OUT_OF_SCOPE_BY_CONSTRUCTION — this entity class is not listed in the BIA annual
list`. See FINDINGS.

Examples: `CE-000QF-D7` Leech Lake (MN) · `CE-000QT-FT` Te-Moak Tribe of Western
Shoshone Indians of Nevada – Battle Mountain Band (NV).

## Alaska Native Regional Corporation — 12 rows

One of the in-state for-profit corporations organised under **ANCSA §7,
43 U.S.C. 1606**.

**Not** the owner of the village corporations in its region (ANCSA ruling
**rule 5**) and **not** a place: `associated_with_region` is geography, and
treating it as ownership once moved **$32.87B** wrongly. Cedar holds 12; ANCSA's
thirteenth region is the out-of-state region and is not held here.

Examples: `CE-00076-76` Ahtna, Incorporated · `CE-00078-KR` Arctic Slope Regional
Corporation.

## ANCSA Group Corporation — 6 rows

A corporation organised for a Native **group** under ANCSA rather than for a
village, named at **43 U.S.C. 1607(c)** — which applies 43 U.S.C. 1606(g), (h)
and (o) identically to Village, Urban and Group Corporations.

**Not** a village corporation, though it shares the retired `ANVC-` prefix — the
second place in Cedar where the prefix does not identify the class. Like the
village corporations it is a for-profit ANCSA corporation, and it is never owned
by, and never owns, a tribal government.

The complete class: `CE-0008G-8G` Caswell Native Association, Inc. ·
`CE-000AF-CQ` Olsonville, Inc. · `CE-000AH-R9` Alexander Creek, Inc. ·
`CE-000AP-P6` Montana Creek Native Association, Inc. · `CE-000BG-Q0` Point
Possession, Inc. · `CE-000CE-GY` Tanalian, Inc.

## State-level constituency entity — 3 rows · **partial**

Cedar's stated definition is *"a constituent group inside a state-recognized
tribe"*, **not** federally recognized and **not** a subsidiary.

The class holds only three rows and the definition does not describe all of them.
`CE-000QY-7Y` Schaghticoke Tribal Nation and `CE-000QZ-DQ` Schaghticoke Indian
Tribe (both CT) fit. `CE-000R0-R0` **Trenton Indian Service Area** (ND) carries
the handle `CNSS-TURTLM-TR` and is a service area associated with the Turtle
Mountain Band of Chippewa, which is **federally** recognized. Read the row; do
not infer the parent's recognition status from the class name.

---

## Types that do not exist in this vocabulary

- **Tribally Designated Housing Entity (TDHE).** Deliberately absent. *"A TDHE is
  not its tribe. The entity spine holds no tribally designated housing entity"*
  (`docs/ADMIN_REGION_CROSSWALK_LOG.md`). HUD's 148 distinct TDHEs are recorded
  by published name with **no** `subject_id`, precisely so a housing authority's
  dollars are never booked to the tribe it serves. One housing authority
  (Bristol Bay Housing Authority, `CE-000R2-4J`) does sit in the spine, classed
  `Intertribal Organization`.
- **ANCSA Urban Corporation.** A real statutory form (43 U.S.C. 1607(c)) with no
  Cedar class; its four members are carried as *Alaska Native Village
  Corporation*.
- **Section 17 corporation, tribal enterprise, gaming property, IHS facility.**
  These are sub-hubs, not entities: they carry `CEDAR-NEST-…` and
  `CEDAR-PLACE-…` ids and never a `CE-` uid.
