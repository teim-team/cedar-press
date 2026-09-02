# Untapped free federal corpora — reachability, verified samples, build plans

*Written 2026-08-26. Scripts claimed: **219**, **220**, **221** (`ls code/` showed
199 as the frontier; 200–218 unclaimed and left unclaimed).*

**Mandate:** *"Don't assume anything is fully settled — look for different sources
or ways to bypass limitations. No paying for stuff, but clever ways to scrape
data, Wayback, maybe it's in a report somewhere."*

**Method rule this file obeys throughout:** a source is not "reachable" because it
answered; it is reachable because a query about a **named Cedar entity** came back
with something we could **check against what we already hold**. Every cohort below
carries a `CONTROL_ABSENT` query — a name built so it cannot exist — because a
search API that returns something for everything is worse than one that returns
nothing. That control fired in this session: **ProPublica's organizations endpoint
returns HTTP 200 with `"name": "Unknown Organization"` for EIN `999999999`.**

Vocabulary is the one already in force (`AGENTS.md`, "A BROKEN SEARCH IS NOT
EVIDENCE OF ABSENCE"): `PUBLISHES` · `WITHHOLDS` · `NOT_FOUND` (swept, naming what
was swept) · `NOT_CHECKED` (nobody looked). `NOT_CHECKED` appears here honestly and
often. A guess does not.

---

## SUMMARY TABLE

| | source | prior Cedar status | reachable | sampled against a known entity | verdict |
|---|---|---|---|---|---|
| **B** | **api.govinfo.gov** | used (OIRA/hearings, FL gaming) — **never for statute** | ✅ 200, 36,000/hr | ✅ 43 U.S.C. §1606 / §1607 / §1602 retrieved and quoted | **SETTLED A RECORDED BLOCKER** |
| **A** | **CourtListener / RECAP** | *partially* used — 5 dockets typed by hand in `139` | ✅ 200 anon; 429s under load | ✅ 37 queries / 4 cohorts / 304 dockets | **HIGH VALUE, NEW** |
| **C** | **api.regulations.gov** | **NEVER TOUCHED** | ✅ 200 on the existing api.data.gov key | ✅ 33 queries / 589 comments / 25 details / 1 verbatim quote | **HIGH VALUE, NEW** |
| **E** | ProPublica + IRS e-file index | ProPublica used; **bulk/index tier unbuilt** | ✅ both | ✅ all 6,217 no-BMF EINs × 10 index years | **CORRECTS A PUBLISHED CLAIM** |
| **D** | efts.sec.gov full-text | used (`105`, `142`, `148`) | ✅ 200 | ✅ `"Chenega Corporation"` → 212 hits | reachable, **not swept** |
| **F** | Wayback CDX | used heavily; technique #1 | ✅ 200 | ✅ `chenega.com` PDF enumeration answered | reachable; lock stale, see below |
| **G1** | NSF award API | never touched | ✅ 200 | ✅ Salish Kootenai College TCUP awards | `NOT_SWEPT` |
| **G2** | NIH RePORTER v2 | never touched | ✅ 200 **on POST** (GET → 405) | ✅ Salish Kootenai College, 42 projects | `NOT_SWEPT` |
| **G3** | Census CFFR archive | never touched | ✅ 200, **1981–2010** | partial — directory listing only | `NOT_CHECKED` (contents) |
| **G4** | GSA eLibrary | never touched | ✅ 200 root | ❌ | `NOT_CHECKED` |
| **G5** | DOL Form 5500 bulk | staged by `156`, unmerged | ✅ 301 → `www.askebsa.dol.gov` | ❌ | `NOT_CHECKED` (owned elsewhere) |
| **G6** | FPDS-NG ATOM | plan of record says **stop** | ✅ 200 | ✅ and it **returned an EMPTY FEED** for CHENEGA | **confirms the stop** |
| **G7** | FOIA reading rooms | used as a discovery index (`136`) | — | — | `NOT_CHECKED` — already doctrine'd |
| — | USASpending Custom Award Download | **another agent owns it** | — | — | not contacted, by instruction |
| — | api.sam.gov · api.usaspending.gov · NIGC · state regulators | — | — | — | not contacted, by instruction |

---

# THE HEADLINE: THE ANCSA §7(h) QUESTION IS SETTLED

`docs/ANCSA_OWNERSHIP_RULING.md` carries an **OPEN QUESTION — UNRESOLVED. Do not
answer by inference**, raised by the owner on 2026-08-26 and left open
deliberately:

> 1. **Do adopted persons receive shares?**
> 2. **May shares be gifted to non-Natives?**
> 3. **May shares be gifted to a spouse?**
>
> *"Nothing in this repository answers these, and nothing in this repository may
> assume an answer."*

It names what would settle it: **ANCSA §7(h), 43 U.S.C. §1606(h)**, its 1987
amendments (Pub. L. 100-241), *"quoted verbatim with its URL."*

**Retrieved today from api.govinfo.gov.** Three granules, HTTP 200 each, saved to
`data/raw/external/untapped_2026-08-26/`. Public, key-free URLs given so any
reader can check them:

| provision | public URL |
|---|---|
| 43 U.S.C. §1606 (ANCSA §7) | `https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1606.htm` |
| 43 U.S.C. §1607 (ANCSA §8, Village Corporations) | `https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1607.htm` |
| 43 U.S.C. §1602 (Definitions) | `https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1602.htm` |
| Pub. L. 100-241, *Alaska Native Claims Settlement Act Amendments of 1987*, 101 Stat. 1788, **enacted 1988-02-03** | `https://www.govinfo.gov/content/pkg/STATUTE-101/pdf/STATUTE-101-Pg1788.pdf` |

## §1606(h) applies to VILLAGE corporations, which is the population Cedar holds

Cedar's 334 defects are about **village** corporations; §1606 is headed *Regional
Corporations*. The bridge is **43 U.S.C. §1607(c)**, verbatim:

> **"(c) Applicability of section 1606**
> The provisions of subsections (g), (h) (other than paragraph (4)), and (o) of
> section 1606 of this title shall apply in all respects to Village Corporations,
> Urban Corporations, and Group Corporations."

*(Credit line: Pub. L. 92-203, §8, Dec. 18, 1971, 85 Stat. 694; **Pub. L. 100-241,
§6, Feb. 3, 1988, 101 Stat. 1795**; Pub. L. 104-10, §1(b), May 18, 1995, 109 Stat.
157. The 1995 amendment is what inserted "(other than paragraph (4))".)*

**Without this section the whole answer would be about the wrong corporations.**

## The operative text — 43 U.S.C. §1606(h)(1), verbatim

> **(h) Settlement Common Stock**
> **(1) Rights and restrictions**
> …
> **(B)** Except as otherwise provided in this subsection, Settlement Common Stock,
> inchoate rights thereto, and rights to dividends or distributions declared with
> respect thereto shall not be—
> (i) sold;
> (ii) pledged;
> (iii) subjected to a lien or judgment execution;
> (iv) assigned in present or future;
> (v) treated as an asset under— (I) title 11 or any successor statute, (II) any
> other insolvency or moratorium law, or (III) other laws generally affecting
> creditors' rights; or
> (vi) otherwise alienated.
>
> **(C)** Notwithstanding the restrictions set forth in subparagraph (B),
> Settlement Common Stock **may be transferred to a Native or a descendant of a
> Native**—
> (i) pursuant to a court decree of separation, divorce, or child support;
> (ii) by a holder who is a member of a professional organization, association, or
> board that limits his or her ability to practice his or her profession because he
> or she holds Settlement Common Stock; or
> (iii) **as an inter vivos gift from a holder to his or her child, grandchild,
> great-grandchild, niece, nephew, or (if the holder has reached the age of
> majority as defined by the laws of the State of Alaska) brother or sister,
> notwithstanding an adoption, relinquishment, or termination of parental rights
> that may have altered or severed the legal relationship between the gift donor
> and recipient.**

*(The trailing clause of (C)(iii) is not original 1988 text. Amendment note,
§1606: **"2000—Subsec. (h)(1)(C)(iii). Pub. L. 106-194 inserted before period at
end ', notwithstanding an adoption, relinquishment, or termination of parental
rights that may have altered or severed the legal relationship between the gift
donor and recipient'."** Structure of (h)(1)–(3) is the 1988 work: **"1988—…
Subsec. (h)(1), (2). Pub. L. 100-241, §5, amended pars. (1) and (2) generally,
changing structure of each from a single unlettered paragraph to one consisting of
subpars. (A) to (C)."**)*

## §1602 supplies the two definitions the answer turns on

> **(b) "Native"** means a citizen of the United States who is a person of
> one-fourth degree or more Alaska Indian … Eskimo, or Aleut blood, or combination
> thereof. **The term includes any Native as so defined either or both of whose
> adoptive parents are not Natives.** …
>
> **(r) "Descendant of a Native"** means—
> (1) a lineal descendant of a Native or of an individual who would have been a
> Native if such individual were alive on December 18, 1971, or
> **(2) an adoptee of a Native or of a descendant of a Native, whose adoption—
> (A) occurred prior to his or her majority, and (B) is recognized at law or in
> equity;**
>
> **(s) "Alienability restrictions"** means the restrictions imposed on Settlement
> Common Stock by section 1606(h)(1)(B) of this title;

## THE THREE ANSWERS

| owner's question | statutory answer | authority |
|---|---|---|
| **1. Do adopted persons receive shares?** | **YES — an adoptee is inside the eligible class, not outside it.** §1602(r)(2) puts *"an adoptee of a Native or of a descendant of a Native, whose adoption (A) occurred prior to his or her majority, and (B) is recognized at law or in equity"* squarely within **"descendant of a Native"**, which is the class §1606(h)(1)(C) transfers may run to. §1606(h)(1)(C)(iii) then says a gift is good **"notwithstanding an adoption, relinquishment, or termination of parental rights that may have altered or severed the legal relationship"** — so adoption does not break the donor-recipient relationship the gift clause requires. And §1602(b) protects the other direction: a Native *"either or both of whose adoptive parents are not Natives"* is still a Native. **Two conditions attach and must not be dropped: adopted before majority, and recognised at law or in equity.** An adult adoption does not qualify. | §1602(b), §1602(r)(2), §1606(h)(1)(C)(iii) |
| **2. May shares be gifted to non-Natives?** | **NO.** Every route in §1606(h)(1)(C) is expressly *"to a Native or a descendant of a Native"*, and (h)(1)(B)(vi) forecloses the residue — *"otherwise alienated."* A non-Native can come to hold Settlement Common Stock only through **death**, not gift: §1606(h)(2) governs *"Inheritance of Settlement Common Stock"* and the stock passes *"in accordance with the lawful will of such holder or pursuant to applicable laws of intestate succession."* Two consequences travel with it, both verbatim: the corporation *"shall have the right to purchase at fair value Settlement Common Stock transferred pursuant to applicable laws of intestate succession to a person not a Native or a descendant of a Native"*; and §1606(h)(2)(C) — stock *"transferred by will or pursuant to applicable laws of intestate succession after February 3, 1988"* or *"transferred by any means prior to February 3, 1988"* to a non-Native/non-descendant **"shall not carry voting rights. If at a later date such stock is lawfully transferred to a Native or a descendant of a Native, voting rights shall be automatically restored."** | §1606(h)(1)(B)(vi), (h)(1)(C), (h)(2)(A)–(C) |
| **3. May shares be gifted to a spouse?** | **NO — a spouse is not in the enumerated class.** §1606(h)(1)(C)(iii) lists exactly: *"his or her child, grandchild, great-grandchild, niece, nephew, or (if the holder has reached the age of majority as defined by the laws of the State of Alaska) brother or sister."* **Spouse is absent, and the list is closed** — (h)(1)(B) is a prohibition and (C) is the exception to it, so anything not enumerated is barred. A spouse may still receive stock two other ways: **by will or intestate succession** (h)(2), and **under a court decree of separation, divorce, or child support** (h)(1)(C)(i) — that route, unlike inheritance, still requires the spouse to be *a Native or a descendant of a Native*. | §1606(h)(1)(C)(i), (C)(iii) |

## THE CAVEATS THAT MUST TRAVEL WITH THIS ANSWER

The ruling document's second condition still stands and is **not** settled here:

1. **These restrictions are not permanent.** §1606(h)(3) and **43 U.S.C. §1629c**
   provide for **termination of alienability restrictions** by shareholder vote and
   the exchange of Settlement Common Stock for **Replacement Common Stock**. Every
   answer above is conditioned on *"any period in which alienability restrictions
   are in effect"* — the statute's own phrase, at §1606(g)(1)(D). Whether any
   specific corporation has terminated is a **per-corporation fact this file does
   not hold**. `sec1629c.txt` (20,170 chars) is on disk, unread.
2. **A corporation may add restrictions of its own.** §1606(h)(3)(D): *"Prior to
   the date on which alienability restrictions terminate, a Regional Corporation
   may amend its articles of incorporation to impose upon Replacement Common
   Stock"* further terms, including a **right of first refusal**. §1606(g) also lets
   a corporation issue additional classes of stock. **So a statutory answer is a
   floor, not the operative answer for a given ANC** — exactly what
   `ANCSA_OWNERSHIP_RULING.md` warned, and the same error shape the Federal Audit
   Clearinghouse already cost this project.
3. **The naming trap in the question itself, resolved.** The ruling doc says *"the
   1987 '1991 Amendments' (Pub. L. 100-241)"*. Both labels are right and the year
   is not the enactment year. GovInfo's Statutes at Large granule
   **STATUTE-101-Pg1788** is titled *"Alaska Native Claims Settlement Act
   **Amendments of 1987**"* with `dateIssued` **1988-02-03**, and §1606's credit
   line reads **"Pub. L. 100-241, §§4, 5, 12(a), Feb. 3, 1988, 101 Stat. 1790,
   1792, 1810."** That is also why **February 3, 1988** is the hinge date written
   into (h)(2)(C).
4. **Does it change any of the 334?** No — and that was already measured, not
   assumed, by `code/191_apply_ancsa_ownership_ruling.py`. Nothing above touches
   *which legal person owns an operating company*. It unblocks the
   **shareholder-level** measure the ruling doc says is *"blocked on this question,
   not merely informed by it."*

---

# A — CourtListener / RECAP · **HIGH VALUE, AND NOT PREVIOUSLY SWEPT**

`code/219_probe_courtlistener_recap.py`

### Correction to the premise
The brief says "completely unused." **It is not.**
`code/139_build_litigation_positions.py` uses CourtListener — but by hand: five
Brackeen docket rows and a West Flagler block, each URL typed out, no query, no
sweep, no entity keying. Its own caveat: *"RECAP coverage of this docket is
PARTIAL … the absence of an organisation here is NOT evidence it did not file."*
**219 is the first entity-keyed sweep.** The right claim to publish is
"unswept", not "unused".

### Reachability, measured
| fact | value |
|---|---|
| `www.courtlistener.com/api/rest/v4/` anonymous | **HTTP 200**, full endpoint map |
| `www.courtlistener.com/robots.txt` | **HTTP 403** — CloudFront `Request blocked`, a fact about that route only |
| search `type=r` anonymous | **HTTP 200**, cursor-paginated |
| throttle | **HTTP 429 on 4 of 41 queries at a 2.5 s gap.** Not an edge block: 200s resumed. A token (free, Free Law Project) lifts it |
| token | not used; none on this machine. `COURTLISTENER_TOKEN` is read if set |

### The sample — 37 queries, 4 cohorts, 304 docket rows

| cohort | n | ≥1 docket | ≥1 **verified party** | dockets | documents | free PDFs on page 1 |
|---|---:|---:|---:|---:|---:|---:|
| `ANCSA_OPCO` (the 334's operating companies, top by $) | 19 | 8 | **8** | 53 | 691 | 42 |
| `ANCSA_PARENT` (their village corporations) | 7 | 7 | **5** | 84 | 1,053 | 45 |
| `GAMING` (gaming operators) | 10 | 10 | **9** | 24,583 | 59,517 | 162 |
| **`CONTROL_ABSENT`** | 1 | **0** | **0** | **0** | **0** | **0** |

**The control returning zero is the load-bearing row.** It is what makes the other
three lines mean something.

### The verified match — and it corroborates the owner's rule 1 on a named defect row

Cedar defect row (`review/identifier_one_to_many_defects_2026-08-26.csv`):

```
usd_observed  572,575,724
observed_name AURORA INDUSTRIES LLC
identifier    UEI EKUWXPKJ2EV3
entities      AKNF-NOMECM-00-BERSTR-KAWRAK | ANVC-SITNAS-00
defect_family ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION
```

RECAP returns **`Pease v. Sitnasuak Native Corporation`**, D.P.R. `3:16-cv-01562`,
filed 2016-03-30, cause `42:2000e Job Discrimination (Employment)` —
`https://www.courtlistener.com/docket/4529248/pease-v-sitnasuak-native-corporation/`

Its `party` array, verbatim:

> `Aurora Industries, LLC | SNC Technical Services, LLC | Company ABC | National
> Union Fire Insurance Company of Pittsburgh PA | Sitnasuak Native Corporation |
> John Doe | Thomas Pease | Insurance Company XYZ | API Manufacturing, LLC |
> Humberto Zacapa | SNC Manufacturing, LLC`

**The operating company and the VILLAGE CORPORATION are co-defendants in one
caption. The village government is not in it.** That is an independent, retrieved
corroboration of rule 1 on this specific row — and, more usefully, it is the shape
of evidence that rule 3 (*"a village government CAN directly own an enterprise …
an exception you must EVIDENCE, not assume"*) requires. **A caption is a
corporate-family disclosure that no regulator publishes.** The docket also
surfaces `SNC Technical Services, LLC` and `SNC Manufacturing, LLC` — two sibling
names Cedar's spine can be checked against.

Other captions of the same kind, all `VERIFIED_PARTY`:
`FPM Remediations, Inc. v. United States` ×2 (**Court of Federal Claims** —
contract claims, the 8(a) world); `Chenega Infinity, LLC v. Transport Worker Union
of America, AFL-CIO`; `Goldbelt Wolf, LLC v. Operational Wear Armor, LLC`.

### The trap this cohort found
`Seminole v. Berkebile`, D. Mont., `42:1983 Prisoner Civil Rights` — **"Seminole"
is a surname.** A short tribe name is also a surname, a county and a town, and the
`GAMING` cohort's 24,583 dockets are mostly that. **The `party` array is the
verifier; the caption is not.** `match_class` in the output separates
`VERIFIED_PARTY` / `NAME_IN_CAPTION_ONLY` / `NAME_IN_DOCUMENT_TEXT_ONLY` for
exactly this reason, and nothing downstream may consume the last two as a link.

### What it adds
- **Dated corporate-family captions** for ANCSA and 8(a) structures — the input
  `docs/INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md` §5b wants for the
  ten dated ownership changes, and the evidence rule 3 requires.
- **Court of Federal Claims** dockets: contract disputes and bid protests, keyed
  to a company Cedar already holds by UEI.
- **Free PDFs.** 249 documents on page 1 of the sample carry `is_available: true`
  — retrievable from CourtListener at no cost, no PACER account, no fee.
- **Firms and attorneys** as a second identifier surface (`Jackson Lewis PC`
  appears on all four Chenega labour dockets).

### What it does NOT do, measured
**It does not yet unblock per-property gaming revenue.** 162 free PDFs sit on
page 1 of the gaming cohort; **whether any contains a revenue schedule is
`NOT_CHECKED`** — that is a document-reading pass, not a search pass, and it is the
phase-2 test. Recording it as "sealed data recovered" today would be a guess.

### Build plan
1. **Get a free Free Law Project API token** and put it in
   `dissertation/docs/API_KEYS.md`. It moves anonymous-throttled to 5,000/hr and
   is the single cheapest unblock here.
2. **Sweep by identifier cohort, not by tribe name.** Query the *operating company*
   names from `prime_contracts.csv` / the defect file, never bare tribe names —
   the `GAMING` cohort proves bare names return mostly noise.
3. **Keep `match_class`.** Only `VERIFIED_PARTY` may become a link, and its tier is
   **inherited from the docket row**, never assigned because a caption is exact.
   (`START_HERE.md` trap 1: *"the exactness of the KEY says nothing about the
   correctness of the LINK."*)
4. **Then** walk `docket-entries` / `recap-documents` for `is_available` PDFs on
   the verified dockets only, and read them for revenue schedules and ownership
   charts. Gate on `PER_DOCKET` retrieved-vs-reported (`AGENTS.md` concurrency
   rule 7) — CourtListener states `count` and `document_count` on every response.
5. Stage to `data/staging/`. Never write into `deals_classified.csv` or the spine
   directly.

---

# C — regulations.gov · **NEVER TOUCHED, AND IT IS THE MISSING HALF OF THE ADVOCACY SPEC**

`code/221_probe_regulations_gov_comments.py`

### Why this one matters more than its size suggests
`docs/LOBBYING_EXPANSION_RECONCILIATION.md` refuses to build
`position_on_native_issue` — *"a characterisation we would be authoring, published
under our name, about a named organisation"* … *"the single most legally exposed
field we would ship"* — and prescribes instead: **"Build the fact, not the
verdict."** Its `AdvocacyChannel` enum has an `ADMINISTRATIVE_COMMENT` member with
**no source behind it**.

A public submission on a rulemaking docket is that fact in its purest form: a named
organisation, a dated federal docket, and **the organisation's own words**. It is
also the only channel in the enum where **the tribe is the speaker** — the 27,796
LDA filings record who was *hired*.

### Reachability, measured
| fact | value |
|---|---|
| `api.regulations.gov/v4` with the **existing api.data.gov key** | **HTTP 200.** No new credential needed — one api.data.gov key serves every api.data.gov-fronted service, exactly as `code/147` records for `api.fac.gov` |
| `www.regulations.gov/robots.txt` (honest UA) | **HTTP 403**, CloudFront |
| `www.regulations.gov/robots.txt` (**declared browser UA**) | **HTTP 200** — and its full content is `User-agent: *` / `Disallow:` — **nothing is disallowed** |
| `downloads.regulations.gov/<id>/attachment_1.pdf` (honest UA) | **HTTP 403** |
| same, declared browser UA | **HTTP 200**, 1,777,774 bytes |

**Recorded as a departure, because it is one.**
`docs/LOBBYING_EXPANSION_RECONCILIATION.md` says of `nrc.gov`: *"a browser-shaped
User-Agent was **refused** where the honest `CedarPress-research/1.0` string was
served. **Do not 'fix' this by pretending to be Chrome.'"* **This host is the
mirror image** — the honest string is refused and the browser string is served,
and robots.txt (fetched with the string that works) allows everything. The rule is
not "never send a browser UA"; the rule is **measure it per host and write down
which one you used**. `docs/ACCESS_TECHNIQUES.md` already lists the declared-UA
curl as the first thing to try on a 403. The API leg uses the honest UA and a key;
only the CDN attachment leg needs the browser string.

### The sample — 33 queries across 6 entity classes, 589 comment rows

| cohort | n | ≥1 comment |
|---|---:|---:|
| Federally recognized tribe | 14 | 14 |
| Intertribal Organization | 6 | 5 |
| Alaska Native Regional Corporation | 4 | 3 |
| Federally recognized Alaska Native Village | 3 | 3 |
| Native Hawaiian Organization | 3 | 1 |
| Tribal College or University | 2 | 2 |
| **`CONTROL_ABSENT`** | 1 | **0** |

**4,467 comments** matched across the sample. Agency spread on page 1 (589 rows):
EPA 101 · DOI 36 · FWS 35 · CMS 35 · BOEM 29 · BIA 28 · SBA 28 · NOAA 24 ·
NHTSA 23 · ED 20 · FS 18 · CEQ 17. **Sixteen agencies on a single tribe** (Three
Affiliated Tribes, 372 comments) — this is a cross-agency advocacy surface Cedar
has nothing comparable to.

### The verified sample — an actual retrieved position, quoted

`CEQ-2019-0003-171421` → detail endpoint → `organization: "Federated Indians of
Graton Rancheria"` (an exact match to the spine's canonical name) → attachment
`https://downloads.regulations.gov/CEQ-2019-0003-171421/attachment_1.pdf`,
10 pages, **31,627 characters of extractable text**, posted 2020-03-11:

> *"These comments on the Proposed Rule are submitted by the **Federated Indians of
> Graton Rancheria** ("the Tribe"), a federally recognized Tribe in California
> comprised of Coast Miwok and Southern Pomo people. While we support, in general,
> the goal of the Council on Environmental Quality ("CEQ") to update the rule to
> allow "more efficient, timely, and effective" compliance with the requirements of
> the National Environmental Policy Act ("NEPA"), **the Tribe disputes the need for
> several changes in the Proposed Rule that would negatively impact environmental
> and cultural protections.** … **As a threshold matter, the CEQ failed to
> meaningfully consult with tribal governments during this rulemaking process.**"*

That is `lda_position_reported`'s administrative twin: **speaker, docket, date,
verbatim text.** No verdict authored, none needed.

### THREE TRAPS THIS SAMPLE FOUND, ALL OF WHICH WOULD HAVE CORRUPTED THE BUILD

1. **The search `title` is NOT the speaker.** I classified page-1 hits by whether
   the search-result `title` named the entity. **59 of 589 passed. Two of the 25 I
   then fetched in detail were false**: `CEQ-2019-0003-478909` and
   `ETA-2019-0005-121688` matched **"Torres Martinez" as a person's surname pair**
   in a mass-comment campaign, and their texts are a NEPA-deregulation form letter
   and a LIUNA apprenticeship form letter — **nothing to do with the Torres
   Martinez Desert Cahuilla Indians.** The correct predicate is the **detail
   endpoint's `organization` field**. Of the 25 details fetched, **3 carry an
   organization naming the entity** (Federated Indians of Graton Rancheria ×2,
   Miami Tribe of Oklahoma ×1). **Search hit ≠ attribution**, and a mass-comment
   campaign will manufacture thousands of the wrong kind.
2. **The position is in an ATTACHMENT, not in the comment body.** **21 of 25**
   details carry an attachment; the inline `comment` field is typically 12–20
   characters — *"See attached file(s) from Miami Tribe of Oklahoma."* Only **2 of
   25** carry >200 characters inline, and **both of those are the false
   positives**. A build that reads only the API's `comment` field gets nothing from
   the real tribal submissions and a lot from form letters. **The signal is
   inversely correlated with the field that is easy to read.**
3. **Not every attachment has a text layer.** `DOI-2022-0016-0015`
   (Miami Tribe of Oklahoma, 3 pages, 1.78 MB) extracts **zero characters** — a
   scanned letter on tribal letterhead. `code/150_run_ocr_overnight.py` already
   exists for this class of object.

### What it adds
- The first source for `AdvocacyChannel.ADMINISTRATIVE_COMMENT`.
- Positions as **retrieved facts**, which is what the reconciliation document
  asked for and what nothing in the repo currently supplies.
- The `alignment` field becomes computable: a tribe's comment on docket X and an
  industry commenter's comment on **the same docket X** are two sourced positions
  on one object, so `SAME | OPPOSED | NO_TRIBAL_POSITION_FOUND` is derived, not
  authored. **A shared docket id is a far cleaner join than a shared bill id.**
- The 4,289-row IBIA/IBLA "opposition layer" gets a second, dated channel.

### Build plan
1. **Sweep by docket, not by entity.** Pull `documents` for tribal-relevant dockets
   (BIA, DOI, IHS, EPA, FWS, BOEM, SBA, ED, CMS), then `comments` filtered on
   `filter[commentOnId]`. This yields **both sides on one object** — the whole point
   — and avoids the surname problem entirely. Entity-keyed search is the *second*
   pass, for coverage.
2. **Attribute on `organization` from the detail endpoint. Never on `title`.**
   Record `TEXT_MENTION_ONLY` rows but never promote them.
3. **Fetch attachments** with the declared browser UA, `.part`-then-rename, log the
   UA used per request. **Text-layer test on every PDF**; route the empties to the
   existing OCR queue rather than dropping them.
4. **Store the verbatim text and the URL. Write no position label.** Not `Support`,
   not `Oppose`, not `Mixed`. If a general-stance label is ever wanted it is a hand
   ruling by Elijah, tiered like any other.
5. Host lock `logs/_HOSTLOCK_api.regulations.gov.json` (created and released by
   221) and a second for `downloads.regulations.gov`. 1,000/hr on the api.data.gov
   key; the CDN is unmetered but should still be one stream.

---

# E — the 6,217 no-BMF EINs · **A PUBLISHED CLAIM IS PARTLY WRONG, MEASURED TWO WAYS**

`code/220_test_nobmf_eins_against_efile_index.py`

### The claim under test
`docs/SCHEDULE_I_BUILD_LOG.md` line 133, echoed as a *publishable sentence* in
`docs/EDITORIAL_PIPELINE.md` line 2699 and marked **✅ VERIFIED 2026-08-26**:

> *"6,217 distinct recipient EINs are printed on a filed Schedule I and absent
> from the entire BMF. **That** is the 7871 signature — an entity outside the Form
> 990 universe, **most often a tribal government. It files no return. This is not
> a gap and is not queued as one.**"*

and line 293: *"The 6,217 no-BMF recipient EINs are **the most Native-dense group
in the file**."*

That conclusion rests on **one** corpus — the BMF, 1,957,340 rows. The BMF is the
roster of organisations with an **exemption ruling**. An entity is absent from it
for at least four reasons, only one of which is §7871.

### Test 1 — a second corpus with a different membership rule

Streamed the **IRS Form 990 e-file index**, `apps.irs.gov`, submission years
**2017–2026**, ten files, 5,576,866 index rows, filtered to the 6,217. Nothing
stored whole; host lock claimed and released.

| | EINs | dollars |
|---|---:|---:|
| no-BMF recipient EINs | 6,217 | $4,915,941,725 |
| **found in the IRS e-file index** | **424 (6.8%)** | **$144,353,351 (2.9%)** |
| absent from **both** corpora | 5,793 (93.2%) | $4,771,588,374 (97.1%) |

**So "It files no return" is FALSE for 424 named EINs — and the two-source test
confirms it for the other 5,793.** That is the outcome a good probe should have:
the headline survives at 93%, and the 424 exceptions are now a named, retrievable
list rather than an assumption. Return types: 990 ×229, 990+990EZ ×76, 990EZ ×56,
990+990O ×17, 990PF ×8, 990T ×6.

**Two of the 424 are entity discovery, immediately:**
`824315629` **Clare Swan Early Learning Center** — **$17,979,284**, the largest
single no-BMF recipient with a filed 990, and a Kenaitze Indian Tribe institution;
`921975377` **ILLUMINATIVE INC** — $6,406,362, a Native-led nonprofit. Both file
retrievable returns and **neither is in `np_orgs`.**

**Coverage caveat that must travel with every one of these verdicts:** mandatory
e-filing arrived with the Taxpayer First Act and **the index begins at submission
year 2017**. `index_2016.csv` and earlier **HTTP 302 → `https://www.irs.gov/404`**
(measured). Absence from the index therefore means *"did not e-file a 990-family
return 2017–2026"*, **not** *"files no return"*. `code/140` already records this.

### Test 2 — where the $4.92B actually goes

This is the part that changes how the number may be published. Decomposed locally,
zero network:

| | |
|---|---:|
| $4,915,941,725 from filers **ruled Native** | **$3,855,549 — 0.078%**, on 39 of 16,344 rows |
| top single filer: **Johns Hopkins University** (EIN 520595110) | **$1,976,757,533 — 40.2%** |
| next: National Fish and Wildlife Foundation (521384139) | $1,454,214,867 |
| then: Univ. of Kentucky Research Foundation, New Venture Fund, Mayo Clinic, The Nature Conservancy | — |
| share reaching a recipient Cedar has **linked to its spine** | **$122,736,192 — 2.50%** |

The largest recipients are `LA Coastal Protection & Restoration` ($508.8M),
`UNIVERSITY OF KENTUCKY` ($325.4M), `LOCKHEED MARTIN CORP-MST-UNDERSEA SYSTEMS
BUSINESS UNIT` ($202.7M), `MS Department of Environmental Quality` ($111.4M),
`WESTAT CORP`, `ALABAMA DEPT OF EDUCATION`, `AEROJET ROCKETDYNE INC`,
`HARRIS CORPORATION`, `ROCKWELL COLLINS INC`, `L-3 COMMUNICATIONS`.

**These are state agencies, public universities and defence primes.** They are
absent from the BMF because they are **government units and for-profit companies**,
which never had an exemption ruling — not because of §7871.

### What survives, and what does not

| claim | verdict |
|---|---|
| *"6,217 distinct recipient EINs … absent from the entire BMF"* | **TRUE.** Reproduced exactly. |
| *"$4,915,941,725 — 29.90%"* | **TRUE.** Reproduced exactly. |
| *"It files no return"* | **FALSE for 424 of them / $144.4M.** True for 5,793 / $4.77B, now on two corpora instead of one. |
| *"most often a tribal government"* | **UNSUPPORTED as stated, and false at the top of the dollar distribution.** Untested by row; the largest recipients are state agencies and defence primes. |
| *"the most Native-dense group in the file"* | **TRUE, and it is a RATE claim, not a dollar claim.** 1,565 of 16,344 no-BMF rows (9.6%) carry a `recipient_entity_id` against 615 of 39,178 in-BMF rows (1.6%) — **6× denser.** But only **2.50% of the dollars** reach a spine-linked recipient. |

**The publishable sentence in `EDITORIAL_PIPELINE.md` needs one clause added**, or
a reader will take $4.92B as a Native-philanthropy figure. It is not: **86.7% of
all 58,685 Schedule I rows come from filers whose Native status is
`not_in_np_orgs_universe_native_status_not_established`, and only 60 rows in the
entire file come from a filer ruled Native.** The file's own `native_status_caveat`
column is honest; the prose quoting it is what drops the caveat.

### Reachability notes worth keeping
- **`curl -I` is useless for sizing `apps.irs.gov`** — HTTP 200 with no
  `Content-Length`. And a **`Range` request is ignored**: `-r 0-2000` on
  `index_2023.csv` downloaded all **77,519,435 bytes**. Stream and filter; never
  probe by range.
- **ProPublica's `organizations/{ein}.json` returns HTTP 200 for an EIN it does not
  hold**, with `"name": "Unknown Organization"` and every field null. Measured on
  `999999999`. **Do not test membership by status code on this endpoint.**
  `projects.propublica.org/robots.txt` disallows `/nonprofits/search*`,
  `/nonprofits/name_search*`, `/nonprofits/full_text_search*`,
  `/nonprofits/display_990*`, `/nonprofits/download-filing*` — **`/nonprofits/api/`
  is not disallowed.** The three search paths are the ones the API replaces, so the
  API is the compliant route by construction.

### Build plan
1. `review/schedule_i_nobmf_eins_efile_verdict_2026-08-26.csv` — 6,217 rows,
   `verdict ∈ {FILES_A_990_EFILE, ABSENT_FROM_BMF_AND_EFILE}`. **The 424 are a
   retrieval queue**, not a finding: each has an `object_id`, so the filed XML
   range-reads out of the published ZIPs by `code/140`'s existing method.
2. Add a `recipient_absence_reason` typed column and stop letting one bucket carry
   four causes: `GOVERNMENT_UNIT` · `FOR_PROFIT` · `IRC_7871_TRIBAL_GOVERNMENT` ·
   `EFILES_BUT_NOT_IN_BMF` · `UNKNOWN`. Resolve the top 100 by dollars by hand —
   that is 90%+ of the money and about an hour.
3. Amend `docs/SCHEDULE_I_BUILD_LOG.md` and `docs/EDITORIAL_PIPELINE.md`. **Do not
   overwrite the originals** — this repo has no version control and
   `docs/DOC_CONTRADICTIONS_2026-08-26.md` exists precisely because superseded
   figures keep looking authoritative. Append a dated correction and register it.
4. The §7871 roster (577 tribal governments) is still the right product. It is now
   **5,793 EINs, $4.77B**, minus the government-unit and for-profit rows — a smaller
   and much more defensible number than 6,217 / $4.92B.

---

# D — SEC EDGAR full-text search · reachable, **not swept**

`efts.sec.gov` answers HTTP 200. Verified sample: `q="Chenega Corporation"` →
**212 hits**, top result `0001193125-06-191913:dex992.htm` — a **Horizon Lines,
Inc.** 8-K exhibit, "PRESS RELEASE DATED SEPTEMBER 12, 2006". **That is the
hypothesis working**: a tribal/ANC enterprise named inside *another filer's*
document, which is a counterparty disclosure Cedar cannot get any other way.

Already used by `code/105`, `142`, `148`; `logs/_HOSTLOCK_efts.sec.gov.json` exists
and is released. **What is missing is a systematic sweep of the spine against
`efts`, not access.** Hard limit to state every time: **EDGAR full-text search
covers 2001 onward only** — for anything earlier, `company.idx` (already used, see
`docs/ACCESS_TECHNIQUES.md` §3) is the route.

**Plan:** sweep all 1,489 spine canonical names + `entity_aliases.csv` through
`efts`; keep `(filer CIK, accession, our entity)`; join to `deals_classified.csv`
on date. Feeds the ten dated ownership changes in
`INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md` §5b — including
**DAWSON → LAUKOA**, where UEI and CAGE did not change and every identifier-keyed
join in the project is blind to it. **`NOT_SWEPT`, not `NOT_CHECKED`.**

---

# F — Wayback CDX · reachable; **the lock is stale and should be taken over**

- `archive.org` → **HTTP 200** (the parent-domain probe `ACCESS_TECHNIQUES.md`
  prescribes; a fast parent + a hanging child is the whole outage diagnosis).
- `http://web.archive.org/cdx/search/cdx?url=chenega.com/*&output=json&filter=mimetype:application/pdf&filter=statuscode:200&collapse=urlkey&limit=50`
  → **HTTP 200**, 6,703 bytes of JSON. **Enumeration works today via a plain HTTP
  client.** The brief's note that a prior agent found `web.archive.org` blocked
  *for WebFetch specifically* is consistent with this: **the block was in the
  transport, not the host.** Recorded so nobody re-derives it.
- **`logs/_HOSTLOCK_web.archive.org.json` is stale.** `active: true`, claimed
  **2026-08-07** by `code/95_wayback_az_gaming_status.py`, `pid: 7420`. **PID 7420
  is dead** (checked). Per `PULL_DISCIPLINE.md` rule 2 — *"a lock older than 6 hours
  with a dead PID may be taken over"* — it may be claimed. **Two queued items have
  been waiting nineteen days**: `code/104_build_wa_allocations.py` (WSGC Tribal
  Lottery System per-tribe terminal counts) and `code/119_build_digital_and_loyalty.py`.
  **I did not take it over** — I made one read-only probe and left it, because a
  fourth deep source was not in scope and a stale lock is someone's queued work,
  not free capacity. **Whoever picks up F drains that queue first.**

---

# G — probed, not sampled

| source | measured | verdict |
|---|---|---|
| **NSF award API** | `api.nsf.gov/services/v1/awards.json?keyword="Salish Kootenai College"` → **HTTP 200**, real TCUP award abstracts. No key. | `NOT_SWEPT`. Tribal Colleges and Universities Program awards are named, per-institution, and Cedar holds 37 TCUs. Cheap, clean, high match confidence. |
| **NIH RePORTER v2** | GET → **HTTP 405**; **POST** `/v2/projects/search` with `{"criteria":{"org_names":["SALISH KOOTENAI COLLEGE"]}}` → **HTTP 200, `total: 42`**. No key. | `NOT_SWEPT`. **A 405 on GET is not "the endpoint is wrong"** — same failure shape as the SAM 404. |
| **Census CFFR** | `www2.census.gov/programs-surveys/cffr/tables/` → **HTTP 200**, directory listing **1981–2010**, 30 year folders. Spot-checked: 1993 and 2010 hold `cff-report/`; 2005 holds `cffr-05.pdf`. | **`NOT_CHECKED` — contents.** Directory exists and covers the pre-FY2007 hole. Whether machine-readable per-county/per-program files sit under `cff-report/` was not opened. **This is the honest verdict; "no microdata" would be a guess.** Note `docs/PUBLISHED_LANDSCAPE_2026-08-26.md` records Census's FAADS page now 301s to usaspending.gov — CFFR is the adjacent artifact nobody has looked at. |
| **GSA eLibrary** | `gsaelibrary.gsa.gov/ElibMain/home.do` → **HTTP 200**, 50 KB. | `NOT_CHECKED`. Reachable; not queried. Schedule-holder rosters would name tribal/ANC 8(a) firms with contract vehicles. |
| **DOL Form 5500** | `askebsa.dol.gov/…/F_5500_2023_Latest.zip` → **301** → `www.askebsa.dol.gov/…`. Host alive. | `NOT_CHECKED` **deliberately.** `code/156_stage_form5500_gaming_employment.py` already staged this and `docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md` §4 says the merge waits on **two rulings** (`FORM5500_ACTIVE_PARTICIPANTS` absent from `cedar_domain.MeasurementType`; *"plan participants are not employees"*). Duplicating a staged pull would not have moved it. |
| **FPDS-NG ATOM** | `fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=VENDOR_FULL_NAME:"CHENEGA"` → **HTTP 200 and an EMPTY FEED** — a well-formed Atom document with zero `<entry>` elements, for a vendor holding thousands of federal contracts. | **Confirms `docs/SAM_EXTRACTION_PLAN.md` line 20: "Stop developing any FPDS-NG ATOM crawler."** Textbook *"a 200 that renders empty is not evidence of absence"* — and equally not evidence of presence. Whether another query shape works is `NOT_CHECKED` and **not worth checking**, because the plan of record already routes these years through SAM. |
| **FOIA reading rooms** | not probed | `NOT_CHECKED`. `code/136` already implements the doctrine (*"FOIA logs as a discovery index, not a request mechanism"*, 667 prior requests read). Nothing here would have added to it in the time available. |
| **USASpending Custom Award Data Download** | **not contacted** | Another agent owns `api.usaspending.gov`. Coordinated by not touching it. |

---

# WHAT WAS PRODUCED

**Scripts** (none writes to a shared table; all stage; all `.part`-then-rename;
all claim and release a host lock):

| script | stages |
|---|---|
| `code/219_probe_courtlistener_recap.py` | `sample` · `report` |
| `code/220_test_nobmf_eins_against_efile_index.py` | `profile` · `index` · `report` |
| `code/221_probe_regulations_gov_comments.py` | `sample` · `detail` |

**Staged outputs**

```
review/courtlistener_recap_sample_2026-08-26.csv              37 query rows
review/courtlistener_recap_dockets_2026-08-26.csv            304 docket rows
review/regulations_gov_comment_sample_2026-08-26.csv          33 query rows
review/regulations_gov_comment_hits_2026-08-26.csv           589 comment rows
review/regulations_gov_comment_detail_2026-08-26.csv          25 detail rows
review/schedule_i_nobmf_recipient_eins_2026-08-26.csv       6,217 rows
review/schedule_i_nobmf_eins_efile_verdict_2026-08-26.csv   6,217 rows + verdict
data/raw/external/untapped_2026-08-26/                       statute text, JSON,
                                                             PDFs, run state
```

**Host locks created and released:** `api.regulations.gov`,
`www.courtlistener.com`. Reused and released: `apps.irs.gov`.
**Left alone:** `web.archive.org` (stale, queued work), `api.usaspending.gov`,
`api.sam.gov`, NIGC, state regulators.

---

# THE ORDER TO DO THESE IN, BY WHAT THEY UNBLOCK

1. **DONE — ANCSA §7(h).** A recorded blocker, settled, verbatim, with URLs.
   Append to `docs/ANCSA_OWNERSHIP_RULING.md`; **do not edit the owner's ruling.**
2. **regulations.gov, docket-first.** It is the only source here with **no prior
   Cedar footprint at all**, and it supplies the one field the advocacy spec
   explicitly refused to author. Highest new-information density per request.
3. **The 424 e-filing EINs**, and the correction to the $4.92B framing. A published
   sentence is currently over-claiming; that is cheaper to fix now than after it
   ships.
4. **CourtListener token, then a verified-party sweep of the ANCSA and 8(a)
   cohorts.** Then read the free PDFs on verified dockets for the sealed gaming
   revenue — a document pass, not a search pass.
5. **EDGAR full-text sweep of the whole spine.** Feeds the ownership-change ledger,
   which is the thing that makes attribution year-aware.
6. NSF and NIH: two afternoons, clean matches, TCU-shaped.
7. Census CFFR: open one year folder before deciding anything about it.

---

# THINGS THAT WOULD HAVE BURNED A DAY, WRITTEN DOWN SO THEY DO NOT

- **A 200 is not presence.** ProPublica → `"Unknown Organization"`. FPDS-NG ATOM →
  an empty feed. Both HTTP 200.
- **A 403 on `/robots.txt` is a fact about that route, not about the host.**
  `courtlistener.com` and `www.regulations.gov` both 403 their robots.txt to an
  honest UA; `www.regulations.gov/robots.txt` fetched with a browser UA reads
  `User-agent: * / Disallow:` — **everything allowed.** Refusing to proceed on a
  403'd robots.txt would have killed source C for no reason.
- **A 302 to a 404 page is not a 404.** `apps.irs.gov` `index_2016.csv` and earlier.
- **A 405 on GET is not a wrong endpoint.** NIH RePORTER is POST-only.
- **`curl -I` and `Range` are both useless on `apps.irs.gov`** — 200 with no
  `Content-Length`, and `-r 0-2000` served all 77 MB.
- **The easy field is the wrong field.** regulations.gov's inline `comment` is
  *"See attached file(s)"* on the real tribal submissions and is full of text on the
  form letters.
- **A tribe name is a surname.** `Seminole v. Berkebile` is a prisoner civil-rights
  case. `Torres Martinez` is two common surnames. Verify on `party` /
  `organization`, never on a caption or a title.
- **The honest User-Agent is not always the served one.** `nrc.gov` refuses the
  browser string; `downloads.regulations.gov` refuses the honest one. **Measure per
  host and log which you used.**
