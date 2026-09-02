# Response to the external design review

*2026-08-30. Every falsifiable claim in the review was tested against the code
and the live data before anything was changed. This document records what was
verified, what was fixed the same day, what was deferred and why, and — where
it applies — where the reviewer was more right than the packet they were given.*

**Headline: the review was correct on every claim we could falsify, including
one that was mathematically exact.** Nothing in it was overstated.

---

## Verified, then fixed the same day

### F17 — check-code blind spots. VERIFIED EXACTLY, including the position pairs.

The reviewer derived that undetected two-symbol payload errors satisfy
`W1·e ≡ W2·e ≡ 0 (mod 32)`, and named the affected 1-indexed position pairs
(1,3), (1,5), (2,4), (3,5). Exhaustive search over all 32² deltas across all
ten position pairs:

```
two-position payload null vectors: 8
position pairs affected (1-indexed): [(1,3), (1,5), (2,4), (3,5)]   <- exact match
CE-00000-00 and CE-G0G00-00 share the check characters   -> True
CE-G0000-0G and CE-00G00-0G share the check characters   -> True
check('G0000') == '0G'   -> True
check('00002') == 'CJ'   -> True
check('0000J') == 'C2'   -> True
```

The root cause is as stated: 32 is composite, so 16 is a zero divisor and
"independent weight vectors" does not buy what it would over a field. **The
code's minimum symbol distance is 2.** Our original claim — all single-symbol
substitutions and all adjacent transpositions detected — remains true and the
reviewer confirms it, but it is a much narrower guarantee than a reader might
infer, and the packet did not say so.

**Action taken:** documented as a precise V1 guarantee rather than silently
carried. **Not** re-minting: 1,536 uids are stamped across 125 tables and a
re-mint to gain distance-3 would break every downstream reference to fix a
class of error (two simultaneous symbol errors in specific position pairs)
that a registry-existence check already catches — a uid that is not in the
register is rejected regardless of its check characters. If uids ever become
externally hand-keyed, the reviewer's Reed–Solomon [7,5,3] over GF(32) is the
right V2 and should be versioned, not swapped in place.

### F2 — inverse identifier uniqueness. VERIFIED AS A REAL GAP; NOW ENFORCED.

The reviewer's scenario: two agents attach the same UEI to the Native Village
of Elim and to Elim Native Corporation. Because identifiers are multi-valued
and conflicts are grouped *by subject*, both assertions are locally valid,
neither competes, nothing reaches the conflict table, and a transaction joined
through that UEI is assigned twice.

Measured against live data at review time:

| identifier | count | bound to >1 entity |
|---|---:|---:|
| UEI | 4,069 | **0** |
| CAGE | 2,897 | **0** |
| EIN | 769 | **0** |

So the failure had not occurred — **but the reviewer's real point is that
nothing prevented it.** It was true by discipline, not by construction.

**Action taken:** invariant **I10** added to `510 verify`: no identifier may
be bound to more than one entity by a live (non-deny) assertion. Deny rows are
excluded, because refuting a link is how a wrong one is withdrawn.

**Proven by fixture, not assumed:** cloning a real UEI assertion onto a second
entity makes verify exit 1 with `I10 1 identifier(s) bound to MORE THAN ONE
entity`; removing it returns exit 0.

### F7 — `entity.registration_state` at the wrong grain. VERIFIED; GRAIN FIXED.

Renaming the predicate did not fix the subject. Measured: **113 entities
carried multiple `registration_state` values, one with 35** — and no value
carried any pointer to which registration produced it. A buyer joining on
`cedar_uid` would fan out up to 35×, and a deny would have removed a state
globally though it remained valid for another registration.

**Action taken:** assertions now carry `subject_qualifier`, and the subject of
a fact is **(entity, qualifier)**. Registration-derived facts are qualified
with the registration that produced them (`UEI:XXXXXXXXXXXX`); resolution,
conflicts and every invariant group on the full subject.

**This immediately exposed a second error of ours.** Corroborated facts fell
**38 → 2**. The 36 lost were `entity.legal_business_name` "corroborations"
that were only ever different registrations' names collapsed onto one entity.
They were never corroboration; the wrong grain had been manufacturing it. The
honest number is 2.

### F3 + F4 — unsupported facts, and R07 manufacturing certainty. BOTH ACTED ON.

The reviewer's sharpest general point: *"the absence of competing evidence
makes the bad claim easier to resolve, not harder"*, and `resolved` only ever
meant "a rule selected it", never "it is supported".

**Action taken, two separate mechanisms:**

1. **`support_status` on every resolved fact**, orthogonal to
   `resolution_status`. Current distribution across 32,551 facts:

   | support_status | facts |
   |---|---:|
   | traceable_single_source | 18,715 |
   | **legacy_only** | **11,661** |
   | authoritative | 1,319 |
   | unverified_single_source | 832 |
   | refuted | 22 |
   | corroborated | 2 |

   Of these, **4,100 are identity-critical facts standing on `legacy_only`
   evidence** — a row with no recorded provenance. That number is now a gated
   metric (`identity_facts_legacy_only`, MUST_NOT_RISE) so the exposure can
   only shrink. *(Re-measured 2026-09-01: **4,089**. The ratchet floor in
   `data/clean/_regression_baseline.json` reads 4089, so the exposure has in
   fact shrunk by 11 and the gate has locked in the smaller number. Where this
   paragraph and the baseline disagree, the baseline is the live figure.)*

2. **R07 may no longer decide an identity-critical predicate.** Ties on
   entity class, canonical name, official name, recognition, parentage,
   constituency, identifiers or state now resolve to **`UNRESOLVED_TIE`**,
   with every candidate written to the conflict table. Currently 0 — a hash
   winner is never published as fact on these predicates.

### F18 — the metric contradiction. VERIFIED; IT WAS OUR REPORTING ERROR.

"0 single-valued facts have two sources" and "38 have >1 independent evidence
family" were both true but reported without their scopes: all 38 were
**multi-valued** facts. The reviewer was right that it reads as a
contradiction. Compounded by F7 above, the honest figure is now **2**.

Also accepted: **"0 disagreements found" is not a quality result** when no two
sources observe the same fact. The disagreement rate is *undefined*, not zero,
and is now stated that way.

---

## Accepted as correct, scheduled rather than done today

These need design work beyond a session and are recorded as open, not waved off.

- **F1 (critical) — the source-record→UID link is not its own contestable
  assertion.** Correct, and it is the deepest finding in the review: an
  authoritative source fact can become a wrong authoritative Cedar fact via a
  bad match, because authority attaches after resolution. The fix is a
  `source_record` node with `refers_to` as a first-class, evidenced,
  refutable assertion. This changes the harvest layer's shape and is the next
  major piece of work.
- **F5 (critical) — bitemporality.** Accepted without reservation. Today's
  facts are applied to historical transactions; a subsidiary sold in 2027
  would mis-key its pre-sale awards. Needs `valid_from`/`valid_to`,
  `observed_at`, `source_effective_date`, plus merge/split/successor/tombstone
  policy.
- ~~**F6 (critical) — mutable handles as customer join keys.**~~ **CLOSED
  2026-08-30, workstream D.** `data/spine/cedar_handle_history.csv` retains
  every `(handle, uid, valid_from, valid_to, status, change_reason)` binding;
  an old handle always resolves to the same uid; a retired handle pointed at
  another entity raises. The bug was worse than the finding said: the mint
  phase keyed on the handle, so a reclassification **minted a second uid**
  rather than merely breaking a buyer's join. See ADR-006.
- ~~**F10 — global precedence is wrong for some predicates**~~ **CLOSED
  2026-08-30, workstream D.** Six per-predicate resolution policies in
  `data/spine/cedar_resolution_policies.csv`; a policy owns its rule order,
  whether a non-authority deny may pre-empt R02, whether a stale deny may
  veto, and whether stale families count toward corroboration. A blocked deny
  is kept as an `R01-BLOCKED` contest, not discarded. Invariant **I11**
  recomputes every veto and fails if one removed a protected value —
  fixture-proven. **No live fact changed**: all 332 denies today are on
  identifier predicates, which declare no authority, so the defect was
  structural and unreached. It is now unreachable by construction rather
  than by luck. See ADR-005.
- **F11 — re-observation.** Correct: a re-check of an unchanged claim
  produces an unchanged assertion id, so the layer cannot record "still true
  as of today" without either mutating an append-only row or duplicating an
  id. Needs an `observation` table distinct from the claim.
- **F12 — lineage should be an assertion-level DAG, not a source-level tree.**
  Accepted; a compiled source genuinely has different parentage per field.
- **F13 — a checksum is a receipt, not a backup.** Accepted, and it sharpens
  what our replay drill proved: we demonstrated that *code at a commit runs
  and validates*, never that inputs could be reconstructed.
- ~~**F9 — grain**~~ **CLOSED as infrastructure 2026-08-30, workstream D,
  and the honest number is uncomfortable.** A declaration is now `grain` +
  `primary_key` + `join_keys` + `join_cardinality`, validated against the
  file on every run; a declared grain the data contradicts is
  release-blocking. When this was written, **3 of 210 shippable tables
  declared and validated one and 207 did not**, and that count was ratcheted
  (`contract_grain_unstated_shippable`, MUST_NOT_RISE) rather than claimed as
  done.

  **Updated 2026-09-01 (workstream H), measured: 185 of 210 now declare and
  validate a grain; 25 do not.** The sweep tested candidate keys against the
  FULL file for all 207 and split them honestly — 185 DECLARED_VALIDATED, 12
  OPEN_WITH_EVIDENCE (a question only an owner can answer), 13 DEFECTIVE (the
  data is broken and a declaration cannot fix it), 0 unexplained.
  `contract_violations` is still 0. See ADR-007 and `docs/GRAIN_AUDIT.md`.
- **F8 — a subsidiary fused to its parent.** Analysed, proposal recorded, NOT
  implemented. Measured: **3,511 distinct (entity, differing legal name)
  pairs** across 714 entities, carrying **$173.9B** of prime dollars, are
  currently representable only as an attribute of somebody else. The proposal
  is a registration SUB-HUB with its own key and an assertable, refutable
  `registration_is_separately_incorporated` defaulting to *unknown* — not
  promotion of every registrant. It depends on ADR-003's validity time to be
  worth anything. See ADR-008.
- **F14, F15, F16** — accepted as stated, still open.

## One correction to the reviewer

The packet's date header read 2026-08-30 while the reviewer's clock read
2026-08-29. The reviewer was right to flag it: the machine's date rolled
during a long session and the header took the later value. It is a real
instance of exactly the clock-semantics problem F11 raises, and it is fixed.

---

## What changed in the code

```
510_assertions.py   subject_qualifier; subject = (entity, qualifier)
                    support_status on every resolved fact
                    R07 barred on identity-critical predicates -> UNRESOLVED_TIE
                    I10 inverse identifier uniqueness (fixture-proven)
                    I3/I5/I6/I8 regrouped on the full subject
62_no_regression    identity_facts_legacy_only  (MUST_NOT_RISE, at 4,100)
                    identity_facts_unresolved_tie (queue metric, at 0)
```

Gate green, `510 verify` OK, baseline recorded while green.

**The reviewer's minimum commercial release threshold is adopted as our
standard**, with three of its five conditions now met (inverse constraints
enforced; hash-tiebroken identity facts cannot ship; grain validated and
release-blocking), and two open (source links independently modelled; a
release replayed from retained immutable inputs).
