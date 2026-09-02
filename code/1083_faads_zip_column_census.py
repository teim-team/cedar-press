"""1083 - FAADS staged-zip COLUMN CENSUS. Settles the 29.8% transaction-key ceiling.

Two workstreams disagree about why `assistance_transaction_unique_key` is present
on only 29.8% of `faads_transactions_all_agencies.csv`:

  claim A (docs/methodology/funding.md 4b): the 60 `<agency>_fy200{1..6}.zip`
          objects are 20-COLUMN objects. `30_funding_pre2008.COLUMNS` requested a
          20-of-112 subset, so the bytes never held the key. No re-extract can
          recover it.
  claim B (elsewhere): the key IS in the staged zips; the re-extract is queued and
          unrun.

This script does not argue. It OPENS every staged zip, reads the header line of
every CSV member WITHOUT extracting the body, and reports the column count and
whether the key literal is present. Read-only: opens nothing for write, touches
no table, makes no network call.

Usage:  py -3 code/1083_faads_zip_column_census.py
        py -3 code/1083_faads_zip_column_census.py --json out.json
"""
import csv, io, json, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAADS = ROOT / "data" / "raw" / "external" / "faads"
KEY = "assistance_transaction_unique_key"
ALSO = ["modification_number", "recipient_zip_code", "recipient_county_name",
        "recipient_city_name", "assistance_award_unique_key", "federal_action_obligation"]


def header_of(zf, name):
    """Read ONLY the first line of a zip member. Never extracts the body."""
    with zf.open(name) as fh:
        buf = b""
        while b"\n" not in buf and len(buf) < 1 << 20:
            chunk = fh.read(65536)
            if not chunk:
                break
            buf += chunk
        line = buf.split(b"\n", 1)[0].decode("utf-8-sig", "replace").rstrip("\r")
    return next(csv.reader(io.StringIO(line)))


def main():
    zips = sorted(FAADS.rglob("*.zip"))
    if not zips:
        print("UNMEASURED: no zips found under", FAADS)
        return 2
    rows = []
    for z in zips:
        rel = z.relative_to(ROOT).as_posix()
        try:
            with zipfile.ZipFile(z) as zf:
                members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
                if not members:
                    rows.append(dict(zip=rel, member="", n_cols=None,
                                     has_key=None, note="NO CSV MEMBER",
                                     members=zf.namelist()[:5]))
                    continue
                for m in members:
                    hdr = header_of(zf, m)
                    rows.append(dict(
                        zip=rel, member=m, n_cols=len(hdr),
                        has_key=KEY in hdr,
                        also={c: (c in hdr) for c in ALSO},
                        note="",
                        first5=hdr[:5],
                    ))
        except Exception as e:  # a zip we cannot open is UNMEASURED, not clean
            rows.append(dict(zip=rel, member="", n_cols=None, has_key=None,
                             note="UNREADABLE: %s" % e))

    print("=" * 78)
    print("FAADS STAGED-ZIP COLUMN CENSUS   (read-only, header bytes only)")
    print("root:", FAADS.relative_to(ROOT).as_posix())
    print("=" * 78)
    print("%-58s %6s %5s" % ("zip member", "ncols", "key?"))
    print("-" * 78)
    for r in rows:
        tag = "n/a" if r["has_key"] is None else ("YES" if r["has_key"] else "no")
        label = r["zip"].replace("data/raw/external/faads/", "")
        if r["member"] and len(members := r.get("member", "")) and r["member"] != label:
            label = "%s :: %s" % (label, r["member"])
        print("%-58s %6s %5s %s" % (label[:58], r["n_cols"], tag, r["note"]))

    total = len(rows)
    unread = [r for r in rows if r["has_key"] is None]
    withkey = [r for r in rows if r["has_key"] is True]
    without = [r for r in rows if r["has_key"] is False]
    print("-" * 78)
    print("members measured : %d" % total)
    print("  key PRESENT    : %d" % len(withkey))
    print("  key ABSENT     : %d" % len(without))
    print("  UNMEASURED     : %d" % len(unread))
    if unread:
        print("  !! UNMEASURED members exist - do NOT read this run as clean:")
        for r in unread:
            print("     ", r["zip"], r["note"])

    from collections import Counter
    print()
    print("column-count distribution over members where the key is ABSENT:")
    for n, c in sorted(Counter(r["n_cols"] for r in without).items(),
                       key=lambda kv: (kv[0] is None, kv[0])):
        print("   %s cols : %d members" % (n, c))
    print("column-count distribution over members where the key is PRESENT:")
    for n, c in sorted(Counter(r["n_cols"] for r in withkey).items(),
                       key=lambda kv: (kv[0] is None, kv[0])):
        print("   %s cols : %d members" % (n, c))

    print()
    print("VERDICT")
    if without and all(r["n_cols"] is not None and r["n_cols"] <= 30 for r in without):
        print("  claim A holds: every key-absent member is a narrow-column object.")
        print("  The bytes on disk do not contain the key. NO re-extract can recover it.")
    elif without:
        print("  MIXED: some key-absent members are wide. Enumerate them before concluding.")
    else:
        print("  claim B holds: the key is present in every staged member.")

    if "--json" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--json") + 1])
        out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
