# The Native entity legal-form registry

*Written 2026-09-03. **Every statutory quotation below was retrieved from the
host named beside it on 2026-09-03**; nothing here is paraphrased from memory or
taken from a secondary summary. **Every count below came from a command run
against a named file on 2026-09-03**; nothing is estimated and nothing is
sampled. Where a thing could not be measured it says NOT MEASURED, and where a
source could not be retrieved it says NOT RETRIEVED.*

**Companions.** `docs/IDENTIFIER_STANDARD.md` is the policy (what a `cedar_uid`
IS). `docs/NATIVE_ENTITY_NUANCES.md` is the name knowledge (which nation a
string denotes). `docs/ANCSA_OWNERSHIP_RULING.md` is the owner's Alaska ruling.
**This file is the third leg: what KIND of legal person a name denotes, and
therefore what a `cedar_uid` is permitted to do with it.** It does not restate
any of the three; it cites them.

**Machine-readable companion:** `review/native_legal_forms_registry.json`,
emitted by `code/1164_native_legal_forms_classifier.py registry`. The identity
layer consumes that, not this prose.

---

## 0. WHY THIS EXISTS — the two cases that produced it

**Case 1, repaired.** `AMEE BAY, LLC` and `OCEAN BAY INFORMATION & SYSTEMS` were
keyed to the **Three Affiliated Tribes of North Dakota** on the token `Three`,
reaching them through their intermediate holding company `THREE SAINTS BAY,
LLC`. They belong to **Old Harbor Native Corporation**, an ANCSA *village*
corporation on Kodiak Island. Repaired 2026-09-02 by
`code/1075_fix_old_harbor_attribution.py`. **Re-measured for this pass on
2026-09-03** in `data/clean/prime_contracts.csv`: both UEIs
(`FGELS2KFR825`, `NW3JPQEZRPK1`) now resolve to one row —
`CE-000A9-81 / ANVC-LDHRBR-00 / Old Harbor Native Corporation`, method
`uei_exact`, **4,947 rows, $449,376,831.04**. Clean. It is quoted here as the
error CLASS, not as a live defect.

**Case 2, live.** `BERING STRAITS REGIONAL HOUSING AUTHORITY` is keyed to
`ANRC-BERSTR-00`, **Bering Straits Native Corporation**. It is not that, and it
is not a tribe either. It is a **public body corporate and politic** created by
Alaska Statute 18.55.996(b), and the association the statute names as its
sponsor is **Kawerak, Inc.** — a third entity again, which Cedar also holds
(`SGVF-KAWRAK-00`). Measured 2026-09-03 in
`data/clean/federal_funding_transactions.csv`: **34 rows, $158,057,698.49**.

Both are one failure: **a string won, because nothing in the pipeline knew what
KIND of legal person the string names.**

---

## 1. THE DISPOSITION VOCABULARY

Five values. `code/1164_native_legal_forms_classifier.py verify` (check V2)
exits 1 on any other.

| disposition | meaning |
|---|---|
| `HUB` | a `cedar_uid` subject in its own right |
| `HUB_DISTINCT_FROM_NAMESAKE` | a hub, **and** it shares a place name with a hub of another form. The two may never merge, and a matcher must never reach one from the other's name |
| `SUB_HUB_ROLLS_UP` | not a hub. Keys to a **named** owner hub, per `docs/IDENTIFIER_STANDARD.md` §2 |
| `MANY_TO_MANY_NO_SINGLE_HUB` | structurally serves, or is authorised by, **many** hubs. Any single `cedar_uid` is false — not merely uncertain |
| `NOT_A_NATIVE_ENTITY` | must be excluded, with the reason recorded. Any Cedar key on it is a defect |

`MANY_TO_MANY_NO_SINGLE_HUB` is new on 2026-09-03 and exists because of the TDHE
class. It is not a weaker `HUB`. It says the question "which one entity owns
this?" has **no true answer**, and that forcing one is a fabrication rather than
a guess.

---

## 2. THE FORMS

Sixteen. Ordered as the mandate ordered them, with the additions at §2.12.

---

### 2.1 Federally recognized tribe / tribal government — `TRIBE_FEDERALLY_RECOGNIZED`

**Statute.** 25 U.S.C. §5123 (Indian Reorganization Act §16); the list is
published under 25 U.S.C. §5131.
`https://www.govinfo.gov/content/pkg/USCODE-2024-title25/html/USCODE-2024-title25-chap45-sec5123.htm`

> **(a) Adoption; effective date**
> Any Indian tribe shall have the right to organize for its common welfare, and
> may adopt an appropriate constitution and bylaws, and any amendments thereto,
> which shall become effective when— (1) ratified by a majority vote of the
> adult members of the tribe or tribes at a special election authorized and
> called by the Secretary … and (2) approved by the Secretary …

> **(h) Tribal sovereignty**
> Notwithstanding any other provision of this Act— (1) each Indian tribe shall
> retain inherent sovereign power to adopt governing documents under procedures
> other than those specified in this section …

**What it legally IS.** A sovereign. §5123(h)(1) is decisive on the point that
matters for a registry: the IRA **recognises** the power, it does not grant it,
so a tribe that never organised under §16 is no less a tribe.

**Members / owner.** Enrolled members as its own constitution defines them.
**Owned by nobody** — a sovereign is not property.

**`cedar_uid` disposition: `HUB`.**

**Name patterns.** None are safe as a *class* signal. Do not try. The Federal
Register list is the authority; `docs/NATIVE_ENTITY_NUANCES.md` carries the
renames and the parenthetical bands. Two live traps recorded there apply here:
a nation's whole name can be an ordinary English word (`Enterprise`,
`Eagle`, `Circle`, `Council`, `Wales`), and a place suffix makes a tribe name a
place.

**Measured in Cedar (2026-09-03, `data/spine/cedar_entity_spine.csv`, 1,555
rows).** `entity_class = Federally recognized tribe` **349**;
`Federally recognized Alaska Native Village` **228**.

---

### 2.2 Section 17 federally chartered corporation — `CORP_IRA_SECTION_17`

**Statute.** 25 U.S.C. §5124 (IRA §17), the whole operative text.
`https://www.govinfo.gov/content/pkg/USCODE-2024-title25/html/USCODE-2024-title25-chap45-sec5124.htm`

> The Secretary of the Interior may, upon petition by any tribe, issue a charter
> of incorporation to such tribe: *Provided,* That such charter shall not become
> operative until ratified by the governing body of such tribe. Such charter may
> convey to the incorporated tribe the power to purchase, take by gift, or
> bequest, or otherwise, own, hold, manage, operate, and dispose of property of
> every description … but no authority shall be granted to sell, mortgage, or
> lease for a period exceeding twenty-five years any trust or restricted lands
> included in the limits of the reservation. Any charter so issued shall not be
> revoked or surrendered except by Act of Congress.

**HOW IT DIFFERS FROM THE §16 GOVERNMENT, AND WHY THE SEPARATENESS IS
DOMAIN-SPLIT.** This is the part a registry gets wrong if it stores one boolean.

**The statute does not say they are separate legal persons.** It says "a charter
… to such tribe" and "the incorporated tribe". There is no separateness clause.
The doctrine is built on top of that one paragraph, and it points **two
different ways depending on the domain**:

*Separate — for liability and asset protection.* BIA, the chartering agency,
`https://www.bia.gov/service/starting-business/choosing-tribal-business-structure`:

> **Preserves tribal assets**: A Section 17 corporation is wholly owned by the
> tribe, but is separate and distinct from the tribal government. If the
> corporation defaults on the payment of funds it has borrowed, only the
> corporation's property and assets are at risk.

*Separate — as a matter of the IRA's design.* Rev. Rul. 81-295, 1981-2 C.B. 15,
`https://www.irs.gov/pub/irs-tege/rr81_295.pdf`:

> Before enactment of the Indian Reorganization Act, both the business and the
> governmental functions of the tribe were conducted by a single tribal entity.
> **The Act allows for a dual mechanism by which governmental affairs are
> conducted under a constitution and bylaws adopted under section 16 of the Act
> and commercial matters are handled by a business corporation organized under
> section 17 of the Act.**

*NOT separate — for federal income tax.* Treas. Reg. §301.7701-1(a)(4), as
finalised at 90 Fed. Reg. 58151 (2025-12-16), effective 2026-01-15,
`https://www.govinfo.gov/content/pkg/FR-2025-12-16/html/2025-22874.htm`:

> **(4) Certain Tribal entities—(i) In general—(A) Rule.** Except as provided in
> paragraphs (a)(4)(ii) and (iii) of this section, section 17 corporations,
> section 3 corporations, and wholly owned Tribal entities … **are not
> recognized as separate entities for Federal tax purposes** and, therefore, are
> not subject to Federal income tax.

> **(iii) Federal employment taxes and excise taxes.** Section 17 corporations,
> section 3 corporations, and wholly owned Tribal entities **are treated as
> separate entities** for Federal employment and certain Federal excise tax
> purposes …

**So: separate for liability, separate as an institution, disregarded for income
tax, separate again for employment tax.** A single `is_separate_entity` flag is
wrong in at least one domain whichever way it is set. Store the domain.

**Members / owner.** The enrolled members of the chartering tribe. In the
classic charter form (Rev. Rul. 81-295): *"each enrolled member of the tribe is
issued a nontransferrable certificate of ownership evidencing his or her equal
share in the corporation's assets."* **Wholly owned by the tribe. No outside
shareholder is possible.**

**`cedar_uid` disposition: `SUB_HUB_ROLLS_UP`** to the chartering tribe's hub.
Cedar's hub model (`IDENTIFIER_STANDARD.md` §2) already puts a corporate arm
under its nation; the tax law agrees for income-tax purposes and BIA disagrees
for liability purposes, and neither of those is a question about *whose money
this is*, which is the question `cedar_uid` answers. **But record the §17
charter as a relationship edge**, because it is the fact that decides whether a
judgment can reach tribal assets, and Cedar will be asked.

**Name patterns.** `section 17`, `federally chartered corporation`. There is no
suffix convention — a §17 corporation is often named identically to its tribe,
which is exactly why it must be evidenced from the charter and never from a
name.

**Measured in Cedar.** **ZERO.** `data/spine/cedar_entity_spine.csv` has no
`entity_class` for it and no row whose any field matches `section 17` /
`federally chartered` / `federal charter` (scanned all 1,555 rows × all 43
columns, 2026-09-03). Cedar cannot currently tell a §16 government from its §17
corporation, in either direction. **This is a gap, not an error** — nothing is
mis-keyed, because the distinction is not represented at all.

---

### 2.3 ANCSA regional corporation — `ANCSA_REGIONAL_CORPORATION`

**Statute.** 43 U.S.C. §1606 (ANCSA §7); definition at §1602(g).
`https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1606.htm`
·
`https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1602.htm`

> **§1606(d)** Five incorporators within each region, named by the Native
> association in the region, **shall incorporate under the laws of Alaska a
> Regional Corporation to conduct business for profit**, which shall be eligible
> for the benefits of this chapter so long as it is organized and functions in
> accordance with this chapter.

> **§1602(g)** "Regional Corporation" means an Alaska Native Regional
> Corporation **established under the laws of the State of Alaska** in
> accordance with the provisions of this chapter;

> **§1606(h)(1)(A)** … Settlement Common Stock of a Regional Corporation shall—
> (i) carry a right to vote in elections for the board of directors …; (ii)
> permit the holder to receive dividends or other distributions …; and **(iii)
> vest in the holder all rights of a shareholder in a business corporation
> organized under the laws of the State.**

**The thirteenth.**

> **§1606(c)** If a majority of all eligible Natives eighteen years of age or
> older who are **not permanent residents of Alaska** elect, pursuant to section
> 1604(c) of this title, to be enrolled in a thirteenth region for Natives who
> are non-residents of Alaska, the Secretary shall establish such a region …
> and they may establish a Regional Corporation pursuant to this chapter.

> **§1606(i)(1)(A)** … The provisions of this subsection shall not apply to the
> thirteenth Regional Corporation if organized pursuant to subsection (c)
> hereof.

**What it legally IS.** An Alaska **state-chartered business corporation for
profit**. CRS R46997, `https://www.congress.gov/crs-product/R46997`:
*"Because ANCs are business entities, they are unlike federally recognized
tribes, which have government-to-government relationships with the United
States."*

**Members / shareholders.** Individual Alaska Natives enrolled to the region.
Not a membership organisation and not a tribal roll — and per
`docs/ANCSA_OWNERSHIP_RULING.md` rule 4, *"a shareholder is not necessarily
enrolled in the tribe. A shareholder necessarily has ancestry."*

**WHO OWNS IT.** Its shareholders — **natural persons**. **No tribe owns an
ANCSA regional corporation, and it owns no tribe.** The regional corporation
also does **not** own the village corporations in its region
(`ANCSA_OWNERSHIP_RULING.md` rule 5).

**`cedar_uid` disposition: `HUB`.**

**Name patterns.** The thirteen, from GAO-13-121 Table 1 (source line:
"Source: Department of the Interior"), `https://www.gao.gov/assets/660/651222.txt`:
Ahtna, Incorporated · The Aleut Corporation · Arctic Slope Regional Corporation
· Bering Straits Native Corporation · Bristol Bay Native Corporation · Calista
Corporation · Chugach Alaska Corporation · Cook Inlet Region, Inc. · Doyon,
Limited · Koniag, Incorporated · NANA Regional Corporation · Sealaska
Corporation · **The 13th Regional Corporation**.

⚠ **Do not seed from BLM's contact list.** The 2024 NPA contact list
(`https://www.blm.gov/sites/default/files/docs/2023-06/Tribes-AK-Native-Corp-Contacted-list_nPA_20230623.pdf`)
labels **Alaska Peninsula Corporation** — a merged *village* corporation — as a
regional corporation, omits The 13th entirely, and files the four urban
corporations under "Alaska ANCSA Village Corporation". Use GAO-13-121 for the
regional list and BLM only as a spelling crosswalk.

**Measured in Cedar.** `entity_class = Alaska Native Regional Corporation`
**12**. **The 13th Regional Corporation is not in the spine.** It IS in
`data/clean/anc_ceiling_roster.csv` — one row, `anc_class = ANC_REGIONAL`,
`row_disposition = CANONICAL_THIRTEENTH_REGIONAL`, **`cedar_uid` blank,
`entity_resolution_status = unresolved`**.

*Status of The 13th, so a reader does not mint it carelessly.* GAO-13-121:
*"the 13th Regional Corporation has experienced long-standing financial
difficulties and has largely been insolvent since 2007 … The last annual meeting
held to elect board directors was in 2006."* The ANCSA Regional Association
(**industry source, not federal**),
`https://ancsaregional.com/about-ancsa/`: *"In 2013, the 13th Regional
Corporation was involuntarily dissolved by the State of Alaska when their
registered agent resigned."* **The State of Alaska corporate record is NOT
RETRIEVED** — `commerce.alaska.gov` serves a JS anti-bot challenge and answered
403 to every attempt. Confirm the dissolution against the State before Cedar
asserts it.

---

### 2.4 ANCSA village corporation — `ANCSA_VILLAGE_CORPORATION`

**THIS IS THE ERROR CLASS CEDAR KEEPS MAKING. The disposition rule at the end of
this section is written so a script can apply it.**

**Statute.** 43 U.S.C. §1607(a) (ANCSA §8); definition at §1602(j).

> **§1607(a)** **The Native residents of** each Native village entitled to
> receive lands and benefits under this chapter **shall organize as a business
> for profit or nonprofit corporation under the laws of the State** before the
> Native village may receive patent to lands or benefits under this chapter …

> **§1602(j)** "Village Corporation" means an Alaska Native Village Corporation
> **organized under the laws of the State of Alaska** as a business for profit
> or nonprofit corporation to hold, invest, manage and/or distribute lands,
> property, funds, and other rights and assets **for and on behalf of a Native
> village** …

**WHY THE CORPORATION IS A DIFFERENT LEGAL PERSON FROM THE VILLAGE TRIBE.**
Four independent grounds, each retrievable:

1. **The subject of §1607(a) is "the Native RESIDENTS", not the village.** The
   individuals organise the corporation. The village does not become it.
2. **Different sovereign creates each.** The corporation is created "under the
   laws of the State of Alaska" (§1602(j)). The tribe exists by federal
   recognition and appears on the BIA list published under 25 U.S.C. §5131.
3. **The two federal rosters do not overlap.** The BIA list —
   `https://www.federalregister.gov/documents/full_text/text/2026/01/30/2026-01899.txt`,
   *"Native Entities Within the State of Alaska Recognized by and Eligible To
   Receive Services From the United States Bureau of Indian Affairs"* — lists
   tribal entities. **No ANCSA corporation appears on it.** The same place name
   appears as a tribe there and as a corporation in the ANCSA corporate lists,
   and they are different rows in different registers.
4. **The owner has already ruled it**, `docs/ANCSA_OWNERSHIP_RULING.md` rule 2:
   *"A village GOVERNMENT never owns an ANC."*

**Members / shareholders.** Individual Alaska Natives enrolled to the village.
**Not the same population as the tribal roll** — ANCSA shares descend by
inheritance and gift (43 U.S.C. §1606(h)(1)(C), §1606(h)(2)) while village
enrolment closed long ago.

**WHO OWNS IT.** Its shareholders. Not the village government, not the regional
corporation, not any tribe.

**`cedar_uid` disposition: `HUB_DISTINCT_FROM_NAMESAKE`.**

#### THE DISPOSITION RULE, IN A FORM A SCRIPT CAN APPLY

```
GIVEN  a row carrying a NAME and a cedar_uid
1. FOLD the name for comparison using case, diacritics and punctuation ONLY.
   NEVER fold a corporate suffix. Do NOT strip INC / LLC / LTD / CORPORATION /
   CORP / ASSOCIATION / COMPANY / THE.
2. Look the folded name up in the ADJUDICATED namesake table
   `review/village_corp_namesake_pairs.csv` (77 pairs, corporation <-> village
   government) and in the spine's own canonical names.
3. IF the name matches the CORPORATION side of a pair
     AND the row's cedar_uid resolves (via the spine, NOT via the handle prefix)
         to the GOVERNMENT side of that same pair
   THEN the row is WRONG. Flag it. Target = the corporation's cedar_uid.
4. IF the name matches the GOVERNMENT side and the key is the CORPORATION,
   flag it the other way. The rule is symmetric.
5. NEVER auto-repoint on a name alone. The flag is a proposal.
```

**Why step 1 is stated as a prohibition.** Stripping `INC` / `CORPORATION` /
`THE` "resolves" `Eklutna, Inc.` to `Eklutna` and `The Port Graham Corporation`
to `Port Graham` in one line, and **merges a village government into its ANCSA
corporation** — the exact assertion §1607(a) and the BIA list refute.
`code/1164_native_legal_forms_classifier.py::_fold` folds nothing but case,
diacritics and punctuation, and `selftest` asserts
`_fold("Eklutna, Inc.") != _fold("Eklutna")` and
`_fold("The Port Graham Corporation") != _fold("Port Graham")`. The sibling trap,
from the NEST audit: indexing **head tokens** turns `white`, `arctic`, `old` and
`port` into brands and would repoint nine White Earth bodies to an Alaska
corporation. Neither end of the name is safe to shorten.

**Why step 2 says the spine and not the prefix.** `AGENTS.md:3977`: **"THE
PREFIX DOES NOT IDENTIFY THE CLASS."** `ANVC-` spans village *and* group
corporations; `CDFI-` spans Native CDFIs *and* Native Financial Institutions.
`41_build_codebooks.py:1338-1340` instructs *"Join to the spine on this prefix"*
and that instruction is **wrong for 272 entities**. Script 1164 reads
`entity_class` off the spine row and never parses the handle. *(Cedar's own
`ANCSA Group Corporation` class is a live instance: all six carry `ANVC-`
handles — see §2.6.)*

**Measured in Cedar (2026-09-03).**

| measurement | file | value |
|---|---|---|
| `entity_class = Alaska Native Village Corporation` | `data/spine/cedar_entity_spine.csv` | **173** |
| adjudicated corporation ↔ village-government namesake pairs | `review/village_corp_namesake_pairs.csv` | **77** (76 of the government sides resolve in the spine) |
| prior repointings already applied | `review/village_government_corrections.csv` | **317** |
| **prime_contracts rows where an adjudicated corporation NAME sits on its own village GOVERNMENT key** | `data/clean/prime_contracts.csv` (all 1,217,768 rows) | **0** |
| **ledger rows, same test** | `data/clean/cedar_identifier_ledger_final.csv` (all 20,740 rows) | **3** — `CAGE:684D6 EKWOK NATIVES LTD`, `CAGE:6VFU2 AKHIOK-KAGUYAK, INC.`, `CAGE:51B71 NINILCHIK NATIVES ASSOCIATION, INC.`, all tier B, all `need_v6` |
| ledger rows whose `legal_business_name` is the **exact** canonical name of a spine ANCSA village corporation but whose key is a village GOVERNMENT | same | **9** (`review/native_legal_forms_crossform_names_2026-09-03.csv`) |
| the 2026-08-26 ANCSA ruling's own repointing | `docs/ANCSA_OWNERSHIP_RULING.md` | 3,883 rows over three files |

**The prime table is clean on the strict test and that is a measured result, not
an assumption.** The 2026-08-26 application did its job. What survives is in the
ledger and in the owner queue, and it survives because those rows were never
name-identical to the adjudicated corporation name — which is precisely why the
rule above keys off the pair table and the spine rather than off a suffix.

---

### 2.5 ANCSA urban and group corporations — `ANCSA_URBAN_CORPORATION`, `ANCSA_GROUP_CORPORATION`

**Statute.** 43 U.S.C. §1613(h). **The numbering is the reverse of what is
usually assumed: (h)(2) is GROUP, (h)(3) is URBAN.**
`https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1613.htm`

> **§1613(h)(2)** The Secretary may withdraw and convey **to a Native group that
> does not qualify as a Native village, if it incorporates under the laws of
> Alaska**, title to the surface estate in not more than 23,040 acres
> surrounding the Native group's locality …

> **§1613(h)(3)** The Secretary may withdraw and convey **to the Natives
> residing in Sitka, Kenai, Juneau, and Kodiak, if they incorporate under the
> laws of Alaska**, the surface estate of lands of a similar character in not
> more than 23,040 acres of land …

Both have their own definitions, so neither is a species of village corporation:

> **§1602(o)** "Urban Corporation" means an Alaska Native Urban Corporation
> organized under the laws of the State of Alaska …
> **§1602(n)** "Group Corporation" means an Alaska Native Group Corporation
> organized under the laws of the State of Alaska …
> **§1602(d)** "Native group" means any tribe, band, clan, village, community,
> or village association of Natives in Alaska **composed of less than
> twenty-five Natives**, who comprise a majority of the residents of the
> locality;

S. Rept. 118-221,
`https://www.govinfo.gov/content/pkg/CRPT-118srpt221/pdf/CRPT-118srpt221.pdf`:

> Section 14(h)(3) of ANCSA (43 U.S.C. 1613(h)(3)) authorized the conveyance of
> 23,040 acres of surface lands to four communities in Southeast: Juneau, Sitka,
> Kenai, and Kodiak, **even though those communities did not meet the
> requirements to be recognized as a Native Village Corporation under ANCSA.**

> Under ANCSA, Alaska Natives received title to a total of 44 million acres to
> be divided among the **220 Native village corporations, four urban
> corporations, and 12 regional corporations** established by the Act.

**Members / owner.** Individual Alaska Native shareholders of that place or
group. Owned by its shareholders.

**`cedar_uid` disposition: `HUB`** for both.

**Measured in Cedar (2026-09-03, `data/spine/cedar_entity_spine.csv`).**

- **`ANCSA Group Corporation` = 6**: Alexander Creek, Inc. · Caswell Native
  Association, Inc. · Montana Creek Native Association, Inc. · Olsonville, Inc.
  · Point Possession, Inc. · Tanalian, Inc. **All six carry an `ANVC-` handle**,
  which is the `AGENTS.md:3977` prefix warning demonstrated inside Cedar's own
  register. The class column is right; the prefix is not, and nothing should
  read the prefix.
- **`ANCSA Urban Corporation` does not exist as a Cedar class.** All four urban
  corporations are held as `Alaska Native Village Corporation`:
  **Goldbelt, Incorporated** (`ANVC-GLDBLT-00`, Juneau) ·
  **Kenai Natives Association, Inc.** (`ANVC-KNNTVS-00`, Kenai) ·
  **Natives of Kodiak, Inc.** (`ANVC-NTVSKD-00`, Kodiak) ·
  **Shee Atika, Incorporated** (`ANVC-SHEEAT-00`, Sitka).
  *Caveat that must travel with this:* mapping those four **entities** to the
  four §1613(h)(3) **communities** is an inference from their addresses.
  **NOT RETRIEVED:** any federal source that labels these four as "urban
  corporations". BLM's own Section 207 report files all four under
  `ANCSAVILLAGECORPS`. Treat the four names as a proposal, and the *class gap*
  as the settled finding.

**Why the misclassification is not cosmetic.** A village corporation's land
entitlement, its §14(c) reconveyance obligations and its relationship to a
Native village under §1602(c) all follow from §1607. An urban corporation has
none of that; its entitlement is a flat 23,040-acre grant under §1613(h)(3) and
there is **no Native village behind it at all** — which means there is no
namesake village tribe, and the §2.4 disposition rule must not be applied to
these four.

---

### 2.6 TDHE / Indian housing authority, and the Alaska regional housing authorities — `TDHE_NAHASDA`, `AK_REGIONAL_HOUSING_AUTHORITY`

**Statute — federal.** 25 U.S.C. §4103 (NAHASDA definitions), §4111 (block
grants). `https://www.govinfo.gov/link/uscode/25/4103?link-type=html`

> **§4103(22)(A)** With respect to any Indian tribe that has not taken action
> under subparagraph (B), and for which an Indian housing authority … the terms
> mean such Indian housing authority.

> **§4103(22)(B)** With respect to any Indian tribe that, pursuant to this
> chapter, authorizes an entity other than the tribal government to receive
> grant amounts and provide assistance under this chapter for affordable housing
> for Indians, which entity is established … **(ii) by operation of State law
> providing specifically for housing authorities or housing entities for
> Indians, including regional housing authorities in the State of Alaska** …
> the terms mean such entity.

> **§4103(22)(C)** A tribally designated housing entity **may be authorized or
> established by one or more Indian tribes to act on behalf of each such tribe**
> authorizing or establishing the housing entity.

> **§4103(19)** The term "recipient" means an Indian tribe **or the entity for
> one or more Indian tribes** that is authorized to receive grant amounts under
> this chapter on behalf of the tribe or tribes.

> **§4111(a)(2)** Under such a grant on behalf of an Indian tribe, the Secretary
> shall provide the grant amounts for the tribe **directly to the recipient for
> the tribe**.

**The statute names the Alaska class by name.** §4103(22)(B)(ii) is the only
place in the definition that names a *state* creature, and the thing it names is
"regional housing authorities in the State of Alaska". So this is not an edge
case Cedar has to reason its way into; Congress put it in the definition.

**Statute — Alaska state law, which is where these actually come from.**
AS 18.55.995 and AS 18.55.996, Article 04 "Regional Native Housing Authorities".

> **AS 18.55.995 Purpose and intent.** "The legislature finds that an acute
> shortage of housing and related facilities exists in the villages of the state
> and that adequate housing cannot be provided by the private sector due to the
> economic depression that exists in most villages of the state. It is the
> purpose and intent of the legislature **to provide a means for certain Native
> associations to form public corporations** with the powers and duties
> comparable to those provided in AS 18.55.100 - 18.55.960."
> `https://law.onecle.com/alaska/title-18/18.55.995.html`

> **AS 18.55.996(b)** "There is created with respect to each of the associations
> named in (a) of this section **a public body corporate and politic**"
> `https://codes.findlaw.com/ak/title-18-health-safety-housing-human-rights-and-public-defender/ak-st-sect-18-55-996.html`

**AS 18.55.996(a) names sixteen SPONSORING ASSOCIATIONS** — and this is the list
that decides Cedar's Alaska housing keys, because **the housing authority is a
separate public body from the association that sponsored it, and the association
is very often not the entity Cedar has keyed to**:

> (1) Arctic Slope Native Association · (2) Kawerak, Inc. · (3) Northwest Alaska
> Native Association · (4) Association of Village Council Presidents · (5)
> Tanana Chiefs Conference · (6) Cook Inlet Tribal Council · (7) Bristol Bay
> Native Association · (8) Aleut League · (9) North Pacific Rim Native Corp. ·
> (10) Tlingit-Haida Central Council or Alaska Native Brotherhood · (11) Kodiak
> Area Native Association · (12) Copper River Native Association · (13) Alaska
> Federation of Natives, Inc. · (14) Sitka Community Association · (15)
> Metlakatla Indian Community · (16) Ketchikan Indian Corporation

*Also in AS 18.55.996: (c) the association's governing body must declare the
need before the authority may operate; (d) five commissioners with staggered
three-year terms; (i) an annual independent audit. Retrieved from
law.onecle.com; the akleg.gov statute viewer returned HTTP 403 to three
attempts.*

**HUD's own position on Alaska TDHEs**, NAHASDA final rule preamble,
63 FR 12334 (1998-03-12),
`https://www.federalregister.gov/documents/full_text/text/1998/03/12/98-6283.txt`:

> Section 1000.206. Several commenters requested clarification on how TDHEs in
> Alaska are designated. **TDHEs in Alaska are designated in the same manner as
> any other TDHE.**

> Section 1000.301. One commenter felt that the following sentence should be
> added … "Native Regional Housing Authorities in Alaska shall be the recipients
> of grants awarded under section 202(1) of NAHASDA …" **This cannot be done by
> regulation; it is a statutory requirement that Indian tribes be funded
> directly.**

**THREE DIFFERENT PARTIES, AND CEDAR MUST NOT COLLAPSE THEM.**
24 C.F.R. §1000.317, `https://www.law.cornell.edu/cfr/text/24/1000.317`:

> **"Who is the recipient for funds for current assisted stock which is owned by
> state-created Regional Native Housing Authorities in Alaska?"**
> "If housing units developed under the 1937 Act are owned by a state-created
> Regional Native Housing Authority in Alaska, and are not located on an Indian
> reservation, then the recipient for funds allocated for the current assisted
> stock portion of NAHASDA funds for the units is **the regional Indian tribe**."

| question | answer |
|---|---|
| **who the ENTITY is** | the regional housing authority — a public body corporate and politic, AS 18.55.996(b), its own legal person |
| **who owns the ASSET** | for 1937 Act current assisted stock, the housing authority owns the units |
| **who receives the MONEY** | **scoped**: for current assisted stock **not on an Indian reservation**, the regional Indian tribe, 24 C.F.R. §1000.317. **Do not generalise this to all NAHASDA funds.** Competitive awards go to the authority by name — 74 FR 55250 (2009-10-27) lists Aleutian, Bristol Bay and Cook Inlet housing authorities as Recovery Act NAHBG recipients |

**`cedar_uid` disposition: `MANY_TO_MANY_NO_SINGLE_HUB`.** §4103(22)(C) is
explicit that one TDHE acts for many tribes. HUD's own TDHE directory
(`https://www.hud.gov/helping-americans/public-indian-housing-tdhe`) carries
**202 `TDHE:` listings across 15 distinct Alaska TDHEs** — the 202 total and the
15 names were confirmed against the PDF by the 2026-09-03 research pass; the
per-TDHE tallies within it (AVCP the largest, at 53) were **relayed and not
independently confirmed**, so treat 53 as indicative. Forcing one `cedar_uid`
onto AVCP Regional Housing Authority is false whichever member is picked. **The
entity needs its own hub, and the money needs a `serves_entities` edge set — not
a single owner key.**

⚠ **There is no single authoritative roster.** AS 18.55.996(a) names **16 Native
associations** (not authorities); HUD's TDHE directory names **15 TDHEs**; the
Association of Alaska Housing Authorities (`https://www.aahaak.org/our-members`,
a **private trade association, not governmental**) names **14 RHAs plus AHFC**.
The three sets do not correspond one-to-one — Ketchikan Indian Community Housing
Authority is in AAHA and not in HUD's TDHE list; Metlakatla and Kenaitze
Salamatof are in HUD's and not in AAHA's — and the names drift ("AVCP" vs
"Association of Village Council Presidents"; "Copper River Basin" vs "Copper
Basin"). **A name-based join across these three is guaranteed to be wrong. Build
a hand-maintained crosswalk with a provenance column.**

**Name patterns.** `housing authority`, `housing entity`, `TDHE`, `tribally
designated housing`; the Alaska specialisation on `regional housing authority`.
**A `housing authority of the city/county/town/borough of …` match SUPPRESSES
the TDHE claim** — see §2.13.

**Measured in Cedar (2026-09-03).**

| measurement | file | value |
|---|---|---|
| entities of this form in the spine | `data/spine/cedar_entity_spine.csv` | **1** — Bristol Bay Housing Authority, `CE-000R2-4J / ITO-BRSTL1-00`, classed **`Intertribal Organization`**. There is no TDHE class and no housing-authority class |
| rows whose name matches the TDHE patterns, all declared files | `review/native_legal_forms_census_2026-09-03.csv` | **14,426**, of which **8,094** carry a resolvable Cedar key |
| rows matching the Alaska-regional specialisation | same | **655**, of which **271** carry a key |
| distinct TDHE names in the FAC tribal audits | `data/clean/fac_tribal_single_audits.csv` (all 6,780 rows) | **902 rows** match; 242 distinct auditee-name/state groups |
| ledger rows naming a housing authority | `data/clean/cedar_identifier_ledger_final.csv` | **154** |
| **NAHASDA IHBG (CFDA 14.867) obligations keyed to an entity that cannot legally receive them** | `data/clean/federal_funding_transactions.csv` | **167 rows, $1,000,340,000** (see the table in §4) |

---

### 2.7 Native Hawaiian Organization, and NHO-owned firms — `NATIVE_HAWAIIAN_ORGANIZATION`, `NHO_OWNED_FIRM`

**Regulation.** 13 C.F.R. §124.3 (definitions), §124.110 (8(a) rules for NHOs);
statutory hook 15 U.S.C. §637(a)(15).
`https://www.law.cornell.edu/cfr/text/13/124.110` *(Cornell is a mirror; eCFR
now 302-redirects automated requests to `unblock.federalregister.gov` and was
NOT RETRIEVED on 2026-09-03.)*

**What it legally IS.** A community service organisation whose members are
Native Hawaiians, controlled by Native Hawaiians, and whose activities principally
benefit Native Hawaiians. **There is no authoritative federal roster**, so the
universe is open — `docs/NATIVE_ENTITY_NUANCES.md`.

**Members / owner.** Native Hawaiians as beneficiaries; governance by its own
board. Nobody owns it in a corporate sense.

**`cedar_uid` disposition: `HUB`.**

**AN NHO-OWNED FIRM IS NOT AN NHO** — `NHO_OWNED_FIRM`,
`SUB_HUB_ROLLS_UP` to the owning NHO. The SAM socio-economic flag
`native_hawaiian_organization_owned_firm` **names the owner, never the
registrant**. `docs/NATIVE_ENTITY_NUANCES.md` records the two worked cases
(Honua Consulting, Nohopapa Hawaiʻi) and the general rule: *a socio-economic
flag describes a RELATIONSHIP to a class; it is never membership of that class.*

**Name patterns.** None safe. Two live traps, both already recorded: **"Inc"
tells you nothing in Hawaiʻi** (Hawaiʻi nonprofit corporations routinely use
"Inc"; read the DCCA registration type), and the ʻokina is a consonant — prefer
U+02BB in canonical storage and match on the folded key.

**Measured in Cedar (2026-09-03).** `entity_class = Native Hawaiian
Organization` **210** in the spine. `data/clean/nho_register.csv` **218** rows
(185 `doi_notification_list`, 33 `contracting_nho`).
`data/clean/nho_verified_entities.csv` **36** firms, of which **27** have an NHO
parent, **4** an `ANC` parent, **1** individual/family, **4** unresolved —
**and none of the 36 carries a `cedar_uid`**. Prime obligations on
`Native Hawaiian Organization` keys: **1,293 rows, $883M**, of which **560 rows
/ $455M** are `reported_8a = 1` (`data/clean/prime_contracts.csv`).

⚠ **One label to adjudicate, flagged not fixed.** `DAWSON MCG, INC.` in
`nho_verified_entities.csv` carries `parent_native_entity = HAWAIIAN NATIVE
CORPORATION` with `parent_entity_class = ANC`. Every ANCSA corporation form is
defined as "organized under the laws of the State of Alaska"
(43 U.S.C. §1602(g), (j), (n), (o)); a Hawaiʻi entity cannot be one. The class
label is wrong or the parent is misidentified. Cedar has already refused a
related resolution — `docs/NATIVE_ENTITY_NUANCES.md` records *Department of
Hawaiian Home Lands → "Hawaiian Native Corporation"* as a refused match.

---

### 2.8 Tribal 8(a) and ANC 8(a) participants — `TRIBAL_8A_CONCERN`

**Regulation.** 13 C.F.R. §124.109 —
*"Do Indian tribes and Alaska Native Corporations have any special rules for
applying to and remaining eligible for the 8(a) BD program?"*
`https://www.law.cornell.edu/cfr/text/13/124.109`

- §124.109(a): *"Small business concerns owned and controlled by ANCs are
  eligible for participation in the 8(a) program"*
- §124.109(c)(3)(i): *"a Tribe must unconditionally own at least 51 percent of
  the voting stock and at least 51 percent …"*
- §124.109(c)(3)(ii): *"A Tribe may not own 51% or more of another firm
  which … has been operating in the 8(a) program"* — the same-primary-NAICS
  limit
- §124.109(c)(1) is the **sovereign-immunity-waiver** requirement, not the
  ownership rule. *(Lettering corrected 2026-09-03; an earlier draft cited
  (c)(1) for ownership.)*

**THE SOLE-SOURCE CEILING EXEMPTION — and it is UNCODIFIED.** This is what
explains the dollar concentrations Cedar sees.

13 C.F.R. §124.506 — *"At what dollar threshold must an 8(a) procurement be
competed among eligible Participants?"* —
`https://www.law.cornell.edu/cfr/text/13/124.506`:

> **(b)(1)** A Participant concern owned and controlled by an Indian Tribe or an
> ANC may be awarded a sole source 8(a) contract **where the anticipated value
> of the procurement exceeds the applicable competitive threshold** if SBA has
> not accepted the requirement into the 8(a) BD program as a competitive
> procurement.

> **(b)(3)** … a current procurement requirement may not be removed from
> competition and awarded to a tribally-owned, ANC-owned or NHO-owned concern on
> a sole source basis.

The statutory hook is **not** 15 U.S.C. §637(a)(1)(D)(i) — that clause *is* the
threshold rule tribal firms are exempted **from**. The exemption is
**Pub. L. 100-656, tit. VI, §602(a)** (Nov. 15, 1988, 102 Stat. 3887, as
amended), carried as a **statutory note** to 15 U.S.C. §637:

> "(a) Competitive Thresholds.—Section 8(a)(1)(D) of the Small Business Act
> [15 U.S.C. 637(a)(1)(D)], as added by section 303 of this Act, shall not apply
> to Program Participants that are owned and controlled by economically
> disadvantaged Indian tribes …"

`https://www.govinfo.gov/content/pkg/USCODE-2024-title15/html/USCODE-2024-title15-chap14A-sec637.htm`

And the statutory definition of "Indian tribe" at 15 U.S.C. §637(a)(13) folds
the ANCs in directly: *"including any Alaska Native village or regional or
village corporation (within the meaning of the Alaska Native Claims Settlement
Act …)"*.

⚠ **DO NOT STORE A SINGLE THRESHOLD VALUE.** Three authorities disagreed as of
2026-09-03: 15 U.S.C. §637(a)(1)(D)(i)(II) **$7M manufacturing / $3M other**;
13 C.F.R. §124.506(a)(2)(ii) **$7M / $4.5M**; FAR 19.805-1(a)(2) **$8.5M /
$5.5M** (90 FR 41879, 2025-08-27). FAR carries the most recent amendment and is
the operative acquisition threshold. **Store the authority beside the figure**
or the field is wrong against two of three no matter what is picked.

**Members / owner.** No members. Owned ≥51% by the tribe, ANC or NHO — **the
hub**. The 8(a) firm is a sub-hub.

**`cedar_uid` disposition: `SUB_HUB_ROLLS_UP`** to the owning hub.

**Measured in Cedar (2026-09-03, `data/clean/prime_contracts.csv`, all
1,217,768 rows).**

| | rows | obligations |
|---|---:|---:|
| `reported_8a = 1` | **364,150** | **$117,056,105,547.54** |
| `reported_8a = 0` | 853,618 | $192,949,153,113.22 |

Joined to the spine on `cedar_uid`, attributed rows only:

| spine `entity_class` | rows | obligations | 8(a) rows | 8(a) obligations |
|---|---:|---:|---:|---:|
| Alaska Native Regional Corporation | 336,212 | $104.435B | 117,876 | $38.271B |
| Alaska Native Village Corporation | 208,551 | $61.456B | 87,944 | $30.277B |
| Federally recognized tribe | 219,560 | $55.320B | 71,339 | $22.924B |
| Federally recognized Alaska Native Village | 18,936 | $5.778B | 6,502 | $2.662B |
| State-recognized tribe | 4,403 | $1.330B | 1,836 | $0.518B |
| Native Hawaiian Organization | 1,293 | $0.883B | 560 | $0.455B |
| *(all remaining classes)* | 2,884 | $1.145B | 335 | $0.212B |

**The concentration is the statute working as written, not an anomaly.**
ANCSA corporations hold **$165.9B of $230.3B** (72.0%) of attributed prime
obligations. §124.506(b)(1) plus the Pub. L. 100-656 §602(a) note is the
mechanism, and 13 C.F.R. §124.109(c)(3)(ii) is why one ANC can carry dozens of
distinct 8(a) subsidiaries rather than one large one. **Any Cedar analysis that
treats a single ANC's subsidiary count or sole-source share as evidence of
irregularity is measuring the regulation.**

---

### 2.9 Inter-tribal consortium / tribal organization — `ISDEAA_TRIBAL_ORGANIZATION`

**Statute.** 25 U.S.C. §5304(l) (ISDEAA definitions); 25 U.S.C. §5381(a)(5),
§5381(b) (Title V self-governance).
`https://www.govinfo.gov/content/pkg/USCODE-2024-title25/html/USCODE-2024-title25-chap46-sec5304.htm`
·
`https://www.govinfo.gov/content/pkg/USCODE-2024-title25/html/USCODE-2024-title25-chap46-subchapV-sec5381.htm`

> **§5304(l)** "Tribal organization" … means the recognized governing body of
> any Indian tribe; **any legally established organization of Indians which is
> controlled, sanctioned, or chartered by such governing body or which is
> democratically elected by the adult members of the Indian community to be
> served by such organization** and which includes the maximum participation of
> Indians in all phases of its activities: *Provided,* That in any case where a
> contract is let or grant made to an organization to perform services
> benefiting more than one Indian tribe, **the approval of each such Indian
> tribe shall be a prerequisite** to the letting or making of such contract or
> grant;

> **§5381(a)(5)** The term "inter-tribal consortium" means **a coalition of two
> [or] more separate Indian tribes that join together for the purpose of
> participating in self-governance**, including tribal organizations.
> *(The U.S. Code prints "two¹ more"; footnote 1 marks the omitted "or".)*

> **§5381(b)** In any case in which an Indian tribe has authorized … an
> inter-tribal consortium … to carry out programs … on its behalf …, the
> authorized … inter-tribal consortium … **shall have the rights and
> responsibilities of the authorizing Indian tribe** (except as otherwise
> provided in the authorizing resolution …).

**Two findings a registry needs.** First, **"inter-tribal consortium" is a Title
V (HHS/IHS) term only** — it is defined at §5381(a)(5) and appears nowhere in
§5304 or in §5361 (the Interior Title IV definitions, checked: zero occurrences
of "consorti-"). On the Interior side the concept must travel through §5304(l)
"tribal organization". Second, the real multi-tribe control rule is the
**§5304(l) proviso**: each benefited tribe holds a **veto over each contract**.
Control is joint and several, not majority.

**Members / owner.** **Tribes, not individuals. Members, not owners.** Cedar
already carries the corollary — *"an intertribal organisation has members, not
owners; 30 lobbying rulings say so"* (`NATIVE_ENTITY_NUANCES.md`).

**`cedar_uid` disposition: `MANY_TO_MANY_NO_SINGLE_HUB`.**

**Name patterns.** `inter-tribal` / `intertribal`, `consortium`, `council of …
tribes`. **All three are token traps**: `Council Native Corporation` is the
ANCSA village corporation for Council, Alaska, and it catches every organisation
with the word *Council*; `Wales Native Corporation` is the village corporation
for Wales, Alaska, and it catches *Prince of Wales*. Both are measured below.

**Measured in Cedar (2026-09-03).** Spine: `Intertribal Organization` **56**,
`Federal-level self-governance consortium` **29**. Rows matching the patterns
across all declared files: **16,238**, of which **5,326** carry a resolvable
key. Conflicts (a consortium name on an ANCSA-corporation key): **27 groups,
935 rows, $191,551,629.16** — led by:

| observed name | keyed to | rows | observed $ |
|---|---|---:|---:|
| PRINCE OF WALES TRIBAL ENTERPRISE CONSORTIUM | Wales Native Corporation (ANVC) | 592 | $118,874,831.92 |
| INTER-TRIBAL COUNCIL OF MICHIGAN INC | Council Native Corporation (ANVC) | 195 | $53,344,012.87 |
| AHTNA INTERTRIBAL RESOURCE COMMISSION | Ahtna, Incorporated (ANRC) | 84 | $8,108,335.66 |
| INTER TRIBAL COUNCIL OF CALIFORNIA INC | Council Native Corporation (ANVC) | 23 | $3,241,812.00 |

---

### 2.10 Tribal nonprofit under IRC §501(c)(3) vs the tribe's own §7871 status — `TRIBAL_NONPROFIT_501C3`

**Statute.** 26 U.S.C. §7871.
`https://www.govinfo.gov/content/pkg/USCODE-2024-title26/html/USCODE-2024-title26-subtitleF-chap80-subchapC-sec7871.htm`

> **(a) General rule.** An Indian tribal government shall be treated as a
> State— (1) for purposes of determining whether and in what amount any
> contribution or transfer to or for the use of such government (or a political
> subdivision thereof) is deductible under— (A) section 170 … (B) sections 2055
> and 2106(a)(2) … or (C) section 2522 …; (2) subject to subsection (b), for
> purposes of any exemption from, credit or refund of, or payment with respect
> to, an excise tax …; (3) for purposes of section 164 …; (4) subject to
> subsection (c), for purposes of section 103 …; (5) for purposes of section
> 511(a)(2)(B) …; (6) for purposes of— (A) section 105(e) … (B) section
> 403(b)(1)(A)(ii) … and (C) section 454(b)(2); and (7) for purposes of— (A)
> chapter 41 … and (B) subchapter A of chapter 42 …

> **(d)** … a subdivision of an Indian tribal government shall be treated as a
> political subdivision of a State **if (and only if) the Secretary determines
> (after consultation with the Secretary of the Interior) that such subdivision
> has been delegated the right to exercise one or more of the substantial
> governmental functions** of the Indian tribal government.

**WHY A TRIBE IS NOT A 501(c)(3).** §7871 is a narrow, **enumerated
equivalence** statute. It is not a status grant, and a tribe does not need one:

Rev. Rul. 67-284, 1967-2 C.B. 55, §V,
`https://www.irs.gov/pub/irs-tege/rr67_284.pdf`:

> Income tax statutes do not tax Indian tribes. **The tribe is not a taxable
> entity.**

Rev. Rul. 94-16, 1994-1 C.B. 19, `https://www.irs.gov/pub/irs-tege/rr94_16.pdf`:

> **HOLDING.** An unincorporated Indian tribe or an Indian tribal corporation
> organized under section 17 of the IRA is not subject to federal income tax on
> the income earned in the conduct of commercial business on or off the tribe's
> reservation. **However, a corporation organized by an Indian tribe under state
> law is subject to federal income tax** on the income earned in the conduct of
> the commercial business on and off the tribe's reservation.

IRS, *FAQs for Indian tribal governments regarding employee plans and exempt
organization issues*, Q1 and Q3
(`https://www.irs.gov/government-entities/indian-tribal-governments/faqs-for-indian-tribal-governments-regarding-employee-plans-and-exempt-organization-issues`
— the page disclaims itself as legal authority; cite the rulings above, this is
corroboration):

> They are not "exempt" from tax such as a charitable organization is under IRC
> 501(c)(3). However, FRTs are governmental entities and, like state
> governments, they are immune from state and federal income tax.

> A federally recognized tribe that exercises sovereign powers generally will
> not qualify for exemption as a charitable organization under IRC section
> 501(c)(3) because the exercise of sovereign powers is not a charitable
> purpose … **A tribe may choose to create, through separate organizing
> documents, an entity separate from the tribe** that does not have sovereign
> powers and that is organized exclusively for purposes as described under IRC
> section 501(c)(3).

**WHAT THIS MEANS FOR THE NONPROFITS DATASET.** Three consequences, all
operational:

1. **A tribe will never appear in the IRS Business Master File as a 501(c)(3),
   and its absence is not evidence of anything.** Contributions to it are
   deductible by force of §7871(a)(1)(A) + §170(c)(1), with no exemption letter
   and no Form 1023 in the chain. A "no BMF record" flag on a tribe means the
   law worked, not that a lookup failed.
2. **A 501(c)(3) row keyed to a tribe's `cedar_uid` is asserting a roll-up, not
   an identity.** The filer is a separate legal person the tribe chartered. That
   is allowed under Cedar's hub model, but the row must carry the sub-hub, or a
   reader will conclude the tribe filed a Form 990.
3. **An ANCSA corporation cannot be a 501(c)(3) at all** when it is organised
   "as a business for profit" (43 U.S.C. §1606(d), §1602(j)). A BMF row keyed to
   an ANC is necessarily an *affiliate* — a foundation, a settlement trust, a
   heritage institute — and never the corporation.

**`cedar_uid` disposition: `SUB_HUB_ROLLS_UP`.**

**Measured in Cedar (2026-09-03, `data/clean/np_orgs.csv`, all 12,764 rows).**
`bmf_subsection = 03` on **10,522** rows. Keyed to a spine class:

| keyed spine class | rows |
|---|---:|
| *(none — no spine class on the row)* | 11,308 |
| Federally recognized tribe | **1,043** |
| Federal-level constituency entity | 126 |
| Intertribal Organization | 68 |
| State-recognized tribe | 51 |
| **Alaska Native Village Corporation** | **49** |
| Federally recognized Alaska Native Village | 45 |
| Urban Indian Organization | 25 |
| Native Hawaiian Organization | 21 |
| Tribal College or University | 13 |
| **Alaska Native Regional Corporation** | **5** |
| BIE School | 5 |
| Federal-level self-governance consortium | 3 |
| State-level constituency entity | 1 |
| Native CDFI | 1 |

**Worked example of consequence 3, and it is a single-token defect at scale.**
Of the 49 rows keyed to an ANCSA village corporation, **41 are keyed to
`Council Native Corporation` (`CE-0008F-2Q`), all at tier B** — on the word
*Council*. They include `ESTATE PLANNING COUNCIL OF POMONA VALLEY INC`,
`NATIONAL COUNCIL OF ASIAN INDIAN ASSOCIATIONS INC`, `CROWN HEIGHTS PASTORAL
COUNCIL INC` and `ARAPAHOE COUNTY COUNCIL ON AGING INC`. Two of the 41 carry
`disposition = NATIVE_VERIFIED_STRICT` — `WESTERN DAKOTA ESTATE PLANNING COUNCIL
INC` (ND) and `ALLEGHENY-LENAPE INDIAN COUNCIL OF OHIO INC` (OH) — i.e. the
verification passed on a row whose entity is an Alaska village corporation with
no connection to either.

---

### 2.11 Alaska Native tribal health consortium / regional health corporation — `AK_TRIBAL_HEALTH_ORGANIZATION`

**Statute.** These are **tribal organizations under 25 U.S.C. §5304(l)**
carrying IHS programmes for a region under a Title V compact
(25 U.S.C. §5381 et seq.). Three citation corrections that must travel with
this section, all verified 2026-09-03:

- **25 U.S.C. §1638h DOES NOT EXIST.** Chapter 18 ends at §1638g. Do not cite it.
- **25 U.S.C. §1621** is the Indian Health Care Improvement Fund — unrelated.
- **Pub. L. 105-83 §325**, the usual ANTHC citation, **never says "Alaska Native
  Tribal Health Consortium".** It names thirteen regional health entities and
  authorises them "to form a consortium". The organic authority is uncodified.
- **The only statute that names ANTHC is Pub. L. 113-68**, the *Alaska Native
  Tribal Health Consortium Land Transfer Act* (Dec. 26, 2013, 127 Stat. 1205),
  `https://www.govinfo.gov/content/pkg/PLAW-113publ68/html/PLAW-113publ68.htm`:
  > **(1) ANTHC.**—The term "ANTHC" means the Alaska Native Tribal Health
  > Consortium.

  It is a **land-conveyance statute, not an organic act**. Cite it for the name,
  not for the powers.

**Members / owner.** Its member tribes and village governments. **Nobody owns
it.** Its board is seated by the member tribes.

**`cedar_uid` disposition: `MANY_TO_MANY_NO_SINGLE_HUB`.**

**Name patterns.** `health corporation`, `health consortium`, `area health`,
`health board`. **These collide with the regional corporation name by
construction** — both are named for the region.

**Measured in Cedar (2026-09-03, `data/spine/cedar_entity_spine.csv`).**
**17 of the 29** `Federal-level self-governance consortium` rows are Alaska
(`state = AK`); the other 12 are CA, UT, AZ and OK health programmes. Of the 17,
eight are health-named — Bristol Bay Area Health Corporation, Kodiak Area Native
Association, Norton Sound Health Corporation, Southcentral Foundation, Southeast
Alaska Regional Health Consortium, Yukon-Kuskokwim Health Corporation, Eastern
Aleutian Tribes, Mount Sanford Tribal Consortium — and nine are the regional
service consortia that also carry health compacts (Aleutian Pribilof Islands
Association, AVCP, Bristol Bay Native Association, Chugachmiut, Copper River
Native Association, Council of Athabascan Tribal Governments, Kawerak, Maniilaq,
Tanana Chiefs Conference). **ANTHC itself is classed
`Intertribal Organization` (`CE-000RZ-J7 / ITO-LSKHLT-00`)** while its peers are
`Federal-level self-governance consortium` — an internal inconsistency, flagged
not fixed. Rows matching the patterns across all declared files: **10,389**, of
which **3,290** carry a key. Conflicts: **3 groups, 21 rows, $183,662,615.74**,
led by **`Bristol Bay Area Health Corporation and Subsidiaries` → Bristol Bay
Native Corporation (ANRC), 3 rows, $181,212,803.00** in
`data/clean/fac_tribal_single_audits.csv` — the FA-01 defect, still live in the
FAC table after being withdrawn in the ledger
(`docs/NATIVE_ENTITY_NUANCES.md`, "Worked case: FA-01").

---

### 2.12 The forms this list was missing — each justified by a row Cedar holds

**(a) Oklahoma Indian Welfare Act §3 corporation — `CORP_OIWA_SECTION_3`.**
25 U.S.C. §5203. Named in its own right by Treas. Reg. §301.7701-1(a)(4)(i)(C):
*"The term section 3 corporation means a federally chartered corporation
incorporated under section 3 of the Oklahoma Indian Welfare Act, as amended
(25 U.S.C. 5203) …"*. It is the Oklahoma analogue of a §17 charter and Treasury
treats it identically. **Justification:** Cedar holds the Oklahoma nations whose
housing authorities and enterprises are the archetypal §3 vehicles — measured in
`data/clean/fac_tribal_single_audits.csv`, **24** distinct Oklahoma
housing-authority auditee names. *Which of them actually hold a §3 charter is
NOT MEASURED — Cedar has no column for it.* `SUB_HUB_ROLLS_UP`. **Measured in Cedar: zero
entities carry this form**, same gap as §17.

**(b) Wholly owned Tribal entity organised under TRIBAL law.**
Treas. Reg. §301.7701-1(a)(4)(i)(D): *"an entity wholly owned by one or more
Indian Tribal governments … that is organized or incorporated exclusively under
the laws of one or more of the owning Indian Tribal governments."* This is the
tribal-LLC / tribal-corporate-code entity, and after 2026-01-15 it is
disregarded for federal income tax exactly as a §17 corporation is.
**Justification:** `data/clean/nest_enterprises.csv` holds **5,820** enterprises,
**4,101** with `owner_class = tribal_government`. Most are this form and Cedar
does not distinguish it from **(c)**. `SUB_HUB_ROLLS_UP`.

**(c) A tribe's corporation organised under STATE law.** The contrasting form,
and the contrast is a tax fact, not a nicety — Rev. Rul. 94-16: *"a corporation
organized by an Indian tribe under state law is subject to federal income tax."*
Cedar cannot currently tell (b) from (c) on any row. `SUB_HUB_ROLLS_UP`.
**Recording the charter law is the only thing that separates them**, and it
decides taxability.

**(d) Non-Native public housing agency — `NON_NATIVE_PUBLIC_HOUSING_AGENCY`.**
See §2.13. `NOT_A_NATIVE_ENTITY`. **This is the largest measured defect in this
pass.**

**(e) ANCSA settlement trust.** 43 U.S.C. §1602(t): *"'Settlement Trust' means a
trust— (1) established and registered by a Native Corporation under the laws of
the State of Alaska pursuant to a resolution of its shareholders, and (2)
operated for the benefit of shareholders, Natives, and descendants of Natives,
in accordance with section 1629e of this title …"*. A distinct legal person from
its settlor corporation. **Justification: 1 row measured** in
`data/clean/cedar_identifier_ledger_final.csv`. Small, but it is the vehicle
through which ANC distributions run, and it will grow. `SUB_HUB_ROLLS_UP` to the
settlor corporation.

**(f) Constituency band / §7871(d) political subdivision.** Cedar already has
`CNSF` (22) and `CNSS` (3), and `docs/NATIVE_ENTITY_NUANCES.md` documents the
Federal Register parenthetical pattern. What is missing is the **legal** test:
26 U.S.C. §7871(d) makes a subdivision a political subdivision *"if (and only
if) the Secretary determines … that such subdivision has been delegated the
right to exercise one or more of the substantial governmental functions of the
Indian tribal government."* That is a determination with a record, and it is the
thing that decides whether a band is a `cedar_uid` subject in its own right.
**Justification: `CE-00170-7S`**, which currently carries both Leech Lake
(`CNSF-MINNCH-LL`) and the Minnesota Chippewa Tribe (`TRBF-MINNCH-00`) — see §5.

**(g) State-recognized tribe.** Already a Cedar class (**64**), but the legal
consequence is not recorded here and should be: a state-recognized tribe is
**not** an "Indian tribe" for NAHASDA §4111 direct funding (25 U.S.C. §4103(13)
admits state-recognized tribes for NAHASDA specifically, which is unusual and
worth noting), is **not** eligible for ISDEAA contracting under §5304(e), and is
**not** on the BIA list. Cedar holds `MOWA CHOCTAW HOUSING AUTHORITY` keyed to
`TRBS-MWACTW-00`; whether that authority is a NAHASDA TDHE turns on §4103(13),
which is a distinct question from federal recognition. NOT MEASURED here.

---

### 2.13 Non-Native public housing agency — `NON_NATIVE_PUBLIC_HOUSING_AGENCY`

**What it is.** A city, county, town or borough housing authority chartered
under state law and operating under the U.S. Housing Act of 1937
(42 U.S.C. §1437a(b)(6) defines "public housing agency"). It carries a place
name, and American place names are very often Native in origin. The Tuscarawas
rule in `docs/NATIVE_ENTITY_NUANCES.md` is the general form.

**`cedar_uid` disposition: `NOT_A_NATIVE_ENTITY`. Any Cedar key on one is a
defect** — which is how `code/1164` scores it: for this form the conflict test
does not consult `never_key_to_classes`, because there is no class it may be
keyed to.

**Measured in Cedar (2026-09-03, `data/clean/federal_funding_transactions.csv`,
all 701,955 rows).** Rows whose `recipient_name` matches
`housing authority of the (city|county|town|borough|village) of` or
`(city|county|town|borough) housing authority` **and** carry a `cedar_uid` that
resolves in the spine:

**6,025 rows, $1,137,939,199.26 — every one of them `attributed_flag = 1`
and `attribution_status = cedar_neid`.** 6,002 at tier B; **23 at tier X**,
which is a second defect on top of the first (a tier-X row is a *refusal* and
must not carry an attribution — `START_HERE.md` trap 1b).

| recipient | state | keyed to | rows | obligations |
|---|---|---|---:|---:|
| HOUSING AUTHORITY OF THE CITY OF OMAHA | NE | Omaha (`Federally recognized tribe`) | **5,015** | **$979,343,497.34** |
| HOUSING AUTHORITY OF THE CITY OF YAKIMA | WA | Confederated Yakama | **965** | **$153,757,575.67** |
| SANTA CLARA COUNTY HOUSING AUTHORITY | CA | Pueblo of Santa Clara (NM) | 11 | $1,727,185.79 |
| WINNEBAGO COUNTY HOUSING AUTHORITY | IL and WI, one name | Winnebago | 34 | $3,110,940.46 |


*Every figure in that table is an unrounded sum. The four names total
6,025 rows and $1,137,939,199.26.*

**Root cause, traced.** `data/clean/cedar_identifier_ledger_final.csv` holds UEI
`DFPYJKG9K2X4` = `OMAHA HOUSING AUTHORITY` → `Omaha`, tier B, method
`cross_dataset_propagation:funding`. The assistance table then keys 5,015 rows
by `uei_exact_archive`. **The identifier is exact and the link is wrong** —
`START_HERE.md` trap 1, at a billion dollars.

**Also in the ledger and unfixed** (`legal_business_name` → keyed entity):
`BOISE CITY ADA HOUSING AUTHORITY` → Bois Forte (MN) · `NARRAGANSETT RHODE
ISLAND HOUSING AUTHORITY, TOWN OF` → Narragansett · `PEORIA HOUSING AUTHORITY` /
`PEORIA HOUSING AUTH` → Peoria Tribe of Indians of Oklahoma (3 rows, one already
tier X) · `SANTA CLARA CNTY HOUSING AUTH` → Pueblo of Santa Clara ·
`YAKIMA HOUSING AUTHORITY` → Confederated Yakama · `WINNEBAGO COUNTY HOUSING
AUTHORITY` ×2 → Winnebago.

**Already correctly refused, and worth keeping as the counter-example:**
`KIOWA COUNTY HOUSING AUTHORITY INC` → Kiowa Tribe, EIN 263074960, **tier X,
`elijah_ruling`**. The owner has ruled this exact shape once. The other nine
were never put to him.

---

## 3. THE FORM → SPINE CLASS MAP, AND THE GAPS

Measured 2026-09-03 against `data/spine/cedar_entity_spine.csv` (1,555 rows).

| form | Cedar `entity_class` | entities |
|---|---|---:|
| `TRIBE_FEDERALLY_RECOGNIZED` | Federally recognized tribe · Federally recognized Alaska Native Village | 349 · 228 |
| `CORP_IRA_SECTION_17` | **none** | **0 — GAP** |
| `CORP_OIWA_SECTION_3` | **none** | **0 — GAP** |
| `ANCSA_REGIONAL_CORPORATION` | Alaska Native Regional Corporation | 12 (**The 13th is absent**) |
| `ANCSA_VILLAGE_CORPORATION` | Alaska Native Village Corporation | 173 (**includes the 4 urban corporations**) |
| `ANCSA_URBAN_CORPORATION` | **none** | **0 — GAP; 4 held as ANVC** |
| `ANCSA_GROUP_CORPORATION` | ANCSA Group Corporation | 6 (**all carry `ANVC-` handles**) |
| `TDHE_NAHASDA` | **none** | **0 — GAP** |
| `AK_REGIONAL_HOUSING_AUTHORITY` | **none** | **0 — GAP; 1 held as `Intertribal Organization`** |
| `NATIVE_HAWAIIAN_ORGANIZATION` | Native Hawaiian Organization | 210 |
| `NHO_OWNED_FIRM` | **none** (sub-hub) | n/a |
| `TRIBAL_8A_CONCERN` | **none** (sub-hub) | n/a — `nest_enterprises.csv` is the nearest layer, 5,820 rows |
| `ISDEAA_TRIBAL_ORGANIZATION` | Intertribal Organization · Federal-level self-governance consortium | 56 · 29 |
| `AK_TRIBAL_HEALTH_ORGANIZATION` | Federal-level self-governance consortium (15 of 29) | ANTHC classed `Intertribal Organization` — inconsistent |
| `TRIBAL_NONPROFIT_501C3` | **none** (sub-hub) | `np_orgs.csv`, 12,764 rows |
| `NON_NATIVE_PUBLIC_HOUSING_AGENCY` | **none** — correctly, it is not a Cedar entity | must be an exclusion, not a class |

**Six gaps.** None of them is a mis-key on its own; each is a distinction Cedar
cannot currently express, which is why the mis-keys in §4 had nothing to catch
them.

---

## 4. THE RANKED WRONG-KEY LIST

`review/native_legal_forms_key_conflicts_2026-09-03.csv` — **84 conflict groups
over 77 distinct (file, name, key) triples, 7,428 rows, $2,828,749,215.64 of
observed dollars.** Produced by
`py -3 code/1164_native_legal_forms_classifier.py conflicts`, which reads **every
row of every declared file — no cap**. `data/clean/subawards.csv` and
`data/clean/native_entity_lobbying_disclosures.csv` are included.

**A conflict requires two legs**: the name classifies to a form, AND the row's
`cedar_uid` resolves — via the spine's `entity_class` column, never via the
handle prefix — to a class that form's statute forbids. A name alone never
produces a row. **Nothing below has been changed. This is a proposal.**

*Per-form sums double count, because `AK_REGIONAL_HOUSING_AUTHORITY` is a
specialisation of `TDHE_NAHASDA` and both fire on the same string. The
de-duplicated figures above are the ones to quote.*

### 4a. The top twenty, ranked by observed dollars

| # | observed name | file | current key | current class | correct entity / disposition | statutory reason | rows | observed $ |
|---:|---|---|---|---|---|---|---:|---:|
| 1 | HOUSING AUTHORITY OF THE CITY OF OMAHA | assistance | `CE-…` Omaha | Federally recognized tribe | **not a Native entity** | 42 U.S.C. §1437a(b)(6) PHA; 25 U.S.C. §4103(22) admits no municipal authority | 5,015 | **$979,343,497.34** |
| 2 | COOK INLET HOUSING AUTHORITY | assistance | Cook Inlet Region, Incorporated | ANCSA Regional Corporation | TDHE; AS 18.55.996(a)(6) sponsor is **Cook Inlet Tribal Council** | 43 U.S.C. §1606(d) makes CIRI a business-for-profit corporation; a TDHE is a public body under AS 18.55.996(b) | 60 | **$402,064,439.58** |
| 3 | AVCP REGIONAL HOUSING AUTHORITY | assistance | Arctic Slope Regional Corporation | ANCSA Regional Corporation | TDHE; AS 18.55.996(a)(4) sponsor is **Association of Village Council Presidents** (`SGVF-ASVCPR-00`) | as above — **and wrong region**: AVCP is the Yukon-Kuskokwim Delta, ASRC is the North Slope | 84 | **$366,277,598.86** |
| 4 | TLINGIT HAIDA REGIONAL HOUSING AUTHORITY | assistance | Tlingit & Haida | Federally recognized tribe | TDHE; AS 18.55.996(a)(10) sponsor is **Tlingit-Haida Central Council** | AS 18.55.996(b) creates the authority as a **separate** public body corporate and politic from the association | 137 | **$221,838,237.64** |
| 5 | Bristol Bay Area Health Corporation and Subsidiaries | FAC tribal | Bristol Bay Native Corporation | ANCSA Regional Corporation | `SGVF-BRSTLB-00` | 25 U.S.C. §5304(l) tribal organization ≠ 43 U.S.C. §1606 corporation. **Already withdrawn in the ledger as FA-01; still live here** | 3 | **$181,212,803.00** |
| 6 | BERING STRAITS REGIONAL HOUSING AUTHORITY | assistance | Bering Straits Native Corporation | ANCSA Regional Corporation | TDHE; AS 18.55.996(a)(2) sponsor is **Kawerak, Inc.** (`SGVF-KAWRAK-00`) | AS 18.55.996(b) | 34 | **$158,057,698.49** |
| 7 | HOUSING AUTHORITY OF THE CITY OF YAKIMA | assistance | Confederated Yakama | Federally recognized tribe | **not a Native entity** | 42 U.S.C. §1437a(b)(6). *Yakima* the city is not *Yakama* the nation | 965 | **$153,757,575.67** |
| 8 | PRINCE OF WALES TRIBAL ENTERPRISE CONSORTIUM | prime | Wales Native Corporation | ANCSA Village Corporation | 25 U.S.C. §5304(l) tribal organization | a consortium has **members, not owners**; the token `Wales` reached a Seward Peninsula village corporation from a SE Alaska consortium | 592 | **$118,874,831.92** |
| 9 | BRISTOL BAY HOUSING AUTHORITY | assistance | Bristol Bay Native Corporation | ANCSA Regional Corporation | **Cedar already holds it** — `CE-000R2-4J`. AS 18.55.996(a)(7) sponsor is **Bristol Bay Native *Association***, not the Corporation | AS 18.55.996(b); the corporation is not even in the (a) list | 50 | **$112,955,429.89** |
| 10† | NORTHWEST INUPIAT HOUSING AUTHORITY | assistance | Inupiat Community of the Arctic Slope | Federally recognized Alaska Native Village | TDHE; AS 18.55.996(a)(3) sponsor is **Northwest Alaska Native Association** | AS 18.55.996(b) — **and wrong region**: NIHA serves the NANA region, ICAS is the Arctic Slope | 46 | **$112,336,680.33** |
| 11 | INTER-TRIBAL COUNCIL OF MICHIGAN INC | assistance | Council Native Corporation | ANCSA Village Corporation | 25 U.S.C. §5304(l) | token `Council`; a Michigan consortium keyed to an Alaska village corporation | 195 | **$53,344,012.87** |
| 12 | TLINGIT-HAIDA REGIONAL HOUSING AUTHORITY | FAC tribal | Tlingit & Haida | Federally recognized tribe | as #4 | AS 18.55.996(b) | 2 | $21,330,767.00 |
| 13 | COOK INLET HOUSING AUTHORITY | subawards | Cook Inlet Region, Incorporated | ANCSA Regional Corporation | as #2 | as #2 | 13 | $12,848,418.02 |
| 14 | Bering Straits Regional Housing Authority | FAC tribal | Bering Straits Native Corporation | ANCSA Regional Corporation | as #6 | as #6 | 1 | $12,158,237.00 |
| 15 | AHTNA INTERTRIBAL RESOURCE COMMISSION | assistance | Ahtna, Incorporated | ANCSA Regional Corporation | 25 U.S.C. §5304(l) | AITRC is the eight Ahtna-region tribes' consortium; Ahtna Inc. is the §1606 corporation | 84 | $8,108,335.66 |
| 16 | INTER TRIBAL COUNCIL OF CALIFORNIA INC | assistance | Council Native Corporation | ANCSA Village Corporation | 25 U.S.C. §5304(l) | token `Council` | 23 | $3,241,812.00 |
| 17† | NORTHERN CIRCLE INDIAN HOUSING AUTHORITY | assistance | Circle (AK village) | Federally recognized Alaska Native Village | multi-tribe TDHE in **Ukiah, California** | 25 U.S.C. §4103(22)(C); token `Circle`, 3,000 miles wrong | 11 | $24,857,858.71 |
| 18 | WINNEBAGO COUNTY HOUSING AUTHORITY (IL, WI) | assistance | Winnebago | Federally recognized tribe | **not a Native entity** | 42 U.S.C. §1437a(b)(6) | 34 | $3,110,940.46 |
| 19 | SANTA CLARA COUNTY HOUSING AUTHORITY | assistance | Pueblo of Santa Clara (NM) | Federally recognized tribe | **not a Native entity** | 42 U.S.C. §1437a(b)(6) | 11 | $1,727,185.79 |
| 20 | WHITE EARTH HOUSING AUTHORITY | assistance (IHBG) | White Earth Tribal and Community College | Tribal College or University | the White Earth Band TDHE | a TCU under 25 U.S.C. §1801 et seq. is not a NAHASDA recipient under §4103(19). **Tier A**, `dofile_corrtd:prefix` — this one keys a dollar at the publishing tier | 1 | $2,306,518.00 |

† **Rows 10 and 17 are NOT in the conflict CSV, and the reason is worth
recording.** The class test cannot reach them: both are keyed to a
`Federally recognized Alaska Native Village`, and a village government keying
its own TDHE is *normal* — 25 U.S.C. §4103(22)(B) is written for exactly that.
So `Federally recognized Alaska Native Village` is deliberately **absent** from
`TDHE_NAHASDA.never_key_to_classes`, and the detector is silent. These two were
found by hand, on geography: Northwest Inupiat Housing Authority serves the NANA
region and is keyed to the Arctic Slope; Northern Circle Indian Housing
Authority is in **Ukiah, California** and is keyed to Circle, **Alaska**.
**A legal-form test cannot catch a right-form/wrong-place error, and that is a
limit of this whole registry, not an oversight in it.** The complement is
`docs/NATIVE_ENTITY_NUANCES.md`: *"when a name is ambiguous, ask where the money
went."* Figures for both are exact, measured on
`data/clean/federal_funding_transactions.csv` 2026-09-03.

*All other figures in this table are the unrounded sums in the CSV.*

**Three more non-Native PHA rows, measured the same way and in the CSV:**
`HOUSING AUTHORITY OF THE COUNTY OF SANTA CLARA` → Pueblo of Santa Clara,
`data/clean/subawards.csv`, 4 rows, $671,540.00 · `WINNEBAGO COUNTY HOUSING
AUTHORITY` → Winnebago, `subawards.csv`, 25 rows, $2,386,887.00 ·
`HOUSING AUTHORITY OF THE CITY OF OMAHA` → Omaha, `subawards.csv`, 2 rows,
$600,000.00.

### 4b. NAHASDA IHBG specifically — money that cannot lawfully reach the keyed entity

`data/clean/federal_funding_transactions.csv`, `cfda = '14.867'` (Indian Housing
Block Grants; the whole programme in Cedar is 11,118 rows / $15.899B), joined to
the spine:

| recipient | keyed to | class | rows | obligations |
|---|---|---|---:|---:|
| COOK INLET HOUSING AUTHORITY | Cook Inlet Region, Incorporated | ANCSA Regional Corporation | 32 | $378,629,502.00 |
| AVCP REGIONAL HOUSING AUTHORITY | Arctic Slope Regional Corporation | ANCSA Regional Corporation | 60 | $358,861,976.48 |
| BERING STRAITS REGIONAL HOUSING AUTHORITY | Bering Straits Native Corporation | ANCSA Regional Corporation | 27 | $148,073,252.00 |
| BRISTOL BAY HOUSING AUTHORITY | Bristol Bay Native Corporation | ANCSA Regional Corporation | 47 | $112,472,119.00 |
| WHITE EARTH HOUSING AUTHORITY | White Earth Tribal and Community College | Tribal College or University | 1 | $2,306,518.00 |
| | | **total** | **167** | **$1,000,343,367.48** |

25 U.S.C. §4111(a)(2) pays "the recipient for the tribe", and §4103(19) defines
"recipient" as an Indian tribe or the entity authorised to receive on its
behalf. **An ANCSA regional corporation is neither.** It is a business-for-profit
corporation under 43 U.S.C. §1606(d) whose shareholders are individuals, and it
appears nowhere in AS 18.55.996(a). A tribal college is not a recipient either.

### 4c. The cross-form exact-name file

`review/native_legal_forms_crossform_names_2026-09-03.csv` — **70 ledger rows
whose `legal_business_name` is the EXACT canonical or Federal-Register name of a
DIFFERENT spine entity of a DIFFERENT legal form.** Scanned all 20,740 ledger
rows. Tiers: **B 51 · X 10 · A 9**.

**Split it before acting on it.** 42 of the 70 are **roll-ups that the hub model
permits** — 33 BIE schools keyed to their operating tribe, 4 tribal colleges
keyed to their chartering tribe, 5 constituency entities (Ramah Navajo Chapter)
keyed to Navajo. Those are not errors; they are the sub-hub level being flattened
onto the hub, and the fix is to record the sub-hub, not to move the key.

**The other 28 are cross-sovereign or cross-place**, and these are proposals:

| observed name | keyed to | tier |
|---|---|---|
| `SOUTHEAST ALASKA REGIONAL HEALTH CONSORTIUM` (CAGE 993Q6) | Sitka (village government) | **A**, `elijah_ruling` |
| `National Indian Education Association` (×3) | Angoon (AK village) | X, X, B |
| `St George Tanaq Corporation` (×2) | Pribilof Islands (village government) | X, B |
| `Chilchinbeto Community School`, `Dibe Yazhi Habitiin Olta` | **Barrow** (AK village) | B |
| `Sonoma County Indian Health Project, Inc.` | Forest County (WI) | B |
| `Hawaiian Islands Land Trust` | Pribilof Islands | B |
| `Native Hawaiian Organization Charity` | The Santee Indian Organization (SC) | B |
| `California Rural Indian Health Board, Inc.` | Agua Caliente | B |
| `Rocky Mountain Tribal Leaders Council` | Chippewa-Cree | B |
| `Kodiak Area Native Association` | Sun'aq | X |
| `Alaska Peninsula Corporation`, `Klukwan, Inc.`, `Ekwok Natives Ltd`, `Akhiok-Kaguyak, Inc.`, `Ninilchik Natives Association, Inc.` | their namesake village GOVERNMENTS | B |
| `American Indian Higher Education Consortium` (×2) | Chugachmiut | X, B |
| `INTER TRIBAL COUNCIL OF CALIFORNIA` / `OF MICHIGAN` | Council Native Corporation | X |
| `BRISTOL BAY HOUSING AUTHORITY`, `BRISTOL BAY AREA HEALTH CORPORATION` | Bristol Bay Native Corporation | X |
| `Hunters Point Boarding School` | Kashia | X, `elijah_ruling` |
| `SAN JUAN SERVICES LLC` | San Juan | B |

**The tier-A row is the one to look at first.** `SOUTHEAST ALASKA REGIONAL
HEALTH CONSORTIUM` sits at tier A on an owner ruling, keyed to the Sitka village
government. SEARHC is a §5304(l) tribal organization serving the whole of
southeast Alaska; Cedar holds it as `SGVF-STHSTL-00`. Either the ruling meant
something narrower than the row now says, or it is wrong. **A tier-A row publishes.**

### 4d. The ledger's own class column disagrees with the spine's

Measured 2026-09-03: **8,344 ledger rows carry a `cedar_uid` that joins the
spine. On 452 of them the ledger's `entity_class` and the spine's
`entity_class` are BOTH drawn from the spine vocabulary and DISAGREE.**

| ledger says | spine says | rows |
|---|---|---:|
| Federally recognized Alaska Native Village | Alaska Native Village Corporation | **391** |
| Federally recognized tribe | Alaska Native Regional Corporation | 15 |
| Federally recognized Alaska Native Village | Federally recognized tribe | 13 |
| Federally recognized Alaska Native Village | Alaska Native Regional Corporation | 8 |
| Federally recognized tribe | Tribal College or University | 8 |
| Federally recognized tribe | Native Community Development Financial Institution | 7 |
| Alaska Native Regional Corporation | Alaska Native Village Corporation | 6 |
| Federally recognized tribe | Alaska Native Village Corporation | 2 |
| Federally recognized tribe | Native Financial Institution | 1 |
| Federally recognized Alaska Native Village | ANCSA Group Corporation | 1 |

*(A further ~2,500 rows disagree only because the ledger uses a legacy
vocabulary — `FEDERAL_TRIBE_LOWER48`, `BGOV tribal vendor`,
`TRIBAL_UNCROSSWALKED_SBA`. Those are not counted above; they are a vocabulary
seam, not a class dispute.)*

**These 452 are a stale LABEL, not necessarily a wrong KEY** — the dominant
pattern is a ledger row whose `cedar_uid` correctly names the village
CORPORATION while the ledger's own class column still reads "village". But it is
the exact column a reader would consult to answer "what kind of entity is this?",
and it is wrong 5.4% of the time it is comparable. **The spine is the authority;
the ledger's `entity_class` should be derived, not stored.**

---

## 5. THE TWELVE TWO-HEADED `cedar_uid` VALUES — which head survives, and why

Raised by the ownership-queue reconciliation
(`docs/CEDAR_UID_COLLISIONS_2026-09-03.md`). **Independently re-measured for this
pass** against `data/clean/cedar_identifier_ledger_final.csv`.

> ### ⚠ THIS FILE IS BEING WRITTEN WHILE IT IS BEING MEASURED. TWO READINGS.
>
> | read at | `(uid, tribe_id)` pairs | uids with >1 `tribe_id` | minority-head rows |
> |---|---:|---:|---:|
> | 2026-09-03 ~00:30 EDT | 893 | **12** | 15 |
> | 2026-09-03 00:44 EDT | 894 | **13** | 16 |
>
> The ledger's mtime moved to `2026-09-03 00:44:03 -0400` between the two, i.e.
> another agent wrote it 44 seconds before the second read. Both readings were
> real when taken. **Twelve reproduced the reconciliation exactly; the
> thirteenth arrived during this pass**, and it is the same class as the rest:
>
> **`CE-0002B-CK`** — bound to `AKNF-INPTAS-00` **Inupiat Community of the
> Arctic Slope** — now also carries `ANVC-KPVKPT-00` **Ukpeaġvik Iñupiat
> Corporation** on `Uic Development Company`, 1 row. UIC is the ANCSA *village*
> corporation for Utqiaġvik; ICAS is the *tribe*. 43 U.S.C. §1607(a). Restamp
> the row to UIC's own uid. This is the Bowhead/UIC-versus-"Barrow" shape the
> ownership queue independently reported.
>
> **The count in this section will keep moving until the class is guarded.**
> Re-derive with `py -3 code/1164_native_legal_forms_classifier.py collisions`
> rather than quoting either number. The table in 5b is the 00:44 reading.

### 5a. A narrower and cheaper statement of the defect

**The identity register is not two-headed. The ledger ROW is.**

`code/1164_native_legal_forms_classifier.py collisions` checks it: for all twelve
uids, `data/spine/cedar_identity_register.csv` holds **exactly one** row —
`register rows per colliding uid : [1]`. Each uid binds to one entity,
`register_status = active`, and the spine agrees.

What is two-headed is the **row**: it carries a `cedar_uid` and a `tribe_id`
that name different entities, because two different matchers wrote the two
columns. **So no uid needs retiring, merging, splitting or reusing, and
`docs/IDENTIFIER_STANDARD.md` §0 is not engaged at all.** The remedy is to
re-stamp the ROW's `cedar_uid` from the register binding of its own `tribe_id`.
That is a column write on 15 rows, not identity surgery.

### 5b. The sixteen minority-head rows, with the head that survives

`review/native_legal_forms_uid_collisions_2026-09-03.csv`. In each row the
`tribe_id` is the head that survives and the `cedar_uid` is the head to
overwrite — **twelve of the thirteen are the single-token defect
`AGENT_FIELD_GUIDE.md` rule 11 already names**, and in every one of those the
`tribe_id` names a corporate owner the name actually supports while the
`cedar_uid` names a place or a word.

| uid | uid is bound to | row's `tribe_id` says | firm on the row | rows | prime $M | proposal | the statute that decides it |
|---|---|---|---|---:|---:|---|---|
| `CE-0012J-TB` | Buena Vista Rancheria | **Bristol Bay Native Corporation** | Vista Defense Technologies | 2 | 294.22 | restamp → `CE-0007A-ZA` | token `vista`. Two distinct legal persons: 43 U.S.C. §1606(d) corporation vs 25 U.S.C. §5123 tribe |
| `CE-0006R-ER` | Eagle (AK village) | **Bristol Bay Native Corporation** | Eagle Global Scientific; Eagle Integrated Healthcare; Eagle Health Analytics | 3 | 245.12 | restamp → `CE-0007A-ZA` | token `eagle` |
| `CE-0014C-0N` | Eastern Shoshone | **Cook Inlet Region, Inc.** | 16 `North Wind …` firms | 16 | 144.95 | restamp → `CE-0007D-HN` | token `wind` — Wind River is the Eastern Shoshone reservation. Named in `AGENT_FIELD_GUIDE.md` rule 11 |
| `CE-0006R-ER` | Eagle | **Cape Fox Corporation** | Eagle Health, Llc | 1 | 96.16 | restamp → `CE-00082-MJ` | token `eagle` |
| `CE-0006R-ER` | Eagle | **Bering Straits Native Corporation** | Eagle Eye Electric | 1 | 59.80 | restamp → `CE-00079-SH` | token `eagle` |
| `CE-00020-A0` | Fort Yukon | **K'oyitl'ots'ina, Ltd.** | Yukon Fire Protection Services | 1 | 47.03 | restamp → `CE-000A8-28` | token `yukon`; and 43 U.S.C. §1607(a) — the village corporation is not the village government |
| `CE-0005G-S0` | Saxman | **Cape Fox Corporation** | Saxman One, Llc | 1 | 33.50 | restamp → `CE-00082-MJ` | **the purest form of item 4**: Cape Fox Corporation is the ANCSA village corporation for Saxman. 43 U.S.C. §1607(a); `ANCSA_OWNERSHIP_RULING.md` rule 2 |
| `CE-0018V-EC` | Paiute of Utah | **Tikigaq Corporation** | Tikigaq Technology Services | 1 | 28.75 | restamp → `CE-000CN-TD` | no shared token at all; an Alaska village corporation on a Utah tribe's uid |
| `CE-00020-A0` | Fort Yukon | **Gana-A'Yoo, Ltd.** | Yukon Management, Llc | 1 | 7.05 | restamp → `CE-0008X-PN` | token `yukon`; 43 U.S.C. §1607(a) |
| `CE-0017X-NE` | Oneida (New York) | **Oneida Nation (Wisconsin)** | Oneida Total Integrated Enterprises | 1 | 3.11 | restamp → `CE-0017Y-V7` | **two separate sovereigns**, both on the 25 U.S.C. §5131 list. `NATIVE_ENTITY_NUANCES.md`: decided by where the money went |
| `CE-00170-7S` | Minnesota Chippewa | **Leech Lake** | Leech Lake Reservation Business Committee Inc | 1 | 1.11 | **OWNER RULING — see 5c** | 26 U.S.C. §7871(d) |
| `CE-0007C-BW` | Chugach Alaska Corporation | **Chugachmiut** | Chugach Regional Resources Commission | 1 | 0.82 | restamp → `CE-0010F-Y0` | 25 U.S.C. §5304(l) tribal organization ≠ 43 U.S.C. §1606 corporation. CRRC is a consortium of the Chugach-region villages, not an ANC subsidiary |
| `CE-0007D-HN` | Cook Inlet Region, Inc. | **Chugach Alaska Corporation** | Heide & Cook, Llc | 1 | 0.02 | restamp → `CE-0007C-BW` | token `cook`. Two §1606 corporations, different regions |
| `CE-0012P-JF` | Cabazon | **Cook Inlet Region, Inc.** | BUSINESS MISSION EDGE, LLC | 1 | 0.00 | restamp → `CE-0007D-HN`, **but see the caveat** | the Cabazon key is supported by nothing in the name; the CIRI key is unverified from the name either. Low value, but adjudicate rather than assume |
| `CE-0016E-P7` | Lumbee | **Cook Inlet Region, Inc.** | 35 `NORTH WIND …` CAGE codes | 35 | 0.00 | restamp → `CE-0007D-HN` | token `north` — `AGENT_FIELD_GUIDE.md` rule 11 names this exact collision on the Lumbee Tribe of *North* Carolina |
| `CE-0002B-CK` | Inupiat Community of the Arctic Slope | **Ukpeaġvik Iñupiat Corporation** | Uic Development Company | 1 | *(arrived 00:44)* | restamp → UIC's own uid | 43 U.S.C. §1607(a): the village CORPORATION is not the village TRIBE |

**Total: 16 rows.** Every one is tier B, `cluster_v3` or `need_v6` — **no owner
ruling is being overturned by any of them.** The `prime_dollars_M` recorded on
the fifteen rows present at the first reading summed to **$961.64M**; re-derive
rather than quoting it, for the reason in the box above.

### 5c. The one that law does not decide

**`CE-00170-7S` — Leech Lake ∥ Minnesota Chippewa Tribe.** This is not a token
collision. The Leech Lake Band **is** a constituent of the Minnesota Chippewa
Tribe, and the Minnesota Chippewa Tribe is the entity on the BIA list. Both keys
name something real.

The law gets you to the edge of an answer and stops. 26 U.S.C. §7871(d): a
subdivision of a tribal government is treated as a political subdivision
*"if (and only if) the Secretary determines (after consultation with the
Secretary of the Interior) that such subdivision has been delegated the right to
exercise one or more of the substantial governmental functions of the Indian
tribal government."* So there is a **federal determination with a record** that
would settle whether the Leech Lake Band is a legal person in its own right for
federal purposes. **Cedar does not hold that record and this pass did not
retrieve it — NOT RETRIEVED.**

**What the owner has to decide, stated as a choice rather than a question:**
> For a Federal Register listing that is ONE recognized tribe composed of named
> constituent bands (Minnesota Chippewa; Te-Moak; Paiute Indian Tribe of Utah;
> Capitan Grande), is the impermeable Cedar entity **the listed tribe**, with the
> bands as sub-hubs, or **each band**, with the listed tribe as an umbrella?

`docs/NATIVE_ENTITY_NUANCES.md` shows Cedar has already answered *both* ways in
different places — the Te-Moak bands and the Paiute of Utah bands carry their own
`CNSF` handles and receive money in their own names, while the Shoshone-Bannock
entry resolves to the joint government. Whichever way the owner rules, **the
`CE-00170-7S` row is wrong today**, because one uid currently carries both, and
that is true under either answer.

**Do not restamp this one on the pattern.** The other fourteen are mechanical;
this one is a ruling.

### 5d. A guard, proposed not applied — and it belongs in `1167`, not here

**`code/1167_cedar_uid_identity_collisions.py` is the DETECTOR for this class.
This pass is the ADJUDICATION.** Two detectors for one class drift — which is
why `code/248` is a retired stub pointing at `293` — and 1167's test is the more
durable of the two: it counts distinct `canonical_name` on a uid's positive rows
and **never reads `tribe_id`**, which is the retired CICD NEID
(`code/843_retire_cicd_scheme.py`). A test against a retired scheme measures the
retired scheme, and reports CLEAN the day the column is finally dropped.

`1164 collisions` reads `tribe_id` deliberately and for one reason: it is the
column that names *which other entity* the row is claiming, and therefore the
only thing that lets a legal form be attached to each head. If `tribe_id`
disappears from the ledger, `1164 collisions` prints **UNMEASURED** and points at
1167 — it does not print zero. That guard is in the code.


`code/846_session_audit.py:128` asserts *"every cedar_uid in the register is
unique and none is blank"* — a claim about the register table, which is true and
was true throughout. It cannot see this defect. The claim that fails is:

> For every `cedar_uid` in `cedar_identifier_ledger_final.csv`, the set of
> non-blank `tribe_id` values on its rows has exactly one member, **and** that
> member is the `tribe_id` the identity register binds that uid to.

The second half matters: the first half alone would pass if a uid were
consistently wrong. Both halves are computed by
`py -3 code/1164_native_legal_forms_classifier.py collisions`. **Tier-X rows
must be excluded before the set is taken** — a tier-X row is a refusal, and
counting a refusal as a resolution invents collisions and hides real ones. *(On
today's data the answer is 12 either way; the exclusion still belongs in the
guard, because it will not stay that way.)*

---

## 6. WHAT WAS NOT MEASURED, AND WHAT WAS NOT RETRIEVED

**NOT MEASURED.**
- Whether any Cedar entity actually *has* a §17 or OIWA §3 charter. Cedar holds
  no column for it, so the honest count is not zero — it is unmeasured.
- Whether the 5,820 `nest_enterprises` rows are tribal-law or state-law
  entities. The distinction decides taxability (Rev. Rul. 94-16) and no column
  carries it.
- Whether MOWA Choctaw Housing Authority is a NAHASDA TDHE. Turns on
  25 U.S.C. §4103(13), which admits state-recognized tribes for NAHASDA
  specifically. Not run.
- The 8(a) participant universe as such. Cedar has `reported_8a` on contract
  rows, which is a fact about an award, not a roster of participants.

**NOT RETRIEVED.**
- The State of Alaska corporate record for The 13th Regional Corporation
  (`commerce.alaska.gov`, 403 / JS challenge, three attempts). The dissolution
  is asserted only by an industry source.
- Any federal source labelling Goldbelt / Kenai Natives Association / Natives of
  Kodiak / Shee Atiká as **urban** corporations. The four *communities* are
  named in 43 U.S.C. §1613(h)(3) and in S. Rept. 118-221; the four *entities*
  are filed as village corporations by BLM.
- Any list of ANCSA **group** corporations by name.
- `akleg.gov` itself for AS 18.55.995/.996 (403 to three attempts). The text
  above is from law.onecle.com and codes.findlaw.com, which agree with each
  other and with the search index; **flagged as a mirror, not the official
  source.**
- eCFR for 13 C.F.R. §124.3, §124.109, §124.110, §124.506 — eCFR now 302s
  automated requests to `unblock.federalregister.gov`. Text above is from
  law.cornell.edu, **a mirror.** Re-verify against ecfr.gov before anything
  publishes on it.
- 13 C.F.R. §124.110(i) onward; §124.513(c)–(l); §124.520.

**The rule of three, applied to this pass.** Zero errors were found in the
`ANCSA_VILLAGE_CORPORATION` strict test against all 1,217,768 rows of
`prime_contracts.csv`. That licenses the statement *"the 2026-08-26 ruling
cleaned the prime table on the strict name-equality test"* — a floor. It does
**not** license "prime is clean of village/corporation confusion", because the
strict test only catches rows whose name is *exactly* the adjudicated
corporation name, and 46.3% of confirmed tribe→vendor linkages share no
non-generic token with the owner's name at all
(`docs/NATIVE_ENTITY_NUANCES.md`). The recall ceiling of any name test on this
class is roughly half, and no fuzzier matcher raises it.

---

## 7. HOW TO USE THIS

```
py -3 code/1050_preflight.py                                  # before you write
py -3 code/1164_native_legal_forms_classifier.py registry     # the JSON the identity layer reads
py -3 code/1164_native_legal_forms_classifier.py census       # per-form counts, denominators printed
py -3 code/1164_native_legal_forms_classifier.py conflicts    # the ranked wrong-key list
py -3 code/1164_native_legal_forms_classifier.py collisions   # the two-headed rows
py -3 code/1164_native_legal_forms_classifier.py verify       # exits 1 on a registry breach
py -3 code/1164_native_legal_forms_classifier.py selftest     # proves every detector FIRES
```

Outputs, all in `review/`, all dated, none of them data:

| file | what it is |
|---|---|
| `native_legal_forms_registry.json` | the machine-readable registry — 16 forms, statutes, URLs, dispositions, name patterns, forbidden key classes |
| `native_legal_forms_census_2026-09-03.csv` | per form, per file: rows matching, of those keyed, with the file's own row count as the denominator and `scan_cap = NONE` |
| `native_legal_forms_key_conflicts_2026-09-03.csv` | the ranked wrong-key list — 84 groups, 77 distinct triples |
| `native_legal_forms_crossform_names_2026-09-03.csv` | 70 ledger rows naming another entity of another form |
| `native_legal_forms_uid_collisions_2026-09-03.csv` | the 15 two-headed rows with the surviving head |

**Nothing in this pass changed a `cedar_uid`, a `tribe_id`, a tier or a dollar.**
Flag, never delete. `cedar_uid` is permanent.
