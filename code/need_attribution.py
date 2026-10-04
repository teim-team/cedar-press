"""Per-record NEED attribution corrections: recorded rulings first, then documented guards.

MIRRORS Lumecon-data ``src/lumecon_data/need/attribution.py`` (the producer that builds the
NEED release from the preserved inputs) so that ``code/1072`` builds the same corrections
into ``need_enterprises.csv`` and ``code/1189`` / ``code/1151`` apply them to the files this
repository publishes. Both copies are held to the same test vectors
(``server/tests/test_need_attribution.py`` here, ``tests/test_need_attribution.py`` there);
change one, change the other.

Owner ruling 2026-10-04 (Elijah Moreno): the only hold is a specific record flagged as
attributed to the wrong entity. This module decides, for one preserved enterprise or
relationship row at a time, whether its owner link stands, is corrected by a recorded
ruling, or is a specific misattribution whose link must not publish. The row itself always
publishes; only the attribution columns are blanked (or replaced by a ruling's owner).

Two inputs decide it:

* **Rulings** (``cedar_rulings`` columns, as written by ``adjudication_triage``) keyed by
  ``NEED_ENTERPRISE`` (an issued enterprise ID), ``NEED_ENTERPRISE_KEY`` (the register key
  ``owner_hub_cedar_uid|enterprise_name_normalized``) or ``NEED_ENTERPRISE_KEY_SHA256``
  (the same key hashed, for a row whose name may be a private individual's).
  ``ATTRIBUTE`` + ``REJECT_ATTRIBUTION`` replaces a wrong owner; ``REJECT_ATTRIBUTION``
  alone removes it; ``HUMAN_REVIEW`` in ``MISATTRIBUTION_FLAGGED`` masks it until a person
  decides. A ruling applies only while the row still carries the owner it names, so a
  rebuild that already fixed the row is left alone.
* **Guards**, the same documented rules cedar-press ``code/1072`` now applies when it
  builds NEED, for every row no ruling covers and whose link rests on an automated route:

  - ``REFUSED_HUB_IS_THE_ENTERPRISE``: the row is the owning government itself;
  - ``REFUSED_VILLAGE_GOVERNMENT_ANCSA_CORPORATION`` (``ANCSA_OWNERSHIP_RULING`` rule 2):
    an Alaska Native village government recorded as the owner of an ANCSA corporation or
    one of its companies;
  - ``REFUSED_GENERIC_TOKEN_ONLY`` (``ENTITY_MATCH_RULES`` rule 1): the enterprise shares
    a word with its owner's name but no full distinctive name of the owner, or only a weak
    place word (the first-shared-token resolver defect).

No identifier is minted, merged, retired or transferred here.
"""

from __future__ import annotations

# A plain module: code/ scripts import it by path (sys.path.insert of code/).

import csv
import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

VILLAGE = "Federally recognized Alaska Native Village"
ANC_CLASSES = frozenset({"Alaska Native Regional Corporation", "Alaska Native Village Corporation"})
OWNER_CLASS = {
    "Federally recognized tribe": "tribal_government",
    "State-recognized tribe": "tribal_government",
    VILLAGE: "tribal_government",
    "Federal-level constituency entity": "tribal_government",
    "State-level constituency entity": "tribal_government",
    "Federal-level self-governance consortium": "tribal_government",
    "Alaska Native Regional Corporation": "alaska_native_corporation",
    "Alaska Native Village Corporation": "alaska_native_corporation",
    "Native Hawaiian Organization": "native_hawaiian_organization",
}

# Evidence on which a link stands on its own; the guards never second-guess it.
PROTECTED_EVIDENCE = frozenset(
    {"audited_annual_report_as_45_55_139", "owner_research_dataset_hand_ruling"}
)
# A hub that a 1072 guard already repointed to the corporation the source names.
PROTECTED_METHODS = frozenset(
    {
        "ancsa_brand_repointed_to_named_corporation",
        "ancsa_village_government_repointed_to_corporation",
    }
)

# Words that carry no identity (ENTITY_MATCH_RULES rule 1).
GENERIC = frozenset(
    {
        "a",
        "and",
        "of",
        "the",
        "at",
        "for",
        "on",
        "in",
        "de",
        "inc",
        "incorporated",
        "llc",
        "ll",
        "llp",
        "lp",
        "ltd",
        "limited",
        "liability",
        "corp",
        "corporation",
        "co",
        "company",
        "plc",
        "pllc",
        "jv",
        "joint",
        "venture",
        "group",
        "holding",
        "holdings",
        "enterprise",
        "enterprises",
        "service",
        "services",
        "business",
        "businesses",
        "development",
        "management",
        "solutions",
        "tribe",
        "tribes",
        "tribal",
        "nation",
        "nations",
        "band",
        "bands",
        "indian",
        "indians",
        "native",
        "natives",
        "american",
        "americans",
        "village",
        "villages",
        "community",
        "communities",
        "council",
        "association",
        "traditional",
        "government",
        "ira",
        "reservation",
        "rancheria",
        "pueblo",
        "confederated",
        "consortium",
        "federation",
        "national",
        "alaska",
        "alaskan",
        "inupiat",
        "state",
        "states",
    }
)
# Place and common words that name many things: a one-word owner name made only of these
# may never award a link on its own (ANCSA_BRAND_WEAK in cedar-press code/1072, extended).
WEAK = frozenset(
    {
        "white",
        "black",
        "red",
        "green",
        "blue",
        "gold",
        "golden",
        "silver",
        "arctic",
        "old",
        "new",
        "twin",
        "port",
        "eagle",
        "bering",
        "north",
        "northern",
        "south",
        "southern",
        "east",
        "eastern",
        "west",
        "western",
        "central",
        "coastal",
        "pacific",
        "big",
        "little",
        "sea",
        "bay",
        "united",
        "general",
        "global",
        "federal",
        "beaver",
        "birch",
        "creek",
        "pass",
        "bill",
        "king",
        "mission",
        "vista",
        "crow",
        "prairie",
        "wind",
        "lake",
        "lakes",
        "river",
        "point",
        "mountain",
        "mountains",
        "harbor",
        "island",
        "islands",
        "ocean",
        "mill",
        "rock",
        "pine",
        "cedar",
        "spring",
        "springs",
        "valley",
        "grand",
        "fort",
        "st",
        "saint",
        "sand",
        "bear",
        "wolf",
        "fox",
        "lagoon",
        "village",
        "summit",
        "peak",
        "star",
        "sun",
        "moon",
        "falls",
        "rapids",
    }
)
GOVERNMENT_WORDS = frozenset(
    {
        "tribe",
        "tribes",
        "tribal",
        "nation",
        "band",
        "indians",
        "village",
        "community",
        "council",
        "government",
        "pueblo",
        "rancheria",
        "traditional",
        "ira",
    }
)
ENTERPRISE_WORDS = frozenset(
    {
        "inc",
        "incorporated",
        "llc",
        "ll",
        "llp",
        "lp",
        "ltd",
        "limited",
        "corp",
        "corporation",
        "co",
        "company",
        "enterprise",
        "enterprises",
        "business",
        "businesses",
        "holdings",
        "holding",
        "services",
        "service",
        "development",
        "authority",
        "gaming",
        "casino",
        "jv",
        "venture",
        "industries",
        "group",
        "natives",
        "properties",
        "solutions",
        "systems",
        "technologies",
        "technology",
        "construction",
    }
)

# Owner-link columns on an enterprise or relationship row: the names ``need.base`` projects
# (``asserted_*``) and the names ``code/1072`` writes and the preview/samples carry.
OWNER_UID_COLUMNS = (
    "asserted_owner_hub_cedar_uid",
    "asserted_cedar_uid",
    "owner_hub_cedar_uid",
    "cedar_uid",
)
OWNER_DETAIL_COLUMNS = (
    "owner_hub_name",
    "owner_hub_entity_class",
    "owner_class",
    "owner_hub_state",
    "parent_enterprise_id",
    "parent_name",
    "parent_is_hub",
)

GUARD_HUB_IS_ENTERPRISE = "REFUSED_HUB_IS_THE_ENTERPRISE"
GUARD_VILLAGE_ANC = "REFUSED_VILLAGE_GOVERNMENT_ANCSA_CORPORATION"
GUARD_GENERIC_TOKEN = "REFUSED_GENERIC_TOKEN_ONLY"  # noqa: S105 - a guard code

STATUS_PUBLISHED = "published"
STATUS_CORRECTED = "corrected_by_ruling"
STATUS_REJECTED = "rejected_by_ruling"
STATUS_FLAGGED = "misattribution_flagged"
STATUS_REFUSED = "refused_by_guard"
STATUS_STALE = "ruling_not_applicable"
MASKED_STATUSES = frozenset({STATUS_REJECTED, STATUS_FLAGGED, STATUS_REFUSED})

RULING_COLUMNS = (
    "ruling_id",
    "ruled_date",
    "identifier_type",
    "identifier",
    "entity_name",
    "ruling",
    "parent_native_entity",
    "parent_entity_id",
    "parent_entity_class",
    "evidence_url",
    "ruled_by",
    "human_category",
)
IDENTIFIER_TYPES = frozenset(
    {"NEED_ENTERPRISE", "NEED_ENTERPRISE_KEY", "NEED_ENTERPRISE_KEY_SHA256"}
)
APPLIED_RULINGS = frozenset({"ATTRIBUTE", "REJECT_ATTRIBUTION", "HUMAN_REVIEW", "CONFIRM"})


def tokens(name: str) -> list[str]:
    """Lower-case ASCII word tokens; apostrophes join (``Moore's`` -> ``moores``)."""

    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub("['\u2019\u2018]", "", text)
    return re.findall(r"[a-z0-9]+", text)


def distinctive(name: str) -> frozenset[str]:
    return frozenset(t for t in tokens(name) if t not in GENERIC)


def key_sha256(owner_uid: str, normalized_name: str) -> str:
    return hashlib.sha256(f"{owner_uid}|{normalized_name}".encode()).hexdigest()


@dataclass(frozen=True)
class Hub:
    uid: str
    canonical_name: str
    entity_class: str
    state: str
    names: tuple[str, ...]


class Register:
    """The issued Native-entity register (cedar-press ``cedar_identity_register.csv``)."""

    def __init__(self, rows: Iterable[Mapping[str, str]]):
        self.by_uid: dict[str, Hub] = {}
        anc_names: dict[tuple[str, ...], set[str]] = defaultdict(set)
        for row in rows:
            uid = (row.get("cedar_uid") or "").strip()
            if not uid:
                continue
            names = [row.get("canonical_name") or "", row.get("federal_register_legal_name") or ""]
            names += re.split(r"[|;]", row.get("former_names") or "")
            hub = Hub(
                uid=uid,
                canonical_name=(row.get("canonical_name") or "").strip(),
                entity_class=(row.get("entity_class") or "").strip(),
                state=(row.get("state") or "").strip(),
                names=tuple(n.strip() for n in names if n.strip()),
            )
            if uid in self.by_uid:
                raise ValueError(f"Register lists {uid} twice")
            self.by_uid[uid] = hub
            if hub.entity_class in ANC_CLASSES:
                for name in hub.names:
                    words = tuple(t for t in tokens(name) if t not in GENERIC)
                    if words and not (len(words) == 1 and words[0] in WEAK):
                        anc_names[words].add(uid)
        # Only an unambiguous full distinctive ANC name may identify a corporation.
        self.anc_by_words = {k: next(iter(v)) for k, v in anc_names.items() if len(v) == 1}

    @classmethod
    def from_csv(cls, path: Path) -> Register:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return cls(csv.DictReader(handle))

    def anc_named_by(self, enterprise_name: str) -> str | None:
        """The ANCSA corporation whose full distinctive name the enterprise begins with."""

        words = [t for t in tokens(enterprise_name) if t not in GENERIC]
        for size in range(min(len(words), 4), 0, -1):
            uid = self.anc_by_words.get(tuple(words[:size]))
            if uid:
                return uid
        return None


STOP = frozenset({"of", "the", "and", "a"})
# A shared legal form is no shared word at all (``Broadleaf, Inc`` vs ``Foundation, Inc.``).
LEGAL_FORMS = frozenset(
    {
        "inc",
        "incorporated",
        "llc",
        "ll",
        "llp",
        "lp",
        "ltd",
        "limited",
        "liability",
        "corp",
        "corporation",
        "co",
        "company",
        "plc",
        "pllc",
    }
)


def _phrase(words: Iterable[str]) -> str:
    return " " + " ".join(t for t in words if t not in STOP) + " "


def carries_full_name(enterprise_name: str, hub: Hub) -> bool:
    """The enterprise carries one of the owner's names in full.

    Either the whole name as a phrase of two or more words (``Prairie Band`` in ``Prairie
    Band Casino``), or every distinctive word of a name when one of them is not weak
    (``Kipnuk`` in ``Kipnuk Technology``). A lone weak word never counts (``Arctic``).
    """

    words = tokens(enterprise_name)
    text = _phrase(words)
    for name in hub.names:
        name_words = [t for t in tokens(name) if t not in STOP]
        core = [t for t in name_words if t not in GENERIC]
        if len(name_words) >= 2 and _phrase(name_words) in text:
            return True
        if core and set(core) <= set(words) and any(t not in WEAK for t in core):
            return True
    return False


def name_relation(enterprise_name: str, hub: Hub) -> str:
    """How an enterprise name relates to its owner's names.

    ``accepted``: it carries one of the owner's names in full (``carries_full_name``).
    ``weak_only``: it shares words with the owner's names, but only generic or weak place
    words, which is the first-shared-token resolver defect. ``distinctive``: it shares a
    distinctive word without carrying a full name (``Oglala Lakota College`` under the
    Oglala Sioux): not refused by name alone. ``none``: no word in common."""

    if carries_full_name(enterprise_name, hub):
        return "accepted"
    owner_words: set[str] = set()
    for name in hub.names:
        owner_words.update(tokens(name))
    shared = set(tokens(enterprise_name)) & (owner_words - STOP - LEGAL_FORMS)
    if not shared:
        return "none"
    if all(t in WEAK or t in GENERIC for t in shared):
        return "weak_only"
    return "distinctive"


class TableContext:
    """What the guards need to know about the whole enterprise table."""

    def __init__(self, register: Register, enterprises: Iterable[Mapping[str, str]]):
        self.register = register
        self.anc_homes: dict[str, set[str]] = defaultdict(set)
        heads: dict[str, Counter[str]] = defaultdict(Counter)
        foreign: set[str] = set()
        for row in enterprises:
            hub = register.by_uid.get(_owner(row))
            name = row.get("enterprise_name_normalized") or ""
            words = [t for t in tokens(row.get("enterprise_name") or "") if t not in GENERIC]
            head = words[0] if words else ""
            if hub is None:
                continue
            if hub.entity_class in ANC_CLASSES:
                if name:
                    self.anc_homes[name].add(row.get("enterprise_id") or hub.uid)
                if head:
                    heads[head][hub.uid] += 1
            elif hub.entity_class != VILLAGE and head:
                foreign.add(head)
        # A brand is the leading word of at least three companies under exactly one ANCSA
        # corporation and of none under any other kind of owner except village governments
        # (the defect this guard exists to catch).
        self.brands = {
            head: next(iter(owners))
            for head, owners in heads.items()
            if len(owners) == 1
            and sum(owners.values()) >= 3
            and head not in WEAK
            and head not in foreign
        }


def _owner(row: Mapping[str, str]) -> str:
    for column in (
        "asserted_owner_hub_cedar_uid",
        "owner_hub_cedar_uid",
        "asserted_cedar_uid",
        "cedar_uid",
    ):
        value = (row.get(column) or "").strip()
        if value:
            return value
    return ""


def guard(row: Mapping[str, str], context: TableContext) -> tuple[str, str] | None:
    """The first documented guard the row's owner link fails, with its reason."""

    if (row.get("evidence_class") or "") in PROTECTED_EVIDENCE:
        return None
    if (row.get("hub_resolution_method") or "") in PROTECTED_METHODS:
        return None
    hub = context.register.by_uid.get(_owner(row))
    if hub is None:
        return None
    name = row.get("enterprise_name") or row.get("child_name_as_recorded") or ""
    words = set(tokens(name))
    core = distinctive(name)
    hub_core: set[str] = set()
    for hub_name in hub.names:
        hub_core |= distinctive(hub_name)
    is_government_name = bool(words & GOVERNMENT_WORDS) and not words & ENTERPRISE_WORDS
    if is_government_name and core and core <= hub_core and carries_full_name(name, hub):
        return GUARD_HUB_IS_ENTERPRISE, f"the row is {hub.canonical_name} ({hub.uid}) itself"
    if hub.entity_class == VILLAGE:
        anc = context.register.anc_named_by(name)
        if anc is not None:
            return (
                GUARD_VILLAGE_ANC,
                f"the enterprise carries the full name of ANCSA corporation {anc}; "
                f"village government {hub.uid} does not own it (ANCSA_OWNERSHIP_RULING rule 2)",
            )
        homes = context.anc_homes.get(row.get("enterprise_name_normalized") or "")
        if homes:
            return (
                GUARD_VILLAGE_ANC,
                "the same enterprise is held under an ANCSA corporation as "
                + ", ".join(sorted(homes))
                + f"; village government {hub.uid} does not own it (rule 2)",
            )
        head = next((t for t in tokens(name) if t not in GENERIC), "")
        if head in context.brands:
            return (
                GUARD_VILLAGE_ANC,
                f"{head!r} is the brand of ANCSA corporation {context.brands[head]}; "
                f"village government {hub.uid} does not own it (rule 2)",
            )
    if name_relation(name, hub) == "weak_only":
        return (
            GUARD_GENERIC_TOKEN,
            f"the enterprise shares only generic or place words with {hub.canonical_name} "
            f"({hub.uid}) and carries none of its full names (ENTITY_MATCH_RULES rule 1)",
        )
    return None


@dataclass(frozen=True)
class Ruling:
    ruling_id: str
    identifier_type: str
    identifier: str
    ruling: str
    parent_uid: str
    parent_name: str
    human_category: str


class Rulings:
    """Recorded NEED attribution rulings, indexed for one-row lookup."""

    def __init__(self, rows: Iterable[Mapping[str, str]]):
        self.by_identifier: dict[tuple[str, str], list[Ruling]] = defaultdict(list)
        seen: set[str] = set()
        for row in rows:
            missing = [c for c in RULING_COLUMNS if c not in row]
            if missing:
                raise ValueError(f"Ruling file lacks columns {missing}")
            kind = row["identifier_type"]
            if kind not in IDENTIFIER_TYPES:
                continue
            if row["ruling"] not in APPLIED_RULINGS:
                raise ValueError(f"{row['ruling_id']}: unknown NEED ruling {row['ruling']!r}")
            if row["ruling_id"] in seen:
                raise ValueError(f"Duplicate ruling id {row['ruling_id']}")
            seen.add(row["ruling_id"])
            ruling = Ruling(
                ruling_id=row["ruling_id"],
                identifier_type=kind,
                identifier=row["identifier"],
                ruling=row["ruling"],
                parent_uid=row["parent_entity_id"],
                parent_name=row["parent_native_entity"],
                human_category=row["human_category"],
            )
            if ruling.ruling in {"ATTRIBUTE", "REJECT_ATTRIBUTION"} and not ruling.parent_uid:
                raise ValueError(f"{ruling.ruling_id}: {ruling.ruling} names no owner")
            self.by_identifier[(kind, ruling.identifier)].append(ruling)

    @classmethod
    def from_csv(cls, path: Path | None) -> Rulings:
        if path is None:
            return cls([])
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return cls(csv.DictReader(handle))

    def for_row(self, row: Mapping[str, str]) -> list[Ruling]:
        found: list[Ruling] = []
        enterprise_id = (row.get("enterprise_id") or "").strip()
        if enterprise_id:
            found += self.by_identifier.get(("NEED_ENTERPRISE", enterprise_id), [])
        owner, name = _owner(row), (row.get("enterprise_name_normalized") or "").strip()
        if owner and name:
            found += self.by_identifier.get(("NEED_ENTERPRISE_KEY", f"{owner}|{name}"), [])
            found += self.by_identifier.get(
                ("NEED_ENTERPRISE_KEY_SHA256", key_sha256(owner, name)), []
            )
        return found


@dataclass(frozen=True)
class Outcome:
    status: str
    basis: str
    removed_owner_uid: str = ""
    assigned_owner_uid: str = ""


def decide(row: Mapping[str, str], rulings: Rulings, context: TableContext) -> Outcome:
    """Rulings first; a ruling about another owner than the row's is stale, not applied."""

    owner = _owner(row)
    found = rulings.for_row(row)
    if found:
        rejects = [r for r in found if r.ruling == "REJECT_ATTRIBUTION" and r.parent_uid == owner]
        attributes = [r for r in found if r.ruling == "ATTRIBUTE"]
        flags = [
            r
            for r in found
            if r.ruling == "HUMAN_REVIEW"
            and r.human_category == "MISATTRIBUTION_FLAGGED"
            and r.parent_uid == owner
        ]
        if rejects and attributes:
            if len({r.parent_uid for r in attributes}) != 1:
                raise ValueError(f"{row.get('enterprise_id')}: rulings attribute two owners")
            chosen = attributes[0]
            return Outcome(
                STATUS_CORRECTED,
                f"{chosen.ruling_id}; {rejects[0].ruling_id}",
                owner,
                chosen.parent_uid,
            )
        if rejects:
            return Outcome(STATUS_REJECTED, rejects[0].ruling_id, owner)
        if flags:
            return Outcome(STATUS_FLAGGED, flags[0].ruling_id, owner)
        if any(r.ruling == "ATTRIBUTE" and r.parent_uid == owner for r in found) or any(
            r.ruling == "CONFIRM" and r.parent_uid == owner for r in found
        ):
            return Outcome(STATUS_PUBLISHED, ";".join(r.ruling_id for r in found))
        if any(r.ruling in {"ATTRIBUTE", "REJECT_ATTRIBUTION", "HUMAN_REVIEW"} for r in found):
            # Human-review rulings in other categories are research, not holds.
            if all(r.ruling == "HUMAN_REVIEW" for r in found):
                pass
            else:
                return Outcome(STATUS_STALE, ";".join(r.ruling_id for r in found))
    refused = guard(row, context)
    if refused is not None:
        return Outcome(STATUS_REFUSED, f"{refused[0]}: {refused[1]}", owner)
    return Outcome(STATUS_PUBLISHED, "")


def apply(
    row: Mapping[str, str], outcome: Outcome, register: Register, *, enterprise_table: bool
) -> dict[str, str]:
    """The row as it publishes: masked, re-attributed, or unchanged."""

    result = dict(row)
    columns = OWNER_UID_COLUMNS + (
        OWNER_DETAIL_COLUMNS if enterprise_table else ("owner_hub_name",)
    )
    if outcome.status in MASKED_STATUSES:
        for column in columns:
            if column in result:
                result[column] = ""
    elif outcome.status == STATUS_CORRECTED:
        hub = register.by_uid.get(outcome.assigned_owner_uid)
        if hub is None:
            raise ValueError(f"Ruled owner {outcome.assigned_owner_uid} is not in the register")
        values = {
            "asserted_owner_hub_cedar_uid": hub.uid,
            "asserted_cedar_uid": hub.uid,
            "owner_hub_cedar_uid": hub.uid,
            "cedar_uid": hub.uid,
            "owner_hub_name": hub.canonical_name,
            "owner_hub_entity_class": hub.entity_class,
            "owner_class": OWNER_CLASS.get(hub.entity_class, ""),
            "owner_hub_state": hub.state,
            "parent_enterprise_id": "",
            "parent_name": hub.canonical_name,
            "parent_is_hub": "Y",
        }
        for column in columns:
            if column in result:
                result[column] = values[column]
    return result
