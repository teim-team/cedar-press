# Twelve `cedar_uid` values resolve to more than one Native entity

Found 2026-09-03, while answering the owner's question "are we still using CICD
NEIDs?" — a question about identifier provenance that turned out to have a defect
sitting under it.

## The invariant being violated

The owner stated it directly on 2026-09-02:

> "The Cedar UID must always resolve to the same impermeable Native entity, while
> the dataset separately identifies the event/object/business and describes the
> Native entity's role."

Measured in `data/clean/cedar_identifier_ledger_final.csv`: of 878 entities carrying
both a `cedar_uid` and a `tribe_id` (NEID), **12 `cedar_uid` values map to two or
more distinct NEIDs**, and 11 NEIDs map to two or more `cedar_uid` values.

The second is fragmentation and merely wasteful. **The first is the invariant
breaking**, and it is the root cause of nearly every "ownership conflict" worked in
`docs/OWNER_QUEUE_RECONCILIATION_2026-09-03.md`.

## The twelve

| `cedar_uid` | resolves to | and to |
|---|---|---|
| `CE-0018V-EC` | `ANVC-TIKIGA-00` Tikigaq Corporation | `TRBF-PTTRUT-00` Paiute of Utah |
| `CE-0012J-TB` | `ANRC-BRBYCO-00` Bristol Bay Native Corporation | `TRBF-BNVSTA-00` Buena Vista Rancheria |
| `CE-0007C-BW` | `ANRC-CHGCCO-00` Chugach Alaska Corporation | `SGVF-CHGCMT-00` Chugachmiut self-governance consortium |
| `CE-0017X-NE` | `TRBF-ONDANY-00` Oneida (New York) | `TRBF-ONDAWI-00` Oneida Nation (Wisconsin) |
| `CE-00170-7S` | `CNSF-MINNCH-LL` Leech Lake | `TRBF-MINNCH-00` Minnesota Chippewa |
| `CE-0007D-HN` | `ANRC-CHGCCO-00` Chugach Alaska Corporation | `ANRC-CKINLT-00` Cook Inlet Region, Inc. |
| `CE-0012P-JF` | `ANRC-CKINLT-00` Cook Inlet Region, Inc. | `TRBF-CABAZN-00` Cabazon |
| `CE-0014C-0N` | `ANRC-CKINLT-00` Cook Inlet Region, Inc. | `TRBF-ESWNDR-00` Eastern Shoshone |
| `CE-0016E-P7` | `ANRC-CKINLT-00` Cook Inlet Region, Inc. | `TRBF-LUMBEE-00` Lumbee |
| `CE-0005G-S0` | `AKNF-SAXMAN-00-…` Saxman | `ANVC-CAPEFO-00` Cape Fox Corporation |
| `CE-00020-A0` | `AKNF-GWCHZG-00-…` Fort Yukon | `ANVC-GANAAY-00` Gana-A'Yoo · `ANVC-KYTLTS-00` K'oyitl'ots'ina |
| `CE-0006R-ER` | `AKNF-VEAGLE-00-…` Eagle | `ANRC-BERSTR-00` Bering Straits · `ANRC-BRBYCO-00` Bristol Bay · `ANVC-CAPEFO-00` Cape Fox |

## Why this matters more than twelve rows

**Every ownership "conflict" I researched today traces back to one of these.** The
field sheet was not reporting a disagreement between Cedar and a source. It was
reporting **the two heads of a single `cedar_uid` against each other**, with one
head printed as "Cedar says" and the other as "source says".

| Card worked today | Unlocks | The two-headed uid underneath |
|---|---:|---|
| Tikigaq Technology Services | $480,510,212 | `CE-0018V-EC` (Tikigaq ∥ Paiute of Utah) |
| Vista Defense Technologies | $729,479,396 | `CE-0012J-TB` (Bristol Bay ∥ Buena Vista) |
| Eagle Eye Electric | $313,575,216 | `CE-0006R-ER` (Eagle ∥ Bering Straits ∥ Bristol Bay ∥ Cape Fox) |
| Mission Support / OTIE | $734,768,250 | `CE-0017X-NE` (Oneida NY ∥ Oneida WI) |
| Chugach Regional Resources Commission | $1,157,620 | `CE-0007C-BW` (Chugach Alaska Corp ∥ Chugachmiut) |
| Leech Lake Reservation Business Committee | $14,937,747 | `CE-00170-7S` (Leech Lake ∥ Minnesota Chippewa) |

Three of those deserve specific note:

- **`CE-0006R-ER` is four-headed.** I ruled Eagle Eye Electric to Bering Straits
  from a published source. Bering Straits is *one of the four heads already on the
  uid*. The research was right and also insufficient — resolving the card does not
  resolve the identifier.
- **`CE-0017X-NE` is the Oneida precision caveat, mechanised.** I flagged in the
  rulings CSV that MS2 and OTIE belong to the Oneida Nation of *Wisconsin*, not the
  Oneida Indian Nation of *New York*. That is not a caveat about the sources — Cedar
  holds both under one `cedar_uid`.
- **`CE-00170-7S` retires the question I escalated to the owner.** I sent Leech Lake
  up as a philosophical matter: is the impermeable entity the Minnesota Chippewa
  Tribe or its constituent band? It is still a real question — but it is *also* a
  concrete violation right now, because one uid carries both, and that is wrong
  whichever answer the owner gives. It needs the ruling *and* a split.

## Not previously tracked, and not guarded

- No mention in `AGENTS.md` or `docs/KNOWN_ISSUES.md`.
- `code/846_session_audit.py:128` asserts *"every cedar_uid in the register is
  unique and none is blank"*. That is a different claim: uniqueness **within the
  register table**, not "resolves to one entity **in the ledger**". A uid can be
  perfectly unique as a register row and still be two-headed downstream, which is
  exactly what these twelve are.

## Proposed guard

Add to the audit, as a claim that fails rather than warns:

> for every `cedar_uid` in `cedar_identifier_ledger_final.csv`, the set of
> non-blank `tribe_id` values on its positive rows (tier ≠ X) has exactly one
> member.

Tier-X rows must be excluded from the set, for the same reason gate 4b of
`code/1166_owner_queue_card_builder.py` excludes them: a tier-X row records a
*rejected* candidate. Counting a refusal as a resolution would both hide real
collisions and invent false ones.

**Do not auto-merge.** Each of the twelve needs a decision about which head
survives, and the ANCSA cases are the load-bearing ones: `CE-0005G-S0` (Saxman ∥
Cape Fox Corporation) and `CE-00020-A0` (Fort Yukon ∥ Gana-A'Yoo ∥ K'oyitl'ots'ina)
are the village-government-versus-village-corporation question in its purest form —
the same class as five of the eight cards in the reconciliation, and the same class
the NEST agent independently named. Collapsing them by rule would assert that a
village government and its ANCSA corporation are one legal person, which is false
under 25 U.S.C. §5123 and 43 U.S.C. §1607.

## A related warning that applies to any fix

`AGENTS.md:3977`: **"THE PREFIX DOES NOT IDENTIFY THE CLASS."** `ANVC` spans village
*and* group corporations; `CDFI` spans Native CDFIs *and* Native Financial
Institutions. `41_build_codebooks.py:1338-1340` instructs *"Join to the spine on
this prefix"*, and that instruction is **wrong for 272 entities**.

So a fix must not resolve these twelve by reading `ANVC-` vs `AKNF-` off the front
of the NEID. The prefix is a hint, not a class.
