#!/usr/bin/env python3
"""
Cedar Press - 153: merge the overnight ordinance OCR and integrate it into the
gaming ordinance layer.

WHAT WAS SITTING UNCONSUMED
---------------------------
The 2026-08-13 overnight run (`150_run_ocr_overnight.py` -> eight shards of
`122_ocr_ordinance_scans.py`) finished all 263 OCR-able image-only scans. It
left:

    data/raw/external/nigc_ordinances/ocr/*.txt        263 verbatim OCR files
    data/interim/ocr_shards/ocr_shard_0..7.csv         233 metadata rows

and nothing read either one. `gaming_ordinances.csv` still carried
`text_layer_status = IMAGE_ONLY_SCAN_NO_TEXT_LAYER` and blank provisions on all
264 of those rows - a quarter of the archive, recorded in
`docs/GAMING_ORDINANCE_BUILD_LOG.md` Sec.8 as the largest known ceiling on the
dataset.

263 .txt AGAINST 233 SHARD ROWS IS NOT A LOSS - IT IS THE INTERRUPTION SHAPE
---------------------------------------------------------------------------
122 writes each `.txt` as soon as a document finishes, but writes its shard CSV
only at the END of the shard. An earlier run of the same shards was killed
mid-flight (START_HERE records "27 of 263" before the overnight attempt), so 28
documents have text on disk and no metadata row, and 2 more sit in the 300-dpi
smoke-test output `data/clean/gaming_ordinance_ocr.csv`.

AGENTS.md: "An interruption must not look like a completion." The mirror of that
rule applies here - an interruption must not look like a DELETION either. Those
28 documents are recovered from their `.txt` files, and every reconstructed row
is stamped `ocr_metadata_basis = reconstructed_from_txt_no_shard_row` so a
recovered figure is never mistaken for a measured one. Their
`ocr_mean_confidence` is left BLANK, never 0.0 - a per-line confidence that was
never recorded is not a document that OCR'd badly.

EVIDENCE GRADE IS PRESERVED, NOT LAUNDERED
------------------------------------------
- `text_layer_status` becomes `OCR_RECOVERED`, never `TEXT_LAYER_PRESENT`. The
  prior value is kept in `text_layer_status_prior`.
- `confidence` becomes `document_ocr_recovered`, a fourth basis alongside
  `document_parsed` / `document_no_text_layer` / `index_only`.
- `provisions_basis` names the text every provision on the row was read from.
- `pdf_chars` is NOT overwritten. It stays at the near-zero PDF text layer that
  made the row a scan in the first place; the OCR length is `ocr_chars`.

TWO REFUSALS CARRIED FORWARD FROM THE BUILD
-------------------------------------------
- The Kialegee row whose linked PDF is byte-identical to Kalispel's was never
  OCR'd and is never touched here. It is the 264th image-only row and it stays
  refused. The script asserts that no row carrying `md5_duplicate_of` or
  `confidence = document_served_belongs_to_another_tribe` gains content.
- A DATE READ OFF AN OCR'd LETTERHEAD NEVER ACCUSES THE INDEX. The build log
  Sec.4 records 117 false date disagreements caused by exactly this - NIGC's
  letterhead date is a scanned stamp. Where an OCR date disagrees with NIGC's
  index this writes `DISAGREE_UNVERIFIED_OCR_DATE`, never the born-digital
  `DISAGREE_DOCUMENT_IS_ANOTHER_INSTRUMENT`. The weaker text gets the weaker
  claim.

The one resolver is not re-run: entity keying is a property of the NIGC index
tribe NAME, which OCR does not change. Extractors are IMPORTED from
`118_build_gaming_ordinances.py`, never re-implemented (standing rule 8).

    py -3 code/153_merge_ordinance_ocr.py merge       # shards -> one table
    py -3 code/153_merge_ordinance_ocr.py integrate   # -> gaming_ordinances.csv
    py -3 code/153_merge_ordinance_ocr.py codebook
    py -3 code/153_merge_ordinance_ocr.py             # all three
"""

import csv
import importlib.util
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
INTERIM = CEDAR / "data" / "interim"
SHARDS = INTERIM / "ocr_shards"
OCRDIR = CEDAR / "data" / "raw" / "external" / "nigc_ordinances" / "ocr"
ORD = CLEAN / "gaming_ordinances.csv"
OCRCSV = CLEAN / "gaming_ordinance_ocr.csv"
SUMMARY = INTERIM / "153_run_summary.txt"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

_spec = importlib.util.spec_from_file_location(
    "ord118", CODE / "118_build_gaming_ordinances.py")
O = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(O)

sys.path.insert(0, str(CODE))
import cedar_codebook as CB                       # noqa: E402

OCR_FIELDS = [
    "ordinance_id", "tribe_id", "tribe_name", "ocr_txt_path", "ocr_chars",
    "ocr_pages", "ocr_pages_blank", "ocr_mean_confidence", "ocr_engine",
    "ocr_dpi", "text_layer_status_after", "source_url", "pdf_md5", "ocr_date",
    "ocr_metadata_basis", "ocr_shard", "ocr_chars_on_disk",
    "ocr_chars_agreement",
]

# Columns 153 adds to gaming_ordinances.csv.
NEW_ORD_FIELDS = [
    "text_layer_status_prior", "provisions_basis", "document_names_tribe_basis",
    "ocr_txt_path", "ocr_chars",
    "ocr_pages", "ocr_pages_blank", "ocr_mean_confidence", "ocr_engine",
    "ocr_dpi", "ocr_date", "ocr_metadata_basis",
]

LOG = []


def say(s=""):
    print(s, flush=True)
    LOG.append(s)


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    """`.part` then rename - an interruption must not look like a completion."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    part = Path(str(p) + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(p)
    say(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def backup(p, reason):
    p = Path(p)
    if not p.exists():
        return None
    dest = Path(str(p) + f".bak_{TODAY}_{reason}")
    n = 1
    while dest.exists():
        n += 1
        dest = Path(str(p) + f".bak_{TODAY}_{reason}{n}")
    dest.write_bytes(p.read_bytes())
    say(f"  backed up {p.name} -> {dest.name}")
    return dest


def clean_agency(name, tribe):
    """Post-filter the agency extractor's output on OCR text.

    NOT a new matcher (standing rule 8) - a string cleanup of one extractor's
    output on a lower-quality text, and every rule below is a MEASURED leak
    from the 263 recovered documents.

    Returns (name, refusal_reason).

    1. OCR loses sentence structure, so the capitalised run swallows the
       sentence in front of the body: `Applicable Standards. The Paskenta Band
       of Nomlaki Indians Gaming Commission`, `Audit of Gaming Operations. The
       Yankton Sioux Tribe Gaming Commission`. Everything up to the last
       sentence break inside the captured string belongs to the sentence, not
       to the name.
    2. OCR glues the date stamp and headings to the following word:
       `FEB82012 Chairwoman ... Gaming Commission`,
       `ESTABLISHMENTOFGAMINGCOMMISSION The Citizen Potawatomi Nation Gaming
       Commission`. A leading token carrying a digit, or an unbroken all-caps
       run, is page furniture.
    3. A STATE-LED BODY IS A STATE AGENCY. `Arizona Gaming Commission` and
       `Arizona Department of Gaming and the Tribal Gaming Office` were written
       into `tribal_gaming_agency_named`, which inverts the exact fact the
       column exists to record - the same failure as the NIGC lookalike, in a
       new form. AGENCY_REJECT catches `state gaming` and `state of` but not a
       state's NAME. Refused unless the tribe's own name STARTS with that state
       token, because a leading state token is usually the tribe's own name
       (`Delaware Nation`, `Iowa Tribe of Kansas and Nebraska`) - the trap
       `states_from_name` already records. This also refuses the truncation
       `Texas Gaming Regulatory Authority` that the build log names.
    """
    if not name:
        return "", ""
    if ". " in name:
        name = name.rsplit(". ", 1)[1]
    toks = name.split()
    while toks and (any(ch.isdigit() for ch in toks[0])
                    or (len(toks[0]) > 12 and toks[0].isupper())):
        toks.pop(0)
    while toks and toks[0].strip(".,").lower() in O.AGENCY_LEAD_DROP:
        toks.pop(0)
    name = " ".join(toks).strip(" .,;:")
    if len(name) < 12:
        return "", "refused_too_short_after_ocr_cleanup"
    first = re.sub(r"[^a-z]", "", toks[0].lower()) if toks else ""
    if first in O.STATES:
        tfirst = re.sub(r"[^a-z]", "", O.norm(tribe).split()[0]) if tribe else ""
        if tfirst != first:
            return "", f"refused_state_named_body:{name}"
    return name, ""


def txt_stats(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    pages = text.split("\n\f\n")
    return text, len(text), len(pages), sum(1 for x in pages if not x.strip())


# ---------------------------------------------------------------------------
# 1. MERGE
# ---------------------------------------------------------------------------
def cmd_merge(argv=()):
    say("=== 153 merge: eight OCR shards -> one table ===")

    seen, dupes, sources = {}, [], Counter()

    def take(row, basis, shard=""):
        oid = (row.get("ordinance_id") or "").strip()
        if not oid:
            return
        row = dict(row)
        row["ocr_metadata_basis"] = basis
        row["ocr_shard"] = shard
        sources[basis] += 1
        if oid in seen:
            # Sharding is i % n over one ordered list, so it CANNOT overlap.
            # Keep the check anyway and prefer the richer/later record rather
            # than silently taking whichever file was globbed last.
            dupes.append((oid, seen[oid]["ocr_metadata_basis"], basis))
            old = seen[oid]
            keep_new = ((row.get("ocr_date") or "") > (old.get("ocr_date") or "")
                        or int(row.get("ocr_dpi") or 0) > int(old.get("ocr_dpi") or 0))
            if not keep_new:
                return
        seen[oid] = row

    for f in sorted(SHARDS.glob("ocr_shard_*.csv")):
        rows = read_csv(f)
        say(f"  {f.name:24s} {len(rows):3d} rows")
        for r in rows:
            take(r, "shard_csv", f.stem.replace("ocr_shard_", ""))
    n_shard = len(seen)

    for r in read_csv(OCRCSV):
        take(r, "prior_clean_csv")
    say(f"\n  shard rows                        : {n_shard}")
    say(f"  + prior data/clean rows (300 dpi) : {len(seen) - n_shard}")
    say(f"  duplicate ordinance_ids across sources : {len(dupes)}")
    for d in dupes[:10]:
        say(f"      {d[0]}  {d[1]} vs {d[2]}")

    # --- the directory is the ground truth for WHAT WAS OCR'd -------------
    on_disk = {p.stem: p for p in OCRDIR.glob("*.txt")}
    missing_meta = sorted(set(on_disk) - set(seen))
    say(f"\n  .txt files on disk                : {len(on_disk)}")
    say(f"  .txt with NO metadata row         : {len(missing_meta)}"
        f"   <- interrupted shard, recovered below")

    ordrows = {r["ordinance_id"]: r for r in read_csv(ORD)}
    for oid in missing_meta:
        text, nch, npg, nblank = txt_stats(on_disk[oid])
        src = ordrows.get(oid, {})
        seen[oid] = {
            "ordinance_id": oid,
            "tribe_id": src.get("tribe_id", ""),
            "tribe_name": src.get("tribe_name", ""),
            "ocr_txt_path": str(on_disk[oid].relative_to(CEDAR)).replace("\\", "/"),
            "ocr_chars": nch, "ocr_pages": npg, "ocr_pages_blank": nblank,
            # NEVER 0.0. A confidence that was never recorded is not a bad OCR.
            "ocr_mean_confidence": "",
            "ocr_engine": "rapidocr-onnxruntime",
            "ocr_dpi": "",          # 220 or 300 - the killed run did not say
            "text_layer_status_after": "OCR_RECOVERED",
            "source_url": src.get("source_url", ""),
            "pdf_md5": src.get("pdf_md5", ""),
            "ocr_date": "",
            "ocr_metadata_basis": "reconstructed_from_txt_no_shard_row",
            "ocr_shard": "",
        }
        sources["reconstructed_from_txt_no_shard_row"] += 1

    # --- every metadata row must have the file it claims ------------------
    orphan_meta, char_disagree = [], []
    for oid, r in seen.items():
        p = OCRDIR / f"{oid}.txt"
        if not p.exists():
            orphan_meta.append(oid)
            r["ocr_chars_on_disk"] = ""
            r["ocr_chars_agreement"] = "TXT_FILE_MISSING"
            continue
        _, nch, _, _ = txt_stats(p)
        r["ocr_chars_on_disk"] = nch
        same = str(nch) == str(r.get("ocr_chars") or "")
        r["ocr_chars_agreement"] = "AGREE" if same else "DISAGREE"
        if not same:
            char_disagree.append((oid, r.get("ocr_chars"), nch))

    say(f"  metadata rows with no .txt        : {len(orphan_meta)}")
    say(f"  ocr_chars disagreeing with disk   : {len(char_disagree)}")
    for d in char_disagree[:10]:
        say(f"      {d[0]}  csv {d[1]} vs disk {d[2]}")

    rows = sorted(seen.values(), key=lambda r: r["ordinance_id"])
    say(f"\n  MERGED                            : {len(rows)}")
    for k, v in sorted(sources.items()):
        say(f"      {k:38s} {v}")

    conf = [float(r["ocr_mean_confidence"]) for r in rows
            if str(r.get("ocr_mean_confidence") or "").strip()]
    blankdoc = [r for r in rows
                if str(r.get("ocr_pages_blank")) == str(r.get("ocr_pages"))]
    say(f"  mean confidence recorded on       : {len(conf)} of {len(rows)}")
    if conf:
        say(f"      mean {sum(conf)/len(conf):.4f}   min {min(conf):.4f}")
        say(f"      below 0.70                     : "
            f"{sum(1 for c in conf if c < 0.70)}")
    say(f"  ALL pages blank (true OCR failure): {len(blankdoc)}")
    say(f"  zero-length .txt                  : "
        f"{sum(1 for r in rows if str(r.get('ocr_chars_on_disk')) == '0')}")

    backup(OCRCSV, "pre153_merge")
    write_csv(OCRCSV, rows, OCR_FIELDS)
    return rows


# ---------------------------------------------------------------------------
# 2. INTEGRATE
# ---------------------------------------------------------------------------
def cmd_integrate(argv=()):
    say("\n=== 153 integrate: OCR text -> gaming_ordinances.csv ===")
    ocr = {r["ordinance_id"]: r for r in read_csv(OCRCSV)}
    rows = read_csv(ORD)
    if not rows:
        raise SystemExit("gaming_ordinances.csv is empty - refusing")
    fields = list(rows[0].keys())
    for f in NEW_ORD_FIELDS:
        if f not in fields:
            fields.append(f)
    for r in rows:
        for f in NEW_ORD_FIELDS:
            r.setdefault(f, "")

    before = Counter(r.get("text_layer_status", "") for r in rows)
    say(f"  rows                : {len(rows):,}")
    say(f"  OCR metadata rows   : {len(ocr):,}")
    say(f"  image-only before   : {before.get('IMAGE_ONLY_SCAN_NO_TEXT_LAYER', 0)}")

    bytribe = defaultdict(dict)          # index_tribe_name -> {date: oid}
    for r in rows:
        bytribe[r["index_tribe_name"]][r["index_date"]] = r["ordinance_id"]

    gained = Counter()
    dates = Counter()
    touched, skipped_refused, no_text = 0, 0, []

    for r in rows:
        oid = r["ordinance_id"]
        m = ocr.get(oid)
        if not m:
            continue
        # REFUSALS CARRIED FORWARD. A file that is another tribe's stays refused
        # however good its OCR is.
        if (r.get("md5_duplicate_of") or "").strip() or \
                r.get("confidence") == "document_served_belongs_to_another_tribe":
            skipped_refused += 1
            continue
        p = OCRDIR / f"{oid}.txt"
        if not p.exists():
            continue
        text, nch, npg, nblank = txt_stats(p)
        if len(text.strip()) < 300:
            # Same floor the build applies to a PDF text layer: a near-empty
            # OCR is a failed recovery, not an empty ordinance.
            no_text.append(oid)
            continue
        pages = text.split("\n\f\n")
        tribe = r["index_tribe_name"]

        # Idempotent: re-running must not overwrite the ORIGINAL status with
        # OCR_RECOVERED and lose the fact that this row was a scan.
        if r.get("text_layer_status") != "OCR_RECOVERED":
            r["text_layer_status_prior"] = r.get("text_layer_status", "")
        r["text_layer_status"] = "OCR_RECOVERED"
        r["confidence"] = "document_ocr_recovered"
        r["provisions_basis"] = "OCR_RECOVERED_TEXT"
        r["ocr_txt_path"] = str(p.relative_to(CEDAR)).replace("\\", "/")
        r["ocr_chars"] = nch
        r["ocr_pages"] = npg
        r["ocr_pages_blank"] = nblank
        r["ocr_mean_confidence"] = m.get("ocr_mean_confidence", "")
        r["ocr_engine"] = m.get("ocr_engine", "")
        r["ocr_dpi"] = m.get("ocr_dpi", "")
        r["ocr_date"] = m.get("ocr_date", "")
        r["ocr_metadata_basis"] = m.get("ocr_metadata_basis", "")

        # DOES THE SCAN NAME THE TRIBE IT IS FILED UNDER?
        # The build's test is a SPACED token test, and OCR breaks it. RapidOCR
        # collapses the spaces in a letterhead block, so Wyandotte Nation's 2007
        # letter reads `LeafordBearskin, Chief / WyandotteNation` and the spaced
        # test returns 0 - "this document does not name the Wyandotte Nation",
        # which is false and would read downstream as a mislinked file, the
        # exact thing this column exists to detect.
        # So a failed spaced test falls back to the space-stripped text, and
        # that fallback requires a token of 6+ characters. Substring matching on
        # a short token is the containment defect in miniature - `elim` sits
        # inside `eliminate`. The basis is recorded on the row.
        # A STATE NAME IS NOT A DISTINCTIVE TOKEN EITHER. `wyandotte` is in
        # NAME_TRAPS (Wyandotte County, Kansas), so `Wyandotte Nation,
        # Oklahoma` reduces to {oklahoma} - and the 2007 approval letter, which
        # says `WyandotteNation` four times, does not contain the word
        # Oklahoma. The spaced test therefore returned 0: "this document does
        # not name the tribe it is filed under", on a document that names it in
        # the address block. The reconcile step already excludes state names
        # from its candidate test for exactly this reason; the same exclusion
        # belongs here. With nothing left, the answer is BLANK - not testable -
        # never 0.
        distinctive = O.core(tribe) - O.CD.NAME_TRAPS - set(O.STATES)
        nt = O.norm(text)
        collapsed = re.sub(r"\s+", "", nt)
        if not distinctive:
            r["document_names_tribe"] = ""
            r["document_names_tribe_basis"] = "only_trap_or_state_tokens_in_name"
        elif any(f" {tok} " in f" {nt} " for tok in distinctive):
            r["document_names_tribe"] = "1"
            r["document_names_tribe_basis"] = "spaced_token_match"
        elif any(tok in collapsed for tok in distinctive if len(tok) >= 6):
            r["document_names_tribe"] = "1"
            r["document_names_tribe_basis"] = "ocr_space_collapsed_token_match"
        else:
            r["document_names_tribe"] = "0"
            r["document_names_tribe_basis"] = "no_token_found_in_ocr_text"

        auth, neg, cq, cbasis = O.extract_classes(text)
        if auth or neg:
            gained["classes"] += 1
        r["classes_authorized"] = "|".join(sorted(auth, key=len))
        r["classes_negated"] = "|".join(sorted(neg, key=len))
        r["class_ii_authorized"] = ("1" if "II" in auth
                                    else "0" if "II" in neg else "")
        r["class_iii_authorized"] = ("1" if "III" in auth
                                     else "0" if "III" in neg else "")
        r["classes_quote"] = cq
        r["classes_basis"] = cbasis

        ag, agq, agb = O.extract_agency(text, tribe)
        ag, refusal = clean_agency(ag, tribe)
        if refusal:
            gained["tribal_gaming_agency_REFUSED"] += 1
            agq, agb = "", refusal
        elif ag:
            gained["tribal_gaming_agency_named"] += 1
        r["tribal_gaming_agency_named"] = ag
        r["tribal_gaming_agency_quote"] = agq
        r["tribal_gaming_agency_basis"] = agb

        rap, rapq, pc, pcq = O.extract_rap_percap(text)
        if rap == "REFERENCED":
            gained["revenue_allocation_plan_referenced"] += 1
        if pc and pc != "NOT_REFERENCED":
            gained["per_capita_referenced"] += 1
        r["revenue_allocation_plan_referenced"] = rap
        r["revenue_allocation_plan_quote"] = rapq
        r["per_capita_referenced"] = pc
        r["per_capita_quote"] = pcq

        mics, micsq = O.extract_mics(text)
        if mics:
            gained["minimum_internal_control_reference"] += 1
        r["minimum_internal_control_reference"] = mics
        r["minimum_internal_control_quote"] = micsq

        lic, licq = O.extract_licensing(text)
        if lic:
            gained["licensing_provisions"] += 1
        r["licensing_provisions"] = lic
        r["licensing_quote"] = licq

        eff, effq = O.extract_effective(text)
        if eff:
            gained["effective_date"] += 1
        r["effective_date"] = eff
        r["effective_date_quote"] = effq

        chair, chq = O.extract_chair(pages[0])
        if chair:
            gained["chair_or_designee"] += 1
        r["chair_or_designee"] = chair
        r["chair_quote"] = chq

        sup_date, sup_q, sup_basis = O.extract_supersedes(text)
        r["supersedes_quote"] = sup_q
        if sup_q:
            gained["supersedes_quote"] += 1
        # An amendment amends; it does not necessarily replace. Upgrade the
        # basis only where the letter NAMES a date that is another instrument
        # of the SAME tribe on the index. The chronological chain is otherwise
        # untouched - it is index-derived and OCR says nothing about it.
        if sup_date and bytribe[tribe].get(sup_date) not in (None, oid):
            newid = bytribe[tribe][sup_date]
            if r.get("supersedes_ordinance_id") != newid:
                gained["supersedes_ordinance_id_corrected"] += 1
            r["supersedes_ordinance_id"] = newid
            r["supersedes_basis"] = "stated_in_document_date_matched"

        ldate, _ = O.extract_letter_date(pages[0])
        r["document_approval_date"] = ldate
        if not ldate:
            r["date_agreement"] = "LETTER_DATE_NOT_FOUND"
        elif ldate == r["index_date"]:
            r["date_agreement"] = "AGREE"
        else:
            d1 = datetime.fromisoformat(ldate)
            d2 = datetime.fromisoformat(r["index_date"])
            if abs((d1 - d2).days) <= 45:
                r["date_agreement"] = "AGREE_WITHIN_45_DAYS"
            elif (d1.month, d1.day) == (d2.month, d2.day) \
                    and abs(d1.year - d2.year) <= 3:
                r["date_agreement"] = "LIKELY_OCR_YEAR_MISREAD"
            else:
                # NOT `DISAGREE_DOCUMENT_IS_ANOTHER_INSTRUMENT`. That label
                # accuses NIGC's index of a defect, and a date lifted off an
                # OCR'd scanned stamp is not strong enough to make that claim.
                r["date_agreement"] = "DISAGREE_UNVERIFIED_OCR_DATE"
        dates[r["date_agreement"]] += 1
        if ldate:
            gained["document_approval_date"] += 1
        touched += 1

    # ---- integrity assertions -------------------------------------------
    assert all(r["source_url"] and r["source_quote"] for r in rows), \
        "a row without a source_url or a verbatim source_quote"
    assert not any(r.get("text_layer_status") == "TEXT_LAYER_PRESENT"
                   and r.get("provisions_basis") == "OCR_RECOVERED_TEXT"
                   for r in rows), "OCR text laundered as a born-digital layer"
    for r in rows:
        if (r.get("md5_duplicate_of") or "").strip() and \
                r.get("provisions_basis") == "OCR_RECOVERED_TEXT":
            raise AssertionError(f"{r['ordinance_id']}: md5-duplicate row gained "
                                 f"content from another tribe's document")
    assert all(r["authorisation_measurement_type"] ==
               "LEGAL_AUTHORISATION_NOT_A_COUNT"
               for r in rows if r.get("class_ii_authorized") == "1")

    after = Counter(r.get("text_layer_status", "") for r in rows)
    say(f"\n  rows integrated     : {touched}")
    say(f"  refused (md5 dup)   : {skipped_refused}")
    say(f"  OCR under 300 chars : {len(no_text)}  {no_text[:5]}")
    say(f"  image-only after    : "
        f"{after.get('IMAGE_ONLY_SCAN_NO_TEXT_LAYER', 0)}")
    say("\n  text_layer_status")
    for k, v in after.most_common():
        say(f"      {k or '(blank)':38s} {before.get(k,0):5d} -> {v}")
    say("\n  fields populated on the recovered rows")
    for k, v in sorted(gained.items(), key=lambda x: -x[1]):
        say(f"      {k:38s} {v}")
    say("\n  date_agreement on the recovered rows")
    for k, v in dates.most_common():
        say(f"      {k:38s} {v}")

    backup(ORD, "pre153_ocr_merge")
    write_csv(ORD, rows, fields)

    # ---- tribe-level effect ---------------------------------------------
    def tribeset(pred):
        return {r["tribe_id"] for r in rows if r["tribe_id"] and pred(r)}
    say("\n  tribe-level effect (keyed tribes only)")
    for label, pred in [
        ("class II authorised", lambda r: r["class_ii_authorized"] == "1"),
        ("class III authorised", lambda r: r["class_iii_authorized"] == "1"),
        ("names a tribal gaming agency",
         lambda r: bool(r["tribal_gaming_agency_named"])),
        ("references a revenue allocation plan",
         lambda r: r["revenue_allocation_plan_referenced"] == "REFERENCED"),
        ("per capita PLAN ASSERTED",
         lambda r: r["per_capita_referenced"] == "PER_CAPITA_PLAN_ASSERTED"),
        ("per capita PROHIBITED",
         lambda r: r["per_capita_referenced"] == "PER_CAPITA_PROHIBITED"),
        ("licensing provisions", lambda r: bool(r["licensing_provisions"])),
        ("internal-control reference",
         lambda r: bool(r["minimum_internal_control_reference"])),
    ]:
        s = tribeset(pred)
        via_ocr = {r["tribe_id"] for r in rows if r["tribe_id"] and pred(r)
                   and r.get("provisions_basis") == "OCR_RECOVERED_TEXT"}
        say(f"      {label:38s} {len(s):4d} tribes   "
            f"({len(via_ocr)} have an OCR-recovered instrument saying so)")
    return rows


# ---------------------------------------------------------------------------
# 3. CODEBOOK  (fragment only - codebook_master.csv has a dozen writers)
# ---------------------------------------------------------------------------
EXTRA_CODEBOOK = [
    ("text_layer_status_prior",
     "The text_layer_status this row carried before OCR recovery - "
     "IMAGE_ONLY_SCAN_NO_TEXT_LAYER on every recovered row. Kept so a recovered "
     "scan stays distinguishable from a born-digital text layer forever."),
    ("provisions_basis",
     "OCR_RECOVERED_TEXT where every provision on the row was read from OCR of "
     "an image-only scan rather than from a PDF text layer. Blank on rows parsed "
     "from a born-digital layer. A recovered scan is a different evidence grade "
     "and must never be pooled with TEXT_LAYER_PRESENT in a precision claim."),
    ("document_names_tribe_basis",
     "How document_names_tribe was established on an OCR-recovered row: "
     "spaced_token_match / ocr_space_collapsed_token_match (OCR collapsed the "
     "spaces in the letterhead, so the spaced test failed on a document that "
     "does name the tribe; the fallback requires a 6+ character token) / "
     "no_token_found_in_ocr_text / only_trap_or_state_tokens_in_name (nothing "
     "in the tribe's name is distinctive once trap tokens and state names are "
     "removed, so the document cannot be tested - the answer is blank, never "
     "0). Blank on rows read from a born-digital text layer."),
    ("ocr_txt_path", "Repo-relative path to the verbatim OCR output."),
    ("ocr_chars", "Characters of OCR text. pdf_chars is NOT overwritten - it "
                  "stays at the near-zero PDF text layer that made this a scan."),
    ("ocr_pages", "Pages OCR'd."),
    ("ocr_pages_blank", "Pages that OCR'd to nothing. Equal to ocr_pages would "
                        "be a true image failure; there are none."),
    ("ocr_mean_confidence",
     "Mean per-line rapidocr confidence over the document. BLANK, never 0, on "
     "the 28 documents recovered from an interrupted shard whose metadata row "
     "was never written - an unrecorded confidence is not a bad OCR."),
    ("ocr_engine", "rapidocr-onnxruntime. tesseract's binary is not installed."),
    ("ocr_dpi", "Render dpi. 220 for the 2026-08-13 overnight run, 300 for the "
                "smoke test, blank where the interrupted run did not record it."),
    ("ocr_date", "Date the document was OCR'd."),
    ("ocr_metadata_basis",
     "shard_csv (metadata written by the shard that OCR'd it) / prior_clean_csv "
     "/ reconstructed_from_txt_no_shard_row (the .txt survived a killed shard "
     "whose CSV was never written; chars and pages recomputed from the file, "
     "confidence unrecoverable)."),
]


def cmd_codebook(argv=()):
    say("\n=== 153 codebook fragment ===")
    master = read_csv(CLEAN / "codebook_master.csv")
    fields = (list(master[0].keys()) if master else
              ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
               "published", "access_tier", "description", "generated"])
    data = read_csv(ORD)
    n = len(data)
    book = list(O.CODEBOOK)
    have = {v for v, _ in book}
    # confidence and text_layer_status gained a value; restate them.
    book = [(v, d) for v, d in book
            if v not in ("confidence", "text_layer_status", "date_agreement",
                         "chair_or_designee", "tribal_gaming_agency_basis")]
    book += [
        ("chair_or_designee",
         "Signatory of the approval letter as printed, 'Name, Title'. A title "
         "alone means OCR lost the signature. NOT NORMALISED, and on an "
         "OCR_RECOVERED row the spelling is the OCR's: `Hafold A. Monteau`, "
         "`Haroxd A. Monteau` and `Harold A. Monteau` are one NIGC chairman. "
         "A DISTINCT COUNT OVER THIS COLUMN IS NOT A COUNT OF PEOPLE - group "
         "born-digital rows only, or normalise first."),
        ("tribal_gaming_agency_basis",
         "tribe_specific_name where the body's name carries the tribe's own "
         "distinctive tokens; generic_name_in_ordinance otherwise; or a "
         "refusal reason on an OCR_RECOVERED row - refused_state_named_body:"
         "<string> where the captured body is a STATE agency (Arizona Gaming "
         "Commission), refused_too_short_after_ocr_cleanup. The refused string "
         "is kept in the basis so the receipt survives the refusal."),
        ("confidence",
         "document_parsed / document_ocr_recovered / document_no_text_layer / "
         "document_unreadable / document_served_belongs_to_another_tribe / "
         "index_only - the evidentiary basis, not a probability."),
        ("text_layer_status",
         "TEXT_LAYER_PRESENT / OCR_RECOVERED / IMAGE_ONLY_SCAN_NO_TEXT_LAYER / "
         "UNREADABLE:<error> / NOT_RETRIEVED / NO_DOCUMENT_LINKED_ON_INDEX. A "
         "near-empty extraction is a scan, not an empty document; OCR_RECOVERED "
         "means that scan was read by OCR and never that it had a text layer."),
        ("date_agreement",
         "AGREE / AGREE_WITHIN_45_DAYS / LIKELY_OCR_YEAR_MISREAD / "
         "DISAGREE_DOCUMENT_IS_ANOTHER_INSTRUMENT (born-digital text only) / "
         "DISAGREE_UNVERIFIED_OCR_DATE (the same disagreement read off OCR of a "
         "scanned date stamp - too weak to accuse NIGC's index of a defect) / "
         "LETTER_DATE_NOT_FOUND / NO_TEXT / NO_DOCUMENT."),
    ]
    book += [(v, d) for v, d in EXTRA_CODEBOOK if v not in have]

    rows = []
    for var, definition in book:
        filled = sum(1 for r in data if (r.get(var) or "").strip())
        num = all(re.fullmatch(r"-?\d+", (r.get(var) or "0").strip() or "0")
                  for r in data) if data else False
        rr = {f: "" for f in fields}
        rr.update({
            "dataset": "07f_gaming_ordinances", "variable": var,
            "type": "integer" if num and var.endswith(
                ("_authorized", "_number", "_pages", "_chars", "_bytes",
                 "_blank", "_dpi")) else
            "numeric" if var == "ocr_mean_confidence" else
            "date" if var.endswith("_date") else "text",
            "units": "code" if var.endswith("_id") else "",
            "pct_filled": f"{100.0 * filled / n:.1f}" if n else "",
            "n_rows": n,
            "published": 0,
            "access_tier": "internal_pending_review",
            "description": definition,
            "generated": TODAY,
        })
        rows.append(rr)
    k = CB.write_fragment("07f_gaming_ordinances", rows, fields)
    say(f"  wrote data/clean/codebook/07f_gaming_ordinances.csv ({k} rows) - "
        f"codebook_master.csv NOT touched")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("merge", "all"):
        cmd_merge(sys.argv[2:])
    if cmd in ("integrate", "all"):
        cmd_integrate(sys.argv[2:])
    if cmd in ("codebook", "all"):
        cmd_codebook(sys.argv[2:])
    if cmd not in ("merge", "integrate", "codebook", "all"):
        raise SystemExit(f"unknown command {cmd!r}")
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print(f"\n  run summary -> {SUMMARY.relative_to(CEDAR)}")
