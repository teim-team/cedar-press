# Recipient holds and rebinds: the policy input for a per-UEI correction that is not a denial

Written 2026-10-02 on the consumer side (`cedar-press`), for the Siletz repair.
Status: **shape shipped, no entry recorded, nothing applied.** The file
`data/cedar/recipient_holds.json` carries zero entries; the loader
`code/cedar_publication.recipient_holds()` validates it and returns them; no
code consumes an entry yet. The producer (Lumecon-data) is adding the matching
mechanism on its side; this is the consumer's half, so the one data entry can
land in one place when its evidence is complete.

## Why a second vocabulary

`docs/REVIEW_STATUS.md` ("Source-side fixes, 2026-10-02") records the fact: two
Federal Funding transactions under recipient UEI `GJV4PJ8M5PC7`, award
`ASST_NON_1896753-42-22_417`, project to the tribal-government recipient while
the recipient is the Siletz Tribal Arts and Heritage Society, a separate Native
nonprofit. The only withholding mechanism the export honoured was
`cedar_publication.denied_ueis()`, built from ruling-ledger rows with
`ruling = not_native`, labelled `excluded_not_native` /
`verified_not_native_denial` on the row. Recording a Native nonprofit there
would be a false statement made so that a withholding fires, and it would
generalise a denial beyond the exact identifier-subject pairing it refutes.

A recipient hold states what is true instead:

| It says | It never says |
| --- | --- |
| the recipient behind **this UEI**, on **these award keys**, is a legal entity **distinct from** the Cedar entity the projection binds it to (`hold_kind = distinct_recipient`, `action = withhold`) | that the recipient is not Native (`ruling` may not contain `not_native`, `not native` or `not a Native entity`; the validator refuses it) |
| or: the recipient is a **different registered** Cedar entity (`hold_kind = rebind_to_entity`, `action = rebind`, `correct_recipient.cedar_uid` already in the register) | that a new entity exists (a hold never mints, recycles or guesses a uid; `hold_id` is `RH-YYYY-NNNN`, never `CE-`/`CB-`) |
| which uid the projection **currently carries** (`bound_cedar_uid`, read off the projection) | anything inferred from the register about which uid that must be |

Applied, a `withhold` blanks the Cedar attribution on the scoped transactions
and writes `attribution_status = withheld_distinct_recipient`
(`cedar_publication.RECIPIENT_HOLD_STATUS`), a controlled value distinct from
`excluded_not_native`, so a consumer never reads a hold as a denial. The raw
transactions are preserved; a hold changes the projection, never the source.

## Shape

`docs/schema/recipient_holds.schema.json` documents the shape;
`cedar_publication.validate_recipient_holds()` is the enforced rule
(`server/tests/test_recipient_holds.py`, 19 tests). The document:

```json
{ "schema_version": 1, "policy": "recipient_hold", "entries": [ ... ] }
```

Each entry, and what the validator checks:

| Field | Rule |
| --- | --- |
| `hold_id` | `RH-YYYY-NNNN`, unique; the hold record's own id (what), never an entity id |
| `collection` | the collection id of the scoped transactions (`funding`) |
| `recipient_uei` | exactly 12 characters, no `I` or `O` (SAM UEI); a dated attribute, not an identity |
| `award_ids` | one or more exact award keys, no repeats; a `(recipient_uei, award_id)` pair belongs to at most one entry across the file |
| `hold_kind`, `action` | `distinct_recipient` pairs with `withhold`; `rebind_to_entity` pairs with `rebind`; any other pairing is refused |
| `bound_cedar_uid` | the uid the projection currently carries; `CE-XXXXX-XX` and in the register; `null` only while `status = evidence_incomplete` |
| `correct_recipient` | `name` required; `cedar_uid` null for a withhold (with `register_status = not_in_register`), a register uid different from `bound_cedar_uid` for a rebind (with `in_register`) |
| `ruling` | the fact in words; refused if it contains `not_native`, `not native` or `not a Native entity` |
| `evidence` | one or more `{url (https), quoted (non-empty), checked_on (YYYY-MM-DD)}`; a URL alone is not evidence |
| `status` | `evidence_incomplete` (recorded, not applicable), `ready` (every field present; the producer rebuild may consume it), `applied` (consumed by a pinned release; the entry stays as the record) |
| `recorded_on`, `recorded_by`, `owner_review` | dates `YYYY-MM-DD`; the reviewer per AGENTS.md section 5 (Havala Hanson for Press data; an identity question reaches Elijah Moreno through her) |

The loader fails closed: an absent file, unreadable JSON or any validation
problem raises `RecipientHoldInvalid`, the same posture as `denied_ueis()`
(an absent ledger must never read as "no denials").

## The Siletz entry, drafted and held

This is the entry the test module carries as `SILETZ_DRAFT`. It validates as
`evidence_incomplete` and is refused as `ready` until `bound_cedar_uid` is
read off the projection. It is **not** in `data/cedar/recipient_holds.json`.

```json
{
  "hold_id": "RH-2026-0001",
  "collection": "funding",
  "recipient_uei": "GJV4PJ8M5PC7",
  "award_ids": ["ASST_NON_1896753-42-22_417"],
  "hold_kind": "distinct_recipient",
  "action": "withhold",
  "bound_cedar_uid": null,
  "correct_recipient": {
    "name": "Siletz Tribal Arts and Heritage Society",
    "cedar_uid": null,
    "register_status": "not_in_register"
  },
  "ruling": "Distinct legal entity from the tribal government: a separate Native nonprofit with its own board. No register entity yet; admission is the owner's adjudication.",
  "evidence": [
    {"url": "https://siletzartsheritagesociety.org/board-of-directors/", "quoted": "QUOTE TO BE RE-READ AND PASTED WHEN THE PAGE IS REACHABLE", "checked_on": "2026-10-02"},
    {"url": "https://www.usaspending.gov/award/ASST_NON_1896753-42-22_417", "quoted": "QUOTE TO BE RE-READ AND PASTED WHEN THE PAGE IS REACHABLE", "checked_on": "2026-10-02"}
  ],
  "status": "evidence_incomplete",
  "recorded_on": "2026-10-02",
  "recorded_by": "consumer-side release-gap pass",
  "owner_review": "Havala Hanson"
}
```

What is missing, in order, before the entry is recorded and set `ready`:

1. **The bound uid.** Read `cedar_uid` on the two transactions in the funding
   projection on the owner's machine (the table is gitignored). The register's
   only Siletz government is `CE-001A3-8M` (Confederated Tribes of Siletz
   Indians of Oregon); the entry must carry what the projection says, not
   what the register suggests.
2. **The two quotations.** Both evidence URLs were unreachable from the
   2026-10-02 environments (egress blocked). Re-read each page, paste the
   sentence that supports the fact, and set `checked_on` to that date.
3. **Owner review.** Havala Hanson reviews the entry; whether the society is
   admitted to the register as its own Native nonprofit (a `CE-` id) is an
   identity adjudication for Elijah Moreno and is not part of the hold.

Then: record the entry in `data/cedar/recipient_holds.json`, run
`python3 -m unittest discover -s server/tests -t server -p "test_recipient_holds.py"`,
and hand the file to the producer's funding candidate rebuild, which consumes
`ready` entries and pins a new release; the served preview changes only
through that pin. Set `status = applied` when the pin lands and keep the
entry.

## What this does not do

- It does not apply to any uid, transaction or sample. No consumer function
  enforces an entry yet; `enforce_denials()` is unchanged.
- It does not retire `denied_ueis()`. A verified `not_native` ruling is still
  a denial; this file is for the case where that vocabulary would misstate
  the fact.
- It does not decide the Siletz binding. It records the shape the decision
  will be written in.
