# Cedar Press — external design review packet

*Paste this whole document into another model (ChatGPT, etc.) and ask it to
find flaws. It is self-contained: no repository access is needed. Everything
here is real — the algorithms are the shipped code's logic, the numbers are
measured, and the weaknesses section is honest. Generated 2026-08-29; see docs/EXTERNAL_REVIEW_RESPONSE.md for what a review of this packet found and what changed as a result.*

---

## Your task as reviewer

You are reviewing the data architecture of **Cedar Press**, a commercial data
product about Native American / Alaska Native / Native Hawaiian entities:
tribal governments, ANCSA corporations, tribal enterprises, Native nonprofits,
and their federal funding, contracting, gaming, lobbying and deals. Buyers
join our tables on our entity IDs, so identity errors become their errors.

**Be adversarial.** Do not summarize the design back. For each numbered
section, try to construct a concrete failure: an input, sequence of events, or
edge case where the stated mechanism gives a wrong answer, silently loses
data, or lets two agents disagree without detection. Rank your findings by
severity. If a mechanism is sound, say so in one line and move on.

---

## 1. The identity system

**Entity classes (17):** federally recognized tribes (`TRBF`), state-recognized
(`TRBS`), Alaska Native village governments (`AKNF`), ANCSA village
corporations (`ANVC`), ANCSA regional corporations (`ANRC`), Native Hawaiian
Organizations (`NHO`), intertribal orgs (`ITO`), tribal colleges (`TCU`),
Native CDFIs (`CDFI`), urban Indian orgs (`UIO`), BIE schools (`BIE`),
constituency entities — bands under one recognized tribe (`CNSF`/`CNSS`),
self-governance consortia (`SGVF`), individually Native-owned businesses
(`CEDAR-ENT-`), and others.

**Two-layer ID:**
- A human-readable *handle*: class prefix + name stem, e.g. `TRBF-MIKMAQ-00`.
  Handles can change if an entity is reclassified.
- A permanent *uid*: `CE-XXXXX-CC` — 5 payload characters in Crockford base32
  (no I/L/O/U), plus **two check characters** computed with independent
  weight vectors:

```python
B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"   # Crockford, 32 chars
_W1 = (2, 3, 4, 5, 6)      # linear positional weights
_W2 = (1, 4, 9, 16, 25)    # quadratic - chosen for a different null space

def check_chars(payload):          # payload = 5 chars from B32
    v = [B32.index(c) for c in payload]
    a = sum(w * x for w, x in zip(_W1, v)) % 32
    b = sum(w * x for w, x in zip(_W2, v)) % 32
    return B32[a] + B32[b]
```

We stress-tested: 100% detection of all single-character substitutions and
100% of all adjacent transpositions across the full payload space. The uid is
minted once, never re-minted; reclassification changes the handle, never the
uid. 1,536 entities minted; re-running the mint produces a byte-identical
register (proven by digest).

**Hub model:** the entity (hub) is the sovereign/organization. Registrations
(UEI/CAGE/EIN), facilities, and properties are *sub-hubs*. A property of a
sub-hub is never a property of the hub — a subsidiary's Virginia mailing
address does not move an Alaska village to Virginia. Hierarchy (parent,
ultimate owner) is a *relationship*, never part of identity.

**Questions for you:**
1. Does the two-vector mod-32 check scheme have a blind spot we missed —
   e.g., twin errors (`AA`→`BB`), jump transpositions (`ABC`→`CBA`), or
   errors involving the check characters themselves?
2. Is 5 base32 chars (≈33.5M ids) with sequential minting a problem for a
   sold product (enumerability, growth)?
3. Any failure mode in "handle mutable, uid permanent" when a buyer has
   already joined on handles?

## 2. Domain rules that guard entity resolution

These are encoded as hard guards in the matcher; each earned its place from a
real error:

- **Gov-class restriction:** "Native Village of Elim" (a government) must
  never resolve to "Elim Native Corporation" (an ANCSA business). A
  shortest-name or containment matcher picks the corporation. Government
  filings may only match government-class entities.
- **State tokens are never stripped:** Oneida Nation (NY) vs Oneida Nation
  (WI) are different sovereigns; 2,208 of 2,210 transaction rows plus $890M
  went to WI — the money's `recipient_state_code` decides, not the name.
- **Constituency entities receive money in their own name:** "ELKO BAND
  COUNCIL" is a band of the Te-Moak Tribe; excluding band-level entities left
  $1.5B "unmatched."
- **Renames:** filings predate renames (San Manuel → Yuhaaviatam of San
  Manuel Nation; Aroostook Micmac Council → Mi'kmaq Nation). The alias layer
  carries history; a spine "gap" is usually an alias gap.
- **A place named for a tribe is not the tribe:** "TUSCARAWAS METROPOLITAN
  HOUSING" is an Ohio county housing authority.
- **Same people, two sovereigns:** Ho-Chunk Nation (WI) vs Winnebago Tribe of
  Nebraska. Ho-Chunk, Inc. is the *Nebraska* tribe's company.
- **Apostrophe folding:** ʻokina (U+02BB), right quote, straight apostrophe,
  and nothing are one match key (Suhʼdutsing/Suh'dutsing/Suhdutsing), but the
  stored canonical name keeps correct marks.

**Questions:** 4. What resolution edge cases in this domain do these rules
still not cover? 5. Is deciding Oneida NY-vs-WI by the money's state code
circular anywhere (e.g., a tribe's enterprise registered out of state)?

## 3. The assertion layer (facts stop being overwritten)

Previously each table had one `state` column etc.; a second writer destroyed
the first answer and its reason. Now:

- `cedar_assertions.csv` — append-only. One row per (subject uid, predicate,
  object, source, polarity). 29,726 rows. Polarity can be `deny`: 332
  refutations ("this UEI is NOT this tribe") survive as first-class rows.
- `cedar_resolved_facts.csv` — computed. The value we stand behind + WHICH
  RULE decided it. 29,363 rows.
- `cedar_fact_conflicts.csv` — every losing value kept, never deleted.
- Assertion IDs are content-addressed (sha1 of the claim), so a re-run is
  byte-identical and diffable in git.

**Evidence lineage.** Every source declares a `lineage_root_id`; roots form a
tree via `derives_from`; two assertions corroborate only if their root
ancestry sets are **disjoint**. Examples: `LR_BIA_DIRECTORY` and `LR_CICD`
(a legacy compiled dataset) both derive from `LR_FEDERAL_REGISTER`, so "CICD
agrees with the FR" is one fact, not two. `LR_USASPENDING` derives from
`LR_SAM` (recipient fields are copied from the registration). Three roots are
flagged `independence_is_unverified` and can never vote in corroboration:
agent web research (we don't know what page the agent read — it may echo the
FR), the legacy compiled dataset, and "no provenance recorded" (11,676
assertions, counted rather than hidden).

**Resolution rules, in precedence order:**

| # | rule | effect |
|---|---|---|
| R00 | MULTI_VALUED_NO_CONTEST | declared multi-valued predicates (identifiers, aliases, registration states): distinct values never compete; only a deny removes one |
| R01 | DENY_VETO | a deny at ≥ the affirm's tier removes that value |
| R02 | AUTHORITY | a source declared `authority_for` this predicate wins outright (kept narrow: the Federal Register decides recognition + official name, nothing else) |
| R03 | HUMAN_OVER_MACHINE | an owner ruling beats any machine source |
| R04 | TIER | A > B > C, after capping at the source's declared ceiling |
| R05 | CORROBORATION | more *independent* lineage families wins |
| R06 | RECENCY | later verified_date wins — deliberately near-last so a fresh guess can't beat an old federal record |
| R07 | DETERMINISTIC_TIEBREAK | lowest sha1 wins, flagged `decided_by_coinflip` |

**Nine verify invariants** run on every build; three notable: I3 recomputes
every assertion id (reproducibility); I6 recomputes independent-family counts
from scratch (circular-corroboration check); I8 proves every losing value
reached the conflict table (nothing silently dropped).

**Bugs this layer already caught in its own first week** (kept in the docs as
evidence the invariants work): (a) the first resolver treated identifiers as
single-valued — one tribe holds 90 real UEIs, and it filed 89 true facts as
"losers" (6,327 fake conflicts); (b) when the tiebreak reordered candidates,
`ranked[1:]` filed the *winner* as a losing value and dropped the real loser
— caught by I8; (c) SAM registration addresses were briefly asserted as
`entity.state`, relocating Alaska villages to Virginia/Florida — fixed by
re-pointing the predicate to `entity.registration_state` (multi-valued,
about the registration, not the entity).

**Questions:** 6. Attack the rule ordering — construct a case where this
precedence gives a wrong resolved value. 7. Attack ancestry-disjoint
corroboration — can two dependent sources still count as independent (e.g.,
both scraped the same upstream that neither declares)? Is a tree even the
right shape, vs a DAG? 8. Is `deny at ≥ tier` the right veto condition?
9. What belongs in MULTI_VALUED that we likely missed, and what's the cost of
misclassifying a predicate's cardinality in each direction?

## 4. Ownership: connections, not hierarchy

Registrants declare immediate/highest-level owners in SAM (FAR 4.18); FPDS
and USAspending transaction files republish these parent UEIs publicly. We
harvest **edges** (literal declared child→parent pairs, 2,901 of them) and
refuse to write trees, because the declared "highest-level owner" is often
the highest *incorporated* owner (Ho-Chunk, Inc., not the Winnebago Tribe).
The last hop — holding company → tribe — comes only from our own researched
spine. Self-edges dropped-and-counted; three "GOVERNMENT OF THE UNITED
STATES" roll-up parents flagged as ownership dead-ends. New subsidiary UEIs
become tier-B *candidates* attributed via the declared connection, never new
entities ("Arctic Slope Federal Services" is a registration owned by ASRC,
not a Native entity).

**Questions:** 10. Failure modes of trusting self-declared parent UEIs even
as mere "connections" (stale registrations, shells, circular declarations)?
11. Anything wrong with "candidates at tier B via declared connection"?

## 5. Gates and process (multi-agent hygiene)

Many AI agent sessions work on this repo; the defenses:

- **Ratcheted regression gate** (script 62): ~60 metrics; MUST_BE_ZERO for
  defect classes, MUST_NOT_RISE for lint counts, floors re-recorded only
  while green. Exit 1 is stop-work by standing rule.
- **Named defect classes** (script 293): e.g. class2c "a drop counter that
  never names what it dropped", class4 "a per-unit budget that can truncate
  and still mark COMPLETE", class6 "one table with both a full-rebuild writer
  and an in-place enricher and no declared ordering", class7 "an id minted
  from position/process rather than content". Waivers require an inline
  reason and are counted, never hidden.
- **NEVER_RUN list:** four scripts whose full rebuild destroys later in-place
  work (with the historical loss documented); an awkward override token
  exists.
- **Dataset contracts** (script 512): per-collection machine-readable
  contracts — tables, status, join keys, rebuilder, enrichers, grain
  (declared only where a human stated it; otherwise recorded as UNSTATED,
  never guessed). Derived from the systems that own each fact so it can't
  drift. First run found 28 shippable tables owned by no collection.
- **Release gate:** `ship --execute` refuses a dirty git tree and stamps the
  release commit. Data is untracked (46 GB); data inputs are attested by
  run-manifest logical checksums instead.
- **Handoffs** (script 513): a claim of completed work is a row born
  UNVERIFIED, carrying the commit hash and `verify_commands` whose exit 0
  constitutes proof. Verification RE-RUNS the commands; self-verification is
  refused (claimant ≠ verifier); a disproven claim gates as stop-work.

**Questions:** 12. Where does this process still let two agents silently
disagree or clobber each other? 13. The release can pin code (commit) but
not data (checksums live in run manifests) — what's the weakest link in
claiming a release is "replayable"? 14. Is "verifier must be a different
session id" meaningfully independent when both are AI sessions that may share
blind spots?

## 6. Honest current weaknesses (do not soften these)

- **Zero single-valued facts have a second independent source.** Across
  8,975 single-valued facts: 0 have two sources. **The disagreement rate is
  therefore UNDEFINED, not zero** - no two sources observe the same fact, so
  there is nothing to disagree. Exactly **2** facts have >1 independent
  evidence family (an earlier "38" counted multi-valued registration facts
  collapsed onto the entity, which was a grain error, not corroboration). The arbitration
  machinery is proven but idle; the FR roster harvest added 565 matches and 0
  corroborations — correctly, because a copy of the FR inside our spine is
  the same evidence family.
- **11,676 of 29,726 assertions carry no recorded provenance**
  (`unattributed_legacy`) — capped at tier C, excluded from corroboration.
- 1,279 of 1,536 spine rows had no verification route when measured; the
  assertion layer counts this rather than fixes it.
- Two declared authorities never actually assert (flagged by our own I7).
- `entity.is_federally_recognized` has no negative case: the roster asserts
  "yes" for members; nothing asserts "no" for non-members.
- Release replay has never been demonstrated end-to-end.
- Inherited data quality: we found a shipped table whose `state` column held
  *that row's own UEI* in 59% of rows (inherited from an upstream extract);
  fixed with a validator now shared by builder and fixer.

**Questions:** 15. Given a small budget (say 40 hours of agent time), rank
what you'd fix first from this list and why. 16. What risk in this design is
*not* on this list?

## 7. Constraints you should respect in your answers

- Proprietary third-party IDs (D-U-N-S, commercial gaming datasets) may be
  held internally but never shipped; don't propose designs that ship them.
- No authoritative federal roster of Native Hawaiian Organizations exists;
  the NHO universe is genuinely open — designs must tolerate that.
- Alaska is excluded from some sibling research projects but IS in scope for
  Cedar Press; village government vs village corporation confusion is the
  single most dangerous class of error in this domain.
- The methodology must be replicable by a human without AI tooling
  (collaborator requirement) — manual verification steps are a feature.

**Deliver your review as:** (1) ranked findings, each with a concrete failure
scenario; (2) one-line "sound" acknowledgments where applicable; (3) answers
to the 16 numbered questions; (4) anything you'd add to section 6.
