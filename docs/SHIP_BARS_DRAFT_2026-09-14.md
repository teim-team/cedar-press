# Ship bars — DRAFT for the owner's approval

*Written 2026-09-14. A draft: nothing ships under it until the owner approves it
(gate G06 in `code/1188_import_chatgpt_r7_business_register.py`). Every count is
measured on the frozen R7 package, before deduplication and before the hand
audit, so a count here is a candidate pool, never a release size.*

---

## 1. The owner's rulings this is built on (2026-09-14, as corrected)

1. R7 is aligned with, and kept as a **checksummed frozen source** until the
   CB-ID format, collisions, publication rules and ownership requirements are
   resolved.
2. The CB-ID format is **not** settled by "align"; see
   `docs/CB_ID_FORMAT_PROPOSAL_2026-09-14.md`.
3. **Business names are published, not withheld.** Sourced names ship under the
   new rule with their evidence. This does not exclude rows whose names were
   previously withheld.
4. **A blank review note means not reviewed, never approved** (in review spreadsheets the
   `YOUR_NOTES` column; for the R7 proposed pairs, the absence of a note in the notes file).
5. **State filings and certifications are authoritative for the facts they
   explicitly establish**, including ownership where the program or filing
   actually verifies ownership.
6. **Ship only what we are confident about, and add over time.**

## 2. Row states

Every row in a shipping dataset is exactly one of:

- **SHIP** — clears the dataset's bar below.
- **HOLD** — does not yet; carries a named reason and the next source to check.
- **DROP** — out of scope; carries a named reason.

Review status is separate and explicit: `REVIEWED_APPROVED`,
`REVIEWED_CHANGE_REQUESTED`, or blank = `NOT_REVIEWED`. A row is never treated
as approved because nobody wrote a note on it.

## 3. Evidence classes, and what each is authoritative for

Measured over R7's 17,279 active businesses by the **strongest** usable
observation each one carries (observations on hold for identity collision or
scope are not counted as support).

| class | what it is | authoritative for | R7 sources |
|---|---|---|---|
| **A1** state certification that reviews ownership and control | Florida CBE `K - Native American, Certified` (45); Massachusetts SDO certified `6-Native American` (7); Minnesota OSP approved TG list, category `I` (49); South Carolina SMBCC `07` (2) | Native ownership and control **as the program certified it**, on its dates and expiry. Not tribal enrollment or citizenship, and not which Native person or entity owns it | 103 businesses |
| **A2** state filing | Secretary of State records (Oregon, Colorado, Connecticut, New Mexico, Alaska) and tribal registries | legal existence, legal name, status, formation jurisdiction; ownership or charter **only where the filing states it** | 70 businesses |
| **A3** owner's annual or audited report | ANCSA corporation annual reports | the owner's own subsidiaries and ownership shares as reported, at the report date | 165 businesses |
| **B1** tribal TERO certification | Cherokee Nation TERO (807), Muscogee (163), MHA (130), EBCI (66), Colville (30), Tohono O'odham (18), others | **OWNER TO RULE.** A tribal government certifying Indian ownership is analogous to A1; proposed to rank with A1 once each program's criteria are recorded | 1,241 businesses |
| **B2** owner or tribal-government source | an owner's portfolio page, a tribe's own enterprise or business listing | that the owner or tribe names the business, and what relationship it states | 3,005 businesses |
| **C1** published Native business directory | DOI, Choctaw and Chickasaw business networks, Navajo NBOA, Native Business Center, Kuhikuhi, others | listing only. **Needs a per-host split first**: at least one host (Navajo NBOA source list) is a tribal certification program and belongs in B1 | 3,455 businesses |
| **D1** state-hosted self-report | North Carolina Commission of Indian Affairs directory, which disclaims accuracy | discovery only | 158 businesses |
| **D2** SBA profile self-attestation | `search.certifications.sba.gov` profiles | discovery only **as retained**: R7 kept no certification-program field, so an SBA-verified 8(a) or entity-owned certification cannot be told apart from self-attestation | 7,679 businesses |
| **D3** federal classification via a public Tableau dashboard | `public.tableau.com` | discovery only; provenance of the classification not established | 1,403 businesses |

**Two gaps these measurements expose, both fixable at source:**

- **D2 hides verified SBA certifications.** A re-pull that keeps each profile's
  certification programs would move every 8(a)-certified and entity-owned firm
  from discovery into an authoritative class. 7,679 businesses rest on D2 alone.
- **C1 mixes certification programs with listings.** Classify by host before
  anything in C1 ships.

## 4. Draft bar: Cedar NEED

A NEED row **ships** when all of these hold:

1. It carries the business name as the source published it.
2. `owner_cedar_uid` resolves to a Cedar entity, and no unresolved proposed equivalence pair or
   identifier conflict involves that entity.
3. Its ownership evidence is A3, an A2 filing that states the ownership, a B2
   page published by the owner or the tribe naming the business, or an A1/B1
   certification with an entity-owned class.
4. A joint venture, majority or minority stake is labelled as such and never
   shown as wholly owned.
5. Every Cedar id on the row resolves, and `CE-` and `CB-` never mix.
6. The hand audit (§7) passes.

Measured candidate pool (NEED rows with an owner resolved): **A3 126 · A2 32 ·
B2 546 = 704**, before deduplication and audit.

Held, with reasons: B2 without a resolved owner **1,788** (research the owner);
SBA self-attestation **3,322** and Tableau classification **377** (re-pull or
corroborate); C1 without owner **457**; A2/A3 without owner **19**.

## 5. Draft bar: Native-owned (individually owned) businesses

A row **ships** when:

1. It carries the business name as published. Names are not withheld (ruling
   3). Personal data about the owner — a person's name, home address, personal
   contact — is not published as a business field.
2. Its Native-ownership evidence is **A1**, or **B1** if the owner so rules, or
   a **B2** tribal-government listing that states Native ownership.
3. It is not also an entity-owned business (routing between Individual and
   NEED is resolved first).
4. The hand audit (§7) passes.

Measured candidate pool: **A1 103**; **B1 1,233** if approved; **B2 649**. Up to
**1,985** before deduplication and audit.

Held: C1 **2,987** (until classified by host), SBA self-attestation **4,307**,
Tableau classification **998**, North Carolina self-report **157**.

**Open question for the owner:** for a firm whose legal name is a person's name,
do its UEI and CAGE publish? The writer currently withholds them on the reasoning
that SAM resolves a UEI to that person's address.

## 6. Proposed entity-business equivalence pairs (the ANCSA corporations)

R7 proposes 83 entity-business equivalence pairs: an ANCSA corporation's entity
id paired with a business record. They are **proposals, not equivalences**, and
**every pair is UNRESOLVED.** Cedar's identifier ledger records *attribution*
(an identifier attributed to the Native entity that owns, controls or is parent
to its registrant). That is a semantic limitation of the ledger: no ledger field
records a same-legal-object determination, so no ledger row by itself can
establish an equivalence, and generated evidence never resolves a pair.

A pair resolves only when the owner records `CONFIRMED_SAME_LEGAL_OBJECT` or
`REFUSED_NOT_SAME_LEGAL_OBJECT` in the decisions file (schema v2, validated by
`code/1188_import_chatgpt_r7_business_register.py`). Each decision names the
`evidence_fingerprint` of the pair as reviewed: the entity and business rows,
the R7 proposal row, the identifiers, every supporting ledger row and each URL's
class. If any of that changes, the decision becomes STALE, is kept as history
and no longer counts. A later decision supersedes an earlier one; neither is
deleted. Decisions dated in the future are rejected.

Generated evidence, measured 2026-09-14 with
`py -3 code/1188_import_chatgpt_r7_business_register.py`:

| generated assessment | pairs | meaning |
|---|---:|---|
| WEAK_OR_INSUFFICIENT_EVIDENCE_ONLY | 60 | only tier B/C, quarantined, excluded-on-other-rows, missing, invalid, homepage-only or downgraded-URL attribution rows |
| IDENTIFIER_NOT_IN_LEDGER | 17 | the business's UEI/CAGE is not in the ledger |
| NO_IDENTIFIER_ON_BUSINESS | 3 | no UEI or CAGE on the business |
| CONFLICT_ATTRIBUTED_TO_OTHER_ENTITY | 2 | a tier A/B, unquarantined row attributes the identifier to a different entity (St. George Tanaq; Ukpeagvik Inupiat, whose CAGE is attributed to the Inupiat Community of the Arctic Slope) |
| ATTRIBUTION_REFUTED_OR_EXCLUDED | 1 | Shee Atika: tier X with an exclusion ruling |
| CANDIDATE_EVIDENCE_REGISTRANT_NAME_MATCHES_UNRESOLVED | **0** | would require a tier A, unquarantined, unexcluded row with a valid record-level URL whose registrant legal name equals the entity |

**Withdrawn claims.** An earlier version promoted tier A/B ledger bindings to an
automatic confirmation ("37 confirmed"); all 37 are now weak or insufficient.
A later version called Leisnoi, Inc. clean direct evidence; its tier A row's
evidence value is literally `https://` with no host, which is not a URL, and its
other row cites only the SBA search homepage. Leisnoi is weak or insufficient.

**The 78 ledger rows behind these pairs** (every row is an ownership or
attribution binding):

| measure | count |
|---|---|
| identifier type | CAGE 42, UEI 36 |
| attribution method | need_v6 33, agent_research_one_leg 20, cluster_v3 12, cross_dataset_propagation:contracting 4, agent_research_two_leg 3, elijah_ruling_redirect 3, unmatched 3 |
| confidence tier | B 53, C 20, A 3, X 2 |
| quarantined method | 46 (disposition KEEP 41, HOLD 3, WITHDRAW 2); not quarantined 32 |
| excluded (exclusion ruling) | 1 |
| evidence URL class (structure only; nothing fetched) | site or search homepage only 38, missing 36, downgraded by integrity note 2, invalid 1, valid record-level URL 1 |
| attributed to the paired entity / to a different entity | 45 / 33 |
| registrant legal name equals the paired entity | 41 |
| tier A + valid record-level URL + registrant name matches | **0** |

**What can and cannot support a decision.** Can: the owner's own check at
cage.dla.mil, sam.gov or the Alaska corporations search, recorded with its basis.
Cannot, by itself: any ledger row; tier B/C, quarantined, withdrawn, held,
refuted or excluded rows; missing, invalid, local-path or homepage-only URLs; and
any common ownership, parentage, affiliation, address or attributed UEI/CAGE.

The queue is the current audit bundle's `queue.csv`, found through
`docs/imports/r7_audit/CURRENT.json`. It is a generated, immutable snapshot: the
complete supporting ledger rows, per-row URL class, relationship meaning, evidence
fingerprint, the exact lookup to run, and read-only snapshots of the owner's
decisions and notes. Nothing inside a bundle is edited; the tool reports any edit
as corruption. Notes are written only in docs/imports/R7_OWNER_NOTES.json
(commentary, never a gate) and decisions only in docs/imports/R7_OWNER_DECISIONS.json.
A pair with no CURRENT decision is UNRESOLVED; a pair with no note has not been
commented on.

## 7. The hand audit, every dataset, every release

Before a dataset ships, at least 50 SHIP rows drawn at random, stratified by
evidence class, are opened at their cited URL and checked field by field: name,
the ownership fact, owner entity, dates. Any error sends its **rule** back for a
fix and the sample is redrawn; the row is not patched by hand. The sample, the
result and the reviewer are recorded with the release.

## 8. What each gate needs to open

| gate | opens when |
|---|---|
| G03 proposed equivalence pairs | every one of the 83 proposed pairs carries a CURRENT owner disposition (confirmed or refused). G03 checks dispositions only; correcting the source-ledger conflicts found along the way is follow-up work recorded in the queue, not a G03 condition |
| G04 CB-ID format | the owner approves a format (`docs/CB_ID_FORMAT_PROPOSAL_2026-09-14.md`) |
| G05 publication | the owner approves publishing business names AND the live policy function `may_publish_individual_native_field` in `code/cedar_domain.py` returns publish. G05 checks that function, not an export; an export fixture is still owed |
| G06 ship bars | the owner approves this document, including the B1 and person-named-UEI questions |

A gate opens only when the decision is recorded in the decisions file, in the
schema `code/1188` validates, and only while it is CURRENT. Integrity passing is never
approval; `freeze` exiting 0 means audit artifacts were written, not approval; and approval
imports nothing: the import is a separate reviewed change. Once approved, these
bars fold into `docs/SHIPPING_RUNBOOK.md` and the applicable dataset contracts,
and this draft is retired.
