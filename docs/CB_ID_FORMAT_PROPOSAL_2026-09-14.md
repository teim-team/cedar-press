# Cedar Business ID format: three specifications, one recommendation

*Written 2026-09-14. **A proposal for the owner's decision; nothing here is
adopted or applied.** The R7 register stays a frozen source until this is
decided (gate G04 in `code/1188_import_chatgpt_r7_business_register.py`).
Once decided, this content folds into the identity specification and this
file is retired.*

---

## 1. The three specifications, and one retired form

| | form | where | status |
|---|---|---|---|
| **ADR-043** (owner decision 2026-09-06) | `CB-0001842-XQ`: seven digits plus "the standard's two check characters over the uid's alphabet" (letters and digits) | `docs/ARCHITECTURE_DECISIONS.md` ADR-043; `docs/CEDAR_BUSINESS_ID_DECISION_2026-09-06.md` | decided, never implemented or minted |
| **Identity specification** (2026-09-13) | `CB-0000001`: plain serial; "a check-character convention can be added later" | `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` §2, §7.1 | specified, never minted |
| **R7 as issued** (ChatGPT, 2026-09-14) | `CB-1000001` to `CB-1017282`: seven digits, no check | R7 `registries/Cedar_Business_Register.csv` inside the frozen ZIP | 17,282 issued, 17,279 active, 3 retired by lineage |
| R3–R5 legacy (ChatGPT, 2026-09-14) | `CB-000001-9A`: six digits plus two characters | R7 `registries/Legacy_Business_ID_Crosswalk.csv` | retired within R6; 3,295 mapped to R7 ids, 55 unmapped |

## 2. Has any business id been used outside?

Checked 2026-09-14. **No evidence found that any issued id left the owner's
machine.** This is the absence of evidence on the surfaces below, not proof.

| surface | result |
|---|---|
| git, every local and fetched remote branch | no issued id ever committed; only the specification examples `CB-0000001` and `CB-0001842-XQ` |
| the live site | shows `CB-0000001` as the *form*, marked "In progress" |
| `public/`, `dist/` | none |
| the private tracking artifact | none; its one `CB-729799` match is inside a GUID |
| owner's sent Gmail since 2026-08-25 | no Cedar data attachment to anyone else; messages to Indian Country Media on 2026-09-03 and 2026-09-04 and a self-sent Deals bundle on 2026-09-06 all predate the R3–R7 packages, which are dated 2026-09-14 |

**Not checkable from here:** ChatGPT share links or its conversation, Slack or
other messaging, files handed over another way. **The owner must confirm.**

## 3. Measurements

Every seven-digit number from 1,000,001 to 1,017,282 is an issued R7 id. Measured
below, **56.48%** of single-digit substitutions and **53.93%** of adjacent
transpositions of an issued id produce *another issued id*; the rest produce a
number no business holds, which a lookup would fail to find. With no check
component, neither kind of error is detectable from the id itself. The
measurement below tests, for **all 17,282 R7 serials**, every
single-character substitution within the payload alphabet and every adjacent
transposition of unequal characters, and counts how many a check would fail to
detect.

**Commands** (read-only, no bytecode written; run from the repository root; both read
the frozen ZIP member directly and run the same Python):

**PowerShell** (the documented environment):

```powershell
@'
import csv, io, zipfile, importlib.util
spec = importlib.util.spec_from_file_location("i", "code/503_identity.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
z = zipfile.ZipFile("data/external/Cedar_Complete_Data_and_Claude_Handoff_2026-09-14.zip")
member = [n for n in z.namelist() if n.endswith("Cedar_Tribal_Review_R7_2026-09-14/registries/Cedar_Business_Register.csv")]
assert len(member) == 1
serials = [r["business_uid"][3:] for r in csv.DictReader(io.StringIO(z.read(member[0]).decode("utf-8-sig")))]
def mod97(p): return f"{98 - (int(p) * 100) % 97:02d}"
def measure(payloads, alphabet, check):
    subs = miss_s = trans = miss_t = 0
    for p in payloads:
        c = check(p)
        for k in range(len(p)):
            for ch in alphabet:
                if ch != p[k]:
                    subs += 1; miss_s += check(p[:k] + ch + p[k+1:]) == c
        for k in range(len(p) - 1):
            if p[k] != p[k+1]:
                trans += 1; miss_t += check(p[:k] + p[k+1] + p[k] + p[k+2:]) == c
    return f"substitutions missed {miss_s}/{subs} ({100*miss_s/subs:.2f}%); adjacent transpositions missed {miss_t}/{trans} ({100*miss_t/trans:.2f}%)"
print("serials:", len(serials), "range", min(serials), "-", max(serials))
print("503 check_chars weights:", m._W1, m._W2)
print("A 503 check_chars over 7 digits :", measure(serials, "0123456789", m.check_chars))
print("B ISO 7064 MOD 97-10 over 7 digits:", measure(serials, "0123456789", mod97))
print("C 503 check_chars over base-32   :", measure([m.encode(int(p)) for p in serials], m.B32, m.check_chars))
issued = set(serials)
land_s = sum((p[:k] + ch + p[k+1:]) in issued for p in serials for k in range(7) for ch in "0123456789" if ch != p[k])
land_t = sum((p[:k] + p[k+1] + p[k] + p[k+2:]) in issued for p in serials for k in range(6) if p[k] != p[k+1])
print(f"errors landing on another issued id: substitutions {land_s}/1088766 ({100*land_s/1088766:.2f}%); adjacent transpositions {land_t}/86539 ({100*land_t/86539:.2f}%)")
'@ | py -3 -B -
```

**Bash:**

```
py -3 -B - <<'EOF'
import csv, io, zipfile, importlib.util
spec = importlib.util.spec_from_file_location("i", "code/503_identity.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
z = zipfile.ZipFile("data/external/Cedar_Complete_Data_and_Claude_Handoff_2026-09-14.zip")
member = [n for n in z.namelist() if n.endswith("Cedar_Tribal_Review_R7_2026-09-14/registries/Cedar_Business_Register.csv")]
assert len(member) == 1
serials = [r["business_uid"][3:] for r in csv.DictReader(io.StringIO(z.read(member[0]).decode("utf-8-sig")))]
def mod97(p): return f"{98 - (int(p) * 100) % 97:02d}"
def measure(payloads, alphabet, check):
    subs = miss_s = trans = miss_t = 0
    for p in payloads:
        c = check(p)
        for k in range(len(p)):
            for ch in alphabet:
                if ch != p[k]:
                    subs += 1; miss_s += check(p[:k] + ch + p[k+1:]) == c
        for k in range(len(p) - 1):
            if p[k] != p[k+1]:
                trans += 1; miss_t += check(p[:k] + p[k+1] + p[k] + p[k+2:]) == c
    return f"substitutions missed {miss_s}/{subs} ({100*miss_s/subs:.2f}%); adjacent transpositions missed {miss_t}/{trans} ({100*miss_t/trans:.2f}%)"
print("serials:", len(serials), "range", min(serials), "-", max(serials))
print("503 check_chars weights:", m._W1, m._W2)
print("A 503 check_chars over 7 digits :", measure(serials, "0123456789", m.check_chars))
print("B ISO 7064 MOD 97-10 over 7 digits:", measure(serials, "0123456789", mod97))
print("C 503 check_chars over base-32   :", measure([m.encode(int(p)) for p in serials], m.B32, m.check_chars))
issued = set(serials)
land_s = sum((p[:k] + ch + p[k+1:]) in issued for p in serials for k in range(7) for ch in "0123456789" if ch != p[k])
land_t = sum((p[:k] + p[k+1] + p[k] + p[k+2:]) in issued for p in serials for k in range(6) if p[k] != p[k+1])
print(f"errors landing on another issued id: substitutions {land_s}/1088766 ({100*land_s/1088766:.2f}%); adjacent transpositions {land_t}/86539 ({100*land_t/86539:.2f}%)")
EOF
```

**Result, 2026-09-14** (identical from both commands):

```
serials: 17282 range 1000001 - 1017282
503 check_chars weights: (2, 3, 4, 5, 6) (1, 4, 9, 16, 25)
A 503 check_chars over 7 digits : substitutions missed 311076/1088766 (28.57%); adjacent transpositions missed 15555/86539 (17.97%)
B ISO 7064 MOD 97-10 over 7 digits: substitutions missed 0/1088766 (0.00%); adjacent transpositions missed 0/86539 (0.00%)
C 503 check_chars over base-32   : substitutions missed 0/2678710 (0.00%); adjacent transpositions missed 0/67020 (0.00%)
errors landing on another issued id: substitutions 614920/1088766 (56.48%); adjacent transpositions 46668/86539 (53.93%)
```

**What A does and does not show.** A applies the existing entity-id function,
`check_chars` in `code/503_identity.py`, unchanged to a seven-digit payload. The
function carries five weights and zips them against the payload, so the sixth
and seventh digits do not enter the check. That measures **one naive
implementation** of ADR-043, not ADR-043 itself: ADR-043 does not specify an
algorithm, and a check over the uid alphabet with seven weights could be built
and measured. What A shows is that reusing the entity function as written is
unsafe for business ids.

**Limits of all three measurements:** single-character and adjacent-swap
errors only; no multi-character errors, no jump transpositions, no OCR
confusions; payloads limited to the R7 serial range.

## 4. Options and their migration consequences

| | option | visible ids change? | migration | measured protection |
|---|---|---|---|---|
| A | Keep R7 as issued, `CB-1003375` | no | none | none |
| B | ADR-043 via the existing entity function, `CB-1003375-3W` | suffix added | re-render 17,282 ids, 3 lineage rows, 3,295 crosswalk rows | partial (§3, row A) |
| B′ | ADR-043 with a new seven-weight check over the uid alphabet | suffix added | same as B, plus a new algorithm to specify, implement and measure | not yet measured |
| C | Specification 2026-09-13, restart at `CB-0000001` | every id renumbered | lookup table for 17,282 ids and 3,350 legacy ids | none |
| **D** | **R7 serial + ISO 7064 MOD 97-10, `CB-1003375-77`** | suffix of two digits added | deterministic re-render; stripping the suffix returns the R7 id; no lookup table | full for the error classes measured (§3, row B) |
| E | Base-32 serial + existing entity function, `CB-0YKVF-7A` | every visible id changes | lookup needed to read any R-package | full for the error classes measured (§3, row C) |

## 5. Recommendation: option D, with what it would change

**Proposed:** `CB-` + the R7 seven-digit serial + `-` + two ISO 7064 MOD 97-10
check digits. Cherokee Nation Businesses, L.L.C. would read `CB-1003375-77`.

**This is not what ADR-043 specifies.** ADR-043 calls for check *characters over
the uid alphabet*; option D uses decimal check *digits* from a different
standard. Adopting D would **amend** ADR-043 and the identity specification;
it is not already sanctioned by either. Option B′ is the way to honour ADR-043's
letter literally, at the cost of designing and measuring a new algorithm.

Why D is recommended anyway:

- **Keeps R7's numbering.** Every R7 id maps to its canonical form by appending
  two digits; no renumbering and no lookup table.
- **Full detection for the measured error classes**, using a published standard
  rather than a new in-house algorithm.
- **Cheapest now,** given §2: no evidence of external use yet.
- **Separable from the legacy form.** Legacy ids have six digits and a
  letter-bearing suffix; D has seven digits and a two-digit suffix. 13 of the
  3,350 legacy ids happen to satisfy MOD 97-10 over their six digits, so a
  validator must require exactly seven.

**Migration, if approved** (one separate reviewed change, not started):

1. Render the 17,282 issued ids, the 3 lineage rows and the 3,295 mapped legacy
   rows in the new form, keeping each R7 form as a recorded alias.
2. The resolver accepts both forms, rejects a seven-digit id whose check digits
   fail, and never corrects one.
3. Future R-rounds emit the canonical form, or intake re-renders them by the
   same function.
4. Amend ADR-043 and the identity specification §2 and §7.1; update the Methods
   page sample and its test to a real id in the adopted form.
5. Record the decision in `docs/imports/R7_OWNER_DECISIONS.json` under
   `gates.cb_id_format`, in the schema `code/1188` validates. Only that record
   opens gate G04.

## 6. Decisions needed

1. Choose D, B′ or another option.
2. Confirm whether any R3–R7 file was shared outside by a channel §2 could not
   check.
