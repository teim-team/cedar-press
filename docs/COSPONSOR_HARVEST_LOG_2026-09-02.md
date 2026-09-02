# Who BACKED a Native bill — cosponsor harvest build log

*Built 2026-09-02 by `code/1145_cosponsor_harvest.py`. Every number below was
re-derived from the files on disk after the last `apply`. Re-derive before
quoting: `py -3 code/1145_cosponsor_harvest.py report`.*

**Collection:** `legislation`. **Four** new tables, **57,061 rows**, all reached
by the existing
`^(bill_|native_bill|congress|member_positions|native_issue_litigation)` pattern
in `code/500_build_architecture_map.py` — no `COLLECTIONS` edit needed and none
is an ORPHAN.

| table | rows | grain | script |
|---|---:|---|---|
| `native_bill_cosponsors.csv` | **18,987** | one (bill, cosponsor, sponsorship date) | `1145` |
| `native_bill_cosponsor_coverage.csv` | **3,069** | one per bill in `native_bills.csv` | `1145` |
| `native_bill_actions.csv` | **31,936** | one published legislative action | `1150` |
| `native_bill_action_coverage.csv` | **3,069** | one per bill in `native_bills.csv` | `1150` |

> **The last two cost ZERO network requests, and this document's own work queue
> nearly sent someone to fetch them.** See *"The second orphan"* at the foot of
> this log.

---

## The gap this closes, and the half of it that was already on disk

`native_bills.csv` has carried a `cosponsor_count` since 2026-08-05 — **a
number**. Who those cosponsors *were* had been attempted for **275 of 3,069
bills** by an earlier, unnumbered pass, and the result was sitting in
`data/clean/_cosponsors.csv`: a leading-underscore file that

* matches no `COLLECTIONS` pattern in `code/500_build_architecture_map.py`,
* reaches no dataset contract in `code/512_build_dataset_contracts.py`,
* appears in no codebook fragment,

i.e. a table that was built and could never ship. It is the exact
`ON_DISK_NOT_PROMOTED` shape `docs/AGENT_FIELD_GUIDE.md` §5 describes, found by
`py -3 code/1050_preflight.py ondisk cosponsor` before a single request was
made.

**The two halves, measured:**

| | bills | rows |
|---|---:|---:|
| legacy `_cosponsors.csv`, a roster present | 162 | 5,318 |
| legacy fetch log, attempted, no roster | 113 | — (`zero_cosponsors_reported` 71 · `no_api_record` 41 · `http_520` 1) |
| **never attempted at all** | **2,794** | — |

So: `ON_DISK_NOT_PROMOTED` for 162 bills, `NOT_ACQUIRED` for 2,794. This pass
does both, and promotes the orphan rather than leaving a second copy behind.

## The pull

Congress.gov API v3, `/v3/bill/{congress}/{billType}/{billNumber}/cosponsors`.
Key `CONGRESS_API_KEY`, resolved by `code/cedar_keys_env.py` from
`D:\Archive\votingpatterns\.env` — **never written into this repo**;
`docs/API_KEYS.md` holds names only. One poller,
`logs/_HOSTLOCK_api.congress.gov.json`, 0.45 s pacing, three-hour hard stop,
checkpointed one JSON object per bill so a re-run downloads nothing it holds.

    3,053 bills fetched in 63.9 minutes at 0.80/s
    ok 2,172 · zero_cosponsors_reported 881 · no_api_record 0 · errors 0
    no 429, no 503, no backoff taken

**The keyed budget is 5,000 requests/hour and the run spent ~3,050 in 64
minutes**, so it fits one hourly window with room. Rate limiting was never
reached, which is worth recording because `docs/AGENT_FIELD_GUIDE.md` §3 notes
that a 403 from `api.congress.gov` once turned out to be a missing User-Agent
rather than an access restriction — this run sends one.

## What landed

    18,987 rows · 2,175 bills · 1,905 distinct members · Congresses 93–119

| cut | value |
|---|---|
| `is_original_cosponsor` | Y **9,239** · N **9,748** |
| `sponsorship_withdrawn_date` non-blank | **28** members who left a bill |
| party | D 12,060 · R 6,871 · I 49 · ID 7 |
| most frequent backers | Rep. Cole, Tom [R-OK-4] **267** · Sen. Inouye, Daniel K. [D-HI] **193** · Rep. Young, Don [R-AK-At Large] **163** · Rep. McCollum, Betty [D-MN-4] **150** · Sen. Murkowski, Lisa [R-AK] **133** · Sen. Tester, Jon [D-MT] **113** |

`cosponsor_lookup_status` over all 3,069 bills: `ok` **2,175** ·
`zero_cosponsors_reported` **886** · `SOURCE_DOES_NOT_PUBLISH_ON_BILL_ENDPOINT`
**8**. **`NEVER_CHECKED` is 0.**

> **The coverage table is the point, not an afterthought.**
> `native_bill_cosponsors.csv` alone cannot tell a bill that had **no backers**
> apart from a bill **nobody looked up**, and those are different facts about
> Indian Country legislation. 886 Native bills genuinely attracted zero
> cosponsors; that is a finding, and it is only legible because the denominator
> table carries all 3,069 rows.

## The legacy file was corroborated, not overwritten

Every one of the 162 legacy bills was re-fetched, and the two rosters compared
on the exact set of bioguide ids:

    162 agree · 0 disagree

So the earlier pass is fully validated and fully superseded, and `record_basis`
is a single value (`congress_gov_api_v3_cosponsors_1145`) on all 18,987 live
rows. **The column stays** — the moment a fetch is incomplete, a legacy row
becomes the only record for that bill and the reader has to be able to tell.

**The earlier pass's 41 `no_api_record` verdicts did not reproduce.** Every
canonical bill answered HTTP 200 first time. Recorded rather than re-litigated:
a source that answered "no such bill" in one session and answered normally in
another is a fact about that session, not about the bill.

## The cross-check against `native_bills.cosponsor_count`, and what its 24 disagreements are

`count_agrees_with_native_bills` compares the roster length against the count
`native_bills.csv` has carried since 2026-08-05 — two independently obtained
numbers for the same thing.

| | n |
|---|---:|
| `Y` | **2,021** |
| `N` | **24** |
| `NOT_TESTABLE` | 1,024 |

**All 24 disagreements are 119th-Congress bills, and in 23 of 24 the source
count is HIGHER.** The 119th Congress runs to January 2027 and is still sitting.
These are not errors in either number: they are cosponsors who signed on
*after* the 2026-08-05 build. `119-hr-7325` went 16 → 20; `119-hr-7705` 10 → 14.
The one exception, `119-s-4315` (2 → 1), is a withdrawal.

> **This is a freshness seam, not a defect, and it is the reason
> `native_bills.cosponsor_count` should not be used as a denominator for the
> current Congress.** Use `native_bill_cosponsor_coverage.n_cosponsors_retrieved`
> and read `fetched_date` beside it.

`NOT_TESTABLE` means one side is blank and **never** that the two agreed:
`native_bills.cosponsor_count` is blank on **1,024** bills, spread evenly across
Congresses 103–117 rather than concentrated anywhere. **This pass recovered a
roster for 130 of them — 5,157 cosponsor rows on bills whose count column has
always been empty.**

## What is deliberately not here

* **The sponsor.** `native_bills.sponsor` / `sponsor_bioguide_id` hold the
  sponsor; a cosponsor is a different relation. Unioning them without saying so
  inflates every per-member count by one bill, and the grain declaration in
  `512` says so.
* **8 bills the source does not carry.** `hre` (2), `hjr` (1), `treatydoc` (2),
  `treatydocno` (3) are not canonical congress.gov slugs and treaty documents
  are not on `/bill` at all — established by `code/1092` for titles, and it
  holds for cosponsors. They are **not** coerced into a slug that would return
  HTTP 200 for the wrong bill. `SOURCE_DOES_NOT_PUBLISH_ON_BILL_ENDPOINT`:
  a fact about the world, not a Cedar deficiency.
* **No personal data.** The API returns `firstName`, `middleName`, `lastName`,
  and a member URL. Only `fullName` and `bioguideId` are carried, plus party,
  state and district — a member of Congress in their public role. No contact
  field exists on this endpoint and none is sought.
* **No `cedar_uid`.** Members of Congress are not Cedar spine entities.
  `native_bills_entity_bridge.csv` already links bills to tribes; this table
  links bills to legislators, and joining the two is the analysis, not the
  acquisition.
* **Committees and subjects.** Same host, same key, same shape, ~3,000
  requests each. Not started — one poller per host, and this run held
  `api.congress.gov`. Queued in `docs/WORK_QUEUE.md` under
  `MONEY-FED-2026-09-02`.
* **Actions** were on this list as a fetch and are now four paragraphs down as
  a promotion. Read that before queueing anything else against this host.

## Verify, and the proof it fires

```
py -3 code/1145_cosponsor_harvest.py verify     # exits 1 when it did not land
py -3 code/1145_cosponsor_harvest.py selftest   # PASSES, 6/6 fired
```

A **landing** check, not a conservation check (`AGENT_FIELD_GUIDE` rule 5):

| invariant | fails when |
|---|---|
| **CS-1 / CS-1b** | fewer than 18,500 rows or 2,100 bills — the harvest did not land or was reverted |
| **CS-2** | a `bill_id` is not a `native_bills.csv` key |
| **CS-3** | the coverage key set is not exactly `native_bills.csv`'s, or a bill repeats |
| **CS-4** | `(bill_id, bioguide_id, sponsorship_date)` collides |
| **CS-5** | a row carries no `cosponsor_bioguide_id` — so the key can never hold a blank |
| **CS-6** | a row carries no `record_basis` |

Floors are set just under the measurement and are a claim that the work landed.
**They are never re-baselined to clear a red gate.**

`selftest` injects each breach, asserts exit 1 **and** that the named invariant
is what fired, restores from a literal path (never a glob — the 163 incident),
and asserts exit 0. Result 2026-09-02: **6 of 6 FIRED, restored, verify exit 0.**

## Re-running

`fetch` is resumable and idempotent: one JSON per bill under
`data/raw/external/congress_gov/1145_cosponsors/<congress>/<type><number>.json`
plus an append-only `_fetch_log.jsonl`. `apply` is a full rebuild from that
cache and takes no network. **There is no in-place enricher on either table**,
so there is no rebuild/enrich ordering to declare and `apply` may be re-run at
any time. To refresh the 119th Congress alone, delete that Congress's cache
directory and re-run `fetch`.


---

## THE SECOND ORPHAN — actions were never a fetch, and this log said they were

`code/1150_bill_actions_promote.py`, same workstream, same evening, **zero
network requests.**

`docs/WORK_QUEUE.md` item 6 — written by this workstream about ninety minutes
before — listed *"bill ACTIONS and COMMITTEES for the 3,069 Native bills… ~3,000
requests, ~1 hour."* **`data/clean/_bill_actions.csv` already held 31,936
actions over 3,061 bills**, fetched 2026-08-06, with
`_bill_actions_fetch_log.csv` recording `ok` on all 3,061. A third file,
`_bill_metadata_backfill.csv` (128 rows), sits beside them.

They were invisible for **exactly the reason `_cosponsors.csv` was**: a leading
underscore, matching no `COLLECTIONS` pattern, so no collection, no contract, no
codebook and no listing anybody reads. Two orphans, one directory, one cause.

**And the search that was supposed to catch this did not.**
`py -3 code/1050_preflight.py ondisk cosponsor` found `_cosponsors.csv`
immediately, because "cosponsor" was the word in the filename. Nobody ran
`ondisk actions` — the queue entry had already decided actions were a fetch, so
there was nothing to look up. They surfaced only because
`62_no_regression_check.py` printed a `data/clean` listing while diagnosing an
unrelated gate.

> **The rule this earns, and it is a sharpening of field-guide §5:** the four
> states are assigned *per item*, and an item is usually named by the person who
> already believes they know its state. `ondisk` answers the question you ask
> it. **Before writing `NOT_ACQUIRED` next to something, run `ondisk` on the
> noun in the row — and on the file-naming convention the neighbours use.** One
> `ls data/clean/_*.csv` would have found both.

### What landed

    31,936 actions · 3,061 bills · 1973-01-03 to 2026-08-05

| `action_type` | n |
|---|---:|
| Floor | 10,324 |
| IntroReferral | 9,775 |
| Committee | 7,044 |
| ResolvingDifferences | 1,685 |
| Calendars | 1,089 |
| President | 894 |
| BecameLaw | 565 |
| NotUsed | 341 |
| Discharge | 150 |
| Veto | 33 |
| *(blank)* | 36 |

**283 of 3,069 Native bills became law** — a 9.2% enactment rate, derived from
the presence of a `BecameLaw` action and carried as `became_law` on the
coverage table. No Cedar table stated it before. **1,135 action rows carry a
recorded-vote reference**, which is the join surface between this table and
`bill_votes.csv`.

`action_lookup_status`: `ok` **3,061** ·
`SOURCE_DOES_NOT_PUBLISH_ON_BILL_ENDPOINT` **8** · `NEVER_CHECKED` **0** — the
same 8 non-canonical slugs as the cosponsor pull.

### No key, and the collision is the SOURCE's

Measured on the full 31,936 rows:

| candidate key | distinct | duplicate groups | surplus rows |
|---|---:|---:|---:|
| `(bill_id, action_date, action_text)` | 27,513 | 4,131 | 4,423 |
| `+ action_code` | 31,361 | 398 | 575 |
| **the entire published tuple** | **31,803** | **111** | **133** |

The 133 are byte-identical repeats congress.gov itself publishes — two
`Conference held.` rows against `99-s-2638` on 1986-10-10, two identical
`DEBATE - The House proceeded with one hour of debate.` rows against
`101-hr-2939`. The publisher supplies no ordinal to tell them apart.
**Nothing was collapsed**; the table is declared in `GRAIN_OPEN` with the
question attached, and `source_system` is on the row because *two chamber
systems recording one event* is the reason many of the near-collisions exist.

### Verify

```
py -3 code/1150_bill_actions_promote.py verify     # exits 1 if it did not land
py -3 code/1150_bill_actions_promote.py selftest   # PASSES, 5/5 fired
```

BA-1 floors (31,000 rows / 3,000 bills) · BA-2 every `bill_id` is a
`native_bills.csv` key · BA-3 coverage is exactly the 3,069 · BA-4 no action
without a date · BA-5 no row without a `record_basis`. **There is no `fetch`
subcommand and that is deliberate** — nothing here needs the network, and giving
the script one would invite a re-pull of 31,936 rows that are already right.
