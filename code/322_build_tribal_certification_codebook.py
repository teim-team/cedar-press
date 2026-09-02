"""322 - codebook fragment for the tribal certification layer.

A FRAGMENT, not a registration. It writes
`docs/codebooks/02m_tribal_certification_layer.md` and does NOT touch the
codebook master: `41_build_codebooks.py` writes that master in "w" mode and
would delete 21 of 43 blocks, so nothing here goes near it (defect class 6).
Registration happens when the layer leaves staging, which it cannot do until
the consent question is answered.

Fill rates and value vocabularies are COMPUTED FROM THE STAGED FILES at build
time, never hand-typed - the same rule the product descriptor carries, for the
same reason: a hand-typed count is a count that drifts.

NO NETWORK CALLS.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "data" / "staging" / "tribal_vendor_lists"
OUT = ROOT / "docs" / "codebooks" / "02m_tribal_certification_layer.md"

SCRIPT = "322_build_tribal_certification_codebook.py"
CAPTURE_DATE = "2026-08-26"

FILES = [
    (STAGE / f"tribal_certification_sources_{CAPTURE_DATE}.csv",
     "tribal_certification_sources",
     "One row per CERTIFYING AUTHORITY. Who asserts, about what class of "
     "thing, where, under what stated terms, and whether that source may be "
     "published."),
    (STAGE / f"tribal_certification_rules_{CAPTURE_DATE}.csv",
     "tribal_certification_rules",
     "One row per (authority, programme): the ELIGIBILITY RULE behind the "
     "certification, quoted verbatim with a source URL and capture date. This "
     "is what lets a subscriber filter for themselves instead of trusting a "
     "threshold Cedar Press picked."),
    (STAGE / f"tribal_certification_facts_sample_{CAPTURE_DATE}.csv",
     "tribal_certification_facts_sample",
     "Firm-level certification FACTS - firm X is asserted by authority Y as "
     "of date Z, per this URL. A SAMPLE: only rows whose identifier was read "
     "from the source and then tested against prime_contracts.csv."),
]

DESCRIPTIONS = {
    'searched':
        'What was looked for, required whenever the verdict is RULE_NOT_PUBLISHED, so the next pass extends the search instead of inheriting the conclusion.',
    'whose_ownership':
        'WHOSE ownership qualifies, and these are DIFFERENT POPULATIONS that do not nest: THIS_TRIBE_MEMBER / ANY_FEDERALLY_RECOGNIZED_TRIBE_MEMBER / ANY_NATIVE_PERSON / TRIBAL_GOVERNMENT_ENTITY / SHAREHOLDER_OR_DESCENDANT_OR_SPOUSE / PARENT_CORPORATION / MIXED_SEE_TIERS. A study of individual Native business ownership wants the first three and specifically NOT the sixth.',
    "certification_rule_id":
        "Identifier for one (authority, programme) rule. Keyed on the "
        "authority's spine id plus a programme slug, never on row position.",
    'programme_name_as_they_call_it':
        "The programme's name in the authority's own words. Load-bearing: searching 'TERO' alone finds a minority of these - CSKT says Indian Preference Office, Muscogee says Contracting and Employment Support Office, Laguna files it under Tax Administration.",
    'rule_list_mismatch':
        "WHERE THE PUBLISHED LIST AND THE GOVERNING RULE DISAGREE, stated plainly. Colville's list flags firms certified at 0% ownership against a code floor of 60%; EBCI's list says 'TRIBAL MEMBER owned' when its own rule admits any federally recognised tribe at 51%. Cedar Press does not adjudicate these - it publishes both and names the conflict.",
    'quote_source_url':
        'Where the quote was read. Required whenever a quote is present.',
    'verbatim_quote_2':
        'A second quote where the tiers need it.',
    'verbatim_quote':
        'The single most load-bearing sentence, exactly as written. A paraphrase is our claim; a quotation is theirs.',
    'expiry_terms':
        'Lapse, decertification and re-application bars.',
    'renewal_cadence':
        'How often certification must be renewed. Ranges from weekly republication to biennial recertification to none stated.',
    'verification_method':
        'What the authority demands and does: documents, site visits, interviews, or nothing at all.',
    'residency_or_onreservation_requirement':
        'Residency or on-reservation criteria, or NOT_STATED. Often the geography bounds where the ordinance BITES rather than who qualifies - the codebook says which.',
    'enrollment_requirement':
        'Whose enrolment counts. CRITICAL: most programmes admit members of ANY federally recognised tribe, so a certification is NOT evidence of citizenship in the certifying nation.',
    'control_requirement':
        'What the programme demands beyond ownership - management, voting control, anti-front tests.',
    'tiers':
        "Each tier and its definition, in the source's words.",
    'is_graded':
        'Y where the programme ranks firms by ownership level rather than issuing a single binary certification.',
    'ownership_pct_threshold':
        "The threshold in the source's own terms, including grading. Prose; use the numeric column to filter.",
    'ownership_pct_floor_numeric':
        'THE MOST USEFUL FILTER COLUMN IN THE TABLE. The lowest certifiable ownership floor as a number. Measured floors range 51 / 60 / 100 - **a blanket 51% filter silently mis-states Colville and CTUIR (both 60) and MHA (100)**.',
    'ownership_pct_required':
        'YES / NO / NOT_STATED / NOT_CHECKED. Whether the programme requires an ownership percentage AT ALL. Measured 2026-08-26: 10 of 14 programmes YES, 1 NO, 3 NOT_STATED.',
    'authority_url':
        'Where the rule text was read.',
    'authority_citation':
        'The ordinance, code title or corporate statement the rule comes from, named precisely enough to re-find.',
    'rule_verdict':
        "RULE_FOUND / RULE_PARTIAL / RULE_NOT_PUBLISHED / BEHIND_LOGIN / NOT_CHECKED / SITE_REFUSED. FOUND and PARTIAL both REQUIRE a verbatim quote and a source URL - the build refuses to write them otherwise. A rule is QUOTED, never inferred from the list's contents.",
    'programme_slug':
        'Short stable token for the programme, used in the key. A (tribe, programme) pair must be unique.',
    "certification_source_id":
        "Identifier for the certifying source. Keyed on the AUTHORITY's spine "
        "id, never on row position, so it survives an insertion.",
    "certifying_authority_entity_id":
        "`tribe_id` in `data/spine/cedar_entity_spine.csv` of the entity "
        "MAKING the assertion - the tribe or ANCSA corporation, not the firm.",
    "certifying_authority_name": "Canonical name of the certifying authority.",
    "authority_class":
        "Whether the authority is a tribal government or an ANCSA "
        "corporation. They certify different things under different powers.",
    "programme_name": "What the authority itself calls the programme.",
    "assertion_class":
        "WHAT THE LIST ASSERTS, and the most load-bearing column in the "
        "layer. `OWNERSHIP` (TERO / Indian-preference certification, a parent "
        "naming its subsidiary, a shareholder-owned directory) is evidence "
        "about who owns a firm. `RELATIONSHIP` (a general vendor or supplier "
        "list) says only that a firm does business with the tribe. "
        "`OPERATING_ON_LAND` (a business licence registry) says only where a "
        "firm operates. Reading a RELATIONSHIP row as OWNERSHIP is the single "
        "failure mode that would discredit this layer.",
    "list_type":
        "The source's own form. TERO / SUBSIDIARY_DIRECTORY / "
        "SHAREHOLDER_VENDOR map to OWNERSHIP; VENDOR and TERO_EMPLOYER map to "
        "RELATIONSHIP; LICENSE maps to OPERATING_ON_LAND.",
    "list_url": "Landing page for the list as published by the authority.",
    "list_format":
        "MACHINE_READABLE (CSV/XLSX/DOCX/XML), PDF, HTML, PORTAL_SEARCH_ONLY "
        "or NONE. PORTAL_SEARCH_ONLY means the rows exist but are not "
        "retrievable as a set.",
    "entry_count_approx":
        "Approximate entries. READ `entry_count_is_verified` BEFORE USING "
        "THIS - several counts are the authority's own claim.",
    "entry_count_is_verified":
        "`Y` only where the count was obtained by enumerating the source. A "
        "claimed count is not a counted one.",
    "identifiers_present":
        "Fields each entry carries. Note whether a JOINABLE identifier "
        "(UEI/CAGE/EIN) is among them - most lists carry none.",
    "carries_joinable_identifier":
        "`Y` when the list publishes UEI, CAGE or EIN. When `N`, the list can "
        "produce CANDIDATES only and never a link: a name is not a key.",
    "update_frequency": "Cadence as STATED by the source, or NOT_STATED.",
    "verdict":
        "Typed discovery outcome for the CERTIFICATION product. "
        "LIST_FOUND_MACHINE_READABLE / LIST_FOUND_PDF / LIST_FOUND_HTML / "
        "LIST_BEHIND_LOGIN / LIST_REFERENCED_NOT_PUBLISHED / NO_LIST_FOUND / "
        "NOT_CHECKED / SITE_UNREACHABLE. `NO_LIST_FOUND` means not published "
        "on the authority's own site as at the capture date - a weaker claim "
        "than 'does not exist'.",
    "capture_date":
        "Date the source was read. EVERY ROW HAS ONE. A snapshot testifies "
        "only about its own date: never present a historical capture as "
        "current, and never rule a current page against a historical record.",
    "source_terms_status":
        "SILENT / TERMS_STATED_PERMISSIVE / TERMS_STATED_RESTRICTIVE / "
        "ROBOTS_DISALLOW / NOT_CHECKED. SILENT means the source states "
        "nothing about reuse. NOT_CHECKED means the terms could not be read, "
        "which is not the same as absent.",
    "source_terms_quote": "The stated term, verbatim, where one exists.",
    "consent_status":
        "UNRESOLVED / OPT_IN / OPT_OUT. **SILENCE IS UNRESOLVED, NEVER "
        "PERMISSION.** A federal record is public by statute; a sovereign "
        "government's own publication is not, and publicly reachable is not "
        "licensed for redistribution.",
    "suppression_key":
        "Flip this row's `consent_status` to remove an authority's rows - or "
        "to admit them if a TERO office opts in. Removal must be one field, "
        "not a search.",
    "publishable":
        "`Y` only when `consent_status = OPT_IN`. Enforced by "
        "`code/321_gate_tribal_source_restriction.py`, which fails the build "
        "rather than leaving the rule as prose.",
    "robots_note":
        "robots.txt behaviour: crawl-delay, named user-agents, or a WAF. A "
        "403 on every path including robots.txt is a filter, not a refusal we "
        "can read, and not evidence of absence.",
    "notes": "Analyst notes, including every caveat that bounds the row.",
    "staged_by": "Script that produced the row.",

    "certification_fact_id":
        "Identifier for one certification fact. Keyed on "
        "(authority, identifier type, identifier) so it is stable across "
        "rebuilds.",
    "asserted_firm_name": "Firm name as the certifying authority prints it.",
    "identifier_type": "UEI, CAGE or NONE.",
    "identifier":
        "The identifier AS PUBLISHED BY THE AUTHORITY. Not looked up, not "
        "inferred, not name-matched.",
    "secondary_identifier_type": "Second identifier type where published.",
    "secondary_identifier": "Second identifier where published.",
    "assertion_verbatim":
        "The authority's OWN WORDS. A paraphrase is our claim; a quotation is "
        "theirs.",
    "assertion_source_url": "Where the assertion was read.",
    "first_seen":
        "Earliest capture in which this firm-authority pair was observed. "
        "Equals `capture_date` until a Wayback pass extends the series.",
    "last_seen": "Most recent capture in which the pair was observed.",
    "certification_status":
        "ASSERTED_AS_OF_CAPTURE / LAPSED_BY_CAPTURE / UNKNOWN. A single "
        "capture can only support ASSERTED_AS_OF_CAPTURE; LAPSED_BY_CAPTURE "
        "requires two captures and says the pair was present in the earlier "
        "and absent in the later.",
    "evidence_leg":
        "THIRD_PARTY_PARENT (a corporation naming its own subsidiary), "
        "THIRD_PARTY_TRIBAL_GOVT (a tribe certifying a firm) or SELF. Tier A "
        "requires a leg that is NOT the firm, which is the whole point of "
        "this layer - a SAM socio-economic flag is self-certification.",
    "join_outcome":
        "MEASURED against `prime_contracts.csv` at build time, never typed. "
        "RESOLVES_UNATTRIBUTED (the identifier is in the unattributed "
        "universe), RESOLVES_EXISTING (already attributed - the assertion "
        "corroborates rather than discovers), NO_MATCH_IN_PRIME, or "
        "CANDIDATE_ONLY_NO_IDENTIFIER.",
    "prime_rows_matched": "Prime contract rows carrying the identifier.",
    "prime_obligations_usd_matched":
        "Obligations on those rows, USD nominal. This is the dollar value the "
        "assertion SPEAKS TO, not dollars newly discovered - read "
        "`value_added` for that.",
    "prime_current_tier": "Modal confidence tier on the matched rows today.",
    "prime_current_attributed_entity":
        "Entity the matched rows are attributed to today, if any.",
    "value_added":
        "NEW_ATTRIBUTION (resolves something unresolved), "
        "NEW_ATTRIBUTION_PARTIAL, INDEPENDENT_CORROBORATION (confirms an "
        "existing link with a leg that is not the firm) or NONE. "
        "Corroboration is not nothing: tier A requires a non-firm leg and the "
        "reconciliation queue has almost none.",
}


def profile(rows, col):
    vals = [(r.get(col) or "").strip() for r in rows]
    filled = sum(1 for v in vals if v)
    pct = round(100 * filled / len(rows)) if rows else 0
    uniq = Counter(v for v in vals if v)
    kind = "text"
    if col.endswith("_usd_matched") or col.endswith("_matched"):
        kind = "number"
    # A short closed vocabulary is worth printing; a free-text column is not.
    vocab = ""
    if 0 < len(uniq) <= 6 and all(len(v) <= 34 for v in uniq):
        vocab = ", ".join(f"`{v}`" for v, _ in uniq.most_common())
    return kind, pct, vocab


def main():
    missing = [p for p, _, _ in FILES if not p.exists()]
    if missing:
        # Defect class 2c: NAME what is missing; a count is not a task.
        raise SystemExit("staged file(s) absent - run 320 first:\n  "
                         + "\n  ".join(str(p) for p in missing))

    lines = [
        "# Codebook fragment - Tribal certification layer",
        "",
        f"*Generated {CAPTURE_DATE} by `code/{SCRIPT}`. Fill rates and value "
        f"vocabularies are computed from the staged files, not typed.*",
        "",
        "**STATUS: STAGED, NOT REGISTERED.** These tables live in "
        "`data/staging/tribal_vendor_lists/` and are deliberately absent from "
        "the codebook master, `25_TABLES` and `27_SPEC`. They do not ship, "
        "and `code/321_gate_tribal_source_restriction.py` fails any build "
        "that tries - a tribal or ANCSA source publishes only on "
        "`consent_status = OPT_IN`, and **silence is UNRESOLVED, never "
        "permission.**",
        "",
        "**THE ONE DISTINCTION TO CARRY OUT OF THIS FRAGMENT.** "
        "`assertion_class` separates three different facts that look alike: "
        "who OWNS a firm, who DOES BUSINESS WITH a tribe, and where a firm "
        "OPERATES. Only `OWNERSHIP` is evidence for attribution. A general "
        "vendor list is a good relationship dataset and a bad ownership "
        "claim, and many of its entries will be Home Depot.",
        "",
    ]

    for path, name, purpose in FILES:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rdr = csv.DictReader(fh)
            cols = list(rdr.fieldnames or [])
            rows = list(rdr)
        lines += [
            f"## `{name}`",
            "",
            f"*{len(rows)} rows, {len(cols)} columns. "
            f"Source: `{path.relative_to(ROOT)}`.*",
            "",
            purpose,
            "",
            "| Variable | Type | Filled | Values / description |",
            "|---|---|---:|---|",
        ]
        for c in cols:
            kind, pct, vocab = profile(rows, c)
            desc = DESCRIPTIONS.get(c, "")
            if not desc:
                raise SystemExit(
                    f"column {c!r} in {name} has no codebook description. "
                    f"An undocumented column is how a table ships meaning "
                    f"nobody can read - add it to DESCRIPTIONS.")
            cell = f"{vocab}<br>{desc}" if vocab else desc
            lines.append(f"| `{c}` | {kind} | {pct}% | {cell} |")
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    part = OUT.with_suffix(".md.part")
    part.write_text("\n".join(lines) + "\n", encoding="utf-8")
    part.replace(OUT)
    back = OUT.read_text(encoding="utf-8")
    if "| Variable |" not in back:
        raise SystemExit("re-read of the codebook fragment looks wrong")
    print(f"{OUT.relative_to(ROOT)}  ({len(back.splitlines())} lines, "
          f"re-read OK)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
