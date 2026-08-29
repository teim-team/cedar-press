#!/usr/bin/env python3
"""
327 - MIGRATE POSITIONAL / PROCESS-HASH KEYS TO DETERMINISTIC DIGESTS,
      IN PLACE, AND MIGRATE EVERY CONSUMER IN THE SAME PASS.

    py -3 code/327_migrate_class7_keys_to_digests.py            # DRY RUN
    py -3 code/327_migrate_class7_keys_to_digests.py --apply    # write

THE HARD PART IS NOT THE KEY. IT IS THE MIGRATION.
--------------------------------------------------
Changing an id in a table that other tables already reference breaks those
references SILENTLY - no error, no missing file, just a join that quietly
returns nothing. So this script refuses to migrate a key until it has proved
where every reference lives.

**The proof is a FULL SCAN, not a declaration.** Before writing anything it
reads every `data/clean/**/*.csv` and `data/spine/*.csv`, cell by cell, and
records every place an old id VALUE appears - including inside a
`,`/`;`/`|`-separated list, because `gaming_financing_events.
lineage_related_opinion_ids` is exactly that shape. Then:

  * every found location that the spec DECLARES is migrated in the same pass;
  * **one found location the spec does NOT declare aborts that whole spec**,
    which is then reported as BLOCKED-ON-CONSUMERS with the location named.

A half-migrated key is worse than a bad key: the bad key at least fails
uniformly. That is why an undeclared consumer is a hard stop rather than a
warning, and why the dry run is the default.

THE KEY RULE THIS IMPLEMENTS
----------------------------
A primary key is either a NATURAL key stated by the source, or a
DETERMINISTIC DIGEST of stated columns. Never a position, never `hash()`.
Every spec below names its composing columns AND says why those columns, so a
later reader can reproduce the id without reading this code. The digest is
`cedar_keys.surrogate_id` - blake2b over NFKC-normalised, case-folded,
whitespace-collapsed parts joined by ASCII 0x1F. Same answer in every process,
every build, every machine.

The producing scripts were edited in the same session to mint the SAME id
(`cedar_keys.surrogate_id(prefix, row, columns)` with the identical column
list), so a future re-run reproduces exactly what this script writes. Where a
producer is on the NEVER-RUN list, or belongs to a live agent, the spec is not
migrated at all - see `BLOCKED` below.

SAFETY
------
No network. Backs up every file it touches as
`<file>.bak_<date>_pre_327_migrate_class7_keys` (tagged with the SCRIPT NAME,
never the number - four agents once all wrote `.bak_2026-08-26_pre163`).
Writes `<file>.part` then renames. **Verifies by RE-READING the written file**
and refuses to report success unless every old value is gone and every new
value is present at the same row count. Writes the complete old -> new map to
`docs/schema/class7_key_migration_map.json` so any id quoted in a document or
a hand-written ruling can still be resolved.

Claimed 2026-08-26 with script numbers 326-333.
"""

import csv
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
MAP_OUT = CEDAR / "docs" / "schema" / "class7_key_migration_map.json"

sys.path.insert(0, str(CODE))
import cedar_keys as CK                      # noqa: E402

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
TODAY = date.today().isoformat()
BAK_TAG = f".bak_{TODAY}_pre_327_migrate_class7_keys"

LIST_SPLIT = re.compile(r"\s*[|;,]\s*")


# ---------------------------------------------------------------------------
# THE SPECS. Each one states its composing columns AND why those columns.
# ---------------------------------------------------------------------------

SPECS = [
    {
        "name": "anc_id",
        "producer": "07_parse_ancsa_ceiling.py:163",
        "was": 'f"ANC-{i:04d}" over a list sorted by (anc_class, name)',
        "prefix": "ANC",
        "old_prefix": "ANC-",
        "home": "data/clean/anc_ceiling_roster.csv",
        "id_column": "anc_id",
        "key_columns": ["corporation_name", "anc_class"],
        "why_these_columns":
            "ANCSA states both: the corporation's own name and whether it is "
            "a regional or a village corporation. Two ANCSA corporations "
            "never share a name within a class - measured unique over all 196 "
            "rows, 0 blank. The rank in a name-sorted list is not stated by "
            "anything and moved every time a corporation was added.",
        "references": [
            ("data/clean/anc_ceiling_roster.csv", "anc_id"),
            ("data/clean/ancsa_filings_index.csv", "anc_id"),
            ("data/clean/deals_party_matches.csv", "proposed_tribe_id"),
        ],
    },
    {
        "name": "allocation_id",
        "producer": "104_build_wa_allocations.py:629",
        "was": 'f"WAALLOC-{n:04d}" over a running counter across tribes',
        "prefix": "WAALLOC",
        "old_prefix": "WAALLOC-",
        "home": "data/clean/wa_machine_allocations.csv",
        "id_column": "allocation_id",
        "key_columns": ["tribe_name", "effective_start", "measurement_type"],
        "why_these_columns":
            "One Washington machine allocation is a tribe, a date the "
            "instrument took effect, and what was measured. All three are "
            "printed in the compact/appendix the row quotes. Unique over all "
            "75 rows, 0 blank.",
        "references": [
            ("data/clean/wa_machine_allocations.csv", "allocation_id"),
        ],
    },
    {
        "name": "band_id",
        "producer": "106_build_revenue_bounds.py:308",
        "was": 'f"NIGCBAND-{fy}-{i+1}" - fy is stated, i is a loop counter',
        "prefix": "NIGCBAND",
        "old_prefix": "NIGCBAND-",
        "home": "data/clean/nigc_revenue_bands.csv",
        "id_column": "band_id",
        "key_columns": ["fiscal_year", "band_ordinal", "band_label"],
        "why_these_columns":
            "NIGC prints a fixed band schedule per fiscal year and labels each "
            "band ('$25M to $50M'). The ordinal and the label are both "
            "written into the row, so the id is reproducible from the row "
            "itself. The old form was ALREADY nearly deterministic - it is "
            "migrated for consistency, not because it was measured to move.",
        "references": [
            ("data/clean/nigc_revenue_bands.csv", "band_id"),
        ],
    },
    {
        "name": "fact_id",
        "producer": "117_build_gaming_devices.py:576,623",
        "was": 'f"GMF-{seq:05d}" then RE-NUMBERED f"GMF-{i:05d}" after a sort',
        "prefix": "GMF",
        "old_prefix": "GMF-",
        "home": "data/clean/gaming_manufacturer_facts.csv",
        "id_column": "fact_id",
        "key_columns": ["manufacturer", "fact_type", "device_class",
                        "geography", "period_end"],
        "why_these_columns":
            "This is the file's own dedupe key - 117 already builds "
            "`(manufacturer, ftype, dclass, geo, fy, val)` to decide whether "
            "it has seen a fact before. The id now uses the same facts the "
            "build already trusts to identify one. Note the second site: the "
            "id was assigned once and then REASSIGNED after a re-sort, so the "
            "same fact carried two different ids inside a single run.",
        "references": [
            ("data/clean/gaming_manufacturer_facts.csv", "fact_id"),
        ],
    },
    {
        "name": "party_id_s106",
        "producer": "130_build_section_106_consultation.py:830",
        "was": 'f"S106P-FR-{dn}-{len(parties)}" - position in the whole run',
        "prefix": "S106P-FR",
        "old_prefix": "S106P-FR-",
        "home": "data/clean/section_106_project_parties.csv",
        "id_column": "party_id",
        "key_columns": ["document_number", "party_name_as_published",
                        "party_role"],
        "why_these_columns":
            "The Federal Register document number is the source's own "
            "identifier for the notice; the party name and role are what the "
            "notice says. The trailing counter was `len(parties)` - the "
            "position in the ENTIRE run, so inserting one earlier notice "
            "renumbered every party after it.",
        "references": [
            ("data/clean/section_106_project_parties.csv", "party_id"),
        ],
    },
    {
        "name": "consultation_event_id",
        "producer": "130_build_section_106_consultation.py:974",
        "was": 'f"S106-FR-{dn}-{i}" - i is the position within one document',
        "prefix": "S106-FR",
        "old_prefix": "S106-FR-",
        "home": "data/clean/section_106_consultation_events.csv",
        "id_column": "consultation_event_id",
        "key_columns": ["document_number", "participant_name_as_published",
                        "participant_role"],
        "why_these_columns":
            "Same reasoning as the party id, one level down: the FR document "
            "plus the participant the document names and the role it gives "
            "them. Unique over all 1,363 rows, 0 blank. `i` was an index into "
            "a sorted dict of matched tribes, so adding a tribe to the spine "
            "renumbered the events of every notice it appeared in.",
        "references": [
            ("data/clean/section_106_consultation_events.csv",
             "consultation_event_id"),
            ("data/clean/ferc_tribal_dockets.csv", "section_106_cross_ref"),
        ],
    },
    {
        "name": "compact_event_id",
        "producer": "15b_build_compact_index.py:262",
        "was": 'f"EVT-{st}-{slug}-{date}-{len(events)+1:04d}"',
        "prefix": "EVT",
        "old_prefix": "EVT-",
        "home": "data/clean/compact_events.csv",
        "id_column": "event_id",
        "key_columns": ["compact_id", "event_date", "event_type"],
        "why_these_columns":
            "A compact event is the compact it happened to, the date the "
            "Federal Register gives it, and what happened. All three are "
            "stated by BIA's own index. The old id already carried the state, "
            "the tribe slug and the date - and then appended the position in "
            "the run, which is the only part that could move.",
        "references": [
            ("data/clean/compact_events.csv", "event_id"),
        ],
    },
    {
        "name": "nho_ownership_event_id",
        "producer": "61_add_nho_intertribal_to_spine.py:496",
        "was": 'f"OWN-NHO-2026-{i:03d}" over a split of a subsidiary list',
        "prefix": "OWN-NHO",
        "old_prefix": "OWN-NHO-2026-",
        "home": "data/clean/nho_ownership_changes.csv",
        "id_column": "event_id",
        "key_columns": ["effective_month", "acquirer_entity", "target_entity",
                        "direction"],
        "why_these_columns":
            "The source states June 2026, the acquirer, the firm acquired and "
            "the direction. `effective_date` is deliberately BLANK on all 9 "
            "rows - the source gives a month and no day, and this project "
            "does not invent one - so the MONTH is the dated part of the key. "
            "The old id was the position in a `|`-split subsidiary string.",
        "references": [
            ("data/clean/nho_ownership_changes.csv", "event_id"),
        ],
    },
    {
        "name": "admin_observation_id",
        "producer": "85_build_admin_region_crosswalk.py:743",
        "was": 'f"CEDAR-ADMOBS-{len(observations)+1:06d}"',
        "prefix": "CEDAR-ADMOBS",
        "old_prefix": "CEDAR-ADMOBS-",
        "home": "data/clean/admin_regional_observations.csv",
        "id_column": "observation_id",
        "key_columns": ["region_system_code", "administrative_region_id",
                        "observation_name", "observation_year"],
        "why_these_columns":
            "An observation is a measure, about one administrative region of "
            "one region system, in one year. All four are columns of the row. "
            "The old id was the call order of `add_obs()`, so adding a system "
            "renumbered every observation added after it.",
        "references": [
            ("data/clean/admin_regional_observations.csv", "observation_id"),
        ],
    },
    {
        "name": "earmark_id",
        "producer": "99_build_earmarks_and_schedc.py:1626,1661,1887",
        "was": 'f"EMK-H{fy}-{n+1:05d}" / "EMK-S..." (positional) and '
               'f"EMK-E{fy}-{abs(hash(p.stem)) % 10**6}-{n:05d}" (PROCESS '
               'HASH - the same PYTHONHASHSEED defect as ferc_filing_id)',
        "prefix": "EMK",
        "old_prefix": "EMK-",
        "home": "data/clean/earmarks.csv",
        "id_column": "earmark_id",
        "key_columns": ["fiscal_year", "chamber", "requesting_member",
                        "recipient_name", "project_title", "amount_enacted",
                        "source_url", "source_quote"],
        "why_these_columns":
            "This is the column list `cedar_keys.NON_DETERMINISTIC_COLUMNS` "
            "already recorded as the join-instead for this id, plus "
            "`source_url` and `source_quote` - which the measurement showed "
            "are REQUIRED: the six-column form leaves 7 collisions over 1,002 "
            "rows (a member requesting the same project twice in one year), "
            "and the eight-column form is unique with 0 blanks. A WIDE key, "
            "and it says so: it is an identity for the row's CONTENT and "
            "changes if any of those values is corrected.",
        "references": [
            ("data/clean/earmarks.csv", "earmark_id"),
        ],
    },
    {
        "name": "ferc_filing_id",
        "producer": "133_build_ferc_advocacy.py:1832-1833",
        "was": 'f"FERC-{d}-{sub}-{acc}-{abs(hash(aff)) % 10000:04d}" - '
               'PROCESS HASH. 4 of 2,534 documents shared between the '
               '2026-08-12 and 2026-08-26 builds kept their id.',
        "prefix": "FERCFIL",
        "old_prefix": "FERC-",
        "home": "data/clean/ferc_docket_filings.csv",
        "id_column": "ferc_filing_id",
        "key_columns": ["docket_number", "subdocket", "accession_number",
                        "filer_organization_as_recorded",
                        "document_description_verbatim"],
        "why_these_columns":
            "START_HERE.md already records the workaround - join on "
            "docket_number + accession_number + filer_organization_as_"
            "recorded - and this adds the two the id itself already carried "
            "(`subdocket`) and the one that separates two filings of the same "
            "type on one accession (`document_description_verbatim`). "
            "MEASURED, and stated rather than hidden: this key is NOT unique. "
            "769 groups covering 1,758 rows collide, i.e. 989 excess rows. "
            "Every one of them is a row that is identical to its twin on "
            "EVERY other column of the table up to case and whitespace - "
            "the same eLibrary document recorded twice. The process hash was "
            "MASKING that duplication behind 855 collisions of its own. So "
            "the column becomes a stable CONTENT identity, and "
            "`ferc_docket_filings.csv` stays what 284 already calls it: "
            "BLOCKED for a primary key until the duplicates are resolved. "
            "Nothing in the repo joins on this column - verified by the full "
            "scan below, which found the values in exactly one place.",
        "references": [
            ("data/clean/ferc_docket_filings.csv", "ferc_filing_id"),
        ],
        "expect_not_unique": True,
        # RECOMPUTE, not remap. The OLD column is not unique either - 855
        # collisions, one id on 64 different documents - so `old -> new` is
        # ambiguous and a value substitution would be undefined. The id is
        # rewritten ROW BY ROW from that row's own stated columns instead.
        # This mode is only legal when the full scan proves the old values
        # appear NOWHERE except this column; anything else is a reference that
        # cannot be resolved, and the spec blocks.
        "mode": "recompute",
    },
]


#: Specs deliberately NOT attempted, each with the consumer list that blocks
#: it. Recorded here rather than in a document, because the next agent runs
#: this file and reads a document only if something tells them to.
BLOCKED = [
    {
        "name": "exclusion_id",
        "producer": "02_extract_exclusion_rulings.py:116",
        "reason": "BLOCKED-ON-CONSUMERS",
        "consumers": [
            "data/spine/cedar_exclusion_rulings.csv.exclusion_id (123 rows)",
            "data/clean/cedar_identifier_ledger_final.csv.exclusion_id",
            "data/clean/cedar_identifier_ledger_tiered.csv.exclusion_id",
            "data/clean/cedar_publishable_identifiers.csv.exclusion_id",
            "data/spine/cedar_rulings.csv.supersedes ('EXCL-0116')",
            "code: 03, 08, 09, 17, 167, 241",
        ],
        "why": "The identifier ledger is the project's crown jewel (20,577 "
               "rows) and `09_import_rulings.py` - which reads exclusion_id - "
               "is on the NEVER-RUN list because it rebuilds the ledger from "
               "a stale `_tiered` and has already cost 1,327 rows once. "
               "`cedar_rulings.csv` is a HAND-AUTHORED ruling record: "
               "'EXCL-0116' is a value a person wrote down. Rewriting an id a "
               "human cited, inside a file that is the authority for what was "
               "decided, is not a migration this script should do "
               "unattended.",
    },
    {
        "name": "nho_id",
        "producer": "05_parse_doi_nho_list.py:90",
        "reason": "BLOCKED-ON-CONSUMERS",
        "consumers": [
            "data/clean/nho_doi_notification_roster.csv.nho_id (190 rows)",
            "data/spine/cedar_rulings.csv.identifier ('NHO-DOI-0132', "
            "ruling DO_NOT_CONFLATE on Native Hawaiian Legal Corporation)",
            "code: 06_verify_nho_via_8a.py, 163_promote_nho_universe_in_"
            "place.py",
        ],
        "why": "Same shape as exclusion_id and blocked for the same one "
               "reason: a HAND-AUTHORED ruling in `data/spine/cedar_rulings."
               "csv` cites `NHO-DOI-0132` by value. The roster itself would "
               "migrate cleanly - `(organization_name, list_type, "
               "doi_list_page)` is unique over all 190 rows - so this is one "
               "ruling row away from being safe. WHAT HAS TO HAPPEN: decide "
               "whether a human ruling may be rewritten by a migration, or "
               "give `cedar_rulings.csv` an `identifier_as_ruled` column that "
               "preserves what the person actually wrote.",
    },
    {
        "name": "verification_id",
        "producer": "170_build_individual_native_candidates.py:482",
        "reason": "BLOCKED-ON-LIVE-AGENT",
        "consumers": [
            "data/clean/individual_native_ownership_verification.csv."
            "verification_id (335 rows)",
            "data/clean/individual_native_ownership_verification.csv."
            "web_pass_verification_id (334 rows - a SELF foreign key)",
            "data/clean/individual_native_verification_candidates.csv."
            "verification_id (335 rows)",
            "code: 171, 172, 173",
        ],
        "why": "THIS IS ONE OF THE THREE MEASURED-DAMAGE INSTANCES and it is "
               "the one that must NOT be fixed right now. Concurrency rule: "
               "`individual_native_firm_register.csv` was written at 19:22 "
               "today, `170` and `171` at 18:00-18:01, and `241`-`244` landed "
               "at 18:58 - the individually-Native-owned firm class is ANOTHER "
               "AGENT'S LIVE WORK. Editing 170 and rewriting its three tables "
               "would race its author, which is the exact failure concurrency "
               "rule 5 is about. The fix is also already SPECIFIED, in "
               "`cedar_keys.PRIVACY_SURROGATE`: the published key is a digest "
               "of `awardee_uei` under prefix `INF`, because SAM's public "
               "entity search resolves a UEI to a person's name and address "
               "for a firm whose legal name IS a person's name. Measured "
               "here: `awardee_uei` is unique and non-blank over all 335 "
               "rows, so the digest is ready to mint the day its owner is "
               "done. WHAT HAS TO HAPPEN: the owner of 170-173 runs the same "
               "surrogate_id('INF', row, ['awardee_uei']) over both tables "
               "and the self-FK `web_pass_verification_id` in one pass.",
    },
    {
        "name": "review_id (RV-)",
        "producer": "01_build_entity_spine.py:269",
        "reason": "BLOCKED-ON-NEVER-RUN-PRODUCER",
        "consumers": ["none - the value reaches no clean or spine table"],
        "why": "`01_build_entity_spine.py` is on the NEVER-RUN list: a "
               "rebuild drops every appended entity - the village "
               "corporations, NHOs, TCUs, CDFIs, BIE schools and UIOs added "
               "by 52, 61, 73 and 75. The id itself is LOW risk (it is a "
               "review-queue row number that never lands in a table), so "
               "editing 01 to fix it would buy nothing and put a hand on a "
               "file that must not be touched casually. Left alone "
               "deliberately.",
    },
    {
        "name": "cedar_opinion_id",
        "producer": "90_fetch_nigc_declinations.py:209",
        "reason": "BLOCKED-ON-CONSUMERS",
        "consumers": [
            "data/clean/nigc_declination_letters.csv.cedar_opinion_id (327)",
            "data/clean/gaming_financing_events.csv.cedar_opinion_id (293)",
            "data/clean/gaming_financing_events.csv."
            "lineage_related_opinion_ids (MULTI-VALUED, 25 rows)",
            "data/clean/gaming_source_claims.csv.source_record_id (113)",
            "code: 91, 100, 119, 149, 174",
        ],
        "why": "Four columns in three tables, one of them a multi-valued list "
               "and one of them a DIFFERENTLY NAMED column "
               "(`source_record_id`) that happens to carry opinion ids. "
               "`119_build_digital_and_loyalty.py` is a consumer and is on "
               "the NEVER-RUN list. This is migratable but it is a "
               "four-column, three-table, list-aware pass and it should be "
               "its own session with its own verification, not a rider on "
               "this one.",
    },
    {
        "name": "resource_revenue_event_id / resource_asset_id",
        "producer": "83_build_resource_ledger.py:441,515,524,2574",
        "reason": "BLOCKED-ON-CONSUMERS",
        "consumers": [
            "data/clean/resource_revenue.csv.resource_revenue_event_id "
            "(10,482)",
            "data/clean/resource_assets.csv.resource_asset_id",
            "code: 84, 129, 135, 137, 149, 227, 41",
        ],
        "why": "Seven consuming scripts, one of which (`41_build_codebooks."
               "py`) is on the NEVER-RUN list and one of which "
               "(`227_anomaly_sweep.py`) was RUNNING during this session. "
               "`resource_asset_id` also mints under the literal `CEDAR-` "
               "prefix, which collides with every other CEDAR-* id in the "
               "project for the purposes of a value scan, so the reference "
               "set cannot be enumerated safely by prefix alone.",
    },
    {
        "name": "ordinance_id",
        "producer": "118_build_gaming_ordinances.py:295",
        "reason": "BLOCKED-ON-CONSUMERS",
        "consumers": [
            "data/clean/gaming_ordinances.csv.ordinance_id (1,155)",
            "data/clean/gaming_ordinances.csv.superseded_by_ordinance_id "
            "(834 - a SELF foreign key)",
            "data/clean/gaming_ordinance_ocr.csv.ordinance_id (263)",
            "data/clean/compact_obligation_tribal_agency_bridge.csv."
            "agency_source_ordinance_id (927)",
            "code: 122, 127, 153, 266",
        ],
        "why": "A self-FK plus two other tables plus an OCR merge stage "
               "(`153_merge_ordinance_ocr.py`) that joins the OCR output back "
               "on this id. The id is also PARTLY natural already - it is "
               "built from the NIGC index date - so the win is smaller than "
               "the blast radius. Migratable in a dedicated pass.",
    },
]


# ---------------------------------------------------------------------------

def read_rows(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd, [])
        return hdr, [r for r in rd]


def build_map(spec):
    """old id -> new id for one spec, or (None, reason)."""
    home = CEDAR / spec["home"]
    if not home.exists():
        return None, f"home table absent: {spec['home']}"
    hdr, rows = read_rows(home)
    miss = [c for c in spec["key_columns"] + [spec["id_column"]]
            if c not in hdr]
    if miss:
        return None, f"columns absent from {home.name}: {miss}"
    idx = {c: hdr.index(c) for c in hdr}
    dicts = [{c: (r[idx[c]] if idx[c] < len(r) else "") for c in hdr}
             for r in rows]

    ok, n, nd, blanks, dupes = CK.verify_unique(dicts, spec["key_columns"])
    if not ok and not spec.get("expect_not_unique"):
        return None, (f"stated key {spec['key_columns']} is NOT unique over "
                      f"{home.name}: {n:,} rows, {nd:,} distinct, "
                      f"{blanks} all-blank. Migrating would create duplicate "
                      f"primary keys, which is worse than a positional one.")

    recompute = spec.get("mode") == "recompute"
    mapping, new_counts, per_row, old_ids = {}, Counter(), [], set()
    ambiguous = 0
    for d in dicts:
        old = (d.get(spec["id_column"]) or "").strip()
        try:
            new = CK.surrogate_id(spec["prefix"], d, spec["key_columns"])
        except CK.UnstableKey as e:
            return None, f"blank key row in {home.name}: {e}"
        per_row.append(new)
        new_counts[new] += 1
        if not old:
            continue
        old_ids.add(old)
        if old in mapping and mapping[old] != new:
            if not recompute:
                return None, (f"old id {old!r} appears twice in {home.name} "
                              f"with two different stated keys - the old "
                              f"column is not even unique, so the map is "
                              f"ambiguous")
            ambiguous += 1
            continue
        mapping[old] = new
    collisions = {k: v for k, v in new_counts.items() if v > 1}
    return {"map": mapping, "old_ids": old_ids, "per_row": per_row,
            "recompute": recompute, "ambiguous_old_ids": ambiguous,
            "rows": len(dicts),
            "distinct_new": len(new_counts),
            "collision_groups": len(collisions),
            "collision_rows": sum(collisions.values())}, ""


def full_scan(specs_with_maps):
    """Every (file, column) where any old id of any spec appears.

    A FULL scan, not a sample. This is the whole safety property: an
    undeclared location found here stops the migration; a location we never
    looked for would have been a silent broken reference.
    """
    by_prefix = {}
    for s, m in specs_with_maps:
        by_prefix[s["old_prefix"]] = (s["name"], set(m["old_ids"]))
    prefix_tuple = tuple(by_prefix)
    hits = defaultdict(Counter)          # spec_name -> Counter[(file, col)]
    files = sorted(list(CLEAN.rglob("*.csv")) + list(SPINE.glob("*.csv")))
    for p in files:
        rel = str(p.relative_to(CEDAR)).replace("\\", "/")
        try:
            fh = open(p, encoding="utf-8-sig", errors="replace", newline="")
        except OSError as e:
            print(f"    UNREADABLE {rel}: {e}")
            continue
        with fh:
            rd = csv.reader(fh)
            hdr = next(rd, None)
            if not hdr:
                continue
            for row in rd:
                for i, v in enumerate(row):
                    if not v or not v.startswith(prefix_tuple):
                        # a list cell can hold an id after a separator
                        if not v or not any(pp in v for pp in prefix_tuple):
                            continue
                    col = hdr[i] if i < len(hdr) else f"col{i}"
                    parts = [v] if len(v) < 200 else []
                    parts += LIST_SPLIT.split(v)
                    for tok in set(parts):
                        tok = tok.strip()
                        if not tok.startswith(prefix_tuple):
                            continue
                        for pre, (nm, ids) in by_prefix.items():
                            if tok.startswith(pre) and tok in ids:
                                hits[nm][(rel, col)] += 1
                                break
    return hits


def recompute_home(path, id_column, per_row, old_ids, apply_):
    """Rewrite `id_column` row by row from the precomputed digests.

    For a key whose OLD column was not unique, so `old -> new` is undefined.
    Row order is the file's own order and `per_row` was built from the same
    read, so the alignment is positional WITHIN ONE PASS over one file - not
    a positional KEY. The row count is re-checked before and after.
    """
    p = CEDAR / path
    hdr, rows = read_rows(p)
    if id_column not in hdr:
        return {"file": path, "status": "COLUMN_ABSENT", "columns": [id_column]}
    if len(rows) != len(per_row):
        return {"file": path, "status": "ROW_COUNT_MOVED",
                "detail": f"the table changed under us: {len(per_row)} rows "
                          f"when the key was computed, {len(rows)} now. "
                          f"Refusing - a shifted row would take another row's "
                          f"id, which is the exact defect being fixed."}
    i = hdr.index(id_column)
    if not apply_:
        would = sum(1 for r, new in zip(rows, per_row)
                    if (r[i] if i < len(r) else "") != new)
        return {"file": path, "status": "DRY_RUN", "columns": [id_column],
                "cells_would_change": would}
    bak = p.with_name(p.name + BAK_TAG)
    if not bak.exists():
        shutil.copy2(p, bak)
    changed = 0
    out = []
    for r, new in zip(rows, per_row):
        r = list(r)
        while len(r) <= i:
            r.append("")
        if r[i] != new:
            changed += 1
        r[i] = new
        out.append(r)
    tmp = p.with_name(p.name + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        w.writerows(out)
    tmp.replace(p)
    hdr2, rows2 = read_rows(p)
    leftover = sum(1 for r in rows2
                   if i < len(r) and r[i].strip() in old_ids)
    ok = (hdr2 == hdr and len(rows2) == len(rows) and leftover == 0
          and all((r[i] if i < len(r) else "") == n
                  for r, n in zip(rows2, per_row)))
    return {"file": path, "status": "OK" if ok else "VERIFY_FAILED",
            "columns": [id_column], "cells_changed": changed,
            "old_values_remaining": leftover, "rows": len(rows2),
            "backup": bak.name}


def rewrite(path, columns, mapping, apply_):
    """Replace every occurrence of an old id in `columns`. Returns a report."""
    p = CEDAR / path
    hdr, rows = read_rows(p)
    cols = [c for c in columns if c in hdr]
    if not cols:
        return {"file": path, "status": "COLUMN_ABSENT", "columns": columns}
    idxs = [hdr.index(c) for c in cols]
    changed = 0
    unmapped = Counter()
    out = []
    for r in rows:
        r = list(r)
        for i in idxs:
            if i >= len(r):
                continue
            v = r[i]
            if not v:
                continue
            # COUNT WHAT WOULD CHANGE, NOT WHAT WOULD BE TOUCHED.
            # This used to increment on every cell whose value was IN the map,
            # which on an already-migrated table is every cell - so a second
            # dry run reported "1,002 cells" on a file where nothing would
            # move, and the log told a reader to expect zero. A counter whose
            # number does not mean what its name says is the 87 defect in a
            # new place. `recompute_home` always compared; this now matches it.
            toks = LIST_SPLIT.split(v)
            if len(toks) == 1:
                if v.strip() in mapping:
                    nv = mapping[v.strip()]
                    if nv != v:
                        r[i] = nv
                        changed += 1
                continue
            # PRESERVE THE SEPARATOR THE PRODUCER WROTE. Re-joining a list
            # cell with a house style is a silent format change: 133 writes
            # `";".join(...)` into `ferc_tribal_dockets.section_106_cross_ref`,
            # and re-joining it with " | " would have left the live file
            # holding a delimiter no rebuild produces and no reader splits on.
            # Caught 2026-08-26 by re-reading the migrated file rather than
            # trusting the run log.
            seps = LIST_SPLIT.findall(v)
            sep = seps[0] if seps else "; "
            new_toks = [mapping.get(t.strip(), t) for t in toks]
            nv = sep.join(new_toks)
            if nv != v:
                r[i] = nv
                changed += 1
        out.append(r)
    if not apply_:
        return {"file": path, "status": "DRY_RUN", "columns": cols,
                "cells_would_change": changed}

    bak = p.with_name(p.name + BAK_TAG)
    if not bak.exists():
        shutil.copy2(p, bak)
    tmp = p.with_name(p.name + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        w.writerows(out)
    tmp.replace(p)

    # VERIFY BY RE-READING. Rule 4: never trust the run log.
    hdr2, rows2 = read_rows(p)
    if hdr2 != hdr or len(rows2) != len(rows):
        return {"file": path, "status": "VERIFY_FAILED",
                "detail": f"header or row count moved "
                          f"({len(rows)} -> {len(rows2)})", "backup": bak.name}
    olds = set(mapping)
    leftover = 0
    for r in rows2:
        for i in idxs:
            if i < len(r) and r[i]:
                for t in LIST_SPLIT.split(r[i]):
                    if t.strip() in olds:
                        leftover += 1
    return {"file": path, "status": "OK" if leftover == 0 else "LEFTOVER",
            "columns": cols, "cells_changed": changed,
            "old_values_remaining": leftover, "rows": len(rows2),
            "backup": bak.name}


def main():
    apply_ = "--apply" in sys.argv
    started = datetime.now()
    print("=" * 78)
    print(f"327  CLASS-7 KEY MIGRATION  [{'APPLY' if apply_ else 'DRY RUN'}]")
    print("=" * 78)

    ready, refused = [], []
    for s in SPECS:
        m, why = build_map(s)
        if m is None:
            refused.append((s, why))
        else:
            ready.append((s, m))

    print(f"\n{len(ready)} spec(s) with a proven stated key, "
          f"{len(refused)} refused up front\n")
    for s, why in refused:
        print(f"  REFUSED  {s['name']:26s} {why}")

    print("\nFULL SCAN of data/clean/**/*.csv + data/spine/*.csv for every "
          "old id value ...")
    hits = full_scan(ready)
    print(f"   scanned; {sum(len(v) for v in hits.values())} "
          f"(file, column) location(s) hold a migrating id\n")

    migrated, blocked_now, results = [], [], {}
    for s, m in ready:
        declared = {(t, c) for t, c in s["references"]}
        found = set(hits.get(s["name"], {}))
        undeclared = sorted(found - declared)
        print("-" * 78)
        print(f"{s['name']}   {s['producer']}")
        print(f"  was:  {s['was']}")
        print(f"  now:  {s['prefix']}-<blake2b(" +
              ", ".join(s["key_columns"]) + ")>")
        print(f"  {m['rows']:,} rows -> {m['distinct_new']:,} distinct new ids"
              + (f"  ({m['collision_groups']} collision group(s), "
                 f"{m['collision_rows']:,} rows)"
                 if m["collision_groups"] else ""))
        if m["recompute"]:
            print(f"  MODE: RECOMPUTE - the OLD column was not unique either "
                  f"({m['ambiguous_old_ids']:,} rows whose old id is shared "
                  f"with a row having a different stated key), so the id is "
                  f"rebuilt per row rather than substituted.")
        for loc in sorted(found):
            n = hits[s["name"]][loc]
            print(f"    found in {loc[0]}.{loc[1]}  ({n:,} cells)")
        if m["recompute"] and found - {(s["home"], s["id_column"])}:
            extra = sorted(found - {(s["home"], s["id_column"])})
            print(f"  !! BLOCKED-ON-CONSUMERS: recompute mode requires the "
                  f"old values to appear NOWHERE else, and they appear in "
                  f"{len(extra)} other location(s):")
            for loc in extra:
                print(f"       {loc[0]}.{loc[1]}")
            blocked_now.append({"name": s["name"], "producer": s["producer"],
                                "reason": "BLOCKED-ON-CONSUMERS "
                                          "(ambiguous old id + external refs)",
                                "undeclared_locations": [f"{a}.{b}"
                                                         for a, b in extra]})
            continue
        if undeclared:
            print(f"  !! BLOCKED-ON-CONSUMERS: {len(undeclared)} location(s) "
                  f"this spec does not declare:")
            for loc in undeclared:
                print(f"       {loc[0]}.{loc[1]}")
            print("     A half-migrated key is worse than a bad key. "
                  "NOT MIGRATED.")
            blocked_now.append({"name": s["name"], "producer": s["producer"],
                                "reason": "BLOCKED-ON-CONSUMERS",
                                "undeclared_locations": [f"{a}.{b}"
                                                         for a, b in
                                                         undeclared]})
            continue
        rep = []
        if m["recompute"]:
            rep.append(recompute_home(s["home"], s["id_column"], m["per_row"],
                                      m["old_ids"], apply_))
        else:
            per_file = defaultdict(list)
            for t, c in s["references"]:
                per_file[t].append(c)
            for t, cs in sorted(per_file.items()):
                rep.append(rewrite(t, cs, m["map"], apply_))
        for r in rep:
            print(f"    {r['status']:14s} {r['file']}  "
                  f"{r.get('cells_changed', r.get('cells_would_change', 0)):,}"
                  f" cell(s)"
                  + (f"  backup {r['backup']}" if r.get("backup") else "")
                  + (f"  {r['detail']}" if r.get("detail") else ""))
        bad = [r for r in rep if r["status"] not in ("OK", "DRY_RUN",
                                                     "COLUMN_ABSENT")]
        if bad:
            print(f"    !! VERIFICATION PROBLEM: {bad}")
        else:
            migrated.append(s["name"])
        results[s["name"]] = {"spec": {k: v for k, v in s.items()},
                              "map_stats": {k: v for k, v in m.items()
                                            if k not in ("map", "old_ids",
                                                         "per_row")},
                              "found_in": sorted(f"{a}.{b}" for a, b in found),
                              "files": rep}

    doc = {"generated": TODAY,
           "generated_at": started.isoformat(timespec="seconds"),
           "produced_by": "327_migrate_class7_keys_to_digests.py",
           "applied": apply_,
           "digest": "cedar_keys.surrogate_id -> "
                     "PREFIX-blake2b(NFKC, casefold, ws-collapsed parts "
                     "joined by 0x1F), 8 bytes / 16 hex",
           "migrated": migrated,
           "blocked_at_scan": blocked_now,
           "blocked_by_design": BLOCKED,
           "refused_no_stated_key": [{"name": s["name"],
                                      "producer": s["producer"],
                                      "reason": why} for s, why in refused],
           "specs": results,
           "old_to_new": {nm: results[nm].get("_map", {}) for nm in results}}
    # the full map, separately, so a quoted id can always be resolved
    doc["old_to_new"] = {}
    for s, m in ready:
        if s["name"] in migrated:
            doc["old_to_new"][s["name"]] = m["map"]

    MAP_OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = MAP_OUT.with_suffix(".json.part")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True, default=str),
                   encoding="utf-8")
    tmp.replace(MAP_OUT)
    back = json.loads(MAP_OUT.read_text(encoding="utf-8"))
    print("\n" + "=" * 78)
    print(f"MIGRATED {len(migrated)}: {', '.join(migrated) or '(none)'}")
    print(f"BLOCKED at scan {len(blocked_now)}, blocked by design "
          f"{len(BLOCKED)}, refused for no stated key {len(refused)}")
    print(f"wrote {MAP_OUT.relative_to(CEDAR)} "
          f"({MAP_OUT.stat().st_size:,} bytes, re-read OK, "
          f"{len(back['old_to_new'])} map(s))")
    print(f"{(datetime.now() - started).total_seconds():.1f}s")
    if not apply_:
        print("\nDRY RUN - nothing was written to data/. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
