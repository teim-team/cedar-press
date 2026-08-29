#!/usr/bin/env python3
"""
Cedar Press 168 - link the ADJUDICATION / PROCEEDING family through its HUBS.

WHY
---
Six tables exist BECAUSE a Native entity was party to a proceeding, and almost
none of them carry the entity:

    ferc_docket_filings      81,805 rows      581 linked (1%)
    ferc_ex_parte_parties     4,246 rows        9 linked (0%)
    admin_appeal_parties     20,027 rows      397 linked (2%)
    admin_appeal_decisions   15,613 rows      397 linked (3%)
    foia_request_index        9,481 rows      453 linked (5%)
    resource_revenue         10,482 rows      734 linked (7%)  ceiling 966

The hub is the docket / the appeal. Resolve the PARTY once, propagate along the
hub key, and keep the ROLE - because a non-Native intervenor filing in a
Native-entity docket is not a Native-entity filing.

THE MATCHER
-----------
`33_apply_party_rulings.resolve_entity` is the project's one resolver and this
script imports its primitives (`norm`, `core`, `STRUCTURAL`) rather than
re-implementing them (standing rule 8). It does NOT call `resolve_entity`
directly, because that function's containment tier is the defect documented in
AGENTS.md "THE CONTAINMENT DEFECT" and re-measured here: of the 599 containment
candidates script 144 correctly HELD rather than wrote, the wrong ones include

    Jackson County, Kansas       -> "Jackson"            (place)
    Western Watersheds Project   -> "The NATIVE Project" (one shared token)
    READ & STEVENS, INC.         -> "Stevens Village"    (one shared token)
    SAN JUAN COAL CO.            -> "San Juan"           (trap token)
    Eagle Butte, South Dakota    -> "Eagle"              (trap token + place)

EVERY one of those is DIRECTION 2 - the SPINE name is contained in the RECORD
name. That is the direction where a single shared token carries the whole match,
and it is the direction of every failure recorded in AGENTS.md (CHICKASAW NATION
-> Chickasaw Children's Village; Sequoyah High School -> Sequoyah Fund; every
one of the 148 TDHEs -> its own tribe).

So this script REFUSES direction 2 outright and admits containment only in
DIRECTION 1 - the record name is contained in one of the entity's own OFFICIAL
name variants (canonical, Federal Register official, legal alias). "White
Mountain Apache Tribe" inside "White Mountain Apache Tribe of the Fort Apache
Reservation, Arizona" is the record naming the entity without the FR's
geographic disambiguator. It is not a token coincidence.

Direction 1 additionally requires, all of them:
  - >= 2 core tokens on the record side (one token is never a name)
  - >= 1 identifying token that is neither in NAME_TRAPS nor a US state name
    (so "Modoc Tribe of Oklahoma" does not link on `oklahoma` alone)
  - no NAME_TRAP immediately followed by a PLACE_SUFFIX ("Wichita Falls",
    "Cherokee Falls", "Indian River")
  - HEAD ANCHOR: the record's first identifying token is the variant's first
    identifying token
  - UNIQUENESS across the whole 1,310-entity spine

TIERS
-----
A tier is INHERITED FROM THE SOURCE ROW, NEVER ASSIGNED BY THE CONSUMER.
Therefore this script NEVER writes `confidence_tier` on any row - that column is
the record's own quality and is left byte-identical. Every link it creates
carries its OWN tier in a NEW `*_link_tier` column:

    A  exact / core match on a spine canonical, FR official, or tier-A legal
       alias - the standard script 144 and 133 already published at
    B  match on a tier-B generated alias, head-anchored containment, a
       60-character truncation prefix, or a BARE ONE-WORD string.
       Visible internally, never publishes.

`confidence_tier` therefore still means "how good is this RECORD"; the
`*_link_tier` columns mean "how good is this LINK". Do not conflate them, and
do not read one off the other.

Nothing is propagated at a tier higher than the party link it came from.

WRITES
------
  data/clean/ferc_docket_parties.csv        NEW - the docket-party hub table
  data/clean/ferc_tribal_dockets.csv        + applicant link columns
  data/clean/ferc_docket_filings.csv        + filer link, + docket CONTEXT
  data/clean/ferc_ex_parte_parties.csv      + presenter link
  data/clean/admin_appeal_parties.csv       + org-party link
  data/clean/admin_appeal_decisions.csv     + ROLE-SPLIT native party columns
  data/clean/foia_request_index.csv         + link audit columns
  data/clean/resource_revenue.csv           (ceiling audit; see report)
  review/168_*.csv                          everything refused, with the reason

Every overwritten file is backed up to
<name>.bak_<date>_pre168_link_adjudication_hubs first, and every
write goes to `.part` and is then renamed, so an interruption never looks like a
completion.

Run:      py -3 code/168_link_adjudication_hubs.py
Undo it:  py -3 code/168_link_adjudication_hubs.py --restore
"""

import csv
import importlib.util
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()
SCRIPT = "code/168_link_adjudication_hubs.py"
# The backup tag NAMES THE SCRIPT, not the number. On 2026-08-26 four agents
# ran four different scripts all numbered 163 and all writing
# `.bak_2026-08-26_pre163`; a glob restore then reverted seven files belonging
# to two other agents. See review/_INCIDENT_2026-08-26_script163_number_collision.md.
BAK_TAG = "pre168_link_adjudication_hubs"

csv.field_size_limit(10 ** 9)

sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import NAME_TRAPS, PLACE_SUFFIXES          # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "cedar_party_rulings", CEDAR / "code" / "33_apply_party_rulings.py")
_pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pr)
norm, core, STRUCTURAL = _pr.norm, _pr.core, _pr.STRUCTURAL

# ---------------------------------------------------------------------------
# Vocabulary used only by the residual test. A residual of state names and
# geographic-administrative words is the Federal Register disambiguating an
# entity; a residual carrying an ethnonym or a corporate form is a different
# legal person.
# ---------------------------------------------------------------------------
US_STATES = set("""alabama alaska arizona arkansas california colorado
connecticut delaware florida georgia hawaii idaho illinois indiana iowa kansas
kentucky louisiana maine maryland massachusetts michigan minnesota mississippi
missouri montana nebraska nevada ohio oklahoma oregon pennsylvania tennessee
texas utah vermont virginia washington wisconsin wyoming hampshire jersey
mexico york carolina dakota rhode island new north south east west""".split())

# Strings that are not organisations at all. A match against any of these would
# be a fact about the transcription, not about a party.
NON_PARTY = {
    "", "n/a", "na", "none", "unknown", "not named", "not stated",
    "individual", "individuals", "individual no affiliation",
    "individual (no detailed affiliation given)", "mass mailing",
    "mass mailings", "grouped letters", "ferc staff", "commission staff",
    "u.s. congress", "us congress", "members of congress", "u.s. senate",
    "u.s. senators", "u.s. house", "congress", "public", "general public",
    "confidential", "withheld", "redacted", "et al.", "et al", "estate",
    "unnamed", "various", "multiple", "several",
}

CORP_FORM_RE = re.compile(
    r"\b(inc|inc\.|incorporated|corp|corp\.|corporation|company|co\.|llc|"
    r"l\.l\.c\.|ltd|limited|lp|llp|plc)\b", re.I)

VILLAGE_GOV_RE = re.compile(
    r"^(native village of|village of|native village|traditional village of)\b"
    r"|\b(ira council|traditional council|village council)\b", re.I)

STATE_PAREN_RE = re.compile(r"\s*\((?:[A-Z]{2})(?:\s*[/,]\s*[A-Z]{2})*\)\s*$")
ETAL_RE = re.compile(r",?\s*et\s+al\.?\s*$", re.I)

CORP_CLASSES = {
    "Alaska Native Village Corporation",
    "Alaska Native Regional Corporation",
    "ANCSA Group Corporation",
}

# CROSS-CLASS GUARD. A record that names itself a TRIBE must not land on that
# tribe's college, school, clinic or loan fund. Measured on the first run of
# this script: "Fort Peck Tribes" resolved to *Fort Peck Community College* -
# the same shape as CHICKASAW NATION -> Chickasaw Children's Village ($2.8B on
# a school), and as the rejected script-57 re-run that repointed the
# Confederated Salish and Kootenai Tribes onto `TCU-SLSHKT-00`.
GOVERNMENT_FORM_RE = re.compile(
    r"\b(tribe|tribes|tribal|nation|nations|band|bands|pueblo|rancheria|"
    r"colony|reservation|indians|village|community)\b", re.I)
# ...unless the record says it IS the institution.
INSTITUTION_FORM_RE = re.compile(
    r"\b(college|university|school|schools|academy|institute|fund|"
    r"health|clinic|hospital|center|centre|library|museum|"
    r"credit union|bank|financial|housing authority)\b", re.I)
INSTITUTION_CLASSES = {
    "BIE School",
    "Tribal College or University",
    "Native Community Development Financial Institution",
    "Native Financial Institution",
    "Urban Indian Organization",
}

# TWO GUARDS FOR WHAT `core()` FOLDS AWAY.
#
# AGENTS.md, "`core()` FOLDS AWAY THE WORD THAT DISTINGUISHES": National
# Education Association resolved to National *Indian* Education Association,
# because `indian` was treated as a generic token. Measured AGAIN on the first
# run of this script: FOIA requester organisation "Indian Health" -> *Native*
# Health (Arizona), tier A, because core() reduces both strings to {health}.
#
# The two shapes are different and need different rules. A blanket
# "structural words must agree" rule was tried here and REMOVED because it
# refused "Cow Creek Band of Umpqua" against "Cow Creek Band of Umpqua Tribe of
# Indians" - a legitimate short/long pair. `tribe`, `band`, `indians`, `pueblo`
# and `village` really are interchangeable suffixes in federal filings. The two
# rules below are narrow enough not to touch them.

# RULE 1 - `Indian` and `Native` are ALTERNATIVES, not synonyms, when they are
# the only thing separating two names. Denver *Indian* Health is not *Native*
# Health.
INDIAN_NATIVE_SWAP = ({"indian"}, {"native"})

# RULE 2 - a core made ENTIRELY of sector and administrative words identifies
# nobody. {health}, {project}, {national, education, association}: each of
# those is shared by hundreds of organisations, and the words that distinguish
# them are exactly the ones core() folded. Every term here is a word that, on
# its own, would name a category rather than an entity.
GENERIC_CORE_TOKENS = frozenset("""
health housing services service association associations council councils
center centers centre project projects authority foundation alliance group
groups institute school schools college university fund funds board boards
commission agency office department program programs development resources
resource energy water land lands gaming casino education national first
american america united states enterprise enterprises management consulting
partners systems solutions technologies technology industries business trust
society network coalition committee conference federation union cooperative
district regional area central general public private international
""".split())

# Government classes for the corporate-form guard below.
GOVERNMENT_CLASSES = {
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "State-recognized tribe",
}


def docket_base(s):
    """`CP12-19-000` and `CP12-19` are the same docket; the third segment is the
    subdocket. FR ex parte notices print the full form, eLibrary the short."""
    s = (s or "").strip()
    m = re.match(r"^([A-Z]{0,3}-?\d+(?:-\d+)?)", s)
    return m.group(1) if m else s


def rd(path):
    p = Path(path)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def fieldnames_of(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh))


# The ONLY files this script overwrites. Restoring is done from THIS LIST and
# never from a glob - a glob restores what matches, which is not the same set
# as what you wrote. See review/_INCIDENT_2026-08-26_script163_number_collision.md.
MY_OUTPUTS = [
    "ferc_docket_filings.csv",
    "ferc_tribal_dockets.csv",
    "ferc_ex_parte_parties.csv",
    "admin_appeal_parties.csv",
    "admin_appeal_decisions.csv",
    "foia_request_index.csv",
]


def backup(path):
    path = Path(path)
    if not path.exists():
        return None
    if path.name not in MY_OUTPUTS:
        raise RuntimeError(
            f"refusing to back up {path.name}: it is not in MY_OUTPUTS. "
            "This script writes only the adjudication family.")
    dst = path.with_name(path.name + f".bak_{TODAY}_{BAK_TAG}")
    if not dst.exists():
        dst.write_bytes(path.read_bytes())
    return dst


def restore_my_outputs():
    """Undo this script's own writes, by NAME, never by glob."""
    n = 0
    for name in MY_OUTPUTS:
        bak = CLEAN / f"{name}.bak_{TODAY}_{BAK_TAG}"
        if bak.exists():
            (CLEAN / name).write_bytes(bak.read_bytes())
            print(f"    restored {name}")
            n += 1
    print(f"  restored {n} file(s) from {BAK_TAG}")


def write_csv(path, rows, fields):
    """`.part` then rename - an interruption must not look like a completion."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    os.replace(part, path)
    print(f"    wrote {path.relative_to(CEDAR)}  ({len(rows):,} rows)")


# ---------------------------------------------------------------------------
# THE NAME INDEX
# ---------------------------------------------------------------------------

class SpineIndex:
    """Name -> entity, with the strength of the name it matched on.

    strength 1  the entity's own canonical / FR official / tier-A legal alias
    strength 2  a tier-B alias (`full_form_federal_filing`, generated, folded)
    """

    def __init__(self, spine, aliases):
        self.by_id = {r["tribe_id"]: r for r in spine}
        self.variants = {}                    # eid -> {normalised name: strength}
        for r in spine:
            self._add(r["tribe_id"], r["canonical_name"], 1)
            if (r.get("fr_official_name") or "").strip():
                self._add(r["tribe_id"], r["fr_official_name"], 1)
            for a in (r.get("aliases") or "").split("|"):
                if a.strip():
                    self._add(r["tribe_id"], a, 1)
        for a in aliases:
            eid = a.get("entity_id", "")
            if eid in self.by_id and (a.get("alias_name") or "").strip():
                self._add(eid, a["alias_name"], 1 if a.get("tier") == "A" else 2)

        self.exact = {}                       # norm name -> {eid: strength}
        self.core = {}                        # frozenset core -> {eid: strength}
        for eid, vs in self.variants.items():
            for n, st in vs.items():
                self.exact.setdefault(n, {})
                self.exact[n][eid] = min(st, self.exact[n].get(eid, 9))
                c = core(n)
                if c:
                    self.core.setdefault(c, {})
                    self.core[c][eid] = min(st, self.core[c].get(eid, 9))

        # Pre-compute per-variant core + head token for the containment pass.
        self.variant_rows = []                # (eid, strength, core, head)
        for eid, vs in self.variants.items():
            for n, st in vs.items():
                c = core(n)
                if len(c) < 2:
                    continue
                head = self._head(n)
                if head:
                    self.variant_rows.append((eid, st, c, head, n))

    def _add(self, eid, name, strength):
        n = norm(name)
        if not n:
            return
        d = self.variants.setdefault(eid, {})
        if n not in d or strength < d[n]:
            d[n] = strength

    @staticmethod
    def _head(normalised):
        for t in normalised.split():
            if t not in STRUCTURAL:
                return t
        return None

    # -- guards ----------------------------------------------------------
    @staticmethod
    def _place_suffix_trap(name):
        toks = norm(name).split()
        for i, t in enumerate(toks[:-1]):
            if t in NAME_TRAPS and toks[i + 1] in PLACE_SUFFIXES:
                return True
        return False

    @staticmethod
    def _identity_residual(variant_norm, record_words):
        """True when the spine variant carries an identity-bearing `Indian` /
        `Native` that the record does not, AND it is not part of a place name.

        `Indian` in the Federal Register's official names is usually GEOGRAPHY -
        "Rosebud Sioux Tribe of the Rosebud **Indian Reservation**", "Lovelock
        Paiute Tribe of the Lovelock **Indian Colony**". Blocking on those cost
        7 correct appeal-party links when this guard was first written, so the
        test is on the word that FOLLOWS: `Indian Reservation` is a place,
        `Indian Health` and `Indian Education` are the organisation's identity.
        """
        toks = variant_norm.split()
        for i, t in enumerate(toks):
            if t not in ("indian", "native") or t in record_words:
                continue
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            if nxt in ("reservation", "colony", "allotment", "allotments",
                       "township", "reserve", "lands", "land"):
                continue                      # geography, not identity
            return True
        return False

    def _disambiguate(self, name, hits):
        """One narrow, documented tie-break, applied to nothing else.

        AGENTS.md: where an Alaska village GOVERNMENT and its ANCSA CORPORATION
        both carry the same name, a CORPORATE-form record belongs to the
        corporation ("Ukpeagvik Inupiat Corporation" is not the Native Village
        of Barrow). Everything else ambiguous is refused.
        """
        if len(hits) == 1:
            return next(iter(hits))
        if CORP_FORM_RE.search(name or ""):
            corps = [e for e in hits
                     if self.by_id[e]["entity_class"] in CORP_CLASSES]
            if len(corps) == 1:
                return corps[0]
        # ...and its mirror. "Native Village of Elim" and "Elim Native
        # Corporation" normalise to two different strings but collide on the
        # spine; a record written in GOVERNMENT form is the village government.
        if VILLAGE_GOV_RE.search(name or ""):
            govs = [e for e in hits
                    if self.by_id[e]["entity_class"]
                    == "Federally recognized Alaska Native Village"]
            if len(govs) == 1:
                return govs[0]
        return None

    # -- the matcher -----------------------------------------------------
    def match(self, raw, allow_truncation_prefix=False):
        """-> (entity_id, method, strength, refusal_reason)."""
        name = ETAL_RE.sub("", STATE_PAREN_RE.sub("", (raw or "").strip())).strip(" ,;-")
        if not name or name.lower() in NON_PARTY:
            return None, None, None, "not_a_party_string"

        n = norm(name)
        if not n:
            return None, None, None, "blank_after_normalisation"

        c = core(n)
        rec_struct = {t for t in n.split() if t in STRUCTURAL}

        def identity_word_guard(eid):
            """True to REFUSE. Two narrow rules, both measured; see the comment
            block on GENERIC_CORE_TOKENS.

            RULE 2 first because it is the general one: if the shared core is
            made only of sector words, the match rests on nothing.
            RULE 1: an `Indian` / `Native` swap between two otherwise identical
            names is a different organisation, never a spelling variant.
            """
            if c and c <= GENERIC_CORE_TOKENS:
                return True
            a, b = INDIAN_NATIVE_SWAP
            rec_side = ((rec_struct & a and "i") or "") + \
                       ((rec_struct & b and "n") or "")
            for vn in self.variants[eid]:
                if core(vn) != c:
                    continue
                vs = {t for t in vn.split() if t in STRUCTURAL}
                v_side = ((vs & a and "i") or "") + ((vs & b and "n") or "")
                if not (rec_side and v_side and rec_side != v_side):
                    return False          # at least one variant is compatible
            return True

        def corp_form_guard(eid):
            """True to REFUSE: a corporate-form record resolving to a tribal or
            village GOVERNMENT on a SINGLE identifying token. "Robinson LLP" is
            not Robinson Rancheria. A tribe DOES own companies directly
            (Chickasaw Management Services, Tohono O'odham Utility Authority) -
            those carry two or more identifying tokens and are unaffected."""
            return (len(c) < 2
                    and bool(CORP_FORM_RE.search(name))
                    and self.by_id[eid]["entity_class"] in GOVERNMENT_CLASSES)

        hits = self.exact.get(n)
        if hits:
            eid = self._disambiguate(name, list(hits))
            if eid and identity_word_guard(eid):
                return None, None, None, "identity_structural_word_differs"
            if eid and corp_form_guard(eid):
                return None, None, None, "corp_form_single_token_vs_government"
            if eid:
                # Take the BEST-evidenced name this entity carries, not the
                # first path that hit. "Chickasaw Nation" is a GENERATED tier-B
                # alias of "The Chickasaw Nation", whose core is identical and
                # tier A - reporting B there would understate a match the spine
                # canonical itself supports.
                st = min(hits[eid], (self.core.get(c) or {}).get(eid, 9))
                # A BARE ONE-WORD STRING IS NEVER A NAME. "Georgetown",
                # "Enterprise", "Jackson" and "Seneca" are all spine canonical
                # names AND ordinary American place / English words. Measured:
                # 94 FOIA rows key to the Native Village of Georgetown, Alaska
                # off `georgetown.edu` in a list of email domains to search.
                # "Yurok Tribe" is two words and is not this case - the test is
                # on the RAW token count, not the core, because the structural
                # word is exactly what says an entity is meant.
                if len(n.split()) < 2:
                    return eid, "exact_name_single_token", max(st, 2), None
                return eid, "exact_name", st, None
            return None, None, None, f"ambiguous_exact:{len(hits)}"

        if not c:
            return None, None, None, "all_structural_tokens"

        hits = self.core.get(c)
        if hits:
            eid = self._disambiguate(name, list(hits))
            if eid and identity_word_guard(eid):
                return None, None, None, "identity_structural_word_differs"
            if eid and corp_form_guard(eid):
                return None, None, None, "corp_form_single_token_vs_government"
            if eid:
                st = hits[eid]
                if len(n.split()) < 2:
                    return eid, "core_name_single_token", max(st, 2), None
                return eid, "core_name", st, None
            return None, None, None, f"ambiguous_core:{len(hits)}"

        # --- guards before any inexact path --------------------------------
        if self._place_suffix_trap(name):
            return None, None, None, "place_suffix_trap"
        if len(c) < 2:
            return None, None, None, "single_token_name"
        identifying = {t for t in c if t not in NAME_TRAPS and t not in US_STATES}
        if not identifying:
            return None, None, None, "only_trap_or_state_tokens"
        if c <= GENERIC_CORE_TOKENS:
            return None, None, None, "generic_core_only"

        head = self._head(n)
        if head is None:
            return None, None, None, "no_head_token"

        # --- DIRECTION 1 CONTAINMENT, head-anchored ------------------------
        # The cross-class guard applies ONLY on the inexact paths. A record
        # calling itself a tribe/nation/band, and NOT calling itself a college
        # or a clinic, may not land on a school, TCU, CDFI or UIO on a partial
        # name. "Fort Peck Tribes" -> Fort Peck Community College is what this
        # refuses; an exact or core-equal match is left alone, because there
        # the whole name agreed.
        refuse_institutions = (GOVERNMENT_FORM_RE.search(name)
                               and not INSTITUTION_FORM_RE.search(name))
        # The identity-word rule, on the containment path. Here the residual is
        # whatever the spine variant has and the record does not, so `indian` or
        # `native` sitting in that residual is the NEA -> National *Indian*
        # Education Association shape again. Measured on run 2 of this script:
        # FOIA requester "Urban Institute" -> *Urban Indian Health Institute*.
        # The Urban Institute is a Washington DC think tank.
        rec_words = set(n.split())
        rec_has_identity = bool(rec_words & (INDIAN_NATIVE_SWAP[0]
                                             | INDIAN_NATIVE_SWAP[1]))
        cands = {}
        blocked_class = blocked_identity = 0
        for eid, st, vc, vhead, vn in self.variant_rows:
            if vhead != head:
                continue
            if not (c < vc):
                continue
            if (refuse_institutions
                    and self.by_id[eid]["entity_class"] in INSTITUTION_CLASSES):
                blocked_class += 1
                continue
            if not rec_has_identity and self._identity_residual(vn, rec_words):
                blocked_identity += 1
                continue
            cands[eid] = min(st, cands.get(eid, 9))
        if not cands and blocked_identity:
            return None, None, None, "identity_word_only_on_the_spine_side"
        if not cands and blocked_class:
            return None, None, None, "cross_class_guard:government_form_vs_institution"
        if len(cands) == 1:
            eid = next(iter(cands))
            return eid, "official_name_containment", max(2, cands[eid]), None
        if len(cands) > 1:
            eid = self._disambiguate(name, list(cands))
            if eid:
                return eid, "official_name_containment", 2, None
            return None, None, None, f"ambiguous_containment:{len(cands)}"

        # --- 60-CHARACTER TRUNCATION ---------------------------------------
        # FERC's filer field truncates at exactly 60 characters (33 distinct
        # names sit at 60, one at 61, and the 60-char ones end mid-word:
        # "...WARM SPRINGS RESERVATION OF OREGO"). A strict word-prefix of a
        # single spine variant recovers those without guessing.
        if allow_truncation_prefix and len(raw.strip()) >= 55:
            pcands = {}
            for eid, st, vc, vhead, vn in self.variant_rows:
                if vhead != head:
                    continue
                if (refuse_institutions
                        and self.by_id[eid]["entity_class"] in INSTITUTION_CLASSES):
                    continue
                if vn.startswith(n) and len(vn) > len(n):
                    pcands[eid] = min(st, pcands.get(eid, 9))
            if len(pcands) == 1:
                eid = next(iter(pcands))
                return eid, "truncation_prefix", 2, None
            if len(pcands) > 1:
                return None, None, None, f"ambiguous_truncation:{len(pcands)}"

        return None, None, None, "no_spine_match"

    def name_of(self, eid):
        return self.by_id[eid]["canonical_name"] if eid else ""

    def class_of(self, eid):
        return self.by_id[eid]["entity_class"] if eid else ""


TIER_OF_STRENGTH = {1: "A", 2: "B"}

# Methods this script writes. A link carrying one of these is OURS, so if a
# later run's guards refuse it, it must be WITHDRAWN rather than left standing -
# otherwise a fixed guard only stops new bad links and leaves the old ones.
# A link written by any OTHER method belongs to another script and is honoured.
MY_METHODS = frozenset({
    "exact_name", "exact_name_single_token", "core_name",
    "core_name_single_token", "official_name_containment", "truncation_prefix",
})


# ---------------------------------------------------------------------------
def resolve_distinct(idx, names, allow_trunc=False):
    """Resolve a set of distinct name strings once. -> dict name -> result."""
    out = {}
    for nm in names:
        eid, method, strength, why = idx.match(nm, allow_truncation_prefix=allow_trunc)
        out[nm] = {
            "entity_id": eid or "",
            "entity_name": idx.name_of(eid),
            "entity_class": idx.class_of(eid),
            "method": method or "",
            "tier": TIER_OF_STRENGTH.get(strength, "") if eid else "",
            "refusal": why or "",
        }
    return out


def review_rows(resolved, counts, context):
    rows = []
    for nm, r in sorted(resolved.items()):
        if r["entity_id"]:
            continue
        if r["refusal"] in ("not_a_party_string", "blank_after_normalisation",
                            "all_structural_tokens"):
            continue
        rows.append({
            "context": context,
            "party_name_as_recorded": nm,
            "rows_affected": counts.get(nm, 0),
            "refusal_reason": r["refusal"],
            "proposed_entity_id": "",
            "proposed_entity_name": "",
            "YOUR_RULING": "",
            "staged_date": TODAY,
            "staged_by_script": SCRIPT,
        })
    rows.sort(key=lambda r: (-r["rows_affected"], r["party_name_as_recorded"]))
    return rows


REVIEW_FIELDS = ["context", "party_name_as_recorded", "rows_affected",
                 "refusal_reason", "proposed_entity_id", "proposed_entity_name",
                 "YOUR_RULING", "staged_date", "staged_by_script"]


# ===========================================================================
def main():
    print("=== Cedar Press 168: link the adjudication family through its hubs ===\n")
    report = {"script": SCRIPT, "run_date": TODAY, "tables": {}}

    spine = rd(CEDAR / "data" / "spine" / "cedar_entity_spine.csv")
    aliases = rd(CLEAN / "entity_aliases.csv")
    idx = SpineIndex(spine, aliases)
    print(f"  spine {len(spine):,} entities  |  aliases {len(aliases):,}  |  "
          f"{len(idx.exact):,} distinct normalised name variants\n")

    # -- honour existing rulings ------------------------------------------
    rulings = rd(CLEAN / "cross_dataset_ruling_map.csv")
    blocked_note_names = {
        norm(r["note"]) for r in rulings
        if r["ruling"].startswith("BLOCKED") and (r.get("note") or "").strip()
    }
    blocked_note_names.discard("")
    print(f"  cross_dataset_ruling_map: {len(rulings):,} rows, "
          f"{sum(1 for r in rulings if r['ruling'].startswith('BLOCKED')):,} BLOCKED\n"
          f"    (keyed on EIN/UEI/CAGE only - none of these six tables carry a\n"
          f"     registry identifier, so no ruling is re-litigated by name here)\n")

    # =====================================================================
    # 1. FERC - the DOCKET is the hub
    # =====================================================================
    print("[1] FERC ------------------------------------------------------")
    dockets = rd(CLEAN / "ferc_tribal_dockets.csv")
    filings = rd(CLEAN / "ferc_docket_filings.csv")
    before_filings = sum(1 for r in filings if r["resolved_native_entity_id"].strip())
    # `ferc_docket_filings.csv` is REBUILT by 133 while this runs (81,805 ->
    # 102,615 rows on 2026-08-26 when four new dockets were fetched), so
    # `before_filings` is not a stable baseline across runs. Read the untouched
    # pre-168 backup where one exists and report both, rather than quoting a
    # "before" that moved for a reason that has nothing to do with linkage.
    snaps = []
    for cand in sorted(CLEAN.glob("ferc_docket_filings.csv.bak_*")):
        b = rd(cand)
        snaps.append(f"{cand.name.split('.bak_')[-1]}: {len(b):,} rows / "
                     f"{sum(1 for r in b if r['resolved_native_entity_id'].strip()):,} linked")
    baseline_note = (
        "code/133_build_ferc_advocacy.py rebuilt this file while 168 was in "
        "flight, so the row count moved for a reason that has nothing to do "
        "with linkage. Every snapshot on disk, so the before/after can be read "
        "against the right one: " + " | ".join(snaps))

    # 1a. the docket applicant / licensee
    app_names = {r["applicant_or_licensee_as_recorded"].strip() for r in dockets}
    app_names.discard("")
    app_res = resolve_distinct(idx, app_names)
    app_counts = {}
    for r in dockets:
        k = r["applicant_or_licensee_as_recorded"].strip()
        app_counts[k] = app_counts.get(k, 0) + 1

    # 1b. the filers
    filer_names = {r["filer_organization_as_recorded"].strip() for r in filings}
    filer_names.discard("")
    filer_counts = {}
    for r in filings:
        k = r["filer_organization_as_recorded"].strip()
        filer_counts[k] = filer_counts.get(k, 0) + 1
    filer_res = resolve_distinct(idx, filer_names, allow_trunc=True)
    n_filer_named = sum(1 for v in filer_res.values() if v["entity_id"])
    print(f"  distinct filer organisations : {len(filer_names):,}  "
          f"-> {n_filer_named} resolve")
    print(f"  distinct docket applicants   : {len(app_names):,}  "
          f"-> {sum(1 for v in app_res.values() if v['entity_id'])} resolve")

    # 1c. THE HUB TABLE - one row per (docket, party, role).
    hub = []
    seen = set()
    for r in dockets:
        nm = r["applicant_or_licensee_as_recorded"].strip()
        res = app_res.get(nm, {})
        key = (r["docket_number"], norm(nm), "APPLICANT_OR_LICENSEE")
        if nm and key not in seen:
            seen.add(key)
            hub.append({
                "ferc_docket_party_id": f"FDP-{len(hub) + 1:06d}",
                "docket_number": r["docket_number"],
                "subdocket": r.get("subdocket", ""),
                "docket_program": r.get("docket_program", ""),
                "party_name_as_recorded": nm,
                "party_role": "APPLICANT_OR_LICENSEE",
                "party_role_basis": ("ferc_tribal_dockets."
                                     "applicant_or_licensee_as_recorded"),
                "n_filings_by_this_party_on_docket": "",
                "resolved_native_entity_id": res.get("entity_id", ""),
                "resolved_native_entity_name": res.get("entity_name", ""),
                "resolved_native_entity_class": res.get("entity_class", ""),
                "entity_link_method": res.get("method", ""),
                "entity_link_tier": res.get("tier", ""),
                "entity_link_refusal_reason": res.get("refusal", ""),
                "source_url": r.get("source_url", ""),
                "built_date": TODAY,
                "built_by_script": SCRIPT,
            })
    per_docket_filer = {}
    for r in filings:
        nm = r["filer_organization_as_recorded"].strip()
        if not nm:
            continue
        per_docket_filer[(r["docket_number"], nm)] = \
            per_docket_filer.get((r["docket_number"], nm), 0) + 1
    dk_meta = {r["docket_number"]: r for r in dockets}
    for (dno, nm), n in sorted(per_docket_filer.items()):
        res = filer_res.get(nm, {})
        key = (dno, norm(nm), "APPLICANT_OR_LICENSEE")
        role = "APPLICANT_AND_FILER" if key in seen else "FILER"
        m = dk_meta.get(dno, {})
        hub.append({
            "ferc_docket_party_id": f"FDP-{len(hub) + 1:06d}",
            "docket_number": dno,
            "subdocket": m.get("subdocket", ""),
            "docket_program": m.get("docket_program", ""),
            "party_name_as_recorded": nm,
            "party_role": role,
            "party_role_basis": "ferc_docket_filings.filer_organization_as_recorded",
            "n_filings_by_this_party_on_docket": n,
            "resolved_native_entity_id": res.get("entity_id", ""),
            "resolved_native_entity_name": res.get("entity_name", ""),
            "resolved_native_entity_class": res.get("entity_class", ""),
            "entity_link_method": res.get("method", ""),
            "entity_link_tier": res.get("tier", ""),
            "entity_link_refusal_reason": res.get("refusal", ""),
            "source_url": m.get("source_url", ""),
            "built_date": TODAY,
            "built_by_script": SCRIPT,
        })
    hub_fields = list(hub[0].keys())
    write_csv(CLEAN / "ferc_docket_parties.csv", hub, hub_fields)
    print(f"  hub table: {len(hub):,} docket-party rows, "
          f"{sum(1 for h in hub if h['resolved_native_entity_id']):,} resolved")

    # 1d. docket CONTEXT - carried as its own columns, never flattened onto
    #     the filing's own filer link.
    ctx = {}
    for h in hub:
        if not h["resolved_native_entity_id"]:
            continue
        d = ctx.setdefault(docket_base(h["docket_number"]),
                           {"ids": [], "names": [], "roles": []})
        if h["resolved_native_entity_id"] not in d["ids"]:
            d["ids"].append(h["resolved_native_entity_id"])
            d["names"].append(h["resolved_native_entity_name"])
            d["roles"].append(h["party_role"])

    # 1e. filings
    new_cols = ["party_role", "filer_entity_link_method", "filer_entity_link_tier",
                "filer_entity_link_refusal_reason", "docket_native_party_ids",
                "docket_native_party_names", "docket_native_party_roles",
                "docket_has_native_party", "entity_link_built_by_script"]
    withdrawn = 0
    for r in filings:
        nm = r["filer_organization_as_recorded"].strip()
        res = filer_res.get(nm, {})
        eid = res.get("entity_id", "")
        d = ctx.get(docket_base(r["docket_number"]))
        if eid and not r["resolved_native_entity_id"].strip():
            r["resolved_native_entity_id"] = eid
            r["resolved_native_entity_name"] = res["entity_name"]
            r["resolution_method"] = res["method"]
            r["filer_is_tribal_entity"] = "1"
            r["filer_entity_link_tier"] = res["tier"]
            r["entity_link_built_by_script"] = SCRIPT
        elif r["resolution_method"] in MY_METHODS:
            # OUR OWN link from an earlier run. Re-derive it, so that a guard
            # added since then WITHDRAWS the bad link instead of only stopping
            # new ones. A fixed guard that leaves the damage in place is not a
            # fix.
            if eid:
                r["resolved_native_entity_id"] = eid
                r["resolved_native_entity_name"] = res["entity_name"]
                r["resolution_method"] = res["method"]
                r["filer_entity_link_tier"] = res["tier"]
            else:
                withdrawn += 1
                r["resolved_native_entity_id"] = ""
                r["resolved_native_entity_name"] = ""
                r["resolution_method"] = ""
                r["filer_is_tribal_entity"] = "0"
                r["filer_entity_link_tier"] = ""
                r["filer_entity_link_refusal_reason"] = (
                    "withdrawn_by_a_later_guard: " + res.get("refusal", ""))
            r["entity_link_built_by_script"] = SCRIPT
        elif r["resolved_native_entity_id"].strip():
            # Someone else's link (script 133's `fr_official_name`,
            # `government_class_core`, `name_head`, ...). HONOURED, never
            # re-litigated; it publishes at the tier its own build gave it.
            r["filer_entity_link_tier"] = r.get("filer_entity_link_tier") or "A"
        else:
            r["filer_entity_link_tier"] = ""
            r["filer_entity_link_refusal_reason"] = res.get("refusal", "")
        r["filer_entity_link_method"] = r["resolution_method"]
        r["party_role"] = ("FILER_IS_NATIVE_ENTITY"
                           if r["resolved_native_entity_id"].strip()
                           else "FILER_NOT_A_NATIVE_ENTITY")
        r["docket_native_party_ids"] = "|".join(d["ids"]) if d else ""
        r["docket_native_party_names"] = "|".join(d["names"]) if d else ""
        r["docket_native_party_roles"] = "|".join(d["roles"]) if d else ""
        r["docket_has_native_party"] = "1" if d else "0"
        r.setdefault("entity_link_built_by_script", "")

    after_filings = sum(1 for r in filings if r["resolved_native_entity_id"].strip())
    ff = fieldnames_of(CLEAN / "ferc_docket_filings.csv")
    ff = ff + [c for c in new_cols if c not in ff]
    backup(CLEAN / "ferc_docket_filings.csv")
    write_csv(CLEAN / "ferc_docket_filings.csv", filings, ff)
    print(f"  filings linked : {before_filings:,} -> {after_filings:,}"
          + (f"   ({withdrawn:,} of OUR earlier links withdrawn by a new guard)"
             if withdrawn else ""))
    print(f"  filings on a docket WITH a Native party but filed by someone else: "
          f"{sum(1 for r in filings if r['docket_has_native_party'] == '1' and r['party_role'] == 'FILER_NOT_A_NATIVE_ENTITY'):,}"
          "  (role kept distinct, NOT linked)")
    report["tables"]["ferc_docket_filings"] = {
        "rows": len(filings), "linked_before": before_filings,
        "linked_after": after_filings,
        "distinct_filer_orgs": len(filer_names),
        "distinct_filer_orgs_resolved": n_filer_named,
        "filings_on_native_docket_by_other_filer": sum(
            1 for r in filings if r["docket_has_native_party"] == "1"
            and r["party_role"] == "FILER_NOT_A_NATIVE_ENTITY"),
        "baseline_note": baseline_note,
    }

    # 1f. dockets
    dnew = ["applicant_resolved_native_entity_id",
            "applicant_resolved_native_entity_name",
            "applicant_entity_link_method", "applicant_entity_link_tier",
            "applicant_entity_link_refusal_reason",
            "docket_native_party_ids", "docket_native_party_names",
            "docket_native_party_roles", "docket_native_party_count",
            "entity_link_built_by_script"]
    for r in dockets:
        res = app_res.get(r["applicant_or_licensee_as_recorded"].strip(), {})
        r["applicant_resolved_native_entity_id"] = res.get("entity_id", "")
        r["applicant_resolved_native_entity_name"] = res.get("entity_name", "")
        r["applicant_entity_link_method"] = res.get("method", "")
        r["applicant_entity_link_tier"] = res.get("tier", "")
        r["applicant_entity_link_refusal_reason"] = (
            "" if res.get("entity_id") else res.get("refusal", ""))
        d = ctx.get(docket_base(r["docket_number"]))
        r["docket_native_party_ids"] = "|".join(d["ids"]) if d else ""
        r["docket_native_party_names"] = "|".join(d["names"]) if d else ""
        r["docket_native_party_roles"] = "|".join(d["roles"]) if d else ""
        r["docket_native_party_count"] = len(d["ids"]) if d else 0
        r["entity_link_built_by_script"] = SCRIPT
    df = fieldnames_of(CLEAN / "ferc_tribal_dockets.csv")
    df = df + [c for c in dnew if c not in df]
    backup(CLEAN / "ferc_tribal_dockets.csv")
    write_csv(CLEAN / "ferc_tribal_dockets.csv", dockets, df)
    n_dk = sum(1 for r in dockets if r["docket_native_party_count"])
    print(f"  dockets with >=1 resolved Native party: {n_dk} of {len(dockets)}")
    report["tables"]["ferc_tribal_dockets"] = {
        "rows": len(dockets),
        "applicant_linked": sum(1 for r in dockets
                                if r["applicant_resolved_native_entity_id"]),
        "dockets_with_native_party": n_dk,
    }

    rv = review_rows(filer_res, filer_counts, "ferc_filer_organization")
    rv += review_rows(app_res, app_counts, "ferc_docket_applicant")
    write_csv(REVIEW / f"168_ferc_unresolved_parties_{TODAY}.csv", rv, REVIEW_FIELDS)

    # 1g. ex parte presenters
    print("\n[1b] FERC ex parte -------------------------------------------")
    ex = rd(CLEAN / "ferc_ex_parte_parties.csv")
    ex_before = sum(1 for r in ex if r["resolved_native_entity_id"].strip())
    # A row flagged as possibly a natural person is NOT resolved to an
    # organisation. Cedar Press publishes no datasets about private individuals.
    ex_names, ex_counts = set(), {}
    for r in ex:
        nm = r["presenter_or_requester_as_printed"].strip()
        if not nm:
            continue
        ex_counts[nm] = ex_counts.get(nm, 0) + 1
        ex_names.add(nm)
    ex_res = resolve_distinct(idx, ex_names)
    for r in ex:
        nm = r["presenter_or_requester_as_printed"].strip()
        res = ex_res.get(nm, {})
        r["party_role"] = "EX_PARTE_PRESENTER_OR_REQUESTER"
        r["party_role_basis"] = ("FR ex parte notice table: this party made or "
                                 "requested the communication")
        # HUB CONTEXT, kept in its own columns. The presenter is one party; the
        # docket's Native parties are others. A tribe being a party to the
        # docket does not make the ex parte communication the tribe's.
        d = ctx.get(docket_base(r.get("primary_docket_number", "")))
        r["docket_native_party_ids"] = "|".join(d["ids"]) if d else ""
        r["docket_native_party_names"] = "|".join(d["names"]) if d else ""
        r["docket_has_native_party"] = "1" if d else "0"
        if res.get("entity_id") and not r["resolved_native_entity_id"].strip():
            r["resolved_native_entity_id"] = res["entity_id"]
            r["resolved_native_entity_name"] = res["entity_name"]
            r["resolution_method"] = res["method"]
            r["entity_link_tier"] = res["tier"]
            r["entity_link_built_by_script"] = SCRIPT
        elif r["resolved_native_entity_id"].strip():
            r["entity_link_tier"] = r.get("entity_link_tier") or "A"
        else:
            r["entity_link_tier"] = ""
            r["entity_link_refusal_reason"] = res.get("refusal", "")
        r.setdefault("entity_link_refusal_reason", "")
        r.setdefault("entity_link_built_by_script", "")
    ex_after = sum(1 for r in ex if r["resolved_native_entity_id"].strip())
    exf = fieldnames_of(CLEAN / "ferc_ex_parte_parties.csv")
    for c in ["party_role", "party_role_basis", "entity_link_tier",
              "entity_link_refusal_reason", "docket_native_party_ids",
              "docket_native_party_names", "docket_has_native_party",
              "entity_link_built_by_script"]:
        if c not in exf:
            exf.append(c)
    backup(CLEAN / "ferc_ex_parte_parties.csv")
    write_csv(CLEAN / "ferc_ex_parte_parties.csv", ex, exf)
    print(f"  ex parte parties linked: {ex_before} -> {ex_after}")
    report["tables"]["ferc_ex_parte_parties"] = {
        "rows": len(ex), "linked_before": ex_before, "linked_after": ex_after}
    write_csv(REVIEW / f"168_ferc_ex_parte_unresolved_{TODAY}.csv",
              review_rows(ex_res, ex_counts, "ferc_ex_parte_presenter"),
              REVIEW_FIELDS)

    # =====================================================================
    # 2. ADMIN APPEALS - the APPEAL is the hub, parties hang off it
    # =====================================================================
    print("\n[2] IBIA / IBLA ----------------------------------------------")
    parties = rd(CLEAN / "admin_appeal_parties.csv")
    decisions = rd(CLEAN / "admin_appeal_decisions.csv")
    p_before = sum(1 for r in parties if r["resolved_entity_id"].strip())
    d_before = sum(1 for r in decisions if r["native_entity_ids"].strip())

    # ONLY organisation-typed parties. A NATURAL_PERSON is never an entity; an
    # AGENCY_OFFICIAL ("Navajo Area Director") is a BIA officer, not the tribe;
    # an ESTATE is a probate subject.
    ORG_TYPES = {"ORGANISATION", "BUSINESS_DBA"}
    p_names, p_counts = set(), {}
    for r in parties:
        if r["party_type"] not in ORG_TYPES:
            continue
        nm = r["party_name"].strip()
        if not nm:
            continue
        p_names.add(nm)
        p_counts[nm] = p_counts.get(nm, 0) + 1
    p_res = resolve_distinct(idx, p_names)
    print(f"  organisation-typed parties: "
          f"{sum(1 for r in parties if r['party_type'] in ORG_TYPES):,} rows, "
          f"{len(p_names):,} distinct names -> "
          f"{sum(1 for v in p_res.values() if v['entity_id']):,} resolve")

    held_confirmed = held_refused = 0
    for r in parties:
        r.setdefault("entity_link_tier", "")
        r.setdefault("entity_link_refusal_reason", "")
        r.setdefault("entity_link_built_by_script", "")
        r["party_caption_names_additional_parties"] = (
            "Y" if ETAL_RE.search(r["party_name"]) else "N")
        if r["party_type"] not in ORG_TYPES:
            r["entity_link_refusal_reason"] = f"party_type={r['party_type']}"
            continue
        res = p_res.get(r["party_name"].strip(), {})
        held = r.get("entity_link_held_candidate_id", "").strip()
        # "THE HOPI TRIBE ET AL" names Hopi AND parties the caption does not
        # list. The link to Hopi is correct; the claim "this appeal had one
        # Native party" would not be. 1,536 party rows carry `et al` and the
        # upstream `compound_party_caption` is N on every one of them, so this
        # is recorded in its own column rather than by overwriting theirs.
        if r["resolved_entity_id"].strip() and r["resolve_method"] in MY_METHODS:
            # ours from an earlier run - re-derive so a new guard withdraws it
            if not res.get("entity_id"):
                r["resolved_entity_id"] = ""
                r["resolved_entity_name"] = ""
                r["resolve_method"] = ""
                r["entity_link_tier"] = ""
                r["entity_link_refusal_reason"] = (
                    "withdrawn_by_a_later_guard: " + res.get("refusal", ""))
                continue
            r["resolved_entity_id"] = res["entity_id"]
            r["resolved_entity_name"] = res["entity_name"]
            r["resolve_method"] = res["method"]
            r["entity_link_tier"] = res["tier"]
            continue
        if r["resolved_entity_id"].strip():
            # script 144's `exact` / `core` / `alias` - honoured, not re-litigated
            r["entity_link_tier"] = r["entity_link_tier"] or "A"
            continue
        if res.get("entity_id"):
            r["resolved_entity_id"] = res["entity_id"]
            r["resolved_entity_name"] = res["entity_name"]
            r["resolve_method"] = res["method"]
            r["entity_link_tier"] = res["tier"]
            r["entity_link_built_by_script"] = SCRIPT
            if held:
                if held == res["entity_id"]:
                    held_confirmed += 1
                else:
                    held_refused += 1
        else:
            r["entity_link_refusal_reason"] = res.get("refusal", "")
            if held:
                held_refused += 1
    p_after = sum(1 for r in parties if r["resolved_entity_id"].strip())
    print(f"  parties linked: {p_before:,} -> {p_after:,}")
    print(f"  of the 599 containment candidates script 144 HELD: "
          f"{held_confirmed} independently confirmed, "
          f"{held_refused} still refused (stay held, staged to review)")

    pf = fieldnames_of(CLEAN / "admin_appeal_parties.csv")
    for c in ["entity_link_tier", "entity_link_refusal_reason",
              "party_caption_names_additional_parties",
              "entity_link_built_by_script"]:
        if c not in pf:
            pf.append(c)
    backup(CLEAN / "admin_appeal_parties.csv")
    write_csv(CLEAN / "admin_appeal_parties.csv", parties, pf)

    # propagate to decisions, ROLE-SPLIT
    ROLE_COL = {"APPELLANT": "appellant", "PETITIONER": "petitioner",
                "APPELLEE": "appellee", "ESTATE_SUBJECT": "estate_subject"}
    agg = {}
    for r in parties:
        if not r["resolved_entity_id"].strip():
            continue
        slot = ROLE_COL.get(r["party_role"], "other_party")
        d = agg.setdefault(r["decision_id"], {})
        s = d.setdefault(slot, {"ids": [], "names": [], "tiers": []})
        if r["resolved_entity_id"] not in s["ids"]:
            s["ids"].append(r["resolved_entity_id"])
            s["names"].append(r["resolved_entity_name"])
            s["tiers"].append(r.get("entity_link_tier", ""))

    dcols = []
    for slot in ["appellant", "appellee", "petitioner", "estate_subject",
                 "other_party"]:
        dcols += [f"native_{slot}_entity_ids", f"native_{slot}_entity_names"]
    dcols += ["native_party_entity_ids_all", "native_party_entity_names_all",
              "native_party_roles_all", "native_entity_link_tier",
              "n_native_parties", "entity_link_built_by_script"]

    for r in decisions:
        d = agg.get(r["decision_id"], {})
        all_ids, all_names, all_roles, all_tiers = [], [], [], []
        for slot in ["appellant", "appellee", "petitioner", "estate_subject",
                     "other_party"]:
            s = d.get(slot)
            r[f"native_{slot}_entity_ids"] = "|".join(s["ids"]) if s else ""
            r[f"native_{slot}_entity_names"] = "|".join(s["names"]) if s else ""
            if s:
                for i, eid in enumerate(s["ids"]):
                    if eid not in all_ids:
                        all_ids.append(eid)
                        all_names.append(s["names"][i])
                        all_roles.append(slot.upper())
                        all_tiers.append(s["tiers"][i])
        r["native_party_entity_ids_all"] = "|".join(all_ids)
        r["native_party_entity_names_all"] = "|".join(all_names)
        r["native_party_roles_all"] = "|".join(all_roles)
        r["native_entity_link_tier"] = ("B" if "B" in all_tiers
                                        else ("A" if all_tiers else ""))
        r["n_native_parties"] = len(all_ids)
        r["entity_link_built_by_script"] = SCRIPT
        if all_ids and not r["native_entity_ids"].strip():
            r["native_entity_ids"] = "|".join(all_ids)
            r["native_entity_names"] = "|".join(all_names)
            r["native_entity_link_basis"] = "PARTY_NAME_RESOLVED"
    d_after = sum(1 for r in decisions if r["native_entity_ids"].strip())
    df2 = fieldnames_of(CLEAN / "admin_appeal_decisions.csv")
    df2 = df2 + [c for c in dcols if c not in df2]
    backup(CLEAN / "admin_appeal_decisions.csv")
    write_csv(CLEAN / "admin_appeal_decisions.csv", decisions, df2)
    print(f"  decisions linked: {d_before:,} -> {d_after:,}")
    print("  role split on decisions: appellant "
          f"{sum(1 for r in decisions if r['native_appellant_entity_ids']):,} | "
          f"appellee {sum(1 for r in decisions if r['native_appellee_entity_ids']):,} | "
          f"both {sum(1 for r in decisions if r['native_appellant_entity_ids'] and r['native_appellee_entity_ids']):,}")
    report["tables"]["admin_appeal_parties"] = {
        "rows": len(parties), "linked_before": p_before, "linked_after": p_after,
        "held_candidates_confirmed": held_confirmed,
        "held_candidates_still_refused": held_refused}
    report["tables"]["admin_appeal_decisions"] = {
        "rows": len(decisions), "linked_before": d_before, "linked_after": d_after,
        "with_native_appellant": sum(1 for r in decisions
                                     if r["native_appellant_entity_ids"]),
        "with_native_appellee": sum(1 for r in decisions
                                    if r["native_appellee_entity_ids"]),
        "native_on_both_sides": sum(
            1 for r in decisions if r["native_appellant_entity_ids"]
            and r["native_appellee_entity_ids"])}
    write_csv(REVIEW / f"168_admin_appeal_unresolved_parties_{TODAY}.csv",
              review_rows(p_res, p_counts, "admin_appeal_organisation_party"),
              REVIEW_FIELDS)

    # =====================================================================
    # 3. FOIA - direct link, and an AUDIT of the links already there
    # =====================================================================
    print("\n[3] FOIA request index ---------------------------------------")
    foia = rd(CLEAN / "foia_request_index.csv")
    f_before = sum(1 for r in foia if r["tribe_entity_id"].strip())

    # AUDIT FIRST. `tribe_match_phrase` is a phrase found in FREE PROSE, which
    # is a far weaker operation than matching a party FIELD: the whole field is
    # the party's name, a description is 2,000 words of other things. Measured:
    # 94 rows match on the bare token "georgetown" and are E&E News listing
    # `georgetown.edu` among ~40 email domains to search - Georgetown
    # University, not the Native Village of Georgetown, Alaska.
    audit = []
    for r in foia:
        r.setdefault("tribe_entity_link_tier", "")
        r.setdefault("tribe_entity_link_audit", "")
        r.setdefault("entity_link_built_by_script", "")
        ph = r["tribe_match_phrase"].strip()
        if not r["tribe_entity_id"].strip():
            continue
        toks = norm(ph).split()
        c = core(ph)
        ident = {t for t in c if t not in NAME_TRAPS and t not in US_STATES}
        if len(toks) < 2 or not ident:
            r["tribe_entity_link_tier"] = "B"
            r["tribe_entity_link_audit"] = (
                "DISPUTED_FREE_TEXT_SINGLE_TOKEN: the entity was matched on the "
                f"bare phrase '{ph}' inside a free-text request description. One "
                "token found in prose is not a party name. Link retained, "
                "demoted, staged for a ruling.")
            audit.append({
                "context": "foia_free_text_single_token",
                "party_name_as_recorded": ph,
                "rows_affected": 1,
                "refusal_reason": "existing_link_disputed_single_token_in_prose",
                "proposed_entity_id": r["tribe_entity_id"],
                "proposed_entity_name": r["tribe_mentioned"],
                "YOUR_RULING": "",
                "staged_date": TODAY, "staged_by_script": SCRIPT})
        else:
            r["tribe_entity_link_tier"] = "A"
            r["tribe_entity_link_audit"] = "phrase_has_2plus_identifying_tokens"

    # Now extend: resolve `tribe_mentioned` / `requester_organization` where the
    # index named something it never keyed.
    ro_names, ro_counts = set(), {}
    for r in foia:
        nm = r.get("requester_organization", "").strip()
        if nm:
            ro_names.add(nm)
            ro_counts[nm] = ro_counts.get(nm, 0) + 1
    ro_res = resolve_distinct(idx, ro_names)
    n_req = 0
    for r in foia:
        nm = r.get("requester_organization", "").strip()
        res = ro_res.get(nm, {})
        r.setdefault("requester_native_entity_id", "")
        r.setdefault("requester_native_entity_name", "")
        r.setdefault("requester_entity_link_method", "")
        r.setdefault("requester_entity_link_tier", "")
        if res.get("entity_id"):
            r["requester_native_entity_id"] = res["entity_id"]
            r["requester_native_entity_name"] = res["entity_name"]
            r["requester_entity_link_method"] = res["method"]
            r["requester_entity_link_tier"] = res["tier"]
            r["entity_link_built_by_script"] = SCRIPT
            n_req += 1
    # `party_role` on a FOIA row: the entity is the SUBJECT of the request
    # unless it is the requester. Two different facts, never merged.
    for r in foia:
        roles = []
        if r["tribe_entity_id"].strip():
            roles.append("SUBJECT_OF_REQUEST")
        if r.get("requester_native_entity_id", "").strip():
            roles.append("REQUESTER")
        r["party_role"] = "|".join(roles)
    f_after = sum(1 for r in foia
                  if r["tribe_entity_id"].strip()
                  or r.get("requester_native_entity_id", "").strip())
    ffo = fieldnames_of(CLEAN / "foia_request_index.csv")
    for c in ["tribe_entity_link_tier", "tribe_entity_link_audit",
              "requester_native_entity_id", "requester_native_entity_name",
              "requester_entity_link_method", "requester_entity_link_tier",
              "party_role", "entity_link_built_by_script"]:
        if c not in ffo:
            ffo.append(c)
    backup(CLEAN / "foia_request_index.csv")
    write_csv(CLEAN / "foia_request_index.csv", foia, ffo)
    n_disputed = sum(1 for r in foia
                     if r["tribe_entity_link_audit"].startswith("DISPUTED"))
    print(f"  rows with any Native entity: {f_before:,} -> {f_after:,}  "
          f"({n_req:,} new via requester_organization)")
    print(f"  existing subject links audited: "
          f"{f_before - n_disputed:,} hold at A, {n_disputed:,} DISPUTED and demoted to B")
    report["tables"]["foia_request_index"] = {
        "rows": len(foia), "linked_before": f_before, "linked_after": f_after,
        "new_requester_links": n_req,
        "pre_existing_links_disputed_and_demoted": n_disputed}
    write_csv(REVIEW / f"168_foia_link_audit_{TODAY}.csv", audit, REVIEW_FIELDS)

    # =====================================================================
    # 4. RESOURCE REVENUE - a DOCUMENTED CEILING of 966. Verify, do not chase.
    # =====================================================================
    print("\n[4] Resource revenue -----------------------------------------")
    rr = rd(CLEAN / "resource_revenue.csv")
    r_before = sum(1 for r in rr if r["recipient_entity_id"].strip())
    named = [r for r in rr if r["recipient_entity_name"].strip()]
    print(f"  rows {len(rr):,}  |  rows naming a recipient at all: {len(named):,}"
          f"   <-- THIS IS THE 966 CEILING")
    print(f"  rows naming no recipient: {len(rr) - len(named):,} "
          f"(national/state aggregates - not attributable to any entity)")
    unl = {}
    for r in named:
        if not r["recipient_entity_id"].strip():
            unl[r["recipient_entity_name"].strip()] = \
                unl.get(r["recipient_entity_name"].strip(), 0) + 1
    print(f"  linked {r_before:,} of {len(named):,}. The residual "
          f"{len(named) - r_before} rows are:")
    rr_review = []
    for nm, n in sorted(unl.items(), key=lambda x: -x[1]):
        eid, method, strength, why = idx.match(nm)
        # An AGGREGATE party string must never resolve to one entity.
        aggregate = bool(re.search(
            r"\b(individuals|holders|shareholders|corporations|"
            r"not individually named|and at-large|other )", nm, re.I))
        verdict = ("AGGREGATE_OR_INDIVIDUALS - refused by rule: an aggregate "
                   "party never resolves to one entity"
                   if aggregate else (why or "resolved"))
        print(f"    {n:5d}  {nm[:72]}")
        print(f"           -> {verdict}")
        rr_review.append({
            "context": "resource_revenue_recipient",
            "party_name_as_recorded": nm, "rows_affected": n,
            "refusal_reason": verdict,
            "proposed_entity_id": "" if aggregate else (eid or ""),
            "proposed_entity_name": "" if aggregate else idx.name_of(eid),
            "YOUR_RULING": "", "staged_date": TODAY, "staged_by_script": SCRIPT})
    write_csv(REVIEW / f"168_resource_revenue_ceiling_{TODAY}.csv",
              rr_review, REVIEW_FIELDS)
    print("  NO rows written to resource_revenue.csv - every unlinked named "
          "recipient is an aggregate or a set of individuals, refused BY RULE.")
    report["tables"]["resource_revenue"] = {
        "rows": len(rr), "linked_before": r_before, "linked_after": r_before,
        "documented_ceiling": len(named),
        "residual_unlinkable_by_rule": len(named) - r_before,
        "note": ("the 966 ceiling is exactly the count of rows carrying a "
                 "recipient_entity_name; the residual are aggregate party "
                 "strings and individual headright holders")}

    # =====================================================================
    # 5. CODEBOOK FRAGMENT. Per-dataset fragment ONLY - `codebook_master.csv`
    #    is never written here. Every variable carries a description, because
    #    `62_no_regression_check.py` fails on any published variable that has
    #    none, and a column shipped without one is a column nobody can use.
    # =====================================================================
    print("\n[5] Codebook fragment ----------------------------------------")
    LINK_TIER_DESC = (
        "Tier of THE LINK, not of the row. A = exact or core-set match on the "
        "entity's own canonical, Federal Register official, or tier-A legal "
        "name. B = match on a tier-B generated alias, a head-anchored "
        "containment against an official name variant, a 60-character "
        "truncation prefix, or a bare one-word string; B is visible internally "
        "and never publishes. Read this INSTEAD of confidence_tier when asking "
        "how good the entity link is; confidence_tier describes the record.")
    ROLE_DESC = (
        "Role of this party in the proceeding. A filing by a non-Native "
        "intervenor in a docket that a Native entity is party to is NOT a "
        "Native-entity filing, and this column is what keeps the two apart.")
    cbf = []

    def cbrow(ds, var, typ, desc, rows, filled, pub=1, tier="public",
              units=""):
        cbf.append({
            "dataset": ds, "variable": var, "type": typ, "units": units,
            "pct_filled": round(100.0 * filled / rows, 1) if rows else 0.0,
            "n_rows": rows, "published": pub, "access_tier": tier,
            "description": desc, "generated": TODAY})

    nH = len(hub)
    for var, typ, desc, filled in [
        ("ferc_docket_party_id", "text", "Identifier for one (docket, party, role) observation.", nH),
        ("docket_number", "text", "FERC docket the party appears on. The HUB key.", nH),
        ("party_name_as_recorded", "text", "Party name verbatim from FERC. Never normalised in place.", nH),
        ("party_role", "text", "APPLICANT_OR_LICENSEE (named on the docket sheet), FILER (filed at least one document), or APPLICANT_AND_FILER (both). " + ROLE_DESC, nH),
        ("party_role_basis", "text", "Which FERC field the role was read from.", nH),
        ("n_filings_by_this_party_on_docket", "integer", "Documents this party filed on this docket. Blank for an applicant that filed none.", sum(1 for h in hub if h["n_filings_by_this_party_on_docket"] != "")),
        ("resolved_native_entity_id", "text", "Cedar Press entity this party resolves to, or blank. Blank means UNRESOLVED, never 'not Native'.", sum(1 for h in hub if h["resolved_native_entity_id"])),
        ("resolved_native_entity_name", "text", "Canonical spine name of the resolved entity.", sum(1 for h in hub if h["resolved_native_entity_name"])),
        ("resolved_native_entity_class", "text", "Spine entity_class of the resolved entity.", sum(1 for h in hub if h["resolved_native_entity_class"])),
        ("entity_link_method", "text", "How the name resolved: exact_name, core_name, official_name_containment, truncation_prefix, or a _single_token variant.", sum(1 for h in hub if h["entity_link_method"])),
        ("entity_link_tier", "text", LINK_TIER_DESC, sum(1 for h in hub if h["entity_link_tier"])),
        ("entity_link_refusal_reason", "text", "Why an unresolved party was REFUSED, named explicitly (place_suffix_trap, generic_core_only, cross_class_guard, identity_word_only_on_the_spine_side, ambiguous_*). A refusal is a finding, not a gap.", sum(1 for h in hub if h["entity_link_refusal_reason"])),
    ]:
        cbrow("04g_ferc_docket_parties", var, typ, desc, nH, filled)

    nF = len(filings)
    for var, typ, desc, filled in [
        ("party_role", "text", "FILER_IS_NATIVE_ENTITY or FILER_NOT_A_NATIVE_ENTITY. " + ROLE_DESC, nF),
        ("filer_entity_link_method", "text", "How the filer name resolved.", sum(1 for r in filings if r["filer_entity_link_method"])),
        ("filer_entity_link_tier", "text", LINK_TIER_DESC, sum(1 for r in filings if r["filer_entity_link_tier"])),
        ("filer_entity_link_refusal_reason", "text", "Why the filer name was refused, or withdrawn_by_a_later_guard.", sum(1 for r in filings if r["filer_entity_link_refusal_reason"])),
        ("docket_native_party_ids", "text", "Pipe-separated Native entities that are party to THIS DOCKET. Docket CONTEXT only. Never evidence about who filed this document - read party_role for that.", sum(1 for r in filings if r["docket_native_party_ids"])),
        ("docket_native_party_names", "text", "Names for docket_native_party_ids.", sum(1 for r in filings if r["docket_native_party_names"])),
        ("docket_native_party_roles", "text", "Roles those docket parties hold, positionally aligned with docket_native_party_ids.", sum(1 for r in filings if r["docket_native_party_roles"])),
        ("docket_has_native_party", "integer", "1 where the docket has at least one resolved Native party. Says nothing about this filing's filer.", nF),
    ]:
        cbrow("04h_ferc_docket_filing_links", var, typ, desc, nF, filled)

    nD = len(dockets)
    for var, typ, desc, filled in [
        ("applicant_resolved_native_entity_id", "text", "Cedar Press entity the docket's applicant or licensee resolves to.", sum(1 for r in dockets if r["applicant_resolved_native_entity_id"])),
        ("applicant_resolved_native_entity_name", "text", "Canonical name of the resolved applicant.", sum(1 for r in dockets if r["applicant_resolved_native_entity_name"])),
        ("applicant_entity_link_method", "text", "How the applicant name resolved.", sum(1 for r in dockets if r["applicant_entity_link_method"])),
        ("applicant_entity_link_tier", "text", LINK_TIER_DESC, sum(1 for r in dockets if r["applicant_entity_link_tier"])),
        ("applicant_entity_link_refusal_reason", "text", "Why the applicant name was refused.", sum(1 for r in dockets if r["applicant_entity_link_refusal_reason"])),
        ("docket_native_party_ids", "text", "All Native entities party to this docket, in any role.", sum(1 for r in dockets if r["docket_native_party_ids"])),
        ("docket_native_party_names", "text", "Names for docket_native_party_ids.", sum(1 for r in dockets if r["docket_native_party_names"])),
        ("docket_native_party_roles", "text", "Roles held, positionally aligned with docket_native_party_ids.", sum(1 for r in dockets if r["docket_native_party_roles"])),
        ("docket_native_party_count", "integer", "Number of distinct Native entities party to this docket.", nD),
    ]:
        cbrow("04i_ferc_tribal_docket_links", var, typ, desc, nD, filled)

    nP = len(parties)
    for var, typ, desc, filled in [
        ("entity_link_tier", "text", LINK_TIER_DESC, sum(1 for r in parties if r["entity_link_tier"])),
        ("entity_link_refusal_reason", "text", "Why this party was not resolved. `party_type=NATURAL_PERSON` / `AGENCY_OFFICIAL` / `ESTATE` means it was never a candidate: an Area Director is a BIA officer, not the tribe.", sum(1 for r in parties if r["entity_link_refusal_reason"])),
        ("party_caption_names_additional_parties", "text", "Y where the caption ended in `et al` - the resolved entity is one named party, not the only party. The upstream compound_party_caption column is N on all 1,536 such rows.", nP),
    ]:
        cbrow("04j_admin_appeal_party_links", var, typ, desc, nP, filled)

    nDe = len(decisions)
    for slot in ["appellant", "appellee", "petitioner", "estate_subject",
                 "other_party"]:
        cbrow("04k_admin_appeal_decision_links",
              f"native_{slot}_entity_ids", "text",
              f"Native entities that appear on this decision AS {slot.upper()}. "
              "Roles are kept in separate columns on purpose: a tribe appearing "
              "as appellee is not the same fact as a tribe appealing.",
              nDe, sum(1 for r in decisions if r[f"native_{slot}_entity_ids"]))
        cbrow("04k_admin_appeal_decision_links",
              f"native_{slot}_entity_names", "text",
              f"Names for native_{slot}_entity_ids.",
              nDe, sum(1 for r in decisions if r[f"native_{slot}_entity_names"]))
    for var, typ, desc, filled in [
        ("native_party_entity_ids_all", "text", "Union of the role columns, de-duplicated. Use the role columns for anything that depends on which side a party was on.", sum(1 for r in decisions if r["native_party_entity_ids_all"])),
        ("native_party_entity_names_all", "text", "Names for native_party_entity_ids_all.", sum(1 for r in decisions if r["native_party_entity_names_all"])),
        ("native_party_roles_all", "text", "Roles positionally aligned with native_party_entity_ids_all.", sum(1 for r in decisions if r["native_party_roles_all"])),
        ("native_entity_link_tier", "text", LINK_TIER_DESC + " B if ANY contributing party link is B.", sum(1 for r in decisions if r["native_entity_link_tier"])),
        ("n_native_parties", "integer", "Distinct Native entities party to this decision.", nDe),
    ]:
        cbrow("04k_admin_appeal_decision_links", var, typ, desc, nDe, filled)

    nFo = len(foia)
    for var, typ, desc, filled in [
        ("tribe_entity_link_tier", "text", LINK_TIER_DESC + " Free-text derived: the entity was found INSIDE a request description, not in a party field.", sum(1 for r in foia if r["tribe_entity_link_tier"])),
        ("tribe_entity_link_audit", "text", "Audit of the pre-existing tribe_entity_id link. DISPUTED_FREE_TEXT_SINGLE_TOKEN means the match rests on one bare word found in prose - 94 rows key to the Native Village of Georgetown, Alaska off `georgetown.edu` in a list of email domains. The link is RETAINED and demoted, never silently deleted.", sum(1 for r in foia if r["tribe_entity_link_audit"])),
        ("requester_native_entity_id", "text", "Native entity that FILED this FOIA request. A different fact from tribe_entity_id, which is the entity the request is ABOUT.", sum(1 for r in foia if r["requester_native_entity_id"])),
        ("requester_native_entity_name", "text", "Canonical name of the requesting entity.", sum(1 for r in foia if r["requester_native_entity_name"])),
        ("requester_entity_link_method", "text", "How the requester organisation name resolved.", sum(1 for r in foia if r["requester_entity_link_method"])),
        ("requester_entity_link_tier", "text", LINK_TIER_DESC, sum(1 for r in foia if r["requester_entity_link_tier"])),
        ("party_role", "text", "SUBJECT_OF_REQUEST, REQUESTER, or both, pipe-separated. " + ROLE_DESC, sum(1 for r in foia if r["party_role"])),
    ]:
        cbrow("13_foia_index_entity_links", var, typ, desc, nFo, filled)

    cb_fields = ["dataset", "variable", "type", "units", "pct_filled",
                 "n_rows", "published", "access_tier", "description",
                 "generated"]
    CB = CLEAN / "codebook"
    for ds in sorted({r["dataset"] for r in cbf}):
        write_csv(CB / f"{ds}.csv", [r for r in cbf if r["dataset"] == ds],
                  cb_fields)
    print(f"  {len(cbf)} variables documented across "
          f"{len({r['dataset'] for r in cbf})} fragments. "
          "codebook_master.csv NOT written.")
    report["codebook_variables_documented"] = len(cbf)

    # =====================================================================
    (CEDAR / "logs").mkdir(exist_ok=True)
    out = CEDAR / "logs" / f"168_linkage_report_{TODAY}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n  report -> {out.relative_to(CEDAR)}")
    print("\n=== done ===")


if __name__ == "__main__":
    if "--restore" in sys.argv:
        print("=== 168: restoring THIS SCRIPT'S OWN OUTPUTS, by name ===")
        restore_my_outputs()
    else:
        main()
