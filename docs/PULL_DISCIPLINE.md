# Pull Discipline — one poller per host

*Written 2026-08-05, after four independent pollers were left retrying against a
host that was blocking us **because of** our retry rate.*

**Read this before writing any script that fetches from a remote host.**

---

## What happened

Four agents ran concurrent pulls against `api.usaspending.gov` on the same day.
The host began refusing at the edge — instant `RemoteDisconnected` on connect,
not a timeout, which is the signature of an IP-level block rather than a slow
server.

Each agent then did the individually sensible thing and left a resumer polling
every 300 seconds:

```
code/30_wait_and_pull.py          probe  8/22 -> BLOCKED
code/37_wait_then_pull.py         blocked
code/43_funding_forward_fill.py   "host still refusing; sleeping 300s"
code/43_resume_subaward_pull.sh   probe  4    -> edge refusing
```

Four processes, none aware of the others, **quadrupling the probe rate against a
host that was blocking us for probe rate.** One agent had already diagnosed the
cause — *"six concurrent workers tripped it; I stopped the puller rather than
let retries extend the block"* — and its own resumer then became one of four.

Nobody did anything unreasonable. The failure is structural: no agent could see
the others.

---

## The rules

### 1. One poller per host. Ever.

Before starting a retry loop, check whether one is already running:

**On Windows, `ps aux` CANNOT answer this question.** Git Bash's `ps` does not
carry command lines, so `ps aux | grep -iE "wait_|resume_|_pull"` returns
nothing while pullers are running. On 2026-08-05 that exact command returned
`0` with **four** puller processes live, and an agent was told the host was free
on the strength of it. A check that cannot observe the thing it claims to check
is worse than no check, because it manufactures confidence.

Use `Win32_Process.CommandLine`:

```bash
ls logs/*resume*.log logs/*wait*.log logs/_HOSTLOCK_* 2>/dev/null

py -3 -c "
import subprocess, re
out = subprocess.run(['wmic','process','where',
    \"name like '%python%' or name like '%py.exe%'\",
    'get','ProcessId,CommandLine','/format:csv'],
    capture_output=True, text=True).stdout
for line in out.splitlines():
    m = re.search(r'(code[/\\][\w]+\.py)', line)
    pid = re.search(r'(\d+)\s*$', line.strip())
    if m and pid: print(pid.group(1), m.group(1))
"
```

PowerShell equivalent: `Get-CimInstance Win32_Process | Select ProcessId, CommandLine`.

If a poller for that host exists, **do not start a second one.** Write your
checkpoint, log that you are deferring to the existing poller, and stop.

### 2. Claim the host in a lock file

Before polling, write `logs/_HOSTLOCK_<host>.json`:

```json
{"host": "api.usaspending.gov", "pid": 1234,
 "script": "code/43_funding_forward_fill.py",
 "started": "2026-08-05T21:36:03Z", "queue": ["fy2024", "fy2025", "fy2026"]}
```

Any later script that wants the same host **appends its work to `queue` and
exits.** The holder drains the queue. A lock older than 6 hours with a dead PID
may be taken over.

### 3. Back off exponentially, and cap the attempts

A fixed 300s retry is not backoff — it is a metronome, and to an edge filter it
looks exactly like the traffic that earned the block. Double the interval each
failure: 60s, 120s, 240s, up to 30 minutes. Stop after ~2 hours and report the
block rather than polling all night.

### 4. Distinguish the three failure shapes

They call for opposite responses, and treating them alike is how a soft
throttle becomes a hard block:

| Shape | Looks like | Do |
|---|---|---|
| **Edge block** | instant `RemoteDisconnected` / curl `000`, < 1s | **Stop.** Back off long. More requests extend it. |
| **Throttle** | HTTP 429, or `Retry-After` | Honour `Retry-After` exactly. |
| **Server slow** | timeout after 30s+ | Retry is fine; lower concurrency. |

Probe with the *cheapest* endpoint the host offers, never with the real job.

### 5. Never re-submit a job the server already accepted

USAspending bulk downloads are server-side jobs. Re-submitting discards
completed server work and costs the queue position. Persist the job token and
recover it; do not start over because the download leg failed.

### 6. Checkpoint before the first request, not after the last

Every puller writes `_state.json` with what is done, what is queued, and the
job tokens outstanding. A killed poller must lose nothing — that is what makes
rule 1 safe to enforce, because stopping a redundant poller then costs nothing.

### 7. Serialise across agents by fiscal year, not by agent

Two agents pulling different fiscal years from one host are still one host.
Split the work by year, and have a single process walk the years.

---

## If you find yourself blocked

1. Confirm it is host-specific — probe a **different** host. If `lda.gov`
   answers and `usaspending.gov` does not, it is not the network.
2. Count the pollers. Stop all but one.
3. Let the survivor back off exponentially.
4. Do the work that does not need that host. There is always some — matching,
   codebooks, review queues, documentation.
5. Report the block plainly, with the probe evidence. A block is a finding, not
   a failure.

## Check the shape of the data you already have, not just its dates

Not a rate-limit rule, but it belongs with them because it is the other way a
pull silently goes wrong.

The federal funding spine looked like full-universe assistance data. It is not:
across all 476,924 rows `business_types_code` takes exactly three values (I, J,
K) - USAspending Recipient Type = tribal. **A blind full-universe pull for the
missing years would have produced a population mismatch that no total, count or
date range would reveal.** The join would work, the series would look
continuous, and the later years would quietly contain a different universe.

So before extending any dataset forward: profile the categorical columns of what
you already have, find the implicit filter, and reproduce it. Then validate the
reproduction against years you ALREADY hold before pulling new ones - here,
FY2022 came back +0.11% and FY2021 +0.40% against the spine, which is what made
the filter trustworthy.

Related API trap: `recipient_type_names` does **not** validate its input. A
bogus value returns HTTP 200 with an empty result set, not an error. An empty
result is not evidence of absence; it may be evidence of a typo.

## Hosts with known limits

| Host | Limit | Note |
|---|---|---|
| `api.usaspending.gov` | per-IP cooldown, undocumented | **Measured 2026-08-05: reachable at 17:05, hard-refusing at 17:17 with FOUR pullers running, clear again ~62 minutes after traffic dropped.** It is a cooldown, not a ban - so the fix is to stop polling, not to keep probing. Any doc claiming this host is "blocked" is describing a cooldown someone sat through. |
| `lda.gov` | 15/min anon, 120/min keyed | Key is in the master `API_KEYS.md`. Use it. |
| ProPublica Nonprofits | soft, undocumented | Rate-limited a 185-row EIN pass; retry slowly. |
| `web.archive.org` | tolerant | The right fallback when an origin blocks. |


---

## BACKOFF BOUNDS THE RATE, NOT THE RUN (2026-08-08)

Exponential backoff is necessary and **not sufficient**. An agent had correct
60s→30min backoff and still built a runaway: with 16 years × 6 attempts and no
global stop, it would have probed a refusing host for hours — and extended the
block for a *different* agent sharing the same IP.

**Every poller needs two stops that backoff cannot provide:**

1. **`RUN_DEADLINE`** — no attempt may START more than ~2h after the run began.
   Check it before each attempt **and** before each backoff sleep, or a long
   sleep carries you past the deadline anyway.
2. **Stop on first refusal when nothing has succeeded.** If the first object
   exhausts its backoff and no object has landed, the **host** is refusing, not
   that one object. Trying the remaining fifteen is fifteen more ways to learn
   the same fact. Exit on a distinct code so it reads as a finding, not a crash.

## A SHARED LOCK FIELD MUST NOT BE AMBIGUOUS (2026-08-08)

The same build wrote `any_success: false` into the shared host lock when it
skipped years already on disk — no network activity at all. **Another agent
reading that lock would conclude the host was refusing.** A false "host is
down" is as damaging as a false "host is up": it stops work that would have
succeeded.

Split ambiguous status into fields that cannot be misread:

```
downloaded_this_run      objects actually fetched now
already_on_disk_skipped  objects present, no request made
refused_by_host          objects the host declined
```

**`downloaded_this_run: false` with `refused_by_host: []` is NOT a block** — it
means there was nothing to do. Any lock field another agent will act on must be
unambiguous on its own, without knowing what the writer was doing.

## WHO CAUSED THE BLOCK GOES IN THE LOG

The same agent recorded that **its own** six large objects in twelve minutes
triggered the edge block that then stopped a peer. That belongs in the log every
time. A block with no attributed cause gets re-triggered by the next agent that
assumes the host is simply flaky.

---

## AN ACCEPTED TOKEN IS NOT A WORKING JOB (2026-08-12)

`api.usaspending.gov` answered **HTTP 200** and returned a `file_name` for
**nine** consecutive `bulk_download` submissions. **Every one of them then failed
server-side** with the generic message `"An error occurred."` Nothing in the
acceptance response predicted it, and a puller that treats acceptance as success
reports nine jobs in flight and discovers hours later that it has nothing.

**Buy the cheap answer before the expensive one.** `code/121_pull_subawards_api.py`
now carries a `canary` stage: ONE two-day job, which generates in ~37 seconds on
this endpoint. It establishes whether the download fleet is producing files at
all, for the price of one submission instead of five fiscal years.

### Design your probes so their outcomes ELIMINATE explanations

Three two-day probes settled in twenty minutes what could have been a day of
redesign, because each one was chosen to kill a specific hypothesis:

| probe | kills |
|---|---|
| two-day job | "the jobs are too big" |
| a year we ALREADY downloaded successfully | "that date window is broken" |
| the same window with `prime_award_types` instead of `sub_award_types` | "this endpoint/filter is broken" |

All three failed → **the whole service was down.** The plausible-looking wrong
moves that this ruled out — split the years, change the payload, add workers —
were all on the table beforehand.

### Four states, not three

`downloaded_this_run` / `already_on_disk_skipped` / `refused_by_host` do not
cover this case. Add:

```
accepted_then_failed_server_side   the API returned 200 and a token, and the
                                   server then did not build the file
```

`refused_by_host: []` with nothing downloaded would otherwise read as "there was
nothing to do", which is the opposite of what happened.

**Rule 5 does not bind on a failed job.** Never re-submitting an accepted job
protects *completed server work*. A job reporting `status: failed` is a corpse;
re-submitting it discards nothing. Keep the dead token as evidence and submit
fresh.

## A POLLER IS A PROCESS THAT MAKES REQUESTS (2026-08-12)

Two false stops in one run, both from the peer check itself:

1. **`py.exe -3 script.py` LAUNCHES `python.exe script.py`.** A self-check on
   `os.getpid()` alone sees its own launcher and defers to itself. Walk the
   process ancestry via `ParentProcessId` and exclude the whole tree.
2. **Matching on the script name counted this build's own `tail -f` log
   monitors — and their bash wrappers — as four live pollers.** A log watcher
   issues no HTTP. Select `Name` as well as `CommandLine` and require the
   process image to be `python.exe` / `pythonw.exe` / `py.exe`.

Rule 9 says `ps aux` cannot answer this on Windows and manufactures false
confidence. These two are the mirror image: a check that is too eager
manufactures false *blocks*, and a false "host is busy" stops work that would
have succeeded just as surely as a false "host is free" causes one.

## HOSTNAMES ARE NOT RATE-LIMIT BUDGETS (2026-08-12)

`api.usaspending.gov` and `files.usaspending.gov` are different hosts and
`114_pull_prime_archive.py` says so correctly in its docstring. **They were
refusing the same IP within two minutes of each other**, with the identical
sub-second `RemoteDisconnected` signature. Treat them as one budget when
deciding whether to add load.

Two practical consequences:

* A peer on the *sibling* host should not block your submissions, but it **must
  gate your downloads** if that is where your objects land. Deferring a download
  is free — a generated object stays retrievable by its `file_name`.
* **Where a peer is already polling, its LOG is the cheapest probe available**,
  and strictly better than adding a second prober. Reading
  `logs/114_prime_archive.log` answered "has the edge cleared?" at a cost of
  zero requests, for the whole 32 minutes of the block.

---

# TARGETED PULLS: THE SELECTION DOCTRINE (2026-08-26)

*Written from `code/276_measure_discovery_gap.py`, which is READ-ONLY and made
zero network requests. Every figure below is recomputable from
`docs/DISCOVERY_GAP.json` and the files it names.*

The owner, on the strategy this project has been half-following:

> *"Whether by unique identifier or names, we want to pull those records and
> then maybe see if anything is missing, so we don't always need the full
> universe of all contracts. I assume you are doing this?"*

**He is right, and it was already half-implemented — inconsistently, by five
pullers doing three different things.**

| script | selects on | leg |
|---|---|---|
| `44_pull_contracts_transactions` | ledger identifiers | IDENTIFIER only |
| `114_pull_prime_archive` | a BGOV export pre-filtered "where Native entities were expected" | FILTER only |
| `141_pull_sam_contract_awards` | `awardeeBusinessTypeName`, a partial string match | FILTER only |
| `121_pull_subawards_api` | identifier + declared parent UEI | IDENTIFIER only |
| **`115_pull_assistance_archive`** | **union of both, recorded per row** | **BOTH — the correct design** |

115's own docstring already stated the principle nobody generalised: filtering
on ledger identifiers ALONE *"would silently change what the series counts: it
would add ledger-known corporations that carry no tribal recipient-type code,
and drop tribal-coded recipients whose UEI the ledger has never seen."*

## THE RULE

**A targeted pull selects on `TYPE_FILTER OR KNOWN_IDENTIFIER`, and records
which leg fired on every row it writes.**

- The **type filter** is the source's own categorisation — USAspending
  `business_types_code` I/J/K, an FPDS Native business-type flag, a set-aside
  family, `entity_type = tribal`. It finds entities we have never heard of and
  misses entities that do not self-certify.
- The **known identifier** is our ledger — UEI, and everything that resolves to
  a UEI. It finds entities that never self-certify and **cannot find anything
  new, ever.**
- Neither leg is a superset of the other. **The union is the population; either
  leg alone is a different dataset wearing the same name.**

**A puller that uses only one leg must SAY SO IN ITS DOCSTRING**, in a
`SELECTION DECLARATION` block naming the leg used, the leg missing, and the
`population_basis` value every row it yields will carry. `44` now carries one;
so does its `_state.json`, under `selection`.

**And it must record the leg on every row, in a `population_basis` column**, as
115 already emits. That column is not bookkeeping. It is what let this
measurement exist at all: because 115 stamped the leg per row, the two routes
could be compared on the shared population years later, by a different agent,
with no re-pull. A pull that does not record its own selection cannot be
audited without repeating it.

Where a puller retrieves server-built objects and cannot stamp rows itself —
`44` collects zips — it ships the per-identifier provenance beside them
(`_pull_universe.csv`) so the merge can stamp `population_basis` instead. The
obligation moves; it does not disappear.

## THE CENTRAL LIMITATION

**An identifier-seeded pull can never discover an entity we do not already
know.** This is not a defect to be fixed inside any puller. It is the defining
property of the selection, and the only honest response is to measure it, label
it, and run something else that looks outside.

It is why **all 209,495 FY2023–FY2026 prime rows are `attributed_flag = 1`**
(`docs/CICD_BENCHMARK.md` INTERNAL-02). That is not a quality result and must
never be published as one. Those years were pulled filtered to known
identifiers, so **100% attributed means 0% discovered**. It is also why the
entire unattributed reconciliation backlog is structurally FY2000–2022: the
recent years contain no unknowns because nobody looked for any.

## THE MEASUREMENT — TWO INSTRUMENTS, AND THEY AGREE

`docs/CICD_BENCHMARK.md` UNDERCOUNT-01 sized the **flag-side** blind spot:
**$140.00B, 57.2% of attributed dollars, 195 of 498 entities** that Cedar
attributes by hand and no set-aside flag ever sees. That is the cost of running
the type leg alone. **This is the identifier-side answer — the cost of running
the identifier leg alone — and it had never been sized.**

### Assistance — the only place both legs already ran, per row

115's per-FY archive extracts, FY2007–FY2026, 701,458 rows, `population_basis`
stamped at pull time. Entity = distinct `recipient_uei`.

| | entities |
|---|---:|
| found by the **TYPE FILTER only** | **4,866** |
| found by the **IDENTIFIER only** | 598 |
| found by **both** | 1,392 |
| **union** | **6,390** |
| an identifier-only pull would have found | **1,524 (23.85%)** |

> **76.15% of the assistance recipient universe is invisible to an
> identifier-only pull.** The type filter multiplies the entities found by
> **4.19x**. Those type-only rows carry **$33.53B of $219.10B — 15.30%**.

The per-year figure is stable at roughly half the universe every year (FY2012
25.2% at the low, FY2024 53.45% at the high) — a standing property of the
selection, not an artefact of one year.

### Prime — the flag route is on disk and nobody had used it as one

`Data Request 4-5-2023 File 1.csv` is HigherGov's FLAG-AT-AWARD extract —
*"every transaction from FPDS where they flagged the contract as Tribal Owned,
Alaskan Native, etc"* — 1,101,796 rows, FY1979–2023. It carries the **true
USAspending business-type self-certification columns**, which
`prime_contracts.csv` does not.

| | entities | dollars |
|---|---:|---:|
| carry a Native business-type flag | **12,643** | $238.80B |
| already in `44`/`114`'s selection set | 2,886 | — |
| rescued only by the declared-parent leg | 38 | — |
| **outside the selection set entirely** | **9,719 (76.87%)** | **$70.96B** |

File 2, the SAM current-registration route, agrees in direction: **4,251 of
6,582 (64.59%), $59.37B**.

> **76.15% (assistance) and 76.87% (prime), from two unrelated sources, two
> different programmes and two different instruments.** Neither was tuned to
> the other. Take the number as **roughly three quarters of the entity universe
> is unreachable by identifier selection alone.**

`CICD_BENCHMARK.md` UNDERCOUNT-05 warns that a flag-defined universe cannot
measure what the flag MISSES. True, and it does not bind here: this measurement
runs the other way. A flag-defined universe is exactly the right instrument for
asking what the flag FINDS.

### THE DECOMPOSITION — and the two sides are OPPOSITE

Being outside the selection set is not the same as never having been seen. Tier
C holds **9,335 UEI rows, 9,320 of them `attribution_method = unmatched`**, all
sourced from `master_tribal_entity_registry.csv`: identifiers **harvested and
never adjudicated**. Splitting on that changes what the number means, and it
splits the two sides in opposite directions:

| | prime (File 1) | assistance |
|---|---:|---:|
| outside the selection set | 9,719 | 4,866 |
| …**on file at tier C, unadjudicated** | **9,154 (94.2%)** | 156 (3.2%) |
| …**absent from the ledger entirely** | **565 (5.8%)** | **4,696 (96.5%)** |

**On the contracting side the gap is an ADJUDICATION BACKLOG. On the assistance
side it is genuine non-discovery.** The ledger was built from contracting
sources, so it has already *seen* almost every flagged contractor and simply
never ruled on it — while the assistance world of tribal governments, housing
authorities, colleges and consortia is 96.5% unrecorded.

That table is what makes the sweep below cheap, and it is why "run a discovery
sweep" and "work the review queue" are **different answers to different halves
of the same number**. Getting them the wrong way round buys an expensive pull
to re-find 9,154 entities already on disk.

**And a self-certification is not a determination.** Goldbelt Raven, an ANC
subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`. Every entity
counted above is a **candidate for adjudication**, never a row to attribute.
The number measures the SEARCH SURFACE an identifier-only pull cannot see. It
is not a count of missing Native entities and must never be published as one.

## THE PERIODIC DISCOVERY SWEEP

Full-universe pulls are expensive and mostly unnecessary — the owner's instinct
is right. But **something must periodically look outside the known set, or the
spine can only ever confirm itself.** A spine that only re-reads its own members
has no error term.

The decomposition above says the cheapest sufficient sweep is **mostly not a
pull at all.**

### Tier 1 — ZERO network, run FIRST, monthly

**Adjudicate tier C.** 9,335 harvested-and-unmatched UEIs, of which **9,154 are
flag-identified contractors already on disk** carrying a share of $70.96B.
Nothing needs to be fetched; `docs/DISCOVERY_GAP.json` names them. This is 94.2%
of the prime-side gap and it costs zero bandwidth.

**Re-read the four extracts we already own** on the same schedule — File 1
(flag), File 2 (registration), the IDVs, and 115's `_unresolved.csv` per year.
`docs/PRE2007_SPENDING_SOURCES.md` closes on the right line: *four of seven
findings came from re-reading files this project already owned.*

Cost: **zero requests.** Expected yield: the 9,154 backlog on first run, then
~0 new per month.

### Tier 2 — the type leg, already running, costs nothing extra

**115 already emits both legs. Keep it that way and never "optimise" it down to
the identifier leg.** Its `recipient_type` leg is the only thing standing
between this project and losing 4,696 assistance entities, and it is free — the
archive object has to be streamed either way, so the filter is a predicate, not
a request.

For `44` the type leg is **not available on its endpoint** (measured: no
`recipient_type_names` combination reproduces the population, +4.56% against a
+0.11% bar, two-directional). That is exactly why 44 carries a
`SELECTION DECLARATION` instead, and why the prime type leg has to come from
Tier 3.

Cost: **zero incremental requests.** Expected yield: ~1,100–1,200 assistance
entities per fiscal year that no identifier route would find.

### Tier 3 — the annual outside look, ONE bounded pull per source

**Name-token sweep against `entity_name_harvest.csv`** (31,728 rows, on disk,
and **stale since 2026-08-05** — refreshing it is itself a Tier-1 job).

Then **one** partitioned FPDS-NG ATOM slice per year, filtered to the Native
business-type flags, as the prime type leg 44 cannot provide. Preconditions,
all already documented and all binding:

- the feed has a **hard, silent 400,000-record paging ceiling** — it serves
  nothing past offset 400,000 and returns HTTP 200 with an empty entry set, so
  **partition every query below 400k and compare retrieved against advertised on
  every partition** (AGENTS.md concurrency rule 7);
- page size is fixed at 10 and `&size=100` is ignored — a full FY1999–2007 pull
  is ~1.67M requests and is NOT this sweep. A single-FY Native-flag slice is;
- `AGENCY_CODE:` and `DEPARTMENT_ID:` **fail open** — they return zero results
  rather than erroring, which reads as "this agency has no contracts". Use
  `CONTRACTING_AGENCY_ID:`;
- **it retires in FY2026.** The window is closing, which argues for a bounded
  slice now rather than a complete corpus later.

**FAC Census-era bulk** (FY1998+, EIN on 100% of auditees, free, no key) is the
assistance-side outside look and is **annual, not monthly** — the archive gains
a year once a year. It is also the one route that reaches entities with no
federal contract at all.

Cost: ~1 bounded job per source per year. Expected yield: the 4,696-entity
backlog on first run, then roughly the annual entry rate — the FY2024/FY2025
type-only counts of 1,215 and 1,181 are the honest estimate.

### Cadence, and the one rule that makes it work

| tier | cadence | requests | first-run yield |
|---|---|---:|---:|
| 1 — adjudicate tier C, re-read owned files | monthly | **0** | 9,154 prime candidates |
| 2 — keep the type leg on every archive stream | every pull | **0** | ~1,100 assistance entities/FY |
| 3 — name tokens + one bounded ATOM slice + FAC | annual | ~1 job/source | 4,696 assistance candidates |

**The sweep does not attribute anything.** It produces candidates for `review/`,
at tier C, inheriting nothing. A tier is inherited from the source row, never
assigned by the consumer — and a sweep that promoted its own finds would be the
laundering defect (`START_HERE.md` standing rule 1) with a new front door.

**A sweep that finds nothing is a result, and it must be recorded as one** —
with the date, the surface probed and the count. Absence under a filter is a
property of the filter, and a sweep whose yield is never written down is
indistinguishable from a sweep that never ran.

## A FALSE "BLOCKED" IS A REAL LOSS — check robots.txt with YOUR user agent

*Added 2026-09-01 by shard H, which lost 22 hosts to this before catching it.*

`urllib.robotparser.RobotFileParser.read()` fetches `robots.txt` **with the
default `Python-urllib` user agent**, not with yours. Hosts that block that UA
return 403 for the robots file itself, and the parser interprets a 403 on
robots.txt as `disallow_all`. The site then looks closed when it is open.

Measured: `oha.org`, `nakupuna.com` and `papaolalokahi.org` all 403 the default
UA while serving a permissive `Disallow:` to Cedar's declared UA. Twenty-two
hosts in one shard's slice were recorded as robots-blocked and skipped, and
none of them was.

**The fix:** fetch `robots.txt` yourself with the same declared user agent you
will use for the content, then hand the body to `RobotFileParser.parse()`.
Never let `.read()` do the fetch.

```python
rp = RobotFileParser()
body = fetch(robots_url, ua=OUR_UA)          # our UA, our headers
rp.parse(body.splitlines() if body else [])  # 404/empty == allowed
```

A missing or empty `robots.txt` means **allowed**, not blocked. Only an actual
`Disallow` matching your path is a refusal.

This is the same shape as the `ps aux` lesson recorded above: **a check that
fails closed for the wrong reason silently stops work that would have
succeeded.** It is the mirror image of the export-gate defect in `AGENTS.md`
where a check read a key that never existed and therefore always passed. Both
are checks that are not measuring what their name says.

**None of this loosens a real refusal.** A genuine `Disallow` on your path, a
`TERMS_STATED_RESTRICTIVE` source, or a host that blocks your declared UA is
still a refusal and stays one. The point is only that the refusal must be real.

### Two companions from the same shard, both the same class of error

**A guessed domain that returns 200 is fabrication with a status code next to
it.** Bare token matching accepted a HugeDomains parking page, a Japanese blog,
a sweepstakes-casino farm, an unrelated coaching consultancy, and two
municipalities. Of 376 generated candidates only 8 survived a bar of: not
parked, the page's own `canonical`/`og:url` on the same apex, and a distinctive
name token in the `<title>`. Where a sourced URL already exists, do not guess at
all. Three other shards independently hit hijacked tribal domains today —
`jicarillaonline.com` (Thai casino), `lacvieuxdesert.com` (Indonesian slots),
`wrpt.us` (adult video), `rockyboy.org` (electronics blog),
`chippewacree.org` (link farm) — and one **Wayback capture that was already
hijacked**. A domain name is never evidence.

**A truncated read reports "no content" rather than "truncated."** A 1.6 MB cap
silently produced three newsletters that looked content-free: a cut-off PDF
still opens and still reports a page count, but extracts zero text. Record
`text_chars_extracted` per document and emit `text_not_extractable` — never a
bare `false` — when extraction yields nothing.
