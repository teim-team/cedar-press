"""170_build_individual_native_candidates.py

Build the CANDIDATE SET for individual-Native ownership verification, and merge
in every ruling the project owner has already made by hand.

WHY THIS EXISTS
---------------
Elijah, 2026-08-26: "I still want to verify individual Native American ownership
though - like seeing if their website says it. You can't lie to federal
contractors, but anyway, the ones I have identified previously as individually
Native owned, I looked."

Two instructions in one sentence:

  1. A SAM socio-economic flag is a SELF-CERTIFICATION. It is legally weighted
     (a false certification to a contracting officer carries False Claims Act
     exposure) but it is still the firm asserting its own status. START_HERE
     records the counter-example: Goldbelt Raven, an ANC subsidiary, certifies
     `alaskanNativeCorporationOwnedFirm = NO`. So the flag is evidence, never
     proof, and it is recorded in its OWN column - never folded into a verdict.

  2. He has ALREADY done this by hand for some firms. Those rulings are
     irreplaceable manual work and are NEVER re-litigated here. This script
     finds them, carries them forward verbatim with their evidence, and marks
     them `prior_ruling_honored = YES`. A later web pass may ADD evidence to
     such a row; it may not change the ruling.

WHAT IT WRITES
--------------
  data/clean/individual_native_verification_candidates.csv   the work list
  data/clean/individual_native_prior_rulings.csv             what Elijah already ruled

The verification table itself is written by 171 after the web pass.

CANDIDATE DEFINITION - TWO STREAMS (measured 2026-08-26)
--------------------------------------------------------
**Stream 1, `TOP400_FLAGGED` (305).** `prime_contracts.csv` awardees with
`attributed_flag = 0` on every row, ranked by obligations. The top 400 such
awardees hold $46.49B and **305 of them carry at least one native
self-certification flag**. Across the whole file 2,550 unattributed awardees
carry a flag holding $19.52B, so the top-400 cut is a priority order, not a
claim about the universe.

**Stream 2, `PRIOR_OWNER_RULING` (29).** Every firm the owner has already ruled
individually Native-owned that stream 1 misses. Forty of his forty-five rulings
key to a UEI and **only eleven land in the top 400**; building the register from
stream 1 alone would drop twenty-nine hand rulings on the floor.

**Stream 2 is not a tidiness measure - it is where the interesting fact is.**
Measured on the 40 prior-ruled UEIs: **22 carry ZERO native self-certification
flags on every one of their contract rows.** The largest is Frontier Electronic
Systems Corp - 998 rows, $204.2M obligated, not one native flag, ruled
`INDIVIDUAL_NATIVE` by the owner from the company's own site. **No
candidate set defined by the federal flag can ever reach that firm.** The
do-file warned about this direction in general ("discovery of residual
candidates restricted to Buy Indian / 8(a) / Indian Business set-asides ->
tribally-owned firms with non-obvious names winning only full-and-open
contracts can be missed"); this is the same undercount measured on the
individual class, and it means `sam_self_certification` is a DISCOVERY channel
with a known blind spot, never a definition of the population.

TWO STRUCTURAL FACTS ABOUT THE CANDIDATE SET, BOTH MEASURED
------------------------------------------------------------
1. **Every candidate's contract activity ends FY2022 or earlier.** Not a
   coincidence: all 209,478 FY2023-2026 rows in `prime_contracts.csv` carry
   `attributed_flag = 1`, because the archive backfill was seeded from known
   Native identifiers (`uei_exact` 152,516 / `parent_uei` 39,673 / `cage_exact`
   17,306) rather than pulled full-universe. **`attributed_flag = 0` therefore
   selects the BGOV `master prime file.dta` era exclusively.** Anyone expecting
   to discover new individually-Native firms in FY2023+ will find none, and the
   absence is a property of the pull, not of Indian Country.
2. **So a 2026 web page is always testifying about a record at least four years
   older than itself.** `temporal_caveat` is populated on 100% of rows for this
   reason. Three gaming rulings were withdrawn 2026-08-06 for exactly this
   error.

WHAT THIS SCRIPT WILL NOT DO
----------------------------
* It never asserts ownership. A name is not evidence; a tribal-sounding token
  is not evidence. `NAME_TRAPS` (39 terms) and `PLACE_SUFFIXES` are applied ONLY
  to raise a `name_trap_warning` on the row so a human reading it knows the
  name is not doing any work.
* It never writes `NOT_NATIVE`. Absence of a claim is `NO_CLAIM_FOUND`.
* It assigns no tier. Tier is computed in 171 from the corroboration actually
  present, by a rule stated in the codebook.

SAFE TO RE-RUN. Reads only; writes two files via .part + rename.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from cedar_domain import NAME_TRAPS, PLACE_SUFFIXES  # noqa: E402

CLEAN = os.path.join(ROOT, "data", "clean")
SPINE = os.path.join(ROOT, "data", "spine")
REVIEW = os.path.join(ROOT, "review")

PRIME = os.path.join(CLEAN, "prime_contracts.csv")

OUT_CANDIDATES = os.path.join(CLEAN, "individual_native_verification_candidates.csv")
OUT_PRIOR = os.path.join(CLEAN, "individual_native_prior_rulings.csv")

TODAY = dt.date.today().isoformat()

# The four SAM socio-economic assertions carried on a prime row, plus setaside.
SAM_FLAG_COLS = (
    "reported_8a",
    "reported_buy_indian",
    "reported_indian_business",
    "reported_native_preference",
)

TOP_N = 400

# ---------------------------------------------------------------------------
# Prior rulings by the project owner. Sources swept 2026-08-26.
#
# Each source is listed with the shape its ruling takes, because they are not
# uniform - three different vocabularies were used across three weeks and a
# reader who assumes one shape silently drops the other two.
# ---------------------------------------------------------------------------

# Vocabulary that means "this firm is individually Native-owned".
POSITIVE_RULINGS = {
    "INDIVIDUAL_NATIVE",
}

# `OWNER_NAMED` means this class ONLY when the note begins/contains "individual
# native" - AGENTS.md, "Ruling vocabulary", 2026-08-07. A note naming a tribe or
# corporation is tribal/ANC ownership and is a DIFFERENT ruling.
OWNER_NAMED_INDIVIDUAL_RE = re.compile(r"individual\s+native", re.I)

# Vocabulary that means "individually Native-owned, therefore NOT a tribal /
# ANC / NHO attribution". Same class of firm, reached from the other direction:
# these were ruled while ruling OUT a tribal owner.
NEGATIVE_TRIBAL_RE = re.compile(
    r"individually\s+native[- ]owned|individual\s+(?:native\s+)?ownership\s+is\s+not",
    re.I,
)


def _f(path: str):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def collect_prior_rulings() -> list[dict]:
    """Sweep every place the owner's individual-Native rulings can live.

    Returns one row per (identifier_type, identifier|name) ruling, carrying the
    ruling text, the note, the evidence URL where one was given, and the file it
    came from. Nothing here is interpreted beyond classifying the vocabulary.
    """
    out: list[dict] = []

    # ---- 1. hci_analysis.do per-UEI drops, extracted to the spine ----------
    # 31 UEI-level rulings, ruled_by "Elijah Moreno", each with an evidence type
    # and (mostly) an evidence URL. These are the seed of the whole class:
    # AGENTS.md, "NEW ENTITY CLASS", 2026-08-07 - "the exclusions we already
    # hold are the seed of it - a hand-verified list built as a by-product of
    # ruling them out."
    for r in _f(os.path.join(SPINE, "cedar_exclusion_rulings.csv")):
        if r.get("exclusion_reason") != "individually_native_owned":
            continue
        out.append(
            dict(
                identifier_type=r.get("identifier_type", ""),
                identifier=r.get("identifier", ""),
                entity_name="",
                ruling_text="individually_native_owned",
                ruling_class="INDIVIDUAL_NATIVE",
                ruling_note=r.get("ruling_note", ""),
                evidence_type=r.get("evidence_type", ""),
                evidence_url=r.get("evidence_url", ""),
                ruled_by=r.get("ruled_by", ""),
                ruled_date=r.get("extracted_date", ""),
                source_file="data/spine/cedar_exclusion_rulings.csv <- "
                + r.get("source_file", ""),
                source_line=r.get("source_line", ""),
            )
        )

    # ---- 2. the dated ruling inboxes --------------------------------------
    inbox_specs = [
        # (path, id column, name column, ruling column, note column)
        ("review/rulings_inbox_2026-08-07_elijah.csv", "uei", "entity_name",
         "YOUR_RULING", "notes"),
        ("review/rulings_inbox_2026-08-08_elijah_batch2.csv", "identifier",
         "entity_name", "YOUR_RULING", "notes"),
    ]
    for rel, idcol, namecol, rulcol, notecol in inbox_specs:
        for r in _f(os.path.join(ROOT, rel)):
            ruling = (r.get(rulcol) or "").strip()
            note = (r.get(notecol) or "").strip()
            cls = None
            if ruling.upper() in POSITIVE_RULINGS:
                cls = "INDIVIDUAL_NATIVE"
            elif ruling.upper() == "OWNER_NAMED" and OWNER_NAMED_INDIVIDUAL_RE.search(note):
                cls = "INDIVIDUAL_NATIVE"
            if not cls:
                continue
            urls = re.findall(r"https?://\S+", note)
            out.append(
                dict(
                    identifier_type="UEI",
                    identifier=(r.get(idcol) or "").strip(),
                    entity_name=(r.get(namecol) or "").strip(),
                    ruling_text=ruling,
                    ruling_class=cls,
                    ruling_note=note,
                    evidence_type="Owner note with URL" if urls else "Owner note",
                    evidence_url=urls[0].rstrip(".,);") if urls else "",
                    ruled_by="Elijah Moreno",
                    ruled_date=re.search(r"\d{4}-\d{2}-\d{2}", rel).group(0),
                    source_file=rel,
                    source_line="",
                )
            )

    # ---- 3. the quarantine / deals-party inboxes --------------------------
    # These say "Not a Native entity - individually Native-owned firm". They are
    # rulings about the SAME class, reached while refusing a tribal attribution.
    # The refusal is of the TRIBAL link, not of Native ownership - reading them
    # as "not Native" would invert the owner's meaning.
    for rel in [
        "review/rulings_inbox_2026-08-05i.csv",
        "review/rulings_inbox_2026-08-05j.csv",
        "review/rulings_inbox_2026-08-05m.csv",
    ]:
        for r in _f(os.path.join(ROOT, rel)):
            ruling = (r.get("YOUR_RULING") or "").strip()
            note = (r.get("YOUR_NOTE") or "").strip()
            if not NEGATIVE_TRIBAL_RE.search(ruling + " " + note):
                continue
            ident = (r.get("cage_code") or r.get("uei") or "").strip()
            out.append(
                dict(
                    identifier_type="CAGE" if r.get("cage_code") else "NAME",
                    identifier=ident or (r.get("entity_or_firm") or "").strip(),
                    entity_name=(r.get("entity_or_firm") or "").strip(),
                    ruling_text=ruling,
                    ruling_class="INDIVIDUAL_NATIVE_NOT_TRIBAL",
                    ruling_note=note,
                    evidence_type="Owner note",
                    evidence_url="",
                    ruled_by="Elijah Moreno",
                    ruled_date=re.search(r"\d{4}-\d{2}-\d{2}", rel).group(0),
                    source_file=rel,
                    source_line="",
                )
            )

    # ---- 4. the applied cross-dataset ruling map ---------------------------
    # 166 rows / 31 distinct UEIs carrying `BLOCKED: individually_native_owned`.
    # These are the SAME 31 rulings as (1), propagated across three identifier
    # files. Recorded so the propagation is visible, deduped on identifier below.
    seen = {(o["identifier_type"], o["identifier"].upper()) for o in out}
    prop = collections.Counter()
    for r in _f(os.path.join(CLEAN, "cross_dataset_ruling_map.csv")):
        if r.get("ruling") != "BLOCKED: individually_native_owned":
            continue
        key = (r.get("identifier_type", ""), (r.get("identifier") or "").upper())
        prop[key] += 1
        if key in seen:
            continue
        seen.add(key)
        out.append(
            dict(
                identifier_type=r.get("identifier_type", ""),
                identifier=r.get("identifier", ""),
                entity_name="",
                ruling_text="BLOCKED: individually_native_owned",
                ruling_class="INDIVIDUAL_NATIVE",
                ruling_note="",
                evidence_type="Applied ruling map",
                evidence_url="",
                ruled_by="Elijah Moreno",
                ruled_date=r.get("applied_date", ""),
                source_file="data/clean/cross_dataset_ruling_map.csv",
                source_line="",
            )
        )
    for o in out:
        o["n_propagated_rows"] = prop.get(
            (o["identifier_type"], o["identifier"].upper()), 0
        )
    return out


def name_trap_warning(name: str) -> str:
    """Say WHY the name is not evidence, per row. Never used to classify."""
    toks = re.findall(r"[a-z']+", (name or "").lower())
    hits = [t for t in toks if t in NAME_TRAPS]
    warn = []
    if hits:
        warn.append("trap_token:" + "|".join(sorted(set(hits))))
    for i, t in enumerate(toks[:-1]):
        if t in NAME_TRAPS and toks[i + 1] in PLACE_SUFFIXES:
            warn.append(f"place_suffix:{t} {toks[i + 1]}")
    return ";".join(warn)


def main() -> int:
    prior = collect_prior_rulings()
    prior_by_uei = {
        p["identifier"].upper(): p for p in prior if p["identifier_type"] == "UEI"
    }
    prior_by_cage = {
        p["identifier"].upper(): p for p in prior if p["identifier_type"] == "CAGE"
    }
    prior_by_name = {
        re.sub(r"[^a-z0-9]", "", p["entity_name"].lower()): p
        for p in prior
        if p["entity_name"]
    }

    # ---- aggregate prime_contracts to the awardee ------------------------
    agg: dict[str, dict] = collections.defaultdict(
        lambda: dict(
            obl=0.0,
            rows=0,
            flag_rows=0,
            names=collections.Counter(),
            cages=collections.Counter(),
            states=collections.Counter(),
            fys=set(),
            flags=collections.Counter(),
            setasides=collections.Counter(),
            sources=collections.Counter(),
            any_attributed=False,
        )
    )
    with open(PRIME, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            key = (r["awardee_uei"] or "").strip().upper() or (
                "NAME:" + (r["awardee_name"] or "").strip().upper()
            )
            a = agg[key]
            if r.get("attributed_flag") not in ("0", "", None):
                a["any_attributed"] = True
            try:
                a["obl"] += float(r["total_obligations"] or 0)
            except ValueError:
                pass
            a["rows"] += 1
            if r["awardee_name"]:
                a["names"][r["awardee_name"]] += 1
            if r["cage_code"]:
                a["cages"][r["cage_code"]] += 1
            if r["recipient_state_code"]:
                a["states"][r["recipient_state_code"]] += 1
            if r["fiscal_year"]:
                a["fys"].add(r["fiscal_year"])
            a["sources"][r.get("source_file", "")] += 1
            hit = False
            for c in SAM_FLAG_COLS:
                if r.get(c) not in ("", "0", "0.0", None):
                    a["flags"][c] += 1
                    hit = True
            if hit:
                a["flag_rows"] += 1
                if r.get("setaside"):
                    a["setasides"][r["setaside"]] += 1

    unattributed = {k: v for k, v in agg.items() if not v["any_attributed"]}
    ranked = sorted(unattributed.items(), key=lambda kv: -kv[1]["obl"])
    top = ranked[:TOP_N]
    top_keys = [k for k, _ in top]
    candidates = [(k, v, "TOP400_FLAGGED") for k, v in top if v["flag_rows"] > 0]
    already = {k for k, _, _ in candidates}

    # ---- SECOND STREAM: every firm the owner has ALREADY ruled -------------
    # 40 of his 45 rulings key to a UEI, and ONLY 11 of those land in the top
    # 400. Building the register from the self-certification route alone would
    # therefore drop 29 of his hand rulings on the floor - the opposite of
    # honouring them.
    #
    # It also hides the most interesting fact in this build. Measured
    # 2026-08-26: **22 of the 40 prior-ruled firms carry ZERO native
    # self-certification flags across every one of their contract rows** -
    # Frontier Electronic Systems Corp, 998 rows and $204.2M, is the largest.
    # A candidate set defined by the federal flag can never reach them. That is
    # the undercount direction the do-file already warned about ("discovery of
    # residual candidates restricted to Buy Indian / 8(a) / Indian Business
    # set-asides"), now measured on the individual class specifically.
    ruled_ids = {p["identifier"].upper() for p in prior if p["identifier"]}
    for key, v in unattributed.items():
        if key in already:
            continue
        cages_u = {c.upper() for c in v["cages"]}
        if key.upper() in ruled_ids or (cages_u & ruled_ids):
            candidates.append((key, v, "PRIOR_OWNER_RULING"))

    cols = [
        "verification_id",
        "awardee_uei",
        "cage_code_modal",
        "awardee_name_modal",
        "awardee_name_variants",
        "recipient_state_modal",
        "candidate_basis",
        # scale
        "n_contract_rows",
        "total_obligations_usd",
        "fy_min",
        "fy_max",
        "obligations_rank_among_unattributed",
        # EVIDENCE FIELD 1 - the federal filing. Self-certification. Independent
        # of the other three and never merged with them.
        "sam_self_certification",
        "sam_flags_asserted",
        "sam_flag_contract_rows",
        "sam_flag_row_share",
        "sam_setaside_values",
        # EVIDENCE FIELD 2/3/4 - filled by the web pass, blank here.
        "self_description",
        "self_description_sentence",
        "self_description_url",
        "self_description_fetch_date",
        "self_description_http_status",
        "self_description_ownership_kind",
        "third_party",
        "third_party_source_type",
        "third_party_sentence",
        "third_party_url",
        "third_party_fetch_date",
        "tribal_affiliation_named",
        "tribal_affiliation_name",
        "tribal_affiliation_source",
        # prior work by the owner - carried, never overwritten
        "prior_owner_ruling",
        "prior_owner_ruling_note",
        "prior_owner_ruling_evidence_url",
        "prior_owner_ruling_source_file",
        "prior_owner_ruling_date",
        "prior_ruling_honored",
        # guardrails
        "name_trap_warning",
        "temporal_caveat",
        "prime_source_files",
        "built_date",
        "built_by",
    ]

    rows = []
    for rank, (key, v, basis) in enumerate(candidates, start=1):
        uei = "" if key.startswith("NAME:") else key
        name = v["names"].most_common(1)[0][0] if v["names"] else key[5:]
        cage = v["cages"].most_common(1)[0][0] if v["cages"] else ""
        pr = (
            prior_by_uei.get(uei.upper())
            or prior_by_cage.get(cage.upper())
            or prior_by_name.get(re.sub(r"[^a-z0-9]", "", name.lower()))
        )
        fys = sorted(v["fys"])
        # A CURRENT page cannot testify about a HISTORICAL record. Three gaming
        # rulings were withdrawn 2026-08-06 for exactly this error. Precompute
        # the caveat so the web pass cannot forget it.
        caveat = ""
        if fys:
            gap = int(TODAY[:4]) - int(fys[-1])
            if gap >= 3:
                caveat = (
                    f"contract rows end FY{fys[-1]}; a page fetched {TODAY} is "
                    f"{gap} years later and cannot testify about ownership then"
                )
        rows.append(
            {
                "verification_id": f"INV-{rank:04d}",
                "awardee_uei": uei,
                "cage_code_modal": cage,
                "awardee_name_modal": name,
                "awardee_name_variants": " | ".join(
                    n for n, _ in v["names"].most_common(4)
                ),
                "recipient_state_modal": (
                    v["states"].most_common(1)[0][0] if v["states"] else ""
                ),
                "n_contract_rows": v["rows"],
                "total_obligations_usd": round(v["obl"], 2),
                "fy_min": fys[0] if fys else "",
                "fy_max": fys[-1] if fys else "",
                "candidate_basis": basis,
                "obligations_rank_among_unattributed": (
                    top_keys.index(key) + 1 if key in top_keys else ""
                ),
                # NOT "YES" by construction any more. The prior-ruling stream
                # reaches firms that never certified anything.
                "sam_self_certification": "YES" if v["flag_rows"] else "NO",
                "sam_flags_asserted": "|".join(sorted(v["flags"])),
                "sam_flag_contract_rows": v["flag_rows"],
                "sam_flag_row_share": round(v["flag_rows"] / v["rows"], 4),
                "sam_setaside_values": " | ".join(
                    f"{s}({n})" for s, n in v["setasides"].most_common(4)
                ),
                "self_description": "NOT_CHECKED",
                "self_description_sentence": "",
                "self_description_url": "",
                "self_description_fetch_date": "",
                "self_description_http_status": "",
                "self_description_ownership_kind": "",
                "third_party": "NOT_CHECKED",
                "third_party_source_type": "",
                "third_party_sentence": "",
                "third_party_url": "",
                "third_party_fetch_date": "",
                "tribal_affiliation_named": "NOT_CHECKED",
                "tribal_affiliation_name": "",
                "tribal_affiliation_source": "",
                "prior_owner_ruling": pr["ruling_class"] if pr else "",
                "prior_owner_ruling_note": pr["ruling_note"] if pr else "",
                "prior_owner_ruling_evidence_url": pr["evidence_url"] if pr else "",
                "prior_owner_ruling_source_file": pr["source_file"] if pr else "",
                "prior_owner_ruling_date": pr["ruled_date"] if pr else "",
                "prior_ruling_honored": "YES" if pr else "",
                "name_trap_warning": name_trap_warning(name),
                "temporal_caveat": caveat,
                "prime_source_files": " | ".join(
                    f"{s}({n})" for s, n in v["sources"].most_common(3)
                ),
                "built_date": TODAY,
                "built_by": "code/170_build_individual_native_candidates.py",
            }
        )

    def write(path: str, fieldnames: list[str], data: list[dict]) -> None:
        part = path + ".part"
        with open(part, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for d in data:
                w.writerow({k: d.get(k, "") for k in fieldnames})
        os.replace(part, path)

    write(OUT_CANDIDATES, cols, rows)

    prior_cols = [
        "identifier_type",
        "identifier",
        "entity_name",
        "ruling_text",
        "ruling_class",
        "ruling_note",
        "evidence_type",
        "evidence_url",
        "ruled_by",
        "ruled_date",
        "source_file",
        "source_line",
        "n_propagated_rows",
    ]
    write(OUT_PRIOR, prior_cols, prior)

    matched = sum(1 for r in rows if r["prior_ruling_honored"] == "YES")
    print(f"unattributed awardees            {len(unattributed):>8,}")
    print(f"top {TOP_N} by obligations          "
          f"${sum(v['obl'] for _, v in top) / 1e9:>7.2f}B")
    n_flag = sum(1 for _, _, b in candidates if b == "TOP400_FLAGGED")
    n_ruled = sum(1 for _, _, b in candidates if b == "PRIOR_OWNER_RULING")
    no_cert = sum(1 for _, v, _ in candidates if not v["flag_rows"])
    print(f"of those, carry a native flag    {n_flag:>8,}")
    print(f"prior-ruled firms outside top400 {n_ruled:>8,}")
    print(f"CANDIDATE SET                    {len(candidates):>8,}")
    print(f"  with NO native self-cert flag  {no_cert:>8,}"
          "  <- unreachable from the federal flag")
    print(f"candidate obligations            "
          f"${sum(v['obl'] for _, v, _ in candidates) / 1e9:>7.2f}B")
    print(f"prior owner rulings found        {len(prior):>8,}")
    print(f"  distinct identifiers           "
          f"{len({(p['identifier_type'], p['identifier'].upper()) for p in prior}):>8,}")
    print(f"  landing on a candidate row     {matched:>8,}")
    print(f"rows with a name-trap warning    "
          f"{sum(1 for r in rows if r['name_trap_warning']):>8,}")
    print(f"rows with a temporal caveat      "
          f"{sum(1 for r in rows if r['temporal_caveat']):>8,}")
    print()
    print("wrote", os.path.relpath(OUT_CANDIDATES, ROOT))
    print("wrote", os.path.relpath(OUT_PRIOR, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
