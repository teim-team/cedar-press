# The Cedar dataset pipeline exemplar

`pipeline.py` is the pattern every Cedar dataset should copy: **one script,
one markdown, one database.** When a new dataset needs building, the answer is
a sibling of this file — not a directory of scripts, configs, and glue.

Today it mocks the target state. The real process is still "scrape and build
on a laptop, clean up, load into our database"; this collapses that into one
registry-driven program whose SQLite file stands in for the production
database. When we go direct-to-database, only the `Database` class changes.

```
sources.jsonl ──▶ due? ──▶ fetch (respectful) ──▶ changed? ──▶ extract ──▶ validate ──▶ database
 (the registry     │            │                    │            │            │        (SQLite now,
  drives it)       │            ▼                    │            ▼            ▼         production later)
                   │       raw snapshot          identical    loud failure  schema fail
                   ▼       (immutable)           bytes: stop  on unknown    = run fails,
              not due: skip                                   layouts       nothing loaded
```

## How it knows what to do (the staleness ladder)

1. **Due** — the registry row's `suggested_cadence` vs the last successful
   run. Never-run sources are due; fresh ones are skipped. Cadence is data
   (a registry edit), not code.
2. **Artifact unchanged** — same content hash as the last snapshot means no
   extraction at all: a run is logged, nothing else moves.
3. **Record unchanged** — `record_hash` covers canonicalized semantic fields
   only (casefolded, whitespace-normalized, digits-only phones, sorted
   arrays; no timestamps or run ids). A reformatted phone number is not a
   change; a new address is.
4. **Vanished** — a record missing from the latest pull flips
   `is_current = 0` and logs a `vanished` event. History is never deleted.
5. **Stale** — newest artifact older than 2× cadence, or the registry marks
   the source Stale. Surfaced in `status`; never silently worked around.

## Commands

```bash
python3 pipeline.py status                      # due / fresh / stale / blocked, in queue order
python3 pipeline.py sync                        # run everything due (needs CEDAR_CONTACT_EMAIL)
python3 pipeline.py sync TBD-030 --from-file naob.csv   # ingest an artifact you downloaded
python3 pipeline.py demo                        # full lifecycle on synthetic data, scratch dir
```

`demo` proves the machinery end-to-end offline: three pulls of a clearly
synthetic fixture (source `TBD-000`, `.invalid` domains) showing
appeared → artifact-unchanged skip → changed/vanished detection.

## Adding a source (the whole procedure)

1. The source must be a Live registry row — the registry is the config.
2. Write one adapter function mapping its artifact layout to partial Layer-1
   fields, and register it: `EXTRACTORS["TBD-###"] = extract_...`.
3. Run `pipeline.py sync TBD-###`. That's it. The envelope, hashing,
   validation, snapshots, and database behavior are shared.

An adapter that meets an unrecognized layout must raise, not guess — a loud
failure is a data point; a guessed record is fabrication.

## What the database holds

- `source_records` — one row per `business_source_id` (Layer 1: one business
  appearance in one source), with `record_hash`, `first_seen`/`last_seen`,
  `is_current`, and the full schema-validated payload.
- `record_events` — append-only appeared/changed/vanished log per run: the
  answer to "what changed and when."
- `runs` — every attempt, including failures and artifact-unchanged skips,
  with artifact hash and HTTP status.

## Non-negotiables carried from the registry (see CLAUDE.md)

- **Respectful fetching**: robots.txt honored, ≥2s per domain, identifying
  User-Agent with a monitored contact email (`CEDAR_CONTACT_EMAIL`; the
  pipeline refuses to fetch without one), full stop on 403/429. Never
  anything behind a login.
- **Never fabricate**: unobserved fields stay null; unrecognized layouts fail
  the run; schema validation failure loads nothing.
- **Evidence hierarchy travels**: every record carries its source's priority
  class; non-tribal sources load with `cross_reference_only: true` and can
  never originate an ownership assertion.
- **Raw snapshots are immutable** (`data/raw/{source_id}/{run_id}/`), stored
  with final URL, status, headers, and content hash.
- **Publication boundary**: this pipeline builds the *internal* Layer-1
  store. Nothing here is publishable until `FIELD_CLASSIFICATION.md` (a
  Phase-5 gate) classifies every field.

## Current status (honest)

Mock stage. One real adapter is registered (TBD-030 Tulalip NAOB CSV — first
in the scrape queue), written header-tolerantly but **unverified against a
real export** because this build environment blocks page fetches; its first
live run happens on a machine with network access, via `sync TBD-030` or
`--from-file`. Everything else — scheduling, snapshots, hashing, change
detection, validation, the database — runs today (`demo`).
