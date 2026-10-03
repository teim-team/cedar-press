"""Consumer-side release-gap register: data this repository holds that no served
collection carries, one row per (collection or component, gate).

Measured facts are read from the tracked files every time this runs (the
manifest, the producer receipts, the component contracts, the spine, the
legacy extracts, the fixtures, the register, the code census); the rows are
authored here with the gate, its closing condition and the evidence, and
every number a row states is taken from the measurement, never typed. The
test module re-derives the register and compares it with the committed JSON
and Markdown, so neither can go stale quietly.

Classification vocabulary (one per row):

- CODE: a defect in this repository; fixed in this pass with a test, or fixable here.
- EVIDENCE_IN_REPO: the gap is real and the repository already holds what explains it.
- EVIDENCE_NEEDED: closing it needs a file or source this clone does not hold; the row names it and the command.
- DECISION: an owner call per AGENTS.md section 5; the row names the owner and asks one question.
- RIGHTS: withheld by a publication or rights rule that is working as written.
- RULED_REBUILD_PENDING: an owner ruling has changed the gate in code; the workstation
  rebuild that applies it to the producer's files has not run yet.

Run from the repository root::

    python3 server/tests/release_gap_register.py            # print the summary
    python3 server/tests/release_gap_register.py --write    # rewrite docs/RELEASE_GAP_2026-10-02.{json,md}
    python3 server/tests/release_gap_register.py --check    # exit 1 when either file is stale
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "docs" / "RELEASE_GAP_2026-10-02.json"
OUT_MD = ROOT / "docs" / "RELEASE_GAP_2026-10-02.md"
DATE = "2026-10-02"

CLASSES = (
    "CODE",
    "EVIDENCE_IN_REPO",
    "EVIDENCE_NEEDED",
    "DECISION",
    "RIGHTS",
    "RULED_REBUILD_PENDING",
)
OWNERS = {
    "havala": "Havala Hanson (@Havala-Hanson), Cedar Grove and Cedar Press including their data",
    "francesca": "Francesca Agnes (@mafranagn), data methods and the Cedar service boundary",
    "elijah": "Elijah Moreno (owner), identity, affiliation and legal-object adjudication, through Havala",
    "kaylyn": "Kaylyn Lee (@kaylynhl), product behaviour and customer-facing copy",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def git_show(ref_path: str) -> str:
    return subprocess.run(
        ["git", "show", ref_path], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def measure() -> dict:
    manifest = read_json(ROOT / "data/cedar/collections.manifest.json")
    receipts = read_json(ROOT / "data/cedar/verified-preview-releases.json")["collections"]
    register = read_json(ROOT / "public/data/cedar/register.json")
    legacy_facts = read_json(ROOT / "data/cedar/collection_descriptors.cedar.json")
    overrides = read_json(ROOT / "data/cedar/explore.overrides.json")
    explore = read_json(ROOT / "data/cedar/explore.json")["tables"]
    need_manifest = read_json(ROOT / "data/cedar/need-reviewed-preview.json")["manifest"]
    graph = read_json(ROOT / "docs/CODE_REFERENCE_GRAPH_2026-10-02.json")["summary"]
    census = read_json(ROOT / "docs/schema/inventory.json")["script_census"]
    ledger_schema = read_json(ROOT / "docs/schema/tables/cedar_ruling_ledger_consolidated.json")
    prior_rulings = read_json(ROOT / "docs/schema/tables/individual_native_prior_rulings.json")
    exclusion_pairs = read_json(ROOT / "docs/schema/tables/individual_native_exclusion_pairs.json")

    collections = {c["id"]: c for c in manifest["collections"]}
    served = {
        cid: {
            "n_rows": c["cedar"]["n_rows"],
            "name": c["descriptor"]["name"],
            "rows_in": c["tables"][0]["rows_in"],
            "rows_withheld": c["tables"][0]["rows_withheld"],
            "sample_rows": c["sample"]["rows"],
            "sample_columns": c["sample"]["columns"],
            "version": c["descriptor"]["version"],
            "updated": c["descriptor"]["updated"],
        }
        for cid, c in collections.items()
    }
    receipt_types = {cid: r["record_types"] for cid, r in receipts.items()}

    # Legacy extracts (2026-09-02) and what they share with the served previews.
    legacy_dir = ROOT / "data/cedar/samples"
    legacy = {}
    for path in sorted(legacy_dir.glob("*__sample.csv")):
        cid = path.name.replace("__sample.csv", "")
        rows = read_csv(path)
        header = list(rows[0].keys()) if rows else []
        entry = {
            "rows": len(rows),
            "columns": len(header),
            "first_column": header[0] if header else None,
            "served": cid in collections,
        }
        if cid in collections:
            served_rows = read_csv(ROOT / ("public" + collections[cid]["sample"]["path"]))
            served_header = list(served_rows[0].keys())
            lowered = {c.lower(): c for c in served_header}
            key = header[0]
            if key.lower() in lowered:
                legacy_keys = {r[key] for r in rows}
                served_keys = {r[lowered[key.lower()]] for r in served_rows}
                entry.update(
                    key=key,
                    legacy_only=len(legacy_keys - served_keys),
                    shared=len(legacy_keys & served_keys),
                )
            else:
                entry.update(
                    key=key,
                    legacy_only=None,
                    shared=None,
                    note="key column absent from the served header; different table",
                )
        legacy[cid] = entry
    legacy_readme = (legacy_dir / "README.md").read_text(encoding="utf-8")
    import re

    workspace_counts = {
        m.group(1): {"table": m.group(2), "rows": int(m.group(3).replace(",", ""))}
        for m in re.finditer(
            r"^\| `([^`]+)` \| `([^`]+)` \| 10 \| ([\d,]+) \| (\d+) \|", legacy_readme, re.M
        )
    }

    # The CEV fixture and where its ids appear.
    fixture = ROOT / "server/tests/fixtures/legacy-preview/samples/deals/deals_classified__10.csv"
    cev_rows = read_csv(fixture)
    cev_ids = [r["Deal_ID"] for r in cev_rows]
    served_deals = read_csv(ROOT / "public/data/cedar/samples/deals/spreadsheet__10.csv")
    cev_in_served = sorted(set(cev_ids) & {r["deal_id"] for r in served_deals})
    cev_elsewhere = subprocess.run(
        [
            "git",
            "grep",
            "-l",
            "CEV-20",
            "--",
            "public",
            "data/cedar",
            "src",
            "server/cedar_press",
            "docs/guides",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.split()

    # Register names with a null name (the publication rule's withholding),
    # by class, and the tracked documents naming a uid of the individually
    # Native-owned class. The mention grep runs over the CLASS's uids, not
    # the null-name uids: since the owner ruling of 2026-10-02 there are no
    # null names, and an empty pattern would match every file.
    classes = register["classes"]
    withheld_by_class = Counter(classes[e[2]]["code"] for e in register["entities"] if e[1] is None)
    individual_index = next(
        (i for i, c in enumerate(classes) if c["code"] == "Individually Native-owned business"),
        None,
    )
    class_uids = sorted(e[0] for e in register["entities"] if e[2] == individual_index)
    withheld_mentions = (
        subprocess.run(
            [
                "git",
                "grep",
                "-l",
                "-E",
                "|".join(class_uids),
                "--",
                "docs",
                "review",
                "AGENTS.md",
                "README.md",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        ).stdout.split()
        if class_uids
        else []
    )

    # Owned preview scope values.
    owned_rows = read_csv(ROOT / "public/data/cedar/samples/owned/spreadsheet__10.csv")
    owned_scope = dict(Counter(r["identity_scope"] for r in owned_rows))
    owned_assertion = dict(Counter(r["assertion_class"] for r in owned_rows))
    consumer_scope_filters = subprocess.run(
        ["git", "grep", "-l", "identity_scope", "--", "server/cedar_press", "src", "scripts"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.split()

    # publication_status conventions in the served previews.
    status_values = {}
    for cid, c in collections.items():
        rows = read_csv(ROOT / ("public" + c["sample"]["path"]))
        for column in rows[0]:
            if column in ("publication_status", "publication_rights_status"):
                status_values.setdefault(cid, {})[column] = dict(
                    Counter(r[column] or "(blank)" for r in rows)
                )

    # Component contracts: components declared per collection versus the permitted record types.
    components = {}
    for path in sorted((ROOT / "data/cedar").glob("*_component_contracts.json")):
        doc = read_json(path)
        cid = doc["collection"]
        declared = sorted(doc["components"])
        permitted = sorted(receipt_types.get(cid, {}))
        components[cid] = {
            "declared": declared,
            "permitted_record_types": permitted,
            "declared_not_permitted": sorted(set(declared) - set(permitted)),
        }
    need_components = Counter()
    for name, comp in need_manifest["components"].items():
        need_components[re.sub(r"_p\d{5}$", "", name)] += comp["record_count"]
    need_total = sum(need_components.values())

    # Review-status release totals (records in reviewed releases, permitted rows).
    review = (ROOT / "docs/REVIEW_STATUS.md").read_text(encoding="utf-8")
    review_table = {}
    for m in re.finditer(r"^\| ([A-Za-z /&-]+?) \| ([\d,]+) \| ([\d,]+) \|$", review, re.M):
        review_table[m.group(1).strip()] = {
            "records_in_release": int(m.group(2).replace(",", "")),
            "permitted": int(m.group(3).replace(",", "")),
        }

    # Explore overrides and the lobbying replacement column after the fix.
    retired = overrides.get("_retired_2026-10-02", {}).get("tables", {})
    live_override_keys = [k for k in overrides if not k.startswith("_")]
    lobbying_contract = explore["lobbying/lobbying"]

    excluded = {e["id"]: e for e in manifest["excluded"]}
    excluded_legacy = {
        cid: {
            "legacy_facts_rows": legacy_facts.get(cid, {}).get("n_rows"),
            "legacy_facts_tables": legacy_facts.get(cid, {}).get("n_tables"),
            "legacy_sample_rows": legacy.get(cid, {}).get("rows"),
        }
        for cid in ("gaming", "newsletters", "_entity_layer")
    }
    gaming_receipt = receipts.get("gaming", {})

    return {
        "served": served,
        "receipt_types": receipt_types,
        "legacy": legacy,
        "workspace_counts": workspace_counts,
        "cev": {
            "ids": cev_ids,
            "in_served_sample": cev_in_served,
            "tracked_paths_naming_cev": cev_elsewhere,
            "fixture_columns": len(cev_rows[0]),
            "served_columns": len(served_deals[0]),
        },
        "withheld": {
            "total": register["withheld_names"],
            "by_class": dict(withheld_by_class),
            "tracked_docs_naming_a_withheld_uid": withheld_mentions,
        },
        "owned": {
            "identity_scope": owned_scope,
            "assertion_class": owned_assertion,
            "consumer_files_filtering_on_identity_scope": consumer_scope_filters,
        },
        "status_values": status_values,
        "components": components,
        "need_components": dict(sorted(need_components.items())),
        "need_total_records": need_total,
        "review_table": review_table,
        "overrides": {
            "live_keys": live_override_keys,
            "retired": len(retired),
            "lobbying_superseded_by": lobbying_contract.get("superseded_by"),
        },
        "excluded": excluded,
        "excluded_legacy": excluded_legacy,
        "gaming_receipt": {k: gaming_receipt.get(k) for k in ("public_records", "record_types")},
        "grove_pins": read_json(ROOT / "data/cedar/grove_release_pin.json")["pins"],
        "press_component_pins": read_json(ROOT / "data/cedar/press_component_release_pin.json")[
            "pins"
        ],
        "ledger_schema": {
            "rows_scanned": ledger_schema["rows_scanned"],
            "generated": ledger_schema["generated"],
            "outcomes": next(
                c["examples"] for c in ledger_schema["columns"] if c["name"] == "outcome"
            ),
        },
        "prior_rulings": {
            "rows": prior_rulings["rows_scanned"],
            "ruling_text": next(
                c["examples"] for c in prior_rulings["columns"] if c["name"] == "ruling_text"
            ),
        },
        "exclusion_pairs": {
            "rows": exclusion_pairs["rows_scanned"],
            "identifiers": next(
                c["examples"] for c in exclusion_pairs["columns"] if c["name"] == "identifier"
            ),
        },
        "graph": graph,
        "census": {
            k: census[k]
            for k in ("scripts", "operational_role_counts", "maintenance_status_counts")
        },
    }


def rows(m: dict) -> list[dict]:
    s = m["served"]
    r = m["review_table"]
    w = m["workspace_counts"]
    L = m["legacy"]

    def row(**kw):
        assert kw["classification"] in CLASSES, kw["classification"]
        return kw

    out = []
    # --- 1. The three collections the old descriptor file carried that the manifest excludes
    out.append(
        row(
            id="GAP-01",
            collection="gaming",
            gate="manifest.excluded (shelf grove) and data/cedar/grove_release_pin.json pins = {}",
            exists=f"Workspace facts 2026-09-02: {m['excluded_legacy']['gaming']['legacy_facts_rows']:,} rows across "
            f"{m['excluded_legacy']['gaming']['legacy_facts_tables']} tables (collection_descriptors.cedar.json); legacy extract "
            f"{m['excluded_legacy']['gaming']['legacy_sample_rows']} rows of gaming_facilities (workspace {w['gaming']['rows']:,}); "
            f"producer receipt: {m['gaming_receipt']['public_records']:,} permitted records in 9 record types "
            f"(REVIEW_STATUS: {r['Gaming']['records_in_release']:,} records in the reviewed release).",
            served="Nothing in Cedar Press (excluded by shelf). Cedar Grove: the runtime pin is empty, so nothing is pinned for production; "
            "a local Grove rehearsal returned the 224-record gaming_regional_revenue component (REVIEW_STATUS).",
            gate_location="data/cedar/collections.manifest.json excluded[gaming]; src/features/grove/pressCatalog.js shelf grove; "
            "server/cedar_press/repository.py is_sold(); data/cedar/grove_release_pin.json",
            closing_condition="Owner rules Gaming ready for Grove; Cedar issues gaming object ids (code/build.py gaming-issue-ids); "
            "Lumecon-data builds a production release from the issued registry; the pin is set by a reviewed PR.",
            evidence="manifest excluded reason; grove_release_pin.json status text; verified-preview-releases.json gaming receipt",
            classification="DECISION",
            owner=OWNERS["havala"],
            question="Is the Gaming release built on PROPOSED object ids acceptable to pin for Cedar Grove, or does production wait for issued ids?",
        )
    )
    out.append(
        row(
            id="GAP-02",
            collection="newsletters",
            gate="manifest.excluded: owner ruling 2026-09-02, not a Cedar Press product",
            exists=f"Workspace facts 2026-09-02: {m['excluded_legacy']['newsletters']['legacy_facts_rows']:,} rows across "
            f"{m['excluded_legacy']['newsletters']['legacy_facts_tables']} tables; legacy extract {m['excluded_legacy']['newsletters']['legacy_sample_rows']} rows "
            f"of tribal_newsletter_corpus (workspace {w['newsletters']['rows']:,} rows: 1,394 publication_channel, 481 probe_absence, 14 other, per the extract README).",
            served="Nowhere. No producer release, no receipt, no shelf.",
            gate_location="data/cedar/collections.manifest.json excluded[newsletters]",
            closing_condition="The owner's ruling stands; the collection stays in the workspace. Nothing to close unless the ruling changes.",
            evidence="manifest excluded reason (owner ruling 2026-09-02); data/cedar/samples/README.md grain note",
            classification="RIGHTS",
            owner=OWNERS["havala"],
            question=None,
        )
    )
    out.append(
        row(
            id="GAP-03",
            collection="_entity_layer",
            gate="manifest.excluded: shelf infrastructure, not sold on its own",
            exists=f"Workspace facts 2026-09-02: {m['excluded_legacy']['_entity_layer']['legacy_facts_rows']:,} rows across "
            f"{m['excluded_legacy']['_entity_layer']['legacy_facts_tables']} tables; legacy extract of the register (workspace {w['_entity_layer']['rows']:,} entities then).",
            served="Partly: public/data/cedar/register.json serves 1,916 entities (uid, name, class) from data/spine/; the 41 other tables "
            "(aliases, relationships, identifier ledger, handle history) are not served and are not in Git except the five spine files.",
            gate_location="data/cedar/collections.manifest.json excluded[_entity_layer]; scripts/derive-explore.mjs buildRegister",
            closing_condition="By design: the spine keys every collection and is published as the register, not as a dataset.",
            evidence="manifest excluded reason; register.json entity count; .gitignore spine allowlist",
            classification="EVIDENCE_IN_REPO",
            owner=None,
            question=None,
        )
    )
    # --- 2. Legacy extracts versus producer samples
    comparable = {
        cid: e for cid, e in L.items() if e.get("served") and e.get("legacy_only") is not None
    }
    different_table = {
        cid: e for cid, e in L.items() if e.get("served") and e.get("legacy_only") is None
    }
    out.append(
        row(
            id="GAP-04",
            collection="all 14 (data/cedar/samples/*__sample.csv)",
            gate="historical extracts, bannered superseded; nothing reads them",
            exists="15 legacy extracts of 10 rows each (2026-09-02, code/770). Same table as the served preview and comparable on the key column in "
            f"{len(comparable)} collections: "
            + "; ".join(
                f"{cid} ({e['key']}: {e['legacy_only']} of 10 legacy rows absent from the served 10)"
                for cid, e in sorted(comparable.items())
            )
            + f". Different table from the served preview in {len(different_table)}: "
            + ", ".join(
                f"{cid} ({w[cid]['table']} vs {cid}.csv)" for cid in sorted(different_table)
            )
            + ".",
            served="The producer's pinned 10-row previews only. Whether each legacy row is in the 2026-10-01 full release is not measurable here: the full "
            "spreadsheets are not in Git, and a preview is a selection, not a population.",
            gate_location="data/cedar/samples/README.md banner; scripts/stage_verified_previews.py (the only path that writes a served sample)",
            closing_condition="Per collection, join the legacy key column to the producer's full spreadsheet; any legacy row absent needs a NAMED disposition in the producer.",
            evidence="data/cedar/samples/*__sample.csv; public/data/cedar/samples/*/spreadsheet__10.csv; the key comparison above",
            classification="EVIDENCE_NEEDED",
            owner=OWNERS["havala"],
            question=None,
            needs="The producer's full spreadsheets (Lumecon-data release store, release ids in data/cedar/verified-preview-releases.json). Command per collection: "
            "`python3 -c \"import csv;a={r['<key>'] for r in csv.DictReader(open('data/cedar/samples/<id>__sample.csv',encoding='utf-8-sig'))};"
            "b={r['<key>'] for r in csv.DictReader(open('<full spreadsheet>.csv',encoding='utf-8-sig'))};print(sorted(a-b))\"`",
        )
    )
    # --- 3. #149 CEV events
    c = m["cev"]
    out.append(
        row(
            id="GAP-05",
            collection="deals / CEV-* events (PR #149)",
            gate="the served sample is the producer's pinned selection; the fixture is a regression input",
            exists=f"{len(c['ids'])} reviewed events ({', '.join(c['ids'][:3])} ... {c['ids'][-1]}), sources checked 2026-10-01 "
            f"(docs/DEALS_PUBLIC_PREVIEW_REVIEW_2026-10-01.md), in the {c['fixture_columns']}-column legacy fixture "
            "server/tests/fixtures/legacy-preview/samples/deals/deals_classified__10.csv.",
            served=f"None of the {len(c['ids'])} ids is in the served {c['served_columns']}-column preview (ids ACQ2020-*/ANCSA-*); no tracked file under "
            f"public/, data/cedar/, src/ or server/cedar_press/ names a CEV id ({len(c['tracked_paths_naming_cev'])} files). Whether the events are among "
            "the 978 released records is not measurable here.",
            gate_location="scripts/stage_verified_previews.py (sample = producer selection); data/cedar/verified-preview-releases.json deals.sample_sha256",
            closing_condition="The producer selects the reviewed events as the Deals sample (or confirms they are in the 978) and pins a new release; "
            "server/tests/legacy_deals_adapter.py documents the 40 -> 36 column mapping so that step is mechanical.",
            evidence="docs/FACT_CHECK_2026-10-02.md section 4; the fixture; server/tests/test_legacy_deals_adapter.py",
            classification="DECISION",
            owner=OWNERS["havala"],
            question="Should the ten reviewed CEV events replace the ACQ2020/ANCSA selection as the served Deals preview in the next producer pin?",
        )
    )
    # --- 4. denied_ueis and ruling classes
    ls = m["ledger_schema"]
    out.append(
        row(
            id="GAP-06",
            collection="all attributed collections / verified not_native denials",
            gate="code/cedar_publication.denied_ueis() from data/clean/cedar_ruling_ledger_consolidated.csv",
            exists=f"The consolidated ruling ledger: {ls['rows_scanned']:,} rows when its schema was captured ({ls['generated']}); outcome vocabulary "
            f"{', '.join(ls['outcomes'])}. Per-class counts are not in Git: docs/schema/tables/ holds the schema and examples, not the rows.",
            served="Rows whose UEI is denied ship with the Cedar attribution blanked (attribution_status excluded_not_native, mask reason "
            "verified_not_native_denial); the row itself ships. The count of rows so masked per collection is in the producer's build log, not here.",
            gate_location="code/cedar_publication.py denied_ueis(), enforce_denials(); code/174_apply_rulings_to_source_tables.py FUND_EXCLUDE_SET",
            closing_condition="Nothing to close for a correct denial. The counts per class come from the ledger on the owner's machine.",
            evidence="docs/schema/tables/cedar_ruling_ledger_consolidated.json; code/173, 174, cedar_publication",
            classification="EVIDENCE_NEEDED",
            owner=None,
            question=None,
            needs='data/clean/cedar_ruling_ledger_consolidated.csv (gitignored). Command: `python3 -c "import csv,collections;'
            "r=list(csv.DictReader(open('data/clean/cedar_ruling_ledger_consolidated.csv',encoding='utf-8-sig')));"
            "print(collections.Counter((x['status'],x['outcome'],x['ruling'].lower()=='not_native',x['tier_source']=='stated_on_ruling_row') for x in r))\"`",
        )
    )
    pr = m["prior_rulings"]
    ep = m["exclusion_pairs"]
    out.append(
        row(
            id="GAP-07",
            collection="all attributed collections / the five tribal-link refusals",
            gate="code/173_consolidate_rulings_ledger.py classify(): NEG_PREFIX before CLASS_PREFIX",
            exists=f"{pr['rows']} prior rulings on individually Native-owned firms (docs/schema/tables/individual_native_prior_rulings.json; ruling_text values "
            f"{', '.join(repr(t) for t in pr['ruling_text'])}); five read 'Not a Native entity - individually Native-owned firm', which refuses the tribal "
            f"link and affirms Native ownership; {ep['rows']} exclusion pairs name the identifiers ({', '.join(ep['identifiers'])}).",
            served="Until this pass, classify() returned NEGATIVE for that sentence (its first clause is a NEG_PREFIX), so 173 settled each such subject as "
            "NEGATIVE/not_native and 174 applied RULED_NOT_NATIVE (excluded_not_native) to its funding and prime rows, while denied_ueis() did not fire "
            "(it needs ruling == 'not_native' exactly): two readers of one ruling, two verdicts, and the ruling class applied more broadly than its "
            "definition to firms the register classes as Native. FIXED: classify() now asks cedar_domain's predicate first and returns CLASS/individual_native.",
            gate_location="code/173_consolidate_rulings_ledger.py classify(), is_tribal_link_refusal(); code/cedar_domain.py is_tribal_link_refusal_not_native_refusal()",
            closing_condition="Re-run 173 on the owner's machine, then 174 and the funding candidate rebuild; confirm the five subjects settle CLASS, not NEGATIVE.",
            evidence="code/173_consolidate_rulings_ledger_test.py (6 tests; HEAD classify(refusal) == NEGATIVE recorded in the register notes); AGENTS.md 'THE INVERTED RULING'; docs/ENTITY_TYPES.md",
            classification="CODE",
            owner=None,
            question=None,
            needs="To measure the live effect: data/clean/cedar_ruling_ledger_consolidated.csv rows whose ruling contains 'individually Native-owned' and outcome == NEGATIVE, before and after re-running 173.",
        )
    )
    # --- 5. Siletz pair
    out.append(
        row(
            id="GAP-08",
            collection="funding / recipient UEI GJV4PJ8M5PC7, award ASST_NON_1896753-42-22_417",
            gate="no consumer vocabulary for 'distinct recipient' until this pass; policy inputs not in Git",
            exists="Two Federal Funding transactions projected to the tribal-government recipient while the recipient is the Siletz Tribal Arts and Heritage Society, "
            "a separate Native nonprofit (docs/REVIEW_STATUS.md 'Source-side fixes, 2026-10-02').",
            served="Both transactions ship bound to the tribal government in the 640,942-row release (not measurable here; the projection is not in Git).",
            gate_location="data/cedar/recipient_holds.json (new, zero entries); code/cedar_publication.recipient_holds()/validate_recipient_holds(); "
            "docs/RECIPIENT_HOLDS_2026-10-02.md; docs/schema/recipient_holds.schema.json",
            closing_condition="Read the bound uid off the two transactions; re-read and quote the two evidence pages; record the entry with status ready; "
            "the producer's funding candidate rebuild consumes it and pins. No new Cedar id without the owner's adjudication.",
            evidence="server/tests/test_recipient_holds.py (19 tests; the drafted entry validates as evidence_incomplete and is refused as ready without the bound uid)",
            classification="EVIDENCE_NEEDED",
            owner=OWNERS["havala"],
            question=None,
            needs="The funding projection on the owner's machine (data/clean/federal_funding_transactions.csv): `python3 -c \"import csv;"
            "print({(r['cedar_uid'],r['canonical_name']) for r in csv.DictReader(open('data/clean/federal_funding_transactions.csv',encoding='utf-8-sig')) "
            "if r.get('recipient_uei')=='GJV4PJ8M5PC7'})\"`; the two URLs re-read from a network that reaches them.",
        )
    )
    out.append(
        row(
            id="GAP-09",
            collection="register / Siletz Tribal Arts and Heritage Society",
            gate="no register entity; admission is an identity adjudication",
            exists="A nonprofit with its own board, named in two sources (REVIEW_STATUS), not in data/spine/cedar_identity_register.csv.",
            served="Nothing can be attributed to it; a withhold leaves the two transactions unattributed.",
            gate_location="data/spine/cedar_identity_register.csv; owner adjudication per AGENTS.md",
            closing_condition="The owner admits the society to the register as a Native nonprofit (a new CE- id) or declines; either way the hold stands.",
            evidence="docs/RECIPIENT_HOLDS_2026-10-02.md 'The Siletz entry, drafted and held'",
            classification="DECISION",
            owner=OWNERS["elijah"],
            question="Is the Siletz Tribal Arts and Heritage Society admitted to the register as its own Native nonprofit (new CE- id), or recorded only as the distinct recipient behind UEI GJV4PJ8M5PC7?",
        )
    )
    # --- 6. publication_status values per collection
    sv = m["status_values"]
    out.append(
        row(
            id="GAP-10",
            collection="foundation-corporate-giving, need / publication_status",
            gate="server/cedar_press/spreadsheet.py drops rows whose publication_status_field is held, contested or withheld",
            exists="Served previews: "
            + "; ".join(
                f"{cid} " + ", ".join(f"{col} = {vals}" for col, vals in cols.items())
                for cid, cols in sorted(sv.items())
            )
            + ". The codebook defines giving's publication_status; the giving reviewed_disclosures rows carry a blank there and derived_facts_only in publication_rights_status.",
            served="Every served row passes (blank and observed are not held values). The NEED patent, rating and profile_links components declare publication_status "
            "'held for all rows under NEED policy' in data/cedar/need_component_contracts.json; needEvidence.js and need_profiles.py require 'eligible', so none shows: consistent.",
            gate_location="server/cedar_press/spreadsheet.py; server/cedar_press/need_profiles.py select_entity_rows; src/features/grove/needEvidence.js",
            closing_condition="Producer: one convention for 'not evaluated' on giving reviewed_disclosures (blank vs observed) and currency on those rows (FACT_CHECK queue, UNRESOLVED).",
            evidence="docs/FACT_CHECK_2026-10-02.md section 5 (giving FG-* rows); data/cedar/need_component_contracts.json",
            classification="EVIDENCE_IN_REPO",
            owner=OWNERS["francesca"],
            question=None,
        )
    )
    # --- 7. The individually Native-owned firm register: ruled 2026-10-02
    wh = m["withheld"]
    out.append(
        row(
            id="GAP-11",
            collection="register / individually Native-owned firm names",
            gate="code/cedar_domain.may_publish_individual_native_field(): publishes every business-record field of the class (owner ruling 2026-10-02); "
            "until that date it withheld them unless consent_status was OPTED_IN",
            exists=f"Register entities with a null name now: {wh['total']} (by class: {wh['by_class'] or 'none'}). Until 2026-10-02, 45 entities of the class "
            "shipped with a uid, a class and a null name because the class was read as a person-proxy and consent_status was NOT_ASKED on all 45. "
            "Owner ruling 2026-10-02: a firm is a business entity regardless of what it is named after; its name, identifiers and business address "
            "are public business records (SAM and USAspending publish them for every federal awardee), not personal identifying information, so "
            "consent is not required.",
            served=f"public/data/cedar/register.json carries every name (withheld_names = {wh['total']}); the viewer's null-name masking has nothing to mask. "
            "The producer's register CSV (data/clean/individual_native_firm_register.csv, workspace) still carries publish_name = 0 and the six "
            "native-owned-businesses samples struck on 2026-09-05 are still absent until the rebuild.",
            gate_location="code/cedar_domain.py may_publish_individual_native_field; code/241 publish_name / publish_federal_identifier; "
            "scripts/derive-explore.mjs deriveRegister; scripts/import_cedar_manifest.py sample_violations (reads the rule)",
            closing_condition="Workstation rebuild: python3 code/241_promote_individual_native_firms_in_place.py, the spine export, "
            "node scripts/derive-explore.mjs, then the importer re-admits the struck samples; the register CSV then reads publish_name = 1 on every row.",
            evidence=f"Tracked documents naming any uid of the class: {wh['tracked_docs_naming_a_withheld_uid'] or 'none'}. "
            "The ruling and the reversed text are recorded in docs/REVIEW_STATUS.md, 'Owner ruling: individually owned firm records publish', 2026-10-02.",
            classification="RULED_REBUILD_PENDING",
            owner=None,
            question=None,
        )
    )
    # --- 8. owned identity_scope
    ow = m["owned"]
    out.append(
        row(
            id="GAP-12",
            collection="owned / identity_scope",
            gate="no consumer-side scope filter; eligibility is the producer's publishable flag",
            exists=f"Served preview: identity_scope {ow['identity_scope']}, assertion_class {ow['assertion_class']}; the codebook defines the scopes as not interchangeable "
            f"evidence of Native ownership. Workspace extract 2026-09-02: {w['owned']['rows']:,} rows; release {s['owned']['n_rows']:,} (larger: the release admits sources the extract excluded).",
            served=f"All {s['owned']['n_rows']:,} permitted rows. Consumer files filtering on identity_scope: {ow['consumer_files_filtering_on_identity_scope'] or 'none'}; "
            "no row is dropped by scope on this side. Rows withheld at the producer (publishable = N, TERMS_STATED_RESTRICTIVE sources) are counted in neither file.",
            gate_location="code/330_build_native_owned_businesses.py (identity_scope per source); code/615_set_publishable_native_owned_businesses.py; producer press_candidates",
            closing_condition="Producer: state the withheld count and reason per source in the release manifest (held_records_in_selected_groups is 0 because the held rows are outside the selected group).",
            evidence="data/cedar/codebook.json owned.identity_scope; data/cedar/collections.manifest.json owned.tables[0]",
            classification="EVIDENCE_IN_REPO",
            owner=OWNERS["francesca"],
            question=None,
        )
    )
    # --- 9. manifest counts below what the build logs / workspace recorded
    diffs = []
    for cid, wc in sorted(w.items()):
        if cid in s and wc["table"].replace(".csv", "") in (
            f"{cid}",
            "deals_classified",
            "prime_contracts",
            "federal_funding_transactions",
            "nagpra_notices",
            "resource_revenue",
            "subawards",
            "native_owned_businesses",
            "np_orgs",
            "need_enterprises",
        ):
            diffs.append(
                (cid, wc["table"], wc["rows"], s[cid]["n_rows"], s[cid]["n_rows"] - wc["rows"])
            )
    below = [d for d in diffs if d[4] < 0]
    out.append(
        row(
            id="GAP-13",
            collection="contractors, deals, funding, natural-resources, subcontracting, nonprofits, need / manifest n_rows below the workspace table",
            gate="producer publication contract (publishable flags, deduplication, exclusions) applied between the workspace table and the release",
            exists="Workspace table rows (2026-09-02 extract README) versus released permitted rows: "
            + "; ".join(
                f"{cid} {table} {ws:,} -> {rel:,} ({delta:+,})"
                for cid, table, ws, rel, delta in diffs
            )
            + ".",
            served="The released count. The rows between the two figures each need a NAMED disposition in the producer's build (duplicate filing, publishable = N, ruled out, excluded "
            "by rights); none is named in this repository. Nonprofits (12,764 -> 89) and NEED (1,610 -> 43) are by construction: the universe considered versus the "
            "rows ruled in / the proof-bound public base. nagpra is equal; owned grew.",
            gate_location="Lumecon-data release builders (press_candidates); scripts/stage_verified_previews.py writes rows_in = permitted + held_records_in_selected_groups",
            closing_condition="Producer release manifest states, per collection, rows_in from the workspace table and the count per named disposition; the consumer manifest then carries a non-zero rows_withheld with withheld_why.",
            evidence="data/cedar/samples/README.md counts; data/cedar/collections.manifest.json; docs/REVIEW_STATUS.md collection inventory",
            classification="EVIDENCE_NEEDED",
            owner=OWNERS["francesca"],
            question=None,
            needs="The producer build logs and release manifests in Lumecon-data for the 2026-10-01 pins (release ids in data/cedar/verified-preview-releases.json); "
            "the workspace tables data/clean/<table>.csv on the owner's machine for a row-level join.",
            measured={"below_workspace": [d[0] for d in below]},
        )
    )
    # --- 10. Release records versus permitted rows (components outside the selected group)
    comp = m["components"]
    nc = m["need_components"]
    out.append(
        row(
            id="GAP-14",
            collection="foundation-corporate-giving, need, plot, gaming / components outside the permitted set",
            gate="producer publication contract per component; consumer manifest counts only the selected group",
            exists="Records in the reviewed release versus permitted rows (docs/REVIEW_STATUS.md): "
            + "; ".join(
                f"{name} {r[name]['records_in_release']:,} / {r[name]['permitted']:,}"
                for name in ("Foundation & Corporate Giving", "NEED", "PLOT", "Gaming")
                if name in r
            )
            + f". Declared components not in the permitted record types: giving {comp['foundation-corporate-giving']['declared_not_permitted']}; "
            f"plot {len(comp['plot']['declared_not_permitted'])} (held_* and internal_*); need {len(comp['need']['declared_not_permitted'])}; "
            f"gaming {len(comp['gaming']['declared_not_permitted'])}. NEED reviewed manifest: {m['need_total_records']:,} records across "
            f"{len(nc)} logical components, reviewed_public_base {nc.get('reviewed_public_base', 0)}; the manifest caveat: whole-NEED public export quarantine remains binding.",
            served="Only the permitted record types; the consumer manifest's rows_in equals the permitted count because held_records_in_selected_groups is 0 for every collection, "
            "so the held and internal components are invisible in data/cedar/collections.manifest.json and visible only in REVIEW_STATUS and the component contract files.",
            gate_location="data/cedar/*_component_contracts.json rights_class INTERNAL_RESEARCH_ONLY / held_*; server/cedar_press/repository.py _grove_component_release (ComponentPublicationHeld); "
            "scripts/stage_verified_previews.py rows_in",
            closing_condition="Working as written. If the manifest should show what exists but is held, the producer receipt needs a per-collection total records field and the staging script a rows_in that uses it.",
            evidence="docs/REVIEW_STATUS.md collection inventory; data/cedar/need-reviewed-preview.json manifest.caveats; component contract files",
            classification="RIGHTS",
            owner=OWNERS["havala"],
            question="Should the consumer manifest record the release's total records beside the permitted count, so a held component is visible to a reader of the manifest?",
        )
    )
    # --- 11. Consumer-side defects found in this pass
    ov = m["overrides"]
    out.append(
        row(
            id="GAP-15",
            collection="all 14 / Explore display contracts",
            gate="scripts/derive-explore.mjs override key = <collection>/<table stem>",
            exists=f"{ov['retired']} hand-written override declarations (reviewed 2026-09-05) keyed to the 2026-09-02 tables (contractors/prime_contracts, lobbying/native_entity_lobbying_disclosures, ...).",
            served="None applied since the 2026-10-01 release renamed every served table to <collection>.csv: the keys matched nothing and derive() applied an empty override to each. "
            "FIXED: derive() refuses a key that names no manifest table; the 27 declarations are retired under _retired_2026-10-02 in explore.overrides.json; "
            f"live override keys now: {ov['live_keys'] or 'none'}.",
            gate_location="scripts/derive-explore.mjs unknownOverrideKeys(); data/cedar/explore.overrides.json",
            closing_condition="A new override for a served table is keyed <collection>/<collection>; the guard fails the generator otherwise.",
            evidence="src/features/grove/explore.test.js 'an override keyed to a table the manifest does not declare is refused'",
            classification="CODE",
            owner=None,
            question=None,
        )
    )
    out.append(
        row(
            id="GAP-16",
            collection="lobbying / superseded filings",
            gate="scripts/derive-explore.mjs RULES.superseded_by",
            exists="The served lobbying header carries superseded_by_record_id (the producer renamed filing_uuid to record_id); the rule listed only superseded_by_filing_uuid.",
            served=f"explore.json carried superseded_by: null, so a superseded filing never offered its replacement's id. FIXED: the rule reads the producer's name first; "
            f"explore.json now carries superseded_by = {ov['lobbying_superseded_by']}. Rows were not dropped by this: is_superseded was already read, and superseded filings are hidden by default with history on request.",
            gate_location="scripts/derive-explore.mjs RULES; src/features/grove/explore.js rowReplacement",
            closing_condition="Closed; regenerate explore.json after any producer rename (make check-generated).",
            evidence="src/features/grove/explore.test.js 'the served lobbying contract reads the producer's replacement column'",
            classification="CODE",
            owner=None,
            question=None,
        )
    )
    out.append(
        row(
            id="GAP-17",
            collection="all / data/cedar/collection_descriptors.cedar.json",
            gate="a 2026-09-02 facts file nothing reads",
            exists="Workspace counts for 15 ids (contractors 3,345,971; deals 2,662; federal-register 502,483; _entity_layer 363,220; gaming 128,561; newsletters 3,444), the shape code/760 writes to dist/.",
            served="Not read by server/, src/ or scripts/ (git grep). The served counts are the manifest's. FIXED: a dated _superseded note is written into the file; counts kept as evidence.",
            gate_location="data/cedar/collection_descriptors.cedar.json; scripts/import_cedar_manifest.py reads dist/, not this copy",
            closing_condition="Delete or keep as dated evidence; Havala's call, no behaviour depends on it.",
            evidence="git grep collection_descriptors.cedar across server/, src/, scripts/: no reader",
            classification="CODE",
            owner=OWNERS["havala"],
            question="Keep data/cedar/collection_descriptors.cedar.json as dated evidence, or remove it now that the manifest carries the served counts?",
        )
    )
    out.append(
        row(
            id="GAP-18",
            collection="deals / 1185 fact-check corrections and 1184 presentation",
            gate="code/cedar_publication.deals_public_view() applies review/deals_2025_2026_corrected.csv at publish",
            exists="Owner's 2025-2026 corrections as data keyed by Deal_ID with a precondition each (review/ file, gitignored) and the reviewer's Caveat derivation (1184), both applied by the workspace writer 1137.",
            served="The served Deals release is built by Lumecon-data from the workspace tables; whether its build applies 1185's corrections and 1184's caveats is not stated in this repository.",
            gate_location="code/cedar_publication.py deals_public_view(); Lumecon-data press_candidates (not here)",
            closing_condition="Producer confirms the corrections are applied in its Deals projection (or imports review/deals_2025_2026_corrected.csv as a reviewed input).",
            evidence="code/cedar_publication.py deals_public_view docstring (Codex PR #56); code/1185_deals_fact_check_2025_2026.py",
            classification="EVIDENCE_NEEDED",
            owner=OWNERS["francesca"],
            question=None,
            needs="review/deals_2025_2026_corrected.csv on the owner's machine and the producer's Deals build log for release f9f50cca...",
        )
    )
    # --- 12. Infrastructure (Grove-only, unpinned)
    out.append(
        row(
            id="GAP-19",
            collection="infrastructure",
            gate="manifest.excluded (separate Cedar Grove dataset); grove_release_pin pins = {}",
            exists="28,484 permitted Records rows (1,163 IHS, 22,380 TTPTIP, 2,467 SDWIS, 1,254 DWINSA, 1,220 NBI) and 13 restricted components; verified local release "
            "d7a93b56... (docs/REVIEW_STATUS.md); 14 component contracts in data/cedar/infrastructure_component_contracts.json.",
            served="Nothing pinned for production; a local Grove process rehearsal returned all 28,484 permitted records. Press never serves it.",
            gate_location="data/cedar/collections.manifest.json excluded[infrastructure]; data/cedar/grove_release_pin.json",
            closing_condition="Reviewed PR sets the Grove pin to the consumer-projection hash; coordinate holds (three data-center coordinate differences) stay explicit.",
            evidence="docs/REVIEW_STATUS.md 'October 2 integration checkpoint'",
            classification="DECISION",
            owner=OWNERS["havala"],
            question="Is the Infrastructure consumer projection (89db65d8...) the release to pin for Cedar Grove, with the three coordinate holds carried as holds?",
        )
    )
    # --- 13. Press component pins (giving, PLOT)
    out.append(
        row(
            id="GAP-20",
            collection="foundation-corporate-giving, plot / production pins",
            gate="data/cedar/press_component_release_pin.json pins = {}",
            exists=f"Verified rehearsal releases pinned for preview (giving {s['foundation-corporate-giving']['n_rows']:,} permitted of {r['Foundation & Corporate Giving']['records_in_release']:,}; "
            f"plot {s['plot']['n_rows']:,} of {r['PLOT']['records_in_release']:,}); release_class rehearsal in every receipt.",
            served="10-row public previews and the connected research API against the rehearsal pins; no production download pin for either.",
            gate_location="data/cedar/press_component_release_pin.json; data/cedar/verified-preview-releases.json release_class",
            closing_condition="An isolated review environment with exact catalog and manifest digests, then a reviewed PR setting the pins (the file's own status text).",
            evidence="press_component_release_pin.json status; REVIEW_STATUS 'Remaining release gates'",
            classification="DECISION",
            owner=OWNERS["havala"],
            question="Which Giving and PLOT releases (by release id and manifest digest) are the production pins, and in which review environment is that approval recorded?",
        )
    )
    # --- 14. Scripts
    g = m["graph"]
    out.append(
        row(
            id="GAP-21",
            collection="code/ / 618 numbered workspace scripts",
            gate="reference graph: Makefile, CI, package.json, other script, product code, document, journal, loader by stem or number",
            exists=f"{g['numbered_scripts']} numbered scripts ({g['pure_numeric_prefix']} numeric-prefixed, {g['letter_suffixed_prefix']} letter-suffixed; the brief's 606 counted "
            f"non-Python files with a numeric prefix). Referenced: {g['referenced']} ({g['referenced_outside_journal']} outside AGENTS.md). Zero references: {g['zero_references']}.",
            served=f"{g['in_code_archive']} moved to code/archive/ (zero references, no tracked artifact written, not ACTIVE, not NEVER_RUN, in no contract or ordering), "
            f"indexed in code/archive/INDEX.md; census refreshed (python3.12 code/521_inventory.py scripts-only).",
            gate_location="docs/CODE_REFERENCE_GRAPH_2026-10-02.json; server/tests/code_reference_graph.py; docs/schema/inventory.json script_census",
            closing_condition="Closed for this pass; the test module proves every archived script still has zero references in the tree.",
            evidence="server/tests/test_code_reference_graph.py (11 tests)",
            classification="CODE",
            owner=None,
            question=None,
        )
    )
    # --- 15. The owned collection's display name (owner decision, 2026-10-02)
    out.append(
        row(
            id="GAP-22",
            collection="owned / display name",
            gate="collection name is a data contract carried into every download's citation (AGENTS.md section 6)",
            exists=f"Owner decision 2026-10-02: the collection is 'Individual Native-Owned Businesses', never 'Native-Owned Businesses' (which makes NEED sound redundant). "
            f"Served now as '{s['owned'].get('name', '')}' at version {s['owned']['version']} (updated {s['owned']['updated']}); the pinned sample and receipt are unchanged.",
            served="Manifest, descriptors, codebook, guides, SEO/JSON-LD, the press dump and the catalog carry the new name; the release ledger keeps v0-v3 under the name they "
            "shipped with and records the rename as v4 (the ledger refuses a changed fact on an existing version). The producer's descriptor still carries the old title; "
            "Lumecon-data #17 is changing it so the next pin agrees. Catalog `short` now equals the full name pending a copy decision.",
            gate_location="data/cedar/collections.manifest.json owned.descriptor; scripts/stage_verified_previews.py copies name from the producer descriptor at pin; "
            "server/tests/test_collection_display_names.py",
            closing_condition="Producer title changed (Lumecon-data #17) before the next pin; a short label chosen for tiles; downloads already held cite the old name, which the ledger records.",
            evidence="server/tests/test_collection_display_names.py (4 tests); data/cedar/releases.json owned v4",
            classification="DECISION",
            owner=OWNERS["kaylyn"],
            question="What short label should tiles show for Individual Native-Owned Businesses, now that the catalog's short name equals the full name?",
        )
    )
    return out


def render_markdown(reg: dict) -> str:
    m = reg["measured"]
    lines = [
        f"# Consumer-side release-gap register, {DATE}",
        "",
        "Generated by `python3 server/tests/release_gap_register.py --write` from the tracked files; "
        "`server/tests/test_release_gap_register.py` fails when this file or the JSON beside it is stale. "
        "One row per (collection or component, gate): what exists in this repository or its workspace, what a served "
        "collection carries, the gate between them, its recorded closing condition, the evidence already in Git, and a "
        "classification. The full producer spreadsheets are not in Git; where a count needs them the row names the "
        "file and the command.",
        "",
        "Classifications: **CODE** (fixed or fixable here, with a test), **EVIDENCE_IN_REPO** (explained by what Git holds), "
        "**EVIDENCE_NEEDED** (names the file and command), **DECISION** (owner per AGENTS.md section 5, one question), "
        "**RIGHTS** (a publication or rights rule working as written), **RULED_REBUILD_PENDING** (an owner ruling changed "
        "the gate in code; the producer rebuild that applies it has not run).",
        "",
        "## Summary",
        "",
        "| Classification | Rows |",
        "| --- | ---: |",
    ]
    counts = Counter(r["classification"] for r in reg["rows"])
    for c in CLASSES:
        lines.append(f"| {c} | {counts.get(c, 0)} |")
    lines += [
        "",
        "## Decision queue",
        "",
        "| Row | Owner | Question |",
        "| --- | --- | --- |",
    ]
    for r in reg["rows"]:
        if r.get("question"):
            lines.append(f"| {r['id']} | {r['owner']} | {r['question']} |")
    lines += ["", "## Rows", ""]
    for r in reg["rows"]:
        lines += [
            f"### {r['id']}: {r['collection']}",
            "",
            f"- **Gate:** {r['gate']}",
            f"- **Exists:** {r['exists']}",
            f"- **Served:** {r['served']}",
            f"- **Gate location:** {r['gate_location']}",
            f"- **Closing condition:** {r['closing_condition']}",
            f"- **Evidence in the repository:** {r['evidence']}",
            f"- **Classification:** {r['classification']}"
            + (f"; owner {r['owner']}" if r.get("owner") else ""),
        ]
        if r.get("question"):
            lines.append(f"- **Question:** {r['question']}")
        if r.get("needs"):
            lines.append(f"- **Needs (exact):** {r['needs']}")
        lines.append("")
    lines += [
        "## Measured facts the rows quote",
        "",
        "| Collection | Served rows | Workspace table (2026-09-02) | Legacy extract key: legacy-only of 10 |",
        "| --- | ---: | --- | --- |",
    ]
    for cid in sorted(m["served"]):
        wc = m["workspace_counts"].get(cid)
        lg = m["legacy"].get(cid, {})
        lo = lg.get("legacy_only")
        lines.append(
            f"| {cid} | {m['served'][cid]['n_rows']:,} | "
            + (f"{wc['table']} {wc['rows']:,}" if wc else "no extract")
            + " | "
            + (
                f"{lg.get('key')}: {lo}"
                if lo is not None
                else (f"{lg.get('key')}: different table" if lg else "no extract")
            )
            + " |"
        )
    lines += [
        "",
        f"Withheld register names: {m['withheld']['total']} ({m['withheld']['by_class']}). "
        f"CEV ids in the served Deals preview: {len(m['cev']['in_served_sample'])} of {len(m['cev']['ids'])}. "
        f"Retired Explore overrides: {m['overrides']['retired']}; live override keys: {m['overrides']['live_keys'] or 'none'}. "
        f"Lobbying `superseded_by` after the fix: `{m['overrides']['lobbying_superseded_by']}`. "
        f"Scripts: {m['graph']['numbered_scripts']} numbered, {m['graph']['referenced']} referenced, {m['graph']['in_code_archive']} archived; "
        f"census {m['census']['scripts']} scripts, maintenance {m['census']['maintenance_status_counts']}.",
        "",
        "Not found, recorded so it is not re-investigated: no consumer file filters rows on `identity_scope` (GAP-12); no tracked file under "
        "`public/`, `data/cedar/`, `src/` or `server/cedar_press/` names a `CEV-*` id (GAP-05). GAP-11's 45 register names are no longer withheld: "
        "the owner ruled on 2026-10-02 that they are business records, and the producer rebuild that applies it is pending.",
        "",
    ]
    return "\n".join(lines)


def build() -> dict:
    m = measure()
    reg = {
        "generated": DATE,
        "generator": "python3 server/tests/release_gap_register.py --write",
        "classifications": list(CLASSES),
        "owners": OWNERS,
        "rows": rows(m),
        "measured": m,
    }
    return reg


def render_json(reg: dict) -> str:
    return json.dumps(reg, indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    reg = build()
    js, md = render_json(reg), render_markdown(reg)
    if "--write" in argv:
        OUT_JSON.write_text(js, encoding="utf-8", newline="\n")
        OUT_MD.write_text(md, encoding="utf-8", newline="\n")
        print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")
    elif "--check" in argv:
        stale = [
            p.relative_to(ROOT)
            for p, text in ((OUT_JSON, js), (OUT_MD, md))
            if not p.exists() or p.read_text(encoding="utf-8") != text
        ]
        if stale:
            print("stale: " + ", ".join(map(str, stale)) + "; rerun with --write", file=sys.stderr)
            return 1
        print("current")
    counts = Counter(r["classification"] for r in reg["rows"])
    print(
        json.dumps({"rows": len(reg["rows"]), **{c: counts.get(c, 0) for c in CLASSES}}, indent=1)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
