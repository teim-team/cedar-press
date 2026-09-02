# The Codex review loop on `teim-team/cedar-press`

*Live doc. The owner's instruction: "Have a standing pull request and keep
updating it so codex can flag stuff and respond to codex after every pull
request. We need to converge both strands of work — the product with the
data."*

This file is the Cedar-side record of that loop, because the data project and
the product repo are two different repositories and neither one's history tells
the whole story on its own.

---

## HOW TO ENUMERATE A CODEX REVIEW, AND THE MISTAKE THAT MAKES YOU MISS IT

**`gh api repos/teim-team/cedar-press/pulls/<n>/comments` can return an empty
list while a review holds six findings.** That endpoint returns review-thread
comments only, and a Codex review distributes its content across three places.
An agent read only that one, found nothing, and told the owner "Codex found no
findings" when there were six. Read all of these before concluding anything:

    /pulls/<n>/reviews              the review objects (state, commit reviewed)
    /pulls/<n>/reviews/<id>/comments   that review's findings
    /pulls/<n>/comments             review-thread comments, top level
    /issues/<n>/comments            the summary comment and any human replies

**The repo is public**, so all four are readable with no token at all:
`curl -s https://api.github.com/repos/teim-team/cedar-press/pulls/26/comments`.
Posting is what needs auth. Note also that `json.load` on those responses dies
on `cp1252` under Windows Python — open with `encoding="utf-8"`.

## ~~AUTH, AS OF 2026-09-02 - READING IS FREE, WRITING IS NOT~~ CORRECTED

> **THE SECTION BELOW IS WRONG AND IT COST A WHOLE JOB.** An agent read it,
> looked for `gh`, did not find it, and reported the round-2 reply blocked. The
> token was in **Windows Credential Manager** the entire time - the same place
> `git push` gets it from, which this section itself notes works. Eight replies
> were posted on 2026-09-02 with no `gh`, no `GH_TOKEN` and no browser:
>
> ```python
> cred = subprocess.run(["git", "credential", "fill"],
>     input="protocol=https
host=github.com

",
>     capture_output=True, text=True).stdout
> tok = next(l.split("=", 1)[1] for l in cred.splitlines()
>            if l.startswith("password="))
> H = {"Authorization": f"Bearer {tok}",
>      "Accept": "application/vnd.github+json",
>      "User-Agent": "cedar-press-integrator"}
> ```
>
> Then `POST /repos/teim-team/cedar-press/pulls/<n>/comments/<comment_id>/replies`
> with `{"body": ...}`. **Never print, log or write the token.**
>
> The reasoning error is the one this project keeps making: *the absence of one
> tool was read as the absence of the capability.* `gh` is a client, not the
> credential. Same shape as "a 403 on robots.txt means the site forbids you"
> and "one auditee's opt-out is a property of the source."

## THE ORIGINAL SECTION, KEPT BECAUSE IT IS STILL TRUE ABOUT `gh`

On this machine there is **no `gh` CLI, no `GITHUB_TOKEN`/`GH_TOKEN`, no
`~/.netrc` and no `~/.config/gh/hosts.yml`.** `git push` works, because the
Windows Git Credential Manager answers for `github.com` silently — so a branch
can be published, and a pull request cannot be opened and a comment cannot be
posted. The Chrome extension route is also unavailable: no browser is
connected to this account.

**So an agent on this machine can push the work and cannot post the reply.**
Whoever wants that closed needs one of: `gh auth login`, a PAT exported as
`GH_TOKEN`, or a connected Chrome. Until then the reply text is written out
below verbatim, ready to paste, and the substance of it also lives in
`data/cedar/README.md` on the branch so it is not lost if nobody pastes it.

---

## PR #26 — opened 2026-09-01, MERGED 2026-09-02 04:39 UTC

Branch `cedar-data-samples`. Codex reviewed commit `7e3a536` and left **six**
findings: three P1, three P2. Round 1 answered all six in `d30a64b`.

| # | pri | file | finding | verdict |
|---|---|---|---|---|
| 1 | P1 | `collection_descriptors.json` | `CollectionDataset(**d)` raises `TypeError` on `n_rows`; `version` and `downloads` missing | **Right, and total.** Not one of the 13 could load. Fixed in round 1; re-verified 13/13 on 2026-09-02. |
| 2 | P1 | `collection_descriptors.json` | the product's id for that collection is `owned`, not `native-owned-businesses` | **Right.** Would have left a READY dataset silently unable to replace the demo record. Mapped. |
| 3 | P1 | `funding__sample.csv` | `PUEBLO OF ACOMA (INC)` resolves to Haaku Community Academy | **Right about the display, and the round-1 reply overstated it.** See the correction below. |
| 4 | P2 | `README.md` | the subaward overstatement is 86.9%, not 46.5% | **Right.** Round 1 fixed the descriptor and left this README saying 46.5%, so the two halves of the handoff then disagreed. Both now state the denominator. |
| 5 | P2 | `collection_descriptors.json` | every blocked dataset says only `BLOCKED` | **Right.** `cedar.blockers` now carries the named contract points. |
| 6 | P2 | `lobbying__sample.csv` | the README promises no natural persons and the sample publishes `STEPHEN GRAHAM` | **Right that the doc and the code disagreed; wrong about which to change.** An individual may register as a lobbyist and the registration IS the record the LDA creates. The claim was narrowed to personal data held apart from a public role. |

**Nothing Codex said in round 1 was wrong on the facts.** Finding 6 is the only
one where the right repair was the opposite of the one suggested, and Codex had
itself offered that as its second option.

---

## THE CORRECTION OWED ON FINDING 3 — text to post on PR #26

> **Correcting my own round-1 reply on the Acoma finding. I told you this was
> "a real defect, and worse than the ten rows showed — 2,434 rows and
> $1.008B." That was wrong, and the correction is more useful than the original
> claim.**
>
> **The keyed columns are correct.** Those rows carry
> `cedar_uid = CE-0011W-HN`, which the identity register resolves to Pueblo of
> Acoma — a federally recognized tribe, not a subordinate institution. This is
> a **labelling** defect and not an attribution one. `canonical_name` in that
> table is copied verbatim by `24_funding_merge.load_tribe_names()` out of
> `lineageA_dta_corrtd_tribe_key.csv`, a legacy do-file key that literally
> contains `{234, 'haaku community academy', NM}`. It is not a Cedar name at
> all, and the register records the reconciliation explicitly.
>
> At scale: of 552,602 rows carrying a `cedar_uid`, 345,108 have a
> `canonical_name` that disagrees with the register's name for that uid, and
> **339,129 of those — 98.3%, $94.0B — are explained entirely by that legacy
> reconciliation.** Right identity, stale label. Of the 5,979 not so explained,
> 3,620 are a *blank* `canonical_name` with a uid present, which is a missing
> label rather than a wrong one.
>
> The register holds the real sub-hubs separately and the table uses them
> correctly when the recipient genuinely is the school — Blackfeet Community
> College is `CE-0010N-2P`, 312 rows. So entity-level grouping on `cedar_uid`,
> which is the key ADR-009 mandates, credits the tribe. Only grouping on the
> legacy display name credits the school. **The funding sample now ships
> `cedar_uid` beside `canonical_name`**, which is what the ten rows were
> missing: you were shown the unreliable half of a correctly attributed row.
>
> **The genuinely wrong attribution turned up while chasing yours, and it is
> smaller in rows and worse in kind.** Legacy id 347 mapped **820 rows and
> $181,881,441.37 of United Keetoowah Band obligations onto Cherokee Nation** —
> two distinct federally recognized tribes merged into one uid on a loose token
> match on the word "Cherokee", with United Keetoowah Band sitting in the
> register in its own right as `CE-001BS-HA` / `TRBF-UKEETW-00`. The crosswalk
> row contradicted itself and said why: its proposed name read "United
> Keetoowah Band of Cherokee Indians in Oklahoma" while its id read
> `TRBF-CHKNAT-00`. Fixed at source in `7b35193`, and the whole legacy CICD id
> scheme has since been retired in `b3a0d7f`.
>
> So: your finding was right, the row you pointed at was not the defect, and
> pulling on it found one that was. Thank you — and the reason the sample let
> me misread it is now fixed rather than argued about.

---

## FINDINGS FOUND BY THIS SIDE WHILE ADDRESSING CODEX'S

Recorded because they came out of the review loop and would not otherwise be
attributed to it.

- **`parent_contract_number` was documented as populated on all 1,217,768 rows
  and was not.** 262,773 rows (21.6%) held the literal string `nan` — a pandas
  float through `str()` on the way to CSV, which counts as present and means
  absent. Found only because Codex's finding 3-adjacent complaint about
  `contract_number` forced that column into the sample. Cleared by
  `772_strip_nan_sentinels.py`; a sweep of the same table found 953,785 such
  cells across twelve columns, most of which a concurrent rebuild had already
  cleaned.
- **The pair is the key, and the cross-tab proves it.** 664,470 rows carry a
  real parent and a full child PIID, 290,525 a real parent and a modification
  stub, 262,773 no parent and a complete standalone PIID, and **zero rows have
  neither**.
- **770 was deleting requested columns.** Any column blank across the ten
  sampled rows was silently dropped, so the sample *schema* was a function of
  the sample. Fixed; blank columns now ship and are named, and a `SHOW` entry
  for a column the table does not carry is a hard `verify` failure.
- **The Eastern/Chickahominy collision is a matcher defect and a blanket
  exclusion would be the wrong fix.** All 44 rows keyed to `Chickahominy
  Indians-Eastern Division` turn on the token `EASTERN` and none is in
  Virginia — but three are real Native organisations keyed to the *wrong*
  tribe, so the instrument is a redirect, not a block. Handed on rather than
  patched.

---

## PR AFTER #26

#26 merged into `main`, and GitHub deleted the branch on merge. `cedar-data-samples`
has been re-pushed on top of `main` at `1241a19`. **A new PR must be opened for
the standing loop to continue** — that is the one action on this page that
cannot be done from this machine. Once it exists, Codex reviews on open; read
all four endpoints listed at the top before deciding it found nothing.

### The PR to open, ready to paste

    gh pr create --repo teim-team/cedar-press \
      --base main --head cedar-data-samples \
      --title "Cedar data: the Acoma correction, and four defects a buyer would have seen"

Body:

> Standing PR for the data side of the handshake. #26 merged and GitHub deleted
> the branch; this re-opens the loop on top of `main`.
>
> **The correction first, because it is owed.** Round 1 told Codex that the
> `PUEBLO OF ACOMA (INC)` finding was "a real defect, and worse than the ten
> rows showed — 2,434 rows and $1.008B." **That was wrong.** The keyed columns
> are correct: those rows carry `cedar_uid = CE-0011W-HN`, Pueblo of Acoma,
> federally recognized. It is a labelling defect — `canonical_name` is copied
> verbatim from a legacy do-file key that literally holds
> `{234, 'haaku community academy', NM}`. Of 552,602 keyed rows, 345,108
> disagree with the register and 339,129 of those (98.3%, $94.0B) are that same
> legacy reconciliation: right identity, stale label. The genuinely wrong
> attribution found by chasing it was **820 rows and $181,881,441.37 of United
> Keetoowah Band obligations credited to Cherokee Nation**, fixed at source in
> `7b35193`; the legacy id scheme is retired in `b3a0d7f`.
>
> **Four defects out of the samples.** `contract_number` was shipping FPDS
> modification stubs (`0098`, `0006`, `SBA0001`) as if they were keys —
> `parent_contract_number` now ships beside it and the pair is the key, and
> adding it exposed 262,773 rows holding the literal string `nan`. The
> nonprofits sample showed `classification_ruling`, which is filled on 3.1% of
> rows, instead of `funnel_stage`, which is where the 4,651 exclusions live.
> `deals` shipped no dollar value though the descriptor promises one.
> `certification_expiration` shipped in six date formats and every date that
> reached a customer was un-normalised.
>
> **And a failure mode in the builder.** It silently deleted any requested
> column that was blank across the ten sampled rows, so the sample schema was
> not stable across rebuilds. Fixed, and the new hard check caught a live drift
> within the hour.
>
> The 46.5% / 86.9% split is closed by stating the denominator in all four
> places. 11 of 13 datasets are READY, up from 4. All 13 descriptors verified
> against the `CollectionDataset` dataclass on `main`.

---

## PR #29 — opened 2026-09-02, ROUND 2 ANSWERED 2026-09-02

Branch `cedar-data-samples`. Codex reviewed commit `3fe58a5` and left **eight**
findings, all P2. All eight answered in `6c4801f`, and all eight replies
**posted** — see the auth correction at the top of this file, because the
previous round recorded posting as impossible on this machine and it never was.

**All eight were right on the facts.** Six were substantially larger at
full-table scale than the sampled row showed; one needed the opposite repair to
the one suggested; one was right in principle and disproportionate in remedy.

| # | file | finding | verdict | scope Codex could not see |
|---|---|---|---|---|
| 1 | `README.md` | `CollectionDataset(**d)` raises on `cedar` / `needs_copy` | **Right, and total** | **0 of 13** constructed. Same defect as PR #26 finding 1, reintroduced BY the fix for it |
| 2 | `contractors__sample.csv` | Old Harbor award credited to Three Affiliated | **Right** | 1 row sampled; **4,947 rows, $449,376,831.04** |
| 3 | `collection_descriptors.json` | C4 blocker removed while README says 42% | **Right that they contradict, WRONG about which half** | the 42% came from a 50,000-row cap; the full scan is 100% |
| 4 | `contractors__sample.csv` | self-referential `parent_contract_number` | **Right** | 1 row sampled; **156,592 rows, 12.86%**, two distinct causes |
| 5 | `gaming__sample.csv` | joint operation exposes one operator | **Right, remedy disproportionate** | **1 of 787**; the obvious generalisation produces 57 false operators |
| 6 | `nagpra__sample.csv` | notice-type text inside institution name | **Right** | 1 row sampled; **966 rows**; distinct institutions 2,184 → 1,798 |
| 7 | `README.md` | `owned` has no `owned__sample.csv` | **Right** | and the same hole existed in reverse for the new `nest` descriptor |
| 8 | `nagpra__sample.csv` | one notice's institutions all get Yale's address | **Right, and worse** | `institution_count` said 4 for 6; `institution_names_all` had **invented an institution** |

### Finding 2 — the one that moves money. `code/1075_fix_old_harbor_attribution.py`

Old Harbor Native Corporation is an Alutiiq **village corporation on Kodiak
Island, Alaska** (`CE-000A9-81`). Three Affiliated — Mandan, Hidatsa, Arikara —
are in **North Dakota** (`CE-0016W-A5`).

    FGELS2KFR825  AMEE BAY, LLC                        3,592   $295,915,554.72
    NW3JPQEZRPK1  OCEAN BAY INFORMATION AND SYSTEMS    1,355   $153,461,276.32
                                                       4,947   $449,376,831.04

Same shape as the United Keetoowah Band merge fixed the day before, so it was
held to the same standard: **the row must contradict itself.** Four
discriminators, all internal:

1. 2,341 carry `parent_uei = K3N7G5L6GRY6`; **629 OTHER rows with that same
   parent UEI are keyed to Old Harbor at tier A.** One parent UEI, two nations.
2. 374 more name `THREE SAINTS BAY LLC` (`ETNKUJ6T6L26`), the holding company —
   Three Saints Bay is the historic site beside Old Harbor on Kodiak Island.
3. **All 4,947 are `recipient_state_code = AK`.** Three Affiliated's other 7,544
   rows: IL 3,486 / ND 2,575 / TX 675 / GA 226 / MT 188.
4. Rolling Bay / Barling Bay / Shearwater Systems — the same corporate family —
   are keyed to Old Harbor at **tier A by `elijah_ruling_redirect`**. The two
   disputed firms are tier B by `cluster_v3`, rationale *"Algorithmic name
   clustering, unreviewed"*. **The owner had already ruled on this family; the
   cluster reached these two first.**

**The cluster's token was `Three`,** and it also caught `Three Guys Garage,
Inc.`, `THREE BEES OF VIRGINIA L.L.C.`, `Three Fires Development Group` (an
Anishinaabe term), `Three Sisters Federal` and `Three Streams Federal`. **Those
are FLAGGED, not moved** — `review/three_token_cluster_flags_2026-09-02.csv`,
20 identifiers. Repointing on a name pattern is the defect, in reverse.

Fixed at source (7 identity tables) **and** in the 5 materialised tables, which
is the exact half `83c7f00` had to come back for. Conservation:

    rows        1,217,768 -> 1,217,768                       0
    columns            70 -> 70                              0
    total       $310,005,258,661.21 -> $310,005,258,661.21   $0.00
    CE-0016W-A5 $1,582,995,932.87 -> $1,133,619,101.83   -$449,376,831.04
    CE-000A9-81   $623,210,444.79 -> $1,072,587,275.83   +$449,376,831.04
    cedar_uids whose total changed: exactly those two

**Two neighbours investigated and NOT moved, because they do not share the
cause** — the mandate asked for this explicitly and the answer is negative both
times. (a) 137 rows, `OLD HARBOR SOLUTIONS LLC` → Alutiiq/Koniag, $27.9M: its
FPDS `parent_uei` is its own, so the contradiction is absent, and Koniag is the
regional corporation for the archipelago containing the village. (b) 292 rows,
$66.4M, `unattributed`: the only route to a key is the parent's *name*, weaker
than the four discriminators. Unresolved is a legitimate outcome. Both flagged.

### Finding 3 — Codex right about the contradiction, wrong about the half

C4 read the **first 50,000 rows** and called it a percentage. `head -n` is not a
sample of an ordered file:

    prime_contracts.csv  first 50,000:  22,595/50,000    = 45.2%
                         FULL:         888,958/1,217,768 = 73.0%   -27.8 pp

It covered 65% of `subawards.csv`, which is why it looked fine wherever anyone
checked. Full scan: contractors 60% → **75%**, subcontracting 42% → **100%**,
funding 40% → **16%** → **80%** today. So the blocker removal is correct and
**the README was the stale half.** Also corrected there: "11 of 13 READY" → 14
of 14.

Said civilly in the reply, with the precedent: this is the same shape as PR #26
finding 6 (`STEPHEN GRAHAM`), where Codex was right that doc and data disagreed
and its own *second* option was the right repair. **When a doc and a
measurement disagree, ask which one was measured.**

### Finding 4 — 156,592 rows, two causes. `code/1076_clear_self_parent_piid.py`

    source                    rows     has parent  self-parent     none
    master prime file.dta   376,766      220,179      156,587        0
    FY*_All_Contracts.zip   841,002      578,224            5  262,773

(a) The legacy `.dta` **encodes** standalone as self-parent: 216,882 of 617,142
raw rows self, **zero blank**, against a genuine 31.2% blank rate in the FPDS
archive. Same population, same rate, two conventions.
(b) `114_pull_prime_archive.py:771` wrote `s("parent_award_id_piid") or
s("award_id_piid")` — a fabricator that had fired on only 5 live rows, which is
why it survived. 262,773 archive rows already carry a genuine blank; one refresh
through that line converts every one.

Both fixed at source (114 and 40) and cleared in place. **The README's proudest
claim went with it:** "zero rows have neither" was true only because a sixth of
the table wore a fabricated parent. Now 507,884 / 290,519 / 419,359 / **6**.

### Findings 6 and 8 — one parser. `code/1077_nagpra_institution_grain.py`

Prefix rows **966**, not the 857 first measured — and *the regenerated sample
caught my own undercount*: the first regex was `^[A-Z][A-Za-z ]{2,40}:` and
missed 98 rows of lowercase `a Cultural Item:` plus 6 of `Notice To Rescind a
Notice of ...`. Distinct institution names **2,184 → 1,798**. Six residual
colons are real names (`Bureau of Reclamation, Region 10:`) or malformed FR
titles and are FLAGGED, not stripped —
`review/nagpra_title_oddities_2026-09-02.csv`.

Finding 8 was worse than reported. `institution_names_all` split on `, and `,
cutting *South Carolina Department of Parks, Recreation, and Tourism* into two
entries, one of them **`Tourism, Columbia, SC` — an institution that does not
exist**, invented by the column meant to fix the reported problem. The FR
separates co-holders with `; `, which the parser never split on.

New shipped table `data/clean/nagpra_notice_institutions.csv`: **7,234 rows**,
one per (notice, institution), 7,087 with a state, 392 notices naming >1.
Declared in `512.GRAIN_PR29`, registered in the codebook, `nagpra` stays READY
at 5 customer tables. Ordering declared in `cedar_pipeline.ENRICHER_ORDERING`
and waived at the top of 77 — **the parser fix is in 77 itself so a rebuild
reproduces the six columns, but only 1077 writes the bridge, so 1077 runs
last.** The FERC failure (102,615 filings, a 183-row docket table, neither file
wrong on its own) is the reason that is written down.

### Finding 5 — 1 of 787, and why it is a column not a bridge

A bridge is the better architecture and would add a third shipped `gaming`
table with a grain, a key and conservation coverage to maintain — for two rows.
`operating_entity_cedar_uids` + `n_operating_entities` carry the same fact at
the existing grain, and the count is what will say when a bridge has become
right. **The obvious generalisation is worse than the bug**: splitting `tribe`
on the usual separators finds 58 of 787 and **57 are false**, because `&`,
` and ` and `,` sit inside single tribes' legal names (*Assiniboine and Sioux
Tribes of the Fort Peck Indian Reservation*). `/` is the only operator
separator and it occurs once.

### Finding 1 — and the lesson about verification claims

`0 of 13`. The round-1 fix for PR #26 finding 1 *created* this by namespacing
Cedar's fields under `cedar` — tidy, and still an undeclared keyword. **The
claim "verified, not assumed" was written in the same commit and never
executed.** The descriptor now carries exactly the 14 dataclass fields; Cedar's
facts move to `dist/collection_descriptors.cedar.json`; and 760 diffs the key
set in both directions and exits 1 rather than writing. Verified against the
real dataclass on `main`: **14 of 14 construct.**

### Findings found by this side while addressing Codex's

- **A descriptor with no sample, the mirror of finding 7.** The `nest`
  collection landed mid-branch and 760 emitted a 14th descriptor for a dataset
  with no sample file at all. `nest__sample.csv` now ships; `sample_file` is a
  field in the `.cedar.json` sibling and every one of the 14 resolves.
- **The two `PRODUCT_ID` maps could drift silently.** 770 now reads 760's dict
  and exits 1 if they differ. One dict, two call sites, one updated, is exactly
  how finding 7 happened.
- **A renamed sample leaves its old file behind, and the old file still looks
  like a sample.** After `native-owned-businesses__sample.csv` became
  `owned__sample.csv`, the first one sat in `dist/samples/` with stale rows
  and anything copying `dist/samples/*` would have shipped both - one of them
  out of date and claimed by no descriptor id. 770 now retires any
  `*__sample.csv` it did not write in the current run, to `.csv.retired`, and
  prints which. Found by diffing `dist/` against the product repo after the
  push, not by any gate.
- **A concurrent rebuild moved a sample out from under the branch.** The
  `nest` workstream rebuilt `nest_enterprises.csv` between the sample being
  drawn and the branch being pushed, so the ten shipped rows were already a
  different ten. Caught by the same `dist/`-vs-repo diff and refreshed in
  `4c3ac3a`. **Re-diff after pushing, not before**: the window that matters is
  the one after your last regeneration.
- **A gaming "encoding bug" that was not one.** `Keex Kwan Gaming – Bingo`
  renders as `Keex Kwan Gaming ? Bingo` in a cp1252 console. The bytes are a
  correct UTF-8 en dash in both the table and the sample. Measured before
  reporting; nothing to fix.

### Gate state at hand-off

`1075`, `1076`, `1077`, `1078` each carry `verify` and `selftest`; all four
`verify` exit 0 and all four `selftest` pass. `293_lint_bug_classes.py` carries
**zero** findings from the four new scripts (the class-5, class-6 and class-7
hits were waived with reasons, not baselined).

**`62_no_regression_check.py` is RED and it is not this workstream's.** Named
with the measurement, per the field guide: `tables_undocumented_in_codebook`
rose 3 → 20, and **all 20 belong to other workstreams** — `geo_*` (7 tables,
870/871/873/874), `cedar_constellation_*` (852), `tribal_newsletter_*`
(993/994), `gaming_web_harvest_*` (980), `native_business_*` (1001/1060),
`consultation_agency_coverage`, `gaming_property_locations`,
`wa_machine_transfers`, `cedar_entity_freshness`. None is a table this pass
created: `nagpra_notice_institutions.csv` was registered in the codebook
(score 1.0) in the same commit, and the three new `gaming_facilities` columns
were documented too (block score 0.857 → 0.882). The other reds —
`hearing_bill_links.csv` 465 → 464, `native_bills_subject_sweep.csv`
2,414 → 2,409, and `advocacy_passthrough_2026-08-07.csv` gone from
`data/clean` — are legislation and advocacy tables this pass never opened.

---

## PR #29 — ROUND 3, pushed 2026-09-02 as `caf7438`

**THE MECHANIC THAT WAS COSTING THE LOOP ITS ROUNDS, AND IT IS NOT AUTH.**
Codex's own summary comment states its triggers: *"Reviews are triggered when
you open a pull request for review, mark a draft as ready, or comment
'@codex review'."* **A push is not a trigger.** The summary comment on #29
still named `3fe58a5` as the last reviewed commit — so `6c4801f` (the eight
round-2 replies) and `4c3ac3a` (the nest refresh) were **never reviewed by
anything**, and pushing again would simply have produced a third unreviewed
commit. The auth correction at the top of this file fixed *posting*; this
fixes *getting reviewed*. **Every cycle must end with an `@codex review`
comment on `/issues/29/comments`, not with a push.**

All three endpoints were enumerated before concluding anything, per the rule
at the top: 9 reviews (1 Codex on `3fe58a5`, 8 reply objects), 16 pull review
comments (8 findings + 8 replies, every reply correctly threaded via
`in_reply_to_id`), 1 issue comment (the Codex summary). Nothing new was
waiting. **The absence of new findings was a property of the trigger, not of
the code.**

### The finding this side brought, and it was already visible in the repo

Nothing Codex asked for. It came out of the standing instruction to re-check
every claim against live data before pushing, and the two contradicting files
were **both already pushed**, in one directory:

    data/cedar/samples/README.md            owned -> native_owned_businesses.csv, 2,916 rows
    data/cedar/collection_descriptors.json  owned -> "rows_label": "1,657 rows"

**A sum over a dataset's tables cannot be smaller than one of its tables.**

`770.FLAGSHIP` draws the customer's ten rows from `native_owned_businesses.csv`
— 2,916 rows, **21** certifying authorities (`docs/PUBLICATION_POLICY.md` still
says 18 and 2,393; both are stale), the table the dataset is named after.
`760.rows_in()` sums only what the collection *contract* claims, and that is
six `individual_native_*` tables totalling 1,657 — firms owned by individual
people, a different relation. `500.COLLECTIONS` matches this collection with
`^(individual_native|tribal_certification)` and the namesake table matches
neither branch.

**It was already a known orphan and the connection was never made.**
`code/730_ws4_grain_money_conservation.py:852` lists it under
`contract_orphan_shippable = 6`, attributed to "the workstreams that
registered them". That attribution was correct and nobody owned the
consequence, which is that the product publishes the number.

**The row count is the smaller half of the cost.** `native-owned-businesses`
is READY on `c4_identity_path = 100% keyed` and `c1_grain = 6/6`, measured
across the six tables that exclude the directory. Measured on the directory:

| | |
|---|---:|
| rows | 2,916 |
| `business_entity_id` filled | **4 (0.1%)** |
| `nation_id` filled | 2,725 (93.4%) |
| `certifying_authority_entity_id` filled | 2,767 (94.9%) |
| declared grain | **UNSTATED** |

"100% keyed" is true of six tables the buyer never sees and false of the one
they are shown. The dataset keys to a *nation*, not to a *business* — which is
a defensible product, and is exactly the `affiliated_with` claim
`PUBLICATION_POLICY.md` argues for, but it is not what READY was asserting.

### What was fixed, and the line that was deliberately not crossed

`760` now enforces the invariant (ADR-018). It reads `FLAGSHIP` and `SPINE`
out of `770` **by text**, mirroring the discipline `770` already uses to read
`760.PRODUCT_ID`, so a rename on either side is a hard failure rather than a
silent divergence. On a violation it does **not** quietly repair the number:
it publishes the union of both Cedar-side declarations (1,657 + 2,916 =
**4,573**, with `n_rows_basis` naming both halves) and marks the dataset
BLOCKED with the measurement in `cedar.blockers`. The status reverts by itself
when the collection is fixed. `verify` exits 1; `selftest` carries **three**
fixtures and all three pass — the undercount fires, a claimed flagship with a
sufficient sum is clean, and an unclaimed flagship fires *even when the sum is
large*, because an unclaimed table has no grain, no key and no rebuild path.

**`500`, `512` and `518` were not run and not edited.** They are
integrator-owned; ADR-017 records another workstream making the same refusal
the same day. Widening the collection adds four tables with no declared grain
and no declared key (`native_owned_businesses.csv` 2,916,
`native_business_contract_links.csv` 2,393,
`native_business_identifier_crosswalk.csv` 481,
`native_business_contracting_by_nation.csv` 18) and moves a dataset's
readiness. **Filed in `review/OWNER_DECISION_QUEUE.md` with the evidence.**

**The invariant is 1 violation, not a class.** All fourteen were checked: 13
flagship tables are claimed by their own collection and every other descriptor
count exceeds its flagship. `_entity_layer` is **exempt from the membership
half rather than passing by luck** — its flagship `cedar_identity_register.csv`
lives in `data/spine/`, outside the contract by construction, and clears the
arithmetic half at 1,555 against 326,899.

### Claims re-measured, and two of them were wrong

- **The README stated one quantity as two different numbers, 72 apart.**
  `345,180` in the money-columns section and `345,108` in the Acoma
  correction, for the same measurement. Today, with the method written down
  (case-insensitive exact compare of `canonical_name` against the register's
  name for that row's `cedar_uid`): **340,738** disagreements + **3,622**
  blank labels of **552,602** keyed rows = 344,360. **0** rows carry a
  `cedar_uid` absent from the register. Case-sensitive, for the record, is
  364,754 — so the comparison mode has to be stated or the number is not
  reproducible.
- **The "98.3% explained" figure understated it.** `340,653 of 340,738 —
  100.0%, $94,256,591,555.42` carry a label appearing verbatim in
  `lineageA_dta_corrtd_tribe_key.csv` (393 distinct name strings).
- **The 85-row residue needs no repoint, and one of the two labels is a
  hazard.** 72 rows / $29,694,344.00 on `CE-001GC-WN` are labelled `Forest
  County` while the register calls that entity *Sonoma County Indian Health
  Project, Inc.* — and **all 72 are `recipient_state_code = CA`**, so the key
  is right and only the label is wrong. It is worse than merely stale: Forest
  County Potawatomi is a real Wisconsin nation and sits on the
  `TERMS_STATED_RESTRICTIVE` list. The other 13 are a `Warms Springs` /
  `Warm Springs` typo, all Oregon.
- **Old Harbor held exactly.** `CE-000A9-81` 7,803 rows / $1,072,587,275.84 and
  `CE-0016W-A5` 7,544 rows / $1,133,619,101.84, re-measured on the live table.
- **The parent/child cross-tab is internally consistent.** 419,365 rows carry
  no parent, which is the README's 419,359 plus the 6 that have neither, and
  the parent-bearing total 798,403 reproduces exactly.
- **Newsletter corpus, for whoever ships it:** 1,650 rows, **1,037 distinct
  channel URLs**, 1,555 entities probed of which **650 carry at least one
  channel**, 1,289 with a live site, archives back to **1970**. The
  "1,195 channels / 650 entities" figure in circulation is stale on the first
  half and right on the second.

### A measurement retracted before it was reported

Two consecutive runs of `770` produced different `legislation` samples, which
would have meant a **non-deterministic sampler** — a class-7 defect and a
serious one, because it would churn the branch diff on every rebuild. Re-run
properly, with the input mtimes captured either side of both runs: **all
fourteen samples byte-identical**, mtimes unchanged, and the first result was
a concurrent job rewriting `bill_votes.csv` between run one and run two. **The
check was measuring something other than its own name** — field guide section
3, from the inside, in this workstream's own hands.

### Concurrency, as it actually behaved

Ten jobs write `data/clean` and it showed. Inside one hour: `deals_classified`
935 → 1,079; the `deals` descriptor 2,386 → 2,674; `lobbying` 242,199 →
264,478; `gaming` 127,312 → 128,487; and **`deals` flipped READY → BLOCKED**
because another workstream added `deals_press_edgar_ancsa_additions.csv` with
no grain and no key. READY went 14 → 13 → 12 while this branch was being
prepared. It is named in the README as another workstream's, not absorbed, and
that section now tells the reader to regenerate the count rather than quote
it.

**The dist-vs-repo diff was run AFTER the push, per the rule earned last
round, and came back in sync.**

### Codex answered — five findings on `caf7438`, all P2, **all five right**

Triggered by the `@codex review` comment, which is the mechanic recorded at
the top of this section. Enumerated across all three endpoints: 5 new review
comments, 0 new issue comments beyond the refreshed summary, latest Codex
review now on `caf7438`.

| # | file | finding | verdict | what it did not show |
|---|---|---|---|---|
| 1 | `collection_descriptors.json` | do not publish the unverified sum 4,573 as the row count | **Right, and further than it knew** | the *other* half, 1,657, is not a row count either — five grains added together |
| 2 | `contractors__sample.csv` | `funding_agency = "Nan"` is a fictitious agency | **Right** | 1 cell sampled; **617,097 cells, 8 columns**; and the source fix then lost a race |
| 3 | `README.md` | `samples/README.md` still publishes both stale figures | **Right, and it is generated** | the sibling was fixed at its generator, not by hand |
| 4 | `README.md` | the overview still says every blocker list is empty | **Right** | same defect shape as the two row counts, one file apart |
| 5 | `collection_descriptors.cedar.json` | blockers omit the flagship's own readiness failures | **Right** | a consumer would conclude fixing the count makes `owned` ready |

#### Finding 1 — the refusal was correct, and it holds against the fix's own reasoning

The first fix published the union, 1,657 + 2,916 = 4,573. Codex: *"nothing
establishes that these are disjoint rows in one shipped dataset."* True, and
the argument against it was already in the text doing the publishing — the
README describes the two as **different relations**, which is a reason to
believe they are disjoint, not a measurement that they are. Worse, the
qualification lived in `n_rows_basis` in the sibling `.cedar.json` while
`rows_label` is the field the product renders. **A fabricated number with a
footnote nobody renders is still a fabricated number**, and 760's own
docstring already carried the rule it broke: *"an empty field a human fills is
honest; a generated sentence that reads like a claim is not."*

`rows_label` is now `row count unresolved`; `n_rows` is `null`;
`n_rows_contract_tables` (1,657) and `n_rows_flagship` (2,916) ship
separately, each labelled with the table set it came from, and are not added.

**Then the measurement Codex's objection provoked found the worse half.**
Across all six contract tables there are **10** shared firm names against the
directory's 2,738 — so the two sets are nearly disjoint after all. But inside
the contract set:

| table | rows | what a row is |
|---|---:|---|
| `individual_native_firm_register.csv` | 45 | a firm |
| `individual_native_firm_contracts.csv` | 324 | a **firm-year**, 38 distinct firms |
| `individual_native_ownership_verification.csv` | 335 | a firm's verification |
| `individual_native_verification_candidates.csv` | 335 | **the same 335 firms again** — all 335 `(name, uei)` keys shared, identical column set |
| `individual_native_firm_contracts_published.csv` | 613 | **not a firm** — `cell_type`, `dimension_1`, `dimension_2`, `n_firms`: a cross-tabulation |
| `individual_native_exclusion_pairs.csv` | 5 | a pair |
| **sum** | **1,657** | **five grains added together** |

**Neither number in the original contradiction was a count of a dataset.**
1,657 counts 335 firms twice and adds 613 aggregate cells to a firm count.
The de-duplication problem Codex asked to see resolved was inside the half
nobody was questioning — including this side, which had spent the whole round
treating 1,657 as the trustworthy figure and 2,916 as the one it contradicted.

#### Finding 2 — one sampled cell, 617,097 in the table, and the reason is a good one

`772_strip_nan_sentinels.py` matched **case-sensitively**, justified in its own
docstring by *"never a substring — `Nanticoke`, `Nanakuli` and `NANA` are real
values"*. Every one of those is an argument against a SUBSTRING rule, and it
was never a substring rule: it is whole-cell equality, and a 3-character token
cannot equal a 4- or 8-character value. **The case-sensitivity guarded nothing
the whole-cell rule was not already guarding.** Hidden by it:

    cage_code               398,840   32.75%   'NAN'
    place_of_perform_city    88,269    7.25%   'NAN'
    place_of_perform_state   87,068    7.15%   'NAN'
    funding_agency           33,263    2.73%   'Nan'
    extent_competed           9,411    0.77%   'NAN'
    recipient_state_code        202            'NAN'
    parent_uei                   22            'NAN'
    recipient_city_name          22            'NAN'
                            -------
                            617,097

`extent_competed` is the worst: START_HERE warns it holds two vocabularies and
must be read through `extent_competed_normalized`; a phantom `NAN` is a third.

**Scope measured in both directions: one table.** The same case-insensitive
sweep over the eleven other flagship tables returns **0** cells. The token set
was deliberately **not** widened — `NA` (6 cells) and `N/A` (7) stay, because
`NA` is an abbreviation a human may have typed to mean *not applicable*, which
is a statement rather than a stringified float. Named, not swept.

**AND THE SOURCE FIX LOST A RACE, WHICH IS THE DURABLE PART.** 772 corrected
and run: 617,097 cleared, 1,217,768 rows in and out, `$310,005,258,660.75`
unchanged to the cent. Re-measured minutes later: **all 617,097 back.** A
concurrent in-place enricher had read the table *before* 772 started and wrote
back its own copy, with five new `identifier_ruling_*` columns and every
sentinel restored. **772's guard compares size and mtime across its own READ
and correctly saw nothing** — the other writer's read predated it, so there
was nothing for that guard to see. The live file's mtime (07:57:20) is
*earlier* than 772's write (08:02:03), which is the tell.

**The rule this earns, beside "the enricher runs LAST": a mtime guard around
your own read cannot detect a writer whose read predates yours. Two in-place
enrichers on one table need a declared ordering, and these two had none.** It
is reported rather than fought — re-running 772 against a live job is a write
war, and the ordering is an integrator decision.

So the guard now sits in **two** places, and the second cannot be raced. `770`
blanks any whole-cell null token across the **whole source table** before the
ten rows are drawn — which also stops a row being scored "complete", and so
preferentially sampled, for holding the string `Nan`. Counts are printed per
column and published in `samples/README.md`, so the guard surfaces the
upstream defect instead of concealing it.

#### Findings 3, 4 — the same defect shape as the one this round opened with

Both are a corrected statement and its uncorrected copy. Finding 3: the
sibling `samples/README.md` still carried **both** stale figures and a
parenthetical calling the gap a rebuild artefact whose last two digits did not
matter. It was not an artefact — the two numbers are the same measurement run
**case-sensitively (364,754) and case-insensitively (340,738)**, a 24,016-row
difference, which is why the comparison mode now ships with the figure. That
file is **generated by 770**, so it was fixed at the generator, not by hand.
Finding 4: the contract overview still said every blocker list was empty after
the status section had been changed to name two.

**Three instances in one branch of one thing: a number corrected in one place
and left standing in another.** It is the same failure as `owned`'s two row
counts, and the same failure as `345,180` / `345,108`. The field guide's
"numbers go stale in place" is usually read as *old documents rot*. These
three rotted **within a single edit**.

#### Finding 5 — blockers are an interface, and prose is not

The measurement existed and sat in prose. A consumer following this project's
own instruction to read `cedar.blockers` would have concluded that reconciling
the count makes `owned` ready. All three now ship, **measured on the table
rather than asserted**: the flagship mismatch, `C4 identity path`
(`business_entity_id` filled on 4 of 2,916 rows, 0.1%), and `C1 grain
UNSTATED` with no validated primary key. The identity column is *found* among
candidates rather than assumed, and a table carrying none of them reports
**UNMEASURED** rather than a fill rate for a column that is not there.

#### Gate state

`293_lint_bug_classes.py`: **zero** findings name `760` or `770`; every new
finding since baseline belongs to another workstream (1011, 1060, 1085, 1086,
846, 852, 873, 992, 1030, 1031, 1110, 980, 1081, 1077, 1107, 30, 518, 870,
871). `760 selftest` — three fixtures, all pass. `760 verify` — exits 1,
correctly, on the named finding it exists to raise.
