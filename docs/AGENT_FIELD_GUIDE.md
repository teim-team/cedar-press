# AGENT FIELD GUIDE

*Written 2026-09-02. Every claim below was re-verified against the live files
that day; the file or script that proves each one is named. If you find one
stale, fix it here — a field guide repeating a stale claim is worse than none.*

**This is the short one.** `AGENTS.md` is ~6,000 lines and is mostly an
append-only journal of gate failures; `START_HERE.md` is ~1,000. Read those for
the dataset you are actually touching. Read *this* before you write anything,
once, in full. It is the set of traps that have each cost this project more
than one session.

---

## 0. Before you write anything

```
py -3 code/1050_preflight.py
```

It claims your script number atomically, prints which shared files need marker
discipline, reads `NEVER_RUN` live out of `cedar_pipeline.py`, and tells you how
to check whether the thing you are about to download is already on this
machine. Four commands, all read-only except `claim`:

```
py -3 code/1050_preflight.py claim <short_slug>   # take a number, atomically
py -3 code/1050_preflight.py ondisk <term>        # is it already local?
py -3 code/1050_preflight.py shared               # which files need markers
py -3 code/1050_preflight.py numbers              # the collision census
```

---

## 1. `ls code/<n>_*` cannot stop a collision. `claim` can.

43 numbers in `code/` carry more than one script; ten carry three. The
instruction to check first has been in `AGENTS.md` since 2026-08-07 and
`62_no_regression_check.py` has ratcheted `code_duplicate_numbers` at 43 since
2026-08-28. Neither made it shrink, because **check-then-write is not atomic**:
two agents both run `ls code/154_*`, both correctly see nothing, both write.

`1050_preflight.py claim` uses `os.open(..., O_CREAT|O_EXCL)`. The OS refuses
the second caller. It allocates strictly above the frontier, so a number is
never reused and a stale citation of "script 154" can never come to mean a
*new* script. Then write your code **into the stub it created** — do not create
a second file.

If you abandon the work: `py -3 code/1050_preflight.py release <n>_<slug>.py`.
It refuses to delete anything that is not still an untouched placeholder.

**Why the existing 43 are not being renamed** (measured 2026-09-02, so the next
agent does not re-open it): 43 numbers cover **96 files**; **40 of the 43** are
cited as "script N" in prose in `docs/` or the root `.md` files; and **417**
`.bak_*` files on disk are tagged with a bare number. Renaming is an owner
decision with a real blast radius, not an agent's cleanup. `claim` stops the
44th; the existing 43 are grandfathered by the ratchet in `62`.

**Backup tags carry the STEM, never the bare number.** `.bak_<date>_pre_1050_preflight`,
not `.bak_<date>_pre1050`. On 2026-08-26 four scripts were numbered 163, all
four wrote `.bak_2026-08-26_pre163`, and one of them restored by *glob* — which
reverted seven files belonging to two other agents and left the spine carrying
179 promoted NHOs whose ledger rows had just been deleted.
Full account: `review/_INCIDENT_2026-08-26_script163_number_collision.md`.
**Never restore by glob. Restore from a literal list of the files you wrote.**

---

## 2. Shared files: append inside your own marker, never rewrite

Some files are written **wholesale** by a generator that preserves only marked
blocks. Put your prose between your own pair and it survives; write outside
them and it is gone on the next run. Write over someone else's block and you
have destroyed their work — this already happened once to the Gaming section of
`docs/MONEY_TOTALLING_RULES.md`, which had to be restored from a commit, and
the marker convention is what came out of it.

```
<!-- BEGIN <YOUR-WORKSTREAM> -->
...
<!-- END <YOUR-WORKSTREAM> -->
```

Currently marker-protected (re-derive with `1050_preflight.py shared`, do not
trust this list to stay complete): `docs/MONEY_TOTALLING_RULES.md` (written by
`code/574_ws1_money_and_conservation.py`), `docs/ARCHITECTURE_DECISIONS.md`,
`docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md`.

The same problem in Python has the same shape: `code/512_build_dataset_contracts.py`
gives every workstream **its own `GRAIN_*` dict** (`GRAIN_WS2`, `GRAIN_FAADS`,
`GRAIN_GAMING`, …). Add yours; touch nobody else's.

Two blocks sharing a marker name are one block to the preserver. Pick a name
nobody has.

**Ownership is declared before you edit**, in `docs/ARCHITECTURE_DECISIONS.md`.
One agent owns a central file per pass. The integrator owns `62`, `512`, `517`,
`518` and **all commits**. No agent commits.

---

## 3. This repo's signature defect: a check that does not measure its own name

**Twenty-four measured instances**, fifteen of them by the morning of
2026-09-02 and nine more by that evening. They share one shape — *the number was
produced, it was plausible, and it was about something else.* Read the table for
the shapes; the rules under it are what you apply.

| the check | what it reported | what it was actually measuring |
|---|---|---|
| `urllib.robotparser` | 22 sources "blocked" | a **403 on robots.txt** reads as `disallow_all`. A site that will not serve its robots file is not a site that forbids you. `docs/PULL_DISCIPLINE.md` |
| `27_build_dataset_manifests` | one gaming table at 17,877 rows | **physical lines**, against 1,521 CSV records — 11.8x, because quoted fields contain newlines. See its own docstring, line ~1404 |
| a `?wpdmdl=` harvester | 302 distinct documents, all HTTP 200 | **the same PDF 302 times**. Green statuses, one file. `docs/GAMING_SOURCE_AUDIT_2026-08-26.md` |
| `630_refresh_cadence` | event-driven sources scored stale | a **calendar** edge applied to sources that publish *when something happens* |
| `api.congress.gov` | 403 | **no User-Agent**, not an access restriction |
| `830_entity_freshness` | median 0 days, then median 6 | first **Cedar's own activity dates** won the max; then **future fiscal years were clamped to today** instead of discarded. It now discards them — see the docstring at line ~178 |
| `518` C4 | 47,877 rows with an attached identity | `owner_as_of_transaction_cedar_uid = "UNKNOWN"`. A populated cell is not a resolved identity |
| `518` C4 | percentages for `prime_contracts`, `subawards`, `faads_transactions*` | **estimates**: `SCAN_CAP = 50_000` rows per table. It now names them in `c4_sampled_tables` — read that field before quoting a C4 figure as a census |
| two, in one day, 2026-09-01 | a column match; a de-dupe | a regex matching `tract` inside `contract_number`; a de-dupe key that evaluated to `""` and would have matched **everything** |
| `845` regenerate guard v1 | 33 unsafe writers, worst at 62 and 53 columns | **name overlap, not the writer's actual output path.** `910`'s 62-column finding was an 11-column review file and `76`'s 27-column finding was a script that only READS that table - 9 of 29 findings were pairings that do not exist, while 26 real ones were invisible because the literal reached the writer as a `write_csv()` argument. A detector loud about nothing and silent about something. `code/845_regenerate_guard.py` |
| a regen-and-diff check | `docs/LOBBYING_BUILD_LOG_2026-08-05.md` PROVEN SAFE, byte-identical | **the generator never ran.** `06_build_log_stats_v2.py` exited 2 - it lives in `code/lobbying_pull/`, not `code/` - and an untouched doc is that check's strongest PASS. **Any regenerate-and-diff anywhere in this repo has this hole: assert the exit code before you read the diff.** `845 regen` now refuses on a nonzero exit |
| `845 scan_md` | 0 markdown docs at risk | **`git log` returned nothing**, so every doc scored 0 hand edits and the whole half printed clean. Seen from inside `62`, where the standalone run of the same code saw 9. It now RAISES rather than report a number it cannot measure, and `62` prints UNMEASURED |
| `845` class 3, first run | 13 sites UNDETERMINED, 6 of them wrongly | **`awards, stats = [], Counter()`** - a tuple bound to a tuple. The key set was fully knowable and the analyser could not see through the unpacking, so it reported *unmeasured* where the honest answer was *clean*. Undetermined is the safe direction to be wrong in, and it is still wrong |
| `845 regen`, "no digit = prose" | `docs/INVENTORY.md`, 20 hand-authored lines at risk | **blank lines and a repeated markdown table header.** A line with no digit in it is not a sentence somebody wrote. Replaced with the real measure - a removed line whose exact text appears NOWHERE in the rebuild - which is immune to reordering and to hunks that stop pairing |
| `845 regen`, default mode | *(caught before it ran)* | it invokes the generator **bare**, and `1020_tail_web_probe.py` writes its doc under `doc` while running a **network probe ladder** with no arguments. Regenerating that markdown would have opened sockets nobody asked for. It now refuses when the doc write sits behind a named subcommand, and takes the mode as an argument |
| `1123_copper_river_attribution` | "$1.5B attributed to the Native Village of Eyak" | **nothing attributed.** It wrote `canonical_name` and `cedar_uid`; `40_build_prime_contracts.py` keys on `tribe_id` and gates on `attributed_flag`, both untouched. 6 rows ended up naming Eyak in `canonical_name` while `tribe_id` still said Seldovia. `docs/QUARANTINE_EXPOSURE_LOG_2026-09-02.md` §5b |
| `1123`'s conservation check | rows and dollars conserved **to the cent** | **that the work had not happened.** Conservation was never the risk. See rule 5 |
| `526.scan()` | *"drop 10 always-empty column(s)"* on `prime_contracts.csv` | **20,000 rows.** Those ten include `contract_transaction_unique_key` and `contract_award_unique_key` (841,002 non-blank each) and `naics_code` (**838,229**). Across 13 capped tables, 65 "always empty" claims and **22** actually empty. `docs/ARCHITECTURE_DECISIONS.md`, ADR-016 |
| CDR-11 | quarantined-method exposure at 2,142 rows / $38.19B *(SUPERSEDED)* | **one join leg of three.** `40` tries `uei_exact`, then `cage_exact`, then `parent_uei`; disjointly they are 227,540 rows / **$45.93B**, and the CAGE leg is where `need_v6` actually lives. `docs/QUARANTINE_EXPOSURE_LOG_2026-09-02.md` §2 |
| `830_entity_freshness`, again | "entities in NO Cedar row at all" pinned at **0** | **its own output.** `cedar_entity_freshness.csv` is written by that script into the directory that script scans, one row per register entity, so from run two the answer could only ever be 0. The honest number was **104**. Fourth occurrence in that one script. `code/830`, `IDENTITY_LAYER` |
| the same, once more | 0 again, after the name list was added | `regulations_gov_entity_coverage.csv` — a ledger of what Cedar **searched** — slipped under a 98% / 1.05-rows-per-entity shape test *by a hair*. A single numeric edge will keep being missed by a hair; `830` now also takes a filename that declares itself `_coverage` / `_freshness` / `_probe_log` at its word |
| a hub-name token matcher | `BLUE TECH INC.` → Blue Lake Rancheria, tier B, **$3.51B** | the token **`blue`**. Same shape on `north` (60+ CAGE codes onto the Lumbee Tribe of *North* Carolina) and on `wind` (Wind River is the Eastern Shoshone reservation). `docs/QUARANTINE_EXPOSURE_LOG_2026-09-02.md` |
| a shared-hub ownership test | the 2012 Alaska Gold purchase read as a **relabelling** | a **present-tense** ownership map. Alaska Gold is a BSNC subsidiary *today*, so both sides of a past acquisition resolve to one hub and the transaction disappears. `docs/methodology/deals.md` §5b |
| `62_no_regression_check.py`, 2026-09-02 03:5x | `NameError: ROOT is not defined` — every gate unrunnable | **a live edit window.** The 37 lines were uncommitted and being written as it was observed. Real when seen, false forty minutes later. `docs/KNOWN_ISSUES.md` A5 / `A5-RESOLUTION` |
| `1116`'s own first draft, 2026-09-02 evening | the gaming facility count is **734** | **`facility_name == "no casino"` exactly.** 7 rows match that string; **16 rows' names say it**, nine of them inside a longer name (`Grand Canyon West - no casino`, `Tribal admin only - no casino`, `No casino currently`). The script written to stop superseded numbers propagating produced one, and the gated ladder in `code/846_session_audit.py::_denom` is 771 facility rows / ~~714 distinct properties~~ **717 distinct properties** — *corrected 2026-09-02 by `code/1141_gaming_quality_pass.py`, and the correction is itself an instance of this rule.* **`714` was the MECHANICAL sweep and it over-collapses three real pairs**; the settled figure is `COUNT(DISTINCT cedar_place_id)` = **717**, which is 771 minus the 54 extras collapsed by the 53 ADJUDICATED merge groups. `846::_denom` and `code/1129_place_ids.py` V9 both assert 717; **`1116 derive` went on computing 714 from its own name-cluster heuristic for most of the day**, under a comment reading *"846's algorithm, reproduced"* — which it was, in the morning. Two ladders for one number, and the second one drifted, exactly as §7 says. It now reads the place id instead of deriving anything. **`714` is still quoted as "the property denominator" in seven other documents** (`ARCHITECTURE_DECISIONS.md`, `CODEX_PR29_OPEN.md`, `DEPENDENCY_MANIFEST.md`, `MONEY_TOTALLING_RULES.md` ×3, `SEC_GAMING_FACILITY_REVENUE_BUILD_LOG.md`, `TRIBAL_DEBT_HOLDINGS_BUILD_LOG.md`, `WHAT_IS_MISSING.md`) — paste the sentence from `py -3 code/1116_ruling_propagation_2026_09_02.py derive` rather than retyping a number |

**The rules that catch all twenty-four.** The first four were written on
2026-09-02 from the first fifteen; the rest were added the same day from the
nine below them, and each is stated as a rule because each arrived twice.

1. **A check does not count until a fixture proves it FIRES.** Inject the
   violation, assert exit 1 *and* that the NAMED invariant is what fired,
   restore, assert exit 0. A check that has never failed on purpose is not
   known to work.
2. **Verify your input contains what you think it does.** A check reading a key
   that does not exist passes for exactly the reason it is useless. Three
   instances in two days.
3. **Print the denominator, the sample cap, and one worked example row.** Every
   entry above would have died on sight next to a single real row.
4. **An absence of evidence must never print as evidence of absence.** Added
   2026-09-02, from two instances in one hour. A subprocess that did not run,
   a `git log` that returned nothing, a detector that could not resolve a
   name - each produced a CLEAN result, and clean is the strongest thing these
   checks can say. Check the exit code, check the input is non-empty, and emit
   **UNMEASURED** rather than a number. `62` already had this discipline for
   `293`; every new check needs it too.
5. **A proof that nothing broke is not a proof that something happened.**
   `1123` proved rows and dollars conserved to the cent on a table in which it
   had attributed nothing. Conservation was never the risk — it is what you get
   for free when the write missed. **Write the check that FAILS when the work
   did not land**: assert the *intended* delta, on the *intended* column, with
   a floor (`n_rows_now_attributed >= N`), and make it fire on a fixture where
   the write is skipped. A green conservation check beside a no-op is how a
   commit message honestly says "$1.5B attributed" about a table where nothing
   is.
6. **Write to the columns the CONSUMER reads, and go and look at which those
   are.** `cedar_uid` and `canonical_name` are display; `40_build_prime_contracts.py`
   keys on `tribe_id` and gates on `attributed_flag`. Writing the first pair and
   not the second leaves the row disagreeing with itself — six Copper River rows
   named Eyak in `canonical_name` while `tribe_id` still said Seldovia. Open the
   consumer, find the column it branches on, write **that** one. The sibling
   rule, from the decision queue: **a decision must be written onto the row that
   asked for it** — 27,067 queue rows had been answered in sibling files and were
   re-asked for weeks, because an answer in a neighbouring artefact is not an
   answer to anything that reads the queue.
7. **A controlled vocabulary is an interface, and prose in it is a breaking
   change.** A pass recorded its verdicts as 240- and 600-character English
   sentences in `prime_contracts.attribution_method`. Another pass's leg
   detection trusted that column to hold one of four values and skipped every
   row where it did not — **1,486 rows invisible**, silently. If a column has a
   vocabulary, put the sentence in a `_basis` or `_note` column beside it and
   leave the vocabulary alone. If you must widen the vocabulary, widen it
   explicitly and count what falls outside: the fix here was to stop trusting
   the label and report `unknown_attribution_method_rows`.
8. **head-N is not a sample, and an instruction may never be issued from one.**
   `518` C4 reads 50,000 rows per table; `526.scan()` read 20,000 and then
   emitted *"drop 10 always-empty column(s)"* about columns holding 838,229
   values. A **measurement** may be sampled if it says so and prints the cap. An
   **instruction** — drop, delete, merge, collapse — may not be sampled at all.
   Re-count over the full file before you tell anyone to remove something.
9. **A refusal cached as a completion is invisible.** `980` builds its resume
   set from `host_probe.jsonl`, and seven hosts carried
   `EXCLUDED_TERMS_STATED_RESTRICTIVE` records there. When the exclusion was
   lifted, a re-run would have skipped all seven and **printed nothing** — a
   correction that silently does not take effect. When a refusal is reversed,
   the cached refusals must be retired, and retired by **MOVE** to a dated file,
   never deleted: the refusal happened, and the record of it is the evidence the
   correction was needed. `code/1096`, and
   `host_probe_retired_navajo_exclusions_2026-09-02.jsonl`.
10. **Never let an instrument scan its own output.** `830_entity_freshness`
    reports "entities in no Cedar row at all"; it writes
    `cedar_entity_freshness.csv`, one row per register entity, into the
    directory it scans. From run two the answer could only be 0, and the honest
    number was 104. It happened to `830` **twice** — the second time a
    *coverage ledger* of what Cedar had searched slipped past a name list under
    a 98% / 1.05-rows-per-entity shape test by a hair. Five instruments in this
    repo have now counted their own artefacts. A name blacklist does not scale;
    exclude by **shape** (near-total register coverage at ~1 row per entity) and
    by **self-declaration** (`_coverage` / `_freshness` / `_probe_log` in the
    filename), and widen the numeric edge, because a single threshold will keep
    being missed by a hair.
11. **One token of a multi-token hub name is not a name.** `BLUE TECH INC.`
    reached Blue Lake Rancheria on `blue` — **$3.51B** at tier B. `north` put
    60+ CAGE codes on the Lumbee Tribe of *North* Carolina, including
    `MERCEDES-BENZ RESEARCH & DEVELOPMENT NORTH AMERICA`. `wind` is a trap
    because Wind River is the Eastern Shoshone reservation. Require the
    distinctive token, require the residue to make sense, and remember the
    companion already in `START_HERE.md`: **a place suffix makes a tribe name a
    place** — "Boys & Girls Clubs of Wichita Falls" is not the Wichita Tribe.
12. **A present-tense ownership map inverts the test on a past acquisition.**
    Alaska Gold is a BSNC subsidiary *today*, so a shared-hub test resolves both
    sides of the 2012 purchase from NovaGold to one hub and reads a real
    transaction as a relabelling. Any ownership test applied to a dated event
    must use ownership **as of that date** — `owner_as_of_transaction_cedar_uid`
    exists for this — and where it cannot, it must say the test was not run
    rather than return "no change".
13. **A failure seen inside a live edit window is real but perishable.** `62`
    was genuinely unrunnable at 03:5x on 2026-09-02 (`NameError: ROOT`), from 37
    uncommitted lines another agent was in the middle of writing. Recording it
    was right; recording it as a standing issue would have been wrong. **Before
    you write a failure down, re-measure it — and say when you measured.** The
    same discipline as the `dist/` hold in `START_HERE.md` that outlived its
    condition by two days: *a warning with no expiry outlives the condition it
    describes, so say what would make it false.*
14. **Check the binding, not the identifier.** `XWALK` in
    `code/1103_decision_queue_clearance.py` is
    `native_business_identifier_crosswalk.csv`; `XWALK` in
    `code/1109_subawardee_geo_promote.py` is `geo_place_county_crosswalk.csv`.
    A variable name, a column name and a script number are all labels, and this
    repo has been bitten by each: 43 numbers carry more than one script, and
    `attribution_method` says WHO decided while `confidence_tier` says WHAT was
    decided. **Resolve the name to the path, the path to the file, and the file
    to a row you have actually read**, before you reason about any of it.
15. **An exact-string test on a free-text column measures the string, not the
    fact — and a denominator is the worst place to find that out.** FIVE gaming
    denominators circulated on 2026-09-02 and every one was quoted as settled:
    **787** (raw rows), **780** (minus the 7 exact `No casino` placeholders),
    **734** (787 minus duplicates, every placeholder left in), **727**, and
    **714** (the measured property count). None was wrong about the piece it
    measured; four are wrong as a denominator. The nine rows that split them say
    *no casino* inside a longer name, so an `== "no casino"` test cannot see
    them — the same shape as `AMERICANTRIBAL GOVERNMENT` in `START_HERE.md`,
    where one missing space drops 7,160 rows from an exact filter. **Substring
    or normalise, print the rows you excluded, and name the definition beside
    the number.** The gated ladder is `code/846_session_audit.py::_denom`; do
    not build a second one — two detectors for one class drift, which is why
    `248` is a retired stub pointing at `293`.
16. **Two blocks with one marker name are one block to the preserver.** Stated
    in §2 for markdown, and it is the general form of the collision problem:
    `<!-- BEGIN X -->` twice, `GRAIN_X` twice, `code/154_*` twice — in every
    case the second one silently becomes the first one, or erases it. Pick a
    name nobody has, and where a tool can allocate it for you
    (`1050_preflight.py claim`, `adr`), let it.

17. **A column that looks like the answer is not the answer, and three
    of them can disagree on one row.** `prime_contracts.tribe_id` reads 96
    rows higher than `attributed_flag` — $269,771,379 of
    `RULED_TIER_C_NOT_ATTRIBUTED`, a NEGATIVE ruling counted as coverage.
    `federal_funding_transactions` gave **three** answers to "how many rows
    are attributed": 553,106 (`attribution_status`), 552,602
    (`tribe_id_neid`), 549,530 (`attributed_flag`); 504 of the gap was the
    FA-01 unlink clearing keys and leaving the status columns claiming an
    attribution, half a billion dollars of it. **Take the CONJUNCTION of every
    column the consumer branches on**, publish each sibling beside it with the
    disagreement in rows, and name the ROLE the link fills —
    `native_owned_businesses.business_entity_id` is 4 of 2,916 and reading it
    as the numerator says 0.14% about a dataset that is 94.89% linked to its
    certifying nation. `code/1139_linkage_coverage.py`, ADR-037.
18. **A LIST-VALUED key column reads as zero to every scan that looks for
    `cedar_uid`.** `nagpra_notices` has no single-id column at all: six
    pipe-delimited role columns, because one notice names many parties. A scan
    for the three usual id names reported **0% on a dataset that is 90.83%
    linked**, and it was run on this product. Declare the list columns and
    take their union; verified against the table's own `has_resolved_entity`
    at 6,169 both ways, 0 disagreeing.

**A standing gate for the rot these rules produce.**
`py -3 code/1116_ruling_propagation_2026_09_02.py verify` scans every `.md` in
`docs/` and `review/` for the superseded literals of 2026-09-02 and exits 1
while any of them stands with nothing beside it; `derive` re-derives each figure
from the live files so a writer pastes a measurement rather than a memory, and
`selftest` proves the scanner fires. **Prefer computing a sentence from the data
over writing a number that can rot** — `574`'s pattern, where the denominator
sentence is derived from the same two totals it describes. Use a marker only
where content cannot be derived.

---

## 4. Measure duplicates before you collapse them

Four of the five duplicate allegations investigated here were **phantom**:

| alleged | real | if collapsed |
|---|---:|---|
| `prime_contracts` | 80,778 → **0** | — |
| `faads_*` | 180,260 → **0** | would have destroyed **$8,291,124,113** of real obligations |
| `np_schedule_i_grants` | 101 → **0** | — |

A repeated *entity name* is not a repeated *transaction*. Two rows with the
same recipient and the same amount in the same year are usually two awards.
Find the discriminator column before you touch a row — `GRAIN_WS5` in `512`
records one that was found rather than assumed (`operating_company_seq`).
Evidence: `docs/FAADS_TRANSACTION_KEY_LOG.md`, `docs/methodology/contractors.md`.

---

## 5. "Missing" has four causes and only one is a download

At least three sessions have re-downloaded files that were already on this
machine. **27 of the 39** ranked absences in `docs/WHAT_IS_MISSING.md` are
`ON_DISK_NOT_PROMOTED`.

```
SOURCE_DOES_NOT_PUBLISH   a fact about the world. Never a Cedar deficiency.
ON_DISK_NOT_PROMOTED      already local. A join or a column list, NOT a fetch.
NOT_ACQUIRED              a real acquisition task.
CONSTRAINED               licence, statute or terms forbid it.
```

**`CONSTRAINED` narrowed sharply on 2026-09-02** and a good deal of what sat
there is now `NOT_ACQUIRED`, which is a *worse* state, not a better one. Owner
ruling, `docs/PUBLICATION_POLICY.md` `TERMS-OWNER-RULING-2026-09-02`: **a tribal
website's terms language does not block harvest.** The eight-source hard list
— Confederated Colville, CTUIR/Umatilla, Yakama, Chickasaw, NANA/Akima,
Southern Ute, Forest County Potawatomi, Stillaguamish — is released for harvest
of **their own public pages**, as is the `METHOD_RESTRICTED_HOSTS` state.
`source_terms_status = TERMS_STATED_RESTRICTIVE` is now a **recorded
observation, not a gate**: keep recording it, stop refusing on it. What is still
`CONSTRAINED`, and none of it is a terms question — **technical access
controls** (no login-gated content, no admin or staging path, no exploiting a
misconfiguration; publicly *reachable* is not publicly *served*); **a natural
person's data held apart from their public role** (home address, personal email
or phone, DOB, SSN/TIN — a firm's name is not PII, a person's home phone is, and
the business row may be harvested while `owner_name_raw` / `email` / `phone` /
`address_raw` may not be published); **a non-tribal licensor** (EMMA/MSRB, with
CUSIP Global Services as a second licensor); and the **proprietary identifiers**
Casino City and D-U-N-S, held internally and never shipped.

Two shapes go with that release and both have already bitten. **A restriction is
scoped to the host and path where the terms were found** — one Navajo
business-regulatory page had excluded the entire Navajo Nation's gaming
properties, on different hosts — and **it does not bind a third party's
independent publication**: NANA's website terms cannot suppress Trilogy Metals'
10-K. And **over-exclusion is a defect, not caution.** An entity absent for a
restriction its publisher never stated is as wrong as one included against
stated terms; it is simply wrong in the quieter direction, which is why it
survives. See also rule 9: when an exclusion is lifted, the cached refusals have
to be retired or the correction never takes effect.

**A worked instance of the `ON_DISK_NOT_PROMOTED` case, 2026-09-02.** The 990
Schedule C layer was described as a fetch backlog at *"2,195 returns retrieved,
34.3%"*. `nonprofit_schedule_c_lobbying.csv` holds **29,149 rows — 90.5% of the
32,218 indexed target returns — and 29,149 XML files are sitting in
`data/raw/external/irs990_schedc/xml/`.** Only the 3,069 genuinely
un-downloaded returns are `NOT_ACQUIRED`. The label sent readers to the network
for files already on the disk.

Name the state before you open a socket, and name it with a measurement:
`py -3 code/1050_preflight.py ondisk <term>` searches filenames *and* the live
column headers of `data/clean/` and `data/spine/`, because the usual shape of
the mistake is a column that exists in a clean table and is absent from the
sample a buyer was shown. `py -3 code/841_missing_probe.py` is the full ranked
measurement.

---

## 6. Numbers in this repo go stale in place

Superseded figures are never overwritten; they sit in the document where they
were written, looking exactly as authoritative as current ones.

- **`docs/DOC_CONTRADICTIONS_2026-08-26.md` outranks every build log** on any
  number they both state. Check it before quoting a figure.
- `docs/handoffs/STATE_OF_BUILD.md` and `docs/handoffs/STATE_OF_THE_LAND_2026-08-07.md` are the densest
  concentrations of superseded numbers in the project. Their *reasoning* is
  still good.
- **`NEVER_RUN` is live in `code/cedar_pipeline.py` and is the only authority.**
  As of 2026-09-01 it contains **one** script — `41_build_codebooks.py`.
  `01_build_entity_spine.py`, `09_import_rulings.py` and
  `88_build_deals_taxonomy.py` came *off* the list, proven safe by
  `code/812_c8_rebuild_proof.py`. Any prose still calling those three "unsafe to
  run" is stale. Before any rebuild: `py -3 code/build.py plan <collection>`.
- `mtime` answers freshness. It says nothing about completeness.
- **A corrected number rots exactly the way the number it replaced did.** Prefer
  computing the sentence: `py -3 code/1116_ruling_propagation_2026_09_02.py derive`
  re-derives the 2026-09-02 correction set from the live files, and `verify`
  exits 1 while any document still states one of the superseded literals with
  nothing beside it. Do not delete a superseded figure — strike it and say what
  is true, because a reader who meets it in a third document needs somewhere to
  find out it is dead.

---

## 7. The standing gates

| command | what it holds |
|---|---|
| `py -3 code/1050_preflight.py` | before you write |
| `py -3 code/293_lint_bug_classes.py` | the seven named defect classes. **The single lint entry point** — `248` is a retired stub. `--selftest` proves the detectors still fire |
| `py -3 code/62_no_regression_check.py` | the ratchets, including `code_duplicate_numbers` |
| `py -3 code/518_dataset_readiness.py` | READY / BLOCKED / NOT_TESTED per dataset. **There is no fourth status** |
| `py -3 code/287_build_dependency_manifest.py` | which script rebuilds a file another script enriches. The enricher runs LAST |
| `py -3 code/1116_ruling_propagation_2026_09_02.py verify` | the 2026-09-02 corrections, still stated stale anywhere in `docs/` or `review/`. `derive` re-measures them from the live files; `selftest` proves the scanner fires and that an empty corpus reports UNMEASURED rather than clean |
| `py -3 code/1139_linkage_coverage.py verify` | **linkage coverage per customer dataset, ratcheted.** The share of rows carrying a resolved Cedar entity, with the denominator stated per dataset in `docs/LINKAGE_COVERAGE.md`. `report` measures, `apply` writes the doc, `baseline` records the floor, `selftest` proves it fires. 62 carries it as `linkage_metrics_below_floor`. **A low figure is not automatically a defect** - `natural-resources` reads 6.24% because ONRR publishes in AGGREGATE, and is 73.67% of the rows that CAN name a recipient |
| `py -3 code/1140_linkage_close.py verify` | the 2026-09-02 linkage closures - 591 bills, 154 McGrath rows, 2,034 stranded rulings, 163 bridged identifiers, 4 sibling repoints. **An IN-PLACE enricher on three flagships**: a rebuild of any of them reverts its share, and this is what tells you to re-run `apply` |
| `py -3 code/1112_harvest_coverage_matrix.py verify` | what was actually looked for, per entity, per thing. **`untouched = 0` in `docs/SHARD_COVERAGE.md` is true and measures web-map membership, not harvest** — per thing, untouched runs 373 to **1,439 of 1,555 (92.5%) for CAGE / UEI / DUNS** |

**Never re-baseline to clear a red gate.** `--baseline` records a floor while
GREEN. A gate you stepped around is a gate the next six sessions also step
around.

**A red gate is not automatically yours.** Name the owner with a measurement —
which table moved, by how many rows, and which script wrote it — the way the
gate-failure entries in `AGENTS.md` do. Then say so in writing.


<!-- BEGIN IDENTITY-AND-DELIVERY-SCRIPTS-2026-09-03 -->
## The five scripts added 2026-09-03, and which question each owns

Owner, 2026-09-03: *"It sounds like you're also making a lot of stuff, so maybe you
can consolidate code and reconcile it and fact check."*

Checked for duplication rather than assumed: there is none, and the division below
is the reason. **Before writing a sixth, find your question here.** Two of these
already exist because someone did not.

| script | the one question it answers | does NOT |
|---|---|---|
| `1164_native_legal_forms_classifier` | *what legal form is this entity, and what does the statute say it can be?* 16 forms, each with a fetched citation | **detect** uid collisions — it defers to 1167 in code and in its docstring |
| `1165_delivered_publication_audit` | *did the publication RULES hold in the file the customer receives?* NEVER, DROP_COLS, lineage, mask, quarantine, the subaward fence, retired NEID values | judge whether the data is internally consistent |
| `1166_owner_queue_card_builder` | *is this a question only the owner can answer?* Five gates that suppress everything already answered | apply any ruling |
| `1167_cedar_uid_identity_collisions` | *does one `cedar_uid` name more than one entity?* ALIAS / TYPO / MERGE, plus `repoint` | decide which head survives on statute — that is 1164 |
| `1168_harmonization_audit` | *do the 13 datasets agree with each other?* Column names, value vocabularies, codebook truth, duplicates | check publication rules |

`1165` and `1168` both stream `dist/customer` and that is not duplication: one asks
whether the rules were applied, the other whether the answers are mutually
consistent. A file can pass either and fail the other.

**The ordering that matters.** `1167 repoint` before `1137 build`, always. Identity
collisions make the NEID→uid map ambiguous, and an ambiguous map is what leaves
retired identifiers in a delivered file. Measured on 2026-09-03: 13 colliding uids
left **1,954** untranslatable values; repointing 68 ledger rows took the collisions
to 2 and the untranslatable values to **0**. One of those 68 rows — a single
`Oneida Nation (Wisconsin)` row keyed to the New York uid — was on its own
responsible for **290 retired identifiers across four delivered datasets**.
<!-- END IDENTITY-AND-DELIVERY-SCRIPTS-2026-09-03 -->
